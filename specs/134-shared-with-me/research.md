# Research: Поделились со мной

## Decision: reuse the existing grant and access-decision model

`MeetingShareGrant` already represents active recipient rights, including
scope, download/export capability, expiry and accepted external invitations.
`decide_meeting_access` remains the authority for whether a recipient may see
the meeting now. No parallel access table or eligibility implementation is
needed.

## Decision: add a narrow cross-workspace grant lookup, not broad meeting RLS

Current normal request RLS is workspace-scoped, so it cannot enumerate grants
from other workspaces. A special context may select only grant candidates where
the current user is the direct active grantee and the grant has not expired.
It has no write policy and receives no direct cross-workspace meeting policy.

Each candidate is then rechecked by the existing proof and access decision in
its source workspace. This preserves revocation, expiry, verified-email and
membership rules without reimplementing them.

## Decision: a dedicated list template

The owner meeting-list template includes upload, delete, filter and workspace
controls. Reusing it would make accidental privilege expansion too easy. The
new page uses the cabinet shell and card styles, but contains only recipient
safe information and a single open action.

## Decision: accepted invitations only

Pending external invitations are address-bound, not a current verified user
right. They are excluded until acceptance creates an active grant. This avoids
revealing a meeting before the recipient has proven ownership of the address.

## Decision: no new endpoint or client state

Existing server-rendered cabinet routes and shared-meeting egress already
provide the required interaction. Two collection routes and one query helper
are sufficient; adding a JSON API or client-side store would add duplicate
access logic.
