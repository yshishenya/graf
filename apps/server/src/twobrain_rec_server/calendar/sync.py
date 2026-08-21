from __future__ import annotations

import asyncio
import random
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import partial
from typing import Any
from uuid import UUID

from cryptography.fernet import InvalidToken
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.auth.context import TenantScope
from twobrain_rec_server.calendar.conference_links import safe_open_meeting_url
from twobrain_rec_server.calendar.credentials import (
    safe_credential_failure,
    seal_credential,
    unseal_credential,
)
from twobrain_rec_server.calendar.normalize import NormalizedCalendarEvent
from twobrain_rec_server.calendar.providers import (
    MAX_PROVIDER_PAGES,
    CalendarCatalogEntry,
    CalendarEventPage,
    CalendarProvider,
    CalendarProviderError,
)
from twobrain_rec_server.db.models import (
    CalendarCredentialEnvelope,
    CalendarEventSnapshot,
    CalendarParticipant,
    CalendarSource,
    ConferenceLinkCandidate,
    ExternalCalendar,
)

MAX_CONFERENCE_LINK_HASHES_PER_EVENT = 10
PROVIDER_RETRY_DELAYS_SECONDS = (0.5, 1.5)


@dataclass(frozen=True, slots=True)
class CalendarSyncRunResult:
    state: str
    event_count: int = 0
    calendar_count: int = 0
    safe_reason_code: str | None = None


async def run_calendar_provider_sync(
    db: AsyncSession,
    *,
    tenant_scope: TenantScope,
    source_id: UUID,
    provider: CalendarProvider,
    credential_encryption_key: bytes,
    now: datetime | None = None,
) -> CalendarSyncRunResult:
    """Run one bounded provider sync using the existing snapshot persistence."""

    source = await db.scalar(
        select(CalendarSource).where(
            CalendarSource.id == source_id,
            CalendarSource.workspace_id == tenant_scope.workspace_id,
            CalendarSource.owner_user_id == tenant_scope.user_id,
        )
    )
    if source is None:
        return CalendarSyncRunResult("not_found", safe_reason_code="calendar_source_not_found")
    if source.disconnected_at is not None or source.connection_state == "disconnected":
        source.sync_state = "failed_closed"
        return CalendarSyncRunResult("failed_closed", safe_reason_code="source_disconnected")
    if source.credential_state != "sealed":
        source.sync_state = "failed_closed"
        return CalendarSyncRunResult("failed_closed", safe_reason_code="invalid_credentials")

    envelope = await db.scalar(
        select(CalendarCredentialEnvelope).where(
            CalendarCredentialEnvelope.calendar_source_id == source.id,
            CalendarCredentialEnvelope.workspace_id == tenant_scope.workspace_id,
            CalendarCredentialEnvelope.purged_at.is_(None),
        )
    )
    if envelope is None or not envelope.sealed_payload:
        source.sync_state = "failed_closed"
        source.credential_state = "invalid"
        source.last_safe_error_code = "invalid_credentials"
        return CalendarSyncRunResult("failed", safe_reason_code="invalid_credentials")
    try:
        credential = unseal_credential(envelope.sealed_payload, credential_encryption_key)
    except (InvalidToken, UnicodeDecodeError, ValueError):
        source.sync_state = "failed_closed"
        source.credential_state = "invalid"
        source.last_safe_error_code = "invalid_credentials"
        return CalendarSyncRunResult("failed", safe_reason_code="invalid_credentials")

    finished_at = now or datetime.now(UTC)
    horizon_start, horizon_end = future_sync_horizon(finished_at)
    calendars = list(
        await db.scalars(
            select(ExternalCalendar).where(
                ExternalCalendar.calendar_source_id == source.id,
                ExternalCalendar.workspace_id == tenant_scope.workspace_id,
                ExternalCalendar.selected.is_(True),
                ExternalCalendar.visibility.in_({"available", "selected", "shared", "delegated"}),
            )
        )
    )
    if not calendars:
        try:
            catalog: list[CalendarCatalogEntry] = []
            page_token: str | None = None
            seen_page_tokens: set[str] = set()
            for _ in range(MAX_PROVIDER_PAGES):
                entries, page_token = await _retry_provider_read(
                    partial(provider.list_calendars, credential, page_token=page_token)
                )
                catalog.extend(entries)
                if not page_token:
                    break
                if page_token in seen_page_tokens:
                    raise CalendarProviderError("invalid_payload")
                seen_page_tokens.add(page_token)
            else:
                raise CalendarProviderError("invalid_payload")
        except CalendarProviderError as error:
            source = await _lock_sync_source(db, tenant_scope, source_id)
            if source is None:
                return CalendarSyncRunResult(
                    "failed_closed", safe_reason_code="source_disconnected"
                )
            source.sync_state = "failed"
            source.last_sync_finished_at = finished_at
            source.last_safe_error_code = error.safe_code
            if error.safe_code in {"invalid_credentials", "revoked_access"}:
                source.credential_state = "invalid"
            return CalendarSyncRunResult("failed", safe_reason_code=error.safe_code)
        except Exception:
            source = await _lock_sync_source(db, tenant_scope, source_id)
            if source is None:
                return CalendarSyncRunResult(
                    "failed_closed", safe_reason_code="source_disconnected"
                )
            source.sync_state = "failed"
            source.last_sync_finished_at = finished_at
            source.last_safe_error_code = "provider_unavailable"
            return CalendarSyncRunResult("failed", safe_reason_code="provider_unavailable")
        if not catalog:
            source = await _lock_sync_source(db, tenant_scope, source_id)
            if source is None:
                return CalendarSyncRunResult(
                    "failed_closed", safe_reason_code="source_disconnected"
                )
            source.sync_state = "failed"
            source.last_sync_finished_at = finished_at
            source.last_safe_error_code = "calendar_catalog_empty"
            return CalendarSyncRunResult("failed", safe_reason_code="calendar_catalog_empty")
        source = await _lock_sync_source(db, tenant_scope, source_id)
        if source is None:
            return CalendarSyncRunResult("failed_closed", safe_reason_code="source_disconnected")
        await _replace_calendar_catalog(db, source, catalog)
        source.last_sync_started_at = finished_at
        source.sync_horizon_start = horizon_start
        source.sync_horizon_end = horizon_end
        source.sync_state = "never_synced"
        source.last_sync_finished_at = finished_at
        return CalendarSyncRunResult("catalog_updated", calendar_count=len(catalog))

    total_events = 0
    pending_results: list[
        tuple[ExternalCalendar, list[NormalizedCalendarEvent], str | None, bool]
    ] = []
    try:
        for calendar in calendars:
            page_token: str | None = None
            sync_token = calendar.sync_token
            retried_full = False
            while True:
                events: list[Any] = []
                next_sync_token: str | None = sync_token
                try:
                    seen_page_tokens: set[str] = set()
                    for _ in range(MAX_PROVIDER_PAGES):
                        page: CalendarEventPage = await _retry_provider_read(
                            partial(
                                provider.list_events,
                                credential,
                                calendar_id=calendar.provider_calendar_id,
                                time_min=horizon_start if not sync_token else None,
                                time_max=horizon_end if not sync_token else None,
                                page_token=page_token,
                                sync_token=sync_token,
                            )
                        )
                        events.extend(page.events)
                        next_sync_token = page.next_sync_token or next_sync_token
                        page_token = page.next_page_token
                        if not page_token:
                            break
                        if page_token in seen_page_tokens:
                            raise CalendarProviderError("invalid_payload")
                        seen_page_tokens.add(page_token)
                    else:
                        raise CalendarProviderError("invalid_payload")
                except CalendarProviderError as error:
                    if error.safe_code == "cursor_invalid" and sync_token and not retried_full:
                        sync_token = None
                        page_token = None
                        retried_full = True
                        continue
                    raise
                if any(not isinstance(event, NormalizedCalendarEvent) for event in events):
                    raise CalendarProviderError("invalid_payload")
                normalized_events = list(events)
                pending_results.append(
                    (calendar, normalized_events, next_sync_token, sync_token is None)
                )
                total_events += len(normalized_events)
                break
    except CalendarProviderError as error:
        source = await _lock_sync_source(db, tenant_scope, source_id)
        if source is None:
            return CalendarSyncRunResult("failed_closed", safe_reason_code="source_disconnected")
        source.last_sync_finished_at = finished_at
        source.last_safe_error_code = error.safe_code
        source.sync_state = "stale" if source.last_successful_sync_at else "failed"
        if error.safe_code in {"invalid_credentials", "revoked_access"}:
            source.credential_state = "invalid"
        return CalendarSyncRunResult("failed", total_events, len(calendars), error.safe_code)
    except Exception:
        source = await _lock_sync_source(db, tenant_scope, source_id)
        if source is None:
            return CalendarSyncRunResult("failed_closed", safe_reason_code="source_disconnected")
        source.last_sync_finished_at = finished_at
        source.last_safe_error_code = "provider_unavailable"
        source.sync_state = "stale" if source.last_successful_sync_at else "failed"
        return CalendarSyncRunResult("failed", total_events, len(calendars), "provider_unavailable")

    source = await _lock_sync_source(db, tenant_scope, source_id)
    if source is None:
        return CalendarSyncRunResult("failed_closed", safe_reason_code="source_disconnected")
    source.last_sync_started_at = finished_at
    source.sync_horizon_start = horizon_start
    source.sync_horizon_end = horizon_end
    for calendar, events, next_sync_token, full_sync in pending_results:
        await apply_calendar_sync_result(
            db,
            tenant_scope=tenant_scope,
            source=source,
            calendar=calendar,
            events=events,
            sync_token=next_sync_token,
            synced_at=finished_at,
            full_sync=full_sync,
            credential_encryption_key=credential_encryption_key,
        )

    source.last_sync_finished_at = finished_at
    source.last_successful_sync_at = finished_at
    source.sync_state = "synced"
    source.last_safe_error_code = None
    return CalendarSyncRunResult("synced", total_events, len(calendars))


async def _retry_provider_read(call: Callable[[], Awaitable[Any]]) -> Any:
    for attempt in range(len(PROVIDER_RETRY_DELAYS_SECONDS) + 1):
        try:
            return await call()
        except CalendarProviderError as error:
            if not error.retryable or attempt == len(PROVIDER_RETRY_DELAYS_SECONDS):
                raise
            base_delay = PROVIDER_RETRY_DELAYS_SECONDS[attempt]
            await asyncio.sleep(base_delay * random.uniform(0.75, 1.25))


async def _lock_sync_source(
    db: AsyncSession, tenant_scope: TenantScope, source_id: UUID
) -> CalendarSource | None:
    source = await db.scalar(
        select(CalendarSource)
        .where(
            CalendarSource.id == source_id,
            CalendarSource.workspace_id == tenant_scope.workspace_id,
            CalendarSource.owner_user_id == tenant_scope.user_id,
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if source is None:
        return None
    if source.disconnected_at is not None or source.connection_state == "disconnected":
        source.sync_state = "failed_closed"
        return None
    if source.credential_state != "sealed":
        source.sync_state = "failed_closed"
        return None
    return source


async def _replace_calendar_catalog(
    db: AsyncSession,
    source: CalendarSource,
    entries: list[CalendarCatalogEntry],
) -> None:
    existing = {
        calendar.provider_calendar_id: calendar
        for calendar in await db.scalars(
            select(ExternalCalendar).where(ExternalCalendar.calendar_source_id == source.id)
        )
    }
    seen: set[str] = set()
    for entry in entries:
        seen.add(entry.provider_calendar_id)
        calendar = existing.get(entry.provider_calendar_id)
        if calendar is None:
            calendar = ExternalCalendar(
                calendar_source_id=source.id,
                workspace_id=source.workspace_id,
                provider_calendar_id=entry.provider_calendar_id,
                display_label=entry.display_label,
                visibility=entry.visibility,
            )
            db.add(calendar)
        else:
            calendar.display_label = entry.display_label
            calendar.visibility = entry.visibility
    for provider_id, calendar in existing.items():
        if provider_id not in seen:
            calendar.selected = False
            calendar.visibility = "removed"
    await db.flush()
    source.selected_calendar_count = sum(
        1
        for calendar in await db.scalars(
            select(ExternalCalendar).where(ExternalCalendar.calendar_source_id == source.id)
        )
        if calendar.selected
        and calendar.visibility in {"available", "selected", "shared", "delegated"}
    )


def future_sync_horizon(now: datetime | None = None) -> tuple[datetime, datetime]:
    sync_started_at = now or datetime.now(UTC)
    return sync_started_at - timedelta(days=7), sync_started_at + timedelta(days=365)


def record_source_sync_failure(
    source: CalendarSource, *, reason: str, now: datetime | None = None
) -> dict[str, str]:
    failure = safe_credential_failure(reason)
    finished_at = now or datetime.now(UTC)
    source.last_sync_finished_at = finished_at
    source.last_safe_error_code = failure["safe_error_code"]
    source.sync_state = "stale" if source.last_successful_sync_at else "failed"
    if failure["credential_state"] != "sealed":
        source.credential_state = failure["credential_state"]
    return failure


async def upsert_event_snapshot(
    db: AsyncSession,
    tenant_scope: TenantScope,
    source: CalendarSource,
    calendar: ExternalCalendar,
    event: NormalizedCalendarEvent,
    credential_encryption_key: bytes | None = None,
) -> CalendarEventSnapshot:
    existing = await db.scalar(
        select(CalendarEventSnapshot).where(
            CalendarEventSnapshot.workspace_id == tenant_scope.workspace_id,
            CalendarEventSnapshot.calendar_source_id == source.id,
            CalendarEventSnapshot.external_calendar_id == calendar.id,
            CalendarEventSnapshot.provider_event_id == event.provider_event_id,
            CalendarEventSnapshot.ical_uid == event.ical_uid,
            CalendarEventSnapshot.recurrence_instance_id == event.recurrence_instance_id,
            CalendarEventSnapshot.original_start == event.original_start,
        )
    )
    snapshot = existing or CalendarEventSnapshot(
        workspace_id=tenant_scope.workspace_id,
        calendar_source_id=source.id,
        external_calendar_id=calendar.id,
    )
    if existing is None:
        db.add(snapshot)

    snapshot.provider_event_id = event.provider_event_id
    snapshot.ical_uid = event.ical_uid
    snapshot.recurring_series_id = event.recurring_series_id
    snapshot.recurrence_instance_id = event.recurrence_instance_id
    snapshot.original_start = event.original_start
    snapshot.source_version = event.source_version
    snapshot.source_status = event.source_status
    snapshot.starts_at = event.starts_at
    snapshot.ends_at = event.ends_at
    snapshot.duration_seconds = event.duration_seconds
    snapshot.timezone = event.timezone
    snapshot.all_day = event.all_day
    snapshot.floating_time = event.floating_time
    snapshot.transparency = event.transparency
    snapshot.recurrence_rule_json = event.recurrence_rule
    snapshot.recurrence_exceptions_json = event.recurrence_exceptions
    snapshot.title = event.title
    snapshot.description = event.description
    snapshot.location = event.location
    snapshot.privacy_class = event.privacy_class
    bounded_conference_links = _bounded_conference_links(event.conference_links)
    snapshot.conference_summary_json = {
        "meeting_link_present": event.meeting_link_present,
        "provider_families": sorted(
            {link.get("provider_family", "generic") for link in bounded_conference_links}
        ),
        "url_hashes": [link["url_hash"] for link in bounded_conference_links],
    }
    sealed_open_url = _sealed_open_meeting_url(bounded_conference_links, credential_encryption_key)
    snapshot.provider_extras_json = event.provider_extras | {
        "recipient_candidate_count": sum(
            1
            for participant in event.participants
            if participant.get("recipient_candidate_class")
            not in {"resource", "room", "group", "unavailable"}
        ),
        "roster_state": "available" if event.participants else "not_available",
        "participant_count": event.participant_count,
        "provider_family": event.provider_family,
        "title_state": event.title_state,
        **({"sealed_open_meeting_url": sealed_open_url} if sealed_open_url else {}),
    }
    snapshot.safe_to_show_in_list = event.title_state == "available"
    snapshot.safe_to_use_as_title = event.title_state == "available"
    snapshot.attachments_metadata_json = event.attachments_metadata
    snapshot.sensitivity_reasons_json = [
        field
        for field, state in event.limitation_states.items()
        if state in {"private_redacted", "free_busy_only"}
    ]
    snapshot.source_created_at = event.source_created_at
    snapshot.source_updated_at = event.source_updated_at
    await db.flush()

    await db.execute(
        delete(CalendarParticipant).where(
            CalendarParticipant.calendar_event_snapshot_id == snapshot.id
        )
    )
    await db.execute(
        delete(ConferenceLinkCandidate).where(
            ConferenceLinkCandidate.calendar_event_snapshot_id == snapshot.id
        )
    )
    for participant in event.participants:
        db.add(
            CalendarParticipant(
                calendar_event_snapshot_id=snapshot.id,
                workspace_id=tenant_scope.workspace_id,
                participant_kind=participant["participant_kind"],
                response_status=participant["response_status"],
                email=participant.get("email"),
                email_hash=participant.get("email_hash"),
                display_name=participant.get("display_name"),
                workspace_relation=participant.get("workspace_relation", "unknown"),
                recipient_candidate_class=participant.get("recipient_candidate_class", "unknown"),
            )
        )
    for link in bounded_conference_links:
        db.add(
            ConferenceLinkCandidate(
                calendar_event_snapshot_id=snapshot.id,
                workspace_id=tenant_scope.workspace_id,
                source_field=link.get("source_field", "unknown"),
                provider_family=link.get("provider_family", "generic"),
                url_hash=link["url_hash"],
                redacted_url_preview=link.get("redacted_url_preview"),
                contains_passcode=bool(link.get("contains_passcode", False)),
                sensitivity_class=link.get("sensitivity_class", "meeting_link"),
            )
        )
    return snapshot


def _bounded_conference_links(links: list[dict]) -> list[dict]:
    """Keep deterministic, hashed meeting identity evidence within the matcher cap."""

    deduped: dict[str, dict] = {}
    for link in links:
        url_hash = link.get("url_hash")
        if not isinstance(url_hash, str) or not url_hash or len(url_hash) > 80 or "://" in url_hash:
            continue
        deduped.setdefault(url_hash, link)
    return [
        deduped[url_hash] for url_hash in sorted(deduped)[:MAX_CONFERENCE_LINK_HASHES_PER_EVENT]
    ]


def _sealed_open_meeting_url(links: list[dict], key: bytes | None) -> str | None:
    if key is None:
        return None
    for link in links:
        open_url = safe_open_meeting_url(link.get("open_url"))
        if open_url:
            return seal_credential(open_url, key).decode("ascii")
    return None


async def apply_calendar_sync_result(
    db: AsyncSession,
    *,
    tenant_scope: TenantScope,
    source: CalendarSource,
    calendar: ExternalCalendar,
    events: list[NormalizedCalendarEvent],
    sync_token: str | None,
    synced_at: datetime | None = None,
    full_sync: bool = True,
    credential_encryption_key: bytes | None = None,
) -> list[CalendarEventSnapshot]:
    finished_at = synced_at or datetime.now(UTC)
    synced_snapshots: list[CalendarEventSnapshot] = []
    seen_snapshot_ids: list[UUID] = []
    for event in events:
        snapshot = await upsert_event_snapshot(
            db,
            tenant_scope,
            source,
            calendar,
            event,
            credential_encryption_key=credential_encryption_key,
        )
        seen_snapshot_ids.append(snapshot.id)
        if event.source_status == "cancelled":
            snapshot.source_deleted_at = finished_at
            continue
        snapshot.source_deleted_at = None
        synced_snapshots.append(snapshot)

    calendar.sync_token = sync_token
    calendar.last_seen_at = finished_at
    source.last_sync_finished_at = finished_at
    source.last_successful_sync_at = finished_at
    source.sync_state = "synced"
    source.last_safe_error_code = None

    seen_ids = seen_snapshot_ids
    stale_conditions = [
        CalendarEventSnapshot.workspace_id == tenant_scope.workspace_id,
        CalendarEventSnapshot.calendar_source_id == source.id,
        CalendarEventSnapshot.external_calendar_id == calendar.id,
        CalendarEventSnapshot.starts_at >= (source.sync_horizon_start or finished_at),
        CalendarEventSnapshot.source_deleted_at.is_(None),
    ]
    if seen_ids:
        stale_conditions.append(CalendarEventSnapshot.id.not_in(seen_ids))
    if full_sync:
        await db.execute(
            update(CalendarEventSnapshot)
            .where(*stale_conditions)
            .values(source_deleted_at=finished_at)
            .execution_options(synchronize_session="fetch")
        )
    return synced_snapshots
