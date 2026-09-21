"""Integration proof: data whose level lost its legal basis is erased in term (T081).

The unit tests prove the plan and the deadline. This test proves the execution on
a real PostgreSQL schema: GRAF's own rows really are deleted or anonymised, the
provider-held rows become a documented provider request with the same deadline,
and the evidence stays metadata only.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from tests.fakes.auth_contexts import USER_ID
from twobrain_rec_server.config import Settings
from twobrain_rec_server.product_analytics.anonymous_aggregate import (
    build_anonymous_aggregate_bucket,
    record_anonymous_aggregate_bucket,
)
from twobrain_rec_server.product_analytics.legal_basis_lifecycle import (
    BASIS_WITHDRAWAL_STATE_FILE_ENV,
    EXECUTION_LOCAL,
    EXECUTION_PROVIDER_REQUEST,
    apply_basis_loss_disposition,
    basis_loss_evidence_lines,
    basis_withdrawal_state_file_path,
    lost_basis_dispositions,
    read_basis_withdrawal_register,
)
from twobrain_rec_server.product_analytics.provider_config import (
    ProductAnalyticsProviderConfig,
)
from twobrain_rec_server.product_analytics.retention import retention_rule

SERVER_AGGREGATE_TABLE = "anonymous_page_aggregate_buckets"
SERVER_VISIT_TABLE = "public_visit_attributions"
SERVER_ACQUISITION_TABLE = "client_acquisition_attributes"

NOW = datetime(2026, 9, 18, 12, 0, tzinfo=UTC)
WITHDRAWAL_DATE = "2026-09-18"


def _withdrawal_line(level_key: str) -> str:
    return (
        f"basis_withdrawal level={level_key} state=withdrawn withdrawn_at={WITHDRAWAL_DATE} "
        "reason=legal_basis_withdrawn evidence_ref=ev-273-basis-withdrawal"
    )


async def _reset(database_url: str) -> None:
    engine = create_async_engine(database_url, poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            for table in (
                SERVER_AGGREGATE_TABLE,
                SERVER_VISIT_TABLE,
                SERVER_ACQUISITION_TABLE,
            ):
                await connection.execute(sa.text(f'delete from "{table}"'))
    finally:
        await engine.dispose()


async def _rows(database_url: str, table: str) -> list[dict]:
    engine = create_async_engine(database_url, poolclass=NullPool)
    try:
        async with engine.connect() as connection:
            result = await connection.execute(sa.text(f'select * from "{table}"'))
            return [dict(row._mapping) for row in result]
    finally:
        await engine.dispose()


async def _seed(database_url: str) -> None:
    engine = create_async_engine(database_url, poolclass=NullPool)
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            await record_anonymous_aggregate_bucket(
                session,
                build_anonymous_aggregate_bucket(
                    path="/download", source="yandex_direct", occurred_at=NOW
                ),
            )
            await session.execute(
                sa.text(
                    f'insert into "{SERVER_VISIT_TABLE}" '
                    "(id, attribution_ref, landing_path, first_seen_at, expires_at) "
                    "values (gen_random_uuid(), :ref, '/download', :seen, :expires)"
                ),
                {"ref": "graf_visit_basis_loss", "seen": NOW, "expires": NOW + timedelta(days=90)},
            )
            await session.execute(
                sa.text(
                    f'insert into "{SERVER_ACQUISITION_TABLE}" '
                    "(id, account_id, source, medium, campaign, content, term, yclid, "
                    "landing_path, attribution_rule, attribution_confidence, captured_at) "
                    "values (gen_random_uuid(), :account, 'yandex_direct', 'cpc', "
                    "'campaign_096', 'banner_a', 'keyword_b', 'yclid_basis_loss', "
                    "'/download', 'last_non_direct_90d', 'linked', :captured)"
                ),
                {"account": USER_ID, "captured": NOW},
            )
            await session.commit()
    finally:
        await engine.dispose()


def _withdrawal_environ(tmp_path: Path, level_key: str = "provider_analytics") -> dict[str, str]:
    path = tmp_path / "legal-basis-withdrawals"
    path.write_text(
        "legal_basis_state_version=1\n" + _withdrawal_line(level_key) + "\n",
        encoding="utf-8",
    )
    return {BASIS_WITHDRAWAL_STATE_FILE_ENV: str(path)}


def _config() -> ProductAnalyticsProviderConfig:
    return ProductAnalyticsProviderConfig.from_settings(
        Settings(
            product_analytics_enabled=True,
            product_analytics_anonymous_aggregate_enabled=True,
            product_analytics_posthog_enabled=True,
            product_analytics_yandex_all_pages_enabled=True,
            product_analytics_yandex_offline_enabled=True,
        )
    )


@pytest.fixture
def erasure_database_url(postgres_seeded_database_url: str) -> str:
    asyncio.run(_reset(postgres_seeded_database_url))
    asyncio.run(_seed(postgres_seeded_database_url))
    return postgres_seeded_database_url


def test_basis_loss_plan_covers_every_affected_category(
    erasure_database_url: str, tmp_path: Path
) -> None:
    register = read_basis_withdrawal_register(_withdrawal_environ(tmp_path))

    plans = lost_basis_dispositions(_config(), withdrawals=register, now=NOW)

    assert [plan.level_key for plan in plans] == ["provider_analytics"]
    assert plans[0].processing_state == "stopped"
    assert {action.category for action in plans[0].actions} == {
        "posthog_product_events",
        "yandex_page_events",
        "yandex_offline_conversions",
    }


def test_provider_held_categories_become_a_dated_provider_request(
    erasure_database_url: str, tmp_path: Path
) -> None:
    register = read_basis_withdrawal_register(_withdrawal_environ(tmp_path))
    plan = lost_basis_dispositions(_config(), withdrawals=register, now=NOW)[0]

    results = asyncio.run(_apply(erasure_database_url, plan))

    assert {result.execution for result in results} == {EXECUTION_PROVIDER_REQUEST}
    assert all(result.rows_affected == 0 for result in results)
    for result in results:
        rule = retention_rule(result.category)
        assert result.due_at == plan.basis_lost_at + timedelta(days=rule.enforced_retention_days())
        assert result.within_deadline is True

    lines = basis_loss_evidence_lines(results, reason=plan.reason)
    assert len(lines) == len(results)
    for result, line in zip(results, lines, strict=True):
        # Each evidence line carries the term of its own category.
        assert f"due_at={result.due_at.date().isoformat()}" in line
        assert f"category={result.category}" in line


def test_level_two_data_is_deleted_and_anonymised_within_the_term(
    erasure_database_url: str, tmp_path: Path
) -> None:
    plan = _plan_for("attribution_profiles", tmp_path)

    results = asyncio.run(_apply(erasure_database_url, plan))

    visits = asyncio.run(_rows(erasure_database_url, SERVER_VISIT_TABLE))
    assert visits == [], "the visit attribution row is deleted"

    rows = asyncio.run(_rows(erasure_database_url, SERVER_ACQUISITION_TABLE))
    assert len(rows) == 1, "the client record itself stays"
    attribute = rows[0]
    assert attribute["account_id"] == USER_ID
    assert attribute["landing_path"] == "/download"
    for label in ("source", "medium", "campaign", "content", "term", "yclid"):
        assert attribute[label] is None, f"{label} must be anonymised"

    assert {result.execution for result in results} == {EXECUTION_LOCAL}
    assert {result.disposition for result in results} == {"delete", "anonymise"}
    for result in results:
        assert result.within_deadline is True
    assert (
        basis_loss_evidence_lines(results, reason=plan.reason)[0].count("reason=") == 1
    )


def test_level_one_aggregate_is_deleted_within_the_term(
    erasure_database_url: str, tmp_path: Path
) -> None:
    plan = _plan_for("anonymous_aggregate", tmp_path)

    results = asyncio.run(_apply(erasure_database_url, plan))

    assert asyncio.run(_rows(erasure_database_url, SERVER_AGGREGATE_TABLE)) == []
    assert results[0].rows_affected == 1
    assert results[0].category == "anonymous_page_aggregate"
    assert results[0].due_at == plan.basis_lost_at + timedelta(days=1095)
    assert results[0].within_deadline is True


def test_erasure_leaves_no_personal_data_in_the_evidence(
    erasure_database_url: str, tmp_path: Path
) -> None:
    plan = _plan_for("attribution_profiles", tmp_path)

    results = asyncio.run(_apply(erasure_database_url, plan))

    lines = "\n".join(basis_loss_evidence_lines(results, reason=plan.reason))
    assert "yandex_direct" not in lines, "a campaign label is not evidence"
    assert "graf_visit_basis_loss" not in lines
    assert str(USER_ID) not in lines


def _plan_for(level_key: str, tmp_path: Path):
    register = read_basis_withdrawal_register(_withdrawal_environ(tmp_path, level_key))
    for plan in lost_basis_dispositions(_config(), withdrawals=register, now=NOW):
        if plan.level_key == level_key:
            return plan
    raise AssertionError(f"no withdrawal plan for {level_key}")


async def _apply(database_url: str, plan):
    engine = create_async_engine(database_url, poolclass=NullPool)
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            return await apply_basis_loss_disposition(session, plan)
    finally:
        await engine.dispose()


def test_state_file_path_is_outside_the_repository(tmp_path: Path) -> None:
    assert basis_withdrawal_state_file_path(
        {BASIS_WITHDRAWAL_STATE_FILE_ENV: str(tmp_path / "explicit-state")}
    ) == str(tmp_path / "explicit-state")
    assert basis_withdrawal_state_file_path(
        {"GRAF_PRODUCT_ANALYTICS_LEGAL_BASIS_STATE_DIR": str(tmp_path)}
    ) == str(tmp_path / "legal-basis-withdrawals")
    assert basis_withdrawal_state_file_path({}).startswith("/var/lib/")
