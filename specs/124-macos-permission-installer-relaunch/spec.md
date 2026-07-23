# Feature Specification: Надёжная установка и выдача разрешений GRAF

**Feature Branch**: `codex/124-macos-permission-installer-relaunch`

**Created**: 2026-07-23

**Status**: Ready for implementation planning

**Input**: User description: "Исправить проблемы установки GRAF на Mac, выдачи разрешения микрофону и перезапуска после разрешения записи экрана и системного звука без Apple Developer account."

## User Scenarios & Testing

### User Story 1 - Установка приложения на чужом Mac (Priority: P1)

Как новый пользователь GRAF, я хочу установить приложение из предоставленного
пакета и понять, какое единственное ручное подтверждение безопасности требуется
от macOS, чтобы не принять штатное предупреждение Gatekeeper за поломку продукта.

**Why this priority**: Без предсказуемого первого запуска пользователь не может
дойти до выдачи разрешений и записи.

**Independent Test**: На Mac без ранее установленного GRAF открыть свежий пакет,
пройти документированный системный trust-шаг, установить приложение в
`/Applications` и запустить его без Terminal-команд.

**Acceptance Scenarios**:

1. **Given** пакет получен из источника без Apple Developer/notarization trust,
   **When** macOS показывает предупреждение, **Then** экран установки объясняет,
   что это ожидаемое ограничение текущего бесплатного канала, и даёт один
   безопасный путь ручного подтверждения через системные настройки или Finder.
2. **Given** пользователь завершил ручное подтверждение, **When** он повторно
   запускает установку, **Then** GRAF устанавливается как `GRAF.app` в
   `/Applications`, а пользователь не должен добавлять аудиодрайверы или
   выполнять команды с повышенными правами для обычной записи.
3. **Given** пакет или приложение изменены после сборки, **When** выполняется
   проверка артефакта, **Then** проверка останавливается и не предлагает считать
   изменённый артефакт безопасным.

### User Story 2 - Выдача разрешения микрофону (Priority: P1)

Как новый пользователь GRAF, я хочу выдать доступ к микрофону из самого GRAF,
а при уже принятом или отклонённом решении получить понятное восстановление,
чтобы приложение появилось в правильном разделе настроек и запись речи стала
доступна.

**Why this priority**: Микрофон — обязательная отдельная дорожка MVP; статус
«запрещено» без работающего восстановления делает запись невозможной.

**Independent Test**: На Mac с неизвестным решением по микрофону открыть GRAF,
нажать действие разрешения, принять системный запрос, вернуться в GRAF и
проверить готовность микрофона; затем отдельно проверить уже отклонённое
решение.

**Acceptance Scenarios**:

1. **Given** решение по микрофону ещё не принято, **When** пользователь нажимает
   «Разрешить микрофон», **Then** macOS показывает запрос с объяснением причины,
   а после согласия GRAF показывает состояние «Готово» без ручного редактирования
   системных баз или скрытого обхода TCC.
2. **Given** пользователь ранее отказал в доступе, **When** он нажимает действие
   восстановления, **Then** GRAF открывает раздел настроек микрофона и объясняет,
   что повторный системный prompt не гарантируется после отказа.
3. **Given** macOS ограничивает доступ политикой устройства, **When** GRAF
   проверяет состояние, **Then** приложение показывает «Ограничено», не обещает
   обход ограничения и оставляет запись заблокированной до изменения политики.

### User Story 3 - Разрешение системного звука и перезапуск (Priority: P1)

Как пользователь GRAF, я хочу выдать разрешение записи экрана и системного звука
и перезапустить GRAF одной понятной операцией, чтобы модальное окно подготовки
не блокировало системный «Quit & Reopen» и приложение после возврата из настроек
показывало актуальное состояние.

**Why this priority**: Screen/System Audio permission применяется macOS только
после повторного запуска, поэтому зависший перезапуск блокирует основной путь
к записи даже при уже выданном разрешении микрофону.

**Independent Test**: Открыть GRAF с отсутствующим Screen/System Audio доступом,
перейти в настройки, включить доступ, нажать системный «Quit & Reopen» либо
встроенное действие перезапуска и проверить выход старого процесса, новый запуск
и обновлённый статус.

**Acceptance Scenarios**:

1. **Given** системный звук не разрешён, **When** пользователь открывает
   восстановление, **Then** GRAF ведёт в раздел «Запись экрана и системного
   звука», отдельно показывает статус системного звука и не смешивает его с
   микрофоном.
2. **Given** macOS запросила перезапуск после изменения доступа, **When**
   пользователь нажимает «Quit & Reopen» или «Перезапустить GRAF», **Then**
   подготовительное модальное окно закрывается до ответа на запрос завершения,
   старый процесс завершается не позднее 10 секунд, а GRAF запускается заново.
3. **Given** активна запись, остановка или финализация локального файла, **When**
   система или пользователь инициирует перезапуск, **Then** GRAF сохраняет
   существующий safety gate, не скрывает запись и завершает только после
   bounded cleanup либо честно фиксирует ограниченный timeout.
4. **Given** пользователь возвращается из настроек без выдачи доступа, **When**
   GRAF становится активным, **Then** статус перечитывается, модальное окно не
   закрывает проблему ложным «Готово», а следующий recovery-шаг остаётся видимым.

## Edge Cases

- Gatekeeper блокирует повторное открытие пакета после первой неудачной попытки;
  пользователь должен получить тот же документированный trust-шаг, а не
  инструкцию отключить защиту macOS целиком.
- Приложение запущено не из `/Applications` или установлено поверх старого
  приложения с другой подписью; GRAF должен явно показать путь/идентичность
  проблемы и не обещать сохранение разрешений.
- Пакет запускается на Mac, где сертификат локального канала отсутствует или
  не доверен; это должно быть обозначено как ограничение канала, а не как
  разрешение на ручное изменение TCC.
- Микрофон был отклонён, но GRAF ещё не отображается в списке микрофона;
  приложение должно повторить нормальный API-запрос до первого отказа, после
  отказа — открыть настройки и объяснить следующий шаг.
- Пользователь изменил только один из двух доступов; каждый статус и recovery
  action остаются независимыми.
- Системные настройки отправили запрос на завершение в момент, когда SwiftUI
  sheet видим, а AppKit modal window отсутствует в ожидаемой иерархии.
- Перезапуск запрошен повторно до окончания первого cleanup; второй запрос не
  должен создавать дублирующиеся continuation или зависший процесс.

## Requirements

### Functional Requirements

- **FR-001**: GRAF MUST сохранять стабильный bundle identifier `pro.2brain.graf`
  и единое имя `GRAF.app` во всех локальных install/update артефактах.
- **FR-002**: Installer MUST явно проверять целостность приложения и вложенного
  кода до установки и останавливать процесс при нарушении проверки.
- **FR-003**: Installer MUST документировать ровно один ручной Gatekeeper trust
  path для бесплатного локального канала и MUST NOT обещать автоматическое
  прохождение Gatekeeper без Apple Developer/notarization.
- **FR-004**: GRAF MUST include user-facing privacy explanations for microphone
  capture and Screen/System Audio capture in the installed app metadata.
- **FR-005**: GRAF MUST request microphone authorization through the normal
  macOS media-capture flow before starting microphone capture.
- **FR-006**: GRAF MUST show microphone states independently as unknown, granted,
  denied or restricted and MUST map denied/restricted states to truthful recovery
  copy.
- **FR-007**: After a microphone denial, GRAF MUST open the macOS microphone
  settings and MUST NOT claim that it can reset or bypass the user's decision.
- **FR-008**: GRAF MUST keep Screen/System Audio authorization separate from
  microphone authorization and open the corresponding macOS settings section.
- **FR-009**: GRAF MUST expose an explicit restart action when the system-audio
  permission change requires a new app process.
- **FR-010**: Before replying to a macOS termination request, GRAF MUST dismiss
  permission onboarding, meeting prompts, attached/detached modal windows and
  any active modal session that can block termination.
- **FR-011**: GRAF MUST return a termination reply within 10 seconds, preserving
  the existing bounded capture cleanup and metadata-only lifecycle events.
- **FR-012**: GRAF MUST refresh permission state after returning from System
  Settings and after relaunch; the UI MUST NOT show ready until both required
  permissions are actually granted.
- **FR-013**: GRAF MUST NOT reset TCC, edit TCC databases, install PPPC profiles,
  install the removed audio-routing driver, or make active capture invisible.
- **FR-014**: Release and user-facing documentation MUST distinguish the free
  local/self-signed path from public Developer ID signing, notarization and
  Gatekeeper-ready distribution.

### Key Entities

- **Install artifact**: The package and embedded GRAF application delivered to a
  Mac, with bundle identity, privacy descriptions, code integrity and trust
  channel metadata.
- **Permission state**: The independently observed microphone and Screen/System
  Audio authorization states used to decide whether recording may start.
- **Termination request**: A macOS or user restart/quit request with modal state,
  cleanup state, bounded reply and relaunch outcome.

## Success Criteria

### Measurable Outcomes

- **SC-001**: On a clean test Mac, a user can install and launch the free-channel
  build after one documented Gatekeeper confirmation without Terminal commands or
  disabling all macOS security settings.
- **SC-002**: In a first-run microphone test, GRAF appears in the microphone
  permission flow and reaches `granted` after one user approval in at least 4 of
  4 repeated runs.
- **SC-003**: After a prior microphone denial, the recovery action opens the
  microphone settings within 2 seconds and never reports `granted` without a
  fresh permission read.
- **SC-004**: After granting Screen/System Audio, both restart paths (macOS
  «Quit & Reopen» and GRAF's explicit restart) exit the old GRAF process within
  10 seconds in 4 of 4 runs, including with the preparation modal visible.
- **SC-005**: After successful relaunch, the permission sheet is absent when both
  permissions are granted, and the recording control becomes available without
  a second manual grant.
- **SC-006**: Focused macOS tests, installer checks and the repository validation
  gate pass without adding a privileged audio component, TCC mutation or new
  runtime dependency.

## Assumptions

- The current MVP remains macOS 14.5+ on Apple Silicon and uses native
  system-audio-first capture with a separate microphone track.
- The user accepts one manual Gatekeeper confirmation for a no-account build;
  eliminating that confirmation for arbitrary external Macs requires Apple's
  Developer ID and notarization path and is out of scope here.
- The existing bundle identifier, package layout, SwiftUI/AppKit lifecycle,
  permission services and focused XCTest target are reused.
- Validation evidence records only metadata and permission state labels; it does
  not include raw audio, transcript text, credentials or private meeting data.

## Out of Scope

- Apple Developer enrollment, Developer ID certificates, notarization,
  stapling, Mac App Store submission or universal public Gatekeeper trust.
- MDM/PPPC fleet deployment or administrator-managed permission grants.
- TCC reset commands as product behavior, direct TCC database edits or hidden
  permission grants.
- Reintroducing the removed separate audio-routing/HAL driver implementation.

## Clarifications

- **2026-07-23**: The no-account channel keeps one explicit Finder/System
  Settings Gatekeeper confirmation. Removing that confirmation for an arbitrary
  colleague's Mac is not a code-only fix; it requires Developer ID signing and
  notarization, which remain out of scope.
- **2026-07-23**: The public package is not replaced or deployed by this slice.
  The implementation makes the local artifact and download instructions honest
  and usable; release publication remains a separately approved operation.
- **2026-07-23**: The restart fix stays inside the existing SwiftUI/AppKit
  lifecycle. It closes the onboarding sheet and aborts any active AppKit modal
  session before the existing bounded `terminateLater` cleanup replies to
  macOS.
