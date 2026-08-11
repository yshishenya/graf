"""Split stable referral links from per-invitee attributions."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from twobrain_rec_server.db.base import NAMING_CONVENTION

revision: str = "0058_referral_link_invitees"
down_revision: str | None = "0057_referral_workspace_scope"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "referral_links",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("inviter_user_id", sa.Uuid(), sa.ForeignKey("user_identities.id"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("campaign_version", sa.String(64), nullable=False, server_default="referral-v1"),
        sa.Column("issued_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("state", sa.String(32), nullable=False, server_default="active"),
        sa.UniqueConstraint("token_hash", name="uq_referral_links_token_hash"),
    )
    op.create_index("ix_referral_links_workspace_state", "referral_links", ["workspace_id", "state"])
    op.add_column(
        "referral_attributions",
        sa.Column("referral_link_id", sa.Uuid(), sa.ForeignKey("referral_links.id"), nullable=True),
    )
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            "insert into referral_links (id, workspace_id, inviter_user_id, token_hash, campaign_version, state) "
            "select distinct on (token_hash) id, workspace_id, inviter_user_id, token_hash, campaign_version, 'active' "
            "from referral_attributions order by token_hash, id"
        )
    else:
        op.execute(
            "insert into referral_links (id, workspace_id, inviter_user_id, token_hash, campaign_version, state) "
            "select a.id, a.workspace_id, a.inviter_user_id, a.token_hash, a.campaign_version, 'active' "
            "from referral_attributions a where a.id in "
            "(select min(id) from referral_attributions group by token_hash)"
        )
    op.execute(
        "update referral_attributions set referral_link_id = "
        "(select id from referral_links where referral_links.token_hash = referral_attributions.token_hash)"
    )
    if bind.dialect.name == "postgresql":
        op.execute("alter table referral_attributions alter column referral_link_id set not null")
        # 0044 created this constraint with ``unique=True`` and therefore
        # PostgreSQL chose ``referral_attributions_token_hash_key`` rather
        # than the ORM naming-convention name. Resolve it by definition so
        # upgrades work on both fresh and long-lived databases.
        op.execute(
            """
            do $$
            declare constraint_name text;
            begin
              select con.conname into constraint_name
                from pg_constraint con
               where con.conrelid = 'referral_attributions'::regclass
                 and con.contype = 'u'
                 and pg_get_constraintdef(con.oid) = 'UNIQUE (token_hash)'
               limit 1;
              if constraint_name is not null then
                execute format('alter table referral_attributions drop constraint %I', constraint_name);
              end if;
            end $$;
            """
        )
        op.create_unique_constraint(
            "uq_referral_attributions_link_invitee",
            "referral_attributions",
            ["referral_link_id", "invitee_user_id"],
        )
        op.create_index(
            "ix_referral_attributions_link_state",
            "referral_attributions",
            ["referral_link_id", "state"],
        )
    else:
        with op.batch_alter_table("referral_attributions", naming_convention=NAMING_CONVENTION) as batch:
            batch.drop_constraint("uq_referral_attributions_token_hash", type_="unique")
            batch.alter_column("referral_link_id", existing_type=sa.Uuid(), nullable=False)
            batch.create_unique_constraint(
                "uq_referral_attributions_link_invitee", ["referral_link_id", "invitee_user_id"]
            )
            batch.create_index("ix_referral_attributions_link_state", ["referral_link_id", "state"])
    if bind.dialect.name == "postgresql":
        op.execute("alter table referral_links enable row level security")
        op.execute("alter table referral_links force row level security")
        op.execute(
            "create policy referral_links_tenant_isolation on referral_links using ("
            "(rec_context_kind() in ('request', 'worker') and workspace_id = rec_current_workspace_id()) "
            "or (rec_context_kind() = 'auth_public' and workspace_id = rec_current_workspace_id() "
            "and inviter_user_id = rec_current_user_id()) "
            # A signup starts in the invitee's personal workspace, while the
            # stable link belongs to the inviter's workspace. The bearer token
            # is the narrow lookup key; do not require the invitee workspace to
            # match the link workspace here.
            "or (rec_context_kind() = 'auth_referral_lookup' "
            "and token_hash = rec_setting('app.referral_token_hash') and state = 'active') "
            "or rec_maintenance_allowed()) with check ("
            "(rec_context_kind() in ('request', 'worker') and workspace_id = rec_current_workspace_id()) "
            "or rec_maintenance_allowed())"
        )
        op.execute("drop policy if exists referral_attributions_tenant_isolation on referral_attributions")
        op.execute(
            "create policy referral_attributions_tenant_isolation on referral_attributions using ("
            "(rec_context_kind() in ('request', 'worker') and workspace_id = rec_current_workspace_id()) "
            "or (rec_context_kind() = 'auth_public' and workspace_id = rec_current_workspace_id() "
            "and (invitee_user_id = rec_current_user_id() or inviter_user_id = rec_current_user_id())) "
            "or (rec_context_kind() = 'auth_referral_user_lookup' "
            "and invitee_user_id = rec_current_user_id() and state = 'bound') "
            "or (rec_context_kind() = 'auth_referral_lookup' "
            "and token_hash = rec_setting('app.referral_token_hash') "
            "and (rec_setting('app.referral_link_id') is null "
            "or referral_link_id::text = rec_setting('app.referral_link_id')) "
            "and state in ('issued', 'bound') "
            "and (invitee_user_id is null or invitee_user_id = rec_current_user_id())) "
            "or rec_maintenance_allowed()) with check ("
            "(rec_context_kind() in ('request', 'worker') and workspace_id = rec_current_workspace_id()) "
            "or (rec_context_kind() = 'auth_referral_user_lookup' "
            "and invitee_user_id = rec_current_user_id() and state = 'bound') "
            "or (rec_context_kind() = 'auth_referral_lookup' "
            "and referral_link_id::text = rec_setting('app.referral_link_id') "
            "and state = 'bound' and invitee_user_id = rec_current_user_id() "
            "and workspace_id = (select workspace_id from referral_links "
            "where id = referral_attributions.referral_link_id) "
            "and inviter_user_id = (select inviter_user_id from referral_links "
            "where id = referral_attributions.referral_link_id)) "
            "or rec_maintenance_allowed())"
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("drop policy if exists referral_attributions_tenant_isolation on referral_attributions")
        op.execute("drop policy if exists referral_links_tenant_isolation on referral_links")
        op.execute("alter table referral_attributions no force row level security")
        op.execute("alter table referral_attributions disable row level security")
        op.execute("alter table referral_links no force row level security")
        op.execute("alter table referral_links disable row level security")
        op.drop_index("ix_referral_attributions_link_state", table_name="referral_attributions")
        op.drop_constraint("uq_referral_attributions_link_invitee", "referral_attributions", type_="unique")
        op.create_unique_constraint(
            "uq_referral_attributions_token_hash", "referral_attributions", ["token_hash"]
        )
        op.drop_column("referral_attributions", "referral_link_id")
    else:
        with op.batch_alter_table("referral_attributions") as batch:
            batch.drop_index("ix_referral_attributions_link_state")
            batch.drop_constraint("uq_referral_attributions_link_invitee", type_="unique")
            batch.create_unique_constraint("uq_referral_attributions_token_hash", ["token_hash"])
            batch.drop_column("referral_link_id")
    op.drop_index("ix_referral_links_workspace_state", table_name="referral_links")
    op.drop_table("referral_links")
