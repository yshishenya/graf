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
    / "apps/server/src/twobrain_rec_server/db/migrations/versions/0021_calendar_auto_context_match.py"
)


def _load_migration_module(path: Path, module_name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _alembic_config(database_path: Path, monkeypatch) -> Config:
    database_url = f"sqlite+aiosqlite:///{database_path}"
    monkeypatch.setenv("TWOBRAIN_DATABASE_URL", database_url)
    get_settings.cache_clear()
    config = Config(str(REPO_ROOT / "apps/server/alembic.ini"))
    config.set_main_option(
        "script_location",
        str(REPO_ROOT / "apps/server/src/twobrain_rec_server/db/migrations"),
    )
    return config


def _seed_legacy_calendar_rows(database_path: Path) -> dict[str, str]:
    ids = {
        name: uuid4().hex
        for name in (
            "organization",
            "workspace",
            "user",
            "device",
            "meeting_titled",
            "meeting_untitled",
            "meeting_no_context",
            "meeting_tie",
            "meeting_unsafe",
            "source",
            "calendar",
            "event_active",
            "event_old",
            "event_new",
            "event_unsafe",
            "link_active",
            "link_unlinked",
            "link_old",
            "link_new",
            "link_tie_low",
            "link_tie_high",
            "link_unsafe",
        )
    }
    ids["link_tie_low"] = "00000000000000000000000000009801"
    ids["link_tie_high"] = "00000000000000000000000000009802"
    engine = create_engine(f"sqlite:///{database_path}")
    try:
        with engine.begin() as connection:
            connection.exec_driver_sql(
                "insert into organizations (id, slug, name) values (?, ?, ?)",
                (ids["organization"], "calendar-auto-match", "Calendar Auto Match"),
            )
            connection.exec_driver_sql(
                "insert into workspaces (id, organization_id, slug, name) values (?, ?, ?, ?)",
                (ids["workspace"], ids["organization"], "calendar-auto-match", "Calendar Auto Match"),
            )
            connection.exec_driver_sql(
                "insert into user_identities (id, organization_id, external_subject, display_name) values (?, ?, ?, ?)",
                (ids["user"], ids["organization"], "calendar-auto-match@example.test", "Synthetic Owner"),
            )
            connection.exec_driver_sql(
                "insert into workspace_memberships (workspace_id, user_id, role, status) values (?, ?, 'owner', 'active')",
                (ids["workspace"], ids["user"]),
            )
            connection.exec_driver_sql(
                """
                insert into registered_devices
                    (id, workspace_id, user_id, device_public_id, status, registration_state)
                values (?, ?, ?, ?, 'active', 'approved')
                """,
                (ids["device"], ids["workspace"], ids["user"], "calendar-auto-match-device"),
            )
            for meeting_id, local_id, title in (
                (ids["meeting_titled"], "calendar-auto-match-titled", "Legacy title"),
                (ids["meeting_untitled"], "calendar-auto-match-untitled", None),
                (ids["meeting_no_context"], "calendar-auto-match-no-context", None),
                (ids["meeting_tie"], "calendar-auto-match-tie", None),
                (ids["meeting_unsafe"], "calendar-auto-match-unsafe", None),
            ):
                connection.exec_driver_sql(
                    """
                    insert into meetings
                        (id, workspace_id, created_by_user_id, device_id, local_recording_id,
                         title, duration_seconds, status)
                    values (?, ?, ?, ?, ?, ?, 60, 'ready')
                    """,
                    (
                        meeting_id,
                        ids["workspace"],
                        ids["user"],
                        ids["device"],
                        local_id,
                        title,
                    ),
                )
            connection.exec_driver_sql(
                """
                insert into calendar_sources
                    (id, workspace_id, owner_user_id, provider_family, auth_mode,
                     credential_state, connection_state, sync_state)
                values (?, ?, ?, 'caldav', 'app_password', 'active', 'active', 'current')
                """,
                (ids["source"], ids["workspace"], ids["user"]),
            )
            connection.exec_driver_sql(
                """
                insert into external_calendars
                    (id, calendar_source_id, workspace_id, provider_calendar_id, display_label, selected)
                values (?, ?, ?, 'synthetic-calendar', 'Synthetic Calendar', 1)
                """,
                (ids["calendar"], ids["source"], ids["workspace"]),
            )
            for event_id, provider_id, title in (
                (ids["event_active"], "active", "Active context"),
                (ids["event_old"], "old", "Older context"),
                (ids["event_new"], "new", "Newer context"),
                (
                    ids["event_unsafe"],
                    "unsafe",
                    "https://meet.example.test/private?token=synthetic-secret",
                ),
            ):
                connection.exec_driver_sql(
                    """
                    insert into calendar_event_snapshots
                        (id, workspace_id, calendar_source_id, external_calendar_id,
                         provider_event_id, starts_at, ends_at, title,
                         privacy_class, safe_to_show_in_list, safe_to_use_as_title)
                    values (?, ?, ?, ?, ?, ?, ?, ?, 'public', 1, 1)
                    """,
                    (
                        event_id,
                        ids["workspace"],
                        ids["source"],
                        ids["calendar"],
                        provider_id,
                        "2026-07-13 09:00:00+00:00",
                        "2026-07-13 10:00:00+00:00",
                        title,
                    ),
                )
            context_rows = (
                (
                    ids["link_active"],
                    ids["meeting_titled"],
                    ids["event_active"],
                    "2026-07-13 09:00:00+00:00",
                    None,
                    "2026-07-13 09:00:00+00:00",
                    "2026-07-13 09:00:00+00:00",
                ),
                (
                    ids["link_unlinked"],
                    ids["meeting_titled"],
                    ids["event_new"],
                    "2026-07-13 09:30:00+00:00",
                    "2026-07-13 09:45:00+00:00",
                    "2026-07-13 09:45:00+00:00",
                    "2026-07-13 09:30:00+00:00",
                ),
                (
                    ids["link_old"],
                    ids["meeting_untitled"],
                    ids["event_old"],
                    "2026-07-13 08:00:00+00:00",
                    "2026-07-13 08:30:00+00:00",
                    "2026-07-13 08:30:00+00:00",
                    "2026-07-13 08:00:00+00:00",
                ),
                (
                    ids["link_new"],
                    ids["meeting_untitled"],
                    ids["event_new"],
                    "2026-07-13 10:00:00+00:00",
                    "2026-07-13 10:30:00+00:00",
                    "2026-07-13 10:30:00+00:00",
                    "2026-07-13 10:00:00+00:00",
                ),
                (
                    ids["link_tie_low"],
                    ids["meeting_tie"],
                    ids["event_old"],
                    "2026-07-13 11:00:00+00:00",
                    None,
                    "2026-07-13 11:00:00+00:00",
                    "2026-07-13 11:00:00+00:00",
                ),
                (
                    ids["link_tie_high"],
                    ids["meeting_tie"],
                    ids["event_new"],
                    "2026-07-13 11:00:00+00:00",
                    None,
                    "2026-07-13 11:00:00+00:00",
                    "2026-07-13 11:00:00+00:00",
                ),
                (
                    ids["link_unsafe"],
                    ids["meeting_unsafe"],
                    ids["event_unsafe"],
                    "2026-07-13 12:00:00+00:00",
                    None,
                    "2026-07-13 12:00:00+00:00",
                    "2026-07-13 12:00:00+00:00",
                ),
            )
            for (
                link_id,
                meeting_id,
                event_id,
                linked_at,
                unlinked_at,
                updated_at,
                created_at,
            ) in context_rows:
                connection.exec_driver_sql(
                    """
                    insert into recording_calendar_context_links
                        (id, workspace_id, meeting_id, calendar_event_snapshot_id,
                         context_confidence, title_source, roster_source,
                         manual_override_state, linked_at, unlinked_at, created_at, updated_at)
                    values (?, ?, ?, ?, 'high', 'calendar', 'calendar',
                            'none', ?, ?, ?, ?)
                    """,
                    (
                        link_id,
                        ids["workspace"],
                        meeting_id,
                        event_id,
                        linked_at,
                        unlinked_at,
                        created_at,
                        updated_at,
                    ),
                )
    finally:
        engine.dispose()
    return ids


def test_calendar_auto_context_models_are_exported() -> None:
    from twobrain_rec_server import db
    from twobrain_rec_server.db import models

    assert hasattr(models, "RecordingCalendarMatchAttempt")
    assert hasattr(db.models, "RecordingCalendarMatchAttempt")
    assert hasattr(models.Meeting, "title_source")
    assert hasattr(models.Meeting, "title_updated_at")
    assert hasattr(models.Meeting, "create_request_fingerprint_sha256")


def test_calendar_auto_context_migration_declares_revision_and_rls_boundary() -> None:
    assert MIGRATION.exists()
    migration = _load_migration_module(MIGRATION, "calendar_auto_context_match_migration")

    assert migration.revision == "0021_calendar_auto_context_match"
    assert migration.down_revision == "0020_user_scoped_recording_ids"
    assert "recording_calendar_match_attempts" in migration.CALENDAR_AUTO_CONTEXT_TABLES


def test_sqlite_upgrade_reconciles_title_provenance_and_one_context_row(tmp_path, monkeypatch) -> None:
    database_path = tmp_path / "calendar-auto-context.db"
    config = _alembic_config(database_path, monkeypatch)
    command.upgrade(config, "0020_user_scoped_recording_ids")
    ids = _seed_legacy_calendar_rows(database_path)

    command.upgrade(config, "head")

    engine = create_engine(f"sqlite:///{database_path}")
    try:
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        meeting_columns = {column["name"] for column in inspector.get_columns("meetings")}
        context_columns = {
            column["name"]: column
            for column in inspector.get_columns("recording_calendar_context_links")
        }
        attempt_indexes = {
            index["name"]
            for index in inspector.get_indexes("recording_calendar_match_attempts")
        }
        attempt_columns = {
            column["name"]
            for column in inspector.get_columns("recording_calendar_match_attempts")
        }
        attempt_uniques = {
            constraint["name"]
            for constraint in inspector.get_unique_constraints("recording_calendar_match_attempts")
        }
        context_uniques = {
            constraint["name"]
            for constraint in inspector.get_unique_constraints("recording_calendar_context_links")
        }
        with engine.connect() as connection:
            title_rows = dict(
                connection.exec_driver_sql(
                    "select local_recording_id, title_source from meetings"
                ).all()
            )
            titled_context = connection.exec_driver_sql(
                """
                select id, context_state, matched_title
                from recording_calendar_context_links
                where meeting_id = ?
                """,
                (ids["meeting_titled"],),
            ).one()
            untitled_context = connection.exec_driver_sql(
                """
                select id, context_state, calendar_event_snapshot_id, matched_title
                from recording_calendar_context_links
                where meeting_id = ?
                """,
                (ids["meeting_untitled"],),
            ).one()
            tie_context = connection.exec_driver_sql(
                """
                select id, context_state, calendar_event_snapshot_id
                from recording_calendar_context_links
                where meeting_id = ?
                """,
                (ids["meeting_tie"],),
            ).one()
            unsafe_context = connection.exec_driver_sql(
                """
                select context_state, matched_title, matched_title_state
                from recording_calendar_context_links
                where meeting_id = ?
                """,
                (ids["meeting_unsafe"],),
            ).one()
        with pytest.raises(IntegrityError), engine.begin() as connection:
            for suffix, idempotency_hash in (("one", "a" * 64), ("two", "b" * 64)):
                connection.exec_driver_sql(
                    """
                        insert into recording_calendar_match_attempts
                            (id, workspace_id, owner_user_id, device_id,
                             local_recording_id, idempotency_key_sha256,
                             request_fingerprint_sha256, recording_started_at,
                             decision_intent, attempt_state, context_confidence,
                             candidate_event_ids_json, candidate_count,
                             matched_title_state, matched_roster_json,
                             matched_roster_state, matched_roster_count,
                             freshness_class, matcher_version, evaluated_at, expires_at)
                        values (?, ?, ?, ?, 'duplicate-local-recording', ?, ?,
                                '2026-07-13 12:00:00+00:00', 'automatic',
                                'no_context', 'none', '[]', 0, 'unavailable', '[]',
                                'not_available', 0, 'current', 'calendar_auto_match_v1',
                                '2026-07-13 12:00:00+00:00',
                                '2026-07-14 12:00:00+00:00')
                        """,
                    (
                        uuid4().hex,
                        ids["workspace"],
                        ids["user"],
                        ids["device"],
                        idempotency_hash,
                        (suffix * 64)[:64],
                    ),
                )
        with pytest.raises(IntegrityError), engine.begin() as connection:
            for suffix in ("first", "second"):
                connection.exec_driver_sql(
                    """
                        insert into recording_calendar_match_attempts
                            (id, workspace_id, owner_user_id, device_id,
                             local_recording_id, idempotency_key_sha256,
                             request_fingerprint_sha256, recording_started_at,
                             decision_intent, attempt_state, context_confidence,
                             candidate_event_ids_json, candidate_count,
                             matched_title_state, matched_roster_json,
                             matched_roster_state, matched_roster_count,
                             freshness_class, matcher_version, evaluated_at, expires_at)
                        values (?, ?, ?, ?, ?, ?, ?,
                                '2026-07-13 12:00:00+00:00', 'automatic',
                                'no_context', 'none', '[]', 0, 'unavailable', '[]',
                                'not_available', 0, 'current', 'calendar_auto_match_v1',
                                '2026-07-13 12:00:00+00:00',
                                '2026-07-14 12:00:00+00:00')
                        """,
                    (
                        uuid4().hex,
                        ids["workspace"],
                        ids["user"],
                        ids["device"],
                        f"idempotency-{suffix}",
                        "c" * 64,
                        (suffix * 64)[:64],
                    ),
                )
        with pytest.raises(IntegrityError), engine.begin() as connection:
            connection.exec_driver_sql(
                """
                    insert into recording_calendar_context_links
                        (id, workspace_id, meeting_id, calendar_event_snapshot_id,
                         context_confidence, context_reasons_json, title_source,
                         roster_source, manual_override_state, context_state,
                         decision_source, candidate_event_ids_json, candidate_count,
                         matched_title_state, matched_roster_json,
                         matched_roster_state, matched_roster_count)
                    values (?, ?, ?, ?, 'high', '[]', 'calendar', 'none', 'none',
                            'legacy_linked', 'legacy', '[]', 0, 'available', '[]',
                            'not_available', 0)
                    """,
                (
                    uuid4().hex,
                    ids["workspace"],
                    ids["meeting_titled"],
                    ids["event_active"],
                ),
            )
    finally:
        engine.dispose()
        get_settings.cache_clear()

    assert "recording_calendar_match_attempts" in tables
    assert {
        "title_source",
        "title_updated_at",
        "create_request_fingerprint_sha256",
    } <= meeting_columns
    assert context_columns["calendar_event_snapshot_id"]["nullable"] is True
    assert {
        "match_attempt_id",
        "context_state",
        "safe_reason_code",
        "decision_source",
        "matcher_version",
        "candidate_event_ids_json",
        "matched_title",
        "matched_roster_json",
        "recurring_series_key_sha256",
    } <= set(context_columns)
    assert {
        "ix_calendar_match_attempts_owner_expiry",
        "ix_calendar_match_attempts_state_evaluated",
    } <= attempt_indexes
    assert {
        "workspace_id",
        "owner_user_id",
        "device_id",
        "local_recording_id",
        "idempotency_key_sha256",
        "request_fingerprint_sha256",
        "recording_started_at",
        "decision_intent",
        "selected_event_snapshot_id",
        "attempt_state",
        "safe_reason_code",
        "context_confidence",
        "candidate_event_ids_json",
        "candidate_count",
        "matched_event_snapshot_id",
        "matched_event_starts_at",
        "matched_event_ends_at",
        "matched_title",
        "matched_title_state",
        "matched_roster_json",
        "matched_roster_state",
        "matched_roster_count",
        "recurring_series_key_sha256",
        "source_version_fingerprint_sha256",
        "freshness_class",
        "matcher_version",
        "evaluated_at",
        "expires_at",
        "consumed_by_meeting_id",
        "consumed_at",
        "created_at",
        "updated_at",
    } <= attempt_columns
    assert "uq_calendar_match_attempts_workspace_owner_local" in attempt_uniques
    assert "uq_calendar_match_attempts_workspace_owner_idempotency" in attempt_uniques
    assert "uq_recording_calendar_context_links_workspace_meeting" in context_uniques
    assert "uq_recording_calendar_context_links_match_attempt" in context_uniques
    assert title_rows["calendar-auto-match-titled"] == "legacy_unknown"
    assert title_rows["calendar-auto-match-untitled"] == "generic"
    assert tuple(titled_context) == (ids["link_active"], "legacy_linked", "Active context")
    assert tuple(untitled_context) == (ids["link_new"], "cleared_by_user", None, None)
    assert tuple(tie_context) == (ids["link_tie_high"], "legacy_linked", ids["event_new"])
    assert tuple(unsafe_context) == ("legacy_linked", None, "policy_hidden")


def test_sqlite_downgrade_restores_0020_schema(tmp_path, monkeypatch) -> None:
    database_path = tmp_path / "calendar-auto-context-rollback.db"
    config = _alembic_config(database_path, monkeypatch)
    command.upgrade(config, "0020_user_scoped_recording_ids")
    ids = _seed_legacy_calendar_rows(database_path)
    command.upgrade(config, "head")

    engine = create_engine(f"sqlite:///{database_path}")
    try:
        with engine.begin() as connection:
            attempt_id = uuid4().hex
            connection.exec_driver_sql(
                """
                insert into recording_calendar_match_attempts
                    (id, workspace_id, owner_user_id, device_id, local_recording_id,
                     idempotency_key_sha256, request_fingerprint_sha256,
                     recording_started_at, decision_intent, attempt_state,
                     context_confidence, candidate_event_ids_json, candidate_count,
                     matched_title_state, matched_roster_json, matched_roster_state,
                     matched_roster_count, freshness_class, matcher_version,
                     evaluated_at, expires_at)
                values (?, ?, ?, ?, 'calendar-auto-match-no-context',
                        'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
                        'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb',
                        '2026-07-13 12:00:00+00:00', 'automatic', 'no_context',
                        'none', '[]', 0, 'unavailable', '[]', 'not_available',
                        0, 'current', 'calendar_auto_match_v1',
                        '2026-07-13 12:00:00+00:00', '2026-07-14 12:00:00+00:00')
                """,
                (attempt_id, ids["workspace"], ids["user"], ids["device"]),
            )
            connection.exec_driver_sql(
                """
                insert into recording_calendar_context_links
                    (id, workspace_id, meeting_id, calendar_event_snapshot_id,
                     match_attempt_id, context_state, context_confidence,
                     context_reasons_json, title_source, roster_source,
                     manual_override_state, decision_source, candidate_event_ids_json,
                     candidate_count, matched_title_state, matched_roster_json,
                     matched_roster_state, matched_roster_count)
                values (?, ?, ?, null, ?, 'no_context', 'none', '[]', 'generic',
                        'none', 'none', 'automatic', '[]', 0, 'unavailable', '[]',
                        'not_available', 0)
                """,
                (uuid4().hex, ids["workspace"], ids["meeting_no_context"], attempt_id),
            )
    finally:
        engine.dispose()

    command.downgrade(config, "0020_user_scoped_recording_ids")

    engine = create_engine(f"sqlite:///{database_path}")
    try:
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        meeting_columns = {column["name"] for column in inspector.get_columns("meetings")}
        context_columns = {
            column["name"]: column
            for column in inspector.get_columns("recording_calendar_context_links")
        }
        with engine.connect() as connection:
            rolled_back_no_context_count = connection.exec_driver_sql(
                "select count(*) from recording_calendar_context_links where meeting_id = ?",
                (ids["meeting_no_context"],),
            ).scalar_one()
            rolled_back_cleared_count = connection.exec_driver_sql(
                "select count(*) from recording_calendar_context_links where meeting_id = ?",
                (ids["meeting_untitled"],),
            ).scalar_one()
            rolled_back_active_count = connection.exec_driver_sql(
                "select count(*) from recording_calendar_context_links where meeting_id in (?, ?)",
                (ids["meeting_titled"], ids["meeting_tie"]),
            ).scalar_one()
    finally:
        engine.dispose()
        get_settings.cache_clear()

    assert "recording_calendar_match_attempts" not in tables
    assert "title_source" not in meeting_columns
    assert "title_updated_at" not in meeting_columns
    assert "create_request_fingerprint_sha256" not in meeting_columns
    assert "context_state" not in context_columns
    assert context_columns["calendar_event_snapshot_id"]["nullable"] is False
    assert rolled_back_no_context_count == 0
    assert rolled_back_cleared_count == 0
    assert rolled_back_active_count == 2
