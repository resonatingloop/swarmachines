#!/usr/bin/env python3
"""Verify sample-run.jsonl has all required event types."""
import json

events = [json.loads(line) for line in open('runtime/sample-run.jsonl')]
types = set(e['type'] for e in events)
print('Event types in sample-run.jsonl:')
for t in sorted(types):
    count = sum(1 for e in events if e['type'] == t)
    print(f'  {t}: {count}')
print(f'Total events: {len(events)}')

# Check for required types from schema
required = {'run.config', 'world.init', 'turn.begin', 'observation.recorded', 
            'message.sent', 'message.delivered', 'message.seen',
            'action.proposed', 'action.validated', 'action.committed',
            'disturbance.applied', 'run.end'}
missing = required - types
if missing:
    print(f'MISSING required types: {missing}')
else:
    print('All required event types present!')
