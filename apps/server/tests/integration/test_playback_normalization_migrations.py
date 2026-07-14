from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import IntegrityError

from twobrain_rec_server.config import get_settings

REPO_ROOT = Path(__file__).resolve().parents[4]
MIGRATION = (
    REPO_ROOT
    / "apps/server/src/twobrain_rec_server/db/migrations/versions/0022_playback_normalization.py"
)
PROFILE = "review_m4a_aac_lc_48k_mono_64k_v1"


def _load_migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("playback_normalization_migration", MIGRATION)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _alembic_config(database_path: Path, monkeypatch) -> Config:
    monkeypatch.setenv("TWOBRAIN_DATABASE_URL", f"sqlite+aiosqlite:///{database_path}")
    get_settings.cache_clear()
    config = Config(str(REPO_ROOT / "apps/server/alembic.ini"))
    config.set_main_option(
        "script_location",
        str(REPO_ROOT / "apps/server/src/twobrain_rec_server/db/migrations"),
    )
    return config


def _seed_legacy_playback_rows(database_path: Path) -> dict[str, str]:
    ids = {
        name: uuid4().hex
        for name in (
            "organization",
            "workspace",
            "user",
            "device",
            "meeting",
            "revision",
            "legacy_one",
            "legacy_two",
        )
    }
    engine = create_engine(f"sqlite:///{database_path}")
    try:
        with engine.begin() as connection:
            connection.exec_driver_sql(
                "insert into organizations (id, slug, name) values (?, 'normalization', 'Normalization')",
                (ids["organization"],),
            )
            connection.exec_driver_sql(
                "insert into workspaces (id, organization_id, slug, name) values (?, ?, 'normalization', 'Normalization')",
                (ids["workspace"], ids["organization"]),
            )
            connection.exec_driver_sql(
                "insert into user_identities (id, organization_id, external_subject) values (?, ?, 'normalization@example.test')",
                (ids["user"], ids["organization"]),
            )
            connection.exec_driver_sql(
                "insert into registered_devices (id, workspace_id, user_id, device_public_id, status, registration_state) values (?, ?, ?, 'normalization-device', 'active', 'approved')",
                (ids["device"], ids["workspace"], ids["user"]),
            )
            connection.exec_driver_sql(
                "insert into meetings (id, workspace_id, created_by_user_id, device_id, local_recording_id, duration_seconds, status) values (?, ?, ?, ?, 'normalization-meeting', 60, 'ready')",
                (ids["meeting"], ids["workspace"], ids["user"], ids["device"]),
            )
            connection.exec_driver_sql(
                "insert into media_revisions (id, workspace_id, meeting_id, local_media_revision_id, source_kind, status, immutable, accepted_at) values (?, ?, ?, 'normalization-revision', 'manual_upload', 'accepted', 1, '2026-07-14 08:00:00+00:00')",
                (ids["revision"], ids["workspace"], ids["meeting"]),
            )
            for artifact_id, object_suffix in (
                (ids["legacy_one"], "one"),
                (ids["legacy_two"], "two"),
            ):
                connection.exec_driver_sql(
                    """
                    insert into track_artifacts
                        (id, meeting_id, media_revision_id, workspace_id, track_role,
                         codec, sample_rate_hz, channel_count, duration_seconds,
                         byte_length, sha256, storage_object_key, status)
                    values (?, ?, ?, ?, 'playback', 'aac', 48000, 1, 60,
                            480000, ?, ?, 'stored')
                    """,
                    (
                        artifact_id,
                        ids["meeting"],
                        ids["revision"],
                        ids["workspace"],
                        ("a" if object_suffix == "one" else "b") * 64,
                        f"legacy/{object_suffix}",
                    ),
                )
    finally:
        engine.dispose()
    return ids


def test_migration_declares_additive_revision_contract() -> None:
    assert MIGRATION.exists()
    migration = _load_migration()

    assert migration.revision == "0022_playback_normalization"
    assert migration.down_revision == "0021_calendar_auto_context_match"
    assert set(migration.PLAYBACK_NORMALIZATION_TABLES) == {
        "playback_normalization_jobs",
        "playback_normalization_attempts",
        "playback_backfill_runs",
    }


def test_sqlite_upgrade_preserves_legacy_rows_and_enforces_one_canonical(
    tmp_path, monkeypatch
) -> None:
    database_path = tmp_path / "playback-normalization.db"
    config = _alembic_config(database_path, monkeypatch)
    command.upgrade(config, "0021_calendar_auto_context_match")
    ids = _seed_legacy_playback_rows(database_path)

    command.upgrade(config, "head")

    engine = create_engine(f"sqlite:///{database_path}")
    try:
        inspector = inspect(engine)
        assert {
            "playback_normalization_jobs",
            "playback_normalization_attempts",
            "playback_backfill_runs",
        } <= set(inspector.get_table_names())
        artifact_columns = {column["name"] for column in inspector.get_columns("track_artifacts")}
        assert {
            "normalization_profile_version",
            "validated_at",
            "derivation_kind",
            "source_fingerprint_sha256",
            "validation_version",
        } <= artifact_columns
        artifact_indexes = {index["name"] for index in inspector.get_indexes("track_artifacts")}
        assert "uq_track_artifacts_canonical_playback" in artifact_indexes

        with engine.connect() as connection:
            legacy_count = connection.exec_driver_sql(
                "select count(*) from track_artifacts where media_revision_id = ? and normalization_profile_version is null",
                (ids["revision"],),
            ).scalar_one()
        assert legacy_count == 2

        canonical_values = (
            uuid4().hex,
            ids["meeting"],
            ids["revision"],
            ids["workspace"],
            "c" * 64,
            "normalization/attempts/one/meeting-review.m4a",
            PROFILE,
            "2026-07-14 09:00:00+00:00",
            "source_byte_copy",
            "f" * 64,
            "playback_validator_v1",
        )
        insert_sql = """
            insert into track_artifacts
                (id, meeting_id, media_revision_id, workspace_id, track_role,
                 codec, sample_rate_hz, channel_count, duration_seconds,
                 byte_length, sha256, storage_object_key, status,
                 normalization_profile_version, validated_at, derivation_kind,
                 source_fingerprint_sha256, validation_version)
            values (?, ?, ?, ?, 'playback', 'aac', 48000, 1, 60,
                    480000, ?, ?, 'stored', ?, ?, ?, ?, ?)
        """
        with engine.begin() as connection:
            connection.exec_driver_sql(insert_sql, canonical_values)
        duplicate = list(canonical_values)
        duplicate[0] = uuid4().hex
        duplicate[4] = "d" * 64
        duplicate[5] = "normalization/attempts/two/meeting-review.m4a"
        with pytest.raises(IntegrityError), engine.begin() as connection:
            connection.exec_driver_sql(insert_sql, tuple(duplicate))
    finally:
        engine.dispose()


def test_sqlite_upgrade_rejects_invalid_normalization_truth(tmp_path, monkeypatch) -> None:
    database_path = tmp_path / "playback-normalization-constraints.db"
    config = _alembic_config(database_path, monkeypatch)
    command.upgrade(config, "0021_calendar_auto_context_match")
    ids = _seed_legacy_playback_rows(database_path)
    command.upgrade(config, "head")

    engine = create_engine(f"sqlite:///{database_path}")
    try:
        backfill_sql = """
            insert into playback_backfill_runs
                (id, workspace_id, profile_version, state)
            values (:id, :workspace_id, :profile_version, :state)
        """
        invalid_backfills = (
            {"profile_version": PROFILE, "state": "unknown"},
            {"profile_version": "unknown_profile", "state": "inventory_pending"},
        )
        for invalid in invalid_backfills:
            with pytest.raises(IntegrityError), engine.begin() as connection:
                connection.exec_driver_sql(
                    backfill_sql,
                    {
                        "id": uuid4().hex,
                        "workspace_id": ids["workspace"],
                        **invalid,
                    },
                )

        job_sql = """
            insert into playback_normalization_jobs
                (id, organization_id, workspace_id, requested_by_user_id,
                 source_device_id, meeting_id, media_revision_id, profile_version,
                 validation_version, trigger_kind, priority_class, source_kind,
                 source_fingerprint_sha256, planned_action, state, reason_code,
                 workflow_id)
            values
                (:id, :organization_id, :workspace_id, :requested_by_user_id,
                 :source_device_id, :meeting_id, :media_revision_id, :profile_version,
                 :validation_version, :trigger_kind, :priority_class, :source_kind,
                 :source_fingerprint_sha256, :planned_action, :state, :reason_code,
                 :workflow_id)
        """
        valid_job = {
            "id": uuid4().hex,
            "organization_id": ids["organization"],
            "workspace_id": ids["workspace"],
            "requested_by_user_id": ids["user"],
            "source_device_id": ids["device"],
            "meeting_id": ids["meeting"],
            "media_revision_id": ids["revision"],
            "profile_version": PROFILE,
            "validation_version": "playback_validator_v1",
            "trigger_kind": "finalize",
            "priority_class": "new_ingest",
            "source_kind": "manual_upload",
            "source_fingerprint_sha256": "e" * 64,
            "planned_action": "normalize_source",
            "state": "queued",
            "reason_code": None,
            "workflow_id": "playback-normalization/constraint-proof",
        }
        invalid_jobs = (
            {"state": "unknown"},
            {"profile_version": "unknown_profile"},
            {"validation_version": "unknown_validator"},
            {"trigger_kind": "unknown"},
            {"priority_class": "unknown"},
            {"planned_action": "unknown"},
            {"source_fingerprint_sha256": "short"},
            {"reason_code": "storage_unavailable"},
        )
        for override in invalid_jobs:
            with pytest.raises(IntegrityError), engine.begin() as connection:
                connection.exec_driver_sql(
                    job_sql,
                    {**valid_job, "id": uuid4().hex, **override},
                )

        with engine.begin() as connection:
            connection.exec_driver_sql(job_sql, valid_job)

        attempt_sql = """
            insert into playback_normalization_attempts
                (id, workspace_id, meeting_id, media_revision_id, job_id,
                 attempt_number, cycle_number, state, storage_object_key,
                 derivation_kind, source_stream_count, source_audio_stream_count,
                 source_duration_ms, cleaned_at)
            values
                (:id, :workspace_id, :meeting_id, :media_revision_id, :job_id,
                 :attempt_number, :cycle_number, :state, :storage_object_key,
                 :derivation_kind, :source_stream_count, :source_audio_stream_count,
                 :source_duration_ms, :cleaned_at)
        """
        valid_attempt = {
            "id": uuid4().hex,
            "workspace_id": ids["workspace"],
            "meeting_id": ids["meeting"],
            "media_revision_id": ids["revision"],
            "job_id": valid_job["id"],
            "attempt_number": 1,
            "cycle_number": 1,
            "state": "local_preparing",
            "storage_object_key": "normalization/attempts/constraint-proof/output.m4a",
            "derivation_kind": "single_source_transcode",
            "source_stream_count": 1,
            "source_audio_stream_count": 1,
            "source_duration_ms": 1,
            "cleaned_at": None,
        }
        invalid_attempts = (
            {"state": "unknown"},
            {"derivation_kind": "unknown"},
            {"source_duration_ms": 0},
            {"state": "cleaned", "cleaned_at": None},
        )
        for override in invalid_attempts:
            with pytest.raises(IntegrityError), engine.begin() as connection:
                connection.exec_driver_sql(
                    attempt_sql,
                    {
                        **valid_attempt,
                        "id": uuid4().hex,
                        "storage_object_key": (
                            "normalization/attempts/" + uuid4().hex + "/output.m4a"
                        ),
                        **override,
                    },
                )
    finally:
        engine.dispose()


def test_sqlite_downgrade_removes_only_feature_099_schema(tmp_path, monkeypatch) -> None:
    database_path = tmp_path / "playback-normalization-downgrade.db"
    config = _alembic_config(database_path, monkeypatch)
    command.upgrade(config, "head")
    command.downgrade(config, "0021_calendar_auto_context_match")

    engine = create_engine(f"sqlite:///{database_path}")
    try:
        inspector = inspect(engine)
        assert "meetings" in inspector.get_table_names()
        assert "playback_normalization_jobs" not in inspector.get_table_names()
        artifact_columns = {column["name"] for column in inspector.get_columns("track_artifacts")}
        assert "normalization_profile_version" not in artifact_columns
    finally:
        engine.dispose()
