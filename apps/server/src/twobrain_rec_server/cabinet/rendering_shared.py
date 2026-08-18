from __future__ import annotations

from twobrain_rec_server.cabinet import view_models as cabinet_view_models
from twobrain_rec_server.cabinet.templates import render_template, trusted_component_html


def _page_shell(
    title: str,
    content: str | None = None,
    *,
    embedded: bool,
    page_template: str = "cabinet/pages/shell.html",
    csrf_token: str | None = None,
    product_analytics_provider: dict[str, object] | None = None,
    content_source: str = "cabinet.shell",
    active_nav: str = "meetings",
    profile=None,
    **context,
) -> str:
    navigation = cabinet_view_models.cabinet_navigation(active=active_nav, embedded=embedded)
    settings_active = context.pop("settings_active", "overview")
    settings_navigation = context.pop(
        "settings_navigation",
        cabinet_view_models.settings_category_navigation(
            embedded=embedded,
            active=settings_active,
        ),
    )
    content_template = context.pop("content_template", None)
    if content is None and content_template:
        content = render_template(
            content_template,
            embedded=embedded,
            navigation=navigation,
            settings_navigation=settings_navigation,
            settings_active=settings_active,
            settings_mode=active_nav == "settings",
            csrf_token=csrf_token,
            **context,
        )
        content_source = "cabinet.shell"
    if content is not None:
        context["content"] = trusted_component_html(content, source=content_source)
    shell = render_template(
        page_template,
        embedded=embedded,
        navigation=navigation,
        settings_navigation=settings_navigation,
        settings_active=settings_active,
        profile=profile or getattr(context.get("account_surface"), "profile", None),
        csrf_token=csrf_token,
        **context,
    )
    return render_template(
        "cabinet/base.html",
        title=title,
        surface_mode="desktop_embedded" if embedded else "standalone_browser",
        csrf_token=csrf_token,
        product_analytics_provider=product_analytics_provider,
        content=trusted_component_html(shell, source="cabinet.shell"),
    )


UI_TEXT: dict[str, str] = {
    "Access": "Доступ",
    "Access state is unavailable.": "Статус доступа недоступен.",
    "Action Items": "Действия",
    "Assistant": "Ассистент",
    "Available": "Доступно",
    "Can view": "Может смотреть",
    "Blocked": "Заблокировано",
    "Copy link": "Ссылка",
    "Decisions": "Решения",
    "Delete planned": "Удаление запланировано",
    "Delete this meeting everywhere GRAF controls": "Удалить встречу в системах GRAF",
    "Delete this meeting everywhere GRAF controls.": "Удалить встречу везде, где ее контролирует GRAF.",
    "Disabled": "Выключено",
    "Disabled by policy": "Заблокировано",
    "Download": "Скачать",
    "Evidence": "Фрагменты",
    "Export": "Экспорт",
    "Export package": "Экспорт",
    "Export ready": "Экспорт готов",
    "Failed": "Сбой",
    "Files already downloaded or exported are outside GRAF deletion control.": "Уже скачанные или экспортированные файлы находятся вне последующего удаления в GRAF.",
    "Files already downloaded or exported are outside later GRAF revocation. Deleting a meeting can remove what GRAF controls, not copies already saved elsewhere.": "Уже скачанные или экспортированные файлы находятся вне последующего отзыва в GRAF. Удаление встречи может убрать то, что контролирует GRAF, но не копии, уже сохраненные где-то еще.",
    "Follow-ups": "Продолжение",
    "Incoming system": "Входящий звук",
    "Interface language": "Язык интерфейса",
    "Key points": "Ключевое",
    "Local only": "Только локально",
    "Local microphone": "Микрофон",
    "Meeting processing needs operator review before outcomes can be trusted.": "Обработку встречи нужно проверить оператору, прежде чем доверять итогам.",
    "More": "Еще",
    "No access activity yet.": "Событий доступа пока нет.",
    "No active user grants.": "Активных доступов для пользователей нет.",
    "No exportable artifacts yet.": "Файлы для выгрузки пока недоступны.",
    "No lifecycle activity yet.": "Событий жизненного цикла пока нет.",
    "No lifecycle rows yet.": "Строк жизненного цикла пока нет.",
    "No local purge acknowledgement has been received yet.": "Подтверждение локальной очистки еще не получено.",
    "Not available": "Недоступно",
    "Notes": "Итоги",
    "On": "Вкл",
    "Off": "Выкл",
    "Open in browser": "Открыть в браузере",
    "Outcome deferred": "Итоги отложены",
    "Outcome source": "Источник итогов",
    "Outcomes blocked": "Итоги заблокированы",
    "Outcomes deferred": "Итоги отложены",
    "Outcomes processing": "Итоги готовятся",
    "Outcomes unavailable": "Итоги недоступны",
    "Owner": "Владелец",
    "owner": "владелец",
    "Partial": "Частично готово",
    "Processing": "Расшифровка",
    "Transcription service could not accept this media file.": "Сервис расшифровки не принял этот медиафайл.",
    "Public links": "Публичные ссылки",
    "Questions": "Вопросы",
    "Ready": "Готово",
    "Report": "Отчет",
    "Request deletion": "Запросить удаление",
    "Retention policy planned": "Правила хранения",
    "Retention controls will show policy truth before activation.": "Правила хранения появятся после активации политики.",
    "Risks": "Риски",
    "Share": "Поделиться",
    "Sharing is unavailable for this meeting.": "Поделиться этой встречей сейчас нельзя.",
    "Speaker lanes are reserved until diarization is available.": "Спикеры появятся после диаризации.",
    "Star": "Избранное",
    "Submitted": "Загружено",
    "Summary": "Кратко",
    "Summary output language": "Язык итогов",
    "Summary unavailable": "Краткое резюме недоступно",
    "Tag": "Тег",
    "Team": "Команда",
    "Team visibility": "Видимость для команды",
    "Template": "Шаблон",
    "Transcript": "Расшифровка",
    "Transcript language": "Язык расшифровки",
    "Transcript and generated outcomes may still be processing.": "Расшифровка и итоги еще могут обрабатываться.",
    "Transcript is still processing.": "Расшифровка еще готовится.",
    "Transcript review is available, but generated meeting outcomes are not part of this stored result.": "Расшифровка доступна, но сгенерированные итоги не входят в этот сохраненный результат.",
    "Uploading": "Загружается",
    "Unavailable": "Недоступно",
    "You own this meeting.": "Это ваша встреча.",
    "accepted": "принято",
    "acknowledged": "подтверждено",
    "active": "активен",
    "artifact lifecycle state": "состояние файла",
    "auth required": "нужен вход",
    "auth_required": "нужен вход",
    "allowed": "разрешено",
    "available": "доступно",
    "backup expiry pending": "ожидает срока хранения резервной копии",
    "backup_expiry_pending": "ожидает срока хранения резервной копии",
    "completed": "готово",
    "delete requested": "удаление запрошено",
    "delete_requested": "удаление запрошено",
    "deletion requested": "удаление запрошено",
    "deletion_requested": "удаление запрошено",
    "Desktop device": "Десктоп",
    "dependency unconfirmed": "зависимость не подтверждена",
    "dependency_unconfirmed": "зависимость не подтверждена",
    "disabled": "выключено",
    "disabled by default": "выключено по умолчанию",
    "disabled_by_default": "выключено по умолчанию",
    "download completed": "скачивание завершено",
    "download requested": "скачивание запрошено",
    "download stream prepared": "поток скачивания подготовлен",
    "enabled": "включено",
    "external deletion support is not confirmed": "удаление во внешнем сервисе не подтверждено",
    "External deletion support is not confirmed": "Удаление во внешнем сервисе не подтверждено",
    "local purge acknowledged": "локальная очистка подтверждена",
    "local_purge_acknowledged": "локальная очистка подтверждена",
    "local buffers purged": "локальные буферы очищены",
    "local_buffers_purged": "локальные буферы очищены",
    "metadata only": "только метаданные",
    "Owner/Admin": "Владелец/админ",
    "outside graf control": "вне контроля GRAF",
    "outside_control": "вне контроля GRAF",
    "pending": "ожидает",
    "Outside GRAF control after delivery": "Вне контроля GRAF после передачи",
    "Delivered copies are outside GRAF control": "Переданные копии находятся вне контроля GRAF",
    "Planned; this does not promise deletion outside GRAF control.": "Запланировано; это не обещает удаление вне контроля GRAF.",
    "policy blocked": "по политике",
    "policy_blocked": "по политике",
    "playback stream prepared": "поток воспроизведения подготовлен",
    "prepared": "подготовлено",
    "processing": "обработка",
    "purge_local_buffers": "локальные буферы",
    "purge_local_exports": "локальные экспорты",
    "confirm_local_expiry": "подтвердить локальное истечение",
    "Server audio purge requested": "Очистка серверного аудио запрошена",
    "unreachable": "недоступно",
    "Workspace policy disables this artifact egress.": "Политика рабочего пространства запрещает выгрузку этого файла.",
    "You": "Вы",
}


def _ui_text(value: str | None) -> str:
    if value is None:
        return ""
    normalized = value.replace("_", " ")
    return UI_TEXT.get(value, UI_TEXT.get(normalized, normalized))


def _base_path(embedded: bool) -> str:
    return "/desktop/meetings" if embedded else "/meetings"


def _settings_path(embedded: bool) -> str:
    return "/desktop/settings/summaries" if embedded else "/settings/summaries"
