"""Record base and additional processing allocations without resetting usage."""

from collections.abc import Sequence

from alembic import op

revision: str = "0098_processing_quota_allocations"
down_revision: str | None = "0097_billing_access_adjustments"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    for table, columns in {
        "free_usage_windows": ("included_seconds", "committed_seconds", "reserved_seconds"),
        "usage_reservations": ("declared_seconds", "committed_seconds"),
    }.items():
        for column in columns:
            op.execute(f"alter table {table} alter column {column} type bigint")
    for table in ("free_usage_windows", "usage_reservations"):
        op.execute(f"alter table {table} add constraint uq_{table}_scope unique(id,workspace_id)")
    op.execute("""create table usage_quota_allocations (
        id uuid primary key default gen_random_uuid(), workspace_id uuid not null references workspaces(id),
        reservation_id uuid not null, window_id uuid not null,
        source_key varchar(36) not null, adjustment_id uuid,
        priority integer not null default 0 check(priority>=0),
        allocated_seconds bigint not null check(allocated_seconds>=0),
        committed_seconds bigint not null default 0 check(committed_seconds>=0 and committed_seconds<=allocated_seconds),
        foreign key(reservation_id,workspace_id) references usage_reservations(id,workspace_id),
        foreign key(window_id,workspace_id) references free_usage_windows(id,workspace_id),
        foreign key(adjustment_id,workspace_id) references billing_access_adjustments(id,workspace_id),
        check((source_key='base' and adjustment_id is null) or
            (adjustment_id is not null and source_key=adjustment_id::text)),
        unique(reservation_id,window_id,source_key)
    )""")
    op.execute("create index ix_usage_quota_source on usage_quota_allocations(workspace_id,adjustment_id)")
    op.execute("""insert into usage_quota_allocations
        (workspace_id,reservation_id,window_id,source_key,allocated_seconds,committed_seconds)
        select workspace_id,id,window_id,'base',declared_seconds,committed_seconds from usage_reservations""")
    op.execute("alter table usage_quota_allocations enable row level security")
    op.execute("alter table usage_quota_allocations force row level security")
    op.execute("revoke all on usage_quota_allocations from public")
    op.execute("""create policy quota_allocation_tenant on usage_quota_allocations using
        ((rec_context_kind() in ('request','worker') and workspace_id=rec_current_workspace_id()) or rec_maintenance_allowed())
        with check ((rec_context_kind() in ('request','worker') and workspace_id=rec_current_workspace_id()) or rec_maintenance_allowed())""")
    op.execute("""create policy system_direct_denied on usage_quota_allocations as restrictive
        to twobrain_rec_system using(false) with check(false)""")
    op.execute("""do $$ begin if exists(select 1 from pg_roles where rolname='twobrain_rec_media') then
        grant select on billing_plans,billing_plan_versions,billing_access_adjustments,billing_access_revocations
            to twobrain_rec_media;
        end if; end $$""")


def downgrade() -> None:
    op.execute("""do $$ begin if exists(select 1 from usage_quota_allocations where adjustment_id is not null) then
        raise exception 'additional quota allocations exist; destructive downgrade refused'; end if; end $$""")
    op.execute("drop table usage_quota_allocations")
    for table in ("free_usage_windows", "usage_reservations"):
        op.execute(f"alter table {table} drop constraint uq_{table}_scope")
    for table, columns in {
        "free_usage_windows": ("included_seconds", "committed_seconds", "reserved_seconds"),
        "usage_reservations": ("declared_seconds", "committed_seconds"),
    }.items():
        for column in columns:
            op.execute(f"alter table {table} alter column {column} type integer")
