# Data Model: Safe Browser Login Returns

## Persistent records

No database migration is required. This feature reuses the existing records.

| Record | Existing fields used | Feature rule |
|---|---|---|
| `AuthCallbackState` | `workspace_id`, `requested_redirect`, `state_nonce`, `expires_at`, `used_at`, `result` | `requested_redirect` remains the server-side candidate bound to one callback/code state. Email verification must use it rather than a later form value. |
| `AuthSession` | `id`, `workspace_id`, `user_id`, `device_id`, `status` | The issued session identifies the user and workspace under which a detail return is evaluated. |
| `Workspace` | `id`, `organization_id` | Supplies the organization component of the authenticated RLS context. |
| `Meeting` | `id`, `workspace_id`, `created_by_user_id`, `visibility`, `deletion_state` | Is read only for an exact requested detail route; no review, media, transcript, or egress data is loaded for redirect resolution. |
| `WorkspaceMembership` and `MeetingShareGrant` | existing active membership and grant fields | Are evaluated only through the existing `decide_meeting_access` policy. |

## Transient completion context

The resolver receives an in-memory completion context after authentication. It
contains organization ID, workspace ID, user ID, auth-session ID, and the
trusted requested redirect. It is neither stored as a new record nor sent to
the browser as a new API shape.

| Input class | Trusted source | Why it is needed |
|---|---|---|
| External-provider completion | callback state and resolved callback profile | Selects the browser destination after provider state, browser nonce, and session checks have succeeded. |
| Email login/registration completion | consumed `AuthCallbackState` and issued email session | Ensures the code state, not a resubmitted form field, supplies the destination. |

## Destination state machine

```text
captured local candidate
        |
        v
new session established and callback/code state consumed
        |
        +-- exact regular/embedded meeting detail --> access decision
        |       +-- can view --> preserve detail candidate
        |       +-- unavailable --> matching meeting list
        |
        +-- other existing safe local path --> existing behavior
        +-- absent/non-local candidate --> existing non-browser callback behavior
```

## RLS and privacy invariants

- The resolver explicitly applies `TenantDatabaseContext` with the completed
  organization, workspace, user, and auth-session IDs before reading a
  meeting. It must not rely on the callback/bootstrap context, which is not an
  authorized meeting-read context.
- The resolver returns only a local route. It does not return a meeting title,
  access reason, owner, workspace name, transcript, media reference, or share
  state.
- The fallback list route is `/meetings` for the regular surface and
  `/desktop/meetings` for the embedded surface.

## Diagnostic data boundary

Request diagnostic events retain only correlation and operational metadata.
They must not contain a raw query, request headers, cookies, authorization
values, provider tokens, callback state, session token, transcript, or meeting
content. This changes event contents, not the database schema or retention
policy.
