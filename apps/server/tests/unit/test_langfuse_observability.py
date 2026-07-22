from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from twobrain_rec_server.observability.langfuse import (
    GenerationTraceContext,
    _GrafLangfuseIdGenerator,
    deterministic_observation_id,
    deterministic_trace_id,
    publish_completed_generation,
    workflow_dispatch_observation,
)
from twobrain_rec_server.workflows.temporal_client import outcome_tracing_interceptor


@dataclass
class _Call:
    trace_id: str
    observation_id: str
    candidate_id: UUID
    meeting_id: UUID
    workspace_id: UUID
    provider_attempt: int
    call_sequence: int
    started_at: datetime
    completed_at: datetime
    actual_model: str | None
    actual_provider: str | None
    token_usage: dict[str, object] | None
    cost_details: dict[str, object] | None
    request_json: object
    transcript_text: str
    raw_response_json: object
    validated_result_json: object


class _Observation:
    def __init__(self, owner, kind: str, kwargs: dict[str, object]) -> None:
        self.owner = owner
        self.kind = kind
        self.kwargs = kwargs
        self.ended: list[int | None] = []

    def start_observation(self, **kwargs):
        child = _Observation(self.owner, "generation", kwargs)
        self.owner.children.append(child)
        return child

    def update(self, **kwargs):
        self.owner.root_update = kwargs

    def end(self, *, end_time=None):
        self.ended.append(end_time)


class _Client:
    def __init__(self) -> None:
        self.roots: list[_Observation] = []
        self.children: list[_Observation] = []
        self.flush_count = 0

    def start_observation(self, **kwargs):
        root = _Observation(self, "chain", kwargs)
        self.roots.append(root)
        return root

    def flush(self):
        self.flush_count += 1


def test_sole_publisher_emits_one_full_content_generation_with_exact_or_unknown_usage() -> None:
    candidate_id = UUID("11111111-1111-1111-1111-111111111111")
    started = datetime.now(UTC) - timedelta(seconds=2)
    call = _Call(
        trace_id=deterministic_trace_id(candidate_id),
        observation_id=deterministic_observation_id(
            candidate_id, provider_attempt=1, call_sequence=1
        ),
        candidate_id=candidate_id,
        meeting_id=UUID("22222222-2222-2222-2222-222222222222"),
        workspace_id=UUID("33333333-3333-3333-3333-333333333333"),
        provider_attempt=1,
        call_sequence=1,
        started_at=started,
        completed_at=started + timedelta(seconds=1),
        actual_model="actual-model",
        actual_provider="provider",
        token_usage={
            "prompt_tokens": 10,
            "completion_tokens": 7,
            "total_tokens": 17,
            "prompt_tokens_details": {"cached_tokens": 3},
            "unknown": "not-fabricated",
        },
        cost_details=None,
        request_json={"messages": [{"content": "full request"}]},
        transcript_text="full transcript",
        raw_response_json={"raw": "full response"},
        validated_result_json={"validated": "full result"},
    )
    client = _Client()
    publish_completed_generation(
        client,
        call=call,
        context=GenerationTraceContext(
            environment="production",
            selected_model="selected-route",
            prompt_name="graf/meeting-outcome/auto",
            prompt_version=4,
            user_id="user",
            session_id="meeting",
            activity_attempt=2,
            temporal_workflow_id="outcome-generation/candidate",
            temporal_run_id="run",
            temporal_activity_id="publish-observability",
        ),
        prompt=object(),
    )
    assert len(client.roots) == 1
    assert len(client.children) == 0
    assert "trace_context" not in client.roots[0].kwargs
    generation = client.roots[0].kwargs
    assert generation["as_type"] == "generation"
    assert generation["name"] == "call-outcome-model"
    assert generation["input"] == {"request": call.request_json}
    assert "transcript" not in generation["input"]
    assert generation["output"] == {
        "raw_response": call.raw_response_json,
        "validated_result": call.validated_result_json,
    }
    assert generation["usage_details"] == {
        "prompt_tokens": 10,
        "completion_tokens": 7,
        "total_tokens": 17,
        "prompt_tokens_details": {"cached_tokens": 3},
    }
    assert generation["cost_details"] is None
    assert generation["metadata"]["temporal_workflow_id"] == "outcome-generation/candidate"
    assert generation["metadata"]["temporal_run_id"] == "run"
    assert generation["metadata"]["temporal_activity_id"] == "publish-observability"
    assert client.flush_count == 1


def test_temporal_dispatch_reuses_trace_and_propagates_w3c_attributes() -> None:
    from langfuse._client.propagation import _get_propagated_attributes_from_context
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
    from opentelemetry.trace import SpanKind

    exporter = InMemorySpanExporter()
    provider = TracerProvider(id_generator=_GrafLangfuseIdGenerator())
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    tracer = provider.get_tracer("langfuse-sdk")

    class _CurrentObservationClient:
        @contextmanager
        def start_as_current_observation(self, **kwargs):
            with tracer.start_as_current_span(kwargs["name"]) as span:
                yield span

    seed = "outcome-generation/11111111-1111-1111-1111-111111111111"
    interceptor = outcome_tracing_interceptor(tracer)
    with workflow_dispatch_observation(
        _CurrentObservationClient(),
        seed=seed,
        trace_name="generate-meeting-outcome",
        input_value={"candidate_id": seed.removeprefix("outcome-generation/")},
        environment="test",
        user_id="user-1",
        session_id="meeting-1",
        tags=["feature:recording-workflows"],
    ):
        headers = interceptor._context_to_headers({})
        carrier = interceptor.payload_converter.from_payloads([headers[interceptor.header_key]])[0]
        assert set(carrier) == {"traceparent", "baggage"}
        assert "langfuse_user_id=user-1" in carrier["baggage"]
        assert "langfuse_session_id=meeting-1" in carrier["baggage"]
        assert "langfuse_environment=test" in carrier["baggage"]
        extracted_context = interceptor._context_from_headers(headers)

    assert extracted_context is not None
    propagated = _get_propagated_attributes_from_context(extracted_context)
    assert propagated["langfuse.trace.tags"] == ["feature:recording-workflows"]
    assert propagated["langfuse.trace.name"] == "generate-meeting-outcome"
    with tracer.start_as_current_span(
        "StartWorkflow:OutcomeGenerationWorkflow",
        attributes=propagated,
        kind=SpanKind.CLIENT,
        context=extracted_context,
    ):
        pass

    spans = {span.name: span for span in exporter.get_finished_spans()}
    root = spans["generate-meeting-outcome"]
    started = spans["StartWorkflow:OutcomeGenerationWorkflow"]
    assert started.context.trace_id == root.context.trace_id
    assert started.parent is not None and started.parent.span_id == root.context.span_id
    assert started.attributes["langfuse.trace.tags"] == ("feature:recording-workflows",)
    assert started.attributes["langfuse.trace.name"] == "generate-meeting-outcome"
    assert root.context.trace_id == int(deterministic_trace_id(seed.split("/", 1)[1]), 16)
