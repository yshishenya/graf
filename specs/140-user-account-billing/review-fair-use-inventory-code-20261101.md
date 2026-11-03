# Независимое кодовое ревью и сверка F140/T077 O12 — 01.11.2026

Решение: **APPROVE для локального среза O12/F1–F6**.
Новых содержательных замечаний CRITICAL/HIGH/MEDIUM/LOW: 0/0/0/0.
Самостоятельная предметная сверка: 6 требований, 7 отношений к плану,
7 конституционных принципов; новых обязательных задач реализации O12 нет.
Это не приёмка полного FR089/T077/O6, не разрешение обходить PR gates и не выпуск.

Исполнитель: /root/f140_notification_content_review, тот же диалог
01a1955c-cb77-78e3-8844-ffeabcb2d594. Полоса high-risk-product / active Spec Kit slice.
Рабочая копия: /Users/yshishenya/.codex/worktrees/f140-referral-reversal/crisp.
Ветка: codex/140-observation-fair-use.
Base/HEAD: 4625146710762f12fb2f854fbbd41d8900146b6b.
Назначение допускает запись только этого отчёта. Чужие изменения сохранены.
Применён навык /Users/yshishenya/.agents/skills/code-reviewer/SKILL.md:
локальное ревью правильности, безопасности, простоты и достаточности проверок.

## Происхождение требований и границы чтения

Переиспользовано собственное полное чтение семи текущих оригиналов и
применимых общих документов в том же диалоге, проверенное по
review-fair-use-inventory-requirements-20261101.md (SHA-256
2340c64b1979a3c1eb20143468b8c9e9c2a2a2e24a1d4da16831ff5ed46d6964).
Там сохранены точные пути, суммы, исходные outputs, полные диапазоны и карта
применимости. Семь оригиналов и 28 неизменных context/source inputs повторно
совпали. Единственное намеренно изменённое прежнее source input — monitoring.py;
его новый diff прочитан и новая сумма независимо совпала с frozen manifest.
Непрочитанные зависимости нового поведения не выявлены. Память не использовалась.

В этом назначении прочитаны фактический git diff всех четырёх файлов кода/
тестов/fragment, полный новый collector и место его включения, новые тесты,
существующие helpers/три затронутых старых PG-теста, actual migrated fixture,
исходные runtime bootstrap grants304–322, O12 целиком и plan83–109.
Сопоставлены действительные XML/testcases, журналы и хеши всех пяти запусков.

Журнал этого диалога:
/Users/yshishenya/.codex/sessions/2026/11/01/rollout-2026-11-01T07-27-29-01a1955c-cb77-78e3-8844-ffeabcb2d594.jsonl.
Фактические output locators:321869 — diff;8864f0 — manifest;
a43181 — skill/helpers/bootstrap/analyze;c6feba — список артефактов;
30a53f — XML/hash/case compare;b96b04 — полные финальные журналы;
f1ed3c — старые тесты/helpers;d78a2c — точные строки collector/O12/плана;
0f1fba — feature pointer/миграционный runner/task diff;
77758f — собственные повторные hash/task/checklist compares.
Это доказательства чтения и проверки артефактов, не новый запуск продукта.

## Проверка реализации F1–F6

| Требование | Фактическая реализация и проверка | Результат |
| --- | --- | --- |
| F1 — источник и смысл | monitoring.py249–274 читает FairUseReviewRecord без report_date/shop фильтров. collect_billing_report311 подключает его в том же защищённом снимке. source=fair_use_reviews/database_inventory/current_state; count означает строки. | PASS |
| F2 — закрытые state | FAIR_USE_STATES и _closed формируют пять разрешённых state и одну unrecognized для любого другого, включая NULL. SQL group/order по закрытому state; count=sum(groups.count). confirmed исключён из pending. Нет writer или вывода о снятом ограничении/закрытии incident. | PASS |
| F3 — четыре группы | invalid254–257 — CASE NULL/isfinite прежде арифметики; затем review<start или numeric epoch delta>86400. Внешний CASE invalid→start>as_of→review<=as_of→waiting. При валидном start<=review это исчерпывающие непересекающиеся ветви. Pending-фильтр исключает terminal/unknown; Python суммирует только количества. | PASS |
| F4 — честная неполнота | reason268–269 строго unrecognized→invalid_schedule→deletion_and_reaction_uninstrumented. Все варианты _source дают partial; deletion/reaction=null. Пустота0/[]/четыре0. Нет дат/возраста/вывода о SLA. Ошибка реальной схемы проходит в существующий whole-report report_unavailable/exit1. | PASS |
| F5 — безопасность и минимум | Один db.execute/select/group/order, только state/starts_at/review_by/count. Нет выбора частных столбцов/дат в Python, writes/egress/новых ролей/миграций/служб. Guard279 и CLI READ ONLY RR/timeout/cleanup не менялись. PG проверяет один SQL, отсутствие private columns/значений и неизменные fingerprints. | PASS |
| F6 — доказательство и остаток | RED сохранён; 3unit+4новыхPG+3затронутыхPG окончательно PASS. Реальные constraints/forced RLS, отдельные malformed VALUES, снимки/новый процесс/privacy/no-write/роли проверены ниже. Требования10/0, scoped analyze и сохранённая T077 установлены. Commit/PR exact SHA/base gates ещё отдельный следующий этап. | PASS локальной части; PR gates pending |

### Почему порядок SQL безопасен

Внутренний CASE проверяет NULL и обе isfinite до ELSE с EXTRACT(EPOCH).
Он не полагается на неопределённый порядок AND для защиты от infinity arithmetic.
Для NULL хотя бы один IS NULL даёт true; для ±infinity соответствующий
NOT isfinite даёт true. На вход epoch попадают только конечные timestamptz.
PostgreSQL EXTRACT(EPOCH) даёт numeric; вычитаются секунды абсолютного времени,
без Python float, interval calendar days или зависимости от session timezone.
Ровно86400 допустимо,86400.000001 недопустимо, обратное расписание invalid.
При валидном нулевом сроке start==review==as_of сразу deadline_reached;
start>as_of остаётся not_started, будущее не считается ошибкой часов.

Реальный PG case с +infinity/+infinity и -infinity/-infinity не падает:
такие строки проходят текущий deadline CHECK и входят в invalid pending.
Неизвестные/NULL state и обратный/>24h schedule проверяются SQL VALUES,
без удаления CHECK или ослабления NOT NULL положительной БД.

## Проверка тестов и действительных результатов

Источник manifest:
/Users/yshishenya/Documents/Codex/2026-11-01/graf-f140-final-failure/f140-t077-fair-use-implementation-validation-20261101.json.
Все 11 frozen file hashes совпали с текущими байтами. Все пять пар XML/log
независимо сопоставлены SHA-256 с manifest; testcase/nodeid и исходы совпали.

| Артефакт в той же папке | Tests / pass / fail / error / skip | Смысл |
| --- | --- | --- |
| fair-use-inventory-red-unit3.xml/.log | 3 / 0 / 3 / 0 / 0 | Исходный ImportError отсутствующего _fair_use_inventory на owned пути. |
| fair-use-inventory-red-pg1.xml/.log | 1 / 0 / 1 / 0 / 0 | Реальный CLI ещё выдаёт not_connected/source=None, вместо нового источника. |
| fair-use-inventory-unit3.xml/.log | 3 / 3 / 0 / 0 / 0 | После реализации: empty/reason/projection и одна SQL-операция. |
| fair-use-inventory-pg7.xml/.log | 7 / 2 / 5 / 0 / 0 | Первый PG отказ; отсутствует SELECT workspaces для существующего owner_scope RLS подзапроса. Не выдан за PASS. |
| fair-use-inventory-pg7-final.xml/.log | 7 / 7 / 0 / 0 / 0 | Окончательная PG-проверка,35.047с XML/35.05с log. Заменяет предыдущие исходы тех же7nodeids. |

Итого **10 уникальных окончательных PASS**,0FAIL/ERROR/SKIP:
3 новых unit,4 новых PG и3 затронутых прежних PG. Успешные запуски не повторялись;
прежние2PG PASS не прибавлены второй раз. Два прежних предупреждения:
PytestAssertRewriteWarning и StarletteDeprecationWarning; SAWarning нет.
18 deselected PG/19 deselected unit не считаются выполненными тестами.

Новые PG-тесты1038–1244 фактически проверяют:

- Пустой реальный CLI, все исходные NOT NULL/state/deadline CHECK отказами
  невозможных INSERT, безопасный отказ отсутствующего столбца и восстановление.
- Все5state;11строк, pending9=invalid2+not_started1+deadline3+waiting3;
  start/review±1мкс и равенства, zero-duration, ровно24ч, будущее и обе infinity.
  SQL один; частных столбцов/синтетических значений нет в JSON/stdout/stderr.
- Три приоритета reason на malformed VALUES: NULL/unknown/обратный/>24ч,
  terminal confirmed с NULL не pending. Session timezone America/New_York,
  fallback01.11.2026: ровно86400 истекших секунд допустимы, +1мкс invalid.
  Это исполнение настоящего SQL, а не имитация Python-результатов.
- Один READ ONLY RR snapshot до/после конкурентного commit не меняется;
  новая session/новый процесс видит строку. Разные report_date не меняют groups.
  Fingerprint включает FairUseReviewRecord и остаётся прежним после чтения.
- Три прежних PG-теста: пустое/заполненное/no-write/privacy/restart;
  реальные identity/read-only до hook и диалекта; SET ROLE/неверный context/
  mutation denied. Они прошли после добавления нового источника.

### Исправление только синтетической fixture

В TABLES добавлен FairUseReviewRecord: новые таблицы не создаются вручную;
существующий isolated fixture выполняет настоящий alembic upgrade head.
Для каждой TABLES проверены relrowsecurity/relforcerowsecurity=(true,true).
Рабочая модель и migrations0068–0074 не менялись.

GRANT SELECT workspaces добавлен только тестовой maintenance роли, потому что
неизменная migrated fair_use policy содержит owner_scope subquery.
Неизменный bootstrap_runtime_database_roles.py304–322 уже выдаёт SELECT/DML
ON ALL TABLES app/maintenance ролям; его SHA-256 независимо совпал с manifest.
Поэтому fixture восстановила существующее runtime право, без BYPASSRLS,
superuser, policy replacement или product grant. Отрицательные role checks
остались и прошли. Наличие права SELECT само по себе не обходит RLS.

Cleanup задан finally штатной isolated fixture, ошибка удаления даёт FAIL.
Финальные XML не содержат teardown errors. Живые контейнеры reviewer не
инспектировал/не запускал/не удалял; отдельной live-очистки этим отчётом не заявляет.

## Самостоятельная предметная сверка converge

Ниже собственная сверка, а не принятие сообщения основного исполнителя PASS.
Покрытие требований6/6 отражено таблицей выше. Отношения к plan83–109:

| Пункт плана | Наблюдаемое соответствие |
| --- | --- |
| P1 один collector существующей модели | Только _fair_use_inventory и включение311; нового входа/службы нет. |
| P2 закрытые state/group/order | _closed/SQL count/group/order, пятьstate+unknown; реальный PG all-states. |
| P3 безопасное время | Вложенный CASE/isfinite/numeric epoch86400, тесты infinity/NULL/DST/±1мкс. |
| P4 данные только в SQL | Python получает закрытые группы/counts; timestamps/ORM rows/частные поля не выбираются. |
| P5 сохранение безопасности | Guard/CLI/RLS/модель/миграции/права/egress прежние; реальная fixture FORCE RLS, отрицательные роли. |
| P6 доказательства в прежних двух test files | RED и10 уникальных окончательных PASS; positive constraints сохранены, malformed отдельно VALUES. |
| P7 процесс и объём | Независимый requirements10/0; analyze6/1/100%/0; данное code review;87tasklines/58gaps/O6 сохранены. Три GitHub exact-SHA/base gates ещё pending. |

| Принцип | Собственная проверка применимого ограничения |
| --- | --- |
| I capture integrity | Нет изменений capture/аудио/старого routing. |
| II visible consent/control | Нет ограничения Record/Stop/согласия/данных. |
| III privacy/observability | Только metadata counts, нет secrets/content/egress. |
| IV deletion truth | deletion/reaction=null; полное удаление не принимается и не меняется. |
| V macOS distribution | Нет app/build/publication/signing; отдельные gates не объявляются выполненными. |
| VI Spec Kit/testable gates | Требования/независимые отметки/анализ/RED/реальные тесты/данное review; PR gates сохраняются, исходный O8 пропуск не исправлен. |
| VII reference fidelity | Пользовательский интерфейс/содержимое reference/ассеты не менялись. |

Новых обязательных задач реализации O12 не обнаружено. Остаток процесса:
независимый отчёт прочитать и принять, оформить converge основного исполнителя,
затем обязательные проверки точного нового PR SHA и актуальной основы.
Это **implementation ready; PR/tracker pending**, не полное завершение T077.

Все87 полных task lines побайтно равны HEAD; T077 `[ ]` сохранена.
Восемь старых checklist побайтно прежние:162 отмечены/58 открыты.
Не принимаются полный O6/FR089, deletion, heartbeat/регулярность/тревоги/
повторы, сохраняемая реакция/owner/evidence, T070/fair-use enforcement и
сохраняемое разрешение, финансовая/приватностная/ручная и выпускная приёмки.
Только Refs #4932; GitHub OPEN не запрашивался, issue этим назначением не менялась.
Transient15мин/24ч, fair-use review≤24ч, receipt canceled немедленно/pending3дня,
registry/F278FR041 реакция≤24ч и оплаченный срок после отзыва сохранены.
Исторический пропуск чтения до PR7884 не исправлен; весь O8 не PASS.

Fragment F140 сохраняет прежние O10/O11 summary details/limitations и дополняет
их только fair-use/confirmed/reached-deadline/null/partial границами; отсутствие
чеков/сверки/показателей заданий не затёрто. Legacy Impact untouched.

## Контрольные суммы проверенных байтов

| Frozen input | SHA-256 |
| --- | --- |
| specs/140-user-account-billing/spec.md | `2bb46cd0c1a56229b805020826b5c394896ad40570e49442e37058b9974c07c1` |
| specs/140-user-account-billing/contracts/operator-observation.md | `d2677f946881c4aac82a96932cfde02d1418e230ce835b177f76f9db5a80563b` |
| specs/140-user-account-billing/plan.md | `541b831f259b4df9c995f2920f7539afda709c6d1ce6546a38b47affb0eb2947` |
| specs/140-user-account-billing/tasks.md | `f37b52d4ddf7f8a36b56f50ca410172a7af19154bc02c13d38373a3f4cc5318c` |
| specs/140-user-account-billing/quickstart.md | `345236fe985477df29e569eb115e5265b126829bd040cc7f60543461476cd434` |
| specs/140-user-account-billing/research.md | `d32added43f00e206e658932dd93574196682ed1e9e58f4b1bcf9e94d2a85183` |
| specs/140-user-account-billing/data-model.md | `b8aa76ae308f33b29d3a58aa5f3c399aa062bedaf54f14e21edea1776d4e2d18` |
| apps/server/src/twobrain_rec_server/billing/monitoring.py | `18715992d1c13f56ffeda4f20c1e09fbe62c4ccd3dc3e34395ce41f1b45cdd05` |
| apps/server/tests/unit/test_billing_monitoring.py | `8672a78be4c35ddacd65c296872d5ad6834f772cbc484869840d2b14acac9e45` |
| apps/server/tests/integration/test_billing_monitoring_postgres.py | `b6c0df6e441c16ea5367ac0d8e2793442769eddd5d8fd81d3469858ae3563842` |
| changes/unreleased/F140.yaml | `8e5f04cabefe38c14b16e9ff4bd59ec465ade584ec0bec5ae430c4dfb7f3a5af` |

| Пара артефактов | SHA-256 XML / log |
| --- | --- |
| fair-use-inventory-red-unit3 | `9e9644682952d4693ad45142ac1d3598d497d8e2ea2325b4a83b6e199d2a6aed` / `e293337a01d4e4849f776fb468eef13c2e7888ee10e58ba6b02c7e231385a268` |
| fair-use-inventory-red-pg1 | `0df58f8d9a2874abce8eeea5eb20bf01bf5c5ff9e975c2563a63850b3a9ea1ff` / `29451e7844917c1e92ded43cb790f8ebf485fb1e841692777e596819893064d5` |
| fair-use-inventory-unit3 | `71fd1fa4472240940f8ee5752570c422f1abe5c72a691dc2f2f56bdcd1c75b55` / `8be8a9f5282724a36b415fecbaf9f2e3e9b414a330b1610baca18feb4359d3bb` |
| fair-use-inventory-pg7 | `6f8510880b961a4a545ce9dcd7f8a40f31f156d5c6fde4dc2a0f0eaa6f1589a4` / `156f69b121e275f15eabfc8d2f3fbbfbbc520313b6958eea25eb713d2fd983e0` |
| fair-use-inventory-pg7-final | `598c221def55178085f22438948f0c88bedfaef7b8730f2822a00f247b4b206d` / `04216a9f6ecddc87e6b9808a9c8aa8b6737fb1b0bfbd41608208c636cced1efa` |

Изменён только этот новый отчёт. Reviewer не менял код/spec/plan/tasks/checklist,
Git/GitHub/CI/PostgreSQL/Dev/данные и не выполнял тесты/hooks/коммиты/выпуск.
Проверки в этом назначении — чтение, hashes/XML parsing и read-only сравнение.

Итог: весь отчёт перечитан в двух неусечённых выводах d3bd83/e9885f;
11 frozen inputs повторно совпали после чтения. Новых findings нет.
Собственный отчёт без trailing whitespace; успешные тесты не повторялись.
