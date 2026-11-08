# Proposal: add-langfuse-tracing-layer

## Why

The spec (001-hackathon-plan, step 5) calls for langfuse-compatible
execution traces nested under agent turns, grouped by episode/run
reference. The event log owns world replay; execution traces describe
how the run executed (identity, timing, errors, usage) without
duplicating the event log's role.

## What changes

- `runtime/tracer.py`: a langfuse-compatible tracer — one trace per run
  (run id + condition + seed), spans nested under agent turns
  (observe/exchange/act) with real parent-id linkage, model/tool calls
  as child spans, usage recorded only when present (unknown otherwise,
  never fabricated), terminal record on every exit path (completed,
  failed with reason).
- `runtime/runner.py`: optional `tracer` parameter on TurnSeamRunner and
  a `--trace` CLI flag (flag alone enables; LANGFUSE_* env configures
  the exporter). When the tracer is None the run is byte-identical to
  the untraced path. Tracing failures are non-fatal: they never mutate
  world state, duplicate actions, or fail the run; gaps are recorded in
  the terminal record.
- `runtime/test_tracer.py`: suite including the acceptance test
  (`turnseam_runner_with_fake_exporter`) that drives the REAL
  TurnSeamRunner with a fake exporter and asserts structural nesting
  (span count == turns x phases x agents, parent chains).

## Scope

- The zero-model-call guarantee is unchanged: untraced and traced
  offline runs make zero provider calls; the tracer only exports when
  configured.
- World semantics, event-log schema, and the offline default path are
  untouched (byte-parity verified).

## How verified

- `python3 runtime/test_tracer.py` — 10/10 (includes the real-runner
  acceptance test).
- `python3 runtime/test_runner.py` — 24/24.
- Script-mode `python3 runtime/runner.py --trace ...` with a fake
  `langfuse` module on PYTHONPATH emits real nested spans (18 spans for
  2 turns x 3 phases x 3 agents, all parent-linked).
- Byte-parity probe: same-seed scripted episode identical to
  origin/master with and without `--trace`.
- Telemetry-failure injection: hostile exporter through a real run —
  world state unchanged, gaps recorded.
