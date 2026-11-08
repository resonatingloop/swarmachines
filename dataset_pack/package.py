"""
dataset_pack/package.py — MANIFEST reconciliation and HF dataset card generation

Produces:
- MANIFEST: Top-level manifest reconciled against disk (counts must match exactly)
- README.md: HF-ready dataset card with yaml frontmatter (configs, license, tags, provenance)
- data/records.jsonl: One record per EVENT with explicit agent labels
- data/runs.jsonl: One summary record per task-run

Provenance requirements:
- MANIFEST counts must equal disk after every fix
- Dataset card names model (glm-53-flash), provider (adaption), commit, token totals
- All model-generated content marked as such
- NO train/test/validation split — this is a swarm dataset, not training corpus
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass
class EventRecord:
    """
    A record for data/records.jsonl representing one event.

    Fields derived from runtime/schema/events.schema.json:
    - run_id, task_id, seed, topology, turn, agent_id, agent_role, event_type
    - content (full text), model, tokens_in, tokens_out, receipt_ref, provenance
    """

    run_id: str
    task_id: str
    seed: int
    topology: str
    turn: int
    agent_id: str | None
    agent_role: str | None
    event_type: str
    content: str
    model: str | None = None
    tokens_in: int | None = None
    tokens_out: int | None = None
    receipt_ref: str | None = None
    provenance: str = "model-generated"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "run_id": self.run_id,
            "task_id": self.task_id,
            "seed": self.seed,
            "topology": self.topology,
            "turn": self.turn,
            "agent_id": self.agent_id,
            "agent_role": self.agent_role,
            "event_type": self.event_type,
            "content": self.content,
            "model": self.model,
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "receipt_ref": self.receipt_ref,
            "provenance": self.provenance,
        }

    def to_jsonl_line(self) -> str:
        """Serialize to JSONL line."""
        return json.dumps(self.to_dict(), separators=(",", ":"), ensure_ascii=False)


@dataclass
class RunSummary:
    """
    A summary record for data/runs.jsonl representing one task-run.

    Attributes:
        run_id: Run identifier
        task_id: Task instance ID
        config_hash: Hash of task configuration
        seed: Random seed
        topology: Communication topology
        turns: Number of turns executed
        total_events: Total event count
        total_calls: Total model call count
        total_tokens: Total token count
        outcome_metrics: Outcome metrics (deliveries, completion status)
        artifact_index: Index of artifacts for this run
        provenance_summary: Provenance label counts
    """

    run_id: str
    task_id: str
    config_hash: str
    seed: int
    topology: str
    turns: int
    total_events: int
    total_calls: int
    total_tokens: int
    outcome_metrics: dict[str, Any]
    artifact_index: dict[str, Any]
    provenance_summary: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "run_id": self.run_id,
            "task_id": self.task_id,
            "config_hash": self.config_hash,
            "seed": self.seed,
            "topology": self.topology,
            "turns": self.turns,
            "total_events": self.total_events,
            "total_calls": self.total_calls,
            "total_tokens": self.total_tokens,
            "outcome_metrics": self.outcome_metrics,
            "artifact_index": self.artifact_index,
            "provenance_summary": self.provenance_summary,
        }

    def to_jsonl_line(self) -> str:
        """Serialize to JSONL line."""
        return json.dumps(self.to_dict(), separators=(",", ":"), ensure_ascii=False)


class DatasetPackager:
    """
    Packages run data into HF-ready dataset format.

    Attributes:
        base_dir: Base directory containing all runs
        output_dir: Output directory for packaged data
        repo_path: Path to git repo for commit hash
    """

    def __init__(
        self,
        base_dir: str,
        output_dir: str,
        repo_path: str | None = None,
    ):
        self.base_dir = Path(base_dir)
        self.output_dir = Path(output_dir)
        self.repo_path = Path(repo_path) if repo_path else Path.cwd()
        self.manifest_data: dict[str, Any] = {}
        self.event_records: list[EventRecord] = []
        self.run_summaries: list[RunSummary] = []

    def _get_repo_commit(self) -> str:
        """Get the current git commit hash."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except (subprocess.SubprocessError, FileNotFoundError):
            return "unknown"

    def _count_files(self, directory: Path, pattern: str = "*") -> int:
        """Count files matching a pattern in a directory."""
        if not directory.exists():
            return 0
        return len(list(directory.glob(pattern)))

    def _sum_tokens_from_receipts(self, receipts_dir: Path) -> dict[str, int]:
        """Sum token counts from all receipt files."""
        totals = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}

        if not receipts_dir.exists():
            return totals

        for receipt_file in receipts_dir.glob("*.json"):
            try:
                with open(receipt_file, "r", encoding="utf-8") as f:
                    receipt = json.load(f)
                totals["input_tokens"] += receipt.get("tokens_in", 0)
                totals["output_tokens"] += receipt.get("tokens_out", 0)
            except (json.JSONDecodeError, KeyError):
                continue

        totals["total_tokens"] = totals["input_tokens"] + totals["output_tokens"]
        return totals

    def _scan_for_api_key(self, directory: Path) -> list[str]:
        """
        Scan directory for API key leaks.

        Returns:
            List of files containing potential API key patterns.
        """
        api_key_patterns = [
            "ADAPTION_API_KEY",
            "adaption_api_key",
            "sk-adaption",
            "adaption-key",
        ]

        found = []
        for file_path in directory.rglob("*"):
            if file_path.is_file():
                try:
                    content = file_path.read_text(encoding="utf-8")
                    for pattern in api_key_patterns:
                        if pattern in content:
                            found.append(str(file_path))
                            break
                except (UnicodeDecodeError, PermissionError):
                    continue

        return found

    def reconcile_manifest(self) -> dict[str, Any]:
        """
        Reconcile MANIFEST counts against disk.

        Returns:
            Manifest dictionary with all counts verified against disk.
        """
        manifest = {
            "schema_version": "dataset-pack-v1",
            "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "repo_commit": self._get_repo_commit(),
            "runs": [],
            "totals": {
                "runs": 0,
                "calls": 0,
                "artifacts": 0,
                "receipts": 0,
                "events": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
            },
        }

        # Find all run directories
        run_dirs = sorted(self.base_dir.glob("run-*"))

        for run_dir in run_dirs:
            if not run_dir.is_dir():
                continue

            # Read run.json
            run_json_path = run_dir / "run.json"
            if not run_json_path.exists():
                continue

            with open(run_json_path, "r", encoding="utf-8") as f:
                run_data = json.load(f)

            # Count artifacts on disk
            artifacts_count = self._count_files(run_dir / "artifacts", "*.txt")
            receipts_count = self._count_files(run_dir / "receipts", "*.json")

            # Count calls in calls.jsonl
            calls_jsonl_path = run_dir / "logs" / "calls.jsonl"
            calls_count = 0
            events_count = 0  # Count from sealed event log
            if calls_jsonl_path.exists():
                with open(calls_jsonl_path, "r", encoding="utf-8") as f:
                    calls_count = sum(1 for line in f if line.strip())

            # Count events from sealed event log (events.jsonl)
            events_jsonl_path = run_dir / "logs" / "events.jsonl"
            if events_jsonl_path.exists():
                with open(events_jsonl_path, "r", encoding="utf-8") as f:
                    events_count = sum(1 for line in f if line.strip())

            # Verify counts match
            run_manifest = {
                "run_id": run_data.get("run_id", run_dir.name),
                "instance_id": run_data.get("instance_id", "unknown"),
                "config_hash": run_data.get("config_hash", ""),
                "calls": {
                    "counted_on_disk": calls_count,
                    "in_run_json": run_data.get("calls_count", 0),
                    "match": calls_count == run_data.get("calls_count", 0),
                },
                "artifacts": {
                    "counted_on_disk": artifacts_count,
                },
                "receipts": {
                    "counted_on_disk": receipts_count,
                },
                "events": {
                    "counted_on_disk": events_count,
                },
                "logs": (
                    ["logs/calls.jsonl", "logs/events.jsonl"]
                    if events_jsonl_path.exists()
                    else ["logs/calls.jsonl"]
                    if calls_jsonl_path.exists()
                    else []
                ),
            }

            manifest["runs"].append(run_manifest)

            # Update totals
            manifest["totals"]["runs"] += 1
            manifest["totals"]["calls"] += calls_count
            manifest["totals"]["artifacts"] += artifacts_count
            manifest["totals"]["receipts"] += receipts_count
            manifest["totals"]["events"] += events_count

            # Sum tokens
            receipts_dir = run_dir / "receipts"
            tokens = self._sum_tokens_from_receipts(receipts_dir)
            manifest["totals"]["input_tokens"] += tokens["input_tokens"]
            manifest["totals"]["output_tokens"] += tokens["output_tokens"]
            manifest["totals"]["total_tokens"] += tokens["total_tokens"]

        self.manifest_data = manifest
        return manifest

    def write_manifest(self, output_path: str | None = None) -> Path:
        """
        Write MANIFEST.md file.

        Args:
            output_path: Optional custom output path

        Returns:
            Path to written manifest file.
        """
        if not self.manifest_data:
            self.reconcile_manifest()

        output = Path(output_path) if output_path else self.output_dir / "MANIFEST.md"
        output.parent.mkdir(parents=True, exist_ok=True)

        # Generate markdown manifest
        md_lines = [
            "# Dataset Pack Manifest",
            "",
            f"**Generated:** {self.manifest_data['generated_at']}",
            f"**Repo Commit:** {self.manifest_data['repo_commit']}",
            f"**Schema Version:** {self.manifest_data['schema_version']}",
            "",
            "## Totals",
            "",
            f"- **Runs:** {self.manifest_data['totals']['runs']}",
            f"- **Calls:** {self.manifest_data['totals']['calls']}",
            f"- **Artifacts:** {self.manifest_data['totals']['artifacts']}",
            f"- **Receipts:** {self.manifest_data['totals']['receipts']}",
            f"- **Events:** {self.manifest_data['totals']['events']}",
            f"- **Input Tokens:** {self.manifest_data['totals']['input_tokens']}",
            f"- **Output Tokens:** {self.manifest_data['totals']['output_tokens']}",
            f"- **Total Tokens:** {self.manifest_data['totals']['total_tokens']}",
            "",
            "## Runs",
            "",
        ]

        for run in self.manifest_data["runs"]:
            md_lines.extend(
                [
                    f"### {run['run_id']} ({run['instance_id']})",
                    "",
                    f"- **Config Hash:** {run['config_hash']}",
                    (
                        f"- **Calls:** {run['calls']['counted_on_disk']} "
                        f"({'✓' if run['calls']['match'] else '✗ MISMATCH'})"
                    ),
                    f"- **Artifacts:** {run['artifacts']['counted_on_disk']}",
                    f"- **Receipts:** {run['receipts']['counted_on_disk']}",
                    "",
                ]
            )

        with open(output, "w", encoding="utf-8") as f:
            f.write("\n".join(md_lines) + "\n")

        return output

    def generate_dataset_card(self, output_path: str | None = None) -> Path:
        """
        Generate HF-ready README.md dataset card.

        Includes:
        - YAML frontmatter with configs (license, tags, provenance)
        - Model and provider disclosure
        - Token statistics
        - Data structure documentation

        Args:
            output_path: Optional custom output path

        Returns:
            Path to written dataset card.
        """
        if not self.manifest_data:
            self.reconcile_manifest()

        output = Path(output_path) if output_path else self.output_dir / "README.md"
        output.parent.mkdir(parents=True, exist_ok=True)

        # YAML frontmatter with configs
        yaml_frontmatter = """---
license: mit
task_categories:
  - text-generation
tags:
  - swarm
  - multi-agent
  - freight-in-the-fog
  - adaption
  - glm-53-flash
  - provenance
configs:
  - config_name: records
    data_files: data/records.jsonl
    features:
      - run_id
      - task_id
      - seed
      - topology
      - turn
      - agent_id
      - agent_role
      - event_type
      - content
      - model
      - tokens_in
      - tokens_out
      - receipt_ref
      - provenance
  - config_name: runs
    data_files: data/runs.jsonl
    features:
      - run_id
      - task_id
      - config_hash
      - seed
      - topology
      - turns
      - total_events
      - total_calls
      - total_tokens
      - outcome_metrics
      - artifact_index
      - provenance_summary
---

"""

        # Dataset card content
        card_content = f"""{yaml_frontmatter}# Freight-in-the-Fog Swarm Dataset

## Dataset Description

This dataset contains governed multi-agent swarm runs in the freight-in-the-fog world.
Each run includes full transcripts, per-call receipts, extracted artifacts, and outcome metrics.

**This is a swarm dataset, not a training corpus.** There is no train/test/validation split.
The dataset consists of two tables:
- `data/records.jsonl`: One record per event (observation, message, action, disturbance)
- `data/runs.jsonl`: One summary record per task-run

## Model and Provider

- **Model:** glm-53-flash
- **Provider:** adaption (Adaption Labs)
- **Repo Commit:** {self.manifest_data["repo_commit"]}
- **Generated At:** {self.manifest_data["generated_at"]}

## Token Statistics

- **Total Input Tokens:** {self.manifest_data["totals"]["input_tokens"]}
- **Total Output Tokens:** {self.manifest_data["totals"]["output_tokens"]}
- **Total Tokens:** {self.manifest_data["totals"]["total_tokens"]}
- **Total Calls:** {self.manifest_data["totals"]["calls"]}

## Provenance

All model-generated content is labeled with provenance metadata:
- **model-generated:** Content generated by the model (glm-53-flash), with model ID and receipt reference
- **team-authored:** Content byte-exact from git commits that held it
- **reconstructed-from-log:** Content reconstructed from event logs

Every event's provenance can be traced back to its source in the transcript.

## Data Structure

### records.jsonl

One record per event with the following fields:
- `run_id`: Run identifier
- `task_id`: Task instance ID
- `seed`: Random seed for deterministic replay
- `topology`: Communication topology (mesh, hub-spoke, bidirectional-ring)
- `turn`: Turn number
- `agent_id`: Agent ID (null for world-level events)
- `agent_role`: Agent role in the event
- `event_type`: Event type (observation.recorded, message.sent, action.committed, etc.)
- `content`: Full event content/text
- `model`: Model ID (for model-generated events)
- `tokens_in`: Input token count (for model-generated events)
- `tokens_out`: Output token count (for model-generated events)
- `receipt_ref`: Receipt reference (for model-generated events)
- `provenance`: Provenance label

### runs.jsonl

One summary record per task-run:
- `run_id`: Run identifier
- `task_id`: Task instance ID
- `config_hash`: Hash of task configuration
- `seed`: Random seed
- `topology`: Communication topology
- `turns`: Number of turns executed
- `total_events`: Total event count
- `total_calls`: Total model call count
- `total_tokens`: Total token count
- `outcome_metrics`: Outcome metrics (deliveries, completion status)
- `artifact_index`: Index of artifacts for this run
- `provenance_summary`: Provenance label counts

### Run directories

Each run is stored under `data/runs/<run_id>/` with:
- `logs/events.jsonl`: Sealed event log (source of truth for turn + event_type)
- `logs/calls.jsonl`: Full call records (prompt + response, never truncated)
- `receipts/`: Individual receipt files with token counts
- `artifacts/`: Extracted artifacts with provenance labels
- `run.json`: Run metadata

## Usage

```python
from datasets import load_dataset

# Load records table
records = load_dataset("your-org/freight-swarm-dataset", "records")

# Load runs table
runs = load_dataset("your-org/freight-swarm-dataset", "runs")
```

## License

MIT License

## Citation

If you use this dataset, please cite the associated hackathon report.
"""

        with open(output, "w", encoding="utf-8") as f:
            f.write(card_content)

        return output

    def build_event_records(self) -> list[EventRecord]:
        """
        Build event records from the sealed event log (source of truth).

        B11 fix: Derive turn + event_type from the run's sealed event log,
        not from artifact string parsing or response substring guessing.
        Every record carries non-empty agent_id (use the acting agent or an
        explicit 'system' actor with its own label).

        Returns:
            List of EventRecord objects.
        """
        self.event_records = []

        run_dirs = sorted(self.base_dir.glob("run-*"))

        for run_dir in run_dirs:
            if not run_dir.is_dir():
                continue

            run_json_path = run_dir / "run.json"
            if not run_json_path.exists():
                continue

            with open(run_json_path, "r", encoding="utf-8") as f:
                run_data = json.load(f)

            run_id = run_data.get("run_id", run_dir.name)
            task_id = run_data.get("instance_id", "unknown")
            seed = run_data.get("seed", 0)
            topology = run_data.get("topology", "unknown")

            # B11: Load sealed event log as source of truth for turn + event_type
            events_path = run_dir / "logs" / "events.jsonl"
            events = []
            if events_path.exists():
                with open(events_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            events.append(json.loads(line))

            # Build a map from event payload to event metadata
            event_by_payload = {}
            for event in events:
                payload = event.get("payload", {})
                if "prompt" in payload and "response" in payload:
                    key = (payload["prompt"], payload["response"])
                    event_by_payload[key] = event

            # Load calls.jsonl for content
            calls_jsonl_path = run_dir / "logs" / "calls.jsonl"
            if not calls_jsonl_path.exists():
                continue

            with open(calls_jsonl_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    call = json.loads(line)

                    # B11: Derive turn + event_type from sealed event log
                    prompt = call.get("prompt_full", "")
                    response = call.get("response_full", "")
                    key = (prompt, response)

                    # Look up in event log
                    event_meta = event_by_payload.get(key, {})
                    turn = event_meta.get("turn", 0)  # From sealed event log
                    event_type = event_meta.get(
                        "type", "observation.recorded"
                    )  # From sealed event log

                    role = call.get("role", "unknown")
                    # B11 fix: Every record must carry non-empty agent_id
                    # Use the acting agent or an explicit 'system' actor
                    agent_id = role if role != "system" else "system"
                    agent_role = role

                    record = EventRecord(
                        run_id=run_id,
                        task_id=task_id,
                        seed=seed,
                        topology=topology,
                        turn=turn,  # B11: from sealed event log
                        agent_id=agent_id,  # B11: non-empty agent_id
                        agent_role=agent_role,
                        event_type=event_type,  # B11: from sealed event log
                        content=response,
                        model=call.get("model"),
                        tokens_in=call.get("tokens_in"),
                        tokens_out=call.get("tokens_out"),
                        receipt_ref=call.get("receipt_ref"),
                        provenance=call.get("provenance", "model-generated"),
                    )

                    self.event_records.append(record)

        return self.event_records

    def build_run_summaries(self) -> list[RunSummary]:
        """
        Build run summary records.

        Returns:
            List of RunSummary objects.
        """
        self.run_summaries = []

        run_dirs = sorted(self.base_dir.glob("run-*"))

        for run_dir in run_dirs:
            if not run_dir.is_dir():
                continue

            run_json_path = run_dir / "run.json"
            if not run_json_path.exists():
                continue

            with open(run_json_path, "r", encoding="utf-8") as f:
                run_data = json.load(f)

            # Count events in calls.jsonl
            calls_jsonl_path = run_dir / "logs" / "calls.jsonl"
            event_count = 0
            if calls_jsonl_path.exists():
                with open(calls_jsonl_path, "r", encoding="utf-8") as f:
                    event_count = sum(1 for line in f if line.strip())

            # Build artifact index
            artifact_index = {"total": 0, "by_type": {}}
            artifacts_dir = run_dir / "artifacts"
            if artifacts_dir.exists():
                artifact_index["total"] = self._count_files(artifacts_dir, "*.txt")

            # Sum tokens
            receipts_dir = run_dir / "receipts"
            tokens = self._sum_tokens_from_receipts(receipts_dir)

            # Build provenance summary
            provenance_summary = {
                "model-generated": 0,
                "team-authored": 0,
                "reconstructed-from-log": 0,
            }

            # Count provenance from calls.jsonl
            if calls_jsonl_path.exists():
                with open(calls_jsonl_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        call = json.loads(line)
                        prov = call.get("provenance", "model-generated")
                        if prov in provenance_summary:
                            provenance_summary[prov] += 1

            # Build outcome metrics
            outcome_metrics = {
                "turns": run_data.get("turns", 0),
                "calls": run_data.get("calls_count", 0),
                "status": run_data.get("status", "unknown"),
            }

            # Create summary
            summary = RunSummary(
                run_id=run_data.get("run_id", run_dir.name),
                task_id=run_data.get("instance_id", "unknown"),
                config_hash=run_data.get("config_hash", ""),
                seed=run_data.get("seed", 0),
                topology=run_data.get("topology", "unknown"),
                turns=run_data.get("turns", 0),
                total_events=event_count,
                total_calls=run_data.get("calls_count", 0),
                total_tokens=tokens["total_tokens"],
                outcome_metrics=outcome_metrics,
                artifact_index=artifact_index,
                provenance_summary=provenance_summary,
            )

            self.run_summaries.append(summary)

        return self.run_summaries

    def write_records_jsonl(self, output_path: str | None = None) -> Path:
        """
        Write data/records.jsonl with one record per event.

        Args:
            output_path: Optional custom output path

        Returns:
            Path to written records.jsonl file.
        """
        if not self.event_records:
            self.build_event_records()

        output = (
            Path(output_path)
            if output_path
            else self.output_dir / "data" / "records.jsonl"
        )
        output.parent.mkdir(parents=True, exist_ok=True)

        with open(output, "w", encoding="utf-8") as f:
            f.writelines(record.to_jsonl_line() + "\n" for record in self.event_records)

        return output

    def write_runs_jsonl(self, output_path: str | None = None) -> Path:
        """
        Write data/runs.jsonl with one summary per task-run.

        Args:
            output_path: Optional custom output path

        Returns:
            Path to written runs.jsonl file.
        """
        if not self.run_summaries:
            self.build_run_summaries()

        output = (
            Path(output_path)
            if output_path
            else self.output_dir / "data" / "runs.jsonl"
        )
        output.parent.mkdir(parents=True, exist_ok=True)

        with open(output, "w", encoding="utf-8") as f:
            f.writelines(
                summary.to_jsonl_line() + "\n" for summary in self.run_summaries
            )

        return output

    def verify_no_split(self) -> dict[str, Any]:
        """
        Verify that no train/test/validation split exists.

        Returns:
            Dict with verification results.
        """
        split_dirs = []
        for pattern in ["train*", "test*", "val*", "validation*"]:
            split_dirs.extend(list(self.output_dir.glob(pattern)))

        # Check for split field in records
        has_split_field = False
        records_path = self.output_dir / "data" / "records.jsonl"
        if records_path.exists():
            with open(records_path, "r", encoding="utf-8") as f:
                for line in f:
                    if '"split"' in line:
                        has_split_field = True
                        break

        return {
            "no_split_dirs": len(split_dirs) == 0,
            "no_split_field": not has_split_field,
            "split_dirs_found": [str(d) for d in split_dirs],
            "passed": len(split_dirs) == 0 and not has_split_field,
        }

    def verify_no_key_in_pack(self) -> dict[str, Any]:
        """
        Verify that no API key appears in any pack file.

        Returns:
            Dict with verification results.
        """
        found = self._scan_for_api_key(self.output_dir)

        return {
            "scan_complete": True,
            "api_key_found": len(found) > 0,
            "files_with_key": found,
            "passed": len(found) == 0,
        }

    def package_all(self) -> dict[str, Any]:
        """
        Execute full packaging workflow.

        Ships:
        - MANIFEST.md: Reconciled counts
        - README.md: HF dataset card
        - data/records.jsonl: Event records table
        - data/runs.jsonl: Run summaries table
        - data/runs/<run_id>/: Raw per-run layer (calls.jsonl, events.jsonl, receipts/, artifacts/)

        Returns:
            Dict with packaging results.
        """
        import shutil

        # Reconcile manifest
        manifest = self.reconcile_manifest()

        # Build records and summaries
        self.build_event_records()
        self.build_run_summaries()

        # Write files
        manifest_path = self.write_manifest()
        card_path = self.generate_dataset_card()
        records_path = self.write_records_jsonl()
        runs_path = self.write_runs_jsonl()

        # Copy raw run directories into the pack (B3: ship raw per-run layer)
        data_runs_dir = self.output_dir / "data" / "runs"
        data_runs_dir.mkdir(parents=True, exist_ok=True)

        run_dirs = sorted(self.base_dir.glob("run-*"))
        for run_dir in run_dirs:
            if not run_dir.is_dir():
                continue
            dest_dir = data_runs_dir / run_dir.name
            if dest_dir.exists():
                shutil.rmtree(dest_dir)
            shutil.copytree(run_dir, dest_dir)

        # Verify no split
        split_check = self.verify_no_split()

        # Verify no API key
        key_check = self.verify_no_key_in_pack()

        return {
            "manifest": manifest,
            "manifest_path": str(manifest_path),
            "card_path": str(card_path),
            "records_path": str(records_path),
            "runs_path": str(runs_path),
            "event_records": len(self.event_records),
            "run_summaries": len(self.run_summaries),
            "raw_runs_shipped": len(run_dirs),
            "no_split_check": split_check,
            "no_key_check": key_check,
        }


def package_dataset(
    base_dir: str,
    output_dir: str,
    repo_path: str | None = None,
) -> dict[str, Any]:
    """
    Convenience function to package a dataset.

    Args:
        base_dir: Base directory containing runs
        output_dir: Output directory for packaged data
        repo_path: Path to git repo for commit hash

    Returns:
        Dict with packaging results.
    """
    packager = DatasetPackager(base_dir, output_dir, repo_path)
    return packager.package_all()


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print(
            "Usage: python -m dataset_pack.package <base_dir> <output_dir> [repo_path]"
        )
        sys.exit(1)

    base_dir = sys.argv[1]
    output_dir = sys.argv[2]
    repo_path = sys.argv[3] if len(sys.argv) > 3 else None

    print(f"Packaging dataset from {base_dir} to {output_dir}...")

    try:
        result = package_dataset(base_dir, output_dir, repo_path)
        print("Packaging complete:")
        print(f"  Manifest: {result['manifest_path']}")
        print(f"  Card: {result['card_path']}")
        print(f"  Records: {result['records_path']} ({result['event_records']} events)")
        print(f"  Runs: {result['runs_path']} ({result['run_summaries']} runs)")
        print(
            f"  No split: {'PASSED' if result['no_split_check']['passed'] else 'FAILED'}"
        )
        print(
            f"  No API key: {'PASSED' if result['no_key_check']['passed'] else 'FAILED'}"
        )

        if not result["no_split_check"]["passed"]:
            print(f"  Split dirs found: {result['no_split_check']['split_dirs_found']}")
            sys.exit(1)

        if not result["no_key_check"]["passed"]:
            print(f"  Files with key: {result['no_key_check']['files_with_key']}")
            sys.exit(1)

    except (RuntimeError, OSError, json.JSONDecodeError) as e:
        print(f"Packaging failed: {e}", file=sys.stderr)
        sys.exit(1)
