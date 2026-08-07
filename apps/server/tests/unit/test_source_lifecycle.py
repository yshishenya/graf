from datetime import UTC, datetime, timedelta

import pytest

from twobrain_rec_server.billing.source_lifecycle import (
    TRANSIENT_HARD_LIFETIME,
    TRANSIENT_PURGE_AFTER,
    SourceLifecycleError,
    SourceLifecycleState,
    TransientMediaState,
    admit_transient_media,
    source_cogs_evidence,
    source_lifecycle_state_for_gates,
    source_retention_deadline,
    source_retention_purge_due,
)

NOW = datetime(2026, 8, 7, 9, 0, tzinfo=UTC)


def test_no_archive_admission_is_explicit_and_never_counts_as_archive() -> None:
    admission = admit_transient_media(now=NOW, source_bytes=1_000, archive_requested=False)
    assert admission.state is TransientMediaState.ADMITTED
    assert admission.hard_deadline == NOW + TRANSIENT_HARD_LIFETIME
    assert admission.terminal_deadline is None

    with pytest.raises(SourceLifecycleError, match="cannot archive"):
        admit_transient_media(now=NOW, source_bytes=1_000, archive_requested=True)


def test_transient_media_purges_within_15_minutes_after_terminal_state() -> None:
    admission = admit_transient_media(now=NOW, source_bytes=1_000, archive_requested=False)
    processing = admission.processing_started()
    terminal = processing.mark_terminal(NOW + timedelta(hours=1))
    assert terminal.purge_deadline == NOW + timedelta(hours=1) + TRANSIENT_PURGE_AFTER
    assert not terminal.is_purge_due(NOW + timedelta(hours=1, minutes=14, seconds=59))
    assert terminal.purge_reason(NOW + timedelta(hours=1, minutes=15)) == (
        "terminal_processing_plus_15_minutes"
    )
    purged = terminal.mark_purged(NOW + timedelta(hours=1, minutes=15))
    assert purged.state is TransientMediaState.PURGED
    assert purged.is_purge_due(NOW + timedelta(days=2)) is False


def test_transient_media_hard_lifetime_cuts_off_stuck_processing() -> None:
    admission = admit_transient_media(now=NOW, source_bytes=1_000, archive_requested=False)
    processing = admission.processing_started()
    cutoff = NOW + TRANSIENT_HARD_LIFETIME
    assert processing.is_purge_due(cutoff)
    assert processing.purge_reason(cutoff) == "hard_lifetime_24_hours"


def test_transient_media_hard_lifetime_wins_over_a_late_terminal_purge_deadline() -> None:
    admission = admit_transient_media(now=NOW, source_bytes=1_000, archive_requested=False)
    terminal = admission.processing_started().mark_terminal(NOW + timedelta(hours=23, minutes=59))

    assert terminal.purge_deadline == NOW + TRANSIENT_HARD_LIFETIME
    assert terminal.purge_reason(NOW + TRANSIENT_HARD_LIFETIME) == "hard_lifetime_24_hours"


def test_source_retention_waits_for_both_import_and_playback_gates() -> None:
    imported = NOW + timedelta(hours=1)
    verified = NOW + timedelta(hours=2)
    period = timedelta(days=7)
    assert source_retention_deadline(
        transcript_imported_at=imported,
        playback_verified_at=None,
        retention_period=period,
    ) is None
    deadline = source_retention_deadline(
        transcript_imported_at=imported,
        playback_verified_at=verified,
        retention_period=period,
    )
    assert deadline == verified + period
    assert source_retention_purge_due(
        now=deadline - timedelta(seconds=1),
        transcript_imported_at=imported,
        playback_verified_at=verified,
        retention_period=period,
    ) is False
    assert source_retention_purge_due(
        now=deadline,
        transcript_imported_at=imported,
        playback_verified_at=verified,
        retention_period=period,
    ) is True


def test_source_retention_policy_reopens_when_a_gate_is_lost() -> None:
    with pytest.raises(SourceLifecycleError):
        source_retention_deadline(
            transcript_imported_at=NOW,
            playback_verified_at=NOW,
            retention_period=timedelta(0),
        )
    with pytest.raises(SourceLifecycleError):
        admit_transient_media(now=NOW.replace(tzinfo=None), source_bytes=1, archive_requested=False)


def test_source_gate_state_is_fail_closed_and_reopens_after_policy_or_gate_loss() -> None:
    state, deadline = source_lifecycle_state_for_gates(
        transcript_imported_at=NOW,
        playback_verified_at=None,
        now=NOW + timedelta(days=99),
        retention_period=timedelta(days=7),
    )
    assert state is SourceLifecycleState.RECOVERABLE
    assert deadline is None

    due_state, due_at = source_lifecycle_state_for_gates(
        transcript_imported_at=NOW,
        playback_verified_at=NOW,
        now=NOW + timedelta(days=7),
        retention_period=timedelta(days=7),
    )
    assert due_state is SourceLifecycleState.PURGE_DUE
    assert due_at == NOW + timedelta(days=7)

    unconfigured_state, unconfigured_deadline = source_lifecycle_state_for_gates(
        transcript_imported_at=NOW,
        playback_verified_at=NOW,
        now=NOW + timedelta(days=30),
        retention_period=None,
    )
    assert unconfigured_state is SourceLifecycleState.RECOVERABLE
    assert unconfigured_deadline is None


def test_source_cogs_evidence_keeps_exact_bytes_and_zero_customer_quota() -> None:
    evidence = source_cogs_evidence(
        byte_length=115_200_123,
        policy_version="source-audio-v1",
        backup_expiry_days=30,
    )
    assert evidence == {
        "actual_primary_bytes": 115_200_123,
        "customer_quota_bytes": 0,
        "backup_expiry_days": 30,
        "policy_version": "source-audio-v1",
        "cogs_status": "exact_bytes_recorded_cost_model_external",
    }
