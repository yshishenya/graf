"""The digest describes the same body text that the cabinet renders."""

import json
import re
from dataclasses import replace
from hashlib import sha256
from html.parser import HTMLParser
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


@pytest.mark.parametrize("kind", ["segments", "turns", "plain", "protocol", "unavailable", "no_search"])
@pytest.mark.parametrize("embedded", [False, True])
def test_proof_attributes_belong_only_to_the_corresponding_body_and_preserve_html(kind, embedded):
    from twobrain_rec_server.cabinet.rendering import (
        render_meeting_detail_fragment,
        render_meeting_detail_page,
    )
    from twobrain_rec_server.cabinet.result_visibility import result_view_text_blocks

    review = projection_review(kind)
    if kind == "protocol":
        protocol = review.notes_action_truth.protocol
        for category in ("executive_summary", "decisions", "open_questions", "next_steps", "notes"):
            protocol[category] = [{"text": f"{category}:{index}", "source_refs": []} for index in range(2)]
        protocol["action_items"] *= 2
        protocol["topics"].append(dict(protocol["topics"][0]))
        for topic_index, topic in enumerate(protocol["topics"]):
            for part in ("outcome", "context", "discussion", "proposals"):
                topic[part] = [{"text": f"{topic_index}:{part}:{index}", "source_refs": []} for index in range(2)]
    elif kind == "plain":
        review.notes_action_truth.summary.items.insert(0, OutcomeItemView(
            category="summary", sequence=0, text=" \n ", truth_label="supported",
        ))
    blocks = result_view_text_blocks(review)
    proofs = {key: f"synthetic-{index}." + "a" * 64 for index, (key, _, _) in enumerate(blocks)}
    expected = {proofs[key]: text for key, _, text in blocks}

    class Bodies(HTMLParser):
        def __init__(self):
            super().__init__()
            self.current = None
            self.values = {}

        def handle_starttag(self, tag, attrs):
            proof = dict(attrs).get("data-result-view-proof")
            if proof:
                assert self.current is None and tag in {"p", "div"}
                assert proof not in self.values
                self.current = proof
                self.values[proof] = ""

        def handle_data(self, text):
            if self.current:
                self.values[self.current] += text

        def handle_endtag(self, tag):
            if tag in {"p", "div"}:
                self.current = None

    for render in (render_meeting_detail_page, render_meeting_detail_fragment):
        before = render(review, embedded=embedded)
        assert render(review, embedded=embedded, result_view_proofs={}) == before
        after = render(review, embedded=embedded, result_view_proofs=proofs)
        parser = Bodies()
        parser.feed(after)
        assert parser.values == expected
        assert re.sub(r' data-result-view-proof="[^"]*"', "", after) == before


def test_proof_attribute_is_escaped_without_changing_the_body_or_other_attributes():
    from twobrain_rec_server.cabinet.rendering import render_meeting_detail_page
    from twobrain_rec_server.cabinet.result_visibility import result_view_text_blocks

    review = projection_review("plain")
    proof = '\" onmouseover=\"synthetic\"><script>synthetic</script>&'
    blocks = result_view_text_blocks(review)
    proofs = {key: proof for key, _, _ in blocks}
    html = render_meeting_detail_page(review, result_view_proofs=proofs)

    class Attributes(HTMLParser):
        def handle_starttag(self, tag, attrs):
            values = dict(attrs)
            if "data-result-view-proof" in values:
                assert values == {"class": "text" if tag == "div" else "outcome-item-text",
                                  "data-result-view-proof": proof}
                self.count += 1

    parser = Attributes()
    parser.count = 0
    parser.feed(html)
    assert parser.count == len(blocks)
    assert re.sub(r' data-result-view-proof="[^"]*"', "", html) == render_meeting_detail_page(review)


def test_blank_bodies_and_unavailable_outcomes_cannot_receive_a_proof():
    from twobrain_rec_server.cabinet.rendering import render_meeting_detail_page
    from twobrain_rec_server.cabinet.result_visibility import result_view_text_blocks

    review = projection_review("plain")
    proofs = {key: "synthetic" for key, _, _ in result_view_text_blocks(review)}
    proofs["title"] = "synthetic"
    review.transcript.segments[0].text = " \n\t "
    review.notes_action_truth.summary.items[0].text = " \t "
    review.notes_action_truth.action_items.state = "unsafe"
    review.notes_action_truth.decisions.items[0].text = ""
    before = render_meeting_detail_page(review)
    assert render_meeting_detail_page(review, result_view_proofs=proofs) == before
    assert "data-result-view-proof" not in before


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
