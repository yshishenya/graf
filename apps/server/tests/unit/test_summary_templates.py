from __future__ import annotations

import pytest
from pydantic import ValidationError

from twobrain_rec_server.api.schemas import CreateSummaryTemplateRequest
from twobrain_rec_server.outcomes.templates import (
    BUILT_IN_TEMPLATES,
    OUTCOME_CATEGORIES,
    prompt_name_for_template,
)


def test_built_ins_are_original_immutable_versioned_definitions() -> None:
    assert [template.key for template in BUILT_IN_TEMPLATES] == [
        "graf-auto-v1",
        "graf-outline-v1",
        "graf-meeting-minutes-v1",
        "graf-project-sync-v1",
        "graf-weekly-team-meeting-v1",
        "graf-one-to-one-v1",
        "graf-client-status-update-v1",
        "graf-interview-v1",
        "graf-sales-discovery-v1",
    ]
    assert BUILT_IN_TEMPLATES[0].sections == OUTCOME_CATEGORIES
    assert len({template.prompt_name for template in BUILT_IN_TEMPLATES}) == len(
        BUILT_IN_TEMPLATES
    )
    assert prompt_name_for_template("graf-auto-v1", built_in=True) == (
        "graf/meeting-outcome/auto"
    )
    assert prompt_name_for_template("anything", built_in=False) == (
        "graf/meeting-outcome/custom"
    )


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
