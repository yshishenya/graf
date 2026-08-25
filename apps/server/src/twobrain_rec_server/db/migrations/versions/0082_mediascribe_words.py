"""Retain validated MediaScribe v0.5.3 diarization words."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0082_mediascribe_words"
down_revision: str | None = "0081_secure_promo_counter"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("diarization_segments", sa.Column("words_json", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("diarization_segments", "words_json")
