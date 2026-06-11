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

### Changed

- Синхронизирован Speckit workflow с обязательными этапами `clarify`,
  `checklist`, `analyze`, `taskstoissues`, чтобы требования и контроль качества
  были сквозными.

### Fixed

- В `.github` и процессе разработки зафиксирован порядок этапов и коммитов для
  Spec Kit.
- MediaScribe client now follows the live production contract for polling and
  result import via `/jobs/{job_id}` and normalizes `start`/`end`/`speaker`
  fields into persisted processing rows (`feature:015`).

### Security

- MediaScribe credentials remain server-side through secret-file configuration;
  processing status, audit metadata, logs, and evidence must not expose raw
  audio, transcript text, signed URLs, API keys, bearer tokens, passwords, or
  live secret paths (`feature:015`, `T040`, `T065-T071`, `T086`).

### Docs

- Обновлён `AGENTS.md`:
  - добавлен раздел `Versioning And Changelog`;
  - закреплён процесс обязательного обновления `CHANGELOG.md`;
  - закреплён системный подход к SemVer и git-тегам релизов.
- Обновлены server README и current product status для границ `015`, fake
  dependency flow, и разделения будущих `016/017/018` поверхностей.

### Ops

- Production smoke для desktop upload queue теперь выпускает временную Rec
  `AuthSession` вместо использования инфраструктурного smoke secret как bearer
  (`feature:014`, `T036-T038`).
- Добавлены production/dev Compose placeholders для Temporal и processing
  worker без live secrets (`feature:015`, `T010`, `T071`, `T085`).
- Remote CD теперь запускает Temporal и processing worker, которые нужны для
  production-проверки обработки (`feature:015`).

## [Unreleased Template]

### Added
### Changed
### Fixed
### Security
### Docs
### Ops
