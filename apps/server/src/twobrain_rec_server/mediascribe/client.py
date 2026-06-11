from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from twobrain_rec_server.config import Settings
from twobrain_rec_server.domain.statuses import MediaScribeJobStatus
from twobrain_rec_server.mediascribe.schemas import (
    MediaScribePollResponse,
    MediaScribeResult,
    MediaScribeSubmitResponse,
)
from twobrain_rec_server.processing.lifecycle import classify_mediascribe_error


class MediaScribeClientError(RuntimeError):
    def __init__(self, reason_code: str, *, retryable: bool, status_code: int | None = None) -> None:
        super().__init__(reason_code)
        self.reason_code = reason_code
        self.retryable = retryable
        self.status_code = status_code


@dataclass(frozen=True, slots=True)
class MediaScribeClient:
    base_url: str
    api_key: str
    timeout_seconds: int = 30
    transport: httpx.AsyncBaseTransport | None = None

    @classmethod
    def from_settings(cls, settings: Settings) -> MediaScribeClient:
        if settings.mediascribe_base_url is None:
            raise MediaScribeClientError("blocked_config", retryable=False)
        if settings.mediascribe_api_key_file is None:
            raise MediaScribeClientError("blocked_config", retryable=False)
        api_key = settings.mediascribe_api_key_file.read_text(encoding="utf-8").strip()
        if not api_key:
            raise MediaScribeClientError("blocked_config", retryable=False)
        return cls(
            base_url=str(settings.mediascribe_base_url).rstrip("/"),
            api_key=api_key,
            timeout_seconds=settings.mediascribe_request_timeout_seconds,
        )

    async def submit_dual_track(
        self,
        *,
        mic_bytes: bytes,
        incoming_bytes: bytes,
        diarize: bool,
        summarize: bool,
    ) -> MediaScribeSubmitResponse:
        payload = {"diarize": str(diarize).lower(), "summarize": str(summarize).lower()}
        files = {
            "mic_file": ("microphone.wav", mic_bytes, "application/octet-stream"),
            "incoming_file": ("incoming.wav", incoming_bytes, "application/octet-stream"),
        }
        data = await self._request_json(
            "POST",
            "/v1/audio/transcriptions/dual-track",
            data=payload,
            files=files,
        )
        external_job_id = str(data.get("id") or data.get("job_id") or "")
        status = MediaScribeJobStatus(str(data.get("status") or MediaScribeJobStatus.UPLOADED.value))
        return MediaScribeSubmitResponse(external_job_id=external_job_id, status=status)

    async def poll_job(self, external_job_id: str) -> MediaScribePollResponse:
        data = await self._request_json("GET", f"/v1/audio/transcriptions/jobs/{external_job_id}")
        status = MediaScribeJobStatus(str(data.get("status") or MediaScribeJobStatus.UPLOADED.value))
        return MediaScribePollResponse(external_job_id=external_job_id, status=status)

    async def fetch_result(self, external_job_id: str) -> MediaScribeResult:
        data = await self._request_json("GET", f"/v1/audio/transcriptions/jobs/{external_job_id}/result")
        data.setdefault("external_job_id", external_job_id)
        return MediaScribeResult.model_validate(data)

    async def _request_json(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        timeout = httpx.Timeout(self.timeout_seconds)
        headers = {"X-API-Key": self.api_key}
        try:
            async with httpx.AsyncClient(
                base_url=self.base_url,
                timeout=timeout,
                headers=headers,
                transport=self.transport,
            ) as client:
                response = await client.request(method, path, **kwargs)
        except httpx.TimeoutException as exc:
            classification = classify_mediascribe_error(None, timeout=True)
            raise MediaScribeClientError(classification.reason_code, retryable=True) from exc
        except httpx.RequestError as exc:
            classification = classify_mediascribe_error(None)
            raise MediaScribeClientError(classification.reason_code, retryable=True) from exc
        if response.status_code >= 400:
            classification = classify_mediascribe_error(response.status_code)
            raise MediaScribeClientError(
                classification.reason_code,
                retryable=classification.retryable,
                status_code=response.status_code,
            )
        try:
            data = response.json()
        except ValueError as exc:
            raise MediaScribeClientError("mediascribe_malformed_response", retryable=True) from exc
        if not isinstance(data, dict):
            raise MediaScribeClientError("mediascribe_malformed_response", retryable=True)
        return data
