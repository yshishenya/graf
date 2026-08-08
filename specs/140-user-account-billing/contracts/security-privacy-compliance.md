# Contract: security, privacy and compliance

## Trust boundaries

- Browser/desktop are untrusted clients; amounts, roles, discounts and entitlement are recalculated server-side.
- YooKassa is an external processor; only opaque references and bounded confirmed fields enter the ledger.
- Worker/system access is narrowly scoped and audited; public/admin queries remain tenant filtered and RLS-backed.

## Controls

- Session, CSRF, current Owner membership and workspace scope on every financial mutation; re-authentication for account close and sign-out-all. Refund email is external correspondence and is not a product mutation or authorization path.
- Postgres unique/check constraints, row locks and monotonic transition guards for duplicate/race protection.
- Secrets only in approved server secret injection; never client bundle, DB row, spec, log, trace, evidence or support reference.
- Payment method reference uses a generic versioned Fernet envelope with current+previous key ring, key id, dual-read and audited re-encryption; legacy calendar payloads remain readable through a bounded v1 path. List/view serializers omit secrets by default.
- Raw webhook body, promo code/referral-link token, email receipt contact, IP/device/payment risk signals have purpose/retention/access rules and never enter broad audit/analytics.
- Financial route class disables Yandex/session replay and masks PostHog. Langfuse receives no financial content.
- Trial activation, Free usage window/ranges, playback capacity/reservation projection, current/legacy transcription-source lifecycle, observed provider-refund reconciliation and time-credit tables join the RLS/lifecycle inventory with same/cross-tenant/worker fail-closed tests. Active `TrackArtifact` remains playback-byte source truth; no duplicate inventory table is added.

## Abuse controls

Rate-limit login-sensitive, checkout/add-on creation, status refresh and promo/referral actions by privacy-approved keys. Unlimited paid use remains subject to disclosed technical/fair-use controls, but no hidden paid quota. A fair-use restriction requires a named capability/reason, bounded evidence, `review_by` within 24 hours and appeal; volume/IP/device alone cannot decide it. Referral correlation is a review signal, never sole rejection evidence. GRAF exposes no refund input, execution endpoint or operator command; support email cannot mutate ledger.

## Compliance launch record

Named owners approve merchant entity, recurring/binding and electronic payment-data refusal, 54-ФЗ/VAT, offer/consent, no-grace copy, unlimited/fair-use, base capacities, transcription-source retention/recovery policy, add-on COGS/value/prices/pro-rata, static refund-email/backoffice boundary, time credit, receipt contact, retention/account-close/privacy. External support/backoffice owns eligibility, calculation, communication and mandatory deadlines; GRAF neither models nor promises them. Product, unit-economics, finance, accounting and legal approvals are explicit versioned gates; exact versions are published before enablement.

## Incident response

Stop-all-charges disables new checkout, binding and scheduled charges while preserving read-only history, static support/refund instruction, electronic payment-data refusal and cancellation. External merchant-backoffice refunds are outside this product switch. Rotate secret and isolate environment on credential exposure; reconcile all potentially affected objects. Evidence contains timestamps/counts/status classes only. Meeting content and real account/payment identifiers are prohibited.
