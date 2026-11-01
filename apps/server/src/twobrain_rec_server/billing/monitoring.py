"""Read-only inventory of declared billing sources; never a financial verdict."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import case, func, select

from twobrain_rec_server.billing.database import require_billing_maintenance_database
from twobrain_rec_server.billing.registry_store import GAPS, registry_status
from twobrain_rec_server.db.models.billing import (
    BillingInvoice,
    BillingNotificationDelivery,
    BillingOperation,
    BillingWebhookEvent,
)

OPERATION_KINDS = (
    "initial_checkout", "renewal", "storage_upgrade", "early_renewal",
    "storage_schedule", "resume_renewal",
)
OPERATION_STATES = (
    "scheduled", "provider_pending", "sent", "processing", "unknown",
    "reconciliation_gap", "manual_resolution", "observation_expired",
    "provider_key_expired", "succeeded", "succeeded_projected", "succeeded_refused",
    "canceled", "pending_reconciliation", "method_required", "failed",
)
READ_COMPATIBILITY_STATES = {"pending_reconciliation", "method_required", "failed"}
INVOICE_STATES = ("pending", "unknown", "succeeded", "canceled", "manual_resolution", "failed")
WEBHOOK_STATES = ("accepted", "pending_reconciliation", "reconciled", "reconciliation_gap")
DELIVERY_STATES = ("pending", "retry", "failed", "delivered", "suppressed")
MAX_GAPS = 500


class ReportLimitError(RuntimeError):
    """Fail whole rather than silently truncate sources."""


def _closed(column, values):
    return case((column.in_(values), column), else_="unrecognized")


async def _groups(db, model, states, as_of, *, time_name="created_at", kinds=()):
    table = model.__table__
    state = _closed(table.c.status if model is BillingInvoice else table.c.state, states)
    timestamp = table.c[time_name]
    invalid = timestamp.is_(None) | (timestamp > as_of)
    keys = [state.label("state")]
    if kinds:
        keys.append(_closed(table.c.kind, kinds).label("kind"))
    columns = [*keys, func.count().label("count"),
               func.min(timestamp).filter(~invalid).label("oldest_at"),
               func.count().filter(invalid).label("invalid_time_count")]
    if model is BillingNotificationDelivery:
        columns += [func.sum(table.c.attempts).label("stored_attempts"),
                    func.count().filter(table.c.attempts < 0).label("invalid_attempt_count")]
    return (await db.execute(select(*columns).group_by(*keys).order_by(*keys))).mappings().all()


def summarize(rows, as_of):
    """A queue's oldest age is a maximum, never a sum of group ages."""
    count = sum(row["count"] for row in rows)
    invalid = sum(row["invalid_time_count"] for row in rows)
    oldest = min((row["oldest_at"] for row in rows if row["oldest_at"] is not None), default=None)
    return {"count": count, "oldest_age_seconds": (
        int((as_of - oldest).total_seconds()) if oldest is not None and not invalid else None
    ), "invalid_time_count": invalid,
        "reason_code": "invalid_time" if invalid else "observed" if count else "empty"}


def _safe_groups(rows, as_of):
    return [{**{key: row[key] for key in ("state", "kind") if key in row},
             **summarize([row], as_of)} for row in rows]


def _source(source, values, *, reason="observed", scope="database_inventory"):
    return {"source": source, "scope": scope, "kind": "current_state",
            "coverage": "complete_declared_source" if reason == "observed" else "partial",
            "reason_code": reason, "values": values}


def _reason(rows, compatibility=()):
    if any(row["state"] == "unrecognized" or row.get("kind") == "unrecognized" for row in rows):
        return "unrecognized"
    if any(row["invalid_time_count"] for row in rows):
        return "invalid_time"
    if any(row["state"] in compatibility for row in rows):
        return "read_compatibility_state"
    if any(row.get("invalid_attempt_count", 0) for row in rows):
        return "invalid_attempt_count"
    return "observed"


async def _registry(db, scope, as_of):
    count = (await db.execute(select(func.count()).select_from(GAPS).where(
        GAPS.c.environment == scope["environment"], GAPS.c.shop_id == scope["shop_id"],
        GAPS.c.report_date == scope["report_date"], GAPS.c.state == "detected",
    ))).scalar_one()
    if count > MAX_GAPS:
        raise ReportLimitError
    raw = await registry_status(db, **scope)
    incomplete = raw["latest_accepted"] is None
    invalid_time_count = 0

    def timestamp(value):
        nonlocal incomplete, invalid_time_count
        if value is None:
            return None
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None or parsed > as_of:
            incomplete = True
            invalid_time_count += 1
            return None
        return parsed.isoformat()

    def receipt(value):
        if value is None:
            return None
        return {"accepted": value["accepted"], "files_complete": value["files_complete"],
                "created_at": timestamp(value["created_at"])}

    gaps = []
    for gap in raw["open_gaps"]:
        # Raw owner/IDs/digests/paths never cross the monitoring boundary.
        safe = {"owner": "owner_unverified", "state": "detected"}
        for key, allowed in (("kind", {"input", "payments", "refunds"}),
                             ("reason", {"missing_kind", "missing_last", "missing_part"}),
                             ("severity", {"high"}),
                             ("containment", {"report_unverified"})):
            safe[key] = gap[key] if gap[key] in allowed else "unrecognized"
            incomplete |= safe[key] == "unrecognized"
        safe["detected_at"] = timestamp(gap["detected_at"])
        safe["checked_at"] = timestamp(gap["checked_at"])
        # A future deadline is valid, unlike a future observation timestamp.
        deadline = datetime.fromisoformat(gap["deadline_at"])
        if deadline.tzinfo is None:
            raise ValueError("invalid timestamp schema")
        safe["deadline_at"] = deadline.isoformat()
        gaps.append(safe)
    values = {"last_attempt": receipt(raw["last_attempt"]),
              "latest_accepted": receipt(raw["latest_accepted"]),
              "financial_status": "not_checked", "detected_count": count, "detected_gaps": gaps,
              "invalid_time_count": invalid_time_count}
    return _source("registry_status", values, scope="proven_current_shop",
                   reason="invalid_time" if invalid_time_count else "unverified" if incomplete else "observed")


async def collect_billing_report(db, *, scope, as_of):
    """Caller owns the bounded READ ONLY REPEATABLE READ transaction."""
    await require_billing_maintenance_database(db)
    operations = await _groups(db, BillingOperation, OPERATION_STATES, as_of, kinds=OPERATION_KINDS)
    invoices = await _groups(db, BillingInvoice, INVOICE_STATES, as_of)
    webhooks = await _groups(db, BillingWebhookEvent, WEBHOOK_STATES, as_of, time_name="received_at")
    deliveries = await _groups(db, BillingNotificationDelivery, DELIVERY_STATES, as_of)
    operation_values = {**summarize(operations, as_of), "groups": _safe_groups(operations, as_of)}
    operation_reason = _reason(operations, READ_COMPATIBILITY_STATES)
    families = {
        "payment_state": _source("billing_operations,billing_invoices", {
            "operations": operation_values,
            "invoices": {**summarize(invoices, as_of), "groups": _safe_groups(invoices, as_of)},
            "bank_cancellation_reasons": None,
        }, reason=operation_reason if operation_reason != "observed" else _reason(invoices, {"failed"})),
        "operation_uncertainty": _source("billing_operations", {
            **operation_values, "unknown_duration_seconds": None,
        }, reason=operation_reason),
        "webhook_queue": _source("billing_webhook_events", {
            "groups": _safe_groups(webhooks, as_of),
            "queue": summarize([row for row in webhooks if row["state"] in {"accepted", "pending_reconciliation"}], as_of),
            "transport_lag_seconds": None,
        }, reason=_reason(webhooks)),
        "notifications": _source("billing_notification_deliveries", {
            "groups": _safe_groups(deliveries, as_of),
            "queue": summarize([row for row in deliveries if row["state"] in {"pending", "retry"}], as_of),
            "failed": summarize([row for row in deliveries if row["state"] == "failed"], as_of),
            "stored_attempts": sum(row["stored_attempts"] for row in deliveries),
            "invalid_attempt_count": sum(row["invalid_attempt_count"] for row in deliveries),
        }, reason=_reason(deliveries)),
        "registry": await _registry(db, scope, as_of),
    }
    for name in ("ingress_and_duplicates", "free_projection", "storage", "addon_and_time_credit",
                 "refunds_and_receipts", "deletion_and_fair_use"):
        families[name] = {"source": None, "scope": "unavailable", "kind": "current_state",
                          "coverage": "unavailable", "reason_code": (
                              "uninstrumented" if name == "ingress_and_duplicates" else "not_connected"
                          ), "values": None}
    return {"schema_version": 1, "coverage": "partial", "as_of": as_of.isoformat(),
            "report_date": scope["report_date"].isoformat(), "families": families}
