"""Read-only inventory of declared billing sources; never a financial verdict."""
from __future__ import annotations

from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import JSON, Text, case, column, func, literal, select, true

from twobrain_rec_server.billing.database import require_billing_maintenance_database
from twobrain_rec_server.billing.purchases import effective_paid_storage
from twobrain_rec_server.billing.registry_store import GAPS, registry_status
from twobrain_rec_server.billing.storage import (
    _active_reserved_bytes,
    project_active_playback_storage,
)
from twobrain_rec_server.db.models.billing import (
    BillingAuditEvent,
    BillingInvoice,
    BillingNotificationDelivery,
    BillingOperation,
    BillingWebhookEvent,
    FairUseReviewRecord,
    ObservedProviderRefund,
    StorageReservation,
    TimeCreditLedgerEntry,
    WorkspaceSubscription,
)
from twobrain_rec_server.db.models.deletion import MeetingDeletionRequest
from twobrain_rec_server.db.models.identity import Workspace

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
CREDIT_STATES = ("pending", "available", "applied", "expired", "rejected", "reversed")
FAIR_USE_STATES = ("notice", "restricted", "appealed", "cleared", "confirmed")
DELETION_STATES = ("requested", "deleting", "active_purge_complete", "retryable_failed")
MAX_GAPS = 500
MAX_STORAGE_WORKSPACES = 500


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


async def _free_projection(db, report_date, as_of):
    """Visible cutoff audit rows, not all Free transitions or a commit watermark."""
    window = {"timezone": "Europe/Moscow", "start": None, "end": None,
              "observed_until": None, "calendar_day_elapsed": None}
    result = {"source": "billing_audit_events", "scope": "database_inventory", "kind": "event_window",
              "coverage": "unavailable", "reason_code": "calendar_boundary_unrepresentable",
              "values": None, "window": window}
    try:
        zone = ZoneInfo(window["timezone"])
        start = datetime.combine(report_date, time.min, zone).astimezone(UTC)
        end = datetime.combine(report_date + timedelta(days=1), time.min, zone).astimezone(UTC)
    except (OverflowError, ValueError):
        return result
    window.update(start=start.isoformat(), end=end.isoformat(), calendar_day_elapsed=end <= as_of)
    if start > as_of:
        result["reason_code"] = "window_not_started"
        return result
    until = min(end, as_of)
    window["observed_until"] = until.isoformat()
    table = BillingAuditEvent.__table__.c
    action = table.action == "renewal.cutoff_projected_free"
    known = (table.target_kind == "workspace_subscription") & (
        ((table.outcome == "blocked") & (table.reason_code == "workspace_scope_invalid"))
        | ((table.outcome == "projected") & table.reason_code.in_(("unknown_pending", "renewal_not_confirmed")))
    )
    outcome = case((known, table.outcome), else_="unrecognized").label("outcome")
    reason = case((known, table.reason_code), else_="unrecognized").label("reason_code")
    groups = [dict(row) for row in (await db.execute(select(
        outcome, reason, func.count().label("count"),
    ).where(action, table.created_at >= start, table.created_at < until)
        .group_by(outcome, reason).order_by(outcome, reason))).mappings().all()]
    undated, after = (await db.execute(select(
        func.count().filter(table.created_at.is_(None)),
        func.count().filter((table.created_at >= start) & (table.created_at < end) & (table.created_at >= as_of)),
    ).where(action))).one()
    count = sum(group["count"] for group in groups)
    reason_code = (
        "unrecognized" if any(group["outcome"] == "unrecognized" for group in groups) else
        "undated_time" if undated else "at_or_after_as_of" if after else
        "window_open" if as_of < end else "observed" if count else "empty"
    )
    result.update(coverage="complete_declared_source" if reason_code in {"observed", "empty"} else "partial",
                  reason_code=reason_code, values={"count": count, "groups": groups,
                  "undated_count": undated, "undated_count_scope": "database_inventory",
                  "at_or_after_as_of_count": after})
    return result


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


async def _credit_ledger(db, as_of):
    """Stored service-credit rows and dates, never job health or financial eligibility."""
    table = TimeCreditLedgerEntry.__table__.c
    state = _closed(table.state, CREDIT_STATES).label("state")
    pending = table.state.in_(("pending", "available"))
    invalid = table.maturity_at.is_(None) | table.expires_at.is_(None) | (table.expires_at <= table.maturity_at)
    reached = pending & ~invalid & (table.maturity_at <= as_of) & (table.expires_at > as_of)
    filters = {
        "invalid_schedule_count": pending & invalid,
        "expiry_reached_count": pending & ~invalid & (table.expires_at <= as_of),
        "maturity_reached_unexpired_count": reached,
        "waiting_count": pending & ~invalid & (table.maturity_at > as_of),
    }
    rows = (await db.execute(select(
        state, func.count().label("count"),
        *[func.count().filter(condition).label(name) for name, condition in filters.items()],
        func.min(table.maturity_at).filter(reached).label("oldest_maturity_at"),
    ).group_by(state).order_by(state))).mappings().all()
    oldest = min((row["oldest_maturity_at"] for row in rows if row["oldest_maturity_at"] is not None), default=None)
    summary = {"count": sum(row["count"] for row in rows if row["state"] in {"pending", "available"}),
               **{name: sum(row[name] for row in rows) for name in filters},
               "oldest_maturity_reached_age_seconds": (as_of - oldest) // timedelta(seconds=1) if oldest is not None else None}
    reason = ("unrecognized" if any(row["state"] == "unrecognized" for row in rows) else
              "invalid_schedule" if summary["invalid_schedule_count"] else "jobs_uninstrumented")
    return _source("time_credit_ledger_entries", {
        "count": sum(row["count"] for row in rows),
        "groups": [{"state": row["state"], "count": row["count"]} for row in rows],
        "pending_or_available": summary,
        "addon_jobs": None, "job_attempts": None, "job_errors": None, "job_retries": None,
    }, reason=reason)


async def _receipt_inventory(db):
    """Stored JSON entries, never unique receipts, pending age or delivery proof."""
    table = BillingInvoice.__table__
    snapshot = table.c.plan_snapshot
    root_object = func.coalesce(func.json_typeof(snapshot) == "object", False)
    observations = snapshot["receipt_observations"]
    map_type = func.json_typeof(observations)
    missing = root_object & (map_type.is_(None) | (map_type == "null"))
    invalid = ~root_object | (root_object & map_type.not_in(("object", "null")))
    invoices, missing_count, invalid_count = (await db.execute(select(
        func.count(), func.count().filter(missing), func.count().filter(invalid),
    ).select_from(table))).one()
    safe_map = case((root_object & (map_type == "object"), observations), else_=literal({}, type_=JSON))
    entries = func.json_each(safe_map).table_valued(column("key", Text), column("value", JSON)).lateral()
    fields = {name: entries.c.value[name] for name in ("parent_kind", "status", "source")}
    known = func.json_typeof(entries.c.value) == "object"
    for name, allowed in (("parent_kind", ("payment", "refund")),
                          ("status", ("pending", "succeeded", "canceled")),
                          ("source", ("webhook", "poll", "registry"))):
        known = known & (func.json_typeof(fields[name]) == "string") & fields[name].as_string().in_(allowed)
    keys = [case((known, value.as_string()), else_="unrecognized").label(name) for name, value in fields.items()]
    groups = [dict(row) for row in (await db.execute(select(
        *keys, func.count().label("count"),
    ).select_from(table.join(entries, true())).group_by(*keys).order_by(*keys))).mappings().all()]
    reason = ("unrecognized" if any(group["parent_kind"] == "unrecognized" for group in groups) else
              "invalid_container" if invalid_count else "missing_observations" if missing_count else
              "timing_and_reconciliation_uninstrumented")
    return _source("billing_invoices.plan_snapshot.receipt_observations", {
        "invoice_count": invoices, "missing_map_count": missing_count, "invalid_container_count": invalid_count,
        "count": sum(group["count"] for group in groups), "groups": groups,
        "pending_age_seconds": None, "escalation_due": None,
    }, reason=reason)


async def _refund_inventory(db):
    """Stored refund rows and receipt entries, without timing or reconciliation claims."""
    table = ObservedProviderRefund.__table__.c
    known = (table.status == "succeeded") & (table.source == "provider_observation")
    status = case((known, "succeeded"), else_="unrecognized").label("status")
    groups = [dict(row) for row in (await db.execute(select(
        status, func.count().label("count"),
    ).group_by(status).order_by(status))).mappings().all()]
    receipts = await _receipt_inventory(db)
    reason = ("unrecognized" if any(row["status"] == "unrecognized" for row in groups) else
              receipts["reason_code"] if receipts["reason_code"] != "timing_and_reconciliation_uninstrumented" else
              "reconciliation_uninstrumented")
    return _source("observed_provider_refunds,billing_invoices.plan_snapshot.receipt_observations", {
        "count": sum(row["count"] for row in groups), "groups": groups,
        "receipts": receipts, "reconciliation_gaps": None,
    }, reason=reason)


async def _deletion_inventory(db):
    """Stored request states, never proof of artifact purge or deadline compliance."""
    state = _closed(MeetingDeletionRequest.__table__.c.state, DELETION_STATES).label("state")
    groups = [dict(row) for row in (await db.execute(select(
        state, func.count().label("count"),
    ).group_by(state).order_by(state))).mappings().all()]
    return _source("meeting_deletion_requests", {
        "count": sum(row["count"] for row in groups), "groups": groups,
        "artifact_completion": None, "deadline_status": None,
        "job_attempts": None, "job_errors": None, "job_retries": None,
    }, reason="unrecognized" if any(row["state"] == "unrecognized" for row in groups) else
        "artifact_and_deadline_uninstrumented")


async def _fair_use_inventory(db, as_of):
    """Stored review schedules, without claiming cleared restrictions or incident closure."""
    table = FairUseReviewRecord.__table__.c
    state = _closed(table.state, FAIR_USE_STATES).label("state")
    pending = table.state.in_(("notice", "restricted", "appealed"))
    invalid = case((table.starts_at.is_(None) | table.review_by.is_(None)
                    | ~func.isfinite(table.starts_at) | ~func.isfinite(table.review_by), True),
                   else_=(table.review_by < table.starts_at)
                   | (func.extract("epoch", table.review_by) - func.extract("epoch", table.starts_at) > 86400))
    bucket = case((invalid, "invalid_schedule_count"),
                  (table.starts_at > as_of, "not_started_count"),
                  (table.review_by <= as_of, "deadline_reached_count"), else_="waiting_count")
    names = ("invalid_schedule_count", "not_started_count", "deadline_reached_count", "waiting_count")
    rows = (await db.execute(select(
        state, func.count().label("count"),
        *[func.count().filter(pending & (bucket == name)).label(name) for name in names],
    ).group_by(state).order_by(state))).mappings().all()
    summary = {"count": sum(row["count"] for row in rows if row["state"] in {"notice", "restricted", "appealed"}),
               **{name: sum(row[name] for row in rows) for name in names}}
    deletion = await _deletion_inventory(db)
    reason = ("unrecognized" if any(row["state"] == "unrecognized" for row in rows)
              or deletion["reason_code"] == "unrecognized" else
              "invalid_schedule" if summary["invalid_schedule_count"] else "deletion_details_and_reaction_uninstrumented")
    return _source("fair_use_reviews,meeting_deletion_requests", {
        "count": sum(row["count"] for row in rows),
        "groups": [{"state": row["state"], "count": row["count"]} for row in rows],
        "pending_review": summary, "deletion": deletion, "reaction": None,
    }, reason=reason)


async def _storage_inventory(db, as_of):
    """Existing byte projections over a bounded snapshot, not object or financial reconciliation."""
    table = StorageReservation.__table__.c
    state = _closed(table.state, ("active", "committed", "released")).label("state")
    invalid = (table.declared_bytes.is_(None) | (table.declared_bytes <= 0)
               | table.committed_bytes.is_(None) | (table.committed_bytes < 0)
               | (table.committed_bytes > table.declared_bytes)
               | (table.expires_at.is_not(None) & ~func.isfinite(table.expires_at)))
    expired = ((table.state == "active") & func.isfinite(table.expires_at) & (table.expires_at <= as_of))
    rows = (await db.execute(select(
        state, func.count().label("count"),
        func.count().filter(invalid).label("invalid_value_count"),
        func.count().filter(expired).label("expired_active_count"),
    ).group_by(state).order_by(state))).mappings().all()
    reservations = {"count": sum(row["count"] for row in rows),
                    "groups": [{"state": row["state"], "count": row["count"]} for row in rows],
                    "expired_active_count": sum(row["expired_active_count"] for row in rows),
                    "invalid_value_count": sum(row["invalid_value_count"] for row in rows)}
    subscription = WorkspaceSubscription.__table__.c
    workspaces = Workspace.__table__
    invalid_time = case(
        (subscription.plan_code == "trial", subscription.trial_ends_at.is_not(None) & ~func.isfinite(subscription.trial_ends_at)),
        (subscription.plan_code == "personal", subscription.paid_through.is_not(None) & ~func.isfinite(subscription.paid_through)),
        else_=False,
    )
    # Never decode PostgreSQL infinities into Python datetime, including unused dates.
    inventory = (await db.execute(select(
        workspaces.c.id.label("workspace_id"), subscription.plan_code, subscription.capacity_bytes,
        case((func.isfinite(subscription.paid_through), subscription.paid_through)).label("paid_through"),
        case((func.isfinite(subscription.trial_ends_at), subscription.trial_ends_at)).label("trial_ends_at"),
        subscription.workspace_id.is_not(None).label("subscription_present"),
        invalid_time.label("invalid_capacity_time"),
    ).select_from(workspaces.outerjoin(WorkspaceSubscription.__table__, workspaces.c.id == subscription.workspace_id))
        .limit(MAX_STORAGE_WORKSPACES + 1))).all()
    if len(inventory) > MAX_STORAGE_WORKSPACES:
        raise ReportLimitError
    totals = {"used_bytes": 0, "reserved_bytes": 0, "capacity_bytes": 0}
    unavailable = unknown = bad_time = 0
    for row in inventory:
        if not row.subscription_present:
            unavailable += 1
            continue
        if row.plan_code not in {"free", "trial", "personal"}:
            unknown += 1
            unavailable += 1
            continue
        if row.invalid_capacity_time:
            bad_time += 1
            unavailable += 1
            continue
        capacity = await effective_paid_storage(db, subscription=row, now=as_of)
        if capacity <= 0:
            unavailable += 1
            continue
        reserved = await _active_reserved_bytes(db, workspace_id=row.workspace_id, now=as_of)
        projection = await project_active_playback_storage(
            db, workspace_id=row.workspace_id, capacity_bytes=capacity, reserved_bytes=reserved,
        )
        for key in totals:
            totals[key] += getattr(projection, key)
    unrecognized = unknown or any(row["state"] == "unrecognized" for row in rows)
    if unavailable or unrecognized or reservations["invalid_value_count"]:
        totals = dict.fromkeys(totals)
    reason = ("unrecognized" if unrecognized else "invalid_storage_values" if reservations["invalid_value_count"] else
              "capacity_unavailable" if unavailable else "reconciliation_uninstrumented")
    return _source(
        "workspaces,workspace_subscriptions,effective_paid_storage,storage_reservations,track_artifacts,upload_sessions", {
            "workspace_count": len(inventory), "capacity_unavailable_workspace_count": unavailable,
            "unrecognized_plan_count": unknown, "invalid_capacity_time_count": bad_time,
            **totals, "reservations": reservations, "reconciliation_gaps": None,
        }, reason=reason,
    )


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
        "free_projection": await _free_projection(db, scope["report_date"], as_of),
        "addon_and_time_credit": await _credit_ledger(db, as_of),
        "refunds_and_receipts": await _refund_inventory(db),
        "deletion_and_fair_use": await _fair_use_inventory(db, as_of),
        "storage": await _storage_inventory(db, as_of),
    }
    families["ingress_and_duplicates"] = {
        "source": None, "scope": "unavailable", "kind": "current_state",
        "coverage": "unavailable", "reason_code": "uninstrumented", "values": None,
    }
    return {"schema_version": 1, "coverage": "partial", "as_of": as_of.isoformat(),
            "report_date": scope["report_date"].isoformat(), "families": families}
