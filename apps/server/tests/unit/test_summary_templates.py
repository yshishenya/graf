from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest
from pydantic import ValidationError

from twobrain_rec_server.api.schemas import CreateSummaryTemplateRequest
from twobrain_rec_server.outcomes.templates import (
    BUILT_IN_BY_KEY,
    BUILT_IN_TEMPLATE_REGISTRY,
    BUILT_IN_TEMPLATES,
    BUILT_IN_VERSIONED_TEMPLATES,
    OUTCOME_CATEGORIES,
    built_in_template_for_key,
    built_in_template_for_version,
    prompt_name_for_template,
)


def test_current_built_ins_preserve_keys_names_order_and_prompt_routes() -> None:
    assert OUTCOME_CATEGORIES == (
        "summary", "key_points", "decisions", "action_items",
        "followups", "risks", "questions", "evidence",
    )
    assert [(template.key, template.name) for template in BUILT_IN_TEMPLATES] == [
        ("graf-auto-v1", "Авто"),
        ("graf-outline-v1", "По темам"),
        ("graf-meeting-minutes-v1", "Протокол встречи"),
        ("graf-project-sync-v1", "Синхронизация проекта"),
        ("graf-weekly-team-meeting-v1", "Еженедельная встреча команды"),
        ("graf-one-to-one-v1", "Один на один"),
        ("graf-client-status-update-v1", "Статус для клиента"),
        ("graf-interview-v1", "Интервью с кандидатом"),
        ("graf-sales-discovery-v1", "Выявление потребностей"),
    ]
    assert len({template.prompt_name for template in BUILT_IN_TEMPLATES}) == len(
        BUILT_IN_TEMPLATES
    )
    for template in BUILT_IN_TEMPLATES:
        profile = template.key.removeprefix("graf-").removesuffix("-v1")
        assert template.prompt_name == f"graf/meeting-outcome/{profile}"
        assert prompt_name_for_template(template.key, built_in=True) == template.prompt_name
        assert built_in_template_for_key(template.key) is template
    assert prompt_name_for_template("anything", built_in=False) == (
        "graf/meeting-outcome/custom"
    )


@pytest.mark.parametrize("template", BUILT_IN_TEMPLATES, ids=lambda template: template.key)
def test_each_builtin_is_a_full_protocol_version_two(template) -> None:
    assert template.version == 2
    assert template.sections == OUTCOME_CATEGORIES
    assert template.purpose.startswith("Полный протокол")
    assert len(template.purpose) <= 240
    assert built_in_template_for_version(template.key, 2) is template
    assert built_in_template_for_version(template.key, 1) is None
    with pytest.raises(FrozenInstanceError):
        template.version = 1


def test_version_registry_contains_only_current_definitions() -> None:
    assert BUILT_IN_VERSIONED_TEMPLATES == BUILT_IN_TEMPLATES
    assert set(BUILT_IN_TEMPLATE_REGISTRY) == {(template.key, 2) for template in BUILT_IN_TEMPLATES}
    assert set(BUILT_IN_BY_KEY) == {template.key for template in BUILT_IN_TEMPLATES}
    with pytest.raises(TypeError):
        BUILT_IN_TEMPLATE_REGISTRY[("graf-auto-v1", 1)] = BUILT_IN_TEMPLATES[0]


@pytest.mark.parametrize("version", [0, 1, 3])
def test_unknown_or_retired_version_never_resolves_to_current(version) -> None:
    assert built_in_template_for_version("graf-auto-v1", version) is None


def test_unknown_builtin_fails_closed_but_personal_route_remains_separate() -> None:
    assert built_in_template_for_key("graf-unknown-v1") is None
    assert built_in_template_for_version("graf-unknown-v1", 2) is None
    with pytest.raises(ValueError, match="unknown built-in template"):
        prompt_name_for_template("graf-unknown-v1", built_in=True)
    assert prompt_name_for_template("personal-format", built_in=False) == "graf/meeting-outcome/custom"


def test_personal_template_is_structured_and_bounded() -> None:
    request = CreateSummaryTemplateRequest(
        name="  Мой   формат ",
        purpose="Рабочий формат",
        sections=["summary", "action_items"],
        output_language="ru",
        detail_level="standard",
    )
    assert request.name == "Мой формат"
    assert request.sections == ["summary", "action_items"]
    for sections in (
        [],
        ["summary", "summary"],
        ["summary", "system_prompt"],
        "summary",
    ):
        with pytest.raises(ValidationError):
            CreateSummaryTemplateRequest(
                name="Формат",
                purpose="Рабочий формат",
                sections=sections,
                output_language="ru",
                detail_level="standard",
            )


def test_personal_selection_does_not_expand_or_reorder_sections() -> None:
    request = CreateSummaryTemplateRequest(
        name="Мой формат",
        purpose="Только выбранные разделы",
        sections=["questions", "summary", "action_items"],
        output_language="en",
        detail_level="brief",
    )
    assert request.sections == ["questions", "summary", "action_items"]
    assert request.output_language == "en"
    assert request.detail_level == "brief"


def test_removed_current_key_has_no_catalog_fallback(monkeypatch) -> None:
    monkeypatch.delitem(BUILT_IN_BY_KEY, "graf-auto-v1")
    assert built_in_template_for_key("graf-auto-v1") is None
    with pytest.raises(ValueError, match="unknown built-in template"):
        prompt_name_for_template("graf-auto-v1", built_in=True)
