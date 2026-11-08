#!/usr/bin/env python3
"""
dataset_pack/dry_run.py — Offline dry-run test of the full packaging workflow

Creates a fake run with mock calls.jsonl, exercises:
- extract: artifact extraction from calls
- package: MANIFEST reconciliation, dataset card, records/runs tables
- tests: all provenance tests

No real model/API calls. Uses fixture data only.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from dataset_pack.audit import run_full_audit
from dataset_pack.extract import extract_artifacts
from dataset_pack.package import DatasetPackager
from dataset_pack.tests import run_all_tests


def create_fixture_run(run_dir: Path) -> dict:
    """
    Create a fixture run directory with mock data.

    Args:
        run_dir: Directory to create run in

    Returns:
        Dict with fixture metadata.
    """
    run_dir.mkdir(parents=True, exist_ok=True)

    # Create subdirectories
    logs_dir = run_dir / "logs"
    receipts_dir = run_dir / "receipts"
    artifacts_dir = run_dir / "artifacts"

    logs_dir.mkdir(exist_ok=True)
    receipts_dir.mkdir(exist_ok=True)
    artifacts_dir.mkdir(exist_ok=True)

    # Create mock calls.jsonl with full prompt+response
    calls = [
        {
            "ts": "2026-11-08T12:00:00Z",
            "run_id": "run-001",
            "call_id": "call-0001",
            "role": "pug-bot",
            "model": "glm-53-flash",
            "prompt_full": "You are pug-bot. Current state: Turn 1. What do you observe?",
            "response_full": "Observation: Agent colette is at depot A with 2 packages.",
            "tokens_in": 150,
            "tokens_out": 25,
            "receipt_ref": "receipt-run-001-0001",
            "provenance": "model-generated",
            "artifact": "pug-bot-t1d1",
        },
        {
            "ts": "2026-11-08T12:00:01Z",
            "run_id": "run-001",
            "call_id": "call-0002",
            "role": "colette",
            "model": "glm-53-flash",
            "prompt_full": "You are colette. You see 2 packages at depot A. What do you do?",
            "response_full": "Decision: Pick up package 1 and move toward depot B.",
            "tokens_in": 120,
            "tokens_out": 30,
            "receipt_ref": "receipt-run-001-0002",
            "provenance": "model-generated",
            "artifact": "colette-t1d2",
        },
        {
            "ts": "2026-11-08T12:00:02Z",
            "run_id": "run-001",
            "call_id": "call-0003",
            "role": "forge",
            "model": "glm-53-flash",
            "prompt_full": "You are forge. colette is moving package 1. What do you do?",
            "response_full": "Decision: Monitor colette's progress. Prepare to assist if needed.",
            "tokens_in": 130,
            "tokens_out": 28,
            "receipt_ref": "receipt-run-001-0003",
            "provenance": "model-generated",
            "artifact": "forge-t1d3",
        },
    ]

    calls_path = logs_dir / "calls.jsonl"
    with open(calls_path, "w", encoding="utf-8") as f:
        f.writelines(json.dumps(call, separators=(",", ":")) + "\n" for call in calls)

    # Create sealed event log (events.jsonl) - source of truth for turn + event_type
    events = []
    for i, call in enumerate(calls):
        event = {
            "ts": call["ts"],
            "run_id": call["run_id"],
            "turn": i,  # 0-indexed turn
            "type": "observation.recorded",
            "agent_id": call["role"],
            "payload": {
                "prompt": call["prompt_full"],
                "response": call["response_full"],
            },
        }
        events.append(event)

    events_path = logs_dir / "events.jsonl"
    with open(events_path, "w", encoding="utf-8") as f:
        f.writelines(json.dumps(event, separators=(",", ":")) + "\n" for event in events)

    # Create mock receipts
    for call in calls:
        receipt = {
            "call_id": call["call_id"],
            "tokens_in": call["tokens_in"],
            "tokens_out": call["tokens_out"],
            "model": call["model"],
        }
        receipt_path = receipts_dir / f"{call['receipt_ref']}.json"
        with open(receipt_path, "w", encoding="utf-8") as f:
            json.dump(receipt, f, indent=2)

    # Create mock artifacts (content should match response)
    for call in calls:
        if call.get("artifact"):
            artifact_path = artifacts_dir / f"{call['artifact']}.txt"
            with open(artifact_path, "w", encoding="utf-8") as f:
                f.write(call["response_full"])

    # Create run.json
    run_json = {
        "run_id": "run-001",
        "instance_id": "task-inst-001",
        "config_hash": "abc123def456",
        "seed": 42,
        "topology": "mesh",
        "turns": 1,
        "calls_count": len(calls),
        "status": "completed",
    }
    with open(run_dir / "run.json", "w", encoding="utf-8") as f:
        json.dump(run_json, f, indent=2)

    return {
        "run_id": "run-001",
        "calls": len(calls),
        "artifacts": len([c for c in calls if c.get("artifact")]),
        "receipts": len(calls),
    }


def run_dry_run() -> dict:
    """
    Run the full offline dry-run workflow.

    Returns:
        Dict with dry-run results.
    """
    # Create temporary directories
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        base_dir = tmp_path / "runs"
        output_dir = tmp_path / "pack"

        base_dir.mkdir(exist_ok=True)
        output_dir.mkdir(exist_ok=True)

        # Create fixture run
        run_dir = base_dir / "run-001"
        fixture_meta = create_fixture_run(run_dir)

        print(f"Created fixture run: {fixture_meta}")

        # Extract artifacts (task 4)
        logs_dir = run_dir / "logs"
        artifacts_dir = run_dir / "artifacts"
        extract_result = extract_artifacts(
            str(logs_dir / "calls.jsonl"), str(artifacts_dir)
        )
        print(f"Extraction: {extract_result['artifacts_extracted']} artifacts")

        # Package dataset (task 5)
        packager = DatasetPackager(
            str(base_dir), str(output_dir), "/workspace/swarmachines"
        )
        package_result = packager.package_all()

        print("Packaging complete:")
        print(f"  Manifest: {package_result['manifest_path']}")
        print(f"  Card: {package_result['card_path']}")
        print(
            f"  Records: {package_result['records_path']} ({package_result['event_records']} events)"
        )
        print(
            f"  Runs: {package_result['runs_path']} ({package_result['run_summaries']} runs)"
        )
        print(
            f"  No split: {'PASSED' if package_result['no_split_check']['passed'] else 'FAILED'}"
        )
        print(
            f"  No API key: {'PASSED' if package_result['no_key_check']['passed'] else 'FAILED'}"
        )

        # Run tests (task 8) - B9: test against BOTH fixture runs dir AND produced pack
        # Test against the fixture runs (base_dir)
        print("\n--- Testing fixture runs (base_dir) ---")
        test_results_fixture = run_all_tests(
            str(base_dir),  # Fixture runs dir
            package_result["manifest_path"],
            package_result["card_path"],
            package_result["records_path"],
        )

        # Test against the produced pack (output_dir/data/runs)
        print("\n--- Testing produced pack (output_dir/data/runs) ---")
        pack_runs_dir = str(output_dir / "data" / "runs")
        test_results_pack = run_all_tests(
            pack_runs_dir,  # Produced pack runs dir
            package_result["manifest_path"],
            package_result["card_path"],
            package_result["records_path"],
        )

        # Audit gate (defect 6 fix): Run six-step audit on the produced pack
        print("\n--- Running six-step audit gate ---")
        audit_result = run_full_audit(
            pack_runs_dir,
            package_result["manifest_path"],
        )
        print(f"Audit Verdict: {audit_result['verdict']}")
        print(
            f"Steps Passed: {audit_result['passed_steps']}/{audit_result['total_steps']}"
        )
        for step in audit_result["steps"]:
            status = "✓" if step["passed"] else "✗"
            print(f"  {status} {step['step']}: {step.get('error_count', 0)} errors")

        # Combine results
        all_passed = (
            test_results_fixture["all_passed"]
            and test_results_pack["all_passed"]
            and audit_result["gate_passed"]
        )

        print(
            f"\nFixture Tests: {test_results_fixture['tests_passed']}/{test_results_fixture['tests_run']} passed"
        )
        for test in test_results_fixture["results"]:
            status = "✓" if test["passed"] else "✗"
            print(f"  {status} {test['test']}")

        print(
            f"\nPack Tests: {test_results_pack['tests_passed']}/{test_results_pack['tests_run']} passed"
        )
        for test in test_results_pack["results"]:
            status = "✓" if test["passed"] else "✗"
            print(f"  {status} {test['test']}")

        return {
            "fixture_meta": fixture_meta,
            "extract_result": extract_result,
            "package_result": package_result,
            "test_results_fixture": test_results_fixture,
            "test_results_pack": test_results_pack,
            "all_passed": all_passed,
        }


if __name__ == "__main__":
    import sys

    print("Running offline dry-run of dataset_pack workflow...")
    print("=" * 60)

    try:
        result = run_dry_run()

        print("=" * 60)
        if result["all_passed"]:
            print("✓ Dry-run PASSED — all tests green")
            sys.exit(0)
        else:
            print("✗ Dry-run FAILED — some tests failed")
            sys.exit(1)

    except (RuntimeError, OSError, json.JSONDecodeError) as e:
        print(f"Dry-run failed with exception: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)
