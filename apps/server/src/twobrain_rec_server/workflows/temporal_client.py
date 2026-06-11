from __future__ import annotations

import re
from dataclasses import dataclass
from uuid import UUID

from twobrain_rec_server.config import Settings

WORKFLOW_ID_PATTERN = re.compile(r"^processing/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


@dataclass(frozen=True, slots=True)
class ProcessingWorkflowStart:
    workflow_id: str
    run_id: str | None = None
    reused: bool = False


def processing_workflow_id(meeting_id: UUID) -> str:
    return f"processing/{meeting_id}"


def validate_processing_workflow_id(workflow_id: str) -> None:
    if not WORKFLOW_ID_PATTERN.fullmatch(workflow_id):
        raise ValueError("processing workflow id must contain only the fixed prefix and meeting UUID")


async def connect_temporal_client(settings: Settings) -> object:
    if not settings.temporal_address:
        raise RuntimeError("temporal_address is not configured")
    from temporalio.client import Client

    return await Client.connect(settings.temporal_address, namespace=settings.temporal_namespace)


async def start_processing_workflow(
    *,
    temporal_client: object,
    settings: Settings,
    meeting_id: UUID,
    workspace_id: UUID,
) -> ProcessingWorkflowStart:
    workflow_id = processing_workflow_id(meeting_id)
    validate_processing_workflow_id(workflow_id)
    payload = {
        "meeting_id": str(meeting_id),
        "workspace_id": str(workspace_id),
        "requested_by": "processing-pickup",
        "source": "ingested_pending_processing",
    }
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
