# Feature 168 implementation evidence ledger

Implementation is complete for the tested, feature-gated slice and remains
intentionally fail-closed for external provider gates. Production rollout was
completed for the server and UI surface; Google Calendar remains disabled in
production until its external verification and production E2E gates pass. No
issue sync was performed. One real Google account was used only for local
end-to-end validation; no account identity, token, event content or meeting
metadata was retained in evidence.

## Audit receipts — 2026-08-19

| Check | Result | Interpretation |
|---|---|---|
| Repository preflight | detached `e6315991`; feature 168 worktree intentionally dirty | User/feature changes preserved; feature 167 untouched. |
| Local browser settings route | current worktree server on `127.0.0.1:8092`; authenticated local session rendered browser settings, Google modal, disconnect confirmation and success result | OBSERVED-RUNTIME; local synthetic account only, no external provider. |
| macOS focused calendar/capture tests | 242 tests, 0 failures | PASS-SYNTHETIC; calendar, prompts, capture boundary and embedded handoff are healthy. |
| macOS full suite | 693 tests, 0 failures; ContractValidation PASS | PASS-SYNTHETIC; full package regression. |
| Server calendar/settings/provider focused run | 59 tests passed | Disposable Postgres plus synthetic provider fixtures; no external provider. Includes the synthetic Google OAuth callback, allow-listed scope persistence, identity hash and sealed refresh-token assertion. |
| Provider/runtime focused run | 16 tests passed | Synthetic HTTP/provider doubles; no external account. |
| Calendar contract/context focused run | Included in the 59-test focused run | Disposable Postgres, RLS/CSRF/no-secret contracts; no external account. |
| Google docs | official OAuth/scopes/sync/events/errors/verification pages read | Design basis only; not provider E2E. |
| Competitor references | Krisp, Fathom, Fireflies, Otter, Read AI public sources checked | Behavioral reference only; no copy/style reuse. |
| Google and CalDAV adapter unit tests | 16 passed | Synthetic HTTP only; no real token, account or event content. |
| Calendar worker unit tests | 2 passed | Provider selection/fail-closed only; no live worker process. |
| Full server/Postgres baseline run | 3086 passed, 1 skipped; strict RLS subset 42 passed, 1 skipped; isolated containers removed | PASS-SYNTHETIC; disposable Postgres, no external provider. |
| Full server/Postgres continuation rerun | 3088 passed, 1 skipped; strict RLS subset 42 passed, 1 skipped; isolated containers removed | PASS-SYNTHETIC after correcting two stale cross-feature contracts for the server-owned Google client secret and Google Calendar env keys; no external provider. |
| Final redirect/contract hardening | Google redirect unit subset 2 passed; canonical OpenAPI drift check passed; full server run found and then cleared the missing `external_revoke` schema field | PASS-SYNTHETIC; no external provider. |
| Provider HTTP status hardening | Google/CalDAV adapter unit suite 14 passed; `HTTPError` status is preserved for revoked, rate-limited and cursor/error mapping; provider response bodies remain unreturned | PASS-SYNTHETIC transport boundary; no external provider. |
| Feature 168 contract/runtime additions | 26 passed: CSRF/ownership/idempotent disconnect, Google contract, provider failure matrix, Google/CalDAV adapters | PASS-SYNTHETIC; no real tokens or calendar content. |
| Fast CI unit run | 1123 passed; Ruff and Python compile passed | Legacy-audio guard, unit suite, lint and compile passed; 2026-08-19 continuation rerun. |
| Browser current walkthrough | Authenticated current worktree at `127.0.0.1:8092`: Google modal opened; Continue produced the safe dependency blocker with no source; cancel/Escape returned focus to the CTA; 390×844 screenshot visually checked; zero-state and reminder boundary remained visible | OBSERVED-RUNTIME; synthetic local login only, no external provider or secret. Synthetic source/disconnect outcomes remain covered by the prior runtime walkthrough and automated lifecycle tests. |
| Provider-form walkthrough | All 12 listed provider forms opened and closed in the embedded route; empty Yandex submission stayed in the dialog with no source created; no provider secret or payload was emitted | OBSERVED-RUNTIME; current worktree, synthetic/local account, no external provider. |
| Synthetic browser E2E | Browser: synthetic CalDAV connect → one-calendar selection → queued manual sync → reload to synced state → future-event preview → disconnect cancel → confirmed disconnect → reload with zero sources | OBSERVED-RUNTIME; synthetic provider double, redacted runtime observation only; event content was not retained in evidence. |
| Synthetic embedded E2E | Embedded `/desktop/settings/integrations/calendar`: same synthetic source was reconnected, selection persisted, manual sync reached synced state after reload, preview became available, then disconnect removed the source | OBSERVED-RUNTIME; same server read model as browser, synthetic provider double, no external provider. |
| Embedded current walkthrough | Current `/desktop/settings/integrations/calendar` rendered the same provider list and zero-state; Google read-only/dependency modal opened; cancel/Escape restored focus to the Google CTA; manual Record/Stop boundary copy stayed visible; 390×844 layout visually checked | OBSERVED-RUNTIME; current worktree, synthetic local login only. |
| Browser/embedded accessibility probe | Both `/settings/integrations/calendar` and `/desktop/settings/integrations/calendar`: 12 provider buttons map to 12 labeled dialogs; all provider CTAs expose `aria-haspopup=dialog`; all status nodes expose explicit `aria-live=polite`; all mutation forms have a status target; Google dialog opens and Escape restores CTA focus | OBSERVED-RUNTIME DOM/AX probe; no private content, no external provider, no physical VoiceOver session. Contract test passed through disposable Postgres runner. |
| Browser narrow viewport | 390x844 settings screen kept provider CTAs, sync/details actions, readable copy and disabled auto-record boundary visible | OBSERVED-RUNTIME; visually inspected, then the generated browser artifact was removed rather than retained as evidence. |
| Browser cancel flow | Modal close restored focus to provider CTA; disconnect cancel closed disclosure without request | Current local runtime. |
| Logout/login boundary | Clean local runtime: browser logout returned `/login`; synthetic login through the visible OTP flow returned to the cabinet; calendar reload after re-login stayed at zero sources/calendars. Embedded clean runtime separately logged in through the native form and opened the same calendar settings read model at zero sources/calendars; manual Record remained available. | OBSERVED-RUNTIME; disposable local runtime only, synthetic identity/code, no provider grant or private calendar data. |
| Tenant boundary regression | Current-user calendar source isolation, unknown-source fail-closed actions, disconnect cleanup and calendar ownership checks passed in disposable Postgres: 4 integration tests plus 21 contract tests. | PASS-SYNTHETIC; strict tenant/RLS fixtures, no external provider. |
| Current calendar regression rerun | 83 integration/contract tests passed; Google/CalDAV/worker unit suite 18 passed; `infra/scripts/ci-local.sh --fast` 1121 passed. | PASS-SYNTHETIC; disposable Postgres and synthetic HTTP/provider doubles, no external account. |
| JS/HTML/static validation | `node --check`, Ruff and Python compile passed | Syntax/static only. |
| Forbidden-content scan | Detector-only matches for schema names (`access_token`, `refresh_token`, `contains_passcode`) | Manual review: no real values, raw payloads, private event content or tokens. |
| macOS tray native build | `swift build --package-path apps/macos --product TwoBrainRecApp`; signed local dev bundle built with loopback origin | PASS-SOURCE/OBSERVED-RUNTIME; no production bundle or release change. |
| macOS tray focused tests | `swift test --package-path apps/macos --filter DesktopCalendarReminderTests`: 23 passed | PASS-SYNTHETIC; tray ordering, safe projection and auth-state mapping covered. |
| macOS tray visual walkthrough | Opened the GRAF Dev menu-bar popover through the native app menu fallback; inspected empty and current-event layouts, refresh control, Russian copy, explicit link action, GRAF/settings actions and AX labels | OBSERVED-RUNTIME; event content was not retained, no auto-join/auto-record executed. |
| Final fast lane after tray slice | `infra/scripts/ci-local.sh --fast`: 1123 passed, 2 warnings; legacy-audio guard PASS; Ruff and Python compile PASS | PASS; fast lane intentionally skips full macOS validation, which was run separately as 244 focused macOS tests. |

## Latest continuation receipts — 2026-08-19

| Check | Result | Interpretation |
|---|---|---|
| Configured Google provider UI | After the runtime availability fix and local server restart, browser and `/desktop` settings showed the Google read-only dialog with `Продолжить в Google`; the dependency blocker was absent. | OBSERVED-RUNTIME; server-owned configuration was present, no secret or provider payload recorded. |
| Browser visual modal | Dark-theme screenshot inspected: provider purpose, read-only badge, server ownership, cancel and focused Google CTA were visible; cancel returned focus to the CTA. | OBSERVED-RUNTIME; visual/DOM check only, no private content. |
| Embedded visual modal | Same screenshot/DOM checks passed on `/desktop/settings/integrations/calendar`; manual Record/Stop boundary remained visible in the page. | OBSERVED-RUNTIME; browser and embedded surfaces shared the same server truth. |
| Historical first OAuth authorization attempt (superseded) | Google returned a sanitized `redirect_uri_mismatch` error for the local callback. | HISTORICAL BLOCKER; superseded by the later successful local OAuth/catalog/sync receipt below. |
| OAuth state/URL safety probe | Authorization URL reached Google with only expected query-key classes; raw state was not retained. | PASS-SOURCE/OBSERVED-RUNTIME; no token, email, event title or meeting content recorded. |
| Google reconnect idempotency | Disposable-Postgres synthetic callback test now proves two authorizations for the same hashed account subject leave one source, one envelope and the selected catalog calendar. | PASS-SYNTHETIC; no external account. |
| Google 403 quota mapping | Provider unit suite covers `userRateLimitExceeded` as retryable `rate_limited` and ordinary 403 as `provider_policy_denied`. | PASS-SYNTHETIC; response bodies remain private to the adapter. |
| Historical focused validation | Google/provider/settings selection: 17 unit/contract tests passed; Google callback/reconnect integration: 2 passed on an isolated disposable Postgres runner; lint/compile passed. | PASS-SYNTHETIC at that point; superseded by the later real Google matrix and 384-test calendar run below. |
| Persistence continuation rerun | `test_calendar_persistence.py`: 21 passed, 2 warnings; isolated Postgres runner removed its disposable container. | PASS-SYNTHETIC; selection, cursor/incremental sync, provider mutation and context stability remain green; no external provider. |
| macOS continuation rerun | Focused calendar/capture filter: 242 passed, 0 failures; `ContractValidation: PASS`. | PASS-SYNTHETIC; native Record/Stop boundary and embedded handoff remain green. |
| Google-configured local runtime | `127.0.0.1:8081` rendered the configured read-only Google dialog and emitted the OAuth authorization request; `127.0.0.1:8092` remains intentionally fail-closed because that process has no Google secret configuration. | OBSERVED-RUNTIME; no secret value or provider payload retained. |
| Historical callback probe (superseded) | Google rejected the first local authorization with `redirect_uri_mismatch`. | HISTORICAL BLOCKER; the local redirect was later registered and the complete local happy path passed. |

## Home/settings UX closeout receipts — 2026-08-20

| Check | Result | Interpretation |
|---|---|---|
| Focused calendar regression | 236 focused PostgreSQL contract, integration and unit tests passed; disposable container removed. | PASS-SYNTHETIC; source ownership, settings, provider runtime, sync, credentials and meeting-list projection are green. |
| Fast CI | `infra/scripts/ci-local.sh --fast`: 1130 passed; legacy-audio guard, Ruff and Python compile passed. | PASS; fast lane intentionally skips Swift and was followed by a focused macOS run. |
| Final macOS regression | Calendar settings, reminders and embedded shell filter: 40 passed, 0 failures. | PASS-SYNTHETIC; native Record/Stop remains independent of calendar state. |
| Home upcoming states | Browser and embedded home were inspected with synthetic current, empty, selection-needed, stale, syncing and credential-failure states. | OBSERVED-RUNTIME; no private title, attendee, URL or provider payload retained. |
| Historical provider truth (superseded) | Google, Yandex, Mail.ru and CalDAV aliases temporarily exposed working actions while EWS and Bitrix24 remained non-interactive. | HISTORICAL only; T062 supersedes this state. Current production defaults all 12 uncertified families to non-interactive `Скоро`; an individual provider may become connectable only after its own real browser/embedded certification. |
| Provider form behavior | Empty Yandex submit showed adjacent required-field status and moved focus; cancel cleared synthetic values and restored CTA focus. | OBSERVED-RUNTIME; no credential value retained in evidence. |
| Selection and sync | Zero/one/many selection behavior, reset, two-calendar save, accepted manual sync and duplicate-sync disabled state were inspected. | OBSERVED-RUNTIME synthetic fixture + PASS-SYNTHETIC persistence. |
| Preferences | Dirty state enabled Save/Reset; Reset restored values and pristine disabled controls; Save returned a focused `preferences_result=saved` status and pristine state after reload. | OBSERVED-RUNTIME; browser and embedded share the same server-owned form contract. |
| Disconnect | Confirmation copy, cancel, successful removal, reload persistence and zero-source result were inspected. | HISTORICAL OBSERVED-RUNTIME synthetic fixture + PASS-SYNTHETIC credential/cache/job cleanup; approved no-revoke copy/policy and real Google local disconnect require T059–T063 revalidation. |
| Responsive/theme/a11y | Settings, modal and home upcoming were inspected at desktop and 390x844 in light/dark themes; no horizontal overflow or button word-breaking; semantic labels/status/focus behavior remained present. | OBSERVED-RUNTIME DOM/visual review; no physical screen-reader session. |

## Real local Google continuation receipts — 2026-08-19

| Check | Result | Interpretation |
|---|---|---|
| OAuth authorization and callback | Local browser reached Google account chooser and consent screens, returned to GRAF with `connect_result=success`, and rendered one connected Google source. | PASS-OBSERVED-RUNTIME; one user-controlled local account, no identity or OAuth value recorded. Google still shows the app as unverified. |
| Google calendar catalog | GRAF rendered a catalog of 5 calendars; one calendar remained selected after reconnect and reload. | PASS-OBSERVED-RUNTIME; only counts/states were retained, never labels or event data. |
| Real Google sync lifecycle | Manual sync visibly moved from queued to an authoritative current state after reload. | PASS-OBSERVED-RUNTIME; server-owned credential decryption and provider calls completed locally; no event title, attendee, URL or raw response retained. |
| Browser and embedded parity | Browser and `/desktop` settings rendered the same connected source, selected-count and current-sync state. | PASS-OBSERVED-RUNTIME; shared server read model confirmed. |
| Calendar preview | Embedded page contained 2 preview rows, both `available/current`; inspection recorded only redacted state attributes. | PASS-OBSERVED-RUNTIME; no private event content or meeting link retained. |
| Disconnect trust UX | Historical confirmation disclosure explained sync stop, credential cleanup and meeting-context retention; cancel returned to the connected state without disconnecting. | HISTORICAL PASS-OBSERVED-RUNTIME; approved concise copy, no provider revoke and real local credential purge remain pending T059–T063. |
| Reconnect after terminal failure | Reconnect reset a stale `failed_closed` source to `never_synced`; targeted disposable-Postgres regression test passed. | PASS-SOURCE + PASS-SYNTHETIC; root cause fixed in shared `connect_source`, real account was then able to sync. |

## Final post-runtime receipts — 2026-08-20

| Check | Result | Interpretation |
|---|---|---|
| Embedded layout root cause | Fresh real `GRAF Local.app` WebView rendered calendar settings without the hidden legacy-navigation column; synthetic computed widths were 1040/1040 for settings/content with zero horizontal overflow. | OBSERVED-RUNTIME; shared CSS root cause fixed, no private event content retained. |
| Responsive loaded-page resize | An already-loaded desktop page resized to 390x844 collapsed from the 176px expanded rail to a 64px rail, leaving 326px content and zero horizontal overflow. | OBSERVED-RUNTIME + focused unit/JS syntax PASS. |
| Historical connect/disconnect/settings interaction | Browser modal, native empty validation, Escape/cancel focus return, disconnect confirmation/cancel, dirty/reset preferences and embedded filter disclosure were clicked in current runtime. | OBSERVED-RUNTIME at that point; confirmed real local disconnect was subsequently executed and is recorded below. |
| Home upcoming action | Synthetic event with a sealed URL rendered a visible `Подключиться` action through the existing authenticated internal endpoint; the sealed sentinel did not appear in HTML. | OBSERVED-RUNTIME + PASS-SYNTHETIC contract; no raw meeting URL retained. |
| Accepted screenshots | `output/playwright/calendar-168/01-calendar-settings-desktop.png`, `02-calendar-settings-narrow.png`, `03-upcoming-home.png`, `04-macos-calendar-settings.png` and `05-macos-calendar-preferences.png` were captured and visually inspected. | LOCAL AUDIT ARTIFACTS only; synthetic/browser or metadata-only settings state, no tokens, emails or private events. |
| Sanitized video proof | `output/playwright/calendar-168/06-calendar-flow.webm` records synthetic selection, unsaved state, save success, manual sync, upcoming navigation, disconnect cancel and confirmed disconnect. Codec/size check passed and sampled frames include the final exact success copy. | LOCAL AUDIT ARTIFACT only; production templates/assets with synthetic identity, calendars and events, no provider credentials or private content. |
| Full calendar/PostgreSQL selection | `bash apps/server/scripts/run_local_postgres_tests.sh -k calendar -q`: 379 passed, 2776 deselected; disposable container removed. | PASS-SYNTHETIC; calendar, settings, provider runtime, deletion and context regressions green. |
| Fast CI | `infra/scripts/ci-local.sh --fast`: 1138 passed; legacy-audio guard, Ruff and Python compile passed. | PASS; fast lane intentionally skips Swift. |
| macOS reminder/tray model | `swift test --package-path apps/macos --filter DesktopCalendarReminderTests`: 24 passed. | PASS-SYNTHETIC; reminders, overlap, safe projection, tray ordering/auth and manual action boundary green. |
| Real installed macOS surface | `GRAF Local.app` showed authoritative failed-closed provider copy, reconnect, disconnect, all preference groups and the native recording panel. Record was disabled only because OS microphone/system-audio permissions were not granted. | OBSERVED-RUNTIME; calendar state did not remove the native control, no permissions were changed. |

## Approved policy closeout receipts — 2026-08-21

| Check | Result | Interpretation |
|---|---|---|
| Local-only disconnect | Every disconnect path omits provider revoke, immediately purges the local credential envelope, blocks later sync and retains only bounded content-free lifecycle metadata. | PASS-SOURCE + PASS-SYNTHETIC; this does not claim that the grant was revoked at Google or another provider. |
| Disconnect trust UX | Browser and embedded synthetic surfaces showed the approved confirmation, cancel preserved the source, success removed the card, reload did not restore it and the result contained only `Календарь отключён от GRAF.` | OBSERVED-RUNTIME synthetic + PASS-SYNTHETIC lifecycle; subsequently repeated against the real local Google source below. |
| Provider truth | The production-default certification set is empty, so all 12 provider families fail closed as `Скоро`. An explicit local development override enabled only configured Google for the real certification walkthrough. | OBSERVED-RUNTIME + PASS-SOURCE fail-closed; the override is not production availability and T062 remains open. |
| Selection boundary | A 21-calendar synthetic catalog was clicked separately by mouse and Space: exactly 20 remain selected, the 21st returns unchecked, focus remains usable and the live status says `Можно выбрать до 20 календарей.` | OBSERVED-RUNTIME in the in-app browser + PASS-CONTRACT; no calendar labels or account data retained. |
| Home credential failure | Browser and embedded home were rechecked with a credential/provider failure and a cached synthetic preview: zero event rows and zero join actions rendered; only reconnect/manual-recording-safe copy remained. | OBSERVED-RUNTIME synthetic + PASS-SYNTHETIC; stale cached titles and links fail closed. |
| Canonical API contract | Runtime OpenAPI and the committed canonical contract now agree on provider availability, upcoming title/time preferences and the authenticated open-meeting endpoint. | PASS-SYNTHETIC; drift test passed on disposable PostgreSQL. |
| Deterministic calendar fixtures | Calendar context/deletion/disconnect/share fixtures now select an explicitly selected calendar, and provider mutation reloads the event's own calendar instead of relying on undefined PostgreSQL row order. | PASS-SYNTHETIC; removes false `no_context`, 404 and stale provider-state failures without changing product runtime. |
| Full calendar/PostgreSQL selection | `bash apps/server/scripts/run_local_postgres_tests.sh -k calendar -q`: 381 passed, 2776 deselected; disposable container removed. | PASS-SYNTHETIC; settings, credentials, local disconnect, provider runtime, deletion, context and RLS-adjacent regressions green. |
| Fast CI | `infra/scripts/ci-local.sh --fast`: 1138 passed; legacy-audio guard, Ruff and Python compile passed. | PASS; fast lane intentionally skips Swift. |
| macOS reminder/tray model | `swift test --package-path apps/macos --filter DesktopCalendarReminderTests`: 24 passed. | PASS-SYNTHETIC; reminder, overlap, tray projection and manual Record/Stop boundaries remain green. |

## Real local Google matrix — 2026-08-21

| Check | Result | Interpretation |
|---|---|---|
| OAuth and catalog | The local browser and embedded return path completed authorization-code consent with only the approved read-only calendar scopes. One active sealed source and five readable calendars appeared after callback. | OBSERVED-RUNTIME local test account; this is not production/all-users verification and no token, account identity or calendar label was retained. |
| Explicit selection and sync | The user explicitly selected all five available calendars, saved the choice and requested manual sync. The source moved queued → synced with no safe error; one credential envelope remained readable by runtime and three future snapshots were stored. | OBSERVED-RUNTIME local test account; selection was not restored from the disconnected source and no event content was retained. |
| Upcoming browser/embedded parity | `/meetings` and `/desktop/meetings` each rendered the labelled upcoming section with one row. Browser and embedded settings each showed one source, five of five selected calendars and an enabled `Синхронизировать` action after completion. | OBSERVED-RUNTIME; counts and state only, no title, URL, participant or provider payload retained. |
| Real local disconnect | Confirmation/cancel and confirmed disconnect were exercised. Success showed exactly `Календарь отключён от GRAF.`, removed the source immediately and after reload, purged the active credential and selected calendars, stopped future projection and retained only one past snapshot under retention. No provider revoke call was made. | OBSERVED-RUNTIME + metadata-only database receipt; local GRAF-side disconnect semantics proven. |
| Reconnect after disconnect | Reauthorization created a new active source. A new disposable-PostgreSQL regression proves that the disconnected source remains disconnected and the fresh source starts with zero selected calendars until the user saves a new selection. | OBSERVED-RUNTIME + PASS-SYNTHETIC; old selection/cache resurrection is guarded. |
| Incremental content boundary | A second real sync returned 550 changed events and reproduced SQLSTATE 22001 because 17 descriptions exceeded the existing 4000-character column. Shared normalization now bounds description/location, unexpected worker errors cannot remain `syncing`, and the identical provider run completed `synced` with no safe error. | OBSERVED-RUNTIME + PASS-SYNTHETIC; only field lengths/counts and exception class/state were retained, never content or DB parameters. |
| Full calendar/PostgreSQL selection | `bash apps/server/scripts/run_local_postgres_tests.sh -k calendar -q`: 389 passed, 2882 deselected; disposable container removed. | PASS-SYNTHETIC; includes fresh reconnect zero-selection, provider-content bounds, worker fail-safe, migration-chain compatibility and NFR-006 performance regressions. |
| Final browser/embedded reconnect check | Both settings routes showed one connected Google source, five of five calendars selected and current sync; both meeting routes rendered one upcoming row. The current row exposed no join action because no safe conferencing action was available. | OBSERVED-RUNTIME; counts/state only, no account, title, URL, attendee or provider payload retained. |
| Native current-worktree review bundle | The isolated review app rendered upcoming/settings IA, read-only copy, dirty/cancel behavior and native `Начать запись`; `DesktopCalendarReminderTests` passed 24 tests. Sanitized screenshots: `output/playwright/calendar-168/07-macos-upcoming-review.png`, `08-macos-calendar-settings-review.png`, `09-macos-calendar-settings-lower-review.png`. | OBSERVED-RUNTIME + PASS-SYNTHETIC; review bundle pointed only to the synthetic harness and was quit after inspection. |
| Google Cloud launch status | Audience is External/In production. Data Access contains only `openid`, `calendar.calendarlist.readonly` and sensitive `calendar.events.readonly`, with no restricted scope. Verification Center reports branding is not shown and data access is unverified. | OBSERVED-RUNTIME metadata only; no credential or account value retained. In production is not Google verification or unrestricted production readiness. |
| Google domain ownership and branding remediation | Search Console confirmed DNS ownership of `2brain.pro`; the ownership issue disappeared from Google branding review. An authorized re-verification submission reached `Verification in progress…` and then returned homepage-purpose/name findings. The first remediation worktree added a calendar-purpose section, but a later full landing redesign removed it from `master` and production. T066 now places the disclosure first in the existing FAQ on clean base `53550c6b`, expanded by default: selected-calendar reads, upcoming/reminder/context purpose, read-only limits, disconnect control, no automatic recording/join, all-users verification status and a privacy-policy link. The duplicate standalone section and desktop/mobile navigation item are absent, and matching `FAQPage` JSON-LD is present. The complete public landing file passes 16/16 tests; Ruff, diff checks and the forbidden-value scan pass. The exact local runtime was visually inspected at 1440x1000 and 390x844 with zero horizontal overflow, a working mobile menu, native FAQ toggle, successful privacy-link navigation and no browser warnings/errors. Key text contrast ratios remain at least 5.12:1. | PASS-SOURCE + PASS-SYNTHETIC + OBSERVED-RUNTIME on the local T066 worktree. The correction is not deployed and Google review must not be resumed until the exact public URL shows it. No DNS value, account identity, calendar content or credential was retained. |
| Calendar interaction performance | The warmed disposable-PostgreSQL regression ran the existing safe-state/audit test plus 20 cached settings projections and 20 sync acknowledgements; all NFR-006 p95 thresholds passed. | PASS-SYNTHETIC: 2 tests passed; provider network time is intentionally excluded from acknowledgement, and the isolated container was removed. |

## Live sync-state and repeated disconnect receipt — 2026-08-21

| Check | Result | Interpretation |
|---|---|---|
| Repeated Google happy path | The local read-only callback restored one source with six readable calendars; five previously selected calendars produced an authoritative current sync and two upcoming rows before the destructive-lifecycle check. | OBSERVED-RUNTIME local account; counts/state only, no account identity, calendar label, event title, attendee or meeting URL retained. |
| Repeated disconnect truth | Cancel preserved the source. Confirm showed exactly `Календарь отключён от GRAF.`, removed the card immediately and after reload, left zero runtime-readable credentials and zero future snapshots, and exposed no further sync action. Past snapshots remained under the approved meeting-history policy. | OBSERVED-RUNTIME + metadata-only DB receipt; Google-side access was intentionally not revoked. |
| Fresh reconnect | Reauthorization created one fresh source with six readable calendars and zero selected calendars; the old selection and cache were not resurrected. | OBSERVED-RUNTIME; user selection remains required before event sync. |
| Manual-sync state refresh | With zero calendars selected, the real page visibly moved `queued` → `syncing` → terminal `never_synced` through bounded automatic refresh, without a manual reload. After four 15-second attempts the shared live region has a safe long-running fallback instead of endless refresh. | OBSERVED-RUNTIME + PASS-SOURCE; browser and embedded share the same `cabinet.js` behavior. |
| Focused regression | `node --check cabinet.js`; three focused web-shell tests passed; the calendar settings contract passed 20/20 through the disposable PostgreSQL runner, which removed its container. | PASS-SYNTHETIC; the first direct contract invocation without the required runner was discarded as invalid setup evidence. |
| Native boundary | The installed local app showed the embedded zero-selection state and the native `Начать запись` control at login, home and calendar settings. Recording was not started, avoiding capture of ambient user audio. | OBSERVED-RUNTIME; manual-control availability proven visually, Stop remains covered by the focused Swift regression. |
| Final local macOS walkthrough | The installed `GRAF Local.app` rendered the same local Google source as the browser: 1 source, 6/6 calendars selected and current sync. Its upcoming section rendered 2 rows, and native `Начать запись` remained available on both calendar settings and meetings screens. | OBSERVED-RUNTIME; AX/visual review only, counts and states retained, no event title, participant, URL, token or audio retained. The separately installed production-origin app was not used as local parity evidence. |

## Production rollout receipt — 2026-08-21

| Check | Result | Interpretation |
|---|---|---|
| Release commit and tag | `6cd0eb5e7da3569ef4ddc62e1fa92aeed04cf3d4`; `v2026.08.21.5` | Exact commit is on `master`, `origin/master`, and the production checkout. |
| Conflict/ancestry check | PASS | Release commit is a direct descendant of the previous `origin/master`; no merge conflict or unrelated worktree change was included. |
| Exact-SHA full CI | PASS | macOS `725 passed`; server `3219 passed, 1 skipped`; strict RLS `50 passed, 1 skipped`; lint, compile, Compose and evidence scan passed. Disposable PostgreSQL was removed. |
| Dry-run | PASS | `infra/scripts/cd-remote.sh --dry-run --branch master` returned `deploy_result=dry_run` and required full CI, backup, restore, migration, health, smoke and rollback gates. |
| Backup and restore rehearsal | PASS | Production backup and restore rehearsal completed before deployment; backup reference is retained in the private deployment receipt. |
| Migration and RLS | PASS | Production reached migration `0075_calendar_sync_maintenance`; runtime database identity and direct SQL RLS boundary passed. |
| Runtime health | PASS | Temporal, processing worker, API live/readiness and public download/update smoke passed. |
| Production smoke | PASS | Smoke upload, metadata-only cleanup and automatic dispatch gate passed; no smoke content was retained. |
| Remote identity | PASS | Remote `master` and deployed SHA both equal `6cd0eb5e7da3569ef4ddc62e1fa92aeed04cf3d4`. |
| Google Calendar production state | Intentionally disabled | `TWOBRAIN_GOOGLE_CALENDAR_ENABLED=false`; provider remains fail-closed and the UI must not claim all-users Google support before Google verification and real production E2E. |
| Rollback | Not required | Deployment completed successfully; guarded backup/rollback path remains available. |

The CD runner also reports `automatic_retry_result`, `backfill_inventory_result`,
`range_playback_result` and `normalization_cleanup_result` as
`required_post_deploy`. These are existing playback-maintenance follow-ups,
not calendar acceptance gates, and were not expanded into this feature rollout.

```text
commit_sha: 6cd0eb5e7da3569ef4ddc62e1fa92aeed04cf3d4
spec_kit_analysis:
provider_matrix:
postgres_url_class: disposable-local-only
server_focused_result: full calendar selection 389 passed; disposable Postgres, 2026-08-21
server_integration_result: exact-SHA full 3219 passed, 1 skipped; strict RLS 50 passed, 1 skipped; isolated containers removed, 2026-08-21
swift_focused_result: DesktopCalendarReminderTests 24 passed, 2026-08-21; historical broader/full receipts remain 242/693 with ContractValidation PASS
browser_scenario_result: real local Google connect/select/sync/upcoming/disconnect/reconnect passed; 20/21 synthetic mouse/keyboard limit passed; uncertified providers remain fail-closed as Soon
embedded_scenario_result: real local Google settings/upcoming parity passed; disconnect/reload truth shares the same server state; complete native release certification remains open
google_test_account_result: local real-account OAuth/catalog/select/sync/upcoming/disconnect/reconnect observed; no private content retained; production-wide access remains blocked by Google verification
oauth_verification_result: External/In production; approved scopes configured; branding hidden and Calendar data access unverified; no submission or production approval performed
forbidden_content_scan: detector-only schema-name matches manually reviewed; no forbidden values
rls_result: strict RLS boundary 50 passed, 1 skipped; disposable Postgres plus production runtime boundary passed
ci_local_result: exact-SHA full gate 725 macOS passed, 3219 server passed/1 skipped, strict RLS 50 passed/1 skipped, 2026-08-21
rollout_flag: production server/UI rollout pass; Google provider disabled fail-closed
rollback_receipt: backup and restore rehearsal pass; guarded rollback not required
```

## Homepage and convergence revalidation — 2026-08-23

| Check | Result | Interpretation |
|---|---|---|
| Current master identity | Local `HEAD` and read-only `ls-remote origin master` resolve to `f0916254fe4c0a84ebe80ec2983cf4407d73b489`; the feature worktree was fast-forwarded from the prior `53550c6b` base without rewriting another worktree. | PASS-METADATA; the FAQ diff is now based on the current remote master. |
| Fresh calendar regression | `bash apps/server/scripts/run_local_postgres_tests.sh -k calendar -q`: 390 passed, 2972 deselected; the disposable PostgreSQL container was removed. | PASS-SYNTHETIC on the current master base; settings, Google/CalDAV adapters, sync, RLS/tenant boundaries, disconnect/deletion, context, upcoming and performance coverage remain green. |
| Google recovery integration regression | `test_calendar_provider_runtime.py` plus `test_google_calendar_provider.py`: 32 passed on disposable PostgreSQL. The added recovery assertion proves `old cursor → cursor_invalid/410 → bounded full sync → new cursor`, including stale in-window snapshot retirement. Existing cases prove safe revoked-credential state and bounded 429 retry. | PASS-SYNTHETIC; this strengthens C168-16 but does not replace the dedicated live Google test-account run required by T036. The disposable container was removed. |
| Provider catalog fail-closed gate | Four focused view-model/contract checks passed on disposable PostgreSQL: all 12 provider labels remain present, no provider is connectable by default, unavailable cards show `Скоро`, and no connect dialog or credential fields are rendered. | PASS-SOURCE + PASS-SYNTHETIC for T062. This certifies current truthful presentation only; it does not certify any provider's real account flow or permit promotion from `Скоро`. |
| Fresh macOS calendar regression | `swift test --package-path apps/macos --disable-swift-testing --filter 'DesktopCalendarReminderTests|CalendarTray'`: 24 passed. | PASS-SYNTHETIC; tray projection, overlap handling, safe titles/links and the manual recording boundary remain green. |
| Forbidden-content recheck | Only schema/detector names such as `access_token`, `refresh_token` and `contains_passcode` matched the quickstart detector; manual review found no values or private calendar/meeting content. | PASS-SOURCE; no credential, account identity, event title, attendee, raw link, transcript or audio was added. |
| Live privacy-policy disclosure | `https://rec.2brain.pro/privacy` returned HTTP 200 and its rendered text contains the required raw-data recipient limits, aggregated/anonymized disclosure, no-generalized-model-training statement, no-other-recipient statement and Limited Use reference. | PASS-PUBLICATION for the privacy-policy remediation requested by Google; this does not prove Google acceptance and does not replace the missing homepage FAQ. |
| Live homepage publication | `https://rec.2brain.pro/` returned HTTP 200 but did not contain the `google_calendar` FAQ marker or the approved Google Calendar question. | BLOCKED-PUBLICATION; local T066 evidence cannot be used for Google review until T072 publishes and rechecks the exact public URL. |
| Production checkout identity | Read-only SSH metadata previously returned clean production checkout SHA `53550c6b0a25ddab811b367f2ab9b42ea2deeb6a`, equal to the then-current `master`/`origin/master`; the production Google rollout flag is disabled or absent. | PASS-METADATA for the prior deployed server/UI commit only; no secret value, environment dump, deploy, restart or mutation was performed in that check. This does not publish the local FAQ change or prove Google production E2E. |
| Release closeout inventory | The current repository master is `f0916254`; the deployed production baseline is the already closed `v2026.08.23.6`. The FAQ correction still has no tag, GitHub Release or production receipt. | PARTIAL-METADATA; T070 remains open for the new exact-SHA `v2026.08.23.7` tag, Russian GitHub Release and metadata-only receipts. |
| Release closeout drafts | Obsolete `v2026.08.23.5` drafts were removed after the master update. The new release notes and production receipt will be written only after the exact candidate SHA, full CI/CD and public readback are proven. | PASS-DOCS locally; T070 remains open and no release claim is made yet. |

## Upcoming event end-boundary revalidation — 2026-08-28

| Check | Result | Interpretation |
|---|---|---|
| Server end-boundary regression | `bash apps/server/scripts/run_local_postgres_tests.sh -k calendar -q`: 399 passed, 3142 deselected; disposable PostgreSQL container removed. | PASS-SYNTHETIC; an event remains eligible while `ends_at` is later than the server's current time, and an already-ended event is excluded. This covers the shared upcoming service and the desktop endpoint. |
| Browser and embedded rendering | Local synthetic runtime `/meetings` and `/desktop/meetings` both rendered the compact upcoming block with visible rows and a metadata-only `data-calendar-upcoming-refresh-at` value. | OBSERVED-RUNTIME local synthetic only; both surfaces use the same server projection and no private event content was retained. |
| Client refresh behavior | `cabinet.js` parses the server-provided earliest visible `ends_at` and schedules a bounded page reload one second after it. `node --check` and `git diff --check` passed. | PASS-SOURCE; the next page read removes the ended event using server truth. No client-side event mutation or calendar provider call is introduced. |
| macOS boundary regression | `swift test --package-path apps/macos --disable-swift-testing --filter 'Calendar|DesktopCalendarReminder|DesktopUploadClient|CaptureControl|DesktopCabinet'`: 258 passed, 0 failures. | PASS-SYNTHETIC; native reminders, calendar context and manual Record/Stop boundary remain green. |
| Fast local lane | `infra/scripts/ci-local.sh --fast`: 1249 passed; lint and Python compile passed. | PASS-FAST; full CI was intentionally not run. |
| Release identity | The patch is merged by PR #5917 at exact merge SHA `a0ca712e96e1f50ea03e4179faac74d76f965554` and is present in the clean master deploy-worktree. | PARTIAL-RELEASE; release-prep, exact-SHA full gate and deployment are not run, so production behavior is not claimed. |

Never write token values, account email, event title, meeting URL, attendee
identity, raw API response, audio or transcript into this file.

## Reproducible validation commands

```sh
cd apps/server
bash scripts/run_local_postgres_tests.sh -q \
  tests/integration/test_calendar_settings_flow.py \
  tests/integration/test_calendar_persistence.py \
  tests/integration/test_calendar_provider_runtime.py \
  tests/contract/test_calendar_settings_contract.py

bash scripts/run_local_postgres_tests.sh -q \
  tests/unit/test_google_calendar_provider.py \
  tests/unit/test_caldav_provider.py \
  tests/unit/test_calendar_worker.py \
  tests/integration/test_calendar_provider_runtime.py

cd ../..
infra/scripts/ci-local.sh --fast
swift test --package-path apps/macos --disable-swift-testing \
  --filter 'Calendar|DesktopCalendarReminder|DesktopUploadClient|CaptureControl|DesktopCabinet'
```

All database URLs are generated by the runner and disposable; none belong in
logs or committed evidence.
