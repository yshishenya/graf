from __future__ import annotations

import json
import re
from contextlib import nullcontext
from dataclasses import dataclass
from datetime import timedelta
from typing import Any
from uuid import UUID

from twobrain_rec_server.auth.context import TenantScope
from twobrain_rec_server.config import Settings

WORKFLOW_ID_PATTERN = re.compile(
    r"^processing/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}(?:/(?:[2-9]|[1-9][0-9]+))?$"
)
PLAYBACK_NORMALIZATION_WORKFLOW_ID_PATTERN = re.compile(
    r"^playback-normalization/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/v1$"
)
OUTCOME_GENERATION_WORKFLOW_ID_PATTERN = re.compile(
    r"^outcome-generation/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)
INVITATION_DELIVERY_WORKFLOW_ID_PATTERN = re.compile(
    r"^share-invitation/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)
ACCOUNT_CREATED_EMAIL_WORKFLOW_ID_PATTERN = re.compile(
    r"^share-account-created/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)
PROMPT_OPTIMIZATION_WORKFLOW_ID_PATTERN = re.compile(
    r"^prompt-optimization/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)
PROMPT_ROLLBACK_WORKFLOW_ID_PATTERN = re.compile(
    r"^prompt-rollback/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/[1-9][0-9]*$"
)
SAFE_WORKER_HOSTNAME = re.compile(r"[^a-zA-Z0-9._-]+")
PROCESSING_WORKER_IDENTITY_PREFIX = "graf-processing:"


@dataclass(frozen=True, slots=True)
class ProcessingWorkflowStart:
    workflow_id: str
    run_id: str | None = None
    reused: bool = False


@dataclass(frozen=True, slots=True)
class ProcessingManualCheckDispatch:
    dispatch: str


def _temporal_update_fallback_allowed(exc: BaseException) -> bool:
    """Fallback only for an explicitly unsupported/unknown Update handler."""

    current: BaseException | None = exc
    seen: set[int] = set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        name = current.__class__.__name__.lower()
        message = str(current).lower()
        if isinstance(current, NotImplementedError):
            return True
        if any(
            marker in name
            for marker in ("updateunsupported", "updatenotsupported", "updatenotfound")
        ):
            return True
        if any(
            marker in message
            for marker in (
                "unknown update",
                "unknown update handler",
                "update handler not found",
                "update not found",
                "unsupported update",
                "update not supported",
                "unimplemented update",
            )
        ):
            return True
        try:
            from temporalio.client import RPCError, RPCStatusCode

            if isinstance(current, RPCError) and current.status == RPCStatusCode.UNIMPLEMENTED:
                return True
        except ImportError:
            pass
        current = current.__cause__ or current.__context__
    return False


@dataclass(frozen=True, slots=True)
class PlaybackNormalizationWorkflowStart:
    workflow_id: str
    run_id: str | None = None
    reused: bool = False


@dataclass(frozen=True, slots=True)
class OutcomeGenerationWorkflowStart:
    workflow_id: str
    run_id: str | None = None
    reused: bool = False


@dataclass(frozen=True, slots=True)
class InvitationDeliveryWorkflowStart:
    workflow_id: str
    run_id: str | None = None
    reused: bool = False


@dataclass(frozen=True, slots=True)
class AccountCreatedEmailWorkflowStart:
    workflow_id: str
    run_id: str | None = None
    reused: bool = False


@dataclass(frozen=True, slots=True)
class PromptOptimizationWorkflowStart:
    workflow_id: str
    run_id: str | None = None
    reused: bool = False


@dataclass(frozen=True, slots=True)
class PromptRollbackWorkflowStart:
    workflow_id: str
    run_id: str | None = None
    reused: bool = False


def _started_workflow_run_id(handle: object) -> str | None:
    """Read the run ID from both real Temporal 1.30 handles and test doubles."""
    if isinstance(handle, dict):
        value = handle.get("result_run_id") or handle.get("run_id")
    else:
        value = getattr(handle, "result_run_id", None) or getattr(handle, "run_id", None)
    return value if isinstance(value, str) and value else None


def prompt_optimization_task_queue(settings: Settings) -> str:
    return f"{settings.temporal_task_queue}-prompt-optimization"


def outcome_generation_task_queue(settings: Settings) -> str:
    return f"{settings.temporal_task_queue}-outcomes"


def prompt_optimization_workflow_id(run_id: str) -> str:
    workflow_id = f"prompt-optimization/{run_id}"
    validate_prompt_optimization_workflow_id(workflow_id)
    return workflow_id


def prompt_rollback_workflow_id(run_id: str, rollback_version: int) -> str:
    workflow_id = f"prompt-rollback/{run_id}/{rollback_version}"
    validate_prompt_rollback_workflow_id(workflow_id)
    return workflow_id


def validate_prompt_optimization_workflow_id(workflow_id: str) -> None:
    if not PROMPT_OPTIMIZATION_WORKFLOW_ID_PATTERN.fullmatch(workflow_id):
        raise ValueError("prompt optimization workflow id is invalid")


def validate_prompt_rollback_workflow_id(workflow_id: str) -> None:
    if not PROMPT_ROLLBACK_WORKFLOW_ID_PATTERN.fullmatch(workflow_id):
        raise ValueError("prompt rollback workflow id is invalid")


def invitation_delivery_workflow_id(invitation_id: UUID) -> str:
    return f"share-invitation/{invitation_id}"


def validate_invitation_delivery_workflow_id(workflow_id: str) -> None:
    if not INVITATION_DELIVERY_WORKFLOW_ID_PATTERN.fullmatch(workflow_id):
        raise ValueError("invitation workflow id must contain only the fixed prefix and UUID")


def account_created_email_workflow_id(invitation_id: UUID) -> str:
    workflow_id = f"share-account-created/{invitation_id}"
    validate_account_created_email_workflow_id(workflow_id)
    return workflow_id


def validate_account_created_email_workflow_id(workflow_id: str) -> None:
    if not ACCOUNT_CREATED_EMAIL_WORKFLOW_ID_PATTERN.fullmatch(workflow_id):
        raise ValueError("account-created email workflow id must contain only the fixed prefix and UUID")


def outcome_generation_workflow_id(candidate_id: UUID) -> str:
    return f"outcome-generation/{candidate_id}"


def validate_outcome_generation_workflow_id(workflow_id: str) -> None:
    if not OUTCOME_GENERATION_WORKFLOW_ID_PATTERN.fullmatch(workflow_id):
        raise ValueError(
            "outcome workflow id must contain only the fixed prefix and candidate UUID"
        )


def outcome_tracing_interceptor(tracer=None):
    from opentelemetry import baggage
    from opentelemetry import context as otel_context
    from opentelemetry.baggage.propagation import W3CBaggagePropagator
    from opentelemetry.propagate import get_global_textmap
    from opentelemetry.propagators.composite import CompositePropagator
    from opentelemetry.propagators.textmap import TextMapPropagator
    from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
    from temporalio.contrib.opentelemetry import (
        TracingInterceptor,
        TracingWorkflowInboundInterceptor,
    )

    base_propagator = CompositePropagator([TraceContextTextMapPropagator(), W3CBaggagePropagator()])
    langfuse_tags_baggage_key = "langfuse_tags"
    langfuse_tags_context_key = "langfuse.propagated.tags"

    class GrafLangfuseTemporalPropagator(TextMapPropagator):
        @property
        def fields(self) -> set[str]:
            return base_propagator.fields

        def inject(self, carrier, context=None, setter=None) -> None:
            tags = otel_context.get_value(langfuse_tags_context_key, context=context)
            if isinstance(tags, list):
                encoded = json.dumps(tags, ensure_ascii=True, separators=(",", ":"))
                context = baggage.set_baggage(
                    langfuse_tags_baggage_key,
                    encoded,
                    context=context,
                )
            if setter is None:
                base_propagator.inject(carrier, context=context)
            else:
                base_propagator.inject(carrier, context=context, setter=setter)

        def extract(self, carrier, context=None, getter=None):
            if getter is None:
                context = base_propagator.extract(carrier, context=context)
            else:
                context = base_propagator.extract(carrier, context=context, getter=getter)
            encoded = baggage.get_baggage(langfuse_tags_baggage_key, context=context)
            if not isinstance(encoded, str) or len(encoded) > 4096:
                return context
            try:
                tags = json.loads(encoded)
            except (TypeError, ValueError):
                return context
            if (
                not isinstance(tags, list)
                or len(tags) > 16
                or any(not isinstance(tag, str) or len(tag) > 200 for tag in tags)
            ):
                return context
            return otel_context.set_value(
                langfuse_tags_context_key,
                tags,
                context=context,
            )

    propagator = GrafLangfuseTemporalPropagator()

    class GrafWorkflowTracingInterceptor(TracingWorkflowInboundInterceptor):
        def __init__(self, next) -> None:
            super().__init__(next)
            self.text_map_propagator = propagator

    class GrafTracingInterceptor(TracingInterceptor):
        def __init__(self) -> None:
            super().__init__(tracer=tracer)
            self.text_map_propagator = propagator

        def workflow_interceptor_class(self, input):
            super().workflow_interceptor_class(input)
            return GrafWorkflowTracingInterceptor

    # Keep propagation local to this interceptor; unrelated workflows retain
    # the process-global propagator.
    assert get_global_textmap() is not None
    return GrafTracingInterceptor()


def processing_worker_identity(hostname: str | None = None) -> str:
    if hostname is None:
        import socket

        hostname = socket.gethostname()
    normalized = SAFE_WORKER_HOSTNAME.sub("-", hostname.strip()).strip("-.")[:120]
    if not normalized:
        raise RuntimeError("processing worker hostname is unavailable")
    return f"{PROCESSING_WORKER_IDENTITY_PREFIX}{normalized}"


def processing_workflow_id(media_revision_id: UUID, attempt_ordinal: int = 1) -> str:
    """Return the stable Temporal identity for one business attempt.

    Attempt one keeps the historical ID so existing Temporal histories remain
    addressable. Later attempts get a new ID and therefore can never reuse the
    completed/failed execution or its provider idempotency lineage.
    """

    if isinstance(attempt_ordinal, bool) or not isinstance(attempt_ordinal, int):
        raise ValueError("processing attempt ordinal must be an integer")
    if attempt_ordinal < 1:
        raise ValueError("processing attempt ordinal must be positive")
    suffix = "" if attempt_ordinal == 1 else f"/{attempt_ordinal}"
    return f"processing/{media_revision_id}{suffix}"


def validate_processing_workflow_id(workflow_id: str) -> None:
    if not WORKFLOW_ID_PATTERN.fullmatch(workflow_id):
        raise ValueError(
            "processing workflow id must contain the fixed prefix, media revision UUID, and optional attempt ordinal"
        )


def playback_normalization_workflow_id(media_revision_id: UUID) -> str:
    return f"playback-normalization/{media_revision_id}/v1"


def validate_playback_normalization_workflow_id(workflow_id: str) -> None:
    if not PLAYBACK_NORMALIZATION_WORKFLOW_ID_PATTERN.fullmatch(workflow_id):
        raise ValueError(
            "playback normalization workflow id must contain only the fixed prefix, revision UUID, and profile version"
        )


async def connect_temporal_client(
    settings: Settings,
    *,
    identity: str | None = None,
    outcome_tracing: bool = False,
) -> object:
    if not settings.temporal_address:
        raise RuntimeError("temporal_address is not configured")
    from temporalio.client import Client
    from temporalio.service import RetryConfig

    langfuse_client = None
    interceptors = []
    if outcome_tracing:
        from twobrain_rec_server.observability.langfuse import (
            create_langfuse_client,
            langfuse_otel_tracer,
        )

        langfuse_client = create_langfuse_client(settings)
        interceptors = [outcome_tracing_interceptor(langfuse_otel_tracer(langfuse_client))]
    client = await Client.connect(
        settings.temporal_address,
        namespace=settings.temporal_namespace,
        identity=identity,
        retry_config=RetryConfig(max_retries=0),
        interceptors=interceptors,
    )
    if langfuse_client is not None:
        client._graf_langfuse_client = langfuse_client
    return client


def _traced_workflow_dispatch(
    temporal_client: object,
    *,
    settings: Settings,
    seed: str,
    trace_name: str,
    input_value: dict[str, object],
    user_id: str | None = None,
    session_id: str | None = None,
):
    langfuse_client = getattr(temporal_client, "_graf_langfuse_client", None)
    if langfuse_client is None:
        return nullcontext()
    from twobrain_rec_server.observability.langfuse import workflow_dispatch_observation

    return workflow_dispatch_observation(
        langfuse_client,
        seed=seed,
        trace_name=trace_name,
        input_value=input_value,
        environment=settings.langfuse_environment,
        user_id=user_id,
        session_id=session_id,
        tags=["feature:recording-workflows", f"operation:{trace_name}"],
    )


async def start_prompt_optimization_workflow(
    *,
    temporal_client: object,
    settings: Settings,
    workflow_id: str,
    payload: dict[str, Any],
) -> PromptOptimizationWorkflowStart:
    from twobrain_rec_server.workflows.prompt_optimization_workflow import (
        PromptOptimizationWorkflow,
    )

    validate_prompt_optimization_workflow_id(workflow_id)
    try:
        with _traced_workflow_dispatch(
            temporal_client,
            settings=settings,
            seed=workflow_id,
            trace_name="optimize-meeting-prompt",
            input_value={"run_id": str(payload.get("run_id", "")), "workflow_id": workflow_id},
            session_id=str(payload.get("run_id", "")) or None,
        ):
            handle = await temporal_client.start_workflow(
                PromptOptimizationWorkflow.run,
                payload,
                id=workflow_id,
                task_queue=prompt_optimization_task_queue(settings),
            )
    except Exception as exc:
        exc_name = exc.__class__.__name__.lower()
        if "already" not in exc_name and "workflowalready" not in exc_name:
            raise
        return PromptOptimizationWorkflowStart(workflow_id=workflow_id, reused=True)
    run_id = _started_workflow_run_id(handle)
    return PromptOptimizationWorkflowStart(workflow_id=workflow_id, run_id=run_id)


async def start_prompt_rollback_workflow(
    *,
    temporal_client: object,
    settings: Settings,
    workflow_id: str,
    payload: dict[str, Any],
) -> PromptRollbackWorkflowStart:
    from twobrain_rec_server.workflows.prompt_rollback_workflow import PromptRollbackWorkflow

    validate_prompt_rollback_workflow_id(workflow_id)
    try:
        with _traced_workflow_dispatch(
            temporal_client,
            settings=settings,
            seed=workflow_id,
            trace_name="rollback-meeting-prompt",
            input_value={"run_id": str(payload.get("run_id", "")), "workflow_id": workflow_id},
            session_id=str(payload.get("run_id", "")) or None,
        ):
            handle = await temporal_client.start_workflow(
                PromptRollbackWorkflow.run,
                payload,
                id=workflow_id,
                task_queue=prompt_optimization_task_queue(settings),
                execution_timeout=timedelta(hours=1),
            )
    except Exception as exc:
        exc_name = exc.__class__.__name__.lower()
        if "already" not in exc_name and "workflowalready" not in exc_name:
            raise
        return PromptRollbackWorkflowStart(workflow_id=workflow_id, reused=True)
    run_id = _started_workflow_run_id(handle)
    return PromptRollbackWorkflowStart(workflow_id=workflow_id, run_id=run_id)


async def start_outcome_generation_workflow(
    *,
    temporal_client: object,
    settings: Settings,
    candidate_id: UUID,
    meeting_id: UUID,
    workspace_id: UUID,
    source_result_id: UUID,
    template_key: str,
    template_version: int,
    prompt_name: str,
    requested_by_user_id: UUID | None = None,
) -> OutcomeGenerationWorkflowStart:
    from temporalio.common import WorkflowIDReusePolicy

    from twobrain_rec_server.workflows.outcome_generation_workflow import (
        OutcomeGenerationWorkflow,
    )

    workflow_id = outcome_generation_workflow_id(candidate_id)
    validate_outcome_generation_workflow_id(workflow_id)
    payload = {
        "candidate_id": str(candidate_id),
        "meeting_id": str(meeting_id),
        "workspace_id": str(workspace_id),
        "source_result_id": str(source_result_id),
        "template_key": template_key,
        "template_version": str(template_version),
        "prompt_name": prompt_name,
    }
    try:
        with _traced_workflow_dispatch(
            temporal_client,
            settings=settings,
            seed=workflow_id,
            trace_name="generate-meeting-outcome",
            input_value={
                "candidate_id": str(candidate_id),
                "meeting_id": str(meeting_id),
                "workspace_id": str(workspace_id),
            },
            user_id=(str(requested_by_user_id) if requested_by_user_id is not None else None),
            session_id=str(meeting_id),
        ):
            handle = await temporal_client.start_workflow(
                OutcomeGenerationWorkflow.run,
                payload,
                id=workflow_id,
                task_queue=outcome_generation_task_queue(settings),
                # A completed successful candidate must not be replayed under
                # the same deterministic ID. Failed runs remain dispatchable
                # for the explicit retry path, while an ambiguous start still
                # safely reuses the same ID.
                id_reuse_policy=WorkflowIDReusePolicy.ALLOW_DUPLICATE_FAILED_ONLY,
            )
    except Exception as exc:
        exc_name = exc.__class__.__name__.lower()
        if "already" not in exc_name and "workflowalready" not in exc_name:
            raise
        existing_run_id = getattr(exc, "run_id", None)
        return OutcomeGenerationWorkflowStart(
            workflow_id=workflow_id,
            run_id=existing_run_id if isinstance(existing_run_id, str) else None,
            reused=True,
        )
    run_id = _started_workflow_run_id(handle)
    return OutcomeGenerationWorkflowStart(workflow_id=workflow_id, run_id=run_id)


async def start_invitation_delivery_workflow(
    *,
    temporal_client: object,
    settings: Settings,
    invitation_id: UUID,
    workspace_id: UUID,
) -> InvitationDeliveryWorkflowStart:
    from twobrain_rec_server.workflows.invitation_delivery_workflow import (
        InvitationDeliveryWorkflow,
    )

    workflow_id = invitation_delivery_workflow_id(invitation_id)
    validate_invitation_delivery_workflow_id(workflow_id)
    try:
        handle = await temporal_client.start_workflow(
            InvitationDeliveryWorkflow.run,
            {"invitation_id": str(invitation_id), "workspace_id": str(workspace_id)},
            id=workflow_id,
            task_queue=settings.temporal_task_queue,
            execution_timeout=timedelta(hours=1),
        )
    except Exception as exc:
        exc_name = exc.__class__.__name__.lower()
        if "already" not in exc_name and "workflowalready" not in exc_name:
            raise
        return InvitationDeliveryWorkflowStart(workflow_id=workflow_id, reused=True)
    run_id = _started_workflow_run_id(handle)
    return InvitationDeliveryWorkflowStart(workflow_id=workflow_id, run_id=run_id)


async def start_account_created_email_workflow(
    *,
    temporal_client: object,
    settings: Settings,
    invitation_id: UUID,
    workspace_id: UUID,
    organization_id: UUID,
    user_id: UUID,
) -> AccountCreatedEmailWorkflowStart:
    from twobrain_rec_server.workflows.invitation_delivery_workflow import (
        AccountCreatedEmailWorkflow,
    )

    workflow_id = account_created_email_workflow_id(invitation_id)
    validate_account_created_email_workflow_id(workflow_id)
    try:
        handle = await temporal_client.start_workflow(
            AccountCreatedEmailWorkflow.run,
            {
                "invitation_id": str(invitation_id),
                "workspace_id": str(workspace_id),
                "organization_id": str(organization_id),
                "user_id": str(user_id),
            },
            id=workflow_id,
            task_queue=settings.temporal_task_queue,
            execution_timeout=timedelta(hours=1),
        )
    except Exception as exc:
        exc_name = exc.__class__.__name__.lower()
        if "already" not in exc_name and "workflowalready" not in exc_name:
            raise
        return AccountCreatedEmailWorkflowStart(workflow_id=workflow_id, reused=True)
    run_id = _started_workflow_run_id(handle)
    return AccountCreatedEmailWorkflowStart(workflow_id=workflow_id, run_id=run_id)


async def cancel_invitation_delivery_workflow(
    *,
    temporal_client: object,
    invitation_id: UUID,
) -> bool:
    """Request deterministic cancellation; the revoked DB state remains authoritative."""
    workflow_id = invitation_delivery_workflow_id(invitation_id)
    validate_invitation_delivery_workflow_id(workflow_id)
    try:
        handle = temporal_client.get_workflow_handle(workflow_id)
        await handle.cancel()
    except Exception:
        # A completed/unreachable workflow cannot re-enable a revoked invitation;
        # the activity rechecks the durable status before delivery.
        return False
    return True


async def cancel_workflow_best_effort(temporal_client: object, workflow_id: str) -> bool:
    """Cancel a just-started workflow when its durable lifecycle fence lost."""
    try:
        handle = temporal_client.get_workflow_handle(workflow_id)
        await handle.cancel()
    except Exception:
        return False
    return True


async def request_processing_manual_check(
    *,
    temporal_client: object,
    workflow_id: str,
    command_id: str,
) -> ProcessingManualCheckDispatch:
    """Wake the existing processing workflow without starting another one."""

    from twobrain_rec_server.workflows.processing_workflow import MediaScribeProcessingWorkflow

    validate_processing_workflow_id(workflow_id)
    handle = temporal_client.get_workflow_handle(workflow_id)
    execute_update = getattr(handle, "execute_update", None)
    if callable(execute_update):
        try:
            await execute_update(
                MediaScribeProcessingWorkflow.request_manual_check_update,
                id=command_id,
            )
            return ProcessingManualCheckDispatch(dispatch="update")
        except Exception as exc:
            if not _temporal_update_fallback_allowed(exc):
                raise
    await handle.signal(MediaScribeProcessingWorkflow.request_manual_check)
    return ProcessingManualCheckDispatch(dispatch="signal")


async def start_processing_workflow(
    *,
    temporal_client: object,
    settings: Settings,
    meeting_id: UUID,
    media_revision_id: UUID,
    workspace_id: UUID,
    tenant_scope: TenantScope | None = None,
    archive_audio: bool = True,
    attempt_ordinal: int = 1,
) -> ProcessingWorkflowStart:
    workflow_id = processing_workflow_id(media_revision_id, attempt_ordinal)
    validate_processing_workflow_id(workflow_id)
    payload = {
        "meeting_id": str(meeting_id),
        "media_revision_id": str(media_revision_id),
        "workspace_id": str(workspace_id),
        "requested_by": "processing-pickup",
        "source": "ingested_pending_processing",
        "archive_audio": "true" if archive_audio else "false",
    }
    if tenant_scope is not None:
        payload.update(
            {
                "organization_id": str(tenant_scope.organization_id),
                "workspace_id": str(tenant_scope.workspace_id),
                "user_id": str(tenant_scope.user_id),
                "device_id": str(tenant_scope.device_id),
            }
        )
        if tenant_scope.auth_session_id is not None:
            payload["auth_session_id"] = str(tenant_scope.auth_session_id)
    from twobrain_rec_server.workflows.processing_workflow import MediaScribeProcessingWorkflow

    try:
        handle = await temporal_client.start_workflow(
            MediaScribeProcessingWorkflow.run,
            payload,
            id=workflow_id,
            task_queue=settings.temporal_task_queue,
        )
    except Exception as exc:
        exc_name = exc.__class__.__name__.lower()
        if "already" not in exc_name and "workflowalready" not in exc_name:
            raise
        return ProcessingWorkflowStart(workflow_id=workflow_id, reused=True)
    run_id = _started_workflow_run_id(handle)
    return ProcessingWorkflowStart(workflow_id=workflow_id, run_id=run_id, reused=False)


async def start_playback_normalization_workflow(
    *,
    temporal_client: object,
    settings: Settings,
    job_id: UUID,
    meeting_id: UUID,
    media_revision_id: UUID,
    tenant_scope: TenantScope,
    profile_version: str,
    validation_version: str,
) -> PlaybackNormalizationWorkflowStart:
    workflow_id = playback_normalization_workflow_id(media_revision_id)
    validate_playback_normalization_workflow_id(workflow_id)
    payload = {
        "organization_id": str(tenant_scope.organization_id),
        "workspace_id": str(tenant_scope.workspace_id),
        "user_id": str(tenant_scope.user_id),
        "device_id": str(tenant_scope.device_id),
        "meeting_id": str(meeting_id),
        "media_revision_id": str(media_revision_id),
        "job_id": str(job_id),
        "profile_version": profile_version,
        "validation_version": validation_version,
        "requested_by": "playback-normalization-dispatch",
    }
    if tenant_scope.auth_session_id is not None:
        payload["auth_session_id"] = str(tenant_scope.auth_session_id)
    from temporalio.common import WorkflowIDReusePolicy

    from twobrain_rec_server.workflows.playback_normalization_workflow import (
        PlaybackNormalizationWorkflow,
    )

    try:
        handle = await temporal_client.start_workflow(
            PlaybackNormalizationWorkflow.run,
            payload,
            id=workflow_id,
            task_queue=settings.playback_normalization_task_queue,
            execution_timeout=timedelta(
                seconds=int(settings.playback_normalization_workflow_timeout_seconds)
            ),
            id_reuse_policy=WorkflowIDReusePolicy.ALLOW_DUPLICATE,
        )
    except Exception as exc:
        exc_name = exc.__class__.__name__.lower()
        if "already" not in exc_name and "workflowalready" not in exc_name:
            raise
        return PlaybackNormalizationWorkflowStart(workflow_id=workflow_id, reused=True)
    run_id = _started_workflow_run_id(handle)
    return PlaybackNormalizationWorkflowStart(
        workflow_id=workflow_id,
        run_id=run_id,
        reused=False,
    )
