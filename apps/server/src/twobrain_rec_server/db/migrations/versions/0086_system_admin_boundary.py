"""Isolate system identities and admit only authenticated meeting metadata reads.

Content and domain writes deliberately receive no grants. Their audited command
paths are introduced by later Feature 254 tasks, before opening those privileges.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0086_system_admin_boundary"
down_revision: str | None = "0085_merge_summary_mediascribe"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "system_control"
SYSTEM = "twobrain_rec_system"
AUTHORITY = "twobrain_rec_system_authority"
METADATA_COLUMNS = (
    "id",
    "workspace_id",
    "created_by_user_id",
    "device_id",
    "started_at",
    "ended_at",
    "duration_seconds",
    "status",
    "processing_status",
    "deletion_state",
    "deletion_epoch",
    "created_at",
    "updated_at",
)


def upgrade() -> None:
    # Roles are cluster-wide and may already exist when another database is
    # migrated. Do not change an existing login or credential during migrations.
    for role in (SYSTEM, AUTHORITY):
        op.execute(f"""
            do $$ begin
                if not exists (select 1 from pg_roles where rolname = '{role}') then
                    create role {role} nologin nosuperuser nocreatedb nocreaterole
                        noinherit noreplication nobypassrls;
                end if;
                if exists (select 1 from pg_roles where rolname = '{role}' and
                    (rolsuper or rolcreatedb or rolcreaterole or rolinherit or
                     rolreplication or rolbypassrls)) or exists (
                    select 1 from pg_auth_members m join pg_roles r
                    on r.oid = m.roleid or r.oid = m.member where r.rolname = '{role}'
                ) then raise exception 'unsafe system database role'; end if;
            end $$
        """)
    op.execute(f"alter role {SYSTEM} set row_security = on")
    op.execute(f"alter role {AUTHORITY} nologin")
    op.execute(f"create schema {SCHEMA}")
    op.execute(f"revoke all on schema {SCHEMA} from public")
    op.execute(
        f"alter default privileges in schema {SCHEMA} revoke execute on functions from public"
    )
    op.create_table(
        "principals",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("normalized_email", sa.String(320), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(512)),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("auth_version", sa.Integer(), nullable=False),
        sa.Column(
            "linked_user_id",
            sa.Uuid(),
            sa.ForeignKey("public.user_identities.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            "status in ('invited','active','recovery_pending','blocked','revoked')", name="status"
        ),
        sa.CheckConstraint("auth_version > 0", name="auth_version"),
        schema=SCHEMA,
    )
    op.create_table(
        "role_assignments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "principal_id", sa.Uuid(), sa.ForeignKey(f"{SCHEMA}.principals.id"), nullable=False
        ),
        sa.Column("role", sa.String(24), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("granted_by", sa.Uuid(), sa.ForeignKey(f"{SCHEMA}.principals.id")),
        sa.Column("reason", sa.String(1000)),
        sa.CheckConstraint(
            "role in ('superadmin','system_admin','support','billing_manager','analyst','auditor')",
            name="role",
        ),
        sa.CheckConstraint("expires_at is null or expires_at > starts_at", name="interval"),
        sa.CheckConstraint("version > 0", name="version"),
        schema=SCHEMA,
    )
    op.create_index(
        "uq_system_role_assignment_current",
        "role_assignments",
        ["principal_id"],
        unique=True,
        schema=SCHEMA,
        postgresql_where=sa.text("revoked_at is null"),
    )
    op.create_table(
        "sessions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "principal_id", sa.Uuid(), sa.ForeignKey(f"{SCHEMA}.principals.id"), nullable=False
        ),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("auth_version", sa.Integer(), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_interaction_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("absolute_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("mfa_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("auth_version > 0", name="auth_version"),
        sa.CheckConstraint(
            "absolute_expires_at > issued_at and "
            "absolute_expires_at <= issued_at + interval '12 hours'",
            name="lifetime",
        ),
        sa.CheckConstraint("last_interaction_at >= issued_at", name="interaction"),
        sa.CheckConstraint("token_hash ~ '^[0-9a-f]{64}$'", name="token_hash"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_system_sessions_principal_revoked",
        "sessions",
        ["principal_id", "revoked_at"],
        schema=SCHEMA,
    )
    for table in ("principals", "role_assignments", "sessions"):
        op.execute(f"alter table {SCHEMA}.{table} enable row level security")
        op.execute(f"alter table {SCHEMA}.{table} force row level security")
        op.execute(
            f"create policy authority_read on {SCHEMA}.{table} "
            f"for select to {AUTHORITY} using (true)"
        )
        op.execute(f"revoke all on {SCHEMA}.{table} from public")
    op.execute(f"grant usage on schema {SCHEMA} to {SYSTEM}, {AUTHORITY}")
    op.execute(f"grant select (id, status, auth_version) on {SCHEMA}.principals to {AUTHORITY}")
    op.execute(f"grant select on {SCHEMA}.sessions, {SCHEMA}.role_assignments to {AUTHORITY}")
    # Only a hash-bound, live session and current role can authorize this read.
    # Text comparisons deliberately fail closed for malformed UUID GUCs.
    op.execute(f"""
        create function {SCHEMA}.meeting_metadata_allowed() returns boolean
        language sql stable security definer set search_path = pg_catalog
        as $$
            select session_user = '{SYSTEM}'
              and current_setting('app.context_kind', true) = 'system'
              and current_setting('app.system_permission', true) = 'meetings.metadata'
              and exists (
                select 1 from {SCHEMA}.sessions s
                join {SCHEMA}.principals p on p.id = s.principal_id
                join {SCHEMA}.role_assignments r on r.principal_id = p.id
                where s.id::text = current_setting('app.system_session_id', true)
                  and p.id::text = current_setting('app.system_actor_id', true)
                  and s.token_hash = current_setting('app.system_session_token_hash', true)
                  and p.status = 'active' and p.auth_version = s.auth_version
                  and s.revoked_at is null and s.issued_at <= statement_timestamp()
                  and s.absolute_expires_at > statement_timestamp()
                  and s.last_interaction_at > statement_timestamp() - interval '30 minutes'
                  and s.last_interaction_at <= statement_timestamp()
                  and s.mfa_at <= statement_timestamp()
                  and r.revoked_at is null and r.starts_at <= statement_timestamp()
                  and (r.expires_at is null or r.expires_at > statement_timestamp())
                  and r.role in ('superadmin', 'system_admin', 'support')
              )
        $$
    """)
    op.execute(f"revoke all on function {SCHEMA}.meeting_metadata_allowed() from public")
    # PostgreSQL requires the new function owner to have CREATE during transfer;
    # it is removed in the same migration transaction.
    op.execute(f"grant create on schema {SCHEMA} to {AUTHORITY}")
    op.execute(f"alter function {SCHEMA}.meeting_metadata_allowed() owner to {AUTHORITY}")
    op.execute(f"revoke create on schema {SCHEMA} from {AUTHORITY}")
    op.execute(f"grant execute on function {SCHEMA}.meeting_metadata_allowed() to {SYSTEM}")
    op.execute(f"grant usage on schema public to {SYSTEM}")
    op.execute(f"grant select ({', '.join(METADATA_COLUMNS)}) on public.meetings to {SYSTEM}")
    # Existing TO PUBLIC permissive policies can never override this mandatory
    # gate, even when a system login forges a request/worker/bootstrap context.
    op.execute(
        f"create policy system_metadata_gate on public.meetings "
        f"as restrictive for select to {SYSTEM} "
        f"using ((select {SCHEMA}.meeting_metadata_allowed()))"
    )
    op.execute(
        f"create policy system_metadata_read on public.meetings "
        f"for select to {SYSTEM} "
        f"using ((select {SCHEMA}.meeting_metadata_allowed()))"
    )
    # No current system DML grants; deny even if a later operator grants them.
    for action in ("insert", "update", "delete"):
        clause = "with check (false)" if action == "insert" else "using (false)"
        if action == "update":
            clause += " with check (false)"
        op.execute(
            f"create policy system_{action}_closed on public.meetings "
            f"as restrictive for {action} to {SYSTEM} {clause}"
        )


def downgrade() -> None:
    # Losing the system actor would destroy attribution. Empty prelaunch schema
    # may roll back; any principal requires an explicit operator migration.
    op.execute(f"""
        do $$ begin
            if exists (select 1 from {SCHEMA}.principals) then
                raise exception 'system principals exist; destructive downgrade refused';
            end if;
        end $$
    """)
    for policy in (
        "system_metadata_gate",
        "system_metadata_read",
        "system_insert_closed",
        "system_update_closed",
        "system_delete_closed",
    ):
        op.execute(f"drop policy {policy} on public.meetings")
    op.execute(f"revoke select ({', '.join(METADATA_COLUMNS)}) on public.meetings from {SYSTEM}")
    op.execute(f"drop function {SCHEMA}.meeting_metadata_allowed()")
    for table in ("sessions", "role_assignments", "principals"):
        op.drop_table(table, schema=SCHEMA)
    op.execute(f"drop schema {SCHEMA}")
    # Roles are cluster-wide; another database can still use them.
