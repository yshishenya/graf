# Feature Specification: Повторная обработка записи пользователем

**Feature Branch**: `codex/213-user-reprocess`

**Created**: 2026-08-30

**Status**: Ready for implementation

**Input**: Дать владельцу записи простой штатный способ повторно подготовить расшифровку, спикеров и итоги из обычной страницы встречи. Административный раздел, операторские роли, причины запуска и отдельный операторский аудит не нужны.

## Clarifications

### Session 2026-08-30

- Q: Нужна ли административная часть? → A: Нет; действие находится в обычной встрече и доступно владельцу записи.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Повторно обработать готовую запись (Priority: P1)

Владелец открывает готовую встречу, выбирает в меню `Ещё` действие `Повторно обработать запись` и подтверждает запуск. GRAF объясняет, что исходное аудио и текущая версия не изменятся, пока новая полностью не готова.

**Why this priority**: Если расшифровка или спикеры получились плохо, пользователь не должен обращаться к администратору или ждать ручного запуска Temporal.

**Independent Test**: Открыть готовую запись владельца, запустить повторную обработку и убедиться, что создана одна новая попытка, текущий результат остаётся доступным, а двойное нажатие не создаёт дубль и повторное списание.

**Acceptance Scenarios**:

1. **Given** у владельца есть готовая запись и исходное аудио доступно, **When** он выбирает `Повторно обработать запись`, **Then** GRAF показывает подтверждение с кнопками `Отмена` и `Запустить повторную обработку`.
2. **Given** пользователь подтвердил запуск, **When** команда принята, **Then** GRAF создаёт не более одной новой попытки для текущей версии аудио и сообщает, что прежний результат остаётся доступным.
3. **Given** команда повторно отправлена из-за двойного клика, обновления страницы, двух вкладок или сетевого повтора, **When** GRAF принимает повтор, **Then** возвращается активная попытка без второго внешнего задания и списания лимита.
4. **Given** пользователь не является владельцем записи, **When** он изменяет запрос или пытается вызвать действие напрямую, **Then** повторная обработка не запускается и существующие правила доступа не раскрывают чужую запись.
5. **Given** запись ещё не имеет опубликованной расшифровки, удаляется или исходное аудио недоступно, **When** пользователь открывает меню, **Then** действие не предлагается, а существующий путь восстановления остаётся основным.

---

### User Story 2 - Пользоваться текущей версией до готовности новой (Priority: P1)

Во время повторной обработки владелец и получатели общего доступа продолжают читать текущую расшифровку, видеть спикеров, проигрывать запись и использовать экспорт. Ненавязчивое сообщение объясняет, что готовится обновлённая версия.

**Why this priority**: Исправление качества не должно временно ломать уже рабочую запись.

**Independent Test**: На стадиях запуска, обработки, временного сбоя, частичного результата, окончательной ошибки и успешной публикации проверить встречу, общий доступ, экспорт и синхронизацию клиента.

**Acceptance Scenarios**:

1. **Given** повторная обработка выполняется, **When** открывается встреча, **Then** прежняя опубликованная версия остаётся доступной, а GRAF показывает `Готовим обновлённую версию. Текущая остаётся доступной.`
2. **Given** новая попытка получила только текст без готового разделения на спикеров, **When** открывается любой пользовательский канал, **Then** неполная версия нигде не заменяет опубликованную.
3. **Given** новая расшифровка и разделение на спикеров полностью готовы, **When** GRAF публикует результат, **Then** все пользовательские каналы начинают использовать одну и ту же новую версию без смешивания старых и новых данных.
4. **Given** новая расшифровка опубликована, а новые итоги ещё готовятся, **When** пользователь открывает итоги, **Then** прежние итоги остаются доступны с пометкой `По предыдущей версии расшифровки`.
5. **Given** новые итоги готовы, **When** они публикуются, **Then** пометка исчезает и показывается согласованный новый набор итогов.
6. **Given** новая попытка завершилась ошибкой, **When** пользователь продолжает работу, **Then** прежняя расшифровка, спикеры, итоги и проигрывание не исчезают.

---

### User Story 3 - Понимать состояние и восстановить попытку (Priority: P1)

Владелец видит правдивое состояние повторной обработки на странице встречи. При временном сбое GRAF показывает время следующей попытки и обратный отсчёт, а кнопка `Повторить сейчас` позволяет не ждать. Ручное действие сбрасывает старый таймер и не создаёт параллельную работу.

**Why this priority**: Пользователь всегда должен понимать, что происходит и что можно сделать дальше.

**Independent Test**: Провести попытку через выполнение, ожидание внешнего результата, временный сбой, ручной повтор, автоматическое восстановление и окончательную ошибку; проверить тексты, действия и отсутствие дублей.

**Acceptance Scenarios**:

1. **Given** повторная обработка выполняется, **When** владелец открывает встречу, **Then** он видит фактический этап и время последнего обновления без выдуманного процента или обещания срока.
2. **Given** известен надёжный момент следующей автоматической попытки, **When** возникает временный сбой, **Then** GRAF показывает время, спокойный обратный отсчёт и кнопку `Повторить сейчас`.
3. **Given** владелец нажимает `Повторить сейчас`, **When** сервер принимает действие, **Then** старый таймер сбрасывается, восстанавливается та же попытка и не создаётся новое внешнее задание.
4. **Given** попытка уже возобновилась автоматически или из другой вкладки, **When** приходит ручной повтор, **Then** GRAF возвращает актуальное выполняющееся состояние без параллельного запуска.
5. **Given** точное время следующей попытки неизвестно, **When** отображается состояние, **Then** GRAF не показывает ложный отсчёт и предлагает `Проверить статус`.
6. **Given** новая попытка завершилась окончательной ошибкой, **When** владелец открывает встречу, **Then** он видит, что текущая версия сохранена, и может снова выбрать `Повторно обработать запись`.
7. **Given** используется клавиатура или программа чтения с экрана, **When** меняется отсчёт, **Then** каждую секунду не создаётся голосовое объявление, а важное изменение состояния объявляется один раз.

### Edge Cases

- Запись удалена во время обработки: кандидат не публикуется, удаление остаётся приоритетным.
- После запуска появилась новая версия исходного аудио: старая попытка не может заменить относящийся к ней результат.
- Ответ о запуске потерян: повтор возвращает ту же активную попытку.
- MediaScribe принял запрос, но GRAF не получил ответ: GRAF сначала сверяет состояние и не создаёт второе задание вслепую.
- В новой попытке нет распознаваемой речи, нет готового разделения на спикеров или результат не проходит проверку полноты: кандидат не публикуется.
- Браузерная вкладка была приостановлена или системное время изменилось: отсчёт восстанавливается по серверному времени и не запускает обработку сам.
- Сеанс истёк между открытием подтверждения и запуском: действие не выполняется до повторной авторизации.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: GRAF MUST show `Повторно обработать запись` in the ordinary meeting `Ещё` menu only to the recording owner when a published result and eligible source audio exist.
- **FR-002**: Every start, status and manual-retry request MUST revalidate the authenticated recording owner; shared recipients and unrelated workspace users MUST NOT invoke the action.
- **FR-003**: The confirmation MUST state that GRAF will prepare a new transcript, speaker attribution and outcomes, the current version remains available until replacement, and source audio is unchanged.
- **FR-004**: The user MUST NOT have to choose or enter a reason for reprocessing.
- **FR-005**: Repeated delivery and concurrent launch of the same user intent MUST resolve to one active attempt without duplicate provider work or quota charge.
- **FR-006**: A later launch after a terminal attempt MUST create a new durable attempt while preserving prior processing history.
- **FR-007**: Starting an attempt MUST NOT change the published transcript, diarization, speaker attribution, outcomes, playback, export, sharing or desktop synchronization result.
- **FR-008**: GRAF MUST select the published processing version independently from the newest operational attempt.
- **FR-009**: A candidate MUST remain non-public until its transcript and matching diarization are complete, valid and tied to the unchanged source revision.
- **FR-010**: Publication MUST be atomic for every customer-facing projection and fail safely on deletion, source revision change, supersession or stale candidate.
- **FR-011**: Any failure before publication MUST leave the previously published processing version unchanged and usable.
- **FR-012**: The published outcomes version MUST remain independent from the published transcript/diarization version.
- **FR-013**: After transcript publication and before matching outcomes are ready, prior outcomes MUST remain visible with `По предыдущей версии расшифровки`.
- **FR-014**: Matching outcomes MUST replace prior outcomes as one published set; outcome failure MUST NOT hide the newly published transcript.
- **FR-015**: During replacement processing, the meeting MUST show `Готовим обновлённую версию. Текущая остаётся доступной.` without blocking normal use.
- **FR-016**: The owner status MUST expose actual stage and freshness without fabricated percentages, queue estimates or completion promises.
- **FR-017**: When a reliable next-attempt time exists, the owner status MUST show that time, a countdown and `Повторить сейчас`; manual retry MUST invalidate the prior countdown and MUST NOT create parallel work.
- **FR-018**: When no reliable next-attempt time exists, GRAF MUST avoid an exact countdown and offer `Проверить статус`.
- **FR-019**: Terminal failure MUST stop retry presentation, preserve the current version and offer a valid new reprocessing action.
- **FR-020**: Countdown updates MUST NOT announce every second to assistive technology; status transitions and actions MUST remain keyboard and screen-reader accessible.
- **FR-021**: Status, publication selection and retry generation MUST survive page refresh, delayed duplicate delivery and worker restart; the browser timer MUST only display server state.
- **FR-022**: Existing initial-processing recovery MUST remain unchanged; manual status checks and retries MUST NOT create a new reprocessing attempt.

### Key Entities

- **Published processing version**: The complete transcript, diarization and speaker-attribution result currently used by all customer-facing channels.
- **Replacement attempt**: One durable execution tied to the owner, meeting and fixed source revision; it produces at most one candidate version.
- **Candidate processing version**: A non-public result eligible for publication only after completeness and lineage checks.
- **Published outcomes version**: The outcomes set currently shown to users and tied to the processing version from which it was generated.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In moderated acceptance, at least 95% of recording owners can find and start reprocessing on the first attempt in under 45 seconds without technical instructions.
- **SC-002**: In 100% of creation, processing, retry, partial-result, terminal-failure and replacement checks, the last published transcript, speakers, playback, export, sharing and desktop result remain available until one complete replacement is published.
- **SC-003**: Across double-click, browser retry, lost response and two-tab concurrency, exactly one active attempt and no duplicate provider job or quota charge are created.
- **SC-004**: Across stale source revision, deletion and concurrent publication, 0 stale or partial candidates become customer-visible.
- **SC-005**: When a reliable retry time exists, its time and manual action appear within 5 seconds of the transient state; when it does not exist, 0 tested screens show a fabricated countdown.
- **SC-006**: In 100% of accessibility checks, launch and retry work by keyboard, status changes are perceivable and the countdown does not cause per-second screen-reader announcements.
- **SC-007**: After restart at each defined stage boundary, the owner sees the same durable attempt and published versions without duplicate work.
- **SC-008**: Between transcript publication and matching outcome publication, 100% of prior-outcome views carry the previous-version label.

## Assumptions

- The action is available only to the authenticated owner of an already published recording; shared recipients cannot start it.
- Existing authentication, meeting ownership, source-audio custody, quota reservation, deletion fencing, MediaScribe integration and automatic retry rules are reused.
- Reprocessing the same source revision does not consume the user's processing quota a second time.
- Partial transcript text remains internal until matching diarization is ready.
- Outcomes may complete after transcript publication without blocking the transcript.
- The interface uses only durable server-provided retry times.

## Out of Scope

- Any administrative page, operator role, mandatory reason, free-form comment or separate operator audit.
- Comparing versions, manual publication, rollback UI or a version-history browser.
- Provider-job cancellation.
- Changing capture, upload, transcoding, MediaScribe, GigaAM, pyannote or post-processing algorithms.
- Redesigning deletion or initial-processing recovery.
- Native macOS controls; the existing embedded meeting page receives the same responsive web flow.
- Commit, pull request, release and production deployment until implementation and validation are complete and separately approved.
