"""one-drop task-10 coordinator for the governed fifteen-instance batch."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from runtime.runner import TurnSeamRunner, verify_seal
from runtime.tracer import TraceConfig, Tracer

from .budget import CreditBudget
from .configs import TaskInstanceConfig, get_task_configs, validate_configs
from .package import package_dataset
from .run import run_governed_run

CONFIRMATION = "task10-15-one-drop"
TASK_CEILING = Decimal(10)


def planned_call_count(configs: list[TaskInstanceConfig]) -> int:
    """return the exact upper bound for observation + decision captures."""
    return sum(len(config.agent_roster) * config.turns * 2 for config in configs)


def verify_matrix_offline(configs: list[TaskInstanceConfig]) -> dict[str, Any]:
    """exercise every declared world without constructing a provider adapter."""
    errors = validate_configs(configs)
    if errors:
        raise ValueError("invalid task matrix: " + "; ".join(errors))

    evidence = []
    for config in configs:
        runner = TurnSeamRunner(**config.to_runner_args())
        runner.run(config.turns)
        verify_seal(runner.log.events)
        initialized = next(
            event["payload"]["jobs"]
            for event in runner.log.events
            if event["type"] == "jobs.initialized"
        )
        actual_jobs = [
            (job["freight_id"], job["origin"], job["destination"])
            for job in initialized
        ]
        declared_jobs = [
            (job["freight_id"], job["origin"], job["destination"])
            for job in config.job_set
        ]
        if actual_jobs != declared_jobs:
            raise ValueError(f"runtime job mismatch for {config.instance_id}")
        evidence.append(
            {
                "instance_id": config.instance_id,
                "config_hash": config.config_hash(),
                "events": len(runner.log.events),
            }
        )
    return {"instances": evidence, "all_passed": True}


def preflight(
    ceiling_credits: str = "10",
    *,
    langfuse_credentials: Path | None = None,
) -> dict[str, Any]:
    """return provider-free proof for the exact task-10 matrix and envelope."""
    ceiling = Decimal(ceiling_credits)
    if ceiling > TASK_CEILING:
        raise ValueError("task-10 credit ceiling cannot exceed 10")
    configs = get_task_configs()
    planned_calls = planned_call_count(configs)
    budget = CreditBudget(format(ceiling, "f"), max_calls=planned_calls)
    return {
        "matrix": verify_matrix_offline(configs),
        "budget": budget.preflight(planned_calls),
        "adaption_credential_configured": bool(os.environ.get("ADAPTION_API_KEY")),
        "langfuse_credential_path_supplied": langfuse_credentials is not None,
        "provider_calls": 0,
    }


def _repo_commit(repo: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _require_clean_generation_commit(repo: Path) -> None:
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    if status:
        raise RuntimeError("live generation requires a clean committed worktree")


def _require_new_directory(path: Path) -> None:
    if path.exists():
        raise FileExistsError(f"one-drop output already exists: {path}")


def _write_receipt(path: Path, receipt: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def execute_batch(
    *,
    runs_dir: Path,
    pack_dir: Path,
    repo: Path,
    ceiling_credits: str,
    confirmation: str,
    langfuse_credentials: Path,
) -> dict[str, Any]:
    """execute the authorized one-drop batch and package it without uploading."""
    if confirmation != CONFIRMATION:
        raise ValueError(f"live execution requires --confirm {CONFIRMATION}")
    if not os.environ.get("ADAPTION_API_KEY"):
        raise RuntimeError("ADAPTION_API_KEY is not configured")
    _require_clean_generation_commit(repo)
    _require_new_directory(runs_dir)
    _require_new_directory(pack_dir)

    proof = preflight(
        ceiling_credits,
        langfuse_credentials=langfuse_credentials,
    )
    configs = get_task_configs()
    planned_calls = planned_call_count(configs)
    budget = CreditBudget(ceiling_credits, max_calls=planned_calls)
    generation_commit = _repo_commit(repo)
    trace_config = TraceConfig.from_file(
        langfuse_credentials,
        release=generation_commit,
        strict=True,
    )
    tracer = Tracer(trace_config)
    receipt_path = runs_dir / "BATCH-RECEIPT.json"
    receipt: dict[str, Any] = {
        "schema": "task10-batch-receipt-v1",
        "status": "running",
        "started_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "generation_commit": generation_commit,
        "planned_instances": [config.instance_id for config in configs],
        "completed_instances": [],
        "budget": budget.summary(),
        "preflight": proof,
    }
    _write_receipt(receipt_path, receipt)

    try:
        for config in configs:
            result = run_governed_run(
                config,
                str(runs_dir),
                dry_run=False,
                budget=budget,
                tracer=tracer,
            )
            receipt["completed_instances"].append(
                {
                    "instance_id": config.instance_id,
                    "run_id": result["run_id"],
                    "calls": result["calls_written"],
                    "artifacts": result["extraction"]["artifacts_extracted"],
                }
            )
            receipt["budget"] = budget.summary()
            _write_receipt(receipt_path, receipt)

        package = package_dataset(str(runs_dir), str(pack_dir), str(repo))
        receipt.update(
            status="completed",
            completed_at=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            budget=budget.summary(),
            package={
                "manifest_path": package["manifest_path"],
                "runs": package["run_summaries"],
                "raw_runs": package["raw_runs_shipped"],
                "no_split_passed": package["no_split_check"]["passed"],
                "no_key_passed": package["no_key_check"]["passed"],
            },
        )
        _write_receipt(receipt_path, receipt)
        return receipt
    except BaseException as error:
        receipt.update(
            status="failed",
            stopped_at=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            failure_type=type(error).__name__,
            budget=budget.summary(),
        )
        _write_receipt(receipt_path, receipt)
        raise
    finally:
        tracer.flush()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--credit-ceiling", default="10")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--confirm")
    parser.add_argument("--runs-dir", type=Path)
    parser.add_argument("--pack-dir", type=Path)
    parser.add_argument("--langfuse-credentials", type=Path)
    args = parser.parse_args()

    if not args.live:
        print(json.dumps(preflight(args.credit_ceiling), indent=2))
        return 0
    if (
        args.runs_dir is None
        or args.pack_dir is None
        or args.langfuse_credentials is None
    ):
        parser.error(
            "--live requires --runs-dir, --pack-dir, and --langfuse-credentials"
        )

    receipt = execute_batch(
        runs_dir=args.runs_dir.resolve(),
        pack_dir=args.pack_dir.resolve(),
        repo=Path.cwd().resolve(),
        ceiling_credits=args.credit_ceiling,
        confirmation=args.confirm or "",
        langfuse_credentials=args.langfuse_credentials,
    )
    print(json.dumps(receipt, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
