from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import Any
from uuid import UUID

from sqlalchemy import or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.auth.context import TenantScope
from twobrain_rec_server.calendar.audit import (
    calendar_match_audit_metadata,
    write_calendar_audit_event,
)
from twobrain_rec_server.db.models import (
    CalendarEventSnapshot,
    CalendarParticipant,
    CalendarSource,
    ConferenceLinkCandidate,
    ExternalCalendar,
    Meeting,
    RecordingCalendarContextLink,
    RecordingCalendarMatchAttempt,
)
from twobrain_rec_server.domain.metadata_text import safe_metadata_text

MATCHER_VERSION = "calendar_auto_match_v1"
MAX_SELECTED_SOURCES = 4
MAX_CANDIDATE_ROWS = 50
MAX_VISIBLE_CANDIDATES = 10
MAX_ROSTER_ITEMS = 100
MAX_CONFERENCE_HASHES_PER_EVENT = 10
PRESTART_GRACE = timedelta(minutes=5)
RECENTLY_ENDED_GUARD = timedelta(minutes=5)
SOURCE_FRESHNESS = timedelta(hours=24)
ATTEMPT_TTL = timedelta(hours=24)


@dataclass(frozen=True, slots=True)
class CalendarMatchDecision:
    attempt_state: str
    safe_reason_code: str
    context_confidence: str
    candidate_event_ids: tuple[object, ...] = ()
    candidate_count: int = 0
    matched_event_id: object | None = None
    matched_event_starts_at: datetime | None = None
    matched_event_ends_at: datetime | None = None
    matched_title: str | None = None
    matched_title_state: str = "unavailable"
    matched_roster: tuple[dict[str, object], ...] = ()
    matched_roster_state: str = "not_available"
    matched_roster_count: int = 0
    recurring_series_key_sha256: str | None = None
    source_version_fingerprint_sha256: str | None = None
    freshness_class: str = "current"
    matcher_version: str = MATCHER_VERSION


def evaluate_calendar_match(
    *,
    sources: Sequence[object],
    events: Sequence[object],
    recording_started_at: datetime,
    evaluated_at: datetime,
    enforce_source_freshness: bool = True,
) -> CalendarMatchDecision:
    """Evaluate bounded, already-sanitized calendar snapshots without provider I/O."""

    recording_start = _as_utc(recording_started_at)
    evaluated = _as_utc(evaluated_at)
    if len(sources) > MAX_SELECTED_SOURCES or len(events) > MAX_CANDIDATE_ROWS:
        return _empty_decision(
            attempt_state="calendar_unavailable",
            reason="calendar_unavailable",
            freshness_class="unavailable",
        )

    selected_sources = [source for source in sources if _source_is_selected(source)]
    if not sources:
        return _empty_decision(
            attempt_state="calendar_unavailable",
            reason="calendar_not_connected",
            freshness_class="unavailable",
        )
    if not selected_sources:
        return _empty_decision(
            attempt_state="calendar_unavailable",
            reason="calendar_not_selected",
            freshness_class="unavailable",
        )

    source_by_id: dict[str, object] = {}
    freshness_by_source_id: dict[str, str] = {}
    for source in selected_sources:
        source_id = _identity(_read(source, "id"))
        if source_id:
            source_by_id[source_id] = source
        freshness, reason = _source_freshness(
            source,
            recording_started_at=recording_start,
            evaluated_at=evaluated,
        )
        if source_id:
            freshness_by_source_id[source_id] = freshness
        if freshness != "current" and enforce_source_freshness:
            return _empty_decision(
                attempt_state=(
                    "skipped_stale_calendar"
                    if freshness in {"stale", "latest_sync_failed", "never_synced"}
                    else "calendar_unavailable"
                ),
                reason=reason,
                freshness_class=freshness,
            )

    eligible: list[object] = []
    recently_ended: list[object] = []
    saw_private = False
    saw_all_day = False
    saw_weak_signal = False

    for event in events:
        source = source_by_id.get(_identity(_read(event, "calendar_source_id")))
        if source is None or not _event_matches_source_scope(event, source):
            continue
        starts_at = _optional_utc(_read(event, "starts_at"))
        ends_at = _optional_utc(_read(event, "ends_at"))
        if starts_at is None or ends_at is None or ends_at <= starts_at:
            continue
        if not _event_near_recording(
            starts_at=starts_at,
            ends_at=ends_at,
            recording_started_at=recording_start,
        ):
            continue
        if _event_is_all_day(event):
            saw_all_day = True
            continue
        if _event_is_private(event):
            saw_private = True
            continue
        if _event_is_cancelled_or_deleted(event):
            continue
        if not _event_has_strong_signal(event):
            saw_weak_signal = True
            continue
        if starts_at - PRESTART_GRACE <= recording_start < ends_at:
            eligible.append(event)
        elif ends_at <= recording_start <= ends_at + RECENTLY_ENDED_GUARD:
            recently_ended.append(event)

    if saw_private:
        return _empty_decision(
            attempt_state="skipped_private",
            reason="private_free_busy_skipped",
        )

    candidate_groups = _dedupe_candidate_groups(eligible)
    boundary_groups = _dedupe_candidate_groups(recently_ended)
    if candidate_groups and boundary_groups:
        representatives = _candidate_representatives(boundary_groups + candidate_groups)
        return CalendarMatchDecision(
            attempt_state="ambiguous",
            safe_reason_code="back_to_back_boundary",
            context_confidence="ambiguous",
            candidate_event_ids=tuple(
                _read(event, "id")
                for event in representatives[:MAX_VISIBLE_CANDIDATES]
                if _read(event, "id") is not None
            ),
            candidate_count=len(representatives),
        )

    if len(candidate_groups) > 1:
        representatives = _candidate_representatives(candidate_groups)
        return CalendarMatchDecision(
            attempt_state="ambiguous",
            safe_reason_code="multiple_time_candidates",
            context_confidence="ambiguous",
            candidate_event_ids=tuple(
                _read(event, "id")
                for event in representatives[:MAX_VISIBLE_CANDIDATES]
                if _read(event, "id") is not None
            ),
            candidate_count=len(candidate_groups),
        )

    if not candidate_groups:
        if saw_all_day:
            return _empty_decision(
                attempt_state="skipped_all_day",
                reason="all_day_skipped",
            )
        return _empty_decision(
            attempt_state="no_context",
            reason="weak_event_signal" if saw_weak_signal else "no_matching_event",
        )

    event = _candidate_representatives(candidate_groups)[0]
    starts_at = _as_utc(_read(event, "starts_at"))
    ends_at = _as_utc(_read(event, "ends_at"))
    roster, roster_count = _safe_roster(event)
    title = _safe_title(event)
    title_state = "available" if title is not None else _title_state(event)
    if title is None and title_state == "available" and _read(event, "title"):
        title_state = "policy_hidden"
    return CalendarMatchDecision(
        attempt_state=("provisional_prestart" if recording_start < starts_at else "matched_auto"),
        safe_reason_code="single_fresh_candidate",
        context_confidence="high",
        candidate_count=1,
        matched_event_id=_read(event, "id"),
        matched_event_starts_at=starts_at,
        matched_event_ends_at=ends_at,
        matched_title=title,
        matched_title_state=title_state,
        matched_roster=tuple(roster),
        matched_roster_state="available" if roster_count else "not_available",
        matched_roster_count=roster_count,
        recurring_series_key_sha256=_recurring_series_fingerprint(event),
        source_version_fingerprint_sha256=_source_version_fingerprint(event),
        freshness_class=freshness_by_source_id.get(
            _identity(_read(event, "calendar_source_id")),
            "current",
        ),
    )


def finalize_provisional_match(
    decision: CalendarMatchDecision,
    *,
    meeting_started_at: datetime | None,
    meeting_ended_at: datetime | None,
) -> CalendarMatchDecision:
    if decision.attempt_state != "provisional_prestart":
        return decision
    event_start = decision.matched_event_starts_at
    event_end = decision.matched_event_ends_at
    meeting_start = _optional_utc(meeting_started_at)
    meeting_end = _optional_utc(meeting_ended_at)
    overlaps = (
        event_start is not None
        and event_end is not None
        and meeting_start is not None
        and meeting_end is not None
        and meeting_start < event_end
        and meeting_end >= event_start
    )
    if overlaps:
        return replace(decision, attempt_state="matched_auto")
    return CalendarMatchDecision(
        attempt_state="no_context",
        safe_reason_code="prestart_not_reached",
        context_confidence="none",
        freshness_class=decision.freshness_class,
    )


async def resolve_recording_calendar_context(
    db: AsyncSession,
    tenant_scope: TenantScope,
    *,
    local_recording_id: str,
    idempotency_key: str,
    recording_started_at: datetime,
    decision_intent: object,
    selected_event_id: UUID | None = None,
    evaluated_at: datetime | None = None,
) -> RecordingCalendarMatchAttempt:
    intent = str(getattr(decision_intent, "value", decision_intent))
    evaluated = _as_utc(evaluated_at or datetime.now(UTC))
    recording_start = _as_utc(recording_started_at)
    idempotency_hash = _sha256_text(idempotency_key)
    request_fingerprint = _request_fingerprint(
        local_recording_id=local_recording_id,
        recording_started_at=recording_start,
        decision_intent=intent,
        selected_event_id=selected_event_id,
    )
    existing = await _find_existing_attempt(
        db,
        tenant_scope,
        local_recording_id=local_recording_id,
        idempotency_key_sha256=idempotency_hash,
    )
    if existing is not None:
        return _validate_idempotent_attempt(existing, request_fingerprint)

    if intent == "user_declined":
        decision = _empty_decision(
            attempt_state="declined_by_user",
            reason="user_declined",
        )
    else:
        sources, events = await _load_match_inputs(
            db,
            tenant_scope,
            recording_started_at=recording_start,
            selected_event_id=selected_event_id if intent == "user_selected" else None,
        )
        decision = evaluate_calendar_match(
            sources=sources,
            events=events,
            recording_started_at=recording_start,
            evaluated_at=evaluated,
            enforce_source_freshness=intent != "user_selected",
        )
        if intent == "user_selected":
            if selected_event_id is None or decision.matched_event_id != selected_event_id:
                raise ProblemDetail(
                    status=404,
                    code="calendar_context_candidate_not_found",
                    title="Calendar context candidate not found",
                )
            decision = replace(
                decision,
                attempt_state="matched_user",
                safe_reason_code="user_selected",
                context_confidence="selected",
            )
        elif intent != "automatic":
            raise ProblemDetail(
                status=400,
                code="invalid_calendar_match_intent",
                title="Invalid calendar match intent",
            )

    attempt = RecordingCalendarMatchAttempt(
        workspace_id=tenant_scope.workspace_id,
        owner_user_id=tenant_scope.user_id,
        device_id=tenant_scope.device_id,
        local_recording_id=local_recording_id,
        idempotency_key_sha256=idempotency_hash,
        request_fingerprint_sha256=request_fingerprint,
        recording_started_at=recording_start,
        decision_intent=intent,
        selected_event_snapshot_id=selected_event_id,
        attempt_state=decision.attempt_state,
        safe_reason_code=decision.safe_reason_code,
        context_confidence=decision.context_confidence,
        candidate_event_ids_json=[str(value) for value in decision.candidate_event_ids],
        candidate_count=decision.candidate_count,
        matched_event_snapshot_id=_as_uuid(decision.matched_event_id),
        matched_event_starts_at=decision.matched_event_starts_at,
        matched_event_ends_at=decision.matched_event_ends_at,
        matched_title=decision.matched_title,
        matched_title_state=decision.matched_title_state,
        matched_roster_json=list(decision.matched_roster),
        matched_roster_state=decision.matched_roster_state,
        matched_roster_count=decision.matched_roster_count,
        recurring_series_key_sha256=decision.recurring_series_key_sha256,
        source_version_fingerprint_sha256=decision.source_version_fingerprint_sha256,
        freshness_class=decision.freshness_class,
        matcher_version=MATCHER_VERSION,
        evaluated_at=evaluated,
        expires_at=evaluated + ATTEMPT_TTL,
    )
    try:
        async with db.begin_nested():
            db.add(attempt)
            await db.flush()
    except IntegrityError:
        existing = await _find_existing_attempt(
            db,
            tenant_scope,
            local_recording_id=local_recording_id,
            idempotency_key_sha256=idempotency_hash,
        )
        if existing is None:
            raise
        return _validate_idempotent_attempt(existing, request_fingerprint)
    await _write_match_audit(
        db,
        tenant_scope,
        event_type="calendar_match_resolved",
        outcome=attempt.attempt_state,
        safe_reason_code=attempt.safe_reason_code,
        matcher_version=attempt.matcher_version,
        candidate_count=attempt.candidate_count,
        roster_count=attempt.matched_roster_count,
        freshness_class=attempt.freshness_class,
        title_applied=False,
    )
    return attempt


async def consume_recording_calendar_match_attempt(
    db: AsyncSession,
    tenant_scope: TenantScope,
    *,
    meeting: object,
    attempt_id: UUID | None,
    consumed_at: datetime | None = None,
) -> RecordingCalendarContextLink:
    meeting_id = _as_uuid(_read(meeting, "id"))
    if meeting_id is None:
        raise ValueError("meeting must have a UUID id")
    existing_context = await db.scalar(
        select(RecordingCalendarContextLink).where(
            RecordingCalendarContextLink.workspace_id == tenant_scope.workspace_id,
            RecordingCalendarContextLink.meeting_id == meeting_id,
        )
    )
    if existing_context is not None:
        return existing_context

    consumed = _as_utc(consumed_at or datetime.now(UTC))
    attempt = await db.get(RecordingCalendarMatchAttempt, attempt_id) if attempt_id else None
    if not _attempt_can_back_meeting(
        attempt,
        tenant_scope=tenant_scope,
        meeting=meeting,
        consumed_at=consumed,
    ):
        context = _offline_context(
            tenant_scope=tenant_scope,
            meeting=meeting,
            evaluated_at=consumed,
        )
        db.add(context)
        await _write_context_audit(
            db,
            tenant_scope,
            context=context,
            meeting=meeting,
            title_applied=False,
        )
        return context

    assert attempt is not None
    claim = await db.execute(
        update(RecordingCalendarMatchAttempt)
        .where(
            RecordingCalendarMatchAttempt.id == attempt.id,
            RecordingCalendarMatchAttempt.workspace_id == tenant_scope.workspace_id,
            RecordingCalendarMatchAttempt.owner_user_id == tenant_scope.user_id,
            RecordingCalendarMatchAttempt.device_id == tenant_scope.device_id,
            RecordingCalendarMatchAttempt.local_recording_id
            == _read(meeting, "local_recording_id"),
            RecordingCalendarMatchAttempt.consumed_by_meeting_id.is_(None),
            RecordingCalendarMatchAttempt.consumed_at.is_(None),
            RecordingCalendarMatchAttempt.expires_at > consumed,
        )
        .values(consumed_by_meeting_id=meeting_id, consumed_at=consumed)
        .execution_options(synchronize_session=False)
    )
    if claim.rowcount != 1:
        context = _offline_context(
            tenant_scope=tenant_scope,
            meeting=meeting,
            evaluated_at=consumed,
        )
        db.add(context)
        await _write_context_audit(
            db,
            tenant_scope,
            context=context,
            meeting=meeting,
            title_applied=False,
        )
        return context
    if attempt.attempt_state == "provisional_prestart":
        finalized = finalize_provisional_match(
            _decision_from_attempt(attempt),
            meeting_started_at=_read(meeting, "started_at"),
            meeting_ended_at=_meeting_end(meeting),
        )
        _apply_decision_to_attempt(attempt, finalized)

    title_applied = await _apply_calendar_title(
        db,
        meeting=meeting,
        attempt=attempt,
        updated_at=consumed,
    )
    attempt.consumed_by_meeting_id = meeting_id
    attempt.consumed_at = consumed
    context = _context_from_attempt(
        tenant_scope=tenant_scope,
        meeting=meeting,
        attempt=attempt,
        title_applied=title_applied,
        linked_at=consumed,
    )
    db.add(context)
    await _write_context_audit(
        db,
        tenant_scope,
        context=context,
        meeting=meeting,
        title_applied=title_applied,
        freshness_class=attempt.freshness_class,
    )
    scrub_match_attempt_snapshot(attempt)
    return context


async def ensure_manual_upload_calendar_skip(
    db: AsyncSession,
    tenant_scope: TenantScope,
    *,
    meeting: object,
    evaluated_at: datetime | None = None,
) -> RecordingCalendarContextLink:
    meeting_id = _as_uuid(_read(meeting, "id"))
    if meeting_id is None:
        raise ValueError("meeting must have a UUID id")
    existing = await db.scalar(
        select(RecordingCalendarContextLink).where(
            RecordingCalendarContextLink.workspace_id == tenant_scope.workspace_id,
            RecordingCalendarContextLink.meeting_id == meeting_id,
        )
    )
    if existing is not None:
        return existing
    context = _skip_context(
        tenant_scope=tenant_scope,
        meeting=meeting,
        context_state="skipped_manual_upload",
        safe_reason_code="manual_upload_skipped",
        evaluated_at=_as_utc(evaluated_at or datetime.now(UTC)),
    )
    db.add(context)
    await _write_context_audit(
        db,
        tenant_scope,
        context=context,
        meeting=meeting,
        title_applied=False,
    )
    return context


def _empty_decision(
    *, attempt_state: str, reason: str, freshness_class: str = "current"
) -> CalendarMatchDecision:
    return CalendarMatchDecision(
        attempt_state=attempt_state,
        safe_reason_code=reason,
        context_confidence="none",
        freshness_class=freshness_class,
    )


def _source_is_selected(source: object) -> bool:
    if _read(source, "selected") is False:
        return False
    if str(_read(source, "connection_state", "active")) != "active":
        return False
    selected_count = _read(source, "selected_calendar_count", 1)
    return isinstance(selected_count, int) and selected_count > 0


def _source_freshness(
    source: object,
    *,
    recording_started_at: datetime,
    evaluated_at: datetime,
) -> tuple[str, str]:
    success = _optional_utc(_read(source, "last_successful_sync_at"))
    finished = _optional_utc(_read(source, "last_sync_finished_at"))
    sync_state = str(_read(source, "sync_state", "never_synced"))
    if success is None:
        return "never_synced", "selected_source_stale"
    if sync_state not in {"synced", "idle"} and (finished is None or finished >= success):
        return "latest_sync_failed", "latest_sync_failed"
    if finished is not None and finished > success:
        return "latest_sync_failed", "latest_sync_failed"
    if evaluated_at - success > SOURCE_FRESHNESS:
        return "stale", "selected_source_stale"
    horizon_start = _optional_utc(_read(source, "sync_horizon_start"))
    horizon_end = _optional_utc(_read(source, "sync_horizon_end"))
    if (
        horizon_start is None
        or horizon_end is None
        or recording_started_at < horizon_start
        or recording_started_at > horizon_end
    ):
        return "unavailable", "calendar_unavailable"
    return "current", "single_fresh_candidate"


def _event_matches_source_scope(event: object, source: object) -> bool:
    event_workspace = _identity(_read(event, "workspace_id"))
    source_workspace = _identity(_read(source, "workspace_id"))
    return not event_workspace or not source_workspace or event_workspace == source_workspace


def _event_near_recording(
    *, starts_at: datetime, ends_at: datetime, recording_started_at: datetime
) -> bool:
    return starts_at <= recording_started_at + PRESTART_GRACE and ends_at >= (
        recording_started_at - RECENTLY_ENDED_GUARD
    )


def _event_is_all_day(event: object) -> bool:
    return bool(_read(event, "all_day", False))


def _event_is_private(event: object) -> bool:
    privacy = str(_read(event, "privacy_class", "unknown")).lower()
    source_status = str(_read(event, "source_status", "unknown")).lower()
    title_state = _title_state(event)
    return (
        privacy in {"private", "confidential", "free_busy_only", "free_busy"}
        or source_status in {"private", "free_busy_only", "free_busy"}
        or title_state in {"private_redacted", "free_busy_only"}
    )


def _event_is_cancelled_or_deleted(event: object) -> bool:
    status = str(_read(event, "source_status", "unknown")).lower()
    return (
        status in {"cancelled", "canceled", "deleted"}
        or _read(event, "source_deleted_at") is not None
    )


def _event_has_strong_signal(event: object) -> bool:
    participants = _read(event, "participants", ()) or ()
    participant_count = _read(event, "participant_count")
    if participant_count is None:
        participant_count = (_read(event, "provider_extras_json", {}) or {}).get(
            "participant_count", 0
        )
    conference = _read(event, "conference_summary_json", {}) or {}
    return bool(
        participants
        or (isinstance(participant_count, int) and participant_count > 0)
        or _conference_hashes(event)
        or conference.get("meeting_link_present")
        or _read(event, "meeting_link_present", False)
        or _read(event, "location")
    )


def is_safe_calendar_context_candidate(
    event: object,
    *,
    participant_count: int | None = None,
) -> bool:
    """Return whether an event is eligible for an explicit 098 context choice.

    The explicit correction path deliberately reuses the matcher's privacy and
    meeting-signal boundary.  It does not make a private, all-day, cancelled,
    deleted, zero-duration, or otherwise unsafe snapshot selectable merely
    because an owner supplied its identifier.
    """

    starts_at = _optional_utc(_read(event, "starts_at"))
    ends_at = _optional_utc(_read(event, "ends_at"))
    if starts_at is None or ends_at is None or ends_at <= starts_at:
        return False
    if (
        _event_is_all_day(event)
        or _event_is_private(event)
        or _event_is_cancelled_or_deleted(event)
    ):
        return False
    if participant_count is not None and participant_count > 0:
        return True
    return _event_has_strong_signal(event)


def safe_calendar_event_title(event: object) -> str | None:
    """Expose the matcher's bounded safe-title projection to correction flows."""

    return _safe_title(event)


def calendar_event_recurring_series_fingerprint(event: object) -> str | None:
    """Return the same immutable recurring fingerprint used at auto-match time."""

    return _recurring_series_fingerprint(event)


def calendar_event_source_version_fingerprint(event: object) -> str | None:
    """Return the same immutable source fingerprint used at auto-match time."""

    return _source_version_fingerprint(event)


def order_previous_recurring_occurrences(
    occurrences: Sequence[object],
    *,
    before: datetime,
) -> list[object]:
    """Return strictly earlier occurrences in deterministic newest-first order."""

    boundary = _as_utc(before)
    earlier = [
        occurrence
        for occurrence in occurrences
        if (started_at := _optional_utc(_read(occurrence, "matched_event_starts_at"))) is not None
        and started_at < boundary
    ]
    return sorted(
        earlier,
        key=lambda occurrence: (
            _as_utc(_read(occurrence, "matched_event_starts_at")),
            _identity(_read(occurrence, "id")),
        ),
        reverse=True,
    )


def _dedupe_candidate_groups(events: Sequence[object]) -> list[list[object]]:
    if not events:
        return []
    parents = list(range(len(events)))

    def find(index: int) -> int:
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    def union(left: int, right: int) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root != right_root:
            parents[max(left_root, right_root)] = min(left_root, right_root)

    link_sets = [_conference_hashes(event) for event in events]
    identities = [_same_source_identity(event) for event in events]
    for left in range(len(events)):
        for right in range(left + 1, len(events)):
            if link_sets[left].intersection(link_sets[right]) or (
                identities[left] is not None and identities[left] == identities[right]
            ):
                union(left, right)

    groups: dict[int, list[object]] = {}
    for index, event in enumerate(events):
        groups.setdefault(find(index), []).append(event)
    return [groups[key] for key in sorted(groups)]


def _candidate_representatives(groups: Sequence[Sequence[object]]) -> list[object]:
    return sorted(
        (min(group, key=_event_sort_key) for group in groups),
        key=_event_sort_key,
    )


def _event_sort_key(event: object) -> tuple[datetime, str]:
    starts_at = _optional_utc(_read(event, "starts_at")) or datetime.max.replace(tzinfo=UTC)
    return starts_at, _identity(_read(event, "id"))


def _same_source_identity(event: object) -> tuple[str, str, str, str] | None:
    source_id = _identity(_read(event, "calendar_source_id"))
    calendar_id = _identity(_read(event, "external_calendar_id"))
    provider_event_id = _identity(_read(event, "provider_event_id"))
    if not source_id or not calendar_id or not provider_event_id:
        return None
    recurrence = _identity(_read(event, "recurrence_instance_id"))
    return source_id, calendar_id, provider_event_id, recurrence


def _conference_hashes(event: object) -> set[str]:
    hashes: set[str] = set()
    for value in _read(event, "conference_link_hashes", ()) or ():
        _add_safe_hash(hashes, value)
    conference = _read(event, "conference_summary_json", {}) or {}
    for value in conference.get("url_hashes", ()) or ():
        _add_safe_hash(hashes, value)
    _add_safe_hash(hashes, conference.get("url_hash"))
    for link in _read(event, "conference_links", ()) or ():
        if isinstance(link, Mapping):
            _add_safe_hash(hashes, link.get("url_hash"))
        else:
            _add_safe_hash(hashes, _read(link, "url_hash"))
    return set(sorted(hashes)[:MAX_CONFERENCE_HASHES_PER_EVENT])


def _add_safe_hash(values: set[str], value: object) -> None:
    if isinstance(value, str) and value and "://" not in value and len(value) <= 80:
        values.add(value)


def _safe_title(event: object) -> str | None:
    title = _read(event, "title")
    safe = bool(_read(event, "safe_to_use_as_title", _title_state(event) == "available"))
    if not safe:
        return None
    return safe_metadata_text(title, max_length=500)


def _title_state(event: object) -> str:
    state = _read(event, "title_state")
    if state is None:
        state = (_read(event, "provider_extras_json", {}) or {}).get("title_state")
    if state in {"available", "policy_hidden", "unavailable"}:
        return str(state)
    if state in {"private_redacted", "free_busy_only"}:
        return str(state)
    return "available" if _read(event, "safe_to_use_as_title", False) else "unavailable"


def _safe_roster(event: object) -> tuple[list[dict[str, object]], int]:
    participants = list(_read(event, "participants", ()) or ())
    count = _read(event, "participant_count")
    if count is None:
        count = (_read(event, "provider_extras_json", {}) or {}).get(
            "participant_count", len(participants)
        )
    count = max(int(count or 0), len(participants))
    return _safe_roster_snapshot(participants), count


def _safe_roster_snapshot(participants: Sequence[object]) -> list[dict[str, object]]:
    safe: list[dict[str, object]] = []
    for participant in participants[:MAX_ROSTER_ITEMS]:
        safe.append(
            {
                "participant_kind": (
                    safe_metadata_text(
                        _read(participant, "participant_kind", "unknown"),
                        max_length=80,
                    )
                    or "unknown"
                ),
                "response_status": (
                    safe_metadata_text(
                        _read(participant, "response_status", "unknown"),
                        max_length=80,
                    )
                    or "unknown"
                ),
                "display_name": safe_metadata_text(
                    _read(participant, "display_name"),
                    max_length=240,
                ),
                "email_present": bool(
                    _read(participant, "email")
                    or _read(participant, "email_hash")
                    or _read(participant, "email_present", False)
                ),
                "workspace_relation": (
                    safe_metadata_text(
                        _read(participant, "workspace_relation", "unknown"),
                        max_length=80,
                    )
                    or "unknown"
                ),
                "recipient_candidate_class": (
                    safe_metadata_text(
                        _read(participant, "recipient_candidate_class", "unknown"),
                        max_length=80,
                    )
                    or "unknown"
                ),
            }
        )
    return safe


def _recurring_series_fingerprint(event: object) -> str | None:
    series = _read(event, "recurring_series_id")
    if not series and _read(event, "recurrence_instance_id"):
        series = _read(event, "ical_uid")
    if not series:
        return None
    return _sha256_text(
        "|".join(
            (
                _identity(_read(event, "workspace_id")),
                _identity(_read(event, "calendar_source_id")),
                str(series),
            )
        )
    )


def _source_version_fingerprint(event: object) -> str | None:
    version = _read(event, "source_version")
    if not version:
        return None
    return _sha256_text(
        "|".join(
            (
                _identity(_read(event, "calendar_source_id")),
                _identity(_read(event, "id")),
                str(version),
            )
        )
    )


async def _load_match_inputs(
    db: AsyncSession,
    tenant_scope: TenantScope,
    *,
    recording_started_at: datetime,
    selected_event_id: UUID | None,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    source_rows = list(
        await db.scalars(
            select(CalendarSource)
            .where(
                CalendarSource.workspace_id == tenant_scope.workspace_id,
                CalendarSource.owner_user_id == tenant_scope.user_id,
                CalendarSource.connection_state == "active",
                CalendarSource.selected_calendar_count > 0,
            )
            .order_by(CalendarSource.id)
            .limit(MAX_SELECTED_SOURCES + 1)
        )
    )
    source_ids = [source.id for source in source_rows]
    calendars: list[ExternalCalendar] = []
    if source_ids:
        calendars = list(
            await db.scalars(
                select(ExternalCalendar).where(
                    ExternalCalendar.workspace_id == tenant_scope.workspace_id,
                    ExternalCalendar.calendar_source_id.in_(source_ids),
                    ExternalCalendar.selected.is_(True),
                )
            )
        )
    calendar_ids = {calendar.id for calendar in calendars}
    selected_by_source: dict[UUID, list[UUID]] = {}
    for calendar in calendars:
        selected_by_source.setdefault(calendar.calendar_source_id, []).append(calendar.id)

    source_payloads = [
        {
            "id": source.id,
            "workspace_id": source.workspace_id,
            "connection_state": source.connection_state,
            "sync_state": source.sync_state,
            "sync_horizon_start": source.sync_horizon_start,
            "sync_horizon_end": source.sync_horizon_end,
            "last_sync_finished_at": source.last_sync_finished_at,
            "last_successful_sync_at": source.last_successful_sync_at,
            "selected_calendar_count": len(selected_by_source.get(source.id, ())),
            "selected": bool(selected_by_source.get(source.id)),
        }
        for source in source_rows
    ]
    if not calendar_ids:
        return source_payloads, []

    event_query = select(CalendarEventSnapshot).where(
        CalendarEventSnapshot.workspace_id == tenant_scope.workspace_id,
        CalendarEventSnapshot.calendar_source_id.in_(source_ids),
        CalendarEventSnapshot.external_calendar_id.in_(calendar_ids),
    )
    if selected_event_id is not None:
        event_query = event_query.where(CalendarEventSnapshot.id == selected_event_id)
    else:
        event_query = event_query.where(
            CalendarEventSnapshot.starts_at <= recording_started_at + PRESTART_GRACE,
            CalendarEventSnapshot.ends_at >= recording_started_at - RECENTLY_ENDED_GUARD,
        )
    event_rows = list(
        await db.scalars(
            event_query.order_by(
                CalendarEventSnapshot.starts_at,
                CalendarEventSnapshot.id,
            ).limit(MAX_CANDIDATE_ROWS + 1)
        )
    )
    event_ids = [event.id for event in event_rows]
    participants_by_event: dict[UUID, list[CalendarParticipant]] = {}
    links_by_event: dict[UUID, list[ConferenceLinkCandidate]] = {}
    if event_ids:
        participant_rows = list(
            await db.scalars(
                select(CalendarParticipant)
                .where(
                    CalendarParticipant.workspace_id == tenant_scope.workspace_id,
                    CalendarParticipant.calendar_event_snapshot_id.in_(event_ids),
                )
                .order_by(
                    CalendarParticipant.calendar_event_snapshot_id,
                    CalendarParticipant.id,
                )
                .limit(MAX_CANDIDATE_ROWS * (MAX_ROSTER_ITEMS + 1))
            )
        )
        for participant in participant_rows:
            participants_by_event.setdefault(participant.calendar_event_snapshot_id, []).append(
                participant
            )
        link_rows = list(
            await db.scalars(
                select(ConferenceLinkCandidate)
                .where(
                    ConferenceLinkCandidate.workspace_id == tenant_scope.workspace_id,
                    ConferenceLinkCandidate.calendar_event_snapshot_id.in_(event_ids),
                )
                .order_by(
                    ConferenceLinkCandidate.calendar_event_snapshot_id,
                    ConferenceLinkCandidate.id,
                )
                .limit(MAX_CANDIDATE_ROWS * (MAX_CONFERENCE_HASHES_PER_EVENT + 1))
            )
        )
        for link in link_rows:
            links_by_event.setdefault(link.calendar_event_snapshot_id, []).append(link)

    event_payloads: list[dict[str, object]] = []
    for event in event_rows:
        participants = participants_by_event.get(event.id, [])
        links = links_by_event.get(event.id, [])
        extras = event.provider_extras_json or {}
        event_payloads.append(
            {
                "id": event.id,
                "workspace_id": event.workspace_id,
                "calendar_source_id": event.calendar_source_id,
                "external_calendar_id": event.external_calendar_id,
                "provider_event_id": event.provider_event_id,
                "ical_uid": event.ical_uid,
                "recurring_series_id": event.recurring_series_id,
                "recurrence_instance_id": event.recurrence_instance_id,
                "source_version": event.source_version,
                "source_status": event.source_status,
                "starts_at": event.starts_at,
                "ends_at": event.ends_at,
                "all_day": event.all_day,
                "title": event.title,
                "title_state": extras.get("title_state"),
                "location": event.location,
                "privacy_class": event.privacy_class,
                "conference_summary_json": event.conference_summary_json or {},
                "conference_link_hashes": [link.url_hash for link in links],
                "participant_count": int(extras.get("participant_count", len(participants))),
                "participants": participants,
                "safe_to_use_as_title": event.safe_to_use_as_title,
                "source_deleted_at": event.source_deleted_at,
            }
        )
    return source_payloads, event_payloads


async def _find_existing_attempt(
    db: AsyncSession,
    tenant_scope: TenantScope,
    *,
    local_recording_id: str,
    idempotency_key_sha256: str,
) -> RecordingCalendarMatchAttempt | None:
    return await db.scalar(
        select(RecordingCalendarMatchAttempt).where(
            RecordingCalendarMatchAttempt.workspace_id == tenant_scope.workspace_id,
            RecordingCalendarMatchAttempt.owner_user_id == tenant_scope.user_id,
            or_(
                RecordingCalendarMatchAttempt.local_recording_id == local_recording_id,
                RecordingCalendarMatchAttempt.idempotency_key_sha256 == idempotency_key_sha256,
            ),
        )
    )


def _validate_idempotent_attempt(
    attempt: RecordingCalendarMatchAttempt,
    request_fingerprint: str,
) -> RecordingCalendarMatchAttempt:
    if attempt.request_fingerprint_sha256 != request_fingerprint:
        raise ProblemDetail(
            status=409,
            code="calendar_match_idempotency_conflict",
            title="Calendar match request conflicts with an existing attempt",
        )
    return attempt


def _request_fingerprint(
    *,
    local_recording_id: str,
    recording_started_at: datetime,
    decision_intent: str,
    selected_event_id: UUID | None,
) -> str:
    payload = {
        "decision_intent": decision_intent,
        "local_recording_id": local_recording_id,
        "recording_started_at": _canonical_instant(recording_started_at),
        "selected_event_id": str(selected_event_id) if selected_event_id else None,
        "version": MATCHER_VERSION,
    }
    return _sha256_text(json.dumps(payload, separators=(",", ":"), sort_keys=True))


def _attempt_can_back_meeting(
    attempt: RecordingCalendarMatchAttempt | None,
    *,
    tenant_scope: TenantScope,
    meeting: object,
    consumed_at: datetime,
) -> bool:
    if attempt is None:
        return False
    meeting_id = _as_uuid(_read(meeting, "id"))
    return bool(
        attempt.workspace_id == tenant_scope.workspace_id
        and attempt.owner_user_id == tenant_scope.user_id
        and attempt.device_id == tenant_scope.device_id
        and attempt.local_recording_id == _read(meeting, "local_recording_id")
        and _read(meeting, "workspace_id") == tenant_scope.workspace_id
        and _read(meeting, "created_by_user_id") == tenant_scope.user_id
        and _read(meeting, "device_id") == tenant_scope.device_id
        and consumed_at < _as_utc(attempt.expires_at)
        and (attempt.consumed_by_meeting_id is None or attempt.consumed_by_meeting_id == meeting_id)
    )


def _decision_from_attempt(
    attempt: RecordingCalendarMatchAttempt,
) -> CalendarMatchDecision:
    return CalendarMatchDecision(
        attempt_state=attempt.attempt_state,
        safe_reason_code=attempt.safe_reason_code or "no_matching_event",
        context_confidence=attempt.context_confidence,
        candidate_event_ids=tuple(attempt.candidate_event_ids_json or ()),
        candidate_count=attempt.candidate_count,
        matched_event_id=attempt.matched_event_snapshot_id,
        matched_event_starts_at=_optional_utc(attempt.matched_event_starts_at),
        matched_event_ends_at=_optional_utc(attempt.matched_event_ends_at),
        matched_title=attempt.matched_title,
        matched_title_state=attempt.matched_title_state,
        matched_roster=tuple(attempt.matched_roster_json or ()),
        matched_roster_state=attempt.matched_roster_state,
        matched_roster_count=attempt.matched_roster_count,
        recurring_series_key_sha256=attempt.recurring_series_key_sha256,
        source_version_fingerprint_sha256=attempt.source_version_fingerprint_sha256,
        freshness_class=attempt.freshness_class,
        matcher_version=attempt.matcher_version,
    )


def _apply_decision_to_attempt(
    attempt: RecordingCalendarMatchAttempt,
    decision: CalendarMatchDecision,
) -> None:
    attempt.attempt_state = decision.attempt_state
    attempt.safe_reason_code = decision.safe_reason_code
    attempt.context_confidence = decision.context_confidence
    attempt.candidate_event_ids_json = [str(value) for value in decision.candidate_event_ids]
    attempt.candidate_count = decision.candidate_count
    attempt.matched_event_snapshot_id = _as_uuid(decision.matched_event_id)
    attempt.matched_event_starts_at = decision.matched_event_starts_at
    attempt.matched_event_ends_at = decision.matched_event_ends_at
    attempt.matched_title = decision.matched_title
    attempt.matched_title_state = decision.matched_title_state
    attempt.matched_roster_json = list(decision.matched_roster)
    attempt.matched_roster_state = decision.matched_roster_state
    attempt.matched_roster_count = decision.matched_roster_count


def scrub_match_attempt_snapshot(attempt: RecordingCalendarMatchAttempt) -> None:
    """Retain consumption correlation while removing duplicated context content."""

    attempt.selected_event_snapshot_id = None
    attempt.candidate_event_ids_json = []
    attempt.candidate_count = 0
    attempt.matched_event_snapshot_id = None
    attempt.matched_event_starts_at = None
    attempt.matched_event_ends_at = None
    attempt.matched_title = None
    attempt.matched_title_state = "unavailable"
    attempt.matched_roster_json = []
    attempt.matched_roster_state = "not_available"
    attempt.matched_roster_count = 0
    attempt.recurring_series_key_sha256 = None
    attempt.source_version_fingerprint_sha256 = None


async def _apply_calendar_title(
    db: AsyncSession,
    *,
    meeting: object,
    attempt: RecordingCalendarMatchAttempt,
    updated_at: datetime,
) -> bool:
    matched = attempt.attempt_state in {"matched_auto", "matched_user"}
    current_source = str(_read(meeting, "title_source", "legacy_unknown"))
    replaceable = current_source in {"app_context", "generic"} or (
        attempt.attempt_state == "matched_user" and current_source == "calendar"
    )
    safe_title = safe_metadata_text(attempt.matched_title, max_length=500)
    if not matched or not safe_title or not replaceable:
        return False
    meeting.title = safe_title
    meeting.title_source = "calendar"
    meeting.title_updated_at = updated_at
    meeting_id = _as_uuid(_read(meeting, "id"))
    model = meeting if isinstance(meeting, Meeting) else await db.get(Meeting, meeting_id)
    if model is not None and model is not meeting:
        model.title = safe_title
        model.title_source = "calendar"
        model.title_updated_at = updated_at
    return True


def _context_from_attempt(
    *,
    tenant_scope: TenantScope,
    meeting: object,
    attempt: RecordingCalendarMatchAttempt,
    title_applied: bool,
    linked_at: datetime,
) -> RecordingCalendarContextLink:
    matched = attempt.attempt_state in {"matched_auto", "matched_user"}
    matched_title = safe_metadata_text(attempt.matched_title, max_length=500) if matched else None
    matched_roster = (
        _safe_roster_snapshot(list(attempt.matched_roster_json or ())) if matched else []
    )
    return RecordingCalendarContextLink(
        workspace_id=tenant_scope.workspace_id,
        meeting_id=_as_uuid(_read(meeting, "id")),
        calendar_event_snapshot_id=(attempt.matched_event_snapshot_id if matched else None),
        match_attempt_id=attempt.id,
        context_state=attempt.attempt_state,
        context_confidence=attempt.context_confidence,
        context_reasons_json=[attempt.safe_reason_code] if attempt.safe_reason_code else [],
        title_source="calendar"
        if title_applied
        else str(_read(meeting, "title_source", "generic")),
        roster_source=(
            "calendar" if matched and attempt.matched_roster_state == "available" else "none"
        ),
        manual_override_state=(
            "declined_by_user" if attempt.attempt_state == "declined_by_user" else "none"
        ),
        safe_reason_code=attempt.safe_reason_code,
        decision_source=(
            "user"
            if attempt.attempt_state in {"matched_user", "declined_by_user"}
            else "automatic"
            if attempt.attempt_state in {"matched_auto", "provisional_prestart"}
            else "system_skip"
        ),
        matcher_version=attempt.matcher_version,
        evaluated_at=attempt.evaluated_at,
        candidate_event_ids_json=list(attempt.candidate_event_ids_json or ()),
        candidate_count=attempt.candidate_count,
        matched_event_starts_at=attempt.matched_event_starts_at if matched else None,
        matched_event_ends_at=attempt.matched_event_ends_at if matched else None,
        matched_title=matched_title,
        matched_title_state=(
            "available"
            if matched_title is not None
            else "policy_hidden"
            if matched and attempt.matched_title_state == "available" and attempt.matched_title
            else attempt.matched_title_state
            if matched
            else "unavailable"
        ),
        matched_roster_json=matched_roster,
        matched_roster_state=(attempt.matched_roster_state if matched else "not_available"),
        matched_roster_count=attempt.matched_roster_count if matched else 0,
        recurring_series_key_sha256=(attempt.recurring_series_key_sha256 if matched else None),
        source_version_fingerprint_sha256=(
            attempt.source_version_fingerprint_sha256 if matched else None
        ),
        linked_at=linked_at if matched else None,
    )


def _offline_context(
    *,
    tenant_scope: TenantScope,
    meeting: object,
    evaluated_at: datetime,
) -> RecordingCalendarContextLink:
    return _skip_context(
        tenant_scope=tenant_scope,
        meeting=meeting,
        context_state="skipped_offline_or_unknown",
        safe_reason_code="offline_or_unknown_skipped",
        evaluated_at=evaluated_at,
    )


def _skip_context(
    *,
    tenant_scope: TenantScope,
    meeting: object,
    context_state: str,
    safe_reason_code: str,
    evaluated_at: datetime,
) -> RecordingCalendarContextLink:
    return RecordingCalendarContextLink(
        workspace_id=tenant_scope.workspace_id,
        meeting_id=_as_uuid(_read(meeting, "id")),
        context_state=context_state,
        context_confidence="none",
        context_reasons_json=[safe_reason_code],
        title_source=str(_read(meeting, "title_source", "generic")),
        roster_source="none",
        manual_override_state="none",
        safe_reason_code=safe_reason_code,
        decision_source="system_skip",
        matcher_version=MATCHER_VERSION,
        evaluated_at=evaluated_at,
        candidate_event_ids_json=[],
        candidate_count=0,
        matched_title_state="unavailable",
        matched_roster_json=[],
        matched_roster_state="not_available",
        matched_roster_count=0,
    )


async def _write_context_audit(
    db: AsyncSession,
    tenant_scope: TenantScope,
    *,
    context: RecordingCalendarContextLink,
    meeting: object,
    title_applied: bool,
    freshness_class: str | None = None,
) -> None:
    title_source = str(_read(meeting, "title_source", "legacy_unknown"))
    user_override_preserved = not title_applied and title_source in {
        "user_confirmed",
        "upload_provided",
        "file_name_derived",
        "legacy_unknown",
    }
    await _write_match_audit(
        db,
        tenant_scope,
        event_type="calendar_match_consumed",
        outcome=context.context_state,
        safe_reason_code=context.safe_reason_code,
        matcher_version=context.matcher_version or MATCHER_VERSION,
        candidate_count=context.candidate_count,
        roster_count=context.matched_roster_count,
        freshness_class=freshness_class,
        title_applied=title_applied,
        user_override_preserved=True if user_override_preserved else None,
        meeting_id=_as_uuid(_read(meeting, "id")),
    )


async def _write_match_audit(
    db: AsyncSession,
    tenant_scope: TenantScope,
    *,
    event_type: str,
    outcome: str,
    safe_reason_code: str | None,
    matcher_version: str,
    candidate_count: int,
    roster_count: int,
    freshness_class: str | None,
    title_applied: bool,
    user_override_preserved: bool | None = None,
    meeting_id: UUID | None = None,
) -> None:
    decision_source = (
        "user"
        if outcome in {"matched_user", "declined_by_user", "cleared_by_user"}
        else "automatic"
        if outcome in {"matched_auto", "provisional_prestart"}
        else "system_skip"
    )
    metadata = calendar_match_audit_metadata(
        {
            "context_state": outcome,
            "safe_reason_code": safe_reason_code,
            "matcher_version": matcher_version,
            "candidate_count": candidate_count,
            "roster_count": roster_count,
            "freshness_class": freshness_class,
            "decision_source": decision_source,
            "title_applied": title_applied,
            "user_override_preserved": user_override_preserved,
        }
    )
    await write_calendar_audit_event(
        db,
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting_id,
        actor_user_id=tenant_scope.user_id,
        device_id=tenant_scope.device_id,
        event_type=event_type,
        outcome=outcome,
        safe_reason_code=safe_reason_code,
        metadata=metadata,
    )


def _meeting_end(meeting: object) -> datetime | None:
    ended_at = _optional_utc(_read(meeting, "ended_at"))
    if ended_at is not None:
        return ended_at
    started_at = _optional_utc(_read(meeting, "started_at"))
    duration = _read(meeting, "duration_seconds")
    if started_at is not None and isinstance(duration, int) and duration >= 0:
        return started_at + timedelta(seconds=duration)
    return None


def _read(value: object, key: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(key, default)
    return getattr(value, key, default)


def _identity(value: object) -> str:
    return "" if value is None else str(value)


def _as_uuid(value: object) -> UUID | None:
    if isinstance(value, UUID):
        return value
    if value is None:
        return None
    try:
        return UUID(str(value))
    except (ValueError, TypeError, AttributeError):
        return None


def _optional_utc(value: object) -> datetime | None:
    return _as_utc(value) if isinstance(value, datetime) else None


def _as_utc(value: object) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError("expected datetime")
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _canonical_instant(value: datetime) -> str:
    return _as_utc(value).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _sha256_text(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()
