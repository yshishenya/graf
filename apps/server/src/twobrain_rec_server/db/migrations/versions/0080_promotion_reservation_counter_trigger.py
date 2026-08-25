"""Keep promotion reservation counters inside the trusted RLS boundary."""

from collections.abc import Sequence

from alembic import op

revision: str = "0080_promo_counter_trigger"
down_revision: str | None = "0079_remove_billing_launch_gates"
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
        set search_path = pg_catalog, public
        set row_security = off
        as $function$
        begin
            if tg_op = 'INSERT' and new.state = 'reserved' then
                update promotion_campaigns
                set reserved_count = reserved_count + 1
                where id = new.campaign_id;
            elsif tg_op = 'UPDATE' and old.state = 'reserved'
                and new.state in ('redeemed', 'released', 'expired') then
                update promotion_campaigns
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
    op.execute(
        """
        create trigger promotion_redemptions_sync_campaign_counter
        after insert or update of state on promotion_redemptions
        for each row execute function rec_sync_promotion_reservation_counter()
        """
    )


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute(
        "drop trigger if exists promotion_redemptions_sync_campaign_counter on promotion_redemptions"
    )
    op.execute("drop function if exists rec_sync_promotion_reservation_counter()")
