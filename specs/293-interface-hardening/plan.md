# Implementation Plan: Сквозное укрепление интерфейса GRAF

**Branch**: `293-interface-hardening` | **Date**: 2026-11-10 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/293-interface-hardening/spec.md`

## Summary

Сделать интерфейс GRAF предсказуемым и проверяемым: типизировать состояние записи и блокировки, убрать разбор пользовательского текста, исправить меню/сочетания клавиш/сброс контекста при смене аккаунта, вынести тяжёлые операции из пути отрисовки, удалить подтверждённо неиспользуемый код и добавить поведенческие тесты. После проверок выпустить нотаризованный macOS-релиз `v2026.11.10.3` с обновлением Sparkle.

## Technical Context

**Language/Version**: Swift 6.0.3 (CI) / macOS 14+, Python 3.12, Jinja/HTML/CSS/JavaScript без отдельного frontend-toolchain.

**Primary Dependencies**: SwiftUI, AppKit, WebKit, Sparkle 2.9.4, XCTest, pytest, Playwright (browser tests), существующий FastAPI-кабинет.

**Storage**: локальная очередь записей и manifests в Application Support; серверные PostgreSQL/MinIO не меняются.

**Testing**: `swift test --package-path apps/macos`, focused `infra/scripts/ci-local.sh --focused`, обязательные GitHub `governance-fast`, `macos-pr`, `pr-metadata`, один `release-full` на замороженном кандидате.

**Risk / Validation Lane**: high-risk-feature. Затрагиваются запись, видимая остановка, разрешения, приватность смены аккаунта, доступность, меню и публичный выпуск macOS.

**Release Gate**: `cd-remote.sh --dry-run` перед production execution; публикация только после полного `release-full`, Developer ID, нотаризации, stapling, Gatekeeper и Sparkle-проверки.

**Target Platform**: macOS 14+ Apple Silicon; self-hosted сервер `https://rec.2brain.pro`.

**Project Type**: desktop-app + web-service monorepo.

**Performance Goals**: отклик основной кнопки и переключения панели ≤100 мс при 60-минутной записи и очереди из 100 записей; отсутствие файловых проверок и перечисления аудиоустройств в пути отрисовки.

**Constraints**: русскоязычный интерфейс; Developer ID-only публикация; один установленный GRAF Dev для ручных проверок; без нового frontend-toolchain; не ослаблять гейты записи, приватности, удаления и диагностики.

**Scale/Scope**: основная macOS-оболочка, панель записи, встроенный кабинет, меню-бар, настройки, онбординг разрешений, карточка уведомлений, веб-CSS кабинета; без изменения серверной бизнес-логики.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Capture-First MVP Integrity**: PASS. Захват, системный звук и микрофон не меняются; меняются представление состояния, путь отрисовки и доступ к остановке. Обязательные метрики и матрица деградации сохраняются.
- **II. Visible Consent And User Control**: PASS. Видимый индикатор и одношаговый Stop сохраняются; добавляется глобальное действие остановки. Трёхсостояние автозаписи и восьмисекундный отсчёт не затрагиваются.
- **III. Plaintext Observability**: PASS. Серверная телеметрия и AI-контуры не меняются; логи только ограничиваются и редактируются.
- **IV. Deletion Truth**: PASS. Тексты удаления и жизненный цикл не ослабляются.
- **V. Public macOS Distribution**: PASS. Релиз только Developer ID, notarization, staple, Gatekeeper, Sparkle.
- **VI. Spec-Driven Delivery**: PASS. Выполняется полный Spec Kit flow с clarify, checklist, analyze и release gates.
- **VII. Reference-Fidelity**: PASS. Визуальный язык не переписывается; исправляются состояния, доступность и согласованность в рамках существующего утверждённого дизайна.

Пост-дизайн: нарушения не выявлены; сложность оправдана существующим монолитом и требованиями тестируемости.

## Validation Plan

- Focused: `swift build --package-path apps/macos`, `swift test --package-path apps/macos --filter` по затронутым тестам, `pytest` по CSS/шаблонным контрактам.
- `infra/scripts/ci-local.sh --fast` — локальная диагностика; не заменяет GitHub.
- Обязательные GitHub checks на точном PR SHA: `governance-fast`, `macos-pr`, `pr-metadata`.
- `release-full` на замороженном кандидате.
- Ручная матрица состояний в `/Applications/GRAF Dev.app` через `dev-harness` (без отдельной копии приложения).
- Release: `release-app-update.sh --phase prepare`, публикация тега, `--phase publish --verify-feed`.
- `cd-remote.sh --dry-run` перед production execution.

## Project Structure

### Documentation (this feature)

```text
specs/293-interface-hardening/
├── plan.md
├── research.md
├── data-model.md
├── contracts/
│   ├── interface-contract.md
│   └── release-contract.md
├── quickstart.md
├── checklists/
│   ├── requirements.md
│   ├── ux.md
│   ├── audio-capture.md
│   └── security.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/macos/RecApp/App/
└── TwoBrainRecApp.swift                 # тонкий @main shim

apps/macos/RecApp/Sources/
├── AppShell/
│   ├── ContentView.swift                # перенос из App, тестируемый shell
│   ├── AppLifecycleDelegate.swift       # окна, меню, завершение
│   ├── AppMenuBuilder.swift             # меню и сочетания клавиш
│   ├── AppLog.swift                     # ограниченный асинхронный лог
│   └── InterfacePreferences.swift       # окно, панель, микрофон
├── Capture/
│   ├── CaptureStatusPresentation.swift  # типизированные статусы
│   ├── RecordingBlockerPresentation.swift
│   └── LocalRecordingPresentation.swift
├── Cabinet/
│   ├── CabinetStatusPresentation.swift
│   └── AccountSwitchResetPolicy.swift
├── DesignSystem/
│   ├── DesktopDesignTokens.swift        # перенос из Cabinet
│   ├── DesktopWebButtonStyle.swift      # перенос из Cabinet
│   └── DesktopMeetingShellChrome.swift  # перенос из Cabinet
├── Notifications/
│   └── DesktopNotificationCardPresenter.swift
└── ... существующие feature-папки

apps/macos/Shared/Tests/
├── AppShellBehaviorTests.swift
├── CaptureStatusPresentationTests.swift
├── AccountSwitchResetTests.swift
├── AppMenuBuilderTests.swift
└── InterfacePerformanceContractTests.swift

apps/server/src/twobrain_rec_server/cabinet/static/cabinet/
└── cabinet.css                         # удаление подтверждённо мёртвых классов
```

**Structure Decision**: существующий single-package macOS target сохраняется. `TwoBrainRecAppCore` расширяется перенесённым app-shell, а executable target остаётся тонким. Это даёт тестам доступ к `ContentView` и меню без запуска приложения. Веб-кабинет остаётся в существующем серверном пакете без отдельного JS-тулчейна.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Перенос крупного `ContentView` в библиотеку | Без этого поведение нельзя тестировать; source-text тесты блокируют любой рефакторинг | Оставить в executable и проверять исходники — уже доказало хрупкость |
| Общие типы представления для Capture/Cabinet/Notifications | Устраняет расхождение статусов и скрытые ошибки при изменении текста | Дублировать строки по-прежнему — поведение зависит от копирайта |
| Глобальное действие Stop | Требование видимой записи и одношаговой остановки при закрытом окне | Полагаться на меню-бар — это два действия, а не одно |
| Кэширование и вынос I/O из body | Иначе 5 Гц обновления уровней вызывает файловые/device-операции | Оставить как есть — риск подтормаживания в встрече |
| Общий контракт токенов CSS/Swift | Палитра уже синхронизируется вручную и может разойтись | Доверять комментариям — нет автоматической проверки |
