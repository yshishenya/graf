# Quickstart: Проверка Share Feature 125

## Scope

This guide validates the first safe delivery: internal authenticated
summary-only sharing, capability-aware UI, calendar-backed internal suggestions,
recipient-bound links, revoke/expiry and security negatives. The B2C exact-email
path is implemented behind its operator gate with metadata-only delivery,
exact-identity acceptance and replay-safe grant exchange. External email,
public links, address-book permission and referral conversion remain disabled
unless their independent gates are explicitly enabled in a synthetic
environment.

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
must keep the following false:

```text
share_external_invitations_enabled=false
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

### C. Disabled external capability

1. Enter `external@example.test` while external invitations are disabled.
2. Confirm no POST is made to `/share-invitations`.
3. Confirm the value remains in the field and the status explains that external
   invitations are unavailable, with an allowed internal alternative if one
   exists.
4. Confirm the UI does not expose a generic retry loop.

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

For a release of this gated-disabled slice, run the documented CD dry-run first
and attach validation evidence, Russian changelog and rollback readiness. Do
not enable external email, public links, address-book/provider lookup or
referral attribution as part of this release.

## Validation record — 2026-07-24

- Focused Feature 125 share/access/workflow matrix: 48 passed; the separate
  wrong-account continuation and desktop share-route check: 4 passed.
- `swift test --package-path apps/macos`: 609 passed, 0 failed;
  `ContractValidation`: pass; legacy-audio guard: pass.
- `infra/scripts/ci-local.sh`: pass — macOS 609 passed; PostgreSQL 2,230
  parallel + 41 strict passed, 2 skipped; Ruff, Python compile, RLS boundary,
  compose config and deployment evidence scan passed.
- Synthetic browser/embedded contract coverage includes both `/meetings/.../share`
  and `/desktop/.../share`; no meeting content, live credentials or real
  contacts were used. Live production public-link and external-delivery gates
  remain disabled.
