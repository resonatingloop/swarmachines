# Topology Mapping Ruling

**Date:** 2026-11-07  
**Authority:** Owner directive (GO issued ~18:05Z)  
**Change:** add-turn-seam-event-log
**Ordering:** This ruling is recorded before any comparison code is written; no comparison implementation lands until this record merges.

## Comparison Arms

The owner has ruled the topology comparison pair for the hackathon evaluation:

1. **fully-connected** (all-pairs communication)
2. **bidirectional ring** with peer-mute disturbance

These are the two arms to be compared under the mute-one-agent disruption scenario.

## Code Verification: mesh = fully-connected

The existing `mesh` topology in `runtime/runner.py` (`CommunicationTopology.can_communicate`) was code-verified:

```python
if self.topology == "mesh":
    # All agents can communicate with all others (unless disturbed)
    if from_agent != to_agent:
        return True, ""
    return False, "self-communication not allowed"
```

**Finding:** mesh topology implements all-pairs communication (fully-connected). Every agent can message every other agent directly, with no intermediary required.

## Scaffolding (Not Comparison Arms)

The following topologies and disturbance variants are **scaffolding only** — useful for development and testing, but not part of the formal comparison:

- **hub-spoke**: communication routing through a hub agent
- **hub-mute relay-loss**: disturbance targeting the hub in hub-spoke topology

These remain in the codebase for development purposes but are excluded from the report's topology comparison.

## Next Steps

- swarmachines-9e5: implement bidirectional ring topology config + peer-mute variant (a fixed non-hub agent's communication muted while local actions continue)
- Extend topology-independence test to cover ring topology
- Comparison evaluation: fully-connected (mesh) vs bidirectional ring, both under peer-mute disturbance
