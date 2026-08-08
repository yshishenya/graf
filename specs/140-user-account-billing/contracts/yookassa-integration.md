# Contract: YooKassa integration

## Server boundary

Only server configuration contains shop id/secret. Use the existing `httpx` stack with strict timeout, TLS defaults and explicit JSON schemas; no provider SDK or generic provider interface. Launch allows only `bank_card`. Test/prod shops, secrets, callback URLs, tables/flags and monitoring labels are separated. Real shop must prove recurring payment and zero-amount binding before enablement.

## Outbound mutations

For payment and binding, persist before network call:

- internal logical operation key;
- stable provider idempotence key;
- request kind, hash and bounded immutable snapshot;
- expected shop/environment, amount/currency and internal metadata identifiers.
- for every recurring charge, the current authority version; immediately before the HTTP mutation, lock the subscription and require the same allowed version. A committed refusal wins and prevents the call.

Retry of an unresolved operation before `provider_key_expires_at` must reuse the exact key/request. 429 honors bounded backoff; 500/timeout becomes `unknown`. At the 24-hour expiry automatic mutation stops: GET/list/reconciliation must prove object absence, an owned gap/manual closure is required, and only then may an explicit new user operation receive a new key. This applies to payment and binding. GRAF has no refund mutation or refund idempotency key.

## Hosted checkout

Create payment with positive server amount, `capture=true`, hosted confirmation, approved receipt lines and `save_payment_method=true` only after recurring consent. Base and co-termed storage add-on are separate positive receipt lines; mid-cycle upgrade line names capacity and service interval. Fiscal description names plan/cycle/purchased duration, not a final calendar interval that may shift after an unknown result. Every initial/one-attempt renewal charge passes the same builder. Return page cannot activate access.

## Webhook

- Accept only `payment.succeeded`, `payment.canceled`, optional `payment.waiting_for_capture`, `refund.succeeded` and `payment_method.active`, with bounded body size/content type.
- Terminate HTTPS on port 443/8443 with TLS 1.2+, configure current published YooKassa source-network allowlist at the trusted edge, reject spoofed forwarded addresses, rate-limit unknown objects and verify subscribed events in test/prod merchant configuration. Source filtering is defense-in-depth; mandatory authoritative GET is the authenticity/truth check.
- Store event type/object id/dedupe identity, not raw body.
- Acknowledge quickly; async worker fetches the object, validates environment/shop/id/amount/currency/metadata, then applies monotonic state.
- Unknown object, cross-environment, mismatch or regressive transition is quarantined/audited and does not reveal tenant data.

## Saved method

Store only encrypted opaque `payment_method.id` plus safe presentation. A new method becomes default after verified zero-amount binding and authoritative `payment_method.active` state (webhook or poll). If binding is unavailable in the real shop, keep the previous method and disable replacement; launch does not use ambiguous captured-small-payment/refund fallback and never collects raw card data.

## Decline and no-grace mapping

Any confirmed `payment.canceled` means the single renewal failed: no scheduled new-key retry. At exact paid cutoff GRAF projects Free and requires manual resume/new method. HTTP timeout/500 is `unknown`, reusing identical request/key or GET; after cutoff it still gives no paid grace and blocks new payment until resolved. Without an effective refusal, late success creates a separate full-duration entitlement grant from restoration time. With earlier cancel/payment-data refusal/account close, recurring authority remains off, no grant is created, one internal financial incident is recorded and the user receives the static support-email instruction. There is no product refund case or `Оставить оплаченный период` workflow. The invoice retains purchased duration/planned interval; actual interval exists only if a grant was created.

## Observing a manual merchant refund

GRAF never calls `POST /v3/refunds`, calculates a refund, builds its receipt or exposes a request/status surface. Support and manual full/partial execution live outside GRAF in the YooKassa merchant cabinet.

`refund.succeeded` is only a signal. Worker performs authenticated refund GET and validates `status=succeeded`, original payment, amount/currency and environment/shop. Periodic refund list polling with an overlap window repairs missed webhook delivery; the official daily refund registry provides the accounting backstop. A mismatch creates an internal reconciliation gap, never a user-facing status. Because public docs do not explicitly guarantee webhook delivery for every manual cabinet refund, real-shop/test-shop canary must prove full and partial manual refund observation; the design remains safe if only poll/registry discovers it.

The persisted row is a read-only observed provider refund. It may feed deterministic referral maturity/reversal and a separately authorized entitlement/add-on correction, but it never restores recurring authority or repeats a payout. Raw email, merchant decision and refund reason do not enter GRAF.

## Receipts and reconciliation

Approved configuration supplies VAT/subject/text, verified primary email snapshot and launch `payment_mode=full_payment` only after finance/legal approval; configs requiring a separate prepayment-settlement receipt block launch. Track registration, not assumed email delivery: `canceled` alerts immediately, `pending` polls and escalates at 3 days. For manual refund GRAF only observes YooKassa `receipt_registration`/receipt truth; operator selected amount/items in the merchant cabinet. Daily official CSV uses separate payments/refunds sets; audited import binds shop/environment/schema/language/config, Moscow report date, all parts/last-part, row identity/hash and requires configured empty reports to distinguish zero from missing. SFTP is deferred. Any mismatch is an owned internal gap.
