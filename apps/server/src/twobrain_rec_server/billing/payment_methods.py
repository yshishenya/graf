from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

_PROVIDER_REFERENCE_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,159}")
_KEY_VERSION_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,31}")


class PaymentMethodEncryptionError(ValueError):
    """Fail-closed payment-method decryption error without secret detail."""


@dataclass(frozen=True, slots=True)
class SavedPaymentMethod:
    provider_ref: str
    kind: str
    masked_label: str


@dataclass(frozen=True, slots=True)
class SealedProviderReference:
    ciphertext: str = field(repr=False)
    key_version: str


@dataclass(frozen=True, slots=True)
class BillingEncryptionKeyring:
    """Current-write/previous-read key ring for saved provider references."""

    current_version: str
    keys: Mapping[str, bytes] = field(repr=False)

    def __post_init__(self) -> None:
        if not _KEY_VERSION_RE.fullmatch(self.current_version):
            raise PaymentMethodEncryptionError("payment-method key version is invalid")
        validated: dict[str, bytes] = {}
        for version, key in self.keys.items():
            if not _KEY_VERSION_RE.fullmatch(version):
                raise PaymentMethodEncryptionError("payment-method key version is invalid")
            try:
                Fernet(key)
            except (TypeError, ValueError) as exc:
                raise PaymentMethodEncryptionError("payment-method encryption key is invalid") from exc
            validated[version] = key
        if self.current_version not in validated:
            raise PaymentMethodEncryptionError("current payment-method key is unavailable")
        object.__setattr__(self, "keys", MappingProxyType(validated))

    def seal(self, provider_ref: str) -> SealedProviderReference:
        key = self.keys[self.current_version]
        return SealedProviderReference(
            ciphertext=seal_provider_reference(provider_ref, key),
            key_version=self.current_version,
        )

    def open(self, *, ciphertext: str, key_version: str) -> str:
        key = self.keys.get(key_version)
        if key is None:
            raise PaymentMethodEncryptionError("payment-method key version is unavailable")
        return open_provider_reference(ciphertext, key)

    def rotate(self, *, ciphertext: str, key_version: str) -> SealedProviderReference:
        provider_ref = self.open(ciphertext=ciphertext, key_version=key_version)
        if key_version == self.current_version:
            return SealedProviderReference(ciphertext=ciphertext, key_version=key_version)
        return self.seal(provider_ref)


def validate_payment_method_key_version(value: str) -> str:
    if not _KEY_VERSION_RE.fullmatch(value):
        raise PaymentMethodEncryptionError("payment-method key version is invalid")
    return value


def extract_saved_bank_card(payload: Mapping[str, Any]) -> SavedPaymentMethod | None:
    method = payload.get("payment_method")
    if not isinstance(method, Mapping) or method.get("type") != "bank_card" or method.get("saved") is not True:
        return None
    provider_ref = method.get("id")
    card = method.get("card")
    last4 = card.get("last4") if isinstance(card, Mapping) else None
    if not isinstance(provider_ref, str) or not _PROVIDER_REFERENCE_RE.fullmatch(provider_ref):
        return None
    if not isinstance(last4, str) or not re.fullmatch(r"\d{4}", last4):
        return None
    return SavedPaymentMethod(provider_ref, "bank_card", f"•••• {last4}")


def extract_payment_method_label(payload: Mapping[str, Any]) -> str | None:
    """Return only the immutable masked card label for invoice history."""
    method = payload.get("payment_method")
    card = method.get("card") if isinstance(method, Mapping) else None
    last4 = card.get("last4") if isinstance(card, Mapping) else None
    if not isinstance(method, Mapping) or method.get("type") != "bank_card":
        return None
    if not isinstance(last4, str) or not re.fullmatch(r"\d{4}", last4):
        return None
    return f"•••• {last4}"


def seal_provider_reference(provider_ref: str, key: bytes) -> str:
    if not _PROVIDER_REFERENCE_RE.fullmatch(provider_ref) or not key:
        raise ValueError("provider reference and encryption key are required")
    return Fernet(key).encrypt(provider_ref.encode("utf-8")).decode("ascii")


def open_provider_reference(ciphertext: str, key: bytes) -> str:
    if not ciphertext or not key:
        raise PaymentMethodEncryptionError("payment-method reference is unavailable")
    try:
        provider_ref = Fernet(key).decrypt(ciphertext.encode("ascii")).decode("utf-8")
    except (InvalidToken, UnicodeDecodeError, ValueError) as exc:
        raise PaymentMethodEncryptionError("payment-method reference is unavailable") from exc
    if not _PROVIDER_REFERENCE_RE.fullmatch(provider_ref):
        raise PaymentMethodEncryptionError("payment-method reference is invalid")
    return provider_ref


def read_billing_encryption_key(path: Path | None) -> bytes | None:
    if path is None or not path.is_file():
        return None
    try:
        key = path.read_bytes().strip()
        Fernet(key)
    except (OSError, ValueError):
        return None
    return key
