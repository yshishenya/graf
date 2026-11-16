# T119 Round240 — common AppMain calendar owner: bounded source review

## Итог текущего снимка

**SOURCE APPROVED, C0/H0/M0/L0. Исторический H1 закрыт повторной проверкой исправления.**
Это независимая проверка исходного кода конкретного owner-среза, не полная
приёмка T119, не installed/runtime acceptance и не подтверждение итогового
Windows test run. Нативный tray entrypoint остаётся известной незавершённой
частью T119; он не объявляется реализованным и не оформляется новым finding.

Canonical workdir:
`/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`.
Заявленные пользователем branch `codex/200-windows-followup`, HEAD
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`; Git не запускался, нового
независимого Git HEAD receipt нет. Dirty work сохранён. Выбранный high-risk
product lane не снижен ограниченным характером этой проверки.

Лично полностью прочитаны `code-reviewer/SKILL.md` и
`ponytail-review/SKILL.md`. Проверены actual owner methods, их admission,
auth/lifecycle/closing/update/Record callers и members в AppMain; Presenter
pending/failure/expiry flow; RecordingNoticePresenter actionPending root;
Host `calendarJoinCurrent`; новые NativeSettingsBridge и RecordingIndicator
регрессии. Дополнительно прочитаны текущие state/fence и launcher зависимости
для проверки matching-drain semantics, без повторного полного их аудита.
Новые Model.h/.cpp изменения рассмотрены только как исправление H1.
Принятые operation/wire/launcher requirements18/0 и действующий plan T119
использованы как граница, без новых требований, схем или checklist markers.

## История: H1 в первом source снимке

Начальный hash receipt: **2026-10-05 19:02:34 UTC**.
AppMain.cpp: `0d4b714c7fcecd7dfbcd18ed63602c77c7ef4e505ae35a7e350db38c886f5d09`.
MeetingReminderPresenter.cpp:
`b3dc5b40ab92fb35fe28d3838cbaaabb14eca14a5b0f5ceb5ca076dfbb23e529`.

**H1 — Record после handoff терял original native event/action current fence.**
В launch-success ветви `completeAction(intent->target, intent->action, ...)`
вызывался перед `recordCapture()`. `completeAction()` через
`retirePresented()` помечал event dismissed и удалял presented/pending action.
Следующий Record predicate проверял account/auth/interaction, model epoch и
исходный monotonic expiry, но больше не проверял исходный target.

Конкретная последовательность: успешный handoff → retire native card →
`recordCapture()` → readiness/indicator UI work → same-epoch calendar update,
удаляющий event либо заменяющий meetingUrl → повторный Record predicate всё
ещё true → capture start. `MeetingReminderModel::update()` заменяет events
без увеличения epoch; один epoch поэтому не доказывает исходную event identity.
Нарушение: plan T1191237–1239/1253–1255 и принятый owner CHK002/007 требуют
отдельный fresh current/prerequisites перед Record. Это был source blocker,
а не требование нового UX, tracker issue или installed доказательства.

Независимо прослежена цепочка `completeAction` → `retirePresented` → dismissed,
`recordCapture` повторные guards и `ensureRecordingIndicator` native UI calls.
Main отдельно сообщил тот же root gap. Динамический сценарий reviewer не
воспроизводил: по запрету пользователя tests/VM/build не запускались.
Минимальная рекомендация: сохранить exact original target проверку до
последнего Record guard; не ослаблять обычный `revalidate()` для dismissed
Join и не считать завершённую карточку повторной launch authority.

## H1 closure — новые actual bytes

Повторный SHA-256 receipt **2026-10-05 19:11:11 UTC** совпал со снимком,
прочитанным после исправления. Все десять файлов ниже принадлежат этому
ограниченному source review; paths относительны canonical workdir.

| Файл | SHA-256 |
| --- | --- |
| apps/windows/RecApp/AppMain.cpp | `8fd082dd4cb08948a8d6fcb78ad7c549baf8f67954999ec544f905a697078eb5` |
| apps/windows/RecApp/Shell/MeetingReminderPresenter.h | `e2efad868e4af47a53692256116d986dc9a80f6adc106c4eb7c49d8421b9d4c2` |
| apps/windows/RecApp/Shell/MeetingReminderPresenter.cpp | `ea0fa2e8f0e30de1bbbd13f917d8ee5513593a51d649f37f53df68ed13a089d0` |
| apps/windows/RecApp/Shell/RecordingNoticePresenter.h | `6170e7095838aa4d5da3224361ee3ca251a0559c05f8f2daa362b392434c1ba0` |
| apps/windows/RecApp/Shell/RecordingNoticePresenter.cpp | `40cb56dcf74913089609c4724f291b860289a18390547720ae695e4fc25985a7` |
| apps/windows/RecApp/Web/WebView2Host.h | `bed52a1dad53a13850564fce040158c5479a6c04b4334766a03f34f6aa27eb0c` |
| apps/windows/Tests/GrafWindowsContractTests/NativeSettingsBridgeTests.cpp | `2f1ec2d0a40cb7a9011b3e07d4ec8e385fa199975532895abd70fe4f6febf45e` |
| apps/windows/Tests/GrafWindowsPackageTests/RecordingIndicatorTests.cpp | `00f1bdb384fc07ec27b99bc75a2fdf5684f96c41ca2ee96f8df0e0aba36f56b1` |
| apps/windows/RecApp/Shell/MeetingReminderModel.h | `c47f2441f8dde806ecba10cbcff1ad0dd09d70e1379e3b29f73e62862f4668f6` |
| apps/windows/RecApp/Shell/MeetingReminderModel.cpp | `089f0811a98a76f394a6779c876d2594c58b87478185bb848096c9a5336c92b4` |

H1 **CLOSED** по следующей actual source цепочке:

- AppMain.cpp3912–3918: после known `CalendarLauncherOutcome::launched`,
  matching child drain, `finish(handedOff)` и успешного `completeAction` ветвь
  joinAndRecord захватывает original `intent->target`. Каждый существующий
  `recordCapture` guard теперь вызывает `handoffRecordingCurrent(target, ...)`
  вместе с fresh auth/interaction и original immutable expiry.
- AppMain.cpp3288–3301: этот predicate проверяется до readiness, после readiness
  и после `ensureRecordingIndicator()` непосредственно перед capture path.
  Обычный manual Record с default empty predicate не изменён.
- Presenter.cpp204–206: observation требует отсутствие presented/pending action,
  видимой карточки/auto prompt, включённые reminders и отсутствие quiet;
  затем проверяет original target в текущей модели и recording prerequisite.
- Model.cpp296–311: общий private `currentEvent()` сверяет epoch, eventId,
  startsAt, meetingUrl, meetingLinkPresent и `eligible(...)` текущих events.
  `matchesHandoffTarget()` только наблюдает соответствие. Обычный `revalidate()`
  дополнительно сохраняет прежний dismissed отказ; повторный Join не разрешён.
  Единственный product caller observation — рассмотренный known-handoff Record
  predicate; сам bool не доказывает OS launch или capture authority.
- NativeSettingsBridgeTests.cpp567–579: после known completeAction проверены
  positive observation, active-recording refusal, same-epoch URL replacement и
  event removal. Повторный completeAction остаётся refused. RecordingIndicator
  source test проверяет наличие нового guard. Это прочитанные assertions,
  не самостоятельно исполненные reviewer runtime tests.

## Остальные bounded source выводы

**Single-flight/reentry.** Один `calendarFlight_`, helper busy и joinable worker
защищены общим `calendarCalling_` scope. Context/source copies подготовлены до
`begin`; оригинальные source values сохранены для denial. Reentrant owner/poll
не может начать второй flight либо очистить слот первого. Host current включает
matching pending request, actual document current и command authorization;
cancel handler сверяет generation/nonce/event/request. `reported` устанавливается
до reply/card reentry. Child completion делегируется exact operation/work ticket,
не одному bool cancellation или stale callback.

**Worker drain.** Resolver захватывает copied config/event/deadline, не window
или `this`. В poll последовательность actual native thread handle
`WAIT_OBJECT_0` → `join()` → future `get()` → helper `complete(ticket)` сохранена.
`WAIT_FAILED` не снимает ticket/thread. Future readiness не используется как
физическое завершение. Poll стоит первым в `refreshNativeState()`, до
capture/shutdown/admission-dependent branches. Отзыв interaction/account
останавливает применимость, но не cleanup. Thread не detached.

**SDK/dialog lease.** Launcher cancellation остаётся discard-only; unknown
terminal/status fault удерживает handle и work. AppMain снимает SDK ticket после
launcher completed result, dialog ticket только после естественного Completed/
Error; GetResults failure не становится handoff. Hide request не очищает dialog
operation. PrimaryButtonClick требует alive, matching operation/work и fresh
current; timestamp явного подтверждения задаёт recovery resolver budget.
Recovery остаётся в opening, использует новый child только после matching drain,
не продлевает original action expiry и не превращает 15s resolver в OS/dialog
timeout. Start failure без acquired handle завершает только synchronous dispatch
scope и не принимается за успешный launch.

**Current/lifecycle/Record.** Owner проверяет exact origin/user/workspace/auth
generation/token, interaction epoch и document либо native target/expiry.
Auth replacement отменяет перед сменой token; hide/closing/interaction
invalidation отменяют applicability. Обычное закрытие удерживает resolver
lifetime; Closed reaps thread перед уничтожением members. Explicit process quit
остаётся принятой границей indeterminate SDK/dialog, не разрешением нового
flight. Ready-for-update не допускает busy calendar mutation. Launch/handoff
не заменяет capture prerequisites/видимый индикатор/Stop; H1 closure сохраняет
source identity после UI work. Нельзя использовать bool observation вне
known-handoff consumer как новую Join/Record authority.

**Card/retry/default behavior.** Для join/joinAndRecord actionPending выставлен
до layout/callback; второй action блокируется, close/expiry остаются действующими.
Pending presenter reconciliation не завершает действие по клику. Failure/retry
сохраняет original monotonic deadline; auth/event/stale/cancel retire не revive.
20s significant-notice clamp и focus hold не распространяются на meeting card.
Record/skip/problem прежние terminal branches не переведены в pending Join.
Новый общий owner не делает ShellExecute, не пишет URL/token в logs/storage
и не обходит strict resolver/validated HTTPS/native target pipeline.

**Ponytail:** лишнего service/interface/factory/второго HTTP client/clock framework
нет. Переиспользованы существующие timer, packaged_task/thread/future, current
helpers, stdlib и native handles. H1 repair вынес только общую exact event
проверку, сохранив dismissed semantics. Обязательные auth/source/drain guards
не являются переусложнением; оснований удалять их нет. Complexity verdict:
bounded diff acceptable, не утверждение готовности к выпуску.

## Evidence boundaries и terminal

Reviewer не запускал tests/build/VM/Git/GitHub и не менял product/norms/tasks,
markers или чужие отчёты. Единственная запись — этот reviewer-owned report.
Main сообщил SDK18718 exit0 и portable57972 45/45 + Chromium/WebKit2/2 для
предыдущего owner снимка; это не re-receipt новых H1 bytes. Native91306/его
первый NTFS AppMain snapshot не объявлен финальным. Historical Round239 proof
не переносится на Round240. Новые model assertions и static source wiring
прочитаны; сами по себе они не доказывают реальный UI message-pump сценарий,
actual worker/SDK/dialog completion или installed common owner.

В пределах рассмотренных десяти файлов после H1 исправления открытых source
findings нет: **C0/H0/M0/L0, historical H1 closed**. Source approval привязан
только к указанным SHA-256. Для full T119 остаются отдельно final-byte validation,
actual delayed/reentrant owner/native lifetime и installed acceptance, а также
известный tray entrypoint. Это не новые requirements и не повод менять schema,
tasks или scope этого отчёта.

## Round241 — isolated upcoming decoder SOURCE review, 2026-10-05

**SOURCE APPROVED C0/H0/M0/L0 только для трёх файлов ниже.** Это отдельный
decoder-срез: прежнее Round240 approval десяти файлов выше остаётся историей
своих bytes, не одобрением menu projection/tray rows/menu owner/Retry или
установленного приложения. Requirements M1 закрыт в operation-gate report
`955a2ff6f21503525513b37bb2ad82ebfede592e12c4f9a0034032a98a2287ca`;
plan menu п.1 и quickstart §16.1 лично перечитаны для этого source review.

Canonical workdir/заявленный HEAD прежние, Git не запускался. Pre-append этого
source report SHA-256 `68e0b7168923c5cb94cb51f7865d59044ddcaaf90ca9fe126c956b998582b262`.
Лично полностью перечитаны code-reviewer и ponytail-review SKILL.md. По явному
запрету пользователя Git diff/status, preflight/build/tests/VM не запускались;
проверены actual current bytes, narrow decoder/helpers, relevant callers и tests.

SHA-256 receipt повторно сверён **2026-10-05 19:34:40 UTC**, одинаковый в начале
и после чтения среза:

| Файл относительно canonical workdir | SHA-256 |
| --- | --- |
| apps/windows/RecApp/Upload/DesktopApiClient.h | `9b60e828795e44ec8d4603137a8eafaab29b64d864dd807ae7bd7a39fd786b80` |
| apps/windows/RecApp/Upload/DesktopApiClient.cpp | `ffd2373e5beca752bb75bd17fac3f157364d00c18e73251096c492373b3a8c68` |
| apps/windows/Tests/GrafWindowsContractTests/NativeSettingsBridgeTests.cpp | `f8bd564b268a57c7a280647a73956909775a183433589978339d51547c85f1ac` |

### Correctness / original behavior / bounds

- Header53–70: event.allDay=false и snapshot.showUpcomingTime/
  showUpcomingTitle=true добавлены в конец aggregate с default member
  initializers. Прежние initializer lists сохраняют порядок старых полей и
  получают новые defaults; обязательные UUID/owner/event поля не заменены.
- Decoder632–654: прежние 1MiB, root JSON, owner/workspace accountId, events
  array≤50 checks сохранены. Один локальный presentationBoolean принимает
  missing либо JSON null как заданный default, только literal true/false как
  boolean; string/number/object/array не coerced. `!showTime/!showTitle` проверяют
  has_value optional, а не contained false. Валидный false поэтому принят.
  JsonReader выделяет value после leading whitespace и до trailing whitespace;
  сравнение literal не зависит от обычных JSON whitespace separators.
- Decoder655–680: all_day проверяется внутри каждого event loop с default false;
  invalid value любого event возвращает nullopt всего snapshot, не partial
  result. Duplicate event IDs, parsed start/end ordering, link bool и прежние
  string validation/bounds продолжают действовать. Новый bool не меняет
  canSurface, titleAvailable, link identity или timestamps.
- Privacy: title_state available остаётся единственным условием сохранения
  decoded title; private/unknown title не возвращается в event.title. Title и
  open URL по-прежнему проходят calendarString UTF-8/surrogate/NUL validation
  и4096-byte bounds. showUpcomingTitle — отдельное presentation поле, не повод
  переписать card title/privacy semantics или разрешить launch. Эти decoded
  bools не создают token/URL egress, diagnostics/history, command/capture authority.
- Borrowed raw field views используются только в пределах decoder, результат
  владеет строками/вектором, boolean values copied. Нет новых dangling views
  или parser mode changes. Generic JSON/response/wire helpers не переделаны.
- Existing flow прослежен: calendarReminders config/confirmed identity/token/
  workspace/status checks → decodeCalendarReminders; AppMain existing response
  generation/session/epoch check → Presenter → Model owner/workspace check.
  Новые bools не обходят auth/current. Model на этой стадии сохраняет прежний
  card event flow, не использует snapshot menu flags; field consumer/menu
  projection ещё не реализован и не выдаётся за готовый functionality.

### Regression source / Ponytail / evidence boundaries

NativeSettingsBridgeTests994–1037 лично прочитан. Existing registered
testCalendarSchemaAndSafeJoin вызывается из main1330. Assertions покрывают:
missing defaults, null/true/false каждого нового поля, строки "true"/"false",
числа0/1, object/array refusals; private title при hidden-title flag; non-bool
all_day во второй строке с distinct valid UUID; прежние malformed date/missing
owner refusals. Response/event construction оставляет валидные прежние поля;
second-row assertion направлен именно на per-row validation. Новые поля не
подменяют safe-URL fixtures/старые action tests. Assertions reviewer не исполнял.

Main сообщил test-first invalidtypes RED assertion1010 на прежнем decoder и
последующее исправление трёх файлов; portable build был in progress. Здесь
это owner-reported история, не самостоятельно полученный GREEN/fullsuite/SDK
receipt. Ни previous full tests, ни read-only source assertions не принимаются
за final-byte runtime proof. Tests/decoder approval не закрывают actual menu,
popup reentry, common menu identity/expiry/Retry lifetime или installed T119.

Ponytail: **Lean already. Ship.** Только complexity verdict этого decoder:
одна локальная literal-bool проверка переиспользована трижды, нет dependency,
service/interface/factory, bool parser framework или второго HTTP client.
Staged fields прямо нужны следующей approved menu projection, не произвольная
unused flexibility; удалять их или типовые regressions оснований нет.

**Terminal Round241 decoder: C0/H0/M0/L0, bounded source approved на трёх SHA-256.**
Единственная запись — этот append; old findings/approvals сохранены, product/
norms/markers/tasks/Git/GitHub/VM/tests/build/audio и чужая dirty работа не менялись.

## Round242 — upcoming model/presenter SOURCE review, 2026-10-05

**SOURCE APPROVED C0/H0/M0/L0 только для текущего среза пяти файлов.**
Открытых actionable findings нет. Это проекция и observation frozen target,
не approval будущего tray popup, menu admission/Retry, полного AppMain owner,
actual native completion, launch/capture или установленного T119.

Canonical workdir: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`.
Заявленные branch/HEAD: `codex/200-windows-followup` /
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`; Git по запрету не запускался,
поэтому это не новый independently verified Git receipt. Pre-append report:
`3e93995de5967df63f6f84355902e6ddf6774321a4b4405bb3c056333dc58f10`.
Лично полностью прочитаны code-reviewer и ponytail-review SKILL.md; прочитаны
четыре текущих model/presenter файла целиком, новые tests и их registration,
затронутый failure/retry test, narrow decoder и actual snapshot apply caller.
Guidance/risk lane остаётся existing high-risk-feature, bounded source review;
нет замены обязательных requirements/analyze/native/installed gates сборкой.

### Exact source receipt

Пять SHA-256 одинаковы при начальном чтении и финальной сверке
**2026-10-05 19:53:41 UTC**:

| Файл относительно canonical workdir | SHA-256 |
| --- | --- |
| apps/windows/RecApp/Shell/MeetingReminderModel.h | `1d2c39eac076277ca005e3f56ff5b1ff37639505d98ac2a2512dee289d9803b9` |
| apps/windows/RecApp/Shell/MeetingReminderModel.cpp | `9d41eea4cf6737247455f3e60f4813847d7470b87481f0e04c9cd955c647e297` |
| apps/windows/RecApp/Shell/MeetingReminderPresenter.h | `a3567653bcf96eb18c8696f40dea9d1d5a78352d8039b30f79d43a54979f5074` |
| apps/windows/RecApp/Shell/MeetingReminderPresenter.cpp | `5ee5fa83ca3aa463dafbf25a5eee2b39674e9449826bb304d9d230fa230b85d6` |
| apps/windows/Tests/GrafWindowsContractTests/NativeSettingsBridgeTests.cpp | `ade3056f7c270dba3d3db6b36693515e69cba4c7c363332d527d75814cd81dde` |

### Correctness, availability и frozen identity

- Model.cpp262–270 сохраняет owner/workspace/epoch admission existing update.
  Неверный/stale ответ не заменяет текущую проекцию. API decoder по-прежнему
  проверяет body/event caps, owner/event IDs, duplicate IDs, instant ordering,
  title privacy и field types. Новый model guard проверяет finite start/end и
  end>start всех rows до разрешения сортировки: invalid typed dates отзывают
  menu availability целиком. Это не расширение decoder authority и не новый
  общий валидатор typed snapshot для произвольных внешних callers.
- Model.cpp272–279 возвращает owning copy существующего CalendarReminderSnapshot
  с owner/workspace и обоими server flags; sort startsAt/eventId, затем resize12.
  Полный events_ не обрезается. Нет фильтра canSurface/due/dismissed, recording,
  quiet/reminders или card deadline; allDay/title/link/URL поля копируются без
  изменения. Пустой успешно принятый snapshot означает available empty, не
  refresh failure. Returned rows не ссылаются на будущую изменяемую проекцию.
- Model.cpp281–288: current требует available, exact epoch, finite now/target
  dates, непустой ID, end>start, now<original endsAt, link и существующий safe
  HTTPS validator. Поиск идёт по полному events_, а не prefix12; совпадают
  eventId/startsAt/endsAt/link/URL. Поэтому unchanged admitted target остаётся
  current после выпадения из prefix, а removal/target replacement/end change
  его отзывают даже при том же owner epoch. Presentation-only title/allDay/
  flags/canSurface не переопределяют frozen target. Будущие auth generation,
  interaction, action UUID и immutable steady expiry проверки остаются
  обязанностью consumer; этот bool не launch/capture/admission authority.
- Model.h98 и Model.cpp260–261: invalidateUpcoming отзывает доступность, не
  стирая data нужные отдельной failed-card Retry. clearCalendar/invalidate/bind
  при смене контекста отзывают меню; same-context bind не сбрасывает snapshot.
  Недоступные старые events нельзя получить через upcoming/current. Presenter
  wrappers только делегируют эти observation APIs, не вводят второе состояние.
- Presenter.cpp72–76: invalidateUpcoming стоит ПЕРЕД failed-card early return.
  Поэтому ошибочный refresh немедленно убирает menu/current и одновременно
  сохраняет прежнюю card Retry/original deadline. Если сохранение карточки не
  требуется, existing retire/clear flow продолжается. Quiet/settings/reconcile
  меняют card presentation, не upcoming availability. Card dismissed checks и
  handoffRecordingCurrent semantics не ослаблены ради меню.
- Actual AppMain.cpp3973–3990 проверяет captured request generation/epoch/token
  и cancellation перед update; missing/rejected snapshot идёт в calendarFailed,
  401/403 также invalidate. Stale чужой response не отзывает новый snapshot.
  Эта трассировка подтверждает вход в model, не повторный source approval всего
  AppMain. Новые upcoming APIs пока не подключены к tray/menu owner; их будущая
  интеграция здесь не выдается за completed behavior.
- Нет I/O, URL launch, Record, новых persisted artifacts, token/URL logging,
  новой schema или передачи прав через flags. SafeMeetingUrl переиспользует
  прежний validator; original endsAt→checked monotonic conversion в этом срезе
  не реализуется и не подменяется wall now/current observation.

### Tests, reported RED и минимальность

Tests495–590 и592–618, failure/retry665–706 и registration1437–1438 прочитаны.
Assertions проверяют unsorted13/prefix12, equal-start ID ordering, server flags/
allDay, dismissed/canSurface=false/future/card-expired target, полный lookup
вне prefix, presentation-only refresh, шесть target replacements, wrong epoch/
owner response, NaN guard, unavailable/empty snapshot и origin/owner/workspace
switch. Presenter test отделяет quiet/reminders/capture от меню. Failure/retry
regression проверяет available до failure и отсутствие projection/current
после failure при всё ещё видимой Retry-card; прежний card Retry не продлён.

Main сообщил missing API compile RED, затем runtime RED на строке687 с stale
menu после failed refresh и последующее перемещение invalidateUpcoming перед
early return. Root cause и repair независимо подтверждены чтением final source
и assertions; это main-reported test history, не reviewer-run RED/GREEN.
Сообщённый stale old executable PASS не является evidence этих five hashes.
Reviewer не запускал сборку/тесты; final portable/native/SDK receipt main остаётся
отдельным доказательством. Source tests не доказывают popup message-loop,
физический worker/SDK/dialog drain либо installed UX.

Ponytail: **Lean already. Ship.** Только complexity verdict: один existing
model owner, три presentation bools, owning snapshot copy + std::sort/resize,
одна exact full-vector current проверка и тонкие presenter delegates. Нет
service/interface/factory, нового event cache/index, clock framework или
dependency. Для production decoder cap50 сортировка копии ограничена; отдельная
структура top12/target registry была бы лишней. Availability guard и finite
checks нужны для принятого failure/privacy/current boundary, удалять их нельзя.

### Normative receipt и terminal boundary

Scoped plan menu1–5/sequence, model§8, bridge§10, quickstart§16 и spec menu
clarification сверены с approved Round242 requirements; tasks T119 остаётся `[ ]`.
Хеши полных normative файлов совпадают с approved Round241/Round242 bytes:

| Артефакт | SHA-256 |
| --- | --- |
| spec.md | `b3edc920a6d6ad31b0be538c53a96637e087c43987f9d8133b58503a6bbf6911` |
| plan.md | `e5a36118f27ba0e3402b5adb5999b0cf853523af4b1a27fff834ac999f96391e` |
| tasks.md | `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f` |
| data-model.md | `d9d085d8a09f28c20e4e18a5359818780e8c33be186516506f98c939c53a5d46` |
| contracts/windows-native-web-bridge.md | `fcb99a1fc91a444cedb570aaa26ca490d71c33fbbfded9b82f5c129f12e1b542` |
| quickstart.md | `9a20a1cbf3737c5afb08cf8db70370af7f009cc803978f70b04a87d8a3e364be` |
| research.md | `62f381f1502a89c202b593f6ba7f8dddd6489fa9fd9a00e3a0696ea6e3f8b25f` |

**Terminal Round242 source: C0/H0/M0/L0, bounded five-file source approved.**
Requirements18/0 остаётся отдельным gate, markers не менялись. Исторические
Round240/241 findings и approvals сохранены; их хеши не заменены новыми.
Единственная запись — этот append reviewer-owned owner-source report. Нет
product/norms/tasks/checklist/Git/GitHub/VM/build/test/audio writes/jobs и изменений
чужой dirty работы. Native tray projection/selection, frozen source expiry,
common menu owner/Retry и installed/full T119 acceptance остаются вне approval.

## Round243 — UserTimeMetadata structural decoder SOURCE review, 2026-10-05

**SOURCE APPROVED C0/H0/M0/L0 только для нового declaration/decoder/test.**
Не re-approval всего DesktopApiClient/owner, formatter, host transport или
WindowsTray. Current requirements M1 CLOSED/18/0 относится к отдельному gate
`6f2e819aba35447f3cf5d1ce6dcac28aceda60ca01bf3a93a35cfee089d1afc1`.

Canonical workdir прежний; branch/HEAD заявлены user, Git не запускался.
Pre-append owner-source report SHA-256:
`90e691ad0e5d480f6954311e173ef9753682c9ba1673e525af7be1b061038174`.
Лично полностью перечитаны code-reviewer и ponytail-review SKILL.md. По user
scope их Git/preflight defaults не исполнялись. Прочитаны UserTimeMetadata,
decodeUserTimeMetadata, testUserTimeMetadataIsBoundedDataOnly и registration;
existing JsonReader/calendarString/accountId лично прослежены для нового call.
Risk lane: bounded source review existing high-risk T119, не новый direct lane.

### Current byte receipt

SHA-256 одинаковы в начале и финальной сверке **2026-10-05 20:20:12 UTC**:

| Файл относительно canonical workdir | SHA-256 |
| --- | --- |
| apps/windows/RecApp/Upload/DesktopApiClient.h | `1c6d5afb77f5310c8a7c957ef598c733eae9e5e130b1dd92f1de7d15e0e5c401` |
| apps/windows/RecApp/Upload/DesktopApiClient.cpp | `8eafdea3d06b85c329050be656bd980da34d4cd02719ee7f6cb238da8148a892` |
| apps/windows/Tests/GrafWindowsContractTests/NativeSettingsBridgeTests.cpp | `e69a4a5012f75b3030572850919490d98e7885c64eb5beaa38544237f7e97bce` |

### Correctness/security/lifetime

- Header89–95/230: пять owning strings, явный data-only contract. Public API
  не обещает current account/document, native timezone existence или auth/Join
  authority. Нет borrowed views, I/O, tokens, persisted context или logging.
- Cpp617–625: inclusive raw cap2048 до parser. Named `JsonReader(json,1,true)`
  живёт до извлечения всех полей; root decoded key views принадлежат reader's
  owning set, raw value views исходному json. Returned metadata копирует строки
  до выхода из reader scope. Не появляется temporary-reader key-view lifetime
  bug. Exact map size5 плюс extraction всех пяти expected keys исключают
  unknown/missing keys; strict reader отвергает raw/escaped alias duplicates.
- Depth1: root object depth0 допускает scalar values на depth1. Empty nested
  object/array может пройти lexical reader, но calendarString отвергает его
  как не-string; nonempty nested values depth2 также отвергаются. Null/bool/
  number не coerced. Trailing JSON bytes, invalid syntax и Unicode отвергаются
  existing strict parsing; generic reader mode/defaults не изменены новым call.
- Cpp626–631: user/workspace/session проходят existing accountId — exact36,
  lower-hex/hyphens и nil refusal. Это canonical identifier syntax, не проверка
  принадлежности аккаунту. timeZone <=100 decoded ASCII bytes; documentURL
  непустой и <=1024 decoded bytes. calendarString делает strict UTF-8/surrogate
  decoding и NUL refusal для всех known fields. Raw2048 ограничивает и escaped
  input representation, не только decoded length.
- Cpp632–635: empty zone либо exact UTC либо slash-containing candidate;
  zone ASCII whitespace/control/DEL/nonASCII отвергаются. URL ASCII whitespace/
  controls/DEL отвергаются, Unicode остаётся validated UTF-8, не URL policy.
  Unknown IANA candidate и чужой URL намеренно допустимы как bounded data:
  native Calendar validation/current URL equality/route/account/generations
  будут обязательны в следующих adapters. Decoder не должен реализовывать
  второй origin parser, zone database или объявлять syntax result предпочтением.
- Existing calendarString strict Unicode и JsonReader decoded duplicate logic
  переиспользованы без новой parser ветки/framework. Ничего не разрешает reading
  form/GRAFTime, bridge command, launch, Record или изменение action expiry.
  Same-page last-confirmed preference semantics остаются context consumer stage,
  не скрытая логика structural decoder.

### Regression source / minimality / evidence

Test28–79 и main1475 прочитаны: owning result после перезаписи raw input;
empty/UTC/IANA-candidate, escaped key/slash, exact zone100/URL1024/raw2048
positives и +1 refusals. Negatives покрывают missing/unknown/extra/duplicate/
decoded alias keys, null/bool/object/array, malformed/nil/noncanonical IDs,
zone controls/NUL/nonASCII/unpaired surrogate/invalid UTF-8, empty/control URL,
trailing bytes. Positive Invalid/NoSuchZone и external URL прямо фиксируют
отсутствие native zone/route/auth authority. Existing assert setup снимает
NDEBUG; тест зарегистрирован, не только объявлен. Runtime assertions reviewer
не исполнял и fixture source не принимается за native integration proof.

Main сообщил compile RED missing API exit2 и implementation build89446 exit0;
focused CTest был running. Здесь это owner-reported history, НЕ independently
полученный final GREEN/fullsuite. PowerShell Calendar7/7 другой стадии не
доказывает C++ decoder/native formatter/host context. Старые Round241/242
receipts не переносятся на новые bytes.

Ponytail: **Lean already. Ship.** Один existing strict reader, небольшая field
extract lambda, existing string/UUID helpers и std::any_of; нет dependency,
service/interface/factory/native zone mock или второго JSON parser. Exact
guards и tests обязательны для принятого trust boundary, не bloat.

Six current normative hashes повторно совпали с accepted Round243 submission:
spec `b411bfb620e9d571422f9c423b0ae193ed70e87303d08e84a4b9844e32f81658`,
plan `527e660d9e1682e7a0f0a79118ea4bab38d4c174542b49c0113f571528a5b89c`,
model `8dd54012c3bfe4003cd18db98ebc67e0b7730cbbdfb6523b881cce4cdc15ec19`,
bridge `21bffa56631901952ae778871f26785522d839eafc8afb9942b488ff22bbd0fa`,
quickstart `1065b1970125f2ea7cc323c0177d07485e34a339a6b7195df4af9aa65a5cb683`,
research `0e7659d4cf5136d392bde28cb273c6ca0be6af2ac3eca50e23a617e1af129522`.
Plan timezone2–5 scoped contract согласован с decoder-only boundary.

**Terminal Round243 decoder: C0/H0/M0/L0, bounded source approved.**
Only write — этот append. Нет code/norm/tasks/markers/Git/GitHub/VM/build/
tests/audio changes/jobs; чужая dirty работа/история preserved. Formatter,
current account/document read/reset integration, same-page runtime scenario,
tray/owner/installed/full T119 остаются отдельными acceptance gates.

## Round243 — upcomingTime formatter SOURCE review, 2026-10-05

**REQUEST CHANGES C0/H0/M1/L0 для текущего четырёхфайлового среза.**
M1 сообщён main сразу, до этого appendix. Это formatter-only review, не
re-approval Presenter/card/whole owner. Structural metadata decoder approval
выше остаётся историей других bytes и отдельной области.

Лично полностью прочитаны code-reviewer и ponytail-review SKILL.md; user no-Git/
build/VM/test restrictions выше skill defaults. Прочитаны declaration,
upcomingTime body, existing startText boundary, новый formatter test/main
apartment lifecycle, CMake object/link flow и existing SDK windowsapp linkage.
Pre-append report SHA-256:
`9da453aced98520315c08c0245acac53577314be2ed1354a1205d792c4649945`.
Current receipt **2026-10-05 20:25:20 UTC**:

| Файл относительно canonical workdir | SHA-256 |
| --- | --- |
| apps/windows/RecApp/Shell/MeetingReminderPresenter.h | `84adb4a7bbed55297eeb4b8eba62c886010308fc34fead35943e2c7056fe667f` |
| apps/windows/RecApp/Shell/MeetingReminderPresenter.cpp | `70e95cadf4c1413c820684327e133477b313fed7b07e928b960479b862669513` |
| apps/windows/Tests/GrafWindowsPackageTests/RecordingIndicatorTests.cpp | `ba4724c8153276c8928b4723268bdb8a94db153910b641d9f0a8e9cbfae86402` |
| apps/windows/CMakeLists.txt | `f9221695886f40209ad1839cf5487caf1d2a97d9170b6084408408293d7feae7` |

### M1 — floating epoch addition advances the displayed minute on MSVC

Location: **MeetingReminderPresenter.cpp:76**.
`floor(instant * 10000000.0L) + 116444736000000000.0L` остаётся floating-point
до final int64 cast. На MSVC long double имеет ту же точность, что double,
по [Microsoft Data Type Ranges](https://learn.microsoft.com/en-us/cpp/cpp/data-type-ranges?view=msvc-170).
Большой 1601 offset теряет low ticks и может округлить instant вверх до следующей
минуты, несмотря на floor, сделанный ДО addition.

Конкретные допустимые входы/арифметические counterexamples:

| UTC Unix instant | MSVC binary64 expression ticks | Expected label | Получаемая минута |
| --- | --- | --- | --- |
| `59.9999999` | `116444736600000000` — ровно60 Unix seconds | `00:00` | `00:01` |
| `1767225659.9999998` | `134116992600000000` — ровно1767225660 Unix seconds | `00:00` | `00:01` |

Reviewer вычислил expression read-only JavaScript binary64 + BigInt reference,
НЕ запускал C++ compiler/native Calendar/VM. Это source/math counterexample;
MSVC representation подтверждена primary documentation, runtime failure receipt
ещё должен получить main. Second input — непосредственно перед UTC minute
границей2026; проблема не ограничена далёким year9999. DateTime получает уже
округлённые ticks и не может восстановить исходную минуту.

**Минимальный repair:** для minute-only presentation сначала floor Unix instant
в checked int64 seconds, затем целочисленно `seconds * 10000000LL + offset`.
При принятом диапазоне0≤instant<253402300800 максимальный результат
2650467743990000000 ticks ниже INT64_MAX, так что этот путь без overflow.
Fractional seconds не нужны HH:mm; не строить дополнительный date/clock framework.
Добавить native assertions для входов непосредственно перед минутой и на самой
границе. Current test целочисленных instants/upper refusal не ловит M1;
portable ветка сама не делает floating WinRT conversion и может проходить.

### Остальной bounded flow / Ponytail / receipt limits

Cpp61–66 отвергает NaN/Inf/negative/upper-year limit и недопустимую syntax/ASCII
zone; hidden возвращает пустую label, allDay «Весь день». Header явно требует
accepted account-bound zone от caller, не выдаёт authority. Fresh Windows
Calendar, Gregorian/24-hour, ChangeTimeZone для named zone и system default
каждого нового Calendar соответствуют intended source; исключения return null,
Hour/Minute range/output checks не фабрикуют время. Native unknown-zone validation
здесь происходит на timed path; hidden/allDay не доказывают accepted context.
Future host обязан independently принять/validate preference по нормам.

Portable timed path честно только UTC/system, без IANA/DST emulation;
time_t conversion ограничен, localtime_r/gmtime_r failure null. Existing startText
и card интеграция не заменены этим API. Нет launch/HTTP/auth/handoff side effects.

CMake132 добавляет existing OS windowsapp к WIN32 executables, которым напрямую
переданы common OBJECT files с new WinRT references. Existing SDK vcxproj уже
имеет windowsapp.lib; новой сторонней зависимости/подавления предупреждений нет.
RecordingIndicatorTests26–55 содержит native Kathmandu/New_York DST/Berlin,
UTC/allDay/hide/invalid instant/zone, fresh system; main502–528 init/uninit
apartment. Эти assertions reviewer НЕ запускал. Main-reported portable1/1
0.49s после missing API RED не является Windows formatter proof; прежняя
metadata-only native CTest и PowerShell Calendar7/7 — другие evidence scopes.

Ponytail: **Lean already. Ship.** Только complexity verdict: existing presenter
static/native Calendar/stdlib и одна OS library, no factory/service/tz database.
Корректность M1 передана обычному review; complexity verdict не разрешает ship.

**Terminal formatter: C0/H0/M1/L0, M1 OPEN; source approval blocked до repair и
точного final-byte recheck.** Only write — этот append. Нет code/norm/tasks/
markers/Git/GitHub/VM/build/tests/audio changes/jobs. Native compile/runtime,
host accepted-time context/formatter integration, tray и full T119 не приняты.

## Round243 — formatter M1 source closure, 2026-10-05

**BOUNDED SOURCE APPROVED C0/H0/M0/L0; formatter M1 CLOSED по текущему source.**
Предыдущий M1 OPEN/math counterexample и original hashes сохранены выше.
Проверены только arithmetic repair и новые assertions, плюс неизменность
header/CMake. Не native C++ RED/GREEN и не formatter/host/tray integration proof.
Pre-append report:
`34867250363f55dead5a6bdac203e83de6a529f5fabcc27e8b46d4978df1efc5`.
code-reviewer/ponytail-review SKILL.md лично полностью перечитаны; user no-Git/
build/test/VM restrictions сохранены.

### Verified source repair

Current upcomingTime сначала отвергает nonfinite/negative/instant≥253402300800,
затем делает `int64_t seconds = floor(instant)`. Поэтому0≤seconds≤253402300799,
conversion определена, максимум далеко ниже INT64_MAX. Умножение и epoch
addition теперь целочисленные:
`seconds * 10000000LL + 116444736000000000LL`.
Максимум2650467743990000000 ticks <9223372036854775807; оба промежуточных
значения также помещаются. Floating-point прибавления большого epoch больше
нет, MSVC double-sized long double не может округлить HH:mm вперёд.
Discard subsecond part корректен для minute-only Gregorian display; это не
изменение исходного event instant/action expiry или audio clock.

Новые четыре assertions прочитаны:
`59.9999999→00:00`, `60→00:01`,
`nextafter(1710054060,0)→07:00`,
`nextafter(253402300800,0)→23:59`, все с UTC.
Они покрывают исходный counterexample, обычную minute boundary и valid point
непосредственно ниже upper cap. Existing equality-at-upper-cap refusal остаётся;
cmath добавлен для nextafter. Assertions находятся вне platform conditional,
поэтому native path исполняет именно repaired WinRT conversion, portable же
проверяет общий minute behavior, НЕ native repair доказательство.

### Exact receipt

Fresh hashes **2026-10-05 20:36:40 UTC** совпадают с submission:

| Файл относительно canonical workdir | SHA-256 | Относительно M1 receipt |
| --- | --- | --- |
| apps/windows/RecApp/Shell/MeetingReminderPresenter.h | `84adb4a7bbed55297eeb4b8eba62c886010308fc34fead35943e2c7056fe667f` | unchanged |
| apps/windows/RecApp/Shell/MeetingReminderPresenter.cpp | `fdbd819e49df00e918ed2e0b28b0bf6069de2cc5e444076ed47eaad3bacd5426` | integer repair |
| apps/windows/Tests/GrafWindowsPackageTests/RecordingIndicatorTests.cpp | `5d4cf9538c2e27467b813cb6e386cf1c7062acd50404f6edb251e9e38041f3ae` | boundary assertions |
| apps/windows/CMakeLists.txt | `f9221695886f40209ad1839cf5487caf1d2a97d9170b6084408408293d7feae7` | unchanged |

### Source против remaining actual proof

| Gate | Статус этого review |
| --- | --- |
| M1 root cause removal / int64 bounds | Independently source-verified, CLOSED |
| Boundary regression source / unchanged header+CMake | Independently read/hash-verified |
| Native C++ RED old formatter + new boundary assertions | NOT YET evidenced; main owns frozen old NTFS helper |
| Native C++ build/GREEN current cpp+test hashes | NOT YET evidenced; не переносить older metadata/integer-test run |
| Current final portable/native suite / SDK | Отдельный main validation receipt, reviewer не запускал |
| Accepted user-time host/account binding / tray / installed | Вне source closure; не приняты |

Main сообщил serial older CTest всё ещё работает и frozen old formatter ждёт
native RED. Reviewer не опрашивал, не перезапускал и не вмешивался в эти jobs;
load/progress информация не доказательство formatter PASS. Предыдущее decoder
three-file approval не переоценивается и не смешивается с этими четырьмя hashes.

Ponytail: **Lean already. Ship.** Complexity only: один integer intermediate,
existing guard/native Calendar и четыре targeted asserts; новый framework или
dependency не добавлены. **Terminal source C0/H0/M0/L0, historical M1 CLOSED.**
Only write — этот append; code/norm/tasks/markers/Git/GitHub/VM/build/tests/audio
не менялись/не запускались. Actual native RED/GREEN и full T119 не объявлены PASS.

## Round243 — main-reported final RED/GREEN receipts, 2026-10-05

Receipt записан **2026-10-05 20:45:00 UTC**, только после сообщённого natural
terminal focused GREEN. Pre-append report:
`9ae88ca33aa544cd562147ba3289a8a126373ac41e181d680f69ba5294a67ab7`.
Reviewer НЕ исполнял эти jobs, не читал их raw logs и не выполнял новый source
review; ниже точная owner-reported evidence, не independently executed tests.

| Проверка | Main-reported terminal receipt | Область доказательства |
| --- | --- | --- |
| Controlled native RED | `90050/ec8a75`, exit8; old `70e95cad…` formatter + new `5d4cf953…` tests compiled; assertion line30 `59.9999999 UTC→00:00` failed, `0xc0000409`,2.73s | Actual воспроизведение M1; expected assertion, не shared-temp crash |
| Fixed native focused GREEN | `92060/0248c4`, exit0; seven final source hashes match; test#35 NativeSettingsBridgeTests PASS0.46s, test#45 RecordingIndicatorTests PASS0.21s;2/2 PASS0.74s | Fixed structural decoder + formatter focused run, не full49 rerun |
| Fixed portable full | build `40911` exit0; `97151/b9568c`,45/45 PASS22.93s; same fixed seven source bytes | Portable suite; named-zone native proof не подменён |
| SDK | `23120` pending по сообщению main | Здесь НЕ BUILD/PASS receipt |

Seven-byte set — три decoder hashes из structural-source receipt и четыре
formatter hashes из M1 source closure выше. Main подтвердил их неизменность;
source approval `9ae88…` остаётся на этих bytes, historical findings сохранены.
Older native49 metadata228.40s и initial-formatter49 642.64s — другие snapshots,
не fixed current49/49. Их не переназывать final fixed suite.

**Source verdict unchanged C0/H0/M0/L0; M1 CLOSED.** Main сообщил validation
Round243/F200 fragment, но reviewer их не менял и не выдаёт за installed proof.
T119 остаётся open/incomplete: host/account user-time context, tray/menu owner
и installed/full-feature acceptance отдельны. Only write — этот appendix;
нет новых tests/build/VM/Git/GitHub/source/norm/tasks/markers/audio actions.
