#!/usr/bin/env python3
"""
Adaption provider adapter for swarmachines.

Provides a thin wrapper around the Adaption SDK for model inference calls.
Reads ADAPTION_API_KEY from environment; never prints or logs the key.

Usage:
    from adaption_adapter import AdaptionAdapter

    adapter = AdaptionAdapter()
    response = adapter.chat(
        model="glm-53-flash",
        messages=[{"role": "user", "content": "Hello"}],
    )
    print(response.output_text)
    print(f"Latency: {response.latency_ms:.2f}ms")
    print(f"Tokens: {response.usage.input_tokens} + {response.usage.output_tokens}")
"""

import time
from dataclasses import dataclass
from typing import Any


class IncompleteResponseError(RuntimeError):
    """Raised when a response is not complete or has no visible output.

    The or6 incident (runs 001-004, 2026-11-08): glm-53-flash burned the
    entire max_output_tokens budget on reasoning before emitting visible
    text — status "incomplete", reasoning_tokens == output_tokens,
    output_text "". The adapter previously discarded the diagnostic fields
    (status, incomplete_details, usage breakdown), so the failure was
    silent by construction. This error makes it loud by design.

    The ``diagnostics`` attribute carries the captured fields so a
    single sealer can emit ONE canonical source-linked failure event.
    """

    diagnostics: dict[str, Any] | None = None


@dataclass
class AdapterUsage:
    """Token usage from a model response."""

    input_tokens: int
    output_tokens: int
    total_tokens: int
    reasoning_tokens: int = 0


@dataclass
class AdapterResponse:
    """Normalized response from the Adaption adapter."""

    model: str
    output_text: str
    usage: AdapterUsage
    latency_ms: float
    raw_response: Any
    status: str = ""
    incomplete_reason: str | None = None

    def validate_complete(self) -> "AdapterResponse":
        """Fail closed unless the response is complete with visible output.

        Returns:
            self, for call-chaining.

        Raises:
            IncompleteResponseError: if the response status is not
                "completed" or the visible output text is empty — with the
                captured diagnostics in the message so the failure names
                its cause.
        """
        text = (self.output_text or "").strip()
        if self.status != "completed" or not text:
            err = IncompleteResponseError(
                f"incomplete model response: status={self.status!r} "
                f"incomplete_reason={self.incomplete_reason!r} "
                f"output_text_len={len(self.output_text or '')} "
                f"reasoning_tokens={self.usage.reasoning_tokens} "
                f"output_tokens={self.usage.output_tokens}"
            )
            err.diagnostics = {
                "status": self.status,
                "incomplete_reason": self.incomplete_reason,
                "reasoning_tokens": self.usage.reasoning_tokens,
                "output_tokens": self.usage.output_tokens,
            }
            raise err
        return self


class AdaptionAdapter:
    """
    Adaption provider adapter for swarmachines.

    Wraps the Adaption SDK to provide a consistent interface for model calls.
    Records latency, tokens, status, and model ID for each call.

    Credential contract: the API key is read from the ADAPTION_API_KEY
    environment variable by the SDK itself. Do not pass credentials
    as arguments. If the env var is absent, the SDK will raise its
    own error on first use.
    """

    def __init__(self):
        """
        Initialize the Adaption adapter.

        The SDK reads ADAPTION_API_KEY from the environment automatically.
        No arguments are accepted — credentials must come from the environment.
        """
        # Lazy import: allows graceful degradation when SDK is unavailable
        from adaption import Adaption

        self._client = Adaption()

    def chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        **kwargs,
    ) -> AdapterResponse:
        """
        Send a chat completion request to Adaption.

        Args:
            model: Model ID (e.g., "glm-53-flash", "gemma-4-26b-a4b-it").
            messages: List of message dicts with "role" and "content" keys.
            **kwargs: Additional parameters passed to the Adaption API.

        Returns:
            AdapterResponse with normalized output, usage, latency, and the
            completion diagnostics (status, incomplete_reason,
            reasoning_tokens) captured from the SDK — the fields the or6
            receipts discarded.

        Raises:
            adaption.AdaptionError: If the API call fails. Completion
            validation is the caller's: call validate_complete().
        """
        start = time.perf_counter()

        # Adaption uses 'input' parameter (not 'messages') for the prompt/messages
        response = self._client.responses.create(
            model=model,
            input=messages,
            **kwargs,
        )

        elapsed_ms = (time.perf_counter() - start) * 1000

        usage_obj = getattr(response, "usage", None)
        out_details = (
            getattr(usage_obj, "output_tokens_details", None) if usage_obj else None
        )
        reasoning_tokens = getattr(out_details, "reasoning_tokens", 0) or 0
        incomplete = getattr(response, "incomplete_details", None)
        incomplete_reason = getattr(incomplete, "reason", None) if incomplete else None
        input_tokens = getattr(usage_obj, "input_tokens", 0) or 0
        output_tokens = getattr(usage_obj, "output_tokens", 0) or 0

        usage = AdapterUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            reasoning_tokens=reasoning_tokens,
        )

        return AdapterResponse(
            model=getattr(response, "model", model),
            output_text=getattr(response, "output_text", "") or "",
            usage=usage,
            latency_ms=elapsed_ms,
            raw_response=response,
            status=getattr(response, "status", "") or "",
            incomplete_reason=incomplete_reason,
        )

    def simple_prompt(
        self,
        model: str,
        prompt: str,
        **kwargs,
    ) -> AdapterResponse:
        """
        Send a simple text prompt to Adaption.

        Convenience wrapper for single-turn text completion.

        Args:
            model: Model ID.
            prompt: Text prompt.
            **kwargs: Additional parameters passed to the Adaption API.

        Returns:
            AdapterResponse, see chat().
        """
        return self.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            **kwargs,
        )
