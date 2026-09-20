"""Доля согласия и стоимость результата считаются продуктом (FR-012, FR-041).

Проверяется то, чего не хватало: знаменатель доли — обезличенный счёт уровня 1
из таблицы ``anonymous_page_aggregate_buckets``, а не ручная вставка оператора, и
считает долю код продукта. Образец числителя (число согласившихся визитов) и
образец расхода допустимы, но соединение и арифметику выполняет продукт.

При нулевом знаменателе проверяется честное поведение: доли нет, деления на ноль
нет и выдуманного «0 %» тоже нет.
"""

import asyncio
import json
import os
from datetime import date
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from twobrain_rec_server.db.models.product_analytics import AnonymousPageAggregateBucket
from twobrain_rec_server.product_analytics.anonymous_aggregate import (
    INSTALLER_DELIVERY_SURFACE,
    MINIMUM_AGGREGATE_BUCKET_SIZE,
)
from twobrain_rec_server.product_analytics.report_surface import (
    REPORT_COUNTS_VERSION,
    build_product_report_surface,
)

BUCKET_DATE = date(2026, 9, 1)
PERIOD = {"period_start": BUCKET_DATE.isoformat(), "period_end": BUCKET_DATE.isoformat()}

SPEND_EXPORT_SAMPLE = """date,campaign,ad,spend_rub,clicks
2026-09-01,brand-search,ad-brand,20000,50
2026-09-01,generic-search,ad-generic,30000,80
"""


async def _reset_aggregate(database_url: str) -> None:
    engine = create_async_engine(database_url, poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.execute(
                AnonymousPageAggregateBucket.__table__.delete()
            )
    finally:
        await engine.dispose()


async def _seed_buckets(database_url: str, buckets: list[dict]) -> None:
    engine = create_async_engine(database_url, poolclass=NullPool)
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            for bucket in buckets:
                session.add(
                    AnonymousPageAggregateBucket(
                        id=uuid4(),
                        bucket_date=bucket.get("bucket_date", BUCKET_DATE),
                        surface=bucket.get("surface", "public_landing"),
                        landing_path=bucket.get("landing_path", "/"),
                        campaign=bucket.get("campaign"),
                        device_class="desktop",
                        referrer_category="paid",
                        traffic_class=bucket.get("traffic_class", "external"),
                        visits=bucket["visits"],
                    )
                )
            await session.commit()
    finally:
        await engine.dispose()


async def _surface(database_url: str, environ: dict[str, str]) -> dict:
    engine = create_async_engine(database_url, poolclass=NullPool)
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            return await build_product_report_surface(session, environ=environ)
    finally:
        await engine.dispose()


@pytest.fixture
def report_database_url(postgres_schema_database_url: str) -> str:
    asyncio.run(_reset_aggregate(postgres_schema_database_url))
    return postgres_schema_database_url


def _write_counts(tmp_path: Path, payload: dict) -> str:
    path = tmp_path / "report-counts.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return str(path)


def _write_spend(tmp_path: Path, text: str = SPEND_EXPORT_SAMPLE) -> str:
    path = tmp_path / "ad-cabinet-spend.csv"
    path.write_text(text, encoding="utf-8")
    return str(path)


def _counts_payload(**overrides) -> dict:
    payload = {
        "version": REPORT_COUNTS_VERSION,
        "consent_visits": 41,
        "conversions": {},
        **PERIOD,
    }
    payload.update(overrides)
    return payload


def test_consent_share_is_computed_by_the_product_from_the_level_1_aggregate(
    report_database_url: str,
    tmp_path: Path,
) -> None:
    asyncio.run(
        _seed_buckets(
            report_database_url,
            [
                {"visits": 60},
                {"visits": 40, "landing_path": "/download"},
            ],
        )
    )
    environ = {"TWOBRAIN_PRODUCT_ANALYTICS_REPORT_COUNTS_FILE": _write_counts(tmp_path, _counts_payload())}

    surface = asyncio.run(_surface(report_database_url, environ))
    share = surface["consent_share"]

    assert share["aggregate_visits"] == 100
    assert share["consent_visits"] == 41
    assert share["published"] is True
    assert share["consent_share"] == 0.41
    assert share["consent_share_label"] == "41 %"
    assert share["denominator_source"] == "graf_aggregate_pg:anonymous_page_aggregate_buckets"
    assert share["aggregate_state"] == "measured"
    assert share["owner"] == "privacy/security reviewer"


def test_zero_denominator_is_not_a_fake_zero(
    report_database_url: str,
    tmp_path: Path,
) -> None:
    environ = {
        "TWOBRAIN_PRODUCT_ANALYTICS_REPORT_COUNTS_FILE": _write_counts(
            tmp_path, _counts_payload(consent_visits=0)
        )
    }

    surface = asyncio.run(_surface(report_database_url, environ))
    share = surface["consent_share"]

    assert share["aggregate_visits"] == 0
    assert share["published"] is False
    assert share["blocked_reason"] == "below_minimum_bucket_size"
    assert share["consent_share"] is None
    assert share["consent_share_percent"] is None
    assert share["consent_share_label"] is None


def test_inconsistent_counters_are_refused_instead_of_clamped(
    report_database_url: str,
    tmp_path: Path,
) -> None:
    asyncio.run(_seed_buckets(report_database_url, [{"visits": 100}]))
    environ = {
        "TWOBRAIN_PRODUCT_ANALYTICS_REPORT_COUNTS_FILE": _write_counts(
            tmp_path, _counts_payload(consent_visits=150)
        )
    }

    surface = asyncio.run(_surface(report_database_url, environ))
    share = surface["consent_share"]

    # Согласившихся больше, чем визитов: это рассогласование источников, а не
    # доля больше 100 процентов. Долю не показываем.
    assert share["published"] is False
    assert share["blocked_reason"] == "counts_inconsistent"
    assert share["consent_share"] is None
    assert share["consent_share_label"] is None


def test_internal_and_small_buckets_stay_out_of_the_denominator(
    report_database_url: str,
    tmp_path: Path,
) -> None:
    asyncio.run(
        _seed_buckets(
            report_database_url,
            [
                {"visits": 500, "traffic_class": "internal"},
                {"visits": 400, "traffic_class": "test"},
                {"visits": MINIMUM_AGGREGATE_BUCKET_SIZE - 1},
            ],
        )
    )
    environ = {"TWOBRAIN_PRODUCT_ANALYTICS_REPORT_COUNTS_FILE": _write_counts(tmp_path, _counts_payload())}

    surface = asyncio.run(_surface(report_database_url, environ))
    share = surface["consent_share"]

    assert share["aggregate_visits"] == 0
    assert share["published"] is False
    assert share["blocked_reason"] == "below_minimum_bucket_size"


def test_missing_counts_file_leaves_the_share_unmeasured(
    report_database_url: str,
    tmp_path: Path,
) -> None:
    asyncio.run(_seed_buckets(report_database_url, [{"visits": 100}]))
    environ = {
        "TWOBRAIN_PRODUCT_ANALYTICS_REPORT_COUNTS_FILE": str(tmp_path / "absent.json")
    }

    surface = asyncio.run(_surface(report_database_url, environ))
    share = surface["consent_share"]

    assert share["published"] is False
    assert share["blocked_reason"] == "counts_unavailable"
    assert share["consent_share_label"] is None
    assert "report_counts_unavailable" in share["counts_file_errors"]


def test_cost_per_installer_download_uses_the_level_1_download_counter(
    report_database_url: str,
    tmp_path: Path,
) -> None:
    asyncio.run(
        _seed_buckets(
            report_database_url,
            [
                {"visits": 60, "campaign": "brand-search"},
                {"visits": 40, "campaign": "generic-search"},
                {"surface": INSTALLER_DELIVERY_SURFACE, "visits": 5, "campaign": "brand-search"},
                {"surface": INSTALLER_DELIVERY_SURFACE, "visits": 2, "campaign": "generic-search"},
            ],
        )
    )
    environ = {
        "TWOBRAIN_PRODUCT_ANALYTICS_REPORT_COUNTS_FILE": _write_counts(
            tmp_path,
            _counts_payload(
                consent_visits=41,
                conversions={"brand-search": {"first_value": 4}},
            ),
        ),
        "TWOBRAIN_PRODUCT_ANALYTICS_AD_CABINET_EXPORT_FILE": _write_spend(tmp_path),
    }

    surface = asyncio.run(_surface(report_database_url, environ))
    cost = surface["cost_per_result"]

    assert cost["blocked_reason"] is None
    downloads = next(
        report for report in cost["companion_reports"] if report["metric_id"] == "cost_per_installer_download"
    )
    by_campaign = {row["label"]: row for row in downloads["rows"]}

    # Знаменатель взят из обезличенного счёта уровня 1, а не из файла оператора.
    assert by_campaign["brand-search"]["results"] == 5
    assert by_campaign["brand-search"]["cost_per_result"] == 4000.0
    # Корзина меньше минимального размера не раскрывается: кампания без
    # раскрытых скачиваний получает «нет данных», а не выдуманный ноль.
    assert by_campaign["generic-search"]["results"] == 0
    assert by_campaign["generic-search"]["cost_per_result"] is None
    assert by_campaign["generic-search"]["rendered_cost"] == "нет данных"
    assert cost["report"]["rows"][0]["cost_per_result"] == 20000.0 / 4


def test_cost_report_needs_the_period_to_judge_completeness(
    report_database_url: str,
    tmp_path: Path,
) -> None:
    asyncio.run(_seed_buckets(report_database_url, [{"visits": 100}]))
    payload = _counts_payload()
    payload.pop("period_start")
    payload.pop("period_end")
    environ = {
        "TWOBRAIN_PRODUCT_ANALYTICS_REPORT_COUNTS_FILE": _write_counts(tmp_path, payload),
        "TWOBRAIN_PRODUCT_ANALYTICS_AD_CABINET_EXPORT_FILE": _write_spend(tmp_path),
    }

    surface = asyncio.run(_surface(report_database_url, environ))
    cost = surface["cost_per_result"]

    # Без периода нельзя ответить, загружен ли расход целиком, поэтому стоимость
    # не считается и причина названа. Долю согласия отсутствие периода не ломает.
    assert cost["blocked_reason"] == "report_period_unknown"
    assert cost["report"] is None
    assert surface["consent_share"]["published"] is True
    assert surface["consent_share"]["consent_share_label"] == "41 %"


def test_counts_file_with_personal_data_is_refused(
    report_database_url: str,
    tmp_path: Path,
) -> None:
    asyncio.run(_seed_buckets(report_database_url, [{"visits": 100}]))
    environ = {
        "TWOBRAIN_PRODUCT_ANALYTICS_REPORT_COUNTS_FILE": _write_counts(
            tmp_path,
            _counts_payload(conversions={"client@example.com": {"first_value": 3}}),
        )
    }

    surface = asyncio.run(_surface(report_database_url, environ))

    assert surface["counts_state"]["usable"] is False
    assert "report_counts_campaign_label_forbidden" in surface["counts_state"]["file_errors"]
    # Сама метка с контактом в отчёт не попадает.
    assert "client@example.com" not in json.dumps(surface, ensure_ascii=False)
    assert surface["consent_share"]["published"] is False
    assert surface["consent_share"]["blocked_reason"] == "counts_unavailable"


def test_surface_without_a_database_names_the_gap_instead_of_a_zero(tmp_path: Path) -> None:
    environ = {
        "TWOBRAIN_PRODUCT_ANALYTICS_REPORT_COUNTS_FILE": _write_counts(tmp_path, _counts_payload())
    }

    surface = asyncio.run(build_product_report_surface(None, environ=environ))
    share = surface["consent_share"]

    # База недоступна: знаменателя нет. Это пробел измерения, и он называется
    # своим именем, а не превращается в ноль процентов.
    assert surface["aggregate_state"] == "unavailable"
    assert share["published"] is False
    assert share["blocked_reason"] == "aggregate_unavailable"
    assert share["aggregate_visits"] is None
    assert share["consent_share"] is None
    assert share["consent_share_label"] is None


def test_report_surface_names_its_sources_and_owners(
    report_database_url: str,
    tmp_path: Path,
) -> None:
    environ = {
        "TWOBRAIN_PRODUCT_ANALYTICS_REPORT_COUNTS_FILE": _write_counts(tmp_path, _counts_payload()),
        "TWOBRAIN_PRODUCT_ANALYTICS_AD_CABINET_EXPORT_FILE": _write_spend(tmp_path),
    }

    surface = asyncio.run(_surface(report_database_url, environ))

    assert surface["owners"] == {
        "R07": "growth analytics operator",
        "R11": "privacy/security reviewer",
    }
    assert surface["reports"] == {
        "R11_consent_coverage": "consent_share",
        "R07_cost_per_result": "cost_per_result",
    }
    assert surface["counts_state"]["usable"] is True
    assert any("нижней границей" in caveat for caveat in surface["caveats"])
    assert os.path.basename(surface["counts_state"]["state_path"]) == "report-counts.json"
