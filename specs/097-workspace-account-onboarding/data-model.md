# Data Model: Workspace Account Onboarding

## Existing entities reused

| Entity | Role in 097 | Invariants |
|---|---|---|
| `UserIdentity` | Canonical user for one GRAF deployment organization | One verified external identity resolves to one active user; no duplicate user for retry. |
| `Workspace` | Personal or corporate data boundary | All records, sessions, devices and audit remain workspace-scoped. |
| `WorkspaceMembership` | Corporate and personal authorization | Personal owner is active; corporate membership is active only after explicit acceptance. |
| `WorkspaceInvitation` | Admin-created corporate invitation | Pending invitation never itself authorizes access. |
| `AuthSession` | Current active workspace | Session workspace must always match a current active membership. |

## Added fields and entity

### Workspace personal marker

Add `kind` (`personal` or `corporate`) and nullable `owner_user_id` to
`workspaces`.

- `personal` requires an owner and exactly one active owner membership.
- A user may own at most one personal workspace per organization.
- `corporate` has no personal owner marker and retains existing admin policy.
- Existing workspaces migrate as `corporate`; no data changes follow from that
  classification.

### WorkspaceJoinOffer

Server-created, user-specific view of a matching pending invitation.

| Field | Rule |
|---|---|
| `id` | opaque UUID, never inferred from a workspace ID |
| `user_id` / `invitation_id` | unique pair; both required |
| `workspace_id` | destination workspace, used only after membership validation |
| `status` | `offered`, `accepted`, `rejected`, `expired`, `revoked` |
| `expires_at` | cannot outlive the invitation |
| audit fields | metadata-only identifiers and state transitions |

An offer may be read only by its user. Acceptance rechecks invitation state,
verified identity match, policy and membership atomically. A replay returns the
same terminal state and never creates a duplicate membership.

## State transitions

```text
verified sign-in → personal workspace present → session scoped to personal
matching invitation → offered → accepted → corporate membership active
matching invitation → offered → rejected|expired|revoked → no membership
corporate membership revoked → current session invalid → personal fallback
```

## Data preservation

No meeting, upload, processing, retention or audit row changes workspace in
this feature. After the report has been reviewed, a verified legacy user may
receive an empty personal space on sign-in; the report aggregates only counts
and classifications and exposes no recording content, raw emails or provider
data.
