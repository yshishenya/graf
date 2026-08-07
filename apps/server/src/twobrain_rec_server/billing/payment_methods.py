from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet


@dataclass(frozen=True, slots=True)
class SavedPaymentMethod:
    provider_ref: str
    kind: str
    masked_label: str


def extract_saved_bank_card(payload: Mapping[str, Any]) -> SavedPaymentMethod | None:
    method = payload.get("payment_method")
    if not isinstance(method, Mapping) or method.get("type") != "bank_card" or method.get("saved") is not True:
        return None
    provider_ref = method.get("id")
    card = method.get("card")
    last4 = card.get("last4") if isinstance(card, Mapping) else None
    if not isinstance(provider_ref, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,159}", provider_ref):
        return None
    if not isinstance(last4, str) or not re.fullmatch(r"\d{4}", last4):
        return None
    return SavedPaymentMethod(provider_ref, "bank_card", f"•••• {last4}")


def seal_provider_reference(provider_ref: str, key: bytes) -> str:
    if not provider_ref or not key:
        raise ValueError("provider reference and encryption key are required")
    return Fernet(key).encrypt(provider_ref.encode("utf-8")).decode("ascii")


def read_billing_encryption_key(path: Path | None) -> bytes | None:
    if path is None or not path.is_file():
        return None
    try:
        key = path.read_bytes().strip()
        Fernet(key)
    except (OSError, ValueError):
        return None
    return key
