from hashlib import sha256


def deterministic_wav_bytes(size: int = 1024) -> bytes:
    return (b"2brain-rec-test-audio" * ((size // 21) + 1))[:size]


def track_descriptor(track_role: str, size: int = 1024) -> dict[str, object]:
    data = deterministic_wav_bytes(size)
    return {
        "track_role": track_role,
        "codec": "pcm_s16le",
        "sample_rate_hz": 48_000,
        "channel_count": 1,
        "duration_seconds": 60,
        "byte_length": len(data),
        "sha256": sha256(data).hexdigest(),
    }
