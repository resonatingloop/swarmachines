#!/usr/bin/env python3
"""Verify sample-run.jsonl has all required event types with schema validation."""
import json
import sys
from pathlib import Path

# Add runtime to path for load_events
sys.path.insert(0, str(Path(__file__).parent))

from runner import load_events


def main():
    events = load_events('runtime/sample-run.jsonl')
    types = set(e['type'] for e in events)
    print('Event types in sample-run.jsonl:')
    for t in sorted(types):
        count = sum(1 for e in events if e['type'] == t)
        print(f'  {t}: {count}')
    print(f'Total events: {len(events)}')

    # Check for required types from schema
    required = {
        'run.config', 'world.init', 'turn.begin',
        'observation.recorded',
        'message.sent', 'message.delivered', 'message.seen', 'message.acted_on',
        'action.proposed', 'action.validated', 'action.rejected', 'action.committed',
        'world.changed', 'disturbance.applied',
        'run.end'
    }
    missing = required - types
    if missing:
        print(f'MISSING required types: {missing}')
        return 1
    else:
        print('All required event types present!')
        return 0


if __name__ == "__main__":
    sys.exit(main())
