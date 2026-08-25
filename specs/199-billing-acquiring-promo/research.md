# Research: billing acquiring and promo closeout

## Existing implementation audit

- Feature 140 already has `PromotionCampaign` and `PromotionRedemption`, with
  raw-code hashing, Unicode normalization, expiry/scope/cap/floor checks, one
  winner between promo/referral, invoice snapshot and authoritative release.
- `POST /billing/checkout/start` reads the approved catalog, locks a campaign,
  creates one reservation and only then calls YooKassa. Provider/configuration
  errors leave the operation recoverable/blocked.
- `/billing/checkout` currently renders the promo field and generic recoverable
  error, but not the calculated discount or payable total. This is the functional
  gap addressed here.
- Campaign rows are global and write-protected by maintenance RLS. Existing
  maintenance context and `billing_reconciliation` operation are reused for
  controlled provisioning; no public operator route is appropriate.
- Current runbook keeps `TWOBRAIN_BILLING_CHECKOUT_ENABLED=false` until test-shop
  canary, receipt/VAT mapping and webhook delivery. This slice removes only the
  obsolete runtime approval registry; it does not weaken the setting or stop.

## Decisions

1. Preview is POST/Redirect/GET with a short-lived HttpOnly cookie, so raw code
   never enters query strings or analytics and the page works without JavaScript.
2. Preview uses the same catalog and eligibility helpers as checkout, but never
   locks a row or increments `reserved_count`.
3. Operator provisioning is dry-run by default and accepts the code via hidden
   prompt/stdin. Output contains only the code hash and metadata.
4. Existing invoice/checkout revalidation remains authoritative if a campaign or
   catalog changes after preview.
5. The internal launch-gate registry duplicated operational approval and blocked
   the exact deployed SHA when no rows existed. It is removed; provider and
   operational evidence remains outside the checkout trust boundary.

## Deferred external evidence

Test/production YooKassa delivery, fiscalization, merchant/legal/finance/security/
QA approval, moderated usability and product-market evidence remain open Feature
140 tasks T078-T080, T083-T085 and T087. Local code/tests cannot close them.
