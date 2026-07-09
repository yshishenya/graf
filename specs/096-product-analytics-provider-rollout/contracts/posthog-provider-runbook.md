# Contract: PostHog Provider Runbook

**Feature**: `096-product-analytics-provider-rollout`

This contract defines the production-ready self-hosted PostHog provider layer. It is not a live secret record.

## Hosting Decision

- Provider: self-hosted PostHog.
- Cloud PostHog: out of scope.
- First rollout placement: same production server as GRAF.
- Domain: separate analytics domain, planned as `analytics.2brain.pro` unless implementation approval changes it.
- Portability: required. PostHog must be movable later to a separate analytics server without changing event contracts, identity rules, dashboard definitions, or disclosure copy.

## Required Service Boundaries

PostHog must have separate:

- service/compose project boundary from GRAF services;
- domain and TLS routing;
- runtime secret files;
- volumes and backup targets;
- resource limits for CPU, memory, disk, and restart policy;
- RBAC/access model and audit expectations for operators, dashboard viewers, exports, and provider configuration changes;
- health checks and log redaction;
- rollback switches for delivery, autocapture, replay, and service exposure.

## Initial Deployment Requirements

The implementation runbook must document:

- DNS record for the analytics domain, without committing provider keys;
- TLS issuance and renewal;
- Docker Compose stack file(s) or deployment wrapper;
- official generated PostHog self-hosted Compose runtime source, because the
  committed GRAF handoff contract is not the complete upstream runtime stack;
- `infra/scripts/cd-remote.sh --dry-run` handoff for the separate PostHog stack, with no live secrets printed;
- service dependency list and health checks;
- volume inventory and backup/restore procedure;
- minimum 90-day retention baseline;
- concrete initial CPU, memory, disk, network, log-retention, backup-retention, disk-full, and alert/review thresholds;
- high-resource behavior that degrades or disables analytics before normal GRAF workflows are starved;
- monitoring/log review commands;
- move-out procedure to a separate analytics server.

## RBAC And Audit Contract

The implementation runbook must document:

- operator roles that may manage the PostHog stack, project settings, retention, replay flags, exports, and dashboard access;
- dashboard viewer roles for product, support, engineering, and campaign review, without committing personal names;
- audit expectations for provider configuration changes, access changes, export creation, replay flag changes, and retention changes;
- evidence allowed for access review: role names, review date/status, and non-secret blocker codes only;
- evidence forbidden for access review: user emails, personal names, session exports, raw payloads, or screenshots with account/visitor data.

## PostHog Data Scope

Allowed in self-hosted PostHog:

- approved 094 activation events;
- approved public acquisition events from 093;
- server-mediated events;
- web-direct events;
- desktop-direct product analytics events;
- broad browser autocapture for all current browser-rendered GRAF pages;
- future browser page autocapture by default after credential suppression exists;
- internal content-bearing product analytics that GRAF can already display, when retained inside PostHog only.

Forbidden everywhere, including PostHog:

- passwords and passcodes;
- OAuth codes;
- access, refresh, and ID tokens;
- API keys and provider/client secrets;
- signed URLs;
- cookies;
- private keys;
- raw audio files;
- raw payload dumps in logs or evidence.

Forbidden outside PostHog and evidence:

- content-bearing PostHog exports;
- screenshots with visitor/account/meeting data;
- raw autocapture payload samples;
- transcript text, meeting content, account names, or private identifiers in committed files.

## Autocapture Contract

- `posthog_autocapture`: enabled everywhere immediately for current browser-rendered GRAF pages.
- Future browser-rendered pages: PostHog autocapture enabled by default once global credential suppression exists.
- Page inventory records sensitivity, expected product-visible data, credential suppression, retention/deletion truth, owner, dashboard purpose, and rollback.
- Autocapture is not session replay.

## Session Replay Contract

- Default: disabled.
- May be enabled only after page-class proof, retention decision, storage capacity proof, masking proof, QA/legal approval, dashboard caveat, and rollback.
- Replay storage must use the current supported self-hosted PostHog recording storage model, not a deprecated path.

## Delivery Routes

| Route | Scope | Required Controls |
| --- | --- | --- |
| `server_mediated` | 094 activation events, attribution bridge, dedupe, delivery gaps | event validator, identity rule, RBAC/audit rule, retention/deletion truth, delivery gap record, no-secret smoke |
| `web_direct` | page views/events/autocapture/replay when approved | credential suppression, disclosure, RBAC/audit rule, retention/deletion truth, provider smoke, rollback |
| `desktop_direct` | product analytics route to self-hosted PostHog | disclosure, identity rule, RBAC/audit rule, retention/deletion truth, no-secret validation, retry/loss rule, rollback |

Desktop direct delivery to Yandex remains blocked unless a later explicit approval changes it.

## Dashboard Requirements

Minimum PostHog dashboards:

- source-to-first-value funnel;
- first milestone dedupe by pseudonymous user;
- onboarding/account connection drop-off;
- broad autocapture exploration dashboard;
- delivery gaps and provider health;
- access/RBAC/audit readiness note;
- internal/support/smoke/test caveat dashboard note;
- retention/deletion truth note.

## Rollback Requirements

Rollback must disable:

- server delivery;
- web-direct delivery;
- desktop-direct delivery;
- autocapture;
- session replay;
- analytics domain exposure if needed.

Rollback expected product impact: measurement gap only. Normal GRAF product workflows must continue.

## Evidence Requirements

Allowed evidence:

- redacted domain readiness;
- service status;
- health pass/fail;
- redacted secret-file presence;
- event names;
- page-class states;
- RBAC/access model status;
- audit-review status;
- deploy dry-run pass/fail status;
- dashboard availability status;
- rollback pass/fail.

Forbidden evidence:

- project keys;
- secret values;
- live user/account identifiers;
- cookies or client IDs;
- raw event/autocapture/replay payloads;
- screenshots with visitor, account, or meeting data.
