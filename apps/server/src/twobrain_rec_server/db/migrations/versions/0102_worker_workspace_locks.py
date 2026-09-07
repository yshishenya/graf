"""Allow workers to read and lock their workspace without changing its fields."""

from alembic import op

revision: str = "0102_worker_workspace_locks"
down_revision: str | None = "0101_share_recipient_lookup"
branch_labels: str | None = None
depends_on: str | None = None

WORKER_SCOPE = """session_user in ('twobrain_rec_app','twobrain_rec_media')
    and rec_context_kind()='worker' and id=rec_current_workspace_id()"""


def upgrade() -> None:
    op.execute(f"create policy worker_workspace_read on workspaces for select using ({WORKER_SCOPE})")
    # SELECT FOR UPDATE needs an UPDATE policy, but an actual UPDATE must fail.
    op.execute(f"""create policy worker_workspace_lock on workspaces for update
        using ({WORKER_SCOPE}) with check (false)""")
    op.execute("""do $$ begin
        if exists(select 1 from pg_roles where rolname='twobrain_rec_media') then
          grant update(id) on workspaces to twobrain_rec_media;
        end if;
        end $$""")


def downgrade() -> None:
    op.execute("drop policy worker_workspace_lock on workspaces")
    op.execute("drop policy worker_workspace_read on workspaces")
    op.execute("""do $$ begin
        if exists(select 1 from pg_roles where rolname='twobrain_rec_media') then
          revoke update(id) on workspaces from twobrain_rec_media;
        end if;
        end $$""")
