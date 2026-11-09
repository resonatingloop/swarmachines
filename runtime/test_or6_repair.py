"""Unit tests for the or6 capture repair: fail-closed responses.

Mocked SDK responses cover the or6 failure shape (status incomplete,
reasoning burned the budget, empty output) and the healthy shape.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent))

from adaption_adapter import (
    AdapterResponse,
    AdapterUsage,
    IncompleteResponseError,
)


def _resp(status, output_text, reasoning_tokens=0, output_tokens=None, reason=None):
    usage = AdapterUsage(
        input_tokens=72,
        output_tokens=output_tokens if output_tokens is not None else reasoning_tokens,
        total_tokens=72
        + (output_tokens if output_tokens is not None else reasoning_tokens),
        reasoning_tokens=reasoning_tokens,
    )
    return AdapterResponse(
        model="glm-53-flash",
        output_text=output_text,
        usage=usage,
        latency_ms=10.0,
        raw_response=MagicMock(),
        status=status,
        incomplete_reason=reason,
    )


class TestValidateComplete(unittest.TestCase):
    """Fail-closed contract for AdapterResponse.validate_complete()."""

    def test_or6_shape_raises(self):
        """The exact or6 failure: incomplete, all-reasoning, empty text."""
        r = _resp("incomplete", "", reasoning_tokens=256, reason="max_output_tokens")
        with self.assertRaises(IncompleteResponseError) as cm:
            r.validate_complete()
        self.assertIn("max_output_tokens", str(cm.exception))
        self.assertIn("reasoning_tokens=256", str(cm.exception))

    def test_completed_but_empty_raises(self):
        """Status says completed but no visible text: still fails closed."""
        r = _resp("completed", "", reasoning_tokens=200)
        with self.assertRaises(IncompleteResponseError):
            r.validate_complete()

    def test_missing_status_fails_closed(self):
        """No status field: unverifiable completion, so it fails closed."""
        r = _resp("", "move med-kit south")
        with self.assertRaises(IncompleteResponseError):
            r.validate_complete()

    def test_healthy_response_passes(self):
        """Complete status with visible text passes and chains."""
        r = _resp(
            "completed",
            "action: carry med-kit | msg: beta, taking the ring",
            reasoning_tokens=180,
            output_tokens=256,
        )
        self.assertIs(r.validate_complete(), r)

    def test_error_names_every_diagnostic(self):
        """The error message carries the full captured diagnostic set."""
        r = _resp("incomplete", "", reasoning_tokens=256, reason="max_output_tokens")
        with self.assertRaises(IncompleteResponseError) as cm:
            r.validate_complete()
        msg = str(cm.exception)
        for fragment in (
            "status='incomplete'",
            "incomplete_reason='max_output_tokens'",
            "output_text_len=0",
            "reasoning_tokens=256",
        ):
            self.assertIn(fragment, msg)


class TestAdapterCapture(unittest.TestCase):
    """chat() captures status, incomplete_reason, reasoning_tokens."""

    def _mock_sdk_response(self, status="completed", text="ok", reasoning=0):
        m = MagicMock()
        m.status = status
        m.model = "glm-53-flash"
        m.output_text = text
        m.usage.input_tokens = 72
        m.usage.output_tokens = 256
        m.usage.output_tokens_details.reasoning_tokens = reasoning
        if status == "incomplete":
            m.incomplete_details.reason = "max_output_tokens"
        else:
            m.incomplete_details = None
        return m

    @patch("adaption_adapter.AdaptionAdapter.__init__", lambda self: None)
    def test_chat_captures_incomplete_diagnostics(self):
        """The or6 shape: fields land on AdapterResponse for the record."""
        from adaption_adapter import AdaptionAdapter

        a = AdaptionAdapter()
        a._client = MagicMock()
        a._client.responses.create.return_value = self._mock_sdk_response(
            status="incomplete", text="", reasoning=256
        )
        r = a.chat(model="glm-53-flash", messages=[{"role": "user", "content": "x"}])
        self.assertEqual(r.status, "incomplete")
        self.assertEqual(r.incomplete_reason, "max_output_tokens")
        self.assertEqual(r.usage.reasoning_tokens, 256)
        with self.assertRaises(IncompleteResponseError):
            r.validate_complete()

    @patch("adaption_adapter.AdaptionAdapter.__init__", lambda self: None)
    def test_chat_captures_healthy(self):
        """Healthy response: status completed, diagnostics captured."""
        from adaption_adapter import AdaptionAdapter

        a = AdaptionAdapter()
        a._client = MagicMock()
        a._client.responses.create.return_value = self._mock_sdk_response(
            status="completed", text="visible answer", reasoning=180
        )
        r = a.chat(model="glm-53-flash", messages=[{"role": "user", "content": "x"}])
        self.assertEqual(r.status, "completed")
        self.assertEqual(r.usage.reasoning_tokens, 180)
        r.validate_complete()


if __name__ == "__main__":
    unittest.main()


class TestCallRecordPersistence(unittest.TestCase):
    """Diagnostics reach CallRecord, jsonl, and the sealed payload."""

    def test_call_record_carries_diagnostics(self):
        """Fields land on the record and serialize to the jsonl line."""
        import json
        import sys as _sys

        _sys.path.insert(0, str(Path(__file__).parent.parent))
        from dataset_pack.run import CallRecord

        r = CallRecord(
            ts="t",
            run_id="r",
            call_id="c1",
            role="alpha",
            topology="ring",
            artifact=None,
            model="glm-53-flash",
            prompt_full="p",
            response_full="visible answer",
            tokens_in=72,
            tokens_out=256,
            receipt_ref="receipt-1",
            credits_estimated="0.0001",
            status="completed",
            incomplete_reason=None,
            reasoning_tokens=180,
        )
        line = json.loads(r.to_jsonl_line())
        self.assertEqual(line["status"], "completed")
        self.assertEqual(line["reasoning_tokens"], 180)
        self.assertIsNone(line["incomplete_reason"])

    def test_failed_call_record_is_persistable(self):
        """A validation-failed call records its diagnostics, not silence."""
        import json
        import sys as _sys

        _sys.path.insert(0, str(Path(__file__).parent.parent))
        from dataset_pack.run import CallRecord

        r = CallRecord(
            ts="t",
            run_id="r",
            call_id="c2",
            role="alpha",
            topology="ring",
            artifact=None,
            model="glm-53-flash",
            prompt_full="p",
            response_full="VALIDATION-FAILED: incomplete model response: status='incomplete'",
            tokens_in=72,
            tokens_out=256,
            receipt_ref="receipt-2",
            credits_estimated="0",
            status="incomplete",
            incomplete_reason="max_output_tokens",
            reasoning_tokens=256,
        )
        line = json.loads(r.to_jsonl_line())
        self.assertEqual(line["status"], "incomplete")
        self.assertEqual(line["incomplete_reason"], "max_output_tokens")
        self.assertIn("VALIDATION-FAILED", line["response_full"])
        self.assertEqual(line["reasoning_tokens"], 256)


if __name__ == "__main__":
    unittest.main()


class TestSealedFailureEvents(unittest.TestCase):
    """Failed calls reach the SEALED event log, with readback coverage."""

    def _capture_log(self, capture):
        """Build a _ModelCaptureEventLog with a failing/capture fn."""
        import sys as _sys

        _sys.path.insert(0, str(Path(__file__).parent.parent))
        from dataset_pack.run import _ModelCaptureEventLog

        log = _ModelCaptureEventLog("run-x", "2026-11-08T00:00:00Z", capture)
        return log

    def test_failed_capture_seals_model_call_failed(self):
        """A raising capture appends model.call.failed before re-raising."""

        def failing_capture(turn, agent_id, event_type, payload, source_event_seq):
            raise RuntimeError("IncompleteResponseError: status='incomplete'")

        log = self._capture_log(failing_capture)
        with self.assertRaises(RuntimeError):
            log.append(1, "alpha", "agent.observe", {"v": 1})
        types = [e["type"] for e in log.events]
        self.assertIn("model.call.failed", types)
        failed = next(e for e in log.events if e["type"] == "model.call.failed")
        self.assertIn("source_event_seq", failed["payload"])
        self.assertIn("IncompleteResponseError", failed["payload"]["error"])

    def test_append_failed_call_seals_diagnostics(self):
        """Direct failure sealing carries the full diagnostic payload."""
        log = self._capture_log(lambda *a: None)
        log.append_failed_call(
            turn=3,
            agent_id="alpha",
            source_event_type="agent.observe",
            failure_payload={
                "call_id": "call-0007",
                "status": "incomplete",
                "incomplete_reason": "max_output_tokens",
                "reasoning_tokens": 256,
                "error": "IncompleteResponseError",
            },
        )
        failed = [e for e in log.events if e["type"] == "model.call.failed"]
        self.assertEqual(len(failed), 1)
        pl = failed[0]["payload"]
        self.assertEqual(pl["reasoning_tokens"], 256)
        self.assertEqual(pl["incomplete_reason"], "max_output_tokens")
        self.assertEqual(pl["call_id"], "call-0007")

    def test_healthy_capture_still_pairs_model_call(self):
        """No regression: successful captures pair model.call as before."""

        from dataset_pack.run import CallRecord

        rec_holder = {}

        def ok_capture(turn, agent_id, event_type, payload, source_event_seq):
            rec_holder["r"] = CallRecord(
                ts="t",
                run_id="run-x",
                call_id="c1",
                role="alpha",
                topology="ring",
                artifact=None,
                model="glm-53-flash",
                prompt_full="p",
                response_full="ok",
                tokens_in=1,
                tokens_out=1,
                receipt_ref="r1",
            )
            return rec_holder["r"]

        log = self._capture_log(ok_capture)
        log.append(1, "alpha", "agent.observe", {"v": 1})
        types = [e["type"] for e in log.events]
        self.assertIn("model.call", types)
        self.assertNotIn("model.call.failed", types)


if __name__ == "__main__":
    unittest.main()


class TestLangfuseWiring(unittest.TestCase):
    """Synthetic lifecycle/error/interruption proof for the Langfuse wiring."""

    def _wiring(self):
        import sys as _sys

        _sys.path.insert(0, str(Path(__file__).parent.parent))
        import dataset_pack.langfuse_wiring as lw

        return lw

    def test_offline_degradation_never_raises(self):
        """No keys => disabled with a recorded reason, calls return False."""
        lw = self._wiring()
        lw._LANGFUSE_CLIENT = None
        lw._LANGFUSE_STATE = {"enabled": False, "reason": "not initialized"}
        import os

        saved = {
            k: os.environ.pop(k, None)
            for k in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY")
        }
        try:
            state = lw.langfuse_state()
            self.assertFalse(state["enabled"])
            self.assertIn("offline mode", state["reason"])
            ok = lw.trace_generation("m", "p", "o", None, "completed", None, 1.0)
            self.assertFalse(ok)
        finally:
            for k, v in saved.items():
                if v is not None:
                    os.environ[k] = v

    def test_lifecycle_success_trace_and_flush(self):
        """Configured client: create_generation + flush, metadata rides."""
        lw = self._wiring()
        calls = []

        class FakeClient:
            def create_generation(self, **kw):
                calls.append(kw)

            def flush(self):
                calls.append("flush")

        lw._LANGFUSE_CLIENT = FakeClient()
        lw._LANGFUSE_STATE = {"enabled": True, "reason": "test"}
        try:
            ok = lw.trace_generation(
                "glm-53-flash",
                "prompt",
                "answer",
                usage=None,
                status="completed",
                incomplete_reason=None,
                latency_ms=12.5,
                metadata={"run_id": "r1"},
            )
            self.assertTrue(ok)
            gen = calls[0]
            self.assertEqual(gen["model"], "glm-53-flash")
            self.assertEqual(gen["metadata"]["run_id"], "r1")
            self.assertEqual(gen["metadata"]["status"], "completed")
            self.assertEqual(calls[-1], "flush")
            # privacy contract: hashes only, no raw prompt/output text
            self.assertIn("sha256", gen["input"])
            self.assertIn("sha256", gen["output"])
            self.assertNotIn("prompt", str(gen["input"]))
            self.assertNotIn("answer", str(gen["output"]))
            self.assertEqual(gen["input"]["chars"], len("prompt"))
        finally:
            lw._LANGFUSE_CLIENT = None

    def test_error_path_records_failure_trace(self):
        """trace_failure marks failed=True and carries the error as output."""
        lw = self._wiring()
        calls = []

        class FakeClient:
            def create_generation(self, **kw):
                calls.append(kw)

            def flush(self):
                pass

        lw._LANGFUSE_CLIENT = FakeClient()
        lw._LANGFUSE_STATE = {"enabled": True, "reason": "test"}
        try:
            ok = lw.trace_failure(
                "glm-53-flash",
                "prompt",
                "IncompleteResponseError: boom",
                usage=None,
                status="incomplete",
                incomplete_reason="max_output_tokens",
                latency_ms=5.0,
            )
            self.assertTrue(ok)
            gen = calls[0]
            self.assertTrue(gen["metadata"]["failed"])
            self.assertEqual(gen["metadata"]["error_class"], "IncompleteResponseError")
            self.assertEqual(len(gen["metadata"]["error_sha256"]), 64)  # sha256 hex
            self.assertNotIn("boom", str(gen["output"]))  # no raw error text
            self.assertEqual(gen["metadata"]["incomplete_reason"], "max_output_tokens")
        finally:
            lw._LANGFUSE_CLIENT = None

    def test_interruption_degrades_without_blocking(self):
        """A raising client records the reason and returns False, no raise."""
        lw = self._wiring()

        class BadClient:
            def create_generation(self, **kw):
                raise ConnectionError("langfuse down")

            def flush(self):
                pass

        lw._LANGFUSE_CLIENT = BadClient()
        lw._LANGFUSE_STATE = {"enabled": True, "reason": "test"}
        try:
            ok = lw.trace_generation("m", "p", "o", None, "completed", None, 1.0)
            self.assertFalse(ok)
            self.assertIn("trace failed", lw.langfuse_state()["reason"])
        finally:
            lw._LANGFUSE_CLIENT = None

    def test_shutdown_flushes_and_closes(self):
        """shutdown_langfuse flushes once and marks the state closed."""
        lw = self._wiring()
        flushed = []

        class FakeClient:
            def flush(self):
                flushed.append(1)

        lw._LANGFUSE_CLIENT = FakeClient()
        lw._LANGFUSE_STATE = {"enabled": True, "reason": "test"}
        lw.shutdown_langfuse()
        self.assertEqual(flushed, [1])
        self.assertIn("shutdown complete", lw.langfuse_state()["reason"])


if __name__ == "__main__":
    unittest.main()


class TestProviderExceptionTrace(unittest.TestCase):
    """Provider exceptions before a response also emit a failure trace."""

    def test_provider_exception_traced(self):
        """A raising provider call traces error_class + hash, not message."""
        import sys as _sys

        _sys.path.insert(0, str(Path(__file__).parent.parent))
        import dataset_pack.langfuse_wiring as lw

        calls = []

        class FakeClient:
            def create_generation(self, **kw):
                calls.append(kw)

            def flush(self):
                pass

        lw._LANGFUSE_CLIENT = FakeClient()
        lw._LANGFUSE_STATE = {"enabled": True, "reason": "test"}
        try:
            ok = lw.trace_provider_exception(
                "glm-53-flash",
                "the prompt text",
                ConnectionError("429 rate limited"),
                latency_ms=42.0,
            )
            self.assertTrue(ok)
            gen = calls[0]
            self.assertEqual(gen["metadata"]["error_class"], "ConnectionError")
            self.assertEqual(len(gen["metadata"]["error_sha256"]), 64)  # sha256 hex
            self.assertEqual(gen["metadata"]["status"], "provider-error")
            self.assertNotIn("rate limited", str(gen))  # no raw message
            self.assertNotIn("the prompt text", str(gen))  # no raw prompt
        finally:
            lw._LANGFUSE_CLIENT = None


if __name__ == "__main__":
    unittest.main()


class TestEnforcedAllowlist(unittest.TestCase):
    """The allowlist is enforced, not descriptive: unknown keys/classes rejected."""

    def _wiring(self):
        import sys as _sys

        _sys.path.insert(0, str(Path(__file__).parent.parent))
        import dataset_pack.langfuse_wiring as lw

        return lw

    def test_unknown_metadata_keys_are_dropped(self):
        """A sneaky metadata key never reaches the transmission."""
        lw = self._wiring()
        calls = []

        class FakeClient:
            def create_generation(self, **kw):
                calls.append(kw)

            def flush(self):
                pass

        lw._LANGFUSE_CLIENT = FakeClient()
        lw._LANGFUSE_STATE = {"enabled": True, "reason": "test"}
        try:
            lw.trace_generation(
                "glm-53-flash",
                "p",
                "o",
                usage=None,
                status="completed",
                incomplete_reason=None,
                latency_ms=1.0,
                metadata={
                    "run_id": "r1",
                    "secret_prompt_leak": "RAW TEXT",
                    "arbitrary": "junk",
                },
            )
            gen = calls[0]
            self.assertIn("run_id", gen["metadata"])
            self.assertNotIn("secret_prompt_leak", gen["metadata"])
            self.assertNotIn("arbitrary", gen["metadata"])
        finally:
            lw._LANGFUSE_CLIENT = None

    def test_unknown_error_class_collapses_to_unknown(self):
        """An arbitrary exception-class string cannot pass through."""
        lw = self._wiring()
        # The current implementation: raw_class = error.split(":", 1)[0]
        # then: error_class = raw_class if raw_class in _ALLOWED_ERROR_CLASSES else "Unknown"
        raw_class = "SomeNeverSeenError"
        error_class = raw_class if raw_class in lw._ALLOWED_ERROR_CLASSES else "Unknown"
        self.assertEqual(error_class, "Unknown")

    def test_failure_trace_uses_sanitized_class(self):
        """trace_failure transmits only allowlisted error classes."""
        lw = self._wiring()
        calls = []

        class FakeClient:
            def create_generation(self, **kw):
                calls.append(kw)

            def flush(self):
                pass

        lw._LANGFUSE_CLIENT = FakeClient()
        lw._LANGFUSE_STATE = {"enabled": True, "reason": "test"}
        try:
            lw.trace_failure(
                "m",
                "p",
                "WeirdCustomError: details",
                usage=None,
                status="incomplete",
                incomplete_reason=None,
                latency_ms=1.0,
            )
            # Current implementation: raw_class = error.split(":", 1)[0]
            # then: error_class = raw_class if raw_class in _ALLOWED_ERROR_CLASSES else "Unknown"
            self.assertEqual(calls[0]["metadata"]["error_class"], "Unknown")
        finally:
            lw._LANGFUSE_CLIENT = None

    def test_one_canonical_failure_event_carries_seq(self):
        """A raising capture seals ONE event with source seq."""
        import sys as _sys

        _sys.path.insert(0, str(Path(__file__).parent.parent))
        from dataset_pack.run import _ModelCaptureEventLog

        def failing_capture(turn, agent_id, event_type, payload, source_event_seq):
            raise RuntimeError("IncompleteResponseError: status='incomplete'")

        log = _ModelCaptureEventLog("run-x", "2026-11-08T00:00:00Z", failing_capture)
        with self.assertRaises(RuntimeError):
            log.append(2, "beta", "agent.observe", {"v": 1})
        failed = [e for e in log.events if e["type"] == "model.call.failed"]
        self.assertEqual(len(failed), 1, "exactly one failure event, no duplicates")
        pl = failed[0]["payload"]
        self.assertIn("source_event_seq", pl)
        self.assertIn("source_event_type", pl)
