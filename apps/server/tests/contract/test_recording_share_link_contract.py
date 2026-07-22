from datetime import UTC, datetime

from twobrain_rec_server.cabinet.access import narrow_summary_projection


def test_public_link_projection_is_summary_only() -> None:
    projection = narrow_summary_projection(
        meeting_label="Синтетическая встреча",
        occurred_at=datetime(2026, 7, 22, tzinfo=UTC),
        duration_seconds=600,
        summary_sections=[{"category": "summary", "text": "Synthetic"}],
    )

    assert set(projection) == {
        "meeting_label",
        "occurred_at",
        "duration_seconds",
        "summary_sections",
    }
    serialized = repr(projection).lower()
    for forbidden in ("transcript", "playback", "speaker", "participant", "template"):
        assert forbidden not in serialized
