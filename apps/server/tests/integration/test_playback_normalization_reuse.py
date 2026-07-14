from __future__ import annotations

import asyncio
from pathlib import Path

from tests.integration.test_playback_normalization_media_matrix import (
    _pipeline,
    _run_ffmpeg,
)
from twobrain_rec_server.normalization.media import inspect_bmff


def _generate_aac_m4a(
    path: Path,
    *,
    faststart: bool,
    sample_rate_hz: int = 48_000,
    channel_count: int = 1,
) -> None:
    arguments = [
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=440:duration=2",
        "-map",
        "0:a:0",
        "-vn",
        "-sn",
        "-dn",
        "-map_metadata",
        "-1",
        "-map_chapters",
        "-1",
        "-ar",
        str(sample_rate_hz),
        "-ac",
        str(channel_count),
        "-c:a",
        "aac",
        "-profile:a",
        "aac_low",
        "-b:a",
        "64k",
        "-fflags",
        "+bitexact",
        "-flags:a",
        "+bitexact",
        "-disposition:a:0",
        "default",
    ]
    if faststart:
        arguments.extend(["-movflags", "+faststart"])
    arguments.extend(["-f", "ipod", str(path)])
    _run_ffmpeg(arguments)


def test_fully_canonical_m4a_is_reused_byte_for_byte(tmp_path: Path) -> None:
    source = tmp_path / "canonical-source.m4a"
    output = tmp_path / "canonical-output.m4a"
    _generate_aac_m4a(source, faststart=True)
    source_bytes = source.read_bytes()

    result = asyncio.run(_pipeline().derive_single_source(source, output))

    assert result.derivation_kind == "source_byte_copy"
    assert output.read_bytes() == source_bytes
    assert result.output_sha256 is not None
    assert inspect_bmff(output).moov_before_mdat is True


def test_non_faststart_canonical_m4a_uses_lossless_remux(tmp_path: Path) -> None:
    source = tmp_path / "non-faststart-source.m4a"
    output = tmp_path / "non-faststart-output.m4a"
    _generate_aac_m4a(source, faststart=False)
    assert inspect_bmff(source).moov_before_mdat is False

    result = asyncio.run(_pipeline().derive_single_source(source, output))

    assert result.derivation_kind == "lossless_faststart_remux"
    assert result.selected_stream_index == 0
    assert inspect_bmff(output).moov_before_mdat is True
    assert result.full_decode_passed is True


def test_audio_profile_mismatch_triggers_transcode_not_copy_or_remux(tmp_path: Path) -> None:
    source = tmp_path / "stereo-44100-source.m4a"
    output = tmp_path / "stereo-44100-output.m4a"
    _generate_aac_m4a(
        source,
        faststart=True,
        sample_rate_hz=44_100,
        channel_count=2,
    )

    result = asyncio.run(_pipeline().derive_single_source(source, output))

    assert result.derivation_kind == "single_source_transcode"
    assert result.output_sample_rate_hz == 48_000
    assert result.output_channel_count == 1
    assert result.moov_before_mdat is True
    assert result.full_decode_passed is True
