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
infra/scripts/cd-remote.sh --dry-run --branch codex/199-billing-acquiring-promo
```

The dry-run is not production approval. Production execution, test-shop
provider mutations and checkout enablement require the Feature 140
`docs/runbooks/billing-launch.md` sequence, exact-SHA full CI and separate
merchant/finance/legal/security/QA sign-off.
