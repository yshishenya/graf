"""Deterministic, content-free MediaScribe v1 transport fixtures."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import httpx


@dataclass
class MediaScribeV1Fixture:
    """Small HTTP fixture covering the lifecycle states used by GRAF tests."""

    job_id: str = "job_fixture_v1"
    status: str = "ready"
    queue_state: str = "completed"
    provider_attempt: int | None = None
    provider_max_attempts: int | None = None
    provider_next_retry_at: str | None = None
    error_code: str | None = None
    retry_after: str | None = None
    replayed: bool = False
    deletion_status: str = "completed"
    calls: list[tuple[str, str]] = field(default_factory=list)
    submissions: list[str] = field(default_factory=list)

    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self)

    async def __call__(self, request: httpx.Request) -> httpx.Response:
        self.calls.append((request.method, request.url.path))
        headers = {"X-Request-ID": "fixture-request-1", "X-MediaScribe-API-Version": "v1"}
        if self.retry_after is not None:
            headers["Retry-After"] = self.retry_after

        if request.method == "POST" and request.url.path in {
            "/v1/audio/transcriptions",
            "/v1/audio/transcriptions/dual-track",
        }:
            key = request.headers.get("Idempotency-Key", "fixture-key")
            if key not in self.submissions:
                self.submissions.append(key)
            headers["Idempotency-Replayed"] = "true" if self.replayed else "false"
            return httpx.Response(
                200,
                headers=headers,
                json={"id": self.job_id, "status": "uploaded", "api_contract_version": "v1"},
            )
        if request.method == "GET" and request.url.path == "/v1/capabilities":
            return httpx.Response(
                200,
                headers=headers,
                json={
                    "api_contract_version": "v1",
                    "supported_media_extensions": ["wav"],
                    "dual_track_supported": True,
                    "max_active_jobs_global": 4,
                    "max_active_jobs_per_user": 2,
                    "max_job_attempts": 3,
                    "max_speaker_count_hint": 8,
                    "max_upload_size_bytes_per_file": 536870912,
                    "queue_dispatch_max_attempts": 3,
                    "queue_dispatch_max_backoff_seconds": 60,
                    "cancellation_grace_seconds": 60,
                    "summary_available": True,
                    "speaker_count_modes": ["exact", "max"],
                },
            )
        if request.method == "GET" and request.url.path == f"/v1/audio/transcriptions/{self.job_id}":
            return httpx.Response(
                200,
                headers=headers,
                json={
                    "id": self.job_id,
                    "status": self.status,
                    "queue_state": self.queue_state,
                    "provider_attempt": self.provider_attempt,
                    "provider_max_attempts": self.provider_max_attempts,
                    "next_retry_at": self.provider_next_retry_at,
                    "error": {"code": self.error_code} if self.error_code else None,
                },
            )
        if request.method == "GET" and request.url.path == f"/v1/audio/transcriptions/{self.job_id}/result":
            return httpx.Response(
                200,
                headers=headers,
                json={
                    "job": {"id": self.job_id, "status": "ready"},
                    "transcript_status": "available",
                    "transcript": [{"start": 0, "end": 1, "text": "fixture", "source_role": "mic"}],
                    "diarization": [{
                        "start": 0,
                        "end": 1,
                        "text": "fixture",
                        "speaker": "SPEAKER_00",
                        "words": [{"word": "fixture", "start": 0, "end": 1, "probability": 0.99}],
                    }],
                    "summary": {"status": "running"},
                    "downloads": {},
                },
            )
        if request.method == "DELETE" and request.url.path == f"/v1/audio/transcriptions/{self.job_id}":
            return httpx.Response(
                202,
                headers=headers,
                json={
                    "id": "receipt_fixture",
                    "state": self.deletion_status,
                    "deleted": self.deletion_status == "completed",
                    "requested_at": "2026-08-24T00:00:00Z",
                    "status_url": f"/v1/audio/transcriptions/{self.job_id}/deletion",
                },
            )
        if request.method == "GET" and request.url.path == f"/v1/audio/transcriptions/{self.job_id}/deletion":
            return httpx.Response(
                200,
                headers=headers,
                json={
                    "id": "receipt_fixture",
                    "state": self.deletion_status,
                    "deleted": self.deletion_status == "completed",
                    "requested_at": "2026-08-24T00:00:00Z",
                    "status_url": f"/v1/audio/transcriptions/{self.job_id}/deletion",
                },
            )
        return httpx.Response(404, headers=headers, json={"code": "fixture_not_found"})


def opaque_result_payload(job_id: str = "job_fixture_v1") -> dict[str, Any]:
    """Return a reusable result with no private meeting content."""

    return {
        "job": {"id": job_id, "status": "ready"},
        "transcript_status": "available",
        "transcript": [{"start": 0, "end": 1, "text": "fixture", "source_role": "mic"}],
        "diarization": [{
            "start": 0,
            "end": 1,
            "text": "fixture",
            "speaker": "SPEAKER_00",
            "words": [{"word": "fixture", "start": 0, "end": 1, "probability": 0.99}],
        }],
        "summary": {"status": "running"},
        "downloads": {},
    }
