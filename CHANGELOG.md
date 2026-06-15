# Changelog

All notable changes to this project will be documented in this file.
This project follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and
Semantic Versioning 2.0.0.

## [Unreleased]

### Added

- Добавлена обязанность вести Changelog в репозитории для всех значимых изменений.
- Добавлена macOS desktop upload queue: durable local queue, truthful retry/upload states,
  server-mediated ingest mapping and compact queue UI (`feature:014`, `T001-T030`).
- Добавлен MVP experience/design handoff для `2brain Rec`: clean-room audit,
  native/web route boundaries, status matrices, screen specs и Figma v5
  full-flow redesign на базе Figma Simple Design System + Apple macOS 26
  reference, 36 top-level frames, 82 button reactions, 130 sidebar/nav
  reactions, 8 meeting-row/status-pill reactions и embedded server-owned
  speaker assignment для desktop shell (`feature:030`, `T001-T085`).

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
