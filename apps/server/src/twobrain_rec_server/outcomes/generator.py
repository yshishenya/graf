from __future__ import annotations

import json
import re
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

from twobrain_rec_server.domain.statuses import OutcomeCategory
from twobrain_rec_server.outcomes.models import (
    GeneratedOutcomeItem,
    GeneratedOutcomePayload,
    OutcomeSourceReference,
    OutcomeTranscriptSegment,
)
from twobrain_rec_server.outcomes.prompts import PromptSnapshot, canonical_json

CATEGORIES = [category.value for category in OutcomeCategory]
NEGATIVE_CONTEXT_RE = re.compile(r"\b(без|нет|не было|отсутств)\b", re.IGNORECASE)
DECISION_RE = re.compile(r"\b(решили|решение|приняли)\b", re.IGNORECASE)
ACTION_RE = re.compile(r"\b(договорились|нужно|надо|проверить|сделать|подготовить)\b", re.IGNORECASE)
FOLLOWUP_RE = re.compile(r"\b(следующ|follow[- ]?up|вернуться)\b", re.IGNORECASE)
RISK_RE = re.compile(r"\b(риск|блокер|проблем|зависим)\b", re.IGNORECASE)
QUESTION_RE = re.compile(r"\?|\b(вопрос|как|что дальше)\b", re.IGNORECASE)


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
        require_route_binding: bool = False,
    ) -> None:
        self._url = f"{base_url.rstrip('/')}/chat/completions"
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds
        self._require_route_binding = require_route_binding

    async def generate(
        self,
        *,
        snapshot: PromptSnapshot,
        messages: Sequence[Mapping[str, str]],
        idempotency_key: str | None = None,
    ) -> LiteLLMGenerationResult:
        import httpx

        request = snapshot.litellm_request(messages)
        route_binding = snapshot.route_binding
        expected_route_hash = snapshot.route_binding_hash
        if self._require_route_binding and route_binding is None:
            raise LiteLLMError(
                "litellm_route_binding_missing",
                retryable=False,
                egress_state="not_sent",
            )
        if route_binding is not None:
            if not expected_route_hash or route_binding.get("binding_hash") != expected_route_hash:
                raise LiteLLMError(
                    "litellm_route_binding_mismatch",
                    retryable=False,
                    egress_state="not_sent",
                )
            descriptor = dict(route_binding)
            descriptor.pop("binding_hash", None)
            if sha256(canonical_json(descriptor).encode("utf-8")).hexdigest() != expected_route_hash:
                raise LiteLLMError(
                    "litellm_route_binding_mismatch",
                    retryable=False,
                    egress_state="not_sent",
                )
        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                headers = {
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                }
                if idempotency_key:
                    headers["Idempotency-Key"] = idempotency_key
                if expected_route_hash:
                    headers["X-GRAF-Route-Binding-Hash"] = expected_route_hash
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
        actual_model = _optional_string(raw.get("model"))
        hidden = raw.get("_hidden_params")
        hidden_mapping = hidden if isinstance(hidden, dict) else {}
        response_headers = getattr(response, "headers", {})
        provider = (
            hidden_mapping.get("custom_llm_provider")
            or raw.get("provider")
            or response_headers.get("X-GRAF-Actual-Provider")
        )
        actual_provider = _optional_string(provider)
        actual_model = actual_model or _optional_string(
            response_headers.get("X-GRAF-Actual-Model")
        )
        if route_binding is not None:
            echoed_hash = response_headers.get("X-GRAF-Route-Binding-Hash")
            if echoed_hash != expected_route_hash:
                raise LiteLLMError(
                    "litellm_route_binding_unconfirmed",
                    retryable=False,
                    raw_response={"route_binding_hash": echoed_hash},
                )
            allowed_pairs = route_binding.get("allowed_provider_models")
            if not isinstance(allowed_pairs, list) or not any(
                isinstance(pair, dict)
                and pair.get("provider") == actual_provider
                and pair.get("model") == actual_model
                for pair in allowed_pairs
            ):
                raise LiteLLMError(
                    "litellm_route_binding_pair_unallowlisted",
                    retryable=False,
                    raw_response={
                        "actual_provider": actual_provider,
                        "actual_model": actual_model,
                    },
                )
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


def compile_prompt_messages(
    snapshot: PromptSnapshot,
    *,
    transcript_json: str,
    output_language: str,
    detail_level: str,
    template_sections: Sequence[str],
) -> list[dict[str, str]]:
    if snapshot.prompt_type != "chat" or not isinstance(snapshot.prompt, list):
        raise ValueError("outcome generation requires a chat prompt")
    variables = {
        "transcript_json": transcript_json,
        "output_language": output_language,
        "detail_level": detail_level,
        "template_sections_json": canonical_json(list(template_sections)),
    }
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
        for key, value in variables.items():
            content = content.replace(f"{{{{{key}}}}}", value)
        if "{{" in content or "}}" in content:
            raise ValueError("chat prompt contains an unresolved variable")
        messages.append({"role": role, "content": content})
    return messages


def _response_content(raw: Mapping[str, Any]) -> object:
    choices = raw.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        raise LiteLLMError("litellm_invalid_response", retryable=False)
    message = choices[0].get("message")
    if not isinstance(message, dict) or "content" not in message:
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


def generate_outcomes(segments: Sequence[OutcomeTranscriptSegment]) -> GeneratedOutcomePayload:
    ordered = [segment for segment in segments if segment_text(segment)]
    items_by_category: dict[str, list[GeneratedOutcomeItem]] = {category: [] for category in CATEGORIES}
    states = {category: "not_found" for category in CATEGORIES}
    if not ordered:
        return GeneratedOutcomePayload(category_states={category: "not_inferable" for category in CATEGORIES}, items_by_category=items_by_category)

    summary_segment = ordered[0]
    items_by_category["summary"].append(_item("summary", 0, _bounded_text(summary_segment.text), summary_segment))
    states["summary"] = "available"

    for index, segment in enumerate(ordered[:3]):
        items_by_category["key_points"].append(_item("key_points", index, _bounded_text(segment.text), segment))
    states["key_points"] = "available"

    evidence_segment = ordered[0]
    items_by_category["evidence"].append(
        _item(
            "evidence",
            0,
            f"Фрагмент на {_time_label(float(evidence_segment.start_seconds))}",
            evidence_segment,
        )
    )
    states["evidence"] = "available"

    cue_map = {
        "decisions": DECISION_RE,
        "action_items": ACTION_RE,
        "followups": FOLLOWUP_RE,
        "risks": RISK_RE,
        "questions": QUESTION_RE,
    }
    counters: dict[str, int] = defaultdict(int)
    for segment in ordered:
        lowered = segment.text.lower()
        if NEGATIVE_CONTEXT_RE.search(lowered):
            continue
        for category, pattern in cue_map.items():
            if pattern.search(segment.text):
                sequence = counters[category]
                counters[category] += 1
                items_by_category[category].append(_item(category, sequence, _bounded_text(segment.text), segment))
                states[category] = "available"

    for category in ["decisions", "action_items", "followups", "risks", "questions"]:
        if not items_by_category[category]:
            states[category] = "not_inferable" if category == "action_items" else "not_found"

    return GeneratedOutcomePayload(category_states=states, items_by_category=items_by_category)


def segment_text(segment: OutcomeTranscriptSegment) -> str:
    return " ".join(segment.text.split())


def _bounded_text(text: str, limit: int = 280) -> str:
    clean = " ".join(text.split())
    if len(clean) <= limit:
        return clean
    return clean[: limit - 1].rstrip() + "…"


def _item(category: str, sequence: int, text: str, segment: OutcomeTranscriptSegment) -> GeneratedOutcomeItem:
    return GeneratedOutcomeItem(
        category=category,
        sequence=sequence,
        text=text,
        truth_label="supported",
        source_refs=[
            OutcomeSourceReference(
                transcript_segment_id=segment.segment_id,
                sequence=segment.sequence,
                start_seconds=float(segment.start_seconds),
                end_seconds=float(segment.end_seconds),
                speaker_label=segment.speaker_label,
                source_role=segment.source_role,
                evidence_kind="segment",
            )
        ],
    )


def _time_label(seconds: float) -> str:
    total = max(0, int(seconds))
    minute, second = divmod(total, 60)
    return f"{minute:02d}:{second:02d}"
