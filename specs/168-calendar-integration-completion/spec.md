# Feature 168: Завершение календарной интеграции GRAF

**Статус:** implementation in progress; provider truth, home upcoming and final browser/embedded visual validation are being closed. External OAuth rollout remains blocked by explicit launch gates.
**Risk lane:** high-risk product area / significant cross-module feature.
**Depends on:** 060-calendar-context-ingestion, 063-calendar-settings-ui,
098-calendar-auto-context-match, current RLS/deletion baseline.

## Executive intent

Make calendar integration truthful and complete across the browser cabinet,
embedded macOS cabinet, server API, provider runtime, sync lifecycle, desktop
prompts and deletion semantics. Preserve the existing read-only, server-owned,
fail-closed and manual-recording boundaries. Add Google Calendar only after a
real authorization → calendar selection → sync → preview → disconnect flow is
available and evidenced.

This feature is not a rewrite of 060/063/098. Existing contracts, models,
normalizers, matcher, lifecycle helpers, fixtures and UI patterns are the
default implementation surface.

## Clarifications

### Session 2026-08-20

- Q: Which Google access and future participant-delivery boundary is approved? → A: Use `openid`, `calendar.events.readonly` and `calendar.calendarlist.readonly`; no Gmail access or calendar writes. A later sharing feature may let the owner manually send a GRAF-hosted secret link to selected attendees, with owner-configured read-only sections; the link opens without registration and may be saved under «Поделились со мной» after sign-in.
- Q: What does disconnect mean across calendar providers? → A: Stop sync, purge GRAF-owned credentials and future cache immediately, retain meeting-owned context under meeting retention, retain content-free lifecycle metadata for 30 days, never call the provider revoke endpoint, show only «Календарь отключён от GRAF.» after success, and provide no external-revoke link.
- Q: Which providers may expose a connect action? → A: Only providers that pass the complete real browser/macOS connection, catalog, selection, sync, reconnect and disconnect matrix. Every unverified or failing provider is non-interactive and labeled «Скоро».
- Q: How is Google Calendar rolled out after launch gates? → A: Enable it for all users at once after every external, security and E2E gate passes; retain one rollback flag to disable new connections globally.
- Q: What sync window and selection limit are approved? → A: Seven days before now through 365 days after now, only selected calendars, zero selection allowed, maximum 20 selected calendars, no silent truncation when the provider volume budget is exceeded.

## Actors and goals

| Actor | Goal |
|---|---|
| Calendar owner | Connect a provider, understand its state, select calendars, sync, and disconnect with confidence. |
| GRAF server | Own credentials, fetch read-only calendar data, maintain tenant-scoped state, and fail closed. |
| Browser cabinet user | Complete the same flow in `/settings/integrations/calendar`. |
| Embedded macOS user | Complete the same server-backed flow at `/desktop/settings/integrations/calendar` without losing native Record/Stop. |
| Desktop capture runtime | Use only a fresh, authorized, safe calendar context for prompts/matching; never let calendar state gate capture. |
| Workspace/admin policy | Restrict provider access and expose safe, actionable policy errors. |
| Support/operations | Diagnose state with metadata-only events, without event content or credentials. |

## User stories and priority

### US1 (P0): Trustworthy connection state

As an owner, I can start, cancel, complete, retry and fail a calendar
connection and always see one durable result. A connection is not reported as
successful until credentials are validated and the provider account/calendar
catalog is obtained, or the provider-specific contract explicitly defines a
safe pending state.

Acceptance: the primary action has loading/disabled state; cancel does not
create a source; success, denial, validation and provider failure are visible
next to the action and survive reload; no source is created on failed
validation; browser and embedded routes project the same server truth.

### US2 (P0): Real provider sync

As an owner, I can see whether a selected calendar has never synced, is queued,
syncing, synced, stale, rate-limited, credential-failed or unavailable. Manual
sync is idempotent and starts an actual provider read, not only a local state
transition.

Acceptance: a successful sync creates/updates normalized snapshots and a
sync cursor; pagination and deletes are handled; a failed provider call leaves
the source fail-soft and capture usable; no sync starts for a disconnected or
policy-disabled source.

### US3 (P0): Safe disconnect and deletion truth

As an owner, I can cancel or confirm disconnect and understand what GRAF will
stop, purge and retain. After confirmed success the source is
absent from active projections after reload, credentials are unavailable to
runtime, future cache does not contribute, and a second sync attempt is
fail-closed.

Acceptance: server response commits atomically; cleanup is idempotent;
credential envelope becomes a non-readable tombstone (or is deleted when
policy permits); future snapshots, participants, conference candidates,
reminder state and unconsumed match attempts are purged; consumed meeting
context follows meeting retention and remains visibly marked as unavailable,
not silently reattached.

### US4 (P1): Calendar selection and settings parity

As an owner, I can select zero, one or many calendars, cancel unsaved changes,
save, reload and manually sync. Preferences for prompts and event filters are
server-owned and identical in browser and embedded cabinet.

Acceptance: the selected count and state are truthful; zero selection keeps the
source connected but produces no upcoming events/prompts; selection survives
reload; errors do not discard the last committed selection; native manual
Record/Stop remains available in every calendar state.

### US5 (P1): Safe calendar context and reminders

As a recorder, I may receive a safe join or record suggestion and may continue
without calendar context. Calendar data never silently starts recording,
changes active context, grants access, sends messages or mutates the provider.

Acceptance: single, overlap, back-to-back, recurring, private/free-busy,
all-day, stale, offline and missing-link cases follow explicit state rules;
context snapshots remain stable after provider mutation; browser and embedded
review have the same owner authorization and no-content projection.

### US6 (P1): Google Calendar read-only integration

As an owner, I can authorize Google Calendar with a server-side OAuth code
flow, select readable calendars, sync events, see Google Meet conference
metadata safely, reconnect after expiry/revocation and disconnect with the same
truthful lifecycle.

Acceptance: the complete flow passes with a dedicated synthetic/test account;
the implementation uses the approved minimal scope set, exact redirect URI,
state/CSRF validation, server-owned refresh token and no desktop credential;
no claim of production support is made until launch gates pass.

### US7 (P1): Upcoming meetings in the macOS menu bar

As a recorder, I can click the GRAF menu-bar icon and see a short, current
list of upcoming calendar events without opening a full calendar grid. The
surface explains when data is unavailable and gives me a direct path to GRAF
meetings and calendar settings.

Acceptance: the native tray uses the existing authenticated desktop calendar
endpoint; it shows loading, empty, sign-in, stale and unavailable states; it
sorts and bounds safe event projections; it never shows unsafe titles or raw
provider payloads; an explicit click may open a server-approved HTTP(S)
meeting link but never joins automatically; the tray never starts/stops
recording; browser, embedded cabinet and tray reflect the same server truth.

### US8 (P1): Upcoming meetings and coherent calendar IA

As a user opening `Мои встречи`, I see an authoritative, compact upcoming
calendar section above meeting history. From there I can understand empty,
updating, stale and current states and open calendar settings. The settings
screen presents connected sources first, then display/reminder behavior, then
available provider connection choices and finally advanced privacy/support
details.

Acceptance: browser and embedded home render the same safe projection and do
not invent events; the section is collapsible but initially visible; it honors
time/title preferences and user timezone; provider cards never offer a connect
action without a working runtime adapter; queued/syncing actions are disabled;
every modal has native validation, visible busy state, safe result and focus
return; no private event content enters screenshots/evidence.

## Functional requirements

### Connection and API

- **FR-001** The server shall expose one authoritative connection projection
  containing connection state, credential state, sync health, selected count,
  catalog availability, safe error code and timestamps.
- **FR-002** A connection request shall validate provider/auth mode/required
  fields before persistence and shall not echo credential input in responses,
  logs, analytics or evidence.
- **FR-003** A provider is `connected` only after provider validation and
  calendar catalog discovery succeed. A separate `pending`, `needs_action` or
  `catalog_unavailable` state must not be labeled connected.
- **FR-004** All mutations require the existing authenticated tenant scope,
  owner policy and CSRF protections; unknown or foreign source IDs fail closed
  without existence leakage.
- **FR-005** Browser and `/desktop` routes shall use the same API/service
  transitions and response semantics; embedded navigation may differ only in
  shell, not in calendar truth.
- **FR-006** Connect, sync, selection and disconnect operations shall be
  idempotent under retries and concurrent duplicate submissions.

### Sync and provider runtime

- **FR-007** A queued sync shall be consumed by an explicit worker/job path that
  reads the sealed credential server-side, calls the provider adapter and
  applies normalized results through the existing sync helper.
- **FR-008** Adapters shall return provider-neutral calendar catalog and event
  contracts, including stable IDs, version/etag, status, time zone, all-day,
  recurrence and privacy metadata, bounded conference identity and safe
  participant metadata.
- **FR-009** Sync shall support full initial load, pagination, incremental
  cursor/token updates, provider deletions/cancellations and full-resync when a
  cursor is invalid.
- **FR-010** Sync shall classify timeout, invalid credential, revoked access,
  unavailable provider, rate limit, malformed payload and policy denial into
  safe problem codes with retry/backoff guidance.
- **FR-011** A stale or failed source shall not block meeting creation, manual
  recording, upload or stop. It shall suppress automatic calendar matching when
  freshness policy requires fail-closed behavior.
- **FR-012** No calendar operation shall create/update/delete provider events,
  invitations, messages, attendees or conference rooms.

### Selection, preferences and UX states

- **FR-013** The catalog shall show readable/selectable/hidden/unavailable
  calendars distinctly and preserve zero selection as an intentional state.
- **FR-014** Selection save shall report `saving`, `saved`, `empty`, `failed`
  and `stale` states; reload shall show the last committed server value.
- **FR-015** Connect, sync and disconnect controls shall expose keyboard and
  screen-reader-visible busy/disabled/result state and maintain focus after
  modal close or error.
- **FR-016** Russian copy shall distinguish: request accepted, operation
  running, operation completed, action required, provider unavailable and
  operation failed.
- **FR-017** The settings surface shall keep visible copy that manual Record and
  Stop are always available and that calendar access is read-only.

### Disconnect and retention

- **FR-018** Confirmation shall state that future sync stops and already-created
  GRAF meetings remain. After successful disconnect the only result copy is
  «Календарь отключён от GRAF.»; the UI shall not offer provider-revoke guidance.
- **FR-019** On successful disconnect, source state becomes disconnected,
  credentials become non-readable/purged, selected count is zero, sync is
  `failed_closed`, and active projections omit the source.
- **FR-020** Unmatched future snapshots, participant rows, conference-link
  candidates, reminder rows and unconsumed attempts for that source are
  deleted or detached according to the lifecycle contract.
- **FR-021** Matched meeting context retains only the approved safe snapshot
  semantics; it is never refreshed from a disconnected provider and is
  accounted for by meeting deletion/retention.

### Context and desktop

- **FR-022** Matching shall use only selected, fresh, readable and eligible
  events; private/free-busy, all-day, cancelled, deleted, stale and ambiguous
  inputs fail closed according to the existing 098 contract.
- **FR-023** A join prompt may open an approved meeting URL only when the URL is
  safely classified; no raw URL, passcode or event body appears in copy,
  telemetry or evidence.
- **FR-024** Calendar resolution is non-blocking for capture; visible native
  Record/Stop and upload recovery remain available on all calendar failures.
- **FR-025** Browser and embedded meeting review shall expose identical owner,
  no-context, ambiguity, correction and clear semantics.

### Google Calendar

- **FR-026** Google authorization shall use the server-side OAuth 2.0 web-server
  authorization-code flow with a random state bound to the authenticated GRAF
  session and exact HTTPS redirect URI (localhost is test-only).
- **FR-027** Client ID/secret and refresh token shall be server-owned. The
  browser may receive only a short-lived provider flow redirect and safe
  result; macOS receives no provider secret.
- **FR-028** The initial catalog shall use `calendarList.list` with pagination;
  selected calendars shall be persisted by stable provider calendar ID.
- **FR-029** Events shall use `events.list` with a documented bounded horizon,
  stable query parameters, pagination and persisted `nextSyncToken`; 410
  invalidation shall trigger a full resync, not silent partial data.
- **FR-030** Event normalization shall preserve recurrence series/instances,
  time zones, all-day dates, cancelled instances, private/free-busy policy,
  bounded attendees and Google Meet conference presence without storing or
  displaying unnecessary content.
- **FR-031** 401/invalid-grant/revoked access shall enter reconnect-required;
  403/429 rate limits shall use bounded exponential backoff and a safe stale
  projection; other errors shall use retry classification.
- **FR-032** Google disconnect shall purge/disable refresh-token use before
  deleting future local cache, shall not call Google's revoke endpoint, and
  shall be safe if repeated. The same local-only disconnect policy applies to
  every calendar provider.
- **FR-033** Google launch is blocked until OAuth client, secret storage,
  redirect URI, consent/brand configuration, test account, policy/verification
  decision and E2E evidence are available.
- **FR-034** The macOS tray shall use `GET /api/v1/desktop/calendar/upcoming`
  with a bounded 15-minute-before/24-hour-after window, the existing desktop
  auth cookie and safe event projection; it shall not create a second calendar
  auth or persistence path.
- **FR-035** The tray shall expose loading, empty, sign-in-required,
  unavailable and stale states; stale data may remain visible but must be
  labeled as not freshly updated.
- **FR-036** The tray shall use `safeDisplayTitle()`, display only bounded time,
  link-presence and safe status metadata, and cap the rendered list at 12
  events.
- **FR-037** An explicit “Открыть встречу” action may open a validated HTTP(S)
  URL returned by the server; no tray action may auto-join, auto-record,
  mutate a calendar or control native Record/Stop.
- **FR-038** Tray actions “Открыть GRAF” and “Настройки календаря” shall route
  through the existing embedded cabinet/session bridge and preserve the same
  browser/embedded owner and tenant boundaries.
- **FR-039** Browser `/meetings` and embedded `/desktop/meetings` shall render a
  compact, initially expanded upcoming section from the existing authorized
  server projection, before meeting history. It shall expose connected-empty,
  selection-needed, updating, current and stale states without raw links or
  provider payloads.
- **FR-040** Home upcoming shall honor `show_upcoming_time`,
  `show_upcoming_title`, event filters and user timezone, cap the visible list
  at four rows and link to the existing settings route. It shall not duplicate
  provider auth, sync or persistence.
- **FR-041** Every provider presented as connectable shall resolve to a real
  validation and worker adapter. EWS and Bitrix24 remain visible only as
  non-interactive `Скоро` cards until dedicated read-only adapters
  and fixtures exist. All CalDAV aliases, including VK WorkSpace, shall reuse
  the existing CalDAV adapter.
- **FR-042** Calendar settings DOM and visual order shall be connected sources
  → display/reminder behavior → available provider catalog → preview/privacy/
  support details. Unavailable providers use progressive disclosure and never
  open an empty form.
- **FR-043** Sync is unavailable while already queued/syncing; reconnect is
  shown for credential/terminal failures; cancelled provider dialogs clear
  entered fields and restore focus; native invalid fields also produce an
  adjacent live status.
- **FR-044** Full sync shall cover seven days before the sync start through 365
  days after it, shall read only selected calendars and shall accept zero to 20
  selected calendars. Selection above 20 or a provider-volume budget overflow
  shall fail with an actionable safe result and never silently truncate data.
- **FR-045** A provider card shall expose an active connect action only after
  that exact provider passes the approved real browser and embedded macOS E2E
  matrix. Any unverified or failing provider shall be non-interactive and use
  the single label «Скоро». An explicit development/certification override may
  enable one configured provider locally for that matrix, but it shall not make
  the provider connectable in production or change the public readiness claim.

## Non-functional requirements

- **NFR-001 Security:** least privilege, server-owned secrets, encryption at
  rest, no secret egress, no raw provider payload in logs/evidence, CSRF and
  tenant/RLS isolation.
- **NFR-002 Privacy:** private/free-busy events are reduced to policy-safe
  metadata; attendee emails, titles, descriptions and raw links are never used
  as analytics dimensions or screenshots.
- **NFR-003 Reliability:** duplicate requests do not create duplicate active
  sources or concurrent syncs; provider failures are fail-soft to recording.
- **NFR-004 Observability:** record event type, provider family, operation,
  outcome, safe reason, duration bucket and retry count; never record token,
  URL, title, description, email or payload.
- **NFR-005 Accessibility:** keyboard-only flow, focus return, labels,
  `role=status`/live region for results, disabled controls during mutation,
  sufficient contrast, narrow viewport and dark/light theme support.
- **NFR-006 Performance:** connection result projection p95 ≤ 500 ms after the
  provider callback; catalog page p95 ≤ 1 s after cached provider response;
  manual sync acknowledgement ≤ 300 ms; context resolve remains within the
  existing 098 p95 budgets (resolve ≤ 200 ms, consume ≤ 50 ms). A warmed,
  repeatable local PostgreSQL benchmark shall enforce these thresholds without
  including provider network time in the acknowledgement measurement.
- **NFR-007 Operations:** sync jobs have bounded timeout, retry budget,
  backoff, dead-letter/terminal state and operator-safe replay; migrations are
  backward-compatible and rollback-described.

## Connection state machine

```text
absent -> connecting -> validating -> cataloging -> connected_selection_needed
                                  |-> needs_action
                                  |-> error
connected_selection_needed -> syncing -> synced
connected_selection_needed -> disconnected
synced -> syncing | stale | credential_failed | rate_limited | disconnected
any active state -> disconnecting -> disconnected
disconnecting -> error (with retry-safe cleanup status)
```

`connected` is a projection, not a synonym for “row exists”. A source row with
sealed credentials but no provider validation is never eligible for prompts.

## Sync state machine

```text
never_synced -> queued -> syncing -> synced
queued/syncing -> queued (idempotent duplicate)
syncing -> stale | credential_failed | provider_unavailable | rate_limited | failed
stale -> queued (manual/retry) | disconnected
cursor_invalid -> full_resync -> syncing
disconnected -> failed_closed (terminal until reconnect)
```

## Approved user flow and IA

1. Settings → Integrations → Calendars.
2. Connected sources summary: connection status, sync health, selected count,
   last successful sync and next safe action.
3. Add source: provider cards with method and read-only explanation.
4. Provider flow: modal/redirect → loading → provider result → catalog step.
5. Calendar selection: zero or more checkboxes, save/cancel, result region.
6. Upcoming preview: filtered safe events and overlap/no-context explanation.
7. Reminders: join/record toggles and privacy filters, with manual-recording
   boundary adjacent.
8. Source details: sync, reconnect/action, disconnect confirmation and
   retention explanation.

## Explicit out of scope

- Auto-join, bot participation, calendar-driven hidden recording or automatic
  recording start.
- Calendar writes, event edits, invitations, RSVP, messages, summaries,
  transcript delivery or attendee access grants.
- Gmail, Google Contacts, Google Meet account integration separate from reading
  `conferenceData`/Meet links in calendar events.
- Automatic participant delivery. A future separate sharing feature may send,
  only after an explicit owner action, a GRAF-hosted secret link through GRAF's
  own mail service. It does not add Gmail scopes to calendar connection.
- Attachment content, meeting content extraction, retrospective matching,
  cross-tenant calendar sharing and service-account domain-wide delegation.
- Production launch of Google Calendar before the listed launch gates pass.

## Dependencies, assumptions and decisions required

### External dependencies/blockers

- Google Cloud project with Calendar API enabled.
- OAuth web client ID/secret, exact production and test redirect URIs, secure
  server secret delivery and rotation procedure.
- OAuth consent/brand configuration, app verification/policy review decision,
  privacy policy/support URLs and a dedicated synthetic test account.
- Provider quota/rate-limit budget and a rollback flag.
- Disposable Postgres test database for integration evidence.

Current observed Google Cloud state on 2026-08-21: audience is External and In
production; the exact approved scope set is configured; branding is not yet
shown to users and Calendar data access remains unverified. This state does not
constitute Google approval or unrestricted production readiness.

### Approved product-owner decisions

1. Google uses only `openid`, `calendar.events.readonly` and
   `calendar.calendarlist.readonly`; calendar writes and Gmail access are not
   requested.
2. Disconnect purges GRAF credentials/future derived data, keeps content-free
   lifecycle metadata for 30 days, does not revoke provider-side access and
   uses the exact concise success copy from FR-018.
3. Only providers with complete real E2E evidence are connectable; every other
   provider is non-interactive and labeled «Скоро».
4. Google opens to all users simultaneously after every launch gate passes;
   the global rollback flag remains mandatory.
5. Full sync covers seven days back and 365 days forward, only selected
   calendars, zero selection allowed and no more than 20 selected calendars.

## Acceptance criteria

- **AC-001** Empty, cancelled, invalid and provider-denied connection paths do
  not create an active source and show a durable safe result.
- **AC-002** During each mutation, the initiating control is disabled and has
  an accessible busy/status indication; success/error remains after redirect or
  fragment replacement.
- **AC-003** A successful source is backed by provider validation/catalog data;
  reload shows the same source and selected calendars.
- **AC-004** Manual sync results in an actual provider adapter call in E2E
  fixture/runtime evidence and updates event snapshots/cursor or a safe error.
- **AC-005** Disconnect confirmation can be cancelled without state change;
  successful disconnect removes the active card after reload, blocks further
  sync, purges credentials from runtime access and purges future cache.
- **AC-006** Existing matched context remains stable and clearly marked under
  retention policy; meeting deletion accounts for it.
- **AC-007** Browser and embedded routes produce the same state/result for all
  connection, selection, sync, disconnect and context cases.
- **AC-008** Native manual Record/Stop is available in connected, syncing,
  stale, error, disconnected and unavailable states.
- **AC-009** Google passes authorization, catalog, selection, full/incremental
  sync, pagination, recurrence/time-zone/cancelled normalization, Meet-link
  presence, expired/revoked reconnect and disconnect using synthetic data.
- **AC-010** No test/evidence/log contains real token, password, private event,
  participant email, raw meeting URL, passcode, transcript or audio.
- **AC-011** With the app running, the menu-bar icon opens a GRAF popover with
  the current bounded upcoming projection; loading/empty/error states are
  understandable without opening Settings.
- **AC-012** A tray refresh uses the same server truth as browser/embedded
  settings, does not leak event content into logs, and keeps native manual
  Record/Stop independent and available.
- **AC-013** A warmed disposable-PostgreSQL benchmark proves p95 ≤ 500 ms for
  post-callback/cached-catalog settings projection, p95 ≤ 1 s for the cached
  catalog surface and p95 ≤ 300 ms for manual-sync acknowledgement without
  waiting for provider I/O.

## Definition of done

The feature-gated implementation may be reviewed now with synthetic fixtures.
Google/provider rollout and any production claim remain blocked until the
approved decisions above are implemented, external OAuth dependencies are
approved, every connectable provider passes its real E2E matrix, and the
implementation quickstart passes with dedicated provider test accounts.
