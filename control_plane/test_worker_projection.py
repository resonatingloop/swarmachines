"""Read-only, accounting and private-field regression proofs with fictional data."""

import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from control_plane import delegation as d
from control_plane import observer as o
from control_plane import worker_projection as w
from control_plane.test_delegation import packet

CANARY = "PRIVATE_CANARY_<script>source-answer-error</script>"


class WorkerProjectionTests(unittest.TestCase):
    """Use local synthetic queues only; never contact a provider."""

    def setUp(self):
        """Create an isolated private writer fixture."""
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "state"
        self.q = d.Queue(self.path)

    def tearDown(self):
        """Release fixtures after any read-only transactions."""
        self.q.close()
        self.temp.cleanup()

    def add(self, number, usage=(278, 87), failure=False, live=True):
        """Persist synthetic outcomes through the real queue contract."""
        p = packet(number)
        p["objective"] = CANARY
        p["expected_deliverable"] = CANARY
        p["source"]["label"] = CANARY
        p["source"]["text"] = CANARY
        p["source"]["sha256"] = d.digest(CANARY)

        def worker(_):
            if failure:
                if usage is None:
                    raise ValueError(CANARY)
                raise d.ProviderResponseError(
                    "response_not_completed",
                    {
                        "status": "incomplete",
                        "usage": {"input_tokens": usage[0], "output_tokens": usage[1]},
                    },
                )
            return {
                "text": CANARY,
                "model": d.MODEL,
                "usage": {"input_tokens": usage[0], "output_tokens": usage[1]},
                "estimated_credits": 999999,
                "private_extra": CANARY,
            }

        return d.execute(self.q, p, "investigator", live=live, runner=worker)[0]

    def inventory(self):
        """Hash content and inventory names; ignore filesystem access times."""
        return {
            p.name: (p.stat().st_size, hashlib.sha256(p.read_bytes()).hexdigest())
            for p in self.path.iterdir()
            if p.is_file()
        }

    def test_realistic_accounting_and_no_private_output_or_mutation(self):
        self.add(1, usage=None, failure=True)
        self.add(2)
        self.add(3, (1878, 2048), failure=True)
        self.add(4, (418, 341))
        self.add(5, (0, 0), live=False)
        before = self.inventory()
        view = w.collect_workers(self.path)
        self.assertEqual(self.inventory(), before)
        self.assertEqual(view["status"], "available")
        self.assertEqual(view["budget"]["requests_used"], 4)
        self.assertEqual(view["budget"]["reserved_credits"], "0.4")
        self.assertEqual(view["budget"]["requests_remaining"], 0)
        self.assertEqual(view["accounting"]["known_usage_attempts"], 3)
        self.assertEqual(view["accounting"]["unknown_usage_attempts"], 1)
        self.assertEqual(view["accounting"]["estimated_subtotal"], "0.0016241")
        rendered = o.render_workers(view)
        for forbidden in (
            CANARY,
            str(self.path),
            "private_extra",
            "claim_token",
            "999999",
        ):
            self.assertNotIn(forbidden, json.dumps(view) + rendered)
        # The still-open writer can continue using its existing connection.
        self.q.db.execute("UPDATE budget SET reserved_micro=reserved_micro WHERE id=1")

    def test_not_supplied_missing_empty_and_symlink(self):
        self.assertEqual(w.collect_workers()["status"], "not supplied")
        missing = self.path / "absent"
        self.assertEqual(w.collect_workers(missing)["status"], "unavailable")
        self.assertFalse(missing.exists())
        self.assertEqual(w.collect_workers(self.path)["attempts"], [])
        link = Path(self.temp.name) / "alias"
        link.symlink_to(self.path, target_is_directory=True)
        self.assertEqual(w.collect_workers(link)["status"], "unavailable")

    def test_active_wal_refused_without_sidecar_changes(self):
        self.q.db.execute("PRAGMA journal_mode=WAL")
        self.add(1)
        before = self.inventory()
        self.assertEqual(w.collect_workers(self.path)["status"], "unavailable")
        self.assertEqual(self.inventory(), before)
        self.q.db.execute("UPDATE budget SET requests=requests WHERE id=1")

    def test_exclusive_lock_unavailable(self):
        self.q.db.execute("BEGIN EXCLUSIVE")
        try:
            before = self.inventory()
            self.assertEqual(w.collect_workers(self.path)["status"], "unavailable")
            self.assertEqual(self.inventory(), before)
        finally:
            self.q.db.execute("ROLLBACK")

    def change_receipt(self, mutation):
        """Inject hostile fixture data without executing it."""
        row = self.q.db.execute("SELECT receipt FROM jobs LIMIT 1").fetchone()
        receipt = json.loads(row[0])
        mutation(receipt)
        self.q.db.execute("UPDATE jobs SET receipt=?", (json.dumps(receipt),))

    def test_unknown_model_usage_error_and_stored_cost(self):
        self.add(1)

        def corrupt(r):
            r["result"]["model"] = CANARY
            r["usage"] = {"input_tokens": True, "output_tokens": 10**10}

        self.change_receipt(corrupt)
        view = w.collect_workers(self.path)
        attempt = view["attempts"][0]
        self.assertEqual(attempt["model"], "unknown")
        self.assertIsNone(attempt["input_tokens"])
        self.assertIsNone(attempt["output_tokens"])
        self.assertIsNone(attempt["estimated_credits"])
        self.assertNotIn(CANARY, json.dumps(view))

    def test_unknown_failure_strings_do_not_escape(self):
        self.add(1, failure=True)
        self.change_receipt(
            lambda r: r.update(
                error={"code": CANARY, "diagnostics": {"status": CANARY}}
            )
        )
        view = w.collect_workers(self.path)
        self.assertEqual(view["attempts"][0]["error_code"], "unknown")
        self.assertNotIn(CANARY, json.dumps(view))

    def test_mismatched_identity_and_result_hash_are_excluded(self):
        self.add(1)
        self.change_receipt(lambda r: r.update(attempt_id="different"))
        view = w.collect_workers(self.path)
        self.assertEqual(view["attempts"], [])
        self.assertTrue(view["diagnostics"])
        self.assertIsNone(view["budget"]["request_limit"])

    def test_duplicate_ids_are_excluded(self):
        self.add(1)
        self.q.db.executescript("""
            CREATE TABLE copied AS SELECT * FROM jobs;
            DROP TABLE jobs;
            ALTER TABLE copied RENAME TO jobs;
            INSERT INTO jobs SELECT * FROM jobs;
        """)
        view = w.collect_workers(self.path)
        self.assertEqual(view["attempts"], [])
        self.assertIn("duplicate identities; excluded", view["diagnostics"])

    def test_result_hash_mismatch(self):
        self.add(1)
        self.change_receipt(lambda r: r.update(result_sha256="0" * 64))
        self.assertEqual(w.collect_workers(self.path)["attempts"], [])

    def test_running_is_not_liveness(self):
        p = packet()
        self.q.claim(p, "investigator", False)
        view = w.collect_workers(self.path)
        self.assertEqual(view["attempts"][0]["state"], "running")
        self.assertIsNone(view["attempts"][0]["finished_at"])

    def test_oversized_and_malformed_rows(self):
        self.add(1)
        for value in ("x" * (w.MAX_FIELD + 1), "{invalid"):
            with self.subTest(value_length=len(value)):
                self.q.db.execute("UPDATE jobs SET receipt=?", (value,))
                view = w.collect_workers(self.path)
                self.assertEqual(view["attempts"], [])
                self.assertTrue(view["diagnostics"])

    def test_row_and_byte_caps_are_explicit(self):
        self.add(1)
        self.add(2)
        with patch.object(w, "MAX_JOBS", 1):
            view = w.collect_workers(self.path)
        self.assertEqual(view["status"], "truncated")
        self.assertIsNone(view["budget"]["requests_remaining"])
        self.assertEqual(view["accounting"]["coverage"], "partial / lower bounds")
        with patch.object(w, "MAX_SCAN", 1):
            self.assertEqual(w.collect_workers(self.path)["status"], "truncated")

    def test_unexpected_schema_and_permissions(self):
        self.q.db.execute("CREATE TABLE extra (value TEXT)")
        self.assertEqual(w.collect_workers(self.path)["status"], "unavailable")
        self.q.db.execute("DROP TABLE extra")
        os.chmod(self.path / "queue.sqlite3", 0o644)
        self.assertEqual(w.collect_workers(self.path)["status"], "unavailable")

    def test_no_writer_constructor_or_network_for_capture(self):
        self.add(1)
        with (
            patch.object(d.Queue, "__init__", side_effect=AssertionError("writer")),
            patch("socket.socket", side_effect=AssertionError("network")),
        ):
            self.assertEqual(w.collect_workers(self.path)["status"], "available")

    def test_old_snapshot_and_source_failure_independence(self):
        with patch.object(o, "command", side_effect=ValueError("unavailable")):
            snapshot = o.collect(Path("."), "example/repo", "origin/ledger", self.path)
        self.assertEqual(snapshot["workers"]["status"], "available")
        snapshot["schema_version"] = 1
        snapshot.pop("workers")
        self.assertIn("not supplied", o.render(snapshot))
        snapshot["schema_version"] = 99
        with self.assertRaises(ValueError):
            o.render(snapshot)


if __name__ == "__main__":
    unittest.main()
