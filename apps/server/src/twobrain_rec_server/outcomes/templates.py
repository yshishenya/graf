from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Final

# Stable personal section selections; the protocol contract maps these keys
# to nested fields. They are not a registry of legacy outcome payloads.
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
    version: int = 2


def _built_in(
    key: str,
    name: str,
    purpose: str,
) -> SummaryTemplateDefinition:
    return SummaryTemplateDefinition(
        # The suffix is part of the stable identity, not the definition version.
        key=f"graf-{key}-v1",
        name=name,
        purpose=purpose,
        sections=OUTCOME_CATEGORIES,
        prompt_name=f"graf/meeting-outcome/{key}",
    )


BUILT_IN_TEMPLATES: Final[tuple[SummaryTemplateDefinition, ...]] = (
    _built_in(
        "auto",
        "Авто",
        "Полный протокол с учётом типа встречи: темы, решения, задачи, риски и открытые вопросы",
    ),
    _built_in(
        "outline",
        "По темам",
        "Полный протокол по темам разговора: контекст, обсуждение, варианты и итог каждой темы",
    ),
    _built_in(
        "meeting-minutes",
        "Протокол встречи",
        "Полный протокол с акцентом на принятые решения, обязательства и согласованные следующие шаги",
    ),
    _built_in(
        "project-sync",
        "Синхронизация проекта",
        "Полный протокол проекта: прогресс, вехи, препятствия, зависимости и договорённости",
    ),
    _built_in(
        "weekly-team-meeting",
        "Еженедельная встреча команды",
        "Полный протокол команды: изменения за неделю, приоритеты, препятствия и совместные действия",
    ),
    _built_in(
        "one-to-one",
        "Один на один",
        "Полный протокол личной рабочей встречи: темы сотрудника, нагрузка, поддержка и взаимные договорённости",
    ),
    _built_in(
        "client-status-update",
        "Статус для клиента",
        "Полный протокол для клиента: подтверждённый прогресс, потребности, риски и согласованные шаги",
    ),
    _built_in(
        "interview",
        "Интервью с кандидатом",
        "Полный протокол интервью: темы вопросов, фактические ответы и уточнения без домыслов о кандидате",
    ),
    _built_in(
        "sales-discovery",
        "Выявление потребностей",
        "Полный протокол о потребностях клиента: критерии, возражения, ограничения и согласованный следующий шаг",
    ),
)

# Existing API names expose only the current definitions. Historical snapshots
# stay in storage; no retired definition is available for generation/rendering.
BUILT_IN_VERSIONED_TEMPLATES: Final[tuple[SummaryTemplateDefinition, ...]] = BUILT_IN_TEMPLATES
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
    return BUILT_IN_BY_KEY.get(template_key)


def prompt_name_for_template(template_key: str, *, built_in: bool) -> str:
    if built_in:
        definition = built_in_template_for_key(template_key)
        if definition is None:
            raise ValueError("unknown built-in template")
        return definition.prompt_name
    return PROMPT_NAME_BY_TEMPLATE_KEY["personal"]
