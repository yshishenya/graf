from copy import deepcopy
from decimal import Decimal
from uuid import UUID

import pytest

from twobrain_rec_server.outcomes.models import OutcomeTranscriptSegment
from twobrain_rec_server.outcomes.prompts import (
    meeting_protocol_config,
    meeting_protocol_schema,
    validate_meeting_protocol,
    validate_prompt_snapshot,
)


def protocol_fixture():
    ref = {"sequence": 0, "quote": "Я сделаю макет, наверное, завтра."}
    statement = {"text": "  Макет обсуждён — риск: нет доступа.  ", "source_refs": [ref]}
    return {
        "schema_version": "graf-meeting-protocol-v1",
        "title": "Обсуждение макета",
        "date_and_time": None,
        "input_type": "Транскрипт",
        "meeting_type": "Рабочая",
        "participants": ["Участник 1"],
        "executive_summary": [deepcopy(statement)],
        "objectives": [],
        "topics": [{
            "title": "Макет", "context": [], "discussion": [deepcopy(statement)],
            "proposals": [], "outcome": [],
        }],
        "decisions": [],
        "action_items": [{
            "task": "Сделать макет", "owner_text": "Участник 1",
            "due_date_text": "наверное, завтра", "source_refs": [deepcopy(ref)],
        }],
        "open_questions": [], "next_steps": [],
        "notes": [{"text": "Дата не указана.", "source_refs": []}],
    }


def source_fixture():
    return [OutcomeTranscriptSegment(
        segment_id=UUID(int=2), sequence=0, start_seconds=Decimal("12.25"),
        end_seconds=Decimal("14"), speaker_label="Участник 1",
        source_role="incoming_system", text="Я сделаю макет, наверное, завтра.",
    )]


def validate(document, segments=None):
    return validate_meeting_protocol(
        document, segments=source_fixture() if segments is None else segments,
        processing_result_id=UUID(int=1),
    )


def test_protocol_preserves_words_and_resolves_only_canonical_sources():
    assert meeting_protocol_schema()["properties"]["schema_version"]["enum"] == ["graf-meeting-protocol-v1"]
    document = protocol_fixture()
    original = deepcopy(document)
    result = validate(document)
    assert document == original
    protocol = result["protocol"]
    assert protocol["executive_summary"][0]["text"] == original["executive_summary"][0]["text"]
    assert protocol["action_items"][0]["due_date_text"] == "наверное, завтра"
    ref = protocol["action_items"][0]["source_refs"][0]
    assert ref["processing_result_id"] == str(UUID(int=1))
    assert ref["transcript_segment_id"] == str(UUID(int=2))
    assert ref["start_seconds"] == 12.25
    assert ref["quote"] == source_fixture()[0].text
    assert result["category_states"]["decisions"] == "not_found"
    assert result["category_states"]["risks"] == "unavailable"
    assert [item["sequence"] for item in result["items"] if item["category"] == "key_points"] == [0, 1]


@pytest.mark.parametrize("sequence", [True, 0.0, "0", -1, 999])
def test_protocol_rejects_invalid_source_sequence(sequence):
    document = protocol_fixture()
    document["executive_summary"][0]["source_refs"][0]["sequence"] = sequence
    with pytest.raises(ValueError):
        validate(document)


@pytest.mark.parametrize("quote", ["я сделаю", "Я  сделаю", "никогда не говорил"])
def test_protocol_does_not_repair_quotes(quote):
    document = protocol_fixture()
    document["executive_summary"][0]["source_refs"][0]["quote"] = quote
    with pytest.raises(ValueError):
        validate(document)


def test_protocol_rejects_duplicate_refs_and_ambiguous_source():
    document = protocol_fixture()
    refs = document["executive_summary"][0]["source_refs"]
    refs.append(deepcopy(refs[0]))
    with pytest.raises(ValueError):
        validate(document)
    with pytest.raises(ValueError):
        validate(protocol_fixture(), source_fixture() * 2)


def test_protocol_requires_evidence_but_not_for_general_notes():
    document = protocol_fixture()
    validate(document)
    document["executive_summary"][0]["source_refs"] = []
    with pytest.raises(ValueError):
        validate(document)


def test_protocol_strict_shape_and_nullable_owner():
    document = protocol_fixture()
    document["action_items"][0]["owner_text"] = None
    document["action_items"][0]["due_date_text"] = None
    assert validate(document)["protocol"]["action_items"][0]["owner_text"] is None
    document["invented_field"] = "ignored?"
    with pytest.raises(ValueError):
        validate(document)


def test_protocol_size_limit_is_explicit_not_truncation():
    document = protocol_fixture()
    document["title"] = "я" * (1024 * 1024)
    with pytest.raises(ValueError, match="size"):
        validate(document)


@pytest.mark.parametrize("expansion", ["references", "flat_projection"])
def test_resolved_protocol_size_is_bounded_after_reference_and_projection_expansion(expansion):
    from dataclasses import replace

    from twobrain_rec_server.outcomes.prompts import canonical_json

    document = protocol_fixture()
    segments = source_fixture()
    if expansion == "references":
        segments = [replace(segments[0], speaker_label="я" * 1024)]
        document["executive_summary"] = [
            {"text": "Решение", "source_refs": [{"sequence": 0, "quote": None}]}
            for _ in range(1100)
        ]
    else:
        document["executive_summary"][0]["text"] = "я" * 550_000
    original = deepcopy(document)
    assert len(canonical_json(document).encode("utf-8")) < 2 * 1024 * 1024
    with pytest.raises(ValueError, match="size"):
        validate(document, segments)
    assert document == original


def test_wire_schema_is_inline_and_has_no_nested_item_limits():
    def inspect(value):
        if isinstance(value, dict):
            assert not {"$ref", "$defs", "maxItems"} & value.keys()
            if value.get("type") == "object":
                assert value["additionalProperties"] is False
                assert set(value["required"]) == set(value["properties"])
            for child in value.values():
                inspect(child)
        elif isinstance(value, list):
            for child in value:
                inspect(child)
    inspect(meeting_protocol_schema())


@pytest.mark.parametrize("model", ["gemini/gemini-3.8-flash", "operator/another-model"])
def test_model_config_is_explicit_without_implicit_parameters(model):
    config = meeting_protocol_config(model=model)
    prompt = [{"role": "system", "content": "{{output_language}} {{detail_level}} {{template_sections_json}} {{meeting_metadata_json}}"},
              {"role": "user", "content": "{{transcript_json}}"}]
    snapshot = validate_prompt_snapshot(name="graf/meeting-outcome/auto", version=1,
                                       prompt_type="chat", prompt=prompt, config=config)
    assert snapshot.litellm_request([]) == {
        "model": model, "messages": [], "response_format": config["response_format"],
    }


@pytest.mark.parametrize("parameters", [
    {"temperature": True}, {"top_p": float("nan")}, {"max_tokens": 0},
    {"max_tokens": 1, "max_completion_tokens": 2}, {"unknown": 1},
])
def test_invalid_model_parameters_are_not_silently_dropped(parameters):
    with pytest.raises(ValueError):
        meeting_protocol_config(model="operator/model", **parameters)


def test_cached_prompt_is_bound_to_project_name_and_label():
    from twobrain_rec_server.cli.langfuse_prompts import outcome_prompt
    from twobrain_rec_server.outcomes.prompts import (
        load_prompt_snapshot,
        persist_prompt_snapshot,
        prompt_cache_key,
    )

    class Storage:
        def put_stream(self, key, stream, length):
            self.data = stream.read(length)
        def get_bytes(self, key):
            return self.data

    snapshot = validate_prompt_snapshot(
        name="graf/meeting-outcome/auto", version=2, prompt_type="chat",
        prompt=outcome_prompt("Авто"), config=meeting_protocol_config(model="operator/model"),
    )
    storage = Storage()
    key = prompt_cache_key(project_identity="project-one", name=snapshot.name, label="dev")
    persist_prompt_snapshot(storage, key=key, snapshot=snapshot)
    assert load_prompt_snapshot(storage, key=key, name=snapshot.name).canonical_hash == snapshot.canonical_hash
    for project, label in [("project-one", "production"), ("project-two", "dev")]:
        other = prompt_cache_key(project_identity=project, name=snapshot.name, label=label)
        with pytest.raises(ValueError, match="identity"):
            load_prompt_snapshot(storage, key=other, name=snapshot.name)
    storage.data = storage.data.replace(b'operator/model', b'operator/other')
    with pytest.raises(ValueError, match="hash"):
        load_prompt_snapshot(storage, key=key, name=snapshot.name)


def test_label_resolution_fetches_current_version_without_sdk_stale_cache():
    from unittest.mock import Mock

    from twobrain_rec_server.observability.langfuse import fetch_prompt_by_label

    client = Mock()
    assert fetch_prompt_by_label(client, name="graf/meeting-outcome/auto", prompt_type="chat", label="dev") is client.get_prompt.return_value
    client.get_prompt.assert_called_once_with(
        "graf/meeting-outcome/auto", label="dev", type="chat", cache_ttl_seconds=0,
        max_retries=0, fetch_timeout_seconds=10,
    )
