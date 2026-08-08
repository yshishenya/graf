from __future__ import annotations

from datetime import UTC, datetime, timedelta

from twobrain_rec_server.billing.renewal_resolution import resolve_renewal_resolution


def renewal_due(*, now: datetime, paid_through: datetime, reminder_hours: int = 72) -> bool:
    return now.astimezone(UTC) >= paid_through.astimezone(UTC) - timedelta(hours=reminder_hours)


def resolve_renewal(*, now: datetime, paid_through: datetime, provider_status: str | None) -> str:
    return resolve_renewal_resolution(
        now=now,
        paid_through=paid_through,
        provider_status=provider_status,
    ).plan_code
