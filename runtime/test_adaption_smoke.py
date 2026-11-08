#!/usr/bin/env python3
"""
Smoke test for the Adaption adapter.

OPTIONAL: Requires ADAPTION_API_KEY environment variable and SDK installed.
This is NOT a CI gate - it is a proof-on-record for the key holder to run.
The actual CI gate is test_adaption_adapter_unit.py which mocks the SDK.

Makes <=4 calls total to validate connectivity and record metrics.

Usage (key holder only):
    python runtime/test_adaption_smoke.py
"""

import json
import os
import sys
from pathlib import Path

# Add runtime to path
sys.path.insert(0, str(Path(__file__).parent))


def run_smoke_test() -> dict:
    """
    Run smoke test with <=4 model calls.

    Returns:
        dict: Metrics and aggregate status. ``calls_made`` counts attempted
        adapter invocations, including failures, not SDK-internal requests.
    """
    results = []
    calls_made = 0

    # Check API key is available BEFORE importing SDK
    if not os.environ.get("ADAPTION_API_KEY"):
        return {
            "status": "blocked",
            "reason": "ADAPTION_API_KEY not set in environment",
            "calls_made": 0,
        }

    # Lazy imports: allows graceful degradation when SDK is unavailable
    # Only reached when API key is present
    # <=4 calls enforced in code; 256/night operational cap enforced by coordinator
    from adaption import AdaptionError
    from adaption_adapter import AdaptionAdapter

    adapter = AdaptionAdapter()

    # Call 1: Small model connectivity check
    try:
        calls_made += 1
        r1 = adapter.simple_prompt(
            model="gemma-4-26b-a4b-it",
            prompt="Reply with exactly one word: hello",
        )
        results.append(
            {
                "call": 1,
                "model": r1.model,
                "prompt": "Reply with exactly one word: hello",
                "output": r1.output_text,
                "latency_ms": round(r1.latency_ms, 2),
                "input_tokens": r1.usage.input_tokens,
                "output_tokens": r1.usage.output_tokens,
                "estimated_credits_consumed": getattr(
                    r1.raw_response, "estimated_credits_consumed", None
                ),
            }
        )
    except AdaptionError as e:
        return {
            "status": "error",
            "call": 1,
            "error": f"AdaptionError: {type(e).__name__}",
            "calls_made": calls_made,
        }

    # Call 2: Primary chat model (glm-53-flash)
    try:
        calls_made += 1
        r2 = adapter.simple_prompt(
            model="glm-53-flash",
            prompt="What is 2+2? Answer with just the number.",
        )
        results.append(
            {
                "call": 2,
                "model": r2.model,
                "prompt": "What is 2+2? Answer with just the number.",
                "output": r2.output_text,
                "latency_ms": round(r2.latency_ms, 2),
                "input_tokens": r2.usage.input_tokens,
                "output_tokens": r2.usage.output_tokens,
                "estimated_credits_consumed": getattr(
                    r2.raw_response, "estimated_credits_consumed", None
                ),
            }
        )
    except AdaptionError as e:
        results.append(
            {
                "call": 2,
                "model": "glm-53-flash",
                "error": f"AdaptionError: {type(e).__name__}",
            }
        )

    # Call 3: Repeat small model for consistency check
    try:
        calls_made += 1
        r3 = adapter.simple_prompt(
            model="gemma-4-26b-a4b-it",
            prompt="Say 'test' exactly once.",
        )
        results.append(
            {
                "call": 3,
                "model": r3.model,
                "prompt": "Say 'test' exactly once.",
                "output": r3.output_text,
                "latency_ms": round(r3.latency_ms, 2),
                "input_tokens": r3.usage.input_tokens,
                "output_tokens": r3.usage.output_tokens,
                "estimated_credits_consumed": getattr(
                    r3.raw_response, "estimated_credits_consumed", None
                ),
            }
        )
    except AdaptionError as e:
        results.append(
            {
                "call": 3,
                "model": "gemma-4-26b-a4b-it",
                "error": f"AdaptionError: {type(e).__name__}",
            }
        )

    # Call 4: Final validation
    try:
        calls_made += 1
        r4 = adapter.simple_prompt(
            model="gemma-4-26b-a4b-it",
            prompt="Output: OK",
        )
        results.append(
            {
                "call": 4,
                "model": r4.model,
                "prompt": "Output: OK",
                "output": r4.output_text,
                "latency_ms": round(r4.latency_ms, 2),
                "input_tokens": r4.usage.input_tokens,
                "output_tokens": r4.usage.output_tokens,
                "estimated_credits_consumed": getattr(
                    r4.raw_response, "estimated_credits_consumed", None
                ),
            }
        )
    except AdaptionError as e:
        results.append(
            {
                "call": 4,
                "model": "gemma-4-26b-a4b-it",
                "error": f"AdaptionError: {type(e).__name__}",
            }
        )

    failures = [row for row in results if "error" in row]
    outcome = {
        "status": "error" if failures else "success",
        "calls_made": calls_made,
        "results": results,
    }
    if failures:
        outcome.update(call=failures[0]["call"], error=failures[0]["error"])
    return outcome


if __name__ == "__main__":
    result = run_smoke_test()
    print(json.dumps(result, indent=2))

    if result["status"] == "blocked":
        print("\n⚠️  BLOCKED: ADAPTION_API_KEY not set", file=sys.stderr)
        sys.exit(2)
    elif result["status"] == "error":
        print(
            f"\n❌ ERROR on call {result.get('call', '?')}: {result.get('error')}",
            file=sys.stderr,
        )
        sys.exit(1)
    else:
        print(f"\n✅ Smoke test passed: {result['calls_made']} calls made")
        sys.exit(0)
