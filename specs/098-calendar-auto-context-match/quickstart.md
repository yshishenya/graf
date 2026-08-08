# Quickstart: Calendar Auto Context Match

**Feature**: `098-calendar-auto-context-match`

## Purpose

Prove feature 098 end to end with synthetic calendar/recording data: live recording-start resolution, deterministic auto-match, safe ambiguity/no-context behavior, immutable context history, title precedence, manual/offline exclusion, recurring authorization, lifecycle accounting and browser/embedded parity.

This quickstart does not run the deferred standalone Codex Security scan. Authorization, privacy/redaction and forbidden-content assertions below are normal feature acceptance tests and must not be presented as completion of that later audit.

## Prerequisites

- Repository root: the active 098 feature worktree anchored to the current branch and current `origin/master`.
- Python/server dependencies resolved through `uv`.
- Xcode/Swift 6 toolchain for the macOS package.
- Docker available for disposable PostgreSQL migration/RLS validation.
- Only synthetic `.test` calendar fixtures; no live credentials, event exports, attendee lists, meeting links, transcript text or audio.
- Feature artifacts complete: `spec.md`, `plan.md`, `research.md`, `data-model.md`, contracts, checklist, tasks and clean analyze result.

## 1. Unit Matching And Read-Model Checks

```sh
cd apps/server
PYTHONPATH=src uv run --extra dev pytest -q \
  tests/unit/test_calendar_auto_context_match.py \
  tests/unit/test_calendar_recording_context.py \
  tests/unit/test_calendar_normalization.py \
  tests/unit/test_calendar_participants.py \
  tests/unit/test_calendar_settings_view_models.py \
  tests/unit/test_cabinet_view_models.py \
  tests/unit/test_cabinet_web_shell.py
```

Expected:

- five-minute pre-start grace and five-minute boundary blocker are deterministic;
- a sole recently ended event is not selected;
- a provisional pre-start match is rejected when the recording stops before event start;
- duplicates collapse only with strong link/source identity;
- stale selected sources veto automatic choice;
- private/all-day/cancelled/deleted/weak-signal events do not match;
- title precedence and immutable roster snapshot validation pass;
- no medium-score winner exists.

The unit suite includes a warmed synthetic performance case with at least 100 resolve evaluations, four selected sources and 50 candidate rows. Its measured p95 requirements are:

- resolve: `<= 200 ms`;
- attempt consumption: `<= 50 ms`.

Record the sample count and measured p95 values in implementation evidence; a single fast call is not sufficient.

## 2. API, OpenAPI And RLS Contracts

```sh
cd apps/server
PYTHONPATH=src uv run --extra dev pytest -q \
  tests/contract/test_calendar_auto_context_contract.py \
  tests/contract/test_calendar_context_contract.py \
  tests/contract/test_calendar_no_secret_content_egress.py \
  tests/contract/test_calendar_rls_contract.py \
  tests/contract/test_cabinet_contract.py \
  tests/contract/test_cabinet_no_secret_content_egress.py \
  tests/contract/test_openapi_contract_drift.py
```

Expected:

- recording-start resolve requires owner/device/workspace and idempotency;
- automatic resolve accepts no event ID;
- explicit selection/decline use distinct intents, and start-time decline persists `declined_by_user` rather than later-clear state `cleared_by_user`;
- every attempt expires exactly at `evaluated_at + 24 hours` and cannot be consumed at or after expiry;
- meeting create consumes only a same-owner/same-workspace/local-recording attempt;
- missing/foreign/expired attempts safely skip instead of rematching;
- GET/PUT/DELETE expose only authorized safe context;
- mutations preserve CSRF coverage;
- private details and raw attendee values never appear in responses;
- the new attempt table is included in RLS inventory;
- canonical OpenAPI and feature-local contract agree.

## 3. Server Integration Matrix

```sh
cd apps/server
PYTHONPATH=src uv run --extra dev pytest -q \
  tests/integration/test_calendar_auto_context_match.py \
  tests/integration/test_calendar_auto_context_migrations.py \
  tests/integration/test_calendar_access_policy.py \
  tests/integration/test_calendar_provider_failures.py \
  tests/integration/test_calendar_deletion_lifecycle.py \
  tests/integration/test_calendar_disconnect_lifecycle.py \
  tests/integration/test_calendar_persistence.py \
  tests/integration/test_manual_media_upload.py \
  tests/integration/test_ingest_happy_path.py \
  tests/integration/test_cabinet_csrf.py \
  tests/integration/test_cabinet_meeting_list.py \
  tests/integration/test_cabinet_meeting_detail.py \
  tests/integration/test_meeting_deletion_workflow.py \
  tests/integration/test_meeting_share_links.py \
  tests/integration/test_postgres_migrations.py
```

Required scenarios:

| Scenario | Expected evidence |
|---|---|
| One current eligible event | `matched_auto`, safe calendar title when replaceable, immutable roster |
| One event starts within 5 minutes and recording reaches start | `matched_auto` after attempt consumption |
| Pre-start recording stops before event | `no_context/prestart_not_reached` |
| Participants, no link/location | title plus roster |
| Link/location, no participants | title, roster unavailable |
| Neither participants nor link/location | no match |
| Overlapping events | `ambiguous`, no title/roster until owner choice |
| Exact/near back-to-back | ambiguous or no context; never arbitrary choice |
| Duplicate provider/link representations | one effective candidate only with strong identity |
| Private/free-busy | generic list state; owner-only safe reason; no details |
| All-day | ignored/skipped, no context |
| Stale or latest-failed selected source | stale/unavailable state, no partial-source match |
| No connected/selected calendar | ordinary no-context recording |
| Manual upload | `skipped_manual_upload`, upload title unchanged |
| Recovered/offline queue without attempt | `skipped_offline_or_unknown` |
| Generated/app title | replaceable by safe calendar title |
| User/upload/file/legacy title | never auto-overwritten |
| Event renamed/deleted/cancelled after match | stored title/roster/time unchanged |
| Explicit ambiguity selection | `matched_user`, stable across retries |
| Explicit continue without calendar | `declined_by_user`, no later auto-attach, never reported as clear |
| Clear matched context later | `cleared_by_user`; roster/link removed; visible title remains stable |
| Attempt at 24-hour boundary | consumption rejected at `evaluated_at + 24 hours`; purge eligible |
| Cross-user/cross-workspace event or attempt | not found/no existence leak |
| Previous recurring occurrence authorized | safe pointer visible |
| Previous occurrence deleted/inaccessible/cross-space | no pointer or placeholder |
| Concurrent/repeated resolve/create | one attempt and one context row |
| Provider failure | capture/meeting/upload/processing path remains successful |
| Calendar attendees | zero grants, recipients, delivery or speaker renames |
| Meeting deletion/source disconnect | derived context accounted/purged per lifecycle |

Requirement-to-evidence map:

| Requirement range | Primary evidence class |
|---|---|
| FR-001–FR-005 | live resolve, same-owner/workspace clear-match and cross-boundary scenarios |
| FR-006–FR-010 | participant/link/weak/private/all-day eligibility scenarios |
| FR-011–FR-013 | manual upload, offline recovery and ad-hoc scenarios |
| FR-014–FR-015 | overlap/back-to-back chooser and correction scenarios |
| FR-016–FR-019 | immutable snapshot, rename/delete/cancel and title-precedence scenarios |
| FR-020–FR-023 | roster-only, zero-access/delivery and unchanged speaker-label scenarios |
| FR-024–FR-026 | recurring authorized/deleted/inaccessible/cross-space scenarios |
| FR-027–FR-028 | duplicate/concurrent retry and stale/latest-failed source scenarios |
| FR-029–FR-032 | metadata-only audit, forbidden-content acceptance and fail-soft provider scenarios |
| FR-033–FR-040 | list/review provenance, safe candidates, explicit clear and roster semantics scenarios |
| FR-041–FR-050 | lifecycle, explainability, UI parity, duplicate events and release evidence receipts |
| FR-051–FR-052 | distinct decline/clear states and exact 24-hour attempt expiry receipts |

Every task/test/evidence receipt must reference the covered FR/SC IDs; a green test without requirement traceability is insufficient for closeout.

## 4. Migration And PostgreSQL/RLS Gate

Run the migration-focused tests first, then the disposable PostgreSQL validation:

```sh
cd apps/server
PYTHONPATH=src uv run --extra dev pytest -q \
  tests/integration/test_calendar_auto_context_migrations.py \
  tests/integration/test_postgres_migrations.py
```

```sh
cd ../..
infra/scripts/verify-rec-migration.sh --execute
```

Expected:

- clean upgrade from `0020` to `0021`;
- deterministic reconciliation of legacy context rows;
- titled legacy meetings backfill to non-overwritable provenance;
- unique attempt/context constraints work on SQLite and PostgreSQL;
- downgrade restores the prior schema without leaving orphan tables/indexes;
- disposable PostgreSQL RLS result is `pass` and cleanup succeeds.

Do not treat a local blocked RLS probe as production evidence. Record the exact result and resolve it before release readiness.

## 5. macOS Intent, Queue And Prompt Checks

```sh
swift test --package-path apps/macos --disable-swift-testing \
  --filter 'CalendarAutoContextMatch|DesktopUploadClient|DesktopUploadQueue|DesktopCalendarReminder|CaptureControl|DesktopCabinetWorkspace|DesktopCabinetUploadLink'
```

Expected:

- local capture starts before resolve and does not wait for it;
- ordinary manual/single-event start uses `automatic` without an event ID;
- overlap selection uses `user_selected`;
- “without calendar” uses `user_declined` and persists `declined_by_user`, distinct from later `cleared_by_user`;
- a successful attempt ID is persisted into the queue/create payload;
- failed resolve and scanned recovery queues contain no fabricated attempt ID;
- retries preserve the original attempt and selected event ID, while decision
  intent remains durable on the server attempt rather than duplicated locally;
- visible Record/Stop and one-action Stop are unchanged;
- no provider credential is stored on desktop.

## 6. Cabinet Rendering And Accessibility

The server integration/contract tests must prove the rendered browser and embedded route HTML for:

- compact list labels;
- owner-only ambiguous action;
- `Контекст встречи` block;
- roster separated from speakers;
- accessible radio chooser and focus/ARIA behavior;
- clear confirmation and durable result;
- recurring pointer authorization;
- generic private/no-context list copy;
- Russian/English message mapping and locale-aware time formatting;
- embedded route policy for all context actions.

If implementation changes visible layout materially, perform browser/embedded visual QA using synthetic data at the same viewport/state. Screenshots alone are not acceptance; compare the rendered state against the existing GRAF design-system/layout references and record the observed differences/fixes.

## 7. Focused Lint

```sh
cd apps/server
PYTHONPATH=src uv run --extra dev ruff check \
  src/twobrain_rec_server/api \
  src/twobrain_rec_server/calendar \
  src/twobrain_rec_server/cabinet \
  src/twobrain_rec_server/db \
  tests/unit/test_calendar_auto_context_match.py \
  tests/contract/test_calendar_auto_context_contract.py \
  tests/integration/test_calendar_auto_context_match.py \
  tests/integration/test_calendar_auto_context_migrations.py
```

Expected: no Ruff errors.

## 8. Canonical Local Closeout Gate

After all focused checks pass and task/analyze artifacts are reconciled:

```sh
infra/scripts/ci-local.sh
```

Required closeout evidence:

- immutable HEAD SHA;
- exact focused commands and counts;
- migration/RLS result;
- full local CI result;
- scenario matrix receipts with synthetic IDs only;
- task/GitHub issue reconciliation;
- changelog/current-product-status update;
- no unaccounted generated files or unrelated changes.

## 9. Release And Production Closeout

Only after implementation PR review/merge and a met release gate:

```sh
./scripts/prepare-release.sh YYYY.MM.DD.N
infra/scripts/cd-remote.sh --dry-run
infra/scripts/cd-remote.sh --execute
```

Then record:

- merged PR and issue links;
- CalVer tag and Russian GitHub Release notes;
- deployed/runtime SHA;
- backup/rollback reference;
- migration outcome;
- production health and smoke result;
- browser and installed macOS/embedded behavior;
- known limitation: standalone security audit deferred for a separate run;
- cleanup status for branch/worktree/issues.

Do not claim feature closeout from local tests alone. Production closeout requires the actual release/deploy/runtime evidence above.
