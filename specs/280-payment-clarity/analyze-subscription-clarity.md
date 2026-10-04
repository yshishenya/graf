# F280 — анализ согласованности управления подпиской

Дата: 2026-10-04. Scope: новые FR-039–045, SC-014, US4 и окончательные T046–T048; исторические части F280 учитываются только как действующие ограничения. Анализ прочитал spec/plan/tasks/contract/quickstart/research, constitution §II/III/VI/VII, product gates и независимый requirements PASS14/0. Prerequisite запуск выполнен с --json --require-tasks --include-tasks; --require-spec исключен, поскольку установленный скрипт этого флага не поддерживает. Spec и plan существуют и прочитаны.

## Findings

Критических, высоких, средних или низких замечаний в активном срезе не обнаружено. Нерешенных уточнений, конституционных конфликтов, дублированных task ID и непокрытых требований нет.

| Требование | Задачи | Покрытие |
|---|---|---|
| FR-039 | T046/T047/T048 | активная карточка, один primary GET, cycle, no-card без ложного отказа |
| FR-040 | T046/T047/T048 | видимые сумма/срок следующей попытки, прямая отмена, последствия |
| FR-041 | T046/T047/T048 | native disclosure, resume consent/version/quote/CSRF, точная дата, existing early/error |
| FR-042 | T046/T047/T048 | все виды pending invoice, unknown/keyexpired, правдивые notices, запрет конкурирующей оплаты |
| FR-043 | T046/T047/T048 | effective trial/free/expired/paid, неизвестные дата/сумма, права |
| FR-044 | T046/T047/T048 | минимальное чтение/представление, неизменные финансовые guards/API/DB/JS, no real financial actions |
| FR-045 | T046/T047/T048 | официальные исторические источники, GRAF assets/code, keyboard/themes/200%/NoJS |
| SC-014 | T046/T047/T048 | тот же synthetic baseline, >=50% поясняющих слов, RED/GREEN и три независимых обзора |

Порядок корректен: reviewer PASS → final tasks → analyze → issue sync/validate → RED → presentation → GREEN → reviews/converge/release. Все48 task IDs уникальны, новые3 имеют US4 и конкретные пути; указанные четыре existing test files существуют. Нет новых [P] со скрытой зависимостью.

Constitution: явные согласия и безопасность сохранены; §VII допускает утвержденную структуру Krisp при независимом коде/ресурсах и правдивых отклонениях; §VI процесс/гейты сохранены. Runtime/платежные API не расширяются. Перенос редких сведений не скрывает сумму/срок перед resume POST либо доступную cancel; GET checkout сам не списывает деньги. Новое чтение all-kind blocking invoice работает и без subscription; его локальный набор CHECKOUT_BLOCKING_STATES | {"provider_key_expired"} явно оставляет INITIAL_CHECKOUT_OBSERVATION_EXPIRED вне выборки. Shared monetary set и денежная транзакция не изменяются. Это уточнение существующего FR042, не новый финансовый переход. Разрешения commit/production сохраняются из пользовательского запроса; выпуск по новым SHA gates.

## Метрики и пределы

Требований8 (FR7 + buildable SC1); задач3; покрытие8/8=100%; ambiguity0; duplication0; CRITICAL0/HIGH0/MEDIUM0/LOW0; unmapped tasks0; вопросы0. Это анализ документов до кода, не результат тестов/измеренного сокращения/финансовой либо человеческой приемки. T011/T012/SC005/006/F278 остаются отдельными.

Привязка редакции SHA256:
- spec.md: 948c14f89d63059de5e91499c01b882b74a27167fdb6344515b93c090fd14a11
- plan.md: c2ca366c4373fe26e087eabf3c74a7010fdc60ce9427bd6900d98dd6d589723f
- tasks.md: 6e5eeb43153fc8f95e7aa08dac1123f930d70adaaa6ec44859704d53d3679d0a
- contracts/payment-journey.md: 60c7adefaec2720de6fe7e5b2855c78c3ff5cbcded0de158a5aae251d43ec800
Добавление только issue links не меняет семантику задач.

Next: canon ensure, all-state ownership dedup T046–T048, canonical issue sync и canon validate. RED разрешен только после этих gates.

## Дополнительная задача T049 после CI RED

T049/#7507 реализует существующие FR-039/041 и SC-014 в прежнем money-path тесте: short date в основных фактах, полный срок в native условиях. Входной RED179/1 явно сохранен; денежные assertions, продуктовый код, границы owner/tenant/provider и независимый reviewer gate неизменны. Новое требование, неоднозначность, миграция или новый consent не вводятся; повторное уточнение/checklist не требуется. Покрытие T049:2/2FR, конфликтов/новых critical/high/medium/low0. Зависимость: существующий reviewerPASS/analyze → canonensure/dedup/issuesync/validate → T049GREEN/независимыйreview → повторные exact-SHA gates → T048 выпуск.

T050 обнаружена перед full release при поиске старых subscription assertions: isolated RED1/81deselected, только требование удаленной повторяющейся фразы. Покрывает прежние FR-039/040/042 и сохранение sent-payment truth; новое требование, consent, правка продукта или неоднозначность отсутствуют. Scope: один assertion прежнего integration test, причинный GREEN/full82/независимыйreview и текущие gates. Конфликтов/новых analyze critical/high/medium/low0; карта3/3FR; требования/checklist ранее PASS сохраняются.

## T051 — анализ до синхронизации задачи

Подтвержденные внешние P2 требуют узкого уточнения FR042 и сохранения FR044: существующая политика CHECKOUT_BLOCKING_STATES без view-only expired расширения, method_required recovery одновременно с pending без необоснованного факта отправки. Spec/plan/contract/quickstart/T051 согласованы; покрытие2/2FR, новые API/DB/JS/денежные переходы0; blocker только независимый requirements refresh перед кодом. Исторические PASS прежних редакций не подтверждают уточненную редакцию. T051 закрывает оба P2; T048 остается выпуском. Неопределенности0/новых критических и высоких конфликтов0. Требуется синхронизация canonical issue и validate, затем RED/GREEN/browser/source review.

После независимого refresh T051 requirements PASS14/0 проверена окончательная редакция: название раскрытия обещает также историю; CHK007/008 согласованы. Analyze conflicts0; canonical issue7511 создан и validate300PASS. Причинный RED/implementation разрешен; выпуск HOLD до новой проверки.

## Итоговая согласованность T051

Текущие FR042/044 и T051 покрывают2/2 выявленных P2; новый source/DB/browser/UX evidence поддерживает существующие критерии. Дополнение invoice не меняет требований подписки: FR019/020 сохранены по прямому уточнению, width720 прежняя. Конфликтов/непокрытых обязательств T0510; exact-SHA CI и выпуск остаются T048.

## T057 после нового внешнего P2

FR042/044 уточняют уже требуемую финансовую правду для любых неоднозначных операций, не только method_required. T057 сохраняет нейтральное описание результата, can-complete и no-repeat-pay, prepared исключение и безопасные URL. Покрытие2/2FR; конфликтов, дублированных taskIDs и новых обязательных решений0. Реализация blocked до независимого checklist refresh14/0, canon sync и causal RED. Денежные query/handlers/политика прежние. Новый source требует новых exactSHA/base checks; прошлый71 PR PASS не становится доказательством T057.

T058 scoped analyze:2 внешних partial gaps в FR039/042/044/045,1buildabletask; новая денежная политика отсутствует. Неоднозначностей/противоречий/дублей/неохваченных новых требований0. Требования отрицательных/положительных состояний и safe recovery связаны сT058. Critical/high/fixablemedium в согласованности артефактов0; product gaps остаются HOLD до реализации и независимых обзоров.


Scoped T059 analyze2026-10-04:4refsFR050/052/SC016/017,1taskT059/issue7530, clarifyClear. Spec/plan/contract/quickstart задают одну permitted nonfinancial existingreceiptform с CSRF/permissionguards, отсутствие денежных форм, invoice copy и subscriptionlabel е-not-ё; task сохраняет реальные GET/POST иprivacy/authority. No duplicate requirement/newmoneyauthority, coverage4/4, missing/contradicts0, CRITICAL0/HIGH0/fixableMEDIUM0. Requirements checklist gate ещеpending, implementation трехcompatfix blockedдоindependentreviewerPASS; initialcontractsRED иinvoice/receipt74PASS сохраняются как текущие evidence, futurebrowser/CI/releaseнеобъявляютсяPASS.

T059 thirdcopy уточнение: subscriptionlabel1glyph+3exactbrowserselectors, без нового смысла/действия/deniedguards. Scope rootmechanicalcopy вpeerbranch явно согласован; те же4refs/1task, clarifyClear, CRITICAL/HIGH/fixableMEDIUM0. Требования reviewerrefreshpending, implementationblockedдоfinalPASS.


Scoped T060 analyze2026-10-04: два внешних P2 PR7532 связаны с FR049/052/SC016/017, одна новая задача,4/4refs covered. Root cause один общий support address, не дублировать sanitization по страницам; область всех пяти sibling presenters явно разрешена без auth/money решения. Budget300с только enclosing browser subprocess, не product таймер. ClarifyClear, duplicate/missing/conflict0, CRITICAL0/HIGH0/fixableMEDIUM0 в артефактах; два product/validation gaps остаются HOLD до independent requirements gate и RED/GREEN. Исторические PASS не становятся новым current CI.

T060 существующее исключение политики контакта: account_merge сохраняет более строгий запрет display-name (test_account_merge_contract.py:438); не ослаблять эту проверку. Normalized display-name принимается только там, где это уже допускает общий billing parser (history/status/referrals/fair_use). Shared CRLF/address/URI безопасность применяется везде; решения авторизации и прежний более строгий account_merge filter сохраняются. Это не новая конфигурация и не новый allow flag.

## Scoped analyze T061 до реализации

2026-10-04. Существующие FR049/052, SC017 и CHK006/010 требуют доступных по раскрытию пояснений возврата. В текущем шаблоне они безусловно есть, старый test opening `billing-coupon` имеет0совпадений против native `settings-disclosure`. T061 покрывает единственный обнаруженный test-only gap; task и quickstart требуют сохранения всех прежних закрытых/раскрытых assertions, без изменения runtime. Связь FR049/052→T061→полный touchedfile→source review→новые exactSHA/base/full/release явная. CRITICAL0/HIGH0/исправимыхMEDIUM0; новых продуктовых требований, денежных разрешений и acceptance waiver нет. Независимый reviewer-owned checklist остается отдельным допуском до кода.
