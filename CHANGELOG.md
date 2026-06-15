# Changelog

All notable changes to this project will be documented in this file.
This project follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and
Semantic Versioning 2.0.0.

## [Unreleased]

### Added

- Добавлена обязанность вести Changelog в репозитории для всех значимых изменений.
- Добавлена macOS desktop upload queue: durable local queue, truthful retry/upload states,
  server-mediated ingest mapping and compact queue UI (`feature:014`, `T001-T030`).
- Добавлен server-side MediaScribe processing pipeline: durable workflow/job/result
  state, idempotent Temporal workflow identity, server-side dual-track submit,
  poll/import, content-safe status API, failure classification, restart-safe job
  reuse, and dependency truth for future deletion (`feature:015`, `T001-T087`).
- Добавлен backend tenant-isolation RLS hardening слой: PostgreSQL policies,
  request/worker/auth bootstrap/session lookup/callback lookup/maintenance DB
  contexts, rollout validation helper, and future-table ADR (`feature:031`,
  `T001-T052`).
- Добавлен MVP experience/design handoff для `2brain Rec`: clean-room audit,
  native/web route boundaries, status matrices, screen specs, embedded
  server-owned speaker assignment для desktop shell и активный Figma v8 clean
  Russian implementation baseline с 98 валидными click reactions
  (`feature:030`, `T001-T085`).

### Changed

- Синхронизирован Speckit workflow с обязательными этапами `clarify`,
  `checklist`, `analyze`, `taskstoissues`, чтобы требования и контроль качества
  были сквозными.
- RLS validation wording now separates destructive test/disposable probes from
  production read-only RLS state truth (`feature:032`, `T001-T014`).

### Fixed

- В `.github` и процессе разработки зафиксирован порядок этапов и коммитов для
  Spec Kit.
- MediaScribe client now follows the live production contract for polling and
  result import via `/jobs/{job_id}` and normalizes `start`/`end`/`speaker`
  fields into persisted processing rows (`feature:015`).
- Исправлены имена unique constraints для MediaScribe processing migration,
  чтобы production PostgreSQL migration не падала на конфликте имен
  (`feature:015`).
- Укорочен Alembic revision id для `0004`, чтобы он помещался в стандартный
  `alembic_version.version_num`, и Temporal production wrapper теперь читает
  local-file secrets с корректными правами (`feature:015`).
- Production env template больше не рассылает service-specific secret-file
  paths во все app containers, а ошибки production secret validation называют
  конкретное field name без раскрытия secret values (`feature:015`).
- Malformed successful MediaScribe submit/result payloads now map to safe
  retryable `mediascribe_malformed_response` processing state instead of
  escaping as unmanaged validation exceptions (`feature:015`).
- Missing or unreadable MediaScribe API key files now map to safe
  `blocked_config` instead of unmanaged file-system exceptions (`feature:015`).
- Production `rec-api` no longer mounts the MediaScribe API key Docker secret;
  only `rec-processing-worker` receives that secret (`feature:015`).

### Security

- MediaScribe credentials remain server-side through secret-file configuration;
  processing status, audit metadata, logs, and evidence must not expose raw
  audio, transcript text, signed URLs, API keys, bearer tokens, passwords, or
  live secret paths (`feature:015`, `T040`, `T065-T071`, `T086`).
- RLS hardening adds database-level tenant isolation coverage for accepted
  identity, auth/session/device, ingest, meeting, processing, transcript, audit,
  and dependency tables, while keeping product/admin bypass out of scope
  (`feature:031`, `T016-T037`).
- RLS post-review hardening now requires explicit auth-session lookup context,
  complete maintenance actor/reason/feature metadata, and fail-closed worker
  tenant scope before tenant-owned processing DB operations (`feature:031`,
  `CR-003`, `CR-005`, `CR-006`).
- RLS post-review hardening now preserves controlled auth/link conflict outcomes
  for globally unique provider identities, requires membership or bounded auth
  bootstrap guards for organization-scoped policies, and rejects unknown tenant
  context kinds at runtime (`feature:031`, `CR-004`, `CR-007`, `CR-008`).
- Provider link conflict/rejected paths now commit metadata-only auth audit
  evidence before returning controlled error responses (`feature:031`, `CR-009`).
- RLS validation now blocks before migrations or probes when
  `RLS_TEST_DATABASE_URL` points at the live `twobrain_rec` database
  (`feature:031`, `#734`, `#735`).
- Production RLS enforcement is now recorded as verified enabled and forced
  through read-only PostgreSQL catalog metadata: production Alembic
  `0005_rls_hardening` and all covered tables report RLS enabled/forced
  (`feature:032`, `T015-T020`).

### Docs

- Обновлён `AGENTS.md`:
  - добавлен раздел `Versioning And Changelog`;
  - закреплён процесс обязательного обновления `CHANGELOG.md`;
  - закреплён системный подход к SemVer и git-тегам релизов.
- Обновлены server README и current product status для границ `015`, fake
  dependency flow, и разделения будущих `016/017/018` поверхностей.
- Зафиксированы production deployment и real-recording e2e evidence для
  `015` без сохранения transcript text в tracked docs.
- Добавлены RLS rollout runbook, ADR `003-tenant-isolation-rls`, and current
  product-status notes for RLS rollout gates (`feature:031`, `T043`,
  `T049-T052`).
- Corrected stale `031` RLS rollout wording in product status, ADR, runbook,
  and quickstart so current docs reflect verified production enabled/forced
  state while preserving test-only destructive probe boundaries
  (`feature:032`, `T021-T027`).

### Ops

- Production smoke для desktop upload queue теперь выпускает временную Rec
  `AuthSession` вместо использования инфраструктурного smoke secret как bearer
  (`feature:014`, `T036-T038`).
- Добавлены production/dev Compose placeholders для Temporal и processing
  worker без live secrets (`feature:015`, `T010`, `T071`, `T085`).
- Remote CD теперь запускает Temporal и processing worker, которые нужны для
  production-проверки обработки (`feature:015`).
- Production Temporal теперь запускается на Postgres backend через Docker
  secret wrapper, а CD блокирует статический `POSTGRES_PWD` в compose config
  (`feature:015`).
- Production processing worker теперь может читать local-file Docker secrets,
  включая MediaScribe API key, при запуске из Compose (`feature:015`).
- Production processing worker больше не наследует smoke/awareness credential
  file settings, которые не нужны для MediaScribe processing (`feature:015`).
- Production smoke cleanup теперь удаляет 015 processing rows перед meeting
  cleanup, чтобы real processing e2e не оставлял residue в Postgres (`feature:015`).
- `015` развернут на `2brain.dev` (`master` at `4cda38c`) и проверен полным
  production e2e на реальной записи приложения: upload, pickup, Temporal
  worker, live MediaScribe, result import, content-safe status и cleanup
  прошли успешно (`feature:015`).
- Local CI and migration verification now reference RLS validation without
  using destructive live production probes (`feature:031`, `T041-T045`).
- RLS migration verification now blocks when the validation helper returns a
  blocked verdict, and the helper delegates to a real PostgreSQL policy suite
  when `RLS_TEST_DATABASE_URL` is supplied (`feature:031`, `CR-001`, `CR-002`).
- PostgreSQL RLS probes now use a non-owner probe role and a SQL-only UUID GUC
  helper, so validation checks enforced RLS behavior without superuser/owner
  bypass and avoids PL/pgSQL migration hangs observed on local PostgreSQL 14
  (`feature:031`, `CR-001`).
- Added production read-only RLS state verification output for covered-table
  counts, enabled/forced counts, failed tables, deployed commit, and Alembic
  revision (`feature:032`, `T015-T020`, `T028-T037`).

## [Unreleased Template]

### Added
### Changed
### Fixed
### Security
### Docs
### Ops
