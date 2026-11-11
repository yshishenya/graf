"""Finite maintenance scan and transactional storage threshold observations."""
import sqlalchemy as sa
from alembic import op

revision = "0112_storage_notifications"
down_revision = "0111_receipt_observation_deltas"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE FUNCTION rec_storage_scan_summary_valid(v jsonb) RETURNS boolean
    LANGUAGE plpgsql IMMUTABLE STRICT AS $$
    DECLARE k text; started timestamptz; finished timestamptz;
    BEGIN
        IF jsonb_typeof(v) <> 'object' OR NOT v ?& ARRAY[
            'started_at','finished_at','attempted','observed','skipped','failed','incomplete']
            OR v - ARRAY['started_at','finished_at','attempted','observed','skipped','failed','incomplete'] <> '{}'::jsonb
        THEN RETURN false; END IF;
        FOREACH k IN ARRAY ARRAY['attempted','observed','skipped','failed'] LOOP
            IF jsonb_typeof(v->k) <> 'number' OR (v->>k) !~ '^[0-9]+$'
                OR (v->>k)::numeric > 9223372036854775807 THEN RETURN false; END IF;
        END LOOP;
        FOREACH k IN ARRAY ARRAY['started_at','finished_at'] LOOP
            IF jsonb_typeof(v->k) <> 'string' OR (v->>k) !~ '(Z|[+]00:00)$'
            THEN RETURN false; END IF;
        END LOOP;
        started := (v->>'started_at')::timestamptz;
        finished := (v->>'finished_at')::timestamptz;
        RETURN isfinite(started) AND isfinite(finished) AND finished >= started
            AND (v->>'attempted')::numeric = (v->>'observed')::numeric + (v->>'skipped')::numeric + (v->>'failed')::numeric
            AND jsonb_typeof(v->'incomplete') = 'boolean'
            AND (v->>'incomplete')::boolean = ((v->>'failed')::numeric > 0);
    EXCEPTION WHEN OTHERS THEN RETURN false;
    END $$""")
    op.create_table(
        "storage_notification_states",
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("owner_user_id", sa.Uuid()),
        sa.Column("band", sa.String(8), nullable=False),
        sa.Column("generation", sa.BigInteger(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("band IN ('normal','80','95','100')", name="storage_notice_band"),
        sa.CheckConstraint("generation >= 0", name="storage_notice_generation"),
        sa.CheckConstraint("isfinite(observed_at)", name="storage_notice_observed_at"),
    )
    op.create_table(
        "storage_notification_scan",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("cycle_started_at", sa.DateTime(timezone=True)),
        sa.Column("upper_workspace_id", sa.Uuid()),
        sa.Column("after_workspace_id", sa.Uuid()),
        *(sa.Column(k, sa.BigInteger(), nullable=False, server_default="0") for k in ("attempted", "observed", "skipped", "failed")),
        sa.Column("last_error_code", sa.String(32)),
        sa.Column("last_finished_summary", sa.JSON(none_as_null=True)),
        sa.CheckConstraint("id = 1", name="storage_scan_singleton"),
        sa.CheckConstraint(
            "(cycle_started_at IS NULL AND upper_workspace_id IS NULL AND after_workspace_id IS NULL) OR "
            "(cycle_started_at IS NOT NULL AND upper_workspace_id IS NOT NULL AND "
            "(after_workspace_id IS NULL OR after_workspace_id <= upper_workspace_id))", name="storage_scan_position",
        ),
        sa.CheckConstraint("cycle_started_at IS NULL OR isfinite(cycle_started_at)", name="storage_scan_started_at"),
        sa.CheckConstraint(
            "attempted >= 0 AND observed >= 0 AND skipped >= 0 AND failed >= 0 AND attempted = observed + skipped + failed",
            name="storage_scan_counts",
        ),
        sa.CheckConstraint(
            "last_error_code IN ('snapshot_unavailable','lock_timeout','query_timeout','database_error')", name="storage_scan_error",
        ),
        sa.CheckConstraint(
            "last_finished_summary IS NULL OR rec_storage_scan_summary_valid(last_finished_summary::jsonb)", name="storage_scan_summary",
        ),
    )
    predicate = """session_user = 'twobrain_rec_maintenance' AND current_user = 'twobrain_rec_maintenance'
        AND current_setting('row_security') = 'on' AND rec_context_kind() = 'maintenance'
        AND rec_maintenance_allowed() AND rec_setting('app.maintenance_operation') = 'billing_reconciliation'"""
    op.execute(f"""CREATE POLICY storage_published_no_archive_select ON playback_normalization_jobs
        FOR SELECT USING ({predicate} AND rec_setting('app.maintenance_feature_area') = 'billing'
        AND ready_at IS NOT NULL AND canonical_track_artifact_id IS NOT NULL
        AND EXISTS (SELECT 1 FROM upload_sessions AS storage_upload
            WHERE storage_upload.workspace_id = playback_normalization_jobs.workspace_id
            AND storage_upload.meeting_id = playback_normalization_jobs.meeting_id
            AND storage_upload.media_revision_id = playback_normalization_jobs.media_revision_id
            AND storage_upload.status = 'finalized' AND storage_upload.archive_audio = false))""")
    for table in ("storage_notification_states", "storage_notification_scan"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        billing = f"{predicate} AND rec_setting('app.maintenance_feature_area') = 'billing'"
        read = billing if table == "storage_notification_scan" else f"{predicate} AND rec_setting('app.maintenance_feature_area') IN ('billing','account')"
        op.execute(f"CREATE POLICY storage_notice_select ON {table} FOR SELECT USING ({read})")
        op.execute(f"CREATE POLICY storage_notice_insert ON {table} FOR INSERT WITH CHECK ({billing})")
        op.execute(f"CREATE POLICY storage_notice_update ON {table} FOR UPDATE USING ({billing}) WITH CHECK ({billing})")
        if table == "storage_notification_states":
            account = f"{predicate} AND rec_setting('app.maintenance_feature_area') = 'account'"
            op.execute(f"CREATE POLICY storage_notice_delete ON {table} FOR DELETE USING ({account})")
        op.execute(f"REVOKE ALL ON {table} FROM PUBLIC")
        for role in ("twobrain_rec_app", "twobrain_rec_media", "twobrain_rec_maintenance"):
            op.execute(f"DO $$ BEGIN IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{role}') THEN REVOKE ALL ON {table} FROM {role}; END IF; END $$")
        grants = "SELECT,INSERT,UPDATE,DELETE" if table == "storage_notification_states" else "SELECT,INSERT,UPDATE"
        op.execute(f"DO $$ BEGIN IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'twobrain_rec_maintenance') THEN GRANT {grants} ON {table} TO twobrain_rec_maintenance; END IF; END $$")


def downgrade():
    op.execute("LOCK TABLE storage_notification_scan, storage_notification_states IN ACCESS EXCLUSIVE MODE")
    op.execute("SET LOCAL row_security = off")
    op.execute("""DO $$ BEGIN IF EXISTS (SELECT 1 FROM storage_notification_scan)
        OR EXISTS (SELECT 1 FROM storage_notification_states)
        THEN RAISE EXCEPTION '0112 downgrade blocked: storage notification state exists'; END IF; END $$""")
    op.execute("DROP POLICY storage_published_no_archive_select ON playback_normalization_jobs")
    op.drop_table("storage_notification_scan")
    op.drop_table("storage_notification_states")
    op.execute("DROP FUNCTION rec_storage_scan_summary_valid(jsonb)")
