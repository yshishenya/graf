# Research: Safe Browser Login Returns and Callback Diagnostics

## Decision 1: Resolve an exact browser detail return after session creation

**Decision**: Add one asynchronous server-side resolver for exact
`/meetings/<UUID>` and `/desktop/meetings/<UUID>` browser return candidates.
It runs only after a new session has been established, sets an explicit
`TenantDatabaseContext`, loads the meeting metadata, and reuses
`decide_meeting_access`. An authorized candidate remains unchanged; a missing,
deleted, malformed, or denied candidate becomes the matching meeting list.

**Rationale**: The old flow replayed the saved local `next` path after OAuth
completion without knowing whether the new user could see that meeting. The
existing access policy already handles ownership, active membership, sharing,
deletion, and workspace boundaries. Calling `get_cabinet_meeting_review` would
load a full review, including content-bearing records, merely to decide a
redirect; that is unnecessary and weakens the privacy boundary.

**Alternatives considered**:

- Let the detail route return its normal 404 after login: rejected because it
  recreates the reported technical dead end.
- Redirect every login to a list: rejected because it discards valid deep links
  for an owner, team member, or named share recipient.
- Make the desktop app repair its current route: rejected because the browser
  server owns external and email login completion and must protect every client.

## Decision 2: Keep pre-auth sanitization separate from post-auth access

**Decision**: Do not broaden or rewrite `_safe_browser_next_path` or
`_safe_browser_return_path`. The new resolver receives a trusted local
candidate after their existing checks and applies an access decision only to
the two exact cabinet detail-route shapes. Other safe local return paths retain
their current behavior.

**Rationale**: The existing helper is an open-redirect boundary used before
authentication and by logout. Combining it with RLS access logic would change a
shared security primitive and enlarge the regression surface.

**Alternatives considered**:

- Replace every browser local-path helper: rejected because it would change
  unrelated settings, logout, and API flows.
- Treat every local path as a meeting route: rejected because settings and
  other existing browser routes have no meeting access decision.

## Decision 3: Bind email completion to the stored callback state

**Decision**: Email login and registration completion use
`AuthCallbackState.requested_redirect` captured when the one-time code was
started. The later verification form's `next` remains presentation data for
error rendering but cannot select the post-auth destination.

**Rationale**: The current verification routes sanitize but then redirect to
the submitted form value. It can differ from the return candidate stored in the
one-time state, so it is not a stable continuation of the authenticated flow.
Using the stored value makes external-provider and email flows share the same
trust boundary.

**Alternatives considered**:

- Re-sanitize the verification form value: rejected because sanitation alone
  does not bind it to the code issuance state.
- Omit all email returns: rejected because it unnecessarily breaks legitimate
  detail links and creates inconsistent sign-in behavior.

## Decision 4: Render unavailable detail failures at the cabinet route

**Decision**: Each regular and embedded full-page detail route returns a
neutral 404 cabinet page when its detail is unavailable or its identifier is
malformed. The page uses the existing shell and a matching list link. HTMX
requests keep their existing `ProblemDetail` behavior.

**Rationale**: The generic problem handler deliberately serves JSON for API
contracts and has no cabinet-surface context beyond the path. Route-local
rendering limits the UX change to full cabinet navigation, avoids a global API
contract change, and does not interfere with playback polling that treats its
fragment 404 as terminal.

**Alternatives considered**:

- Convert all `ProblemDetail` 404 responses to HTML: rejected because APIs and
  existing consumers rely on their machine-readable problem contract.
- Render a custom fragment for every HTMX failure: rejected because the current
  terminal behavior must remain stable and this feature concerns page recovery.

## Decision 5: Disable Uvicorn access logs and allowlist application metadata

**Decision**: Add Uvicorn's `--no-access-log` to the production Docker command
and stop placing request headers in application `request.start` and
`request.end` events. Continue logging request ID, method, UUID-templated path,
status, and duration through the existing JSON logger.

**Rationale**: Uvicorn access lines retain raw request targets, including OAuth
query values. The application logger redacts selected sensitive header names,
but retaining arbitrary headers still allows a `Referer` or custom header to
carry authorization material. An explicit metadata allowlist is smaller and
more reliable than an expanding denylist.

**Alternatives considered**:

- Redact known query keys in Uvicorn output: rejected because Uvicorn formats
  a raw request target and future providers may use different names.
- Add more header names to a blocklist: rejected because arbitrary request
  headers can carry credential-like values.
- Remove all request diagnostics: rejected because support still needs
  correlation, route category, status, and duration.

## Decision 6: Keep deployment, log retention, and macOS code out of scope

**Decision**: Make this a server-only change. Validate the Docker command and
runtime logging locally; do not deploy, rotate, delete, or otherwise alter
production logs. Do not update the macOS app.

**Rationale**: The server controls login completion and the embedded web route.
The macOS client already defaults to the embedded meeting list and receives the
new behavior from the server. Production operation remains explicitly closed
while parallel work is underway.

**Alternatives considered**:

- Ship a client-only fallback: rejected because it cannot cover normal browser
  or email flows and would leave the server replay unsafe.
- Perform a production log cleanup now: rejected because it is an operational,
  potentially destructive action outside the user's current authorization.
