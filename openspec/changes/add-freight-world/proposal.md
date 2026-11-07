# add the freight-in-the-fog world

## why

the hackathon brief (specs/001-hackathon-plan.md) names freight-in-the-fog as the working world: a graph with depots, hubs, and routes, four agents with limited local views, and freight delivery as the collective task. this change integrates that world with the existing v4x turn-seam runner so day-1 produces one complete, schema-valid, replayable episode with zero model calls.

the existing runner already implements the turn cycle (observe→exchange→act→record), message lifecycle, communication topologies, and disturbances. this change adds:
- the freight world state machine (graph, depots, routes, closures, freight items)
- scripted 4-agent / 16-turn episode configuration
- event log validated against runtime/schema/events.schema.json
- documented rerun command for byte-identical replay from seed

## what changes

- freight world module (runtime/freight_world.py): graph state, delivery jobs, legal moves, capacity limits, partial observations
- runner integration: world.observe() produces agent-specific visible state; world.apply_action() validates and commits route_freight actions
- scripted episode config: 4 agents (a,b,c,d), 16 turns, seed control, one disturbance (relay-loss) at turn 8
- sample output: runtime/freight-episode.jsonl (schema-valid, replayable)
- tests: freight world behavior tests + existing 12/12 runner tests remain green

## out of scope

- adaption model calls (later slice under spend ceiling)
- topology comparison (fully-connected vs bidirectional ring) — day-2 work
- second disturbance (stale-report) — day-2 work
- learning-loop branch or training

## acceptance

requirements verified against the sample episode; owner accepts before any archival. draft until then.
