from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any, BinaryIO
from urllib.parse import quote, unquote, urlsplit, urlunsplit

import httpx
from pydantic import ValidationError

from twobrain_rec_server.config import Settings
from twobrain_rec_server.domain.statuses import ProcessingAvailabilityStatus, SummaryStatus
from twobrain_rec_server.mediascribe.schemas import (
    MediaScribeCapabilitiesResponse,
    MediaScribeDeletionResponse,
    MediaScribeDownloadResponse,
    MediaScribeJobListResponse,
    MediaScribeJobResponse,
    MediaScribePollResponse,
    MediaScribeProblemDetails,
    MediaScribeProviderQueueState,
    MediaScribeProviderStatus,
    MediaScribeResponseHeaders,
    MediaScribeResult,
    MediaScribeSubmitResponse,
    MediaScribeSummaryResponse,
    MediaScribeVersionResponse,
)
from twobrain_rec_server.processing.lifecycle import classify_mediascribe_error

_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
_SAFE_PROVIDER_VALUE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_IDEMPOTENCY_KEY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/+-]{0,255}$")
_SAFE_ID_MAX_LENGTH = 256
_SAFE_MACHINE_VALUE_MAX_LENGTH = 128
_V1_TRANSCRIPTIONS_PATH = "/v1/audio/transcriptions"
_V1_API_VERSION = "v1"
_DOWNLOAD_ARTIFACTS = frozenset({"archive", "diarization", "summary", "transcript"})
_RETRYABLE_CONFLICT_CODES = frozenset({"result_not_ready", "summary_not_ready"})


class MediaScribeClientError(RuntimeError):
    """Safe adapter error with machine-readable provider evidence."""

    def __init__(
        self,
        reason_code: str,
        *,
        retryable: bool,
        status_code: int | None = None,
        egress_state: str = "not_sent",
        problem: MediaScribeProblemDetails | None = None,
        headers: MediaScribeResponseHeaders | None = None,
        retry_after_seconds: int | None = None,
        request_id: str | None = None,
        job_id: str | None = None,
        error_origin: str | None = None,
    ) -> None:
        # Do not put provider detail, request bodies, credentials or signed
        # URLs into the exception string. Callers can use the safe fields below.
        super().__init__(reason_code)
        self.reason_code = reason_code
        self.retryable = retryable
        self.status_code = status_code
        self.http_status = status_code
        self.egress_state = egress_state
        self.problem = problem
        self.headers = headers or MediaScribeResponseHeaders(status_code=status_code)
        self.retry_after_seconds = retry_after_seconds
        self.request_id = request_id
        self.job_id = job_id
        self.error_origin = error_origin
        self.error_code = (
            problem.code if problem is not None and problem.code is not None else reason_code
        )
        self.errors = problem.errors if problem is not None else None
        self.detail = problem.detail if problem is not None else None


@dataclass(frozen=True, slots=True)
class _MediaScribeHttpResponse:
    status_code: int
    headers: MediaScribeResponseHeaders
    json_payload: dict[str, Any] | None
    content: bytes


@dataclass(frozen=True, slots=True)
class MediaScribeClient:
    base_url: str
    api_key: str
    timeout_seconds: int = 30
    transport: httpx.AsyncBaseTransport | None = None
    shared_http_client: httpx.AsyncClient | None = field(
        default=None,
        repr=False,
        compare=False,
    )

    @classmethod
    def from_settings(
        cls,
        settings: Settings,
        *,
        reuse_connections: bool = False,
    ) -> MediaScribeClient:
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
        base_url = str(settings.mediascribe_base_url).rstrip("/")
        timeout_seconds = settings.mediascribe_request_timeout_seconds
        return cls(
            base_url=base_url,
            api_key=api_key,
            timeout_seconds=timeout_seconds,
            shared_http_client=(
                httpx.AsyncClient(
                    base_url=base_url,
                    timeout=httpx.Timeout(timeout_seconds),
                    headers={"X-API-Key": api_key},
                )
                if reuse_connections
                else None
            ),
        )

    async def aclose(self) -> None:
        if self.shared_http_client is not None:
            await self.shared_http_client.aclose()

    async def submit_dual_track(
        self,
        *,
        mic_file: BinaryIO,
        incoming_file: BinaryIO,
        diarize: bool,
        summarize: bool,
        num_speakers: int | None = None,
        speaker_count_mode: str | None = None,
        idempotency_key: str | None = None,
        request_id: str | None = None,
    ) -> MediaScribeSubmitResponse:
        payload = _upload_form_fields(
            diarize=diarize,
            summarize=summarize,
            num_speakers=num_speakers,
            speaker_count_mode=speaker_count_mode,
        )
        files = {
            "mic_file": ("microphone.wav", mic_file, "audio/wav"),
            "incoming_file": ("incoming.wav", incoming_file, "audio/wav"),
        }
        response = await self._request_json(
            "POST",
            f"{_V1_TRANSCRIPTIONS_PATH}/dual-track",
            data=payload,
            files=files,
            idempotency_key=idempotency_key,
            request_id=request_id,
        )
        return _parse_submit_response(response)

    async def submit_single_track(
        self,
        *,
        media_file: BinaryIO,
        diarize: bool,
        summarize: bool,
        num_speakers: int | None = None,
        speaker_count_mode: str | None = None,
        media_content_type: str | None = None,
        media_filename: str | None = None,
        idempotency_key: str | None = None,
        request_id: str | None = None,
    ) -> MediaScribeSubmitResponse:
        payload = _upload_form_fields(
            diarize=diarize,
            summarize=summarize,
            num_speakers=num_speakers,
            speaker_count_mode=speaker_count_mode,
        )
        media_type = _safe_media_content_type(media_content_type, _read_media_probe(media_file))
        files = {
            "file": (
                _safe_media_filename(media_type, preferred_filename=media_filename),
                media_file,
                media_type,
            )
        }
        response = await self._request_json(
            "POST",
            _V1_TRANSCRIPTIONS_PATH,
            data=payload,
            files=files,
            idempotency_key=idempotency_key,
            request_id=request_id,
        )
        return _parse_submit_response(response)

    async def get_capabilities(
        self, *, request_id: str | None = None
    ) -> MediaScribeCapabilitiesResponse:
        response = await self._request_json("GET", "/v1/capabilities", request_id=request_id)
        payload = _require_json_payload(response)
        _require_v1_contract_version(payload)
        try:
            return MediaScribeCapabilitiesResponse.model_validate(
                {
                    **payload,
                    "headers": response.headers,
                    "http_status": response.status_code,
                }
            )
        except ValidationError as exc:
            raise _malformed_response_error(
                status_code=response.status_code,
                headers=response.headers,
                egress_state="not_sent",
            ) from exc

    async def get_version(self, *, request_id: str | None = None) -> MediaScribeVersionResponse:
        response = await self._request_json("GET", "/version", request_id=request_id)
        payload = _require_json_payload(response)
        _require_v1_contract_version(payload)
        try:
            return MediaScribeVersionResponse.model_validate(
                {
                    **payload,
                    "headers": response.headers,
                    "http_status": response.status_code,
                }
            )
        except ValidationError as exc:
            raise _malformed_response_error(
                status_code=response.status_code,
                headers=response.headers,
                egress_state="not_sent",
            ) from exc

    async def get_job(
        self, external_job_id: str, *, request_id: str | None = None
    ) -> MediaScribeJobResponse:
        response = await self._request_json(
            "GET",
            _job_path(external_job_id),
            request_id=request_id,
            _provider_job_id=external_job_id,
        )
        payload = _require_json_payload(response)
        job_payload = _job_payload_for_response(payload, external_job_id=external_job_id)
        try:
            return MediaScribeJobResponse.model_validate(
                {
                    **job_payload,
                    "headers": response.headers,
                    "http_status": response.status_code,
                }
            )
        except ValidationError as exc:
            raise _malformed_response_error(
                status_code=response.status_code,
                headers=response.headers,
                egress_state="not_sent",
            ) from exc

    async def poll_job(
        self, external_job_id: str, *, request_id: str | None = None
    ) -> MediaScribePollResponse:
        response = await self._request_json(
            "GET",
            _job_path(external_job_id),
            request_id=request_id,
            _provider_job_id=external_job_id,
        )
        payload = _require_json_payload(response)
        job_id, raw_status, raw_queue_state, job = _extract_job_state(
            payload,
            expected_job_id=external_job_id,
        )
        raw_status = raw_status or response.headers.job_status
        raw_queue_state = raw_queue_state or response.headers.queue_state
        status = _provider_status(raw_status)
        queue_state = _provider_queue_state(raw_queue_state)
        error_code = _safe_machine_value(job.get("error_code"))
        error_origin = _safe_machine_value(job.get("error_origin"))
        reason_code = _safe_machine_value(job.get("reason_code")) or error_code
        return MediaScribePollResponse(
            external_job_id=job_id,
            status=status,
            queue_state=queue_state,
            status_raw=status.value,
            queue_state_raw=queue_state.value if queue_state is not None else None,
            status_projection=status.safe_value,
            queue_state_projection=queue_state.safe_value if queue_state is not None else None,
            reason_code=reason_code,
            error_code=error_code,
            error_origin=error_origin,
            attempt=_safe_int(job.get("attempt"), default=0),
            max_attempts=_safe_int(job.get("max_attempts"), default=3),
            retry_after_seconds=(
                response.headers.retry_after_seconds
                if response.headers.retry_after_seconds is not None
                else _safe_nonnegative_int(job.get("retry_after_seconds"))
            ),
            next_retry_at=_safe_text(job.get("next_retry_at")),
            result_available=bool(job.get("result_available", False)),
            request_id=response.headers.request_id,
            headers=response.headers,
            http_status=response.status_code,
        )

    async def fetch_result(
        self, external_job_id: str, *, request_id: str | None = None
    ) -> MediaScribeResult:
        response = await self._request_json(
            "GET",
            f"{_job_path(external_job_id)}/result",
            request_id=request_id,
            _provider_job_id=external_job_id,
        )
        payload = _require_json_payload(response)
        try:
            result = MediaScribeResult.model_validate(
                {
                    **_normalize_result_payload(payload, external_job_id=external_job_id),
                    "request_id": response.headers.request_id,
                    "headers": response.headers,
                    "http_status": response.status_code,
                }
            )
            return result
        except MediaScribeClientError:
            raise
        except ValidationError as exc:
            raise _malformed_response_error(
                status_code=response.status_code,
                headers=response.headers,
                egress_state="not_sent",
            ) from exc

    async def get_summary(
        self,
        external_job_id: str,
        *,
        request_id: str | None = None,
    ) -> MediaScribeSummaryResponse:
        response = await self._request_json(
            "GET",
            f"{_job_path(external_job_id)}/summary",
            request_id=request_id,
            _provider_job_id=external_job_id,
        )
        payload = _require_json_payload(response)
        summary_payload = (
            payload.get("summary") if isinstance(payload.get("summary"), dict) else payload
        )
        try:
            return MediaScribeSummaryResponse.model_validate(
                {
                    **summary_payload,
                    "headers": response.headers,
                    "http_status": response.status_code,
                }
            )
        except ValidationError as exc:
            raise _malformed_response_error(
                status_code=response.status_code,
                headers=response.headers,
                egress_state="not_sent",
            ) from exc

    async def list_jobs(
        self,
        *,
        q: str | None = None,
        status: str | None = None,
        diarization: str | None = None,
        sort: str | None = None,
        page: int = 1,
        page_size: int = 20,
        cursor: str | None = None,
        request_id: str | None = None,
    ) -> MediaScribeJobListResponse:
        if cursor is not None and any(
            value is not None for value in (q, status, diarization, sort)
        ):
            raise MediaScribeClientError("invalid_cursor_filters", retryable=False)
        if cursor is not None and page != 1:
            raise MediaScribeClientError("invalid_cursor_page", retryable=False)
        params: dict[str, Any] = {
            "page": 1 if cursor is not None else page,
            "page_size": page_size,
        }
        for name, value in (
            ("q", q),
            ("status", status),
            ("diarization", diarization),
            ("sort", sort),
            ("cursor", cursor),
        ):
            if value is not None:
                params[name] = value
        response = await self._request_json(
            "GET",
            _V1_TRANSCRIPTIONS_PATH,
            params=params,
            request_id=request_id,
        )
        payload = _require_json_payload(response)
        try:
            return MediaScribeJobListResponse.model_validate(
                {
                    **payload,
                    "headers": response.headers,
                    "http_status": response.status_code,
                }
            )
        except ValidationError as exc:
            raise _malformed_response_error(
                status_code=response.status_code,
                headers=response.headers,
                egress_state="not_sent",
            ) from exc

    async def delete_job(
        self,
        external_job_id: str,
        *,
        request_id: str | None = None,
    ) -> MediaScribeDeletionResponse:
        response = await self._request_json(
            "DELETE",
            _job_path(external_job_id),
            request_id=request_id,
            _provider_job_id=external_job_id,
        )
        return _parse_deletion_response(response)

    async def get_deletion(
        self,
        external_job_id: str,
        *,
        request_id: str | None = None,
    ) -> MediaScribeDeletionResponse:
        response = await self._request_json(
            "GET",
            f"{_job_path(external_job_id)}/deletion",
            request_id=request_id,
            _provider_job_id=external_job_id,
        )
        return _parse_deletion_response(response)

    async def download(
        self,
        download_url: str,
        *,
        request_id: str | None = None,
    ) -> MediaScribeDownloadResponse:
        path = _resolve_download_path(self.base_url, download_url)
        response = await self._request_bytes("GET", path, request_id=request_id)
        return MediaScribeDownloadResponse(
            content=response.content,
            content_type=response.headers.raw_headers.get("Content-Type"),
            content_disposition=response.headers.raw_headers.get("Content-Disposition"),
            request_id=response.headers.request_id,
            headers=response.headers,
            http_status=response.status_code,
        )

    async def _request_json(
        self,
        method: str,
        path: str,
        *,
        idempotency_key: str | None = None,
        request_id: str | None = None,
        _provider_job_id: str | None = None,
        **kwargs: Any,
    ) -> _MediaScribeHttpResponse:
        return await self._request(
            method,
            path,
            idempotency_key=idempotency_key,
            request_id=request_id,
            _provider_job_id=_provider_job_id,
            expect_json=True,
            **kwargs,
        )

    async def _request_bytes(
        self,
        method: str,
        path: str,
        *,
        idempotency_key: str | None = None,
        request_id: str | None = None,
        _provider_job_id: str | None = None,
        **kwargs: Any,
    ) -> _MediaScribeHttpResponse:
        return await self._request(
            method,
            path,
            idempotency_key=idempotency_key,
            request_id=request_id,
            _provider_job_id=_provider_job_id,
            expect_json=False,
            **kwargs,
        )

    async def _request(
        self,
        method: str,
        path: str,
        *,
        idempotency_key: str | None = None,
        request_id: str | None = None,
        _provider_job_id: str | None = None,
        expect_json: bool,
        **kwargs: Any,
    ) -> _MediaScribeHttpResponse:
        if request_id is not None and not _REQUEST_ID_RE.fullmatch(request_id):
            raise MediaScribeClientError("invalid_request_id", retryable=False)
        if idempotency_key is not None and not _IDEMPOTENCY_KEY_RE.fullmatch(idempotency_key):
            raise MediaScribeClientError("invalid_idempotency_key", retryable=False)
        timeout = httpx.Timeout(self.timeout_seconds)
        headers = {"X-API-Key": self.api_key}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        if request_id:
            headers["X-Request-ID"] = request_id
        try:
            if self.shared_http_client is not None:
                response = await self.shared_http_client.request(
                    method,
                    path,
                    headers=headers,
                    **kwargs,
                )
            else:
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
                job_id=_provider_job_id,
            ) from exc
        except httpx.RequestError as exc:
            classification = classify_mediascribe_error(None)
            raise MediaScribeClientError(
                classification.reason_code,
                retryable=True,
                egress_state="unknown",
                job_id=_provider_job_id,
            ) from exc

        response_headers = _response_headers(response)
        if response_headers.api_version not in {None, _V1_API_VERSION}:
            raise MediaScribeClientError(
                "mediascribe_api_version_mismatch",
                retryable=False,
                status_code=response.status_code,
                egress_state="response_received",
                headers=response_headers,
                request_id=response_headers.request_id,
            )
        if response.status_code >= 400:
            raise _error_from_response(
                response,
                response_headers,
                method=method,
                fallback_job_id=_provider_job_id,
            )

        payload: dict[str, Any] | None = None
        if expect_json:
            try:
                decoded = response.json()
            except ValueError as exc:
                raise _malformed_response_error(
                    status_code=response.status_code,
                    headers=response_headers,
                    egress_state="unknown" if method == "POST" else "not_sent",
                    job_id=_provider_job_id,
                ) from exc
            if not isinstance(decoded, dict):
                raise _malformed_response_error(
                    status_code=response.status_code,
                    headers=response_headers,
                    egress_state="unknown" if method == "POST" else "not_sent",
                    job_id=_provider_job_id,
                )
            payload = decoded
        return _MediaScribeHttpResponse(
            status_code=response.status_code,
            headers=response_headers,
            json_payload=payload,
            content=response.content,
        )


def _upload_form_fields(
    *,
    diarize: bool,
    summarize: bool,
    num_speakers: int | None,
    speaker_count_mode: str | None,
) -> dict[str, str]:
    fields = {"diarize": str(diarize).lower(), "summarize": str(summarize).lower()}
    if num_speakers is not None:
        fields["num_speakers"] = str(num_speakers)
    if speaker_count_mode is not None:
        fields["speaker_count_mode"] = speaker_count_mode
    return fields


def _parse_submit_response(response: _MediaScribeHttpResponse) -> MediaScribeSubmitResponse:
    data = _require_json_payload(response)
    job_id, raw_status, raw_queue_state, job = _extract_job_state(data, egress_state="unknown")
    raw_status = raw_status or response.headers.job_status
    raw_queue_state = raw_queue_state or response.headers.queue_state
    status = _provider_status(raw_status, default=MediaScribeProviderStatus.UPLOADED.value)
    queue_state = _provider_queue_state(raw_queue_state)
    return MediaScribeSubmitResponse(
        external_job_id=job_id,
        status=status,
        queue_state=queue_state,
        status_raw=status.value,
        queue_state_raw=queue_state.value if queue_state is not None else None,
        status_projection=status.safe_value,
        queue_state_projection=queue_state.safe_value if queue_state is not None else None,
        attempt=_safe_int(job.get("attempt"), default=0),
        max_attempts=_safe_int(job.get("max_attempts"), default=3),
        retry_after_seconds=response.headers.retry_after_seconds
        if response.headers.retry_after_seconds is not None
        else _safe_nonnegative_int(job.get("retry_after_seconds")),
        next_retry_at=_safe_text(job.get("next_retry_at")),
        result_available=bool(job.get("result_available", False)),
        idempotency_replayed=(
            response.headers.idempotency_replayed
            if response.headers.idempotency_replayed is not None
            else bool(job.get("idempotency_replayed", False))
        ),
        location=response.headers.location or _safe_text(job.get("retrieve_url")),
        result_url=_safe_text(job.get("result_url")),
        deletion_url=_safe_text(job.get("deletion_url")),
        request_id=response.headers.request_id,
        api_contract_version=_safe_text(data.get("api_contract_version")),
        egress_state="accepted",
        headers=response.headers,
        http_status=response.status_code,
    )


def _parse_deletion_response(response: _MediaScribeHttpResponse) -> MediaScribeDeletionResponse:
    payload = _require_json_payload(response)
    normalized = dict(payload)
    if normalized.get("status_url") is None and response.headers.location is not None:
        normalized["status_url"] = response.headers.location
    if normalized.get("retry_after_seconds") is None:
        normalized["retry_after_seconds"] = response.headers.retry_after_seconds
    try:
        return MediaScribeDeletionResponse.model_validate(
            {
                **normalized,
                "headers": response.headers,
                "http_status": response.status_code,
            }
        )
    except ValidationError as exc:
        raise _malformed_response_error(
            status_code=response.status_code,
            headers=response.headers,
            egress_state="not_sent",
        ) from exc


def _extract_job_state(
    data: dict[str, Any],
    *,
    expected_job_id: str | None = None,
    egress_state: str = "not_sent",
) -> tuple[str, str | None, str | None, dict[str, Any]]:
    nested = data.get("job")
    nested_job = nested if isinstance(nested, dict) else {}
    job = {**nested_job, **{key: value for key, value in data.items() if key != "job"}}
    reported_job_id = (
        data.get("id") or data.get("job_id") or data.get("external_job_id") or nested_job.get("id")
    )
    if reported_job_id is None:
        reported_job_id = expected_job_id
    if not isinstance(reported_job_id, str) or not _bounded_id_is_valid(reported_job_id):
        raise _malformed_response_error(egress_state=egress_state)
    if expected_job_id is not None and reported_job_id != expected_job_id:
        raise _malformed_response_error(egress_state=egress_state)
    raw_status = data.get("status") or nested_job.get("status")
    if raw_status is not None and not isinstance(raw_status, str):
        raise _malformed_response_error(egress_state="not_sent")
    raw_status = _safe_provider_token(raw_status)
    raw_queue_state = data.get("queue_state") or nested_job.get("queue_state")
    if raw_queue_state is not None and not isinstance(raw_queue_state, str):
        raise _malformed_response_error(egress_state="not_sent")
    raw_queue_state = _safe_provider_token(raw_queue_state)
    return reported_job_id, raw_status, raw_queue_state, job


def _job_payload_for_response(data: dict[str, Any], *, external_job_id: str) -> dict[str, Any]:
    job_id, raw_status, raw_queue_state, job = _extract_job_state(
        data, expected_job_id=external_job_id
    )
    normalized = dict(job)
    normalized["id"] = job_id
    if raw_status is not None:
        normalized["status"] = raw_status
    if raw_queue_state is not None:
        normalized["queue_state"] = raw_queue_state
    return normalized


def _normalize_result_payload(data: dict[str, Any], *, external_job_id: str) -> dict[str, Any]:
    if (
        not isinstance(data.get("job"), dict)
        or "transcript" not in data
        or "transcript_status" not in data
        or not isinstance(data.get("downloads"), dict)
    ):
        raise _malformed_response_error(egress_state="not_sent")

    job_id, raw_status, raw_queue_state, job = _extract_job_state(
        data, expected_job_id=external_job_id
    )
    normalized_job = dict(job)
    normalized_job["id"] = job_id
    normalized_job.setdefault("status", raw_status or MediaScribeProviderStatus.UPLOADED.value)
    if raw_queue_state is not None:
        normalized_job["queue_state"] = raw_queue_state
    default_source_role = (
        "unknown_provider_state" if normalized_job.get("source_mode") == "dual" else "mixed"
    )

    transcript_payload = _list_payload(data.get("transcript"), field_name="transcript")
    transcript_status = data.get("transcript_status")
    if transcript_status is None:
        raise _malformed_response_error(egress_state="not_sent")
    if transcript_status not in {
        ProcessingAvailabilityStatus.AVAILABLE.value,
        ProcessingAvailabilityStatus.UNAVAILABLE.value,
    }:
        raise _malformed_response_error(egress_state="not_sent")
    transcript_reason = data.get("transcript_reason")
    if transcript_reason is not None and transcript_reason != "no_recognizable_speech":
        raise _malformed_response_error(egress_state="not_sent")
    if transcript_status == ProcessingAvailabilityStatus.AVAILABLE.value and not transcript_payload:
        raise _malformed_response_error(egress_state="not_sent")
    if transcript_status == ProcessingAvailabilityStatus.UNAVAILABLE.value and (
        transcript_payload
        or (transcript_reason != "no_recognizable_speech" and not data.get("diarization"))
    ):
        raise _malformed_response_error(egress_state="not_sent")

    diarization_value = data.get("diarization")
    diarization_payload = (
        None
        if diarization_value is None and "diarization" in data
        else _list_payload(diarization_value, field_name="diarization")
    )
    normalized_diarization = (
        None
        if diarization_payload is None
        else [
            _normalize_diarization_segment(
                index,
                item,
                default_source_role=default_source_role,
            )
            for index, item in enumerate(diarization_payload)
        ]
    )
    acoustic_turns = _list_payload(
        data.get("acoustic_speaker_turns"), field_name="acoustic_speaker_turns"
    )
    overlaps = _list_payload(data.get("overlaps"), field_name="overlaps")
    summary_payload = data.get("summary")
    summary_status = _summary_status_for_payload(summary_payload)

    normalized = dict(data)
    normalized.update(
        {
            "external_job_id": external_job_id,
            "job": normalized_job,
            "transcript_status": transcript_status,
            "transcript_reason": transcript_reason,
            "failure_reason": transcript_reason if transcript_status == "unavailable" else None,
            "transcript": (
                [
                    _normalize_transcript_segment(
                        index,
                        item,
                        default_source_role=default_source_role,
                    )
                    for index, item in enumerate(transcript_payload)
                ]
                if transcript_status == ProcessingAvailabilityStatus.AVAILABLE.value
                else []
            ),
            "diarization": normalized_diarization,
            "acoustic_speaker_turns": acoustic_turns,
            "overlaps": overlaps,
            "summary_status": summary_status,
            "result_version": data.get("result_version") or 1,
        }
    )
    return normalized


def _summary_status_for_payload(summary_payload: Any) -> SummaryStatus:
    raw_status = summary_payload.get("status") if isinstance(summary_payload, dict) else None
    return {
        "available": SummaryStatus.AVAILABLE,
        "ready": SummaryStatus.AVAILABLE,
        "failed": SummaryStatus.FAILED,
        "running": SummaryStatus.UNAVAILABLE,
        "queued": SummaryStatus.UNAVAILABLE,
        "unavailable": SummaryStatus.UNAVAILABLE,
        "not_requested": SummaryStatus.NOT_REQUESTED,
        None: SummaryStatus.NOT_REQUESTED,
    }.get(raw_status, SummaryStatus.UNAVAILABLE)


def _list_payload(value: Any, *, field_name: str) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise _malformed_response_error(egress_state="not_sent")
    for item in value:
        if field_name in {"transcript", "diarization"}:
            _validate_segment_payload(item, field_name=field_name)
        elif field_name in {"acoustic_speaker_turns", "overlaps"}:
            _validate_interval_payload(item)
    if field_name in {"transcript", "diarization", "acoustic_speaker_turns", "overlaps"}:
        _validate_chronological_order(value)
    return value


def _validate_segment_payload(item: dict[str, Any], *, field_name: str) -> None:
    start = item.get("start_seconds", item.get("start"))
    end = item.get("end_seconds", item.get("end"))
    if (
        not _valid_number(start)
        or not _valid_number(end)
        or float(start) < 0
        or float(end) <= float(start)
    ):
        raise _malformed_response_error(egress_state="not_sent")
    if not isinstance(item.get("text"), str) or not item.get("text", "").strip():
        raise _malformed_response_error(egress_state="not_sent")


def _validate_interval_payload(item: dict[str, Any]) -> None:
    start = item.get("start")
    end = item.get("end")
    if (
        not _valid_number(start)
        or not _valid_number(end)
        or float(start) < 0
        or float(end) <= float(start)
    ):
        raise _malformed_response_error(egress_state="not_sent")


def _validate_chronological_order(items: list[dict[str, Any]]) -> None:
    previous_start: float | None = None
    for item in items:
        start = item.get("start_seconds", item.get("start"))
        if start is None:
            raise _malformed_response_error(egress_state="not_sent")
        current_start = float(start)
        if previous_start is not None and current_start < previous_start:
            raise _malformed_response_error(egress_state="not_sent")
        previous_start = current_start


def _normalize_transcript_segment(
    sequence: int,
    item: dict[str, Any],
    *,
    default_source_role: str = "mixed",
) -> dict[str, Any]:
    source_role = item.get("source_role")
    normalized = dict(item)
    normalized.update(
        {
            "sequence": item.get("sequence", sequence),
            "start_seconds": item.get("start_seconds", item.get("start", 0)),
            "end_seconds": item.get("end_seconds", item.get("end", 0)),
            "text": item.get("text") or "",
            "source_role": _safe_provider_token(
                source_role or item.get("role") or default_source_role
            ),
            "source_role_original": item.get("source_role_original") or source_role,
        }
    )
    return normalized


def _normalize_diarization_segment(
    sequence: int,
    item: dict[str, Any],
    *,
    default_source_role: str = "mixed",
) -> dict[str, Any]:
    normalized = _normalize_transcript_segment(
        sequence,
        item,
        default_source_role=default_source_role,
    )
    normalized["speaker_label"] = (
        _safe_provider_token(item.get("speaker_label") or item.get("speaker")) or ""
    )
    if "words" in item:
        normalized["words"] = item["words"]
    return normalized


def _provider_status(
    raw_value: str | None, *, default: str | None = None
) -> MediaScribeProviderStatus:
    value = raw_value if raw_value is not None else default
    if value is None:
        raise _malformed_response_error(egress_state="not_sent")
    try:
        return MediaScribeProviderStatus(_safe_provider_token(value) or "unknown_provider_state")
    except ValueError as exc:
        raise _malformed_response_error(egress_state="not_sent") from exc


def _provider_queue_state(raw_value: str | None) -> MediaScribeProviderQueueState | None:
    if raw_value is None:
        return None
    try:
        return MediaScribeProviderQueueState(
            _safe_provider_token(raw_value) or "unknown_provider_state"
        )
    except ValueError as exc:
        raise _malformed_response_error(egress_state="not_sent") from exc


def _require_json_payload(response: _MediaScribeHttpResponse) -> dict[str, Any]:
    if response.json_payload is None:
        raise _malformed_response_error(
            status_code=response.status_code,
            headers=response.headers,
            egress_state="not_sent",
        )
    return response.json_payload


def _require_v1_contract_version(payload: dict[str, Any]) -> None:
    version = payload.get("api_contract_version")
    if version is not None and version != _V1_API_VERSION:
        raise MediaScribeClientError("mediascribe_api_version_mismatch", retryable=False)


def _error_from_response(
    response: httpx.Response,
    headers: MediaScribeResponseHeaders,
    *,
    method: str,
    fallback_job_id: str | None = None,
) -> MediaScribeClientError:
    problem = _parse_problem_details(response)
    classification = classify_mediascribe_error(response.status_code)
    provider_retryable = (
        problem.retryable
        if problem is not None and problem.retryable is not None
        else headers.error_retryable
        if headers.error_retryable is not None
        else None
    )
    reason_code = (
        _safe_machine_value(problem.code)
        if problem is not None and problem.code is not None
        else headers.error_code
        if headers.error_code is not None
        else classification.reason_code
    )
    if response.status_code == 409:
        # 409 is overloaded by the v1 contract: only explicit not-ready
        # machine codes are safe to retry. Unknown or terminal conflicts must
        # fail closed even if a proxy/provider omitted the Problem Details.
        retryable = (
            reason_code in _RETRYABLE_CONFLICT_CODES
            and provider_retryable is not False
        )
    else:
        retryable = classification.retryable and provider_retryable is not False
    request_id = headers.request_id or (problem.request_id if problem is not None else None)
    job_id = (
        problem.job_id if problem is not None and problem.job_id is not None else fallback_job_id
    )
    error_origin = (
        problem.error_origin
        if problem is not None and problem.error_origin is not None
        else headers.error_origin
    )
    if request_id is not None and headers.request_id is None:
        headers = headers.model_copy(update={"request_id": request_id})
    egress_state = (
        "unknown"
        if method.upper() == "POST" and response.status_code in {408, 502, 503, 504}
        else "response_received"
    )
    return MediaScribeClientError(
        reason_code,
        retryable=retryable,
        status_code=response.status_code,
        egress_state=egress_state,
        problem=problem,
        headers=headers,
        retry_after_seconds=headers.retry_after_seconds,
        request_id=request_id,
        job_id=job_id,
        error_origin=error_origin,
    )


def _parse_problem_details(response: httpx.Response) -> MediaScribeProblemDetails | None:
    try:
        decoded = response.json()
    except ValueError:
        return None
    if not isinstance(decoded, dict):
        return None
    candidate: dict[str, Any] = {
        "status": decoded.get("status") if isinstance(decoded.get("status"), int) else None,
        "code": _safe_machine_value(decoded.get("code")),
        "retryable": decoded.get("retryable")
        if isinstance(decoded.get("retryable"), bool)
        else None,
        "request_id": _safe_request_id(decoded.get("request_id")),
        "job_id": _safe_opaque_id(decoded.get("job_id")),
        "error_origin": _safe_machine_value(decoded.get("error_origin")),
        # ``detail`` and arbitrary validation values are intentionally not
        # copied into the safe DTO. ``errors`` keeps only bounded machine
        # fields for server-side classification/support.
        "errors": _safe_problem_errors(decoded.get("errors")),
    }
    try:
        return MediaScribeProblemDetails.model_validate(candidate)
    except ValidationError:
        return None


def _response_headers(response: httpx.Response) -> MediaScribeResponseHeaders:
    retry_after = _parse_nonnegative_header(response.headers.get("Retry-After"))
    idempotency_replayed = _parse_bool_header(response.headers.get("Idempotency-Replayed"))
    job_deleted = _parse_bool_header(response.headers.get("X-Job-Deleted"))
    request_id = _safe_request_id(response.headers.get("X-Request-ID"))
    location = _safe_provider_location(response.headers.get("Location"))
    job_status = _safe_provider_token(response.headers.get("X-Job-Status"))
    queue_state = _safe_provider_token(response.headers.get("X-Queue-State"))
    error_code = _safe_machine_value(
        response.headers.get("X-Job-Error-Code") or response.headers.get("X-Error-Code")
    )
    error_origin = _safe_machine_value(response.headers.get("X-Job-Error-Origin"))
    error_retryable = _parse_bool_header(
        response.headers.get("X-Job-Retryable") or response.headers.get("X-Error-Retryable")
    )
    raw_headers: dict[str, str] = {}
    for header_name in (
        "Location",
        "Retry-After",
        "Idempotency-Replayed",
        "X-Request-ID",
        "X-MediaScribe-API-Version",
        "X-Job-Status",
        "X-Queue-State",
        "X-Job-Deleted",
        "X-Job-Error-Code",
        "X-Job-Error-Origin",
        "X-Job-Retryable",
        "X-Error-Code",
        "X-Error-Retryable",
        "Content-Type",
    ):
        value = response.headers.get(header_name)
        safe_value = _safe_header_value(value)
        if safe_value is not None:
            raw_headers[header_name] = safe_value
    return MediaScribeResponseHeaders(
        status_code=response.status_code,
        location=location,
        retry_after_seconds=retry_after,
        idempotency_replayed=idempotency_replayed,
        request_id=request_id,
        api_version=_safe_provider_token(response.headers.get("X-MediaScribe-API-Version")),
        job_status=job_status,
        queue_state=queue_state,
        job_deleted=job_deleted,
        error_code=error_code,
        error_origin=error_origin,
        error_retryable=error_retryable,
        raw_headers=raw_headers,
    )


def _malformed_response_error(
    *,
    status_code: int | None = None,
    headers: MediaScribeResponseHeaders | None = None,
    egress_state: str = "unknown",
    job_id: str | None = None,
) -> MediaScribeClientError:
    return MediaScribeClientError(
        "mediascribe_malformed_response",
        retryable=True,
        status_code=status_code,
        egress_state=egress_state,
        headers=headers,
        retry_after_seconds=headers.retry_after_seconds if headers is not None else None,
        request_id=headers.request_id if headers is not None else None,
        job_id=job_id,
    )


def _job_path(external_job_id: str) -> str:
    if not _bounded_id_is_valid(external_job_id):
        raise MediaScribeClientError("invalid_job_id", retryable=False)
    return f"{_V1_TRANSCRIPTIONS_PATH}/{quote(external_job_id, safe='')}"


def _resolve_download_path(base_url: str, download_url: str) -> str:
    if not isinstance(download_url, str) or not download_url:
        raise MediaScribeClientError("invalid_download_url", retryable=False)
    parsed = urlsplit(download_url)
    if parsed.scheme or parsed.netloc:
        base = urlsplit(base_url)
        if (
            parsed.scheme.lower() != base.scheme.lower()
            or parsed.hostname != base.hostname
            or parsed.port != base.port
        ):
            raise MediaScribeClientError("invalid_download_url", retryable=False)
    if parsed.query or parsed.fragment or parsed.username or parsed.password:
        raise MediaScribeClientError("invalid_download_url", retryable=False)
    path = parsed.path if parsed.scheme or parsed.netloc else download_url
    if not path.startswith("/"):
        path = f"/{path}"
    decoded_parts = unquote(path).split("/")
    if (
        len(decoded_parts) != 7
        or decoded_parts[1:4] != ["v1", "audio", "transcriptions"]
        or decoded_parts[5] != "downloads"
        or decoded_parts[6] not in _DOWNLOAD_ARTIFACTS
        or not _bounded_id_is_valid(decoded_parts[4])
        or "." in decoded_parts
        or ".." in decoded_parts
    ):
        raise MediaScribeClientError("invalid_download_url", retryable=False)
    return urlunsplit(("", "", path, "", ""))


def _response_string(value: Any, *, max_length: int) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    if len(value) > max_length:
        return None
    return value


def _safe_text(value: Any) -> str | None:
    return _response_string(value, max_length=1024)


def _safe_machine_value(value: Any) -> str | None:
    candidate = _response_string(value, max_length=_SAFE_MACHINE_VALUE_MAX_LENGTH)
    return (
        candidate
        if candidate is not None and _SAFE_PROVIDER_VALUE_RE.fullmatch(candidate)
        else None
    )


def _safe_provider_token(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        return None
    if _SAFE_PROVIDER_VALUE_RE.fullmatch(value):
        return value
    return "unknown_provider_state"


def _safe_request_id(value: Any) -> str | None:
    if not isinstance(value, str) or not _REQUEST_ID_RE.fullmatch(value):
        return None
    return value


def _safe_opaque_id(value: Any) -> str | None:
    if not isinstance(value, str) or not value or len(value) > _SAFE_ID_MAX_LENGTH:
        return None
    if not _SAFE_PROVIDER_VALUE_RE.fullmatch(value):
        return None
    return value


def _safe_provider_location(value: Any) -> str | None:
    if not isinstance(value, str) or not value or len(value) > 1024:
        return None
    parsed = urlsplit(value)
    if (
        parsed.scheme
        or parsed.netloc
        or parsed.query
        or parsed.fragment
        or parsed.username
        or parsed.password
    ):
        return None
    path = parsed.path
    if not path.startswith("/v1/"):
        return None
    decoded_parts = unquote(path).split("/")
    if "." in decoded_parts or ".." in decoded_parts:
        return None
    return path


def _safe_header_value(value: Any) -> str | None:
    candidate = _response_string(value, max_length=256)
    if candidate is None or any(ord(char) < 32 or ord(char) == 127 for char in candidate):
        return None
    return candidate


def _safe_problem_errors(value: Any) -> list[dict[str, str]] | None:
    if not isinstance(value, list):
        return None
    safe_errors: list[dict[str, str]] = []
    for item in value[:16]:
        if not isinstance(item, dict):
            continue
        safe_item: dict[str, str] = {}
        for field_name in ("field", "code", "reason", "type"):
            safe_value = _safe_machine_value(item.get(field_name))
            if safe_value is not None:
                safe_item[field_name] = safe_value
        if safe_item:
            safe_errors.append(safe_item)
    return safe_errors or None


def _bounded_id_is_valid(value: Any) -> bool:
    return _safe_opaque_id(value) is not None


def _safe_int(value: Any, *, default: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return default
    return value


def _safe_nonnegative_int(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def _valid_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def _parse_nonnegative_header(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        try:
            target = parsedate_to_datetime(value)
        except (TypeError, ValueError, OverflowError):
            return None
        if target.tzinfo is None:
            target = target.replace(tzinfo=UTC)
        parsed = math.ceil((target.astimezone(UTC) - datetime.now(UTC)).total_seconds())
    return parsed if parsed >= 0 else None


def _parse_bool_header(value: str | None) -> bool | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    return None


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
        if normalized in _MEDIA_TYPE_EXTENSION_BY_CONTENT_TYPE:
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
    # Only the canonical server-owned name is accepted. Local paths and
    # meeting titles never become provider-facing multipart metadata.
    if content_type == "audio/wav" and preferred_filename == "meeting-transcription.wav":
        return preferred_filename
    extension = _MEDIA_TYPE_EXTENSION_BY_CONTENT_TYPE.get(content_type, "bin")
    return f"manual-media.{extension}"
