"""
dataset_pack/run.py — governed run glue for dataset generation

Implements the governed task-submission workflow:
- prepare: set up run directory structure
- submit: execute run through TurnSeamRunner with full provenance logging
- capture: persist calls.jsonl with full prompt+response per line, receipts, run.json

Provenance contract:
- One calls.jsonl line per adaption call (ts, run, call, role, topology, artifact,
  model, FULL prompt, FULL response, tokens_in, tokens_out, receipt, provenance)
- One receipt per call
- run.json with run metadata
- API key NEVER appears in any pack file
"""

from __future__ import annotations

import json
import os
import random
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Add parent to path for runtime import
sys.path.insert(0, str(Path(__file__).parent.parent))
from runtime.runner import EventLog

from .configs import TaskInstanceConfig


@dataclass
class CallRecord:
    """
    A single model call record with full provenance.

    Attributes:
        ts: Timestamp of the call
        run_id: Run identifier
        call_id: Unique call identifier within the run
        role: Agent role that made the call
        topology: Communication topology in use
        artifact: Artifact reference if applicable
        model: Model ID used
        prompt_full: Full prompt text (never truncated)
        response_full: Full response text (never truncated)
        tokens_in: Input token count
        tokens_out: Output token count
        receipt_ref: Receipt reference ID
        provenance: Provenance label ("model-generated", "team-authored", "reconstructed-from-log")
    """

    ts: str
    run_id: str
    call_id: str
    role: str
    topology: str
    artifact: str | None
    model: str
    prompt_full: str
    response_full: str
    tokens_in: int
    tokens_out: int
    receipt_ref: str
    provenance: str = "model-generated"

    def to_jsonl_line(self) -> str:
        """Serialize to a JSONL line."""
        return json.dumps(
            {
                "ts": self.ts,
                "run_id": self.run_id,
                "call_id": self.call_id,
                "role": self.role,
                "topology": self.topology,
                "artifact": self.artifact,
                "model": self.model,
                "prompt_full": self.prompt_full,
                "response_full": self.response_full,
                "tokens_in": self.tokens_in,
                "tokens_out": self.tokens_out,
                "receipt_ref": self.receipt_ref,
                "provenance": self.provenance,
            },
            separators=(",", ":"),
            ensure_ascii=False,
        )


@dataclass
class RunMetadata:
    """
    Metadata for a governed run.

    Attributes:
        run_id: Unique run identifier
        instance_id: Task instance ID from config
        seed: Random seed used
        topology: Communication topology
        disturbance_schedule: Disturbance schedule applied
        agent_roster: List of agent IDs
        turns: Number of turns executed
        policy: Agent policy used
        started_at: Run start timestamp
        completed_at: Run completion timestamp
        status: Run status ("completed", "failed", "dry-run")
        calls_count: Number of model calls made
        config_hash: Hash of the task config
    """

    run_id: str
    instance_id: str
    seed: int
    topology: str
    disturbance_schedule: dict[str, Any]
    agent_roster: list[str]
    turns: int
    policy: str
    started_at: str
    completed_at: str
    status: str
    calls_count: int = 0
    config_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "run_id": self.run_id,
            "instance_id": self.instance_id,
            "seed": self.seed,
            "topology": self.topology,
            "disturbance_schedule": self.disturbance_schedule,
            "agent_roster": self.agent_roster,
            "turns": self.turns,
            "policy": self.policy,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "status": self.status,
            "calls_count": self.calls_count,
            "config_hash": self.config_hash,
        }


class GovernedRunner:
    """
    Governed runner for dataset generation.

    Executes task instances through the prepare → submit → capture workflow
    with full provenance logging.

    Attributes:
        base_dir: Base directory for run output
        config: Task instance configuration
        dry_run: If True, simulate execution without model calls
    """

    def __init__(
        self,
        base_dir: str,
        config: TaskInstanceConfig,
        dry_run: bool = True,
    ):
        self.base_dir = Path(base_dir)
        self.config = config
        self.dry_run = dry_run
        self.run_id = f"run-{config.instance_id}"
        self.run_dir = self.base_dir / self.run_id
        self.logs_dir = self.run_dir / "logs"
        self.artifacts_dir = self.run_dir / "artifacts"
        self.receipts_dir = self.run_dir / "receipts"
        self.call_records: list[CallRecord] = []
        self.call_counter = 0
        self.event_log: EventLog | None = None  # Sealed event log

    def prepare(self) -> Path:
        """
        Prepare the run directory structure.

        Creates:
        - <run_id>/
          - logs/
          - artifacts/
          - receipts/

        Returns:
            Path to the run directory.

        Raises:
            ValueError: If run directory already exists (prevents overwriting).
        """
        if self.run_dir.exists():
            raise ValueError(f"Run directory {self.run_dir} already exists")

        self.run_dir.mkdir(parents=True, exist_ok=False)
        self.logs_dir.mkdir(exist_ok=False)
        self.artifacts_dir.mkdir(exist_ok=False)
        self.receipts_dir.mkdir(exist_ok=False)

        # Write config snapshot
        config_snapshot = {
            "instance_id": self.config.instance_id,
            "seed": self.config.seed,
            "topology": self.config.topology,
            "hub": self.config.hub,
            "disturbance_schedule": self.config.disturbance_schedule,
            "turns": self.config.turns,
            "policy": self.config.policy,
            "config_hash": self.config.config_hash(),
        }
        config_path = self.run_dir / "config.json"
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config_snapshot, f, indent=2, ensure_ascii=False)

        return self.run_dir

    def _generate_call_record(
        self,
        role: str,
        prompt: str,
        response: str,
        model: str = "glm-53-flash",
        artifact: str | None = None,
    ) -> CallRecord:
        """Generate a call record with full provenance."""
        self.call_counter += 1
        now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        receipt_ref = f"receipt-{self.run_id}-{self.call_counter:04d}"

        # In dry-run mode, use deterministic token counts
        if self.dry_run:
            tokens_in = len(prompt) // 4  # Rough approximation
            tokens_out = len(response) // 4
        else:
            # Real counts would come from API response
            tokens_in = 0
            tokens_out = 0

        return CallRecord(
            ts=now,
            run_id=self.run_id,
            call_id=f"call-{self.call_counter:04d}",
            role=role,
            topology=self.config.topology,
            artifact=artifact,
            model=model,
            prompt_full=prompt,
            response_full=response,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            receipt_ref=receipt_ref,
            provenance="model-generated",
        )

    def _init_event_log(self) -> None:
        """Initialize the sealed event log for this run."""
        base_ts = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        self.event_log = EventLog(self.run_id, base_ts)

    def submit(self) -> None:
        """
        Submit the run for execution.

        In dry-run mode: generates fixture log from a predefined scenario.
        In live mode: executes through the governed task-submission workflow
        (prepare → submit → capture) with real API calls via Adaption.

        Live mode integration:
        - Uses ADAPTION_API_KEY from environment (never printed/written)
        - Reads real token counts from API response
        - Writes sealed event log per run
        """
        if self.dry_run:
            self._simulate_run()
        else:
            # Live execution via governed workflow
            self._execute_live_run()

    def _execute_live_run(self) -> None:
        """
        Execute a live run through the governed task-submission workflow.

        Uses Adaption API for model calls with full provenance logging.
        API key is read from ADAPTION_API_KEY environment variable only.
        """
        from adaption import Adaption

        api_key = os.environ.get("ADAPTION_API_KEY")
        if not api_key:
            raise RuntimeError("ADAPTION_API_KEY not set in environment")

        # Initialize Adaption client (key from env, never printed)
        client = Adaption()

        # Initialize event log for sealing
        self._init_event_log()

        rng = random.Random(self.config.seed)
        agents = self.config.agent_roster

        for turn in range(1, self.config.turns + 1):
            # Apply disturbance if scheduled
            for dist_kind, dist_config in self.config.disturbance_schedule.items():
                if dist_config.get("turn") == turn:
                    # Log disturbance to event log
                    self.event_log.append(
                        turn=turn,
                        agent_id=None,
                        event_type="disturbance.applied",
                        payload={"kind": dist_kind, "config": dist_config},
                    )
                    # Generate call record for disturbance
                    self._generate_call_record(
                        role="system",
                        prompt=f"Apply disturbance: {dist_kind} at turn {turn}",
                        response=f"Disturbance {dist_kind} applied: {json.dumps(dist_config)}",
                        model="glm-53-flash",
                        artifact=None,
                    )

            # Simulate each agent's turn
            for agent_id in agents:
                # Check if agent is muted
                if "peer-mute" in self.config.disturbance_schedule:
                    mute_config = self.config.disturbance_schedule["peer-mute"]
                    if mute_config.get("agent") == agent_id and turn >= mute_config.get(
                        "turn", 0
                    ):
                        # Log mute event
                        self.event_log.append(
                            turn=turn,
                            agent_id=agent_id,
                            event_type="agent.muted",
                            payload={"by": "peer-mute"},
                        )
                        continue  # Muted agent skips communication

                # Generate observation prompt
                obs_prompt = (
                    f"Agent {agent_id} observes at turn {turn} in {self.config.topology} topology. "
                    f"Seed: {self.config.seed}. Location: {rng.choice(['west', 'east', 'south', 'relay-a'])}. "
                    f"Visible freight: {rng.randint(0, 3)} items."
                )

                # Call Adaption API
                response = client.chat.completions.create(
                    model="glm-53-flash",
                    messages=[{"role": "user", "content": obs_prompt}],
                )
                obs_response = response.choices[0].message.content
                tokens_in = response.usage.prompt_tokens
                tokens_out = response.usage.completion_tokens

                # Log to event log
                self.event_log.append(
                    turn=turn,
                    agent_id=agent_id,
                    event_type="observation.recorded",
                    payload={"prompt": obs_prompt, "response": obs_response},
                )

                # Generate call record with REAL token counts
                self.call_counter += 1
                now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
                receipt_ref = f"receipt-{self.run_id}-{self.call_counter:04d}"
                self.call_records.append(
                    CallRecord(
                        ts=now,
                        run_id=self.run_id,
                        call_id=f"call-{self.call_counter:04d}",
                        role=agent_id,
                        topology=self.config.topology,
                        artifact=f"obs-{agent_id}-t{turn:02d}",
                        model="glm-53-flash",
                        prompt_full=obs_prompt,
                        response_full=obs_response,
                        tokens_in=tokens_in,
                        tokens_out=tokens_out,
                        receipt_ref=receipt_ref,
                        provenance="model-generated",
                    )
                )

                # Generate decision prompt
                decision_prompt = (
                    f"Agent {agent_id} decides at turn {turn}. "
                    f"Context: {obs_response}. Inbox: {rng.randint(0, 2)} messages."
                )

                # Call Adaption API for decision
                response = client.chat.completions.create(
                    model="glm-53-flash",
                    messages=[{"role": "user", "content": decision_prompt}],
                )
                decision_response = response.choices[0].message.content
                tokens_in = response.usage.prompt_tokens
                tokens_out = response.usage.completion_tokens

                # Log to event log
                self.event_log.append(
                    turn=turn,
                    agent_id=agent_id,
                    event_type="policy.decision",
                    payload={"prompt": decision_prompt, "response": decision_response},
                )

                # Generate call record with REAL token counts
                self.call_counter += 1
                now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
                receipt_ref = f"receipt-{self.run_id}-{self.call_counter:04d}"
                self.call_records.append(
                    CallRecord(
                        ts=now,
                        run_id=self.run_id,
                        call_id=f"call-{self.call_counter:04d}",
                        role=agent_id,
                        topology=self.config.topology,
                        artifact=f"dec-{agent_id}-t{turn:02d}",
                        model="glm-53-flash",
                        prompt_full=decision_prompt,
                        response_full=decision_response,
                        tokens_in=tokens_in,
                        tokens_out=tokens_out,
                        receipt_ref=receipt_ref,
                        provenance="model-generated",
                    )
                )

        # Seal the event log
        if self.event_log:
            self.event_log.seal()

    def _simulate_run(self) -> None:
        """
        Simulate a run for dry-run testing.

        Generates fixture call records that exercise the full event vocabulary
        including disturbances. Also creates a sealed event log.
        """
        # Initialize event log for sealing
        self._init_event_log()

        # Simulate agent observations and decisions
        rng = random.Random(self.config.seed)
        agents = self.config.agent_roster

        for turn in range(1, self.config.turns + 1):
            # Apply disturbance if scheduled
            for dist_kind, dist_config in self.config.disturbance_schedule.items():
                if dist_config.get("turn") == turn:
                    # Log disturbance to event log
                    self.event_log.append(
                        turn=turn,
                        agent_id=None,
                        event_type="disturbance.applied",
                        payload={"kind": dist_kind, "config": dist_config},
                    )
                    # Log disturbance application
                    self._generate_call_record(
                        role="system",
                        prompt=f"Apply disturbance: {dist_kind} at turn {turn}",
                        response=f"Disturbance {dist_kind} applied: {json.dumps(dist_config)}",
                        model="glm-53-flash",
                        artifact=None,
                    )

            # Simulate each agent's turn
            for agent_id in agents:
                # Check if agent is muted
                if "peer-mute" in self.config.disturbance_schedule:
                    mute_config = self.config.disturbance_schedule["peer-mute"]
                    if mute_config.get("agent") == agent_id and turn >= mute_config.get(
                        "turn", 0
                    ):
                        # Log mute event
                        self.event_log.append(
                            turn=turn,
                            agent_id=agent_id,
                            event_type="agent.muted",
                            payload={"by": "peer-mute"},
                        )
                        continue  # Muted agent skips communication

                # Generate observation prompt
                obs_prompt = (
                    f"Agent {agent_id} observes at turn {turn} in {self.config.topology} topology. "
                    f"Seed: {self.config.seed}. Location: {rng.choice(['west', 'east', 'south', 'relay-a'])}. "
                    f"Visible freight: {rng.randint(0, 3)} items."
                )
                obs_response = (
                    f"Observation for {agent_id}: queue={rng.randint(0, 3)}, "
                    f"requests=[{{'freight': 'med-kit', 'dest': 'south'}}], "
                    f"known_closures=[], roads_in_view=['east-bridge']"
                )
                # Log observation to event log
                self.event_log.append(
                    turn=turn,
                    agent_id=agent_id,
                    event_type="observation.recorded",
                    payload={"prompt": obs_prompt, "response": obs_response},
                )
                self._generate_call_record(
                    role=agent_id,
                    prompt=obs_prompt,
                    response=obs_response,
                    artifact=f"obs-{agent_id}-t{turn:02d}",
                )

                # Generate decision prompt
                decision_prompt = (
                    f"Agent {agent_id} decides at turn {turn}. "
                    f"Context: {obs_response}. Inbox: {rng.randint(0, 2)} messages."
                )
                decision_response = (
                    f"Decision for {agent_id}: route_freight(f-00{rng.randint(1, 4)}, "
                    f"via='{rng.choice(['west', 'east', 'south'])}->{rng.choice(['west', 'east', 'south'])}')"
                )
                # Log decision to event log
                self.event_log.append(
                    turn=turn,
                    agent_id=agent_id,
                    event_type="policy.decision",
                    payload={"prompt": decision_prompt, "response": decision_response},
                )
                self._generate_call_record(
                    role=agent_id,
                    prompt=decision_prompt,
                    response=decision_response,
                    artifact=f"dec-{agent_id}-t{turn:02d}",
                )

        # Seal the event log
        if self.event_log:
            self.event_log.seal()

    def capture(self) -> dict[str, Any]:
        """
        Capture run results to disk.

        Writes:
        - logs/calls.jsonl: Full call records
        - logs/events.jsonl: Sealed event log (eventlog-seal-v1)
        - receipts/: Individual receipt files
        - run.json: Run metadata

        Returns:
            Dict with capture statistics.
        """
        # Write calls.jsonl
        calls_path = self.logs_dir / "calls.jsonl"
        with open(calls_path, "w", encoding="utf-8") as f:
            f.writelines(record.to_jsonl_line() + "\n" for record in self.call_records)

        # Write sealed event log
        if self.event_log:
            events_path = self.logs_dir / "events.jsonl"
            with open(events_path, "w", encoding="utf-8") as f:
                f.write(self.event_log.to_jsonl())

        # Write individual receipts
        for record in self.call_records:
            receipt_path = self.receipts_dir / f"{record.receipt_ref}.json"
            receipt_data = {
                "receipt_ref": record.receipt_ref,
                "call_id": record.call_id,
                "run_id": record.run_id,
                "model": record.model,
                "tokens_in": record.tokens_in,
                "tokens_out": record.tokens_out,
                "ts": record.ts,
            }
            with open(receipt_path, "w", encoding="utf-8") as f:
                json.dump(receipt_data, f, indent=2, ensure_ascii=False)

        # Write run.json
        completed_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        metadata = RunMetadata(
            run_id=self.run_id,
            instance_id=self.config.instance_id,
            seed=self.config.seed,
            topology=self.config.topology,
            disturbance_schedule=self.config.disturbance_schedule,
            agent_roster=list(self.config.agent_roster),
            turns=self.config.turns,
            policy=self.config.policy,
            started_at=self.call_records[0].ts if self.call_records else completed_at,
            completed_at=completed_at,
            status="dry-run" if self.dry_run else "completed",
            calls_count=len(self.call_records),
            config_hash=self.config.config_hash(),
        )
        run_json_path = self.run_dir / "run.json"
        with open(run_json_path, "w", encoding="utf-8") as f:
            json.dump(metadata.to_dict(), f, indent=2, ensure_ascii=False)

        return {
            "run_id": self.run_id,
            "calls_written": len(self.call_records),
            "receipts_written": len(self.call_records),
            "run_json": str(run_json_path),
            "calls_jsonl": str(calls_path),
            "events_jsonl": str(self.logs_dir / "events.jsonl")
            if self.event_log
            else None,
            "event_log_sealed": self.event_log.sealed if self.event_log else False,
        }

    def run_full_workflow(self) -> dict[str, Any]:
        """
        Execute the full prepare → submit → capture workflow.

        Returns:
            Dict with workflow results.
        """
        # Prepare
        run_dir = self.prepare()

        # Submit (execute or simulate)
        self.submit()

        # Capture
        capture_result = self.capture()

        return {
            "run_dir": str(run_dir),
            **capture_result,
        }


def run_governed_run(
    config: TaskInstanceConfig,
    base_dir: str,
    dry_run: bool = True,
) -> dict[str, Any]:
    """
    Convenience function to run a full governed workflow.

    Args:
        config: Task instance configuration
        base_dir: Base directory for run output
        dry_run: If True, simulate without model calls

    Returns:
        Dict with workflow results.
    """
    runner = GovernedRunner(base_dir, config, dry_run=dry_run)
    return runner.run_full_workflow()


if __name__ == "__main__":
    import sys

    from .configs import get_task_configs

    # Test with first config in dry-run mode
    configs = get_task_configs()
    test_config = configs[0]

    print(f"Testing governed run for {test_config.instance_id} (dry-run)...")

    try:
        result = run_governed_run(
            config=test_config,
            base_dir="/tmp/dataset-pack-test",
            dry_run=True,
        )
        print(f"Run completed: {result['run_id']}")
        print(f"  Calls: {result['calls_written']}")
        print(f"  Receipts: {result['receipts_written']}")
        print(f"  Run JSON: {result['run_json']}")
        print(f"  Calls JSONL: {result['calls_jsonl']}")
    except (RuntimeError, OSError, json.JSONDecodeError) as e:
        print(f"Run failed: {e}", file=sys.stderr)
        sys.exit(1)
