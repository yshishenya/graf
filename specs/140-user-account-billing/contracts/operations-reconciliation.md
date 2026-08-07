# Contract: operations, reconciliation and launch

## Scheduled operations

- Renewal planner creates exactly one operation per subscription period and skips cancel/stop/ineligible rows under lock; confirmed/unconfirmed outcome at cutoff projects Free without a new charge attempt.
- Unknown-resolution poller reuses/reads the same operation; late success restores a full term once only without an earlier effective refusal. Late-after-refusal stays Free, records one internal financial incident and sends the safe support-email instruction; it creates no refund case. Final failure enables manual resume.
- Webhook worker and stuck-object poller perform authoritative GET and the same transition function.
- Storage reservation expiry/TrackArtifact projection reconciliation, transient-media terminal hook plus 15-minute/24-hour purge deadlines, fair-use 24-hour review deadline, co-termed add-on application, promo cleanup, 7/30-day credit maturity/expiry/application and notices use deterministic keys and restart-safe workflow registration.
- Playback quota reconciliation proves `used = sum(active validated canonical meeting-review.m4a TrackArtifact.byte_length)` and excludes source WAV/replica/backup/transient bytes. Source-WAV reconciliation proves every controlled track has lifecycle state; normal purge occurs only after transcript import, active playback verification and approved policy/deadline, while accepted deletion/account close uses mandatory purge precedence. Missing normal-retention gates retain recovery data and alert instead of deleting.
- Account-close workflow persists exact `finalize_at`, waits the versioned seven-day cooling timer, accepts cancel signal, rechecks ownership, fans out existing deletion activities, waits terminal/declared-limit states and finalizes idempotently across worker restart.
- Daily reconciliation compares GRAF ledger, YooKassa API/list and audited official CSV sets. Payments/refunds are separate required report kinds bound to shop/environment/schema/language/config; completeness requires every declared part or an expected empty report for each kind/date. Replacement, missing, empty, duplicate and malformed states create owned gaps. SFTP is deferred.
- Stop-all-charges blocks GRAF-originated checkout, binding and scheduled charge. It preserves cancellation/payment-data refusal, history, static support/refund instruction, local Record/Stop, deletion and export. Manual merchant-cabinet refunds remain external to GRAF.

## Observability

Metrics: create/success/cancel by safe reason, unknown age, webhook lag/dedupe, authoritative-read failure, immediate-Free count, duplicate prevented, storage used/reserved/capacity/gap classes, transient purge deadline/missed-SLA privacy incident, fair-use review deadline/appeal state, add-on/time-credit jobs, observed provider-refund/receipt reconciliation, notice and registry gaps. No refund request/SLA/status metric exists. Alerts contain no amount/email/method/code/provider id.

## Incident lifecycle

Missed transient/WAV purge, orphan lifecycle rows, quota projection mismatch
and payment/registry gaps enter the same durable lifecycle:
`detected → contained → owner_assigned → notified → investigating →
resolved|accepted_risk`. A privacy or money-impacting missed deadline is
launch-blocking until containment; every incident has a severity, named owner,
containment action, evidence class/reference, next deadline, resolution and
closure timestamp. Evidence remains metadata-only and never contains meeting,
card, email or provider payload.

## Runbooks

Required: provider outage/unknown/late success and 24-hour key expiry; no-grace cutoff; payment/refund registry gap; payment/refund receipt observation escalation; manual-merchant-refund observation mismatch; charge stop; secret rotation; storage reservation/TrackArtifact projection/add-on repair; transient terminal/forced purge and missed-SLA incident; fair-use create/restrict/appeal/review/clear with 24-hour escalation; time-credit correction; account close; backup/restore, migration rollback and disk-full. Product runbooks contain no refund calculation, approval or execution step.

## Launch matrix

Production flag defaults off. Release owner collects:

1. product approval of `Free` 250 MB / Trial 500 MB / `Личный` 2 GB, unlimited scope/fair-use, total-capacity 5/20/100/500 GB add-on/pro-rata and usability evidence;
2. unit-economics/finance/accounting/legal approval of every base/add-on price version, plus approved transcription-source retention/recovery deadline and compliance records;
3. security/RLS/secret/analytics/privacy and abuse review;
4. automated test-shop matrix and accessibility/brand-distance evidence;
5. Docker configuration, billing-ledger backup/restore, migration rollback, disk-full fail-closed behavior, health, monitoring and stop-all-charges drill;
6. real-shop base payment and only approved/enabled add-on payment → GET/webhook → unlimited/storage entitlement → payment receipt → manual full and partial refund in YooKassa merchant cabinet outside GRAF → webhook or poll + authoritative refund GET → refund receipt observation → registry reconciliation, with zero GRAF refund mutation calls;
7. support/runbook ownership and closure of global `pilot_blocked` gaps.

Any failure leaves checkout disabled. Payment canary alone is not public-launch approval.
