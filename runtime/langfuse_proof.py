"""provider-free live proof for the accepted task10 langfuse boundary.

this command performs exactly two ordered external phases: credential
authentication, then one fictional metadata-only trace. it never imports the
adaption integration. a flush return is not treated as delivery evidence;
the trace passes only after observations-v2 readback and privacy validation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import re
import secrets
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

from runtime.tracer import (
    LANGFUSE_REQUEST_TIMEOUT_SECONDS,
    MASKING_MARKER_KEY,
    RunStatus,
    TraceConfig,
    Tracer,
    _bounded_json_object,
    create_langfuse_client,
)

PROOF_SCHEMA = "task10-langfuse-proof-v1"
ENVIRONMENT = "task10"
READBACK_TIMEOUT_SECONDS = 90.0
READBACK_BACKOFF_SECONDS = (1.0, 2.0, 4.0, 8.0, 10.0)
OBSERVATION_FIELDS = "core,basic,io,metadata,model,usage,trace_context"
ROOT_NAME = "swarmachines-run"
GENERATION_NAME = "swarmachines-model-call"
SYNTHETIC_MODEL = "unknown"
SYNTHETIC_CONDITION = "synthetic-proof"

_RELEASE_PATTERN = re.compile(r"[0-9a-f]{40}")
_TRACE_ID_PATTERN = re.compile(r"[0-9a-f]{32}")
_SPAN_ID_PATTERN = re.compile(r"[0-9a-f]{16}")
_UUID_PATTERN = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}"
)
_SERVICE_NAME_PATTERN = re.compile(r"[A-Za-z0-9_.:-]{1,128}")
_ABSOLUTE_PATH_PATTERN = re.compile(r"(?:^|[\s\"'])(?:/home/|/tmp/|file://)")

_ROOT_METADATA_KEYS = {
    "condition",
    "run_id_sha256",
    "schema_version",
    "seed",
    "type",
    MASKING_MARKER_KEY,
}
_GENERATION_METADATA_KEYS = {
    "agent_id",
    "call_id_sha256",
    "categorical_error",
    "condition",
    "incomplete_reason",
    "latency_ms",
    "message_content_type_counts",
    "model_matches_selected",
    "output_item_type_counts",
    "phase",
    "prompt_sha256",
    "response_id_sha256",
    "response_sha256",
    "seed",
    "source_event_type",
    "status",
    "terminal_state",
    "topology",
    "turn",
    "visible_response_chars",
    MASKING_MARKER_KEY,
}
_OTEL_SCOPE_FLAT_KEYS = {
    "scope.name",
    "scope.version",
    "scope.attributes",
}
_OTEL_RESOURCE_LEAF_KEYS = {
    "resource.attributes.service.instance.id",
    "resource.attributes.service.name",
    "resource.attributes.telemetry.sdk.language",
    "resource.attributes.telemetry.sdk.name",
    "resource.attributes.telemetry.sdk.version",
    "resource.dropped_attributes_count",
    "resource.schema_url",
}
_OTEL_RESOURCE_CONTAINER_KEYS = {
    "resource.attributes",
    "resource.dropped_attributes_count",
    "resource.schema_url",
}
_OTEL_NESTED_KEYS = {"resourceAttributes", "scope"}
_OTEL_RESOURCE_ATTRIBUTE_KEYS = {
    "service.instance.id",
    "service.name",
    "telemetry.sdk.language",
    "telemetry.sdk.name",
    "telemetry.sdk.version",
}
_OTEL_RESOURCE_CONTEXT_KEYS = {
    "langfuse.environment",
    "langfuse.release",
}
_SAFE_FAILURE_CATEGORIES = {
    "auth_check_failed",
    "auth_check_rejected",
    "client_init_failed",
    "client_shutdown_failed",
    "credential_preflight_failed",
    "evidence_write_failed",
    "invalid_release",
    "readback_api_failed",
    "readback_extra_observations",
    "readback_privacy_failed",
    "readback_shape_failed",
    "readback_timeout",
    "synthetic_trace_failed",
    "unsupported_sdk_version",
}
_SAFE_ASSERTION_NAMES = {
    "environment_matches",
    "exact_observation_count",
    "expected_hashes_present",
    "generation_hash_only_io",
    "generation_input_object",
    "generation_mask_marker_safe",
    "generation_metadata_allowlisted",
    "generation_output_object",
    "generation_shape",
    "model_is_synthetic_unknown",
    "model_resolution_safe",
    "no_sensitive_values",
    "release_matches",
    "root_hash_only_io",
    "root_input_object",
    "root_mask_marker_safe",
    "root_metadata_allowlisted",
    "root_output_object",
    "root_shape",
    "terminal_metadata_safe",
    "trace_ids_match",
    "zero_cost",
    "zero_usage",
}


class ProofFailure(RuntimeError):
    """a fixed-category proof failure without provider-controlled text."""

    def __init__(
        self,
        category: str,
        *,
        failed_assertions: tuple[str, ...] = (),
    ):
        if category not in _SAFE_FAILURE_CATEGORIES:
            category = "synthetic_trace_failed"
        self.category = category
        self.failed_assertions = tuple(
            name for name in failed_assertions if name in _SAFE_ASSERTION_NAMES
        )
        super().__init__(category)


@dataclass(frozen=True)
class SyntheticFixture:
    run_id: str
    call_id: str
    prompt: str
    response: str

    @property
    def run_sha256(self) -> str:
        return _sha256(self.run_id)

    @property
    def call_sha256(self) -> str:
        return _sha256(self.call_id)

    @property
    def prompt_sha256(self) -> str:
        return _sha256(self.prompt)

    @property
    def response_sha256(self) -> str:
        return _sha256(self.response)


@dataclass(frozen=True)
class ReadbackResult:
    polls: int
    observations: list[dict[str, Any]]
    summaries: list[dict[str, Any]]
    assertions: dict[str, bool]


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _iso8601(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _plain(value: Any) -> Any:
    """convert sdk response models into json-compatible in-memory data."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, datetime):
        return _iso8601(value)
    if isinstance(value, dict):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    if hasattr(value, "model_dump"):
        return _plain(value.model_dump(mode="json", by_alias=False))
    if hasattr(value, "dict"):
        return _plain(value.dict())
    if hasattr(value, "__dict__"):
        return {
            str(key): _plain(item)
            for key, item in vars(value).items()
            if not key.startswith("_")
        }
    raise ProofFailure("readback_shape_failed")


def _field(observation: dict[str, Any], snake: str, camel: str) -> Any:
    if snake in observation:
        return observation[snake]
    return observation.get(camel)


def _json_object(value: Any) -> tuple[dict[str, Any], bool]:
    payload = _bounded_json_object(value)
    if payload is None:
        return {}, False
    return payload, True


def _response_data(response: Any) -> tuple[list[dict[str, Any]], str | None]:
    plain = _plain(response)
    if not isinstance(plain, dict) or not isinstance(plain.get("data"), list):
        raise ProofFailure("readback_shape_failed")
    observations = plain["data"]
    if not all(isinstance(item, dict) for item in observations):
        raise ProofFailure("readback_shape_failed")
    meta = plain.get("meta") or {}
    if not isinstance(meta, dict):
        raise ProofFailure("readback_shape_failed")
    cursor = meta.get("cursor")
    if cursor is not None and not isinstance(cursor, str):
        raise ProofFailure("readback_shape_failed")
    return observations, cursor


def _all_scalars(value: Any) -> list[str]:
    if isinstance(value, dict):
        scalars: list[str] = []
        for key, item in value.items():
            scalars.append(str(key))
            scalars.extend(_all_scalars(item))
        return scalars
    if isinstance(value, list):
        scalars = []
        for item in value:
            scalars.extend(_all_scalars(item))
        return scalars
    if value is None:
        return []
    return [str(value)]


def _contains_sensitive_value(
    observations: list[dict[str, Any]],
    *,
    fixture: SyntheticFixture,
    config: TraceConfig,
    credential_path: Path,
) -> bool:
    scrubbed_observations: list[dict[str, Any]] = []
    for observation in observations:
        scrubbed = dict(observation)
        metadata = observation.get("metadata")
        if isinstance(metadata, dict):
            scrubbed_metadata = dict(metadata)
            flat_scope = _bounded_json_object(metadata.get("scope.attributes"))
            if flat_scope == {"public_key": config.public_key}:
                scrubbed_metadata["scope.attributes"] = {
                    "public_key": "expected-public-routing-key"
                }
            nested_scope = metadata.get("scope")
            if isinstance(nested_scope, dict):
                nested_attributes = _bounded_json_object(nested_scope.get("attributes"))
                if nested_attributes == {"public_key": config.public_key}:
                    scrubbed_scope = dict(nested_scope)
                    scrubbed_scope["attributes"] = {
                        "public_key": "expected-public-routing-key"
                    }
                    scrubbed_metadata["scope"] = scrubbed_scope
            scrubbed["metadata"] = scrubbed_metadata
        scrubbed_observations.append(scrubbed)
    try:
        serialized = json.dumps(
            scrubbed_observations,
            sort_keys=True,
            ensure_ascii=False,
        )
    except (TypeError, ValueError, OverflowError, RecursionError):
        return True
    forbidden_values = {
        fixture.run_id,
        fixture.call_id,
        fixture.prompt,
        fixture.response,
        str(credential_path),
        credential_path.name,
        "LANGFUSE_PUBLIC_KEY",
        "LANGFUSE_SECRET_KEY",
        "LANGFUSE_BASE_URL",
    }
    # langfuse injects the public project key into scope.attributes after the
    # masking callback. only that exact validated location was scrubbed above;
    # any second occurrence remains forbidden and cannot enter a receipt.
    for value in (config.public_key, config.secret_key, config.base_url):
        if value:
            forbidden_values.add(value)
    if any(value and value in serialized for value in forbidden_values):
        return True
    if _ABSOLUTE_PATH_PATTERN.search(serialized):
        return True
    try:
        scalars = _all_scalars(observations)
    except RecursionError:
        return True
    for scalar in scalars:
        lowered = scalar.lower()
        if lowered.startswith(("exception.", "error.")):
            return True
    return False


def _finite_zero(value: Any, *, allow_none: bool = False) -> bool:
    if value is None:
        return allow_none
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    if isinstance(value, int):
        return value == 0
    return math.isfinite(value) and value == 0.0


def _zero_map(value: Any) -> bool:
    if value is None:
        return True
    return isinstance(value, dict) and all(
        _finite_zero(item) for item in value.values()
    )


def _empty_status(value: Any) -> bool:
    return value is None or value == ""


def _safe_mask_marker(value: Any) -> bool:
    return value is None or value is True


def _installed_version(distribution: str) -> str | None:
    try:
        return version(distribution)
    except PackageNotFoundError:
        return None


def _safe_scope(
    *,
    name: Any,
    sdk_version: Any,
    attributes: Any,
    config: TraceConfig,
) -> bool:
    scope_attributes = _bounded_json_object(attributes)
    return (
        name == "langfuse-sdk"
        and sdk_version == _installed_version("langfuse")
        and scope_attributes == {"public_key": config.public_key}
    )


def _safe_resource_attributes(
    attributes: Any,
    *,
    config: TraceConfig,
    release: str,
) -> bool:
    if not isinstance(attributes, dict):
        return False
    keys = set(attributes)
    if keys != _OTEL_RESOURCE_ATTRIBUTE_KEYS and keys != (
        _OTEL_RESOURCE_ATTRIBUTE_KEYS | _OTEL_RESOURCE_CONTEXT_KEYS
    ):
        return False
    instance_id = attributes.get("service.instance.id")
    service_name = attributes.get("service.name")
    if not (
        isinstance(instance_id, str)
        and _UUID_PATTERN.fullmatch(instance_id)
        and isinstance(service_name, str)
        and _SERVICE_NAME_PATTERN.fullmatch(service_name)
        and service_name != config.public_key
        and attributes.get("telemetry.sdk.language") == "python"
        and attributes.get("telemetry.sdk.name") == "opentelemetry"
        and attributes.get("telemetry.sdk.version")
        == _installed_version("opentelemetry-sdk")
    ):
        return False
    if _OTEL_RESOURCE_CONTEXT_KEYS.issubset(keys):
        return (
            attributes.get("langfuse.environment") == ENVIRONMENT
            and attributes.get("langfuse.release") == release
        )
    return True


def _safe_resource_envelope(
    *,
    attributes: Any,
    dropped_attributes_count: Any,
    schema_url: Any,
    config: TraceConfig,
    release: str,
) -> bool:
    return (
        _safe_resource_attributes(attributes, config=config, release=release)
        and isinstance(dropped_attributes_count, int)
        and not isinstance(dropped_attributes_count, bool)
        and dropped_attributes_count == 0
        and schema_url in {None, ""}
    )


def _system_metadata_safe(
    metadata: dict[str, Any],
    *,
    custom_keys: set[str],
    config: TraceConfig,
    release: str,
) -> bool:
    custom_metadata = {
        key: value for key, value in metadata.items() if key in custom_keys
    }
    try:
        if config.public_key and any(
            config.public_key in scalar for scalar in _all_scalars(custom_metadata)
        ):
            return False
    except RecursionError:
        return False
    system_keys = set(metadata) - custom_keys
    if system_keys == _OTEL_SCOPE_FLAT_KEYS | _OTEL_RESOURCE_LEAF_KEYS:
        resource_attributes = {
            key.removeprefix("resource.attributes."): metadata[key]
            for key in _OTEL_RESOURCE_LEAF_KEYS
            if key.startswith("resource.attributes.")
        }
        return _safe_scope(
            name=metadata["scope.name"],
            sdk_version=metadata["scope.version"],
            attributes=metadata["scope.attributes"],
            config=config,
        ) and _safe_resource_envelope(
            attributes=resource_attributes,
            dropped_attributes_count=metadata["resource.dropped_attributes_count"],
            schema_url=metadata["resource.schema_url"],
            config=config,
            release=release,
        )

    if system_keys == _OTEL_SCOPE_FLAT_KEYS | _OTEL_RESOURCE_CONTAINER_KEYS:
        return _safe_scope(
            name=metadata["scope.name"],
            sdk_version=metadata["scope.version"],
            attributes=metadata["scope.attributes"],
            config=config,
        ) and _safe_resource_envelope(
            attributes=metadata["resource.attributes"],
            dropped_attributes_count=metadata["resource.dropped_attributes_count"],
            schema_url=metadata["resource.schema_url"],
            config=config,
            release=release,
        )

    if system_keys == _OTEL_NESTED_KEYS:
        scope = metadata["scope"]
        if not isinstance(scope, dict) or set(scope) != {
            "name",
            "version",
            "attributes",
        }:
            return False
        return _safe_scope(
            name=scope["name"],
            sdk_version=scope["version"],
            attributes=scope["attributes"],
            config=config,
        ) and _safe_resource_attributes(
            metadata["resourceAttributes"],
            config=config,
            release=release,
        )
    return False


def _safe_ambient_parent(
    value: Any,
    *,
    root_id: str,
    generation_id: str,
) -> bool:
    return value is None or (
        isinstance(value, str)
        and bool(_SPAN_ID_PATTERN.fullmatch(value))
        and value != "0" * 16
        and value not in {root_id, generation_id}
    )


def _safe_span_id(value: Any) -> bool:
    return (
        isinstance(value, str)
        and bool(_SPAN_ID_PATTERN.fullmatch(value))
        and value != "0" * 16
    )


def _safe_model_resolution(generation: dict[str, Any]) -> bool:
    internal_model_id = _field(
        generation,
        "internal_model_id",
        "internalModelId",
    )
    model_id = _field(generation, "model_id", "modelId")
    return model_id is None and (
        internal_model_id is None
        or (
            isinstance(internal_model_id, str)
            and bool(_UUID_PATTERN.fullmatch(internal_model_id))
        )
    )


def _validate_readback(
    observations: list[dict[str, Any]],
    *,
    trace_id: str,
    release: str,
    fixture: SyntheticFixture,
    config: TraceConfig,
    credential_path: Path,
) -> tuple[list[dict[str, Any]], dict[str, bool]]:
    if len(observations) > 2:
        raise ProofFailure("readback_extra_observations")
    if len(observations) != 2:
        raise ProofFailure("readback_shape_failed")

    by_name = {item.get("name"): item for item in observations}
    if set(by_name) != {ROOT_NAME, GENERATION_NAME}:
        raise ProofFailure("readback_shape_failed")
    root = by_name[ROOT_NAME]
    generation = by_name[GENERATION_NAME]

    root_id = root.get("id")
    generation_id = generation.get("id")
    if (
        not _safe_span_id(root_id)
        or not _safe_span_id(generation_id)
        or root_id == generation_id
    ):
        raise ProofFailure("readback_shape_failed")

    root_metadata = root.get("metadata") or {}
    generation_metadata = generation.get("metadata") or {}
    if not isinstance(root_metadata, dict) or not isinstance(generation_metadata, dict):
        raise ProofFailure("readback_shape_failed")
    root_metadata_allowlisted = _system_metadata_safe(
        root_metadata,
        custom_keys=_ROOT_METADATA_KEYS,
        config=config,
        release=release,
    )
    generation_metadata_allowlisted = _system_metadata_safe(
        generation_metadata,
        custom_keys=_GENERATION_METADATA_KEYS,
        config=config,
        release=release,
    )

    root_input, root_input_object = _json_object(root.get("input"))
    root_output, root_output_object = _json_object(root.get("output"))
    generation_input, generation_input_object = _json_object(generation.get("input"))
    generation_output, generation_output_object = _json_object(generation.get("output"))

    root_parent_id = _field(root, "parent_observation_id", "parentObservationId")
    assertions = {
        "exact_observation_count": len(observations) == 2,
        "trace_ids_match": all(
            _field(item, "trace_id", "traceId") == trace_id for item in observations
        ),
        "root_shape": (
            root.get("type") == "SPAN"
            and _safe_ambient_parent(
                root_parent_id,
                root_id=root_id,
                generation_id=generation_id,
            )
            and _field(root, "is_root_observation", "isRootObservation") is True
        ),
        "generation_shape": (
            generation.get("type") == "GENERATION"
            and _field(generation, "parent_observation_id", "parentObservationId")
            == root_id
            and _field(generation, "is_root_observation", "isRootObservation")
            is not True
        ),
        "root_metadata_allowlisted": root_metadata_allowlisted,
        "generation_metadata_allowlisted": generation_metadata_allowlisted,
        "root_mask_marker_safe": _safe_mask_marker(
            root_metadata.get(MASKING_MARKER_KEY)
        ),
        "generation_mask_marker_safe": _safe_mask_marker(
            generation_metadata.get(MASKING_MARKER_KEY)
        ),
        "root_input_object": root_input_object,
        "root_output_object": root_output_object,
        "generation_input_object": generation_input_object,
        "generation_output_object": generation_output_object,
        "release_matches": all(item.get("release") == release for item in observations),
        "environment_matches": all(
            item.get("environment") == ENVIRONMENT for item in observations
        ),
        "model_is_synthetic_unknown": generation.get("model") == SYNTHETIC_MODEL,
        "model_resolution_safe": _safe_model_resolution(generation),
        "zero_usage": _zero_map(_field(generation, "usage_details", "usageDetails")),
        "zero_cost": (
            _zero_map(_field(generation, "cost_details", "costDetails"))
            and _finite_zero(
                _field(generation, "total_cost", "totalCost"),
                allow_none=True,
            )
        ),
        "root_hash_only_io": (
            root_input == {"run_id_sha256": fixture.run_sha256}
            and root_output
            == {
                "status": "completed",
                "reason_category": None,
                "telemetry_error_count": 0,
            }
        ),
        "generation_hash_only_io": (
            generation_input == {"prompt_sha256": fixture.prompt_sha256}
            and generation_output == {"response_sha256": fixture.response_sha256}
        ),
        "expected_hashes_present": (
            root_metadata.get("run_id_sha256") == fixture.run_sha256
            and generation_metadata.get("call_id_sha256") == fixture.call_sha256
            and generation_metadata.get("prompt_sha256") == fixture.prompt_sha256
            and generation_metadata.get("response_sha256") == fixture.response_sha256
        ),
        "terminal_metadata_safe": (
            generation_metadata.get("status") == "completed"
            and generation_metadata.get("terminal_state") == "completed"
            and generation_metadata.get("categorical_error") is None
            and _empty_status(root.get("status_message"))
            and _empty_status(root.get("statusMessage"))
            and _empty_status(generation.get("status_message"))
            and _empty_status(generation.get("statusMessage"))
        ),
        "no_sensitive_values": not _contains_sensitive_value(
            observations,
            fixture=fixture,
            config=config,
            credential_path=credential_path,
        ),
    }
    if not all(assertions.values()):
        raise ProofFailure(
            "readback_privacy_failed",
            failed_assertions=tuple(
                sorted(name for name, passed in assertions.items() if not passed)
            ),
        )

    summaries = [
        {
            "id": root_id,
            "trace_id": trace_id,
            "type": "SPAN",
            "name": ROOT_NAME,
            "parent_observation_id": root_parent_id,
        },
        {
            "id": generation_id,
            "trace_id": trace_id,
            "type": "GENERATION",
            "name": GENERATION_NAME,
            "parent_observation_id": root_id,
        },
    ]
    return summaries, assertions


def _poll_readback(
    client: Any,
    *,
    trace_id: str,
    release: str,
    fixture: SyntheticFixture,
    config: TraceConfig,
    credential_path: Path,
    from_start_time: datetime,
    to_start_time: datetime,
    monotonic: Callable[[], float],
    sleep: Callable[[float], None],
) -> ReadbackResult:
    deadline = monotonic() + READBACK_TIMEOUT_SECONDS
    polls = 0
    backoff_index = 0
    while True:
        remaining = deadline - monotonic()
        if remaining <= 0:
            raise ProofFailure("readback_timeout")
        request_timeout = min(
            LANGFUSE_REQUEST_TIMEOUT_SECONDS,
            int(remaining),
        )
        if request_timeout < 1:
            raise ProofFailure("readback_timeout")
        polls += 1
        try:
            response = client.api.observations.get_many(
                trace_id=trace_id,
                fields=OBSERVATION_FIELDS,
                from_start_time=from_start_time,
                to_start_time=to_start_time,
                limit=10,
                request_options={
                    "timeout_in_seconds": request_timeout,
                    "max_retries": 0,
                },
            )
            observations, cursor = _response_data(response)
        except ProofFailure:
            raise
        except Exception as error:
            raise ProofFailure("readback_api_failed") from error

        if cursor is not None or len(observations) > 2:
            raise ProofFailure("readback_extra_observations")
        if len(observations) == 2:
            summaries, assertions = _validate_readback(
                observations,
                trace_id=trace_id,
                release=release,
                fixture=fixture,
                config=config,
                credential_path=credential_path,
            )
            return ReadbackResult(
                polls=polls,
                observations=observations,
                summaries=summaries,
                assertions=assertions,
            )

        remaining = deadline - monotonic()
        if remaining <= 0:
            raise ProofFailure("readback_timeout")
        delay = min(
            READBACK_BACKOFF_SECONDS[
                min(backoff_index, len(READBACK_BACKOFF_SECONDS) - 1)
            ],
            remaining,
        )
        sleep(delay)
        backoff_index += 1


def _safe_receipt_base(release: str, started_at: datetime) -> dict[str, Any]:
    try:
        langfuse_version = version("langfuse")
    except PackageNotFoundError:
        langfuse_version = "unavailable"
    return {
        "schema": PROOF_SCHEMA,
        "status": "failed",
        "release": release if _RELEASE_PATTERN.fullmatch(release) else "invalid",
        "environment": ENVIRONMENT,
        "runtime": {
            "python": platform.python_version(),
            "langfuse": langfuse_version,
        },
        "started_at": _iso8601(started_at),
        "ended_at": None,
        "auth": {"attempted": False, "passed": False},
        "synthetic": {"attempted": False, "passed": False},
        "failure_category": None,
        "failed_assertions": [],
    }


def _fixture() -> SyntheticFixture:
    nonce = secrets.token_hex(8)
    return SyntheticFixture(
        run_id=f"synthetic-langfuse-proof-{nonce}",
        call_id=f"synthetic-call-{nonce}",
        prompt=f"fictional freight prompt canary {nonce}",
        response=f"fictional freight response canary {nonce}",
    )


def execute_proof(
    *,
    credential_path: Path,
    release: str,
    client_factory: Callable[[TraceConfig], Any] = create_langfuse_client,
    monotonic: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
    now: Callable[[], datetime] = _utc_now,
) -> dict[str, Any]:
    """run the two gates and return a sanitized receipt; never call a model."""
    started_at = now()
    receipt = _safe_receipt_base(release, started_at)
    client = None
    try:
        if not _RELEASE_PATTERN.fullmatch(release):
            raise ProofFailure("invalid_release")
        if not re.fullmatch(r"5(?:\..+)?", receipt["runtime"]["langfuse"]):
            raise ProofFailure("unsupported_sdk_version")
        try:
            config = TraceConfig.from_file(
                credential_path,
                release=release,
                strict=True,
            )
        except Exception as error:
            raise ProofFailure("credential_preflight_failed") from error
        try:
            client = client_factory(config)
        except Exception as error:
            raise ProofFailure("client_init_failed") from error

        receipt["auth"]["attempted"] = True
        try:
            authenticated = client.auth_check()
        except Exception as error:
            raise ProofFailure("auth_check_failed") from error
        if authenticated is not True:
            raise ProofFailure("auth_check_rejected")
        receipt["auth"]["passed"] = True

        fixture = _fixture()
        receipt["synthetic"]["attempted"] = True
        trace_start = now()
        tracer = Tracer(config, client=client)
        try:
            tracer.start_trace(
                fixture.run_id,
                condition=SYNTHETIC_CONDITION,
                seed=0,
            )
            trace_id = tracer.current_trace_id
            if not isinstance(trace_id, str) or not _TRACE_ID_PATTERN.fullmatch(
                trace_id
            ):
                raise ProofFailure("synthetic_trace_failed")
            with tracer.generation(
                call_id=fixture.call_id,
                model_id=SYNTHETIC_MODEL,
                prompt=fixture.prompt,
                metadata={
                    "condition": SYNTHETIC_CONDITION,
                    "topology": "mesh",
                    "seed": 0,
                    "turn": 0,
                    "phase": "observe",
                    "agent_id": "a",
                    "source_event_type": "observation.recorded",
                },
            ) as generation:
                generation.complete(
                    response_sha256=fixture.response_sha256,
                    diagnostics={
                        "status": "completed",
                        "visible_response_chars": len(fixture.response),
                    },
                    usage_details={"input": 0, "output": 0, "total": 0},
                    cost_details={"total": 0.0},
                    latency_ms=0,
                    terminal_state="completed",
                )
            tracer.end_trace(RunStatus.COMPLETED)
        except ProofFailure:
            raise
        except Exception as error:
            raise ProofFailure("synthetic_trace_failed") from error

        from_start_time = trace_start - timedelta(seconds=5)
        to_start_time = trace_start + timedelta(seconds=5)
        readback = _poll_readback(
            client,
            trace_id=trace_id,
            release=release,
            fixture=fixture,
            config=config,
            credential_path=credential_path,
            from_start_time=from_start_time,
            to_start_time=to_start_time,
            monotonic=monotonic,
            sleep=sleep,
        )
        receipt["synthetic"] = {
            "attempted": True,
            "passed": True,
            "trace_id": trace_id,
            "polls": readback.polls,
            "readback": {
                "fields": OBSERVATION_FIELDS,
                "from_start_time": _iso8601(from_start_time),
                "to_start_time": _iso8601(to_start_time),
                "deadline_seconds": READBACK_TIMEOUT_SECONDS,
                "request_timeout_seconds": LANGFUSE_REQUEST_TIMEOUT_SECONDS,
                "sdk_retries": 0,
            },
            "observations": readback.summaries,
            "expected_hashes": {
                "run_id_sha256": fixture.run_sha256,
                "call_id_sha256": fixture.call_sha256,
                "prompt_sha256": fixture.prompt_sha256,
                "response_sha256": fixture.response_sha256,
            },
            "assertions": readback.assertions,
        }
        receipt["status"] = "passed"
    except ProofFailure as error:
        receipt["failure_category"] = error.category
        receipt["failed_assertions"] = list(error.failed_assertions)
    finally:
        if client is not None:
            try:
                client.shutdown()
            except Exception:  # noqa: BLE001 - never persist remote text
                receipt["status"] = "failed"
                receipt["failure_category"] = "client_shutdown_failed"
                if "synthetic" in receipt:
                    receipt["synthetic"]["passed"] = False
        receipt["ended_at"] = _iso8601(now())
    return receipt


def write_receipt(path: Path, receipt: dict[str, Any]) -> str:
    """write one new mode-0600 receipt and return its content digest."""
    payload = (json.dumps(receipt, sort_keys=True, indent=2) + "\n").encode("utf-8")
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        raise
    if path.stat().st_mode & 0o077:
        path.unlink()
        raise PermissionError("proof receipt permissions are not private")
    return hashlib.sha256(payload).hexdigest()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="authenticate langfuse, emit one fictional trace, and read it back"
    )
    parser.add_argument("--langfuse-credentials", type=Path, required=True)
    parser.add_argument("--release", required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    receipt = execute_proof(
        credential_path=args.langfuse_credentials,
        release=args.release,
    )
    try:
        receipt_sha256 = write_receipt(args.evidence, receipt)
    except Exception:  # noqa: BLE001 - do not print paths or exception text
        print("langfuse proof: failed (evidence_write_failed)", file=sys.stderr)
        return 2
    if receipt["status"] != "passed":
        print(
            f"langfuse proof: failed ({receipt['failure_category']}); "
            f"receipt_sha256={receipt_sha256}",
            file=sys.stderr,
        )
        return 1
    print(f"langfuse proof: passed; receipt_sha256={receipt_sha256}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
