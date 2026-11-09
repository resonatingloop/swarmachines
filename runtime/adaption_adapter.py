"""bounded adaption responses-api adapter for governed swarm runs."""

from __future__ import annotations

import hashlib
import time
from dataclasses import asdict, dataclass, field
from typing import Any

MAX_TOKEN_COUNT = 100_000_000
ALLOWED_STATUSES = {
    "completed",
    "incomplete",
    "failed",
    "cancelled",
    "queued",
    "in_progress",
}
ALLOWED_INCOMPLETE_REASONS = {"max_output_tokens", "content_filter"}
ALLOWED_OUTPUT_TYPES = {
    "message",
    "reasoning",
    "function_call",
    "mcp_call",
    "mcp_approval_request",
    "mcp_list_tools",
    "file_search_call",
}
ALLOWED_CONTENT_TYPES = {"output_text", "refusal"}


class ResponseContractError(RuntimeError):
    """a provider response cannot become an analytically complete call."""

    def __init__(self, category: str, diagnostics: ResponseDiagnostics):
        super().__init__(category)
        self.category = category
        self.diagnostics = diagnostics


class ResponseShapeError(ResponseContractError):
    """the provider response does not match the bounded local contract."""


class IncompleteResponseError(ResponseContractError):
    """the provider returned no acceptable visible answer."""


def _get(value: Any, name: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(name, default)
    return getattr(value, name, default)


def _bounded_int(value: Any, field_name: str, *, required: bool = True) -> int | None:
    if value is None and not required:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"invalid_{field_name}")
    if value < 0 or value > MAX_TOKEN_COUNT:
        raise ValueError(f"invalid_{field_name}")
    return value


def _allowlisted(value: Any, allowed: set[str]) -> str:
    return value if isinstance(value, str) and value in allowed else "other"


def _count_types(items: Any, allowed: set[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    if not isinstance(items, (list, tuple)):
        return counts
    for item in items:
        item_type = _allowlisted(_get(item, "type"), allowed)
        counts[item_type] = counts.get(item_type, 0) + 1
    return dict(sorted(counts.items()))


@dataclass(frozen=True)
class AdapterUsage:
    """validated token usage from a model response."""

    input_tokens: int
    output_tokens: int
    total_tokens: int
    reasoning_tokens: int | None = None
    cached_input_tokens: int | None = None


@dataclass
class ResponseDiagnostics:
    """bounded, allowlisted provider evidence safe for local persistence."""

    response_id_sha256: str | None
    status: str
    incomplete_reason: str | None
    output_item_type_counts: dict[str, int] = field(default_factory=dict)
    message_content_type_counts: dict[str, int] = field(default_factory=dict)
    visible_response_chars: int = 0
    model_matches_selected: bool = False
    categorical_error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AdapterResponse:
    """normalized response with raw payload retained in memory only."""

    model: str
    output_text: str
    usage: AdapterUsage
    latency_ms: float
    diagnostics: ResponseDiagnostics = field(repr=False)
    raw_response: Any = field(repr=False, default=None)

    def __init__(
        self,
        model: str,
        output_text: str,
        usage: AdapterUsage,
        latency_ms: float,
        diagnostics: ResponseDiagnostics | None = None,
        raw_response: Any = None,
        status: str | None = None,
        incomplete_reason: str | None = None,
    ) -> None:
        self.model = model
        self.output_text = output_text
        self.usage = usage
        self.latency_ms = latency_ms
        self.raw_response = raw_response
        if diagnostics is not None:
            self.diagnostics = diagnostics
        else:
            self.diagnostics = ResponseDiagnostics(
                response_id_sha256=None,
                status=status if status else "completed",
                incomplete_reason=incomplete_reason,
                output_item_type_counts={},
                message_content_type_counts={},
                visible_response_chars=len(output_text),
                model_matches_selected=True,
            )

    @property
    def status(self) -> str | None:
        return self.diagnostics.status if self.diagnostics else None

    @property
    def incomplete_reason(self) -> str | None:
        return self.diagnostics.incomplete_reason if self.diagnostics else None

    def validate_complete(self) -> None:
        if not self.diagnostics.model_matches_selected:
            self.diagnostics.categorical_error = "model_mismatch"
            raise IncompleteResponseError("model_mismatch", self.diagnostics)
        if self.diagnostics.status != "completed":
            self.diagnostics.categorical_error = "response_not_completed"
            raise IncompleteResponseError("response_not_completed", self.diagnostics)
        if not self.output_text.strip():
            self.diagnostics.categorical_error = "empty_visible_response"
            raise IncompleteResponseError("empty_visible_response", self.diagnostics)


class AdaptionAdapter:
    """single-attempt, bounded-time adapter for the documented responses api."""

    def __init__(self, *, client: Any | None = None, timeout_seconds: float = 60.0):
        if timeout_seconds <= 0 or timeout_seconds > 120:
            raise ValueError("timeout_seconds must be in (0, 120]")
        if client is None:
            from adaption import Adaption

            client = Adaption(max_retries=0, timeout=timeout_seconds)
        self._client = client

    def chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> AdapterResponse:
        """make exactly one request and normalize only bounded diagnostics."""
        start = time.perf_counter()
        response = self._client.responses.create(
            model=model,
            input=messages,
            **kwargs,
        )
        elapsed_ms = (time.perf_counter() - start) * 1000
        try:
            usage_raw = _get(response, "usage")
            input_tokens = _bounded_int(_get(usage_raw, "input_tokens"), "input_tokens")
            output_tokens = _bounded_int(
                _get(usage_raw, "output_tokens"), "output_tokens"
            )
            total_raw = _get(usage_raw, "total_tokens")
            total_tokens = (
                input_tokens + output_tokens
                if total_raw is None
                else _bounded_int(total_raw, "total_tokens")
            )
            input_details = _get(usage_raw, "input_tokens_details")
            output_details = _get(usage_raw, "output_tokens_details")
            cached = _bounded_int(
                _get(input_details, "cached_tokens"),
                "cached_input_tokens",
                required=False,
            )
            reasoning = _bounded_int(
                _get(output_details, "reasoning_tokens"),
                "reasoning_tokens",
                required=False,
            )
            if total_tokens < input_tokens + output_tokens:
                raise ValueError("invalid_total_tokens")
            if reasoning is not None and reasoning > output_tokens:
                raise ValueError("invalid_reasoning_tokens")
            if cached is not None and cached > input_tokens:
                raise ValueError("invalid_cached_input_tokens")
        except (TypeError, ValueError) as error:
            diagnostics = self._diagnostics(response, model, "", "malformed_usage")
            raise ResponseShapeError("malformed_usage", diagnostics) from error

        output_text = _get(response, "output_text", "")
        if not isinstance(output_text, str):
            diagnostics = self._diagnostics(
                response, model, "", "malformed_output_text"
            )
            raise ResponseShapeError("malformed_output_text", diagnostics)

        diagnostics = self._diagnostics(response, model, output_text)
        normalized_model = _get(response, "model")
        return AdapterResponse(
            model=model if normalized_model == model else "other",
            output_text=output_text,
            usage=AdapterUsage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                reasoning_tokens=reasoning,
                cached_input_tokens=cached,
            ),
            latency_ms=elapsed_ms,
            diagnostics=diagnostics,
            raw_response=response,
        )

    @staticmethod
    def _diagnostics(
        response: Any,
        selected_model: str,
        output_text: str,
        categorical_error: str | None = None,
    ) -> ResponseDiagnostics:
        response_id = _get(response, "id")
        response_id_hash = (
            hashlib.sha256(response_id.encode("utf-8")).hexdigest()
            if isinstance(response_id, str) and response_id
            else None
        )
        output = _get(response, "output", [])
        content_items: list[Any] = []
        if isinstance(output, (list, tuple)):
            for item in output:
                if _get(item, "type") == "message":
                    content = _get(item, "content", [])
                    if isinstance(content, (list, tuple)):
                        content_items.extend(content)
        incomplete_details = _get(response, "incomplete_details")
        reason_raw = _get(incomplete_details, "reason")
        return ResponseDiagnostics(
            response_id_sha256=response_id_hash,
            status=_allowlisted(_get(response, "status"), ALLOWED_STATUSES),
            incomplete_reason=(
                _allowlisted(reason_raw, ALLOWED_INCOMPLETE_REASONS)
                if reason_raw is not None
                else None
            ),
            output_item_type_counts=_count_types(output, ALLOWED_OUTPUT_TYPES),
            message_content_type_counts=_count_types(
                content_items, ALLOWED_CONTENT_TYPES
            ),
            visible_response_chars=len(output_text),
            model_matches_selected=_get(response, "model") == selected_model,
            categorical_error=categorical_error,
        )

    def simple_prompt(self, model: str, prompt: str, **kwargs: Any) -> AdapterResponse:
        return self.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            **kwargs,
        )
