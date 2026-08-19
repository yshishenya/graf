# Contract: email auth completion and recovery

## Ordinary email login

| Condition | HTTP/user result | Persistent result |
| --- | --- | --- |
| Valid code, one user | `303` to state-bound first-party destination | One active session; callback `completed` |
| Invalid/expired/replayed code | Localized `400` | No new session; callback terminal at most once |
| Completion failure | Safe server error/retry path | Whole transaction rolled back; no orphan session |

The callback workspace and issued session workspace may differ. The callback is
always completed by exact nonce, never by widening target workspace access.

## Ambiguous unauthenticated email

- Do not issue a session or select an account.
- Explain in Russian that several accounts were found and another existing
  sign-in method is required.
- Render configured active Яндекс ID/VK actions through the existing provider
  registry and preserve safe `next`.
- Do not expose account IDs, counts of meetings, provider subjects or private
  profile data.

## Authenticated email linking

| Other active users after excluding current | Outcome |
| --- | --- |
| 0 | `identity_linked` |
| 1 | `merge_preview_ready` or `merge_blocked`; never automatic completion |
| >1 | `ambiguous_email_recovery_required` |

Every terminal result consumes the exact email callback once. A merge preview
does not itself move user data.

The preview states that the authenticated current account remains the survivor,
summarizes preserved sign-in methods/data classes and separate workspaces, and
explains session/device revocation and blockers without exposing raw identifiers.

## OAuth provider-link sibling

When provider confirmation discovers an identity owned by another account,
merge work may switch to `AccountMergeTenantContext`. Merge changes are flushed
there; the original provider-link state is scrubbed/finalized only after an
allowed workspace auth context is restored.

## Invariants

- Forced RLS remains enabled and enforced for the app role.
- CSRF, state, nonce, verified-email, rate-limit and safe-destination rules are unchanged.
- Web and embedded surfaces share outcomes and copy.
- Embedded email link and merge actions remain on `/desktop/...` routes.
- Existing successful Яндекс ID/VK login remains unchanged.
- Evidence contains synthetic identifiers only.
