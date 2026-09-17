> Путь запуска обновлён: используйте единственный `/Applications/GRAF Dev.app` через `infra/scripts/dev-harness.sh`; см. [действующую инструкцию](/docs/agent-guidance/local-development.md). Старые отдельные приложения больше не собираются.

# Quickstart: Источник системного звука в индикаторе записи

## Prerequisites

- macOS 14+ host with the repository checked out.
- Existing Swift package dependencies resolved.
- No production credentials or meeting content are needed.

## Focused validation

From the repository root:

```sh
swift test --package-path apps/macos --filter CaptureIndicatorTests
swift test --package-path apps/macos --filter AppControlAccessibilityTests
```

Expected: focused XCTest suites pass, including known-app, manual-system-audio, unknown-source, lifecycle, truncation/accessibility, and preserved action contracts.

## Local app smoke

On a macOS host with capture permissions:

```sh
infra/scripts/dev-harness.sh status --json
```

После build/promote/smoke выбранного SHA откройте `/Applications/GRAF Dev.app` и проверьте:

1. Start a detector-assisted recording for a verified meeting app. The upper card shows «Идёт запись» and «Источник: `<app>`».
2. Start a manual recording. The upper card shows «Источник: Системный звук».
3. Pause, resume, and stop. The source stays stable while the session is active and the existing actions remain available.
4. Use a narrow window or a long app name. The row remains single-line; the full name is available through VoiceOver/help.

## Repository gate

Before closeout run:

```sh
infra/scripts/ci-local.sh --fast
```

No deploy, release, notarization, or appcast check is part of this feature.
