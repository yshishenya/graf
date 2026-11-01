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
