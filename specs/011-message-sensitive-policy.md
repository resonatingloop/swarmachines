# route gossip / a decision that can hear

status: accepted

owner: colette · runtime integration: coordinate with pug · measurement review: caduceus

## owner view

- change: introduce an explicit deterministic freight policy that uses delivered route reports in route selection.
- before: inspected `Agent.act` ignores context; exchange emits stochastic `message.acted_on` markers.
- after: actions depend only on local observations and admissible delivered reports; a controlled fixture proves a report can change a legal first hop.
- authority: owner requested this direction after the readiness finding. colette explicitly accepted these rules and cleared coordination and implementation in the coding session on 2026-11-08. no paid run, formal batch or world redesign is included.

## current ground

source inspection is pinned to pr #29 head `1c3fd5005ac717a339ce7817bc72c16537757e20`; that head has since advanced. implementation must rebase the design on the independently reviewed integrated runtime, not overwrite the active freight/tracing lanes. [spec006](006-formal-experiment-handoff.md) gate 3 requires a message-sensitive capability fixture. pr #31 holds the original evidence mapping.

`FreightWorld.observe` already returns current location, visible freight with destinations, adjacent locations, route statuses and turn. `Agent.observe` currently logs that view without retaining it for the action policy. exchange stores generic status bodies and appends only message identifiers to recipient context. the world validator remains the authority for legality and mutation.

## recommended decisions

1. deterministic policy first, named `route-gossip-v1`, explicitly selected and recorded. preserve the legacy scripted mode for regression use; neither is an llm policy. alternative: a model-driven policy introduces provider and sampling variables and needs a separate protocol.
2. no new world conditions. the positive capability fixture may use a small synthetic world with two legal first hops; label it as a test. the actual three-seed experiment can produce no outcome difference. direct routes in the current world may make peer information redundant.
3. same-turn reports only, no relay or persistent beliefs in v1. this bounds freshness and prevents cached reports masking peer-mute. local observations override conflicting peer claims; conflicting peer reports about an otherwise unobserved edge make that edge unknown. alternatives involving memory and trust are deferred.

## scope and rules

in: retain bounded observations, typed route reports, deterministic selection, decision provenance, a message-sensitivity fixture and regression tests. likely surfaces: runner, a small pure policy module, the event contract/schema, and runtime tests.

out: model agents, training, provider calls, changing physical worlds/jobs/topologies/intervention, report generation, job-metric implementation, autonomous dispatch, historical-log rewriting, and opportunistic freight/tracing repairs.

### observation and exchange

- retain the exact current-turn local view already emitted by observe. the policy receives a copy, never the world object or another agent's context.
- retain the existing send schedule and topology/delivery gates. sending is not delivery. reports contain sender, observed turn, and only directed route/status pairs actually in that sender's local view; no invented remote knowledge or recommendations.
- only successfully delivered current-turn reports enter the policy inbox. mute and topology denial prevent admission. parse a bounded typed structure, not executable text. ignore malformed, stale, future-dated or identity-mismatched reports with categorical reasons.
- no report forwarding. original message identities remain attached to every admitted fact. freeze the inbox after exchange; all agents observe before exchange and all exchange before act.

### selection and execution

- preserve the existing independently seeded action-opportunity schedule; changing traffic must not consume its random stream.
- choose the lexicographically first visible freight id. no visible freight means a logged no-op, not an invalid synthetic freight action.
- build a directed graph from local and admitted reported routes. only edges explicitly known open are traversable; unknown and closed are excluded. local facts take precedence; peer conflicts are unknown.
- compute the shortest known path to that item's destination, tie-breaking by the lexicographic complete location sequence. require the first hop to be locally observed as open. if no known path exists, wait with reason `no_known_path`; do not query hidden world state or invent an exploratory hop.
- propose the first hop with freight id from the local observation. existing world validation/application can reject stale observations or capacity conflicts; record those outcomes without changing the decision retrospectively.
- the selected graph path is a belief-supported proposal, not a guarantee of reachability or optimality in the true world.

### provenance and sensitivity

- record policy name/version in run configuration and a bounded decision record referencing observation, consumed message ids, proposed path or wait reason, and action identity when present. final field names and schema changes are reviewed before implementation lands; preserve legacy log acceptance.
- compute a pure local-only counterfactual with the same observation and opportunity, but no peer reports. record whether the proposed first hop or wait choice differs. this is a policy-input sensitivity diagnostic, not causal evidence of improved episode outcomes.
- do not emit random `message.acted_on` markers in this new mode. record reports used by the graph separately from decision sensitivity; consulting a report does not establish individual causal responsibility. do not assign a collective change to one message when several jointly support the path.

## change shape

| dimension | changed? | source of truth | proof |
|---|---|---|---|
| user-visible behavior | yes | explicit policy option and replayable decision records | cli and replay regression |
| persisted state or schema | yes | reviewed policy/decision event contract | old and new fixture validation |
| external or provider-visible behavior | no | scripted zero-provider path | no SDK invocation fixture |
| identifiers, secrets or privacy | yes | observation/message/action references, bounded local reports | foreign-id and hidden-state tests; no credentials |
| lifecycle or terminal states | yes | wait/proposal/rejection paths | no-path and apply-failure tests |
| setup, operation or recovery | yes | explicit policy selection | reproducible invocation |
| normative contract or decision | yes | this accepted spec plus spec006 | owner acceptance and source mapping review |
| cross-repository dependency | no | runtime in this repository | isolated integration proof |

## implementation order

1. accept these semantics and agree a single runtime writer with pug; take the reviewed integrated head. do not fork a second runner.
2. specify the bounded report and decision event fields; implement the pure selector and its fixtures before wiring exchange.
3. retain local observations and deliver typed reports through the existing transport rules; wire explicit policy selection and preserve legacy behavior.
4. test capability, noninterference and event provenance; run runtime and schema regressions against the integrated result.
5. hand exact head and evidence to caduceus for independent review. return to spec006 readiness and measurement mapping; do not launch a formal batch automatically.

## observable acceptance criteria

- positive fixture: fixed world, local view, agent state, action opportunity and rng; both alternative first hops legal. vary only an admissible remote route report, causing a different first hop or wait-to-legal-action transition. record and assert the exact input/output difference.
- negative controls: an irrelevant report does not alter the decision; an undelivered, muted, stale, malformed or foreign report cannot influence it. local authoritative route status wins; peer disagreement yields unknown.
- topology and mute tests prove differences in admitted information without changing physical state or action-opportunity randomness. muted agents retain local observe/action behavior.
- equal inputs reproduce equal decisions; complete reruns reproduce under fixed configuration. no calls to world getters from the pure policy; no provider calls.
- no-op, no-path, delivery at destination, validation rejection and application failure have explicit tested outcomes. every emitted decision/message/action reference resolves; no stochastic influence marker appears in this policy mode.
- old scripted tests and old episode validation remain green. do not label fixture success as beneficial coordination or formal experiment success.

## validation and limits

run the repository-owned runtime suite, new pure policy and integration tests, ruff, schema checks and exact reruns using the actual commands documented on the integrated base. the implementation pr must state exact commands and results rather than assume unavailable test names now.

unknowns: the integrated base and teammate ownership are moving; final event field mapping is not yet reviewed. path tie-breaking and strict unknown-edge treatment can cause waiting; this is a declared policy choice, not automatically a bug. this slice addresses input dependence only, not ecological validity, policy quality or statistical power.
