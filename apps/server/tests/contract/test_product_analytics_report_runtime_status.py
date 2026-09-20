"""Проверка фактического состояния отчётной поверхности (T092).

Статический статус не должен расходиться с серверным кодом. Этот контракт не
подключается к продуктивному PostHog или Метрике: он вызывает реальный
``build_product_report_surface`` в безопасном режиме без базы и проверяет, что
недоступный источник обозначен пробелом, а не поддельным нулём.
"""

import asyncio
import json
from pathlib import Path

import pytest

from twobrain_rec_server.api.product_analytics import router
from twobrain_rec_server.product_analytics.operator_evidence import (
    OPERATOR_EVIDENCE_SCHEMA,
    OPERATOR_RECEIPT_SCHEMA,
    OperatorEvidenceValidationError,
    validate_operator_evidence,
    validate_runtime_status,
)
from twobrain_rec_server.product_analytics.report_surface import (
    REPORT_OWNERS,
    REPORT_SURFACE_SCHEMA,
    build_product_report_surface,
)

REPO_ROOT = Path(__file__).parents[4]
DASHBOARDS_ROOT = REPO_ROOT / "infra" / "analytics" / "dashboards"
CATALOG_PATH = DASHBOARDS_ROOT / "catalog.json"
STATUS_PATH = DASHBOARDS_ROOT / "runtime-status.json"
EVIDENCE_SCHEMA_PATH = DASHBOARDS_ROOT / "operator-evidence.schema.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_runtime_status_references_operator_evidence_schema() -> None:
    catalog = _load(CATALOG_PATH)
    assert catalog["operator_evidence_schema"] == "operator-evidence.schema.json"
    assert (DASHBOARDS_ROOT / catalog["operator_evidence_schema"]).is_file()


def test_runtime_status_names_the_real_server_endpoint_and_implementation() -> None:
    status = _load(STATUS_PATH)
    checked_surface = status["checked_surface"]

    assert checked_surface["endpoint"] == "GET /api/v1/product-analytics/reports"
    assert checked_surface["response_schema"] == REPORT_SURFACE_SCHEMA
    assert checked_surface["implementation"].endswith("product_analytics/report_surface.py")
    assert {route.path for route in router.routes if "GET" in (route.methods or set())} >= {
        "/api/v1/product-analytics/reports"
    }
    assert status["server_surface"]["implemented_reports"] == list(REPORT_OWNERS)
    assert status["server_surface"]["owners"] == REPORT_OWNERS


def test_runtime_status_covers_every_catalog_report_once() -> None:
    catalog = _load(CATALOG_PATH)
    status = _load(STATUS_PATH)
    catalog_ids = {report["report_id"] for report in catalog["reports"]}
    implemented = set(status["server_surface"]["implemented_reports"])
    definition_only = set(status["definition_only_reports"]["report_ids"])

    assert implemented == {"R07", "R11"}
    assert implemented | definition_only == catalog_ids
    assert implemented.isdisjoint(definition_only)
    assert status["status"] == "partially_applied"


def test_real_server_surface_reports_a_gap_without_faking_zero() -> None:
    status = _load(STATUS_PATH)
    surface = asyncio.run(build_product_report_surface(None, environ={}))

    assert surface["schema"] == REPORT_SURFACE_SCHEMA
    assert surface["owners"] == REPORT_OWNERS
    assert surface["reports"] == {
        "R11_consent_coverage": "consent_share",
        "R07_cost_per_result": "cost_per_result",
    }
    assert surface["aggregate_state"] == "unavailable"
    assert surface["consent_share"]["published"] is False
    assert surface["consent_share"]["consent_share"] is None
    assert surface["consent_share"]["consent_share_label"] is None
    assert surface["consent_share"]["blocked_reason"] == "aggregate_unavailable"
    assert surface["cost_per_result"]["blocked_reason"] == "report_counts_unavailable"
    assert "aggregate_unavailable" in surface["blocked_reasons"]
    assert "report_counts_unavailable" in surface["blocked_reasons"]
    assert status["server_surface"]["unavailable_inputs_are"] == "нет данных с blocked_reason, а не 0"
    assert surface["consent_share"]["consent_share_label"] != "0 %"


def test_runtime_status_does_not_claim_live_provider_application() -> None:
    status = _load(STATUS_PATH)
    catalog = _load(CATALOG_PATH)

    assert status["operator_required"] is True
    assert status["no_live_provider_connection"] is True
    assert catalog["constraints"]["no_live_connection"]
    assert status["definition_only_reports"]["posthog"]["status"] == (
        "definition_prepared_operator_apply_required"
    )
    assert status["definition_only_reports"]["yandex"]["status"] == (
        "definition_prepared_operator_apply_required"
    )


def test_runtime_status_validates_metadata_only_operator_evidence() -> None:
    status = _load(STATUS_PATH)
    schema = _load(EVIDENCE_SCHEMA_PATH)

    assert schema["$id"] == "urn:graf:analytics:operator-evidence:v1"
    assert schema["additionalProperties"] is False
    assert schema["properties"]["mode"]["const"] == "metadata_only"
    validate_runtime_status(status)
    assert status["operator_evidence"]["mode"] == "metadata_only"
    assert {entry["kind"] for entry in status["operator_evidence"]["receipts"]} == {
        "dashboard",
        "rollback",
        "alert",
    }
    assert status["operator_evidence"]["receipts"][1]["status"] == "metadata_only_not_executed"


def test_applied_runtime_status_requires_receipt_fields() -> None:
    status = _load(STATUS_PATH)
    status["status"] = "applied"

    with pytest.raises(OperatorEvidenceValidationError, match="requires applied receipts"):
        validate_runtime_status(status)


def test_applied_evidence_rejects_missing_receipt() -> None:
    evidence = {
        "schema": OPERATOR_EVIDENCE_SCHEMA,
        "mode": "metadata_only",
        "receipts": [
            {"kind": "dashboard", "status": "applied", "receipt": None},
            {"kind": "rollback", "status": "metadata_only_not_executed", "receipt": None},
            {"kind": "alert", "status": "ready_not_executed", "receipt": None},
        ],
    }

    with pytest.raises(OperatorEvidenceValidationError, match="required when status=applied"):
        validate_operator_evidence(evidence)


def test_complete_metadata_only_receipt_is_accepted() -> None:
    evidence = {
        "schema": OPERATOR_EVIDENCE_SCHEMA,
        "mode": "metadata_only",
        "receipts": [
            {
                "kind": "dashboard",
                "status": "applied",
                "receipt": {
                    "schema": OPERATOR_RECEIPT_SCHEMA,
                    "kind": "dashboard",
                    "status": "applied",
                    "recorded_at": "2026-09-18T12:00:00Z",
                    "operator_role": "analytics_operator",
                    "scope": "dashboard_definitions",
                    "result": "pass",
                    "checks": {
                        "definitions_applied": True,
                        "freshness_verified": True,
                        "empty_state_verified": True,
                    },
                },
            },
            {
                "kind": "rollback",
                "status": "ready_not_executed",
                "receipt": None,
            },
            {
                "kind": "alert",
                "status": "ready_not_executed",
                "receipt": None,
            },
        ],
    }

    validate_operator_evidence(evidence)
