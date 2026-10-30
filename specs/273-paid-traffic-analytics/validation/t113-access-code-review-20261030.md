# F273/T113: независимое ревью reader прав и зависимостей

Дата: 30.10.2026. Проверяющий: `/root/f273_release_boundary`.
Основа: `24cf069c869dfc71d1bd5a2d534e34f42a078398`, ветка
`codex/f273-local-period-20261029`, T113/#7804, `high-risk-product`.

## Решение и охват

**SCOPED CODE REVIEW PASS. Открытых P1: 0, P2: 0.** Принят только
фиксированный `local_retention_database_access`, его включение в существующие
`_runtime_databases` / `_backup_lifecycle`, согласование `search_path` одной
физической сессии и соответствующие проверки. Это ревью локальных файлов,
привязанных контрольными суммами ниже; после коммита требуется отдельное
подтверждение проверок именно его полного SHA.

Прочитаны весь diff, полный новый SQL/helper, оба фактических вызывающих
участка, `_physical_connection`, изменённые интеграционные сценарии и
добавленное утверждение unit-проверки. Принятый исходный алгоритм и дизайн
сохранены в [design review](t113-access-design-review-20261030.md).
Дополнение O/A ниже уточняет прежний SQL этого исторического отчёта.
Прежний SQL `35b014ae4857bfeed77ee47599c5d17370af2b49a2c8e53c5956dfe51a00c428`
и прежний precode `a1d8b84f36443c6fbe62085d8d9f4c91053a2fbf2c2f66f416a606c52de8949b`
относятся к прошлому design-снимку; ниже приняты конечные байты с уточнением O/A.

## Найденный дефект и его исправление

**R1 / P2, закрыт.** `_physical_connection` передавал `search_path=pg_catalog,
public`, тогда как прежний catalog и новый access reader требуют ровно
`"$user", public`. Действующий путь останавливался на старом catalog ещё до
access reader; сценарий отмены не доходил до тела контекста. Это подтверждено
первой реальной проверкой: 4 failed / 6 passed, ошибкой
`activation_operator_retention_catalog_unverified`, после которой выполнена
очистка своего контейнера. Этот журнал сохранён, его результат не выдан за PASS.

Исполнитель исправил единственную общую строку `server_settings` на принятый
`"$user", public`. Сам guard, квалификация каталогов и порядок reader не
ослаблены. Проверены все вызовы этого helper: они принадлежат существующему
runtime DB flow. Утверждение существующего cancellation unit-теста теперь
закрепляет это значение. Повтор исходных 10 сценариев прошёл; конечные 17
сценариев также прошли после дополнения совместимости ниже.

## Дополнение сохранения прежней совместимости

Исполнитель обнаружил, что pinned access descriptor первоначально принимал
только `O`, хотя старый catalog допускает `O` и `A` (`ENABLE ALWAYS`) семи
точных пользовательских триггеров. Независимо проверено и до изменения SQL
согласовано минимальное уточнение: только `NOT tgisinternal AND tgenabled='A'`
нормализуется в `O` в access row. `D`, `R` и внутренние FK-триггеры остаются
точными. Иные поля и dependency edges не исключены.

Старый catalog по-прежнему выполняется первым, проверяет точный закрытый набор
триггеров и включает фактический O/A в свой digest. Конечная сверка повторяет
оба reader через тот же source: переход O→A во время операции поэтому
запрещён прежним сравнением catalog. Собственные настоящие PG17 тесты
исполнителя закрепляют catalog O≠A, access O=A, возврат к baseline,
первоначальный A→успех и O→A внутри yield→`retention_catalog_changed`.
Это сохраняет прежний договор без снятия защиты от изменения во время работы.

Конечный precode SHA-256:
`fabf49db62c2377737d87cf51c9100018de6fbee0ce7f9189bfaf9b6e81be4ca`.
Конечный SQL SHA-256:
`45d345f080e38878dce505a0bb036378e04dfbe50c45056958fcdeef45c9b40d`.
Проверяющий независимо извлёк константу через AST, убрал только начальный
перевод строки и подтвердил побайтовое совпадение с конечным SQL-прототипом.
Expected 575 canonical records остаётся
`bfb2080813ca48347c03e453b1e52195d4b5d21d69915d207fe518d12f554ddc`.

## Проверенные свойства кода

- Reader требует существующую read-only transaction, PG17 и точный
  `search_path` до metadata SQL. Использует закрытый `TABLES`, fixed query
  и expected из исходного кода; источник/окружение/CLI не передают expected.
- ACL/defaults/columns/constraints/incoming FK/indices/types/triggers/
  policies/rules/languages/roles/settings и обе стороны выбранных зависимостей
  реализованы согласно принятому точному SQL. Случайные внутренние FK-имена
  и intrinsic toast edge нормализованы только в принятых местах; фактические
  свойства внутренних триггеров сохраняются. Нет рекурсивного механизма.
- Возвращается только digest. Исключения и несовпадение дают стабильный
  `activation_operator_retention_access_unverified` без SQL/строк в сообщении;
  `CancelledError` не поглощается `except Exception`.
- Оба callers сначала выполняют прежний catalog. Runtime читает новый access
  до снижения прав и повторяет оба reader после yield через тот же reduced
  source. Lifecycle сохраняет свою read-only repeatable-read transaction,
  maintenance/context и проверки действительного удаления; новый digest
  включён в прежний lifecycle binding. Новых соединений или смены роли внутри
  reader нет. Общая RR-транзакция всего preflight не заявляется.
- Отмена и исключение не дают proof успешного выхода; существующий физический
  cleanup дожидается закрытия, при необходимости завершает соединение.
  Runtime-тест дважды отменяет настоящий запрос и проверяет отсутствие
  оставшихся сессий `graf-activation-preflight`.
- `datallowconn` и `datconnlimit` не попадают в pinned descriptor. Существующий
  coherent-backup success реально проходит при закрытом source и проверяет
  итог `(False, 0)`; его export/drain/resume guards сохранены.

## Прочитанные завершённые проверки

Проверяющий тесты не запускал. Полностью прочитаны завершённые журналы
исполнителя и соответствующий тестовый код; незавершённый вывод не принят.

| Журнал `.dev/growth/` | Результат | SHA-256 |
|---|---|---|
| `t113-access-focused-20261030.log` | Исходные 4 failed / 6 passed; cleanup PASS; R1 | `303fcf7ecc506d065568c3eaa112c5b6591d358aa0e493211b29b2dfb2957ca6` |
| `t113-access-focused-final-20261030.log` | 10 passed, 2 warnings, 53.38 s; cleanup/result PASS; до уточнения O/A | `fee4682e6ec0ebb0297cd80158535b3fab88b3707403b7ba697ca389716187e8` |
| `t113-access-consumers-20261030.log` | 348 passed / 37 skipped, 2 warnings, 86.71 s; cleanup/result PASS; до уточнения O/A | `97b16fd5f38f012c904e0f1e338d5cc411af338ea4537f6a6e95b9fef429afbf` |
| `t113-access-native-final-20261030.log` | Конечные 17 passed, 2 warnings, 137.99 s; cleanup/result PASS | `79dad2e22b3275a3b90c265ada3c1c77082363820d4e508c296f0847b2343bd9` |

Конечная коллекция — 17 тестов,
`b02e9cdd6cfc745e7465e108eba02ae1d5b54a452a3f01df82e1947e35b7775d`.
Она повторяет actual reader, все 11 runtime cases и действующие потребители:
coherent backup+restore success, lifecycle, четыре категории и их source
postconditions, точный category replay, старую копию с exact account replay.
Reader-тест проверяет отсутствие транзакции/read-write, неверную версию,
query failure, отмену, wrong expected, повтор, owner→maintenance, O/A и 17
обратимых metadata изменений с восстановлением baseline после каждого.
Подмена в runtime test ограничена host/port собственного UUID PG17;
сам SQL/параметры сессии не подменяются. Новые rule/DELETE для обхода каталога
не исполняются. Ошибки и изменения не ведут к рабочим удалениям.

37 пропусков широкого профиля не являются успешной проверкой: Linux
root/proc/memfd/FD/ACL границы требуют своей платформы. Конечный узкий native
набор пропусков не содержит. Два предупреждения относятся к существующим
pytest plugin import и Starlette/httpx, ошибок в журналах успеха нет.

## 117 вопросов и требования

Повторно прочитаны все 117 действующих вопросов четырёх reviewer-owned
списков. Отметки не изменялись. Качество требований остаётся **117 `[x]` /
0 `[ ]`**; это не готовность реализации или достигнутые результаты роста.

| Список | Отмечено / не отмечено | SHA-256 |
|---|---:|---|
| requirements | 16 / 0 | `6755318d0b7a76a9f6439446ad42362272d43859cc6f4b3c045b5c36ad1ed9a2` |
| privacy-measurement | 45 / 0 | `8c390000a2da12cf719348d56c08dcb21d886aac98ba1a90ad3d5c41e141cb4f` |
| security | 27 / 0 | `57f082b0b90faf7a3302db0aa1b9aacd29948641e824578ca4f86eee4dee9cb8` |
| infra | 29 / 0 | `998175e297553cedac7f4d7b2829459fcb3f1b650b3b3b6d072e9065437bfa94` |

В соответствии с разрешённым исключением повторного чтения F273 проверены
неизменные хеши ранее полностью прочитанных constitution, PRD, current status,
product-gates, spec, plan, operations, data-model и полного алгоритма оператора:
все совпали с таблицей design review. Первоначально также совпали tasks и
quickstart; затем исполнитель добавил только запись текущего результата.
Их конечные добавления и изменения organic-growth-plan/owned fragment, а также
целый `validation/t113-access-20261030.md` независимо прочитаны. Они правильно
разделяют scoped metadata PASS и ещё открытые полный T113/рабочие ворота.
Нового основания,
получателя, срока хранения, автоматического удаления или продуктовой границы
не вводится. FR-036/050 и существующие backup/restore/deletion/admission
требования сохраняются. Новых пробелов требований этого участка не найдено.

Конечные SHA-256 изменившихся документов:

| Документ | SHA-256 |
|---|---|
| quickstart | `14af4d747644380db6cfe0254de947cb625dadaefc743a2f4e14654ffeefe631` |
| tasks | `8e3140b4f76456083ebbb90e5d21f05f0479f1bee77f6bbb3c189a0e154b7294` |
| organic-growth-plan | `9ae0dc9e190658415014458689bea50e83ec37aa8e8ebaf9c6edcc23fe1f93ce` |
| F273 fragment | `b9baf66d0cd8615cd2f83c4cf076ad6f2b08dd71b5ffc1f4b7c0963ea9295c3f` |
| t113-access-20261030 report | `7959a4595bdfa76682fb4f93f7f75b829ef51f3ac427e05dd23807848a8f0382` |

## Привязка к локальным файлам

| Путь | SHA-256 |
|---|---|
| `apps/server/src/twobrain_rec_server/product_analytics/local_retention.py` | `600658bdef8dfe5a7c243994647ee84727de26b48099559a008b215a1be249c9` |
| `apps/server/src/twobrain_rec_server/product_analytics/activation_operator.py` | `01c5117741d94135978096575ad834902c93bb0e9324e2f28da7b3c472e448c9` |
| `apps/server/tests/integration/test_activation_restore_replay.py` | `7fd4b6ac7483585f7be7a96f946ff950626eec46fa0383f53f8964deff2c70e9` |
| `apps/server/tests/integration/test_activation_product_drain.py` | `31fdae19c3681a38531b43891af72b99650d407deff9578c8b8a71a21a18c862` |
| `apps/server/tests/unit/test_activation_operator.py` | `dd8591334cb098aec30a73b77107bfb3dd9e55b3cf159feb9a780dbd4de5673c` |

## Сохранённые ограничения

`full_preflight_not_implemented` и `activation_recovery_unverified` остаются.
Полные T113/#7804, installed jobs/host schedules, верхний оператор, настоящие
restore/resume, shell/CD/rollback, T112, рабочие T0/ready/IP, включение аналитики,
выпуск и коммерческие AC01–AC06 не приняты этим отчётом. Локальные тесты не
заменяют exact-source GitHub CI, frozen candidate, сервер или пользовательскую
приёмку. Новых внешних сообщений/публикаций и доступа к рабочим данным нет.

Проверяющий изменил только этот отчёт; не менял код/spec/plan/tasks/checklists,
Git/GitHub, процессы/БД/Docker/SSH, GRAF Dev или production. После записи отчёт
перечитан целиком, хеши его входных файлов и итог117/0 сверены повторно.
