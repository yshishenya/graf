# Feature 168 scenario matrix

## Verdict taxonomy

- **PASS-SOURCE:** proven by current source/contract.
- **PASS-SYNTHETIC:** proven by existing synthetic tests/fixtures.
- **OBSERVED-RUNTIME:** observed on local runtime, not this worktree/release.
- **BLOCKED:** requires Postgres, authenticated runtime or external provider.
- **NOT-PROVEN:** no evidence yet; implementation gate.

| ID | Browser | Embedded macOS | Expected | Current verdict |
|---|---|---|---|---|
| S168-01 connect modal/cancel | modal opens, cancel returns focus to CTA | same route/session | focus return, no source | OBSERVED-RUNTIME current worktree; no source mutation |
| S168-02 empty/invalid connect | required fields/server safe error | same | no source, adjacent error | PASS-SOURCE/CONTRACT; authenticated DB run BLOCKED |
| S168-03 connect loading | disabled + live busy | disabled + native controls | no duplicate submit | PASS-SOURCE + PASS-SYNTHETIC; live provider mutation not run |
| S168-04 provider success | validated catalog then source card | same truth | durable success | OBSERVED-RUNTIME synthetic + real local Google browser/embedded; production gate remains |
| S168-05 provider error/reload | safe error after reload | same | no misleading success | PASS-SYNTHETIC mapping + OBSERVED-RUNTIME reload; real provider NOT-PROVEN |
| S168-06 catalog no calendars | safe empty catalog/action | same | source not eligible for prompts | PASS-SYNTHETIC; live catalog NOT-PROVEN |
| S168-07 selection zero/one/many | save/cancel/reload | same | count and event eligibility stable | PASS-SYNTHETIC + PASS-SOURCE |
| S168-08 manual sync queued | accepted then state changes | same | actual provider call | OBSERVED-RUNTIME real local Google queued→syncing→terminal state without manual reload; bounded one-minute refresh and safe long-running fallback; synthetic cursor/provider coverage |
| S168-09 stale/failure | safe stale/reconnect | same | capture remains usable | PASS-SYNTHETIC |
| S168-10 disconnect cancel | no mutation | same | source unchanged | PASS-SOURCE copy/handler + synthetic lifecycle |
| S168-11 disconnect success | card absent after reload | same | local credentials/cache/jobs closed; no provider revoke | OBSERVED-RUNTIME real local Google: approved one-line result, immediate/removal-after-reload, local credential/selection/future-cache purge and sync stop passed; PASS-SYNTHETIC lifecycle |
| S168-12 reconnect | active same-account reconnect preserves selection; reconnect after disconnect starts fresh | same | no duplicate active source or old cache resurrection | PASS-SYNTHETIC + OBSERVED-RUNTIME local Google; fresh source remained unselected until explicit user save |
| S168-13 preferences | prompts/filter settings save/reload | same | shared server preference | OBSERVED-RUNTIME reset/save/PRG/reload + PASS-SYNTHETIC DB |
| S168-14 single context | one eligible event | same | safe match | PASS-SYNTHETIC 098 |
| S168-15 ambiguity/overlap | chooser/continue without | same | no arbitrary context | PASS-SYNTHETIC 098/macOS |
| S168-16 private/all-day/offline | generic/none | same | no content leak, recording continues | PASS-SYNTHETIC |
| S168-17 browser/embedded parity | same read model | same | same owner truth | OBSERVED-RUNTIME real local Google browser + `GRAF Local.app` settings/upcoming parity after sync (1 source, 6/6 selected, current sync, 2 upcoming rows) plus synthetic reconnect/disconnect/logout-login; PASS-SYNTHETIC current-user/RLS tenant isolation |
| S168-18 keyboard/a11y | focus/live/labels | same | complete usable flow | PASS-SOURCE + OBSERVED-RUNTIME current DOM/AX: empty validation, Escape/cancel focus return, dirty/reset states; no physical VoiceOver session |
| S168-19 Google OAuth | consent/callback | same web route | state/redirect/server secret | OBSERVED-RUNTIME local account passed chooser/consent/callback; production verification remains BLOCKED |
| S168-20 Google sync | catalog/select/full/incremental | same | cursor/pagination/deletes | OBSERVED-RUNTIME local explicit selection, full sync, upcoming projection and 550-change incremental sync; pagination/delete cases remain synthetic-only |
| S168-21 Google revoke/429/410 | reconnect/backoff/full sync | same | safe state | PASS-SYNTHETIC mappings; live revoke/429/410 NOT-PROVEN |
| S168-22 Google disconnect/tenant | purge/reload/other tenant | same | no provider call/cache leak and no provider revoke call | OBSERVED-RUNTIME real local disconnect/reload/purge with no provider revoke + PASS-SYNTHETIC tenant isolation |
| S168-23 macOS tray loading/empty | open menu-bar item, observe refresh and zero-state | same native app | understandable status, no content leak | OBSERVED-RUNTIME empty state + PASS-SYNTHETIC model |
| S168-24 macOS tray upcoming | open tray with current server projection | same server projection | sorted safe rows, bounded list, explicit link action | OBSERVED-RUNTIME with redacted review + PASS-SYNTHETIC model |
| S168-25 macOS tray stale/auth | synthetic 401/transport fixtures | same | sign-in/unavailable/stale copy, no raw error | PASS-SYNTHETIC; no private content |
| S168-26 tray navigation/recording | use GRAF/settings actions and inspect native controls | embedded shell | existing route opens; Record/Stop unaffected | OBSERVED-RUNTIME route + SOURCE/focused tests |
| S168-27 home upcoming current | safe event rows above history | same projection | title/time preferences, explicit join action and settings link | OBSERVED-RUNTIME real local Google rows in browser + `GRAF Local.app` plus synthetic visible `Подключиться`; PASS-SYNTHETIC sealed-URL contract |
| S168-28 home upcoming empty/selection-needed | compact explicit state | same | no invented event, clear settings action | OBSERVED-RUNTIME browser + embedded synthetic fixture |
| S168-29 home upcoming stale/updating | labeled safe projection | same | no false freshness | OBSERVED-RUNTIME synthetic stale/syncing/credential states |
| S168-30 provider catalog truth | all uncertified providers show `Скоро` | same | no active form until real browser + embedded certification | OBSERVED-RUNTIME browser + embedded: all 12 fail closed; T062 remains BLOCKED |
| S168-31 provider validation/cancel | native + adjacent validation; cancel clears fields/focus returns | same | no secret retained in DOM after cancel | OBSERVED-RUNTIME empty validation/cancel/focus/field cleanup |
| S168-32 coherent settings IA | source → behavior → add → advanced | same DOM order | concise groups, keyboard order equals visual order | OBSERVED-RUNTIME current desktop + 390x844 + real embedded WebView; DOM/AX review |
| S168-33 responsive loaded-page resize | expanded desktop rail then 390px | embedded/browser breakpoint | rail collapses, content remains readable, no overflow | OBSERVED-RUNTIME: 64px rail, 326px content, zero horizontal overflow; focused JS/unit regression PASS |
| S168-34 selection maximum | click 21st calendar by mouse and Space | same shared form | 20 remain checked; 21st unchecked; live limit message wins over dirty state | OBSERVED-RUNTIME synthetic mouse + keyboard; PASS-CONTRACT; 20/21 PostgreSQL boundary PASS |
| S168-35 credential failure on home | cached synthetic preview exists but source fails closed | same projection | no stale title or join action; reconnect/manual recording remain | OBSERVED-RUNTIME browser + embedded with zero rows/actions; PASS-SYNTHETIC regression |
| S168-36 interaction performance | 20 warmed cached settings projections and 20 sync acknowledgements | same server route/read model | p95 ≤ 500 ms/1 s for projection/catalog and ≤ 300 ms acknowledgement without provider I/O | PASS-SYNTHETIC disposable PostgreSQL; 2 focused tests passed and container removed |

## Required evidence columns for implementation

For every row record: scenario ID, commit SHA, surface, viewport, fixture/test
account class, steps, expected, actual, verdict, safe evidence path, and
redaction review. Evidence may contain state IDs/counts/timestamps, never
private content or credentials.
