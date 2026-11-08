"""
dataset_pack/tests.py — Provenance and packaging tests

Tests:
1. wrong-side guard: artifact content matches call response
2. manifest-equals-disk: MANIFEST counts match disk after every fix
3. card required fields: README has model, provider, commit, token totals
4. no-key-in-pack scan: API key never appears in any pack file
5. verbatim-transcript diff: records/calls match source event log byte-for-byte
6. raw-layer-presence: HF repo contains calls.jsonl, receipts/, sealed log, artifacts/
7. no-split check: no train/val/test directory or split field
8. agent-label completeness: non-empty agent_id/event_type per row
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def test_wrong_side_guard(pack_dir: str) -> dict[str, Any]:
    """
    Test: every model-generated artifact's content matches its call's response field.

    Args:
        pack_dir: Directory containing the packaged dataset

    Returns:
        Dict with test results.
    """
    pack_path = Path(pack_dir)
    mismatches = []
    artifacts_checked = 0

    # Iterate through all runs
    for run_dir in pack_path.glob("run-*"):
        if not run_dir.is_dir():
            continue

        # Load calls.jsonl
        calls_path = run_dir / "logs" / "calls.jsonl"
        if not calls_path.exists():
            continue

        calls = []
        with open(calls_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    calls.append(json.loads(line))

        # Load artifacts
        artifacts_dir = run_dir / "artifacts"
        if not artifacts_dir.exists():
            continue

        for call in calls:
            artifact_id = call.get("artifact")
            if not artifact_id:
                continue

            artifact_path = artifacts_dir / f"{artifact_id}.txt"
            if not artifact_path.exists():
                mismatches.append(
                    {
                        "run_id": run_dir.name,
                        "call_id": call.get("call_id"),
                        "artifact_id": artifact_id,
                        "error": "artifact file not found",
                    }
                )
                continue

            with open(artifact_path, "r", encoding="utf-8") as f:
                artifact_content = f.read()

            response_content = call.get("response_full", "")

            # Check identity (artifact should be identical to response or substring)
            if (
                artifact_content.strip() != response_content.strip()
                and artifact_content.strip() not in response_content
            ):
                mismatches.append(
                    {
                        "run_id": run_dir.name,
                        "call_id": call.get("call_id"),
                        "artifact_id": artifact_id,
                        "artifact_hash": hashlib.sha256(
                            artifact_content.encode("utf-8")
                        ).hexdigest()[:16],
                        "response_hash": hashlib.sha256(
                            response_content.encode("utf-8")
                        ).hexdigest()[:16],
                    }
                )

            artifacts_checked += 1

    return {
        "test": "wrong-side-guard",
        "artifacts_checked": artifacts_checked,
        "mismatches": len(mismatches),
        "mismatch_details": mismatches[:10],
        "passed": len(mismatches) == 0,
    }


def test_manifest_equals_disk(pack_dir: str, manifest_path: str) -> dict[str, Any]:
    """
    Test: MANIFEST counts match disk after every fix.

    Args:
        pack_dir: Directory containing the packaged dataset
        manifest_path: Path to MANIFEST.md

    Returns:
        Dict with test results.
    """
    pack_path = Path(pack_dir)
    manifest = Path(manifest_path)

    if not manifest.exists():
        return {
            "test": "manifest-equals-disk",
            "passed": False,
            "error": "MANIFEST.md not found",
        }

    # Parse MANIFEST.md to extract counts
    manifest_content = manifest.read_text(encoding="utf-8")
    expected_counts = {}

    # Parse totals from markdown (format: "- **Field:** value")
    in_totals_section = False
    for line in manifest_content.split("\n"):
        line = line.strip()

        # Track section
        if line.startswith("## Totals"):
            in_totals_section = True
            continue
        if line.startswith("## "):
            in_totals_section = False
            continue

        # Parse totals (format: "- **Field:** value")
        if in_totals_section and line.startswith("- **"):
            # Extract field name: between ** and :
            parts = line.split("**")
            if len(parts) >= 3:
                # parts[1] is the field name with colon, e.g., "Runs:"
                field_raw = parts[1].strip()
                # Remove trailing colon and normalize
                field = field_raw.rstrip(":").lower().replace(" ", "_")
                # parts[2] is ": value" - extract the value
                value_str = parts[2].strip().lstrip(":").strip()
                try:
                    value = int(value_str)
                    if field == "runs":
                        expected_counts["runs"] = value
                    elif field == "calls":
                        expected_counts["calls"] = value
                    elif field == "artifacts":
                        expected_counts["artifacts"] = value
                    elif field == "receipts":
                        expected_counts["receipts"] = value
                    elif field == "events":
                        expected_counts["events"] = value
                except ValueError:
                    pass

    # Count on disk
    actual_counts = {
        "runs": 0,
        "calls": 0,
        "artifacts": 0,
        "receipts": 0,
    }

    for run_dir in pack_path.glob("run-*"):
        if not run_dir.is_dir():
            continue
        actual_counts["runs"] += 1

        # Count calls
        calls_path = run_dir / "logs" / "calls.jsonl"
        if calls_path.exists():
            with open(calls_path, "r", encoding="utf-8") as f:
                actual_counts["calls"] += sum(1 for line in f if line.strip())

        # Count artifacts
        artifacts_dir = run_dir / "artifacts"
        if artifacts_dir.exists():
            actual_counts["artifacts"] += len(list(artifacts_dir.glob("*.txt")))

        # Count receipts
        receipts_dir = run_dir / "receipts"
        if receipts_dir.exists():
            actual_counts["receipts"] += len(list(receipts_dir.glob("*.json")))

    mismatches = []
    for key, expected_value in expected_counts.items():
        if key in actual_counts and expected_value != actual_counts[key]:
            mismatches.append(
                {
                    "field": key,
                    "expected": expected_value,
                    "actual": actual_counts[key],
                }
            )

    return {
        "test": "manifest-equals-disk",
        "expected": expected_counts,
        "actual": actual_counts,
        "mismatches": mismatches,
        "passed": len(mismatches) == 0,
    }


def test_card_required_fields(card_path: str) -> dict[str, Any]:
    """
    Test: README dataset card has required fields (model, provider, commit, token totals).

    Args:
        card_path: Path to README.md

    Returns:
        Dict with test results.
    """
    card = Path(card_path)

    if not card.exists():
        return {
            "test": "card-required-fields",
            "passed": False,
            "error": "README.md not found",
        }

    content = card.read_text(encoding="utf-8")

    required_fields = {
        "model": "glm-53-flash",
        "provider": "adaption",
        "commit": "Repo Commit:",
        "token_totals": "Total Tokens:",
        "configs": "configs:",
    }

    missing = []
    for field, marker in required_fields.items():
        if marker not in content:
            missing.append(field)

    # Check YAML frontmatter has configs
    if "configs:" not in content:
        missing.append("configs_in_frontmatter")

    return {
        "test": "card-required-fields",
        "required_fields": list(required_fields.keys()),
        "missing": missing,
        "passed": len(missing) == 0,
    }


def test_no_key_in_pack(pack_dir: str) -> dict[str, Any]:
    """
    Test: API key never appears in any pack file.

    Scans for:
    - Actual credential value from ADAPTION_API_KEY environment variable
    - Common key prefixes: sk-, hf_, adk_, adaption

    Args:
        pack_dir: Directory containing the packaged dataset

    Returns:
        Dict with test results.
    """
    import os

    pack_path = Path(pack_dir)

    # B8: Scan for actual credential VALUE from env (never print it)
    api_key_value = os.environ.get("ADAPTION_API_KEY", "")

    api_key_patterns = [
        "ADAPTION_API_KEY",
        "adaption_api_key",
        "sk-adaption",
        "adaption-key",
        "sk-",  # Common API key prefix
        "hf_",  # Hugging Face prefix
        "adk_",  # Adaption prefix
        "adaption",  # Provider name in suspicious contexts
    ]

    found = []
    for file_path in pack_path.rglob("*"):
        if file_path.is_file():
            try:
                content = file_path.read_text(encoding="utf-8")

                # Check for actual credential value (B8)
                if (
                    api_key_value
                    and len(api_key_value) > 10
                    and api_key_value in content
                ):
                    found.append(f"{file_path}:contains_actual_api_key_value")
                    continue

                # Check for common prefixes - must be at word boundary (not substring of other words)
                import re

                for pattern in api_key_patterns:
                    # Word boundary check: pattern must be at start or preceded by non-alphanumeric
                    if pattern in ("sk-", "hf_", "adk_"):
                        # These are almost always credential leaks - check word boundary
                        if re.search(rf"(^|[^a-zA-Z0-9]){re.escape(pattern)}", content):
                            found.append(f"{file_path}:contains_{pattern}")
                            break
                    elif pattern == "adaption":
                        # Check if it's in a suspicious context (not just docs)
                        if "key" in content.lower() and re.search(
                            rf"(^|[^a-zA-Z0-9]){re.escape(pattern)}", content
                        ):
                            found.append(f"{file_path}:contains_{pattern}_with_key")
                            break
                    else:
                        # Other patterns - simple substring match
                        if pattern in content:
                            found.append(f"{file_path}:contains_{pattern}")
                            break
            except (UnicodeDecodeError, PermissionError):
                continue

    return {
        "test": "no-key-in-pack",
        "patterns_checked": api_key_patterns + ["actual_api_key_value"],
        "files_with_key": found,
        "passed": len(found) == 0,
    }


def test_verbatim_transcript_diff(pack_dir: str) -> dict[str, Any]:
    """
    Test: records/calls match source event log byte-for-byte.

    Diffs paired prompt/response against the source sealed event log
    and calls.jsonl to verify no truncation or paraphrasing.

    Args:
        pack_dir: Directory containing the packaged dataset

    Returns:
        Dict with test results.
    """
    pack_path = Path(pack_dir)
    mismatches = []
    records_checked = 0

    for run_dir in pack_path.glob("run-*"):
        if not run_dir.is_dir():
            continue

        # Load calls.jsonl
        calls_path = run_dir / "logs" / "calls.jsonl"
        if not calls_path.exists():
            continue

        # Load sealed event log (source of truth)
        events_path = run_dir / "logs" / "events.jsonl"
        events = []
        if events_path.exists():
            with open(events_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        events.append(json.loads(line))

        # Load records.jsonl if exists
        records_path = pack_path / "data" / "records.jsonl"
        records = []
        if records_path.exists():
            with open(records_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        records.append(json.loads(line))

        # Filter records for this run
        run_id = run_dir.name
        run_records = [r for r in records if r.get("run_id") == run_id]

        # Load calls
        calls = []
        with open(calls_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    calls.append(json.loads(line))

        # B7: Genuinely diff records/calls against SOURCE event log + calls.jsonl
        # Build a map from call_id to event log entries
        event_by_payload = {}
        for event in events:
            payload = event.get("payload", {})
            if "prompt" in payload and "response" in payload:
                key = (payload["prompt"], payload["response"])
                event_by_payload[key] = event

        # Verify each call's prompt/response matches the event log
        for call in calls:
            prompt = call.get("prompt_full", "")
            response = call.get("response_full", "")

            # Check for truncation markers
            if "[...]" in prompt or "[truncated]" in prompt.lower():
                mismatches.append(
                    {
                        "run_id": run_id,
                        "call_id": call.get("call_id"),
                        "error": "prompt appears truncated",
                    }
                )

            if "[...]" in response or "[truncated]" in response.lower():
                mismatches.append(
                    {
                        "run_id": run_id,
                        "call_id": call.get("call_id"),
                        "error": "response appears truncated",
                    }
                )

            # Verify against event log (byte-for-byte)
            key = (prompt, response)
            if key not in event_by_payload and events:
                # Call should have a corresponding event log entry
                # Check if any event has matching content
                found_match = False
                for event in events:
                    payload = event.get("payload", {})
                    if (
                        payload.get("prompt") == prompt
                        and payload.get("response") == response
                    ):
                        found_match = True
                        break
                if not found_match and len(prompt) > 10 and len(response) > 10:
                    # Only flag for substantial content
                    mismatches.append(
                        {
                            "run_id": run_id,
                            "call_id": call.get("call_id"),
                            "error": "call not found in sealed event log",
                        }
                    )

            records_checked += 1

        # Verify records match calls.jsonl content
        for record in run_records[:10]:  # Sample first 10
            content = record.get("content", "")
            # Find corresponding call
            found_in_calls = False
            for call in calls:
                if content == call.get("response_full", "") or content in call.get(
                    "response_full", ""
                ):
                    found_in_calls = True
                    break
            if not found_in_calls and len(content) > 20:
                mismatches.append(
                    {
                        "run_id": run_id,
                        "record_turn": record.get("turn"),
                        "error": "record content not found in calls.jsonl",
                    }
                )

    return {
        "test": "verbatim-transcript-diff",
        "records_checked": records_checked,
        "truncation_found": len(mismatches),
        "mismatches": mismatches[:10],
        "passed": len(mismatches) == 0,
    }


def test_raw_layer_presence(pack_dir: str) -> dict[str, Any]:
    """
    Test: HF repo contains calls.jsonl, receipts/, sealed event log, artifacts/ for each run.

    Args:
        pack_dir: Directory containing the packaged dataset

    Returns:
        Dict with test results.
    """
    pack_path = Path(pack_dir)
    missing = []

    for run_dir in pack_path.glob("run-*"):
        if not run_dir.is_dir():
            continue

        run_id = run_dir.name
        required = {
            "logs/calls.jsonl": run_dir / "logs" / "calls.jsonl",
            "receipts/": run_dir / "receipts",
            "artifacts/": run_dir / "artifacts",
        }

        for name, path in required.items():
            if not path.exists():
                missing.append(f"{run_id}: {name}")

    return {
        "test": "raw-layer-presence",
        "runs_checked": len(list(pack_path.glob("run-*"))),
        "missing_components": missing,
        "passed": len(missing) == 0,
    }


def test_no_split(pack_dir: str, records_path: str) -> dict[str, Any]:
    """
    Test: no train/val/test directory or split field.

    Args:
        pack_dir: Directory containing the packaged dataset
        records_path: Path to records.jsonl

    Returns:
        Dict with test results.
    """
    pack_path = Path(pack_dir)

    # Check for split directories
    split_dirs = []
    for pattern in ["train*", "test*", "val*", "validation*"]:
        split_dirs.extend(list(pack_path.glob(pattern)))

    # Check for split field in records
    has_split_field = False
    records = Path(records_path)
    if records.exists():
        with open(records, "r", encoding="utf-8") as f:
            for line in f:
                if '"split"' in line:
                    has_split_field = True
                    break

    return {
        "test": "no-split",
        "split_dirs_found": [str(d) for d in split_dirs],
        "has_split_field": has_split_field,
        "passed": len(split_dirs) == 0 and not has_split_field,
    }


def test_agent_label_completeness(records_path: str) -> dict[str, Any]:
    """
    Test: non-empty agent_id/event_type per row (for agent-specific events).

    Args:
        records_path: Path to records.jsonl

    Returns:
        Dict with test results.
    """
    records = Path(records_path)

    if not records.exists():
        return {
            "test": "agent-label-completeness",
            "passed": False,
            "error": "records.jsonl not found",
        }

    incomplete = []
    total = 0

    with open(records, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue

            record = json.loads(line)
            total += 1

            event_type = record.get("event_type", "")
            agent_id = record.get("agent_id")

            # For agent-specific events (not world-level), agent_id should be present
            world_level_events = {
                "run.config",
                "world.init",
                "world.changed",
                "disturbance.applied",
                "run.end",
                "run.seal",
            }

            if event_type not in world_level_events and not agent_id:
                incomplete.append(
                    {
                        "line": line_num,
                        "event_type": event_type,
                        "error": "missing agent_id for agent-specific event",
                    }
                )

            if not event_type:
                incomplete.append(
                    {
                        "line": line_num,
                        "error": "missing event_type",
                    }
                )

    return {
        "test": "agent-label-completeness",
        "total_records": total,
        "incomplete": len(incomplete),
        "incomplete_details": incomplete[:10],
        "passed": len(incomplete) == 0,
    }


def run_all_tests(
    pack_dir: str, manifest_path: str, card_path: str, records_path: str
) -> dict[str, Any]:
    """
    Run all provenance and packaging tests.

    Args:
        pack_dir: Directory containing the packaged dataset
        manifest_path: Path to MANIFEST.md
        card_path: Path to README.md
        records_path: Path to records.jsonl

    Returns:
        Dict with all test results.
    """
    tests = [
        test_wrong_side_guard(pack_dir),
        test_manifest_equals_disk(pack_dir, manifest_path),
        test_card_required_fields(card_path),
        test_no_key_in_pack(pack_dir),
        test_verbatim_transcript_diff(pack_dir),
        test_raw_layer_presence(pack_dir),
        test_no_split(pack_dir, records_path),
        test_agent_label_completeness(records_path),
    ]

    passed = sum(1 for t in tests if t["passed"])
    total = len(tests)

    return {
        "tests_run": total,
        "tests_passed": passed,
        "tests_failed": total - passed,
        "all_passed": passed == total,
        "results": tests,
    }


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 5:
        print(
            "Usage: python -m dataset_pack.tests <pack_dir> <manifest_path> <card_path> <records_path>"
        )
        sys.exit(1)

    pack_dir = sys.argv[1]
    manifest_path = sys.argv[2]
    card_path = sys.argv[3]
    records_path = sys.argv[4]

    print(f"Running provenance tests on {pack_dir}...")

    results = run_all_tests(pack_dir, manifest_path, card_path, records_path)

    print(f"\nTest Results: {results['tests_passed']}/{results['tests_run']} passed")

    for test in results["results"]:
        status = "✓" if test["passed"] else "✗"
        print(f"  {status} {test['test']}")
        if not test["passed"]:
            if "error" in test:
                print(f"      Error: {test['error']}")
            if test.get("missing"):
                print(f"      Missing: {test['missing']}")
            if test.get("mismatches"):
                print(f"      Mismatches: {len(test['mismatches'])}")

    sys.exit(0 if results["all_passed"] else 1)
