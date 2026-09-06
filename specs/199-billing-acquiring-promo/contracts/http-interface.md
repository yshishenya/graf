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

## Initial checkout recovery

- A create failure before `provider_id` redirects to the existing invoice status
  page, not to a generic or ordinary-pending result.
- `POST /billing/checkout/status/{safe_number}/continue` is owner-only,
  CSRF-protected and rate-limited. It may run only for the existing initial
  operation with no `provider_id` while its provider key is unexpired.
- Continuation uses the existing invoice, immutable snapshot and original
  idempotency key. It never creates a new invoice, operation or promo reservation.
- Failure metadata is limited to `class`, optional `http_status` and timestamp.
  Provider payload, exception text, receipt contact and credentials are absent.
- Status refresh reports success only when the reconciliation call processed the
  selected operation; `processed=0` is rendered as unchanged.
