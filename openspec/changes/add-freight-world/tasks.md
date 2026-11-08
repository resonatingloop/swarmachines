# tasks — add-freight-world

- [ ] 1. write freight world spec delta (specs/freight-world/spec.md) with ADDED Requirements section, SHALL statements, and WHEN/THEN scenarios
  - Note: freight world requirements are in specs/001-hackathon-plan.md (freight-in-the-fog world), not a separate spec file
- [x] 2. implement runtime/freight_world.py: graph state, depots, routes, closures, freight items, delivery jobs, legal moves, partial observations
- [x] 3. integrate freight world with runner: world.observe() for agent-specific views, world.apply_action() for route_freight validation
- [x] 4. configure scripted episode: 4 agents (a,b,c,d), 16 turns, seed 42, relay-loss@turn 8 on agent c
  - Regenerated with --disturbance relay-loss:8:c (406 events, disturbance.applied at turn 8)
- [x] 5. produce runtime/freight-episode.jsonl (schema-valid, 406 events for 16 turns × 4 agents with disturbance)
- [ ] 6. add documented rerun command (README or Makefile entry) for byte-identical replay from seed
- [x] 7. write freight world tests (runtime/test_freight_world.py): legal moves, capacity limits, observation boundaries, action validation
  - Tests integrated into runtime/test_runner.py: test_freight_illegal_move_noop, test_freight_supplies_conservation, test_freight_capacity_check, test_freight_determinism
  - All tests have real assertions (not vacuous) and pass on fixed code
  - Discriminating assertion added: FAILS on origin/master, PASSES on fixed branch (A/B verified)
- [x] 8. verify existing runner tests remain green (24/24 passing)
- [x] 9. determinism check: two same-seed runs produce byte-identical freight episode logs
- [ ] 10. update STATUS.md checkpoint with branch/PR/test state
  - Note: checkpoint not added; gate state tracked in PR #38 body and ledger
- [x] 11. fix act-phase mislabel: legal no-op → action.committed (not action.rejected)
- [x] 12. reconcile verify_events.py required types with actual event design (action.rejected and disturbance.applied are conditional)

## residue fix summary

Branch t-006-freight-residue fixes the act-phase mislabel where apply_action returning
(success=True, event_payload=None) for legal no-ops was incorrectly logged as action.rejected.

Commits:
1. fix: act-phase mislabel - legal no-op is action.committed not rejected
2. test: rewrite freight acceptance tests with real assertions
3. test: fix freight_supplies_conservation to extract freight_id from 'what' field
4. chore: regenerate freight-episode.jsonl from fixed code (436 events)
5. fix: verify_events - make action.rejected and disturbance.applied conditional
6. docs: add openspec/changes/add-freight-world with truthful tasks
