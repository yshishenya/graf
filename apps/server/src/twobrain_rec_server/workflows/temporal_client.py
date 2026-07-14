from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID

from twobrain_rec_server.auth.context import TenantScope
from twobrain_rec_server.config import Settings

WORKFLOW_ID_PATTERN = re.compile(
    r"^processing/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)
PLAYBACK_NORMALIZATION_WORKFLOW_ID_PATTERN = re.compile(
    r"^playback-normalization/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/v1$"
)


@dataclass(frozen=True, slots=True)
class ProcessingWorkflowStart:
    workflow_id: str
    run_id: str | None = None
    reused: bool = False


@dataclass(frozen=True, slots=True)
class PlaybackNormalizationWorkflowStart:
    workflow_id: str
    run_id: str | None = None
    reused: bool = False


def processing_workflow_id(media_revision_id: UUID) -> str:
    return f"processing/{media_revision_id}"


def validate_processing_workflow_id(workflow_id: str) -> None:
    if not WORKFLOW_ID_PATTERN.fullmatch(workflow_id):
        raise ValueError(
            "processing workflow id must contain only the fixed prefix and media revision UUID"
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
) -> object:
    if not settings.temporal_address:
        raise RuntimeError("temporal_address is not configured")
    from temporalio.client import Client

    return await Client.connect(
        settings.temporal_address,
        namespace=settings.temporal_namespace,
        identity=identity,
    )


async def start_processing_workflow(
    *,
    temporal_client: object,
    settings: Settings,
    meeting_id: UUID,
    media_revision_id: UUID,
    workspace_id: UUID,
    tenant_scope: TenantScope | None = None,
) -> ProcessingWorkflowStart:
    workflow_id = processing_workflow_id(media_revision_id)
    validate_processing_workflow_id(workflow_id)
    payload = {
        "meeting_id": str(meeting_id),
        "media_revision_id": str(media_revision_id),
        "workspace_id": str(workspace_id),
        "requested_by": "processing-pickup",
        "source": "ingested_pending_processing",
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
    run_id = getattr(handle, "run_id", None)
    if isinstance(handle, dict):
        run_id = handle.get("run_id")
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
    run_id = getattr(handle, "run_id", None)
    if isinstance(handle, dict):
        run_id = handle.get("run_id")
    return PlaybackNormalizationWorkflowStart(
        workflow_id=workflow_id,
        run_id=run_id,
        reused=False,
    )
