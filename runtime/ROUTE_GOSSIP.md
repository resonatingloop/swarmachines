# route gossip / explicit scripted policy

status: implemented; independent review pending

[accepted spec011](../specs/011-message-sensitive-policy.md) introduces
`--policy route-gossip-v1` with `--world freight`. omission keeps the legacy
policy. no model provider, credentials, training or paid calls are involved.

## run a local integration example

from the repository root, use a new output path:

```sh
python3 runtime/runner.py --world freight --policy route-gossip-v1 \
  --seed 42 --turns 16 --topology bidirectional-ring \
  --disturbance peer-mute:8:c --output /tmp/route-gossip-example.jsonl
python3 runtime/verify_events.py /tmp/route-gossip-example.jsonl
```

the runner's existing output option overwrites its target. choose an unused
path; do not overwrite prior experimental attempts. this invocation is an
integration example, not an accepted formal experiment or a claim of useful
coordination. open the file in the existing replay/paired viewer.

## decision boundary

all agents retain their own observation before any exchange. reports contain
only observed outgoing route/status pairs, sender and observed turn. successful
transport delivery is required before admission; the inbox is cleared on the
next observation. no relay or belief persistence is used. admissible reports
can still be wrong: delivery and shape checking do not establish truth.

selection uses a copy of the local view and frozen admitted reports, never a
world object. local route facts override peers. disagreement among peers makes
a nonlocal edge unknown. the selector finds the shortest known-open path for
the lowest freight id, using lexicographic whole-path ties; the first hop must
be locally known open. no known path means wait. the existing action-opportunity
rng is separate from exchange, so traffic does not change opportunity draws.
world validation/application remains authoritative after the proposal.

limits: 32 route facts/report, 32 reports/inbox, 32 visible freight items,
32 unique agents, and 40-character alphanumeric/hyphen agent identities in
this mode. malformed or mistimed reports produce categorical refusals; limits
are explicit rather than silently truncating evidence. observations are internal
runtime data; invalid local observations stop execution instead of inventing a
fallback policy. no-op decisions do not create invalid synthetic freight actions.

## event contract

legacy events remain valid. `run.config` adds `policy: route-gossip-v1` and
`world: freight` only in the new mode. two additive types have strict payload
schemas in `schema/events.schema.json`:

- `policy.report`: recipient is envelope `agent_id`; payload contains
  `message_id`, `sender`, `admitted`, categorical nullable `reason`, nullable
  `observed_turn`, and admitted `routes`. refused bodies are not copied into the
  event. the transport's delivered message precedes this record.
- `policy.decision`: `policy`, `decision_id`, `observation_seq`, nullable
  `action_id`, `opportunity`, nullable `freight_id`, proposed `path`, nullable
  `next_hop`, `reason`, `consumed_message_ids`, nullable `local_only_next_hop`,
  and `choice_changed`. observation references use the episode's sequence;
  action ids exist only when an action is proposed.

`consumed_message_ids` identifies reports supplying nonlocal facts considered
in the graph, including irrelevant/conflicting facts. it does not assign
individual causal responsibility. `choice_changed` compares the actual first
hop with a pure local-only counterfactual under the same observation and action
opportunity. it measures input sensitivity, not benefit or episode-level causal
effect. without an action opportunity both choices are null and the diagnostic
is false. the new mode never emits random `message.acted_on` markers.

replay retains these records and offers their exact payloads through the existing
record detail view; it does not draw new influence edges. `verify_events.py`
recognizes that waiting, no traffic and no rejection can be valid, refuses
legacy influence markers in a policy episode, and refuses partially loaded
policy files. it remains a structural check, not the formal readiness gate.

## proof and limits

```sh
PYTHONPATH=runtime python3 -m unittest runtime/test_route_gossip.py runtime/test_gossip_integration.py -v
python3 runtime/test_runner.py
node --test viewer/replay.test.cjs viewer/comparison.test.cjs viewer/evidence.test.cjs
```

requires the existing jsonschema test dependency. 18 focused tests cover legal
first-hop sensitivity, world application, local precedence/conflict handling,
malformed and stale reports, inbox reset, mute/topology admission, opportunity
invariance, explicit waits, rejection, provenance, schema and deterministic
reruns. the positive capability fixture uses synthetic alternative reports
with fixed physical world state; both selected first hops pass the real world
validator. it is not an observed formal episode. the legacy runtime suite
passes 24/24, and 82 viewer tests pass.

legacy scripted and freight episodes at seed 42/horizon 16 were independently
compared byte-for-byte with merged runtime base `7103ac0` and match. an explicit
new-policy ring/mute integration produced 381 schema-valid records, including
64 decisions and 37 admitted reports; replay parses all 381. none of these
counts establishes performance improvement. direct routes in the unchanged
world may make peer information redundant. spec006's remaining job evidence,
metric mapping and formal-run gates still apply.

job audit instrumentation is documented in [offline measures](../analysis/README.md). the 381-record integration count above is the pre-instrumentation snapshot; current runs add roster/completion records without changing decisions.
