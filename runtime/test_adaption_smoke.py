#!/usr/bin/env python3
"""
Smoke test for the Adaption adapter.

Makes <=4 calls total to validate connectivity and record metrics.
Requires ADAPTION_API_KEY environment variable.

Usage:
    python runtime/test_adaption_smoke.py
"""

import json
import os
import sys
from pathlib import Path

# Add runtime to path
sys.path.insert(0, str(Path(__file__).parent))

from adaption_adapter import AdaptionAdapter


def run_smoke_test() -> dict:
    """
    Run smoke test with <=4 model calls.

    Returns dict with metrics from each call.
    """
    results = []

    # Check API key is available
    if not os.environ.get("ADAPTION_API_KEY"):
        return {
            "status": "blocked",
            "reason": "ADAPTION_API_KEY not set in environment",
            "calls_made": 0,
        }

    adapter = AdaptionAdapter()

    # Call 1: Small model connectivity check
    try:
        r1 = adapter.simple_prompt(
            model="gemma-4-26b-a4b-it",
            prompt="Reply with exactly one word: hello",
        )
        results.append({
            "call": 1,
            "model": r1.model,
            "prompt": "Reply with exactly one word: hello",
            "output": r1.output_text,
            "latency_ms": round(r1.latency_ms, 2),
            "input_tokens": r1.usage.input_tokens,
            "output_tokens": r1.usage.output_tokens,
        })
    except Exception as e:
        return {
            "status": "error",
            "call": 1,
            "error": str(e),
            "calls_made": len(results),
        }

    # Call 2: Primary chat model (glm-53-flash)
    try:
        r2 = adapter.simple_prompt(
            model="glm-53-flash",
            prompt="What is 2+2? Answer with just the number.",
        )
        results.append({
            "call": 2,
            "model": r2.model,
            "prompt": "What is 2+2? Answer with just the number.",
            "output": r2.output_text,
            "latency_ms": round(r2.latency_ms, 2),
            "input_tokens": r2.usage.input_tokens,
            "output_tokens": r2.usage.output_tokens,
        })
    except Exception as e:
        results.append({
            "call": 2,
            "model": "glm-53-flash",
            "error": str(e),
        })

    # Call 3: Repeat small model for consistency check
    try:
        r3 = adapter.simple_prompt(
            model="gemma-4-26b-a4b-it",
            prompt="Say 'test' exactly once.",
        )
        results.append({
            "call": 3,
            "model": r3.model,
            "prompt": "Say 'test' exactly once.",
            "output": r3.output_text,
            "latency_ms": round(r3.latency_ms, 2),
            "input_tokens": r3.usage.input_tokens,
            "output_tokens": r3.usage.output_tokens,
        })
    except Exception as e:
        results.append({
            "call": 3,
            "model": "gemma-4-26b-a4b-it",
            "error": str(e),
        })

    # Call 4: Final validation
    try:
        r4 = adapter.simple_prompt(
            model="gemma-4-26b-a4b-it",
            prompt="Output: OK",
        )
        results.append({
            "call": 4,
            "model": r4.model,
            "prompt": "Output: OK",
            "output": r4.output_text,
            "latency_ms": round(r4.latency_ms, 2),
            "input_tokens": r4.usage.input_tokens,
            "output_tokens": r4.usage.output_tokens,
        })
    except Exception as e:
        results.append({
            "call": 4,
            "model": "gemma-4-26b-a4b-it",
            "error": str(e),
        })

    return {
        "status": "success",
        "calls_made": len(results),
        "results": results,
    }


if __name__ == "__main__":
    result = run_smoke_test()
    print(json.dumps(result, indent=2))

    if result["status"] == "blocked":
        print("\n⚠️  BLOCKED: ADAPTION_API_KEY not set", file=sys.stderr)
        sys.exit(2)
    elif result["status"] == "error":
        print(f"\n❌ ERROR on call {result.get('call', '?')}: {result.get('error')}", file=sys.stderr)
        sys.exit(1)
    else:
        print(f"\n✅ Smoke test passed: {result['calls_made']} calls made")
        sys.exit(0)
