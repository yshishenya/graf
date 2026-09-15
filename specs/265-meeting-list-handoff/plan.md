# Implementation Plan: Immediate meeting-list handoff after native recording upload

**Branch**: `265-meeting-list-handoff` | **Date**: 2026-09-15 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/265-meeting-list-handoff/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

После подтверждения серверного `meetingId` нативная очередь уже знает, что встреча
создана, но встроенный кабинет не получает отдельного сигнала перечитать список.
План добавляет в существующий `GRAFLocalRecordings.update` один переходный handoff:
он обнаруживает первое появление `meetingId`, один раз вызывает уже используемый
`requestMeetingListRefresh` с текущим состоянием формы и сохраняет локальный
заместитель до завершения авторитетного ответа списка. После `htmx:afterSwap`
серверная строка заменяет заместитель; если текущий контекст её не включает,
заместитель удаляется и не возвращается. Нового API, постоянного опроса и нового
нативного моста не требуется.

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: JavaScript ES2020+ в общем кабинете; существующий Swift-мост
остаётся без изменения контракта

**Primary Dependencies**: локальный HTMX 2.0.10, существующая форма списка,
Playwright 1.63.0 для браузерных сценариев

**Storage**: N/A для handoff-состояния; ожидание живёт только в памяти страницы

**Testing**: Node `--check`, Playwright browser scripts, pytest contract/unit
проверки, существующие XCTest source-boundary проверки при macOS-валидации

**Risk / Validation Lane**: `high-risk-product`: это исправление видимого пути
записи и отправки в macOS-клиенте, затрагивает локальную проекцию, доступность,
фокус, выбор, ошибки и границы авторитетного серверного списка. Изменение не
меняет аудиозапись, хранение, авторизацию или серверный протокол.

**Release Gate**: `no deploy` в этой ветке; перед слиянием нужны обязательные
GitHub-проверки `governance-fast`, `macos-pr`, `pr-metadata` на точном SHA.
Production release/deploy не входит в задачу.

**Target Platform**: встроенный WebView macOS GRAF Dev и обычный кабинет в
современном браузере; общий JavaScript должен оставаться совместимым с текущим
HTMX-путём

**Project Type**: веб-кабинет внутри desktop-приложения и серверный HTML-проекционный
слой

**Performance Goals**: не более одного авторитетного обновления на новый handoff;
100 повторных публикаций прогресса не создают дополнительных автоматических
запросов; нет постоянного таймера списка

**Constraints**: серверная строка остаётся источником истины; текущие поиск,
фильтры, сортировка, выбор, фокус, HTMX-защита от устаревших ответов, удаление,
ручная загрузка и существующий polling не должны регрессировать; локальные пути
и содержимое записи не попадают в браузерную телеметрию или новый интерфейс

**Scale/Scope**: один WebView и до 100 локальных handoff-ов в одной публикации;
изменение ограничено `cabinet.js` и его браузерным покрытием, без миграций и
изменений серверных схем/эндпоинтов

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

PASS — не меняются capture, аудио-маршрутизация, авторизация, хранение,
удаление или AI. Сохраняется видимая локальная запись и доступное управление;
сервер остаётся источником истины для встречи. Временное состояние не содержит
секретов, аудио или текста встречи и не записывается в хранилище. Используется
существующий локальный HTMX и независимый браузерный тестовый контур. Требуемые
высокорисковые UX-проверки описываются в `checklists/ux.md`.

## Validation Plan

1. Выполнить `quickstart.md`: переход без `meetingId` → с `meetingId`, один
   запрос, сохранение заместителя, замена серверной строкой, отсутствие дублей.
2. Проверить фильтры/поиск/сортировку, выбор и фокус, несколько одновременных
   handoff-ов, отсутствие повторов после 100 публикаций и штатный retry после
   ошибки списка.
3. Выполнить `node --check` для изменённого JavaScript и оба существующих
   browser-сценария `mixed-meeting-list` и `local-recording-focus`, а также новый
   `local-recording-handoff`.
4. Выполнить связанные pytest contract/unit проверки и `git diff --check`.
5. Для PR получить `governance-fast`, `macos-pr`, `pr-metadata` на точном SHA.
   Production deploy и `release-full` не требуются до отдельного запроса на
   релиз.

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```text
apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js
apps/server/tests/browser/local-recording-handoff.test.cjs
apps/server/tests/browser/mixed-meeting-list.test.cjs
apps/server/tests/browser/local-recording-focus.test.cjs
apps/server/tests/contract/test_cabinet_static_assets_contract.py
apps/server/tests/unit/test_cabinet_web_shell.py
apps/server/tests/unit/test_meeting_progress_ui.py
apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetWebView.swift
apps/macos/Shared/Tests/DesktopMeetingShellWebViewBoundaryTests.swift
specs/265-meeting-list-handoff/
```

**Structure Decision**: Серверный кабинет остаётся владельцем смешанного DOM и
существующей HTMX-синхронизации. Нативный Swift-код продолжает публиковать ту же
`GRAFLocalRecordings.update`-проекцию; новый браузерный handoff обнаруживается в
общем JavaScript-слое, поэтому ручная загрузка и desktop upload callback не
получают дублирующей логики. Покрытие добавляется в существующий browser-контур,
а исходные contract/unit проверки используются для регрессий.

## Implementation Design

1. До замены `localRecordingRows` сравнить текущую публикацию с предыдущей по
   стабильному local ID. Переход без `meetingId` к строковому `meetingId` и
   первое наблюдение уже связанной записи после загрузки WebView становятся
   новым handoff; повторный прогресс его не повторяет.
2. Для нового handoff, которого ещё нет среди серверных строк, добавить его
   `meetingId` в короткий набор ожидания. `renderLocalRecordingRows` оставляет
   такую локальную строку видимой; обычные строки с уже известным `meetingId`
   по-прежнему не восстанавливаются поверх серверного списка.
3. Вызвать `requestMeetingListRefresh` с несколькими handoff-идентификаторами
   одним запросом. Если список ещё не доступен, сохранить handoff до появления
   формы; пометить идентификатор отправленным только после запуска запроса.
   Передать `restoreFocus` только если фокус находится в списке, чтобы модальные
   окна и ввод пользователя не потеряли фокус.
4. В обработчике `htmx:afterSwap` считать ответ авторитетным: matching server
   row переносит selection/focus и удаляет локальный заместитель; отсутствие
   строки снимает ожидание, сохраняя фильтры и границу текущего списка.
5. При сетевой ошибке использовать существующее состояние восстановления и
   оставить ожидающую локальную строку в том же списке; штатная кнопка retry
   повторяет обычный запрос формы.

Намеренно не меняются `DesktopUploadClient`, `DesktopUploadQueueService`,
`EmbeddedCabinetLocalRecordingBridge`, API `/api/v1/meetings` и серверная модель:
непосредственная причина находится в том, что локальная проекция удаляется до
первого запроса списка, а сам запрос не был вызван.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | The design reuses the existing refresh, HTMX fencing, and focus-recovery paths. |
