#!/usr/bin/env python3
"""Verify sample-run.jsonl has all required event types with schema validation."""

import sys
from pathlib import Path

# Add runtime to path for load_events
sys.path.insert(0, str(Path(__file__).parent))

from runner import load_events


def main():
    # Accept path from CLI argument, default to sample-run.jsonl for backward compat
    if len(sys.argv) > 1:
        event_path = Path(sys.argv[1])
    else:
        event_path = Path(__file__).parent / "sample-run.jsonl"

    if not event_path.exists():
        print(f"ERROR: File not found: {event_path}", file=sys.stderr)
        return 1

    events = load_events(str(event_path))
    types = {e["type"] for e in events}
    print(f"Event types in {event_path.name}:")
    for t in sorted(types):
        count = sum(1 for e in events if e["type"] == t)
        print(f"  {t}: {count}")
    print(f"Total events: {len(events)}")

    # Check for required types from schema
    # Note: action.rejected and disturbance.applied are conditional - they only occur
    # when validation fails or disturbances are scheduled. A clean run with all legal
    # actions and no disturbances will not have these events, which is valid.
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
        "action.committed",
        "world.changed",
        "run.end",
    }
    # Conditional requirements - only required when the scenario calls for them
    conditional_required = {
        "action.rejected",  # Only if validation fails
        "disturbance.applied",  # Only if disturbance scheduled
    }
    route_gossip = any(
        e["type"] == "run.config" and e["payload"].get("policy") == "route-gossip-v1"
        for e in events
    )
    if route_gossip:
        # Waiting, no traffic, and no rejection can all be valid policy outcomes.
        # Influence markers are deliberately absent in this mode.
        required = {
            "run.config",
            "world.init",
            "turn.begin",
            "observation.recorded",
            "policy.decision",
            "run.end",
        }
        source_count = sum(
            bool(line.strip()) for line in event_path.read_text().splitlines()
        )
        if len(events) != source_count:
            print("ERROR: policy episode contains invalid records")
            return 1
        if "message.acted_on" in types:
            print("ERROR: legacy influence marker in route-gossip episode")
            return 1
    missing = required - types
    if missing:
        print(f"MISSING required types: {missing}")
        return 1
    else:
        print("All required event types present!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
