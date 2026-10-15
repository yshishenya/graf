"""Move the fixed summary and delivery graph with a proof-bound account merge."""

from alembic import op

revision: str = "0104_summary_share_scope_cascade"
down_revision: str | None = "0103_summary_autosend"
branch_labels = None
depends_on = None

SCOPED_REFERENCES = (
    (
        "fk_published_summary_meeting_scope",
        "published_meeting_summaries",
        "meetings",
        ["meeting_id", "workspace_id"],
        ["id", "workspace_id"],
    ),
    (
        "fk_summary_batch_publication_scope",
        "summary_delivery_batches",
        "published_meeting_summaries",
        ["published_summary_id", "workspace_id", "meeting_id"],
        ["id", "workspace_id", "meeting_id"],
    ),
    (
        "fk_summary_recipient_batch_scope",
        "summary_recipient_deliveries",
        "summary_delivery_batches",
        ["batch_id", "workspace_id"],
        ["id", "workspace_id"],
    ),
    *(
        (
            constraint,
            table,
            "published_meeting_summaries",
            ["published_summary_id", "workspace_id", "meeting_id"],
            ["id", "workspace_id", "meeting_id"],
        )
        for table, constraint in (
            ("meeting_share_grants", "fk_grant_publication_scope"),
            ("meeting_share_invitations", "fk_invitation_publication_scope"),
        )
    ),
)


def _replace_scope_references(onupdate):
    for name, table, parent, columns, parent_columns in SCOPED_REFERENCES:
        op.drop_constraint(name, table, type_="foreignkey")
        op.create_foreign_key(name, table, parent, columns, parent_columns, onupdate=onupdate)


def upgrade():
    _replace_scope_references("CASCADE")


def downgrade():
    _replace_scope_references(None)
