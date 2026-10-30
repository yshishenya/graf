# T113: независимое ревью проекта согласованной копии

30.10.2026. Проверяющий `/root/f273_release_boundary`, исполнитель `/root`.
Основа `593d6aa70f517d97d5f9f262f0323f6c7acec683`, F273/T113/#7804,
полоса `high-risk-product`.

## Решение

**SCOPED PASS проекта `_create_coherent_backup` для реализации. Конкретных
блокирующих неопределённостей в прочитанном алгоритме не обнаружено.**
Проект задаёт настоящий native backup и проверяемую согласованность полного
комплекта; он не ограничивается записью подтверждения. Код и результаты
будущих тестов не запрашиваются как условие этого проектного решения.

Полностью прочитан `.dev/growth/t113-coherent-backup-precode-20261030.md`,
SHA256 `d57c8d82601ad798e30934c35feddc8ccb23ab89bbbe7a7cf4a25d677de5eb9b`.
Это конкретизация прежнего 473-строчного
[проекта полного оператора](t113-full-operator-design-20261030.md), SHA256
`5d1e069f3fe18f31a21c72c9b0abc41614ff8bfc00c3269f27b1f3cb596738ec`.
Отдельный выпуск, новая служба, рабочие T0/ready или расписание не создаются.

## Почему проект достаточен

**Связность БД и объектов.** Caller удерживает deployment lock, filesystem EX
с отозванной готовностью, остановленные writers, reduced source с session EX,
owner в postgres и фиксированную установку. До копирования повторяются
identity/closed/quiet. В принятом controlled export source временно становится
true/limit0: native SQL держит один exported RR snapshot для dump, schema и
inventory. Полное SDK-чтение source objects до и после mirror совпадает между
собой и с файловым manifest новой копии. Так проверяется согласованность
источника в закрытом интервале; checksum уже скопированного дерева её не
подменяет. После export source снова false/limit0/quiet.

Прочитаны весь `backup-rec-stack.sh`, native
`rec-db-backup-inventory.sql` и `rec-db-verify.py`. SQL действительно держит
экспортированный snapshot до окончания native dump/schema/metadata и считает
checksums после завершения inventory. Verifier проверяет supported revision,
роли, RLS, ограничения, ledger columns/права/триггер, count/states и каноническую
схему. Новый путь переиспользует эти средства. Прежний shell не объявляется
готовым верхним оператором; его перевод на конечный общий вход остаётся T113.

**Журнал попыток.** До создания каталога новый UUID run записывает собственный
in_progress через atomic replace/fsync. Существующие каталоги и завершённые
копии не переиспользуются. Предыдущая запись проверяется закрытым parser;
missing допустим лишь при never_started без initial, malformed/unknown/
in_progress дают HOLD. Неудачная последняя попытка не заменяется ссылкой на
старую успешную. Новый manifest появляется O_EXCL/fsync только после полного
copy/verification/cleanup и повторных проверок source/backup, затем completed
attempt связывает его digest. Ошибка записи, fsync, отмена или неизвестная
очистка не разрешают успешный ответ либо готовность. Неполный комплект
сохраняется приватно; прежняя пригодная копия не удаляется.

Малый attempt читается через существующий fence `_file` с пределом16К.
Полный object manifest остаётся отдельным приватным файлом без этого
неподходящего ограничения. Предусмотрены version1, строгая схема, конечные
reason codes, binding установки/DB/OID/образов/версии, интервал, snapshot,
вычисленные schema/roles/inventory/lifecycle digests и точные artifact/object
размеры и SHA256. Готовый PASS/hash от внешнего caller не принимается.

**Текущие удаления.** Прочитаны `database_context`, `closure_snapshot`,
`replay_accounts`, полный v2 parser и применимые validated maintenance settings.
Проект переиспользует тот же текст запросов policy/access/full closure rows,
а не создаёт второй SQL-договор. В своей reduced RR read-only транзакции он
устанавливает те же transaction-local GUC, проверяет CLOSURE_POLICY/SELECT,
читает все строки и текущий private v2 register, выполняет parser и точную
проверку coverage с DB clock. Failed/unknown и непокрытая completed closure
дают HOLD. Два чтения register должны совпасть. Source не очищается и IDs
не выходят в manifest. Это текущая coverage activation lifecycle; отдельный
общий retention gate этим не считается выполненным.

**Отмена и владение.** Извлечение общих внутренних `_pg_run`/
`_wait_pg_commands`/`_mc_run` не меняет принятый протокол native completion.
Один владелец сохраняет pending markers, неизвестные uploads и известные
container IDs. Нормальный путь имеет один общий deadline600с; повторная
отмена не бросает SQL, Docker CLI или SDK thread. Очистка не даёт успеха после
исходного deadline. Неизвестный upload/native completion сохраняет staging,
а известный `mc` останавливается и проверяется до успеха. Неизвестное создание
не разрешает удаление по похожему имени. Source bucket SDK только читает,
очистка не удаляет его объекты. Повторное использование для backup получает
только направление source→новые файлы; rehearsal сохраняет readonly
файлы→свой UUID bucket.

Приватность проверяется до изменения modes новых файлов: обычный тип,
single-link, текущий owner; ссылки/специальные объекты и неоднозначные keys
запрещены. Source и старые копии не chmod. Последовательность допускает
неизвестный результат с сохранением данных и HOLD, без неявного resume.
Классификация ordinary backup failure/incident и безопасное возобновление
продукта остаются обязанностью уже принятого верхнего алгоритма.

## Обязательная проверка следующего кода

Проект задаёт причинный native успех на полном migrated PG17 ledger,
accepted closure и собственном MinIO с двумя объектами. Новая coherent copy
должна закрыть source, создать завершённые manifest/attempt и пройти тот же
native rehearsal/replay/COMMIT/новое физическое reduced чтение до очистки.
Это одна копия; она не заменяет минимум двух комплектов, 30-дневную проверку
восстановления или весь initial.

Указанные отрицательные случаи достаточны для следующего кода: changed source
после mirror, same-size corruption, invalid register/unknown closure до copy,
missing/in_progress/malformed attempt, занятый destination, native failure,
отмена живого copy/mirror и двойная отмена cleanup, unknown completion/upload,
cleanup и fsync failure. Проверка кода отдельно должна подтвердить неизменность
двух существующих callers общих native helpers, завершение lifecycle
транзакции до post-export identity и отсутствие completed допуска при ошибках
durability. Это проверяемые следствия прочитанного проекта, не дополнительные
предварительные блокеры. Прежние131 проверок требуют повторения после кода;
предыдущий результат не принимается за проверку будущих байтов.

## Scoped analyze и 117 вопросов

Все117 действующих вопросов четырёх reviewer-owned checklist перечитаны:
requirements **16/0**, privacy-measurement **45/0**, security **27/0**,
infra **29/0**, всего **117 checked / 0 unchecked**. Отметки и байты списков
не менялись. Это качество требований, не приёмка реализации или продукта.

Spec/plan/quickstart/activation-milestones/operations/constitution сверены
по прежним SHA256 в рамках разрешённого для F273 исключения повторного чтения.
Актуальное добавление tasks повторно прочитано: T113/#7804 и T112 открыты,
верхний trusted оператор, actual restore/resume и ежедневные проверки впереди.
Новая конкретизация согласуется с FR-025/033–036/051–053, предыдущим проектом
durable attempts/closed interval и действующими удалениями/основаниями.
Резервирование локальное; потеря узла/диска не объявляется покрытой. Нового
внешнего receiver, категории или срока хранения нет; разграничение с PostHog,
T118/T119 и рабочим запуском сохраняется. Дублирующая задача не нужна.

## Контрольные суммы

| Файл | SHA256 |
|---|---|
| spec.md | `45bcc14f170951e99813d6aeb0eddbbb413dd64f89cf410da256b6d5e30986b2` |
| plan.md | `02f4b52274c61fdf69f01415448a28d9509a1c12274a09d5a7382d3fc3db1b19` |
| tasks.md | `4e1723fdaf18a364d93a32af745f9fdad24680b75b1baa6e7db4117c72f505ab` |
| quickstart.md | `5bde6a5f388a03b6df1440fca32429f49bd458fdf9203fdc8df880352d249fea` |
| contracts/activation-milestones.md | `9898007a0e87400246f8c95b899dd807fab0424472143e15338429873982f3f9` |
| contracts/operations.md | `7d68aa7dc06b170508cd8b2858ede6e3e929b2e7155cd03b0895e715cb2b3abb` |
| constitution.md | `7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8` |
| backup-rec-stack.sh | `603738f16525d86fbed1c681ce0dfcca5cb90bdebd37c9af6641d306c907efc9` |
| rec-db-backup-inventory.sql | `3638e1d9279656a1864a5229a2210af8812499747108e37d16b33c763a419cdd` |
| rec-db-verify.py | `9878ffa671eacede35b599fe7a8c6fed0a2c8a75561a8d6d7d7911c13e28ebad` |
| rehearse-rec-restore.sh | `1d597450088a7667aa83fad718b3aa6469df04782a979e20d02fb9eebb922a35` |
| activation_operator.py | `7230ff0159ed92509cffdaae5408c5a8a4af15a2f5079dfbf1da67f5e46a1f8e` |
| restore_replay.py | `f76d79140add5c7f04eeb3a804d37ee894fcca32211daf72b659348ab8105085` |
| legal_basis_lifecycle.py | `ac4eb465afb0c647b0d3501bdbeaca2a8a4b1d9c6cad59d4c9a9953cae5f81f9` |
| tenant_context.py | `a7dc09e2b153344d5d3cf2f71dedaffba875995460d13342ad19389885b1762c` |
| checklists/requirements.md | `6755318d0b7a76a9f6439446ad42362272d43859cc6f4b3c045b5c36ad1ed9a2` |
| checklists/privacy-measurement.md | `8c390000a2da12cf719348d56c08dcb21d886aac98ba1a90ad3d5c41e141cb4f` |
| checklists/security.md | `57f082b0b90faf7a3302db0aa1b9aacd29948641e824578ca4f86eee4dee9cb8` |
| checklists/infra.md | `998175e297553cedac7f4d7b2829459fcb3f1b650b3b3b6d072e9065437bfa94` |

Ревьюер создал только этот отчёт. Исходники, spec/plan/tasks/checklist,
governance, Git/GitHub/runtime не менял; тесты, SQL, сборки, серверные команды
и выпуск не запускал. Чужие изменения сохранены. T0/ready/аналитика/IP/
расписание не включены, T113/T112 и коммерческие критерии остаются открытыми.
