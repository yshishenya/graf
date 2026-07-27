# Data Model: Поделились со мной

## Persisted model reused

### MeetingShareGrant

Existing fields used by the feature:

| Field | Purpose |
|---|---|
| `workspace_id`, `meeting_id` | Source meeting identity and shared-page target. |
| `grantee_user_id`, `audience_type` | Candidate belongs to the authenticated direct recipient. |
| `status`, `expires_at` | Initial active-grant eligibility filter. |
| `content_scope`, `can_download`, `can_export` | Existing access decision and recipient-safe access label. |
| `metadata_json` | Existing accepted-external invitation verification semantics. |

No persisted fields are added.

## Ephemeral view models

### SharedWithMeMeetingCard

Built only after authoritative revalidation:

| Field | Source | Exposure rule |
|---|---|---|
| `meeting_id`, `workspace_id` | Active candidate grant | Used only for the existing restricted target. |
| `title`, `started_at`, `duration_seconds`, `status` | Authorized meeting | Existing recipient-safe meeting metadata only. |
| `access_label` | Effective access decision | No owner or workspace details. |
| `href` | Existing shared-meeting route | Never points to an owner workspace page. |

### SharedWithMeLookupContext

Ephemeral DB context with the authenticated `user_id` and distinct context
kind. It is valid only for candidate-grant `SELECT`; it has no workspace
membership, meeting, mutation or invitation-continuation capability.

## Lifecycle

1. Grant becomes active after direct share or accepted invitation.
2. Lookup finds only direct active, non-expired candidates for the current user.
3. Existing access decision rechecks live recipient proof and source meeting.
4. One card is emitted per meeting using the most complete currently valid
   access level.
5. Revoke, expiry, deleted meeting or failed recipient proof removes the card
   on the next page load.
