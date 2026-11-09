"""Schema validation tests for run.config and run.end events."""

import json
import sys
from pathlib import Path

import jsonschema
import pytest

# Load schema
schema_path = Path(__file__).parent / "schema/events.schema.json"
schema = json.loads(schema_path.read_text())


def validate_event(event):
    """Validate an event against the schema."""
    jsonschema.validate(event, schema)


def test_run_config_valid():
    """Valid run.config should pass validation."""
    event = {
        "run_id": "test",
        "seq": 0,
        "turn": 0,
        "agent_id": None,
        "type": "run.config",
        "ts": "2026-11-07T14:30:00Z",
        "payload": {
            "seed": 42,
            "comm_topology": "mesh",
            "delivery_config_sha": "44136fa355b3678a",
            "disturbance_schedule": {},
            "agents": ["a", "b"],
        },
    }
    validate_event(event)
    print("✓ test_run_config_valid: PASSED")


def test_run_config_rejects_extra():
    """run.config with extra property should fail."""
    event = {
        "run_id": "test",
        "seq": 0,
        "turn": 0,
        "agent_id": None,
        "type": "run.config",
        "ts": "2026-11-07T14:30:00Z",
        "payload": {
            "seed": 42,
            "comm_topology": "mesh",
            "delivery_config_sha": "44136fa355b3678a",
            "disturbance_schedule": {},
            "agents": ["a", "b"],
            "unknown_field": "should fail",
        },
    }
    with pytest.raises(jsonschema.ValidationError):
        validate_event(event)
    print("✓ test_run_config_rejects_extra: PASSED")


def test_run_end_valid():
    """Valid run.end should pass validation."""
    event = {
        "run_id": "test",
        "seq": 100,
        "turn": 16,
        "agent_id": None,
        "type": "run.end",
        "ts": "2026-11-07T14:33:09Z",
        "payload": {
            "recovery_interval_turns": 16,
        },
    }
    validate_event(event)
    print("✓ test_run_end_valid: PASSED")


def test_run_end_rejects_extra():
    """run.end with extra property should fail."""
    event = {
        "run_id": "test",
        "seq": 100,
        "turn": 16,
        "agent_id": None,
        "type": "run.end",
        "ts": "2026-11-07T14:33:09Z",
        "payload": {
            "recovery_interval_turns": 16,
            "unknown_field": "should fail",
        },
    }
    with pytest.raises(jsonschema.ValidationError):
        validate_event(event)
    print("✓ test_run_end_rejects_extra: PASSED")


def test_existing_logs_validate():
    """Existing freight-episode.jsonl should validate."""
    jsonl_path = Path(__file__).parent / "freight-episode.jsonl"
    with open(jsonl_path) as f:
        for line in f:
            event = json.loads(line.strip())
            validate_event(event)
    print("✓ test_existing_logs_validate: PASSED")


def test_sample_run_validate():
    """Existing sample-run.jsonl should validate."""
    jsonl_path = Path(__file__).parent / "sample-run.jsonl"
    with open(jsonl_path) as f:
        for line in f:
            event = json.loads(line.strip())
            validate_event(event)
    print("✓ test_sample_run_validate: PASSED")


if __name__ == "__main__":
    print("Running schema validation tests...\n")

    test_run_config_valid()
    test_run_config_rejects_extra()
    test_run_end_valid()
    test_run_end_rejects_extra()
    test_existing_logs_validate()
    test_sample_run_validate()

    print("\n" + "=" * 50)
    print("All tests PASSED")
    sys.exit(0)
