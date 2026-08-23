# Feature 168 quickstart and validation plan

All fixture values must be synthetic `.test` values. Do not use real OAuth
tokens, passwords, private event text, participant email, raw meeting URL,
passcode, transcript or audio.

## Preconditions

```sh
specify --version
specify self check
git status --short
```

For DB-backed tests, start only a disposable local Postgres environment using
the repository script and record the resulting `TWOBRAIN_DATABASE_URL` as
environment metadata, never in evidence:

```sh
bash apps/server/scripts/run_local_postgres_tests.sh
```

## Focused checks

```sh
cd apps/server
PYTHONPATH=src uv run --extra dev pytest -q \
  tests/unit/test_calendar_credentials.py \
  tests/unit/test_calendar_normalization.py \
  tests/unit/test_calendar_provider_fixtures.py \
  tests/unit/test_calendar_settings_view_models.py \
  tests/unit/test_calendar_auto_context_match.py \
  tests/contract/test_calendar_settings_contract.py \
  tests/contract/test_calendar_context_contract.py \
  tests/contract/test_calendar_integration_completion_contract.py \
  tests/contract/test_google_calendar_contract.py \
  tests/contract/test_calendar_no_secret_content_egress.py \
  tests/contract/test_calendar_rls_contract.py

PYTHONPATH=src uv run --extra dev pytest -q \
  tests/integration/test_calendar_persistence.py \
  tests/integration/test_calendar_provider_failures.py \
  tests/integration/test_calendar_disconnect_lifecycle.py \
  tests/integration/test_calendar_deletion_lifecycle.py \
  tests/integration/test_calendar_settings_flow.py \
  tests/integration/test_calendar_provider_runtime.py \
  tests/integration/test_calendar_access_policy.py

cd ../..
swift test --package-path apps/macos --disable-swift-testing \
  --filter 'Calendar|DesktopCalendarReminder|DesktopUploadClient|CaptureControl|DesktopCabinet'

# Tray projection and native calendar surface
swift test --package-path apps/macos --disable-swift-testing \
  --filter 'DesktopCalendarReminderTests|CalendarTray'
```

## macOS tray walkthrough

1. Build and launch the local macOS app with the existing app script.
2. Confirm a GRAF calendar icon is visible in the menu bar and has the label
   “Ближайшие встречи GRAF”.
3. Open it while authenticated: observe loading, then upcoming rows or the
   explicit empty state. Use only synthetic or redacted event data in evidence.
4. Refresh once and verify the control is disabled while loading.
5. Revoke the local session or use a synthetic 401 fixture: verify “Нужен
   вход” and no raw error detail.
6. Disconnect the source in browser/embedded settings, reopen the tray and
   verify that the next refresh no longer shows the source events.
7. Use “Открыть GRAF” and “Настройки календаря” and verify the existing
   embedded routes open. If a safe synthetic link is present, verify only an
   explicit click opens it; never test by auto-joining.
8. Verify native Record and Stop remain visible and usable independently of
   tray/calendar state.

## Scenario matrix

| ID | Surface | Steps | Expected | Evidence/verdict |
|---|---|---|---|---|
| C168-01 | browser/embedded | Open settings, open each connectable provider form, cancel; inspect every `Скоро` card | No source; focus returns to CTA; no secret transmitted; `Скоро` cards have no active form | current local runtime + DOM |
| C168-02 | browser/embedded | Submit empty/invalid synthetic fields | Native/server validation; no source; safe inline/result error | automated + browser |
| C168-03 | browser/embedded | Start connect with synthetic provider double | Button busy/disabled; success only after validation/catalog; catalog step shown | PASS-SYNTHETIC + observed browser/embedded E2E; no external provider |
| C168-04 | browser/embedded | Provider timeout/401/403/429/invalid payload | Safe local error; retry guidance; no token/payload echo | adapter test + UI |
| C168-05 | browser/embedded | Reload after success/error/cancel | Durable server result and source projection remain truthful | route test |
| C168-06 | browser/embedded | Select zero/one/20/21, cancel, save, reload; inspect seven-day/365-day boundaries | Selection is committed/empty truth; no events when zero; 21 is rejected safely; no out-of-window or silently truncated data | integration + browser |
| C168-07 | browser/embedded | Manual sync with page/cursor/delete fixture | queued→syncing→synced; snapshots/cursor/delete truth | worker spy + DB read-back |
| C168-08 | browser/embedded | Retry sync while queued/syncing | One job/one provider call policy; safe accepted/already-running | concurrency test |
| C168-09 | browser/embedded | Open disconnect, cancel | Source unchanged; no cleanup | browser + DB |
| C168-10 | browser/embedded | Confirm disconnect, reload, repeat sync | Card omitted/disabled; credentials non-readable; future rows gone; sync failed_closed | DB read-back + runtime |
| C168-11 | browser/embedded | Reconnect after disconnect | New source/operation; no old credential/cache resurrection | lifecycle test |
| C168-12 | macOS | Calendar connected/stale/error/disconnected while recording | native Record/Stop and upload remain available | Swift + embedded runtime |
| C168-13 | desktop | one/none/multiple/overlap/back-to-back/recurring event | deterministic match/ambiguous/no-context; no context switch mid-recording | 098 suite |
| C168-14 | desktop | private/free-busy/all-day/cancelled/offline | safe generic state; no content/link leak; capture continues | fixture + redaction |
| C168-15 | Google | authorize → callback → catalog → select → sync → preview | test account completes with approved scopes and safe result | real test-account E2E |
| C168-16 | Google | token expiry/revocation/410/429/pagination | reconnect/full-resync/backoff state; no silent stale success | dedicated test account for expiry/revocation/reconnect; deterministic provider double + disposable PostgreSQL for 410/429 unless a separately approved controlled Google fault/quota test is available |
| C168-17 | Google | disconnect and reload/logout/login/other tenant | no provider calls/cache/credential access, no provider revoke call; tenant isolation | E2E + DB/RLS |
| C168-18 | a11y | keyboard, focus, screen reader, narrow/dark/light | labeled controls, live status, no focus trap, readable copy | browser a11y evidence |
| C168-19 | provider certification | Repeat connect/catalog/select/sync/reconnect/local disconnect in browser and embedded macOS for each advertised family | Exact provider is connectable only after every step passes; otherwise `Скоро` with no form | dedicated provider test account + sanitized runtime evidence |
| C168-20 | performance | Warm cached settings projection and submit 20 synthetic sync acknowledgements on disposable PostgreSQL | post-callback projection p95 ≤ 500 ms; cached catalog p95 ≤ 1 s; acknowledgement p95 ≤ 300 ms without provider I/O | `test_calendar_settings_cached_projection_and_sync_ack_p95` |

## Forbidden-content gate

```sh
rg -n -i \
  -e 'authorization\s*:\s*bearer\s+[a-z0-9._~+/-]{10,}' \
  -e 'refresh_token\s*[:=]' \
  -e 'access_token\s*[:=]' \
  -e 'passcode\s*[:=]' \
  -e 'attendee_email_dump|raw_event_payload|signed_url' \
  specs/168-calendar-integration-completion \
  apps/server/tests/fixtures/calendar apps/server/src/twobrain_rec_server/calendar \
  apps/macos/RecApp/Sources/Calendar apps/macos/Shared/Sources/Models/CalendarContextModels.swift
```

Expected: no real values. Schema field names and redaction-test detector
references require manual review, not deletion.

## Closeout

```sh
infra/scripts/ci-local.sh
```

Do not run production deploy, remote smoke or issue sync from this worktree.
Google rollout requires the owner/OAuth gates in `research.md`; update exact
receipts in `validation/implementation-evidence.md` after each approved gate.
