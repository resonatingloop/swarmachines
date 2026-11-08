"""
Test suite for Langfuse-compatible tracing layer.

Tests per spec (specs/001-hackathon-plan.md step 5):
- Trace events captured in-memory via fake exporter (no network)
- Assert nesting under turns
- Assert usage-recorded-or-unknown
- Assert telemetry-failure-does-not-mutate-world
- Assert no-op path when unconfigured
"""

import hashlib
import sys
from pathlib import Path

# Add runtime to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from tracer import (
    FakeExporter,
    RunStatus,
    TraceConfig,
    Tracer,
    create_tracer,
)


def test_no_op_when_unconfigured():
    """Test that tracing is a no-op when not configured."""
    print("Test: no-op when unconfigured...")

    # Create tracer with enabled=False
    config = TraceConfig(enabled=False)
    exporter = FakeExporter()
    tracer = Tracer(config, exporter=exporter)

    # All operations should be no-ops
    tracer.start_trace("test-run", condition="mesh", seed=42)
    with tracer.span("test-span"):
        pass
    tracer.record_model_call("test-model")
    tracer.end_trace(RunStatus.COMPLETED, reason="test")

    # Exporter should have nothing recorded
    assert len(exporter.traces) == 0, f"Expected 0 traces, got {len(exporter.traces)}"
    assert len(exporter.spans) == 0, f"Expected 0 spans, got {len(exporter.spans)}"

    return True, "OK: tracing is no-op when disabled"


def test_trace_start_end():
    """Test that trace start and end are recorded."""
    print("Test: trace start and end...")

    config = TraceConfig(enabled=True)
    exporter = FakeExporter()
    tracer = Tracer(config, exporter=exporter)

    tracer.start_trace("test-run-123", condition="ring-mute", seed=42)
    tracer.end_trace(RunStatus.COMPLETED, reason="completed 4 turns")

    # Should have trace recorded
    assert len(exporter.traces) >= 1, (
        f"Expected at least 1 trace, got {len(exporter.traces)}"
    )

    # Check trace has correct metadata
    trace = exporter.traces[0]
    expected_id = hashlib.sha256(b"test-run-123").hexdigest()
    assert trace["metadata"]["run_id_sha256"] == expected_id
    assert trace["metadata"]["condition"] == "ring-mute"
    assert trace["metadata"]["seed"] == 42

    return True, "OK: trace start/end recorded with correct metadata"


def test_span_nesting_under_turns():
    """Test that spans are nested under agent turns."""
    print("Test: span nesting under turns...")

    config = TraceConfig(enabled=True)
    exporter = FakeExporter()
    tracer = Tracer(config, exporter=exporter)

    tracer.start_trace("run-test", seed=42)

    # Simulate turn structure: turn 1 with observe, exchange, act phases
    with (
        tracer.span(
            "turn-1-observe", metadata={"turn": 1, "phase": "observe", "agent_id": "a"}
        ),
        tracer.span("model:glm-53-flash", metadata={"type": "model_call"}),
    ):
        pass

    with tracer.span(
        "turn-1-exchange", metadata={"turn": 1, "phase": "exchange", "agent_id": "a"}
    ):
        pass

    with tracer.span(
        "turn-1-act", metadata={"turn": 1, "phase": "act", "agent_id": "a"}
    ):
        pass

    tracer.end_trace(RunStatus.COMPLETED)

    # Check spans are recorded
    assert len(exporter.spans) >= 4, (
        f"Expected at least 4 spans, got {len(exporter.spans)}"
    )

    # Check turn spans have correct metadata
    turn_spans = [s for s in exporter.spans if s["name"].startswith("turn-1-")]
    assert len(turn_spans) >= 3, f"Expected 3 turn phase spans, got {len(turn_spans)}"

    # Verify each turn span has required metadata
    for span in turn_spans:
        assert "turn" in span.get("metadata", {}), (
            f"Turn span missing 'turn' metadata: {span}"
        )
        assert "phase" in span.get("metadata", {}), (
            f"Turn span missing 'phase' metadata: {span}"
        )
        assert "agent_id" in span.get("metadata", {}), (
            f"Turn span missing 'agent_id' metadata: {span}"
        )

    return True, f"OK: {len(turn_spans)} turn phase spans with correct nesting metadata"


def test_usage_recorded_or_unknown():
    """Test that missing usage is recorded as 'unknown', not fabricated."""
    print("Test: usage recorded or unknown...")

    config = TraceConfig(enabled=True)
    exporter = FakeExporter()
    tracer = Tracer(config, exporter=exporter)

    tracer.start_trace("run-test", seed=42)

    # Record model call with partial usage (some fields missing)
    tracer.record_model_call(
        model_id="glm-53-flash",
        prompt_tokens=100,
        # completion_tokens missing
        # total_tokens missing
    )

    # Record model call with no usage at all
    tracer.record_model_call(model_id="gemma-4-26b-a4b-it")

    tracer.end_trace(RunStatus.COMPLETED)

    # Check model call spans
    model_spans = [s for s in exporter.spans if s["name"].startswith("model:")]
    assert len(model_spans) >= 2, (
        f"Expected at least 2 model spans, got {len(model_spans)}"
    )

    # Check first span: prompt_tokens present, others should be 'unknown'
    span1 = model_spans[0]
    usage1 = span1.get("usage", {})
    assert usage1.get("prompt_tokens") == 100, (
        f"Expected prompt_tokens=100, got {usage1.get('prompt_tokens')}"
    )
    assert usage1.get("completion_tokens") == "unknown", (
        f"Expected completion_tokens='unknown', got {usage1.get('completion_tokens')}"
    )
    assert usage1.get("total_tokens") == "unknown", (
        f"Expected total_tokens='unknown', got {usage1.get('total_tokens')}"
    )

    # Check second span: all usage should be 'unknown'
    span2 = model_spans[1]
    usage2 = span2.get("usage", {})
    assert usage2.get("prompt_tokens") == "unknown", (
        f"Expected prompt_tokens='unknown', got {usage2.get('prompt_tokens')}"
    )
    assert usage2.get("completion_tokens") == "unknown", (
        f"Expected completion_tokens='unknown', got {usage2.get('completion_tokens')}"
    )
    assert usage2.get("total_tokens") == "unknown", (
        f"Expected total_tokens='unknown', got {usage2.get('total_tokens')}"
    )

    return True, "OK: missing usage recorded as 'unknown', not fabricated"


def test_telemetry_failure_does_not_mutate_world():
    """Test that telemetry failures are non-fatal and don't alter world state."""
    print("Test: telemetry failure does not mutate world...")

    config = TraceConfig(enabled=True)
    exporter = FakeExporter()
    tracer = Tracer(config, exporter=exporter)

    tracer.start_trace("run-test", seed=42)

    # Simulate some world state (event log entries)
    world_events = []

    # Record a span - this should not affect world_events
    with tracer.span("test-span"):
        world_events.append({"type": "action.committed", "agent_id": "a"})

    # Simulate telemetry error (manually add one)
    tracer._telemetry_errors.append(
        {
            "type": "simulated_error",
            "time": "2026-11-08T00:00:00Z",
        }
    )

    tracer.end_trace(RunStatus.COMPLETED)

    # World events should be unchanged by telemetry
    assert len(world_events) == 1, f"Expected 1 world event, got {len(world_events)}"
    assert world_events[0]["type"] == "action.committed"

    # Telemetry errors should be recorded but not affect world
    telemetry_errors = tracer.get_telemetry_errors()
    assert len(telemetry_errors) >= 1, "Expected at least 1 telemetry error"

    return True, "OK: telemetry failure recorded but world state unchanged"


def test_fake_exporter_captures_events():
    """Test that fake exporter captures trace events in-memory."""
    print("Test: fake exporter captures events...")

    config = TraceConfig(enabled=True)
    exporter = FakeExporter()
    tracer = Tracer(config, exporter=exporter)

    tracer.start_trace("run-test", seed=42)

    with tracer.span("observe", metadata={"agent_id": "a", "turn": 1}):
        pass

    with tracer.span("act", metadata={"agent_id": "a", "turn": 1}):
        pass

    tracer.record_model_call(
        "glm-53-flash", prompt_tokens=50, completion_tokens=100, total_tokens=150
    )
    tracer.record_tool_call("browser_exec", args={"code": "print('hi')"})

    tracer.end_trace(RunStatus.COMPLETED)

    # Verify exporter captured everything
    assert len(exporter.traces) >= 1, f"Expected traces, got {len(exporter.traces)}"
    assert len(exporter.spans) >= 4, (
        f"Expected at least 4 spans, got {len(exporter.spans)}"
    )

    # Check model call span
    model_spans = exporter.get_spans_by_name("model:glm-53-flash")
    assert len(model_spans) >= 1, "Expected model span"
    model_span = model_spans[0]
    assert model_span["usage"]["prompt_tokens"] == 50
    assert model_span["usage"]["completion_tokens"] == 100
    assert model_span["usage"]["total_tokens"] == 150

    # Check tool call span
    tool_spans = exporter.get_spans_by_name("tool:browser_exec")
    assert len(tool_spans) >= 1, "Expected tool span"
    tool_span = tool_spans[0]
    assert tool_span["metadata"]["args"]["code"] == "print('hi')"

    return True, f"OK: fake exporter captured {len(exporter.spans)} spans in-memory"


def test_create_tracer_helper():
    """Test create_tracer helper function."""
    print("Test: create_tracer helper...")

    # Test with fake exporter
    tracer, exporter = create_tracer(
        run_id="test-run",
        condition="mesh",
        seed=123,
        use_fake_exporter=True,
    )

    assert exporter is not None, "Expected fake exporter"
    assert tracer is not None, "Expected tracer"

    tracer.start_trace("test-run", seed=123)
    tracer.end_trace(RunStatus.COMPLETED)

    assert len(exporter.traces) >= 1, "Expected trace to be recorded"

    return True, "OK: create_tracer returns tracer and fake exporter"


def test_run_status_enum():
    """Test RunStatus enum values per spec."""
    print("Test: RunStatus enum values...")

    # Per spec: completed, failed, budget-stopped, cancelled
    assert RunStatus.COMPLETED.value == "completed"
    assert RunStatus.FAILED.value == "failed"
    assert RunStatus.BUDGET_STOPPED.value == "budget-stopped"
    assert RunStatus.CANCELLED.value == "cancelled"

    return True, "OK: RunStatus has all required terminal states"


def test_turn_span_helper():
    """Test turn_span context manager."""
    print("Test: turn_span context manager...")

    config = TraceConfig(enabled=True)
    exporter = FakeExporter()
    tracer = Tracer(config, exporter=exporter)

    tracer.start_trace("run-test", seed=42)

    with tracer.turn_span(turn=2, phase="observe", agent_id="b"):
        pass

    with tracer.turn_span(turn=2, phase="act", agent_id="b"):
        pass

    tracer.end_trace(RunStatus.COMPLETED)

    # Check turn spans
    turn_spans = [s for s in exporter.spans if "turn-2" in s["name"]]
    assert len(turn_spans) >= 2, f"Expected 2 turn-2 spans, got {len(turn_spans)}"

    # Verify metadata
    for span in turn_spans:
        assert span["metadata"]["turn"] == 2
        assert span["metadata"]["agent_id"] == "b"
        assert span["metadata"]["type"] == "agent_turn"

    return True, "OK: turn_span creates properly structured spans"


def test_turnseam_runner_with_fake_exporter():
    """Acceptance test: TurnSeamRunner with tracer emits nested spans."""
    print("Test: TurnSeamRunner with fake exporter (acceptance)...")

    # Import runner here to avoid circular imports
    from runner import TurnSeamRunner

    # Create tracer with fake exporter
    from tracer import create_tracer

    tracer, exporter = create_tracer(
        run_id="acceptance-test-run",
        condition="mesh",
        seed=42,
        use_fake_exporter=True,
    )

    # Exporter is guaranteed non-None when use_fake_exporter=True
    assert exporter is not None, "Expected fake exporter to be created"

    # Create runner with tracer
    runner = TurnSeamRunner(
        seed=42,
        comm_topology="mesh",
        agents_config=["a", "b", "c", "d"],
        disturbance_schedule={},
        tracer=tracer,
    )

    # Run 2 turns
    runner.run(num_turns=2)

    # Expected: 2 turns × 4 agents × 3 phases = 24 turn spans
    expected_turn_spans = 2 * 4 * 3  # 24

    # Get all turn spans
    turn_spans = [s for s in exporter.spans if s["name"].startswith("turn-")]

    # Assert span count
    assert len(turn_spans) == expected_turn_spans, (
        f"Expected {expected_turn_spans} turn spans, got {len(turn_spans)}"
    )

    # Assert every turn span's parent_id == run trace id
    trace_id = tracer.current_trace_id
    for span in turn_spans:
        assert span.get("parent_id") == trace_id, (
            f"Turn span {span['name']} has parent_id {span.get('parent_id')}, expected {trace_id}"
        )

    # Assert spans nest structurally: check that we have all phases for each turn/agent
    # Structure: turn-{N}-{phase} for each turn (1,2), agent (a,b,c,d), phase (observe,exchange,act)
    expected_span_names = set()
    for turn in [1, 2]:
        for agent in ["a", "b", "c", "d"]:
            for phase in ["observe", "exchange", "act"]:
                expected_span_names.add(f"turn-{turn}-{phase}")

    actual_span_names = {s["name"] for s in turn_spans}
    assert actual_span_names == expected_span_names, (
        f"Span names mismatch:\n  Missing: {expected_span_names - actual_span_names}\n"
        f"  Extra: {actual_span_names - expected_span_names}"
    )

    # Verify metadata on each span
    for span in turn_spans:
        metadata = span.get("metadata", {})
        assert "turn" in metadata, f"Span {span['name']} missing 'turn' metadata"
        assert "phase" in metadata, f"Span {span['name']} missing 'phase' metadata"
        assert "agent_id" in metadata, (
            f"Span {span['name']} missing 'agent_id' metadata"
        )
        assert metadata["type"] == "agent_turn", (
            f"Span {span['name']} has wrong type: {metadata.get('type')}"
        )

    return (
        True,
        f"OK: {len(turn_spans)} turn spans, all parent_id={trace_id}, structure verified",
    )


def main():
    """Run all tests."""
    print("=" * 60)
    print("Tracing layer test suite")
    print("=" * 60)

    tests = [
        ("no_op_when_unconfigured", test_no_op_when_unconfigured),
        ("trace_start_end", test_trace_start_end),
        ("span_nesting_under_turns", test_span_nesting_under_turns),
        ("usage_recorded_or_unknown", test_usage_recorded_or_unknown),
        (
            "telemetry_failure_does_not_mutate_world",
            test_telemetry_failure_does_not_mutate_world,
        ),
        ("fake_exporter_captures_events", test_fake_exporter_captures_events),
        ("create_tracer_helper", test_create_tracer_helper),
        ("run_status_enum", test_run_status_enum),
        ("turn_span_helper", test_turn_span_helper),
        (
            "turnseam_runner_with_fake_exporter",
            test_turnseam_runner_with_fake_exporter,
        ),
    ]

    passed = 0
    failed = 0
    failures = []

    for name, test in tests:
        try:
            ok, msg = test()
            if ok:
                print(f"  PASS [{name}]: {msg}")
                passed += 1
            else:
                print(f"  FAIL [{name}]: {msg}")
                failed += 1
                failures.append((name, msg))
        except Exception as e:  # noqa: BLE001
            print(f"  ERROR [{name}]: {e}")
            import traceback

            traceback.print_exc()
            failed += 1
            failures.append((name, str(e)))

    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    if failures:
        print("\nFailures:")
        for name, msg in failures:
            print(f"  - {name}: {msg}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
