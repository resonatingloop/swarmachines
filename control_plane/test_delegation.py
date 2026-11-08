"""Offline proofs of assignment, acknowledgment, execution and receipt integrity."""

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

from control_plane import delegation as d


def packet(number=1):
    """Create a fictional task with an explicit hash-bound source."""
    return {
        "schema_version": "v1",
        "emitted_at": "2026-11-07T23:00:00+00:00",
        "task_id": f"proof-{number}",
        "attempt_id": f"attempt-{number}",
        "assigned_worker": "investigator",
        "objective": "inspect this fictional source",
        "expected_deliverable": "a concise finding with evidence",
        "source": {
            "label": "fiction.py",
            "revision": "a" * 40,
            "text": "return True\n",
            "sha256": d.digest("return True\n"),
        },
        "limits": {"max_output_tokens": 100, "max_requests": 1, "timeout_seconds": 30},
    }


class DelegationTests(unittest.TestCase):
    """No real credentials, provider requests or external workers used."""

    def setUp(self):
        """Start an isolated private queue."""
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "state"
        self.queue = d.Queue(self.path)

    def tearDown(self):
        """Close handles and remove synthetic state."""
        self.queue.close()
        self.temp.cleanup()

    def test_complete_roundtrip_and_duplicate_no_execution(self):
        runner = Mock(side_effect=d.offline_worker)
        first, replay = d.execute(self.queue, packet(), "investigator", runner=runner)
        self.assertFalse(replay)
        second, replay = d.execute(self.queue, packet(), "investigator", runner=runner)
        self.assertTrue(replay)
        self.assertEqual(first, second)
        runner.assert_called_once()
        self.assertEqual(first["result_sha256"], d.digest(first["result"]["text"]))
        self.assertEqual(first["packet_hash"], d.digest(d.encoded(packet())))
        self.assertIn("acknowledged_at", first)

    def test_ack_persisted_before_worker_runs(self):
        def run(p):
            with self.queue.db:
                row = self.queue.db.execute("SELECT ack,state FROM jobs").fetchone()
                self.assertEqual(row["state"], "running")
                self.assertEqual(json.loads(row["ack"])["attempt_id"], p["attempt_id"])
            return d.offline_worker(p)

        d.execute(self.queue, packet(), "investigator", runner=run)

    def test_worker_identity_must_match(self):
        with self.assertRaises(ValueError):
            self.queue.claim(packet(), "another-worker", False)
        self.assertEqual(self.queue.summary()["jobs"], [])

    def test_duplicate_active_claim_cannot_run(self):
        self.queue.claim(packet(), "investigator", False)
        with self.assertRaises(ValueError):
            self.queue.claim(packet(), "investigator", False)

    def test_one_slot_across_connections(self):
        other = d.Queue(self.path)
        try:
            self.queue.claim(packet(), "investigator", False)
            with self.assertRaises(ValueError):
                other.claim(packet(2), "investigator", False)
        finally:
            other.close()

    def test_conflicting_packet_cannot_replace_assignment(self):
        d.execute(self.queue, packet(), "investigator")
        changed = packet()
        changed["objective"] = "different objective"
        with self.assertRaises(ValueError):
            self.queue.claim(changed, "investigator", False)

    def test_attempt_collision_cannot_alias_task(self):
        d.execute(self.queue, packet(), "investigator")
        changed = packet(2)
        changed["attempt_id"] = packet()["attempt_id"]
        with self.assertRaises(ValueError):
            self.queue.claim(changed, "investigator", False)

    def test_offline_receipt_cannot_be_live_proof(self):
        d.execute(self.queue, packet(), "investigator")
        with self.assertRaises(ValueError):
            self.queue.claim(packet(), "investigator", True)

    def test_failure_is_sanitized_and_not_retried(self):
        runner = Mock(side_effect=RuntimeError("secret-canary-do-not-emit"))
        receipt, _ = d.execute(
            self.queue, packet(), "investigator", live=True, runner=runner
        )
        self.assertEqual(receipt["state"], "failed")
        self.assertNotIn("secret-canary", d.encoded(receipt))
        d.execute(self.queue, packet(), "investigator", live=True, runner=runner)
        runner.assert_called_once()
        self.assertEqual(self.queue.summary()["budget"]["requests"], 1)

    def test_crash_leaves_reconciliation_required(self):
        with self.assertRaises(KeyboardInterrupt):
            d.execute(
                self.queue,
                packet(),
                "investigator",
                live=True,
                runner=Mock(side_effect=KeyboardInterrupt()),
            )
        self.assertEqual(self.queue.summary()["jobs"][0]["state"], "running")
        with self.assertRaises(ValueError):
            self.queue.claim(packet(2), "investigator", True)

    def test_budget_persists_and_blocks_fifth_request(self):
        for n in range(4):
            d.execute(
                self.queue,
                packet(n),
                "investigator",
                live=True,
                runner=d.offline_worker,
            )
        self.queue.close()
        self.queue = d.Queue(self.path)
        with self.assertRaises(ValueError):
            self.queue.claim(packet(5), "investigator", True)
        self.assertEqual(self.queue.summary()["budget"]["requests"], 4)
        self.assertEqual(self.queue.summary()["budget"]["reserved_micro"], 400000)

    def test_credit_limit_independent_of_request_limit(self):
        self.queue.db.execute("UPDATE budget SET reserved_micro=1000000")
        with self.assertRaises(ValueError):
            self.queue.claim(packet(), "investigator", True)

    def test_stale_claim_cannot_write_receipt(self):
        token, _ = self.queue.claim(packet(), "investigator", False)
        with self.assertRaises(ValueError):
            self.queue.finish(packet(), "wrong-token", d.offline_worker(packet()))
        self.queue.finish(packet(), token, d.offline_worker(packet()))
        with self.assertRaises(ValueError):
            self.queue.finish(packet(), token, d.offline_worker(packet()))

    def test_invalid_packet_rejected(self):
        for field, value in [
            ("limits", {"max_output_tokens": 999999}),
            ("schema_version", True),
            ("tools", ["shell"]),
        ]:
            p = packet()
            p[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                d.validate(p)
        p = packet()
        p["source"]["text"] = "tampered"
        with self.assertRaises(ValueError):
            d.validate(p)
        p["source"]["text"] = "x" * 25000
        with self.assertRaises(ValueError):
            d.validate(p)

    def test_state_permissions_and_symlink_refusal(self):
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o700)
        self.assertEqual((self.path / "queue.sqlite3").stat().st_mode & 0o777, 0o600)
        link = Path(self.temp.name) / "link"
        link.symlink_to(self.path)
        with self.assertRaises(ValueError):
            d.Queue(link)

    def test_sdk_bounds_no_tools_no_fallback(self):
        client = MagicMock()
        client.responses.create.return_value = SimpleNamespace(
            status="completed",
            output_text="advisory finding",
            model=d.MODEL,
            usage=SimpleNamespace(input_tokens=10, output_tokens=5),
        )
        sdk = MagicMock()
        sdk.Adaption.return_value.__enter__.return_value = client
        transport = MagicMock()
        with patch.dict("sys.modules", {"adaption": sdk, "httpx": transport}):
            result = d.adaption_worker(packet())
        options = sdk.Adaption.call_args.kwargs
        self.assertEqual(options["max_retries"], 0)
        self.assertEqual(options["base_url"], "https://api.prod.adaptionlabs.ai")
        self.assertNotIn("api_key", options)
        transport.Client.assert_called_once_with(follow_redirects=False, timeout=30)
        args = client.responses.create.call_args.kwargs
        self.assertEqual(args["tools"], [])
        self.assertFalse(args["store"])
        self.assertEqual(args["max_output_tokens"], 100)
        self.assertEqual(result["usage"], {"input_tokens": 10, "output_tokens": 5})
        self.assertIsNone(result["observed_credits"])

    def test_failure_diagnostics_are_bounded_and_persisted(self):
        response = SimpleNamespace(
            status="incomplete",
            usage=SimpleNamespace(input_tokens=12, output_tokens=100),
        )

        def worker(p):
            raise d.ProviderResponseError(
                "response_not_completed", d.response_diagnostics(response)
            )

        receipt, _ = d.execute(self.queue, packet(), "investigator", runner=worker)
        self.assertEqual(receipt["error"]["code"], "response_not_completed")
        self.assertEqual(receipt["usage"], {"input_tokens": 12, "output_tokens": 100})
        response.status = "secret-canary"
        response.usage = SimpleNamespace(
            input_tokens=True, output_tokens="secret-canary"
        )
        diagnostics = d.response_diagnostics(response)
        self.assertNotIn("secret-canary", d.encoded(diagnostics))
        self.assertEqual(diagnostics["status"], "unknown")
        self.assertEqual(
            diagnostics["usage"], {"input_tokens": None, "output_tokens": None}
        )

    def test_incomplete_response_is_failure(self):
        client = MagicMock()
        client.responses.create.return_value = SimpleNamespace(
            status="incomplete", output_text="partial"
        )
        sdk = MagicMock()
        sdk.Adaption.return_value.__enter__.return_value = client
        with (
            patch.dict("sys.modules", {"adaption": sdk, "httpx": MagicMock()}),
            self.assertRaises(ValueError),
        ):
            d.adaption_worker(packet())

    def test_incomplete_response_keeps_bounded_diagnostics_channel(self):
        """The failure path must still carry fixed codes and bounded diagnostics."""
        client = MagicMock()
        client.responses.create.return_value = SimpleNamespace(
            status="incomplete", output_text="partial"
        )
        sdk = MagicMock()
        sdk.Adaption.return_value.__enter__.return_value = client
        with (
            patch.dict("sys.modules", {"adaption": sdk, "httpx": MagicMock()}),
            self.assertRaises(d.ProviderResponseError) as caught,
        ):
            d.adaption_worker(packet())
        self.assertEqual(caught.exception.code, "response_not_completed")
        self.assertEqual(caught.exception.diagnostics["status"], "incomplete")

    def test_hostile_model_string_records_as_unknown(self):
        """Hostile/garbage model strings must not flow into persisted receipts."""
        for hostile_model in [
            "glm-53-flash\ninjected",  # newline injection
            "glm-53-flash\x00\x1f",  # unicode control chars
            "x" * 250,  # >200 chars
            "gpt-4",  # different model
            "",  # empty
            "<script>alert(1)</script>",  # XSS attempt
        ]:
            client = MagicMock()
            client.responses.create.return_value = SimpleNamespace(
                status="completed",
                output_text="advisory finding",
                model=hostile_model,
                usage=SimpleNamespace(input_tokens=10, output_tokens=5),
            )
            sdk = MagicMock()
            sdk.Adaption.return_value.__enter__.return_value = client
            with patch.dict("sys.modules", {"adaption": sdk, "httpx": MagicMock()}):
                result = d.adaption_worker(packet())
            self.assertEqual(
                result["model"],
                "unknown",
                f"hostile model {hostile_model!r} should be sanitized",
            )

    def test_valid_model_records_correctly(self):
        """The fixed MODEL constant should be recorded verbatim."""
        client = MagicMock()
        client.responses.create.return_value = SimpleNamespace(
            status="completed",
            output_text="advisory finding",
            model=d.MODEL,
            usage=SimpleNamespace(input_tokens=10, output_tokens=5),
        )
        sdk = MagicMock()
        sdk.Adaption.return_value.__enter__.return_value = client
        with patch.dict("sys.modules", {"adaption": sdk, "httpx": MagicMock()}):
            result = d.adaption_worker(packet())
        self.assertEqual(result["model"], d.MODEL)

    def test_usage_float_coerced_to_null(self):
        """Float usage values must be coerced to None."""
        client = MagicMock()
        client.responses.create.return_value = SimpleNamespace(
            status="completed",
            output_text="advisory finding",
            model=d.MODEL,
            usage=SimpleNamespace(input_tokens=10.5, output_tokens=5.0),
        )
        sdk = MagicMock()
        sdk.Adaption.return_value.__enter__.return_value = client
        with patch.dict("sys.modules", {"adaption": sdk, "httpx": MagicMock()}):
            result = d.adaption_worker(packet())
        self.assertEqual(result["usage"], {"input_tokens": None, "output_tokens": None})
        self.assertIsNone(result["estimated_credits"])

    def test_usage_oversized_coerced_to_null(self):
        """Usage values above MAX_USAGE_TOKENS must be coerced to None."""
        client = MagicMock()
        client.responses.create.return_value = SimpleNamespace(
            status="completed",
            output_text="advisory finding",
            model=d.MODEL,
            usage=SimpleNamespace(input_tokens=d.MAX_USAGE_TOKENS + 1, output_tokens=5),
        )
        sdk = MagicMock()
        sdk.Adaption.return_value.__enter__.return_value = client
        with patch.dict("sys.modules", {"adaption": sdk, "httpx": MagicMock()}):
            result = d.adaption_worker(packet())
        self.assertEqual(result["usage"], {"input_tokens": None, "output_tokens": 5})
        self.assertIsNone(result["estimated_credits"])

    def test_usage_negative_coerced_to_null(self):
        """Negative usage values must be coerced to None."""
        client = MagicMock()
        client.responses.create.return_value = SimpleNamespace(
            status="completed",
            output_text="advisory finding",
            model=d.MODEL,
            usage=SimpleNamespace(input_tokens=-1, output_tokens=5),
        )
        sdk = MagicMock()
        sdk.Adaption.return_value.__enter__.return_value = client
        with patch.dict("sys.modules", {"adaption": sdk, "httpx": MagicMock()}):
            result = d.adaption_worker(packet())
        self.assertEqual(result["usage"], {"input_tokens": None, "output_tokens": 5})

    def test_usage_boundary_values_accepted(self):
        """Boundary values 0 and MAX_USAGE_TOKENS should be accepted."""
        client = MagicMock()
        client.responses.create.return_value = SimpleNamespace(
            status="completed",
            output_text="advisory finding",
            model=d.MODEL,
            usage=SimpleNamespace(input_tokens=0, output_tokens=d.MAX_USAGE_TOKENS),
        )
        sdk = MagicMock()
        sdk.Adaption.return_value.__enter__.return_value = client
        with patch.dict("sys.modules", {"adaption": sdk, "httpx": MagicMock()}):
            result = d.adaption_worker(packet())
        self.assertEqual(
            result["usage"], {"input_tokens": 0, "output_tokens": d.MAX_USAGE_TOKENS}
        )

    def test_usage_partial_validity_keeps_valid_channel_without_cost(self):
        """One invalid token channel must not erase the other or crash costing."""
        client = MagicMock()
        client.responses.create.return_value = SimpleNamespace(
            status="completed",
            output_text="advisory finding",
            model=d.MODEL,
            usage=SimpleNamespace(input_tokens=10, output_tokens=None),
        )
        sdk = MagicMock()
        sdk.Adaption.return_value.__enter__.return_value = client
        with patch.dict("sys.modules", {"adaption": sdk, "httpx": MagicMock()}):
            result = d.adaption_worker(packet())
        self.assertEqual(result["usage"], {"input_tokens": 10, "output_tokens": None})
        self.assertIsNone(result["estimated_credits"])


if __name__ == "__main__":
    unittest.main()
