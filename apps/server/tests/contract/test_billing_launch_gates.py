from pathlib import Path

from twobrain_rec_server.billing.monitoring import BillingMetricSnapshot
from twobrain_rec_server.billing.operations import BillingEmergencyStop, require_billing_enabled
from twobrain_rec_server.observability.redaction import redact_mapping
from twobrain_rec_server.readiness.checks import evaluate_billing_readiness


def test_launch_readiness_fails_closed_for_disabled_checkout_stop_and_missing_evidence() -> None:
    result = evaluate_billing_readiness(
        checkout_enabled=False,
        emergency_stop=True,
        required_evidence={"test_shop": False, "rls": True},
    )
    assert result.provider_mutations_allowed is False
    assert result.blocked_reasons == ("checkout_disabled", "emergency_stop", "evidence_missing:test_shop")


def test_emergency_stop_blocks_provider_mutations() -> None:
    try:
        require_billing_enabled(checkout_enabled=True, emergency_stop=True)
    except BillingEmergencyStop:
        pass
    else:
        raise AssertionError("emergency stop must block checkout and renewal mutations")


def test_monitoring_and_redaction_are_safe_for_evidence() -> None:
    snapshot = BillingMetricSnapshot(
        payment_success=1,
        reconciliation_gaps=2,
        notification_failures=1,
    )
    safe = snapshot.as_safe_dict()
    assert set(safe) == set(BillingMetricSnapshot.__dataclass_fields__)
    assert all(isinstance(value, int) for value in safe.values())
    redacted = redact_mapping({"provider_payment_id": "pay-secret", "invoice": "INV-1"})
    assert redacted["provider_payment_id"] == "[REDACTED]"
    assert redacted["invoice"] == "INV-1"


def test_billing_tables_have_tenant_rls_inventory() -> None:
    migration = Path(__file__).parents[2] / "src/twobrain_rec_server/db/migrations/versions/0044_user_account_billing.py"
    source = migration.read_text(encoding="utf-8")
    for table in (
        "billing_operations",
        "billing_notification_deliveries",
        "storage_reservations",
        "observed_provider_refunds",
    ):
        assert table in source
    assert "BILLING_TABLES" in source
    assert "_tenant_isolation" in source


def test_launch_runbook_keeps_signoff_accessibility_and_stop_procedure_explicit() -> None:
    runbook = Path(__file__).parents[4] / "docs/runbooks/billing-launch.md"
    text = runbook.read_text(encoding="utf-8").lower()
    for owner in ("product", "finance/accounting", "legal", "security/qa"):
        assert owner in text
    assert "accessibility" in text
    assert "emergency stop" in text
    contract = (
        Path(__file__).parents[4]
        / "specs/140-user-account-billing/contracts/operations-reconciliation.md"
    ).read_text(encoding="utf-8")
    spec = (
        Path(__file__).parents[4] / "specs/140-user-account-billing/spec.md"
    ).read_text(encoding="utf-8")
    assert "four-eyes" in spec
    assert "approver and executor" in spec
    assert "Any failure leaves checkout disabled" in contract
    assert all(term in contract for term in ("owner", "deadline", "severity"))
    ia_contract = (
        Path(__file__).parents[4]
        / "specs/140-user-account-billing/contracts/account-ia-ux-ui-cx.md"
    ).read_text(encoding="utf-8")
    assert "WCAG 2.2 AA" in ia_contract
