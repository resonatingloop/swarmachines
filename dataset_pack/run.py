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

import hashlib
import json
import random
import sys
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Add parent to path for runtime import
sys.path.insert(0, str(Path(__file__).parent.parent))
from runtime.runner import EventLog
from runtime.tracer import Tracer

from .budget import CreditBudget
from .configs import TaskInstanceConfig


def _validate_model_call_events(events: list[dict[str, Any]]) -> None:
    """validate each completed or failed provider event against the schema."""
    from jsonschema import Draft202012Validator

    schema_path = (
        Path(__file__).parent.parent / "runtime" / "schema" / "events.schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    for event in events:
        if event.get("type") in {"model.call", "model.call.failed"}:
            validator.validate(event)


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
    credits_estimated: str = "0"
    provenance: str = "model-generated"
    response_status: str = "completed"
    incomplete_reason: str | None = None
    response_id_sha256: str | None = None
    output_item_type_counts: dict[str, int] | None = None
    message_content_type_counts: dict[str, int] | None = None
    visible_response_chars: int = 0
    total_tokens: int = 0
    reasoning_tokens: int | None = None
    cached_input_tokens: int | None = None
    model_matches_selected: bool = True
    latency_ms: float = 0.0
    categorical_error: str | None = None

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
                "credits_estimated": self.credits_estimated,
                "provenance": self.provenance,
                "response_status": self.response_status,
                "incomplete_reason": self.incomplete_reason,
                "response_id_sha256": self.response_id_sha256,
                "output_item_type_counts": self.output_item_type_counts or {},
                "message_content_type_counts": self.message_content_type_counts or {},
                "visible_response_chars": self.visible_response_chars,
                "total_tokens": self.total_tokens,
                "reasoning_tokens": self.reasoning_tokens,
                "cached_input_tokens": self.cached_input_tokens,
                "model_matches_selected": self.model_matches_selected,
                "latency_ms": self.latency_ms,
                "categorical_error": self.categorical_error,
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
    failure_type: str | None = None
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
            "failure_type": self.failure_type,
            "calls_count": self.calls_count,
            "config_hash": self.config_hash,
        }


def _trace_usage(usage: Any) -> dict[str, int]:
    """map provider usage into non-overlapping langfuse buckets."""
    reasoning = usage.reasoning_tokens or 0
    visible_output = usage.output_tokens - reasoning
    details = {
        "input": usage.input_tokens,
        "output": visible_output,
        "total": usage.total_tokens,
    }
    if reasoning:
        details["output_reasoning_tokens"] = reasoning
    if usage.cached_input_tokens:
        details["input_cached_tokens"] = usage.cached_input_tokens
    return details


def _model_call_payload(
    record: CallRecord, source_seq: int, source_event_type: str
) -> dict[str, Any]:
    """build the sealed event payload paired with one persisted call record."""
    if record.response_status != "completed" or not record.response_full.strip():
        raise ValueError(
            "only completed nonempty responses may become model.call events"
        )
    return {
        "source_event_seq": source_seq,
        "source_event_type": source_event_type,
        "call_id": record.call_id,
        "model": record.model,
        "prompt": record.prompt_full,
        "response": record.response_full,
        "tokens_in": record.tokens_in,
        "tokens_out": record.tokens_out,
        "receipt_ref": record.receipt_ref,
        "provenance": record.provenance,
        "response_status": record.response_status,
        "response_id_sha256": record.response_id_sha256,
        "output_item_type_counts": record.output_item_type_counts or {},
        "message_content_type_counts": record.message_content_type_counts or {},
        "visible_response_chars": record.visible_response_chars,
        "total_tokens": record.total_tokens,
        "reasoning_tokens": record.reasoning_tokens,
        "cached_input_tokens": record.cached_input_tokens,
        "model_matches_selected": record.model_matches_selected,
        "latency_ms": record.latency_ms,
        "categorical_error": record.categorical_error,
    }


def _model_call_failed_payload(
    record: CallRecord, source_seq: int, source_event_type: str
) -> dict[str, Any]:
    """build one source-linked failure event without inventing a response."""
    if record.response_full:
        raise ValueError("failed model call events require an empty persisted response")
    if record.categorical_error is None:
        raise ValueError("failed model call events require a categorical error")
    return {
        "source_event_seq": source_seq,
        "source_event_type": source_event_type,
        "call_id": record.call_id,
        "model": record.model,
        "prompt": record.prompt_full,
        "tokens_in": record.tokens_in,
        "tokens_out": record.tokens_out,
        "receipt_ref": record.receipt_ref,
        "provenance": record.provenance,
        "response_status": record.response_status,
        "incomplete_reason": record.incomplete_reason,
        "response_id_sha256": record.response_id_sha256,
        "output_item_type_counts": record.output_item_type_counts or {},
        "message_content_type_counts": record.message_content_type_counts or {},
        "visible_response_chars": record.visible_response_chars,
        "total_tokens": record.total_tokens,
        "reasoning_tokens": record.reasoning_tokens,
        "cached_input_tokens": record.cached_input_tokens,
        "model_matches_selected": record.model_matches_selected,
        "latency_ms": record.latency_ms,
        "categorical_error": record.categorical_error,
    }


class _ModelCaptureEventLog(EventLog):
    """append model transcripts inside the turn loop and before sealing."""

    def __init__(
        self,
        run_id: str,
        base_ts: str,
        capture: Callable[[int, str | None, str, dict], CallRecord | None],
        call_records: list[CallRecord],
    ):
        super().__init__(run_id, base_ts)
        self._capture = capture
        self._call_records = call_records

    def append(
        self, turn: int, agent_id: str | None, event_type: str, payload: dict
    ) -> None:
        super().append(turn, agent_id, event_type, payload)
        source_seq = self.events[-1]["seq"]
        prior_call_count = len(self._call_records)
        try:
            record = self._capture(turn, agent_id, event_type, payload)
        except BaseException:
            if len(self._call_records) == prior_call_count + 1:
                failed_record = self._call_records[-1]
                super().append(
                    turn,
                    agent_id,
                    "model.call.failed",
                    _model_call_failed_payload(
                        failed_record,
                        source_seq,
                        event_type,
                    ),
                )
            raise
        if record is None:
            return
        super().append(
            turn,
            agent_id,
            "model.call",
            _model_call_payload(record, source_seq, event_type),
        )

    def seal(self) -> None:
        _validate_model_call_events(self.events)
        super().seal()


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
        budget: CreditBudget | None = None,
        tracer: Tracer | None = None,
    ):
        self.base_dir = Path(base_dir)
        self.config = config
        self.dry_run = dry_run
        if not dry_run and budget is None:
            raise ValueError("live governed runs require an explicit credit budget")
        self.budget = budget
        self.tracer = tracer
        self.status = "prepared"
        self.failure_type: str | None = None
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
            "graph": self.config.graph,
            "job_set": self.config.job_set,
            "agent_roster": self.config.agent_roster,
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
        tokens_in: int = 0,
        tokens_out: int = 0,
        credits_estimated: str = "0",
        diagnostics: dict[str, Any] | None = None,
        total_tokens: int | None = None,
        reasoning_tokens: int | None = None,
        cached_input_tokens: int | None = None,
        latency_ms: float = 0.0,
    ) -> CallRecord:
        """
        Generate a call record with full provenance and append to call_records.

        N1 fix: The record is now appended to self.call_records so dry-run
        ships real calls/receipts/artifacts generated by the machinery.

        Args:
            role: Agent role that made the call
            prompt: Full prompt text
            response: Full response text
            model: Model ID used
            artifact: Artifact reference if applicable
            tokens_in: Input token count (from API or estimated)
            tokens_out: Output token count (from API or estimated)

        Returns:
            The generated CallRecord.
        """
        self.call_counter += 1
        now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        receipt_ref = f"receipt-{self.run_id}-{self.call_counter:04d}"

        diagnostic = diagnostics or {}
        record = CallRecord(
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
            credits_estimated=credits_estimated,
            provenance="model-generated",
            response_status=diagnostic.get("status", "completed"),
            incomplete_reason=diagnostic.get("incomplete_reason"),
            response_id_sha256=diagnostic.get("response_id_sha256"),
            output_item_type_counts=diagnostic.get("output_item_type_counts", {}),
            message_content_type_counts=diagnostic.get(
                "message_content_type_counts", {}
            ),
            visible_response_chars=diagnostic.get(
                "visible_response_chars", len(response)
            ),
            total_tokens=(
                total_tokens if total_tokens is not None else tokens_in + tokens_out
            ),
            reasoning_tokens=reasoning_tokens,
            cached_input_tokens=cached_input_tokens,
            model_matches_selected=diagnostic.get("model_matches_selected", True),
            latency_ms=latency_ms,
            categorical_error=diagnostic.get("categorical_error"),
        )
        # N1 fix: Append the record so dry-run ships real calls/receipts/artifacts
        self.call_records.append(record)
        return record

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
        self.status = "dry-run" if self.dry_run else "completed"

    def _execute_live_run(self) -> None:
        """
        Execute a live run through the governed task-submission workflow.

        B1 fix: Uses TurnSeamRunner with configs.to_runner_args() for the genuine
        turn loop (observe→exchange→act→record). The AdaptionAdapter is the only
        model surface (responses.create; usage input_tokens/output_tokens).
        Live transcripts come from the real world simulation (TurnSeamRunner + freight).

        Uses Adaption API for model calls with full provenance logging.
        API key is read from ADAPTION_API_KEY environment variable only.
        """
        from runtime.adaption_adapter import AdaptionAdapter
        from runtime.runner import TurnSeamRunner

        # Initialize Adaption adapter (key from env, never printed)
        adapter = AdaptionAdapter()

        # B1: Construct TurnSeamRunner from configs.to_runner_args()
        runner_args = self.config.to_runner_args()
        runner = TurnSeamRunner(
            seed=runner_args["seed"],
            comm_topology=runner_args["comm_topology"],
            agents_config=runner_args["agents_config"],
            disturbance_schedule=runner_args["disturbance_schedule"],
            delivery_map=runner_args.get("delivery_map", {}),
            use_freight_world=runner_args.get("use_freight_world", False),
            policy=runner_args.get("policy", "legacy"),
            world_graph=runner_args.get("world_graph"),
            job_set=runner_args.get("job_set"),
            tracer=self.tracer,
        )
        # The dataset instance identity owns every layer of the persisted run.
        # TurnSeamRunner's seed-derived default is useful for standalone runs,
        # but would split calls/run metadata from the sealed event log here.
        runner.run_id = self.run_id

        # Model calls happen at the event seam while the genuine turn loop is
        # running. A dedicated model.call record is appended immediately after
        # its source event, so the terminal seal commits the exact prompt and
        # response without rewriting the source event's typed payload.
        runner.log = _ModelCaptureEventLog(
            runner.run_id,
            runner.base_ts,
            lambda turn, agent_id, event_type, payload: self._capture_live_event(
                adapter, turn, agent_id, event_type, payload
            ),
            self.call_records,
        )

        # B1: Execute the genuine turn loop (observe→exchange→act→record)
        # The runner.run() method handles the full turn cycle and seals the event log
        try:
            runner.run(num_turns=self.config.turns)
        finally:
            # Preserve attempted-call evidence even when the episode aborts.
            self.event_log = runner.log

    def _capture_live_event(
        self,
        adapter: Any,
        turn: int,
        agent_id: str | None,
        event_type: str,
        payload: dict,
    ) -> CallRecord | None:
        """capture one model transcript before the runner seals its log."""
        role = agent_id or "system"

        if event_type == "observation.recorded" and "visible" in payload:
            prompt = (
                f"Agent {role} observes at turn {turn} in {self.config.topology} topology. "
                f"Seed: {self.config.seed}. Visible: {json.dumps(payload['visible'])}"
            )
            artifact = f"obs-{role}-t{turn:02d}"
        elif event_type == "policy.decision":
            prompt = (
                f"Agent {role} decides at turn {turn}. "
                f"Context: {payload.get('context', '')}. "
                f"Topology: {self.config.topology}."
            )
            artifact = f"dec-{role}-t{turn:02d}"
        else:
            return None

        if self.budget is None:
            raise RuntimeError("live provider call attempted without credit budget")
        if self.tracer is None:
            raise RuntimeError("live provider call attempted without strict tracing")
        reservation = self.budget.begin(prompt)
        next_call_id = f"call-{self.call_counter + 1:04d}"
        phase = "observe" if event_type == "observation.recorded" else "act"
        from runtime.adaption_adapter import ResponseContractError

        with self.tracer.generation(
            call_id=next_call_id,
            model_id="glm-53-flash",
            prompt=prompt,
            metadata={
                "turn": turn,
                "phase": phase,
                "agent_id": role,
                "source_event_type": event_type,
                "condition": (
                    ",".join(sorted(self.config.disturbance_schedule)) or "none"
                ),
                "topology": self.config.topology,
                "seed": self.config.seed,
            },
        ) as generation:
            request_args: dict[str, Any] = {
                "instructions": (
                    "answer directly in at most 120 visible words. return a useful "
                    "plain-text answer; do not expose private reasoning."
                ),
                "max_output_tokens": self.budget.MAX_OUTPUT_TOKENS,
                "tools": [],
                "tool_choice": "none",
                "agentic_memory": False,
                "store": False,
            }
            if generation.traceparent is not None:
                request_args["traceparent"] = generation.traceparent
            try:
                model_response = adapter.chat(
                    model="glm-53-flash",
                    messages=[{"role": "user", "content": prompt}],
                    **request_args,
                )
            except ResponseContractError as error:
                self.budget.fail(reservation)
                self._generate_call_record(
                    role=role,
                    prompt=prompt,
                    response="",
                    artifact=artifact,
                    diagnostics=error.diagnostics.to_dict(),
                )
                raise
            except BaseException:
                self.budget.fail(reservation)
                self._generate_call_record(
                    role=role,
                    prompt=prompt,
                    response="",
                    artifact=artifact,
                    diagnostics={
                        "status": "other",
                        "visible_response_chars": 0,
                        "model_matches_selected": True,
                        "categorical_error": "provider_transport_error",
                    },
                )
                raise

            provider_credits = getattr(
                getattr(model_response, "raw_response", None),
                "estimated_credits_consumed",
                None,
            )
            diagnostic = model_response.diagnostics.to_dict()
            try:
                model_response.validate_complete()
            except ResponseContractError:
                credits = self.budget.finish_failed(
                    reservation,
                    input_tokens=model_response.usage.input_tokens,
                    output_tokens=model_response.usage.output_tokens,
                    provider_credits=provider_credits,
                )
                diagnostic = model_response.diagnostics.to_dict()
                record = self._generate_call_record(
                    role=role,
                    prompt=prompt,
                    response="",
                    artifact=artifact,
                    tokens_in=model_response.usage.input_tokens,
                    tokens_out=model_response.usage.output_tokens,
                    credits_estimated=format(credits, "f"),
                    diagnostics=diagnostic,
                    total_tokens=model_response.usage.total_tokens,
                    reasoning_tokens=model_response.usage.reasoning_tokens,
                    cached_input_tokens=model_response.usage.cached_input_tokens,
                    latency_ms=model_response.latency_ms,
                )
                generation.complete(
                    response_sha256=None,
                    diagnostics=diagnostic,
                    usage_details=_trace_usage(model_response.usage),
                    cost_details={"total": float(credits)},
                    latency_ms=model_response.latency_ms,
                    terminal_state="rejected",
                )
                raise

            credits = self.budget.finish(
                reservation,
                input_tokens=model_response.usage.input_tokens,
                output_tokens=model_response.usage.output_tokens,
                provider_credits=provider_credits,
            )
            response = model_response.output_text
            record = self._generate_call_record(
                role=role,
                prompt=prompt,
                response=response,
                model="glm-53-flash",
                artifact=artifact,
                tokens_in=model_response.usage.input_tokens,
                tokens_out=model_response.usage.output_tokens,
                credits_estimated=format(credits, "f"),
                diagnostics=diagnostic,
                total_tokens=model_response.usage.total_tokens,
                reasoning_tokens=model_response.usage.reasoning_tokens,
                cached_input_tokens=model_response.usage.cached_input_tokens,
                latency_ms=model_response.latency_ms,
            )
            generation.complete(
                response_sha256=hashlib.sha256(response.encode("utf-8")).hexdigest(),
                diagnostics=diagnostic,
                usage_details=_trace_usage(model_response.usage),
                cost_details={"total": float(credits)},
                latency_ms=model_response.latency_ms,
                terminal_state="completed",
            )
            return record

    def _append_dry_model_call(
        self,
        *,
        turn: int,
        agent_id: str | None,
        source_event_type: str,
        record: CallRecord,
    ) -> None:
        """pair a synthetic call with the source event immediately before it."""
        if self.event_log is None or not self.event_log.events:
            raise RuntimeError("model call requires a source event")
        source_seq = self.event_log.events[-1]["seq"]
        self.event_log.append(
            turn,
            agent_id,
            "model.call",
            _model_call_payload(record, source_seq, source_event_type),
        )

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
                    disturbance_prompt = (
                        f"Apply disturbance: {dist_kind} at turn {turn}"
                    )
                    disturbance_response = (
                        f"Disturbance {dist_kind} applied: {json.dumps(dist_config)}"
                    )
                    # Log disturbance to event log
                    self.event_log.append(
                        turn=turn,
                        agent_id=None,
                        event_type="disturbance.applied",
                        payload={"kind": dist_kind, "detail": dist_config},
                    )
                    # Log disturbance application
                    disturbance_record = self._generate_call_record(
                        role="system",
                        prompt=disturbance_prompt,
                        response=disturbance_response,
                        model="glm-53-flash",
                        artifact=None,
                    )
                    self._append_dry_model_call(
                        turn=turn,
                        agent_id=None,
                        source_event_type="disturbance.applied",
                        record=disturbance_record,
                    )

            # Simulate each agent's turn
            for agent_id in agents:
                # Check if agent is muted
                if "peer-mute" in self.config.disturbance_schedule:
                    mute_config = self.config.disturbance_schedule["peer-mute"]
                    if mute_config.get("agent") == agent_id and turn >= mute_config.get(
                        "turn", 0
                    ):
                        # The canonical disturbance.applied event above owns the
                        # mute transition; there is no separate agent.muted type.
                        continue  # Muted agent skips communication

                # Generate observation prompt
                location = rng.choice(["west", "east", "south", "relay-a"])
                visible_freight = rng.randint(0, 3)
                obs_prompt = (
                    f"Agent {agent_id} observes at turn {turn} in {self.config.topology} topology. "
                    f"Seed: {self.config.seed}. Location: {location}. "
                    f"Visible freight: {visible_freight} items."
                )
                queue = rng.randint(0, 3)
                obs_response = (
                    f"Observation for {agent_id}: queue={queue}, "
                    f"requests=[{{'freight': 'med-kit', 'dest': 'south'}}], "
                    f"known_closures=[], roads_in_view=['east-bridge']"
                )
                # Log observation to event log
                self.event_log.append(
                    turn=turn,
                    agent_id=agent_id,
                    event_type="observation.recorded",
                    payload={
                        "visible": {
                            "current_location": location,
                            "visible_freight_count": visible_freight,
                            "queue": queue,
                        }
                    },
                )
                observation_seq = self.event_log.events[-1]["seq"]
                observation_record = self._generate_call_record(
                    role=agent_id,
                    prompt=obs_prompt,
                    response=obs_response,
                    artifact=f"obs-{agent_id}-t{turn:02d}",
                )
                self._append_dry_model_call(
                    turn=turn,
                    agent_id=agent_id,
                    source_event_type="observation.recorded",
                    record=observation_record,
                )

                # Generate decision prompt
                inbox_count = rng.randint(0, 2)
                decision_prompt = (
                    f"Agent {agent_id} decides at turn {turn}. "
                    f"Context: {obs_response}. Inbox: {inbox_count} messages."
                )
                freight_id = f"f-00{rng.randint(1, 4)}"
                route_from = rng.choice(["west", "east", "south"])
                route_to = rng.choice(["west", "east", "south"])
                decision_response = (
                    f"Decision for {agent_id}: route_freight({freight_id}, "
                    f"via='{route_from}->{route_to}')"
                )
                # Log decision to event log
                self.event_log.append(
                    turn=turn,
                    agent_id=agent_id,
                    event_type="policy.decision",
                    payload={
                        "policy": "route-gossip-v1",
                        "freight_id": freight_id,
                        "path": [route_from, route_to],
                        "next_hop": route_to,
                        "reason": "route",
                        "consumed_message_ids": [],
                        "local_only_next_hop": route_to,
                        "choice_changed": False,
                        "decision_id": f"decision-{agent_id}-{turn}",
                        "observation_seq": observation_seq,
                        "action_id": f"act-{agent_id}{turn:02d}",
                        "opportunity": True,
                    },
                )
                decision_record = self._generate_call_record(
                    role=agent_id,
                    prompt=decision_prompt,
                    response=decision_response,
                    artifact=f"dec-{agent_id}-t{turn:02d}",
                )
                self._append_dry_model_call(
                    turn=turn,
                    agent_id=agent_id,
                    source_event_type="policy.decision",
                    record=decision_record,
                )

        # Seal the event log
        if self.event_log:
            _validate_model_call_events(self.event_log.events)
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
                "credits_estimated": record.credits_estimated,
                "ts": record.ts,
                "response_status": record.response_status,
                "incomplete_reason": record.incomplete_reason,
                "response_id_sha256": record.response_id_sha256,
                "output_item_type_counts": record.output_item_type_counts or {},
                "message_content_type_counts": record.message_content_type_counts or {},
                "visible_response_chars": record.visible_response_chars,
                "total_tokens": record.total_tokens,
                "reasoning_tokens": record.reasoning_tokens,
                "cached_input_tokens": record.cached_input_tokens,
                "model_matches_selected": record.model_matches_selected,
                "latency_ms": record.latency_ms,
                "categorical_error": record.categorical_error,
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
            status=self.status,
            failure_type=self.failure_type,
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

        # Submit (execute or simulate), retaining partial evidence on failure.
        try:
            self.submit()
        except BaseException as error:
            self.status = "failed"
            self.failure_type = type(error).__name__
            if self.event_log is not None and not self.event_log.sealed:
                _validate_model_call_events(self.event_log.events)
                self.event_log.seal()
            self.capture()
            raise

        # Capture
        capture_result = self.capture()

        # Extract only from the persisted response fields after capture.
        from .extract import extract_artifacts

        extraction_result = extract_artifacts(
            capture_result["calls_jsonl"], str(self.artifacts_dir)
        )

        return {
            "run_dir": str(run_dir),
            **capture_result,
            "extraction": extraction_result,
        }


def run_governed_run(
    config: TaskInstanceConfig,
    base_dir: str,
    dry_run: bool = True,
    budget: CreditBudget | None = None,
    tracer: Tracer | None = None,
) -> dict[str, Any]:
    """
    Convenience function to run a full governed workflow.

    Args:
        config: Task instance configuration
        base_dir: Base directory for run output
        dry_run: If True, simulate without model calls
        budget: Shared fail-closed batch governor required for live calls

    Returns:
        Dict with workflow results.
    """
    runner = GovernedRunner(
        base_dir,
        config,
        dry_run=dry_run,
        budget=budget,
        tracer=tracer,
    )
    return runner.run_full_workflow()


if __name__ == "__main__":
    import sys
    import tempfile

    from .configs import get_task_configs

    # Test with first config in dry-run mode
    configs = get_task_configs()
    test_config = configs[0]

    print(f"Testing governed run for {test_config.instance_id} (dry-run)...")

    try:
        with tempfile.TemporaryDirectory(prefix="swarmachines-dataset-pack-") as root:
            result = run_governed_run(
                config=test_config,
                base_dir=root,
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
