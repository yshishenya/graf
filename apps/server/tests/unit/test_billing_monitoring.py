import asyncio
from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from twobrain_rec_server.billing.monitoring import ReportLimitError, summarize
from twobrain_rec_server.cli.billing_monitoring import build_parser, serialize
from twobrain_rec_server.readiness.checks import (
    billing_readiness_status,
)


def test_oldest_age_is_maximum_and_future_is_unknown() -> None:
    now = datetime(2026, 11, 1, tzinfo=UTC)
    rows = [{"count": 2, "oldest_at": now - timedelta(seconds=60), "invalid_time_count": 0},
            {"count": 1, "oldest_at": now - timedelta(seconds=120), "invalid_time_count": 0}]
    assert summarize(rows, now)["oldest_age_seconds"] == 120
    assert summarize(rows, now)["count"] == 3
    rows[1]["invalid_time_count"] = 1
    assert summarize(rows, now)["oldest_age_seconds"] is None
    assert summarize(rows, now)["reason_code"] == "invalid_time"
    assert summarize([], now) == {"count": 0, "oldest_age_seconds": None,
                                  "invalid_time_count": 0, "reason_code": "empty"}


def test_output_limit_is_utf8_bytes_including_newline() -> None:
    with pytest.raises(ReportLimitError):
        serialize({"value": "я" * 32768})


@pytest.mark.parametrize("arguments", [[], ["--date", "private-input"],
                                      ["--date", "20261031"], ["--date", "2026-W44-6"],
                                      ["--date", "2026-10-31", "--private-input"]])
def test_parser_never_echoes_invalid_input(arguments, capsys) -> None:
    with pytest.raises(SystemExit) as error:
        build_parser().parse_args(arguments)
    assert error.value.code == 2
    assert capsys.readouterr().err == '{"schema_version": 1, "result_code": "invalid_arguments"}\n'


def test_billing_readiness_status_is_bounded_and_health_safe() -> None:
    assert billing_readiness_status(checkout_enabled=False) == "disabled"
    assert billing_readiness_status(checkout_enabled=True) == "ready"


@pytest.mark.parametrize("day,reason", [
    (date.min, "calendar_boundary_unrepresentable"),
    (date.max, "calendar_boundary_unrepresentable"),
    (date(2026, 11, 2), "window_not_started"),
])
def test_free_projection_unavailable_window_never_queries(day, reason):
    from twobrain_rec_server.billing.monitoring import _free_projection

    db = AsyncMock()
    result = asyncio.run(_free_projection(db, day, datetime(2026, 11, 1, tzinfo=UTC)))
    assert result["kind"] == "event_window" and result["scope"] == "database_inventory"
    assert result["coverage"] == "unavailable" and result["reason_code"] == reason
    assert result["values"] is None and result["window"]["observed_until"] is None
    assert result["window"]["timezone"] == "Europe/Moscow"
    assert result["window"]["calendar_day_elapsed"] is (
        False if reason == "window_not_started" else None)
    if reason == "calendar_boundary_unrepresentable":
        assert result["window"]["start"] is result["window"]["end"] is None
    db.execute.assert_not_awaited()


def test_free_projection_historical_midnights_and_private_columns():
    from twobrain_rec_server.billing.monitoring import _free_projection

    response = MagicMock()
    response.mappings.return_value.all.return_value = []
    response.one.return_value = (0, 0)
    db = AsyncMock()
    db.execute.return_value = response
    result = asyncio.run(_free_projection(db, date(2014, 10, 26), datetime(2026, 11, 1, tzinfo=UTC)))
    window = result["window"]
    assert window == {"timezone": "Europe/Moscow", "start": "2014-10-25T20:00:00+00:00",
                      "end": "2014-10-26T21:00:00+00:00", "observed_until": "2014-10-26T21:00:00+00:00",
                      "calendar_day_elapsed": True}
    assert result["reason_code"] == "empty" and result["coverage"] == "complete_declared_source"
    for call in db.execute.await_args_list:
        sql = str(call.args[0]).lower()
        for private in ("metadata_json", "target_ref", "workspace_id", "actor_user_id", "billing_audit_events.id"):
            assert private not in sql


def test_credit_ledger_empty_and_private_column_projection():
    from twobrain_rec_server.billing.monitoring import _credit_ledger

    response = MagicMock()
    response.mappings.return_value.all.return_value = []
    db = AsyncMock(execute=AsyncMock(return_value=response))
    result = asyncio.run(_credit_ledger(db, datetime(2026, 11, 1, tzinfo=UTC)))
    assert result == {
        "source": "time_credit_ledger_entries", "scope": "database_inventory", "kind": "current_state",
        "coverage": "partial", "reason_code": "jobs_uninstrumented",
        "values": {"count": 0, "groups": [], "pending_or_available": {
            "count": 0, "invalid_schedule_count": 0, "expiry_reached_count": 0,
            "maturity_reached_unexpired_count": 0, "waiting_count": 0,
            "oldest_maturity_reached_age_seconds": None,
        }, "addon_jobs": None, "job_attempts": None, "job_errors": None, "job_retries": None},
    }
    db.execute.assert_awaited_once()
    sql = str(db.execute.await_args.args[0]).lower()
    assert "maturity_at is null" in sql and "expires_at is null" in sql
    for private in ("days", "source_ref", ".id", "workspace_id", "referral_attribution_id",
                    "capacity_snapshot_bytes", "applied_start", "applied_end", "reversal_of_id"):
        assert private not in sql


@pytest.mark.parametrize("unknown,invalid,reason", [
    (False, 0, "jobs_uninstrumented"), (False, 2, "invalid_schedule"), (True, 2, "unrecognized"),
])
def test_credit_ledger_reason_precedence_and_maximum_age(unknown, invalid, reason):
    from twobrain_rec_server.billing.monitoring import _credit_ledger

    now = datetime(2026, 11, 1, tzinfo=UTC)
    rows = [{"state": state, "count": 4 + invalid, "invalid_schedule_count": invalid,
             "expiry_reached_count": 1, "maturity_reached_unexpired_count": 2, "waiting_count": 1,
             "oldest_maturity_at": now - timedelta(seconds=age)}
            for state, age in (("available", 120.9), ("pending", 60.5))]
    if unknown:
        rows.append({"state": "unrecognized", "count": 1, "invalid_schedule_count": 0,
                     "expiry_reached_count": 0, "maturity_reached_unexpired_count": 0,
                     "waiting_count": 0, "oldest_maturity_at": None})
    response = MagicMock()
    response.mappings.return_value.all.return_value = rows
    db = AsyncMock(execute=AsyncMock(return_value=response))
    result = asyncio.run(_credit_ledger(db, now))
    assert result["coverage"] == "partial" and result["reason_code"] == reason
    values = result["values"]
    assert values["count"] == sum(group["count"] for group in values["groups"])
    assert [group["state"] for group in values["groups"]] == sorted(row["state"] for row in rows)
    pending = values["pending_or_available"]
    assert pending == {"count": 8 + 2 * invalid, "invalid_schedule_count": 2 * invalid,
                       "expiry_reached_count": 2, "maturity_reached_unexpired_count": 4,
                       "waiting_count": 2, "oldest_maturity_reached_age_seconds": 120}
    rows[0]["oldest_maturity_at"] = datetime.min.replace(tzinfo=UTC) + timedelta(microseconds=1)
    extreme = asyncio.run(_credit_ledger(db, datetime.max.replace(tzinfo=UTC)))
    assert extreme["values"]["pending_or_available"]["oldest_maturity_reached_age_seconds"] == 315537897599


@pytest.mark.parametrize("rows,reason", [
    ([], "missing_observations"),
    ([{"status": "succeeded", "count": 2}], "missing_observations"),
    ([{"status": "succeeded", "count": 2}, {"status": "unrecognized", "count": 3}], "unrecognized"),
])
def test_refund_inventory_closed_projection_and_incomplete_sources(rows, reason, monkeypatch):
    from twobrain_rec_server.billing import monitoring
    from twobrain_rec_server.billing.monitoring import _refund_inventory

    receipts = {"reason_code": "missing_observations", "coverage": "partial"}
    monkeypatch.setattr(monitoring, "_receipt_inventory", AsyncMock(return_value=receipts))

    response = MagicMock()
    response.mappings.return_value.all.return_value = rows
    db = AsyncMock(execute=AsyncMock(return_value=response))
    result = asyncio.run(_refund_inventory(db))
    assert result == {
        "source": "observed_provider_refunds,billing_invoices.plan_snapshot.receipt_observations",
        "scope": "database_inventory", "kind": "current_state",
        "coverage": "partial", "reason_code": reason,
        "values": {"count": sum(row["count"] for row in rows), "groups": rows,
                   "receipts": receipts, "reconciliation_gaps": None},
    }
    db.execute.assert_awaited_once()
    statement = db.execute.await_args.args[0]
    sql = str(statement).lower()
    assert "case when" in sql and "status =" in sql and "source =" in sql and "else" in sql
    assert statement.compile().params == {
        "status_1": "succeeded", "source_1": "provider_observation", "param_1": "succeeded",
        "param_2": "unrecognized",
    }
    for private in (".id", "workspace_id", "invoice_id", "provider_refund_id", "amount_minor",
                    "currency", "shop_environment", "observed_at", "plan_snapshot"):
        assert private not in sql


@pytest.mark.parametrize("unknown,invalid,missing,reason", [
    (False, 0, 0, "timing_and_reconciliation_uninstrumented"),
    (False, 0, 2, "missing_observations"),
    (False, 1, 2, "invalid_container"),
    (True, 1, 2, "unrecognized"),
])
def test_receipt_inventory_counts_priorities_and_closed_sql(unknown, invalid, missing, reason):
    from twobrain_rec_server.billing.monitoring import _receipt_inventory

    containers, entries = MagicMock(), MagicMock()
    containers.one.return_value = (4, missing, invalid)
    groups = [{"parent_kind": "payment", "status": "pending", "source": "poll", "count": 2}]
    if unknown:
        groups.append({"parent_kind": "unrecognized", "status": "unrecognized",
                       "source": "unrecognized", "count": 3})
    entries.mappings.return_value.all.return_value = groups
    db = AsyncMock(execute=AsyncMock(side_effect=[containers, entries]))
    result = asyncio.run(_receipt_inventory(db))
    assert result == {
        "source": "billing_invoices.plan_snapshot.receipt_observations",
        "scope": "database_inventory", "kind": "current_state", "coverage": "partial",
        "reason_code": reason, "values": {
            "invoice_count": 4, "missing_map_count": missing, "invalid_container_count": invalid,
            "count": 5 if unknown else 2, "groups": groups,
            "pending_age_seconds": None, "escalation_due": None,
        },
    }
    assert db.execute.await_count == 2
    from sqlalchemy.dialects import postgresql
    sql = [str(call.args[0].compile(dialect=postgresql.dialect())).lower()
           for call in db.execute.await_args_list]
    assert "json_typeof" in sql[0] and "json_each(case when" in sql[1]
    for call in db.execute.await_args_list:
        assert call.args[0].whereclause is None
        selected = str(call.args[0].selected_columns).lower()
        assert "key" not in selected
        for private in (".id", "workspace_id", "operation_id", "amount_minor", "receipt_contact",
                        "created_at", "observed_at", "registered_at", "shop_id", "environment", "receipt_url"):
            assert private not in str(call.args[0]).lower()


@pytest.mark.parametrize("state,invalid,reason", [
    (None, 0, "deletion_details_and_reaction_uninstrumented"),
    ("notice", 2, "invalid_schedule"), ("unrecognized", 0, "unrecognized"),
])
def test_fair_use_inventory_closed_counts_and_private_projection(state, invalid, reason):
    from twobrain_rec_server.billing.monitoring import _fair_use_inventory

    rows = [] if state is None else [{
        "state": state, "count": 2, "invalid_schedule_count": invalid,
        "not_started_count": 0, "deadline_reached_count": 0, "waiting_count": 0,
    }]
    response = MagicMock()
    response.mappings.return_value.all.return_value = rows
    empty = MagicMock()
    empty.mappings.return_value.all.return_value = []
    db = AsyncMock(execute=AsyncMock(side_effect=[response, empty]))
    result = asyncio.run(_fair_use_inventory(db, datetime(2026, 11, 1, tzinfo=UTC)))
    assert result == {
        "source": "fair_use_reviews,meeting_deletion_requests", "scope": "database_inventory", "kind": "current_state",
        "coverage": "partial", "reason_code": reason,
        "values": {"count": 2 if rows else 0,
                   "groups": [{"state": state, "count": 2}] if rows else [],
                   "pending_review": {"count": 2 if state == "notice" else 0,
                                      "invalid_schedule_count": invalid, "not_started_count": 0,
                                      "deadline_reached_count": 0, "waiting_count": 0},
                   "deletion": {"source": "meeting_deletion_requests", "scope": "database_inventory",
                                "kind": "current_state", "coverage": "partial",
                                "reason_code": "artifact_and_deadline_uninstrumented", "values": {
                                    "count": 0, "groups": [], "artifact_completion": None, "deadline_status": None,
                                    "job_attempts": None, "job_errors": None, "job_retries": None}}, "reaction": None},
    }
    assert db.execute.await_count == 2
    sql = str(db.execute.await_args_list[0].args[0]).lower()
    assert "isfinite(" in sql and "extract(epoch" in sql and "case when" in sql
    for private in (".id", "workspace_id", "subject_user_id", "capability", "reason_code",
                    "evidence_ref", "appeal", "resolved_at", "resolution_code", "created_at", "updated_at"):
        assert private not in sql


@pytest.mark.parametrize("groups,reason", [
    ([], "artifact_and_deadline_uninstrumented"),
    ([{"state": "active_purge_complete", "count": 2}], "artifact_and_deadline_uninstrumented"),
    ([{"state": "unrecognized", "count": 3}], "unrecognized"),
])
def test_deletion_inventory_closed_projection_and_truthful_limits(groups, reason):
    from twobrain_rec_server.billing.monitoring import _deletion_inventory

    response = MagicMock()
    response.mappings.return_value.all.return_value = groups
    db = AsyncMock(execute=AsyncMock(return_value=response))
    result = asyncio.run(_deletion_inventory(db))
    assert result == {
        "source": "meeting_deletion_requests", "scope": "database_inventory", "kind": "current_state",
        "coverage": "partial", "reason_code": reason,
        "values": {"count": sum(row["count"] for row in groups), "groups": groups,
                   "artifact_completion": None, "deadline_status": None,
                   "job_attempts": None, "job_errors": None, "job_retries": None},
    }
    db.execute.assert_awaited_once()
    query = db.execute.await_args.args[0]
    assert query.whereclause is None
    sql = str(query).lower()
    assert "case when" in sql and "order by" in sql
    for private in (".id", "workspace_id", "meeting_id", "requested_by", "request_source", "reason",
                    "confirmation_boundary", "policy", "metadata", "created_at", "accepted_at",
                    "completed_at", "failed_at"):
        assert private not in sql


def test_storage_empty_and_explicit_exact_helper_arguments(monkeypatch):
    from twobrain_rec_server.billing import monitoring

    rows, reservations = MagicMock(), MagicMock()
    rows.all.return_value = []
    reservations.mappings.return_value.all.return_value = []
    db = AsyncMock(execute=AsyncMock(side_effect=lambda query: rows if "workspaces" in str(query) else reservations))
    now = datetime(2026, 11, 2, tzinfo=UTC)
    result = asyncio.run(monitoring._storage_inventory(db, now))
    assert result["scope"] == "database_inventory" and result["coverage"] == "partial"
    assert result["reason_code"] == "reconciliation_uninstrumented"
    assert result["values"] == {
        "workspace_count": 0, "capacity_unavailable_workspace_count": 0,
        "unrecognized_plan_count": 0, "invalid_capacity_time_count": 0,
        "used_bytes": 0, "reserved_bytes": 0, "capacity_bytes": 0,
        "reservations": {"count": 0, "groups": [], "expired_active_count": 0, "invalid_value_count": 0},
        "reconciliation_gaps": None,
    }
    row = SimpleNamespace(workspace_id="private-workspace", subscription_present=True,
                          plan_code="free", invalid_capacity_time=False)
    rows.all.return_value = [row, row]
    capacity, reserved = 2**60 + 1, 2**54 + 3
    paid = AsyncMock(return_value=capacity)
    hold = AsyncMock(return_value=reserved)
    playback = AsyncMock(return_value=SimpleNamespace(used_bytes=2**53 + 7, reserved_bytes=reserved, capacity_bytes=capacity))
    monkeypatch.setattr(monitoring, "effective_paid_storage", paid)
    monkeypatch.setattr(monitoring, "_active_reserved_bytes", hold)
    monkeypatch.setattr(monitoring, "project_active_playback_storage", playback)
    result = asyncio.run(monitoring._storage_inventory(db, now))
    assert result["values"]["used_bytes"] == 2 * (2**53 + 7)
    assert result["values"]["reserved_bytes"] == 2 * reserved
    assert result["values"]["capacity_bytes"] == 2 * capacity
    assert "private-" not in str(result)
    for call in paid.await_args_list:
        assert call.args == (db,) and call.kwargs == {"subscription": row, "now": now}
    for call in hold.await_args_list:
        assert call.args == (db,) and call.kwargs == {"workspace_id": row.workspace_id, "now": now}
    for call in playback.await_args_list:
        assert call.args == (db,) and call.kwargs == {"workspace_id": row.workspace_id, "capacity_bytes": capacity,
                                                    "reserved_bytes": reserved}


def test_storage_unavailable_and_reservation_priorities(monkeypatch):
    from twobrain_rec_server.billing import monitoring

    rows, reservations = MagicMock(), MagicMock()
    reservations.mappings.return_value.all.return_value = []
    db = AsyncMock(execute=AsyncMock(side_effect=lambda query: rows if "workspaces" in str(query) else reservations))
    paid = AsyncMock(return_value=0)
    monkeypatch.setattr(monitoring, "effective_paid_storage", paid)
    monkeypatch.setattr(monitoring, "_active_reserved_bytes", AsyncMock(side_effect=AssertionError("no capacity")))
    for present, plan, invalid, unavailable, unknown, bad_time, reason in (
        (False, None, False, 1, 0, 0, "capacity_unavailable"),
        (True, None, False, 1, 1, 0, "unrecognized"),
        (True, "private-plan", False, 1, 1, 0, "unrecognized"),
        (True, "personal", True, 1, 0, 1, "capacity_unavailable"),
        (True, "trial", True, 1, 0, 1, "capacity_unavailable"),
        (True, "free", False, 1, 0, 0, "capacity_unavailable"),
    ):
        rows.all.return_value = [SimpleNamespace(subscription_present=present, plan_code=plan,
                                                invalid_capacity_time=invalid)]
        result = asyncio.run(monitoring._storage_inventory(db, datetime(2026, 11, 2, tzinfo=UTC)))
        v = result["values"]
        assert result["reason_code"] == reason
        assert (v["capacity_unavailable_workspace_count"], v["unrecognized_plan_count"],
                v["invalid_capacity_time_count"]) == (unavailable, unknown, bad_time)
        assert v["used_bytes"] is v["reserved_bytes"] is v["capacity_bytes"] is None
    paid.assert_awaited_once()
    for state, invalid, reason in (("active", 2, "invalid_storage_values"), ("unrecognized", 2, "unrecognized")):
        reservations.mappings.return_value.all.return_value = [
            {"state": state, "count": 3, "expired_active_count": 1, "invalid_value_count": invalid}]
        result = asyncio.run(monitoring._storage_inventory(db, datetime(2026, 11, 2, tzinfo=UTC)))
        assert result["reason_code"] == reason
        assert result["values"]["reservations"] == {
            "count": 3, "groups": [{"state": state, "count": 3}], "expired_active_count": 1,
            "invalid_value_count": invalid,
        }


def test_storage_workspace_limit_before_helpers(monkeypatch):
    from twobrain_rec_server.billing import monitoring

    rows, reservations = MagicMock(), MagicMock()
    reservations.mappings.return_value.all.return_value = []
    db = AsyncMock(execute=AsyncMock(side_effect=lambda query: rows if "workspaces" in str(query) else reservations))
    # Missing subscriptions still count toward the inventory boundary.
    row = SimpleNamespace(subscription_present=False)
    paid = AsyncMock(side_effect=AssertionError("limit/missing subscription must not call helper"))
    monkeypatch.setattr(monitoring, "effective_paid_storage", paid)
    rows.all.return_value = [row] * 500
    assert asyncio.run(monitoring._storage_inventory(db, datetime.now(UTC)))["values"]["workspace_count"] == 500
    rows.all.return_value.append(row)
    with pytest.raises(ReportLimitError):
        asyncio.run(monitoring._storage_inventory(db, datetime.now(UTC)))
    paid.assert_not_awaited()
