from datetime import UTC, datetime, timedelta

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
