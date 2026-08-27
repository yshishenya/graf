from __future__ import annotations

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
from twobrain_rec_server.domain.speaker_turns import (
    CanonicalSpeakerTurn,
    canonical_speaker_model,
    canonical_speech_available,
)
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
from twobrain_rec_server.processing.results import (
    result_is_terminal_input,
    result_lineage_is_current,
)

if TYPE_CHECKING:
    from twobrain_rec_server.auth.account_closure import AccountCloseView
    from twobrain_rec_server.db.models import WorkspaceProviderLinkState


PROVIDER_LINK_LABELS = {
    "email": "Email",
    "email_link": "Email",
    "email_magic_link": "Email",
    "yandex": "Яндекс ID",
    "vk": "VK ID",
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
    provider: str | None = None
    can_restart: bool = False


def provider_link_settings_surface(link: WorkspaceProviderLinkState) -> ProviderLinkSettingsSurface:
    status_labels = {
        "initiated": "Ожидаем входа у провайдера",
        "callback_verified": "Провайдер подтверждён — подтвердите подключение в GRAF",
        "confirmed": "Способ входа подключён",
        "expired": "Срок подключения истёк. Начните заново.",
        "rejected": "Подключение не завершено. Начните заново.",
        "unavailable": "Подключение временно недоступно. Попробуйте заново.",
    }
    return ProviderLinkSettingsSurface(
        link_state_id=link.id,
        provider=link.candidate_provider,
        provider_label=PROVIDER_LINK_LABELS.get(link.candidate_provider or "", "Провайдер"),
        status=link.status,
        status_label=status_labels.get(link.status, "Подключение недоступно. Начните заново."),
        can_confirm=link.status == "callback_verified",
        can_restart=link.status in {"rejected", "expired", "unavailable"},
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
            account_session_view(session, current_session_id=current_session_id)
            for session in sessions
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

MeetingListTimeBasis = Literal["meeting", "updated", "upload"]


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
    ProcessingStatus.WAITING_RETRY.value,
    ProcessingStatus.FAILED_RETRYABLE.value,
    ProcessingStatus.IMPORTING.value,
}

PROCESSING_WATCHDOG_REASONS = frozenset(
    {"processing_retry_deadline_exceeded", "mediascribe_poll_limit_exceeded"}
)

GENERATED_MANUAL_UPLOAD_RE = re.compile(r"^manual[-_]upload(?:[-_][a-z0-9]+)+$", re.IGNORECASE)
GENERATED_CAPTURE_TITLE_RE = re.compile(
    r"^(?:current(?: display)? system audio|system audio|yandex telemost|zoom(?:\.us)?|meeting)"
    r"\s*-\s*\d{4}-\d{2}-\d{2}(?:[ T]\d{1,2}:\d{2})?$",
    re.IGNORECASE,
)
GENERATED_CAPTURE_TITLE_SUFFIX_RE = re.compile(r"\s*-\s*\d{4}-\d{2}-\d{2}(?:[ T]\d{1,2}:\d{2})?$")
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
        "VK WorkSpace / свой CalDAV",
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
        "Nextcloud / SOGo через CalDAV",
        "manual_url",
        "CalDAV URL сервера и выбранные календари.",
    ),
    "custom_caldav": (
        "Другой CalDAV",
        "manual_url",
        "Пользователь указывает URL; синхронизация работает только на чтение, насколько это позволяет сервер.",
    ),
    "google_calendar": (
        "Google Calendar",
        "oauth",
        "OAuth только для чтения. Доступность зависит от настроек Google Cloud и проверки приложения.",
    ),
}

CALENDAR_METHOD_LABELS = {
    "app_password": "Пароль приложения",
    "manual_url": "Ручной CalDAV URL",
    "provider_specific_limited": "Может требовать администратора",
    "oauth": "OAuth только для чтения",
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
    "google_calendar": "G",
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
    "connect_invalid_credentials": (
        "Неверные данные Яндекса",
        "Проверьте полный логин и создайте новый пароль приложения типа «Календарь» в Яндекс ID. Обычный пароль аккаунта не подходит.",
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
    "dependency_missing": (
        "Google Calendar пока недоступен",
        "Владелец GRAF еще не настроил OAuth client, redirect URI и проверку доступа Google. Источник не добавлен.",
        "warning",
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
    "selection_limit": (
        "Можно выбрать до 20 календарей",
        "Снимите лишние отметки и сохраните выбор ещё раз.",
        "warning",
    ),
    "preferences_saved": (
        "Настройки сохранены",
        "Будущие подсказки и список ближайших встреч будут учитывать выбранные типы событий. Ручная запись остается доступной.",
        "success",
    ),
    "sync_completed": (
        "Синхронизация завершена",
        "Календарь обновлен. GRAF использует только выбранные события и не изменяет календарь у провайдера.",
        "success",
    ),
    "sync_catalog_updated": (
        "Календари загружены",
        "Выберите один или несколько календарей, чтобы GRAF мог обновлять встречи. Доступ остается только для чтения.",
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
        "Календарь отключён от GRAF.",
        "",
        "success",
    ),
    "disconnect_partial": (
        "Отключение выполнено частично",
        "Не удалось подтвердить полную локальную очистку. Попробуйте ещё раз.",
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
    future_sync_copy: str = (
        "Новые встречи перестанут появляться в GRAF. Уже созданные встречи останутся."
    )
    credential_copy: str = ""
    retention_copy: str = ""
    confirm_label: str = "Отключить"
    cancel_label: str = "Отмена"


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
    runtime_available: bool
    availability_label: str
    connected_source_count: int
    trigger_label: str


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
    sync_action_enabled: bool
    sync_action_label: str
    reconnect_recommended: bool


@dataclass(frozen=True)
class UpcomingPreviewItemView:
    event_id: str
    title: str
    title_state: str
    starts_at: datetime
    ends_at: datetime
    source_ids: tuple[str, ...]
    meeting_link_present: bool
    open_meeting_available: bool = False
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
    private_free_busy_copy: str = (
        "Приватные события и события только со статусом занятости показываются без названия, "
        "ссылок, участников, описания и вложений."
    )
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
    *,
    connected_provider_counts: dict[str, int] | None = None,
) -> tuple[CalendarSettingsProviderPreset, ...]:
    connected_provider_counts = connected_provider_counts or {}
    presets = []
    for payload in provider_payloads:
        family = str(payload.get("provider_family") or "")
        provider_copy = CALENDAR_PROVIDER_UI.get(family)
        if provider_copy is None:
            continue
        label, method, explanation = provider_copy
        runtime_available = bool(payload.get("runtime_available", payload.get("supported", False)))
        connected_source_count = connected_provider_counts.get(family, 0)
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
                    method,
                    payload.get("capability_state") or {},
                    runtime_available=payload.get("runtime_available"),
                ),
                explanation=explanation,
                runtime_available=runtime_available,
                availability_label=("Доступно" if runtime_available else "Скоро"),
                connected_source_count=connected_source_count,
                trigger_label=(
                    f"Добавить ещё · {label}" if connected_source_count else f"Подключить {label}"
                ),
            )
        )
    priority = {
        "google_calendar": 0,
        "caldav_yandex": 1,
        "caldav_mail_ru": 2,
        "custom_caldav": 3,
    }
    return tuple(
        sorted(
            presets,
            key=lambda provider: (
                not provider.runtime_available,
                priority.get(provider.provider_family, 10),
            ),
        )
    )


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
    connected_provider_counts: dict[str, int] = defaultdict(int)
    for source in source_rows:
        connected_provider_counts[source.provider_family] += 1
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
        providers=calendar_provider_presets(
            provider_payloads,
            connected_provider_counts=connected_provider_counts,
        ),
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
        last_successful_sync_label=calendar_sync_time_label(
            source.last_successful_sync_at, now=now
        ),
        safe_error_message=safe_calendar_error_message(source.last_safe_error_code),
        calendars=calendar_views,
        disconnect_confirmation=CalendarDisconnectConfirmationView(),
        sync_action_enabled=sync_health_state not in {"queued", "syncing", "disconnected"},
        sync_action_label=(
            "Синхронизация идет…"
            if sync_health_state == "syncing"
            else "Синхронизация в очереди…"
            if sync_health_state == "queued"
            else "Синхронизировать"
        ),
        reconnect_recommended=sync_health_state in {"credential_failed", "failed_closed"},
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
        "private": "приватное / только занятость",
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


def calendar_sync_time_label(value: datetime | None, *, now: datetime | None = None) -> str:
    if value is None:
        return "успешной синхронизации еще не было"
    synced_at = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    current = now or datetime.now(UTC)
    elapsed_seconds = max(0, int((current - synced_at).total_seconds()))
    if elapsed_seconds < 60:
        return "только что"
    if elapsed_seconds < 3600:
        minutes = elapsed_seconds // 60
        return f"{minutes} {_russian_count_word(minutes, 'минуту', 'минуты', 'минут')} назад"
    if elapsed_seconds < 86400:
        hours = elapsed_seconds // 3600
        return f"{hours} {_russian_count_word(hours, 'час', 'часа', 'часов')} назад"
    days = elapsed_seconds // 86400
    return f"{days} {_russian_count_word(days, 'день', 'дня', 'дней')} назад"


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
        "oauth": "Продолжить в Google",
    }
    return labels.get(method_category, "Подключить календарь")


def calendar_provider_credential_label(method_category: str) -> str | None:
    if method_category == "app_password":
        return "Пароль приложения"
    if method_category == "manual_url":
        return "Пароль приложения или секрет CalDAV"
    return None


def calendar_provider_limitation_copy(
    method_category: str,
    capability_state: object,
    *,
    runtime_available: object = None,
) -> str | None:
    if runtime_available is False and method_category != "oauth":
        return "Подключение появится после полной проверки."
    if method_category == "provider_specific_limited":
        return "Может понадобиться настройка организации или администратор."
    if isinstance(capability_state, dict) and "admin_policy_dependent" in set(
        capability_state.values()
    ):
        return "Часть возможностей зависит от политики организации."
    if method_category == "manual_url":
        return "Если URL или пароль неверны, мы покажем безопасную ошибку без деталей провайдера."
    if method_category == "oauth":
        if runtime_available is True:
            return None
        return "Подключение появится после полной проверки."
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
        open_meeting_available=bool(
            meeting_link_present
            and (event.provider_extras_json or {}).get("sealed_open_meeting_url")
        ),
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
    description: str
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
            "Разрешения и автозапись на Mac.",
            "На этом Mac",
            "/recording",
            "Встречи",
            "video",
        ),
        (
            "summaries",
            "Итоги",
            "Форматы и структура итогов.",
            "В этом пространстве",
            "/summaries",
            "Встречи",
            "transcript",
        ),
        (
            "calendar",
            "Календари",
            "Подключения, календари и подсказки.",
            "Личная настройка",
            "/integrations/calendar",
            "Встречи",
            "calendar-days",
        ),
        (
            "workspace",
            "Пространства",
            "Новые встречи и приглашения.",
            "В этом пространстве",
            "/workspace",
            "Рабочее пространство",
            "users-round",
        ),
        (
            "account",
            "Аккаунт и безопасность",
            "Профиль, интерфейс и безопасность.",
            "Личная настройка",
            "/account",
            "Аккаунт",
            "settings",
        ),
    )
    definitions += (
        (
            "notifications",
            "Уведомления",
            "Подсказки и системные сообщения.",
            "Личная настройка",
            "/notifications",
            "Аккаунт",
            "bell",
        ),
        (
            "billing",
            "Тариф и оплата",
            "Тариф, хранилище и платежи.",
            "В этом пространстве",
            "/billing",
            "Оплата",
            "activity",
        ),
    )
    return tuple(
        SettingsCategoryView(
            id=category_id,
            label=label,
            description=description,
            scope_label=scope_label,
            href="/billing" if embedded and category_id == "billing" else base + suffix,
            group_label=group_label,
            icon=icon,
        )
        for category_id, label, description, scope_label, suffix, group_label, icon in definitions
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
        return meeting_time_label(item, time_basis="meeting")
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
    prefix = (
        "Обновлено " if time_basis == "updated" else "Загружено " if time_basis == "upload" else ""
    )
    return f"{prefix}{localized.day} {SHORT_MONTH_LABELS[localized.month]}, {localized:%H:%M}"


def meeting_time_label(item: MeetingListItem, *, time_basis: MeetingListTimeBasis) -> str:
    if time_basis == "updated":
        value = item.updated_at
    elif time_basis == "upload":
        value = item.uploaded_at
    else:
        value = item.started_at
        if value is None and item.source == "manual_upload":
            value = item.uploaded_at
            if value is not None:
                time_basis = "upload"
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
    presentation_status = meeting_list_presentation_status(item)
    if presentation_status == "processing" and item.status_label == "Нужна проверка":
        return "Результат ещё не подтверждён · откройте встречу для проверки"
    if presentation_status in {"submitted", "processing"}:
        return "Спикеры определяются · расшифровка готовится"
    if item.primary_action != "open" and presentation_status not in {"ready", "partial"}:
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
    if (
        title
        and meeting.title_source not in AUTHORITATIVE_TITLE_SOURCES
        and MEDIA_FILENAME_EXTENSION_RE.search(title)
    ):
        return _clean_file_title(title)
    projected = recording_display_title(meeting, source=source)
    if (
        projected == "Запись без названия"
        and meeting.title_source not in AUTHORITATIVE_TITLE_SOURCES
    ):
        return "Запись"
    return projected


def safe_title(
    meeting: Meeting,
    *,
    source: str | None = None,
    include_recording_time: bool = True,
) -> str:
    return recording_display_title(
        meeting,
        source=source,
        include_recording_time=include_recording_time,
    )


def recording_display_title(
    meeting: Meeting,
    *,
    source: str | None = None,
    include_recording_time: bool = True,
) -> str:
    title = safe_title_candidate(meeting.title)
    if title:
        if meeting.title_source in AUTHORITATIVE_TITLE_SOURCES:
            if meeting.title_source == "calendar":
                title = _authoritative_title(title)
                return _with_recording_time(title, meeting) if include_recording_time else title
            return _authoritative_title(title)
        if GENERATED_MANUAL_UPLOAD_RE.fullmatch(title):
            return "Загруженная запись"
        if meeting.title_source == "app_context":
            app_title = GENERATED_CAPTURE_TITLE_SUFFIX_RE.sub("", title).strip()
            app_title = _authoritative_title(app_title)
            return _with_recording_time(app_title, meeting) if include_recording_time else app_title
        if GENERATED_CAPTURE_TITLE_RE.fullmatch(title):
            return (
                _generated_recording_title(meeting) or "Запись без названия"
                if include_recording_time
                else "Запись без названия"
            )
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
    return _recording_time_label(meeting, prefix="Запись")


def _with_recording_time(title: str, meeting: Meeting) -> str:
    if meeting.started_at is None:
        return title or "Запись"
    return _recording_time_label(meeting, prefix=title or "Запись", separator=" — ")


def _recording_time_label(
    meeting: Meeting,
    *,
    prefix: str,
    separator: str = " ",
) -> str:
    time_label = meeting_list_time_label(
        meeting.started_at,
        timezone_offset_minutes=meeting.recording_display_timezone_offset_minutes,
        time_basis="meeting",
    )
    return f"{prefix}{separator}{time_label}"


def safe_title_candidate(raw: str | None) -> str | None:
    return safe_metadata_text(raw, max_length=500)


def _result_lineage_matches(
    result: ProcessingResult | None,
    *,
    media_revision_id: UUID | None = None,
    processing_workflow_id: UUID | None = None,
) -> bool:
    """Keep public artifact flags pinned to the current revision lineage.

    The effective result may belong to an older workflow attempt when a newer
    attempt has only a partial result.  The database selector has already
    fenced that result to the current media revision; attempt identity is not
    a reason to hide the previously usable content.
    """

    if result is None:
        return False
    if media_revision_id is not None:
        if result_lineage_is_current(result, media_revision_id=media_revision_id):
            return True
        # Detached unit/view-model fixtures may carry the revision but omit
        # the workflow FK. DB selectors remain fail-closed before production
        # data reaches this pure projection layer.
        return (
            processing_workflow_id is None
            and getattr(result, "processing_workflow_id", None) is None
            and getattr(result, "media_revision_id", None) in {None, media_revision_id}
        )
    if processing_workflow_id is not None:
        return result.processing_workflow_id == processing_workflow_id
    # Direct pure view-model callers may omit a context. Production database
    # selectors fail closed before such a row reaches this projection.
    return True


def _transcript_artifact_available(
    result: ProcessingResult | None,
    *,
    media_revision_id: UUID | None = None,
    processing_workflow_id: UUID | None = None,
) -> bool:
    return bool(
        _result_lineage_matches(
            result,
            media_revision_id=media_revision_id,
            processing_workflow_id=processing_workflow_id,
        )
        and result.status == ProcessingResultStatus.IMPORTED.value
        and canonical_speech_available(result)
    )


def transcript_available(
    result: ProcessingResult | None,
    *,
    media_revision_id: UUID | None = None,
    processing_workflow_id: UUID | None = None,
) -> bool:
    """Return the first user-usable transcript milestone, never transcript-only."""

    return bool(
        _transcript_artifact_available(
            result,
            media_revision_id=media_revision_id,
            processing_workflow_id=processing_workflow_id,
        )
        and _diarization_artifact_available(
            result,
            media_revision_id=media_revision_id,
            processing_workflow_id=processing_workflow_id,
        )
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


def _diarization_artifact_available(
    result: ProcessingResult | None,
    *,
    media_revision_id: UUID | None = None,
    processing_workflow_id: UUID | None = None,
) -> bool:
    return bool(
        _result_lineage_matches(
            result,
            media_revision_id=media_revision_id,
            processing_workflow_id=processing_workflow_id,
        )
        and result.status == ProcessingResultStatus.IMPORTED.value
        and result.diarization_status == ProcessingAvailabilityStatus.AVAILABLE.value
        and result.diarization_segment_count > 0
    )


def diarization_available(
    result: ProcessingResult | None,
    *,
    media_revision_id: UUID | None = None,
    processing_workflow_id: UUID | None = None,
) -> bool:
    return _diarization_artifact_available(
        result,
        media_revision_id=media_revision_id,
        processing_workflow_id=processing_workflow_id,
    )


def review_status(
    meeting: Meeting,
    *,
    result: ProcessingResult | None,
    workflow: ProcessingWorkflow | None,
    media_revision_id: UUID | None = None,
) -> MeetingReviewStatus:
    if meeting_is_deleted_or_deleting(meeting):
        return "deleted_future"
    processing_workflow_id = workflow.id if workflow is not None else None
    # ``partial`` is an internal lifecycle state.  It must remain observable
    # as state, but it must not promote transcript-only rows to user content.
    has_transcript = _transcript_artifact_available(
        result,
        media_revision_id=media_revision_id,
        processing_workflow_id=processing_workflow_id,
    )
    has_diarization = _diarization_artifact_available(
        result,
        media_revision_id=media_revision_id,
        processing_workflow_id=processing_workflow_id,
    )
    if has_transcript and has_diarization:
        return "ready"
    if has_transcript or has_diarization:
        return "partial"

    # An imported provider result with an explicit terminal input outcome
    # is authoritative even if a stale workflow row still says "processing".
    # This keeps list, detail, and the content-safe status endpoint on the
    # same user-visible terminal state.
    if (
        result is not None
        and _result_lineage_matches(
            result,
            media_revision_id=media_revision_id,
            processing_workflow_id=processing_workflow_id,
        )
        and (workflow is None or result.processing_workflow_id == workflow.id)
        and result_is_terminal_input(result)
    ):
        return "failed"

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
    if lifecycle_status == ProcessingStatus.BLOCKED_UNKNOWN.value:
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
    current_media_revision_id = media_revision.id if media_revision is not None else None
    current_workflow_id = workflow.id if workflow is not None else None
    status = review_status(
        meeting,
        result=result,
        workflow=workflow,
        media_revision_id=current_media_revision_id,
    )
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
        uploaded_at=meeting.created_at,
        ended_at=meeting.ended_at,
        recording_display_timezone_offset_minutes=meeting.recording_display_timezone_offset_minutes,
        duration_seconds=max(0, meeting.duration_seconds),
        source=source,
        status=status,
        status_label=(
            "Нужна проверка"
            if status == "processing"
            and workflow is not None
            and workflow.last_reason_code in PROCESSING_WATCHDOG_REASONS
            else STATUS_LABELS[status]
        ),
        status_reason=workflow.last_reason_code
        if workflow is not None
        and (
            status in {"blocked", "failed"}
            or workflow.last_reason_code in PROCESSING_WATCHDOG_REASONS
        )
        else result.failure_reason
        if result is not None and status == "unavailable"
        else None,
        primary_action=primary_action_for_status(status),
        transcript_available=transcript_available(
            result,
            media_revision_id=current_media_revision_id,
            processing_workflow_id=current_workflow_id,
        ),
        diarization_available=diarization_available(
            result,
            media_revision_id=current_media_revision_id,
            processing_workflow_id=current_workflow_id,
        ),
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
    media_revision_id: UUID | None = None,
) -> ProcessingReviewState:
    processing_workflow_id = workflow.id if workflow is not None else None
    status = review_status(
        meeting,
        result=result,
        workflow=workflow,
        media_revision_id=media_revision_id,
    )
    has_transcript = transcript_available(
        result,
        media_revision_id=media_revision_id,
        processing_workflow_id=processing_workflow_id,
    )
    has_diarization = diarization_available(
        result,
        media_revision_id=media_revision_id,
        processing_workflow_id=processing_workflow_id,
    )
    summary_available = bool(
        _result_lineage_matches(
            result,
            media_revision_id=media_revision_id,
            processing_workflow_id=processing_workflow_id,
        )
        and result.summary_status == SummaryStatus.AVAILABLE.value
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
        if lifecycle_status in {
            ProcessingStatus.SUBMITTED.value,
            ProcessingStatus.POLLING.value,
            ProcessingStatus.WAITING_RETRY.value,
        }:
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
        "provider_result_not_ready": "Запись сохранена. GRAF проверит обработку автоматически; расшифровка появится после диаризации.",
        "processing_retry_deadline_exceeded": "MediaScribe ещё не сообщил об ошибке, но автоматическое ожидание остановлено. Проверьте обработку вручную.",
        "manual_processing_check": "GRAF проверяет текущую попытку обработки.",
        "blocked_mediascribe_submission_outcome_unknown": "Не удалось подтвердить результат отправки записи. Повторная отправка остановлена во избежание дубликата; обратитесь к оператору.",
        "blocked_missing_artifacts": "Исходный файл записи недоступен. Повторите синхронизацию или загрузите запись заново.",
        "blocked_config": "Обработка заблокирована настройкой сервера. Обратитесь к оператору.",
        "processing_temp_storage_unavailable": "На сервере временно недоступно место для обработки. Повторите позже.",
        "unknown_dependency_status": "Сервис транскрипции вернул неизвестный статус. Повторите позже.",
    }.get(reason_code, "Обработка требует проверки оператором.")


def _same_result_transcript_rows(
    transcript_segments: Iterable[TranscriptSegment],
    diarization_segments: Iterable[DiarizationSegment],
) -> bool:
    """Require visible rows to come from one result, allowing diarization-only display rows."""

    transcript_result_ids = {
        row.processing_result_id for row in transcript_segments if row.processing_result_id is not None
    }
    diarization_result_ids = {
        row.processing_result_id for row in diarization_segments if row.processing_result_id is not None
    }
    if not transcript_result_ids or len(transcript_result_ids) != 1:
        return False
    if not diarization_result_ids or len(diarization_result_ids) != 1:
        return False
    return transcript_result_ids == diarization_result_ids and len(transcript_result_ids) == 1


def _hidden_transcript_state(
    *,
    language: str | None,
    degraded_reason: str,
) -> TranscriptReviewState:
    return TranscriptReviewState(
        available=False,
        language=language,
        degraded_reason=degraded_reason,
        search_enabled=False,
        segments=[],
        speaker_turns=[],
    )


def transcript_state(
    *,
    language: str | None,
    transcript_segments: Iterable[TranscriptSegment],
    diarization_segments: Iterable[DiarizationSegment],
    status: MeetingReviewStatus,
    playback_available: bool = False,
    playback_duration_seconds: int | None = None,
    speaker_names: dict[str, str] | None = None,
    require_diarization: bool = True,
) -> TranscriptReviewState:
    transcripts = sorted(transcript_segments, key=lambda row: (row.sequence, row.start_seconds))
    diarization_rows = sorted(
        diarization_segments, key=lambda row: (row.start_seconds, row.sequence)
    )
    if status in {"processing", "submitted"}:
        degraded_reason = "processing"
        return _hidden_transcript_state(
            language=language,
            degraded_reason=degraded_reason,
        )
    if status == "partial":
        degraded_reason = "partial_transcript" if transcripts else "unavailable"
        return _hidden_transcript_state(
            language=language,
            degraded_reason=degraded_reason,
        )
    if status not in {"ready", "partial"}:
        return _hidden_transcript_state(
            language=language,
            degraded_reason="diarization_pending" if transcripts else "unavailable",
        )
    if require_diarization and not _same_result_transcript_rows(transcripts, diarization_rows):
        return _hidden_transcript_state(
            language=language,
            degraded_reason="diarization_pending" if transcripts else "unavailable",
        )
    speaker_names = speaker_names or {}
    if not transcripts and not diarization_rows:
        return TranscriptReviewState(
            available=False,
            language=language,
            degraded_reason="unavailable",
            search_enabled=False,
            segments=[],
        )
    processing_result_id = (
        transcripts[0].processing_result_id
        if transcripts
        else diarization_rows[0].processing_result_id
    )
    model = canonical_speaker_model(
        transcripts,
        diarization_rows,
        processing_result_id=processing_result_id,
        speaker_names=speaker_names,
    )
    segments: list[TranscriptSegmentView] = []
    for row in transcripts:
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
                speaker_label="Спикер не определён",
                speaker_key=f"evidence:{processing_result_id.hex}",
                provider_speaker_key=None,
                attribution_state="uncertain",
                result_state=model.result_state,
                processing_result_id=processing_result_id,
                source_role=source_role_label(row.source_role),
                source_role_original=row.source_role_original,
                text=row.text,
                confidence_label="unknown",
                seekable=seek_seconds is not None,
                seek_seconds=seek_seconds,
            )
        )
    turns = [
        _speaker_turn_view(
            turn,
            processing_result_id=processing_result_id,
            playback_available=playback_available,
            playback_duration_seconds=playback_duration_seconds,
        )
        for turn in model.turns
    ]
    return TranscriptReviewState(
        available=True,
        language=language,
        degraded_reason=(
            "degraded_provider_result"
            if model.result_state == "degraded_provider_result"
            else None
            if status == "ready"
            else "partial_transcript"
        ),
        search_enabled=True,
        segments=segments,
        speaker_turns=turns,
        result_state=model.result_state,
    )


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


def _speaker_turn_view(
    turn: CanonicalSpeakerTurn,
    *,
    processing_result_id: UUID,
    playback_available: bool = False,
    playback_duration_seconds: int | None = None,
) -> TranscriptSpeakerTurnView:
    seek_seconds = _seek_seconds(
        turn.start_seconds,
        playback_available=playback_available,
        playback_duration_seconds=playback_duration_seconds,
    )
    return TranscriptSpeakerTurnView(
        turn_id=turn.turn_id,
        sequence=turn.sequence,
        start_seconds=float(turn.start_seconds),
        end_seconds=float(turn.end_seconds),
        timestamp_label=format_timestamp(turn.start_seconds),
        speaker_label=turn.speaker_label,
        speaker_key=turn.speaker_key,
        provider_speaker_key=turn.provider_speaker_key,
        attribution_state=turn.attribution_state,
        result_state=turn.result_state,
        processing_result_id=processing_result_id,
        source_role=source_role_label(turn.source_role),
        text=turn.text,
        source_segment_ids=[turn.source_segment_id],
        overlap=turn.overlap,
        confidence_label="unknown",
        seekable=seek_seconds is not None,
        seek_seconds=seek_seconds,
    )


def speaker_state(
    diarization_segments: Iterable[DiarizationSegment],
    *,
    transcript_segments: Iterable[TranscriptSegment] = (),
    speaker_names: dict[str, str] | None = None,
    can_rename: bool = False,
) -> SpeakerReviewState:
    speaker_names = speaker_names or {}
    rows = sorted(diarization_segments, key=lambda row: (row.start_seconds, row.sequence))
    transcripts = sorted(transcript_segments, key=lambda row: (row.sequence, row.start_seconds))
    if not rows and not transcripts:
        return SpeakerReviewState(
            available=False,
            assignment_state="reserved",
            degraded_reason="diarization_unavailable",
            speakers=[],
            can_rename=False,
        )

    result_id = rows[0].processing_result_id if rows else transcripts[0].processing_result_id
    model = canonical_speaker_model(
        transcripts,
        rows,
        processing_result_id=result_id,
        speaker_names=speaker_names,
    )
    grouped = defaultdict(list)
    for turn in model.turns:
        grouped[turn.speaker_key].append(turn)
    total = model.talk_time_denominator_seconds or Decimal("1")
    speakers: list[SpeakerLane] = []
    for speaker_key, speaker_rows in grouped.items():
        first = speaker_rows[0]
        duration = sum(
            (max(Decimal("0"), row.end_seconds - row.start_seconds) for row in speaker_rows),
            start=Decimal("0"),
        )
        source_roles = _unique(source_role_label(row.source_role) for row in speaker_rows)
        confirmed = first.attribution_state == "confirmed"
        speakers.append(
            SpeakerLane(
                speaker_key=speaker_key,
                label=first.speaker_label,
                display_name=(
                    first.speaker_label
                    if confirmed and first.speaker_label != first.canonical_label
                    else None
                ),
                talk_time_percent=round(float(duration / total * 100)),
                source_roles=source_roles,
                segments=[
                    SpeakerLaneSegment(
                        start_seconds=float(row.start_seconds), end_seconds=float(row.end_seconds)
                    )
                    for row in speaker_rows
                ],
                confidence_label="unknown",
                provider_speaker_key=first.provider_speaker_key,
                confirmed=confirmed,
                can_rename=can_rename and confirmed,
            )
        )
    return SpeakerReviewState(
        available=True,
        assignment_state="reserved",
        degraded_reason=(
            "degraded_provider_result" if model.result_state == "degraded_provider_result" else None
        ),
        turns=[_speaker_turn_view(turn, processing_result_id=result_id) for turn in model.turns],
        speakers=speakers,
        can_rename=can_rename and bool(model.confirmed_speaker_keys),
        result_state=model.result_state,
        talk_time_label=model.talk_time_label,
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
        if result is not None and result.summary_status in {
            SummaryStatus.FAILED.value,
            SummaryStatus.UNAVAILABLE.value,
        }:
            summary = _notes_action_category(
                state="unavailable",
                label="Outcomes unavailable",
                reason="Итоги не удалось подготовить. Расшифровка остаётся доступной независимо от этого сбоя.",
                readiness_impact="non_blocking",
                copy_key="notes.summary.unavailable",
            )
            deferred = _notes_action_category(
                state="deferred",
                label="Outcome deferred",
                reason="Эта категория появится после отдельной подготовки итогов.",
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
    current_media_revision_id = media_revision.id if media_revision is not None else None
    current_lineage = result_lineage_is_current(
        result,
        media_revision_id=current_media_revision_id,
    )
    if not current_lineage and result is not None and workflow is None:
        # Pure view-model callers historically supplied detached ORM fixtures
        # without the DB lineage context. Production selectors never do this:
        # they require an accepted revision and a non-null workflow lineage.
        current_lineage = (
            media_revision is None
            or result.media_revision_id is None
            or result.media_revision_id == current_media_revision_id
        )
    safe_result = result if current_lineage else None
    safe_outcome_set = (
        outcome_set
        if current_lineage
        and result is not None
        and outcome_set is not None
        and outcome_set.processing_result_id == result.id
        else None
    )
    safe_outcome_items = outcome_items if safe_outcome_set is not None else []
    if current_lineage and result is not None:
        # Query code already pins these rows to ``result.id``.  Keep the
        # invariant at the projection boundary as well so stale/mixed rows
        # cannot become transcript, search, speaker, or source-link content.
        transcript_segments = [
            row
            for row in transcript_segments
            if row.processing_result_id == result.id
            and row.meeting_id == meeting.id
            and row.workspace_id == meeting.workspace_id
        ]
        diarization_segments = [
            row
            for row in diarization_segments
            if row.processing_result_id == result.id
            and row.meeting_id == meeting.id
            and row.workspace_id == meeting.workspace_id
        ]
    else:
        transcript_segments = []
        diarization_segments = []
    access_state = access or owner_access_state()
    artifact_states = artifacts or []
    item = build_list_item(
        meeting,
        media_revision=media_revision,
        result=safe_result,
        workflow=workflow,
        access=access_state,
        artifacts=artifact_states,
        calendar_context=calendar_context,
        playback=review_playback,
    )
    row_visibility = _same_result_transcript_rows(transcript_segments, diarization_segments)
    if not row_visibility:
        item.transcript_available = False
    status = cast(MeetingReviewStatus, item.status)
    notes_truth = notes_action_truth_state(
        status=status,
        result=safe_result,
        outcome_set=safe_outcome_set,
        outcome_items=safe_outcome_items,
    )
    item.notes_available = notes_truth.summary.state == "available"
    item.notes_action_truth = notes_truth
    playback = playback_state(
        meeting,
        status,
        review_playback,
        media_revision=media_revision,
    )
    processing_projection = processing_state(
        meeting,
        result=safe_result,
        workflow=workflow,
        media_revision_id=current_media_revision_id,
    )
    if not row_visibility:
        processing_projection.transcript_available = False
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
        processing=processing_projection,
        transcript=transcript_state(
            language=safe_result.language if safe_result is not None else None,
            transcript_segments=transcript_segments,
            diarization_segments=diarization_segments,
            status=status,
            playback_available=playback.available,
            playback_duration_seconds=playback.duration_seconds,
            speaker_names=speaker_names,
            require_diarization=True,
        ),
        speakers=speaker_state(
            diarization_segments if row_visibility else [],
            transcript_segments=transcript_segments if row_visibility else [],
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
            safe_outcome_set,
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
