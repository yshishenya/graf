"""Соединение расхода рекламного кабинета с конверсиями (FR-041, SC-007).

Расход приходит только выгрузкой кабинета: оператор ежедневно кладет файл, а
автоматический обмен через API в эту фичу не входит. Поэтому источник расхода
здесь один и названный, а не выдуманный: колонки выгрузки объявлены в
``infra/analytics/dashboards/catalog.json`` (раздел ``cost_join.cost_source``) и
в ``docs/analytics/product-analytics-reports.md`` (раздел 5).

Соединение выполняется по метке кампании, очищенной тем же очистителем, что и
метки обезличенного агрегата уровня 1 (T009). Правила из каталога выполняются
кодом, а не описанием: ноль результатов дает «нет данных», а не 0 и не
бесконечность; неполный период не дает стоимости; несопоставленный расход
показывается отдельной строкой и не распределяется по другим кампаниям.
"""

from __future__ import annotations

import csv
import io
import os
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import UTC, date, datetime
from typing import Any

from twobrain_rec_server.product_analytics.anonymous_aggregate import (
    sanitize_anonymous_aggregate_label,
)
from twobrain_rec_server.product_analytics.forbidden_fields import (
    find_forbidden_fields,
    find_security_credential_fields,
)

# Колонки выгрузки Яндекс.Директа. Обязательные отделены от необязательных:
# выгрузка без даты, кампании или расхода не является выгрузкой расхода, а
# показы и клики нужны только вспомогательным разрезам. Порядок колонок
# совпадает с объявленным в каталоге, чтобы артефакт и код нельзя было развести.
AD_CABINET_EXPORT_COLUMNS = (
    "date",
    "campaign",
    "ad_group",
    "ad",
    "spend_rub",
    "impressions",
    "clicks",
)
AD_CABINET_EXPORT_REQUIRED_COLUMNS = ("date", "campaign", "spend_rub")
AD_CABINET_EXPORT_OPTIONAL_COLUMNS = tuple(
    column for column in AD_CABINET_EXPORT_COLUMNS if column not in AD_CABINET_EXPORT_REQUIRED_COLUMNS
) + ("currency", "vat_basis")

AD_CABINET_EXPORT_FILE_ENV = "TWOBRAIN_PRODUCT_ANALYTICS_AD_CABINET_EXPORT_FILE"
AD_CABINET_EXPORT_DIR_ENV = "TWOBRAIN_PRODUCT_ANALYTICS_AD_CABINET_EXPORT_DIR"
DEFAULT_AD_CABINET_EXPORT_DIR = "/var/lib/twobrain-rec/product-analytics"
DEFAULT_AD_CABINET_EXPORT_NAME = "ad-cabinet-spend.csv"

# Правило пустого значения (T060, FR-040): пробел выглядит пробелом.
UNDEFINED_VALUE_LABEL = "нет данных"
UNMATCHED_CAMPAIGN_LABEL = "кампания не сопоставлена"
AMBIGUOUS_MATCH_LABEL = "неоднозначное сопоставление"
# Свежесть выгрузки: суточная выгрузка старше этого срока считается устаревшей.
SPEND_FRESHNESS_HOURS = 26


@dataclass(frozen=True, slots=True)
class CostJoinMetric:
    """Одна величина стоимости результата из раздела ``cost_join.metrics``."""

    metric_id: str
    title: str
    formula: str
    results_field: str | None
    responsible_metric: str | None
    undefined_when: str
    unit: str = "₽"
    note: str | None = None

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "id": self.metric_id,
            "title": self.title,
            "formula": self.formula,
            "unit": self.unit,
            "undefined_when": self.undefined_when,
            "undefined_rendered_as": UNDEFINED_VALUE_LABEL,
        }
        if self.responsible_metric is not None:
            payload["responsible_metric"] = self.responsible_metric
        if self.note is not None:
            payload["note"] = self.note
        return payload


COST_JOIN_METRICS: tuple[CostJoinMetric, ...] = (
    CostJoinMetric(
        metric_id="cost_per_activation",
        title="Стоимость одной активации, ₽",
        formula="spend_rub / first_value",
        results_field="first_value",
        responsible_metric="first_value",
        undefined_when="first_value = 0 или расход за период не загружен целиком",
    ),
    CostJoinMetric(
        metric_id="cost_per_installer_download",
        title="Стоимость состоявшегося скачивания, ₽",
        formula="spend_rub / installer_downloads",
        results_field="installer_downloads",
        responsible_metric="installer_downloads",
        undefined_when="installer_downloads = 0 или расход загружен не целиком",
    ),
    CostJoinMetric(
        metric_id="cost_per_download_intent",
        title="Стоимость намерения скачать, ₽",
        formula="spend_rub / download_intent_clicks",
        results_field="download_intent_clicks",
        responsible_metric="download_intent_clicks",
        undefined_when="download_intent_clicks = 0 или расход загружен не целиком",
        note=(
            "вспомогательная величина: намерение дешевле активации и не заменяет "
            "стоимость результата (FR-043)"
        ),
    ),
)
COST_JOIN_RECONCILIATION_METRIC = CostJoinMetric(
    metric_id="spend_reconciliation_delta",
    title="Расхождение с кабинетом, ₽",
    formula="spend_in_report - spend_in_cabinet",
    results_field=None,
    responsible_metric=None,
    undefined_when="одна из сторон не загружена",
)

COST_JOIN_RULES: dict[str, str] = {
    "zero_results": (
        "Если результатов ноль, стоимость результата не определена: показывать «нет данных», "
        "а не 0 и не бесконечность. Это правило главнее правила нулевого расхода."
    ),
    "zero_spend": (
        "Если расход подтверждённо равен нулю и результат есть, стоимость результата равна нулю — "
        "это настоящий ноль. Если результатов нет, стоимость не определена независимо от расхода."
    ),
    "missing_spend": (
        "Если расход не загружен, стоимость результата «нет данных» на всех разрезах периода."
    ),
    "stale_spend": (
        "Если выгрузка старше 26 часов, стоимость результата заблокирована: показывать «нет данных» "
        "и состояние «расход устарел», а не принимать старый расход за свежий."
    ),
    "partial_period": "Если расход загружен за часть периода, стоимость результата не считается.",
    "unmatched_rows": (
        "Расход без кампании показывается отдельной строкой и не распределяется по другим кампаниям."
    ),
    "no_backfill_from_totals": (
        "Нельзя досчитывать расход кампании из общего расхода пропорционально кликам."
    ),
    "mixed_basis": (
        "Основы с НДС и без НДС не смешиваются, валюты не смешиваются: смешанная выгрузка "
        "стоимость результата не дает."
    ),
    "ambiguous_match": (
        "Если одной метке объявления соответствует несколько кампаний, строка показывается как "
        "«неоднозначное сопоставление» и в стоимость результата не входит."
    ),
}

COST_JOIN_CAVEATS: tuple[str, ...] = (
    "Списания, возвраты и корректировки кабинета приходят с задержкой и переносятся в отчёт "
    "задним числом.",
    "Выгрузка расхода старше 26 часов блокирует стоимость результата и помечается устаревшей.",
    "Расход без сопоставленной кампании показан отдельной строкой и не распределён по другим "
    "кампаниям.",
    "Неоднозначный расход показан отдельными строками и исключён из стоимости кампаний.",
    "Стоимость намерения скачать не заменяет стоимость активации (FR-043).",
)

METRIC_IDS = tuple(metric.metric_id for metric in COST_JOIN_METRICS) + (
    COST_JOIN_RECONCILIATION_METRIC.metric_id,
)


def cost_join_metric(metric_id: str) -> CostJoinMetric:
    for metric in (*COST_JOIN_METRICS, COST_JOIN_RECONCILIATION_METRIC):
        if metric.metric_id == metric_id:
            return metric
    raise ValueError(f"unknown cost join metric: {metric_id}")


# --- Правило стоимости результата -------------------------------------------


def cost_per_result(
    spend_rub: float | None,
    results: int | None,
    *,
    spend_loaded: bool = True,
    spend_period_complete: bool = True,
) -> float | None:
    """Стоимость одного результата, или ``None`` когда она не определена.

    Порядок правил повторяет каталог и важен: сначала проверяется, что расход
    загружен и период полный, затем что результат вообще есть, и только потом
    считается отношение. Ноль результатов главнее нулевого расхода: иначе
    кампания без результата показала бы дешевый ноль и выглядела бы выгодной.
    """
    if not spend_loaded or not spend_period_complete:
        return None
    if spend_rub is None or results is None:
        return None
    if results == 0:
        return None
    if spend_rub == 0:
        return 0.0
    return spend_rub / results


def spend_reconciliation_delta(
    *,
    spend_in_report: float | None,
    spend_in_cabinet: float | None,
) -> float | None:
    """Расхождение расхода между отчётом и кабинетом, или ``None``."""
    if spend_in_report is None or spend_in_cabinet is None:
        return None
    return spend_in_report - spend_in_cabinet


def render_cost(value: float | None) -> str:
    """Как значение показывается владельцу: пробел вместо нуля."""
    if value is None:
        return UNDEFINED_VALUE_LABEL
    return f"{value:,.2f}".replace(",", " ")


# --- Выгрузка расхода кабинета ----------------------------------------------


@dataclass(frozen=True, slots=True)
class AdCabinetSpendRow:
    """Одна строка выгрузки: день, метки и расход."""

    day: date
    campaign: str | None
    ad_group: str | None
    ad: str | None
    spend_rub: float
    impressions: int | None = None
    clicks: int | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "date": self.day.isoformat(),
            "campaign": self.campaign,
            "ad_group": self.ad_group,
            "ad": self.ad,
            "spend_rub": self.spend_rub,
            "impressions": self.impressions,
            "clicks": self.clicks,
        }


@dataclass(frozen=True, slots=True)
class AdCabinetSpendExport:
    """Разобранная выгрузка расхода вместе с ее покрытием периода."""

    available: bool
    state_path: str
    rows: tuple[AdCabinetSpendRow, ...] = ()
    file_errors: tuple[str, ...] = ()
    ignored_columns: tuple[str, ...] = ()
    currency: str | None = None
    vat_basis: str | None = None
    loaded_at: datetime | None = None
    freshness_state: str = "unchecked"

    @property
    def usable(self) -> bool:
        """Выгрузку можно использовать: она есть, разобрана и не просрочена."""
        return (
            self.available
            and not self.file_errors
            and bool(self.rows)
            and not self.freshness_is_stale
        )

    @property
    def freshness_is_stale(self) -> bool:
        """Проверенная выгрузка старше допустимого срока."""
        return self.freshness_state == "stale"

    @property
    def period_start(self) -> date | None:
        return min((row.day for row in self.rows), default=None)

    @property
    def period_end(self) -> date | None:
        return max((row.day for row in self.rows), default=None)

    @property
    def days(self) -> frozenset[date]:
        return frozenset(row.day for row in self.rows)

    def covers(self, period_start: date, period_end: date) -> bool:
        """Загружен ли расход за каждый день периода (R08).

        Проверяется не только граница выгрузки, но и каждый день внутри
        периода: пропущенный день означает, что часть расхода не загружена, и
        стоимость результата за период не считается.
        """
        if period_end < period_start:
            return False
        days = self.days
        current = period_start
        while current <= period_end:
            if current not in days:
                return False
            current = date.fromordinal(current.toordinal() + 1)
        return True

    def spend_by_campaign(self, *, include_ambiguous: bool = True) -> dict[str | None, float]:
        """Расход по кампании; ``None`` — расход без кампании.

        В режиме ``include_ambiguous=False`` исключаются строки, чья метка
        объявления встречается у нескольких кампаний. Такой режим предназначен
        именно для расчёта стоимости: неоднозначный расход нельзя приписывать
        ни одной кампании.
        """
        ambiguous = set(self.ambiguous_ad_labels()) if not include_ambiguous else set()
        totals: dict[str | None, float] = defaultdict(float)
        for row in self.rows:
            if row.ad in ambiguous:
                continue
            totals[row.campaign] += row.spend_rub
        return dict(totals)

    def ambiguous_spend_by_campaign(self) -> dict[str, float]:
        """Неоднозначный расход по затронутым кампаниям.

        Сумма нужна для отдельной строки отчёта и сверки с исходной выгрузкой;
        она никогда не участвует в стоимости результата.
        """
        ambiguous = set(self.ambiguous_ad_labels())
        totals: dict[str, float] = defaultdict(float)
        for row in self.rows:
            if row.ad in ambiguous and row.campaign is not None:
                totals[row.campaign] += row.spend_rub
        return dict(totals)

    def spend_by_ad(self) -> dict[str | None, float]:
        totals: dict[str | None, float] = defaultdict(float)
        for row in self.rows:
            totals[row.ad] += row.spend_rub
        return dict(totals)

    def ambiguous_ad_labels(self) -> tuple[str, ...]:
        """Метки объявлений, которым соответствует больше одной кампании.

        Такая метка не может быть сопоставлена однозначно. Расход таких строк
        должен быть исключён из стоимости и показан отдельно как
        «неоднозначное сопоставление», а не оставлен внутри кампании.
        """
        campaigns_by_ad: dict[str, set[str]] = defaultdict(set)
        for row in self.rows:
            if row.ad is None or row.campaign is None:
                continue
            campaigns_by_ad[row.ad].add(row.campaign)
        return tuple(sorted(ad for ad, campaigns in campaigns_by_ad.items() if len(campaigns) > 1))

    def as_dict(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "usable": self.usable,
            "state_path": self.state_path,
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
            "row_count": len(self.rows),
            "currency": self.currency,
            "vat_basis": self.vat_basis,
            "loaded_at": self.loaded_at.isoformat() if self.loaded_at else None,
            "freshness_state": self.freshness_state,
            "file_errors": list(self.file_errors),
            "ignored_columns": list(self.ignored_columns),
        }


def ad_cabinet_export_state_file_path(environ: Mapping[str, str] | None = None) -> str:
    environment = os.environ if environ is None else environ
    explicit = environment.get(AD_CABINET_EXPORT_FILE_ENV)
    if explicit:
        return explicit
    directory = environment.get(AD_CABINET_EXPORT_DIR_ENV) or DEFAULT_AD_CABINET_EXPORT_DIR
    return os.path.join(directory, DEFAULT_AD_CABINET_EXPORT_NAME)


def ad_cabinet_spend_freshness_state(
    loaded_at: datetime | None,
    *,
    now: datetime | None = None,
) -> str:
    """Return ``fresh``/``stale`` for a checked export timestamp.

    ``loaded_at`` is the source file modification time, which is the only
    timestamp available for the operator-managed CSV. A missing timestamp is
    deliberately reported as ``unchecked`` rather than silently treated as
    fresh; this keeps text-only fixtures usable while the file-reading path
    remains fail-closed when it cannot stat the source file.
    """
    if loaded_at is None:
        return "unchecked"
    current = _as_utc(now or datetime.now(UTC))
    loaded = _as_utc(loaded_at)
    age_hours = (current - loaded).total_seconds() / 3600
    return "fresh" if age_hours <= SPEND_FRESHNESS_HOURS else "stale"


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def read_ad_cabinet_spend_export(
    environ: Mapping[str, str] | None = None,
    *,
    now: datetime | None = None,
) -> AdCabinetSpendExport:
    """Прочитать выгрузку расхода; отсутствие файла стоимости не выдумывает.

    Функция не поднимает исключений: отчет обязан показать «нет данных» и
    причину, а не упасть и не выдать ноль вместо пропуска.
    """
    path = ad_cabinet_export_state_file_path(environ)
    try:
        with open(path, encoding="utf-8") as export_file:
            text = export_file.read()
        loaded_at = datetime.fromtimestamp(os.stat(path).st_mtime, tz=UTC)
    except (OSError, UnicodeError):
        return AdCabinetSpendExport(
            available=False,
            state_path=path,
            file_errors=("ad_cabinet_export_unavailable",),
            freshness_state="unavailable",
        )
    export = build_ad_cabinet_spend_export(text, state_path=path)
    freshness_state = ad_cabinet_spend_freshness_state(loaded_at, now=now)
    return replace(export, loaded_at=loaded_at, freshness_state=freshness_state)


def build_ad_cabinet_spend_export(
    text: str,
    *,
    state_path: str = "",
) -> AdCabinetSpendExport:
    """Разобрать выгрузку расхода из текста CSV.

    Ошибка хотя бы в одной строке делает выгрузку непригодной целиком: частично
    прочитанный расход дал бы стоимость, которая выглядит настоящей. Направление
    отказа выбрано в пользу «нет данных».
    """
    reader = csv.DictReader(io.StringIO(text))
    header = tuple(field.strip() for field in (reader.fieldnames or ()) if field)
    missing = tuple(column for column in AD_CABINET_EXPORT_REQUIRED_COLUMNS if column not in header)
    if missing:
        return AdCabinetSpendExport(
            available=True,
            state_path=state_path,
            file_errors=("ad_cabinet_export_columns_missing:" + ",".join(missing),),
        )

    rows: list[AdCabinetSpendRow] = []
    row_errors: list[str] = []
    currencies: set[str] = set()
    vat_bases: set[str] = set()
    cells: list[str] = []
    for line_number, raw_row in enumerate(reader, start=2):
        row = {key.strip(): (value or "").strip() for key, value in raw_row.items() if key}
        cells.extend(value for value in row.values() if value)
        day = _parse_day(row.get("date"))
        if day is None:
            row_errors.append(f"row_{line_number}_date")
            continue
        spend = _parse_amount(row.get("spend_rub"))
        if spend is None:
            row_errors.append(f"row_{line_number}_spend_rub")
            continue
        rows.append(
            AdCabinetSpendRow(
                day=day,
                campaign=sanitize_anonymous_aggregate_label(row.get("campaign")),
                ad_group=sanitize_anonymous_aggregate_label(row.get("ad_group")),
                ad=sanitize_anonymous_aggregate_label(row.get("ad")),
                spend_rub=spend,
                impressions=_parse_count(row.get("impressions")),
                clicks=_parse_count(row.get("clicks")),
            )
        )
        currency = row.get("currency")
        if currency:
            currencies.add(currency.upper())
        vat_basis = row.get("vat_basis")
        if vat_basis:
            vat_bases.add(vat_basis.lower())

    file_errors = list(row_errors)
    if len(currencies) > 1:
        file_errors.append("ad_cabinet_export_mixed_currency")
    if len(vat_bases) > 1:
        file_errors.append("ad_cabinet_export_mixed_vat_basis")
    file_errors.extend(_forbidden_export_findings(cells))

    return AdCabinetSpendExport(
        available=True,
        state_path=state_path,
        rows=tuple(rows),
        file_errors=tuple(file_errors),
        ignored_columns=tuple(column for column in header if column not in AD_CABINET_EXPORT_COLUMNS),
        currency=next(iter(currencies), None),
        vat_basis=next(iter(vat_bases), None),
    )


# --- Отчёт стоимости результата по кампании ---------------------------------


@dataclass(frozen=True, slots=True)
class CostJoinRow:
    """Строка отчёта: кампания, расход, результат и стоимость результата."""

    campaign: str | None
    label: str
    spend_rub: float
    results: int | None
    cost_per_result: float | None
    rendered_cost: str
    state: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "campaign": self.campaign,
            "label": self.label,
            "spend_rub": self.spend_rub,
            "results": self.results,
            "cost_per_result": self.cost_per_result,
            "rendered_cost": self.rendered_cost,
            "state": self.state,
        }


@dataclass(frozen=True, slots=True)
class CostJoinReport:
    """Отчёт стоимости результата по кампаниям (R07, FR-041)."""

    metric_id: str
    metric_title: str
    unit: str
    results_field: str | None
    period_start: date | None
    period_end: date | None
    spend_loaded: bool
    spend_period_complete: bool
    spend_freshness_state: str
    spend_state_path: str
    spend_file_errors: tuple[str, ...]
    spend_period_start: date | None
    spend_period_end: date | None
    rows: tuple[CostJoinRow, ...]
    unmatched_rows: tuple[CostJoinRow, ...]
    ambiguous_rows: tuple[CostJoinRow, ...]
    ambiguous_labels: tuple[str, ...]
    caveats: tuple[str, ...]
    blocked_reason: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "metric_id": self.metric_id,
            "metric_title": self.metric_title,
            "unit": self.unit,
            "results_field": self.results_field,
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
            "spend_loaded": self.spend_loaded,
            "spend_period_complete": self.spend_period_complete,
            "spend_freshness_state": self.spend_freshness_state,
            "spend_state_path": self.spend_state_path,
            "spend_period_start": (
                self.spend_period_start.isoformat() if self.spend_period_start else None
            ),
            "spend_period_end": (
                self.spend_period_end.isoformat() if self.spend_period_end else None
            ),
            "spend_file_errors": list(self.spend_file_errors),
            "rows": [row.as_dict() for row in self.rows],
            "unmatched_rows": [row.as_dict() for row in self.unmatched_rows],
            "ambiguous_rows": [row.as_dict() for row in self.ambiguous_rows],
            "ambiguous_labels": list(self.ambiguous_labels),
            "undefined_rendered_as": UNDEFINED_VALUE_LABEL,
            "caveats": list(self.caveats),
            "blocked_reason": self.blocked_reason,
        }


def build_cost_join_report(
    export: AdCabinetSpendExport,
    results_by_campaign: Mapping[str, Mapping[str, int]] | None,
    *,
    period_start: date,
    period_end: date,
    metric_id: str = "cost_per_activation",
) -> CostJoinReport:
    """Соединить расход кабинета с конверсиями и посчитать стоимость результата.

    Расход берется из выгрузки, результат — из счетчиков отчётной поверхности по
    метке кампании. Сопоставление идет по кампании, потому что именно кампания
    несет бюджет; метка объявления проверяется отдельно и попадает в отчёт как
    «неоднозначное сопоставление», если ведет больше чем в одну кампанию.

    Общий расход никогда не распределяется пропорционально: кампания, которой нет
    в выгрузке, получает подтвержденный ноль только тогда, когда выгрузка
    загружена целиком, — иначе стоимость не определена.
    """
    metric = cost_join_metric(metric_id)
    if metric.results_field is None:
        raise ValueError(f"metric {metric_id} is not a cost per result metric")

    spend_loaded = export.usable and not export.freshness_is_stale
    spend_period_complete = spend_loaded and export.covers(period_start, period_end)
    counts = results_by_campaign or {}

    spend_by_campaign = export.spend_by_campaign(include_ambiguous=False)
    ambiguous_spend_by_campaign = export.ambiguous_spend_by_campaign()
    ambiguous_campaigns = set(ambiguous_spend_by_campaign)
    rows: list[CostJoinRow] = []
    unmatched: list[CostJoinRow] = []
    ambiguous_rows: list[CostJoinRow] = []

    matched_campaigns = sorted(
        {campaign for campaign in spend_by_campaign if campaign is not None}
        | {campaign for campaign in counts if campaign}
    )
    for campaign in matched_campaigns:
        spend_rub = float(spend_by_campaign.get(campaign, 0.0))
        results = _results_count(counts.get(campaign), metric.results_field)
        campaign_is_ambiguous = campaign in ambiguous_campaigns
        cost = None if campaign_is_ambiguous else cost_per_result(
            spend_rub,
            results,
            spend_loaded=spend_loaded,
            spend_period_complete=spend_period_complete,
        )
        rows.append(
            CostJoinRow(
                campaign=campaign,
                label=campaign,
                spend_rub=spend_rub,
                results=results,
                cost_per_result=cost,
                rendered_cost=render_cost(cost),
                state=(
                    "ambiguous"
                    if campaign_is_ambiguous
                    else _row_state(
                        cost=cost,
                        results=results,
                        spend_loaded=spend_loaded,
                        spend_period_complete=spend_period_complete,
                    )
                ),
            )
        )

    unmatched_spend = spend_by_campaign.get(None)
    if unmatched_spend is not None:
        unmatched.append(
            CostJoinRow(
                campaign=None,
                label=UNMATCHED_CAMPAIGN_LABEL,
                spend_rub=float(unmatched_spend),
                results=None,
                cost_per_result=None,
                rendered_cost=UNDEFINED_VALUE_LABEL,
                state="unmatched",
            )
        )

    for campaign, spend_rub in sorted(ambiguous_spend_by_campaign.items()):
        ambiguous_rows.append(
            CostJoinRow(
                campaign=campaign,
                label=AMBIGUOUS_MATCH_LABEL,
                spend_rub=float(spend_rub),
                results=None,
                cost_per_result=None,
                rendered_cost=UNDEFINED_VALUE_LABEL,
                state="ambiguous",
            )
        )

    blocked_reason = None
    if not export.available:
        blocked_reason = "spend_not_loaded"
    elif export.freshness_is_stale:
        blocked_reason = "spend_stale"
    elif not export.usable:
        blocked_reason = "spend_not_loaded"
    elif export.ambiguous_ad_labels():
        blocked_reason = "ambiguous_spend_excluded"

    return CostJoinReport(
        metric_id=metric.metric_id,
        metric_title=metric.title,
        unit=metric.unit,
        results_field=metric.results_field,
        period_start=period_start,
        period_end=period_end,
        spend_loaded=spend_loaded,
        spend_period_complete=spend_period_complete,
        spend_freshness_state=export.freshness_state,
        spend_state_path=export.state_path,
        spend_file_errors=export.file_errors,
        spend_period_start=export.period_start,
        spend_period_end=export.period_end,
        rows=tuple(rows),
        unmatched_rows=tuple(unmatched),
        ambiguous_rows=tuple(ambiguous_rows),
        ambiguous_labels=export.ambiguous_ad_labels(),
        caveats=COST_JOIN_CAVEATS,
        blocked_reason=blocked_reason,
    )


def _row_state(
    *,
    cost: float | None,
    results: int | None,
    spend_loaded: bool,
    spend_period_complete: bool,
) -> str:
    """Назвать состояние строки так, чтобы пробел не читался как ноль."""
    if not spend_loaded:
        return "spend_not_loaded"
    if not spend_period_complete:
        return "partial_period"
    if results is None:
        return "results_not_measured"
    if results == 0:
        return "no_results"
    if cost == 0.0:
        return "true_zero"
    return "measured"


def _results_count(values: Mapping[str, Any] | None, field: str) -> int:
    if not values:
        return 0
    value = values.get(field, 0)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return 0
    return value


def _parse_day(value: Any) -> date | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return date.fromisoformat(value.strip())
    except ValueError:
        return None


def _parse_amount(value: Any) -> float | None:
    if not isinstance(value, str) or not value.strip():
        return None
    normalized = value.strip().replace(" ", "").replace("\u00a0", "").replace(",", ".")
    try:
        amount = float(normalized)
    except ValueError:
        return None
    if amount < 0:
        return None
    return amount


def _parse_count(value: Any) -> int | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        count = int(float(value.strip().replace(" ", "")))
    except ValueError:
        return None
    return count if count >= 0 else None


def _forbidden_export_findings(cells: Sequence[str]) -> tuple[str, ...]:
    """Выгрузка кабинета не должна нести контакты, токены и пути.

    Проверка нужна не для красоты: выгрузку кладет оператор, и отчет не должен
    становиться способом протащить в аналитику персональные данные. Значения
    проверяются по одному, а не целым текстом: иначе проверка судила бы о целом
    файле как об одном значении.
    """
    if not cells:
        return ()
    findings = set(find_forbidden_fields(list(cells)))
    findings.update(find_security_credential_fields(list(cells)))
    return tuple(f"ad_cabinet_export_forbidden_fields:{name}" for name in sorted(findings))
