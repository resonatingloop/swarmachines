# tasks — add-hf-task-dataset

- [ ] 1. claim the bd issue; branch off master per eng-standards
- [ ] 2. `dataset_pack/configs.py`: 15 versioned task-instance configs — retain the original 5 (seeds 42/137/299/413/571), add 10 varied (seed, graph, job set, roster, topology, disturbance schedule; mesh/ring/hub-spoke all represented; ≥1 mute-one-agent) + deterministic-replay test
- [ ] 3. `dataset_pack/run.py`: governed run glue (prepare → submit → capture); per-call `calls.jsonl` line (ts, run, call, role, topology, artifact, model, FULL prompt, FULL response, tokens_in, tokens_out, receipt, provenance); one receipt per call; `run.json`
- [ ] 4. `dataset_pack/extract.py`: post-run artifact extraction from the persisted jsonl response fields; content-identity check vs response; labels `model-generated` / `team-authored` / `reconstructed-from-log`
- [ ] 5. `dataset_pack/package.py`: MANIFEST reconciliation; README dataset card (license, tags, `configs` declaring the two tables, provenance: model id, provider, commit, token totals from receipts); `data/records.jsonl` — one row per event: run_id, task_id, seed, topology, turn, agent_id, agent_role, event_type, FULL content, model/tokens_in/tokens_out/receipt_ref, provenance; `data/runs.jsonl` per-run summary; NO train/test split; ship the raw per-run layer (calls.jsonl, receipts/, sealed event log, artifacts/) inside the HF repo — dataset auditable on HF alone
- [ ] 6. `dataset_pack/upload.py`: two targets — HF (full pack) and Adaption datasets API (records + runs tables) — reading credentials from env only; refuses without token; token never logged or written; return codes checked
- [ ] 7. offline dry-run: packager produces a valid card + manifest from a fixture log with zero model calls
- [ ] 8. tests: wrong-side guard, manifest-equals-disk, card required fields, no-key-in-pack scan, verbatim-transcript diff (records/calls vs source event log, byte for byte), raw-layer-presence in the repo layout; ruff + full suite green
- [ ] 9. PR referencing add-hf-task-dataset
- [ ] 10. coordinator go (after verification GO): merge PR #64, extend configs to 15, execute ALL 15 governed runs through the governed workflow; regenerate MANIFEST counts from disk
- [ ] 11. verifier: six-step provenance audit on the shipped pack (bd swarmachines-b1w)
