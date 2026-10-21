# Независимое итоговое ревью синтетического POST F136 — 21.10.2026

## Решение и область

**APPROVE ограниченного исправления теста. Замечаний: 0; блокирующих замечаний к этому исправлению: 0.**

Проверена рабочая дельта на HEAD `adb345c42a55ea5a5acf7777fa4e13b7eacef7fc`,
ветка `codex/136-auth-navigation-recovery`, активный каталог F136 подтверждён
по указателю и ветке. Полоса: существующий **high-risk-product**, T006/T017.
На момент ревью нового коммита с этим исправлением ещё нет. Решение относится
к прочитанным байтам теста SHA256
`e374b04a579464737a97d9d411a3d5c260edf7ac882a42d9a82986c36b3f0552`.

Проверяющий меняет только примечания `checklists/requirements.md`,
`checklists/auth-navigation.md` и этот отчёт. Код, spec, plan, tasks,
validation, Git/GitHub, приложение и данные проверяющий не менял.
Сборки и тесты повторно не запускались: самостоятельно прочитаны фактические
исходники, diff и журналы исполнителя. Это независимая оценка доказательств,
а не второе независимое исполнение XCTest.

## Исправление и сохранённые проверки

В `DesktopCabinetWorkspaceTests.swift` изменена доставка одного синтетического
сценария `testSessionBoundaryCommittedPostCancellationRemainsUnsafe`:

1. Основной POST получает весь HTML с точным `Content-Length=html.utf8.count`;
   соединение отправляет полный ответ и закрывается обычным путём. Прежнее
   намеренное обещание ещё1MiB основного тела удалено.
2. Только `committedCancellation && isPost` добавляет обычный `img` на
   `/f136-held-resource`. Отдельная точная ветка GET учитывает запрос,
   удерживает его соединение без ответа и возвращается до обработки документа.
   Повторного POST и второго основного перехода она не создаёт.
3. Из прежней ветки отмены основного ответа исключён `committedCancellation`;
   остальные режимы `cancel`, network failure, redirect, reselect и
   supersedesPendingForm сохраняют прежние ветки. Это выполняет условие
   предварительного допуска, иначе основной документ не был бы отправлен.
4. После настоящего `didCommit` с прежним timeout5s тест ограниченно ожидает
   фактический GET ресурса (250×20ms), проверяет ровно один запрос, новую
   history item, `webView.isLoading=true` и `finishCount=0`. Затем выполняется
   прежний настоящий `stopLoading`. Ожидание не подменено ручным событием.
5. После отмены остаются assertions терминального состояния без loading,
   `.malformedResponse`, прежней session boundary и того же WKWebView,
   единственного POST, запрета Reload committed POST и отсутствия resend.
   `finishCount=0` проверяется также после попытки Reload. Затем прежняя
   проверка завершает новый безопасный GET и подтверждает полезный Back,
   пропускающий опасную POST-запись без повторной отправки.

Сам `CommittedNavigationProbe` не менялся: настоящий `didCommit` передаётся
Coordinator и выполняет expectation, настоящий `didFinish` учитывается и
передаётся Coordinator; другие delegate selectors перенаправляются ему.
Новые ручные callbacks, skip, увеличение существующих timeout или ослабление
продуктовых assertions не введены. Сравнение имён тестов с HEAD:63 до/63 после,
удалено0, добавлено0. Новый сценарий по имени не создавался, исправлен прежний.

У `SessionBoundaryRequests` сохранены lock и `defer` вызова
`cancelHeldConnection()`. Единственный вызов `committedCancellation=true`
использует `method=POST,cancel=true` и не совмещён с удерживаемой первой формой
`supersedesPendingForm`; один существующий слот соединения достаточен для
этого сценария. Этот вывод из исходников не является отдельным измерением
остатков процессов или соединений после исполнения.

## Продуктовый код и требования

`EmbeddedCabinetWebView.swift` побайтно не изменён этой дельтой, SHA256
`8dd084e32763ac4d16df6ea6ff76a8114c959e642b0c66fbe83b12331b285078`.
Самостоятельно перечитаны применимые controller/coordinator пути:
`navigationDidCommit`, `navigationDidFinish`, `navigationDidFail`,
`navigationDidCancel`, текущая WKNavigation identity, фильтр history items,
настоящие delegate commit/finish/fail и response handling.

Принятая новая POST history item становится опасной только при настоящем
commit текущего WKNavigation в прикреплённом WKWebView. Ошибка или отмена
не делает её безопасной; `confirmsDocument=true` приходит только из настоящего
didFinish. Устаревшие события отклоняются до завершения текущего перехода.
Прочитана вся `DesktopCabinetNavigationResponsePolicy`: неосновной response
разрешён отдельным guard. Новый удержанный ресурс не требует расширения
разрешённых основных маршрутов или изменения origin/header policy.

После сжатия контекста самостоятельно полностью перечитаны применимые
инструкции, конституция, PRD, текущий статус, product-gates,
release-and-validation и active spec/plan/tasks/quickstart/research/data-model/
contract, оба списка требований и validation. Хеши служат контролем байтов,
а не заменой чтению. Относительно предварительного отчёта все перечисленные
инструкции, исходники продукта и документы требований остались прежними;
**tasks и validation обновлены исполнителем и прочитаны полностью заново**.
Они точно сохраняют текущие результаты, прежний отказ и открытые T017/OAuth/manual.
Исторические указания об отдельных согласиях в старых записях validation
не выдаются за действующее правило или новое требование к пользователю.

Повторно проверены все пункты обоих списков. Подробная матрица R01–R16 и
CHK001–CHK020 в [предварительном отчёте](review-hosted-commit-plan-20261021.md)
сохраняет основания: spec не менялся, план соблюдён, изменение не вводит нового
требования продукта. Отдельно перепроверены CHK005/006/008/010/017/018:
единственность POST, общая безопасная история, последующий GET, отмена и
identity guards сохранены. CHK012/015/019 сохраняют синтетические данные,
раздельные local/hosted/manual доказательства и отсутствие секретов в отчёте.
Отметки подтверждают качество требований и проверяемость текущего среза;
они не аттестуют исполнение всей F136.

## Фактически прочитанные журналы

Сохранённый `hosted-final-failure.log` относится к run39607758091 на точном
HEAD выше. Его прежний прочитанный отказ остаётся: один сценарий не получил
настоящий didCommit и дал6 ошибок assertions. Это не6 отказавших тестов.
Локальный успех не исправляет этот GitHub результат задним числом. Возможная
буферизация неполного основного HTTP body объясняет выбор исправления;
конкретный внутренний порог WebKit или подтверждённая межверсионная причина
не установлены и не заявляются.

Прочитаны строки текущего сценария, итоги наборов и все причины SKIP в
`held-resource-*.log`; полный большой журнал не переносится в репозиторий.

| Журнал | Фактический результат |
|---|---|
| `held-resource-focused.log` |1 PASS,0 FAIL,0 SKIP; сценарий0.928s, внешний итог0.929s |
| `held-resource-cabinet.log` |RoutePolicy23+Workspace63=86 PASS,0 FAIL,0 SKIP;3.873s; исправленный сценарий0.325s |
| `held-resource-full.log` |1248 выбранных:1246 PASS,2 SKIP,0 FAIL/0 unexpected;111.939s; исправленный сценарий0.294s |
| `governance.log` |`spec-kit-governance: OK (bootstrap integrity + GRAF invariants)` |

В полном журнале строки1146–1147 подтверждают SKIP
`testCardSurfacesCanBeCapturedForReferenceComparison`: не настроен
`GRAF_CARD_SNAPSHOT_DIR`; строки2845–2846 подтверждают SKIP
`testRenderSyntheticPermissionStates`: не настроен `GRAF_PERMISSION_PREVIEW_DIR`.
Это необязательный экспорт изображений. Других SKIP в этом запуске нет;
все86 кабинетных тестов прошли. Пропуски не считаются PASS или установленной
приёмкой. Пересекающиеся1/86/1248 не суммируются как разные проверки.

Текущие прочитанные журналы не доказывают нового исполнения ContractValidation;
его прежнее подтверждение относится к своей проверке. Deployment target
`arm64e-apple-macos14.0` не удостоверяет версию текущей ОС. Исполнение на
локальной macOS26/Swift6.3.3 не заменяет новый GitHub macOS14/Swift6.0.3 запуск.

## Оставшиеся ворота

Новых обязательных кодовых остатков именно этого исправления теста не выявлено.
После коммита требуются новые `governance-fast`, `macos-pr`, `pr-metadata` на
точном SHA и проверенной основе PR#7668 через общий
`scripts/validate-pr-checks.py`. Лишь после их успешного результата можно
принимать этот срез; APPROVE этого отчёта не является разрешением обойти CI.
T017 остаётся открытой. T004/T011/T012 (OAuth/provider linking), T016
(ручная приёмка в единственном GRAF Dev), общая F136, выпуск и production
не закрываются. Установленное приложение этим ревью не проверялось.

## Контрольные суммы

Полные обязательные документы перечитаны; в больших Swift-файлах прочитаны
применимые части, как описано выше. Состояние checklist после добавления
итогового примечания перечитывается полностью; итоги:requirements16/0,
auth-navigation20/0, всего36 checked/0 unchecked. Исторические заметки и
отметки сохранены.

| Файл | SHA256 |
|---|---|
| `AGENTS.md` | `4bdbcd97dbb86b560cc5cf5294684d7adfbe85a1a39716765145072aa840ae77` |
| `docs/agent-guidance/README.md` | `2f3e0339a89d3ccdf0878026920955a189584d6a985116b069584cd78b3c75bb` |
| `docs/agent-guidance/document-reading.md` | `5263860b1974df022826ac81c2482e6ee92100bc0bb718ab5a29b32e2422e411` |
| `docs/agent-guidance/development-process.md` | `1037b91f153f0757fff372e26cd05dd31433158c9c35d149125197a8a523f20d` |
| `docs/agent-guidance/codex-worktrees.md` | `d7d8c9cce8315c17efaa1da05ece80c2542ca01b966f81fb848580104b785e1d` |
| `docs/agent-guidance/spec-kit-flow.md` | `afb816ce48624eb79fcd7fd44d09f0986296e87ef1cfecd790228ac70a5b9b9e` |
| `.specify/memory/constitution.md` | `7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8` |
| `docs/prd-voice-layer-final.md` | `0f3ccfcfa60062bb0aae6802eeb0012056a635a30cb9f46f54d1992d0b4f57c2` |
| `docs/current-product-status.md` | `25b7f383be47c7160da8e852006ff82019f30a5f9c371fc30baa79238649cd16` |
| `docs/agent-guidance/product-gates.md` | `9f7072c879490d250053cb7397ad6b9b68fdcde17bdf9367ed874a41e450b5f5` |
| `docs/agent-guidance/release-and-validation.md` | `ff0d996c95101d5f782259661131db1b7528b3bf58991603f5652092e1e5256f` |
| `specs/136-auth-navigation-recovery/spec.md` | `6810346229072b50319c981607a0fb2a3164105075a4024a624f0e4b7bcd2668` |
| `specs/136-auth-navigation-recovery/plan.md` | `4f5af22e9ede74c3723fb3a8dc4b870a34edde2644b11cddcf491717b981240a` |
| `specs/136-auth-navigation-recovery/tasks.md` | `c430c6af9457d2fdfaf0136329037aa2aa07aa73dd2238221c7724789f627797` |
| `specs/136-auth-navigation-recovery/quickstart.md` | `880984fc8177b0baa3868db9ef77570c857c649e5d50fb292049a2987b36f144` |
| `specs/136-auth-navigation-recovery/research.md` | `5494a84d795102bf03f616b12d6f1dbe8acc905a5f5214a53ddb87fbef87c6b2` |
| `specs/136-auth-navigation-recovery/data-model.md` | `ea2683c1e7838b9d154508fac52f37e2b9f5098b4a443f3f793e164c257136ac` |
| `specs/136-auth-navigation-recovery/contracts/cabinet-navigation-lifecycle.md` | `fd3a209a57af6057c618d8667b64e62c97bf485db958d69f2665518a4929726f` |
| `apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetWebView.swift` | `8dd084e32763ac4d16df6ea6ff76a8114c959e642b0c66fbe83b12331b285078` |
| `apps/macos/RecApp/Sources/Cabinet/DesktopCabinetNavigationResponsePolicy.swift` | `43739cd36236e479216d9cc52c595730d8a9384923f48c1518107d4d5f40f685` |
| `apps/macos/Shared/Tests/DesktopCabinetWorkspaceTests.swift` | `e374b04a579464737a97d9d411a3d5c260edf7ac882a42d9a82986c36b3f0552` |
| `apps/macos/Shared/Tests/DesktopCabinetRoutePolicyTests.swift` | `719dbbb0d0dbc63bd1752a1a6b3455cce2dc6e35bb11c0ab2da7b6d60221e7f9` |
| `specs/136-auth-navigation-recovery/validation.md` | `6fec184a04a2f083c011820be252a1c6cdc9d8f6f312ea33d3265d3db2782d4c` |

| Внешний журнал | SHA256 |
|---|---|
| `held-resource-focused.log` | `ecdc7d3dc590fef423bdaea2a8472890017f95148f141616ac361ecc18ed2860` |
| `held-resource-cabinet.log` | `e313bba03b2a56b27815e20874b119e06d52ae793541361b7c2473ce02ae01ac` |
| `held-resource-full.log` | `c076db67a726add8e8b984f5963e6e440ec2a2027b2c9399847fab8e61a4c12c` |
| `governance.log` | `59cfeb588ee423427af9f09c0dfe4d3d2b36bbfcca7bbb8b49ba0f0b1ce6bceb` |
| `hosted-final-failure.log` | `807dd84b7dbae6c82335037229be656b039b691577fcbe995a02605786c09f13` |
