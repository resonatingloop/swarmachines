"""offline contract proofs for task10 response capture and tracing."""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import runtime.adaption_adapter as adaption_module
from dataset_pack.budget import CreditBudget
from dataset_pack.configs import get_task_configs
from dataset_pack.package import package_dataset
from dataset_pack.run import GovernedRunner, _validate_model_call_events
from runtime.adaption_adapter import (
    AdaptionAdapter,
    IncompleteResponseError,
    ResponseShapeError,
)
from runtime.runner import TurnSeamRunner
from runtime.tracer import (
    FakeExporter,
    RunStatus,
    TelemetryFailure,
    TraceConfig,
    Tracer,
    _mask_otel_spans,
)


class FakeResponses:
    def __init__(self, response):
        self.response = response
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if isinstance(self.response, BaseException):
            raise self.response
        return self.response


class FakeClient:
    def __init__(self, response):
        self.responses = FakeResponses(response)


def _response(
    *,
    status: str = "completed",
    output_text: str = "visible answer",
    output=None,
    incomplete_reason: str | None = None,
    usage=None,
):
    return SimpleNamespace(
        id="resp-secret-id",
        model="glm-53-flash",
        status=status,
        output_text=output_text,
        output=output
        if output is not None
        else [
            SimpleNamespace(
                type="message",
                content=[SimpleNamespace(type="output_text")],
            )
        ],
        incomplete_details=(
            SimpleNamespace(reason=incomplete_reason)
            if incomplete_reason is not None
            else None
        ),
        usage=usage
        if usage is not None
        else SimpleNamespace(
            input_tokens=10,
            output_tokens=8,
            total_tokens=18,
            input_tokens_details=SimpleNamespace(cached_tokens=2),
            output_tokens_details=SimpleNamespace(reasoning_tokens=3),
        ),
        estimated_credits_consumed="0.00001",
    )


def _adapter(response):
    return AdaptionAdapter(client=FakeClient(response))


def test_completed_visible_response_preserves_bounded_shape():
    response = _adapter(_response()).simple_prompt(
        "glm-53-flash",
        "private prompt",
        max_output_tokens=4096,
    )
    response.validate_complete()
    assert response.output_text == "visible answer"
    assert (
        response.diagnostics.response_id_sha256
        == hashlib.sha256(b"resp-secret-id").hexdigest()
    )
    assert response.diagnostics.output_item_type_counts == {"message": 1}
    assert response.diagnostics.message_content_type_counts == {"output_text": 1}
    assert response.usage.reasoning_tokens == 3
    assert "resp-secret-id" not in repr(response)


@pytest.mark.parametrize(
    ("provider_response", "category"),
    [
        (
            _response(
                status="incomplete",
                output_text="",
                incomplete_reason="max_output_tokens",
                output=[SimpleNamespace(type="reasoning", content=[])],
            ),
            "response_not_completed",
        ),
        (
            _response(
                status="completed",
                output_text="",
                output=[SimpleNamespace(type="reasoning", content=[])],
            ),
            "empty_visible_response",
        ),
        (
            _response(
                status="completed",
                output_text="",
                output=[
                    SimpleNamespace(
                        type="message",
                        content=[SimpleNamespace(type="refusal")],
                    )
                ],
            ),
            "empty_visible_response",
        ),
    ],
)
def test_nonanswers_fail_closed(provider_response, category):
    response = _adapter(provider_response).simple_prompt("glm-53-flash", "prompt")
    with pytest.raises(IncompleteResponseError, match=category):
        response.validate_complete()


def test_malformed_usage_fails_without_provider_text():
    malformed = _response(
        usage=SimpleNamespace(
            input_tokens="ten",
            output_tokens=8,
            total_tokens=18,
        )
    )
    with pytest.raises(ResponseShapeError, match="malformed_usage"):
        _adapter(malformed).simple_prompt("glm-53-flash", "prompt")


def _write_credentials(path: Path, mode: int = 0o600) -> None:
    path.write_text(
        "LANGFUSE_BASE_URL=https://cloud.langfuse.com\n"
        "LANGFUSE_PUBLIC_KEY=test-public-key\n"
        "LANGFUSE_SECRET_KEY=test-secret-key\n",
        encoding="utf-8",
    )
    path.chmod(mode)


def test_credential_loader_is_explicit_private_and_non_symlink():
    with tempfile.TemporaryDirectory() as root:
        credential = Path(root) / "trace.token"
        _write_credentials(credential)
        config = TraceConfig.from_file(credential, release="test")
        assert config.enabled
        assert config.strict

        credential.chmod(0o640)
        with pytest.raises(PermissionError):
            TraceConfig.from_file(credential, release="test")

        credential.chmod(0o600)
        link = Path(root) / "linked.token"
        link.symlink_to(credential)
        with pytest.raises(ValueError, match="non-symlink"):
            TraceConfig.from_file(link, release="test")


def test_credential_loader_accepts_literal_outer_quotes_only():
    with tempfile.TemporaryDirectory() as root:
        credential = Path(root) / "trace.token"
        credential.write_text(
            'LANGFUSE_BASE_URL="https://cloud.langfuse.com"\n'
            "LANGFUSE_PUBLIC_KEY='test-public-key'\n"
            'LANGFUSE_SECRET_KEY="test-secret-key"\n',
            encoding="utf-8",
        )
        credential.chmod(0o600)

        config = TraceConfig.from_file(credential, release="test")
        assert config.base_url == "https://cloud.langfuse.com"
        assert config.public_key == "test-public-key"
        assert config.secret_key == "test-secret-key"

        credential.write_text(
            'LANGFUSE_BASE_URL="https://cloud.langfuse.com\n'
            "LANGFUSE_PUBLIC_KEY='test-public-key'\n"
            'LANGFUSE_SECRET_KEY="test-secret-key"\n',
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="invalid quoting"):
            TraceConfig.from_file(credential, release="test")

        credential.write_text(
            'LANGFUSE_BASE_URL="https://cloud.langfuse.com"\n'
            "LANGFUSE_PUBLIC_KEY=''\n"
            'LANGFUSE_SECRET_KEY="test-secret-key"\n',
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="empty field"):
            TraceConfig.from_file(credential, release="test")


def test_generation_exports_hashes_only_and_flushes_strictly():
    exporter = FakeExporter()
    tracer = Tracer(
        TraceConfig(enabled=True, strict=True),
        exporter=exporter,
    )
    tracer.start_trace("private-run-id", condition="mesh", seed=1)
    with tracer.generation(
        call_id="private-call-id",
        model_id="glm-53-flash",
        prompt="private prompt",
        metadata={
            "turn": 1,
            "phase": "observe",
            "agent_id": "a",
            "source_event_type": "observation.recorded",
            "unknown_private_field": "must not cross",
        },
    ) as generation:
        generation.complete(
            response_sha256=hashlib.sha256(b"private answer").hexdigest(),
            diagnostics={
                "status": "completed",
                "provider_error_text": "must not cross",
                "categorical_error": "arbitrary-class-name",
            },
            usage_details={"input": 10, "output": 5, "total": 15},
            cost_details={"total": 0.00001},
            latency_ms=2.0,
            terminal_state="completed",
        )
    tracer.end_trace(status=RunStatus.COMPLETED)

    encoded = repr(exporter.traces + exporter.generations)
    assert "private prompt" not in encoded
    assert "private answer" not in encoded
    assert "private-call-id" not in encoded
    assert "private-run-id" not in encoded
    assert "must not cross" not in encoded
    assert "arbitrary-class-name" not in encoded
    assert "unknown_private_field" not in encoded
    assert "provider_error_text" not in encoded
    assert exporter.flush_count == 2


def test_trace_boundary_drops_arbitrary_metadata_and_terminal_prose():
    exporter = FakeExporter()
    tracer = Tracer(TraceConfig(enabled=True), exporter=exporter)
    tracer.start_trace("run-secret", condition="ring-mute", seed=42)

    with tracer.span(
        "turn-1-observe",
        metadata={
            "turn": 1,
            "phase": "observe",
            "agent_id": "agent-a",
            "type": "agent_turn",
            "untrusted": "raw transcript fragment",
        },
    ):
        pass
    tracer.end_trace(RunStatus.FAILED, reason="raw exception text")

    assert exporter.spans[0]["metadata"] == {
        "turn": 1,
        "phase": "observe",
        "agent_id": "agent-a",
        "type": "agent_turn",
    }
    assert exporter.traces[-1]["output"]["reason_category"] == "other"
    assert "raw transcript fragment" not in repr(exporter.spans)
    assert "raw exception text" not in repr(exporter.traces)


def test_legacy_trace_methods_export_only_hashes_and_finite_categories():
    exporter = FakeExporter()
    tracer = Tracer(TraceConfig(enabled=True), exporter=exporter)
    private_model = "private-experimental-model"
    private_tool = "private-shell-tool"
    private_args = {"code": "print('private corpus fragment')"}
    private_result = {"stdout": "private model result"}
    private_error = "private provider exception text"

    tracer.record_model_call(
        private_model,
        prompt_tokens=-1,
        completion_tokens=5,
        total_tokens=10,
        latency_ms=2,
        error=private_error,
    )
    tracer.record_tool_call(
        private_tool,
        args=private_args,
        result=private_result,
        latency_ms=3,
        error=private_error,
    )

    encoded = repr(exporter.spans)
    for raw_value in (
        private_model,
        private_tool,
        private_args["code"],
        private_result["stdout"],
        private_error,
    ):
        assert raw_value not in encoded
    assert exporter.spans[0]["name"] == "model-call"
    assert exporter.spans[0]["metadata"]["model_id"] == "unknown"
    assert exporter.spans[0]["metadata"]["prompt_tokens"] == "unknown"
    assert exporter.spans[0]["metadata"]["error_category"] == "other"
    assert exporter.spans[1]["name"] == "tool-call"
    assert exporter.spans[1]["metadata"]["error_category"] == "other"
    for key in ("tool_name_sha256", "args_sha256", "result_sha256", "error_sha256"):
        assert len(exporter.spans[1]["metadata"][key]) == 64


def test_v5_export_mask_returns_attribute_patches():
    from langfuse.types import (
        MaskOtelSpansParams,
        OtelSpanData,
        OtelSpanIdentifier,
    )

    identifier = OtelSpanIdentifier(trace_id="0" * 32, span_id="1" * 16)
    span = OtelSpanData(
        trace_id=identifier.trace_id,
        span_id=identifier.span_id,
        parent_span_id=None,
        name="generation",
        instrumentation_scope_name="langfuse",
        instrumentation_scope_version="5.2.0",
        attributes={
            "gen_ai.prompt.0.content": "private prompt",
            "exception.message": "private provider text",
            "safe": "kept",
        },
        resource_attributes={},
    )
    result = _mask_otel_spans(params=MaskOtelSpansParams(spans={identifier: span}))
    patch = result.span_patches[identifier]
    assert patch is not None
    assert set(patch.delete_attributes) == {
        "gen_ai.prompt.0.content",
        "exception.message",
    }
    assert patch.set_attributes["swarmachines.masking_applied"] is True


def test_installed_langfuse_v5_surface_is_zero_network_and_metadata_only():
    from langfuse import Langfuse
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
        InMemorySpanExporter,
    )

    sink = InMemorySpanExporter()
    client = Langfuse(
        public_key="test-public-key",
        secret_key="test-secret-key",
        base_url="https://example.invalid",
        span_exporter=sink,
        mask_otel_spans=_mask_otel_spans,
    )
    tracer = Tracer(
        TraceConfig(enabled=True, strict=True),
        client=client,
    )
    tracer.start_trace("private-run", condition="mesh", seed=1)
    with tracer.generation(
        call_id="private-call",
        model_id="glm-53-flash",
        prompt="private prompt",
        metadata={"turn": 1, "agent_id": "a"},
    ) as generation:
        generation.complete(
            response_sha256=hashlib.sha256(b"private answer").hexdigest(),
            diagnostics={"status": "completed"},
            usage_details={"input": 10, "output": 5, "total": 15},
            cost_details={"total": 0.00001},
            latency_ms=1,
            terminal_state="completed",
        )
    tracer.record_model_call(
        "private-model-id",
        prompt_tokens=10,
        completion_tokens=5,
        total_tokens=15,
        error="private model error",
    )
    tracer.record_tool_call(
        "private-tool-name",
        args={"prompt": "private tool argument"},
        result={"answer": "private tool result"},
        error="private tool error",
    )
    tracer.end_trace(RunStatus.COMPLETED)
    exported = repr([span.attributes for span in sink.get_finished_spans()])
    assert "private prompt" not in exported
    assert "private answer" not in exported
    assert "private-call" not in exported
    assert "private-run" not in exported
    assert "private-model-id" not in exported
    assert "private model error" not in exported
    assert "private-tool-name" not in exported
    assert "private tool argument" not in exported
    assert "private tool result" not in exported
    assert "private tool error" not in exported


def test_disabled_tracing_is_byte_identical_to_absent_tracing():
    args = {
        "seed": 91,
        "comm_topology": "mesh",
        "agents_config": ["a", "b"],
        "disturbance_schedule": {},
    }
    absent = TurnSeamRunner(**args).run(2)
    disabled = TurnSeamRunner(
        **args,
        tracer=Tracer(TraceConfig(enabled=False)),
    ).run(2)
    assert absent == disabled


def test_strict_flush_failure_stops_after_one_generation():
    exporter = FakeExporter()
    exporter.fail_flush = True
    tracer = Tracer(
        TraceConfig(enabled=True, strict=True),
        exporter=exporter,
    )
    tracer.start_trace("run", seed=1)
    with (
        pytest.raises(TelemetryFailure, match="trace_flush_failed"),
        tracer.generation(
            call_id="call",
            model_id="glm-53-flash",
            prompt="prompt",
            metadata={},
        ) as generation,
    ):
        generation.complete(
            response_sha256=None,
            diagnostics={"status": "incomplete"},
            usage_details={"input": 1, "output": 0, "total": 1},
            cost_details=None,
            latency_ms=1,
            terminal_state="rejected",
        )
    assert len(exporter.generations) == 1
    assert exporter.flush_count == 1


def test_governed_call_uses_exact_visible_response_contract():
    client = FakeClient(_response())
    adapter = AdaptionAdapter(client=client)
    exporter = FakeExporter()
    tracer = Tracer(TraceConfig(enabled=True, strict=True), exporter=exporter)
    config = get_task_configs()[0]
    budget = CreditBudget("10", max_calls=1)
    with tempfile.TemporaryDirectory() as root:
        runner = GovernedRunner(
            root,
            config,
            dry_run=False,
            budget=budget,
            tracer=tracer,
        )
        tracer.start_trace(runner.run_id, condition="none", seed=config.seed)
        record = runner._capture_live_event(
            adapter,
            1,
            "a",
            "observation.recorded",
            {"visible": {"freight": "fictional"}},
        )
    assert record is not None
    assert record.response_full == "visible answer"
    assert len(client.responses.calls) == 1
    request = client.responses.calls[0]
    assert request["max_output_tokens"] == 4096
    assert request["tools"] == []
    assert request["tool_choice"] == "none"
    assert request["agentic_memory"] is False
    assert request["store"] is False
    assert "at most 120 visible words" in request["instructions"]
    assert request["traceparent"].startswith("00-")
    assert budget.calls_completed == 1


def test_interruption_is_not_retried_and_is_accounted_once():
    client = FakeClient(KeyboardInterrupt())
    adapter = AdaptionAdapter(client=client)
    tracer = Tracer(
        TraceConfig(enabled=True, strict=True),
        exporter=FakeExporter(),
    )
    config = get_task_configs()[0]
    budget = CreditBudget("10", max_calls=1)
    with tempfile.TemporaryDirectory() as root:
        runner = GovernedRunner(
            root,
            config,
            dry_run=False,
            budget=budget,
            tracer=tracer,
        )
        tracer.start_trace(runner.run_id, seed=config.seed)
        with pytest.raises(KeyboardInterrupt):
            runner._capture_live_event(
                adapter,
                1,
                "a",
                "observation.recorded",
                {"visible": {}},
            )
    assert len(client.responses.calls) == 1
    assert budget.calls_started == 1
    assert budget.calls_failed == 1
    assert len(runner.call_records) == 1
    assert runner.call_records[0].categorical_error == "provider_transport_error"


def test_timeout_is_categorical_and_does_not_persist_provider_text():
    private_error_text = "private timeout transport detail"
    client = FakeClient(TimeoutError(private_error_text))
    adapter = AdaptionAdapter(client=client)
    tracer = Tracer(
        TraceConfig(enabled=True, strict=True),
        exporter=FakeExporter(),
    )
    config = get_task_configs()[0]
    budget = CreditBudget("10", max_calls=1)
    with tempfile.TemporaryDirectory() as root:
        runner = GovernedRunner(
            root,
            config,
            dry_run=False,
            budget=budget,
            tracer=tracer,
        )
        tracer.start_trace(runner.run_id, seed=config.seed)
        with pytest.raises(TimeoutError):
            runner._capture_live_event(
                adapter,
                1,
                "a",
                "observation.recorded",
                {"visible": {}},
            )
    persisted = runner.call_records[0].to_jsonl_line()
    assert runner.call_records[0].categorical_error == "provider_transport_error"
    assert private_error_text not in persisted
    assert len(client.responses.calls) == 1


def test_failed_call_is_one_source_linked_event_in_a_sealed_failed_run(monkeypatch):
    adapter = _adapter(
        _response(
            status="incomplete",
            output_text="",
            output=[SimpleNamespace(type="reasoning", content=[])],
            incomplete_reason="max_output_tokens",
        )
    )
    monkeypatch.setattr(adaption_module, "AdaptionAdapter", lambda: adapter)
    exporter = FakeExporter()
    tracer = Tracer(TraceConfig(enabled=True, strict=True), exporter=exporter)
    config = replace(get_task_configs()[0], turns=1)
    budget = CreditBudget("10", max_calls=1)

    with tempfile.TemporaryDirectory() as root:
        runner = GovernedRunner(
            root,
            config,
            dry_run=False,
            budget=budget,
            tracer=tracer,
        )
        with pytest.raises(IncompleteResponseError):
            runner.run_full_workflow()

        events_path = Path(root) / runner.run_id / "logs" / "events.jsonl"
        events = [
            json.loads(line)
            for line in events_path.read_text(encoding="utf-8").splitlines()
        ]
        failures = [event for event in events if event["type"] == "model.call.failed"]
        assert len(failures) == 1
        failure = failures[0]
        source = events[failure["payload"]["source_event_seq"]]
        assert failure["seq"] == source["seq"] + 1
        assert source["type"] == failure["payload"]["source_event_type"]
        assert failure["payload"]["response_status"] == "incomplete"
        assert failure["payload"]["incomplete_reason"] == "max_output_tokens"
        assert failure["payload"]["categorical_error"] == "response_not_completed"
        assert events[-1]["type"] == "run.seal"
        _validate_model_call_events(events)

        run_metadata = json.loads(
            (Path(root) / runner.run_id / "run.json").read_text(encoding="utf-8")
        )
        assert run_metadata["status"] == "failed"
        assert run_metadata["calls_count"] == 1

    assert budget.calls_started == 1
    assert budget.calls_failed == 1
    assert len(exporter.generations) == 1


def test_package_boundary_recomputes_source_seals():
    config = replace(get_task_configs()[0], turns=1)
    with tempfile.TemporaryDirectory() as root:
        root_path = Path(root)
        result = GovernedRunner(
            str(root_path / "runs"),
            config,
            dry_run=True,
        ).run_full_workflow()
        events_path = Path(result["events_jsonl"])
        events = [
            json.loads(line)
            for line in events_path.read_text(encoding="utf-8").splitlines()
        ]
        model_call = next(event for event in events if event["type"] == "model.call")
        model_call["payload"]["response"] += " tampered"
        events_path.write_text(
            "\n".join(json.dumps(event) for event in events) + "\n",
            encoding="utf-8",
        )
        with pytest.raises(ValueError):
            package_dataset(
                str(root_path / "runs"),
                str(root_path / "pack"),
            )
