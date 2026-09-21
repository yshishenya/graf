"""Контракт определений дашбордов PostHog и отчётов Метрики (T055, T056, T058).

Проверяется, что определения — это файлы, а не картинки; что каждый дашборд
несёт обязательные плитки свежести, полноты и оговорок; что число дашбордов и
отчётов не меньше восьми; что применение требует оператора и что в файлах нет
секретов и персональных данных.
"""

import json
import re
from pathlib import Path

from twobrain_rec_server.product_analytics.operator_evidence import validate_runtime_status

REPO_ROOT = Path(__file__).parents[4]
DASHBOARDS_ROOT = REPO_ROOT / "infra" / "analytics" / "dashboards"
CATALOG_PATH = DASHBOARDS_ROOT / "catalog.json"
POSTHOG_PATH = DASHBOARDS_ROOT / "posthog" / "dashboards.json"
YANDEX_PATH = DASHBOARDS_ROOT / "yandex" / "reports.json"
RUNTIME_STATUS_PATH = DASHBOARDS_ROOT / "runtime-status.json"

MINIMUM_DASHBOARDS = 8
MINIMUM_YANDEX_REPORTS = 8
ALLOWED_INSIGHT_KINDS = {"TRENDS", "FUNNELS", "PATHS", "RETENTION", "STICKINESS", "LIFECYCLE"}
ALLOWED_TILE_KINDS = {"insight", "text"}
FORBIDDEN_MARKERS = (
    "screenshot",
    "iVBORw0KGgo",
    "data:image",
    "phc_",
    "Bearer ",
    "eyJhbGciOi",
    "ym:s:counterUserIDHash",
)
LIVE_COUNTER_ID = re.compile(r"\b\d{7,}\b")


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _catalog() -> dict:
    return _load(CATALOG_PATH)


def _posthog() -> dict:
    return _load(POSTHOG_PATH)


def _yandex() -> dict:
    return _load(YANDEX_PATH)


def _runtime_status() -> dict:
    return _load(RUNTIME_STATUS_PATH)


def _catalog_report_ids() -> set[str]:
    return {report["report_id"] for report in _catalog()["reports"]}


def test_posthog_definitions_cover_every_catalog_report() -> None:
    dashboards = _posthog()["dashboards"]

    assert len(dashboards) >= MINIMUM_DASHBOARDS
    assert {dashboard["report_id"] for dashboard in dashboards} == _catalog_report_ids()
    assert _posthog()["data_availability"]["status"] == "not_fillable_today"
    assert _posthog()["data_availability"]["unblocks_when"]


def test_runtime_status_is_explicit_about_applied_and_operator_only_reports() -> None:
    status = _runtime_status()
    catalog_ids = _catalog_report_ids()
    server_ids = set(status["server_surface"]["implemented_reports"])
    definition_only_ids = set(status["definition_only_reports"]["report_ids"])

    assert status["status"] == "partially_applied"
    assert server_ids == {"R07", "R11"}
    assert server_ids | definition_only_ids == catalog_ids
    assert server_ids.isdisjoint(definition_only_ids)
    assert status["server_surface"]["status"] == "implemented"
    assert status["server_surface"]["unavailable_inputs_are"] == "нет данных с blocked_reason, а не 0"
    assert status["definition_only_reports"]["posthog"]["status"] == "definition_prepared_operator_apply_required"
    assert status["definition_only_reports"]["yandex"]["status"] == "definition_prepared_operator_apply_required"
    assert status["operator_required"] is True
    assert status["no_live_provider_connection"] is True
    validate_runtime_status(status)

    requirements = status["requirements"]
    assert requirements["FR-040"]["status"] == "definition_prepared_operator_apply_required"
    assert requirements["FR-041"]["status"] == "partially_implemented"
    assert requirements["FR-042"]["status"] == "partially_implemented"
    assert requirements["FR-043"]["status"] == "definition_prepared_operator_apply_required"
    for requirement in requirements.values():
        assert set(requirement["server_reports"]).issubset(server_ids)
        assert requirement["operator_action"].strip()


def test_every_posthog_dashboard_has_freshness_completeness_and_caveats() -> None:
    provider = _posthog()
    required_roles = set(provider["required_tile_roles"])

    for dashboard in provider["dashboards"]:
        report_id = dashboard["report_id"]
        assert dashboard["name"].strip(), report_id
        assert dashboard["description"].strip(), report_id
        assert dashboard["owner"].strip(), report_id
        assert dashboard["refresh_hours"] > 0, report_id
        assert "273" in dashboard["tags"], report_id

        roles = [tile["role"] for tile in dashboard["tiles"]]
        for role in required_roles:
            assert role in roles, f"{report_id}: нет плитки роли {role}"

        for tile in dashboard["tiles"]:
            assert tile["tile_kind"] in ALLOWED_TILE_KINDS, tile["name"]
            assert tile["name"].strip(), report_id
            if tile["tile_kind"] == "insight":
                assert tile["insight"] in ALLOWED_INSIGHT_KINDS, tile["name"]
                assert tile["query"]["source"]["series"], tile["name"]
            else:
                assert tile["body"].strip(), tile["name"]

        freshness = next(tile for tile in dashboard["tiles"] if tile["role"] == "freshness")
        assert freshness["stale_after_hours"] > 0, report_id

        completeness = next(tile for tile in dashboard["tiles"] if tile["role"] == "completeness")
        rule = f"{completeness.get('rule', '')} {completeness.get('body', '')}"
        assert "нет данных" in rule, f"{report_id}: правило пустого значения не названо"


def test_caveat_tiles_carry_the_mandatory_caveats_in_words() -> None:
    provider = _posthog()
    requirements = provider["caveat_tile_requirements"]
    universal = requirements["universal_fragments"]
    by_caveat_id = requirements["fragments_by_caveat_id"]
    catalog = {report["report_id"]: report for report in _catalog()["reports"]}

    for dashboard in provider["dashboards"]:
        report_id = dashboard["report_id"]
        caveats = next(tile for tile in dashboard["tiles"] if tile["role"] == "caveats")
        assert caveats["tile_kind"] == "text"
        body = caveats["body"].lower()

        required = list(universal)
        for caveat_id in catalog[report_id]["caveats"]:
            fragment = by_caveat_id.get(caveat_id)
            if fragment:
                required.append(fragment)

        for fragment in required:
            assert fragment.lower() in body, f"{report_id}: нет оговорки «{fragment}»"


def test_posthog_definitions_are_files_not_pictures_and_need_an_operator() -> None:
    text = POSTHOG_PATH.read_text(encoding="utf-8")
    provider = _posthog()

    for marker in FORBIDDEN_MARKERS:
        assert marker not in text, f"в определениях найдено запрещённое значение: {marker}"
    assert not LIVE_COUNTER_ID.search(text)

    apply_block = provider["apply"]
    assert apply_block["requires_operator"] is True
    assert apply_block["api_reference"]["create_dashboard"].startswith("POST ")
    assert apply_block["api_reference"]["create_insight"].startswith("POST ")
    assert apply_block["steps"]
    assert apply_block["forbidden_in_this_file"]


def test_yandex_definitions_meet_the_minimum_and_cover_the_same_cuts() -> None:
    provider = _yandex()
    reports = provider["reports"]

    assert len(reports) >= MINIMUM_YANDEX_REPORTS

    catalog_reports = {report["report_id"]: report for report in _catalog()["reports"]}
    yandex_ids = {report["yandex_id"] for report in reports}
    assert len(yandex_ids) == len(reports), "имена отчётов Метрики не повторяются"

    for report in reports:
        report_id = report["report_id"]
        assert report["name"].strip()
        assert report["owner"].strip(), report_id
        assert report["ui_equivalent"].strip(), report_id
        assert report["caveats"], report_id
        assert report["freshness"]["stale_after_hours"] > 0, report_id
        assert report["empty_state"]["no_data"].strip(), report_id
        assert report["empty_state"]["true_zero"].strip(), report_id
        assert report["requires_operator"] is True

        params = report["reporting_api"]["params"]
        assert params["ids"] == "<counter_id>", report_id
        assert params["metrics"], report_id
        assert params["dimensions"], report_id
        assert params["accuracy"] == "full", report_id
        assert report["reporting_api"]["path"] == "/stat/v1/data"

        assert catalog_reports[report_id]["surfaces"]["yandex"] == report["name"].split(" —")[0]


def test_yandex_definitions_explain_absent_cuts_and_avoid_secrets() -> None:
    provider = _yandex()
    text = YANDEX_PATH.read_text(encoding="utf-8")

    for marker in FORBIDDEN_MARKERS:
        assert marker not in text, f"в определениях найдено запрещённое значение: {marker}"
    assert not LIVE_COUNTER_ID.search(text)

    absent = {item["report_id"] for item in provider["not_expressed_in_metrica"]}
    catalog = _catalog()
    declared_absent = {
        report["report_id"] for report in catalog["reports"] if report["surfaces"]["yandex"] is None
    }
    assert absent == declared_absent
    for item in provider["not_expressed_in_metrica"]:
        assert len(item["reason"]) > 40, item["report_id"]

    assert provider["apply"]["requires_operator"] is True
    assert provider["goal_id_policy"].strip()
    assert provider["attribution"]["rule"] == catalog["attribution_rule"]["rule"]
    assert provider["attribution"]["window_days"] == catalog["attribution_rule"]["window_days"]
    assert provider["consistency_check"]["requirement"] == "SC-008, T061"


def test_offline_conversions_stay_limited_to_two_approved_milestones() -> None:
    provider = _yandex()

    assert provider["offline_conversion_names"] == [
        "desktop_account_connected",
        "first_value_session_completed",
    ]
    for report in provider["reports"]:
        for name in report.get("offline_conversions", []):
            assert name in provider["offline_conversion_names"], report["report_id"]
