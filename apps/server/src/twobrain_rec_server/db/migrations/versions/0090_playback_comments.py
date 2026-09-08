"""Version-bound discussions and explicitly granted collaboration permissions."""

import sqlalchemy as sa
from alembic import op

revision: str = "0090_playback_comments"
down_revision: str | None = "0089_merge_protocol_notify"
branch_labels = None
depends_on = None


def upgrade():
    for table in ("meeting_share_grants", "meeting_share_invitations"):
        for field in ("can_comment", "can_edit"):
            op.add_column(
                table, sa.Column(field, sa.Boolean(), nullable=False, server_default=sa.false())
            )
        op.create_check_constraint(
            table + "_comment_permissions",
            table,
            "(NOT can_edit OR can_comment) AND (content_scope = 'full_meeting' OR (NOT can_comment AND NOT can_edit))",
        )
    op.create_table(
        "meeting_comments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("meeting_id", sa.Uuid(), sa.ForeignKey("meetings.id"), nullable=False),
        sa.Column("author_user_id", sa.Uuid(), sa.ForeignKey("user_identities.id"), nullable=False),
        sa.Column(
            "media_revision_id", sa.Uuid(), sa.ForeignKey("media_revisions.id"), nullable=False
        ),
        sa.Column("processing_result_id", sa.Uuid(), sa.ForeignKey("processing_results.id")),
        sa.Column("source_segment_id", sa.Uuid()),
        sa.Column("parent_id", sa.Uuid(), sa.ForeignKey("meeting_comments.id", ondelete="CASCADE")),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("start_ms", sa.BigInteger(), nullable=False),
        sa.Column("end_ms", sa.BigInteger()),
        sa.Column("body", sa.String(10000), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("resolved", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("resolved_by", sa.Uuid(), sa.ForeignKey("user_identities.id")),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("edited_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint(
            "author_user_id", "meeting_id", "request_id", name="uq_comment_request"
        ),
        sa.CheckConstraint(
            "start_ms >= 0 AND (end_ms IS NULL OR end_ms >= start_ms)", name="comment_range"
        ),
        sa.CheckConstraint("version >= 1", name="comment_version"),
    )
    op.create_index(
        "ix_comment_meeting_created",
        "meeting_comments",
        ["workspace_id", "meeting_id", "created_at", "id"],
    )
    for table, extra, unique in (
        (
            "meeting_comment_mentions",
            [
                sa.Column("start", sa.Integer(), nullable=False),
                sa.Column("end", sa.Integer(), nullable=False),
            ],
            ["comment_id", "user_id"],
        ),
        (
            "meeting_comment_reactions",
            [sa.Column("emoji", sa.String(32), nullable=False)],
            ["comment_id", "user_id", "emoji"],
        ),
    ):
        op.create_table(
            table,
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
            sa.Column("meeting_id", sa.Uuid(), sa.ForeignKey("meetings.id"), nullable=False),
            sa.Column(
                "comment_id",
                sa.Uuid(),
                sa.ForeignKey("meeting_comments.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("user_id", sa.Uuid(), sa.ForeignKey("user_identities.id"), nullable=False),
            *extra,
            sa.UniqueConstraint(
                *unique, name="uq_comment_mention" if "mentions" in table else "uq_comment_reaction"
            ),
        )
    op.drop_constraint("notification_family", "server_notifications", type_="check")
    op.drop_constraint("notification_source_family", "server_notifications", type_="check")
    op.create_check_constraint(
        "notification_family", "server_notifications", "family IN ('result','share','comment')"
    )
    op.create_check_constraint(
        "notification_source_family",
        "server_notifications",
        "(family='comment' AND kind='mentioned') OR (family='share' AND kind='shared') OR (family='result' AND source_id=meeting_id AND kind IN ('transcript_ready','result_ready','summary_failed','processing_failed','no_speech'))",
    )
    if op.get_bind().dialect.name == "postgresql":
        for table in ("meeting_comments", "meeting_comment_mentions", "meeting_comment_reactions"):
            op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
            op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
            policy = "(rec_context_kind()='request' AND workspace_id=rec_current_workspace_id()) OR rec_maintenance_allowed()"
            op.execute(
                f"CREATE POLICY {table}_tenant ON {table} USING ({policy}) WITH CHECK ({policy})"
            )
        # Only actual author-owned mentions can produce comment cards. This does
        # not widen the existing result/share producer or allow recipient forgery.
        mention = """family='comment' AND workspace_id=rec_current_workspace_id() AND EXISTS (
          SELECT 1 FROM meeting_comment_mentions mm JOIN meeting_comments c ON c.id=mm.comment_id
          WHERE mm.comment_id=server_notifications.source_id AND mm.user_id=server_notifications.recipient_id
          AND mm.workspace_id=server_notifications.workspace_id AND mm.meeting_id=server_notifications.meeting_id
          AND c.workspace_id=mm.workspace_id AND c.meeting_id=mm.meeting_id
          AND c.author_user_id=rec_current_user_id())"""
        # Historical cards must remain purgeable after an edited comment has
        # removed its mention row. Only producer policies require that row.
        historical = """family='comment' AND workspace_id=rec_current_workspace_id() AND EXISTS (
          SELECT 1 FROM meeting_comments c WHERE c.id=server_notifications.source_id
          AND c.workspace_id=server_notifications.workspace_id AND c.meeting_id=server_notifications.meeting_id
          AND c.author_user_id=rec_current_user_id())"""
        moderator = historical.replace(
            "c.author_user_id=rec_current_user_id()",
            """(c.author_user_id=rec_current_user_id() OR EXISTS (
          SELECT 1 FROM meeting_comments root WHERE root.id=c.parent_id
          AND root.workspace_id=c.workspace_id AND root.meeting_id=c.meeting_id
          AND root.author_user_id=rec_current_user_id()) OR EXISTS (
          SELECT 1 FROM meeting_share_grants g WHERE g.workspace_id=c.workspace_id AND g.meeting_id=c.meeting_id
          AND g.status='active' AND (g.expires_at IS NULL OR g.expires_at>now()) AND g.content_scope='full_meeting'
          AND g.can_edit AND ((g.audience_type='user' AND g.audience_id=rec_current_user_id())
          OR (g.audience_type='workspace' AND g.audience_id=c.workspace_id AND EXISTS (
            SELECT 1 FROM workspace_memberships wm WHERE wm.workspace_id=c.workspace_id
            AND wm.user_id=rec_current_user_id() AND wm.status='active')))))""",
        )
        for action in ("SELECT", "INSERT", "UPDATE", "DELETE"):
            predicate = mention if action in ("INSERT", "UPDATE") else moderator
            clause = f"WITH CHECK ({mention})" if action == "INSERT" else f"USING ({predicate})"
            if action == "UPDATE":
                clause += f" WITH CHECK ({mention})"
            op.execute(
                f"CREATE POLICY comment_notice_{action.lower()} ON server_notifications FOR {action} {clause}"
            )

        # A bounded identity projection lets comments rebuild recipient proof
        # across organizations. Raw addresses never enter the HTTP projection.
        op.execute("""
          CREATE FUNCTION rec_comment_recipient_identity(target_meeting uuid, target_user uuid)
          RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER
          SET search_path = pg_catalog, public SET row_security = off AS $$
          SELECT jsonb_build_object('display_label', u.display_name,
            'workspace_membership_is_active', EXISTS (SELECT 1 FROM workspace_memberships wm
              WHERE wm.workspace_id=m.workspace_id AND wm.user_id=u.id AND wm.status='active'),
            'verified_emails', COALESCE((SELECT jsonb_agg(e.email) FROM external_identities e
              WHERE e.user_id=u.id AND e.is_active AND e.is_verified AND e.email IS NOT NULL), '[]'::jsonb))
          FROM user_identities u JOIN meetings m ON m.id=target_meeting
          WHERE u.id=target_user AND u.status='active'
            AND rec_context_kind()='request' AND m.workspace_id=rec_current_workspace_id()
            AND m.deleted_at IS NULL AND COALESCE(m.deletion_state, 'none')='none'
            AND (m.created_by_user_id=rec_current_user_id() OR EXISTS (
              SELECT 1 FROM meeting_share_grants actor WHERE actor.meeting_id=m.id AND actor.workspace_id=m.workspace_id
              AND actor.status='active' AND (actor.expires_at IS NULL OR actor.expires_at>now())
              AND actor.content_scope='full_meeting' AND actor.can_comment
              AND ((actor.audience_type='user' AND actor.audience_id=rec_current_user_id())
                OR (actor.audience_type='workspace' AND actor.audience_id=m.workspace_id AND EXISTS (
                  SELECT 1 FROM workspace_memberships wm WHERE wm.workspace_id=m.workspace_id
                  AND wm.user_id=rec_current_user_id() AND wm.status='active')))))
            AND (u.id=m.created_by_user_id OR EXISTS (SELECT 1 FROM workspace_memberships wm
              WHERE wm.workspace_id=m.workspace_id AND wm.user_id=u.id AND wm.status='active')
              OR EXISTS (SELECT 1 FROM meeting_share_grants target WHERE target.meeting_id=m.id
              AND target.workspace_id=m.workspace_id AND target.audience_type='user' AND target.audience_id=u.id
              AND target.status='active' AND (target.expires_at IS NULL OR target.expires_at>now())
              AND target.content_scope='full_meeting'
              AND target.metadata_json->>'source'='accepted_external_invitation'))
          $$
        """)
        shared = """rec_context_kind()='request' AND family='share' AND kind='shared'
          AND workspace_id=rec_current_workspace_id() AND EXISTS (
            SELECT 1 FROM meeting_share_grants target WHERE target.id=server_notifications.source_id
            AND target.workspace_id=server_notifications.workspace_id
            AND target.meeting_id=server_notifications.meeting_id
            AND target.audience_type='user' AND target.audience_id=server_notifications.recipient_id
            AND target.status='active' AND (target.expires_at IS NULL OR target.expires_at>now())
          ) AND EXISTS (
            SELECT 1 FROM meeting_share_grants editor WHERE editor.workspace_id=server_notifications.workspace_id
            AND editor.meeting_id=server_notifications.meeting_id AND editor.status='active'
            AND (editor.expires_at IS NULL OR editor.expires_at>now()) AND editor.content_scope='full_meeting'
            AND editor.can_edit AND ((editor.audience_type='user' AND editor.audience_id=rec_current_user_id())
              OR (editor.audience_type='workspace' AND editor.audience_id=server_notifications.workspace_id
                AND EXISTS (SELECT 1 FROM workspace_memberships wm WHERE wm.workspace_id=editor.workspace_id
                  AND wm.user_id=rec_current_user_id() AND wm.status='active'))))"""
        for action in ("SELECT", "INSERT", "UPDATE"):
            clause = f"WITH CHECK ({shared})" if action == "INSERT" else f"USING ({shared})"
            if action == "UPDATE":
                clause += f" WITH CHECK ({shared})"
            op.execute(
                f"CREATE POLICY editor_share_notice_{action.lower()} ON server_notifications FOR {action} {clause}"
            )


def downgrade():
    op.execute("DELETE FROM server_notifications WHERE family='comment'")
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP FUNCTION rec_comment_recipient_identity(uuid, uuid)")
        for action in ("select", "insert", "update"):
            op.execute(f"DROP POLICY editor_share_notice_{action} ON server_notifications")
        for action in ("select", "insert", "update", "delete"):
            op.execute(f"DROP POLICY comment_notice_{action} ON server_notifications")
    op.drop_constraint("notification_family", "server_notifications", type_="check")
    op.drop_constraint("notification_source_family", "server_notifications", type_="check")
    op.create_check_constraint(
        "notification_family", "server_notifications", "family IN ('result','share')"
    )
    op.create_check_constraint(
        "notification_source_family",
        "server_notifications",
        "(family='share' AND kind='shared') OR (family='result' AND source_id=meeting_id AND kind IN ('transcript_ready','result_ready','summary_failed','processing_failed','no_speech'))",
    )
    for table in ("meeting_comment_reactions", "meeting_comment_mentions", "meeting_comments"):
        op.drop_table(table)
    for table in ("meeting_share_grants", "meeting_share_invitations"):
        op.drop_constraint(table + "_comment_permissions", table, type_="check")
        op.drop_column(table, "can_edit")
        op.drop_column(table, "can_comment")
