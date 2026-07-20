# Research: Workspace Account Onboarding

## Current integration map (2026-07-17)

- Browser email registration resolves the configured workspace in
  `cabinet/web_routes/auth.py` and creates its membership in
  `cabinet/web_routes/auth_email_flow.py`.
- Provider callbacks create/reuse a scoped user in `auth/callbacks.py`.
- `admin/invitations.py` currently calls
  `complete_matching_invitation_after_login`, which creates membership during
  login and must be replaced by an offer.
- `AuthSession` is already the authoritative active-workspace scope;
  `auth/dependencies.py` revalidates membership for server requests.
- Regression coverage starts in `test_auth_contracts.py`,
  `test_web_owner_session_context.py`, `test_tenant_authorization.py`,
  `test_rls_application_boundaries.py` and the embedded-cabinet workspace
  tests. These are the focused suites for 097.

## Decision 1: retain the current account identity within one deployment organization

**Decision**: `UserIdentity` remains the canonical account for the configured
GRAF organization. A new personal workspace is another `Workspace` owned by
that user; it is not a new organization or a duplicate user.

**Rationale**: `ExternalIdentity(provider, provider_subject)` is globally
unique and all current auth/session/RLS paths already operate inside one
organization. Creating a second account or organization would prevent a person
from accepting a corporate invitation without reworking identity federation.

**Alternatives considered**: a new global accounts service (unnecessary new
trust boundary); one organization per personal space (breaks the existing
unique provider identity).

## Decision 2: bootstrap workspace is an internal auth anchor, never a destination

**Decision**: retain `web_login_workspace_id` only to locate the deployment
organization and its public login policy during transition. Public registration
must create/select a personal workspace and issue the session there.

**Rationale**: the server needs a configured bootstrap scope before an unknown
visitor has a workspace. Keeping it internal avoids a public identifier while
removing its dangerous implicit-membership meaning.

**Alternatives considered**: require a workspace ID (rejected by FR-001 and
FR-007); create a new global anonymous tenant (extra architecture without user
value).

## Decision 3: invitations become visible offers before membership

**Decision**: after verified sign-in, the server claims matching pending
invitations as user-specific offers. Only an authenticated, CSRF-protected
accept endpoint can create a membership; reject/dismiss leaves no membership.

**Rationale**: existing `complete_matching_invitation_after_login` creates a
membership during login. That violates the explicit-choice requirement and
cannot explain multiple invitations safely.

**Alternatives considered**: silently complete the invitation (unsafe);
return all pending invitations directly from a public page (leaks workspace
existence).

## Decision 4: active workspace is the server-issued session scope

**Decision**: list accessible workspaces from active membership, then switch
by issuing a new session/device scope only after server-side membership check.
The browser uses its new cookie; desktop treats a rejected scope as a blocked
state and asks for an explicit new selection.

**Rationale**: `AuthSession` already binds user, workspace and device. A
separate mutable client preference would be an authority bypass and could
silently retarget an upload.

**Alternatives considered**: client-only selector (not authoritative); moving
an in-flight upload (violates FR-015a).

## Decision 5: legacy migration is report-only in this release

**Decision**: ship a metadata-only command/report classifying existing
bootstrap-workspace users and recording ownership counts before enabling the
release. Thereafter the same idempotent helper may add a personal workspace on
that person's next verified sign-in, but it must not move recordings, remove a
corporate membership or change any existing workspace ownership.

**Rationale**: existing workspace ownership cannot be inferred safely. The
spec requires a reviewable report before a separately accepted migration.

**Alternatives considered**: automatic data move (irreversible privacy risk);
leave legacy users without a personal fallback (can strand a revoked user).

## Decision 6: invitation resend is a generic sign-in notification

**Decision**: an admin resend renews an otherwise valid pending invitation and
sends a generic notification to its email target telling the person to sign in
and review the offer. It carries no invitation token, raw workspace ID or
automatic enrollment action.

**Rationale**: the current invitation model has no safe email-link token, but
the existing Postal delivery path can notify the verified email target. The
later offer lookup still rechecks identity, invitation status and explicit
acceptance.

**Alternatives considered**: make resend a no-op (does not meet FR-011); add a
bearer invitation link (unnecessary secret-bearing surface).
