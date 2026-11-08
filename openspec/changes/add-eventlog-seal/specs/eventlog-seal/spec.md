# event log seal — integrity contract

## ADDED Requirements

### Requirement: chain hash per event

every runner-produced event record SHALL carry a `chain` field equal to
`sha256(prev_chain_hex + "|" + canonical_json(event_without_chain))`, where
`canonical_json` is `json.dumps(event, sort_keys=True, separators=(",", ":"))`
and `prev_chain_hex` for the first event is
`sha256("swarmachines/eventlog-seal-v1|" + run_id)`. the chain SHALL be
recomputable from the log content alone.

#### Scenario: two honest runs agree

- **WHEN** the runner produces two logs from the same seed
- **THEN** the logs are byte-identical, chain fields included

#### Scenario: the chain is independently recomputable

- **WHEN** a third party recomputes the chain from a sealed log
- **THEN** every recomputed hash matches the recorded chain field

### Requirement: terminal seal record

every runner-produced log SHALL end with exactly one `run.seal` record whose
payload carries `chain` (the terminal chain hash over all preceding events),
`events` (the number of sealed records), and `alg` (the constant
`eventlog-seal-v1`), with no additional payload properties. appending any
event after the seal SHALL raise.

#### Scenario: appending after the seal is refused

- **WHEN** `append` is called on a sealed EventLog
- **THEN** it raises instead of producing a record

### Requirement: analyzer verifies a present seal

the offline analyzer SHALL verify the chain and the seal whenever a log
contains any chain field or any `run.seal` record, and SHALL reject with a
categorical error when: any chained event's recomputed hash differs, a
chained event is missing between two chained neighbors, the seal's event
count disagrees with the number of preceding records, the seal's chain
disagrees with the recomputed terminal hash, or the seal is not the final
record. a log with no chain fields and no seal record SHALL remain valid.

#### Scenario: edited event is detected

- **WHEN** one byte of a chained event's payload is altered after the run
- **THEN** the analyzer rejects the log with a categorical error

#### Scenario: inserted event is detected

- **WHEN** a fabricated event is inserted between two chained events
- **THEN** the analyzer rejects the log with a categorical error

#### Scenario: removed event is detected

- **WHEN** a chained event is deleted from a sealed log
- **THEN** the analyzer rejects the log with a categorical error

#### Scenario: legacy logs stay valid

- **WHEN** the analyzer reads a log with no chain fields and no seal record
- **THEN** validation passes and the measurements are unchanged

### Requirement: schema admits the seal

the event schema SHALL include `run.seal` in the type enum, an optional
`chain` property (lowercase hex sha256), and a `run.seal` payload shape with
required `chain`, `events`, `alg` and `additionalProperties: false`.

#### Scenario: sealed log validates

- **WHEN** a runner-produced sealed log is validated against the schema
- **THEN** every record, including the seal, validates
