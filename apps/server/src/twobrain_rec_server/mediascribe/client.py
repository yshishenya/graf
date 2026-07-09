from __future__ import annotations

from dataclasses import dataclass
from typing import Any, BinaryIO

import httpx
from pydantic import ValidationError

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
        try:
            api_key = settings.mediascribe_api_key_file.read_text(encoding="utf-8").strip()
        except OSError as exc:
            raise MediaScribeClientError("blocked_config", retryable=False) from exc
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
        mic_file: BinaryIO,
        incoming_file: BinaryIO,
        diarize: bool,
        summarize: bool,
    ) -> MediaScribeSubmitResponse:
        payload = {"diarize": str(diarize).lower(), "summarize": str(summarize).lower()}
        files = {
            "mic_file": ("microphone.wav", mic_file, "application/octet-stream"),
            "incoming_file": ("incoming.wav", incoming_file, "application/octet-stream"),
        }
        data = await self._request_json(
            "POST",
            "/v1/audio/transcriptions/dual-track",
            data=payload,
            files=files,
        )
        external_job_id = str(data.get("id") or data.get("job_id") or "")
        if not external_job_id:
            raise _malformed_response_error()
        try:
            status = MediaScribeJobStatus(str(data.get("status") or MediaScribeJobStatus.UPLOADED.value))
            return MediaScribeSubmitResponse(external_job_id=external_job_id, status=status)
        except (ValueError, ValidationError) as exc:
            raise _malformed_response_error() from exc

    async def poll_job(self, external_job_id: str) -> MediaScribePollResponse:
        data = await self._request_json("GET", f"/jobs/{external_job_id}")
        try:
            status = MediaScribeJobStatus(str(data.get("status") or MediaScribeJobStatus.UPLOADED.value))
        except ValueError as exc:
            raise _malformed_response_error() from exc
        return MediaScribePollResponse(external_job_id=external_job_id, status=status)

    async def fetch_result(self, external_job_id: str) -> MediaScribeResult:
        data = await self._request_json("GET", f"/jobs/{external_job_id}/result")
        try:
            return MediaScribeResult.model_validate(_normalize_result_payload(data, external_job_id=external_job_id))
        except ValidationError as exc:
            raise _malformed_response_error() from exc

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


def _malformed_response_error() -> MediaScribeClientError:
    return MediaScribeClientError("mediascribe_malformed_response", retryable=True)


def _normalize_result_payload(data: dict[str, Any], *, external_job_id: str) -> dict[str, Any]:
    job = data.get("job")
    if not isinstance(job, dict):
        job = {}
    return {
        "external_job_id": data.get("external_job_id") or data.get("id") or job.get("id") or external_job_id,
        "language": data.get("language") or job.get("language"),
        "transcript": [_normalize_transcript_segment(index, item) for index, item in enumerate(_list_payload(data.get("transcript")))],
        "diarization": [_normalize_diarization_segment(index, item) for index, item in enumerate(_list_payload(data.get("diarization")))],
        "summary_status": data.get("summary_status") or ("available" if data.get("summary") else "not_requested"),
        "result_version": data.get("result_version") or 1,
    }


def _list_payload(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _normalize_transcript_segment(sequence: int, item: dict[str, Any]) -> dict[str, Any]:
    source_role = item.get("source_role")
    return {
        "sequence": item.get("sequence", sequence),
        "start_seconds": item.get("start_seconds", item.get("start", 0)),
        "end_seconds": item.get("end_seconds", item.get("end", 0)),
        "text": item.get("text") or "",
        "source_role": source_role or item.get("role") or "incoming",
        "source_role_original": item.get("source_role_original") or source_role,
    }


def _normalize_diarization_segment(sequence: int, item: dict[str, Any]) -> dict[str, Any]:
    normalized = _normalize_transcript_segment(sequence, item)
    normalized["speaker_label"] = item.get("speaker_label") or item.get("speaker") or f"SPEAKER_{sequence:02d}"
    return normalized
