# Coordination Example: Reroute During Relay Loss

## Context
- **Run ID**: example-reroute-001
- **Turn**: 3 (post-disruption, agent A unreachable since turn 2)
- **Topology**: Mesh (physical graph unchanged; agent A muted)
- **Active Agents**: B (east), C (south), D (relay-a)
- **Situation**: Med-kit freight needs west→south delivery; east-bridge closed at turn 2

## Message Exchange

### Turn 3, Agent C (South Depot)
**Observation**: 
- Local queue: 1 med-kit pending delivery to south
- Known closures: east-bridge (from turn 2 report)
- Visible routes: west→south (open), south→east (closed at bridge)

**Message Sent** (to B):
```
{
  "message_id": "m-c3-001",
  "to": "b",
  "content": "East-bridge confirmed closed. Med-kit at west needs alternate route. Can you verify west→south capacity?",
  "observation_turn": 3,
  "provenance": "team-authored seed material prepared without API access (0 calls); NOT model-generated and NOT observed experimental evidence"
}
```

### Turn 3, Agent B (East Depot)
**Received**: Message m-c3-001 from C (delivered turn 3)

**Observation**:
- Local queue: empty
- Known closures: east-bridge
- Visible routes: east→west (open), east→south (closed), west→south (unknown locally)

**Message Sent** (to D):
```
{
  "message_id": "m-b3-001",
  "to": "d",
  "content": "C reports bridge closed. Need west→south route status for med-kit reroute. Can you query west depot visibility?",
  "observation_turn": 3,
  "provenance": "team-authored seed material prepared without API access (0 calls); NOT model-generated and NOT observed experimental evidence"
}
```

### Turn 3, Agent D (Relay-A Hub)
**Received**: Message m-b3-001 from B (delivered turn 3)

**Observation**:
- Local queue: 1 supplies pending
- Known closures: east-bridge
- Visible routes: all hub connections visible (west, east, south)
- West→south route status: OPEN, capacity 2/3

**Message Sent** (to B and C):
```
{
  "message_id": "m-d3-001",
  "to": ["b", "c"],
  "content": "West→south route OPEN, capacity available (2/3). Recommend direct reroute west→south, bypassing east hub entirely.",
  "observation_turn": 3,
  "provenance": "team-authored seed material prepared without API access (0 calls); NOT model-generated and NOT observed experimental evidence"
}
```

### Turn 4, Action Resolution
**Agent C Action** (committed):
```json
{
  "action_id": "act-c4-001",
  "type": "route_freight",
  "details": {
    "freight": "med-kit",
    "path": ["west", "south"],
    "bypasses": ["east"],
    "reason": "east-bridge closed; direct route available per D's report"
  }
}
```

**Outcome**:
- Freight rerouted successfully via west→south
- Delivery completed turn 6
- Recovery interval: 2 turns (disruption turn 2 → resumed delivery turn 4)

## Analysis
This exchange demonstrates:
1. **Distributed information aggregation**: C knows bridge status, D knows west→south capacity
2. **Multi-hop coordination without relay**: B intermediates despite A's absence
3. **Provenance tracking**: Each message carries observation turn and generation note
4. **Successful recovery**: Delivery completed despite disruption

## Provenance
- team-authored seed material prepared without API access (0 calls); NOT model-generated and NOT observed experimental evidence
