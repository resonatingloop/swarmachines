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

from adaption import Adaption


@dataclass
class AdapterUsage:
    """Token usage from a model response."""

    input_tokens: int
    output_tokens: int
    total_tokens: int


@dataclass
class AdapterResponse:
    """Normalized response from the Adaption adapter."""

    model: str
    output_text: str
    usage: AdapterUsage
    latency_ms: float
    raw_response: Any


class AdaptionAdapter:
    """
    Adaption provider adapter for swarmachines.

    Wraps the Adaption SDK to provide a consistent interface for model calls.
    Records latency, tokens, and model ID for each call.

    The ADAPTION_API_KEY environment variable must be set before instantiation.
    """

    def __init__(self, api_key: str | None = None):
        """
        Initialize the Adaption adapter.

        Args:
            api_key: Optional API key. If not provided, reads ADAPTION_API_KEY
                     from the environment (default SDK behavior).

        Raises:
            ValueError: If no API key is provided and ADAPTION_API_KEY is not set.
        """
        if api_key:
            self._client = Adaption(api_key=api_key)
        else:
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
            AdapterResponse with normalized output, usage, and latency.

        Raises:
            adaption.AdaptionError: If the API call fails.
        """
        start = time.perf_counter()

        # Convert messages to Adaption's expected format
        # Adaption uses 'input' for simple text or supports messages format
        response = self._client.responses.create(
            model=model,
            messages=messages,
            **kwargs,
        )

        elapsed_ms = (time.perf_counter() - start) * 1000

        usage = AdapterUsage(
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            total_tokens=response.usage.input_tokens + response.usage.output_tokens,
        )

        return AdapterResponse(
            model=response.model,
            output_text=response.output_text,
            usage=usage,
            latency_ms=elapsed_ms,
            raw_response=response,
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
            AdapterResponse with normalized output, usage, and latency.
        """
        return self.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            **kwargs,
        )


def smoke_test() -> dict:
    """
    Run a smoke test against the Adaption API.

    Makes a minimal call to validate connectivity and record metrics.
    Uses the small model (gemma-4-26b-a4b-it) to minimize cost.

    Returns:
        Dict with model_id, latency_ms, input_tokens, output_tokens.

    Raises:
        adaption.AdaptionError: If the API call fails.
    """
    adapter = AdaptionAdapter()
    response = adapter.simple_prompt(
        model="gemma-4-26b-a4b-it",
        prompt="Reply with exactly one word: hello",
    )
    return {
        "model_id": response.model,
        "latency_ms": response.latency_ms,
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "output_text": response.output_text,
    }


if __name__ == "__main__":
    import json
    import sys

    try:
        result = smoke_test()
        print(json.dumps(result, indent=2))
        sys.exit(0)
    except Exception as e:
        print(f"Smoke test failed: {e}", file=sys.stderr)
        sys.exit(1)
