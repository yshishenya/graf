# T077: чтение реестра бонусных дней — 01.11.2026

Область: O10/C1–C6 в исходной T077/#4932, high-risk-product.
Основа локальной проверки: 458e874ddb40b3eb56dbc6535d84ef2e6bd2f8df.
Это ограниченная реализация наблюдения, не завершение FR-089/O6.

## Допуск до нового кода

Семь текущих оригиналов прочитаны полностью основным исполнителем в этом
диалоге; после сжатия проверены исходные выводы/байты и восстановлены целые
применимые разделы и зависимости. Внешние own-current-reading,
current-reading-verification, context-provenance и continuation-provenance
содержат происхождение. Исторический пропуск чтения до первоначального
кода PR7884 сохранён: весь O8 не объявляется PASS.

Независимый reviewer принял требования: [10/0](checklists/credit-ledger.md),
[отчёт](review-credit-ledger-requirements-20261101.md).
Scoped analyze C1–C6: 6 требований / 1 исходная задача / 100% покрытия,
новых CRITICAL/HIGH/MEDIUM замечаний0. Canon ensure, единственная OPEN4932
и canon validate243 прошли; новых issues и изменений GitHub не было.
Все87 исходных полных task lines и58старых открытых checklist gaps сохранены.

## Реализация и смысл

В существующем monitoring.py добавлена одна SQL-агрегация
TimeCreditLedgerEntry: закрытые state/count, четыре непересекающихся
временных количества pending/available и MIN допустимой достигнутой maturity.
Возраст — точная целая часть максимума, без округления через float.
Реестр относится к database_inventory/current_state независимо от report_date.

Шесть сохраняемых состояний включают rejected; matured остаётся только
результатом вспомогательного расчёта и здесь относится к unrecognized.
Отрицательная reversal считается строкой. Дни, баланс, идентификаторы,
source_ref, capacity и applied interval не выбираются. Будущая maturity
нормальна; достижение даты не доказывает eligibility, ошибку или SLA.
Приоритет причины: unrecognized → invalid_schedule → jobs_uninstrumented.
Даже пустое успешное чтение даёт partial/jobs_uninstrumented и четыре нуля;
add-on/job_attempts/errors/retries остаются null.

CLI/guard/READ ONLY RR/cleanup, схема, полномочия, финансовые writers и
остальные семейства не изменены. В тестовый TABLES добавлен существующий
реестр: он проверяется на ENABLE/FORCE RLS и входит в fingerprint no-write.

## Фактические проверки

Существующий owned apps/server/.venv, PYTHONPATH=src:.; путь monitoring.__file__
подтверждён. PostgreSQL — штатный одноразовый runner
scripts/run_local_postgres_tests.sh --focused. Рабочие данные/Dev не использованы.

| Набор | Последний результат | Предел утверждения |
| --- | --- | --- |
| credit-ledger-unit4 | 4PASS/0FAIL/ERROR/SKIP | Пустота, форма SQL/защитные NULL-ветви, причины и точный max/floor, включая предел datetime. |
| credit-ledger-pg6 | 6PASS/0FAIL/ERROR/SKIP,32.39с | Три новых PostgreSQL случая и три затронутых прежних; настоящий CLI/guard/forced RLS, роли/SET ROLE/READ ONLY до hook. |

Итого10 уникальных последних PASS:7новых (4unit+3PG) и3повтора из прежнего
набора из-за добавления реестра в collector/TABLES. Старые10/26/3 не
перезапускались целиком и не суммируются с этим набором. Два прежних warning
на запуск, SAWarning нет. Runner завершился isolated_container_removed.

Новые реальные сценарии: все шесть state/две неизвестные строки/отрицательная
reversal; maturity/expiry±1мкс, равенство и обратный порядок; исключение
терминальных/unknown из временной классификации; сумма четырёх=count;
приоритеты причин; новый CLI-процесс/другая report_date; старый RR-снимок
не меняется после writer commit, новый видит строку; no-write/privacy,
запрет HTTP; реальная схема отвергает NULL state/maturity/expiry без
ослабления NOT NULL. Переименование maturity даёт безопасный отказ целого
отчёта, затем схема восстанавливается. Запрещённые поля отсутствуют и в SQL,
и в JSON. Никакой financial helper не вызывается.

RED сохранён отдельно:4 ImportError до появления _credit_ledger и1PG FAIL
на прежнем source=null. Это история, не текущий PASS. XML/log/контрольные
суммы и11замороженных входов — во внешнем
f140-t077-credit-ledger-implementation-validation-20261101.json.

## Локальная приёмка и оставшиеся ворота

Независимое [кодовое ревью](review-credit-ledger-code-20261101.md): APPROVE
для O10/C1–C6,0новых замечаний,11/11замороженных входов совпали. Основной
исполнитель полностью прочитал фактический отчёт. Scoped converge и его
отдельная независимая сверка PASS:6требований/
7решений плана/7принципов,0новыхfindings; существующий O6 HIGH/partial
сохранён в T077, новой задачи нет. Process/governance/agent-context/fragments/
Ruff/diff прошли. Автоматических hooks после implement/converge нет.

Остаются commit/PR и три точных SHA/base GitHub gates/common validator.
Новое окно выпуска v2026.11.01.3 сохраняет
запрет merge до явного сообщения release operator; этот срез в него не входит.
Результаты commit/PR/merge/выпуска в этом документе пока не заявляются.

T077[ ]/#4932 OPEN. Другие источники, постоянные показатели попыток/ошибок/
повторов, регулярность/heartbeat, внутренние тревоги/retry и сохраняемая
реакция detected→contained→owner_assigned→notified→investigating→
resolved|accepted_risk остаются исходным O6. Сроки и обязательные финансовая,
приватностная, ручная и выпускная приёмки сохранены. Только Refs #4932.
F272/F199 stop/runtime gates и отказ в оплаченном сроке F278FR041 не возвращены.
