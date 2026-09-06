from __future__ import annotations

import asyncio
import json
import os
import signal
import stat
import struct
from collections.abc import Collection, Sequence
from contextlib import suppress
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from hashlib import sha256
from pathlib import Path

MAX_PROBE_STDOUT_BYTES = 256 * 1024
MAX_DECODE_PROGRESS_BYTES = 64 * 1024
MAX_PROCESS_STDERR_BYTES = 1024 * 1024
MAX_OUTPUT_BYTES = 128 * 1024 * 1024
MAX_DURATION_SECONDS = Decimal("14400")
DECODE_GUARD_SECONDS = MAX_DURATION_SECONDS + Decimal("1")
DECODE_PROGRESS_PERIOD_SECONDS = 60
MAX_STREAMS = 16
MAX_AUDIO_STREAMS = 8
MIN_REUSE_BIT_RATE = 56_000
MAX_REUSE_BIT_RATE = 72_000
MAX_BMFF_BOXES = 2_048
MAX_BMFF_DEPTH = 8
MAX_EBML_HEADER_BYTES = 4_096
COPY_CHUNK_BYTES = 4 * 1024 * 1024
FORMAT_WHITELIST = "wav,w64,mp3,aac,flac,ogg,mov,matroska,webm"
COPY_REMUX_DURATION_TOLERANCE_SECONDS = Decimal("0.050")
TRANSCODE_MIX_DURATION_TOLERANCE_SECONDS = Decimal("0.250")
TOLERANT_FIRST_DURATION_TOLERANCE_SECONDS = Decimal("0.250")
MAX_GENERATED_DURATION_SECONDS = MAX_DURATION_SECONDS + TOLERANT_FIRST_DURATION_TOLERANCE_SECONDS
RECOVERED_TRANSCODE_MAX_DURATION_LOSS_SECONDS = Decimal("60")
RECOVERED_TRANSCODE_MAX_DURATION_LOSS_RATIO = Decimal("0.02")

_PROBE_TOP_LEVEL_KEYS = frozenset(
    {"format", "streams", "chapters", "error", "programs", "stream_groups"}
)
_PROBE_FORMAT_KEYS = frozenset({"format_name", "start_time", "duration", "size", "bit_rate"})
_PROBE_STREAM_KEYS = frozenset(
    {
        "index",
        "codec_type",
        "codec_name",
        "codec_tag_string",
        "profile",
        "sample_rate",
        "channels",
        "start_time",
        "duration",
        "bit_rate",
        "disposition",
        "tags",
    }
)
_PROBE_DISPOSITION_KEYS = frozenset({"default", "attached_pic"})
_CONTAINER_BOXES = frozenset({"moov", "trak", "mdia", "minf", "stbl", "edts", "dinf", "udta"})
_SAFE_TOP_LEVEL_BOXES = frozenset({"ftyp", "moov", "free", "mdat"})
_SAFE_SCANNED_CHILD_BOXES = frozenset(
    {
        "mvhd",
        "trak",
        "tkhd",
        "edts",
        "elst",
        "mdia",
        "mdhd",
        "hdlr",
        "minf",
        "smhd",
        "dinf",
        "dref",
        "stbl",
        "stsd",
        "stts",
        "stsc",
        "stsz",
        "stco",
        "co64",
        "sgpd",
        "sbgp",
        "udta",
        "meta",
        "ilst",
    }
)


class MediaPolicyError(ValueError):
    def __init__(self, reason_code: str) -> None:
        self.reason_code = reason_code
        super().__init__(f"Media operation rejected: {reason_code}")


class ProcessOutputLimitError(MediaPolicyError):
    def __init__(self) -> None:
        super().__init__("dependency_unavailable")


class ProcessTimeoutError(MediaPolicyError):
    def __init__(self) -> None:
        super().__init__("normalization_timeout")


class ProcessExecutionError(MediaPolicyError):
    def __init__(self, *, return_code: int, stderr_byte_count: int) -> None:
        self.return_code = return_code
        self.stderr_byte_count = stderr_byte_count
        super().__init__("dependency_unavailable")


class NormalizationAction(StrEnum):
    BYTE_COPY = "source_byte_copy"
    FASTSTART_REMUX = "lossless_faststart_remux"
    SINGLE_TRANSCODE = "single_source_transcode"
    RECOVERED_SINGLE_TRANSCODE = "recovered_single_source_transcode"
    DUAL_MIX_TRANSCODE = "dual_source_mix_transcode"


@dataclass(frozen=True, slots=True)
class ProbeStream:
    index: int
    codec_type: str
    codec_name: str
    codec_tag_string: str | None
    profile: str | None
    sample_rate_hz: int | None
    channels: int | None
    start_time_seconds: Decimal | None
    duration_seconds: Decimal | None
    bit_rate: int | None
    default: bool
    attached_picture: bool


@dataclass(frozen=True, slots=True)
class ProbeFacts:
    format_names: tuple[str, ...]
    start_time_seconds: Decimal | None
    duration_seconds: Decimal | None
    size_bytes: int | None
    bit_rate: int | None
    streams: tuple[ProbeStream, ...]
    chapter_count: int

    @property
    def stream_count(self) -> int:
        return len(self.streams)

    @property
    def audio_streams(self) -> tuple[ProbeStream, ...]:
        return tuple(stream for stream in self.streams if stream.codec_type == "audio")


@dataclass(frozen=True, slots=True)
class BMFFLayout:
    box_types: tuple[str, ...]
    moov_before_mdat: bool
    fragmented: bool
    has_private_metadata: bool = False


@dataclass(frozen=True, slots=True)
class ProcessResult:
    return_code: int
    stdout: bytes
    stderr_byte_count: int


@dataclass(frozen=True, slots=True)
class FullDecodeReceipt:
    duration_seconds: Decimal


@dataclass(frozen=True, slots=True)
class FileDigest:
    byte_length: int
    sha256_hex: str


def _reject_json_constant(_: str) -> None:
    raise ValueError("invalid numeric constant")


def _decimal_value(value: object, *, allow_none: bool = True) -> Decimal | None:
    if value is None and allow_none:
        return None
    if isinstance(value, bool) or not isinstance(value, str | int):
        raise MediaPolicyError("corrupt_source")
    try:
        parsed = Decimal(str(value))
    except InvalidOperation as exc:
        raise MediaPolicyError("corrupt_source") from exc
    if not parsed.is_finite():
        raise MediaPolicyError("corrupt_source")
    return parsed


def _int_value(value: object, *, allow_none: bool = True) -> int | None:
    if value is None and allow_none:
        return None
    if isinstance(value, bool) or not isinstance(value, str | int):
        raise MediaPolicyError("corrupt_source")
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise MediaPolicyError("corrupt_source") from exc
    if str(parsed) != str(value).strip() and not isinstance(value, int):
        raise MediaPolicyError("corrupt_source")
    return parsed


def _mapping(value: object) -> dict[str, object]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise MediaPolicyError("corrupt_source")
    return value


def _duration_tag_value(value: object) -> Decimal | None:
    if value is None:
        return None
    if not isinstance(value, str) or len(value) > 32 or not value.isascii():
        raise MediaPolicyError("corrupt_source")
    parts = value.split(":")
    if len(parts) != 3 or not parts[0].isdigit() or not parts[1].isdigit():
        raise MediaPolicyError("corrupt_source")
    try:
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = Decimal(parts[2])
    except (InvalidOperation, ValueError) as exc:
        raise MediaPolicyError("corrupt_source") from exc
    if minutes >= 60 or not seconds.is_finite() or not Decimal(0) <= seconds < Decimal(60):
        raise MediaPolicyError("corrupt_source")
    return Decimal(hours * 3600 + minutes * 60) + seconds


def parse_probe_output(payload: bytes) -> ProbeFacts:
    if not payload or len(payload) > MAX_PROBE_STDOUT_BYTES:
        raise MediaPolicyError("corrupt_source")
    try:
        document = json.loads(payload.decode("utf-8"), parse_constant=_reject_json_constant)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise MediaPolicyError("corrupt_source") from exc
    root = _mapping(document)
    if not set(root) <= _PROBE_TOP_LEVEL_KEYS or root.get("error"):
        raise MediaPolicyError("corrupt_source")
    if root.get("programs", []) != [] or root.get("stream_groups", []) != []:
        raise MediaPolicyError("corrupt_source")

    format_data = _mapping(root.get("format", {}))
    if not set(format_data) <= _PROBE_FORMAT_KEYS:
        raise MediaPolicyError("corrupt_source")
    format_name = format_data.get("format_name")
    if not isinstance(format_name, str) or not format_name.strip():
        raise MediaPolicyError("unsupported_container")
    format_names = tuple(part.strip().lower() for part in format_name.split(",") if part.strip())

    raw_streams = root.get("streams", [])
    if not isinstance(raw_streams, list):
        raise MediaPolicyError("corrupt_source")
    if len(raw_streams) > MAX_STREAMS:
        raise MediaPolicyError("stream_limit_exceeded")

    streams: list[ProbeStream] = []
    seen_indexes: set[int] = set()
    for raw_stream in raw_streams:
        stream_data = _mapping(raw_stream)
        if not set(stream_data) <= _PROBE_STREAM_KEYS:
            raise MediaPolicyError("corrupt_source")
        index = _int_value(stream_data.get("index"), allow_none=False)
        if index is None or index < 0 or index in seen_indexes:
            raise MediaPolicyError("corrupt_source")
        seen_indexes.add(index)
        codec_type = stream_data.get("codec_type")
        codec_name = stream_data.get("codec_name")
        codec_tag_string = stream_data.get("codec_tag_string")
        profile = stream_data.get("profile")
        if not isinstance(codec_type, str) or not isinstance(codec_name, str):
            raise MediaPolicyError("corrupt_source")
        if codec_tag_string is not None and (
            not isinstance(codec_tag_string, str)
            or not codec_tag_string
            or len(codec_tag_string) > 32
            or not codec_tag_string.isascii()
            or not codec_tag_string.isprintable()
        ):
            raise MediaPolicyError("corrupt_source")
        if profile is not None and not isinstance(profile, str):
            raise MediaPolicyError("corrupt_source")
        disposition = _mapping(stream_data.get("disposition", {}))
        if not set(disposition) <= _PROBE_DISPOSITION_KEYS:
            raise MediaPolicyError("corrupt_source")
        default = _int_value(disposition.get("default", 0), allow_none=False)
        attached = _int_value(disposition.get("attached_pic", 0), allow_none=False)
        if default not in {0, 1} or attached not in {0, 1}:
            raise MediaPolicyError("corrupt_source")
        sample_rate = _int_value(stream_data.get("sample_rate"))
        channels = _int_value(stream_data.get("channels"))
        bit_rate = _int_value(stream_data.get("bit_rate"))
        tags = _mapping(stream_data.get("tags", {}))
        if not set(tags) <= {"DURATION"}:
            raise MediaPolicyError("corrupt_source")
        duration = _decimal_value(stream_data.get("duration"))
        tagged_duration = _duration_tag_value(tags.get("DURATION"))
        if (
            duration is not None
            and tagged_duration is not None
            and abs(duration - tagged_duration) > TOLERANT_FIRST_DURATION_TOLERANCE_SECONDS
        ):
            raise MediaPolicyError("source_mismatch")
        duration = duration or tagged_duration
        if sample_rate is not None and sample_rate <= 0:
            raise MediaPolicyError("corrupt_source")
        if channels is not None and channels <= 0:
            raise MediaPolicyError("corrupt_source")
        if bit_rate is not None and bit_rate <= 0:
            raise MediaPolicyError("corrupt_source")
        streams.append(
            ProbeStream(
                index=index,
                codec_type=codec_type.lower(),
                codec_name=codec_name.lower(),
                codec_tag_string=(
                    codec_tag_string.casefold() if codec_tag_string is not None else None
                ),
                profile=profile,
                sample_rate_hz=sample_rate,
                channels=channels,
                start_time_seconds=_decimal_value(stream_data.get("start_time")),
                duration_seconds=duration,
                bit_rate=bit_rate,
                default=default == 1,
                attached_picture=attached == 1,
            )
        )

    audio_count = sum(stream.codec_type == "audio" for stream in streams)
    if audio_count > MAX_AUDIO_STREAMS:
        raise MediaPolicyError("stream_limit_exceeded")
    chapters = root.get("chapters", [])
    if not isinstance(chapters, list):
        raise MediaPolicyError("corrupt_source")

    size_bytes = _int_value(format_data.get("size"))
    bit_rate = _int_value(format_data.get("bit_rate"))
    if size_bytes is not None and size_bytes < 0:
        raise MediaPolicyError("corrupt_source")
    if bit_rate is not None and bit_rate <= 0:
        raise MediaPolicyError("corrupt_source")
    return ProbeFacts(
        format_names=format_names,
        start_time_seconds=_decimal_value(format_data.get("start_time")),
        duration_seconds=_decimal_value(format_data.get("duration")),
        size_bytes=size_bytes,
        bit_rate=bit_rate,
        streams=tuple(streams),
        chapter_count=len(chapters),
    )


def parse_full_decode_progress(payload: bytes) -> FullDecodeReceipt:
    if not payload or len(payload) > MAX_DECODE_PROGRESS_BYTES:
        raise MediaPolicyError("dependency_unavailable")
    try:
        lines = payload.decode("ascii").splitlines()
    except UnicodeDecodeError as exc:
        raise MediaPolicyError("dependency_unavailable") from exc

    observed_microseconds: list[int] = []
    final_progress: str | None = None
    for line in lines:
        key, separator, value = line.partition("=")
        if not separator:
            raise MediaPolicyError("dependency_unavailable")
        if key == "out_time_us":
            if not value.isascii() or not value.isdecimal():
                raise MediaPolicyError("dependency_unavailable")
            parsed = int(value)
            if observed_microseconds and parsed < observed_microseconds[-1]:
                raise MediaPolicyError("dependency_unavailable")
            observed_microseconds.append(parsed)
        elif key == "progress":
            if value not in {"continue", "end"}:
                raise MediaPolicyError("dependency_unavailable")
            final_progress = value

    if (
        not observed_microseconds
        or final_progress != "end"
        or not lines
        or lines[-1] != "progress=end"
    ):
        raise MediaPolicyError("dependency_unavailable")
    return FullDecodeReceipt(
        duration_seconds=Decimal(observed_microseconds[-1]) / Decimal(1_000_000)
    )


def _container_family(format_names: tuple[str, ...]) -> str | None:
    names = set(format_names)
    if names & {"wav", "w64"}:
        return "wav"
    if "mp3" in names:
        return "mp3"
    if "aac" in names:
        return "aac"
    if "flac" in names:
        return "flac"
    if names & {"ogg", "oga"}:
        return "ogg"
    if "matroska" in names:
        return "matroska"
    if "webm" in names:
        return "webm"
    if names & {"mov", "mp4", "m4a", "m4v", "3gp", "3g2", "mj2"}:
        return "mov"
    return None


def _codec_family(codec_name: str) -> str:
    if codec_name.startswith("pcm_"):
        return "pcm"
    return codec_name


_ALLOWED_CODEC_FAMILIES = {
    "wav": frozenset({"pcm", "adpcm_ima_wav", "adpcm_ms"}),
    "mp3": frozenset({"mp3"}),
    "aac": frozenset({"aac"}),
    "flac": frozenset({"flac"}),
    "ogg": frozenset({"vorbis", "opus", "flac"}),
    "mov": frozenset({"aac", "alac", "mp3", "pcm"}),
    "webm": frozenset({"opus", "vorbis"}),
    "matroska": frozenset({"opus", "vorbis", "aac", "mp3", "flac", "pcm"}),
}


def select_audio_stream(
    facts: ProbeFacts,
    *,
    container_family: str | None = None,
) -> ProbeStream:
    family = container_family or _container_family(facts.format_names)
    if family is None:
        raise MediaPolicyError("unsupported_container")
    audio_streams = facts.audio_streams
    if not audio_streams:
        raise MediaPolicyError("no_audio")
    if any(stream.codec_tag_string in {"enca", "encv"} for stream in audio_streams):
        raise MediaPolicyError("encrypted_media")
    usable = [
        stream
        for stream in audio_streams
        if _codec_family(stream.codec_name) in _ALLOWED_CODEC_FAMILIES[family]
        and not stream.attached_picture
        and (stream.sample_rate_hz is None or stream.sample_rate_hz > 0)
        and (stream.channels is None or stream.channels > 0)
    ]
    if not usable:
        raise MediaPolicyError("unsupported_codec")
    if len(usable) == 1:
        return usable[0]
    defaults = [stream for stream in usable if stream.default]
    if len(defaults) == 1:
        return defaults[0]
    raise MediaPolicyError("ambiguous_audio_tracks")


def _ebml_vint(
    payload: bytes,
    offset: int,
    *,
    keep_marker: bool,
    max_length: int,
) -> tuple[int, int]:
    if offset >= len(payload):
        raise MediaPolicyError("corrupt_source")
    first = payload[offset]
    length = next(
        (candidate for candidate in range(1, max_length + 1) if first & (0x80 >> (candidate - 1))),
        0,
    )
    if length == 0 or offset + length > len(payload):
        raise MediaPolicyError("corrupt_source")
    value = first if keep_marker else first & ((0x80 >> (length - 1)) - 1)
    for byte in payload[offset + 1 : offset + length]:
        value = (value << 8) | byte
    if not keep_marker and value == (1 << (7 * length)) - 1:
        raise MediaPolicyError("corrupt_source")
    return value, length


def inspect_ebml_doctype(path: str | Path) -> str:
    source = Path(path)
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        file_descriptor = os.open(source, flags)
    except OSError as exc:
        raise MediaPolicyError("corrupt_source") from exc
    try:
        file_stat = os.fstat(file_descriptor)
        if not stat.S_ISREG(file_stat.st_mode) or file_stat.st_size <= 0:
            raise MediaPolicyError("corrupt_source")
        payload = os.read(file_descriptor, min(file_stat.st_size, MAX_EBML_HEADER_BYTES))
    finally:
        os.close(file_descriptor)

    element_id, id_length = _ebml_vint(payload, 0, keep_marker=True, max_length=4)
    if element_id != 0x1A45DFA3:
        raise MediaPolicyError("unsupported_container")
    header_size, size_length = _ebml_vint(
        payload,
        id_length,
        keep_marker=False,
        max_length=8,
    )
    header_start = id_length + size_length
    header_end = header_start + header_size
    if header_end > len(payload):
        raise MediaPolicyError("corrupt_source")

    offset = header_start
    while offset < header_end:
        child_id, child_id_length = _ebml_vint(
            payload,
            offset,
            keep_marker=True,
            max_length=4,
        )
        child_size, child_size_length = _ebml_vint(
            payload,
            offset + child_id_length,
            keep_marker=False,
            max_length=8,
        )
        value_start = offset + child_id_length + child_size_length
        value_end = value_start + child_size
        if value_end > header_end:
            raise MediaPolicyError("corrupt_source")
        if child_id == 0x4282:
            try:
                document_type = payload[value_start:value_end].decode("ascii").lower()
            except UnicodeDecodeError as exc:
                raise MediaPolicyError("corrupt_source") from exc
            if document_type in {"matroska", "webm"}:
                return document_type
            raise MediaPolicyError("unsupported_container")
        offset = value_end
    raise MediaPolicyError("corrupt_source")


def inspected_container_family(facts: ProbeFacts, source_path: str | Path) -> str | None:
    names = set(facts.format_names)
    if {"matroska", "webm"} <= names:
        return inspect_ebml_doctype(source_path)
    return _container_family(facts.format_names)


def validate_canonical_profile(
    facts: ProbeFacts,
    *,
    bmff_layout: BMFFLayout,
    byte_length: int,
    full_decode_passed: bool,
    enforce_reuse_bitrate: bool = True,
) -> None:
    if facts.duration_seconds is None or facts.duration_seconds <= 0:
        raise MediaPolicyError("generated_output_invalid")
    if facts.duration_seconds > MAX_GENERATED_DURATION_SECONDS:
        raise MediaPolicyError("duration_limit_exceeded")
    if not 0 < byte_length <= MAX_OUTPUT_BYTES:
        raise MediaPolicyError("generated_output_invalid")
    if facts.stream_count != 1 or len(facts.audio_streams) != 1 or facts.chapter_count:
        raise MediaPolicyError("generated_output_invalid")
    if _container_family(facts.format_names) != "mov":
        raise MediaPolicyError("generated_output_invalid")
    stream = facts.audio_streams[0]
    effective_start = stream.start_time_seconds
    if effective_start is None:
        effective_start = facts.start_time_seconds
    if effective_start is None or not Decimal("0") <= effective_start <= Decimal("0.100"):
        raise MediaPolicyError("generated_output_invalid")
    if (
        stream.codec_name != "aac"
        or stream.profile not in {"LC", "AAC LC"}
        or stream.sample_rate_hz != 48_000
        or stream.channels != 1
        or not stream.default
        or stream.attached_picture
    ):
        raise MediaPolicyError("generated_output_invalid")
    if enforce_reuse_bitrate and (
        stream.bit_rate is None or not MIN_REUSE_BIT_RATE <= stream.bit_rate <= MAX_REUSE_BIT_RATE
    ):
        raise MediaPolicyError("generated_output_invalid")
    if (
        not bmff_layout.moov_before_mdat
        or bmff_layout.fragmented
        or bmff_layout.has_private_metadata
        or not full_decode_passed
    ):
        raise MediaPolicyError("generated_output_invalid")


def validate_duration_alignment(
    *,
    action: NormalizationAction,
    source_durations_seconds: Sequence[Decimal],
    output_duration_seconds: Decimal,
) -> None:
    expected_source_count = 2 if action is NormalizationAction.DUAL_MIX_TRANSCODE else 1
    if (
        len(source_durations_seconds) != expected_source_count
        or not output_duration_seconds.is_finite()
        or output_duration_seconds <= 0
        or output_duration_seconds > MAX_GENERATED_DURATION_SECONDS
        or any(
            not duration.is_finite() or duration <= 0 or duration > MAX_DURATION_SECONDS
            for duration in source_durations_seconds
        )
    ):
        raise MediaPolicyError("generated_output_invalid")
    expected_duration = (
        max(source_durations_seconds)
        if action is NormalizationAction.DUAL_MIX_TRANSCODE
        else source_durations_seconds[0]
    )
    tolerance = (
        COPY_REMUX_DURATION_TOLERANCE_SECONDS
        if action in {NormalizationAction.BYTE_COPY, NormalizationAction.FASTSTART_REMUX}
        else _recovered_transcode_duration_tolerance(source_durations_seconds[0])
        if action is NormalizationAction.RECOVERED_SINGLE_TRANSCODE
        else TRANSCODE_MIX_DURATION_TOLERANCE_SECONDS
    )
    if abs(output_duration_seconds - expected_duration) > tolerance:
        raise MediaPolicyError("generated_output_invalid")


def validate_tolerant_source_duration(facts: ProbeFacts, stream: ProbeStream) -> Decimal:
    """Return bounded probe duration without claiming that damaged frames were recovered."""

    durations = tuple(
        duration
        for duration in (facts.duration_seconds, stream.duration_seconds)
        if duration is not None
    )
    if not durations or any(not duration.is_finite() or duration <= 0 for duration in durations):
        raise MediaPolicyError("corrupt_source")
    if any(duration > MAX_DURATION_SECONDS for duration in durations):
        raise MediaPolicyError("duration_limit_exceeded")
    has_video = any(
        candidate.codec_type == "video" and not candidate.attached_picture
        for candidate in facts.streams
    )
    if (
        not has_video
        and len(durations) == 2
        and abs(durations[0] - durations[1]) > TOLERANT_FIRST_DURATION_TOLERANCE_SECONDS
    ):
        raise MediaPolicyError("source_mismatch")
    selected_duration = stream.duration_seconds or facts.duration_seconds
    if selected_duration is None:  # Kept explicit for type checkers and future edits.
        raise MediaPolicyError("corrupt_source")
    return selected_duration


def validate_tolerant_output_duration(
    *,
    source_duration_seconds: Decimal,
    output_format_duration_seconds: Decimal | None,
    output_stream_duration_seconds: Decimal | None,
    output_decode_duration_seconds: Decimal,
) -> None:
    """Accept bounded frame loss while keeping generated timelines internally exact."""

    probe_durations = tuple(
        duration
        for duration in (
            output_format_duration_seconds,
            output_stream_duration_seconds,
        )
        if duration is not None
    )
    if not probe_durations:
        raise MediaPolicyError("generated_output_invalid")
    if (
        not source_duration_seconds.is_finite()
        or source_duration_seconds <= 0
        or source_duration_seconds > MAX_DURATION_SECONDS
        or any(
            not duration.is_finite() or duration <= 0 or duration > MAX_GENERATED_DURATION_SECONDS
            for duration in (*probe_durations, output_decode_duration_seconds)
        )
    ):
        raise MediaPolicyError("generated_output_invalid")
    if any(
        abs(duration - output_decode_duration_seconds) > TOLERANT_FIRST_DURATION_TOLERANCE_SECONDS
        for duration in probe_durations
    ):
        raise MediaPolicyError("generated_output_invalid")
    if (
        output_decode_duration_seconds - source_duration_seconds
        > TOLERANT_FIRST_DURATION_TOLERANCE_SECONDS
    ):
        raise MediaPolicyError("generated_output_invalid")
    if (
        source_duration_seconds - output_decode_duration_seconds
        > _recovered_transcode_duration_tolerance(source_duration_seconds)
    ):
        raise MediaPolicyError("generated_output_invalid")


def _recovered_transcode_duration_tolerance(source_duration: Decimal) -> Decimal:
    """Bound how much tolerant decoding may discard before rejecting output."""

    return max(
        TRANSCODE_MIX_DURATION_TOLERANCE_SECONDS,
        min(
            RECOVERED_TRANSCODE_MAX_DURATION_LOSS_SECONDS,
            source_duration * RECOVERED_TRANSCODE_MAX_DURATION_LOSS_RATIO,
        ),
    )


def _read_exact(file_descriptor: int, offset: int, length: int) -> bytes:
    data = os.pread(file_descriptor, length, offset)
    if len(data) != length:
        raise MediaPolicyError("generated_output_invalid")
    return data


def _box_header(file_descriptor: int, offset: int, boundary: int) -> tuple[str, int, int]:
    if boundary - offset < 8:
        raise MediaPolicyError("generated_output_invalid")
    header = _read_exact(file_descriptor, offset, 8)
    size_32, raw_type = struct.unpack(">I4s", header)
    box_type = raw_type.decode("latin-1")
    header_length = 8
    if size_32 == 0:
        raise MediaPolicyError("generated_output_invalid")
    if size_32 == 1:
        if boundary - offset < 16:
            raise MediaPolicyError("generated_output_invalid")
        box_size = struct.unpack(">Q", _read_exact(file_descriptor, offset + 8, 8))[0]
        header_length = 16
    else:
        box_size = size_32
    if box_size < header_length or offset + box_size > boundary:
        raise MediaPolicyError("generated_output_invalid")
    return box_type, header_length, box_size


def _scan_nested_boxes(
    file_descriptor: int,
    start: int,
    end: int,
    *,
    parent_type: str,
    depth: int,
    counter: list[int],
) -> tuple[bool, bool]:
    if depth > MAX_BMFF_DEPTH:
        raise MediaPolicyError("generated_output_invalid")
    offset = start
    fragmented = False
    private_metadata = False
    while offset < end:
        box_type, header_length, box_size = _box_header(file_descriptor, offset, end)
        counter[0] += 1
        if counter[0] > MAX_BMFF_BOXES:
            raise MediaPolicyError("generated_output_invalid")
        payload_start = offset + header_length
        payload_end = offset + box_size
        if box_type == "mvex" or box_type == "moof":
            fragmented = True
        if box_type not in _SAFE_SCANNED_CHILD_BOXES:
            private_metadata = True
        if box_type == "ilst" and payload_end > payload_start:
            private_metadata = True
        if box_type == "hdlr" and parent_type == "meta":
            if payload_end - payload_start < 24:
                raise MediaPolicyError("generated_output_invalid")
            handler_name = _read_exact(
                file_descriptor,
                payload_start + 24,
                payload_end - payload_start - 24,
            )
            if handler_name.strip(b"\x00"):
                private_metadata = True
        if box_type == "meta":
            if payload_end - payload_start < 4:
                raise MediaPolicyError("generated_output_invalid")
            child_fragmented, child_private = _scan_nested_boxes(
                file_descriptor,
                payload_start + 4,
                payload_end,
                parent_type=box_type,
                depth=depth + 1,
                counter=counter,
            )
            fragmented = fragmented or child_fragmented
            private_metadata = private_metadata or child_private
        elif box_type in _CONTAINER_BOXES:
            child_fragmented, child_private = _scan_nested_boxes(
                file_descriptor,
                payload_start,
                payload_end,
                parent_type=box_type,
                depth=depth + 1,
                counter=counter,
            )
            fragmented = fragmented or child_fragmented
            private_metadata = private_metadata or child_private
        offset = payload_end
    if offset != end:
        raise MediaPolicyError("generated_output_invalid")
    return fragmented, private_metadata


def inspect_bmff(path: str | Path) -> BMFFLayout:
    source = Path(path)
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        file_descriptor = os.open(source, flags)
    except OSError as exc:
        raise MediaPolicyError("generated_output_invalid") from exc
    try:
        file_stat = os.fstat(file_descriptor)
        if not stat.S_ISREG(file_stat.st_mode) or not 0 < file_stat.st_size <= MAX_OUTPUT_BYTES:
            raise MediaPolicyError("generated_output_invalid")
        offset = 0
        box_types: list[str] = []
        top_level: dict[str, tuple[int, int]] = {}
        counter = [0]
        fragmented = False
        private_metadata = False
        while offset < file_stat.st_size:
            box_type, header_length, box_size = _box_header(
                file_descriptor,
                offset,
                file_stat.st_size,
            )
            counter[0] += 1
            if counter[0] > MAX_BMFF_BOXES:
                raise MediaPolicyError("generated_output_invalid")
            box_types.append(box_type)
            if box_type not in _SAFE_TOP_LEVEL_BOXES:
                private_metadata = True
            if box_type == "free" and box_size != header_length:
                private_metadata = True
            if box_type in {"ftyp", "moov", "mdat"}:
                if box_type in top_level:
                    raise MediaPolicyError("generated_output_invalid")
                top_level[box_type] = (offset, box_size)
            if box_type == "ftyp" and box_size - header_length < 8:
                raise MediaPolicyError("generated_output_invalid")
            if box_type == "moof":
                fragmented = True
            if box_type == "moov" and box_size > header_length:
                child_fragmented, child_private = _scan_nested_boxes(
                    file_descriptor,
                    offset + header_length,
                    offset + box_size,
                    parent_type=box_type,
                    depth=1,
                    counter=counter,
                )
                fragmented = fragmented or child_fragmented
                private_metadata = private_metadata or child_private
            offset += box_size
        if set(top_level) != {"ftyp", "moov", "mdat"} or fragmented:
            raise MediaPolicyError("generated_output_invalid")
        return BMFFLayout(
            box_types=tuple(box_types),
            moov_before_mdat=top_level["moov"][0] < top_level["mdat"][0],
            fragmented=False,
            has_private_metadata=private_metadata,
        )
    finally:
        os.close(file_descriptor)


def _input_guard_arguments() -> list[str]:
    return [
        "-protocol_whitelist",
        "file",
        "-format_whitelist",
        FORMAT_WHITELIST,
        "-probesize",
        "16777216",
        "-analyzeduration",
        "30000000",
    ]


def build_probe_command(executable: str, source_path: str | Path) -> list[str]:
    return [
        executable,
        "-hide_banner",
        "-v",
        "error",
        *_input_guard_arguments(),
        "-show_error",
        "-show_format",
        "-show_streams",
        "-show_chapters",
        "-show_entries",
        (
            "format=format_name,start_time,duration,size,bit_rate:"
            "format_tags=:"
            "stream=index,codec_type,codec_name,codec_tag_string,profile,sample_rate,channels,"
            "start_time,duration,bit_rate:stream_disposition=default,attached_pic:"
            "stream_tags=DURATION:chapter=id,start_time,end_time:chapter_tags="
        ),
        "-of",
        "json=compact=1:string_validation=fail",
        str(source_path),
    ]


def _ffmpeg_preamble(executable: str, *, tolerant: bool = False) -> list[str]:
    return [
        executable,
        "-hide_banner",
        "-loglevel",
        "error",
        "-nostdin",
        *([] if tolerant else ["-xerror"]),
        "-y",
    ]


def _canonical_output_arguments(output_path: str | Path) -> list[str]:
    return [
        "-vn",
        "-sn",
        "-dn",
        "-map_metadata",
        "-1",
        "-map_chapters",
        "-1",
        "-threads",
        "1",
        "-filter_threads",
        "1",
        "-ac",
        "1",
        "-ar",
        "48000",
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
        "-fs",
        str(MAX_OUTPUT_BYTES),
        "-movflags",
        "+faststart",
        "-f",
        "ipod",
        str(output_path),
    ]


def build_transcode_command(
    executable: str,
    source_path: str | Path,
    output_path: str | Path,
    *,
    stream_index: int,
    tolerant: bool = False,
) -> list[str]:
    if stream_index < 0:
        raise ValueError("stream_index must be non-negative")
    return [
        *_ffmpeg_preamble(executable, tolerant=tolerant),
        *_input_guard_arguments(),
        *(["-err_detect", "ignore_err", "-fflags", "+discardcorrupt"] if tolerant else []),
        "-i",
        str(source_path),
        "-map",
        f"0:{stream_index}",
        "-af",
        "aresample=48000:first_pts=0,asetpts=PTS-STARTPTS",
        *(["-t", str(DECODE_GUARD_SECONDS)] if tolerant else []),
        *_canonical_output_arguments(output_path),
    ]


def build_dual_mix_command(
    executable: str,
    microphone_path: str | Path,
    system_path: str | Path,
    output_path: str | Path,
    *,
    microphone_stream_index: int,
    system_stream_index: int,
) -> list[str]:
    if microphone_stream_index < 0 or system_stream_index < 0:
        raise ValueError("stream indexes must be non-negative")
    mix_filter = (
        f"[0:{microphone_stream_index}]aresample=48000:first_pts=0,"
        "asetpts=PTS-STARTPTS,volume=0.5[mic];"
        f"[1:{system_stream_index}]aresample=48000:first_pts=0,"
        "asetpts=PTS-STARTPTS,volume=0.5[system];"
        "[mic][system]amix=inputs=2:duration=longest:dropout_transition=0:normalize=0,"
        "asoftclip=type=hard:threshold=1[mix]"
    )
    return [
        *_ffmpeg_preamble(executable),
        *_input_guard_arguments(),
        "-i",
        str(microphone_path),
        *_input_guard_arguments(),
        "-i",
        str(system_path),
        "-filter_complex_threads",
        "1",
        "-filter_complex",
        mix_filter,
        "-map",
        "[mix]",
        *_canonical_output_arguments(output_path),
    ]


def build_lossless_remux_command(
    executable: str,
    source_path: str | Path,
    output_path: str | Path,
    *,
    stream_index: int,
) -> list[str]:
    if stream_index < 0:
        raise ValueError("stream_index must be non-negative")
    return [
        *_ffmpeg_preamble(executable),
        *_input_guard_arguments(),
        "-i",
        str(source_path),
        "-map",
        f"0:{stream_index}",
        "-vn",
        "-sn",
        "-dn",
        "-map_metadata",
        "-1",
        "-map_chapters",
        "-1",
        "-c:a",
        "copy",
        "-fflags",
        "+bitexact",
        "-disposition:a:0",
        "default",
        "-fs",
        str(MAX_OUTPUT_BYTES),
        "-movflags",
        "+faststart",
        "-f",
        "ipod",
        str(output_path),
    ]


def build_full_decode_command(
    executable: str,
    source_path: str | Path,
    *,
    stream_index: int,
) -> list[str]:
    if stream_index < 0:
        raise ValueError("stream_index must be non-negative")
    return [
        executable,
        "-hide_banner",
        "-loglevel",
        "error",
        "-nostdin",
        "-xerror",
        *_input_guard_arguments(),
        "-i",
        str(source_path),
        "-map",
        f"0:{stream_index}",
        "-vn",
        "-sn",
        "-dn",
        "-af",
        "aresample=48000:first_pts=0,asetpts=N/SR/TB",
        "-t",
        str(DECODE_GUARD_SECONDS),
        "-stats_period",
        str(DECODE_PROGRESS_PERIOD_SECONDS),
        "-progress",
        "pipe:1",
        "-nostats",
        "-f",
        "null",
        "-",
    ]


def _safe_process_environment() -> dict[str, str]:
    return {
        "PATH": "/usr/bin:/bin",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "HOME": "/nonexistent",
    }


async def _terminate_process_group(process: asyncio.subprocess.Process) -> None:
    if process.returncode is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        await asyncio.wait_for(process.wait(), timeout=0.5)
        return
    except TimeoutError:
        pass
    with suppress(ProcessLookupError):
        os.killpg(process.pid, signal.SIGKILL)
    await process.wait()


async def _read_process_stream(
    stream: asyncio.StreamReader,
    *,
    limit: int,
    capture: bool,
) -> tuple[bytes, int]:
    output = bytearray()
    total = 0
    while True:
        chunk = await stream.read(min(64 * 1024, limit + 1))
        if not chunk:
            break
        total += len(chunk)
        if total > limit:
            raise ProcessOutputLimitError()
        if capture:
            output.extend(chunk)
    return bytes(output), total


async def run_bounded_process(
    argv: Sequence[str],
    *,
    timeout_seconds: float,
    stdout_limit_bytes: int,
    stderr_limit_bytes: int,
    allowed_executables: Collection[str] = (
        "ffmpeg",
        "ffprobe",
        "/usr/bin/ffmpeg",
        "/usr/bin/ffprobe",
    ),
    cwd: str | Path | None = None,
) -> ProcessResult:
    if (
        not argv
        or not all(
            isinstance(argument, str) and argument and "\x00" not in argument for argument in argv
        )
        or argv[0] not in allowed_executables
        or timeout_seconds <= 0
        or stdout_limit_bytes < 0
        or stderr_limit_bytes < 0
    ):
        raise MediaPolicyError("dependency_unavailable")
    process_cwd: str | None = None
    if cwd is not None:
        work_directory = Path(cwd)
        if (
            not work_directory.is_absolute()
            or work_directory.is_symlink()
            or not work_directory.is_dir()
        ):
            raise MediaPolicyError("temporary_storage_unavailable")
        process_cwd = str(work_directory)

    try:
        process = await asyncio.create_subprocess_exec(
            *argv,
            cwd=process_cwd,
            env=_safe_process_environment(),
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            start_new_session=True,
        )
    except OSError as exc:
        raise MediaPolicyError("dependency_unavailable") from exc
    assert process.stdout is not None
    assert process.stderr is not None
    stdout_task = asyncio.create_task(
        _read_process_stream(process.stdout, limit=stdout_limit_bytes, capture=True)
    )
    stderr_task = asyncio.create_task(
        _read_process_stream(process.stderr, limit=stderr_limit_bytes, capture=False)
    )
    wait_task = asyncio.create_task(process.wait())
    tasks = (stdout_task, stderr_task, wait_task)
    try:
        async with asyncio.timeout(timeout_seconds):
            (stdout, _), (_, stderr_count), return_code = await asyncio.gather(*tasks)
    except TimeoutError:
        await _terminate_process_group(process)
        raise ProcessTimeoutError() from None
    except BaseException:
        await asyncio.shield(_terminate_process_group(process))
        raise
    finally:
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
    if return_code != 0:
        raise ProcessExecutionError(return_code=return_code, stderr_byte_count=stderr_count)
    return ProcessResult(
        return_code=return_code,
        stdout=stdout,
        stderr_byte_count=stderr_count,
    )


def hash_regular_file(path: str | Path, *, max_bytes: int = MAX_OUTPUT_BYTES) -> FileDigest:
    source = Path(path)
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        file_descriptor = os.open(source, flags)
    except OSError as exc:
        raise MediaPolicyError("generated_output_invalid") from exc
    digest = sha256()
    total = 0
    try:
        file_stat = os.fstat(file_descriptor)
        if (
            not stat.S_ISREG(file_stat.st_mode)
            or file_stat.st_size <= 0
            or file_stat.st_size > max_bytes
        ):
            raise MediaPolicyError("generated_output_invalid")
        while True:
            chunk = os.read(file_descriptor, COPY_CHUNK_BYTES)
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                raise MediaPolicyError("generated_output_invalid")
            digest.update(chunk)
        if total != file_stat.st_size:
            raise MediaPolicyError("generated_output_invalid")
        return FileDigest(byte_length=total, sha256_hex=digest.hexdigest())
    finally:
        os.close(file_descriptor)


def validate_probe_source_file(path: str | Path) -> int:
    """Verify local probe input without imposing a smaller accepted-source size limit."""

    source = Path(path)
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        file_descriptor = os.open(source, flags)
    except OSError as exc:
        raise MediaPolicyError("temporary_storage_unavailable") from exc
    try:
        file_stat = os.fstat(file_descriptor)
        if not stat.S_ISREG(file_stat.st_mode):
            raise MediaPolicyError("corrupt_source")
        if file_stat.st_size == 0:
            raise MediaPolicyError("empty_source")
        return file_stat.st_size
    finally:
        os.close(file_descriptor)


def copy_regular_file(
    source_path: str | Path,
    destination_path: str | Path,
    *,
    max_bytes: int = MAX_OUTPUT_BYTES,
) -> FileDigest:
    source = Path(source_path)
    destination = Path(destination_path)
    source_flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    destination_flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    source_descriptor = -1
    destination_descriptor = -1
    destination_created = False
    digest = sha256()
    total = 0
    try:
        source_descriptor = os.open(source, source_flags)
        source_stat = os.fstat(source_descriptor)
        if not stat.S_ISREG(source_stat.st_mode) or not 0 < source_stat.st_size <= max_bytes:
            raise MediaPolicyError("generated_output_invalid")
        destination_descriptor = os.open(destination, destination_flags, 0o600)
        destination_created = True
        while True:
            chunk = os.read(source_descriptor, COPY_CHUNK_BYTES)
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                raise MediaPolicyError("generated_output_invalid")
            digest.update(chunk)
            view = memoryview(chunk)
            while view:
                written = os.write(destination_descriptor, view)
                view = view[written:]
        os.fsync(destination_descriptor)
        if total != source_stat.st_size:
            raise MediaPolicyError("generated_output_invalid")
        return FileDigest(byte_length=total, sha256_hex=digest.hexdigest())
    except BaseException:
        if destination_created:
            with suppress(OSError):
                destination.unlink(missing_ok=True)
        raise
    finally:
        if destination_descriptor >= 0:
            os.close(destination_descriptor)
        if source_descriptor >= 0:
            os.close(source_descriptor)
