from __future__ import annotations

from datetime import UTC, datetime
from urllib.parse import urlencode
from uuid import UUID

from sqlalchemy import (
    Integer,
    Select,
    String,
    and_,
    asc,
    case,
    cast,
    desc,
    exists,
    func,
    literal,
    nullslast,
    or_,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.api.schemas import (
    AccessState,
    MeetingActivityItem,
    MeetingActivityResponse,
    MeetingCalendarContextResponse,
    MeetingFilterState,
    MeetingListResponse,
    MeetingReviewResponse,
    MeetingReviewStatus,
    MeetingUploadProgressState,
    PreviousRecurringMeetingView,
)
from twobrain_rec_server.auth.context import TenantScope
from twobrain_rec_server.auth.policy import read_auth_providers
from twobrain_rec_server.auth.provider_links import (
    RECOVERY_CAPABLE_PROVIDERS,
    recovery_safe_unlink_allowed,
)
from twobrain_rec_server.auth.providers import build_provider_registry
from twobrain_rec_server.cabinet.access import (
    ShareRecipientAccessProof,
    decide_meeting_access,
    recipient_share_access_proof,
    share_panel_state,
)
from twobrain_rec_server.cabinet.egress import (
    activity_response,
    artifact_egress_states,
    content_export_capabilities,
    current_outcome_set,
    review_playback_state,
)
from twobrain_rec_server.cabinet.speakers import speaker_names_for_result
from twobrain_rec_server.cabinet.view_models import (
    AUTHORITATIVE_TITLE_SOURCES,
    PROVIDER_LINK_LABELS,
    MeetingListTimeBasis,
    ProviderLinkSettingsSurface,
    ProviderLinkStartOption,
    SharedWithMeMeetingItem,
    build_list_item,
    build_review_response,
    format_duration,
    meeting_list_presentation_status,
    meeting_list_time_label,
    meeting_list_title,
    meeting_source,
    normalize_meeting_list_sort,
    previous_recurring_meeting_readiness,
    provider_link_settings_surface,
    safe_title,
)
from twobrain_rec_server.calendar.audit import calendar_context_activity_projections
from twobrain_rec_server.calendar.google import google_oauth_config_from_settings
from twobrain_rec_server.calendar.service import (
    SELECTABLE_CALENDAR_VISIBILITIES,
    calendar_event_matches_preferences,
    get_calendar_settings_preferences,
    get_meeting_calendar_context_response,
    list_owner_context_correction_candidates,
    list_provider_presets,
)
from twobrain_rec_server.db.models import (
    AccountClosureRequest,
    AuthSession,
    CalendarEventSnapshot,
    CalendarParticipant,
    CalendarSettingsPreference,
    CalendarSource,
    DiarizationSegment,
    ExternalCalendar,
    ExternalIdentity,
    MediaRevision,
    Meeting,
    MeetingOutcomeSet,
    MeetingShareGrant,
    MeetingSpeakerName,
    MeetingSummarySlot,
    ProcessingDependencyState,
    ProcessingResult,
    ProcessingWorkflow,
    RecordingCalendarContextLink,
    RegisteredDevice,
    SummaryTemplate,
    TranscriptSegment,
    UploadPart,
    UploadSession,
    UserIdentity,
    Workspace,
    WorkspaceProviderLinkState,
)
from twobrain_rec_server.db.tenant_context import (
    SharedWithMeLookupContext,
    TenantDatabaseContext,
    apply_tenant_context,
)
from twobrain_rec_server.domain.media_filenames import MEDIA_FILENAME_EXTENSION_ALTERNATION
from twobrain_rec_server.domain.statuses import (
    DeletionState,
    MediaRevisionSourceKind,
    MediaRevisionStatus,
    ProcessingResultStatus,
    UploadSessionStatus,
)
from twobrain_rec_server.outcomes.service import load_outcome_items
from twobrain_rec_server.outcomes.templates import built_in_template_for_version
from twobrain_rec_server.processing.results import (
    effective_processing_result_query,
)

WEB_STATUS_FILTER_GROUPS: dict[MeetingReviewStatus, frozenset[MeetingReviewStatus]] = {
    "processing": frozenset({"local_only", "uploading", "processing", "submitted"}),
    "failed": frozenset({"failed", "blocked", "unavailable"}),
}
GENERATED_TITLE_MONTH_FRAGMENTS = frozenset(
    {"янв", "фев", "мар", "апр", "май", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"}
)
GENERATED_CAPTURE_TITLE_SQL_RE = (
    r"^(current( display)? system audio|system audio|yandex telemost|zoom(\.us)?|meeting)"
    r"[[:space:]]*-[[:space:]]*[0-9]{4}-[0-9]{2}-[0-9]{2}"
    r"([ T][0-9]{1,2}:[0-9]{2})?$"
)
GENERATED_MANUAL_UPLOAD_SQL_RE = r"^manual[-_]upload([-_][a-z0-9]+)+$"


async def get_provider_link_start_options(
    db: AsyncSession,
    tenant_scope: TenantScope,
) -> tuple[ProviderLinkStartOption, ...]:
    snapshot = await read_auth_providers(
        db,
        tenant_scope.workspace_id,
        adapters=build_provider_registry(),
        persist_defaults=True,
    )
    return tuple(
        ProviderLinkStartOption(
            provider=entry.provider,
            label=PROVIDER_LINK_LABELS.get(entry.provider, entry.label),
        )
        for entry in snapshot.providers
        if entry.enabled
    )


async def get_provider_link_settings_surface(
    db: AsyncSession,
    tenant_scope: TenantScope,
    *,
    link_state_id: UUID,
) -> ProviderLinkSettingsSurface | None:
    link = await db.scalar(
        select(WorkspaceProviderLinkState).where(
            WorkspaceProviderLinkState.id == link_state_id,
            WorkspaceProviderLinkState.workspace_id == tenant_scope.workspace_id,
            WorkspaceProviderLinkState.initiating_user_id == tenant_scope.user_id,
        )
    )
    return provider_link_settings_surface(link) if link is not None else None


async def get_account_settings_surface(
    db: AsyncSession,
    tenant_scope: TenantScope,
):
    from datetime import UTC, datetime

    from twobrain_rec_server.auth.account_closure import close_view
    from twobrain_rec_server.cabinet.view_models import account_settings_surface

    user = await db.get(UserIdentity, tenant_scope.user_id)

    identities = tuple(
        await db.scalars(
            select(ExternalIdentity)
            .where(
                ExternalIdentity.user_id == tenant_scope.user_id,
                ExternalIdentity.is_active.is_(True),
            )
            .order_by(ExternalIdentity.created_at.asc())
        )
    )
    verified_recovery_count = sum(
        1
        for identity in identities
        if identity.is_verified and identity.provider in RECOVERY_CAPABLE_PROVIDERS
    )
    devices = tuple(
        await db.scalars(
            select(RegisteredDevice)
            .where(
                RegisteredDevice.workspace_id == tenant_scope.workspace_id,
                RegisteredDevice.user_id == tenant_scope.user_id,
            )
            .order_by(RegisteredDevice.created_at.desc())
        )
    )
    sessions = tuple(
        await db.scalars(
            select(AuthSession)
            .where(
                AuthSession.workspace_id == tenant_scope.workspace_id,
                AuthSession.user_id == tenant_scope.user_id,
            )
            .order_by(AuthSession.last_seen_at.desc(), AuthSession.created_at.desc())
        )
    )
    closure = await db.scalar(
        select(AccountClosureRequest)
        .where(
            AccountClosureRequest.workspace_id == tenant_scope.workspace_id,
            AccountClosureRequest.requested_by_user_id == tenant_scope.user_id,
            AccountClosureRequest.state.in_(("scheduled", "finalizing")),
        )
        .order_by(AccountClosureRequest.requested_at.desc())
    )
    return account_settings_surface(
        profile=_account_profile_view(user, identities),
        identities=identities,
        devices=devices,
        sessions=sessions,
        current_session_id=tenant_scope.auth_session_id,
        current_device_id=tenant_scope.device_id,
        can_unlink_provider=lambda identity: recovery_safe_unlink_allowed(
            verified_identity_count=verified_recovery_count
            + int(identity.is_verified and identity.provider not in RECOVERY_CAPABLE_PROVIDERS),
            target_is_verified=identity.is_verified,
        ),
        account_close=(close_view(closure, now=datetime.now(UTC)) if closure else None),
    )


def _account_profile_view(user: UserIdentity | None, identities: tuple[ExternalIdentity, ...]):
    from twobrain_rec_server.cabinet.view_models import AccountProfileView

    return AccountProfileView(
        display_name=(user.display_name if user and user.display_name else "Без имени"),
        primary_email=next(
            (identity.email for identity in identities if identity.email and identity.is_verified),
            None,
        ),
        locale=(user.locale if user else "ru-RU"),
        timezone=(user.timezone if user else "Europe/Moscow"),
        theme=(user.theme if user else "system"),
    )


async def get_account_profile_view(db: AsyncSession, tenant_scope: TenantScope):
    user = await db.get(UserIdentity, tenant_scope.user_id)
    identities = tuple(
        await db.scalars(
            select(ExternalIdentity)
            .where(
                ExternalIdentity.user_id == tenant_scope.user_id,
                ExternalIdentity.is_active.is_(True),
            )
            .order_by(ExternalIdentity.created_at.asc())
        )
    )
    return _account_profile_view(user, identities)


async def get_calendar_settings_surface(
    db: AsyncSession,
    tenant_scope: TenantScope,
    *,
    settings: object | None = None,
    notice_codes: tuple[str, ...] = (),
):
    from twobrain_rec_server.cabinet.view_models import calendar_settings_surface

    sources = list(
        await db.scalars(
            select(CalendarSource)
            .where(
                CalendarSource.workspace_id == tenant_scope.workspace_id,
                CalendarSource.owner_user_id == tenant_scope.user_id,
                CalendarSource.disconnected_at.is_(None),
                CalendarSource.connection_state != "disconnected",
            )
            .order_by(CalendarSource.created_at.desc())
        )
    )
    source_ids = [source.id for source in sources]
    calendars_by_source: dict[object, list[ExternalCalendar]] = {
        source.id: [] for source in sources
    }
    if source_ids:
        calendars = list(
            await db.scalars(
                select(ExternalCalendar)
                .where(
                    ExternalCalendar.workspace_id == tenant_scope.workspace_id,
                    ExternalCalendar.calendar_source_id.in_(source_ids),
                )
                .order_by(ExternalCalendar.display_label.asc())
            )
        )
        for calendar in calendars:
            calendars_by_source.setdefault(calendar.calendar_source_id, []).append(calendar)
    preference = await get_calendar_settings_preferences(db, tenant_scope)
    preview = await _calendar_settings_preview_events(
        db,
        tenant_scope,
        source_ids=source_ids,
        preference=preference,
    )
    return calendar_settings_surface(
        provider_payloads=list_provider_presets(
            google_available=(
                google_oauth_config_from_settings(settings) is not None
                if settings is not None
                else None
            ),
            allow_uncertified_google=(
                settings is not None
                and getattr(settings, "env", "production").lower() == "development"
            ),
        ),
        sources=sources,
        calendars_by_source=calendars_by_source,
        preference=preference,
        preview_events=preview,
        notice_codes=notice_codes,
    )


async def _calendar_settings_preview_events(
    db: AsyncSession,
    tenant_scope: TenantScope,
    *,
    source_ids: list[UUID],
    preference: CalendarSettingsPreference | None,
) -> list[CalendarEventSnapshot]:
    if not source_ids:
        return []
    selected_calendar_ids = list(
        await db.scalars(
            select(ExternalCalendar.id).where(
                ExternalCalendar.workspace_id == tenant_scope.workspace_id,
                ExternalCalendar.calendar_source_id.in_(source_ids),
                ExternalCalendar.selected.is_(True),
                ExternalCalendar.visibility.in_(SELECTABLE_CALENDAR_VISIBILITIES),
            )
        )
    )
    if not selected_calendar_ids:
        return []
    now = datetime.now(UTC)
    query = (
        select(CalendarEventSnapshot)
        .where(
            CalendarEventSnapshot.workspace_id == tenant_scope.workspace_id,
            CalendarEventSnapshot.calendar_source_id.in_(source_ids),
            CalendarEventSnapshot.external_calendar_id.in_(selected_calendar_ids),
            CalendarEventSnapshot.source_deleted_at.is_(None),
            CalendarEventSnapshot.ends_at > now,
        )
        .order_by(CalendarEventSnapshot.starts_at.asc())
    )
    if preference is None or not preference.include_all_day_events:
        query = query.where(CalendarEventSnapshot.all_day.is_(False))
    if preference is None or not preference.include_private_free_busy_prompt_candidates:
        query = query.where(
            CalendarEventSnapshot.safe_to_show_in_list.is_(True),
            CalendarEventSnapshot.privacy_class.notin_({"private", "free_busy", "free_busy_only"}),
        )
    rows = list(await db.scalars(query.limit(81)))
    return [event for event in rows if calendar_event_matches_preferences(event, preference)][:8]


async def list_cabinet_meetings(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    viewer_user_id: UUID,
    storage: object | None = None,
    q: str | None = None,
    status: MeetingReviewStatus | None = None,
    group_status_filter: bool = False,
    visible_title_search: bool = False,
    access: AccessState | None = None,
    sort: str = "updated_desc",
    unknown_sort_fallback: str = "updated_desc",
    normalize_response_sort: bool = False,
    limit: int = 50,
) -> MeetingListResponse:
    requested_sort = sort
    sort = normalize_meeting_list_sort(sort, fallback=unknown_sort_fallback)
    visible_time_basis: MeetingListTimeBasis = (
        "updated" if sort in {"updated_desc", "updated_asc"} else "meeting"
    )
    query = select(Meeting).where(
        Meeting.workspace_id == workspace_id,
        Meeting.deleted_at.is_(None),
        or_(Meeting.deletion_state.is_(None), Meeting.deletion_state == DeletionState.NONE.value),
    )
    if (
        q
        and (
            search_filter := _meeting_search_candidate_filter(
                q,
                include_visible_time=visible_title_search,
                visible_time_basis=visible_time_basis,
            )
        )
        is not None
    ):
        query = query.where(search_filter)
    query = _apply_sort(query, sort)
    meetings = (await db.scalars(query)).all()
    matching_statuses = (
        WEB_STATUS_FILTER_GROUPS.get(status, frozenset({status}))
        if status is not None and group_status_filter
        else frozenset({status})
        if status is not None
        else None
    )

    items = []
    for meeting in meetings:
        decision = await decide_meeting_access(
            db,
            meeting,
            workspace_id=workspace_id,
            viewer_user_id=viewer_user_id,
        )
        if not decision.can_view:
            continue
        if access is not None and decision.state != access:
            continue
        media_revision = await _latest_media_revision(
            db, workspace_id=workspace_id, meeting_id=meeting.id
        )
        source = meeting_source(media_revision)
        if q and not _meeting_matches_query(
            meeting,
            q,
            source=source,
            visible_title_only=visible_title_search,
            visible_time_basis=visible_time_basis,
        ):
            continue
        media_revision_id = media_revision.id if media_revision is not None else None
        workflow = await _latest_workflow(
            db,
            workspace_id=workspace_id,
            meeting_id=meeting.id,
            media_revision_id=media_revision_id,
        )
        result = await _latest_result(
            db,
            workspace_id=workspace_id,
            meeting_id=meeting.id,
            media_revision_id=media_revision_id,
        )
        outcome_set = await _current_outcome_set(
            db,
            workspace_id=workspace_id,
            meeting_id=meeting.id,
            processing_result_id=result.id if result is not None else None,
        )
        artifacts = await artifact_egress_states(
            db, meeting=meeting, access=decision, result=result
        )
        playback = await review_playback_state(
            db,
            meeting=meeting,
            access=decision,
            storage=storage,
        )
        upload_progress = await _latest_upload_progress(db, meeting)
        calendar_context = await _calendar_context_link(
            db,
            workspace_id=workspace_id,
            meeting_id=meeting.id,
        )
        previous_recurring_meeting = await _previous_recurring_meeting(
            db,
            workspace_id=workspace_id,
            viewer_user_id=viewer_user_id,
            meeting_id=meeting.id,
            current_link=calendar_context,
        )
        item = build_list_item(
            meeting,
            media_revision=media_revision,
            result=result,
            workflow=workflow,
            access=decision.to_schema(),
            artifacts=artifacts,
            outcome_set=outcome_set,
            outcome_items=[],
            upload=upload_progress,
            calendar_context=calendar_context,
            previous_recurring_meeting=previous_recurring_meeting,
            playback=playback,
        )
        if visible_title_search:
            item.title = meeting_list_title(meeting, source=source)
        filter_status = (
            meeting_list_presentation_status(item) if group_status_filter else item.status
        )
        if matching_statuses is not None and filter_status not in matching_statuses:
            continue
        items.append(item)
        if sort != "title_asc" and len(items) > limit:
            break
    if sort == "title_asc":
        items.sort(key=lambda item: item.title.casefold())
    has_more = len(items) > limit
    response = MeetingListResponse(
        items=items[:limit],
        filters=MeetingFilterState(
            q=q,
            status=status,
            access=access,
            sort=sort if normalize_response_sort else requested_sort,
        ),
        generated_at=datetime.now(UTC),
    )
    response._has_more = has_more
    return response


async def list_shared_with_me_meetings(
    sessionmaker,
    *,
    recipient_scope: TenantScope,
    limit: int = 50,
) -> tuple[SharedWithMeMeetingItem, ...]:
    """List only recipient grants that still pass the existing access decision."""
    now = datetime.now(UTC)
    async with sessionmaker() as lookup_db:
        await apply_tenant_context(
            lookup_db,
            SharedWithMeLookupContext(user_id=recipient_scope.user_id),
        )
        grants = list(
            await lookup_db.scalars(
                select(MeetingShareGrant)
                .where(
                    MeetingShareGrant.grantee_user_id == recipient_scope.user_id,
                    MeetingShareGrant.audience_type == "user",
                    MeetingShareGrant.status == "active",
                    MeetingShareGrant.expires_at.is_(None) | (MeetingShareGrant.expires_at > now),
                )
                .order_by(MeetingShareGrant.created_at.desc())
                .limit(limit)
            )
        )
    grants_by_workspace: dict[UUID, list[MeetingShareGrant]] = {}
    for grant in grants:
        grants_by_workspace.setdefault(grant.workspace_id, []).append(grant)

    rows: dict[UUID, tuple[datetime, tuple[int, int, int], SharedWithMeMeetingItem]] = {}
    for workspace_id, workspace_grants in grants_by_workspace.items():
        proof = await recipient_share_access_proof(
            sessionmaker,
            recipient_scope=recipient_scope,
            owner_workspace_id=workspace_id,
        )
        if not proof.user_is_active:
            continue
        async with sessionmaker() as source_db:
            await apply_tenant_context(
                source_db,
                TenantDatabaseContext(
                    organization_id=UUID(int=0),
                    workspace_id=workspace_id,
                    user_id=UUID(int=0),
                ),
            )
            meeting_ids = [grant.meeting_id for grant in workspace_grants]
            meetings = {
                meeting.id: meeting
                for meeting in await source_db.scalars(
                    select(Meeting).where(
                        Meeting.workspace_id == workspace_id,
                        Meeting.id.in_(meeting_ids),
                        Meeting.deleted_at.is_(None),
                        or_(
                            Meeting.deletion_state.is_(None),
                            Meeting.deletion_state == DeletionState.NONE.value,
                        ),
                    )
                )
            }
            for grant in workspace_grants:
                meeting = meetings.get(grant.meeting_id)
                if meeting is None:
                    continue
                decision = await decide_meeting_access(
                    source_db,
                    meeting,
                    workspace_id=workspace_id,
                    viewer_user_id=recipient_scope.user_id,
                    recipient_proof=proof,
                )
                if not decision.can_view:
                    continue
                rank = (
                    int(decision.can_view_full_meeting),
                    int(decision.can_download),
                    int(decision.can_export),
                )
                occurred_at = meeting.started_at or meeting.created_at
                card = SharedWithMeMeetingItem(
                    title=meeting_list_title(meeting),
                    time_label=meeting_list_time_label(
                        occurred_at,
                        timezone_offset_minutes=meeting.recording_display_timezone_offset_minutes,
                        time_basis="meeting",
                    ),
                    duration_label=format_duration(meeting.duration_seconds),
                    status_label=(
                        "В обработке"
                        if meeting.processing_status in {"submitted", "processing", "uploading"}
                        else "Готово"
                    ),
                    access_label=(
                        "Полный доступ" if decision.can_view_full_meeting else "Только итоги"
                    ),
                    href=(
                        f"/shared-meetings/{meeting.id}?"
                        f"{urlencode({'workspace_id': str(workspace_id)})}"
                    ),
                )
                previous = rows.get(meeting.id)
                if previous is None or rank > previous[1]:
                    rows[meeting.id] = (occurred_at, rank, card)
    return tuple(card for _, _, card in sorted(rows.values(), key=lambda row: row[0], reverse=True))


def _meeting_matches_query(
    meeting: Meeting,
    query: str,
    *,
    source: str | None,
    visible_title_only: bool,
    visible_time_basis: MeetingListTimeBasis,
) -> bool:
    normalized_query = " ".join(query.casefold().split())
    if not normalized_query:
        return True
    visible_title = (
        meeting_list_title(meeting, source=source)
        if visible_title_only
        else safe_title(meeting, source=source)
    )
    if visible_title_only:
        visible_duration = format_duration(meeting.duration_seconds)
        visible_time_value = (
            meeting.updated_at
            if visible_time_basis == "updated"
            else meeting.started_at
        )
        visible_time_label_basis: MeetingListTimeBasis = visible_time_basis
        if (
            visible_time_basis == "meeting"
            and visible_time_value is None
            and source == "manual_upload"
        ):
            visible_time_value = meeting.created_at
            visible_time_label_basis = "upload"
        visible_time = meeting_list_time_label(
            visible_time_value,
            timezone_offset_minutes=meeting.recording_display_timezone_offset_minutes,
            time_basis=visible_time_label_basis,
        )
        candidates = (
            visible_title,
            visible_duration,
            visible_time,
            f"{visible_title} {visible_duration}",
            f"{visible_title} {visible_time}",
            f"{visible_duration} {visible_time}",
            f"{visible_title} {visible_duration} {visible_time}",
        )
    else:
        candidates = (meeting.title, meeting.local_recording_id, visible_title)
    return any(
        normalized_query in " ".join(candidate.casefold().split())
        for candidate in candidates
        if candidate
    )


def _meeting_search_candidate_filter(
    query: str,
    *,
    include_visible_time: bool = False,
    visible_time_basis: MeetingListTimeBasis = "meeting",
):
    normalized_query = " ".join(query.casefold().split())
    if not normalized_query:
        return None

    pattern = _escaped_contains_pattern(normalized_query)
    normalized_title = func.regexp_replace(
        func.btrim(Meeting.title),
        "[[:space:]]+",
        " ",
        "g",
    )
    normalized_local_id = func.regexp_replace(
        func.replace(Meeting.local_recording_id, "_", " "),
        "[[:space:]]+",
        " ",
        "g",
    )
    direct_matches = or_(
        Meeting.title.ilike(pattern, escape="\\"),
        Meeting.local_recording_id.ilike(pattern, escape="\\"),
        func.replace(Meeting.title, "_", " ").ilike(pattern, escape="\\"),
        func.replace(Meeting.local_recording_id, "_", " ").ilike(pattern, escape="\\"),
        normalized_title.ilike(pattern, escape="\\"),
        normalized_local_id.ilike(pattern, escape="\\"),
    )
    display_only_candidates = []
    if not include_visible_time and _query_can_match_generated_recording_title(normalized_query):
        display_only_candidates.append(Meeting.title_source.notin_(AUTHORITATIVE_TITLE_SOURCES))
    if normalized_query in "загруженная запись":
        display_only_candidates.append(
            or_(
                Meeting.title.ilike("manual-upload-%"),
                Meeting.title.ilike("manual_upload_%"),
                Meeting.local_recording_id.ilike("manual-upload-%"),
                Meeting.local_recording_id.ilike("manual_upload_%"),
                exists(
                    select(MediaRevision.id).where(
                        MediaRevision.workspace_id == Meeting.workspace_id,
                        MediaRevision.meeting_id == Meeting.id,
                        MediaRevision.source_kind == MediaRevisionSourceKind.MANUAL_UPLOAD.value,
                    )
                ),
            )
        )
    if include_visible_time:
        display_only_candidates.append(
            _meeting_visible_row_search_expression(
                time_basis=visible_time_basis,
            ).ilike(pattern, escape="\\")
        )
    return or_(direct_matches, *display_only_candidates)


def _meeting_visible_row_search_expression(*, time_basis: MeetingListTimeBasis):
    """Build a SQL-only coarse projection for visible date/duration searches.

    The exact match remains in `_meeting_matches_query`; this expression prevents
    projected-field searches from expanding into per-meeting access/media queries.
    """

    manual_upload = or_(
        Meeting.title.ilike("manual-upload-%"),
        Meeting.title.ilike("manual_upload_%"),
        Meeting.local_recording_id.ilike("manual-upload-%"),
        Meeting.local_recording_id.ilike("manual_upload_%"),
        exists(
            select(MediaRevision.id).where(
                MediaRevision.workspace_id == Meeting.workspace_id,
                MediaRevision.meeting_id == Meeting.id,
                MediaRevision.source_kind == MediaRevisionSourceKind.MANUAL_UPLOAD.value,
            )
        ),
    )
    upload_fallback = and_(Meeting.started_at.is_(None), manual_upload)
    timestamp_value = (
        Meeting.updated_at
        if time_basis == "updated"
        else case(
            (upload_fallback, Meeting.created_at),
            else_=Meeting.started_at,
        )
    )
    timezone_offset = case(
        (
            Meeting.recording_display_timezone_offset_minutes.between(-14 * 60, 14 * 60),
            Meeting.recording_display_timezone_offset_minutes,
        ),
        else_=0,
    )
    localized_timestamp = func.timezone(literal("UTC"), timestamp_value) + func.make_interval(
        0,
        0,
        0,
        0,
        0,
        func.coalesce(timezone_offset, 0),
    )
    month_number = cast(func.extract("month", localized_timestamp), Integer)
    month_label = case(
        *[
            (month_number == month, literal(label))
            for month, label in enumerate(
                (
                    "янв",
                    "фев",
                    "мар",
                    "апр",
                    "май",
                    "июн",
                    "июл",
                    "авг",
                    "сен",
                    "окт",
                    "ноя",
                    "дек",
                ),
                start=1,
            )
        ],
        else_=literal(""),
    )
    date_prefix = (
        literal("Обновлено ")
        if time_basis == "updated"
        else case((upload_fallback, literal("Загружено ")), else_=literal(""))
    )
    time_label = case(
        (timestamp_value.is_(None), literal("Без даты")),
        else_=func.concat(
            date_prefix,
            cast(cast(func.extract("day", localized_timestamp), Integer), String),
            literal(" "),
            month_label,
            literal(", "),
            func.to_char(localized_timestamp, literal("HH24:MI")),
        ),
    )

    duration_seconds = func.greatest(Meeting.duration_seconds, 0)
    duration_hours = cast(func.floor(duration_seconds / 3600), Integer)
    duration_minutes = cast(func.floor((duration_seconds % 3600) / 60), Integer)
    total_minutes = cast(func.floor(duration_seconds / 60), Integer)
    duration_label = case(
        (
            duration_hours > 0,
            func.concat(
                cast(duration_hours, String),
                literal(" ч"),
                case(
                    (
                        duration_minutes > 0,
                        func.concat(
                            literal(" "),
                            cast(duration_minutes, String),
                            literal(" мин"),
                        ),
                    ),
                    else_=literal(""),
                ),
            ),
        ),
        (
            total_minutes > 0,
            func.concat(cast(total_minutes, String), literal(" мин")),
        ),
        else_=func.concat(cast(duration_seconds, String), literal(" с")),
    )

    raw_title = func.nullif(func.btrim(Meeting.title), "")
    title = func.left(raw_title, 500)
    unsafe_title = or_(
        raw_title.op("~*")(
            r"https?://|www\.|[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}|"
            r"token=|password|bearer[[:space:]]|(^|[^A-Z0-9])sk-[A-Z0-9_-]{8,}|"
            r"\m([A-Z0-9-]+\.)+[A-Z]{2,}/[^[:space:]<>'\"]+"
        ),
        raw_title.op("~")(r"[[:cntrl:]]"),
    )
    safe_title_value = case((unsafe_title, None), else_=title)
    normalized_title = func.regexp_replace(
        safe_title_value,
        "[[:space:]]+",
        " ",
        "g",
    )
    leaf_title = func.regexp_replace(normalized_title, r"^.*[\\/]", "", "g")
    authoritative_title = case(
        (
            or_(
                normalized_title.like("/%"),
                normalized_title.like("\\%"),
                normalized_title.op("~")(r"^[A-Za-z]:[\\/]"),
            ),
            leaf_title,
        ),
        else_=normalized_title,
    )
    normalized_file_title = func.regexp_replace(
        func.replace(leaf_title, "_", " "),
        "[[:space:]]+",
        " ",
        "g",
    )
    cleaned_file_title = func.regexp_replace(
        normalized_file_title,
        rf"\.({MEDIA_FILENAME_EXTENSION_ALTERNATION})$",
        "",
        "i",
    )
    manual_revision_exists = exists(
        select(MediaRevision.id).where(
            MediaRevision.workspace_id == Meeting.workspace_id,
            MediaRevision.meeting_id == Meeting.id,
            MediaRevision.source_kind == MediaRevisionSourceKind.MANUAL_UPLOAD.value,
        )
    )
    generated_manual_title = safe_title_value.op("~*")(GENERATED_MANUAL_UPLOAD_SQL_RE)
    generated_manual_without_title = and_(
        safe_title_value.is_(None),
        or_(
            Meeting.local_recording_id.op("~*")(GENERATED_MANUAL_UPLOAD_SQL_RE),
            manual_revision_exists,
        ),
    )
    generated_capture_title = and_(
        or_(
            Meeting.title_source.is_(None),
            Meeting.title_source.notin_(AUTHORITATIVE_TITLE_SOURCES),
        ),
        safe_title_value.op("~*")(GENERATED_CAPTURE_TITLE_SQL_RE),
    )
    fallback_looking_title = and_(
        or_(
            Meeting.title_source.is_(None),
            Meeting.title_source.notin_(AUTHORITATIVE_TITLE_SOURCES),
        ),
        safe_title_value == "Запись без названия",
    )
    visible_title = case(
        (
            and_(
                Meeting.title_source.in_(AUTHORITATIVE_TITLE_SOURCES),
                safe_title_value.is_not(None),
            ),
            authoritative_title,
        ),
        (
            or_(generated_manual_title, generated_manual_without_title),
            literal("Загруженная запись"),
        ),
        (
            or_(safe_title_value.is_(None), generated_capture_title, fallback_looking_title),
            literal("Запись"),
        ),
        (
            safe_title_value.op("~*")(rf"\.({MEDIA_FILENAME_EXTENSION_ALTERNATION})$"),
            func.coalesce(
                func.nullif(func.btrim(cleaned_file_title), ""),
                literal("Загруженная запись"),
            ),
        ),
        else_=normalized_title,
    )
    return func.concat(
        visible_title,
        literal(" "),
        duration_label,
        literal(" "),
        time_label,
        literal(" | "),
        visible_title,
        literal(" "),
        time_label,
        literal(" | "),
        duration_label,
        literal(" "),
        time_label,
    )


def _escaped_contains_pattern(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _query_can_match_generated_recording_title(normalized_query: str) -> bool:
    if normalized_query in "запись без названия" or normalized_query.startswith("запись"):
        return True
    if any(fragment in normalized_query for fragment in GENERATED_TITLE_MONTH_FRAGMENTS):
        return True
    if any(character.isdigit() for character in normalized_query):
        return True
    return "," in normalized_query or ":" in normalized_query


async def _latest_upload_progress(
    db: AsyncSession, meeting: Meeting
) -> MeetingUploadProgressState | None:
    session = await db.scalar(
        select(UploadSession)
        .where(
            UploadSession.workspace_id == meeting.workspace_id,
            UploadSession.meeting_id == meeting.id,
        )
        .order_by(UploadSession.created_at.desc())
        .limit(1)
    )
    if session is None:
        return None

    status = str(session.status)
    active_statuses = {
        UploadSessionStatus.PENDING.value,
        UploadSessionStatus.UPLOADING.value,
        UploadSessionStatus.RETRYING.value,
        UploadSessionStatus.FINALIZING.value,
    }
    is_active = status in active_statuses
    if not is_active and status == UploadSessionStatus.FINALIZED.value:
        return None

    uploaded = int(
        await db.scalar(
            select(func.coalesce(func.sum(UploadPart.byte_length), 0)).where(
                UploadPart.upload_session_id == session.id,
                UploadPart.status == "accepted",
            )
        )
        or 0
    )
    total = _expected_upload_total_bytes(session.expected_track_sizes)
    progress_percent = None
    if is_active and total > 0:
        progress_percent = max(0, min(100, round((uploaded / total) * 100)))
    return MeetingUploadProgressState(
        status=status,
        label=_upload_progress_label(status),
        uploaded_bytes=max(0, uploaded),
        total_bytes=max(0, total),
        progress_percent=progress_percent,
        is_active=is_active,
    )


def _expected_upload_total_bytes(expected_track_sizes: object) -> int:
    if not isinstance(expected_track_sizes, dict):
        return 0
    total = 0
    for value in expected_track_sizes.values():
        if isinstance(value, int | float):
            total += max(0, int(value))
    return total


def _upload_progress_label(status: str) -> str:
    if status in {
        UploadSessionStatus.PENDING.value,
        UploadSessionStatus.UPLOADING.value,
        UploadSessionStatus.RETRYING.value,
        UploadSessionStatus.FINALIZING.value,
    }:
        return "Отправляем"
    if status in {
        UploadSessionStatus.FAILED.value,
        UploadSessionStatus.ABORTED.value,
        UploadSessionStatus.EXPIRED.value,
    }:
        return "Нужна помощь"
    if status == UploadSessionStatus.DEGRADED.value:
        return "Готово с замечаниями"
    return "Готово"


async def get_cabinet_meeting_review(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting_id: UUID,
    viewer_user_id: UUID,
    storage: object | None = None,
    include_calendar_correction_candidates: bool = False,
    external_invitations_enabled: bool = False,
    invitation_encryption_key: bytes | None = None,
    recipient_proof: ShareRecipientAccessProof | None = None,
) -> MeetingReviewResponse | None:
    meeting = await db.scalar(
        select(Meeting).where(
            Meeting.workspace_id == workspace_id,
            Meeting.id == meeting_id,
        )
    )
    if meeting is None:
        return None
    decision = await decide_meeting_access(
        db,
        meeting,
        workspace_id=workspace_id,
        viewer_user_id=viewer_user_id,
        recipient_proof=recipient_proof,
    )
    if not decision.can_view:
        return None
    media_revision = await _latest_media_revision(
        db, workspace_id=workspace_id, meeting_id=meeting_id
    )
    media_revision_id = media_revision.id if media_revision is not None else None
    workflow = await _latest_workflow(
        db,
        workspace_id=workspace_id,
        meeting_id=meeting_id,
        media_revision_id=media_revision_id,
    )
    result = await _latest_result(
        db,
        workspace_id=workspace_id,
        meeting_id=meeting_id,
        media_revision_id=media_revision_id,
    )
    transcript_segments: list[TranscriptSegment] = []
    diarization_segments: list[DiarizationSegment] = []
    if result is not None:
        transcript_segments = (
            await db.scalars(
                select(TranscriptSegment)
                .where(
                    TranscriptSegment.workspace_id == workspace_id,
                    TranscriptSegment.meeting_id == meeting_id,
                    TranscriptSegment.processing_result_id == result.id,
                )
                .order_by(TranscriptSegment.sequence.asc(), TranscriptSegment.start_seconds.asc())
            )
        ).all()
        diarization_segments = (
            await db.scalars(
                select(DiarizationSegment)
                .where(
                    DiarizationSegment.workspace_id == workspace_id,
                    DiarizationSegment.meeting_id == meeting_id,
                    DiarizationSegment.processing_result_id == result.id,
                )
                .order_by(DiarizationSegment.sequence.asc(), DiarizationSegment.start_seconds.asc())
            )
        ).all()
    speaker_names = speaker_names_for_result(
        (
            await db.scalars(
                select(MeetingSpeakerName).where(
                    MeetingSpeakerName.workspace_id == workspace_id,
                    MeetingSpeakerName.meeting_id == meeting_id,
                )
            )
        ).all(),
        result_imported_at=result.imported_at if result is not None else None,
    )
    outcome_set = await _current_outcome_set(
        db,
        workspace_id=workspace_id,
        meeting_id=meeting_id,
        # The default slot is the summary's revision fence.  The transcript
        # may already have a newer imported result; passing that result ID
        # here would make a valid last-known-good summary disappear.
        processing_result_id=None,
    )
    outcome_template_name = None
    if outcome_set is not None and outcome_set.template_id is not None:
        outcome_template = await db.scalar(
            select(SummaryTemplate).where(
                SummaryTemplate.workspace_id == workspace_id,
                SummaryTemplate.id == outcome_set.template_id,
            )
        )
        outcome_template_name = outcome_template.name if outcome_template is not None else None
    default_summary_template_key = "graf-auto-v1"
    default_summary_template_name = None
    workspace = await db.scalar(select(Workspace).where(Workspace.id == workspace_id))
    if workspace is not None:
        default_definition = built_in_template_for_version(
            workspace.default_summary_template_key,
            workspace.default_summary_template_version,
        )
        if workspace.default_summary_template_id is None and default_definition is not None:
            default_summary_template_key = default_definition.key
        elif workspace.default_summary_template_id is not None:
            personal_default = await db.scalar(
                select(SummaryTemplate).where(
                    SummaryTemplate.workspace_id == workspace_id,
                    SummaryTemplate.id == workspace.default_summary_template_id,
                    SummaryTemplate.owner_user_id == viewer_user_id,
                    SummaryTemplate.template_key == workspace.default_summary_template_key,
                    SummaryTemplate.version == workspace.default_summary_template_version,
                    SummaryTemplate.status == "active",
                )
            )
            if personal_default is not None:
                default_summary_template_key = personal_default.template_key
                default_summary_template_name = personal_default.name
    dependency = await db.scalar(
        select(ProcessingDependencyState)
        .where(
            ProcessingDependencyState.workspace_id == workspace_id,
            ProcessingDependencyState.meeting_id == meeting_id,
        )
        .order_by(ProcessingDependencyState.updated_at.desc())
    )
    calendar_context = await _calendar_context_link(
        db,
        workspace_id=workspace_id,
        meeting_id=meeting_id,
    )
    calendar_context_detail = await get_meeting_calendar_context_read_model(
        db,
        workspace_id=workspace_id,
        viewer_user_id=viewer_user_id,
        meeting_id=meeting_id,
        recipient_proof=recipient_proof,
    )
    if include_calendar_correction_candidates and calendar_context_detail.can_change:
        correction_candidates = await list_owner_context_correction_candidates(
            db,
            workspace_id=workspace_id,
            owner_user_id=viewer_user_id,
            meeting_id=meeting_id,
        )
        calendar_context_detail = calendar_context_detail.model_copy(
            update={
                "candidate_count": len(correction_candidates),
                "candidates": correction_candidates,
            }
        )
    return build_review_response(
        meeting,
        media_revision=media_revision,
        result=result,
        workflow=workflow,
        transcript_segments=transcript_segments,
        diarization_segments=diarization_segments,
        dependency=dependency,
        access=decision.to_schema(),
        share=await share_panel_state(
            db,
            meeting,
            decision,
            external_invitations_enabled=external_invitations_enabled,
            invitation_encryption_key=invitation_encryption_key,
        ),
        artifacts=await artifact_egress_states(db, meeting=meeting, access=decision, result=result),
        content_exports=await content_export_capabilities(
            db, meeting=meeting, access=decision, result=result
        ),
        review_playback=await review_playback_state(
            db,
            meeting=meeting,
            access=decision,
            storage=storage,
        ),
        calendar_roster=await _calendar_roster_state(
            db,
            workspace_id=workspace_id,
            meeting_id=meeting_id,
            link=calendar_context,
        ),
        calendar_context=calendar_context,
        calendar_context_detail=calendar_context_detail,
        activity=await _meeting_activity_response(
            db,
            workspace_id=workspace_id,
            meeting_id=meeting_id,
            viewer_user_id=viewer_user_id,
        ),
        outcome_set=outcome_set,
        outcome_template_name=outcome_template_name,
        default_summary_template_key=default_summary_template_key,
        default_summary_template_name=default_summary_template_name,
        outcome_items=await load_outcome_items(db, outcome_set=outcome_set),
        speaker_names=speaker_names,
        can_rename_speakers=decision.state == "owner" or decision.role in {"owner", "admin"},
    )


async def _meeting_activity_response(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting_id: UUID,
    viewer_user_id: UUID,
) -> MeetingActivityResponse:
    base = await activity_response(
        db,
        workspace_id=workspace_id,
        meeting_id=meeting_id,
        viewer_user_id=viewer_user_id,
    )
    calendar_items = [
        MeetingActivityItem(
            event_id=projection.event_id,
            event_type=projection.event_type,
            actor_label=("You" if projection.actor_user_id == viewer_user_id else "User"),
            artifact_class=None,
            outcome="completed",
            reason=projection.reason,
            created_at=projection.created_at,
        )
        for projection in await calendar_context_activity_projections(
            db,
            workspace_id=workspace_id,
            meeting_id=meeting_id,
        )
    ]
    items = sorted(
        [*base.items, *calendar_items],
        key=lambda item: (item.created_at, str(item.event_id)),
        reverse=True,
    )[:50]
    return MeetingActivityResponse(
        meeting_id=meeting_id,
        redaction_state="metadata_only",
        items=items,
    )


async def _calendar_context_link(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting_id: UUID,
) -> RecordingCalendarContextLink | None:
    return await db.scalar(
        select(RecordingCalendarContextLink).where(
            RecordingCalendarContextLink.workspace_id == workspace_id,
            RecordingCalendarContextLink.meeting_id == meeting_id,
        )
    )


async def get_meeting_calendar_context_read_model(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    viewer_user_id: UUID,
    meeting_id: UUID,
    recipient_proof: ShareRecipientAccessProof | None = None,
) -> MeetingCalendarContextResponse:
    """Return current context plus one independently authorized series pointer."""

    response = await get_meeting_calendar_context_response(
        db,
        workspace_id=workspace_id,
        viewer_user_id=viewer_user_id,
        meeting_id=meeting_id,
        recipient_proof=recipient_proof,
    )
    current_link = await _calendar_context_link(
        db,
        workspace_id=workspace_id,
        meeting_id=meeting_id,
    )
    previous = await _previous_recurring_meeting(
        db,
        workspace_id=workspace_id,
        viewer_user_id=viewer_user_id,
        meeting_id=meeting_id,
        current_link=current_link,
        recipient_proof=recipient_proof,
    )
    return response.model_copy(update={"previous_recurring_meeting": previous})


async def _previous_recurring_meeting(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    viewer_user_id: UUID,
    meeting_id: UUID,
    current_link: RecordingCalendarContextLink | None,
    recipient_proof: ShareRecipientAccessProof | None = None,
) -> PreviousRecurringMeetingView | None:
    if (
        current_link is None
        or current_link.context_state not in {"matched_auto", "matched_user"}
        or current_link.recurring_series_key_sha256 is None
        or current_link.matched_event_starts_at is None
    ):
        return None

    row = (
        await db.execute(
            select(RecordingCalendarContextLink, Meeting)
            .join(
                Meeting,
                Meeting.id == RecordingCalendarContextLink.meeting_id,
            )
            .where(
                RecordingCalendarContextLink.workspace_id == workspace_id,
                Meeting.workspace_id == workspace_id,
                RecordingCalendarContextLink.meeting_id != meeting_id,
                RecordingCalendarContextLink.context_state.in_({"matched_auto", "matched_user"}),
                RecordingCalendarContextLink.recurring_series_key_sha256
                == current_link.recurring_series_key_sha256,
                RecordingCalendarContextLink.matched_event_starts_at
                < current_link.matched_event_starts_at,
            )
            .order_by(
                RecordingCalendarContextLink.matched_event_starts_at.desc(),
                RecordingCalendarContextLink.id.desc(),
            )
            .limit(1)
        )
    ).first()
    if row is None:
        return None
    _previous_link, previous_meeting = row
    access = await decide_meeting_access(
        db,
        previous_meeting,
        workspace_id=workspace_id,
        viewer_user_id=viewer_user_id,
        recipient_proof=recipient_proof,
    )
    if not access.can_view or previous_meeting.started_at is None:
        return None

    media_revision = await _latest_media_revision(
        db,
        workspace_id=workspace_id,
        meeting_id=previous_meeting.id,
    )
    result = await _latest_result(
        db,
        workspace_id=workspace_id,
        meeting_id=previous_meeting.id,
        media_revision_id=media_revision.id if media_revision is not None else None,
    )
    outcome_set = await _current_outcome_set(
        db,
        workspace_id=workspace_id,
        meeting_id=previous_meeting.id,
        processing_result_id=result.id if result is not None else None,
    )
    started_at = previous_meeting.started_at
    started_at = (
        started_at.replace(tzinfo=UTC) if started_at.tzinfo is None else started_at.astimezone(UTC)
    )
    return PreviousRecurringMeetingView(
        meeting_id=previous_meeting.id,
        safe_title=safe_title(previous_meeting, include_recording_time=False),
        started_at=started_at,
        readiness_state=previous_recurring_meeting_readiness(
            previous_meeting,
            result=result,
            outcome_set=outcome_set,
        ),
    )


async def _calendar_roster_state(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting_id: UUID,
    link: RecordingCalendarContextLink | None = None,
):
    link = link or await _calendar_context_link(
        db,
        workspace_id=workspace_id,
        meeting_id=meeting_id,
    )
    if link is None:
        return None
    from twobrain_rec_server.cabinet.view_models import (
        calendar_roster_snapshot_state,
        calendar_roster_state,
    )

    snapshot = calendar_roster_snapshot_state(link)
    if snapshot is not None:
        return snapshot
    if link.context_state != "legacy_linked" or link.calendar_event_snapshot_id is None:
        return None
    participants = (
        await db.scalars(
            select(CalendarParticipant)
            .where(
                CalendarParticipant.workspace_id == workspace_id,
                CalendarParticipant.calendar_event_snapshot_id == link.calendar_event_snapshot_id,
            )
            .order_by(
                CalendarParticipant.participant_kind.asc(),
                CalendarParticipant.display_name.asc(),
            )
        )
    ).all()
    return calendar_roster_state(participants)


def _apply_sort(query: Select[tuple[Meeting]], sort: str) -> Select[tuple[Meeting]]:
    sorters = {
        "updated_desc": nullslast(desc(Meeting.updated_at)),
        "updated_asc": nullslast(asc(Meeting.updated_at)),
        "started_desc": nullslast(desc(Meeting.started_at)),
        "started_asc": nullslast(asc(Meeting.started_at)),
        "duration_desc": desc(Meeting.duration_seconds),
        "duration_asc": asc(Meeting.duration_seconds),
    }
    if sort == "title_asc":
        return query.order_by(desc(Meeting.created_at))
    return query.order_by(
        sorters.get(sort, nullslast(desc(Meeting.started_at))),
        desc(Meeting.created_at),
    )


async def _latest_workflow(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting_id: UUID,
    media_revision_id: UUID | None = None,
) -> ProcessingWorkflow | None:
    query = select(ProcessingWorkflow).where(
        ProcessingWorkflow.workspace_id == workspace_id,
        ProcessingWorkflow.meeting_id == meeting_id,
    )
    query = query.where(
        ProcessingWorkflow.media_revision_id == media_revision_id
        if media_revision_id is not None
        else ProcessingWorkflow.media_revision_id.is_(None)
    )
    return await db.scalar(query.order_by(ProcessingWorkflow.updated_at.desc()))


async def _latest_result(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting_id: UUID,
    media_revision_id: UUID | None = None,
) -> ProcessingResult | None:
    return await db.scalar(
        effective_processing_result_query(
            workspace_id=workspace_id,
            meeting_id=meeting_id,
            media_revision_id=media_revision_id,
        )
    )


async def _latest_media_revision(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting_id: UUID,
    prefer_latest: bool = False,
) -> MediaRevision | None:
    meeting = await db.scalar(
        select(Meeting).where(
            Meeting.workspace_id == workspace_id,
            Meeting.id == meeting_id,
        )
    )
    if not prefer_latest and meeting is not None and await db.scalar(
        select(MeetingSummarySlot.id).where(
            MeetingSummarySlot.workspace_id == workspace_id,
            MeetingSummarySlot.meeting_id == meeting_id,
            MeetingSummarySlot.is_meeting_default.is_(True),
        )
    ) is not None:
        published_outcome = await current_outcome_set(
            db,
            workspace_id=workspace_id,
            meeting_id=meeting_id,
            processing_result_id=None,
        )
        if published_outcome is None or published_outcome.media_revision_id is None:
            return None
        return await db.scalar(
            select(MediaRevision).where(
                MediaRevision.id == published_outcome.media_revision_id,
                MediaRevision.workspace_id == workspace_id,
                MediaRevision.meeting_id == meeting_id,
                MediaRevision.status == MediaRevisionStatus.ACCEPTED.value,
                MediaRevision.immutable.is_(True),
            )
        )
    return await db.scalar(
        select(MediaRevision)
        .where(
            MediaRevision.workspace_id == workspace_id,
            MediaRevision.meeting_id == meeting_id,
            MediaRevision.status == MediaRevisionStatus.ACCEPTED.value,
            MediaRevision.immutable.is_(True),
        )
        .order_by(MediaRevision.revision_number.desc(), MediaRevision.updated_at.desc())
    )


async def _current_outcome_set(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting_id: UUID,
    processing_result_id: UUID | None,
) -> MeetingOutcomeSet | None:
    accepted = await current_outcome_set(
        db,
        workspace_id=workspace_id,
        meeting_id=meeting_id,
        processing_result_id=processing_result_id,
    )
    return accepted


async def latest_processing_result(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting_id: UUID,
    prefer_latest: bool = False,
) -> ProcessingResult | None:
    meeting = await db.scalar(
        select(Meeting).where(
            Meeting.workspace_id == workspace_id,
            Meeting.id == meeting_id,
        )
    )
    if not prefer_latest and meeting is not None and await db.scalar(
        select(MeetingSummarySlot.id).where(
            MeetingSummarySlot.workspace_id == workspace_id,
            MeetingSummarySlot.meeting_id == meeting_id,
            MeetingSummarySlot.is_meeting_default.is_(True),
        )
    ) is not None:
        published_outcome = await current_outcome_set(
            db,
            workspace_id=workspace_id,
            meeting_id=meeting_id,
            processing_result_id=None,
        )
        if published_outcome is not None:
            return await db.scalar(
                select(ProcessingResult).where(
                    ProcessingResult.id == published_outcome.processing_result_id,
                    ProcessingResult.workspace_id == workspace_id,
                    ProcessingResult.meeting_id == meeting_id,
                    ProcessingResult.status == ProcessingResultStatus.IMPORTED.value,
                )
            )
        return None
    media_revision = await _latest_media_revision(
        db,
        workspace_id=workspace_id,
        meeting_id=meeting_id,
        prefer_latest=prefer_latest,
    )
    if media_revision is None:
        return None
    return await _latest_result(
        db,
        workspace_id=workspace_id,
        meeting_id=meeting_id,
        media_revision_id=media_revision.id,
    )
