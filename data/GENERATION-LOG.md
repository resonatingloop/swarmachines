# ./data — Generation Log

## Full Regeneration Run (gen-full-20261108)

**Generated**: 2026-11-08T03:56:35.313847+00:00
**Model**: gemma-4-26b-a4b-it
**Run Directory**: `data/runs/gen-full-20261108/`

## Summary

- **Total API Calls**: 38
- **Total Tokens**: 86,578
- **Artifacts Generated**: 34 distinct (8 prompts + 22 scenarios + 4 examples)
- **Team-authored Preserved**: 5

## Results by Kind

- example: 4 model-generated (MESH calls 31, 33, 35, 37) + 4 ring-only in artifacts/
- prompt: 8 (team-authored base templates; calls 1-8 recorded model acknowledgments)
- scenario: 22 (model-enhanced JSON, calls 9-30)

## Team-authored Seeds (Preserved, Not Regenerated)

- data/scenarios/relay-loss-early.json
- data/scenarios/ring-relay-loss.json
- data/scenarios/stale-report.json
- data/examples/reroute-coordination.md

Note: data/prompts/dispatcher_ring.md was regenerated in call 4 (model acknowledgment response recorded).

## Evidence

- **JSONL Log**: `data/runs/gen-full-20261108/logs/calls.jsonl` (full prompt + response per call)
- **Receipts**: `data/runs/gen-full-20261108/receipts/` (34 real captured + 4 reconstructed from calls.jsonl)
- **Run Manifest**: `data/runs/gen-full-20261108/run.json`

## Prior Generation (Superseded)

The pre-workflow generation (commit 0dca625) produced 20 artifacts with
synthetic receipts reconstructed from gen-run-001-tally.log. This full
regeneration run supersedes that work with:

- Real per-call JSONL logs (no reconstruction)
- Real captured receipts for 34 calls; 4 MESH example receipts reconstructed from calls.jsonl
- Complete provenance chain

The synthetic receipts have been removed — reconstruction is documented in
this log. Of the 38 current receipts, 34 are real captured receipts and 4
(MESH example calls 31, 33, 35, 37) are reconstructed from calls.jsonl in
`data/runs/gen-full-20261108/receipts/`.

**Correction note (2026-11-08)**: This log's count language was reconciled with disk:
- "Artifacts Generated: 38" corrected to 34 distinct (8 prompts + 22 scenarios + 4 examples)
- Example tally clarified: 4 model-generated MESH narratives + 4 ring-only outputs in artifacts/
- dispatcher_ring.md removed from preserved list (call 4 shows model acknowledgment was recorded)
- Receipts description updated to match GENERATION-LOG.md claims

## Regeneration

To regenerate this pack faithfully (making fresh API calls):

```bash
export ADAPTION_API_KEY=...
python3 scripts/regenerate_data_pack.py --run-id gen-full-20261108
```

---
*Log generated 2026-11-08T03:56:35.313847+00:00.*
*Single full regeneration run — all model-generated items fresh from this run.*
