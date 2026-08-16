from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from html import escape
from urllib.parse import urlencode
from uuid import UUID

from twobrain_rec_server.api.schemas import (
    MeetingListItem,
    MeetingListResponse,
    MeetingReviewResponse,
    NotesActionCategoryState,
    PreviousRecurringMeetingView,
    SpeakerLane,
    TranscriptSegmentView,
    TranscriptSpeakerTurnView,
)
from twobrain_rec_server.auth.workspace_onboarding import (
    WorkspaceAccessView,
    WorkspaceJoinOfferView,
)
from twobrain_rec_server.billing.notification_preferences import NotificationPreferences
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
    _render_activity,
    _render_artifacts,
    _render_delete_action,
    _render_delete_confirmation,
)
from twobrain_rec_server.cabinet.templates import (
    render_icon,
    render_template,
    trusted_component_html,
)
from twobrain_rec_server.deletion.report import BOUNDED_DELETE_COPY
from twobrain_rec_server.domain.media_filenames import MANUAL_MEDIA_UPLOAD_ACCEPT
from twobrain_rec_server.outcomes.templates import BUILT_IN_BY_KEY, BUILT_IN_TEMPLATES


def render_meeting_list_page(
    response: MeetingListResponse,
    *,
    embedded: bool = False,
    csrf_token: str | None = None,
    poll_url: str | None = None,
    product_analytics_provider: dict[str, object] | None = None,
) -> str:
    query_value = " ".join((response.filters.q or "").split())
    sort_value = cabinet_view_models.normalize_meeting_list_sort(response.filters.sort)
    active_filter_count = int(bool(response.filters.status)) + int(bool(response.filters.access))
    return _page_shell(
        "Мои встречи",
        embedded=embedded,
        csrf_token=csrf_token,
        product_analytics_provider=product_analytics_provider,
        content_template="cabinet/pages/meeting_list_content.html",
        filter_action=_base_path(embedded),
        filter_reset_url=f"{_base_path(embedded)}?sort={sort_value}",
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
            ),
            source="meeting_list.manual_upload",
        ),
        sort_label=cabinet_view_models.SORT_LABELS[sort_value],
        query_value=query_value,
        status_value=response.filters.status or "",
        access_value=response.filters.access or "",
        sort_value=sort_value,
        filters_active=bool(query_value or active_filter_count),
        active_filter_count=active_filter_count,
        filter_label=(f"Фильтры: {active_filter_count}" if active_filter_count else "Фильтры"),
        upcoming_content=trusted_component_html(
            _render_upcoming_recurring(response, embedded=embedded),
            source="meeting_list.upcoming_recurring",
        ),
    )


def render_shared_with_me_page(
    items: tuple[cabinet_view_models.SharedWithMeMeetingItem, ...],
    *,
    embedded: bool = False,
    csrf_token: str | None = None,
    product_analytics_provider: dict[str, object] | None = None,
) -> str:
    return _page_shell(
        "Поделились со мной",
        embedded=embedded,
        csrf_token=csrf_token,
        product_analytics_provider=product_analytics_provider,
        active_nav="shared-with-me",
        content_template="cabinet/pages/shared_with_me_list_content.html",
        items=items,
    )


def render_meeting_unavailable_page(
    *,
    embedded: bool = False,
    csrf_token: str | None = None,
    product_analytics_provider: dict[str, object] | None = None,
) -> str:
    return _page_shell(
        "Встреча больше недоступна",
        embedded=embedded,
        csrf_token=csrf_token,
        product_analytics_provider=product_analytics_provider,
        content_template="cabinet/pages/meeting_unavailable_content.html",
        meeting_list_href=_base_path(embedded),
    )


def render_share_invitation_unavailable_page() -> str:
    return _page_shell(
        "Приглашение недоступно",
        embedded=False,
        content_template="cabinet/pages/share_invitation_content.html",
        invitation_available=False,
        meeting_list_href=_base_path(False),
    )


def render_share_invitation_accept_page(
    *,
    share_token: str,
    workspace_id: str,
    csrf_token: str | None,
    meeting_title: str | None = None,
    meeting_occurred_at: datetime | None = None,
    meeting_duration_seconds: int | None = None,
    invitation_expires_at: datetime | None = None,
    content_scope: str = "summary_only",
    authenticated: bool = False,
    post_login_next_path: str = "/meetings",
    magic_action: str | None = None,
    magic_state: str | None = None,
    magic_csrf_token: str | None = None,
    auto_accept: bool = False,
) -> str:
    return _page_shell(
        "Приглашение на встречу",
        embedded=False,
        csrf_token=csrf_token,
        content_template="cabinet/pages/share_invitation_content.html",
        accept_action=(
            f"/api/v1/cabinet/share-invitations/{share_token}/accept?workspace_id={workspace_id}"
        ),
        invitation_available=meeting_title is not None,
        meeting_list_href=_base_path(False),
        meeting_title=meeting_title,
        meeting_occurred_at=meeting_occurred_at,
        meeting_duration_seconds=meeting_duration_seconds,
        invitation_expires_at=invitation_expires_at,
        content_scope=content_scope,
        authenticated=authenticated,
        login_href=f"/login?{urlencode({'next': post_login_next_path})}",
        magic_action=magic_action,
        magic_state=magic_state,
        magic_csrf_token=magic_csrf_token,
        auto_accept=auto_accept,
    )


def render_shared_meeting_summary_page(
    *,
    meeting_title: str,
    occurred_at: datetime,
    duration_seconds: int,
    summary_sections: list[dict[str, object]],
    authenticated: bool = False,
) -> str:
    return _page_shell(
        "Итоги встречи",
        embedded=False,
        content_template="cabinet/pages/shared_meeting_summary_content.html",
        meeting_title=meeting_title,
        occurred_at=occurred_at,
        duration_seconds=duration_seconds,
        summary_sections=_localized_shared_summary_sections(summary_sections),
        authenticated=authenticated,
    )


def _localized_shared_summary_sections(
    rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    labels = {
        "summary": "Кратко",
        "action_items": "Действия",
        "decisions": "Решения",
        "key_points": "Ключевые пункты",
        "followups": "Следующие шаги",
        "risks": "Риски",
        "questions": "Вопросы",
        "evidence": "Подтверждения",
    }
    grouped: dict[str, list[dict[str, str]]] = {key: [] for key in labels}
    for row in rows[:100]:
        category = str(row.get("category") or "")
        text = str(row.get("text") or "").strip()
        if category not in grouped or not text:
            continue
        grouped[category].append(
            {
                "text": text,
                "owner_text": str(row.get("owner_text") or "").strip(),
                "due_date_text": str(row.get("due_date_text") or "").strip(),
            }
        )
    return [
        {"label": label, "items": grouped[category]}
        for category, label in labels.items()
        if grouped[category]
    ]


def render_settings_page(
    *,
    embedded: bool = False,
    csrf_token: str | None = None,
    product_analytics_provider: dict[str, object] | None = None,
    category: str = "overview",
    provider_link_options: tuple[cabinet_view_models.ProviderLinkStartOption, ...] = (),
    workspace_spaces: tuple[WorkspaceAccessView, ...] = (),
    workspace_join_offers: tuple[WorkspaceJoinOfferView, ...] = (),
    workspace_offer_result: str | None = None,
    workspace_switch_result: str | None = None,
    account_surface: cabinet_view_models.AccountSettingsSurface | None = None,
    provider_link_result: str | None = None,
    device_revoke_result: str | None = None,
    session_result: str | None = None,
    notification_result: str | None = None,
    account_close_result: str | None = None,
    profile_result: str | None = None,
    preferences_result: str | None = None,
    provider_unlink_result: str | None = None,
    account_active: str = "profile",
    notification_preferences: object | None = None,
    show_account_navigation: bool = True,
) -> str:
    offer_result_copy = {
        "accepted": "Рабочее пространство добавлено. Текущее пространство не изменилось.",
        "rejected": "Приглашение отклонено. Текущее пространство не изменилось.",
        "unavailable": "Приглашение больше недоступно. Текущее пространство не изменилось.",
    }.get(workspace_offer_result)
    switch_result_copy = {
        "activated": "Текущее пространство изменено. Новые встречи сохранятся здесь.",
    }.get(workspace_switch_result)
    provider_link_result_copy = {
        "confirmed": "Способ входа подключён к текущему аккаунту.",
        "provider_link_conflict": "Этот способ входа уже связан с другим аккаунтом.",
        "merge_blocked": "Объединение заблокировано: сначала нужно устранить указанный конфликт.",
        "merge_cancelled": "Объединение отменено. Данные не изменены.",
        "provider_link_denied": "Подключение не разрешено текущей политикой.",
        "provider_link_expired": "Срок подключения истёк. Начните заново.",
    }.get(provider_link_result)
    provider_unlink_result_copy = {
        "success": "Способ входа отключён. Остальные подтверждённые способы сохранены.",
    }.get(provider_unlink_result)
    device_revoke_result_copy = {
        "revoked": "Устройство отозвано. Его активные сессии больше не действуют.",
        "others_revoked": "Доступ на остальных устройствах завершён. Текущее устройство остаётся активным.",
        "reauth_required": "Для этого действия войдите через подтверждённую веб-сессию и повторите попытку.",
        "failed": "Не удалось отозвать устройство. Попробуйте ещё раз.",
    }.get(device_revoke_result)
    content_templates = {
        "overview": "cabinet/pages/settings_content.html",
        "recording": "cabinet/pages/settings_recording_content.html",
        "summaries": "cabinet/pages/settings_summaries_content.html",
        "workspace": "cabinet/pages/settings_workspace_content.html",
        "account": "cabinet/pages/settings_account_content.html",
        "notifications": "cabinet/pages/settings_notifications_content.html",
    }
    titles = {
        "overview": "Настройки",
        "recording": "Запись встреч",
        "summaries": "Итоги",
        "workspace": "Пространства",
        "account": "Аккаунт и безопасность",
        "notifications": "Уведомления",
    }
    resolved_category = category if category in content_templates else "overview"
    settings_context = {
        "provider_link_options": provider_link_options,
        "provider_link_start_base_path": "/desktop/settings/provider-links"
        if embedded
        else "/settings/provider-links",
        "workspace_spaces": workspace_spaces,
        "workspace_switch_result": switch_result_copy,
        "workspace_switch_action_base_path": "/desktop/settings/spaces"
        if embedded
        else "/settings/spaces",
        "workspace_switch_available": True,
        "workspace_join_offers": workspace_join_offers,
        "workspace_offer_result": offer_result_copy,
        "workspace_offer_action_base_path": "/desktop/settings/join-offers"
        if embedded
        else "/settings/join-offers",
        "summary_formats": BUILT_IN_TEMPLATES,
        "account_surface": account_surface or cabinet_view_models.AccountSettingsSurface(),
        "provider_link_result": provider_link_result_copy,
        "provider_unlink_result": provider_unlink_result_copy,
        "device_revoke_result": device_revoke_result_copy,
        "session_result": {
            "revoked": "Сеанс завершён.",
            "others_revoked": "Остальные сеансы завершены. Текущая сессия остаётся активной.",
            "reauth_required": "Для управления сессиями войдите через подтверждённую веб-сессию и повторите попытку.",
        }.get(session_result),
        "notification_result": {"saved": "Настройки уведомлений сохранены."}.get(
            notification_result
        ),
        "account_close_result": {
            "scheduled": "Закрытие аккаунта запланировано. До даты отмены доступ и данные сохраняются, будущие списания отключены.",
            "canceled": "Закрытие аккаунта отменено.",
            "reauth_required": "Для закрытия аккаунта войдите через подтверждённую веб-сессию и повторите попытку.",
        }.get(account_close_result),
        "profile_result": {"saved": "Профиль сохранён."}.get(profile_result),
        "preferences_result": {"saved": "Настройки языка, часового пояса и темы сохранены."}.get(
            preferences_result
        ),
        "account_active": account_active,
        "notification_preferences": notification_preferences or NotificationPreferences(),
        "show_account_navigation": show_account_navigation,
    }
    return _page_shell(
        titles[resolved_category],
        embedded=embedded,
        active_nav="settings",
        settings_active=resolved_category,
        csrf_token=csrf_token,
        product_analytics_provider=product_analytics_provider,
        content_template=content_templates[resolved_category],
        **settings_context,
    )


def render_provider_link_settings_page(
    surface: cabinet_view_models.ProviderLinkSettingsSurface,
    *,
    embedded: bool = False,
    csrf_token: str | None = None,
    product_analytics_provider: dict[str, object] | None = None,
    result: str | None = None,
) -> str:
    base_path = "/desktop/settings/provider-links" if embedded else "/settings/provider-links"
    return _page_shell(
        "Способ входа",
        embedded=embedded,
        active_nav="settings",
        settings_active="account",
        csrf_token=csrf_token,
        product_analytics_provider=product_analytics_provider,
        content_template="cabinet/fragments/provider_link_settings.html",
        surface=surface,
        settings_href="/desktop/settings/account" if embedded else "/settings/account",
        confirmation_action=f"{base_path}/{surface.link_state_id}/confirm",
        result=result,
    )


def render_account_merge_page(
    preview: object | None,
    *,
    intent_id: UUID,
    embedded: bool = False,
    csrf_token: str | None = None,
    product_analytics_provider: dict[str, object] | None = None,
    error_message: str | None = None,
) -> str:
    base_path = "/desktop/settings/account/merge" if embedded else "/settings/account/merge"
    return _page_shell(
        "Объединение аккаунтов",
        embedded=embedded,
        active_nav="settings",
        settings_active="account",
        csrf_token=csrf_token,
        product_analytics_provider=product_analytics_provider,
        content_template="cabinet/pages/account_merge_content.html",
        preview=preview,
        intent_id=intent_id,
        confirm_action=f"{base_path}/{intent_id}/confirm",
        cancel_action=f"{base_path}/{intent_id}/cancel",
        settings_href="/desktop/settings/account" if embedded else "/settings/account",
        error_message=error_message,
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
    product_analytics_provider: dict[str, object] | None = None,
) -> str:
    return _page_shell(
        surface.title,
        embedded=embedded,
        active_nav="settings",
        settings_active="calendar",
        csrf_token=csrf_token,
        product_analytics_provider=product_analytics_provider,
        content_template="cabinet/fragments/calendar_settings.html",
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
        settings_navigation=cabinet_view_models.settings_category_navigation(
            embedded=embedded,
            active="calendar",
        ),
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
    query_value = " ".join((response.filters.q or "").split())
    has_refinement = bool(query_value or response.filters.status or response.filters.access)
    sort_value = cabinet_view_models.normalize_meeting_list_sort(response.filters.sort)
    time_basis: cabinet_view_models.MeetingListTimeBasis = (
        "updated" if sort_value in {"updated_desc", "updated_asc"} else "meeting"
    )
    rows = "\n".join(
        _render_meeting_row(
            item,
            embedded=embedded,
            csrf_token=csrf_token,
            time_basis=time_basis,
        )
        for item in response.items
    )
    if rows:
        list_content = f'<ol class="meeting-list" role="list" aria-label="Встречи">{rows}</ol>'
    else:
        if has_refinement:
            list_content = (
                '<div class="empty-state"><strong>Ничего не найдено</strong>'
                "<span>Измените запрос или сбросьте фильтры.</span></div>"
            )
        else:
            list_content = (
                '<div class="empty-state"><strong>Пока нет встреч</strong>'
                "<span>Начните запись или загрузите готовый файл.</span></div>"
            )
    poll_attrs = _meeting_list_poll_attrs(response, poll_url=poll_url, poll_empty=embedded)
    result_count_copy = (
        f"Найдено: больше {len(response.items)}"
        if response._has_more
        else f"Найдено: {len(response.items)}"
    )
    result_count = (
        f'<div class="meeting-result-count" data-meeting-result-count>{result_count_copy}</div>'
        if has_refinement
        else ""
    )
    result_complete = "false" if response._has_more else "true"
    content = f"""
      <div class="list-loading-state" data-list-loading-state role="status" aria-live="polite" hidden>
        <span>Загружаем встречи…</span>
        <div class="list-loading-skeleton" aria-hidden="true">
          <span></span><span></span><span></span>
        </div>
      </div>
      <div data-list-current-content data-meeting-result-complete="{result_complete}">
        {result_count}
        <section class="list-card cabinet-card" aria-label="Встречи" data-meeting-list{poll_attrs}>
          {list_content}
        </section>
      </div>
    """
    return render_template(
        "cabinet/fragments/meeting_list.html",
        content=trusted_component_html(content, source="meeting_list.rows"),
    )


def _render_manual_upload_fragment(
    *,
    embedded: bool,
    csrf_token: str | None,
) -> str:
    base_path = _base_path(embedded)
    return render_template(
        "cabinet/fragments/manual_upload.html",
        embedded=embedded,
        upload_available=bool(csrf_token),
        upload_endpoint="/api/v1/cabinet/media-uploads",
        media_accept=MANUAL_MEDIA_UPLOAD_ACCEPT,
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
        f' data-upload-progress-poll hx-get="{hx_get}" hx-trigger="every 1s" '
        'hx-target="#meeting-list-region" hx-select="#meeting-list-region" hx-swap="outerHTML"'
    )


def _meeting_list_should_poll(response: MeetingListResponse, *, poll_empty: bool) -> bool:
    if not response.items:
        return poll_empty
    for item in response.items:
        presentation_status = cabinet_view_models.meeting_list_presentation_status(item)
        if presentation_status == "failed":
            continue
        if (
            (item.upload is not None and item.upload.is_active)
            or presentation_status in {"uploading", "submitted", "processing"}
            or item.playback.state == "preparing"
        ):
            return True
    return False


def render_meeting_detail_page(
    review: MeetingReviewResponse,
    *,
    embedded: bool = False,
    csrf_token: str | None = None,
    poll_url: str | None = None,
    product_analytics_provider: dict[str, object] | None = None,
    shared_workspace_id: UUID | None = None,
) -> str:
    content = _render_meeting_detail_content(
        review,
        embedded=embedded,
        csrf_token=csrf_token,
        poll_url=poll_url,
        shared_workspace_id=shared_workspace_id,
    )
    return _page_shell(
        review.meeting.title,
        content,
        embedded=embedded,
        csrf_token=csrf_token,
        product_analytics_provider=product_analytics_provider,
        content_source="meeting_detail.content",
    )


def render_meeting_detail_fragment(
    review: MeetingReviewResponse,
    *,
    embedded: bool = False,
    csrf_token: str | None = None,
    focus_calendar_context: bool = False,
    poll_url: str | None = None,
    shared_workspace_id: UUID | None = None,
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
                shared_workspace_id=shared_workspace_id,
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
    shared_workspace_id: UUID | None = None,
) -> str:
    transcript_rows = review.transcript.speaker_turns or review.transcript.segments
    speaker_palette = _speaker_palette(review)
    transcript = trusted_component_html(
        _render_transcript(transcript_rows, speaker_palette), source="meeting_detail.transcript"
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
    outcomes_selected = review.notes_action_truth.summary.state == "available"
    content_export_available = review.content_exports is not None and (
        review.content_exports.transcript.state == "available"
        or review.content_exports.summary.state in {"available", "partial"}
        or review.content_exports.combined.state == "available"
    )
    meeting_details_available = _meeting_details_available(review) and shared_workspace_id is None
    more_actions_available = (
        content_export_available
        or review.governance.download.state == "available"
        or meeting_details_available
        or review.governance.delete.state == "available"
    )
    current_summary_format_key = review.template.reason or "graf-auto-v1"
    current_summary_format = BUILT_IN_BY_KEY.get(current_summary_format_key)
    shared_api_root = f"/api/v1/cabinet/shared-meetings/{review.meeting.meeting_id}"
    shared_query = f"?workspace_id={shared_workspace_id}" if shared_workspace_id is not None else ""
    playback_path = (
        f"{shared_api_root}/playback{shared_query}"
        if shared_workspace_id is not None
        else review.playback.playback_path
    )
    audio_download_href = (
        f"{shared_api_root}/downloads/audio{shared_query}"
        if shared_workspace_id is not None
        else f"/api/v1/cabinet/meetings/{review.meeting.meeting_id}/downloads/audio"
    )
    content_export_endpoint = (
        f"{shared_api_root}/content-exports{shared_query}"
        if shared_workspace_id is not None
        else f"/api/v1/cabinet/meetings/{review.meeting.meeting_id}/content-exports"
    )
    return render_template(
        "cabinet/pages/meeting_detail_content.html",
        base_path=_base_path(embedded),
        meeting_title=review.meeting.title,
        meeting_date=cabinet_view_models.date_label(review.meeting),
        meeting_duration=cabinet_view_models.format_duration(review.meeting.duration_seconds),
        status_label=_ui_text(review.meeting.status_label),
        media_revision_id=(
            ""
            if shared_workspace_id is not None
            else str(review.provenance.media_revision_id or "")
        ),
        local_media_revision_id=(
            ""
            if shared_workspace_id is not None
            else review.provenance.local_media_revision_id or ""
        ),
        playback_poll_url=poll_url or "",
        playback_poll_active="true" if review.playback.state == "preparing" else "false",
        playback_live_label=review.playback.label,
        top_actions=trusted_component_html(
            _render_meeting_workspace_actions(
                review,
                embedded=embedded,
                more_actions_available=more_actions_available,
            ),
            source="meeting_detail.top_actions",
        ),
        outcomes_selected=outcomes_selected,
        content_export_available=content_export_available,
        meeting_details_available=meeting_details_available,
        more_actions_available=more_actions_available,
        meeting_id=review.meeting.meeting_id,
        summary_controls_available=bool(
            review.access is not None
            and review.access.state == "owner"
            and review.transcript.available
        ),
        summary_formats=BUILT_IN_TEMPLATES,
        current_summary_format_key=current_summary_format_key,
        current_summary_format_version=str(
            review.template.template_version
            or (current_summary_format.version if current_summary_format is not None else "")
        ),
        current_summary_format_id=str(review.template.template_id or ""),
        current_summary_format=(
            current_summary_format.name
            if current_summary_format is not None
            else review.template.label
        ),
        current_outcome_set_id=(
            str(review.content_exports.outcome_set_id or "")
            if review.content_exports is not None
            else ""
        ),
        current_summary_format_template_id=(str(review.template.template_id or "")),
        summary_settings_href=_settings_path(embedded) + "#summary-formats",
        audio_download_available=(review.governance.download.state == "available"),
        audio_download_href=audio_download_href,
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
        artifacts=trusted_component_html(
            _render_artifacts(review), source="meeting_detail.artifacts"
        ),
        deletion_truth_copy=review.deletion_truth_copy or "",
        deletion_truth_text=_ui_text(review.deletion_truth_copy or ""),
        delete_confirmation=trusted_component_html(
            _render_delete_confirmation(
                review,
                embedded=embedded,
                csrf_token=csrf_token,
            ),
            source="meeting_detail.delete_confirmation",
        ),
        delete_action=trusted_component_html(
            _render_delete_action(review),
            source="meeting_detail.delete_confirmation",
        ),
        deletion_report_href=(
            f"{_base_path(embedded)}/{review.meeting.meeting_id}/deletion-report"
            if review.governance.delete.state == "available"
            else ""
        ),
        speaker_lanes=trusted_component_html(
            _render_speaker_lanes(review, embedded=embedded, csrf_token=csrf_token),
            source="meeting_detail.speaker_lanes",
        ),
        activity=trusted_component_html(_render_activity(review), source="meeting_detail.activity"),
        playback=trusted_component_html(
            _render_playback(
                review,
                embedded=embedded,
                csrf_token=csrf_token,
                playback_path=playback_path,
            ),
            source="meeting_detail.playback",
        ),
        content_export_dialog=trusted_component_html(
            _render_content_export_dialog(
                review,
                csrf_token=csrf_token,
                embedded=embedded,
                endpoint=content_export_endpoint,
            ),
            source="meeting_detail.content_export_dialog",
        ),
    )


def _meeting_details_available(review: MeetingReviewResponse) -> bool:
    return bool(
        review.artifacts
        or (review.activity is not None and review.activity.items)
        or (review.speakers is not None and review.speakers.speakers)
        or review.provenance.media_revision_id
        or review.provenance.local_media_revision_id
        or review.calendar_context
        or review.deletion_truth_copy
    )


def _render_meeting_workspace_actions(
    review: MeetingReviewResponse,
    *,
    embedded: bool,
    more_actions_available: bool,
) -> str:
    share_available = review.governance.share.state == "available"
    share_attributes = (
        ' aria-haspopup="dialog" aria-expanded="false"'
        if share_available
        else ' disabled aria-disabled="true" aria-describedby="meeting-share-disabled-reason"'
    )
    share_reason = (
        ""
        if share_available
        else '<span class="sr-only" id="meeting-share-disabled-reason">'
        "Поделиться пока недоступно по политике встречи</span>"
    )
    share_url = f"{_base_path(embedded)}/{review.meeting.meeting_id}/share"
    more_action = ""
    if more_actions_available:
        more_action = """
      <button type="button" id="meeting-actions-trigger" data-meeting-panel-open="more"
              aria-haspopup="menu" aria-controls="meeting-context-more"
              aria-expanded="false">Ещё</button>
        """
    return f"""
      <button type="button" data-share-dialog-open aria-controls="meeting-share-dialog" hx-get="{share_url}" hx-target="#meeting-share-host" hx-swap="innerHTML"{share_attributes}>Поделиться</button>
      {share_reason}
      {more_action}
    """


def _render_content_export_dialog(
    review: MeetingReviewResponse,
    *,
    csrf_token: str | None,
    embedded: bool,
    endpoint: str | None = None,
) -> str:
    capability = review.content_exports
    if capability is None:
        return ""
    scope_states = {
        "transcript": capability.transcript,
        "summary": capability.summary,
        "combined": capability.combined,
    }
    scope_labels = {
        "transcript": "Расшифровка",
        "summary": "Итоги",
        "combined": "Расшифровка и итоги",
    }
    state_labels = {
        "available": "доступно",
        "partial": "частично готово",
        "processing": "обрабатывается",
        "missing": "недоступно",
        "denied": "запрещено политикой",
        "deletion_in_progress": "встреча удаляется",
        "failed": "ошибка подготовки",
        "audit_unavailable": "аудит недоступен",
    }
    initial_scope = next(
        (
            scope
            for scope, state in scope_states.items()
            if state.state == "available" or (scope == "summary" and state.state == "partial")
        ),
        "transcript",
    )
    scope_options = "".join(
        (
            f'<option value="{scope}" '
            f"{'selected' if scope == initial_scope else ''} "
            f"{'disabled' if not (state.state == 'available' or (scope == 'summary' and state.state == 'partial')) else ''}>"
            f"{escape(scope_labels[scope])}"
            f"{'' if state.state == 'available' else f' — {escape(state_labels[state.state])}'}</option>"
        )
        for scope, state in scope_states.items()
    )
    format_data = " ".join(
        f'data-export-formats-{scope}="{escape(",".join(formats))}"'
        for scope, formats in capability.formats.items()
    )
    format_groups = (
        ("Текст", ("txt", "md")),
        ("Таблицы", ("csv", "xlsx")),
        ("Данные", ("json",)),
        ("Субтитры", ("srt",)),
    )
    format_labels = {
        "txt": "Текст (.txt)",
        "md": "Markdown (.md)",
        "csv": "Таблица CSV (.csv)",
        "xlsx": "Excel (.xlsx)",
        "json": "JSON (.json)",
        "srt": "Субтитры (.srt)",
    }
    initial_formats = set(capability.formats[initial_scope])
    format_options = "".join(
        f'<optgroup label="{escape(group_label)}">'
        + "".join(
            f'<option value="{format_name}">{escape(format_labels[format_name])}</option>'
            for format_name in group_formats
            if format_name in initial_formats
        )
        + "</optgroup>"
        for group_label, group_formats in format_groups
        if any(format_name in initial_formats for format_name in group_formats)
    )
    result_id = str(capability.processing_result_id or "")
    outcome_id = str(capability.outcome_set_id or "")
    submit_label = "Сохранить…" if embedded else "Скачать файл"
    delivery_mode = "save" if embedded else "download"
    return f"""
      <dialog id="content-export-dialog" class="content-export-dialog" data-content-export-dialog aria-labelledby="content-export-title">
        <form
          class="content-export-form"
          data-content-export-form
          data-endpoint="{escape(endpoint or f"/api/v1/cabinet/meetings/{review.meeting.meeting_id}/content-exports")}"
          data-processing-result-id="{escape(result_id)}"
          data-outcome-set-id="{escape(outcome_id)}"
          data-csrf-token="{escape(csrf_token or "")}"
          data-export-delivery="{delivery_mode}"
          {format_data}
        >
          <header class="content-export-header">
            <h2 id="content-export-title" tabindex="-1" data-export-dialog-title>Сохранить файл</h2>
            <button type="button" class="icon-button content-export-close" aria-label="Закрыть экспорт" data-export-dialog-close>{_ui_icon("x")}</button>
          </header>
          <div class="content-export-body">
            <label class="content-export-field">
              <span>Что сохранить</span>
              <select name="content_scope" data-export-scope>{scope_options}</select>
            </label>
            <label class="content-export-field">
              <span>Формат</span>
              <select name="format" data-export-format>{format_options}</select>
            </label>
            <details class="content-export-details" data-export-options-details>
              <summary>Дополнительно</summary>
              <div class="content-export-options">
                <label data-export-option-speakers><input type="checkbox" name="include_speaker_labels" checked> Указывать участников</label>
                <label data-export-option-timestamps><input type="checkbox" name="include_timestamps" checked> Добавлять время</label>
                <label data-export-option-evidence><input type="checkbox" name="include_evidence" checked> Добавлять ссылки на фрагменты</label>
                <button type="button" class="quiet content-export-copy" data-export-copy>Скопировать текст</button>
              </div>
            </details>
          </div>
          <footer class="content-export-footer">
            <p class="content-export-status" data-export-status role="status" aria-live="polite" aria-atomic="true"></p>
            <div class="content-export-actions">
              <button type="button" class="quiet" data-export-dialog-cancel>Отмена</button>
              <button type="submit" class="primary" data-export-submit>{submit_label}</button>
            </div>
          </footer>
        </form>
      </dialog>
    """


def _speaker_display_label(label: str) -> str:
    if label.startswith("SPEAKER_") and label.removeprefix("SPEAKER_").isdigit():
        return label
    if label.startswith("Speaker "):
        suffix = label.removeprefix("Speaker ").strip()
        return f"Спикер {suffix}" if suffix else "Спикер"
    return _ui_text(label)


def _speaker_palette(review: MeetingReviewResponse) -> dict[str, int]:
    return {
        speaker.speaker_key: index % 6 + 1 for index, speaker in enumerate(review.speakers.speakers)
    }


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
    time_basis: cabinet_view_models.MeetingListTimeBasis = "meeting",
) -> str:
    presentation = cabinet_view_models.meeting_list_row_presentation(
        item,
        time_basis=time_basis,
    )
    meeting_path = f"{_base_path(embedded)}/{item.meeting_id}"
    delete_action = f"{meeting_path}/deletion-requests"
    row_state_classes = ""
    if presentation.status_label is not None:
        row_state_classes += " has-status"
    if selected:
        row_state_classes += " is-selected"
    source_icon = render_icon(presentation.media_kind)
    source_label = presentation.media_label
    title = escape(presentation.display_title)
    action_context = escape(f"{presentation.display_title}, {presentation.time_label}")
    id_base = f"meeting-{item.meeting_id}"
    duration_id = f"{id_base}-duration"
    status_id = f"{id_base}-status"
    readiness_id = f"{id_base}-readiness"
    time_id = f"{id_base}-time"
    described_by = [duration_id]
    if presentation.status_label is not None:
        described_by.append(status_id)
    if presentation.content_readiness_label is not None:
        described_by.append(readiness_id)
    described_by.append(time_id)
    link_described_by_value = " ".join(
        described_by[:-1]
        if presentation.display_title in {"Запись", "Загруженная запись"}
        else described_by
    )
    row_meta = _render_meeting_row_meta(
        presentation,
        meeting_path=meeting_path,
        status_id=status_id,
        readiness_id=readiness_id,
    )
    meta_html = f'<span class="row-meta">{row_meta}</span>' if row_meta else ""
    can_manage_lifecycle = item.access.state == "owner" or item.access.can_manage_team_visibility
    selection_control = (
        f'<label class="row-select-hit"><input class="row-check" type="checkbox" '
        f'data-meeting-select aria-label="Выбрать встречу {action_context}"></label>'
        if can_manage_lifecycle
        else '<span class="row-select-hit row-contextual-placeholder" aria-hidden="true"></span>'
    )
    csrf_field = (
        f'<input type="hidden" name="csrf_token" value="{escape(csrf_token)}">'
        if csrf_token
        else ""
    )
    delete_control = (
        f"""
        <form class="row-delete-form" method="post" action="{delete_action}" data-row-delete-form>
          {csrf_field}
          <input type="hidden" name="confirmation_boundary" value="{escape(BOUNDED_DELETE_COPY)}">
          <button class="row-delete icon-button" type="button" data-row-delete aria-label="Удалить встречу {action_context}" title="Удалить">{render_icon("trash")}</button>
          <noscript><button class="row-delete-noscript" type="submit">Удалить</button></noscript>
        </form>
        """
        if can_manage_lifecycle
        else '<span class="row-delete-form row-contextual-placeholder" aria-hidden="true"></span>'
    )
    return f"""
      <li class="meeting-row cabinet-row{row_state_classes}" data-meeting-row data-meeting-id="{item.meeting_id}">
        {selection_control}
        <span class="row-icon" data-media-kind="{source_label}" aria-hidden="true">{source_icon}</span>
        <div class="meeting-content">
          <span class="meeting-heading">
            <a class="meeting-title" data-meeting-open href="{meeting_path}" aria-label="{escape(presentation.open_accessible_name)}" aria-describedby="{link_described_by_value}"><span class="row-title">{title}</span></a>
            <span class="meeting-duration muted" id="{duration_id}">{escape(presentation.duration_label)}</span>
          </span>
          {meta_html}
        </div>
        {delete_control}
        <span class="meeting-date" id="{time_id}">{escape(presentation.time_label)}</span>
      </li>
    """


def _render_meeting_row_meta(
    presentation: cabinet_view_models.MeetingListRowPresentation,
    *,
    meeting_path: str,
    status_id: str,
    readiness_id: str,
) -> str:
    status = ""
    if presentation.status_label is not None:
        progress_attrs = (
            f' data-upload-progress-active data-upload-progress-percent="{presentation.progress_percent}"'
            if presentation.progress_percent is not None
            else ""
        )
        status = (
            f'<span class="meeting-status" id="{status_id}" '
            f'data-status-kind="{escape(presentation.status_kind or "")}"'
            f"{progress_attrs}>"
            f"{escape(presentation.status_label)}</span>"
        )
    progress = ""
    if presentation.progress_percent is not None:
        percent = presentation.progress_percent
        progress = f"""
          <span class="upload-progress-meter" role="progressbar" aria-label="Прогресс отправки записи" aria-valuemin="0" aria-valuemax="100" aria-valuenow="{percent}">
            <span class="upload-progress-meter__bar" style="width: {percent}%"></span>
          </span>
        """
    action = ""
    if presentation.status_kind == "calendar_choice":
        action_context = escape(f"{presentation.display_title}, {presentation.time_label}")
        action = (
            f'<a class="mini-link calendar-context-list-action" '
            f'href="{meeting_path}#calendar-context-chooser" '
            f'aria-label="Выбрать встречу {action_context}">'
            "Выбрать встречу</a>"
        )
    readiness = (
        f'<span class="meeting-content-readiness" id="{readiness_id}">'
        f"{escape(presentation.content_readiness_label)}</span>"
        if presentation.content_readiness_label is not None
        else ""
    )
    return status + progress + readiness + action


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
        <div class="dialog-error" data-delete-error hidden>Не удалось удалить запись. Попробуйте ещё раз.</div>
      </dialog>
    """


def _render_transcript(
    segments: list[TranscriptSegmentView | TranscriptSpeakerTurnView],
    speaker_palette: dict[str, int],
) -> str:
    return "\n".join(
        f"""
          <article class="segment speaker-color-{speaker_palette.get(segment.speaker_key, 0)}" data-transcript-turn data-source-segments="{escape(_transcript_source_segment_ids(segment))}" data-speaker-key="{escape(segment.speaker_key)}" data-start-seconds="{escape(str(segment.start_seconds))}" data-end-seconds="{escape(str(segment.end_seconds))}" tabindex="-1">
            {_render_timestamp(segment)}
            <div class="speaker"><span class="dot" aria-hidden="true"></span>{escape(_speaker_display_label(segment.speaker_label))}</div>
            <div class="text">{escape(segment.text)}</div>
          </article>
        """
        for segment in segments
    )


def _transcript_source_segment_ids(
    segment: TranscriptSegmentView | TranscriptSpeakerTurnView,
) -> str:
    source_ids = getattr(segment, "source_segment_ids", None)
    if source_ids:
        return " ".join(str(source_id) for source_id in source_ids)
    return str(getattr(segment, "segment_id", ""))


def _render_timestamp(segment: TranscriptSegmentView | TranscriptSpeakerTurnView) -> str:
    if segment.seekable and segment.seek_seconds is not None:
        return (
            f'<button class="timestamp timestamp-seek" type="button" '
            f'data-seek-seconds="{escape(str(segment.seek_seconds))}">{escape(segment.timestamp_label)}</button>'
        )
    return f'<div class="timestamp">{escape(segment.timestamp_label)}</div>'


def _render_playback(
    review: MeetingReviewResponse,
    *,
    embedded: bool,
    csrf_token: str | None,
    playback_path: str | None = None,
) -> str:
    playback_path = playback_path or review.playback.playback_path
    if review.playback.can_play and playback_path:
        speed_options = ",".join(f"{speed:g}" for speed in review.playback.speed_options)
        speaker_palette = _speaker_palette(review)
        return f"""
          <section class="playback-bar detail-playback" data-playback-shell data-playback-state="available" data-playback-reason="{escape(review.playback.reason_code)}" data-source-mode="{escape(review.playback.source_mode)}" aria-describedby="playback-live-status">
            <audio class="playback-audio" data-playback-player preload="metadata" src="{escape(playback_path)}"></audio>
            <div class="playback-toolbar">
              {_render_speaker_manager(review, embedded=embedded, csrf_token=csrf_token, speaker_palette=speaker_palette)}
              <div class="playback-controls" aria-label="Управление воспроизведением">
                <button type="button" class="playback-round" data-playback-skip="-15" aria-label="Назад на 15 секунд">15</button>
                <button type="button" class="playback-round primary-play" data-playback-toggle aria-label="Воспроизвести">▶</button>
                <button type="button" class="playback-round" data-playback-skip="15" aria-label="Вперед на 15 секунд">15</button>
                <button type="button" class="playback-speed" data-playback-speed-toggle data-speed-options="{escape(speed_options)}">1x</button>
              </div>
            </div>
            <p class="playback-error" data-playback-error role="status" aria-live="polite" hidden>Воспроизведение временно недоступно.</p>
            <div class="playback-progress-row">
              <span class="playback-time" data-playback-current>00:00</span>
              <span class="timeline-scale playback-scale">
                <input class="playback-progress" data-playback-progress type="range" min="0" max="{review.playback.duration_seconds}" step="0.1" value="0" aria-label="Позиция записи">
                <span class="playback-range-track" aria-hidden="true"><span class="playback-range-thumb"></span></span>
              </span>
              <span class="playback-time" data-playback-duration>{_timecode(review.playback.duration_seconds)}</span>
            </div>
            {_render_playback_speaker_timeline(review, speaker_palette=speaker_palette)}
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
        <span>{cabinet_view_models.format_duration(review.playback.duration_seconds)}</span>
      </section>
    """


def _render_playback_speaker_timeline(
    review: MeetingReviewResponse,
    *,
    speaker_palette: dict[str, int],
) -> str:
    if not review.speakers.available:
        return '<div class="speaker-timeline" data-speaker-timeline></div>'
    duration = max(1, review.playback.duration_seconds)
    lanes = []
    for speaker in review.speakers.speakers:
        speaker_label = _speaker_display_label(speaker.label)
        color_class = f"speaker-color-{speaker_palette.get(speaker.speaker_key, 0)}"
        segments = []
        for segment in speaker.segments:
            start = max(0.0, float(segment.start_seconds))
            end = min(float(duration), max(start, float(segment.end_seconds)))
            left = min(100.0, max(0.0, start / duration * 100))
            width = min(100.0 - left, max(0.2, (end - start) / duration * 100))
            segment_label = f"{speaker_label} {_timecode(int(start))}-{_timecode(int(end))}"
            segments.append(
                f'<span class="timeline-segment" data-lane-segment data-start-seconds="{start:.3f}" data-end-seconds="{end:.3f}" title="{escape(segment_label)}" '
                f'aria-label="{escape(segment_label)}" style="left:{left:.2f}%;width:{width:.2f}%"></span>'
            )
        lanes.append(
            f"""
            <div class="timeline-lane {color_class}" data-speaker-lane="{escape(speaker.speaker_key)}">
              <span class="timeline-speaker" title="{escape(speaker_label)}"><span class="speaker-dot" aria-hidden="true"></span><span class="timeline-label">{escape(speaker_label)}</span></span>
              <span class="timeline-scale lane-scale"><span class="timeline-track" data-timeline-track role="button" tabindex="0" aria-label="Перейти по дорожке {escape(speaker_label)}">{"".join(segments)}<span class="timeline-playhead" data-timeline-playhead aria-hidden="true"></span></span></span>
              <span class="timeline-share">{speaker.talk_time_percent}%</span>
            </div>
            """
        )
    return f'<div class="speaker-timeline" data-speaker-timeline>{"".join(lanes)}</div>'


def _render_speaker_manager(
    review: MeetingReviewResponse,
    *,
    embedded: bool,
    csrf_token: str | None,
    speaker_palette: dict[str, int],
) -> str:
    if not review.speakers.available:
        return ""
    markers = "".join(
        f'<span class="speaker-manager-marker speaker-color-{speaker_palette.get(speaker.speaker_key, 0)}"></span>'
        for speaker in review.speakers.speakers[:4]
    )
    rows = []
    for speaker in review.speakers.speakers:
        speaker_label = _speaker_display_label(speaker.label)
        color_class = f"speaker-color-{speaker_palette.get(speaker.speaker_key, 0)}"
        editor = ""
        action = ""
        if review.speakers.can_rename:
            form_id = f"speaker-manager-form-{speaker.speaker_key}"
            action = f'<button class="speaker-manager-edit" type="button" data-speaker-name-open aria-expanded="false" aria-controls="{escape(form_id)}">Изменить</button>'
            editor = _render_speaker_name_form(
                review,
                speaker,
                embedded=embedded,
                csrf_token=csrf_token,
                form_id=form_id,
                extra_class="speaker-manager-form",
                hidden=True,
            )
        rows.append(
            f"""
              <div class="speaker-manager-row {color_class}">
                <span class="speaker-manager-dot" aria-hidden="true"></span>
                <span class="speaker-manager-name" title="{escape(speaker_label)}">{escape(speaker_label)}</span>
                <span class="speaker-manager-share">{speaker.talk_time_percent}%</span>
                {action}
                {editor}
              </div>
            """
        )
    return f"""
      <div class="speaker-manager" data-speaker-manager>
        <button class="speaker-manager-trigger" type="button" data-speaker-manager-toggle aria-expanded="false" aria-controls="speaker-manager-popover">
          <span>Спикеры · {len(review.speakers.speakers)}</span><span class="speaker-manager-markers" aria-hidden="true">{markers}</span>
        </button>
        <div id="speaker-manager-popover" class="speaker-manager-popover" hidden>{"".join(rows)}</div>
      </div>
    """


def _render_speaker_lanes(
    review: MeetingReviewResponse,
    *,
    embedded: bool = False,
    csrf_token: str | None = None,
) -> str:
    if not review.speakers.available:
        return f'<div class="muted">{escape(_ui_text("Speaker lanes are reserved until diarization is available."))}</div>'
    lanes = []
    for speaker in review.speakers.speakers:
        speaker_label = _speaker_display_label(speaker.label)
        editor = ""
        if review.speakers.can_rename and not review.playback.can_play:
            editor = _render_speaker_name_form(
                review,
                speaker,
                embedded=embedded,
                csrf_token=csrf_token,
                form_id=f"speaker-name-form-{speaker.speaker_key}",
            )
        lanes.append(
            f"""
        <div class="speaker-lane">
          <div class="row-meta" data-speaker-key="{escape(speaker.speaker_key)}"><strong>{escape(speaker_label)}</strong><span>{speaker.talk_time_percent}%</span></div>
          <div class="lane-track"><div class="lane-fill" style="width:{speaker.talk_time_percent}%"></div></div>
          {editor}
        </div>
        """
        )
    return "\n".join(lanes)


def _render_speaker_name_form(
    review: MeetingReviewResponse,
    speaker: SpeakerLane,
    *,
    embedded: bool,
    csrf_token: str | None,
    form_id: str,
    extra_class: str = "",
    hidden: bool = False,
) -> str:
    speaker_label = _speaker_display_label(speaker.label)
    csrf = (
        f'<input type="hidden" name="csrf_token" value="{escape(csrf_token)}">'
        if csrf_token
        else ""
    )
    cancel = (
        '<button type="button" class="quiet" data-speaker-name-cancel>Отмена</button>'
        if hidden
        else ""
    )
    return f"""
      <form id="{escape(form_id)}" class="speaker-name-form {escape(extra_class)}" data-speaker-name-form method="post" action="{_base_path(embedded)}/{review.meeting.meeting_id}/speakers/{escape(speaker.speaker_key)}"{" hidden" if hidden else ""}>
        {csrf}
        <label class="sr-only" for="speaker-name-{escape(speaker.speaker_key)}">Имя для {escape(speaker_label)}</label>
        <input id="speaker-name-{escape(speaker.speaker_key)}" name="display_name" value="{escape(speaker.display_name or "")}" placeholder="Имя спикера" maxlength="80" autocomplete="off">
        <button type="submit" class="quiet">Сохранить</button>
        {cancel}
        <span class="speaker-name-error" data-speaker-name-error role="status" aria-live="polite" hidden>Не удалось сохранить имя. Проверьте имя и попробуйте ещё раз.</span>
      </form>
    """


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
    primary = [
        ("summary", "Summary", review.notes_action_truth.summary),
        ("action_items", "Action Items", review.notes_action_truth.action_items),
        ("decisions", "Decisions", review.notes_action_truth.decisions),
    ]
    secondary = [
        ("key_points", "Key points", review.notes_action_truth.key_points),
        ("followups", "Follow-ups", review.notes_action_truth.followups),
        ("risks", "Risks", review.notes_action_truth.risks),
        ("questions", "Questions", review.notes_action_truth.questions),
        ("evidence", "Evidence", review.notes_action_truth.evidence),
    ]
    aggregate_states = {"processing", "blocked", "unavailable", "deferred", "unsafe"}
    aggregate_candidates = [
        state for _, _, state in primary + secondary if state.state in aggregate_states
    ]
    priority = {"blocked": 0, "unsafe": 1, "processing": 2, "deferred": 3, "unavailable": 4}
    aggregate = min(
        aggregate_candidates,
        key=lambda state: priority.get(state.state, len(priority)),
        default=None,
    )
    primary = [row for row in primary if row[2].state not in aggregate_states]
    secondary = [row for row in secondary if row[2].state not in aggregate_states]
    source_destination_available = review.playback.can_play or bool(review.transcript.segments)
    primary_rows = "".join(
        _render_notes_outcome_row(
            category,
            title,
            state,
            source_destination_available=source_destination_available,
        )
        for category, title, state in primary
    )
    secondary_rows = "".join(
        _render_notes_outcome_row(
            category,
            title,
            state,
            source_destination_available=source_destination_available,
        )
        for category, title, state in secondary
    )
    source = escape(_notes_source_label(review.notes_action_truth.source_basis))
    source_basis = escape(review.notes_action_truth.source_basis)
    secondary_count = sum(
        state.state == "available" and any(item.text for item in state.items)
        for _, _, state in secondary
    )
    secondary_label = "Дополнительные разделы"
    if secondary_count:
        secondary_label += f" ({secondary_count})"
    aggregate_html = ""
    if aggregate is not None:
        reason = _ui_text(aggregate.reason)
        aggregate_html = (
            f'<div class="notes-aggregate-state" data-outcome-state="{escape(aggregate.state)}" '
            'role="status">'
            f"<strong>{escape(_ui_text(aggregate.label))}</strong>"
            + (f"<p>{escape(reason)}</p>" if reason else "")
            + "</div>"
        )
    secondary_html = (
        f"""
        <details class="notes-more">
          <summary>{secondary_label}</summary>
          <div class="notes-outcomes notes-secondary-outcomes" aria-label="Дополнительные разделы">
            {secondary_rows}
          </div>
        </details>
        """
        if secondary_rows
        else ""
    )
    return f"""
      <section class="notes" data-outcome-source-basis="{source_basis}" aria-labelledby="meeting-outcomes-title">
        <div class="notes-header">
          <div class="notes-header-copy">
            <h3 id="meeting-outcomes-title">{escape(_ui_text("Итоги встречи"))}</h3>
            <p class="notes-source-line">Источник: {source}</p>
          </div>
        </div>
        {aggregate_html}
        <div class="notes-outcomes notes-primary-outcomes">
          {primary_rows}
        </div>
        {secondary_html}
      </section>
    """


def _render_notes_outcome_row(
    category: str,
    title: str,
    state: NotesActionCategoryState,
    *,
    source_destination_available: bool,
) -> str:
    state_name = escape(state.state)
    item_html = (
        "".join(
            _render_outcome_item(
                item,
                source_destination_available=source_destination_available,
            )
            for item in state.items
            if item.text
        )
        if state.state == "available"
        else ""
    )
    items = f'<div class="notes-items">{item_html}</div>' if item_html else ""
    state_reason = "" if state.state == "available" else _ui_text(state.reason)
    state_html = (
        f'<span class="notes-state-label">{escape(_ui_text(state.label))}</span>'
        if state.state != "available"
        else ""
    )
    reason_html = f'<p class="notes-state-copy">{escape(state_reason)}</p>' if state_reason else ""
    return f"""
      <section class="notes-outcome-row notes-section" data-outcome-category="{escape(category)}" data-outcome-state="{state_name}">
        <div class="notes-section-header">
          <div class="notes-section-title">
            <h4>{escape(_notes_title(title))}</h4>
            {reason_html}
          </div>
          {state_html}
        </div>
        {items}
      </section>
    """


def _render_outcome_item(item, *, source_destination_available: bool) -> str:
    text = escape(item.text or "")
    if not text:
        return ""
    owner = escape((item.owner_text or "").strip())
    due_date = escape((item.due_date_text or "").strip())
    metadata = []
    if owner:
        metadata.append(f'<span class="notes-item-meta">Ответственный: {owner}</span>')
    if due_date:
        metadata.append(f'<span class="notes-item-meta">Срок: {due_date}</span>')

    truth_label = getattr(item, "truth_label", "")
    truth_copy = {
        "supported": "Подтверждено расшифровкой",
        "not_found": "Не найдено",
        "not_inferable": "Не удалось определить",
        "unsafe": "Нужна проверка",
        "blocked": "Заблокировано",
    }.get(truth_label, _ui_text(truth_label))
    if truth_copy and truth_label != "supported":
        metadata.append(
            f'<span class="notes-item-meta notes-item-truth" data-outcome-truth-label="{escape(truth_label)}">{escape(truth_copy)}</span>'
        )

    source_controls = []
    for ref in item.source_refs:
        if not source_destination_available or not ref.seekable or ref.start_seconds is None:
            continue
        seconds = escape(str(ref.start_seconds))
        timestamp = _timecode(int(ref.start_seconds))
        source_label = f"Источник: {timestamp}"
        segment_id = escape(str(ref.transcript_segment_id or ""))
        source_controls.append(
            f'<button type="button" class="notes-source-link" data-seek-seconds="{seconds}" '
            f'data-source-segment="{segment_id}" '
            f'data-source-label="{escape(source_label)}" '
            f'aria-label="Открыть источник {escape(timestamp)} в расшифровке">{escape(timestamp)}</button>'
        )
    if source_controls:
        overflow_count = max(0, len(source_controls) - 2)
        source_noun = (
            "источник"
            if overflow_count == 1
            else "источника"
            if overflow_count < 5
            else "источников"
        )
        overflow_html = (
            f'<details class="notes-source-more"><summary aria-label="Показать ещё {overflow_count} {source_noun}">'
            f"Ещё {overflow_count}</summary>{''.join(source_controls[2:])}</details>"
            if overflow_count
            else ""
        )
        source_html = (
            '<div class="notes-item-sources"><span class="notes-source-label">Источник:</span>'
            + "".join(source_controls[:2])
            + overflow_html
            + "</div>"
        )
    else:
        source_html = ""
    metadata_html = (
        f'<div class="notes-item-meta-row">{"".join(metadata)}</div>' if metadata else ""
    )
    return (
        f'<article class="outcome-item" data-outcome-truth-label="{escape(truth_label)}">'
        f'<p class="outcome-item-text">{text}</p>{metadata_html}{source_html}</article>'
    )


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
