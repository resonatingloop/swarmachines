"""bounded provider policy and private spend evidence for freight episodes."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import tempfile
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

POLICY = "model-route-v1"
MAX_REASON_CHARS = 160
MAX_INPUT_TOKENS = 4_000
MAX_INPUT_BYTES = 4_000
MAX_OUTPUT_TOKENS = 2_048
MAX_CEILING_MICROCREDITS = 10_000_000
OUTPUT_CONTRACT = "json-or-single-fence-v2"

# frozen 2026-11-08 adaption rates, in microcredits per million tokens.
MODEL_RATES = {
    "gemma-4-26b-a4b-it": {"input": 76_500, "output": 255_000},
    "glm-53-flash": {"input": 150_000, "output": 500_000},
    "qwen3.5-397b": {"input": 550_000, "output": 3_500_000},
}

# the hosted catalog exposes these models but not their inference rates. each
# calibration call therefore keeps a deliberately conservative full-credit
# reservation instead of laundering an invented token price into the ledger.
FIXED_RESERVATIONS = {
    "deepseek-v4-flash": 1_000_000,
    "gemma-4-31b-it": 1_000_000,
    "glm-5.2": 1_000_000,
    "qwen3.8-27b": 1_000_000,
}
ACCEPTED_MODELS = frozenset(MODEL_RATES) | frozenset(FIXED_RESERVATIONS)


class BudgetExhausted(RuntimeError):
    """raised before a call whose reservation would cross the ceiling."""


class ModelOutputError(ValueError):
    """categorical model-output rejection without hostile text reflection."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class ParsedDecision:
    action: dict[str, str] | None
    reason: str


@dataclass(frozen=True)
class ModelDecision:
    status: str
    action: dict[str, str] | None
    reason: str
    attempt_id: str | None
    model: str
    input_hash: str
    response_hash: str | None
    input_tokens: int | None
    output_tokens: int | None
    latency_ms: float | None
    reserved_microcredits: int
    charged_microcredits: int
    cost_basis: str
    output_contract: str
    max_output_tokens: int
    available_message_ids: tuple[str, ...]
    provider_status: str | None
    incomplete_reason: str | None


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def estimate_microcredits(
    model: str,
    input_tokens: int = MAX_INPUT_TOKENS,
    output_tokens: int = MAX_OUTPUT_TOKENS,
) -> int:
    """return a published-rate estimate or retained conservative reservation."""
    if model in FIXED_RESERVATIONS:
        return FIXED_RESERVATIONS[model]
    if model not in MODEL_RATES:
        raise ValueError("model not in accepted panel")
    if input_tokens < 0 or output_tokens < 0:
        raise ValueError("token counts must be nonnegative")
    rates = MODEL_RATES[model]
    numerator = input_tokens * rates["input"] + output_tokens * rates["output"]
    return (numerator + 999_999) // 1_000_000


def cost_basis(model: str) -> str:
    if model in MODEL_RATES:
        return "published_rate_estimate"
    if model in FIXED_RESERVATIONS:
        return "fixed_conservative_reservation"
    raise ValueError("model not in accepted panel")


class BudgetLedger:
    """atomic mode-0600 attempt ledger with reserve-before-call semantics."""

    def __init__(self, path: str | Path, ceiling_microcredits: int):
        if not 0 < ceiling_microcredits <= MAX_CEILING_MICROCREDITS:
            raise ValueError("budget ceiling exceeds accepted bound")
        self.path = Path(path)
        self.lock_path = self.path.with_suffix(self.path.suffix + ".lock")
        self.ceiling_microcredits = ceiling_microcredits
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)

    @contextmanager
    def _locked(self) -> Iterator[dict[str, Any]]:
        lock_fd = os.open(self.lock_path, os.O_RDWR | os.O_CREAT, 0o600)
        os.chmod(self.lock_path, 0o600)
        with os.fdopen(lock_fd, "r+") as lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            if self.path.exists():
                state = json.loads(self.path.read_text(encoding="utf-8"))
                if state.get("ceiling_microcredits") != self.ceiling_microcredits:
                    raise ValueError("ledger ceiling mismatch")
            else:
                state = {
                    "version": 1,
                    "ceiling_microcredits": self.ceiling_microcredits,
                    "attempts": [],
                }
            yield state
            self._write_atomic(state)
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    def _write_atomic(self, state: dict[str, Any]) -> None:
        fd, temp_name = tempfile.mkstemp(prefix=".ledger-", dir=self.path.parent)
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(_canonical(state) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, self.path)
            os.chmod(self.path, 0o600)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)

    @staticmethod
    def _charged(state: dict[str, Any]) -> int:
        return sum(int(row["charged_microcredits"]) for row in state["attempts"])

    def reserve(self, model: str, context: dict[str, Any]) -> dict[str, Any]:
        reserved = estimate_microcredits(model)
        with self._locked() as state:
            if self._charged(state) + reserved > self.ceiling_microcredits:
                raise BudgetExhausted("budget_stopped")
            row = {
                "attempt_id": uuid.uuid4().hex,
                "model": model,
                "status": "reserved",
                "reserved_microcredits": reserved,
                "charged_microcredits": reserved,
                "cost_basis": cost_basis(model),
                "input_tokens": None,
                "output_tokens": None,
                "context": context,
            }
            state["attempts"].append(row)
            return dict(row)

    def settle(
        self,
        attempt_id: str,
        *,
        status: str,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
    ) -> dict[str, Any]:
        if status not in {
            "completed",
            "null",
            "malformed",
            "illegal",
            "incomplete",
            "input_rejected",
            "evidence_failed",
            "provider_failed",
        }:
            raise ValueError("unknown settlement status")
        with self._locked() as state:
            rows = [row for row in state["attempts"] if row["attempt_id"] == attempt_id]
            if len(rows) != 1 or rows[0]["status"] != "reserved":
                raise ValueError("attempt is not uniquely reservable")
            row = rows[0]
            row["status"] = status
            if input_tokens is not None and output_tokens is not None:
                if input_tokens < 0 or output_tokens < 0:
                    raise ValueError("token counts must be nonnegative")
                row["input_tokens"] = input_tokens
                row["output_tokens"] = output_tokens
                row["charged_microcredits"] = estimate_microcredits(
                    row["model"], input_tokens, output_tokens
                )
            # an uncertain provider failure intentionally retains its reservation.
            return dict(row)

    def snapshot(self) -> dict[str, Any]:
        with self._locked() as state:
            result = json.loads(_canonical(state))
            result["charged_microcredits"] = self._charged(state)
            return result


def candidate_actions(observation: dict[str, Any]) -> tuple[dict[str, str], ...]:
    """derive the only actions a model is allowed to return from local evidence."""
    current = observation.get("current_location")
    freight = observation.get("visible_freight")
    routes = observation.get("known_routes")
    if (
        not isinstance(current, str)
        or not isinstance(freight, list)
        or not isinstance(routes, dict)
    ):
        raise TypeError("invalid model observation")
    candidates = []
    for item in freight:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            raise TypeError("invalid visible freight")
        for route, status in sorted(routes.items()):
            if status == "open" and route.startswith(current + "->"):
                candidates.append(
                    {"kind": "route_freight", "freight_id": item["id"], "via": route}
                )
    return tuple(candidates)


def parse_model_output(
    text: str, candidates: tuple[dict[str, str], ...]
) -> ParsedDecision:
    """parse raw json or one solitary json fence, then enforce the action boundary."""
    if not isinstance(text, str):
        raise ModelOutputError("invalid_json")
    body = text.strip()
    try:
        value = json.loads(body)
    except json.JSONDecodeError:
        match = re.fullmatch(r"```json[ \t]*\r?\n(?P<body>[\s\S]*?)\r?\n```", body)
        if match is None:
            raise ModelOutputError("invalid_json") from None
        try:
            value = json.loads(match.group("body"))
        except json.JSONDecodeError:
            raise ModelOutputError("invalid_json") from None
    if not isinstance(value, dict) or set(value) != {"action", "reason"}:
        raise ModelOutputError("invalid_shape")
    reason = value["reason"]
    if not isinstance(reason, str) or not reason or len(reason) > MAX_REASON_CHARS:
        raise ModelOutputError("invalid_reason")
    action = value["action"]
    if action is None:
        return ParsedDecision(action=None, reason=reason)
    if not isinstance(action, dict) or set(action) != {"kind", "freight_id", "via"}:
        raise ModelOutputError("invalid_action_shape")
    if action not in candidates:
        raise ModelOutputError("action_not_candidate")
    return ParsedDecision(action=action, reason=reason)


def _report_manifest(reports: tuple[Any, ...]) -> list[dict[str, Any]]:
    manifest = []
    for report in reports:
        manifest.append(
            {
                "message_id": report.message_id,
                "sender": report.sender,
                "observed_turn": report.turn,
                "routes": dict(report.routes),
            }
        )
    return manifest


def build_messages(
    observation: dict[str, Any], reports: tuple[Any, ...]
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    """build a bounded prompt and its inspectable input manifest."""
    manifest = {
        "observation": observation,
        "reports": _report_manifest(reports),
        "allowed_actions": list(candidate_actions(observation)),
    }
    messages = [
        {
            "role": "system",
            "content": (
                "choose one allowed freight action using only the supplied evidence. "
                "return either raw json or one solitary ```json markdown fence, with no "
                "surrounding prose. the object must contain exactly action and reason. "
                "action must be null or an exact allowed_actions object. reason must be "
                "1-160 characters."
            ),
        },
        {"role": "user", "content": _canonical(manifest)},
    ]
    return messages, manifest


def _write_private_evidence(
    evidence_dir: Path, attempt_id: str, evidence: dict[str, Any]
) -> None:
    evidence_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(evidence_dir, 0o700)
    path = evidence_dir / f"{attempt_id}.json"
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(_canonical(evidence) + "\n")


def _raw_response_data(response: Any) -> dict[str, Any]:
    """serialize the provider object privately without falling back to repr."""
    raw = response.raw_response
    if raw is None:
        return {"available": False}
    if hasattr(raw, "to_dict"):
        value = raw.to_dict()
        if isinstance(value, dict):
            return value
    if isinstance(raw, dict):
        return raw
    return {"available": False, "type": type(raw).__name__}


class ModelActionPolicy:
    """single-call model action boundary; no retries and no hidden fallback."""

    def __init__(
        self,
        *,
        model: str,
        adapter: Any,
        ledger: BudgetLedger,
        evidence_dir: str | Path,
    ):
        if model not in ACCEPTED_MODELS:
            raise ValueError("model not in accepted panel")
        self.model = model
        self.cost_basis = cost_basis(model)
        self.adapter = adapter
        self.ledger = ledger
        self.evidence_dir = Path(evidence_dir)

    def decide(
        self,
        observation: dict[str, Any],
        reports: tuple[Any, ...],
        *,
        run_id: str,
        agent_id: str,
        turn: int,
    ) -> ModelDecision:
        messages, manifest = build_messages(observation, reports)
        input_text = _canonical(messages)
        input_hash = _sha256_text(input_text)
        message_ids = tuple(row["message_id"] for row in manifest["reports"])
        context = {
            "run_id": run_id,
            "agent_id": agent_id,
            "turn": turn,
            "input_hash": input_hash,
            "output_contract": OUTPUT_CONTRACT,
            "max_output_tokens": MAX_OUTPUT_TOKENS,
        }
        if len(input_text.encode("utf-8")) > MAX_INPUT_BYTES:
            return ModelDecision(
                status="input_rejected",
                action=None,
                reason="input_limit",
                attempt_id=None,
                model=self.model,
                input_hash=input_hash,
                response_hash=None,
                input_tokens=None,
                output_tokens=None,
                latency_ms=None,
                reserved_microcredits=0,
                charged_microcredits=0,
                cost_basis=self.cost_basis,
                output_contract=OUTPUT_CONTRACT,
                max_output_tokens=MAX_OUTPUT_TOKENS,
                available_message_ids=message_ids,
                provider_status=None,
                incomplete_reason=None,
            )
        try:
            reservation = self.ledger.reserve(self.model, context)
        except BudgetExhausted:
            return ModelDecision(
                status="budget_stopped",
                action=None,
                reason="budget_stopped",
                attempt_id=None,
                model=self.model,
                input_hash=input_hash,
                response_hash=None,
                input_tokens=None,
                output_tokens=None,
                latency_ms=None,
                reserved_microcredits=0,
                charged_microcredits=0,
                cost_basis=self.cost_basis,
                output_contract=OUTPUT_CONTRACT,
                max_output_tokens=MAX_OUTPUT_TOKENS,
                available_message_ids=message_ids,
                provider_status=None,
                incomplete_reason=None,
            )

        attempt_id = reservation["attempt_id"]
        try:
            response = self.adapter.chat(
                model=self.model,
                messages=messages,
                max_output_tokens=MAX_OUTPUT_TOKENS,
            )
        except Exception as exc:  # noqa: BLE001 - categorical provider boundary
            _write_private_evidence(
                self.evidence_dir,
                attempt_id,
                {"messages": messages, "error_type": type(exc).__name__},
            )
            settled = self.ledger.settle(attempt_id, status="provider_failed")
            return ModelDecision(
                status="provider_failed",
                action=None,
                reason="provider_failed",
                attempt_id=attempt_id,
                model=self.model,
                input_hash=input_hash,
                response_hash=None,
                input_tokens=None,
                output_tokens=None,
                latency_ms=None,
                reserved_microcredits=reservation["reserved_microcredits"],
                charged_microcredits=settled["charged_microcredits"],
                cost_basis=self.cost_basis,
                output_contract=OUTPUT_CONTRACT,
                max_output_tokens=MAX_OUTPUT_TOKENS,
                available_message_ids=message_ids,
                provider_status=None,
                incomplete_reason=None,
            )

        response_hash = _sha256_text(response.output_text)
        try:
            _write_private_evidence(
                self.evidence_dir,
                attempt_id,
                {
                    "messages": messages,
                    "model": response.model,
                    "output_text": response.output_text,
                    "usage": asdict(response.usage),
                    "latency_ms": response.latency_ms,
                    "raw_response": _raw_response_data(response),
                },
            )
        except (OSError, TypeError, ValueError):
            settled = self.ledger.settle(
                attempt_id,
                status="evidence_failed",
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
            )
            return ModelDecision(
                status="evidence_failed",
                action=None,
                reason="private_evidence_failed",
                attempt_id=attempt_id,
                model=self.model,
                input_hash=input_hash,
                response_hash=response_hash,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                latency_ms=response.latency_ms,
                reserved_microcredits=reservation["reserved_microcredits"],
                charged_microcredits=settled["charged_microcredits"],
                cost_basis=self.cost_basis,
                output_contract=OUTPUT_CONTRACT,
                max_output_tokens=MAX_OUTPUT_TOKENS,
                available_message_ids=message_ids,
                provider_status=response.status,
                incomplete_reason=response.incomplete_reason,
            )
        status = "completed"
        action = None
        reason = "model_action"
        incomplete_reason = response.incomplete_reason
        if response.status == "incomplete":
            status = "incomplete"
            reason = (
                "max_output_tokens"
                if incomplete_reason == "max_output_tokens"
                else "provider_incomplete"
            )
        elif response.status not in (None, "completed"):
            status = "provider_failed"
            reason = "provider_failed"
        else:
            try:
                parsed = parse_model_output(
                    response.output_text, tuple(manifest["allowed_actions"])
                )
                action = parsed.action
                if action is None:
                    status = "null"
                    reason = "model_null"
            except ModelOutputError as exc:
                status = (
                    "illegal" if exc.code == "action_not_candidate" else "malformed"
                )
                reason = exc.code
        settled = self.ledger.settle(
            attempt_id,
            status=status,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )
        return ModelDecision(
            status=status,
            action=action,
            reason=reason,
            attempt_id=attempt_id,
            model=self.model,
            input_hash=input_hash,
            response_hash=response_hash,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            latency_ms=response.latency_ms,
            reserved_microcredits=reservation["reserved_microcredits"],
            charged_microcredits=settled["charged_microcredits"],
            cost_basis=self.cost_basis,
            output_contract=OUTPUT_CONTRACT,
            max_output_tokens=MAX_OUTPUT_TOKENS,
            available_message_ids=message_ids,
            provider_status=response.status,
            incomplete_reason=incomplete_reason,
        )
