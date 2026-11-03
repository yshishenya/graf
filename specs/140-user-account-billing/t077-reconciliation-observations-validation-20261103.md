# F140 / T077 / O16: проверка постоянных наблюдений reconciliation

Дата: 03.11.2026. Полоса: `active Spec Kit slice / high-risk-product`.
Основа реализации: `eab30ac17aa676e25fd367735cbdb39a48eaf40c`.
Это проверка первого шага J1–J4 и агрегатов, не закрытие T077/#4932.
Точный source SHA и проверенная основа PR фиксируются в описании PR после
коммита; этот документ не выдаёт старый SHA за проверку будущего коммита.

## Требования и допуск до кода

Владелец назначил себя ответственным за инциденты биллинга и приватности,
выбрал почту и принял проверку каждые5мин, confirmed failure/conflict/gap15мин,
повтор failed/unknown отправки не чаще5мин, запрет повторной одинаковой
сохранённой accepted тревоги и сохраняемую реакцию до resolved либо явно
accepted_risk. Адрес находится вне git и материалов проверки. Принятый
канал ещё не является подключённым механизмом доставки. Postal acceptance
не означает получение или прочтение человеком. Финансовая почта не меняется.

До реализации завершены specify/clarify/plan, независимое reviewer-owned
ревью12/0, tasks-stage исходной T077, scoped analyze J1–J6/1task/100%/0findings
и taskstoissues: ensure, единственная OPEN#4932, canon validate244 на снимке.
87 исходных полных task lines сохранены; T070/T077 `[ ]`. Старые21checklist
побайтно сохранены (276checked/58unchecked); новый12/0 относится только к
качеству требований первого шага. Это не доказательство полного O6.

SHA-256 исходного независимого requirements report:
`7182d7a597b7ca7e041b56ab5a76e942b4a15c3cf677cee6b5be44c87c7cb773`.
SHA-256 scoped analyze:
`faf6f98bc9ebd7315171445536e726155b7737da3c02dac61f55551bf1196362`.
Поддерживаемый prerequisite `--require-tasks --include-tasks` выполнен;
установленный script не поддерживает `--require-spec`, наличие spec проверено
явно. Отказ неподдерживаемого флага сохранён, script не менялся ради него.

## Реализованная граница

Одна `billing_reconciliation_observations` с PK полного actual Temporal
namespace/workflow_id/workflow_run_id/activity_id/attempt/event_kind.
Миграция `0109_reconciliation_observations` следует за0108_public_consent.
started/succeeded/failed/canceled неизменяемы, повтор того же события не
обновляет время, противоречащий terminal сохраняется отдельно. DB timestamp
конечный; UTF-8 bounds, UUID, pattern, positive bounded integer, NOTNULL/CHECK.
ENABLE/FORCE RLS, точные session/current maintenance и прежний billing context,
SELECT/INSERT, запрет UPDATE/DELETE и destructive downgrade непустого журнала.

Recorder имеет отдельные engine/connection/session и транзакцию на событие;
общий2с deadline включает setup/SQL/COMMIT/cleanup. Driver options задают
statement1с/lock0.5с до первого SQL. Публичный `do_connect` получает
`AdaptedConnection.driver_connection` и ставит synchronous terminate callback
до dialect initialize и tenant after_begin. Connection.invalidate предшествует
Session.invalidate; собственного shield/__aexit__ или фонового writer нет.
Обычная ошибка наблюдения даёт фиксированный `billing_observation_unavailable`
без raw exception/SQL/URL/identity. Внешняя отмена сохраняется.

Исходное финансовое тело выделено в `_run_billing_reconciliation_activity`.
Полное AST тела и аргументы равны прежней функции, включая дваCOMMIT,
maintenance→освобождение locks→webhook→initial checkout и cleanup.
Обёртка вызывает тело один раз; ошибку наблюдения нельзя использовать для
повтора денег или подмены исходного результата/исключения/отмены.

Одна SQL-агрегация нового семейства `reconciliation_attempts`: count уникальных
полных ключей, пять sorted outcome groups, observed attempt>1 и missing-start.
Нет вымышленных прошлых attempts, возраста/heartbeat или полного исторического
покрытия. unknown не financial failure; coverage всегда partial. CLI остаётся
DB-only/no-write/READ ONLY RR с прежними15с/5с/2с/500gaps/64KiB. Старые addon
job_* и heartbeat не подменены этим источником; нет Temporal RPC/почты.

## Выполненные проверки

Финальный набор содержит65 уникальных PASS,0FAIL/ERROR/SKIP. Переиспользованы
59 исходных уникальных результатов с заменой7 затронутых nodeids; добавлены
6 ранних cancellation cases. Повторные успешные запуски не складываются.

| Набор | Результат | Время | Роль |
| --- | --- | --- | --- |
| unit-initial |42PASS|0.37с|исходный набор,6 deadline nodeids позднее заменены|
| unit-additional |10PASS|0.11с|границы двух COMMIT/ошибки/повторная отмена|
| pg-initial |5PASS|29.05с|RLS/CLI/constraints/dedup/conflict/snapshot/faults|
| pg-additional |2PASS|11.72с|restore/rollback и actual activity;1nodeid заменён|
| unit-review-fix |6PASS|0.33с|замена6затронутыхdeadline nodeids|
| pg-review-fix |3PASS|14.07с|замена actualactivity nodeid;2 ранних случая позже заменены6|
| pg-early-cancel-final |6PASS|27.53с|dialect/tenant × deadline/external/repeated cancel|

Все соответствующие команды завершились exit0. Исходные RED3unit/1PG
завершились exit1. Отдельный RED раннего tenant SQL при бюджете0.15с занял
2.153с и подтвердил CR-01; dialect case прошёл. Assertions no-tail/checkout
после упавшего времени в RED не выполнены. После исправления все6cases
подтвердили полный возврат менее0.5с при том же бюджете0.15с, сохранение
CancelledError, отсутствие оставшихся задач и checkout, закрытые драйверы.
Это синтетический отказ транспорта на настоящих SQLAlchemy/asyncpg/PG17,
не наблюдение аварии production.

Один дополнительный запуск2старыхcases произошёл после ошибки пути правки;
он завершился exit0, сохранён отдельно и не включён в65. Два предупреждения
основных наборов прежние: pytest assert rewrite и Starlette/httpx deprecation.
Первый отдельный probe вне project config имел2 предупреждения strict_rls;
он не объявляется основным финальным набором.

Проверены настоящая ActivityEnvironment identity и разные execution run ID,
плохие metadata/payload, отказ до/между/после финансовых COMMIT, cancellation,
guard и роли/SETROLE/BYPASSRLS/row_securityoff, NOTNULL/CHECK/immutability,
независимые транзакции/rollback, конкурентный dedup с неизменным timestamp,
conflict/unknown/missing-start/пропущенный attempt1, CLI/newprocess/date
independence/RR latecommit/no-write/privacy/whole-schema failure, query/lock
limits, synthetic SQLSTATE53100 и reply-lost после успешного observation
COMMIT. Последний остаётся unknown, хотя строка сохранена; деньги не повторяются.

В одноразовой PostgreSQL17 выполнены empty downgrade/upgrade, отказ nonempty
downgrade до потери истории, synthetic pg_dump/custom/pg_restore и проверка
строк/агрегата/FORCE RLS/grants/immutability после восстановления. Временные
dump/DB/owned containers удалены finally. Полные наборы79container IDs до/после
равны; чужие среды сохранены. Использовалась собственная server .venv с явным
PYTHONPATH и проверенным `twobrain_rec_server.__file__`.

## Независимое ревью и оставшиеся ворота

Первое независимое кодовое ревью: REQUEST CHANGES, CR-01(P1)/CR-02(P2).
Отчёт297строк полностью прочитан основным агентом, SHA-256:
`dad5edd40c90ca1d15c6c8baa72f2cf799b2eaaec106a0a662f1b62d23c51123`.
Оба замечания исправлены без изменения семи документов требований или
финансового тела. Новый frozen manifest содержит19inputs/14XML-log hashes,
65 уникальных cases. Повторное независимое code review завершено:
APPROVE для J1–J4, без новых блокеров. Полный227-строчный фактический отчёт
прочитан основным агентом; SHA-256:
`0db4fa56f128d35f40c3db575121de9854d829f671c069ce0ceec1ebb5073e3f`.
Все19 входов и14 XML/log сумм повторно совпали; исходные отчёты сохранены.
После кодового ревью завершён отдельный независимый scoped converge J1–J4.
Полный214-строчный фактический отчёт прочитан основным агентом; SHA-256:
`f0278a75acfa0846c8d57f586e16cfd1e8366a015b0933bb3e92976b76616dd5`.
Проверены6 требований J1–J6,7 решений плана и7 нормативных обязательств:
4 требования удовлетворены в первом шаге, J5/J6 остаются частичным
обязательным продолжением. Новых недоделок J1–J4 нет; полный FR-089/O6
сохраняет одну существующую HIGH partial находку в T077/#4932.
Все19 входов и14 XML/log сумм совпали до и после сверки; новых тестов,
task IDs или issues нет. Это приёмка первого шага, не полного O6.

Fragment/process/context/Ruff/diff прошли. Глобальный specify1.2.6 не совпал
с lock1.0.7; governance проверен actual pinned1.0.7/fe1d00e3 в отдельной
временной среде и прошёл, после чего среда удалена. Repo lock, глобальный
инструмент и зависимости продукта не менялись; обхода frozen doctor нет.

Локальные независимые code review и scoped converge первого шага приняты.
До merge обязательны точные GitHub governance-fast/macos-pr/pr-metadata
с common validator до/после merge, checked base и tree/parent proof.
Commit/PR/merge после проверок разрешены владельцем ранее. Full/CD/release,
production config и работающие данные не затрагивались.

## Открытый остаток

Рабочая почта, recipient binding, регулярный observer/heartbeat, остальные
источники, delivery attempts/retry/dedup и сохраняемая реакция J5/J6/O6
остаются обязательными в исходной T077. Исходные transient15мин/24ч,
fair-use≤24ч, receipt canceled немедленно/pending3дня, registry/F278FR041≤24ч
и eligible primary purge≤24ч сохраняются. Запрет оплаченного срока и
удалённые F272/F199 stop/runtime gates не возвращаются.

Новая таблица не закрывает #4932, T070 или весь backlog. Исторический пропуск
обязательного чтения до первоначального PR7884 не исправлен задним числом.
Свои текущие полные чтения7docs/23original ranges и применимые зависимости
проверены основным по original bytes/current hashes. Это контекст, не
универсальная приёмка продукта, ручных/финансовых/приватностных/выпускных ворот.
