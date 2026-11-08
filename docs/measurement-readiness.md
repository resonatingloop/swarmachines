# measurement readiness / freight runner

status: observed source mapping; proposed analyzer boundary awaiting review

this is evidence integration under [accepted spec006](../specs/006-formal-experiment-handoff.md), not a new experimental protocol or authorization to repair the runtime. inspected runtime: `1c3fd5005ac717a339ce7817bc72c16537757e20` (pr #29). findings are pinned to that revision; later heads need rechecking. no formal episodes or paid calls were executed for this assessment.

## consequential finding

readiness gate 3 is not met: the scripted action policy does not consume received messages. `runtime/runner.py:467–593` selects actions using its dedicated random stream and freight-world access, never `self.context` or the supplied `message_lifecycle`. context is populated during exchange, but `message.acted_on` is emitted from `exchange_acted_rng.random() > 0.5` at lines 440–452. that label is not evidence of a message influencing a decision.

therefore current runs can exercise transport and freight-world mechanics. their outcome differences must not be interpreted as coordination performance. this does not contradict the narrower runtime wiring gates reported for pr #29.

## field mapping

| accepted measure | inspected source | usable boundary |
|---|---|---|
| unique jobs delivered / jobs released | `freight_world.py:117–145` creates four jobs; `346–358` counts terminal states; `runner.py:766–784` emits aggregate totals | world-derived count available with pinned freight-mode provenance. release inventory and job identities are not in `world.init`; do not hard-code denominator 4 in a generic log analyzer. require a verified job manifest and completion mapping before reporting the primary rate. |
| intervention to first subsequent job completion | `action.committed` includes `freight_id` and `new_state` from `freight_world.py:333–341`; job mapping is source-defined as `j-{freight_id}` | candidate freight completion evidence exists, but job identity/release mapping must be verified. distinguish deduplicated jobs from repeated records. only assert right-censoring when complete logging through the horizon is established; missing evidence is unavailable. |
| existing `recovery_interval_turns` | `runner.py:783` assigns `num_turns` | horizon placeholder. never use as observed recovery or first-completion delay. |
| per-agent message counts | `message.sent` gives sender/recipient/id; `message.delivered` gives recipient/id/status, including undelivered | count records in turns 1–7 and 8–16 separately, report 7 versus 9 turns of exposure. validate message identity links; no influence claim. |
| rejected actions | `action.validated` gives legality; later `action.rejected` can indicate failed application even after legal validation | join on action identity. distinguish validation rejection from apply-stage rejection; retain reasons and proposed-action denominator. do not equate validated with committed. |
| failed runs and fallbacks | complete/failure manifest and process outcome required | absent `run.end` cannot alone distinguish failed execution from truncated capture. missing fallback telemetry stays unknown. |
| provider usage and elapsed time | invocation/usage/timing manifest, not ordinary message traffic | missing usage is unknown. zero provider calls requires independently verified scripted invocation. |

scripted mode assigns delivery totals zero despite its comment saying the fields are omitted (`runner.py:771–784`). the terminal payload alone cannot distinguish these placeholders from measured zero. the analyzer needs mode/revision provenance, rather than trusting a field name.

## controlled policy fixture

on the pinned runner, two fresh copies of agent a and the freight world were initialized with the same seed. one agent had empty context; the other had a synthetic route-closure report. both executed turns 1–16. this directly exercises `Agent.act`, not a full simulation, formal topology comparison, or schema-validation gate.

| seed | action event records per copy | exact event equality | final delivery-count equality |
|---|---:|---|---|
| 7 | 16 | yes | yes |
| 42 | 19 | yes | yes |
| 101 | 31 | yes | yes |

three examples alone do not prove universal invariance. the stronger finding is the source-level absence of a message input read, supported by this fixture.

reproduce from an isolated checkout of the pinned revision, using a python environment that can import its runtime modules:

```sh
python3 - <<'PY'
import sys
sys.path.insert(0, 'runtime')
from runner import Agent, EventLog
from freight_world import FreightWorld
for seed in (7, 42, 101):
    records, outcomes = [], []
    for context in ([], [{'message_id': 'fixture-report', 'turn': 1,
                         'body': {'route': 'west->south', 'status': 'closed'}}]):
        agent = Agent('a', seed, 0)
        agent.context = context
        world = FreightWorld(seed=seed)
        log = EventLog('fixture', '2026-11-07T14:30:00Z')
        for turn in range(1, 17):
            agent.act(turn, log, freight_world=world)
        records.append(log.events)
        outcomes.append(world.get_delivery_stats())
    assert records[0] == records[1]
    assert outcomes[0] == outcomes[1]
    print(seed, len(records[0]), 'same actions and delivery counts')
PY
```

## next bounded action

caduceus reviews this mapping against the delivered schema. the runtime lane supplies either a message-sensitive policy plus its controlled capability fixture, or the owner explicitly accepts transport/world-only scope. neither choice is inferred from a passing wiring test.

after that gate, the smallest analyzer can expose supported traffic and action counts, provenance-backed delivery totals, and explicit unavailable reasons for unsupported job metrics. implementing job rates or post-intervention delay requires the accepted job mapping and completeness rules first. no morphology labels, significance claims, or silent substitutions are proposed.
