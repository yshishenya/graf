"""Operations-only Temporal worker for deployment-global prompt optimization.

This worker intentionally does not register the normal processing or outcome
queues. It is run from the operations Compose profile with the maintenance DB
role, so ordinary recording workers never receive that credential.
"""

from __future__ import annotations

import asyncio

from temporalio import activity
from temporalio.worker import Worker

from twobrain_rec_server.config import get_settings
from twobrain_rec_server.db.session import (
    create_prompt_optimization_database,
    verify_prompt_optimization_database_identity,
)
from twobrain_rec_server.outcomes.prompt_optimization import (
    authorize_prompt_optimization_action_activity,
    authorize_prompt_rollback_action_activity,
    finalize_prompt_optimization_activity,
    finalize_prompt_optimization_history_materialization_activity,
    promote_prompt_candidate_activity,
    publish_prompt_candidate_activity,
    resolve_prompt_optimization_contract_activity,
    rollback_prompt_production_label_activity,
    run_gepa_prompt_optimization_activity,
    snapshot_prompt_optimization_history_chunk_activity,
    validate_heldout_prompt_candidate_activity,
)
from twobrain_rec_server.workflows.prompt_optimization_workflow import (
    PromptOptimizationWorkflow,
)
from twobrain_rec_server.workflows.prompt_rollback_workflow import PromptRollbackWorkflow
from twobrain_rec_server.workflows.temporal_client import (
    connect_temporal_client,
    processing_worker_identity,
    prompt_optimization_task_queue,
)


async def run_prompt_optimization_worker() -> None:
    settings = get_settings()
    if not settings.prompt_optimization_enabled:
        raise RuntimeError("prompt optimization worker is disabled")
    identity_engine, identity_sessionmaker = create_prompt_optimization_database(settings)
    try:
        await verify_prompt_optimization_database_identity(identity_sessionmaker)
    finally:
        await identity_engine.dispose()
    temporal = await connect_temporal_client(
        settings,
        identity=f"{processing_worker_identity()}:prompt-optimization-operator",
        outcome_tracing=True,
    )
    optimizer_activities = [
        activity.defn(name=callable_.__name__)(callable_)
        for callable_ in (
            resolve_prompt_optimization_contract_activity,
            run_gepa_prompt_optimization_activity,
            snapshot_prompt_optimization_history_chunk_activity,
            finalize_prompt_optimization_history_materialization_activity,
            validate_heldout_prompt_candidate_activity,
            publish_prompt_candidate_activity,
            authorize_prompt_optimization_action_activity,
            promote_prompt_candidate_activity,
            finalize_prompt_optimization_activity,
            authorize_prompt_rollback_action_activity,
            rollback_prompt_production_label_activity,
        )
    ]
    worker = Worker(
        temporal,
        task_queue=prompt_optimization_task_queue(settings),
        workflows=[PromptOptimizationWorkflow, PromptRollbackWorkflow],
        activities=optimizer_activities,
        identity=f"{processing_worker_identity()}:prompt-optimization",
        max_concurrent_activities=1,
    )
    await worker.run()


def main() -> None:
    asyncio.run(run_prompt_optimization_worker())


if __name__ == "__main__":
    main()
