# Pre-Recorded Data Manifest

**Generated**: 2026-11-08 (volume pass, live Adaption Responses API)
**Model**: gemma-4-26b-a4b-it
**Total API Calls**: 20
**Total Tokens**: 3,862 input + 7,330 output = 11,192

## Provenance Statement

This pack is MIXED-PROVENANCE, stated per file:

- **Model-generated** (20 artifacts): produced by the Adaption Responses API
  (`gemma-4-26b-a4b-it`) from team-authored draft seeds. Each file carries a
  per-file provenance footer naming the model and date.
- **Team-authored** (4 artifacts): prepared without API access (0 calls at
  authoring time), labeled team-authored in-file.

ALL files are **seed material for keyless teammate agents (asterion,
caduceus) to use in freight-in-the-fog coordination experiments**. NONE are
observed experimental evidence — generated or authored, these are inputs,
not results.

## Contents

### Prompts (8 files — all model-generated)

Pilot prompt pack for 4 freight roles under 2 topologies. Each regenerated
from a team-authored draft seed (1 call each):

| File | Role | Topology |
|------|------|----------|
| data/prompts/dispatcher_mesh.md | dispatcher | mesh |
| data/prompts/dispatcher_ring.md | dispatcher | ring |
| data/prompts/relay_mesh.md | relay | mesh |
| data/prompts/relay_ring.md | relay | ring |
| data/prompts/carrier_mesh.md | carrier | mesh |
| data/prompts/carrier_ring.md | carrier | ring |
| data/prompts/observer_mesh.md | observer | mesh |
| data/prompts/observer_ring.md | observer | ring |

### Scenarios (11 files — 8 model-generated, 3 team-authored)

Scenario seeds/configs for the freight world. The 8 generated configs are
structurally validated (topology in {mesh, bidirectional-ring}, turns 8-16,
disturbance format, jobs array):

| File | Topology | Provenance |
|------|----------|------------|
| data/scenarios/scenario-00-mesh.json | mesh | model-generated |
| data/scenarios/scenario-01-bidirectional-ring.json | ring | model-generated |
| data/scenarios/scenario-02-mesh.json | mesh | model-generated |
| data/scenarios/scenario-03-bidirectional-ring.json | ring | model-generated |
| data/scenarios/scenario-04-mesh.json | mesh | model-generated |
| data/scenarios/scenario-05-bidirectional-ring.json | ring | model-generated |
| data/scenarios/scenario-06-mesh.json | mesh | model-generated |
| data/scenarios/scenario-07-bidirectional-ring.json | ring | model-generated |
| data/scenarios/relay-loss-early.json | mesh | team-authored |
| data/scenarios/ring-relay-loss.json | ring | team-authored |
| data/scenarios/stale-report.json | mesh | team-authored |

### Examples (5 files — 4 model-generated, 1 team-authored)

Coordination example exchanges:

| File | Scenario | Provenance |
|------|----------|------------|
| data/examples/relay-loss-reroute.md | reroute after relay goes dark | model-generated |
| data/examples/capacity-conflict.md | contested route at capacity | model-generated |
| data/examples/stale-info-recovery.md | stale bridge report, corrected | model-generated |
| data/examples/ring-neighbor-routing.md | ring routing via two neighbors | model-generated |
| data/examples/reroute-coordination.md | reroute during relay-loss | team-authored |

## API Usage Summary (volume pass)
- **Calls**: 20 (8 prompts + 8 scenarios + 4 examples)
- **Input Tokens**: 3,862
- **Output Tokens**: 7,330
- **Total Tokens**: 11,192
- **Failures**: 0

## Usage Notes
1. Prompts are templates — adapt agent IDs and context as needed for specific runs
2. Scenarios are seeds — actual runs may vary based on agent execution
3. Examples illustrate expected coordination patterns, not guaranteed outcomes
4. Per-file provenance lines are authoritative — preserve them in derived materials
5. Regeneration script: `scripts/generate_data_pack.py` (call-capped, tally in output)

---
*Manifest updated 2026-11-08 after the live-API volume pass.*
