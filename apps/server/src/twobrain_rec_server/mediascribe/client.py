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
    def __init__(
        self,
        reason_code: str,
        *,
        retryable: bool,
        status_code: int | None = None,
        egress_state: str = "not_sent",
    ) -> None:
        super().__init__(reason_code)
        self.reason_code = reason_code
        self.retryable = retryable
        self.status_code = status_code
        self.egress_state = egress_state


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
        idempotency_key: str | None = None,
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
            idempotency_key=idempotency_key,
        )
        external_job_id = str(data.get("id") or data.get("job_id") or "")
        if not external_job_id:
            raise _malformed_response_error()
        try:
            status = MediaScribeJobStatus(
                str(data.get("status") or MediaScribeJobStatus.UPLOADED.value)
            )
            return MediaScribeSubmitResponse(external_job_id=external_job_id, status=status)
        except (ValueError, ValidationError) as exc:
            raise _malformed_response_error() from exc

    async def submit_single_track(
        self,
        *,
        media_file: BinaryIO,
        diarize: bool,
        summarize: bool,
        media_content_type: str | None = None,
        media_filename: str | None = None,
        idempotency_key: str | None = None,
    ) -> MediaScribeSubmitResponse:
        payload = {"diarize": str(diarize).lower(), "summarize": str(summarize).lower()}
        media_type = _safe_media_content_type(media_content_type, _read_media_probe(media_file))
        files = {
            "file": (
                _safe_media_filename(media_type, preferred_filename=media_filename),
                media_file,
                media_type,
            )
        }
        data = await self._request_json(
            "POST",
            "/v1/audio/transcriptions",
            data=payload,
            files=files,
            idempotency_key=idempotency_key,
        )
        external_job_id = str(data.get("id") or data.get("job_id") or "")
        if not external_job_id:
            raise _malformed_response_error()
        try:
            status = MediaScribeJobStatus(
                str(data.get("status") or MediaScribeJobStatus.UPLOADED.value)
            )
            return MediaScribeSubmitResponse(external_job_id=external_job_id, status=status)
        except (ValueError, ValidationError) as exc:
            raise _malformed_response_error() from exc

    async def poll_job(self, external_job_id: str) -> MediaScribePollResponse:
        data = await self._request_json("GET", f"/jobs/{external_job_id}")
        job = data.get("job")
        if not isinstance(job, dict):
            job = {}
        raw_status = data.get("status") or job.get("status")
        if not isinstance(raw_status, str) or not raw_status:
            raise _malformed_response_error(egress_state="not_sent")
        reported_job_id = data.get("id") or data.get("job_id") or job.get("id")
        if reported_job_id is not None and str(reported_job_id) != external_job_id:
            raise _malformed_response_error(egress_state="not_sent")
        try:
            status = MediaScribeJobStatus(raw_status)
        except ValueError as exc:
            raise _malformed_response_error(egress_state="not_sent") from exc
        error_code = data.get("error_code") or job.get("error_code")
        error_origin = data.get("error_origin") or job.get("error_origin")
        reason_code = data.get("reason_code") or job.get("reason_code") or error_code
        return MediaScribePollResponse(
            external_job_id=external_job_id,
            status=status,
            reason_code=str(reason_code) if reason_code else None,
            error_code=str(error_code) if error_code else None,
            error_origin=str(error_origin) if error_origin else None,
        )

    async def fetch_result(self, external_job_id: str) -> MediaScribeResult:
        data = await self._request_json("GET", f"/jobs/{external_job_id}/result")
        try:
            return MediaScribeResult.model_validate(
                _normalize_result_payload(data, external_job_id=external_job_id)
            )
        except ValidationError as exc:
            raise _malformed_response_error() from exc

    async def _request_json(
        self,
        method: str,
        path: str,
        *,
        idempotency_key: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        timeout = httpx.Timeout(self.timeout_seconds)
        headers = {"X-API-Key": self.api_key}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
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
            raise MediaScribeClientError(
                classification.reason_code,
                retryable=True,
                egress_state="unknown",
            ) from exc
        except httpx.RequestError as exc:
            classification = classify_mediascribe_error(None)
            raise MediaScribeClientError(
                classification.reason_code,
                retryable=True,
                egress_state="unknown",
            ) from exc
        if response.status_code >= 400:
            classification = classify_mediascribe_error(response.status_code)
            raise MediaScribeClientError(
                classification.reason_code,
                retryable=classification.retryable,
                status_code=response.status_code,
                egress_state=(
                    "response_received"
                    if response.status_code in {408, 429} or response.status_code >= 500
                    else "not_sent"
                ),
            )
        try:
            data = response.json()
        except ValueError as exc:
            raise MediaScribeClientError(
                "mediascribe_malformed_response",
                retryable=True,
                egress_state="unknown" if method == "POST" else "not_sent",
            ) from exc
        if not isinstance(data, dict):
            raise MediaScribeClientError(
                "mediascribe_malformed_response",
                retryable=True,
                egress_state="unknown" if method == "POST" else "not_sent",
            )
        return data


def _malformed_response_error(*, egress_state: str = "unknown") -> MediaScribeClientError:
    return MediaScribeClientError(
        "mediascribe_malformed_response",
        retryable=True,
        egress_state=egress_state,
    )


_MEDIA_TYPE_EXTENSION_BY_CONTENT_TYPE = {
    "audio/wav": "wav",
    "audio/x-wav": "wav",
    "audio/wave": "wav",
    "audio/mpeg": "mp3",
    "audio/mp3": "mp3",
    "audio/mp4": "m4a",
    "audio/x-m4a": "m4a",
    "audio/m4a": "m4a",
    "audio/aac": "aac",
    "audio/webm": "webm",
    "audio/ogg": "ogg",
    "audio/flac": "flac",
    "video/mp4": "mp4",
    "video/quicktime": "mov",
    "video/webm": "webm",
}


def _read_media_probe(media_file: BinaryIO, max_bytes: int = 64) -> bytes:
    try:
        position = media_file.tell()
    except OSError:
        position = None
    probe = media_file.read(max_bytes)
    if position is not None:
        media_file.seek(position)
    return probe


def _safe_media_content_type(content_type: str | None, media_bytes: bytes) -> str:
    if content_type:
        normalized = content_type.split(";", 1)[0].strip().lower()
        if normalized and normalized != "application/octet-stream":
            if normalized in {"audio/x-m4a", "audio/m4a"}:
                return "audio/mp4"
            return normalized
    return _infer_media_content_type(media_bytes)


def _infer_media_content_type(media_bytes: bytes) -> str:
    if media_bytes.startswith(b"RIFF") and media_bytes[8:12] == b"WAVE":
        return "audio/wav"
    if media_bytes.startswith(b"ID3") or (
        len(media_bytes) >= 2 and media_bytes[0] == 0xFF and media_bytes[1] & 0xE0 == 0xE0
    ):
        return "audio/mpeg"
    if media_bytes.startswith(b"OggS"):
        return "audio/ogg"
    if media_bytes.startswith(b"fLaC"):
        return "audio/flac"
    if media_bytes.startswith(b"\x1a\x45\xdf\xa3"):
        return "audio/webm"
    if len(media_bytes) >= 12 and media_bytes[4:8] == b"ftyp":
        brand = media_bytes[8:12]
        if brand in {b"M4A ", b"M4B ", b"mp41"}:
            return "audio/mp4"
        if brand == b"qt  ":
            return "video/quicktime"
        return "video/mp4"
    return "application/octet-stream"


def _safe_media_filename(content_type: str, *, preferred_filename: str | None = None) -> str:
    # A v5 caller may use this fixed, non-user-derived name. Any other
    # preferred name is ignored so client-controlled local paths never become
    # provider-facing multipart metadata.
    if content_type == "audio/wav" and preferred_filename == "meeting-transcription.wav":
        return preferred_filename
    extension = _MEDIA_TYPE_EXTENSION_BY_CONTENT_TYPE.get(content_type, "bin")
    return f"manual-media.{extension}"


def _normalize_result_payload(data: dict[str, Any], *, external_job_id: str) -> dict[str, Any]:
    job = data.get("job")
    if not isinstance(job, dict):
        job = {}
    if not any(
        key in data
        for key in (
            "job",
            "id",
            "job_id",
            "external_job_id",
            "transcript_status",
            "transcript",
            "diarization",
            "summary_status",
            "summary",
        )
    ):
        raise _malformed_response_error(egress_state="not_sent")
    reported_job_id = (
        data.get("external_job_id") or data.get("id") or data.get("job_id") or job.get("id")
    )
    if reported_job_id is not None and str(reported_job_id) != external_job_id:
        raise _malformed_response_error(egress_state="not_sent")
    transcript_payload = _list_payload(data.get("transcript"))
    diarization_payload = _list_payload(data.get("diarization"))
    transcript_status = data.get("transcript_status")
    if transcript_status is None:
        if transcript_payload:
            transcript_status = "available"
        elif diarization_payload:
            transcript_status = "unavailable"
        else:
            raise _malformed_response_error(egress_state="not_sent")
    transcript_reason = data.get("transcript_reason")
    if transcript_status == "available" and not transcript_payload:
        raise _malformed_response_error(egress_state="not_sent")
    if transcript_status == "unavailable":
        if transcript_payload:
            raise _malformed_response_error(egress_state="not_sent")
        if diarization_payload:
            if transcript_reason is not None:
                raise _malformed_response_error(egress_state="not_sent")
        elif transcript_reason != "no_recognizable_speech":
            raise _malformed_response_error(egress_state="not_sent")
    normalized_transcript = (
        [
            _normalize_transcript_segment(index, item)
            for index, item in enumerate(transcript_payload)
        ]
        if transcript_status == "available"
        else []
    )
    return {
        "external_job_id": external_job_id,
        "language": data.get("language") or job.get("language"),
        "transcript_status": transcript_status,
        "transcript_reason": transcript_reason,
        "failure_reason": transcript_reason if transcript_status == "unavailable" else None,
        "transcript": normalized_transcript,
        "diarization": [
            _normalize_diarization_segment(index, item)
            for index, item in enumerate(diarization_payload)
        ],
        "summary_status": data.get("summary_status")
        or ("available" if data.get("summary") else "not_requested"),
        "result_version": data.get("result_version") or 1,
        "provider_result_version": data.get("speaker_result_version")
        or data.get("provider_result_version")
        or data.get("result_version"),
        "provider_build_version": data.get("build_version") or job.get("build_version"),
        "provider_model_version": data.get("model_version") or job.get("model_version"),
        "alignment_version": data.get("alignment_version") or job.get("alignment_version"),
    }


def _list_payload(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise _malformed_response_error(egress_state="not_sent")
    if any(not isinstance(item, dict) for item in value):
        raise _malformed_response_error(egress_state="not_sent")
    for item in value:
        _validate_segment_payload(item)
    return value


def _validate_segment_payload(item: dict[str, Any]) -> None:
    if not {"start", "start_seconds"}.intersection(item) or not {
        "end",
        "end_seconds",
    }.intersection(item):
        raise _malformed_response_error(egress_state="not_sent")
    if not isinstance(item.get("text"), str) or not item.get("text", "").strip():
        raise _malformed_response_error(egress_state="not_sent")


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
    speaker_label = item.get("speaker_label")
    if speaker_label is None:
        speaker_label = item.get("speaker")
    normalized["speaker_label"] = "" if speaker_label is None else speaker_label
    return normalized
