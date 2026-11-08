# add the HF task-dataset pack

## why

the pipeline now produces governed multi-agent runs with real provenance —
#28 recorded 38 adaption calls, 43 artifacts, full transcripts and receipts,
and #61/#62 hardened the regen path after the audit caught 9 provenance
slips. the same machinery can emit a publishable dataset: five freight-world
task instances, each executed by the 4-agent swarm, shipped with the full
transcript, per-call receipts, extracted artifacts, and outcome metrics.
that gives the hackathon a released testbed artifact (track 1) and gives the
report a citable data release.

the owner floated the scope in #pug-chat on report day (5 tasks, swarms go
after them, huggingface-ready). this change builds the machinery offline and
dry-runs it; executing the real adaption runs is gated on the coordinator
go after adversarial verification.

## what changes

- `dataset_pack` module: versioned task-instance configs (seed, graph, job
  set, agent roster, topology, disturbance schedule) with a
  deterministic-replay check
- runner glue: each instance executes through the governed task-submission
  workflow (prepare → submit → capture) — no ad-hoc api calls
- per-run pack under `data/runs/<run_id>/`: `artifacts/`, `logs/calls.jsonl`
  (full prompt + response per line), `receipts/`, sealed event log, `run.json`
- extractor runs after the run: artifacts are pulled from the persisted
  jsonl response fields (never written prompt-side), each labeled
  `model-generated` / `team-authored` / `reconstructed-from-log`
- packager: top-level MANIFEST reconciled against disk; HF README dataset
  card (yaml frontmatter, provenance section); `data/records.jsonl` with
  one agent-labeled record per event (run, task, seed, topology, turn,
  agent_id, agent_role, event_type, full content, tokens, receipt ref,
  provenance) plus `data/runs.jsonl` per-run summaries — no train/test
  split; this is a swarm dataset, not a training corpus
- upload script reading credentials from the environment only; packaging
  and audit are fully offline; two targets: HuggingFace (full pack) and
  Adaption datasets API (records + runs tables)

## amendment (2026-11-08, owner ruling)

scope expanded from 5 to 15 task instances (10 additional with varied
seeds, job sets, topologies, disturbance schedules; mesh, ring, and
hub-spoke all represented) and the release ships as ONE drop — the HF +
Adaption upload happens only after all 15 governed runs clear the
verifier's pack audit. the machinery verification (rounds 1-3) is
unaffected: it validated the pipeline against the original 5-config
contract.

## out of scope

- topology-paired runs (mesh vs ring per task) — stretch, follow-up change
- new runtime features or world changes
- any upload without owner-provided credentials in the environment

## acceptance

requirements verified by the verifier's six-step provenance audit; owner
accepts before archival. draft until then.
