# Browser Authentication Return Contract

## Scope

This contract applies when a supported external provider, email login, or email
registration completes a browser cabinet sign-in. It does not change native
API callback responses without a safe browser return, provider-link callbacks,
meeting access policy, or desktop client permission behavior.

## Inputs and trust boundary

| Input | Source | Trust rule |
|---|---|---|
| Requested return candidate | `AuthCallbackState.requested_redirect` | It is captured at sign-in start after existing local-path validation and is bound to the one-time callback/code state. |
| Session identity | issued callback or email session | It is available only after callback/code validation, enrollment policy, and browser binding checks succeed. |
| Meeting access | existing `decide_meeting_access` under authenticated RLS context | It is the sole authority for whether an exact detail candidate can remain. |
| Verification-form `next` | browser form submission | It may support error-page presentation but never overrides the stored completion candidate. |

## Resolution behavior

| Candidate after existing local-path checks | Completed session can view target | Browser result |
|---|---:|---|
| `/meetings/<valid UUID>` | yes | 303 to the original regular detail path, including any existing safe query. |
| `/meetings/<valid UUID>` | no, missing, deleted, or no longer shared | 303 to `/meetings`. |
| `/desktop/meetings/<valid UUID>` | yes | 303 to the original embedded detail path, including any existing safe query. |
| `/desktop/meetings/<valid UUID>` | no, missing, deleted, or no longer shared | 303 to `/desktop/meetings`. |
| Exact detail shape with malformed identifier | n/a | 303 to its matching meeting list. |
| Other existing safe local path | n/a | Current behavior is preserved. |
| Absent or non-local candidate | n/a | Current non-browser/API callback behavior is preserved. |

The redirect decision happens after session creation. No branch may reveal
whether an unavailable meeting exists.

## Direct unavailable detail behavior

For an authenticated full-page cabinet request, both a missing/denied detail
and a malformed detail identifier produce:

- HTTP 404 with `text/html`;
- the normal cabinet shell for that surface;
- a neutral title and recovery copy;
- exactly one matching list action (`/meetings` or `/desktop/meetings`);
- no problem-document JSON, problem code, requested identifier, title, owner,
  workspace, transcript, media, or share detail.

HTMX/fragment requests retain their existing machine-readable 404 behavior so
that current asynchronous clients and playback terminal handling do not change.

## Callback diagnostics contract

Production Uvicorn runs without its access logger. Application request events
may contain only:

- request ID;
- HTTP method;
- UUID-templated path;
- response status;
- duration.

They must not contain raw URI query values, request headers, cookies,
authorization values, provider authorization material, callback state, session
tokens, media, transcript text, or meeting content. The structured event names
remain `request.start` and `request.end` for support continuity.
