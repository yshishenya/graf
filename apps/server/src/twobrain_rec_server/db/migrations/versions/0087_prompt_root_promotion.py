"""Operator-only immutable root admission and retained call authority."""

import sqlalchemy as sa
from alembic import op

revision = "0087_prompt_root_promotion"
down_revision = "0086_full_meeting_protocol"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("generation_calls", sa.Column("execution_authority_json", sa.JSON(none_as_null=True)))
    op.add_column("generation_calls", sa.Column("execution_authority_hash", sa.String(64)))
    op.add_column("generation_calls", sa.Column("predecessor_call_id", sa.Uuid()))
    op.add_column("generation_calls", sa.Column("predecessor_result_hash", sa.String(64)))
    op.add_column("generation_calls", sa.Column("header_snapshot_hash", sa.String(64)))
    op.create_table(
        "prompt_root_promotions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("project_id", sa.String(240), nullable=False),
        sa.Column("root_name", sa.String(240), nullable=False),
        sa.Column("operation_kind", sa.String(32), nullable=False),
        sa.Column("expected_source_version", sa.Integer(), nullable=False),
        sa.Column("root_export_json", sa.JSON(), nullable=False),
        sa.Column("root_export_hash", sa.String(64), nullable=False),
        sa.Column("activation_json", sa.JSON(), nullable=False),
        sa.Column("activation_hash", sa.String(64), nullable=False),
        sa.Column("qualification_json", sa.JSON(), nullable=False),
        sa.Column("qualification_hash", sa.String(64), nullable=False),
        sa.Column("event_json", sa.JSON(none_as_null=True)),
        sa.Column("event_hash", sa.String(64)),
        sa.Column("state", sa.String(32), nullable=False, server_default="prepared"),
        sa.Column("failure_code", sa.String(120)),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("state in ('prepared', 'reconciliation_required', 'succeeded', 'cancelled')", name="state"),
        sa.CheckConstraint("operation_kind in ('initial_activation', 'promotion')", name="operation_kind"),
        sa.CheckConstraint("expected_source_version > 0", name="expected_version"),
        sa.CheckConstraint("not is_current or state = 'succeeded'", name="current_success"),
        sa.CheckConstraint(
            "(state = 'succeeded' and event_json is not null and event_hash is not null) "
            "or (state <> 'succeeded' and event_json is null and event_hash is null)",
            name="event_success",
        ),
    )
    op.create_index("uq_prompt_root_current", "prompt_root_promotions", ["project_id", "root_name"],
                    unique=True, postgresql_where=sa.text("is_current"))
    op.create_index("uq_prompt_root_unfinished", "prompt_root_promotions", ["project_id", "root_name"],
                    unique=True, postgresql_where=sa.text("state in ('prepared', 'reconciliation_required')"))
    op.execute("alter table prompt_root_promotions enable row level security")
    op.execute("alter table prompt_root_promotions force row level security")
    op.execute("create policy prompt_root_read on prompt_root_promotions for select using (true)")
    op.execute("""
        create policy prompt_root_operator on prompt_root_promotions for all
            using (session_user = 'twobrain_rec_maintenance' and rec_maintenance_allowed()
                and rec_setting('app.maintenance_operation') = 'prompt_optimization')
            with check (session_user = 'twobrain_rec_maintenance' and rec_maintenance_allowed()
                and rec_setting('app.maintenance_operation') = 'prompt_optimization');
    """)
    op.execute("""
        do $$ begin
            if exists(select 1 from pg_roles where rolname = 'twobrain_rec_app') then
                revoke all on prompt_root_promotions from twobrain_rec_app;
                grant select on prompt_root_promotions to twobrain_rec_app;
            end if;
            if exists(select 1 from pg_roles where rolname = 'twobrain_rec_maintenance') then
                grant select, insert, update on prompt_root_promotions to twobrain_rec_maintenance;
            end if;
        end $$;
    """)
    op.execute("""
        create function rec_prompt_root_immutable() returns trigger language plpgsql as $$
        begin
            if tg_op = 'DELETE' then
                raise exception 'prompt_root_immutable';
            end if;
            if (to_jsonb(new) - array['event_json','event_hash','state','failure_code','is_current'])
                is distinct from
                (to_jsonb(old) - array['event_json','event_hash','state','failure_code','is_current']) then
                raise exception 'prompt_root_immutable';
            end if;
            if old.event_json is not null and (
                new.event_json::jsonb is distinct from old.event_json::jsonb
                or new.event_hash is distinct from old.event_hash or new.state <> old.state
                or new.failure_code is distinct from old.failure_code) then
                raise exception 'prompt_root_event_immutable';
            end if;
            if old.state = 'cancelled' and to_jsonb(new) is distinct from to_jsonb(old) then
                raise exception 'prompt_root_terminal';
            end if;
            if old.state = 'reconciliation_required' and new.state not in ('reconciliation_required','cancelled') then
                raise exception 'prompt_root_reconciliation_required';
            end if;
            return new;
        end $$;
    """)
    op.execute("""
        create trigger prompt_root_immutable before update or delete on prompt_root_promotions
            for each row execute function rec_prompt_root_immutable();
    """)
    op.execute("""
        create function rec_generation_authority_immutable() returns trigger language plpgsql as $$
        begin
            if new.execution_authority_json::jsonb is distinct from old.execution_authority_json::jsonb
                or new.execution_authority_hash is distinct from old.execution_authority_hash
                or new.predecessor_call_id is distinct from old.predecessor_call_id
                or new.predecessor_result_hash is distinct from old.predecessor_result_hash
                or new.header_snapshot_hash is distinct from old.header_snapshot_hash then
                raise exception 'generation_authority_immutable';
            end if;
            return new;
        end $$;
    """)
    op.execute("""
        create trigger generation_authority_immutable before update on generation_calls
            for each row execute function rec_generation_authority_immutable();
    """)


def downgrade():
    op.execute("drop trigger generation_authority_immutable on generation_calls")
    op.execute("drop function rec_generation_authority_immutable()")
    op.drop_table("prompt_root_promotions")
    op.execute("drop function rec_prompt_root_immutable()")
    op.drop_column("generation_calls", "execution_authority_hash")
    op.drop_column("generation_calls", "execution_authority_json")
    op.drop_column("generation_calls", "predecessor_call_id")
    op.drop_column("generation_calls", "predecessor_result_hash")
    op.drop_column("generation_calls", "header_snapshot_hash")
