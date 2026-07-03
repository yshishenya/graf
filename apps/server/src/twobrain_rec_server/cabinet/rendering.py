from __future__ import annotations

from html import escape

from twobrain_rec_server.api.schemas import (
    ArtifactEgressState,
    MeetingListItem,
    MeetingListResponse,
    MeetingReviewResponse,
    NotesActionCategoryState,
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
) -> str:
    return _page_shell(
        "Мои встречи",
        embedded=embedded,
        csrf_token=csrf_token,
        content_template="cabinet/pages/meeting_list_content.html",
        filter_action=_base_path(embedded),
        list_region=trusted_component_html(
            _render_meeting_list_region(response, embedded=embedded, csrf_token=csrf_token),
            source="meeting_list.region",
        ),
        delete_dialog=trusted_component_html(_render_list_delete_dialog(), source="meeting_list.delete_dialog"),
        sort_label=_sort_label(response.filters.sort),
        query_value=response.filters.q or "",
        status_value=response.filters.status or "",
        access_value=response.filters.access or "",
        sort_value=response.filters.sort,
        calendar_settings_href=_settings_path(embedded),
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


def render_meeting_list_fragment(response: MeetingListResponse, *, embedded: bool = False) -> str:
    return _render_meeting_list_region(response, embedded=embedded)


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
        base_path="/desktop/settings/integrations/calendar" if embedded else "/settings/integrations/calendar",
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
        base_path="/desktop/settings/integrations/calendar" if embedded else "/settings/integrations/calendar",
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
) -> str:
    rows = "\n".join(
        _render_meeting_row(item, embedded=embedded, csrf_token=csrf_token)
        for item in response.items
    )
    if not rows:
        rows = '<div class="empty-state">Нет встреч для выбранного фильтра.</div>'
    content = f"""
      <section class="list-card cabinet-card" aria-label="Записи встреч" data-meeting-list>
        {rows}
      </section>
    """
    return render_template(
        "cabinet/fragments/meeting_list.html",
        content=trusted_component_html(content, source="meeting_list.rows"),
    )


def render_meeting_detail_page(
    review: MeetingReviewResponse,
    *,
    embedded: bool = False,
    csrf_token: str | None = None,
) -> str:
    content = _render_meeting_detail_content(review, embedded=embedded)
    return _page_shell(
        review.meeting.title,
        content,
        embedded=embedded,
        csrf_token=csrf_token,
        content_source="meeting_detail.content",
    )


def render_meeting_detail_fragment(review: MeetingReviewResponse, *, embedded: bool = False) -> str:
    return render_template(
        "cabinet/fragments/meeting_detail.html",
        content=trusted_component_html(
            _render_meeting_detail_content(review, embedded=embedded),
            source="meeting_detail.content",
        ),
    )


def _render_meeting_detail_content(review: MeetingReviewResponse, *, embedded: bool) -> str:
    transcript = trusted_component_html(_render_transcript(review.transcript.segments), source="meeting_detail.transcript")
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
        recording_tab=recording_tab,
        access_chip=trusted_component_html(_render_access_chip(review.meeting.access), source="meeting_detail.access_chip"),
        top_actions=trusted_component_html(_render_top_actions(review, embedded=embedded), source="meeting_detail.top_actions"),
        outcomes=trusted_component_html(_render_notes_outcomes(review), source="meeting_detail.outcomes"),
        transcript=transcript,
        revision_status=trusted_component_html(_render_revision_status(review), source="meeting_detail.revision_status"),
        access_summary=trusted_component_html(_render_access_summary(review), source="meeting_detail.access_summary"),
        share_panel=trusted_component_html(_render_share_panel(review), source="meeting_detail.share_panel"),
        artifacts=trusted_component_html(_render_artifacts(review), source="meeting_detail.artifacts"),
        deletion_truth_copy=review.deletion_truth_copy or "",
        deletion_truth_text=_ui_text(review.deletion_truth_copy or ""),
        delete_confirmation=trusted_component_html(
            _render_delete_confirmation(review, embedded=embedded),
            source="meeting_detail.delete_confirmation",
        ),
        speaker_lanes=trusted_component_html(_render_speaker_lanes(review), source="meeting_detail.speaker_lanes"),
        governance=trusted_component_html(_render_governance(review), source="meeting_detail.governance"),
        activity=trusted_component_html(_render_activity(review), source="meeting_detail.activity"),
        assistant_label=_ui_text(review.assistant.label),
        template_label=_ui_text(review.template.label),
        playback=trusted_component_html(_render_playback(review), source="meeting_detail.playback"),
    )


def _speaker_display_label(label: str) -> str:
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
    href = f"{_base_path(embedded)}/{item.meeting_id}"
    delete_action = f"{href}/deletion-requests"
    selected_class = " is-selected" if selected else ""
    source_icon, source_label = _meeting_media_icon(item)
    title = escape(item.title)
    csrf_field = f'<input type="hidden" name="csrf_token" value="{escape(csrf_token)}">' if csrf_token else ""
    return f"""
      <article class="meeting-row cabinet-row{selected_class}" data-meeting-row data-meeting-id="{item.meeting_id}" data-meeting-title="{title}">
        <input class="row-check" type="checkbox" data-meeting-select aria-label="Выбрать запись {title}">
        <span class="row-icon" data-media-kind="{source_label}" aria-label="{source_label}" title="{source_label}">{source_icon}</span>
        <a class="meeting-title" href="{href}">
          <span class="row-title">{title} <span class="muted">{_duration(item.duration_seconds)}</span></span>
          <span class="row-meta"><span>{escape(_ui_text(item.status_label))}</span></span>
        </a>
        <form class="row-delete-form" method="post" action="{delete_action}" data-row-delete-form
          data-hx-post="{delete_action}"
          data-hx-target="#delete-feedback-region"
          data-hx-select="[data-cabinet-fragment='deletion-feedback']"
          data-hx-swap="innerHTML">
          {csrf_field}
          <input type="hidden" name="confirmation_boundary" value="{escape(BOUNDED_DELETE_COPY)}">
          <button class="row-delete icon-button" type="button" data-row-delete aria-label="Удалить запись {title}" title="Удалить">{_ui_icon("trash")}</button>
          <noscript><button class="row-delete-noscript" type="submit">Удалить</button></noscript>
        </form>
        <span class="meeting-date">{_date_label(item)}</span>
      </article>
    """


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
        <div class="dialog-error" data-delete-error hidden>Не удалось удалить запись. Попробуйте еще раз.</div>
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
    if review.playback.available and review.playback.playback_path:
        speed_options = ",".join(f"{speed:g}" for speed in review.playback.speed_options)
        return f"""
          <section class="playback-bar detail-playback" data-playback-shell data-source-mode="{escape(review.playback.source_mode)}">
            <audio class="playback-audio" data-playback-player preload="metadata" src="{escape(review.playback.playback_path)}"></audio>
            <div class="playback-controls" aria-label="Управление воспроизведением">
              <button type="button" class="playback-round" data-playback-skip="-15" aria-label="Назад на 15 секунд">15</button>
              <button type="button" class="playback-round primary-play" data-playback-toggle aria-label="Воспроизвести">Play</button>
              <button type="button" class="playback-round" data-playback-skip="15" aria-label="Вперед на 15 секунд">15</button>
              <button type="button" class="playback-speed" data-playback-speed-toggle data-speed-options="{escape(speed_options)}">1x</button>
            </div>
            <div class="playback-progress-row">
              <span class="playback-time" data-playback-current>00:00</span>
              <input class="playback-progress" data-playback-progress type="range" min="0" max="{review.playback.duration_seconds}" step="0.1" value="0" aria-label="Позиция записи">
              <span class="playback-time" data-playback-duration>{_timecode(review.playback.duration_seconds)}</span>
            </div>
            {_render_playback_speaker_timeline(review)}
          </section>
        """
    return f"""
      <section class="playback-bar detail-playback is-unavailable" data-source-mode="{escape(review.playback.source_mode)}">
        <span>{escape(review.playback.policy_label)}</span>
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
    reason = escape(_ui_text(review.processing.reason_label or review.processing.reason_code) or "Текущая медиа-ревизия")
    return f"""
      <section class="revision-status" aria-label="Статус медиа-ревизии" data-media-revision-id="{media_revision_id}" data-local-media-revision-id="{local_media_revision_id}">
        <span class="chip {escape(review.meeting.status)}">{label}</span>
        <span class="row-meta"><span>Медиа-ревизия</span><span>{reason}</span></span>
      </section>
    """


def _render_access_chip(access) -> str:
    if access is None:
        return ""
    return f'<span class="chip {escape(access.state)}">{escape(_ui_text(access.label))}</span>'


def _render_access_summary(review: MeetingReviewResponse) -> str:
    access = review.access
    if access is None:
        return f'<div class="muted">{escape(_ui_text("Access state is unavailable."))}</div>'
    reason = f'<div class="muted">{escape(_ui_text(access.reason))}</div>' if access.reason else ""
    capabilities = [
        ("Поделиться", access.can_share),
        ("Скачать", access.can_download),
        ("Экспорт", access.can_export),
    ]
    capability_rows = "".join(
        f'<div class="state-row"><span>{escape(label)}</span><span class="chip {"available" if enabled else "disabled"}">{escape(_ui_text("On" if enabled else "Off"))}</span></div>'
        for label, enabled in capabilities
    )
    return f"""
      <div class="state-list">
        <div class="state-row"><strong>{escape(_ui_text(access.label))}</strong><span class="chip {escape(access.state)}">{escape(_ui_text(access.state))}</span></div>
        {reason}
        {capability_rows}
      </div>
    """


def _render_share_panel(review: MeetingReviewResponse) -> str:
    share = review.share
    if share is None:
        return f'<div class="muted">{escape(_ui_text("Sharing is unavailable for this meeting."))}</div>'
    grants = "".join(
        f"""
        <div class="state-row">
          <span><strong>{escape(grant.display_name)}</strong><br><span class="muted">{escape(_ui_text(grant.role_label))}</span></span>
          <span class="chip {escape(grant.status)}">{escape(_ui_text(grant.status))}</span>
        </div>
        """
        for grant in share.active_grants
    )
    if not grants:
        grants = f'<div class="muted">{escape(_ui_text("No active user grants."))}</div>'
    return f"""
      <div class="state-list">
        <div class="state-row"><span>{escape(_ui_text("Team visibility"))}</span><span class="chip {escape(share.team_visibility)}">{escape(_ui_text(share.team_visibility))}</span></div>
        <div class="state-row"><span>{escape(_ui_text("Copy link"))}</span><span class="chip {escape(share.copy_link_state)}">{escape(_ui_text(share.copy_link_state))}</span></div>
        <div class="state-row"><span>{escape(_ui_text("Public links"))}</span><span class="chip {escape(share.public_link_state)}">{escape(_ui_text(share.public_link_state))}</span></div>
        {grants}
      </div>
    """


def _render_artifacts(review: MeetingReviewResponse) -> str:
    if not review.artifacts:
        return f'<div class="muted">{escape(_ui_text("No exportable artifacts yet."))}</div>'
    rows = "".join(_render_artifact_state(review, artifact) for artifact in review.artifacts)
    return f'<div class="state-list">{rows}</div>'


def _render_artifact_state(review: MeetingReviewResponse, artifact: ArtifactEgressState) -> str:
    label = escape(_ui_text(artifact.label))
    reason = f'<span class="muted">{escape(_ui_text(artifact.reason))}</span>' if artifact.reason else ""
    if artifact.state == "available" and artifact.artifact_class != "package":
        action = (
            f'<a class="mini-link" href="/api/v1/cabinet/meetings/{review.meeting.meeting_id}/downloads/'
            f'{escape(artifact.artifact_class)}">{escape(_ui_text("Download"))}</a>'
        )
    elif artifact.state == "available":
        action = f'<span class="chip available">{escape(_ui_text("Export ready"))}</span>'
    else:
        action = f'<span class="chip {escape(artifact.state)}">{escape(_ui_text(artifact.state))}</span>'
    return f"""
      <div class="state-row">
        <span><strong>{label}</strong><br>{reason}</span>
        {action}
      </div>
    """


def _render_delete_confirmation(review: MeetingReviewResponse, *, embedded: bool) -> str:
    report_href = f"{_base_path(embedded)}/{review.meeting.meeting_id}/deletion-report"
    return f"""
      <div class="delete-confirmation">
        <strong>{escape(_ui_text("Delete this meeting everywhere GRAF controls"))}</strong>
        <div class="truth-copy" data-boundary-copy="{escape(BOUNDED_DELETE_COPY)}">{escape(_ui_text(BOUNDED_DELETE_COPY))}</div>
        <div class="state-row">
          <span class="muted">Резервные копии, локальные буферы, метаданные провайдера и уже переданные копии показываются отдельно.</span>
          <a class="mini-link" href="{report_href}">{escape(_ui_text("Report"))}</a>
        </div>
        <button type="button" disabled>{escape(_ui_text("Request deletion"))}</button>
      </div>
    """


def _render_activity(review: MeetingReviewResponse) -> str:
    activity = review.activity
    if activity is None or not activity.items:
        return f'<div class="muted">{escape(_ui_text("No access activity yet."))}</div>'
    rows = "".join(
        f"""
        <div class="activity-item">
          <div class="state-row"><strong>{escape(_ui_text(item.event_type))}</strong><span class="chip {escape(item.outcome)}">{escape(_ui_text(item.outcome))}</span></div>
          <div class="muted">{escape(_ui_text(item.actor_label))} · {escape(item.created_at.strftime("%Y-%m-%d %H:%M"))}</div>
        </div>
        """
        for item in activity.items[:6]
    )
    return f'<div class="activity-list">{rows}</div>'


def _render_governance(review: MeetingReviewResponse) -> str:
    actions = [
        review.governance.share,
        review.governance.export,
        review.governance.download,
        review.governance.retention,
        review.governance.delete,
    ]
    return "\n".join(
        f'<button type="button" title="{escape(_ui_text(action.reason or action.label))}" {"disabled" if action.state != "available" else ""}>{escape(_ui_text(action.label))}</button>'
        for action in actions
    )


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
    rows = "".join(_render_notes_outcome_row(category, title, state) for category, title, state in outcomes)
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


def _render_top_actions(review: MeetingReviewResponse, *, embedded: bool) -> str:
    if embedded:
        return f'<button type="button" disabled>{escape(_ui_text("Open in browser"))}</button>'
    export_disabled = "disabled" if review.governance.export.state != "available" else ""
    share_disabled = "disabled" if review.governance.share.state != "available" else ""
    return f"""
      <button type="button" disabled>{escape(_ui_text(review.template.label))}</button>
      <button type="button" {export_disabled}>{escape(_ui_text(review.governance.export.label))}</button>
      <button type="button" {share_disabled}>{escape(_ui_text(review.governance.share.label))}</button>
      <button type="button" disabled>{escape(_ui_text("More"))}</button>
    """


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
