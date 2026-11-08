"""Offline regression proof for smoke outcomes and attempted-call accounting."""

import contextlib
import io
import os
import runpy
import sys
import unittest
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

SCRIPT = Path(__file__).with_name("test_adaption_smoke.py")


class FakeProviderError(Exception):
    """Represent a provider failure without importing or contacting an SDK."""


class SmokeOutcomeTests(unittest.TestCase):
    """Exercise each failure position and the CLI's observable exit status."""

    def run_case(self, failures=(), cli=False):
        """Run with synthetic modules; return outcome and attempted calls."""
        calls = []

        class Adapter:
            def simple_prompt(self, **kwargs):
                calls.append(kwargs)
                if len(calls) in failures:
                    raise FakeProviderError("private exception canary")
                return SimpleNamespace(
                    model=kwargs["model"],
                    output_text="fixture",
                    latency_ms=0,
                    usage=SimpleNamespace(input_tokens=0, output_tokens=0),
                    raw_response=SimpleNamespace(),
                )

        sdk = ModuleType("adaption")
        sdk.AdaptionError = FakeProviderError
        adapter = ModuleType("adaption_adapter")
        adapter.AdaptionAdapter = Adapter
        stdout, stderr = io.StringIO(), io.StringIO()
        with (
            patch.dict(sys.modules, {"adaption": sdk, "adaption_adapter": adapter}),
            patch.dict(os.environ, {"ADAPTION_API_KEY": "synthetic-unused"}),
            contextlib.redirect_stdout(stdout),
            contextlib.redirect_stderr(stderr),
        ):
            if cli:
                with self.assertRaises(SystemExit) as exited:
                    runpy.run_path(str(SCRIPT), run_name="__main__")
                result = exited.exception.code
            else:
                result = runpy.run_path(str(SCRIPT))["run_smoke_test"]()
        self.assertNotIn(
            "private exception canary",
            str(result) + stdout.getvalue() + stderr.getvalue(),
        )
        return result, len(calls)

    def test_each_failure_is_error_and_counts_attempts(self):
        for position in range(1, 5):
            with self.subTest(position=position):
                result, attempts = self.run_case((position,))
                self.assertEqual(result["status"], "error")
                self.assertEqual(result["calls_made"], attempts)
                self.assertEqual(attempts, 1 if position == 1 else 4)

    def test_all_success(self):
        result, attempts = self.run_case()
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["calls_made"], attempts)
        self.assertEqual(attempts, 4)

    def test_multiple_later_failures_keep_all_rows(self):
        result, attempts = self.run_case((2, 3, 4))
        self.assertEqual(result["status"], "error")
        self.assertEqual(attempts, 4)
        self.assertEqual(sum("error" in row for row in result["results"]), 3)

    def test_cli_exit_status(self):
        for failures in ((), (1,), (2,), (3,), (4,)):
            with self.subTest(failures=failures):
                code, _ = self.run_case(failures, cli=True)
                self.assertEqual(code, 1 if failures else 0)

    def test_no_key_skips_sdk_and_cli_exits_blocked(self):
        with (
            patch.dict(os.environ, {}, clear=True),
            patch.dict(sys.modules, {"adaption": None}),
        ):
            result = runpy.run_path(str(SCRIPT))["run_smoke_test"]()
            self.assertEqual(result["status"], "blocked")
            self.assertEqual(result["calls_made"], 0)
            with (
                contextlib.redirect_stdout(io.StringIO()),
                contextlib.redirect_stderr(io.StringIO()),
                self.assertRaises(SystemExit) as exited,
            ):
                runpy.run_path(str(SCRIPT), run_name="__main__")
            self.assertEqual(exited.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
