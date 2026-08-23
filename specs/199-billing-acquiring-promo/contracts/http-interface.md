# Contract: checkout promo preview

- `POST /billing/checkout/preview` is authenticated, workspace-scoped,
  CSRF-protected, owner-only and rate-limited like other billing actions.
- Input is `cycle` and optional `promo_code`. The code is normalized before any
  lookup; it is retained only in a short-lived HttpOnly checkout cookie for the
  subsequent GET.
- Success redirects to `/billing/checkout?result=promo_applied&cycle=...` and
  renders server-calculated list, discount and payable amounts.
- Invalid/expired/ineligible/exhausted/below-floor input redirects to a generic
  recoverable error state. It never reveals campaign counters, provider details
  or raw code in a URL.
- Preview does not create an invoice, `BillingOperation`, `PromotionRedemption`,
  provider request or analytics amount event. `/billing/checkout/start` remains
  the only money mutation route and revalidates everything.
