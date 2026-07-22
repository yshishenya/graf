from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
from uuid import UUID

import pytest

from twobrain_rec_server.db import models
from twobrain_rec_server.db.base import Base

REPO_ROOT = Path(__file__).resolve().parents[4]
MIGRATION = (
    REPO_ROOT
    / "apps/server/src/twobrain_rec_server/db/migrations/versions/0031_recording_workflow_templates_sharing.py"
)

NEW_TABLES = {
    "summary_templates",
    "generation_calls",
    "prompt_optimization_runs",
    "prompt_optimization_call_ledger",
    "meeting_share_invitations",
}


def _load_migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("recording_workflow_migration", MIGRATION)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_recording_workflow_models_are_registered_with_parent_independent_call_ledger() -> None:
    assert models.SummaryTemplate.__tablename__ == "summary_templates"
    assert models.GenerationCall.__tablename__ == "generation_calls"
    assert models.PromptOptimizationRun.__tablename__ == "prompt_optimization_runs"
    assert (
        models.PromptOptimizationCallLedger.__tablename__
        == "prompt_optimization_call_ledger"
    )
    assert models.MeetingShareInvitation.__tablename__ == "meeting_share_invitations"
    assert NEW_TABLES.issubset(Base.metadata.tables)

    generation_calls = Base.metadata.tables["generation_calls"]
    for column in (
        "workspace_id",
        "meeting_id",
        "candidate_id",
        "trace_id",
        "observation_id",
        "call_state",
        "request_json",
        "transcript_text",
        "raw_response_json",
        "validated_result_json",
        "request_hash",
        "transcript_hash",
        "raw_response_hash",
        "validated_result_hash",
        "export_status",
        "export_attempt_count",
        "next_export_attempt_at",
    ):
        assert column in generation_calls.c
    assert not generation_calls.c.meeting_id.foreign_keys
    assert not generation_calls.c.candidate_id.foreign_keys

    optimizer = Base.metadata.tables["prompt_optimization_runs"]
    assert "workspace_id" not in optimizer.c
    assert "deployment_scope" in optimizer.c
    assert "checkpoint_hash" in optimizer.c


def test_existing_models_gain_revision_prompt_and_sharing_provenance() -> None:
    meetings = Base.metadata.tables["meetings"]
    outcome_sets = Base.metadata.tables["meeting_outcome_sets"]
    attempts = Base.metadata.tables["meeting_outcome_generation_attempts"]
    grants = Base.metadata.tables["meeting_share_grants"]

    assert "current_outcome_set_id" in meetings.c
    for column in (
        "template_id",
        "template_key",
        "template_version",
        "revision_state",
        "requested_by_user_id",
        "accepted_by_user_id",
        "supersedes_outcome_set_id",
    ):
        assert column in outcome_sets.c
    for column in (
        "candidate_id",
        "requested_by_user_id",
        "prompt_name",
        "prompt_version",
        "prompt_source",
        "prompt_definition",
        "prompt_config",
        "prompt_hash",
        "output_schema_version",
        "model_route",
        "model_parameters",
        "workflow_id",
        "workflow_run_id",
        "langfuse_trace_id",
        "temporal_transcript_hash",
        "temporal_transcript_chunk_count",
        "attempt_count",
        "failure_code",
    ):
        assert column in attempts.c
    for column in (
        "audience_type",
        "audience_id",
        "content_scope",
        "can_download",
        "can_export",
        "expires_at",
        "rotated_at",
        "last_used_at",
    ):
        assert column in grants.c


def test_migration_is_additive_rls_covered_and_downgrade_safe() -> None:
    assert MIGRATION.exists()
    migration = _load_migration()
    source = MIGRATION.read_text(encoding="utf-8")

    assert migration.revision == "0031_recording_workflows"
    assert migration.down_revision == "0030_expand_meeting_registry"
    assert migration.TENANT_TABLE_POLICIES == {
        "summary_templates": migration.REQUEST_WORKER_TENANT,
        "meeting_share_invitations": migration.REQUEST_WORKER_TENANT,
        "generation_calls": migration.WORKER_OPERATOR_TENANT,
    }
    assert set(migration.GLOBAL_OPERATOR_TABLES) == {
        "prompt_optimization_runs",
        "prompt_optimization_call_ledger",
    }
    assert "rec_maintenance_allowed()" in source
    assert "enable row level security" in source
    assert "force row level security" in source
    assert "def downgrade()" in source
    assert "set content_scope = 'full_meeting'" in source
    assert "can_download = true, can_export = true" in source
    for table_name in NEW_TABLES:
        assert f'"{table_name}"' in source
        assert f'op.drop_table("{table_name}")' in source


def test_generation_delivery_has_one_authoritative_per_call_status() -> None:
    calls = Base.metadata.tables["generation_calls"]
    attempts = Base.metadata.tables["meeting_outcome_generation_attempts"]

    assert "export_status" in calls.c
    assert "export_attempt_count" in calls.c
    assert "export_status" not in attempts.c
    assert "observability_status" not in attempts.c


def test_cabinet_schemas_are_bounded_and_exclude_optimizer_control() -> None:
    from pydantic import ValidationError

    from twobrain_rec_server.api import schemas

    request = schemas.CreateSummaryTemplateRequest(
        name="Итоги встречи",
        purpose="Решения и следующие шаги",
        sections=[
            "summary",
            "key_points",
            "decisions",
            "action_items",
            "followups",
            "risks",
            "questions",
            "evidence",
        ],
        output_language="ru",
        detail_level="standard",
    )
    assert request.sections[-1] == "evidence"
    assert len(request.sections) == 8
    with pytest.raises(ValidationError):
        schemas.CreateSummaryTemplateRequest(
            name="Итоги",
            purpose="Проверка",
            sections=["summary", "summary"],
            output_language="ru",
            detail_level="standard",
        )
    with pytest.raises(ValidationError):
        schemas.CreateMeetingShareInvitationRequest(
            address="invalid",
            content_scope="summary_only",
        )
    assert not hasattr(schemas, "PromptOptimizationRequest")


def test_foundation_audit_and_lifecycle_accounting_are_bounded_and_truthful() -> None:
    from twobrain_rec_server.cabinet.access import denied_access_audit_metadata
    from twobrain_rec_server.deletion.service import _initial_artifact_states
    from twobrain_rec_server.domain.statuses import (
        DeletionArtifactClass,
        DeletionArtifactState,
    )
    from twobrain_rec_server.processing.audit import (
        ALLOWED_AUDIT_EVENT_TYPES,
        safe_audit_metadata,
    )

    assert {
        "summary_generation_requested",
        "prompt_optimization_promoted",
        "share_invitation_failed",
        "share_link_revoked",
    }.issubset(ALLOWED_AUDIT_EVENT_TYPES)
    metadata = safe_audit_metadata(
        {
            "prompt_version": 7,
            "prompt_hash": "a" * 64,
            "workflow_id": "outcome-generation/synthetic",
            "transcript_text": "must-not-enter-audit",
            "raw_response": {"private": True},
        }
    )
    assert metadata == {
        "prompt_version": 7,
        "prompt_hash": "a" * 64,
        "workflow_id": "outcome-generation/synthetic",
    }
    assert denied_access_audit_metadata(
        request_class="share",
        feature_area="recording_workflow",
        reason_category="cross_tenant",
        validation_outcome="denied",
        transcript_text="must-not-enter-audit",
    ) == {
        "request_class": "share",
        "feature_area": "recording_workflow",
        "reason_category": "cross_tenant",
        "validation_outcome": "denied",
    }

    meeting = models.Meeting(
        id=UUID("10000000-0000-0000-0000-000000000121"),
        workspace_id=UUID("20000000-0000-0000-0000-000000000121"),
        created_by_user_id=UUID("30000000-0000-0000-0000-000000000121"),
        device_id=UUID("40000000-0000-0000-0000-000000000121"),
        local_recording_id="synthetic-121",
        duration_seconds=1,
    )
    rows = _initial_artifact_states(
        meeting,
        UUID("50000000-0000-0000-0000-000000000121"),
        materialized_artifact_classes={DeletionArtifactClass.OUTCOME_ATTEMPT},
    )
    retained = {row.artifact_class: row for row in rows}
    assert retained["outcome_attempt"].state == DeletionArtifactState.METADATA_RETAINED
    for artifact_class in ("generation_call", "langfuse", "temporal_history"):
        assert retained[artifact_class].state == DeletionArtifactState.OBSERVABILITY_RETAINED
