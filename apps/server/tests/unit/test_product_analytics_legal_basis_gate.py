"""Writer enforcement for FR-048 levels 1 and 2.

The withdrawal register is operator-managed state outside the repository. These
unit tests use a temporary register and a SQL spy to prove that the shared gate
runs before each local writer can execute SQL, while an absent register keeps the
existing best-effort path available.
"""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from twobrain_rec_server.config import Settings
from twobrain_rec_server.product_analytics.acquisition import (
    build_client_acquisition_attribute,
    build_visit_attribution,
    record_client_acquisition_attribute_safely,
    record_visit_attribution_safely,
)
from twobrain_rec_server.product_analytics.anonymous_aggregate import (
    build_anonymous_aggregate_bucket,
    record_anonymous_aggregate_bucket_safely,
)
from twobrain_rec_server.product_analytics.legal_basis_gate import (
    ANONYMOUS_AGGREGATE_LEVEL,
    ATTRIBUTION_PROFILES_LEVEL,
    WRITE_ALLOWED,
    WRITE_BLOCKED_SETTINGS,
    WRITE_BLOCKED_WITHDRAWN,
    legal_basis_write_gate,
)
from twobrain_rec_server.product_analytics.legal_basis_lifecycle import (
    BASIS_WITHDRAWAL_STATE_FILE_ENV,
)
from twobrain_rec_server.public.analytics import (
    record_public_installer_delivery,
    record_public_page_visit,
    record_public_registration_step,
)


class _SpyResult:
    def scalar_one(self) -> int:
        return 1

    def scalar_one_or_none(self):
        return uuid4()


class _SpyNested:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args) -> None:
        return None


class _SpySession:
    def __init__(self) -> None:
        self.execute_calls = 0
        self.commit_calls = 0
        self.rollback_calls = 0

    async def execute(self, _statement):
        self.execute_calls += 1
        return _SpyResult()

    async def commit(self) -> None:
        self.commit_calls += 1

    async def rollback(self) -> None:
        self.rollback_calls += 1

    def begin_nested(self) -> _SpyNested:
        return _SpyNested()


class _FakeRequest:
    def __init__(self, path: str = "/download") -> None:
        self.url = SimpleNamespace(path=path, scheme="https")
        self.query_params = {}
        self.cookies = {}
        self.headers = {"user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X)"}
        self.client = SimpleNamespace(host="203.0.113.10")
        self.app = SimpleNamespace(
            state=SimpleNamespace(
                settings=Settings(product_analytics_anonymous_aggregate_enabled=True)
            )
        )


def _withdrawal_file(tmp_path, level: str):
    path = tmp_path / "legal-basis-withdrawals"
    path.write_text(
        "legal_basis_state_version=1\n"
        f"basis_withdrawal level={level} state=withdrawn "
        "withdrawn_at=2026-09-18 reason=legal_basis_withdrawn "
        "evidence_ref=ev-273-writer-gate\n",
        encoding="utf-8",
    )
    return path


@pytest.mark.asyncio
async def test_level_one_public_writers_do_not_execute_sql_after_withdrawal(
    tmp_path, monkeypatch
) -> None:
    state = _withdrawal_file(tmp_path, ANONYMOUS_AGGREGATE_LEVEL)
    monkeypatch.setenv(BASIS_WITHDRAWAL_STATE_FILE_ENV, str(state))
    session = _SpySession()
    request = _FakeRequest()

    assert await record_public_page_visit(session, request) is None
    assert await record_public_registration_step(session, request, "signup_step_viewed") is None
    assert await record_public_installer_delivery(session, request) is None
    assert session.execute_calls == 0
    assert session.commit_calls == 0


@pytest.mark.asyncio
async def test_level_one_low_level_writer_returns_none_before_sql_after_withdrawal(
    tmp_path,
) -> None:
    state = _withdrawal_file(tmp_path, ANONYMOUS_AGGREGATE_LEVEL)
    session = _SpySession()
    bucket = build_anonymous_aggregate_bucket(path="/download")

    result = await record_anonymous_aggregate_bucket_safely(
        session,
        bucket,
        settings=Settings(product_analytics_anonymous_aggregate_enabled=True),
        environ={BASIS_WITHDRAWAL_STATE_FILE_ENV: str(state)},
    )

    assert result is None
    assert session.execute_calls == 0
    assert session.commit_calls == 0


@pytest.mark.asyncio
async def test_level_two_visit_and_auth_acquisition_writers_do_not_execute_sql_after_withdrawal(
    tmp_path,
) -> None:
    state = _withdrawal_file(tmp_path, ATTRIBUTION_PROFILES_LEVEL)
    environ = {BASIS_WITHDRAWAL_STATE_FILE_ENV: str(state)}
    session = _SpySession()
    moment = datetime(2026, 9, 18, 12, 0, tzinfo=UTC)
    visit = build_visit_attribution(
        landing_path="/download",
        source="yandex_direct",
        campaign="writer_gate",
        first_seen_at=moment,
    )
    attribute = build_client_acquisition_attribute(
        account_id=uuid4(),
        landing_path="/download",
        source="yandex_direct",
        campaign="writer_gate",
        captured_at=moment,
    )

    assert (
        await record_visit_attribution_safely(
            session,
            visit.as_dict(),
            environ=environ,
        )
        is None
    )
    assert (
        await record_client_acquisition_attribute_safely(
            session,
            attribute,
            environ=environ,
        )
        is False
    )
    assert session.execute_calls == 0
    assert session.commit_calls == 0


@pytest.mark.asyncio
async def test_missing_register_keeps_normal_writers_on_the_sql_path(tmp_path) -> None:
    absent = tmp_path / "no-withdrawal-register"
    environ = {BASIS_WITHDRAWAL_STATE_FILE_ENV: str(absent)}
    session = _SpySession()
    moment = datetime(2026, 9, 18, 12, 0, tzinfo=UTC)
    bucket = build_anonymous_aggregate_bucket(path="/download", occurred_at=moment)
    visit = build_visit_attribution(
        landing_path="/download",
        source="yandex_direct",
        campaign="normal_path",
        first_seen_at=moment,
    )
    attribute = build_client_acquisition_attribute(
        account_id=uuid4(),
        landing_path="/download",
        source="yandex_direct",
        campaign="normal_path",
        captured_at=moment,
    )

    assert (
        await record_anonymous_aggregate_bucket_safely(
            session,
            bucket,
            settings=Settings(product_analytics_anonymous_aggregate_enabled=True),
            environ=environ,
        )
        == 1
    )
    assert (
        await record_visit_attribution_safely(
            session,
            visit.as_dict(),
            environ=environ,
        )
        == visit.attribution_ref
    )
    assert (
        await record_client_acquisition_attribute_safely(
            session,
            attribute,
            environ=environ,
        )
        is True
    )
    assert session.execute_calls == 3
    assert session.commit_calls == 2


def test_missing_register_keeps_normal_writers_allowed(tmp_path) -> None:
    absent = tmp_path / "no-withdrawal-register"
    decision_level_one = legal_basis_write_gate(
        ANONYMOUS_AGGREGATE_LEVEL,
        settings=Settings(product_analytics_anonymous_aggregate_enabled=True),
        environ={BASIS_WITHDRAWAL_STATE_FILE_ENV: str(absent)},
    )
    decision_level_two = legal_basis_write_gate(
        ATTRIBUTION_PROFILES_LEVEL,
        settings=Settings(product_analytics_enabled=False),
        environ={BASIS_WITHDRAWAL_STATE_FILE_ENV: str(absent)},
    )

    assert decision_level_one.allowed is True
    assert decision_level_one.reason == WRITE_ALLOWED
    assert decision_level_two.allowed is True
    assert decision_level_two.reason == WRITE_ALLOWED


def test_level_one_settings_brake_is_scoped_to_level_one(tmp_path) -> None:
    absent = tmp_path / "no-withdrawal-register"
    decision = legal_basis_write_gate(
        ANONYMOUS_AGGREGATE_LEVEL,
        settings=Settings(product_analytics_anonymous_aggregate_enabled=False),
        environ={BASIS_WITHDRAWAL_STATE_FILE_ENV: str(absent)},
    )

    assert decision.allowed is False
    assert decision.reason == WRITE_BLOCKED_SETTINGS


def test_withdrawal_decision_is_scoped_to_the_recorded_level(tmp_path) -> None:
    state = _withdrawal_file(tmp_path, ATTRIBUTION_PROFILES_LEVEL)
    environ = {BASIS_WITHDRAWAL_STATE_FILE_ENV: str(state)}

    affected = legal_basis_write_gate(
        ATTRIBUTION_PROFILES_LEVEL,
        settings=Settings(),
        environ=environ,
    )
    unaffected = legal_basis_write_gate(
        ANONYMOUS_AGGREGATE_LEVEL,
        settings=Settings(product_analytics_anonymous_aggregate_enabled=True),
        environ=environ,
    )

    assert affected.allowed is False
    assert affected.reason == WRITE_BLOCKED_WITHDRAWN
    assert affected.withdrawal is not None
    assert unaffected.allowed is True
