from pathlib import Path

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


def test_smoke_auth_cleanup_deletes_binding_before_session() -> None:
    script = (
        Path(__file__).resolve().parents[2]
        / "scripts"
        / "cleanup_smoke_auth_session.py"
    ).read_text(encoding="utf-8")

    binding_delete = "delete from auth_session_device_bindings"
    session_delete = "delete from auth_sessions"

    assert 'parser.add_argument("--auth-session-id")' in script
    assert binding_delete in script
    assert session_delete in script
    assert script.index(binding_delete) < script.index(session_delete)


def test_smoke_artifact_cleanup_supports_run_id_only_identity_cleanup() -> None:
    script = (
        Path(__file__).resolve().parents[2]
        / "scripts"
        / "cleanup_smoke_artifacts.py"
    ).read_text(encoding="utf-8")

    assert "build_smoke_identity_seed(run_id)" in script
    assert "if args.execute:" in script
    assert "args.meeting_id and args.session_id" not in script
    assert "delete from registered_devices where id=:device_id" in script
    assert "delete from auth_session_device_bindings where registered_device_id=:device_id" in script
