# T119 Round237: ограниченный requirements gate calendar wire

Дата: 2026-10-05. Независимый reviewer-owned результат.

**REQUEST CHANGES: C0 / H0 / M1 / L0; 4 checked / 1 unchecked.**
Из пяти пунктов CHK001/002/004/005 подтверждены; CHK003 остаётся unchecked.
Gate не PASS до узкого уточнения поведения на cap1024. Это дефект ясности
требований на конкретной границе, не отсутствие будущей реализации/тестов.

## Область и процесс

Canonical repo: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`.
Branch `codex/200-windows-followup`, HEAD
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1` проверены read-only заново.
Документы находятся в dirty worktree; их SHA-256 ниже, не предположение о
включении этих bytes в HEAD. Чужая dirty работа сохранена.

Применён лично прочитанный проектный `speckit-checklist`; generation rules не
подменяют явное reviewer-authorized право оценки существующих markers.
Лично прочитаны действующие AGENTS/guidance, constitution 7.1.0, активные
FR-006/Session2026-10-05, wire подраздел plan, bridge §3/§5/§10, затронутые
data-model §8, quickstart §13, research и task T119. Неизменные более широкие
части ранее прочитанного контекста не проверялись заново. Prerequisites
подтвердили active Feature200/high-risk-product; checklist hooks выключены.

Полоса — bounded requirements-quality gate существующего high-risk T119,
не новый service/feature и не low-risk реализация. Constitution сохраняет
отдельные capture/user control, auth/privacy, independent reviewer и release
gates. Само сообщение main о разрешении дизайна не считается evidence PASS.

## Пять критериев

| Пункт | Вердикт и основание |
| --- | --- |
| CHK001 | PASS. Spec FR-006:426–439 и bridge §5/§10 теперь явно включают cancellation-only command. Join имеет ровно action="joinCalendarEvent", eventId, requestId; cancel — ровно два строковых eventId/requestId с той же UUID hex формой и нормализацией регистра. Extra/duplicate/type/URL/path/Record authority не допускаются. Cancel не стартует resolver/launch/recovery/Record, не отменяет card/menu и не освобождает actual work. Прежний allowlist H разрешён письменными нормами. |
| CHK002 | PASS. Bridge:393–396 требует strict original envelope до SDK Parse/Stringify, decoded duplicate keys, валидные UTF-8/surrogates и whole64KiB. Payload depth≤8 отделён от envelope root. Plan:1265–1269 требует reuse JsonReader/calendarString/calendarEventId и owned raw payload, запрещает dangling string_view. Typed UUID/data не являются authority; exact origin/nonce/direction/message-id guards сохраняются. |
| CHK003 | NOT PASS. One-time canonical UUID history, consume busy/not-ready, no eviction и запрет старого cancel против нового flight определены для первых admitted UUID. Однако cap response и replay-no-response не имеют явного совместимого правила для ещё не сохранённого 1025-го UUID. Конкретный M1 ниже. |
| CHK004 | PASS. Bridge:378–392,406–415 и dispatch lifecycle задают current attached main meetings, exact approved route/origin/nonce/message-id, frame/auth/settings/billing/detail/review/external отказ. Plan:1274–1280 задаёт cancellation + terminal reply старому current document до nonce/script invalidation; late reply не получает новый nonce. HTMX сверяет итоговое DOM-состояние: тот же canonical доступный UUID сохраняет pending, removal/replacement отменяет. Document cancel не является SDK/worker drain и не затрагивает native card/menu child; новый document reset history не снимает прежнюю lease. |
| CHK005 | PASS. Plan:1282–1286 разделяет strict portable decoder, host guards/replay/reply, trusted shim/HTMX/a11y и последующий AppMain owner. SDK ветвь требует independent source review и Windows full solution compile, fake/compile не являются installed auth/UI acceptance. Quickstart §13 перечисляет focused wire/replay/invalidation cases и отдельную installed матрицу. Tasks:583 T119 остаётся одной открытой задачей с существующими путями и FR/SC; сервер/UI business logic не дублируются. |

## M1 — consume/not-ready/replay при полном bounded set не определены совместно

Точные затронутые места:

- Spec Session2026-10-05:728–732: UUID принимается не более одного раза,
  включая busy/not-ready; cap1024; новый корректный запрос после cap получает
  cancelled/not_ready, старые UUID не вытесняются.
- Bridge §10:398–404: одноразовый UUID включая busy/not-ready; повтор без
  действия/ответа; до1024 entries без eviction; новый корректный Join после
  cap получает cancelled/not_ready.
- Data-model §8:325–328: Join consumes UUID даже при busy/not-ready.
- Plan:1271–1273: replay без ответа, новый UUID при полном наборе получает
  cancelled/not_ready.

Контрпример требований: документ уже хранит 1024 UUID. Корректный Join с новым
UUID R получает cancelled/not_ready. Затем тот же R присылается с новым
валидным outer message_id. Если R consumed, его нужно где-то хранить сверх
cap либо вытеснить entry — оба варианта запрещены. Если R не consumed, повтор
снова выглядит как новый UUID и получает ответ, что требует явного исключения
из consume-on-not-ready и общего replay-no-response правила.

Без запуска resolver это не создаёт новый OS flight и не позволяет старому
cancel попасть в новый документ: nonce/generation границы остаются правильны.
Тем не менее CHK003 требует однозначного поведения reply/replay на указанной
границе, а выбор нельзя оставлять первому implementation тесту.

Нужна минимальная письменная clarification, согласованная хотя бы в Spec
Session/bridge и производных plan/model: являются ли UUID, отклонённые именно
по cap, не admitted и исключением из consume/replay-no-response (тогда повтор
может снова получить только cancelled/not_ready, без work/history growth),
либо применяется иная явно определённая bounded terminal policy. Reviewer
не выбирает новую семантику и не правит нормы самостоятельно. Исправление
не требует второго service, cache eviction, увеличения cap или изменения
capture/launcher/deadline требований.

## Что подтверждено и что не утверждается

Отсутствуют оставшиеся C/H конфликты в четырёх подтверждённых пунктах. Новый
cancel wire больше не отсутствует в нормативном allowlist; ownership исходного
JSON и root/payload distinction определены; source/auth proof не смешаны.
Но один M1 удерживает именно этот requirements gate до ясного решения cap edge.

Отметки не означают наличие strict decoder, host/shim/AppMain integration,
фактической отмены WinHTTP/SDK/dialog, receiver/Record или installed acceptance.
Source review, runtime/installed, T097/T063/SC и release остаются отдельными.
Build/test/probe/VM/GitHub действий не выполнялось. Только checklist и этот
отчёт изменены; product code, нормы, tasks, другие markers и Git не изменялись.

## SHA-256 рассмотренных документов

Пути относительно `specs/200-windows-desktop-app/`:

| Документ | SHA-256 |
| --- | --- |
| spec.md | `8512c456cbfaab7a705518ebe3e1b75dd54ef82dea4ca8d26c9f462e528c1954` |
| plan.md | `5eafc973354969ad0d0806a733a13461f7937323f5e6db1af7dca44d4b7ff852` |
| tasks.md | `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f` |
| contracts/windows-native-web-bridge.md | `ff26fdd44477313fb2703dc972bc77f5e996b5b057446220857b65717aad47e6` |
| data-model.md | `169c3619e63facd22a1acfb557f5bc7fa821ac71f082070bd6ee514a6118726b` |
| quickstart.md | `0ede94d65034e4edda6e2a3d596eeff1fcc098f10bef1cd5130eaac7765257fb` |
| research.md | `c6329bedc995c50109a431b07674184b2ac0882a3b51884676ee6470be369088` |
| calendar-wire.md до reviewer markers | `c8f1489c5c4bea39a51f4326f7411f2174d719f18f20ffd0bef60948b894f28b` |

Governance fresh hashes: constitution
`d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859`;
AGENTS `384c41c0b1674a3daf75d0e57646379198295c3f8452012c8101fc6332bec58b`;
spec-kit-flow `5edf818b6ee27c7ee66d14edc003325ec7b16789eb1a195377cdeb901ae44887`;
product-gates `e5c39fb473dcf785f417b9785b0d6ba17fe23026906eedc08c0620c7a6f5d097`.

Terminal verdict для этой submission: **REQUEST CHANGES C0/H0/M1/L0, 4/1**.
Единственный блокер — CHK003 cap/replay clarification, не весь Feature200.

## Конечный receipt после механической очистки main

Main удалил пустой дублирующий heading около wire подразделов plan/research.
Текущие подразделы лично перечитаны; смысл правил cap/replay не изменился.
Финальные SHA-256 этих двух документов:

- plan.md: `5b58ddc6d701fbf6d32c3916d1f3a83ef6492cacd0f5b78aa2c5aa154ebf2172`.
- research.md: `62e37c39985159a6d98655adb4a1acdf5f723a216685aaa70485c6ffc3248938`.

Остальные пять normative hashes из таблицы повторно совпали. Старые plan/research
hashes выше сохранены как история первого чтения; final verdict применим к
текущим bytes. После удаления heading plan wire anchors сдвинулись на две строки;
название подраздела остаётся однозначным.

Main также ограничил предполагаемый первый implementation slice strict typed
intent/raw-envelope owned decoder и regressions, без включения runtime calendar
allowlist/handlers до общей AppMain owner integration. Это не устраняет M1
в общем wire requirements и не превращает 4/1 gate в PASS. Вопрос о cap не
приписывается decoder implementation, которой reviewer здесь не проверял.

Итог неизменён: **C0/H0/M1/L0, checked4/unchecked1; CHK003 требует уточнения**.

## M1 closure — ограниченный повторный review 2026-10-05

**Текущий итог: PASS C0/H0/M0/L0; 5 checked / 0 unchecked. M1 CLOSED.**
Первый REQUEST CHANGES и receipt выше сохранены как история; этот appendix
заменяет их только в части актуального verdict, не переписывая findings.

Лично перечитаны только затронутые cap/replay положения в Spec
Session2026-10-05:733–736, bridge §10:405–408, plan wire, data-model §8 и
quickstart §13. Остальные четыре ранее подтверждённых пункта не пересмотрены
и их markers не изменены. Canonical HEAD повторно подтверждён без изменений.

Новая нормативная последовательность однозначна:

1. Saved canonical request UUID отвергается как replay **до** cap check;
   нового действия и ответа нет, даже если набор заполнен.
2. Новый UUID при ещё свободной вместимости admitted/consumed, включая обычный
   busy/not-ready отказ; история сохраняется без eviction.
3. Новый UUID при полном cap1024 **не admitted/consumed**. Его повтор с новым
   outer message_id снова может получить только cancelled/not_ready, без
   flight/work/history growth. Это явное единственное исключение из общего
   consume-on-not-ready правила, не последующее разрешение запуска.
4. Full set не получает expiry/eviction/освобождение slot в том же документе.
   Новый document начинает новую history с новым generation/nonce, но не
   завершает SDK/worker child старой операции. Cancellation относится лишь к
   matching pending document event/request, поэтому cap-refused UUID не даёт
   позднему cancel цели для новой операции.

Это прямо закрывает прежний контрпример 1025-го UUID: его отказ теперь не требует
ни 1025-й history entry, ни нарушения replay-no-response для сохранённых UUID.
Spec/bridge/plan/model согласованы; quickstart отдельно требует cap-repeat
terminal outcome без роста history. Увеличение cap, скрытый cache/eviction,
новый service или изменение current/lease/capture требований не появились.
Грамматическая правка model уже присутствует в прочитанных bytes: cap exception
заканчивается перед `Cancel содержит...`; субъект Cancel и запрет создания
request однозначны. Незакрытых C/H/M/L в проверенном closure нет.

### Текущие normative SHA-256 для PASS

| Документ | SHA-256 |
| --- | --- |
| spec.md | `8a61bbcb1ef78043e755aae48ba284118e1dab04118be00d7050e695c1a90ed0` |
| plan.md | `4e2aadb044c2ca8f21c8189e74c5f3338a3663fc6704db4280f7edccb79c7dec` |
| contracts/windows-native-web-bridge.md | `a0acaca20097199e42cba490839cd719b8198ad124d916d611ec4bdcd6b11a65` |
| data-model.md | `217a7a4f1e8cb45543a824ffd878bb32ffd2ea1c5bf44f7ee421a2c2ab0d9cdc` |
| quickstart.md | `189e52e8464f528589eb937315641aef1e293408b179bfc9084c76dc4ca39c1e` |
| research.md, без изменения closure | `62e37c39985159a6d98655adb4a1acdf5f723a216685aaa70485c6ffc3248938` |
| tasks.md, без изменения closure | `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f` |

CHK003 теперь marked checked по этому evidence, не по будущему коду. Актуальный
gate **5/0 PASS** снимает только requirements blocker данного wire slice.
Первый decoder-only шаг и последующие host/shim/AppMain изменения потребуют
своего source/validation evidence; до единого owner integration runtime command
не получает разрешения обходить его guards. Полный T119, installed/auth/UI,
Record, hardware и release acceptance здесь не утверждаются.

Reviewer изменил только CHK003 marker и append-only notes/report. Нормы, product
code, tasks, остальные checklist markers, Git/GitHub и чужая dirty работа не
изменялись. Новые тесты, probes, VM или whole-feature review не выполнялись.

## Round238 — requirements gate перед staged host integration, 2026-10-05

**PASS C0/H0/M0/L0. Calendar-wire: 5 checked / 0 unchecked.**
Это ограниченный review достаточности существующих требований для интеграции,
не source verdict. Исторический M1 и его closure выше сохранены. Canonical
branch `codex/200-windows-followup` и HEAD
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1` подтверждены свежими read-only
командами; рассмотренные dirty bytes не приписываются этому commit.

Лично перечитаны все пункты calendar-wire/operation/launcher, bridge §3/§5/§6/§10,
FR-006/Session2026-10-05, подразделы plan T119/operation/wire/launcher,
data-model §8, quickstart §13 и единственный task T119. Применён лично прочитанный
проектный speckit-checklist: качество требований не подменяется наличием кода.
Ранее лично прочитанные constitution/AGENTS/guidance сверены по неизменным hashes;
guidance index перечитан. Fresh prerequisites подтвердили Feature200;
before/after_checklist auto-commit hooks выключены. Полоса остаётся bounded
requirements-quality review существующего high-risk T119. Фактический source
аудит host/AppMain оставлен main, здесь не дублировался.

### Пять wire критериев в границах интеграции

| Пункт | Текущий вывод и нормативное основание |
| --- | --- |
| CHK001 | PASS. FR-006:419–440 и bridge:379–396 задают exact join action/eventId/requestId и cancellation-only два UUID. Current attached main document, exact origin/meetings route/nonce/message-id обязательны; frame и другие маршруты исключены. Cancel действует только на matching pending event/request того же current document, не card/menu и не следующий flight; не даёт URL/Record/resolver/recovery/drain authority. |
| CHK002 | PASS. Bridge:393–396 и plan:1263–1267 требуют original JSON до SDK Parse/Stringify, decoded duplicates/валидный Unicode всего сообщения, whole64KiB, payload depth8 отдельно от дополнительного envelope root. Owned raw payload/typed UUID не заменяют source/version/direction/origin/nonce/replay checks. SDK-нормализация не может стать первым calendar parser. |
| CHK003 | PASS. Bridge:398–407, Session2026-10-05 и plan:1269–1273 задают saved UUID replay без ответа перед cap, до1024 admitted UUID без eviction, consume обычного busy/not-ready и единственное исключение cap-refused UUID. Последние получают только cancelled/not_ready без work/history growth. Cancel не расходует UUID; новый generation/nonce сбрасывает history, но не actual old work. |
| CHK004 | PASS. Bridge:409–425,443–450 и plan:1274–1279 требуют cancellation и terminal reply старому ещё current document до nonce/runtime-script invalidation, никогда новому документу. Reply pinned к исходным generation/nonce/request и pending event, с допустимыми transitions; terminal не оживает. HTMX same accessible canonical UUID сохраняет pending, removal/replacement отменяет. Plan:1246–1254 отделяет actual completion от UI terminal/interactionPermit; matching operation/work ID не позволяет старому callback освободить новую операцию. |
| CHK005 | PASS. Plan:1166–1186,1219–1256,1281–1286 задаёт общий AppMain state/fence owner для cabinet/card/menu и reuse существующих transport/dispatcher/alive/SDK механизмов. Source review/Windows solution proof отделены от installed; quickstart §13 содержит wire/lifecycle/one-busy/delayed completion и установленную матрицу. Tasks:583 T119 открыта; новый service/factory/UI/server или задача не требуются. |

### Lifecycle, pinned reply и общий owner

`generation`/`alive` не перечислены отдельными шагами в wire предложении
plan:1276–1278. Это не разрешает отзывать их раньше отмены: обязательные
cancellation и terminal reply **старому ещё current document до invalidation**
требуют сохранить старую привязку до этой точки. Нельзя сначала сменить
generation, обнулить nonce либо отозвать alive/current документа, а затем
отправлять terminal от нового контекста. Требуемый порядок: отменить applicability
matching document action, выдать допустимый pinned terminal старому документу,
пока он ещё current, затем отозвать его document guards/runtime-script.
Поздний completion не подставляет новый nonce/generation. Это следствие уже
принятых норм, не новая wire/UX политика и не обещание доставки в уничтоженный
документ. Document invalidation не является actual worker/SDK/dialog exit.

Cancellation-only wire не отменяет независимое native card/menu действие.
Общий owner/token/workspace drift проверяется через snapshot всех источников;
actual lease и matching operation/work ticket живут отдельно от UI applicability.
Resolver15s не переносится на OS/dialog; recovery сохраняет opening той же
операции, новый resolver budget после явного подтверждения и исходный action
expiry. Прочитанные operation 8/0 и launcher 5/0 поддерживают эти ограничения,
не позволяя принять PASS parser за доказательство adapter completion.

### Уточнённый первый product slice main

Первый шаг ограничен host trust/history/reply/invalidation adapter и original
JSON lexical validation перед SDK, **без shim/AppMain mutation**. Calendar
commands остаются denied по умолчанию; enabled только при одновременном
подключении обоих concrete owner join/cancel handlers. AppMain пока их не
подключает, поэтому планируемый staged slice сохраняет production denial.
Tests подключают owner к existing host, без нового service/factory.

Это согласовано с plan:1281–1286: host precedes shim и общий AppMain owner.
Один handler, готовый parser либо native_ready не включают calendar authority;
оба handlers не отменяют document/auth/route/replay guards. Это условия
допустимого implementation, **не утверждение о проверенном коде**. Source review
должен отдельно доказать default denial, отказ при каждой неполной паре handlers,
отсутствие AppMain attachment и host trust/history/pinned reply/invalidation.
До общего owner wiring command enablement не служит обходом accepted guards.

### Fresh hashes и фактические counts

Пути относительно `specs/200-windows-desktop-app/`:

| Документ | SHA-256 |
| --- | --- |
| spec.md | `8a61bbcb1ef78043e755aae48ba284118e1dab04118be00d7050e695c1a90ed0` |
| plan.md | `4e2aadb044c2ca8f21c8189e74c5f3338a3663fc6704db4280f7edccb79c7dec` |
| tasks.md | `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f` |
| contracts/windows-native-web-bridge.md | `a0acaca20097199e42cba490839cd719b8198ad124d916d611ec4bdcd6b11a65` |
| data-model.md | `217a7a4f1e8cb45543a824ffd878bb32ffd2ea1c5bf44f7ee421a2c2ab0d9cdc` |
| quickstart.md | `189e52e8464f528589eb937315641aef1e293408b179bfc9084c76dc4ca39c1e` |
| checklists/calendar-wire.md — 5/0 | `0b58c484e25b5f37ec3b157f0bbe227ddcc2cff682dbae5ab0af882936796895` |
| checklists/calendar-operation.md — 8/0 | `a656adcd4d6cccf578cc7c98f385fe10ba5b422cfb47dba7e3662f8b24e0a834` |
| checklists/calendar-launcher.md — 5/0 | `99f1a945f2b557ece837ea484633d3e61af5a7838c0068a182bea17de22e4355` |

Все шесть normative hashes совпали с актуальным receipt M1 closure; сумма
трёх checklists — 18 checked / 0 unchecked. Новых критериев/markers нет:
wire 5/0 подтверждён свежим review; operation 8/0 и launcher 5/0 служат
согласованными ограничениями интеграции, не whole-feature приёмкой. Governance
hashes те же, что в исходном разделе; README fresh SHA-256
`40e357e422c60915d2c4334c83b9ab74f5ef4c0df6ab8831e3ed16e281ba18a6`.

**Terminal Round238: requirements PASS C0/H0/M0/L0; wire 5/0.**
Блокеров в требованиях к staged host slice не найдено. Это не source approval
host/shim/AppMain, actual drain, installed auth/receiver/Record, закрытие T119
или выпускной допуск. Source/Windows validation/installed gates отдельны.
Reviewer изменил только этот append-only report; checklist markers сохранены
по evidence. Нормы/product/tasks/Git/GitHub/другие reports и чужая dirty работа
не изменялись. Build/probe/VM и повторный source audit не выполнялись.

## Следующий shim-срез — trusted click / HTMX / a11y gate, 2026-10-05

**Requirements PASS C0/H0/M0/L0; wire5/0. Новых обязательных ожиданий перед
test-first реализацией: 0.** Допуск относится к предложенному default-disabled
presentation shim, не к включению owner/launcher или установленной приёмке.
Предыдущие findings, closures и host/source evidence сохранены независимо.

Лично прочитаны проектный speckit-checklist, актуальные FR-006/SC-006/SC-009,
plan T119 wire, task T119, quickstart §13, bridge §4/§10 и три checklists.
Constitution VI/VII и product-gates сохраняют independent implementation,
accessibility/user-control/security и отдельную validation полосу. Неизменные
ранее прочитанные governance сверены по hashes; fresh prerequisites подтвердили
Feature200, checklist auto-commit hooks выключены. Canonical branch/HEAD снова
подтверждены: codex/200-windows-followup,
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`.

Лично прочитаны pinned721b5125 Mac EmbeddedCabinetCalendarJoinBridge целиком и
его main-frame registration/readiness/current/reply callers, pinned server
calendar-series.js click handler и rendering.py календарный anchor/status.
Текущие Windows kDesktopBridgeScript и native_ready creation/SDK completion
прочитаны как исходные ограничения интеграции, не новый полный source audit.

| Wire пункт | Требования к следующему срезу |
| --- | --- |
| CHK001 — PASS | Только exact action/eventId/requestId и cancellation-only eventId/requestId. UUID canonical case, no URL/href/Record authority. Native keyboard activation штатного anchor/button даёт тот же trusted click; отдельная synthetic .click()/key framework не требуется. |
| CHK002 — PASS | Shim не заменяет strict original-envelope parser: JSON/schema/Unicode/depth и native trust остаются за host. Typed reply принимается только с known state/safe reason и исходным nonce/request; pending event сопоставляется с сохранённым canonical UUID, не добавляется новое поле reply. |
| CHK003 — PASS | One pending, новый request UUID для нового явного действия, без отложенной очереди. Saved UUID replay-before-cap1024 остаётся host обязанностью. Late reply/cancel старого request не снимает новый pending; terminal не возрождается. JS history не подменяет native history/actual lease. |
| CHK004 — PASS | До handshake pending отсутствует; delegated trusted capture click предшествует standalone bubble. HTMX observer оценивает итоговый доступный canonical UUID: same UUID сохраняет pending/feedback, removal/replacement отправляет matching cancel. Nonce/document invalidation и presentation disable снимают старые local pending/aria states без влияния на новую identity и без объявления physical work drain. |
| CHK005 — PASS | Внешние resolving/opening/handed_off/failed/cancelled и русские status/live-region/явный повтор уже определены. Terminal снимает aria-disabled, focus/keyboard semantics исходных элементов сохраняются. Source/native-event/installed keyboard, HTMX и a11y proof отделены от object parser, script text hook и compile. T119 остаётся открытой. |

### Readiness/default-denial: принятое bounded решение main

Bridge §4 требует `native_ready.payload={}`. Текущий SDK создаёт этот общий
handshake после script completion независимо от calendar callbacks; следовательно,
сам native_ready **не доказывает calendar availability**. Unconditional calendar
interception после одного handshake при default-denied host было бы ошибкой:
standalone подавлен, intent отвергнут без reply, pending зависает. Такое включение
не входит в данный PASS.

Предложение main согласовано с уже принятым staged plan: calendar presentation
изначально disabled внутри existing script; host включает только fixed literal
через existing guarded nativeRunScript для exact meetings при обеих callbacks,
и отключает перед handler replacement/revoke. Пустой native_ready не меняется;
нового message/capability payload/host object/schema нет. JS-флаг — лишь
presentation, не authorization; source/route/nonce/current/owner guards остаются
native. Это native-owned reuse существующего update presentation pattern.

Практический runtime barrier обязателен, но **уже следует из accepted guards**:
валидный handshake И разрешающее native presentation состояние. Ни один из них
по отдельности не позволяет создавать pending или подавлять standalone click.
Нужно учитывать setter до script installation/handshake: включение нельзя
потерять как вызов отсутствующей функции; после bootstrap состояние сверяется
повторно. При disable/nonce replacement local pending и aria не оставляются
зависшими даже для ещё не admitted intent; cancellation не объявляет drain и не
создаёт auto fallback/new native work. Source tests должны охватить эти порядки,
default/partial callback pairs и temporary-not-ready terminal.

Pinned server calendar-series.js:23–30 пропускает `defaultPrevented` и untrusted
click, использует GRAFDesktop fallback. Поэтому native capture ownership с
preventDefault достаточен для этого bubble handler; копировать server fetch/
popup logic, добавлять сообщение readiness или новый server/UI не требуется.
Mac script показывает trusted capture, one pending, role=status/aria и handler
presence gate; его слабый 36-character UUID regex/общий observer/безусловный reply
update не заменяют более точные Windows нормы UUID/transitions/removal-cancel.
Это read-only reference, не предложение менять Mac/server.

Обязательные новые уточнения/ожидания перед test-first: **0** для указанного
default-disabled/fixed-literal дизайна. Требуемые tests: before handshake и
partial/no handlers без interception; trusted keyboard/click vs synthetic;
double click; same/replaced/removed HTMX UUID; pinned reply/unknown state/late
terminal/nonce change; disable и postMessage failure cleanup; aria/status/повтор.
Fake event.isTrusted/body-hook/objectparser equality/compile не доказывают реальный
WebView input, isolated/native authority или installed screen-reader/focus proof.

### Current hashes

Normative SHA-256 совпали с прежним PASS, без новых изменений:

| Файл относительно specs/200-windows-desktop-app | SHA-256 |
| --- | --- |
| spec.md | `8a61bbcb1ef78043e755aae48ba284118e1dab04118be00d7050e695c1a90ed0` |
| plan.md | `4e2aadb044c2ca8f21c8189e74c5f3338a3663fc6704db4280f7edccb79c7dec` |
| tasks.md | `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f` |
| quickstart.md | `189e52e8464f528589eb937315641aef1e293408b179bfc9084c76dc4ca39c1e` |
| contracts/windows-native-web-bridge.md | `a0acaca20097199e42cba490839cd719b8198ad124d916d611ec4bdcd6b11a65` |

Current Windows Host.cpp SHA-256:
`9dcc3cf218532c3aed461777b4f0e9eb03ba28f8a65b0210ff7f00d843640f1a`.
Reference SHA `721b5125d799ea798a4af0b3625e18d3c1109039`; Git-show bytes SHA-256:

- Mac EmbeddedCabinetCalendarJoinBridge.swift:
  `3932bf4f37d6fab48537c91c35d03161534154638612184d16bd9b850a6a8cd5`.
- Mac EmbeddedCabinetWebView.swift (registration/readiness callers):
  `05dfde689bbe45872bf75879b6782f29ed443aeadf039c24b598ed4acef39be8`.
- Server calendar-series.js:
  `3935a6c932d956d18a0ffae5068d95c526cb6b8b2829101a2ad3af540646f8e0`.

Checklist hashes и counts неизменны относительно Round238 table: wire5/0,
operation8/0, launcher5/0, всего18/0. Markers/new criteria не добавлялись.
Полученные от main final portable45/native49/full SDK BUILD0 receipts относятся
к host этапу, не принимаются здесь как installed или ещё отсутствующий shim PASS.
Reviewer изменил только append-only wire-gate report. Код/нормы/tasks/markers/
Git/GitHub/старые source reports сохранены; build/probe/VM не выполнялись.

**Terminal shim requirements: PASS C0/H0/M0/L0; дополнительных ожиданий 0.**
