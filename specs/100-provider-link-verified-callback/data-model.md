# Data Model: Provider Link Verified Callback

## Existing table extended: `workspace_provider_link_states`

The existing table remains the sole link-intent and pending-candidate record.

| Field | Rule |
|---|---|
| `workspace_id`, `initiating_user_id` | Set from the authenticated current principal; never accepted from a candidate payload. |
| `initiating_auth_session_id` | New required foreign key to the current active `auth_sessions` row. Confirmation requires this exact session. |
| `source_provider_identity_id` | Derived server-side from the current session/user; never changes the primary identity. |
| `candidate_provider` | New provider label derived from the selected server route. |
| `callback_state_id` | New unique foreign key to `auth_callback_states`; binds this intent to one callback nonce without putting linkage in a redirect. |
| `candidate_identity_subject`, contact/display claims | Nullable pending data written only after adapter verification. Present only for `callback_verified`; cleared for all terminal/expired states. |
| `target_provider_identity_id` | Set only after confirmation creates or finds the same user's `ExternalIdentity`. |
| `status`, `resolution`, timestamps | Lifecycle and safe reason code. Terminal states are `confirmed`, `conflict`, `rejected`, or `expired`. |
| `expires_at` | Same 15-minute lifetime as callback state; all callback/confirm actions reject expiry. |

## State transitions

```text
initiated --verified callback--> callback_verified --bound confirm--> confirmed
    |                                  |                        |
    +--denied/error/expiry------------> rejected / expired       +--claims cleared
                                       +--foreign identity------> conflict (claims cleared)
```

Callbacks and confirmations are one-time. A repeat of the same terminal intent performs no identity mutation. A fresh intent for an identity already owned by the same user is a safe idempotent `confirmed` result.

## Invariants

- `ExternalIdentity(provider, provider_subject)` remains globally unique.
- Only an adapter-verified callback writes a candidate subject or claim.
- A confirmed link points to an identity owned by `initiating_user_id`.
- Provider contact claims are never a lookup/merge key for this flow.
- RLS request context exposes a row only to its initiating user/workspace; callback lookup additionally requires the exact bound callback nonce.
- Any read or mutation observing expiry atomically marks the state expired and clears candidate claims; an idempotent maintenance command cleans abandoned expired rows.
