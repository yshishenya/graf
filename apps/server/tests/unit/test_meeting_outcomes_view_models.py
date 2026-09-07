
import pytest

from tests.fixtures.meeting_protocol import protocol_outcome
from twobrain_rec_server.cabinet import view_models
from twobrain_rec_server.outcomes.ai_service import _content_hash


def test_stored_protocol_preserves_topics_and_canonical_sources():
    outcome = protocol_outcome()
    truth = view_models.stored_outcome_truth_state(outcome)
    assert truth.protocol.executive_summary[0].text == "Обсудили ограничения пилота."
    assert truth.protocol.topics[0].discussion[0].source_refs[0].start_seconds == 12.5
    assert truth.protocol.header["title"] == "Проверка пилота"
    assert truth.summary.state == truth.key_points.state == "available"
    assert truth.decisions.state == "not_found"
    assert "items" not in truth.summary.model_dump()


def test_historical_flat_output_is_unavailable_and_never_projected():
    outcome = protocol_outcome()
    outcome.protocol_json = None
    outcome.protocol_schema_version = None
    truth = view_models.stored_outcome_truth_state(outcome)
    assert truth.protocol is None
    assert "items" not in truth.summary.model_dump()
    assert truth.summary.state == "unavailable"
    assert truth.summary.reason == "Нужно сформировать новую версию итогов."


@pytest.mark.parametrize("field,value", [
    ("participants", None), ("participants", ["invented"]),
    ("duration_seconds", "NaN"), ("duration_seconds", True),
    ("started_at", "not-a-date"), ("sections", ["unknown"]),
])
def test_malformed_frozen_header_is_rejected_before_rendering(field, value):
    outcome = protocol_outcome()
    outcome.protocol_json["header"][field] = value
    outcome.content_hash = _content_hash(outcome.protocol_json)
    assert view_models.meeting_protocol_view(outcome) is None


def test_corrupt_protocol_is_unavailable_without_partial_rendering():
    outcome = protocol_outcome()
    outcome.protocol_json["executive_summary"][0]["text"] = "Изменено без нового хеша"
    truth = view_models.stored_outcome_truth_state(outcome)
    assert truth.protocol is None
    assert truth.summary.state == "unavailable"


def test_protocol_html_has_full_structure_task_empty_state_and_safe_inline_sources():
    from twobrain_rec_server.cabinet.rendering import render_meeting_protocol

    protocol = view_models.meeting_protocol_view(protocol_outcome())
    ref = protocol.executive_summary[0].source_refs[0]
    protocol.topics[0].title = "<script>alert(1)</script>"
    html = render_meeting_protocol(protocol, source_segment_ids={str(ref.transcript_segment_id)})
    assert "Ключевые итоги" in html and "Ключевые обсуждения" in html
    assert "Контекст" not in html  # absent optional topic subsection
    assert 'data-seek-seconds="12.5"' in html
    assert 'data-source-segment="' in html
    assert "<table" in html and "Задачи не зафиксированы" in html
    assert "Принятые решения в расшифровке не зафиксированы." in html
    assert "Не назначен" in html and "Не указан" in html
    assert "<script>" not in html and "&lt;script&gt;" in html
    assert "Имена спикеров указаны только" in html
    narrowed = render_meeting_protocol(protocol)
    assert "data-seek-seconds" not in narrowed and "data-source-segment" not in narrowed
    assert "[00:12]" in narrowed  # retained evidence time, no false destination


def test_protocol_html_keeps_personal_order_and_does_not_expose_unselected_sections():
    from twobrain_rec_server.cabinet.rendering import render_meeting_protocol

    protocol = view_models.meeting_protocol_view(protocol_outcome())
    protocol.header["sections"] = ["action_items", "executive_summary"]
    html = render_meeting_protocol(protocol)
    assert html.index(">Задачи<") < html.index(">Ключевые итоги<")
    assert "Ключевые обсуждения" not in html
    assert "Имена спикеров указаны только" in html
