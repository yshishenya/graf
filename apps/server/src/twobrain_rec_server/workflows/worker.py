from __future__ import annotations

import asyncio
from uuid import UUID

from twobrain_rec_server.config import get_settings
from twobrain_rec_server.db.session import create_engine, create_sessionmaker
from twobrain_rec_server.domain.statuses import ProcessingStatus
from twobrain_rec_server.mediascribe.client import MediaScribeClient, MediaScribeClientError
from twobrain_rec_server.processing import store
from twobrain_rec_server.processing.submit import (
    poll_and_import_mediascribe_result,
    submit_to_mediascribe,
)
from twobrain_rec_server.storage.minio_client import get_storage
from twobrain_rec_server.workflows.processing_workflow import MediaScribeProcessingWorkflow
from twobrain_rec_server.workflows.temporal_client import connect_temporal_client


async def run_processing_pipeline_activity(payload: dict[str, str]) -> dict[str, str]:
    from temporalio import activity

    activity.heartbeat({"state": "starting", "meeting_id": payload["meeting_id"]})
    settings = get_settings()
    engine = create_engine(settings)
    sessionmaker = create_sessionmaker(engine)
    storage = get_storage(settings)
    try:
        mediascribe_client = MediaScribeClient.from_settings(settings)
        meeting_id = UUID(payload["meeting_id"])
        workspace_id = UUID(payload["workspace_id"])
        async with sessionmaker() as db:
            workflow = await store.get_processing_workflow(
                db,
                workspace_id=workspace_id,
                meeting_id=meeting_id,
            )
            if workflow is None:
                workflow = await store.upsert_processing_workflow(
                    db,
                    workspace_id=workspace_id,
                    meeting_id=meeting_id,
                    workflow_id=f"processing/{payload['meeting_id']}",
                    status=ProcessingStatus.WORKFLOW_STARTED,
                )
            submit_result = await submit_to_mediascribe(
                db=db,
                settings=settings,
                storage=storage,
                mediascribe_client=mediascribe_client,
                workflow=workflow,
            )
            job = submit_result.job
            for poll_attempt in range(settings.processing_max_poll_attempts):
                activity.heartbeat({"state": "polling", "poll_attempt": poll_attempt + 1})
                import_result = await poll_and_import_mediascribe_result(
                    db=db,
                    workflow=workflow,
                    job=job,
                    mediascribe_client=mediascribe_client,
                )
                if import_result.status == ProcessingStatus.PROCESSED:
                    return {"meeting_id": payload["meeting_id"], "processing_status": "processed"}
                if import_result.status == ProcessingStatus.FAILED_TERMINAL:
                    return {"meeting_id": payload["meeting_id"], "processing_status": "failed_terminal"}
                await asyncio.sleep(settings.processing_poll_interval_seconds)
            await store.set_workflow_status(
                db,
                workflow,
                ProcessingStatus.FAILED_TERMINAL,
                reason_code="mediascribe_poll_limit_exceeded",
                terminal=True,
            )
            return {"meeting_id": payload["meeting_id"], "processing_status": "failed_terminal"}
    except MediaScribeClientError as exc:
        return {"meeting_id": payload["meeting_id"], "processing_status": "failed_retryable" if exc.retryable else "failed_terminal"}
    finally:
        await engine.dispose()


async def run_worker() -> None:
    from temporalio import activity
    from temporalio.worker import Worker

    settings = get_settings()
    client = await connect_temporal_client(settings)
    processing_activity = activity.defn(name="run_processing_pipeline_activity")(run_processing_pipeline_activity)
    worker = Worker(
        client,
        task_queue=settings.temporal_task_queue,
        workflows=[MediaScribeProcessingWorkflow],
        activities=[processing_activity],
    )
    await worker.run()


def main() -> None:
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
