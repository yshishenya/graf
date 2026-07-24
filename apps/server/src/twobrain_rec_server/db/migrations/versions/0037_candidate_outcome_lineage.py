"""keep expired candidate outcome sets immutable across retries

Revision ID: 0037_candidate_outcome_lineage
Revises: 0036_generator_provenance
Create Date: 2026-07-24
"""

from collections.abc import Sequence
from hashlib import sha256

import sqlalchemy as sa
from alembic import op

revision: str = "0037_candidate_lineage"
down_revision: str | None = "0036_generator_provenance"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "uq_meeting_outcome_sets_current_generator_config",
        "meeting_outcome_sets",
        type_="unique",
    )
    op.add_column(
        "meeting_outcome_sets",
        sa.Column("candidate_id", sa.Uuid(), nullable=True),
    )
    # Candidate rows are the new idempotent unit. Keep the legacy NULL-key
    # semantics in a separate partial index so pre-existing immutable baseline
    # rows that legitimately repeat a NULL revision/config never make this
    # migration fail. Candidate rows still get strict null-normalized keys.
    op.execute(
        sa.text(
            """
            CREATE UNIQUE INDEX uq_meeting_outcome_sets_candidate_generator_config
              ON meeting_outcome_sets (
                workspace_id,
                meeting_id,
                COALESCE(media_revision_id, '00000000-0000-0000-0000-000000000000'::uuid),
                processing_result_id,
                generator_version,
                COALESCE(generator_config_hash, ''),
                candidate_id
              )
              WHERE candidate_id IS NOT NULL
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE UNIQUE INDEX uq_meeting_outcome_sets_legacy_generator_config
              ON meeting_outcome_sets (
                workspace_id,
                meeting_id,
                media_revision_id,
                processing_result_id,
                generator_version,
                generator_config_hash
              )
              WHERE candidate_id IS NULL
            """
        )
    )
    connection = op.get_bind()
    legacy_results = connection.execute(
        sa.text(
            "SELECT id FROM processing_results "
            "WHERE source_result_hash IS NULL"
        )
    ).mappings()
    for row in legacy_results:
        result_id = str(row["id"])
        connection.execute(
            sa.text(
                "UPDATE processing_results SET source_result_hash = :source_hash "
                "WHERE id = :result_id AND source_result_hash IS NULL"
            ),
            {
                "source_hash": sha256(
                    f"legacy-processing-result:{result_id}".encode()
                ).hexdigest(),
                "result_id": row["id"],
            },
        )
    connection.execute(
        sa.text(
            "UPDATE meeting_outcome_sets AS outcome "
            "SET source_result_hash = result.source_result_hash "
            "FROM processing_results AS result "
            "WHERE outcome.processing_result_id = result.id "
            "AND outcome.source_result_hash IS NULL "
            "AND result.source_result_hash IS NOT NULL"
        )
    )


def downgrade() -> None:
    connection = op.get_bind()
    candidate_count = connection.execute(
        sa.text(
            "SELECT count(*) FROM meeting_outcome_sets "
            "WHERE candidate_id IS NOT NULL"
        )
    ).scalar_one()
    duplicate_count = connection.execute(
        sa.text(
            "SELECT count(*) FROM ("
            "SELECT workspace_id, meeting_id, media_revision_id, "
            "processing_result_id, generator_version, generator_config_hash "
            "FROM meeting_outcome_sets "
            "GROUP BY workspace_id, meeting_id, media_revision_id, "
            "processing_result_id, generator_version, generator_config_hash "
            "HAVING count(*) > 1"
            ") duplicates"
        )
    ).scalar_one()
    if candidate_count or duplicate_count:
        raise RuntimeError(
            "0037 downgrade requires candidate rows to be archived and "
            "generator-config duplicates to be deduplicated first"
        )
    op.drop_index(
        "uq_meeting_outcome_sets_candidate_generator_config",
        table_name="meeting_outcome_sets",
    )
    op.drop_index(
        "uq_meeting_outcome_sets_legacy_generator_config",
        table_name="meeting_outcome_sets",
    )
    op.drop_column("meeting_outcome_sets", "candidate_id")
    op.create_unique_constraint(
        "uq_meeting_outcome_sets_current_generator_config",
        "meeting_outcome_sets",
        [
            "workspace_id",
            "meeting_id",
            "media_revision_id",
            "processing_result_id",
            "generator_version",
            "generator_config_hash",
        ],
    )
