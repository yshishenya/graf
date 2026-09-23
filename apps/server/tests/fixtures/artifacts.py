from hashlib import sha256


def deterministic_wav_bytes(size: int = 1024) -> bytes:
    """Return exact-size transport bytes, not a decodable WAV.

    Range/checksum tests depend on these bytes, including sizes below a WAV
    header. Processing tests use deterministic_canonical_wav_bytes instead.
    """
    return (b"2brain-rec-test-audio" * ((size // 21) + 1))[:size]


def track_descriptor(
    track_role: str,
    size: int = 1024,
    *,
    data: bytes | None = None,
    duration_seconds: int = 60,
) -> dict[str, object]:
    """Describe canonical transport roles; payload overrides bind exact hashes."""
    codec, sample_rate_hz, channel_count = {
        "manifest": ("json", 1, 1),
        "media": ("wav-pcm-s16le", 16_000, 1),
        "playback": ("m4a-aac-lc", 48_000, 1),
    }[track_role]
    data = deterministic_wav_bytes(size) if data is None else data
    return {
        "track_role": track_role,
        "codec": codec,
        "sample_rate_hz": sample_rate_hz,
        "channel_count": channel_count,
        "duration_seconds": duration_seconds,
        "byte_length": len(data),
        "sha256": sha256(data).hexdigest(),
    }
