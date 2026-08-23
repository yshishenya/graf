# Feature Specification: Политики автозаписи по приложениям

**Feature Branch**: `codex/199-per-app-recording-policies`

**Created**: 2026-08-23

**Status**: Draft

**Input**: User description: "Синхронизировать master и сделать осознанный выбор автозаписи: prompt с 8-секундным автозапуском, сохранение выбора только через кнопку и галочку, три состояния для каждого приложения и общий выбор для всех приложений."

## Context And Product Decision

Текущий путь хранит бинарный список приложений и отдельное общее подтверждение.
Из-за этого выбор одного приложения может быть ошибочно распространён на другие,
а интерфейс заставляет пользователя разбираться в технических деталях.

Новый пользовательский контракт использует три постоянных состояния для каждого
проверенного native-приложения: `Всегда`, `Спрашивать`, `Никогда`. Новые приложения
начинают в состоянии `Спрашивать`.

Prompt остаётся ненавязчивым и содержит 8-секундный таймер. Если пользователь
ничего не нажал, по истечении таймера запись текущей встречи начинается независимо
от состояния галочки. Таймер никогда не сохраняет выбор. Сохранение правила
происходит только после явной кнопки и включённой галочки.

Постоянный статус автозаписи на главном экране, счётчик приложений, технические
идентификаторы и уведомление после таймера не добавляются. Обязательный видимый
индикатор активной записи и однокнопочная остановка сохраняются.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Явное решение в prompt (Priority: P1)

Как пользователь, я хочу быстро начать или пропустить запись конкретной встречи,
а постоянное правило сохранять только осознанным действием.

**Why this priority**: Capture и privacy зависят от точного различия текущего
решения и будущей политики приложения.

**Independent Test**: На synthetic встрече проверить обе кнопки, все состояния
галочки и истечение таймера без записи содержимого реальной встречи.

**Acceptance Scenarios**:

1. **Given** приложение имеет состояние `Спрашивать`, **When** prompt показан,
   **Then** видны `Записать сейчас`, `Не записывать`, галочка и countdown 8 секунд.
2. **Given** галочка выключена, **When** пользователь нажимает `Записать сейчас`,
   **Then** начинается только текущая запись, а состояние приложения остаётся
   `Спрашивать`.
3. **Given** галочка включена, **When** пользователь нажимает `Записать сейчас`,
   **Then** начинается текущая запись и состояние приложения становится `Всегда`.
4. **Given** галочка выключена, **When** пользователь нажимает `Не записывать`,
   **Then** текущая встреча пропускается, а состояние приложения остаётся
   `Спрашивать`.
5. **Given** галочка включена, **When** пользователь нажимает `Не записывать`,
   **Then** текущая встреча пропускается и состояние приложения становится
   `Никогда`.
6. **Given** prompt показан, **When** 8 секунд истекли без нажатия кнопки,
   **Then** начинается текущая запись, prompt закрывается, а состояние приложения
   и сохранённая политика не изменяются независимо от состояния галочки.
7. **Given** prompt показан, **When** пользователь меняет только состояние
   галочки, **Then** запись и политика не изменяются до явного нажатия кнопки или
   истечения таймера.

### User Story 2 - Правило для одного приложения (Priority: P1)

Как пользователь, я хочу в настройках назначить для приложения одно из трёх
понятных состояний и вернуть его к запросу в любой момент.

**Why this priority**: Пользователь должен исправлять ошибочное решение без
поиска технических идентификаторов или повторной установки приложения.

**Independent Test**: Для synthetic registry проверить переключение каждой строки
между `Всегда`, `Спрашивать` и `Никогда`, затем проверить следующий detector event.

**Acceptance Scenarios**:

1. **Given** новое verified native-приложение появилось в registry, **When** оно
   отображается в настройках, **Then** выбрано `Спрашивать`.
2. **Given** приложение имеет `Всегда`, **When** встреча обнаружена, **Then** prompt
   не показывается и текущие capture gates проверяются перед стартом.
3. **Given** приложение имеет `Никогда`, **When** встреча обнаружена, **Then** prompt
   и запись не запускаются.
4. **Given** приложение имеет `Спрашивать`, **When** встреча обнаружена, **Then**
   показывается prompt с 8-секундным таймером.

### User Story 3 - Общее состояние для всех приложений (Priority: P2)

Как пользователь, я хочу одним выбором назначить одинаковое состояние всем
проверенным приложениям, а затем при необходимости уточнить отдельные строки.

**Why this priority**: Большой список приложений нельзя удобно настраивать по одному.

**Independent Test**: В registry из нескольких targets выбрать каждое общее
состояние и проверить, что все eligible rows получили его, а индивидуальная
правка одной строки сохраняется.

**Acceptance Scenarios**:

1. **Given** список verified targets, **When** пользователь выбирает общее
   `Всегда`, `Спрашивать` или `Никогда`, **Then** выбранное состояние применяется
   ко всем видимым eligible targets.
2. **Given** individual targets имеют разные состояния, **When** страница открыта,
   **Then** общий контрол показывает нейтральное состояние `Разные`.
3. **Given** общее состояние применено, **When** пользователь изменяет одну строку,
   **Then** остальные строки не изменяются.

### User Story 4 - Спокойные настройки и технические подсказки (Priority: P2)

Как пользователь, я хочу видеть короткий список приложений без технического шума,
но иметь доступ к объяснению служебных переключателей при необходимости.

**Independent Test**: Проверить визуальный и клавиатурный путь settings surface,
включая focus/hover hint для технических controls.

**Acceptance Scenarios**:

1. **Given** settings page открыта, **Then** в строках показываются иконка, имя
   приложения и radio-карточки с подписями `Всегда`, `Спрашивать`, `Никогда`.
2. **Given** технический switch отображён, **Then** его основная подпись короткая,
   а подробное описание доступно через hint по наведению, фокусу и VoiceOver.
3. **Given** пользователь находится на главном экране в idle, **Then** нет отдельного
   статуса или счётчика включённых приложений.

### Edge Cases

- Истечение таймера при включённой галочке никогда не сохраняет правило.
- Быстрые повторные клики по кнопкам дают только один terminal prompt outcome.
- При недоступной policy, permissions, storage, visible indicator или Stop gate
  автоматический старт не выполняется; пользователь получает существующее
  понятное состояние блокировки, а не ложное подтверждение записи.
- Истечение prompt после окончания встречи не создаёт запись и не сохраняет выбор.
- Старый бинарный список и глобальное acknowledgement не должны превращаться в
  разрешение для всех приложений без доказанного target-specific выбора.
- Browser, manual-only, неизвестные и неподтверждённые targets не получают
  автоматическую политику.
- При смешанных значениях общий контрол остаётся нейтральным и не перезаписывает
  строки до явного выбора пользователя.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST store one reversible recording rule per verified target:
  `always`, `ask` or `never`.
- **FR-002**: New verified native targets MUST default to `ask` without creating
  acknowledgement or silently starting capture.
- **FR-003**: Prompt MUST show the target name, `Записать сейчас`, `Не записывать`,
  an unchecked-by-default `Запомнить выбор` checkbox and an 8-second countdown.
- **FR-004**: Prompt button actions MUST be the only user actions that can persist
  a target rule; checkbox changes alone MUST NOT start recording or persist a rule.
- **FR-005**: Countdown expiry MUST start the current recording when all existing
  policy and capture gates pass, regardless of checkbox state, and MUST NOT persist
  a target rule.
- **FR-006**: `Записать сейчас` with checkbox off MUST affect only the current
  meeting; with checkbox on it MUST persist `always` after a successful save.
- **FR-007**: `Не записывать` with checkbox off MUST suppress only the current
  meeting; with checkbox on it MUST persist `never` after a successful save.
- **FR-008**: A target in `always` MUST bypass the prompt while retaining all
  current policy, permission, readiness, visible-indicator and one-action Stop gates.
- **FR-009**: A target in `ask` MUST show the prompt on every eligible detection.
- **FR-010**: A target in `never` MUST suppress both prompt and automatic recording.
- **FR-011**: Settings MUST render per-target rules as accessible theme-style radio
  cards labelled exactly `Всегда`, `Спрашивать`, `Никогда`.
- **FR-012**: Settings MUST provide one equivalent three-state control that applies
  a selected rule to all eligible verified targets; mixed values MUST render as
  `Разные` until an explicit bulk selection is made.
- **FR-013**: Individual target changes MUST remain independent after a bulk action.
- **FR-014**: Technical switches MUST remain available with short labels and their
  former detailed descriptions exposed through keyboard/hover/VoiceOver hints.
- **FR-015**: Main and settings surfaces MUST NOT expose bundle IDs, an enabled-app
  count, a persistent auto-record status, or a post-timeout undo notification.
- **FR-016**: Active recording MUST retain a visible local indicator and one-action
  Stop control.
- **FR-017**: Legacy target sets and global acknowledgements MUST be migrated without
  granting cross-target automatic recording; ambiguous legacy choices default to
  `ask`.
- **FR-018**: Diagnostics MUST contain only bounded metadata and MUST NOT include
  audio, transcript, credentials, cookies, tokens or private meeting content.

### Key Entities

- **AutomaticRecordingRule**: Target-scoped value `always`, `ask` or `never`.
- **PromptDecision**: Current target, button/timeout outcome, checkbox state and
  whether a persistent rule was saved.
- **BulkRecordingRuleSelection**: Explicit selection applied to all eligible
  targets; displays `Разные` when current values are not uniform.
- **WorkspaceAutoStartAuthorization**: Existing workspace/device policy gate,
  separate from the target-scoped user rule.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of prompt decision combinations produce the exact current and
  future outcome defined in the acceptance table, including timeout with checkbox on.
- **SC-002**: 100% of eligible new targets appear as `Спрашивать`; no installation,
  registry refresh or timeout creates a persistent target rule.
- **SC-003**: 100% of `always` and `never` targets bypass the prompt in the correct
  direction without bypassing capture gates.
- **SC-004**: A bulk selection updates 100% of eligible visible targets in one
  deliberate interaction, and a later individual edit changes only that target.
- **SC-005**: Settings users can identify and change an app policy without seeing a
  bundle ID or technical paragraph; all three states are keyboard and VoiceOver
  reachable.
- **SC-006**: No active recording loses its visible indicator or one-action Stop
  path in focused and synthetic runtime validation.
- **SC-007**: Focused Swift tests and synthetic desktop smoke pass; full repository
  CI remains an explicitly reported separate lane and is not claimed unless run.

## Assumptions

- Existing verified-native registry, workspace policy and capture readiness gates
  remain authoritative.
- The 8-second countdown remains part of the prompt and starts the current meeting
  when it expires; it is not a persistence mechanism.
- The checkbox is intentionally off by default and has effect only when paired with
  an explicit button.
- Existing technical controls remain in the settings surface; their descriptions
  move to hints without changing the policy boundary.
- Migration cannot infer target-specific intent from the old global acknowledgement;
  ambiguous legacy targets become `ask`.
- Production deployment, release publication and full CI are out of scope for this
  implementation turn unless separately approved.

## Out Of Scope

- Persistent home-screen auto-record status or application counts.
- Participant-facing notices, new capture engines, browser extensions or arbitrary
  system-audio recording.
- Production deploy, Sparkle publication, release tagging or replacement of the
  installed app.
- New server endpoints or database tables; existing policy and registry boundaries
  are reused.
