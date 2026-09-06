from __future__ import annotations

from typing import Any

import pytest

from twobrain_rec_server.outcomes.generator import LiteLLMError, LiteLLMGateway
from twobrain_rec_server.outcomes.prompts import outcome_config, validate_prompt_snapshot


def _snapshot():
    return validate_prompt_snapshot(
        name="graf/meeting-outcome/auto",
        version=3,
        prompt_type="chat",
        prompt=[
            {
                "role": "system",
                "content": (
                    "{{output_language}} {{detail_level}} {{template_sections_json}}"
                ),
            },
            {"role": "user", "content": "{{transcript_json}}"},
        ],
        config={**outcome_config(schema_name="graf_meeting_outcome_auto_v1"), "model": "synthetic-route", "temperature": 0},
    )


class _Response:
    status_code = 200

    def json(self) -> dict[str, Any]:
        return {
            "id": "gateway-request",
            "model": "provider-model",
            "provider": "provider-a",
            "usage": {"input": 11, "output": 7, "total": 18},
            "choices": [
                {
                    "message": {
                        "content": '{"category_states":{},"items":[]}',
                    }
                }
            ],
        }


class _AsyncClient:
    requests: list[dict[str, object]] = []

    def __init__(self, *, timeout: int) -> None:
        self.timeout = timeout

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def post(self, url: str, *, headers: dict[str, str], json: dict[str, object]):
        self.requests.append({"url": url, "headers": headers, "json": json})
        return _Response()


@pytest.mark.asyncio
async def test_gateway_projects_only_pinned_config_and_does_not_retry(monkeypatch) -> None:
    import httpx

    _AsyncClient.requests.clear()
    monkeypatch.setattr(httpx, "AsyncClient", _AsyncClient)
    result = await LiteLLMGateway(
        base_url="https://litellm.example/v1",
        api_key="secret",
        timeout_seconds=19,
    ).generate(
        snapshot=_snapshot(),
        messages=[{"role": "user", "content": "full"}],
        idempotency_key="candidate-attempt-1",
    )
    assert len(_AsyncClient.requests) == 1
    assert set(result.request) == {
        "model",
        "messages",
        "temperature",
        "response_format",
    }
    assert result.actual_model == "provider-model"
    assert result.actual_provider == "provider-a"
    assert result.token_usage == {"input": 11, "output": 7, "total": 18}
    assert _AsyncClient.requests[0]["headers"]["Idempotency-Key"] == "candidate-attempt-1"


@pytest.mark.asyncio
async def test_gateway_accepts_plain_authenticated_response_without_route_contract(monkeypatch) -> None:
    from types import SimpleNamespace

    import httpx

    pinned = _snapshot()
    snapshot = SimpleNamespace(
        config=pinned.config, litellm_request=pinned.litellm_request,
    )
    monkeypatch.setattr(httpx, "AsyncClient", _AsyncClient)
    _AsyncClient.requests.clear()
    result = await LiteLLMGateway(
        base_url="https://litellm.example/v1",
        api_key="secret",
        timeout_seconds=19,
    ).generate(snapshot=snapshot, messages=[{"role": "user", "content": "full"}])
    assert result.actual_model == "provider-model"
    assert _AsyncClient.requests[0]["headers"] == {
        "Authorization": "Bearer secret", "Content-Type": "application/json",
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("reported", "expected"),
    [
        ({}, (None, None)),
        ({"model": "other-model"}, ("other-model", None)),
        ({"model": "other-model", "provider": "other-provider"}, ("other-model", "other-provider")),
        ({"_hidden_params": {"custom_llm_provider": "reported-provider"}}, (None, "reported-provider")),
        ({"model": 42, "provider": False}, (None, None)),
    ],
)
async def test_gateway_uses_only_reported_body_provenance(monkeypatch, reported, expected) -> None:
    import httpx

    class HeaderOnlyResponse(_Response):
        headers = {
            "X-Provider": "ignored-header-provider",
            "X-Model": "ignored-header-model",
        }

        def json(self) -> dict[str, Any]:
            value = super().json()
            value.pop("provider")
            value.pop("model")
            return {**value, **reported}

    class HeaderOnlyClient(_AsyncClient):
        async def post(self, *args, **kwargs):
            self.requests.append({"url": args[0], "headers": kwargs["headers"], "json": kwargs["json"]})
            return HeaderOnlyResponse()

    monkeypatch.setattr(httpx, "AsyncClient", HeaderOnlyClient)
    _AsyncClient.requests.clear()
    result = await LiteLLMGateway(
        base_url="https://litellm.example/v1",
        api_key="secret",
        timeout_seconds=19,
    ).generate(snapshot=_snapshot(), messages=[{"role": "user", "content": "full"}])

    assert (result.actual_model, result.actual_provider) == expected
    assert result.raw_response == HeaderOnlyResponse().json()
    assert len(_AsyncClient.requests) == 1


@pytest.mark.asyncio
async def test_gateway_classifies_auth_as_terminal(monkeypatch) -> None:
    import httpx

    class AuthResponse(_Response):
        status_code = 401

    class AuthClient(_AsyncClient):
        async def post(self, *args, **kwargs):
            return AuthResponse()

    monkeypatch.setattr(httpx, "AsyncClient", AuthClient)
    with pytest.raises(LiteLLMError) as raised:
        await LiteLLMGateway(
            base_url="https://litellm.example/v1",
            api_key="secret",
            timeout_seconds=19,
        ).generate(snapshot=_snapshot(), messages=[{"role": "user", "content": "full"}])
    assert raised.value.retryable is False
    assert raised.value.raw_response == {
        "http_status": 401,
        "response_json": AuthResponse().json(),
    }


@pytest.mark.asyncio
async def test_gateway_retains_retryable_http_response(monkeypatch) -> None:
    import httpx

    class RateLimitResponse(_Response):
        status_code = 429

    class RateLimitClient(_AsyncClient):
        async def post(self, *args, **kwargs):
            return RateLimitResponse()

    monkeypatch.setattr(httpx, "AsyncClient", RateLimitClient)
    with pytest.raises(LiteLLMError) as raised:
        await LiteLLMGateway(
            base_url="https://litellm.example/v1",
            api_key="secret",
            timeout_seconds=19,
        ).generate(snapshot=_snapshot(), messages=[{"role": "user", "content": "full"}])

    assert raised.value.retryable is True
    assert raised.value.egress_state == "response_received"
    assert raised.value.raw_response == {
        "http_status": 429,
        "response_json": RateLimitResponse().json(),
    }


@pytest.mark.asyncio
async def test_gateway_preserves_malformed_success_response_for_observability(monkeypatch) -> None:
    import httpx

    class MalformedResponse(_Response):
        def json(self) -> dict[str, Any]:
            return {"id": "gateway-request", "model": "provider-model", "choices": []}

    class MalformedClient(_AsyncClient):
        async def post(self, *args, **kwargs):
            return MalformedResponse()

    monkeypatch.setattr(httpx, "AsyncClient", MalformedClient)
    with pytest.raises(LiteLLMError) as raised:
        await LiteLLMGateway(
            base_url="https://litellm.example/v1",
            api_key="secret",
            timeout_seconds=19,
        ).generate(snapshot=_snapshot(), messages=[{"role": "user", "content": "full"}])

    assert raised.value.code == "litellm_invalid_response"
    assert raised.value.raw_response == MalformedResponse().json()


@pytest.mark.asyncio
async def test_gateway_marks_connect_failure_safe_for_a_new_provider_attempt(monkeypatch) -> None:
    import httpx

    class ConnectFailureClient(_AsyncClient):
        async def post(self, *args, **kwargs):
            request = httpx.Request("POST", "https://litellm.example/v1/chat/completions")
            raise httpx.ConnectError("connect failed", request=request)

    monkeypatch.setattr(httpx, "AsyncClient", ConnectFailureClient)
    with pytest.raises(LiteLLMError) as raised:
        await LiteLLMGateway(
            base_url="https://litellm.example/v1",
            api_key="secret",
            timeout_seconds=19,
        ).generate(snapshot=_snapshot(), messages=[{"role": "user", "content": "full"}])

    assert raised.value.retryable is True
    assert raised.value.egress_state == "not_sent"
    assert raised.value.raw_response is None


@pytest.mark.asyncio
async def test_gateway_marks_read_timeout_as_ambiguous_without_fabricating_response(
    monkeypatch,
) -> None:
    import httpx

    class ReadTimeoutClient(_AsyncClient):
        async def post(self, *args, **kwargs):
            request = httpx.Request("POST", "https://litellm.example/v1/chat/completions")
            raise httpx.ReadTimeout("response timed out", request=request)

    monkeypatch.setattr(httpx, "AsyncClient", ReadTimeoutClient)
    with pytest.raises(LiteLLMError) as raised:
        await LiteLLMGateway(
            base_url="https://litellm.example/v1",
            api_key="secret",
            timeout_seconds=19,
        ).generate(snapshot=_snapshot(), messages=[{"role": "user", "content": "full"}])

    assert raised.value.retryable is False
    assert raised.value.egress_state == "unknown"
    assert raised.value.raw_response is None
