# Changelog

All notable changes to this project will be documented in this file.
This project follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and
Semantic Versioning 2.0.0.

## [Unreleased]

### Added

- Добавлена обязанность вести Changelog в репозитории для всех значимых изменений.
- Добавлена macOS desktop upload queue: durable local queue, truthful retry/upload states,
  server-mediated ingest mapping and compact queue UI (`feature:014`, `T001-T030`).

### Changed

- Синхронизирован Speckit workflow с обязательными этапами `clarify`,
  `checklist`, `analyze`, `taskstoissues`, чтобы требования и контроль качества
  были сквозными.

### Fixed

- В `.github` и процессе разработки зафиксирован порядок этапов и коммитов для
  Spec Kit.

### Docs

- Обновлён `AGENTS.md`:
  - добавлен раздел `Versioning And Changelog`;
  - закреплён процесс обязательного обновления `CHANGELOG.md`;
  - закреплён системный подход к SemVer и git-тегам релизов.

### Ops

- Production smoke для desktop upload queue теперь выпускает временную Rec
  `AuthSession` вместо использования инфраструктурного smoke secret как bearer
  (`feature:014`, `T036-T038`).

## [Unreleased Template]

### Added
### Changed
### Fixed
### Security
### Docs
### Ops
