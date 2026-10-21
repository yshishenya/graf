# F136: исследование двух новых замечаний до реализации — 21.10.2026

Роль: независимый проверяющий требований и причин ошибок. Полоса:
существующая **high-risk-product**, T005/T006/T010/T017/T018, новые T019/T020. Рабочая копия
`f136-session-boundary/crisp`, ветка `codex/136-auth-navigation-recovery`,
HEAD `0c0cfba5690dead496aaa1bc00cabbe9cc0b6a76`. Начальное рабочее дерево
чистое; локальный feature pointer соответствует F136, ветке и этому HEAD.

**Итог проверки требований и плана: PASS, 36 checked / 0 unchecked,
блокеров проверяющего 0.** Первоначальный HOLD снят после полного чтения
обновлённых plan/research/quickstart/tasks. Обе причины подтверждены
исходниками; настоящие воспроизводящие тесты этого среза проверяющий не
запускал. Ранее принятый тестовый срез и его 86/1248 проверок не доказывают
устранение этих новых замечаний. Анализ согласованности и синхронизацию
issues перед кодом проверяет основной исполнитель отдельно.

Разрешены изменения только двух reviewer-owned списков и этого отчёта.
Продуктовый код, spec/plan/tasks, Git/GitHub, приложение, Dev и данные
проверяющий не менял; сборки и тесты в этом исследовании не запускал.
Источником замечаний служит сохранённый снимок обсуждений PR; новый live
запрос к GitHub в этой проверке не выполнялся.

## Завершающий слеш и граница сессии

Замечание [4337458144](https://github.com/yshishenya/graf/pull/7668#discussion_r4337458144)
подтверждено чтением.

1. `DesktopCabinetRoutePolicy.swift:491` не удаляет завершающий слеш.
   Классификация `:140–160` делит путь на компоненты, поэтому `/login/`
   и `/sign-up/` получают `.authLogin` и `.authSignup`.
2. `EmbeddedCabinetNavigationPolicy.isSafeDocument`,
   `EmbeddedCabinetWebView.swift:80–104`, допускает эти корневые документы
   и исключает вложенные auth actions тем же разделением компонентов.
3. `navigationDidFinish:519–526` выставляет `sessionExpired=true`, но
   отдельное точное сравнение с массивом `[/login, /sign-up]` не выставляет
   `sessionBoundaryPending` для завершающего слеша. Вследствие этого
   `commitPendingSessionBoundary:711` не меняет идентичность WebView
   и не уничтожает прежнюю историю при переходе protected → auth.

Минимальное направление исправления: определять корневой auth-документ
согласованно с существующим safe-document правилом. В этой ветке достаточно
`.authLogin/.authSignup` вместе с существующим `isSafeHistoryDocument`, который
уже отвергает вложенные действия и опасную POST-запись. Отдельный `hasPrefix`,
новая нормализация всего кабинета или расширение серверных маршрутов не нужны.
Сохранить порядок: финальные route/request identity/state, затем граница.

Нужна настоящая WebKit/SwiftUI-регрессия для обоих корней со слешем и query:
переход из завершённой защищённой страницы → финальный auth GET → ровно одна
граница → новый WebView без прежних protected history items. Существующие
root-only policy assertions `testOnlyRootAuthDocumentsCanEnterHistoryAndSwiftUIRecovery`
проверяют слеш, но не границу. Старый boundary helper проверяет только `/login`
и содержит точные сравнения этого пути при выборе initial/finished state;
при расширении матрицы эти ожидания должны различать вид маршрута корректно.
Вложенные start/verify, callback и POST не должны создавать новую успешную
границу сами по себе. Обычный корень без слеша остаётся контрольным случаем.

## Предварительная отмена и удаление сохранённого документа

Замечание [4337458154](https://github.com/yshishenya/graf/pull/7668#discussion_r4337458154)
подтверждено чтением всей цепочки состояния.

1. Разрешённая основная navigation action переводит `cabinetState` в
   `.loading`, `EmbeddedCabinetWebView.swift:2392/2419`.
2. Настоящая provisional failure проходит attachment/current-navigation
   guards, очищает активную навигацию и вызывает
   `transitionAfterNavigationFailure`, `:2772–2780`.
3. `DesktopCabinetState.state(forNavigationError:currentState:)`,
   `DesktopCabinetState.swift:154–179`, сохраняет состояние для ожидаемых
   `NSURLErrorCancelled` и `WebKitErrorDomain/102`; здесь оно уже `.loading`.
4. `transitionAfterNavigationFailure:2816–2823` превращает `.loading` в
   `.malformedResponse`. `DesktopCabinetWorkspace.shouldShowEmbeddedSurface`,
   `DesktopCabinetState.swift:351`, для этого состояния возвращает false.
5. Настоящий `DesktopCabinetWorkspaceView.swift:126–171` заменяет embedded
   ветку на unavailable. SwiftUI демонтирует `EmbeddedCabinetWebView`;
   `dismantleNSView:1793` отсоединяет controller, observers и message handlers.
   Сохранённый GET/current item исчезает из пользовательского экрана вместе
   с полезной историей, хотя controller до демонтажа мог разрешать Reload.

Существующий `SessionBoundaryFixture` в конце
`DesktopCabinetWorkspaceTests.swift` всегда монтирует EmbeddedCabinetWebView
независимо от `document.state`. Поэтому текущая проверка cancellation ожидает
`.malformedResponse` и всё равно видит старый экземпляр. Она не проверяет
условную ветку настоящего Workspace и не опровергает замечание.

### Минимальная безопасная граница восстановления

Допустимо сохранить видимость только при ожидаемой **предварительной**
отмене и наличии того же ранее завершённого безопасного документа текущей
сессии. Безусловное `.ready` для любой ошибки/отмены недопустимо. Нельзя
выдавать незавершённую первую загрузку, committed POST, unsafe auth action,
устаревший callback, старый attachment или отозванную сессию за ready.

Один URL, static allow или `canReload` не доказывают предыдущее завершение:
`observeNavigationRequest:623–662` добавляет безопасный URL уже при action,
до настоящего didFinish. Пример минимального решения — слабая ссылка на
последний подтверждённый безопасный `WKBackForwardListItem` рядом с уже
существующим controller ledger. Сертифицировать её может только принятый
настоящий didFinish с безопасным методом; resource/download terminal и
синтетическая сверка адреса этого не делают. Восстановление требует той же
currentItem, действующих safe-history/session guards, прежней `.loading`
и accepted provisional identity. После attach/detach/session fence и
небезопасного/неподтверждённого завершения прежнее доказательство не должно
переходить к новому документу. Конкретная реализация выбирается обновлённым
планом; новый журнал отката URL или параллельный navigation механизм не нужен.

Дополнительная зависимость сохранённой страницы: `didStartProvisionalNavigation`
инвалидирует recording/notification bridges. Их `invalidate()` очищает nonce
и WebView; notification bridge ещё вызывает `disconnect()` в странице.
Одного возврата `.ready` недостаточно для работоспособности этих настроек.
При подтверждённом восстановлении нужно повторно задействовать существующие
activation/current-document/auth-epoch проверки, без повторения формы или
операции календаря. `synchronizeUserTime` уже содержит защищённый путь
активации notification settings после согласования cookies; прямой обход
`refreshContext` недопустим. Этот остаток выявлен чтением, отдельный runtime
отказ bridge в данном исследовании не заявляется.

### Требуемые регрессии

| Сценарий | Наблюдаемое доказательство |
|---|---|
| Завершённый GET → удержанный POST → stopLoading до commit | Настоящий DesktopCabinetWorkspaceView после обновления SwiftUI всё ещё содержит тот же WKWebView в том же окне; прежние DOM marker/currentItem/route сохраняются, не loading, нет повторного GET/POST или границы. |
| Продолжение после отмены | Reload и Back/Forward реально работают по безопасным GET; POST остаётся отправленным один раз. DOM-действие исполняется в сохранённом документе. |
| Первая загрузка без завершённого документа | Ожидаемая отмена не создаёт ложную ready; безопасное восстановление доступно вручную. |
| Новый POST уже committed, held resource ещё не завершён | Отмена не реабилитирует POST, Reload не повторяет его; настоящий новый GET может сертифицировать только собственную запись. |
| 401/выбор пространства; detach; устаревшие события | Прежняя protected page не восстанавливается, действующие identity/session guards сохранены. |
| Последующая настоящая сеть/timeout или отказ response policy | Не получают новое общее разрешение ready; существующие состояния и безопасное восстановление сохраняются. |
| Корневой auth и вложенные действия; повторяющиеся URL; resource terminal | Сессионная граница и сертификация документа не подменяются URL, методом синтетического запроса или завершением ресурса. |
| Настройки записи/уведомлений в восстановленном документе | Существующая activation проходит с новой актуальной nonce/epoch и текущим документом; отменённая операция не повторяется. |

Новая проверка видимости должна использовать настоящий Workspace в
NSHostingView/обычном синтетическом окне. Недостаточны чистый predicate,
старый всегда монтируемый fixture или одна сохранённая сильная ссылка на WebView.
Нужно дать SwiftUI обработать изменение и повторно найти view в дереве, проверить
его принадлежность окну и DOM, а не только object identity. Для двух новых
причин требуются отдельные RED/GREEN, затем весь кабинетный и полный набор
quickstart. Запуски и оценку результатов выполняет назначенный исполнитель.

## Повторная проверка всех пунктов требований

Requirements: content quality 4/4 подтверждены пользовательскими историями,
FR и отдельным планом; requirement completeness 8/8 — определениями,
уточнениями17/19.10, измеримыми SC, исключениями и границами; feature readiness
4/4 — соответствием US/AC/FR/SC. Всего **16 checked / 0 unchecked**.

Auth-navigation: CHK001–004 — stable/transient, две OAuth цели,
сессионные переходы и scope; CHK005–008 — запрет повтора, единое правило
истории, порядок границы и обычная навигация; CHK009–013 — измеримость,
кнопки/ошибки/отмена, секреты и доступность; CHK014–015 — серверные зависимости
и безопасная ручная приёмка; CHK016–020 — границы среза, ordinary POST,
identity/сессия, разделение доказательств и root-only auth. По всем двадцати
пунктам есть явное основание в прочитанных spec/plan/research/data-model/contract/
quickstart/tasks. Всего **20 checked / 0 unchecked**.

Отметки проверяют качество требований и сохранены. Новые дефекты относятся
к уже существующим FR-004/006; отдельного продуктового решения пользователя
не требуется. Первоначальный HOLD касался отсутствия обновлённого плана и
неверной прежней фразы research о сохранении WebView при `.malformedResponse`.
После чтения исправленных документов этот блокер снят, как описано ниже.

## Окончательный допуск обновлённого плана

Полностью перечитаны актуальные `plan.md`, `research.md`, `quickstart.md`,
`tasks.md` и действующий `AGENTS.md`. План §«Два замечания PR — 21.10.2026»
принимает минимальный общий путь: auth kind плюс существующий safe-history
predicate для границы, одна слабая ссылка на настоящий завершённый безопасный
history item для предварительной отмены. Нет новой нормализации всех маршрутов,
журнала отката URL или безусловного восстановления ready.

План явно сохраняет safe pending method, тот же currentItem и действующую
attachment/session проверку; допускает восстановление finishedState только
из loading после ожидаемой текущей provisional cancellation. Первая
незавершённая загрузка, committed POST, ресурсное/синтетическое завершение,
401/выбор пространства и устаревшие/отсоединённые события не дают права
восстанавливать прежний защищённый документ. Маркер очищается при смене
attachment/сессии и неподтверждённом или unsafe настоящем finish.

Учтена зависимость настроек: существующие `recordingSettingsBridge.activate`
и `synchronizeUserTime` восстанавливают соединение только сохранённого
документа; notification settings остаются за cookies/authEpoch/current-document
проверками. Календарная операция не повторяется, предпочтения пользователя
не изменяются ради теста. Research исправляет неверное прежнее утверждение
о `.malformedResponse`; quickstart требует настоящий Workspace после
обновления SwiftUI, DOM/currentItem и WebView в том же окне, единственный POST,
отрицательные initial/committed случаи и прежние 401/stale/detach проверки.

Append-only Phase 8 сохраняет прежние task IDs и добавляет последовательные
T019/#7688 и T020/#7689 с точными файлами и связями FR/SC. Номера issues
здесь прочитаны из tasks.md; их live-состояние проверяющий не подтверждал.
Эти задачи теперь явно входят в зависимость открытой T017. Требования
достаточно полны и проверяемы для описанного исправления: **requirements
16/0, auth-navigation 20/0; всего 36 checked / 0 unchecked, блокеров 0**.

Это предварительный допуск требований и плана, а не приёмка будущего кода.
Основному исполнителю остаются актуальный analyze и issue sync перед кодом,
настоящие RED/GREEN для обоих замечаний, quickstart, converge, независимое
итоговое ревью и три обязательные GitHub проверки нового точного SHA/основы.
OAuth T004/T011/T012, установленная ручная T016 и вся F136 остаются открытыми.

## Источники и границы доказательств

После сжатия контекста reviewer полностью перечитал mandatory AGENTS/index,
document-reading/development-process/codex-worktrees/spec-kit-flow,
конституцию, PRD, current-product-status, product-gates,
release-and-validation и активные spec/plan/tasks/quickstart/research/data-model/
contract/validation плюс оба checklist. Исторические linked receipts не
использованы как текущая приёмка; новые runtime/hosted результаты не заявлены.
Применён code-reviewer для чтения текущего кода; checkout/preflight из общего
навыка не выполнялись из-за более узкого назначения проверяющего.

| Источник | SHA256 |
|---|---|
| AGENTS.md | `4bdbcd97dbb86b560cc5cf5294684d7adfbe85a1a39716765145072aa840ae77` |
| guidance README | `2f3e0339a89d3ccdf0878026920955a189584d6a985116b069584cd78b3c75bb` |
| document-reading | `5263860b1974df022826ac81c2482e6ee92100bc0bb718ab5a29b32e2422e411` |
| development-process | `1037b91f153f0757fff372e26cd05dd31433158c9c35d149125197a8a523f20d` |
| codex-worktrees | `d7d8c9cce8315c17efaa1da05ece80c2542ca01b966f81fb848580104b785e1d` |
| spec-kit-flow | `afb816ce48624eb79fcd7fd44d09f0986296e87ef1cfecd790228ac70a5b9b9e` |
| constitution | `7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8` |
| PRD | `0f3ccfcfa60062bb0aae6802eeb0012056a635a30cb9f46f54d1992d0b4f57c2` |
| current-product-status | `25b7f383be47c7160da8e852006ff82019f30a5f9c371fc30baa79238649cd16` |
| product-gates | `9f7072c879490d250053cb7397ad6b9b68fdcde17bdf9367ed874a41e450b5f5` |
| release-and-validation | `ff0d996c95101d5f782259661131db1b7528b3bf58991603f5652092e1e5256f` |
| spec | `6810346229072b50319c981607a0fb2a3164105075a4024a624f0e4b7bcd2668` |
| plan до уточнения | `4f5af22e9ede74c3723fb3a8dc4b870a34edde2644b11cddcf491717b981240a` |
| plan после уточнения | `db910631b8be797c98ef0eeb92333c879974960f832e92fbcdeb5a08548d4127` |
| tasks после добавления T019/T020 и issue links | `91f4af4b319774160cd0764529d60e565f1ffcb15411b4bda210d1042d013c78` |
| quickstart после уточнения | `9167952e3e862622cc9154dfc272bcc9344be6343a25e8ed86a28f6c7ee3eb19` |
| research до уточнения | `5494a84d795102bf03f616b12d6f1dbe8acc905a5f5214a53ddb87fbef87c6b2` |
| research после уточнения | `e49a028936a317a75e21afc6b4f554b04bab19f8175bb0635f3eb377fb2603a8` |
| data-model | `ea2683c1e7838b9d154508fac52f37e2b9f5098b4a443f3f793e164c257136ac` |
| cabinet-navigation-lifecycle | `fd3a209a57af6057c618d8667b64e62c97bf485db958d69f2665518a4929726f` |
| validation | `e26b894edb95cec2810d70b833885fc707252eb8256bae5fb0d23507c43d7186` |
| EmbeddedCabinetWebView.swift | `8dd084e32763ac4d16df6ea6ff76a8114c959e642b0c66fbe83b12331b285078` |
| DesktopCabinetState.swift | `426e6e132b76d0cd6c1877b17c7ce6a30c91e3207097bdbaa17eeba247f9757f` |
| DesktopCabinetWorkspaceView.swift | `c62897a32cd0bc2b7b020697a7f91bf51ab0cc693ec9c59beb4a1113747ab70e` |
| DesktopCabinetRoutePolicy.swift | `a0688ae25b0d25ddc2329bf50ed58069eb1148f5c20e28930082ed4a3cd5c1ea` |
| DesktopCabinetWorkspaceTests.swift | `e374b04a579464737a97d9d411a3d5c260edf7ac882a42d9a82986c36b3f0552` |
| RecordingSettingsBridge | `51194127db5fbf544eb5325250e43f6c7ba75a67a0b22185db05652a9e680358` |
| NotificationSettingsBridge | `90e5478b81f4b230e56a47bcae9ba056c131dc7f0947da2ddc20adf2002eebca` |

T017 остаётся открытой. OAuth T004/T011/T012, ручная T016 и вся F136 также
остаются открытыми. Новые три GitHub checks точного SHA/основы, независимое
итоговое ревью и обычные защитные проверки принятия PR по-прежнему обязательны.
Выпуск, развёртывание и замена установленного GRAF Dev в это назначение не входят.
