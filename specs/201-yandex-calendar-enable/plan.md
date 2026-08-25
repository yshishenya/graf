# Implementation Plan: Включение Яндекс Календаря

**Branch**: `codex/201-yandex-calendar-enable` | **Date**: 2026-08-25 | **Spec**: [spec.md](spec.md)

## Summary

Feature 168 уже содержит read-only CalDAV adapter для `caldav_yandex`,
серверное хранение credential envelope, общий sync worker, нормализацию,
disconnect lifecycle и browser/embedded settings. Feature 201 не создаёт новый
интеграционный слой: она доказывает реальный Яндекс-путь и переводит только
`caldav_yandex` из `Скоро` в connectable после полного certification receipt.

До receipt production остаётся fail-closed. Для ручной проверки выделенного
аккаунта локальный `start-local.sh` может включить отдельную форму Yandex без
изменения production capability allowlist. Google и Exchange в этот план не
входят. После подключения Яндекс сразу запускает первый sync; активные
выбранные источники повторяются через пять минут, а ручная кнопка выполняет
sync синхронно до ответа.

## Technical Context

**Language/Version**: Python 3.13 runtime in the server image, Swift/macOS
surface reused without provider-specific code.

**Primary Dependencies**: FastAPI, SQLAlchemy async, existing stdlib CalDAV
HTTP/XML/ICS adapter, existing cabinet templates and macOS embedded route.

**Storage**: Existing PostgreSQL tables `CalendarSource`,
`CalendarCredentialEnvelope`, `ExternalCalendar`, `CalendarEventSnapshot` and
calendar audit/lifecycle rows. No migration planned.

**Testing**: Existing pytest unit/contract/PostgreSQL suites, browser and
embedded macOS real E2E matrix, focused Swift calendar/cabinet checks.

**Risk / Validation Lane**: `high-risk-feature`: external credentials, tenant
scope, privacy, deletion, provider egress and user-visible integration state.

**Release Gate**: `cd dry-run` only for release preparation; no production
execute in this feature turn. Production enablement requires explicit release
approval after the real E2E receipt and full repository gate.

**Target Platform**: GRAF server, browser cabinet and embedded macOS cabinet.

**Project Type**: Server-rendered web service with native macOS client shell.

**Performance Goals**: Reuse Feature 168 bounds: cached settings projection
p95 ≤ 500 ms and catalog projection p95 ≤ 1 s. Manual sync is intentionally
provider-bound and must remain within the existing provider timeout/retry
budget; it no longer promises a queue-only acknowledgement.

**Constraints**: Read-only provider access; server-only secret handling; no
calendar writes, auto-join or auto-record; maximum 20 selected calendars;
seven-day lookback and 12-month forward sync horizon; five-minute Yandex
reconciliation; metadata-only evidence.

**Scale/Scope**: One provider family, one existing adapter, one staged rollout;
no generic provider platform, OAuth service or schema expansion.

## Constitution Check

Initial gate: PASS.

- Server-owned credentials remain sealed; no password enters desktop code,
  logs, analytics or committed evidence.
- Calendar access remains read-only and never gates manual Record/Stop, upload or
  meeting creation.
- Existing tenant/RLS, deletion, retention and GRAF-side disconnect contracts
  remain authoritative.
- Provider is not advertised as available until browser and embedded macOS real
  E2E certification passes.
- No raw event content, participant email, signed URL or private meeting data is
  written to specs, tests, logs or receipts.
- Existing server and native surfaces are reused; no new dependency, external
  scheduler, provider factory hierarchy or migration is justified. The existing
  maintenance loop owns the five-minute due-source check.

Post-design gate: PASS if the plan below remains within the same contracts and
the certification receipt is kept separate from implementation tests.

## Phase 0 — Research decisions

1. Confirm the existing Yandex CalDAV endpoint and app-password contract from
   source and metadata-only unauthenticated response.
2. Confirm `CalDAVAdapter` is routed both by connection validation and by the
   maintenance worker, and that it uses same-origin/public-destination checks.
3. Confirm the existing provider matrix deliberately keeps `caldav_yandex` at
   `Скоро` until real browser/embedded evidence exists.
4. Keep the current allowlist/certification seam; only the exact provider family
   may be promoted after receipt. Do not broaden all CalDAV aliases.

## Phase 1 — Design and contract

- Reuse the existing provider matrix and calendar integration contract.
- Add a provider-specific certification contract describing the exact evidence
  required before the allowlist changes.
- Add no data model fields and no migration.
- Keep synthetic provider doubles for automated tests; mark them as synthetic
  and never treat them as public support evidence.
- Update the source matrix/receipt only after the real test-account run passes.

## Phase 2 — Implementation slice

1. Run the existing focused CalDAV, worker, settings, no-secret and lifecycle
  tests.
2. Verify immediate-after-connect, five-minute due-source scheduling and
   blocking manual sync with synthetic providers before real E2E.
3. Use the explicit local-only Yandex form for the dedicated test account;
  this mode is not certification evidence.
4. Execute the real Yandex matrix on a dedicated test account without exposing
   credentials in chat or artifacts:
   connect, catalog, zero/one selection, sync, upcoming projection, reconnect,
   disconnect, reload and the same flow in embedded macOS.
5. If the matrix passes, make the smallest provider-gate change needed to mark
   only `caldav_yandex` certified and update the focused expectations.
6. If any matrix step fails, leave the provider `Скоро`, fix only the root cause,
   and do not claim launch.

## Rollout and rollback

- Before certification: no user-facing connect action; existing synthetic and
  local adapter tests remain available.
- After certification: expose only Yandex; Google and every other provider keep
  their current state.
- Rollback: restore Yandex to `Скоро`/fail-closed for new connections and sync
  claims. Do not resurrect disconnected credentials or delete meeting-owned
  context.
- Production release, deploy, live smoke and public launch are separate gates
  and require explicit approval after exact-SHA validation.

## Validation Plan

Focused checks:

```sh
cd apps/server
PYTHONPATH=src uv run --extra dev pytest -q \
  tests/unit/test_caldav_provider.py \
  tests/unit/test_calendar_worker.py \
  tests/unit/test_calendar_credentials.py \
  tests/unit/test_calendar_normalization.py \
  tests/unit/test_calendar_settings_view_models.py \
  tests/contract/test_calendar_settings_contract.py \
  tests/contract/test_calendar_context_contract.py \
  tests/contract/test_calendar_no_secret_content_egress.py
```

PostgreSQL-backed validation uses the repository disposable database runner
and covers connection-before-persistence, selection limits, sync lifecycle,
disconnect, deletion and tenant boundaries. macOS validation covers the
embedded calendar settings route and existing native Record/Stop independence.

The real-provider gate is defined in [contracts/yandex-certification.md](contracts/yandex-certification.md)
and the runnable sequence is in [quickstart.md](quickstart.md).

The full repository gate is `infra/scripts/ci-local.sh` before PR/closeout.
Production `infra/scripts/cd-remote.sh --dry-run --branch master` is required
only for a separately approved release; no execute/deploy is part of the
implementation step.

## Project Structure

```text
specs/201-yandex-calendar-enable/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── yandex-certification.md
└── checklists/requirements.md

apps/server/src/twobrain_rec_server/calendar/
├── capabilities.py
├── caldav.py
├── service.py
└── worker.py

apps/server/src/twobrain_rec_server/cabinet/
├── queries.py
├── view_models.py
└── web_routes/calendar.py

apps/server/tests/
├── unit/test_caldav_provider.py
├── unit/test_calendar_worker.py
├── unit/test_calendar_settings_view_models.py
├── contract/test_calendar_settings_contract.py
└── integration/test_calendar_provider_runtime.py
```

**Structure Decision**: Extend the existing calendar capability seam and tests;
do not add a second provider runtime, database model, migration or macOS
credential path.

## Complexity Tracking

None. The existing adapter and lifecycle already cover the required behavior.
