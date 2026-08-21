from __future__ import annotations

import json
from hashlib import sha256
from ipaddress import ip_address
from urllib.parse import urlparse

from cryptography.fernet import Fernet

SAFE_CREDENTIAL_FAILURES = {
    "invalid_app_password": ("invalid_credentials", "invalid"),
    "tenant_denied": ("tenant_policy_denied", "revoked"),
    "provider_timeout": ("provider_timeout", "sealed"),
    "rate_limited": ("rate_limited", "sealed"),
}


def generate_credential_key() -> bytes:
    return Fernet.generate_key()


def credential_fingerprint(secret: str) -> str:
    return sha256(secret.encode("utf-8")).hexdigest()


def seal_credential(secret: str, key: bytes) -> bytes:
    return Fernet(key).encrypt(secret.encode("utf-8"))


def unseal_credential(sealed_payload: bytes, key: bytes) -> str:
    return Fernet(key).decrypt(sealed_payload).decode("utf-8")


def sealed_credential_metadata(*, secret: str, secret_kind: str) -> dict[str, str]:
    return {
        "secret_kind": secret_kind,
        "secret_fingerprint_sha256": credential_fingerprint(secret),
        "credential_state": "sealed",
    }


def calendar_connection_secret(
    *,
    method_category: str,
    caldav_url: str | None,
    username: str | None,
    credential_input: str | None,
) -> str | None:
    secret = (credential_input or "").strip()
    if not secret:
        return None
    if method_category == "app_password":
        user = (username or "").strip()
        if not user:
            return None
        return json.dumps(
            {"username": user, "credential_input": secret},
            ensure_ascii=False,
            separators=(",", ":"),
        )
    url = _safe_caldav_url(caldav_url)
    user = (username or "").strip()
    if method_category != "manual_url" or url is None or not user:
        return None
    return json.dumps(
        {
            "caldav_url": url,
            "username": user,
            "credential_input": secret,
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )


def safe_credential_failure(reason: str) -> dict[str, str]:
    safe_error_code, credential_state = SAFE_CREDENTIAL_FAILURES.get(reason, ("provider_unavailable", "sealed"))
    return {
        "safe_error_code": safe_error_code,
        "credential_state": credential_state,
        "detail": "Calendar connection could not be verified.",
    }


def _safe_caldav_url(value: str | None) -> str | None:
    url = (value or "").strip()
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname
        _port = parsed.port
    except ValueError:
        return None
    if parsed.scheme != "https" or not parsed.netloc or not hostname:
        return None
    if parsed.username or parsed.password:
        return None
    hostname = hostname.rstrip(".").lower()
    if hostname == "localhost" or hostname.endswith(".localhost"):
        return None
    try:
        if not ip_address(hostname).is_global:
            return None
    except ValueError:
        pass
    return url
