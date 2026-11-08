# Pre-Recorded Data Manifest

**Generated**: 2026-11-08T03:56:35.313847+00:00
**Run ID**: gen-full-20261108
**Model**: gemma-4-26b-a4b-it

## Provenance Statement

This pack is generated from a **SINGLE FULL REGENERATION RUN** (gen-full-20261108).

- **Model-generated** (38 artifacts): produced by the Adaption Responses API
  (`gemma-4-26b-a4b-it`) in this run. Each file carries a per-file provenance footer.
  Full JSONL logs with complete prompts and responses: `data/runs/gen-full-20261108/logs/calls.jsonl`
  Real captured receipts: `data/runs/gen-full-20261108/receipts/`

- **Team-authored** (5 artifacts): preserved from prior work, NOT regenerated:
  - `data/scenarios/relay-loss-early.json`
  - `data/scenarios/ring-relay-loss.json`
  - `data/scenarios/stale-report.json`
  - `data/examples/reroute-coordination.md`
  - `data/prompts/dispatcher_ring.md`

ALL files are **seed material for keyless teammate agents** to use in
freight-in-the-fog coordination experiments. NONE are observed experimental
evidence — these are inputs, not results.

## Contents

### Prompts (8 model-generated)

| File | Role | Topology |
|------|------|----------|
| data/prompts/carrier_mesh.md | carrier | mesh |
| data/prompts/carrier_ring.md | carrier | ring |
| data/prompts/dispatcher_mesh.md | dispatcher | mesh |
| data/prompts/dispatcher_ring.md | dispatcher | ring |
| data/prompts/observer_mesh.md | observer | mesh |
| data/prompts/observer_ring.md | observer | ring |
| data/prompts/relay_mesh.md | relay | mesh |
| data/prompts/relay_ring.md | relay | ring |

### Scenarios (22 model-generated + 4 team-authored)

| File | Scenario | Provenance |
|------|----------|------------|
| data/scenarios/fog-mesh.json | fog-mesh | model-generated |
| data/scenarios/fog-ring.json | fog-ring | model-generated |
| data/scenarios/relay-loss-mesh.json | relay-loss-mesh | model-generated |
| data/scenarios/relay-loss-ring.json | relay-loss-ring | model-generated |
| data/scenarios/peer-mute-mesh.json | peer-mute-mesh | model-generated |
| data/scenarios/peer-mute-ring.json | peer-mute-ring | model-generated |
| data/scenarios/stale-report-mesh.json | stale-report-mesh | model-generated |
| data/scenarios/stale-report-ring.json | stale-report-ring | model-generated |
| data/scenarios/capacity-conflict-mesh.json | capacity-conflict-mesh | model-generated |
| data/scenarios/capacity-conflict-ring.json | capacity-conflict-ring | model-generated |
| data/scenarios/contested-deliveries-mesh.json | contested-deliveries-mesh | model-generated |
| data/scenarios/contested-deliveries-ring.json | contested-deliveries-ring | model-generated |
| data/scenarios/route-gossip-mesh.json | route-gossip-mesh | model-generated |
| data/scenarios/route-gossip-ring.json | route-gossip-ring | model-generated |
| data/scenarios/bridge-closure-mesh.json | bridge-closure-mesh | model-generated |
| data/scenarios/bridge-closure-ring.json | bridge-closure-ring | model-generated |
| data/scenarios/dual-disruption-mesh.json | dual-disruption-mesh | model-generated |
| data/scenarios/dual-disruption-ring.json | dual-disruption-ring | model-generated |
| data/scenarios/cascading-failure-mesh.json | cascading-failure-mesh | model-generated |
| data/scenarios/cascading-failure-ring.json | cascading-failure-ring | model-generated |
| data/scenarios/scenario-00-mesh.json | scenario-00-mesh | model-generated |
| data/scenarios/scenario-00-ring.json | scenario-00-ring | model-generated |
| data/scenarios/relay-loss-early.json | relay-loss-early | team-authored |
| data/scenarios/ring-relay-loss.json | ring-relay-loss | team-authored |
| data/scenarios/stale-report.json | stale-report | team-authored |

### Examples (8 model-generated + 1 team-authored)

| File | Description | Provenance |
|------|-------------|------------|
| data/examples/relay-loss-reroute.md | Relay Loss Reroute | model-generated |
| data/examples/relay-loss-reroute.md | Relay Loss Reroute | model-generated |
| data/examples/capacity-conflict.md | Capacity Conflict | model-generated |
| data/examples/capacity-conflict.md | Capacity Conflict | model-generated |
| data/examples/stale-info-recovery.md | Stale Info Recovery | model-generated |
| data/examples/stale-info-recovery.md | Stale Info Recovery | model-generated |
| data/examples/ring-neighbor-routing.md | Ring Neighbor Routing | model-generated |
| data/examples/ring-neighbor-routing.md | Ring Neighbor Routing | model-generated |
| data/examples/reroute-coordination.md | Reroute coordination | team-authored |

## Run Evidence

**Run Directory**: `data/runs/gen-full-20261108/`

- `artifacts/` — all generated files (canonical source)
- `logs/calls.jsonl` — complete JSONL stream (full prompt + response per call)
- `receipts/` — real captured receipts
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
*Manifest generated 2026-11-08T03:56:35.313847+00:00 from run gen-full-20261108.*
*Single full regeneration — supersedes all prior generation passes.*
