"""Administrative campaign helpers with one-time plaintext code delivery."""

from __future__ import annotations

import json
import secrets
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.billing.promotions import normalize_promo, promo_code_hash


def generate_codes(count: int, *, prefix: str = "GRAF") -> list[tuple[str, str]]:
    if type(count) is not int or not 1 <= count <= 1000:
        raise ValueError("количество кодов должно быть от 1 до 1000")
    normalized_prefix = normalize_promo(prefix)
    result: list[tuple[str, str]] = []
    for _ in range(count):
        # token_urlsafe is reduced to the same ASCII alphabet accepted by the
        # checkout normalizer; collisions are rejected by the database.
        code = f"{normalized_prefix}-{secrets.token_hex(8).upper()}"
        result.append((code, promo_code_hash(code)))
    return result


async def list_campaigns(db: AsyncSession, *, after: UUID | None = None) -> list[dict[str, Any]]:
    result = await db.scalar(text("select system_control.list_campaigns(:after)"), {"after": after})
    if result is None:
        raise PermissionError("promotions.read required")
    return list(result)


async def create_campaign(db: AsyncSession, *, code: str, campaign_version: str,
                          plan_code: str, cycle: str | None, benefit_kind: str,
                          discount_percent: int | None, gift_days: int | None,
                          audience: str, target_user_id: UUID | None, max_redemptions: int,
                          budget_minor: int | None, starts_at: datetime | None,
                          ends_at: datetime | None, display_name: str | None) -> dict[str, Any]:
    normalized = normalize_promo(code)
    if benefit_kind == "discount":
        if type(discount_percent) is not int or not 1 <= discount_percent <= 99:
            raise ValueError("скидка должна быть от 1 до 99 процентов")
        gift_days = None
    elif benefit_kind == "gift":
        if type(gift_days) is not int or not 1 <= gift_days <= 365:
            raise ValueError("подарочный период должен быть от 1 до 365 дней")
        discount_percent = 0
    else:
        raise ValueError("неизвестный тип акции")
    if cycle not in (None, "month", "year") or type(max_redemptions) is not int or not 1 <= max_redemptions <= 1_000_000:
        raise ValueError("условия акции недействительны")
    if budget_minor is not None and (type(budget_minor) is not int or budget_minor <= 0):
        raise ValueError("бюджет акции недействителен")
    if starts_at and starts_at.tzinfo is None or ends_at and ends_at.tzinfo is None:
        raise ValueError("время акции должно содержать часовой пояс")
    result = await db.scalar(text("""select system_control.create_promotion_campaign(
      :hash,:version,:plan,:cycle,:kind,:discount,:gift,:audience,:target,:max,:budget,:starts,:ends,:name)"""), {
        "hash": promo_code_hash(normalized), "version": campaign_version.strip(), "plan": plan_code,
        "cycle": cycle, "kind": benefit_kind, "discount": discount_percent, "gift": gift_days,
        "audience": audience, "target": target_user_id, "max": max_redemptions, "budget": budget_minor,
        "starts": starts_at.astimezone(UTC) if starts_at else None,
        "ends": ends_at.astimezone(UTC) if ends_at else None, "name": display_name,
    })
    return dict(result or {})


async def issue_codes(db: AsyncSession, *, campaign_id: UUID, idempotency_key: str,
                      count: int, prefix: str = "GRAF", target_user_ids: list[UUID | None] | None = None) -> dict[str, Any]:
    generated = generate_codes(count, prefix=prefix)
    if target_user_ids is None:
        target_user_ids = [None] * count
    if len(target_user_ids) != count:
        raise ValueError("число адресатов должно совпадать с числом кодов")
    result = await db.scalar(text("select system_control.issue_promotion_codes(:campaign,:key,cast(:hashes as jsonb),cast(:targets as jsonb))"), {
        "campaign": campaign_id, "key": idempotency_key,
        "hashes": json.dumps([item[1] for item in generated]),
        "targets": json.dumps([str(item) if item else None for item in target_user_ids]),
    })
    result = dict(result or {})
    if result.get("duplicate"):
        # Plaintext is intentionally not recoverable after a lost response.
        return {key: value for key, value in result.items() if key not in {"code_ids"}}
    if result.get("error"):
        return result
    result["codes"] = [code for code, _ in generated]
    return result
