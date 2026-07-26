# Data Model: invitation magic-link RLS boundary

This hotfix introduces no tables, columns, indexes or migrations.

## Existing entities and ownership

| Entity | Workspace ownership | Required context |
| --- | --- | --- |
| `AuthAuditEvent` | The workspace in which the auth event occurred | Personal workspace context for email login audit |
| `AuthSession` / device binding | Recipient personal workspace | Personal workspace, user and device context |
| `MeetingShareInvitation` | Workspace that owns the meeting | Invited meeting workspace context |
| `MeetingShareGrant` | Source meeting workspace, recipient-bound | Invited meeting workspace context |
| `MeetingShareRateLimitBucket` | Source meeting workspace and recipient/device | Invited meeting workspace context |
| Continuation state | Source invitation workspace and one-time nonce | Invitation continuation lookup/request context |

## Invariant

Every flush must occur while the database tenant context matches the workspace
of each pending row. The fix closes the only discovered boundary where a pending
personal-workspace audit row survived a context switch into the source workspace.
