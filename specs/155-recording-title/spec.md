# Feature Specification: Meaningful Recording Titles

**Feature Branch**: `155-recording-title`

**Created**: 2026-08-16

**Status**: Ready for implementation

**Input**: User description: "Назвать запись в приложении по названию встречи, если оно доступно, с датой и временем; если названия встречи нет — использовать название приложения-источника или понятный fallback. Изменение имени аудиофайла можно рассмотреть отдельно."

## Clarifications

### Session 2026-08-16

- Q: Новое название должно быть одинаковым в macOS-приложении и web-кабинете или достаточно изменить только macOS-интерфейс, где сейчас пользователь видит «Запись»? → A: Одинаковое название в macOS-приложении и web-кабинете.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Понятно найти запись встречи (Priority: P1)

Как пользователь, я хочу видеть в списке записей название встречи вместе с датой и временем, чтобы узнавать нужную запись без открытия каждой записи и прослушивания аудио.

**Why this priority**: Сейчас записи отображаются как «Запись», поэтому список не помогает отличать встречи и быстро находить нужную.

**Independent Test**: Создать запись, для которой доступно название встречи, открыть список записей и убедиться, что запись однозначно отображается по названию встречи, дате и времени.

**Acceptance Scenarios**:

1. **Given** у записи есть подтверждённое название встречи «Планирование релиза» и время начала 16 августа в 14:30, **When** пользователь открывает список записей, **Then** он видит название «Планирование релиза — 16 августа, 14:30» или эквивалентное локализованное представление с теми же данными.
2. **Given** запись была сопоставлена с событием календаря, **When** запись отображается в списке, **Then** используется название календарного события, а не общее «Запись».
3. **Given** название встречи содержит пробелы, Unicode-символы или знаки пунктуации, **When** запись отображается, **Then** название сохраняет читаемый текст и не ломает строку списка или действие открытия записи.

### User Story 2 - Понятно отличить запись без названия встречи (Priority: P1)

Как пользователь, я хочу видеть источник записи или датированный fallback, если название встречи недоступно, чтобы даже незапланированная запись не выглядела как безымянная.

**Why this priority**: Не каждая запись связана с календарным событием; отсутствие названия не должно возвращать бесполезное имя «Запись» без даты.

**Independent Test**: Создать записи с доступным названием приложения-источника и без него, открыть список и проверить оба варианта отображения.

**Acceptance Scenarios**:

1. **Given** у записи нет названия встречи, но известен источник «Zoom» и время начала 16 августа в 14:30, **When** пользователь открывает список записей, **Then** он видит «Zoom — 16 августа, 14:30» или эквивалентное локализованное представление.
2. **Given** у записи нет ни названия встречи, ни названия приложения-источника, **When** пользователь открывает список записей, **Then** он видит «Запись — 16 августа, 14:30» или эквивалентный датированный fallback.
3. **Given** время начала записи отсутствует или не может быть преобразовано в локальное представление, **When** список строит заголовок, **Then** он использует доступную часть данных без падения интерфейса и не возвращает пустой заголовок.

### User Story 3 - Сохранить намеренное название пользователя (Priority: P1)

Как пользователь, я хочу, чтобы моё вручную заданное название записи не заменялось автоматически названием встречи или приложения.

**Why this priority**: Автоматическая классификация должна помогать, но не должна уничтожать пользовательское решение и уже выполненную работу.

**Independent Test**: Задать записи пользовательское название, после чего обновить или повторно сопоставить её с календарём и убедиться, что пользовательское название осталось прежним.

**Acceptance Scenarios**:

1. **Given** пользователь уже задал записи своё название, **When** системе становится доступно название встречи, **Then** отображается пользовательское название.
2. **Given** запись пока имеет автоматически созданное название, **When** позднее появляется более точное название встречи, **Then** автоматически созданное название может обновиться до названия встречи с датой и временем.

### Edge Cases

- Название встречи отсутствует, пустое или состоит только из пробелов: использовать следующий источник по приоритету.
- Название встречи очень длинное: список должен оставаться usable; полное значение должно быть доступно при открытии записи или через предусмотренное отображение полного заголовка.
- Название содержит Unicode, эмодзи, кавычки, слэши или переносы строк: отображать безопасно и читаемо, не превращая его в путь и не нарушая разметку интерфейса.
- Несколько записей имеют одинаковое название встречи: дата и время должны оставаться частью отображаемого названия, чтобы различать записи.
- Календарное сопоставление появилось после первичного создания записи: обновление допускается только для автоматически созданного названия.
- Запись создана без календаря, без контекста приложения или в режиме, где источник не определён: использовать датированный общий fallback.
- Сбой загрузки или синхронизации метаданных не должен блокировать сохранение, воспроизведение, транскрибацию или удаление записи.
- Изменение отображаемого названия не меняет идентификатор записи, аудиоданные, транскрипцию, состояние обработки или право удаления.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST display a meaningful title for every recording in the in-scope recording list and recording detail surfaces.
- **FR-002**: When a meeting title is available, System MUST construct the automatic recording title from that meeting title plus the recording start date and time.
- **FR-003**: When a meeting title is unavailable, System MUST use the recording application's/source name plus the recording start date and time when the source name is available.
- **FR-004**: When neither meeting title nor source application name is available, System MUST use a generic localized recording label plus the recording start date and time.
- **FR-005**: System MUST use the recording start timestamp as the date/time basis and render it in the user's applicable locale and timezone.
- **FR-006**: System MUST apply one deterministic source precedence for automatic titles: user-confirmed title, meeting/calendar title, source application title, then generic recording label.
- **FR-007**: System MUST preserve a user-confirmed title when meeting or application metadata is later added, refreshed, or changed.
- **FR-008**: System MUST allow an automatically generated title to refresh when a more authoritative meeting title becomes available, without creating a second recording or changing recording identity.
- **FR-009**: System MUST treat missing, blank, whitespace-only, and invalid metadata as unavailable and continue to the next source without exposing an empty title.
- **FR-010**: System MUST keep title rendering safe and readable for Unicode, punctuation, emoji, long text, and line-break input; title content MUST NOT be interpreted as markup or a file path.
- **FR-011**: System MUST keep the recording title change independent from audio-file naming; changing the displayed title MUST NOT rename, move, or rewrite the audio asset in this feature.
- **FR-012**: Failure to resolve or synchronize title metadata MUST NOT prevent recording persistence, playback, transcription, deletion, or other existing recording lifecycle actions.
- **FR-013**: System MUST make the complete title available to assistive technologies and to a user who needs to distinguish otherwise truncated titles.

### Key Entities

- **Recording**: A captured meeting artifact with a stable identity, start timestamp, lifecycle state, audio asset, and optional displayed title.
- **Meeting metadata**: Candidate context for a recording, including calendar title, source application name, and the authority/state of each candidate.
- **User-confirmed title**: A title explicitly chosen or edited by the user and therefore protected from automatic replacement.
- **Automatic title**: A deterministic projection of the highest-priority available meeting/source context and the recording start timestamp.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In a representative set of recordings with known meeting titles, 100% of recording list entries show the meeting title and start date/time without requiring the user to open the recording.
- **SC-002**: In a representative set of recordings without meeting titles, 100% show either the source application and start date/time or the dated generic fallback; no new recording is displayed only as «Запись» without date/time.
- **SC-003**: A user can distinguish two recordings with the same meeting title but different start times from the list alone.
- **SC-004**: Updating calendar or application metadata never replaces a user-confirmed title in regression scenarios.
- **SC-005**: Title resolution or synchronization failure produces no regression in recording save, playback, transcription, deletion, or stable recording identity checks.
- **SC-006**: The macOS application and web cabinet use the same title value and source precedence for the same recording.

## Assumptions

- The recording start timestamp already exists as trusted recording metadata and is the correct timestamp for the displayed title.
- Existing calendar matching and recording metadata flows remain the source of candidate titles; this feature does not introduce a new calendar provider or meeting detector.
- «Название приложения» means the verified source application/context associated with the recording, when that context is available.
- The generic label is localized using the product's existing localization conventions.
- User-confirmed titles and automatic-title provenance are already representable by existing recording metadata or can be distinguished without changing recording identity.
- Audio-file naming is explicitly out of scope for the first implementation and may be designed as a separate feature.
- The macOS application and web cabinet are both in scope and must use one consistent title value and source precedence.
