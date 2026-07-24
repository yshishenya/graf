"""Store accepted meeting-share grant token material for safe response replay."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0034_share_grant_token_replay"
down_revision: str | None = "0033_prompt_opt_maintenance"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "meeting_share_invitations",
        sa.Column("grant_token_ciphertext", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("meeting_share_invitations", "grant_token_ciphertext")
