"""Store full meeting protocols and candidate header snapshots without rewriting history."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0086_full_meeting_protocol"
down_revision: str = "0087_merge_calendar_timezone"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # New writers supply provenance explicitly; historical rows stay unchanged.
    op.alter_column("meeting_outcome_sets", "source_kind", server_default=None)
    op.alter_column("meeting_outcome_sets", "generator_kind", server_default=None)
    op.alter_column("meeting_outcome_generation_attempts", "provider_kind", server_default=None)
    # Existing flat results are unavailable, not converted into invented protocols.
    op.add_column(
        "meeting_outcome_sets", sa.Column("protocol_json", sa.JSON(none_as_null=True), nullable=True)
    )
    op.add_column(
        "meeting_outcome_sets", sa.Column("protocol_schema_version", sa.String(64), nullable=True)
    )
    op.add_column(
        "meeting_outcome_sets",
        sa.Column("protocol_state", sa.String(32), nullable=False, server_default="unavailable"),
    )
    op.add_column(
        "meeting_outcome_generation_attempts",
        sa.Column("header_snapshot_json", sa.JSON(none_as_null=True), nullable=True),
    )


def downgrade() -> None:
    op.alter_column("meeting_outcome_sets", "source_kind", server_default="extractive_generator")
    op.alter_column("meeting_outcome_sets", "generator_kind", server_default="deterministic_extractive")
    op.alter_column("meeting_outcome_generation_attempts", "provider_kind", server_default="deterministic_extractive")
    op.drop_column("meeting_outcome_generation_attempts", "header_snapshot_json")
    op.drop_column("meeting_outcome_sets", "protocol_state")
    op.drop_column("meeting_outcome_sets", "protocol_schema_version")
    op.drop_column("meeting_outcome_sets", "protocol_json")
