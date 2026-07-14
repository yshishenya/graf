#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

SERVER_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVER_ROOT / "src"))

from twobrain_rec_server.normalization.service import FFmpegNormalizationPipeline  # noqa: E402
from twobrain_rec_server.normalization.statuses import (  # noqa: E402
    CANONICAL_PROFILE_VERSION,
    VALIDATION_VERSION,
)


def _run(arguments: list[str], *, capture: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        arguments,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE if capture else subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        check=False,
        text=True,
        timeout=60,
    )


def _require_success(arguments: list[str]) -> None:
    completed = _run(arguments)
    if completed.returncode != 0:
        raise RuntimeError("synthetic media command failed")


def _generate_source(
    ffmpeg: str,
    path: Path,
    *,
    muxer: str,
    audio_codec: str,
    include_video: bool,
) -> None:
    sample_rate = "48000" if audio_codec == "libopus" else "44100"
    arguments = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-nostdin",
        "-y",
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=440:duration=0.6",
    ]
    if include_video:
        arguments.extend(
            [
                "-f",
                "lavfi",
                "-i",
                "color=c=blue:s=64x64:d=0.6",
                "-shortest",
                "-map",
                "1:v:0",
                "-c:v",
                "libvpx" if muxer == "webm" else "mpeg4",
            ]
        )
    arguments.extend(
        [
            "-map",
            "0:a:0",
            "-ar",
            sample_rate,
            "-ac",
            "2",
            "-c:a",
            audio_codec,
            "-f",
            muxer,
            str(path),
        ]
    )
    _require_success(arguments)


def _generate_canonical_m4a(ffmpeg: str, path: Path, *, faststart: bool) -> None:
    arguments = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-nostdin",
        "-y",
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=550:duration=2",
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
        "48000",
        "-ac",
        "1",
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
    _require_success(arguments)


def _full_decode(ffmpeg: str, path: Path) -> None:
    _require_success(
        [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-nostdin",
            "-xerror",
            "-i",
            str(path),
            "-map",
            "0:a:0",
            "-f",
            "null",
            "-",
        ]
    )


async def _verify_matrix(work_path: Path, ffmpeg: str, ffprobe: str) -> list[dict[str, str]]:
    pipeline = FFmpegNormalizationPipeline(
        ffmpeg_path=ffmpeg,
        ffprobe_path=ffprobe,
        probe_timeout_seconds=20,
        process_timeout_seconds=60,
    )
    cases = [
        ("wav", "wav", "pcm_s16le", False),
        ("mp3", "mp3", "libmp3lame", False),
        ("aac", "adts", "aac", False),
        ("flac", "flac", "flac", False),
        ("ogg-vorbis", "ogg", "libvorbis", False),
        ("ogg-opus", "ogg", "libopus", False),
        ("m4a", "ipod", "aac", False),
        ("mp4", "mp4", "aac", True),
        ("mov", "mov", "pcm_s16le", True),
        ("m4v", "mp4", "aac", True),
        ("webm", "webm", "libopus", True),
        ("mkv", "matroska", "flac", True),
    ]
    receipts: list[dict[str, str]] = []
    for name, muxer, codec, include_video in cases:
        source = work_path / f"{name}.source"
        output = work_path / f"{name}.m4a"
        _generate_source(
            ffmpeg,
            source,
            muxer=muxer,
            audio_codec=codec,
            include_video=include_video,
        )
        result = await pipeline.derive_single_source(source, output)
        if (
            result.derivation_kind != "single_source_transcode"
            or not result.full_decode_passed
            or result.output_sample_rate_hz != 48_000
            or result.output_channel_count != 1
        ):
            raise RuntimeError("matrix output did not reach canonical profile")
        _full_decode(ffmpeg, output)
        receipts.append({"case": name, "result": "ready", "action": result.derivation_kind})

    canonical = work_path / "canonical.source"
    canonical_output = work_path / "canonical.m4a"
    _generate_canonical_m4a(ffmpeg, canonical, faststart=True)
    canonical_bytes = canonical.read_bytes()
    canonical_result = await pipeline.derive_single_source(canonical, canonical_output)
    if canonical_result.derivation_kind != "source_byte_copy":
        raise RuntimeError("canonical input did not use byte-copy")
    if canonical_output.read_bytes() != canonical_bytes:
        raise RuntimeError("byte-copy changed canonical input")
    _full_decode(ffmpeg, canonical_output)
    receipts.append({"case": "canonical-m4a", "result": "ready", "action": "source_byte_copy"})

    non_faststart = work_path / "non-faststart.source"
    remuxed = work_path / "remuxed.m4a"
    _generate_canonical_m4a(ffmpeg, non_faststart, faststart=False)
    remux_result = await pipeline.derive_single_source(non_faststart, remuxed)
    if remux_result.derivation_kind != "lossless_faststart_remux":
        raise RuntimeError("layout-only mismatch did not use lossless remux")
    _full_decode(ffmpeg, remuxed)
    receipts.append(
        {
            "case": "non-faststart-m4a",
            "result": "ready",
            "action": "lossless_faststart_remux",
        }
    )
    return receipts


def main() -> int:
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if ffmpeg is None or ffprobe is None:
        raise RuntimeError("FFmpeg runtime is unavailable")
    if os.geteuid() == 0:
        raise RuntimeError("media capability gate must run as non-root")

    work_root = Path(os.environ.get("TMPDIR", "/var/lib/twobrain-rec/playback-normalization"))
    root_mode = stat.S_IMODE(work_root.stat().st_mode)
    if root_mode & 0o077:
        raise RuntimeError("media work root is not private")

    version_output = _run([ffmpeg, "-version"], capture=True)
    if version_output.returncode != 0:
        raise RuntimeError("unable to inspect FFmpeg version")
    version_lines = version_output.stdout.splitlines()
    protocol_probe = _run(
        [
            ffprobe,
            "-v",
            "error",
            "-protocol_whitelist",
            "file",
            "https://example.invalid/media",
        ]
    )
    if protocol_probe.returncode == 0:
        raise RuntimeError("non-file protocol was not refused")

    work_path = Path(tempfile.mkdtemp(prefix="capability-", dir=work_root))
    os.chmod(work_path, 0o700)
    try:
        cases = asyncio.run(_verify_matrix(work_path, ffmpeg, ffprobe))
    finally:
        shutil.rmtree(work_path, ignore_errors=True)
    residue_count = sum(1 for _ in work_root.iterdir())
    if residue_count:
        raise RuntimeError("synthetic media residue remains")

    receipt = {
        "cases": cases,
        "container_user": "non_root",
        "ffmpeg_configuration": version_lines[2] if len(version_lines) > 2 else "unknown",
        "ffmpeg_version": version_lines[0] if version_lines else "unknown",
        "full_decode": "passed",
        "non_file_protocol": "refused",
        "private_work_root_mode": oct(root_mode),
        "profile_version": CANONICAL_PROFILE_VERSION,
        "synthetic_residue_count": residue_count,
        "validation_version": VALIDATION_VERSION,
    }
    print(json.dumps(receipt, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
