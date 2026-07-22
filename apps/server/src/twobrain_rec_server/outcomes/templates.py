from __future__ import annotations

from dataclasses import dataclass
from typing import Final

OUTCOME_CATEGORIES: Final[tuple[str, ...]] = (
    "summary",
    "key_points",
    "decisions",
    "action_items",
    "followups",
    "risks",
    "questions",
    "evidence",
)
MAX_TEMPLATE_NAME_LENGTH: Final = 80
MAX_TEMPLATE_SECTIONS: Final = len(OUTCOME_CATEGORIES)


@dataclass(frozen=True, slots=True)
class SummaryTemplateDefinition:
    key: str
    name: str
    purpose: str
    sections: tuple[str, ...]
    prompt_name: str
    version: int = 1


def _built_in(
    key: str,
    name: str,
    purpose: str,
    sections: tuple[str, ...],
) -> SummaryTemplateDefinition:
    return SummaryTemplateDefinition(
        key=f"graf-{key}-v1",
        name=name,
        purpose=purpose,
        sections=sections,
        prompt_name=f"graf/meeting-outcome/{key}",
    )


BUILT_IN_TEMPLATES: Final[tuple[SummaryTemplateDefinition, ...]] = (
    _built_in("auto", "Авто", "Краткие итоги, решения и действия", OUTCOME_CATEGORIES),
    _built_in(
        "outline", "Структура", "Последовательная структура разговора", ("summary", "key_points", "evidence")
    ),
    _built_in(
        "meeting-minutes",
        "Протокол встречи",
        "Решения, действия и следующие шаги",
        ("summary", "decisions", "action_items", "followups", "evidence"),
    ),
    _built_in(
        "project-sync",
        "Синхронизация проекта",
        "Статус проекта, решения, действия и риски",
        ("summary", "key_points", "decisions", "action_items", "risks"),
    ),
    _built_in(
        "weekly-team-meeting",
        "Еженедельная встреча команды",
        "Главное за неделю и дальнейшие действия",
        ("summary", "key_points", "action_items", "risks", "questions"),
    ),
    _built_in(
        "one-to-one",
        "Один на один",
        "Темы разговора, договорённости и вопросы",
        ("summary", "key_points", "action_items", "followups", "questions"),
    ),
    _built_in(
        "client-status-update",
        "Статус для клиента",
        "Понятный клиентский статус и риски",
        ("summary", "key_points", "decisions", "action_items", "risks"),
    ),
    _built_in(
        "interview",
        "Интервью",
        "Ключевые ответы и подтверждающие фрагменты",
        ("summary", "key_points", "questions", "evidence"),
    ),
    _built_in(
        "sales-discovery",
        "Встреча с клиентом",
        "Потребности, вопросы, риски и следующие шаги",
        ("summary", "key_points", "action_items", "risks", "questions", "evidence"),
    ),
)

BUILT_IN_BY_KEY: Final = {template.key: template for template in BUILT_IN_TEMPLATES}
PROMPT_NAME_BY_TEMPLATE_KEY: Final = {
    **{template.key: template.prompt_name for template in BUILT_IN_TEMPLATES},
    "personal": "graf/meeting-outcome/custom",
}


def prompt_name_for_template(template_key: str, *, built_in: bool) -> str:
    if built_in:
        try:
            return PROMPT_NAME_BY_TEMPLATE_KEY[template_key]
        except KeyError as exc:
            raise ValueError("unknown built-in template") from exc
    return PROMPT_NAME_BY_TEMPLATE_KEY["personal"]
