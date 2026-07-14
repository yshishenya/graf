# Feature Specification: Calendar Auto Context Match

**Feature Branch**: `098-calendar-auto-context-match`
**Created**: 2026-07-09
**Status**: Draft
**Input**: User description: "После подключения календаря GRAF должен сам матчить запись с календарной встречей по времени записи и брать оттуда название, roster участников и полезный recurring context. Ручная привязка event_id не должна быть основным сценарием."

## Implementation Note

The 090 security closeout tightened the existing manual calendar-context
link/unlink endpoints so a user can only link their own recording to a calendar
event from their own selected calendar source in the same space, and cannot
unlink another user's recording context.

That hotfix only closes the immediate authorization gap. It does not implement
098's intended product behavior: automatic time-based matching for normal
first-party recordings, ambiguity handling, private/all-day exclusions,
recurring context and the rule that manual uploads/offline recovery are not
calendar-matched.

## Product Context

GRAF уже имеет базовую календарную инфраструктуру из feature slices `060-calendar-context-ingestion` и `063-calendar-settings-ui`: пользователь может подключить календарь, выбрать календари, видеть prompt/settings и хранить нормализованные snapshots будущих событий. Но обсуждение показало, что текущая модель слишком легко превращает календарь в ручную привязку события к записи. Это не тот продуктовый сценарий, который нужен meeting assistant.

Правильный сценарий для пользователя:

1. Пользователь подключает календарь.
2. GRAF записывает обычную встречу через first-party recording flow.
3. GRAF сам смотрит на время записи и календарь владельца записи.
4. Если есть ровно одна безопасная и уверенная календарная встреча, запись получает понятное название встречи и roster участников.
5. Если сигнал неоднозначный, приватный или не относится к текущей записи, GRAF ничего не придумывает и не приклеивает неправильный context.
6. Ручной выбор нужен только как correction/ambiguity path, а не как основной путь.

Главная продуктовая цель 098: сделать календарь невидимо полезным в обычных случаях и безопасно молчаливым в рискованных случаях. Пользователь не должен каждый раз думать про `event_id`, вручную связывать запись и встречу или разгребать неверно присвоенные названия.

## Current-State Correction

Эта фича не заменяет `060` и `063`; она уточняет, каким должен быть главный product behavior поверх уже созданных слоев.

- `060` дало read-only календарные подключения, event snapshots, participants, conference-link metadata и задел для context links.
- `063` дало настройки календаря, выбор календарей, prompts, preview и privacy-safe UI вокруг календаря.
- `098` меняет основной пользовательский loop: calendar context должен появляться автоматически для normal first-party recordings, когда это безопасно и однозначно.
- Ручная привязка календарного события остается, но только для случаев выбора пользователем, исправления ошибки или разрешения ambiguity.
- Manual upload и offline recovery специально не включаются в 098, чтобы не делать сомнительный retrospective matching по времени загрузки или поздней синхронизации.

## Reference Product Lessons *(Clean-Room)*

Мы смотрели на публичные материалы Krisp только как на category reference, а не как на дизайн для копирования. Нельзя копировать их UI, copy, assets, icons или proprietary behavior. Полезные category lessons:

- Calendar integration ожидаемо связывает meeting transcript/recording с календарным событием по времени, чтобы дать записи название встречи.
- Calendar context может использовать участников как roster/contact context, но это не равно доказанному присутствию людей на записи.
- Overlapping/back-to-back ситуации опасны: лучше попросить пользователя выбрать, чем автоматически прикрепить неправильную встречу.
- Auto-share и delivery должны быть отдельными политиками; сам факт наличия attendee в календаре не должен давать доступ к записи.
- Speaker identity из календаря/контактов требует отдельной фичи, confidence model и correction UX; для 098 transcript labels остаются `SPEAKER_00`, `SPEAKER_01` и так далее.

## Product Principles For 098

- **No wrong magic**: неправильный calendar match хуже отсутствия match.
- **Time is the anchor**: matching опирается на actual recording time, а не на время upload, processing или review.
- **Owner calendar only**: запись матчится только с календарем владельца записи внутри того же workspace/space.
- **Calendar is context, not permission**: участники календаря не получают доступ, recipients, shares или speaker identity.
- **Stable history**: после match запись не должна неожиданно переименовываться из-за позднего изменения календаря.
- **Manual title wins**: если пользователь дал записи название сам, календарь его не перетирает.
- **Read-only calendar**: GRAF читает календарь, но не меняет события, приглашения, RSVP и не отправляет сообщения.
- **Degrade silently**: если календарь недоступен, stale или ambiguous, запись создается и обрабатывается без calendar context.

## Scenario Decision Matrix

| Scenario | 098 Behavior | Reason |
|----------|--------------|--------|
| Calendar not connected | Do nothing | Нет надежного источника context. |
| One eligible timed event overlaps recording time | Auto-match | Это основной полезный сценарий. |
| Event has participants, no meeting link/location | Auto-match eligible | Участники сами по себе достаточный сигнал, что это встреча. |
| Event has meeting link/location, no participants | Auto-match title only | Есть встреча и название, но roster недоступен. |
| Event has no participants and no meeting link/location | Do not auto-match by default | Слишком слабый сигнал, легко назвать запись бытовым календарным блоком. |
| Private/free-busy event | Do nothing | Нельзя раскрывать скрытое название или участников. |
| All-day event | Ignore completely | All-day события обычно не описывают конкретную запись. |
| Ad-hoc meeting not in calendar | Do nothing | Нет календарного события, которое можно безопасно использовать. |
| Back-to-back boundary | User chooses or no context | На границе легко выбрать соседнюю встречу. |
| Overlapping events | User chooses or no context | Несколько plausible candidates, автоматический выбор небезопасен. |
| Long recording continues into later event | Keep first chosen/matched context | Не переключаем context посреди записи. |
| Calendar event renamed after recording | Do not update recording title | История записи должна быть стабильной. |
| User manually renamed recording | Calendar never overwrites | Ручное название пользователя авторитетнее календаря. |
| Manual media upload | Do not calendar-match | Upload time не равен meeting time; пользовательское имя/имя файла важнее. |
| Offline/delayed upload recovery | Do not calendar-match in 098 | Поздний recovery не должен запускать ненадежный retrospective match. |
| Recurring meeting with previous matched occurrence | Show safe previous context to authorized users | Это полезный continuity case, но только без leakage. |
| Recurring previous occurrence inaccessible/deleted/other space | Do not show previous context | Нет доступа - нет context. |
| Calendar participants | Roster/context only | Attendees не являются permissions, recipients или speaker identities. |
| Multiple workspace/space membership | Match only active recording space | Нельзя смешивать personal и corporate contexts. |

## Clarifications

### Session 2026-07-09

- Decision: Основной сценарий - автоматическое сопоставление записи с календарным событием владельца по времени записи, а не ручная привязка `event_id`.
- Decision: Calendar context принадлежит владельцу записи: кандидаты берутся только из календарей, подключенных этим же пользователем в том же workspace/space.
- Decision: Back-to-back встречи не матчим автоматически; пользователь должен сам выбрать нужное событие или продолжить без календарного контекста.
- Decision: Ad-hoc meeting, которого нет в календаре, оставляем без календарных действий.
- Decision: Private/free-busy события не используем для automatic context, title или roster.
- Decision: Событие без участников, но с meeting link/location, может дать название встречи.
- Decision: Событие с участниками, но без meeting link/location, считается валидной встречей и может дать название плюс roster.
- Decision: All-day events вообще не учитываем для matching.
- Decision: Для recurring meetings нужно поддержать pre-meeting context из прошлой matched встречи той же серии.
- Decision: Если календарное событие переименовали после recording-time match, GRAF не меняет уже созданное название/context записи.
- Decision: Если пользователь вручную поменял название записи, календарь не перетирает это название.
- Decision: Участники календаря - только roster/context: они не получают доступ, shares, delivery и не меняют speaker identity.
- Decision: Маппинг `SPEAKER_00`, `SPEAKER_01` и т.д. на имена из календаря/контактов - будущая отдельная фича, не часть 098.
- Decision: Один пользователь может быть в нескольких spaces; matching не пересекает границы workspace/space.
- Decision: Manual uploads не матчим к календарю вообще.
- Decision: Offline recordings или delayed offline upload recovery не матчим к календарю в этой фиче.
- Decision: Calendar access остается read-only: без calendar mutation, emails/messages, auto-join, auto-record и attendee-based permission grants.

### Session 2026-07-13

- Q: Как показывать причину отсутствия context, если по времени совпало private/free-busy событие? → A: В списке записей показывать общий статус без calendar context; только авторизованный владелец может увидеть в детальном состоянии безопасную metadata-only причину `private/free-busy event skipped`, без названия, roster, описания, ссылок или иных деталей события.
- Decision: Feature `097-workspace-account-onboarding` пропущена по явному указанию пользователя и не является prerequisite для 098; matching использует уже действующие owner/workspace boundaries, а будущая 097 может только уточнить terminology/UX без изменения 098 truth model.
- Decision: Отдельный Codex Security scan не входит в текущий delivery/closeout 098 и будет выполнен пользователем отдельно; обязательные product acceptance checks для authorization, privacy-safe projections, lifecycle и forbidden-content evidence остаются частью реализации, но не выдаются за отдельный security audit.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Автоматическое название и roster при уверенном совпадении (Priority: P1)

Как пользователь, который подключил календарь, я хочу, чтобы обычная запись встречи автоматически получила название календарной встречи и roster участников, чтобы список записей и review были полезными без ручной уборки.

**Why this priority**: Календарная интеграция ценна только тогда, когда продукт сам обогащает записи. Ручной выбор event как основной путь слишком тяжелый и не соответствует ожидаемому поведению meeting assistant.

**Independent Test**: Записать встречу, когда ровно одно selected календарное событие владельца записи уверенно совпадает по времени. Итоговая запись получает безопасное название события и roster context в authorized review.

**Acceptance Scenarios**:

1. **Given** пользователь подключил календарь в текущем workspace и selected timed event с участниками пересекает время начала записи, **When** запись создается обычным recording flow, **Then** запись связывается с этим event, получает safe event title и показывает calendar roster как context.
2. **Given** selected timed event имеет meeting link или location, но не имеет participant list, **When** запись уверенно совпадает с event по времени, **Then** запись может использовать event title и показывает, что roster недоступен.
3. **Given** selected timed event имеет участников, но не имеет meeting link/location, **When** запись уверенно совпадает с event по времени, **Then** запись может использовать event title и roster context так же, как для link-based встречи.
4. **Given** matched event title unsafe для использования, **When** calendar context связан с записью, **Then** запись сохраняет обычное generated/user название и не показывает unsafe event text.
5. **Given** пользователь состоит в нескольких workspaces/spaces, **When** запись создается в одном workspace, **Then** учитываются только календарные события, подключенные владельцем записи в этом же workspace.

---

### User Story 2 - Не матчить, когда сигнал слабый или небезопасный (Priority: P1)

Как privacy-conscious пользователь, я хочу, чтобы GRAF оставлял записи без календарного контекста, когда matching ambiguous, private или outside scope, чтобы продукт не приклеивал неправильное название и не раскрывал чувствительные календарные данные.

**Why this priority**: Неправильный calendar match хуже отсутствия match. Он может неправильно назвать запись, раскрыть private calendar data или запутать review/sharing workflows.

**Independent Test**: Создать записи в ambiguous, private, all-day, ad-hoc, manual upload и offline/delayed сценариях. Система не должна автоматически прикреплять calendar context.

**Acceptance Scenarios**:

1. **Given** два календарных события пересекают recording start time, **When** запись создается, **Then** GRAF не auto-matches ни одно событие и помечает context как ambiguous или unavailable.
2. **Given** одно событие заканчивается ровно когда другое начинается и запись попадает около boundary, **When** GRAF не может выбрать одно событие с high confidence, **Then** пользователь должен выбрать intended event или продолжить без calendar context.
3. **Given** запись - ad-hoc meeting без matching calendar event, **When** запись создается, **Then** GRAF ничего календарного не делает.
4. **Given** единственное time-matching событие private или free/busy-only, **When** запись создается, **Then** GRAF не использует это событие для title, roster или context.
5. **Given** единственное time-matching событие all-day, **When** запись создается, **Then** GRAF полностью игнорирует его.
6. **Given** пользователь вручную загружает media file, **When** upload становится записью, **Then** GRAF не auto-matches calendar context.
7. **Given** запись создана offline или восстановлена позже из offline queue, **When** она загружается позже, **Then** GRAF не делает delayed calendar auto-matching.

---

### User Story 3 - Ручной выбор только для ambiguity и correction (Priority: P2)

Как пользователь, я хочу выбирать календарное событие только когда GRAF не может безопасно определить его сам, чтобы я сохранял контроль без ручной работы для обычных встреч.

**Why this priority**: Manual selection полезен, но должен быть override/ambiguity-resolution path, а не основным механизмом enrichment.

**Independent Test**: Создать запись с несколькими plausible candidates и проверить, что UI/API представляет choice-required state без прикрепления неправильного события.

**Acceptance Scenarios**:

1. **Given** back-to-back или overlapping calendar ситуация дает несколько plausible events, **When** запись создается, **Then** запись остается unlinked и показывает владельцу safe candidate choices.
2. **Given** пользователь выбирает один candidate из ambiguous set, **When** выбор сохраняется, **Then** запись использует safe title и roster context только выбранного event.
3. **Given** пользователь выбирает continue without calendar context, **When** запись потом открывается в review, **Then** calendar title или roster не прикреплены, пока пользователь явно не изменит это.
4. **Given** у записи уже есть calendar context, **When** другое событие начинается позже во время этой записи, **Then** GRAF не переключает context автоматически.

---

### User Story 4 - Стабильное название и context после встречи (Priority: P2)

Как пользователь, я хочу, чтобы названия записей и calendar context оставались стабильными после встречи, чтобы поздние изменения календаря неожиданно не переписывали мою библиотеку.

**Why this priority**: Календарные события часто переименовывают, двигают или редактируют после встречи. История записи должна отражать то, что было известно в момент match, и уважать ручные правки пользователя.

**Independent Test**: Сматчить запись с календарным событием, потом переименовать событие или вручную изменить title записи. Название и context остаются стабильными.

**Acceptance Scenarios**:

1. **Given** запись была matched с event и использовала его title, **When** календарное событие переименовали после записи, **Then** recording title не меняется.
2. **Given** пользователь вручную изменил recording title, **When** later calendar sync или matching запускается, **Then** manual title остается authoritative.
3. **Given** календарное событие удалили или отменили после match, **When** запись открывается в review, **Then** существующий recording context остается стабильным и не удаляется молча, если только пользователь или deletion/retention workflow явно не убрали его.

---

### User Story 5 - Continuity для recurring meetings (Priority: P3)

Как пользователь, который идет на recurring meeting, я хочу перед встречей видеть полезный context из прошлой matched встречи, чтобы быстро вспомнить, что было в прошлый раз.

**Why this priority**: Recurring meetings частые, и calendar context может дать ценность не только через naming. Это должно строиться поверх надежного matching, а не заменять его.

**Independent Test**: Сматчить два occurrence одной recurring series и показать, что более поздний occurrence может показать concise pointer на предыдущую matched запись без private content leak для unauthorized users.

**Acceptance Scenarios**:

1. **Given** recurring calendar series имеет ранее matched запись, **When** следующий occurrence показывается до или во время встречи, **Then** GRAF может показать authorized users safe summary/link на предыдущую matched запись.
2. **Given** предыдущая запись удалена, недоступна или находится в другом workspace, **When** recurring context запрошен, **Then** GRAF не показывает его.
3. **Given** recurring metadata отсутствует или ambiguous, **When** новый occurrence matched, **Then** GRAF нормально обрабатывает текущий event, но не придумывает series continuity.

---

### User Story 6 - Speaker-name suggestions явно отложены (Priority: P3)

Как product owner, я хочу отдельно зафиксировать calendar/contact-based speaker naming, чтобы 098 случайно не переименовал diarization speakers без отдельной identity feature.

**Why this priority**: Calendar attendees - это invited roster, а не доказанные speakers. Speaker identity changes требуют отдельного consent, confidence и correction design.

**Independent Test**: Matched calendar participants появляются только как roster context; transcript speaker labels остаются `SPEAKER_00`, `SPEAKER_01` и так далее.

**Acceptance Scenarios**:

1. **Given** matched calendar event имеет attendees, **When** transcript отображается, **Then** diarization labels остаются `SPEAKER_XX`, пока отдельная speaker-name feature явно не реализована.
2. **Given** product backlog review обсуждает speaker naming, **When** команда планирует работу, **Then** эта тема ведется как отдельная future feature и не принимается как часть 098.

### Edge Cases

- У владельца записи не подключен календарь.
- Календарь подключен в другом workspace/space, чем запись.
- Calendar source принадлежит другому пользователю в том же workspace.
- Один clear selected event пересекает recording start.
- Запись начинается за несколько минут до единственного scheduled event.
- Запись начинается внутри одного event и рядом со стартом второго back-to-back event.
- Запись начинается во время двух overlapping events.
- Запись продолжается намного дольше matched event.
- Event имеет participants, но не имеет meeting link/location.
- Event имеет meeting link/location, но не имеет participants.
- Event не имеет ни participants, ни meeting link/location.
- Event all-day.
- Event private или free/busy-only.
- Event deleted, cancelled, renamed или moved после match time.
- Calendar sync stale или unavailable в момент записи.
- Пользователь вручную меняет recording title до или после match.
- Пользователь вручную загружает media file.
- Запись создана offline или загружена позже из offline recovery queue.
- Пользователь состоит в personal и corporate spaces с разными календарями.
- Calendar participant list truncated, hidden, provider-limited, duplicated или содержит rooms/resources/groups.
- Recurring event instance metadata missing, duplicated или provider-specific.
- Previous recurring recording exists, но deleted, retained-only, inaccessible или in another workspace.
- Evidence, logs и diagnostics не должны содержать raw attendee emails, meeting links with passcodes, event descriptions, provider tokens или private meeting content.

### Primary User Flow: Clear Calendar Match

1. Пользователь заранее подключил календарь и выбрал нужные calendars/settings.
2. Пользователь начинает обычную запись встречи в активном workspace/space.
3. GRAF знает actual recording start time и owner of recording.
4. GRAF ищет eligible timed calendar events только у этого owner и только в этом active workspace/space.
5. GRAF отбрасывает all-day, private, free/busy-only, stale/unsafe и cross-space events.
6. Если остается ровно одно high-confidence событие, GRAF связывает recording с match-time snapshot этого события.
7. Если у записи нет user/manual title, GRAF может использовать safe calendar title как recording title.
8. Authorized review surfaces показывают calendar roster как context.
9. Transcript speaker labels остаются `SPEAKER_00`, `SPEAKER_01`, `SPEAKER_02` и так далее.
10. Участники календаря не получают доступ, не становятся recipients и не получают delivery.

### Primary User Flow: No Calendar Match

1. Пользователь создает запись, но календарь не подключен, событие отсутствует, событие private/free-busy/all-day или сигнал недостаточно сильный.
2. GRAF создает и обрабатывает запись как обычно.
3. Название записи остается generated/user/file-derived according to existing recording title rules.
4. Review показывает отсутствие calendar context без раскрытия названия private/hidden event.
5. Пользователь не видит ошибку там, где это не ошибка продукта: отсутствие context - нормальный fallback.

### Primary User Flow: Ambiguous Calendar Match

1. Пользователь записывает встречу около boundary двух событий или во время overlap.
2. GRAF понимает, что plausible candidates больше одного.
3. GRAF не выбирает event автоматически.
4. Владелец записи может выбрать правильное событие или продолжить без calendar context.
5. До выбора запись не получает calendar title, roster или recurring context.
6. Если пользователь выбирает event, выбранный context становится user-selected и не должен быть silently overwritten later.

### Primary User Flow: Recurring Continuity

1. Пользователь имеет recurring meeting series.
2. Один occurrence уже был safely matched к записи в том же workspace/space.
3. Перед следующим occurrence или в relevant meeting surface GRAF может показать authorized pointer на прошлую matched запись/итоги.
4. GRAF не показывает previous context, если предыдущая запись удалена, недоступна, в другом workspace/space или если текущий пользователь не имеет права ее видеть.
5. Recurring continuity не меняет transcript speaker labels, не создает recipients и не отправляет summaries.

### Trust And Privacy Boundaries

- Calendar title is context, not content proof. Название события может помочь назвать запись, но не доказывает, что именно это обсуждалось.
- Calendar attendees are invited roster, not actual speakers. Их нельзя использовать как speaker truth.
- Calendar attendees are not access control. Нельзя автоматически добавлять их в meeting access, share grants, report recipients, summary recipients или email/message delivery.
- Calendar links can be sensitive. Meeting links, passcodes и raw provider payloads не должны попадать в logs, diagnostics, screenshots, specs или support evidence.
- Private/free-busy means no visible context. Даже если время совпало идеально, GRAF не должен использовать hidden title или participants.
- Workspace/space boundary is hard. Personal calendar context не должен попадать в corporate recording и наоборот.
- Calendar is read-only. Эта фича не пишет в календарь, не двигает события, не меняет RSVP, не отправляет invite updates и не включает auto-join/auto-record.
- Manual upload is user-provided media, not a live calendar recording. Для upload важнее пользовательское имя; если его нет, используется имя файла по правилам upload flow, а не calendar match.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: GRAF MUST автоматически пытаться сопоставить calendar context для normal first-party recordings, когда владелец записи подключил календари в active workspace/space.
- **FR-002**: Calendar matching MUST использовать actual recording time, а не upload request time, processing time или review open time.
- **FR-003**: Calendar matching MUST учитывать только selected, timed, non-private, non-free/busy, non-all-day events из calendar sources, owned by the same user who owns the recording and scoped to the same workspace/space.
- **FR-004**: Calendar matching MUST NOT учитывать events другого пользователя, другого workspace, другого personal space или workspace, где владелец записи больше не имеет valid access.
- **FR-005**: Recording MUST be auto-linked только когда ровно один high-confidence calendar event совпадает по recording time и eligibility rules.
- **FR-006**: Events with participants but no meeting link/location MUST be eligible for automatic matching and roster context.
- **FR-007**: Events with meeting link/location but no participants MUST be eligible for automatic title context, with roster marked unavailable.
- **FR-008**: Events without participants and without meeting link/location SHOULD NOT be auto-matched by default unless a later settings feature explicitly changes this rule.
- **FR-009**: All-day events MUST be ignored completely for automatic calendar context matching.
- **FR-010**: Private and free/busy-only events MUST NOT be used for automatic title, roster или visible event context. Recording list surfaces MUST show only the generic no-calendar-context state; an authorized owner detail surface MAY explain the metadata-only reason `private/free-busy event skipped` without exposing title, roster, description, links или other event details.
- **FR-011**: Manual media uploads MUST NOT be automatically matched to calendar events.
- **FR-012**: Offline recordings and delayed offline upload recovery MUST NOT be automatically matched to calendar events in this feature.
- **FR-013**: Ad-hoc recordings without a matching eligible calendar event MUST remain unchanged.
- **FR-014**: Back-to-back, overlapping или otherwise ambiguous calendar situations MUST require user selection или continue without calendar context; GRAF MUST NOT silently choose one event.
- **FR-015**: Existing explicit calendar-context selection MUST become an override/ambiguity-resolution path, not the primary matching mechanism.
- **FR-016**: When an event is matched, GRAF MUST store enough calendar context to render recording title source, event relationship, roster availability и recurring-series continuity without depending on future calendar event edits.
- **FR-017**: Safe calendar event title MAY become the recording title only when the recording does not already have a user/manual title.
- **FR-018**: User-edited recording titles MUST remain authoritative and MUST NOT be overwritten by calendar sync, automatic matching или explicit calendar context selection.
- **FR-019**: Calendar event renames, moves, deletes или cancellations after match time MUST NOT silently rewrite the recording title or remove the already matched context.
- **FR-020**: Calendar participants MUST be exposed only as roster/context for authorized review surfaces.
- **FR-021**: Calendar participants MUST NOT create meeting access, share grants, report recipients, summary recipients, email recipients или any other delivery side effect.
- **FR-022**: Calendar participants MUST NOT rename transcript or diarization speaker labels in 098; transcript labels remain `SPEAKER_00`, `SPEAKER_01`, etc.
- **FR-023**: Product MUST preserve a future-feature note for calendar/contact-based speaker-name suggestions with explicit consent, confidence, correction и speaker-truth requirements.
- **FR-024**: Recurring meeting context MUST be based on matched occurrences in the same recurring series and same workspace/space.
- **FR-025**: Recurring meeting context MUST show previous-meeting information only to users authorized to see the previous recording.
- **FR-026**: If previous recurring context is unavailable, deleted, ambiguous или inaccessible, GRAF MUST not fabricate or leak previous-meeting information.
- **FR-027**: Calendar matching MUST be idempotent: retries, refreshes, duplicate upload attempts или repeated processing MUST NOT create duplicate active calendar context links.
- **FR-028**: Calendar matching MUST be safe under stale calendar sync: if event snapshot set is unavailable или too stale to make a high-confidence decision, GRAF MUST leave the recording unchanged или require user choice.
- **FR-029**: Audit and diagnostics MUST record metadata-only outcomes for matched, not matched, ambiguous, skipped-private, skipped-all-day, skipped-manual-upload, skipped-offline, skipped-stale-calendar, user-selected, declined-by-user и cleared-by-user states.
- **FR-030**: Logs, diagnostics, specs, screenshots, test evidence и support payloads MUST NOT contain provider tokens, app passwords, raw event descriptions, meeting links with passcodes, raw attendee email dumps, raw calendar payloads, transcript text или private meeting content.
- **FR-031**: Calendar matching MUST remain read-only with respect to external calendars: no event mutation, no calendar writes, no invite changes, no messages и no auto-join.
- **FR-032**: Calendar matching MUST NOT block recording creation, upload, processing, playback или review; failures degrade to no calendar context.
- **FR-033**: UI surfaces MUST clearly distinguish auto-matched context, user-selected context, ambiguous context и no calendar context without exposing unsafe private event content; a private/free-busy skip reason is restricted to an authorized owner detail surface and MUST remain generic in recording lists.
- **FR-034**: Feature MUST preserve brand-distance и clean-room rules: public reference products can inform category expectations, but GRAF must not copy proprietary UI, copy, assets или private behavior.
- **FR-035**: GRAF MUST keep the source of the recording title distinguishable: user/manual title, calendar title, generated title, upload-provided title или file-name-derived title.
- **FR-036**: Calendar title MUST NOT replace upload-provided title or file-name-derived title for manual uploads, because manual uploads are out of calendar matching scope.
- **FR-037**: When calendar context is ambiguous, user-facing surfaces MUST avoid showing private/unsafe candidate details until the owner is authorized to choose among safe candidates.
- **FR-038**: User-selected calendar context MUST be treated as an explicit correction and MUST NOT be overwritten by a later automatic match.
- **FR-039**: If a user clears calendar context from a recording, GRAF MUST respect that choice and MUST NOT immediately reattach the same context automatically.
- **FR-040**: Calendar matching MUST treat participants/rooms/resources/groups as roster metadata with clear semantics that they may be invited entities, not confirmed attendees.
- **FR-041**: Calendar context MUST NOT affect retention/deletion promises except by registering any created context artifacts in the normal lifecycle/deletion accounting.
- **FR-042**: Calendar match decisions MUST be explainable to authorized owners in plain product language such as matched automatically, needs choice, skipped private event, no matching event, calendar unavailable, manual upload skipped, or offline recording skipped.
- **FR-043**: Calendar context shown in the recording list MUST be concise and non-blocking; users must not need to open a separate calendar-linking workflow for normal clear matches.
- **FR-044**: Calendar context shown in review MUST separate meeting metadata from transcript content so roster context is not confused with diarization output.
- **FR-045**: Recurring previous-meeting context MUST be optional context for preparation/review and MUST NOT change the current recording title, roster или speaker labels by itself.
- **FR-046**: Calendar matching MUST avoid using event descriptions as primary matching evidence or visible context in 098, because descriptions often contain sensitive links and notes.
- **FR-047**: If selected calendars contain duplicate provider events representing the same meeting, GRAF MUST avoid creating duplicate active context links and MUST present only one effective choice when possible.
- **FR-048**: Calendar matching behavior MUST be consistent between web cabinet and desktop/app surfaces: the same recording should not appear matched in one surface and unmatched in another.
- **FR-049**: The product MUST preserve existing recording creation and processing behavior for users who never connect a calendar.
- **FR-050**: The feature MUST provide enough product evidence for release review to prove safe behavior across clear match, no match, ambiguous match, private/free-busy, all-day, manual upload, offline recording, multi-space and recurring cases.
- **FR-051**: An explicit recording-start choice to continue without calendar context MUST persist as `declined_by_user`, distinct from `cleared_by_user`, which is reserved for removing context from an already created meeting. Both states MUST prevent later automatic attachment until the owner explicitly selects context.
- **FR-052**: Every recording-start match attempt MUST set `expires_at` to exactly 24 hours after its server `evaluated_at`; an unconsumed attempt at or after that instant MUST NOT be consumed and MUST be eligible for bounded purge.

### Key Entities *(include if feature involves data)*

- **Recording**: User-owned audio/video record created by first-party recording flows. It has recording-time metadata and may receive calendar context.
- **Calendar Source**: Read-only connected calendar account owned by a user inside a workspace/space.
- **Calendar Event Snapshot**: Normalized event data available to GRAF at match time: schedule, safe title state, meeting link/location summary, privacy state, participants/roster metadata и recurrence identifiers.
- **Calendar Context Match**: Product decision that a recording corresponds to one calendar event, including confidence, reason, title source, roster source и match-time snapshot boundaries.
- **Ambiguous Calendar Context**: State where more than one plausible event exists or signal is too weak, requiring user selection или no context.
- **Calendar Roster**: Context from organizer/attendees/resources/rooms/groups. It is not proof of attendance and not a permission list.
- **Recurring Meeting Context**: Safe relationship between matched occurrences of the same recurring series, used to surface previous-meeting context to authorized users.
- **Future Speaker-Name Suggestion**: Deferred feature candidate that may suggest mapping speakers to people using calendar/contact context, but is not part of 098.
- **Title Source**: Product state explaining why a recording has its visible name: user/manual title, safe calendar title, generated date/title, upload-provided title или file-name-derived title.
- **No Calendar Context State**: Explicit product outcome when matching was skipped, unavailable, private, all-day, stale, manual-upload, offline, cross-space или not found.
- **User Calendar Choice**: Explicit owner action that selects a candidate event, declines calendar context at recording start, or later clears context from an existing recording. Start-time decline and later clear are distinct durable states.

## Out of Scope *(mandatory)*

- Реализация feature в этом specify step.
- Calendar matching для manual media upload.
- Calendar matching для offline/delayed upload.
- Retrospective scanning старых записей для calendar context.
- Calendar writes, calendar event mutation, invite updates, RSVP updates, auto-join, auto-record или message sending.
- Auto-sharing recordings, transcripts, summaries, reports или links с calendar attendees.
- Granting meeting access based on calendar attendees.
- Renaming transcript/diarization speakers from calendar attendees или contacts.
- Full CRM enrichment, company directory sync, SSO directory sync или external contact identity resolution.
- Multi-event timeline context для одной длинной записи, которая spans several meetings.
- Moving recordings between workspaces/spaces based on calendar data.
- Copying UI, copy, assets, icons или proprietary flows from reference products.

## Dependencies *(mandatory)*

- `060-calendar-context-ingestion` for connected calendar sources, normalized event snapshots, participant normalization, conference-link metadata и current context link storage.
- `063-calendar-settings-ui` for selected calendars, event category preferences, prompt settings и privacy-safe calendar settings copy.
- Existing recording metadata from desktop first-party recording flows, especially recording start/end times and active workspace/space.
- Existing meeting title source behavior from `059-recording-date-title`.
- Existing cabinet review access decisions, share grants и no-attendee-access boundaries.
- Existing deletion, retention, audit и diagnostics product gates.
- Existing workspace membership and active-workspace boundaries are sufficient for 098. A future `097-workspace-account-onboarding` slice may refine personal/corporate terminology and onboarding UX, but 098 MUST NOT depend on 097 implementation or weaken its same-owner/same-workspace rule.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In tests with one eligible matching event, 100% of normal first-party recordings receive safe calendar title when no user/manual title exists.
- **SC-002**: In tests with one eligible matching event with participants, 100% of authorized review responses expose roster context without raw attendee email dumps.
- **SC-003**: In overlap and back-to-back tests, 0 recordings are auto-linked to an arbitrary event; each requires user choice или remains without calendar context.
- **SC-004**: In private/free-busy/all-day/manual-upload/offline-upload tests, 0 recordings receive automatic calendar context.
- **SC-005**: In multi-workspace tests, 0 recordings are matched with calendar events from another user или another workspace/space.
- **SC-006**: In event-rename tests, 0 already matched recording titles change because calendar event was renamed after match time.
- **SC-007**: In manual-title tests, 0 user-edited recording titles are overwritten by calendar matching или sync.
- **SC-008**: In attendee tests, 0 calendar attendees receive access, share grants, message delivery, summary delivery, report delivery или speaker-name assignment.
- **SC-009**: In recurring-series tests, previous-meeting context is shown only when previous recording is matched, authorized и in the same workspace/space.
- **SC-010**: Calendar match failure, stale sync, provider downtime или ambiguity never blocks recording creation, upload, processing, playback или review.
- **SC-011**: Feature authorization/privacy acceptance tests and evidence-hygiene checks find 0 provider tokens, app passwords, raw event descriptions, meeting links with passcodes, raw attendee dumps, transcript text, raw audio или private meeting content. A standalone Codex Security scan is explicitly deferred to a separate run and MUST NOT be claimed as completed by 098 closeout.
- **SC-012**: In normal first-party recording smoke tests, web cabinet and desktop/app surfaces show the same calendar context state for the same recording.
- **SC-013**: In ambiguous matching tests, 100% of recordings remain unlinked until a user explicitly selects a safe candidate or chooses no calendar context.
- **SC-014**: In user-correction tests, 100% of user-selected, start-time-declined or later-cleared calendar context decisions survive later sync/retry without automatic reversal, and decline is never reported as clear.
- **SC-015**: In no-calendar-user tests, users who never connect a calendar experience no new blocking steps, prompts or errors during recording creation and review.
- **SC-016**: In release review, all required scenario evidence is captured without storing raw meeting content, raw event descriptions, raw attendee email dumps, raw meeting links or provider credentials.
- **SC-017**: Across at least 100 warmed synthetic evaluations with four selected sources and 50 candidate rows, recording-start resolve completes in `<= 200 ms` p95 and atomic attempt consumption completes in `<= 50 ms` p95.

## Assumptions

- "Normal first-party recording" means a recording created through the desktop/app recording flow while the user is authenticated and app/server have enough current calendar context to decide safely.
- Manual upload is any user-selected media file uploaded through cabinet/app upload workflow rather than a first-party recording session.
- Offline/delayed upload means the recording could not be associated with current calendar state at recording time because app/server was offline, unauthenticated или recovering from a delayed queue.
- The pre-start candidate grace is exactly five minutes. A recording at or after an event end and at or before five minutes after that end sees the event only as a boundary blocker; these thresholds never override ambiguity/back-to-back safety.
- Calendar event snapshots are treated as match-time evidence. Later provider changes are not automatically applied to matched recordings.
- Calendar roster means invited/known calendar participants, not confirmed attendees and not diarized speakers.

## Completed Planning Decisions

- `$speckit-clarify` fixed the confidence language and user-facing states without reopening the settled product decisions.
- `$speckit-plan` fixed the five-minute timing rules and 24-hour calendar-freshness threshold; any resulting ambiguity remains non-automatic.
- `$speckit-plan` mapped reuse of the 060/063 calendar concepts without expanding into auto-share, speaker naming or retrospective matching.
- `$speckit-checklist` covers every 2026-07-09 decision: back-to-back choice, ad-hoc no-op, private/free-busy no-op, all-day ignored, manual upload skipped, offline skipped, stable renamed events, manual title protection, roster-only participants and recurring continuity.
- `$speckit-tasks` separates clear match, ambiguity, privacy/no-op, recurring continuity, UI consistency and release evidence into independently validated work.
- `$speckit-analyze` reconciled existing calendar-link behavior, upload naming, workspace/space ownership, review authorization and deletion/retention accounting before implementation.

## Release Review Evidence Expected Later

- Scenario matrix evidence for clear match, no match, ambiguous match, back-to-back, overlap, private/free-busy, all-day, participants-without-link, link-without-participants, no-link-no-participants, manual upload, offline/delayed upload and recurring continuity.
- Privacy evidence showing calendar attendees did not become permissions, recipients, shares or speaker names.
- Stability evidence showing calendar event rename/delete/cancel after match does not silently rewrite recording title/context.
- Multi-space evidence showing personal/corporate/workspace boundaries are preserved.
- UI evidence showing web cabinet and desktop/app surfaces present the same state without forcing users into manual event selection for clear matches.
- Diagnostics evidence showing safe metadata-only reasons without provider tokens, raw event descriptions, meeting passcodes, raw attendee dumps, transcript text or audio.
