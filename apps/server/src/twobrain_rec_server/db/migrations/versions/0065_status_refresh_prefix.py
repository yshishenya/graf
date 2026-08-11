"""Tighten the status-refresh inbox policy to an exact event-id prefix."""

from collections.abc import Sequence

from alembic import op

revision: str = "0065_status_refresh_prefix"
down_revision: str | None = "0064_status_refresh_rls"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute(
        "drop policy if exists billing_webhook_events_status_refresh_select on billing_webhook_events"
    )
    op.execute(
        "drop policy if exists billing_webhook_events_status_refresh_insert on billing_webhook_events"
    )
    op.execute(
        "create policy billing_webhook_events_status_refresh_select on billing_webhook_events "
        "for select using ("
        "rec_context_kind() = 'request' "
        "and workspace_id = rec_current_workspace_id() "
        "and left(provider_event_id, 15) = 'status_refresh_'"
        ")"
    )
    op.execute(
        "create policy billing_webhook_events_status_refresh_insert on billing_webhook_events "
        "for insert with check ("
        "rec_context_kind() = 'request' "
        "and workspace_id = rec_current_workspace_id() "
        "and left(provider_event_id, 15) = 'status_refresh_' "
        "and event_type = 'payment.succeeded' "
        "and state = 'pending_reconciliation' "
        "and metadata_json->>'source' = 'status_refresh'"
        ")"
    )


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            "drop policy if exists billing_webhook_events_status_refresh_insert on billing_webhook_events"
        )
        op.execute(
            "drop policy if exists billing_webhook_events_status_refresh_select on billing_webhook_events"
        )
