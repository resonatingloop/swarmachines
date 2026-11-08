"""Offline proofs for explicit submission and persistent session authority bounds."""

import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from control_plane import delegation as d
from control_plane import observer as o
from control_plane import submit as s
from control_plane import worker_projection as w
from control_plane.limits import SESSION
from control_plane.test_delegation import packet


class SubmissionTests(unittest.TestCase):
    """Fictional source/queues; provider and capture traffic are mocked."""

    def setUp(self):
        """Create a tiny pinned git repository and an offline-authorized session."""
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.git("init", "-q")
        (self.repo / "runtime").mkdir()
        (self.repo / "runtime" / "sample.py").write_bytes(
            b"def sample():\r\n    return 42\r\n"
        )
        self.git("add", "runtime/sample.py")
        self.git(
            "-c",
            "user.name=fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "-c",
            "core.hooksPath=/dev/null",
            "commit",
            "-qm",
            "fictional source",
        )
        self.revision = self.git("rev-parse", "HEAD").strip()
        self.session = s.initialize(
            self.root / "sessions",
            "fixture-session",
            "fictional owner instruction",
            "offline verification",
        )
        self.path = Path(self.session["session_path"])
        self.prepared = self.prepare()

    def tearDown(self):
        """Discard private fixtures."""
        self.temp.cleanup()

    def git(self, *args):
        """Run git only against the temporary fixture."""
        return subprocess.check_output(
            ["git", *args], cwd=self.repo, text=True, stderr=subprocess.DEVNULL
        )

    def prepare(self, name="task"):
        """Prepare one stable packet from the committed fictional source."""
        return s.prepare(
            self.repo,
            self.revision,
            "runtime/sample.py",
            name,
            name + "-attempt",
            "inspect the return",
            "one concise answer",
            self.root / name,
        )

    def run_task(self, output="capture", live=False):
        """Invoke the wrapper without adding any hidden budget or retry."""
        return s.run(
            self.path,
            self.session["manifest_sha256"],
            self.prepared["packet_path"],
            self.prepared["packet_sha256"],
            self.repo,
            self.root / output,
            live,
        )

    def test_prepare_ignores_dirty_files_and_preserves_bytes(self):
        (self.repo / "runtime" / "sample.py").write_text("PRIVATE_WORKTREE_CANARY")
        data = self.prepare("dirty-proof")
        p = json.loads(Path(data["packet_path"]).read_text())
        self.assertEqual(p["source"]["text"], "def sample():\r\n    return 42\r\n")
        self.assertNotIn(
            "PRIVATE_WORKTREE_CANARY", Path(data["review_path"]).read_text()
        )
        self.assertEqual(Path(data["packet_path"]).stat().st_mode & 0o777, 0o600)
        self.assertEqual(Path(data["packet_path"]).parent.stat().st_mode & 0o777, 0o700)
        self.assertEqual(d.digest(d.encoded(p)), data["packet_sha256"])

    def test_excerpt_and_invalid_sources(self):
        text, label = s.source_text(self.repo, self.revision, "runtime/sample.py", 2, 2)
        self.assertEqual(text, "    return 42\r\n")
        self.assertIn(":2-2", label)
        for source in (
            "../runtime/sample.py",
            "/runtime/sample.py",
            "runtime/.env",
            "runtime/../sample.py",
            "runtime//sample.py",
        ):
            with self.subTest(source=source), self.assertRaises(ValueError):
                s.source_text(self.repo, self.revision, source)
        for bounds in ((0, 1), (3, 3), (2, 1), (None, 1)):
            with self.subTest(bounds=bounds), self.assertRaises(ValueError):
                s.source_text(self.repo, self.revision, "runtime/sample.py", *bounds)

    def test_symlink_and_oversized_blob_refused(self):
        (self.repo / "runtime" / "alias.py").symlink_to("sample.py")
        (self.repo / "runtime" / "large.py").write_text("x" * (s.MAX_BLOB + 1))
        self.git("add", "runtime")
        self.git(
            "-c",
            "user.name=fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "-c",
            "core.hooksPath=/dev/null",
            "commit",
            "-qm",
            "hostile fixtures",
        )
        rev = self.git("rev-parse", "HEAD").strip()
        for name in ("alias.py", "large.py"):
            with self.assertRaises(ValueError):
                s.source_text(self.repo, rev, "runtime/" + name)

    def test_refuse_existing_outputs_sessions_and_partial_init(self):
        with self.assertRaises(FileExistsError):
            self.prepare()
        with self.assertRaises(FileExistsError):
            s.initialize(self.root / "sessions", "fixture-session", "owner", "test")
        with (
            patch.object(d, "Queue", side_effect=RuntimeError("interrupted")),
            self.assertRaises(RuntimeError),
        ):
            s.initialize(self.root / "sessions", "partial", "owner", "test")
        self.assertTrue((self.root / "sessions" / "partial" / "manifest.json").exists())
        with self.assertRaises(FileExistsError):
            s.initialize(self.root / "sessions", "partial", "owner", "test")

    def test_tampered_packet_refuses_before_claim(self):
        p = Path(self.prepared["packet_path"])
        data = json.loads(p.read_text())
        data["objective"] = "changed"
        p.write_text(json.dumps(data))
        with patch.object(d, "execute") as execute, self.assertRaises(ValueError):
            self.run_task()
        execute.assert_not_called()

    def test_tampered_manifest_and_missing_queue_refuse(self):
        with self.assertRaises(ValueError):
            s.load_manifest(self.path, "0" * 64)
        (self.path / "queue" / "queue.sqlite3").unlink()
        with self.assertRaises(OSError):
            self.run_task()
        self.assertFalse((self.path / "queue" / "queue.sqlite3").exists())

    def test_partial_database_is_not_reinitialized(self):
        database = self.path / "queue" / "queue.sqlite3"
        database.write_bytes(b"")
        with self.assertRaises(ValueError):
            self.run_task()
        self.assertEqual(database.read_bytes(), b"")

    def test_swapped_session_queue_refused(self):
        other = s.initialize(self.root / "sessions", "other", "owner", "test")
        shutil.copyfile(
            Path(other["session_path"]) / "queue" / "queue.sqlite3",
            self.path / "queue" / "queue.sqlite3",
        )
        with self.assertRaises(ValueError):
            self.run_task()

    def test_live_requires_authority_and_credential(self):
        with (
            patch.dict(os.environ, {"ADAPTION_API_KEY": "synthetic-unused"}),
            patch.object(d, "execute") as execute,
            self.assertRaises(ValueError),
        ):
            self.run_task(live=True)
        execute.assert_not_called()

    def test_live_session_with_fake_worker_and_missing_key(self):
        self.session = s.initialize(
            self.root / "sessions",
            "live-fixture",
            "fictional authorization",
            "test live boundary",
            True,
        )
        self.path = Path(self.session["session_path"])
        with patch.dict(os.environ, {}, clear=True), self.assertRaises(ValueError):
            self.run_task(live=True)
        with (
            patch.dict(os.environ, {"ADAPTION_API_KEY": "synthetic-unused"}),
            patch.object(d, "adaption_worker", side_effect=d.offline_worker) as worker,
            patch.object(s, "capture", return_value=True),
        ):
            result, code = self.run_task(live=True)
            replay, _ = self.run_task("another-capture", live=True)
        self.assertEqual(code, 0)
        self.assertEqual(result["state"], "completed")
        self.assertTrue(replay["replayed"])
        self.assertEqual(worker.call_count, 1)

    def test_offline_roundtrip_capture_and_duplicate(self):
        responses = ["a" * 40, "", "[]"]
        with patch.object(o, "command", side_effect=responses):
            result, code = self.run_task()
        self.assertEqual(code, 0)
        self.assertEqual(result["state"], "completed")
        view = json.loads((self.root / "capture" / "snapshot.json").read_text())
        self.assertEqual(view["workers"]["session"]["id"], "fixture-session")
        self.assertEqual(view["workers"]["budget"]["request_limit"], 20)
        self.assertNotIn(
            "inspect the return", (self.root / "capture" / "index.html").read_text()
        )
        with (
            patch.object(s, "capture", return_value=True),
            patch.object(d, "offline_worker", side_effect=AssertionError("duplicate")),
        ):
            replay, code = self.run_task("capture-two")
        self.assertTrue(replay["replayed"])
        self.assertEqual(code, 0)

    def test_capture_failure_does_not_repeat_execution(self):
        calls = Mock(side_effect=d.offline_worker)
        with (
            patch.object(d, "offline_worker", calls),
            patch.object(s, "capture", side_effect=OSError("private-path-canary")),
        ):
            result, code = self.run_task()
            again, second_code = self.run_task("retry-capture")
        self.assertEqual((code, second_code), (3, 3))
        self.assertEqual(calls.call_count, 1)
        self.assertEqual(result["result_sha256"], again["result_sha256"])
        self.assertNotIn("private-path-canary", json.dumps(result))

    def test_same_object_used_after_hash(self):
        original = d.execute

        def intercepted(q, packet_value, worker, live=False):
            Path(self.prepared["packet_path"]).write_text("tampered after inspection")
            return original(q, packet_value, worker, live=live)

        with (
            patch.object(d, "execute", side_effect=intercepted),
            patch.object(s, "capture", return_value=True),
        ):
            result, code = self.run_task()
        self.assertEqual(code, 0)
        self.assertEqual(result["packet_sha256"], self.prepared["packet_sha256"])

    def test_failed_worker_exit_precedes_capture_failure(self):
        with (
            patch.object(d, "offline_worker", side_effect=ValueError("secret-canary")),
            patch.object(s, "capture", return_value=False),
        ):
            result, code = self.run_task()
        self.assertEqual(code, 1)
        self.assertEqual(result["state"], "failed")
        self.assertNotIn("secret-canary", json.dumps(result))

    def test_policy_persists_and_twenty_first_call_is_blocked(self):
        queue = d.Queue(self.path / "queue")
        for number in range(1, 21):
            d.execute(
                queue,
                packet(number),
                "investigator",
                live=True,
                runner=d.offline_worker,
            )
        queue.close()
        queue = d.Queue(self.path / "queue")
        try:
            self.assertEqual(queue.limits, SESSION)
            with self.assertRaises(ValueError):
                d.execute(
                    queue,
                    packet(21),
                    "investigator",
                    live=True,
                    runner=d.offline_worker,
                )
            self.assertEqual(queue.summary()["budget"]["reserved_micro"], 2_000_000)
        finally:
            queue.close()
        view = w.collect_workers(self.path / "queue")
        self.assertEqual(view["budget"]["requests_remaining"], 0)
        self.assertEqual(view["budget"]["reservation_ceiling"], "2")

    def test_old_queue_not_migrated_and_policy_cannot_change(self):
        path = self.root / "legacy"
        q = d.Queue(path)
        q.close()
        before = (path / "queue.sqlite3").read_bytes()
        with self.assertRaises(ValueError):
            d.Queue(path, limits=SESSION)
        self.assertEqual((path / "queue.sqlite3").read_bytes(), before)
        with self.assertRaises(ValueError):
            d.Queue(self.path / "queue", limits={**SESSION, "request_limit": 19})

    def test_cli_metadata_and_capture_only(self):
        argv = [
            "submit",
            "run",
            "--session",
            str(self.path),
            "--manifest-sha256",
            self.session["manifest_sha256"],
            "--packet",
            self.prepared["packet_path"],
            "--packet-sha256",
            self.prepared["packet_sha256"],
            "--repo",
            str(self.repo),
            "--output",
            str(self.root / "cli-capture"),
        ]
        output = io.StringIO()
        with (
            patch.object(sys, "argv", argv),
            patch.object(s, "capture", return_value=True),
            contextlib.redirect_stdout(output),
        ):
            self.assertEqual(s.main(), 0)
        self.assertNotIn("inspect the return", output.getvalue())
        with (
            patch.object(d, "execute", side_effect=AssertionError("must not run")),
            patch.object(o, "command", side_effect=["a" * 40, "", "[]"]),
        ):
            manifest = s.load_manifest(self.path, self.session["manifest_sha256"])
            self.assertTrue(
                s.capture(
                    self.path,
                    manifest,
                    self.session["manifest_sha256"],
                    self.repo,
                    self.root / "recapture",
                )
            )


if __name__ == "__main__":
    unittest.main()
