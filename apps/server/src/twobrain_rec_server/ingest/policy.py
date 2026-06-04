from dataclasses import dataclass

from twobrain_rec_server.config import Settings


@dataclass(frozen=True, slots=True)
class IngestLimitViolation(Exception):
    code: str
    limit_name: str
    limit_value: int
    actual_value: int


def validate_recording_duration(settings: Settings, duration_seconds: int) -> None:
    if duration_seconds > settings.max_recording_duration_seconds:
        raise IngestLimitViolation(
            code="recording_duration_exceeded",
            limit_name="max_recording_duration_seconds",
            limit_value=settings.max_recording_duration_seconds,
            actual_value=duration_seconds,
        )


def validate_track_bytes(settings: Settings, byte_length: int) -> None:
    if byte_length > settings.max_track_bytes:
        raise IngestLimitViolation(
            code="track_bytes_exceeded",
            limit_name="max_track_bytes",
            limit_value=settings.max_track_bytes,
            actual_value=byte_length,
        )
