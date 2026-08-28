"""Backfill the direct workflow lineage of revision-scoped processing results.

Revision ID: 0083_result_workflow_lineage
Revises: 0082_mediascribe_words
Create Date: 2026-08-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0083_result_workflow_lineage"
down_revision: str | None = "0082_mediascribe_words"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            WITH candidates AS (
                SELECT
                    result.id AS result_id,
                    job.processing_workflow_id,
                    ROW_NUMBER() OVER (
                        PARTITION BY
                            result.workspace_id,
                            job.processing_workflow_id,
                            result.source_result_hash
                        ORDER BY
                            (accepted_outcome.id IS NOT NULL) DESC,
                            result.result_version DESC,
                            result.imported_at DESC NULLS LAST,
                            result.created_at DESC,
                            result.id DESC
                    ) AS rank
                  FROM processing_results AS result
                  JOIN meetings AS meeting
                    ON meeting.id = result.meeting_id
                   AND meeting.workspace_id = result.workspace_id
                  JOIN mediascribe_jobs AS job
                    ON result.mediascribe_job_id = job.id
                   AND result.workspace_id = job.workspace_id
                   AND result.meeting_id = job.meeting_id
                   AND result.media_revision_id = job.media_revision_id
                  JOIN processing_workflows AS workflow
                    ON workflow.id = job.processing_workflow_id
                   AND workflow.workspace_id = job.workspace_id
                   AND workflow.meeting_id = job.meeting_id
                   AND workflow.media_revision_id = job.media_revision_id
                   AND workflow.purpose = 'transcription'
                  LEFT JOIN meeting_outcome_sets AS accepted_outcome
                    ON accepted_outcome.id = meeting.current_outcome_set_id
                   AND accepted_outcome.workspace_id = result.workspace_id
                   AND accepted_outcome.meeting_id = result.meeting_id
                   AND accepted_outcome.processing_result_id = result.id
                   AND accepted_outcome.revision_state = 'accepted'
                   AND accepted_outcome.lifecycle_state = 'active'
                 WHERE result.processing_workflow_id IS NULL
                   AND result.media_revision_id IS NOT NULL
                   AND (
                       result.source_result_hash IS NULL
                       OR NOT EXISTS (
                           SELECT 1
                             FROM processing_results AS existing
                            WHERE existing.workspace_id = result.workspace_id
                              AND existing.processing_workflow_id = job.processing_workflow_id
                              AND existing.source_result_hash = result.source_result_hash
                       )
                   )
            )
            UPDATE processing_results AS result
               SET processing_workflow_id = candidate.processing_workflow_id
              FROM candidates AS candidate
             WHERE result.id = candidate.result_id
               AND (result.source_result_hash IS NULL OR candidate.rank = 1)
            """
        )
    )


def downgrade() -> None:
    # A proven workflow relation is normal product data after the upgrade.
    pass
