from __future__ import annotations

from collections.abc import Mapping
from contextlib import contextmanager, suppress
from contextvars import ContextVar, Token
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Any, Protocol

from twobrain_rec_server.config import Settings

_forced_trace_id: ContextVar[int | None] = ContextVar("graf_langfuse_trace_id", default=None)
_forced_span_ids: ContextVar[tuple[int, ...]] = ContextVar("graf_langfuse_span_ids", default=())
_BLOCKED_INSTRUMENTATION_SCOPES = {
    "opentelemetry.instrumentation.fastapi",
    "opentelemetry.instrumentation.httpx",
    "opentelemetry.instrumentation.sqlalchemy",
}
# Keep this predicate dependency-free.  The Temporal tracing interceptor invokes
# it from workflow sandbox code; importing the Langfuse SDK there pulls in
# urllib and is rejected by the sandbox.  These are the Langfuse SDK's stable
# default LLM/GenAI scope prefixes (Langfuse 4.x).
_LANGFUSE_TRACER_SCOPE = "langfuse-sdk"
_KNOWN_LLM_SCOPE_PREFIXES = frozenset(
    {
        _LANGFUSE_TRACER_SCOPE,
        "agent_framework",
        "autogen-core",
        "ai",
        "haystack",
        "langsmith",
        "litellm",
        "openinference",
        "opentelemetry.instrumentation.openai",
        "opentelemetry.instrumentation.anthropic",
        "opentelemetry.instrumentation.agno",
        "opentelemetry.instrumentation.alephalpha",
        "opentelemetry.instrumentation.bedrock",
        "opentelemetry.instrumentation.cohere",
        "opentelemetry.instrumentation.crewai",
        "opentelemetry.instrumentation.google_generativeai",
        "opentelemetry.instrumentation.groq",
        "opentelemetry.instrumentation.haystack",
        "opentelemetry.instrumentation.mistralai",
        "opentelemetry.instrumentation.langchain",
        "opentelemetry.instrumentation.llamaindex",
        "opentelemetry.instrumentation.ollama",
        "opentelemetry.instrumentation.openai_agents",
        "opentelemetry.instrumentation.openai_v2",
        "opentelemetry.instrumentation.replicate",
        "opentelemetry.instrumentation.sagemaker",
        "opentelemetry.instrumentation.together",
        "opentelemetry.instrumentation.transformers",
        "opentelemetry.instrumentation.vertexai",
        "opentelemetry.instrumentation.voyageai",
        "opentelemetry.instrumentation.watsonx",
        "opentelemetry.instrumentation.writer",
        "pydantic-ai",
        "strands-agents",
        "vllm",
    }
)
_OPENAI_USAGE_FIELDS = {
    "prompt_tokens",
    "completion_tokens",
    "total_tokens",
    "prompt_tokens_details",
    "completion_tokens_details",
}
_OPENAI_PROMPT_TOKEN_DETAIL_FIELDS = {"cached_tokens", "audio_tokens"}
_OPENAI_COMPLETION_TOKEN_DETAIL_FIELDS = {
    "accepted_prediction_tokens",
    "audio_tokens",
    "reasoning_tokens",
    "rejected_prediction_tokens",
}


class CompletedGenerationCall(Protocol):
    trace_id: str
    observation_id: str
    candidate_id: object
    meeting_id: object
    workspace_id: object
    provider_attempt: int
    call_sequence: int
    started_at: datetime
    completed_at: datetime | None
    actual_model: str | None
    actual_provider: str | None
    token_usage: Mapping[str, object] | None
    cost_details: Mapping[str, object] | None
    request_json: object
    transcript_text: str
    raw_response_json: object
    validated_result_json: object


@dataclass(frozen=True, slots=True)
class GenerationTraceContext:
    environment: str
    selected_model: str
    prompt_name: str
    prompt_version: int
    prompt_hash: str | None = None
    user_id: str | None = None
    session_id: str | None = None
    activity_attempt: int = 1
    temporal_workflow_id: str | None = None
    temporal_run_id: str | None = None
    temporal_activity_id: str | None = None


def deterministic_trace_id(candidate_id: object) -> str:
    from langfuse import Langfuse

    return Langfuse.create_trace_id(seed=f"outcome-generation/{candidate_id}")


def deterministic_observation_id(
    candidate_id: object,
    *,
    provider_attempt: int,
    call_sequence: int,
) -> str:
    seed = f"outcome-generation/{candidate_id}/{provider_attempt}/{call_sequence}"
    return sha256(seed.encode("utf-8")).digest()[:8].hex()


def deterministic_workflow_root_id(seed: str) -> str:
    return sha256(f"{seed}/root".encode()).digest()[:8].hex()


class _GrafLangfuseIdGenerator:
    """Use call-scoped deterministic IDs without changing unrelated OTel spans."""

    def __init__(self) -> None:
        from opentelemetry.sdk.trace.id_generator import RandomIdGenerator

        self._fallback = RandomIdGenerator()

    def generate_trace_id(self) -> int:
        value = _forced_trace_id.get()
        return value if value is not None else self._fallback.generate_trace_id()

    def generate_span_id(self) -> int:
        values = _forced_span_ids.get()
        if not values:
            return self._fallback.generate_span_id()
        _forced_span_ids.set(values[1:])
        return values[0]

    def is_trace_id_random(self) -> bool:
        return _forced_trace_id.get() is None


class _DeterministicIdScope:
    def __init__(self, *, trace_id: str, span_ids: tuple[str, ...]) -> None:
        self._trace_id = int(trace_id, 16)
        self._span_ids = tuple(int(value, 16) for value in span_ids)
        self._trace_token: Token[int | None] | None = None
        self._span_token: Token[tuple[int, ...]] | None = None

    def __enter__(self) -> None:
        self._trace_token = _forced_trace_id.set(self._trace_id)
        self._span_token = _forced_span_ids.set(self._span_ids)

    def __exit__(self, *_exc: object) -> None:
        if self._span_token is not None:
            _forced_span_ids.reset(self._span_token)
        if self._trace_token is not None:
            _forced_trace_id.reset(self._trace_token)


@contextmanager
def deterministic_observation_scope(*, trace_id: str, observation_id: str):
    """Assign stable OTel IDs while preserving any current distributed parent."""
    with _DeterministicIdScope(trace_id=trace_id, span_ids=(observation_id,)):
        yield


def create_langfuse_client(settings: Settings) -> Any:
    from langfuse import Langfuse

    return Langfuse(
        public_key=_read_required_secret(settings.langfuse_public_key_file),
        secret_key=_read_required_secret(settings.langfuse_secret_key_file),
        base_url=str(settings.langfuse_base_url).rstrip("/"),
        environment=settings.langfuse_environment,
        release=settings.langfuse_release,
        tracing_enabled=True,
        mask=None,
        should_export_span=_should_export_langfuse_span,
        id_generator=_GrafLangfuseIdGenerator(),
    )


def _should_export_langfuse_span(span: Any) -> bool:
    scope = getattr(span, "instrumentation_scope", None)
    scope_name = getattr(scope, "name", None)
    if scope_name in _BLOCKED_INSTRUMENTATION_SCOPES:
        return False
    if scope_name is not None and any(
        scope_name == prefix or scope_name.startswith(f"{prefix}.")
        for prefix in _KNOWN_LLM_SCOPE_PREFIXES
    ):
        return True
    attributes = getattr(span, "attributes", None) or {}
    return any(isinstance(key, str) and key.startswith("gen_ai") for key in attributes)


def langfuse_otel_tracer(client: Any) -> Any:
    """Return the tracer owned by the client's shared Langfuse provider."""
    resources = getattr(client, "_resources", None)
    tracer = getattr(resources, "tracer", None)
    if tracer is None:
        raise RuntimeError("Langfuse tracer provider is unavailable")
    return tracer


@contextmanager
def workflow_dispatch_observation(
    client: Any,
    *,
    seed: str,
    trace_name: str,
    input_value: Mapping[str, object],
    environment: str,
    user_id: str | None,
    session_id: str | None,
    tags: list[str],
) -> Any:
    """Create a deterministic current root for one traced Temporal workflow."""
    from langfuse import Langfuse, propagate_attributes

    with (
        _DeterministicIdScope(
            trace_id=Langfuse.create_trace_id(seed=seed),
            span_ids=(deterministic_workflow_root_id(seed),),
        ),
        propagate_attributes(
            user_id=user_id,
            session_id=session_id,
            environment=environment,
            tags=tags,
            trace_name=trace_name,
            as_baggage=True,
        ),
        client.start_as_current_observation(
            name=trace_name,
            as_type="chain",
            input=input_value,
        ) as observation,
    ):
        yield observation


def fetch_prompt_by_label(
    client: Any, *, name: str, prompt_type: str, label: str = "production"
) -> Any:
    if prompt_type not in {"chat", "text"}:
        raise ValueError("unsupported Langfuse prompt type")
    return client.get_prompt(
        name,
        label=label,
        type=prompt_type,
        cache_ttl_seconds=60,
        max_retries=0,
        fetch_timeout_seconds=10,
    )


def publish_completed_generation(
    client: Any,
    *,
    call: CompletedGenerationCall,
    context: GenerationTraceContext,
    prompt: Any | None,
) -> None:
    """Publish one completed provider call; caller owns durable pending/confirmed state."""
    from langfuse import propagate_attributes

    if call.completed_at is None:
        raise ValueError("only completed generation calls can be published")
    usage_details = _usage_details(call.token_usage)
    cost_details = _float_mapping(call.cost_details)
    tags = [
        "feature:recording-workflows",
        "operation:meeting-outcome",
        f"activity-attempt:{context.activity_attempt}",
    ]
    metadata = {
        "candidate_id": str(call.candidate_id),
        "meeting_id": str(call.meeting_id),
        "workspace_id": str(call.workspace_id),
        "observation_id": call.observation_id,
        "provider_attempt": call.provider_attempt,
        "call_sequence": call.call_sequence,
        "activity_attempt": context.activity_attempt,
        "prompt_name": context.prompt_name,
        "prompt_version": context.prompt_version,
        "prompt_hash": context.prompt_hash,
        "selected_model": context.selected_model,
        "actual_model": call.actual_model,
        "actual_provider": call.actual_provider,
        "original_started_at": call.started_at.isoformat(),
        "original_completed_at": call.completed_at.isoformat(),
        "temporal_workflow_id": context.temporal_workflow_id,
        "temporal_run_id": context.temporal_run_id,
        "temporal_activity_id": context.temporal_activity_id,
    }
    with (
        _DeterministicIdScope(
            trace_id=call.trace_id,
            span_ids=(call.observation_id,),
        ),
        propagate_attributes(
            user_id=context.user_id,
            session_id=context.session_id,
            environment=context.environment,
            tags=tags,
            trace_name="generate-meeting-outcome",
            prompt=prompt,
            as_baggage=False,
        ),
    ):
        generation = client.start_observation(
            name="call-outcome-model",
            as_type="generation",
            input={"request": call.request_json},
            output={
                "raw_response": call.raw_response_json,
                "validated_result": call.validated_result_json,
            },
            metadata=metadata,
            model=call.actual_model or context.selected_model,
            model_parameters=_model_parameters(call.request_json),
            usage_details=usage_details or None,
            cost_details=cost_details or None,
            prompt=prompt,
            completion_start_time=call.started_at,
        )
        _set_original_start_time(generation, call.started_at)
        generation.end(end_time=_nanoseconds(call.completed_at))
    client.flush()


def shutdown_langfuse(client: Any) -> None:
    # Langfuse v4 shares one resource manager per public key. Activity-local
    # clients therefore share the worker's Temporal tracer provider; shutting
    # one down would disable tracing for every later activity in that process.
    # The SDK's atexit hook owns process shutdown, while call sites flush.
    with suppress(Exception):
        client.flush()


def _read_required_secret(path: Path | None) -> str:
    if path is None:
        raise RuntimeError("Langfuse credential file is not configured")
    value = path.read_text(encoding="utf-8").strip()
    if not value:
        raise RuntimeError("Langfuse credential file is empty")
    return value


def _nanoseconds(value: datetime) -> int:
    return int(value.timestamp() * 1_000_000_000)


def _set_original_start_time(observation: Any, value: datetime) -> None:
    # Langfuse v4 exposes historical end_time but not start_time. The wrapped
    # SDK span is updated before end/export so delayed durable delivery keeps
    # the provider's original timing instead of the retry timestamp.
    otel_span = getattr(observation, "_otel_span", None)
    if otel_span is not None and hasattr(otel_span, "_start_time"):
        otel_span._start_time = _nanoseconds(value)


def _integer_mapping(value: Mapping[str, object] | None) -> dict[str, int]:
    if value is None:
        return {}
    return {
        key: item
        for key, item in value.items()
        if isinstance(item, int) and not isinstance(item, bool)
    }


def _usage_details(value: Mapping[str, object] | None) -> dict[str, Any]:
    if value is None:
        return {}
    if set(value) & {
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
    }:
        normalized: dict[str, Any] = _integer_mapping(
            {key: value[key] for key in _OPENAI_USAGE_FIELDS & set(value)}
        )
        detail_fields = {
            "prompt_tokens_details": _OPENAI_PROMPT_TOKEN_DETAIL_FIELDS,
            "completion_tokens_details": _OPENAI_COMPLETION_TOKEN_DETAIL_FIELDS,
        }
        for key, allowed_fields in detail_fields.items():
            details = value.get(key)
            if isinstance(details, Mapping):
                normalized[key] = _integer_mapping(
                    {field: details[field] for field in allowed_fields & set(details)}
                )
        return normalized
    return _integer_mapping(value)


def _float_mapping(value: Mapping[str, object] | None) -> dict[str, float]:
    if value is None:
        return {}
    return {
        key: float(item)
        for key, item in value.items()
        if isinstance(item, (int, float)) and not isinstance(item, bool)
    }


def _model_parameters(request: object) -> dict[str, str | int | float | bool | list[str] | None]:
    if not isinstance(request, Mapping):
        return {}
    allowed = {"temperature"}
    return {key: value for key, value in request.items() if key in allowed}  # type: ignore[return-value]
