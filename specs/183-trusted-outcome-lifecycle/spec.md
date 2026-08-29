# Feature Specification: Доверенные версии итогов по типам

**Feature Branch**: `codex/183-trusted-outcome-lifecycle`

**Created**: 2026-08-23

**Status**: Draft for implementation review

**Input**: Закрепить простой пользовательский lifecycle итогов: GRAF автоматически создаёт полезный результат, хранит отдельный актуальный результат для каждого типа итогов, мгновенно переключает сохранённые типы и безопасно заменяет только перегенерированный тип.

## Clarifications

### Session 2026-08-23

- Q: Должен ли пользователь проверять и вручную принимать каждую новую генерацию? → A: Нет. Каждый тип итогов хранится отдельно; проверенный результат публикуется автоматически, а перегенерация атомарно заменяет только этот тип и не стирает старый результат при ожидании или ошибке.
- Q: Кто запускает и публикует первую генерацию после готовности расшифровки? → A: Feature 197 владеет source-ready trigger и выбором формата по умолчанию. Feature 183 создаёт slot/read/CAS foundation и единственную fail-closed publication entry point в `ai_service.py`, но не имеет успешного model-generated publication path. Feature 195 достраивает эту же entry point полными receipt/runtime gates; второго publisher быть не может.
- Q: Что происходит с сохранёнными итогами после удаления пользовательского формата? → A: Сохранённый результат остаётся читаемым как результат архивного формата, но сам формат недоступен для новой генерации/обновления и не может незаметно стать новым default.

## User Scenarios & Testing

### User Story 1 — Не показать непроверенные итоги и не требовать лишнего решения (Priority: P1)

Feature 183 убирает пользовательское принятие из целевой модели и оставляет один серверный publication entry point. Пока Features 194/195 не предоставили полный canonical artifact, call membership и receipts, эта entry point обязана завершаться fail-closed: пользователь видит сохранённый результат либо честное состояние без mock/raw/candidate content. Успешная model-generated публикация принадлежит Feature 195, которое расширяет эту же entry point.

**Why this priority**: Основная функция должна работать сама и не перекладывать контроль качества каждой генерации на пользователя.

**Independent Test**: Передать pending model-generated candidate при отсутствии хотя бы одного Feature 194/195 prerequisite; publication entry point не меняет slot, не завершает DispatchIntent, не показывает candidate и не предлагает accept/reject. Существующий current result остаётся доступным. Положительный receipt-backed end-to-end test принадлежит Feature 195.

**Acceptance Scenarios**:

1. **Given** у встречи уже есть сохранённый результат, **When** пользователь открывает встречу, **Then** он видит этот результат без шага принятия и без нового inference.
2. **Given** результат ещё готовится, **When** пользователь открывает встречу, **Then** он видит честное состояние подготовки и может пользоваться расшифровкой.
3. **Given** генерация завершилась ошибкой, не прошла проверку либо полного receipt-backed runtime ещё нет, **When** пользователь открывает встречу, **Then** GRAF показывает понятное состояние и не публикует mock, сырой ответ, candidate или случайную нарезку расшифровки.

---

### User Story 2 — Дать интерфейсу мгновенно читать сохранённые типы (Priority: P1)

В полном пользовательском пути Feature 196 позволяет выбрать «Авто», «Протокол», «1:1» или другой тип. Feature 183 даёт этому интерфейсу точный list/read/ensure contract: уже созданный тип возвращается без повторной генерации, а каждый тип сохраняет собственную актуальную версию.

**Why this priority**: Разные представления одной встречи полезны в разных задачах; переключатель должен ощущаться как выбор документа, а не как опасная перегенерация.

**Independent Test**: Создать результаты для трёх типов и многократно читать каждый через list/read API, обычный browser default/requested route и executable embedded-macOS route contract; каждый запрос возвращает тот же `outcome_set_id`, не создаёт dispatch/model call и не требует наличия пользовательского selector. Реальное переключение и его reload persistence проверяются в Feature 196.

**Acceptance Scenarios**:

1. **Given** для запрошенного типа уже есть актуальная версия, **When** клиент читает этот type slot, **Then** API сразу возвращает точный результат без нового model call.
2. **Given** для запрошенного типа результата ещё нет, **When** клиент вызывает explicit ensure, **Then** GRAF создаёт одну генерацию и возвращает честное состояние именно этого типа; результат другого типа не подставляется под запрошенным названием.
3. **Given** генерация нового типа завершилась ошибкой, **When** клиент снова читает уже созданный тип, **Then** его результат остаётся доступным и неизменным.
4. **Given** клиент повторно запрашивает ранее созданный тип, **When** тип всё ещё доступен, **Then** GRAF возвращает ту же сохранённую ревизию без генерации и без изменения данных других пользователей; selector и запоминание presentation preference относятся к Feature 196.
5. **Given** пользовательский формат удалён после публикации результата, **When** пользователь открывает этот сохранённый результат, **Then** он остаётся читаемым как архивный формат, но ensure/refresh запрещены и никакой другой формат не подставляется вместо него.

---

### User Story 3 — Подготовить безопасную замену одного типа итогов (Priority: P1)

Пользовательский contract сохраняет старую ревизию, пока обновление готовится. Feature 183 реализует slot-scoped expected-current/CAS primitive и блокирует model-generated success; Feature 195 после всех автоматических gates вызывает этот primitive внутри единственной publication transaction.

**Why this priority**: Обновление должно улучшать результат без риска остаться с пустым экраном или потерять результаты других типов.

**Independent Test**: На DB-only non-model fixture проверить slot CAS отдельно от publication: точное expected-current значение может атомарно заменить только целевой pointer, stale/mismatched значение не меняет ничего, второй тип остаётся побайтно неизменным. Затем доказать, что до Feature 195 ни один model-generated candidate не может вызвать успешный CAS.

**Acceptance Scenarios**:

1. **Given** у типа есть актуальная версия, **When** начинается обновление, **Then** старая версия остаётся основной, а подготовка показана ненавязчиво.
2. **Given** будущий Feature 195 подтвердил полный publication contract, **When** он вызывает единственную transaction entry point с точным expected-current, **Then** CAS может целиком заменить только этот type slot; Feature 183 самостоятельно такой вызов не авторизует.
3. **Given** обновление завершилось ошибкой, невалидным ответом или устарело, **When** процесс заканчивается, **Then** старая версия остаётся актуальной без ручного восстановления.
4. **Given** новый результат стал актуальным, **When** пользователь переключается на другой тип, **Then** результат другого типа не изменён.
5. **Given** требуется восстановление после ошибочной регрессии качества, **When** оператор или будущая функция отката использует историю, **Then** предыдущая ревизия доступна технически, хотя обязательное управление историей не навязывается в основном интерфейсе.

---

### User Story 4 — Не опубликовать устаревший или конфликтующий результат (Priority: P1)

GRAF автоматически блокирует публикацию, если во время генерации изменились расшифровка, спикеры, медиа, состояние удаления, версия типа или другой запрос уже обновил тот же type slot.

**Why this priority**: Автоматическая публикация безопасна только при строгих source и concurrency fences.

**Independent Test**: По отдельности изменить каждую исходную ревизию, запустить удаление и смоделировать два обновления одного типа; устаревший результат не меняет актуальную версию и получает различимую причину.

**Acceptance Scenarios**:

1. **Given** источник изменился после старта генерации, **When** результат готов, **Then** он не заменяет актуальную версию и может быть автоматически пересоздан из нового источника по bounded policy.
2. **Given** встреча удаляется или удалена, **When** генерация завершается, **Then** новый результат не публикуется.
3. **Given** два обновления одного типа конкурируют, **When** одно уже опубликовано, **Then** второе не может молча перезаписать его по устаревшему ожидаемому состоянию.
4. **Given** одновременно генерируются разные типы, **When** оба успешно завершаются, **Then** каждый обновляет только собственный slot и не конфликтует с другим.

---

### User Story 5 — Не отправить неправильную версию во время перехода (Priority: P2)

Существующие export/share пути во время перехода используют только документированный тип по умолчанию и его точную актуальную ревизию. Они не выбирают внутренний candidate, последнюю попытку или случайный legacy outcome.

**Why this priority**: Миграция на несколько типов не должна изменить наружный результат или раскрыть непроверенную ревизию. Полный выбор любого типа поставляется отдельно в Feature 203.

**Independent Test**: Для встречи с несколькими типами вызвать существующие share/export пути без нового type-selection API; они используют exact current revision документированного default slot, отклоняют internal/stale результат и не меняются после последующей генерации.

**Acceptance Scenarios**:

1. **Given** существующий внешний путь не передаёт тип, **When** формируется результат, **Then** используется документированный формат по умолчанию и его exact current revision, а не самая новая попытка генерации.
2. **Given** default slot отсутствует или устарел относительно canonical source, **When** создаётся новый export/share, **Then** действие завершается честным недоступным состоянием без fallback на другой тип.
3. **Given** после создания export/share тип был обновлён, **When** открывается ранее созданный артефакт или ссылка, **Then** он остаётся привязан к зафиксированной ревизии и не меняется неявно.

---

### User Story 6 — Сохранить существующие встречи (Priority: P2)

Владелец большого архива встреч не теряет уже показанные итоги. Существующий единичный current result становится актуальной версией своего типа, а неоднозначные старые записи не выбираются эвристически во время просмотра.

**Why this priority**: Миграция не должна ломать пользовательский архив или создавать несколько конкурирующих «Авто» результатов.

**Independent Test**: Прогнать legacy-состояния с явным current result, единственной активной версией, несколькими активными версиями, отсутствующей целью указателя и удалённой встречей; однозначные данные сохраняются, неоднозначные попадают в операторский отчёт.

**Acceptance Scenarios**:

1. **Given** у встречи есть однозначный текущий результат, **When** создаются type slots, **Then** он сохраняется как актуальная ревизия соответствующего типа без изменения содержимого.
2. **Given** старое состояние неоднозначно, **When** выполняется совместимость, **Then** GRAF не угадывает победителя и создаёт операторски проверяемое состояние.
3. **Given** legacy-результат не имеет достоверной идентичности типа, **When** он переносится, **Then** используется один документированный compatibility type без ложной классификации встречи.

## Edge Cases

- Первый автоматический результат формата по умолчанию.
- Выбран тип без результата, пока другой тип обновляется.
- Два запроса обновления одного типа и параллельные запросы разных типов.
- Повтор idempotency key после сетевой неопределённости.
- Расшифровка, медиа, спикеры, template version или deletion epoch меняются до публикации.
- Валидный model response сохранён, но итоговая deterministic verification не завершилась.
- Новый результат короче, длиннее или структурно пуст по сравнению со старым, но формально валиден.
- Тип удалён или его template изменён после создания сохранённого результата.
- Выбранный пользователем тип недоступен из-за прав или удаления custom template.
- Share/export создаётся во время обновления этого типа.
- Default format изменился после создания generation intent или во время share/export.
- У current slot отсутствует цель либо цель принадлежит другой встрече/workspace/type.
- Старые встречи имеют несколько legacy outcome sets без однозначной текущей связи.

## Requirements

### Functional Requirements

- **FR-001**: Каждая встреча MUST поддерживать не более одного актуального опубликованного результата для каждой устойчивой идентичности типа итогов.
- **FR-002**: Результаты разных типов MUST храниться независимо и MUST NOT заменять друг друга.
- **FR-003**: Переключение на уже созданный тип MUST читать его сохранённый актуальный результат без повторной генерации.
- **FR-004**: Выбор типа без результата MUST создавать не более одной эквивалентной активной генерации, показывать честное состояние выбранного типа и сохранять мгновенный возврат к другим готовым типам.
- **FR-005**: Feature 183 MUST оставлять model-generated publication fail-closed и не иметь положительного runtime path, пока Feature 195 не реализует структурную, доказательную, обязательную откалиброванную semantic-entailment для каждого canonical claim, critical-omission по полному deterministic source catalog и отдельную statement-level presentation проверку (entailment, numbers, negation, decision/action state, translation, critical-ID retention), а также source-revision, deletion, access и concurrency checks. Совпадение цитаты или наличие source ref само по себе MUST NOT авторизовать slot CAS; criticality MUST управлять omission/non-droppable gates, а не освобождать non-critical claims от entailment.
- **FR-006**: Внутреннее candidate state MUST NOT требовать от пользователя обычного accept/reject решения и MUST NOT показываться как основной продуктовый объект.
- **FR-007**: Slot-scoped CAS primitive MUST атомарно заменять только актуальный указатель целевого типа при точном expected-current; создание и receipt-backed авторизация новой model-generated ревизии относятся к Feature 195.
- **FR-008**: Ожидание, ошибка, invalid result, stale source, deletion, timeout или конфликт обновления MUST оставлять прежнюю актуальную ревизию этого типа неизменной.
- **FR-009**: Предыдущая успешно опубликованная ревизия MUST сохраняться в технической истории для аудита и безопасного восстановления, но основной UX MUST NOT требовать управления историей.
- **FR-010**: Повтор эквивалентного запроса MUST быть идемпотентным и MUST NOT создавать дополнительную публикацию или model call после доказанного завершения.
- **FR-011**: Два параллельных обновления одного type slot MUST использовать expected-current fence; устаревший результат MUST NOT перезаписывать более новый.
- **FR-012**: Параллельные CAS для разных типов MAY завершаться независимо и MUST изменять только собственные type slots; положительные model-generated race fixtures относятся к Feature 195.
- **FR-013**: Сохранённый Generation Call, raw response, невалидный outcome set или последняя попытка MUST NOT становиться опубликованным результатом без полного автоматического publication gate.
- **FR-014**: `apps/server/src/twobrain_rec_server/outcomes/ai_service.py` MUST оставаться единственным владельцем model-generated publication. Feature 183 MUST создать только slot/source/deletion/expected-current preconditions, transaction-ready CAS primitive и fail-closed entry point; отсутствие любого downstream proof возвращает стабильный отказ и не меняет slot, DispatchIntent или candidate visibility. Feature 195 MUST завершить эту же entry point — не создавать вторую — полным DB-enforced one-to-one attempt/outcome provenance tuple, owner-row canonical/publication receipts, GenerationCall membership, presentation gates, calibration/deletion fences и единым lock order из `contracts/receipts.md`. Успешная receipt finalization, P1–P4/full-schema vectors и canonical/call/calibration race proof являются acceptance Feature 195, не Feature 183.
- **FR-015**: Публикация или обновление одного типа MUST NOT изменять глобальный выбранный тип встречи для других пользователей; хранение presentation preference относится к Feature 196.
- **FR-016**: Существующие share/export пути Feature 183 MUST использовать документированный default type и фиксировать его точную текущую ревизию; выбор «самой новой попытки», другого типа или неявное следование будущим обновлениям запрещены. Пользовательский выбор любого типа относится к Feature 203.
- **FR-017**: При отсутствии результата выбранного типа UI MUST различать подготовку, ошибку, недоступность и type-scoped отсутствие поддерживаемого содержимого без mock/fallback content; meeting-scoped отсутствие полезного источника MUST быть отдельным состоянием и не маскировать готовые другие типы.
- **FR-018**: Создание и публикация MUST блокироваться для удаляемых/удалённых встреч и сохранять действующие workspace/RLS/CSRF/audit boundaries.
- **FR-019**: Legacy-совместимость MUST переносить только однозначно доказуемый current result; неоднозначные записи MUST попадать в metadata-only операторский отчёт.
- **FR-020**: Удаление custom type или изменение template MUST NOT делать исторические результаты нечитаемыми и MUST NOT менять их snapshots.
- **FR-021**: После изменения canonical source все active saved slots на старой
  source revision MUST стать явно `stale`; прежние ревизии MAY оставаться
  читаемыми, но новый share/export из них MUST быть заблокирован до публикации
  актуальных ревизий. Feature 197 создаёт по одному coalesced replacement intent
  для каждого active saved available type, default/current first, но не для
  unsaved/retired типов; Feature 195 публикует каждый replacement только в его
  slot. Уже созданные pinned artifacts остаются неизменяемыми и получают
  действующее удаление/доступ.
- **FR-022**: Feature 183 MUST использовать один уже разрешённый и сохранённый meeting-default slot для generation intent и compatibility egress. Slot MUST хранить stable `template_key`, source/version результата разрешения и момент фиксации; Feature 197 атомарно фиксирует его до dispatch. Для legacy-встречи без snapshot допускается однократный документированный workspace resolver с последующей фиксацией slot до egress. Presentation preference и динамический personal default запрашивающего пользователя MUST NOT менять compatibility egress. Исчезнувший default MUST давать честный отказ, а не fallback на другой доступный тип.
- **FR-023**: Удалённый/retired custom type с опубликованной ревизией MUST оставаться читаемым как read-only snapshot; его availability MUST запрещать ensure/refresh/default selection и создание нового share/export, не меняя сохранённый результат, ранее созданные pinned artifacts и не маскируя его состоянием `no_supported_content`.
- **FR-024**: API MUST представлять result presence, generation attempt, source readiness/freshness и catalog availability как независимые измерения; transcript failure, meeting source empty, type-scoped no-supported-content, retired/unavailable type и provider-ambiguous attempt MUST NOT сворачиваться в одно состояние `unsupported` или `error`. Один versioned `SummaryTypeCatalogEntryV1` snapshot MUST также задавать локализованные name/description, group/category, quick/full rank, availability и opaque provenance/deviation metadata; state changes MUST NOT переупорядочивать selector или full catalog.
- **FR-025**: Compatibility share/export MUST разрешать текущий default slot и записывать точные `template_key`/`outcome_set_id` в артефакт или grant в одной транзакционной точке фиксации. Refresh до этой точки может изменить выбираемую current revision; refresh после неё MUST NOT менять уже созданный артефакт.
- **FR-026**: Shared-slot API and the future Receipt V1 MUST отвергать generated
  `my_actions`, `private_self` и другие subject-dependent controls.
  Feature 183 MUST NOT добавлять positive `my_actions` read path: canonical
  actions и trusted authenticated-subject mapping принадлежат Feature 205, после
  чего Feature 196 MAY добавить zero-inference read-time filter без model call и
  generated revision. Generated subject-dependent outcomes belong only to
  separately numbered Feature 208 and MUST remain rejected by Feature 199.
  `focus=topic` MUST быть discriminated union; raw typed query,
  normalization version/value и resolved canonical topic IDs MUST входить в
  request/idempotency identity; immutable resolved-run manifest, receipt и
  content hash binding входят в Feature 195. Subject-dependent generation MAY появиться только в Feature 208 после отдельной subject-scoped slot/receipt версии с authenticated subject,
  participant-mapping snapshot/hash и access-policy epoch.

### Non-Functional Requirements

- **NFR-001**: Пользователь не может наблюдать пустой промежуток, две актуальные ревизии одного типа или частично обновлённый slot.
- **NFR-002**: Чтение сохранённого типа MUST не зависеть от доступности LLM, Langfuse, Temporal или истории генераций.
- **NFR-003**: Ошибки и аудит вне разрешённых Langfuse, Generation Call и Temporal boundaries MUST оставаться metadata-only.
- **NFR-004**: Изменение MUST переиспользовать существующие outcome sets, generation attempts, dispatch intents, Generation Call ledger и source/deletion fences; новый параллельный outcomes stack запрещён.
- **NFR-005**: Любая новая сущность MAY существовать только как минимальный индекс/pointer для current revision per type, а не как копия содержимого итогов.

### Key Entities

- **Summary Type**: устойчивая пользовательская идентичность формата; версия template является snapshot, а не новым типом сама по себе.
- **Meeting Summary Slot**: связь встречи и типа с единственным актуальным outcome revision.
- **Outcome Revision**: неизменяемый результат конкретной генерации, source basis и template snapshot.
- **Generation Attempt**: попытка создать новую ревизию и её конечное состояние.
- **Internal Candidate**: непубличная ревизия до завершения автоматического publication gate.
- **Current Revision**: опубликованная ревизия конкретного type slot.
- **Superseded Revision**: ранее опубликованная ревизия того же type slot, сохранённая для аудита/восстановления.
- **Display Preference**: пользовательский выбор текущего типа, не изменяющий meeting truth для других пользователей.
- **Generation Call**: сохранённый факт внешнего model call; не является опубликованными итогами.

## Success Criteria

- **SC-001**: Для набора минимум из трёх типов одной встречи 100% повторных переключений используют сохранённые результаты и не создают model call.
- **SC-002**: Во всех DB-only CAS success/error/stale/deletion/timeout/concurrency fixtures меняется только целевой type slot; остальные типы остаются побайтно неизменны. Model-generated success не входит в Feature 183.
- **SC-003**: В 100% ошибочных и невалидных обновлений предыдущая актуальная ревизия остаётся видимой и доступной без действий пользователя.
- **SC-004**: В 100% Feature 183 fixtures model-generated candidate не публикуется и не двигает slot. Feature 195 отдельно доказывает, что положительный path невозможен без schema/ref/span, откалиброванной canonical semantic/omission проверки, полной statement-level presentation проверки, source, deletion, access и expected-current checks.
- **SC-005**: Повтор каждого завершённого запроса не создаёт дополнительной публикации или повторного inference в 100% idempotency fixtures.
- **SC-006**: Доменные проверки не находят type slot с двумя актуальными ревизиями, broken pointer или outcome другой встречи/workspace/type.
- **SC-007**: Все однозначные legacy fixtures сохраняют ранее опубликованный текст побайтно; все неоднозначные fixtures дают отдельный отчёт и ноль runtime-угадываний.
- **SC-008**: Открытие сохранённого типа остаётся доступным во всех предусмотренных outage-сценариях внешних AI-зависимостей.
- **SC-009**: Во всех source-change fixtures каждый active saved old-source slot
  становится `stale`, его старая ревизия остаётся различимо читаемой, новый
  egress блокируется, retired/unsaved типы не генерируются и поздний старый
  candidate не становится current ни в одном slot.
- **SC-010**: Во всех retired/unavailable/source-empty/transcript-failed/ambiguous fixtures API возвращает однозначную комбинацию независимых состояний и ни разу не предлагает unsafe retry или другой тип как тот же результат.
- **SC-011**: В 100% share/export-versus-refresh race fixtures созданный артефакт содержит ровно одну ревизию, определённую транзакционной точкой фиксации, и никогда не следует за последующим refresh.
- **SC-012**: В 100% Feature 183 shared-slot identity fixtures generated
  `my_actions`/`private_self` отклоняются и positive `my_actions` route/control
  отсутствует; downstream Feature 205/196 отдельно доказывает authenticated
  filtering/no-existence-leak. Mutation raw/normalized/resolved topic focus
  остаётся различимым typed request identity; его manifest/receipt/content hashes
  проверяются Feature 195.

## Scope Boundaries

### In Scope

- Устойчивая идентичность summary type и current revision per meeting/type.
- Отсутствие пользовательского accept/reject и одна fail-closed publication entry point.
- Transaction-ready slot-scoped expected-current/CAS primitive без model-generated success path.
- Сохранение старой ревизии при ожидании/ошибке и техническая история успешных замен.
- Idempotency, source, deletion, access и concurrency fences.
- Default type compatibility contract для существующих share/export путей.
- Meeting-pinned/workspace default resolver boundary, retired-result readability и ортогональный lifecycle state contract.
- Детерминированная совместимость существующих встреч.
- Lifecycle/data/API contracts и regression matrix.

### Out of Scope

- Новая схема meeting intelligence и prompt chain.
- Успешная model-generated publication, owner-row canonical/publication receipt finalization, P1–P4/full-schema vectors и canonical/call/calibration race proof; это Feature 195, которое достраивает ту же `ai_service.py` entry point.
- Настройка `gpt-5.6-luna`, реальные генерации, Langfuse dataset/judge/promotion и GEPA.
- Новая Temporal workflow, automatic post-transcript trigger и default-precedence UX; это Feature 197/199. Feature 183 принимает уже разрешённый `default_template_key` и не вычисляет динамический personal default на чтении.
- KRISP-parity visual redesign, каталог типов, custom builder и UI истории ревизий.
- Ручной обязательный review/accept/reject для обычной генерации.
- Пользовательский выбор произвольного summary type для share/export и полный egress UX/API; это Feature 203.
- Изменение retention/deletion политики Langfuse или Temporal.
- Реализация KRISP-parity UI в рамках Feature 183. Она разрешена новой
  конституцией, но остаётся scope Feature 196; extracted assets, source,
  binaries, private API/protocols, private content и proprietary model behavior
  не разрешены.
- Commit, GitHub issues, PR, prompt promotion, release и production deploy.

## Dependencies

- Feature 182 canonical speaker turns как источник устойчивых evidence refs; до merge/release 182 Feature 183 не считается готовой к поставке.
- Существующие meeting/outcome/generation/dispatch модели, RLS и deletion contracts.
- Действующая конституция GRAF и её external dependency boundaries.
- После Feature 182 Feature 183 может независимо реализовать и проверить slot/migration/read/default-egress/CAS foundation и fail-closed publication seam без synthetic successful receipts. Feature 195 владеет первым положительным model-generated publication test и не может считаться готовой, пока Feature 194 не предоставит canonical artifact contract. Пользовательский rollout всей функции дополнительно блокируют 196, 197, 198, 200 и 202–204 из `program-roadmap.md`.

## Assumptions

- Формат по умолчанию запускается после готовности транскрипта отдельной Feature 197; Feature 183 предоставляет slot/idempotency/fail-closed boundary, а Feature 195 делает положительную публикацию безопасной.
- Тип определяется устойчивым opaque `template_key`; существующий ключ не переименовывается при изменении `template_version`, даже если legacy-имя ключа содержит `-v1`. Изменение версии не стирает уже созданный тип и его историю.
- Выбранный тип хранится как пользовательская UI preference; внешний share/export получает явный type/revision snapshot.
- История ревизий остаётся internal/operator-only для аудита и аварийного восстановления. Пользовательская история/undo не входит в эту программу и требует отдельного будущего продуктового решения.
- В коде уже есть internal candidate и outcome revision lifecycle; Feature 183 добавляет только недостающий per-type current pointer, CAS/fences и единственную закрытую publication entry point. Receipt-backed policy добавляет Feature 195 в ту же точку.
- UX/UI/IA parity с KRISP реализуется Feature 196 по принятому
  reference-fidelity решению Constitution 5.0.0.
