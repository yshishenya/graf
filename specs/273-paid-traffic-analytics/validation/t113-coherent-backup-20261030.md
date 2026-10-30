# T113: согласованная копия закрытого источника

30.10.2026. F273/T113/#7804, `high-risk-product`, Legacy Impact: `untouched`.
Основа `593d6aa70f517d97d5f9f262f0323f6c7acec683` и локальные изменения.
Это следующая внутренняя стадия [полного оператора](t113-full-operator-design-20261030.md).
[Независимое ревью проекта](t113-coherent-backup-design-review-20261030.md)
разрешило реализацию; нового внешнего входа или отдельного выпуска нет.

## Реализовано

- [x] `_create_coherent_backup` переиспользует native inventory/dump/verifier,
  controlled export и уже удерживаемые блокировки. Новый каталог не заменяет
  старую копию; постоянный журнал попытки записывается до его создания.
  Неизвестная версия, повреждение или незавершённая последняя попытка дают HOLD.
- [x] Dump/schema/inventory получены из одного exported RR snapshot. Все байты
  объектов прочитаны SDK до и после native mirror и сопоставлены с файлами
  копии. Проверены родительский каталог, owner/modes, отсутствие ссылок,
  полные native schema/roles/RLS/constraints/ledger metadata и checksum.
- [x] Текущее покрытие lifecycle прочитано своей reduced RR read-only
  транзакцией: общие SQL policy/access/closure rows, полный v2 register,
  DB clock и прежний parser/coverage. Реестр перечитывается. Идентификаторы
  и содержимое в manifest не выходят; source не очищается. Это только
  текущая activation coverage, не приёмка всех категорий хранения.
- [x] `_pg_run`/`_wait_pg_commands`/`_mc_run` общие для двух настоящих callers.
  Completion marker подтверждает native child, а не только Docker CLI.
  Неизвестный copy/completion сохраняет используемый staging. Source bucket
  только читается; известные mc containers удаляются и проверяются.
- [x] После закрытия export/cleanup повторяются identity/closed/quiet/revoked
  и полный файловый manifest. Manifest создаётся O_EXCL и записывается потоком,
  перечитывается; fsync включает held parent FD, сохраняя запись backup-UUID.
  Только затем публикуется completed attempt. При ошибке его публикации
  точный собственный inode возвращается к прежнему in_progress до попытки
  failed. Постоянный отказ fsync не даёт гарантии crash-durability;
  видимый неопределённый журнал не разрешает допуск, source остаётся закрыт.
- [x] Один владелец переживает повторную отмену до окончания cleanup.
  Общий deadline не продлевается ради успешного ответа. Новая неполная
  копия сохраняется закрытой; предыдущие копии не удаляются.

## Проверка

Первый причинный запуск восьми проверок журнала: 8FAIL на отсутствующем
`_previous_backup_attempt`, затем 8PASS. Первый native сценарий: FAIL на
отсутствующем `_create_coherent_backup`, затем PASS через настоящий dump,
mirror, восстановление и чтение. Первая матрица дала 12PASS/1FAIL: тест
ошибочно ожидал limit0 при collision до controlled export. Реализация
сохранила исходный -1 и закрытую БД; исправлено только ожидание теста.

Первый дополнительный запуск: 6PASS и ошибка подготовки одной Docker-сети.
Две одновременно запущенные мной проверки выбрали один свободный диапазон
между чтением inventory и созданием сети. Это ошибка организации проверки;
финальный дополнительный запуск выполнен последовательно после основного.
Код оператора из-за неё не менялся.

Основной профиль fence/operator/unit replay/drain/native replay: **172PASS,
2 существующих предупреждения, 428,37с**, exit0. Он использовал финальные
исходники оператора/replay и тест с15 coherent-сценариями (SHA256
`ff0fe6546d9b2b6d513f5389942f6138592b2e4c1a5d35a93206c99c73ae69b2`).
После старта к тому же тесту добавлены только3 native исхода и утверждение
отказа читателя после двойного fsync. Для них и3 прежних native сценариев
назначен отдельный последовательный прогон7 случаев на финальном тестовом
файле. Исходники оператора/replay при этом не менялись. Последовательный прогон:
**7PASS, 32 deselected, 2 существующих предупреждения,104,66с**, exit0.
Вместе проверены175 уникальных случаев;4 выполнены повторно. Финальный
тестовый файл дополнительно доказывает, что читатель отвергает in_progress
после двойного fsync failure. Native coherent matrix теперь18 случаев:
успех, изменение source/copy/register, неизвестное/неудачное native завершение,
потерянный copy/create response, отмена native/mirror/cleanup, ошибки cleanup,
fsync manifest/parent/attempt и collision. Предыдущие consumers helpers
также входят в основной профиль; собственные контейнеры/сети удалены.

Ruff, governance, development-process, fragments и whitespace: PASS.
[Независимое ревью кода](t113-coherent-backup-code-review-20261030.md):
**SCOPED PASS**, SHA256
`fd542df05bac9c85d3f5e15cb33b12634425d567974cf3e4f7e3f75286b97fb3`.
Найденные два риска сохранения устранены до приёмки. Scoped convergence:
новых обязательных работ вне прежней открытой T113 не обнаружено; весь
перечисленный ниже остаток сохраняется. Приёмка всей T113 и рабочего
измерения этим не объявляется.

| Файл | SHA256 |
| --- | --- |
| activation_operator.py | `549908b8d93879a484e8e86f51946fb24e92f7fa6e45940e38dc6585ea4a1532` |
| restore_replay.py | `b103dc57f0ed7569c07a1e4412d9b2caf52aead2bf70eb5e9e05cd2552832e92` |
| test_activation_operator.py | `cfdd8aa625caf2324937268698217cb2c9b2dc8e2fa40fe3078d4233e6d3e1e4` |
| test_activation_restore_replay.py, финальный | `28c1c1cd5862cfd2379a36e0e1d34d6c6e752de3a1b14ccec297fd5469dc4932` |
| Дополнительный журнал7PASS | `4695e3d3dd2ccfed5582ad9e59d9c4530f2f9bed29975c97a169fcb2c9c404f5` |
| Основной журнал172PASS | `1448b003b1fd870d6ce287009210a0b46d0635a0e8ff67bc2c7e8a3d393972f2` |

Журналы — ignored `.dev/growth/t113-coherent-final-profile.log` и
`.dev/growth/t113-coherent-native-final.log`.
Нативные данные, пароли, дампы и полные зависимости в доказательства не
копируются. Эти локальные проверки не заменяют GitHub CI точного PR SHA.

## Остаток того же T113

Одна согласованная копия не заменяет минимум двух комплектов, ротацию,
периодическую репетицию или весь initial. Trusted верхний preflight и
initial/backup/verify/actual-restore/resume, полное сравнение product-state,
ежедневные retention/access/resource проверки, CD/rollback, перевод shell
на общий вход и T112 остаются открытыми. Новых задач и закрытий нет.

Рабочий T0 ещё не установлен; ready, аналитика/IP, внешние получатели
и расписание не включены. Production и GRAF Dev не изменялись.
Учебные пробы не засчитываются как трафик, новые клиенты или продажи.
