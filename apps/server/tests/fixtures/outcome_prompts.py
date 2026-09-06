"""Explicit synthetic Langfuse settings; production templates have no defaults."""

from twobrain_rec_server.cli.langfuse_prompts import desired_prompts as prompt_templates
from twobrain_rec_server.outcomes.prompts import PromptSnapshot, validate_prompt_snapshot
from twobrain_rec_server.outcomes.prompts import judge_config as judge_template
from twobrain_rec_server.outcomes.prompts import outcome_config as outcome_template


def outcome_config(*, schema_name: str) -> dict[str, object]:
    return {**outcome_template(schema_name=schema_name), "model": "gpt-5.6-luna", "temperature": 1}


def judge_config(*, schema_name: str) -> dict[str, object]:
    return {**judge_template(schema_name=schema_name), "model": "gpt-5.6-luna", "temperature": 1}


def desired_prompts() -> dict[str, tuple[str, object, dict[str, object]]]:
    return {
        name: (kind, prompt, {**config, "model": "gpt-5.6-luna", "temperature": 1})
        for name, (kind, prompt, config) in prompt_templates().items()
    }


def pin_model_settings(attempt) -> PromptSnapshot:
    """Finish an explicitly prepared synthetic attempt before exercising runtime guards."""
    from twobrain_rec_server.outcomes.ai_service import (
        _ai_generator_config_hash,
        _template_sections,
    )

    snapshot = validate_prompt_snapshot(
        name=attempt.prompt_name, version=attempt.prompt_version, prompt_type="chat",
        prompt=attempt.prompt_definition, config=attempt.prompt_config, source=attempt.prompt_source,
    )
    attempt.model_route = snapshot.model
    attempt.model_parameters = snapshot.model_parameters
    attempt.generator_config_hash = _ai_generator_config_hash(
        template_id=attempt.template_id, template_key=attempt.template_key,
        template_version=attempt.template_version, template_sections=_template_sections(attempt),
        output_language=attempt.output_language, detail_level=attempt.detail_level, snapshot=snapshot,
    )
    return snapshot
