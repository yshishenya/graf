from datetime import UTC, datetime
from types import SimpleNamespace

from twobrain_rec_server.billing.catalog import plan_descriptor
from twobrain_rec_server.billing.usage import format_duration
from twobrain_rec_server.cabinet.templates import render_template
from twobrain_rec_server.cabinet.view_models import settings_category_navigation


def test_billing_hub_uses_exact_free_copy_and_external_refund_boundary() -> None:
    html = render_template(
        "cabinet/pages/billing_overview_content.html",
        embedded=False,
        settings_navigation=settings_category_navigation(active="billing"),
        settings_active="billing",
        plan=plan_descriptor("free"),
        plan_code="free",
        storage_used=0,
        storage_capacity=250_000_000,
        storage_threshold="normal",
        processing_used=0,
        processing_used_label=format_duration(0),
        free_processing_limit_label=format_duration(18_000),
        storage_capacity_label="250 000 000",
        processing_threshold="normal",
        billing_enabled=False,
        trial_result=None,
    )
    assert "0 мин 0 сек" in html
    assert "300 мин 0 сек (18 000 сек)" in html
    assert "250 000 000 байт" in html
    assert "только письмом" in html
    assert "автоматической заявки" in html


def test_subscription_and_usage_surfaces_keep_no_grace_and_unlimited_copy() -> None:
    common = {
        "embedded": False,
        "settings_navigation": settings_category_navigation(active="billing"),
        "settings_active": "billing",
        "csrf_token": "synthetic-csrf",
    }
    subscription_html = render_template(
        "cabinet/pages/billing_subscription_content.html",
        **common,
        subscription=SimpleNamespace(
            plan_code="personal",
            paid_through=datetime(2026, 9, 1, tzinfo=UTC),
            recurring_allowed=False,
            recurring_authority_version=1,
        ),
        active=True,
        result=None,
    )
    usage_html = render_template(
        "cabinet/pages/billing_usage_content.html",
        **common,
        plan_code="personal",
        processing_used=0,
        processing_used_label="0 мин 0 сек",
        free_processing_limit_label="300 мин 0 сек",
        processing_threshold="normal",
        processing_unlimited=True,
        storage_used=0,
        storage_reserved=0,
        storage_available=2_000_000_000,
        storage_capacity=2_000_000_000,
        storage_threshold="normal",
    )
    assert "Возобновить автопродление" in subscription_html
    assert "Без лимита по минутам и встречам" in usage_html
    assert "meeting-review.m4a" in usage_html
