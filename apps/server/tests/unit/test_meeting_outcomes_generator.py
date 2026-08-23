from __future__ import annotations

import importlib
import json
from decimal import Decimal
from uuid import uuid4


def _generator_module():
    try:
        return importlib.import_module("twobrain_rec_server.outcomes.generator")
    except ModuleNotFoundError as exc:
        raise AssertionError("outcome generator module is missing") from exc


def test_extractive_generator_creates_supported_items_with_source_refs() -> None:
    generator = _generator_module()
    segment = generator.OutcomeTranscriptSegment(
        segment_id=uuid4(),
        sequence=0,
        start_seconds=Decimal("5.000"),
        end_seconds=Decimal("15.000"),
        speaker_label="Speaker 1",
        source_role="mic",
        text="Синтетическая встреча: обсудили запуск кабинета и договорились проверить итоговый экран.",
    )

    payload = generator.generate_outcomes([segment])

    assert payload.category_states["summary"] == "available"
    assert payload.category_states["key_points"] == "available"
    assert payload.category_states["evidence"] == "available"
    assert payload.items_by_category["summary"][0].source_refs[0].sequence == 0
    assert payload.items_by_category["summary"][0].truth_label == "supported"


def test_extractive_generator_marks_unsupported_categories_without_fabrication() -> None:
    generator = _generator_module()
    segment = generator.OutcomeTranscriptSegment(
        segment_id=uuid4(),
        sequence=0,
        start_seconds=Decimal("0.000"),
        end_seconds=Decimal("9.000"),
        speaker_label="Speaker 1",
        source_role="incoming",
        text="Синтетический разговор без решений, владельцев, сроков и поручений.",
    )

    payload = generator.generate_outcomes([segment])

    for category in ["decisions", "action_items", "followups", "risks", "questions"]:
        assert payload.category_states[category] in {"not_found", "not_inferable"}
        assert payload.items_by_category[category] == []
    for items in payload.items_by_category.values():
        assert all(item.owner_text is None for item in items)
        assert all(item.due_date_text is None for item in items)


def test_extractive_generator_detects_question_cues_without_question_mark() -> None:
    generator = _generator_module()
    segment = generator.OutcomeTranscriptSegment(
        segment_id=uuid4(),
        sequence=0,
        start_seconds=Decimal("11.000"),
        end_seconds=Decimal("18.000"),
        speaker_label="Speaker 2",
        source_role="incoming",
        text="У меня есть вопрос по итогам встречи и следующему шагу.",
    )

    payload = generator.generate_outcomes([segment])

    assert payload.category_states["questions"] == "available"
    assert payload.items_by_category["questions"][0].source_refs[0].sequence == 0


def test_outcomes_keep_canonical_input_order_and_all_speaker_fields() -> None:
    generator = _generator_module()
    first = generator.OutcomeTranscriptSegment(
        segment_id=uuid4(),
        sequence=5,
        start_seconds=Decimal("0.000"),
        end_seconds=Decimal("1.000"),
        speaker_label="Первый",
        speaker_key="provider:result:first",
        provider_speaker_key="raw-first",
        attribution_state="confirmed",
        result_state="accepted",
        source_role="mic",
        text="Первая каноническая реплика.",
    )
    second = generator.OutcomeTranscriptSegment(
        segment_id=uuid4(),
        sequence=1,
        start_seconds=Decimal("1.000"),
        end_seconds=Decimal("2.000"),
        speaker_label="Второй",
        speaker_key="provider:result:second",
        provider_speaker_key="raw-second",
        attribution_state="confirmed",
        result_state="accepted",
        source_role="incoming",
        text="Вторая каноническая реплика.",
    )

    transcript = json.loads(generator.canonical_transcript([first, second]))
    outcomes = generator.generate_outcomes([first, second])

    assert [row["text"] for row in transcript] == [first.text, second.text]
    assert transcript[0] == {
        "attribution_state": "confirmed",
        "end_seconds": "1.000",
        "provider_speaker_key": "raw-first",
        "result_state": "accepted",
        "sequence": 5,
        "source_role": "mic",
        "speaker_key": "provider:result:first",
        "speaker_label": "Первый",
        "start_seconds": "0.000",
        "text": "Первая каноническая реплика.",
        "transcript_segment_id": str(first.segment_id),
    }
    assert outcomes.items_by_category["summary"][0].text == first.text
