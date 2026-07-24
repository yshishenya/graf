# Quickstart: Проверка Share Feature 125

## Scope

This guide validates the first safe delivery: internal authenticated
summary-only sharing, capability-aware UI, calendar-backed internal suggestions,
recipient-bound links, revoke/expiry and security negatives. The B2C exact-email
path is implemented behind its operator gate with metadata-only delivery,
exact-identity acceptance, one-step auth/automatic first-account bootstrap and
replay-safe grant exchange. Exact-email external
delivery is enabled in the controlled production rollout after the deploy-gate
passed; public links,
address-book permission and referral conversion remain disabled unless their
independent gates are explicitly enabled in a synthetic environment.

All names, addresses, meeting IDs and meeting content in this guide are
synthetic. Do not use a real mailbox, token, transcript, audio file or private
calendar contact.

## Prerequisites

From the repository root:

```sh
cd /Users/yshishenya/.codex/worktrees/fa7e/crisp
specify --version
```

Use the repository's normal test environment and fixtures. The default settings
must keep the following false; production overrides only the first flag after
the external-delivery gate passes:

```text
share_external_invitations_enabled=false  # synthetic/default
share_public_links_enabled=false
share_team_audience_enabled=false
```

## Focused automated checks

Run the focused unit/contract/integration checks after each implementation
phase:

```sh
cd apps/server
pytest -q \
  tests/unit/test_recording_workflow_access.py \
  tests/contract/test_recording_share_ui_contract.py \
  tests/contract/test_recording_share_invitation_contract.py \
  tests/integration/test_meeting_share_links.py
```

Add the Feature 125 tests named by `tasks.md` for:

- capability projection and no request when external invitations are disabled;
- recipient search bound to meeting and `can_share`, escaped search text and
  bounded results;
- display-name/email/calendar deduplication;
- internal summary-only grant, API-returned recipient-bound link and Copy link;
- revoke, rotation, expiry and parallel duplicate action;
- accepted invitation inheriting bounded expiry;
- accepted invitation returning a separate grant token and replaying the same
  grant URL only for the same verified recipient;
- domain invariant enforcement independent of request schema;
- token/log/header/analytics negative checks using synthetic values.

Then run:

```sh
git diff --check
```

## Manual acceptance matrix

Use one synthetic owner, one active workspace user, one calendar-matched active
user and one unknown external address.

### A. Share opens only on explicit action

1. Open a meeting detail page in browser cabinet and embedded desktop cabinet.
2. Activate `Поделиться` once.
3. Confirm one modal appears, the recipient field receives focus and the opener
   regains focus after close/Escape.
4. Reload with JavaScript disabled or with a stale fragment and confirm the
   server still controls access and Share does not auto-open.

### B. Internal recipient

1. Search synthetic display name and synthetic verified email.
2. Confirm result is limited to active current-workspace identities.
3. Confirm a calendar-matched result has a `Календарь` source label.
4. Choose the result and explicitly open summary-only access.
5. Confirm the access list updates, Copy link uses only the returned URL, and
   the recipient can view summary but not transcript/playback/download/export.
6. Revoke and confirm the next controlled request is blocked.

### C. External exact-email capability

1. In the synthetic environment, enter `recipient@example.test` and confirm the
   request is summary-only/view-only and carries no meeting content.
2. Confirm the delivery state distinguishes `sent` (Postal accepted the
   request) from `outcome_unknown` (the network result was not confirmed).
3. Confirm exact verified-email acceptance creates no workspace membership and
   creates a separate bounded grant token.
4. For a new synthetic recipient, open the invitation, choose the single email
   login action, enter the one-time code and confirm the personal account is
   created automatically before the browser returns to the invitation and opens
   summary. No separate `/sign-up` step is shown or required.
5. In a second synthetic run with external delivery disabled, confirm no POST
   is made to `/share-invitations`, the value is preserved and the UI offers an
   internal alternative.

### D. Lifecycle and race negatives

1. Use synthetic invitations with pending, sent, expired, revoked and
   outcome-unknown states.
2. Confirm each has a distinct bounded next action.
3. Accept immediately before expiry and confirm grant expiry is no later than
   invitation expiry.
4. Accept after expiry, after revoke and after meeting deletion; all responses
   are generic unavailable and no meeting metadata leaks.
5. Submit duplicate actions from two tabs and confirm one active grant/invite
   and bounded audit evidence.

### E. Calendar and address-book privacy

1. Link a synthetic calendar event with internal, declined, stale and external
   participants.
2. Confirm only the current authorized context is suggested and source/freshness
   is visible.
3. Confirm attendee presence does not create a grant or change recording state.
4. In browser-only mode, confirm no Contacts permission is requested and typed
   email remains available according to policy.
5. In a future native-picker fixture, select one synthetic address and confirm
   only that selection enters the recipient flow; no full contact list is sent.

### F. Accessibility and presentation

Check browser and embedded surfaces in dark/light themes, 320 CSS px width,
200% zoom, keyboard-only navigation, VoiceOver labels, increased contrast and
reduced motion. Confirm no horizontal scroll, focus loss, hidden disabled action
that still fires a request, or copied competitor visual treatment.

## Security checks

Use synthetic marker strings and inspect application/proxy test logs, response
headers, browser history/autocapture fixtures and audit JSON:

- zero raw share/invitation/referral tokens outside the intended one-time
  response;
- no transcript/audio/summary text/private contact data in email or analytics;
- no directory enumeration without authorized meeting context;
- no wildcard search expansion;
- no cross-tenant or wrong-recipient access;
- no stale token access after revoke, expiry, rotation or deletion;
- rate-limit response is bounded and privacy-preserving.

## Repository gate and release boundary

Before PR/closeout for this high-risk feature:

```sh
infra/scripts/ci-local.sh
```

For a release of this slice, run the documented CD dry-run first and attach
validation evidence, Russian changelog and rollback readiness. Exact-email
external delivery may be enabled only with the server-side Postal and HMAC
secret settings; public links, address-book/provider lookup and referral
attribution remain disabled.

## Validation record — 2026-07-24

- Focused Feature 125 share/access/auth matrix: 50 passed; the targeted
  invitation-auth/provider-workspace regression passed separately.
- `swift test --package-path apps/macos`: 624 passed, 0 failed;
  `ContractValidation`: pass; legacy-audio guard: pass.
- `infra/scripts/ci-local.sh`: pass after synchronizing with `master` — macOS
  624 passed; PostgreSQL 2,255 parallel + 41 strict passed, 2 skipped; Ruff,
  Python compile, RLS boundary, compose config and deployment evidence scan
  passed. The runtime OpenAPI drift found during merge was fixed by adding the
  five missing `SummaryCandidateResponse.reason_code` enum values and the
  focused drift test passed.
- CD dry-run and execute: pass for branch `125-meeting-sharing` and deployed
  SHA `2db3d4ccd2541fbc7701b5803ef8049d2c2cc709`; migration head
  `0035_meeting_share_security`, backup/restore rehearsal, disposable RLS
  probe, runtime/worker readiness, production smoke and automatic dispatch
  passed. Automatic retry, backfill, range and normalization maintenance are
  recorded by the deploy gate as required post-deploy follow-up checks.
- External exact-email rollout verification: provider configuration,
  credential-encryption key,
  generated share-identity HMAC secret, durable actor/device invitation limit,
  at-most-once delivery fence, token-scrubbing and revoke/deletion evidence
  passed in production config gates for both API and worker. Postal network
  reachability returned an auth-protected response without sending a message;
  a live email was intentionally not sent without a consented test recipient.
  Public links, address-book/provider lookup and referral attribution remain
  disabled.
- macOS local artifact `2026.07.24.3` was built as
  `apps/macos/.build/installer/graf-local.pkg` with `GRAF Local Code Signing`;
  SHA-256 is `4cb73bdc94d8d18aba3597794d34fc1abfb9f0276f3f9351bac9445dbf51a197`;
  the package is unsigned and has no Developer ID or notarization evidence.
- Synthetic browser/embedded contract coverage includes both `/meetings/.../share`
  and `/desktop/.../share`; no meeting content, live credentials or real
  contacts were used. Live production public-link, Contacts/provider and
  referral gates remain disabled; exact-email is the only enabled external path.

## Validation record — 2026-07-24 post-review hardening

- Focused PostgreSQL/RLS/auth/Share regression matrix: `22 passed`; the
  broader focused Feature 125 and security/access matrix also passed. The
  checks cover the read-only invitation continuation context, durable auth-code
  throttling, provider email-verification updates, Share retry/confirmation
  states, notification outcome reporting and initial calendar suggestions.
- `infra/scripts/ci-local.sh`: pass — macOS `624 passed`; PostgreSQL `2,260
  passed, 1 skipped` in parallel and `41 passed, 1 skipped` in strict mode;
  Ruff, Python compile, compose config and deployment-evidence scan passed.
- Repeat security/code/Ponytail review: no critical findings. The lookup RLS
  context is `USING`-only, rate-limit scopes use keyed HMAC, invitation rows
  commit before Temporal dispatch, and unknown delivery outcomes do not trigger
  an automatic duplicate email.
- Product/accessibility review is complete at the static/contract level,
  including error, retry, keyboard, combobox, focus-return and clean-room
  checks. Screenshot-based authenticated browser review was not executable in
  this environment because no authenticated local GRAF tab was available and
  the production URL was blocked by the in-app browser policy; this is not
  claimed as rendered visual evidence.
- This section records the pre-deploy review evidence. The release CD gate has
  since completed successfully; the production closeout below is now the source
  of truth for the deployed SHA and migration head.

## Production closeout — 2026-07-24

- `infra/scripts/cd-remote.sh --execute --branch
  codex/125-meeting-sharing-review-fixes`: pass. Production runtime SHA is
  `9a44d9af9c0bce0c4a75b6d497657492f44c818a`; migration head is
  `0037_auth_rate_limit_buckets`.
- Backup/restore rehearsal, RLS probe, database-role boundary, Temporal and
  processing-worker readiness, media-worker boundary, production smoke,
  automatic dispatch and final `health/live` plus `health/ready` checks passed.
  Backup reference:
  `/opt/projects/2brain-rec/backups/20260724T113944Z`.
- Runtime configuration verification passed in both API and delivery worker:
  external invitations and email login are enabled, Postal is configured and
  the public base URL is configured. No live email was sent without a
  consented synthetic recipient.
- The rebuilt macOS package is
  `/Users/yshishenya/.codex/worktrees/fa7e/crisp/apps/macos/.build/installer/graf-local-release-125-v4.pkg`,
  version `2026.07.24.4`, SHA-256
  `112a5f2419d8517a0ef5d9fde26ebac0564bf966d01897576ecb7878c2e5d936`.
  It is local-only signed/unsigned for distribution purposes; Developer ID,
  notarization and public artifact publication are not claimed.

## Production delivery incident follow-up — 2026-07-24

- A metadata-only production check found that an external invitation could stay
  queued in the UI and then become `outcome_unknown` without reaching the
  mailbox. Worker logs showed DNS failure before the Postal request reached the
  provider; no meeting content or email body was included in the investigation.
- Root cause: `rec-processing-worker` had the Postal API settings and secret but
  was not attached to the external `postal-network`, so `postal-web` was not
  resolvable from that worker.
- Fix: production Compose now attaches the worker to both `rec-private` and
  `postal-network`; the Compose contract test asserts this boundary and that the
  Postal network remains external.
- The hotfix was deployed at exact SHA
  `7b601cf94b7f1a8183dc55e8651d2851c4b0eee7` with backup
  `/opt/projects/2brain-rec/backups/20260724T121617Z`; CD backup/restore, RLS,
  migrations, readiness, smoke and automatic dispatch passed.
- Post-deploy metadata-only checks confirmed the worker is healthy, joined to
  `postal_postal-network` and `twobrain-rec-private`, and resolves `postal-web`.
  No live email was sent by the operator. Existing `outcome_unknown` rows are
  not resent automatically; cancel the old invitation and create a new explicit
  invitation after the hotfix.
