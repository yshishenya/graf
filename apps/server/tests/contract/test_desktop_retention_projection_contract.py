from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from twobrain_rec_server.config import Settings
from twobrain_rec_server.deletion.retention import retention_projection
from twobrain_rec_server.domain.statuses import RetentionPolicyState


def _settings(**overrides) -> Settings:
    values = {
        "retention_meeting_delete_after_days": 365,
        "retention_backup_expiry_days": 30,
        "retention_local_buffer_expiry_days": 7,
    }
    values.update(overrides)
    return Settings(**values)


def _meeting(**overrides) -> SimpleNamespace:
    values = {
        "retention_delete_after": None,
        "retention_policy_state": "not_configured",
        "started_at": datetime(2026, 1, 1, tzinfo=UTC),
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_default_retention_uses_started_at_plus_configured_days() -> None:
    deadline, state = retention_projection(_meeting(), _settings(), now=datetime(2026, 6, 1, tzinfo=UTC))

    assert deadline == datetime(2027, 1, 1, tzinfo=UTC)
    assert state == RetentionPolicyState.ACTIVE


def test_explicit_delete_after_wins_over_configured_window() -> None:
    explicit = datetime(2026, 8, 1, tzinfo=UTC)
    deadline, state = retention_projection(
        _meeting(retention_delete_after=explicit),
        _settings(),
        now=datetime(2026, 6, 1, tzinfo=UTC),
    )

    assert deadline == explicit
    assert state == RetentionPolicyState.ACTIVE


def test_missing_started_at_is_not_configured_not_forever() -> None:
    deadline, state = retention_projection(
        _meeting(started_at=None),
        _settings(),
        now=datetime(2026, 6, 1, tzinfo=UTC),
    )

    assert deadline is None
    assert state == RetentionPolicyState.NOT_CONFIGURED


def test_missing_configured_days_is_unsafe_without_explicit_deadline() -> None:
    deadline, state = retention_projection(
        _meeting(),
        _settings(retention_meeting_delete_after_days=None),
        now=datetime(2026, 6, 1, tzinfo=UTC),
    )

    assert deadline is None
    assert state == RetentionPolicyState.UNSAFE


def test_missing_backup_or_local_buffer_policy_is_unsafe() -> None:
    for missing in (
        {"retention_backup_expiry_days": None},
        {"retention_local_buffer_expiry_days": None},
    ):
        deadline, state = retention_projection(
            _meeting(),
            _settings(**missing),
            now=datetime(2026, 6, 1, tzinfo=UTC),
        )
        assert deadline is None
        assert state == RetentionPolicyState.UNSAFE


def test_unsafe_policy_exposes_only_an_explicit_deadline() -> None:
    explicit = datetime(2027, 1, 1, tzinfo=UTC)
    deadline, state = retention_projection(
        _meeting(retention_delete_after=explicit),
        _settings(retention_backup_expiry_days=None),
        now=datetime(2026, 6, 1, tzinfo=UTC),
    )

    assert deadline == explicit
    assert state == RetentionPolicyState.UNSAFE


def test_past_deadline_is_expired() -> None:
    deadline, state = retention_projection(
        _meeting(),
        _settings(),
        now=datetime(2027, 1, 2, tzinfo=UTC),
    )

    assert deadline == datetime(2027, 1, 1, tzinfo=UTC)
    assert state == RetentionPolicyState.EXPIRED


def test_stored_unsafe_and_blocked_states_are_preserved() -> None:
    for stored in ("unsafe", "blocked"):
        deadline, state = retention_projection(
            _meeting(retention_policy_state=stored),
            _settings(),
            now=datetime(2026, 6, 1, tzinfo=UTC),
        )
        assert deadline == datetime(2027, 1, 1, tzinfo=UTC)
        assert state == RetentionPolicyState(stored)


def test_stored_expired_is_preserved_even_with_future_deadline() -> None:
    deadline, state = retention_projection(
        _meeting(
            retention_policy_state="expired",
            retention_delete_after=datetime(2030, 1, 1, tzinfo=UTC),
        ),
        _settings(),
        now=datetime(2026, 6, 1, tzinfo=UTC),
    )

    assert deadline == datetime(2030, 1, 1, tzinfo=UTC)
    assert state == RetentionPolicyState.EXPIRED


def test_unknown_stored_state_fails_closed_as_unsafe() -> None:
    deadline, state = retention_projection(
        _meeting(retention_policy_state="mystery"),
        _settings(),
        now=datetime(2026, 6, 1, tzinfo=UTC),
    )

    assert deadline == datetime(2027, 1, 1, tzinfo=UTC)
    assert state == RetentionPolicyState.UNSAFE


def test_projection_does_not_persist_or_mutate_meeting() -> None:
    meeting = _meeting()
    before = dict(vars(meeting))

    retention_projection(meeting, _settings(), now=datetime(2026, 6, 1, tzinfo=UTC))

    assert vars(meeting) == before
