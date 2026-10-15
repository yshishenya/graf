# T119 Round235: CalendarJoinOperation — bounded source review

Проверка начата 2026-10-04, завершена 2026-10-05; имя отчёта сохранено по scope.
Вердикт: **APPROVED для state/fence primitive**.
**C0 / H0 / M0 / L1**; блокирующих C/H/M в данном срезе не найдено.
L1 — необязательное усиление защитных тестов, не установленная ошибка кода.

## Область и основание

Канонический repo: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`.
Branch: `codex/200-windows-followup`; свежий HEAD:
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`. Dirty изменения сохранены.
Пять файлов прочитаны полностью, включая actual untracked helper/tests и полный
CMake/vcxproj. Для tracked registration прочитан diff; его старые transport/URL/
storage строки не переоценивались как новые Round235 изменения.

Lane: bounded source review внутри existing high-risk T119, не release lane.
Лично полностью прочитаны `code-reviewer` и `ponytail-review` SKILL.md. Применены
correctness/security/lifetime/edge-case и отдельная complexity оценка. Единственная
запись — этот reviewer-owned report; код, нормы, tasks, checklists markers,
GitHub, commits, build/VM и чужие dirty файлы не изменялись.

Requirements основание перечитано: принятые calendar-operation 8/0 и собственный
requirements report, current plan T119 operation paragraph. Хеши bridge §10,
data-model §8, quickstart §13 и plan совпадают с принятым gate; их ранее прочитанный
нормативный контекст сохранён. Дополнительно прослежены существующие
DesktopApiClient::calendarJoinTargetPath → calendarEventId → accountId/nil exception
для проверки UUID reuse, без нового decoder/transport review.

## Точные текущие SHA-256

| Файл | SHA-256 |
| --- | --- |
| apps/windows/RecApp/Shell/CalendarJoinOperation.h | `e2e4c2aac96a7d3097aeebe103353aef8399302d6256c43f8a69945ab0f3b335` |
| apps/windows/RecApp/Shell/CalendarJoinOperation.cpp | `3933fb7fa4a8ed70688bdf0869a30222297fdd2f56b0299a62771096b80812ed` |
| apps/windows/Tests/GrafWindowsContractTests/CalendarJoinOperationTests.cpp | `f585c4d93309712ec8f5e3db7000cedb562dfb4986b597432af23197640b1cb7` |
| apps/windows/CMakeLists.txt | `e61d00fa66b7142dd4dc3610e762569119bee5b023bd08f6769af2d2ca17a5e0` |
| apps/windows/RecApp/GrafWindowsApp.vcxproj | `4ecb8d544bfd40da3ee483a816a2ff92c02e88ce3b27cba33c5b019f78efa445` |

Повторное чтение хешей до отчёта подтвердило те же пять значений.

| Принятое основание / scoped dependency | SHA-256 |
| --- | --- |
| checklists/calendar-operation.md | `a656adcd4d6cccf578cc7c98f385fe10ba5b422cfb47dba7e3662f8b24e0a834` |
| checklists/review-2026-10-04-calendar-operation-gate.md | `c67cc1d98742e1087116baa00a243b653b900481a0b319dc5c841fdcd51994bb` |
| plan.md | `f9cf2f74a57f6a2b739bd72915e2d7cab281f9685c997d008e2b81c4d17bfaac` |
| contracts/windows-native-web-bridge.md | `ee5e6007eecfbd8ce317338d8dfed680009ca089420af63b93c5ebccdb01ccf1` |
| data-model.md | `28641767480ac310579fd55f1a4d5c2f91b82ad69d8dcf6da4a53040c6419764` |
| quickstart.md | `930aed240d1efe1ce58b2657a27a82a80552684c7e8b35f8763a7f34c71640c0` |
| DesktopApiClient.cpp | `05f5eb4bd5e47e5ec2faf184d4bf9154f3625a3d606119b25cce1a388aa1060c` |
| DesktopApiClient.h | `af7ded9a6001609fe331b722eb29071a7497a60c59c7a26b3b7c891bae31c9fb` |

## Correctness / security assessment

- **Admission и UUID reuse.** cpp15–18/43–54 используют существующий path builder
  только для syntax validation, без I/O. DesktopApiClient.cpp526–532/575–577
  обеспечивает exact36 UUID, hex/hyphens через existing accountId, ASCII case
  normalization и разрешённый nil calendar UUID. Helper затем сохраняет IDs в
  lower-case. Account authority validator не изменён. Обязательные context strings
  и valid source проверяются до admission; cancellation allocation выполняется
  до изменения текущей операции.
- **Single flight и child identity.** cpp25–41/66–87: busy сохраняется в
  resolving/opening даже между child work и при terminal с ещё pending ticket.
  Только один work_ разрешён. Operation и work IDs независимы, возрастают без
  сброса work ID на новой operation. Matching completion сверяет оба IDs, kind,
  deadline и cancellation pointer до любого изменения. Duplicate initial result
  не сбрасывает recovery child; старый operation не отменяет новый.
- **Context fence.** cpp10–13/56–64 сравнивают exact origin, owner, workspace,
  token, auth generation, source, epoch, identity и immutable action expiry.
  Drift/expiry дают cancelled/stale, ставят общий cancellation flag и не снимают
  pending work. Context не обновляется при recovery. Нулевой/чужой ID и уже
  terminal state возвращают false, не применяя эффект к новой операции.
- **Resolver budget и drain.** cpp37–41/61–72: initial budget строится от
  acceptedAt, recovery — от confirmedAt, а не от момента worker start/chunk.
  Ровно на deadline применяется отказ (`>=`). complete проверяет срок/current
  до work_.reset; поздний результат становится drain-only. Следующий opening
  требует отсутствия initial pending resolver (74–76).
- **Почему deadline не проверяется после resolver drain.** Это соответствует
  whole-resolver-call, а не whole-open-operation сроку. До успешного matching
  complete срок проверен; после него старый resolver уже не pending. Сохранить
  его как общий timeout для query/launch/dialog означало бы нарушить принятое
  уточнение. Original action expiry и весь context по-прежнему проверяются на
  каждом helper переходе. Adapter обязан передавать актуальное монотонное время
  на проверках/применении, не обходить проверку подстановкой старого timestamp.
- **Recovery и terminal.** cpp78–105 допускают OS/dialog work только в opening,
  без параллельного child. recover создаёт новый resolver ticket, сохраняя
  внешний opening и request identity. Terminal не оживает. Failed/cancelled
  могут быть выставлены с pending work; busy остаётся до точного drain.
  HandedOff требует opening, отсутствия pending work, reason=none и fresh context.
- **Числовые границы.** cpp34–40/45–46 отказывают при uint64 max до increment;
  счётчики не оборачиваются и не создают ID alias. Сложение15s guarded:
  near-clock-max saturates к time_point::max(), не выполняет переполнение.
  При max абсолютная проверка expiry отвергает результат; saturation сокращает
  представимый остаток, не даёт бесконечного приёма после deadline. В обычном
  диапазоне budget ровно15s. Для query/launch/dialog max — отсутствие выдуманного
  resolver timeout, не отмена исходного action expiry.
- **Registration.** CMake12–15/50/92–101/130 подхватывает helper в existing common
  OBJECT и добавляет ровно один отдельный test target без второго implementation
  include. vcxproj129 включает cpp один раз в production project. Existing
  DesktopApiClient находится в обоих source наборах; новая dependency не добавлена.

## Обязательная граница trusted caller / adapter

begin проверяет непустой native context, **не** HTTPS allowlist, Source/route/
nonce/replay/auth authority. Это не web parser: h17 и37–39 явно ограничивают
input доверенным native snapshot. До вызова будущий adapter обязан установить
доверенность источника и актуальные owner/workspace/token, а после ожиданий
передавать новый снимок действительного контекста, не копию принятого старого.

complete — сигнал adapter о факте actual exit либо доказательстве, что work не
был создан при dispatch (h50–51). Helper не имеет worker/OS handle и не способен
проверить physical completion. Cancellation atomic — только запрос отмены.
Destructor запрашивает её, **не** доказывает drain и не является освобождением
реального native lease. Adapter должен удерживать owner/реальные операции до
фактического completion, в том числе при close/Hide/Cancel/queue rejection.

recover требует caller proof явного подтверждения пользователя, а finish
handedOff — caller proof положительного OS outcome после matching completion.
В helper не закодированы outcome/confirmation/последний успешный launch kind;
он не удостоверяет эти факты. Поэтому drain resolver/query/dialog сам по себе
не разрешает production handedOff. Это граница принятого primitive, не найденный
дефект при его trusted-caller контракте. Fresh auth/URL policy/проверка прямо
перед OS dispatch, auth expiry apply и Record-after-current/readiness остаются
в consumer/adapter; helper не выполняет и не принимает их.

## L1 — недостающие защитные тесты (не блокирует)

Место: `CalendarJoinOperationTests.cpp:72–107`; защитные ветки production
`CalendarJoinOperation.cpp:34–40` и `66–68`.

Текущие assertions покрывают обычные15s, recovery, action expiry и duplicate old
ticket, но не near-clock-max saturation и различающиеся kind/deadline/cancellation
при совпадающих operation/work IDs. По чтению ветки корректны; выявленной ошибки
нет. Небольшое необязательное усиление: synthetic acceptedAt=max−1s → deadline=max,
refusal/drain на max; изменённая копия active ticket → complete=false с сохранением
настоящего pending work, затем original ticket drain. Framework/private-counter
seam или обход2^64 шагов для этого не нужны. uint64 exhaustion оценён по source,
не объявлен выполненным тестом.

## Тестовые доказательства и Ponytail

Прочитаны assertions oneFlightAndDrain, everyContextFence,
resolverAndRecoveryBudgets: cancellation удерживает busy, late old completion не
меняет новый ID, все9 context fields проверяются, recovery остаётся opening,
старый child не освобождает новый, ровно deadline даёт отказ, action expiry не
продлевается. NDEBUG снят перед assert, поэтому проверки не исчезают в Release.
Наличие assertions — source coverage, не independently executed PASS.

По сообщению main focused portable RED missing header → GREEN прошёл. Reviewer
не повторял build/tests; заявленные в работе portable full42/native full45 не
считаются завершёнными. Ни один helper test не доказывает actual worker/OS/dialog
completion, реальный источник/auth, installed launch или Record.

Ponytail-only assessment: **Lean already. Ship.** Это вывод только о сложности
данного primitive: stdlib optional/shared atomic/chrono, один concrete owner,
existing UUID helper, без I/O/factory/interface/framework/нового HTTP client.
Фраза не означает разрешение shipping, релиза или функциональной приёмки T119.

## Итоговая граница acceptance

Source approval относится только к этим пяти точным файлам и trusted UI-thread
state/fence поведению. AppMain/WebView/card/menu ещё не подключены: scoped поиск
CalendarJoinOperation показал только helper и его tests. Actual adapter lifetime,
reentrancy/shutdown/drain, browser confirmation, OS query/launch outcome,
pre-dispatch authorization/URL/current и native Record не приняты этим review.
Другие T119/native OS/installed gates и общий Feature200 остаются вне scope.

Новых C/H/M блокеров нет; L1 необязателен. Requirements checklist/старый gate
не изменены. Финальный report hash выдаётся отдельно после reread, без self-hash.

## Приложение 2026-10-05 — ограниченная перепроверка L1

**L1 закрыт по source coverage. Текущий verdict: APPROVED для того же
state/fence primitive, C0 / H0 / M0 / L0.** Исходный L1 выше сохранён как история.
Это не повторная оценка всего helper или новый native/installed gate.

Лично прочитаны новые actual test bytes, `ticketAndClockBounds()` строки109–128
и регистрация вызова в main131. Новая функция по очереди меняет kind, deadline
и cancellation pointer, сохраняя operation/work IDs. Каждый ложный ticket даёт
complete=false, owner остаётся busy/resolving, настоящий cancellation flag не
установлен. Original ticket затем проходит drain. Проверка max−1s подтверждает
saturation deadline=max; max−1ns ещё current, на max matching completion не
применяется и снимает pending work, выставляя cancellation. Здесь original
actionExpiresAt=max выигрывает проверку прежде resolver deadline: ожидаемый
terminal — cancelled, а не failed/dependencyUnavailable. Это корректное
покрытие уже рассмотренной защитной границы, не изменение её семантики.

Новый test SHA-256:
`a6b01c1fa2dab323047cd2dde2ff445e348591e07a5b128dfe19c5981a983964`.
Read-only преобразование stdout, исключающее только добавленную функцию и её
вызов, восстановило исходный hash
`f585c4d93309712ec8f5e3db7000cedb562dfb4986b597432af23197640b1cb7`.
Таким образом, остальной test text совпадает с первым receipt.

Четыре остальных source hash независимо сверены и **не изменены**:

| Файл | SHA-256 |
| --- | --- |
| CalendarJoinOperation.h | `e2e4c2aac96a7d3097aeebe103353aef8399302d6256c43f8a69945ab0f3b335` |
| CalendarJoinOperation.cpp | `3933fb7fa4a8ed70688bdf0869a30222297fdd2f56b0299a62771096b80812ed` |
| CMakeLists.txt | `e61d00fa66b7142dd4dc3610e762569119bee5b023bd08f6769af2d2ca17a5e0` |
| GrafWindowsApp.vcxproj | `4ecb8d544bfd40da3ee483a816a2ff92c02e88ce3b27cba33c5b019f78efa445` |

Канонические branch/HEAD повторно подтверждены:
`codex/200-windows-followup`, `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`.
Report до приложения имел SHA-256
`da31025c77d7f0d1e3934fd3efd5f9bfd6ec320688328a72eb2fb703190f86fc`.
Изменён только этот отчёт, append-only; старые findings/verdict/receipts не
перезаписаны. Requirements markers и product source не изменялись reviewer.

Code-reviewer и ponytail-review лично полностью перечитаны для bounded recheck.
Новые assertions минимальны, без framework или production seam.
Ponytail-only: **Lean already. Ship.** Граница этой фразы остаётся прежней.

По сообщению main full portable42/42 PASS20.72s и native45/45 PASS206.02s
относятся к байтам до L1 additions. Финальный rerun новых test bytes выполняет
main; reviewer его не запускал и не объявляет завершённым. Закрытие L1 означает
наличие корректных assertions, не independently executed PASS. Actual adapter
completion, auth/launch/Record и установленный T119 по-прежнему не приняты.

## Round247 — bounded SOURCE review: owned menu Retry helper + AppMain

2026-10-06, actual read receipt `2026-10-05T22:44:34Z`.
**REQUEST CHANGES: C0/H0/M1/L0. M1 блокирует source approval этого slice.**
Requirements gate18/0 остаётся принят, не переоткрывается из-за source finding.
Canonical `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`,
branch/HEAD submission `codex/200-windows-followup` /
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`; новой Git-проверки не выполнялось.
High-risk-product lane. Reviewer полностью прочитал code-reviewer и
ponytail-review; их review-only применение ограничено этими изменениями.

Прочитаны полный CalendarJoinOperation.h/.cpp и весь CalendarJoinOperationTests,
AppMain common owner/current/source/admission/resolver/SDK/dialog/poll/member
участки и все найденные вызовы cancel/admit/poll, auth switch, Hide/exit/Closed,
timer-before-admission; fresh native UUID generator и existing
DesktopApiClient::calendarJoinTargetPath. Дополнительно по уточнению main
прочитаны RecordingIndicatorTests::testCalendarJoinOwnerSourceWiring и Retry
assertions. Остальные функции больших AppMain/RecordingIndicatorTests не
объявляются повторно audited; source hash связывает весь файл, scope — этот diff.

### Точные reviewed bytes (после двух уточнений main)

| Файл | SHA-256 |
| --- | --- |
| apps/windows/RecApp/Shell/CalendarJoinOperation.h | `a22ed3de17f5a21e7e7b0bd3e3ca46f2f89ab9c72141a95b9e9f1bd61cd4c630` |
| apps/windows/RecApp/Shell/CalendarJoinOperation.cpp | `946f7e452b8cdf803ab96d39f85fee2f9c252f362ab269ea34d855e135da7337` |
| apps/windows/Tests/GrafWindowsContractTests/CalendarJoinOperationTests.cpp | `597b000601f8b661782d07ba8f084b1a445a7c2215835d36272f996117ea5d46` |
| apps/windows/RecApp/AppMain.cpp | `9eddf871a910a6442b615adfbf6b4d6832fff4f264c716a29587c53bd2bfbc02` |
| apps/windows/Tests/GrafWindowsPackageTests/RecordingIndicatorTests.cpp | `2809071d9bca9c274131e370b41bc61d7ad45ba813f9dc30bf4569440176099c` |

Initial intermediate helper.cpp `2fccd0ae…`, tests `8a63bf2d…`, AppMain
`340abaf5…` не принимаются как final receipt; latest files перечитаны.
Applicable Round247 requirements report hash:
`8e080c2991d2cb73b20fa0982880bcf4c75c5ae8640bd78276304d11567c81f1`.
This source report before append:
`cba8a3e1b9a0c7828d05bd8c44efb4b2ad0038409e3aa8c3a6c0260b94b2e4d0`.

### M1 — first resolver deadline tick cancels the menu Retry reservation

**AppMain.cpp3925–3926**, together with CalendarJoinOperation.cpp64–70 and
147–151. Concrete source trace, not reviewer-executed runtime reproduction:

1. An admitted current menu flight is resolving, its resolver still owns work,
   original action expiry is later than the15s resolver deadline.
2. On the first poll at/after deadline, `failedMenu` is computed as false because
   the attempt is still resolving before `calendarCurrent()` runs.
3. That call executes helper `current()`: terminal failed/dependencyUnavailable,
   cancellation set, return false, with retryAllowed reservation still true.
4. The already-selected false branch immediately calls cancelCalendarJoin.
   Helper cancel observes failed+retryAllowed and clears that reservation.
5. Actual worker drain correctly stays pending, but after it finishes the
   predicate at AppMain4034–4037 cannot offer Retry: retryCurrent is false and
   cleanup resets the flight. The user sees no owned failure Retry for this
   ordinary resolver timeout; the same path affects a new retry resolver timeout.

This violates approved plan menu6–7 / quickstart§16.4: timeout is a failed
attempt eligible for explicit Retry after actual drain while source remains
current, not a request to revoke the reservation. No concurrent second launch
was found here; severity MEDIUM is functional/source acceptance blocking.

Minimal correction direction: after current() returns false, distinguish the
newly failed current menu reservation from genuine stale/cancelled/revoked
source before invoking cancellation. Revalidate fresh source/auth/expiry; do
not generally ignore cancellation. Preserve pending ticket/thread until actual
matching exit and no admission gap. No new owner/interface/schema is needed.

Required narrow regression: reproduce the first poll sequence (resolving →
current at deadline → cancellation decision), assert failed + reserved busy
before and after old matching drain, then allow one owned Retry dialog. Repeat
with a NEW Retry resolver timeout; stale source/action expiry must still revoke
the reservation. Existing CalendarJoinOperationTests.cpp164 uses direct complete() at
deadline; it exercises helper retention but bypasses the offending AppMain
decision. Static RecordingIndicator assertions also do not execute this branch.

### Other evaluated boundaries — no additional C/H/M findings

- Helper opt-in defaults false, rejects document opt-in, compares all9 context
  fields including original expiry, preserves failed result while reserved;
  cancel never drains work. Distinct monotonically increasing operation/work
  IDs and complete() exact ticket keep old callbacks from draining a new child.
- confirmRetry114–119 uses exact dialog ticket including cancellation pointer,
  rejects null/cancelled token and repeated click. The added oldDialog test
  rejects a failed browser-dialog ticket as a Retry decision. retry121–131
  requires stored click + matching drain, fresh normalized request UUID,
  unchanged context/expiry, valid click+15s and counter bounds; new cancellation
  allocation precedes state mutation. Event/source identity remain unchanged.
- AppMain3902 records click before ShowAsync completion; polling drains natural
  Completed/Error before new request/operation and guards the whole transition
  with calendarCalling. Late click+15s refusal cancels reservation, not a fresh
  budget. New attempt clears cached URL/browser/decision fields and resolves
  again; menu cannot enter native joinAndRecord/Record path.
- Resolver signal → join → future.get → complete ordering remains, not
  future_ready proof. SDK indeterminate and dialog Status fault/Canceled retain
  pending ownership. failCalendarJoin3750–3752 now Hide-requests a failed old
  dialog without using Hide as drain; retry-dialog unknown exit revokes Primary.
  Source/auth/expiry invalidation cancels applicability; poll runs independently
  of interaction admission. Explicit process exit remains the approved boundary.
- Reuse is minimal: existing state helper/common flight/ContentDialog/UUID path;
  no new dependency, HTTP client, owner, factory, persistent cache or logging.
  Ponytail-only: **Lean already. Ship.** net: 0 lines recommended for deletion;
  this complexity verdict does not override the correctness M1 or authorize ship.

Assertions are source coverage only. Reviewer ran no build/test/VM/browser or
native UI jobs; main's ongoing validation is not stamped PASS here. Actual
ContentDialog user click/exit, delayed worker/SDK completion, installed native
menu/recovery/current-account and card/cabinet regressions still require their
own proofs. No full T119/Feature200/runtime acceptance. Only this append changed;
code/norm/tasks/checklist markers/Git/GitHub/user dirty files were not edited.

## Round247b — append-only M1 closure, first deadline tick

2026-10-06, fresh receipt `2026-10-05T22:47:39Z`.
**M1 CLOSED by source revalidation; APPROVED bounded Round247 Retry slice,
C0/H0/M0/L0.** Original M1 and rejected source hashes above remain historical.
Requirements18/0 unchanged. This is not actual UI/SDK/dialog/installed acceptance.

Code-reviewer and ponytail-review were fully personally reread for this delta.
Only AppMain's poll condition and the two changed tests were re-reviewed;
helper .h/.cpp were independently hash-checked unchanged. Canonical worktree/
submission branch/HEAD remain as above; no Git/VM/build/test commands executed.

### Exact current SHA-256

| Файл | SHA-256 |
| --- | --- |
| apps/windows/RecApp/Shell/CalendarJoinOperation.h — unchanged | `a22ed3de17f5a21e7e7b0bd3e3ca46f2f89ab9c72141a95b9e9f1bd61cd4c630` |
| apps/windows/RecApp/Shell/CalendarJoinOperation.cpp — unchanged | `946f7e452b8cdf803ab96d39f85fee2f9c252f362ab269ea34d855e135da7337` |
| apps/windows/Tests/GrafWindowsContractTests/CalendarJoinOperationTests.cpp | `f40c1f0d825906e9a304e15b4606d7c2d0306374648ddb0bc0a42c53c3e77bd2` |
| apps/windows/RecApp/AppMain.cpp | `2b7fb97f1a64853b78146cb715bfe3f752a11908727ed4fb2d0babade63194dc` |
| apps/windows/Tests/GrafWindowsPackageTests/RecordingIndicatorTests.cpp | `4f0c98ffd5127d8e3e7c74f60c59567ab79ab7f469bb0db1238af2686d3757b3` |

AppMain3925–3927 removes cached failedMenu and uses the ordered condition:
`if (!calendarCurrent() && !calendarRetryCurrent()) cancelCalendarJoin();`.
On the first deadline tick, current() first creates terminal failed and signals
the old worker cancellation; retryCurrent then independently rechecks menu
source/auth/context/original expiry and preserves its reservation. No worker is
drained by this condition, no result becomes current again, and no Retry dialog
is offered before matching actual old completion. Stale/expiry/explicit cancel
still fail both predicates and revoke applicability without releasing pending
work. Document/card without menu Retry opt-in remain fail-closed.

CalendarJoinOperationTests216–246, registered at251, executes that exact ordered
helper decision at deadline for two attempts: initial resolver and a NEW
explicit Retry resolver. It checks failed/cancelled old token + busy before
drain, refusal to create dialog while old work pending, drain-only completion
with reservation retained, matching dialog/explicit Primary/drain, and new
retry resolver. Separate stale-context and original-expiry cases assert
cancelled+busy until old drain, then no busy/no retryDialog. Existing tests
continue to cover click+15s refusal, all9 context fences and old IDs/tickets.
RecordingIndicatorTests432–433 requires the exact ordered AppMain expression
and forbids cached `const bool failedMenu`. This binds the helper regression to
the source call order; it does not execute AppMain or prove physical completion.

Read-only stdout-only reconstruction of each file, reversing just this delta,
reproduced all three prior reviewed full hashes:
AppMain `9eddf871a910a6442b615adfbf6b4d6832fff4f264c716a29587c53bd2bfbc02`,
operation tests `597b000601f8b661782d07ba8f084b1a445a7c2215835d36272f996117ea5d46`,
indicator tests `2809071d9bca9c274131e370b41bc61d7ad45ba813f9dc30bf4569440176099c`.
Thus no other bytes in those three files changed from the bounded first review.
No new C/H/M/L findings. Ponytail-only: **Lean already. Ship.** net: 0 additional
lines recommended for deletion; no new abstraction/service/helper/schema.

Report before this closure:
`e86721cea6d5c97855e41212473fa5e2c8e0582c99a9990311a44492dad6dfc5`.
Main portable/final SDK validation was still pending at submission; no final
runtime receipts are asserted here. Initial247 SDK bytes, any old PASS and
source assertions are not final247b UI/installed proof. T119 remains open with
actual delayed worker/SDK/dialog, explicit user Retry, installed/current-source,
card/cabinet and release gates separate. Only this append was written; product,
norms/tasks/markers/Git/GitHub/user dirty work preserved.

## Round249/249b — isolated native ContentDialog fixture source review

2026-10-06; read receipt `2026-10-05T23:22:46Z` plus immediate249b re-read.
**No concrete source findings: C0/H0/M0/L0. Static snapshot APPROVED within the
two-file fixture scope; final frozen submission and native build/run are pending.**
Code-reviewer and ponytail-review were read fully. Both new files were personally
read in full, including the metadata/header repair; production operation helper
and central build props were personally traced as reused inputs. No Git, VM,
build/test, OS input, installation or external-state action was executed.
Canonical feature/worktree/submission branch/HEAD remain as recorded above;
requirements gate18/0 and Round249 gate are separate from this source decision.

### Exact reviewed bytes

| File | SHA256 |
| --- | --- |
| Tests/GrafWindowsContractTests/NativeCalendarDialogTests.cpp —249b | `aed944baa3449e863d7d33122c6606c2cee6b678ac9af62053e2f270c1ab055a` |
| Tests/GrafWindowsContractTests/NativeCalendarDialogTests.vcxproj —249b | `79109cfff8324a9ff13e68299b8cd0ecd0650087e54308553bd162bfbaa48c8e` |
| RecApp/Shell/CalendarJoinOperation.h — unchanged | `a22ed3de17f5a21e7e7b0bd3e3ca46f2f89ab9c72141a95b9e9f1bd61cd4c630` |
| RecApp/Shell/CalendarJoinOperation.cpp — unchanged | `946f7e452b8cdf803ab96d39f85fee2f9c252f362ab269ea34d855e135da7337` |
| Directory.Build.props — existing | `e3a21249e822df3c1201b2ba2df1941f44538f33e34bf8b2e07bd3ed4d3f4a6b` |
| Directory.Packages.props — existing | `7a15dfcd1f0f6a0b4f229e40096467319a01e4be3bea96afe4e709e4e7093088` |

Paths above are relative to apps/windows. Initial read hashes cpp `f6e4c2a1…`
and project `2861382c…` preceded the249b dependency/header repair; no final
approval attaches to those earlier bytes. Report before append:
`01ae01e97672aab21bac24eaa3a6bb40a55ce31fdb7aa869c6ffe6299bac480f`.
No Directory.Build.targets exists at this level; no such input was assumed.

### Correctness / native lifecycle / proof strength

- **Cpp72–86,133–149:** promise readiness is intentionally produced while the
  real thread remains blocked on a native event. The UI observes WAIT_TIMEOUT
  on its native thread handle, marks failure, verifies retryDialog refusal and
  retains busy. After releasing the event it waits for WAIT_OBJECT_0, joins,
  consumes the future and closes the event before matching resolver completion
  and showing a dialog. Ready/get alone is not treated as physical thread exit.
  The synthetic promise is not a real WinHTTP resolver, and this observation
  does not execute AppMain's worker adapter.
- **Cpp91–116,151–179:** a live attached XamlRoot and actual ShowAsync handle
  are used. Opened and Closed events are observed, the SDK Closing deferral is
  retained, and Started refuses retry with busy retained. Matching dialog ticket
  completion happens only after Status Completed, exactly one Closed event and
  GetResults. Hide/cancellation never calls async Cancel/Close or completes a
  ticket at presentation time. Canceled/Error/Status/GetResults exceptions fail
  this fixture; they do not qualify unknown-drain product behavior as passed.
- **Cpp124–128:** the actual enabled button in the visual tree is invoked via
  ButtonAutomationPeer/IInvokeProvider, not a direct fixture callback or helper
  confirmation. This is synthetic SDK button automation, not physical keyboard,
  screen-reader output or a trusted web click. Microsoft's documented
  [ButtonAutomationPeer](https://learn.microsoft.com/en-us/windows/windows-app-sdk/api/winrt/microsoft.ui.xaml.automation.peers.buttonautomationpeer?view=windows-app-sdk-1.8)
  provides the Invoke pattern; actual execution is still pending here.
- **Cpp70–204:** six explicit sequential cases: current Primary, Close,
  cancel+Hide, auth-generation stale before Primary, stale while closing after
  Primary, and a real16000ms closing deferral. They require exact event/result/
  confirmation counts. Stale revokes owner retry applicability and signals the
  pending ticket without freeing it. In the positive case matching dialog drain
  permits new operation/work/request IDs, same event/context/original45s expiry,
  resolver deadline from recorded click+15s; old ticket completion cannot drain
  the new one. Case5's real closing delay must consume that budget, not reset it
  at poll. Close/Hide/stale/budget refusal produce no next ticket.
- **Cpp181–197:** new resolver is only a production helper ticket. The fixture
  deliberately does not dispatch it, then cancels/drains it as rejected dispatch.
  This is not a fresh GET, target validation, browser/native launch or handoff.
  Old failure does not become current again, and fixture code contains no Record.
- Application/window/timer/owner/operation storage is held by the test app while
  callbacks run. Normal case teardown is after real thread join/event close and
  dialog natural completion; there is no detached worker, second owner, captured
  product window, private/public macro or production seam. Watchdog25s and worker
  wait5s fail the fixture, not release product work. Fatal failure exits the test
  process rather than claiming successful cleanup/drain. No unexpected-shutdown
  lifetime proof is claimed for AppMain. Initial Loaded/bootstrap preparation
  also needs the runner's bounded setup/terminal detection; the tick watchdog
  starts only after Loaded and cannot prove a missing UI host eventually starts.

### Project / compile repair / runner contract

The small Release|x64 UseWinUI/WindowsPackageType=None project compiles unchanged
CalendarJoinOperation, DesktopApiClient UUID-path dependency and Sha256. It uses
the existing central pins/build policy, native App SDK bootstrap pattern and
normal libraries; no product project/solution integration or source edit was
submitted. Directory.Build.props retains /W4/error policy, stable SDK and
AsInvoker. No new external version/package source or runtime installer is added.

Main-reported initial249 restore0/build1: cppwinrt could not resolve WinUI's
Microsoft.Web.WebView2.Core.CoreWebView2 metadata. Final249b adds the already
central-pinned Microsoft.Web.WebView2 reference, WebView2UseWinRT=true and
WebView2EnableCsWinRTProjection=false like the product, plus full Collections/
Interop projected headers. Re-read shows no WebView construction, loader,
profile, cookie, auth or network call. This is a necessary metadata build input,
not a new runtime WebView test or authority. The build failure is retained as
main-reported history, not reviewer-reproduced RED or repaired-build PASS.

**Runner fence:** the source intentionally returns success marker **73**, not
ordinary exit0, only after all six cases; default/setup failure is2. A runner
must explicitly require the intended73 terminal code plus all six case records
and the exact source/EXE manifest. A standard CTest/nonzero-is-failure invocation
must not silently call this success, and a printed PASS alone is insufficient.
No runner was submitted/reviewed in this two-file scope, so that mapping and
actual process shutdown remain pending evidence, not a new source bug assumed
against an unknown runner. Synthetic Invoke is local to this UI object; no
SendInput/global keyboard/mouse injection is used. Real window activation makes
the fixture desktop-visible, not headless/background-safe. Missing interactive
desktop/runtime/root/button setup must be a failure, not a native proof skip.

### Boundary and verdict

Ponytail: **Lean already. Ship.** No deletion recommendation; one concrete
test app, stdlib thread/promise, native event/dispatcher/automation/deferral and
unchanged production helper, without framework/service/factory. The six cases
are bounded acceptance probes rather than speculative product flexibility.

Outstanding proof, not C/H/M source findings: final frozen hashes and repaired
MSVC build; actual six-case SDK results/terminal73/runner receipt; resource and
unexpected-shutdown coverage where claimed. Not covered: every context fence or
SDK fault, human keyboard/a11y/DPI, private AppMain offer/poll/auth/capture/reminder/
shutdown binding, actual resolver/launch/browser recovery, installed T119/T097 or
whole Feature200 acceptance. Source copied presentation never implies AppMain
integration. Only this reviewer-owned append changed; code/norm/tasks/markers/
Git/GitHub/VM/audio/user dirty work preserved. Re-read final source deltas when
main supplies the frozen receipt; no runtime PASS is asserted at this stage.

### Round249b/249c — frozen source and warning-policy rereceipt

Independent narrow reread: **C0 / H0 / M0 / L0; source APPROVED**. Full fixture
C++ reread confirms the previously reviewed semantics, including native thread
exit before resolver drain, actual SDK Closing deferral/Closed/Completed before
dialog drain, and the 16-second delay consuming the budget measured from Primary
click. No source finding or new production change is introduced by this receipt.

Current SHA-256:

- `NativeCalendarDialogTests.cpp`: `aed944baa3449e863d7d33122c6606c2cee6b678ac9af62053e2f270c1ab055a` (unchanged).
- `NativeCalendarDialogTests.vcxproj`: `bea57c9856f98531630fea4b41e3cd74a20188d754ba33126b9c69ca69cc3ffd`.

The project delta explicitly sets ClCompile `WarningLevel=Level4` and
`TreatWarningAsError=true`; it does not suppress warnings, change SDK/package
versions, or alter fixture behavior. Read-only removal of precisely those two
XML properties from stdout reproduces the earlier project SHA-256
`79109cfff8324a9ff13e68299b8cd0ecd0650087e54308553bd162bfbaa48c8e`.
Ponytail: **Lean already. Ship.** No deletion recommendation.

Main-reported evidence, NOT reviewer-executed: 249b actual SDK build exited 0
and produced all six asserted case rows, including the 16-second Closing case.
Its external receipt remains **FAIL / not accepted final PASS**, because
`Start-Process.ExitCode` was null. Printed rows/assertions do not repair an
unobserved process exit. The replacement external helper using
`System.Diagnostics.Process.Start` is outside this source scope and has not
been independently reviewed; fresh 249c rebuild/run is pending in this receipt.
Acceptance still requires an observed terminal fixture exit **73**, all six
case records, and the exact source/EXE manifest. Null exit is not success;
ordinary exit-0 test-runner conventions must not silently replace this fixture's
explicit exit-73 contract.

Pre-append report SHA-256 was
`f5b2a87d30fd437f5a763adec5a0ea24ca17d1eee7a3b777bae1da5edfe497d1`.
Only this reviewer-owned report append changed. No VM/build/test/Git/source/
norm/task/marker/audio changes or runner execution were performed. This remains
synthetic SDK + production-helper source approval, not private AppMain binding,
human/a11y, installed acceptance, or T119/T097 closeout.

### Round249c — final frozen static approval and main-reported terminal receipt

**APPROVED — C0 / H0 / M0 / L0**, bounded to the submitted synthetic native
dialog fixture and its project. Fresh canonical SHA-256 verification retains
C++ `aed944baa3449e863d7d33122c6606c2cee6b678ac9af62053e2f270c1ab055a`
and project `bea57c9856f98531630fea4b41e3cd74a20188d754ba33126b9c69ca69cc3ffd`.
The project was personally reread in full: explicit ClCompile `Level4` (`/W4`)
and `TreatWarningAsError=true` (`/WX`) remain present, with no warning suppression
or package/version change. The exact unchanged C++ retains the independently
reviewed physical worker-exit, natural SDK terminal, cancellation, stale context,
and click-budget semantics described above. Ponytail: **Lean already. Ship.**

Main-reported, not reviewer-executed: Round249c restore=0, build=0, observed
`.NET Process` terminal exit=73, all six bounded SDK cases passed, durable
`C:\Temp\graf-f200-round249c-dialog.json` reports `phase=passed`, `terminal=true`;
EXE SHA-256 `390da463d20e3e4975f77db654888d18c8a911a11d794c2f221262be548ef2ca`.
This is a reported successful final fixture receipt, distinct from the retained
249b null-exit external receipt failure. The external runner, durable JSON and
EXE were not independently inspected or executed here. The same-source repeat
was announced as running; no repeat PASS is asserted in this appendix.

Requested quickstart addition is not yet present at this read: current
`quickstart.md` SHA-256 is unchanged
`1065b1970125f2ea7cc323c0177d07485e34a339a6b7195df4af9aa65a5cb683`;
no `249` or `NativeCalendarDialog` entry was found. No proposed text is therefore
approved by this receipt; it can be reviewed when submitted without changing
the approved source verdict.

Only this report append was written. Static approval and main-reported SDK
fixture success do not establish private AppMain integration, human/a11y/DPI,
installed acceptance or whole-feature acceptance. T119/T097 remain open. No
VM/build/test/Git/GitHub/source/norm/task/marker/audio operations were performed.

### Round249 — bounded quickstart guidance review

**APPROVED — C0 / H0 / M0 / L0**, scoped to the new quickstart subsection
“Настоящее окно повторной попытки T119 — Round249”, lines 627–674 at this read.
Current quickstart SHA-256:
`5cc51e712a6b1543771aab46ba922b3f90768f177e0e274d548df4a8eb6681d2`.
Fixture C++ and project hashes remain the approved `aed944baa3449e863d7d33122c6606c2cee6b678ac9af62053e2f270c1ab055a`
and `bea57c9856f98531630fea4b41e3cd74a20188d754ba33126b9c69ca69cc3ffd`.

Personally read the entire added subsection. It requires an interactive
desktop/runtime, serial window testing, standalone Release/x64 MSBuild restore
and build with checked exits, and a retained `.NET Process` with checked start
and terminal exit. Its EXE path matches the existing Directory.Build.props
OutDir. The 60-second external watchdog throws an explicit failure after forced
termination; it is not represented as natural completion or product drain.
Success requires actual exit 73 plus six case records, not a printed PASS alone.
For this exact fixture, exit 73 is only assigned after its six sequential
asserted cases; the documented count check is consistent with that source.
Output is bounded to this synthetic fixture, not a general runner contract.

The explanation accurately distinguishes SDK button Automation Invoke from
human keyboard/screen-reader acceptance, worker future readiness from native
thread exit, Closing deferral from completed SDK lifetime, and a new ticket from
HTTP execution. It expressly leaves AppMain binding, SDK error/unknown/failure
paths, auth, fresh target, launch, installed MSIX, audio/storage/hardware/release
acceptance outside this proof. No new product schema or lifecycle requirement
is introduced by the validation instructions. No concrete fix is required.

The instructions were inspected, not executed. Round249c remains main-reported
runtime evidence; the announced repeat remains pending here. Only this report
append changed. No quickstart/norm/source/task/marker/Git/GitHub/VM/build/test or
audio writes/actions were performed. T119/T097 remain open.
