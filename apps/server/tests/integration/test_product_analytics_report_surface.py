"""Отчётная поверхность продукта отвечает и считает (FR-012, FR-041).

Проверяется не только арифметика, но и то, что код продукта действительно
вызывается: доля согласия и стоимость результата приходят с поверхности
``GET /api/v1/product-analytics/reports``. Поверхность закрыта аутентификацией,
потому что стоимость активации по кампании — это расход рекламного бюджета.
"""

import asyncio
import json
from datetime import date
from pathlib import Path
from uuid import uuid4

from tests.contract.test_ingest_openapi_contract import auth_headers
from twobrain_rec_server.db.models.product_analytics import AnonymousPageAggregateBucket
from twobrain_rec_server.product_analytics.report_surface import REPORT_COUNTS_VERSION

BUCKET_DATE = date(2026, 9, 1)
SPEND_EXPORT_SAMPLE = """date,campaign,ad,spend_rub,clicks
2026-09-01,brand-search,ad-brand,20000,50
2026-09-01,generic-search,ad-generic,30000,80
"""


async def _seed_buckets(client, buckets: list[dict]) -> None:
    async with client.app_state["sessionmaker"]() as session:
        for bucket in buckets:
            session.add(
                AnonymousPageAggregateBucket(
                    id=uuid4(),
                    bucket_date=BUCKET_DATE,
                    surface=bucket.get("surface", "public_landing"),
                    landing_path=bucket.get("landing_path", "/"),
                    campaign=bucket.get("campaign"),
                    device_class="desktop",
                    referrer_category="paid",
                    traffic_class="external",
                    visits=bucket["visits"],
                )
            )
        await session.commit()


def _write_report_inputs(monkeypatch, tmp_path: Path, *, consent_visits: int) -> None:
    counts_path = tmp_path / "report-counts.json"
    counts_path.write_text(
        json.dumps(
            {
                "version": REPORT_COUNTS_VERSION,
                "period_start": BUCKET_DATE.isoformat(),
                "period_end": BUCKET_DATE.isoformat(),
                "consent_visits": consent_visits,
                "conversions": {"brand-search": {"first_value": 4}},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    spend_path = tmp_path / "ad-cabinet-spend.csv"
    spend_path.write_text(SPEND_EXPORT_SAMPLE, encoding="utf-8")
    monkeypatch.setenv("TWOBRAIN_PRODUCT_ANALYTICS_REPORT_COUNTS_FILE", str(counts_path))
    monkeypatch.setenv("TWOBRAIN_PRODUCT_ANALYTICS_AD_CABINET_EXPORT_FILE", str(spend_path))


def test_reports_endpoint_computes_the_consent_share_and_the_cost(
    client,
    monkeypatch,
    tmp_path: Path,
) -> None:
    asyncio.run(
        _seed_buckets(
            client,
            [
                {"visits": 60},
                {"visits": 40, "landing_path": "/download"},
            ],
        )
    )
    _write_report_inputs(monkeypatch, tmp_path, consent_visits=41)

    response = client.get("/api/v1/product-analytics/reports", headers=auth_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload["consent_share"]["consent_share_label"] == "41 %"
    assert payload["consent_share"]["aggregate_visits"] == 100
    assert payload["consent_share"]["published"] is True
    assert payload["aggregate_state"] == "measured"
    rows = {row["label"]: row for row in payload["cost_per_result"]["report"]["rows"]}
    assert rows["brand-search"]["cost_per_result"] == 5000.0
    assert rows["generic-search"]["cost_per_result"] is None
    assert rows["generic-search"]["rendered_cost"] == "нет данных"
    assert payload["cost_per_result"]["report"]["spend_period_complete"] is True


def test_reports_endpoint_hides_the_share_when_the_denominator_is_empty(
    client,
    monkeypatch,
    tmp_path: Path,
) -> None:
    _write_report_inputs(monkeypatch, tmp_path, consent_visits=0)

    response = client.get("/api/v1/product-analytics/reports", headers=auth_headers())

    assert response.status_code == 200
    share = response.json()["consent_share"]
    assert share["published"] is False
    assert share["consent_share"] is None
    assert share["consent_share_label"] is None
    assert share["blocked_reason"] == "below_minimum_bucket_size"


def test_reports_endpoint_requires_an_authenticated_operator(client) -> None:
    response = client.get("/api/v1/product-analytics/reports")

    assert response.status_code == 401
