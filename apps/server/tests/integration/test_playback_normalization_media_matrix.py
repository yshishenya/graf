from __future__ import annotations

import asyncio
import json
import shutil
import struct
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest

from tests.fixtures.playback_normalization import (
    SyntheticAudioStream,
    synthetic_probe_payload,
)
from twobrain_rec_server.normalization.media import (
    MediaPolicyError,
    ProcessResult,
    parse_probe_output,
    select_audio_stream,
)
from twobrain_rec_server.normalization.service import (
    CandidateRejected,
    FFmpegNormalizationPipeline,
    _validate_authoritative_source_duration,
    normalization_reason_from_exception,
)
from twobrain_rec_server.normalization.statuses import (
    NormalizationReason,
    ReasonClass,
    reason_class,
)


def _media_tools() -> tuple[str, str]:
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if ffmpeg is None or ffprobe is None:
        pytest.skip("FFmpeg capability is validated in the media runtime container")
    return ffmpeg, ffprobe


def _pipeline() -> FFmpegNormalizationPipeline:
    ffmpeg, ffprobe = _media_tools()
    return FFmpegNormalizationPipeline(
        ffmpeg_path=ffmpeg,
        ffprobe_path=ffprobe,
        probe_timeout_seconds=20,
        process_timeout_seconds=30,
    )


class _RecordingPipeline(FFmpegNormalizationPipeline):
    def __init__(self) -> None:
        ffmpeg, ffprobe = _media_tools()
        super().__init__(
            ffmpeg_path=ffmpeg,
            ffprobe_path=ffprobe,
            probe_timeout_seconds=20,
            process_timeout_seconds=30,
        )
        self.events: list[tuple[str, Path | list[str]]] = []

    async def _probe_source(self, source_path: Path):
        self.events.append(("probe", source_path))
        return await super()._probe_source(source_path)

    async def _run_ffmpeg(
        self,
        argv: list[str],
        *,
        cwd: Path,
        stdout_limit_bytes: int = 0,
    ) -> ProcessResult:
        self.events.append(("ffmpeg", argv))
        return await super()._run_ffmpeg(
            argv,
            cwd=cwd,
            stdout_limit_bytes=stdout_limit_bytes,
        )


def _run_ffmpeg(arguments: list[str]) -> None:
    ffmpeg, _ = _media_tools()
    completed = subprocess.run(
        [ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin", "-y", *arguments],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        check=False,
        timeout=30,
    )
    assert completed.returncode == 0, completed.stderr.decode("utf-8", errors="replace")


def test_empty_source_is_objective_terminal_truth_before_media_tool_execution(
    tmp_path: Path,
) -> None:
    source = tmp_path / "empty-source.media"
    source.write_bytes(b"")
    pipeline = FFmpegNormalizationPipeline(
        ffmpeg_path="/usr/bin/false",
        ffprobe_path="/usr/bin/false",
    )

    with pytest.raises(MediaPolicyError, match="empty_source") as error:
        asyncio.run(pipeline.derive_single_source(source, tmp_path / "empty-output.m4a"))

    assert error.value.reason_code == "empty_source"


def test_encrypted_audio_tag_is_terminal_without_codec_guessing() -> None:
    payload = synthetic_probe_payload(SyntheticAudioStream(codec_name="none"))
    payload["streams"][0]["codec_tag_string"] = "enca"

    facts = parse_probe_output(json.dumps(payload).encode())

    with pytest.raises(MediaPolicyError, match="encrypted_media") as error:
        select_audio_stream(facts)

    assert error.value.reason_code == "encrypted_media"


@pytest.mark.parametrize(
    "reason",
    [
        NormalizationReason.EMPTY_SOURCE,
        NormalizationReason.CORRUPT_SOURCE,
        NormalizationReason.ENCRYPTED_MEDIA,
        NormalizationReason.NO_AUDIO,
        NormalizationReason.AMBIGUOUS_AUDIO_TRACKS,
        NormalizationReason.UNSUPPORTED_CONTAINER,
        NormalizationReason.UNSUPPORTED_CODEC,
        NormalizationReason.STREAM_LIMIT_EXCEEDED,
        NormalizationReason.DURATION_LIMIT_EXCEEDED,
        NormalizationReason.SOURCE_MISSING,
        NormalizationReason.SOURCE_MISMATCH,
    ],
)
def test_objective_source_failure_matrix_is_permanent(reason: NormalizationReason) -> None:
    detected = normalization_reason_from_exception(MediaPolicyError(reason.value))

    assert detected is reason
    assert reason_class(detected) is ReasonClass.PERMANENT_SOURCE


def test_no_audio_unsupported_container_and_codec_are_distinct() -> None:
    video_only = synthetic_probe_payload(include_video=True)
    unsupported_container = synthetic_probe_payload(
        SyntheticAudioStream(),
        format_name="avi",
    )
    unsupported_codec = synthetic_probe_payload(
        SyntheticAudioStream(codec_name="ac3"),
    )

    cases = (
        (video_only, "no_audio"),
        (unsupported_container, "unsupported_container"),
        (unsupported_codec, "unsupported_codec"),
    )
    for payload, expected_reason in cases:
        facts = parse_probe_output(json.dumps(payload).encode())
        with pytest.raises(MediaPolicyError, match=expected_reason) as error:
            select_audio_stream(facts)
        assert error.value.reason_code == expected_reason


def test_probe_stream_limit_is_terminal_before_selection() -> None:
    payload = synthetic_probe_payload(*(SyntheticAudioStream(index=index) for index in range(17)))

    with pytest.raises(MediaPolicyError, match="stream_limit_exceeded") as error:
        parse_probe_output(json.dumps(payload).encode())

    assert error.value.reason_code == "stream_limit_exceeded"


class DurationLimitPipeline(FFmpegNormalizationPipeline):
    def __init__(self) -> None:
        super().__init__(ffmpeg_path="/usr/bin/false", ffprobe_path="/usr/bin/false")

    async def _probe_source(self, source_path: Path):
        del source_path
        facts = parse_probe_output(
            json.dumps(
                synthetic_probe_payload(
                    SyntheticAudioStream(duration_seconds=14_401),
                    duration_seconds=14_401,
                )
            ).encode()
        )
        return facts, select_audio_stream(facts)

    async def _full_decode(self, *args, **kwargs) -> None:
        del args, kwargs
        raise AssertionError("over-limit media must be rejected before full decode")


def test_duration_limit_is_terminal_before_decode_or_output(tmp_path: Path) -> None:
    source = tmp_path / "duration-limit.media"
    source.write_bytes(b"synthetic")
    output = tmp_path / "duration-limit.m4a"

    with pytest.raises(MediaPolicyError, match="duration_limit_exceeded") as error:
        asyncio.run(DurationLimitPipeline().derive_single_source(source, output))

    assert error.value.reason_code == "duration_limit_exceeded"
    assert not output.exists()


def test_candidate_duration_limit_falls_back_before_decode_or_output(tmp_path: Path) -> None:
    source = tmp_path / "duration-limit-candidate.media"
    source.write_bytes(b"synthetic")
    output = tmp_path / "duration-limit-candidate.m4a"

    with pytest.raises(CandidateRejected):
        asyncio.run(DurationLimitPipeline().derive_candidate(source, output))

    assert not output.exists()


def test_dual_source_duration_limit_is_terminal_before_decode_or_output(
    tmp_path: Path,
) -> None:
    microphone = tmp_path / "duration-limit-microphone.media"
    system = tmp_path / "duration-limit-system.media"
    microphone.write_bytes(b"synthetic")
    system.write_bytes(b"synthetic")
    output = tmp_path / "duration-limit-dual.m4a"

    with pytest.raises(MediaPolicyError, match="duration_limit_exceeded") as error:
        asyncio.run(DurationLimitPipeline().derive_dual_source(microphone, system, output))

    assert error.value.reason_code == "duration_limit_exceeded"
    assert not output.exists()


def _generate_single_source(
    path: Path,
    *,
    muxer: str,
    audio_codec: str,
    include_video: bool,
) -> None:
    arguments = ["-f", "lavfi", "-i", "sine=frequency=440:duration=0.6"]
    if include_video:
        arguments.extend(["-f", "lavfi", "-i", "color=c=blue:s=64x64:d=0.6", "-shortest"])
        arguments.extend(["-map", "1:v:0", "-c:v", "libvpx" if muxer == "webm" else "mpeg4"])
    arguments.extend(
        [
            "-map",
            "0:a:0",
            "-ar",
            "48000" if audio_codec == "libopus" else "44100",
            "-ac",
            "2",
            "-c:a",
            audio_codec,
        ]
    )
    if audio_codec == "vorbis":
        arguments.extend(["-strict", "experimental"])
    arguments.extend(["-f", muxer, str(path)])
    _run_ffmpeg(arguments)


@pytest.mark.parametrize(
    ("case_name", "muxer", "audio_codec", "include_video"),
    [
        ("wav", "wav", "pcm_s16le", False),
        ("wav-adpcm-ima", "wav", "adpcm_ima_wav", False),
        ("wav-adpcm-ms", "wav", "adpcm_ms", False),
        ("mp3", "mp3", "libmp3lame", False),
        ("aac", "adts", "aac", False),
        ("flac", "flac", "flac", False),
        ("ogg-vorbis", "ogg", "vorbis", False),
        ("ogg-opus", "ogg", "libopus", False),
        ("m4a", "ipod", "aac", False),
        ("mp4", "mp4", "aac", True),
        ("mov", "mov", "pcm_s16le", True),
        ("m4v", "mp4", "aac", True),
        ("webm", "webm", "libopus", True),
        ("mkv", "matroska", "flac", True),
    ],
)
def test_supported_audio_video_matrix_is_detected_by_bytes_and_normalized(
    tmp_path: Path,
    case_name: str,
    muxer: str,
    audio_codec: str,
    include_video: bool,
) -> None:
    source = tmp_path / f"source-{case_name}.media"
    output = tmp_path / f"output-{case_name}.m4a"
    _generate_single_source(
        source,
        muxer=muxer,
        audio_codec=audio_codec,
        include_video=include_video,
    )

    result = asyncio.run(_pipeline().derive_single_source(source, output))

    assert result.derivation_kind == "single_source_transcode"
    assert result.selected_stream_index is not None
    assert result.output_sample_rate_hz == 48_000
    assert result.output_channel_count == 1
    assert result.moov_before_mdat is True
    assert result.fragmented is False
    assert result.full_decode_passed is True
    assert output.is_file()


def test_tolerant_video_accepts_audio_shorter_than_container_without_padding(
    tmp_path: Path,
) -> None:
    source = tmp_path / "longer-video.webm"
    output = tmp_path / "shorter-audio.m4a"
    _run_ffmpeg(
        [
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=0.6",
            "-f",
            "lavfi",
            "-i",
            "color=c=blue:s=64x64:d=2",
            "-map",
            "0:a:0",
            "-map",
            "1:v:0",
            "-c:a",
            "libopus",
            "-c:v",
            "libvpx",
            "-f",
            "webm",
            str(source),
        ]
    )

    result = asyncio.run(_pipeline().derive_single_source(source, output, tolerant_first=True))

    assert 500 <= result.output_duration_ms <= 700
    assert 500 <= result.source_duration_ms <= 700


def test_wrong_extension_does_not_override_supported_media_bytes(tmp_path: Path) -> None:
    source = tmp_path / "actually-flac.mp3"
    output = tmp_path / "wrong-extension-output.m4a"
    _generate_single_source(
        source,
        muxer="flac",
        audio_codec="flac",
        include_video=False,
    )

    result = asyncio.run(_pipeline().derive_single_source(source, output))

    assert result.derivation_kind == "single_source_transcode"
    assert result.full_decode_passed is True


def test_unknown_private_bmff_box_forces_sanitizing_remux(tmp_path: Path) -> None:
    raw_source = tmp_path / "private-marker.flac"
    source = tmp_path / "private-marker.m4a"
    output = tmp_path / "private-marker-output.m4a"
    _generate_single_source(
        raw_source,
        muxer="flac",
        audio_codec="flac",
        include_video=False,
    )
    asyncio.run(_pipeline().derive_single_source(raw_source, source))
    marker_payload = b"\x00" * 16 + b"private-marker"
    marker = struct.pack(">I4s", len(marker_payload) + 8, b"uuid") + marker_payload
    with source.open("ab") as source_file:
        source_file.write(marker)

    result = asyncio.run(_pipeline().derive_single_source(source, output))

    assert result.derivation_kind == "lossless_faststart_remux"
    assert b"private-marker" in source.read_bytes()
    assert b"private-marker" not in output.read_bytes()


class _SourceProbeOverridePipeline(FFmpegNormalizationPipeline):
    def __init__(self, source_path: Path, *, forged_duration: str | None) -> None:
        ffmpeg, ffprobe = _media_tools()
        super().__init__(
            ffmpeg_path=ffmpeg,
            ffprobe_path=ffprobe,
            probe_timeout_seconds=20,
            process_timeout_seconds=30,
        )
        self.source_path = source_path
        self.forged_duration = forged_duration

    async def _probe_source(self, source_path: Path):
        facts, stream = await super()._probe_source(source_path)
        if source_path != self.source_path:
            return facts, stream
        duration = None if self.forged_duration is None else self.forged_duration
        forged = None if duration is None else type(facts.duration_seconds)(duration)
        return (
            replace(facts, duration_seconds=forged),
            replace(stream, duration_seconds=forged),
        )


@pytest.mark.parametrize("forged_duration", [None, "0.1"])
def test_unknown_or_forged_probe_duration_uses_bounded_decode_truth(
    tmp_path: Path,
    forged_duration: str | None,
) -> None:
    source = tmp_path / "duration-source.flac"
    output = tmp_path / "duration-output.m4a"
    _generate_single_source(
        source,
        muxer="flac",
        audio_codec="flac",
        include_video=False,
    )

    result = asyncio.run(
        _SourceProbeOverridePipeline(
            source,
            forged_duration=forged_duration,
        ).derive_single_source(source, output)
    )

    assert result.source_duration_ms >= 500
    assert result.output_duration_ms >= 500
    assert abs(result.output_duration_ms - result.source_duration_ms) <= 250


def _generate_two_audio_streams(
    path: Path,
    *,
    first_codec: str,
    second_codec: str,
    first_default: bool,
    second_default: bool,
) -> None:
    _run_ffmpeg(
        [
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=330:duration=0.6",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=660:duration=0.6",
            "-map",
            "0:a:0",
            "-map",
            "1:a:0",
            "-c:a:0",
            first_codec,
            "-c:a:1",
            second_codec,
            "-disposition:a:0",
            "default" if first_default else "0",
            "-disposition:a:1",
            "default" if second_default else "0",
            "-f",
            "matroska",
            str(path),
        ]
    )


def _generate_silent_then_default_tone(path: Path) -> None:
    _run_ffmpeg(
        [
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=48000:cl=mono:d=0.6",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=660:sample_rate=48000:duration=0.6",
            "-map",
            "0:a:0",
            "-map",
            "1:a:0",
            "-c:a",
            "flac",
            "-disposition:a:0",
            "0",
            "-disposition:a:1",
            "default",
            "-f",
            "matroska",
            str(path),
        ]
    )


def test_dual_mix_uses_each_selected_global_stream_index(tmp_path: Path) -> None:
    microphone = tmp_path / "microphone.mkv"
    system = tmp_path / "system.mkv"
    output = tmp_path / "dual-output.m4a"
    _generate_silent_then_default_tone(microphone)
    _generate_silent_then_default_tone(system)

    result = asyncio.run(_pipeline().derive_dual_source(microphone, system, output))

    ffmpeg, _ = _media_tools()
    decoded = subprocess.run(
        [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-nostdin",
            "-i",
            str(output),
            "-map",
            "0:a:0",
            "-ac",
            "1",
            "-ar",
            "48000",
            "-f",
            "s16le",
            "pipe:1",
        ],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        check=False,
        timeout=30,
    )
    assert decoded.returncode == 0, decoded.stderr.decode("utf-8", errors="replace")
    peak = max(abs(sample[0]) for sample in struct.iter_unpack("<h", decoded.stdout))

    assert result.derivation_kind == "dual_source_mix_transcode"
    assert peak > 100


def test_unique_usable_stream_is_selected_without_guessing(tmp_path: Path) -> None:
    source = tmp_path / "one-usable.mkv"
    output = tmp_path / "one-usable.m4a"
    _generate_two_audio_streams(
        source,
        first_codec="ac3",
        second_codec="flac",
        first_default=True,
        second_default=False,
    )

    result = asyncio.run(_pipeline().derive_single_source(source, output))

    assert result.selected_stream_index == 1
    assert result.derivation_kind == "single_source_transcode"


def test_unique_default_stream_is_selected_deterministically(tmp_path: Path) -> None:
    source = tmp_path / "unique-default.mkv"
    output = tmp_path / "unique-default.m4a"
    _generate_two_audio_streams(
        source,
        first_codec="flac",
        second_codec="flac",
        first_default=False,
        second_default=True,
    )

    result = asyncio.run(_pipeline().derive_single_source(source, output))

    assert result.selected_stream_index == 1


def test_ambiguous_usable_streams_fail_without_selecting_one(tmp_path: Path) -> None:
    source = tmp_path / "ambiguous.mkv"
    output = tmp_path / "ambiguous.m4a"
    _generate_two_audio_streams(
        source,
        first_codec="flac",
        second_codec="flac",
        first_default=False,
        second_default=False,
    )

    with pytest.raises(MediaPolicyError, match="ambiguous_audio_tracks") as error:
        asyncio.run(_pipeline().derive_single_source(source, output))

    assert error.value.reason_code == "ambiguous_audio_tracks"
    assert not output.exists()


class DecodeFailingPipeline(FFmpegNormalizationPipeline):
    def __init__(self) -> None:
        super().__init__(ffmpeg_path="/usr/bin/false", ffprobe_path="/usr/bin/false")
        self.decode_calls: list[int] = []

    async def _probe_source(self, source_path: Path):
        del source_path
        facts = parse_probe_output(
            json.dumps(
                synthetic_probe_payload(
                    SyntheticAudioStream(index=0, default=False),
                    SyntheticAudioStream(index=1, default=True),
                    format_name="matroska,webm",
                )
            ).encode()
        )
        return facts, select_audio_stream(facts)

    async def _full_decode(
        self,
        source_path: Path,
        *,
        stream_index: int,
        generated: bool,
    ) -> None:
        del source_path, generated
        self.decode_calls.append(stream_index)
        raise MediaPolicyError("corrupt_source")


def test_selected_default_decode_failure_does_not_fallback_to_another_stream(
    tmp_path: Path,
) -> None:
    source = tmp_path / "synthetic-selected.media"
    source.write_bytes(b"synthetic")
    pipeline = DecodeFailingPipeline()

    with pytest.raises(MediaPolicyError, match="dependency_unavailable"):
        asyncio.run(pipeline.derive_single_source(source, tmp_path / "output.m4a"))

    assert pipeline.decode_calls == [1]


def test_corrupt_mp3_is_recovered_by_tolerant_first_transcode(tmp_path: Path) -> None:
    source = tmp_path / "source.mp3"
    broken = tmp_path / "broken.mp3"
    output = tmp_path / "recovered.m4a"
    candidate_output = tmp_path / "recovered-candidate.m4a"
    _run_ffmpeg(
        [
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=5",
            "-c:a",
            "libmp3lame",
            "-b:a",
            "192k",
            str(source),
        ]
    )
    payload = bytearray(source.read_bytes())
    assert len(payload) > 10_700
    payload[10_700:10_704] = b"\x00\x00\x00\x00"
    broken.write_bytes(payload)

    result = asyncio.run(_pipeline().derive_single_source(broken, output))

    assert result.recovered_source is True
    assert result.derivation_kind == "single_source_transcode"
    assert result.full_decode_passed is True
    assert output.is_file()

    candidate_result = asyncio.run(_pipeline().derive_candidate(broken, candidate_output))

    assert candidate_result.recovered_source is True
    assert candidate_result.derivation_kind == "single_source_transcode"
    assert candidate_result.full_decode_passed is True
    assert candidate_output.is_file()


@pytest.mark.parametrize("damage_frame", [False, True])
def test_explicit_tolerant_first_primitive_has_exact_subprocess_budget(
    tmp_path: Path,
    damage_frame: bool,
) -> None:
    source = tmp_path / "tolerant-source.mp3"
    output = tmp_path / "tolerant-output.m4a"
    _run_ffmpeg(
        [
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=5",
            "-c:a",
            "libmp3lame",
            "-b:a",
            "192k",
            str(source),
        ]
    )
    if damage_frame:
        payload = bytearray(source.read_bytes())
        assert len(payload) > 10_700
        payload[10_700:10_704] = b"\x00\x00\x00\x00"
        source.write_bytes(payload)

    pipeline = _RecordingPipeline()
    result = asyncio.run(pipeline.derive_single_source(source, output, tolerant_first=True))

    assert [kind for kind, _ in pipeline.events] == [
        "probe",
        "ffmpeg",
        "probe",
        "ffmpeg",
    ]
    assert pipeline.events[0] == ("probe", source)
    transcode = pipeline.events[1][1]
    assert isinstance(transcode, list)
    assert transcode[transcode.index("-i") + 1] == str(source)
    assert transcode[transcode.index("-t") + 1] == "14401"
    assert "-xerror" not in transcode
    assert pipeline.events[2] == ("probe", output)
    strict_decode = pipeline.events[3][1]
    assert isinstance(strict_decode, list)
    assert strict_decode[strict_decode.index("-i") + 1] == str(output)
    assert strict_decode[strict_decode.index("-f") + 1 :] == ["null", "-"]
    assert result.recovered_source is False
    assert result.output_byte_length == output.stat().st_size
    assert result.moov_before_mdat is True


def test_manual_duration_mismatch_stops_after_probe_before_transcode(tmp_path: Path) -> None:
    source = tmp_path / "duration-mismatch.mp3"
    output = tmp_path / "must-not-exist.m4a"
    _run_ffmpeg(
        [
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=5",
            "-c:a",
            "libmp3lame",
            str(source),
        ]
    )
    pipeline = _RecordingPipeline()

    with pytest.raises(MediaPolicyError, match="source_mismatch"):
        asyncio.run(
            pipeline.derive_single_source(
                source,
                output,
                tolerant_first=True,
                expected_duration_seconds=30,
            )
        )

    assert pipeline.events == [("probe", source)]
    assert not output.exists()


def test_truncated_mp3_is_rejected_against_authoritative_duration(tmp_path: Path) -> None:
    source = tmp_path / "source-with-tail.mp3"
    truncated = tmp_path / "truncated-tail.mp3"
    output = tmp_path / "truncated-tail.m4a"
    _run_ffmpeg(
        [
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=5",
            "-c:a",
            "libmp3lame",
            "-b:a",
            "192k",
            str(source),
        ]
    )
    source_bytes = source.read_bytes()
    truncated.write_bytes(source_bytes[: int(len(source_bytes) * 0.85)])

    result = asyncio.run(_pipeline().derive_single_source(truncated, output))

    assert result.source_duration_ms < 4_750
    with pytest.raises(MediaPolicyError, match="source_mismatch") as error:
        _validate_authoritative_source_duration(
            result.source_duration_ms,
            expected_duration_seconds=5,
        )
    assert error.value.reason_code == "source_mismatch"

    tolerant_output = tmp_path / "truncated-tail-tolerant.m4a"
    with pytest.raises(MediaPolicyError, match="generated_output_invalid") as tolerant_error:
        asyncio.run(
            _pipeline().derive_single_source(
                truncated,
                tolerant_output,
                tolerant_first=True,
            )
        )
    assert tolerant_error.value.reason_code == "generated_output_invalid"


def test_manual_upload_duration_allowance_stays_bounded_for_long_recordings() -> None:
    _validate_authoritative_source_duration(
        3_598_750,
        expected_duration_seconds=3_600,
        manual_upload=True,
    )

    with pytest.raises(MediaPolicyError, match="source_mismatch"):
        _validate_authoritative_source_duration(
            3_598_749,
            expected_duration_seconds=3_600,
            manual_upload=True,
        )

    # Recovery output uses the wider, duration-relative allowance; the client
    # declaration does not.
    _validate_authoritative_source_duration(
        3_598_749,
        expected_duration_seconds=3_600,
    )
