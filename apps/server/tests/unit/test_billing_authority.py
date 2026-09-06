from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select

from twobrain_rec_server.billing.authority import (
    BillingActor,
    BillingAuthorizationError,
    lock_billing_row,
    require_authority_version,
    require_billing_owner,
    safe_audit_metadata,
)
from twobrain_rec_server.billing.operations import (
    BillingEmergencyStop,
    OperationOutcome,
    blocks_new_checkout,
    classify_provider_outcome,
    provider_key_is_expired,
    require_billing_enabled,
)
from twobrain_rec_server.db.models import BillingOperation


def test_billing_authority_is_owner_only_for_sensitive_changes() -> None:
    owner = BillingActor(uuid4(), uuid4(), "owner")
    require_billing_owner(owner)
    assert owner.may_manage_billing
    assert not BillingActor(owner.user_id, owner.workspace_id, "admin").may_manage_billing
    with pytest.raises(BillingAuthorizationError):
        require_billing_owner(BillingActor(owner.user_id, owner.workspace_id, "member"))


def test_authority_version_and_audit_redaction_fail_closed() -> None:
    with pytest.raises(BillingAuthorizationError):
        require_authority_version(expected=2, actual=1)
    assert "FOR UPDATE" in str(lock_billing_row(select(BillingOperation)).compile()).upper()
    assert safe_audit_metadata(
        {
            "provider_token": "secret",
            "support_email": "owner@example.test",
            "provider_object_id": "pay-123",
            "state": "paid",
        }
    ) == {"state": "paid"}


def test_operation_outcomes_and_emergency_stop() -> None:
    assert (
        classify_provider_outcome(status_code=200, provider_status="succeeded")
        is OperationOutcome.SUCCESS
    )
    assert (
        classify_provider_outcome(status_code=504, provider_status=None) is OperationOutcome.UNKNOWN
    )
    now = datetime.now(UTC)
    assert provider_key_is_expired(expires_at=now - timedelta(seconds=1), now=now)
    assert blocks_new_checkout("scheduled")
    assert blocks_new_checkout("provider_pending")
    assert blocks_new_checkout("unknown")
    assert blocks_new_checkout("pending_reconciliation")
    assert blocks_new_checkout("manual_resolution")
    assert blocks_new_checkout("reconciliation_gap")
    assert blocks_new_checkout("provider_key_expired")
    assert not blocks_new_checkout("canceled")
    assert not blocks_new_checkout("succeeded")
    with pytest.raises(BillingEmergencyStop):
        require_billing_enabled(checkout_enabled=True, emergency_stop=True)
