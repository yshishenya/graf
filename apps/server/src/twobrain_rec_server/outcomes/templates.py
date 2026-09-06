from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
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


_BUILT_IN_TEMPLATE_CATALOG_V1: Final[tuple[SummaryTemplateDefinition, ...]] = (
    _built_in(
        "auto",
        "Авто",
        "Главное после встречи: решения, действия, риски и открытые вопросы",
        OUTCOME_CATEGORIES,
    ),
    _built_in(
        "outline",
        "По темам",
        "Темы разговора по порядку и вывод по каждой",
        ("summary", "key_points", "evidence"),
    ),
    _built_in(
        "meeting-minutes",
        "Протокол встречи",
        "Цель, принятые решения, обязательства и следующие шаги",
        ("summary", "decisions", "action_items", "followups", "evidence"),
    ),
    _built_in(
        "project-sync",
        "Синхронизация проекта",
        "Прогресс проекта, вехи, блокеры, зависимости и запросы",
        ("summary", "key_points", "decisions", "action_items", "risks"),
    ),
    _built_in(
        "weekly-team-meeting",
        "Еженедельная встреча команды",
        "Изменения за неделю, приоритеты, блокеры и командные действия",
        ("summary", "key_points", "action_items", "risks", "questions"),
    ),
    _built_in(
        "one-to-one",
        "Один на один",
        "Темы сотрудника, нагрузка, обратная связь и взаимные договорённости",
        ("summary", "key_points", "action_items", "followups", "questions"),
    ),
    _built_in(
        "client-status-update",
        "Статус для клиента",
        "Достигнутая ценность, подтверждённый прогресс, риски и следующие шаги",
        ("summary", "key_points", "decisions", "action_items", "risks"),
    ),
    _built_in(
        "interview",
        "Интервью с кандидатом",
        "Вопросы, фактические ответы кандидата и темы для уточнения",
        ("summary", "key_points", "questions", "evidence"),
    ),
    _built_in(
        "sales-discovery",
        "Выявление потребностей",
        "Потребности клиента, влияние, ограничения и согласованный следующий шаг",
        ("summary", "key_points", "action_items", "risks", "questions", "evidence"),
    ),
)

# Keep this immutable v1 fixture separate from the mutable current catalog
# alias.  A future catalog release appends new versioned definitions without
# rewriting the historical rows used by existing outcomes.
BUILT_IN_VERSIONED_TEMPLATES: Final[tuple[SummaryTemplateDefinition, ...]] = _BUILT_IN_TEMPLATE_CATALOG_V1
BUILT_IN_TEMPLATES: Final[tuple[SummaryTemplateDefinition, ...]] = _BUILT_IN_TEMPLATE_CATALOG_V1
BUILT_IN_TEMPLATE_REGISTRY: Final = MappingProxyType(
    {(template.key, template.version): template for template in BUILT_IN_VERSIONED_TEMPLATES}
)
BUILT_IN_BY_KEY: Final = {template.key: template for template in BUILT_IN_TEMPLATES}
PROMPT_NAME_BY_TEMPLATE_KEY: Final = {
    **{template.key: template.prompt_name for template in BUILT_IN_VERSIONED_TEMPLATES},
    "personal": "graf/meeting-outcome/custom",
}


def built_in_template_for_version(
    template_key: str,
    template_version: int,
) -> SummaryTemplateDefinition | None:
    return BUILT_IN_TEMPLATE_REGISTRY.get((template_key, template_version))


def built_in_template_for_key(template_key: str) -> SummaryTemplateDefinition | None:
    current = BUILT_IN_BY_KEY.get(template_key)
    if current is not None:
        return current
    return next(
        (template for template in BUILT_IN_VERSIONED_TEMPLATES if template.key == template_key),
        None,
    )


def prompt_name_for_template(template_key: str, *, built_in: bool) -> str:
    if built_in:
        definition = built_in_template_for_key(template_key)
        if definition is None:
            raise ValueError("unknown built-in template")
        return definition.prompt_name
    return PROMPT_NAME_BY_TEMPLATE_KEY["personal"]
