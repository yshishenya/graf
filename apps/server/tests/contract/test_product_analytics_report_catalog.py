"""Контракт каталога отчётов фичи 273 (T055, T058, T059, T060; FR-040…FR-043).

Проверяется сам артефакт: набор отчётов покрывает вопросы владельца, у каждого
отчёта есть владелец, свежесть, обязательные оговорки и правило пустого
значения, а стоимость результата и разделение намерения и активации описаны
машиночитаемо.
"""

import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parents[4]
DASHBOARDS_ROOT = REPO_ROOT / "infra" / "analytics" / "dashboards"
CATALOG_PATH = DASHBOARDS_ROOT / "catalog.json"

MINIMUM_REPORTS = 8
# Пять вопросов владельца из US4: каналы, объявления и страницы, воронка,
# деньги, доверие к цифрам.
REQUIRED_TOPICS = {
    "channel-comparison": "сравнение каналов",
    "creative-comparison": "сравнение объявлений",
    "landing-comparison": "сравнение посадочных страниц",
    "visit-to-first-value-funnel": "воронка от визита до первой ценности",
    "delivery-health": "здоровье доставки данных",
    "measurement-gaps": "пробел в данных показан как пробел",
    "cost-per-result": "стоимость результата",
    "download-intent-vs-activation": "намерение скачать против активации",
}
FR_043_SLUGS = {"download-intent-vs-activation", "visit-to-first-value-funnel"}
SECRET_PATTERNS = (
    re.compile(r"phc_[A-Za-z0-9]"),
    re.compile(r"Bearer\s+[A-Za-z0-9._-]"),
    re.compile(r"eyJ[A-Za-z0-9._-]{10,}"),
    re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    re.compile(r"\+7[\s(-]?\d{3}"),
    re.compile(r"(?i)(api[_-]?key|access[_-]?token|password|cookie)\s*[:=]\s*[A-Za-z0-9]"),
)


def _catalog() -> dict:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def _reports() -> list[dict]:
    return _catalog()["reports"]


def _cost_metric_ids() -> set[str]:
    return {metric["id"] for metric in _catalog()["cost_join"]["metrics"]}


def test_report_set_meets_the_minimum_and_covers_every_owner_question() -> None:
    catalog = _catalog()
    reports = catalog["reports"]

    assert len(reports) >= MINIMUM_REPORTS, "спецификации 096 и 093 требуют не менее восьми отчётов"

    slugs = {report["slug"] for report in reports}
    for slug, topic in REQUIRED_TOPICS.items():
        assert slug in slugs, f"нет отчёта на тему: {topic}"

    question_ids = {question["id"] for question in catalog["owner_questions"]}
    assert len(question_ids) == 5
    covered: set[str] = set()
    for question in catalog["owner_questions"]:
        assert question["question"].strip()
        assert question["reports"], f"вопрос {question['id']} не покрыт ни одним отчётом"
        covered.update(question["reports"])

    assert covered == {report["report_id"] for report in reports}
    for report in reports:
        assert report["owner_question"] in question_ids


def test_every_report_has_an_owner_freshness_and_mandatory_caveats() -> None:
    catalog = _catalog()
    library = catalog["caveat_library"]

    for report in catalog["reports"]:
        report_id = report["report_id"]
        assert report["title"].strip(), report_id
        assert report["purpose"].strip(), report_id
        assert report["owner"]["role"].strip(), report_id
        assert report["owner"]["responsibility"].strip(), report_id
        assert report["refresh"]["cadence"].strip(), report_id
        assert report["refresh"]["stale_after_hours"] > 0, report_id
        assert report["refresh"]["freshness_field"].strip(), report_id
        assert report["data_sources"], report_id
        assert report["dimensions"], report_id
        assert report["metrics"], report_id
        assert report["caveats"], report_id
        for caveat_id in report["caveats"]:
            assert caveat_id in library, f"{report_id}: оговорка {caveat_id} не объявлена"

    for caveat_id, caveat in library.items():
        assert caveat["text"].strip(), caveat_id


def test_consent_share_caveat_is_required_on_every_report() -> None:
    catalog = _catalog()
    consent_caveat = "no_optional_consent_share"

    assert catalog["caveat_library"][consent_caveat]["required_on_every_report"] is True
    assert "согласия" in catalog["caveat_library"][consent_caveat]["text"]

    for report in catalog["reports"]:
        assert consent_caveat in report["caveats"], (
            f"{report['report_id']}: FR-042 требует долю посетителей без необязательного согласия"
        )


def test_every_report_declares_an_empty_state_that_is_not_zero() -> None:
    catalog = _catalog()
    policy = catalog["empty_value_policy"]

    assert policy["rule_id"] == "gap_is_not_zero"
    assert policy["default_period_value"] is None
    assert "0" in policy["never_render_as"]
    for state in ("no_data", "true_zero", "measured", "suppressed_small_bucket", "not_applicable"):
        assert state in policy["meaning"], state
    assert "нет данных" in policy["meaning"]["no_data"]
    assert "0" in policy["meaning"]["true_zero"]

    for report in catalog["reports"]:
        empty_state = report["empty_state"]
        for field in ("no_data", "true_zero", "how_to_tell"):
            assert empty_state[field].strip(), f"{report['report_id']}: пустое поле {field}"

    gap_caveat = catalog["caveat_library"]["delivery_gap_note"]["text"]
    assert "нет данных" in gap_caveat
    assert "0" in gap_caveat


def test_reports_separate_download_intent_from_completed_activation() -> None:
    catalog = _catalog()
    vocabulary = catalog["metric_vocabulary"]

    intent = vocabulary["download_intent_clicks"]
    downloads = vocabulary["installer_downloads"]
    activation = vocabulary["first_value"]

    assert intent["event"] == "public_installer_download_clicked"
    assert "намерение" in intent["meaning"]
    assert downloads["signal"] == "public_installer_download_aggregate"
    assert "факт" in downloads["meaning"]
    assert activation["event"] == "first_value_session_completed"
    assert "активация" in activation["meaning"]
    assert intent["event"] != downloads["signal"] != activation["event"]

    separating = {
        report["slug"]: report for report in catalog["reports"] if report.get("intent_vs_activation")
    }
    for slug in FR_043_SLUGS:
        assert slug in separating, f"{slug}: FR-043 требует разделения намерения и активации"
        separation = separating[slug]["intent_vs_activation"]
        assert len(separation["separates"]) >= 2
        assert separation["rule"].strip()


def test_cost_join_defines_cost_per_result_and_refuses_false_zero() -> None:
    catalog = _catalog()
    cost_join = catalog["cost_join"]

    assert cost_join["requirement"] == "FR-041, SC-007"
    assert cost_join["cost_source"]["fields"]
    assert cost_join["join"]["keys"]
    assert cost_join["join"]["normalization"].strip()

    metric_ids = {metric["id"] for metric in cost_join["metrics"]}
    for metric_id in (
        "cost_per_activation",
        "cost_per_installer_download",
        "cost_per_download_intent",
    ):
        assert metric_id in metric_ids, metric_id

    for metric in cost_join["metrics"]:
        assert metric["formula"].strip(), metric["id"]
        assert metric["unit"].strip(), metric["id"]
        assert metric["undefined_when"].strip(), metric["id"]
        assert metric["undefined_rendered_as"] == "нет данных", metric["id"]

    rules = cost_join["rules"]
    assert "нет данных" in rules["zero_results"]
    assert "настоящий ноль" in rules["zero_spend"]
    assert "нет данных" in rules["missing_spend"]
    assert "не считается" in rules["partial_period"]
    assert "не распределяется" in rules["unmatched_rows"]
    assert rules["no_backfill_from_totals"].strip()

    cost_report = next(report for report in catalog["reports"] if report["slug"] == "cost-per-result")
    assert cost_report["cost_join"] == "C1"
    assert "cost_per_activation" in cost_report["metrics"]

    intent_metric = next(m for m in cost_join["metrics"] if m["id"] == "cost_per_download_intent")
    assert "не заменяет стоимость результата" in intent_metric["note"]


def test_catalog_references_only_declared_metrics_and_surfaces() -> None:
    catalog = _catalog()
    known_metrics = set(catalog["metric_vocabulary"]) | _cost_metric_ids()

    for report in catalog["reports"]:
        for metric_id in report["metrics"]:
            assert metric_id in known_metrics, f"{report['report_id']}: неизвестный показатель {metric_id}"
        for source in report["data_sources"]:
            assert source["surface"].strip(), report["report_id"]
            assert source["detail"].strip(), report["report_id"]


def test_provider_minimums_are_declared_and_respected() -> None:
    catalog = _catalog()
    minimums = catalog["report_minimums"]

    assert minimums["posthog_dashboards"] == 8
    assert minimums["yandex_reports"] == 8
    assert minimums["claimed"]["posthog_dashboards"] >= minimums["posthog_dashboards"]
    assert minimums["claimed"]["yandex_reports"] >= minimums["yandex_reports"]
    assert len(minimums["source_096"]) == 2

    posthog = json.loads((DASHBOARDS_ROOT / "posthog" / "dashboards.json").read_text("utf-8"))
    yandex = json.loads((DASHBOARDS_ROOT / "yandex" / "reports.json").read_text("utf-8"))
    assert minimums["claimed"]["posthog_dashboards"] == len(posthog["dashboards"])
    assert minimums["claimed"]["yandex_reports"] == len(yandex["reports"])
    assert catalog["runtime_status"] == "runtime-status.json"
    assert (DASHBOARDS_ROOT / catalog["runtime_status"]).is_file()

    covered = {item["minimum_item"] for item in catalog["provider_minimum_coverage"]}
    assert len(covered) == len(catalog["provider_minimum_coverage"]), "пункты минимума не повторяются"
    for item in catalog["provider_minimum_coverage"]:
        assert item["covered_by"].startswith("R"), item["minimum_item"]
        assert item["provider"] in {"posthog", "yandex"}
    assert sum(1 for i in catalog["provider_minimum_coverage"] if i["provider"] == "posthog") >= 8
    assert sum(1 for i in catalog["provider_minimum_coverage"] if i["provider"] == "yandex") >= 8


def test_consistency_check_names_the_single_attribution_rule() -> None:
    catalog = _catalog()
    check = catalog["consistency_check"]

    assert check["requirement"] == "SC-008, FR-017, T061"
    assert check["single_rule"]["rule"] == catalog["attribution_rule"]["rule"]
    assert check["single_rule"]["window_days"] == catalog["attribution_rule"]["window_days"] == 90
    assert check["single_rule"]["unknown_is_not_direct"] is True
    assert len(check["procedure"]) >= 5
    assert check["on_mismatch"].strip()
    assert check["mismatch_causes"]
    assert check["expected_on_sample"].strip()
    assert check["bucket_mapping"]["direct"].strip()
    assert (DASHBOARDS_ROOT / check["sample"]).is_file()
    assert check["how_to_run"].strip()


def test_catalog_contains_no_secrets_and_no_personal_data() -> None:
    text = CATALOG_PATH.read_text(encoding="utf-8")

    for pattern in SECRET_PATTERNS:
        assert not pattern.search(text), f"в каталоге найдено запрещённое значение: {pattern.pattern}"

    constraints = _catalog()["constraints"]
    assert "не картинки" in constraints["no_screenshots"]
    assert "нет" in constraints["no_secrets"]
    assert constraints["no_live_connection"].strip()


@pytest.mark.parametrize("report_id", [report["report_id"] for report in _reports()])
def test_every_report_declares_both_provider_surfaces_or_explains_absence(report_id: str) -> None:
    catalog = _catalog()
    report = next(item for item in catalog["reports"] if item["report_id"] == report_id)

    assert report["surfaces"]["posthog"], f"{report_id}: дашборд PostHog обязателен"
    assert report["requires_operator"] is True
    if report["surfaces"]["yandex"] is None:
        assert report_id in {"R11", "R13", "R14"}, f"{report_id}: отсутствие отчёта Метрики нужно объяснить"
