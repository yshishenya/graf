"""Контракт передачи атрибуции от публичной страницы к аккаунту (T041).

Проверяется реальный путь рендера страницы: ``build_public_bridge_context``
создаёт настоящую запись моста и кладёт её в реестр процесса, а не только
описывает поля. Уровни надёжности и отказ от значений идентификаторов взяты из
FR-016, FR-022, FR-023, FR-024, FR-028.
"""

import json
from datetime import UTC, datetime, timedelta

import pytest

from twobrain_rec_server.product_analytics.attribution import (
    APP_HANDOFF_SCHEME,
    ATTRIBUTION_BRIDGE_TTL_HOURS,
    ATTRIBUTION_RELIABILITY_LINKED,
    ATTRIBUTION_RELIABILITY_UNKNOWN,
    ATTRIBUTION_RELIABILITY_WEAK,
    AttributionBridgeRegistry,
    build_app_handoff_url,
    build_public_bridge_context,
    create_attribution_bridge,
    default_attribution_bridge_registry,
    parse_app_handoff_url,
    resolve_attribution_handoff,
)

NOW = datetime(2026, 9, 18, 12, 0, tzinfo=UTC)
CLICK_ID = "1234567890123456789"
# Идентификатор моста того же формата, что выдаёт ``uuid4().hex``.
BRIDGE_ID = "graf_attr_a1b2c3d4e5f60718293a4b5c6d7e8f90"
RELIABILITY_LEVELS = {
    ATTRIBUTION_RELIABILITY_LINKED,
    ATTRIBUTION_RELIABILITY_WEAK,
    ATTRIBUTION_RELIABILITY_UNKNOWN,
}
PAID_CONTEXT = {
    "utm_source": "yandex_direct",
    "utm_medium": "cpc",
    "utm_campaign": "2026q3_b2c_launch_ru",
    "utm_content": "creative_a",
    "referrer_category": "paid",
    "landing_path": "/download",
}
CAMPAIGN_LABELS = {
    "utm_source": "yandex_direct",
    "utm_medium": "cpc",
    "utm_campaign": "2026q3_b2c_launch_ru",
    "utm_id": None,
    "utm_content": "creative_a",
    "utm_term": None,
}


def test_the_bridge_contract_pins_the_scheme_and_the_lifetime() -> None:
    assert APP_HANDOFF_SCHEME == "grafrec"
    assert ATTRIBUTION_BRIDGE_TTL_HOURS == 72
    assert {"linked", "weak", "unknown"} == RELIABILITY_LEVELS


def test_the_public_bridge_context_is_a_real_recorded_bridge() -> None:
    context = build_public_bridge_context({**PAID_CONTEXT, "yclid": CLICK_ID})

    assert context["bridge_supported"] is True
    assert context["graf_attribution_id_required_for_reliable_handoff"] is True
    assert context["graf_attribution_id"].startswith("graf_attr_")
    assert context["attribution_link_state"] == "linked"
    assert context["attribution_reliability"] in RELIABILITY_LEVELS
    # Срок жизни моста лежит внутри окна атрибуции в 90 дней (FR-014).
    moment = datetime.now(UTC)
    expires_at = datetime.fromisoformat(context["bridge_expires_at"])
    assert moment < expires_at <= moment + timedelta(days=90)
    # Контекст страницы — это настоящая запись реестра процесса, а не описание
    # полей: рендер страницы создаёт мост (FR-022).
    registry = default_attribution_bridge_registry()
    assert registry.resolve(context["graf_attribution_id"]) is not None


def test_the_bridge_reports_the_click_identifier_only_as_presence() -> None:
    with_click = build_public_bridge_context({**PAID_CONTEXT, "yclid": CLICK_ID})
    without_click = build_public_bridge_context(PAID_CONTEXT)

    assert with_click["yclid_present"] is True
    assert "Yclid" in with_click["yandex_identity_sources_present"]
    assert without_click["yclid_present"] is False
    assert "Yclid" not in without_click["yandex_identity_sources_present"]
    # Идентификатор клика существует только как флаг присутствия: ни в контексте
    # страницы, ни в ссылке передачи приложения нет его значения (FR-016, FR-028).
    assert CLICK_ID not in json.dumps(with_click, ensure_ascii=False)


@pytest.mark.parametrize(
    "private_label",
    ["user@example.com", "8-800-555-35-35", "+7 999 111 22 33"],
)
def test_a_private_looking_campaign_label_is_dropped_without_raising(private_label: str) -> None:
    # Метка, похожая на личные данные, отбрасывается молча: страница обязана
    # продолжать отрисовываться (FR-011, FR-014).
    context = build_public_bridge_context(
        {**PAID_CONTEXT, "utm_term": private_label, "utm_content": private_label}
    )

    assert context["source_context"]["utm_term"] is None
    assert context["source_context"]["utm_content"] is None
    assert private_label not in json.dumps(context, ensure_ascii=False)
    # Отброшенная метка не мешает остальным меткам визита и самому мосту.
    assert context["source_context"]["utm_campaign"] == "2026q3_b2c_launch_ru"
    assert (
        default_attribution_bridge_registry().resolve(context["graf_attribution_id"]) is not None
    )


def test_the_bridge_identifier_resolves_back_to_the_same_campaign_labels() -> None:
    registry = AttributionBridgeRegistry()
    bridge = create_attribution_bridge(
        source_context=PAID_CONTEXT,
        bridge_id=BRIDGE_ID,
        now=NOW,
    )
    registry.record(bridge)
    assert len(registry) == 1

    handoff = resolve_attribution_handoff(
        {"bridge": bridge.graf_attribution_id}, registry=registry, now=NOW
    )

    assert handoff is not None
    assert handoff.graf_attribution_id == BRIDGE_ID
    assert handoff.campaign_known() is True
    assert handoff.campaign_context == CAMPAIGN_LABELS
    assert handoff.fallback_recovered is False
    assert handoff.reliability(account_connected=True) == ATTRIBUTION_RELIABILITY_LINKED


def test_an_expired_bridge_no_longer_resolves() -> None:
    registry = AttributionBridgeRegistry(clock=lambda: NOW)
    live = create_attribution_bridge(
        source_context=PAID_CONTEXT,
        bridge_id="graf_attr_1a2b3c4d5e6f70819a2b3c4d5e6f7081",
        ttl_hours=2,
        now=NOW,
    )
    expired_for_handoff = create_attribution_bridge(
        source_context=PAID_CONTEXT,
        bridge_id="graf_attr_1a2b3c4d5e6f70819a2b3c4d5e6f7082",
        ttl_hours=1,
        now=NOW,
    )
    expired_for_registry = create_attribution_bridge(
        source_context=PAID_CONTEXT,
        bridge_id="graf_attr_1a2b3c4d5e6f70819a2b3c4d5e6f7083",
        ttl_hours=1,
        now=NOW,
    )
    for bridge in (live, expired_for_handoff, expired_for_registry):
        registry.record(bridge)

    within_lifetime = resolve_attribution_handoff(
        {"bridge": live.graf_attribution_id},
        registry=registry,
        now=NOW + timedelta(minutes=30),
    )
    assert within_lifetime is not None
    assert within_lifetime.campaign_context == CAMPAIGN_LABELS

    beyond_lifetime = NOW + timedelta(hours=2)
    # Просроченный мост больше не отдаёт метки кампании: событие остаётся
    # честно несвязанным, а не получает выдуманную атрибуцию (FR-023, FR-024).
    stale = resolve_attribution_handoff(
        {"bridge": expired_for_handoff.graf_attribution_id},
        registry=registry,
        now=beyond_lifetime,
    )
    assert stale is not None
    assert stale.campaign_known() is False
    assert all(value is None for value in stale.campaign_context.values())
    assert stale.reliability(account_connected=True) == ATTRIBUTION_RELIABILITY_UNKNOWN
    assert registry.resolve(expired_for_registry.graf_attribution_id, now=beyond_lifetime) is None


def test_the_app_handoff_link_round_trips_labels_and_landing_path() -> None:
    bridge = create_attribution_bridge(
        source_context={**PAID_CONTEXT, "yclid": CLICK_ID},
        bridge_id=BRIDGE_ID,
        now=NOW,
    )

    url = build_app_handoff_url(bridge)

    assert url.startswith("grafrec://attribution?")
    # Значения идентификаторов не едут в ссылке: только метки кампании и путь.
    assert CLICK_ID not in url
    assert "yclid" not in url
    assert bridge.yclid_present is True
    assert "yclid" not in bridge.source_context

    handoff = parse_app_handoff_url(url)

    assert handoff is not None
    assert handoff.graf_attribution_id == BRIDGE_ID
    # Резервный путь восстановления связки всегда помечается (FR-022).
    assert handoff.fallback_recovered is True
    assert handoff.landing_path == "/download"
    assert handoff.campaign_context == CAMPAIGN_LABELS
    assert handoff.campaign_known() is True
    assert handoff.reliability(account_connected=True) == ATTRIBUTION_RELIABILITY_WEAK


def test_a_bridge_lifetime_outside_the_allowed_window_is_refused() -> None:
    for invalid in (0, -1, 2161):
        with pytest.raises(ValueError):
            create_attribution_bridge(source_context=PAID_CONTEXT, ttl_hours=invalid)
        with pytest.raises(ValueError):
            build_public_bridge_context(PAID_CONTEXT, ttl_hours=invalid)

    for allowed in (1, 90 * 24):
        bridge = create_attribution_bridge(source_context=PAID_CONTEXT, ttl_hours=allowed)
        assert bridge.graf_attribution_id.startswith("graf_attr_")
        assert bridge.expires_at - bridge.created_at == timedelta(hours=allowed)
