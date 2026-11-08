# Tasks: add-langfuse-tracing-layer

## 1. Tracer module

- [x] `runtime/tracer.py`: TraceConfig.from_env, Tracer with
  start_trace/end_trace/span/turn_span, parent-id nesting,
  usage-or-unknown, terminal statuses (completed/failed), create_tracer
  factory.
- [x] Telemetry failures contained: exporter errors never mutate world
  state or fail the run; gaps recorded (`trace_start_failed`,
  `trace_end_failed`, `span_error`).

## 2. Runner wiring

- [x] TurnSeamRunner accepts an optional `tracer`; run() starts the
  trace, wraps each agent turn phase in a turn span (parent = run
  trace id), and emits the terminal record on every exit path
  (try/finally).
- [x] `--trace` CLI flag enables tracing by itself; LANGFUSE_* env
  configures the exporter; unconfigured = no-op.

## 3. Tests

- [x] `runtime/test_tracer.py` — 10 tests including the acceptance test
  `turnseam_runner_with_fake_exporter` (real TurnSeamRunner + fake
  exporter, structural nesting asserted).
- [x] Offline default byte-parity: same-seed scripted episode identical
  to the untraced path (probe-verified; also `--trace` with no env).

## 4. Known gaps (honest)

- [ ] Live langfuse cloud export untested in this environment (fake
  exporter + fake SDK module used for verification; the real SDK path
  is exercised only when `langfuse` is importable and keys are set).
- [ ] Model/tool child spans are emitted by the adapter path once the
  model-backed episode lands; the scripted runner emits turn spans
  only.
