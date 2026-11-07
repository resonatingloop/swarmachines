# formal experiment / a pair we can actually explain

status: accepted

owner: colette · runtime handoff: pug · measures/review: caduceus · evidence integration: asterion

## acceptance

colette accepted this protocol on 2026-11-07 in the coding session. the recommended conditions and measure definitions below are accepted; their original proposal wording is retained for review provenance. runtime readiness, caduceus source mapping review, and final observable field mapping remain gates. acceptance authorizes this bounded zero-provider workflow, not runtime repairs or paid runs.

## owner view

- change: turn the working replay/export pipeline into a reproducible, bounded formal experiment handoff.
- before: mesh/hub-spoke scaffold episodes reproduce and export correctly, but this is a plumbing rehearsal, not the ruled experiment.
- after: one pinned reviewed runtime produces the ruled topology pair with traceable world outcomes, a declared policy and an auditable run manifest.
- authority: this accepted protocol fixes conditions and measure definitions subject to the readiness gates. it authorizes no paid runs, provider setup, runtime repairs or unsupported report claims.

## context

formal arms are fixed by the [merged topology ruling](../openspec/changes/add-turn-seam-event-log/topology-ruling.md): fully-connected (`mesh`) versus bidirectional ring, both under peer-mute. hub-spoke/relay-loss remain scaffold conditions. the [weekend plan](001-hackathon-plan.md) proposes job completion, delay, usage and traffic measures; this handoff makes their evidence requirements explicit.

as inspected on 2026-11-07, pr #5 at `c89dd2a54a2aefce4d5ba2665d11a015cd7c44d7` and pr #6 at `46d54a31f45b43ec6c190a5e7badfad29a2d076c` remain open. pr #6's inspected runner still does not integrate freight state; the runtime owner confirmed the issue and linked viewer956 to b9f/i5s repairs. reported unpushed repairs are not a reviewed handoff. export pr #14 has now merged after independent gates cleared.

## scope

in:
- readiness gates, exact condition manifest, small zero-provider pilot, and proposed exploratory scripted batch.
- explicit measure definitions and missing-evidence handling.
- mapping verified artifacts to report sections without writing the owner's prose.

out:
- model-in-the-loop runs, training, provider expenditure, runtime-lane repairs or automatic experiment dispatch.
- causal claims about peer-mute without a no-mute control, statistical significance from three scenarios, or morphology labels inferred from traffic alone.

## owner decisions

### pilot then small batch

- recommendation: first run one scripted pair at seed 42; after readiness passes, use seeds 7, 42 and 101 across both topologies (six unique condition runs). seed 42 pilot may count if the frozen revision/configuration are identical.
- alternative: stop at the single pair and report an instrument demonstration if time is tight.
- consequence: three distinct seeds are exploratory scenario replicates, not three independent repeats of the same deterministic scenario. exact reruns test reproducibility and do not increase sample size.

### topology comparison under a fixed intervention

- recommendation: mute agent c starting at the beginning of turn 8 through turn 16 in both arms; preserve its local observations/actions. four agents a,b,c,d, horizon 16; ring order a–b–c–d–a.
- alternative: a later two-by-two design adds a no-mute arm for each topology.
- consequence: the initial pair compares topologies under the same intervention. it cannot isolate the effect of muting or topology-by-mute interaction. adding controls is a separately accepted expansion.

## readiness gates

1. identify one integrated reviewed commit containing freight wiring and ring/peer-mute, with independent verification/security verdicts and exact rerun commands. branch names or a fixture filename are insufficient.
2. demonstrate observations derived from world state, legal/illegal actions checked against that state, committed actions mutating it, and outcome counts derived from actual jobs. never use randomized summary values as task evidence.
3. inspect whether the declared policy actually consumes received information in its decision path. include a controlled fixture where changed received information can change a legal decision, while world and policy are fixed. this is a capability check, not proof of beneficial coordination. if the policy ignores messages, label the run a transport/world test and do not interpret it as coordination performance.
4. verify directed ring adjacency, identical physical world graph/jobs per seed, mute starting precisely at turn 8, and local actions continuing. permitted links and delivered messages are distinct evidence.
5. validate event envelopes and identities, nondecreasing logical turns for comparison, lifecycle consistency, and required job/outcome evidence. retain failed attempts and errors rather than replacing them with successful reruns silently.
6. inspect the invocation and dependencies for zero-provider operation. require explicit scripted mode and no model credentials/calls. no silent provider fallback.

## frozen run manifest

before the first formal run, record: runtime commit, policy/version, interpreter/dependency versions, schema version, physical-world initialization hash, jobs/release schedule hash, ordered agent roles, seed, topology/adjacency, disturbance timing/semantics, horizon, complete invocation, expected stop condition and provider mode.

topology is the intended changing variable within each seed pair. physical world, job releases, policy, observation rules, action budgets, seeds/streams and disturbance timing stay fixed. do not use delivery_config_sha as a physical-world hash. distinguish absent metadata from a verified equality.

assign a unique manifest condition id to every seed/topology combination even if the runner reuses a seed-based run_id. store each output separately and attach original-byte sha256, exit status, event count, end condition and failure details. never overwrite a prior attempt. record actual execution order; alternate mesh-first and ring-first across seeds.

## proposed measures

these definitions are owner-accepted and await caduceus review against the delivered schema. unavailable evidence yields an unavailable measure, never a guessed value. use direct computations, not a model judge. the compact goal/guardrail/operational split follows [langfuse's evaluation guidance](https://langfuse.com/academy/evaluate/choosing-what-to-evaluate); no langfuse integration is required here.

| priority | status | measure | source / evidence | decision informed | measurability |
|---|---|---|---|---|---|
| primary | proposed | unique jobs delivered by horizon / unique jobs released by horizon | job ids and release/completion transitions, reconciled with final world state | whether task completion differs between topologies | requires traceable job events; zero released jobs yields undefined rate, with numerator/denominator retained |
| secondary | proposed | turns from start-of-turn-8 intervention to first completion at or after it | ordered intervention/completion events with job ids | whether useful work resumes; not stable recovery | completion during turn 8 has delay 0; none by horizon is right-censored, not an invented delay of 8 or 16 |
| descriptive | available event types | per-agent sent/delivered/undelivered record counts before and after intervention | message lifecycle records, recipient/sender references | locate traffic differences for inspection | report exposure windows turns 1–7 and 8–16 separately; raw counts are not directly rate-comparable across unequal windows |
| guardrail | available event types | rejected actions, failed runs and fallbacks | action/reason records and manifest failures | distinguish invalid decisions from implementation failure | retain denominators and reasons; unavailable fallback reporting stays unknown |
| operational | proposed accounting | provider calls, tokens, observed credits and elapsed time | explicit scripted configuration, usage records, local run timing | verify cost/mode and batch feasibility | scripted zero calls must be verified; model usage absent from a future run is unknown, not zero |

report per-run numerators/denominators and paired ring-minus-mesh differences by seed. do not pool job observations as independent trials or fit significance claims to this tiny batch. zero, negative, mixed and inconclusive outcomes are valid. select replay specimens only after retaining the whole batch table.

## evidence pipeline and report boundary

readiness proof → frozen manifest → recorded pair → schema/invariant checks → paired viewer → selected-turn evidence export → author-reviewed tables and prose.

the existing export contains record counts and references, not job outcome calculations. outcomes need a separate reviewed analyzer tied to the delivered job schema; do not relabel the export as that analyzer. include all-run outcomes in the eventual batch table, and use selected turns only as supporting exhibits.

report mapping: methods get the frozen configuration and policy; reproducibility gets commands/hashes/repeat checks; results get verified per-run measurements; limitations get missing controls, scripted policies, small scenario count and any unavailable measures. replace scaffold language such as “a log that cannot lie” or “tamper-evident” with the narrower properties actually verified. source hashes establish byte identity, not truth or tamper-proof production. the report remains colette's authored work.

## change shape

| dimension | changed? | source of truth | proof |
|---|---|---|---|
| user-visible behavior | no | existing viewer/export | no UI implementation in this handoff |
| persisted state or schema | yes | run manifest and future result records | schema/manifest review before implementation |
| external or provider-visible behavior | no | scripted zero-provider gate | invocation and usage inspection |
| identifiers, secrets or privacy | yes | unique condition ids, source hashes | collision checks; no credential export |
| lifecycle or terminal states | yes | pilot/batch readiness and failures | explicit gates and retained attempts |
| setup, operation or recovery | yes | pinned invocation and manifest | isolated rerun proof |
| normative contract or decision | yes | this draft's conditions/measures | owner acceptance and metric review |
| cross-repository dependency | no | one integrated project revision | merged source inspection |

## implementation order

1. receive the corrected reviewed runtime handoff; map proposed measures to its actual events and surface missing job evidence.
2. accept the final conditions/measure mapping, then implement manifest validation and the smallest direct analyzer needed. this draft does not fabricate CLI flags or schema fields before the runtime lands.
3. execute a zero-provider pilot pair and one exact rerun per arm; verify world/record invariants and byte reproducibility under deterministic policy.
4. if the frozen pilot passes, complete the accepted small batch, preserve all attempts, and inspect paired records alongside measured outcomes.
5. hand verified artifacts and limits to the report author; route any code change through standing pr/review procedure.

## done when

- one reviewed integrated runtime and exact invocations satisfy all readiness gates, or explicit transport-only scope is accepted instead.
- the manifest fixes every intended control and records topology as the varying factor.
- job measures trace to actual source transitions/state; absent evidence is clearly unavailable.
- reruns reproduce deterministic artifacts, every condition is preserved, and failed attempts remain visible.
- viewer/export identities match original log bytes; selected-turn exhibits agree with the all-run table without implying omitted turns were measured by the export.
- the report handoff separates verified findings, descriptive differences, limitations and future work.

## risks and unknowns

- corrected freight integration and ring/peer-mute are not yet a merged handoff at the inspected revisions.
- the current delivered schema may lack job release/completion records needed for outcomes and delay; runtime must expose them or those measures remain unavailable.
- message-sensitive decisions may not exist in the scripted policy. traffic differences alone cannot establish coordination benefits.
- exact CLI flags, final event fields and integrated revision remain unresolved until the runtime owner supplies them.

## open questions

- seed set, mute schedule and definitions are owner-accepted; observable source mapping and runtime readiness remain pending.

## review surfaces

[change atlas](formal-handoff-review/index.html) projects this accepted protocol with source fingerprint. no separate companion is added: the central uncertainty is evidence readiness, not a supported append-record trace. the markdown remains canonical; no formal experiment has been run under this protocol.
