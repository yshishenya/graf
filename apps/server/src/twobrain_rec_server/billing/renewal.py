from __future__ import annotations

from datetime import UTC, datetime, timedelta


def renewal_due(*, now: datetime, paid_through: datetime, reminder_hours: int = 72) -> bool:
    return now.astimezone(UTC) >= paid_through.astimezone(UTC) - timedelta(hours=reminder_hours)


def resolve_renewal(*, now: datetime, paid_through: datetime, provider_status: str | None) -> str:
    if now.astimezone(UTC) < paid_through.astimezone(UTC):
        return "personal"
    return "personal" if provider_status == "succeeded" else "free"
