# Research: Provider Link Verified Callback

## Decision 1: reuse the existing short-lived link-state model

**Decision**: Extend `WorkspaceProviderLinkState` instead of adding a second intent/candidate subsystem.

**Why**: The existing model already has workspace, initiating user, source and target identity, candidate fields, terminal status, expiry, and an RLS policy. The feature adds only the missing server-side bindings: `candidate_provider`, `callback_state_id`, and `initiating_auth_session_id`. The callback relation allows an RLS rule to prove that a callback nonce can access only its own intent.

**Rejected**: Reusing client-supplied candidate fields as proof. Those fields are now written only by the verified provider callback. The deprecated direct endpoint remains a safe `409` compatibility guard.

## Decision 2: keep login and link callback resolution separate

**Decision**: Dispatch link callbacks to a dedicated resolver after the shared provider adapter verifies the callback; never send them through `resolve_callback_to_user`.

**Why**: The login resolver may create users, identities and sessions. A link resolver must only consume its state, verify the provider response, store a pending candidate, and redirect to a local confirmation page. It never returns a session token or provider subject to the browser.

## Decision 3: explicit confirmation is a bound POST

**Decision**: Confirm with an authenticated, CSRF-protected `POST` that accepts only an opaque link-state identifier.

**Why**: The server can require `auth_via_session`, the same session ID, user, and workspace that started the flow, then load the verified candidate from the database. A GET redirect and a request containing identity claims are not proof of the current GRAF account or provider identity.

## Decision 4: conflicts and idempotence are intentionally distinct

**Decision**: A new verified intent for an identity already owned by the same user completes idempotently; replaying the same terminal callback or confirm does not create another identity. An identity owned by another user produces a generic conflict with no owner disclosure and never transfers or merges it.

## Decision 5: minimum UI is one shared Settings surface

**Decision**: Add a "Способы входа" Settings card and a server-rendered provider-link page. The embedded desktop cabinet uses the same templates, routes and CSRF conventions; no Swift UI is added.

**Why**: This is the existing calendar-settings pattern and prevents divergent browser/desktop auth behavior. UI displays a provider label and safe status only—never a provider subject, contact claim, nonce or token.

## Decision 6: retention and audit are fail-closed

**Decision**: Candidate claims exist only while the intent is `callback_verified`; confirmation, rejection, conflict and expiry clear them. Audit records provider, lifecycle event, safe fingerprint and reason code, but never raw claims, callback state, authorization code, token or cookie.

## Decision 7: RLS has an explicit callback path

**Decision**: The migration extends the existing owner-scoped policy with a narrow callback-lookup clause: it may access a link state only when its `callback_state_id` resolves to the exact `rec_auth_callback_state_nonce()`.

**Why**: A public callback has no user session yet. Broad callback context or a post-hoc RLS bypass would allow cross-intent access and risks a production 500. Postgres integration tests must prove both the permitted row and a foreign nonce return no row/update.

## Decision 8: expiry scrub has online and operational paths

**Decision**: Every callback, confirmation and Settings read expires and scrubs an overdue pending candidate in its own transaction. A narrow idempotent maintenance command provides bounded cleanup for abandoned rows before release/operations; it clears claims and records only safe terminal status.

**Why**: The short callback TTL makes stale candidates unusable, but privacy requires raw callback claims not to wait indefinitely for the user to revisit the page. Reusing the hardened maintenance runtime avoids adding a scheduler or a second persistent service.

## Decision 9: schema rollback preserves the safe baseline

**Decision**: The migration is additive and reversible: downgrade removes only new bindings/indexes/policy clauses after ensuring no pending candidate remains; the existing table and the direct-link `409` compatibility guard remain intact.

**Why**: If a callback regression is detected, deploy rollback must return to the previously released safe rejection behavior, not revive raw-subject linking.
