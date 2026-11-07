# turn seam — event contract

## ADDED Requirements

### Requirement: event identity

every event record SHALL carry `run_id`, `turn`, `seq`, `agent_id` (null for
world-level events), `type`, `ts`, and a type-specific payload. `(run_id,
seq)` SHALL be unique within a run, and `seq` SHALL increase monotonically in
append order.

#### Scenario: identifiers survive a replay

- **WHEN** an episode log is replayed by the observatory
- **THEN** every rendered moment resolves to exactly one event by
  `(run_id, seq)`

### Requirement: fixed turn cycle

a turn SHALL process phases in the order observe, exchange, act, record.
an agent's observation SHALL contain only that agent's local slice: its own
queue, requests addressed to it, and road/bridge knowledge within its view.

#### Scenario: partial view stays partial

- **WHEN** the world state contains information outside an agent's slice
- **THEN** that information does not appear in the agent's observation record

### Requirement: communication independence

the communication graph SHALL be configurable independently of the delivery
graph. the runner SHALL support the arrangements `mesh` (every agent may
message every other agent) and `hub-spoke` (all messages route through one
hub agent), and changing the arrangement SHALL NOT change the delivery map.

#### Scenario: same world, different wiring

- **WHEN** two runs share a seed and delivery map but differ in arrangement
- **THEN** world states and delivery outcomes remain comparable event by
  event, with only communication events differing

### Requirement: message lifecycle

each message SHALL be recorded with its lifecycle transitions: `sent`,
`delivered`, `seen`, `acted_on`. a message marked `seen` SHALL be
attributable to the receiving agent's context at a specific turn, so "the
report was in context but ignored" is answerable from the log alone.

#### Scenario: the quiet specialist is checkable

- **WHEN** an agent acts contrary to a report it received
- **THEN** the log shows the report delivered and seen before the contradicting
  action, or shows that it never arrived

### Requirement: disturbances

the disturbances `relay-loss` (one named agent becomes unreachable for the
rest of the run) and `stale-report` (an outdated route report enters
circulation) SHALL each be schedulable at a defined turn and SHALL emit
explicit before/after world events.

#### Scenario: scheduled rupture

- **WHEN** a run config schedules `relay-loss` at turn 8
- **THEN** the event log contains a disruption event at turn 8 and messages
  addressed to the lost agent after that turn are recorded as undelivered

### Requirement: replay determinism

with the same seed and the same recorded decisions, regenerating a run SHALL
produce an identical event log, and replay SHALL be playback of the log, not
re-simulation.

#### Scenario: byte-identical rerun

- **WHEN** the same seed drives two scripted runs
- **THEN** the two event logs are byte-identical

### Requirement: zero-model operation

the full turn cycle SHALL run to a complete event log using scripted
dispatchers only, with no model or network calls.

#### Scenario: offline sample episode

- **WHEN** the runner executes a scripted run
- **THEN** the resulting log satisfies every requirement above without any
  provider call
