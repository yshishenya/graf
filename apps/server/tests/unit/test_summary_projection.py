from twobrain_rec_server.cabinet.summary_sharing import reader_projection, reader_protocol


def test_recursive_sensitive_unknown_fields_are_dropped():
    protocol = {
        "title": "Title",
        "executive_summary": [
            {
                "text": "Outcome",
                "quote": "raw",
                "source_refs": [{"url": "secret"}],
                "email": "private",
            }
        ],
        "participants": ["A"],
        "secret": {"token": "x"},
        "topics": [
            {
                "title": "Topic",
                "discussion": [{"text": "Discussed", "speaker_id": "x"}],
                "source_url": "x",
            }
        ],
    }
    cleaned = reader_protocol(protocol)
    assert "secret" not in cleaned
    assert cleaned["executive_summary"] == [{"text": "Outcome"}]
    assert cleaned["topics"][0]["discussion"] == [{"text": "Discussed"}]
    projection = reader_projection(
        {
            "meeting_label": "Title",
            "occurred_at": "2026-10-06T00:00:00+00:00",
            "duration_seconds": 2,
            "summary_sections": [{"category": "summary", "text": "Text", "source_url": "x"}],
            "protocol": protocol,
            "secret": "x",
        }
    )
    assert projection["summary_sections"] == [{"category": "summary", "text": "Text"}]
    assert "secret" not in projection
