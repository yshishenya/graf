# Implementation Plan: Восстановление скачивания аудио

**Branch**: `127-audio-download-recovery` | **Date**: 2026-07-25 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/127-audio-download-recovery/spec.md`

## Summary

Восстановить переход по существующей ссылке «Скачать аудио…» из меню действий встречи. Текущий общий `click`-обработчик синхронно скрывает родительское меню до выполнения стандартного действия ссылки; во встроенном WebKit это может отменить навигацию к server-mediated download. Закрытие меню для ссылок будет отложено на следующий macrotask, чтобы сначала сохранить стандартный переход/скачивание. Серверный endpoint, авторизация, policy и native WebKit download flow сохраняются; проверка актуальности текстовой ревизии применяется только к текстовым артефактам и не блокирует независимый playback-аудиоартефакт.

## Technical Context

**Language/Version**: JavaScript ES2020+ в server-rendered кабинете; Python 3.11+ tests; Swift 5.9+ существующего macOS shell

**Primary Dependencies**: существующий cabinet JS, Jinja templates, pytest, Node.js syntax check, XCTest

**Storage**: без изменений; аудио остаётся server-mediated stored review artifact

**Testing**: focused pytest contract tests; `node --check`; focused macOS XCTest; `infra/scripts/ci-local.sh`

**Risk / Validation Lane**: `high-risk-feature`: пользовательский egress-путь скачивания, embedded WebKit, permissions/fail-closed states и UX; требуется полный Spec Kit flow и repository gate

**Release Gate**: `no deploy`: пользователь не просил релиз или production rollout; deployment checks не являются частью этой правки

**Target Platform**: server-rendered browser cabinet и macOS embedded WKWebView

**Project Type**: web-service плюс macOS desktop shell

**Performance Goals**: не добавлять сетевых запросов, задержка закрытия меню не должна быть заметна пользователю

**Constraints**: не отменять native/default navigation ссылки; не передавать аудио через JS; не раскрывать storage URL; не менять policy, retention или lifecycle

**Scale/Scope**: один общий menu click-handler, один static contract test, существующие server и macOS download contracts

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

* PASS: сохранён server-mediated egress через `/api/v1/cabinet/meetings/{meeting_id}/downloads/audio`; клиент не получает storage URL и не хранит MediaScribe credentials.
* PASS: существующие permissions, auth, playback artifact и fail-closed правила не изменяются.
* PASS: diagnostics/evidence остаются metadata-only; аудио, transcript, private meeting content и signed URLs не попадают в тестовые артефакты.
* PASS: macOS system-audio-first MVP и clean-room UI scope не затрагиваются.

## Validation Plan

1. До кода: checklist requirements/UX/access-egress и read-only analyze без критических findings.
2. Focused: `node --check apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js` и contract tests для menu/download behavior.
3. Existing egress guard: artifact integration tests при доступном local PostgreSQL; если окружение не поднято, зафиксировать blocker отдельно, не ослабляя contract checks.
4. macOS: `swift test --filter DesktopCabinetConfigurationTests` и `swift test --filter DesktopCabinetRoutePolicyTests`.
5. Closeout: `infra/scripts/ci-local.sh`; deploy не выполняется, потому что release gate не достигнут.

## Project Structure

### Documentation (this feature)

```text
specs/127-audio-download-recovery/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/meeting-audio-download.md
├── checklists/requirements.md
├── checklists/ux.md
├── checklists/access-egress.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js
apps/server/tests/contract/test_recording_governance_ui_contract.py
apps/macos/Shared/Sources/Cabinet/             # existing route/download policy, unchanged
apps/macos/Shared/Tests/DesktopCabinetConfigurationTests.swift
apps/macos/Shared/Tests/DesktopCabinetRoutePolicyTests.swift
CHANGELOG.md
```

**Structure Decision**: исправление остаётся в общем server-rendered menu handler и общем egress guard; существующий macOS navigation policy покрывается текущими контрактами и не дублируется новым слоем. Аудио проверяется через собственный валидированный playback artifact, а revision guard остаётся для transcript/summary.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Нет | — | Конституция не нарушена |
