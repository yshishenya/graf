# T119: независимый requirements gate единой операции — 2026-10-04

## Вердикт и область

**REQUIREMENTS PASS — checked8 / unchecked0; C0 / H0 / M0.** Блокеров качества
требований в этих восьми критериях не обнаружено. Это разрешение по данному
requirements gate, не source approval, общий analyze PASS, runtime/installed
приёмка или завершение T119. Остальные обязательные ворота не отменяются.

Канонический repo: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`.
Branch: `codex/200-windows-followup`. Свежий read-only HEAD:
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`. Worktree содержит чужие dirty изменения;
они сохранены. Review учитывает последнее уточнение helper paragraph в plan,
включая отдельный work ID, один pending child и adapter-only completion proof.

Lane: независимая requirements-проверка внутри existing high-risk T119 slice;
единственные записи — `calendar-operation.md` и этот отчёт. Никаких product,
spec/plan/tasks/guidance, GitHub, commit, build, probe или VM изменений.

## Лично прочитанные основания

- Канонические `AGENTS.md`, guidance index, `spec-kit-flow.md`, `product-gates.md`
  и constitution 7.1.0; scoped validation/evidence/safety разделы
  `release-and-validation.md` (§Validation Lanes, §Git Safety, §Evidence Safety).
- Scoped product baseline: PRD §4.y и §30; current-product-status раздел
  календарной Feature168 — исторический контекст, не доказательство Windows.
- Project-local `.agents/skills/speckit-checklist/SKILL.md` прочитан полностью:
  критерии оцениваются как качество требований, не тесты реализации.
  `.specify/extensions.yml` прочитан: before/after_checklist hooks отключены;
  prerequisites подтвердил именно Feature200. Генерация нового набора критериев,
  issue sync и auto-commit не выполнялись.
- `spec.md`: US2, FR-002/005/006/015, SC-002/006/009, Session2026-10-02 T119;
  `tasks.md`: существующая открытая T119, без переоценки остальных задач.
- `plan.md`: T119, строки1157–1255; bridge §10 целиком; data-model §8;
  quickstart §13 целиком; все восемь исходных пунктов calendar-operation.
- Собственный pinned Mac reference из Git object
  `721b5125d799ea798a4af0b3625e18d3c1109039`: целиком
  `EmbeddedCabinetCalendarJoinBridge.swift` и `CalendarMeetingOpener.swift`.
  Никакой другой worktree/ветки или перенос Mac кода не использованы.

## Решение по каждому критерию

| Критерий | Решение | Конкретное основание качества требований |
| --- | --- | --- |
| CHK001 | `[x]` | Bridge строки390–395 и416–419 объединяет cabinet/menu/card и resolver/launcher/dialog; busy отвергает второй intent, не ставит его в очередь. Plan1226–1239 и1245–1251 различает единую operation и единственный pending child; UI terminal не снимает lease до actual completion. Data-model323–327 запрещает новое действие до drain. |
| CHK002 | `[x]` | Bridge421–428 требует origin/owner/workspace/auth generation/token, operation ID и document generation/nonce либо native action identity/epoch/deadline, проверку до/после ожиданий и перед launch/Record; даже смена token при прежнем owner отменяет действие. Plan1220–1233 дополняет неизменяемым monotonic action expiry; web без отдельного срока получает max, а не новый произвольный timeout. Data-model315–327 оставляет URL/auth только в памяти и вне reply/history; helper URL не хранит. |
| CHK003 | `[x]` | Plan1215–1218: initial absolute deadline = принятие действия+15s; dispatch/queue входит, chunks не перезапускают budget. Bridge416–419 задаёт terminal failed/dependency_unavailable при expiry, cancellation и удержание lease до actual completion. Quickstart465–469 и475–482 определяет проверяемые trickle/delayed-completion сценарии; test-first plan1240–1243 требует точную границу15s. |
| CHK004 | `[x]` | Plan1226–1239: отдельные monotonic work IDs поверх operation ID, один физически pending child, completion только matching operation/work ticket. Initial resolver duplicate не завершает recovery child. Adapter сообщает actual worker/OS/dialog exit; cancellation, elapsed time, exception poll и отказ очереди сами этого не доказывают (1245–1251). Завершения забираются независимо от interactionPermit; stale completion не применяет эффект и не освобождает новый ID. |
| CHK005 | `[x]` | Pinned Mac `join` отправляет opening перед await open и terminal лишь после его результата; `open` ждёт recoverInBrowser, который ждёт confirm, fresh resolve и browser completion. Bridge475–485 и plan1212–1218/1234–1239 сохраняют те же operation/request identity и внешний opening; fresh GET начинается после явного подтверждения с новым15s, но terminal request не оживает. Ошибка recovery заканчивает request, последующий повтор — новое явное действие. |
| CHK006 | `[x]` | Bridge475–485, data-model323–327, plan1215–1218/1231–1233 и quickstart475–482 согласованно сохраняют original card/action expiry. Новый resolver budget не является новым сроком жизни действия и не распространяется на OS query/launch/dialog. Current/отмена/исходный expiry продолжают действовать; отсутствие искусственного общего15s timeout определено прямо. |
| CHK007 | `[x]` | Bridge463–473 требует card-close-only-handoff и native-only joinAndRecord → handed_off → fresh current → existing capture prerequisites, без второй записи при active/starting/paused/stopping/finalizing. Plan1234–1237/1252–1254 запрещает early close и допускает handed_off только из opening после matching drain/current; Record делает consumer с новой проверкой, не helper. US2/FR-015 и quickstart459–461 сохраняют indicator/Stop и исходные сроки карточки. |
| CHK008 | `[x]` | Plan1220–1225 ограничивает helper state/fence: no URL/disk/I/O/factory/interface; actual completion сообщает adapter, не helper. Plan1245–1255 и quickstart475–482 требуют отдельные integration source review и actual delayed worker/native/installed proofs. Existing T119 остаётся owner задачей; нет второй HTTP/launcher/backend реализации или ложного закрытия T119/SC-002 по portable helper tests. |

## Ownership и границы доказательств

Требования однозначно разделяют три факта: внешний UI state, наличие pending
работы и фактическое завершение конкретного child ticket. Один UI-thread state
owner управляет admission/fence. AppMain adapter владеет реальными future/WinRT/
dialog lifetime и сообщает завершение только после actual completion. Helper
может проверить совпадение идентичностей и допустимость перехода, но не способен
доказать, что OS/worker действительно завершились.

Initial resolving → opening требует drain initial resolver. Recovery оставляет
opening того же request во время dialog/fresh GET/browser launch. Новый child
получает новый work ID и абсолютный resolver deadline от подтверждения. Matching
drain не означает current authorization: полный context/immutable expiry должен
быть проверен заново перед переходом и эффектом. Terminal failed/cancelled делает
дальнейшие эффекты неприменимыми, но pending ticket удерживается до actual exit. Record
после handoff остаётся отдельным действием consumer с fresh current/readiness.

Это проверяемые требования, а не принятая implementation API. Будущая source/
adapter проверка должна отдельно установить реальные сигналы completion,
удержание lease при Cancel/Hide и при ошибке/отказе очереди, защиту от reentrant
native вызовов, забор terminal work при недоступном UI/context и lifetime при
закрытии. Helper boolean/fake completion, future readiness без доказанного
нужного lifetime или номинальный API success не подменяют эти основания.

Ни одно native OS/installed launch gate этим review не принято. Прежние
reported portable41/41/native44/44/corpus141/141 относятся к URL срезу, не доказывают
ещё не реализованный operation owner, browser/dialog wiring или T119 целиком.

## Хеши проверенных требований

SHA-256 полных файлов; чтение scoped разделов не означает whole-feature review.

| Артефакт | SHA-256 |
| --- | --- |
| plan.md | `f9cf2f74a57f6a2b739bd72915e2d7cab281f9685c997d008e2b81c4d17bfaac` |
| contracts/windows-native-web-bridge.md | `ee5e6007eecfbd8ce317338d8dfed680009ca089420af63b93c5ebccdb01ccf1` |
| data-model.md | `28641767480ac310579fd55f1a4d5c2f91b82ad69d8dcf6da4a53040c6419764` |
| quickstart.md | `930aed240d1efe1ce58b2657a27a82a80552684c7e8b35f8763a7f34c71640c0` |
| spec.md | `0073b6f2ff8e3e9f07389473cf7fc0f5c2eaf146961f08426d140163dd5d4fe2` |
| tasks.md | `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f` |
| calendar-operation.md before review | `f54c9d6d2e0df42ca1c7a21e33b2f9e030542935e2a02d4490213f51a379abf4` |
| pinned Mac EmbeddedCabinetCalendarJoinBridge.swift | `3932bf4f37d6fab48537c91c35d03161534154638612184d16bd9b850a6a8cd5` |
| pinned Mac CalendarMeetingOpener.swift | `05eef2ba53c10913747b314d3eca0aff8a29303c055189c58d2083c677e08652` |
| AGENTS.md | `384c41c0b1674a3daf75d0e57646379198295c3f8452012c8101fc6332bec58b` |
| constitution.md | `d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859` |
| guidance README.md | `40e357e422c60915d2c4334c83b9ab74f5ef4c0df6ab8831e3ed16e281ba18a6` |
| spec-kit-flow.md | `5edf818b6ee27c7ee66d14edc003325ec7b16789eb1a195377cdeb901ae44887` |
| product-gates.md | `e5c39fb473dcf785f417b9785b0d6ba17fe23026906eedc08c0620c7a6f5d097` |

## Завершение

Все CHK001–CHK008 оценены независимо; неподтверждённых требований в этих восьми
пунктах нет. Checklist сохраняет исходные формулировки; изменены только восемь
markers и добавлена reviewer receipt. Старые reports не изменялись. После записи
фактический checklist перечитан: checked8/unchecked0. Хеши всех шести проверенных
feature документов совпали с receipt выше; scoped diff/whitespace checks чистые.
Проверены также новые untracked outputs на trailing whitespace. Финальные
хеши двух reviewer-owned outputs выдаются отдельно, без self-hash в отчёте.

## Round239 sidecar — requirements gate общего AppMain owner, 2026-10-05

**REQUIREMENTS PASS C0/H0/M0/L0; дополнительных продуктовых уточнений:0.**
Current operation8/0, wire5/0, launcher5/0; фактические counts перечитаны,
всего18checked/0unchecked. Markers не менялись, новые критерии/задачи не созданы.
Это пригодность текущих требований для следующего owner integration slice,
не source approval AppMain, physical completion или installed T119 acceptance.

Canonical branch/HEAD свежим read-only чтением подтверждены:
`codex/200-windows-followup`, `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`.
Предыдущая часть этого report лично прочитана целиком и сохранена; исходный
SHA-256 `c67cc1d98742e1087116baa00a243b653b900481a0b319dc5c841fdcd51994bb`.

Лично перечитаны current calendar-operation/calendar-wire/calendar-launcher,
plan T1191157–1329, bridge §10 lifecycle/launcher/recovery, data-model §8,
quickstart §13, FR-006/015 и SC-002/006/009, открытая task T119. Constitution
VI/VII и ранее прочитанные governance сохранены, hashes сверены. Project
speckit-checklist прочитан полностью: review качества требований, не проверка
работы кода. Prerequisites подтвердил Feature200; before/after checklist
auto-commit hooks disabled. По user scope используется append existing gate,
а не новый checklist/schema/UI/interface. Весь AppMain/остальные tasks/storage/
hardware не аудировались; build/probe/VM/jobs/Git/GitHub не запускались.

### Почему existing gate достаточен

| Operation criterion | Current requirements-quality решение для owner integration |
| --- | --- |
| CHK001 — PASS | Plan1170–1185/1246–1251 и data-model §8 задают один owner/busy для cabinet/card/menu, resolver/query/launch/dialog. Новый intent не в очереди; UI terminal не освобождает child. Wire cancel относится только к matching document request, не к native card/menu. |
| CHK002 — PASS | Plan1221–1234 и bridge §10 требуют exact origin/owner/workspace/auth generation/token, event/request/operation ID, document generation/nonce либо native action epoch/identity/immutable expiry. Token drift отменяет даже при прежнем owner. Matching drain отдельно от fresh authorization, проверяемой после await/dialog и прямо перед OS dispatch/Record. |
| CHK003 — PASS | Plan1216–1219: initial resolver15s от принятия, recovery15s от explicit confirmation, очередь включена, chunks не обновляют budget. UI expiry terminal не снимает worker lease и не позволяет применить поздний результат. |
| CHK004 — PASS | Plan1227–1231/1246–1252 явно требует exact operation/work ticket и actual worker/OS/dialog exit; helper этого не доказывает. Drain независимо от interactionPermit; cancellation/poll fault/queue failure не являются completion. Old child/reply не освобождает recovery/new operation. |
| CHK005 — PASS | Plan1212–1218/1235–1239, bridge recovery и data-model §8 сохраняют original request opening через confirm/fresh resolver/browser. Terminal не оживает; новый child только после matching drain и fresh current. No cached URL/auto retry/fallback. |
| CHK006 — PASS | Bridge recovery и plan1232–1234 сохраняют original native event/card action expiry, не продлеваемый recovery. Resolver15s не превращается в OS/dialog/user timeout; web без отдельного action срока использует max согласно plan. |
| CHK007 — PASS | Bridge §10 и plan1237–1239/1253–1255: card close лишь handoff; joinAndRecord native-only после matching completion, fresh current и existing capture prerequisites, без второй записи. Нормы не разрешают перенос completeAction early close/cancelDialog early release в Join. |
| CHK008 — PASS | Plan1246–1256/1282–1286/1296–1329 и quickstart §13 отделяют helper от actual adapters/source review/SDK build/installed proof; existing timer/future/packaged_task/alive/DispatcherQueue/SDK/ContentDialog reused. Нет нового HTTP/launcher/dialog service или factory. |

### Обязательные bounded proof fences следующего source review

Ниже — следствия **уже написанных** требований actual completion/current,
не новая schema, UX policy или скрытое implementation approval:

1. Result availability и окончание физического resolver worker — разные
   доказательства. `future_ready`/готовый return value сами не разрешают снять
   lease, если поток ещё может использовать resources/snapshot. Adapter обязан
   предъявить конкретное exit/reaping основание; matching helper bool, signal
   до возврата worker или detach/drop handle как обход busy недостаточны.
   После результата нельзя начать SDK child до доказанного resolver drain.
2. Для SDK query/launch boundary — owned API child, не завершение приложения
   встречи или доказательство личности получателя. Discard не вызывает OS
   Cancel/Close. Started держит handle; natural Completed/Error допускает
   matching completion. Status fault/unsolicited Canceled остаются indeterminate
   и удерживают busy; GetResults fault после достоверного terminal — failure
   результата, а не потеря completion proof. StartFailed без handle завершает
   только synchronous dispatch scope, не доказывает отсутствие OS effect.
3. ContentDialog owner отдельно удерживает actual ShowAsync scope/handle.
   Hide/cancel request, снятый UI slot, dialog flag или отказ DispatcherQueue
   не заменяют completion. Результат применяется только exact ticket/current;
   callback старого dialog не снимает новый child. Early-release existing
   cancelDialog pattern для Join прямо запрещён plan1253–1254.
4. Admission/effect guard и cleanup/drain должны быть отдельными ветвями.
   При interactionPermit=false, auth/context drift, UI terminal или отказе
   очереди outstanding child всё равно собирается/завершается безопасным
   owner-lifetime путём. UI-disabled/alive guard не должен оставлять единственный
   drain poll за early return; при этом stale completion не делает новый эффект.
5. Close/logout/document revoke сначала снимают applicability. Ordinary
   window/owner teardown не объявляет thread/SDK/dialog actual exit и не
   освобождает живые captures/lease. Тот же lifetime accounting нужен при
   shutdown; выполнение cleanup должно быть доказано отдельно от discard.
   Разрешённый bridge/launcher recovery через **явный process quit/restart**
   при indeterminate SDK не является matching drain и не разрешает следующий
   flight в продолжающемся процессе. Он также не доказывает отзыв уже
   переданного ОС URI. Никакого timer forced release или нового busy limit нет.
6. Все three entrypoints сходятся в одном state/fence owner; native card/menu
   используют event UUID/current action identity/epoch/original monotonic expiry,
   не сохранённый meetingUrl и не web cancel authority. Перед resolver/current
   переходами и launch/Record сверяется полный confirmed auth/workspace snapshot.
   Диалог/подтверждение не обновляют action expiry и не создают новую operation.

Эти fences измеримы delayed worker/dialog/SDK и stale/reentrant scenarios из
plan/quickstart. Portable helper/fake ticket proof не заменяет настоящий
adapter lifetime; source/SDK и installed gates идут отдельно. Выбор конкретного
exit/reaping механизма остаётся минимальной реализацией main, не новым
продуктовым вопросом и не основанием добавить service/factory.

### Current requirement hashes

SHA-256 полных файлов, чтение scoped разделов не является whole-feature review:

| Артефакт относительно specs/200-windows-desktop-app | SHA-256 |
| --- | --- |
| spec.md | `8a61bbcb1ef78043e755aae48ba284118e1dab04118be00d7050e695c1a90ed0` |
| plan.md | `4e2aadb044c2ca8f21c8189e74c5f3338a3663fc6704db4280f7edccb79c7dec` |
| tasks.md | `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f` |
| contracts/windows-native-web-bridge.md | `a0acaca20097199e42cba490839cd719b8198ad124d916d611ec4bdcd6b11a65` |
| data-model.md | `217a7a4f1e8cb45543a824ffd878bb32ffd2ea1c5bf44f7ee421a2c2ab0d9cdc` |
| quickstart.md | `189e52e8464f528589eb937315641aef1e293408b179bfc9084c76dc4ca39c1e` |
| checklists/calendar-operation.md — 8/0 | `a656adcd4d6cccf578cc7c98f385fe10ba5b422cfb47dba7e3662f8b24e0a834` |
| checklists/calendar-wire.md — 5/0 | `0b58c484e25b5f37ec3b157f0bbe227ddcc2cff682dbae5ab0af882936796895` |
| checklists/calendar-launcher.md — 5/0 | `99f1a945f2b557ece837ea484633d3e61af5a7838c0068a182bea17de22e4355` |

Current hashes совпадают с принятыми Round238/239 norms. Нового normative gap
или противоречия в этом owner scope нет. Memory использована только для
ориентации/evidence границ; актуальность установлена текущими файлами.

Квитанции main по предыдущему shim source slice: latest Browser/portable69373
2/2+45/45 PASS23.00s BUILD0 и SDK10038 BUILD0 получены; serial CoreTests direct
и50398 exit0 после всех49 до нового49. Старый46277 exit255 retained, найденный
shared temp path **не доказывает race**. Final NTFS49/85788 ещё running,
pre-M1 native24638 49/49 PASS222.42s исторический. Эти owner-reported receipts
не использованы как доказательство ещё отсутствующего common AppMain owner.

**Terminal owner requirements: PASS C0/H0/M0/L0, operation8/0; aggregate18/0.
Новых продуктовых уточнений:0.** Записан только этот append; checklist markers,
нормы/code/tasks/Git/GitHub/чужая работа и историческая часть report сохранены.
High-risk analyze/source/SDK/actual lifetime/installed gates и T119 остаются
отдельными, без approval реализации или расширения протокола/UI.

## Round240 — fresh owner requirements/checklist revalidation, 2026-10-05

**REQUIREMENTS PASS C0/H0/M0/L0. Operation8/0, wire5/0, launcher5/0;
aggregate18/0. Дополнительных продуктовых уточнений:0.** Это только повторная
проверка качества требований common AppMain owner, не review нового product
source или его actual completion. Round239 sidecar/proof fences сохраняются.

Workdir: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`.
User сообщил HEAD `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`;
current `.specify/feature.json` подтверждает Feature200/high-risk-product,
заявленные branch `codex/200-windows-followup` и source_sha. Git не запускался,
поэтому нового independent Git HEAD read здесь не заявляется.
Pre-append report SHA-256 fresh matches принятый main Round239:
`9a666d5e0541cb30fa053b90fcfafcf63d3c67aa0c23a5dab4ea359498a311ae`.

Лично перечитаны current checklist criteria всех18 пунктов, plan T119 operation/
wire/launcher, spec FR-006/015, task T119, bridge §10 current/deadline/recovery/
SDK lifetime, data-model §8 и quickstart §13 owner/launcher acceptance.
Constitution VI/VII scoped reread; ранее прочитанные governance hashes unchanged.
Canonical `.agents/skills/speckit-checklist/SKILL.md` прочитан полностью;
использован для requirements-quality, без новой генерации/markers. Checklist
hooks disabled. По явному запрету Git prerequisites script не запускался;
Feature identity установлена read-only из feature.json и user scope.
AppMain/Presenter/source/tests/storage/audio и другие dirty документы не
аудировались и не менялись; no VM/build/Git/GitHub/jobs.

### Reaffirmed operation criteria

| Критерий | Решение и current requirement evidence |
| --- | --- |
| CHK001 | PASS — plan1227–1231/1246–1251, bridge §10, data-model §8 определяют один busy для cabinet/card/menu и один pending child до actual completion, без очереди. |
| CHK002 | PASS — plan1221–1234/bridge §10 задают origin/owner/workspace/auth generation/token, document generation/nonce либо native event/action epoch/identity/immutable expiry; полный current проверяется после ожиданий и перед эффектами. |
| CHK003 | PASS — plan1216–1219/bridge §10: initial15s от acceptance, recovery15s от explicit confirmation, queue включена, chunks срок не обновляют. |
| CHK004 | PASS — plan1230–1231/1246–1252: exact operation/work ticket, actual worker/OS/dialog completion, drain независимо от interactionPermit; UI terminal/Cancel/poll fault не освобождают lease. |
| CHK005 | PASS — plan1212–1219/1235–1239, bridge recovery: original request opening через dialog/fresh resolver/browser; terminal не оживает, следующий child только после matching drain/current. |
| CHK006 | PASS — plan1232–1234/bridge §10/quickstart §13: original action/card expiry не продлевается recovery; resolver15s не становится OS/dialog timeout. |
| CHK007 | PASS — plan1237–1239/1253–1255, bridge §10/FR-015: native pending action не завершается early completeAction; card закрывается только handoff, Record только после fresh current/prerequisites, Stop/indicator сохранены. |
| CHK008 | PASS — plan1246–1256/1282–1286, quickstart §13 отделяют helper от actual adapter lifetime/source/SDK/installed proof; reuse, без новой schema/service/factory/interface. |

Текущий test-first focus main (native pending action + immutable expiry + actual
worker drain) соответствует CHK002/004/006/007, но его исполнение этим gate
**не подтверждено**. `future_ready` не заменяет доказательство физического
выхода worker; pending/lease сохраняется до matching actual completion.
Hide/Cancel/отзыв UI не считаются dialog/SDK drain. При interactionPermit=false
cleanup/drain продолжается без новых effects. Shutdown/window teardown не
выдаётся за completion; indeterminate SDK quit/restart исключение остаётся
process-level boundary, а не освобождением busy для нового flight.
Нет основания менять requirements, расширять протокол/UI или добавлять интерфейс.

### Current exact hashes and totals

Свежие SHA-256 всех шести normative файлов **побайтно совпали** с таблицей
Round239 sidecar выше: spec `8a61bbcb…`, plan `4e2aadb0…`, tasks `80fc15cd…`,
bridge `a0acaca2…`, model `217a7a4f…`, quickstart `189e52e8…`.
Полные значения остаются в той таблице, без перезаписи исторических receipts.
Checklist hashes также unchanged: operation `a656adcd…`, wire `0b58c484…`,
launcher `99f1a945…`; actual markers перечитаны как8/0+5/0+5/0.

Финальные Round23949/49/SDK/browser/portable/CoreTests receipts получены ранее
от main и не являются доказательством Round240 owner implementation. Старый
CoreTests exit255/cause unproven не переобъясняется. Installed/full T119,
source approval нового AppMain и обязательный analyze остаются отдельными.

**Terminal Round240 requirements: PASS C0/H0/M0/L0; existing18/0 unchanged.**
Only write — этот append reviewer-owned operation-gate report; прежняя часть,
markers/norms/tasks/product code и чужая dirty работа сохранены.

## Round241 — remaining native MENU requirements sidecar, 2026-10-05

**Existing shared requirements PASS: operation8/0 + wire5/0 + launcher5/0 =
18 checked / 0 unchecked. Native menu-specific coverage: C0/H0/M1/L0,
M1 unresolved pending pinned CalendarTray mapping.** Ни текущие кнопки карточки,
ни Round240 owner source approval не доказывают настоящую menu entrypoint.
Это requirements review, не source/installed acceptance и не новая задача.

Canonical workdir — `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`.
Заявленный HEAD `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`, branch
`codex/200-windows-followup`; feature.json подтверждает Feature200/high-risk-product
и эти поля. Git не запускался, свежего independent Git HEAD receipt нет.
До append report SHA-256:
`4c2c495b0a0951f238da7df7687130011a01c9a67e73b7c9a021fd6eb6fb15a5`.
Ни одна прежняя часть отчёта или checklist marker не изменена.

Лично прочитаны FULL canonical `speckit-implement/SKILL.md` и
`speckit-checklist/SKILL.md`: применены только independent requirements gate,
reviewer ownership и различие requirements/implementation. Implementation,
prerequisites script (вызывает Git), source audit и issue sync не запускались
по явной границе пользователя. В extensions.yml before/after implement и
checklist hooks disabled; никакой hook не исполнен. Checklist skill ограничивает
оценку качеством требований, поэтому уже существующий runtime owner не принят
за доказательство достаточного описания меню.

Лично перечитаны все18 actual критериев; spec US2 scenarios4–6, FR-002/003/005/
006/015, SC-002/006/009; plan1157–1330, включая1169; bridge §10; data-model §8;
quickstart §13; task T119; scoped T119 research для происхождения reference.
Root AGENTS/guidance index, полный spec-kit-flow/product-gates и constitution
VI/VII перечитаны; high-risk tray/auth/Record и reference-fidelity gates сохранены.
Не повторял весь Feature200, storage/audio или прежние source reviews.

### Подтверждённая общая область всех18 пунктов

- Operation CHK001–004: один общий owner и запрет очереди/второго child; exact
  owner/workspace/origin/auth generation/token и native action identity/epoch;
  initial resolver15s от acceptance, matching operation/work drain, cancellation
  не равна completion. Native menu прямо включено в plan1169, task T119 и
  bridge §10 one-busy scope, не заменено notification buttons.
- Operation CHK005–008: recovery остаётся opening, fresh resolve после явного
  подтверждения со своим15s, original native action expiry не продлевается;
  handoff/current/readiness обязательны для Record, actual adapter/installed
  evidence отделено. Обязательные manual Record/indicator/Stop не ослабляются.
- Wire CHK001–005: строгие document join/cancel и owned original-envelope
  semantics, replay-before-cap1024, invalidation и staged ownership определены.
  Document nonce/UUID-history и cancellation-only command **не становятся**
  authority для menu action: §10 прямо запрещает web cancel native card/menu.
  Меню — native source, без нового web payload или capability schema.
- Launcher CHK001–005: target из freshly resolved validated HTTPS, не saved URL
  или provider family; native query outcomes и явный browser recovery; discard
  без OS Cancel/Close; indeterminate busy и process-quit boundary; actual receiver
  acceptance отделена. Все эти требования распространяются и на menu source.

### M1 — menu-specific reference mapping ещё не зафиксировано

**Основание:** spec US2.4–6 требует Join из нативного меню и current action;
FR-002/SC-002 — тот же пользовательский смысл актуального Mac. Plan1169 лишь
называет меню как третий entrypoint; bridge §10/data-model §8 требуют native
identity/epoch/deadline, но не раскрывают menu projection. Quickstart §13 требует
installed cabinet/card/menu matrix, не определяя выбор menu upcoming events.
Прочитанный T119 research описывает bridge/opener, а не CalendarTray projection.

Для закрытия M1 нужна узкая проверяемая mapping запись по утверждённому
`721b5125d799ea798a4af0b3625e18d3c1109039` CalendarTray, который сейчас читает main:

1. Какие upcoming events и действия входят в фактическое меню: reference
   selection/window/order/limit и empty/unavailable/busy presentation, если они
   существуют в reference. Не выбирать самостоятельно Windows количество,
   состав или reminder-only eligibility; FR-003 не разрешает вторую native
   meeting-list бизнес-логику под видом подключения.
2. Как current native menu action привязан к выбранному event/context, не к
   наличию presented notification card, и какой reference-derived original expiry
   превращается в immutable monotonic action expiry. Одного факта «UUID существует»
   либо живого account epoch недостаточно для menu action current. Upcoming
   selection нельзя без доказательства свести к временному окну карточки.
3. Что является close/replacement выбранного action после dispatch: обычное
   завершение popup вследствие выбора и действительный отзыв/замена исходного
   action должны быть различены по утверждённому сценарию. Иначе можно отменить
   каждое меню сразу после выбора либо ошибочно сохранять уже отозванное действие.
   Повторный Join/recovery обязан сохранять принятые current/expiry/lease fences,
   а Record после handoff — проверять именно menu target, не card visibility.

Это **один пробел полноты/трассировки для расширенного menu scope**, а не три
новых требования продукта или обнаруженная source ошибка. Он не опровергает
прочитанные18 shared criteria и не даёт оснований менять их historical markers.
В рамках разрешённого append-only scope дополнительных checkbox items нет:
menu projection неподтверждена и явно записана здесь, а не скрыта за18/0.
До наличия этой mapping записи полный native menu requirements gate не PASS;
наличие общего owner не снимает этот остаток.

**Новых продуктовых решений пока не требуется.** Уже выбраны Mac parity и
общий T119 owner. Нужен результат чтения pinned GRAF reference и точное
сопоставление существующим lifetime/current требованиям, не произвольное
проектирование Windows menu. Если reference не задаёт нужную границу либо
выявляет конфликт с обязательной безопасностью/accessibility, только тогда
нужно явное техническое уточнение/документированное отклонение до кода; сейчас
такой конфликт не доказан. Reviewer не заявляет личный source receipt pinned
CalendarTray: эту параллельную работу выполняет main, её вывод здесь не выдуман.

### Fresh hashes / фактические counts

SHA-256 receipt: **2026-10-05 19:20:07 UTC**. Все шесть normative hashes
побайтно совпали с Round240, без принятия сообщения «unchanged» на веру:

| Артефакт | SHA-256 |
| --- | --- |
| spec.md | `8a61bbcb1ef78043e755aae48ba284118e1dab04118be00d7050e695c1a90ed0` |
| plan.md | `4e2aadb044c2ca8f21c8189e74c5f3338a3663fc6704db4280f7edccb79c7dec` |
| tasks.md | `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f` |
| contracts/windows-native-web-bridge.md | `a0acaca20097199e42cba490839cd719b8198ad124d916d611ec4bdcd6b11a65` |
| data-model.md | `217a7a4f1e8cb45543a824ffd878bb32ffd2ea1c5bf44f7ee421a2c2ab0d9cdc` |
| quickstart.md | `189e52e8464f528589eb937315641aef1e293408b179bfc9084c76dc4ca39c1e` |
| calendar-operation.md — checked8/unchecked0 | `a656adcd4d6cccf578cc7c98f385fe10ba5b422cfb47dba7e3662f8b24e0a834` |
| calendar-wire.md — checked5/unchecked0 | `0b58c484e25b5f37ec3b157f0bbe227ddcc2cff682dbae5ab0af882936796895` |
| calendar-launcher.md — checked5/unchecked0 | `99f1a945f2b557ece837ea484633d3e61af5a7838c0068a182bea17de22e4355` |

Constitution `d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859`,
spec-kit-flow `5edf818b6ee27c7ee66d14edc003325ec7b16789eb1a195377cdeb901ae44887`,
product-gates `e5c39fb473dcf785f417b9785b0d6ba17fe23026906eedc08c0620c7a6f5d097`
также unchanged. Actual markers прочитаны и отдельно пересчитаны:18 checked/0
unchecked только для этих трёх checklist files; число остальных Feature200
checklists не объявляется заново. T119 actual task marker остаётся `[ ]`.

**Terminal:** shared18 requirements PASS; remaining native menu coverage pending
M1, C0/H0/M1/L0. Единственная запись — этот append. Никаких product/norm/tasks/
Git/GitHub/VM/build/test/audio действий; чужая dirty работа и review history
сохранены. Source, actual lifetime/SDK/installed/T119 closeout не приняты.

### Round241 — receipt main pinned CalendarTray и уточнение границы M1

После предыдущей записи main сообщил actual reference evidence на том же
`721b5125d799ea798a4af0b3625e18d3c1109039`: CalendarTrayModel.refresh использует
server events, startsAt/id sort и prefix12; server showUpcomingTitle/
showUpcomingTime, all-day «Весь день» и generic private title. Upcoming menu
отдельно от notification due/dismissal/reminders quiet; safe native row event ID
идёт в openEventFromMenu с explicit failure Retry dialog и one busy;
projection/auth changes вызывают menu.cancelTracking. Это **main-reported pinned
source receipt**, не лично выполненный reviewer source audit. Его нельзя считать
нормативной записью menu lifetime или Windows implementation/installed proof.
Сообщённые отсутствие Windows upcoming menu и потеря show_upcoming_*/all_day в
snapshot decoder здесь не оформлены source finding: source scope не проверялся.

Receipt подтверждает M1: добавление двух кнопок текущей reminder card не покрывает
утверждённое native menu. Нового продуктового выбора не требуется; необходим
technical appendix в существующих plan/data-model/quickstart T119 **до menu кода**:

- Зафиксировать exact reference projection и её связь с server snapshot fields,
  отдельно от notification eligibility/preferences/dismissal, включая privacy
  presentation. Не придумывать другой Windows count/order/selector.
- Зафиксировать current menu target/action identity, auth/context projection
  invalidation и исходный action expiry с его monotonic представлением. Не
  наследовать reminder deadline. Если reference не даёт конечный срок, описать
  фактическое validity правило и допустимое отображение в existing context,
  а не молча вводить новый15s/карточный/другой timeout.
- Разделить popup tracking end после выбора, projection/auth cancelTracking и
  applicability активного owner flight; определить, какой именно source факт
  отменяет текущий action. Не приравнивать закрытие popup к actual worker/SDK/
  dialog drain и не терять проверки после OS/dialog ожиданий.
- Описать explicit menu failure Retry как новое явное current действие со свежим
  resolver без cached URL, auto-retry или нового owner; до matching drain busy
  сохраняется. Original action expiry/recovery semantics и native Record fresh
  source проверки не ослаблять.

**Ограниченный menu requirements verdict остаётся C0/H0/M1/L0: STOP menu code
до такого appendix и его независимого re-review.** Это не отмена shared18/0 и
не повторная оценка Round240 source; новые нормы ещё не представлены. Reviewer
ничего не менял вне append этого отчёта и не выбрал собственную expiry формулу.

### Round241 — M1 re-review новых menu norms, 2026-10-05

**REQUIREMENTS PASS C0/H0/M0/L0, M1 CLOSED.** Shared checklist totals повторно
прочитаны/пересчитаны: operation8/0, wire5/0, launcher5/0, aggregate18/0.
Новых markers нет; прежний M1/STOP выше сохраняется как история своего снимка.
Это допуск качества требований, включая узкие decoder fields; не approval
product source, реального menu/Retry lifetime, installed parity или закрытие T119.

Scope unchanged: canonical workdir/заявленный HEAD прежние; Git не запускался.
Pre-append report SHA-256 fresh matches:
`953470aec3aea5ddd94144d420adeb47455833539d93ce55829910654d52b577`.
Лично прочитаны actual affected sections всех шести норм и research: spec Session
«ближайшие встречи», plan1652–1727, model §8 menu append, bridge §10 menu append
и прежняя deadline/terminal граница, quickstart §16, research EOF. Task T119
и shared owner gates остаются прежними; scopes/tests/builds не расширены.
Pinned source происхождение оценено по записанным main receipt и actual research;
повторный личный source audit CalendarTray/Windows implementation не заявляется.

#### Закрытие конкретных частей M1

1. **Projection/decoder — PASS.** Plan п.1–3/model/quickstart §16 точно задают
   startsAt/eventId sort, prefix12, общий authenticated upcoming snapshot;
   независимость от card due/canSurface/dismissal/quiet/capture. Добавляются только
   server show_upcoming_title/show_upcoming_time и event all_day: missing/null
   соответственно true/true/false, present non-bool invalidates весь snapshot,
   включая поле не первой строки. Owner/UUID/instant/link/title privacy и прежние
   bounds не ослабляются. Нет новых local preferences, endpoint/client или
   web authority. Узкая первая decoder стадия **requirements-approved**.
2. **Presentation — PASS.** Safe available/empty/private/hidden title, timezone
   HH:mm/all-day «Весь день», hidden time, link-unavailable non-actionable rows,
   native DPI fitting/accessibility заданы; snapshot URL лишь availability,
   launch всегда fresh join-target. Refresh failure/auth invalidation очищают
   menu отдельно от failed-card retention. Нет замены меню двумя card buttons.
3. **Frozen source/current — PASS.** Plan п.3–5/model определяют copied rows/
   handlers до TrackPopupMenuEx exit, frozen event target вместо нового row index,
   owner epoch/native action UUID и target identity. After-loop alive/window/
   current проверка и запрет Impl access после potentially destroying callback
   задают native loop lifetime boundary. Current accepted flight требует доступной
   проекции, exact event/owner/target и original expiry; card pendingAction не
   используется. Для меню нет joinAndRecord/Record authority.
4. **Expiry — PASS, документированное техническое уточнение.** Original endsAt
   из принятого snapshot один раз переводится через endsAt-wallNow в checked
   steady expiry при selection acceptance. <=0/invalid/overflow fail closed;
   refresh/Retry/clock rollback не продлевают исходный deadline. End-time/target
   change также отзывает frozen target; новая projection не меняет его молча.
   Research явно отличает эту Windows staleness конкретизацию от Mac opener
   timer. Это не receipt TTL/dismissal, не card120s или resolver15s, не новый
   пользовательский timeout и не ослабление обязательного current gate.
5. **Tracking vs flight — PASS.** Normal popup close после selection не отменяет
   accepted flight. Presentation-only EndMenu прекращает старый selection,
   но не отменяет unchanged accepted target; removal/replacement/unavailable
   projection/auth/interaction/exit/expiry отменяют applicability. Ни Hide,
   EndMenu, Cancel, presentation revoke, ни elapsed time не доказывают drain.
6. **Retry/lease — PASS.** Plan п.6–7/model/bridge/quickstart согласованы:
   failure dialog — owned child общего owner до terminal, только после drain
   прежнего work; purpose отличен от browser recovery. Matching natural dialog
   completion + explicit current Primary + fresh source check завершают старый
   attempt failed и начинают новый request/operation с прежним source/expiry.
   Reentrant admission gap запрещён. acceptedAt/deadline берутся от click,
   включая animation/queue/drain delay, не от позднего poll. Unknown completion
   удерживает handle/ticket/busy; stale/cancel/auth/expiry не запускают Retry.

**Важная согласованная граница terminal/deadline:** bridge §10 продолжает требовать
terminal failed/dependency_unavailable при resolver expiry. Plan п.7 явно исключает
expiry из нового Retry; это исключение не ограничено только source expiry.
Вместе с общим no-terminal-revival правилом оно означает: уже terminal resolver
timeout/cancelled attempt нельзя переводить обратно в owned Retry/dialog work.
Описанный failure-dialog путь относится к ещё нетерминальному отказу при current
source, а не к оживлению timeout. Original action expiry также запрещает попытку.
Эта граница является обязательным source-review fence, не новой нормой reviewer.

#### Exact current normative receipt

SHA-256 прочитаны повторно; clock receipt **2026-10-05 19:30:33 UTC**.

| Артефакт | SHA-256 |
| --- | --- |
| spec.md | `b3edc920a6d6ad31b0be538c53a96637e087c43987f9d8133b58503a6bbf6911` |
| plan.md | `e5a36118f27ba0e3402b5adb5999b0cf853523af4b1a27fff834ac999f96391e` |
| tasks.md — unchanged, T119 `[ ]` | `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f` |
| contracts/windows-native-web-bridge.md | `fcb99a1fc91a444cedb570aaa26ca490d71c33fbbfded9b82f5c129f12e1b542` |
| data-model.md | `d9d085d8a09f28c20e4e18a5359818780e8c33be186516506f98c939c53a5d46` |
| quickstart.md | `9a20a1cbf3737c5afb08cf8db70370af7f009cc803978f70b04a87d8a3e364be` |
| research.md | `62f381f1502a89c202b593f6ba7f8dddd6489fa9fd9a00e3a0696ea6e3f8b25f` |

Existing checklist hashes/markers остаются прежними Round24118/0; не переписаны.
Новых product questions/decisions:0. Remaining requirements blockers этого menu
scope:0. Mandatory analyze/issue ownership/source review/validation остаются
отдельными, requirements approval их не заменяет и не разрешает bypass.

Порядок decoder → independent menu projection → frozen tray rows → common owner
menu admission/Retry соответствует accepted T119. До integration обязательны
следующие implementation proofs, **не объявленные PASS этим report**: strict
decoder default/type/privacy regressions; native popup reentry/destruction;
source expiry/current до/после ожиданий; no-gap Retry replacement после actual
dialog drain; final-byte SDK/tests и installed menu/card/cabinet parity.
Menu никогда не запускает Record; прежний card Record/indicator/Stop сохраняются.

**Terminal M1 closure: C0/H0/M0/L0, shared18/0, decoder requirements PASS и menu
requirements PASS на указанных байтах.** Только этот reviewer-owned append;
product/norms/tasks/markers/Git/GitHub/VM/build/tests/audio не изменялись.

## Round242 — upcoming model/presenter requirements gate, 2026-10-05

**REQUIREMENTS PASS C0/H0/M0/L0.** Operation8 checked/0 unchecked,
wire5/0, launcher5/0, aggregate18/0. Round241 M1 closure подтверждён для текущей
ограниченной стадии upcoming projection в existing model/presenter. Новых
product questions/decisions и blocking requirement gaps:0. Это не source review
будущих шести файлов и не approval native popup/menu owner/Retry/installed T119.

Canonical workdir прежний; feature.json прочитан и подтверждает Feature200,
high-risk-product, заявленные branch codex/200-windows-followup и source_sha
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`. Git не запускался: нового independent
Git HEAD receipt нет. Pre-append report SHA-256 fresh matches
`955a2ff6f21503525513b37bb2ad82ebfede592e12c4f9a0034032a98a2287ca`.

Лично перечитаны current menu plan п.1–5/порядок стадий, data-model §8,
quickstart §16, spec menu clarification, bridge §10 menu append, research menu
решение, task T119 и actual criteria всех трёх checklists. Constitution VI/VII,
guidance risk lanes/reviewer ownership/reference-fidelity scoped reread выполнен;
high-risk lane сохранён. `speckit-checklist/SKILL.md` прочитан FULL и применён
для requirements-quality, без генерации checklist или проверки поведения кода.
Before/after checklist hooks disabled; prerequisites script/Git/hooks не
запускались по явной границе пользователя. Markers не переписаны.

### Подтверждённые требования стадии

| Область | Current evidence и обязательная граница |
| --- | --- |
| Accepted availability/context | Plan menu п.1/3/5, model §8, bridge §10: только authenticated owner/workspace accepted snapshot; failed refresh, invalidation/auth switch отзывают menu availability. Старый успешный snapshot не остаётся menu authority. |
| Independent projection | Spec menu clarification, plan п.1/3, model §8, quickstart16.2: card canSurface/due/dismissal, quiet/reminders и active capture не скрывают явные menu rows. Нельзя использовать card eligibility или presented pendingAction как menu source. |
| Sorted bounded projection | Plan п.1, model §8, quickstart16.2: startsAt, затем eventId, prefix12; unsorted13+ и equal-start cases заданы. Новый selector/count или дополнительная business-logic лента не вводятся. |
| Server flags/privacy | Plan п.1–2/model/quickstart16.1–2: принятые showUpcomingTime/showUpcomingTitle/allDay сохраняются как server presentation data; defaults и type refusal decoder не ослабляются, local quiet/show-title preferences их не заменяют. Private/hidden/generic labels и отсутствие safe link не создают launch authority. |
| Frozen target/current | Plan п.3–5/model/quickstart16.3/5: frozen eventId/startsAt/endsAt/link availability/URL identity и owner epoch, не row index новой проекции. Source current требует доступной принятой projection, unchanged target/context и original expiry; presentation-only change отличается от target/auth replacement. |
| Failure vs failed card | Plan п.3/model/quickstart16.2 явно требуют clear menu при refresh failure, даже если failed reminder card сохранена. Сохранение card/error для Retry не возвращает menu availability и не продлевает original action expiry. |

Operation CHK002/006/007/008 непосредственно покрывают current source/immutable
expiry/отдельные card semantics/границы стадий; CHK001/003/004/005 сохраняют один
owner, resolver deadlines, matching actual drain и recovery без terminal revival.
Wire CHK001–005 не расширяются native projection: нового envelope/URL/Record
payload, nonce authority или web cancel native menu нет. Launcher CHK001–005
сохраняют общий validator/fresh resolver/native lifecycle и отдельное installed
доказательство; model/presenter projection сама не выполняет launch/Record.

Original menu endsAt→checked monotonic expiry и no-extension правила остаются
принятыми Round241, не заменены card deadline. При source current нельзя
подменять frozen selected target новым event с тем же row index либо считать
факт stored snapshot доказательством accepted availability после failure.
Presentation-only flags/title change не даёт права переписать target активного
flight. Эта стадия готовит данные/current observation; action UUID admission,
native popup tracking, one-owner Retry и actual worker/SDK/dialog drain следуют
отдельно. Недостающая implementation proof не является дефектом этих требований.

### Exact current receipt / counts

Fresh SHA-256 и clock receipt **2026-10-05 19:44:42 UTC**; все normative bytes
побайтно совпали с одобренным Round241, не только с сообщением main:

| Артефакт | SHA-256 |
| --- | --- |
| spec.md | `b3edc920a6d6ad31b0be538c53a96637e087c43987f9d8133b58503a6bbf6911` |
| plan.md | `e5a36118f27ba0e3402b5adb5999b0cf853523af4b1a27fff834ac999f96391e` |
| tasks.md — T119 `[ ]` | `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f` |
| data-model.md | `d9d085d8a09f28c20e4e18a5359818780e8c33be186516506f98c939c53a5d46` |
| contracts/windows-native-web-bridge.md | `fcb99a1fc91a444cedb570aaa26ca490d71c33fbbfded9b82f5c129f12e1b542` |
| quickstart.md | `9a20a1cbf3737c5afb08cf8db70370af7f009cc803978f70b04a87d8a3e364be` |
| research.md | `62f381f1502a89c202b593f6ba7f8dddd6489fa9fd9a00e3a0696ea6e3f8b25f` |
| calendar-operation.md —8/0 | `a656adcd4d6cccf578cc7c98f385fe10ba5b422cfb47dba7e3662f8b24e0a834` |
| calendar-wire.md —5/0 | `0b58c484e25b5f37ec3b157f0bbe227ddcc2cff682dbae5ab0af882936796895` |
| calendar-launcher.md —5/0 | `99f1a945f2b557ece837ea484633d3e61af5a7838c0068a182bea17de22e4355` |

Constitution/flow/product-gates hashes совпали с прежними receipts:
`d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859`,
`5edf818b6ee27c7ee66d14edc003325ec7b16789eb1a195377cdeb901ae44887`,
`e5c39fb473dcf785f417b9785b0d6ba17fe23026906eedc08c0620c7a6f5d097`.
Actual checklist text прочитан, counts отдельно перечитаны/пересчитаны;18/0
относится только к указанным трём checklists, не всем gates Feature200.

**Terminal Round242: requirements PASS C0/H0/M0/L0, scoped18/0.** Only write —
этот append. Нет source/norm/tasks/markers/Git/GitHub/VM/tests/build/audio edits
или jobs; чужая dirty работа и предыдущие findings/approvals сохранены.
Source phase не начата. Mandatory analyze/ownership, последующие source/actual
native/installed validation и T119 closeout остаются самостоятельными gates.

## Round243 — frozen WindowsTray rows / nested-loop requirements, 2026-10-05

**REQUIREMENTS PASS C0/H0/M0/L0; недостающих нормативных решений:0.**
Допуск ограничен copied native rows/labels и lifetime `TrackPopupMenuEx`.
Не source approval WindowsTray, не интеграция AppMain menu admission/expiry/
Retry и не installed/full T119 acceptance. Existing high-risk-feature lane
сохраняет самостоятельные source/native/a11y/installed gates.

Canonical workdir и заявленный HEAD прежние; Git не запускался. Текущий
`.specify/feature.json` подтверждает feature200/branch/source_sha metadata,
не independent Git HEAD proof. Pre-append этого report:
`c03ce031b5fe8edb50b2150cb24b79d1496ddbbfe860bcf060079c17fe7afad8`.
Root AGENTS/guidance, constitution VI/VII и scoped spec menu clarification,
plan menu appendix, model§8, bridge§10, quickstart§16, tasks T119 перечитаны.
Применён speckit-analyze после полного личного чтения SKILL.md, только scoped
cross-artifact reasoning. Prerequisite command не запускался: script допускает
feature.json persistence/Git, запрещённые этим review. Paths сверены read-only;
before/after_analyze hooks в extensions.yml disabled, ничего не исполнялось.
Это не full-feature analyze command receipt. Единственный разрешённый append
следует прямой инструкции пользователя; нормы не исправляются.

### Достаточность требований / границы реализации

- **Состав и privacy:** plan menu1–2/quickstart16.1–2 задают startsAt/eventId
  prefix12, server title/time flags и allDay. Available непустое название
  показывается; available пустое после пробелов — «Без названия»; private,
  unavailable либо скрытое — «Встреча». HH:mm в существующем пользовательском
  часовом поясе, all-day «Весь день», hidden time отсутствует. Full safe
  accessibility text, native font/DPI fitting и no private title/URL diagnostics
  обязательны; caption layout/native text escaping — implementation details,
  не новый выбор продукта. Captions не являются target identity.
- **Availability без authority:** отсутствие безопасной snapshot HTTPS либо
  link=false оставляет строку видимой, но disabled. Snapshot URL не запускается;
  будущий consumer использует fresh resolver. Capture/quiet/reminders/dismissed/
  card deadline не скрывают rows и не запрещают явный menu Join. Existing
  Record/Stop/settings/history должны сохраняться; menu никогда не Record.
- **Обновление tracking:** plan menu3/5 требует EndMenu при изменении отображаемых
  rows/flags/auth и исключает stale selection. Capture-state change относится
  к этому правилу, когда меняет показываемые Record/Stop/доступность команд,
  а не вводит capture filter calendar rows. Не требуется новый таймер или
  безусловное EndMenu на каждом одинаковом refresh. Failed refresh/unavailable
  projection отзывает selection даже при сохранённой отдельной Retry-card.
- **Вложенный loop:** plan1682–1685 прямо требует локальные owning copies
  rows/handlers до выхода TrackPopupMenuEx, frozen event identity вместо row
  index новой проекции; перед callback — fresh alive/window/current projection.
  Alive-check должен безопасно предшествовать доступу к потенциально удалённому
  Impl; один cached HWND или старый row index не заменяет current proof.
  Callback может уничтожить owner: после него не обращаться к Impl, включая
  cleanup/уведомления. Quickstart16.3 задаёт destruction/update/auth во вложенном
  loop как отдельную проверку. Нормы достаточны без новой factory/interface.
- **Selection не flight:** presentation-only EndMenu отменяет незавершённый
  popup selection, но не уже принятый unchanged flight; normal close после
  выбора также не отменяет его. EndMenu/Hide/closing не actual drain. Это
  согласовано между plan3–5, data-model8 и bridge10. AppMain common owner,
  action UUID, checked original endsAt→steady expiry и Retry выполняются
  следующей стадией, не считаются реализованными этим rows slice.
- **Границы приёмки:** plan sequence явно decoder → model/presenter → frozen
  tray rows → common menu admission/Retry. Round242 source approval — dependency
  предыдущих bytes, не доказательство native popup lifetime. Quickstart16.3
  требует keyboard/screen-reader/theme/high-contrast/DPI/long-title и loop
  invalidation;16.6 отдельно installed exact MSIX. Тестовая callback injection,
  labels/unit tests либо compile сами по себе не закрывают эти проверки.

Scoped consistency findings/ambiguity/constitution conflicts/uncovered T119
requirements: **0**. Все перечисленные обязанности покрыты existing T119 и
plan menu1–5/quickstart16; отдельная задача, схема, launcher/client или продуктовый
выбор не требуются. Это не coverage% всего Feature200.

### Reviewer-owned counts и hashes

Все18 текущих criteria перечитаны, markers не переписаны. Operation CHK001–008
сохраняют one owner/current/source expiry/actual drain/staging; wire CHK001–005
не дают native menu web authority; launcher CHK001–005 сохраняют native outcomes
и отдельный installed proof. Новых unsupported требований в этой области нет.
Фактические counts: operation **8/0**, wire **5/0**, launcher **5/0**;
итого **18 checked / 0 unchecked**, только качество требований.

Fresh receipt **2026-10-05 20:01:05 UTC**; full-file hashes совпадают с approved
Round241/242 normative bytes:

| Артефакт | SHA-256 |
| --- | --- |
| spec.md | `b3edc920a6d6ad31b0be538c53a96637e087c43987f9d8133b58503a6bbf6911` |
| plan.md | `e5a36118f27ba0e3402b5adb5999b0cf853523af4b1a27fff834ac999f96391e` |
| tasks.md — T119 `[ ]` | `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f` |
| data-model.md | `d9d085d8a09f28c20e4e18a5359818780e8c33be186516506f98c939c53a5d46` |
| contracts/windows-native-web-bridge.md | `fcb99a1fc91a444cedb570aaa26ca490d71c33fbbfded9b82f5c129f12e1b542` |
| quickstart.md | `9a20a1cbf3737c5afb08cf8db70370af7f009cc803978f70b04a87d8a3e364be` |
| research.md | `62f381f1502a89c202b593f6ba7f8dddd6489fa9fd9a00e3a0696ea6e3f8b25f` |
| calendar-operation.md —8/0 | `a656adcd4d6cccf578cc7c98f385fe10ba5b422cfb47dba7e3662f8b24e0a834` |
| calendar-wire.md —5/0 | `0b58c484e25b5f37ec3b157f0bbe227ddcc2cff682dbae5ab0af882936796895` |
| calendar-launcher.md —5/0 | `99f1a945f2b557ece837ea484633d3e61af5a7838c0068a182bea17de22e4355` |

Root AGENTS, constitution, spec-kit-flow и product-gates hashes неизменны:
`384c41c0b1674a3daf75d0e57646379198295c3f8452012c8101fc6332bec58b`,
`d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859`,
`5edf818b6ee27c7ee66d14edc003325ec7b16789eb1a195377cdeb901ae44887`,
`e5c39fb473dcf785f417b9785b0d6ba17fe23026906eedc08c0620c7a6f5d097`.

**Terminal Round243: REQUIREMENTS PASS C0/H0/M0/L0, scoped18/0.**
Only write — этот append; старые findings/receipts сохранены. Нет source/norm/
tasks/markers/Git/GitHub/VM/tests/build/audio изменений или jobs. Source review
нового WindowsTray кода не начат. AppMain menu admission/expiry/Retry, launch,
actual work completion, native/installed/full T119 остаются отдельными gates.

## Round243 — timezone counterevidence / M1, 2026-10-05

**UPDATED REQUIREMENTS VERDICT: C0/H0/M1/L0; полный rows + HH:mm slice НЕ PASS.**
Предыдущий Round243 PASS выше сохранён как история и уточняется этим appendix.
Он ошибочно считал фразу «существующий пользовательский часовой пояс» достаточной
для Windows formatter. Продуктовый результат задан, но его Windows trust-boundary
design не задан; это реальный technical-planning gap, не запрос нового UX выбора.

### M1 — отсутствует account-bound user-time context для Windows

Location: plan menu2 (`plan.md:1674` — «существующем пользовательском часовом
поясе»), quickstart16.2, data-model8 menu fields/identity. Нормы не говорят,
откуда Windows получает выбранный user timezone/готовую user-time label,
какой trusted context её владелец, как сбрасываются auth/session/origin/document
и stale read, как timezone presentation update прекращает старый tracking.
Отсутствие equivalent transport сейчас не разрешает всегда форматировать system
localtime либо объявить незавершённый user TZ готовым.

Main сообщил pinned-reference открытие CalendarTray на
`721b5125d799ea798a4af0b3625e18d3c1109039`. Reviewer НЕ вычитывал этот Git blob:
Git запрещён. Независимо лично прочитан current Mac working-tree
DesktopUserTimeContext.swift целиком, CalendarTray.swift328–335 и narrow
EmbeddedCabinetWebView.swift2605–2614 плюс focused reference tests14–70.
Current code подтверждает именно user-context, не always-system-local:

- `timeText`: allDay → «Весь день»; HH:mm DateFormatter в
  `DesktopUserTimeContext.shared.timeZone`.
- Context хранит origin/userId/sessionId/preferredTimeZone; fallback
  `.autoupdatingCurrent`, preference эфемерна, reset меняет revision.
- Native read script в лично прочитанном current файле использует существующие
  `graf-time-user`, `graf-time-session`, `graf-time-preferred`, не предложенную
  новую schema `graf-user-timezone`. Reader ограничен approved cabinet routes,
  проверяет current document/documentURL/revision; auth reset отвергает старый
  callback. Named zone проверяется Foundation и ограничением100 символов.
- Focused read-only rg по Windows не нашёл equivalent user-time/TZ transport.
  Это текущая отсутствующая интеграция, не доказательство дефекта Mac и не
  основание менять server/Mac или clock/capture semantics.

**Перед кодом полного formatter нужен narrow norm/design closure:** выбрать
существующий trusted native context/read pattern без нового bridge payload;
явно описать owner/auth/session/document binding, validation timezone,
reset/stale-read rules и fallback только по установленной reference семантике.
Нужен Windows-native способ корректно форматировать выбранную именованную зону
(включая DST), либо trusted, account-bound уже formatted plain time label.
System localtime нельзя использовать вместо валидной выбранной user zone.
Изменение user-time presentation прекращает старый popup selection, но не
переписывает frozen target/исходный expiry уже принятого flight.

**Допустимое разделение стадии:** safe-title, copied frozen rows и nested-loop
lifetime остаются достаточно определены. Main может сначала документировать
ограничение renderer на externally supplied validated/current user-time label
без native TZ resolver в этом срезе. Такой label — presentation data, не URL,
action/expiry authority; источник/проверка актуальности должны быть явными.
Это conditional route, не approval ещё не описанного API/transport и не
готовая timezone functionality. Hidden-time/allDay не доказывают общий HH:mm.
Для полного rows/time product slice M1 остаётся blocker до narrow closure.

### Receipt / counts / boundaries

Clock **2026-10-05 20:02:47 UTC**. Pre-counterevidence report SHA-256:
`77378dbf200e786dbc7f367a0bf620a94535ae5566628384ad10e3cd4de4690f`.
Лично прочитанные CURRENT working-tree Mac files, не pinned-blob proof:

| Файл | SHA-256 |
| --- | --- |
| apps/macos/RecApp/Sources/Cabinet/DesktopUserTimeContext.swift | `22ebc7a441aaa6fdbbe295b158d7361ff94aca7f60426478df782baca1f6c9ef` |
| apps/macos/RecApp/Sources/Calendar/CalendarTray.swift | `4eca72ce427b7614395188d0805a4fb17102099bd8d40399735c5367d9de80c1` |

Normative hashes остаются exact receipt предыдущего Round243 appendix;
никто не исправлял нормы этим review. Actual existing markers **8/0 +5/0 +5/0
=18/0** не переписаны по запрету. Эти физические counts НЕ означают новый
unconditional PASS user-time требований: affected context/staging основания
operation CHK002/008 требуют M1 closure для полного formatter. Новые markers
не добавлены, historical checklists не нормализованы.

**Terminal updated Round243: C0/H0/M1/L0; user-time formatter requirements STOP.**
Safe-title/frozen-row/lifetime часть — conditional scoped continuation, без
timezone completion claim. Единственная запись — этот appendix; нет source/
norm/tasks/markers/Git/GitHub/VM/build/tests/audio writes/jobs. Main's pinned
receipt, current-reference source чтение и будущая Windows implementation
proof разделены. Full T119/installed/launch/clock/storage не переаудируются.

Уточнение точной ссылки M1 после line-number receipt: timezone clause начинается
в `plan.md:1673`;1674 — продолжение того же пункта. Все семь normative hashes
и три checklist hashes повторно сверены после appendix и остались прежними.

## Round243 — timezone M1 closure, 2026-10-05

**REQUIREMENTS PASS C0/H0/M0/L0; M1 CLOSED для revised normative bytes ниже.**
Прежние PASS→M1 findings сохранены как история. Только timezone closure и
relevant prior T119 menu boundaries; не source, native API feasibility или
installed acceptance. Pre-append report SHA-256:
`4857d123d8e0f316bf25c928ae5af8e672fbd070a2511f6cf9b6b6d38244d927`.

Лично прочитаны новые шесть paragraphs: spec753–759, plan1732–1800,
data-model372–379, bridge537–545, quickstart606–626, research2946–2967.
speckit-analyze SKILL.md полностью перечитан; scoped read-only consistency
reasoning сохраняет прежний запрет prerequisite persistence/Git/hooks. User-
authorized append не изменяет нормы; это не whole-feature command receipt.

### Закрытие trust / ownership / formatter gap

- Spec теперь прямо различает выбранную account zone и system fallback при
  отсутствии принятой настройки; timezone эфемерна и account/session/document
  bound. DST определяется датой события, не текущим UTC offset.
- Plan1–2 задают existing native ExecuteScript read после cookie/native account
  reconciliation, current trusted main document и конкретные allowed route
  kinds. Auth/provider/payment/frame/external/recovery/failed документы не
  устанавливают context. Exact5 owned strings/2048-byte result, UUID IDs,
  zone100 ASCII/documentURL1024, duplicates/unknown/null/missing/type refusals
  тестируемы; нет нового web command/endpoint/cookie reader/скрытого fetch.
- Plan3–4 задают dispatch/completion native account/workspace/auth generation/
  token identity + document generation/nonce/URL + context revision. Metadata
  не auth proof; session UUID не заменяет native token/generation. Stale result
  не очищает более новый context; invalid current result сбрасывает preference.
  Logout/switch/detach/failed-document и accepted replacement revocation явно
  описаны. Непустая unknown zone не сохраняет старую preference; empty/absent
  preference использует свежую system zone. Persistence/logging запрещены.
- Plan5 задаёт Windows.Globalization.Calendar, IANA/UTC native validation,
  Gregorian/24-hour HH:mm из UTC instant с DST на дату события; finite/range/
  tick overflow guard и отсутствие выдуманного времени при refusal. Не
  допускаются fixed-offset table, localtime вместо chosen zone или portable
  named-zone simulation как native proof. Quickstart задаёт UTC/Kathmandu/
  New_York/Berlin DST, empty/unknown/NaN/Inf/range cases без изменения OS zone.
- Plan6/bridge/model связывают display preference/system-zone change с labels
  и прекращением старого popup selection, не с отменой unchanged admitted Join
  или изменением immutable action expiry. Ранее принятые frozen rows/callback
  lifetime/current fences сохранены; timezone context не второй Join owner.

API choice independently проверен только по primary documentation:
[Calendar.ChangeTimeZone](https://learn.microsoft.com/en-us/uwp/api/windows.globalization.calendar.changetimezone?view=winrt-26100)
и [Calendar constructors](https://learn.microsoft.com/en-us/uwp/api/windows.globalization.calendar.-ctor?view=winrt-26100)
подтверждают IANA ID и native language/calendar/clock/timezone parameters.
Это не проверка OS behavior/DST runtime/SDK build; synthetic feasibility probe
остаётся у main и не объявлен PASS reviewer-ом.

### Same-page successful save — явная граница accepted context

**Fresh confirmed document parity достаточно; немедленный GRAFTime→native sync
в этом срезе не требуется и не одобрен.** Plan6 прямо требует сохранённое на
сервере preference проверять на свежем confirmed document, не форме; quickstart
отдельно называет server save + new confirmed document. Поэтому same-page
successful save с неизменным metadata сам по себе НЕ новая accepted native zone:
до нового guarded read текущая last-confirmed preference остаётся прежней
(либо system fallback, если preference отсутствует/была отозвана). Dirty/failed
save также не назначает native zone. При новом документе с updated metadata
current guarded completion принимает новую зону и обновляет menu tracking.

Эта ожидаемая последовательность следует существующим revised нормам, не
добавляет protocol/новый UX выбор. Same-page test должен различить web GRAFTime
update и native accepted-context update; нельзя выдать первое за второе.
Если будущая стадия потребует немедленный native refresh после save, ей нужен
отдельно описанный trusted synchronization path, а не доверие form value.

Narrow current-reference read подтвердил: settings-autosave.js175 меняет GRAFTime
на saved, не graf-time-preferred; DesktopUserTimeContext читает meta; existing
Mac host reader guarded current document/revision/documentURL. Это current
working-tree evidence, НЕ самостоятельно вычитанный pinned Git blob; pinned
`721b5125d799ea798a4af0b3625e18d3c1109039` receipt в revised research принадлежит
main. Описанный fresh-document boundary согласован с этим actual reference
flow; отдельная Windows реализация не объявляется готовой по чтению Mac.

### Exact revised receipt / counts / terminal

SHA-256 повторно сверены **2026-10-05 20:14:50 UTC**, совпадают с submission:

| Артефакт | SHA-256 |
| --- | --- |
| spec.md | `b411bfb620e9d571422f9c423b0ae193ed70e87303d08e84a4b9844e32f81658` |
| plan.md | `527e660d9e1682e7a0f0a79118ea4bab38d4c174542b49c0113f571528a5b89c` |
| data-model.md | `8dd54012c3bfe4003cd18db98ebc67e0b7730cbbdfb6523b881cce4cdc15ec19` |
| contracts/windows-native-web-bridge.md | `21bffa56631901952ae778871f26785522d839eafc8afb9942b488ff22bbd0fa` |
| quickstart.md | `1065b1970125f2ea7cc323c0177d07485e34a339a6b7195df4af9aa65a5cb683` |
| research.md | `0e7659d4cf5136d392bde28cb273c6ca0be6af2ac3eca50e23a617e1af129522` |
| tasks.md — unchanged T119 `[ ]` | `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f` |

Actual counts повторно пересчитаны: operation8/0, wire5/0, launcher5/0,
**18checked/0unchecked**. Checklists hashes unchanged
`a656adcd4d6cccf578cc7c98f385fe10ba5b422cfb47dba7e3662f8b24e0a834`,
`0b58c484e25b5f37ec3b157f0bbe227ddcc2cff682dbae5ab0af882936796895`,
`99f1a945f2b557ece837ea484633d3e61af5a7838c0068a182bea17de22e4355`.
M1 closure восстанавливает affected context/staging основания CHK002/008 без
переписывания markers. Scoped ambiguity/constitution/coverage blockers0;
existing T119 покрывает this transport/formatter stage, новая задача не нужна.

**Terminal: C0/H0/M0/L0, M1 CLOSED, requirements scoped18/0.** Only write —
этот append. Нет code/norm/tasks/markers/Git/GitHub/VM/build/tests/audio changes
или probes; чужая dirty работа сохранена. Native feasibility, source review,
actual host/account binding, frozen tray lifetime, AppMain menu admission/
expiry/Retry и installed/full T119 acceptance остаются отдельными доказательствами.

## Round244 — requirements revalidation: host/account user-time integration

2026-10-05. Canonical worktree: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`.
Branch/HEAD из submission: `codex/200-windows-followup`,
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`; Git не запускался, поэтому это
не новая независимая проверка HEAD. Scope — только plan Round243 steps1–6 и
соответствующие user-time paragraphs spec/model/bridge/quickstart/research,
T119 tasks и три текущих checklist. Root guidance, constitution, relevant
Spec Kit/reference-fidelity rules и `speckit-analyze` прочитаны лично.
High-risk lane сохранён; scoped consistency analysis не заменяет full-feature
analyze или источник доказательств реализации. Prerequisite script/hooks не
запускались: запрет Git/других записей сохранён, feature metadata прочитаны
read-only; auto-commit hook disabled.

**Requirements PASS: C0/H0/M0/L0; новый technical mapping gap не выявлен.**

- Plan1–2 и bridge определяют существующий ExecuteScript, подтверждённый native
  account/cookie reconciliation и current trusted main document; exact five
  strings/raw2048/decoded duplicates/UUID/zone100/documentURL1024 — структурная
  граница, не доказательство account/auth, валидной IANA zone или Join authority.
- Plan3–4 требуют captured native account/workspace/auth generation/token
  identity плюс document generation/nonce/URL/display revision и повторную
  проверку перед применением. Metadata session UUID не заменяет native token.
  Stale callback игнорируется без сброса newer context; invalid **current**
  completion, logout/session/account/origin change и failed/detached document
  исключают reuse старого preference. Missing/empty/unknown-zone paths имеют
  явный system fallback; контекст только в памяти, без logging/persistence.
- Plan5–6, model и quickstart задают native zone validation/event-date DST,
  свежую system zone и label refresh/EndMenu. Presentation change не отменяет
  unchanged accepted Join и не изменяет immutable steady expiry. Same-page
  saved value не новая native preference до нового confirmed guarded document;
  прежняя принятая staging граница остаётся, form/GRAFTime не authority.
- Требования дают проверяемые current/stale/reset/account-switch и same-page
  сценарии без нового protocol/client/service/task. T119 остаётся открытым;
  actual callback ordering, cookie/account mapping, alive/lifetime fencing и
  native integration будут проверяться по исходникам/исполнению отдельно.
  Требований достаточно для этого этапа; готовность будущего кода не заявлена.

Текущие SHA-256 сверены лично; все совпадают с approved Round243 bytes:

| Артефакт | SHA-256 |
| --- | --- |
| spec.md | `b411bfb620e9d571422f9c423b0ae193ed70e87303d08e84a4b9844e32f81658` |
| plan.md | `527e660d9e1682e7a0f0a79118ea4bab38d4c174542b49c0113f571528a5b89c` |
| data-model.md | `8dd54012c3bfe4003cd18db98ebc67e0b7730cbbdfb6523b881cce4cdc15ec19` |
| contracts/windows-native-web-bridge.md | `21bffa56631901952ae778871f26785522d839eafc8afb9942b488ff22bbd0fa` |
| quickstart.md | `1065b1970125f2ea7cc323c0177d07485e34a339a6b7195df4af9aa65a5cb683` |
| research.md | `0e7659d4cf5136d392bde28cb273c6ca0be6af2ac3eca50e23a617e1af129522` |
| tasks.md | `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f` |
| calendar-operation.md | `a656adcd4d6cccf578cc7c98f385fe10ba5b422cfb47dba7e3662f8b24e0a834` |
| calendar-wire.md | `0b58c484e25b5f37ec3b157f0bbe227ddcc2cff682dbae5ab0af882936796895` |
| calendar-launcher.md | `99f1a945f2b557ece837ea484633d3e61af5a7838c0068a182bea17de22e4355` |

Actual counts заново пересчитаны: operation8/0 + wire5/0 + launcher5/0 =
**18 checked / 0 unchecked**. Markers не изменялись. Scoped C0/H0/M0 threshold
выполнен; новые ambiguities/constitution conflicts/coverage blockers отсутствуют.
Only write — этот append; исторические findings сохранены. Нет code/norm/tasks/
Git/GitHub/VM/build/test/audio действий. Main source audit не дублирован;
crypto/capture и whole-feature/installed acceptance вне этого заключения.

## Round245 — requirements continuity: frozen tray rows / common menu owner Retry

2026-10-06. **PASS, C0/H0/M0/L0; scoped requirements18/0.** Canonical worktree
`/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`; branch/HEAD
из submission/feature metadata `codex/200-windows-followup` /
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1` (не новая Git-проверка).
Existing high-risk-product lane сохранён. Лично перечитаны affected spec US2/
FR006/menu clarification, plan1166–1184/operation/launcher и menu1652–1730,
timezone1732–1800, model346–379, bridge516–545, quickstart§16/user-time,
research menu/time decisions, T119 и все три checklist; root/guidance/
constitution gates учтены. Current source Presenter/Tray/AppMain не аудирован:
main владеет этой параллельной проверкой, implementation/source approval здесь нет.

`speckit-analyze` прочитан полностью и применён как scoped read-only consistency
analysis. Указанная пользователем запись только reviewer report соблюдена;
prerequisite script не запускался из-за Git/возможной metadata записи. Current
feature.json прочитан read-only. Before/after-analyze hooks просмотрены:
auto-commit disabled, hooks не выполнялись. Это не full-feature analyze receipt.

### Основания допуска следующих этапов

- Plan1–2/model/quickstart определяют startsAt/eventId sorted prefix12 из одного
  authenticated available snapshot, отдельно от card due/dismissal/quiet/capture.
  Title available/nonempty → safe title; empty → «Без названия»; private/hidden/
  unavailable → «Встреча». Server flags управляют title/time, all-day → «Весь день»;
  accepted account zone/event-date DST либо свежая system fallback, не fixed
  offset/always-local. Snapshot HTTPS/link availability только включает строку,
  не разрешает launch; без safe link строка видна disabled. Native width/DPI,
  полный safe accessibility name, Record/Stop/settings/history сохраняются.
- Plan3/model/quickstart явно требуют invalidate menu при failed refresh/auth
  независимо от retained failed card. Rows и handlers копируются локально на весь
  TrackPopupMenuEx; selection несёт frozen event identity, не row index.
  Projection/flags/auth/time presentation change вызывает EndMenu. После nested
  loop alive/window/current projection проверяются **до** copied callback; после
  callback потенциально уничтоженный Impl не читается. Эти требования достаточны
  для bounded lifetime design; actual implementation proof впереди.
- Plan4–5 задают native action UUID/owner epoch/full frozen target и single checked
  endsAt-wallNow→steady expiry при admission, invalid/overflow/expired refusal.
  Original expiry не продлевают refresh/Retry/clock change. Normal popup close и
  presentation-only change не отменяют уже admitted unchanged target; target/
  owner/projection unavailable/interaction/exit/expiry invalidation отменяет
  applicability. Это не actual drain и не card pendingAction expiry.
- Plan6–7/bridge/model согласуют общий existing owner/resolver/launcher/dialog,
  menu never joinAndRecord. Failure Retry — owned dialog после предыдущего
  matching actual drain; terminal UI/Hide/Cancel/unknown Status не release busy.
  Explicit current Primary + matching dialog terminal дают новый request/operation
  с тем же source/original expiry. Замена выполняется одной reentrancy-protected
  UI transition без admission gap; budget click+15s включает ожидание dialog exit,
  не restart-at-poll. Browser recovery остаётся отдельным purpose с прежним opening
  lifecycle; stale/auth/expiry не запускают Retry/launch, cached URL запрещена.
- Operation/work identities, drain при interactionPermit=false, latest-current
  checks до/после resolver/OS/dialog и indeterminate handle удержание уже заданы
  operation/launcher checklist. Menu source не создаёт новый service/protocol/
  authority. Time context только presentation; labels/EndMenu не подменяют fresh
  native account/session validation. Same-page saved preference staging unchanged.

Scoped coverage: семь menu design obligations plan1–7 и timezone integration
plan5–6 имеют existing T119 coverage; unmapped affected obligations0, новых
задач/продуктовых вопросов0, ambiguity/constitution/continuity blockers0.
Точные internal types/callback signatures выбирает минимальная implementation;
их отсутствие в requirements не новый design blocker. Нужны отдельные test-first
и source/native lifetime/Retry proofs, не новые требования.

### Fresh normative SHA-256 / actual counts

| Артефакт | SHA-256 |
| --- | --- |
| spec.md | `b411bfb620e9d571422f9c423b0ae193ed70e87303d08e84a4b9844e32f81658` |
| plan.md | `527e660d9e1682e7a0f0a79118ea4bab38d4c174542b49c0113f571528a5b89c` |
| data-model.md | `8dd54012c3bfe4003cd18db98ebc67e0b7730cbbdfb6523b881cce4cdc15ec19` |
| contracts/windows-native-web-bridge.md | `21bffa56631901952ae778871f26785522d839eafc8afb9942b488ff22bbd0fa` |
| quickstart.md | `1065b1970125f2ea7cc323c0177d07485e34a339a6b7195df4af9aa65a5cb683` |
| research.md | `0e7659d4cf5136d392bde28cb273c6ca0be6af2ac3eca50e23a617e1af129522` |
| tasks.md — T119 `[ ]` | `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f` |
| calendar-operation.md | `a656adcd4d6cccf578cc7c98f385fe10ba5b422cfb47dba7e3662f8b24e0a834` |
| calendar-wire.md | `0b58c484e25b5f37ec3b157f0bbe227ddcc2cff682dbae5ab0af882936796895` |
| calendar-launcher.md | `99f1a945f2b557ece837ea484633d3e61af5a7838c0068a182bea17de22e4355` |

Лично сверены unchanged hashes и заново пересчитаны markers:
operation8 checked/0 unchecked + wire5/0 + launcher5/0 = **18/0**.
Markers не менялись. Scoped C0/H0/M0 threshold выполнен; требований достаточно
для следующих tray rows/common menu owner Retry stages без нового product choice.
SDK exec26912 по submission live/pending — не опрашивался, не перезапускался,
terminal/PASS не объявлен. SourceM1 closure/earlier tests не подменяют будущую
tray/menu/installed acceptance. Only write — этот append. Нет norm/code/tasks/
Git/GitHub/VM/build/test/audio действий; crypto/capture/whole Feature200 вне scope.

## Round246 — requirements continuity before frozen Tray rows / common menu source / Retry

2026-10-06 (fresh read timestamp `2026-10-05T21:55:07Z`). **PASS requirements;
C0/H0/M0/L0; 18 checked / 0 unchecked.** Canonical worktree:
`/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`. Branch/HEAD
`codex/200-windows-followup` / `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`
из submission и лично прочитанного feature.json, не новая Git-проверка.
High-risk-product lane сохранён; это допуск требований к следующему bounded
этапу, не source/native/installed acceptance.

Лично перечитаны все18 критериев operation/wire/launcher, затронутые FR002/005/
006/015, SC002/006/009 и menu/time clarifications; plan T119 operation/wire/
launcher, menu1652–1730 и user-time1732–1800; model§8; bridge§10; quickstart§13/16;
research operation/menu/time decisions; открытый T119. Учтены root guidance,
конституция I/II/III/IV/VI/VII, product privacy/reference-fidelity и validation
boundaries. Предыдущий Round245 verdict не заменял новое чтение.

`speckit-analyze` прочитан полностью и применён к ограниченной проверке
согласованности. Before/after-analyze hooks просмотрены: commit hooks disabled;
ничего не выполнялось. Prerequisite script не запускался из-за запрета Git и
записей вне reviewer report; пути закреплены canonical submission/feature.json.
Единственная разрешённая запись — этот append, явно заданный пользователем.
Это не полный feature analyze и не новый issue-sync receipt.

### Повторная проверка критериев и преемственности

| Группа критериев | Текущее основание требований | Результат |
| --- | --- | --- |
| Operation CHK001–002 | Один общий cabinet/card/menu owner; exact origin/owner/workspace/token/auth generation и document либо frozen native action identity/epoch; menu не использует reminder pending action. | 2/0 |
| Operation CHK003–004 | Initial/recovery resolver15s от admission/explicit click, queue входит; terminal UI не drain, matching operation/work IDs и actual worker/SDK/dialog completion, завершения забираются при interactionPermit=false. | 2/0 |
| Operation CHK005–006 | Browser recovery сохраняет opening того же request; menu failure Retry — новый request/operation после matching dialog drain и explicit current Primary, прежний source/expiry, click+15s без переноса budget на OS/user wait. | 2/0 |
| Operation CHK007–008 | Card close только handoff, Record требует fresh current/prerequisites; menu never Record; helper/adapter/source/native/installed proofs разделены, existing T119 без второго owner/client/factory. | 2/0 |
| Wire CHK001–002 | Exact join3/cancel2 UUID fields без URL/Record; исходный strict JSON до SDK collapse, decoded duplicate/Unicode/64KiB/depth/owned-result guards; menu не расширяет wire schema. | 2/0 |
| Wire CHK003–005 | Replay-before-cap1024 без eviction, cap exception; matching current document cancellation/invalidation до nonce revoke не затрагивают menu/actual drain; host/shim/common owner/installed этапы разделены. | 3/0 |
| Launcher CHK001–003 | Target только validated HTTPS/пinned conversion, не calendar family; discard-only cancellation без OS Cancel/Close; natural terminal, indeterminate status и startFailed scope различены, неизвестность удерживает lease. | 3/0 |
| Launcher CHK004–005 | Guard/current перед dispatch и после ожиданий, отдельные operation/work IDs, no automatic retry/launch/Record; API outcomes не доказывают receiver/installed/auth/capture. | 2/0 |

Menu plan1–7 и user-time plan5–6 полностью сопоставлены existing T119:
**9/9 affected design obligations covered**, unmapped0, ambiguous0,
constitution conflicts0. Это scoped coverage, не 100% выполнения Feature200.
Сортировка/prefix12, независимость от card/quiet/capture, server flags/private/
empty/all-day labels, accepted account zone/event-date DST/system fallback,
safe-link disabled rows и сохранение Record/Stop/settings/history определены.
Refresh failure очищает menu даже при failed card. EndMenu на изменении
projection/auth/labels, локальные copied rows/handlers на весь nested loop,
alive/window/current projection до callback и запрет обращения к Impl после
callback дают проверяемый lifetime contract без новой UI/schema.

### Предыдущая карта потока — необходимые условия реализации, не source PASS

Read-only сверены узкие места текущего потока: WindowsTray.cpp430–453 хранит
menu items локально, но dispatch через отложенный WM_COMMAND нельзя использовать
для lookup нового row index; CalendarJoinOperation.cpp56–87 не считает terminal
attempt current и выдаёт dialog work только из opening; AppMain.cpp3677–3690
пока различает document/card source, 3867–3877 ждёт native thread signal → join →
get → matching completion, 3935–3957 содержит browser-purpose dialog и cleanup;
CalendarFlight4316–4328 ещё не frozen menu source. Это не повторный source audit.

Следующий код должен обеспечить уже предписанные нормы:

- Frozen menu target/owner epoch/action UUID и independent source-current,
  single checked endsAt-wallNow→steady expiry при admission. Refresh/Retry/
  clock change не пересчитывают его. Presentation-only EndMenu не отзывает
  уже admitted unchanged target; auth/target/unavailable/expiry — отзывает.
- Timeout может закончить result попытки, но не worker lease. После actual
  matching drain общий owner сохраняется для failure Retry dialog; terminal
  попытку нельзя оживлять через opening/recover. Нужна минимальная поддержка
  owned failure-dialog/reservation в existing helper/flight, не второй owner.
- Отдельный native-only dialog purpose от browser recovery. Primary фиксирует
  click time; только matching actual dialog drain + fresh source/auth/expiry
  допускают новый request/operation с исходным expiry. Замена защищена от
  reentrancy, без flight-reset/admission gap. Если click+15s уже истёк при poll,
  позднее закрытие диалога не создаёт свежие15s. Старые callback/terminal/cancel
  не освобождают новую попытку, неизвестный exit остаётся busy.

Эти трудности уже определены plan6–7/model/bridge/quickstart; отсутствие такого
API в текущем helper не дефект требований и не разрешение принять намерение за
actual drain. Новых продуктовых решений/clarification blockers0. Отдельные
test-first/source/native popup/dialog/thread lifetime proofs обязательны.

### Fresh exact SHA-256 и повторно прочитанные totals

| Артефакт | SHA-256 |
| --- | --- |
| spec.md | `b411bfb620e9d571422f9c423b0ae193ed70e87303d08e84a4b9844e32f81658` |
| plan.md | `527e660d9e1682e7a0f0a79118ea4bab38d4c174542b49c0113f571528a5b89c` |
| data-model.md | `8dd54012c3bfe4003cd18db98ebc67e0b7730cbbdfb6523b881cce4cdc15ec19` |
| contracts/windows-native-web-bridge.md | `21bffa56631901952ae778871f26785522d839eafc8afb9942b488ff22bbd0fa` |
| quickstart.md | `1065b1970125f2ea7cc323c0177d07485e34a339a6b7195df4af9aa65a5cb683` |
| research.md | `0e7659d4cf5136d392bde28cb273c6ca0be6af2ac3eca50e23a617e1af129522` |
| tasks.md — T119 `[ ]` | `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f` |
| calendar-operation.md | `a656adcd4d6cccf578cc7c98f385fe10ba5b422cfb47dba7e3662f8b24e0a834` |
| calendar-wire.md | `0b58c484e25b5f37ec3b157f0bbe227ddcc2cff682dbae5ab0af882936796895` |
| calendar-launcher.md | `99f1a945f2b557ece837ea484633d3e61af5a7838c0068a182bea17de22e4355` |

Все текущие нормативные/checklist hashes совпали с Round245. Actual counts:
operation8/0 + wire5/0 + launcher5/0 = **18/0**. Markers не переписывались.
Scoped analyze threshold C0/H0/M0 выполнен; L0. История findings сохранена.

Последняя квитанция submission, **main-reported, не reviewer-executed**:
Round245 projection source approved; SDK build0/Core0, portable45/45;
serial native **48/49, OwnerTimeout300s — NOT overall PASS**; старые jobs terminal.
Причина storage failure здесь не исследовалась, не объявляется race/не связана
доказательством с требованиями T119 и не позволяет закрыть общую validation.
Новых jobs/VM/build/tests не было. Native/installed T119, storage/audio/physical
acceptance и whole Feature200 остаются открытыми. Только reviewer-owned append;
norm/source/tasks/markers/Git/GitHub и пользовательские dirty файлы не менялись.

## Round247 — requirements continuity: owned menu failure Retry

2026-10-06, fresh read `2026-10-05T22:36:28Z`. **PASS requirements;
C0/H0/M0/L0; operation8/0 + wire5/0 + launcher5/0 = 18/0.** Canonical:
`/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`.
Branch/HEAD `codex/200-windows-followup` /
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1` закреплены submission/feature.json,
не новой Git-проверкой. High-risk-product lane сохранён. Gate допускает
test-first реализацию уже принятого Retry, не одобряет будущий source/installed.

Лично перечитаны действующие operation/wire/launcher критерии, scoped spec
FR002/005/006/015 и SC002/006/009/menu clarifications, plan T119 operation и
menu1655–1724, bridge§10, model§8, quickstart§16, research menu rationale и
открытый T119. Применены root guidance, constitution/privacy/reference-fidelity
и разделение validation evidence. `speckit-analyze` прочитан полностью;
согласованность проверена только для этого scope. Commit hooks disabled;
prerequisite/Git/issue-sync не запускались. User-authorized write — лишь этот
append. Исторические source findings не превращались в новые requirements STOP.

### Scoped consistency / обязательные условия следующего source review

| Обязательство | Нормативное основание | Verdict |
| --- | --- | --- |
| Failed result не означает actual drain; Retry dialog только после завершения предыдущего matching work. | Plan operation + menu7; launcher CHK002–004 | PASS |
| Retry dialog/ticket и reservation принадлежат тому же common owner; неизвестный SDK/dialog exit удерживает busy до natural terminal/выхода процесса. | Plan menu6–7; bridge§10; operation CHK001/004 | PASS |
| Старый failed attempt не возвращается в opening/resolving; matching dialog drain + explicit current Primary дают новый operation/request. | Plan menu7; model§8; operation CHK005 | PASS |
| Новый attempt сохраняет исходный frozen source/event/owner/action identity и monotonic expiry; никакого повторного endsAt-wallNow conversion. | Plan menu4–5/7; model§8; operation CHK002/006 | PASS |
| Budget click+15s включает dialog exit/dispatch delay; поздний poll не начинает новые15s. | Plan menu7; quickstart§16.4 | PASS |
| Замена защищена от reentrancy, без admission gap; старые IDs/callback не освобождают новый flight. | Plan menu7 + operation work IDs; bridge§10 | PASS |
| Fresh source/auth/context/expiry проверяются до/после ожиданий и перед новым dispatch; cancelled/stale не создают Retry/launch. | Plan menu5/7; bridge§10; quickstart§16.5 | PASS |
| Только fresh resolver; no cached URL/autoRetry/new owner/wire fields; menu never Record, browser recovery остаётся отдельным purpose. | Plan menu6–7; model§8; wire CHK001/005 | PASS |

**8/8 affected obligations mapped to existing T119; unmapped0, ambiguous0,
constitution conflicts0. Scoped analyze threshold C0/H0/M0 выполнен, L0.**
Все18 критериев остаются evidence-supported требованиями, markers не менялись.
Это не процент исполнения Feature200 и не приёмка нативной реализации.

### Receipt предложенного helper design — без source approval

Предложенные explicit menuRetry/nativeAction opt-in, failed reservation,
отдельный retryCurrent, новый cancellation/dialog ticket после старого drain и
atomic retry совместимы с указанными нормами. Reservation сохраняет владение,
а не применимость старого terminal result. Strict context comparison должен
оставлять исходные поля неизменными; caller дополнительно доказывает актуальность
frozen target/projection, а не только равенство переданного ctx. NativeAction
сам по себе не доказывает menu: opt-in задаётся trusted menu caller, card/web
не приобретают этот Retry path. Новой schema/пользовательского решения не нужно.

Условия проверки будущих bytes: cancel/source expiry снимают применимость
reservation, но не actual pending ticket; failed completion остаётся drain-only.
retryDialog создаёт не более одного owned child и не принимается до actual
matching old-work drain. retry требует доказанного matching dialog drain и
записанного explicit Primary для этой попытки, не произвольного timestamp caller.
CLICK/now и click+15s проверяются без future timestamp/overflow/продления исходного
expiry. Новый request/operation ID и cancellation готовятся до mutation;
allocation failure не оставляет admission gap/частично заменённое состояние.
Старые dialog/work callbacks не могут затронуть новую попытку. `retryOffered`
относится к одной failed попытке; это не новый общий лимит явных повторов.
Контекст/token удерживаются лишь в памяти принадлежащей reservation и очищаются
при её доказанном завершении; no diagnostics/persistence. Всё это — условия
принятого дизайна для следующего source review, не новые findings требований.

### Current exact SHA-256

| Артефакт | SHA-256 |
| --- | --- |
| spec.md | `b411bfb620e9d571422f9c423b0ae193ed70e87303d08e84a4b9844e32f81658` |
| plan.md | `527e660d9e1682e7a0f0a79118ea4bab38d4c174542b49c0113f571528a5b89c` |
| tasks.md — T119 `[ ]` | `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f` |
| data-model.md | `8dd54012c3bfe4003cd18db98ebc67e0b7730cbbdfb6523b881cce4cdc15ec19` |
| contracts/windows-native-web-bridge.md | `21bffa56631901952ae778871f26785522d839eafc8afb9942b488ff22bbd0fa` |
| quickstart.md | `1065b1970125f2ea7cc323c0177d07485e34a339a6b7195df4af9aa65a5cb683` |
| research.md | `0e7659d4cf5136d392bde28cb273c6ca0be6af2ac3eca50e23a617e1af129522` |
| calendar-operation.md | `a656adcd4d6cccf578cc7c98f385fe10ba5b422cfb47dba7e3662f8b24e0a834` |
| calendar-wire.md | `0b58c484e25b5f37ec3b157f0bbe227ddcc2cff682dbae5ab0af882936796895` |
| calendar-launcher.md | `99f1a945f2b557ece837ea484633d3e61af5a7838c0068a182bea17de22e4355` |

All normative/checklist bytes совпали с предыдущим gate; actual totals заново
прочитаны8/0+5/0+5/0. Report before append:
`a82b704f501e45632b16c0b63e89cadef4a396297bab0b8628496cfa04de82d3`.
Round246b SDK build/Core0, native focused4/4, portable45/45 и sourceM1/M2 closure
— **main-reported**, не reviewer-executed и не новый общий native/installed PASS.
Source этого этапа не проверялся; новых jobs/build/VM/tests не было.
T119/installed/current authenticated UI и остальные release/capture/storage
gates остаются открытыми. Только reviewer-owned append; source/norm/tasks/
markers/Git/GitHub и dirty работа других участников не изменены.

## Round248 — requirements continuity: actual native popup fixture

2026-10-06, fresh receipt `2026-10-05T22:53:29Z`.
**PASS requirements; C0/H0/M0/L0. Actual totals operation8/0 + wire5/0 +
launcher5/0 = 18/0; markers unchanged.** Canonical worktree and submission
branch/HEAD remain `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`,
`codex/200-windows-followup`, `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`.
Feature.json personally reread; no fresh Git invocation. High-risk-product lane.

Scope: test-first synthetic native popup fixture in existing RecordingIndicatorTests,
real WindowsTray/public HWND/production iconresource, quickstart§16.3 and existing
T119/T097 acceptance mapping. No production source audit or fixture implementation
review. All18 custom criteria, affected FR002/005/006 and SC002/006/009, current
plan menu1–7, model§8, bridge§10, quickstart§16, research rationale and open
T119/T097 personally reread. Constitution VI/VII and independent implementation/
privacy/reference fidelity, root guidance and validation boundaries retained.
speckit-analyze fully personally read; applied as scoped cross-artifact analysis,
not a full-feature analyze execution. Before/after hooks are disabled commit
hooks; no prerequisite/Git/issue-sync actions. User permits only this append.

### Affected obligations and proof boundary

| Obligation | Norm/task coverage | Result |
| --- | --- | --- |
| Real popup/nested loop with copied rows/handler, frozen identity rather than fresh row index; selection is Join only. | Plan menu2–3, model§8, quickstart16.3; T119 | PASS |
| Projection/flags/auth/time/lifecycle invalidation ends old tracking; stale row dispatch count stays zero. | Plan menu3/5, bridge§10; T119 | PASS |
| Owner destruction/reentry during menu loop is safe; fresh alive/window/current check before callback and no Impl accesses after callback. | Plan menu3, quickstart16.3; T119 | PASS |
| Positive unchanged selection calls copied handler for its frozen target; normal popup close does not revoke an admitted unchanged flight. | Plan menu3/5, model§8, quickstart16.3; T119 | PASS |
| Native font/DPI fitting, literal labels, full safe accessibility text; privacy/private/unavailable rows and legacy controls preserved. | Plan menu2; FR002/SC009; T119/T097 | PASS |
| Synthetic popup/tests/resources are partial native evidence, not source authorization, OS launch, actual account or installed MSIX acceptance. | Operation CHK008, launcher CHK005, quickstart16.6; T119/T097 | PASS |

**6/6 affected obligations mapped; unmapped0, ambiguous0, constitution conflicts0.
Scoped analyze threshold C0/H0/M0 met; L0.** Operation8 criteria remain supported
by common owner/context/deadline/drain/recovery/expiry/Record/proof separation;
wire5 by exact schema/strict JSON/replay/trusted cancellation/staged acceptance;
launcher5 by target/outcome/lifetime/current/proof distinctions. Popup fixture
does not change those contracts or add payload/authority. Historical unchecked
findings later closed are not new requirements blockers.

Real synthetic Windows menu actions are permissible within the submitted test
scope. Production iconresource should be linked normally; do not bypass failed
WindowsTray construction, inject a fake available flag or replace TrackPopup
with a direct callback/posted WM_COMMAND and label that popup acceptance.
Callbacks can count/copy synthetic identities without resolving/launching URLs,
auth/server calls, recording or real meeting data. Destroy-owner/reentry cases
must occur during the actual nested loop; selection/invalidation counts should
distinguish positive current dispatch from zero stale dispatch. Normal popup
close vs already-admitted operation remains an integration boundary, not something
proved solely by a tray-only callback count.

Resource accounting where feasible can support menu/font/brush cleanup after
the loop unwinds; raw whole-process counters are not a full leak/performance
proof. No new numeric leak budget or repetition threshold is invented here.
Keyboard/screen-reader/high-contrast/DPI and exact installed current-account
flows remain separate acceptance; this fixture does not waive them or require
OS setting changes. No new service/client/owner/constructor bypass, user product
choice or normative clarification is needed before test-first fixture work.

### Current exact SHA-256

| Artifact | SHA-256 |
| --- | --- |
| spec.md | `b411bfb620e9d571422f9c423b0ae193ed70e87303d08e84a4b9844e32f81658` |
| plan.md | `527e660d9e1682e7a0f0a79118ea4bab38d4c174542b49c0113f571528a5b89c` |
| tasks.md — T119/T097 remain `[ ]` | `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f` |
| data-model.md | `8dd54012c3bfe4003cd18db98ebc67e0b7730cbbdfb6523b881cce4cdc15ec19` |
| contracts/windows-native-web-bridge.md | `21bffa56631901952ae778871f26785522d839eafc8afb9942b488ff22bbd0fa` |
| quickstart.md | `1065b1970125f2ea7cc323c0177d07485e34a339a6b7195df4af9aa65a5cb683` |
| research.md | `0e7659d4cf5136d392bde28cb273c6ca0be6af2ac3eca50e23a617e1af129522` |
| calendar-operation.md | `a656adcd4d6cccf578cc7c98f385fe10ba5b422cfb47dba7e3662f8b24e0a834` |
| calendar-wire.md | `0b58c484e25b5f37ec3b157f0bbe227ddcc2cff682dbae5ab0af882936796895` |
| calendar-launcher.md | `99f1a945f2b557ece837ea484633d3e61af5a7838c0068a182bea17de22e4355` |

Hashes unchanged from Round247; actual checklist totals independently reread.
Report before append `8e080c2991d2cb73b20fa0982880bcf4c75c5ae8640bd78276304d11567c81f1`.
Round247b approved source receipt remains separate; final portable45/45,
native-focused4/4, solution build0/Core0 and Dev EXE
`c816972887ba7c7e971c5d21c83b3168508066bff648a61d38831c5c8992ef6c`
are main-reported, not reviewer-executed/installed. No new runtime receipt here.
Reviewer ran no build/test/VM/browser/OS action. Only this append changed;
code/norm/tasks/markers/Git/GitHub/audio/server and dirty work preserved.
T119/T097/installed and whole Feature200 acceptance remain open.

## Round249 — requirements continuity and safe native ContentDialog fixture

2026-10-06; fresh canonical receipt `2026-10-05T23:17:37Z`.
**PASS requirements: C0/H0/M0/L0.** Custom checked/unchecked totals personally
reread and counted: operation8/0 + wire5/0 + launcher5/0 = **18/0**. Referenced
UX25/0 and security27/0 remain requirements markers; only affected dialog/current/
privacy/accessibility obligations were revalidated, not all capture/storage work.
No marker changed. Existing high-risk-product T119, no new feature/schema/owner.

Canonical worktree: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`.
Feature.json branch/submission HEAD: `codex/200-windows-followup`,
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`; no fresh Git invocation/claim.
Personally read current root/router, scoped spec-kit-flow/product-gates/validation
guidance, Constitution7.1.0 including II/VI/VII, applicable PRD/status boundaries,
spec US2/FR002/005/006/015/SC002/006/009, plan T119 operation/launcher/menu,
bridge10, model8, quickstart13/16, taskT119 and referenced UX/security criteria.
speckit-analyze read fully and applied as bounded cross-artifact analysis, not
full-feature analyze execution. Feature paths were read directly from feature.json;
the Git-using prerequisite command was not run under the explicit no-Git scope.
Before/after-analyze commit hooks are disabled; no hook or issue-sync action.

### Requirements / testable acceptance mapping

| Affected obligation | Current authority / task | Result |
| --- | --- | --- |
| One common busy reservation; no failure dialog before actual prior worker/API drain; dialog itself owns a distinct matching child ticket. | Operation CHK001/004/008; plan1211–1255,1707–1717; T119 | PASS |
| Real SDK dialog lifecycle must be observed; Hide/Cancel/Closing, helper bool or future readiness alone cannot clear pending. Completion of an actual owned SDK API is not universal proof of another worker's exit. | Operation CHK004/008; launcher CHK002/003/005; quickstart13/16.4; T119 | PASS |
| Menu failure Retry differs from browser recovery: failed attempt never revives; recovery stays opening. Cancel/stale has no automatic resolver, launch or Record. | Operation CHK005; bridge10, model8, plan1702–1717; T119 | PASS |
| Retry requires matching dialog terminal plus explicit current Primary, new request/operation and fresh resolver, same source/original expiry, protected transition without admission gap. | Operation CHK002/006; bridge529–534, quickstart16.4–5; T119 | PASS |
| Resolver budget starts at Primary click, includes later close/dispatch delay, and is not reset by poll; no invented15s dialog/OS timeout. | Operation CHK003/006; plan1215–1219,1711–1717, quickstart16.4; T119 | PASS |
| Owner/workspace/auth/token/action/document drift, source replacement/expiry/exit invalidate applicability; stale callbacks cannot drain or change a new flight. Poll/drain remains necessary after interaction is revoked. | Operation CHK002/004; wire CHK003/004; bridge438–450; T119 | PASS |
| Unknown SDK Status/Canceled/exit retains handle/ticket/busy; natural terminal GetResults failure is a failed result, not permission to retry/Record. Start dispatch with no owned handle is a different scoped completion. | Launcher CHK002–004; plan1299–1322,1715–1717; T119 | PASS |
| Safe native SDK tests, AppMain integration, human/accessibility and exact installed acceptance are distinct; menu never Record and no real auth/URL/audio is needed for this fixture. | Operation CHK007/008; launcher CHK005; UX CHK014–020, security CHK017/018/021; quickstart16.6; T119/T097 | PASS |

**Scoped analysis:8/8 affected obligations mapped; unmapped0, ambiguity0,
constitution conflicts0, C0/H0/M0 threshold met, L0.** No new product decision,
normative amendment, separate task or protocol capability is required. These
are requirements-quality results, not an assertion that forthcoming fixture
or AppMain runtime already passed.

### Safe minimal setup and proof fences

Main's refined proposal is admissible: an SDK-only standalone synthetic WinUI
fixture under Tests, with actual ContentDialog/ShowAsync and the production
CalendarJoinOperation compiled unchanged. Do not start the full AppMain merely
to obtain a XamlRoot: its live profile/auth/capture dependencies are outside
this synthetic setup. No private/public macro, production test seam, copied
state helper, second owner/service/client, real resolver/launcher or installation.
All identities/context values are synthetic, in memory; output only bounded
case/outcome/count/ordering metadata, no profile/cookies/token/URL/private title.

The minimal project choice is constrained by actual existing build inputs:
GrafWindowsCoreTests.vcxproj and portable/CMake fixtures are not WinUI XAML test
hosts; GrafWindowsApp.vcxproj is the existing UseWinUI/runtime/bootstrap pattern.
Reuse an existing suitable SDK test host if one is found; otherwise a narrow
test-only project is justified, reusing Directory.Packages.props/locked SDK,
normal WindowsPackageType/bootstrap and only required helper sources. Do not
clone the whole app/profile startup, upgrade packages, disable flags or pretend
windowsapp.lib alone creates a WinUI XAML host. The product project's source is
not approved for change by this gate.

Use a real attached root/window/UI dispatcher and real SDK handle, one dialog
at a time. Microsoft requires a ContentDialog XamlRoot from the attached XAML
tree and limits simultaneous dialogs per window:
[Dialog controls](https://learn.microsoft.com/en-us/windows/apps/develop/ui/controls/dialogs-and-flyouts/dialogs).
Unpackaged WinUI must initialize its runtime dependency normally:
[Windows App SDK runtime](https://learn.microsoft.com/en-us/windows/apps/windows-app-sdk/use-windows-app-sdk-run-time).
Missing runtime/interactive desktop/root is setup failure, not native PASS or
a silently skipped mandatory case. No runtime install or OS setting change is
authorized in this reviewer turn.

The test must observe actual show/open and natural terminal/result ordering,
not directly call PrimaryButtonClick handlers or helper complete and call that
SDK acceptance. Copying production title/Close-default/theme/button properties
is useful parity input, not execution of offerCalendarDialog. For delayed closing,
a test-only SDK Closing deferral is a minimal native mechanism: Closing precedes
Closed, and GetDeferral supports asynchronous closing work
([Closing](https://learn.microsoft.com/en-us/windows/windows-app-sdk/api/winrt/microsoft.ui.xaml.controls.contentdialog.closing?view=windows-app-sdk-1.8),
[GetDeferral](https://learn.microsoft.com/en-us/windows/windows-app-sdk/api/winrt/microsoft.ui.xaml.controls.contentdialogclosingeventargs.getdeferral?view=windows-app-sdk-1.8)).
It may be used in the fixture, not injected into product behavior. Assert busy/
matching ticket retained while actual close is deferred, then release the
deferral and collect the real terminal operation/result before matching drain.
Do not call IAsyncInfo.Cancel/Close to fabricate drain. Hide is an applicability/
presentation action; its return is not completion proof.

Minimum bounded cases derive directly from the table: explicit Primary and
Close/Cancel; cancel/Hide while dialog work remains pending; old work blocks
failure-dialog admission; matching old drain then one owned dialog; current
Primary plus matching dialog drain yields new IDs without busy gap; preserved
source/expiry and click+15s refusal when close delay consumes budget; stale
auth/source/expiry during pending dialog; late old ticket/decision cannot alter
the new attempt; no Record/URL/automatic retry. Real delayed SDK close and a
controlled helper-clock assertion must be labelled separately if both are used.
Unknown Status/result/start faults not actually induced by this real SDK fixture
remain separate adapter-fault coverage, not inferred from happy-path success.
Watchdog timeout is a failed test/cleanup boundary, never evidence that the
production work drained. Teardown retains callback/root/handle storage until
observed completion; explicit process exit is not a normal reusable drain.

This isolated test can prove **actual SDK dialog + production ticket lifecycle**.
It cannot prove private AppMain offer/poll/reentry/current binding, live account/
capture/reminder/XamlRoot/shutdown wiring, fresh HTTP/native/browser handoff,
installed T119 or physical keyboard/a11y/DPI merely by reproducing properties.
Full AppMain source/integration and installed acceptance remain separate open
gates. Safe synthetic button automation must be identified as such; no global
input or claim of human keyboard testing is implicit in this approval.

### Fresh exact SHA256 receipt

| Artifact | SHA256 |
| --- | --- |
| spec.md | `b411bfb620e9d571422f9c423b0ae193ed70e87303d08e84a4b9844e32f81658` |
| plan.md | `527e660d9e1682e7a0f0a79118ea4bab38d4c174542b49c0113f571528a5b89c` |
| tasks.md — T119/T097 still open | `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f` |
| data-model.md | `8dd54012c3bfe4003cd18db98ebc67e0b7730cbbdfb6523b881cce4cdc15ec19` |
| contracts/windows-native-web-bridge.md | `21bffa56631901952ae778871f26785522d839eafc8afb9942b488ff22bbd0fa` |
| quickstart.md | `1065b1970125f2ea7cc323c0177d07485e34a339a6b7195df4af9aa65a5cb683` |
| research.md | `0e7659d4cf5136d392bde28cb273c6ca0be6af2ac3eca50e23a617e1af129522` |
| calendar-operation.md | `a656adcd4d6cccf578cc7c98f385fe10ba5b422cfb47dba7e3662f8b24e0a834` |
| calendar-wire.md | `0b58c484e25b5f37ec3b157f0bbe227ddcc2cff682dbae5ab0af882936796895` |
| calendar-launcher.md | `99f1a945f2b557ece837ea484633d3e61af5a7838c0068a182bea17de22e4355` |
| ux.md | `1a5a28f7226d7fc25bafdb8239b3d4bea2aeae0d4aad969eb89b45ec5b855801` |
| security.md | `0a321d6d52a4f56d8c2888bd3fa639c85a7c9dc82b5a6acdc2bc3f1bb7a40273` |
| Constitution7.1.0 | `d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859` |

Norms and custom markers match prior Round248 hashes. Report before append:
`2efacf056d1faec47f52416a4b0f91781cfad13b528157ccf0e07eaccfbff651`.
Round248 popup receipts/source approval are historical separate evidence, not
ContentDialog runtime proof. No Round249 fixture implementation/source approval,
native execution or acceptance result is asserted here. Only this reviewer-owned
append changed; norms/code/tasks/markers/Git/GitHub/VM/audio/external state and
other agents' dirty work preserved. T119/T097 and whole Feature200 remain open.

## Round250 — safety requirements before package replacement / first launch

Reviewed 2026-10-05 23:39 UTC, canonical
`/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`.
Feature pointer still identifies high-risk-product F200, branch
`codex/200-windows-followup`, source_sha
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`. This is a freshly read file anchor,
not an independently executed Git HEAD check. Main reports installed GRAF
0.1.0.12, installed EXE hash
`7c4193727f2653832da23e10641c3abe2686293d802ad5dd0edddac9ffff9994`,
process 7328 Responding/from-installed, a prior capture-clock error and ten
attention rows. Reviewer did not inspect that process, profile or records.
Ten UI rows are not a verified disk inventory, proof of pending deletion, or
proof that all workers have exited. No content or actual user paths were read.

### Two separate verdicts

- **Requirements quality PASS: C0/H0/M0/L0** in this bounded safety scope.
  No new normative/schema/product decision is required. Existing preservation,
  migration, authority, shutdown, deletion and package gates are explicit.
- **Installed replacement + first launch on this working profile: NO-GO with
  current evidence. Acceptance blockers C0/H2/M0/L0**, below. These are missing
  implementation/acceptance proofs, not newly discovered requirements defects
  or a full source audit verdict. Do not convert requirement checkmarks into
  permission to run the dirty candidate against the user's records.

Open T116/T117 does not forbid independent T119 source development or isolated
synthetic SDK testing: spec Session2026-10-02 and plan1517–1529 explicitly separate
them. Conversely it grants no waiver for real-inventory migration or package
startup effects. This audit neither requires every unrelated hardware gate to
finish before synthetic tests nor permits a real-data transition on primitive
or calendar PASS. Package installation and the first app launch are separate
effects; preserving data during installation alone does not prove safe startup.

### Exact effects found by bounded source tracing

This is narrowly identifying reachable mutations, not re-reviewing storage
algorithms or the main agent's package/performance investigation:

| Current source | Reachable behavior relevant to the no-touch boundary |
| --- | --- |
| AppMain.cpp:459–465,596–604,1192 | NativeCapture uses the fixed user-scoped `GRAF/recordings` root, creates it if necessary, loads the queue and sweeps discarded short recordings during construction, before a calendar click. A different executable location/unpackaged launch is not evidence of profile isolation. |
| DesktopUploadQueueService.cpp:135–163,356–372 | Queue load can rename malformed ledger to `.quarantine`; it can rewrite a readable v2 ledger or interrupted-upload statuses via persist. It is not a read-only display load. Missing ledger without quarantine is accepted by this legacy loader; it is not proof of a virgin protected root. |
| DesktopUploadQueueService.cpp:600–666 | Startup sweep invokes marked short-discard cleanup: queue row removal/persist, file removals and removal of the empty package directory. This is conditional on path/marker/ledger checks, not proof that any of the ten records actually qualifies. No such qualification was inspected. |
| AppMain.cpp:646–653,678–695,4139–4160; DesktopUploadRecoveryScheduler.cpp:29–68,89–107 | Auth recovery and launch/wake/scheduled ticks can prepare a queue flight, mutate retry state and dispatch upload once current account/config prerequisites pass. A calendar test must not be called HTTP-free merely because it never clicks Send. |
| AppMain.cpp:855–866,2316–2413,4143–4157 | The periodic loop can finish previously recorded local deletion intent, fetch/ensure server purge tasks and apply local recycle/purge with acknowledgements. Current guards and existing intent/account prerequisites are acknowledged; this review does not infer permission from an attention badge or prove a server task exists. |
| AppMain.cpp:3154–3158; plan647–674 | In-product update readiness includes queue completion, capture/file work, purge/deletion work and calendar busy. Manual package replacement is not evidence that these gates ran. Cancellation or Responding=true cannot substitute for actual quiescence. |

These actions may be intentional normal product recovery; they are nevertheless
incompatible with treating this launch as a no-mutation calendar-only probe.
No actual data loss, performance root cause, active microphone, migration run or
installed-binary behavior is inferred from the source trace.

### Acceptance blockers and existing prerequisites

**H250-1 — non-read-only startup against existing records is not safely admitted.**
Current constructor/timer/auth effects above are concrete. Under the human's
no-record/profile-touch boundary, main must not launch/replace against this
working profile assuming idle UI or calendar-only behavior is sufficient.
Before a permitted real-profile run, demonstrate on disposable generated data
the exact candidate's load/recovery/discard/deletion/upload behavior, preservation
of unknown/degraded/malformed/oversized/key-loss artifacts and safe refusals.
Account/auth/token/owner and actual pending intent must be proven, not invented
from ten rows. Existing short-recording policy does not allow discarding a
clock-failed recording merely because it is short. Existing confirmed deletion
rights are not a new test authorization to exercise them on user files.

**H250-2 — exact candidate compatibility/migration/update/rollback proof is missing.**
FR012/013/020/022, SC005/008, T116→T117→T118 and quickstart§8/12/14 already
require this. Identify the exact frozen dirty-source/package/EXE manifest and
changed consumers, standard-user dependencies/architecture, signature Valid,
package identity/publisher and data/profile continuity. Demonstrate generated
legacy/protected/v2/v3 inventories, cuts/restart, retained original bytes/UUID/
accepted ranges/delete operations, single authority and old-reader refusal.
Unknown format/key/integrity failure retains artifacts and blocks unsafe effects;
no empty ledger, plaintext downgrade, forced GC or normal protection claim.
Reinstallation of 0.1.0.12 is not automatically a safe data rollback after a new
authority switch; contract§8 permits preservation + explicit unsupported-format
refusal, not restoration of an old writer over new state.

The existing transition order is specific: exclusive recovery lease and actual
writer/flight/pin quiescence; prepared protected intent; migration admission
fence; verified copy/readback and fresh source stamp; durable old-reader barrier
before rename; one authority switch; restart reconciliation; original cleanup
only with separately authorized cleanup or established delete/purge intent.
Key/profile copying or deletion is expressly forbidden by custody§7. Legacy
originals/unknown leftovers remain retained and cannot be called fully encrypted.
Required disk/quota/reserve peaks and refusal boundaries must hold, not only
the best performance measurement. These are inherited prerequisites, not a new
schema, service, product choice or calendar protocol.

Before installer handoff also prove no active capture/finalizer/upload/purge/
calendar/dialog work remains, close admission and wait for actual completion;
failed bounded wait cancels update rather than just forcing shutdown. Package
signing/identity/dependencies and exact-byte evidence do not authorize uninstall,
profile reset, ledger replacement, permission changes, user-record cleanup or
installation in this review turn. Backups are not a substitute for transition
proof and this report does not authorize copying user data/DPAPI keys.

Safe next evidence remains existing synthetic fixtures/disposable inventory and
isolated SDK tests. Any future full-app test must prove it cannot reach the live
fixed custody/WebView profile; changing the EXE name/package alone does not
establish isolation. Actual installed T119 scenarios can follow only after the
applicable safety proofs and a permitted execution scope, without closing T119/
T097 early. No installed action is authorized by this gate report itself.

### Requirements and checklist receipt

Personally applied full project-local `speckit-analyze` and `speckit-checklist`
instructions; used scoped cross-artifact coverage, not checklist generation or
runtime checklist conversion. Read root AGENTS, guidance index, worktree/risk/
product/release guidance, Constitution7.1.0, applicable PRD/current-status
sections, spec requirements/sessions, plan storage/release/T119 boundaries,
tasks T116–119/T071/T097, quickstart§2/8/12/13/14/16 plus Round249, data-model§12,
custody§7–9 and packed§6.1. Existing legacy status paragraphs remain historical.
Before/after analyze/checklist commit hooks are disabled. Prerequisite scripts
were not executed because this request excludes Git; active paths verified by
direct feature-pointer/artifact reads. No state-changing hooks were invoked.

Freshly reread marker counts, unchanged:

| Checklist | checked | unchecked | Meaning retained |
| --- | ---: | ---: | --- |
| calendar-operation.md | 8 | 0 | Requirements quality |
| calendar-wire.md | 5 | 0 | Requirements quality |
| calendar-launcher.md | 5 | 0 | Requirements quality |
| security.md | 27 | 0 | Requirements quality; storage/update/purge criteria checked as norms |
| ux.md | 25 | 0 | Requirements quality; no installed/a11y acceptance |
| packed-writer.md | 12 | 0 | Worker primitive requirements; no consumer/migration approval |
| review-2026-10-04-packed-package-gate.md | 12 | 0 | Structural package requirements; historic H1 already closed |

Calendar subtotal **18/0**, calendar+security+UX **70/0**; with the two bounded
storage requirement checklists **94/0**. No markers changed or new items created;
this is not a fresh whole-feature112-item or full-storage implementation audit.
Scoped coverage: FR012/013/014/015/019/020/021/022 and SC005/008 have existing
T116–118, T071 and T119 task owners (10/10 requirements mapped); no uncovered
norm, new contradiction, blocking clarification or constitution conflict found.
Quality analyze C0/H0/M0/L0 does not remove the two acceptance blockers above.

### Exact SHA-256 inputs

| Artifact | SHA-256 |
| --- | --- |
| spec.md | `b411bfb620e9d571422f9c423b0ae193ed70e87303d08e84a4b9844e32f81658` |
| plan.md | `527e660d9e1682e7a0f0a79118ea4bab38d4c174542b49c0113f571528a5b89c` |
| tasks.md | `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f` |
| quickstart.md, including Round249 | `5cc51e712a6b1543771aab46ba922b3f90768f177e0e274d548df4a8eb6681d2` |
| data-model.md | `8dd54012c3bfe4003cd18db98ebc67e0b7730cbbdfb6523b881cce4cdc15ec19` |
| bridge contract | `21bffa56631901952ae778871f26785522d839eafc8afb9942b488ff22bbd0fa` |
| base custody contract | `ec93d11c474cb970d57c2324518d541cd9fb3e7bb7f2f807d63d612ad878624a` |
| packed custody contract | `a1dedd9d5b7ce02e4a6c200a300b0423bcada82192217e2a79f9773428c4a7b5` |
| Constitution7.1.0 | `d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859` |
| AppMain.cpp, bounded startup trace only | `2b7fb97f1a64853b78146cb715bfe3f752a11908727ed4fb2d0babade63194dc` |
| DesktopUploadQueueService.cpp | `08ea8aac504d6f31d03cfed53b65ff4caed05522e57871a0a34ab376a4c12e5b` |
| DesktopUploadRecoveryScheduler.cpp | `e4fdac0709bf03c7b3f18d2629651ebded4f895d24fd3f026cc8bee066d6bf3c` |
| DesktopLocalPurgeService.cpp, path/effect trace | `3286865422c17325cb299d30b5b730f00029498dbe6b557bf491c8304443df8e` |
| calendar-operation.md | `a656adcd4d6cccf578cc7c98f385fe10ba5b422cfb47dba7e3662f8b24e0a834` |
| calendar-wire.md | `0b58c484e25b5f37ec3b157f0bbe227ddcc2cff682dbae5ab0af882936796895` |
| calendar-launcher.md | `99f1a945f2b557ece837ea484633d3e61af5a7838c0068a182bea17de22e4355` |
| security.md | `0a321d6d52a4f56d8c2888bd3fa639c85a7c9dc82b5a6acdc2bc3f1bb7a40273` |
| ux.md | `1a5a28f7226d7fc25bafdb8239b3d4bea2aeae0d4aad969eb89b45ec5b855801` |
| packed-writer.md | `a1f18f2cdfe6ebcdb369ad0ed6a877f77af4658bc388a4cab1475c50b45b62a0` |
| packed-package gate | `a93a08a1fda433a2a4523161edc39d6d0547eee8ed7cc5d42bc66675a5dc06f2` |

Report pre-append SHA:
`e183766c0098587793d85d1302f6a462967db17d54a760b85281a905442248d0`.
Only this reviewer-owned append changed. No product/norm/task/marker/Git/GitHub/
VM/build/test/install/audio/profile/user-record operations. Source/package safety
acceptance itself is NOT granted; main owns its separate code/package diagnosis.
T119/T097/T116/T117/T118 and whole-feature/release acceptance remain open.

### Round250 terminal update — owner test passed; no diagnostic edit

Main reports run76270/eb0270 is now terminal: rebuild0, complete owner test
exit0 in228.38s with the unchanged300s limit, helperexit0 and every existing case
retained. This is main-reported native execution, not reviewer-executed proof.
Fresh canonical test hash remains
`ca4e041ca15b978e6573e3473fe8ac003b166ac313bbc46c54a643bfbcef3205`.
The proposed stage-label instrumentation is no longer needed and is not to be
implemented on the strength of the earlier optional diagnostic assessment.
No stage-label test changes were made by reviewer. Historical failures remain;
this successful unchanged-source run does not prove their cause was fixed.
The announced serial full49 native repeat has no terminal result in this receipt.

**Final installed-safety review remains complete: requirements C0/H0/M0/L0,
calendar18/0; working-profile replacement/first-launch NO-GO, acceptance
C0/H2/M0/L0.** Full owner-test success improves bounded T116 evidence but does
not independently establish startup inventory preservation, actual pending
effects/worker quiescence, consumer adoption, T117 migration/downgrade or exact
candidate package/profile continuity. H250-1/H250-2 above therefore remain open.
No need to alter requirements or rerun a whole-feature audit to state this.

Fresh spec/plan/tasks/quickstart and traced AppMain/queue hashes are unchanged
from the Round250 table. Main reports origin/master
`df9c8f4ee4b538cba6c42e1fad6007595e22774a` fetched, branch HEAD unchanged and
issues7540/7444 OPEN; reviewer did not perform Git/GitHub checks. Incoming-diff
inspection belongs to main and is not evidence of a merge or candidate safety.
No merge/commit, installed replacement, new app startup or profile/record action
is authorized by this update. Only this safety-report appendix was written;
the optional diagnostic report/history is preserved without further edits.
Pre-append report SHA:
`7562d5ea0ad16bd930b1348da39cdca819d16a9ae9f1e05cc7db596ccf52d9a0`.
