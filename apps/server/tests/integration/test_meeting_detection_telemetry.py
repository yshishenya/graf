from __future__ import annotations

import asyncio
from copy import deepcopy

from sqlalchemy import select

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.contract.test_meeting_detection_api_contract import meeting_detection_payload
from twobrain_rec_server.db.models import (
    MeetingDetectionCandidate,
    MeetingDetectionTargetHealthRollup,
    MeetingDetectionTelemetryBatch,
    MeetingDetectionTelemetryRateLimitBucket,
)

TELEMETRY_PATH = "/api/v1/desktop/meeting-detection/telemetry"


def _post(client, key: str, payload: dict[str, object]):
    return client.post(
        TELEMETRY_PATH,
        headers=auth_headers() | {"Idempotency-Key": key},
        json=payload,
    )


def test_valid_telemetry_persists_batch_health_and_candidate(client) -> None:
    response = _post(client, "meeting-detection:valid-001", meeting_detection_payload())

    async def load_counts() -> tuple[int, int, int, str | None]:
        async with client.app_state["sessionmaker"]() as db:
            batch_count = len((await db.scalars(select(MeetingDetectionTelemetryBatch))).all())
            health_count = len((await db.scalars(select(MeetingDetectionTargetHealthRollup))).all())
            candidates = (await db.scalars(select(MeetingDetectionCandidate))).all()
            return batch_count, health_count, len(candidates), candidates[0].bundle_id if candidates else None

    batch_count, health_count, candidate_count, bundle_id = asyncio.run(load_counts())

    assert response.status_code == 201
    assert response.json()["accepted_target_rollup_count"] == 1
    assert response.json()["accepted_candidate_count"] == 1
    assert batch_count == 1
    assert health_count == 1
    assert candidate_count == 1
    assert bundle_id == "ru.example.vks"


def test_old_sensor_signal_telemetry_is_rejected(client) -> None:
    payload = meeting_detection_payload()
    payload["targetRollups"][0]["signalFamilies"] = ["macos_sensor_indicators_mic"]

    response = _post(client, "meeting-detection:old-signal-001", payload)

    assert response.status_code == 422
    assert response.json()["code"] == "request_validation_error"


def test_same_idempotency_key_and_payload_returns_duplicate_without_second_batch(client) -> None:
    payload = meeting_detection_payload()
    first = _post(client, "meeting-detection:dupe-001", payload)
    second = _post(client, "meeting-detection:dupe-001", payload)

    async def load_batch_count() -> int:
        async with client.app_state["sessionmaker"]() as db:
            return len((await db.scalars(select(MeetingDetectionTelemetryBatch))).all())

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["dedupe_status"] == "duplicate"
    assert asyncio.run(load_batch_count()) == 1


def test_same_idempotency_key_with_different_payload_conflicts(client) -> None:
    payload = meeting_detection_payload()
    changed = deepcopy(payload)
    changed["registryVersion"] = "2026.07.08.2"

    first = _post(client, "meeting-detection:conflict-001", payload)
    second = _post(client, "meeting-detection:conflict-001", changed)

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["code"] == "meeting_detection_telemetry_idempotency_conflict"


def test_server_candidate_upload_below_score_threshold_is_rejected(client) -> None:
    payload = meeting_detection_payload()
    payload["unknownNativeAppRollups"][0]["candidateScore"] = 3

    response = _post(client, "meeting-detection:low-score-001", payload)

    assert response.status_code == 422
    assert response.json()["code"] == "meeting_detection_telemetry_schema_invalid"


def test_daily_rate_limit_blocks_second_new_upload_and_persists_bucket(client) -> None:
    first = _post(client, "meeting-detection:rate-001", meeting_detection_payload())
    second = _post(client, "meeting-detection:rate-002", meeting_detection_payload(registryVersion="2026.07.08.2"))

    async def load_bucket() -> MeetingDetectionTelemetryRateLimitBucket:
        async with client.app_state["sessionmaker"]() as db:
            return await db.scalar(select(MeetingDetectionTelemetryRateLimitBucket))

    bucket = asyncio.run(load_bucket())

    assert first.status_code == 201
    assert second.status_code == 429
    assert second.json()["code"] == "meeting_detection_telemetry_rate_limited"
    assert bucket.attempt_count == 2
    assert bucket.blocked_until is not None
