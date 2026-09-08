"""Bound comment author labels and editor recipient reads to an authorized meeting."""

from alembic import op

revision: str = "0091_comment_reader_projection"
down_revision: str | None = "0090_playback_comments"
branch_labels = None
depends_on = None

# Keyed invitation address proofs are verified by the application, where the
# HMAC key lives. The short-lived marker supplements (never replaces) the live
# grant, actor, workspace and meeting checks below.
MEMBERSHIP = """EXISTS (SELECT 1 FROM workspace_memberships wm
    WHERE wm.workspace_id=m.workspace_id AND wm.user_id=rec_current_user_id()
    AND wm.status='active')"""


def _grant_access(*, editor: bool) -> str:
    marker = "editor" if editor else "reader"
    edit = "AND g.can_edit" if editor else ""
    return f"""EXISTS (SELECT 1 FROM meeting_share_grants g
      WHERE g.meeting_id=m.id AND g.workspace_id=m.workspace_id
      AND g.status='active' AND (g.expires_at IS NULL OR g.expires_at>now())
      AND g.content_scope='full_meeting' {edit}
      AND ((g.audience_type='workspace' AND g.audience_id=m.workspace_id AND {MEMBERSHIP})
        OR (g.audience_type='user' AND g.audience_id=rec_current_user_id()
          AND g.grantee_user_id=rec_current_user_id()
          AND ((COALESCE(g.metadata_json->>'source','')<>'accepted_external_invitation' AND {MEMBERSHIP})
            OR (g.metadata_json->>'source'='accepted_external_invitation'
              AND COALESCE(g.metadata_json->>'recipient_address_hash','')<>''
              AND rec_setting_uuid('app.comment_{marker}_meeting_id')=m.id
              AND rec_setting_uuid('app.comment_{marker}_user_id')=rec_current_user_id())))))"""


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute(f"""
      CREATE FUNCTION rec_comment_author_labels(target_meeting uuid, target_users uuid[])
      RETURNS TABLE(user_id uuid, display_label text)
      LANGUAGE sql STABLE SECURITY DEFINER
      SET search_path=pg_catalog,public SET row_security=off AS $$
      SELECT author.id, author.display_name::text
      FROM user_identities author JOIN meetings m ON m.id=target_meeting
      JOIN user_identities actor ON actor.id=rec_current_user_id() AND actor.status='active'
      WHERE rec_context_kind()='request' AND m.workspace_id=rec_current_workspace_id()
        AND m.deleted_at IS NULL AND COALESCE(m.deletion_state,'none')='none'
        AND cardinality(target_users) BETWEEN 1 AND 5100 AND author.id=ANY(target_users)
        AND EXISTS (SELECT 1 FROM meeting_comments c WHERE c.meeting_id=m.id
          AND c.workspace_id=m.workspace_id AND c.author_user_id=author.id)
        AND (m.created_by_user_id=actor.id OR {_grant_access(editor=False)}
          OR (lower(COALESCE(m.visibility,'')) IN ('team','team_visible','workspace','workspace_visible')
            AND {MEMBERSHIP}))
      $$
    """)
    op.execute(f"""
      CREATE FUNCTION rec_comment_editor_member_visible(target_user uuid)
      RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER
      SET search_path=pg_catalog,public SET row_security=off AS $$
      SELECT EXISTS (SELECT 1 FROM meetings m
        JOIN user_identities actor ON actor.id=rec_current_user_id() AND actor.status='active'
        JOIN workspace_memberships target ON target.workspace_id=m.workspace_id
          AND target.user_id=target_user AND target.status='active'
        JOIN user_identities member ON member.id=target.user_id AND member.status='active'
        JOIN workspaces ws ON ws.id=m.workspace_id AND member.organization_id=ws.organization_id
        WHERE rec_context_kind()='request' AND m.workspace_id=rec_current_workspace_id()
          AND m.id=rec_setting_uuid('app.comment_editor_meeting_id')
          AND actor.id=rec_setting_uuid('app.comment_editor_user_id')
          AND m.deleted_at IS NULL AND COALESCE(m.deletion_state,'none')='none'
          AND ((m.created_by_user_id=actor.id AND {MEMBERSHIP})
            OR {_grant_access(editor=True)}))
      $$
    """)
    op.execute("""CREATE POLICY comment_editor_member_read ON user_identities FOR SELECT
      USING (rec_comment_editor_member_visible(id))""")
    op.execute("""CREATE POLICY comment_editor_membership_read ON workspace_memberships FOR SELECT
      USING (workspace_id=rec_current_workspace_id() AND status='active'
        AND rec_comment_editor_member_visible(user_id))""")
    op.execute("""CREATE POLICY comment_editor_verified_identity_read ON external_identities FOR SELECT
      USING (is_active AND is_verified AND email IS NOT NULL
        AND rec_comment_editor_member_visible(user_id))""")


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute("DROP POLICY comment_editor_verified_identity_read ON external_identities")
    op.execute("DROP POLICY comment_editor_membership_read ON workspace_memberships")
    op.execute("DROP POLICY comment_editor_member_read ON user_identities")
    op.execute("DROP FUNCTION rec_comment_editor_member_visible(uuid)")
    op.execute("DROP FUNCTION rec_comment_author_labels(uuid, uuid[])")
