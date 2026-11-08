# dataset pack — publishable swarm runs with verifiable provenance

## ADDED Requirements

### Requirement: fifteen seeded task instances

the pack SHALL contain exactly 15 task instances for the freight-in-the-fog
world, each defined by a versioned config carrying seed, graph, job set,
agent roster, topology, and disturbance schedule, committed to the repo.
the original five (seeds 42/137/299/413/571) SHALL be retained; the ten
additional instances SHALL vary seed, job set, topology, and disturbance
schedule, and mesh, ring, and hub-spoke topologies SHALL all be
represented. no two instances SHALL share both seed and job set, and at
least one instance SHALL use the mute-one-agent disturbance. the owner
ruled on 2026-11-08 that all 15 ship as one drop — no partial release.

#### Scenario: distinct instances replay deterministically

- **WHEN** the 15 configs are loaded and each is replayed from its seed
- **THEN** no two configs share both seed and job set, all three
  topologies appear, and each replay is byte-identical to its first run

### Requirement: governed runs with full provenance

each task instance SHALL be executed through the governed task-submission
workflow (prepare → submit → capture) with one `calls.jsonl` line per
adaption call carrying the full prompt text, the full response text, model
id, tokens in/out, and a receipt reference, plus one persisted receipt per
call. the api key SHALL never appear in any pack file.

#### Scenario: receipts match the transcript

- **WHEN** a run's `calls.jsonl` is cross-checked against its receipts
- **THEN** every line has a receipt whose model and token counts match the
  line, and no orphan receipts exist

#### Scenario: no key in the pack

- **WHEN** the shipped pack is scanned for the credential's value and
  common key prefixes
- **THEN** no match is found in any file

### Requirement: artifacts extracted from the persisted log

every shipped artifact SHALL be extracted from the persisted `calls.jsonl`
response fields after the run completes, with content identical (not
paraphrased) to its call's response field, and SHALL carry one label:
`model-generated` (model id + receipt ref), `team-authored` (byte-exact
from the git commit that held it), or `reconstructed-from-log`.

#### Scenario: wrong-side guard

- **WHEN** each model-generated artifact's parsed content is compared to
  its call's response field
- **THEN** they are equal for every artifact

#### Scenario: team seeds unchanged

- **WHEN** a team-authored file is compared to the git commit that held it
- **THEN** the bytes match exactly

### Requirement: pack layout and manifest

each run SHALL be a self-contained pack under `data/runs/<run_id>/`
(`artifacts/`, `logs/calls.jsonl`, `receipts/`, `run.json`), and the
top-level MANIFEST SHALL carry every count and mapping such that recomputing
it from disk reproduces it exactly.

#### Scenario: manifest equals disk

- **WHEN** the MANIFEST counts are recomputed from the files on disk
- **THEN** every number matches, after every fix

### Requirement: complete transcripts — nothing omitted

the dataset SHALL contain the complete conversation of every run with full
text: every inter-agent message, every observation delivered to an agent,
every action and its outcome, and every disturbance event. every model
prompt and response SHALL appear verbatim — full prompt text and full
response text in `calls.jsonl`, with no truncation, no summarization, and
no sampling. the raw per-run layer (`logs/calls.jsonl`, `receipts/`, the
sealed event log, and `artifacts/`) SHALL ship inside the HF repo
alongside the curated tables, so the dataset is auditable without leaving
huggingface.

#### Scenario: verbatim against source

- **WHEN** a sampled record's content and its paired call's prompt and
  response fields are diffed against the source event log and
  `calls.jsonl`
- **THEN** they match verbatim, byte for byte

#### Scenario: raw layer ships

- **WHEN** the uploaded HF repo is inspected
- **THEN** every run directory contains `calls.jsonl`, its receipts, the
  sealed event log, and its artifacts

### Requirement: HF dataset structure — per-turn, agent-labeled

the pack is a swarm dataset, not a training corpus: it SHALL ship NO
train/test/validation split. the primary table `data/records.jsonl` SHALL
carry one record per event (message, observation, action, disturbance)
with explicit labels: `run_id`, `task_id`, `seed`, `topology`, `turn`,
`agent_id`, `agent_role`, `event_type`, `content` (full text), `model`,
`tokens_in`, `tokens_out`, `receipt_ref` for model-generated events, and
`provenance`. a second table `data/runs.jsonl` SHALL carry one summary
record per task-run (config hash, totals, outcome metrics, artifact
index). the `README.md` dataset card SHALL declare both tables via
`configs` in its yaml frontmatter along with license, tags, and the
provenance section (model `glm-53-flash`, provider adaption, repo commit
at generation time, request/token totals from receipts).

#### Scenario: card discloses generation

- **WHEN** the dataset card is read
- **THEN** it names the model, provider, commit, and token totals, and
  marks all model-generated content as such

#### Scenario: records are agent-labeled and turn-ordered

- **WHEN** `data/records.jsonl` is grouped by `run_id` and ordered by
  `turn`
- **THEN** every record has non-empty `agent_id` and `event_type`, and the
  ordering is consistent with the run's event log

#### Scenario: no split

- **WHEN** the repo layout is inspected
- **THEN** there is no train/validation/test directory or split field —
  only `data/records.jsonl` and `data/runs.jsonl`

### Requirement: audit gate before publish

the pack SHALL pass the six-step provenance audit — transcript validity,
receipt cross-check, artifact content match, team-seed byte-exactness,
manifest reconciliation, no mislabeled artifacts — with per-step results
recorded, before any upload. upload SHALL use only owner-provided
credentials from the environment, and the credential SHALL never enter
logs, artifacts, or the card.

#### Scenario: audit verdict recorded

- **WHEN** the verifier runs the six-step audit on the shipped pack
- **THEN** each step reports pass/fail with evidence and no step is skipped
