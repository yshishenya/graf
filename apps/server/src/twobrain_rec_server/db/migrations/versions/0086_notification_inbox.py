"""Add the quiet web inbox and optimistic notification preference version."""
import sqlalchemy as sa
from alembic import op

revision = '0086_notification_inbox'
down_revision = '0085_merge_summary_mediascribe'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('server_notifications',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('recipient_id', sa.Uuid(), sa.ForeignKey('user_identities.id'), nullable=False),
        sa.Column('workspace_id', sa.Uuid(), sa.ForeignKey('workspaces.id'), nullable=False),
        sa.Column('meeting_id', sa.Uuid(), sa.ForeignKey('meetings.id', ondelete='CASCADE'), nullable=False),
        sa.Column('family', sa.String(16), nullable=False),
        sa.Column('source_id', sa.Uuid(), nullable=False),
        sa.Column('source_revision', sa.String(160), nullable=False),
        sa.Column('kind', sa.String(32), nullable=False),
        sa.Column('revision', sa.Integer(), nullable=False),
        sa.Column('read_revision', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('requires_action', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('resolved_at', sa.DateTime(timezone=True)),
        sa.Column('expires_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('recipient_id','workspace_id','family','source_id', name='uq_server_notification_source'),
        sa.CheckConstraint('revision >= 1 AND read_revision >= 0 AND read_revision <= revision', name='notification_revision'),
        sa.CheckConstraint("family IN ('result', 'share')", name='notification_family'),
        sa.CheckConstraint("(family = 'share' AND kind = 'shared') OR (family = 'result' AND source_id = meeting_id AND kind IN ('transcript_ready', 'result_ready', 'summary_failed', 'processing_failed', 'no_speech'))", name='notification_source_family'),
    )
    op.create_index('ix_server_notification_recipient', 'server_notifications', ['recipient_id','created_at','id'])
    op.add_column('billing_notification_preferences', sa.Column('version', sa.Integer(), nullable=False, server_default='0'))
    if op.get_bind().dialect.name == 'postgresql':
        op.execute('ALTER TABLE server_notifications ENABLE ROW LEVEL SECURITY')
        op.execute('ALTER TABLE server_notifications FORCE ROW LEVEL SECURITY')
        producer = """(workspace_id = rec_current_workspace_id() AND
            (rec_context_kind() = 'worker' OR EXISTS (
                SELECT 1 FROM meetings WHERE meetings.id = server_notifications.meeting_id
                AND meetings.workspace_id = server_notifications.workspace_id
                AND meetings.created_by_user_id = rec_current_user_id()))) OR rec_maintenance_allowed()"""
        reader = f"recipient_id = rec_current_user_id() OR ({producer})"
        op.execute(f"CREATE POLICY server_notification_read ON server_notifications FOR SELECT USING ({reader})")
        op.execute(f"CREATE POLICY server_notification_insert ON server_notifications FOR INSERT WITH CHECK ({producer})")
        op.execute(f"CREATE POLICY server_notification_update ON server_notifications FOR UPDATE USING ({reader}) WITH CHECK ({reader})")
        op.execute(f"CREATE POLICY server_notification_delete ON server_notifications FOR DELETE USING ({producer})")


def downgrade():
    op.drop_column('billing_notification_preferences', 'version')
    op.drop_table('server_notifications')
