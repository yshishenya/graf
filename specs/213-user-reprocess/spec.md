# Feature Specification: Повторная обработка записи пользователем

**Feature Branch**: `codex/213-user-reprocess`

**Created**: 2026-08-30

**Status**: Ready for implementation

**Input**: Дать владельцу записи простой штатный способ повторно подготовить расшифровку, спикеров и итоги из обычной страницы встречи. Административный раздел, операторские роли, причины запуска и отдельный операторский аудит не нужны.

## Clarifications

### Session 2026-08-30

- Q: Нужна ли административная часть? → A: Нет; действие находится в обычной встрече и доступно владельцу записи.

### Session 2026-09-02

- Q: Нужно ли переносить ручные имена спикеров в новую версию? → A: Нет; перед запуском нужно предупредить, а сбросить имена только после успешной публикации.
- Q: Что показывать владельцу во время повторной обработки? → A: Скрыть текущую версию и оставить один нейтральный индикатор `Готовим новую версию` без промежуточных статусов и ручных проверок.
- Q: Что делать при окончательной ошибке? → A: Вернуть прежнюю версию с ручными именами и предложить `Попробовать снова`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Повторно обработать готовую запись (Priority: P1)

Владелец открывает готовую встречу, выбирает в меню `Ещё` действие `Повторно обработать запись` и подтверждает подготовку новой версии. GRAF коротко предупреждает, что вручную заданные имена спикеров будут сброшены только после успешной обработки.

**Why this priority**: Если расшифровка или спикеры получились плохо, пользователь не должен обращаться к администратору или ждать ручного запуска Temporal.

**Independent Test**: Открыть готовую запись владельца, запустить повторную обработку и убедиться, что создана одна новая попытка, показана предупреждающая формулировка о ручных именах, а двойное нажатие не создаёт дубль и повторное списание.

**Acceptance Scenarios**:

1. **Given** у владельца есть готовая запись и исходное аудио доступно, **When** он выбирает `Повторно обработать запись`, **Then** GRAF показывает подтверждение `Подготовить новую версию?`, предупреждение о сбросе вручную заданных имён после успеха и кнопки `Отмена` и `Подготовить`.
2. **Given** пользователь подтвердил запуск, **When** команда принята, **Then** GRAF создаёт не более одной новой попытки для текущей версии аудио и скрывает прежнюю версию на странице владельца.
3. **Given** команда повторно отправлена из-за двойного клика, обновления страницы, двух вкладок или сетевого повтора, **When** GRAF принимает повтор, **Then** возвращается активная попытка без второго внешнего задания и списания лимита.
4. **Given** пользователь не является владельцем записи, **When** он изменяет запрос или пытается вызвать действие напрямую, **Then** повторная обработка не запускается и существующие правила доступа не раскрывают чужую запись.
5. **Given** запись ещё не имеет опубликованной расшифровки, удаляется или исходное аудио недоступно, **When** пользователь открывает меню, **Then** действие не предлагается, а существующий путь восстановления остаётся основным.

---

### User Story 2 - Дождаться новой версии без лишних состояний (Priority: P1)

Во время повторной обработки страница владельца скрывает прежние итоги, расшифровку и плеер и показывает один нейтральный индикатор. Опубликованный результат при этом сохраняется на сервере, остаётся доступен получателям общего доступа и не заменяется частичным кандидатом.

**Why this priority**: Исправление качества не должно временно ломать уже рабочую запись.

**Independent Test**: На стадиях запуска, штатного ожидания, автоматического повтора, частичного результата, окончательной ошибки и успешной публикации проверить страницу владельца, общий доступ, экспорт и синхронизацию клиента.

**Acceptance Scenarios**:

1. **Given** повторная обработка выполняется, **When** владелец открывает встречу, **Then** вкладки с прежней версией и плеер скрыты, а GRAF показывает только `Готовим новую версию`.
2. **Given** новая попытка получила только текст без готового разделения на спикеров, **When** открывается любой пользовательский канал, **Then** неполная версия нигде не заменяет опубликованную.
3. **Given** новая расшифровка и разделение на спикеров полностью готовы, **When** GRAF публикует результат, **Then** расшифровка и плеер на странице владельца заменяются в одном обновлении и используют имена новой версии без смешивания старых и новых данных.
4. **Given** новая расшифровка опубликована, а новые итоги ещё готовятся, **When** пользователь открывает итоги, **Then** прежние итоги остаются доступны с пометкой `По предыдущей версии расшифровки`.
5. **Given** новые итоги готовы, **When** они публикуются, **Then** пометка исчезает и показывается согласованный новый набор итогов.
6. **Given** новая попытка завершилась окончательной ошибкой, **When** владелец остаётся на странице или открывает её снова, **Then** прежняя расшифровка, ручные имена спикеров, итоги и проигрывание возвращаются.

---

### User Story 3 - Понимать состояние и восстановить попытку (Priority: P1)

Владелец видит только полезные состояния повторной обработки. Штатное ожидание провайдера, автоматические повторы и кратковременная невозможность обновить статус остаются под единым нейтральным индикатором. Отдельная ошибка появляется только после окончательного завершения попытки.

**Why this priority**: Пользователь всегда должен понимать, что происходит и что можно сделать дальше.

**Independent Test**: Провести попытку через выполнение, ожидание внешнего результата, автоматическое восстановление и окончательную ошибку; проверить единый текст ожидания, возврат прежней версии и отсутствие дублей.

**Acceptance Scenarios**:

1. **Given** повторная обработка выполняется штатно, **When** меняется внутренний этап или наступает автоматический повтор, **Then** владелец продолжает видеть только `Готовим новую версию` без процента, этапа, таймера и ручной проверки.
2. **Given** провайдер ещё не подготовил результат, **When** GRAF получает штатный `result_not_ready`, **Then** интерфейс не называет это ошибкой и не меняет нейтральный индикатор.
3. **Given** запрос статуса временно не удался, **When** сама попытка не завершена окончательно, **Then** GRAF продолжает автоматические проверки без тревожного сообщения и без возврата старой версии.
4. **Given** новая попытка завершилась окончательной ошибкой, **When** владелец открывает встречу, **Then** он видит `Не удалось подготовить новую версию`, прежнюю версию и кнопку `Попробовать снова`.
5. **Given** владелец выбирает `Попробовать снова`, **When** он повторно подтверждает подготовку, **Then** создаётся одна новая попытка без параллельного запуска.
6. **Given** используется клавиатура или программа чтения с экрана, **When** начинается обработка или появляется окончательная ошибка, **Then** важное изменение состояния объявляется один раз и доступные действия остаются управляемыми с клавиатуры.

### Edge Cases

- Запись удалена во время обработки: кандидат не публикуется, удаление остаётся приоритетным.
- После запуска появилась новая версия исходного аудио: старая попытка не может заменить относящийся к ней результат.
- Ответ о запуске потерян: повтор возвращает ту же активную попытку.
- MediaScribe принял запрос, но GRAF не получил ответ: GRAF сначала сверяет состояние и не создаёт второе задание вслепую.
- В новой попытке нет распознаваемой речи, нет готового разделения на спикеров или результат не проходит проверку полноты: кандидат не публикуется.
- Браузерная вкладка была приостановлена или потеряла сеть: после возвращения она продолжает автоматические проверки и не показывает промежуточную ошибку как окончательную.
- Сеанс истёк между открытием подтверждения и запуском: действие не выполняется до повторной авторизации.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: GRAF MUST show `Повторно обработать запись` in the ordinary meeting `Ещё` menu only to the recording owner when a published result and eligible source audio exist.
- **FR-002**: Every start, status and manual-retry request MUST revalidate the authenticated recording owner; shared recipients and unrelated workspace users MUST NOT invoke the action.
- **FR-003**: The confirmation MUST use the title `Подготовить новую версию?`, warn that manually assigned speaker names reset only after successful processing, and provide `Отмена` and `Подготовить` actions without additional explanatory copy.
- **FR-004**: The user MUST NOT have to choose or enter a reason for reprocessing.
- **FR-005**: Repeated delivery and concurrent launch of the same user intent MUST resolve to one active attempt without duplicate provider work or quota charge.
- **FR-006**: A later launch after a terminal attempt MUST create a new durable attempt while preserving prior processing history.
- **FR-007**: Starting an attempt MUST NOT change the published transcript, diarization, speaker attribution, outcomes, playback, export, sharing or desktop synchronization result.
- **FR-008**: GRAF MUST select the published processing version independently from the newest operational attempt.
- **FR-009**: A candidate MUST remain non-public until its transcript and matching diarization are complete, valid and tied to the unchanged source revision.
- **FR-010**: Publication MUST be atomic for every customer-facing projection and fail safely on deletion, source revision change, supersession or stale candidate.
- **FR-011**: Any failure before publication MUST leave the previously published processing version unchanged and usable.
- **FR-011a**: Manually assigned speaker names MUST NOT be reconciled or copied to a replacement result; they MUST remain attached to the previous result and therefore reappear if the replacement fails.
- **FR-012**: The published outcomes version MUST remain independent from the published transcript/diarization version.
- **FR-013**: After transcript publication and before matching outcomes are ready, prior outcomes MUST remain visible with `По предыдущей версии расшифровки`.
- **FR-014**: Matching outcomes MUST replace prior outcomes as one published set; outcome failure MUST NOT hide the newly published transcript.
- **FR-015**: During replacement processing, the owner meeting page MUST hide the published outcomes, transcript, speaker UI and player and show only `Готовим новую версию`; the server MUST retain the published result until replacement succeeds.
- **FR-016**: Internal stages, `result_not_ready`, automatic retry timing and status-fetch failures MUST NOT replace the neutral replacement indicator while the attempt remains non-terminal.
- **FR-017**: Replacement processing MUST NOT expose countdowns, `Повторить сейчас`, `Проверить статус`, stage details or freshness timestamps to the owner.
- **FR-018**: Terminal replacement failure MUST restore the previous outcomes, transcript, speaker names and player and show `Не удалось подготовить новую версию`, `Текущая версия не изменилась.` and `Попробовать снова`.
- **FR-019**: `Попробовать снова` MUST route through the same owner-authorized, coalesced reprocessing admission and warning without creating parallel work.
- **FR-020**: Replacement start, successful publication and terminal failure MUST be announced once to assistive technology; hidden published content MUST be removed from keyboard and screen-reader navigation until success or restoration.
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
- **SC-002**: In 100% of active, waiting, retryable and status-fetch-failure checks, the owner detail shows one neutral replacement indicator and exposes none of the previous outcomes, transcript, speaker controls or player; shared recipients and server-side result selection retain the last complete result.
- **SC-003**: Across double-click, browser retry, lost response and two-tab concurrency, exactly one active attempt and no duplicate provider job or quota charge are created.
- **SC-004**: Across stale source revision, deletion and concurrent publication, 0 stale or partial candidates become customer-visible.
- **SC-005**: In 100% of `result_not_ready`, automatic-retry and temporary status-fetch-failure checks, 0 owner screens show `Временная ошибка`, a countdown, a manual status action or a recovery card distinct from the neutral indicator.
- **SC-006**: In 100% of accessibility checks, confirmation and retry work by keyboard, hidden content is not reachable, and start, success and terminal failure are announced once.
- **SC-007**: After restart at each defined stage boundary, the owner sees the same durable attempt and published versions without duplicate work.
- **SC-008**: Between transcript publication and matching outcome publication, 100% of prior-outcome views carry the previous-version label.

## Assumptions

- The action is available only to the authenticated owner of an already published recording; shared recipients cannot start it.
- Existing authentication, meeting ownership, source-audio custody, quota reservation, deletion fencing, MediaScribe integration and automatic retry rules are reused.
- Reprocessing the same source revision does not consume the user's processing quota a second time.
- Partial transcript text remains internal until matching diarization is ready.
- Outcomes may complete after transcript publication without blocking the transcript.
- A shared recipient who cannot launch reprocessing continues to receive the last complete published result until a complete replacement exists.

## Out of Scope

- Any administrative page, operator role, mandatory reason, free-form comment or separate operator audit.
- Comparing versions, manual publication, rollback UI or a version-history browser.
- Automatic speaker-name matching, migration or reconciliation between processing results.
- Provider-job cancellation.
- Changing capture, upload, transcoding, MediaScribe, GigaAM, pyannote or post-processing algorithms.
- Redesigning deletion or initial-processing recovery.
- Native macOS controls; the existing embedded meeting page receives the same responsive web flow.
- Commit, pull request, release and production deployment until implementation and validation are complete and separately approved.

## Legacy Impact

Classification: `untouched`

Изменение использует существующие attempt/result, recovery и playback-пути;
новые legacy runtime, совместимые обходы и зависимости не добавляются.
