from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


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
    return label[:32]
