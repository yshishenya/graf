# Research: Owner Review Live Polish

Feature: `036-owner-review-live-polish`

## Decision: Keep owner review server-owned and authenticate it through existing session primitives

**Rationale**: The existing cabinet API and HTML routes already depend on
`get_principal`, `get_device_context`, and `get_tenant_scope`. Session tokens
are supported through `Authorization` and `X-Auth-Session`, and the production
smoke helper already issues a temporary `AuthSession` without printing the raw
token. Reusing this path preserves RLS, device binding, workspace membership,
and cleanup behavior.

**Alternatives considered**:

- Add a new unauthenticated debug route: rejected because it would violate the
  auth boundary and could leak meeting existence.
- Use legacy `X-User-Id`/`X-Workspace-Id` browser headers manually: rejected for
  owner-review evidence because normal browser navigation cannot provide those
  headers and it bypasses the real session path.
- Commit live screenshots with redactions: rejected by default because private
  meeting content, account identifiers, and URLs are easy to expose accidentally.

## Decision: Treat browser access as unresolved until a safe session handoff exists

**Rationale**: Feature 035 proved that `https://rec.2brain.pro/meetings` exists
but returns `401 missing_auth_context` without auth headers. A normal browser
route cannot use `X-Auth-Session` unless the app provides a safe cookie/session
handoff or the evidence runner injects headers without committing secrets.
Implementation must either add a short-lived, cleanup-backed owner-review
handoff or record that live browser UX remains blocked while header-auth API
proof passes.

**Alternatives considered**:

- Declare the route ready because the API works with headers: rejected because
  the product owner needs a usable web review workspace, not only API access.
- Store a bearer token in local docs/scripts: rejected because token leakage is
  forbidden.
- Use the user's logged-in Chrome state blindly: rejected unless the state is
  verified without inspecting or committing cookies, tokens, or private content.

## Decision: Notes/actions are truth states in 036 unless persisted generated output already exists

**Rationale**: The current processing model exposes summary availability state
but not durable summary/action content suitable for launch review. 036 must not
invent meeting outcomes. It should show summary, decisions, action items, and
follow-ups as `available`, `processing`, `blocked`, `unavailable`, or
`deferred`, and explain launch-readiness impact. If generated content remains
unavailable or deferred, `mvp_loop_ready` remains excluded.

**Alternatives considered**:

- Generate notes client-side from transcripts during this slice: rejected
  because it would introduce new AI/data-egress behavior outside the spec.
- Show optimistic placeholder notes: rejected because it would overclaim the
  MVP value loop.
- Hide notes/actions entirely: rejected because it would obscure a P1 launch
  blocker.

## Decision: Polish runtime-critical V8 surfaces only

**Rationale**: Feature 030 V8 covers 17 top-level frames, but 036 is the first
runtime polish slice after live evidence. It should focus on surfaces that the
owner actually opens now: meeting list, meeting detail, notes/action state,
governance/access/delete states, upload/new entry points, search/filter/sort
controls, desktop embedded cabinet shell, and native capture control placement.

**Alternatives considered**:

- Implement every V8 frame: rejected as too broad for one validation slice.
- Ignore V8 and only fix backend auth: rejected because the user explicitly
  called out that the current interface is not close enough to reference quality.
- Copy Krisp visual expression to move faster: rejected by constitution and
  clean-room rules.

## Decision: Evidence is metadata-safe and private screenshots stay out of git

**Rationale**: Live owner review may reveal private meeting titles, transcript
text, account identifiers, emails, cookies, tokens, or signed URLs. Committed
evidence should use structured status, sanitized route names, HTTP/result
classes, capability names, screenshots only when private content is absent or
synthetic, and forbidden-content scans.

**Alternatives considered**:

- Commit raw screenshots and redact later: rejected because irreversible leaks
  can happen before review.
- Omit live evidence entirely: rejected because `web-owner-live-auth-context`
  is the main P1 gap.

## Decision: Installed desktop proof stays anchored to `/Applications/2brain Rec.app`

**Rationale**: The user asked to launch from Applications so macOS permissions
remain stable. 035 already proved this path. 036 must keep using the installed
bundle for runtime screenshots and manual proof, while source-level Swift build
and tests still run from the repository.

**Alternatives considered**:

- Run from Xcode/SwiftPM build products: rejected for runtime evidence because
  permissions and app identity can differ from the installed app.
- Move the app to `~/Applications`: rejected for now because the accepted 035
  evidence and user instruction converged on `/Applications/2brain Rec.app`.
