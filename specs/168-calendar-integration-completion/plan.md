# Feature 168 implementation plan

## Governance and lane

This is a high-risk/significant cross-module feature touching provider
credentials, Postgres/RLS, deletion, auth/CSRF, desktop UX and external OAuth.
The full Spec Kit sequence is required. This audit created the artifacts but
did not invoke repository hooks that would create a branch or commit, because
the user explicitly forbade both and required active feature 167 to remain
untouched.

Constitution gates carried forward:

- server-owned credentials and least privilege;
- read-only provider access;
- tenant isolation/RLS and fail-closed state;
- deletion truth and metadata-only evidence;
- visible manual Record/Stop regardless of calendar state;
- no auto-join, auto-record or calendar writes;
- clean-room/brand-distance and accessibility review;
- no task-to-issues sync before separate permission.

## Ponytail decision

Reuse the existing `CalendarSource`, `CalendarCredentialEnvelope`,
`ExternalCalendar`, event normalization, `apply_calendar_sync_result`,
`disconnect_source`, matching, route aliases, view models, fixtures and
macOS request/prompt models. Add only the missing provider-runtime seam,
state projection and shared mutation UX behavior. Do not introduce a generic
integration platform, new state store or desktop OAuth implementation until a
second live provider proves that the existing adapter boundary is insufficient.

## Target architecture

```text
Provider connect request
  -> authenticated tenant/owner/CSRF boundary
  -> provider flow coordinator
  -> provider adapter validate + identify + list calendars
  -> transaction: source + sealed credential + catalog + operation result
  -> authoritative read model / PRG or fragment response

Manual/periodic sync
  -> idempotent sync job claim
  -> server credential read/decrypt
  -> adapter full or incremental fetch (page/cursor loop)
  -> normalize + existing apply_calendar_sync_result
  -> safe outcome/audit + read model invalidation

Disconnect
  -> idempotent transaction lock/claim
  -> stop new jobs; never call provider-side revoke
  -> purge future derived rows / detach matched context
  -> mark credential tombstone + source failed_closed/disconnected
  -> commit result and refresh source projection
```

## Implementation phases

### Phase 0: Contract and readiness gate

Freeze current states/copy, decide Google scope, retention, provider catalog
policy and external dependencies. Add no live provider until owner decisions
are recorded.

### Phase 1: Truthful shared connection UX

Add one reusable form-state behavior for provider connect/sync/disconnect;
retain native POST fallback. Make operation result and authoritative source
projection durable. Add tests for empty, invalid, cancel, retry and reload.

### Phase 2: Provider runtime boundary

The small provider-neutral adapter protocol and job coordinator now wrap the
existing normalized event/sync functions. Google and shared CalDAV adapters are
implemented; every family remains production-disabled until its exact real
matrix passes rather than treating synthetic adapter coverage as support.

### Phase 3: Disconnect/read-model hardening

Make cleanup idempotent and transactionally visible. Decide tombstone retention,
ensure active projections omit disconnected sources, prevent job claims after
disconnect and prove no credential runtime access.

### Phase 4: Google Calendar beta

Server OAuth callback, token exchange/refresh, hashed account identity, catalog,
full/incremental sync, reconnect and local-only disconnect are implemented
behind the existing gate. The remaining phase is dedicated test-account
recovery evidence, Google verification, client-secret rotation and
rollout/rollback approval. Do not expose the provider in production before
those gates pass.

### Phase 5: Parity/UX/accessibility closeout

Run the same scenario IDs in browser and embedded cabinet at narrow/dark/light
states. Confirm native controls, prompt settings, context corrections and
no-context flow. Complete release/rollback evidence only after product approval.

### Phase 6: macOS upcoming tray

Add one native `NSStatusItem` and a SwiftUI popover backed by a short-lived
`CalendarTrayModel`. Reuse `DesktopUploadClient`, the existing auth cookie,
`DesktopCalendarPromptEvent.safeDisplayTitle()` and the existing embedded
cabinet route bridge. Keep tray state separate from prompt timing state, but
do not introduce a new credential, provider adapter, database table or
calendar cache. Refresh on app activation, auth-session changes, wake and a
bounded timer. Open only existing GRAF routes or an explicit validated
HTTP(S) meeting link; leave recording controls outside the tray.

## Suggested file ownership (implementation only)

Reuse/extend:

- `apps/server/src/twobrain_rec_server/calendar/service.py`
- `apps/server/src/twobrain_rec_server/calendar/sync.py`
- `apps/server/src/twobrain_rec_server/calendar/lifecycle.py`
- `apps/server/src/twobrain_rec_server/calendar/capabilities.py`
- `apps/server/src/twobrain_rec_server/calendar/credentials.py`
- `apps/server/src/twobrain_rec_server/api/calendar.py`
- `apps/server/src/twobrain_rec_server/cabinet/web_routes/calendar.py`
- `apps/server/src/twobrain_rec_server/cabinet/web_routes/calendar_helpers.py`
- `apps/server/src/twobrain_rec_server/cabinet/view_models.py`
- `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/fragments/calendar_settings.html`
- `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`
- `apps/server/src/twobrain_rec_server/db/models/calendar.py` and a new
  migration only if the selected contract requires it.

Add only if justified by Phase 0:

- `apps/server/src/twobrain_rec_server/calendar/providers.py` (small adapter
  protocol/coordinator; do not add a factory hierarchy for one provider).
- `apps/server/src/twobrain_rec_server/calendar/google.py` (Google adapter,
  only after OAuth dependency approval).
- worker integration in the existing job runtime, not a second scheduler.
- matching focused tests in existing calendar test files.

macOS should normally need no provider code. Reuse:

- `apps/macos/RecApp/Sources/Calendar/DesktopCalendarPromptActions.swift`
- `apps/macos/RecApp/Sources/Calendar/DesktopCalendarReminderService.swift`
- `apps/macos/Shared/Sources/Models/CalendarContextModels.swift`
- existing embedded cabinet route/session bridge.
- `apps/macos/RecApp/Sources/Calendar/CalendarTray.swift` for the native menu
  bar projection and popover.

## Rollout and rollback

- Feature-flag provider runtime and Google independently from legacy synthetic
  projections.
- Dark-launch adapter validation with metadata-only counters before exposing
  source success.
- Enable Google for all users simultaneously only after Google-specific OAuth,
  dedicated test-account and release gates pass. Enable every other provider
  independently only after that exact family's real browser/embedded matrix.
- Keep one global rollback flag that disables new connections and sync claims
  without reviving disconnected credentials or deleting meeting-owned context.
- Rollback disables new connect/sync claims, stops new job claims, preserves
  already-accounted meeting context, and leaves disconnect cleanup available.
- Never roll back by restoring credentials or reactivating a disconnected
  source without explicit owner action.

## Migration impact

Preferred path is no schema migration: reuse current source/catalog/snapshot,
credential and audit fields. A migration is allowed only for a durable
operation/job id, OAuth account identity, cursor metadata or tombstone field
that cannot safely fit existing columns. Any migration must have upgrade,
downgrade, RLS inventory and delete/rollback evidence.

## Validation gates

1. Existing unit/contract/macOS focused suites remain green.
2. Disposable Postgres integration/RLS suite runs with `TWOBRAIN_DATABASE_URL`.
3. Synthetic provider adapter proves pagination, failure, delete and retry.
4. Local Google happy path is proven; a dedicated test account must still prove
   revoked access, 410 and 429 recovery before any production claim.
5. Browser and embedded scenario matrix passes with keyboard/accessibility.
6. Warmed local PostgreSQL performance checks enforce NFR-006 independently of
   external provider latency.
7. `infra/scripts/ci-local.sh` and release guidance run before release; no
   commit, issue sync, deploy or release occurs without separate approval.
