from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from twobrain_rec_server.domain.speaker_turns import canonical_speaker_model

RESULT_ID = UUID("00000000-0000-0000-0000-000000000182")


@dataclass(frozen=True)
class Row:
    sequence: int
    start_seconds: Decimal
    end_seconds: Decimal
    text: str
    source_role: str = "mixed"
    speaker_label: str = ""
    id: UUID = UUID("00000000-0000-0000-0000-000000000001")
    processing_result_id: UUID = RESULT_ID


def row(
    sequence: int,
    start: str,
    end: str,
    text: str,
    speaker: str = "",
) -> Row:
    return Row(
        sequence=sequence,
        start_seconds=Decimal(start),
        end_seconds=Decimal(end),
        text=text,
        speaker_label=speaker,
        id=UUID(f"00000000-0000-0000-0000-{sequence + 1:012d}"),
    )


def test_one_asr_segment_preserves_two_provider_turns() -> None:
    model = canonical_speaker_model(
        [row(0, "0.000", "4.000", "Alpha beta gamma delta")],
        [
            row(0, "0.000", "1.500", "Alpha beta", "voice-a"),
            row(1, "1.500", "4.000", "gamma delta", "voice-b"),
        ],
        processing_result_id=RESULT_ID,
    )

    assert model.result_state == "accepted"
    assert [(turn.start_seconds, turn.end_seconds) for turn in model.turns] == [
        (Decimal("0.000"), Decimal("1.500")),
        (Decimal("1.500"), Decimal("4.000")),
    ]
    assert [turn.provider_speaker_key for turn in model.turns] == ["voice-a", "voice-b"]
    assert model.diagnostics.multi_label_conflict_count == 1


def test_one_asr_segment_preserves_three_turns_without_winner() -> None:
    model = canonical_speaker_model(
        [row(0, "0", "3", "one two three")],
        [
            row(0, "0", "1", "one", "a"),
            row(1, "1", "2", "two", "b"),
            row(2, "2", "3", "three", "c"),
        ],
        processing_result_id=RESULT_ID,
    )

    assert [turn.text for turn in model.turns] == ["one", "two", "three"]
    assert all(turn.attribution_state == "confirmed" for turn in model.turns)
    assert len({turn.speaker_key for turn in model.turns}) == 3


def test_below_half_overlap_never_becomes_confirmed_asr_assignment() -> None:
    model = canonical_speaker_model(
        [row(0, "0", "10", "one two")],
        [
            row(0, "0", "4.9", "one", "a"),
            row(1, "4.9", "10", "two", "b"),
        ],
        processing_result_id=RESULT_ID,
    )

    assert len(model.turns) == 2
    assert not any(
        turn.start_seconds == Decimal("0") and turn.end_seconds == Decimal("10")
        for turn in model.turns
    )


def test_tiny_unknown_degrades_without_confirmed_third_participant() -> None:
    model = canonical_speaker_model(
        [row(0, "0", "2", "one two unknown")],
        [
            row(0, "0", "0.98", "one", "a"),
            row(1, "0.98", "1.96", "two", "b"),
            row(2, "1.96", "2.00", "unknown", "UNKNOWN"),
        ],
        processing_result_id=RESULT_ID,
    )

    assert model.result_state == "degraded_provider_result"
    assert model.diagnostics.unknown_tiny_count == 1
    assert len(model.turns) == 1
    assert model.turns[0].text == "one two unknown"
    assert model.turns[0].attribution_state == "uncertain"
    assert model.confirmed_speaker_keys == ()


def test_triplicated_full_text_degrades_and_outputs_asr_once() -> None:
    transcript = [row(0, "0", "3", "synthetic conservation phrase")]
    provider = [
        row(index, str(index), str(index + 1), "synthetic conservation phrase", f"s{index}")
        for index in range(3)
    ]

    model = canonical_speaker_model(transcript, provider, processing_result_id=RESULT_ID)

    assert model.result_state == "degraded_provider_result"
    assert model.diagnostics.duplicate_text_count == 3
    assert [turn.text for turn in model.turns] == ["synthetic conservation phrase"]


def test_stable_one_two_and_eleven_label_models_are_idempotent() -> None:
    for speaker_count in (1, 2, 11):
        words = [f"word{index}" for index in range(speaker_count)]
        transcript = [row(0, "0", str(speaker_count), " ".join(words))]
        provider = [
            row(index, str(index), str(index + 1), word, f"raw-{speaker_count - index:02d}")
            for index, word in enumerate(words)
        ]
        first = canonical_speaker_model(transcript, provider, processing_result_id=RESULT_ID)
        second = canonical_speaker_model(transcript, provider, processing_result_id=RESULT_ID)

        assert first == second
        assert len(first.confirmed_speaker_keys) == speaker_count


def test_provider_key_is_stable_when_display_order_changes() -> None:
    first = canonical_speaker_model(
        [row(0, "0", "2", "alpha beta")],
        [row(0, "0", "1", "alpha", "raw-a"), row(1, "1", "2", "beta", "raw-b")],
        processing_result_id=RESULT_ID,
    )
    rebuilt = canonical_speaker_model(
        [row(0, "0", "2", "beta alpha")],
        [row(0, "0", "1", "beta", "raw-b"), row(1, "1", "2", "alpha", "raw-a")],
        processing_result_id=RESULT_ID,
    )

    first_keys = {turn.provider_speaker_key: turn.speaker_key for turn in first.turns}
    rebuilt_keys = {turn.provider_speaker_key: turn.speaker_key for turn in rebuilt.turns}
    assert first_keys == rebuilt_keys
    assert [turn.canonical_label for turn in rebuilt.turns] == ["SPEAKER_00", "SPEAKER_01"]


def test_source_precision_is_not_rounded_in_canonical_model() -> None:
    model = canonical_speaker_model(
        [row(0, "0.0004", "1.0006", "alpha")],
        [row(0, "0.0004", "1.0006", "alpha", "raw-a")],
        processing_result_id=RESULT_ID,
    )

    assert model.turns[0].start_seconds == Decimal("0.0004")
    assert model.turns[0].end_seconds == Decimal("1.0006")
