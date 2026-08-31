# Feature Specification: Безопасная инвентаризация и retirement legacy

**Feature Branch**: `220-legacy-retirement`

**Created**: 2026-08-31

**Status**: Draft

**Input**: Продолжение governance-процесса GRAF: после запрета нового legacy провести полный read-only inventory существующих aliases, fallback-путей, старых состояний, миграций, Temporal и macOS update compatibility и подготовить независимые безопасные retirement slices.

## Actors and Goals

- **Владелец продукта** — понимает, какие legacy-контуры существуют, зачем они нужны и когда их можно безопасно удалить.
- **Feature/maintenance agent** — описывает один retirement slice, его границы, тесты, миграцию и rollback, не удаляя соседние контуры.
- **Reviewer** — подтверждает классификацию, риск, доказательства и готовность к cutover.
- **Release operator** — не включает retirement в release train без полного evidence и одобренного rollback.
- **Оператор Dev** — проверяет миграцию и совместимость только на изолированной Dev-копии.

## User Scenarios & Testing

### User Story 1 — Получить полный legacy inventory (Priority: P1)

Владелец получает единый metadata-only список legacy-поверхностей: старые имена, aliases, fallback-конфигурации, флаги, миграции, Temporal compatibility, Sparkle/update paths, тестовые fixtures и документацию.

**Why this priority**: удаление без полного inventory может сломать пользовательские данные, старые клиенты или незавершённые workflow.

**Independent Test**: повторяемый скан на чистом exact SHA формирует inventory с путём, типом, owner, источником evidence и текущим статусом, не записывая содержимое пользовательских данных.

**Acceptance Scenarios**:

1. **Given** репозиторий и доступные metadata-only источники, **When** запускается inventory, **Then** каждый найденный contour имеет уникальный идентификатор и ссылку на файл/контракт.
2. **Given** пользовательские записи, аудио, transcript или секреты, **When** строится inventory, **Then** в отчёт попадают только тип, путь, digest и агрегированные признаки, без содержимого.
3. **Given** повторный запуск на том же SHA, **When** сравниваются результаты, **Then** порядок и идентификаторы стабильны.

### User Story 2 — Принять классификацию и приоритет (Priority: P1)

Для каждого contour владелец и reviewer выбирают `remove` или `retain-with-exception`, указывают owner, риск, trigger, expiry и зависимость от данных/клиентов.

**Why this priority**: классификация отделяет безопасное удаление от временной совместимости и предотвращает бесконечное «оставить на всякий случай».

**Independent Test**: validator принимает только полную запись классификации и блокирует отсутствие owner, риска, срока или retirement trigger.

**Acceptance Scenarios**:

1. **Given** contour нужен старому клиенту, **When** выбирается `retain-with-exception`, **Then** запись содержит дату окончания, условие удаления и связанную retirement task.
2. **Given** contour больше не нужен и есть доказательства, **When** выбирается `remove`, **Then** создаётся отдельный slice с cutover и rollback.
3. **Given** истёкшая exception, **When** запускается governance gate, **Then** merge и release блокируются.

### User Story 3 — Выполнять retirement маленькими slices (Priority: P1)

Каждый contour выводится отдельной задачей с минимальным diff, независимой проверкой, явной границей миграции и обратимым cutover.

**Why this priority**: малые slices ограничивают blast radius и позволяют выпускать изменения реже, но с полной проверкой train.

**Independent Test**: один slice можно проверить и откатить независимо от остальных contour, не меняя production data до approved release gate.

**Acceptance Scenarios**:

1. **Given** slice затрагивает migration или Temporal history, **When** готовится план, **Then** описаны expand/contract, backup, replay/compatibility и rollback.
2. **Given** slice затрагивает macOS update path, **When** готовится план, **Then** сохранены trust identity, подписанный rollback и совместимость поддерживаемого клиента.
3. **Given** slice не имеет доказанного rollback, **When** его предлагают к merge, **Then** governance gate отклоняет его.

### User Story 4 — Не добавлять новое legacy (Priority: P1)

Каждая новая feature обязана доказать, что она не добавляет alias, fallback, flag, dependency, fixture или документационный путь, сохраняющий старую архитектуру без временного исключения.

**Why this priority**: иначе cleanup не уменьшает долг, а только создаёт новые контуры.

**Independent Test**: changed-path scanner и Legacy Impact validator блокируют несоответствие между изменёнными файлами и декларацией.

**Acceptance Scenarios**:

1. **Given** изменён legacy-sensitive путь, **When** PR объявляет `untouched`, **Then** gate требует корректную классификацию или exception.
2. **Given** добавлен fallback с expiry и owner, **When** валидируется PR, **Then** он проходит только при наличии retirement task.

### User Story 5 — Иметь доказуемый closeout (Priority: P2)

Владелец получает русский issue/PR closeout с exact SHA, inventory digest, validation evidence, known limitations и ссылками на последующие slices.

**Why this priority**: без traceability невозможно понять, что именно проверялось и какой legacy ещё остаётся.

**Independent Test**: closeout validator отклоняет отчёт без exact SHA, scope, результата проверки, owner или незакрытого риска.

## Edge Cases and Failure States

- GitHub или remote discovery недоступны: inventory помечается неполным и не может закрыть contour.
- Один путь обслуживает одновременно новый и старый контракт: сначала выделяется boundary, затем выполняется expand/contract.
- Историческая миграция присутствует в данных, но отсутствует в кодовом graph: запрещены blind stamp/reset; создаётся отдельный migration repair slice.
- Temporal workflow уже существует в истории: удаление runtime-кода не считается безопасным без replay/compatibility evidence.
- Старый macOS-клиент обновляется через Sparkle: rollback должен сохранять bundle identity, signing trust и appcast contract.
- Найден секрет, raw audio или transcript: запись немедленно исключается из отчёта и заменяется metadata-only digest.
- Exception просрочена или не имеет owner: merge/release fail-closed.
- Inventory меняется между двумя SHA: предыдущий отчёт становится stale и не закрывает новый candidate.

## Requirements

### Functional Requirements

- **FR-001**: Система MUST формировать детерминированный metadata-only inventory всех заявленных legacy-категорий.
- **FR-002**: Каждая запись MUST содержать contour ID, category, source path, owner, risk, classification, evidence и статус.
- **FR-003**: Inventory MUST быть привязан к exact source SHA и digest входных metadata.
- **FR-004**: Inventory MUST исключать secrets, credentials, signed URLs, raw audio, transcript text, private meeting data и строки пользовательского содержимого.
- **FR-005**: `retain-with-exception` MUST требовать owner, future expiry, removal trigger, risk, validation и linked retirement task.
- **FR-006**: Просроченная или неполная exception MUST блокировать governance gate.
- **FR-007**: `remove` MUST иметь отдельный independently testable retirement slice.
- **FR-008**: Каждый slice MUST описывать migration/cutover boundary, backup/restore rehearsal, compatibility impact и rollback.
- **FR-009**: Migration и Temporal slices MUST иметь отдельные replay/idempotency или expand/contract checks до production approval.
- **FR-010**: macOS update slices MUST сохранять bundle identity, signing trust, designated requirement и проверенный rollback.
- **FR-011**: Changed-path scanner MUST сопоставлять legacy-sensitive изменения с Legacy Impact classification.
- **FR-012**: Новый alias, fallback, flag, dependency, fixture или compatibility path MUST блокироваться без time-bounded exception.
- **FR-013**: Inventory MUST поддерживать append-only history и явно помечать stale результаты после изменения SHA.
- **FR-014**: Closeout MUST ссылаться на issue, PR, task IDs, exact SHA, validation commands и known limitations.
- **FR-015**: Ни один retirement slice MUST NOT выполнять production deploy, irreversible data deletion или ручное изменение migration pointer без отдельного approved release gate.
- **FR-016**: Все issue, PR и closure notes MUST следовать русскому GitHub issue canon.

### Key Entities

- **Legacy Contour** — идентифицируемая compatibility-поверхность с категорией, источником, owner и риском.
- **Legacy Exception** — временное разрешение сохранить contour с expiry и trigger удаления.
- **Retirement Slice** — отдельная задача удаления или миграции с тестами, cutover и rollback.
- **Inventory Snapshot** — immutable metadata-only снимок на exact SHA.

## Success Criteria

### Measurable Outcomes

- **SC-001**: 100% legacy-записей в принятом inventory имеют owner, category, classification, risk и source evidence.
- **SC-002**: 100% `retain-with-exception` записей имеют future expiry и linked retirement task; expired exceptions не проходят validator.
- **SC-003**: Повторный inventory на одном SHA выдаёт одинаковый digest и порядок записей.
- **SC-004**: В metadata-only отчётах отсутствуют raw audio, transcript text, secrets и пользовательские строки.
- **SC-005**: Каждый approved `remove` contour связан ровно с одним independently testable retirement slice.
- **SC-006**: Changed-path governance test блокирует 100% synthetic случаев нового unowned legacy.
- **SC-007**: Ни один retirement slice не проходит release gate без backup/restore, cutover и rollback evidence.
- **SC-008**: Closeout каждого slice содержит exact SHA, команды проверки, результат, ограничения и ссылки на issue/PR.

## Assumptions

- Feature 216 и её governance contracts являются базовыми правилами этого процесса.
- Feature 220 сначала выполняет inventory и классификацию; массовое удаление не входит в первый slice.
- Production data, Temporal history и поддерживаемые macOS-клиенты считаются защищёнными границами.
- Для миграционных contour используется отдельная Feature 221, если сначала требуется восстановить локальную Dev-базу.
- Владелец и reviewer определяют допустимый срок поддержки каждой exception; отсутствие ответа означает блокировку, а не бессрочное продление.

## Scope

### In Scope

- Metadata-only inventory aliases, fallbacks, flags, dependencies, fixtures, migrations, Temporal, Sparkle/update paths и documentation.
- Классификация, owner/risk register, exceptions, prioritization и task-backed retirement backlog.
- Изменения governance validators, templates и runbooks, необходимые для запрета нового legacy.
- Безопасные локальные/Dev rehearsal для будущих retirement slices.

### Out of Scope

- Массовое удаление legacy в одном PR.
- Production migration/deploy, удаление volume, ручное изменение `alembic_version`.
- Удаление Temporal history или Sparkle compatibility без отдельной approved feature.
- Изменение пользовательского поведения capture, auth, billing, transcription или deletion.

## Legacy Impact

- **Classification**: `remove`
- **New legacy**: запрещён; новые exceptions допускаются только с owner, expiry, trigger и task.
- **Existing contours**: сначала фиксируются metadata-only inventory; runtime removal выполняется отдельными slices.
- **Protected compatibility**: migrations, Temporal history, Sparkle/client updates и production data требуют собственных cutover/rollback gates.
