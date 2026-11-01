import asyncio
from datetime import UTC, date, datetime, timedelta
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
