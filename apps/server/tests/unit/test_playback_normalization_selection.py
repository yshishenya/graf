from __future__ import annotations

import json
import sys
from asyncio import CancelledError, create_task, sleep

import pytest

from twobrain_rec_server.normalization.media import (
    MediaPolicyError,
    ProcessOutputLimitError,
    ProcessTimeoutError,
    build_dual_mix_command,
    build_full_decode_command,
    build_lossless_remux_command,
    build_probe_command,
    build_transcode_command,
    parse_full_decode_progress,
    parse_probe_output,
    run_bounded_process,
    select_audio_stream,
)


def _probe_with_streams(streams: list[dict[str, object]]) -> bytes:
    return json.dumps(
        {
            "format": {
                "format_name": "matroska,webm",
                "duration": "60.0",
                "start_time": "0.0",
                "size": "1000",
                "bit_rate": "128000",
            },
            "streams": streams,
            "chapters": [],
        }
    ).encode()


def _audio(index: int, *, default: int = 0, codec: str = "opus") -> dict[str, object]:
    return {
        "index": index,
        "codec_type": "audio",
        "codec_name": codec,
        "profile": None,
        "sample_rate": "48000",
        "channels": 1,
        "duration": "60.0",
        "start_time": "0.0",
        "bit_rate": "64000",
        "disposition": {"default": default, "attached_pic": 0},
    }


def test_single_container_selection_uses_only_unique_default() -> None:
    facts = parse_probe_output(_probe_with_streams([_audio(1), _audio(4, default=1)]))

    assert select_audio_stream(facts).index == 4

    ambiguous = parse_probe_output(_probe_with_streams([_audio(1), _audio(4)]))
    with pytest.raises(MediaPolicyError) as exc_info:
        select_audio_stream(ambiguous)
    assert exc_info.value.reason_code == "ambiguous_audio_tracks"


def test_selection_rejects_no_audio_and_unsupported_codec_truthfully() -> None:
    no_audio = parse_probe_output(
        _probe_with_streams(
            [
                {
                    "index": 0,
                    "codec_type": "video",
                    "codec_name": "h264",
                    "profile": "High",
                    "duration": "60.0",
                    "start_time": "0.0",
                    "bit_rate": "128000",
                    "disposition": {"default": 1, "attached_pic": 0},
                }
            ]
        )
    )
    with pytest.raises(MediaPolicyError) as exc_info:
        select_audio_stream(no_audio)
    assert exc_info.value.reason_code == "no_audio"

    unsupported = parse_probe_output(_probe_with_streams([_audio(0, codec="wmav2")]))
    with pytest.raises(MediaPolicyError) as exc_info:
        select_audio_stream(unsupported)
    assert exc_info.value.reason_code == "unsupported_codec"


def test_media_commands_are_explicit_file_only_and_metadata_free(tmp_path) -> None:
    source = tmp_path / "00000000-0000-0000-0000-000000000001"
    output = tmp_path / "00000000-0000-0000-0000-000000000002"
    probe = build_probe_command("ffprobe", source)
    transcode = build_transcode_command("ffmpeg", source, output, stream_index=3)
    dual = build_dual_mix_command(
        "ffmpeg",
        source,
        source,
        output,
        microphone_stream_index=3,
        system_stream_index=5,
    )
    remux = build_lossless_remux_command("ffmpeg", source, output, stream_index=3)
    full_decode = build_full_decode_command("ffmpeg", output, stream_index=0)

    assert probe[0] == "ffprobe"
    assert probe.count("-protocol_whitelist") == 1
    assert probe[probe.index("-protocol_whitelist") + 1] == "file"
    assert transcode[transcode.index("-map") + 1] == "0:3"
    assert transcode[
        transcode.index("-map_metadata") : transcode.index("-map_metadata") + 2
    ] == ["-map_metadata", "-1"]
    assert "[mix]" in dual
    assert "amix=inputs=2:duration=longest" in " ".join(dual)
    assert "[0:3]" in " ".join(dual)
    assert "[1:5]" in " ".join(dual)
    assert "[0:a:0]" not in " ".join(dual)
    assert "[1:a:0]" not in " ".join(dual)
    assert remux[remux.index("-c:a") + 1] == "copy"
    assert remux[remux.index("-movflags") + 1] == "+faststart"
    assert remux[remux.index("-map_metadata") + 1] == "-1"
    assert full_decode[full_decode.index("-f") + 1 :] == ["null", "-"]
    assert full_decode[full_decode.index("-map") + 1] == "0:0"
    assert full_decode[full_decode.index("-af") + 1].endswith("asetpts=N/SR/TB")
    assert full_decode[full_decode.index("-t") + 1] == "14401"
    assert full_decode[full_decode.index("-progress") + 1] == "pipe:1"


def test_dual_mix_command_rejects_negative_global_stream_indexes(tmp_path) -> None:
    source = tmp_path / "source"
    output = tmp_path / "output"

    with pytest.raises(ValueError, match="non-negative"):
        build_dual_mix_command(
            "ffmpeg",
            source,
            source,
            output,
            microphone_stream_index=-1,
            system_stream_index=0,
        )


def test_full_decode_progress_requires_bounded_monotonic_eof_receipt() -> None:
    receipt = parse_full_decode_progress(
        b"out_time_us=1000000\nprogress=continue\nout_time_us=2500000\nprogress=end\n"
    )
    assert receipt.duration_seconds == 2.5

    invalid_payloads = (
        b"out_time_us=1000000\nprogress=continue\n",
        b"progress=end\n",
        b"out_time_us=-1\nprogress=end\n",
        b"out_time_us=2000000\nout_time_us=1000000\nprogress=end\n",
        b"out_time_us=invalid\nprogress=end\n",
    )
    for payload in invalid_payloads:
        with pytest.raises(MediaPolicyError, match="dependency_unavailable"):
            parse_full_decode_progress(payload)


def test_audio_selection_allows_unknown_duration_for_bounded_decode() -> None:
    stream = _audio(0, default=1)
    stream.pop("duration")
    payload = json.loads(_probe_with_streams([stream]))
    payload["format"].pop("duration")

    assert select_audio_stream(parse_probe_output(json.dumps(payload).encode())).index == 0


@pytest.mark.asyncio
async def test_process_runner_enforces_executable_and_streaming_output_caps() -> None:
    with pytest.raises(MediaPolicyError):
        await run_bounded_process(
            ["not-approved", "--version"],
            timeout_seconds=1,
            stdout_limit_bytes=16,
            stderr_limit_bytes=16,
        )

    with pytest.raises(ProcessOutputLimitError):
        await run_bounded_process(
            [sys.executable, "-c", "import sys,time; sys.stdout.write('x' * 128); sys.stdout.flush(); time.sleep(5)"],
            timeout_seconds=5,
            stdout_limit_bytes=16,
            stderr_limit_bytes=16,
            allowed_executables={sys.executable},
        )


@pytest.mark.asyncio
async def test_process_runner_terminates_process_group_on_timeout_and_cancellation() -> None:
    with pytest.raises(ProcessTimeoutError):
        await run_bounded_process(
            [sys.executable, "-c", "import time; time.sleep(30)"],
            timeout_seconds=0.05,
            stdout_limit_bytes=16,
            stderr_limit_bytes=16,
            allowed_executables={sys.executable},
        )

    task = create_task(
        run_bounded_process(
            [sys.executable, "-c", "import time; time.sleep(30)"],
            timeout_seconds=30,
            stdout_limit_bytes=16,
            stderr_limit_bytes=16,
            allowed_executables={sys.executable},
        )
    )
    await sleep(0.05)
    task.cancel()
    with pytest.raises(CancelledError):
        await task
