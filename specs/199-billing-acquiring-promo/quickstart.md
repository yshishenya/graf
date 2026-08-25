# Quickstart: billing acquiring and promo closeout

## Preconditions

- Run from the repository root on `codex/199-billing-acquiring-promo`.
- Keep `TWOBRAIN_BILLING_CHECKOUT_ENABLED=false` and
  `TWOBRAIN_BILLING_EMERGENCY_STOP=true` during local/production preparation
  unless the Feature 140 runbook approval exists.
- Use synthetic/local database data only; never paste a real promo code, payment
  identifier, email, card data or provider response into evidence.

## Focused checks

```sh
cd apps/server
PYTHONPATH=src uv run pytest \
  tests/unit/test_promotions.py \
  tests/integration/test_promo_checkout.py \
  tests/contract/test_billing_accessibility.py \
  tests/contract/test_billing_ui.py \
  tests/unit/test_initial_checkout_recovery.py \
  tests/unit/test_promo_campaign_cli.py -q
```

Expected result: all selected tests pass; warnings do not count as provider or
launch evidence.

## Preview scenarios

1. Render `/billing/checkout` with approved month/year catalog and no code: the
   list and next-period amounts are visible, with no discount.
2. Submit `/billing/checkout/preview` with a synthetic active code: the page
   shows discount and payable amount, while no invoice/reservation/provider row
   is created.
3. Repeat with expired, wrong-cycle, exhausted, confusable and below-floor
   inputs: a safe recoverable error is rendered and the code is absent from the
   redirect URL.
4. With an eligible referral attribution, compare no-code and entered-code
   previews: only the more favorable one discount is shown and no stacking is
   applied.
5. Change the catalog/campaign after preview, then submit checkout: POST
   revalidation wins and stale state cannot create a second payment.

## Checkout recovery scenarios

1. Make synthetic YooKassa create fail before returning `provider_id`: the
   existing operation/invoice remain visible with a bounded safe error class.
2. Continue from the status page before key expiry: the same operation id,
   invoice, amount and idempotency key reach YooKassa and no second row appears.
3. Repeat after key expiry: no provider call occurs and the status says that
   automatic continuation is unavailable.
4. Request status refresh for an operation without `provider_id`: the page does
   not claim that YooKassa was checked or that state changed.

## Provisioning scenarios

```sh
cd apps/server
PYTHONPATH=src uv run python scripts/manage_promo_campaign.py create \
  --campaign-version launch-2026-08 \
  --discount-percent 10 \
  --max-redemptions 100 \
  --starts-at 2026-08-24T00:00:00Z \
  --ends-at 2026-09-30T23:59:59Z
```

The command asks for the code without echoing it and performs a dry-run. Review
the hash/metadata, then repeat with `--execute` only after operator approval.
Use `disable` with the same hidden-input flow to stop new uses. Do not put a
real code in shell history or evidence.

## Repository and release gates

```sh
git diff --check
infra/scripts/ci-local.sh --fast
infra/scripts/ci-local.sh --full
infra/scripts/cd-remote.sh --dry-run --branch master
```

The dry-run is not deployment evidence. The approved canary uses the ordinary
production application with test-shop credentials only. Production-shop
credentials remain disabled. Deployment requires a merged exact `master` SHA,
full CI and the Feature 140 `docs/runbooks/billing-launch.md` sequence.

Production migration verification and synthetic smoke are release-owned steps.
Do not run their `--execute`/`--remote` forms directly: they require the
internal release gate and shared production lock, and are invoked by
`cd-remote.sh --execute --branch master` only after merge.
