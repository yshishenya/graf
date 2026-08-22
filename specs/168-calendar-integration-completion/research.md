# Feature 168 research and audit evidence

**Checked:** 2026-08-20 (Europe/Moscow)
**Evidence rule:** metadata-only. A real Google account was used only for local
OAuth/catalog/sync validation; no credential value, private event, attendee
identity, raw meeting link or audio was retained.

## Approved product decisions — 2026-08-20

- Google requests only `openid`, `calendar.events.readonly` and
  `calendar.calendarlist.readonly`; no Gmail or calendar-write permission.
- A future participant-sharing feature is separate from Calendar: after an
  explicit owner click, GRAF's own mail service sends only a secret GRAF link.
  The owner configures visible meeting sections inside GRAF; the link opens
  without registration and may be attached to «Поделились со мной» after sign-in.
- Disconnect is local to GRAF for every provider: stop sync, purge credentials
  and future cache, retain meeting-owned context, retain content-free lifecycle
  metadata for 30 days, and never call a provider revoke endpoint. Success copy
  is exactly «Календарь отключён от GRAF.» with no revoke link.
- A provider is connectable only after the full real browser/macOS matrix
  passes for that exact provider; otherwise its card is non-interactive and
  labeled «Скоро».
- Google opens to all users simultaneously only after every launch gate passes;
  one global rollback flag remains available to stop new connections.
- Full sync covers seven days back and 365 days forward, only selected
  calendars, zero selection allowed, maximum 20 selected calendars, and no
  silent truncation on volume overflow.

## Current implementation findings and closeout status

| ID | Symptom | Reproducibility | Actual path/root cause | Severity | Minimum correction | Evidence needed |
|---|---|---|---|---|---|---|
| F168-01 | Connect button gave no reliable indication that work is happening. | Reproduced before implementation; source and contract tests now cover the fix. | Provider forms lacked shared mutation state. `cabinet.js` now binds `data-calendar-mutation`, sets `aria-busy`, disables submit and exposes a live status. | P1 / fixed | Shared mutation-state behavior for provider connect, sync and disconnect; preserve native POST fallback. | 147 calendar contract/context tests plus browser modal/cancel observation; authenticated runtime still requires a session. |
| F168-02 | “Success” can mean only that a local source row was created. | Reproduced before implementation; fixed in source, synthetic tests and local Google runtime. | Connect now validates the provider and obtains a non-empty catalog before committing `CalendarSource`; validation failure leaves no source. | P0 / fixed | Keep provider validation/catalog atomic; do not claim production readiness from a local account. | 69 focused Postgres tests plus real local Google catalog receipt; no private content retained. |
| F168-03 | Manual sync appeared accepted but could remain queued. | Proven before implementation; fixed path is source-tested and observed with Google locally. | `request_source_sync` now has an explicit `calendar_sync_reconciliation` maintenance worker. The worker claims queued rows, applies tenant-scoped RLS, reads the sealed credential only server-side, and routes provider pages through `sync.py`. | P0 / fixed | Keep external provider evidence separate from production readiness. | Synthetic cursor/failure tests plus local Google queued→current receipt. |
| F168-04 | Disconnect semantics were hard to understand from UI. | Fixed in source, tests and real local Google runtime. | The committed lifecycle stops job claims, purges the runtime credential envelope, selections and future cache, detaches matched references according to retention truth, removes the source from both read models and returns the approved one-line result. Provider access is not revoked. | P1 / fixed | Preserve the local-only lifecycle and content-free tombstone semantics. | Real confirm/cancel, immediate removal, reload, no-runtime-credential, no-future-sync and reconnect receipts plus lifecycle tests. |
| F168-05 | Provider catalog suggested broad support that runtime did not prove. | Proven by source and synthetic adapter tests. | CalDAV and Google adapters now implement the provider-neutral contract; unsupported/provider-limited entries remain fail-closed and are not claimed as live. | P0 / partial | Mark unsupported providers unavailable or implement the smallest tested runtime slice; do not imply live support. | 17 provider/runtime tests plus focused contracts; no production provider E2E. |
| F168-06 | Google Calendar was absent as a calendar provider. | Source implementation and the complete local happy path now exist; production-wide access remains gated. | Feature-gated server OAuth callback, exact approved read-only scopes, token exchange/refresh, paginated catalog/events, full and incremental sync, cursor invalidation, normalization, reconnect and local-only disconnect are implemented; provider-side revoke is explicitly excluded. | P0 / gated | Keep Google behind launch gates until verification, secret rotation, dedicated test-account certification and rollout/rollback approval exist. | Local metadata-only authorize → catalog → select → full sync → upcoming → incremental sync → disconnect → reconnect passed; production verification remains open. |
| F168-07 | Empty/validation/error results use PRG safely but are shallow. | Error/result mapping and reload projection are source/test-proven; live provider error was not exercised. | `calendar_helpers.py` allow-lists result values and `view_models.py` projects authoritative source/sync/error copy; failed validation never projects a connected source. | P1 / fixed in tested path | Preserve safe PRG and add live provider evidence later. | Settings/provider failure tests and browser dependency blocker observation. |
| F168-08 | Browser and embedded routes may look different while sharing server handlers. | Code, contracts and local Google runtime show the same read model. | `/desktop` aliases reuse handlers; embedded shell/navigation is separately governed by macOS policies. | P1 / fixed for current slice | Keep parity assertions on both surfaces. | Browser and embedded current-sync/catalog/preview state matched; no private content retained. |
| F168-09 | Real provider HTTP failures could be mislabeled as generic transport failures. | Reproduced by code inspection; fixed and regression-tested. | `urllib` raises `HTTPError` for 401/403/429/410; the provider clients previously caught it as a network exception before the existing safe status mappers ran. | P0 / fixed | Preserve provider HTTP status at the transport boundary; map revoked, rate-limit and cursor-invalid states centrally without exposing response bodies. | 14 Google/CalDAV unit tests, including synthetic HTTPError status receipts. |
| F168-10 | A configured Google client still appeared unavailable in the settings dialog. | Reproduced in the configured local runtime before the repair. | Provider view-model payloads did not receive runtime OAuth availability, so the OAuth limitation copy was unconditional. | P1 / fixed | Pass a safe runtime-availability boolean through the existing provider preset payload; retain the blocker when configuration is absent. | Browser and embedded configured dialog observation; configured/unconfigured unit coverage. |
| F168-11 | Reconnecting the same Google account could create duplicate active sources or leave a terminal sync failure stuck. | Reproduced by tracing the callback into `connect_source`; fixed synthetically and exercised during local reconnect. | `connect_source` now reuses the active source matching the tenant, owner, provider and hashed account subject, replaces the sealed credential/catalog, preserves selected IDs and reopens `failed_closed` as `never_synced`. | P1 / fixed | Keep reconnect idempotent and reopen sync after credential replacement. | Disposable-Postgres callback regression plus local reconnect/catalog/sync receipt. |
| F168-12 | Upcoming events were absent from `Мои встречи` even though settings/API/tray had an authoritative projection. | Reproduced in the current browser home. | Feature 104 correctly removed a placeholder because the route had no projection; feature 168 now has one but did not wire it to home. | P1 / implementation added | Reuse the existing tenant-scoped settings preview on browser and embedded home; no new provider path. | Focused contract + browser/embedded desktop and narrow screenshots. |
| F168-13 | Calendar settings looked like one long engineering form. | Reproduced in current browser/embedded DOM and screenshot. | Connected source, 12-provider catalog, preferences, preview and trust text had weak progressive disclosure and user-goal grouping. | P1 / implementation added | Source first; group upcoming/prompt settings; available providers next; unavailable services and trust/support advanced. | Keyboard/AX order, desktop/narrow visual walkthrough. |
| F168-14 | EWS/Bitrix24 offered a connect dialog with no fields while VK WorkSpace failed worker adapter selection. | Reproduced in source and live DOM. | Preset `supported=True` was not coupled to adapter resolution; worker matched string prefixes instead of adapter metadata. | P0 / fixed in source | One provider metadata seam for connection/worker routing; unavailable cards for missing adapters. | Unit/contract/Postgres provider matrix plus visual catalog check. |
| F168-15 | Disconnect could wait behind a long provider read and stale sync work could approach persistence. | Reproduced by concurrency trace; regression test now passes. | Sync held/depended on source row state across provider I/O instead of re-validating only at persistence. | P0 / fixed | Mark syncing, release lock for provider I/O, then lock and fail closed before persistence. | Disconnect-vs-sync race test plus full calendar/Postgres selection. |
| F168-16 | Malicious or broken pagination could repeat forever; transient provider reads had no common bounded retry. | Proven by adapter inspection and synthetic doubles. | Page iteration trusted provider tokens and did not enforce one retry budget. | P1 / fixed | Maximum 20 pages, repeated-token rejection, three attempts with 0.5/1.5s jittered backoff. | Google/provider runtime pagination and retry tests. |
| F168-17 | Real embedded calendar settings showed a large blank column. | Reproduced visually in `GRAF Local.app`; fixed and rechecked. | Hidden legacy navigation stayed in the grid while content remained assigned to column two. | P1 / fixed | Collapse the existing settings grid to one column when the legacy node is present. | Computed-width check, unit contract and fresh WebView screenshot. |
| F168-18 | Resizing an already-loaded cabinet to 390px left the 176px rail expanded and only 214px for content. | Reproduced in current browser; fixed and rechecked. | Rail state was initialized once and did not react when its existing media breakpoint changed. | P1 / fixed | Subscribe to the existing breakpoint and collapse only when entering the tight layout. | 390x844 visual check, zero-overflow metrics and focused unit test. |
| F168-19 | Upcoming rows said a link existed but the visual flow did not prove an action to join. | Reproduced in the synthetic home fixture. | The product renderer already supported a safe open route, but the fixture had no sealed URL and the CTA copy was generic. | P1 / fixed | Reuse the internal open endpoint, show `Подключиться`, and prove it with a sealed synthetic sentinel. | Contract asserts CTA/internal URL and no sealed value egress; current screenshot inspected. |

## Proven-working areas (do not rewrite)

- Server-owned sealed credential envelope and stable encryption-key gate.
- Tenant-scoped models, migrations and RLS inventory for source, catalog,
  snapshots, participants, conference candidates, settings, audit and context.
- Normalized event model, privacy/title states, recurrence fields, hashed
  conference identity and safe participant counts.
- 098 deterministic match/attempt contract, idempotency, immutable matched
  snapshot and explicit no-context/ambiguous/private/all-day/stale outcomes.
- Disconnect lifecycle helper and meeting-deletion accounting, subject to the
  new explicit provider-runtime contract.
- Browser/embedded route aliases, CSRF, owner/membership policy and native
  manual Record/Stop boundary.
- Synthetic provider fixtures and macOS prompt/queue tests.

## Architecture trace

```text
Browser cabinet                  Embedded macOS cabinet
  GET /settings/...                GET /desktop/settings/...
  POST provider/connect            POST desktop provider/connect
  POST source/calendars            POST desktop source/calendars
  POST source/sync                 POST desktop source/sync
  POST source/disconnect           POST desktop source/disconnect
            \                         /
             shared FastAPI routes + TenantScope + CSRF
                              |
                 calendar service / view model / PRG
                              |
        CalendarSource, CredentialEnvelope, ExternalCalendar,
        EventSnapshot, participants, conference candidates,
        settings, audit, context link/attempt
                              |
  provider-neutral adapter + maintenance sync worker/job
                              |
              provider validation/catalog/events API
                              |
        normalized events -> existing sync/matching/read models
                              |
               desktop upcoming/prompts/context resolve
```

## Root-cause map

| Root cause | Downstream symptoms | Fix locus |
|---|---|---|
| Local row creation is called “connected” | false success, no catalogs, empty selection | provider connection service/state machine |
| No live provider evidence | external failure states and Google readiness cannot be claimed | provider runtime boundary + launch evidence |
| Loading helper is opt-in per form | no disabled state for high-impact actions | shared cabinet mutation behavior/template attributes |
| Disconnect cleanup is not projected as one operation | source/card ambiguity and unclear residue | disconnect contract + read model + committed result |
| Provider catalog is capability metadata only | UI overpromises support | provider readiness matrix/feature flags |
| Main meeting route never consumed calendar projection | upcoming existed only in settings/API/tray | reuse settings preview in meeting-list page render |
| Provider/runtime state did not control actions | duplicate sync and actionless dialogs | source view action state + non-interactive unavailable cards |
| Generic dirty-state rendering overwrote selection-limit feedback | mouse users saw only `Есть несохранённые изменения` after the rejected 21st choice | preserve the higher-priority live mutation message until the next input |
| Failed-closed sources could still project cached preview rows | stale meeting title/link appeared while credentials required reconnect | credential/provider failure takes precedence over cached preview on home |
| Calendar tests selected an unordered source calendar | full-suite-only `no_context`, 404 and stale mutation assertions | fixtures explicitly select a selected calendar; mutation follows the event's own calendar |
| 060/063/098 contracts were built on synthetic inputs | “implemented” status is mistaken for external E2E | evidence taxonomy and launch gates |

## Browser/runtime observations

The local server from the current worktree rendered the GRAF calendar settings
route. Before the provider-truth correction, browser and embedded checks opened
all listed provider forms, verified
cancel/focus return and native empty-field validation. A real local Google
account then completed OAuth, catalog discovery, explicit five-calendar
selection, full and incremental sync, metadata-only upcoming projection,
local-only disconnect and fresh reconnect; no event content was retained. The
same source truth was observed through both the browser and `/desktop` route.
A 390x844 viewport kept provider CTAs, sync/details actions and the
manual-recording boundary readable. Real disconnect removed the source
immediately and after reload, purged runtime credentials, selections and future
cache, stopped sync, and did not call provider revoke.
Provider failure/loading behavior remains additionally proven by
source/contract/provider tests, and production Google readiness remains gated.

The approved 2026-08-21 continuation changed production provider truth to fail
closed: all 12 provider families default to `Скоро` and expose no connect form
until their complete real browser + embedded matrix passes. An explicit local
development override enabled only configured Google for certification; it is
not a production readiness flag. Disconnect is local-only and does not call
provider revoke. Synthetic browser/embedded checks proved the approved one-line
result, card removal/reload, the 20-calendar limit by mouse and Space, and
failed-closed home projection without stale event actions.

## Test evidence and limits

- Final full calendar selection: **385 passed** on disposable PostgreSQL,
  including settings, sync, provider runtime, disconnect/deletion and context
  regressions.
- Google and CalDAV provider unit run: **16 passed** with synthetic HTTP
  doubles; no external account.
- Final fast CI unit run: **1138 passed**; Ruff and Python compile passed.
- Final focused macOS reminder/tray run: **24 passed**.
- Warmed cached-settings/manual-sync p95 regression: **2 passed** together with
  the existing safe-state/audit test; projection stayed within 500 ms/1 s and
  acknowledgement within 300 ms on disposable PostgreSQL.
- macOS calendar/capture focused run: **242 passed**; full macOS run: **693
  passed**, ContractValidation passed.
- Full disposable-Postgres baseline run: **3086 passed, 1 skipped**; strict
  RLS subset **42 passed, 1 skipped**; isolated containers were removed.
- Feature 168 contract/runtime additions: **26 passed**, including CSRF,
  ownership, idempotent disconnect, Google contract and provider failure states.
- Existing historical feature docs report larger green receipts, but they are
  feature-specific synthetic/release evidence and do not prove a live external
  provider adapter. They remain useful regression evidence, not Google
  readiness evidence.

## External Google sources checked

Checked 2026-08-19:

- [OAuth 2.0 for Web Server Applications](https://developers.google.com/identity/protocols/oauth2/web-server): authorization code, exact redirect URI, `state`, offline access/refresh token, granted-scope handling, error and redirect safety.
- [Choose Calendar API scopes](https://developers.google.com/workspace/calendar/api/auth): documented scope meanings, including `calendar.events.readonly`, `calendar.calendarlist.readonly`, and broader `calendar.readonly`.
- [Synchronize resources efficiently](https://developers.google.com/workspace/calendar/api/guides/sync): full initial sync, `nextSyncToken`, pagination, deleted entries and 410 full-resync behavior.
- [Events: list](https://developers.google.com/workspace/calendar/api/v3/reference/events/list): paginated event retrieval and list parameters.
- [Events resource](https://developers.google.com/workspace/calendar/api/v3/reference/events): recurrence, time zones, all-day date/time, cancelled instances, privacy and `conferenceData`/Google Meet metadata.
- [Handle API errors](https://developers.google.com/workspace/calendar/api/guides/errors): 401 credential recovery, 403/429 backoff and 410 cursor invalidation.
- [CalendarList: list](https://developers.google.com/workspace/calendar/api/v3/reference/calendarList/list): calendar catalog endpoint and authorization requirement.
- [OAuth App Verification Help](https://support.google.com/cloud/answer/9110914): sensitive/restricted scope verification and brand verification distinction.

## Competitive/reference check

Date of check: 2026-08-19. These are behavior/IA references only; no visual or
copy imitation is intended.

| Product/source | Observed behavior | Adaptable pattern | Not suitable for GRAF |
|---|---|---|---|
| [Krisp: Connecting your Calendar](https://help.krisp.ai/hc/en-us/articles/10277892556828-Connecting-your-Calendar-to-Krisp) | Public help article exists for connect and viewing/managing calendar. The article itself was anti-bot/JS gated in this environment, so interaction details were not independently verified. | Make connection and management a named, documented lifecycle; show what calendar enables. | Do not infer unverified behavior or copy Krisp copy/visuals. |
| [Fathom integrations](https://www.fathom.ai/integrations) | Public catalog groups integrations by category, plan and search; current page visibly lists conferencing and workflow integrations. Calendar-specific connect UX was not exposed on the public catalog. | Clear integration IA, search/filter and capability grouping. | GRAF needs source state/retention truth, not a marketing catalog alone. |
| [Fireflies supported calendars](https://guide.fireflies.ai/articles/4246295295-what-calendars-are-supported) | Public documentation states Google/Outlook support and explains account/calendar behavior; integration can lead to auto-join/record behavior and only one calendar per account in the article. | State provider coverage and account/calendar limits before consent; make the post-connect result explicit. | Auto-join and participant behavior are outside GRAF scope. |
| [Otter calendar connection](https://help.otter.ai/hc/en-us/articles/360048070154-Connect-your-Calendar-and-Contacts-to-Otter) | Documentation names Google/Outlook/iOS, explains Add → sign in → review permissions → connect, says events begin syncing, documents disconnect and primary-calendar limitation. | Permission review, explicit sync start, primary action and disconnect documentation. | Do not copy auto-record/auto-join promises. |

## Krisp desktop reverse-engineering note — 2026-08-20

The locally installed Krisp application was inspected read-only in its current
main window and Calendar settings. Private account/meeting content was visible
to the user-owned app but was not retained in GRAF evidence or screenshots. Its
calendar surface is an `Upcoming`/context layer, not a traditional grid. The
main window places a collapsible Upcoming block above meeting history with an
explicit empty state. Calendar settings show connected account status first,
then event filters and menu-bar time/title controls. This clear hierarchy is
the relevant pattern; bot/join automation is not.

GRAF adopts only the useful trust/IA pattern: a small upcoming surface above
meeting history and in the menu bar, explicit current/empty/stale state, one
connected-source status, grouped event display controls, a direct settings path
and a bounded event projection. GRAF deliberately excludes Krisp bot participation,
automatic joining, automatic recording, calendar writes and any provider
credential ownership in the desktop app. GRAF's explicit meeting-link button
is a user action, not an automation trigger. This is a behavioral reference,
not a visual or copy clone.
| [Read AI Google page](https://www.read.ai/google) and [connect help](https://support.read.ai/hc/en-us/articles/26340445031443-How-do-I-connect-my-calendar-to-Read) | Public page separates Google Meet, Gmail and Calendar capabilities, says calendar may be connected independently, and documents a policy/data-use link. | Explain integration boundaries separately and offer granular feature controls. | Gmail, scheduler, browser extension and bot behavior are not GRAF requirements. |

## Confidence labels

- **Proven in source:** current route/service/model/test behavior, the Google
  provider/runtime adapter and local-only disconnect boundary.
- **Proven synthetic:** existing fixtures/tests for normalization, lifecycle,
  matcher, privacy and macOS prompts.
- **Observed local runtime:** real Google OAuth/catalog/selection/full and
  incremental sync/upcoming/local disconnect/reconnect plus synthetic 20/21
  mouse and keyboard selection, failed-closed projection, embedded parity,
  dark/light and narrow viewport. This proves the local product path, not
  production-wide availability.
- **Not proven:** real Google 410 reset, revoked-access recovery and rate-limit
  recovery; dedicated provider test-account certification; production OAuth
  verification/publication; complete automated browser accessibility and
  foreign-tenant logout/login walkthrough evidence.
- **Latest external blocker:** Google Cloud still reports that OAuth app
  verification is required. Audience is External/In production and the exact
  approved scopes are configured, but branding is not shown and Calendar data
  access is unverified. Production-wide rollout also requires rotation of the
  previously exposed client secret, production callback inventory, dedicated
  test-account certification and approved rollout/rollback receipts.
