"""Small, typed helpers used by the system-console catalog editor."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.billing.catalog import (
    CatalogNotApproved,
    validate_capabilities,
    validate_display_terms,
)


def validate_draft(
    *,
    code: str,
    display_name: str,
    capabilities: object,
    display_terms: object,
    monthly_amount_minor: int | None = None,
    annual_amount_minor: int | None = None,
) -> dict[str, Any]:
    """Validate a draft before it reaches the database trust boundary."""
    if not isinstance(code, str) or not code.isascii() or not code.islower() or not code.replace("_", "").isalnum():
        raise CatalogNotApproved("invalid plan code")
    if not 3 <= len(code) <= 32 or not code[0].isalpha():
        raise CatalogNotApproved("invalid plan code")
    if not isinstance(display_name, str) or not 1 <= len(display_name.strip()) <= 80:
        raise CatalogNotApproved("invalid plan name")
    caps = validate_capabilities(capabilities)
    terms = validate_display_terms(display_terms)
    for amount in (monthly_amount_minor, annual_amount_minor):
        if amount is not None and (type(amount) is not int or not 0 < amount <= 9_000_000_000_000_000):
            raise CatalogNotApproved("invalid plan price")
    return {
        "code": code,
        "display_name": display_name.strip(),
        "capabilities": caps,
        "display_terms": terms,
        "monthly_amount_minor": monthly_amount_minor,
        "annual_amount_minor": annual_amount_minor,
    }


async def list_plans(db: AsyncSession, *, after: UUID | None = None) -> list[dict[str, Any]]:
    result = await db.scalar(text("select system_control.list_catalog_plans(:after)"), {"after": after})
    if result is None:
        raise PermissionError("catalog.read required")
    return list(result)


async def create_plan(db: AsyncSession, values: dict[str, Any]) -> dict[str, Any]:
    validated = validate_draft(**values)
    return dict(await db.scalar(text("""select system_control.create_catalog_plan(
        :code,:name,cast(:capabilities as jsonb),cast(:terms as jsonb),:month,:year)"""), {
            "code": validated["code"], "name": validated["display_name"],
            "capabilities": json.dumps(validated["capabilities"]),
            "terms": json.dumps(validated["display_terms"]),
            "month": validated["monthly_amount_minor"], "year": validated["annual_amount_minor"],
        }) or {})


async def publish_plan(db: AsyncSession, *, plan_id: UUID, version_id: UUID) -> dict[str, Any]:
    return dict(await db.scalar(text("select system_control.publish_catalog_plan(:plan,:version)"), {
        "plan": plan_id, "version": version_id,
    }) or {})


async def set_plan_state(db: AsyncSession, *, plan_id: UUID, state: str) -> dict[str, Any]:
    return dict(await db.scalar(text("select system_control.set_catalog_plan_state(:plan,:state)"), {
        "plan": plan_id, "state": state,
    }) or {})


def new_idempotency_key() -> str:
    return str(uuid4())


def utc_now() -> datetime:
    return datetime.now(UTC)
