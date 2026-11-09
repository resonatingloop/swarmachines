# tasks: repair task10 response capture and observability

> status: accepted for bounded implementation — paid provider calls, upload,
> publication, and continuation of runs `005–015` remain separately gated.

## 1. credential and sdk boundary

- [x] verify the owner-supplied credential file's path, ownership, mode, shape,
  and base url without printing values.
- [x] determine server compatibility and pin the supported langfuse sdk range.
- [x] add a fail-closed private-file loader and synthetic permission tests.

## 2. response contract

- [x] add bounded response diagnostics and visible-response validation.
- [x] use no tools, no memory, no storage, no retries, bounded timeout, fixed
  direct-answer instruction, and 4096 maximum output tokens.
- [x] update budget proofs for the larger per-call allowance under the existing
  aggregate ceiling.
- [x] validate completed and failed call events before sealing, emit exactly one
  source-linked `model.call.failed` event for a rejected attempt, and make
  empty/incomplete output a terminal run failure.

## 3. langfuse integration

- [x] replace the deprecated real-client surface with current observations.
- [x] emit one run root and one generation per provider call with allowlisted
  metadata/hashes only.
- [x] apply export-stage masking, explicit terminal flush, and local categorical
  telemetry failure evidence.
- [x] stop before another provider call if trace creation/export fails; never
  repeat the already-paid call.

## 4. offline proof

- [x] cover completed, reasoning-only, incomplete, refused, malformed, timeout,
  telemetry-failure, and interruption paths with fake sdks.
- [x] prove trace-off byte parity, zero network by default, unchanged provider
  call counts, schema validation, and package-boundary seal verification.
- [x] run all affected project-owned gates and record exact results.

## 5. external gates

- [ ] obtain independent exact-head review.
- [ ] run owner-authorized auth check and fictional synthetic trace; flush and
  read back the trace.
- [ ] run one separately authorized adaption diagnostic call; reconcile local
  and remote metadata.
- [ ] return the continuation contract for a new owner ruling. do not infer
  authorization for runs `005–015`, packaging, upload, or publication.

## offline evidence

- `pytest -q`: 189 passed, 201 subtests passed; 42 pre-existing
  return-not-none warnings.
- ruff on every changed python file: all checks passed.
- task10 provider-free preflight: 15 instances, 1,920 planned calls, 4,096
  maximum output tokens, 7.471104 maximum reserved credits under the 10-credit
  ceiling, zero provider calls.
- installed langfuse `5.2.0`: current observation/generation/masking/flush
  surface exercised through an in-memory exporter with zero network.
- documentation checker: 6 pre-existing missing-status errors in older specs
  and 8 status-heading warnings; no new broken link or template residue was
  reported.
