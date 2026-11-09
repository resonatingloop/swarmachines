# model-swarm evidence expansion

status: accepted

owner: colette · implementation: asterion · independent review: caduceus/pug

amendment accepted 2026-11-08: after the retained v0 calibration exhausted the
original 160-token/two-call bound, colette accepted one repair-calibration call
per panel model at 512 output tokens. exact-json parsing, the shared ledger,
zero automatic retries, and the 10.000-credit ceiling remain unchanged. any
model that is still provider-incomplete after its repair call stops there.

replacement amendment accepted 2026-11-08: after the repair calibration left
only glm across the full action seam, colette cleared the evidence-led
replacement branch. keep the exact-json contract; add current hosted models
`qwen3.8-27b` and `deepseek-v4-flash`; give each exactly one 512-token
calibration call. the 2026-11-08 caller-specific hosted catalog listed both
without a shutdown date but exposed no inference rates. each call therefore
retains a fixed 1.000-credit conservative ledger reservation rather than an
invented rate-derived charge. the shared 10.000-credit ceiling, no-retry rule
and interpretation stop remain unchanged.

fallback continuation: if either first replacement fails, calibrate
`gemma-4-31b-it` once for family diversity; only if it fails, calibrate
`glm-5.2` once. both use the same 512-token exact-json contract and retained
1.000-credit reservation. stop the ladder as soon as three models have crossed
the full action seam or the hosted candidates are exhausted.

contract-v2 amendment accepted 2026-11-08: the replacement calibration showed
that exact-json compliance was confounded with response-wrapper and reasoning
length behavior. accept either raw json or exactly one solitary `json` markdown
fence with no surrounding prose, while preserving the exact two-key object,
candidate-action allowlist, 160-character reason bound and all categorical
rejections. raise the provider output ceiling uniformly to 2,048 tokens and
record both the contract version and ceiling on new decisions. old sealed
evidence remains immutable and valid under its recorded request bound. perform
one bounded `gemma-4-31b-it` calibration under v2; if it still fails, stop and
interpret before another provider call. the shared 10.000-credit ceiling,
fixed 1.000-credit reservation, private evidence boundary and no-retry rule are
unchanged.

## acceptance

colette accepted this bounded evidence expansion in the coding session on
2026-11-08: proceed with a provider-backed swarm comparison under an absolute
10.000-credit ceiling, stage the work so analysis capacity gates expansion,
and compare multiple models. acceptance authorizes the implementation and the
staged provider calls below. it does not authorize training, publication,
dataset upload, or spending beyond the fixed ceiling.

## owner view

- change: add one provider-backed freight action policy to the existing runner,
  then record a balanced three-model pilot whose work survives the intervention.
- before: the adapter can call adaption, but the runner never invokes it; the
  frozen seed-42 pair completed all jobs before peer-mute and cannot measure a
  task effect.
- after: model decisions pass through the existing validator and event log,
  every call has private evidence and budget accounting, and expansion stops at
  explicit analysis gates.
- authority: this accepted spec owns the transition. existing freight, event,
  seal, analyzer, and provider credential contracts remain governing behavior.

## owner decisions

### fixed reports, model-selected actions

- recommendation: retain the existing typed route-report transport and let the
  model choose only a bounded freight action and reason from the local
  observation plus delivered reports.
- alternative: let the model generate recipients and message bodies in the same
  call.
- consequence: v1 isolates model decision behavior under identical information.
  it does not study free-form communication strategy; that is a separate slice.

### staged three-model panel

- stage one models: `gemma-4-26b-a4b-it`, `glm-53-flash`, and
  `qwen3.5-397b`.
- replacement candidates after the recorded calibration failures:
  `qwen3.8-27b` and `deepseek-v4-flash`. they join a comparison panel only if
  their single accepted calibration calls cross the exact action seam.
- stage one conditions: seed 42 across mesh/ring, mute/control, and
  local-sufficient/peer-required information regimes: 24 episodes.
- stage two: add seeds 7 and 101 only after structural and measurement review,
  producing at most 72 total episodes.
- consequence: the original panel's stage one costs an estimated 2.706 credits
  at the amended 4,000-input/512-output call bounds; all three seeds cost at
  most an estimated 8.118 credits. those rate-derived estimates do not price a
  replacement panel whose rates were not exposed. estimates never override the
  ledger.

### budget and failure behavior

- absolute session ceiling: 10,000,000 microcredits (10.000 credits).
- reserve estimated uncached cost before every request using the frozen model
  rates and token bounds. refuse a call whose reservation could cross the cap.
- settle to reported usage when complete; uncertain failures retain their full
  reservation. no automatic retries. a deliberate rerun gets a new attempt id.
- provider or parse failure remains an observed failed decision; it is never
  silently replaced with a successful call.

## scope

in:
- one model action policy in the existing runner; no second runner.
- bounded structured output, strict parsing, existing world validation, explicit
  rejection, call usage/latency evidence and private raw-response sidecars.
- a staggered freight regime with jobs visible at turns 1, 7, 9 and 11.
- a peer-required regime where successful multi-hop routing can depend on typed
  reports about remote routes.
- calibration, one episode per cell, measurement review and gated expansion.

out:
- free-form model messages, tools, agentic memory, training, adaptation,
  autonomous retry, dataset upload, automatic report prose or morphology labels.
- claiming model superiority, peer-mute causality or statistical significance
  from the exploratory batch.

## call and evidence contract

each active agent-turn supplies only the role, turn, bounded local observation,
admitted typed reports and allowed action shape. the model returns json:

```json
{"action":{"kind":"route_freight","freight_id":"f-001","via":"west->south"},"reason":"short bounded text"}
```

`action` may be null. the object may be returned as raw json or inside exactly
one solitary `json` markdown fence with no surrounding prose. extra keys,
invalid json, other wrappers, identifiers outside the observed freight/candidate
routes, overlong reason text or non-object output are rejected categorically.
the model never receives a world instance or hidden state.

the sealed event log records normalized decisions, categorical failures,
response hash, model, usage, latency and attempt id. raw prompts and responses
live in a private mode-0600 sidecar outside report exports. secrets never enter
events, sidecars, errors or command arguments; the sdk reads `ADAPTION_API_KEY`
from the environment.

## experimental matrix and gates

| gate | work | exit |
|---|---|---|
| offline | mocked responses for valid, null, malformed, illegal, provider-failed and budget-stopped paths | all invariants and legacy suites pass |
| calibration | two retained v0 calls plus exactly one repair call per stage-one model | each model returns parseable bounded output or remains visibly failed; an incomplete repair response stops that model |
| apparatus | one seed-42 episode in each of the 24 model/condition cells | jobs remain after turn 8; identities, seals, usage and measures reconcile |
| interpretation | automated all-run table plus selected human replay | primary/guardrail values are understandable without raw-log archaeology |
| expansion | add seeds 7 and 101 | only if the prior gate is accepted and projected reservation remains below cap |

## measures

| priority | measure | source | decision |
|---|---|---|---|
| primary | verified jobs delivered / released by horizon | job evidence and terminal roster | compare outcomes without treating jobs as independent trials |
| secondary | first verified completion at/after intervention | disturbance and job completion events | whether useful work resumes |
| mechanism | delivered reports available to the model; selected action differs from local-only deterministic reference | model input manifest plus route-gossip counterfactual | whether remote information could matter to the choice |
| guardrail | malformed output, illegal action, provider failure, budget stop | decision and call receipts | distinguish model behavior from infrastructure failure |
| descriptive | sent/delivered/undelivered reports and normalized action counts | event log | locate topology and intervention differences |
| operational | calls, tokens, reserved/estimated credits and latency | private call ledger | decide whether to expand |

## implementation order

1. add staggered release and peer-required scenario fixtures with zero-provider
   proofs that work survives turn 8 and information can change a legal route.
2. add the pure model-output parser and action candidate contract.
3. integrate the provider policy at the existing act seam; retain typed reports.
4. add an atomic private budget/call ledger and terminal budget-stopped behavior.
5. add event/schema/analyzer support without changing legacy bytes or measures.
6. run offline suites and independent review; then perform the calibration gate.
7. preserve every attempted episode, generate the all-run table and stop for
   interpretation before expansion.

## validation

```sh
PYTHONPATH=runtime python3 -m unittest runtime.test_model_policy -v
PYTHONPATH=runtime python3 -m unittest runtime.test_route_gossip runtime.test_gossip_integration -v
python3 runtime/test_runner.py
python3 -m unittest analysis.test_measure_episode -v
node --test viewer/replay.test.cjs viewer/comparison.test.cjs viewer/evidence.test.cjs
```

provider calibration additionally proves model id, output bound, token usage,
latency, response hash, reservation/settlement and secret exclusion. tests use
mocked sdk responses and make zero provider calls.

## change shape

| dimension | changed? | source of truth | proof |
|---|---:|---|---|
| user-visible behavior | no | offline viewer remains unchanged | existing viewer suite |
| persisted state or schema | yes | event schema and private call ledger | schema, restart and mutation tests |
| external or provider-visible behavior | yes | adaption request contract | mocked boundary plus bounded calibration |
| identifiers, secrets or privacy | yes | condition/attempt ids and env-only credential contract | rejection and secret-exclusion tests |
| lifecycle or terminal states | yes | completed/failed/budget-stopped/cancelled | terminal-state tests |
| setup, operation or recovery | yes | exact commands, model/rate snapshot and retained attempts | clean-checkout dry run |
| normative contract or decision | yes | this accepted spec | owner acceptance and independent review |
| cross-repository dependency | no | one repository and adaption service | pinned revision and api receipt |

## risks and unknowns

- provider latency and rate limits are unmeasured for the three-model panel.
- fixed typed reports improve experimental control but do not expose emergent
  language or recipient-selection strategies.
- model outputs are stochastic even with fixed world seeds; three world seeds
  are exploratory scenarios, not statistical power.
- staggered release and peer-required routing must be proven independently of
  the model policy before their outcomes can be interpreted.
- the local beads cli is unavailable to asterion; board tracking must be added
  by a teammate without reinitializing the store.

## done when

- legacy scripted behavior remains byte-compatible and all existing suites pass.
- offline proofs cover every parser, validation, budget and terminal path.
- calibration cannot exceed the accepted cap and exposes actual usage.
- the stage-one matrix preserves all successes and failures and produces a
  reconciled per-episode table.
- expansion is a separate accepted gate after human inspection, not an automatic
  consequence of successful execution.
