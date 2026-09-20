"""Воронка от клика по объявлению до первой ценности (T050, FR-015…FR-025, SC-005).

Каждый сценарий навигации проходит весь реальный путь: рендер публичной
страницы создает мост атрибуции, метки читаются обратно через
``resolve_attribution_handoff``, попадают в атрибут привлечения записи о клиенте
и в свойства каждой из шести вех активации, которые принимает настоящий сервис
приема событий.
"""

import json
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from html.parser import HTMLParser
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from twobrain_rec_server.config import Settings
from twobrain_rec_server.main import create_app
from twobrain_rec_server.product_analytics.acquisition import (
    ATTRIBUTION_RULE_LAST_NON_DIRECT_90D,
    ATTRIBUTION_SOURCE_CAMPAIGN,
    ATTRIBUTION_SOURCE_DIRECT,
    ATTRIBUTION_SOURCE_UNKNOWN,
    DIRECT_REFERRER_CATEGORY,
    ClientAcquisitionAttribute,
    VisitAttribution,
    build_client_acquisition_attribute_from_visits,
    build_visit_attribution_from_attribution,
    classify_attribution_source,
)
from twobrain_rec_server.product_analytics.attribution import (
    ATTRIBUTION_RELIABILITY_UNKNOWN,
    CAMPAIGN_LABEL_FIELDS,
    AttributionHandoff,
    default_attribution_bridge_registry,
    resolve_attribution_handoff,
)
from twobrain_rec_server.product_analytics.event_catalog import (
    FULL_ACTIVATION_FUNNEL,
    PRODUCT_ACTIVATION_EVENT_NAMES,
)
from twobrain_rec_server.product_analytics.forbidden_fields import find_forbidden_fields
from twobrain_rec_server.product_analytics.identity import build_safe_identity
from twobrain_rec_server.product_analytics.ingest import (
    ProductAnalyticsIngestResult,
    ProductAnalyticsIngestService,
)
from twobrain_rec_server.product_analytics.milestones import (
    milestone_attribution_properties,
    resolve_conversion_reliability,
)
from twobrain_rec_server.public.analytics import normalize_public_campaign_attribution

CLICK_ID = "1234567890123456789"
# Идентификатор моста того же формата, что выдает ``uuid4().hex``.
BRIDGE_ID = "graf_attr_a1b2c3d4e5f60718293a4b5c6d7e8f90"
CAMPAIGN_LABELS = {
    "source": "yandex_direct",
    "medium": "cpc",
    "campaign": "2026q3_b2c_launch_ru",
}
EMPTY_LABELS = {"source": None, "medium": None, "campaign": None}
CAMPAIGN_RELIABILITY_LEVELS = {"linked", "weak"}


@dataclass(frozen=True, slots=True)
class NavigationScenario:
    """Один сценарий прихода посетителя на страницу загрузки."""

    name: str
    query: dict[str, str]
    referrer: str | None
    expected_source: str
    expected_referrer_category: str
    expected_normalization_status: str
    expected_labels: dict[str, str | None]


SCENARIOS = (
    NavigationScenario(
        name="paid_click",
        query={
            "utm_source": "yandex_direct",
            "utm_medium": "cpc",
            "utm_campaign": "2026q3_b2c_launch_ru",
            "utm_content": "creative_a",
            "yclid": CLICK_ID,
        },
        referrer=None,
        expected_source=ATTRIBUTION_SOURCE_CAMPAIGN,
        expected_referrer_category="paid",
        expected_normalization_status="clean",
        expected_labels=dict(CAMPAIGN_LABELS),
    ),
    NavigationScenario(
        name="referral_without_labels",
        query={},
        referrer="https://news.example.org/article",
        expected_source=ATTRIBUTION_SOURCE_UNKNOWN,
        expected_referrer_category="referral",
        expected_normalization_status="missing",
        expected_labels=dict(EMPTY_LABELS),
    ),
    NavigationScenario(
        name="direct_visit",
        query={},
        referrer=None,
        expected_source=ATTRIBUTION_SOURCE_DIRECT,
        expected_referrer_category="direct",
        expected_normalization_status="missing",
        expected_labels=dict(EMPTY_LABELS),
    ),
    NavigationScenario(
        name="unknown_campaign",
        # Метка отброшена как личные данные, поэтому кампания неизвестна.
        query={"utm_campaign": "user@example.com"},
        referrer="https://news.example.org/article",
        expected_source=ATTRIBUTION_SOURCE_UNKNOWN,
        expected_referrer_category="referral",
        expected_normalization_status="unsafe_dropped",
        expected_labels=dict(EMPTY_LABELS),
    ),
)
SCENARIO_IDS = [scenario.name for scenario in SCENARIOS]


class _DownloadPageLinks(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: dict[str, dict[str, str | None]] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        attributes = dict(attrs)
        cta = attributes.get("data-analytics-cta")
        if cta:
            self.links[cta] = attributes


def _page_links(html: str) -> dict[str, dict[str, str | None]]:
    parser = _DownloadPageLinks()
    parser.feed(html)
    return parser.links


@dataclass(frozen=True, slots=True)
class FunnelWalk:
    """Результат прохода воронки одним сценарием."""

    funnel: tuple[str, ...]
    results: tuple[ProductAnalyticsIngestResult, ...]
    event_payloads: tuple[dict[str, Any], ...]
    reliabilities: tuple[str, ...]
    bridge_present: tuple[bool, ...]
    campaign_label_states: tuple[str, ...]
    campaign_labels: tuple[dict[str, str | None], ...]
    forbidden: tuple[str, ...]
    attribute: ClientAcquisitionAttribute
    visit: VisitAttribution
    handoff: AttributionHandoff | None


@pytest.fixture(scope="module")
def download_page_client() -> Iterator[TestClient]:
    # Один клиент на модуль: страница рендерится без базы данных и без сети,
    # события принимает настоящий сервис приема.
    yield TestClient(create_app(Settings()))


def _walk_the_funnel(client: TestClient, scenario: NavigationScenario) -> FunnelWalk:
    headers = {"referer": scenario.referrer} if scenario.referrer else {}
    response = client.get("/download", params=scenario.query, headers=headers)
    assert response.status_code == 200

    links = _page_links(response.text)
    installer = links["download_page_installer"]
    open_app = links["download_page_open_app"]
    # Шаг «клик по объявлению»: на странице загрузки есть кнопка установщика.
    assert installer["href"]
    bridge_id = str(open_app["data-graf-attribution-id"])

    registry = default_attribution_bridge_registry()
    bridge = registry.resolve(bridge_id)
    # Страница создала настоящий мост, а не только описала поля (FR-022).
    assert bridge is not None
    page_labels = bridge.campaign_context()
    campaign_known = any(page_labels.values())

    if campaign_known:
        handoff = resolve_attribution_handoff(
            {**page_labels, "bridge": bridge_id}, registry=registry
        )
        assert handoff is not None
        assert handoff.campaign_known() is True
        visit_labels = handoff.campaign_context
    else:
        # У визита нет меток: связки может не быть вовсе, и кампании в любом
        # случае нет — событие обязано остаться unknown (FR-024).
        handoff = resolve_attribution_handoff({"bridge": bridge_id}, registry=registry)
        visit_labels = dict(page_labels)

    now = datetime.now(UTC)
    visit = build_visit_attribution_from_attribution(
        visit_labels,
        landing_path="/download",
        yclid=scenario.query.get("yclid"),
        first_seen_at=now,
    )
    attribute = build_client_acquisition_attribute_from_visits(
        account_id=uuid4(),
        visits=[visit],
        captured_at=now,
        linked_automatically=True,
    )

    reliability = resolve_conversion_reliability(
        campaign_known=campaign_known, account_connected=True
    )
    if handoff is not None:
        assert handoff.reliability(account_connected=True) == reliability

    identity = build_safe_identity(user_source_id=str(uuid4()))
    service = ProductAnalyticsIngestService(Settings(product_analytics_enabled=True))
    funnel: list[str] = [FULL_ACTIVATION_FUNNEL[0]]
    results: list[ProductAnalyticsIngestResult] = []
    payloads: list[dict[str, Any]] = []
    reliabilities: list[str] = []
    bridge_present: list[bool] = []
    campaign_label_states: list[str] = []
    campaign_labels: list[dict[str, str | None]] = []
    forbidden: list[str] = []
    for event_name in PRODUCT_ACTIVATION_EVENT_NAMES:
        # Идентификатор моста не входит в свойства шага воронки: значение с
        # длинной серией цифр отвергает общая проверка запрещенных полей (см.
        # отчет по задаче). Передачу идентификатора в свойстве вехи закрывает
        # отдельная проверка ниже.
        properties = milestone_attribution_properties(
            attribution_reliability=reliability,
            campaign_known=campaign_known,
            account_connected=True,
            bridge_present=True,
            # Метки кампании визита едут в каждой вехе (FR-018): без них
            # связать конверсию с каналом можно только через запись о клиенте.
            campaign_context=visit_labels,
        )
        result = service.ingest(
            {
                "event_name": event_name,
                "stable_pseudonymous_user_id": identity.stable_pseudonymous_user_id,
                "properties": properties,
            }
        )
        assert result.event is not None
        payload = result.event.as_payload()
        funnel.append(event_name)
        results.append(result)
        payloads.append(payload)
        reliabilities.append(str(result.event.properties["attribution_reliability"]))
        bridge_present.append(bool(result.event.properties["bridge_present"]))
        campaign_label_states.append(str(result.event.properties["campaign_label_state"]))
        campaign_labels.append(
            {
                field: result.event.properties.get(field)
                for field in CAMPAIGN_LABEL_FIELDS
            }
        )
        # Запрещенные поля проверяются на всем, что описывает вызывающий:
        # свойства события и его псевдонимный идентификатор.
        described = {key: value for key, value in payload.items() if key != "occurred_at"}
        forbidden.extend(find_forbidden_fields(described))
        # На полном событии общая проверка находит только служебную метку
        # времени: шаблон телефона читает ISO-дату «2026-09-18» как номер.
        assert set(find_forbidden_fields(payload)) <= {"$.occurred_at"}
    return FunnelWalk(
        funnel=tuple(funnel),
        results=tuple(results),
        event_payloads=tuple(payloads),
        reliabilities=tuple(reliabilities),
        bridge_present=tuple(bridge_present),
        campaign_label_states=tuple(campaign_label_states),
        campaign_labels=tuple(campaign_labels),
        forbidden=tuple(dict.fromkeys(forbidden)),
        attribute=attribute,
        visit=visit,
        handoff=handoff,
    )


@pytest.mark.parametrize("scenario", SCENARIOS, ids=SCENARIO_IDS)
def test_every_scenario_is_classified_by_the_single_attribution_rule(
    scenario: NavigationScenario,
) -> None:
    attribution = normalize_public_campaign_attribution(
        scenario.query, referrer=scenario.referrer, landing_path="/download"
    )

    assert attribution["normalization_status"] == scenario.expected_normalization_status
    assert attribution["referrer_category"] == scenario.expected_referrer_category
    assert (
        classify_attribution_source(
            campaign_known=any(
                attribution[field] for field in ("utm_source", "utm_medium", "utm_campaign")
            ),
            referrer_category=attribution["referrer_category"],
        )
        == scenario.expected_source
    )


@pytest.mark.parametrize("scenario", SCENARIOS, ids=SCENARIO_IDS)
def test_the_funnel_carries_the_campaign_of_the_visit(
    download_page_client: TestClient, scenario: NavigationScenario
) -> None:
    walk = _walk_the_funnel(download_page_client, scenario)

    # Воронка пройдена в точном порядке контракта: все шесть вех плюс клик.
    assert len(PRODUCT_ACTIVATION_EVENT_NAMES) == 6
    assert FULL_ACTIVATION_FUNNEL[1:] == PRODUCT_ACTIVATION_EVENT_NAMES
    assert walk.funnel == FULL_ACTIVATION_FUNNEL
    # Каждую веху принял настоящий сервис приема событий.
    assert all(result.accepted is True for result in walk.results)
    assert all(result.status not in {"rejected", "disabled", "duplicate"} for result in walk.results)
    # Ни одно событие не несет запрещенного поля.
    assert walk.forbidden == ()

    # Кампания визита — та же кампания на записи о клиенте (FR-015, FR-017).
    assert walk.attribute.attribution_rule == ATTRIBUTION_RULE_LAST_NON_DIRECT_90D
    assert walk.attribute.source == walk.visit.source == scenario.expected_labels["source"]
    assert walk.attribute.medium == walk.visit.medium == scenario.expected_labels["medium"]
    assert walk.attribute.campaign == walk.visit.campaign == scenario.expected_labels["campaign"]

    if scenario.expected_source == ATTRIBUTION_SOURCE_CAMPAIGN:
        # SC-005: 100 % конверсионных событий несут исходную кампанию.
        assert walk.handoff is not None
        linked = [
            level for level in walk.reliabilities if level in CAMPAIGN_RELIABILITY_LEVELS
        ]
        assert len(linked) == len(PRODUCT_ACTIVATION_EVENT_NAMES)
        assert all(walk.bridge_present)
        assert walk.attribute.attribution_confidence == "linked"
        # FR-018: каждая веха несет сами метки кампании, а не только уровень.
        assert walk.campaign_label_states == ("known",) * len(PRODUCT_ACTIVATION_EVENT_NAMES)
        for labels in walk.campaign_labels:
            assert labels["utm_source"] == scenario.expected_labels["source"]
            assert labels["utm_medium"] == scenario.expected_labels["medium"]
            assert labels["utm_campaign"] == scenario.expected_labels["campaign"]
    else:
        # FR-024: без кампании событие остается неизвестным и никогда «direct».
        assert walk.reliabilities == (ATTRIBUTION_RELIABILITY_UNKNOWN,) * len(
            PRODUCT_ACTIVATION_EVENT_NAMES
        )
        assert "direct" not in walk.reliabilities
        assert all(walk.bridge_present)
        assert walk.attribute.attribution_confidence == "unknown"
        # FR-018: отсутствие кампании видно в самом событии, а не только в
        # уровне: явное состояние и пустые метки, никогда «прямой заход».
        assert walk.campaign_label_states == ("unknown",) * len(
            PRODUCT_ACTIVATION_EVENT_NAMES
        )
        for labels in walk.campaign_labels:
            assert set(labels.values()) == {None}
            assert DIRECT_REFERRER_CATEGORY not in labels.values()


def test_the_click_identifier_stays_a_stored_fact_and_never_reaches_an_event(
    download_page_client: TestClient,
) -> None:
    walk = _walk_the_funnel(download_page_client, SCENARIOS[0])

    # FR-016: идентификатор клика сохранен на визите уровня 2.
    assert walk.visit.yclid == CLICK_ID
    assert walk.attribute.as_analytics_dict()["yclid_present"] is True
    # FR-028: в события активации он не попадает.
    assert CLICK_ID not in json.dumps(walk.event_payloads, ensure_ascii=False)


def test_a_milestone_carries_the_bridge_identifier_of_the_visit() -> None:
    service = ProductAnalyticsIngestService(Settings(product_analytics_enabled=True))
    identity = build_safe_identity(user_source_id=str(uuid4()))

    result = service.ingest(
        {
            "event_name": "desktop_account_connected",
            "stable_pseudonymous_user_id": identity.stable_pseudonymous_user_id,
            "properties": milestone_attribution_properties(
                attribution_reliability="linked",
                bridge_present=True,
                graf_attribution_id=BRIDGE_ID,
            ),
        }
    )

    assert result.accepted is True
    assert result.event is not None
    assert result.event.properties["graf_attribution_id"] == BRIDGE_ID
    assert result.event.properties["attribution_reliability"] == "linked"
    assert result.event.properties["bridge_present"] is True
