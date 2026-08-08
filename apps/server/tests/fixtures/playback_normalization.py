from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
from struct import pack
from typing import Any

CANONICAL_PROFILE = "review_m4a_aac_lc_48k_mono_64k_v1"


@dataclass(frozen=True, slots=True)
class SyntheticAudioStream:
    index: int = 0
    codec_name: str = "aac"
    profile: str = "LC"
    sample_rate: int = 48_000
    channels: int = 1
    bit_rate: int = 64_000
    duration_seconds: float = 60.0
    default: bool = True

    def as_probe_stream(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "codec_type": "audio",
            "codec_name": self.codec_name,
            "profile": self.profile,
            "sample_rate": str(self.sample_rate),
            "channels": self.channels,
            "bit_rate": str(self.bit_rate),
            "duration": f"{self.duration_seconds:.6f}",
            "start_time": "0.000000",
            "disposition": {"default": 1 if self.default else 0},
        }


def synthetic_probe_payload(
    *streams: SyntheticAudioStream,
    format_name: str = "mov,mp4,m4a,3gp,3g2,mj2",
    duration_seconds: float = 60.0,
    byte_length: int = 512_000,
    include_video: bool = False,
) -> dict[str, Any]:
    selected_streams: list[dict[str, Any]] = [stream.as_probe_stream() for stream in streams]
    if include_video:
        selected_streams.insert(
            0,
            {
                "index": 0,
                "codec_type": "video",
                "codec_name": "h264",
                "duration": f"{duration_seconds:.6f}",
                "disposition": {"default": 1},
            },
        )
    return {
        "streams": selected_streams,
        "format": {
            "format_name": format_name,
            "duration": f"{duration_seconds:.6f}",
            "size": str(byte_length),
        },
        "chapters": [],
    }


def synthetic_pcm_wav_bytes(
    *,
    duration_milliseconds: int = 100,
    sample_rate: int = 16_000,
    channels: int = 1,
) -> bytes:
    """Generate deterministic PCM silence in memory; no media fixture is committed."""

    sample_width = 2
    frame_count = sample_rate * duration_milliseconds // 1_000
    data_length = frame_count * channels * sample_width
    byte_rate = sample_rate * channels * sample_width
    block_align = channels * sample_width

    output = BytesIO()
    output.write(b"RIFF")
    output.write(pack("<I", 36 + data_length))
    output.write(b"WAVEfmt ")
    output.write(pack("<IHHIIHH", 16, 1, channels, sample_rate, byte_rate, block_align, 16))
    output.write(b"data")
    output.write(pack("<I", data_length))
    output.write(b"\x00" * data_length)
    return output.getvalue()


def synthetic_source_receipt(*, role: str = "media", byte_length: int = 1024) -> dict[str, Any]:
    digest = sha256(f"synthetic:{role}:{byte_length}".encode()).hexdigest()
    return {
        "track_role": role,
        "byte_length": byte_length,
        "sha256": digest,
        "status": "stored",
    }


def synthetic_job_values(
    *,
    state: str = "queued",
    source_kind: str = "manual_upload",
) -> dict[str, Any]:
    return {
        "profile_version": CANONICAL_PROFILE,
        "state": state,
        "source_kind": source_kind,
        "attempt_count": 0,
        "cycle_attempt_count": 0,
        "retry_cycle_count": 0,
        "reason_code": None,
    }


def synthetic_backfill_values(*, state: str = "inventory_pending") -> dict[str, Any]:
    return {
        "profile_version": CANONICAL_PROFILE,
        "state": state,
        "evaluated_count": 0,
        "ready_count": 0,
        "terminal_count": 0,
        "cancelled_count": 0,
    }
