# Feature Specification: Стабильные статусы обработки в списке встреч

**Feature Branch**: `codex/202-fix-processing-list-flicker`

**Created**: 2026-08-25

**Status**: Implemented and locally validated; PR and production rollout pending

**Input**: Пользователь сообщил, что при обработке одной записи периодически
мигают верхняя и нижняя соседние записи и на них появляются противоречивые
статусы.

## User Scenarios & Testing

### User Story 1 - Соседние записи не меняются при обработке (Priority: P1)

Пользователь загружает запись и наблюдает её обработку, не видя мигания,
перестроения или временных processing-статусов у других записей.

**Why this priority**: Ложный статус другой встречи разрушает доверие к списку
и не позволяет понять, какая запись реально обрабатывается.

**Independent Test**: Показать список с failed-строкой выше, processing-строкой
в центре и failed-строкой ниже; выполнить несколько циклов обновления статуса и
убедиться, что меняется только центральная строка, а соседние DOM-узлы, текст и
геометрия остаются неизменными.

**Acceptance Scenarios**:

1. **Given** одна встреча обрабатывается, **When** приходит промежуточный статус,
   **Then** обновляется только строка этой встречи.
2. **Given** рядом есть failed-встречи, **When** active processing обновляется,
   **Then** failed-строки сохраняют серверный статус «Не удалось обработать» и
   не получают processing-подсказку.
3. **Given** пользователь сфокусировал или выбрал строку, **When** статус
   обработки обновился, **Then** фокус и выбор не теряются.

### User Story 2 - Завершение обработки отражается авторитетно (Priority: P1)

Когда обработка переходит в ready, partial, blocked или terminal failure,
пользователь получает единый серверный статус без постоянной перерисовки списка.

**Independent Test**: Вернуть terminal/processed projection для active-строки и
убедиться, что запрошено одно обновление списка, после которого projection этой
строки прекращается.

**Acceptance Scenarios**:

1. **Given** active processing, **When** состояние становится terminal или
   processed, **Then** список обновляется один раз из авторитетного источника.
2. **Given** состояние остаётся промежуточным, **When** выполняется очередная
   проверка, **Then** весь список не заменяется.
3. **Given** browser cabinet или embedded cabinet, **When** выполняются те же
   переходы, **Then** поведение и тексты совпадают.

## Edge Cases

- Запоздалый ответ от старого DOM-поколения не должен менять новую строку.
- Ответ с другим `meeting_id` не должен менять ни одну строку.
- Failed-строка с устаревшим или неполным processing projection остаётся failed.
- Несколько active processing-строк обновляются независимо без дублирующего
  terminal refresh.
- Потеря сети не удаляет последний правдивый серверный статус и не меняет
  соседние строки.
- Фильтр, сортировка, удаление и ручной refresh имеют приоритет над фоновым
  обновлением.

## Requirements

### Functional Requirements

- **FR-001**: Каждая строка MUST показывать не более одного совместимого
  видимого состояния обработки.
- **FR-002**: Фоновое обновление active processing MUST обновлять только строку
  с совпадающим `meeting_id` в текущем DOM-поколении.
- **FR-003**: Failed, blocked и другие terminal строки MUST NOT получать
  промежуточную processing-проекцию.
- **FR-004**: Наличие только submitted/processing записи MUST NOT запускать
  секундную замену всего списка.
- **FR-005**: Active processing строка MUST иметь стабильное место для
  readiness-текста до первого клиентского ответа, чтобы соседние строки не
  сдвигались.
- **FR-006**: Переход active processing в processed, blocked, failed-terminal
  или canceled MUST вызвать не более одного авторитетного обновления списка.
- **FR-007**: Upload progress и подготовка playback MUST сохранить существующий
  жизненный цикл обновления.
- **FR-008**: Фильтры, сортировка, selection, focus recovery, auth fencing и
  aria-live объявления MUST сохранить текущее поведение.
- **FR-009**: Web и embedded cabinet MUST использовать один общий контракт.
- **FR-010**: Проверки и evidence MUST быть metadata-only.

## Success Criteria

- **SC-001**: В regression-сценарии processing между двумя failed-строками
  соседние DOM-узлы и их видимый текст не меняются на всех циклах polling.
- **SC-002**: Submitted/processing-only список не содержит секундного full-list
  poll; активная строка проверяется не чаще одного раза за 15 секунд.
- **SC-003**: Terminal/processed transition вызывает ровно один authoritative
  list refresh и после него не продолжает projection для terminal-строки.
- **SC-004**: Focused server-rendering, JavaScript lifecycle, HTMX fencing и
  browser/embedded contract проверки проходят без новых зависимостей.

## Assumptions

- Серверный meeting list остаётся источником структурного и terminal-состояния.
- Content-safe processing endpoint остаётся источником промежуточной проекции
  только для строк, которые сервер уже пометил как processing.
- Интервал 15 секунд соответствует существующему throttle processing projection.
- Изменения provider, Temporal retry, quota и processing data model не требуются.

## Out of Scope

- Изменение MediaScribe/Temporal retry semantics или создание новой попытки.
- Переработка upload-progress polling и playback normalization polling.
- Новый frontend framework, dependency или API endpoint.
- Production deploy и release до отдельного release gate.
