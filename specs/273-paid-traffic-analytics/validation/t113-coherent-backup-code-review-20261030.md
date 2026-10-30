# T113: независимое ревью кода согласованной копии

30.10.2026. Проверяющий `/root/f273_release_boundary`, исполнитель `/root`.
Основа `593d6aa70f517d97d5f9f262f0323f6c7acec683` и зафиксированные локальные
байты; F273/T113/#7804, полоса `high-risk-product`.

## Решение

**SCOPED PASS `_create_coherent_backup`, общих native helpers, переиспользуемых
SQL closure и соответствующих проверок. Неустранённых блокеров в проверенной
области нет.** Решение относится к четырём финальным source/test SHA256 ниже.
Два завершённых журнала прочитаны и их хеши независимо сверены.

Код сопоставлен с precode SHA256
`d57c8d82601ad798e30934c35feddc8ccb23ab89bbbe7a7cf4a25d677de5eb9b`
и [принятым проектным ревью](t113-coherent-backup-design-review-20261030.md),
SHA256 `95149e287a28681a0a228bcd61168b042b6ba3900d5d8640b63b4af72647acf9`.
Это внутренний шаг того же общего оператора. Данный PASS не завершает T113,
не принимает верхний trusted вход, initial/T0/ready, actual restore/resume,
рабочее расписание, T112 или выпуск.

## Найденные риски сохранения и исправления

**R1: запись нового каталога копии не была закреплена в его parent.**
Первоначальный код fsync содержимое и сам каталог копии, но не каталог,
содержащий новую запись backup-UUID. Completed attempt мог оказаться сохранён
раньше этой записи. В финальном коде parent открыт O_DIRECTORY|O_NOFOLLOW,
его FD удерживается до finally; mkdir выполняется через dir_fd. Проверяются
dev/ino parent и reference. После manifest/readback повторяются эти проверки,
затем fsync(parent_fd) до completed. Native `parent_fsync_failure` отказывает
именно на FD родителя: успешного завершения нет, attempt не completed,
source закрыт и готовность отозвана.

**R2: двойной отказ fsync мог оставить видимый completed.** Если rename
completed уже прошёл, а directory fsync и следующая запись failed отказали,
первоначальный путь мог оставить latest completed при неподтверждённом исходе.
Теперь до completed сохраняются точные прежние in_progress bytes этого run.
При ошибке публикации проверяется совпадение текущего inode с удерживаемым
собственным FD; на этом inode восстанавливаются прежние bytes, затем внешний
обработчик пробует failed. Повреждённое/частичное состояние также не принимается
читателем. Native `double_attempt_fsync_failure` после начала completed
непрерывно отказывает всем следующим fsync: видимое состояние остаётся
in_progress с manifest_sha256=None, а `_previous_backup_attempt` даёт HOLD.
При неисправности постоянного хранения гарантия сохранения после аварии
не заявляется; рабочая готовность остаётся отозванной. Нового сервиса или
параллельного файла допуска для исправления не введено.

Оба замечания сообщены исполнителю до окончательной приёмки. Исправления
прочитаны по финальным байтам; исходный вариант не считается принятым.

## Проверенная реализация

**Действительная полная копия.** До copy повторяются source/owner identity,
closed/quiet/revoked, container cluster и prior attempt. Установка и writers
остаются обязанностью trusted caller. Новый UUID destination не заменяется
и не переиспользуется. In_progress записывается до mkdir. В controlled export
native psql запускает прежний capture_dump=true: dump/schema/inventory
получаются из одного exported RR snapshot. Прежний native verifier и
канонизация схемы проверяют artifact checksums, supported revision, роли,
RLS, ограничения и ledger invariants. Digests вычислены кодом, а не приняты
аргументами как PASS.

SDK manifest source objects до mirror и после него сопоставляется с полным
файловым manifest новой копии: точный key/size/byteSHA256, включая Unicode
и пустой объект. Порча одинакового размера и изменение source обнаруживаются.
Перед chmod/fsync проверяются собственник, обычный тип и single-link;
symlinks/special/collisions запрещены. Старые копии и source не chmod.
Source bucket только читается; SDK-удаления source objects нет.

**Lifecycle без изменения источника.** Вынесены три прежних SQL constants
policy/access/full rows, и ими пользуются оба callers. Текст прежних запросов
сохранён. `_backup_lifecycle` открывает свою reduced RR read-only транзакцию,
применяет validated transaction-local maintenance settings, проверяет
CLOSURE_POLICY и SELECT, использует DB clock и полный v2 parser/coverage.
Failed/unknown/exact coverage сохраняются. Register прочитан повторно внутри
proof и перед завершением copy. Транзакция закрыта до post-export identity.
В manifest выходят только digests, без closure IDs и содержимого строк.
Эта coverage не выдаётся за весь retention gate.

**Процессы и отмена.** Общие `_pg_run`/`_wait_pg_commands` сохраняют UUID,
command digest и атомарный completion marker native child. Завершение Docker
CLI не подменяет завершение `psql`/`pg_dump`. Unknown upload или completion
сохраняют staging и HOLD; собственные `mc` containers удаляются и отсутствие
проверяется. Неизвестный create не разрешает rm по имени. Один outer owner
дожидается cleanup через повторную отмену; продление cleanup не разрешает
успех после исходного deadline. Controlled export закрывает source обратно
false/limit0 и ждёт quiet. Product resume здесь отсутствует.

**Сохранение результата.** До manifest проверены cleanup, source identity/
closed/quiet/revoked, неизменность parent и всех backup bytes. Manifest создан
O_EXCL0600, записан потоком без ограничения16К, fsync и полностью перечитан
по SHA256 и artifacts. Удерживаемый parent синхронизируется до completed.
Attempt использует atomic replace/fsync/readback и ограниченный parser;
missing после начала initial, in_progress, повреждение и неизвестная версия
не разрешают готовность. Новая неполная копия остаётся приватной, старые
успешные комплекты не удаляются.

## Причинные доказательства и точный охват

Основной профиль fence/operator/unit replay/drain/native replay завершился:
**172 passed, 2 warnings, 428,37 с**, exit0. Он использовал финальные исходники
оператора/replay и integration file SHA256
`ff0fe6546d9b2b6d513f5389942f6138592b2e4c1a5d35a93206c99c73ae69b2`
с15 coherent-сценариями. После collection добавлены только3 native случая
и дополнительное утверждение отказа читателя после двойного fsync.

Их отдельный последовательный прогон вместе с тремя прежними native случаями
и double-fsync проверкой на финальном integration file завершился:
**7 passed, 32 deselected, 2 warnings, 104,66 с**, exit0.
В совокупности это **175 уникальных тестов, четыре повторены**, а не179
уникальных или один общий прогон175 на финальном файле. Исходники продукта
между этими прогонами неизменны. Предупреждения — ранее известные pytest
fixture import и deprecated httpx в Starlette TestClient.

Новый native успех создаёт полную coherent copy текущей БД с8 ledger rows
и accepted closure, затем использует ту же `_rehearsal_resources`, native
restore, пониженный replay, COMMIT и новое физическое NullPool readback.
Старый reference dump с9 строками не подменяет новую текущую копию.
Готовность, initial и T0 не создаются. Источник для replay не изменяется.

Прочитанные18 coherent случаев охватывают успех, changed source/register,
same-size corruption, invalid register, native failure, unknown copy/create,
cleanup failure, manifest/parent/double-attempt fsync, destination collision,
двойную отмену mirror/cleanup/native, lost native response и неизвестный
completion. Дополнительный native wrapper действительно открывает source
сессию перед dump. Cancel ждёт наблюдаемую чужую source-сессию; неизвестный
ответ разрешается через pending marker, неизвестное завершение сохраняет
staging. Это проверяет взаимодействие нового caller с controlled export,
а не только прежний изолированный rehearsal helper.

Первый matrix collision FAIL был неверным ожиданием теста: до export
закрытая БД сохраняет исходный limit -1. Исправлено ожидание, не поведение
продукта. Первый дополнительный прогон имел6PASS и ошибку подготовки сети
при двух одновременно выбранных одинаковых свободных subnet. Это не PASS
того случая; окончательный последовательный прогон7PASS заменяет эту попытку.

## Контрольные суммы и пределы

| Файл | SHA256 |
|---|---|
| activation_operator.py | `549908b8d93879a484e8e86f51946fb24e92f7fa6e45940e38dc6585ea4a1532` |
| restore_replay.py | `b103dc57f0ed7569c07a1e4412d9b2caf52aead2bf70eb5e9e05cd2552832e92` |
| test_activation_operator.py | `cfdd8aa625caf2324937268698217cb2c9b2dc8e2fa40fe3078d4233e6d3e1e4` |
| test_activation_restore_replay.py, финальный | `28c1c1cd5862cfd2379a36e0e1d34d6c6e752de3a1b14ccec297fd5469dc4932` |
| .dev/growth/t113-coherent-final-profile.log | `1448b003b1fd870d6ce287009210a0b46d0635a0e8ff67bc2c7e8a3d393972f2` |
| .dev/growth/t113-coherent-native-final.log | `4695e3d3dd2ccfed5582ad9e59d9c4530f2f9bed29975c97a169fcb2c9c404f5` |

Прочитано последнее добавление tasks.md, SHA256
`37b96e428629766e1e2d99c023d411f307383ca40be929cd493376d01e2003e4`:
оно фиксирует172PASS внутреннего шага и оставляет T113/T112 открытыми.
117 reviewer-owned вопросов и хеши требований приняты в предшествующем
проектном ревью: requirements16/0, privacy45/0, security27/0, infra29/0.
Их отметки не менялись и не превращаются в приёмку реализации продукта.

Верхний caller по-прежнему обязан удерживать фиксированную установку,
deployment/filesystem EX, остановленных writers, source session EX и
проверенные SDK timeouts без retries. Два комплекта, ротация, общий initial/
backup/verify/actual-restore/resume, полное product-state сравнение,
ежедневные retention/access/resource gates, shell delegation, CD/rollback
и T112 сохраняются в общем кандидате. Рабочий recovery blocker не снят.
Локальные учебные результаты не подтверждают GitHub CI точного SHA, выпуск,
рабочее измерение/IP, трафик, внешних клиентов или продажи.

Ревьюер создал только этот отчёт. Код, spec/plan/tasks/checklist/governance,
Git/GitHub/runtime не менял; тесты, SQL, сборки, серверные команды и выпуск
не запускал. Чужие правки сохранены.
