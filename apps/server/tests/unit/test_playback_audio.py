from __future__ import annotations

import io
import wave


def _wav_bytes(samples: list[int], *, sample_rate: int = 16_000) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(b"".join(sample.to_bytes(2, "little", signed=True) for sample in samples))
    return buffer.getvalue()


def _samples(body: bytes) -> list[int]:
    with wave.open(io.BytesIO(body), "rb") as wav:
        frames = wav.readframes(wav.getnframes())
    return [int.from_bytes(frames[index : index + 2], "little", signed=True) for index in range(0, len(frames), 2)]


def test_combined_review_wav_represents_microphone_and_incoming_sources() -> None:
    from twobrain_rec_server.cabinet.playback_audio import build_combined_review_wav

    mic = _wav_bytes([1000, 1000, 0, 0])
    incoming = _wav_bytes([0, 0, 2000, 2000])

    result = build_combined_review_wav(
        [
            ("local_microphone", mic),
            ("incoming_system", incoming),
        ]
    )

    assert result.source_mode == "combined_review_stream"
    assert result.included_sources == ["local_microphone", "incoming_system"]
    assert result.media_type == "audio/wav"
    assert result.duration_seconds == 0
    assert _samples(result.body) == [1000, 1000, 2000, 2000]


def test_combined_review_wav_rejects_incompatible_sources() -> None:
    from twobrain_rec_server.cabinet.playback_audio import (
        ReviewAudioBuildError,
        build_combined_review_wav,
    )

    mic = _wav_bytes([1000, 1000], sample_rate=16_000)
    incoming = _wav_bytes([2000, 2000], sample_rate=48_000)

    try:
        build_combined_review_wav(
            [
                ("local_microphone", mic),
                ("incoming_system", incoming),
            ]
        )
    except ReviewAudioBuildError as exc:
        assert exc.reason == "incompatible_audio"
    else:
        raise AssertionError("incompatible sources must fail closed")
