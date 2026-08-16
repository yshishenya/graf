# Data model: связка и merge аккаунтов

## Existing entities

| Entity | Current source | Role in feature |
| --- | --- | --- |
| `UserIdentity` | `db/models/identity.py` | Canonical account row; survivor remains active, source becomes archived/merged. |
| `ExternalIdentity` | `db/models/federated_auth.py` | Verified email/OAuth identity; moved to survivor only after proof. |
| `Workspace` | `db/models/identity.py` | Tenant boundary; never merged implicitly. |
| `WorkspaceMembership` | `db/models/identity.py` | Access relation; union only when it does not alter role/ownership. |
| `Meeting`, `ProcessingPlaceholder`, ingest/artifact/outcome rows | `db/models/*.py` | Content is preserved in its original workspace and keeps its ID. |
| `AuthSession`, `RegisteredDevice` | `db/models/federated_auth.py`, `identity.py` | Invalidated/re-authenticated after merge. |
| `AuthAuditEvent` | `db/models/federated_auth.py` | Append-only, metadata-only evidence. |
| Calendar, billing, deletion and invitation entities | `db/models/calendar.py`, `billing.py`, `deletion.py`, `admin.py` | Preserved in scope; conflict gates prevent unsafe reassignment. |

## New or extended entities

### AccountMergeIntent

Short-lived server-owned workflow record.

- `id`
- `survivor_user_id`
- `source_user_id`
- `initiating_workspace_id`
- `email_proof_state` and `oauth_proof_state` (state only; no raw code/token)
- `preview_fingerprint`
- `requested_policy_version`
- `status`: `initiated`, `awaiting_proof`, `preview_ready`, `confirmed`,
  `completed`, `cancelled`, `expired`, `rejected`, `blocked`, `failed`
- `expires_at`, `confirmed_at`, `completed_at`
- bounded `error_code`/`blocker_code`
- `created_at`, `updated_at`

Constraints: source and survivor differ; deterministic uniqueness for an active
pair; one-use completion; no raw email code, OAuth token, meeting title,
transcript or provider secret.

### AccountMergeJournal

Metadata-only immutable outcome record for idempotency and support.

- `id`, `merge_intent_id`, `survivor_user_id`, `source_user_id`
- `policy_version`, `preview_fingerprint`, `status`
- bounded counts by entity class (not content)
- `blocked_conflict_codes` and `error_code`
- timestamps and request correlation ID

The journal is not a replacement for existing audit rows. It links the merge
operation to its metadata-only audit event and permits safe retry/readback.

### UserIdentity merge state

Extend the existing user row with a terminal merge marker (or equivalent
server-owned relation) containing `merged_into_user_id` and `merged_at`. The
source row remains addressable for foreign keys and cannot issue new sessions.

## Relationship rules

1. One active `ExternalIdentity` belongs to exactly one active or archived
   `UserIdentity`; a provider subject can never be linked to two users.
2. A successful merge moves eligible identities to the survivor under row lock;
   it never copies them.
3. `Meeting.workspace_id` is unchanged. `created_by_user_id` and other user
   references may be rewritten to the survivor only in the same transaction;
   append-only audit actor references are not rewritten.
4. Workspace memberships are merged by `(workspace_id, user_id)` only when
   role/ownership policy is unambiguous. A role conflict is a blocker, not a
   max-role calculation.
5. Active sessions for both users are revoked. Devices keep their historical
   rows but their trust/session bindings are revoked and require re-auth.
6. Existing deletion, billing and calendar ownership rows are not silently
   reassigned. Their preflight state controls whether merge is allowed.

## Merge transaction state machine

`initiated → awaiting_proof → preview_ready → confirmed → completed`

Terminal non-mutating branches: `cancelled`, `expired`, `rejected`, `blocked`,
`failed`. A completed intent can only return its prior result on retry; it
cannot execute a second merge.
