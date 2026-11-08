# ./data — Generation Log

## Full Regeneration Run (gen-full-20261108)

**Generated**: 2026-11-08T03:56:35.313847+00:00
**Model**: gemma-4-26b-a4b-it
**Run Directory**: `data/runs/gen-full-20261108/`

## Summary

- **Total API Calls**: 38
- **Total Tokens**: 86,578
- **Artifacts Generated**: 38
- **Team-authored Preserved**: 5

## Results by Kind

- example: 8
- prompt: 8
- scenario: 22

## Team-authored Seeds (Preserved, Not Regenerated)

- data/scenarios/relay-loss-early.json
- data/scenarios/ring-relay-loss.json
- data/scenarios/stale-report.json
- data/examples/reroute-coordination.md
- data/prompts/dispatcher_ring.md

## Evidence

- **JSONL Log**: `data/runs/gen-full-20261108/logs/calls.jsonl` (full prompt + response per call)
- **Receipts**: `data/runs/gen-full-20261108/receipts/` (real captured receipts)
- **Run Manifest**: `data/runs/gen-full-20261108/run.json`

## Prior Generation (Superseded)

The pre-workflow generation (commit 0dca625) produced 20 artifacts with
synthetic receipts reconstructed from gen-run-001-tally.log. This full
regeneration run supersedes that work with:

- Real per-call JSONL logs (no reconstruction)
- Real captured receipts (not synthetic)
- Complete provenance chain

The synthetic receipts have been removed — reconstruction is documented in
this log. All current receipts are real captured receipts in
`data/runs/gen-full-20261108/receipts/`.

## Regeneration

To regenerate this pack faithfully (making fresh API calls):

```bash
export ADAPTION_API_KEY=...
python3 scripts/regenerate_data_pack.py --run-id gen-full-20261108
```

---
*Log generated 2026-11-08T03:56:35.313847+00:00.*
*Single full regeneration run — all model-generated items fresh from this run.*
