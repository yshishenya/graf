from twobrain_rec_server.api.schemas import (
    TranscriptReviewState,
    TranscriptSegmentView,
    TranscriptSpeakerTurnView,
)


def test_transcript_contract_keeps_raw_segments_and_adds_speaker_turns() -> None:
    raw = TranscriptSegmentView(
        segment_id="raw-segment-1",
        speaker_key="speaker_00",
        sequence=3,
        start_seconds=10.0,
        end_seconds=11.0,
        timestamp_label="00:10",
        speaker_label="SPEAKER_00",
        source_role="incoming_system",
        text="synthetic raw text",
    )
    turn = TranscriptSpeakerTurnView(
        turn_id="raw-segment-1",
        speaker_key="speaker_00",
        sequence=3,
        start_seconds=10.0,
        end_seconds=12.0,
        timestamp_label="00:10",
        speaker_label="SPEAKER_00",
        source_role="incoming_system",
        text="synthetic merged text",
        source_segment_ids=["raw-segment-1", "raw-segment-2"],
    )

    state = TranscriptReviewState(
        available=True,
        language="ru",
        search_enabled=True,
        segments=[raw],
        speaker_turns=[turn],
    )

    payload = state.model_dump()

    assert payload["segments"][0]["segment_id"] == "raw-segment-1"
    assert payload["segments"][0]["speaker_key"] == "speaker_00"
    assert payload["segments"][0]["text"] == "synthetic raw text"
    assert payload["speaker_turns"][0]["turn_id"] == "raw-segment-1"
    assert payload["speaker_turns"][0]["speaker_key"] == "speaker_00"
    assert payload["speaker_turns"][0]["source_segment_ids"] == [
        "raw-segment-1",
        "raw-segment-2",
    ]
    assert "mediascribe_job_id" not in payload["speaker_turns"][0]
    assert "api_key" not in payload["speaker_turns"][0]


def test_transcript_contract_defaults_speaker_turns_to_empty() -> None:
    state = TranscriptReviewState(available=False)

    assert state.speaker_turns == []
