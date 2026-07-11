from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.admin.audit import write_admin_audit_event
from twobrain_rec_server.admin.queries import AdminWorkspaceContext
from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.cabinet.access import AccessDecision
from twobrain_rec_server.cabinet.egress import artifact_egress_states, review_playback_state
from twobrain_rec_server.cabinet.queries import latest_processing_result
from twobrain_rec_server.db.models import Meeting, TrackArtifact
from twobrain_rec_server.domain.statuses import DeletionState, RetentionPolicyState


class AdminFileAccessOutcome(StrEnum):
    ALLOWED = "allowed"
    DENIED_CROSS_WORKSPACE = "denied_cross_workspace"
    DENIED_NOT_ADMIN = "denied_not_admin"
    UNAVAILABLE_MISSING_ARTIFACT = "unavailable_missing_artifact"
    UNAVAILABLE_DELETION_ACTIVE = "unavailable_deletion_active"
    UNAVAILABLE_RETENTION_OR_LIFECYCLE_BLOCK = "unavailable_retention_or_lifecycle_block"
    UNAVAILABLE_POST_EGRESS_LIMIT = "unavailable_post_egress_limit"
    DENIED_AUDIT_UNAVAILABLE = "denied_audit_unavailable"


@dataclass(frozen=True, slots=True)
class AdminFileAccessDecision:
    outcome: AdminFileAccessOutcome

    @property
    def allowed(self) -> bool:
        return self.outcome == AdminFileAccessOutcome.ALLOWED


def admin_file_access_decision(
    *,
    actor_role: str,
    actor_workspace_id: UUID,
    meeting_workspace_id: UUID,
    artifact_available: bool = True,
    deletion_active: bool = False,
    retention_or_lifecycle_block: bool = False,
    post_egress_limit: bool = False,
    audit_available: bool = True,
) -> AdminFileAccessDecision:
    if actor_workspace_id != meeting_workspace_id:
        return AdminFileAccessDecision(AdminFileAccessOutcome.DENIED_CROSS_WORKSPACE)
    if actor_role not in {"owner", "admin"}:
        return AdminFileAccessDecision(AdminFileAccessOutcome.DENIED_NOT_ADMIN)
    if not audit_available:
        return AdminFileAccessDecision(AdminFileAccessOutcome.DENIED_AUDIT_UNAVAILABLE)
    if deletion_active:
        return AdminFileAccessDecision(AdminFileAccessOutcome.UNAVAILABLE_DELETION_ACTIVE)
    if retention_or_lifecycle_block:
        return AdminFileAccessDecision(
            AdminFileAccessOutcome.UNAVAILABLE_RETENTION_OR_LIFECYCLE_BLOCK
        )
    if post_egress_limit:
        return AdminFileAccessDecision(AdminFileAccessOutcome.UNAVAILABLE_POST_EGRESS_LIMIT)
    if not artifact_available:
        return AdminFileAccessDecision(AdminFileAccessOutcome.UNAVAILABLE_MISSING_ARTIFACT)
    return AdminFileAccessDecision(AdminFileAccessOutcome.ALLOWED)


async def list_admin_files(
    db: AsyncSession,
    *,
    context: AdminWorkspaceContext,
    q: str | None = None,
    owner_user_id: UUID | None = None,
    file_type: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    processing_state: str | None = None,
    deletion_state: str | None = None,
    retention_state: str | None = None,
    min_size: int | None = None,
    max_size: int | None = None,
    min_duration: int | None = None,
    max_duration: int | None = None,
    limit: int = 50,
) -> dict[str, object]:
    meetings = (
        (
            await db.execute(
                select(Meeting)
                .where(Meeting.workspace_id == context.workspace_id)
                .order_by(Meeting.updated_at.desc())
            )
        )
        .scalars()
        .all()
    )
    rows: list[dict[str, object]] = []
    for meeting in meetings:
        if not _meeting_matches_filters(
            meeting,
            q=q,
            owner_user_id=owner_user_id,
            date_from=date_from,
            date_to=date_to,
            processing_state=processing_state,
            deletion_state=deletion_state,
            retention_state=retention_state,
            min_duration=min_duration,
            max_duration=max_duration,
        ):
            continue
        summary = await admin_file_summary(db, context=context, meeting=meeting)
        if not _summary_matches_filters(
            summary, file_type=file_type, min_size=min_size, max_size=max_size
        ):
            continue
        rows.append(summary)
        if len(rows) >= limit:
            break
    return {
        "files": rows,
        "filters": {
            "q": q,
            "owner_user_id": str(owner_user_id) if owner_user_id else None,
            "type": file_type,
            "date_from": date_from.isoformat() if date_from else None,
            "date_to": date_to.isoformat() if date_to else None,
            "processing_state": processing_state,
            "deletion_state": deletion_state,
            "retention_state": retention_state,
            "min_size": min_size,
            "max_size": max_size,
            "min_duration": min_duration,
            "max_duration": max_duration,
        },
    }


async def get_admin_file_detail(
    db: AsyncSession,
    *,
    context: AdminWorkspaceContext,
    meeting_id: UUID,
) -> dict[str, object]:
    meeting = await _load_workspace_meeting(db, context.workspace_id, meeting_id)
    return await admin_file_summary(db, context=context, meeting=meeting, include_actions=True)


async def record_admin_review_access(
    db: AsyncSession,
    *,
    context: AdminWorkspaceContext,
    meeting_id: UUID,
) -> dict[str, object]:
    meeting = await _load_workspace_meeting(db, context.workspace_id, meeting_id)
    decision = await _decision_for_meeting(db, context=context, meeting=meeting)
    access = admin_meeting_access(context)
    result = await latest_processing_result(
        db, workspace_id=context.workspace_id, meeting_id=meeting.id
    )
    review_state = await review_playback_state(db, meeting=meeting, access=access, result=result)
    allowed = decision.allowed and review_state.state == "available"
    await write_admin_audit_event(
        db,
        workspace_id=context.workspace_id,
        actor_user_id=context.actor_user_id,
        actor_role=context.actor_role,
        action="file_review_accessed",
        target_kind="meeting",
        target_id=str(meeting.id),
        outcome="allowed" if allowed else "denied",
        reason_code=decision.outcome.value
        if not decision.allowed
        else (review_state.reason or review_state.state),
    )
    if not allowed:
        code = (
            decision.outcome.value
            if not decision.allowed
            else (review_state.reason or "review_unavailable")
        )
        raise ProblemDetail(status=409, code=code, title="Meeting review unavailable")
    return {
        "meeting_id": str(meeting.id),
        "review_path": f"/admin/files/{meeting.id}",
        "access": {"outcome": decision.outcome.value},
        "review": review_state.model_dump(mode="json"),
    }


async def admin_file_summary(
    db: AsyncSession,
    *,
    context: AdminWorkspaceContext,
    meeting: Meeting,
    include_actions: bool = False,
) -> dict[str, object]:
    decision = await _decision_for_meeting(db, context=context, meeting=meeting)
    result = await latest_processing_result(
        db, workspace_id=context.workspace_id, meeting_id=meeting.id
    )
    access = admin_meeting_access(context)
    egress_states = await artifact_egress_states(db, meeting=meeting, access=access, result=result)
    review_state = await review_playback_state(db, meeting=meeting, access=access, result=result)
    artifact_stats = await _artifact_stats(db, meeting=meeting)
    artifact_classes = _artifact_classes(artifact_stats, result)
    available_downloads = [
        state.artifact_class
        for state in egress_states
        if state.action == "download"
        and state.state == "available"
        and state.artifact_class != "package"
    ]
    package_available = any(
        state.artifact_class == "package"
        and state.action == "export"
        and state.state == "available"
        for state in egress_states
    )
    payload: dict[str, object] = {
        "meeting_id": str(meeting.id),
        "title": meeting.title,
        "owner_user_id": str(meeting.created_by_user_id),
        "started_at": meeting.started_at.isoformat() if meeting.started_at else None,
        "duration_seconds": meeting.duration_seconds,
        "artifact_count": artifact_stats["artifact_count"],
        "total_size_bytes": artifact_stats["total_size_bytes"],
        "artifact_classes": artifact_classes,
        "processing_state": meeting.processing_status,
        "deletion_state": meeting.deletion_state,
        "retention_state": meeting.retention_policy_state,
        "access": {"outcome": decision.outcome.value},
        "review": review_state.model_dump(mode="json"),
        "egress": [state.model_dump(mode="json") for state in egress_states],
    }
    if include_actions:
        payload["actions"] = {
            "review": decision.allowed and review_state.state == "available",
            "download": decision.allowed and bool(available_downloads),
            "export": decision.allowed and package_available,
            "delete": context.actor_role in {"owner", "admin"}
            and meeting.deletion_state in {None, "none"},
        }
    return payload


async def ensure_admin_file_access_allowed(
    db: AsyncSession,
    *,
    context: AdminWorkspaceContext,
    meeting: Meeting,
) -> AdminFileAccessDecision:
    decision = await _decision_for_meeting(db, context=context, meeting=meeting)
    if not decision.allowed:
        raise ProblemDetail(
            status=409,
            code=decision.outcome.value,
            title="Meeting file egress unavailable",
        )
    return decision


def admin_meeting_access(context: AdminWorkspaceContext) -> AccessDecision:
    return AccessDecision(
        state="admin",
        label="Workspace admin",
        reason="Workspace admin access.",
        can_view=True,
        can_share=False,
        can_manage_team_visibility=False,
        can_download=True,
        can_export=True,
        role=context.actor_role,
    )


async def _decision_for_meeting(
    db: AsyncSession,
    *,
    context: AdminWorkspaceContext,
    meeting: Meeting,
) -> AdminFileAccessDecision:
    artifact_count = int(
        await db.scalar(
            select(func.count())
            .select_from(TrackArtifact)
            .where(
                TrackArtifact.workspace_id == meeting.workspace_id,
                TrackArtifact.meeting_id == meeting.id,
            )
        )
        or 0
    )
    deletion_state = meeting.deletion_state or DeletionState.NONE.value
    retention_state = meeting.retention_policy_state or RetentionPolicyState.NOT_CONFIGURED.value
    retention_or_lifecycle_block = retention_state in {
        RetentionPolicyState.BLOCKED.value,
        RetentionPolicyState.UNSAFE.value,
    } or deletion_state == DeletionState.POLICY_BLOCKED.value
    post_egress_limit = deletion_state == DeletionState.POST_EGRESS_LIMIT.value
    return admin_file_access_decision(
        actor_role=context.actor_role,
        actor_workspace_id=context.workspace_id,
        meeting_workspace_id=meeting.workspace_id,
        artifact_available=artifact_count > 0,
        deletion_active=deletion_state != DeletionState.NONE.value
        and not retention_or_lifecycle_block
        and not post_egress_limit,
        retention_or_lifecycle_block=retention_or_lifecycle_block,
        post_egress_limit=post_egress_limit,
    )


async def load_workspace_meeting(db: AsyncSession, workspace_id: UUID, meeting_id: UUID) -> Meeting:
    return await _load_workspace_meeting(db, workspace_id, meeting_id)


async def _load_workspace_meeting(
    db: AsyncSession, workspace_id: UUID, meeting_id: UUID
) -> Meeting:
    meeting = await db.scalar(
        select(Meeting).where(Meeting.workspace_id == workspace_id, Meeting.id == meeting_id)
    )
    if meeting is None:
        raise ProblemDetail(status=404, code="meeting_not_found", title="Meeting not found")
    return meeting


async def _artifact_stats(db: AsyncSession, *, meeting: Meeting) -> dict[str, int | bool]:
    rows = (
        await db.execute(
            select(TrackArtifact.track_role, TrackArtifact.byte_length).where(
                TrackArtifact.workspace_id == meeting.workspace_id,
                TrackArtifact.meeting_id == meeting.id,
            )
        )
    ).all()
    return {
        "artifact_count": len(rows),
        "total_size_bytes": sum(int(row[1] or 0) for row in rows),
        "has_audio": bool(rows),
    }


def _artifact_classes(artifact_stats: dict[str, int | bool], result: object | None) -> list[str]:
    classes = ["audio"] if artifact_stats.get("has_audio") else []
    if (
        result is not None
        and getattr(result, "transcript_status", None) == "available"
        and int(getattr(result, "segment_count", 0) or 0) > 0
    ):
        classes.append("transcript")
    if result is not None and getattr(result, "summary_status", None) == "available":
        classes.append("summary")
    return classes


def _meeting_matches_filters(
    meeting: Meeting,
    *,
    q: str | None,
    owner_user_id: UUID | None,
    date_from: date | None,
    date_to: date | None,
    processing_state: str | None,
    deletion_state: str | None,
    retention_state: str | None,
    min_duration: int | None,
    max_duration: int | None,
) -> bool:
    if q:
        haystack = " ".join(
            str(value).lower()
            for value in (
                meeting.id,
                meeting.title,
                meeting.local_recording_id,
                meeting.created_by_user_id,
            )
            if value is not None
        )
        if q.strip().lower() not in haystack:
            return False
    if owner_user_id is not None and meeting.created_by_user_id != owner_user_id:
        return False
    if date_from is not None and (
        meeting.started_at is None or meeting.started_at.date() < date_from
    ):
        return False
    if date_to is not None and (meeting.started_at is None or meeting.started_at.date() > date_to):
        return False
    if processing_state and meeting.processing_status != processing_state:
        return False
    if deletion_state and (meeting.deletion_state or "none") != deletion_state:
        return False
    if retention_state and (meeting.retention_policy_state or "not_configured") != retention_state:
        return False
    if min_duration is not None and meeting.duration_seconds < min_duration:
        return False
    return not (max_duration is not None and meeting.duration_seconds > max_duration)


def _summary_matches_filters(
    summary: dict[str, object],
    *,
    file_type: str | None,
    min_size: int | None,
    max_size: int | None,
) -> bool:
    if file_type:
        classes = {str(item) for item in summary.get("artifact_classes", [])}
        if file_type not in classes and file_type != "meeting":
            return False
    total_size = int(summary.get("total_size_bytes") or 0)
    if min_size is not None and total_size < min_size:
        return False
    return not (max_size is not None and total_size > max_size)
