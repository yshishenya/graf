from copy import deepcopy
from datetime import UTC, datetime

from tests.fixtures.meeting_protocol import protocol_outcome
from twobrain_rec_server.api.schemas import PublicShareSummaryResponse
from twobrain_rec_server.cabinet.access import narrow_summary_projection


def test_public_link_projection_is_full_protocol_without_nested_evidence() -> None:
    document = protocol_outcome().protocol_json
    document["header"]["participants"] = [
        {"label": "Участник 1", "speaker_key": "internal-key", "attribution_state": "unknown"}
    ]
    original = deepcopy(document)
    projection = narrow_summary_projection(
        meeting_label="Изменённое название",
        occurred_at=datetime(2026, 7, 22, tzinfo=UTC),
        duration_seconds=600,
        protocol=document,
    )

    assert set(projection) == {"meeting_label", "occurred_at", "duration_seconds", "protocol"}
    assert projection["meeting_label"] == document["header"]["title"]
    assert projection["occurred_at"] is None
    assert projection["protocol"]["topics"] == [
        {"title": "Синтетическая тема", "context": [],
         "discussion": [{"text": "Обсудили ограничения пилота."}],
         "proposals_and_alternatives": [], "outcome": []}
    ]
    serialized = repr(projection).lower()
    for forbidden in ("source_refs", "transcript_segment_id", "source_result_id", "quote", "playback", "speaker_key", "template_key", "template_name", "attribution_state"):
        assert forbidden not in serialized
    assert projection["protocol"]["header"]["participants"] == [{"label": "Участник 1"}]
    assert document == original
    PublicShareSummaryResponse.model_validate(projection)


def test_public_link_without_protocol_does_not_invent_meeting_date() -> None:
    projection = narrow_summary_projection(
        meeting_label="Встреча", occurred_at=None, duration_seconds=0, protocol=None,
    )
    assert projection["protocol"] is None
    assert projection["occurred_at"] is None
