"""Langfuse generation wiring for the swarmachines adapter.

Real current-SDK wiring (langfuse 5.x) with explicit flush and honest
degradation, per the cc1 governing contract:
- every adapter.chat() call is traced as a generation (input, output,
  model, usage incl. reasoning_tokens, metadata incl. status +
  incomplete_reason);
- explicit flush() after each call (batch_size=1 equivalent — no silent
  background loss on crash);
- lifecycle/error/interruption proof is covered by synthetic tests
  (test_or6_repair.TestLangfuseWiring) — no network, no paid calls;
- offline by default: LANGFUSE_PUBLIC_KEY absent => wiring disables
  itself with a recorded reason, never raises, never blocks a run.
"""

from __future__ import annotations

import os
from typing import Any

_LANGFUSE_CLIENT: Any = None
_LANGFUSE_STATE: dict[str, Any] = {"enabled": False, "reason": "not initialized"}


def _init_langfuse() -> Any:
    """Initialize the Langfuse client once; None when not configured.

    Returns:
        The Langfuse client, or None when keys are absent (offline mode).

    Environment:
        LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY / LANGFUSE_HOST:
        the standard SDK variables. Absent keys disable the wiring.
    """
    global _LANGFUSE_CLIENT
    if _LANGFUSE_CLIENT is not None or _LANGFUSE_STATE.get("tried"):
        return _LANGFUSE_CLIENT
    _LANGFUSE_STATE["tried"] = True
    public_key = os.environ.get("LANGFUSE_PUBLIC_KEY", "")
    secret_key = os.environ.get("LANGFUSE_SECRET_KEY", "")
    if not public_key or not secret_key:
        _LANGFUSE_STATE["reason"] = (
            "LANGFUSE_PUBLIC_KEY/LANGFUSE_SECRET_KEY not set — offline mode"
        )
        return None
    try:
        import sys

        site = "/opt/data/.local/lib/python3.14/site-packages"
        if site not in sys.path:
            sys.path.insert(0, site)
        from langfuse import Langfuse

        _LANGFUSE_CLIENT = Langfuse(public_key=public_key, secret_key=secret_key)
        _LANGFUSE_STATE.update({"enabled": True, "reason": "client initialized"})
        return _LANGFUSE_CLIENT
    except Exception as exc:  # noqa: BLE001 — degrade, never block a run
        _LANGFUSE_STATE["reason"] = f"init failed: {exc}"
        return None


def langfuse_state() -> dict[str, Any]:
    """Return the wiring state (for run.json and diagnostics)."""
    global _LANGFUSE_STATE  # noqa: PLW0602 — refreshed by init, read-only here
    _init_langfuse()
    return dict(_LANGFUSE_STATE)


def trace_generation(
    model: str,
    prompt: str,
    output_text: str,
    usage: Any,
    status: str,
    incomplete_reason: str | None,
    latency_ms: float,
    metadata: dict[str, Any] | None = None,
) -> bool:
    """Record one generation trace with explicit flush.

    Args:
        model: Model id.
        prompt: Full prompt text.
        output_text: Visible output text (may be empty on failure).
        usage: AdapterUsage (input_tokens, output_tokens, reasoning_tokens).
        status: Response status ("completed", "incomplete", ...).
        incomplete_reason: incomplete_details.reason when present.
        latency_ms: Call latency in milliseconds.
        metadata: Extra metadata merged into the trace.

    Returns:
        True when a trace was recorded and flushed; False when the
        wiring is offline or the trace failed (reason in langfuse_state()).
    """
    client = _init_langfuse()
    if client is None:
        return False
    try:
        client.create_generation(
            name="adapter.chat",
            model=model,
            input=prompt,
            output=output_text,
            usage={
                "input": getattr(usage, "input_tokens", 0),
                "output": getattr(usage, "output_tokens", 0),
                "reasoning_tokens": getattr(usage, "reasoning_tokens", 0),
                "total": getattr(usage, "total_tokens", 0),
                "latency_ms": latency_ms,
            },
            metadata={
                "status": status,
                "incomplete_reason": incomplete_reason,
                **(metadata or {}),
            },
        )
        client.flush()
        return True
    except Exception as exc:  # noqa: BLE001 — degrade, never block a run
        _LANGFUSE_STATE["reason"] = f"trace failed: {exc}"
        return False


def trace_failure(
    model: str,
    prompt: str,
    error: str,
    usage: Any,
    status: str,
    incomplete_reason: str | None,
    latency_ms: float,
) -> bool:
    """Record a failed/validation-rejected call as a generation trace.

    The failure trace carries the same fields as a success plus the error
    text as the output, so lifecycle/error/interruption events are visible
    in the trace stream alongside healthy generations.

    Returns:
        True when recorded and flushed; False when offline.
    """
    return trace_generation(
        model=model,
        prompt=prompt,
        output_text=f"FAILED: {error}",
        usage=usage,
        status=status,
        incomplete_reason=incomplete_reason,
        latency_ms=latency_ms,
        metadata={"failed": True},
    )


def shutdown_langfuse() -> None:
    """Flush and close the client at run end (explicit lifecycle close)."""
    global _LANGFUSE_CLIENT
    if _LANGFUSE_CLIENT is not None:
        try:
            _LANGFUSE_CLIENT.flush()
        except Exception as exc:  # noqa: BLE001 — best-effort close
            _LANGFUSE_STATE["reason"] = f"shutdown flush failed: {exc}"
        _LANGFUSE_CLIENT = None
        _LANGFUSE_STATE.update(
            {"enabled": False, "reason": "shutdown complete", "tried": True}
        )
