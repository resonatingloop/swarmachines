# Pre-Recorded Data Manifest

**Generated**: 2026-11-08T03:56:35.313847+00:00
**Run ID**: gen-full-20261108
**Model**: gemma-4-26b-a4b-it

## Provenance Statement

This pack contains **38 total artifacts** with honest provenance labeling:

- **Model-generated** (26 artifacts): produced by the Adaption Responses API
  (`gemma-4-26b-a4b-it`) in run gen-full-20261108. Each file carries a per-file
  provenance footer. Full JSONL logs with complete prompts and responses:
  `data/runs/gen-full-20261108/logs/calls.jsonl`

- **Team-authored** (12 artifacts): preserved from prior work or used as base templates:
  - 8 prompt templates (`data/prompts/*.md`) — base templates authored by team;
    model acknowledgment responses recorded in run log (calls 1-8)
  - 4 seed scenarios/examples restored from commit 0dca625:
    - `data/scenarios/relay-loss-early.json`
    - `data/scenarios/ring-relay-loss.json`
    - `data/scenarios/stale-report.json`
    - `data/examples/reroute-coordination.md`

ALL files are **seed material for keyless teammate agents** to use in
freight-in-the-fog coordination experiments. NONE are observed experimental
evidence — these are inputs, not results.

## Contents

### Prompts (8 team-authored base templates)

| File | Role | Topology | Provenance |
|------|------|----------|------------|
| data/prompts/carrier_mesh.md | carrier | mesh | team-authored base, model acknowledgment in run log (call 1) |
| data/prompts/carrier_ring.md | carrier | ring | team-authored base, model acknowledgment in run log (call 2) |
| data/prompts/dispatcher_mesh.md | dispatcher | mesh | team-authored base, model acknowledgment in run log (call 3) |
| data/prompts/dispatcher_ring.md | dispatcher | ring | team-authored base (0dca625), model acknowledgment in run log (call 4) |
| data/prompts/observer_mesh.md | observer | mesh | team-authored base, model acknowledgment in run log (call 5) |
| data/prompts/observer_ring.md | observer | ring | team-authored base, model acknowledgment in run log (call 6) |
| data/prompts/relay_mesh.md | relay | mesh | team-authored base, model acknowledgment in run log (call 7) |
| data/prompts/relay_ring.md | relay | ring | team-authored base, model acknowledgment in run log (call 8) |

### Scenarios (22 model-generated + 3 team-authored)

| File | Scenario | Provenance |
|------|----------|------------|
| data/scenarios/fog-mesh.json | fog-mesh | model-enhanced JSON (call 9) |
| data/scenarios/fog-ring.json | fog-ring | model-enhanced JSON (call 10) |
| data/scenarios/relay-loss-mesh.json | relay-loss-mesh | model-enhanced JSON (call 11) |
| data/scenarios/relay-loss-ring.json | relay-loss-ring | model-enhanced JSON (call 12) |
| data/scenarios/peer-mute-mesh.json | peer-mute-mesh | model-enhanced JSON (call 13) |
| data/scenarios/peer-mute-ring.json | peer-mute-ring | model-enhanced JSON (call 14) |
| data/scenarios/stale-report-mesh.json | stale-report-mesh | model-enhanced JSON (call 15) |
| data/scenarios/stale-report-ring.json | stale-report-ring | model-enhanced JSON (call 16) |
| data/scenarios/capacity-conflict-mesh.json | capacity-conflict-mesh | model-enhanced JSON (call 17) |
| data/scenarios/capacity-conflict-ring.json | capacity-conflict-ring | model-enhanced JSON (call 18) |
| data/scenarios/contested-deliveries-mesh.json | contested-deliveries-mesh | model-enhanced JSON (call 19) |
| data/scenarios/contested-deliveries-ring.json | contested-deliveries-ring | model-enhanced JSON (call 20) |
| data/scenarios/route-gossip-mesh.json | route-gossip-mesh | model-enhanced JSON (call 21) |
| data/scenarios/route-gossip-ring.json | route-gossip-ring | model-enhanced JSON (call 22) |
| data/scenarios/bridge-closure-mesh.json | bridge-closure-mesh | model-enhanced JSON (call 23) |
| data/scenarios/bridge-closure-ring.json | bridge-closure-ring | model-enhanced JSON (call 24) |
| data/scenarios/dual-disruption-mesh.json | dual-disruption-mesh | model-enhanced JSON (call 25) |
| data/scenarios/dual-disruption-ring.json | dual-disruption-ring | model-enhanced JSON (call 26) |
| data/scenarios/cascading-failure-mesh.json | cascading-failure-mesh | model-enhanced JSON (call 27) |
| data/scenarios/cascading-failure-ring.json | cascading-failure-ring | model-enhanced JSON (call 28) |
| data/scenarios/scenario-00-mesh.json | scenario-00-mesh | model-enhanced JSON (call 29) |
| data/scenarios/scenario-00-ring.json | scenario-00-ring | model-enhanced JSON (call 30) |
| data/scenarios/relay-loss-early.json | relay-loss-early | team-authored (restored from 0dca625) |
| data/scenarios/ring-relay-loss.json | ring-relay-loss | team-authored (restored from 0dca625) |
| data/scenarios/stale-report.json | stale-report | team-authored (restored from 0dca625) |

### Examples (4 model-generated + 1 team-authored)

| File | Description | Provenance |
|------|-------------|------------|
| data/examples/relay-loss-reroute.md | Relay Loss Reroute (MESH) | model-generated narrative (call 31) |
| data/examples/capacity-conflict.md | Capacity Conflict (MESH) | model-generated narrative (call 33) |
| data/examples/stale-info-recovery.md | Stale Info Recovery (MESH) | model-generated narrative (call 35) |
| data/examples/ring-neighbor-routing.md | Ring Neighbor Routing (MESH) | model-generated narrative (call 37) |
| data/examples/reroute-coordination.md | Reroute coordination | team-authored (restored from 0dca625) |

## Run Evidence

**Run Directory**: `data/runs/gen-full-20261108/`

- `logs/calls.jsonl` — complete JSONL stream (38 calls, full prompt + response per call)
- `receipts/` — real captured receipts for calls with API responses
- `run.json` — run manifest with totals

## Regeneration Path

To regenerate this pack faithfully:

```bash
export ADAPTION_API_KEY=...
python3 scripts/regenerate_data_pack.py --run-id gen-full-20261108
```

## Usage Notes

1. Prompts are templates — adapt agent IDs and context as needed
2. Scenarios are seeds — actual runs may vary based on agent execution
3. Examples illustrate expected coordination patterns, not guaranteed outcomes
4. Per-file provenance lines are authoritative — preserve in derived materials

---
*Manifest corrected 2026-11-08 — honest provenance labeling after audit FIX-FIRST.*
*Total: 38 artifacts (26 model-generated, 12 team-authored).*
