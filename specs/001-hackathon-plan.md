# swarmachines / a provisional two-day build plan

status: draft

> continuity role: proposed transition
> owner: repository owner, with the hackathon team choosing assignments
> created: 2026-11-06
> supersedes: none
> format: written plan with a [visual review companion](../plans/spec-review/index.html)

this is a route through the weekend, using the freight-world idea as a working
default. none of the build steps below has been carried out. the choices are
provisional; this document does not accept itself or authorize provider spend.

## owner view

- **change:** build a small world in which we can watch an agent collective
  coordinate, lose a familiar arrangement, and possibly recover.
- **before:** a visual proposal and documentation, at planning baseline commit
  `2158ea9`. there is no experimental runtime.
- **after:** a runner, real recorded episodes, an inspectable replay, and a
  small comparison of communication arrangements under disruption.
- **day-one checkpoint:** one complete recorded episode plays in the viewer.
- **day-two checkpoint:** comparable runs and an explanation supported by
  their events, including a boring or inconclusive result.
- **authority:** this markdown owns the proposed sequence. the
  [visual proposal](../plans/index.html) introduces the idea;
  [the brief](../PROJECT_BRIEF.md) owns intent. acceptance remains with the owner.

## working defaults to review

these defaults make the steps concrete. change them before implementation if
the team prefers another shape.

| choice | recommendation | alternative and consequence |
|---|---|---|
| world | freight in the fog: graph, delivery jobs, limited local observations | a different resource-routing world needs new rules and examples |
| people | one owner per lane, with pairing across interfaces | combine roles by interest, but name one integration owner |
| runtime | python for world, runner, and analysis; plain browser javascript for replay | a shared typescript stack reduces language boundaries if the team prefers it |
| communication | fully connected and bidirectional ring; equal per-agent message allowances | a forced star is possible, but losing its hub may structurally disconnect peers rather than reveal a learned coordination failure |
| first disruption | temporarily mute one fixed agent's communication while local actions continue | stale information is the second case; it tests information handling rather than availability |
| episode | four agents, sixteen turns, one decision call per agent per turn | adjust after the pilot if cost or the timing of useful behavior warrants it |
| evidence | local event log and state snapshots, plus langfuse for execution traces | a storage service adds setup and is unnecessary for the first weekend |
| extension | finish the core comparison before model training | prioritize an adapted-agent comparison only after cost, training time, serving, and a baseline are demonstrated |

the actual model, exact dependency versions, lane owners, and spend ceiling
remain decisions. choose and record validated versions during setup, before
building their integrations. this draft is not a dependency lockfile.

## the step-by-step

these are suggested working blocks, not a continuous forty-eight-hour shift.
keep an integration checkpoint at the end of each day.

### 1. choose the first specimen together

**when:** day one, opening thirty to forty-five minutes. **who:** everyone.

review the defaults. choose the world, first disturbance, and four human lane
owners. name an integration owner; the nervous-system owner is a reasonable
default, but integration is an additional responsibility, not a fifth lane.

agree on the demo's minimum: a world doing useful work, a disruption, and
the actual ensuing behavior. record the decisions and accept a bounded initial
slice before runtime implementation. the second disturbance and training
branch can remain provisional.

**leave with:** owners, an accepted initial slice, and a one-sentence demo.
prepare individual agent context handoffs from these choices using
[the agent guide](../AGENTS.md). the handoffs should tell each agent its scope,
checkout, shared interfaces, evidence to produce, and first concrete task.

### 2. establish the workroom and a small provider budget

**when:** day one, first hour; overlap with step 3. **who:** integration owner,
with each human handling their harness/account setup.

confirm checkouts, branches, and how peers obtain the revision behind a
handoff. use separate working copies or worktrees for parallel writers. fill
the discord room card from the distributed harness guides, discover actual
tools, and prove a peer round trip in the approved room. check at milestones
and interface changes; ordinary read/send tools do not wake idle agents.

establish which adaption accounts hold which credits, usable models and
operations, and who owns the run budget. the reported $500 / 1,500 credits
does not establish pooled funds or a price per call. within the agreed scope,
make one small request and record model id, latency, tokens, and any observed
credit charge. choose the langfuse destination and the fictional experiment
data it may receive.

the existing `.env` remains outside agent read access. use the owner's
approved credential setup; keys do not belong in handoffs, logs, or chat.

**leave with:** a provider probe or explicit access blocker, a bounded pilot
allowance, and a real discord connection result. the other lanes can keep
working against scripted agents and sample events while access is resolved.

### 3. agree on one turn and one event

**when:** day one, first shared design block. **who:** worldbuilder and nervous
system, with the observatory and naturalist checking the example.

write one complete example: world snapshot, differing local observations,
agent response, checked action, and resulting events. the proposed turn order:

1. apply scheduled world changes and deliver messages due this turn.
2. construct local views and record the exact context supplied to each agent.
3. ask each agent once for a structured action and bounded outgoing messages.
4. validate responses and resolve competing actions by a documented,
   reproducible rule against the same turn snapshot.
5. commit world changes, queue new messages for the next turn, save the
   resulting state, and continue until the horizon or a stop condition.

agents receive only their permitted views, delivered messages, and their own
retained context. global state belongs to the simulator/viewer. newly sent
messages cannot benefit agents called later in the same turn.

candidate record fields: schema version, run id, scenario seed, condition,
turn, event sequence, agent id where relevant, event type, and payload.
messages also need stable ids, sender/recipient ids, source-observation turn,
send turn, and delivery turn. attach trace references when available. retained
agent notes are context/output, not proof of hidden reasoning.

**leave with:** a sample episode, an agreed format version, and an owner for
interface changes. these are proposed fields, not an existing contract.

### 4. build the first pieces in parallel

**when:** day one, main work block. **who:** all four owners.

| lane | first implementation | evidence before handoff |
|---|---|---|
| worldbuilder | graph, delivery jobs, legal moves, capacity limits, partial observations, scripted policy | a complete scripted episode; illegal moves change nothing; supplies are not duplicated or lost |
| nervous system | turn runner, private context, message routing, adaption adapter, episode recorder | a model response becomes a checked action or explicit rejection; only allowed recipients receive messages |
| observatory | sample-log reader, world view, communication overlay, turn controls, event inspection | the same turn shows the same saved state; sample data is labeled; events retain their source |
| field naturalist | baseline, disturbances, run manifest, small event-derived analysis | a comparison table and an explanation of what its measurements can establish |

the worldbuilder's first success is ordinary graph/state-machine work. pair
with the nervous-system owner to replace one scripted policy with a model.
keep the scripted version as a useful baseline. this gives the teammate new
to agents substantial ownership and a concrete way into the agent loop.

**leave with:** four pieces that agree on the example from step 3. share
artifacts and revisions, not just “my part works.”

### 5. join the pieces while the system is small

**when:** day one, before the final work block. **who:** integration owner,
with every lane available to fix its boundary.

connect one agent to the world, then all four under one arrangement. load the
real episode in the viewer. follow a selected turn from local observation
through model response and validation to world change and replay state.

nest model/tool observations under agent turns in langfuse, grouped with an
episode/run reference. record identity, timing, errors, and usage; missing
usage remains unknown. the event log owns world replay. langfuse's graph
describes execution structure, not automatically communication or influence.
see its [data model](https://langfuse.com/docs/observability/data-model).

record invalid output and a deterministic fallback, such as no action. bound
and count retries. a telemetry failure must not duplicate a committed action.
finish runs as completed, failed, budget-stopped, or cancelled, with a reason.
a missing terminal record means the log is incomplete. for this weekend,
start a new linked run after interruption rather than transparently resuming
provider calls.

**leave with:** one real, inspectable episode that replays without another
model call. identify any remaining tracing gap explicitly.

### 6. freeze a day-one specimen

**when:** day one, final thirty to forty-five minutes. **who:** everyone.

save a known-working run, configuration, prompt/model versions, and matching
code revision. document launch, run, inspect, and replay. have another teammate
follow the path from their checkout. update the checkpoint and leave a next
action per lane.

if the complete loop still fails, narrow to one arrangement and one disturbance.
defer rich classification and training until the loop works.

**leave with:** a recoverable working specimen and a credible day-two scope.

### 7. introduce a disturbance and its matched control

**when:** day two, first block. **who:** worldbuilder and naturalist, supported
by the nervous-system owner.

keep the scenario, jobs, model/prompt configuration, horizon, and message
allowance comparable. first contrast undisturbed communication with a fixed
agent muted for a specified interval. its local routing actions continue:
the intervention changes communication without also removing delivery capacity.

choose the target and timing before viewing outcomes. log the intervention
and permitted graph. check which peers remain reachable; disconnection and a
failure to use remaining routes are different findings.
call it relay loss only when pre-disruption behavior supports that description;
the fixed target may never have become a coordinator.

**leave with:** two runs whose meaningful difference is explicit in their
manifests, plus a disruption marker in the viewer.

### 8. expand to the second arrangement and stale information

**when:** day two, after the first comparison works. **who:** nervous system
and naturalist, with the worldbuilder handling scenario changes.

compare a fully connected graph with a bidirectional ring while keeping the
physical freight map separate. centralization may emerge within either;
do not call an imposed topology a discovered morphology.

for stale information, delay a report that was true when sent until after a
world change. preserve its source and original observation turn. the control
gets timely reports under the same world-change schedule. if a fixture supplies
the report, record scenario authorship instead of calling it model-generated.

use the same small seed set across conditions and vary execution order. seeded
worlds support comparable inputs; they do not make model outputs deterministic.
three repeats per condition are an exploratory starting point, not a statistical
guarantee.

**leave with:** a small comparable batch, or an explicitly narrower comparison
if cost or time requires it.

### 9. use more of adaption where it serves the experiment

**when:** alongside day two, once the complete loop is stable. **who:** naturalist,
pairing with the nervous-system owner.

use adaption inference for the agents. a second useful contribution is generating
candidate scenarios or coordination examples: inspect a small sample, validate
it against the world, and expand useful material. generated trajectories are
examples, not observed experimental evidence.

dataset generation/adaptation offer estimates. the documented autoscientist
mcp tool has no estimate mode; a hyperparameter recommendation is not a quote.
see [adaption's operation reference](https://docs.adaptionlabs.ai/tools/mcp/).

if training fits, isolate one skill, such as communicating a route update with
provenance. separate held-out scenarios before selecting training examples.
compare base and adapted agents under the same topology and budgets, and prove
the trained artifact can be served in time. this is an optional branch, not a
dependency of the main demo.

**leave with:** a useful data artifact or bounded adaptation comparison, if
feasible. report the sponsor capabilities actually exercised.

### 10. inspect before naming the collective

**when:** day two, comparison block. **who:** naturalist and observatory, with
the team reviewing selected episodes.

review these proposed measures before implementing them. start with event
counts and human interpretation, without requiring a model judge. the small,
goal-linked measurement approach is supported by
[langfuse's evaluation guide](https://langfuse.com/academy/evaluate/choosing-what-to-evaluate).

| priority | status | candidate measure | source | decision informed | measurability |
|---|---|---|---|---|---|
| core | proposed | deliveries completed / jobs released by the horizon | world events | whether coordination helps the task | direct counts; retain unmet jobs |
| core | proposed | calls, tokens, observed credits per episode | runner/provider usage | affordable and comparable repeats | calls direct; missing usage stays unknown |
| core | proposed | turns from intervention to next completed delivery | world timeline | whether useful work resumes promptly | record no delivery before horizon explicitly; this is not stable recovery |
| supporting | proposed | per-agent sent/delivered traffic and concentration | message events | where coordination may concentrate | descriptive; include reachability and allowances |
| supporting | proposed | invalid actions, failed requests, fallbacks | validation/lifecycle events | distinguish behavioral and implementation failures | direct counts with reasons |

for a quiet-specialist candidate, inspect local evidence, delivery, decision
context, and subsequent action. for repair, inspect changed exchanges alongside
resumed useful work. allow mixed, unclear, and no-pattern outcomes. keep the
whole small batch visible when selecting replay specimens.

**leave with:** evidence-linked observations and their limitations. a compelling
nickname is the beginning of an interpretation.

### 11. finish around one honest reveal

**when:** day two, final sixty to ninety minutes. **who:** observatory and
integration owner, with the naturalist preparing the explanation.

show the task and limited views. pause before the disruption, advance the
replay, and inspect events behind changed behavior. compare the control or
other arrangement. distinguish allowed links, exchanges, and inferred influence.

keep a recorded episode available when live inference is slow. label the
recording, replay it without provider spend, and finish with one observation,
one limitation, and the next experiment it suggests.

**leave with:** a demo backed by inspectable events.

### 12. leave a usable handoff

**when:** after the demo build stabilizes. **who:** all lane owners.

run the agreed checks, reconcile actual setup and implementation docs, and
replace the checkpoint. preserve manifests and findings with provenance;
record omissions and unverified claims. hand over one exact revision and next
action per remaining task. commits, pushes, posts, or publication follow the
team's established scope; this written plan performs none of those actions.

## workload and scope cuts

the visual calculator's default is four agents × sixteen turns × two
arrangements × two disturbances × three repeats: **768 calls in 12 runs**.
this plan adds an undisturbed-communication control for each arrangement:

| comparison size | runs | agent calls before retries |
|---|---:|---:|
| one arrangement, control plus one disturbance, one repeat | 2 | 128 |
| two arrangements, control plus one disturbance, three repeats | 12 | 768 |
| two arrangements, control plus two disturbances, three repeats | 18 | 1,152 |

all four agents receive one decision call per turn, including while muted.
these counts exclude probes, retries, data generation, training, and extra
evaluators. the html still describes its original four conditions; it has
not been changed by this plan.

measure cost and elapsed time on the pilot before choosing a batch. agree
episode/call/token ceilings and a separate data/training allowance. if credit
usage is unavailable, call counts are not a guaranteed currency cap; use
available account controls and small batches rather than inventing a conversion.

cut training first, then the second disturbance, then rich visual classification.
preserve the local record, complete replay, and a matched comparison. if provider
access never works, show a scripted prototype honestly; the model-backed
experiment remains incomplete.

## scope and governing documents

**proposed core:** one world, bounded agent decisions, controlled communication,
an undisturbed control, at least one disturbance, real episode records, replay,
and event-derived comparisons.

**outside the core:** production hosting, open-ended autonomous agents,
a multi-world benchmark suite, a definitive automatic taxonomy, and a
dependency on finishing model training.

likely new components are the simulator, runner/provider adapter, event schema,
recorder, fixtures, analysis, tests, and replay ui. choose paths and dependency
pins in steps 1–3. give the runtime its own entry point; retain the proposal at
`plans/index.html`. choose a local storage/ignore policy before generating runs.

[AGENTS.md](../AGENTS.md) governs collaboration;
[PROJECT_BRIEF.md](../PROJECT_BRIEF.md) owns intent;
[development](../docs/DEVELOPMENT.md) describes the existing proposal.
there are no accepted runtime contracts. extract durable contracts when the
turn/event decisions actually exist; do not infer them from this draft alone.

## change shape of the proposed implementation

this describes the future build, not the documentation edits made today.

| dimension | changed? | proposed source of truth | proof to establish |
|---|---|---|---|
| user-visible behavior | yes | real replay ui | inspect a saved episode and its source events |
| persisted state or schema | yes | agreed events, manifests, snapshots | validate complete logs; detect incomplete/incompatible input |
| external or provider-visible behavior | yes | provider adapter and trace configuration | real inference response and a retrieved useful trace |
| identifiers, secrets or privacy | yes | run/agent/message ids and approved provider data boundary | match representations; inspect fictional outbound data and credential exclusion |
| lifecycle or terminal states | yes | runner's stop/error rules | invalid output, failed call, interruption, and budget stop without duplicate actions |
| setup, operation or recovery | yes | actual dependency pins and development instructions | another teammate completes run-to-replay |
| normative contract or decision | yes | owner-accepted turn/event rules | consumer agreement on an example and semantic checks |
| cross-repository dependency | no | one project checkout; harness guides are external setup references | no imports from another private repository |

## done when, and how to prove it

the core is done when a fresh checkout can run a real model-backed episode,
save it, replay it without more model calls, and explain a matched comparison
from its events. integration and research limits remain visible in the demo
and checkpoint.

after choosing the runtime, add a documented offline validation command for
world invariants, information boundaries, scheduling, action validation,
event/replay agreement, and terminal states. under the python default, a
proposed command is `python3 -m unittest discover -s tests -v`; tests do not
exist yet, and a zero-test result is not proof.

add a separately invoked live-provider smoke command when the adapter exists,
with a small call limit and a run/trace reference. do not hide paid calls inside
offline tests. record actual run/replay commands in development docs once
they work rather than inventing commands here.

the documentation check already runs from the repository root:

```sh
python3 /home/resonatingloop/.resonance/exoresonance/repository-continuity/skills/manage-project-docs/scripts/check_docset.py .
```

six lowercase checkpoint-heading warnings are known. this check proves
document structure, not future implementation criteria.

## unresolved decisions and risks

- choose the world, owners, runtime, arrangements, disruption semantics, and
  first accepted slice. the defaults above make these decisions reviewable.
- verify account coverage, models, exact sdk versions/compatibility, trace
  destination, spend limits, and provider latency during setup.
- simplistic routing may need little communication. pilot the information
  asymmetry and scripted baseline before paying for a large batch.
- context leakage, unequal allowances, call ordering, reachability, and
  provider errors can masquerade as collective behavior. record them.
- two days may yield a useful instrument and a few observations. three repeats
  do not justify a general causal or statistical claim.

review the defaults with the team, revise this draft, and accept the exact
bounded slice before implementation. the later route can remain provisional
as the first real traces teach us what is worth pursuing.
