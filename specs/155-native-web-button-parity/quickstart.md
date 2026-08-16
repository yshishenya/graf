# Quickstart Validation

## Focused native checks

```sh
swift test --package-path apps/macos --filter AppControlAccessibilityTests
swift test --package-path apps/macos --filter CaptureControlV5Tests
swift build --package-path apps/macos --product TwoBrainRecApp
```

## Manual UX check

1. Запустить локальное macOS-приложение через
   `apps/macos/Scripts/run-local-app.sh`.
2. Проверить в dark и light theme: Record, Stop, Pause/Resume, recovery,
   permission, support и settings buttons.
3. Сверить с веб-кабинетом: видимая высота 32 px, radius 7 px, primary
   `#8c73ff`, neutral surface/border, disabled/pressed/destructive contrast;
   switches and checkboxes use the same purple accent instead of the macOS blue.
4. Убедиться, что icon-only controls и Stop сохраняют доступную область не
   менее 40 px, labels и shortcuts не изменились.

## Closeout

```sh
git diff --check
git status --short --branch
```

This feature is currently validated locally. Do not run the full repository CI
for this iteration. Per `docs/agent-guidance/release-and-validation.md`, use
the fast lane at the PR boundary and the full lane only for a release candidate
or production validation.

## Deferred release validation

```sh
infra/scripts/ci-local.sh --full
git status --short --branch
```

The deferred command is not part of the current feature closeout. Production
deployment, notarization and release packaging remain out of scope.
