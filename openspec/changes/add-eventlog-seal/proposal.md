# add the event log seal

## why

the formal gate on the job-evidence change (#34) accepted the pipeline with one
open MEDIUM, dispositioned as a follow-up (ledger `swarmachines-i64`): the
event log is append-only by convention but nothing detects fabrication. an
episode is the evidence artifact the offline analyzer certifies measurements
from; a record inserted, edited, or removed after the fact currently produces
the same measurements as an honest run. policy-level fabrication — inventing
deliveries, decisions, or terminal states that never happened — must be
detectable from the log alone, without trusting the producer.

## what changes

- every event record optionally carries a `chain` field: the sha256 hash of
  the previous chain hash plus the canonical JSON of the event without its
  chain field. the chain is deterministic and recomputable from the log
  content alone — no secret, no clock, no producer trust.
- a terminal `run.seal` certification record closes every runner-produced
  log: it carries the terminal chain hash, the sealed event count, and the
  algorithm tag. appending after the seal is refused.
- the offline analyzer verifies the seal when one is present: any edit to a
  chained event, any inserted or removed chained event, or any chain
  discontinuity is rejected with a categorical error. a log with no seal
  fields at all remains valid (byte-compat with the settled base); a log
  where some records are chained and others are not is rejected.
- the event schema gains the `run.seal` type, the optional `chain` property,
  and a strict payload shape for `run.seal`.

## out of scope

- signatures or secrets (the seal detects accidental and post-hoc
  fabrication; it is not an authentication mechanism — a fabricator with
  write access can recompute a whole chain, which is why the analyzer's
  provenance rules stay in place)
- retroactive sealing of previously produced fixture logs
- changes to measure semantics: sealed records measure identically to
  unsealed ones
