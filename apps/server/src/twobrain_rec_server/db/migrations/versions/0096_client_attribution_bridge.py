"""Keep the attribution bridge identifier on the client acquisition attribute.

The campaign of a visit reaches the customer record through the handoff link of
the download page, and the identifier of that bridge is what ties the record
back to the visit it came from. The value is an opaque identifier issued by the
product itself: it is not a click identifier and not an identifier of a person,
and it is stored under the same retention category as the campaign it belongs to
(FR-015, FR-022).
"""

import sqlalchemy as sa
from alembic import op

revision: str = "0096_client_attribution_bridge"
down_revision: str | None = "0095_public_attribution"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "client_acquisition_attributes",
        sa.Column("graf_attribution_id", sa.String(80)),
    )
    # The shape is a storage rule, not a convention of the writer: only the
    # prefix plus an opaque suffix may ever be stored here.
    op.create_check_constraint(
        "acquisition_attribution_bridge",
        "client_acquisition_attributes",
        "graf_attribution_id IS NULL OR graf_attribution_id ~ '^graf_attr_[0-9a-z_-]{8,64}$'",
    )


def downgrade() -> None:
    op.drop_constraint(
        "acquisition_attribution_bridge",
        "client_acquisition_attributes",
        type_="check",
    )
    op.drop_column("client_acquisition_attributes", "graf_attribution_id")
