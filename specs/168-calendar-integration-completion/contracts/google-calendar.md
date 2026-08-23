# Google Calendar contract

## Official API basis

- OAuth web server: <https://developers.google.com/identity/protocols/oauth2/web-server>
- Scopes: <https://developers.google.com/workspace/calendar/api/auth>
- Calendar catalog: <https://developers.google.com/workspace/calendar/api/v3/reference/calendarList/list>
- Event list: <https://developers.google.com/workspace/calendar/api/v3/reference/events/list>
- Sync: <https://developers.google.com/workspace/calendar/api/guides/sync>
- Event resource: <https://developers.google.com/workspace/calendar/api/v3/reference/events>
- Errors: <https://developers.google.com/workspace/calendar/api/guides/errors>
- Verification: <https://support.google.com/cloud/answer/9110914>

## OAuth flow

1. Authenticated GRAF owner chooses Google Calendar.
2. Server creates random state bound to session, provider, tenant, return path
   and expiry; redirect uses exact registered redirect URI.
3. Google returns authorization code or denial; server validates state and error
   before exchanging the code.
4. Server stores only sealed refresh-token material and safe account/scope
   metadata; access token remains short-lived runtime memory. The authorization
   request includes the documented `openid` identity scope in addition to the
   two read-only Calendar scopes. The server calls Google's OIDC userinfo
   endpoint with the short-lived access token, hashes only `sub`, and persists
   that hash as the provider account identity. It never stores the email, ID
   token or raw userinfo response.
5. Server lists calendars, then returns a safe catalog/selection screen.
6. Callback/result URL is PRG-clean; authorization code is not rendered to
   page resources or analytics.

## Approved scope

Candidate documented read-only scopes:

- `https://www.googleapis.com/auth/calendar.events.readonly` — view events on
  all calendars;
- `https://www.googleapis.com/auth/calendar.calendarlist.readonly` — see the
  list of subscribed calendars;
- `https://www.googleapis.com/auth/calendar.readonly` — broader read/download
  access to calendars.

The approved request is `openid`, `calendar.events.readonly` and
`calendar.calendarlist.readonly`. The broader `calendar.readonly` scope and all
Gmail/calendar-write scopes are excluded. Record granted scopes and handle
partial grants safely. Source and contract tests assert this exact allow-list,
and the successful local OAuth callback granted only these three scopes.

## Catalog and event reads

- `calendarList.list`: paginate until `nextPageToken` is absent; persist stable
  calendar ID, summary/label only where policy allows, access role and
  primary/selected state.
- `events.list`: use seven days before sync start through 365 days after sync
  start for full sync; read only selected calendars, allow zero selection and
  reject selection above 20 with a safe actionable result. Paginate each page
  and never silently truncate a provider-volume overflow.
- Persist `nextSyncToken` only from the final page. Include deleted entries on
  incremental sync so local copies can be removed/marked deleted.
- On HTTP 410/cursor invalidation, clear provider event cache for that calendar
  and run a full sync. Do not show the old cache as current.
- Use `showDeleted`/`singleEvents` and other parameters only as allowed by the
  corresponding Google list contract; document the exact query in tests.

## Normalization

| Google data | GRAF behavior |
|---|---|
| `start.date`/`end.date` | all-day state; excluded from prompts by default |
| `start.dateTime`/`end.dateTime` + `timeZone` | normalize to UTC plus original IANA zone |
| `recurrence`, `recurringEventId`, `originalStartTime` | preserve series/instance identity and moved/cancelled exceptions |
| `status=cancelled` | delete normal local copy; retain only required recurrence exception identity |
| `visibility=private`/free-busy policy | generic/redacted state; no title/roster/link |
| `attendees` | bounded counts/classification; never access grants or email dump |
| `conferenceData` / `hangoutLink` | detect Google Meet presence and store bounded hash/classification; never log raw URI/passcode |
| `etag`/`updated` | source version for idempotent upsert and audit metadata |

## Error/reconnect contract

- 401/invalid credentials: refresh once if safe; otherwise `credential_failed`
  / `reconnect_required`, no repeated blind retry.
- `invalid_grant` or revoked consent: disable sync and require new OAuth;
  preserve only safe local state until disconnect/reconnect policy runs.
- 403/429 rate limits: exponential backoff with jitter, bounded retry budget,
  `rate_limited` and stale/fail-closed matching.
- 5xx/network timeout: bounded retry, then `provider_unavailable`/stale.
- malformed/unexpected payload: `invalid_payload`, quarantine operation, no
  partial success claim unless every page applied atomically by the adapter.
- Disconnect never calls Google's revoke endpoint. It stops new jobs, purges
  the local envelope before future-cache cleanup and leaves any provider-side
  grant outside GRAF unchanged.

## Launch gates/blockers

- Google Cloud project/API enabled.
- Server-owned client secret delivery and rotation.
- Exact test/production redirect URIs.
- Consent/brand/privacy/support configuration.
- Scope classification and OAuth verification/brand verification decision.
- Dedicated test account with synthetic calendar data and revocation control.
- Quota/rate-limit budget, global launch flag and rollback owner.
- Real E2E evidence for authorize/catalog/select/sync/preview/local disconnect.

## Provider/runtime readiness matrix

| Capability | Current implementation | Evidence class | Launch state |
|---|---|---|---|
| OAuth authorization-code flow | Server route, state/redirect validation and PRG result; local authorization and callback passed | Observed local runtime + synthetic/unit | Production launch remains gated by verification, secret rotation and production callback/brand inventory |
| Server-owned token custody | Encrypted credential envelope; access token runtime-only | Synthetic/integration | Ready for gated test environment |
| Calendar catalog | Paginated adapter and selected-catalog reconciliation | Synthetic/unit | Ready for gated test environment |
| Full/incremental event sync | Pagination, cursor, 410 reset, cancelled/recurring/all-day/time-zone normalization; real incremental persistence boundary repaired | Observed local full/incremental runtime + synthetic/unit/integration | Deterministic 410 full-resync passes disposable PostgreSQL; dedicated account must still prove revoked access and reconnect |
| Rate limit/revoked-access recovery | Safe error mapping, refresh/reconnect and bounded retry contract | Synthetic/unit/integration | Dedicated account must prove revoked access/reconnect; live 429 is required only with an approved controlled quota test |
| Google end-to-end | Local account completed OAuth, catalog, explicit selection, full/incremental sync, redacted upcoming projection, local-only disconnect and reconnect | Observed local runtime | Launch blocker until verification, secret rotation, dedicated test-account certification and rollback evidence |
| Production rollout | No OAuth verification, rollout owner or rollback receipt | Not proven | Launch blocker |

An implemented adapter and a local account receipt do not make the provider
production-ready. The production UI must remain gated until the external gates,
dedicated test-account certification and rollout/rollback receipts exist.
