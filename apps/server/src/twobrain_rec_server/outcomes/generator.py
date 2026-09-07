from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from twobrain_rec_server.outcomes.models import (
    OutcomeTranscriptSegment,
)
from twobrain_rec_server.outcomes.prompts import (
    PROMPT_VARIABLE_RE,
    PromptSnapshot,
    canonical_json,
)


class LiteLLMError(RuntimeError):
    def __init__(
        self,
        code: str,
        *,
        retryable: bool,
        raw_response: object | None = None,
        egress_state: str = "response_received",
    ) -> None:
        super().__init__(code)
        self.code = code
        self.retryable = retryable
        self.raw_response = raw_response
        self.egress_state = egress_state


@dataclass(frozen=True, slots=True)
class LiteLLMGenerationResult:
    request: dict[str, object]
    raw_response: dict[str, object]
    parsed_content: object
    actual_model: str | None
    actual_provider: str | None
    provider_request_id: str | None
    token_usage: dict[str, object] | None
    cost_details: dict[str, object] | None


class LiteLLMGateway:
    """One zero-retry OpenAI-compatible call through the operator-owned proxy."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        timeout_seconds: int,
    ) -> None:
        self._url = f"{base_url.rstrip('/')}/chat/completions"
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    async def generate(
        self,
        *,
        snapshot: PromptSnapshot,
        messages: Sequence[Mapping[str, str]],
        idempotency_key: str | None = None,
    ) -> LiteLLMGenerationResult:
        import httpx

        request = snapshot.litellm_request(messages)
        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                headers = {
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                }
                if idempotency_key:
                    headers["Idempotency-Key"] = idempotency_key
                response = await client.post(
                    self._url,
                    headers=headers,
                    json=request,
                )
        except (httpx.ConnectTimeout, httpx.ConnectError, httpx.PoolTimeout) as exc:
            # These failures happen before an HTTP request can be accepted by LiteLLM,
            # so a Temporal activity retry may reserve a new provider-attempt row.
            raise LiteLLMError(
                "litellm_unavailable",
                retryable=True,
                egress_state="not_sent",
            ) from exc
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            # Read/write/protocol failures may occur after LiteLLM accepted the request.
            # Conservatively block automatic replay because provider outcome is unknown.
            raise LiteLLMError(
                "litellm_outcome_ambiguous",
                retryable=False,
                egress_state="unknown",
            ) from exc
        if response.status_code == 504:
            # A proxy timeout cannot establish whether upstream inference completed.
            raise LiteLLMError(
                "litellm_outcome_ambiguous",
                retryable=False,
                egress_state="unknown",
                raw_response=_error_response_payload(response),
            )
        if response.status_code in {408, 409, 429} or response.status_code >= 500:
            raise LiteLLMError(
                "litellm_retryable_response",
                retryable=True,
                raw_response=_error_response_payload(response),
            )
        if response.status_code in {401, 403}:
            raise LiteLLMError(
                "litellm_authentication_failed",
                retryable=False,
                raw_response=_error_response_payload(response),
            )
        if response.status_code >= 400:
            raise LiteLLMError(
                "litellm_request_rejected",
                retryable=False,
                raw_response=_error_response_payload(response),
            )
        try:
            raw = response.json()
        except ValueError as exc:
            raise LiteLLMError(
                "litellm_invalid_json",
                retryable=False,
                raw_response={
                    "http_status": response.status_code,
                    "body_text": getattr(response, "text", ""),
                },
            ) from exc
        if not isinstance(raw, dict):
            raise LiteLLMError(
                "litellm_invalid_response",
                retryable=False,
                raw_response={"response_json": raw},
            )
        actual_model, actual_provider = reported_model_provenance(raw)
        hidden = raw.get("_hidden_params")
        hidden_mapping = hidden if isinstance(hidden, dict) else {}
        try:
            content = _response_content(raw)
        except LiteLLMError as exc:
            raise LiteLLMError(
                exc.code,
                retryable=exc.retryable,
                raw_response=dict(raw),
            ) from exc
        try:
            parsed = (
                json.loads(content)
                if "response_format" in snapshot.config and isinstance(content, str)
                else content
            )
        except json.JSONDecodeError as exc:
            raise LiteLLMError(
                "litellm_invalid_structured_output",
                retryable=False,
                raw_response=dict(raw),
            ) from exc
        usage = raw.get("usage")
        cost = hidden_mapping.get("response_cost") or raw.get("cost")
        return LiteLLMGenerationResult(
            request=request,
            raw_response=dict(raw),
            parsed_content=parsed,
            actual_model=actual_model,
            actual_provider=actual_provider,
            provider_request_id=_optional_string(raw.get("id")),
            token_usage=dict(usage) if isinstance(usage, dict) else None,
            cost_details={"total": cost} if isinstance(cost, (int, float)) and not isinstance(cost, bool) else None,
        )


def reported_model_provenance(raw: object) -> tuple[str | None, str | None]:
    """Only response-body facts; requested aliases and transport headers are not proof."""
    if not isinstance(raw, Mapping):
        return None, None
    hidden = raw.get("_hidden_params")
    provider = (
        _optional_string(hidden.get("custom_llm_provider"))
        if isinstance(hidden, Mapping) else None
    )
    return _optional_string(raw.get("model")), provider or _optional_string(raw.get("provider"))


def canonical_transcript(segments: Sequence[OutcomeTranscriptSegment]) -> str:
    rows = [
        {
            "attribution_state": segment.attribution_state,
            "end_seconds": str(segment.end_seconds),
            "provider_speaker_key": segment.provider_speaker_key,
            "result_state": segment.result_state,
            "sequence": segment.sequence,
            "source_role": segment.source_role,
            "speaker_key": segment.speaker_key,
            "speaker_label": segment.speaker_label,
            "start_seconds": str(segment.start_seconds),
            "text": segment.text,
            "transcript_segment_id": str(segment.segment_id),
        }
        for segment in segments
    ]
    return canonical_json(rows)


def model_transcript(transcript_json: str) -> str:
    """Lossless model view; the ledger keeps the unchanged canonical snapshot."""
    attributions: list[dict[str, object]] = []
    attribution_indexes: dict[str, int] = {}
    segments = []
    segment_fields = (
        "sequence", "transcript_segment_id", "text", "start_seconds", "end_seconds",
    )
    for row in json.loads(transcript_json):
        attribution = {key: value for key, value in row.items() if key not in segment_fields}
        key = canonical_json(attribution)
        if key not in attribution_indexes:
            attribution_indexes[key] = len(attributions)
            attributions.append(attribution)
        segments.append({
            "sequence": row["sequence"], "transcript_segment_id": row["transcript_segment_id"],
            "attribution": attribution_indexes[key], "text": row["text"],
            "start_seconds": row["start_seconds"], "end_seconds": row["end_seconds"],
        })
    return json.dumps({"attributions": attributions, "segments": segments}, ensure_ascii=False, indent=2)


def compile_prompt_messages(
    snapshot: PromptSnapshot,
    *,
    transcript_json: str,
    output_language: str,
    detail_level: str,
    template_sections: Sequence[str],
    draft_json: str | None = None,
    extraction_json: str | None = None,
) -> list[dict[str, str]]:
    if snapshot.prompt_type != "chat" or not isinstance(snapshot.prompt, list):
        raise ValueError("outcome generation requires a chat prompt")
    variables = {
        "transcript_json": transcript_json,
        "output_language": output_language,
        "detail_level": detail_level,
        "template_sections_json": canonical_json(list(template_sections)),
    }
    if draft_json is not None:
        variables["draft_json"] = draft_json
    if extraction_json is not None:
        variables["extraction_json"] = extraction_json
    messages: list[dict[str, str]] = []
    for message in snapshot.prompt:
        if not isinstance(message, dict) or set(message) not in (
            {"role", "content"},
            {"type", "role", "content"},
        ):
            raise ValueError("chat prompt messages must contain role and content only")
        if "type" in message and message["type"] != "message":
            raise ValueError("chat prompt message type is invalid")
        role = message["role"]
        content = message["content"]
        if role not in {"system", "user", "assistant"} or not isinstance(content, str):
            raise ValueError("chat prompt message is invalid")
        # Validate placeholders in the template before inserting values. A
        # transcript is untrusted data and may legitimately contain
        # placeholder-looking text; checking the rendered message would treat
        # that data as an unresolved instruction.
        template_content = content
        for key in variables:
            template_content = template_content.replace(f"{{{{{key}}}}}", "")
        if "{{" in template_content or "}}" in template_content:
            raise ValueError("chat prompt contains an unresolved variable")
        # Replace template variables in one pass so inserted data is never
        # processed as another variable.
        content = PROMPT_VARIABLE_RE.sub(
            lambda match: variables.get(match.group(1), match.group(0)),
            content,
        )
        messages.append({"role": role, "content": content})
    return messages


def _response_content(raw: Mapping[str, Any]) -> object:
    choices = raw.get("choices")
    if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict):
        raise LiteLLMError("litellm_invalid_response", retryable=False)
    if choices[0].get("finish_reason") != "stop":
        raise LiteLLMError("litellm_incomplete_response", retryable=False)
    message = choices[0].get("message")
    if not isinstance(message, dict) or not isinstance(message.get("content"), str) or message.get("refusal"):
        raise LiteLLMError("litellm_invalid_response", retryable=False)
    return message["content"]


def _optional_string(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def _error_response_payload(response: object) -> dict[str, object]:
    status_code = getattr(response, "status_code", None)
    try:
        response_json = response.json()  # type: ignore[attr-defined]
    except (AttributeError, ValueError):
        return {
            "http_status": status_code,
            "body_text": getattr(response, "text", ""),
        }
    return {"http_status": status_code, "response_json": response_json}
