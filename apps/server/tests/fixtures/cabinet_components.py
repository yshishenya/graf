COMPONENT_STATE_NAMES = (
    "normal",
    "hover",
    "focus",
    "disabled",
    "unavailable",
    "loading",
    "selected",
    "destructive",
    "error",
    "empty",
    "overflow_text",
)

COMPONENT_SAFE_FIXTURE = {
    "workspace_name": "Команда 2brain",
    "workspace_subtitle": "Онлайн-кабинет",
    "meeting_title": "Длинное безопасное название синтетической встречи для проверки переносов в строке списка",
    "status_label": "Готово к проверке",
    "count": 2,
    "total": 5,
}

COMPONENT_FORBIDDEN_MARKERS = (
    "fixture-mediascribe-private-job-id",
    "storage_object_key",
    "signed_url",
    "session_token",
    "raw_audio",
    "transcript_text",
)
