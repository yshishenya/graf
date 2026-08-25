from pathlib import Path

from twobrain_rec_server.billing.monitoring import BillingMetricSnapshot
from twobrain_rec_server.billing.operations import BillingEmergencyStop, require_billing_enabled
from twobrain_rec_server.observability.redaction import redact_mapping


def test_emergency_stop_blocks_provider_mutations() -> None:
    try:
        require_billing_enabled(checkout_enabled=True, emergency_stop=True)
    except BillingEmergencyStop:
        pass
    else:
        raise AssertionError("emergency stop must block checkout and renewal mutations")


def test_money_mutations_keep_provider_boundary_and_no_launch_gate_dependency() -> None:
    root = Path(__file__).parents[2] / "src/twobrain_rec_server"
    checkout = (root / "cabinet/web_routes/billing.py").read_text(encoding="utf-8")
    renewal = (root / "billing/renewal_charge.py").read_text(encoding="utf-8")
    for source in (checkout, renewal):
        assert "launch_gate" not in source
        assert "provider.create_payment(" in source


def test_monitoring_and_redaction_are_safe_for_evidence() -> None:
    snapshot = BillingMetricSnapshot(payment_success=1, reconciliation_gaps=2, notification_failures=1)
    safe = snapshot.as_safe_dict()
    assert set(safe) == set(BillingMetricSnapshot.__dataclass_fields__)
    assert all(isinstance(value, int) for value in safe.values())
    redacted = redact_mapping({"provider_payment_id": "pay-secret", "invoice": "INV-1"})
    assert redacted["provider_payment_id"] == "[REDACTED]"
    assert redacted["invoice"] == "INV-1"


def test_yookassa_webhook_edge_remains_dedicated_and_fail_closed() -> None:
    root = Path(__file__).parents[4]
    nginx = (root / "infra/nginx/rec.2brain.pro.conf").read_text(encoding="utf-8")
    installer = (root / "infra/scripts/install-billing-webhook-edge.sh").read_text(encoding="utf-8")
    assert "listen 8443 ssl" in nginx
    assert "client_max_body_size 256k" in nginx
    assert "allow 2a02:5180::/32" in nginx
    assert "deny all" in nginx
    assert "graf-billing-webhook-secret.conf" in nginx
    assert "(test|production)" in nginx
    assert 'proxy_set_header X-Billing-Webhook-Secret ""' in nginx
    assert all(term in installer for term in ("nginx -t", "rollback", "untrusted_edge_status"))


def test_billing_tables_keep_tenant_rls_inventory() -> None:
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


def test_runbook_keeps_review_accessibility_and_stop_procedure_explicit() -> None:
    runbook = (Path(__file__).parents[4] / "docs/runbooks/billing-launch.md").read_text(encoding="utf-8").lower()
    for owner in ("product", "finance/accounting", "legal", "security/qa"):
        assert owner in runbook
    assert "accessibility" in runbook
    assert "emergency stop" in runbook
    spec = (Path(__file__).parents[4] / "specs/140-user-account-billing/spec.md").read_text(encoding="utf-8")
    assert "four-eyes" in spec
    assert "approver and executor" in spec
