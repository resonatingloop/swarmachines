"""
Langfuse-compatible execution tracing for swarmachines.

Provides optional tracing behind --trace CLI flag and LANGFUSE_* env config.
When unconfigured, tracing is a no-op (zero network, zero behavior change).

Trace shape per spec (specs/001-hackathon-plan.md step 5):
- One trace per run (run id + condition + seed)
- Spans nested under each agent turn (observe/exchange/act)
- Model/tool calls as child spans with identity, latency, error, and token usage
- Missing usage recorded as unknown, not fabricated
- Telemetry failures are non-fatal: never alter world state, duplicate action, or fail run

Langfuse data model: https://langfuse.com/docs/observability/data-model
"""

import os
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class RunStatus(Enum):
    """Terminal run states per spec."""

    COMPLETED = "completed"
    FAILED = "failed"
    BUDGET_STOPPED = "budget-stopped"
    CANCELLED = "cancelled"


@dataclass
class TraceConfig:
    """Configuration for tracing."""

    enabled: bool = False
    public_key: str | None = None
    secret_key: str | None = None
    host: str | None = None
    run_id: str | None = None
    condition: str | None = None
    seed: int | None = None

    @classmethod
    def from_env(
        cls,
        run_id: str | None = None,
        condition: str | None = None,
        seed: int | None = None,
    ) -> "TraceConfig":
        """Build config from environment variables."""
        enabled = os.environ.get("LANGFUSE_ENABLED", "").lower() == "true"
        # Also enable if --trace flag was used (passed via env)
        if os.environ.get("TRACE_ENABLED", "").lower() == "true":
            enabled = True

        return cls(
            enabled=enabled,
            public_key=os.environ.get("LANGFUSE_PUBLIC_KEY"),
            secret_key=os.environ.get("LANGFUSE_SECRET_KEY"),
            host=os.environ.get("LANGFUSE_HOST"),
            run_id=run_id,
            condition=condition,
            seed=seed,
        )


@dataclass
class SpanContext:
    """Context for a span being built."""

    id: str
    name: str
    start_time: datetime
    parent_id: str | None = None
    metadata: dict = field(default_factory=dict)
    usage: dict | None = None
    error: str | None = None


class FakeExporter:
    """
    In-memory exporter for testing.
    Captures trace events without network calls.
    """

    def __init__(self):
        self.traces: list[dict] = []
        self.spans: list[dict] = []
        self.errors: list[dict] = []

    def trace(self, trace_data: dict) -> None:
        """Record a trace."""
        self.traces.append(trace_data)

    def span(self, span_data: dict) -> None:
        """Record a span."""
        self.spans.append(span_data)

    def error(self, error_data: dict) -> None:
        """Record an error."""
        self.errors.append(error_data)

    def clear(self) -> None:
        """Clear all recorded events."""
        self.traces.clear()
        self.spans.clear()
        self.errors.clear()

    def get_spans_by_parent(self, parent_id: str | None) -> list[dict]:
        """Get all spans with a given parent."""
        return [s for s in self.spans if s.get("parent_id") == parent_id]

    def get_spans_by_name(self, name: str) -> list[dict]:
        """Get all spans with a given name."""
        return [s for s in self.spans if s.get("name") == name]


class Tracer:
    """
    Langfuse-compatible tracer.

    When not configured (no keys), all methods are no-ops.
    When configured, uses Langfuse SDK or fake exporter for tests.
    """

    def __init__(self, config: TraceConfig, exporter: FakeExporter | None = None):
        self.config = config
        self.exporter = exporter  # Fake exporter for tests
        self._client = None
        self._current_trace = None
        self._current_trace_id: str | None = None
        self._span_stack: list[SpanContext] = []
        self._telemetry_errors: list[dict] = []
        self._initialized = False

    def _try_init(self) -> bool:
        """Try to initialize the Langfuse client. Returns True if successful."""
        if not self.config.enabled:
            return False

        if self._initialized:
            # Already initialized: success if we have either a real client or fake exporter
            return self._client is not None or self.exporter is not None

        self._initialized = True

        # If using fake exporter (tests), no real client needed
        if self.exporter is not None:
            return True

        # Try to import and initialize Langfuse
        if not self.config.public_key or not self.config.secret_key:
            return False

        try:
            from langfuse import Langfuse

            self._client = Langfuse(
                public_key=self.config.public_key,
                secret_key=self.config.secret_key,
                host=self.config.host,
            )
            return True
        except Exception:  # noqa: BLE001
            # Telemetry failure: log and continue as no-op
            self._telemetry_errors.append(
                {
                    "type": "init_failed",
                    "time": datetime.now(UTC).isoformat() + "Z",
                }
            )
            return False

    def start_trace(
        self, run_id: str, condition: str | None = None, seed: int | None = None
    ) -> None:
        """
        Start a new trace for a run.

        Per spec: one trace per run (run id + condition + seed).
        """
        # Store the trace id for child spans to reference
        self._current_trace_id = run_id

        if not self._try_init():
            return

        trace_data = {
            "id": run_id,
            "name": f"swarmachines-run-{run_id}",
            "metadata": {
                "condition": condition,
                "seed": seed,
                "type": "run",
            },
            "input": {
                "run_id": run_id,
                "condition": condition,
                "seed": seed,
            },
        }

        try:
            if self.exporter:
                self.exporter.trace(trace_data)
            elif self._client:
                self._current_trace = self._client.trace(**trace_data)
        except Exception as e:  # noqa: BLE001
            # Telemetry failure: non-fatal, log and continue
            self._telemetry_errors.append(
                {
                    "type": "trace_start_failed",
                    "time": datetime.now(UTC).isoformat() + "Z",
                    "error": str(type(e).__name__),
                }
            )

    def end_trace(self, status: RunStatus, reason: str | None = None) -> None:
        """
        End the current trace with terminal status.

        Per spec: finish runs as completed/failed/budget-stopped/cancelled with a reason.
        """
        if not self._try_init():
            return

        output_data = {
            "status": status.value,
            "reason": reason,
            "telemetry_errors": len(self._telemetry_errors),
        }

        try:
            if self.exporter:
                self.exporter.trace(
                    {
                        "id": self.config.run_id,
                        "output": output_data,
                    }
                )
            elif self._current_trace:
                self._current_trace.update(output=output_data)
                self._current_trace.end()
        except Exception as e:  # noqa: BLE001
            # Telemetry failure: non-fatal
            self._telemetry_errors.append(
                {
                    "type": "trace_end_failed",
                    "time": datetime.now(UTC).isoformat() + "Z",
                    "error": str(type(e).__name__),
                }
            )

    @contextmanager
    def span(
        self, name: str, parent_id: str | None = None, metadata: dict | None = None
    ):
        """
        Create a span with automatic timing.

        Usage:
            with tracer.span("observe", metadata={"agent_id": "a"}):
                # do work
        """
        if not self._try_init():
            yield
            return

        start_time = datetime.now(UTC)
        span_data = {
            "name": name,
            "start_time": start_time,
            "parent_id": parent_id,
            "metadata": metadata or {},
        }

        langfuse_span = None
        try:
            if self.exporter:
                # Fake exporter: record span start
                pass
            elif self._current_trace:
                langfuse_span = self._current_trace.span(
                    name=name,
                    parent_id=parent_id,
                    metadata=metadata or {},
                )
        except Exception as e:  # noqa: BLE001
            # Telemetry failure: non-fatal, continue without tracing
            self._telemetry_errors.append(
                {
                    "type": "span_start_failed",
                    "name": name,
                    "time": datetime.now(UTC).isoformat() + "Z",
                    "error": str(type(e).__name__),
                }
            )
            yield
            return

        try:
            yield
        except Exception as e:
            # Record error in span
            if langfuse_span:
                try:
                    langfuse_span.end(
                        level="ERROR",
                        status_message=str(e),
                    )
                except Exception:  # noqa: BLE001, S110
                    pass
            self._telemetry_errors.append(
                {
                    "type": "span_error",
                    "name": name,
                    "time": datetime.now(UTC).isoformat() + "Z",
                    "error": str(e),
                }
            )
            raise
        else:
            # Success: end span with timing
            end_time = datetime.now(UTC)
            duration_ms = (end_time - start_time).total_seconds() * 1000

            span_data["end_time"] = end_time
            span_data["duration_ms"] = duration_ms

            try:
                if self.exporter:
                    self.exporter.span(span_data)
                elif langfuse_span:
                    langfuse_span.end()
            except Exception as e:  # noqa: BLE001
                self._telemetry_errors.append(
                    {
                        "type": "span_end_failed",
                        "name": name,
                        "time": datetime.now(UTC).isoformat() + "Z",
                        "error": str(type(e).__name__),
                    }
                )

    @property
    def current_trace_id(self) -> str | None:
        """Return the current trace id (set by start_trace)."""
        return self._current_trace_id

    @contextmanager
    def turn_span(
        self, turn: int, phase: str, agent_id: str, parent_id: str | None = None
    ):
        """
        Create a span for an agent turn phase (observe/exchange/act).

        Per spec: nest model/tool observations under agent turns grouped by episode/run reference.
        """
        span_name = f"turn-{turn}-{phase}"
        metadata = {
            "turn": turn,
            "phase": phase,
            "agent_id": agent_id,
            "type": "agent_turn",
        }

        with self.span(span_name, parent_id=parent_id, metadata=metadata):
            yield

    def record_model_call(
        self,
        model_id: str,
        prompt_tokens: int | None = None,
        completion_tokens: int | None = None,
        total_tokens: int | None = None,
        latency_ms: float | None = None,
        error: str | None = None,
    ) -> None:
        """
        Record a model call as a child span with usage data.

        Per spec: record identity, timing, errors, and usage; missing usage remains unknown.
        """
        if not self._try_init():
            return

        # Per spec: missing usage recorded as unknown, not fabricated
        usage = {
            "prompt_tokens": prompt_tokens if prompt_tokens is not None else "unknown",
            "completion_tokens": completion_tokens
            if completion_tokens is not None
            else "unknown",
            "total_tokens": total_tokens if total_tokens is not None else "unknown",
        }

        metadata = {
            "model_id": model_id,
            "type": "model_call",
            "latency_ms": latency_ms,
        }

        span_data = {
            "name": f"model:{model_id}",
            "metadata": metadata,
            "usage": usage,
            "error": error,
        }

        try:
            if self.exporter:
                self.exporter.span(span_data)
            elif self._current_trace:
                span = self._current_trace.span(
                    name=f"model:{model_id}",
                    metadata=metadata,
                )
                # Per spec: record usage only when present, never fabricate zeros
                # Langfuse SDK accepts None for unknown usage
                if (
                    prompt_tokens is not None
                    or completion_tokens is not None
                    or total_tokens is not None
                ):
                    span.usage(
                        input=prompt_tokens,
                        output=completion_tokens,
                        total=total_tokens,
                    )
                if error:
                    span.end(level="ERROR", status_message=error)
                else:
                    span.end()
        except Exception as e:  # noqa: BLE001
            # Telemetry failure: non-fatal
            self._telemetry_errors.append(
                {
                    "type": "model_call_record_failed",
                    "model_id": model_id,
                    "time": datetime.now(UTC).isoformat() + "Z",
                    "error": str(type(e).__name__),
                }
            )

    def record_tool_call(
        self,
        tool_name: str,
        args: dict | None = None,
        result: Any | None = None,
        latency_ms: float | None = None,
        error: str | None = None,
    ) -> None:
        """
        Record a tool call as a child span.

        Per spec: record identity, timing, errors.
        """
        if not self._try_init():
            return

        metadata = {
            "tool_name": tool_name,
            "type": "tool_call",
            "latency_ms": latency_ms,
            "args": args,
        }

        span_data = {
            "name": f"tool:{tool_name}",
            "metadata": metadata,
            "error": error,
        }

        try:
            if self.exporter:
                self.exporter.span(span_data)
            elif self._current_trace:
                span = self._current_trace.span(
                    name=f"tool:{tool_name}",
                    metadata=metadata,
                )
                if error:
                    span.end(level="ERROR", status_message=error)
                else:
                    span.end()
        except Exception as e:  # noqa: BLE001
            # Telemetry failure: non-fatal
            self._telemetry_errors.append(
                {
                    "type": "tool_call_record_failed",
                    "tool_name": tool_name,
                    "time": datetime.now(UTC).isoformat() + "Z",
                    "error": str(type(e).__name__),
                }
            )

    def get_telemetry_errors(self) -> list[dict]:
        """Return list of telemetry errors encountered."""
        return self._telemetry_errors.copy()

    def flush(self) -> None:
        """Flush any pending trace data."""
        if not self._try_init():
            return

        try:
            if self._client:
                self._client.flush()
        except Exception:  # noqa: BLE001, S110
            # Non-fatal
            pass


def create_tracer(
    run_id: str,
    condition: str | None = None,
    seed: int | None = None,
    use_fake_exporter: bool = False,
) -> tuple[Tracer, FakeExporter | None]:
    """
    Create a tracer for a run.

    Args:
        run_id: Unique run identifier
        condition: Experimental condition (e.g., "mesh", "ring-mute")
        seed: Random seed used
        use_fake_exporter: If True, use in-memory exporter for tests

    Returns:
        Tuple of (tracer, fake_exporter) - exporter is None if not using fake
    """
    config = TraceConfig.from_env(run_id=run_id, condition=condition, seed=seed)

    # Enable tracing when using fake exporter (tests)
    if use_fake_exporter:
        config.enabled = True

    exporter = FakeExporter() if use_fake_exporter else None

    tracer = Tracer(config, exporter=exporter)

    return tracer, exporter
