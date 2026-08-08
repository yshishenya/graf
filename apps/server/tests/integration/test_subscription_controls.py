from datetime import UTC, datetime, timedelta

import pytest

from twobrain_rec_server.billing.subscription import (
    SubscriptionControl,
    cancel_auto_renewal,
    project_plan,
    resume_auto_renewal,
)


def test_cancel_and_resume_require_the_current_authority_version() -> None:
    paid_through = datetime(2026, 9, 1, tzinfo=UTC)
    control = SubscriptionControl(paid_through, True, 4)
    canceled = cancel_auto_renewal(control, expected_version=4)
    assert canceled.recurring_allowed is False
    assert canceled.authority_version == 5
    with pytest.raises(ValueError, match="changed"):
        resume_auto_renewal(canceled, expected_version=4, now=datetime(2026, 8, 7, tzinfo=UTC))
    resumed = resume_auto_renewal(canceled, expected_version=5, now=datetime(2026, 8, 7, tzinfo=UTC))
    assert resumed.recurring_allowed is True
    assert resumed.authority_version == 6


def test_resume_after_cutoff_is_refused_and_plan_has_no_grace() -> None:
    cutoff = datetime(2026, 8, 7, tzinfo=UTC)
    with pytest.raises(ValueError, match="no longer active"):
        resume_auto_renewal(
            SubscriptionControl(cutoff, False, 1),
            expected_version=1,
            now=cutoff + timedelta(seconds=1),
        )
    assert project_plan(now=cutoff, paid_through=cutoff, recurring_allowed=False) == "free"
