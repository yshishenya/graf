# Feature Specification: Immediate meeting-list handoff after native recording upload

**Feature Branch**: `265-meeting-list-handoff`

**Created**: 2026-09-15

**Status**: Draft

**Input**: User description: "Когда прошла запись и она отправилась на сервер, в интерфейсе я ее не вижу. Чтобы увидеть записи, нужно принудительно обновить интерфейс. Изучи внимательно, в чем проблема. Найди все корни. Продумай, как сделать правильно, чтобы был единый беспроблемный пользовательский путь, чтобы интерфейс был понятный в этой части и при этом простой. Без переусложнений. Также проверь что код не дает проблем, и чтобы вообще все было так, как правильно, по лучшим практикам и точно правильно работало."

## User Scenarios & Testing

### User Story 1 - Новая запись появляется сама (Priority: P1)

Пользователь завершает запись в macOS-приложении. После того как сервер принял создание встречи, новая встреча должна появиться во встроенном списке встреч сама, без обновления страницы и без отдельного действия пользователя.

**Why this priority**: Сейчас пользователь видит устаревший список и вынужден угадывать, сохранилась ли запись. Это нарушает основной путь записи и подрывает доверие к результату.

**Independent Test**: На странице встроенного списка опубликовать последовательность локальных состояний записи, в которой сначала нет `meetingId`, а затем появляется подтверждённый идентификатор встречи. Проверить, что список перечитывается, серверная строка появляется без перезагрузки, а в DOM остаётся ровно одна строка встречи.

**Acceptance Scenarios**:

1. **Given** встроенный список встреч открыт без активного поиска и фильтров, **When** локальная очередь впервые получает `meetingId` созданной серверной встречи, **Then** выполняется один запрос текущего списка и после его успешного ответа новая встреча отображается без ручного обновления.
2. **Given** серверная встреча уже создана, но ответ обновления списка ещё не пришёл, **When** пользователь смотрит на список, **Then** временная локальная строка не исчезает и не создаётся ощущение потери записи.
3. **Given** серверная строка с тем же `meetingId` появилась в ответе списка, **When** обновление DOM завершено, **Then** локальный заместитель удаляется, серверная строка остаётся единственной и показывает серверное состояние встречи.

### User Story 2 - Обновление не ломает текущий контекст (Priority: P1)

Пользователь может искать встречи, включать фильтры, менять сортировку, выбирать строки и работать с клавиатурой. Автоматическое обновление должно использовать тот же контекст списка и не забирать фокус у другого текущего действия.

**Why this priority**: Автоматическое исправление, которое сбрасывает поиск, выбор или фокус, создаёт новый пользовательский дефект и делает путь непредсказуемым.

**Independent Test**: Повторить handoff при каждом типе сортировки, с поиском и фильтрами, а также с выбранной строкой и фокусом на её управляющем элементе. Сравнить состояние формы, выбранных идентификаторов и фокуса до и после ответа сервера.

**Acceptance Scenarios**:

1. **Given** в списке заданы поиск, фильтры или сортировка, **When** запускается автоматическое обновление, **Then** запрос использует текущие значения формы и не возвращает пользователя к другому контексту.
2. **Given** пользователь выбрал локальную строку или сфокусировал её доступное действие, **When** серверная строка с тем же идентификатором появляется, **Then** выбор и фокус переходят на серверную строку, если пользователь не переместил фокус сам.
3. **Given** текущий поиск, фильтр или видимая часть списка не включает новую встречу, **When** авторитетный ответ списка завершён, **Then** локальный заместитель убирается и не возвращается на следующих публикациях состояния только потому, что у записи есть `meetingId`.

### User Story 3 - Путь устойчив к повторным состояниям и сбоям (Priority: P2)

Пользователь получает частые обновления прогресса отправки, может продолжать работу при временном сбое сети и не должен получать поток одинаковых запросов или ошибочные дубликаты.

**Why this priority**: Прогресс отправки публикуется много раз; привязка обновления списка к каждому прогрессу создаст лишнюю нагрузку и гонки DOM.

**Independent Test**: Опубликовать не менее 100 повторных состояний после одного перехода к `meetingId`, проверить один запрос обновления, отсутствие ошибок страницы и сохранение локальной строки при неуспешном запросе. Отдельно проверить несколько одновременных handoff-ов.

**Acceptance Scenarios**:

1. **Given** первый handoff уже запустил обновление, **When** приходят повторные состояния прогресса, **Then** новые одинаковые запросы списка не создаются.
2. **Given** запрос списка завершился сетевой или сервисной ошибкой, **When** пользователь продолжает работать, **Then** локальная запись не скрывается, существующее состояние восстановления списка используется без потери данных, а повторная попытка остаётся возможной штатным способом. **Given** запрос завершился `401/403`, **Then** приватные серверные строки очищаются из DOM и показывается существующее состояние восстановления доступа, но нативная проекция и локальные файлы сохраняются; после повторной авторизации авторитетный список сервера заменяет временный заместитель без дубля.
3. **Given** несколько локальных записей одновременно получают `meetingId`, **When** состояние публикуется, **Then** обновление объединяет их в один запрос, а после ответа каждая встреча сопоставляется со своей серверной строкой без дублей.

## Edge Cases

- WebView может получить обновление локальных строк до загрузки списка или находиться на странице настроек. В этом случае JavaScript не должен выбрасывать ошибку или подменять настройки; следующий штатный переход к списку должен показать серверную встречу.
- Серверная строка может отсутствовать в текущем ответе из-за поиска, фильтра, неполной видимой части списка или уже подтверждённого удаления. После завершения этого авторитетного ответа локальная копия не должна снова появляться как новая встреча.
- Ответ обновления может прийти после другого авторитетного запроса списка. Устаревший ответ не должен откатывать более новое состояние и не должен ломать существующую защиту от гонок HTMX.
- Пользователь может открыть модальное окно удаления или ручной загрузки во время завершения нативной записи. Обновление списка не должно очищать введённые данные, менять подтверждаемую выборку или неожиданно переносить фокус из модального окна.
- Страница может быть скрыта или потерять сеть. Решение не должно добавлять постоянный опрос всего списка и не должно считать отсутствие ответа доказательством удаления записи.
- При `401/403` браузер не должен оставлять приватные строки встреч в DOM. Это не означает удаления локальной записи: нативная очередь и файлы сохраняются, а после входа в исходный аккаунт или выбора пространства обычный серверный список снова становится источником истины.

## Requirements

### Functional Requirements

- **FR-001**: System MUST detect either the first transition of a visible native local-recording projection from no server meeting identity to a confirmed `meetingId`, or the first observation in a newly loaded WebView of a linked projection whose `meetingId` is absent from the current server DOM.
- **FR-002**: System MUST reuse the existing authoritative meeting-list refresh path and current list form state to request the list after a new handoff, without introducing a new API, browser-push channel, or permanent list timer.
- **FR-003**: System MUST coalesce multiple handoffs observed in one publication into one list request and MUST NOT issue another request for repeated progress publications of the same handoff.
- **FR-004**: System MUST keep a newly handed-off local row visible until the first relevant authoritative list response is applied, unless the server row is already present.
- **FR-005**: When the authoritative response contains the matching server meeting row, System MUST replace the local placeholder with that row, preserve the existing server-list identity rules, and keep exactly one visible row for the meeting.
- **FR-006**: When the authoritative response does not contain the matching server row, System MUST remove the temporary alias after that response and MUST NOT resurrect it merely because the native projection still contains a `meetingId`.
- **FR-007**: System MUST preserve the current search, status/access filters, sort order, selection, and focus-recovery behavior used by the existing meeting-list path.
- **FR-008**: System MUST leave manual upload refresh, meeting deletion, processing-status polling, authorization recovery, and stale-HTMX-response fencing behavior unchanged except where the shared refresh path is reused.
- **FR-009**: A failed automatic refresh other than an authorization failure MUST leave the local recording projection visible and actionable through the existing recovery or retry path; it MUST NOT delete local artifacts or expose local filesystem paths. For `401/403`, the browser MUST clear private meeting-list data from the DOM and show the existing authorization/access recovery state, while the native projection and local files remain intact; after authorization is restored, the server list MUST be authoritative and MUST NOT create a duplicate local row.
- **FR-010**: The browser code MUST remain free of page errors for the handoff, repeated-update, missing-list, failed-request, filter, selection, focus, and duplicate-row scenarios.
- **FR-011**: The visible behavior MUST use the existing loading and accessible status semantics; it MUST not introduce a new notification, modal, sound, or persistent progress surface for this handoff.

### Key Entities

- **Local recording projection**: Ephemeral native queue data shown in the embedded list, identified by a stable local recording ID and optionally linked to a server `meetingId`.
- **Server meeting row**: The authoritative meeting-list representation returned by the existing list request, identified by `meetingId` and subject to the current query, filters, sorting, and visible-result boundary.
- **Pending handoff**: Short-lived browser state recording that a local projection has just acquired a server identity and is waiting for one authoritative list response; it is not persisted as meeting data.

## Success Criteria

### Measurable Outcomes

- **SC-001**: In every automated handoff scenario with a successful list response, the new meeting is visible without a full-page reload and the DOM contains exactly one row for its `meetingId`.
- **SC-002**: One handoff publication causes no more than one authoritative list request; 100 repeated progress publications after the same handoff cause zero additional automatic list requests.
- **SC-003**: In all supported sort, search, and filter scenarios, the list controls retain their pre-handoff values and the resulting list matches the requested context.
- **SC-004**: In selection and keyboard-focus scenarios, the selected identity and connected focus target are preserved or transferred to the matching server row, unless the user moved focus during the request.
- **SC-005**: Failed (other than authorization), missing, stale, and pre-navigation handoff scenarios produce no browser page errors, no duplicate rows, and no deletion of local recording data; `401/403` scenarios clear private server rows from the DOM, preserve native local custody, and reconcile to one server row after authorization is restored.
- **SC-006**: Existing manual-upload, deletion, processing-poll, and authorization-recovery browser checks remain passing after the change.

## Assumptions

- The existing server meeting-creation operation commits the meeting before the desktop client receives its `meetingId`; the normal meeting-list request is therefore the authoritative source for the rendered row.
- The current meeting-list form and HTMX fencing are the supported refresh mechanism and already preserve query, filter, sort, and focus state.
- If a meeting is excluded by the user’s current search, filter, or visible-result boundary, not showing it in that context is correct; the handoff placeholder exists only until the first authoritative response for the current context.
- A temporary network failure does not revoke or delete the local recording. The existing recovery/retry interaction remains the user’s fallback.
- The scope is limited to the embedded/native recording handoff. No new server event stream, database field, or general real-time synchronization mechanism is required.

## Out of Scope

- Replacing the existing list request with WebSocket, server-sent events, or continuous polling.
- Changing server meeting creation, upload protocol, processing workflow, retention, deletion, or authorization semantics.
- Adding toast notifications, sounds, new dialogs, or a second upload-progress interface.
- Changing the behavior of ordinary browser manual upload except for retaining the shared existing refresh behavior.

## Legacy Impact

Classification: `untouched`

Feature 265 изменяет только общий handoff в кабинете и не добавляет, не удаляет
и не сохраняет legacy runtime, fallback, alias или compatibility path.
