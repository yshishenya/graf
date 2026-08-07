from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.db.models import BillingNotificationDelivery


class BillingNotification(StrEnum):
    TRIAL_ENDING = "trial_ending"
    PAYMENT_SUCCEEDED = "payment_succeeded"
    PAYMENT_FAILED = "payment_failed"
    STORAGE_THRESHOLD = "storage_threshold"
    RECEIPT_AVAILABLE = "receipt_available"
    REFERRAL_CREDIT = "referral_credit"
    RENEWAL_UNKNOWN = "renewal_unknown"


@dataclass(frozen=True, slots=True)
class NotificationEvent:
    event_id: str
    kind: BillingNotification
    safe_payload: dict[str, str]


@dataclass(frozen=True, slots=True)
class NotificationDelivery:
    event_id: str
    recipient_id: str
    channel: str
    state: str = "pending"


class NotificationOutbox:
    """Idempotent metadata-only outbox primitive; persistence is supplied by support outbox."""

    def __init__(self) -> None:
        self._rows: dict[tuple[str, str, str], NotificationDelivery] = {}

    def enqueue(
        self,
        event: NotificationEvent,
        *,
        recipient_id: str,
        channel: str = "email",
        marketing_allowed: bool = True,
    ) -> NotificationDelivery | None:
        if not recipient_id.strip() or channel not in {"email", "in_app"}:
            raise ValueError("notification recipient or channel is invalid")
        if channel == "email" and not marketing_allowed and event.kind not in {
            BillingNotification.PAYMENT_SUCCEEDED,
            BillingNotification.PAYMENT_FAILED,
            BillingNotification.RENEWAL_UNKNOWN,
        }:
            return None
        key = (event.event_id, recipient_id, channel)
        existing = self._rows.get(key)
        if existing is not None:
            return existing
        row = NotificationDelivery(event.event_id, recipient_id, channel)
        self._rows[key] = row
        return row

    def mark_delivered(self, *, event_id: str, recipient_id: str, channel: str) -> NotificationDelivery:
        key = (event_id, recipient_id, channel)
        row = self._rows[key]
        delivered = NotificationDelivery(row.event_id, row.recipient_id, row.channel, "delivered")
        self._rows[key] = delivered
        return delivered


class DurableNotificationOutbox:
    """Transactional DB outbox; the caller commits with the business mutation."""

    async def enqueue(
        self,
        db: AsyncSession,
        event: NotificationEvent,
        *,
        workspace_id: UUID,
        recipient_id: UUID,
        channel: str = "email",
        marketing_allowed: bool = True,
    ) -> BillingNotificationDelivery | None:
        if channel not in {"email", "in_app"}:
            raise ValueError("notification channel is invalid")
        if channel == "email" and not marketing_allowed and event.kind not in {
            BillingNotification.PAYMENT_SUCCEEDED,
            BillingNotification.PAYMENT_FAILED,
            BillingNotification.RENEWAL_UNKNOWN,
        }:
            return None
        row = await db.scalar(
            select(BillingNotificationDelivery)
            .where(
                BillingNotificationDelivery.workspace_id == workspace_id,
                BillingNotificationDelivery.event_id == event.event_id,
                BillingNotificationDelivery.recipient_id == recipient_id,
                BillingNotificationDelivery.channel == channel,
            )
            .with_for_update()
        )
        if row is not None:
            return row
        row = BillingNotificationDelivery(
            workspace_id=workspace_id,
            event_id=event.event_id,
            recipient_id=recipient_id,
            channel=channel,
            template_key=event.kind.value,
            state="pending",
            safe_payload=event.safe_payload,
        )
        db.add(row)
        await db.flush()
        return row

    async def mark_delivered(
        self,
        db: AsyncSession,
        *,
        workspace_id: UUID,
        event_id: str,
        recipient_id: UUID,
        channel: str,
    ) -> BillingNotificationDelivery:
        row = await db.scalar(
            select(BillingNotificationDelivery)
            .where(
                BillingNotificationDelivery.workspace_id == workspace_id,
                BillingNotificationDelivery.event_id == event_id,
                BillingNotificationDelivery.recipient_id == recipient_id,
                BillingNotificationDelivery.channel == channel,
            )
            .with_for_update()
        )
        if row is None:
            raise ValueError("notification delivery is missing")
        row.state = "delivered"
        row.delivered_at = datetime.now(UTC)
        return row


def notification_copy(event: NotificationEvent) -> tuple[str, str]:
    """Russian-first copy built only from allowlisted event fields."""
    invoice = event.safe_payload.get("invoice")
    suffix = f" Номер платежа: {invoice}." if invoice else ""
    copy = {
        BillingNotification.TRIAL_ENDING: ("Пробный период скоро закончится", "Выберите тариф, чтобы сохранить платную обработку."),
        BillingNotification.PAYMENT_SUCCEEDED: ("Платёж подтверждён", f"Оплата прошла успешно.{suffix}"),
        BillingNotification.PAYMENT_FAILED: ("Не удалось продлить подписку", "Платный доступ завершён, выбран бесплатный тариф."),
        BillingNotification.STORAGE_THRESHOLD: ("Заканчивается место", "Проверьте использование хранилища или увеличьте его ёмкость."),
        BillingNotification.RECEIPT_AVAILABLE: ("Чек доступен", "Откройте историю платежей, чтобы посмотреть чек."),
        BillingNotification.REFERRAL_CREDIT: ("Начислен реферальный бонус", "Дополнительные дни применены к вашему оплачиваемому периоду."),
        BillingNotification.RENEWAL_UNKNOWN: ("Проверяем продление", "Статус платежа пока неизвестен. Новое списание не создаём."),
    }
    return copy[event.kind]


def build_notification(*, event_id: str, kind: BillingNotification, payload: dict[str, object]) -> NotificationEvent:
    allowed_keys = {
        BillingNotification.PAYMENT_SUCCEEDED: {"invoice"},
        BillingNotification.PAYMENT_FAILED: {"invoice"},
        BillingNotification.RECEIPT_AVAILABLE: {"invoice"},
        BillingNotification.RENEWAL_UNKNOWN: {"invoice"},
        BillingNotification.TRIAL_ENDING: set(),
        BillingNotification.STORAGE_THRESHOLD: set(),
        BillingNotification.REFERRAL_CREDIT: set(),
    }[kind]
    safe: dict[str, str] = {}
    for key in allowed_keys:
        value = payload.get(key)
        if isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,79}", value):
            safe[key] = value
    return NotificationEvent(event_id, kind, safe)
