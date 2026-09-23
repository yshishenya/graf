#!/usr/bin/env python3
"""Generate a bounded synthetic v5 package; stream it from the media runtime."""

import argparse
import io
import json
import os
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import wave
from hashlib import sha256
from pathlib import Path
from typing import BinaryIO

MAX_DURATION_SECONDS = 300
FILES = {
    "manifest": "manifest.json",
    "media": "meeting-transcription.wav",
    "playback": "meeting-review.m4a",
}
DESCRIPTORS = {
    "manifest": ("json", 1, 1),
    "media": ("wav-pcm-s16le", 16_000, 1),
    "playback": ("m4a-aac-lc", 48_000, 1),
}
FILE_LIMITS = {
    FILES["manifest"]: 64 * 1024,
    FILES["media"]: 44 + MAX_DURATION_SECONDS * 16_000 * 2,
    FILES["playback"]: 4 * 1024 * 1024,
}
MAX_TRANSFER_BYTES = sum(FILE_LIMITS.values()) + 64 * 1024


def _new_directory(path: Path) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        os.mkdir(path, 0o700)
    except FileExistsError as exc:
        raise ValueError(
            "test artifact output must be a new directory, not an existing path or symlink"
        ) from exc


def validate_duration(duration: int) -> None:
    if type(duration) is not int or not 1 <= duration <= MAX_DURATION_SECONDS:
        raise ValueError(f"duration_seconds must be between 1 and {MAX_DURATION_SECONDS}")


def artifact_descriptor(role: str, data: bytes, duration: int) -> dict:
    codec, rate, channels = DESCRIPTORS[role]
    return {
        "role": role,
        "path": FILES[role],
        "codec": codec,
        "sample_rate_hz": rate,
        "channel_count": channels,
        "duration_seconds": duration,
        "byte_length": len(data),
        "sha256": sha256(data).hexdigest(),
    }


def read_package(path: Path) -> tuple[dict, dict[str, bytes]]:
    """Validate bounded files before transfer/upload, without ffmpeg in rec-api."""
    if path.is_symlink() or not path.is_dir():
        raise ValueError("test artifact must be a regular directory")
    payloads = {}
    for role, name in FILES.items():
        descriptor = os.open(path / name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(descriptor, "rb") as handle:
            metadata = os.fstat(handle.fileno())
            if not stat.S_ISREG(metadata.st_mode) or not 0 < metadata.st_size <= FILE_LIMITS[name]:
                raise ValueError("invalid test artifact file size or type")
            data = handle.read(FILE_LIMITS[name] + 1)
        if len(data) != metadata.st_size:
            raise ValueError("test artifact changed while reading")
        payloads[role] = data
    manifest = json.loads(payloads["manifest"])
    if (
        manifest.get("schema_version") != "local-recording-manifest.v5"
        or manifest.get("source_kind") != "initial_mixed_recording"
        or manifest.get("media_scribe_source_mode") != "single_wav_v1"
    ):
        raise ValueError("unsupported test artifact manifest")
    duration = manifest.get("duration_seconds")
    validate_duration(duration)
    if manifest.get("tracks") != [
        artifact_descriptor(role, payloads[role], duration) for role in ("media", "playback")
    ]:
        raise ValueError("test artifact descriptor or checksum mismatch")
    with wave.open(io.BytesIO(payloads["media"]), "rb") as audio:
        frames = duration * 16_000
        if (
            (audio.getnchannels(), audio.getsampwidth(), audio.getframerate(), audio.getnframes())
            != (1, 2, 16_000, frames)
            or audio.getcomptype() != "NONE"
            or len(audio.readframes(frames)) != frames * 2
        ):
            raise ValueError("invalid canonical WAV")
    # The producer decodes the AAC in media-runtime; the receiver needs no
    # codec dependency. Reject obvious text placeholders here as well.
    if payloads["playback"][4:8] != b"ftyp":
        raise ValueError("invalid M4A container")
    return manifest, payloads


def create_package(path: Path, duration: int) -> None:
    validate_duration(duration)
    _new_directory(path)
    try:
        with wave.open(str(path / FILES["media"]), "wb") as audio:
            audio.setparams((1, 2, 16_000, 0, "NONE", "not compressed"))
            for _ in range(duration):
                audio.writeframesraw(b"\0\0" * 16_000)
        subprocess.run(
            [
                "ffmpeg",
                "-nostdin",
                "-hide_banner",
                "-loglevel",
                "error",
                "-n",
                "-i",
                str(path / FILES["media"]),
                "-map",
                "0:a:0",
                "-vn",
                "-ac",
                "1",
                "-ar",
                "48000",
                "-c:a",
                "aac",
                "-profile:a",
                "aac_low",
                "-b:a",
                "64000",
                "-threads",
                "1",
                "-movflags",
                "+faststart",
                str(path / FILES["playback"]),
            ],
            check=True,
            timeout=90,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        subprocess.run(
            [
                "ffmpeg",
                "-nostdin",
                "-hide_banner",
                "-loglevel",
                "error",
                "-xerror",
                "-i",
                str(path / FILES["playback"]),
                "-map",
                "0:a:0",
                "-f",
                "null",
                "-",
            ],
            check=True,
            timeout=90,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        manifest = {
            "schema_version": "local-recording-manifest.v5",
            "source_kind": "initial_mixed_recording",
            "media_scribe_source_mode": "single_wav_v1",
            "canonical_mix_profile": "canonical-mix.v1",
            "duration_seconds": duration,
            "tracks": [
                artifact_descriptor(role, (path / FILES[role]).read_bytes(), duration)
                for role in ("media", "playback")
            ],
        }
        (path / FILES["manifest"]).write_bytes(json.dumps(manifest, sort_keys=True).encode())
        read_package(path)
    except BaseException:
        shutil.rmtree(path)
        raise


def stream_package(stream: BinaryIO, duration: int) -> None:
    # Honors media-runtime's writable TMPDIR, including cleanup on broken pipe.
    with tempfile.TemporaryDirectory(prefix="graf-smoke-") as temporary:
        path = Path(temporary) / "package"
        create_package(path, duration)
        with tarfile.open(fileobj=stream, mode="w|", format=tarfile.USTAR_FORMAT) as archive:
            for name in FILES.values():
                archive.add(path / name, arcname=name, recursive=False)


class _BoundedReader:
    def __init__(self, stream: BinaryIO) -> None:
        self.stream = stream
        self.remaining = MAX_TRANSFER_BYTES
        self.tail = b""
        self.size = 0

    def read(self, size: int = -1) -> bytes:
        data = self.stream.read(min(size if size >= 0 else self.remaining + 1, self.remaining + 1))
        self.remaining -= len(data)
        if self.remaining < 0:
            raise ValueError("test artifact transfer exceeds size limit")
        self.tail = (self.tail + data)[-1024:]
        self.size += len(data)
        return data


def receive_package(stream: BinaryIO, path: Path) -> None:
    _new_directory(path)
    try:
        bounded = _BoundedReader(stream)
        seen = set()
        with tarfile.open(fileobj=bounded, mode="r|", ignore_zeros=True) as archive:
            for member in archive:
                if (
                    member.name not in FILE_LIMITS
                    or member.name in seen
                    or not member.isfile()
                    or member.issparse()
                    or not 0 < member.size <= FILE_LIMITS[member.name]
                ):
                    raise ValueError("invalid test artifact archive member")
                seen.add(member.name)
                # Do not extract paths, owners, permissions, links or devices.
                source = archive.extractfile(member)
                if source is None:
                    raise ValueError("missing test artifact archive body")
                with source, (path / member.name).open("xb") as target:
                    shutil.copyfileobj(source, target, length=64 * 1024)
        if seen != set(FILE_LIMITS):
            raise ValueError("incomplete test artifact archive")
        # Include trailing padding in the bound on the entire input stream.
        while bounded.read(64 * 1024):
            pass
        if bounded.size % 512 or bounded.tail != b"\0" * 1024:
            raise ValueError("incomplete test artifact tar terminator")
        read_package(path)
    except BaseException:
        shutil.rmtree(path)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--stream", action="store_true")
    mode.add_argument("--receive", action="store_true")
    parser.add_argument("--duration-seconds", type=int)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if args.stream and args.out or not args.stream and args.out is None:
        parser.error("--out is required except with --stream")
    if args.receive:
        if args.duration_seconds is not None:
            parser.error("--receive reads duration from the manifest")
        receive_package(sys.stdin.buffer, args.out)
    else:
        try:
            validate_duration(args.duration_seconds)
        except ValueError as exc:
            parser.error(str(exc))
        if args.stream:
            stream_package(sys.stdout.buffer, args.duration_seconds)
            return
        create_package(args.out, args.duration_seconds)
    _manifest, payloads = read_package(args.out)
    print(
        json.dumps(
            {"manifest_sha256": sha256(payloads["manifest"]).hexdigest(), "out": str(args.out)}
        )
    )


if __name__ == "__main__":
    main()
