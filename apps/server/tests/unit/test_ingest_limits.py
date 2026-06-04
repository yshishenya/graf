import pytest
from twobrain_rec_server.config import Settings
from twobrain_rec_server.ingest.policy import (
    IngestLimitViolation,
    validate_recording_duration,
    validate_track_bytes,
)


def settings() -> Settings:
    return Settings(max_recording_duration_seconds=60, max_track_bytes=100)


def test_duration_at_limit_is_accepted() -> None:
    validate_recording_duration(settings(), 60)


def test_duration_over_limit_is_rejected() -> None:
    with pytest.raises(IngestLimitViolation) as exc:
        validate_recording_duration(settings(), 61)
    assert exc.value.code == "recording_duration_exceeded"


def test_track_bytes_over_limit_is_rejected() -> None:
    with pytest.raises(IngestLimitViolation) as exc:
        validate_track_bytes(settings(), 101)
    assert exc.value.code == "track_bytes_exceeded"
