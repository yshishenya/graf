# Feature Specification: Восстановление автозаписи встреч

**Feature Branch**: `124-restore-automatic-recording`

**Created**: 2026-07-23

**Status**: Implemented and re-reviewed on branch; focused validation and full
local CI passed; release/commit approval pending

**Input**: User description: "Вернуть таймер, автоматический старт, чекбокс
«больше не спрашивать», настройки и список приложений от Feature 092/119;
закрепить этот контракт в коде и документации, чтобы его снова не удалили."

## Context And Decision

Feature 121 намеренно упростила путь обнаружения встреч до detect-and-ask и
удалила из текущего интерфейса таймер, автоматический старт, opt-in чекбокс и
список приложений. Это было временное решение для safety/consent UX, но оно
удалило ранее продуманный и уже реализованный target-scoped workflow из
Feature 092/119. Feature 124 восстанавливает этот workflow с его safety-gates;
это не разрешение на запись произвольного системного звука и не возврат
устаревшего audio-routing слоя.

Настоящий контракт имеет приоритет над временными формулировками Feature 121.
Исторические документы Feature 121 должны оставаться правдивыми о том, что
было сделано в той фиче, но явно ссылаться на Feature 124 как на текущий
superseding contract.

## User Scenarios & Testing

### User Story 1 - Автоматически писать выбранные приложения (Priority: P1)

Как пользователь, который регулярно проводит встречи в известных приложениях,
я хочу один раз разрешить автозапись для конкретного приложения, чтобы GRAF
сам начинал запись следующих встреч без повторного вопроса.

**Why this priority**: Фоновая автозапись встреч — одна из основных ценностей
продукта. Повторный ручной запуск для каждой встречи приводит к пропущенным
записям.

**Independent Test**: Включить автозапись для одного зарегистрированного
приложения, подать валидное событие встречи и убедиться, что запись стартует
только для этого приложения, видима локально и останавливается одной командой.

**Acceptance Scenarios**:

1. **Given** зарегистрированное приложение отмечено для автозаписи,
   разрешения захвата выданы, политика разрешает запись и встреча уверенно
   обнаружена, **When** detector подтверждает встречу, **Then** запись
   стартует автоматически без нового вопроса.
2. **Given** автозапись разрешена для приложения A, **When** встреча обнаружена
   только в приложении B, **Then** правило A не применяется к B.
3. **Given** автозапись начала запись, **When** пользователь нажимает Stop,
   **Then** запись немедленно останавливается, а последующее событие встречи
   не запускает второй параллельный сеанс.

### User Story 2 - Видимый вопрос с таймером и запоминанием выбора (Priority: P1)

Как пользователь, который ещё не настроил приложение, я хочу увидеть вопрос о
начале записи с таймером, иметь возможность начать сразу или отказаться, а
также выбрать «Всегда писать это приложение», чтобы следующий вопрос для этого
приложения больше не появлялся.

**Why this priority**: Пользователь должен одновременно получать предсказуемый
контроль и не пропускать начало встречи, если он не успел нажать кнопку.

**Independent Test**: Подать встречу для приложения без сохранённого правила,
проверить видимый восьмисекундный countdown, немедленный Start, dismiss,
автоматический старт по окончании countdown и сохранение opt-in выбора.

**Acceptance Scenarios**:

1. **Given** встреча обнаружена в зарегистрированном приложении без правила
   автозаписи, **When** появляется prompt, **Then** prompt показывает
   восьмисекундный countdown, primary action «Записать сейчас», dismiss
   action «Пропустить», а также чекбокс «Всегда писать это приложение».
2. **Given** prompt показывает countdown, **When** пользователь нажимает
   «Записать сейчас», **Then** запись стартует сразу и countdown отменяется.
3. **Given** prompt показывает countdown, **When** countdown достигает нуля
   без отмены и запись разрешена всеми gates, **Then** запись стартует
   автоматически и остаётся видимой локально.
4. **Given** пользователь отмечает «Всегда писать это приложение» и начинает
   запись, **When** следующая встреча обнаруживается в том же приложении,
   **Then** prompt больше не спрашивает разрешение, а target-scoped правило
   запускает автозапись.
5. **Given** пользователь нажимает «Пропустить», **Then** текущий prompt
   закрывается без записи и без изменения сохранённого правила автозаписи.

### User Story 3 - Управлять полным списком приложений (Priority: P1)

Как пользователь, я хочу в настройках видеть все проверенные native meeting
applications и отдельно включать или выключать автозапись для каждого из них,
чтобы понимать и контролировать, откуда GRAF может начать запись.

**Why this priority**: Без полного списка невозможно проверить границы
разрешения и восстановить ранее настроенный workflow.

**Independent Test**: Открыть настройки, сопоставить список с текущим
реестром, включить/выключить одну строку, использовать «Выбрать все» и
«Снять все», перезапустить приложение и проверить сохранённые значения.

**Acceptance Scenarios**:

1. **Given** в реестре есть проверенные native targets, **When** пользователь
   открывает настройки meeting detection, **Then** каждый target появляется в
   одном общем списке с понятным названием, идентификатором/описанием и
   отдельным auto-record toggle.
2. **Given** пользователь меняет toggle одного приложения, **When** он снова
   открывает настройки, **Then** изменение сохранено только для этого target.
3. **Given** пользователь нажимает «Выбрать все» или «Снять все», **Then** все
   отображаемые verified targets получают соответствующее состояние, а
   неизвестные/непроверенные приложения не добавляются в список.
4. **Given** target исчез из текущего реестра после обновления, **When** его
   сохранённое правило загружается, **Then** правило не применяется к другому
   target и пользователь получает безопасное состояние, не теряя остальные
   настройки.

### User Story 4 - Сохранить защитные границы (Priority: P1)

Как пользователь и владелец продукта, я хочу, чтобы восстановление автозаписи
не превращалось в скрытую запись любого звука, поэтому автоматический путь
должен работать только при выполнении всех существующих capture и privacy
gates.

**Why this priority**: Таймер и автозапись полезны только при честной границе
между встречей и произвольным звуком устройства.

**Independent Test**: Прогнать обнаружение для неизвестного приложения,
неуверенного сигнала, отозванного разрешения, режима «не записывать»,
отсутствующего хранилища и уже активной записи; ни один сценарий не должен
создать скрытую или вторую запись.

**Acceptance Scenarios**:

1. **Given** сигнал исходит от неизвестного/непроверенного приложения или
   является media playback, **When** detector его видит, **Then** prompt и
   auto-start не происходят.
2. **Given** не выполнено любое обязательное разрешение, storage/readiness,
   workspace-policy, suppression или confidence gate, **When** срабатывает
   countdown/auto-record rule, **Then** запись не стартует и состояние остаётся
   объяснимым пользователю.
3. **Given** запись уже активна, **When** приходит повторное событие detector,
   **Then** новый prompt/сеанс не создаётся.
4. **Given** автоматическая запись активна, **When** пользователь смотрит на
   локальный trust surface, **Then** состояние и доступная одна команда Stop
   видимы без сети и без открытия веб-кабинета.

### User Story 5 - Не потерять контракт при следующих изменениях (Priority: P2)

Как разработчик и reviewer, я хочу видеть единый источник правды и
регрессионные проверки для автозаписи, timer, checkbox и app list, чтобы
рефакторинг UX не удалил эти функции снова без осознанного решения.

**Why this priority**: Предыдущая фича удалила runtime-поведение и тесты,
несмотря на существующие требования и сохранённые поля модели.

**Independent Test**: Выполнить поиск по active product docs, проверить
traceability до исходного кода и убедиться, что focused tests требуют наличие
и поведение всех четырёх частей контракта.

**Acceptance Scenarios**:

1. **Given** Feature 124 считается текущим контрактом, **When** reviewer
   читает status, constitution, product gates, spec, plan, quickstart и tests,
   **Then** нигде нет активного требования удалить countdown/autostart/app
   list/checkbox.
2. **Given** будущий diff удаляет одну из обязательных частей, **When** запускаются
   focused regression checks, **Then** проверка блокирует такой diff или
   сообщает о нарушении контракта.

## Edge Cases

- Если timer prompt закрыт самим detector до истечения восьми секунд, запись
  не начинается и сохранённое правило не меняется.
- Если пользователь выбирает auto-record в prompt, но стартовая readiness
  проверка не проходит, правило не должно обходить gate; UI сообщает причину.
- Если настройки недоступны во время загрузки реестра, ранее сохранённые
  значения не сбрасываются и приложение не подменяет список неизвестными
  targets.
- Если два события встречи приходят почти одновременно, создаётся не более
  одного prompt или recording session.
- Если приложение перезапущено во время countdown, старый transient timer не
  восстанавливается как скрытый старт; следующая встреча проходит через обычный
  видимый prompt/rule flow.
- Если пользователь снял auto-record permission во время активной записи,
  текущая запись не обрывается неожиданно, но следующая встреча больше не
  стартует автоматически.

## Requirements

### Functional Requirements

- **FR-001**: System MUST persist the meeting-detection enabled state and the
  target-scoped auto-record permissions independently.
- **FR-002**: Settings MUST show every currently verified native meeting target
  from the canonical registry in one common applications list.
- **FR-003**: Each listed target MUST have a reversible auto-record toggle, and
  settings MUST provide «Выбрать все» and «Снять все» actions for the displayed
  verified targets.
- **FR-004**: A meeting prompt for a target without saved auto-record
  permission MUST show a visible eight-second countdown, an immediate
  «Записать сейчас» action, a «Пропустить» action, and the checkbox «Всегда
  писать это приложение».
- **FR-005**: Pressing «Записать сейчас» MUST start recording immediately and
  cancel the countdown; pressing «Пропустить» MUST close the prompt without starting a
  recording or changing saved auto-record permission.
- **FR-006**: When the eight-second countdown expires, the system MUST start
  recording automatically if and only if all meeting-detection, target,
  permission, readiness, policy, suppression, storage, and active-session gates
  pass.
- **FR-007**: Checking «Всегда писать это приложение» and starting the current
  recording MUST persist auto-record permission for the exact detected target,
  and MUST NOT create a global permission for other targets.
- **FR-008**: A saved target-scoped auto-record permission MUST start a future
  eligible meeting for that exact target without showing a new permission
  prompt, subject to all hard gates.
- **FR-009**: Unknown, unverified, diagnostic-only, suppressed, non-meeting,
  media-playback, and policy-blocked signals MUST NOT produce a prompt or
  automatic recording.
- **FR-010**: Manual Start and Stop MUST remain available, while active capture
  MUST retain a persistent local visible indicator and one-action Stop.
- **FR-011**: The system MUST prevent duplicate prompts and parallel recording
  sessions when detector events are repeated or arrive concurrently.
- **FR-012**: Revoking a target toggle MUST take effect for the next eligible
  detection and MUST NOT be reused for a different target identity.
- **FR-013**: Loading, updating, or shrinking the registry MUST preserve
  unrelated user preferences and MUST fail closed for a missing target rather
  than applying its rule to another target.
- **FR-014**: The user-facing Russian labels for the restored contract MUST
  remain explicit: «Автозапись», «Приложения», «Выбрать все», «Снять все»,
  «Всегда писать это приложение», «Записать сейчас» and «Пропустить».
- **FR-015**: Active product documentation MUST identify Feature 124 as the
  current owner of the timer, auto-start, opt-in checkbox, target list and
  target-scoped policy; historical Feature 121 text MUST be marked as
  superseded instead of serving as a removal instruction.
- **FR-016**: Any future change that removes or narrows one of the FR-002,
  FR-003, FR-004, FR-006, FR-007 or FR-008 capabilities MUST be introduced by
  a new approved Spec Kit feature with explicit compatibility/migration notes,
  updated regression tests and product-owner approval.

### Key Entities

- **Verified Meeting Target**: A canonical native application identity that
  has passed registry verification and may produce a meeting candidate.
- **Target-Scoped Auto-Record Permission**: A persisted reversible user choice
  keyed to one exact verified target identity.
- **Meeting Detection Prompt**: A transient visible decision surface containing
  an eight-second countdown, Start/Not-now actions and the target opt-in
  checkbox.
- **Recording Prerequisite Gate**: The combined current checks for permissions,
  capture readiness, storage, policy, suppression, confidence and active
  session state.
- **Capture Session**: One local recording lifecycle with visible state,
  source target, start trigger and one-action Stop.

## Success Criteria

### Measurable Outcomes

- **SC-001**: In focused acceptance scenarios, 100% of verified registry
  targets appear in the settings list and every row maps to exactly one target
  identity.
- **SC-002**: In 100% of eligible prompt scenarios, the countdown is visible,
  Start begins capture immediately, and expiry begins capture at eight seconds
  without a second confirmation.
- **SC-003**: In 100% of opt-in scenarios, the checkbox choice survives an app
  restart and only the same target auto-starts on a later eligible meeting.
- **SC-004**: In 100% of blocked/unknown/suppressed/duplicate scenarios, no
  hidden capture, prompt, or second active recording session is created.
- **SC-005**: Users can find the meeting-detection setting and change one
  target's auto-record permission without changing another target's permission
  in under 60 seconds during usability review.
- **SC-006**: The active documentation search has one current, consistent
  policy for timer, auto-start, checkbox and target list; any historical
  removal statement links to Feature 124 as its superseding correction.

## Assumptions

- The existing canonical native target registry and target identity format are
  reused; this feature does not add a second registry or revive removed audio
  routing.
- The designed legacy countdown is exactly eight seconds and is part of the
  user-visible contract until a future approved feature changes it.
- Existing recording prerequisite, workspace policy, suppression, storage,
  permission, visibility and Stop mechanisms remain the safety authority.
- Existing persisted target-scoped fields are migrated forward rather than
  discarded or reset.
- Automatic recording is limited to the internal MVP's approved workspace
  policy; external/customer legal notice requirements remain enforced by the
  existing policy gates.
- Focused macOS XCTest/static contract checks are required because this slice
  changes capture-critical native behavior and user-facing settings.

## Out Of Scope

- General automatic recording from arbitrary system audio, media playback,
  notifications, music, video or unknown applications.
- A new audio engine, virtual device, separate routing architecture, bot
  joining, video recording or calendar-driven start.
- Server-side replacement of the local capture truth or remote ownership of
  the visible recording indicator/Stop action.
- New target discovery heuristics beyond the existing canonical registry.
- Rewriting the historical changelog to hide that Feature 121 temporarily
  removed the behavior.
