# T119 Round238: bounded host adapter source review

Дата: 2026-10-05. Независимый reviewer-owned результат.

**REQUEST CHANGES — C0/H0/M1/L0.** Единственный обнаруженный source blocker —
безусловная отмена текущего pending request из exception path старого dispatch
после reentry. Source approval этих bytes не выдан.

## Область и основание

Canonical repo `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`,
branch `codex/200-windows-followup`, HEAD
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1` подтверждены read-only. Dirty работа
main сохранена; reviewed hashes относятся к файлам, не к содержимому HEAD.

Лично прочитаны code-reviewer и ponytail-review. Проверены текущие Host/Bridge
headers, Bridge implementation, изменённые Host parser/gate/reply/lifecycle
функции и их native event callers, CalendarJoinHostTests и CMake registration.
Прочитаны прямые AppMain/CabinetWindow attach/close/recreate callers в рамках
проверки отсутствия owner attachment и порядка host teardown. Существующие
FR-006/bridge §10/plan wire и gates wire5/0, operation8/0, launcher5/0 — основание
проверки, не доказательство реализации. Полоса — bounded source review
существующего high-risk T119; clock/storage/whole-feature audit не проводился.

Первоначально сверены все шесть предоставленных hashes. Во время review main
перенёс initial resolving delivery внутрь try и добавил delivery-throw regression.
Ниже зафиксированы повторно прочитанные актуальные bytes после этого изменения;
первый Host.cpp `1ffe4230a2e06358e58e632ff5c9e21d69da66f308314d8852a930870bc6db83`
и test `42a20df6970126d273e82febe8448136b70464674152464f7611260f1253fd38`
сохранены только как история, не final source receipt.

## M1 — старый exception path отменяет новый request после reentry

Точное место: `apps/windows/RecApp/Web/WebView2Host.cpp:1090`,
`handleCalendarJoinMessage` catch вызывает `cancelPendingCalendarJoin()` без
сравнения с исходным `request`.

Достижимая последовательность без нарушения public callback contract:

1. Host принимает request1, сохраняет его pending, выдаёт resolving и вызывает
   concrete join callback с копией request1.
2. Callback синхронно выдаёт допустимый terminal для request1 через
   `replyCalendarJoin(request1, {failed, launchFailed})`. Host перед reply
   освобождает document pending; UUID1 остаётся consumed.
3. Во время reentry принимается request2 того же current document; он становится
   новым pending и его join callback dispatch происходит нормально.
4. Callback request1 затем бросает исключение. Внешний catch request1 отменяет
   **request2**, вызывает cancel callback для него и отправляет его cancelled.

Тот же root cause доступен при initial resolving delivery, которая отменяет
request1, принимает request2 и затем бросает исключение. Проверка matching IDs
перед join dispatch на строках1086–1087 защищает normal return, но не catch.
Нарушен accepted invariant: старый callback не изменяет новую операцию.
Production commands пока denied, поэтому находка не означает уже включённый
пользовательский launch; она блокирует именно source acceptance этого adapter.

Минимальное исправление: exception cleanup может отменять только pending,
совпадающий с исходным request по document generation/nonce/eventId/requestId.
Не нужен новый owner/service/factory, восстановление consumed UUID или глобальный
reentry запрет. Нужна адресная regression: завершить/отменить1 → принять2 →
throw старого callback; cancel2/reply2 cancelled не появляются,2 остаётся pending
и может получить допустимый opening/terminal. Existing simple throw и resolving
reentry tests проверяют эти события по отдельности, не указанную комбинацию.

## Подтверждённые границы кода

- Default/partial handlers: Bridge flag default false; Host setter отключает
  команды перед сменой handlers и включает только при обеих callbacks. Поиск
  actual production callers не нашёл AppMain/Shell attachment. Shim не добавляет
  calendar handler. Наличие parser само по себе не включает native authority.
- Original JSON: Host:185–219 вычисляет strict owned calendar payload до SDK
  Parse; calendar command требует успешного strict результата и совпадения
  envelope origin с native Source origin. WebMessageReceived:1655–1675 ограничивает
  весь raw message64KiB, проверяет Source/core/current/native route, затем передаёт
  original payload, не SDK Stringify. Decoder reuse проверяет decoded duplicates,
  Unicode и root/payload depth отдельно; прежние legacy handlers не заменены.
- Host current gate: alive, ready, nonzero matching generation, непустой matching
  nonce, current=committed и exact allowed meetings. Общий Bridge дополнительно
  проверяет protocol/version/direction/origin/nonce/messageId/payload limits и
  optional command enablement. Typed UUID не считаются auth proof.
- History: canonical UUID replay перед cap, максимум1024 без eviction; busy
  consume, cap-refused повтор только notReady без history growth. Cancel требует
  matching event/request; late cancel не адресует следующий flight. Handler
  replacement не сбрасывает history. New document revoke очищает correlation,
  но не доказывает actual native work drain.
- Lifecycle: beginDocumentNavigation отменяет до committed clear/generation change;
  close — до alive=false/generation change; process failure — до generation change;
  fail и setRuntimeState(nonready) — до nonce/bridge/script revoke. attach вызывает
  close старого host lifetime; bootstrap revoke предшествует nonce rotation.
  AutomaticallyRecoverable не объявлен новым document boundary. Отмена вызывает
  старый cancel callback и ограниченный pinned terminal, не actual completion.
- Reply: matching generation/nonce/event/request, resolving→opening, handoff только
  после opening; terminal снимает pending до reentrant delivery и не оживает.
  Native serializer использует request nonce/UUID и фиксированные literals, не
  новый nonce, URLs/tokens/title/exception. Unknown state не проходит transitions;
  unknown reason у failed/cancelled отображается безопасным literal cancelled,
  не arbitrary value. Opening/handedOff с reason!=none отвергаются.
- Исправление main initial delivery throw реально присутствует в текущем try;
  simple delivery exception теперь проходит cancellation cleanup. Это отдельный
  исправленный путь, не закрытие M1 с заменённым pending. Cancel callback/delivery
  exceptions поглощаются без logging private payload. Host здесь не доказывает
  physical cancellation/exit resolver, SDK или будущего dialog.

## Проверки и незакрытые proof boundaries

Тесты лично прочитаны: default/partial denial, transitions/no terminal revival,
canonical IDs, replay/busy/cap, bad source/nonce/version/direction/payload,
route denial, navigation/close/process/auth/handler invalidation, new nonce/stale
reply, normal resolving reentry, handler throw и новый delivery throw.

Main сообщил portable45/45 PASS23.03s для исходной submission; после delivery
fix rerun активен. Native49 и full SDK app build ещё не имеют подтверждённого
финального receipt в этой проверке. Здесь тесты/build/VM не запускались; pending
jobs не называются PASS. Новая правильная AEC layout сама не является build PASS.

CMake host fixture вызывает actual common gate, но не `parseEnvelope` и native
reply lambda под `_WIN32 && GRAF_WINDOWS_APP_SDK`. Поэтому portable/native CMake
counts не доказывают SDK original-envelope/serializer event boundary. Её source
flow прочитан; Windows full solution compile и последующая native event/installed
валидация остаются отдельными доказательствами, не новым whole-feature scope.
Frame fixture с отличающимся source URL не является installed same-URL iframe
proof. AppMain common owner, trusted shim/HTMX, actual worker/dialog leases,
auth/launcher/Record/receiver/installed acceptance на этом этапе не заявлены.

Ponytail: лишнего service/factory/parser/dependency в bounded diff не найдено;
existing strict decoder/native SDK/set/std::function reuse сохранён. Минимальная
matching identity проверка для M1 — необходимая correctness граница, не bloat.
`net: -0 lines possible.` Это не разрешение shipping при незакрытом M1.

## SHA-256 актуально рассмотренных bytes

Пути относительно `apps/windows/`:

| Файл | SHA-256 |
| --- | --- |
| RecApp/Web/WebView2Host.h | `4023715875a4b638eec6b1f42cb7049dd9b339c30c337b7f3c0c5c7d1ae0cbad` |
| RecApp/Web/WebView2Host.cpp | `44acf6fde00d50abc860bad2b55f2e37f2beb90f71024fc580573c574e075974` |
| RecApp/Web/WebViewBridge.h | `c542ef246439a8218d1860a092f8f6bf9b2f8a9c7dd8156a09652c248725ac4f` |
| RecApp/Web/WebViewBridge.cpp | `2e4ecb0ece261cc9308b50f26303401a67494b858fd679da9e89d741c615316b` |
| Tests/GrafWindowsContractTests/CalendarJoinHostTests.cpp | `4862240ba51632e2bd918aa19a086c7d9bdc8757878a60d13e0cf3e4f96b4111` |
| CMakeLists.txt | `38de3178085b1bcb4b38601bab2130656088dfa72f1285a867a9962e7faf36fd` |

Existing wire-source historical report hash повторно совпал:
`1d6b704a479f992f66512fd3ef653c899481da8731028d9324e2d61f4a99e5f5`.
Reviewer записал только этот новый report; код/нормы/tasks/checklist markers/
Git/GitHub/старые reports и чужую dirty работу не менял.

**Terminal: REQUEST CHANGES C0/H0/M1/L0; M1 требует matching exception cleanup.**

## M1 closure — bounded source recheck, 2026-10-05

**Текущий source verdict: APPROVED C0/H0/M0/L0; M1 CLOSED.**
Первый REQUEST CHANGES, контрпример и исходные hashes выше сохранены как история.
Этот appendix обновляет verdict только по исправлению M1; не расширяет область
host adapter и не превращает pending validation в PASS.

Лично перечитаны точный private helper и три его call sites, declaration в Host.h
и обе новые regression-последовательности. Code-reviewer и ponytail-review снова
прочитаны; broad source audit/build/VM не повторялись. Canonical HEAD свежим
read-only чтением остаётся `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`.

`calendarRequestPending` (Host.cpp:1032–1035) проверяет существование pending и
все четыре поля исходной identity: documentGeneration, nonce, eventId, requestId.
Это private noexcept сравнение без allocation/I/O либо нового authority.
`replyCalendarJoin`:1020 сохраняет прежнюю полную matching проверку через helper
и отдельный current guard; pre-dispatch:1088 теперь использует тот же полный
matching guard вместо только UUID проверки. Главное исправление — catch:1092
вызывает cancel только при `calendarRequestPending(request)`.

Таким образом после завершения/отмены1 и принятия2 старый catch1 видит mismatch
и не меняет pending2, не вызывает cancel2 и не выдаёт ему cancelled. При simple
throw без замены pending matching1 по-прежнему отменяется; исправление не теряет
предыдущий delivery-throw cleanup. Generation/nonce сравнение также исключает
совпадение UUID между разными документами. Correlation history не сбрасывается
и прежние replay/default-denial/lifecycle guards не изменены этим исправлением.

Tests:204–230 покрывают оба root paths: old delivery cancel1→accept2→throw и
old owner terminal1→accept2→throw. Проверяют отсутствие дополнительной отмены,
identity принятого2 и успешные opening/handedOff для2 после возврата из старого
catch. При неверной безусловной отмене последние два reply не могли бы пройти
matching pending gate. Main сообщил focused RED89287 на старом catch; это
owner-reported test evidence, не самостоятельно запущенная reviewer проверка.
Ponytail: один переиспользуемый private identity helper закрывает root cause без
нового framework/service/factory и убирает разнобой трёх проверок. Лишних слоёв
в closure не найдено; `net: -0 lines possible.`

### Fresh current source hashes

Пути относительно `apps/windows/`:

| Файл | SHA-256 |
| --- | --- |
| RecApp/Web/WebView2Host.h | `37e9ca1d082a21eead2e862904647ca816472fe5ef63ef2ed7090f61f9bbf0af` |
| RecApp/Web/WebView2Host.cpp | `9dcc3cf218532c3aed461777b4f0e9eb03ba28f8a65b0210ff7f00d843640f1a` |
| Tests/GrafWindowsContractTests/CalendarJoinHostTests.cpp | `7c789cee2d48c766ae5717e17835fe5027770a7ffbaf57e8a271b5b62479cbcd` |
| RecApp/Web/WebViewBridge.h — unchanged | `c542ef246439a8218d1860a092f8f6bf9b2f8a9c7dd8156a09652c248725ac4f` |
| RecApp/Web/WebViewBridge.cpp — unchanged | `2e4ecb0ece261cc9308b50f26303401a67494b858fd679da9e89d741c615316b` |
| CMakeLists.txt — unchanged | `38de3178085b1bcb4b38601bab2130656088dfa72f1285a867a9962e7faf36fd` |

Main сообщил старый Native49 PASS422.37s; это только historical receipt до closure.
Final portable/native49 reruns активны, SDK build29557 относится к старому Host
hash и не доказывает final bytes. Их результат здесь не принят как PASS.
Остаются отдельными full SDK compile/native event boundary validation и будущие
shim/AppMain common owner/actual drain/installed auth/launch/Record gates из
исходного отчёта. Source closure не является функциональной приёмкой T119.

Reviewer изменил только этот append-only report. Старые findings/reports, код,
нормы, tasks, markers, Git/GitHub и чужая dirty работа сохранены.
**Terminal current source: APPROVED C0/H0/M0/L0, M1 CLOSED в hashes выше.**

## Round244 — host/account user-time source review, 2026-10-06

**REQUEST CHANGES: C0/H0/M1/L0** для bounded user-time integration ниже.
Это новое Round244-M1, не повторное открытие historical Round238-M1.
Canonical worktree `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`;
branch/HEAD по submission `codex/200-windows-followup` /
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`, Git не запускался.
`code-reviewer` и `ponytail-review` лично прочитаны полностью. Прочитаны текущие
affected host declarations/core/SDK cookie+ExecuteScript callbacks/lifecycle,
AppMain native account/token mutation and binding paths, new fixture cases;
не проводился повторный аудит всего AppMain, capture/storage или Feature200.
High-risk lane и approved Round243/244 requirements сохранены. Skills применены
без Git/preflight/build: пользователь ограничил работу чтением и этим отчётом.

### Round244-M1 — old auth-handler exception can clear newer time context

**Medium, blocking this slice:** `RecApp/Web/WebView2Host.cpp:2072–2074`.
SDK cookie completion копирует `authSessionHandler_` и допускает его reentry
(комментарий2068 прямо учитывает navigation/destruction). Normal-return path
2076–2079 повторно проверяет generation/nonce/runtime. Но catch2073 проверяет
только old `alive` и вызывает `bindUserTimeAccount({}, {}, {}, {}, 0)`.

Конкретная последовательность: cookie callback документа1 вызывает handler;
handler/nested UI подтверждает документ2 и новую native binding/context, после
чего старый handler выбрасывает исключение. Host остаётся живым, поэтому catch1
очищает binding и preference2, повышает revision и делает callback2 stale.
Это нарушает plan3–4/data-model: stale completion не стирает newer context.
Даже без нового документа смена binding/revision внутри handler не защищена
одним `alive`. Здесь нет расширения Join/auth authority; дефект — destructive
stale presentation reset и потеря подтверждённого preference.

Минимальное исправление: invalid-result cleanup должен быть привязан к исходному
cookie/document и context identity, а не к одному alive. Проверить исходные
generation/nonce/source и binding/revision перед exception reset; новый контекст
не трогать. При ordinary throw без смены контекста сброс сохранить. Использовать
existing fields/helper pattern, без нового service/factory. Нужны regressions
old handler→new document/binding→throw (new preference/revision сохраняются),
matching ordinary throw (fallback), close/self-destroy (нет доступа к умершему
host). Текущие tests113–195 напрямую вызывают core read/cookie methods и этот
SDK-only catch не исполняют; их PASS не опровергает finding. Counterexample
получен чтением control flow, не reviewer-executed runtime test.

### Подтверждённые bounded свойства / границы

- Host444–480 принимает только trusted-origin/native UUID owner/workspace и
  token, затем требует ready/main committed URL/nonce/cookie generation/token,
  allowed route; billing action отказ469 переиспользует safeRecoveryUrl.
  NativeSettings navigation остаётся отдельным native-window path633/AppMain1841.
- Refresh483–494 фиксирует owning snapshot, помечает attempted revision до
  dispatch, копирует callback и alive; ordinary callback throw применяет invalid
  только через matching read. Повторное bind/cookie не запускает duplicate read.
  Read507–516 строгий/raw-owned decoder, owner/workspace/document equality,
  native formatter zone validation, current invalid fallback, duplicate/stale
  completion refusal и same-page confirmed-document staging.
- SDK2165–2187 читает только main document meta, не cookies/forms/webcommand;
  marshals completion в DispatcherQueue, проверяет alive/context/source до
  GetResults/application. UTF16 size gate ограничивает conversion, затем strict
  decoder ограничивает raw UTF8 2048. Нет второго HTTP client, persistence,
  token/metadata/URL logging или нового Join разрешения.
- Navigation/setRuntimeState/close очищают time context/cookie proof/reader;
  captured old alive отбрасывает callbacks после close/reattach. Cookie normal
  return rechecks alive первым после copied auth handler, потом document fence.
  M1 касается именно exception path, не этих normal guards.
- AppMain2716–2724 bind берёт existing capture.currentAccount/authGeneration/
  token. Capture645–653 сбрасывает confirmed account при token change;
  account result953–975 generation-bound. **Текущая дополнительная строка3885**
  лично прочитана: оба callsites setter —1898 и3886— предварительно очищают
  time binding1891/3885. Это synchronous invalidation, не обещание timer cadence.
- Tests113–195 покрывают cookie-before-account/account-before-cookie, duplicate
  suppression, generation/token/owner/workspace/origin changes, invalid/current
  fallback, stale result after newer preference, nonce/source/lifecycle/routes.
  Fixture native reader не доказывает actual SDK apartment/reentry boundary.
  Tray labels/EndMenu integration и installed scenarios остаются следующими
  стадиями; здесь не заявлены actual menu/Join/Record/full T119 acceptance.

### Fresh exact source receipt

Пути относительно `apps/windows/`. Initial AppMain submission `0c80d45d…`
не final receipt: во время review main добавил synchronous token reset3885.
Updated AppMain ниже перечитан в affected paths; остальные три hashes unchanged.

| Файл | SHA-256 |
| --- | --- |
| RecApp/Web/WebView2Host.h | `17365420fe6b243737eb2ec29c25a8a0193db8f7b6dbf7cdb7b6cdd9ff8b3b96` |
| RecApp/Web/WebView2Host.cpp | `65b81862469c1c9bced21ae3931a9b5968b4f1fbc0a403a2b879d24aae660713` |
| RecApp/AppMain.cpp | `875bca5d3e4fba2ad1273bfd52f9becd2a282140b0b6f91b3efa67f53d95b497` |
| Tests/GrafWindowsContractTests/CalendarJoinHostTests.cpp | `0e12a0c77233049843c1f677297bc24286cb279a8284c5f85093757e56d5a5a8` |

Norm hashes personally rechecked unchanged: spec `b411bfb620e9d571422f9c423b0ae193ed70e87303d08e84a4b9844e32f81658`;
plan `527e660d9e1682e7a0f0a79118ea4bab38d4c174542b49c0113f571528a5b89c`;
model `8dd54012c3bfe4003cd18db98ebc67e0b7730cbbdfb6523b881cce4cdc15ec19`;
bridge `21bffa56631901952ae778871f26785522d839eafc8afb9942b488ff22bbd0fa`;
quickstart `1065b1970125f2ea7cc323c0177d07485e34a339a6b7195df4af9aa65a5cb683`;
research `0e7659d4cf5136d392bde28cb273c6ca0be6af2ac3eca50e23a617e1af129522`;
tasks `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f`.
Requirements18/0 остаются requirements-quality gate, не source approval.

Main сообщил compile/runtime RED и focused portable1/1, затем core45/45
22.52s/native focused4/4 1s; reviewer их не запускал, exact run-byte binding
здесь отдельно не проверял. Stale ctest после failed compile не evidence;
SDKcompile pending не объявлен PASS. Ни один receipt не закрывает Round244-M1.

Ponytail (отдельно от correctness): existing host/parser/formatter/dispatcher
reuse, private owning snapshot и один attempted revision оправданы требованиями;
лишних dependency/interface/service не найдено. `Lean already. Ship.` относится
только к форме реализации, не permission при M1. `net: -0 lines possible.`

Only write — этот append; historical findings сохранены, code/norm/tasks/markers/
Git/GitHub/VM/build/tests/audio не менялись/не запускались.
**Terminal: C0/H0/M1/L0, REQUEST CHANGES; exact source slice не одобрен до M1 closure.**

### Round244 supplemental browser fixture receipt

По дополнительному submission лично прочитан только новый extraction12–13 и
metadata case47–66 в `Tests/GrafWindowsContractTests/CalendarJoinShimTests.cjs`,
SHA-256 `0adc4d1c8c87168312d624e9e016d8471ef14e23107152f967f78b309d7efb9b`.
Fixture извлекает actual native metadata script из Host.cpp, ожидает точные
five returned fields, main-document Kathmandu вместо divergent iframe,
throwing document.cookie/GRAFTime getters, empty zone и missing user.
Fresh boot66 изолирует остальные Join tests. Новых findings в этом добавлении
нет; это source assessment assertions, не reviewer-run Chromium/WebKit PASS.
Script case не выполняет SDK cookie/auth handler и не закрывает Round244-M1.
Main подтвердил current AppMain875bca5d…; первый SDK BUILD0 относится к прежнему
AppMain, свежий build/browser runs pending. Terminal остаётся C0/H0/M1/L0.

### Round244 — final independent source status / main validation receipt

2026-10-06: лично повторно прочитаны catch2072–2074 и normal fence2076–2079;
сверены все четыре source hashes и browser fixture hash выше — unchanged.
Round244-M1 всё ещё присутствует в Host.cpp65b81862…; source review завершён,
не ждёт новых test jobs для выдачи решения: **C0/H0/M1/L0, REQUEST CHANGES**.
Для закрытия требуется narrow exception-fence repair и regression, а не ещё
одна сборка unchanged bytes. Прочих C/H/M дефектов в заявленном срезе не найдено.

Main-reported receipt (не reviewer-executed): Chromium+WebKit CalendarJoinShimTests
PASS terminal6190/e680c0, fixture `0adc4d1c8c87168312d624e9e016d8471ef14e23107152f967f78b309d7efb9b`;
SDK53596 terminal0. Main выполняет отдельный two-NTFS-source hash/timestamp
verifier/rebuild против stale-object overlap, затем serial CoreTests.
Этот verifier/final CoreTests здесь pending; raw logs/objects/NTFS copies
reviewer не проверял. Browser PASS проверяет script, не auth-handler catch;
SDK BUILD0 доказывает сборку по сообщению main, не отсутствие M1/runtime parity.
Старые pending/failed/historical receipts сохранены. Installed/menu/T119 не закрыты.
Only write — этот report append, без новых jobs или расширения review scope.

## Round244-M1 closure — exact current source, 2026-10-06

**APPROVED bounded source: C0/H0/M0/L0, Round244-M1 CLOSED.** Historical
finding/REQUEST CHANGES и old-byte receipts выше сохранены без переписывания.
Это narrow rereview M1 repair + current five-file receipt, не новый whole-feature
review. `code-reviewer` и `ponytail-review` снова прочитаны полностью;
Git/build/VM/tests не запускались.

Лично прочитаны private declaration Host.h315–316, helper Host.cpp519–536,
actual SDK caller2087–2096, fixture authTime48–50 и regressions119–136;
перепроверены unchanged AppMain token invalidation paths и browser metadata case.

- Helper519–524 сначала фиксирует old shared alive и проверяет generation/nonce,
  ready/current/committed URL и native bridge route. Callback копируется до вызова;
  nonce/URL/token переданы owned strings, не views на изменяемые host members.
- Exception fence529–531 требует old alive, original generation/nonce/current+
  committed URL, runtime и captured display revision. Любой account/auth/token
  binding change или accepted preference меняет revision; navigation меняет
  generation/nonce, close/reattach завершает captured alive lifetime. Старый catch
  больше не очищает newer binding/preference. Matching ordinary throw по-прежнему
  вызывает empty native binding и возвращает false, без dispatch cookie/read.
- Normal return534–535 проверяет alive первым, затем reconciled и document identity.
  Revision здесь намеренно не запрещает успешное account reconciliation handler:
  дальнейший read использует уже current native binding/cookie-token match.
  SDK2089 вызывает этот же helper;2092 **заново** читает actual core.Source после
  handler, затем reconcileUserTimeCookie проверяет current+committed URL/token.
  Requested/captured source не подставляется вместо actual native source.
- Outer SDK catch2094–2095 также fenced old alive/generation/nonce/ready/revision,
  поэтому exception после смены контекста не выполняет stale invalidation.
  Parsing/current checks/no authority/no persistence/logging из initial review
  не менялись. Нового service/интерфейса или публичного test API нет.
- Tests119–130 реально вызывают production helper через friend fixture. Четыре
  branches: same document/new auth generation; same URL/new document; close+
  recreate; same binding/new accepted preference. Каждый принимает UTC внутри
  handler, затем throws; assert129 требует сохранить UTC. Old alive-only catch
  стирал preference в этих случаях (кроме already-dead captured lifetime).
  Matching throw131–136 требует fallback, рост revision и отсутствие нового read.
  Это source-verified regression paths; actual destruction/SDK event apartment
  исполнение не объявлено independently tested.

### Exact five-file SHA-256 receipt

Лично сверены canonical bytes; пути относительно `apps/windows/`:

| Файл | SHA-256 |
| --- | --- |
| RecApp/Web/WebView2Host.h | `44addeaf08b826d46db0b144f51da5079b96b3fd356ca4c610f92de41181e1e6` |
| RecApp/Web/WebView2Host.cpp | `ffd757e33314ae213de737ed33143ee2af6f9bde8f3658bd38717132712b691c` |
| RecApp/AppMain.cpp — unchanged | `875bca5d3e4fba2ad1273bfd52f9becd2a282140b0b6f91b3efa67f53d95b497` |
| Tests/GrafWindowsContractTests/CalendarJoinHostTests.cpp | `3187d87be93a7b325c37f2222313ec028581f920ce7cc3ce3a01fba88eedf346` |
| Tests/GrafWindowsContractTests/CalendarJoinShimTests.cjs — unchanged | `0adc4d1c8c87168312d624e9e016d8471ef14e23107152f967f78b309d7efb9b` |

Main-reported controlled RED29708/6b5529 exit8 (extracted helper with old catch,
UTC assertion failed), then GREEN17043/86916a focused1/1 PASS0.41s. Reviewer
не запускал эти tests/не вычитывал raw run logs. Final native-focused/fullportable/
SDK reruns pending на submission; предыдущие PASS/SDK53596 не receipt новых
Host/test bytes и здесь не объявлены final validation.

Ponytail: один private helper извлекает actual production dispatch для regression;
existing native fields/revision закрывают identity без нового framework/factory.
`Lean already. Ship.` — только complexity assessment, `net: -0 lines possible.`
Remaining native/SDK execution, staged tray labels/EndMenu и installed/full T119
acceptance отдельны. Requirements18/0 не новые implementation markers.
Only write — этот append; code/norm/tasks/Git/GitHub/audio/чужая dirty работа
сохранены. **Terminal source approval относится только к пяти hashes выше.**

## Round245 — isolated safe upcomingRows projection source review

2026-10-06. **APPROVED bounded source, C0/H0/M0/L0.** Scope только
UpcomingMeetingRow/MeetingReminderPresenter::upcomingRows и new testUpcomingMenuRows;
это отдельное заключение, не продолжение host/account approval и не tray/owner Retry
integration acceptance. Canonical worktree прежний; Git не запускался.
`code-reviewer` и `ponytail-review` лично прочитаны полностью; applied correctness/
privacy/edge-case/minimality review без preflight/build/VM/test jobs.

### Лично проверенный поток

- Presenter.h9–14/27–35 возвращает owning vector safe labels + frozen event/epoch/
  enabled. Метод не принимает auth, не запускает I/O/launch/Record, не назначает
  action expiry. Preferred zone supplied caller должна быть accepted native account
  context; её binding не устанавливается проекцией.
- Presenter.cpp98–107 отвергает nonfinite now/unavailable snapshot и reuse model
  upcoming272–279 (sort startsAt/eventId, prefix12). Native upcomingTime вызывается
  с server showTime/allDay; formatting refusal возвращает nullopt всей projection,
  не fabricated time. No quiet/reminder/card/capture фильтров. Empty available
  snapshot даёт empty vector, не unavailable sentinel.
- Title108–116 проверяет server showTitle/titleAvailable до decoding/display.
  Private/hidden/unavailable остаются «Встреча»; empty/whitespace-only available —
  «Без названия». Invalid UTF8/oversized internal title fallback generic; API
  decoder уже ограничивает title4096 и strict calendarString. wide helper использует
  native strict UTF8 conversion на Windows и scalar-complete bounded-input decoding
  portable (invalid leading/continuation/overlong/surrogate/range refusal).
  NBSP/thin/ideographic spaces входят в blank set; nonblank title не trim-ится.
- Current/enabled117 reuse model.upcomingCurrent281–288: available full snapshot,
  matching epoch/event/starts/ends/link/URL, finite/not ended and safe HTTPS policy.
  Отсутствующая/unsafe/expired ссылка даёт visible disabled row. Matching не зависит
  от title/allDay/presentation flags; stripping title118 не разрушает frozen target
  identity. Row не cached launch grant: future admission требует fresh current,
  expiry/account checks и resolver, не только enabled=true.
- Title118 очищается и titleAvailable=false в target; displayed safe title остаётся
  только в owning label. No private title/URL logging/persistence/diagnostics.
  Raw frozen meetingUrl хранится только ephemeral identity, не передаётся странице
  и не доказывает launch authority. Full text остаётся для последующей native
  accessibility; menu escaping/width/DPI и lifetime здесь не реализуются/не приняты.

Narrow current own-Mac read: Shared CalendarContextModels.safeDisplayTitle262–271
проверяет whitespaceAndNewlines только на empty, затем возвращает исходный candidate;
CalendarTray264–273 использует server flags/generic title,328–335 allDay/account
timezone. Это чтение current файлов, не independently retrieved pinned Git blob;
pinned721b5125… comparison receipt принадлежит main. Здесь не заявлена exhaustive
all-scalar Foundation CharacterSet parity по одной whitespace fixture.

### Tests / exact three-file receipt

Лично прочитан test63–142: unavailable vs empty; unsorted14/equal starts prefix12;
safe Cyrillic/ampersand label; title removed from target; local quiet/reminders/
showTitles and active capture independence; endsAt boundary disabled; private,
ASCII/Unicode blank, allDay, missing/unsafe link, invalidUTF8, title4096;
unknown-zone/nonfinite refusal; server hidden flags; failed refresh/account switch
invalidate frozen current; stale epoch update rejected. Tests register via main594.
No concrete C/H/M/L findings in this slice. Native formatting construction/SDK
execution remains separate from source assertions and portable adapter proof.

| Файл — относительно apps/windows/ | SHA-256 |
| --- | --- |
| RecApp/Shell/MeetingReminderPresenter.h | `ebbc1eafe1ad80e1feccaed3db6188b66170403db53e70119efb856006f71c8e` |
| RecApp/Shell/MeetingReminderPresenter.cpp | `f24bee159c929b7b780844d83e22e86b8a76469ee2df2777bbe3d1b3560afee5` |
| Tests/GrafWindowsPackageTests/RecordingIndicatorTests.cpp | `f58b66b0f035f6acf58bfc3c2040d825bbcfdd5c3951e4ad0e98e29660b9b46e` |

Hashes лично сверены повторно; approval только этих exact bytes. Main-reported
test-first stub compile + RED80004/5da708 exit8 rows-size12 assertion, focused
final run pending на submission. Reviewer tests не запускал/raw logs не проверял;
не записывает pending как GREEN. Existing requirements18/0 не implementation proof.

Ponytail: reuse upcoming/sort/prefix/current/time/wide, одна простая owning row
structure, no duplicate client/validator/service/factory. `Lean already. Ship.`
`net: -0 lines possible.` Only write — этот append. Старые findings/receipts
сохранены; norms/code/tasks/markers/Git/GitHub/VM/build/audio не менялись.
Tray rows lifetime/EndMenu, AppMain account/time wiring into labels/common menu
Join admission/Retry и installed/full T119 acceptance **не одобрены этим разделом**.

### Round245 projection — main-reported portable validation receipt

2026-10-06. Exact three projection hashes выше лично пересверены unchanged;
source verdict остаётся APPROVED C0/H0/M0/L0, нового source review нет.
Main сообщил terminal focused51049/7c76fb exit0, 1/1 PASS0.49s; full portable
86068/164b8e terminal0, build +45/45 PASS23.18s. Это main-reported execution,
не reviewer-run: raw logs/build artifacts reviewer не проверял, tests не запускал.
Исторический stub RED/pending на prior submission сохранён; этот receipt добавлен
после завершения portable, не задним числом заменяет его статус.

Native49/SDK новые runs74087/2209 по сообщению main всё ещё running; actual
Presenter/Host и AppMain compile log lines не terminal test/build PASS. Старый
owned26912 macprl channel terminated143; диагностика main сообщает отсутствие
owned remote SDK process/old EXE hash и новый frozen mirror. Reviewer VM/processes/
EXE не проверял; interrupted run не объявлен успешным или автоматически равным
новому. Native/SDK final receipt, tray/owner integration и installed/T119 open
остаются отдельными. Only write — этот receipt append; новых jobs/VM действий нет.

## Round246 — independent MAIN-only source review: menu admission/source/expiry/projection

2026-10-06; fresh source receipt `2026-10-05T22:12:56Z`, повторная проверка хешей
после чтения unchanged. **APPROVED только заявленный bounded source slice;
C0/H0/M0/L0.** Canonical worktree
`/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`, submission
HEAD `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1` (Git не запускался).
High-risk-product lane, current requirements gate18/0 и нормы Round243–246
сохранены. Нет полного T119/menu Retry/native/installed approval.

Независимая область этой записи — изменения MAIN только в
MeetingReminderPresenter.h/.cpp, AppMain.cpp и RecordingIndicatorTests.cpp.
Лично прочитаны полный Presenter и затронутые AppMain registration/admission/
source/poll/handoff/context/projection/member paths, новые executable equality/
expiry asserts и source wiring regression. `code-reviewer` и `ponytail-review`
прочитаны полностью. Git diff/preflight/test/VM не запускались согласно scope.
Reviewer реализовал WindowsTray.h/.cpp по отдельному поручению: **собственные
Tray изменения прямо исключены из этого независимого verdict**, их проверка
принадлежит main/другому reviewer. Отчёт не является self-approval этих файлов.

### Проверенные основания

- Presenter.h9–18: equality сравнивает eventId/startsAt/endsAt/link flag/URL,
  owner epoch, label и enabled. Не включает card canSurface: это не menu
  eligibility. Safe title остаётся только presentation, не копируется в target.
- Presenter.cpp98–110: upcomingExpiry проверяет finite inputs, finite positive
  remaining и положительные целые ticks; conversion flooring не удлиняет
  выбранный срок. Перед signed cast ограничение учитывает MSVC double-sized
  long double/rounded signed maximum, затем проверяется steady addition overflow.
  Нет duration cast от непроверенного floating point и нет card120s/15s expiry.
- AppMain.cpp1320–1323: скопированный alive token проверяется перед menu callback.
  beginMenuCalendarJoin3752–3754 направляет frozen row в существующий общий owner,
  без второго HTTP/launcher/dialog service. Busy/flight/joinable/reentry refusal
  до admission общий с document/card, не отдельный menu slot.
- AppMain.cpp3783–3807: проверяются row enabled, available full target/current
  epoch, native owner/workspace/origin и fresh auth/interaction; checked
  endsAt-wallNow→steady выполняется один раз. Native action UUID/source identity
  создаётся до begin; allocating copies context/document/native/menu prepared
  до admission. После begin переносится owning flight и запускается existing
  resolver только с event ID/current config/deadline, не snapshot URL.
- AppMain.cpp3681–3710: source-current выделен из attempt-current; для menu
  повторно сверяются epoch/owner/workspace/origin и frozen target в доступной
  upcoming projection, плюс original steady expiry. Нет pending card/quiet/
  capture filter либо повторного upcomingExpiry на refresh. Presentation label/
  timezone-only change не отзывает admitted unchanged target. Helper.current
  продолжает защищать operation/ticket/deadline; stale source передаёт revocation,
  не новый context.
- Existing poll3890–3990 reuses actual thread signal → join → future.get →
  matching complete, затем fresh calendarCurrent до OS dispatch/continuation.
  RefreshNativeState4059 забирает completion до admission/readiness early return.
  Discard-only SDK/dialog cancel не становится drain. Source inspection не
  подтверждает физический выход потока/WinRT/ContentDialog на реальном Windows.
- Handoff3949–3962: native reminder intent остаётся отдельным optional; menu
  не получает intent/action joinAndRecord и не попадает в completeAction/Record.
  Прежний card fresh handoffRecordingCurrent/prerequisite guard не ослаблен.
- Projection4196–4201: owning upcomingRows получает accepted host preferred zone;
  tray setter получает native authGeneration, time revision и оба server flags.
  Без reminders projection unavailable; label generation не становится Join
  authority. Existing account/time binding2720–2733 и token reset paths сохранены.

Конкретных C/H/M/L дефектов в этих изменениях не найдено. Ponytail: общий row,
существующий source/current/owner/transport и одна checked expiry функция;
новых dependencies/interfaces/factories/cache нет. `Lean already. Ship.`
`net: -0 lines possible.` Это оценка только main slice, не собственного Tray.

### Tests / exact four source hashes

Tests144–180 лично прочитаны: все восемь equality dimensions, canSurface
independence; ordinary remaining duration, ended/negative remaining, NaN/Inf,
floating/signed/addition overflow, sub-tick refusal и exact near-clock-max
addition. Registration main648 присутствует. Tests399–437 проверяют наличие и
порядок AppMain guards, frozen storage/current, отсутствие reconversion в source,
projection/time revision и alive callback. Комментарий прямо ограничивает их
source wiring, не actual UI/thread/SDK completion. Нет ложного native proof.

| Файл — относительно apps/windows/ | SHA-256 |
| --- | --- |
| RecApp/Shell/MeetingReminderPresenter.h | `56ceb960e3c793cb9a5c33f8220de7cf345d66e1fe6484dd6756206a930e778d` |
| RecApp/Shell/MeetingReminderPresenter.cpp | `f4092215243d9f1fd78d3198f9b0fca4dddfd095bcce5b037ad0a749abc77dc2` |
| RecApp/AppMain.cpp | `89ec71c966655130e9dc2c5b63f507ee438e62b1aa8ba965c958bc4143d75bee` |
| Tests/GrafWindowsPackageTests/RecordingIndicatorTests.cpp | `c67dfc64fb63fbf80b98621f91d471aad3453f27b9e63d5b521662cf6ad19b40` |

Нормативные SHA-256 лично пересверены, unchanged:

| Артефакт | SHA-256 |
| --- | --- |
| spec.md | `b411bfb620e9d571422f9c423b0ae193ed70e87303d08e84a4b9844e32f81658` |
| plan.md | `527e660d9e1682e7a0f0a79118ea4bab38d4c174542b49c0113f571528a5b89c` |
| data-model.md | `8dd54012c3bfe4003cd18db98ebc67e0b7730cbbdfb6523b881cce4cdc15ec19` |
| contracts/windows-native-web-bridge.md | `21bffa56631901952ae778871f26785522d839eafc8afb9942b488ff22bbd0fa` |
| quickstart.md | `1065b1970125f2ea7cc323c0177d07485e34a339a6b7195df4af9aa65a5cb683` |
| research.md | `0e7659d4cf5136d392bde28cb273c6ca0be6af2ac3eca50e23a617e1af129522` |
| tasks.md — T119 `[ ]` | `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f` |

Main сообщает expiry/equality/wiring PASS; reviewer не запускал tests и не
проверял raw logs. Final SDK/native focused validation planned, не объявлены
PASS текущих байтов. Последний общий native Round24548/49 OwnerTimeout300s
сохранён как неполная квитанция, не новый успех и не доказанная причина race.

### Явные следующие границы и минимальная native popup проверка

Menu failure Retry сознательно **NEXT slice**, не выполнен этим кодом:
publishCalendarResult пока не показывает menu failure dialog, helper work()
не выдаёт его terminal attempt, cleanup освобождает drained flight. Будущий
owned Retry purpose/reservation, matching actual dialog drain, новый operation/
request с тем же source/expiry, click+15s и отсутствие busy gap требуют отдельной
реализации/source/native проверки. Browser recovery остаётся существующим
opening lifecycle. Не объявлять нынешнее menu failure UI либо full T119 принятым.

Bounded тест для main: существующий RecordingIndicatorTests может вызвать
реальный production Tray popup на Windows только после добавления resource
icon1 в test executable — constructor использует GetModuleHandle(nullptr)/
LoadIcon(resource1), а текущий CMake target не включает .rc. Сохранить отсутствие
иконки как честную ошибку setup, не обходить production constructor. Имеющийся
RecApp/GrafWindowsApp.rc можно связать в test target (RC language/build wiring —
main scope). UI-thread timer во время actual TrackPopupMenuEx меняет rows/auth/
time/state либо уничтожает tray: ожидать безопасный возврат и ноль calendar
callbacks. Отдельно callback при свежем frozen selection может уничтожить tray;
никакого HTTP/launch/Record. Это synthetic native popup/lifetime proof, не
installed/auth/trusted human click/a11y/DPI matrix. Reviewer этот тест не писал
и не запускал; предложение не создаёт нового service/test framework.

Only review write — этот append; main source/norm/tasks/markers/Git/GitHub/VM/
build/audio не менялись. Две собственные Tray implementation записи были по
отдельному явному поручению в этом же turn и не входят в независимую проверку.
Source approval exact четырёх hashes; whole UI/Retry/T119/installed остаются open.
