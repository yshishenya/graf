from __future__ import annotations

from datetime import UTC, datetime, timedelta

from tests.fixtures.calendar_settings import (
    calendar_settings_calendar,
    calendar_settings_snapshot,
    calendar_settings_source,
)
from twobrain_rec_server.cabinet import view_models
from twobrain_rec_server.calendar.service import calendar_event_matches_preferences
from twobrain_rec_server.db.models import CalendarSettingsPreference


def test_calendar_settings_boundary_copy_names_read_only_no_auto_record_attendee_and_credentials() -> (
    None
):
    items = view_models.calendar_boundary_items()
    rendered = " ".join(
        [
            view_models.CALENDAR_BOUNDARY_COPY,
            *view_models.CALENDAR_FORBIDDEN_ACTION_LABELS,
            *(item.label for item in items),
            *(item.body for item in items),
        ]
    )

    assert "читаем выбранные будущие события" in rendered
    assert "не меняет события календаря" in rendered
    assert "не получают доступ к записи автоматически" in rendered
    assert "на сервере GRAF" in rendered
    assert "Приложение на Mac их не хранит" in rendered
    assert "не включает автоматическую запись" in rendered
    assert "автоматическую запись" in rendered
    assert "raw_token" not in rendered
    assert "refresh_token" not in rendered


def test_calendar_settings_provider_return_notices_are_safe_and_deduplicated() -> None:
    notices = view_models.calendar_settings_notices(
        ["connect_denied", "policy_limited", "unknown_provider_payload", "connect_denied"]
    )

    assert [notice.code for notice in notices] == ["connect_denied", "policy_limited"]
    rendered = " ".join(notice.title + " " + notice.body for notice in notices)
    assert "доступ только для чтения" in rendered
    assert "администратор организации" in rendered
    assert "raw provider" not in rendered.lower()
    assert "access_token" not in rendered
    assert "passcode" not in rendered.lower()


def test_calendar_settings_provider_limitation_copy_is_plain_and_safe() -> None:
    assert (
        view_models.calendar_provider_limitation_copy("provider_specific_limited", {})
        == "Может понадобиться настройка организации или администратор."
    )
    assert (
        view_models.calendar_provider_limitation_copy("manual_url", {})
        == "Если URL или пароль неверны, мы покажем безопасную ошибку без деталей провайдера."
    )
    assert (
        view_models.calendar_provider_limitation_copy(
            "manual_url",
            {"tenant": "admin_policy_dependent"},
        )
        == "Часть возможностей зависит от политики организации."
    )


def test_calendar_settings_defaults_keep_manual_safe_prompt_behavior() -> None:
    preferences = view_models.calendar_settings_preferences_view(None)

    assert preferences.join_prompt_enabled is True
    assert preferences.record_prompt_enabled is True
    assert preferences.include_events_without_participants is False
    assert preferences.include_events_without_link_or_location is False
    assert preferences.include_all_day_events is False
    assert preferences.include_private_free_busy_prompt_candidates is False
    assert not hasattr(preferences, "auto_record_state")


def test_calendar_settings_prompt_copy_keeps_policy_overlap_and_auto_record_boundaries() -> None:
    preferences = view_models.CalendarSettingsPreferencesView()

    assert (
        preferences.join_prompt_label
        == "Напоминать за 1 минуту до встречи с предложением подключиться"
    )
    assert preferences.record_prompt_label == "Предлагать начать запись в момент старта встречи"
    assert "политика организации" in preferences.prompt_policy_copy
    assert "выбрать событие" in preferences.overlap_prompt_copy
    assert "продолжить без календарного контекста" in preferences.overlap_prompt_copy
    assert (
        preferences.disabled_auto_record_label == "Больше не спрашивать и записывать автоматически"
    )
    assert "отдельной безопасной настройкой" in preferences.disabled_auto_record_copy
    assert "Автоматическая запись пока недоступна" in preferences.disabled_auto_record_copy
    assert (
        preferences.manual_recording_copy == "Ручной старт и стоп записи остаются доступны всегда."
    )


def test_098_calendar_settings_separates_prompt_filters_from_auto_context_eligibility() -> None:
    # FR-003/FR-009/FR-010: feature 063 preview choices never weaken 098 matching.
    surface = view_models.calendar_settings_surface(provider_payloads=[], sources=[])

    assert surface.auto_context_boundary_copy == (
        "Эти фильтры управляют подсказками и списком ближайших встреч. "
        "Приватные события и события на весь день не используются для "
        "автоматического контекста записи."
    )


def test_calendar_settings_safe_state_copy_covers_empty_loading_policy_and_private_free_busy() -> (
    None
):
    surface = view_models.calendar_settings_surface(provider_payloads=[], sources=[])
    combined = " ".join(
        [
            surface.loading_state_copy,
            surface.unavailable_state_copy,
            surface.policy_constrained_copy,
            surface.no_readable_calendars_copy,
            surface.no_selected_calendars_copy,
            surface.no_matching_events_copy,
            surface.private_free_busy_copy,
            surface.empty_state_title,
            surface.empty_state_body,
        ]
    )

    assert surface.empty_state_title == "Календари пока не подключены"
    assert "ручная запись остается доступной" in surface.loading_state_copy
    assert "секреты не показываются" in surface.unavailable_state_copy
    assert "политикой организации" in surface.policy_constrained_copy
    assert "доступных для чтения календарей" in surface.no_readable_calendars_copy
    assert "не влияет на будущие встречи" in surface.no_selected_calendars_copy
    assert (
        surface.no_matching_events_copy
        == "Нет будущих событий, которые подходят под выбранные настройки."
    )
    assert "без названия" in surface.private_free_busy_copy
    assert "ссылок" in surface.private_free_busy_copy
    assert "участников" in surface.private_free_busy_copy
    assert "raw_token" not in combined
    assert "refresh_token" not in combined
    assert "app password" not in combined.lower()
    assert "secret-" not in combined.lower()


def test_calendar_settings_count_words_use_russian_forms() -> None:
    one_source = calendar_settings_source()
    one_calendar = calendar_settings_calendar(one_source, selected=True)
    two_sources = [
        calendar_settings_source(provider_label="Источник 1"),
        calendar_settings_source(provider_label="Источник 2"),
    ]
    five_sources = [
        calendar_settings_source(provider_label=f"Источник {index}") for index in range(5)
    ]

    one_surface = view_models.calendar_settings_surface(
        provider_payloads=[],
        sources=[one_source],
        calendars_by_source={one_source.id: [one_calendar]},
    )
    two_surface = view_models.calendar_settings_surface(provider_payloads=[], sources=two_sources)
    five_surface = view_models.calendar_settings_surface(provider_payloads=[], sources=five_sources)

    assert one_surface.source_count_word == "источник"
    assert one_surface.selected_calendar_count_total_word == "календарь"
    assert two_surface.source_count_word == "источника"
    assert five_surface.source_count_word == "источников"


def test_calendar_settings_source_state_needs_selection_after_connect() -> None:
    source = calendar_settings_source(connection_state="active", sync_state="synced")
    calendars = [
        calendar_settings_calendar(source, provider_calendar_id="primary", selected=False),
        calendar_settings_calendar(source, provider_calendar_id="team", selected=False),
    ]

    rendered = view_models.calendar_source_settings_view(source, calendars=calendars)

    assert rendered.connection_state == "connected_selection_needed"
    assert rendered.connection_state_label == "Нужно выбрать календари"
    assert rendered.selected_calendar_count == 0
    assert rendered.readable_calendar_count == 2


def test_calendar_settings_source_state_marks_no_readable_calendars() -> None:
    source = calendar_settings_source(connection_state="active", sync_state="synced")

    rendered = view_models.calendar_source_settings_view(source, calendars=[])

    assert rendered.connection_state == "no_readable_calendars"
    assert rendered.connection_state_label == "Нет календарей для чтения"
    assert rendered.selected_calendar_count == 0
    assert rendered.readable_calendar_count == 0

    unavailable = calendar_settings_calendar(
        source,
        provider_calendar_id="unavailable-calendar",
        display_label="Архив",
        selected=True,
        visibility="unavailable",
    )
    rendered_unavailable = view_models.calendar_source_settings_view(
        source, calendars=[unavailable]
    )

    assert rendered_unavailable.connection_state == "no_readable_calendars"
    assert rendered_unavailable.selected_calendar_count == 0
    assert rendered_unavailable.readable_calendar_count == 0
    assert rendered_unavailable.calendars[0].selected is False
    assert rendered_unavailable.calendars[0].selectable is False


def test_calendar_settings_selectable_calendar_labels_distinguish_duplicates_and_visibility() -> (
    None
):
    source = calendar_settings_source(connection_state="active", sync_state="synced")
    shared = calendar_settings_calendar(
        source,
        provider_calendar_id="shared-calendar",
        display_label="Проект",
        selected=True,
        visibility="shared",
    )
    shared.owner_display_name = "Команда"
    delegated = calendar_settings_calendar(
        source,
        provider_calendar_id="delegated-calendar",
        display_label="Проект",
        visibility="delegated",
    )
    delegated.owner_display_name = "Ассистент"
    private = calendar_settings_calendar(
        source,
        provider_calendar_id="private-calendar",
        display_label="Личный",
        visibility="private",
    )
    unavailable = calendar_settings_calendar(
        source,
        provider_calendar_id="unavailable-calendar",
        display_label="Архив",
        visibility="unavailable",
    )

    rendered = view_models.calendar_source_settings_view(
        source, calendars=[shared, delegated, private, unavailable]
    )

    assert rendered.selected_calendar_count == 1
    assert rendered.readable_calendar_count == 3
    assert [calendar.display_label for calendar in rendered.calendars[:2]] == [
        "Проект - Команда",
        "Проект - Ассистент",
    ]
    assert {calendar.visibility_label for calendar in rendered.calendars} >= {
        "общий календарь",
        "делегированный календарь",
        "private/free-busy",
        "недоступен",
    }
    assert [calendar.selectable for calendar in rendered.calendars] == [
        True,
        True,
        True,
        False,
    ]


def test_calendar_settings_sync_health_marks_sources_stale_after_24_hours() -> None:
    now = datetime(2026, 7, 2, 12, 0, tzinfo=UTC)
    source = calendar_settings_source(
        sync_state="synced",
        last_successful_sync_at=now - timedelta(hours=25),
    )

    assert view_models.calendar_sync_health_state(source, now=now) == "stale"


def test_calendar_settings_sync_health_maps_running_failed_and_never_synced_states() -> None:
    queued = calendar_settings_source(sync_state="queued")
    syncing = calendar_settings_source(sync_state="syncing")
    credential_failed = calendar_settings_source(sync_state="credential_failed")
    provider_limited = calendar_settings_source(sync_state="rate_limited")
    never_synced = calendar_settings_source(sync_state="synced")
    never_synced.last_successful_sync_at = None

    assert view_models.calendar_sync_health_state(queued) == "queued"
    assert view_models.calendar_sync_recovery_label("queued") == "Дождитесь текущей синхронизации."
    assert view_models.calendar_sync_health_state(syncing) == "syncing"
    assert view_models.calendar_sync_health_state(credential_failed) == "credential_failed"
    assert (
        view_models.calendar_sync_recovery_label("credential_failed") == "Переподключите календарь."
    )
    assert view_models.calendar_sync_health_state(provider_limited) == "rate_limited"
    assert view_models.calendar_sync_health_state(never_synced) == "never_synced"


def test_calendar_settings_sync_health_treats_latest_failure_as_stale_even_after_success() -> None:
    now = datetime(2026, 7, 2, 12, 0, tzinfo=UTC)
    source = calendar_settings_source(
        sync_state="failed",
        last_successful_sync_at=now - timedelta(hours=2),
    )

    assert view_models.calendar_sync_health_state(source, now=now) == "stale"
    assert view_models.calendar_sync_health_label("stale") == "синхронизация устарела"
    assert view_models.calendar_sync_recovery_label("stale") == "Запустите синхронизацию вручную."


def test_calendar_settings_safe_sync_error_copy_does_not_expose_provider_payloads() -> None:
    assert (
        view_models.safe_calendar_error_message("invalid_credentials")
        == "Нужно переподключить календарь."
    )
    assert (
        view_models.safe_calendar_error_message("tenant_policy_denied")
        == "Подключение ограничено политикой организации."
    )

    fallback = view_models.safe_calendar_error_message("raw_provider_payload_with_access_token")

    assert fallback == "Синхронизация не прошла. Проверьте подключение или повторите позже."
    assert "raw_provider_payload" not in fallback
    assert "access_token" not in fallback


def test_calendar_settings_safe_labels_redact_urls_emails_and_secret_like_text() -> None:
    assert (
        view_models.safe_calendar_label("alice@example.test", fallback="Календарь") == "Календарь"
    )
    assert (
        view_models.safe_calendar_label("https://meet.example.test/private", fallback="Событие")
        == "Событие"
    )
    assert (
        view_models.safe_calendar_label("Общий календарь", fallback="Календарь")
        == "Общий календарь"
    )


def test_calendar_settings_preview_hides_private_free_busy_title() -> None:
    source = calendar_settings_source()
    calendar = calendar_settings_calendar(source, selected=True)
    event = calendar_settings_snapshot(
        source,
        calendar,
        title="Private strategy call",
        safe_to_show=False,
        meeting_link_present=False,
    )

    rendered = view_models.upcoming_preview_item(event)

    assert rendered.title == "Скрытое событие"
    assert rendered.title_state == "private"
    assert rendered.meeting_link_present is False


def test_calendar_settings_event_category_eligibility_defaults_and_opt_ins() -> None:
    source = calendar_settings_source()
    calendar = calendar_settings_calendar(source, selected=True)
    permissive_preferences = CalendarSettingsPreference(
        workspace_id=source.workspace_id,
        owner_user_id=source.owner_user_id,
        include_events_without_participants=True,
        include_events_without_link_or_location=True,
        include_all_day_events=True,
        include_private_free_busy_prompt_candidates=True,
    )
    linked = calendar_settings_snapshot(source, calendar, meeting_link_present=True)
    no_link_with_participants = calendar_settings_snapshot(
        source,
        calendar,
        provider_event_id="participants-no-link",
        meeting_link_present=False,
    )
    no_link_with_participants.conference_summary_json = {
        "meeting_link_present": False,
        "participant_count": 3,
    }
    no_participants_no_link = calendar_settings_snapshot(
        source,
        calendar,
        provider_event_id="solo-block",
        meeting_link_present=False,
    )
    no_participants_no_link.conference_summary_json = {
        "meeting_link_present": False,
        "participant_count": 0,
    }
    all_day = calendar_settings_snapshot(
        source, calendar, provider_event_id="all-day", meeting_link_present=True
    )
    all_day.all_day = True
    private = calendar_settings_snapshot(
        source,
        calendar,
        title="Private board review",
        provider_event_id="private-free-busy",
        meeting_link_present=True,
        safe_to_show=False,
    )

    assert calendar_event_matches_preferences(linked, None) is True
    assert calendar_event_matches_preferences(no_link_with_participants, None) is True
    assert calendar_event_matches_preferences(no_participants_no_link, None) is False
    assert calendar_event_matches_preferences(all_day, None) is False
    assert calendar_event_matches_preferences(private, None) is False

    assert (
        calendar_event_matches_preferences(no_link_with_participants, permissive_preferences)
        is True
    )
    assert (
        calendar_event_matches_preferences(no_participants_no_link, permissive_preferences) is True
    )
    assert calendar_event_matches_preferences(all_day, permissive_preferences) is True
    assert calendar_event_matches_preferences(private, permissive_preferences) is True
    private_preview = view_models.upcoming_preview_item(private)
    assert private_preview.title == "Скрытое событие"
    assert private_preview.meeting_link_present is False
    assert "Private board review" not in private_preview.title


def test_calendar_settings_duplicate_groups_use_provider_event_identity() -> None:
    source = calendar_settings_source()
    calendar = calendar_settings_calendar(source, selected=True)
    first = calendar_settings_snapshot(source, calendar, provider_event_id="same-event")
    second = calendar_settings_snapshot(
        source,
        calendar,
        provider_event_id="same-event",
        starts_at=datetime(2026, 7, 1, 9, 0, tzinfo=UTC),
    )

    groups = view_models.calendar_preview_groups([first, second])

    assert len(groups) == 1
    assert {event.provider_event_id for event in groups[0]} == {"same-event"}
    assert len(groups[0]) == 2


def test_calendar_settings_duplicate_groups_keep_same_provider_id_from_different_sources() -> None:
    first_source = calendar_settings_source(provider_family="caldav_yandex")
    first_calendar = calendar_settings_calendar(first_source, selected=True)
    second_source = calendar_settings_source(
        provider_family="caldav_mail_ru",
        provider_label="Mail.ru Календарь",
    )
    second_calendar = calendar_settings_calendar(second_source, selected=True)
    first = calendar_settings_snapshot(first_source, first_calendar, provider_event_id="same-event")
    second = calendar_settings_snapshot(
        second_source, second_calendar, provider_event_id="same-event"
    )

    groups = view_models.calendar_preview_groups([first, second])

    assert len(groups) == 2


def test_098_calendar_duplicate_groups_keep_same_provider_id_from_distinct_calendars() -> None:
    # FR-005/FR-047: provider event IDs are scoped by calendar, not only by account.
    source = calendar_settings_source(provider_family="caldav_yandex")
    first_calendar = calendar_settings_calendar(source, selected=True)
    second_calendar = calendar_settings_calendar(source, selected=True)
    first = calendar_settings_snapshot(
        source,
        first_calendar,
        provider_event_id="same-provider-event",
    )
    second = calendar_settings_snapshot(
        source,
        second_calendar,
        provider_event_id="same-provider-event",
    )

    groups = view_models.calendar_preview_groups([first, second])

    assert len(groups) == 2


def test_calendar_settings_preview_groups_same_meeting_link_and_marks_stale_confidence() -> None:
    first_source = calendar_settings_source(
        provider_family="caldav_yandex", provider_label="Яндекс"
    )
    first_calendar = calendar_settings_calendar(
        first_source, selected=True, display_label="Рабочий"
    )
    second_source = calendar_settings_source(
        provider_family="caldav_mail_ru", provider_label="Mail.ru"
    )
    second_calendar = calendar_settings_calendar(
        second_source, selected=True, display_label="Команда"
    )
    first = calendar_settings_snapshot(
        first_source, first_calendar, provider_event_id="yandex-event"
    )
    second = calendar_settings_snapshot(
        second_source, second_calendar, provider_event_id="mail-ru-event"
    )
    first.conference_summary_json = {"meeting_link_present": True, "url_hash": "same-link"}
    second.conference_summary_json = {"meeting_link_present": True, "url_hash": "same-link"}

    items = view_models.preview_items(
        [first, second],
        source_labels_by_id={first_source.id: "Яндекс", second_source.id: "Mail.ru"},
        calendar_labels_by_id={first_calendar.id: "Рабочий", second_calendar.id: "Команда"},
        source_sync_by_id={first_source.id: "synced", second_source.id: "stale"},
    )

    assert len(items) == 1
    assert items[0].duplicate_source_count == 2
    assert items[0].source_labels == ("Яндекс", "Mail.ru")
    assert items[0].calendar_labels == ("Рабочий", "Команда")
    assert items[0].sync_confidence_state == "stale"


def test_calendar_settings_preview_empty_reason_explains_next_step() -> None:
    assert (
        view_models.calendar_preview_empty_reason(
            has_sources=False,
            has_selected_calendar=False,
            has_matching_events=False,
        )
        == "Подключите источник календаря, чтобы увидеть будущие встречи."
    )
    assert (
        view_models.calendar_preview_empty_reason(
            has_sources=True,
            has_selected_calendar=False,
            has_matching_events=False,
        )
        == "Выберите хотя бы один календарь: без выбора будущие встречи и подсказки не подтягиваются."
    )
    assert (
        view_models.calendar_preview_empty_reason(
            has_sources=True,
            has_selected_calendar=True,
            has_matching_events=False,
        )
        == "Нет будущих событий, которые подходят под выбранные настройки."
    )


def test_calendar_settings_overlap_group_keeps_partial_overlap_as_user_choice() -> None:
    first_source = calendar_settings_source(provider_family="caldav_yandex")
    first_calendar = calendar_settings_calendar(first_source, selected=True)
    second_source = calendar_settings_source(
        provider_family="caldav_mail_ru",
        provider_label="Mail.ru Календарь",
    )
    second_calendar = calendar_settings_calendar(second_source, selected=True)
    first = calendar_settings_snapshot(
        first_source,
        first_calendar,
        provider_event_id="event-1200-1300",
        starts_at=datetime(2026, 7, 1, 12, 0, tzinfo=UTC),
        ends_at=datetime(2026, 7, 1, 13, 0, tzinfo=UTC),
    )
    second = calendar_settings_snapshot(
        second_source,
        second_calendar,
        provider_event_id="event-1230-1330",
        starts_at=datetime(2026, 7, 1, 12, 30, tzinfo=UTC),
        ends_at=datetime(2026, 7, 1, 13, 30, tzinfo=UTC),
    )

    groups = view_models.overlap_conflict_groups(
        [first, second],
        at=datetime(2026, 7, 1, 12, 45, tzinfo=UTC),
    )

    assert len(groups) == 1
    assert groups[0].overlap_starts_at == datetime(2026, 7, 1, 12, 30, tzinfo=UTC)
    assert groups[0].overlap_ends_at == datetime(2026, 7, 1, 13, 0, tzinfo=UTC)
    assert len(groups[0].events) == 2
    assert {event.title for event in groups[0].events} == {"Synthetic Planning Sync"}

    before_overlap = view_models.overlap_conflict_groups(
        [first, second],
        at=datetime(2026, 7, 1, 12, 15, tzinfo=UTC),
    )
    assert before_overlap == ()


def test_calendar_settings_overlap_group_ignores_duplicate_meeting_link() -> None:
    first_source = calendar_settings_source(provider_family="caldav_yandex")
    first_calendar = calendar_settings_calendar(first_source, selected=True)
    second_source = calendar_settings_source(
        provider_family="caldav_mail_ru",
        provider_label="Mail.ru Календарь",
    )
    second_calendar = calendar_settings_calendar(second_source, selected=True)
    first = calendar_settings_snapshot(
        first_source,
        first_calendar,
        provider_event_id="yandex-event",
        starts_at=datetime(2026, 7, 1, 12, 0, tzinfo=UTC),
        ends_at=datetime(2026, 7, 1, 13, 0, tzinfo=UTC),
    )
    second = calendar_settings_snapshot(
        second_source,
        second_calendar,
        provider_event_id="mail-ru-event",
        starts_at=datetime(2026, 7, 1, 12, 0, tzinfo=UTC),
        ends_at=datetime(2026, 7, 1, 13, 0, tzinfo=UTC),
    )
    first.conference_summary_json = {"meeting_link_present": True, "url_hash": "same-link"}
    second.conference_summary_json = {"meeting_link_present": True, "url_hash": "same-link"}

    groups = view_models.overlap_conflict_groups(
        [first, second],
        at=datetime(2026, 7, 1, 12, 30, tzinfo=UTC),
    )

    assert groups == ()
