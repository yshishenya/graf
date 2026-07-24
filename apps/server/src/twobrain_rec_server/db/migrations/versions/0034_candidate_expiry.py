"""add bounded candidate expiry and idempotency indexes

Revision ID: 0034_candidate_expiry
Revises: 0033_deletion_purge
Create Date: 2026-07-24
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0034_candidate_expiry"
down_revision: str | None = "0033_deletion_purge"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Legacy rows normally have NULL keys, but a partial rollout can leave
    # duplicate non-NULL keys. Repair only the later rows before adding the
    # database invariant; the UUID suffix keeps the rewrite deterministic.
    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            """
            with ranked as (
                select id,
                       row_number() over (
                           partition by workspace_id, idempotency_key
                           order by created_at nulls first, id
                       ) as row_number
                  from meeting_outcome_generation_attempts
                 where idempotency_key is not null
            )
            update meeting_outcome_generation_attempts as attempt
               set idempotency_key = left('legacy:' || attempt.id::text, 240)
              from ranked
             where ranked.id = attempt.id
               and ranked.row_number > 1
            """
        )
    op.create_unique_constraint(
        "uq_generation_attempt_workspace_idempotency_key",
        "meeting_outcome_generation_attempts",
        ["workspace_id", "idempotency_key"],
    )
    op.create_index(
        "ix_generation_attempts_expiry",
        "meeting_outcome_generation_attempts",
        ["workspace_id", "status", "expires_at"],
    )
    op.create_index(
        "ix_generation_attempts_source_hash",
        "meeting_outcome_generation_attempts",
        ["workspace_id", "meeting_id", "source_result_hash"],
    )


def downgrade() -> None:
    op.drop_index("ix_generation_attempts_source_hash", table_name="meeting_outcome_generation_attempts")
    op.drop_index("ix_generation_attempts_expiry", table_name="meeting_outcome_generation_attempts")
    op.drop_constraint(
        "uq_generation_attempt_workspace_idempotency_key",
        "meeting_outcome_generation_attempts",
        type_="unique",
    )
