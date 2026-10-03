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
