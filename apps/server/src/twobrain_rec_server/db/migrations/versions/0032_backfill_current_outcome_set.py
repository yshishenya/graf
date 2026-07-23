"""Backfill the accepted outcome pointer for legacy extractive summaries."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0032_outcome_pointer"
down_revision: str | None = "0031_recording_workflows"
branch_labels: str | None = None
depends_on: str | None = None

BACKFILL_SQL = """
WITH ranked AS (
    SELECT
        outcome.id AS outcome_set_id,
        outcome.workspace_id,
        outcome.meeting_id,
        ROW_NUMBER() OVER (
            PARTITION BY outcome.workspace_id, outcome.meeting_id
            ORDER BY
                result.imported_at DESC NULLS LAST,
                result.created_at DESC NULLS LAST,
                outcome.generated_at DESC NULLS LAST,
                outcome.created_at DESC NULLS LAST,
                outcome.id DESC
        ) AS rank
    FROM meeting_outcome_sets AS outcome
    JOIN meetings AS meeting
      ON meeting.id = outcome.meeting_id
     AND meeting.workspace_id = outcome.workspace_id
    JOIN processing_results AS result
      ON result.id = outcome.processing_result_id
     AND result.meeting_id = outcome.meeting_id
     AND result.workspace_id = outcome.workspace_id
    WHERE meeting.current_outcome_set_id IS NULL
      AND meeting.deleted_at IS NULL
      AND COALESCE(meeting.deletion_state, 'none') = 'none'
      AND outcome.generator_version = 'outcomes-extractive-v1'
      AND outcome.lifecycle_state = 'active'
      AND outcome.status IN ('available', 'partial')
      AND outcome.revision_state IS NULL
),
selected AS (
    SELECT outcome_set_id, workspace_id, meeting_id
    FROM ranked
    WHERE rank = 1
),
pointed AS (
    UPDATE meetings AS meeting
       SET current_outcome_set_id = selected.outcome_set_id
     FROM selected
     WHERE meeting.id = selected.meeting_id
       AND meeting.workspace_id = selected.workspace_id
       AND meeting.current_outcome_set_id IS NULL
       AND meeting.deleted_at IS NULL
       AND COALESCE(meeting.deletion_state, 'none') = 'none'
    RETURNING
        meeting.workspace_id,
        meeting.id AS meeting_id,
        meeting.current_outcome_set_id
)
UPDATE meeting_outcome_sets AS outcome
   SET revision_state = 'accepted',
       accepted_at = COALESCE(
           outcome.accepted_at,
           outcome.generated_at,
           outcome.created_at,
           CURRENT_TIMESTAMP
       )
  FROM pointed
 WHERE outcome.id = pointed.current_outcome_set_id
   AND outcome.workspace_id = pointed.workspace_id
   AND outcome.meeting_id = pointed.meeting_id
"""


def upgrade() -> None:
    op.execute(sa.text(BACKFILL_SQL))


def downgrade() -> None:
    # The backfilled pointer becomes normal product state after deployment.
    # Clearing it later could discard a legitimate user acceptance.
    pass
