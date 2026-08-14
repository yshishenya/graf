from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, Literal, cast
from uuid import UUID

from twobrain_rec_server.api.schemas import (
    ArtifactEgressState,
    CalendarRosterParticipantView,
    CalendarRosterReviewState,
    ContentExportCapabilityResponse,
    GovernanceActionState,
    GovernanceActionSummary,
    MeetingAccessState,
    MeetingActivityResponse,
    MeetingCalendarContextResponse,
    MeetingCalendarContextSummary,
    MeetingListItem,
    MeetingProvenance,
    MeetingReviewResponse,
    MeetingReviewStatus,
    MeetingUploadProgressState,
    NotesActionCategoryState,
    NotesActionTruthState,
    NotesReviewState,
    OutcomeItemView,
    OutcomeProvenanceView,
    OutcomeSourceReferenceView,
    PlaybackPreparationReasonCode,
    PlaybackPreparationState,
    PlaybackReviewState,
    PreviousRecurringMeetingReadiness,
    PreviousRecurringMeetingView,
    ProcessingReviewState,
    SharePanelState,
    SlotState,
    SourceRoleView,
    SpeakerLane,
    SpeakerLaneSegment,
    SpeakerReviewState,
    TranscriptReviewState,
    TranscriptSegmentView,
    TranscriptSpeakerTurnView,
)
from twobrain_rec_server.cabinet.access import owner_access_state
from twobrain_rec_server.cabinet.constants import DELETION_TRUTH_COPY
from twobrain_rec_server.calendar.service import (
    SELECTABLE_CALENDAR_VISIBILITIES,
    calendar_duplicate_group_key,
    dedupe_calendar_events,
)
from twobrain_rec_server.db.models import (
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
    MeetingOutcomeItem,
    MeetingOutcomeSet,
    ProcessingDependencyState,
    ProcessingResult,
    ProcessingWorkflow,
    RecordingCalendarContextLink,
    RegisteredDevice,
    TranscriptSegment,
)
from twobrain_rec_server.domain.media_filenames import (
    LEGACY_SERIALIZED_MEDIA_FILENAME_EXTENSION_RE,
    MEDIA_FILENAME_EXTENSION_RE,
    clean_legacy_serialized_media_filename_title,
    clean_media_filename_title,
    media_filename_leaf,
)
from twobrain_rec_server.domain.metadata_text import safe_metadata_text
from twobrain_rec_server.domain.statuses import (
    MediaRevisionSourceKind,
    MeetingStatus,
    ProcessingAvailabilityStatus,
    ProcessingResultStatus,
    ProcessingStatus,
    SummaryStatus,
)
from twobrain_rec_server.outcomes.templates import built_in_template_for_version
from twobrain_rec_server.processing.fences import meeting_is_deleted_or_deleting

if TYPE_CHECKING:
    from twobrain_rec_server.auth.account_closure import AccountCloseView
    from twobrain_rec_server.db.models import WorkspaceProviderLinkState


PROVIDER_LINK_LABELS = {
    "email": "Email",
    "email_magic_link": "Email",
    "yandex": "Яндекс",
    "vk": "VK",
    "telegram": "Telegram",
}


@dataclass(frozen=True, slots=True)
class ProviderLinkStartOption:
    provider: str
    label: str


@dataclass(frozen=True, slots=True)
class ProviderLinkSettingsSurface:
    link_state_id: UUID
    provider_label: str
    status: str
    status_label: str
    can_confirm: bool


def provider_link_settings_surface(link: WorkspaceProviderLinkState) -> ProviderLinkSettingsSurface:
    status_labels = {
        "initiated": "Ожидаем входа у провайдера",
        "callback_verified": "Провайдер подтверждён — подтвердите подключение в GRAF",
        "confirmed": "Способ входа подключён",
        "expired": "Срок подключения истёк. Начните заново.",
        "rejected": "Подключение не завершено. Начните заново.",
    }
    return ProviderLinkSettingsSurface(
        link_state_id=link.id,
        provider_label=PROVIDER_LINK_LABELS.get(link.candidate_provider or "", "Провайдер"),
        status=link.status,
        status_label=status_labels.get(link.status, "Подключение недоступно. Начните заново."),
        can_confirm=link.status == "callback_verified",
    )


@dataclass(frozen=True, slots=True)
class AccountProviderView:
    provider: str
    label: str
    status_label: str
    primary: bool
    connected_at: datetime | None
    can_unlink: bool = False
    identity_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class AccountDeviceView:
    device_id: UUID
    platform_label: str
    version_label: str
    status_label: str
    last_seen_at: datetime | None
    current: bool
    can_revoke: bool


@dataclass(frozen=True, slots=True)
class AccountSessionView:
    session_id: UUID
    provider_label: str
    status_label: str
    last_seen_at: datetime | None
    expires_at: datetime
    current: bool
    can_revoke: bool


@dataclass(frozen=True, slots=True)
class AccountProfileView:
    display_name: str
    primary_email: str | None = None
    locale: str = "ru-RU"
    timezone: str = "Europe/Moscow"
    theme: str = "system"


@dataclass(frozen=True, slots=True)
class AccountSettingsSurface:
    profile: AccountProfileView | None = None
    providers: tuple[AccountProviderView, ...] = ()
    devices: tuple[AccountDeviceView, ...] = ()
    sessions: tuple[AccountSessionView, ...] = ()
    unavailable: bool = False
    account_close: AccountCloseView | None = None


def account_provider_view(
    identity: ExternalIdentity,
    *,
    primary: bool = False,
    can_unlink: bool = False,
) -> AccountProviderView:
    return AccountProviderView(
        provider=identity.provider,
        label=PROVIDER_LINK_LABELS.get(identity.provider, "Способ входа"),
        status_label="Подключён" if identity.is_verified else "Проверка не завершена",
        primary=primary,
        connected_at=identity.last_seen_at or identity.created_at,
        can_unlink=can_unlink,
        identity_id=identity.id,
    )


def account_device_view(
    device: RegisteredDevice,
    *,
    current_device_id: UUID | None,
) -> AccountDeviceView:
    platform_labels = {
        "macos": "Mac",
        "web": "Браузер",
        "browser": "Браузер",
    }
    status_labels = {
        "active": "Активно",
        "revoked": "Отозвано",
    }
    is_current = device.id == current_device_id
    return AccountDeviceView(
        device_id=device.id,
        platform_label=platform_labels.get(device.platform, "Устройство"),
        version_label=device.client_version or "Версия неизвестна",
        status_label=status_labels.get(device.status, "Состояние неизвестно"),
        last_seen_at=device.last_seen_at,
        current=is_current,
        can_revoke=device.status == "active" and not is_current,
    )


def account_session_view(
    session: AuthSession,
    *,
    current_session_id: UUID | None,
) -> AccountSessionView:
    provider_label = PROVIDER_LINK_LABELS.get(session.provider, "Способ входа")
    status_label = "Активна" if session.status == "active" else "Отозвана"
    current = session.id == current_session_id
    return AccountSessionView(
        session_id=session.id,
        provider_label=provider_label,
        status_label=status_label,
        last_seen_at=session.last_seen_at,
        expires_at=session.expires_at,
        current=current,
        can_revoke=session.status == "active" and not current,
    )


def account_settings_surface(
    *,
    profile: AccountProfileView | None = None,
    identities: Iterable[ExternalIdentity] = (),
    devices: Iterable[RegisteredDevice] = (),
    sessions: Iterable[AuthSession] = (),
    current_session_id: UUID | None = None,
    current_device_id: UUID | None = None,
    can_unlink_provider: Callable[[ExternalIdentity], bool] | None = None,
    unavailable: bool = False,
    account_close: AccountCloseView | None = None,
) -> AccountSettingsSurface:
    identity_rows = tuple(identities)
    return AccountSettingsSurface(
        profile=profile,
        providers=tuple(
            account_provider_view(
                identity,
                primary=index == 0,
                can_unlink=(can_unlink_provider(identity) if can_unlink_provider else False),
            )
            for index, identity in enumerate(identity_rows)
        ),
        devices=tuple(
            account_device_view(device, current_device_id=current_device_id) for device in devices
        ),
        sessions=tuple(
            account_session_view(session, current_session_id=current_session_id) for session in sessions
        ),
        unavailable=unavailable,
        account_close=account_close,
    )


STATUS_LABELS: dict[str, str] = {
    "local_only": "Сохранено на Mac",
    "uploading": "Отправляем",
    "submitted": "Обрабатывается",
    "processing": "Обрабатывается",
    "ready": "Готово",
    "partial": "Готово с замечаниями",
    "blocked": "Нужна помощь",
    "failed": "Нужна помощь",
    "unavailable": "Нужна помощь",
    "deleted_future": "Удаляется",
}

MEDIASCRIBE_SPEAKER_LABEL_RE = re.compile(r"^SPEAKER_\d{2,}$")

SORT_LABELS: dict[str, str] = {
    "updated_desc": "Недавно обновлённые",
    "updated_asc": "Давно обновлённые",
    "started_desc": "Сначала новые",
    "started_asc": "Сначала старые",
    "duration_desc": "Сначала длинные",
    "duration_asc": "Сначала короткие",
    "title_asc": "По названию",
}
SHORT_MONTH_LABELS = (
    "",
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
)

MeetingListTimeBasis = Literal["meeting", "updated"]


@dataclass(frozen=True, slots=True)
class MeetingListRowPresentation:
    display_title: str
    duration_label: str
    time_label: str
    media_kind: str
    media_label: str
    status_kind: str | None
    status_label: str | None
    progress_percent: int | None
    open_accessible_name: str
    content_readiness_label: str | None = None


CALENDAR_CONTEXT_OWNER_REASON_LABELS: dict[str, str] = {
    "private_free_busy_skipped": "Приватное событие пропущено",
    "all_day_skipped": "Событие на весь день пропущено",
    "selected_source_stale": "Данные календаря устарели",
    "latest_sync_failed": "Данные календаря устарели",
    "calendar_not_connected": "Календарь недоступен",
    "calendar_not_selected": "Календарь недоступен",
    "calendar_unavailable": "Календарь недоступен",
    "manual_upload_skipped": "Ручная загрузка не сопоставляется",
    "offline_or_unknown_skipped": "Офлайн-запись не сопоставляется",
    "no_matching_event": "Подходящая встреча не найдена",
    "weak_event_signal": "Подходящая встреча не найдена",
    "prestart_not_reached": "Запись завершилась до начала встречи",
    "user_declined": "Вы начали запись без календарного контекста",
    "user_cleared": "Контекст убран вами",
}

CALENDAR_CONTEXT_STATE_COPY: dict[str, dict[str, str]] = {
    "ru": {
        "matched_auto": "Из календаря",
        "matched_user": "Выбрано вами",
        "ambiguous": "Нужно выбрать встречу",
        "no_context": "Без календарного контекста",
        "declined_by_user": "Вы начали запись без календарного контекста",
        "cleared_by_user": "Контекст убран вами",
    },
    "en": {
        "matched_auto": "From calendar",
        "matched_user": "Selected by you",
        "ambiguous": "Choose a meeting",
        "no_context": "No calendar context",
        "declined_by_user": "You started recording without calendar context",
        "cleared_by_user": "Context removed by you",
    },
}

PLAYBACK_TERMINAL_REASON: dict[str, PlaybackPreparationReasonCode] = {
    "empty_source": "empty_source",
    "no_audio": "no_audio",
    "ambiguous_audio_tracks": "ambiguous_audio_tracks",
    "unsupported_container": "unsupported_media",
    "unsupported_codec": "unsupported_media",
    "encrypted_media": "encrypted_media",
    "corrupt_source": "corrupt_source",
    "stream_limit_exceeded": "limit_exceeded",
    "duration_limit_exceeded": "limit_exceeded",
    "source_size_limit_exceeded": "limit_exceeded",
    "source_missing": "source_missing",
    "source_mismatch": "source_mismatch",
}

PLAYBACK_REASON_COPY: dict[str, dict[str, str]] = {
    "ru": {
        "normalization_queued": "Аудио готовится автоматически",
        "normalization_running": "Аудио готовится автоматически",
        "normalization_publishing": "Завершаем подготовку аудио",
        "normalization_retry_wait": (
            "Подготовка занимает больше времени. GRAF продолжит автоматически"
        ),
        "reconciliation_pending": "GRAF автоматически восстанавливает подготовку аудио",
        "canonical_artifact_missing": "GRAF автоматически восстанавливает аудио",
        "canonical_ready": "Аудио готово",
        "access_denied": "Аудио недоступно",
        "empty_source": "В исходном файле нет данных",
        "no_audio": "В файле нет пригодной аудиодорожки",
        "ambiguous_audio_tracks": "В файле несколько равноправных аудиодорожек",
        "unsupported_media": "Формат или кодек файла не поддерживается",
        "encrypted_media": "Защищённый файл нельзя подготовить для воспроизведения",
        "corrupt_source": "Файл повреждён и не может быть воспроизведён",
        "limit_exceeded": "Файл превышает допустимые параметры",
        "source_missing": "Исходный файл больше не хранится в GRAF",
        "source_mismatch": "Целостность исходного файла не подтверждена",
        "meeting_deleting": "Аудио удаляется",
        "meeting_deleted": "Аудио удалено",
        "audio_purged": "Аудио удалено",
        "fallback": "Аудио недоступно",
    },
    "en": {
        "normalization_queued": "Audio is being prepared automatically",
        "normalization_running": "Audio is being prepared automatically",
        "normalization_publishing": "Finishing audio preparation",
        "normalization_retry_wait": (
            "Preparation is taking longer. GRAF will continue automatically"
        ),
        "reconciliation_pending": "GRAF is automatically recovering audio preparation",
        "canonical_artifact_missing": "GRAF is automatically recovering the audio",
        "canonical_ready": "Audio is ready",
        "access_denied": "Audio is unavailable",
        "empty_source": "The source file is empty",
        "no_audio": "The file has no usable audio track",
        "ambiguous_audio_tracks": "The file has multiple equally valid audio tracks",
        "unsupported_media": "The file format or codec is not supported",
        "encrypted_media": "Protected media cannot be prepared for playback",
        "corrupt_source": "The file is corrupt and cannot be played",
        "limit_exceeded": "The file exceeds supported limits",
        "source_missing": "The source file is no longer retained by GRAF",
        "source_mismatch": "Source file integrity could not be confirmed",
        "meeting_deleting": "Audio is being deleted",
        "meeting_deleted": "Audio was deleted",
        "audio_purged": "Audio was deleted",
        "fallback": "Audio is unavailable",
    },
}


def calendar_context_state_copy(state: str, *, locale: str = "ru") -> str:
    language = locale if locale in CALENDAR_CONTEXT_STATE_COPY else "ru"
    return CALENDAR_CONTEXT_STATE_COPY[language].get(
        state,
        CALENDAR_CONTEXT_STATE_COPY[language]["no_context"],
    )


def playback_terminal_reason(reason_code: str | None) -> PlaybackPreparationReasonCode:
    return PLAYBACK_TERMINAL_REASON.get(reason_code or "", "unsupported_media")


def playback_reason_copy(reason_code: str, *, locale: str = "ru") -> str:
    language = locale if locale in PLAYBACK_REASON_COPY else "ru"
    copy = PLAYBACK_REASON_COPY[language]
    return copy.get(reason_code, copy["fallback"])


PROCESSING_STATUSES = {
    ProcessingStatus.PENDING_PROCESSING.value,
    ProcessingStatus.STARTING.value,
    ProcessingStatus.WORKFLOW_STARTED.value,
    ProcessingStatus.SUBMITTING.value,
    ProcessingStatus.SUBMITTED.value,
    ProcessingStatus.POLLING.value,
    ProcessingStatus.IMPORTING.value,
}

GENERATED_MANUAL_UPLOAD_RE = re.compile(r"^manual[-_]upload(?:[-_][a-z0-9]+)+$", re.IGNORECASE)
GENERATED_CAPTURE_TITLE_RE = re.compile(
    r"^(?:current(?: display)? system audio|system audio|yandex telemost|zoom(?:\.us)?|meeting)"
    r"\s*-\s*\d{4}-\d{2}-\d{2}(?:[ T]\d{1,2}:\d{2})?$",
    re.IGNORECASE,
)
AUTHORITATIVE_TITLE_SOURCES = frozenset({"user_confirmed", "calendar", "upload_provided"})
CALENDAR_PROVIDER_UI: dict[str, tuple[str, str, str]] = {
    "caldav_yandex": (
        "Яндекс Календарь",
        "app_password",
        "Введите логин и пароль приложения из настроек Яндекса.",
    ),
    "caldav_mail_ru": (
        "Mail.ru Календарь",
        "app_password",
        "Введите логин и пароль приложения из настроек Mail.ru.",
    ),
    "exchange_ews": (
        "Exchange / Exchange Server / EWS",
        "provider_specific_limited",
        "Подключение может требовать настройки организации или администратора.",
    ),
    "bitrix24": (
        "Bitrix24",
        "provider_specific_limited",
        "Доступ зависит от прав пользователя и политики портала.",
    ),
    "custom_caldav_vk_workspace": (
        "VK WorkSpace / custom CalDAV",
        "manual_url",
        "CalDAV URL из настроек рабочего пространства.",
    ),
    "caldav_mailion_myoffice": (
        "Mailion / MyOffice",
        "manual_url",
        "CalDAV URL или готовая настройка провайдера из параметров организации.",
    ),
    "caldav_r7_office": (
        "R7-Office",
        "manual_url",
        "CalDAV URL из портала или настроек организации.",
    ),
    "caldav_communigate_pro": (
        "CommuniGate Pro",
        "manual_url",
        "CalDAV доступ зависит от прав почтового ящика и сервера.",
    ),
    "caldav_rupost": (
        "RuPost",
        "manual_url",
        "Синхронизация CalDAV зависит от конфигурации организации.",
    ),
    "caldav_nextcloud_sogo": (
        "Nextcloud / SOGo-like CalDAV",
        "manual_url",
        "CalDAV URL сервера и выбранные календари.",
    ),
    "custom_caldav": (
        "Другой CalDAV",
        "manual_url",
        "Пользователь указывает URL; синхронизация работает только на чтение, насколько это позволяет сервер.",
    ),
}

CALENDAR_METHOD_LABELS = {
    "app_password": "Пароль приложения",
    "manual_url": "Ручной CalDAV URL",
    "provider_specific_limited": "Может требовать администратора",
}

CALENDAR_PROVIDER_MARKS = {
    "caldav_yandex": "Я",
    "caldav_mail_ru": "@",
    "exchange_ews": "Ex",
    "bitrix24": "B24",
    "custom_caldav_vk_workspace": "VK",
    "caldav_mailion_myoffice": "My",
    "caldav_r7_office": "R7",
    "caldav_communigate_pro": "CP",
    "caldav_rupost": "RP",
    "caldav_nextcloud_sogo": "NC",
    "custom_caldav": "CV",
}

CALENDAR_BOUNDARY_COPY = (
    "GRAF читает выбранные будущие события календаря, чтобы показать встречи и предложить начать запись. "
    "GRAF не меняет события календаря, не отправляет письма и не рассылает саммари. "
    "Участники календаря не получают доступ к записи автоматически. "
    "Данные для подключения хранятся на сервере GRAF; приложение на Mac не хранит пароль календаря."
)

CALENDAR_AUTO_CONTEXT_BOUNDARY_COPY = (
    "Эти фильтры управляют подсказками и списком ближайших встреч. "
    "Приватные события и события на весь день не используются для "
    "автоматического контекста записи."
)

CALENDAR_BOUNDARY_ITEMS: tuple[tuple[str, str], ...] = (
    (
        "Только чтение",
        "Мы читаем выбранные будущие события. События календаря не меняются, приглашения не обновляются.",
    ),
    (
        "Доступы остаются у владельца",
        "Участники встречи не становятся получателями саммари и не получают доступ к записи автоматически.",
    ),
    (
        "Пароли не живут на Mac",
        "Пароли приложений и CalDAV-данные остаются на сервере GRAF. Приложение на Mac их не хранит.",
    ),
    (
        "Запись остается под контролем",
        "Календарь может показать подсказку, но GRAF не включает скрытую или автоматическую запись.",
    ),
)

CALENDAR_FORBIDDEN_ACTION_LABELS: tuple[str, ...] = (
    "не меняет события календаря",
    "не отправляет письма",
    "не рассылает саммари",
    "не выдает доступ участникам",
    "не включает автоматическую запись",
)

CALENDAR_NOTICE_COPY: dict[str, tuple[str, str, str]] = {
    "connect_success": (
        "Календарь подключен",
        "Теперь выберите конкретные календари. До выбора событий источник не влияет на подсказки.",
        "success",
    ),
    "connect_cancelled": (
        "Подключение отменено",
        "Источник не добавлен. Можно повторить подключение или продолжить ручную запись без календаря.",
        "warning",
    ),
    "connect_denied": (
        "Календарь не подключен",
        "Провайдер не дал доступ только для чтения. Проверьте разрешения или выберите другой способ подключения.",
        "warning",
    ),
    "connect_failed": (
        "Не удалось подключить календарь",
        "Мы скрыли технические детали ошибки. Проверьте данные подключения или попробуйте позже.",
        "error",
    ),
    "no_readable_calendars": (
        "Нет доступных для чтения календарей",
        "Источник подключен, но провайдер не вернул календари, которые можно читать. Проверьте права доступа.",
        "warning",
    ),
    "policy_limited": (
        "Ограничено политикой организации",
        "Некоторые способы подключения или календари может включить только администратор организации.",
        "warning",
    ),
    "provider_limited": (
        "Есть ограничение провайдера",
        "Для этого провайдера могут понадобиться настройки организации. GRAF все равно работает только на чтение.",
        "warning",
    ),
    "selection_saved": (
        "Выбор календарей сохранен",
        "Будущие встречи и подсказки будут использовать только выбранные календари.",
        "success",
    ),
    "selection_empty": (
        "Календари не выбраны",
        "Источник остается подключенным, но не влияет на будущие встречи и подсказки.",
        "warning",
    ),
    "preferences_saved": (
        "Настройки сохранены",
        "Будущие подсказки и preview будут учитывать выбранные типы событий. Ручная запись остается доступной.",
        "success",
    ),
    "sync_accepted": (
        "Синхронизация поставлена в очередь",
        "Мы приняли запрос и обновим состояние источника после безопасной проверки провайдера. Не нужно ждать на этом экране.",
        "success",
    ),
    "sync_already_running": (
        "Синхронизация уже идет",
        "Повторный запуск не нужен. Текущая синхронизация продолжит работу.",
        "warning",
    ),
    "sync_reconnect_required": (
        "Нужно действие",
        "Переподключите календарь или обновите доступ. Детали ошибки скрыты безопасно.",
        "warning",
    ),
    "sync_unavailable": (
        "Синхронизация недоступна",
        "Источник отключен или ограничен политикой. Ручная запись остается доступной.",
        "warning",
    ),
    "sync_failed": (
        "Синхронизация не запущена",
        "Не удалось безопасно начать синхронизацию. Попробуйте позже или переподключите календарь.",
        "error",
    ),
    "disconnect_success": (
        "Календарь отключен",
        "Будущая синхронизация остановлена, данные подключения удалены или отозваны там, где это контролирует GRAF.",
        "success",
    ),
    "disconnect_partial": (
        "Отключение выполнено частично",
        "Будущая синхронизация остановлена. Часть внешнего отзыва доступа может зависеть от провайдера или администратора.",
        "warning",
    ),
    "disconnect_failed": (
        "Не удалось отключить календарь",
        "Мы скрыли технические детали ошибки. Попробуйте позже или обратитесь к администратору.",
        "error",
    ),
}


@dataclass(frozen=True)
class CalendarBoundaryItemView:
    label: str
    body: str


@dataclass(frozen=True)
class CalendarSettingsNoticeView:
    code: str
    title: str
    body: str
    tone: str


@dataclass(frozen=True)
class CalendarDisconnectConfirmationView:
    title: str = "Отключить календарь?"
    future_sync_copy: str = "Будущая синхронизация из этого источника остановится, и календарь перестанет влиять на подсказки."
    credential_copy: str = (
        "Данные подключения будут удалены или отозваны там, где это контролирует GRAF."
    )
    retention_copy: str = (
        "Уже связанный контекст встреч живет по политике хранения встречи. "
        "GRAF не обещает удалить данные вне своего контроля."
    )
    confirm_label: str = "Отключить источник"
    cancel_label: str = "Оставить подключенным"


@dataclass(frozen=True)
class CalendarSettingsProviderPreset:
    provider_family: str
    label: str
    mark: str
    method_category: str
    method_label: str
    action_label: str
    credential_label: str | None
    url_label: str | None
    limitation_copy: str | None
    explanation: str


@dataclass(frozen=True)
class CalendarSettingsPreferencesView:
    join_prompt_enabled: bool = True
    record_prompt_enabled: bool = True
    show_upcoming_time: bool = True
    show_upcoming_title: bool = True
    include_events_without_participants: bool = False
    include_events_without_link_or_location: bool = False
    include_all_day_events: bool = False
    include_private_free_busy_prompt_candidates: bool = False
    join_prompt_label: str = "Напоминать за 1 минуту до встречи с предложением подключиться"
    record_prompt_label: str = "Предлагать начать запись в момент старта встречи"
    disabled_auto_record_label: str = "Больше не спрашивать и записывать автоматически"
    disabled_auto_record_copy: str = (
        "Автоматическая запись пока недоступна. Если такое поведение понадобится, "
        "его нужно включать отдельной безопасной настройкой."
    )
    prompt_policy_copy: str = "Если политика организации ограничит подсказки, настройка останется видимой и объяснит ограничение."
    overlap_prompt_copy: str = (
        "Если несколько выбранных событий идут одновременно, GRAF попросит выбрать событие "
        "или продолжить без календарного контекста."
    )
    manual_recording_copy: str = "Ручной старт и стоп записи остаются доступны всегда."


@dataclass(frozen=True)
class SelectableCalendarView:
    calendar_id: str
    display_label: str
    selected: bool
    selectable: bool
    visibility: str
    visibility_label: str
    color: str | None = None


@dataclass(frozen=True)
class CalendarSourceSettingsView:
    source_id: str
    provider_family: str
    provider_label: str
    provider_mark: str
    safe_account_label: str
    connection_state: str
    connection_state_label: str
    sync_health_state: str
    sync_health_label: str
    sync_recovery_label: str
    selected_calendar_count: int
    readable_calendar_count: int
    last_successful_sync_label: str
    safe_error_message: str | None
    calendars: tuple[SelectableCalendarView, ...]
    disconnect_confirmation: CalendarDisconnectConfirmationView


@dataclass(frozen=True)
class UpcomingPreviewItemView:
    event_id: str
    title: str
    title_state: str
    starts_at: datetime
    ends_at: datetime
    source_ids: tuple[str, ...]
    meeting_link_present: bool
    calendar_labels: tuple[str, ...] = ()
    source_labels: tuple[str, ...] = ()
    duplicate_source_count: int = 1
    sync_confidence_state: str = "current"


@dataclass(frozen=True)
class OverlapConflictGroupView:
    conflict_id: str
    overlap_starts_at: datetime
    overlap_ends_at: datetime
    events: tuple[UpcomingPreviewItemView, ...]


@dataclass(frozen=True)
class CalendarSettingsSurfaceView:
    breadcrumb: tuple[str, ...]
    title: str
    subtitle: str
    read_only_boundary_copy: str
    auto_context_boundary_copy: str
    boundary_items: tuple[CalendarBoundaryItemView, ...]
    forbidden_action_labels: tuple[str, ...]
    notices: tuple[CalendarSettingsNoticeView, ...]
    providers: tuple[CalendarSettingsProviderPreset, ...]
    sources: tuple[CalendarSourceSettingsView, ...]
    preferences: CalendarSettingsPreferencesView
    selected_calendar_count_total: int = 0
    preview: tuple[UpcomingPreviewItemView, ...] = ()
    conflicts: tuple[OverlapConflictGroupView, ...] = ()
    preview_empty_reason: str = "Пока нет ближайших событий из выбранных календарей."
    loading_state_copy: str = "Во время загрузки настроек ручная запись остается доступной."
    unavailable_state_copy: str = "Если настройки календарей временно недоступны, секреты не показываются, ручная запись остается доступной."
    policy_constrained_copy: str = "Если настройка ограничена политикой организации, интерфейс покажет причину и безопасное следующее действие."
    no_readable_calendars_copy: str = (
        "Источник подключен, но доступных для чтения календарей пока нет."
    )
    no_selected_calendars_copy: str = (
        "Календари не выбраны: источник подключен, но не влияет на будущие встречи и подсказки."
    )
    no_matching_events_copy: str = "Нет будущих событий, которые подходят под выбранные настройки."
    private_free_busy_copy: str = "Private/free-busy события показываются без названия, ссылок, участников, описания и вложений."
    empty_state_title: str = "Календари пока не подключены"
    empty_state_body: str = "Подключите источник календаря, затем выберите календари. Пока календарь не выбран, встречи из него не подтягиваются."

    @property
    def source_count_word(self) -> str:
        return _russian_count_word(len(self.sources), "источник", "источника", "источников")

    @property
    def selected_calendar_count_total_word(self) -> str:
        return _russian_count_word(
            self.selected_calendar_count_total,
            "календарь",
            "календаря",
            "календарей",
        )


def calendar_provider_presets(
    provider_payloads: Iterable[dict[str, object]],
) -> tuple[CalendarSettingsProviderPreset, ...]:
    presets = []
    for payload in provider_payloads:
        family = str(payload.get("provider_family") or "")
        provider_copy = CALENDAR_PROVIDER_UI.get(family)
        if provider_copy is None:
            continue
        label, method, explanation = provider_copy
        presets.append(
            CalendarSettingsProviderPreset(
                provider_family=family,
                label=label,
                mark=CALENDAR_PROVIDER_MARKS.get(family, label[:2]),
                method_category=method,
                method_label=CALENDAR_METHOD_LABELS.get(
                    method, "Способ подключения зависит от провайдера"
                ),
                action_label=calendar_provider_action_label(method),
                credential_label=calendar_provider_credential_label(method),
                url_label="CalDAV URL" if method == "manual_url" else None,
                limitation_copy=calendar_provider_limitation_copy(
                    method, payload.get("capability_state") or {}
                ),
                explanation=explanation,
            )
        )
    return tuple(presets)


def _russian_count_word(value: int, one: str, few: str, many: str) -> str:
    normalized = abs(value)
    if 11 <= normalized % 100 <= 14:
        return many
    if normalized % 10 == 1:
        return one
    if 2 <= normalized % 10 <= 4:
        return few
    return many


def calendar_settings_preferences_view(
    preference: CalendarSettingsPreference | None,
) -> CalendarSettingsPreferencesView:
    if preference is None:
        return CalendarSettingsPreferencesView()
    return CalendarSettingsPreferencesView(
        join_prompt_enabled=preference.join_prompt_enabled,
        record_prompt_enabled=preference.record_prompt_enabled,
        show_upcoming_time=preference.show_upcoming_time,
        show_upcoming_title=preference.show_upcoming_title,
        include_events_without_participants=preference.include_events_without_participants,
        include_events_without_link_or_location=preference.include_events_without_link_or_location,
        include_all_day_events=preference.include_all_day_events,
        include_private_free_busy_prompt_candidates=preference.include_private_free_busy_prompt_candidates,
    )


def calendar_settings_surface(
    *,
    provider_payloads: Iterable[dict[str, object]],
    sources: Iterable[CalendarSource],
    calendars_by_source: dict[object, list[ExternalCalendar]] | None = None,
    preference: CalendarSettingsPreference | None = None,
    preview_events: Iterable[CalendarEventSnapshot] = (),
    notice_codes: Iterable[str] = (),
    now: datetime | None = None,
) -> CalendarSettingsSurfaceView:
    calendars_by_source = calendars_by_source or {}
    source_rows = tuple(sources)
    preferences = calendar_settings_preferences_view(preference)
    preview_event_rows = tuple(preview_events)
    rendered_sources = tuple(
        calendar_source_settings_view(
            source,
            calendars=calendars_by_source.get(source.id, []),
            now=now,
        )
        for source in source_rows
    )
    source_labels_by_id = {
        source.id: safe_calendar_label(source.provider_label, fallback=source.provider_family)
        for source in source_rows
    }
    source_sync_by_id = {
        source.id: calendar_sync_health_state(source, now=now) for source in source_rows
    }
    calendar_labels_by_id = {
        calendar.id: safe_calendar_label(calendar.display_label, fallback="Календарь")
        for calendars in calendars_by_source.values()
        for calendar in calendars
    }
    has_selected_calendar = any(source.selected_calendar_count > 0 for source in rendered_sources)
    return CalendarSettingsSurfaceView(
        breadcrumb=("Настройки", "Интеграции", "Календари"),
        title="Календари",
        subtitle="Подключите источник, выберите календари и получите подсказку перед встречей.",
        read_only_boundary_copy=CALENDAR_BOUNDARY_COPY,
        auto_context_boundary_copy=CALENDAR_AUTO_CONTEXT_BOUNDARY_COPY,
        boundary_items=calendar_boundary_items(),
        forbidden_action_labels=CALENDAR_FORBIDDEN_ACTION_LABELS,
        notices=calendar_settings_notices(notice_codes),
        providers=calendar_provider_presets(provider_payloads),
        sources=rendered_sources,
        preferences=preferences,
        selected_calendar_count_total=sum(
            source.selected_calendar_count for source in rendered_sources
        ),
        preview=preview_items(
            preview_event_rows,
            source_labels_by_id=source_labels_by_id,
            calendar_labels_by_id=calendar_labels_by_id,
            source_sync_by_id=source_sync_by_id,
        ),
        conflicts=overlap_conflict_groups(preview_event_rows, at=now or datetime.now(UTC)),
        preview_empty_reason=calendar_preview_empty_reason(
            has_sources=bool(source_rows),
            has_selected_calendar=has_selected_calendar,
            has_matching_events=bool(preview_event_rows),
        ),
    )


def calendar_source_settings_view(
    source: CalendarSource,
    *,
    calendars: Iterable[ExternalCalendar] = (),
    now: datetime | None = None,
) -> CalendarSourceSettingsView:
    calendar_rows = list(calendars)
    safe_labels = [
        safe_calendar_label(calendar.display_label, fallback="Календарь")
        for calendar in calendar_rows
    ]
    duplicate_labels = {label for label in safe_labels if safe_labels.count(label) > 1}
    calendar_views = tuple(
        selectable_calendar_view(calendar, duplicate_label=safe_label in duplicate_labels)
        for calendar, safe_label in zip(calendar_rows, safe_labels, strict=True)
    )
    provider_label = CALENDAR_PROVIDER_UI.get(
        source.provider_family, (source.provider_label or source.provider_family, "", "")
    )[0]
    readable_count = sum(1 for calendar in calendar_views if calendar.selectable)
    selected_count = sum(
        1 for calendar in calendar_views if calendar.selected and calendar.selectable
    )
    sync_health_state = calendar_sync_health_state(source, now=now)
    connection_state = calendar_connection_state(
        source, selected_count=selected_count, readable_count=readable_count
    )
    return CalendarSourceSettingsView(
        source_id=str(source.id),
        provider_family=source.provider_family,
        provider_label=provider_label,
        provider_mark=CALENDAR_PROVIDER_MARKS.get(source.provider_family, provider_label[:2]),
        safe_account_label=safe_calendar_label(
            source.provider_label or provider_label, fallback=provider_label
        ),
        connection_state=connection_state,
        connection_state_label=calendar_connection_state_label(connection_state),
        sync_health_state=sync_health_state,
        sync_health_label=calendar_sync_health_label(sync_health_state),
        sync_recovery_label=calendar_sync_recovery_label(sync_health_state),
        selected_calendar_count=selected_count,
        readable_calendar_count=readable_count,
        last_successful_sync_label=calendar_sync_time_label(source.last_successful_sync_at),
        safe_error_message=safe_calendar_error_message(source.last_safe_error_code),
        calendars=calendar_views,
        disconnect_confirmation=CalendarDisconnectConfirmationView(),
    )


def selectable_calendar_view(
    calendar: ExternalCalendar, *, duplicate_label: bool = False
) -> SelectableCalendarView:
    selectable = calendar.visibility in SELECTABLE_CALENDAR_VISIBILITIES
    selected = calendar.selected and selectable
    label = safe_calendar_label(calendar.display_label, fallback="Календарь")
    if duplicate_label:
        detail = safe_calendar_label(
            calendar.owner_display_name or calendar.provider_calendar_id,
            fallback="другой календарь",
        )
        if detail == label:
            detail = "другой календарь"
        label = f"{label} - {detail}"
    return SelectableCalendarView(
        calendar_id=calendar.provider_calendar_id,
        display_label=label,
        selected=selected,
        selectable=selectable,
        visibility=calendar.visibility,
        visibility_label=calendar_visibility_label(calendar.visibility),
        color=calendar.color if _safe_color(calendar.color) else None,
    )


def calendar_visibility_label(visibility: str) -> str:
    labels = {
        "available": "доступен",
        "selected": "выбран",
        "hidden": "скрыт провайдером",
        "unavailable": "недоступен",
        "private": "private/free-busy",
        "shared": "общий календарь",
        "delegated": "делегированный календарь",
        "removed": "удален у провайдера",
        "disconnected": "источник отключен",
    }
    return labels.get(visibility, "состояние неизвестно")


def calendar_connection_state(
    source: CalendarSource, *, selected_count: int, readable_count: int
) -> str:
    if source.disconnected_at is not None or source.connection_state == "disconnected":
        return "disconnected"
    if source.connection_state in {"disabled", "disabled_by_policy"}:
        return "disabled_by_policy"
    if source.connection_state in {"connecting", "disconnecting", "error", "needs_action"}:
        return source.connection_state
    if readable_count == 0:
        return "no_readable_calendars"
    if readable_count > 0 and selected_count == 0:
        return "connected_selection_needed"
    return "connected"


def calendar_connection_state_label(state: str) -> str:
    labels = {
        "connected": "Подключено",
        "connected_selection_needed": "Нужно выбрать календари",
        "connecting": "Подключаем",
        "needs_action": "Нужно действие",
        "error": "Ошибка подключения",
        "disabled_by_policy": "Отключено политикой",
        "disconnecting": "Отключаем",
        "disconnected": "Отключено",
        "no_readable_calendars": "Нет календарей для чтения",
    }
    return labels.get(state, "Состояние неизвестно")


def calendar_sync_health_state(source: CalendarSource, *, now: datetime | None = None) -> str:
    if source.disconnected_at is not None or source.connection_state == "disconnected":
        return "disconnected"
    if source.sync_state in {
        "syncing",
        "queued",
        "never_synced",
        "partial_sync",
        "rate_limited",
        "credential_failed",
        "failed_closed",
    }:
        return source.sync_state
    if source.sync_state in {"failed", "stale", "error", "provider_unavailable"}:
        return "stale"
    if source.last_successful_sync_at is not None:
        current = now or datetime.now(UTC)
        synced_at = source.last_successful_sync_at
        if synced_at.tzinfo is None:
            synced_at = synced_at.replace(tzinfo=UTC)
        if current - synced_at > timedelta(hours=24):
            return "stale"
    return "synced" if source.last_successful_sync_at else "never_synced"


def calendar_sync_time_label(value: datetime | None) -> str:
    if value is None:
        return "успешной синхронизации еще не было"
    return value.strftime("%Y-%m-%d %H:%M UTC")


def calendar_sync_health_label(state: str) -> str:
    labels = {
        "never_synced": "успешной синхронизации еще не было",
        "queued": "синхронизация в очереди",
        "syncing": "синхронизация идет",
        "synced": "синхронизация актуальна",
        "partial_sync": "синхронизация частичная",
        "stale": "синхронизация устарела",
        "provider_unavailable": "провайдер недоступен",
        "rate_limited": "провайдер ограничил синхронизацию",
        "credential_failed": "нужно переподключить",
        "failed_closed": "синхронизация остановлена безопасно",
        "disconnected": "источник отключен",
    }
    return labels.get(state, "состояние синхронизации неизвестно")


def calendar_sync_recovery_label(state: str) -> str:
    labels = {
        "never_synced": "Запустите синхронизацию после выбора календарей.",
        "queued": "Дождитесь текущей синхронизации.",
        "syncing": "Дождитесь текущей синхронизации.",
        "partial_sync": "Запустите синхронизацию еще раз или проверьте источник.",
        "stale": "Запустите синхронизацию вручную.",
        "provider_unavailable": "Попробуйте позже.",
        "rate_limited": "Попробуйте позже.",
        "credential_failed": "Переподключите календарь.",
        "failed_closed": "Проверьте подключение или переподключите источник.",
        "disconnected": "Подключите источник заново.",
    }
    return labels.get(
        state, "Если встреч не видно, запустите синхронизацию или переподключите источник."
    )


def safe_calendar_error_message(code: str | None) -> str | None:
    if not code:
        return None
    messages = {
        "credential_failed": "Нужно переподключить календарь.",
        "invalid_credentials": "Нужно переподключить календарь.",
        "tenant_policy_denied": "Подключение ограничено политикой организации.",
        "provider_timeout": "Провайдер календаря не ответил вовремя. Попробуйте позже.",
        "rate_limited": "Провайдер временно ограничил синхронизацию. Попробуйте позже.",
        "provider_unavailable": "Провайдер календаря временно недоступен.",
        "calendar_sync_stale": "Синхронизация устарела; встречи могут быть неактуальны.",
    }
    return messages.get(code, "Синхронизация не прошла. Проверьте подключение или повторите позже.")


def calendar_provider_action_label(method_category: str) -> str:
    labels = {
        "app_password": "Подключить",
        "manual_url": "Подключить",
        "provider_specific_limited": "Проверить подключение",
    }
    return labels.get(method_category, "Подключить календарь")


def calendar_provider_credential_label(method_category: str) -> str | None:
    if method_category == "app_password":
        return "Пароль приложения"
    if method_category == "manual_url":
        return "Пароль приложения или секрет CalDAV"
    return None


def calendar_provider_limitation_copy(method_category: str, capability_state: object) -> str | None:
    if method_category == "provider_specific_limited":
        return "Может понадобиться настройка организации или администратор."
    if isinstance(capability_state, dict) and "admin_policy_dependent" in set(
        capability_state.values()
    ):
        return "Часть возможностей зависит от политики организации."
    if method_category == "manual_url":
        return "Если URL или пароль неверны, мы покажем безопасную ошибку без деталей провайдера."
    return None


def calendar_boundary_items() -> tuple[CalendarBoundaryItemView, ...]:
    return tuple(
        CalendarBoundaryItemView(label=label, body=body) for label, body in CALENDAR_BOUNDARY_ITEMS
    )


def calendar_settings_notices(
    notice_codes: Iterable[str],
) -> tuple[CalendarSettingsNoticeView, ...]:
    notices = []
    seen: set[str] = set()
    for code in notice_codes:
        if code in seen:
            continue
        copy = CALENDAR_NOTICE_COPY.get(code)
        if copy is None:
            continue
        title, body, tone = copy
        notices.append(CalendarSettingsNoticeView(code=code, title=title, body=body, tone=tone))
        seen.add(code)
    return tuple(notices)


def safe_calendar_label(raw: str | None, *, fallback: str) -> str:
    return safe_title_candidate(raw) or fallback


def preview_items(
    events: Iterable[CalendarEventSnapshot],
    *,
    source_labels_by_id: dict[object, str] | None = None,
    calendar_labels_by_id: dict[object, str] | None = None,
    source_sync_by_id: dict[object, str] | None = None,
) -> tuple[UpcomingPreviewItemView, ...]:
    source_labels_by_id = source_labels_by_id or {}
    calendar_labels_by_id = calendar_labels_by_id or {}
    source_sync_by_id = source_sync_by_id or {}
    return tuple(
        upcoming_preview_item(
            group[0],
            source_ids=tuple(str(event.calendar_source_id) for event in group),
            source_labels=tuple(
                source_labels_by_id.get(event.calendar_source_id, "Календарь") for event in group
            ),
            calendar_labels=tuple(
                calendar_labels_by_id.get(event.external_calendar_id, "Календарь")
                for event in group
            ),
            duplicate_source_count=len(group),
            sync_confidence_state=calendar_preview_sync_confidence(
                source_sync_by_id.get(event.calendar_source_id, "current") for event in group
            ),
        )
        for group in calendar_preview_groups(events)
    )


def calendar_preview_groups(
    events: Iterable[CalendarEventSnapshot],
) -> tuple[tuple[CalendarEventSnapshot, ...], ...]:
    groups: dict[str, list[CalendarEventSnapshot]] = defaultdict(list)
    indexed_events = list(enumerate(events))
    for _, event in sorted(indexed_events, key=lambda item: (_as_utc(item[1].starts_at), item[0])):
        groups[calendar_duplicate_group_key(event)].append(event)
    return tuple(tuple(group) for group in groups.values())


def calendar_preview_sync_confidence(states: Iterable[str]) -> str:
    state_set = set(states)
    if state_set & {
        "stale",
        "credential_failed",
        "failed_closed",
        "provider_unavailable",
        "rate_limited",
        "disconnected",
    }:
        return "stale"
    if state_set & {"queued", "syncing", "never_synced", "partial_sync"}:
        return "updating"
    return "current"


def calendar_preview_empty_reason(
    *,
    has_sources: bool,
    has_selected_calendar: bool,
    has_matching_events: bool,
) -> str:
    if not has_sources:
        return "Подключите источник календаря, чтобы увидеть будущие встречи."
    if not has_selected_calendar:
        return "Выберите хотя бы один календарь: без выбора будущие встречи и подсказки не подтягиваются."
    if not has_matching_events:
        return "Нет будущих событий, которые подходят под выбранные настройки."
    return "Пока нет ближайших событий из выбранных календарей."


def upcoming_preview_item(
    event: CalendarEventSnapshot,
    *,
    source_ids: tuple[str, ...] | None = None,
    source_labels: tuple[str, ...] = (),
    calendar_labels: tuple[str, ...] = (),
    duplicate_source_count: int = 1,
    sync_confidence_state: str = "current",
) -> UpcomingPreviewItemView:
    title = safe_calendar_label(
        event.title if event.safe_to_show_in_list else None, fallback="Скрытое событие"
    )
    title_state = (
        "available"
        if event.safe_to_show_in_list and title != "Скрытое событие"
        else event.privacy_class
    )
    meeting_link_present = bool((event.conference_summary_json or {}).get("meeting_link_present"))
    if _is_private_or_free_busy(event):
        meeting_link_present = False
    return UpcomingPreviewItemView(
        event_id=str(event.id),
        title=title,
        title_state=title_state,
        starts_at=event.starts_at,
        ends_at=event.ends_at,
        source_ids=source_ids or (str(event.calendar_source_id),),
        meeting_link_present=meeting_link_present,
        calendar_labels=calendar_labels,
        source_labels=source_labels,
        duplicate_source_count=duplicate_source_count,
        sync_confidence_state=sync_confidence_state,
    )


def overlap_conflict_groups(
    events: Iterable[CalendarEventSnapshot], *, at: datetime
) -> tuple[OverlapConflictGroupView, ...]:
    current = [
        event
        for event in dedupe_calendar_events(events)
        if _as_utc(event.starts_at) <= _as_utc(at) < _as_utc(event.ends_at)
    ]
    if len(current) < 2:
        return ()
    overlap_start = max(_as_utc(event.starts_at) for event in current)
    overlap_end = min(_as_utc(event.ends_at) for event in current)
    return (
        OverlapConflictGroupView(
            conflict_id="overlap:" + ",".join(sorted(str(event.id) for event in current)),
            overlap_starts_at=overlap_start,
            overlap_ends_at=overlap_end,
            events=tuple(upcoming_preview_item(event) for event in current),
        ),
    )


def _safe_color(value: str | None) -> bool:
    return bool(value and re.fullmatch(r"#[0-9a-fA-F]{6}", value))


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _event_participant_count(event: CalendarEventSnapshot) -> int:
    conference = event.conference_summary_json or {}
    provider_extras = event.provider_extras_json or {}
    raw = conference.get("participant_count", provider_extras.get("participant_count", 0))
    try:
        return max(int(raw or 0), 0)
    except (TypeError, ValueError):
        return 0


def _is_private_or_free_busy(event: CalendarEventSnapshot) -> bool:
    return (
        event.privacy_class in {"private", "free_busy", "free_busy_only"}
        or not event.safe_to_show_in_list
    )


@dataclass(frozen=True)
class CabinetNavigationItem:
    id: str
    label: str
    href: str
    icon: str


@dataclass(frozen=True)
class CabinetNavigationModel:
    active: str
    items: tuple[CabinetNavigationItem, ...]


def cabinet_navigation(
    *, active: str = "meetings", embedded: bool = False
) -> CabinetNavigationModel:
    meetings_href = "/desktop/meetings" if embedded else "/meetings"
    shared_with_me_href = "/desktop/shared-with-me" if embedded else "/shared-with-me"
    settings_href = "/desktop/settings" if embedded else "/settings"
    items = (
        CabinetNavigationItem("meetings", "Мои встречи", meetings_href, "calendar-days"),
        CabinetNavigationItem(
            "shared-with-me", "Поделились со мной", shared_with_me_href, "users-round"
        ),
        CabinetNavigationItem("settings", "Настройки", settings_href, "settings"),
    )
    item_ids = {item.id for item in items}
    return CabinetNavigationModel(
        active=active if active in item_ids else "meetings",
        items=items,
    )


@dataclass(frozen=True, slots=True)
class SharedWithMeMeetingItem:
    title: str
    time_label: str
    duration_label: str
    status_label: str
    access_label: str
    href: str


@dataclass(frozen=True, slots=True)
class SettingsCategoryView:
    id: str
    label: str
    scope_label: str
    href: str
    group_label: str
    icon: str


def settings_category_navigation(
    *,
    embedded: bool = False,
    active: str = "overview",
) -> tuple[SettingsCategoryView, ...]:
    base = "/desktop/settings" if embedded else "/settings"
    definitions = (
        (
            "recording",
            "Запись",
            "На этом Mac",
            "/recording",
            "Встречи",
            "video",
        ),
        (
            "summaries",
            "Итоги",
            "В этом пространстве",
            "/summaries",
            "Встречи",
            "transcript",
        ),
        (
            "calendar",
            "Календари",
            "Личная настройка",
            "/integrations/calendar",
            "Встречи",
            "calendar-days",
        ),
        (
            "workspace",
            "Пространство",
            "В этом пространстве",
            "/workspace",
            "Рабочее пространство",
            "users-round",
        ),
        (
            "account",
            "Аккаунт и безопасность",
            "Личная настройка",
            "/account",
            "Аккаунт",
            "settings",
        ),
    )
    definitions += (
        ("notifications", "Уведомления", "Личная настройка", "/notifications", "Аккаунт", "bell"),
        ("billing", "Тариф и оплата", "В этом пространстве", "/billing", "Оплата", "activity"),
    )
    return tuple(
        SettingsCategoryView(
            id=category_id,
            label=label,
            scope_label=scope_label,
            href="/billing" if embedded and category_id == "billing" else base + suffix,
            group_label=group_label,
            icon=icon,
        )
        for category_id, label, scope_label, suffix, group_label, icon in definitions
    )


def source_role_label(source_role: str | None) -> SourceRoleView:
    normalized = (source_role or "").lower()
    if normalized in {"mic", "microphone", "local_microphone"}:
        return "local_microphone"
    if normalized in {"incoming", "system", "incoming_system"}:
        return "incoming_system"
    if normalized in {"mixed", "media", "canonical_mixed"}:
        return "canonical_mixed"
    return "unknown"


def format_timestamp(seconds: Decimal | float | int) -> str:
    total_seconds = max(0, int(float(seconds)))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, second = divmod(remainder, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{second:02d}"
    return f"{minutes:02d}:{second:02d}"


def format_duration(seconds: int) -> str:
    minutes, second = divmod(max(0, seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours} ч {minutes} мин" if minutes else f"{hours} ч"
    if minutes:
        return f"{minutes} мин"
    return f"{second} с"


def date_label(item: MeetingListItem) -> str:
    if item.started_at is None:
        return "Без даты"
    return short_date_label(
        item.started_at,
        timezone_offset_minutes=item.recording_display_timezone_offset_minutes,
    )


def meeting_list_time_label(
    value: datetime | None,
    *,
    timezone_offset_minutes: int | None,
    time_basis: MeetingListTimeBasis,
) -> str:
    if value is None:
        return "Без даты"
    localized = _localized_datetime(
        value,
        timezone_offset_minutes=timezone_offset_minutes,
    )
    prefix = "Обновлено " if time_basis == "updated" else ""
    return f"{prefix}{localized.day} {SHORT_MONTH_LABELS[localized.month]}, {localized:%H:%M}"


def meeting_time_label(item: MeetingListItem, *, time_basis: MeetingListTimeBasis) -> str:
    value = item.updated_at if time_basis == "updated" else item.started_at
    return meeting_list_time_label(
        value,
        timezone_offset_minutes=item.recording_display_timezone_offset_minutes,
        time_basis=time_basis,
    )


def _localized_datetime(
    value: datetime,
    *,
    timezone_offset_minutes: int | None,
) -> datetime:
    localized = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    if timezone_offset_minutes is not None and -14 * 60 <= timezone_offset_minutes <= 14 * 60:
        localized = localized.astimezone(timezone(timedelta(minutes=timezone_offset_minutes)))
    return localized


def short_date_label(
    value: datetime,
    *,
    timezone_offset_minutes: int | None = None,
) -> str:
    localized = _localized_datetime(
        value,
        timezone_offset_minutes=timezone_offset_minutes,
    )
    return f"{localized.day} {SHORT_MONTH_LABELS[localized.month]}"


def normalize_meeting_list_sort(
    sort: str | None,
    *,
    fallback: str = "started_desc",
) -> str:
    normalized_fallback = fallback if fallback in SORT_LABELS else "started_desc"
    return sort if sort in SORT_LABELS else normalized_fallback


def sort_label(sort: str) -> str:
    return SORT_LABELS.get(sort, SORT_LABELS["updated_desc"])


def meeting_list_row_presentation(
    item: MeetingListItem,
    *,
    time_basis: MeetingListTimeBasis,
) -> MeetingListRowPresentation:
    time = meeting_time_label(item, time_basis=time_basis)
    status_kind, status_copy, progress = _meeting_list_compact_status(item)
    source_title = item.title.strip()
    title = source_title or "Запись"
    open_name = f"Открыть встречу {title}"
    if title in {"Запись", "Загруженная запись"}:
        open_name = f"{open_name}, {time}"
    return MeetingListRowPresentation(
        display_title=title,
        duration_label=format_duration(item.duration_seconds),
        time_label=time,
        media_kind=meeting_media_kind(item),
        media_label=meeting_media_label(item),
        status_kind=status_kind,
        status_label=status_copy,
        progress_percent=progress,
        open_accessible_name=open_name,
        content_readiness_label=_meeting_list_content_readiness(item),
    )


def _meeting_list_content_readiness(item: MeetingListItem) -> str | None:
    if item.primary_action != "open" and item.status not in {"ready", "partial"}:
        return None
    transcript_ready = item.transcript_available
    outcomes_ready = item.notes_action_truth.source_basis == "stored_output"
    if transcript_ready and outcomes_ready:
        return "Расшифровка и итоги готовы"
    if transcript_ready:
        outcome_copy = (
            "итоги готовятся"
            if item.notes_action_truth.source_basis in {"processing_status", "policy_deferral"}
            else "итоги недоступны"
        )
        return f"Расшифровка готова · {outcome_copy}"
    if outcomes_ready:
        return "Итоги готовы · расшифровка недоступна"
    return "Расшифровка и итоги пока недоступны"


def _meeting_list_compact_status(
    item: MeetingListItem,
) -> tuple[
    str | None,
    str | None,
    int | None,
]:
    presentation_status = meeting_list_presentation_status(item)
    if presentation_status == "deleted_future":
        return "deleting", "Удаляется", None
    if presentation_status in {"blocked", "failed", "unavailable"}:
        return "failed", "Не удалось обработать", None
    upload = item.upload
    if item.calendar_context is not None and item.calendar_context.needs_owner_action:
        return "calendar_choice", "Нужен выбор", None
    if presentation_status == "local_only":
        return "saved_local", "Сохранено на Mac", None

    if upload is not None and upload.is_active:
        progress = upload.progress_percent
        trustworthy = (
            progress is not None
            and 0 <= progress < 100
            and upload.total_bytes > 0
            and 0 <= upload.uploaded_bytes <= upload.total_bytes
        )
        if trustworthy:
            return (
                "uploading_measured",
                f"Отправляем {progress}%",
                progress,
            )
        return "uploading", "Отправляем", None
    if presentation_status == "uploading":
        return "uploading", "Отправляем", None
    if presentation_status in {"submitted", "processing"}:
        return "processing", "Обрабатывается", None

    openable = item.primary_action == "open" or presentation_status in {"ready", "partial"}
    if openable and item.playback.state == "preparing":
        return "audio_preparing", "Аудио готовится", None
    if openable and item.playback.state in {"unavailable", "deleting", "deleted"}:
        return "without_audio", "Без аудио", None
    if presentation_status == "partial":
        return "limited", "Готово с ограничениями", None
    return None, None, None


def meeting_list_presentation_status(item: MeetingListItem) -> MeetingReviewStatus:
    if item.status == "deleted_future":
        return item.status
    if item._presentation_meeting_status in {
        MeetingStatus.ABORTED.value,
        MeetingStatus.EXPIRED.value,
    }:
        return "failed"
    if item.upload is not None and item.upload.status in {"failed", "aborted", "expired"}:
        return "failed"
    return item.status


def meeting_media_kind(item: MeetingListItem) -> str:
    if item.source == "manual_upload":
        return "upload"
    if item.source == "video_recording":
        return "video"
    has_audio = any(
        artifact.artifact_class == "audio" and artifact.state == "available"
        for artifact in item.artifacts
    )
    has_transcript = item.transcript_available or any(
        artifact.artifact_class == "transcript" and artifact.state == "available"
        for artifact in item.artifacts
    )
    if has_transcript and not has_audio:
        return "transcript"
    return "audio"


def meeting_media_label(item: MeetingListItem) -> str:
    return {
        "audio": "аудио",
        "video": "видео",
        "transcript": "транскрипт",
        "upload": "медиа",
    }[meeting_media_kind(item)]


def meeting_list_title(meeting: Meeting, *, source: str | None = None) -> str:
    title = safe_title_candidate(meeting.title)
    projected = safe_title(meeting, source=source)
    if title is None:
        return projected if projected == "Загруженная запись" else "Запись"
    if (
        meeting.title_source not in AUTHORITATIVE_TITLE_SOURCES
        and GENERATED_CAPTURE_TITLE_RE.fullmatch(title)
    ):
        return "Запись"
    if (
        projected == "Запись без названия"
        and meeting.title_source not in AUTHORITATIVE_TITLE_SOURCES
    ):
        return "Запись"
    if (
        meeting.title_source not in AUTHORITATIVE_TITLE_SOURCES
        and MEDIA_FILENAME_EXTENSION_RE.search(title)
    ):
        return _clean_file_title(title)
    return projected


def safe_title(meeting: Meeting, *, source: str | None = None) -> str:
    title = safe_title_candidate(meeting.title)
    if title:
        if meeting.title_source in AUTHORITATIVE_TITLE_SOURCES:
            return _authoritative_title(title)
        if GENERATED_MANUAL_UPLOAD_RE.fullmatch(title):
            return "Загруженная запись"
        if GENERATED_CAPTURE_TITLE_RE.fullmatch(title):
            return _generated_recording_title(meeting) or "Запись без названия"
        if LEGACY_SERIALIZED_MEDIA_FILENAME_EXTENSION_RE.search(title):
            return _clean_legacy_file_title(title)
        return media_filename_leaf(title) or "Запись без названия"

    if source == "manual_upload" or GENERATED_MANUAL_UPLOAD_RE.fullmatch(
        meeting.local_recording_id or ""
    ):
        return "Загруженная запись"
    return _generated_recording_title(meeting) or "Запись без названия"


def _authoritative_title(title: str) -> str:
    if title.startswith(("/", "\\")) or re.match(r"^[A-Za-z]:[/\\]", title):
        return re.split(r"[/\\]", title)[-1].strip() or "Запись без названия"
    return title


def _clean_file_title(title: str) -> str:
    return clean_media_filename_title(title) or "Загруженная запись"


def _clean_legacy_file_title(title: str) -> str:
    return clean_legacy_serialized_media_filename_title(title) or "Загруженная запись"


def _generated_recording_title(meeting: Meeting) -> str | None:
    started_at = meeting.started_at
    if started_at is None:
        return None
    started_at = _localized_datetime(
        started_at,
        timezone_offset_minutes=meeting.recording_display_timezone_offset_minutes,
    )
    return f"Запись {started_at.day} {SHORT_MONTH_LABELS[started_at.month]}, {started_at:%H:%M}"


def safe_title_candidate(raw: str | None) -> str | None:
    return safe_metadata_text(raw, max_length=500)


def transcript_available(result: ProcessingResult | None) -> bool:
    return bool(
        result is not None
        and result.status == ProcessingResultStatus.IMPORTED.value
        and result.transcript_status == ProcessingAvailabilityStatus.AVAILABLE.value
        and result.segment_count > 0
    )


def previous_recurring_meeting_readiness(
    meeting: Meeting,
    *,
    result: ProcessingResult | None,
    outcome_set: MeetingOutcomeSet | None,
) -> PreviousRecurringMeetingReadiness:
    """Project only bounded artifact readiness for an authorized predecessor."""

    notes_ready = bool(
        result is not None and result.summary_status == SummaryStatus.AVAILABLE.value
    ) or bool(
        outcome_set is not None
        and outcome_set.lifecycle_state == "active"
        and outcome_set.status in {"completed", "ready"}
        and outcome_set.summary_state == "available"
    )
    if notes_ready:
        return PreviousRecurringMeetingReadiness.NOTES_READY
    if transcript_available(result):
        return PreviousRecurringMeetingReadiness.TRANSCRIPT_READY
    if review_status(meeting, result=result, workflow=None) in {
        "uploading",
        "submitted",
        "processing",
        "partial",
    }:
        return PreviousRecurringMeetingReadiness.PROCESSING
    return PreviousRecurringMeetingReadiness.UNAVAILABLE


def diarization_available(result: ProcessingResult | None) -> bool:
    return bool(
        result is not None
        and result.status == ProcessingResultStatus.IMPORTED.value
        and result.diarization_status == ProcessingAvailabilityStatus.AVAILABLE.value
        and result.diarization_segment_count > 0
    )


def review_status(
    meeting: Meeting,
    *,
    result: ProcessingResult | None,
    workflow: ProcessingWorkflow | None,
) -> MeetingReviewStatus:
    if meeting_is_deleted_or_deleting(meeting):
        return "deleted_future"
    has_transcript = transcript_available(result)
    has_diarization = diarization_available(result)
    if has_transcript and has_diarization:
        return "ready"
    if has_transcript or has_diarization:
        return "partial"

    if meeting.status == MeetingStatus.DRAFT.value:
        return "local_only"
    if meeting.status == MeetingStatus.UPLOADING.value:
        return "uploading"
    if meeting.status in {MeetingStatus.FAILED.value, MeetingStatus.DEGRADED.value}:
        return "failed"

    lifecycle_status = workflow.status if workflow is not None else meeting.processing_status
    if lifecycle_status in PROCESSING_STATUSES:
        return "processing"
    if lifecycle_status == ProcessingStatus.NOT_SUBMITTED.value:
        return "submitted"
    if lifecycle_status == ProcessingStatus.BLOCKED.value:
        return "blocked"
    if lifecycle_status in {
        ProcessingStatus.FAILED_RETRYABLE.value,
        ProcessingStatus.FAILED_TERMINAL.value,
    }:
        return "failed"
    if lifecycle_status == ProcessingStatus.CANCELED.value:
        return "unavailable"

    return "unavailable"


def governance_summary(
    *,
    access: MeetingAccessState | None = None,
    artifacts: list[ArtifactEgressState] | None = None,
    content_exports: ContentExportCapabilityResponse | None = None,
    can_delete: bool = False,
) -> GovernanceActionSummary:
    access = access or owner_access_state()
    artifacts = artifacts or []
    download_available = any(
        artifact.artifact_class in {"audio", "transcript", "summary"}
        and artifact.state == "available"
        for artifact in artifacts
    )
    canonical_export_available = content_exports is not None and (
        content_exports.transcript.state == "available"
        or content_exports.summary.state in {"available", "partial"}
        or content_exports.combined.state == "available"
    )
    package_export_available = any(
        artifact.artifact_class == "package" and artifact.state == "available"
        for artifact in artifacts
    )
    export_available = canonical_export_available or package_export_available
    return GovernanceActionSummary(
        share=GovernanceActionState(
            state="available" if access.can_share else "disabled",
            label="Share",
            reason="Login-required sharing is available."
            if access.can_share
            else "Only permitted owners can manage sharing.",
            destructive=False,
        ),
        export=GovernanceActionState(
            state="available" if export_available and access.can_export else "disabled",
            label="Экспортировать…" if canonical_export_available else "Export package",
            reason="Canonical revision-pinned export is available."
            if canonical_export_available and access.can_export
            else "A policy-allowed export package is available."
            if export_available and access.can_export
            else "No policy-allowed canonical content export is available.",
            destructive=False,
        ),
        download=GovernanceActionState(
            state="available" if download_available and access.can_download else "disabled",
            label="Download",
            reason="Server-mediated artifact download is available."
            if download_available and access.can_download
            else "No policy-allowed artifact download is available.",
            destructive=False,
        ),
        retention=GovernanceActionState(
            state="planned",
            label="Retention policy planned",
            reason="Retention controls will show policy truth before activation.",
            destructive=False,
        ),
        delete=GovernanceActionState(
            state="available" if can_delete and access.state == "owner" else "disabled",
            label="Удалить встречу…",
            reason="Deletes meeting artifacts everywhere GRAF controls; retained observability remains."
            if can_delete and access.state == "owner"
            else "Deletion is available in the authorized meeting detail with the GRAF-controlled scope."
            if access.state == "owner"
            else "Only the meeting owner can delete this meeting.",
            destructive=True,
        ),
    )


def future_slots() -> list[SlotState]:
    return [
        SlotState(state="planned", label="Star", reason="Saved meetings are planned."),
        SlotState(state="planned", label="Tag", reason="Tags are planned."),
        SlotState(state="planned", label="Access", reason="Collaboration access is planned."),
        SlotState(state="planned", label="More", reason="More actions are planned."),
    ]


def slot_state(label: str) -> SlotState:
    return SlotState(state="planned", label=label, reason="Planned for a later feature slice.")


def summary_template_slot(
    outcome_set: MeetingOutcomeSet | None,
    *,
    personal_name: str | None = None,
    default_template_key: str = "graf-auto-v1",
    default_template_name: str | None = None,
) -> SlotState:
    template_key = (
        outcome_set.template_key
        if outcome_set is not None and outcome_set.template_key
        else default_template_key
    )
    definition = built_in_template_for_version(
        template_key,
        outcome_set.template_version
        if outcome_set is not None and outcome_set.template_version is not None
        else 1,
    )
    return SlotState(
        state="available",
        label=(
            definition.name
            if definition is not None
            else personal_name or default_template_name or "Личный формат"
        ),
        reason=template_key,
        template_id=outcome_set.template_id if outcome_set is not None else None,
        version=(
            outcome_set.template_version
            if outcome_set is not None and outcome_set.template_version is not None
            else definition.version
            if definition is not None
            else None
        ),
        template_version=(
            outcome_set.template_version
            if outcome_set is not None and outcome_set.template_version is not None
            else definition.version
            if definition is not None
            else None
        ),
    )


def build_list_item(
    meeting: Meeting,
    *,
    media_revision: MediaRevision | None = None,
    result: ProcessingResult | None,
    workflow: ProcessingWorkflow | None,
    access: MeetingAccessState | None = None,
    artifacts: list[ArtifactEgressState] | None = None,
    outcome_set: MeetingOutcomeSet | None = None,
    outcome_items: list[MeetingOutcomeItem] | None = None,
    upload: MeetingUploadProgressState | None = None,
    calendar_context: RecordingCalendarContextLink | None = None,
    previous_recurring_meeting: PreviousRecurringMeetingView | None = None,
    playback: PlaybackPreparationState | None = None,
) -> MeetingListItem:
    status = review_status(meeting, result=result, workflow=workflow)
    source = meeting_source(media_revision)
    access_state = access or owner_access_state()
    artifact_states = artifacts or []
    notes_truth = notes_action_truth_state(
        status=status, result=result, outcome_set=outcome_set, outcome_items=outcome_items or []
    )
    item = MeetingListItem(
        meeting_id=meeting.id,
        title=safe_title(meeting, source=source),
        started_at=meeting.started_at,
        ended_at=meeting.ended_at,
        recording_display_timezone_offset_minutes=meeting.recording_display_timezone_offset_minutes,
        duration_seconds=max(0, meeting.duration_seconds),
        source=source,
        status=status,
        status_label=STATUS_LABELS[status],
        status_reason=workflow.last_reason_code
        if workflow is not None and status in {"blocked", "failed"}
        else result.failure_reason
        if result is not None and status == "unavailable"
        else None,
        primary_action=primary_action_for_status(status),
        transcript_available=transcript_available(result),
        diarization_available=diarization_available(result),
        notes_available=notes_truth.summary.state == "available",
        notes_action_truth=notes_truth,
        updated_at=meeting.updated_at,
        access=access_state,
        artifacts=artifact_states,
        governance=governance_summary(access=access_state, artifacts=artifact_states),
        future_slots=future_slots(),
        upload=upload,
        calendar_context=calendar_context_summary(
            calendar_context,
            meeting_title_source=meeting.title_source,
            owner_actions=access_state.state == "owner",
            public_projection=True,
        ),
        previous_recurring_meeting=previous_recurring_meeting,
        playback=playback or PlaybackPreparationState(),
    )
    item._presentation_meeting_status = meeting.status
    return item


def calendar_context_summary(
    context: RecordingCalendarContextLink | None,
    *,
    meeting_title_source: str | None,
    owner_detail: bool = False,
    owner_actions: bool = False,
    public_projection: bool = False,
) -> MeetingCalendarContextSummary | None:
    if context is None:
        return None
    context_state = context.context_state
    matched_states = {"matched_auto", "matched_user", "legacy_linked"}
    owner_list_states = {"ambiguous", "declined_by_user", "cleared_by_user"}
    if (
        public_projection
        and not owner_detail
        and context_state not in matched_states | (owner_list_states if owner_actions else set())
    ):
        context_state = "no_context"
    accepted_title_sources = {
        "user_confirmed",
        "calendar",
        "app_context",
        "generic",
        "upload_provided",
        "file_name_derived",
        "legacy_unknown",
    }
    title_source = meeting_title_source if meeting_title_source in accepted_title_sources else None
    label = (
        "Подобрано автоматически"
        if owner_detail and context_state == "matched_auto"
        else calendar_context_state_copy(context_state)
        if context_state in CALENDAR_CONTEXT_STATE_COPY["ru"]
        else "Без контекста календаря"
    )
    return MeetingCalendarContextSummary(
        state=context_state,
        label=label,
        reason_label=(
            CALENDAR_CONTEXT_OWNER_REASON_LABELS.get(context.safe_reason_code)
            if owner_detail
            else None
        ),
        title_source=title_source,
        needs_owner_action=(owner_detail or owner_actions) and context.context_state == "ambiguous",
    )


def primary_action_for_status(status: MeetingReviewStatus) -> str:
    if status in {"ready", "partial"}:
        return "open"
    if status in {"processing", "submitted", "uploading"}:
        return "wait"
    if status == "blocked":
        return "open_status"
    if status == "failed":
        return "retry_future"
    return "unavailable"


def meeting_source(media_revision: MediaRevision | None) -> str:
    if (
        media_revision is not None
        and media_revision.source_kind == MediaRevisionSourceKind.MANUAL_UPLOAD.value
    ):
        return "manual_upload"
    if (
        media_revision is not None
        and media_revision.source_kind == MediaRevisionSourceKind.VIDEO_CAPTURE.value
    ):
        return "video_recording"
    return "desktop_recording"


def processing_state(
    meeting: Meeting,
    *,
    result: ProcessingResult | None,
    workflow: ProcessingWorkflow | None,
) -> ProcessingReviewState:
    status = review_status(meeting, result=result, workflow=workflow)
    has_transcript = transcript_available(result)
    has_diarization = diarization_available(result)
    summary_available = bool(
        result is not None and result.summary_status == SummaryStatus.AVAILABLE.value
    )
    reason_code = (
        workflow.last_reason_code
        if workflow is not None and status in {"blocked", "failed"}
        else None
    )
    if reason_code is None and result is not None and not has_transcript:
        reason_code = result.failure_reason
    return ProcessingReviewState(
        state=status,
        stage=stage_for_status(
            status, workflow.status if workflow is not None else meeting.processing_status
        ),
        reason_code=reason_code,
        reason_label=reason_label(reason_code),
        content_available=has_transcript or has_diarization or summary_available,
        transcript_available=has_transcript,
        diarization_available=has_diarization,
        summary_available=summary_available,
        updated_at=(workflow.updated_at if workflow is not None else meeting.updated_at),
        next_action=next_action_for_status(status, reason_code=reason_code),
    )


def stage_for_status(status: str, lifecycle_status: str) -> str | None:
    if status in {"ready", "partial"}:
        return "ready"
    if status == "processing":
        if lifecycle_status in {ProcessingStatus.SUBMITTED.value, ProcessingStatus.POLLING.value}:
            return "mediascribe"
        if lifecycle_status == ProcessingStatus.IMPORTING.value:
            return "importing"
        return "submitted"
    if status == "submitted":
        return "stored"
    if status in {"blocked", "failed"}:
        return status
    if status in {"uploading", "local_only"}:
        return "upload"
    return None


def next_action_for_status(status: str, *, reason_code: str | None = None) -> str:
    if status in {"processing", "submitted", "uploading"}:
        return "wait"
    if status == "blocked":
        return "contact_operator"
    if status == "failed":
        if reason_code in {
            "mediascribe_timeout",
            "mediascribe_rate_limited",
            "mediascribe_server_error",
            "mediascribe_submission_in_progress",
            "mediascribe_result_not_ready",
            "processing_temp_storage_unavailable",
            "unknown_dependency_status",
        }:
            return "retry_future"
        return "contact_operator"
    if status == "local_only":
        return "open_desktop_queue"
    return "none"


def reason_label(reason_code: str | None) -> str | None:
    if reason_code is None:
        return None
    return {
        "no_recognizable_speech": "MediaScribe обработал запись, но транскрипт не создан: распознаваемая речь не найдена.",
        "invalid_audio_payload": "Файл записи не является декодируемым аудио или поврежден.",
        "mediascribe_validation_failed": "Сервис транскрипции отклонил файл: проверьте формат и повторите обработку.",
        "mediascribe_payload_too_large": "Файл записи превышает допустимый размер.",
        "mediascribe_auth_failed": "Сервис транскрипции отклонил доступ; повторить можно после проверки настройки сервера.",
        "mediascribe_malformed_response": "Сервис транскрипции вернул некорректный ответ. Повторите обработку; если ошибка повторится, обратитесь к оператору.",
        "mediascribe_timeout": "Сервис транскрипции не ответил вовремя. Повторная попытка будет выполнена автоматически.",
        "mediascribe_rate_limited": "Сервис транскрипции временно ограничил запросы. Повторите позже.",
        "mediascribe_server_error": "Сервис транскрипции временно недоступен. Повторите позже.",
        "mediascribe_retries_exhausted": "Сервис транскрипции не восстановился после нескольких попыток. Повторите позже или обратитесь к оператору.",
        "mediascribe_poll_limit_exceeded": "Сервис транскрипции не завершил обработку в отведённое время. Повторите позже или обратитесь к оператору.",
        "mediascribe_submission_in_progress": "Предыдущая отправка ещё выполняется. Подождите завершения и обновите страницу.",
        "mediascribe_result_not_ready": "Сервис транскрипции ещё готовит результат. Повторная проверка будет выполнена автоматически.",
        "blocked_mediascribe_submission_outcome_unknown": "Не удалось подтвердить результат отправки записи. Повторная отправка остановлена во избежание дубликата; обратитесь к оператору.",
        "blocked_missing_artifacts": "Исходный файл записи недоступен. Повторите синхронизацию или загрузите запись заново.",
        "blocked_config": "Обработка заблокирована настройкой сервера. Обратитесь к оператору.",
        "processing_temp_storage_unavailable": "На сервере временно недоступно место для обработки. Повторите позже.",
        "unknown_dependency_status": "Сервис транскрипции вернул неизвестный статус. Повторите позже.",
    }.get(reason_code, "Обработка требует проверки оператором.")


def transcript_state(
    *,
    language: str | None,
    transcript_segments: Iterable[TranscriptSegment],
    diarization_segments: Iterable[DiarizationSegment],
    status: MeetingReviewStatus,
    playback_available: bool = False,
    playback_duration_seconds: int | None = None,
    force_speaker_labels: bool = False,
    speaker_names: dict[str, str] | None = None,
) -> TranscriptReviewState:
    transcripts = sorted(transcript_segments, key=lambda row: (row.sequence, row.start_seconds))
    diarization_rows = sorted(
        diarization_segments, key=lambda row: (row.start_seconds, row.sequence)
    )
    diarization_display_rows = [row for row in diarization_rows if row.text.strip()]
    if status not in {"ready", "partial"}:
        return TranscriptReviewState(
            available=False,
            language=language,
            degraded_reason="processing"
            if status in {"processing", "submitted"}
            else "unavailable",
            search_enabled=False,
            segments=[],
        )
    speaker_labels_by_key = canonical_speaker_labels(diarization_rows)
    speaker_names = speaker_names or {}
    if force_speaker_labels and diarization_display_rows:
        return diarization_transcript_state(
            language=language,
            diarization_rows=diarization_display_rows,
            speaker_rows=mediascribe_speaker_rows(diarization_rows),
            status=status,
            playback_available=playback_available,
            playback_duration_seconds=playback_duration_seconds,
            speaker_names=speaker_names,
        )
    if not transcripts:
        return TranscriptReviewState(
            available=False,
            language=language,
            degraded_reason="unavailable",
            search_enabled=False,
            segments=[],
        )
    segments = []
    mapped_rows: list[tuple[TranscriptSegmentView, bool]] = []
    for segment in transcripts:
        seek_seconds = _seek_seconds(
            segment.start_seconds,
            playback_available=playback_available,
            playback_duration_seconds=playback_duration_seconds,
        )
        matching_diarization = matching_diarization_segment(segment, diarization_rows)
        confirmed = matching_diarization is not None and bool(
            matching_diarization.speaker_label.strip()
        )
        attribution_state = (
            "confirmed"
            if confirmed
            else ("unconfirmed" if matching_diarization is not None else "unknown")
        )
        canonical_label = (
            speaker_label_for_segment(
                segment,
                matching_diarization,
                speaker_labels_by_key=speaker_labels_by_key,
            )
            if confirmed
            else "UNKNOWN"
        )
        speaker_key = (
            canonical_label.lower()
            if confirmed
            else (
                f"unconfirmed:{matching_diarization.id}"
                if matching_diarization is not None
                else f"unknown:{segment.id}"
            )
        )
        view = TranscriptSegmentView(
            segment_id=str(segment.id),
            sequence=segment.sequence,
            start_seconds=float(segment.start_seconds),
            end_seconds=float(segment.end_seconds),
            timestamp_label=format_timestamp(segment.start_seconds),
            speaker_label=speaker_names.get(speaker_key, canonical_label),
            speaker_key=speaker_key,
            attribution_state=attribution_state,
            processing_result_id=segment.processing_result_id,
            source_role=source_role_label(segment.source_role),
            source_role_original=segment.source_role_original,
            text=segment.text,
            confidence_label="unknown",
            seekable=seek_seconds is not None,
            seek_seconds=seek_seconds,
        )
        segments.append(view)
        mapped_rows.append(
            (
                view,
                confirmed,
            )
        )
    return TranscriptReviewState(
        available=True,
        language=language,
        degraded_reason=None if status == "ready" else "partial_transcript",
        search_enabled=True,
        segments=segments,
        speaker_turns=derive_speaker_turns(mapped_rows) if status == "ready" else [],
    )


def diarization_transcript_state(
    *,
    language: str | None,
    diarization_rows: list[DiarizationSegment],
    speaker_rows: list[DiarizationSegment],
    status: MeetingReviewStatus,
    playback_available: bool,
    playback_duration_seconds: int | None,
    speaker_names: dict[str, str] | None = None,
) -> TranscriptReviewState:
    speaker_labels = mediascribe_speaker_labels_by_time(
        diarization_rows,
        speaker_rows,
    )
    speaker_names = speaker_names or {}
    segments = []
    for row, canonical_label in zip(diarization_rows, speaker_labels, strict=True):
        confirmed = canonical_label != "UNKNOWN"
        speaker_key = canonical_label.lower() if confirmed else f"unconfirmed:{row.id}"
        seek_seconds = _seek_seconds(
            row.start_seconds,
            playback_available=playback_available,
            playback_duration_seconds=playback_duration_seconds,
        )
        segments.append(
            TranscriptSegmentView(
                segment_id=str(row.id),
                sequence=row.sequence,
                start_seconds=float(row.start_seconds),
                end_seconds=float(row.end_seconds),
                timestamp_label=format_timestamp(row.start_seconds),
                speaker_label=speaker_names.get(speaker_key, canonical_label),
                speaker_key=speaker_key,
                attribution_state="confirmed" if confirmed else "unconfirmed",
                processing_result_id=row.processing_result_id,
                source_role=source_role_label(row.source_role),
                source_role_original=row.source_role,
                text=row.text,
                confidence_label="unknown",
                seekable=seek_seconds is not None,
                seek_seconds=seek_seconds,
            )
        )
    return TranscriptReviewState(
        available=True,
        language=language,
        degraded_reason=None if status == "ready" else "partial_transcript",
        search_enabled=True,
        segments=segments,
        speaker_turns=(
            derive_speaker_turns(
                [(view, view.attribution_state == "confirmed") for view in segments]
            )
            if status == "ready"
            else []
        ),
    )


def canonical_turn_id(processing_result_id: UUID | None, segment_ids: Iterable[str]) -> str:
    source_ids = tuple(segment_ids)
    if processing_result_id is None:
        return source_ids[0]
    digest = hashlib.sha256(f"{processing_result_id}:{','.join(source_ids)}".encode()).hexdigest()[
        :24
    ]
    return f"turn_{digest}"


def derive_speaker_turns(
    rows: list[tuple[TranscriptSegmentView, bool]],
) -> list[TranscriptSpeakerTurnView]:
    turns: list[TranscriptSpeakerTurnView] = []
    current: list[TranscriptSegmentView] = []
    valid_rows = [
        row for row, _ in rows if row.start_seconds >= 0 and row.end_seconds >= row.start_seconds
    ]
    overlap_ids: set[str] = set()
    timeline_rows = sorted(
        valid_rows,
        key=lambda row: (row.start_seconds, row.end_seconds, row.sequence, row.segment_id),
    )
    longest: TranscriptSegmentView | None = None
    for row in timeline_rows:
        if (
            longest is not None
            and row.start_seconds < longest.end_seconds
            and longest.start_seconds < row.end_seconds
        ):
            overlap_ids.update((longest.segment_id, row.segment_id))
        if longest is None or row.end_seconds > longest.end_seconds:
            longest = row

    def flush() -> None:
        if not current or not any(row.text.strip() for row in current):
            current.clear()
            return
        first = current[0]
        last = current[-1]
        turns.append(
            TranscriptSpeakerTurnView(
                turn_id=canonical_turn_id(
                    first.processing_result_id,
                    (row.segment_id for row in current),
                ),
                sequence=first.sequence,
                start_seconds=first.start_seconds,
                end_seconds=last.end_seconds,
                timestamp_label=first.timestamp_label,
                speaker_label=first.speaker_label,
                speaker_key=first.speaker_key,
                attribution_state=first.attribution_state,
                processing_result_id=first.processing_result_id,
                source_role=first.source_role,
                text=" ".join(row.text.strip() for row in current if row.text.strip()),
                source_segment_ids=[row.segment_id for row in current],
                overlap=any(row.segment_id in overlap_ids for row in current),
                confidence_label=first.confidence_label,
                seekable=first.seekable,
                seek_seconds=first.seek_seconds,
            )
        )
        current.clear()

    for row, confirmed in rows:
        if row.start_seconds < 0 or row.end_seconds < row.start_seconds:
            flush()
            continue
        if confirmed and row.attribution_state == "unknown":
            row = row.model_copy(update={"attribution_state": "confirmed"})
        if not current:
            current.append(row)
            continue
        previous = current[-1]
        gap = Decimal(str(row.start_seconds)) - Decimal(str(previous.end_seconds))
        if (
            row.speaker_key == previous.speaker_key
            and row.attribution_state == "confirmed"
            and previous.attribution_state == "confirmed"
            and (row.source_role_original or row.source_role)
            == (previous.source_role_original or previous.source_role)
            and row.processing_result_id == previous.processing_result_id
            and row.segment_id not in overlap_ids
            and previous.segment_id not in overlap_ids
            and Decimal("0") <= gap <= Decimal("1")
        ):
            current.append(row)
            continue
        flush()
        current.append(row)
    flush()
    return turns


def _seek_seconds(
    value: Decimal,
    *,
    playback_available: bool,
    playback_duration_seconds: int | None,
) -> float | None:
    if not playback_available:
        return None
    seconds = float(value)
    if seconds < 0:
        return None
    if playback_duration_seconds is not None and seconds > playback_duration_seconds:
        return None
    return seconds


def speaker_label_for_segment(
    segment: TranscriptSegment,
    diarization: DiarizationSegment | None,
    *,
    speaker_labels_by_key: dict[str, str] | None = None,
) -> str:
    if diarization is None:
        return "SPEAKER_00"
    labels = speaker_labels_by_key or canonical_speaker_labels([diarization])
    return labels[_speaker_identity_key(diarization)]


def matching_diarization_segment(
    segment: TranscriptSegment,
    diarization_rows: Iterable[DiarizationSegment],
) -> DiarizationSegment | None:
    segment_source = source_role_label(segment.source_role)
    best: DiarizationSegment | None = None
    best_overlap = Decimal("0")
    best_source_match = False
    for row in diarization_rows:
        if row.start_seconds >= segment.end_seconds:
            break
        overlap = min(segment.end_seconds, row.end_seconds) - max(
            segment.start_seconds, row.start_seconds
        )
        if overlap <= 0:
            continue
        source_match = source_role_label(row.source_role) == segment_source
        if (source_match and not best_source_match) or (
            source_match == best_source_match and overlap > best_overlap
        ):
            best = row
            best_overlap = overlap
            best_source_match = source_match
    return best


def canonical_speaker_labels(diarization_segments: Iterable[DiarizationSegment]) -> dict[str, str]:
    labels: dict[str, str] = {}
    for row in sorted(diarization_segments, key=lambda item: (item.start_seconds, item.sequence)):
        key = _speaker_identity_key(row)
        if key not in labels:
            labels[key] = f"SPEAKER_{len(labels):02d}"
    return labels


def _speaker_identity_key(row: DiarizationSegment) -> str:
    raw_label = (row.speaker_label or "").strip()
    if raw_label:
        return raw_label
    return f"{source_role_label(row.source_role)}:{row.sequence}"


def is_mediascribe_speaker_label(label: str | None) -> bool:
    return mediascribe_speaker_label(label) is not None


def mediascribe_speaker_label(label: str | None) -> str | None:
    if label is None:
        return None
    normalized = label.strip()
    if MEDIASCRIBE_SPEAKER_LABEL_RE.fullmatch(normalized):
        return normalized
    return None


def transcript_speaker_labels(
    transcripts: list[TranscriptSegment],
    *,
    diarization_rows: list[DiarizationSegment],
    diarization_by_segment_key: dict[tuple[int, SourceRoleView], DiarizationSegment],
    force_speaker_labels: bool,
) -> list[str]:
    if force_speaker_labels:
        return mediascribe_speaker_labels_by_time(
            transcripts,
            mediascribe_speaker_rows(diarization_rows),
        )
    return [
        speaker_label_for_segment(
            segment,
            diarization_by_segment_key.get(
                (segment.sequence, source_role_label(segment.source_role))
            ),
        )
        for segment in transcripts
    ]


def mediascribe_speaker_labels_by_time(
    segments: list[TranscriptSegment] | list[DiarizationSegment],
    speaker_rows: list[DiarizationSegment],
) -> list[str]:
    if not speaker_rows:
        return ["UNKNOWN"] * len(segments)
    labels = ["UNKNOWN"] * len(segments)
    cursor = 0
    for index, segment in sorted(enumerate(segments), key=lambda item: segment_time_key(item[1])):
        own_label = mediascribe_speaker_label(getattr(segment, "speaker_label", None))
        if own_label is not None:
            labels[index] = own_label
            continue
        midpoint = segment_midpoint(segment)
        while cursor + 1 < len(speaker_rows) and segment_end(speaker_rows[cursor]) < midpoint:
            cursor += 1
        labels[index] = nearest_speaker_label_at_midpoint(midpoint, speaker_rows, cursor)
    return labels


def mediascribe_speaker_rows(rows: list[DiarizationSegment]) -> list[DiarizationSegment]:
    return [row for row in rows if is_mediascribe_speaker_label(row.speaker_label)]


def nearest_speaker_label_at_midpoint(
    midpoint: float,
    speaker_rows: list[DiarizationSegment],
    cursor: int,
) -> str:
    last_index = len(speaker_rows) - 1
    candidate_indexes = {max(0, cursor - 1), cursor, min(last_index, cursor + 1)}

    def rank(index: int) -> tuple[float, float, int, int]:
        row = speaker_rows[index]
        start = segment_start(row)
        end = segment_end(row)
        if start <= midpoint <= end:
            gap = 0.0
        elif midpoint < start:
            gap = start - midpoint
        else:
            gap = midpoint - end
        return (gap, abs(segment_midpoint(row) - midpoint), row.sequence, index)

    label = mediascribe_speaker_label(speaker_rows[min(candidate_indexes, key=rank)].speaker_label)
    return label or "UNKNOWN"


def segment_time_key(segment: TranscriptSegment | DiarizationSegment) -> tuple[float, float, int]:
    return (segment_start(segment), segment_end(segment), segment.sequence)


def segment_start(segment: TranscriptSegment | DiarizationSegment) -> float:
    return float(segment.start_seconds)


def segment_end(segment: TranscriptSegment | DiarizationSegment) -> float:
    return float(segment.end_seconds)


def segment_midpoint(segment: TranscriptSegment | DiarizationSegment) -> float:
    return (segment_start(segment) + segment_end(segment)) / 2


def speaker_state(
    diarization_segments: Iterable[DiarizationSegment],
    *,
    force_speaker_labels: bool = False,
    speaker_names: dict[str, str] | None = None,
    can_rename: bool = False,
) -> SpeakerReviewState:
    speaker_names = speaker_names or {}
    rows = sorted(diarization_segments, key=lambda row: (row.start_seconds, row.sequence))
    if not rows:
        return SpeakerReviewState(
            available=False,
            assignment_state="reserved",
            degraded_reason="diarization_unavailable",
            speakers=[],
            can_rename=False,
        )

    grouped: dict[str, list[DiarizationSegment]] = defaultdict(list)
    labels_by_key: dict[str, str] = {}
    if force_speaker_labels:
        speaker_labels = mediascribe_speaker_labels_by_time(rows, mediascribe_speaker_rows(rows))
        for row, speaker_label in zip(rows, speaker_labels, strict=True):
            speaker_key = speaker_label.lower()
            labels_by_key[speaker_key] = speaker_label
            grouped[speaker_key].append(row)
    else:
        speaker_labels_by_key = canonical_speaker_labels(rows)
        for row in rows:
            speaker_label = speaker_labels_by_key[_speaker_identity_key(row)]
            speaker_key = speaker_label.lower()
            labels_by_key[speaker_key] = speaker_label
            grouped[speaker_key].append(row)
    total = sum(max(0.0, float(row.end_seconds) - float(row.start_seconds)) for row in rows) or 1.0
    speakers: list[SpeakerLane] = []
    for speaker_key, speaker_rows in grouped.items():
        speaker_label = labels_by_key[speaker_key]
        duration = sum(
            max(0.0, float(row.end_seconds) - float(row.start_seconds)) for row in speaker_rows
        )
        source_roles = _unique(source_role_label(row.source_role) for row in speaker_rows)
        speakers.append(
            SpeakerLane(
                speaker_key=speaker_key,
                label=speaker_names.get(speaker_key, speaker_label),
                display_name=speaker_names.get(speaker_key),
                talk_time_percent=round(duration / total * 100),
                source_roles=source_roles,
                segments=[
                    SpeakerLaneSegment(
                        start_seconds=float(row.start_seconds), end_seconds=float(row.end_seconds)
                    )
                    for row in speaker_rows
                ],
                confidence_label="unknown",
            )
        )
    return SpeakerReviewState(
        available=True,
        assignment_state="reserved",
        degraded_reason=None,
        speakers=speakers,
        can_rename=can_rename,
    )


def calendar_roster_state(participants: Iterable[CalendarParticipant]) -> CalendarRosterReviewState:
    views = [
        CalendarRosterParticipantView(
            participant_kind=participant.participant_kind,
            response_status=participant.response_status,
            display_name=safe_metadata_text(participant.display_name, max_length=240),
            email_present=bool(participant.email_hash or participant.email),
            workspace_relation=participant.workspace_relation,
            recipient_candidate_class=participant.recipient_candidate_class,
        )
        for participant in participants
    ]
    return CalendarRosterReviewState(
        available=bool(views),
        roster_state="available" if views else "not_available",
        participant_count=len(views),
        source="calendar" if views else "none",
        participants=views,
    )


def _calendar_roster_snapshot_items_state(
    participants: Iterable[dict[str, object]],
    *,
    roster_state: str,
    participant_count: int,
) -> CalendarRosterReviewState:
    views = [
        CalendarRosterParticipantView(
            participant_kind=str(participant.get("participant_kind") or "unknown")[:80],
            response_status=str(participant.get("response_status") or "unknown")[:80],
            display_name=safe_metadata_text(
                participant.get("display_name"),
                max_length=240,
            ),
            email_present=bool(participant.get("email_present", False)),
            workspace_relation=str(participant.get("workspace_relation") or "unknown")[:80],
            recipient_candidate_class=str(
                participant.get("recipient_candidate_class") or "unknown"
            )[:80],
        )
        for participant in list(participants)[:100]
    ]
    normalized_state = (
        roster_state
        if roster_state in {"available", "not_available", "hidden"}
        else "not_available"
    )
    return CalendarRosterReviewState(
        available=normalized_state == "available" and bool(views),
        roster_state=normalized_state,
        participant_count=max(participant_count, len(views), 0),
        source="calendar" if normalized_state == "available" else "none",
        participants=views,
    )


def calendar_roster_snapshot_state(
    context: RecordingCalendarContextLink | None,
) -> CalendarRosterReviewState | None:
    if context is None or context.context_state not in {
        "matched_auto",
        "matched_user",
    }:
        return None
    has_immutable_snapshot = bool(
        context.match_attempt_id
        or context.matcher_version
        or context.matched_roster_json
        or context.matched_roster_count
    )
    if not has_immutable_snapshot:
        return None
    return _calendar_roster_snapshot_items_state(
        context.matched_roster_json or [],
        roster_state=context.matched_roster_state,
        participant_count=context.matched_roster_count,
    )


def notes_state(status: MeetingReviewStatus) -> NotesReviewState:
    if status in {"ready", "partial"}:
        return NotesReviewState(
            available=False, sections=[], unavailable_reason="generation_future"
        )
    if status in {"processing", "submitted", "uploading"}:
        return NotesReviewState(available=False, sections=[], unavailable_reason="processing")
    return NotesReviewState(available=False, sections=[], unavailable_reason="not_requested")


def _notes_action_category(
    *,
    state: str,
    label: str,
    reason: str,
    readiness_impact: str,
    copy_key: str,
    items: list[OutcomeItemView] | None = None,
) -> NotesActionCategoryState:
    return NotesActionCategoryState(
        state=state,
        label=label,
        reason=reason,
        readiness_impact=readiness_impact,
        copy_key=copy_key,
        items=items or [],
    )


def notes_action_truth_state(
    *,
    status: MeetingReviewStatus,
    result: ProcessingResult | None,
    outcome_set: MeetingOutcomeSet | None = None,
    outcome_items: list[MeetingOutcomeItem] | None = None,
) -> NotesActionTruthState:
    if outcome_set is not None and status in {"ready", "partial"}:
        return stored_outcome_truth_state(outcome_set, outcome_items or [])
    if status in {"processing", "submitted", "uploading"}:
        category = _notes_action_category(
            state="processing",
            label="Outcomes processing",
            reason="Transcript and generated outcomes may still be processing.",
            readiness_impact="keeps_gap_open",
            copy_key="notes.outcomes.processing",
        )
        return NotesActionTruthState(
            summary=category,
            key_points=category,
            decisions=category,
            action_items=category,
            followups=category,
            risks=category,
            questions=category,
            evidence=category,
            source_basis="processing_status",
        )

    if status in {"blocked", "failed"}:
        category = _notes_action_category(
            state="blocked",
            label="Outcomes blocked",
            reason="Meeting processing needs operator review before outcomes can be trusted.",
            readiness_impact="keeps_gap_open",
            copy_key="notes.outcomes.blocked",
        )
        return NotesActionTruthState(
            summary=category,
            key_points=category,
            decisions=category,
            action_items=category,
            followups=category,
            risks=category,
            questions=category,
            evidence=category,
            source_basis="processing_status",
        )

    if status in {"ready", "partial"}:
        if result is not None and result.summary_status == SummaryStatus.AVAILABLE.value:
            summary = _notes_action_category(
                state="blocked",
                label="Summary unavailable",
                reason="Summary availability was reported, but no stored launch-safe summary content is available.",
                readiness_impact="keeps_gap_open",
                copy_key="notes.summary.blocked_missing_stored_output",
            )
            deferred = _notes_action_category(
                state="deferred",
                label="Outcome deferred",
                reason="This outcome is deferred until generated content is stored and reviewable.",
                readiness_impact="keeps_gap_open",
                copy_key="notes.outcomes.deferred",
            )
            return NotesActionTruthState(
                summary=summary,
                key_points=deferred,
                decisions=deferred,
                action_items=deferred,
                followups=deferred,
                risks=deferred,
                questions=deferred,
                evidence=deferred,
                source_basis="processing_status",
            )
        category = _notes_action_category(
            state="deferred",
            label="Outcomes deferred",
            reason="Transcript review is available, but generated meeting outcomes are not part of this stored result.",
            readiness_impact="keeps_gap_open",
            copy_key="notes.outcomes.deferred",
        )
        return NotesActionTruthState(
            summary=category,
            key_points=category,
            decisions=category,
            action_items=category,
            followups=category,
            risks=category,
            questions=category,
            evidence=category,
            source_basis="policy_deferral",
        )

    category = _notes_action_category(
        state="unavailable",
        label="Outcomes unavailable",
        reason="No reviewable transcript or generated outcome source is available for this meeting.",
        readiness_impact="keeps_gap_open",
        copy_key="notes.outcomes.unavailable",
    )
    return NotesActionTruthState(
        summary=category,
        key_points=category,
        decisions=category,
        action_items=category,
        followups=category,
        risks=category,
        questions=category,
        evidence=category,
        source_basis="not_supported",
    )


def stored_outcome_truth_state(
    outcome_set: MeetingOutcomeSet,
    outcome_items: list[MeetingOutcomeItem],
) -> NotesActionTruthState:
    by_category: dict[str, list[OutcomeItemView]] = defaultdict(list)
    if outcome_set.status in {"available", "partial"}:
        for item in sorted(outcome_items, key=lambda row: (row.category, row.sequence)):
            by_category[item.category].append(_outcome_item_view(item))

    def category_state(category: str, label: str) -> NotesActionCategoryState:
        state = getattr(outcome_set, f"{category}_state")
        return _notes_action_category(
            state=state,
            label=_outcome_state_label(state, label),
            reason=_outcome_state_reason(state),
            readiness_impact="closes_gap"
            if state in {"available", "not_found", "not_inferable"}
            else "keeps_gap_open",
            copy_key=f"notes.{category}.{state}",
            items=by_category.get(category, []),
        )

    return NotesActionTruthState(
        summary=category_state("summary", "Итоги готовы"),
        key_points=category_state("key_points", "Ключевые пункты"),
        decisions=category_state("decisions", "Решения"),
        action_items=category_state("action_items", "Действия"),
        followups=category_state("followups", "Follow-ups"),
        risks=category_state("risks", "Риски"),
        questions=category_state("questions", "Вопросы"),
        evidence=category_state("evidence", "Evidence"),
        source_basis=_outcome_source_basis(outcome_set),
        provenance=OutcomeProvenanceView(
            generator_kind=outcome_set.generator_kind,
            generator_version=outcome_set.generator_version,
            generated_at=outcome_set.generated_at,
            latency_ms=outcome_set.latency_ms,
        ),
    )


def _outcome_source_basis(outcome_set: MeetingOutcomeSet) -> str:
    if outcome_set.status in {"queued", "generating"}:
        return "processing_status"
    if outcome_set.status in {"blocked", "failed", "unsafe"}:
        return "blocked"
    return "stored_output"


def _outcome_item_view(item: MeetingOutcomeItem) -> OutcomeItemView:
    refs = [
        OutcomeSourceReferenceView(
            **{
                **ref,
                "evidence_kind": ref.get("evidence_kind") or "segment",
                "seekable": ref.get("start_seconds") is not None,
            }
        )
        for ref in item.source_refs_json
        if isinstance(ref, dict)
    ]
    return OutcomeItemView(
        category=item.category,
        sequence=item.sequence,
        text=item.text,
        owner_text=item.owner_text,
        due_date_text=item.due_date_text,
        truth_label=item.truth_label,
        source_refs=refs,
    )


def _outcome_state_label(state: str, available_label: str) -> str:
    return {
        "available": available_label,
        "not_found": "Не найдено",
        "not_inferable": "Не удалось надежно определить",
        "processing": "Готовится",
        "blocked": "Заблокировано",
        "unsafe": "Нужна проверка",
        "unavailable": "Недоступно",
    }.get(state, state)


def _outcome_state_reason(state: str) -> str:
    return {
        "available": "Сохраненный итог доступен и связан с расшифровкой.",
        "not_found": "В расшифровке нет надежной опоры для этой категории.",
        "not_inferable": "Эту категорию нельзя надежно вывести из расшифровки.",
        "processing": "Итоги еще формируются.",
        "blocked": "Итоги заблокированы безопасной проверкой.",
        "unsafe": "Итоги требуют проверки перед показом.",
        "unavailable": "Итоги недоступны.",
    }.get(state, "Состояние итогов неизвестно.")


def playback_state(
    meeting: Meeting,
    status: MeetingReviewStatus,
    review_playback: PlaybackPreparationState | None = None,
    *,
    media_revision: MediaRevision | None = None,
) -> PlaybackReviewState:
    del status  # Playback preparation has its own durable state machine.
    duration_seconds = max(0, meeting.duration_seconds)
    durable = review_playback or PlaybackPreparationState()
    unavailable_reason = {
        "preparing": "processing",
        "deleting": "deleting",
        "deleted": "deleted",
    }.get(durable.state)
    if unavailable_reason is None:
        unavailable_reason = (
            "none"
            if durable.can_play
            else "access_denied"
            if durable.reason_code == "access_denied"
            else "no_audio"
            if durable.reason_code in {"empty_source", "no_audio", "source_missing"}
            else "failed"
        )
    return PlaybackReviewState(
        **durable.model_dump(),
        available=durable.can_play,
        duration_seconds=duration_seconds,
        unavailable_reason=unavailable_reason,
        playback_path=(
            f"/api/v1/cabinet/meetings/{meeting.id}/playback" if durable.can_play else None
        ),
        policy_label=durable.label,
        source_mode="stored_review_m4a" if durable.can_play else "none",
        included_sources=(
            ["uploaded_media"]
            if durable.can_play
            and media_revision is not None
            and media_revision.source_kind == MediaRevisionSourceKind.MANUAL_UPLOAD.value
            else ["canonical_mixed"]
            if durable.can_play
            and media_revision is not None
            and media_revision.source_kind == MediaRevisionSourceKind.INITIAL_MIXED_RECORDING.value
            else ["local_microphone", "incoming_system"]
            if durable.can_play
            else []
        ),
    )


def provenance_state(
    *,
    media_revision: MediaRevision | None,
    transcript_segments: Iterable[TranscriptSegment],
    diarization_segments: Iterable[DiarizationSegment],
    dependency: ProcessingDependencyState | None,
) -> MeetingProvenance:
    roles = _unique(
        [source_role_label(row.source_role) for row in transcript_segments]
        + [source_role_label(row.source_role) for row in diarization_segments]
    )
    return MeetingProvenance(
        media_revision_id=media_revision.id if media_revision is not None else None,
        local_media_revision_id=media_revision.local_media_revision_id
        if media_revision is not None
        else None,
        source_roles=roles,
        processing_dependency=dependency.dependency if dependency is not None else None,
        content_policy="authorized_detail_only",
    )


def build_review_response(
    meeting: Meeting,
    *,
    media_revision: MediaRevision | None = None,
    result: ProcessingResult | None,
    workflow: ProcessingWorkflow | None,
    transcript_segments: list[TranscriptSegment],
    diarization_segments: list[DiarizationSegment],
    dependency: ProcessingDependencyState | None,
    access: MeetingAccessState | None = None,
    share: SharePanelState | None = None,
    artifacts: list[ArtifactEgressState] | None = None,
    content_exports: ContentExportCapabilityResponse | None = None,
    review_playback: PlaybackPreparationState | None = None,
    calendar_roster: CalendarRosterReviewState | None = None,
    calendar_context: RecordingCalendarContextLink | None = None,
    calendar_context_detail: MeetingCalendarContextResponse | None = None,
    activity: MeetingActivityResponse | None = None,
    outcome_set: MeetingOutcomeSet | None = None,
    outcome_template_name: str | None = None,
    default_summary_template_key: str = "graf-auto-v1",
    default_summary_template_name: str | None = None,
    outcome_items: list[MeetingOutcomeItem] | None = None,
    speaker_names: dict[str, str] | None = None,
    can_rename_speakers: bool = False,
) -> MeetingReviewResponse:
    access_state = access or owner_access_state()
    artifact_states = artifacts or []
    item = build_list_item(
        meeting,
        media_revision=media_revision,
        result=result,
        workflow=workflow,
        access=access_state,
        artifacts=artifact_states,
        calendar_context=calendar_context,
        playback=review_playback,
    )
    status = cast(MeetingReviewStatus, item.status)
    notes_truth = notes_action_truth_state(
        status=status, result=result, outcome_set=outcome_set, outcome_items=outcome_items or []
    )
    item.notes_available = notes_truth.summary.state == "available"
    item.notes_action_truth = notes_truth
    playback = playback_state(
        meeting,
        status,
        review_playback,
        media_revision=media_revision,
    )
    force_speaker_labels = (
        media_revision is not None
        and media_revision.source_kind == MediaRevisionSourceKind.MANUAL_UPLOAD.value
    )
    return MeetingReviewResponse(
        meeting=item,
        calendar_context=calendar_context_summary(
            calendar_context,
            meeting_title_source=meeting.title_source,
            owner_detail=access_state.state == "owner",
            public_projection=True,
        ),
        calendar_context_detail=calendar_context_detail,
        provenance=provenance_state(
            media_revision=media_revision,
            transcript_segments=transcript_segments,
            diarization_segments=diarization_segments,
            dependency=dependency,
        ),
        processing=processing_state(meeting, result=result, workflow=workflow),
        transcript=transcript_state(
            language=result.language if result is not None else None,
            transcript_segments=transcript_segments,
            diarization_segments=diarization_segments,
            status=status,
            playback_available=playback.available,
            playback_duration_seconds=playback.duration_seconds,
            force_speaker_labels=force_speaker_labels,
            speaker_names=speaker_names,
        ),
        speakers=speaker_state(
            diarization_segments,
            force_speaker_labels=force_speaker_labels,
            speaker_names=speaker_names,
            can_rename=can_rename_speakers,
        ),
        calendar_roster=calendar_roster,
        notes=notes_state(status),
        notes_action_truth=notes_truth,
        playback=playback,
        governance=governance_summary(
            access=access_state,
            artifacts=artifact_states,
            content_exports=content_exports,
            can_delete=True,
        ),
        access=access_state,
        share=share,
        artifacts=artifact_states,
        content_exports=content_exports,
        activity=activity,
        deletion_truth_copy=DELETION_TRUTH_COPY,
        assistant=slot_state("Assistant"),
        template=summary_template_slot(
            outcome_set,
            personal_name=outcome_template_name,
            default_template_key=default_summary_template_key,
            default_template_name=default_summary_template_name,
        ),
    )


def _unique(values: Iterable[SourceRoleView]) -> list[SourceRoleView]:
    seen: set[str] = set()
    result: list[SourceRoleView] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result
