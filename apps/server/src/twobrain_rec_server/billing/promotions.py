from __future__ import annotations

import unicodedata
from dataclasses import dataclass


class PromoError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class PromoCode:
    code: str
    discount_percent: int
    plan_code: str
    max_redemptions: int
    redeemed: int = 0


def normalize_promo(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).strip().upper()
    if not normalized or len(normalized) > 48 or not all(char.isascii() and (char.isalnum() or char in "-_") for char in normalized):
        raise PromoError("Промокод не распознан")
    return normalized


def apply_promo(*, amount_minor: int, promo: PromoCode, plan_code: str, provider_floor_minor: int) -> int:
    if promo.plan_code != plan_code or promo.redeemed >= promo.max_redemptions:
        raise PromoError("Промокод недоступен для этого тарифа")
    if not 1 <= promo.discount_percent <= 100:
        raise PromoError("Промокод имеет неверные условия")
    discounted = amount_minor * (100 - promo.discount_percent) // 100
    if discounted < provider_floor_minor:
        raise PromoError("Скидка не может примениться к минимальной сумме платежа")
    return discounted
