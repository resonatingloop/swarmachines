# ./data — pre-recorded seed pack (volume run 2026-11-08)

## Generation Summary

- **Commit**: 0dca625
- **Model**: gemma-4-26b-a4b-it (Adaption API)
- **Total Calls**: 20
- **Total Tokens**: 3,862 input + 7,330 output = 11,192

## Results

### Prompts (8 files)
- prompt: carrier_mesh.md regenerated
- prompt: carrier_ring.md regenerated
- prompt: dispatcher_mesh.md regenerated
- prompt: dispatcher_ring.md **CORRUPTED** — restored to team-authored seed from b72fa7f
- prompt: observer_mesh.md regenerated
- prompt: observer_ring.md regenerated
- prompt: relay_mesh.md regenerated
- prompt: relay_ring.md regenerated

### Scenarios (8 new files generated)
- scenario: scenario-00-mesh.json generated+valid
- scenario: scenario-01-bidirectional-ring.json generated+valid
- scenario: scenario-02-mesh.json generated+valid
- scenario: scenario-03-bidirectional-ring.json generated+valid
- scenario: scenario-04-mesh.json generated+valid
- scenario: scenario-05-bidirectional-ring.json generated+valid
- scenario: scenario-06-mesh.json generated+valid
- scenario: scenario-07-bidirectional-ring.json generated+valid

### Scenarios (3 team-authored preserved)
- scenario: relay-loss-early.json team-authored (preserved)
- scenario: ring-relay-loss.json team-authored (preserved)
- scenario: stale-report.json team-authored (preserved)

### Examples (4 files generated)
- example: relay-loss-reroute generated
- example: capacity-conflict generated
- example: stale-info-recovery generated
- example: ring-neighbor-routing generated

### Examples (1 team-authored preserved)
- example: reroute-coordination.md team-authored (preserved)

## Post-Generation Fixes

1. **dispatcher_ring.md** — API output corrupted (content lost, only provenance footer remained). Restored to team-authored seed from commit b72fa7f.

2. **dispatcher_mesh.md** — Provenance footer incorrectly named model as "glm-53-flash". Corrected to "gemma-4-26b-a4b-it".

3. **Receipts** — Synthetic receipts created in `data/receipts/` from gen-run.log tally. Individual per-call metrics not preserved; receipts show averaged token counts.

4. **MANIFEST.md** — Updated to reflect mixed provenance, restoration, and receipt reconstruction.

## Regeneration

To regenerate this pack faithfully (making fresh API calls):

```bash
export ADAPTION_API_KEY=...
python3 scripts/regenerate_data_pack.py --receipts-dir data/receipts
```

See `scripts/regenerate_data_pack.py` for the faithful regeneration path.
