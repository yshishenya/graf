# Data Model: account, subscription and billing

## Modeling rules

- `workspace_id` is the billing/tenant boundary; actor/payer references the
  existing `UserIdentity`.
- Money is integer minor units plus ISO currency (`RUB` at launch). Decimal
  bytes are integers; displayed hour equivalents never drive enforcement.
- All timestamps are UTC. Free window boundaries are derived once from
  `Europe/Moscow`; display uses the user locale/timezone with authority noted.
- Catalog, invoice, receipt lines, consent, discount and policy snapshots are
  immutable bounded schemas, not raw provider payloads.
- Provider references are opaque and environment/shop scoped. Saved payment
  method ids are encrypted and excluded from generic account/admin queries.
- Every commercial mutation has a stable logical operation, database
  uniqueness/lock and append-only audit source.
- GRAF has no refund request/case/execution entity. A refund is only a
  read-only provider observation created after merchant-backoffice action.

## Existing entities and truth reused

`Organization`, `Workspace`, `UserIdentity`, `WorkspaceMembership`,
`RegisteredDevice`, auth sessions/provider links, `WorkspaceQuotaPolicy`,
`WorkspaceUsageDaily`, `UserUsageDaily`, `AdminAuditEvent`, `TrackArtifact`,
`UploadSession`, `TemporaryUploadObject`, `DeletionFence`, `PurgeJournal` and
existing meeting deletion/lifecycle entities.

- `ensure_personal_workspace` remains the idempotent personal tenant bootstrap.
- User preferences add only bounded `locale`, IANA `timezone`, `theme` and
  optional-notification settings; verified login identity remains auth truth.
- `WorkspaceUsageDaily`/`UserUsageDaily` are display projections, never
  transactional quota admission.
- Active validated canonical playback `TrackArtifact.byte_length` and lifecycle
  status remain authoritative storage truth; no duplicate object inventory is
  introduced.

## Catalog and launch control

### `billing_plan_version`

Immutable version: stable `plan_code`, display name, cycle, `amount_minor`,
currency, typed entitlement snapshot (`quota|unlimited` per dimension), base
storage bytes, receipt/offer/fair-use policy versions, effective window and
`enabled_for_checkout`. Disabling affects new checkout only.

### `storage_capacity_sku_version`

Immutable co-termed add-on version: stable SKU, total capacity bytes
(`5_000_000_000|20_000_000_000|100_000_000_000|500_000_000_000`), cycle,
nullable approved amount, currency, COGS/value-study version, effective window
and `enabled_for_checkout=false` by default.

### `billing_launch_gate`

Versioned approval matrix for product, unit economics, finance, accounting,
legal, security, privacy, storage, QA, accessibility and provider canary.
Each gate stores a named owner, evidence class/reference, approved-at,
valid-until/revalidation timestamp, revocation state and binary blocking
outcome. Four-eyes thresholds and approver/executor role mappings are versioned
gate values. Checkout requires a complete current gate plus enabled catalog
versions; a client cannot override missing, stale or revoked approval or price.

## Account, subscription and authority

### `workspace_subscription`

One row per workspace: billing Owner, state
`free|trialing|active|cancel_at_period_end`, current plan/cycle/capacity,
trial/paid/bonus boundaries, billing anchor, default method, current recurring
authority allowed/version, renewal-resolution flag and monotonic application
version. There is no `past_due`, grace or paid suspension state.

```text
free → trialing → free
free|trialing → active
active → active                    confirmed renewal / contiguous time credit
active → cancel_at_period_end → free
cancel_at_period_end → active      resume before final cutoff
active → free                      confirmed failure or unconfirmed cutoff
```

Unknown renewal is operation truth, not paid access: at cutoff the projection
is Free and manual pay is blocked until resolution. No transition deletes
invoice/audit/data, and local Record/Stop/read/export/delete never depends on
subscription state.

### `trial_activation`

One immutable row per verified `UserIdentity` (unique): activation operation,
target personal workspace, policy version, exact `starts_at`, `ends_at =
starts_at + 7 calendar days`, verification/eligibility source and audit time.
The identity key is locked before subscription update. Signup, linked methods,
new workspaces, sessions and concurrent tabs cannot create a second row.

### `billing_consent`

Append-only evidence: workspace, actor, purpose `offer|recurring`, exact
version, accepted time and only retention-approved bounded fields. Offer and
recurring controls remain separate and unchecked by default.

### `billing_payment_authority_event`

Append-only `accepted|refused` evidence: workspace, payer/actor,
purpose/version, source
`checkout|renewal_cancel|payment_data_refusal|role_loss|account_close`,
`recorded_at`, `effective_at` and resulting monotonic authority version. The
subscription stores only current projection. An email about refund is not an
input and cannot change this ledger.

### `account_close_request`

User-scoped durable request: policy version, state
`scheduled_cooling|canceled|finalizing|completed|blocked`, exact `finalize_at`,
Temporal workflow id, re-auth class, membership/last-owner decision, future
charge veto, meeting deletion fanout, retained-finance pseudonymous subject and
session/device finalization. Launch cooling is seven days. Finalization uses
the existing deletion fence/purge journal; it does not create a second purge
system.

## Checkout, invoice and entitlement

### `billing_checkout_intent`

Mutable bounded quote before provider mutation: workspace/actor, plan/cycle,
optional capacity SKU, catalog/offer/consent versions, masked receipt contact,
base/add-on lines, candidate promo/referral discount, state
`draft|ready|locked|expired|converted|canceled`, revision and expiry. Mid-cycle
storage upgrade stores exact remaining/full billable seconds and calculated
positive pro-rata delta.

### `billing_invoice`

Immutable invoice created immediately before provider mutation: safe invoice
number, checkout revision, plan/price/tax/discount/offer/contact snapshots,
base/add-on receipt lines, amount/currency, kind
`initial|renewal|storage_upgrade`, purchased duration, planned service interval
and status. A unique logical source prevents two payable invoices for one
operation. UI timeout cannot void a pending/unknown invoice.

### `entitlement_grant`

Append-only actual access entry: workspace, source payment/time-credit/manual
correction reference, kind `paid|late_paid|time_credit|correction`, actual
`starts_at/ends_at`, plan/capacity snapshot, source authority version,
application version, optional `reversal_of_id` and bounded reason. Normal
success uses the planned interval; late success without an earlier effective
refusal starts a full term at `access_restored_at`. Late success after refusal
creates no grant and leaves Free; any later correction is a separate explicit
audited backoffice decision, not an inferred refund state.

### `storage_capacity_addon`

At most one per workspace: SKU/version, current/scheduled total capacity,
cycle/price snapshot, shared base renewal anchor, state
`payment_pending|active|change_scheduled|removal_scheduled|ended`, effective
date, source invoice and application version. It cannot exist independently of
`Личный`, stack, or own another renewal anchor.

## Payment provider observation

### `billing_operation`

Durable logical mutation: workspace, kind `initial_payment|renewal|binding`,
internal/provider idempotence keys, `provider_key_expires_at`, canonical request
hash/snapshot, actor/source, recurring-authority version snapshot, state and
timestamps. Refund mutation is not an allowed kind. Immediately before a
recurring provider call, subscription lock must still show the same allowed
authority version.

### `billing_payment_attempt`

One provider attempt for an invoice/operation: environment/shop class,
confirmed provider payment id, amount/currency, state
`checkout_pending|processing|succeeded|canceled|unknown|method_required`, safe
cancellation reason class, saved-method result and timestamps. Provider id is
unique within environment/shop; only one non-final attempt exists per invoice.

### `billing_payment_method`

Workspace + original billing Owner scoped: encrypted opaque provider reference,
encryption key id/version, safe kind/mask/expiry, state
`pending|active|revoked|expired|permission_revoked` and verified time. At most
one default active method. A successor Owner cannot inherit it.

### `billing_webhook_inbox`

Bounded signal: environment/shop, allowlisted event type, object id, dedupe
identity, received/processed timestamps and safe result/error class. Raw body
is not retained as audit. Worker must perform authoritative provider read
before state application.

### `observed_provider_refund`

Read-only reconciliation row: unique environment/shop/provider refund id,
original provider payment reference, confirmed `succeeded` status,
amount/currency, provider timestamps, observed/last-checked timestamps,
source set `webhook|poll|registry`, receipt-registration state and monotonic
applied-consistency version. It contains no request, claimant, reason,
calculation, decision, correspondence, SLA, operator action or user-visible
state. GRAF never creates this provider object.

### `billing_receipt_state`

Payment or observed-refund linked: kind, approved configuration version,
bounded provider registration/reference class, `pending|succeeded|canceled`,
requested/confirmed timestamps, last poll and error class. Money state and
fiscal state are separate. Restricted contact snapshot remains on invoice and
is omitted from general/admin projections.

## Usage and storage

### `free_usage_window`

Unique `(workspace_id, capability, window_start)`: policy version,
`included_seconds=18_000`, UTC start/end derived from the Moscow calendar
month, committed/reserved projection and reconciliation freshness. No rollover.

### `usage_reservation` / `usage_ledger_entry`

Reservation stores authoritative admission/window, media/source identity,
declared whole seconds and unique operation. Ledger entry stores accepted
non-overlapping source range, committed seconds and release/reversal linkage.
Admission checks committed + active reservations + incoming. Only unique
successful ranges commit; failed/canceled/rejected/unaccepted ranges release.
Paid/trial actual usage may be observed but cannot deny from a commercial
counter.

### `storage_reservation`

Transactionally reserves declared normalized playback bytes for a unique
upload/job with `pending|committed|released`, expiry and final
`TrackArtifact` reference. Admission locks workspace capacity and checks:

```text
sum(active validated canonical playback TrackArtifact.byte_length)
+ active reservations + incoming <= effective capacity
```

Commit requires verified active `meeting-review.m4a`; failure/cancel releases.
A small reconciled projection may cache used/reserved/freshness, but it is
rebuildable and not source truth. `meeting-transcription.wav`, legacy
`mic.wav`/`incoming.wav`, transcripts/notes, derivatives, replicas/backups,
transient/local/provider objects and logically deleted artifacts contribute
zero customer bytes.

### Existing transcription-source lifecycle extension

Current and legacy source artifacts keep role, actual bytes, transcript-import
verification, playback verification, policy version, purge deadline/evidence
and bounded recovery state in existing artifact/lifecycle/purge journal records.
Normal purge requires approved recovery policy. Accepted meeting deletion or
account-close finalization overrides that delay: access/quota ends immediately
and all primary artifacts enter mandatory purge unless a formally approved hold
exists.

### Existing transient upload/object extension

Explicit `Обработать без сохранения аудио` stores admission/job reference,
actual bytes, state, `terminal_at`, `purge_due_at ≤ terminal + 15 min` and hard
`expires_at ≤ admission + 24 h`. It never becomes playback inventory. Missed
purge is a lifecycle/privacy gap, not chargeable storage.

## Promotions and referrals

### `promotion_campaign` / `promotion_redemption`

Versioned normalized-code hash, eligibility/window/scope/discount/caps and
immutable application snapshot. Redemption state
`reserved|redeemed|released|reversed` has bounded expiry and subject uniqueness.
Invoice creation revalidates and locks counters. Raw codes do not enter logs or
analytics.

### `referral_link` / `referral_attribution`

`referral_link` is one stable opaque share link per personal inviter workspace
(`workspace_id + inviter_user_id`), with a hashed token, campaign version,
active/expired state and bounded expiry. The public canonical path is
`/r/{opaque}`; `/referral/{opaque}` remains a non-indexed compatibility alias.

`referral_attribution` is one first-touch row per invitee and link, copied with
the inviter/workspace authority and lifecycle
`issued|bound|registered|paid|pending_maturity|available|rejected|reversed`.
The link is not consumed after the first signup: concurrent new invitees get
separate attribution rows, while the invitee/user uniqueness and first-payment
source uniqueness keep rewards idempotent. Email and new OAuth registration use
the same binder; existing accounts are never re-attributed. Referral lookup
contexts expose only the bearer-token link or the current invitee's own bound
row under RLS; inviter identity is not rendered to the invitee.

### `time_credit_ledger_entry`

Append-only target-workspace service credit: 7 or 30 days, first paid
source/cycle, `maturity_at = confirmed payment + 14 calendar days`, expiry,
state `pending|available|applied|expired|reversed`, applied interval and
`reversal_of_id`. Unique first-payment source; cap 180 granted days per rolling
12 months. Active renewal shifts charge anchor; cancel-scheduled extends only
final service/add-on cutoff; Free holds credit up to 12 months. No cash value,
receipt or mutable wallet.

### `fair_use_review`

Narrow non-meter restriction: workspace, affected capability, reason class
`automated_bulk|resale|circumvention|security_abuse`, bounded evidence,
urgency/state, `starts_at`, `review_by ≤ starts_at + 24h`, appeal and decision.
Volume/IP/device alone cannot decide it. Local Record/Stop and existing
read/export/delete remain available.

## Notifications, audit and reconciliation

### `transactional_notice`

Idempotent outbox keyed by logical event/recipient/channel/template version,
with locale, safe destination class, delivery state/attempts/error and
timestamps. Marketing preference cannot disable mandatory security/financial/
receipt messages. Refund correspondence is outside this outbox.

### `billing_audit_event`

Append-only actor/workspace/action/target class/outcome/reason/source/time.
Broad admin projection omits provider ids, amounts, contacts, codes and private
payloads. Observed refund audit records only source/reference class/outcome and
projection before/after, never email/backoffice content.

### `reconciliation_gap`

Internal/provider/registry mismatch: object class, safe reference, severity,
source, detected/checked/resolved times, owner and bounded resolution class.
Gaps are internal operations truth, never a user refund status.

### `registry_import`

Audited manual CSV import: report kind `payments|refunds`, shop/environment,
Moscow report date, schema/language/config version, part/last-part, content hash,
safe filename, row identities/counts/totals, state/error. Completeness requires
every part or configured empty report for both kinds. Restricted input has
short retention after normalized evidence; SFTP automation is deferred.

## Transaction boundaries and invariants

1. Checkout submit locks intent/workspace, revalidates catalog/gates/consents/
   discount/floor, creates one immutable invoice + operation, then calls
   provider. After mutation, pending/unknown invoice and discount remain locked.
2. Provider payment state applies only after authoritative read. Redirect and
   webhook body cannot grant access. Same operation/key resolves unknown; no
   silent new payment exists after provider-key expiry.
3. Renewal planner creates one `(subscription, paid period)` operation.
   Confirmed/unconfirmed cutoff → Free and no retry. Late success grants once
   only when no earlier effective refusal; otherwise it creates an internal
   financial incident and support-email notice, not a refund case.
4. Trial uniqueness is identity-scoped; plan/subscription/usage/storage are
   workspace-scoped. Every mutation rechecks current membership/role/session.
5. Free usage commits only deduplicated accepted ranges. Storage admission
   reserves bytes then converges on existing active playback `TrackArtifact`
   truth. Logical deletion releases quota and existing purge lifecycle wins.
6. Base/add-on/cancel/renewal/time credit serialize on one workspace
   subscription; add-on never owns a second anchor.
7. Provider-confirmed refund observation is read-only and idempotent. It may
   prevent/reverse referral reward by policy; any entitlement/add-on correction
   needs separate explicit audited authority and never restores recurring
   consent. No provider refund mutation path exists.
8. Account-close scheduling vetoes future charges; finalizer reuses existing
   meeting deletion/purge and then revokes sessions/devices.
9. Every workspace/user table joins the RLS inventory. Worker/maintenance paths
   use exact existing tenant or allowlisted maintenance context.

## Retention and deletion

Account/profile/session data follows account close. Required invoice, consent,
authority, payment, observed provider refund/receipt, entitlement, audit and
reconciliation records retain the approved financial period with identity
minimized where lawful. No refund email or merchant decision evidence enters
GRAF. Playback/source/transient artifacts follow existing lifecycle and the
specification’s deletion precedence; backup expiry and YooKassa-controlled
objects remain separately disclosed.
