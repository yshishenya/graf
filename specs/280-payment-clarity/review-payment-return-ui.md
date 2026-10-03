# F280 — независимая проверка интерфейса возвращения

Дата: 2026-10-03. Проверяющий владеет только этим отчетом; implementation/spec/plan/tasks/checklist/GitHub не изменялись. Это предварительный read-only обзор draft `/tmp/graf-f280-status-controller.js`, а не финальный допуск рабочего кода. Template/JS еще не встроены; billing.py находится в изменении root.

## Findings draft

### UI-R1 — HIGH: смена session перезапускает автоматическую проверку

Evidence: draft строки48–56,66–76. `initBillingStatusRefresh` при другом key останавливает прежний ledger, но затем создает новый с attempts0/startednow/stoppedfalse. Key включает session через `billingRenewalPreferenceKey`, следовательно при изменении session в том же документе у того же user/workspace/invoice создается новая60с последовательность. FR-034/CHK009 требуют остановки без reset/restart при смене session; сравнение incoming/current в beforeSwap не устраняет этот путь инициализации в idle состоянии.

Reproduction by code path: pending page имеет ledger scope-sessionA+invoice с несколькими попытками; текущая meta session меняется наsessionB, тот же status page инициализируется → old stoppedtrue → new ledger attempts0 → timer вызывает POST. Требуется сохранить остановку для прежнего document/контекста после session change и предложить safe local GET, не новый auto ledger; отдельный платеж/полная новая навигация могут иметь собственный допустимый цикл. Добавить настоящий browser session-change reinit test.

### UI-R2 — MEDIUM: подавление повторного aria-live не попадает в HTMX response

Evidence: draft строки128–142. DOMParser создаёт отдельный response document; setAttribute aria-live=off меняет только `incoming` из этого parsed document. `event.detail.serverResponse` остается исходной строкой, а HTMX выполняет swap из неё; в замененном DOM role=status сохраняется прежняя live semantics. Каждая неизменная pending проверка может повторно объявлять тот же текст, вопреки FR-036. Требуется изменить actual swapped content/actual incoming DOM через поддерживаемый HTMX hook либо обновить serverResponse после проверки, либо после вставки отключить именно тот новый status node до live announcement (последний вариант требует browser/a11y доказательства). Не подавлять переход pending→paid.

## Предварительно подтвержденные свойства

6/60/10 ограничены beforeRequest и ledger; oneflight, duplicate/reinit guards и old-key ledger сохранены; controls блокируются на запрос; incoming main единственный/current target+invoice/session scope проверены; late/detached/non200/hidden/error отвергаются. Timeout/error блокирует ledger/manual POST и показывает local GET recovery, не считает abort остановкой серверной activity. Manual checks после успешной exhausted последовательности допустимы, последовательны и rate-protected сервером. GET purity/API-only-server лежат в server contract и требуют actual code review.

15с timeout зависит от будущего template hx-request, его еще нельзя подтвердить draft controller. Lifecycle departure/reset не окончательно подтвержден без интеграционных hooks. Focus restoration требует реальных браузеров: автоматический ответ с focused heading безid уходит наmain, важно подтвердить отсутствие лишнего скачка фокуса/повторной озвучки.

## Gate

Draft HOLD: open HIGH1 / MEDIUM1. Root должен исправить два конкретных пути, после сигнала final code повторно сравнивается actual template/server/controller и browser evidence. Код/тесты этим обзором не выполнялись; реальные деньги/grant/выпуск им не подтверждаются.


## Повторный обзор встроенного кода

Текущее чтение actual `billing.py`, `billing_operation_status_content.html`, `cabinet.js` после сигнала root. Ранее UI-R1 закрыт: `billingStatusContextStopped` становится true при смене/потере ключа, новая ledger сразу stopped/blocked и не отправляет новую automatic sequence. UI-R2 исходный дефект закрыт: измененный DOMParser content теперь сериализуется в actual `event.detail.serverResponse`.

### UI-R3 — MEDIUM: ошибка провайдера не озвучивается при неизменном operation_state

Actual `cabinet.js` строки2090–2093 выключает aria-live, сравнивая только `data-billing-state` (operation.state). Actual template `data-billing-state` не содержит `status_result`/check_error. При pending→POST refresh provider_unavailable→GET pending оба operation_state одинаковы, хотя возвращенный notice меняется на ошибку, `data-billing-status-error=true` и controller прекращает проверку. В таком ответе главный role=status получает aria-live=off; error notice внутри него не имеет role=alert, recovery только показывается, data-billing-status-message остается hidden. Новый результат/ошибка связи не озвучивается.

Требуется подавлять только действительно неизменное пользовательское состояние: учитывать check_error/status_result/needs_service_review либо сравнивать нормализованный итоговый текст status region; при переходе к provider_unavailable/unavailable оставить новое объявление. Добавить pending→provider_error browser assertion actual swapped aria-live/status/alert и не сломать unchanged pending suppression. Это новый дефект конкретизации подавления, не прежний потерянный DOMParser update.

### Подтверждения actual source

- Template содержит hx-request timeout15000, native action/method/CSRF, HX POST/select main/outerHTML/sync drop/push false.
- Controller вставлен в общий initializer, одна document ledger,6/60/10/15, late/detached/scope/current-target guards, error/timeout stop, safe local GET recovery без нового POST.
- Status projection проверяет invoice succeeded и связанный grant для initial/renewal/early; storage grant отдельно; срок подписочного purchase выводится из grant, текущая active subscription не требуется. Missing grant дает service-review. Terminal continue запрещен сервером, actor/tenant/CSRF/rate защиты прежние.
- Success не выводится из return/query; GET provider mutation не добавлена. «К встречам», период и paid исключают continue; pending refresh главнее secondary continue.

### Неподтвержденные границы

Root сообщает186 focused PASS и2 устаревших fixtures FAIL, которые исправлены; здесь suite не запускалась и окончательный rerun не наблюдался. Browser success1POST достиг paid, но initial user-time document reload расследуется tests owner; отсутствие document navigation нельзя объявить подтвержденным. Focus/VoiceOver, полный Chromium/WebKit320/1280/темы/200% и множество timeout/hidden/detached/context cases также требуют текущего browser evidence. Роль maintenance/настоящий grant/выпуск не подтверждаются этим UI-only чтением.

Gate текущего source review: открытых HIGH0; применимый MEDIUM1 (UI-R3). После исправления и browser evidence требуется повторное чтение. Предыдущий draft HOLD сохраняется как история, а не итог актуальных R1/R2.


## Итоговый source review и граница выкладки

UI-R3 закрыт actual code: controller сравнивает normalized current/incoming status text, только одинаковый текст получает aria-live=off; `event.detail.serverResponse` переписывается. Новый provider error текст отличается и остается live. UI-R1/R2/R3 по чтению текущего code закрыты, новых применимых UI critical/high/medium не найдено.

Независимо прочитаны `billing/database.py`, `workflows/maintenance_worker.py` и activity guard в `worker.py`: actual session_user/current_user обязаны быть maintenance, row_security on, rolsuper/rolbypassrls false, rec_maintenance_allowed и точные operation/feature GUC true. Startup/reconnect проверяются до poller, activity — до сверки; guard не доверяет URL. В processing registry reconciliation workflow/activity/queue удалены, renewal не переносится. Один maintenance poller на existing queue; нормальный ранний выход poller становится исключением; reconnect finally отменяет/дожидается старых loops/poller и закрывает client до нового. Engine identity check и activity engine dispose в finally. После commit validated tenant GUC восстанавливаются существующим Session.after_begin hook; права/RLS не расширены.

Прочитаны существующие unit/reconnect/role/replay tests и реальные журналы: `/tmp/graf-f280-payment-worker-unit-final-green.log`25PASS, `/tmp/graf-f280-payment-worker-postgres-final-green.log`19PASS, `/tmp/graf-f280-payment-root-regression.log`389PASS. Тесты повторно не запускал. Настоящий maintenance-role тест воспроизводит delayed webhook, invoice success/personal access и replay без второго grant/payment; app role test требует fail до provider call/пустого успеха. Эти synthetic payment tests не являются живым восстановлением настоящего счета.

### UI-R4 — HIGH release gate: старый processing poller может конкурировать при выкладке

На момент независимого чтения `infra/scripts/cd-remote-runtime.sh` после `capture_processing_runtime_baseline` ставит runtime_mutated1, останавливает только rec-api, затем Compose up одновременно перечисляет rec-processing-worker и rec-maintenance без гарантированного завершения старого processing consumer. Старый processing image еще исполняет reconciliation activity с app role без нового guard. Пока новый maintenance poller уже запущен, старый может забрать задание той же existing queue и подтвердить completed0, повторяя обнаруженную причину. Проверка candidate image после up не доказывает отсутствие промежуточной конкуренции.

Минимальный precise fix: после capture_processing_runtime_baseline и до runtime_up выполнить один fail-closed Compose stop `rec-api rec-processing-worker rec-maintenance`; не ставить `|| true`. Capture baseline обязан оставаться до остановки. Затем существующий up запускает candidate services, role/image/readiness gates сохраняются. Root должен добавить узкую regression порядка baseline→stop всех3→up/verify и наблюдение единственного consumer после выпуска. Ошибка stop должна перейти к существующему rollback/failure пути, не продолжать start нового poller. Сохранение durable Temporal queue и idempotent activities позволяет повторное исполнение прерванной работы; новая очередь/миграция/processing elevated role не нужны.

Влияние на требования: это исполнение уже допущенного FR-038 «единственный maintenance consumer, app processing без reconciliation», T032 runtime/release, high-risk-product/release-deploy. Не новый продуктовый scope/номер фичи. Документировать реальный quiesce порядок в release evidence; reviewer-owned требования markers этим обзором не менялись. Реализация безопасного stop/root spec update не входит в права этого проверяющего.

Current gate: UI/backend-worker source review PASS с0 применимых открытых замечаний; release HOLD по UI-R4 до исправления и точной проверки. Browser no-document-navigation/focus/full matrix и живой invoice/grant runtime остаются неподтвержденными до самостоятельного evidence. Code/source PASS не равен разрешению публикации или банковской приемке.


## Повторная проверка передачи очереди и отката — T033

Actual forward diff: после capture_processing_runtime_baseline/runtime_mutated1 выполняется strict `compose stop rec-api rec-processing-worker rec-maintenance`, без `|| true`; только затем runtime_up. `set -euo pipefail` и EXIT rollback trap включены. В baseline читаются прежние container IDs/restart counters до остановки; image verify/role/readiness gates остаются после up. Причинный тест `tests/integration/test_deployment_readiness_gates.py::test_remote_deploy_stops_previous_reconciliation_consumers_before_runtime_up` проверяет порядок/strict stop/trap presence; весь файл53PASS в `/tmp/graf-f280-rollout-green.log`. Это static regression, а не исполненный отказ Docker в production.

UI-R4 forward rollout закрыт: старый processing reconciliation consumer остановлен до нового maintenance poller; T033 отражает convergence и issue7478. Checklist актуальный17/0, исторические задачи не переоценивались. Runtime/production этими проверками не изменялись.

### UI-R5 — HIGH release recovery: rollback compatibility branch может вновь запустить consumer без quiesce processing

Actual failure path: если strict forward stop завершится частично/ошибкой, runtime_mutated1 вызывает rollback_on_exit → restore_previous_runtime. Эта функция сейчас останавливает media/maintenance/api/prompt, но **не rec-processing-worker**, и игнорирует stop failure через `|| true`. Для одинакового schema (текущий billing change без миграций) она запускает `restore_compatibility_runtime`, который поднимает candidate processing/API/maintenance параллельным Compose up. Оставшийся прежний app-role processing poller может конкурировать с новым candidate maintenance poller до завершения recreate processing — тот же подтвержденный механизм completed0 возвращается в recovery ветке. Forward fail-closed исправление само по себе не закрывает этот reachable fallback.

Precise minimal recovery fix: перед любой веткой restore_previous_runtime, которая запускает прежние/candidate consumers, подтвердить остановку `rec-processing-worker rec-maintenance`; при failure не выполнять restore_compatibility_runtime/consumer up, объявить rollback blocked/forward_fix_required и вернуть failure. Это может быть строгий targeted stop barrier внутри restore_previous_runtime с проверяемым return; существующий best-effort media/API/prompt cleanup сохраняется. Не просто добавить processing в старый stop с `|| true`, поскольку тогда ошибку по-прежнему можно проигнорировать. Regression должна моделировать/source-assert failure barrier до compatibility/previous up и отсутствие нового start при stop error. Хранить baseline/queue/history/image records, не менять RLS/роль processing.

Current source gate: UI/worker PASS; forward R4 закрыт; release HOLD по reachable rollback UI-R5. Browser/live gates сохраняются отдельно. Report writer не менял production/spec/tasks/checklist/GitHub.


## Финальная независимая проверка UI-R5 и T033

UI-R5 закрыт: в самом начале actual `restore_previous_runtime` strict conditional stop `rec-processing-worker rec-maintenance` выполняется до media inspect/cleanup и до любой schema/compatibility/previous restore branch. Stop failure сообщает rollback blocked/forward_fix_required и возвращает1; никакой consumer up из этой функции не выполняется. Outer rollback_on_exit сохраняет исходный nonzero exit, recovery verification не объявляется successful. При stop0 сохраняются прежние compatibility/previous images paths. Дополнительный best-effort media/API/prompt cleanup после подтвержденной остановки consumers не открывает найденную гонку.

Причинные execution tests перечитаны независимо: Bash исполняет реальный forward fragment baseline→runtime_mutated→strict stop→runtime_up с compose/env заглушками; stop23 заканчивается EXIT23 и trace без up, stop0 достигает up. Реальная функция restore_previous_runtime исполняется с controlled runtime services: stop23 дает единственный trace stop и blocked/forward-fix, stop0 достигает compatibility branch. Scoped env stub убирает только synthetic inline env assignments в forward harness, production script не модифицирует. Это сильнее прежнего string-only order теста; external Docker/production rollback им не проверены.

`/tmp/graf-f280-rollout-green.log` перечитан:56PASS,2known warnings. Независимый `bash -n infra/scripts/cd-remote-runtime.sh` завершился0. Исторические RED1 forward/RED2 recovery получены root и не пересоздавались; final execution test body соответствует обоим причинным дефектам. Требование FR-038 единственного maintenance consumer покрыто T030 runtime registration/guard и T033 forward/recovery handoff; T033→T032 dependency и issue7478 присутствуют в tasks. Reviewer-owned requirements checklist перечитан:17checked/0unchecked, markers не менялись. Исторические task prefix/issue states этим обзором не редактировались.

Source bindings этого final review:

- cd-remote-runtime.sh SHA256 `48428a85cb326de2f6a1ebb48992eff554978ab93a997693e47a66c81519b57c`
- test_deployment_readiness_gates.py SHA256 `04e8803b652cab8c3e1187f0dc41ba7342638db249e578a48901115520f612e1`
- rollout GREEN log SHA256 `4538126921566c2823b3cde098cba419ae1746ef26f6a867fd429568c336521d`

Итог независимого source/rollout-review: UI-R1–R5 закрыты; применимых открытых critical/high/medium0. Новых замечаний не найдено. Release source gate PASS для рассмотренных UI/worker/queue-handoff исходников. Browser matrix/focus/navigation, exact-SHA CI/Full/CD и live actual invoice/grant/publication остаются отдельными pending доказательствами; этот PASS не утверждает production изменение, банк, recurring либо полный финансовый closeout. Production code/spec/tasks/checklist/GitHub/git не менялись.


## Актуальное покрытие FR-031–038 / SC-013 / T029–T033

Повторно прочитаны current spec/plan/tasks/server/template/controller, unit/real-DB/browser harness. Browser owner еще завершает матрицу; текущая таблица различает source coverage и завершенную приемку.

| Требование | Implementation / tasks | Независимый вывод |
|---|---|---|
| FR-031 | billing.py invoice+operation+linked subscription grant/period; storage grant; template paid/service-review; T029,T031,T032 | Source covered; исторический grant и missing grant имеют server tests в test_billing_clarity.py. Истекшая текущая подписка не условие успеха |
| FR-032 | Refresh выше secondary continue, pending/unknown/canceled/error; stale continue terminal invoice guard; T029 | Source covered, error текст/announcement R3 исправлен. Legacy pre-provider recovery имеет native continuation отдельно |
| FR-033 | document ledger6/60/10, hx timeout15с, oneflight/init/lifecycle guards; T029 | Source covered, clocked browser matrix еще pending |
| FR-034 | непустые current/incoming user/workspace/session/invoice, detached guards, global context stop; T029 | Scope/late covered, timeout recovery reentry имеет UI-R6 ниже |
| FR-035 | existing protected POST owner/tenant/CSRF/rate, GET pure, terminal continue guards; T029,T030,T032 | Source covered, new financial create call в UI/worker не добавлен |
| FR-036 | Native form/JS-off, role status/error, focus, themes/reflow; T029,T031 | Source covered частично; фактическая browser/a11y матрица и focus pending |
| FR-037 | Real browser→ASGI→PostgreSQL harness + negative create/grant assertions; independent reviews/live closeout; T029–T032 | Harness реальный, final browser evidence и independent final converge/CI/release/live еще pending |
| FR-038 | maintenance poller + actual role guard, RLS/replay tests; forward/recovery strict stop; T030,T033,T032 | Worker/source+25unit/19DB+56rollout evidence покрыты; actual released queue/grant pending |
| SC-013 | success/pending/canceled/service-gap/errors/context/late/native matrices; T029–T033 | Критерий не объявлен выполненным без final both-engine proof и закрытия UI-R6 |

T031 review/convergence и T032 CI/Full/CD/live обязательно еще предъявить как отдельное evidence; отсутствие завершенного выпуска не дефект source architecture и не основание закрывать задачи. T033 покрывает причинный handoff и actual stop-failure execution tests, issue7478. Historical T011/T012/F278 не приписаны этим тестам.

### UI-R6 — HIGH: recovery GET после browser timeout запускает новый automatic POST

Current actual template recovery anchor href — обычный `/billing/checkout/status/<invoice>` без признака read-only recovery. После 15с timeout controller блокирует только текущую document ledger; сам серверный запрос может продолжаться20с. При нажатии «Обновить результат» браузер получает новый документ, Map/ledger сбрасываются; pending GET снова рендерит data-billing-auto-check=true, initializer отправляет немедленный POST. Следовательно, чтение local status переходит в новую авто-сверку и может пересечься с еще исполняемым прежним server request. FR-034/plan/quickstart/T029 обещают safe local GET без overlapping/restarted POST; current browser timeout scenario уже правильно требует отсутствие такого POST после recovery click.

Precise fix: recovery GET должен явно рендерить безопасный режим без auto-check (не финансовый authority), либо выполняться на месте с сохранением blocked/stopped ledger; результат local read не должен сам запускать новую POST sequence. Условия ручного дальнейшего восстановления должны оставаться явными и protected, query/UI flag не подтверждает оплату/доступ. Обычный первоначальный return GET продолжает automatic sequence. Добавить actual timeout→recovery-click case и подтвердить неизменное число refresh POST.

Этот defect установлен по current code path, не объявляется результатом еще незавершенной browser матрицы. Root/browser owner должен сверить его с текущим final run. Source UI/worker/rollout прежние R1–R5 закрыты; общий coverage/source gate HOLD до устранения UI-R6 и итогового browser evidence. Reviewer пишет только этот отчет.


## Независимая проверка исправления UI-R6 — 2026-10-03

UI-R6 закрыт на уровне текущего исходного кода и серверного теста. Recovery anchor ведет на `/billing/checkout/status/<invoice>?view=local`; сервер передает `read_only_recovery=true` и принудительно исключает `can_continue_payment` для этого режима, включая legacy pre-provider путь. Template исключает automatic checking через `auto_check ... and not read_only_recovery`, pending primary action становится тем же local GET, refresh form не рендерится. Таким образом новый документ после timeout не имеет ни автоматического POST, ни refresh/continue форм в payment main; потенциально продолжающийся прежний серверный запрос не запускается повторно этим восстановлением.

Query `view=local` меняет только поведение отображения. GET handler по-прежнему читает workspace-scoped subscription/invoice/operation/grants, проверяет billing role и не вызывает YooKassa/финансовую мутацию. Invoice+operation+grant projection успешной оплаты не зависит от query: уже подтвержденное состояние покажет «Оплачено», оплаченный срок из grant и «К встречам»; pending query не может подтвердить оплату. Обычный первоначальный GET сохраняет автоматическую сверку.

Независимо прочитан `/tmp/graf-f280-local-recovery-targeted-green.log`: `test_local_status_recovery_never_restarts_payment_check` — 1 passed, 38 deselected, isolated PostgreSQL cleanup confirmed. Actual test проверяет обычный auto=true, recovery auto=false, отсутствие refresh form и любого POST в payment main, local href, отсутствие ложного «Оплачено» и сохранение 1invoice/1operation. Проверка ограничена payment main корректно: account preference forms вне него не относятся к восстановлению платежа. Предыдущий combined run с ошибкой широкого assertion не считается зеленым результатом всей выборки.

Actual browser timeout scenario дополнительно проверяет 15с error/disabled button, остановку последующих POST и неизменное число refresh POST после recovery click + нового document load. Исходник этого assertion прочитан; окончательный результат его исполнения в Chromium/WebKit ещё не предъявлен. Текущие browser logs неполные, содержат failures, поэтому они не дают PASS и должны быть разобраны владельцем браузерной матрицы.

Итог этого повторного обзора: UI-R1–R6 закрыты на уровне рассмотренных исходников; открытых critical/high/medium findings по source 0. Source gate PASS, FR-034 recovery покрыт. SC-013/full browser convergence, T031 final independent review, T032 exact-SHA CI/Full/CD/release/live остаются pending. Этот обзор не утверждает, что исправление выпущено, что реальный invoice/grant восстановлен, или что проверены банковское зачисление/возврат/автосписание. Reviewer изменил только данный отчет; code/spec/plan/tasks/checklists/GitHub/git/production не изменялись.


## Последняя независимая source оценка перед T031 — 2026-10-03

Перечитано узкое изменение template: secondary «Вернуться к оплате» теперь допускает `status_result in ["unchanged", "refreshed"]` при неизменном серверном `can_continue_payment`. Это соответствует фактическому `_status_refresh_result`: обработанный подтвержденный pending ответ возвращает `refreshed`, даже если provider по-прежнему pending; прежнее условие только `unchanged` могло скрывать допустимое вторичное действие после успешной сверки. Основным остается «Проверить оплату». Ошибка провайдера/недоступность не входят в допустимые result; readonly branch находится выше и can_continue принудительно выключен сервером; terminal invoice/operation и service-gap не получают эту форму. Query result не дает полномочия: POST continue повторно проверяет роль, tenant, CSRF, rate, pending invoice/operation, actor и разрешенный адрес существующего provider payment. Повторный платеж из этого узкого изменения не создается.

Requirements/task coverage перечитано: FR-032 требует вторичное продолжение только совместимого незавершенного платежа, FR-035 сохраняет серверное authority/защиту terminal continue; оба покрыты T029 и независимым T031. FR-031 success/grant, FR-033/034 bounded controller/local recovery, FR-036 native/accessibility, FR-037 browser evidence и FR-038 maintenance role/lifecycle/handoff имеют прежнее покрытие T029/T030/T033 с release/live в T032. Узкое исправление не меняет scope и не требует нового несвязанного task; historical T001–T028 и reviewer-owned checklist markers не менялись.

Независимо прочитаны окончательные доступные журналы: `/tmp/graf-f280-payment-browser-webkit-final.log` — 28 passed; `/tmp/graf-f280-payment-browser-chromium-final.log` — 27 passed, 1 failed pending-320 при page.goto timeout5000ms (это не successful full Chromium run); `/tmp/graf-f280-pending-continuation-chromium-green.log` — pending320/1280, 2 passed; `/tmp/graf-f280-pending-continuation-webkit-green.log` — pending320/1280, 2 passed. Последние целевые прогоны после узкого исправления подтверждают наличие вторичного действия и bounded6/60/10 behavior для обеих ширин/движков. `/tmp/graf-f280-pending-continuation-contract.log` — 53 passed. Timeout320/1280 входят в успешные результаты обоих окончательных matrix logs, следовательно UI-R6 теперь имеет и фактическое browser execution evidence; прежний browser pending в предыдущем разделе исторический. Новые браузерные прогоны этим reviewer не запускались.

Независимый итог source: PASS, UI-R1–R6 закрыты; открытых critical/high/исправимых medium0. Новых применимых source замечаний не найдено. Доступные browser evidence в совокупности покрывают все28 случаев в каждом движке с отдельным повтором pending после narrow template change; единый full Chromium run не объявлен зеленым. Этот отчет является одним независимым входом для T031/converge, а не утверждением о завершении всех трех обзоров либо T032. Exact-SHA CI/Full/CD/production и штатное согласование уже оплаченного реального invoice/operation/grant остаются отдельными gates. Ни реальная банковская приемка, ни refund/recurring/human conversion этим обзором не закрыты. Изменен только owned report; code/spec/plan/tasks/checklist/GitHub/git/production не менялись.


## Финальная сверка wording и reviewer-owned gate — 2026-10-03

Перечитаны FR-031 в `spec.md` и строка «Деньги подтверждены, доступ еще не применен» в `contracts/payment-journey.md`: оба теперь используют «Оплата получена. Проверяем доступ», как actual template/tests. Уточнение допустимо: не обещает автоматического подключения в ситуации service-review/help, сохраняет запрет ложного активного тарифа и новой оплаты. Условие «Оплачено» остается прежним: авторитетный invoice/operation success и связанный результат предоставления услуги/grant; действительный срок из grant, historical paid не зависит от текущей подписки. Финансовое требование не ослаблено.

Reviewer-owned `checklists/payment-return.md` полностью перечитан: checked17 / unchecked0, CHK001–CHK017; markers не менялись. PASS качества требований сохраняется после wording consistency. Это не маркировка реализации/выпуска/банковской приемки. Дополнительные post-fix pending прогоны уже независимо прочитаны: Chromium2PASS32.08с, WebKit2PASS35.97с. Последний independent source вывод сохраняется: PASS, source blockers0, открытых critical/high/исправимых medium0. Review-only writer изменил только этот отчет.
