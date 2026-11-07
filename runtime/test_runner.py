#!/usr/bin/env python3
"""
Test suite for turn-seam scripted runner.
Validates all acceptance criteria from add-turn-seam-event-log.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path


def run_runner(args: list[str], output_path: str) -> tuple[int, str]:
    """Run the runner with given args, return exit code and output."""
    cmd = [sys.executable, "runtime/runner.py"] + args + ["--output", output_path]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd="/workspace/swarmachines")
    return result.returncode, result.stdout.strip()


def load_events(path: str) -> list[dict]:
    """Load events from JSONL file."""
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def check_event_types(events: list[dict], required: set[str]) -> list[str]:
    """Return list of missing required event types."""
    present = {e["type"] for e in events}
    return list(required - present)


def check_schema(events: list[dict]) -> list[str]:
    """Check events conform to schema requirements."""
    errors = []
    required_fields = {"run_id", "seq", "turn", "type", "ts", "payload"}
    prev_seq = -1
    for i, e in enumerate(events):
        for field in required_fields:
            if field not in e:
                errors.append(f"Event {i}: missing field '{field}'")
        if "seq" in e:
            if e["seq"] <= prev_seq:
                errors.append(f"Event {i}: seq {e['seq']} not > previous {prev_seq}")
            prev_seq = e["seq"]
        if "agent_id" not in e:
            errors.append(f"Event {i}: missing 'agent_id' (should be null for world events)")
    return errors


def test_basic_run():
    """Test basic run produces valid event log."""
    print("Test: basic run...")
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
        output = f.name
    
    code, out = run_runner(["--seed", "42", "--turns", "3"], output)
    if code != 0:
        return False, f"Runner failed with code {code}: {out}"
    
    events = load_events(output)
    if len(events) < 20:
        return False, f"Expected >= 20 events, got {len(events)}"
    
    required = {
        "run.config", "world.init", "turn.begin",
        "observation.recorded", "message.sent", "message.delivered", "message.seen",
        "action.proposed", "action.validated", "action.committed", "run.end"
    }
    missing = check_event_types(events, required)
    if missing:
        return False, f"Missing event types: {missing}"
    
    errors = check_schema(events)
    if errors:
        return False, f"Schema violations: {errors[:3]}"
    
    Path(output).unlink()
    return True, f"OK: {len(events)} events, all types present"


def test_determinism():
    """Test that same seed produces byte-identical output."""
    print("Test: determinism...")
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f1:
        out1 = f1.name
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f2:
        out2 = f2.name
    
    run_runner(["--seed", "123", "--turns", "4"], out1)
    run_runner(["--seed", "123", "--turns", "4"], out2)
    
    content1 = Path(out1).read_bytes()
    content2 = Path(out2).read_bytes()
    
    Path(out1).unlink()
    Path(out2).unlink()
    
    if content1 != content2:
        return False, "Runs with same seed produced different output"
    
    return True, "OK: byte-identical outputs"


def test_relay_loss_disturbance():
    """Test relay-loss disturbance is applied and logged."""
    print("Test: relay-loss disturbance...")
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
        output = f.name
    
    run_runner(["--seed", "42", "--turns", "4", "--disturbance", "relay-loss:2:c"], output)
    events = load_events(output)
    
    Path(output).unlink()
    
    disturbance_events = [e for e in events if e["type"] == "disturbance.applied"]
    if not disturbance_events:
        return False, "No disturbance.applied events found"
    
    relay_loss = [e for e in disturbance_events if e["payload"].get("kind") == "relay-loss"]
    if not relay_loss:
        return False, "No relay-loss disturbance found"
    
    detail = relay_loss[0]["payload"]["detail"]
    if detail.get("agent") != "c":
        return False, f"Expected agent 'c', got {detail.get('agent')}"
    
    return True, f"OK: relay-loss applied at turn {relay_loss[0]['turn']}"


def test_stale_report_disturbance():
    """Test stale-report disturbance is applied and logged."""
    print("Test: stale-report disturbance...")
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
        output = f.name
    
    run_runner(["--seed", "42", "--turns", "3", "--disturbance", "stale-report:2:m-test:open:closed"], output)
    events = load_events(output)
    
    Path(output).unlink()
    
    disturbance_events = [e for e in events if e["type"] == "disturbance.applied"]
    stale_reports = [e for e in disturbance_events if e["payload"].get("kind") == "stale-report"]
    
    if not stale_reports:
        return False, "No stale-report disturbance found"
    
    detail = stale_reports[0]["payload"]["detail"]
    if detail.get("claimed_state") != "open":
        return False, f"Expected claimed_state 'open', got {detail.get('claimed_state')}"
    
    return True, "OK: stale-report applied with correct detail"


def test_hub_spoke_topology():
    """Test hub-spoke topology configuration."""
    print("Test: hub-spoke topology...")
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
        output = f.name
    
    code, out = run_runner(["--seed", "42", "--turns", "2", "--topology", "hub-spoke", "--agents", "hub,a,b"], output)
    if code != 0:
        return False, f"Runner failed: {out}"
    
    events = load_events(output)
    config_event = [e for e in events if e["type"] == "run.config"][0]
    
    Path(output).unlink()
    
    if config_event["payload"]["comm_topology"] != "hub-spoke":
        return False, f"Expected topology 'hub-spoke', got {config_event['payload']['comm_topology']}"
    
    return True, "OK: hub-spoke topology configured"


def test_message_lifecycle():
    """Test message lifecycle tracking (sent -> delivered -> seen)."""
    print("Test: message lifecycle...")
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
        output = f.name
    
    run_runner(["--seed", "42", "--turns", "2"], output)
    events = load_events(output)
    
    Path(output).unlink()
    
    sent = [e for e in events if e["type"] == "message.sent"]
    delivered = [e for e in events if e["type"] == "message.delivered"]
    seen = [e for e in events if e["type"] == "message.seen"]
    
    if not sent:
        return False, "No message.sent events found"
    
    # Each sent message should have corresponding delivered and seen events
    sent_ids = {e["payload"]["message_id"] for e in sent}
    delivered_ids = {e["payload"]["message_id"] for e in delivered}
    seen_ids = {e["payload"]["message_id"] for e in seen}
    
    if not sent_ids.issubset(delivered_ids):
        return False, "Some sent messages were not delivered"
    if not sent_ids.issubset(seen_ids):
        return False, "Some sent messages were not seen"
    
    return True, f"OK: {len(sent)} messages with complete lifecycle"


def test_zero_model_calls():
    """Verify runner has no model/network calls (static analysis)."""
    print("Test: zero model calls...")
    runner_path = Path("/workspace/swarmachines/runtime/runner.py")
    content = runner_path.read_text()
    
    # Check for common model/API call patterns
    forbidden = [
        "openai.", "anthropic.", "google.genai.",
        "requests.post", "requests.get", "urllib.request",
        "httpx.", "aiohttp."
    ]
    
    found = []
    for pattern in forbidden:
        if pattern in content:
            found.append(pattern)
    
    if found:
        return False, f"Found potential model/network calls: {found}"
    
    return True, "OK: no model/network calls detected"


def main():
    """Run all tests."""
    print("=" * 60)
    print("turn-seam runner test suite")
    print("=" * 60)
    
    tests = [
        test_basic_run,
        test_determinism,
        test_relay_loss_disturbance,
        test_stale_report_disturbance,
        test_hub_spoke_topology,
        test_message_lifecycle,
        test_zero_model_calls,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            ok, msg = test()
            if ok:
                print(f"  PASS: {msg}")
                passed += 1
            else:
                print(f"  FAIL: {msg}")
                failed += 1
        except Exception as e:
            print(f"  ERROR: {e}")
            failed += 1
    
    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
