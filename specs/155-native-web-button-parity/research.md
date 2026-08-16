# Research: Feature 155

## Findings

1. Веб-кабинет задаёт базовый control contract в
   `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`:
   `min-height: 32px`, `border-radius: 7px`, горизонтальный padding `12px`,
   action accent `#8c73ff`, dark secondary surface `#26282c` и line `#30343a`.
   Синий `--blue: #2f91ff` используется отдельными blue-status controls, а не
   основными action-кнопками.
2. Нативный macOS слой использует несколько системных путей одновременно:
   `.bordered`, `.borderedProminent`, `.controlSize(.small)` и локальные
   `Color`/`frame` значения. Это объясняет разницу и делает исправление в
   каждом caller хрупким.
3. `DesktopMeetingShellChrome.controlHeight` используется как общий размер
   capture-кнопок в shell, `CaptureControlView` и `CaptureStatusItem`; его
   изменение на 32 px выравнивает базовые текстовые кнопки без изменения
   критических hit-area, которые используют отдельные 40/44 px constants.
4. Действия, labels, keyboard shortcuts и accessibility identifiers уже
   покрыты существующими XCTest/source-contract checks. Новый style path можно
   проверить отдельным контрактом без запуска реального capture.

## Decisions

- Ввести один переиспользуемый SwiftUI `ButtonStyle` для web-parity кнопок.
- Разделить варианты `primary`, `secondary` и `destructive`; destructive
  сохраняет красный текстовой смысл, но не меняет действие и подтверждение.
- Использовать `@Environment(\.colorScheme)` и web tokens для light/dark тем.
- Оставить icon-only controls и их 40/44 px hit-area вне базовой высоты 32 px.
- Не менять `cabinet.css`, серверные маршруты, capture flow или auth flow.

## Deferred / Not Needed

- Pixel-perfect screenshot diff и новая UI automation harness не нужны для
  этого узкого style-token изменения.
- Новые зависимости, asset pipeline и отдельная дизайн-система не нужны.
