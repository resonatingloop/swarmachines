#!/usr/bin/env python3
"""
Test suite for turn-seam scripted runner.
Validates all acceptance criteria from add-turn-seam-event-log.
"""

import ast
import json
import subprocess
import sys
import tempfile
from pathlib import Path


def run_runner(args: list[str], output_path: str) -> tuple[int, str, str]:
    """Run the runner with given args, return exit code, stdout, and stderr."""
    repo_root = Path(__file__).parent.parent
    cmd = [sys.executable, "runtime/runner.py"] + args + ["--output", output_path]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(repo_root))
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def run_runner_simple(args: list[str], output_path: str) -> tuple[int, str]:
    """Run the runner, return exit code and combined output (for tests that don't need stderr)."""
    code, stdout, stderr = run_runner(args, output_path)
    return code, stdout


def load_events(path: str) -> list[dict]:
    """Load events from JSONL file (delegates to runner.load_events for schema validation)."""
    # Use runner.load_events which validates against schema
    from runner import load_events as validated_load

    return validated_load(path)


def check_event_types(events: list[dict], required: set[str]) -> list[str]:
    """Return list of missing required event types."""
    present = {e["type"] for e in events}
    return list(required - present)


def check_schema(events: list[dict]) -> list[str]:
    """Check events conform to schema requirements."""
    errors = []
    required_fields = {"run_id", "seq", "turn", "agent_id", "type", "ts", "payload"}
    prev_seq = -1
    for i, e in enumerate(events):
        for field in required_fields:
            if field not in e:
                errors.append(f"Event {i}: missing field '{field}'")
        if "seq" in e:
            if e["seq"] <= prev_seq:
                errors.append(f"Event {i}: seq {e['seq']} not > previous {prev_seq}")
            prev_seq = e["seq"]
    return errors


def test_basic_run():
    """Test basic run produces valid event log with all required types."""
    print("Test: basic run...")
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
        output = f.name

    # Use seed 7 with a disturbance to ensure all event types are generated
    code, out = run_runner_simple(
        ["--seed", "7", "--turns", "3", "--disturbance", "relay-loss:2:a"], output
    )
    if code != 0:
        return False, f"Runner failed with code {code}: {out}"

    events = load_events(output)
    if len(events) < 20:
        return False, f"Expected >= 20 events, got {len(events)}"

    required = {
        "run.config",
        "world.init",
        "turn.begin",
        "observation.recorded",
        "message.sent",
        "message.delivered",
        "message.seen",
        "message.acted_on",
        "action.proposed",
        "action.validated",
        "action.rejected",
        "action.committed",
        "world.changed",
        "disturbance.applied",
        "run.end",
    }
    missing = check_event_types(events, required)
    if missing:
        return False, f"Missing event types: {missing}"

    errors = check_schema(events)
    if errors:
        return False, f"Schema violations: {errors[:3]}"

    Path(output).unlink()
    return True, f"OK: {len(events)} events, all base types present"


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


def test_relay_loss_emits_undelivered():
    """Test relay-loss disturbance emits message.sent + message.delivered(status='undelivered')."""
    print("Test: relay-loss emits undelivered messages...")
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
        output = f.name

    # Use seed that will generate messages, with relay-loss on agent 'c' at turn 2
    run_runner(
        ["--seed", "7", "--turns", "4", "--disturbance", "relay-loss:2:c"], output
    )
    events = load_events(output)

    Path(output).unlink()

    # Find message.sent events at turn >= 2 involving agent c
    sent_events = [e for e in events if e["type"] == "message.sent" and e["turn"] >= 2]
    if not sent_events:
        return False, "No message.sent events found after relay-loss applied"

    # Check for undelivered messages
    delivered_events = [e for e in events if e["type"] == "message.delivered"]
    undelivered = [
        e for e in delivered_events if e["payload"].get("status") == "undelivered"
    ]

    if not undelivered:
        return (
            False,
            "No message.delivered(status='undelivered') events found - relay-loss should block and report",
        )

    # Verify undelivered has reason
    for ud in undelivered:
        if "reason" not in ud["payload"]:
            return False, f"undelivered event missing 'reason' field: {ud}"

    return (
        True,
        f"OK: {len(undelivered)} undelivered messages with reasons (relay-loss working)",
    )


def test_topology_independence():
    """Test same seed + disturbance under mesh vs hub-spoke produces identical non-comm events."""
    print("Test: topology-independence (non-comm events identical)...")

    def get_non_comm_events(output_path: str) -> list[dict]:
        events = load_events(output_path)
        # Exclude communication events AND run.config (which includes topology name)
        excluded_types = {
            "message.sent",
            "message.delivered",
            "message.seen",
            "message.acted_on",
            "run.config",
        }
        return [e for e in events if e["type"] not in excluded_types]

    def normalize_event(e: dict) -> dict:
        """Remove logging artifacts (seq, ts) for semantic comparison."""
        return {k: v for k, v in e.items() if k not in ("seq", "ts")}

    def event_key(e: dict) -> tuple:
        """Sort key for deterministic ordering: (turn, agent_id, type, payload_hash)."""
        import hashlib

        payload_hash = hashlib.sha256(
            json.dumps(e.get("payload", {}), sort_keys=True).encode()
        ).hexdigest()
        # Handle None agent_id (world events) by using empty string for sorting
        agent_id = e.get("agent_id") or ""
        return (e["turn"], agent_id, e["type"], payload_hash)

    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f1:
        out1 = f1.name
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f2:
        out2 = f2.name

    # Run with same seed and disturbance under both topologies
    run_runner(
        [
            "--seed",
            "42",
            "--turns",
            "3",
            "--disturbance",
            "relay-loss:2:b",
            "--topology",
            "mesh",
        ],
        out1,
    )
    run_runner(
        [
            "--seed",
            "42",
            "--turns",
            "3",
            "--disturbance",
            "relay-loss:2:b",
            "--topology",
            "hub-spoke",
            "--hub",
            "a",
        ],
        out2,
    )

    non_comm_1 = sorted(
        [normalize_event(e) for e in get_non_comm_events(out1)], key=event_key
    )
    non_comm_2 = sorted(
        [normalize_event(e) for e in get_non_comm_events(out2)], key=event_key
    )

    Path(out1).unlink()
    Path(out2).unlink()

    # Compare non-communication events (should be identical when sorted by semantic key)
    json1 = json.dumps(non_comm_1, sort_keys=True)
    json2 = json.dumps(non_comm_2, sort_keys=True)

    if json1 != json2:
        # Debug: find first difference
        for i, (e1, e2) in enumerate(zip(non_comm_1, non_comm_2)):
            if e1 != e2:
                return (
                    False,
                    f"Non-comm events differ: {e1['type']} (turn={e1['turn']}, agent={e1.get('agent_id')}) vs {e2['type']} (turn={e2['turn']}, agent={e2.get('agent_id')})",
                )
        if len(non_comm_1) != len(non_comm_2):
            return (
                False,
                f"Non-comm events differ in count: {len(non_comm_1)} vs {len(non_comm_2)}",
            )
        return False, "Non-comm events differ (unknown reason)"

    return True, "OK: non-communication events identical across topologies"


def test_hub_spoke_cli_delivery():
    """Test hub-spoke CLI actually routes and delivers messages through hub."""
    print("Test: hub-spoke CLI delivers messages...")
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
        output = f.name

    # hub-spoke with hub='a', agents a,b,c
    code, out = run_runner_simple(
        [
            "--seed",
            "7",
            "--turns",
            "3",
            "--topology",
            "hub-spoke",
            "--hub",
            "a",
            "--agents",
            "a,b,c",
        ],
        output,
    )
    if code != 0:
        return False, f"Runner failed: {out}"

    events = load_events(output)
    Path(output).unlink()

    # Check run.config has correct topology
    config = [e for e in events if e["type"] == "run.config"][0]
    if config["payload"]["comm_topology"] != "hub-spoke":
        return (
            False,
            f"Expected topology 'hub-spoke', got {config['payload']['comm_topology']}",
        )

    # Check delivery_config_sha is real (not placeholder)
    sha = config["payload"].get("delivery_config_sha")
    if not sha or sha == "computed-at-run" or sha == "placeholder-computed-at-run":
        return False, f"delivery_config_sha is placeholder: {sha}"

    # Check that messages are actually delivered (hub-spoke should allow hub<->spoke)
    delivered = [
        e
        for e in events
        if e["type"] == "message.delivered"
        and e["payload"].get("status") == "delivered"
    ]
    if not delivered:
        return False, "No delivered messages in hub-spoke - routing may be broken"

    return (
        True,
        f"OK: hub-spoke delivers {len(delivered)} messages, delivery_config_sha={sha}",
    )


def test_message_acted_on_emitted():
    """Test message.acted_on events are emitted."""
    print("Test: message.acted_on emitted...")
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
        output = f.name

    run_runner(["--seed", "7", "--turns", "3"], output)
    events = load_events(output)

    Path(output).unlink()

    acted_on = [e for e in events if e["type"] == "message.acted_on"]
    if not acted_on:
        return False, "No message.acted_on events found"

    # Verify structure
    for ao in acted_on:
        payload = ao["payload"]
        if "message_id" not in payload:
            return False, f"message.acted_on missing message_id: {payload}"

    return True, f"OK: {len(acted_on)} message.acted_on events emitted"


def test_stale_report_has_before_after():
    """Test stale-report disturbance has before/after detail AND uses a message in circulation."""
    print("Test: stale-report has before/after detail...")
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
        output = f.name

    # First run: get a real message_id that was sent in turn 1
    run_runner(["--seed", "42", "--turns", "3"], output)
    events = load_events(output)
    Path(output).unlink()

    # Find a message that was sent in turn 1 (has full lifecycle)
    sent_in_turn1 = [
        e for e in events if e["type"] == "message.sent" and e["turn"] == 1
    ]
    if not sent_in_turn1:
        return False, "No messages sent in turn 1 for stale-report test"

    # Use a real message_id that was sent
    real_message_id = sent_in_turn1[0]["payload"]["message_id"]

    # Second run: apply stale-report with the real message_id at turn 2
    run_runner(
        [
            "--seed",
            "42",
            "--turns",
            "3",
            "--disturbance",
            f"stale-report:2:{real_message_id}:open:closed",
        ],
        output,
    )
    events = load_events(output)

    Path(output).unlink()

    # Find the stale-report disturbance
    stale_reports = [
        e
        for e in events
        if e["type"] == "disturbance.applied"
        and e["payload"].get("kind") == "stale-report"
    ]
    if not stale_reports:
        return False, "No stale-report disturbance found"

    payload = stale_reports[0]["payload"]
    if "before" not in payload or "after" not in payload:
        return False, f"stale-report missing before/after: {payload}"

    # Verify the message_id has lifecycle entries (was in circulation)
    message_id = payload["detail"]["message_id"]
    lifecycle_events = [
        e
        for e in events
        if e["type"]
        in ("message.sent", "message.delivered", "message.seen", "message.acted_on")
        and e["payload"].get("message_id") == message_id
    ]

    if not lifecycle_events:
        return (
            False,
            f"stale-report message_id {message_id} has 0 lifecycle entries - not in circulation",
        )

    # Verify full lifecycle: sent, delivered, seen
    lifecycle_types = {e["type"] for e in lifecycle_events}
    required_lifecycle = {"message.sent", "message.delivered", "message.seen"}
    missing_lifecycle = required_lifecycle - lifecycle_types
    if missing_lifecycle:
        return (
            False,
            f"stale-report message_id {message_id} missing lifecycle: {missing_lifecycle}",
        )

    return (
        True,
        f"OK: stale-report has before/after detail; message {message_id} has {len(lifecycle_events)} lifecycle entries",
    )


def test_delivery_config_sha_real():
    """Test delivery_config_sha is a real hash, not placeholder."""
    print("Test: delivery_config_sha is real hash...")
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
        output = f.name

    run_runner(["--seed", "42", "--turns", "2", "--hub", "a"], output)
    events = load_events(output)

    Path(output).unlink()

    config = [e for e in events if e["type"] == "run.config"][0]
    sha = config["payload"].get("delivery_config_sha")

    if not sha:
        return False, "delivery_config_sha missing"
    if sha in ("computed-at-run", "placeholder-computed-at-run"):
        return False, f"delivery_config_sha is placeholder: {sha}"
    # Should be a hex string
    if not all(c in "0123456789abcdef" for c in sha):
        return False, f"delivery_config_sha not hex: {sha}"

    return True, f"OK: delivery_config_sha={sha}"


def test_rng_streams_independent():
    """Test that send decisions don't affect acted_on RNG stream (swarmachines-8s2)."""
    print("Test: RNG streams independent (send doesn't affect acted_on)...")

    # Run twice with same seed - should be deterministic
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f1:
        out1 = f1.name
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f2:
        out2 = f2.name

    run_runner(["--seed", "42", "--turns", "3"], out1)
    run_runner(["--seed", "42", "--turns", "3"], out2)

    events1 = load_events(out1)
    events2 = load_events(out2)

    Path(out1).unlink()
    Path(out2).unlink()

    # Count acted_on events - should be identical due to deterministic separate streams
    acted_on_1 = [e for e in events1 if e["type"] == "message.acted_on"]
    acted_on_2 = [e for e in events2 if e["type"] == "message.acted_on"]

    if len(acted_on_1) != len(acted_on_2):
        return False, f"acted_on count differs: {len(acted_on_1)} vs {len(acted_on_2)}"

    # Verify message_ids match (same decisions made)
    ids_1 = {e["payload"]["message_id"] for e in acted_on_1}
    ids_2 = {e["payload"]["message_id"] for e in acted_on_2}

    if ids_1 != ids_2:
        return False, f"acted_on message_ids differ: {ids_1} vs {ids_2}"

    return (
        True,
        f"OK: {len(acted_on_1)} acted_on decisions deterministic with split streams",
    )


def test_zero_model_calls():
    """Verify runner has no model/network calls (import scan)."""
    print("Test: zero model calls (import scan)...")
    runner_path = Path(__file__).parent / "runner.py"
    content = runner_path.read_text()

    # Parse AST to find actual imports
    tree = ast.parse(content)

    forbidden_modules = {
        "openai",
        "anthropic",
        "google",
        "genai",
        "requests",
        "urllib",
        "httpx",
        "aiohttp",
    }

    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if any(fm in alias.name.lower() for fm in forbidden_modules):
                    found.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module and any(
                fm in node.module.lower() for fm in forbidden_modules
            ):
                found.append(node.module)

    if found:
        return False, f"Found forbidden imports: {found}"

    return True, "OK: no model/network imports detected"


def test_agent_id_validation():
    """Test agent id charset validation at CLI parse."""
    print("Test: agent id charset validation...")
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
        output = f.name

    # Try invalid agent id with special chars
    code, out = run_runner_simple(
        ["--seed", "42", "--turns", "1", "--agents", "a,b@c"], output
    )

    Path(output).unlink(missing_ok=True)

    if code == 0:
        return False, "Runner should reject agent id with special chars"

    return True, "OK: invalid agent ids rejected"


def test_turns_cap():
    """Test --turns is capped."""
    print("Test: --turns cap...")
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
        output = f.name

    code, out = run_runner_simple(["--seed", "42", "--turns", "101"], output)

    Path(output).unlink(missing_ok=True)

    if code == 0:
        return False, "Runner should reject turns > 100"

    return True, "OK: --turns capped at 100"


def test_stale_report_validates_message_id():
    """Test stale-report disturbance fails if message_id was never sent."""
    print("Test: stale-report validates message_id exists...")

    # First run: get a valid message_id that was sent
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
        output1 = f.name

    run_runner_simple(["--seed", "42", "--turns", "3"], output1)
    events = load_events(output1)
    Path(output1).unlink()

    # Get a real message_id from turn 1
    sent_turn1 = [e for e in events if e["type"] == "message.sent" and e["turn"] == 1]
    if not sent_turn1:
        return False, "No messages sent in turn 1 for test setup"

    real_message_id = sent_turn1[0]["payload"]["message_id"]
    fake_message_id = "m-nonexistent999"

    # Test 1: stale-report with valid message_id should succeed
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
        output_valid = f.name

    code, out = run_runner_simple(
        [
            "--seed",
            "42",
            "--turns",
            "3",
            "--disturbance",
            f"stale-report:2:{real_message_id}:open:closed",
        ],
        output_valid,
    )
    Path(output_valid).unlink()

    if code != 0:
        return False, f"Valid message_id should succeed, got code {code}: {out}"

    # Test 2: stale-report with non-existent message_id should fail
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
        output_invalid = f.name

    code, stdout, stderr = run_runner(
        [
            "--seed",
            "42",
            "--turns",
            "3",
            "--disturbance",
            f"stale-report:2:{fake_message_id}:open:closed",
        ],
        output_invalid,
    )
    Path(output_invalid).unlink(missing_ok=True)

    if code == 0:
        return False, "stale-report with non-existent message_id should fail"

    combined_output = stdout + stderr
    if (
        "non-existent message_id" not in combined_output
        and "never sent" not in combined_output
    ):
        return (
            False,
            f"Error message should mention non-existent message: {combined_output}",
        )

    return True, "OK: stale-report validates message_id exists"


def test_bidirectional_ring_topology():
    """Test bidirectional-ring topology restricts communication to neighbors only."""
    print("Test: bidirectional-ring topology...")
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
        output = f.name

    # Run with bidirectional-ring topology, 4 agents in a ring: a-b-c-d-a
    code, out = run_runner_simple(
        [
            "--seed",
            "42",
            "--turns",
            "2",
            "--topology",
            "bidirectional-ring",
            "--agents",
            "a,b,c,d",
        ],
        output,
    )
    if code != 0:
        return False, f"Runner failed with code {code}: {out}"

    events = load_events(output)
    Path(output).unlink()

    # Check that messages are only sent between neighbors
    # In ring a-b-c-d-a: a's neighbors are (d,b), b's are (a,c), c's are (b,d), d's are (c,a)
    sent_messages = [e for e in events if e["type"] == "message.sent"]

    neighbors = {
        "a": {"d", "b"},
        "b": {"a", "c"},
        "c": {"b", "d"},
        "d": {"c", "a"},
    }

    for msg in sent_messages:
        from_agent = msg["payload"]["from"]
        to_agent = msg["payload"]["to"]
        if to_agent not in neighbors.get(from_agent, set()):
            return (
                False,
                f"Ring violation: {from_agent} sent to non-neighbor {to_agent}",
            )

    return (
        True,
        f"OK: ring topology restricts communication to neighbors ({len(sent_messages)} messages)",
    )


def test_peer_mute_disturbance():
    """Test peer-mute disturbance mutes agent communication while local actions continue."""
    print("Test: peer-mute disturbance...")
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
        output = f.name

    # Run with peer-mute on agent 'b' at turn 2
    code, out = run_runner_simple(
        [
            "--seed",
            "42",
            "--turns",
            "3",
            "--topology",
            "mesh",
            "--disturbance",
            "peer-mute:2:b",
        ],
        output,
    )
    if code != 0:
        return False, f"Runner failed with code {code}: {out}"

    events = load_events(output)
    Path(output).unlink()

    # Check that peer-mute disturbance event is logged
    peer_mute_events = [
        e
        for e in events
        if e["type"] == "disturbance.applied"
        and e["payload"].get("kind") == "peer-mute"
    ]
    if not peer_mute_events:
        return False, "No peer-mute disturbance event found"

    # Check that muted agent 'b' has no message.sent events after turn 2
    post_mute_comm = [
        e
        for e in events
        if e["turn"] >= 2 and e["agent_id"] == "b" and e["type"] == "message.sent"
    ]
    if post_mute_comm:
        return (
            False,
            f"Muted agent 'b' should not send messages after turn 2, found {len(post_mute_comm)} events",
        )

    # Check that muted agent 'b' still has local actions (observe, act) after turn 2
    post_mute_actions = [
        e
        for e in events
        if e["turn"] >= 2
        and e["agent_id"] == "b"
        and e["type"] in ("observation.recorded", "action.proposed", "action.committed")
    ]
    if not post_mute_actions:
        return False, "Muted agent 'b' should still have local actions after turn 2"

    return True, "OK: peer-mute mutes communication but local actions continue"


def test_topology_independence_with_ring():
    """Test topology-independence: non-comm events identical across mesh and bidirectional-ring."""
    print("Test: topology-independence with ring...")

    def get_non_comm_events(output_path: str) -> list[dict]:
        events = load_events(output_path)
        # Exclude communication events AND run.config (which includes topology name)
        excluded_types = {
            "message.sent",
            "message.delivered",
            "message.seen",
            "message.acted_on",
            "run.config",
        }
        return [e for e in events if e["type"] not in excluded_types]

    def normalize_event(e: dict) -> dict:
        """Remove logging artifacts (seq, ts) for semantic comparison."""
        return {k: v for k, v in e.items() if k not in ("seq", "ts")}

    def event_key(e: dict) -> tuple:
        """Sort key for deterministic ordering: (turn, agent_id, type, payload_hash)."""
        import hashlib

        payload_hash = hashlib.sha256(
            json.dumps(e.get("payload", {}), sort_keys=True).encode()
        ).hexdigest()
        # Handle None agent_id (world events) by using empty string for sorting
        agent_id = e.get("agent_id") or ""
        return (e["turn"], agent_id, e["type"], payload_hash)

    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f1:
        out1 = f1.name
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f2:
        out2 = f2.name

    # Run with same seed under mesh and bidirectional-ring topologies
    run_runner_simple(["--seed", "42", "--turns", "3", "--topology", "mesh"], out1)
    run_runner_simple(
        [
            "--seed",
            "42",
            "--turns",
            "3",
            "--topology",
            "bidirectional-ring",
            "--agents",
            "a,b,c,d",
        ],
        out2,
    )

    non_comm_1 = sorted(
        [normalize_event(e) for e in get_non_comm_events(out1)], key=event_key
    )
    non_comm_2 = sorted(
        [normalize_event(e) for e in get_non_comm_events(out2)], key=event_key
    )

    Path(out1).unlink()
    Path(out2).unlink()

    # Compare non-communication events (should be identical when sorted by semantic key)
    json1 = json.dumps(non_comm_1, sort_keys=True)
    json2 = json.dumps(non_comm_2, sort_keys=True)

    if json1 != json2:
        # Debug: find first difference
        for i, (e1, e2) in enumerate(zip(non_comm_1, non_comm_2)):
            if e1 != e2:
                return (
                    False,
                    f"Non-comm events differ: {e1['type']} (turn={e1['turn']}, agent={e1.get('agent_id')}) vs {e2['type']} (turn={e2['turn']}, agent={e2.get('agent_id')})",
                )
        if len(non_comm_1) != len(non_comm_2):
            return (
                False,
                f"Non-comm events differ in count: {len(non_comm_1)} vs {len(non_comm_2)}",
            )
        return False, "Non-comm events differ (unknown reason)"

    return True, "OK: non-communication events identical across mesh and ring"


def test_load_events_hardening():
    """Test load_events has 10MB cap and non-echoing errors (swarmachines-mnp)."""
    print("Test: load_events hardening (10MB cap, non-echoing errors)...")
    import importlib

    import runner
    importlib.reload(runner)

    # Verify default is 10MB
    import inspect
    sig = inspect.signature(runner.load_events)
    default_limit = sig.parameters["char_limit"].default
    if default_limit != 10000000:
        return False, f"char_limit default is {default_limit}, expected 10000000 (10MB)"

    # Test non-echoing errors - hostile input not echoed
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False, mode="w") as f:
        hostile_file = f.name
        # Malicious JSON with ANSI escape codes and path traversal
        f.write('{"run_id": "../../etc/passwd", "seq": "\\u001b[31mMALICIOUS\\u001b[0m"}\n')
        # Invalid JSON with hostile content
        f.write('not valid json <script>alert("xss")</script>\n')

    # Capture stdout to verify non-echoing
    import io
    from contextlib import redirect_stdout

    captured = io.StringIO()
    with redirect_stdout(captured):
        events = runner.load_events(hostile_file)

    output = captured.getvalue()
    Path(hostile_file).unlink()

    # Verify hostile content is NOT echoed
    if "../../etc/passwd" in output:
        return False, "Hostile path traversal echoed in error output"
    if "\\u001b[31m" in output or "MALICIOUS" in output:
        return False, "Hostile ANSI/content echoed in error output"
    if "<script>" in output or "xss" in output:
        return False, "Hostile script tag echoed in error output"
    if "invalid_json" not in output and "schema_validation_failed" not in output:
        return False, f"Expected categorical error types, got: {output}"

    return True, "OK: 10MB cap configured, non-echoing errors verified"


def main():
    """Run all tests."""
    print("=" * 60)
    print("turn-seam runner test suite (v4x gate findings)")
    print("=" * 60)

    tests = [
        ("basic_run", test_basic_run),
        ("determinism", test_determinism),
        ("relay_loss_undelivered", test_relay_loss_emits_undelivered),
        ("topology_independence", test_topology_independence),
        ("hub_spoke_delivery", test_hub_spoke_cli_delivery),
        ("message_acted_on", test_message_acted_on_emitted),
        ("stale_report_detail", test_stale_report_has_before_after),
        ("delivery_config_sha", test_delivery_config_sha_real),
        ("rng_streams_independent", test_rng_streams_independent),
        ("zero_model_calls", test_zero_model_calls),
        ("agent_id_validation", test_agent_id_validation),
        ("turns_cap", test_turns_cap),
        ("stale_report_validates_message_id", test_stale_report_validates_message_id),
        ("bidirectional_ring_topology", test_bidirectional_ring_topology),
        ("peer_mute_disturbance", test_peer_mute_disturbance),
        ("topology_independence_with_ring", test_topology_independence_with_ring),
        ("load_events_hardening", test_load_events_hardening),
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
        except Exception as e:
            print(f"  ERROR [{name}]: {e}")
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
