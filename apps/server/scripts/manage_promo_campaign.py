#!/usr/bin/env python3
"""Provision billing promo campaigns without retaining the raw code."""

from __future__ import annotations

import argparse
import asyncio
import getpass
import json
import sys
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.billing.promotions import PromoError, normalize_promo, promo_code_hash
from twobrain_rec_server.billing.storage import lock_storage_workspace
from twobrain_rec_server.config import Settings
from twobrain_rec_server.db.models import (
    BillingAcceptanceBudget,
    PromotionCampaign,
    Workspace,
    WorkspaceSubscription,
)
from twobrain_rec_server.db.session import create_engine, create_sessionmaker
from twobrain_rec_server.db.tenant_context import (
    MaintenanceTenantContext,
    maintenance_context_settings,
)

OPERATION_NAME = "billing_reconciliation"
ACTOR_ID = "manage_promo_campaign.py"


def _aware_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        raise PromoError("Дата кампании должна содержать часовой пояс", code="campaign_invalid")
    return value.astimezone(UTC)


def _validate_campaign_window(
    starts_at: datetime | None,
    ends_at: datetime | None,
) -> tuple[datetime | None, datetime | None]:
    starts = _aware_utc(starts_at)
    ends = _aware_utc(ends_at)
    if starts is None or ends is None:
        raise PromoError("Кампания должна иметь даты начала и окончания", code="campaign_invalid")
    if starts is not None and ends is not None and ends <= starts:
        raise PromoError(
            "Дата окончания кампании должна быть позже даты начала", code="campaign_invalid"
        )
    return starts, ends


def campaign_values_for_create(
    *,
    code: str,
    campaign_version: str,
    discount_percent: int,
    max_redemptions: int,
    cycle: str | None,
    starts_at: datetime | None,
    ends_at: datetime | None,
    purpose: str = "initial_checkout",
    acceptance_workspace: UUID | None = None,
    acceptance_limit_minor: int | None = None,
) -> dict[str, Any]:
    """Validate input and return ORM values without the raw code."""
    normalized = normalize_promo(code)
    if not campaign_version.strip() or len(campaign_version) > 64:
        raise PromoError("Версия кампании недействительна", code="campaign_invalid")
    if not 1 <= discount_percent <= 99:
        raise PromoError("Скидка должна быть от 1 до 99 процентов", code="campaign_invalid")
    if max_redemptions < 1:
        raise PromoError("Лимит применений должен быть положительным", code="campaign_invalid")
    if cycle not in {None, "month", "year"}:
        raise PromoError("Период кампании недействителен", code="campaign_invalid")
    starts, ends = _validate_campaign_window(starts_at, ends_at)
    if purpose not in {"initial_checkout", "storage_upgrade", "early_renewal"}:
        raise PromoError("Назначение кампании недействительно", code="campaign_invalid")
    if (acceptance_workspace is None) != (acceptance_limit_minor is None):
        raise PromoError(
            "Укажите проверочное пространство и общий бюджет вместе", code="campaign_invalid"
        )
    if acceptance_workspace is not None and (
        type(acceptance_limit_minor) is not int
        or not 100 <= acceptance_limit_minor <= 20000
        or max_redemptions != 1
        or ends - starts > timedelta(hours=24)
    ):
        raise PromoError(
            "Проверочная акция: одна покупка, окно до 24 часов, общий бюджет до 200 ₽",
            code="campaign_invalid",
        )
    return {
        "code_hash": promo_code_hash(normalized),
        "campaign_version": campaign_version.strip(),
        "plan_code": "personal",
        "cycle": cycle,
        "discount_percent": discount_percent,
        "max_redemptions": max_redemptions,
        "starts_at": starts,
        "ends_at": ends,
        "enabled": True,
        "policy_snapshot": {
            "source": "operator",
            "provisioning": "manage_promo_campaign.py",
            "purposes": [purpose],
            **(
                {
                    "workspace_id": str(acceptance_workspace),
                    "acceptance_limit_minor": acceptance_limit_minor,
                }
                if acceptance_workspace
                else {}
            ),
        },
    }


def safe_campaign_metadata(values: dict[str, Any], *, mode: str, action: str) -> dict[str, Any]:
    """Return output safe for logs and evidence; deliberately omits raw code."""
    return {
        "mode": mode,
        "action": action,
        "code_hash": values["code_hash"],
        "campaign_version": values["campaign_version"],
        "plan_code": values["plan_code"],
        "cycle": values["cycle"],
        "discount_percent": values["discount_percent"],
        "max_redemptions": values["max_redemptions"],
        "starts_at": values["starts_at"].isoformat() if values["starts_at"] else None,
        "ends_at": values["ends_at"].isoformat() if values["ends_at"] else None,
        "purpose": values["policy_snapshot"]["purposes"][0],
        "acceptance_limit_minor": values["policy_snapshot"].get("acceptance_limit_minor"),
    }


def _read_code(*, from_stdin: bool) -> str:
    value = sys.stdin.read() if from_stdin else getpass.getpass("Промокод (ввод скрыт): ")
    if not value.strip():
        raise PromoError("Промокод не задан", code="campaign_invalid")
    return value.strip()


def _maintenance_sessionmaker(
    base_sessionmaker: Callable[..., AsyncSession],
) -> Callable[..., AsyncSession]:
    context_settings = maintenance_context_settings(
        MaintenanceTenantContext(
            operation_name=OPERATION_NAME,
            actor_id=ACTOR_ID,
            reason_category="promo_campaign_provisioning",
            feature_area="billing",
        )
    )

    def sessionmaker(*args: Any, **kwargs: Any) -> AsyncSession:
        session = base_sessionmaker(*args, **kwargs)
        sync_session = getattr(session, "sync_session", session)
        sync_session.info["tenant_context"] = dict(context_settings)
        return session

    return sessionmaker


async def _run_create(args: argparse.Namespace, code: str) -> dict[str, Any]:
    values = campaign_values_for_create(
        code=code,
        campaign_version=args.campaign_version,
        discount_percent=args.discount_percent,
        max_redemptions=args.max_redemptions,
        cycle=args.cycle,
        starts_at=args.starts_at,
        ends_at=args.ends_at,
        purpose=getattr(args, "purpose", "initial_checkout"),
        acceptance_workspace=getattr(args, "acceptance_workspace", None),
        acceptance_limit_minor=getattr(args, "acceptance_limit_minor", None),
    )
    metadata = safe_campaign_metadata(
        values, mode="execute" if args.execute else "dry_run", action="create"
    )
    if not args.execute:
        return metadata
    settings = Settings()
    engine = create_engine(settings)
    sessionmaker = _maintenance_sessionmaker(create_sessionmaker(engine))
    try:
        async with sessionmaker() as db:
            acceptance_workspace = getattr(args, "acceptance_workspace", None)
            if acceptance_workspace is not None:
                await lock_storage_workspace(db, acceptance_workspace)
                workspace = await db.scalar(
                    select(Workspace).where(Workspace.id == acceptance_workspace).with_for_update()
                )
                if (
                    workspace is None
                    or workspace.kind != "personal"
                    or workspace.owner_user_id is None
                ):
                    raise PromoError(
                        "Нужно личное проверочное пространство", code="campaign_invalid"
                    )
                budget = await db.scalar(
                    select(BillingAcceptanceBudget)
                    .where(BillingAcceptanceBudget.workspace_id == acceptance_workspace)
                    .with_for_update()
                )
                if budget is None:
                    budget = BillingAcceptanceBudget(
                        workspace_id=acceptance_workspace,
                        limit_minor=args.acceptance_limit_minor,
                        enabled=True,
                        expires_at=values["ends_at"],
                    )
                    db.add(budget)
                    await db.flush()
                elif (
                    not budget.enabled
                    or budget.limit_minor != args.acceptance_limit_minor
                    or budget.expires_at < values["ends_at"]
                ):
                    raise PromoError(
                        "Бюджет закрыт или отличается; акция не может расширять лимит и окно",
                        code="campaign_invalid",
                    )
                values["policy_snapshot"]["acceptance_budget_id"] = str(budget.id)
            existing = await db.scalar(
                select(PromotionCampaign)
                .where(PromotionCampaign.code_hash == values["code_hash"])
                .with_for_update()
            )
            if existing is not None:
                raise PromoError("Кампания с таким кодом уже существует", code="campaign_exists")
            db.add(PromotionCampaign(**values))
            try:
                await db.commit()
            except IntegrityError as exc:
                await db.rollback()
                raise PromoError(
                    "Кампания с таким кодом уже существует", code="campaign_exists"
                ) from exc
    finally:
        await engine.dispose()
    return metadata


async def _run_disable(args: argparse.Namespace, code: str) -> dict[str, Any]:
    normalized = normalize_promo(code)
    values = {"code_hash": promo_code_hash(normalized)}
    metadata = {
        "mode": "execute" if args.execute else "dry_run",
        "action": "disable",
        "code_hash": values["code_hash"],
    }
    if not args.execute:
        return metadata
    settings = Settings()
    engine = create_engine(settings)
    sessionmaker = _maintenance_sessionmaker(create_sessionmaker(engine))
    try:
        async with sessionmaker() as db:
            campaign = await db.scalar(
                select(PromotionCampaign)
                .where(PromotionCampaign.code_hash == values["code_hash"])
                .with_for_update()
            )
            if campaign is None:
                raise PromoError("Кампания не найдена", code="campaign_missing")
            changed = campaign.enabled
            campaign.enabled = False
            await db.commit()
            metadata["changed"] = changed
    finally:
        await engine.dispose()
    return metadata


def _parse_timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("timestamp must be ISO-8601 with timezone") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise argparse.ArgumentTypeError("timestamp must include timezone")
    return parsed


def _add_code_input(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--code-stdin",
        action="store_true",
        help="read the raw code from stdin instead of the hidden interactive prompt",
    )
    parser.add_argument(
        "--execute", action="store_true", help="write the campaign; dry-run is the default"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Provision GRAF billing promo campaigns without logging raw codes"
    )
    subparsers = parser.add_subparsers(dest="action", required=True)
    create = subparsers.add_parser("create")
    _add_code_input(create)
    create.add_argument("--campaign-version", required=True)
    create.add_argument("--discount-percent", type=int, required=True)
    create.add_argument("--max-redemptions", type=int, required=True)
    create.add_argument("--cycle", choices=("month", "year"))
    create.add_argument("--starts-at", type=_parse_timestamp)
    create.add_argument("--ends-at", type=_parse_timestamp)
    create.add_argument(
        "--purpose",
        choices=("initial_checkout", "storage_upgrade", "early_renewal"),
        default="initial_checkout",
    )
    create.add_argument("--acceptance-workspace", type=UUID)
    create.add_argument("--acceptance-limit-minor", type=int)
    disable = subparsers.add_parser("disable")
    _add_code_input(disable)
    close = subparsers.add_parser("close-acceptance")
    close.add_argument("--workspace", type=UUID, required=True)
    close.add_argument("--execute", action="store_true")
    return parser.parse_args()


async def _run(args: argparse.Namespace) -> int:
    try:
        if args.action == "close-acceptance":
            result = await _close_acceptance(args)
        else:
            code = _read_code(from_stdin=args.code_stdin)
            result = await (
                _run_create(args, code) if args.action == "create" else _run_disable(args, code)
            )
    except (PromoError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


async def _close_acceptance(args: argparse.Namespace) -> dict[str, Any]:
    result = {"action": "close-acceptance", "mode": "execute" if args.execute else "dry_run"}
    if not args.execute:
        return result
    engine = create_engine(Settings())
    factory = _maintenance_sessionmaker(create_sessionmaker(engine))
    try:
        async with factory() as db:
            await lock_storage_workspace(db, args.workspace)
            workspace = await db.scalar(
                select(Workspace).where(Workspace.id == args.workspace).with_for_update()
            )
            budget = await db.scalar(
                select(BillingAcceptanceBudget)
                .where(BillingAcceptanceBudget.workspace_id == args.workspace)
                .with_for_update()
            )
            if workspace is None or budget is None:
                raise PromoError(
                    "Проверочное пространство с бюджетом не найдено", code="campaign_invalid"
                )
            budget.enabled = False
            campaigns = await db.scalars(
                select(PromotionCampaign)
                .where(
                    PromotionCampaign.policy_snapshot["acceptance_budget_id"].as_string()
                    == str(budget.id)
                )
                .with_for_update()
            )
            for campaign in campaigns:
                campaign.enabled = False
            subscription = await db.scalar(
                select(WorkspaceSubscription)
                .where(WorkspaceSubscription.workspace_id == args.workspace)
                .with_for_update()
            )
            if subscription and subscription.recurring_allowed:
                subscription.recurring_allowed = False
                subscription.recurring_authority_version += 1
                subscription.application_version += 1
            result.update(
                {
                    "spent_minor": budget.spent_minor,
                    "reserved_minor": budget.reserved_minor,
                    "unresolved_payments": budget.reserved_minor > 0,
                }
            )
            await db.commit()
    finally:
        await engine.dispose()
    return result


def main() -> None:
    raise SystemExit(asyncio.run(_run(parse_args())))


if __name__ == "__main__":
    main()
