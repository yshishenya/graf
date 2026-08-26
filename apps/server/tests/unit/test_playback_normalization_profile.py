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
        (("format", "duration", "14400.100000"), "duration_limit_exceeded"),
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
