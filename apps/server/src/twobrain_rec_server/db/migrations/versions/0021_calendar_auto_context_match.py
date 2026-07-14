"""calendar auto context match

Revision ID: 0021_calendar_auto_context_match
Revises: 0020_user_scoped_recording_ids
Create Date: 2026-07-13
"""

import re
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0021_calendar_auto_context_match"
down_revision: str | None = "0020_user_scoped_recording_ids"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CALENDAR_AUTO_CONTEXT_TABLES = ("recording_calendar_match_attempts",)
CONTENT_WORKSPACE_POLICIES = CALENDAR_AUTO_CONTEXT_TABLES
POLICY_NAMES = {
    table_name: f"{table_name}_tenant_isolation"
    for table_name in CALENDAR_AUTO_CONTEXT_TABLES
}

LEGACY_CONTEXT_INDEX = "ix_recording_calendar_context_links_meeting"
CONTEXT_WORKSPACE_MEETING_UNIQUE = (
    "uq_recording_calendar_context_links_workspace_meeting"
)
CONTEXT_MATCH_ATTEMPT_UNIQUE = "uq_recording_calendar_context_links_match_attempt"
CONTEXT_MATCH_ATTEMPT_FK = "fk_recording_calendar_context_links_match_attempt"

# Keep this migration-local policy immutable. It mirrors the metadata-safe title
# rules that are active when 0021 is introduced without importing mutable app code.
UNSAFE_LEGACY_METADATA_TEXT_RE = re.compile(
    r"https?://|www\.|[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}|"
    r"token=|password|bearer\s|(?:^|[^A-Z0-9])sk-[A-Z0-9_-]{8,}|"
    r"\b(?:[A-Z0-9-]+\.)+[A-Z]{2,}/[^\s<>'\"]+",
    re.IGNORECASE,
)


def _is_postgresql() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def _q(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _create_all_policy(table_name: str) -> None:
    table = _q(table_name)
    policy = _q(POLICY_NAMES[table_name])
    predicate = (
        "((rec_context_kind() in ('request', 'worker') "
        "and workspace_id = rec_current_workspace_id()) or rec_maintenance_allowed())"
    )
    op.execute(f"alter table {table} enable row level security")
    op.execute(f"alter table {table} force row level security")
    op.execute(f"drop policy if exists {policy} on {table}")
    op.execute(
        f"create policy {policy} on {table} "
        f"using ({predicate}) with check ({predicate})"
    )


def _drop_policy(table_name: str) -> None:
    table = _q(table_name)
    policy = _q(POLICY_NAMES[table_name])
    op.execute(f"drop policy if exists {policy} on {table}")
    op.execute(f"alter table {table} no force row level security")
    op.execute(f"alter table {table} disable row level security")


def _add_meeting_title_provenance() -> None:
    with op.batch_alter_table("meetings") as batch_op:
        batch_op.add_column(
            sa.Column(
                "title_source",
                sa.String(length=64),
                nullable=False,
                server_default="legacy_unknown",
            )
        )
        batch_op.add_column(
            sa.Column("title_updated_at", sa.DateTime(timezone=True))
        )
        batch_op.add_column(
            sa.Column(
                "create_request_fingerprint_sha256",
                sa.String(length=64),
            )
        )
    op.execute(
        sa.text(
            """
            update meetings
            set title_source = case
                when title is null or trim(title) = '' then 'generic'
                else 'legacy_unknown'
            end
            """
        )
    )


def _create_match_attempts() -> None:
    op.create_table(
        "recording_calendar_match_attempts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.Uuid(),
            sa.ForeignKey("workspaces.id"),
            nullable=False,
        ),
        sa.Column(
            "owner_user_id",
            sa.Uuid(),
            sa.ForeignKey("user_identities.id"),
            nullable=False,
        ),
        sa.Column(
            "device_id",
            sa.Uuid(),
            sa.ForeignKey("registered_devices.id"),
            nullable=False,
        ),
        sa.Column("local_recording_id", sa.String(length=240), nullable=False),
        sa.Column("idempotency_key_sha256", sa.String(length=64), nullable=False),
        sa.Column("request_fingerprint_sha256", sa.String(length=64), nullable=False),
        sa.Column(
            "recording_started_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column("decision_intent", sa.String(length=64), nullable=False),
        sa.Column(
            "selected_event_snapshot_id",
            sa.Uuid(),
            sa.ForeignKey("calendar_event_snapshots.id"),
        ),
        sa.Column("attempt_state", sa.String(length=64), nullable=False),
        sa.Column("safe_reason_code", sa.String(length=120)),
        sa.Column(
            "context_confidence",
            sa.String(length=64),
            nullable=False,
            server_default="none",
        ),
        sa.Column(
            "candidate_event_ids_json",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
        sa.Column("candidate_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "matched_event_snapshot_id",
            sa.Uuid(),
            sa.ForeignKey("calendar_event_snapshots.id"),
        ),
        sa.Column("matched_event_starts_at", sa.DateTime(timezone=True)),
        sa.Column("matched_event_ends_at", sa.DateTime(timezone=True)),
        sa.Column("matched_title", sa.String(length=500)),
        sa.Column(
            "matched_title_state",
            sa.String(length=64),
            nullable=False,
            server_default="unavailable",
        ),
        sa.Column(
            "matched_roster_json",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
        sa.Column(
            "matched_roster_state",
            sa.String(length=64),
            nullable=False,
            server_default="not_available",
        ),
        sa.Column(
            "matched_roster_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("recurring_series_key_sha256", sa.String(length=64)),
        sa.Column("source_version_fingerprint_sha256", sa.String(length=64)),
        sa.Column("freshness_class", sa.String(length=64), nullable=False),
        sa.Column("matcher_version", sa.String(length=80), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "consumed_by_meeting_id",
            sa.Uuid(),
            sa.ForeignKey("meetings.id"),
        ),
        sa.Column("consumed_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "workspace_id",
            "owner_user_id",
            "local_recording_id",
            name="uq_calendar_match_attempts_workspace_owner_local",
        ),
        sa.UniqueConstraint(
            "workspace_id",
            "owner_user_id",
            "idempotency_key_sha256",
            name="uq_calendar_match_attempts_workspace_owner_idempotency",
        ),
    )
    op.create_index(
        "ix_calendar_match_attempts_owner_expiry",
        "recording_calendar_match_attempts",
        ["workspace_id", "owner_user_id", "expires_at"],
    )
    op.create_index(
        "ix_calendar_match_attempts_state_evaluated",
        "recording_calendar_match_attempts",
        ["workspace_id", "attempt_state", "evaluated_at"],
    )


def _collapse_legacy_context_rows() -> None:
    op.execute(
        sa.text(
            """
            with ranked as (
                select
                    id,
                    row_number() over (
                        partition by workspace_id, meeting_id
                        order by
                            case when unlinked_at is null then 0 else 1 end,
                            coalesce(updated_at, linked_at, created_at) desc,
                            coalesce(linked_at, created_at) desc,
                            created_at desc,
                            id desc
                    ) as row_rank
                from recording_calendar_context_links
            )
            delete from recording_calendar_context_links
            where id in (select id from ranked where row_rank > 1)
            """
        )
    )


def _extend_context_table() -> None:
    op.drop_index(
        LEGACY_CONTEXT_INDEX,
        table_name="recording_calendar_context_links",
    )
    with op.batch_alter_table("recording_calendar_context_links") as batch_op:
        batch_op.alter_column(
            "calendar_event_snapshot_id",
            existing_type=sa.Uuid(),
            nullable=True,
        )
        batch_op.add_column(sa.Column("match_attempt_id", sa.Uuid()))
        batch_op.create_foreign_key(
            CONTEXT_MATCH_ATTEMPT_FK,
            "recording_calendar_match_attempts",
            ["match_attempt_id"],
            ["id"],
        )
        batch_op.add_column(
            sa.Column(
                "context_state",
                sa.String(length=64),
                nullable=False,
                server_default="no_context",
            )
        )
        batch_op.add_column(sa.Column("safe_reason_code", sa.String(length=120)))
        batch_op.add_column(
            sa.Column(
                "decision_source",
                sa.String(length=64),
                nullable=False,
                server_default="legacy",
            )
        )
        batch_op.add_column(sa.Column("matcher_version", sa.String(length=80)))
        batch_op.add_column(sa.Column("evaluated_at", sa.DateTime(timezone=True)))
        batch_op.add_column(
            sa.Column(
                "candidate_event_ids_json",
                sa.JSON(),
                nullable=False,
                server_default=sa.text("'[]'"),
            )
        )
        batch_op.add_column(
            sa.Column(
                "candidate_count",
                sa.Integer(),
                nullable=False,
                server_default="0",
            )
        )
        batch_op.add_column(
            sa.Column("matched_event_starts_at", sa.DateTime(timezone=True))
        )
        batch_op.add_column(
            sa.Column("matched_event_ends_at", sa.DateTime(timezone=True))
        )
        batch_op.add_column(sa.Column("matched_title", sa.String(length=500)))
        batch_op.add_column(
            sa.Column(
                "matched_title_state",
                sa.String(length=64),
                nullable=False,
                server_default="unavailable",
            )
        )
        batch_op.add_column(
            sa.Column(
                "matched_roster_json",
                sa.JSON(),
                nullable=False,
                server_default=sa.text("'[]'"),
            )
        )
        batch_op.add_column(
            sa.Column(
                "matched_roster_state",
                sa.String(length=64),
                nullable=False,
                server_default="not_available",
            )
        )
        batch_op.add_column(
            sa.Column(
                "matched_roster_count",
                sa.Integer(),
                nullable=False,
                server_default="0",
            )
        )
        batch_op.add_column(
            sa.Column("recurring_series_key_sha256", sa.String(length=64))
        )
        batch_op.add_column(
            sa.Column("source_version_fingerprint_sha256", sa.String(length=64))
        )
        batch_op.create_unique_constraint(
            CONTEXT_WORKSPACE_MEETING_UNIQUE,
            ["workspace_id", "meeting_id"],
        )
        batch_op.create_unique_constraint(
            CONTEXT_MATCH_ATTEMPT_UNIQUE,
            ["match_attempt_id"],
        )

    op.create_index(
        "ix_calendar_context_state_updated",
        "recording_calendar_context_links",
        ["workspace_id", "context_state", "updated_at"],
    )
    op.create_index(
        "ix_calendar_context_series_start",
        "recording_calendar_context_links",
        [
            "workspace_id",
            "recurring_series_key_sha256",
            "matched_event_starts_at",
        ],
    )


def _backfill_context_state() -> None:
    op.execute(
        sa.text(
            """
            update recording_calendar_context_links
            set
                context_state = case
                    when exists (
                        select 1
                        from meetings
                        where meetings.id = recording_calendar_context_links.meeting_id
                          and (
                              meetings.deleted_at is not null
                              or meetings.deletion_requested_at is not null
                              or coalesce(meetings.deletion_state, 'none') <> 'none'
                          )
                    ) then 'deleted'
                    when unlinked_at is not null then 'cleared_by_user'
                    else 'legacy_linked'
                end,
                decision_source = 'legacy',
                matched_event_starts_at = case
                    when unlinked_at is null and not exists (
                        select 1
                        from meetings
                        where meetings.id = recording_calendar_context_links.meeting_id
                          and (
                              meetings.deleted_at is not null
                              or meetings.deletion_requested_at is not null
                              or coalesce(meetings.deletion_state, 'none') <> 'none'
                          )
                    ) then (
                        select starts_at
                        from calendar_event_snapshots
                        where calendar_event_snapshots.id =
                            recording_calendar_context_links.calendar_event_snapshot_id
                    )
                    else null
                end,
                matched_event_ends_at = case
                    when unlinked_at is null and not exists (
                        select 1
                        from meetings
                        where meetings.id = recording_calendar_context_links.meeting_id
                          and (
                              meetings.deleted_at is not null
                              or meetings.deletion_requested_at is not null
                              or coalesce(meetings.deletion_state, 'none') <> 'none'
                          )
                    ) then (
                        select ends_at
                        from calendar_event_snapshots
                        where calendar_event_snapshots.id =
                            recording_calendar_context_links.calendar_event_snapshot_id
                    )
                    else null
                end,
                matched_title = case
                    when unlinked_at is null and not exists (
                        select 1
                        from meetings
                        where meetings.id = recording_calendar_context_links.meeting_id
                          and (
                              meetings.deleted_at is not null
                              or meetings.deletion_requested_at is not null
                              or coalesce(meetings.deletion_state, 'none') <> 'none'
                          )
                    ) then (
                        select case
                            when safe_to_use_as_title = true
                                 and title is not null
                                 and trim(title) <> ''
                            then title
                            else null
                        end
                        from calendar_event_snapshots
                        where calendar_event_snapshots.id =
                            recording_calendar_context_links.calendar_event_snapshot_id
                    )
                    else null
                end,
                matched_title_state = case
                    when unlinked_at is not null then 'unavailable'
                    when exists (
                        select 1
                        from meetings
                        where meetings.id = recording_calendar_context_links.meeting_id
                          and (
                              meetings.deleted_at is not null
                              or meetings.deletion_requested_at is not null
                              or coalesce(meetings.deletion_state, 'none') <> 'none'
                          )
                    ) then 'unavailable'
                    when exists (
                        select 1
                        from calendar_event_snapshots
                        where calendar_event_snapshots.id =
                            recording_calendar_context_links.calendar_event_snapshot_id
                          and safe_to_use_as_title = true
                          and title is not null
                          and trim(title) <> ''
                    ) then 'available'
                    when exists (
                        select 1
                        from calendar_event_snapshots
                        where calendar_event_snapshots.id =
                            recording_calendar_context_links.calendar_event_snapshot_id
                          and safe_to_use_as_title = false
                    ) then 'policy_hidden'
                    else 'unavailable'
                end,
                context_confidence = case
                    when unlinked_at is null then context_confidence
                    else 'none'
                end,
                calendar_event_snapshot_id = case
                    when unlinked_at is null and not exists (
                        select 1
                        from meetings
                        where meetings.id = recording_calendar_context_links.meeting_id
                          and (
                              meetings.deleted_at is not null
                              or meetings.deletion_requested_at is not null
                              or coalesce(meetings.deletion_state, 'none') <> 'none'
                          )
                    ) then calendar_event_snapshot_id
                    else null
                end
            """
        )
    )
    _scrub_unsafe_legacy_matched_titles()


def _scrub_unsafe_legacy_matched_titles() -> None:
    connection = op.get_bind()
    rows = connection.execute(
        sa.text(
            """
            select id, matched_title
            from recording_calendar_context_links
            where matched_title is not null
            """
        )
    ).mappings()
    for row in rows:
        title = str(row["matched_title"])
        if not (
            UNSAFE_LEGACY_METADATA_TEXT_RE.search(title)
            or any(ord(character) < 32 or ord(character) == 127 for character in title)
        ):
            continue
        connection.execute(
            sa.text(
                """
                update recording_calendar_context_links
                set matched_title = null,
                    matched_title_state = 'policy_hidden'
                where id = :link_id
                """
            ),
            {"link_id": row["id"]},
        )


def upgrade() -> None:
    _add_meeting_title_provenance()
    _create_match_attempts()
    _collapse_legacy_context_rows()
    _extend_context_table()
    _backfill_context_state()
    if _is_postgresql():
        for table_name in CALENDAR_AUTO_CONTEXT_TABLES:
            _create_all_policy(table_name)


def _restore_legacy_context_table() -> None:
    op.drop_index(
        "ix_calendar_context_series_start",
        table_name="recording_calendar_context_links",
    )
    op.drop_index(
        "ix_calendar_context_state_updated",
        table_name="recording_calendar_context_links",
    )

    # 0020 cannot represent an authoritative state without an event FK. This is
    # intentionally lossy: 098-only no-link/clear/delete rows are discarded.
    # ponytail: take a pre-migration backup/export before downgrade; add a reversible
    # side table only if rolling back 098 becomes a supported production operation.
    op.execute(
        sa.text(
            """
            delete from recording_calendar_context_links
            where calendar_event_snapshot_id is null
            """
        )
    )

    with op.batch_alter_table("recording_calendar_context_links") as batch_op:
        batch_op.drop_constraint(CONTEXT_MATCH_ATTEMPT_UNIQUE, type_="unique")
        batch_op.drop_constraint(CONTEXT_WORKSPACE_MEETING_UNIQUE, type_="unique")
        batch_op.drop_constraint(CONTEXT_MATCH_ATTEMPT_FK, type_="foreignkey")
        batch_op.drop_column("source_version_fingerprint_sha256")
        batch_op.drop_column("recurring_series_key_sha256")
        batch_op.drop_column("matched_roster_count")
        batch_op.drop_column("matched_roster_state")
        batch_op.drop_column("matched_roster_json")
        batch_op.drop_column("matched_title_state")
        batch_op.drop_column("matched_title")
        batch_op.drop_column("matched_event_ends_at")
        batch_op.drop_column("matched_event_starts_at")
        batch_op.drop_column("candidate_count")
        batch_op.drop_column("candidate_event_ids_json")
        batch_op.drop_column("evaluated_at")
        batch_op.drop_column("matcher_version")
        batch_op.drop_column("decision_source")
        batch_op.drop_column("safe_reason_code")
        batch_op.drop_column("context_state")
        batch_op.drop_column("match_attempt_id")
        batch_op.alter_column(
            "calendar_event_snapshot_id",
            existing_type=sa.Uuid(),
            nullable=False,
        )

    op.create_index(
        LEGACY_CONTEXT_INDEX,
        "recording_calendar_context_links",
        ["workspace_id", "meeting_id"],
    )


def downgrade() -> None:
    if _is_postgresql():
        for table_name in CALENDAR_AUTO_CONTEXT_TABLES:
            _drop_policy(table_name)

    _restore_legacy_context_table()
    op.drop_index(
        "ix_calendar_match_attempts_state_evaluated",
        table_name="recording_calendar_match_attempts",
    )
    op.drop_index(
        "ix_calendar_match_attempts_owner_expiry",
        table_name="recording_calendar_match_attempts",
    )
    op.drop_table("recording_calendar_match_attempts")

    with op.batch_alter_table("meetings") as batch_op:
        batch_op.drop_column("create_request_fingerprint_sha256")
        batch_op.drop_column("title_updated_at")
        batch_op.drop_column("title_source")
