from __future__ import annotations

from datetime import date

from twobrain_rec_server.admin.usage import quota_risk_state, summarize_usage_rows


def test_quota_risk_state_handles_missing_near_and_exceeded_limits() -> None:
    assert quota_risk_state(used=10, limit=None) == "not_configured"
    assert quota_risk_state(used=40, limit=100) == "ok"
    assert quota_risk_state(used=85, limit=100) == "near_limit"
    assert quota_risk_state(used=120, limit=100) == "exceeded"


def test_summarize_usage_rows_reconciles_source_rows() -> None:
    summary = summarize_usage_rows(
        [
            {
                "recording_minutes": 10,
                "storage_bytes": 1000,
                "processing_jobs": 1,
                "freshness_state": "fresh",
            },
            {
                "usage_date": date(2026, 6, 27),
                "recording_minutes": 15,
                "storage_bytes": 2000,
                "processing_jobs": 2,
                "freshness_state": "lagging",
            },
        ]
    )

    assert summary["recording_minutes"] == 25
    assert summary["storage_bytes"] == 3000
    assert summary["processing_jobs"] == 3
    assert summary["freshness"] == "incomplete"
    assert summary["date_window"] == {"from": "2026-06-27", "to": "2026-06-27"}
