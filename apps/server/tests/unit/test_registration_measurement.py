"""The optional registration counter cannot take ownership of sign-in."""

import asyncio
from types import SimpleNamespace

import pytest

from twobrain_rec_server.api import auth


@pytest.mark.asyncio
async def test_counter_handles_session_factory_failure_without_retry(monkeypatch):
    calls = []

    def broken_sessionmaker():
        calls.append("setup")
        raise RuntimeError("synthetic session factory failure")

    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(
        db_sessionmaker=broken_sessionmaker,
        settings=SimpleNamespace(product_analytics_anonymous_aggregate_enabled=True),
    )))
    await auth._record_web_registration_step(request, db=object(), step="signup_completed")
    assert calls == ["setup"]


@pytest.mark.asyncio
async def test_counter_does_not_open_session_when_disabled():
    def forbidden_sessionmaker():
        pytest.fail("disabled measurement opened a session")

    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(
        db_sessionmaker=forbidden_sessionmaker,
        settings=SimpleNamespace(product_analytics_anonymous_aggregate_enabled=False),
    )))
    await auth._record_web_registration_step(request, db=object(), step="signup_completed")


@pytest.mark.asyncio
async def test_counter_propagates_external_cancellation():
    def cancelled_sessionmaker():
        raise asyncio.CancelledError()

    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(
        db_sessionmaker=cancelled_sessionmaker,
        settings=SimpleNamespace(product_analytics_anonymous_aggregate_enabled=True),
    )))
    with pytest.raises(asyncio.CancelledError):
        await auth._record_web_registration_step(request, db=object(), step="signup_completed")
