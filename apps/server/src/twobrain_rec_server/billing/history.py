from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime

_MASKED_METHOD_PATTERNS = (
    re.compile(r"•••• \d{4}"),
    re.compile(r"card_ending_\d{4}"),
)


@dataclass(frozen=True, slots=True)
class PaymentHistoryItem:
    invoice_number: str
    created_at: datetime
    amount_minor: int
    currency: str
    status: str
    masked_method: str | None
    receipt_available: bool


def mask_payment_method(label: str | None) -> str | None:
    if not label:
        return None
    normalized = label.strip()
    if any(pattern.fullmatch(normalized) for pattern in _MASKED_METHOD_PATTERNS):
        return normalized
    return None
