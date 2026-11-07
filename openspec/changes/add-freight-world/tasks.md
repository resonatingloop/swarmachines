# tasks — add-freight-world

- [ ] 1. write freight world spec delta (specs/freight-world/spec.md) with ADDED Requirements section, SHALL statements, and WHEN/THEN scenarios
- [ ] 2. implement runtime/freight_world.py: graph state, depots, routes, closures, freight items, delivery jobs, legal moves, partial observations
- [ ] 3. integrate freight world with runner: world.observe() for agent-specific views, world.apply_action() for route_freight validation
- [ ] 4. configure scripted episode: 4 agents (a,b,c,d), 16 turns, seed 42, relay-loss@turn 8 on agent c
- [ ] 5. produce runtime/freight-episode.jsonl (schema-valid, ~200 events for 16 turns × 4 agents)
- [ ] 6. add documented rerun command (README or Makefile entry) for byte-identical replay from seed
- [ ] 7. write freight world tests (runtime/test_freight_world.py): legal moves, capacity limits, observation boundaries, action validation
- [ ] 8. verify existing 12/12 runner tests remain green
- [ ] 9. determinism check: two same-seed runs produce byte-identical freight episode logs
- [ ] 10. update STATUS.md checkpoint with branch/PR/test state
