"""FR-018: метки кампании в конверсионном событии.

Требование говорит две вещи, и обе проверяются здесь на настоящем сервисе
приема событий, а не на описании:

* каждое конверсионное событие несет исходную кампанию — те самые метки
  ``utm_source``, ``utm_medium``, ``utm_campaign``, а не только уровень
  надежности связи;
* отсутствие кампании отличимо от «прямого захода»: событие без кампании несет
  явное ``unknown`` и пустые метки, и слово ``direct`` не появляется в нем
  нигде (FR-024).

Запрещенные поля проверяет общий механизм проекта
(:func:`find_forbidden_fields` и :func:`assert_no_forbidden_fields`), а не
список, собранный этим тестом: иначе тест проверял бы сам себя.
"""

from __future__ import annotations

import json
from uuid import uuid4

import pytest

from twobrain_rec_server.config import Settings
from twobrain_rec_server.product_analytics.acquisition import DIRECT_REFERRER_CATEGORY
from twobrain_rec_server.product_analytics.attribution import (
    ATTRIBUTION_RELIABILITY_UNKNOWN,
    CAMPAIGN_LABEL_FIELDS,
    CAMPAIGN_LABEL_STATE_KNOWN,
    CAMPAIGN_LABEL_STATE_UNKNOWN,
    CAMPAIGN_LABEL_STATES,
)
from twobrain_rec_server.product_analytics.event_catalog import (
    PRODUCT_ACTIVATION_EVENT_NAMES,
    get_event_definition,
)
from twobrain_rec_server.product_analytics.forbidden_fields import (
    find_forbidden_fields,
)
from twobrain_rec_server.product_analytics.identity import build_safe_identity
from twobrain_rec_server.product_analytics.ingest import ProductAnalyticsIngestService
from twobrain_rec_server.product_analytics.milestones import milestone_attribution_properties

CAMPAIGN = {
    "utm_source": "Yandex_Direct",
    "utm_medium": "CPC",
    "utm_campaign": "2026q3_b2c_launch_ru",
    "utm_content": "creative_a",
    "utm_term": "kupit_zapis",
}
# Значение, которое обязано быть отброшено: адрес почты в метке кампании.
PRIVATE_LABEL = "customer@example.com"


def _service() -> ProductAnalyticsIngestService:
    return ProductAnalyticsIngestService(Settings(product_analytics_enabled=True))


def _ingest(properties: dict[str, object]):
    identity = build_safe_identity(user_source_id=str(uuid4()))
    result = _service().ingest(
        {
            "event_name": "desktop_account_connected",
            "stable_pseudonymous_user_id": identity.stable_pseudonymous_user_id,
            "properties": properties,
        }
    )
    assert result.accepted is True
    assert result.event is not None
    return result.event


def test_every_conversion_event_may_carry_the_campaign_labels() -> None:
    # Каталог событий — это allowlist: построитель не может добавить поле, пока
    # каталог его не разрешает (FR-018).
    for event_name in PRODUCT_ACTIVATION_EVENT_NAMES:
        allowed = set(get_event_definition(event_name).allowed_fields)
        assert {"campaign_label_state", *CAMPAIGN_LABEL_FIELDS} <= allowed, event_name


def test_a_known_campaign_reaches_the_event_as_safe_labels() -> None:
    event = _ingest(milestone_attribution_properties(campaign_context=CAMPAIGN))

    assert event.properties["campaign_label_state"] == CAMPAIGN_LABEL_STATE_KNOWN
    # Источник и канал приводятся к нижнему регистру тем же правилом, что и в
    # записи о визите, поэтому одна кампания читается как один канал.
    assert event.properties["utm_source"] == "yandex_direct"
    assert event.properties["utm_medium"] == "cpc"
    assert event.properties["utm_campaign"] == "2026q3_b2c_launch_ru"
    assert event.properties["utm_content"] == "creative_a"
    assert event.properties["utm_term"] == "kupit_zapis"
    # Уровень выводится из той же кампании, а не задается отдельно.
    assert event.properties["attribution_reliability"] != ATTRIBUTION_RELIABILITY_UNKNOWN


def test_a_campaign_nobody_knows_is_explicitly_unknown_and_never_direct() -> None:
    for properties in (
        milestone_attribution_properties(),
        milestone_attribution_properties(campaign_context=None),
        milestone_attribution_properties(campaign_context={}),
        # Прямой заход — это свойство источника визита, а не метка кампании:
        # даже названный явно, он не становится кампанией события (FR-024).
        milestone_attribution_properties(
            campaign_context={"referrer_category": DIRECT_REFERRER_CATEGORY}
        ),
    ):
        event = _ingest(properties)

        assert event.properties["campaign_label_state"] == CAMPAIGN_LABEL_STATE_UNKNOWN
        assert event.properties["attribution_reliability"] == ATTRIBUTION_RELIABILITY_UNKNOWN
        for field in CAMPAIGN_LABEL_FIELDS:
            assert event.properties[field] is None, field
        assert DIRECT_REFERRER_CATEGORY not in event.properties.values()
        # Ни в самом событии, ни в его сериализованном виде.
        assert DIRECT_REFERRER_CATEGORY not in json.dumps(event.as_payload(), ensure_ascii=False)


def test_the_state_vocabulary_has_no_direct_value() -> None:
    assert CAMPAIGN_LABEL_STATES == (CAMPAIGN_LABEL_STATE_KNOWN, CAMPAIGN_LABEL_STATE_UNKNOWN)
    assert DIRECT_REFERRER_CATEGORY not in CAMPAIGN_LABEL_STATES


def test_a_label_that_looks_like_private_data_is_dropped_before_the_event() -> None:
    event = _ingest(
        milestone_attribution_properties(
            campaign_context={
                "utm_source": "yandex_direct",
                "utm_campaign": PRIVATE_LABEL,
                "utm_content": "https://private.example/signed?token=abc",
                "utm_term": "+7 999 111 22 33",
            }
        )
    )

    assert event.properties["utm_source"] == "yandex_direct"
    assert event.properties["utm_campaign"] is None
    assert event.properties["utm_content"] is None
    assert event.properties["utm_term"] is None
    assert PRIVATE_LABEL not in json.dumps(event.as_payload(), ensure_ascii=False)


def test_the_shared_forbidden_field_check_accepts_the_event_and_rejects_a_leak() -> None:
    """Проверка запрещенных полей — общая, и она же ловит подмену метки."""
    properties = milestone_attribution_properties(campaign_context=CAMPAIGN)
    event = _ingest(properties)
    payload = event.as_payload()
    described = {key: value for key, value in payload.items() if key != "occurred_at"}

    # Общий механизм не находит в событии ничего запрещенного. Единственное,
    # что он видит во всем событии, — служебная метка времени: шаблон телефона
    # читает ISO-дату «2026-09-18» как номер. Это свойство самой проверки, а не
    # данных события.
    assert find_forbidden_fields(described) == ()
    assert set(find_forbidden_fields(payload)) <= {"$.occurred_at"}

    # Тот же механизм отвергает метку, которая несет адрес почты: значит,
    # проверка выше прошла не потому, что список полей пуст.
    leaked = _ingest(
        milestone_attribution_properties(campaign_context={"utm_campaign": "clean_campaign"})
    )
    leaked_payload = {
        key: value
        for key, value in leaked.as_payload().items()
        if key != "occurred_at"
    }
    leaked_payload["properties"]["utm_campaign"] = PRIVATE_LABEL
    assert find_forbidden_fields(leaked_payload) != ()


@pytest.mark.parametrize("campaign_context", [CAMPAIGN, {}, None])
def test_the_event_always_names_every_campaign_label(campaign_context) -> None:
    # Отсутствие метки и отсутствие кампании — разные вещи: событие всегда
    # называет все метки контракта, поэтому читатель видит и то, и другое.
    event = _ingest(milestone_attribution_properties(campaign_context=campaign_context))

    assert set(CAMPAIGN_LABEL_FIELDS) <= set(event.properties)
