"""Offline regression tests for observation boundaries and claim preservation."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from control_plane import observer as o

REV = "a" * 40
PR = {
    "number": 8,
    "title": "adapter",
    "state": "MERGED",
    "headRefOid": REV,
    "updatedAt": "2026-11-07T22:00:00Z",
}
LINE = "- [doing] T-005: PR #8 smoke — owner: maker — updated: 2026-11-07T21:00Z"


class ObserverTests(unittest.TestCase):
    """Exercise missing, contradictory and hostile source evidence."""

    def capture(self, ledger=LINE, prs=None):
        """Collect a synthetic snapshot with real parsing and no external calls."""
        responses = [REV, ledger, json.dumps([PR] if prs is None else prs)]
        with patch.object(o, "command", side_effect=responses):
            return o.collect(Path("."), "example/project", "origin/ledger")

    def test_merged_reference_does_not_close_task(self):
        snapshot = self.capture()
        self.assertEqual(snapshot["tasks"][0]["reported_state"], "doing")
        self.assertIn("do not auto-close", snapshot["diagnostics"][0])

    def test_duplicate_ids_are_excluded(self):
        tasks, issues = o.parse_ledger(LINE + "\n" + LINE.replace("[doing]", "[done]"))
        self.assertEqual(tasks, [])
        self.assertIn("duplicate", issues[-1])

    def test_historical_missing_timestamp_visible(self):
        tasks, issues = o.parse_ledger("- [done] T-001: old task — owner: maker")
        self.assertIsNone(tasks[0]["updated_at"])
        self.assertTrue(issues)

    def test_invalid_timestamp_is_not_fresh(self):
        tasks, issues = o.parse_ledger(LINE.replace("2026-11-07T21:00Z", "tomorrow"))
        self.assertIsNone(tasks[0]["updated_at"])
        self.assertTrue(issues)

    def test_unsupported_group_row_not_silently_counted(self):
        tasks, issues = o.parse_ledger("- [done] T-001, T-002: grouped — owner: maker")
        self.assertEqual(tasks, [])
        self.assertIn("not counted", issues[0])

    def test_incomplete_pr_collection_is_explicit(self):
        prs = [{**PR, "number": n} for n in range(1, o.PR_LIMIT + 1)]
        snapshot = self.capture(prs=prs)
        self.assertEqual(
            snapshot["sources"]["github"]["coverage"], "possibly truncated"
        )

    def test_absent_pr_is_unknown(self):
        snapshot = self.capture(prs=[])
        self.assertIn("state unknown", snapshot["diagnostics"][0])

    def test_source_failures_are_independent(self):
        with patch.object(
            o, "command", side_effect=[ValueError("secret"), json.dumps([PR])]
        ):
            snapshot = o.collect(Path("."), "example/project", "origin/ledger")
        self.assertEqual(snapshot["sources"]["ledger"]["status"], "unavailable")
        self.assertEqual(len(snapshot["prs"]), 1)
        self.assertNotIn("secret", json.dumps(snapshot))
        self.assertIn("<span>?</span>", o.render(snapshot))

    def test_github_failure_keeps_task_claims(self):
        with patch.object(o, "command", side_effect=[REV, LINE, ValueError("secret")]):
            snapshot = o.collect(Path("."), "example/project", "origin/ledger")
        self.assertEqual(len(snapshot["tasks"]), 1)
        self.assertEqual(snapshot["sources"]["github"]["status"], "unavailable")

    def test_hostile_titles_are_text_not_markup(self):
        hostile = "<script>alert(1)</script>&#x202e;\u202e@@lanes@@"
        snapshot = self.capture(ledger=LINE.replace("PR #8 smoke", hostile))
        rendered = o.render(snapshot)
        self.assertNotIn("<script>", rendered)
        self.assertNotIn("\u202e", rendered)
        self.assertIn("&lt;script&gt;", rendered)
        self.assertIn("&amp;#x202e;", rendered)
        self.assertIn("\\u202e", rendered)
        self.assertIn("@@lanes@@", rendered)

    def test_invalid_prs_rejected(self):
        for prs in (
            [PR, PR],
            [{**PR, "number": True}],
            [{**PR, "state": "APPROVED"}],
            [{**PR, "headRefOid": "<script>"}],
            [{**PR, "title": None}],
        ):
            with self.subTest(prs=prs), self.assertRaises(ValueError):
                o.validate_prs(prs)

    def test_input_bounds(self):
        with self.assertRaises(ValueError):
            o.parse_ledger("x" * (o.MAX_BYTES + 1))

    def test_ref_and_repo_cannot_be_command_options(self):
        with patch.object(o, "command") as command:
            for repo, ref in [
                ("example/project", "--help"),
                ("--help", "origin/ledger"),
            ]:
                with self.assertRaises(ValueError):
                    o.collect(Path("."), repo, ref)
            command.assert_not_called()

    def test_collector_only_runs_read_operations(self):
        with patch.object(
            o, "command", side_effect=[REV, LINE, json.dumps([PR])]
        ) as command:
            o.collect(Path("."), "example/project", "origin/ledger")
        args = [call.args[0] for call in command.call_args_list]
        self.assertEqual(
            [arg[:2] for arg in args],
            [["git", "rev-parse"], ["git", "show"], ["gh", "pr"]],
        )
        self.assertEqual(args[1][2], REV + ":TASKS.md")
        self.assertEqual(args[2][2], "list")

    def test_private_output_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as parent:
            output = Path(parent) / "capture"
            with (
                patch("sys.argv", ["observer", "--output", str(output)]),
                patch.object(o, "collect", return_value=self.capture()),
            ):
                self.assertEqual(o.main(), 0)
                self.assertEqual(output.stat().st_mode & 0o777, 0o700)
                self.assertEqual(
                    (output / "snapshot.json").stat().st_mode & 0o777, 0o600
                )
                with self.assertRaises(FileExistsError):
                    o.main()


if __name__ == "__main__":
    unittest.main()
