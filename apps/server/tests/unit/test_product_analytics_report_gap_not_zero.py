"""Пробел в данных показывается как пробел, а не как ноль (T060; FR-040).

Проверяется правило из ``infra/analytics/dashboards/catalog.json`` (раздел
``empty_value_policy``) и его связь с настоящим кодом доставки: пробел возникает
там, где модуль пробелов доставки пометил событие как ``measurement_gap``.

Главное утверждение: неделя с одним пропущенным днём не даёт итогового числа.
Иначе владелец прочитает неполную сумму как отсутствие интереса.
"""

import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from twobrain_rec_server.product_analytics.anonymous_aggregate import is_disclosed_bucket
from twobrain_rec_server.product_analytics.delivery_gap import build_delivery_gap
from twobrain_rec_server.product_analytics.posthog_client import ProviderDeliveryResult

REPO_ROOT = Path(__file__).parents[4]
CATALOG_PATH = REPO_ROOT / "infra" / "analytics" / "dashboards" / "catalog.json"

DELIVERED = "delivered"
GAP = "gap"
NO_DATA = "no_data"
TRUE_ZERO = "true_zero"
MEASURED = "measured"
SUPPRESSED = "suppressed_small_bucket"
UNDEFINED = "нет данных"


@dataclass(frozen=True, slots=True)
class DayObservation:
    """Один день периода: подтверждена доставка или нет."""

    day: str
    delivery: str
    events: int = 0


def day_status_from_delivery(results: Sequence[ProviderDeliveryResult]) -> str:
    """День помечается пробелом, когда модуль пробелов доставки нашёл разрыв."""
    gap = build_delivery_gap("public_landing_viewed", list(results))
    return GAP if gap is not None else DELIVERED


def resolve_day_value(observation: DayObservation) -> tuple[str, int | None]:
    """Значение одного дня по правилам политики пустого значения."""
    if observation.delivery == GAP:
        return NO_DATA, None
    if observation.events == 0:
        return TRUE_ZERO, 0
    return MEASURED, observation.events


def resolve_period_value(observations: Sequence[DayObservation]) -> tuple[str, int | None]:
    """Итог периода. Пробел в любом дне отменяет итоговое число."""
    resolved = [resolve_day_value(observation) for observation in observations]
    if any(state == NO_DATA for state, _ in resolved):
        return NO_DATA, None
    total = sum(value for _, value in resolved if value is not None)
    if total == 0:
        return TRUE_ZERO, 0
    return MEASURED, total


def render(state: str, value: int | None) -> str:
    """Как значение показывается владельцу."""
    if state == NO_DATA:
        return UNDEFINED
    if state == SUPPRESSED:
        return "скрыто: мало данных"
    assert value is not None
    return str(value)


def _catalog() -> dict:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def _delivered(events: int) -> list[ProviderDeliveryResult]:
    return [ProviderDeliveryResult(provider="posthog", status="delivered", detail="ok", metadata={})]


def _failed() -> list[ProviderDeliveryResult]:
    return [
        ProviderDeliveryResult(
            provider="posthog",
            status="failed",
            detail="transport_error",
            metadata={},
        )
    ]


def test_failed_delivery_is_marked_as_a_measurement_gap() -> None:
    assert day_status_from_delivery(_delivered(4)) == DELIVERED
    assert day_status_from_delivery(_failed()) == GAP


def test_gap_day_is_rendered_as_no_data_and_not_as_zero() -> None:
    observation = DayObservation(day="2026-09-03", delivery=GAP, events=0)

    state, value = resolve_day_value(observation)

    assert state == NO_DATA
    assert value is None
    assert render(state, value) == UNDEFINED
    assert render(state, value) != "0"


def test_confirmed_day_without_events_is_a_real_zero() -> None:
    observation = DayObservation(day="2026-09-03", delivery=DELIVERED, events=0)

    state, value = resolve_day_value(observation)

    assert state == TRUE_ZERO
    assert value == 0
    assert render(state, value) == "0"


def test_week_with_a_gap_has_no_total_instead_of_a_partial_sum() -> None:
    week = [
        DayObservation("2026-09-01", DELIVERED, 3),
        DayObservation("2026-09-02", DELIVERED, 2),
        DayObservation("2026-09-03", GAP, 0),
        DayObservation("2026-09-04", DELIVERED, 4),
        DayObservation("2026-09-05", DELIVERED, 1),
        DayObservation("2026-09-06", DELIVERED, 2),
        DayObservation("2026-09-07", DELIVERED, 2),
    ]

    state, value = resolve_period_value(week)

    assert state == NO_DATA
    assert value is None
    assert render(state, value) == UNDEFINED
    # Неполная сумма двенадцати событий не выдаётся за итог недели.
    assert render(state, value) != "12"


def test_fully_delivered_week_reports_the_real_total() -> None:
    week = [
        DayObservation("2026-09-01", DELIVERED, 3),
        DayObservation("2026-09-02", DELIVERED, 2),
        DayObservation("2026-09-03", DELIVERED, 0),
    ]

    state, value = resolve_period_value(week)

    assert state == MEASURED
    assert value == 5
    assert render(state, value) == "5"


def test_week_without_any_events_is_a_real_zero() -> None:
    week = [DayObservation("2026-09-01", DELIVERED, 0), DayObservation("2026-09-02", DELIVERED, 0)]

    state, value = resolve_period_value(week)

    assert state == TRUE_ZERO
    assert value == 0
    assert render(state, value) == "0"


def test_small_bucket_is_suppressed_and_never_shown_as_zero() -> None:
    assert is_disclosed_bucket(1) is False
    assert is_disclosed_bucket(2) is False
    assert is_disclosed_bucket(3) is True
    assert render(SUPPRESSED, None) == "скрыто: мало данных"
    assert render(SUPPRESSED, None) != "0"


def test_unknown_consent_share_is_not_zero() -> None:
    catalog = _catalog()
    policy = catalog["empty_value_policy"]

    consent_report = next(report for report in catalog["reports"] if report["slug"] == "consent-coverage")
    assert "нет данных" in consent_report["empty_state"]["no_data"]
    assert policy["meaning"]["no_data"].strip()
    # Доля неизмеренного согласия — пробел, а не нулевая доля.
    assert render(NO_DATA, None) == UNDEFINED


def test_catalog_policy_forbids_zero_for_a_gap() -> None:
    policy = _catalog()["empty_value_policy"]

    assert policy["rule_id"] == "gap_is_not_zero"
    assert policy["default_period_value"] is None
    assert "0" in policy["never_render_as"]
    assert "0 %" in policy["never_render_as"]
    assert policy["rendered_as"] == UNDEFINED
    assert "плитка" in policy["how_to_distinguish"].lower()
    for state in (NO_DATA, TRUE_ZERO, MEASURED, SUPPRESSED):
        assert state in policy["meaning"]

    gap_caveat = _catalog()["caveat_library"]["delivery_gap_note"]
    assert gap_caveat["required_on_every_report"] is True
    assert UNDEFINED in gap_caveat["text"]
    assert "0" in gap_caveat["text"]
