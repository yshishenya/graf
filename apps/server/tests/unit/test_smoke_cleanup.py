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
    assert "select m.id as meeting_id" in script
    assert "playback_normalization_attempts" in script
    assert "playback_normalization_jobs" in script
    assert "_smoke_storage_prefix" in script
    assert "storage_residue" in script


def test_smoke_artifact_cleanup_deletes_processing_rows_before_meeting() -> None:
    script = (
        Path(__file__).resolve().parents[2]
        / "scripts"
        / "cleanup_smoke_artifacts.py"
    ).read_text(encoding="utf-8")

    ordered_fragments = [
        "delete from calendar_audit_events where meeting_id=:meeting_id",
        "delete from recording_calendar_context_links where meeting_id=:meeting_id",
        "delete from recording_calendar_match_attempts where consumed_by_meeting_id=:meeting_id",
        "delete from transcript_segments where meeting_id=:meeting_id",
        "delete from diarization_segments where meeting_id=:meeting_id",
        "delete from processing_audit_events where meeting_id=:meeting_id",
        '"processing_dependency_states",\n            processing_dependency_delete',
        "delete from dispatch_intents where meeting_id=:meeting_id",
        "delete from meeting_outcome_generation_attempts",
        "delete from meeting_outcome_items",
        "delete from meeting_outcome_sets where meeting_id=:meeting_id",
        "delete from processing_results where meeting_id=:meeting_id",
        "delete from mediascribe_jobs where meeting_id=:meeting_id",
        "delete from processing_workflows where meeting_id=:meeting_id",
        "delete from playback_normalization_attempts where meeting_id=:meeting_id",
        "delete from playback_normalization_jobs where meeting_id=:meeting_id",
        "delete from media_revisions where meeting_id=:meeting_id",
        "delete from meetings where id=:meeting_id",
    ]

    previous_position = -1
    for fragment in ordered_fragments:
        position = script.index(fragment)
        assert position > previous_position
        previous_position = position


def test_smoke_artifact_cleanup_matches_revision_linked_dependencies() -> None:
    script = (
        Path(__file__).resolve().parents[2]
        / "scripts"
        / "cleanup_smoke_artifacts.py"
    ).read_text(encoding="utf-8")

    dependency_delete = script.index(
        "delete from processing_dependency_states where meeting_id=:meeting_id"
    )
    revision_delete = script.index(
        "delete from media_revisions where meeting_id=:meeting_id"
    )

    assert "media_revision_id in (" in script
    assert "select id from media_revisions where meeting_id=:meeting_id" in script
    assert dependency_delete < revision_delete
