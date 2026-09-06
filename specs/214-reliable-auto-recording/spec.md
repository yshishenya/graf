# Feature Specification: Надёжный полный цикл автоматической записи

**Feature Branch**: `codex/214-reliable-auto-recording`

**Created**: 2026-08-30

**Status**: Draft

**Input**: User description: "Полностью проверить и сделать надёжным весь путь
автозаписи: локальные состояния «Всегда», «Спрашивать», «Никогда», запуск через
8 секунд, точная остановка после встречи, сохранение и восстановление записи,
показ неотправленных и повреждённых записей в общем списке, действие
«Отправить» и полное поэтапное удаление серверного управления этим выбором."

## Context And Product Decision

У пользователя есть ровно три локальных состояния для каждого проверенного
приложения: `Всегда`, `Спрашивать`, `Никогда`. Новая установка использует
`Спрашивать`. В этом режиме GRAF показывает окно и через 8 секунд начинает
запись, если пользователь не выбрал другое действие и встреча ещё продолжается.

Галочка `Запомнить выбор` меняет настройку только вместе с явной кнопкой:
`Записать` сохраняет `Всегда`, `Не записывать` сохраняет `Никогда`. Без галочки
меняется только текущая встреча. Истечение таймера никогда не меняет настройку.

Этот выбор принадлежит клиенту. Сервер не хранит, не разрешает и не
подтверждает его. Общие ограничения рабочего пространства, правила согласия,
разрешения macOS, готовность локального хранилища, видимый индикатор и остановка
одним действием сохраняются.

Надёжность рассматривается как один путь: определение встречи → решение о
записи → запуск → остановка → локальное сохранение → восстановление после сбоя
→ отображение в общем списке → отправка. Нельзя считать автозапись исправной,
если запись началась, но не остановилась, стала невидимой после сбоя или
потерялась из интерфейса при ошибке отправки.

## Clarifications

### Session 2026-08-30

- Q: Что делать в режиме `Спрашивать`, если пользователь ничего не нажал? → A:
  Через 8 секунд начать запись, если встреча всё ещё активна и обязательные
  проверки пройдены.
- Q: Как удалять серверное управление выбором автозаписи? → A: Сначала выпустить
  клиент, который больше от него не зависит, затем удалить серверное поле,
  настройки, проверки и тесты.
- Q: Что показывать, если локальную запись невозможно восстановить? → A:
  Статус `Запись повреждена`; доступно существующее удаление, действие
  `Отправить` не показывается.
- Q: Как назвать ручное действие для исправной, но не отправленной записи? → A:
  `Отправить`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Понятный локальный выбор для каждого приложения (Priority: P1)

Как пользователь, я хочу для каждого приложения выбрать `Всегда`,
`Спрашивать` или `Никогда` и в любой момент изменить решение, чтобы поведение
автозаписи было понятным и не зависело от сервера.

**Why this priority**: Это пользовательский источник правды для всего
автоматического пути. Ошибка здесь приводит либо к пропущенной встрече, либо к
неожиданной записи.

**Independent Test**: На чистых локальных настройках и проверенном списке
приложений назначить каждое состояние одной строке и всем строкам, перезапустить
GRAF без сети и убедиться, что выбор и следующее решение о записи сохранились.

**Acceptance Scenarios**:

1. **Given** GRAF установлен впервые, **When** открыты настройки автозаписи,
   **Then** каждое известное приложение имеет состояние `Спрашивать`.
2. **Given** приложение имеет `Всегда`, **When** подтверждена встреча,
   **Then** вопрос не показывается и GRAF пытается начать запись после всех
   обязательных проверок.
3. **Given** приложение имеет `Спрашивать`, **When** подтверждена встреча,
   **Then** показывается вопрос с таймером 8 секунд.
4. **Given** приложение имеет `Никогда`, **When** подтверждена встреча,
   **Then** вопрос и автоматическая запись не появляются.
5. **Given** у приложений разные состояния, **When** открыт общий выбор,
   **Then** он показывает `Разные`, не изменяя строки.
6. **Given** пользователь выбирает одно из трёх значений `Для всех приложений`,
   **When** изменение подтверждено локально, **Then** это значение получают все
   текущие проверенные приложения, а последующая правка одной строки не меняет
   остальные.
7. **Given** сервер недоступен, **When** пользователь открывает или меняет
   настройки, **Then** текущие локальные значения доступны и сохраняются.

---

### User Story 2 - Предсказуемый вопрос с восьмисекундным запуском (Priority: P1)

Как пользователь режима `Спрашивать`, я хочу либо принять решение сам, либо
позволить GRAF начать запись через 8 секунд, а постоянное правило сохранить
только осознанно.

**Why this priority**: Таймер уже является привычным поведением, но его
результат и сохранение галочки должны быть однозначными во всех гонках.

**Independent Test**: Для одной искусственной встречи проверить обе кнопки с
галочкой и без неё, истечение таймера, окончание встречи во время таймера,
повторные нажатия и смену настройки во время открытого вопроса.

**Acceptance Scenarios**:

1. **Given** состояние `Спрашивать`, **When** появляется вопрос, **Then** видны
   имя приложения, `Записать`, `Не записывать`, `Запомнить выбор` и оставшееся
   время из 8 секунд.
2. **Given** галочка выключена, **When** пользователь выбирает `Записать`,
   **Then** начинается только текущая запись, а состояние остаётся
   `Спрашивать`.
3. **Given** галочка включена, **When** пользователь выбирает `Записать`,
   **Then** начинается текущая запись, а локальное состояние становится
   `Всегда` и сразу отображается в настройках.
4. **Given** галочка выключена, **When** пользователь выбирает
   `Не записывать`, **Then** пропускается только текущая встреча, а состояние
   остаётся `Спрашивать`.
5. **Given** галочка включена, **When** пользователь выбирает
   `Не записывать`, **Then** текущая встреча пропускается, а локальное состояние
   становится `Никогда` и сразу отображается в настройках.
6. **Given** пользователь ничего не нажал, **When** истекли 8 секунд и встреча
   всё ещё активна, **Then** начинается текущая запись, а сохранённое состояние
   не меняется независимо от положения галочки.
7. **Given** встреча закончилась до истечения таймера, **When** приходит граница
   окончания, **Then** вопрос закрывается, запись не начинается и настройка не
   меняется.
8. **Given** решение для этого вопроса уже принято, **When** приходит повторное
   нажатие или событие таймера, **Then** второго запуска, пропуска или сохранения
   настройки не происходит.

---

### User Story 3 - Одна запись точно заканчивается вместе со встречей (Priority: P1)

Как пользователь, я хочу, чтобы автоматическая запись запускалась один раз,
оставалась управляемой и обязательно останавливалась после окончания встречи,
включая сон Mac и завершение встречи во время запуска записи.

**Why this priority**: Неостановленная запись захватывает лишний звук, расходует
место и нарушает доверие к продукту.

**Independent Test**: Прогнать одну и ту же искусственную встречу с обычным
окончанием, окончанием во время запуска, sleep/wake, перезапуском наблюдения,
повторными сигналами и ручной остановкой. Каждый сценарий даёт не более одного
старта и ровно одно завершение пригодной записи.

**Acceptance Scenarios**:

1. **Given** несколько источников подтверждают одну встречу, **When** один
   источник исчезает, а другой остаётся активным, **Then** запись продолжается.
2. **Given** все источники встречи завершились, **When** пройдена действующая
   граница окончания, **Then** связанная автоматическая запись останавливается
   ровно один раз и начинается её сохранение.
3. **Given** встреча закончилась, пока захват ещё запускается, **When** запуск
   завершается или отклоняется, **Then** требование остановки не теряется и
   запись не остаётся активной.
4. **Given** встреча закончилась во время сна Mac или разрыва наблюдения,
   **When** наблюдение восстановлено, **Then** GRAF сверяет текущую активность и
   останавливает устаревшую автоматическую запись.
5. **Given** пользователь вручную остановил автоматическую запись, **When** та
   же непрерывная встреча остаётся активной, **Then** GRAF не запускает её снова.
6. **Given** сигналы окончания потеряны, **When** в течение 10 минут нет ни
   одного подтверждения встречи, **Then** запись останавливается и сохраняется
   с понятной причиной.
7. **Given** активна ручная запись, **When** заканчивается обнаруженная встреча,
   **Then** автоматическая логика не останавливает несвязанную ручную запись.

---

### User Story 4 - Запись переживает штатный и аварийный сбой (Priority: P1)

Как пользователь, я хочу после остановки, ошибки или перезапуска GRAF увидеть
максимально сохранённую запись, чтобы встреча не исчезала только из-за
незавершённого служебного файла.

**Why this priority**: Запись, которую нельзя найти или восстановить после
сбоя, равнозначна потерянной встрече.

**Independent Test**: Прервать GRAF после начала захвата, во время записи, при
остановке, при создании файла прослушивания и перед постановкой на отправку.
После запуска каждая папка классифицируется как готовая, восстановленная или
повреждённая и появляется в общем списке.

**Acceptance Scenarios**:

1. **Given** запись собирается начать захват, **When** первый звук может быть
   принят, **Then** уже существует надёжная локальная запись о незавершённой
   встрече, достаточная для последующего поиска и восстановления.
2. **Given** штатная остановка, **When** завершается запись файлов, **Then**
   основная звуковая запись закреплена на диске до постановки на отправку.
3. **Given** ошибка финальной обработки, **When** основной звук пригоден,
   **Then** сохраняется восстановленная запись с честным ограниченным статусом,
   а не удаляется вся встреча.
4. **Given** GRAF завершился аварийно после появления пригодного звука,
   **When** приложение запускается снова, **Then** запись автоматически
   восстанавливается и становится доступна для отправки.
5. **Given** файлы невозможно восстановить до отправляемого состояния,
   **When** запусковая проверка заканчивается, **Then** запись отображается как
   `Запись повреждена`, предлагает существующее удаление и не предлагает
   `Отправить`.
6. **Given** одна и та же незавершённая папка найдена повторно, **When** проверка
   запускается ещё раз, **Then** не создаётся вторая запись или вторая отправка.

---

### User Story 5 - Неотправленная запись видна в общем списке (Priority: P1)

Как пользователь, я хочу видеть запись сразу после остановки в общем списке и
понимать, отправилась ли она, чтобы ошибка сети или сервера не делала встречу
невидимой.

**Why this priority**: Скрытая запись без понятного состояния воспринимается как
потерянная, даже если файлы ещё лежат на Mac.

**Independent Test**: Остановить исправную запись при доступном сервере, без
сети, с временной ошибкой и с постоянной ошибкой. Проверить общий список,
перезапуск, автоматическое восстановление сети, `Отправить` и отсутствие дубля
после успеха.

**Acceptance Scenarios**:

1. **Given** запись остановлена, **When** начинается локальное сохранение,
   **Then** она сразу появляется в общем списке со статусом сохранения.
2. **Given** запись готова локально, **When** отправка выполняется, **Then** в той
   же строке видны статус отправки и доступный процент выполнения.
3. **Given** сеть или сервер временно недоступны, **When** отправка не удалась,
   **Then** запись остаётся в общем списке, ожидает автоматического повтора и
   переживает перезапуск приложения.
4. **Given** исправная запись ожидает отправки или получила ошибку, **When**
   пользователь выбирает `Отправить`, **Then** запускается одна немедленная
   попытка без создания второй записи или второй очереди.
5. **Given** сеть восстановилась, **When** автоматическая отправка завершилась,
   **Then** локальная строка заменяется серверной встречей без видимого дубля.
6. **Given** запись повреждена, **When** открыт её ряд действий, **Then**
   `Отправить` отсутствует, а удаление остаётся доступным.
7. **Given** общий список открыт, **When** есть локальные записи, **Then** они не
   дублируются в отдельной правой панели или боковом меню.

---

### User Story 6 - Серверная зависимость удаляется без поломки клиентов (Priority: P2)

Как владелец продукта, я хочу полностью удалить серверное управление локальным
выбором автозаписи после переходного выпуска, чтобы не поддерживать две
противоречивые модели и не отключить старые клиенты неожиданно.

**Why this priority**: Немедленное удаление серверного ответа ломает прежние
версии клиента; сохранение его навсегда возвращает неоднозначность.

**Independent Test**: Сначала проверить новый клиент против сервера со старым
полем и без сети; затем проверить сервер без поля с новым клиентом. На первом
шаге старый сервер не влияет на решение нового клиента, на втором новый клиент
не делает запросов и не разбирает удалённое поле.

**Acceptance Scenarios**:

1. **Given** сервер ещё публикует устаревшее разрешение, **When** работает новый
   клиент, **Then** решение определяется только локальным трёхпозиционным
   состоянием и общими обязательными ограничениями записи.
2. **Given** совместимый клиент выпущен, **When** начинается серверная очистка,
   **Then** удаляются поле ответа, внутреннее значение, переменные окружения,
   проверки, описание договора и тесты этой зависимости.
3. **Given** серверная очистка завершена, **When** новый клиент определяет
   встречу, **Then** отсутствие удалённого поля не блокирует вопрос, таймер или
   состояние `Всегда`.
4. **Given** сервер продолжает публиковать список поддерживаемых приложений,
   **When** обновляется список, **Then** это не изменяет сохранённые локальные
   состояния существующих приложений, а новые получают `Спрашивать`.

### Edge Cases

- Два проверенных приложения активны одновременно, но активная запись может
  быть только одна; второе решение не создаёт параллельный захват.
- Приложение встречи сменило технический идентификатор или исчезло из списка;
  старое локальное правило не должно примениться к другой цели.
- Список приложений недоступен при первой установке без сети; встроенный
  проверенный базовый список позволяет использовать настройки и определение.
- Пользователь меняет состояние в настройках, пока для того же приложения
  открыт вопрос; уже принятое явное решение не выполняется дважды.
- Разрешение macOS, место на диске или общее разрешение записи исчезает во время
  таймера или запуска; интерфейс не сообщает об успешной записи до фактического
  начала захвата.
- Встреча заканчивается одновременно с нажатием `Записать`; итог может быть
  только одним: запись не началась либо началась и немедленно остановилась.
- GRAF завершается до первого пригодного звука; пустая служебная запись не
  выдаётся за полноценную встречу, но очищается или отмечается правдиво.
- На диске недостаточно места для завершения; доступные данные сохраняются,
  состояние показывается честно, бесконечная отправка не запускается.
- Сервер принял данные, но клиент не получил ответ; повтор использует прежнюю
  личность отправки и не создаёт вторую серверную встречу.
- Серверная встреча появилась в веб-списке раньше завершения локального
  согласования; строки объединяются по устойчивой личности.
- Пользователь нажимает `Отправить` без сети; запись остаётся в очереди и
  показывает понятное ожидание без потери предыдущей ошибки.
- Пользователь удаляет локальную повреждённую запись; удаление не обещает
  удалить то, что уже могло быть принято сервером.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST store exactly one local automatic-recording state for
  every verified application: `always`, `ask` or `never`.
- **FR-002**: A new installation and every newly discovered verified
  application MUST default to `ask`.
- **FR-003**: Stored application states MUST remain available and editable when
  the server or network is unavailable.
- **FR-004**: Settings MUST show the three states as one accessible reversible
  choice for every application and MUST show a mixed bulk value as `Разные`.
- **FR-005**: A bulk choice MUST apply one of the same three states to all
  currently known verified applications and MUST NOT create a fourth global
  state.
- **FR-006**: Settings MUST remove the redundant controls `Разрешить запуск
  записи после таймера` and `Запрашивать запись` because their behavior is fully
  represented by the three states.
- **FR-007**: In `ask`, the prompt MUST show the application name, `Записать`,
  `Не записывать`, `Запомнить выбор` and an eight-second countdown.
- **FR-008**: Countdown expiry MUST attempt the current recording only while the
  same meeting remains active and all mandatory recording gates pass.
- **FR-009**: Countdown expiry MUST NOT persist an application state regardless
  of the remembrance checkbox.
- **FR-010**: `Записать` MUST start only the current recording when remembrance
  is off and MUST persist `always` when remembrance is on.
- **FR-011**: `Не записывать` MUST suppress only the current meeting when
  remembrance is off and MUST persist `never` when remembrance is on.
- **FR-012**: A persisted prompt choice MUST be visible in settings immediately
  and remain reversible.
- **FR-013**: `always` MUST bypass the prompt, while `never` MUST suppress both
  the prompt and automatic recording.
- **FR-014**: Only one terminal outcome MAY be applied to one prompt and one
  continuous meeting candidate.
- **FR-015**: Every automatic start MUST pass approved-target, current-meeting,
  permissions, local storage, suppression, general workspace recording/consent,
  visible-indicator and one-action Stop gates.
- **FR-016**: The local three-state decision MUST NOT require a server
  assisted-auto-start policy, acknowledgement or network connection.
- **FR-017**: One continuous meeting MUST create at most one automatic recording.
- **FR-018**: A meeting MUST remain active while any current trusted source for
  that target remains active and MUST end only after all current sources cross
  the confirmed end boundary.
- **FR-019**: An automatic recording tied to an ended meeting MUST receive one
  durable stop request even when ending races with capture startup.
- **FR-020**: A pending stop request MUST be re-evaluated after startup finishes
  and MUST NOT be discarded because capture was transitioning.
- **FR-021**: After sleep, wake, observer restart or interrupted observation, the
  client MUST reconcile active automatic recording against a fresh current
  meeting state and stop stale capture.
- **FR-022**: A safety stop MUST end detector-started capture after 10 continuous
  minutes without trusted evidence of the associated meeting when a normal end
  event was lost.
- **FR-023**: Manual Stop MUST suppress automatic restart for the same continuous
  meeting, and automatic end MUST NOT stop an unrelated manual recording.
- **FR-024**: Before accepting capturable audio, the client MUST durably identify
  an in-progress local recording so it can be found after a crash.
- **FR-025**: During capture, enough recording data MUST be secured periodically
  to recover a useful artifact after process or device interruption with no
  more than 10 seconds of otherwise accepted audio lost from the tail.
- **FR-026**: Normal stop MUST secure the primary audio before derived playback
  media or upload work can determine the recording outcome.
- **FR-027**: Startup recovery MUST inspect every in-progress local recording,
  rebuild missing derived media when possible, and classify the result exactly
  once as ready, degraded but sendable, or damaged.
- **FR-028**: A useful primary recording MUST NOT be discarded solely because a
  derived file or final description failed to complete.
- **FR-029**: An unrecoverable recording MUST appear in the common list as
  `Запись повреждена`, MUST retain the existing delete action and MUST NOT offer
  `Отправить`.
- **FR-030**: A stopped or recovered sendable recording MUST appear in the
  common meeting list before server upload succeeds.
- **FR-031**: The common list MUST show local lifecycle states for saving,
  sending progress, waiting for automatic retry, send failure and damage.
- **FR-032**: Sendable failures MUST remain in the existing durable upload queue,
  retry automatically after eligible delays or connectivity recovery and
  survive application restart.
- **FR-033**: A sendable local row in waiting or failed state MUST offer the
  action labelled exactly `Отправить`.
- **FR-034**: `Отправить` MUST request one immediate attempt through the existing
  queue and MUST NOT create a duplicate queue item, local row or server meeting.
- **FR-035**: Successful upload MUST reconcile the local row with the server row
  without a visible duplicate or loss of selection.
- **FR-036**: The separate right-side local-custody list MUST be removed after
  all its necessary states and actions are available in the common list.
- **FR-037**: The first rollout step MUST ship a client that ignores the obsolete
  server assisted-auto-start preference while remaining compatible with a
  server that still includes it.
- **FR-038**: Only after the compatible-client step, the server MUST remove the
  assisted-auto-start response field, internal value, environment switches,
  policy checks, contract description and tests that exist solely for this
  local preference.
- **FR-039**: Server cleanup MUST retain the supported-application registry,
  false-target exclusions, registry version/cache validation and metadata-safe
  diagnostics.
- **FR-040**: The client MUST include a verified baseline application registry
  sufficient for first-install automatic-recording settings and detection
  without network access; server registry refresh MAY add or update targets.
- **FR-041**: Diagnostics and committed validation evidence MUST remain
  metadata-only and MUST NOT contain audio, transcript text, meeting content,
  credentials, cookies, tokens, signed URLs or live secret paths.
- **FR-042**: The implementation MUST reuse the existing local writer,
  recording description, recovery path, upload queue and common meeting list;
  it MUST NOT add a second database, queue, upload service or parallel meeting
  list for this feature.

### Key Entities

- **AutomaticRecordingPreference**: Local value `always`, `ask` or `never`,
  stored for one exact verified application identity.
- **PromptDecision**: One current-meeting outcome: explicit start, explicit
  refusal, timeout or cancellation, plus whether an explicit action saved a
  preference.
- **AutomaticRecordingSession**: A capture tied to one continuous meeting
  candidate, including start and durable stop intent.
- **LocalRecordingArtifact**: Durable local identity and files whose lifecycle
  is in progress, ready, degraded but sendable, or damaged.
- **UploadQueueItem**: Existing durable request that owns automatic retries,
  progress, last failure and the manual `Отправить` action.
- **UnifiedMeetingRow**: One common-list projection that represents a local
  recording before upload and reconciles with its server meeting after success.
- **SupportedApplicationRegistry**: Verified application identities and
  false-target exclusions; it supplies eligible targets but does not own user
  preferences.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of the `always` / `ask` / `never`, remembrance and timeout
  combinations produce the specified current-meeting and future-setting outcome
  in the deterministic acceptance matrix.
- **SC-002**: In 100% of clean-install tests, all baseline and newly discovered
  verified applications start as `Спрашивать`, including first launch without
  network access.
- **SC-003**: In the lifecycle matrix covering normal end, end-during-start,
  duplicate events, sleep/wake, observer restart and manual Stop, each
  continuous meeting creates no more than one recording and no automatic
  recording remains active after its confirmed end or bounded safety stop.
- **SC-004**: In forced-interruption checks at every documented capture stage,
  every local folder is visible after restart as sendable or `Запись
  повреждена`; no folder with useful primary audio remains invisible and a
  recoverable recording loses no more than the final 10 seconds.
- **SC-005**: A successfully stopped sendable recording appears in the common
  list before network upload is required in 100% of focused checks.
- **SC-006**: Network loss, application restart and temporary server failure do
  not remove the local row or queue item; automatic retry or `Отправить`
  completes through the same item without duplicates.
- **SC-007**: After successful upload, 100% of focused reconciliation scenarios
  show one meeting row rather than separate local and server duplicates.
- **SC-008**: All interactive states and actions in the settings, prompt and
  common list are reachable by keyboard and announced with their visible
  meaning by VoiceOver; status is never conveyed only by color.
- **SC-009**: The new client passes the same local behavior matrix against a
  server that includes the obsolete field, a server without it and no network;
  only general recording/consent restrictions may change eligibility.
- **SC-010**: Focused capture, recovery, queue, server-contract, accessibility
  and integrated end-to-end checks pass before closeout; the repository fast
  gate passes before PR, and one full gate is required on the exact release
  candidate before release.

## Assumptions

- The current three-state setting is preserved for existing installations;
  missing or ambiguous legacy values become `Спрашивать` and never become
  `Всегда` by inference.
- The eight-second prompt behavior is intentionally retained. There is no
  separate switch that disables timeout start while leaving `Спрашивать`.
- General workspace recording and consent restrictions may still prohibit all
  recording. The server no longer makes the personal per-application choice.
- The supported-application registry remains updateable from the server, but a
  verified baseline copy ships with the client for offline first use.
- The existing local delete action is reused for damaged recordings. No new
  open-folder action is required.
- Existing upload identity and idempotency rules are reused when the server
  outcome is uncertain.
- Release, notarization, deployment and removal of the server field are
  separate gated rollout steps even when implemented in one feature branch.

## Dependencies

- Existing native meeting detector and supported-application registry.
- Existing capture start/stop coordinator and persistent visible indicator.
- Existing local recording writer, recording description and recovery code.
- Existing durable desktop upload queue and authenticated ingest protocol.
- Existing embedded common meeting list and local/server reconciliation bridge.
- Existing delete behavior and metadata-only diagnostics.

## Out Of Scope

- Server-side storage, synchronization or administration of the three local
  per-application states.
- A fourth global automatic-recording state or recording arbitrary system audio.
- Calendar-driven start, browser extension work, bot joining or screen/video
  recording.
- A new local database, replacement upload protocol, second upload queue,
  separate native meeting history or separate damaged-recording page.
- Participant-facing notice design beyond enforcing the existing general
  workspace consent restriction.
- Automatic repair of audio that has no useful recoverable media data.
- Production deployment, public release, notarization or installed-app
  replacement without a separate release approval and release gates.
