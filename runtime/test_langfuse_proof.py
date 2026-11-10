"""offline fake-client proofs for the provider-free langfuse gate."""

from __future__ import annotations

import hashlib
import json
import stat
from collections.abc import Callable
from copy import deepcopy
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from langfuse.api.commons.types.observation_v2 import ObservationV2

from runtime.langfuse_proof import (
    ENVIRONMENT,
    GENERATION_NAME,
    MASKING_MARKER_KEY,
    OBSERVATION_FIELDS,
    READBACK_TIMEOUT_SECONDS,
    ROOT_NAME,
    _plain,
    execute_proof,
    write_receipt,
)
from runtime.tracer import (
    LANGFUSE_REQUEST_TIMEOUT_SECONDS,
    TraceConfig,
    create_langfuse_client,
)

RELEASE = "a" * 40
SERVICE_INSTANCE_ID = "0d6b16c8-a178-4e53-a7e2-f9177cc968ab"


def _otel_metadata(public_key: str) -> dict[str, Any]:
    return {
        "scope.name": "langfuse-sdk",
        "scope.version": version("langfuse"),
        "scope.attributes": {"public_key": public_key},
        "resource.attributes.service.instance.id": SERVICE_INSTANCE_ID,
        "resource.attributes.service.name": "unknown_service:python",
        "resource.attributes.telemetry.sdk.language": "python",
        "resource.attributes.telemetry.sdk.name": "opentelemetry",
        "resource.attributes.telemetry.sdk.version": version("opentelemetry-sdk"),
        "resource.dropped_attributes_count": 0,
        "resource.schema_url": "",
    }


class FakeObservation:
    def __init__(self, record: dict[str, Any]):
        self.record = record

    def update(self, **values: Any) -> None:
        copied = deepcopy(values)
        metadata = copied.pop("metadata", None)
        self.record.update(copied)
        if isinstance(metadata, dict):
            self.record["metadata"].update(metadata)
        cost_details = values.get("cost_details")
        if isinstance(cost_details, dict):
            self.record["total_cost"] = cost_details.get("total")


class FakeObservationContext:
    def __init__(self, client: FakeLangfuse, values: dict[str, Any]):
        self.client = client
        self.values = values
        self.observation: FakeObservation | None = None

    def __enter__(self) -> FakeObservation:
        parent = self.client.stack[-1] if self.client.stack else None
        trace_context = self.values.get("trace_context") or {}
        trace_id = trace_context.get("trace_id") or (
            parent["trace_id"] if parent is not None else None
        )
        index = len(self.client.observations) + 1
        metadata = deepcopy(self.values.get("metadata")) or {}
        metadata.update(_otel_metadata(self.client.public_key))
        record = {
            "id": f"{index:016x}",
            "trace_id": trace_id,
            "parent_observation_id": parent["id"] if parent else None,
            "is_root_observation": parent is None,
            "type": self.values["as_type"].upper(),
            "name": self.values["name"],
            "environment": self.client.environment,
            "release": self.client.release,
            "input": deepcopy(self.values.get("input")),
            "output": None,
            "metadata": metadata,
            "model": self.values.get("model"),
            "internal_model_id": None,
            "model_id": None,
            "usage_details": None,
            "cost_details": None,
            "total_cost": None,
            "status_message": None,
        }
        self.client.observations.append(record)
        self.client.stack.append(record)
        self.observation = FakeObservation(record)
        return self.observation

    def __exit__(self, *_args: object) -> None:
        self.client.stack.pop()


class FakeObservationsApi:
    def __init__(self, client: FakeLangfuse):
        self.client = client

    def get_many(self, **kwargs: Any) -> dict[str, Any]:
        self.client.readback_calls.append(kwargs)
        if self.client.api_delay is not None:
            self.client.api_delay()
        if self.client.readback_exception:
            raise RuntimeError("remote text that must not escape")
        if len(self.client.readback_calls) <= self.client.empty_reads:
            return {"data": [], "meta": {"cursor": None}}
        observations = deepcopy(self.client.observations)
        if self.client.mutator is not None:
            observations = self.client.mutator(observations)
        return {
            "data": observations,
            "meta": {"cursor": self.client.cursor},
        }


class FakeLangfuse:
    def __init__(
        self,
        config: Any,
        *,
        authenticated: bool = True,
        auth_exception: bool = False,
        empty_reads: int = 0,
        readback_exception: bool = False,
        cursor: str | None = None,
        mutator: Callable[[list[dict[str, Any]]], list[dict[str, Any]]] | None = None,
        shutdown_exception: bool = False,
        api_delay: Callable[[], None] | None = None,
    ):
        self.release = config.release
        self.environment = config.environment
        self.public_key = config.public_key
        self.authenticated = authenticated
        self.auth_exception = auth_exception
        self.empty_reads = empty_reads
        self.readback_exception = readback_exception
        self.cursor = cursor
        self.mutator = mutator
        self.shutdown_exception = shutdown_exception
        self.api_delay = api_delay
        self.auth_calls = 0
        self.flush_calls = 0
        self.shutdown_calls = 0
        self.stack: list[dict[str, Any]] = []
        self.observations: list[dict[str, Any]] = []
        self.readback_calls: list[dict[str, Any]] = []
        self.api = SimpleNamespace(observations=FakeObservationsApi(self))

    def auth_check(self) -> bool:
        self.auth_calls += 1
        if self.auth_exception:
            raise RuntimeError("private authentication failure")
        return self.authenticated

    def create_trace_id(self, *, seed: str) -> str:
        return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:32]

    def start_as_current_observation(self, **values: Any) -> FakeObservationContext:
        return FakeObservationContext(self, values)

    def get_current_observation_id(self) -> str:
        return self.stack[-1]["id"]

    def flush(self) -> None:
        self.flush_calls += 1

    def shutdown(self) -> None:
        self.shutdown_calls += 1
        if self.shutdown_exception:
            raise RuntimeError("private shutdown failure")


class FakeClock:
    def __init__(self):
        self.value = 0.0
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        return self.value

    def sleep(self, delay: float) -> None:
        self.sleeps.append(delay)
        self.value += delay


@pytest.fixture
def credential_file(tmp_path: Path) -> Path:
    path = tmp_path / "langfuse.token"
    path.write_text(
        "LANGFUSE_PUBLIC_KEY=pk-synthetic-proof\n"
        "LANGFUSE_SECRET_KEY=sk-synthetic-proof\n"
        "LANGFUSE_BASE_URL=https://example.invalid\n",
        encoding="utf-8",
    )
    path.chmod(0o600)
    return path


def _run(
    credential_file: Path,
    *,
    client_options: dict[str, Any] | None = None,
    clock: FakeClock | None = None,
) -> tuple[dict[str, Any], FakeLangfuse, FakeClock]:
    created: list[FakeLangfuse] = []
    fake_clock = clock or FakeClock()

    def factory(config: Any) -> FakeLangfuse:
        client = FakeLangfuse(config, **(client_options or {}))
        created.append(client)
        return client

    receipt = execute_proof(
        credential_path=credential_file,
        release=RELEASE,
        client_factory=factory,
        monotonic=fake_clock.monotonic,
        sleep=fake_clock.sleep,
    )
    assert len(created) == 1
    return receipt, created[0], fake_clock


def test_success_requires_auth_flush_and_exact_observations_v2_readback(
    credential_file: Path,
) -> None:
    receipt, client, clock = _run(
        credential_file,
        client_options={"empty_reads": 2},
    )

    assert receipt["status"] == "passed"
    assert receipt["auth"] == {"attempted": True, "passed": True}
    assert receipt["synthetic"]["passed"] is True
    assert receipt["synthetic"]["polls"] == 3
    assert all(receipt["synthetic"]["assertions"].values())
    assert [item["name"] for item in receipt["synthetic"]["observations"]] == [
        ROOT_NAME,
        GENERATION_NAME,
    ]
    assert client.auth_calls == 1
    assert client.flush_calls == 2
    assert client.shutdown_calls == 1
    assert len(client.observations) == 2
    assert clock.sleeps == [1.0, 2.0]

    query = client.readback_calls[-1]
    assert query["trace_id"] == receipt["synthetic"]["trace_id"]
    assert query["fields"] == OBSERVATION_FIELDS
    assert query["limit"] == 10
    assert query["request_options"] == {
        "timeout_in_seconds": LANGFUSE_REQUEST_TIMEOUT_SECONDS,
        "max_retries": 0,
    }
    assert query["from_start_time"] < query["to_start_time"]

    encoded = json.dumps(receipt, sort_keys=True)
    assert "pk-synthetic-proof" not in encoded
    assert "sk-synthetic-proof" not in encoded
    assert str(credential_file) not in encoded
    assert "fictional freight" not in encoded


@pytest.mark.parametrize(
    ("options", "category"),
    [
        ({"authenticated": False}, "auth_check_rejected"),
        ({"auth_exception": True}, "auth_check_failed"),
    ],
)
def test_auth_failure_stops_before_synthetic_trace(
    credential_file: Path,
    options: dict[str, Any],
    category: str,
) -> None:
    receipt, client, _clock = _run(credential_file, client_options=options)

    assert receipt["status"] == "failed"
    assert receipt["failure_category"] == category
    assert receipt["auth"]["attempted"] is True
    assert receipt["auth"]["passed"] is False
    assert receipt["synthetic"] == {"attempted": False, "passed": False}
    assert client.observations == []
    assert client.readback_calls == []


def test_readback_timeout_is_strictly_bounded(credential_file: Path) -> None:
    receipt, client, clock = _run(
        credential_file,
        client_options={"empty_reads": 1000},
    )

    assert receipt["status"] == "failed"
    assert receipt["failure_category"] == "readback_timeout"
    assert receipt["synthetic"]["attempted"] is True
    assert receipt["synthetic"]["passed"] is False
    assert clock.value == READBACK_TIMEOUT_SECONDS
    assert all(delay <= 10.0 for delay in clock.sleeps)
    assert client.flush_calls == 2


def test_blocking_read_is_inside_the_ninety_second_deadline(
    credential_file: Path,
) -> None:
    clock = FakeClock()

    def block_for_eighty_nine_seconds() -> None:
        clock.value += 89.0

    receipt, client, _clock = _run(
        credential_file,
        client_options={
            "empty_reads": 1000,
            "api_delay": block_for_eighty_nine_seconds,
        },
        clock=clock,
    )

    assert receipt["failure_category"] == "readback_timeout"
    assert clock.value == READBACK_TIMEOUT_SECONDS
    assert len(client.readback_calls) == 1
    assert client.readback_calls[0]["request_options"] == {
        "timeout_in_seconds": LANGFUSE_REQUEST_TIMEOUT_SECONDS,
        "max_retries": 0,
    }


def test_readback_api_exception_is_categorical(credential_file: Path) -> None:
    receipt, _client, _clock = _run(
        credential_file,
        client_options={"readback_exception": True},
    )

    assert receipt["status"] == "failed"
    assert receipt["failure_category"] == "readback_api_failed"
    assert "remote text" not in json.dumps(receipt)


def test_extra_observation_or_cursor_fails_closed(credential_file: Path) -> None:
    def add_extra(observations: list[dict[str, Any]]) -> list[dict[str, Any]]:
        observations.append(
            {
                "id": "f" * 16,
                "trace_id": observations[0]["trace_id"],
                "type": "EVENT",
                "name": "unexpected",
            }
        )
        return observations

    extra_receipt, _client, _clock = _run(
        credential_file,
        client_options={"mutator": add_extra},
    )
    cursor_receipt, _client, _clock = _run(
        credential_file,
        client_options={"cursor": "unexpected-next-page"},
    )

    assert extra_receipt["failure_category"] == "readback_extra_observations"
    assert cursor_receipt["failure_category"] == "readback_extra_observations"


@pytest.mark.parametrize(
    "mutator",
    [
        lambda observations: [
            {
                **item,
                "metadata": {
                    **(item.get("metadata") or {}),
                    "secret_blob": "nope",
                },
            }
            if item["name"] == GENERATION_NAME
            else item
            for item in observations
        ],
        lambda observations: [
            {**item, "status_message": "/home/private-error"}
            if item["name"] == GENERATION_NAME
            else item
            for item in observations
        ],
        lambda observations: [{**item, "release": "b" * 40} for item in observations],
        lambda observations: [
            {**item, "model": "glm-53-flash"}
            if item["name"] == GENERATION_NAME
            else item
            for item in observations
        ],
    ],
)
def test_privacy_or_contract_mismatch_fails_closed(
    credential_file: Path,
    mutator: Callable[[list[dict[str, Any]]], list[dict[str, Any]]],
) -> None:
    receipt, _client, _clock = _run(
        credential_file,
        client_options={"mutator": mutator},
    )

    assert receipt["status"] == "failed"
    assert receipt["failure_category"] == "readback_privacy_failed"


def test_empty_status_message_is_safe_unset_value(
    credential_file: Path,
) -> None:
    def normalize_unset_status(
        observations: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        return [{**item, "statusMessage": ""} for item in observations]

    receipt, _client, _clock = _run(
        credential_file,
        client_options={"mutator": normalize_unset_status},
    )

    assert receipt["status"] == "passed"
    assert receipt["failed_assertions"] == []


def test_server_generated_parent_and_model_ids_are_bounded_system_fields(
    credential_file: Path,
) -> None:
    def add_server_fields(
        observations: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        return [
            {**item, "parent_observation_id": "b" * 16}
            if item["name"] == ROOT_NAME
            else {
                **item,
                "internal_model_id": "55cddea8-c176-41fd-ae37-fb9b8b0422ed",
            }
            for item in observations
        ]

    receipt, _client, _clock = _run(
        credential_file,
        client_options={"mutator": add_server_fields},
    )

    assert receipt["status"] == "passed"
    assert receipt["synthetic"]["observations"][0]["parent_observation_id"] == (
        "b" * 16
    )


@pytest.mark.parametrize(
    ("root_parent", "internal_model_id", "failed_assertion"),
    [
        ("not-a-span", None, "root_shape"),
        (None, "model-id-with-private-tail", "model_resolution_safe"),
    ],
)
def test_unbounded_server_generated_ids_fail_closed(
    credential_file: Path,
    root_parent: str | None,
    internal_model_id: str | None,
    failed_assertion: str,
) -> None:
    def corrupt_server_fields(
        observations: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        return [
            {**item, "parent_observation_id": root_parent}
            if item["name"] == ROOT_NAME
            else {**item, "internal_model_id": internal_model_id}
            for item in observations
        ]

    receipt, _client, _clock = _run(
        credential_file,
        client_options={"mutator": corrupt_server_fields},
    )

    assert receipt["status"] == "failed"
    assert failed_assertion in receipt["failed_assertions"]
    assert "private-tail" not in json.dumps(receipt)


def test_sdk_observation_serialization_preserves_empty_camel_status() -> None:
    observation = ObservationV2(
        id="1",
        trace_id="0" * 32,
        start_time=datetime(2026, 11, 9, tzinfo=UTC),
        end_time=None,
        project_id="project",
        parent_observation_id=None,
        type="SPAN",
        name=ROOT_NAME,
        status_message="",
    )

    plain = _plain(observation)

    assert plain["statusMessage"] == ""
    assert "status_message" not in plain


def test_failure_receipt_contains_only_fixed_assertion_names(
    credential_file: Path,
) -> None:
    remote_release = "b" * 40

    def change_release(
        observations: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        return [{**item, "release": remote_release} for item in observations]

    receipt, _client, _clock = _run(
        credential_file,
        client_options={"mutator": change_release},
    )

    encoded = json.dumps(receipt, sort_keys=True)
    assert receipt["status"] == "failed"
    assert receipt["failure_category"] == "readback_privacy_failed"
    assert receipt["failed_assertions"] == ["release_matches"]
    assert remote_release not in encoded


def test_masking_marker_is_allowlisted_only_when_true(
    credential_file: Path,
) -> None:
    def add_marker(
        observations: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        return [
            {
                **item,
                "metadata": {
                    **(item.get("metadata") or {}),
                    MASKING_MARKER_KEY: True,
                },
            }
            for item in observations
        ]

    passed, _client, _clock = _run(
        credential_file,
        client_options={"mutator": add_marker},
    )
    assert passed["status"] == "passed"

    def corrupt_marker(
        observations: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        marked = add_marker(observations)
        return [
            {
                **item,
                "metadata": {
                    **(item.get("metadata") or {}),
                    MASKING_MARKER_KEY: False,
                },
            }
            for item in marked
        ]

    failed, _client, _clock = _run(
        credential_file,
        client_options={"mutator": corrupt_marker},
    )
    assert failed["status"] == "failed"
    assert failed["failed_assertions"] == [
        "generation_mask_marker_safe",
        "root_mask_marker_safe",
    ]


def test_metadata_allowlist_failure_is_named_without_remote_values(
    credential_file: Path,
) -> None:
    remote_key = "remote_private_key"
    remote_value = "remote-private-value"

    def add_remote_metadata(
        observations: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        return [
            {
                **item,
                "metadata": {
                    **(item.get("metadata") or {}),
                    remote_key: remote_value,
                },
            }
            if item["name"] == GENERATION_NAME
            else item
            for item in observations
        ]

    receipt, _client, _clock = _run(
        credential_file,
        client_options={"mutator": add_remote_metadata},
    )

    encoded = json.dumps(receipt, sort_keys=True)
    assert receipt["status"] == "failed"
    assert receipt["failed_assertions"] == ["generation_metadata_allowlisted"]
    assert remote_key not in encoded
    assert remote_value not in encoded


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("scope.version", "999.0.0"),
        ("resource.schema_url", "https://private.invalid/schema"),
        ("resource.attributes.service.name", "/home/private-service"),
    ],
)
def test_corrupt_otel_envelope_fails_closed(
    credential_file: Path,
    key: str,
    value: str,
) -> None:
    def corrupt_system_metadata(
        observations: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        return [
            {
                **item,
                "metadata": {
                    **(item.get("metadata") or {}),
                    key: value,
                },
            }
            for item in observations
        ]

    receipt, _client, _clock = _run(
        credential_file,
        client_options={"mutator": corrupt_system_metadata},
    )

    encoded = json.dumps(receipt, sort_keys=True)
    assert receipt["status"] == "failed"
    assert {
        "generation_metadata_allowlisted",
        "root_metadata_allowlisted",
    }.issubset(receipt["failed_assertions"])
    assert value not in encoded


@pytest.mark.parametrize("credential_field", ["secret_key", "base_url"])
def test_secret_material_in_scope_attributes_is_rejected_and_not_persisted(
    credential_file: Path,
    credential_field: str,
) -> None:
    private_value = {
        "secret_key": "sk-synthetic-proof",
        "base_url": "https://example.invalid",
    }[credential_field]

    def add_secret_to_scope(
        observations: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        return [
            {
                **item,
                "metadata": {
                    **(item.get("metadata") or {}),
                    "scope.attributes": {
                        "public_key": "pk-synthetic-proof",
                        credential_field: private_value,
                    },
                },
            }
            for item in observations
        ]

    receipt, _client, _clock = _run(
        credential_file,
        client_options={"mutator": add_secret_to_scope},
    )

    encoded = json.dumps(receipt, sort_keys=True)
    assert receipt["status"] == "failed"
    assert receipt["failed_assertions"] == [
        "generation_metadata_allowlisted",
        "no_sensitive_values",
        "root_metadata_allowlisted",
    ]
    assert private_value not in encoded


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("condition", "pk-synthetic-proof"),
        ("resource.attributes.service.name", "pk-synthetic-proof"),
    ],
)
def test_public_key_is_accepted_only_as_scope_routing_metadata(
    credential_file: Path,
    key: str,
    value: str,
) -> None:
    def move_public_key(
        observations: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        return [
            {
                **item,
                "metadata": {
                    **(item.get("metadata") or {}),
                    key: value,
                },
            }
            for item in observations
        ]

    receipt, _client, _clock = _run(
        credential_file,
        client_options={"mutator": move_public_key},
    )

    assert receipt["status"] == "failed"
    assert receipt["failed_assertions"] == [
        "generation_metadata_allowlisted",
        "no_sensitive_values",
        "root_metadata_allowlisted",
    ]
    assert value not in json.dumps(receipt, sort_keys=True)


def test_public_key_cannot_masquerade_as_receipt_bound_observation_id(
    credential_file: Path,
) -> None:
    def move_public_key_to_ids(
        observations: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        public_key = "pk-synthetic-proof"
        return [
            {**item, "id": public_key}
            if item["name"] == ROOT_NAME
            else {**item, "parent_observation_id": public_key}
            for item in observations
        ]

    receipt, _client, _clock = _run(
        credential_file,
        client_options={"mutator": move_public_key_to_ids},
    )

    assert receipt["status"] == "failed"
    assert receipt["failure_category"] == "readback_shape_failed"
    assert "pk-synthetic-proof" not in json.dumps(receipt, sort_keys=True)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("user_id", "pk-synthetic-proof"),
        ("id", "0" * 16),
    ],
)
def test_unchecked_top_level_public_key_and_zero_span_id_fail_closed(
    credential_file: Path,
    field: str,
    value: str,
) -> None:
    def corrupt_root(
        observations: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        return [
            {**item, field: value} if item["name"] == ROOT_NAME else item
            for item in observations
        ]

    receipt, _client, _clock = _run(
        credential_file,
        client_options={"mutator": corrupt_root},
    )

    assert receipt["status"] == "failed"
    assert value not in json.dumps(receipt, sort_keys=True)


def test_zero_ambient_parent_is_rejected(credential_file: Path) -> None:
    def add_zero_parent(
        observations: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        return [
            {**item, "parent_observation_id": "0" * 16}
            if item["name"] == ROOT_NAME
            else item
            for item in observations
        ]

    receipt, _client, _clock = _run(
        credential_file,
        client_options={"mutator": add_zero_parent},
    )

    assert receipt["status"] == "failed"
    assert receipt["failed_assertions"] == ["root_shape"]


def test_malformed_io_names_fixed_fields_without_remote_values(
    credential_file: Path,
) -> None:
    remote_value = "remote-private-io-value"

    def corrupt_io(
        observations: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        return [
            {**item, "input": None}
            if item["name"] == ROOT_NAME
            else {**item, "output": [remote_value]}
            for item in observations
        ]

    receipt, _client, _clock = _run(
        credential_file,
        client_options={"mutator": corrupt_io},
    )

    encoded = json.dumps(receipt, sort_keys=True)
    assert receipt["status"] == "failed"
    assert receipt["failure_category"] == "readback_privacy_failed"
    assert receipt["failed_assertions"] == [
        "generation_hash_only_io",
        "generation_output_object",
        "root_hash_only_io",
        "root_input_object",
    ]
    assert remote_value not in encoded


@pytest.mark.parametrize(
    "hostile_output",
    [
        '{"response_sha256":"remote-private-io-value","response_sha256":"'
        + "a" * 64
        + '"}',
        "[" * 2000 + '"remote-private-io-value"' + "]" * 2000,
        {"response_sha256": float("nan")},
        {"response_sha256": {"nested": "remote-private-io-value"}},
    ],
)
def test_hostile_json_io_names_fixed_fields_without_remote_values(
    credential_file: Path,
    hostile_output: Any,
) -> None:
    def corrupt_io(
        observations: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        return [
            {**item, "output": hostile_output}
            if item["name"] == GENERATION_NAME
            else item
            for item in observations
        ]

    receipt, _client, _clock = _run(
        credential_file,
        client_options={"mutator": corrupt_io},
    )

    encoded = json.dumps(receipt, sort_keys=True)
    assert receipt["status"] == "failed"
    assert receipt["failure_category"] == "readback_privacy_failed"
    assert receipt["failed_assertions"] == [
        "generation_hash_only_io",
        "generation_output_object",
    ]
    assert "remote-private-io-value" not in encoded


def test_malformed_remote_total_cost_is_categorical_and_never_escapes(
    credential_file: Path,
) -> None:
    remote_text = "remote-private-total-cost-text"

    def malformed_cost(
        observations: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        return [
            {**item, "total_cost": remote_text}
            if item["name"] == GENERATION_NAME
            else item
            for item in observations
        ]

    receipt, _client, _clock = _run(
        credential_file,
        client_options={"mutator": malformed_cost},
    )

    encoded = json.dumps(receipt, sort_keys=True)
    assert receipt["status"] == "failed"
    assert receipt["failure_category"] == "readback_privacy_failed"
    assert remote_text not in encoded
    assert "traceback" not in encoded.lower()


def test_oversized_remote_total_cost_is_categorical_and_never_escapes(
    credential_file: Path,
) -> None:
    oversized_cost = 10**10000

    def malformed_cost(
        observations: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        return [
            {**item, "total_cost": oversized_cost}
            if item["name"] == GENERATION_NAME
            else item
            for item in observations
        ]

    receipt, _client, _clock = _run(
        credential_file,
        client_options={"mutator": malformed_cost},
    )

    encoded = json.dumps(receipt, sort_keys=True)
    assert receipt["status"] == "failed"
    assert receipt["failure_category"] == "readback_privacy_failed"
    assert "traceback" not in encoded.lower()


def test_shutdown_failure_revokes_a_pass(credential_file: Path) -> None:
    receipt, _client, _clock = _run(
        credential_file,
        client_options={"shutdown_exception": True},
    )

    assert receipt["status"] == "failed"
    assert receipt["failure_category"] == "client_shutdown_failed"
    assert receipt["synthetic"]["passed"] is False


def test_invalid_release_and_credential_mode_fail_before_client(
    credential_file: Path,
) -> None:
    factory_calls = 0

    def factory(_config: Any) -> FakeLangfuse:
        nonlocal factory_calls
        factory_calls += 1
        raise AssertionError("client must not be constructed")

    invalid_release = execute_proof(
        credential_path=credential_file,
        release="not-a-commit",
        client_factory=factory,
    )
    credential_file.chmod(0o644)
    invalid_mode = execute_proof(
        credential_path=credential_file,
        release=RELEASE,
        client_factory=factory,
    )

    assert invalid_release["failure_category"] == "invalid_release"
    assert invalid_mode["failure_category"] == "credential_preflight_failed"
    assert factory_calls == 0


def test_receipt_is_new_private_and_never_overwritten(tmp_path: Path) -> None:
    path = tmp_path / "evidence" / "proof.json"
    receipt = {
        "schema": "test",
        "status": "failed",
        "failure_category": "auth_check_failed",
    }

    digest = write_receipt(path, receipt)

    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert digest == hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(FileExistsError):
        write_receipt(path, {"status": "passed"})
    assert json.loads(path.read_text(encoding="utf-8")) == receipt


def test_receipt_refuses_existing_symlink(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.write_text("untouched", encoding="utf-8")
    path = tmp_path / "proof.json"
    path.symlink_to(target)

    with pytest.raises(FileExistsError):
        write_receipt(path, {"status": "passed"})

    assert target.read_text(encoding="utf-8") == "untouched"


def test_environment_is_fixed(credential_file: Path) -> None:
    receipt, client, _clock = _run(credential_file)

    assert receipt["environment"] == ENVIRONMENT
    assert all(item["environment"] == ENVIRONMENT for item in client.observations)


def test_shared_client_factory_has_bounded_transport_timeout(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    def fake_langfuse(**kwargs: Any) -> object:
        captured.update(kwargs)
        return object()

    import langfuse

    monkeypatch.setattr(langfuse, "Langfuse", fake_langfuse)
    config = TraceConfig(
        enabled=True,
        public_key="pk-synthetic",
        secret_key="sk-synthetic",
        base_url="https://example.invalid",
        release=RELEASE,
        environment=ENVIRONMENT,
    )

    create_langfuse_client(config)

    assert captured["timeout"] == LANGFUSE_REQUEST_TIMEOUT_SECONDS
    assert captured["release"] == RELEASE
    assert captured["environment"] == ENVIRONMENT
    assert callable(captured["mask_otel_spans"])
