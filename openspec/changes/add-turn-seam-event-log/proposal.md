# add the turn seam and event log

## why

the proposal names one seam every lane needs before parallel work: a single
turn defined as observation → exchange → act → record, plus the event record
that makes runs replayable and comparable. agents.md flags the gap
directly: "the proposed observation/action/event seam has no accepted schema
yet." this change drafts that contract so the observatory can replay a real
log, the world can run scripted turns, and the nervous system can bind model
calls later without reworking the record.

## what changes

- one event schema with stable identifiers: `run_id`, `agent_id`, `turn`,
  `seq`, `type`, `ts`, plus a payload; `(run_id, seq)` unique per run
- one turn cycle in fixed phase order: observe → exchange → act → record
- communication topology configurable independently of the delivery map,
  with two named arrangements: `mesh` and `hub-spoke`
- message lifecycle recorded as sent / delivered / seen / acted_on
- two named disturbances, `relay-loss` and `stale-report`, schedulable at a
  defined turn, each emitting before/after world events
- a scripted-dispatcher runner that produces a complete event log with zero
  model calls — the observatory's first replay input

## out of scope

- adaption model calls and langfuse tracing (a later change binds them)
- lane assignments, scoring policy beyond delivery outcomes, and the
  learning-loop branch

## acceptance

requirements verified against the sample run; owner accepts before any
archival. draft until then.
