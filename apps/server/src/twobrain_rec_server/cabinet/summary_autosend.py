"""Explicit calendar-bound automation. No network calls or implicit commits."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from types import SimpleNamespace
from uuid import UUID

from sqlalchemy import and_, delete, exists, func, or_, select
from sqlalchemy.exc import IntegrityError

from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.cabinet.access import (
    ACTIVE_CALENDAR_CONTEXT_STATES,
    decide_meeting_access,
    hash_invitation_address,
    lock_shareable_meeting,
    normalize_invitation_address,
)
from twobrain_rec_server.calendar.owner_content import (
    owner_content_key_from_settings,
    owner_event_content,
)
from twobrain_rec_server.calendar.series import series_key
from twobrain_rec_server.db.models import (
    CalendarEventSnapshot,
    CalendarSource,
    ExternalCalendar,
    ExternalIdentity,
    MediaRevision,
    Meeting,
    MeetingOutcomeSet,
    MeetingSummarySlot,
    ProcessingResult,
    RecordingCalendarContextLink,
    UserIdentity,
    Workspace,
    WorkspaceMembership,
)
from twobrain_rec_server.db.models.summary_autosend import (
    SummaryAutoSendException,
    SummaryAutoSendRule,
    SummarySharingPreference,
)
from twobrain_rec_server.processing.results import (
    effective_processing_result_query,
    result_is_complete,
)

AUTO_DELAY = timedelta(minutes=5)
AUTO_LIFETIME = timedelta(hours=24)
CALENDAR_FRESHNESS = timedelta(minutes=15)
AUTO_DAILY_BATCH_LIMIT = 20


@dataclass(frozen=True, slots=True)
class AutoSendGuard:
    allowed: bool
    reason_code: str | None = None
    requires_review: bool = False


@dataclass
class CalendarAudience:
    guard: AutoSendGuard
    event: CalendarEventSnapshot | None = None
    source: CalendarSource | None = None
    roster: list | None = None
    fingerprint: str | None = None
    occurrence_key: str | None = None
    canonical_series_key: str | None = None


def _utc(value: datetime | None) -> datetime | None:
    return value.replace(tzinfo=UTC) if value is not None and value.tzinfo is None else value


def _review(reason: str) -> AutoSendGuard:
    return AutoSendGuard(False, reason, True)


def _problem(code: str, *, status: int = 422) -> ProblemDetail:
    return ProblemDetail(status=status, code=code, title="Проверьте настройку отправки итогов")


def evaluate_google_roster(event, source, content: dict, *, now=None) -> AutoSendGuard:
    """Positive provider proof is required; RSVP never proves attendance."""
    now = now or datetime.now(UTC)
    if source.provider_family != "google_calendar":
        return _review("calendar_unsupported")
    if event.source_deleted_at is not None or event.source_status != "confirmed":
        return _review("calendar_unavailable")
    if event.privacy_class != "public":
        return _review("calendar_private")
    synced = _utc(source.last_successful_sync_at)
    if (
        source.sync_state != "synced"
        or synced is None
        or not timedelta(0) <= now - synced <= CALENDAR_FRESHNESS
    ):
        return _review("calendar_stale")
    extras = content.get("provider_extras") or {}
    if extras.get("google_attendees_complete") is not True:
        return _review("calendar_incomplete")
    if extras.get("google_organizer_self") is not True:
        return _review("distributor_unverified")
    participants = content.get("participants") or []
    if not participants:
        return _review("calendar_incomplete")
    for person in participants:
        if person.get("participant_kind") in {"resource", "room", "group"}:
            return _review("calendar_resource")
        if person.get("response_status", "unknown").lower() == "declined":
            return _review("calendar_declined")
        if (person.get("provider_details") or {}).get("additionalGuests", 0) != 0:
            return _review("calendar_incomplete")
        if not person.get("email"):
            return _review("calendar_identity_unknown")
        if (
            person.get("participant_kind") != "organizer"
            and person.get("response_status", "unknown").lower() != "accepted"
        ):
            return _review("calendar_unconfirmed")
    return AutoSendGuard(True)


async def get_preferences(db, *, workspace_id: UUID, owner_user_id: UUID, for_update=False):
    row = await db.scalar(
        select(SummarySharingPreference)
        .where(
            SummarySharingPreference.workspace_id == workspace_id,
            SummarySharingPreference.owner_user_id == owner_user_id,
        )
        .with_for_update()
        .execution_options(populate_existing=True)
        if for_update
        else select(SummarySharingPreference).where(
            SummarySharingPreference.workspace_id == workspace_id,
            SummarySharingPreference.owner_user_id == owner_user_id,
        )
    )
    if row is None and for_update:
        try:
            async with db.begin_nested():
                row = SummarySharingPreference(
                    workspace_id=workspace_id,
                    owner_user_id=owner_user_id,
                    ask_enabled=True,
                    paused=False,
                    version=0,
                    auto_epoch=0,
                    budget_batches=0,
                )
                db.add(row)
                await db.flush()
        except IntegrityError:
            row = await db.scalar(
                select(SummarySharingPreference)
                .where(
                    SummarySharingPreference.workspace_id == workspace_id,
                    SummarySharingPreference.owner_user_id == owner_user_id,
                )
                .with_for_update()
                .execution_options(populate_existing=True)
            )
    return row or SimpleNamespace(
        ask_enabled=True, paused=False, version=0, auto_epoch=0, last_resumed_at=None
    )


async def update_preferences(
    db,
    *,
    workspace_id: UUID,
    owner_user_id: UUID,
    expected_version: int,
    ask_enabled=None,
    paused=None,
    now=None,
):
    # This handler takes only the preference lock, never a meeting lock after it.
    row = await get_preferences(
        db, workspace_id=workspace_id, owner_user_id=owner_user_id, for_update=True
    )
    if row.version != expected_version:
        raise _problem("settings_conflict", status=409)
    changed = False
    if ask_enabled is not None and row.ask_enabled != ask_enabled:
        row.ask_enabled = ask_enabled
        changed = True
    if paused is not None and row.paused != paused:
        row.paused = paused
        row.auto_epoch += 1
        if not paused:
            row.last_resumed_at = now or datetime.now(UTC)
        changed = True
    if changed:
        row.version += 1
    await db.flush()
    return row


async def _owner_meeting(db, workspace_id, meeting_id, owner_user_id):
    meeting = await lock_shareable_meeting(db, workspace_id=workspace_id, meeting_id=meeting_id)
    access = await decide_meeting_access(
        db, meeting, workspace_id=workspace_id, viewer_user_id=owner_user_id
    )
    if meeting.created_by_user_id != owner_user_id or not access.can_share:
        raise _problem("meeting_not_found", status=404)
    return meeting


async def _audience(db, *, settings, meeting, now=None) -> CalendarAudience:
    now = now or datetime.now(UTC)
    row = (
        await db.execute(
            select(CalendarEventSnapshot, CalendarSource, ExternalCalendar)
            .join(
                RecordingCalendarContextLink,
                RecordingCalendarContextLink.calendar_event_snapshot_id == CalendarEventSnapshot.id,
            )
            .join(CalendarSource, CalendarSource.id == CalendarEventSnapshot.calendar_source_id)
            .join(
                ExternalCalendar, ExternalCalendar.id == CalendarEventSnapshot.external_calendar_id
            )
            .where(
                RecordingCalendarContextLink.workspace_id == meeting.workspace_id,
                RecordingCalendarContextLink.meeting_id == meeting.id,
                RecordingCalendarContextLink.context_state.in_(ACTIVE_CALENDAR_CONTEXT_STATES),
                CalendarEventSnapshot.workspace_id == meeting.workspace_id,
                CalendarSource.workspace_id == meeting.workspace_id,
                CalendarSource.owner_user_id == meeting.created_by_user_id,
                ExternalCalendar.workspace_id == meeting.workspace_id,
                ExternalCalendar.calendar_source_id == CalendarSource.id,
            )
        )
    ).first()
    if row is None:
        return CalendarAudience(_review("calendar_unavailable"), roster=[])
    event, source, _calendar = row
    if (
        source.connection_state != "active"
        or source.disconnected_at is not None
        or not _calendar.selected
        or _calendar.visibility != "available"
    ):
        return CalendarAudience(_review("calendar_unavailable"), event, source, roster=[])
    content = owner_event_content(event, owner_content_key_from_settings(settings))
    guard = evaluate_google_roster(event, source, content, now=now)
    participants = content.get("participants") or []
    addresses: dict[str, dict] = {}
    for participant in participants:
        try:
            address = normalize_invitation_address(participant.get("email") or "")
        except ProblemDetail:
            guard = _review("calendar_identity_unknown")
            continue
        previous = addresses.get(address)
        # Organizer duplication in attendees must not invent a second recipient.
        if previous is None or participant.get("participant_kind") == "organizer":
            addresses[address] = participant
    verified = []
    if addresses:
        verified = (
            await db.execute(
                select(UserIdentity, ExternalIdentity.email)
                .join(ExternalIdentity, ExternalIdentity.user_id == UserIdentity.id)
                .join(WorkspaceMembership, WorkspaceMembership.user_id == UserIdentity.id)
                .join(Workspace, Workspace.id == WorkspaceMembership.workspace_id)
                .where(
                    WorkspaceMembership.workspace_id == meeting.workspace_id,
                    WorkspaceMembership.status == "active",
                    UserIdentity.status == "active",
                    UserIdentity.organization_id == Workspace.organization_id,
                    ExternalIdentity.is_active.is_(True),
                    ExternalIdentity.is_verified.is_(True),
                    func.lower(func.trim(ExternalIdentity.email)).in_(list(addresses)),
                )
            )
        ).all()
    matches: dict[str, set] = {}
    for user, email in verified:
        matches.setdefault(normalize_invitation_address(email), set()).add(user.id)
    roster = []
    user_addresses: dict[UUID, set] = {}
    for email, participant in sorted(addresses.items()):
        users = matches.get(email, set())
        user_id = next(iter(users)) if len(users) == 1 else None
        if user_id:
            user_addresses.setdefault(user_id, set()).add(email)
        eligible = user_id is not None and user_id != meeting.created_by_user_id
        reason = (
            None
            if eligible
            else "sender"
            if user_id == meeting.created_by_user_id
            else "recipient_unverified"
        )
        roster.append(
            {
                "user_id": str(user_id) if user_id else None,
                "email": email,
                "kind": participant.get("participant_kind", "attendee"),
                "rsvp": participant.get("response_status", "unknown").lower(),
                "eligible": eligible,
                "reason_code": reason,
                "selected": False,
            }
        )
        if user_id is None:
            guard = _review("recipient_unverified")
    if any(len(emails) > 1 for emails in user_addresses.values()):
        guard = _review("recipient_ambiguous")
    organizers = [person for person in roster if person["kind"] == "organizer"]
    if len(organizers) != 1 or organizers[0]["user_id"] != str(meeting.created_by_user_id):
        guard = _review("distributor_unverified")
    fingerprint = sha256(
        json.dumps(
            [
                [
                    person["user_id"],
                    hash_invitation_address(person["email"]),
                    person["kind"],
                    person["rsvp"],
                ]
                for person in roster
            ],
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    occurrence = canonical_series = None
    if event.ical_uid and len(organizers) == 1:
        canonical_series = sha256(
            json.dumps(
                ["google-v1", event.ical_uid, hash_invitation_address(organizers[0]["email"])],
                separators=(",", ":"),
            ).encode()
        ).hexdigest()
        original = _utc(event.original_start)
        if event.recurring_series_id and original is None:
            guard = _review("calendar_instance_unknown")
        else:
            occurrence = sha256(
                f"{canonical_series}:{original.isoformat() if original else 'single'}".encode()
            ).hexdigest()
    else:
        guard = _review("calendar_instance_unknown")
    return CalendarAudience(guard, event, source, roster, fingerprint, occurrence, canonical_series)


def _targets(meeting, audience):
    return {
        "meeting": str(meeting.id),
        "series": series_key(audience.event, meeting.created_by_user_id)
        if audience.event is not None
        else None,
    }


async def _rules(db, meeting, audience):
    targets = _targets(meeting, audience)
    return list(
        (
            await db.scalars(
                select(SummaryAutoSendRule).where(
                    SummaryAutoSendRule.workspace_id == meeting.workspace_id,
                    SummaryAutoSendRule.owner_user_id == meeting.created_by_user_id,
                    or_(
                        *[
                            and_(
                                SummaryAutoSendRule.scope == scope,
                                SummaryAutoSendRule.target_key == target,
                            )
                            for scope, target in targets.items()
                            if target
                        ]
                    ),
                )
            )
        ).all()
    )


async def _exception(db, meeting):
    return await db.scalar(
        select(SummaryAutoSendException).where(
            SummaryAutoSendException.workspace_id == meeting.workspace_id,
            SummaryAutoSendException.owner_user_id == meeting.created_by_user_id,
            SummaryAutoSendException.meeting_id == meeting.id,
        )
    )


async def _retain_review(db, meeting, rule, reason):
    exception = await _exception(db, meeting)
    if exception is None:
        db.add(
            SummaryAutoSendException(
                workspace_id=meeting.workspace_id,
                owner_user_id=meeting.created_by_user_id,
                meeting_id=meeting.id,
                rule_id=rule.id,
                state="requires_review",
                reason_code=reason,
            )
        )
    elif exception.state != "cancelled":
        exception.state, exception.reason_code = "requires_review", reason
    await db.flush()


async def _ready_outcome(db, meeting, template_key):
    row = (
        await db.execute(
            select(MeetingOutcomeSet, ProcessingResult)
            .join(
                MeetingSummarySlot,
                MeetingSummarySlot.current_outcome_set_id == MeetingOutcomeSet.id,
            )
            .join(ProcessingResult, ProcessingResult.id == MeetingOutcomeSet.processing_result_id)
            .where(
                MeetingSummarySlot.workspace_id == meeting.workspace_id,
                MeetingSummarySlot.meeting_id == meeting.id,
                MeetingSummarySlot.template_key == template_key,
                MeetingSummarySlot.current_binding_class == "verified_complete",
                MeetingOutcomeSet.workspace_id == meeting.workspace_id,
                MeetingOutcomeSet.meeting_id == meeting.id,
                MeetingOutcomeSet.lifecycle_state == "active",
                MeetingOutcomeSet.status == "available",
                MeetingOutcomeSet.revision_state == "accepted",
                MeetingOutcomeSet.accepted_at.is_not(None),
                ProcessingResult.workspace_id == meeting.workspace_id,
                ProcessingResult.meeting_id == meeting.id,
            )
        )
    ).first()
    if row is None or not result_is_complete(row[1]) or meeting.ended_at is None:
        return None
    outcome, result = row
    revision = await db.scalar(
        select(MediaRevision)
        .where(
            MediaRevision.workspace_id == meeting.workspace_id,
            MediaRevision.meeting_id == meeting.id,
            MediaRevision.status == "accepted",
            MediaRevision.immutable.is_(True),
        )
        .order_by(MediaRevision.revision_number.desc(), MediaRevision.updated_at.desc())
        .limit(1)
    )
    if (
        revision is None
        or revision.id != result.media_revision_id
        or outcome.media_revision_id != revision.id
    ):
        return None
    effective = await db.scalar(
        effective_processing_result_query(
            workspace_id=meeting.workspace_id, meeting_id=meeting.id, media_revision_id=revision.id
        )
    )
    if effective is None or effective.id != result.id:
        return None
    return outcome


def _approved(audience, user_ids):
    wanted = {str(value) for value in user_ids}
    available = {
        person["user_id"]: person for person in audience.roster or [] if person["eligible"]
    }
    if not wanted or len(wanted) > 50 or not wanted <= available.keys():
        raise _problem("auto_recipient_invalid")
    return sorted(
        [
            {"user_id": uid, "email_hash": hash_invitation_address(available[uid]["email"])}
            for uid in wanted
        ],
        key=lambda person: person["user_id"],
    )


async def save_rule(
    db,
    *,
    settings,
    workspace_id,
    meeting_id,
    owner_user_id,
    scope,
    enabled,
    template_key,
    recipient_user_ids,
    expected_version,
    now=None,
):
    now = now or datetime.now(UTC)
    meeting = await _owner_meeting(db, workspace_id, meeting_id, owner_user_id)
    await get_preferences(
        db, workspace_id=workspace_id, owner_user_id=owner_user_id, for_update=True
    )
    audience = await _audience(db, settings=settings, meeting=meeting, now=now)
    target = _targets(meeting, audience).get(scope)
    if not target:
        raise _problem("auto_scope_unavailable")
    rule = await db.scalar(
        select(SummaryAutoSendRule)
        .where(
            SummaryAutoSendRule.workspace_id == workspace_id,
            SummaryAutoSendRule.owner_user_id == owner_user_id,
            SummaryAutoSendRule.scope == scope,
            SummaryAutoSendRule.target_key == target,
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if (rule.version if rule else 0) != expected_version:
        raise _problem("auto_rule_conflict", status=409)
    if not enabled and rule is None:
        # A meeting-level off is an explicit series exception, even without a rule.
        if scope == "meeting":
            exception = await _exception(db, meeting)
            if exception is None:
                db.add(
                    SummaryAutoSendException(
                        workspace_id=workspace_id,
                        owner_user_id=owner_user_id,
                        meeting_id=meeting_id,
                        state="cancelled",
                        reason_code="meeting_auto_disabled",
                    )
                )
            else:
                exception.state, exception.reason_code = "cancelled", "meeting_auto_disabled"
            await db.flush()
        return await auto_state(
            db,
            settings=settings,
            workspace_id=workspace_id,
            meeting_id=meeting_id,
            owner_user_id=owner_user_id,
            now=now,
        )
    approved = rule.approved_recipients_json if rule else []
    if enabled:
        if not settings.share_external_invitations_enabled:
            raise _problem("summary_email_unavailable", status=503)
        if not audience.guard.allowed:
            raise _problem(audience.guard.reason_code or "auto_ineligible")
        approved = _approved(audience, recipient_user_ids)
        # An explicit one-meeting permission is collected while its result is preparing.
        unchanged = (
            rule is not None
            and rule.enabled
            and rule.template_key == template_key
            and approved == rule.approved_recipients_json
            and rule.approved_roster_fingerprint == audience.fingerprint
        )
        if (
            scope == "meeting"
            and not unchanged
            and await _ready_outcome(db, meeting, template_key) is not None
        ):
            raise _problem("auto_already_ready")
        canonical = audience.occurrence_key if scope == "meeting" else audience.canonical_series_key
        conflicts = await db.scalar(
            select(SummaryAutoSendRule.id)
            .where(
                SummaryAutoSendRule.workspace_id == workspace_id,
                SummaryAutoSendRule.canonical_target_key == canonical,
                SummaryAutoSendRule.enabled.is_(True),
                SummaryAutoSendRule.owner_user_id != owner_user_id,
            )
            .limit(1)
        )
        if conflicts:
            raise _problem("distributor_conflict", status=409)
    same = (
        rule is not None
        and rule.enabled == enabled
        and (
            not enabled
            or (
                rule.template_key == template_key
                and approved == rule.approved_recipients_json
                and rule.approved_roster_fingerprint == audience.fingerprint
            )
        )
    )
    if not same:
        if rule is None:
            rule = SummaryAutoSendRule(
                workspace_id=workspace_id,
                owner_user_id=owner_user_id,
                distributor_user_id=owner_user_id,
                scope=scope,
                target_key=target,
                canonical_target_key=audience.occurrence_key
                if scope == "meeting"
                else audience.canonical_series_key,
                meeting_id=meeting_id if scope == "meeting" else None,
                calendar_source_id=audience.event.calendar_source_id,
                external_calendar_id=audience.event.external_calendar_id,
                calendar_series_id=audience.event.recurring_series_id
                if scope == "series"
                else None,
                template_key=template_key,
                approved_roster_fingerprint=audience.fingerprint,
                approved_recipients_json=approved,
                enabled=enabled,
                version=1,
            )
            db.add(rule)
        else:
            rule.version += 1
            if enabled:
                rule.template_key, rule.approved_recipients_json = template_key, approved
                rule.approved_roster_fingerprint = audience.fingerprint
        rule.enabled = enabled
        rule.enabled_at = now if enabled else rule.enabled_at
        rule.disabled_at = None if enabled else now
    if enabled:
        # Clearing sticky review requires this explicit owner decision.
        await db.execute(
            delete(SummaryAutoSendException).where(
                SummaryAutoSendException.workspace_id == workspace_id,
                SummaryAutoSendException.owner_user_id == owner_user_id,
                SummaryAutoSendException.meeting_id == meeting_id,
            )
        )
    elif scope == "meeting":
        exception = await _exception(db, meeting)
        if exception is None:
            db.add(
                SummaryAutoSendException(
                    workspace_id=workspace_id,
                    owner_user_id=owner_user_id,
                    meeting_id=meeting_id,
                    rule_id=rule.id,
                    state="cancelled",
                    reason_code="meeting_auto_disabled",
                )
            )
        else:
            exception.state, exception.reason_code = "cancelled", "meeting_auto_disabled"
    await db.flush()
    return await auto_state(
        db,
        settings=settings,
        workspace_id=workspace_id,
        meeting_id=meeting_id,
        owner_user_id=owner_user_id,
        now=now,
    )


async def _validate(db, *, settings, meeting, rule, preference, authority, now):
    if rule is None or not rule.enabled:
        return AutoSendGuard(False, "auto_rule_disabled")
    if rule.version != authority.get("rule_version"):
        return AutoSendGuard(False, "auto_rule_changed")
    if preference.paused or preference.auto_epoch != authority.get("preference_auto_epoch"):
        return AutoSendGuard(False, "auto_paused")
    exception = await _exception(db, meeting)
    if exception:
        return AutoSendGuard(False, exception.reason_code, exception.state == "requires_review")
    if (
        meeting.created_by_user_id != rule.owner_user_id
        or rule.distributor_user_id != rule.owner_user_id
    ):
        return _review("distributor_unverified")
    access = await decide_meeting_access(
        db, meeting, workspace_id=meeting.workspace_id, viewer_user_id=rule.owner_user_id
    )
    if not access.can_share:
        return _review("meeting_unavailable")
    audience = await _audience(db, settings=settings, meeting=meeting, now=now)
    if not audience.guard.allowed:
        return audience.guard
    if (
        rule.calendar_source_id != audience.event.calendar_source_id
        or rule.external_calendar_id != audience.event.external_calendar_id
    ):
        return _review("calendar_changed")
    if _targets(meeting, audience).get(rule.scope) != rule.target_key:
        return _review("calendar_changed")
    if rule.scope == "series" and _utc(audience.event.starts_at) <= _utc(rule.enabled_at):
        return AutoSendGuard(False, "auto_historical")
    try:
        authority_ready_at = _utc(datetime.fromisoformat(authority["ready_at"]))
    except (ValueError, TypeError, KeyError):
        return _review("auto_authority_invalid")
    if preference.last_resumed_at is not None and (
        (
            _utc(rule.enabled_at) <= _utc(preference.last_resumed_at)
            and _utc(audience.event.starts_at) <= _utc(preference.last_resumed_at)
        )
        or (rule.scope == "meeting" and authority_ready_at <= _utc(preference.last_resumed_at))
    ):
        return AutoSendGuard(False, "auto_historical")
    if (
        rule.approved_roster_fingerprint != audience.fingerprint
        or authority.get("roster_fingerprint") != audience.fingerprint
    ):
        return _review("roster_changed")
    if audience.occurrence_key != authority.get("occurrence_key"):
        return _review("calendar_changed")
    try:
        approved = _approved(
            audience, [person["user_id"] for person in rule.approved_recipients_json]
        )
    except (ProblemDetail, KeyError, TypeError):
        return _review("recipient_changed")
    if approved != rule.approved_recipients_json:
        return _review("recipient_changed")
    conflict = await db.scalar(
        select(SummaryAutoSendRule.id)
        .where(
            SummaryAutoSendRule.workspace_id == meeting.workspace_id,
            SummaryAutoSendRule.owner_user_id != rule.owner_user_id,
            SummaryAutoSendRule.enabled.is_(True),
            SummaryAutoSendRule.canonical_target_key.in_(
                [audience.occurrence_key, audience.canonical_series_key]
            ),
        )
        .limit(1)
    )
    return _review("distributor_conflict") if conflict else AutoSendGuard(True)


async def validate_auto_authority(
    db, *, meeting, authority, recipients, template_key, now=None, settings=None
):
    from twobrain_rec_server.config import get_settings

    now = now or datetime.now(UTC)
    settings = settings or get_settings()
    preference = await get_preferences(
        db,
        workspace_id=meeting.workspace_id,
        owner_user_id=meeting.created_by_user_id,
        for_update=True,
    )
    try:
        rule_id = UUID(str(authority.get("rule_id")))
    except (ValueError, TypeError):
        return _review("auto_authority_invalid")
    rule = await db.scalar(
        select(SummaryAutoSendRule)
        .where(
            SummaryAutoSendRule.id == rule_id,
            SummaryAutoSendRule.workspace_id == meeting.workspace_id,
            SummaryAutoSendRule.owner_user_id == meeting.created_by_user_id,
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    guard = await _validate(
        db,
        settings=settings,
        meeting=meeting,
        rule=rule,
        preference=preference,
        authority=authority,
        now=now,
    )
    if not guard.allowed:
        return guard
    if rule.template_key != template_key:
        return _review("summary_changed")
    audience = await _audience(db, settings=settings, meeting=meeting, now=now)
    selected = {person["user_id"] for person in rule.approved_recipients_json}
    expected = {person["email"] for person in audience.roster if person["user_id"] in selected}
    if {normalize_invitation_address(email) for email in recipients} != expected:
        return _review("recipient_changed")
    outcome = await _ready_outcome(db, meeting, template_key)
    if outcome is None:
        return _review("summary_unavailable")
    try:
        ready_at = _utc(datetime.fromisoformat(authority["ready_at"]))
    except (ValueError, TypeError, KeyError):
        return _review("auto_authority_invalid")
    if ready_at != _utc(outcome.accepted_at) or ready_at < _utc(rule.enabled_at):
        return AutoSendGuard(False, "auto_historical")
    if now > ready_at + AUTO_LIFETIME:
        return AutoSendGuard(False, "auto_expired")
    return AutoSendGuard(True)


async def guard_auto_batch(db, *, batch, recipient=None, now=None, phase="reserve", settings=None):
    from twobrain_rec_server.config import get_settings
    from twobrain_rec_server.db.models.summary_sharing import (
        PublishedMeetingSummary,
        SummaryEmailSuppression,
    )

    if not batch.automatic:
        return AutoSendGuard(True)
    now = now or datetime.now(UTC)
    settings = settings or get_settings()
    meeting = await db.get(Meeting, batch.meeting_id)
    if meeting is None or meeting.workspace_id != batch.workspace_id:
        return AutoSendGuard(False, "meeting_unavailable")
    authority = dict(batch.auto_authority_json or {}) | {
        "rule_id": str(batch.auto_rule_id),
        "rule_version": batch.auto_rule_version,
    }
    preference = await get_preferences(
        db,
        workspace_id=batch.workspace_id,
        owner_user_id=meeting.created_by_user_id,
        for_update=True,
    )
    rule = await db.scalar(
        select(SummaryAutoSendRule)
        .where(
            SummaryAutoSendRule.id == batch.auto_rule_id,
            SummaryAutoSendRule.workspace_id == batch.workspace_id,
            SummaryAutoSendRule.owner_user_id == meeting.created_by_user_id,
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    guard = await _validate(
        db,
        settings=settings,
        meeting=meeting,
        rule=rule,
        preference=preference,
        authority=authority,
        now=now,
    )
    if not guard.allowed:
        if guard.requires_review and rule:
            await _retain_review(db, meeting, rule, guard.reason_code)
        return guard
    if batch.deadline_at is None or now > _utc(batch.deadline_at):
        return AutoSendGuard(False, "auto_expired")
    if phase == "reserve" and (batch.scheduled_at is None or now < _utc(batch.scheduled_at)):
        return AutoSendGuard(False, "not_due")
    publication = await db.get(PublishedMeetingSummary, batch.published_summary_id)
    outcome = await _ready_outcome(db, meeting, rule.template_key)
    if outcome is None or publication is None or publication.source_outcome_id != outcome.id:
        await _retain_review(db, meeting, rule, "summary_changed")
        return _review("summary_changed")
    if recipient is not None:
        approved = {person["email_hash"] for person in rule.approved_recipients_json}
        if recipient.normalized_address_hash not in approved:
            return _review("recipient_changed")
        suppressed = await db.scalar(
            select(SummaryEmailSuppression.id)
            .where(
                SummaryEmailSuppression.workspace_id == batch.workspace_id,
                SummaryEmailSuppression.sender_user_id == batch.owner_user_id,
                SummaryEmailSuppression.normalized_address_hash
                == recipient.normalized_address_hash,
                SummaryEmailSuppression.opted_out_at.is_not(None),
            )
            .limit(1)
        )
        if suppressed:
            return AutoSendGuard(False, "recipient_suppressed")
    return AutoSendGuard(True)


async def reconcile_meeting_autosend(db, *, settings, workspace_id, meeting_id, now=None):
    from twobrain_rec_server.cabinet.summary_sharing import create_batch
    from twobrain_rec_server.db.models.summary_sharing import SummaryDeliveryBatch

    now = now or datetime.now(UTC)
    meeting = await lock_shareable_meeting(db, workspace_id=workspace_id, meeting_id=meeting_id)
    # Most summary publications have no AUTO rule. Do not materialize defaults
    # or hold a settings lock for those meetings.
    if not await db.scalar(
        select(SummaryAutoSendRule.id)
        .where(
            SummaryAutoSendRule.workspace_id == workspace_id,
            SummaryAutoSendRule.owner_user_id == meeting.created_by_user_id,
            SummaryAutoSendRule.enabled.is_(True),
        )
        .limit(1)
    ):
        return None
    preference = await get_preferences(
        db, workspace_id=workspace_id, owner_user_id=meeting.created_by_user_id, for_update=True
    )
    audience = await _audience(db, settings=settings, meeting=meeting, now=now)
    rules = await _rules(db, meeting, audience)
    rule = next((item for item in rules if item.scope == "meeting"), None)
    rule = rule or next((item for item in rules if item.scope == "series"), None)
    if rule is None or not rule.enabled or preference.paused or await _exception(db, meeting):
        return None
    # Lock the exact rule before capturing its version/consent.
    rule = await db.scalar(
        select(SummaryAutoSendRule)
        .where(SummaryAutoSendRule.id == rule.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if not rule.enabled:
        return None
    outcome = await _ready_outcome(db, meeting, rule.template_key)
    if outcome is None:
        return None
    ready_at = _utc(outcome.accepted_at)
    if ready_at < _utc(rule.enabled_at) or (
        rule.scope == "series"
        and audience.event is not None
        and _utc(audience.event.starts_at) <= _utc(rule.enabled_at)
    ):
        return None
    if preference.last_resumed_at is not None and (
        ready_at <= _utc(preference.last_resumed_at)
        or (
            _utc(rule.enabled_at) <= _utc(preference.last_resumed_at)
            and audience.event is not None
            and _utc(audience.event.starts_at) <= _utc(preference.last_resumed_at)
        )
    ):
        return None
    authority = {
        "rule_id": str(rule.id),
        "rule_version": rule.version,
        "roster_fingerprint": audience.fingerprint,
        "preference_version": preference.version,
        "preference_auto_epoch": preference.auto_epoch,
        "occurrence_key": audience.occurrence_key,
        "ready_at": ready_at.isoformat(),
    }
    guard = await _validate(
        db,
        settings=settings,
        meeting=meeting,
        rule=rule,
        preference=preference,
        authority=authority,
        now=now,
    )
    if not guard.allowed:
        if guard.requires_review:
            await _retain_review(db, meeting, rule, guard.reason_code)
        return None
    if now > ready_at + AUTO_LIFETIME:
        await _retain_review(db, meeting, rule, "auto_expired")
        return None
    existing = await db.scalar(
        select(SummaryDeliveryBatch).where(
            SummaryDeliveryBatch.workspace_id == workspace_id,
            SummaryDeliveryBatch.auto_occurrence_key == audience.occurrence_key,
        )
    )
    if existing:
        return existing
    if (
        preference.budget_window_started_at is None
        or now - _utc(preference.budget_window_started_at) >= AUTO_LIFETIME
    ):
        preference.budget_window_started_at, preference.budget_batches = now, 0
    if preference.budget_batches >= AUTO_DAILY_BATCH_LIMIT:
        await _retain_review(db, meeting, rule, "automatic_budget_exceeded")
        return None
    selected = {person["user_id"] for person in rule.approved_recipients_json}
    recipients = [person["email"] for person in audience.roster if person["user_id"] in selected]
    batch = await create_batch(
        db,
        settings=settings,
        workspace_id=workspace_id,
        meeting_id=meeting_id,
        actor_user_id=meeting.created_by_user_id,
        template_key=rule.template_key,
        recipients=recipients,
        idempotency_key=f"auto:{audience.occurrence_key}",
        automatic_authority=authority,
        scheduled_at=ready_at + AUTO_DELAY,
        deadline_at=ready_at + AUTO_LIFETIME,
    )
    preference.budget_batches += 1
    await db.flush()
    return batch


async def list_autosend_readiness_candidates(db, *, limit=25):
    from twobrain_rec_server.db.models.summary_sharing import SummaryDeliveryBatch

    # No locks here: the caller commits this metadata scan, then locks one meeting.
    targets = list(
        (
            await db.execute(
                select(Meeting.workspace_id, Meeting.id)
                .join(
                    SummaryAutoSendRule,
                    and_(
                        SummaryAutoSendRule.workspace_id == Meeting.workspace_id,
                        SummaryAutoSendRule.owner_user_id == Meeting.created_by_user_id,
                    ),
                )
                .join(
                    MeetingSummarySlot,
                    and_(
                        MeetingSummarySlot.workspace_id == Meeting.workspace_id,
                        MeetingSummarySlot.meeting_id == Meeting.id,
                        MeetingSummarySlot.template_key == SummaryAutoSendRule.template_key,
                    ),
                )
                .join(
                    MeetingOutcomeSet,
                    MeetingOutcomeSet.id == MeetingSummarySlot.current_outcome_set_id,
                )
                .join(
                    RecordingCalendarContextLink,
                    and_(
                        RecordingCalendarContextLink.workspace_id == Meeting.workspace_id,
                        RecordingCalendarContextLink.meeting_id == Meeting.id,
                    ),
                )
                .join(
                    CalendarEventSnapshot,
                    CalendarEventSnapshot.id
                    == RecordingCalendarContextLink.calendar_event_snapshot_id,
                )
                .outerjoin(
                    SummarySharingPreference,
                    and_(
                        SummarySharingPreference.workspace_id == Meeting.workspace_id,
                        SummarySharingPreference.owner_user_id == Meeting.created_by_user_id,
                    ),
                )
                .where(
                    or_(
                        SummarySharingPreference.paused.is_(None),
                        SummarySharingPreference.paused.is_(False),
                    ),
                    or_(
                        SummarySharingPreference.last_resumed_at.is_(None),
                        and_(
                            MeetingOutcomeSet.accepted_at
                            > SummarySharingPreference.last_resumed_at,
                            or_(
                                and_(
                                    SummaryAutoSendRule.scope == "meeting",
                                    SummaryAutoSendRule.enabled_at
                                    > SummarySharingPreference.last_resumed_at,
                                ),
                                CalendarEventSnapshot.starts_at
                                > SummarySharingPreference.last_resumed_at,
                            ),
                        ),
                    ),
                    SummaryAutoSendRule.enabled.is_(True),
                    Meeting.deleted_at.is_(None),
                    Meeting.deletion_state == "none",
                    Meeting.ended_at.is_not(None),
                    MeetingOutcomeSet.accepted_at >= SummaryAutoSendRule.enabled_at,
                    or_(
                        and_(
                            SummaryAutoSendRule.scope == "meeting",
                            SummaryAutoSendRule.meeting_id == Meeting.id,
                        ),
                        and_(
                            SummaryAutoSendRule.scope == "series",
                            CalendarEventSnapshot.calendar_source_id
                            == SummaryAutoSendRule.calendar_source_id,
                            CalendarEventSnapshot.external_calendar_id
                            == SummaryAutoSendRule.external_calendar_id,
                            CalendarEventSnapshot.recurring_series_id
                            == SummaryAutoSendRule.calendar_series_id,
                            CalendarEventSnapshot.starts_at > SummaryAutoSendRule.enabled_at,
                        ),
                    ),
                    ~exists(
                        select(SummaryDeliveryBatch.id).where(
                            SummaryDeliveryBatch.workspace_id == Meeting.workspace_id,
                            SummaryDeliveryBatch.meeting_id == Meeting.id,
                            SummaryDeliveryBatch.automatic.is_(True),
                        )
                    ),
                    ~exists(
                        select(SummaryAutoSendException.id).where(
                            SummaryAutoSendException.workspace_id == Meeting.workspace_id,
                            SummaryAutoSendException.meeting_id == Meeting.id,
                            SummaryAutoSendException.owner_user_id == Meeting.created_by_user_id,
                        )
                    ),
                )
                .group_by(Meeting.workspace_id, Meeting.id, Meeting.updated_at)
                .order_by(Meeting.updated_at.desc(), Meeting.id)
                .limit(max(0, min(limit, 100)))
            )
        ).all()
    )
    return [(workspace, meeting) for workspace, meeting in targets]


def _rule_json(rule):
    if rule is None:
        return {"id": None, "version": 0, "enabled": False}
    return {
        "id": str(rule.id),
        "version": rule.version,
        "enabled": rule.enabled,
        "template_key": rule.template_key,
        "scope": rule.scope,
        "recipient_user_ids": [person["user_id"] for person in rule.approved_recipients_json],
    }


def _delivery_presentation(batch, counts):
    """Expose recipient outcomes, never the durable aggregate's internal label."""
    if batch.state in {"cancelled", "requires_review", "expired"}:
        return batch.state
    if counts.get("sending"):
        return "sending"
    if counts.get("pending"):
        return "scheduled"
    if counts.get("failed") or counts.get("suppressed"):
        return "partial"
    if counts.get("unknown"):
        return "unknown"
    if counts.get("cancelled") == sum(counts.values()) and counts:
        return "cancelled"
    if counts.get("cancelled"):
        return "partial"
    if counts.get("accepted") and counts["accepted"] == sum(counts.values()):
        return "sent"
    return "requires_review"


async def auto_state(db, *, settings, workspace_id, meeting_id, owner_user_id, now=None):
    from twobrain_rec_server.cabinet.summary_sharing import batch_view
    from twobrain_rec_server.db.models.summary_sharing import SummaryDeliveryBatch

    now = now or datetime.now(UTC)
    meeting = await _owner_meeting(db, workspace_id, meeting_id, owner_user_id)
    preference = await get_preferences(db, workspace_id=workspace_id, owner_user_id=owner_user_id)
    audience = await _audience(db, settings=settings, meeting=meeting, now=now)
    rules = await _rules(db, meeting, audience)
    by_scope = {rule.scope: rule for rule in rules}
    rule = by_scope.get("meeting") or by_scope.get("series")
    batch = await db.scalar(
        select(SummaryDeliveryBatch)
        .where(
            SummaryDeliveryBatch.workspace_id == workspace_id,
            SummaryDeliveryBatch.meeting_id == meeting_id,
            SummaryDeliveryBatch.owner_user_id == owner_user_id,
            SummaryDeliveryBatch.automatic.is_(True),
        )
        .order_by(SummaryDeliveryBatch.created_at.desc())
        .limit(1)
    )
    exception = await _exception(db, meeting)
    state, reason = "off", None
    view = await batch_view(db, batch, settings=settings) if batch else None
    if batch:
        state = _delivery_presentation(batch, view["counts"])
    elif rule and rule.enabled:
        state = "waiting_summary"
        if not audience.guard.allowed:
            state, reason = "requires_review", audience.guard.reason_code
        elif rule.approved_roster_fingerprint != audience.fingerprint:
            state, reason = "requires_review", "roster_changed"
    if exception:
        state, reason = exception.state, exception.reason_code
    if preference.paused and state not in {"sent", "partial", "unknown", "cancelled", "expired"}:
        state, reason = "paused", "auto_paused"
    selected = {person["user_id"] for person in rule.approved_recipients_json} if rule else set()
    for person in audience.roster or []:
        person["selected"] = person["user_id"] in selected
    return {
        "state": state,
        "reason_code": reason,
        "ask_enabled": preference.ask_enabled,
        "paused": preference.paused,
        "preferences_version": preference.version,
        "rules": {scope: _rule_json(by_scope.get(scope)) for scope in ("meeting", "series")},
        "available_scopes": [
            scope for scope, target in _targets(meeting, audience).items() if target
        ],
        "effective_scope": rule.scope if rule else None,
        "template_key": rule.template_key if rule else None,
        "eligible": audience.guard.allowed,
        "eligibility_reason_code": audience.guard.reason_code,
        "roster": audience.roster or [],
        "batch": view,
    }


async def preferences_view(db, *, workspace_id, owner_user_id):
    preference = await get_preferences(db, workspace_id=workspace_id, owner_user_id=owner_user_id)
    rules = (
        await db.scalars(
            select(SummaryAutoSendRule)
            .where(
                SummaryAutoSendRule.workspace_id == workspace_id,
                SummaryAutoSendRule.owner_user_id == owner_user_id,
            )
            .order_by(SummaryAutoSendRule.updated_at.desc())
            .limit(100)
        )
    ).all()
    from twobrain_rec_server.db.models.summary_sharing import (
        SummaryDeliveryBatch,
        SummaryRecipientDelivery,
    )

    queue = (
        await db.scalars(
            select(SummaryDeliveryBatch)
            .where(
                SummaryDeliveryBatch.workspace_id == workspace_id,
                SummaryDeliveryBatch.owner_user_id == owner_user_id,
                SummaryDeliveryBatch.automatic.is_(True),
                SummaryDeliveryBatch.state.in_(
                    ["pending", "scheduled", "sending", "requires_review"]
                ),
            )
            .order_by(SummaryDeliveryBatch.created_at.desc())
            .limit(50)
        )
    ).all()
    counts_by_batch = {batch.id: {} for batch in queue}
    if queue:
        for batch_id, state, count in await db.execute(
            select(SummaryRecipientDelivery.batch_id, SummaryRecipientDelivery.state, func.count())
            .where(
                SummaryRecipientDelivery.workspace_id == workspace_id,
                SummaryRecipientDelivery.batch_id.in_(counts_by_batch),
            )
            .group_by(SummaryRecipientDelivery.batch_id, SummaryRecipientDelivery.state)
        ):
            counts_by_batch[batch_id][state] = count
    return {
        "ask_enabled": preference.ask_enabled,
        "paused": preference.paused,
        "version": preference.version,
        "auto_epoch": preference.auto_epoch,
        "rules": [
            _rule_json(rule) | {"meeting_id": str(rule.meeting_id) if rule.meeting_id else None}
            for rule in rules
        ],
        "queue": [
            {
                "batch_id": str(batch.id),
                "meeting_id": str(batch.meeting_id),
                "state": _delivery_presentation(batch, counts_by_batch[batch.id]),
                "scheduled_at": batch.scheduled_at,
                "can_cancel": bool(counts_by_batch[batch.id].get("pending")),
            }
            for batch in queue
        ],
    }


async def disable_rule(db, *, workspace_id, owner_user_id, rule_id, expected_version):
    # Taking only preference -> rule avoids an inverse rule -> meeting lock.
    await get_preferences(
        db, workspace_id=workspace_id, owner_user_id=owner_user_id, for_update=True
    )
    rule = await db.scalar(
        select(SummaryAutoSendRule)
        .where(
            SummaryAutoSendRule.id == rule_id,
            SummaryAutoSendRule.workspace_id == workspace_id,
            SummaryAutoSendRule.owner_user_id == owner_user_id,
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if rule is None:
        raise _problem("auto_rule_not_found", status=404)
    if rule.version != expected_version:
        raise _problem("auto_rule_conflict", status=409)
    if rule.enabled:
        rule.enabled = False
        rule.disabled_at = datetime.now(UTC)
        rule.version += 1
    await db.flush()
    return _rule_json(rule)
