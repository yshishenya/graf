"""Поверхность отчёта продуктовой аналитики: доля согласия и стоимость результата.

Здесь сходятся два требования, которые до этого жили только в определениях и
тестах.

FR-012. Доля посетителей с необязательным согласием считается продуктом, а не
вписывается оператором: знаменатель — обезличенный счёт уровня 1 из PostgreSQL,
который считает всех посетителей, включая отказавшихся; числитель — число
согласившихся визитов, которое есть только на поверхности уровня 3. Обе стороны
соединяет :func:`twobrain_rec_server.public.analytics.build_public_consent_share_report`,
и результат публикуется на поверхности отчёта.

FR-041. Расход рекламного кабинета соединяется с конверсиями по кампании кодом
продукта (:mod:`twobrain_rec_server.product_analytics.ad_cabinet_spend`), а не
пересчитывается вручную.

Обе величины берутся из названных источников: расход и числитель согласия — из
файлов, которые кладёт оператор (обмен через API в эту фичу не входит), знаменатель
и состоявшиеся скачивания — из обезличенного агрегата уровня 1. Файлы оператора
содержат только счётчики и метки: персональных данных в них нет и быть не может,
а проверка запрещённых полей это подтверждает.
"""

from __future__ import annotations

import json
import logging
import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.product_analytics.ad_cabinet_spend import (
    COST_JOIN_METRICS,
    COST_JOIN_RECONCILIATION_METRIC,
    COST_JOIN_RULES,
    AdCabinetSpendExport,
    CostJoinReport,
    build_cost_join_report,
    cost_join_metric,
    read_ad_cabinet_spend_export,
)
from twobrain_rec_server.product_analytics.anonymous_aggregate import (
    INSTALLER_DELIVERY_SURFACE,
    MINIMUM_AGGREGATE_BUCKET_SIZE,
    build_minimum_bucket_size_disclosure,
    sanitize_anonymous_aggregate_label,
    sum_reportable_aggregate_visits,
    sum_reportable_aggregate_visits_by_campaign,
)
from twobrain_rec_server.product_analytics.forbidden_fields import (
    find_forbidden_fields,
    find_security_credential_fields,
)
from twobrain_rec_server.public.analytics import (
    PUBLIC_CONSENT_SHARE_CAVEAT,
    build_public_consent_share_report,
)

logger = logging.getLogger(__name__)

REPORT_SURFACE_SCHEMA = "graf-product-analytics-report-surface-v1"
REPORT_COUNTS_VERSION = "graf-product-analytics-report-counts-v1"
REPORT_COUNTS_FILE_ENV = "TWOBRAIN_PRODUCT_ANALYTICS_REPORT_COUNTS_FILE"
REPORT_COUNTS_DIR_ENV = "TWOBRAIN_PRODUCT_ANALYTICS_REPORT_COUNTS_DIR"
DEFAULT_REPORT_COUNTS_DIR = "/var/lib/twobrain-rec/product-analytics"
DEFAULT_REPORT_COUNTS_NAME = "report-counts.json"

# Величины конверсий, которые приносит отчётная поверхность уровня 3.
REPORT_COUNT_CONVERSION_FIELDS = ("first_value", "download_intent_clicks")
# Состоявшиеся скачивания считает уровень 1, поэтому они не приходят из файла
# оператора: их читает продукт из обезличенного агрегата.
AGGREGATE_CONVERSION_FIELDS = ("installer_downloads",)
REPORT_COUNT_FIELDS = REPORT_COUNT_CONVERSION_FIELDS + AGGREGATE_CONVERSION_FIELDS

REPORT_OWNERS: dict[str, str] = {
    "R07": "growth analytics operator",
    "R11": "privacy/security reviewer",
}

REPORT_SURFACE_CAVEATS: tuple[str, ...] = (
    PUBLIC_CONSENT_SHARE_CAVEAT,
    (
        "Знаменатель доли согласия — обезличенный счёт уровня 1: корзины меньше "
        "минимального размера не раскрываются, поэтому знаменатель является нижней "
        "границей."
    ),
    "В цифры может попадать внутренний, служебный и тестовый трафик до подтверждения фильтра.",
    "Состоявшиеся скачивания читаются из обезличенного агрегата уровня 1, а активации и "
    "нажатия «Скачать» — с поверхности уровня 3.",
)


@dataclass(frozen=True, slots=True)
class ReportCounts:
    """Счётчики отчётной поверхности: согласие и конверсии по кампании.

    Файл метаданных: только числа и метки. Персональных данных в нем нет, и
    проверка запрещённых полей это подтверждает до того, как числа попадут в
    отчёт.
    """

    available: bool
    state_path: str
    file_errors: tuple[str, ...] = ()
    period_start: date | None = None
    period_end: date | None = None
    consent_visits: int | None = None
    conversions: dict[str, dict[str, int]] = field(default_factory=dict)

    @property
    def usable(self) -> bool:
        return self.available and not self.file_errors

    @property
    def has_period(self) -> bool:
        return self.period_start is not None and self.period_end is not None

    def as_dict(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "usable": self.usable,
            "state_path": self.state_path,
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
            "consent_visits": self.consent_visits,
            "conversion_campaigns": len(self.conversions),
            "file_errors": list(self.file_errors),
        }


def report_counts_state_file_path(environ: Mapping[str, str] | None = None) -> str:
    environment = os.environ if environ is None else environ
    explicit = environment.get(REPORT_COUNTS_FILE_ENV)
    if explicit:
        return explicit
    directory = environment.get(REPORT_COUNTS_DIR_ENV) or DEFAULT_REPORT_COUNTS_DIR
    return os.path.join(directory, DEFAULT_REPORT_COUNTS_NAME)


def read_report_counts(environ: Mapping[str, str] | None = None) -> ReportCounts:
    """Прочитать счётчики отчётной поверхности; ошибка не поднимает исключение."""
    path = report_counts_state_file_path(environ)
    try:
        with open(path, encoding="utf-8") as counts_file:
            text = counts_file.read()
    except (OSError, UnicodeError):
        return ReportCounts(
            available=False,
            state_path=path,
            file_errors=("report_counts_unavailable",),
        )
    return parse_report_counts(text, state_path=path)


def parse_report_counts(text: str, *, state_path: str = "") -> ReportCounts:
    """Разобрать счётчики строго: непонятное поле делает файл непригодным."""
    try:
        payload = json.loads(text)
    except (TypeError, ValueError):
        return ReportCounts(
            available=True,
            state_path=state_path,
            file_errors=("report_counts_invalid_json",),
        )
    if not isinstance(payload, Mapping):
        return ReportCounts(
            available=True,
            state_path=state_path,
            file_errors=("report_counts_must_be_object",),
        )

    findings = set(find_forbidden_fields(dict(payload)))
    findings.update(find_security_credential_fields(dict(payload)))
    if findings:
        return ReportCounts(
            available=True,
            state_path=state_path,
            file_errors=tuple(
                f"report_counts_forbidden_fields:{name}" for name in sorted(findings)
            ),
        )

    errors: list[str] = []
    if payload.get("version") != REPORT_COUNTS_VERSION:
        errors.append("report_counts_version_unsupported")

    unknown_top_level = sorted(
        set(payload)
        - {
            "version",
            "period_start",
            "period_end",
            "consent_visits",
            "conversions",
            "source_surfaces",
        }
    )
    if unknown_top_level:
        errors.append("report_counts_unknown_fields:" + ",".join(unknown_top_level))

    period_start = _parse_day(payload.get("period_start"))
    period_end = _parse_day(payload.get("period_end"))
    if (period_start is None) != (period_end is None):
        # Период назван наполовину: это испорченный файл, а не отсутствие периода.
        errors.append("report_counts_period_incomplete")
    elif period_start is not None and period_end is not None and period_end < period_start:
        errors.append("report_counts_period_reversed")
    # Отсутствие периода целиком файл не портит: доля согласия считается и без
    # него, а стоимость результата без периода не считается вовсе и говорит об
    # этом отдельной причиной.

    consent_visits = _parse_count(payload.get("consent_visits"))
    if consent_visits is None:
        errors.append("report_counts_consent_visits_missing")

    conversions: dict[str, dict[str, int]] = {}
    raw_conversions = payload.get("conversions")
    if raw_conversions is None:
        conversions = {}
    elif not isinstance(raw_conversions, Mapping):
        errors.append("report_counts_conversions_must_be_object")
    else:
        for campaign, values in raw_conversions.items():
            if not isinstance(campaign, str) or not campaign.strip():
                errors.append("report_counts_campaign_label_invalid")
                continue
            # Метка приводится к той же форме, что и метка расхода: иначе
            # «Brand Search» из файла не нашла бы «brand-search» из выгрузки, а
            # метка с контактом попала бы в отчёт. Саму метку в ошибке не
            # повторяем: она и есть то, что не должно оказаться в отчёте.
            label = sanitize_anonymous_aggregate_label(campaign)
            if label is None:
                errors.append("report_counts_campaign_label_forbidden")
                continue
            if not isinstance(values, Mapping):
                errors.append(f"report_counts_campaign_values_invalid:{label}")
                continue
            unknown_fields = sorted(set(values) - set(REPORT_COUNT_FIELDS))
            if unknown_fields:
                errors.append(
                    f"report_counts_campaign_unknown_fields:{label}:"
                    + ",".join(unknown_fields)
                )
                continue
            counts: dict[str, int] = {}
            for field_name in REPORT_COUNT_CONVERSION_FIELDS:
                if field_name not in values:
                    continue
                parsed = _parse_count(values[field_name])
                if parsed is None:
                    errors.append(f"report_counts_campaign_count_invalid:{label}:{field_name}")
                    continue
                counts[field_name] = parsed
            conversions[label] = counts

    return ReportCounts(
        available=True,
        state_path=state_path,
        file_errors=tuple(errors),
        period_start=period_start,
        period_end=period_end,
        consent_visits=consent_visits,
        conversions=conversions,
    )


async def build_product_report_surface(
    session: AsyncSession | None,
    *,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Собрать отчётную поверхность продукта: доля согласия и стоимость результата.

    Знаменатель доли и состоявшиеся скачивания читаются из обезличенного
    агрегата уровня 1, расход и счётчики согласия — из файлов оператора. Ни одно
    из чтений не поднимает исключение наружу: отчёт обязан показать «нет данных»
    и причину, а не упасть.
    """
    counts = read_report_counts(environ)
    aggregate_state, aggregate_visits, installer_downloads = await _read_level_1_aggregate(
        session,
        period_start=counts.period_start if counts.usable else None,
        period_end=counts.period_end if counts.usable else None,
    )

    consent_share = _build_consent_share(
        counts=counts,
        aggregate_state=aggregate_state,
        aggregate_visits=aggregate_visits,
    )
    cost_per_result = _build_cost_per_result(
        counts=counts,
        aggregate_state=aggregate_state,
        installer_downloads=installer_downloads,
        environ=environ,
    )

    blocked_reasons = [
        block["blocked_reason"]
        for block in (consent_share, cost_per_result)
        if block.get("blocked_reason")
    ]
    return {
        "schema": REPORT_SURFACE_SCHEMA,
        "owners": dict(REPORT_OWNERS),
        "reports": {
            "R11_consent_coverage": "consent_share",
            "R07_cost_per_result": "cost_per_result",
        },
        "consent_share": consent_share,
        "cost_per_result": cost_per_result,
        "aggregate_state": aggregate_state,
        "counts_state": counts.as_dict(),
        "minimum_bucket_size": build_minimum_bucket_size_disclosure(),
        "caveats": list(REPORT_SURFACE_CAVEATS),
        "blocked_reasons": blocked_reasons,
    }


def _build_consent_share(
    *,
    counts: ReportCounts,
    aggregate_state: str,
    aggregate_visits: int | None,
) -> dict[str, Any]:
    """Долю считает продукт: числитель и знаменатель соединяет одна функция."""
    report = build_public_consent_share_report(
        aggregate_visits=aggregate_visits,
        consent_visits=counts.consent_visits if counts.usable else None,
        minimum_bucket_size=MINIMUM_AGGREGATE_BUCKET_SIZE,
    )
    report["report_id"] = "R11"
    report["owner"] = REPORT_OWNERS["R11"]
    report["denominator_source"] = "graf_aggregate_pg:anonymous_page_aggregate_buckets"
    report["numerator_source"] = "level_3_consent_events"
    report["aggregate_state"] = aggregate_state
    report["counts_state_path"] = counts.state_path
    report["counts_file_errors"] = list(counts.file_errors)
    if not report["published"]:
        # Причину отказа называет продукт, но источник пробела виднее здесь:
        # «invalid_counts» не отличил бы отсутствие знаменателя от отсутствия
        # числителя, а оператору нужно знать, какой источник чинить.
        if aggregate_state != "measured":
            report["blocked_reason"] = "aggregate_unavailable"
        elif not counts.usable:
            report["blocked_reason"] = "counts_unavailable"
    else:
        report["blocked_reason"] = None
    return report


def _build_cost_per_result(
    *,
    counts: ReportCounts,
    aggregate_state: str,
    installer_downloads: Mapping[str, int],
    environ: Mapping[str, str] | None,
) -> dict[str, Any]:
    """Стоимость результата: расход кабинета соединяется с конверсиями кодом."""
    metric = cost_join_metric("cost_per_activation")
    block: dict[str, Any] = {
        "report_id": "R07",
        "owner": REPORT_OWNERS["R07"],
        "metric": metric.as_dict(),
        "metric_definitions": [item.as_dict() for item in COST_JOIN_METRICS],
        "reconciliation_metric": COST_JOIN_RECONCILIATION_METRIC.as_dict(),
        "rules": dict(COST_JOIN_RULES),
        "results_sources": {
            "first_value": "posthog_events",
            "download_intent_clicks": "posthog_events",
            "installer_downloads": "graf_aggregate_pg:anonymous_page_aggregate_buckets",
        },
        "cost_source": "ad_cabinet_export",
        "aggregate_state": aggregate_state,
        "blocked_reason": None,
        "report": None,
        "companion_reports": [],
    }
    if not counts.usable:
        block["blocked_reason"] = "report_counts_unavailable"
        return block
    if not counts.has_period:
        # Без периода нельзя ответить на главный вопрос отчёта: загружен ли
        # расход целиком. Молчаливое «за весь файл» выдало бы частичный период
        # за полный.
        block["blocked_reason"] = "report_period_unknown"
        return block

    period_start = counts.period_start
    period_end = counts.period_end
    assert period_start is not None and period_end is not None
    export = read_ad_cabinet_spend_export(environ)
    results_by_campaign = _merge_results(counts.conversions, installer_downloads)
    block["spend_export"] = export.as_dict()
    block["results_by_campaign"] = results_by_campaign
    block["report"] = _cost_report(
        export, results_by_campaign, period_start, period_end, "cost_per_activation"
    )
    block["companion_reports"] = [
        _cost_report(export, results_by_campaign, period_start, period_end, item.metric_id)
        for item in COST_JOIN_METRICS
        if item.metric_id != "cost_per_activation"
    ]
    return block


def _merge_results(
    conversions: Mapping[str, Mapping[str, int]],
    installer_downloads: Mapping[str, int],
) -> dict[str, dict[str, int]]:
    """Свести конверсии двух поверхностей по кампании.

    Активации и нажатия «Скачать» приносит поверхность уровня 3, состоявшиеся
    скачивания считает уровень 1. Кампания, которой нет ни в одном источнике, в
    слияние не попадает: ноль вместо отсутствия данных здесь был бы выдумкой.
    """
    merged: dict[str, dict[str, int]] = {}
    for campaign, values in conversions.items():
        merged[campaign] = dict(values)
    for campaign, visits in installer_downloads.items():
        merged.setdefault(campaign, {})["installer_downloads"] = int(visits)
    return merged


def _cost_report(
    export: AdCabinetSpendExport,
    results_by_campaign: Mapping[str, Mapping[str, int]],
    period_start: date,
    period_end: date,
    metric_id: str,
) -> dict[str, Any]:
    report: CostJoinReport = build_cost_join_report(
        export,
        results_by_campaign,
        period_start=period_start,
        period_end=period_end,
        metric_id=metric_id,
    )
    return report.as_dict()


async def _read_level_1_aggregate(
    session: AsyncSession | None,
    *,
    period_start: date | None,
    period_end: date | None,
) -> tuple[str, int | None, dict[str, int]]:
    """Прочитать знаменатель и состоявшиеся скачивания из уровня 1."""
    if session is None:
        return "unavailable", None, {}
    try:
        visits = await sum_reportable_aggregate_visits(
            session,
            bucket_date_from=period_start,
            bucket_date_to=period_end,
        )
        installer_downloads = await sum_reportable_aggregate_visits_by_campaign(
            session,
            surface=INSTALLER_DELIVERY_SURFACE,
            bucket_date_from=period_start,
            bucket_date_to=period_end,
        )
    except Exception as exc:  # noqa: BLE001 - отчёт обязан показать пробел, а не упасть
        # Ошибка чтения — это пробел измерения, и он должен быть виден в отчёте
        # как «нет данных», а не превратиться в пятисотую ошибку поверхности.
        logger.warning("report surface could not read the level 1 aggregate: %s", exc.__class__.__name__)
        return "unavailable", None, {}
    return "measured", visits, installer_downloads


def _parse_day(value: Any) -> date | None:
    if isinstance(value, date):
        return value
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return date.fromisoformat(value.strip())
    except ValueError:
        return None


def _parse_count(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value
