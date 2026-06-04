import pytest

from twobrain_rec_server.deployment import SmokeCleanupRecord


def test_smoke_cleanup_pass_records_removed_counts_without_residue() -> None:
    cleanup = SmokeCleanupRecord(
        run_id="smoke-20260604-0001",
        cleanup_result="pass",
        database_records_removed=6,
        object_keys_removed=3,
    )

    assert cleanup.cleanup_result == "pass"
    assert cleanup.residue_records == []


def test_smoke_cleanup_requires_owner_for_residue() -> None:
    with pytest.raises(ValueError, match="residue owner"):
        SmokeCleanupRecord(
            run_id="smoke-20260604-0001",
            cleanup_result="residue_recorded",
            residue_records=["track_artifacts:1"],
        )


def test_smoke_cleanup_pass_rejects_residue_records() -> None:
    with pytest.raises(ValueError, match="pass cleanup"):
        SmokeCleanupRecord(
            run_id="smoke-20260604-0001",
            cleanup_result="pass",
            residue_records=["minio:object-key"],
        )
