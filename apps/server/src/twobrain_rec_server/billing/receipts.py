from __future__ import annotations

from enum import StrEnum


class ReceiptState(StrEnum):
    UNKNOWN = "unknown"
    AVAILABLE = "available"
    PENDING = "pending"
    FAILED = "failed"


def receipt_label(state: ReceiptState) -> str:
    return {
        ReceiptState.UNKNOWN: "Чек пока не найден",
        ReceiptState.AVAILABLE: "Открыть чек",
        ReceiptState.PENDING: "Чек формируется",
        ReceiptState.FAILED: "Чек временно недоступен",
    }[state]
