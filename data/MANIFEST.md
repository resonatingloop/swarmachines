# Pre-Recorded Data Manifest

**Generated**: 2026-11-08 (volume pass, live Adaption Responses API)
**Model**: gemma-4-26b-a4b-it
**Total API Calls**: 20
**Total Tokens**: 3,862 input + 7,330 output = 11,192
**Commit**: 0dca625

## Provenance Statement

This pack is **MIXED-PROVENANCE**, stated per file:

- **Model-generated** (20 artifacts): produced by the Adaption Responses API
  (`gemma-4-26b-a4b-it`) from team-authored draft seeds. Each file carries a
  per-file provenance footer naming the model and date. Receipts for all calls
  are stored in `data/receipts/` (synthetic, reconstructed from gen-run.log tally).

- **Team-authored** (4 artifacts): prepared without API access (0 calls at
  authoring time), labeled team-authored in-file:
  - `data/scenarios/relay-loss-early.json`
  - `data/scenarios/ring-relay-loss.json`
  - `data/scenarios/stale-report.json`
  - `data/examples/reroute-coordination.md`

- **Restored** (1 artifact): `data/prompts/dispatcher_ring.md` was regenerated
  but the API output was corrupted (content lost). Restored to team-authored
  seed from commit b72fa7f.

ALL files are **seed material for keyless teammate agents (asterion,
caduceus) to use in freight-in-the-fog coordination experiments**. NONE are
observed experimental evidence — generated or authored, these are inputs,
not results.

## Contents

### Prompts (8 files — 7 model-generated, 1 restored team-authored)

Pilot prompt pack for 4 freight roles under 2 topologies:

| File | Role | Topology | Provenance |
|------|------|----------|------------|
| data/prompts/dispatcher_mesh.md | dispatcher | mesh | model-generated |
| data/prompts/dispatcher_ring.md | dispatcher | ring | team-authored (restored) |
| data/prompts/relay_mesh.md | relay | mesh | model-generated |
| data/prompts/relay_ring.md | relay | ring | model-generated |
| data/prompts/carrier_mesh.md | carrier | mesh | model-generated |
| data/prompts/carrier_ring.md | carrier | ring | model-generated |
| data/prompts/observer_mesh.md | observer | mesh | model-generated |
| data/prompts/observer_ring.md | observer | ring | model-generated |

### Scenarios (11 files — 8 model-generated, 3 team-authored)

Scenario seeds/configs for the freight world:

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

- **Calls**: 20 (7 prompts + 8 scenarios + 4 examples; 1 prompt failed/restored)
- **Input Tokens**: 3,862
- **Output Tokens**: 7,330
- **Total Tokens**: 11,192
- **Failures**: 0 (1 corrupted output restored from seed)

## Receipts

Receipts for all 20 API calls are stored in `data/receipts/`. Each receipt contains:
- call_name, call_number, timestamp, model
- input_tokens, output_tokens, total_tokens
- item_path, kind, provenance

Note: Receipts are synthetic, reconstructed from the gen-run.log tally
(commit 0dca625). Individual per-call metrics were not preserved; receipts
show averaged token counts.

## Regeneration Path

To regenerate this pack faithfully:

```bash
export ADAPTION_API_KEY=...
export PYTHONPATH=/opt/data/profiles/dev/home/.local/lib/python3.14/site-packages
python3 scripts/regenerate_data_pack.py --receipts-dir data/receipts
```

The `scripts/regenerate_data_pack.py` script:
1. Reads team-authored seeds (preserved, not overwritten)
2. Makes actual API calls (not hardcoded content)
3. Saves receipts for each call
4. Labels provenance correctly per file

## Usage Notes

1. Prompts are templates — adapt agent IDs and context as needed for specific runs
2. Scenarios are seeds — actual runs may vary based on agent execution
3. Examples illustrate expected coordination patterns, not guaranteed outcomes
4. Per-file provenance lines are authoritative — preserve them in derived materials

---
*Manifest updated 2026-11-08 after the live-API volume pass (commit 0dca625).*
*Corrupted dispatcher_ring.md restored; provenance corrected; receipts added.*
