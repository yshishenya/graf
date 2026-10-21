# Независимый допуск исправления синтетической загрузки F136 — 21.10.2026

## Решение и границы

**Предварительный допуск: PASS. Блокирующих замечаний к требованиям и выбранному плану: 0.**
Проверены оба reviewer-owned списка: requirements — 16 checked / 0 unchecked;
auth-navigation — 20 checked / 0 unchecked, всего 36 / 0. Каждая отметка
подтверждает качество требований и проверяемость плана; код будущего исправления
и исполнение проверок этим допуском не приняты.

Ветка `codex/136-auth-navigation-recovery`, HEAD
`adb345c42a55ea5a5acf7777fa4e13b7eacef7fc`, активный каталог F136 подтверждён
собственным prerequisite. Текущий `.specify/feature.json` уже указывает этот SHA;
прежнее расхождение указателя исправлено исполнителем до допуска. План на момент
проверки: SHA256 `4f5af22e9ede74c3723fb3a8dc4b870a34edde2644b11cddcf491717b981240a`.
Область: существующий high-risk-product срез T006/T017. Новых требований
продукта, задач, серверных контрактов и разрешений для этой проверки не нужно.
Независимый проверяющий меняет только примечания двух списков и этот отчёт.

## Подтверждённый отказ и предел объяснения

Выборочно прочитан сохранённый журнал macos-pr run39607758091. REQUESTED_SHA
совпадает с HEAD. Строки4703–4716 показывают один отказавший сценарий
`testSessionBoundaryCommittedPostCancellationRemainsUnsafe`: listener, host и
начальный документ готовы, затем настоящее ожидание didCommit истекает через
5 секунд; currentItem остаётся прежним. Ещё пять assertions этого же сценария
падают позднее. Это шесть сообщений об ошибке в одном тесте. Локальный PASS
на другом macOS не отменяет этот отказ. Версию macOS runner в данном выборочном
фрагменте отдельно не удостоверял; macOS14 указана в задании исполнителя.

В прочитанном исходнике сервер отправляет короткий HTML результата и объявляет
Content-Length больше фактического тела на1MiB, удерживая основное соединение.
Приём send callback без ошибки подтверждает только локальную отправку, а не
приём, разбор или commit WebKit. Незавершённая основная HTTP-сущность не даёт
межверсионной гарантии момента commit: WebKit вправе буферизовать данные.
Буферизация — правдоподобное объяснение; точный внутренний порог и отдельный
дефект WebKit этим журналом не доказаны. Это основание исправить способ
доставки синтетического документа и затем проверить его настоящими событиями,
а не признавать продуктовый код ошибочным или считать проблему уже решённой.

SHA256 внешнего журнала: `807dd84b7dbae6c82335037229be656b039b691577fcbe995a02605786c09f13`.
Сам журнал в репозиторий не переносился.

## Проверенный минимальный план

1. Только для committedCancellation сервер отдаёт полный POST HTML с точным
   Content-Length и обычным закрытием основного соединения. В HTML — обычный
   eager img на отдельный loopback путь `/f136-held-resource`, без lazy loading.
2. Отдельная точная ветка GET ресурса учитывает реальный запрос и удерживает
   его NWConnection без ответа. Она не выполняет повторный POST и не заменяет
   основную навигацию. У существующего владельца соединения сохраняется defer
   отмены. Этот сценарий удерживает одно соединение; остальные режимы fixture
   не начинают одновременно использовать тот же единственный слот.
3. Прежняя ветка `cancel && isResult` иначе отменит main response до отправки.
   Исполнитель должен исключить committedCancellation из этой ветки либо явно
   отправить полный основной ответ до неё. Другие cancellation-сценарии
   сохраняют прежнее поведение. Эта деталь сообщена исполнителю до правки.
4. Настоящий CommittedNavigationProbe по-прежнему передаёт события настоящему
   Coordinator. После реального didCommit нужно дождаться GET ресурса,
   подтвердить count1, новый currentItem, isLoading=true и finishCount=0,
   затем вызвать существующий stopLoading. Таймаут5s не увеличивается.
5. Сохраняются все прежние проверки: терминальное состояние без loading,
   malformedResponse отмены, тот же WebView/sessionBoundary, один POST,
   запрет Reload committed POST, отсутствие resend/finish, пригодность нового
   завершённого GET и Back, пропускающий опасную POST-запись без повтора.
6. Продуктовые identity/attach/stale guards, didCommit/didFinish и политика
   ресурсов не меняются. В прочитанной DesktopCabinetNavigationResponsePolicy
   неосновной ответ разрешён отдельно; отсутствие ответа ресурса не требует
   расширять route allowlist. Используются синтетические loopback данные.

План разделяет две проверяемые фазы: основной POST-документ может быть
зафиксирован, пока отдельный ресурс ещё удерживает загрузку незавершённой.
Это сильнее прежней зависимости от размера неполного main body, но фактический
порядок didCommit/stopLoading/didFail/didFinish всё равно должен подтвердить
WebKit. При неожиданном didFinish или отсутствии cancellation callback нельзя
ослаблять assertions, подставлять события вручную, добавлять skip, циклы
повторного запуска до успеха или увеличивать timeout.

## Повторная проверка каждого пункта требований

Порядок R01–R16 соответствует 16 существующим строкам requirements.md.

| Пункт | Основание текущего PASS |
|---|---|
| R01 | Spec описывает результат и поведение пользователя; механизм HTTP fixture находится в plan. |
| R02 | US1–US3 объясняют доступ к встречам, безопасную навигацию и отсутствие повтора формы. |
| R03 | Истории и FR сформулированы как наблюдаемые пользовательские результаты. |
| R04 | Scenarios, Requirements, SC, Assumptions и ограничения заполнены. |
| R05 | Нет NEEDS CLARIFICATION; committed/provisional и новая GET-запись разделены явно. |
| R06 | FR001–009 проверяемы; current slice и открытые OAuth/manual ограничены отдельно. |
| R07 | SC001 ограничивает белый экран10s после ответа; SC002–004 задают единственность и безопасность. |
| R08 | SC не зависят от конкретного языка, HTTP fixture или версии WebKit. |
| R09 | Успех, отмена, ошибка, вход, выход, повтор и история представлены историями/приёмкой. |
| R10 | Edge Cases охватывают provider cancel, rate limit, restart, expiry и query-переходы. |
| R11 | Current slice не закрывает T004/T011/T012/T016, не меняет сервер и выпуск. |
| R12 | Assumptions задают текущие routes/providers и синтетические данные. |
| R13 | FR прослеживаются в сценариях/SC, плане и tasks; текущая доставка относится к T006/T017. |
| R14 | US1–US3 покрывают первичный вход, навигацию и формы настроек. |
| R15 | Исходы SC можно измерить указанными сценариями; отметка не означает достигнутый runtime PASS. |
| R16 | Детали нового удержанного img не внесены в product spec. |

| Пункт auth-navigation | Основание текущего PASS |
|---|---|
| CHK001 | FR002/003 и Key Entities различают стабильный документ и одноразовый переход. |
| CHK002 | US1/US3, contract и OAuth continuation различают вход и привязку провайдера. |
| CHK003 | FR004 и таблица session boundary охватывают login/logout/expiry/reselection. |
| CHK004 | FR007 и Assumptions исключают изменение server methods/providers/storage. |
| CHK005 | FR001/003/007 запрещают повтор и замену семантики POST на GET. |
| CHK006 | FR002–005 и contract invariant3 охватывают native/gesture/restart/SwiftUI. |
| CHK007 | FR004 и contract определяют безопасную цель до успешной boundary;401 немедленно. |
| CHK008 | FR006 сохраняет нормальную историю; старый POST и новый GET разделены по записи. |
| CHK009 | US1 и SC001/002 дают отдельную проверку каждого метода без ложного закрытия OAuth. |
| CHK010 | US2/SC003/004 и plan сохраняют Reload/Back/Forward для безопасных записей. |
| CHK011 | Edge Cases/FR008 охватывают отмену, ошибки, rate limit и restart recovery. |
| CHK012 | FR007, quickstart, constitution/guidance запрещают секреты и личное содержимое в evidence. |
| CHK013 | FR009 сохраняет имена и единые правила доступности нативных controls. |
| CHK014 | Assumptions/FR007 не требуют обходного серверного GET или нового auth API. |
| CHK015 | Quickstart отделяет разрешённый тестовый вход/manual Dev от synthetic XCTest и metadata-only evidence. |
| CHK016 | Tasks и spec сохраняют открытыми T004/T011/T012/T016 и итоговую T017. |
| CHK017 | FR001/006/current acceptance покрывают success/error/cancel без remount/resend. |
| CHK018 | FR004/current acceptance и plan сохраняют identity/stale и immediate401/reselection guards. |
| CHK019 | Hosted отказ сохранён отдельно от прежнего local PASS и будущей hosted/manual приёмки. |
| CHK020 | FR002/003/005, data model/research/T018 сохраняют root-only login/sign-up. |

## Обязательное продолжение и незакрытые ворота

После правки: отдельный настоящий XCTest, весь кабинетный набор и полный набор
quickstart; сравнить фактические результаты и пропуски, прочитать новый diff
независимо. Затем требуются новые governance-fast, macos-pr, pr-metadata
для точного SHA и основы через общий validate-pr-checks.py. Успех на локальной
macOS не заменяет требуемый GitHub macOS запуск. T017 остаётся открытой до
успешных проверок и принятия PR. OAuth T004/T011/T012, ручная T016,
общая F136, release/deploy и установленный GRAF Dev этим отчётом не принимаются.

Во время этого предварительного ревью сборки, тесты, приложения, GitHub,
аккаунты, сеть и данные не изменялись. Просмотрены текущие артефакты, relevant
source и ограниченный фрагмент внешнего журнала. Полные обязательные документы
и supporting artifacts перечитаны самим проверяющим после потери контекста;
совпадение хеша не используется как замена чтению или runtime приёмке.

## Контрольные суммы прочитанных документов и исходников

Инструкции, продуктовые документы и active artifacts прочитаны полностью;
в больших Swift-файлах прочитаны применимые lifecycle/fixture участки.
Исторические references не выдаются за текущую приёмку. Ключевые требования
зафиксированы оригиналами ниже; отдельные копии исходных документов не создаются.

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
| `specs/136-auth-navigation-recovery/tasks.md` | `ac567e51b90d123ddaa948a92c626e9063663a1e9e3bcf7f3906ad1f2389f9dc` |
| `specs/136-auth-navigation-recovery/quickstart.md` | `880984fc8177b0baa3868db9ef77570c857c649e5d50fb292049a2987b36f144` |
| `specs/136-auth-navigation-recovery/research.md` | `5494a84d795102bf03f616b12d6f1dbe8acc905a5f5214a53ddb87fbef87c6b2` |
| `specs/136-auth-navigation-recovery/data-model.md` | `ea2683c1e7838b9d154508fac52f37e2b9f5098b4a443f3f793e164c257136ac` |
| `specs/136-auth-navigation-recovery/contracts/cabinet-navigation-lifecycle.md` | `fd3a209a57af6057c618d8667b64e62c97bf485db958d69f2665518a4929726f` |
| `apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetWebView.swift` | `8dd084e32763ac4d16df6ea6ff76a8114c959e642b0c66fbe83b12331b285078` |
| `apps/macos/RecApp/Sources/Cabinet/DesktopCabinetNavigationResponsePolicy.swift` | `43739cd36236e479216d9cc52c595730d8a9384923f48c1518107d4d5f40f685` |
| `apps/macos/Shared/Tests/DesktopCabinetWorkspaceTests.swift` | `0f4bdc8c5542f270aa39d57a36df24f251c20e3f089b58b48d37fe91e15dfd7e` |
| `apps/macos/Shared/Tests/DesktopCabinetRoutePolicyTests.swift` | `719dbbb0d0dbc63bd1752a1a6b3455cce2dc6e35bb11c0ab2da7b6d60221e7f9` |
