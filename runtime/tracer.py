"""privacy-bounded langfuse tracing for governed swarm runs."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

LANGFUSE_REQUEST_TIMEOUT_SECONDS = 10


class RunStatus(Enum):
    COMPLETED = "completed"
    FAILED = "failed"
    BUDGET_STOPPED = "budget-stopped"
    CANCELLED = "cancelled"


class TelemetryFailure(RuntimeError):
    """a strict trace operation failed and the live batch must stop."""


@dataclass(frozen=True)
class TraceConfig:
    enabled: bool = False
    public_key: str | None = field(default=None, repr=False)
    secret_key: str | None = field(default=None, repr=False)
    base_url: str | None = None
    run_id: str | None = None
    condition: str | None = None
    seed: int | None = None
    strict: bool = False
    release: str = "uncommitted"
    environment: str = "task10"

    @classmethod
    def from_file(
        cls,
        path: str | Path,
        *,
        release: str,
        strict: bool = True,
    ) -> TraceConfig:
        """load a private credentials file without changing process environment."""
        credential_path = Path(path)
        metadata = credential_path.lstat()
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
            raise ValueError(
                "langfuse credential path must be a regular non-symlink file"
            )
        if metadata.st_uid != os.getuid():
            raise PermissionError("langfuse credential file must be owned by this user")
        if stat.S_IMODE(metadata.st_mode) & 0o077:
            raise PermissionError(
                "langfuse credential file must have mode 0600 or stricter"
            )

        values: dict[str, str] = {}
        for raw_line in credential_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            key, separator, value = line.partition("=")
            if not separator or key not in {
                "LANGFUSE_PUBLIC_KEY",
                "LANGFUSE_SECRET_KEY",
                "LANGFUSE_BASE_URL",
            }:
                raise ValueError("langfuse credential file has an invalid field")
            value = value.strip()
            starts_quoted = value.startswith(('"', "'"))
            ends_quoted = value.endswith(('"', "'"))
            if starts_quoted or ends_quoted:
                if len(value) < 2 or value[0] != value[-1]:
                    raise ValueError("langfuse credential file has invalid quoting")
                value = value[1:-1]
            if key in values or not value:
                raise ValueError(
                    "langfuse credential file has a duplicate or empty field"
                )
            values[key] = value

        required = {
            "LANGFUSE_PUBLIC_KEY",
            "LANGFUSE_SECRET_KEY",
            "LANGFUSE_BASE_URL",
        }
        if set(values) != required:
            raise ValueError("langfuse credential file is incomplete")
        parsed = urlparse(values["LANGFUSE_BASE_URL"])
        if parsed.scheme != "https" or not parsed.hostname or parsed.username:
            raise ValueError("langfuse base url must be an https origin")
        if parsed.query or parsed.fragment:
            raise ValueError("langfuse base url must not contain query or fragment")

        return cls(
            enabled=True,
            public_key=values["LANGFUSE_PUBLIC_KEY"],
            secret_key=values["LANGFUSE_SECRET_KEY"],
            base_url=values["LANGFUSE_BASE_URL"].rstrip("/"),
            strict=strict,
            release=release,
        )


def create_langfuse_client(config: TraceConfig) -> Any:
    """construct the current sdk client from an already validated config."""
    if not (
        config.enabled and config.public_key and config.secret_key and config.base_url
    ):
        raise ValueError("langfuse trace config is incomplete")

    from langfuse import Langfuse

    return Langfuse(
        public_key=config.public_key,
        secret_key=config.secret_key,
        base_url=config.base_url,
        release=config.release,
        environment=config.environment,
        timeout=LANGFUSE_REQUEST_TIMEOUT_SECONDS,
        mask_otel_spans=_mask_otel_spans,
    )


class FakeExporter:
    """zero-network trace sink used by offline proofs."""

    def __init__(self):
        self.traces: list[dict[str, Any]] = []
        self.spans: list[dict[str, Any]] = []
        self.generations: list[dict[str, Any]] = []
        self.errors: list[dict[str, Any]] = []
        self.flush_count = 0
        self.fail_flush = False

    def trace(self, trace_data: dict[str, Any]) -> None:
        self.traces.append(trace_data)

    def span(self, span_data: dict[str, Any]) -> None:
        self.spans.append(span_data)

    def generation(self, generation_data: dict[str, Any]) -> None:
        self.generations.append(generation_data)

    def error(self, error_data: dict[str, Any]) -> None:
        self.errors.append(error_data)

    def flush(self) -> None:
        self.flush_count += 1
        if self.fail_flush:
            raise RuntimeError("synthetic flush failure")

    def clear(self) -> None:
        self.traces.clear()
        self.spans.clear()
        self.generations.clear()
        self.errors.clear()
        self.flush_count = 0

    def get_spans_by_parent(self, parent_id: str | None) -> list[dict[str, Any]]:
        return [span for span in self.spans if span.get("parent_id") == parent_id]

    def get_spans_by_name(self, name: str) -> list[dict[str, Any]]:
        return [span for span in self.spans if span.get("name") == name]


class GenerationObservation:
    """one provider call's allowlisted, metadata-only trace state."""

    def __init__(
        self,
        *,
        traceparent: str | None,
        data: dict[str, Any],
        observation: Any = None,
    ):
        self.traceparent = traceparent
        self.data = data
        self.observation = observation

    def complete(
        self,
        *,
        response_sha256: str | None,
        diagnostics: dict[str, Any],
        usage_details: dict[str, int],
        cost_details: dict[str, float] | None,
        latency_ms: float,
        terminal_state: str,
    ) -> None:
        safe_hash = (
            response_sha256
            if isinstance(response_sha256, str)
            and re.fullmatch(r"[0-9a-f]{64}", response_sha256)
            else None
        )
        safe_usage = {
            key: value
            for key, value in usage_details.items()
            if key
            in {
                "input",
                "output",
                "total",
                "output_reasoning_tokens",
                "input_cached_tokens",
            }
            and isinstance(value, int)
            and not isinstance(value, bool)
            and 0 <= value <= 100_000_000
        }
        safe_cost = {}
        total_cost = (cost_details or {}).get("total")
        if (
            isinstance(total_cost, (int, float))
            and not isinstance(total_cost, bool)
            and 0 <= total_cost <= 10_000
        ):
            safe_cost["total"] = float(total_cost)
        safe_latency = (
            round(float(latency_ms), 3)
            if isinstance(latency_ms, (int, float))
            and not isinstance(latency_ms, bool)
            and 0 <= latency_ms <= 3_600_000
            else None
        )
        safe_terminal = (
            terminal_state
            if terminal_state in {"completed", "rejected", "failed"}
            else "failed"
        )
        self.data.update(
            output={"response_sha256": safe_hash},
            metadata={
                **self.data["metadata"],
                **_safe_diagnostics(diagnostics),
                "response_sha256": safe_hash,
                "latency_ms": safe_latency,
                "terminal_state": safe_terminal,
            },
            usage_details=safe_usage,
            cost_details=safe_cost,
        )
        if self.observation is not None:
            self.observation.update(
                output=self.data["output"],
                metadata=self.data["metadata"],
                usage_details=safe_usage,
                cost_details=safe_cost or None,
            )


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _bounded_label(value: Any, *, pattern: str, maximum: int = 64) -> str:
    if (
        isinstance(value, str)
        and 0 < len(value) <= maximum
        and re.fullmatch(pattern, value)
    ):
        return value
    return "other"


def _safe_generation_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    """project caller metadata onto the finite task10 export contract."""
    safe: dict[str, Any] = {}
    turn = metadata.get("turn")
    if isinstance(turn, int) and not isinstance(turn, bool) and 0 <= turn <= 100:
        safe["turn"] = turn
    seed = metadata.get("seed")
    if isinstance(seed, int) and not isinstance(seed, bool) and 0 <= seed <= 2**63 - 1:
        safe["seed"] = seed
    if "phase" in metadata:
        phase = metadata["phase"]
        safe["phase"] = phase if phase in {"observe", "exchange", "act"} else "other"
    if "agent_id" in metadata:
        safe["agent_id"] = _bounded_label(
            metadata["agent_id"],
            pattern=r"[a-zA-Z0-9-]+",
            maximum=40,
        )
    if "source_event_type" in metadata:
        source = metadata["source_event_type"]
        safe["source_event_type"] = (
            source if source in {"observation.recorded", "policy.decision"} else "other"
        )
    if "condition" in metadata:
        safe["condition"] = _bounded_label(
            metadata["condition"],
            pattern=r"[a-z,-]+",
        )
    if "topology" in metadata:
        topology = metadata["topology"]
        safe["topology"] = (
            topology
            if topology in {"mesh", "hub-spoke", "bidirectional-ring"}
            else "other"
        )
    return safe


def _safe_span_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    """project ordinary span metadata onto the same finite export contract."""
    safe = _safe_generation_metadata(metadata)
    span_type = metadata.get("type")
    if span_type in {"agent_turn", "model_call", "tool_call"}:
        safe["type"] = span_type
    model_id = metadata.get("model_id")
    if model_id in {"glm-53-flash", "unknown"}:
        safe["model_id"] = model_id
    for key in (
        "model_id_sha256",
        "tool_name_sha256",
        "args_sha256",
        "result_sha256",
        "error_sha256",
    ):
        value = metadata.get(key)
        if isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value):
            safe[key] = value
    for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
        value = metadata.get(key)
        if value == "unknown" or (
            isinstance(value, int)
            and not isinstance(value, bool)
            and 0 <= value <= 100_000_000
        ):
            safe[key] = value
    latency_ms = metadata.get("latency_ms")
    if (
        isinstance(latency_ms, (int, float))
        and not isinstance(latency_ms, bool)
        and 0 <= latency_ms <= 3_600_000
    ):
        safe["latency_ms"] = round(float(latency_ms), 3)
    error_category = metadata.get("error_category")
    if error_category in {
        "cancelled",
        "timeout",
        "transport",
        "validation",
        "other",
    }:
        safe["error_category"] = error_category
    return safe


def _bounded_digest(value: Any, *, text_only: bool = False) -> str | None:
    """hash bounded caller data without exporting or retaining its raw value."""
    if value is None:
        return None
    try:
        if text_only:
            if not isinstance(value, str):
                return None
            encoded = value.encode("utf-8")
        else:
            encoded = json.dumps(
                value,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            ).encode("utf-8")
    except (TypeError, ValueError, UnicodeError):
        return None
    if len(encoded) > 65_536:
        return None
    return hashlib.sha256(encoded).hexdigest()


def _safe_metric(value: Any) -> int | str:
    if (
        isinstance(value, int)
        and not isinstance(value, bool)
        and 0 <= value <= 100_000_000
    ):
        return value
    return "unknown"


def _safe_legacy_error_category(error: Any) -> str | None:
    if error is None:
        return None
    return (
        error
        if error in {"cancelled", "timeout", "transport", "validation", "other"}
        else "other"
    )


def _safe_reason_category(reason: Any) -> str | None:
    """retain only coarse terminal categories, never caller-supplied prose."""
    if reason is None:
        return None
    return (
        reason
        if reason
        in {
            "budget_stopped",
            "cancelled",
            "provider_error",
            "runner_error",
            "schema_validation_error",
            "telemetry_error",
        }
        else "other"
    )


def _safe_count_map(value: Any, allowed: set[str]) -> dict[str, int]:
    if not isinstance(value, dict):
        return {}
    return {
        key: count
        for key, count in sorted(value.items())
        if key in allowed
        and isinstance(count, int)
        and not isinstance(count, bool)
        and 0 <= count <= 10_000
    }


def _safe_diagnostics(diagnostics: dict[str, Any]) -> dict[str, Any]:
    safe: dict[str, Any] = {}
    response_hash = diagnostics.get("response_id_sha256")
    safe["response_id_sha256"] = (
        response_hash
        if isinstance(response_hash, str)
        and re.fullmatch(r"[0-9a-f]{64}", response_hash)
        else None
    )
    status = diagnostics.get("status")
    safe["status"] = (
        status
        if status
        in {
            "completed",
            "incomplete",
            "failed",
            "cancelled",
            "queued",
            "in_progress",
            "other",
        }
        else "other"
    )
    reason = diagnostics.get("incomplete_reason")
    safe["incomplete_reason"] = (
        reason if reason in {"max_output_tokens", "content_filter", "other"} else None
    )
    safe["output_item_type_counts"] = _safe_count_map(
        diagnostics.get("output_item_type_counts"),
        {
            "message",
            "reasoning",
            "function_call",
            "mcp_call",
            "mcp_approval_request",
            "mcp_list_tools",
            "file_search_call",
            "other",
        },
    )
    safe["message_content_type_counts"] = _safe_count_map(
        diagnostics.get("message_content_type_counts"),
        {"output_text", "refusal", "other"},
    )
    visible_chars = diagnostics.get("visible_response_chars")
    safe["visible_response_chars"] = (
        visible_chars
        if isinstance(visible_chars, int)
        and not isinstance(visible_chars, bool)
        and 0 <= visible_chars <= 10_000_000
        else None
    )
    model_matches = diagnostics.get("model_matches_selected")
    safe["model_matches_selected"] = (
        model_matches if isinstance(model_matches, bool) else None
    )
    error = diagnostics.get("categorical_error")
    safe["categorical_error"] = (
        error
        if error
        in {
            "model_mismatch",
            "response_not_completed",
            "empty_visible_response",
            "malformed_usage",
            "malformed_output_text",
            "provider_transport_error",
        }
        else None
    )
    return safe


def _mask_otel_spans(*, params: Any) -> Any:
    """return v5 export-stage patches that delete raw content and errors."""
    from langfuse.types import MaskOtelSpansResult, OtelSpanPatch

    blocked_prefixes = (
        "gen_ai.prompt",
        "gen_ai.completion",
        "exception.",
        "error.",
    )
    blocked_exact = {
        "langfuse.observation.input",
        "langfuse.observation.output",
        "langfuse.observation.status_message",
    }
    patches = {}
    for identifier, span in params.spans.items():
        delete_attributes = tuple(
            key
            for key in span.attributes
            if key in blocked_exact or key.startswith(blocked_prefixes)
        )
        if delete_attributes:
            patches[identifier] = OtelSpanPatch(
                delete_attributes=delete_attributes,
                set_attributes={"swarmachines.masking_applied": True},
            )
    return MaskOtelSpansResult(span_patches=patches)


class Tracer:
    """current-sdk tracing with strict task10 failure semantics."""

    def __init__(
        self,
        config: TraceConfig,
        exporter: FakeExporter | None = None,
        *,
        client: Any | None = None,
    ):
        self.config = config
        self.exporter = exporter
        self._client = client
        self._initialized = client is not None
        self._current_trace_id: str | None = None
        self._root_context: Any = None
        self._root_observation: Any = None
        self._telemetry_errors: list[dict[str, Any]] = []

    def _failure(self, category: str, error: BaseException | None = None) -> None:
        record = {
            "type": category,
            "time": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        }
        self._telemetry_errors.append(record)
        if self.exporter is not None:
            self.exporter.error(record)
        if self.config.strict:
            raise TelemetryFailure(category) from error

    def _try_init(self) -> bool:
        if not self.config.enabled:
            return False
        if self._initialized:
            return self._client is not None or self.exporter is not None
        self._initialized = True
        if self.exporter is not None:
            return True
        if not (
            self.config.public_key and self.config.secret_key and self.config.base_url
        ):
            self._failure("trace_config_incomplete")
            return False
        try:
            self._client = create_langfuse_client(self.config)
        except Exception as error:  # noqa: BLE001
            self._failure("trace_init_failed", error)
            return False
        return True

    @property
    def current_trace_id(self) -> str | None:
        return self._current_trace_id

    def start_trace(
        self, run_id: str, condition: str | None = None, seed: int | None = None
    ) -> None:
        if not self._try_init():
            return
        self._current_trace_id = (
            _sha256_text(f"swarmachines:{run_id}")[:32]
            if self.exporter is not None
            else self._client.create_trace_id(seed=f"swarmachines:{run_id}")
        )
        metadata = {
            "run_id_sha256": _sha256_text(run_id),
            "condition": _bounded_label(condition, pattern=r"[a-z,-]+")
            if condition is not None
            else None,
            "seed": seed
            if isinstance(seed, int)
            and not isinstance(seed, bool)
            and 0 <= seed <= 2**63 - 1
            else None,
            "type": "run",
            "schema_version": "task10-observability-v1",
        }
        try:
            if self.exporter is not None:
                self.exporter.trace(
                    {
                        "id": metadata["run_id_sha256"],
                        "trace_id": self._current_trace_id,
                        "metadata": metadata,
                    }
                )
                return
            self._root_context = self._client.start_as_current_observation(
                as_type="span",
                name="swarmachines-run",
                trace_context={"trace_id": self._current_trace_id},
                input={"run_id_sha256": metadata["run_id_sha256"]},
                metadata=metadata,
            )
            self._root_observation = self._root_context.__enter__()
        except Exception as error:  # noqa: BLE001
            self._failure("trace_start_failed", error)

    def end_trace(self, status: RunStatus, reason: str | None = None) -> None:
        if not self.config.enabled:
            return
        output = {
            "status": status.value,
            "reason_category": _safe_reason_category(reason),
            "telemetry_error_count": len(self._telemetry_errors),
        }
        try:
            if self.exporter is not None:
                self.exporter.trace({"id": self._current_trace_id, "output": output})
            elif self._root_observation is not None:
                self._root_observation.update(output=output)
            if self._root_context is not None:
                self._root_context.__exit__(None, None, None)
        except Exception as error:  # noqa: BLE001
            self._failure("trace_end_failed", error)
        finally:
            self._root_context = None
            self._root_observation = None
        self.flush()

    @contextmanager
    def span(
        self, name: str, parent_id: str | None = None, metadata: dict | None = None
    ):
        if not self._try_init():
            yield
            return
        safe_metadata = _safe_span_metadata(metadata or {})
        started = datetime.now(UTC)
        observation_context = None
        try:
            if self.exporter is None:
                observation_context = self._client.start_as_current_observation(
                    as_type="span",
                    name=name,
                    metadata=safe_metadata,
                )
                observation_context.__enter__()
            yield
        except BaseException as error:
            if observation_context is not None:
                observation_context.__exit__(type(error), error, error.__traceback__)
            raise
        else:
            if self.exporter is not None:
                ended = datetime.now(UTC)
                self.exporter.span(
                    {
                        "name": name,
                        "parent_id": parent_id,
                        "metadata": safe_metadata,
                        "start_time": started,
                        "end_time": ended,
                        "duration_ms": (ended - started).total_seconds() * 1000,
                    }
                )
            elif observation_context is not None:
                observation_context.__exit__(None, None, None)

    @contextmanager
    def turn_span(
        self, turn: int, phase: str, agent_id: str, parent_id: str | None = None
    ):
        with self.span(
            f"turn-{turn}-{phase}",
            parent_id=parent_id,
            metadata={
                "turn": turn,
                "phase": phase,
                "agent_id": agent_id,
                "type": "agent_turn",
            },
        ):
            yield

    @contextmanager
    def generation(
        self,
        *,
        call_id: str,
        model_id: str,
        prompt: str,
        metadata: dict[str, Any],
    ):
        """create one generation and flush it before another provider call."""
        if not self._try_init():
            yield GenerationObservation(
                traceparent=None,
                data={"metadata": dict(metadata)},
            )
            return
        safe_metadata = {
            **_safe_generation_metadata(metadata),
            "call_id_sha256": _sha256_text(call_id),
            "prompt_sha256": _sha256_text(prompt),
        }
        data: dict[str, Any] = {
            "name": "swarmachines-model-call",
            "model": model_id,
            "input": {"prompt_sha256": safe_metadata["prompt_sha256"]},
            "metadata": safe_metadata,
        }
        observation_context = None
        observation = None
        try:
            if self.exporter is None:
                observation_context = self._client.start_as_current_observation(
                    as_type="generation",
                    name=data["name"],
                    model=model_id,
                    input=data["input"],
                    metadata=safe_metadata,
                )
                observation = observation_context.__enter__()
        except Exception as error:  # noqa: BLE001
            self._failure("generation_start_failed", error)

        trace_id = self._current_trace_id or _sha256_text("missing-trace")[:32]
        if self.exporter is not None:
            observation_id = _sha256_text(call_id)[:16]
        else:
            observation_id = self._client.get_current_observation_id()
        traceparent = (
            f"00-{trace_id}-{observation_id}-01"
            if isinstance(observation_id, str)
            and len(trace_id) == 32
            and len(observation_id) == 16
            else None
        )
        capture = GenerationObservation(
            traceparent=traceparent,
            data=data,
            observation=observation,
        )
        pending_error: BaseException | None = None
        pending_traceback = None
        try:
            yield capture
        except BaseException as error:  # noqa: BLE001 - preserve user interruption evidence
            pending_error = error
            pending_traceback = error.__traceback__
            if "output" not in data:
                data.update(
                    output={"response_sha256": None},
                    metadata={
                        **data["metadata"],
                        "categorical_error": "provider_call_exception",
                        "terminal_state": "failed",
                    },
                    usage_details={},
                    cost_details={},
                )
                if observation is not None:
                    observation.update(
                        output=data["output"],
                        metadata=data["metadata"],
                    )

        export_error: BaseException | None = None
        try:
            if self.exporter is not None:
                self.exporter.generation(data)
            elif observation_context is not None:
                observation_context.__exit__(None, None, None)
            self.flush()
        except TelemetryFailure as error:
            export_error = error
        except Exception as error:  # noqa: BLE001
            try:
                self._failure("generation_export_failed", error)
            except TelemetryFailure as categorized:
                export_error = categorized
            else:
                export_error = error

        if pending_error is not None:
            raise pending_error.with_traceback(pending_traceback)
        if export_error is not None:
            raise export_error

    def record_model_call(
        self,
        model_id: str,
        prompt_tokens: int | None = None,
        completion_tokens: int | None = None,
        total_tokens: int | None = None,
        latency_ms: float | None = None,
        error: str | None = None,
    ) -> None:
        safe_model_id = model_id if model_id == "glm-53-flash" else "unknown"
        metadata = {
            "type": "model_call",
            "model_id": safe_model_id,
            "model_id_sha256": _bounded_digest(model_id, text_only=True),
            "prompt_tokens": _safe_metric(prompt_tokens),
            "completion_tokens": _safe_metric(completion_tokens),
            "total_tokens": _safe_metric(total_tokens),
            "latency_ms": latency_ms,
            "error_category": _safe_legacy_error_category(error),
            "error_sha256": _bounded_digest(error, text_only=True),
        }
        with self.span("model-call", metadata=metadata):
            pass

    def record_tool_call(
        self,
        tool_name: str,
        args: dict | None = None,
        result: Any | None = None,
        latency_ms: float | None = None,
        error: str | None = None,
    ) -> None:
        metadata = {
            "type": "tool_call",
            "tool_name_sha256": _bounded_digest(tool_name, text_only=True),
            "args_sha256": _bounded_digest(args),
            "result_sha256": _bounded_digest(result),
            "latency_ms": latency_ms,
            "error_category": _safe_legacy_error_category(error),
            "error_sha256": _bounded_digest(error, text_only=True),
        }
        with self.span("tool-call", metadata=metadata):
            pass

    def get_telemetry_errors(self) -> list[dict[str, Any]]:
        return [dict(error) for error in self._telemetry_errors]

    def flush(self) -> None:
        if not self._try_init():
            return
        try:
            if self.exporter is not None:
                self.exporter.flush()
            elif self._client is not None:
                self._client.flush()
        except Exception as error:  # noqa: BLE001
            self._failure("trace_flush_failed", error)


def create_tracer(
    run_id: str,
    condition: str | None = None,
    seed: int | None = None,
    use_fake_exporter: bool = False,
) -> tuple[Tracer, FakeExporter | None]:
    exporter = FakeExporter() if use_fake_exporter else None
    config = TraceConfig(
        enabled=use_fake_exporter,
        run_id=run_id,
        condition=condition,
        seed=seed,
    )
    return Tracer(config, exporter=exporter), exporter
