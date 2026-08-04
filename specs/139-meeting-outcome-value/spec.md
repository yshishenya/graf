# Feature Specification: Проверяемая ценность итогов встречи

**Feature Branch**: `codex/139-meeting-outcome-value`

**Created**: 2026-08-04

**Status**: Draft

**Input**: Пользовательский запрос: внимательно продумать весь путь от записи и
расшифровки до полезного результата; проверить промпты, логику, UX, UI, IA и CX,
сравнить с Krisp и похожими продуктами и довести опыт до уровня Krisp или лучше,
не усложняя и не перегружая интерфейс.

## Product Outcome

В течение первых 30 секунд на странице завершённой встречи человек должен
понять: что произошло, что решено и что делать дальше. Любой существенный вывод
должен проверяться по расшифровке, а отсутствие факта, ответственного или срока
не должно маскироваться догадкой модели.

Krisp, Granola, Fathom, Otter, Fireflies, tl;dv, Zoom и Teams используются только
как clean-room ориентиры пользовательских задач. GRAF сохраняет собственную
русскую IA, визуальный язык, privacy-first sharing, локально видимый capture и
недеструктивную модель кандидатов.

## User Scenarios & Testing

### User Story 1 - Сильные итоги готовятся без ручного запуска (Priority: P1)

Как владелец завершённой встречи, я хочу, чтобы после появления пригодной
расшифровки GRAF сам начал готовить качественный вариант итогов, чтобы мне не
приходилось сначала находить формат и нажимать «Обновить итоги».

**Why this priority**: Сейчас первым результатом становится быстрый
детерминированный черновик, а качественный модельный вариант появляется только
после ручного запроса. Это разрывает путь до основной ценности.

**Independent Test**: Завершить обработку синтетической встречи с доступной
расшифровкой и проверить, что ровно один вариант «Авто» начинает готовиться без
дополнительного действия, восстанавливается после reload и не заменяет текущие
итоги без решения владельца.

**Acceptance Scenarios**:

1. **Given** первая пригодная расшифровка встречи стала доступна, **When**
   обработка завершается, **Then** GRAF создаёт не более одного качественного
   варианта «Авто» по рабочему шаблону пространства.
2. **Given** быстрые итоги уже доступны, **When** качественный вариант ещё
   готовится, **Then** быстрые итоги и расшифровка остаются доступны, а UI
   показывает одно спокойное состояние без требования повторно запустить работу.
3. **Given** качественный вариант готов, **When** владелец возвращается на
   встречу с другого устройства или после reload, **Then** он видит готовый
   вариант и может использовать либо отклонить его.
4. **Given** модельный вариант готов или не удался, **Then** текущий принятый
   результат не меняется автоматически и не теряется.

### User Story 2 - Итог отвечает на рабочие вопросы, а не пересказывает начало (Priority: P1)

Как участник встречи, я хочу увидеть краткий смысл, решения и следующие
действия, чтобы не читать приветствие, повестку и дословный пересказ разговора.

**Why this priority**: Пользовательская ценность определяется правильным
отбором и формулировкой результата, а не количеством заполненных секций.

**Independent Test**: Запустить кандидаты на синтетических встречах разных
типов и проверить, что общая структура остаётся компактной, а содержание
соответствует назначению выбранного формата.

**Acceptance Scenarios**:

1. **Given** встреча содержит приветствие, повестку, обсуждение и итог, **When**
   готовится «Авто», **Then** «Кратко» описывает итог встречи, а не первую
   реплику и не список тем без результата.
2. **Given** участники обсуждают предложение, но не принимают его, **When**
   формируется раздел «Решения», **Then** предложение не становится решением.
3. **Given** участники выражают пожелание или идею без обязательства, **When**
   формируется раздел «Действия», **Then** идея не становится назначенной
   задачей.
4. **Given** явное решение или действие позже отменено либо исправлено, **When**
   формируется результат, **Then** используется финальная поддержанная версия с
   контекстом исправления.
5. **Given** выбран специальный формат, **Then** он меняет приоритеты и состав
   содержания, но не ослабляет правила доказательности и неизвестных данных.

### User Story 3 - Каждый вывод можно быстро проверить (Priority: P1)

Как владелец или разрешённый читатель, я хочу перейти от вывода к точному месту
расшифровки, чтобы понять контекст и заметить ошибку до использования или share.

**Why this priority**: Проверяемость создаёт больше доверия, чем общий AI-
disclaimer, и является clean-room преимуществом GRAF над продуктами, где связь
summary с источником не систематична.

**Independent Test**: Проверить каждый пункт готового результата и candidate-
preview на наличие подтверждающего источника, переход к правильному времени и
отсутствие содержимого при заблокированном доступе.

**Acceptance Scenarios**:

1. **Given** доступный пункт итога, **Then** у него есть хотя бы одна ссылка на
   подтверждающий фрагмент текущей закреплённой расшифровки.
2. **Given** ссылка на источник, **When** пользователь активирует её, **Then**
   GRAF открывает расшифровку в контексте этого фрагмента и переводит player к
   соответствующему моменту.
3. **Given** одного фрагмента недостаточно из-за исправления или разнесённого
   контекста, **Then** пункт может ссылаться на несколько совместно
   подтверждающих фрагментов.
4. **Given** источник изменился, устарел или недоступен, **Then** кандидат нельзя
   принять или показать как текущую подтверждённую версию.

### User Story 4 - Действия и решения не выдумываются (Priority: P1)

Как участник встречи, я хочу видеть только подтверждённые договорённости с
ответственным и сроком лишь тогда, когда они действительно прозвучали, чтобы
не получить ложные обязательства.

**Independent Test**: Прогнать контрастные синтетические сценарии с явными,
неявными, отменёнными и отсутствующими actions/owners/due dates и проверить
каждое поле отдельно.

**Acceptance Scenarios**:

1. **Given** действие явно согласовано, **Then** оно появляется один раз и
   сохраняет смысл обязательства.
2. **Given** ответственный или срок явно не подтверждён, **Then** соответствующее
   поле отсутствует без placeholder и догадки.
3. **Given** говорящий использует «я», **Then** имя может появиться только при
   надёжной привязке реплики к подтверждённому участнику; иначе поле остаётся
   неизвестным.
4. **Given** относительный срок «к пятнице», **Then** он сохраняется как сказано
   и не превращается в календарную дату без закреплённых даты и timezone.
5. **Given** встреча не содержит решений или действий, **Then** раздел получает
   честное пустое состояние, а не общую формулировку для заполнения места.

### User Story 5 - Новый вариант удобно сравнить и принять (Priority: P1)

Как владелец встречи, я хочу просмотреть новый вариант в понятной структуре,
чтобы принять его одним осознанным действием и не потерять текущие итоги.

**Independent Test**: Открыть готовый candidate на desktop и 390 CSS px,
проверить русские названия, приоритет «Кратко → Действия → Решения», owner/due,
источник и явные действия «Оставить текущие»/«Использовать».

**Acceptance Scenarios**:

1. **Given** кандидат готов, **Then** preview использует человеческие русские
   названия категорий и не показывает внутренние keys или технический JSON.
2. **Given** в кандидате есть действие, **Then** preview показывает текст,
   сохранённые owner/due и способ проверить источник до принятия.
3. **Given** кандидат содержит вторичные разделы, **Then** они не вытесняют
   «Кратко», «Действия» и «Решения» с первого экрана.
4. **Given** пользователь выбирает «Использовать», **Then** новый вариант
   становится текущим атомарно; предыдущий остаётся в недеструктивной истории.
5. **Given** пользователь выбирает «Оставить текущие» или кандидат завершается
   ошибкой, **Then** текущие итоги остаются без изменений.

### User Story 6 - Сбой одного этапа не скрывает остальную ценность (Priority: P2)

Как пользователь, я хочу понимать, готова ли расшифровка, быстрые итоги или
качественный вариант, чтобы ожидание AI не выглядело как потеря встречи.

**Independent Test**: Проверить processing, unavailable, partial, invalid,
timeout, stale, expired и provider-failure состояния при доступной расшифровке и
при её отсутствии.

**Acceptance Scenarios**:

1. **Given** расшифровка готова, а качественный вариант задерживается, **Then**
   расшифровка и быстрые итоги остаются доступны.
2. **Given** модель вернула отказ, незавершённый или семантически неверный
   результат, **Then** он не становится доступным кандидатом.
3. **Given** повторный безопасный запуск поддерживается, **Then** UI предлагает
   одно понятное действие; при неоднозначном provider outcome GRAF не повторяет
   inference и не реконструирует результат догадкой.
4. **Given** встреча слишком короткая, без распознаваемой речи или источник
   неполон, **Then** GRAF объясняет это без fake summary и лишних уведомлений.

### User Story 7 - Share и export распространяют только осознанный результат (Priority: P2)

Как владелец, я хочу сначала проверить AI-текст, а затем явно выбрать аудиторию
и состав материалов, чтобы автоматическая генерация не стала автоматической
утечкой или рассылкой ошибки.

**Independent Test**: При активном кандидате проверить owner, viewer,
summary-only share и export: непринимаемый кандидат не раскрывается читателю и
не заменяет принятый результат в выгрузке.

**Acceptance Scenarios**:

1. **Given** качественный кандидат ещё не принят, **Then** viewer, share и export
   получают только текущую принятую версию.
2. **Given** владелец открывает Share или export, **Then** текущие access и
   privacy границы сохраняются и не появляется новый permissive default.
3. **Given** AI-текст готов к распространению, **Then** UI напоминает проверить
   содержимое без повторяющегося предупреждения у каждого пункта.

### User Story 8 - Результат остаётся понятным на каждом разрешённом входе (Priority: P1)

Как владелец или разрешённый читатель, я хочу видеть одинаково понятный статус
и структуру итогов из списка, detail и summary-only share, чтобы путь не
заканчивался техническим JSON, ложным «Готово» или неработающим источником.

**Independent Test**: Открыть owner, full-viewer и summary-only сценарии из
списка и по прямой ссылке; проверить artifact status, русскую IA, доступность
source destination и keyboard-focus после перехода.

**Acceptance Scenarios**:

1. **Given** расшифровка готова, а качественный вариант ещё формируется,
   **Then** список и detail различают готовность расшифровки и итогов и не
   называют весь результат просто «Готово».
2. **Given** разрешён только summary-only доступ, **When** человек открывает
   встречу из списка или по ссылке, **Then** он получает продуктовую HTML-
   страницу с той же локализованной read-only IA, а не JSON и не внутренние
   category keys.
3. **Given** источник нельзя открыть из-за отсутствия доступной расшифровки или
   playback, **Then** UI не обещает интерактивный переход и показывает bounded
   неинтерактивное основание.
4. **Given** источник доступен, **When** keyboard-пользователь активирует его,
   **Then** открывается расшифровка, player переходит к моменту, соответствующий
   фрагмент получает focus и изменение объявляется assistive technology.
5. **Given** итог ещё processing, blocked или unavailable, **Then** первичная
   область показывает одно общее truthful состояние вместо трёх одинаковых
   сообщений в «Кратко», «Действия» и «Решения».

## Edge Cases

- Короткая встреча, тишина, недоступная или частичная расшифровка.
- Очень длинная встреча у границы контекста модели и у действующего ограничения
  размера; никакого скрытого обрезания.
- Важный факт находится в начале, середине или конце длинной встречи.
- Смешанная русско-английская речь, имена, числа, валюты и относительные даты.
- Несколько похожих действий, повторение одного обязательства и смена
  ответственного или срока.
- Предложение → возражение → финальное решение в удалённых друг от друга
  фрагментах.
- Реплика «я сделаю» при подтверждённом, неподтверждённом и неизвестном
  говорящем.
- Косвенная prompt injection, fake system/XML/JSON schema, ссылка, base64 или
  просьба раскрыть prompt внутри расшифровки.
- Invalid JSON, schema mismatch, пустые source references, provider refusal,
  premature stop, timeout до egress и неоднозначный egress.
- Prompt-control, LiteLLM, Langfuse или Temporal временно недоступны.
- Reload, второй tab/устройство, повторный dispatch и повторный import одного
  результата.
- Расшифровка изменилась, встреча удаляется или доступ владельца отозван во
  время генерации или принятия.
- Кандидат истёк, отклонён или содержит только `not_found`/`not_inferable`.
- Web и embedded surface показывают один и тот же разрешённый результат; mobile
  viewport не создаёт горизонтальный overflow.

## Requirements

### Functional Requirements

- **FR-001**: Первая пригодная расшифровка MUST инициировать не более одного
  policy-owned качественного варианта «Авто» без ручного запроса пользователя,
  когда AI generation разрешена конфигурацией и политикой.
- **FR-002**: Автоматический вариант MUST использовать закреплённый текущий
  processing result, выбранный default template и его точную versioned prompt/
  config policy; повторный dispatch MUST reuse ту же durable identity.
- **FR-003**: Автоматическая генерация MUST NOT менять принятый outcome pointer;
  публикация качественного варианта требует явного решения владельца.
- **FR-004**: Быстрые итоги, расшифровка и playback MUST оставаться доступными
  независимо от состояния качественного кандидата, если их собственные access,
  lifecycle и readiness gates пройдены.
- **FR-005**: Prompt policy MUST определять назначение каждой категории и
  различать финальное решение, предложение, вопрос, риск, follow-up и
  обязательство.
- **FR-006**: Prompt policy MUST приоритизировать конечную ценность встречи,
  исключать приветствия, filler, служебные фразы и повторения и сохранять
  компактность в соответствии с detail level.
- **FR-007**: Каждый доступный outcome item MUST содержать минимум один точный
  source reference из закреплённой расшифровки; пустые или посторонние refs MUST
  отклонять весь candidate до его показа как готового.
- **FR-008**: Decision, action, owner и due date MUST появляться только при
  полном подтверждении указанными source references; критические поля не могут
  компенсироваться aggregate quality score.
- **FR-009**: Owner и due date MUST быть допустимы только для action items; при
  недостаточном подтверждении они MUST оставаться отсутствующими.
- **FR-010**: Candidate generation MUST treat transcript and custom-template
  content as untrusted data and MUST ignore embedded instructions, role changes,
  schemas, links and secret/prompt disclosure requests.
- **FR-011**: Исправления и противоречия в расшифровке MUST разрешаться в пользу
  последней явно поддержанной позиции; при невозможности выбрать результат
  MUST быть опущен или отмечен как невыводимый.
- **FR-012**: Candidate preview MUST использовать локализованные пользовательские
  названия и порядок «Кратко → Действия → Решения → дополнительные разделы»,
  показывать сохранённые owner/due и доступный путь к источнику.
- **FR-013**: Candidate preview MUST сохранять current accepted outcome до
  решения владельца и давать ровно два смысловых исхода: оставить текущий или
  использовать новый; состояния ошибки не должны уничтожать текущий результат.
- **FR-014**: Owner-only candidate content MUST NOT попадать в viewer/share/
  export responses до принятия; существующие authorization, deletion и
  privacy-first sharing gates MUST сохраняться.
- **FR-015**: Refusal, incomplete output, invalid schema, invalid semantic
  result, stale source, oversize input и ambiguous provider outcome MUST иметь
  разные truthful machine states и не публиковаться как доступный outcome.
- **FR-016**: Eval contract MUST измерять отдельно factual precision, source
  attribution, must-unit coverage, action detection, owner/due slots, unknown
  restraint, category states, injection resistance и long-context position.
- **FR-017**: Любая неподтверждённая decision/action/owner/due, неверная source
  attribution или успешная prompt injection MUST быть hard failure независимо
  от полноты, языка или среднего score.
- **FR-018**: Prompt/model/schema/outcome-logic change MUST проходить versioned
  synthetic regression и private held-out gate; judge changes требуют
  human-labelled calibration и operator approval до promotion.
- **FR-019**: Committed evidence MUST оставаться metadata-only: versions,
  hashes, fixture IDs, counts, metrics и bounded error codes без transcript,
  outcome text или свободного judge feedback.
- **FR-020**: Web, embedded, full-viewer и summary-only review MUST сохранять
  одинаковые разрешённые artifact states, локализованную read-only IA, content
  authorization, candidate decisions, keyboard behavior и responsive usability
  на 390 CSS px; summary-only browser entry MUST NOT возвращать JSON.
- **FR-021**: Реализация MUST reuse существующие outcome candidate, prompt
  snapshot, Temporal dispatch, review, player, access, share и export модели и
  MUST NOT добавлять новый AI service, task hub, chat panel или UI framework.
- **FR-022**: Capture, MediaScribe, retained plaintext observability, deletion
  disclosure и system-audio-first границы MUST оставаться без изменений.
- **FR-023**: Source reference MUST быть интерактивной только при существующем
  разрешённом transcript/playback destination; успешный переход MUST
  переключать вкладку, seek player и переносить keyboard focus к точному
  transcript segment без раскрытия недоступного содержимого.
- **FR-024**: Processing, blocked, failed и unavailable summary MUST
  отображаться одним локализованным aggregate state, а не повторяться в каждой
  первичной категории.
- **FR-025**: Meeting-list status MUST различать readiness расшифровки и
  принятых итогов; неизвестное, blocked или failed состояние MUST NOT попадать
  в optimistic fallback «Готово».
- **FR-026**: Heading outline, timeline controls, candidate actions и source
  controls MUST быть семантичными, keyboard-operable и иметь различимый focus;
  disabled действия не должны объясняться только через `title`.

### Key Entities

- **Accepted outcome revision**: текущая разрешённая пользователям версия
  итогов, которая меняется только после явного принятия владельцем.
- **Automatic outcome candidate**: один качественный вариант для первой
  пригодной расшифровки, закреплённый за source revision, default template,
  prompt/config snapshot и durable generation identity.
- **Outcome item**: атомарный вывод одной категории с текстом, состоянием,
  обязательными source references и опциональными owner/due только для action.
- **Prompt policy version**: неизменяемая версия инструкций, model settings и
  закрытой response schema, прошедшая quality gates до production promotion.
- **Synthetic eval fixture**: clean-room meeting scenario с атомарными gold
  units, action slots, источниками, запрещёнными claims и ожидаемым runtime
  state; реальные встречи в committed evidence не используются.
- **Eval run manifest**: закреплённые dataset/scorer/prompt/schema/model/judge/
  code versions и метрики, необходимые для сравнения кандидата с baseline.

## Success Criteria

### Measurable Outcomes

- **SC-001**: В 100% синтетических first-transcript сценариев создаётся ровно
  один automatic quality candidate либо одно truthful policy/dependency state;
  ручной запуск до первой ценности не требуется.
- **SC-002**: В restart, reload, duplicate-dispatch и second-device сценариях
  выполняется не более одного publishable provider call для одной durable
  identity, а accepted outcome никогда не меняется автоматически.
- **SC-003**: Не менее 9 из 10 русскоязычных evaluators за 30 секунд правильно
  называют итог, решения и следующие действия на ready desktop/mobile review.
- **SC-004**: 100% доступных synthetic outcome items имеют минимум один
  существующий точный source reference; для decisions/actions/owners/due нет ни
  одной неподтверждённой или неверно атрибутированной выдачи в release gate.
- **SC-005**: На private held-out action precision не ниже 98%, recall не ниже
  90%, owner/due precision и unknown restraint равны 100%; must-unit recall
  равен 100%, weighted coverage не ниже 90%.
- **SC-006**: Ни одна adversarial fixture не меняет инструкции, output schema,
  source IDs или disclosure policy; injection attack success равен 0.
- **SC-007**: Для одинакового supported fact/action в начале, середине и конце
  long-context fixtures нет critical error, а разрыв coverage не превышает 5
  процентных пунктов; oversize не обрезается скрыто.
- **SC-008**: Candidate preview содержит 0 внутренних category keys и 0
  fabricated owner/due, не создаёт horizontal overflow на 390 CSS px и
  позволяет проверить источник до принятия.
- **SC-009**: Viewer/share/export получают только accepted outcome в 100%
  candidate-state сценариев; deletion/access race раскрывает 0 meeting content.
- **SC-010**: Focused automated checks, synthetic prompt regression, browser UX
  evidence, forbidden-content scan и выбранный repository validation lane
  проходят до предложения implementation commit; release/deploy остаются
  отдельным явно подтверждённым gate.
- **SC-011**: В owner/full-viewer/summary-only матрице нет JSON dead-end,
  внутренних category keys, ложного общего «Готово» или интерактивного source
  без destination; keyboard source jump оставляет focus на целевом фрагменте.
- **SC-012**: Processing, blocked, failed, no-summary и no-player состояния
  проходят desktop и 390 CSS px runtime-check без повторного шума,
  горизонтального overflow и английских внутренних reason codes.

## Assumptions

- Feature 138 остаётся канонической компактной IA готовых итогов; Feature 139
  меняет путь получения и проверки ценности, а не возвращает восемь равновесных
  карточек или отдельный workspace.
- Первый automatic candidate использует текущий default template; format change
  и refresh после него остаются явными действиями владельца.
- Fast deterministic outcome остаётся безопасной временной ценностью и fallback,
  пока качественный candidate готовится; он не объявляется эквивалентом AI-
  анализа.
- Точное human-name owner extraction возможно только из подтверждённой speaker
  identity. Generic или неподтверждённые speaker labels не превращаются в имена.
- Относительные даты не нормализуются без закреплённого meeting date/timezone
  input contract.
- Eval thresholds являются стартовыми release gates и уточняются только после
  human-calibrated baseline, без ослабления critical hard failures.
- Текущие Langfuse, LiteLLM, Temporal и retained Generation Call границы
  переиспользуются; их plaintext retention policy не меняется.

## Out of Scope

- Новый capture engine, bot, camera/video, direct desktop-to-MediaScribe path,
  audio routing или изменение локального one-action Stop.
- AI chat, общий cross-meeting task hub, CRM/project-management integrations,
  completion checkboxes и one-way task sync.
- Автоматический share, permissive public-link default или рассылка непроверенного
  кандидата.
- Редактирование raw transcript, полноценный collaborative notes editor и
  ручной diff/merge произвольного текста.
- Cross-meeting transcript search и переработка всей meeting-list navigation;
  feature исправляет только artifact readiness и разрешённый summary entry.
- Скрытое chunking/truncation длинной встречи без отдельного утверждённого
  correctness contract.
- Изменение Langfuse/Temporal/Generation Call retention, redaction, encryption
  или deletion promises.
- Копирование layout, copy, colors, icons, assets или interaction choreography
  Krisp и других продуктов.
