"""Prevent temporary-table shadowing in the promotion counter trigger."""

from collections.abc import Sequence

from alembic import op

revision: str = "0081_secure_promo_counter"
down_revision: str | None = "0080_promo_counter_trigger"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute(
        """
        create or replace function rec_sync_promotion_reservation_counter()
        returns trigger
        language plpgsql
        security definer
        set search_path = pg_catalog, pg_temp
        set row_security = off
        as $function$
        begin
            if tg_op = 'INSERT' and new.state = 'reserved' then
                update public.promotion_campaigns
                set reserved_count = reserved_count + 1
                where id = new.campaign_id;
            elsif tg_op = 'UPDATE' and old.state = 'reserved'
                and new.state in ('redeemed', 'released', 'expired') then
                update public.promotion_campaigns
                set reserved_count = greatest(0, reserved_count - 1),
                    redeemed_count = case
                        when new.state = 'redeemed' then redeemed_count + 1
                        else redeemed_count
                    end
                where id = new.campaign_id;
            end if;
            return new;
        end;
        $function$
        """
    )


def downgrade() -> None:
    # Security hardening remains valid at the 0080 schema revision.
    pass
