from __future__ import annotations

from hashlib import sha256

from cryptography.fernet import Fernet

SAFE_CREDENTIAL_FAILURES = {
    "invalid_app_password": ("invalid_credentials", "invalid"),
    "oauth_unavailable": ("tenant_policy_denied", "pending"),
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


def safe_credential_failure(reason: str) -> dict[str, str]:
    safe_error_code, credential_state = SAFE_CREDENTIAL_FAILURES.get(reason, ("provider_unavailable", "sealed"))
    return {
        "safe_error_code": safe_error_code,
        "credential_state": credential_state,
        "detail": "Calendar connection could not be verified.",
    }
