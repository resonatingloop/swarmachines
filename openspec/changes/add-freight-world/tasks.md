# tasks — add-freight-world

- [x] 1. write freight world spec delta (specs/freight-world/spec.md) with ADDED Requirements section, SHALL statements, and WHEN/THEN scenarios
- [x] 2. implement runtime/freight_world.py: graph state, depots, routes, closures, freight items, delivery jobs, legal moves, partial observations
- [x] 3. integrate freight world with runner: world.observe() for agent-specific views, world.apply_action() for route_freight validation
- [x] 4. configure scripted episode: 4 agents (a,b,c,d), 16 turns, seed 42, relay-loss@turn 8 on agent c
- [x] 5. produce runtime/freight-episode.jsonl (schema-valid, 394 events for 16 turns × 4 agents)
- [ ] 6. add documented rerun command (README or Makefile entry) for byte-identical replay from seed
- [ ] 7. write freight world tests (runtime/test_freight_world.py): legal moves, capacity limits, observation boundaries, action validation
- [x] 8. verify existing 15/15 runner tests remain green
- [x] 9. determinism check: two same-seed runs produce byte-identical freight episode logs
- [ ] 10. update STATUS.md checkpoint with branch/PR/test state
