from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from twobrain_rec_server.domain import speaker_turns as speaker_turns_module
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
    source_role: str = "mixed",
) -> Row:
    return Row(
        sequence=sequence,
        start_seconds=Decimal(start),
        end_seconds=Decimal(end),
        text=text,
        source_role=source_role,
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
        [row(0, "0", "10", "one two three")],
        [
            row(0, "0", "4", "one", "a"),
            row(1, "4", "7", "two", "b"),
            row(2, "7", "10", "three", "c"),
        ],
        processing_result_id=RESULT_ID,
    )

    assert max(turn.end_seconds - turn.start_seconds for turn in model.turns) < Decimal("5")
    assert len(model.turns) == 3
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
    assert [turn.text for turn in model.turns] == ["one", "two", "unknown"]
    assert [turn.attribution_state for turn in model.turns] == [
        "confirmed",
        "confirmed",
        "unknown",
    ]
    assert [turn.speaker_label for turn in model.turns] == [
        "SPEAKER_00",
        "SPEAKER_01",
        "Спикер не определён",
    ]
    assert model.diagnostics.accepted_turn_count == 3
    assert len(model.confirmed_speaker_keys) == 2


def test_invalid_asr_timing_never_confirms_provider_attribution() -> None:
    model = canonical_speaker_model(
        [row(0, "2", "1", "synthetic text")],
        [row(0, "0", "1", "synthetic text", "voice-a")],
        processing_result_id=RESULT_ID,
    )

    assert model.result_state == "degraded_provider_result"
    assert "invalid_transcript_timing" in model.diagnostics.reason_codes
    assert model.diagnostics.accepted_turn_count == 0
    assert model.confirmed_speaker_keys == ()
    assert [turn.attribution_state for turn in model.turns] == ["uncertain"]


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


def test_repeated_text_in_separate_asr_turns_is_not_duplicate_provider_text() -> None:
    model = canonical_speaker_model(
        [
            row(0, "0", "1", "hello"),
            row(1, "2", "3", "hello"),
        ],
        [
            row(0, "0", "1", "hello", "a"),
            row(1, "2", "3", "hello", "b"),
        ],
        processing_result_id=RESULT_ID,
    )

    assert model.result_state == "accepted"
    assert model.diagnostics.duplicate_text_count == 0
    assert model.diagnostics.text_conservation_status == "matched"


def test_text_conservation_ignores_punctuation_and_case_representation() -> None:
    model = canonical_speaker_model(
        [row(0, "0", "1", "Привет, мир!")],
        [row(0, "0", "1", "привет мир", "voice-a")],
        processing_result_id=RESULT_ID,
    )

    assert model.result_state == "accepted"
    assert model.diagnostics.text_conservation_status == "matched"


def test_text_conservation_treats_typographic_symbols_as_representation() -> None:
    model = canonical_speaker_model(
        [row(0, "0", "1", "Итого 500 ₽ + комиссия + НДС")],
        [row(0, "0", "1", "итого 500 комиссия ндс", "voice-a")],
        processing_result_id=RESULT_ID,
    )

    assert model.result_state == "accepted"
    assert model.diagnostics.text_conservation_status == "matched"


def test_text_conservation_still_rejects_missing_words_or_numbers() -> None:
    model = canonical_speaker_model(
        [row(0, "0", "1", "Итого 500 комиссия")],
        [row(0, "0", "1", "итого 400", "voice-a")],
        processing_result_id=RESULT_ID,
    )

    assert model.result_state == "degraded_provider_result"
    assert model.diagnostics.text_conservation_status == "mismatched"


def test_text_conservation_preserves_unicode_combining_marks() -> None:
    model = canonical_speaker_model(
        [row(0, "0", "1", "क")],
        [row(0, "0", "1", "कि", "voice-a")],
        processing_result_id=RESULT_ID,
    )

    assert model.result_state == "degraded_provider_result"
    assert model.diagnostics.text_conservation_status == "mismatched"


def test_empty_source_role_rows_do_not_create_false_text_mismatch() -> None:
    model = canonical_speaker_model(
        [
            row(0, "0", "1", "alpha", source_role="mixed"),
            row(1, "1", "2", "", source_role="mic"),
        ],
        [row(0, "0", "1", "alpha", "voice-a", source_role="mixed")],
        processing_result_id=RESULT_ID,
    )

    assert model.result_state == "accepted"
    assert model.diagnostics.text_conservation_status == "matched"


def test_provider_turns_without_asr_evidence_remain_visible_but_degraded() -> None:
    model = canonical_speaker_model(
        [],
        [row(0, "0", "1", "provider only", "voice-a")],
        processing_result_id=RESULT_ID,
    )

    assert model.result_state == "degraded_provider_result"
    assert model.diagnostics.defect_origin == "graf"
    assert "transcript_evidence_unavailable" in model.diagnostics.reason_codes
    assert [turn.text for turn in model.turns] == ["provider only"]
    assert model.turns[0].attribution_state == "confirmed"
    assert model.diagnostics.accepted_turn_count == 1


def test_raw_provider_key_is_preserved_exactly_while_unknown_detection_is_normalized() -> None:
    raw_key = "  UNKNOWN  "
    model = canonical_speaker_model(
        [row(0, "0", "1", "synthetic text")],
        [row(0, "0", "1", "synthetic text", raw_key)],
        processing_result_id=RESULT_ID,
    )

    assert model.turns[0].provider_speaker_key == raw_key
    assert model.turns[0].speaker_label == "Спикер не определён"
    assert model.turns[0].attribution_state == "unknown"


def test_legacy_ordinal_name_follows_only_the_matching_raw_provider_key() -> None:
    exact = canonical_speaker_model(
        [row(0, "0", "1", "alpha")],
        [row(0, "0", "1", "alpha", "SPEAKER_00")],
        processing_result_id=RESULT_ID,
        speaker_names={"speaker_00": "Старое имя"},
    )
    not_exact = canonical_speaker_model(
        [row(0, "0", "1", "alpha")],
        [row(0, "0", "1", "alpha", " SPEAKER_00 ")],
        processing_result_id=RESULT_ID,
        speaker_names={"speaker_00": "Чужое имя"},
    )

    assert exact.turns[0].speaker_label == "Старое имя"
    assert not_exact.turns[0].speaker_label == "SPEAKER_00"


def test_stable_name_is_used_while_legacy_ordinal_name_is_ignored() -> None:
    baseline = canonical_speaker_model(
        [row(0, "0", "1", "alpha")],
        [row(0, "0", "1", "alpha", "SPEAKER_00")],
        processing_result_id=RESULT_ID,
    )
    stable_key = baseline.turns[0].speaker_key

    named = canonical_speaker_model(
        [row(0, "0", "1", "alpha")],
        [row(0, "0", "1", "alpha", "SPEAKER_00")],
        processing_result_id=RESULT_ID,
        speaker_names={"speaker_00": "Старое имя", stable_key: "Новое имя"},
    )

    assert named.turns[0].speaker_label == "Новое имя"


def test_same_text_on_parallel_source_roles_is_not_a_duplicate() -> None:
    model = canonical_speaker_model(
        [
            row(0, "0", "1", "yes", source_role="mic"),
            row(1, "0", "1", "yes", source_role="incoming"),
        ],
        [
            row(0, "0", "1", "yes", "local", source_role="mic"),
            row(1, "0", "1", "yes", "remote", source_role="incoming"),
        ],
        processing_result_id=RESULT_ID,
    )

    assert model.result_state == "accepted"
    assert model.diagnostics.duplicate_text_count == 0
    assert model.diagnostics.multi_label_conflict_count == 0
    assert not any(turn.overlap for turn in model.turns)


def test_overlap_flags_use_strict_same_role_provider_intersections() -> None:
    model = canonical_speaker_model(
        [row(0, "0", "4", "one two three")],
        [
            row(0, "0", "2", "one", "a"),
            row(1, "1", "3", "two", "b"),
            row(2, "3", "4", "three", "c"),
        ],
        processing_result_id=RESULT_ID,
    )

    assert model.result_state == "accepted"
    assert [turn.overlap for turn in model.turns] == [True, True, False]


def test_overlap_flags_include_every_simultaneous_provider_turn() -> None:
    model = canonical_speaker_model(
        [row(0, "0", "4", "one two three")],
        [
            row(0, "0", "3", "one", "a"),
            row(1, "1", "4", "two", "b"),
            row(2, "2", "3", "three", "c"),
        ],
        processing_result_id=RESULT_ID,
    )

    assert model.result_state == "accepted"
    assert [turn.overlap for turn in model.turns] == [True, True, True]


def test_empty_provider_key_stays_unknown_without_becoming_a_participant() -> None:
    model = canonical_speaker_model(
        [row(0, "0", "1", "synthetic text")],
        [row(0, "0", "1", "synthetic text", "")],
        processing_result_id=RESULT_ID,
    )

    assert model.result_state == "accepted"
    assert model.turns[0].provider_speaker_key == ""
    assert model.turns[0].speaker_label == "Спикер не определён"
    assert model.turns[0].attribution_state == "unknown"
    assert model.confirmed_speaker_keys == ()


def test_tiny_unknown_count_uses_aggregate_identity_duration() -> None:
    model = canonical_speaker_model(
        [row(0, "0", "0.08", "one two")],
        [
            row(0, "0", "0.04", "one", "UNKNOWN"),
            row(1, "0.04", "0.08", "two", "UNKNOWN"),
        ],
        processing_result_id=RESULT_ID,
    )

    assert model.result_state == "accepted"
    assert model.diagnostics.unknown_tiny_count == 0


def test_parallel_source_sequences_do_not_create_false_chronology_defect() -> None:
    transcript = [
        row(0, "0", "10", "mic zero", source_role="mic"),
        row(0, "100", "110", "incoming zero", source_role="incoming"),
        row(1, "10", "20", "mic one", source_role="mic"),
        row(1, "110", "120", "incoming one", source_role="incoming"),
    ]
    provider = [
        row(0, "0", "10", "mic zero", "local", source_role="mic"),
        row(0, "100", "110", "incoming zero", "remote", source_role="incoming"),
        row(1, "10", "20", "mic one", "local", source_role="mic"),
        row(1, "110", "120", "incoming one", "remote", source_role="incoming"),
    ]

    model = canonical_speaker_model(transcript, provider, processing_result_id=RESULT_ID)

    assert model.result_state == "accepted"
    assert "impossible_provider_chronology" not in model.diagnostics.reason_codes
    assert [turn.start_seconds for turn in model.turns] == [
        Decimal("0"),
        Decimal("10"),
        Decimal("100"),
        Decimal("110"),
    ]


def test_simultaneous_turn_order_does_not_depend_on_input_order() -> None:
    transcript = [
        row(0, "0", "1", "local", source_role="mic"),
        row(0, "0", "1", "remote", source_role="incoming"),
    ]
    provider = [
        row(0, "0", "1", "local", "MIC", source_role="mic"),
        row(0, "0", "1", "remote", "REMOTE", source_role="incoming"),
    ]

    first = canonical_speaker_model(transcript, provider, processing_result_id=RESULT_ID)
    reordered = canonical_speaker_model(
        reversed(transcript),
        reversed(provider),
        processing_result_id=RESULT_ID,
    )

    assert first == reordered
    assert [turn.provider_speaker_key for turn in first.turns] == ["MIC", "REMOTE"]


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


def test_canonicalization_does_not_scan_the_transcript_provider_cartesian_product(
    monkeypatch,
) -> None:
    count = 100
    transcript = [row(index, str(index), str(index + 1), f"word{index}") for index in range(count)]
    provider = [
        row(index, str(index), str(index + 1), f"word{index}", f"voice-{index % 11}")
        for index in range(count)
    ]
    decimal_calls = 0
    normalization_calls = 0
    original_decimal = speaker_turns_module._decimal
    original_normalized_tokens = speaker_turns_module._normalized_tokens

    def counted_decimal(value):
        nonlocal decimal_calls
        decimal_calls += 1
        return original_decimal(value)

    def counted_normalized_tokens(values):
        nonlocal normalization_calls
        normalization_calls += 1
        return original_normalized_tokens(values)

    monkeypatch.setattr(speaker_turns_module, "_decimal", counted_decimal)
    monkeypatch.setattr(speaker_turns_module, "_normalized_tokens", counted_normalized_tokens)

    model = canonical_speaker_model(transcript, provider, processing_result_id=RESULT_ID)

    assert model.result_state == "accepted"
    assert normalization_calls <= count * 3
    assert decimal_calls <= count * 25
