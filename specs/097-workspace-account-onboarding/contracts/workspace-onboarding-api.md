# Workspace Onboarding Contract

All endpoints require the existing authenticated session unless stated
otherwise. IDs are opaque and no public form accepts a raw workspace ID.

## Public registration

`POST /sign-up/email/verify` and provider callback completion retain their
existing forms. For a new verified identity they must create or reuse the
personal workspace and redirect to the cabinet with a session scoped to it.

Responses must not disclose pending corporate workspaces. A matching
invitation creates a private offer after authentication.

## Accessible spaces

`GET /settings/spaces`

Returns the current personal space and active corporate memberships only. Each
item contains an opaque ID, safe display name, `kind`, role and whether it is
active. Revoked or pending spaces are absent.

## Invitation offers

`GET /settings/join-offers`

Returns offers owned by the authenticated user. The list contains a safe
workspace label, invited role, expiry and opaque offer ID; it does not expose
contacts, provider claims or internal policy.

`POST /settings/join-offers/{offer_id}/accept`

Requires CSRF and an active session. Revalidates the invitation and identity,
then creates/reuses exactly one membership. It returns the terminal offer
state; it does not silently change the current workspace.

`POST /settings/join-offers/{offer_id}/reject`

Requires CSRF. Marks only this offer rejected and never changes membership.

## Corporate invitation resend

`POST /admin/invitations/{invitation_id}/resend`

Requires a corporate administrator. It may renew a valid pending invitation
and sends a generic sign-in notification to the existing email target. It does
not expose an invitation bearer token, create membership or disclose the target
contact outside the authorized admin surface. A revoked, expired or completed
invitation remains terminal and cannot be revived by resend.

## Active workspace switch

`POST /settings/spaces/{workspace_id}/activate`

Requires CSRF. The server verifies active membership and issues a new scoped
session. An unavailable or revoked membership returns a safe denial; ongoing
uploads/recordings keep their original scope and require explicit recovery.
