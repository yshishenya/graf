# Contract: HTTP interface

All workspace-mutating browser routes require authenticated session, CSRF, current workspace role and server state revalidation. JSON endpoints use the same dependency chain. There is no post-role-loss refund claim route: refund correspondence is external email and does not authorize workspace access or product mutation. Error bodies contain a safe request reference and bounded reason class, never provider details.

## Browser routes

`GET /account/profile|security|notifications|referrals|close` render account pages. Matching `POST` routes mutate only the named action. Billing routes are under `/account/workspaces/{workspace_slug}/billing`; slug lookup is tenant-scoped and cannot expose existence cross-tenant.

`POST /account/workspaces/switch` accepts an internal workspace reference, rechecks active membership within the same auth Organization, rotates owner session and CSRF/tenant context, and redirects to a canonical safe route. Cross-organization, inactive, stale and replayed switches fail closed without object disclosure.

Key mutations:

- `POST .../trial/start` — atomically claim once-per-verified-`UserIdentity` eligibility and start exactly seven days on the current personal `Free` workspace; creates no invoice/payment method/recurring consent. Duplicate/concurrent requests return the same resulting state or bounded `trial_already_used`.
- `POST .../checkout` — create/reuse logical checkout and redirect hosted confirmation; fails closed with `checkout_disabled` or `catalog_not_approved` when the required versioned launch gate is incomplete.
- `GET .../checkout/{operation_ref}` — safe status page; authenticated internal ref only.
- `POST .../checkout/{operation_ref}/refresh` — authoritative status read, rate-limited.
- `POST .../payment-method` — begin hosted verified replacement.
- `POST .../renewal/cancel` and `/renewal/resume` — exact preview token + explicit confirmation through the shared atomic recurring-authority service; cancel persists refusal before any provider mutation.
- `POST .../storage/preview|upgrade|schedule-downgrade|schedule-removal` — one co-termed capacity; only an approved/enabled priced upgrade may create positive pro-rata checkout; an absent price or approval returns `catalog_not_approved` without a quote/invoice.
- `POST .../promotions/preview|apply|remove` — server-calculated result; apply is bound to invoice creation.
- Invoice detail renders a static configured refund/support email, safe invoice number and `mailto:` action. It creates no request/case route, accepts no refund fields and performs no provider mutation. Future-charge refusal remains the separate `renewal/cancel` operation.
- `POST /account/close|close/cancel` — schedule/cancel durable close request; last-owner-with-members routes to ownership transfer. Sole-member personal finalizer fans out existing meeting deletion and removes workspace-scoped non-financial state after terminal lifecycle accounting.

POST success follows POST/Redirect/GET. A stale preview/version returns `409 state_changed` with a fresh summary and no charge. Existing in-flight operation returns `303` to its status page. Permission loss returns generic `404` or `403` according to existing tenant policy without revealing object existence.

## Provider endpoint

`POST /api/v1/billing/providers/yookassa/webhook/{environment}` accepts only provider traffic, bounded size/type/event/object id, writes the durable dedupe inbox and returns quickly. A five-minute Temporal reconciliation activity performs the authenticated provider GET/list and projection outside the request path. It never renders tenant data or performs entitlement activation from the body.

`payment_method.active` is accepted as an observation signal only; recurring authority is granted from an authoritative payment GET with a saved bank-card method. Replacement remains disabled until the real-shop zero-amount binding gate is proven.

## Read API for desktop

`GET /api/v1/auth/me` reuses a safe selected-workspace summary: plan/state, trial/paid/bonus dates, renewal-resolution class, unlimited core-use flag, coarse storage used/capacity and handoff route. Desktop opens every monetary route in the system browser.

## Internal operations boundary

No public financial admin UI. Audited internal commands/runbooks may perform safe lookup, authoritative payment/refund/receipt reconciliation, official registry import, stop/resume GRAF-originated charges, storage repair and time-credit correction. They expose no refund intake/decision/amount/execution command and never call the YooKassa refund mutation. Manual refund execution exists only in the external YooKassa merchant cabinet. Emergency stop blocks checkout/binding/charge while preserving cancellation, history, static support instruction, Record/Stop, deletion and export.
