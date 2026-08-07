from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from twobrain_rec_server.billing.trial import activate_trial, trial_plan_at


def test_trial_is_one_time_verified_and_expires_to_free() -> None:
    now = datetime(2026, 8, 6, 9, 0, tzinfo=UTC)
    trial = activate_trial(user_id=uuid4(), now=now, policy_version="trial-v1", verified=True, eligible=True)
    assert trial_plan_at(now=now + timedelta(days=6), trial=trial) == "trial"
    assert trial_plan_at(now=now + timedelta(days=7), trial=trial) == "free"
    with pytest.raises(PermissionError):
        activate_trial(user_id=trial.user_id, now=now, policy_version="trial-v1", verified=False, eligible=True)
    with pytest.raises(ValueError):
        activate_trial(user_id=trial.user_id, now=now, policy_version="trial-v1", verified=True, eligible=False)
