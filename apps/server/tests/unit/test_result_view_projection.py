"""The digest describes the same body text that the cabinet renders."""

import json
from dataclasses import replace
from hashlib import sha256
from uuid import UUID

import pytest

from tests.unit.test_cabinet_web_shell import _review
from tests.unit.test_meeting_protocol import protocol_fixture, validate
from twobrain_rec_server.api.schemas import (
    OutcomeItemView,
    TranscriptSegmentView,
    TranscriptSpeakerTurnView,
)


def projection_review(kind="segments"):
    review = _review()
    review.meeting.meeting_id = UUID(int=10)
    review.provenance.media_revision_id = UUID(int=11)
    review.template.outcome_set_id = UUID(int=12)
    review.transcript.available = True
    review.transcript.search_enabled = True
    row = dict(
        sequence=0, start_seconds=0, end_seconds=10, timestamp_label="00:00",
        speaker_label="Синтетическое имя", source_role="canonical_mixed",
        text="  Точный <текст> & пробелы.  ", processing_result_id=UUID(int=13),
    )
    review.transcript.segments = [TranscriptSegmentView(segment_id="segment", **row)]
    if kind == "turns":
        review.transcript.speaker_turns = [TranscriptSpeakerTurnView(
            turn_id="turn", **(row | {"text": "Показанный turn"}),
        )]
    if kind == "unavailable":
        review.transcript.available = False
    if kind == "no_search":
        review.transcript.search_enabled = False
    if kind == "plain":
        for category in ("summary", "action_items", "decisions"):
            state = getattr(review.notes_action_truth, category).model_copy(deep=True)
            state.state = "available"
            state.items = [OutcomeItemView(
                category=category, sequence=0, text=f"Тело {category}",
                owner_text="Имя ответственного", due_date_text="завтра",
                truth_label="supported",
            )]
            setattr(review.notes_action_truth, category, state)
    if kind == "protocol":
        review.notes_action_truth.protocol = validate(protocol_fixture())["protocol"]
    return review


@pytest.mark.parametrize("kind,expected", [
    ("segments", ["  Точный <текст> & пробелы.  "]),
    ("turns", ["Показанный turn"]),
    ("unavailable", []),
    ("no_search", []),
])
def test_projection_uses_the_displayed_transcript_rows(kind, expected):
    from twobrain_rec_server.cabinet.result_visibility import result_view_text_blocks

    blocks = result_view_text_blocks(projection_review(kind))
    assert [text for _, block_type, text in blocks if block_type == "transcript"] == expected


def test_projection_ignores_metadata_unavailable_items_and_blank_text():
    from twobrain_rec_server.cabinet.result_visibility import result_view_text_blocks

    review = projection_review("plain")
    review.transcript.segments[0].text = " \n\t "
    review.notes_action_truth.decisions.state = "unsafe"
    review.notes_action_truth.summary.items.append(OutcomeItemView(
        category="summary", sequence=1, text=" \n ", truth_label="supported",
    ))
    blocks = result_view_text_blocks(review)
    assert [(kind, text) for _, kind, text in blocks] == [
        ("summary", "Тело summary"), ("action_items", "Тело action_items"),
    ]
    assert len({key for key, _, _ in blocks}) == len(blocks)
    serialized = json.dumps(blocks, ensure_ascii=False)
    for metadata in (review.meeting.title, "Имя ответственного", "завтра", "Синтетическое имя"):
        assert metadata not in serialized


def test_protocol_projection_preserves_render_order_without_titles_or_empty_messages():
    from twobrain_rec_server.cabinet.result_visibility import result_view_text_blocks

    review = projection_review("protocol")
    review.transcript.available = False
    protocol = review.notes_action_truth.protocol
    protocol["open_questions"] = [{"text": "Вопрос", "source_refs": []}]
    protocol["next_steps"] = [{"text": "Следующий шаг", "source_refs": []}]
    protocol["topics"][0]["outcome"] = [{"text": "Итог темы", "source_refs": []}]
    blocks = result_view_text_blocks(review)
    assert [(kind, text) for _, kind, text in blocks] == [
        ("summary", "  Макет обсуждён — риск: нет доступа.  "),
        ("action_items", "Сделать макет"),
        ("outcome", "Вопрос"), ("outcome", "Следующий шаг"),
        ("outcome", "Итог темы"),
        ("outcome", "  Макет обсуждён — риск: нет доступа.  "),
        ("outcome", "Дата не указана."),
    ]
    assert len({key for key, _, _ in blocks}) == len(blocks)


def test_protocol_metadata_and_empty_disclosures_do_not_become_result_text():
    from twobrain_rec_server.cabinet.result_visibility import result_view_text_blocks

    review = projection_review("protocol")
    review.transcript.available = False
    protocol = review.notes_action_truth.protocol
    for key in ("executive_summary", "decisions", "action_items", "open_questions", "next_steps", "notes"):
        protocol[key] = []
    for key in ("outcome", "context", "discussion", "proposals"):
        protocol["topics"][0][key] = []
    assert result_view_text_blocks(review) == []


def test_digest_is_canonical_binds_its_own_result_and_preserves_original_text():
    from twobrain_rec_server.cabinet.result_visibility import (
        ResultViewSource,
        result_view_block_digest,
    )

    source = ResultViewSource(
        owner_id=UUID(int=1), workspace_id=UUID(int=2), meeting_id=UUID(int=10),
        media_revision_id=UUID(int=11), source_fingerprint="a" * 64,
        result_id=UUID(int=13), result_version=2, deletion_epoch=0,
        first_recording_completed=False,
    )
    text = "  Точный <текст> & пробелы.  "
    expected = sha256(json.dumps({
        "type": "transcript", "result_id": str(source.result_id), "result_version": 2,
        "texts": [text],
    }, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    digest = result_view_block_digest(source, block_type="transcript", texts=[text])
    assert digest == expected
    assert result_view_block_digest(source, block_type="transcript", texts=[text.strip()]) != digest
    assert result_view_block_digest(
        replace(source, result_version=3), block_type="transcript", texts=[text],
    ) != digest
    assert result_view_block_digest(
        replace(source, result_id=UUID(int=14)), block_type="transcript", texts=[text],
    ) != digest
    assert result_view_block_digest(
        source, block_type="summary", texts=[text], outcome_set_id=UUID(int=12),
    ) != result_view_block_digest(
        source, block_type="summary", texts=[text], outcome_set_id=UUID(int=15),
    )
    assert result_view_block_digest(source, block_type="summary", texts=["a", "b"]) != (
        result_view_block_digest(source, block_type="summary", texts=["b", "a"])
    )


@pytest.mark.parametrize("kind,texts", [
    ("transcript", []), ("transcript", [" \t\n "]), ("title", ["Название"]),
])
def test_empty_or_unapproved_body_cannot_produce_a_digest(kind, texts):
    from twobrain_rec_server.cabinet.result_visibility import (
        ResultViewSource,
        result_view_block_digest,
    )

    source = ResultViewSource(
        owner_id=UUID(int=1), workspace_id=UUID(int=2), meeting_id=UUID(int=10),
        media_revision_id=UUID(int=11), source_fingerprint="a" * 64,
        result_id=UUID(int=13), result_version=2, deletion_epoch=0,
        first_recording_completed=False,
    )
    assert result_view_block_digest(source, block_type=kind, texts=texts) is None
