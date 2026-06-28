from __future__ import annotations

import io
import wave
from dataclasses import dataclass
from typing import Literal

from twobrain_rec_server.api.schemas import SourceRoleView


@dataclass(frozen=True, slots=True)
class ReviewAudio:
    body: bytes
    media_type: str
    duration_seconds: int
    source_mode: Literal["combined_review_stream", "stored_review_m4a"]
    included_sources: list[SourceRoleView]


class ReviewAudioBuildError(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True, slots=True)
class _DecodedWav:
    source: SourceRoleView
    sample_rate: int
    channels: int
    sample_width: int
    frames: bytes
    frame_count: int


def build_combined_review_wav(sources: list[tuple[SourceRoleView, bytes]]) -> ReviewAudio:
    decoded = [_decode_wav(source, body) for source, body in sources]
    if len(decoded) < 2:
        raise ReviewAudioBuildError("missing_audio_source")

    first = decoded[0]
    if first.sample_width != 2:
        raise ReviewAudioBuildError("unsupported_audio")
    if any(
        item.sample_rate != first.sample_rate
        or item.channels != first.channels
        or item.sample_width != first.sample_width
        for item in decoded[1:]
    ):
        raise ReviewAudioBuildError("incompatible_audio")

    sample_lists = [_pcm16_samples(item.frames) for item in decoded]
    max_samples = max(len(samples) for samples in sample_lists)
    mixed = []
    for index in range(max_samples):
        value = 0
        for samples in sample_lists:
            if index < len(samples):
                value += samples[index]
        mixed.append(_clip_pcm16(value))

    body = _encode_wav(mixed, sample_rate=first.sample_rate, channels=first.channels)
    frame_count = max(item.frame_count for item in decoded)
    return ReviewAudio(
        body=body,
        media_type="audio/wav",
        duration_seconds=int(frame_count / first.sample_rate),
        source_mode="combined_review_stream",
        included_sources=[item.source for item in decoded],
    )


def _decode_wav(source: SourceRoleView, body: bytes) -> _DecodedWav:
    try:
        with wave.open(io.BytesIO(body), "rb") as wav:
            channels = wav.getnchannels()
            sample_width = wav.getsampwidth()
            sample_rate = wav.getframerate()
            frame_count = wav.getnframes()
            frames = wav.readframes(frame_count)
    except (EOFError, wave.Error) as exc:
        raise ReviewAudioBuildError("unsupported_audio") from exc
    if channels <= 0 or sample_rate <= 0 or sample_width <= 0:
        raise ReviewAudioBuildError("unsupported_audio")
    return _DecodedWav(
        source=source,
        sample_rate=sample_rate,
        channels=channels,
        sample_width=sample_width,
        frames=frames,
        frame_count=frame_count,
    )


def _pcm16_samples(frames: bytes) -> list[int]:
    return [int.from_bytes(frames[index : index + 2], "little", signed=True) for index in range(0, len(frames), 2)]


def _encode_wav(samples: list[int], *, sample_rate: int, channels: int) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(b"".join(sample.to_bytes(2, "little", signed=True) for sample in samples))
    return buffer.getvalue()


def _clip_pcm16(value: int) -> int:
    return max(-32768, min(32767, value))
