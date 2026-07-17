"""keep active playback normalization attempts out of cleanup

Revision ID: 0026_active_cleanup
Revises: 0025_provider_link_cleanup
Create Date: 2026-07-17
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0026_active_cleanup"
down_revision: str | None = "0025_provider_link_cleanup"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _replace_cleanup_page_function(*, skip_active_attempts: bool) -> None:
    active_attempt_clause = (
        """
              and not (
                  cleanup_job.state in ('running', 'publishing')
                  and cleanup_job.lease_expires_at > current_timestamp
              )
        """
        if skip_active_attempts
        else ""
    )
    op.execute(
        f"""
        create or replace function rec_playback_normalization_cleanup_page(
            p_page_size integer
        )
        returns table (
            attempt_id uuid,
            job_id uuid,
            organization_id uuid,
            workspace_id uuid,
            user_id uuid,
            device_id uuid,
            attempt_state varchar
        )
        language sql
        stable
        security definer
        set search_path = pg_catalog, public
        set row_security = off
        as $$
            select
                cleanup_attempt.id,
                cleanup_job.id,
                cleanup_job.organization_id,
                cleanup_job.workspace_id,
                cleanup_job.requested_by_user_id,
                cleanup_job.source_device_id,
                cleanup_attempt.state
            from playback_normalization_attempts as cleanup_attempt
            join playback_normalization_jobs as cleanup_job
              on cleanup_job.id = cleanup_attempt.job_id
            where session_user = 'twobrain_rec_media'
              and rec_setting('app.context_kind') = 'maintenance'
              and rec_setting('app.maintenance_operation') =
                  'playback_normalization_dispatch'
              and rec_setting('app.maintenance_actor') is not null
              and rec_setting('app.maintenance_reason') is not null
              and rec_setting('app.maintenance_feature_area') =
                  'playback_normalization'
              and cleanup_attempt.state in (
                  'local_preparing', 'uploaded', 'cleanup_pending', 'purged'
              )
              and (
                  cleanup_attempt.state != 'purged'
                  or cleanup_attempt.cleaned_at is null
              )
              {active_attempt_clause}
            order by cleanup_attempt.updated_at asc nulls first, cleanup_attempt.id
            limit least(greatest(p_page_size, 1), 25)
        $$;
        """
    )
    op.execute(
        "revoke all privileges on function "
        "rec_playback_normalization_cleanup_page(integer) from public"
    )


def upgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        _replace_cleanup_page_function(skip_active_attempts=True)


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        _replace_cleanup_page_function(skip_active_attempts=False)
