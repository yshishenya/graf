from __future__ import annotations

import hashlib
import hmac
import json
from base64 import urlsafe_b64encode
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from urllib.parse import urlencode
from urllib.request import Request, urlopen

PROVIDER_YANDEX = "yandex"
PROVIDER_VK = "vk"
PROVIDER_TELEGRAM = "telegram"

SUPPORTED_PROVIDER_IDS = (PROVIDER_YANDEX, PROVIDER_VK, PROVIDER_TELEGRAM)


def normalize_provider(provider: str) -> str:
    value = provider.strip().lower()
    if value not in SUPPORTED_PROVIDER_IDS:
        raise ValueError(f"unsupported provider: {provider}")
    return value


@dataclass(frozen=True)
class ProviderIdentity:
    provider: str
    provider_subject: str
    provider_username: str | None = None
    email: str | None = None
    phone: str | None = None
    display_name: str | None = None
    # Providers must opt in after a verified callback/profile exchange. A
    # subject alone is not proof that the attached email belongs to it.
    is_verified: bool = False

    def normalized_subject(self) -> str:
        return self.provider_subject.strip().lower()


@dataclass(frozen=True)
class ProviderProfile:
    provider: str
    enabled: bool
    label: str
    requires_email: bool = True


class ProviderVerificationError(ValueError):
    """Raised when a provider callback cannot be cryptographically verified."""


@dataclass(frozen=True)
class ProviderCredentials:
    client_id: str
    redirect_uri: str
    client_secret: str | None = None


class ProviderHttpClient(Protocol):
    def post_form(
        self,
        url: str,
        data: dict[str, str],
        *,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]: ...

    def get_json(
        self,
        url: str,
        *,
        params: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]: ...


class UrlLibProviderHttpClient:
    def post_form(
        self,
        url: str,
        data: dict[str, str],
        *,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        body = urlencode(data).encode()
        request = Request(
            url,
            data=body,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
                **(headers or {}),
            },
            method="POST",
        )
        return _decode_json_response(request)

    def get_json(
        self,
        url: str,
        *,
        params: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        target = url
        if params:
            target = f"{url}?{urlencode(params)}"
        request = Request(target, headers={"Accept": "application/json", **(headers or {})})
        return _decode_json_response(request)


def _decode_json_response(request: Request) -> dict[str, Any]:
    try:
        with urlopen(request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise ProviderVerificationError("provider verification request failed") from exc
    if not isinstance(payload, dict):
        raise ProviderVerificationError("provider verification response is not an object")
    return payload


_PROVIDER_HTTP_CLIENT = UrlLibProviderHttpClient()


def get_provider_http_client() -> ProviderHttpClient:
    return _PROVIDER_HTTP_CLIENT


class ProviderAdapter:
    provider: str = ""
    label: str = ""
    requires_email: bool = False
    auth_base_url: str = ""
    requires_state: bool = True
    accepts_direct_callback_claims: bool = False

    def is_known(self, provider: str) -> bool:
        return normalize_provider(provider) == self.provider

    def build_authorization_url(
        self,
        *,
        client_id: str,
        client_secret: str | None = None,
        redirect_uri: str,
        state: str,
        return_url: str | None,
        workspace_id: str,
        auth_provider: str | None = None,
    ) -> str:
        _ = client_secret, auth_provider
        params: dict[str, str] = {
            "response_type": "code",
            "client_id": client_id,
            "state": state,
            "redirect_uri": redirect_uri,
        }
        if return_url:
            params["workspace_return_url"] = return_url
        params["workspace_id"] = workspace_id
        return f"{self.auth_base_url}?{urlencode(params)}"

    def parse_callback(self, query: dict[str, str], *, expected_state: str) -> ProviderIdentity:
        state = query.get("state", "")
        if self.requires_state and state != expected_state:
            raise ValueError("invalid callback state")
        if not self.accepts_direct_callback_claims:
            raise ProviderVerificationError(
                f"provider {self.provider} callback verification is not implemented"
            )
        subject = query.get("code", "").strip()
        if not subject:
            subject = query.get("id", "").strip()
        if not subject:
            raise ValueError("missing provider subject code")
        provider_subject = self.normalize_subject(subject)
        email = _optional_str(query.get("email"))
        return ProviderIdentity(
            provider=self.provider,
            provider_subject=provider_subject,
            provider_username=query.get("username"),
            email=email,
            phone=query.get("phone"),
            display_name=query.get("name") or query.get("display_name"),
            # The provider adapter has already exchanged and validated the
            # callback; an email claim returned by that verified profile is
            # eligible for exact-email invitation matching.
            is_verified=bool(email),
        )

    def verify_callback(
        self,
        query: dict[str, str],
        *,
        expected_state: str,
        credentials: ProviderCredentials,
        http_client: ProviderHttpClient,
        now: datetime | None = None,
    ) -> ProviderIdentity:
        if self.accepts_direct_callback_claims:
            return self.parse_callback(query, expected_state=expected_state)
        raise ProviderVerificationError(
            f"provider {self.provider} callback verification is not implemented"
        )

    def normalize_subject(self, subject: str) -> str:
        return subject.strip().lower()


class YandexAdapter(ProviderAdapter):
    provider = PROVIDER_YANDEX
    label = "Yandex ID"
    requires_email = True
    auth_base_url = "https://oauth.yandex.ru/authorize"
    token_url = "https://oauth.yandex.ru/token"
    user_info_url = "https://login.yandex.ru/info"

    def verify_callback(
        self,
        query: dict[str, str],
        *,
        expected_state: str,
        credentials: ProviderCredentials,
        http_client: ProviderHttpClient,
        now: datetime | None = None,
    ) -> ProviderIdentity:
        _assert_state(query, expected_state)
        code = _required_query_value(query, "code")
        secret = _required_secret(credentials)
        token = http_client.post_form(
            self.token_url,
            {
                "grant_type": "authorization_code",
                "code": code,
                "client_id": credentials.client_id,
                "client_secret": secret,
                "redirect_uri": credentials.redirect_uri,
            },
        )
        access_token = _required_payload_value(token, "access_token")
        profile = http_client.get_json(
            self.user_info_url,
            params={"format": "json"},
            headers={"Authorization": f"OAuth {access_token}"},
        )
        if str(profile.get("client_id") or "") != credentials.client_id:
            raise ProviderVerificationError("Yandex token was not issued for configured client")
        subject = str(profile.get("id") or profile.get("uid") or "").strip()
        if not subject:
            raise ProviderVerificationError("Yandex profile is missing subject")
        default_phone = profile.get("default_phone") if isinstance(profile.get("default_phone"), dict) else {}
        email = _optional_str(profile.get("default_email") or profile.get("email"))
        return ProviderIdentity(
            provider=self.provider,
            provider_subject=self.normalize_subject(subject),
            provider_username=_optional_str(profile.get("login")),
            email=email,
            phone=_optional_str(default_phone.get("number") or profile.get("number")),
            display_name=_optional_str(
                profile.get("display_name")
                or profile.get("real_name")
                or " ".join(
                    item
                    for item in [
                        _optional_str(profile.get("first_name")),
                        _optional_str(profile.get("last_name")),
                    ]
                    if item
                )
                or profile.get("login")
            ),
            is_verified=bool(email),
        )


class VkAdapter(ProviderAdapter):
    provider = PROVIDER_VK
    label = "VK ID"
    requires_email = True
    auth_base_url = "https://id.vk.ru/authorize"
    token_url = "https://id.vk.ru/oauth2/auth"
    user_info_url = "https://id.vk.ru/oauth2/user_info"
    supported_auth_providers = {"vkid", "ok_ru", "mail_ru"}

    def build_authorization_url(
        self,
        *,
        client_id: str,
        client_secret: str | None = None,
        redirect_uri: str,
        state: str,
        return_url: str | None,
        workspace_id: str,
        auth_provider: str | None = None,
    ) -> str:
        params: dict[str, str] = {
            "response_type": "code",
            "client_id": client_id,
            "state": state,
            "redirect_uri": redirect_uri,
            "scope": "email phone",
            "code_challenge": _vk_code_challenge(client_id=client_id, client_secret=client_secret, state=state),
            "code_challenge_method": "S256",
            "workspace_id": workspace_id,
        }
        if return_url:
            params["workspace_return_url"] = return_url
        if auth_provider in self.supported_auth_providers:
            params["provider"] = auth_provider
        return f"{self.auth_base_url}?{urlencode(params)}"

    def verify_callback(
        self,
        query: dict[str, str],
        *,
        expected_state: str,
        credentials: ProviderCredentials,
        http_client: ProviderHttpClient,
        now: datetime | None = None,
    ) -> ProviderIdentity:
        _assert_state(query, expected_state)
        code = _required_query_value(query, "code")
        device_id = _required_query_value(query, "device_id")
        token = http_client.post_form(
            self.token_url,
            {
                "grant_type": "authorization_code",
                "client_id": credentials.client_id,
                "code_verifier": _vk_code_verifier(
                    client_id=credentials.client_id,
                    client_secret=credentials.client_secret,
                    state=expected_state,
                ),
                "device_id": device_id,
                "redirect_uri": credentials.redirect_uri,
                "code": code,
                "state": expected_state,
            },
        )
        if "error" in token:
            raise ProviderVerificationError("VK authorization code exchange failed")
        if token.get("state") not in {None, "", expected_state}:
            raise ProviderVerificationError("VK token response state mismatch")
        access_token = _required_payload_value(token, "access_token")
        profile_payload = http_client.post_form(
            self.user_info_url,
            {
                "client_id": credentials.client_id,
                "access_token": access_token,
            },
        )
        if "error" in profile_payload:
            raise ProviderVerificationError("VK profile request failed")
        profile = _required_user_info(profile_payload)
        subject = str(token.get("user_id") or profile.get("user_id") or "").strip()
        if not subject:
            raise ProviderVerificationError("VK token response is missing subject")
        first_name = _optional_str(profile.get("first_name"))
        last_name = _optional_str(profile.get("last_name"))
        display_name = " ".join(item for item in [first_name, last_name] if item) or None
        email = _optional_str(profile.get("email"))
        return ProviderIdentity(
            provider=self.provider,
            provider_subject=self.normalize_subject(subject),
            provider_username=None,
            email=email,
            phone=_optional_str(profile.get("phone")),
            display_name=display_name,
            is_verified=bool(email),
        )


class TelegramAdapter(ProviderAdapter):
    provider = PROVIDER_TELEGRAM
    label = "Telegram Login"
    requires_email = False
    auth_base_url = "https://oauth.telegram.org/auth"

    def verify_callback(
        self,
        query: dict[str, str],
        *,
        expected_state: str,
        credentials: ProviderCredentials,
        http_client: ProviderHttpClient,
        now: datetime | None = None,
    ) -> ProviderIdentity:
        _assert_state(query, expected_state)
        bot_token = _required_secret(credentials)
        supplied_hash = _required_query_value(query, "hash").lower()
        signed_fields = {
            key: value
            for key, value in query.items()
            if key not in {"hash", "state"} and value is not None and value != ""
        }
        if not signed_fields:
            raise ProviderVerificationError("Telegram callback has no signed fields")
        data_check_string = "\n".join(f"{key}={signed_fields[key]}" for key in sorted(signed_fields))
        secret_key = hashlib.sha256(bot_token.encode()).digest()
        expected_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected_hash, supplied_hash):
            raise ProviderVerificationError("Telegram callback signature is invalid")
        auth_date = int(_required_query_value(query, "auth_date"))
        now = now or datetime.now(UTC)
        if now.timestamp() - auth_date > 86_400:
            raise ProviderVerificationError("Telegram callback auth_date is expired")
        subject = _required_query_value(query, "id")
        first_name = _optional_str(query.get("first_name"))
        last_name = _optional_str(query.get("last_name"))
        display_name = " ".join(item for item in [first_name, last_name] if item) or None
        return ProviderIdentity(
            provider=self.provider,
            provider_subject=self.normalize_subject(subject),
            provider_username=_optional_str(query.get("username")),
            email=None,
            phone=_optional_str(query.get("phone") or query.get("phone_number")),
            display_name=display_name or _optional_str(query.get("username")),
            is_verified=False,
        )


def _assert_state(query: dict[str, str], expected_state: str) -> None:
    if query.get("state", "") != expected_state:
        raise ValueError("invalid callback state")


def _required_query_value(query: dict[str, str], key: str) -> str:
    value = query.get(key, "").strip()
    if not value:
        raise ProviderVerificationError(f"provider callback missing {key}")
    return value


def _required_payload_value(payload: dict[str, Any], key: str) -> str:
    value = str(payload.get(key) or "").strip()
    if not value:
        raise ProviderVerificationError(f"provider response missing {key}")
    return value


def _required_secret(credentials: ProviderCredentials) -> str:
    value = (credentials.client_secret or "").strip()
    if not value:
        raise ProviderVerificationError("provider client secret is not configured")
    return value


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _base64url(data: bytes) -> str:
    return urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _vk_code_verifier(*, client_id: str, client_secret: str | None, state: str) -> str:
    seed = (client_secret or client_id).encode("utf-8")
    return _base64url(hmac.new(seed, f"{client_id}:{state}".encode(), hashlib.sha256).digest())


def _vk_code_challenge(*, client_id: str, client_secret: str | None, state: str) -> str:
    verifier = _vk_code_verifier(client_id=client_id, client_secret=client_secret, state=state)
    return _base64url(hashlib.sha256(verifier.encode()).digest())


def _required_user_info(payload: dict[str, Any]) -> dict[str, Any]:
    user = payload.get("user")
    if not isinstance(user, dict):
        raise ProviderVerificationError("provider response is missing profile item")
    return user
