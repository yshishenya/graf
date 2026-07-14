from __future__ import annotations

from datetime import UTC, timedelta, timezone
from html import escape

from twobrain_rec_server.api.schemas import (
    MeetingListItem,
    MeetingListResponse,
    MeetingReviewResponse,
    NotesActionCategoryState,
    PreviousRecurringMeetingView,
    TranscriptSegmentView,
)
from twobrain_rec_server.cabinet import view_models as cabinet_view_models
from twobrain_rec_server.cabinet.auth_rendering import (
    render_email_code_page as render_email_code_page,
)
from twobrain_rec_server.cabinet.auth_rendering import (
    render_login_page as render_login_page,
)
from twobrain_rec_server.cabinet.auth_rendering import (
    render_signup_page as render_signup_page,
)
from twobrain_rec_server.cabinet.deletion_rendering import (
    render_deletion_feedback_fragment as render_deletion_feedback_fragment,
)
from twobrain_rec_server.cabinet.deletion_rendering import (
    render_deletion_report_fragment as render_deletion_report_fragment,
)
from twobrain_rec_server.cabinet.deletion_rendering import (
    render_deletion_report_page as render_deletion_report_page,
)
from twobrain_rec_server.cabinet.rendering_shared import (
    _base_path,
    _page_shell,
    _settings_path,
    _ui_text,
)
from twobrain_rec_server.cabinet.review_policy_rendering import (
    _render_access_chip,
    _render_access_summary,
    _render_activity,
    _render_artifacts,
    _render_delete_confirmation,
    _render_governance,
    _render_share_panel,
    _render_top_actions,
)
from twobrain_rec_server.cabinet.templates import (
    render_icon,
    render_template,
    trusted_component_html,
)
from twobrain_rec_server.deletion.report import BOUNDED_DELETE_COPY


def render_meeting_list_page(
    response: MeetingListResponse,
    *,
    embedded: bool = False,
    csrf_token: str | None = None,
    poll_url: str | None = None,
) -> str:
    return _page_shell(
        "Мои встречи",
        embedded=embedded,
        csrf_token=csrf_token,
        content_template="cabinet/pages/meeting_list_content.html",
        filter_action=_base_path(embedded),
        list_region=trusted_component_html(
            _render_meeting_list_region(
                response, embedded=embedded, csrf_token=csrf_token, poll_url=poll_url
            ),
            source="meeting_list.region",
        ),
        delete_dialog=trusted_component_html(
            _render_list_delete_dialog(), source="meeting_list.delete_dialog"
        ),
        manual_upload=trusted_component_html(
            _render_manual_upload_fragment(
                embedded=embedded,
                csrf_token=csrf_token,
                list_refresh_url=poll_url or _base_path(embedded),
            ),
            source="meeting_list.manual_upload",
        ),
        sort_label=_sort_label(response.filters.sort),
        query_value=response.filters.q or "",
        status_value=response.filters.status or "",
        access_value=response.filters.access or "",
        sort_value=response.filters.sort,
        filters_active=bool(
            response.filters.q or response.filters.status or response.filters.access
        ),
        active_filter_count=sum(
            value is not None and value != ""
            for value in (response.filters.status, response.filters.access)
        ),
        upcoming_content=trusted_component_html(
            _render_upcoming_recurring(response, embedded=embedded),
            source="meeting_list.upcoming_recurring",
        ),
        visible_total=len(response.items),
    )


def render_settings_page(*, embedded: bool = False, csrf_token: str | None = None) -> str:
    return _page_shell(
        "Настройки",
        embedded=embedded,
        active_nav="settings",
        csrf_token=csrf_token,
        content_template="cabinet/pages/settings_content.html",
        calendar_settings_href=_settings_path(embedded),
    )


def render_meeting_list_fragment(
    response: MeetingListResponse,
    *,
    embedded: bool = False,
    poll_url: str | None = None,
) -> str:
    return _render_meeting_list_region(response, embedded=embedded, poll_url=poll_url)


def render_calendar_settings_page(
    surface: cabinet_view_models.CalendarSettingsSurfaceView,
    *,
    embedded: bool = False,
    csrf_token: str | None = None,
) -> str:
    return _page_shell(
        surface.title,
        embedded=embedded,
        csrf_token=csrf_token,
        content_template="cabinet/fragments/calendar_settings.html",
        active_nav="settings",
        skip_target="calendar-settings-region",
        base_path="/desktop/settings/integrations/calendar"
        if embedded
        else "/settings/integrations/calendar",
        surface=surface,
    )


def render_calendar_settings_fragment(
    surface: cabinet_view_models.CalendarSettingsSurfaceView,
    *,
    embedded: bool = False,
    csrf_token: str | None = None,
) -> str:
    return render_template(
        "cabinet/fragments/calendar_settings.html",
        surface=surface,
        embedded=embedded,
        base_path="/desktop/settings/integrations/calendar"
        if embedded
        else "/settings/integrations/calendar",
        csrf_token=csrf_token,
    )


def calendar_settings_notice_codes(
    *,
    connect_result: str | None = None,
    policy_limited: str | None = None,
    selection_result: str | None = None,
    preferences_result: str | None = None,
    sync_result: str | None = None,
    disconnect_result: str | None = None,
) -> tuple[str, ...]:
    codes: list[str] = []
    result_map = {
        "success": "connect_success",
        "cancelled": "connect_cancelled",
        "denied": "connect_denied",
        "failed": "connect_failed",
        "no_readable_calendars": "no_readable_calendars",
    }
    if connect_result:
        code = result_map.get(connect_result.strip().lower())
        if code:
            codes.append(code)
    if policy_limited:
        normalized = policy_limited.strip().lower()
        if normalized in {"admin_required", "workspace_policy", "tenant_policy"}:
            codes.append("policy_limited")
        elif normalized in {"provider_limited", "unsupported_provider"}:
            codes.append("provider_limited")
    if selection_result:
        normalized_selection = selection_result.strip().lower()
        if normalized_selection == "saved":
            codes.append("selection_saved")
        elif normalized_selection == "empty":
            codes.append("selection_empty")
    if preferences_result and preferences_result.strip().lower() == "saved":
        codes.append("preferences_saved")
    if sync_result:
        normalized_sync = sync_result.strip().lower()
        sync_codes = {
            "accepted": "sync_accepted",
            "already_running": "sync_already_running",
            "reconnect_required": "sync_reconnect_required",
            "unavailable": "sync_unavailable",
            "failed": "sync_failed",
        }
        code = sync_codes.get(normalized_sync)
        if code:
            codes.append(code)
    if disconnect_result:
        normalized_disconnect = disconnect_result.strip().lower()
        disconnect_codes = {
            "success": "disconnect_success",
            "partial": "disconnect_partial",
            "failed": "disconnect_failed",
        }
        code = disconnect_codes.get(normalized_disconnect)
        if code:
            codes.append(code)
    return tuple(codes)


def calendar_connection_result_from_problem(code: str | None) -> str:
    result_map = {
        "unsupported_calendar_provider": "failed",
        "credential_encryption_key_unavailable": "failed",
        "calendar_credential_key_unavailable": "failed",
        "invalid_credentials": "denied",
        "tenant_policy_denied": "denied",
        "provider_timeout": "failed",
        "rate_limited": "failed",
        "no_readable_calendars": "no_readable_calendars",
    }
    return result_map.get(code or "", "failed")


def _render_meeting_list_region(
    response: MeetingListResponse,
    *,
    embedded: bool,
    csrf_token: str | None = None,
    poll_url: str | None = None,
) -> str:
    rows = "\n".join(
        _render_meeting_row(item, embedded=embedded, csrf_token=csrf_token)
        for item in response.items
    )
    if not rows:
        if response.filters.q or response.filters.status or response.filters.access:
            rows = (
                '<div class="empty-state"><strong>Ничего не найдено</strong>'
                "<span>Измените запрос или сбросьте фильтры.</span></div>"
            )
        else:
            rows = (
                '<div class="empty-state"><strong>Пока нет записей</strong>'
                "<span>Начните запись в приложении или загрузите файл кнопкой выше.</span></div>"
            )
    poll_attrs = _meeting_list_poll_attrs(response, poll_url=poll_url, poll_empty=embedded)
    content = f"""
      <section class="list-card cabinet-card" aria-label="Записи встреч" data-meeting-list{poll_attrs}>
        {rows}
      </section>
    """
    return render_template(
        "cabinet/fragments/meeting_list.html",
        content=trusted_component_html(content, source="meeting_list.rows"),
    )


def _render_manual_upload_fragment(
    *,
    embedded: bool,
    csrf_token: str | None,
    list_refresh_url: str,
) -> str:
    base_path = _base_path(embedded)
    return render_template(
        "cabinet/fragments/manual_upload.html",
        embedded=embedded,
        upload_available=bool(csrf_token),
        upload_endpoint="/api/v1/cabinet/media-uploads",
        list_refresh_url=list_refresh_url,
        detail_base_path=base_path,
        login_href=f"/login?next={base_path}",
    )


def _meeting_list_poll_attrs(
    response: MeetingListResponse, *, poll_url: str | None, poll_empty: bool
) -> str:
    if not poll_url:
        return ""
    if not _meeting_list_should_poll(response, poll_empty=poll_empty):
        return ""
    hx_get = escape(poll_url)
    return (
        f' data-upload-progress-poll hx-get="{hx_get}" hx-trigger="every 3s" '
        'hx-target="#meeting-list-region" hx-select="#meeting-list-region" hx-swap="outerHTML"'
    )


def _meeting_list_should_poll(response: MeetingListResponse, *, poll_empty: bool) -> bool:
    if not response.items:
        return poll_empty
    return any(
        (item.upload is not None and item.upload.is_active)
        or item.status in {"uploading", "processing"}
        or item.playback.state == "preparing"
        for item in response.items
    )


def render_meeting_detail_page(
    review: MeetingReviewResponse,
    *,
    embedded: bool = False,
    csrf_token: str | None = None,
    poll_url: str | None = None,
) -> str:
    content = _render_meeting_detail_content(
        review,
        embedded=embedded,
        csrf_token=csrf_token,
        poll_url=poll_url,
    )
    return _page_shell(
        review.meeting.title,
        content,
        embedded=embedded,
        csrf_token=csrf_token,
        content_source="meeting_detail.content",
    )


def render_meeting_detail_fragment(
    review: MeetingReviewResponse,
    *,
    embedded: bool = False,
    csrf_token: str | None = None,
    focus_calendar_context: bool = False,
    poll_url: str | None = None,
) -> str:
    return render_template(
        "cabinet/fragments/meeting_detail.html",
        content=trusted_component_html(
            _render_meeting_detail_content(
                review,
                embedded=embedded,
                csrf_token=csrf_token,
                focus_calendar_context=focus_calendar_context,
                poll_url=poll_url,
            ),
            source="meeting_detail.content",
        ),
    )


def _render_meeting_detail_content(
    review: MeetingReviewResponse,
    *,
    embedded: bool,
    csrf_token: str | None = None,
    focus_calendar_context: bool = False,
    poll_url: str | None = None,
) -> str:
    transcript = trusted_component_html(
        _render_transcript(review.transcript.segments), source="meeting_detail.transcript"
    )
    if not review.transcript.available:
        transcript = trusted_component_html(
            f"""
            <div class="empty-state">
              <div>
                <strong>{escape(_empty_title(review))}</strong>
                <div class="muted">{escape(_empty_body(review))}</div>
              </div>
            </div>
            """,
            source="meeting_detail.empty_transcript",
        )
    recording_tab = "Расшифровка" if embedded else "Запись и расшифровка"
    return render_template(
        "cabinet/pages/meeting_detail_content.html",
        base_path=_base_path(embedded),
        meeting_title=review.meeting.title,
        status_label=_ui_text(review.meeting.status_label),
        media_revision_id=str(review.provenance.media_revision_id or ""),
        local_media_revision_id=review.provenance.local_media_revision_id or "",
        playback_poll_url=poll_url or "",
        playback_poll_active="true" if review.playback.state == "preparing" else "false",
        playback_live_label=review.playback.label,
        recording_tab=recording_tab,
        access_chip=trusted_component_html(
            _render_access_chip(review.meeting.access), source="meeting_detail.access_chip"
        ),
        top_actions=trusted_component_html(
            _render_top_actions(review, embedded=embedded), source="meeting_detail.top_actions"
        ),
        outcomes=trusted_component_html(
            _render_notes_outcomes(review), source="meeting_detail.outcomes"
        ),
        transcript=transcript,
        calendar_context_chooser=trusted_component_html(
            _render_calendar_context_chooser(
                review,
                embedded=embedded,
                csrf_token=csrf_token,
            ),
            source="meeting_detail.calendar_context_chooser",
        ),
        revision_status=trusted_component_html(
            _render_revision_status(review), source="meeting_detail.revision_status"
        ),
        calendar_context=trusted_component_html(
            _render_calendar_context(
                review,
                embedded=embedded,
                csrf_token=csrf_token,
                focus_heading=focus_calendar_context,
            ),
            source="meeting_detail.calendar_context",
        ),
        access_summary=trusted_component_html(
            _render_access_summary(review), source="meeting_detail.access_summary"
        ),
        share_panel=trusted_component_html(
            _render_share_panel(review), source="meeting_detail.share_panel"
        ),
        artifacts=trusted_component_html(
            _render_artifacts(review), source="meeting_detail.artifacts"
        ),
        deletion_truth_copy=review.deletion_truth_copy or "",
        deletion_truth_text=_ui_text(review.deletion_truth_copy or ""),
        delete_confirmation=trusted_component_html(
            _render_delete_confirmation(review, embedded=embedded),
            source="meeting_detail.delete_confirmation",
        ),
        speaker_lanes=trusted_component_html(
            _render_speaker_lanes(review), source="meeting_detail.speaker_lanes"
        ),
        governance=trusted_component_html(
            _render_governance(review), source="meeting_detail.governance"
        ),
        activity=trusted_component_html(_render_activity(review), source="meeting_detail.activity"),
        assistant_label=_ui_text(review.assistant.label),
        template_label=_ui_text(review.template.label),
        playback=trusted_component_html(_render_playback(review), source="meeting_detail.playback"),
    )


def _speaker_display_label(label: str) -> str:
    if label.startswith("SPEAKER_") and label.removeprefix("SPEAKER_").isdigit():
        return label
    if label.startswith("Speaker "):
        suffix = label.removeprefix("Speaker ").strip()
        return f"Спикер {suffix}" if suffix else "Спикер"
    return _ui_text(label)


def _notes_source_label(source_basis: str) -> str:
    return {
        "blocked": "заблокировано",
        "not_supported": "не поддерживается",
        "policy_deferral": "отложено политикой",
        "processing_status": "статус обработки",
        "stored_output": "сохраненные итоги",
    }.get(source_basis, _ui_text(source_basis))


def _notes_title(title: str) -> str:
    return {
        "Summary": "Кратко",
        "Key points": "Ключевое",
        "Decisions": "Решения",
        "Action Items": "Действия",
        "Follow-ups": "Продолжение",
        "Risks": "Риски",
        "Questions": "Вопросы",
        "Evidence": "Фрагменты",
    }.get(title, _ui_text(title))


def _ui_icon(name: str) -> str:
    return render_icon(name)


def _render_meeting_row(
    item: MeetingListItem,
    *,
    embedded: bool,
    selected: bool = False,
    csrf_token: str | None = None,
) -> str:
    meeting_path = f"{_base_path(embedded)}/{item.meeting_id}"
    needs_context_choice = bool(item.calendar_context and item.calendar_context.needs_owner_action)
    href = f"{meeting_path}#calendar-context-chooser" if needs_context_choice else meeting_path
    delete_action = f"{meeting_path}/deletion-requests"
    selected_class = " is-selected" if selected else ""
    source_icon, source_label = _meeting_media_icon(item)
    title = escape(item.title)
    row_meta = _render_meeting_row_meta(item)
    csrf_field = (
        f'<input type="hidden" name="csrf_token" value="{escape(csrf_token)}">'
        if csrf_token
        else ""
    )
    return f"""
      <article class="meeting-row cabinet-row{selected_class}" tabindex="0" aria-label="Встреча {title}" data-meeting-row data-meeting-id="{item.meeting_id}" data-meeting-title="{title}">
        <span class="row-select-hit"><input class="row-check" type="checkbox" tabindex="-1" aria-hidden="true" data-row-contextual data-meeting-select aria-label="Выбрать запись {title}"></span>
        <span class="row-icon" data-media-kind="{source_label}" aria-hidden="true">{source_icon}</span>
        <a class="meeting-title" href="{href}" aria-label="Открыть встречу {title}">
          <span class="row-title">{title} <span class="muted">{_duration(item.duration_seconds)}</span></span>
          <span class="row-meta">{row_meta}</span>
        </a>
        <form class="row-delete-form" method="post" action="{delete_action}" data-row-delete-form
          data-hx-post="{delete_action}"
          data-hx-target="#delete-feedback-region"
          data-hx-select="[data-cabinet-fragment='deletion-feedback']"
          data-hx-swap="innerHTML">
          {csrf_field}
          <input type="hidden" name="confirmation_boundary" value="{escape(BOUNDED_DELETE_COPY)}">
          <button class="row-delete icon-button" type="button" tabindex="-1" aria-hidden="true" data-row-contextual data-row-delete aria-label="Удалить запись {title}" title="Удалить">{_ui_icon("trash")}</button>
          <noscript><button class="row-delete-noscript" type="submit">Удалить</button></noscript>
        </form>
        <span class="meeting-date">{_date_label(item)}</span>
      </article>
    """


def _render_meeting_row_meta(item: MeetingListItem) -> str:
    calendar_context = _render_list_calendar_context(item)
    playback = _render_list_playback_state(item)
    if item.upload is None:
        return f"<span>{escape(_ui_text(item.status_label))}</span>{playback}{calendar_context}"
    label = escape(item.upload.label)
    if not item.upload.is_active or item.upload.progress_percent is None:
        return f'<span class="upload-progress-label">{label}</span>{playback}{calendar_context}'
    percent = max(0, min(100, item.upload.progress_percent))
    active_attr = " data-upload-progress-active" if item.upload.is_active else ""
    return f"""
      <span class="upload-progress-label"{active_attr}>{label} {percent}%</span>
      <span class="upload-progress-meter" role="progressbar" aria-label="Прогресс отправки записи" aria-valuemin="0" aria-valuemax="100" aria-valuenow="{percent}">
        <span class="upload-progress-meter__bar" style="width: {percent}%"></span>
      </span>
      {playback}
      {calendar_context}
    """


def _render_list_playback_state(item: MeetingListItem) -> str:
    state = item.playback.state
    compact_label = {
        "preparing": "Аудио готовится",
        "available": "Аудио готово",
        "unavailable": "Аудио недоступно",
        "deleting": "Аудио удаляется",
        "deleted": "Аудио удалено",
    }[state]
    return (
        f'<span class="playback-state-token is-{escape(state)}" '
        f'data-playback-state="{escape(state)}" '
        f'data-playback-reason="{escape(item.playback.reason_code)}" '
        f'aria-label="Статус аудио: {escape(item.playback.label)}">'
        f"{escape(compact_label)}</span>"
    )


def _render_upcoming_recurring(response: MeetingListResponse, *, embedded: bool) -> str:
    generated_at = (
        response.generated_at
        if response.generated_at.tzinfo is not None
        else response.generated_at.replace(tzinfo=UTC)
    )
    rows: list[str] = []
    for item in response.items:
        started_at = item.started_at
        previous = item.previous_recurring_meeting
        if started_at is None or previous is None:
            continue
        normalized_start = (
            started_at if started_at.tzinfo is not None else started_at.replace(tzinfo=UTC)
        )
        if normalized_start.astimezone(UTC) <= generated_at.astimezone(UTC):
            continue
        rows.append(
            f"""
              <div class="calendar-upcoming-recurring">
                <strong>{escape(item.title)}</strong>
                {
                _render_previous_recurring_pointer(
                    previous,
                    embedded=embedded,
                    timezone_offset_minutes=item.recording_display_timezone_offset_minutes,
                    show_title=True,
                )
            }
              </div>
            """
        )
    if rows:
        return f'<div class="calendar-upcoming-list">{"".join(rows)}</div>'
    return ""


def _render_previous_recurring_pointer(
    previous: PreviousRecurringMeetingView,
    *,
    embedded: bool,
    timezone_offset_minutes: int | None,
    show_title: bool = False,
) -> str:
    date = cabinet_view_models.short_date_label(
        previous.started_at,
        timezone_offset_minutes=timezone_offset_minutes,
    )
    readiness = {
        "notes_ready": "Итоги готовы",
        "transcript_ready": "Транскрипт готов",
        "processing": "Обрабатывается",
        "unavailable": "",
    }[previous.readiness_state]
    href = f"{_base_path(embedded)}/{previous.meeting_id}"
    if show_title:
        title = (
            f'<span class="muted calendar-recurring-title">{escape(previous.safe_title)}</span>'
            if previous.safe_title
            else ""
        )
        readiness_copy = (
            f'<span class="muted calendar-recurring-readiness">{escape(readiness)}</span>'
            if readiness
            else ""
        )
        aria_label = f"Открыть запись серии за {date}"
    else:
        title = ""
        readiness_copy = ""
        aria_label = ", ".join(
            value for value in (previous.safe_title or "Запись серии", date, readiness) if value
        )
    return f"""
      <div class="calendar-recurring-pointer" data-previous-recurring-meeting>
        <div class="section-title">В серии</div>
        {title}
        <a class="mini-link" href="{href}" aria-label="{escape(aria_label)}">Предыдущая встреча · {date}</a>
        {readiness_copy}
      </div>
    """


def _render_list_calendar_context(item: MeetingListItem) -> str:
    context = item.calendar_context
    if context is None:
        return ""
    label = (
        f'<span class="calendar-context-label" '
        f'data-calendar-context-state="{escape(context.state)}">'
        f"{escape(context.label)}</span>"
    )
    if not context.needs_owner_action:
        return label
    return f'{label}<span class="mini-link calendar-context-list-action">Выбрать</span>'


def _render_calendar_context_chooser(
    review: MeetingReviewResponse,
    *,
    embedded: bool,
    csrf_token: str | None,
) -> str:
    context = review.calendar_context
    if context is None:
        return ""
    detail = review.calendar_context_detail
    candidates = list(
        detail.candidates if detail is not None else getattr(context, "candidates", [])
    )
    can_change = (
        detail.can_change if detail is not None else bool(getattr(context, "can_change", False))
    )
    if not can_change or not candidates:
        return ""
    is_ambiguity = context.state == "ambiguous"
    mode = "ambiguity" if is_ambiguity else "correction"
    reason = "ambiguity_resolution" if is_ambiguity else "correction"
    helper_copy = (
        "Несколько встреч подходят по времени. GRAF ничего не выбрал."
        if is_ambiguity
        else "Выберите правильную встречу. Текущий контекст изменится только после сохранения."
    )
    chip_copy = "Нужен выбор" if is_ambiguity else "Изменение"
    meeting_path = f"{_base_path(embedded)}/{review.meeting.meeting_id}"
    choose_action = f"{meeting_path}/calendar-context/choose"
    continue_action = f"{meeting_path}/calendar-context/continue-without"
    csrf_field = _calendar_context_csrf_field(csrf_token)
    timezone_offset = review.meeting.recording_display_timezone_offset_minutes or 0
    choices: list[str] = []
    for candidate in candidates:
        title = candidate.safe_title or "Встреча без названия"
        starts_at = _calendar_context_time(candidate.starts_at, timezone_offset)
        ends_at = _calendar_context_time(candidate.ends_at, timezone_offset)
        choices.append(
            f"""
              <label class="calendar-context-choice">
                <input type="radio" name="event_id" value="{candidate.event_id}" required>
                <span class="calendar-context-choice__body">
                  <strong>{escape(title)}</strong>
                  <span class="muted">{escape(candidate.safe_source_label)} · {starts_at}–{ends_at}</span>
                </span>
              </label>
            """
        )
    continue_without = (
        f"""
        <form method="post" action="{continue_action}"
          data-hx-post="{continue_action}" data-hx-target="#cabinet-main"
          data-hx-select="#cabinet-main" data-hx-swap="outerHTML">
          {csrf_field}
          <button type="submit" class="secondary">Продолжить без календаря</button>
        </form>
        """
        if is_ambiguity
        else ""
    )
    return f"""
      <section class="panel calendar-context-chooser" id="calendar-context-chooser"
        data-calendar-context-chooser data-calendar-context-mode="{mode}"
        aria-labelledby="calendar-context-chooser-heading" tabindex="-1" autofocus>
        <div class="panel-head">
          <h2 id="calendar-context-chooser-heading">Календарный контекст</h2>
          <span class="chip warning">{chip_copy}</span>
        </div>
        <p class="truth-copy" id="calendar-context-choice-help">{helper_copy}</p>
        <form method="post" action="{choose_action}"
          data-hx-post="{choose_action}" data-hx-target="#cabinet-main"
          data-hx-select="#cabinet-main" data-hx-swap="outerHTML">
          {csrf_field}
          <input type="hidden" name="context_reason" value="{reason}">
          <fieldset aria-describedby="calendar-context-choice-help">
            <legend>Выберите встречу</legend>
            <div class="calendar-context-choices">{"".join(choices)}</div>
          </fieldset>
          <div class="row-actions">
            <button type="submit">Сохранить выбор</button>
          </div>
        </form>
        {continue_without}
        <div id="calendar-context-result" class="truth-copy" aria-live="polite"></div>
      </section>
    """


def _render_calendar_context(
    review: MeetingReviewResponse,
    *,
    embedded: bool,
    csrf_token: str | None,
    focus_heading: bool = False,
) -> str:
    context = review.calendar_context
    if context is None:
        return ""
    roster = review.calendar_roster
    roster_rows = ""
    roster_heading = ""
    roster_copy = ""
    if roster is not None and roster.available:
        roster_heading = (
            f'<div class="section-title">Участники из календаря · {roster.participant_count}</div>'
        )
        roster_rows = "".join(
            f'<div class="state-row"><span>{escape(participant.display_name or "Участник")}</span>'
            f'<span class="muted">{escape(_calendar_participant_label(participant.participant_kind))}</span></div>'
            for participant in roster.participants
        )
        roster_copy = "Приглашённые участники, не подтверждённые спикеры"
    elif context.state in {"matched_auto", "matched_user"}:
        roster_copy = "Список участников недоступен. Спикеры определяются отдельно по записи."
    elif context.reason_label is not None:
        roster_copy = context.reason_label
    chip_state = "ready" if context.state in {"matched_auto", "matched_user"} else "disabled"
    chip_label = (
        "Автоматически"
        if context.state == "matched_auto"
        else "Выбрано"
        if context.state == "matched_user"
        else "Без контекста"
    )
    detail = review.calendar_context_detail
    matched_event = ""
    if detail is not None and context.state in {"matched_auto", "matched_user", "legacy_linked"}:
        title = detail.matched_title or "Событие календаря"
        event_time = ""
        if detail.matched_event_starts_at is not None and detail.matched_event_ends_at is not None:
            starts_at = _calendar_context_time(
                detail.matched_event_starts_at,
                review.meeting.recording_display_timezone_offset_minutes or 0,
            )
            ends_at = _calendar_context_time(
                detail.matched_event_ends_at,
                review.meeting.recording_display_timezone_offset_minutes or 0,
            )
            event_time = f'<span class="muted">{starts_at}–{ends_at}</span>'
        if detail.matched_title is not None or event_time:
            matched_event = (
                '<div class="state-row calendar-context-event">'
                f"<strong>{escape(title)}</strong>{event_time}</div>"
            )
    previous_recurring = (
        _render_previous_recurring_pointer(
            detail.previous_recurring_meeting,
            embedded=embedded,
            timezone_offset_minutes=review.meeting.recording_display_timezone_offset_minutes,
        )
        if detail is not None and detail.previous_recurring_meeting is not None
        else ""
    )
    clear_action = f"{_base_path(embedded)}/{review.meeting.meeting_id}/calendar-context/clear"
    change_href = (
        f"{_base_path(embedded)}/{review.meeting.meeting_id}"
        "?calendar_context_action=change#calendar-context-chooser"
    )
    change_action = ""
    if detail is not None and detail.can_change and context.state != "ambiguous":
        change_action = f'<a class="button quiet" href="{change_href}">Изменить</a>'
    clear_confirmation = ""
    if (
        context.state in {"matched_auto", "matched_user", "legacy_linked"}
        and detail is not None
        and detail.can_clear
    ):
        clear_confirmation = f"""
          <form class="calendar-context-clear" method="post" action="{clear_action}"
            data-hx-post="{clear_action}" data-hx-target="#cabinet-main"
            data-hx-select="#cabinet-main" data-hx-swap="outerHTML">
            {_calendar_context_csrf_field(csrf_token)}
            <p class="truth-copy">Контекст и список приглашённых исчезнут. Название записи останется прежним.</p>
            <button type="submit" class="secondary">Убрать контекст</button>
          </form>
        """
    heading_focus = ' tabindex="-1" autofocus' if focus_heading else ""
    return f"""
      <section class="calendar-context" aria-labelledby="calendar-context-heading" data-calendar-context-state="{escape(context.state)}">
        <h3 id="calendar-context-heading"{heading_focus}>Контекст встречи</h3>
        <div class="state-row">
          <strong>{escape(context.label)}</strong>
          <span class="chip {chip_state}">{escape(chip_label)}</span>
        </div>
        {matched_event}
        {roster_heading}
        <div class="truth-copy">{escape(roster_copy)}</div>
        <div class="state-list">{roster_rows}</div>
        {previous_recurring}
        {change_action}
        {clear_confirmation}
      </section>
    """


def _calendar_context_time(value, timezone_offset_minutes: int) -> str:
    display_timezone = timezone(timedelta(minutes=timezone_offset_minutes))
    localized = value.replace(tzinfo=UTC) if value.tzinfo is None else value
    return localized.astimezone(display_timezone).strftime("%H:%M")


def _calendar_context_csrf_field(csrf_token: str | None) -> str:
    if not csrf_token:
        return ""
    return f'<input type="hidden" name="csrf_token" value="{escape(csrf_token)}">'


def _calendar_participant_label(kind: str) -> str:
    return {
        "organizer": "Организатор",
        "required_attendee": "Участник",
        "optional_attendee": "Необязательный участник",
        "resource": "Ресурс",
        "room": "Комната",
        "group": "Группа",
    }.get(kind, "Участник")


def _meeting_media_icon(item: MeetingListItem) -> tuple[str, str]:
    kind = cabinet_view_models.meeting_media_kind(item)
    return _ui_icon(kind), cabinet_view_models.meeting_media_label(item)


def _render_list_delete_dialog() -> str:
    bounded_copy = "Запись будет удалена везде, где ее контролирует GRAF. Уже скачанные или экспортированные копии могут оставаться вне контроля GRAF."
    return f"""
      <dialog class="delete-dialog" data-delete-dialog data-title-one="Удалить запись?" data-title-many="Удалить записи?">
        <h2 data-delete-title>Удалить запись?</h2>
        <p><span data-delete-count>Вы удаляете 1 запись.</span> Это действие нельзя отменить.</p>
        <p class="truth-copy" data-bounded-delete-copy="{escape(BOUNDED_DELETE_COPY)}">{escape(bounded_copy)}</p>
        <div class="dialog-actions">
          <button type="button" class="quiet" data-delete-cancel>Отмена</button>
          <button type="button" class="danger-button" data-delete-confirm>Удалить</button>
        </div>
        <div class="dialog-error" role="status" aria-live="polite" data-delete-error hidden>Не удалось удалить запись. Попробуйте ещё раз.</div>
      </dialog>
    """


def _render_transcript(segments: list[TranscriptSegmentView]) -> str:
    return "\n".join(
        f"""
          <article class="segment">
            {_render_timestamp(segment)}
            <div class="speaker"><span class="dot"></span>{escape(_speaker_display_label(segment.speaker_label))}</div>
            <div class="text">{escape(segment.text)}</div>
          </article>
        """
        for segment in segments
    )


def _render_timestamp(segment: TranscriptSegmentView) -> str:
    if segment.seekable and segment.seek_seconds is not None:
        return (
            f'<button class="timestamp timestamp-seek" type="button" '
            f'data-seek-seconds="{escape(str(segment.seek_seconds))}">{escape(segment.timestamp_label)}</button>'
        )
    return f'<div class="timestamp">{escape(segment.timestamp_label)}</div>'


def _render_playback(review: MeetingReviewResponse) -> str:
    if review.playback.can_play and review.playback.playback_path:
        speed_options = ",".join(f"{speed:g}" for speed in review.playback.speed_options)
        return f"""
          <section class="playback-bar detail-playback" data-playback-shell data-playback-state="available" data-playback-reason="{escape(review.playback.reason_code)}" data-source-mode="{escape(review.playback.source_mode)}" aria-describedby="playback-live-status">
            <audio class="playback-audio" data-playback-player preload="metadata" src="{escape(review.playback.playback_path)}"></audio>
            <div class="playback-controls" aria-label="Управление воспроизведением">
              <button type="button" class="playback-round" data-playback-skip="-15" aria-label="Назад на 15 секунд">15</button>
              <button type="button" class="playback-round primary-play" data-playback-toggle aria-label="Воспроизвести">▶</button>
              <button type="button" class="playback-round" data-playback-skip="15" aria-label="Вперед на 15 секунд">15</button>
              <button type="button" class="playback-speed" data-playback-speed-toggle data-speed-options="{escape(speed_options)}">1x</button>
            </div>
            <p class="playback-error" data-playback-error role="status" aria-live="polite" hidden>Воспроизведение временно недоступно.</p>
            <div class="playback-progress-row">
              <span class="playback-time" data-playback-current>00:00</span>
              <input class="playback-progress" data-playback-progress type="range" min="0" max="{review.playback.duration_seconds}" step="0.1" value="0" aria-label="Позиция записи">
              <span class="playback-time" data-playback-duration>{_timecode(review.playback.duration_seconds)}</span>
            </div>
            {_render_playback_speaker_timeline(review)}
          </section>
        """
    focus_attribute = (
        ""
        if review.playback.state == "preparing"
        else ' role="status" tabindex="0" aria-live="off"'
    )
    state_classes = "is-unavailable"
    if review.playback.state != "unavailable":
        state_classes += f" is-{escape(review.playback.state)}"
    return f"""
      <section class="playback-bar detail-playback {state_classes}" data-playback-state="{escape(review.playback.state)}" data-playback-reason="{escape(review.playback.reason_code)}" data-source-mode="{escape(review.playback.source_mode)}" aria-describedby="playback-live-status"{focus_attribute}>
        <span>{escape(review.playback.label)}</span>
        <span>{_duration(review.playback.duration_seconds)}</span>
      </section>
    """


def _render_playback_speaker_timeline(review: MeetingReviewResponse) -> str:
    if not review.speakers.available:
        return '<div class="speaker-timeline" data-speaker-timeline></div>'
    duration = max(1, review.playback.duration_seconds)
    lanes = []
    for speaker in review.speakers.speakers:
        speaker_label = _speaker_display_label(speaker.label)
        segments = []
        for segment in speaker.segments:
            start = max(0.0, float(segment.start_seconds))
            end = min(float(duration), max(start, float(segment.end_seconds)))
            left = min(100.0, max(0.0, start / duration * 100))
            width = min(100.0 - left, max(0.2, (end - start) / duration * 100))
            segment_label = f"{speaker_label} {_timecode(int(start))}-{_timecode(int(end))}"
            segments.append(
                f'<span class="timeline-segment" data-lane-segment title="{escape(segment_label)}" '
                f'aria-label="{escape(segment_label)}" style="left:{left:.2f}%;width:{width:.2f}%"></span>'
            )
        lanes.append(
            f"""
            <div class="timeline-lane" data-speaker-lane="{escape(speaker.speaker_key)}">
              <span class="timeline-label">{escape(speaker_label)}</span>
              <span class="timeline-track">{"".join(segments)}</span>
              <span class="timeline-share">{speaker.talk_time_percent}%</span>
            </div>
            """
        )
    return f'<div class="speaker-timeline" data-speaker-timeline>{"".join(lanes)}</div>'


def _render_speaker_lanes(review: MeetingReviewResponse) -> str:
    if not review.speakers.available:
        return f'<div class="muted">{escape(_ui_text("Speaker lanes are reserved until diarization is available."))}</div>'
    return "\n".join(
        f"""
        <div class="speaker-lane">
          <div class="row-meta"><strong>{escape(_speaker_display_label(speaker.label))}</strong><span>{speaker.talk_time_percent}%</span></div>
          <div class="lane-track"><div class="lane-fill" style="width:{speaker.talk_time_percent}%"></div></div>
        </div>
        """
        for speaker in review.speakers.speakers
    )


def _render_revision_status(review: MeetingReviewResponse) -> str:
    media_revision_id = escape(str(review.provenance.media_revision_id or ""))
    local_media_revision_id = escape(review.provenance.local_media_revision_id or "")
    label = escape(_ui_text(review.meeting.status_label))
    reason = escape(
        _ui_text(review.processing.reason_label or review.processing.reason_code)
        or "Текущая медиа-ревизия"
    )
    return f"""
      <section class="revision-status" aria-label="Статус медиа-ревизии" data-media-revision-id="{media_revision_id}" data-local-media-revision-id="{local_media_revision_id}">
        <span class="chip {escape(review.meeting.status)}">{label}</span>
        <span class="row-meta"><span>Медиа-ревизия</span><span>{reason}</span></span>
      </section>
    """


def _render_notes_outcomes(review: MeetingReviewResponse) -> str:
    outcomes = [
        ("summary", "Summary", review.notes_action_truth.summary),
        ("key_points", "Key points", review.notes_action_truth.key_points),
        ("decisions", "Decisions", review.notes_action_truth.decisions),
        ("action_items", "Action Items", review.notes_action_truth.action_items),
        ("followups", "Follow-ups", review.notes_action_truth.followups),
        ("risks", "Risks", review.notes_action_truth.risks),
        ("questions", "Questions", review.notes_action_truth.questions),
        ("evidence", "Evidence", review.notes_action_truth.evidence),
    ]
    rows = "".join(
        _render_notes_outcome_row(category, title, state) for category, title, state in outcomes
    )
    source = escape(_notes_source_label(review.notes_action_truth.source_basis))
    source_basis = escape(review.notes_action_truth.source_basis)
    return f"""
      <div class="notes" data-outcome-source-basis="{source_basis}">
        <h3>{escape(_ui_text("Итоги встречи"))}</h3>
        <div class="state-list notes-outcomes">
          {rows}
        </div>
        <div class="muted">{escape(_ui_text("Outcome source"))}: {source}</div>
      </div>
    """


def _render_notes_outcome_row(category: str, title: str, state: NotesActionCategoryState) -> str:
    state_name = escape(state.state)
    items = "".join(_render_outcome_item(item) for item in state.items)
    return f"""
      <div class="state-row notes-outcome-row" data-outcome-category="{escape(category)}" data-outcome-state="{state_name}">
        <span><strong>{escape(_notes_title(title))}</strong><br><span class="muted">{escape(_ui_text(state.reason))}</span></span>
        <span class="chip {state_name}">{escape(_ui_text(state.label))}</span>
        {items}
      </div>
    """


def _render_outcome_item(item) -> str:
    text = escape(item.text or "")
    if not text:
        return ""
    refs = ", ".join(
        _timecode(int(ref.start_seconds or 0))
        for ref in item.source_refs[:2]
        if ref.start_seconds is not None
    )
    refs_html = f'<span class="muted">Источник: {escape(refs)}</span>' if refs else ""
    return f'<div class="outcome-item"><span>{text}</span>{refs_html}</div>'


def _empty_title(review: MeetingReviewResponse) -> str:
    if review.processing.state in {"processing", "submitted"}:
        return "Транскрипт готовится"
    if review.processing.state == "failed":
        return "Обработка остановилась"
    if review.processing.state == "blocked":
        return "Обработка требует проверки"
    return "Транскрипт недоступен"


def _empty_body(review: MeetingReviewResponse) -> str:
    if review.processing.reason_label:
        return _ui_text(review.processing.reason_label)
    if review.processing.state in {"processing", "submitted"}:
        return "Мы показываем только подтвержденные данные и не создаем фальшивый текст."
    return "Проверьте статус обработки позже."


def _timecode(seconds: int) -> str:
    minutes, second = divmod(max(0, seconds), 60)
    return f"{minutes:02d}:{second:02d}"


def _duration(seconds: int) -> str:
    return cabinet_view_models.format_duration(seconds)


def _date_label(item: MeetingListItem) -> str:
    return cabinet_view_models.date_label(item)


def _sort_label(sort: str) -> str:
    return cabinet_view_models.sort_label(sort)
