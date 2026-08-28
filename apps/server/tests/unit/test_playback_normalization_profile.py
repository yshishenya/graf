from __future__ import annotations

import json
from decimal import Decimal

import pytest

from twobrain_rec_server.normalization.media import (
    BMFFLayout,
    MediaPolicyError,
    NormalizationAction,
    parse_probe_output,
    validate_canonical_profile,
    validate_duration_alignment,
    validate_tolerant_output_duration,
    validate_tolerant_source_duration,
)


def _canonical_probe_payload() -> dict[str, object]:
    return {
        "format": {
            "format_name": "mov,mp4,m4a,3gp,3g2,mj2",
            "duration": "60.000000",
            "start_time": "0.000000",
            "size": "480000",
            "bit_rate": "64000",
        },
        "streams": [
            {
                "index": 0,
                "codec_type": "audio",
                "codec_name": "aac",
                "profile": "LC",
                "sample_rate": "48000",
                "channels": 1,
                "duration": "60.000000",
                "start_time": "0.000000",
                "bit_rate": "64000",
                "disposition": {"default": 1, "attached_pic": 0},
            }
        ],
        "chapters": [],
    }


def test_typed_probe_parser_and_complete_canonical_gate() -> None:
    facts = parse_probe_output(json.dumps(_canonical_probe_payload()).encode())

    assert facts.stream_count == 1
    assert facts.audio_streams[0].sample_rate_hz == 48_000
    validate_canonical_profile(
        facts,
        bmff_layout=BMFFLayout(
            box_types=("ftyp", "moov", "mdat"),
            moov_before_mdat=True,
            fragmented=False,
        ),
        byte_length=480_000,
        full_decode_passed=True,
    )


@pytest.mark.parametrize(
    ("mutation", "reason_code"),
    [
        (("streams", 0, "profile", "HE-AAC"), "generated_output_invalid"),
        (("streams", 0, "sample_rate", "44100"), "generated_output_invalid"),
        (("streams", 0, "channels", 2), "generated_output_invalid"),
        (("streams", 0, "bit_rate", "90000"), "generated_output_invalid"),
        (("format", "duration", "14400.251000"), "duration_limit_exceeded"),
    ],
)
def test_canonical_gate_rejects_noncanonical_output(
    mutation: tuple[object, ...],
    reason_code: str,
) -> None:
    payload = _canonical_probe_payload()
    if len(mutation) == 4:
        collection, index, key, value = mutation
        payload[collection][index][key] = value  # type: ignore[index]
    else:
        section, key, value = mutation
        payload[section][key] = value  # type: ignore[index]
    facts = parse_probe_output(json.dumps(payload).encode())

    with pytest.raises(MediaPolicyError) as exc_info:
        validate_canonical_profile(
            facts,
            bmff_layout=BMFFLayout(
                box_types=("ftyp", "moov", "mdat"),
                moov_before_mdat=True,
                fragmented=False,
            ),
            byte_length=480_000,
            full_decode_passed=True,
        )
    assert exc_info.value.reason_code == reason_code


def test_generated_canonical_gate_allows_bounded_encoder_padding_at_four_hours() -> None:
    payload = _canonical_probe_payload()
    payload["format"]["duration"] = "14400.250000"  # type: ignore[index]
    payload["streams"][0]["duration"] = "14400.250000"  # type: ignore[index]
    facts = parse_probe_output(json.dumps(payload).encode())

    validate_canonical_profile(
        facts,
        bmff_layout=BMFFLayout(
            box_types=("ftyp", "moov", "mdat"),
            moov_before_mdat=True,
            fragmented=False,
        ),
        byte_length=480_000,
        full_decode_passed=True,
    )


def test_probe_parser_rejects_unrequested_private_metadata() -> None:
    payload = _canonical_probe_payload()
    payload["format"]["tags"] = {"title": "private meeting"}  # type: ignore[index]

    with pytest.raises(MediaPolicyError) as exc_info:
        parse_probe_output(json.dumps(payload).encode())
    assert exc_info.value.reason_code == "corrupt_source"
    assert "private meeting" not in str(exc_info.value)


@pytest.mark.parametrize(
    ("action", "source_durations", "accepted", "rejected"),
    [
        (
            NormalizationAction.BYTE_COPY,
            (Decimal("60.000"),),
            Decimal("60.050"),
            Decimal("60.051"),
        ),
        (
            NormalizationAction.FASTSTART_REMUX,
            (Decimal("60.000"),),
            Decimal("59.950"),
            Decimal("59.949"),
        ),
        (
            NormalizationAction.SINGLE_TRANSCODE,
            (Decimal("60.000"),),
            Decimal("60.250"),
            Decimal("60.251"),
        ),
        (
            NormalizationAction.RECOVERED_SINGLE_TRANSCODE,
            (Decimal("3600.000"),),
            Decimal("3540.000"),
            Decimal("3539.999"),
        ),
        (
            NormalizationAction.DUAL_MIX_TRANSCODE,
            (Decimal("59.000"), Decimal("60.000")),
            Decimal("59.750"),
            Decimal("59.749"),
        ),
    ],
)
def test_duration_alignment_uses_fixed_derivation_specific_tolerance(
    action: NormalizationAction,
    source_durations: tuple[Decimal, ...],
    accepted: Decimal,
    rejected: Decimal,
) -> None:
    validate_duration_alignment(
        action=action,
        source_durations_seconds=source_durations,
        output_duration_seconds=accepted,
    )

    with pytest.raises(MediaPolicyError) as exc_info:
        validate_duration_alignment(
            action=action,
            source_durations_seconds=source_durations,
            output_duration_seconds=rejected,
        )
    assert exc_info.value.reason_code == "generated_output_invalid"


def test_duration_alignment_rejects_wrong_source_cardinality() -> None:
    with pytest.raises(MediaPolicyError):
        validate_duration_alignment(
            action=NormalizationAction.DUAL_MIX_TRANSCODE,
            source_durations_seconds=(Decimal("60"),),
            output_duration_seconds=Decimal("60"),
        )


@pytest.mark.parametrize(
    ("format_duration", "stream_duration", "reason_code"),
    [
        (None, None, "corrupt_source"),
        ("0", "0", "corrupt_source"),
        ("14400.001", "14400.001", "duration_limit_exceeded"),
        ("60.000", "60.251", "source_mismatch"),
    ],
)
def test_tolerant_source_duration_is_known_bounded_and_aligned(
    format_duration: str | None,
    stream_duration: str | None,
    reason_code: str,
) -> None:
    payload = _canonical_probe_payload()
    payload["format"]["duration"] = format_duration  # type: ignore[index]
    payload["streams"][0]["duration"] = stream_duration  # type: ignore[index]
    facts = parse_probe_output(json.dumps(payload).encode())

    with pytest.raises(MediaPolicyError) as exc_info:
        validate_tolerant_source_duration(facts, facts.audio_streams[0])
    assert exc_info.value.reason_code == reason_code


def test_tolerant_source_and_output_duration_accept_bounded_frame_loss() -> None:
    payload = _canonical_probe_payload()
    payload["format"]["duration"] = "60.000"  # type: ignore[index]
    payload["streams"][0]["duration"] = "60.250"  # type: ignore[index]
    facts = parse_probe_output(json.dumps(payload).encode())

    duration = validate_tolerant_source_duration(facts, facts.audio_streams[0])
    assert duration == Decimal("60.250")
    validate_tolerant_output_duration(
        source_duration_seconds=duration,
        output_format_duration_seconds=Decimal("60.020"),
        output_stream_duration_seconds=Decimal("60.000"),
        output_decode_duration_seconds=Decimal("60.000"),
    )
    validate_tolerant_output_duration(
        source_duration_seconds=Decimal("60"),
        output_format_duration_seconds=Decimal("59.5"),
        output_stream_duration_seconds=Decimal("59.5"),
        output_decode_duration_seconds=Decimal("59.5"),
    )


@pytest.mark.parametrize(
    ("probe_duration", "decode_duration"),
    [(None, Decimal("60")), (Decimal("58.799"), Decimal("58.799"))],
)
def test_tolerant_output_duration_rejects_unknown_or_tail_loss(
    probe_duration: Decimal | None,
    decode_duration: Decimal,
) -> None:
    with pytest.raises(MediaPolicyError) as exc_info:
        validate_tolerant_output_duration(
            source_duration_seconds=Decimal("60"),
            output_format_duration_seconds=probe_duration,
            output_stream_duration_seconds=None,
            output_decode_duration_seconds=decode_duration,
        )
    assert exc_info.value.reason_code == "generated_output_invalid"
