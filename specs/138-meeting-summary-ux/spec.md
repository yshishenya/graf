# Feature Specification: Удобные и проверяемые итоги встречи

**Feature Branch**: `codex/138-meeting-summary-ux`

**Created**: 2026-08-03

**Status**: Draft

**Input**: Пользовательская проблема: на странице встречи итоговые данные уже
есть, но они выглядят как длинный список технических статусов; пользователю
трудно за полминуты понять суть, решения, действия, ответственных, сроки и
основания для доверия.

## Clarifications

Сессия 2026-08-03: критичных неоднозначностей не осталось после локального
runtime-аудита, reference research и review субагентов. Решения по owner/due,
пустым категориям, source seek, candidate lifecycle и degraded states записаны в
[clarifications.md](./clarifications.md) и являются границами P0.

Уточнение 2026-08-04: по результатам сравнения с Krisp и похожими recap-
продуктами интерфейс намеренно оставляет только спокойный Notes-документ; пустые
карточки, повторяющиеся status chips и отдельная export CTA удалены из scope.

## User Scenarios & Testing

### User Story 1 - Пользователь понимает главное за 30 секунд (Priority: P1)

Как участник встречи, я хочу сразу увидеть краткий смысл, решения и действия,
чтобы не читать все технические состояния и не искать важное в расшифровке.

**Why this priority**: Это основной job-to-be-done страницы review; текущая
равномерная восьмикатегорийная выдача мешает принять следующее решение.

**Independent Test**: Открыть синтетическую готовую встречу на desktop и mobile,
проверить порядок и визуальную иерархию блоков, отсутствие горизонтального
скролла и наличие первого понятного действия.

**Acceptance Scenarios**:

1. **Given** сохранённые итоги доступны, **When** пользователь открывает вкладку
   «Итоги», **Then** в начале страницы видны «Кратко», «Действия» и
   «Решения», а вторичные категории не конкурируют с ними по визуальному весу.
2. **Given** в категории несколько пунктов, **When** пользователь сканирует
   раздел, **Then** пункты различимы, переносят длинный текст и не прячутся за
   техническим reason-копирайтом.
3. **Given** в категории нет подтверждённого результата, **When** пользователь
   открывает встречу, **Then** состояние объясняется коротко и честно, без
   синтетического текста и без равного веса с готовым содержимым; вторичные
   состояния находятся в одном раскрываемом блоке.

### User Story 2 - Пользователь превращает итог в действие (Priority: P1)

Как участник встречи, я хочу видеть ответственного, срок и источник для каждого
действия, чтобы понять, что делать дальше и проверить основание формулировки.

**Why this priority**: Модель уже хранит `owner_text`, `due_date_text` и
`source_refs`, но текущий интерфейс скрывает owner/due и выводит источник только
как неинтерактивный таймкод.

**Independent Test**: Отрендерить synthetic action item со всеми и с частью
метаданных; проверить условительный вывод owner/due и кликабельные source refs.

**Acceptance Scenarios**:

1. **Given** owner или due date сохранены в результате, **When** пользователь
   читает действие, **Then** эти значения отображаются рядом с действием.
2. **Given** owner или due date отсутствуют, **When** пользователь читает
   действие, **Then** UI не выдумывает значение и не добавляет пустой
   placeholder.
3. **Given** у действия есть source reference, **When** пользователь нажимает
   на таймкод, **Then** существующий player получает seek к этому фрагменту, а
   расшифровка остаётся доступной в том же контексте.
4. **Given** UI показывает action item, **Then** он не утверждает, что действие
   назначено во внешнюю систему или уже выполнено.

### User Story 3 - Пользователь проверяет доверие к AI (Priority: P1)

Как владелец или разрешённый участник, я хочу отличать сохранённый итог,
неопределённость и обработку, чтобы не принять предположение модели за факт.

**Independent Test**: Проверить готовый, `not_found`, `not_inferable`,
`processing`, `blocked`, `unsafe` и `unavailable` synthetic states; убедиться,
что текст состояния различим без цвета и приватное содержимое не появляется в
заблокированном состоянии.

**Acceptance Scenarios**:

1. **Given** состояние не `available`, **When** оно отображается, **Then** есть
   понятная русская label и следующий bounded смысл («готовится», «не найдено»,
   «нужна проверка», «недоступно»).
2. **Given** outcome source basis известен, **When** пользователь просматривает
   итоги, **Then** источник/происхождение результата сообщается один раз на
   уровне блока и не раскрывает внутренние credentials, storage keys или raw
   model response.
3. **Given** outcome заблокирован или отсутствует, **Then** UI не рендерит
   вложенные outcome items как будто они подтверждены.
4. **Given** владелец запускает новый формат или регенерацию, **Then** текущий
   сохранённый результат остаётся видимым до явного принятия candidate.

### User Story 4 - Пользователь переходит от вывода к доказательству (Priority: P2)

Как участник встречи, я хочу одним действием перейти от важного пункта к
расшифровке и player, чтобы проверить контекст без повторного поиска.

**Independent Test**: Для synthetic item с двумя references проверить две
seek-кнопки, доступные имена, отсутствие горизонтального overflow и сохранение
работы вкладок «Итоги»/«Расшифровка».

**Acceptance Scenarios**:

1. **Given** reference доступен, **When** он отображается, **Then** это
   семантическая кнопка с временем, понятным accessible label и существующим
   `data-seek-seconds` поведением.
2. **Given** пользователь меняет вкладку, **Then** состояние вкладки отражается
   в URL hash и восстанавливается после refresh.
3. **Given** viewport шириной 390 CSS px, **Then** разделы, метаданные, tabs и
   fixed player не создают горизонтальный overflow или обрезанный primary CTA.

### User Story 5 - Сбой и неполнота остаются понятными (Priority: P2)

Как пользователь, я хочу понимать, что можно сделать при processing/blocked и
не терять доступный transcript, чтобы сбой итогов не выглядел как потеря записи.

**Independent Test**: Открыть synthetic processing, blocked и partial review;
проверить truthful state copy, сохранение существующих вкладок и отсутствие
приватного контента в blocked HTML.

**Acceptance Scenarios**:

1. **Given** итоги ещё формируются, **Then** UI говорит «готовится» и не создаёт
   fake summary.
2. **Given** итоги заблокированы, **Then** UI объясняет bounded состояние и не
   предлагает несуществующий retry/export/integration action.
3. **Given** transcript уже доступен при неполных итогах, **Then** пользователь
   по-прежнему может открыть вкладку «Расшифровка» и player.

### User Story 6 - Пользователь не перегружен лишними действиями (Priority: P2)

Как участник встречи, я хочу видеть только нужные действия рядом с итогами, чтобы
саммари оставалось спокойным и не дублировало существующее меню встречи.

**Independent Test**: Для synthetic review проверить, что summary не добавляет
вторую export CTA, а существующий share/export flow остаётся доступным.

**Acceptance Scenarios**:

1. **Given** пользователь находится в блоке итогов, **Then** рядом с заголовком
   нет дублирующей export CTA.
2. **Given** пользователь хочет сохранить результат, **Then** существующее меню
   Share/Export остаётся доступным и сохраняет текущие policy ограничения.

## Requirements

### Functional Requirements

- **FR-001**: Страница итогов MUST использовать спокойный порядок «Кратко →
  Действия → Решения → Дополнительные разделы» при сохранении всех
  существующих восьми категорий и их `data-outcome-category`; дополнительные
  категории находятся внутри одного закрытого по умолчанию disclosure.
- **FR-002**: Доступный outcome item MUST показывать текст, а для сохранённых
  значений — owner, due date и truth label без подстановки непроверенных данных.
- **FR-003**: Каждый доступный source reference MUST быть представлен
  семантической seek-кнопкой с timestamp и доступным именем; она MUST reuse
  существующее playback seek поведение.
- **FR-004**: `not_found`, `not_inferable`, `processing`, `blocked`, `unsafe` и
  `unavailable` MUST иметь различимый текстовый статус; цвет MUST не быть
  единственным носителем смысла.
- **FR-005**: Состояния, в которых outcome items не подтверждены, MUST NOT
  показывать их как готовое содержимое.
- **FR-006**: Web и embedded detail routes MUST сохранять одинаковый порядок,
  states, source basis и контентные access/privacy ограничения.
- **FR-007**: Выбор вкладки «Итоги»/«Расшифровка» MUST отражаться в URL hash и
  корректно восстанавливаться после reload без нового endpoint.
- **FR-008**: Responsive layout MUST оставаться usable на 390 CSS px и
  desktop-ширинах, включая fixed playback bar, длинные строки и focus-visible.
- **FR-009**: Existing candidate preview, explicit acceptance, share/export,
  deletion copy, access checks и server-mediated capture boundary MUST remain
  unchanged.
- **FR-010**: Реализация MUST использовать только существующие server-rendered
  шаблоны, CSS/JS и view-model fields; новая БД-схема, provider call,
  интеграция задач или UI-фреймворк не входят в этот slice.
- **FR-011**: Summary UI MUST NOT добавлять отдельный inline export opener;
  существующие Share/Export controls встречи MUST оставаться доступными и
  server-mediated.

## Edge Cases

- Summary доступно, но transcript/player недоступен: итог остаётся видимым,
  source reference не обещает действие, которого нет.
- У item нет текста, но есть owner/due/source: пустой item не создаёт пустую
  карточку; метаданные не превращаются в новый outcome.
- У item больше двух source refs: показываются первые два, как в текущем
  ограниченном review-контракте; полный экспорт остаётся отдельным surface.
- Длинный text, owner или due date переносится в одну колонку без overflow.
- Все категории `not_found`/`not_inferable`: страница остаётся понятной и не
  выглядит как готовая встреча с пустым fake summary.
- `unsafe`, `blocked`, `processing` или stale candidate: item text не
  появляется до разрешённого stored/accepted состояния.
- Web и embedded routes используют один renderer; расхождение считается
  ошибкой контракта.

## Success Criteria

- **SC-001**: На synthetic ready review в viewport 1440×900 видны заголовок,
  status, «Кратко» и начало «Действия»/«Решения» без чтения technical reason
  для каждой категории.
- **SC-002**: На synthetic ready review с 390 CSS px нет horizontal overflow,
  обрезанных action metadata или недоступного primary content; fixed player не
  закрывает первый actionable block.
- **SC-003**: Для каждого synthetic action item с сохранёнными owner/due они
  присутствуют в HTML и визуальном runtime; при отсутствии полей в HTML нет
  fabricated owner/due.
- **SC-004**: Количество source seek controls равно числу отображённых source
  references; каждый control имеет `data-seek-seconds` и non-empty accessible
  name.
- **SC-005**: Web/embedded parity сохраняет 8 outcome categories, source basis
  и state map; blocked/processing fixtures не раскрывают outcome item text.
- **SC-006**: Focused pytest, browser runtime check, `git diff --check` и
  `infra/scripts/ci-local.sh --fast` проходят; production deploy не заявляется.
- **SC-007**: Для ready synthetic review нет дополнительного inline
  summary-export opener; browser runtime подтверждает доступность существующего
  meeting export trigger и отсутствие ложного action в blocked fixture.

## Assumptions

- Существующая view-model truth state является источником истины; UI не выводит
  новые AI-выводы и не меняет stored outcome.
- Отсутствие owner/due означает, что UI ничего не добавляет; это не задача без
  ответственного или срока и не повод показывать placeholder.
- Источник остаётся segment/timestamp reference; отдельная страница evidence,
  полнотекстовый поиск и cross-meeting retrieval не нужны для P0.
- Вкладки и persistent player уже являются каноническим review workflow и
  переиспользуются.

## Out of Scope

- Новые поля БД, миграции, API, AI prompt/model, генератор outcome или provider.
- Ручное редактирование canonical summary/action item, подтверждение owner/due,
  статусы выполнения, task manager integrations и уведомления.
- Отдельная inline export CTA, per-item truth chips, empty-state карточки и
  расширенный dashboard для всех восьми категорий.
- Полнотекстовый поиск по transcript/outcomes, cross-meeting carry-over,
  AI-chat и история версий с diff.
- Изменение macOS capture, audio routing, MediaScribe boundary, Langfuse или
  Temporal retention/deletion policy.
- Production deploy, изменение access policy и массовая reconcile-операция.
