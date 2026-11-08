"""regressions for governed dataset-run causality and transcript matching."""

from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import jsonschema

from runtime.runner import verify_seal

from .configs import get_task_configs
from .run import GovernedRunner


class _FakeAdapter:
    """offline adapter that records deterministic, non-network responses."""

    calls = 0

    def chat(self, *, model: str, messages: list[dict[str, str]]):
        type(self).calls += 1
        return SimpleNamespace(
            output_text=f"offline-response-{type(self).calls}",
            usage=SimpleNamespace(input_tokens=7, output_tokens=3),
        )


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _assert_schema(test: unittest.TestCase, events: list[dict]) -> None:
    schema_path = (
        Path(__file__).parents[1] / "runtime" / "schema" / "events.schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    for event in events:
        with test.subTest(seq=event["seq"], event_type=event["type"]):
            jsonschema.validate(event, schema)


def _assert_model_call_links(test: unittest.TestCase, events: list[dict]) -> None:
    by_seq = {event["seq"]: event for event in events}
    model_calls = [event for event in events if event["type"] == "model.call"]
    for event in model_calls:
        payload = event["payload"]
        source = by_seq[payload["source_event_seq"]]
        with test.subTest(seq=event["seq"], source_seq=source["seq"]):
            test.assertLess(source["seq"], event["seq"])
            test.assertEqual(source["type"], payload["source_event_type"])
            test.assertEqual(source["seq"] + 1, event["seq"])


class GovernedRunCausalityTests(unittest.TestCase):
    def test_live_model_evidence_is_hashed_before_seal(self):
        config = replace(get_task_configs()[0], turns=1)
        _FakeAdapter.calls = 0
        with tempfile.TemporaryDirectory() as root:
            runner = GovernedRunner(root, config, dry_run=False)
            runner.prepare()
            with patch("runtime.adaption_adapter.AdaptionAdapter", _FakeAdapter):
                runner.submit()

            self.assertTrue(runner.event_log.sealed)
            verify_seal(runner.event_log.events)
            _assert_schema(self, runner.event_log.events)
            _assert_model_call_links(self, runner.event_log.events)
            event_pairs = {
                (event["payload"].get("prompt"), event["payload"].get("response"))
                for event in runner.event_log.events
                if "prompt" in event.get("payload", {})
            }
            call_pairs = {
                (record.prompt_full, record.response_full)
                for record in runner.call_records
            }
            self.assertEqual(call_pairs, event_pairs)
            self.assertEqual(len(call_pairs), 8)

    def test_disturbance_call_matches_a_preseal_event(self):
        config = replace(get_task_configs()[1], turns=5)
        with tempfile.TemporaryDirectory() as root:
            result = GovernedRunner(root, config, dry_run=True).run_full_workflow()
            run_dir = Path(result["run_dir"])
            events = _read_jsonl(run_dir / "logs" / "events.jsonl")
            calls = _read_jsonl(run_dir / "logs" / "calls.jsonl")

            verify_seal(events)
            _assert_schema(self, events)
            _assert_model_call_links(self, events)
            event_pairs = {
                (event["payload"].get("prompt"), event["payload"].get("response"))
                for event in events
                if "prompt" in event.get("payload", {})
            }
            unmatched = [
                call["call_id"]
                for call in calls
                if (call["prompt_full"], call["response_full"]) not in event_pairs
            ]
            self.assertEqual(unmatched, [])


if __name__ == "__main__":
    unittest.main()
