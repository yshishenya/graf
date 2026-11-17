from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy.exc import OperationalError
from starlette.requests import Request

from twobrain_rec_server.cabinet.web_routes import referrals
from twobrain_rec_server.cabinet.web_routes.referrals import _referral_landing_html

ROOT = Path(__file__).resolve().parents[2]
VALID_TOKEN = "r1_" + "a" * 64


def _request() -> Request:
    app = SimpleNamespace(
        state=SimpleNamespace(
            settings=SimpleNamespace(billing_checkout_enabled=True),
        )
    )
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": f"/referral/{VALID_TOKEN}",
            "headers": [],
            "query_string": b"",
            "app": app,
        }
    )


@pytest.mark.asyncio
async def test_referral_landing_returns_503_when_database_is_unavailable(monkeypatch) -> None:
    async def unavailable(*_args, **_kwargs):
        raise OperationalError("select", {}, RuntimeError("database is down"))

    monkeypatch.setattr(referrals, "apply_tenant_context", unavailable)
    monkeypatch.setattr(referrals, "public_analytics_page_context", lambda *_a, **_k: {})

    response = await referrals.referral_landing(_request(), VALID_TOKEN, object())

    body = response.body.decode("utf-8")
    assert response.status_code == 503
    assert "Приглашение временно недоступно" in body
    assert "Internal Server Error" not in body


@pytest.mark.asyncio
async def test_referral_landing_returns_410_for_unknown_token(monkeypatch) -> None:
    class EmptyDb:
        async def scalar(self, _query):
            return None

    async def apply_context(*_args, **_kwargs):
        return None

    monkeypatch.setattr(referrals, "apply_tenant_context", apply_context)
    monkeypatch.setattr(referrals, "public_analytics_page_context", lambda *_a, **_k: {})

    response = await referrals.referral_landing(_request(), VALID_TOKEN, EmptyDb())

    body = response.body.decode("utf-8")
    assert response.status_code == 410
    assert "Ссылка недействительна" in body
    assert "Internal Server Error" not in body


@pytest.mark.asyncio
async def test_referral_landing_returns_200_for_active_token(monkeypatch) -> None:
    class ActiveDb:
        async def scalar(self, _query):
            return SimpleNamespace(expires_at=None)

    async def apply_context(*_args, **_kwargs):
        return None

    monkeypatch.setattr(referrals, "apply_tenant_context", apply_context)
    monkeypatch.setattr(referrals, "public_analytics_page_context", lambda *_a, **_k: {})

    response = await referrals.referral_landing(_request(), VALID_TOKEN, ActiveDb())

    body = response.body.decode("utf-8")
    assert response.status_code == 200
    assert "Вас пригласили в GRAF" in body
    assert "graf_referral_token" in response.headers.get("set-cookie", "")
    assert "Internal Server Error" not in body


def test_referral_landing_renders_without_public_analytics() -> None:
    html = _referral_landing_html(state="invalid", public_analytics=None)

    assert "Приглашение в GRAF" in html
    assert "Internal Server Error" not in html


def test_referral_landing_renders_with_public_analytics() -> None:
    html = _referral_landing_html(
        state="valid",
        expires_at_label="1 января 2027",
        public_analytics={"consent_ui_enabled": False},
    )

    assert "Приглашение в GRAF" in html
    assert "Internal Server Error" not in html


def test_offer_copy_matches_checked_auto_renewal_and_four_hour_limit() -> None:
    offer = (ROOT / "src/twobrain_rec_server/public/templates/public/offer.html").read_text(
        encoding="utf-8"
    )
    landing = (ROOT / "src/twobrain_rec_server/public/templates/public/landing.html").read_text(
        encoding="utf-8"
    )

    assert "Автопродление включено по умолчанию" in offer
    assert "Согласие не должно быть заранее отмечено" not in offer
    assert "до 4 часов" in offer
    assert "без ограничения длительности" not in offer
    assert "до 4 часов" in landing
    assert "без ограничения длительности" not in landing
    assert "без лимита по времени" not in landing


def test_checkout_keeps_csrf_post_and_checked_optional_renewal() -> None:
    checkout = (
        ROOT
        / "src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_checkout_content.html"
    ).read_text(encoding="utf-8")

    assert 'action="/billing/checkout/start"' in checkout
    assert 'method="post"' in checkout
    assert "csrf_field(csrf_token" in checkout
    assert 'name="recurring_consent" value="true" checked' in checkout
    assert 'name="recurring_consent" value="true" checked required' not in checkout
