# Независимое итоговое ревью F136 — 21.10.2026

Проверяющий: `/root/review_f290_infra`. Ветка:
`codex/136-auth-navigation-recovery`; HEAD:
`3ca5da7a9745e543414643ae3917b0e790ba9203`; проверенная основа:
`845e6dcff7eb7f8e0e2b884902080ecb96582a3a`.
Полоса: существующий `high-risk-product`, исправление T005/T006/T010/T018,
подготовка доказательств открытой T017.

**APPROVE ограниченного исправления кода и регрессий. Замечаний: 0;
блокирующих замечаний к этому diff: 0.** Требования подтверждены по всем
пунктам: requirements **16 checked / 0 unchecked**, auth-navigation
**20 checked / 0 unchecked**, всего **36/0**.

Результат относится к прочитанным изменённым файлам, указанным ниже по SHA256.
Они ещё не входят в указанный HEAD. Локальное заключение не подтверждает
новый коммит, GitHub checks, слияние, установленное приложение, выпуск или
развёртывание. T004/T011/T012, ручная T016 и итоговая T017 остаются открытыми.

## Проверенные источники и метод

После перебазирования сверены branch, HEAD, merge-base, `.specify/feature.json`
и вывод `check-prerequisites.sh --json --paths-only`: все указывают на F136.
Полностью перечитаны AGENTS, guidance index, document-reading,
codex-worktrees, spec-kit-flow, development-process, release-and-validation,
конституция, PRD, current-product-status и product-gates; затем spec, plan,
tasks, quickstart, research, data-model, lifecycle contract и оба checklist.
Прочитан предварительный [отчёт](review-plan-20261021.md) с разбором всех 36
пунктов. Новых требований или неопределённостей в текущем изменении не найдено.

Независимо прочитаны фактические diff кода и тестов, controller и общие
callers: start/redirect/commit/finish/fail/cancel, attach/detach,
response policy, download/resource terminals, native Back/Forward/Reload,
отбор history items и отклонение устаревших событий. Проверены исходники
новых регрессий, синтетического HTTP-сервера и наблюдателя настоящего commit.
Сборки и тесты проверяющий не запускал, чтобы не пересекаться с исполнителем;
результаты ниже непосредственно сверены с сохранёнными журналами.

## Вывод по коду

В `observeNavigationRequest` небезопасный запрос сохраняет ожидающий признак
`pendingHistoryRequestIsSafe=false`, не меняя безопасность ещё видимого GET.
Новый `navigationDidCommit` меняет наборы истории только после проверки
присоединённого WebView и текущей WKNavigation. Опасными становятся настоящие
`currentItem` и его URL уже принятого документа. Признак не снимается при
последующей ошибке/отмене; отдельного механизма отката URL не добавлено.

`didFinish` по-прежнему подтверждает безопасность только настоящего
завершившегося документа. Новый GET восстанавливает доступность собственной
записи; прежние POST остаются в наборе опасных WKBackForwardListItem.
При выборе нативной истории они пропускаются; неоднозначный жест к тому же
адресу отклоняется. Синтетическая сверка URL в finish, скачивание и отказ
ресурса не подтверждают GET и не реабилитируют POST.

Устаревшие непустые WKNavigation проходят прежнюю проверку текущей identity
до любых изменений. Ожидающий новый action блокирует прежние terminal events;
start/подтверждённый redirect фиксируют нужную identity. Guard не ослаблен и
не заменён сравнением одного URL. Ошибка/отмена очищают ожидающее состояние,
а attach/detach и граница сессии сбрасывают реестры. Немедленная защита 401/
выбора пространства и порядок стабильной страницы до успешной границы
сохранены. Origin/header policy, billing, download и native Record/Stop
этот diff не изменяет.

Новый `CommittedNavigationProbe` использует стандартную Objective-C передачу
селекторов настоящему Coordinator. Он сообщает поддержку методов Coordinator,
пересылает остальные события, передаёт настоящий `didCommit`, отдельно считает
`didFinish` и возвращает исходного delegate до последующей проверки истории.
Большой незавершённый HTTP body позволяет остановить настоящий POST после
commit до finish. Это не искусственная отправка didFail уже завершённой формы.
Старые события в отдельном тесте вводятся явно через сохранённую реальную
WKNavigation; такой тест доказывает guard, а не естественный порядок WebKit.

## Соответствие обязательной матрице предварительного ревью

| Критерий | Непосредственно проверенное доказательство | Итог |
|---|---|---|
| 1. Сетевая ошибка POST U до commit сохраняет GET U | `testSessionBoundarySettingsPostNetworkFailureKeepsSafeGet`: currentItem/WebView/сессия сохранены, loading завершён, Reload создаёт GET, POST остаётся1; затем Back/Forward | PASS |
| 2. Отказ response policy 503 и явная provisional cancel | Существующие Error/Cancellation tests расширены теми же утверждениями про прежний item, Reload/Back/Forward и счётчики; отдельные настоящие ответы/stopLoading | PASS |
| 3. POST действительно committed, отменён до finish | Новый CommittedPostCancellation: реальный delegate commit, другой currentItem, `isLoading=true`, finishCount0, после stop Reload запрещён; новый GET U становится безопасным, native Back пропускает старый POST, POST не повторён | PASS |
| 4. Новый настоящий GET U после POST U | Существующий `testNewGetAfterPostRestoresHistoryWithoutReplayingOldPost` прошёл; Reload/Back/Forward, старый POST skipped, настоящий Coordinator отклоняет WebKit history action | PASS |
| 5. Старые commit/finish/fail при новом pending POST | Cancellation test сохраняет прежнюю завершённую WKNavigation и передаёт все три события при новой provisional форме; новая loading/item не меняются, конечный прежний GET пригоден для истории | PASS |
| 6. Общие terminal/reset пути и303 | 12 session scenarios, resource404 после supersededGET, чтение download callers и сбросов; ни один ресурсный terminal не сертифицирует текущий POST | PASS |
| 7. Сессия, root-only auth и общие ограничения | Login/Logout проверяют route/state до boundary,401/reselection немедленно закрывают protected commands; root-only, origin/header, billing и доступные идентификаторы входят в86 проверок | PASS |

Для пункта 3 проверена именно отмена после commit. Произвольные ошибки всех
доменов после commit отдельно не вводились; они используют прочитанные общие
пути `navigationDidFail`/`navigationDidCancel`, сохраняющие опасный item.
Внешние OAuth и установленная ручная матрица этой синтетической проверкой
не покрываются.

## Проверка поправки синтетического сервера

Первый общий запуск macOS получил ошибку `Incomplete synthetic session request`
из `receiveSessionFixtureRequest`, асинхронно отнесённую к следующему тесту
F277. Это отказ тестового HTTP-сервера, а не доказанный дефект F277.
При закрытии TCP без единого байта HTTP прежний сервер тоже вызывал эту ошибку.

Исполнитель добавил в обычный GET-сценарий настоящее пустое TCP-соединение с
отправкой EOF через `.finalMessage` и ожиданием закрытия. На сервере без нового
условия тот же сценарий даёт точный отказ `Incomplete synthetic session request`
в `unused-connection-red-final.log`. Первый вариант пробы без `.finalMessage`
получил только timeout и не считается доказательством этого отказа.

Поправка ограничена `bytes.isEmpty && (complete || error != nil)`:
закрыть соединение и закончить callback. Непустые неполные/неверные HTTP
по-прежнему дают XCTFail; ограничение размера и неожиданные маршруты остаются.
HTTP-счётчики и ожидания реальных запросов не ослаблены, пустое соединение
завершается до создания WebView. Дополнительного класса или внешней зависимости
нет. Исправление согласуется с уже существующим поведением history fixture.
После него снова прошли все 86 cabinet checks и полный локальный набор.
Первый общий отказ сохранён, его история не заменена последующим PASS.

## Проверенные результаты и границы

Журналы находятся в отдельном каталоге
`/Users/yshishenya/Documents/Codex/2026-10-21/f136-review-fix/`.
Названия ниже однозначно определяют прочитанный журнал; контрольные суммы
приведены далее. Проверяющий сам выполнял только чтение, SHA256,
`check-prerequisites` и `git diff --check`.

| Журнал | Проверенный результат |
|---|---|
| `provisional-red.log` | 3 tests,3 FAIL,0 unexpected: cancellation,503,network failure — прежний GET терял canReload; старый runtime с первой версией регрессий |
| `provisional-green.log` | 3 tests,0 FAIL после runtime fix |
| `session-matrix.log` | 12 tests,11 unexpected FAIL: лишнее unwaited expectation в невыбранных ветках helper; committed scenario прошёл. Это ошибка теста, не продуктовый RED |
| `session-matrix-final.log` | 12 tests,0 FAIL после создания expectation только в committed branch |
| `cabinet-final.log` | 23 RoutePolicy +63 Workspace =86 tests,0 FAIL |
| `macos-full.log` | 1248 tests,9 SKIP,1 FAIL из синтетического HTTP-сервера; общий PASS не заявляется |
| `unused-connection-red.log` | 1 FAIL по timeout ранней некорректной пробы; не используется как RED причины |
| `unused-connection-red-final.log` | 1 test,1 FAIL с точным `Incomplete synthetic session request` при настоящем EOF пустого TCP |
| `cabinet-fixture-final.log` | На окончательном тестовом файле:23 RoutePolicy +63 Workspace =86 tests,0 FAIL |
| `macos-full-final.log` | 1248 выбранных,1239 PASS,9 SKIP,0 FAIL; ранее затронутый F277 test прошёл |
| `governance.log` | `spec-kit-governance: OK (bootstrap integrity + GRAF invariants)` |

Пересекающиеся проверки не суммируются. Ранний продуктовый RED относится к
старому runtime и более ранней версии теста; он не выдаётся за запуск финальных
bytes теста на старом коде. Общий повтор — локальная диагностика по quickstart,
не авторитетный GitHub `release-full` и не подтверждение полной доступности.

В итоговом общем запуске7 пропусков относятся к независимой проверке фокуса
обычного AppKit-окна перед тестами уведомлений, ещё2 — к ненастроенным каталогам
экспорта тестовых изображений. Они не считаются PASS, не подтверждают ручную
приёмку GRAF Dev и не отменяют соответствующие открытые границы. В 86 проверках
кабинета пропусков нет. Ни один тест/порог ради зелёного результата не удалён.

## Повторная сверка всех пунктов checklist

Отметки означают качество требований. Пункты повторно сопоставлены с текущими
документами; подробная поштучная таблица остаётся в предварительном отчёте.

| Пункты | Текущее основание | Итог |
|---|---|---|
| requirements Content Quality1–4 | Spec сохраняет пользовательский результат,3 US и все обязательные разделы; алгоритм находится в plan | 4/0 |
| requirements Completeness1–4 | Clarifications19.10, FR-001–009, SC-001–004 и plan21.10 дают однозначную измеримую границу старого GET/нового POST | 4/0 |
| requirements Completeness5–8 | US/Edge Cases/Assumptions, текущая приёмка, quickstart и открытые T004/T011/T012/T016/T017 задают сценарии, исключения и зависимости | 4/0 |
| requirements Readiness1–4 | US/FR/SC согласованы; технические детали не подменяют критерии; полное выполнение продукта не заявлено | 4/0 |
| auth-navigation CHK001–004 | Key Entities/data-model/FR-004/Assumptions различают документ, действие, способы входа, сессию и серверную границу | 4/0 |
| auth-navigation CHK005–008 | FR-001–007/US2/уточнение19.10 и plan21.10 запрещают повтор, сохраняют полезную историю и правильный момент boundary | 4/0 |
| auth-navigation CHK009–013 | US/SC/Edge Cases/FR-007–009 определяют способы входа, кнопки, ошибки, безопасность доказательств и доступные названия | 5/0 |
| auth-navigation CHK014–015 | Assumptions/FR-007/quickstart определяют существующие маршруты, тестовые данные и отсутствие секретов | 2/0 |
| auth-navigation CHK016–019 | Clarifications/текущая приёмка/plan/tasks/quickstart отделяют срез, success/error/cancel, stale identity и виды доказательств | 4/0 |
| auth-navigation CHK020 | Root-only predicate в spec/data-model/research/T018 сохраняется | 1/0 |

Требования не изменялись, отметки 36 пунктов сохранены. Неподтверждённых
пунктов качества требований нет; неисполненные OAuth/manual/hosted gates
не превращены в выполненные checklist-тесты.

## Что остаётся перед принятием среза

Исполнитель оформляет validation/converge и новый точный коммит. Затем нужны
`governance-fast`, `macos-pr`, `pr-metadata` на том же PR SHA и проверенной
основе через `scripts/validate-pr-checks.py`. Старый hosted nil-unwrap/blocker
не снимается одним локальным PASS: итог нового hosted run обязателен.
Итоговое состояние GitHub, слияние и закрытие task issues проверяет владелец
основной задачи. Вся F136 не завершена: T004/T011/T012/T016/T017 открыты.
Выпуск, установка, production и любые живые аккаунты этим ревью не затронуты.

Legacy Impact: `untouched`. Исправляется существующий lifecycle; новых путей
совместимости, fallback, flags, aliases, зависимостей или исключений нет.
Тестовый delegate probe наблюдает текущий публичный WebKit API и не является
производственным запасным механизмом.

## Проверенные контрольные суммы

Пути относительно корня репозитория; документы полностью прочитаны, а их
контрольные суммы сверены после чтения. HEAD runtime до исправления:
`dca71fb3eaf1fd9609daca1adec01691c8f9d9e62d48887c4d8203189c2a3dfa`.

```text
4bdbcd97dbb86b560cc5cf5294684d7adfbe85a1a39716765145072aa840ae77  AGENTS.md
2f3e0339a89d3ccdf0878026920955a189584d6a985116b069584cd78b3c75bb  docs/agent-guidance/README.md
5263860b1974df022826ac81c2482e6ee92100bc0bb718ab5a29b32e2422e411  docs/agent-guidance/document-reading.md
d7d8c9cce8315c17efaa1da05ece80c2542ca01b966f81fb848580104b785e1d  docs/agent-guidance/codex-worktrees.md
afb816ce48624eb79fcd7fd44d09f0986296e87ef1cfecd790228ac70a5b9b9e  docs/agent-guidance/spec-kit-flow.md
9f7072c879490d250053cb7397ad6b9b68fdcde17bdf9367ed874a41e450b5f5  docs/agent-guidance/product-gates.md
1037b91f153f0757fff372e26cd05dd31433158c9c35d149125197a8a523f20d  docs/agent-guidance/development-process.md
ff0d996c95101d5f782259661131db1b7528b3bf58991603f5652092e1e5256f  docs/agent-guidance/release-and-validation.md
7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8  .specify/memory/constitution.md
0f3ccfcfa60062bb0aae6802eeb0012056a635a30cb9f46f54d1992d0b4f57c2  docs/prd-voice-layer-final.md
25b7f383be47c7160da8e852006ff82019f30a5f9c371fc30baa79238649cd16  docs/current-product-status.md
6810346229072b50319c981607a0fb2a3164105075a4024a624f0e4b7bcd2668  specs/136-auth-navigation-recovery/spec.md
bd8150f49cb8e47e7447dd368e5224f48c7340bdc4da1b91c8120fb88f9e1aa9  specs/136-auth-navigation-recovery/plan.md
9ba79f73f97d815d47f6a03566c4267d239cbc28059cae59e3639b3549f13149  specs/136-auth-navigation-recovery/tasks.md
5494a84d795102bf03f616b12d6f1dbe8acc905a5f5214a53ddb87fbef87c6b2  specs/136-auth-navigation-recovery/research.md
ea2683c1e7838b9d154508fac52f37e2b9f5098b4a443f3f793e164c257136ac  specs/136-auth-navigation-recovery/data-model.md
880984fc8177b0baa3868db9ef77570c857c649e5d50fb292049a2987b36f144  specs/136-auth-navigation-recovery/quickstart.md
fd3a209a57af6057c618d8667b64e62c97bf485db958d69f2665518a4929726f  specs/136-auth-navigation-recovery/contracts/cabinet-navigation-lifecycle.md
8dd084e32763ac4d16df6ea6ff76a8114c959e642b0c66fbe83b12331b285078  apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetWebView.swift
0f4bdc8c5542f270aa39d57a36df24f251c20e3f089b58b48d37fe91e15dfd7e  apps/macos/Shared/Tests/DesktopCabinetWorkspaceTests.swift
```

SHA256 прочитанных журналов в каталоге выше:

```text
9c1b8f7c1acd21c3a5017f14f83348be5145af63656f02f3b9cec7c775333c82  provisional-red.log
5c4e3040bb13107832336d1af4e6de277701b2c3558563e4a76e344986878396  provisional-green.log
f43b7713b0640a45d700e9b23367714f5e265994f1c0561be3063cb6de1c063b  session-matrix.log
b080437bcece41360ffdbcd1e877927cd535864d7a1f056c340c9e1a762e17dc  session-matrix-final.log
0f340ef095adc9837f40871be36a852db460dc6bcf4e292b60a9b2a60e81d2a7  cabinet-final.log
e3cba5d534d6a2a426d8e995b0a05f22ec4a96631c0d80b236084e2ad3cd1823  macos-full.log
2513159f29765944ae8cf5f49e29dee1c687d570288113d8a22be30f9c6a290b  unused-connection-red.log
a4cc644b2555d9ae4420d25d5c97eaf4e383d154740e675bf4192cd5c3db39cc  unused-connection-red-final.log
325e58b7ec3968a08ee8502e1e00a42fb9719edcd03714d079d753df60d06a3c  cabinet-fixture-final.log
c3167a587a7dcf3d948566710cd8176c390bfa5cee873b214e54a6ac60316fc1  macos-full-final.log
59cfeb588ee423427af9f09c0dfe4d3d2b36bbfcca7bbb8b49ba0f0b1ce6bceb  governance.log
```

Изменены только этот отчёт и примечания двух назначенных checklist.
Оба checklist после примечаний перечитаны и пересчитаны; существующие отметки
сохранены. `git diff --check` прошёл. Код/spec/plan/tasks, Git/GitHub,
приложение, данные, коммиты, выпуск и развёртывание проверяющий не менял.
