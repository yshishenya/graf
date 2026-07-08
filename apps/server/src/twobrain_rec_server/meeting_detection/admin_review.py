from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.admin.audit import write_admin_audit_event
from twobrain_rec_server.admin.queries import AdminWorkspaceContext
from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.db.models import (
    MeetingDetectionCandidate,
    MeetingDetectionNonTargetRule,
    MeetingDetectionReviewAction,
    MeetingDetectionTargetHealthRollup,
    MeetingTargetRegistryEntry,
    MeetingTargetRegistryVersion,
)
from twobrain_rec_server.meeting_detection.registry import (
    build_registry_draft_document,
    get_latest_published_registry,
    registry_entries,
    registry_etag,
)


async def load_meeting_detection_review(
    db: AsyncSession,
    *,
    context: AdminWorkspaceContext,
    limit: int = 50,
) -> dict[str, Any]:
    candidates = (
        (
            await db.execute(
                select(MeetingDetectionCandidate)
                .where(MeetingDetectionCandidate.workspace_id == context.workspace_id)
                .order_by(
                    MeetingDetectionCandidate.candidate_score.desc(),
                    MeetingDetectionCandidate.updated_at.desc(),
                )
                .limit(limit)
            )
        )
        .scalars()
        .all()
    )
    health_rows = (
        (
            await db.execute(
                select(MeetingDetectionTargetHealthRollup)
                .where(MeetingDetectionTargetHealthRollup.workspace_id == context.workspace_id)
                .order_by(MeetingDetectionTargetHealthRollup.rollup_date.desc())
                .limit(limit)
            )
        )
        .scalars()
        .all()
    )
    registry_rows = (
        (
            await db.execute(
                select(MeetingTargetRegistryVersion)
                .where(
                    (MeetingTargetRegistryVersion.workspace_id == context.workspace_id)
                    | (MeetingTargetRegistryVersion.workspace_id.is_(None))
                )
                .order_by(MeetingTargetRegistryVersion.created_at.desc())
                .limit(limit)
            )
        )
        .scalars()
        .all()
    )
    return {
        "candidates": [_candidate_row(candidate) for candidate in candidates],
        "target_health": [_health_row(row) for row in health_rows],
        "registry_versions": [_registry_row(row) for row in registry_rows],
        "counts": {
            "candidate_count": len(candidates),
            "target_health_count": len(health_rows),
            "registry_version_count": len(registry_rows),
        },
    }


async def mark_candidate_non_target(
    db: AsyncSession,
    *,
    context: AdminWorkspaceContext,
    candidate_id: UUID,
    reason_code: str | None,
) -> dict[str, Any]:
    candidate = await _load_candidate(db, context=context, candidate_id=candidate_id)
    previous_state = candidate.state
    candidate.state = "non_target"
    if candidate.bundle_id:
        existing_rule = await db.scalar(
            select(MeetingDetectionNonTargetRule).where(
                MeetingDetectionNonTargetRule.workspace_id == context.workspace_id,
                MeetingDetectionNonTargetRule.platform == candidate.platform,
                MeetingDetectionNonTargetRule.rule_kind == "bundle_id",
                MeetingDetectionNonTargetRule.rule_value == candidate.bundle_id,
            )
        )
        if existing_rule is None:
            db.add(
                MeetingDetectionNonTargetRule(
                    workspace_id=context.workspace_id,
                    platform=candidate.platform,
                    rule_kind="bundle_id",
                    rule_value=candidate.bundle_id,
                    reason_code=reason_code or "admin_marked_non_target",
                    created_by_user_id=context.actor_user_id,
                    active=True,
                )
            )
        else:
            existing_rule.reason_code = reason_code or existing_rule.reason_code
            existing_rule.active = True
    await _write_review_action(
        db,
        context=context,
        candidate=candidate,
        action="mark_non_target",
        previous_state=previous_state,
        next_state=candidate.state,
        reason_code=reason_code or "admin_marked_non_target",
    )
    return _candidate_row(candidate)


async def merge_candidate_with_target(
    db: AsyncSession,
    *,
    context: AdminWorkspaceContext,
    candidate_id: UUID,
    target_id: str,
    reason_code: str | None,
) -> dict[str, Any]:
    candidate = await _load_candidate(db, context=context, candidate_id=candidate_id)
    registry = await get_latest_published_registry(db, workspace_id=context.workspace_id)
    if target_id not in {target["id"] for target in registry.document.get("targets", [])}:
        raise ProblemDetail(
            status=422,
            code="meeting_detection_target_not_found",
            title="Meeting detection target not found",
        )
    previous_state = candidate.state
    candidate.state = "merged"
    candidate.merged_target_id = target_id
    await _write_review_action(
        db,
        context=context,
        candidate=candidate,
        action="merge_existing_target",
        previous_state=previous_state,
        next_state=candidate.state,
        reason_code=reason_code or "same_target",
        metadata={"target_kind": "meeting_detection_target"},
    )
    return _candidate_row(candidate)


async def add_diagnostic_only_draft(
    db: AsyncSession,
    *,
    context: AdminWorkspaceContext,
    candidate_id: UUID,
    target_id: str,
    display_name: str,
    market: str,
    reason_code: str | None,
) -> dict[str, Any]:
    candidate = await _load_candidate(db, context=context, candidate_id=candidate_id)
    previous_state = candidate.state
    registry_version = _draft_registry_version()
    target = {
        "id": target_id,
        "displayName": display_name,
        "market": market,
        "platform": candidate.platform,
        "targetFamily": "native_app",
        "nativeBundleIds": [candidate.bundle_id] if candidate.bundle_id else [],
        "mode": "diagnostic_only",
        "evidence": "runtime_start_verified",
        "requiredSignals": ["macos_sensor_indicators_mic"],
        "comments": "Created from admin candidate review; prompt remains disabled.",
    }
    document = await build_registry_draft_document(
        db,
        workspace_id=context.workspace_id,
        registry_version=registry_version,
        target=target,
    )
    draft = MeetingTargetRegistryVersion(
        workspace_id=context.workspace_id,
        registry_version=registry_version,
        schema_version=1,
        status="draft",
        source="admin_candidate_review",
        document_json=document,
        etag=registry_etag(document),
    )
    db.add(draft)
    await db.flush()
    for entry in registry_entries(document):
        db.add(MeetingTargetRegistryEntry(registry_version_id=draft.id, **entry))
    candidate.state = "diagnostic_only_draft"
    candidate.proposed_target_id = target_id
    await _write_review_action(
        db,
        context=context,
        candidate=candidate,
        registry_version=draft,
        action="add_diagnostic_only_draft",
        previous_state=previous_state,
        next_state=candidate.state,
        reason_code=reason_code or "candidate_runtime_observed",
    )
    return {"candidate": _candidate_row(candidate), "registry_draft": _registry_row(draft)}


async def request_candidate_validation(
    db: AsyncSession,
    *,
    context: AdminWorkspaceContext,
    candidate_id: UUID,
    validation_kind: str,
    reason_code: str | None,
) -> dict[str, Any]:
    candidate = await _load_candidate(db, context=context, candidate_id=candidate_id)
    previous_state = candidate.state
    candidate.state = "validation_needed"
    action = (
        "request_runtime_validation"
        if validation_kind == "runtime"
        else "request_package_validation"
    )
    await _write_review_action(
        db,
        context=context,
        candidate=candidate,
        action=action,
        previous_state=previous_state,
        next_state=candidate.state,
        reason_code=reason_code or action,
    )
    return _candidate_row(candidate)


async def _load_candidate(
    db: AsyncSession,
    *,
    context: AdminWorkspaceContext,
    candidate_id: UUID,
) -> MeetingDetectionCandidate:
    candidate = await db.scalar(
        select(MeetingDetectionCandidate).where(
            MeetingDetectionCandidate.workspace_id == context.workspace_id,
            MeetingDetectionCandidate.id == candidate_id,
        )
    )
    if candidate is None:
        raise ProblemDetail(
            status=404,
            code="meeting_detection_candidate_not_found",
            title="Meeting detection candidate not found",
        )
    return candidate


async def _write_review_action(
    db: AsyncSession,
    *,
    context: AdminWorkspaceContext,
    candidate: MeetingDetectionCandidate,
    action: str,
    previous_state: str | None,
    next_state: str | None,
    reason_code: str,
    registry_version: MeetingTargetRegistryVersion | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> None:
    db.add(
        MeetingDetectionReviewAction(
            workspace_id=context.workspace_id,
            candidate_id=candidate.id,
            registry_version_id=registry_version.id if registry_version is not None else None,
            actor_user_id=context.actor_user_id,
            action=action,
            previous_state=previous_state,
            next_state=next_state,
            reason_code=reason_code,
            metadata_json={"action": action, "reason_code": reason_code},
        )
    )
    await write_admin_audit_event(
        db,
        workspace_id=context.workspace_id,
        actor_user_id=context.actor_user_id,
        actor_role=context.actor_role,
        action=action,
        target_kind="meeting_detection_candidate",
        target_id=str(candidate.id),
        outcome="completed",
        reason_code=reason_code,
        metadata={"action": action, "reason_code": reason_code, **dict(metadata or {})},
    )
    await db.flush()


def _candidate_row(candidate: MeetingDetectionCandidate) -> dict[str, Any]:
    return {
        "candidate_id": str(candidate.id),
        "platform": candidate.platform,
        "state": candidate.state,
        "bundle_id": candidate.bundle_id,
        "display_name": candidate.display_name,
        "signing_team_id": candidate.signing_team_id,
        "candidate_score": candidate.candidate_score,
        "candidate_reasons": candidate.candidate_reasons_json or [],
        "suppression_reasons": candidate.suppression_reasons_json or [],
        "stable_observation_count": candidate.stable_observation_count,
        "reporting_installation_count": candidate.reporting_installation_count,
        "manual_record_nearby_count": candidate.manual_record_nearby_count,
        "calendar_or_join_hint_count": candidate.calendar_or_join_hint_count,
        "proposed_target_id": candidate.proposed_target_id,
        "merged_target_id": candidate.merged_target_id,
        "first_seen_bucket": candidate.first_seen_bucket.isoformat()
        if candidate.first_seen_bucket
        else None,
        "last_seen_bucket": candidate.last_seen_bucket.isoformat()
        if candidate.last_seen_bucket
        else None,
    }


def _health_row(row: MeetingDetectionTargetHealthRollup) -> dict[str, Any]:
    return {
        "target_id": row.target_id,
        "platform": row.platform,
        "registry_version": row.registry_version,
        "support_mode": row.support_mode,
        "rollup_date": row.rollup_date.isoformat(),
        "signal_families": row.signal_families_json or [],
        "outcomes": row.outcomes_json or {},
        "duration_buckets": row.duration_buckets_json or {},
        "reason_codes": row.reason_codes_json or [],
    }


def _registry_row(row: MeetingTargetRegistryVersion) -> dict[str, Any]:
    return {
        "registry_version_id": str(row.id),
        "registry_version": row.registry_version,
        "schema_version": row.schema_version,
        "status": row.status,
        "source": row.source,
        "etag": row.etag,
        "published_at": row.published_at.isoformat() if row.published_at else None,
        "target_count": len((row.document_json or {}).get("targets", [])),
    }


def _draft_registry_version(now: datetime | None = None) -> str:
    value = now or datetime.now(UTC)
    return f"{value:%Y.%m.%d}.{int(value.timestamp())}"
