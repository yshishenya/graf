from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.auth.context import TenantScope
from twobrain_rec_server.db.models import (
    MeetingDetectionCandidate,
    MeetingDetectionTargetHealthRollup,
    MeetingDetectionTelemetryBatch,
    MeetingDetectionTelemetryRateLimitBucket,
)
from twobrain_rec_server.meeting_detection.candidates import (
    SERVER_CANDIDATE_MIN_SCORE,
    aggregate_unknown_native_rollups,
    upload_allowed,
)
from twobrain_rec_server.meeting_detection.redaction import (
    MeetingDetectionRedactionError,
    assert_metadata_only,
)

DAILY_ROLLUP_LIMIT = 1
DAILY_ROLLUP_WINDOW = timedelta(days=1)


@dataclass(frozen=True, slots=True)
class MeetingDetectionTelemetryResult:
    batch_id: Any
    dedupe_status: str
    accepted_target_rollup_count: int
    accepted_candidate_count: int
    suppressed_candidate_count: int
    registry_version: str
    next_upload_after: datetime


class MeetingDetectionTelemetryError(RuntimeError):
    def __init__(self, *, status: int, code: str, title: str, detail: str | None = None) -> None:
        super().__init__(code)
        self.status = status
        self.code = code
        self.title = title
        self.detail = detail


async def submit_meeting_detection_telemetry(
    *,
    tenant_scope: TenantScope,
    db: AsyncSession | None,
    payload: Mapping[str, Any],
    idempotency_key: str | None,
    received_at: datetime | None = None,
) -> MeetingDetectionTelemetryResult:
    if db is None:
        raise MeetingDetectionTelemetryError(
            status=503,
            code="meeting_detection_store_unavailable",
            title="Meeting detection store unavailable",
        )
    if not idempotency_key:
        raise MeetingDetectionTelemetryError(
            status=422,
            code="meeting_detection_telemetry_schema_invalid",
            title="Idempotency key required",
        )
    now = received_at or datetime.now(UTC)
    payload_dict = dict(payload)
    try:
        assert_metadata_only(payload_dict)
        _validate_unknown_rollups(payload_dict)
    except MeetingDetectionRedactionError as exc:
        raise MeetingDetectionTelemetryError(
            status=400,
            code="meeting_detection_telemetry_unsafe_payload",
            title="Meeting detection telemetry contains unsafe content",
        ) from exc

    payload_fingerprint = _fingerprint(payload_dict)
    idempotency_fingerprint = _fingerprint(idempotency_key)
    existing_batch = await _load_existing_batch(
        tenant_scope=tenant_scope,
        db=db,
        idempotency_fingerprint=idempotency_fingerprint,
    )
    if existing_batch is not None:
        if existing_batch.payload_fingerprint != payload_fingerprint:
            raise MeetingDetectionTelemetryError(
                status=409,
                code="meeting_detection_telemetry_idempotency_conflict",
                title="Meeting detection telemetry idempotency conflict",
            )
        return MeetingDetectionTelemetryResult(
            batch_id=existing_batch.id,
            dedupe_status="duplicate",
            accepted_target_rollup_count=0,
            accepted_candidate_count=0,
            suppressed_candidate_count=0,
            registry_version=existing_batch.registry_version,
            next_upload_after=now + DAILY_ROLLUP_WINDOW,
        )

    await _touch_daily_rate_limit(tenant_scope=tenant_scope, db=db, now=now)
    batch = _build_batch(
        tenant_scope=tenant_scope,
        payload=payload_dict,
        idempotency_fingerprint=idempotency_fingerprint,
        payload_fingerprint=payload_fingerprint,
        now=now,
    )
    db.add(batch)
    await db.flush()
    accepted_target_count = await _store_target_health_rollups(
        tenant_scope=tenant_scope,
        db=db,
        batch=batch,
        payload=payload_dict,
    )
    accepted_candidate_count = await _store_candidates(
        tenant_scope=tenant_scope,
        db=db,
        batch=batch,
        payload=payload_dict,
    )
    unknown_rollups = list(payload_dict.get("unknownNativeAppRollups", []))
    suppressed_candidate_count = max(0, len(unknown_rollups) - accepted_candidate_count)
    await db.flush()
    return MeetingDetectionTelemetryResult(
        batch_id=batch.id,
        dedupe_status="created",
        accepted_target_rollup_count=accepted_target_count,
        accepted_candidate_count=accepted_candidate_count,
        suppressed_candidate_count=suppressed_candidate_count,
        registry_version=str(payload_dict["registryVersion"]),
        next_upload_after=now + DAILY_ROLLUP_WINDOW,
    )


def _fingerprint(value: Any) -> str:
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return sha256(canonical.encode("utf-8")).hexdigest()


async def _load_existing_batch(
    *,
    tenant_scope: TenantScope,
    db: AsyncSession,
    idempotency_fingerprint: str,
) -> MeetingDetectionTelemetryBatch | None:
    return await db.scalar(
        select(MeetingDetectionTelemetryBatch).where(
            MeetingDetectionTelemetryBatch.workspace_id == tenant_scope.workspace_id,
            MeetingDetectionTelemetryBatch.device_id == tenant_scope.device_id,
            MeetingDetectionTelemetryBatch.idempotency_key_fingerprint == idempotency_fingerprint,
        )
    )


async def _touch_daily_rate_limit(*, tenant_scope: TenantScope, db: AsyncSession, now: datetime) -> None:
    bucket = await db.scalar(
        select(MeetingDetectionTelemetryRateLimitBucket).where(
            MeetingDetectionTelemetryRateLimitBucket.workspace_id == tenant_scope.workspace_id,
            MeetingDetectionTelemetryRateLimitBucket.user_id == tenant_scope.user_id,
            MeetingDetectionTelemetryRateLimitBucket.device_id == tenant_scope.device_id,
            MeetingDetectionTelemetryRateLimitBucket.bucket_key == "daily_rollup",
        )
    )
    if bucket is None:
        db.add(
            MeetingDetectionTelemetryRateLimitBucket(
                workspace_id=tenant_scope.workspace_id,
                user_id=tenant_scope.user_id,
                device_id=tenant_scope.device_id,
                bucket_key="daily_rollup",
                window_started_at=now,
                attempt_count=1,
            )
        )
        await db.flush()
        return
    window_started_at = _aware(bucket.window_started_at)
    blocked_until = _aware(bucket.blocked_until) if bucket.blocked_until is not None else None
    if blocked_until is not None and blocked_until > now:
        raise _rate_limited(blocked_until)
    if now - window_started_at >= DAILY_ROLLUP_WINDOW:
        bucket.window_started_at = now
        bucket.attempt_count = 1
        bucket.blocked_until = None
        await db.flush()
        return
    bucket.attempt_count += 1
    if bucket.attempt_count > DAILY_ROLLUP_LIMIT:
        bucket.blocked_until = window_started_at + DAILY_ROLLUP_WINDOW
        await db.flush()
        raise _rate_limited(_aware(bucket.blocked_until))
    await db.flush()


def _rate_limited(blocked_until: datetime) -> MeetingDetectionTelemetryError:
    return MeetingDetectionTelemetryError(
        status=429,
        code="meeting_detection_telemetry_rate_limited",
        title="Meeting detection telemetry rate limited",
        detail=f"next_upload_after={blocked_until.isoformat()}",
    )


def _build_batch(
    *,
    tenant_scope: TenantScope,
    payload: Mapping[str, Any],
    idempotency_fingerprint: str,
    payload_fingerprint: str,
    now: datetime,
) -> MeetingDetectionTelemetryBatch:
    window = payload["rollupWindow"]
    return MeetingDetectionTelemetryBatch(
        workspace_id=tenant_scope.workspace_id,
        user_id=tenant_scope.user_id,
        device_id=tenant_scope.device_id,
        idempotency_key_fingerprint=idempotency_fingerprint,
        payload_fingerprint=payload_fingerprint,
        schema_version=int(payload["schemaVersion"]),
        client_version=str(payload["clientVersion"]),
        platform=str(payload["platform"]),
        os_version_major=str(payload["osVersionMajor"]),
        registry_version=str(payload["registryVersion"]),
        candidate_filter_version=str(payload["candidateFilterVersion"]),
        rollup_started_at=_parse_datetime(str(window["startedAt"])),
        rollup_ended_at=_parse_datetime(str(window["endedAt"])),
        policy_json=dict(payload["policy"]),
        resource_rollup_json=dict(payload["resourceRollup"]),
        redaction_result="accepted",
        received_at=now,
    )


async def _store_target_health_rollups(
    *,
    tenant_scope: TenantScope,
    db: AsyncSession,
    batch: MeetingDetectionTelemetryBatch,
    payload: Mapping[str, Any],
) -> int:
    count = 0
    rollup_date = batch.rollup_started_at.date()
    for rollup in payload.get("targetRollups", []):
        db.add(
            MeetingDetectionTargetHealthRollup(
                workspace_id=tenant_scope.workspace_id,
                target_id=str(rollup["targetId"]),
                platform=str(payload["platform"]),
                registry_version=str(payload["registryVersion"]),
                client_version_bucket=str(payload["clientVersion"]),
                os_version_major=str(payload["osVersionMajor"]),
                rollup_date=rollup_date,
                support_mode=str(rollup["supportMode"]),
                signal_families_json=list(rollup.get("signalFamilies", [])),
                outcomes_json=dict(rollup.get("outcomes", {})),
                duration_buckets_json=dict(rollup.get("durationBuckets", {})),
                reason_codes_json=list(rollup.get("reasonCodes", [])),
            )
        )
        count += 1
    return count


async def _store_candidates(
    *,
    tenant_scope: TenantScope,
    db: AsyncSession,
    batch: MeetingDetectionTelemetryBatch,
    payload: Mapping[str, Any],
) -> int:
    accepted_count = 0
    rollup_date = batch.rollup_started_at.date()
    aggregates = aggregate_unknown_native_rollups(list(payload.get("unknownNativeAppRollups", [])))
    for aggregate in aggregates:
        if not aggregate.bundle_id:
            continue
        candidate = await db.scalar(
            select(MeetingDetectionCandidate).where(
                MeetingDetectionCandidate.workspace_id == tenant_scope.workspace_id,
                MeetingDetectionCandidate.platform == aggregate.platform,
                MeetingDetectionCandidate.bundle_id == aggregate.bundle_id,
            )
        )
        if candidate is None:
            candidate = MeetingDetectionCandidate(
                workspace_id=tenant_scope.workspace_id,
                platform=aggregate.platform,
                bundle_id=aggregate.bundle_id,
                display_name=aggregate.display_name,
                signing_team_id=aggregate.signing_team_id,
                first_seen_bucket=rollup_date,
            )
            db.add(candidate)
        candidate.last_seen_bucket = rollup_date
        candidate.last_batch_id = batch.id
        candidate.candidate_score = max(candidate.candidate_score or 0, aggregate.candidate_score)
        candidate.candidate_reasons_json = sorted(aggregate.candidate_reasons)
        candidate.suppression_reasons_json = sorted(aggregate.suppression_reasons)
        candidate.version_samples_json = aggregate.version_samples
        candidate.stable_observation_count = (
            candidate.stable_observation_count or 0
        ) + aggregate.stable_observation_count
        candidate.reporting_installation_count = max(
            1,
            (candidate.reporting_installation_count or 0) + 1,
        )
        candidate.manual_record_nearby_count = (
            candidate.manual_record_nearby_count or 0
        ) + aggregate.manual_record_nearby_count
        candidate.calendar_or_join_hint_count = (
            candidate.calendar_or_join_hint_count or 0
        ) + aggregate.calendar_or_join_hint_count
        candidate.updated_at = _aware(batch.received_at)
        accepted_count += 1
    return accepted_count


def _validate_unknown_rollups(payload: Mapping[str, Any]) -> None:
    for index, rollup in enumerate(payload.get("unknownNativeAppRollups", [])):
        identity_mode = rollup.get("identityMode")
        upload_eligibility = rollup.get("uploadEligibility")
        score = int(rollup.get("candidateScore", 0))
        if identity_mode == "redacted" and any(
            key in rollup for key in ("bundleId", "displayName", "signingTeamId", "version")
        ):
            raise _schema_invalid(index, "redacted_unknown_identity_contains_raw_fields")
        if upload_eligibility == "server_candidate_upload":
            if identity_mode != "raw_candidate_allowed":
                raise _schema_invalid(index, "server_upload_requires_raw_candidate_identity")
            if score < SERVER_CANDIDATE_MIN_SCORE:
                raise _schema_invalid(index, "server_upload_candidate_score_too_low")
            if not rollup.get("bundleId") or not rollup.get("displayName"):
                raise _schema_invalid(index, "server_upload_missing_candidate_identity")
            if not upload_allowed(dict(rollup)):
                raise _schema_invalid(index, "server_upload_candidate_suppressed")


def _schema_invalid(index: int, reason: str) -> MeetingDetectionTelemetryError:
    return MeetingDetectionTelemetryError(
        status=422,
        code="meeting_detection_telemetry_schema_invalid",
        title="Meeting detection telemetry schema invalid",
        detail=f"unknownNativeAppRollups[{index}]={reason}",
    )


def _parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
