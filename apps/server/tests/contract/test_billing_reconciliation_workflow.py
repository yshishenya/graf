from uuid import UUID

import pytest

from twobrain_rec_server.workflows.billing_reconciliation_workflow import (
    billing_reconciliation_workflow_id,
    validate_billing_reconciliation_payload,
)


def test_reconciliation_workflow_payload_is_bounded_and_versioned() -> None:
    run_id = UUID("11111111-1111-4111-8111-111111111111")
    assert billing_reconciliation_workflow_id(run_id).endswith("/v1")
    assert validate_billing_reconciliation_payload({"run_id": str(run_id)}) == {
        "run_id": str(run_id)
    }
    with pytest.raises(ValueError):
        validate_billing_reconciliation_payload({"run_id": str(run_id), "workspace_id": str(run_id)})
