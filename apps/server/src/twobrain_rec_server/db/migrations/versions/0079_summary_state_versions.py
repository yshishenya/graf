"""Persist monotonic summary read/event versions."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0079_summary_state_versions"
down_revision: str | None = "0078_merge_summary_slots_provider_unlink"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "meeting_summary_slots",
        sa.Column("state_version", sa.BigInteger(), nullable=False, server_default=sa.text("1")),
    )
    op.create_check_constraint(
        "ck_meeting_summary_slots_state_version",
        "meeting_summary_slots",
        "state_version between 1 and 9223372036854775807",
    )
    op.add_column(
        "meeting_outcome_generation_attempts",
        sa.Column("state_version", sa.BigInteger(), nullable=False, server_default=sa.text("1")),
    )
    op.create_check_constraint(
        "ck_meeting_outcome_generation_attempts_state_version",
        "meeting_outcome_generation_attempts",
        "state_version between 1 and 9223372036854775807",
    )
    op.execute(
        """
        create or replace function rec_bump_summary_slot_state_version()
        returns trigger
        language plpgsql
        as $fn$
        begin
            if old.status is distinct from new.status
               or old.failure_code is distinct from new.failure_code
               or old.failure_reason is distinct from new.failure_reason
               or old.outcome_set_id is distinct from new.outcome_set_id
               or old.metadata_json::text is distinct from new.metadata_json::text
               or old.ended_at is distinct from new.ended_at then
                update meeting_summary_slots
                   set state_version = state_version + 1,
                       updated_at = now()
                 where workspace_id = new.workspace_id
                   and meeting_id = new.meeting_id
                   and template_key = new.template_key
                   and state_version < 9223372036854775807;
                if not found and exists (
                    select 1
                      from meeting_summary_slots
                     where workspace_id = new.workspace_id
                       and meeting_id = new.meeting_id
                       and template_key = new.template_key
                       and state_version >= 9223372036854775807
                ) then
                    raise exception 'summary_state_version_exhausted';
                end if;
            end if;
            return new;
        end
        $fn$
        """
    )
    op.execute(
        """
        create trigger trg_bump_summary_slot_state_version
        after update of status, failure_code, failure_reason, outcome_set_id,
            metadata_json, ended_at on meeting_outcome_generation_attempts
        for each row execute function rec_bump_summary_slot_state_version()
        """
    )


def downgrade() -> None:
    op.execute(
        "drop trigger if exists trg_bump_summary_slot_state_version on meeting_outcome_generation_attempts"
    )
    op.execute("drop function if exists rec_bump_summary_slot_state_version()")
    op.drop_constraint(
        "ck_meeting_outcome_generation_attempts_state_version",
        "meeting_outcome_generation_attempts",
        type_="check",
    )
    op.drop_column("meeting_outcome_generation_attempts", "state_version")
    op.drop_constraint(
        "ck_meeting_summary_slots_state_version",
        "meeting_summary_slots",
        type_="check",
    )
    op.drop_column("meeting_summary_slots", "state_version")
