"""LiteLLM callback for the GRAF trusted route-binding fence.

This file is copied into the separately operated LiteLLM deployment. It is
kept in GRAF so the provider-side contract is reviewable and reproducible;
the deployment still owns its keys and runtime configuration.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any

from fastapi import HTTPException
from litellm.integrations.custom_logger import CustomLogger

ROUTE_HASH_HEADER = "X-GRAF-Route-Binding-Hash"
ACTUAL_PROVIDER_HEADER = "X-GRAF-Actual-Provider"
ACTUAL_MODEL_HEADER = "X-GRAF-Actual-Model"


def _header(headers: Mapping[str, object] | None, name: str) -> str | None:
    if not headers:
        return None
    expected = name.lower()
    for key, value in headers.items():
        if str(key).lower() == expected and isinstance(value, str):
            return value
    return None


def _field(value: object, name: str) -> object | None:
    if isinstance(value, Mapping):
        return value.get(name)
    return getattr(value, name, None)


class GrafRouteBindingCallback(CustomLogger):
    """Validate GRAF calls before egress and expose trusted provenance after it."""

    def __init__(self) -> None:
        self.expected_hash = os.environ.get("GRAF_ROUTE_BINDING_HASH", "").strip()
        self.key_alias = os.environ.get("GRAF_LITELLM_KEY_ALIAS", "GRAF").strip()
        self.expected_model = os.environ.get("GRAF_ROUTE_MODEL", "gpt-5.6-luna").strip()
        self.expected_provider = os.environ.get("GRAF_ROUTE_PROVIDER", "openai").strip()

    def _is_graf_key(self, user_api_key_dict: object) -> bool:
        return _field(user_api_key_dict, "key_alias") == self.key_alias

    async def async_pre_call_hook(
        self,
        user_api_key_dict: object,
        cache: object,
        data: dict[str, Any],
        call_type: object,
    ) -> dict[str, Any]:
        if not self._is_graf_key(user_api_key_dict):
            return data
        proxy_request = data.get("proxy_server_request")
        request_headers = proxy_request.get("headers") if isinstance(proxy_request, Mapping) else None
        request_hash = _header(request_headers, ROUTE_HASH_HEADER) or _header(
            data.get("headers"), ROUTE_HASH_HEADER
        )
        if not self.expected_hash or request_hash != self.expected_hash:
            raise HTTPException(status_code=403, detail="graf_route_binding_invalid")
        if data.get("model") != self.expected_model:
            raise HTTPException(status_code=403, detail="graf_route_model_invalid")
        return data

    async def async_post_call_response_headers_hook(
        self,
        data: dict[str, Any],
        user_api_key_dict: object,
        response: object,
        request_headers: Mapping[str, object] | None = None,
        litellm_call_info: Mapping[str, object] | None = None,
    ) -> dict[str, str] | None:
        if not self._is_graf_key(user_api_key_dict):
            return None
        request_hash = _header(request_headers, ROUTE_HASH_HEADER) or _header(
            data.get("headers"), ROUTE_HASH_HEADER
        )
        if not self.expected_hash or request_hash != self.expected_hash:
            return None

        model_info = _field(litellm_call_info, "model_info")
        hidden_params = _field(response, "_hidden_params")
        provider = (
            _field(litellm_call_info, "custom_llm_provider")
            or _field(response, "custom_llm_provider")
            or _field(hidden_params, "custom_llm_provider")
            or _field(model_info, "litellm_provider")
            or _field(model_info, "provider")
        )
        model = _field(response, "model") or data.get("model")
        if model != self.expected_model:
            if isinstance(model_info, Mapping):
                model = model_info.get("key") or model_info.get("model_name") or model
        # LiteLLM 1.95 can omit custom_llm_provider from the response callback
        # even when the selected model has one deployment in the model registry.
        # Only use the operator-pinned provider after the successful response
        # still identifies the exact expected model; any model mismatch returns
        # no provenance and GRAF fails closed.
        if provider is None and model == self.expected_model:
            provider = self.expected_provider
        if provider != self.expected_provider or model != self.expected_model:
            return None
        return {
            ROUTE_HASH_HEADER: self.expected_hash,
            ACTUAL_PROVIDER_HEADER: str(provider),
            ACTUAL_MODEL_HEADER: str(model),
        }


graf_route_binding_callback = GrafRouteBindingCallback()
