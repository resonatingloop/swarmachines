# job evidence / count what happened

status: accepted

owner: colette · implementation: asterion · measure mapping review: caduceus

## owner view

- change: make the accepted completion and post-intervention measures computable from an episode with explicit job evidence.
- before: initial jobs exist only in runtime state; completion records identify freight rather than an explicit released-job roster; the recovery field is a horizon placeholder.
- after: a bounded offline analyzer reconciles a released-job roster, completion transitions and final job states, returning values with exact supporting sequence ids or explicit unavailable reasons.
- authority: colette accepted this slice and cleared implementation in the coding session on 2026-11-08. caduceus's field-mapping review and the settled runtime base remain implementation gates. no formal experiment or paid call is authorized.

## current ground and dependencies

master inspected: `3a95bb0`. [measurement mapping](../docs/measurement-readiness.md) is merged. message-sensitive policy pr #33 is under independent review; tracing and e2e work belong to pug's lanes. implementation starts from the reviewed integrated policy head, with one runner writer agreed. do not patch those branches concurrently or create another runner.

[spec006](006-formal-experiment-handoff.md) already accepts unique delivered/released jobs and intervention-to-first-completion delay. this spec supplies their evidence contract, not new outcomes. the current world initializes all jobs before turn 1 and has no delayed-release scheduler; preserve that world.

## recommended decisions

1. instrument the explicit route-gossip freight mode only. legacy episodes remain loadable but lack this evidence version; their unsupported measures are unavailable, not guessed from filenames or a hard-coded four-job denominator.
2. use deterministic local calculation, no llm judge and no provider. report the first completion after intervention as resumption delay, never stable recovery.
3. distinguish `available`, `undefined`, `right_censored`, `unavailable`, and `invalid`. malformed or contradictory evidence fails validation; valid old/incomplete evidence is unavailable. a genuinely empty release roster has an undefined completion rate, not zero percent.

## evidence contract

add `job_evidence_version: 1` and `horizon_turns` to the new policy's run configuration. retain original run/agent/message identities. these global audit records never enter agent observations or policy inboxes.

- one `jobs.initialized` event at turn 0 before any agent action contains the actual sorted roster: `job_id`, `freight_id`, `origin`, `destination`, `release_turn: 0`, initial state `pending`. ids are unique and the current one-job-per-freight mapping is explicit. an empty roster is permitted. do not invent future releases or alter jobs.
- one `job.completed` event after a successful `action.committed`, only on a real transition to delivered: `job_id`, `freight_id`, `action_id`. turn comes from the event envelope. look up the actual world job rather than manufacture its id from a naming convention. no completion event on failed validation/application.
- `run.end` carries an actual sorted terminal roster of `job_id`, `freight_id`, `state` and explicit successful termination/horizon. allowed states remain pending, in-transit, delivered, stuck. the obsolete `recovery_interval_turns` is not consumed by the analyzer; do not reinterpret it.
- no simulated summary replacement, state mutation for logging, or network lookup. old schema records remain accepted; new versioned records receive typed bounded schemas. failures before run.end remain incomplete evidence.

## analyzer behavior

new offline entry point: `python3 -m analysis.measure_episode EPISODE --output NEW_JSON`. implementation must document actual invocation and package layout. output creation refuses an existing path. read bounded UTF-8 input with the existing episode limits; validate the complete file, never silently drop invalid lines. no eval, provider, runtime import or resimulation.

preserve original-byte sha256, run id, evidence version, policy, topology, seed, horizon, schema/analysis version and supporting sequence ids. a hash establishes byte identity, not producer truth. an external frozen runtime manifest is still required for formal runs.

validation requires unique increasing sequence ids, one run, nondecreasing turns, one config, initialized roster before actions, and one terminal roster at the declared horizon for complete version-1 evidence. no events after terminal. verify job/freight/action identity joins, successful commit before completion, no duplicate completion, no unknown or unreleased jobs, and exact initial/final roster identity agreement. every terminal delivered job must have exactly one completion; no completed job may end non-delivered. reject contradictory state or terminal metadata.

### primary measure

numerator: unique roster jobs with verified completion by horizon, reconciled against final delivered states. denominator: unique roster jobs released by horizon. emit both integers, ratio or null, status and supporting sequences. denominator zero yields `undefined` with 0/0 retained. missing roster or terminal evidence yields `unavailable`; do not infer denominator from observed completions.

### post-intervention resumption

for the accepted protocol, require exactly one observed peer-mute of agent c at start of turn 8, matching configuration and occurring before turn-8 actions/completions. take the first verified completion at turn >= 8. delay = completion turn - 8; turn-8 completion means zero. preserve all jobs completing at that first turn as witnesses.

with complete consistent evidence and no completion by horizon, emit `right_censored`, delay null, observed-through turn and follow-up duration. missing/truncated records yield `unavailable`, not censoring. absent/wrong/ambiguous intervention yields `unavailable` for this measure while independently supported completion counts can remain available. a pre-intervention completion is excluded from resumption delay.

### descriptive counts and guardrails

retain per-agent sent/delivered/undelivered record counts for turns 1–7 and 8–16 with explicit exposure 7 and 9 turns when that horizon is present. validate message identity links. record proposed/validated/rejected/committed action counts and reasons, separating validation rejection from apply-stage rejection. unsupported provider usage, fallback and failure accounting stay unavailable; absence is not zero.

out of scope: paired significance tests, pooled-job independence, morphology classification, report prose, batch dispatch, model training, changes to policy/physical world, and tracing repair. paired ring-minus-mesh reporting follows once per-run measurement evidence passes review.

## change shape

| dimension | changed? | source of truth | proof |
|---|---|---|---|
| user-visible behavior | yes | explicit offline JSON analysis | golden outcome fixtures and CLI checks |
| persisted state or schema | yes | versioned job events and results | old/new schema and identity validation |
| external or provider-visible behavior | no | offline pipeline | network/provider tripwire |
| identifiers, secrets or privacy | yes | job/freight/action joins and source hash | unknown-id refusals; no credentials or chat input |
| lifecycle or terminal states | yes | completion, terminal and incomplete evidence | failure/truncation/censoring tests |
| setup, operation or recovery | yes | bounded CLI with exclusive output | wrong input and existing-output refusals |
| normative contract or decision | yes | spec006 definitions plus this mapping | owner acceptance and caduceus review |
| cross-repository dependency | no | existing runtime and analysis package | isolated checkout proof |

## implementation order and acceptance

1. accept this mapping, obtain caduceus's source/field review, and settle the runner integration base.
2. write fictional evidence fixtures covering completion at turns 7/8/16, none, zero jobs, duplicate or unknown completion, failed action, roster mismatch, invalid line, partial log and wrong intervention.
3. add read-only state snapshots/transition logging to the new policy mode. demonstrate identical action/world trajectories before and after instrumentation after removing the new audit records/metadata; preserve legacy byte output.
4. implement analyzer and CLI. every reported value traces to validated input; missing evidence is explicit. no hidden world reconstruction or provider calls.
5. run runtime/schema/analysis/replay regression and one local integration fixture plus exact rerun. independently review the final head before merging. a formal pair remains a separate spec006 readiness decision.

## validation and open limits

expected checks: targeted analyzer unit/CLI tests, runtime suite, new policy suite, schema validation, scoped ruff, viewer parser regression and deterministic instrumentation comparison. record exact runnable commands when implemented; no claim that prospective commands already pass.

the current runtime may offer little need for peer information even after policy sensitivity is established. metrics do not cure that ecological limitation. this does not add new job arrivals, a no-mute control, or more seeds. exact event production can prove consistency of a controlled instrument, not truth of arbitrary externally authored logs.
