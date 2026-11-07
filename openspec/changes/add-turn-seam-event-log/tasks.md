# tasks — add-turn-seam-event-log

- [ ] 1. write the event schema (JSON schema) plus a reference sample episode
      as JSONL (~20 events covering all event types)
- [ ] 2. implement the turn cycle with enforced phase order:
      observe → exchange → act → record
- [ ] 3. implement communication topology config (`mesh`, `hub-spoke`),
      independent of the delivery graph
- [ ] 4. implement message lifecycle states and the per-agent
      "was this report in context at turn n?" query
- [ ] 5. implement the two disturbances with scheduled application and
      before/after events
- [ ] 6. scripted dispatchers + seed control; produce one complete sample run
      log under `runtime/`
- [ ] 7. determinism check: two same-seed runs produce byte-identical logs
- [x] 8. after owner acceptance: update the STATUS.md checkpoint and point
      the observatory lane at the sample log (2026-11-07: topology ruling merged via PR #2)
