from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.auth.context import TenantScope
from twobrain_rec_server.config import Settings
from twobrain_rec_server.db.models.normalization import PlaybackNormalizationJob
from twobrain_rec_server.db.models.support import (
    SUPPORT_INCIDENT_GITHUB_REPO,
    SupportIncident,
    SupportIncidentRateLimitBucket,
)
from twobrain_rec_server.normalization.audit import (
    add_normalization_audit_event,
    build_audit_receipt,
)
from twobrain_rec_server.normalization.statuses import (
    NormalizationReason,
    PlannedAction,
    TriggerKind,
)
from twobrain_rec_server.support.github_issues import (
    GitHubIssueClientError,
    build_github_issue_draft,
    updated_deduped_issue_body,
)
from twobrain_rec_server.support.redaction import (
    SupportIncidentRedactionError,
    build_server_redacted_report,
    derive_affected_identity,
    derive_dedupe_key,
    stable_report_fingerprint,
)

SUPPORT_INCIDENT_RATE_LIMIT_SCOPE = "support_incident_intake"
SUPPORT_INCIDENT_SYNC_RATE_LIMIT_SCOPE = "support_incident_sync"


@dataclass(frozen=True, slots=True)
class SupportIncidentSubmissionResult:
    incident_id: str
    incident_status: str
    github_issue_number: int | None
    github_issue_url: str | None
    dedupe_status: str
    affected_count: int


class SupportIncidentSubmissionError(RuntimeError):
    def __init__(self, *, status: int, code: str, title: str, detail: str | None = None) -> None:
        super().__init__(code)
        self.status = status
        self.code = code
        self.title = title
        self.detail = detail


def support_incident_configuration_status(settings: Settings) -> str:
    """Return a bounded startup readiness state without exposing credential material."""

    if (
        settings.support_incident_github_owner != "yshishenya"
        or settings.support_incident_github_repo != "crisp"
    ):
        return "configuration_invalid"
    token_file = settings.support_incident_github_token_file
    if token_file is None:
        return "not_configured"
    try:
        return "configured" if token_file.read_text(encoding="utf-8").strip() else "configuration_invalid"
    except OSError:
        return "configuration_invalid"


@dataclass(frozen=True, slots=True)
class PlaybackNormalizationIncidentResult:
    incident_id: str
    created: bool


async def record_playback_normalization_incident(
    *,
    db: AsyncSession,
    job: PlaybackNormalizationJob,
    reason_code: NormalizationReason,
    cooldown_cycle: int,
    recorded_at: datetime | None = None,
) -> PlaybackNormalizationIncidentResult:
    """Persist one content-free operational incident for a cooldown escalation."""

    if cooldown_cycle < 1:
        raise ValueError("cooldown_cycle must be positive")
    now = recorded_at or datetime.now(UTC)
    receipt = build_audit_receipt(
        "playback_normalization_incident_recorded",
        {"reason_code": reason_code.value, "cooldown_cycle": cooldown_cycle},
    )
    job_fingerprint = "job_fpr_" + sha256(str(job.id).encode("utf-8")).hexdigest()[:20]
    profile_fingerprint = "profile_fpr_" + sha256(
        job.profile_version.encode("utf-8")
    ).hexdigest()[:20]
    dedupe_material = ":".join(
        (str(job.id), job.profile_version, reason_code.value, str(cooldown_cycle))
    )
    dedupe_key = "playback_norm_" + sha256(dedupe_material.encode("utf-8")).hexdigest()
    report = {
        "schema_version": "playback_normalization_incident_v1",
        "redaction_state": "metadata_only",
        "problem_code": "playback_normalization.retry_cycle_exhausted",
        "failure_category": reason_code.value,
        "retry_class": "automatic",
        "job_fingerprint": job_fingerprint,
        "profile_fingerprint": profile_fingerprint,
        "cooldown_cycle": cooldown_cycle,
        "audit_event": receipt.event_type,
    }
    report_fingerprint = "report_fpr_" + sha256(
        json.dumps(report, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    existing = await db.scalar(
        select(SupportIncident).where(
            SupportIncident.workspace_id == job.workspace_id,
            SupportIncident.dedupe_key == dedupe_key,
        )
    )
    if existing is not None:
        existing.last_duplicate_received_at = now
        existing.last_received_at = now
        await db.flush()
        return PlaybackNormalizationIncidentResult(
            incident_id=str(existing.id),
            created=False,
        )

    incident = SupportIncident(
        workspace_id=job.workspace_id,
        reporter_user_id=job.requested_by_user_id,
        device_id=job.source_device_id,
        dedupe_key=dedupe_key,
        problem_code="playback_normalization.retry_cycle_exhausted",
        failure_category=reason_code.value,
        retry_class="automatic",
        status="system_recorded",
        affected_count=1,
        safe_affected_identities=[job_fingerprint],
        latest_safe_report_json=report,
        latest_safe_report_fingerprint=report_fingerprint,
        first_received_at=now,
        last_received_at=now,
        redaction_result="accepted",
        github_repo=SUPPORT_INCIDENT_GITHUB_REPO,
    )
    try:
        async with db.begin_nested():
            db.add(incident)
            await db.flush()
    except IntegrityError:
        existing = await db.scalar(
            select(SupportIncident).where(
                SupportIncident.workspace_id == job.workspace_id,
                SupportIncident.dedupe_key == dedupe_key,
            )
        )
        if existing is None:
            raise
        return PlaybackNormalizationIncidentResult(
            incident_id=str(existing.id),
            created=False,
        )
    add_normalization_audit_event(
        db,
        workspace_id=job.workspace_id,
        meeting_id=job.meeting_id,
        media_revision_id=job.media_revision_id,
        actor_user_id=job.requested_by_user_id,
        device_id=job.source_device_id,
        event_type=receipt.event_type,
        metadata={"reason_code": reason_code.value, "cooldown_cycle": cooldown_cycle},
        created_at=now,
    )
    return PlaybackNormalizationIncidentResult(incident_id=str(incident.id), created=True)


async def record_impossible_legacy_normalization_incident(
    *,
    db: AsyncSession,
    job: PlaybackNormalizationJob,
    reason_code: NormalizationReason,
    recorded_at: datetime | None = None,
) -> PlaybackNormalizationIncidentResult:
    """Persist exactly one metadata-only incident for an impossible legacy source."""

    if job.trigger_kind != TriggerKind.LEGACY_BACKFILL.value or reason_code not in {
        NormalizationReason.SOURCE_MISSING,
        NormalizationReason.SOURCE_MISMATCH,
    }:
        raise ValueError("legacy source incident identity is invalid")
    now = recorded_at or datetime.now(UTC)
    receipt = build_audit_receipt(
        "playback_normalization_legacy_source_unavailable",
        {
            "reason_code": reason_code.value,
            "trigger_kind": TriggerKind.LEGACY_BACKFILL.value,
            "planned_action": PlannedAction.UNAVAILABLE_SOURCE.value,
        },
    )
    job_fingerprint = "job_fpr_" + sha256(str(job.id).encode("utf-8")).hexdigest()[:20]
    profile_fingerprint = "profile_fpr_" + sha256(
        job.profile_version.encode("utf-8")
    ).hexdigest()[:20]
    dedupe_key = "playback_norm_legacy_" + sha256(
        f"{job.id}:{job.profile_version}:{reason_code.value}".encode()
    ).hexdigest()
    report = {
        "schema_version": "playback_normalization_incident_v1",
        "redaction_state": "metadata_only",
        "problem_code": "playback_normalization.legacy_source_unavailable",
        "failure_category": reason_code.value,
        "retry_class": "terminal",
        "job_fingerprint": job_fingerprint,
        "profile_fingerprint": profile_fingerprint,
        "audit_event": receipt.event_type,
    }
    report_fingerprint = "report_fpr_" + sha256(
        json.dumps(report, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    existing = await db.scalar(
        select(SupportIncident).where(
            SupportIncident.workspace_id == job.workspace_id,
            SupportIncident.dedupe_key == dedupe_key,
        )
    )
    if existing is not None:
        existing.last_duplicate_received_at = now
        existing.last_received_at = now
        await db.flush()
        return PlaybackNormalizationIncidentResult(
            incident_id=str(existing.id),
            created=False,
        )
    incident = SupportIncident(
        workspace_id=job.workspace_id,
        reporter_user_id=job.requested_by_user_id,
        device_id=job.source_device_id,
        dedupe_key=dedupe_key,
        problem_code="playback_normalization.legacy_source_unavailable",
        failure_category=reason_code.value,
        retry_class="terminal",
        status="system_recorded",
        affected_count=1,
        safe_affected_identities=[job_fingerprint],
        latest_safe_report_json=report,
        latest_safe_report_fingerprint=report_fingerprint,
        first_received_at=now,
        last_received_at=now,
        redaction_result="accepted",
        github_repo=SUPPORT_INCIDENT_GITHUB_REPO,
    )
    try:
        async with db.begin_nested():
            db.add(incident)
            await db.flush()
    except IntegrityError:
        existing = await db.scalar(
            select(SupportIncident).where(
                SupportIncident.workspace_id == job.workspace_id,
                SupportIncident.dedupe_key == dedupe_key,
            )
        )
        if existing is None:
            raise
        return PlaybackNormalizationIncidentResult(
            incident_id=str(existing.id),
            created=False,
        )
    return PlaybackNormalizationIncidentResult(incident_id=str(incident.id), created=True)


async def submit_support_incident(
    *,
    settings: Settings,
    tenant_scope: TenantScope,
    db: AsyncSession | None,
    payload: Mapping[str, Any],
    github_client: Any | None,
    github_failure_code: str | None = None,
    idempotency_key: str | None = None,
    received_at: datetime | None = None,
) -> SupportIncidentSubmissionResult:
    if db is None:
        raise SupportIncidentSubmissionError(
            status=503,
            code="support_incident.configuration_invalid",
            title="Support incident store unavailable",
        )
    now = received_at or datetime.now(UTC)
    try:
        report = build_server_redacted_report(payload, received_at=now)
    except SupportIncidentRedactionError as exc:
        raise _redaction_error(exc) from exc
    report = _apply_server_scope(report, tenant_scope)

    idempotency_fingerprint = _idempotency_fingerprint(idempotency_key)
    idempotency_report_fingerprint = (
        str(report["safe_report_fingerprint"]) if idempotency_fingerprint else None
    )
    idempotent_incident = await _load_idempotent_incident(
        tenant_scope=tenant_scope,
        db=db,
        idempotency_fingerprint=idempotency_fingerprint,
    )
    if idempotent_incident is not None:
        stored_report_fingerprint = idempotent_incident.last_idempotency_report_fingerprint
        if (
            stored_report_fingerprint is not None
            and stored_report_fingerprint != idempotency_report_fingerprint
        ) or (
            stored_report_fingerprint is None
            and idempotent_incident.dedupe_key != str(report["dedupe_key"])
        ):
            raise SupportIncidentSubmissionError(
                status=409,
                code="support_incident.idempotency_conflict",
                title="Idempotency key conflict",
            )
        _ensure_incident_number(idempotent_incident)
        await db.flush()
        return _result_from_incident(idempotent_incident, dedupe_status="updated")

    await _touch_rate_limit(
        settings=settings,
        tenant_scope=tenant_scope,
        db=db,
        now=now,
        rate_limit_scope=SUPPORT_INCIDENT_RATE_LIMIT_SCOPE,
    )
    incident, dedupe_status = await _upsert_incident(
        tenant_scope=tenant_scope,
        db=db,
        report=report,
        now=now,
        idempotency_fingerprint=idempotency_fingerprint,
        idempotency_report_fingerprint=idempotency_report_fingerprint,
    )
    _ensure_incident_number(incident)
    await db.flush()
    return await _synchronize_incident(
        settings=settings,
        db=db,
        incident=incident,
        github_client=github_client,
        github_failure_code=github_failure_code,
        dedupe_status=dedupe_status,
        now=now,
    )


async def sync_support_incident(
    *,
    settings: Settings,
    tenant_scope: TenantScope,
    db: AsyncSession | None,
    incident_id: str,
    github_client: Any | None,
    github_failure_code: str | None = None,
    received_at: datetime | None = None,
) -> SupportIncidentSubmissionResult:
    if db is None:
        raise SupportIncidentSubmissionError(
            status=503,
            code="support_incident.configuration_invalid",
            title="Support incident store unavailable",
        )
    incident = await db.scalar(
        select(SupportIncident).where(
            SupportIncident.workspace_id == tenant_scope.workspace_id,
            SupportIncident.reporter_user_id == tenant_scope.user_id,
            SupportIncident.incident_number == incident_id,
        )
    )
    if incident is None:
        raise SupportIncidentSubmissionError(
            status=404,
            code="support_incident.not_found",
            title="Support incident not found",
        )
    _ensure_incident_number(incident)
    if incident.github_issue_number is not None:
        return _result_from_incident(incident, dedupe_status="updated")

    now = received_at or datetime.now(UTC)
    await _touch_rate_limit(
        settings=settings,
        tenant_scope=tenant_scope,
        db=db,
        now=now,
        rate_limit_scope=SUPPORT_INCIDENT_SYNC_RATE_LIMIT_SCOPE,
    )
    return await _synchronize_incident(
        settings=settings,
        db=db,
        incident=incident,
        github_client=github_client,
        github_failure_code=github_failure_code,
        dedupe_status="updated",
        now=now,
    )


async def _synchronize_incident(
    *,
    settings: Settings,
    db: AsyncSession,
    incident: SupportIncident,
    github_client: Any | None,
    github_failure_code: str | None,
    dedupe_status: str,
    now: datetime,
) -> SupportIncidentSubmissionResult:
    _ensure_incident_number(incident)
    if github_client is None:
        _mark_sync_pending(
            incident,
            github_failure_code or "support_incident.configuration_invalid",
        )
        await db.flush()
        return _result_from_incident(incident, dedupe_status=dedupe_status)

    owner = settings.support_incident_github_owner
    repo = settings.support_incident_github_repo
    try:
        await github_client.validate_repository_ready(owner=owner, repo=repo)
        issue = await _create_or_update_issue(
            github_client=github_client,
            owner=owner,
            repo=repo,
            incident=incident,
            dedupe_status=dedupe_status,
        )
    except GitHubIssueClientError as exc:
        _mark_sync_pending(incident, exc.reason_code)
        await db.flush()
        return _result_from_incident(incident, dedupe_status=dedupe_status)

    issue_number = int(issue["number"])
    incident.github_issue_number = issue_number
    incident.github_issue_url = str(issue.get("html_url") or "")
    incident.github_issue_state = str(issue.get("state") or "open")
    incident.github_last_synced_at = now
    incident.github_failure_code = None
    incident.status = "synced"
    await db.flush()
    return _result_from_incident(incident, dedupe_status=dedupe_status)


def _ensure_incident_number(incident: SupportIncident) -> None:
    if incident.incident_number is None:
        incident.incident_number = f"CUST-{incident.id.hex[:12].upper()}"


def _mark_sync_pending(incident: SupportIncident, failure_code: str) -> None:
    incident.status = "pending_github"
    incident.github_failure_code = failure_code


def _redaction_error(exc: SupportIncidentRedactionError) -> SupportIncidentSubmissionError:
    if exc.code == "support_incident.unsupported_schema":
        return SupportIncidentSubmissionError(
            status=422,
            code=exc.code,
            title="Unsupported support incident schema",
        )
    return SupportIncidentSubmissionError(
        status=400,
        code="support_incident.unsafe_payload",
        title="Unsafe support incident payload",
    )


async def _touch_rate_limit(
    *,
    settings: Settings,
    tenant_scope: TenantScope,
    db: AsyncSession,
    now: datetime,
    rate_limit_scope: str,
) -> None:
    bucket = await db.scalar(
        select(SupportIncidentRateLimitBucket).where(
            SupportIncidentRateLimitBucket.workspace_id == tenant_scope.workspace_id,
            SupportIncidentRateLimitBucket.reporter_user_id == tenant_scope.user_id,
            SupportIncidentRateLimitBucket.device_id == tenant_scope.device_id,
            SupportIncidentRateLimitBucket.dedupe_key == rate_limit_scope,
        )
    )
    window = timedelta(seconds=int(settings.support_incident_rate_limit_window_seconds))
    blocked_until = (
        _aware(bucket.blocked_until)
        if bucket is not None and bucket.blocked_until is not None
        else None
    )
    if blocked_until is not None and blocked_until > now:
        raise _rate_limited()
    if bucket is None:
        bucket = SupportIncidentRateLimitBucket(
            workspace_id=tenant_scope.workspace_id,
            reporter_user_id=tenant_scope.user_id,
            device_id=tenant_scope.device_id,
            dedupe_key=rate_limit_scope,
            window_started_at=now,
            attempt_count=1,
            last_attempt_at=now,
        )
        db.add(bucket)
    elif now - _aware(bucket.window_started_at) >= window:
        bucket.window_started_at = now
        bucket.attempt_count = 1
        bucket.last_attempt_at = now
        bucket.blocked_until = None
    else:
        bucket.attempt_count += 1
        bucket.last_attempt_at = now
    if bucket.attempt_count > int(settings.support_incident_rate_limit_max_attempts):
        bucket.blocked_until = now + window
        await db.flush()
        raise _rate_limited()
    await db.flush()


def _rate_limited() -> SupportIncidentSubmissionError:
    return SupportIncidentSubmissionError(
        status=429,
        code="support_incident.rate_limited",
        title="Support incident rate limited",
        detail="Support intake is temporarily rate limited.",
    )


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _apply_server_scope(report: Mapping[str, Any], tenant_scope: TenantScope) -> dict[str, Any]:
    scoped = dict(report)
    device_fingerprint = _scope_fingerprint(tenant_scope.device_id, prefix="dev_fpr")
    scoped["workspace_fingerprint"] = _scope_fingerprint(tenant_scope.workspace_id, prefix="ws_fpr")
    scoped["user_fingerprint"] = _scope_fingerprint(tenant_scope.user_id, prefix="usr_fpr")
    scoped["device_fingerprint"] = device_fingerprint
    scoped["safe_device_identifier"] = f"device:{device_fingerprint}"
    scoped["safe_report_fingerprint"] = stable_report_fingerprint(scoped)
    scoped["dedupe_key"] = derive_dedupe_key(scoped)
    scoped["affected_identity_fingerprint"] = derive_affected_identity(scoped)
    return scoped


def _scope_fingerprint(value: object, *, prefix: str) -> str:
    return prefix + "_" + sha256(str(value).encode("utf-8")).hexdigest()[:12]


async def _upsert_incident(
    *,
    tenant_scope: TenantScope,
    db: AsyncSession,
    report: Mapping[str, Any],
    now: datetime,
    idempotency_fingerprint: str | None,
    idempotency_report_fingerprint: str | None,
) -> tuple[SupportIncident, str]:
    dedupe_key = str(report["dedupe_key"])
    incident = await db.scalar(
        select(SupportIncident).where(
            SupportIncident.workspace_id == tenant_scope.workspace_id,
            SupportIncident.dedupe_key == dedupe_key,
        )
    )
    affected_count = _reported_affected_count(report)
    report_identities = _reported_safe_identities(report)
    identity = str(report.get("affected_identity_fingerprint") or "unknown")
    identities_to_merge = report_identities or [identity]
    if incident is None:
        incident = SupportIncident(
            workspace_id=tenant_scope.workspace_id,
            reporter_user_id=tenant_scope.user_id,
            device_id=tenant_scope.device_id,
            dedupe_key=dedupe_key,
            problem_code=str(report.get("problem_code") or "unknown"),
            failure_category=str(report.get("failure_category") or "unknown"),
            retry_class=str(report.get("retry_class") or "unknown"),
            status="pending_github",
            affected_count=affected_count,
            safe_affected_identities=identities_to_merge[:5],
            latest_safe_report_json=dict(report),
            latest_safe_report_fingerprint=str(report["safe_report_fingerprint"]),
            last_idempotency_key_fingerprint=idempotency_fingerprint,
            last_idempotency_report_fingerprint=idempotency_report_fingerprint,
            first_received_at=now,
            last_received_at=now,
            redaction_result=str(report.get("redaction_result") or "accepted"),
            github_repo=SUPPORT_INCIDENT_GITHUB_REPO,
        )
        db.add(incident)
        await db.flush()
        return incident, "created"

    is_replay = (
        idempotency_fingerprint is not None
        and incident.last_idempotency_key_fingerprint == idempotency_fingerprint
        and (
            incident.last_idempotency_report_fingerprint is None
            or incident.last_idempotency_report_fingerprint == idempotency_report_fingerprint
        )
    )
    if not is_replay:
        incident.affected_count += affected_count
    identities = list(incident.safe_affected_identities or [])
    for identity in identities_to_merge:
        if identity not in identities and len(identities) < 5:
            identities.append(identity)
    incident.safe_affected_identities = identities
    incident.latest_safe_report_json = dict(report)
    incident.latest_safe_report_fingerprint = str(report["safe_report_fingerprint"])
    incident.last_idempotency_key_fingerprint = (
        idempotency_fingerprint or incident.last_idempotency_key_fingerprint
    )
    incident.last_idempotency_report_fingerprint = (
        idempotency_report_fingerprint or incident.last_idempotency_report_fingerprint
    )
    incident.last_received_at = now
    if not is_replay:
        incident.last_duplicate_received_at = now
    incident.redaction_result = str(report.get("redaction_result") or incident.redaction_result)
    await db.flush()
    return incident, "updated"


async def _load_idempotent_incident(
    *,
    tenant_scope: TenantScope,
    db: AsyncSession,
    idempotency_fingerprint: str | None,
) -> SupportIncident | None:
    if idempotency_fingerprint is None:
        return None
    return await db.scalar(
        select(SupportIncident).where(
            SupportIncident.workspace_id == tenant_scope.workspace_id,
            SupportIncident.last_idempotency_key_fingerprint == idempotency_fingerprint,
        )
    )


def _reported_affected_count(report: Mapping[str, Any]) -> int:
    value = report.get("affected_count")
    if isinstance(value, int) and value > 0:
        return value
    return 1


def _reported_safe_identities(report: Mapping[str, Any]) -> list[str]:
    value = report.get("safe_affected_identities")
    if not isinstance(value, list):
        return []
    return [
        item
        for item in value[:5]
        if isinstance(item, str) and item and item != "redacted_metadata"
    ]


def _result_from_incident(
    incident: SupportIncident, *, dedupe_status: str
) -> SupportIncidentSubmissionResult:
    if incident.incident_number is None:
        raise RuntimeError("Support incident is missing a correlation number")
    synced = incident.github_issue_number is not None
    return SupportIncidentSubmissionResult(
        incident_id=incident.incident_number,
        incident_status="synced" if synced else "pending_sync",
        github_issue_number=incident.github_issue_number,
        github_issue_url=str(incident.github_issue_url) if incident.github_issue_url else None,
        dedupe_status=dedupe_status,
        affected_count=incident.affected_count,
    )


def _idempotency_fingerprint(idempotency_key: str | None) -> str | None:
    if not idempotency_key:
        return None
    return "idem_fpr_" + sha256(idempotency_key.encode("utf-8")).hexdigest()[:32]


async def _create_or_update_issue(
    *,
    github_client: Any,
    owner: str,
    repo: str,
    incident: SupportIncident,
    dedupe_status: str,
) -> Mapping[str, Any]:
    if incident.incident_number is None:
        raise RuntimeError("Support incident is missing a correlation number")
    report = incident.latest_safe_report_json
    draft = build_github_issue_draft(
        report,
        affected_count=incident.affected_count,
        safe_affected_identities=incident.safe_affected_identities,
        incident_number=incident.incident_number,
        sync_status="synced",
    )
    if dedupe_status == "updated" and incident.github_issue_number is not None:
        existing = await github_client.get_issue(
            owner=owner, repo=repo, issue_number=incident.github_issue_number
        )
        body = updated_deduped_issue_body(
            str(existing.get("body") or ""),
            report,
            affected_count=incident.affected_count,
            safe_affected_identities=incident.safe_affected_identities,
            incident_number=incident.incident_number,
            sync_status="synced",
        )
        return await github_client.update_issue(
            owner=owner,
            repo=repo,
            issue_number=incident.github_issue_number,
            draft=replace(draft, body=body),
        )
    return await github_client.create_issue(owner=owner, repo=repo, draft=draft)
