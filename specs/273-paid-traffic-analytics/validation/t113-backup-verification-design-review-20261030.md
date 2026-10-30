# T113: независимое ревью проекта чтения завершённых копий

30.10.2026. Проверяющий `/root/f273_release_boundary`, исполнитель `/root`.
Основа `6524c1de4a2c199aed365947c2d54adba5370d4e`, F273/T113/#7804,
полоса `high-risk-product`.

## Решение

**SCOPED PASS проекта `_read_coherent_backup` и `_verified_backup_set`
для реализации. Конкретной неразрешённой обязательной неоднозначности
в прочитанном алгоритме не обнаружено.** Решение оценивает достаточность
проекта; будущий код, готовые тесты и рабочие результаты не требуются как
предварительное условие этого PASS.

Полностью прочитан `.dev/growth/t113-backup-verification-precode-20261030.md`,
SHA256 `397b1a12dc62efea5c14b1c03dbf5cbefee2a9ba604c22c68231892baaf75e44`.
Это продолжение принятого 473-строчного
[проекта общего оператора](t113-full-operator-design-20261030.md), а не новый
scope, внешний вход или самостоятельный выпуск helper. Верхний initial/
verify, T0/ready, actual restore/resume, ротация, ежедневные проверки и T112
остаются открытыми.

## Почему алгоритм достаточен

**Проверяется физический комплект.** Reader требует закрытый backup-UUID
каталог0700 текущего владельца без symlink, читает все файлы существующим
полным manifest и отдельно raw manifest.json0600/single-link. Его размер
ограничен фактически установленным размером собственного файла, поэтому
полный список объектов не обрезается лимитом16К или10MiB. SHA256 raw
сопоставляется с действительно прочитанным файлом; duplicate JSON keys
отклоняет существующий `_object`, в котором нет лимита16К.

Точная версия1,20 producer fields, строгие типы и grammar, UUID/name/binding,
UTC-порядок start/export/finish, cleanup=confirmed и digests проверяются до
признания комплекта. Sorted unique artifact entries совпадают со всеми
физическими файлами, кроме самого manifest; object entries совпадают
с minio-objects subset. Пустой каталог объектов обязателен и при нулевом
числе объектов. Bool не принимается как integer size/count. Пересчитываются
native header/schema/roles/ledger/inventory/revision через прежние verifier/
`_backup_metadata`, а не принимаются сохранённые PASS поля. Повторный полный
manifest и root identity/mode/owner проверяют стабильность до возврата.

**Последнюю попытку определяет журнал.** `_previous_backup_attempt` проверяет
строгую запись, а latest должен иметь completed и binding текущей trusted
установки. Физический manifest этого destination обязан совпасть с digest
и finished_at из журнала. Freshness задана точно: `0 <= now-finish <26ч`,
по одному внутреннему aware UTC DB clock. Равенство26ч и время из будущего
дают HOLD. Внешний CLI не задаёт now. Отсутствие журнала при never_started
не превращается в успешный набор; после начала initial missing запрещён.
Failed/in_progress/unknown latest не маскируются двумя старыми копиями.
До/после чтения сверяются bytes latest-attempt, identity fence и revoked.
mtime каталога не определяет последнюю попытку.

**Два комплекта и текущая пригодность разделены явно.** Возвращаются latest
и один distinct полный UUID companion из доверенного parent этой canonical
DB. Каждый проходит физическую и native проверку. Исторический companion
может иметь прежние source/image/OID/cluster/schema/code binding; его
назначение — вторая полная локальная точка, а не доказательство текущих
runtime invariants. Запретить такие исторические копии лишь из-за изменения
версии означало бы подменить проверку полноты проверкой текущего rehearsal.

Latest при этом требует current binding. Reader не обновляет rehearsal
timestamp/digest, не выбирает companion вместо rehearsed reference и не
объявляет current source/lifecycle/code matching или rehearsal<=30дней
выполненными. Эти отдельные ворота остаются у верхнего verifier. Условия
допуска на момент использования результата также остаются у общего verifier/
ready consumer; эта стадия сама допуска не выдаёт.

**Ошибки и выбор определены.** Latest проверяется обязательно. Остальные
nofollow UUID names перебираются в детерминированном порядке до второго
пригодного. Отдельный invalid/incomplete/old-layout candidate не считается
полным и не исправляется. Ошибки parent/listing/identity и общий deadline
запрещают PASS всего набора; deadline нельзя скрыть исключением одного
candidate. Выбранные latest/companion должны оставаться физически теми же
до возврата, что явно включено в алгоритм и его причинные проверки.
Недостаток двух полных комплектов даёт HOLD. Читатель ничего не удаляет,
не chmod и не выдаёт выбор двух файлов за выполненную ротацию.

Caller удерживает trusted parent/install binding, deployment/filesystem EX,
resource capacity и один общий deadline. Все физические чтения в async пути
остаются во владении `_settled_sql` до завершения; нового retry600 нет.
Новых DB/provider вызовов, публичных SQL/callback/pass-file интерфейсов нет.
Возвращаемые refs/metadata приватные; IDs/keys/content не выходят в отчёт.

## Причинная проверка следующего кода

Предложенный native путь двух созданных coherent copies → verified set →
прежний native rehearsal/replay/COMMIT/новое физическое reduced readback
проверяет связь producer и reader на настоящих artifacts. Это достаточная
основа будущего теста, а не уже выполненный результат.

Отрицательные случаи конкретны: один комплект, old-style/partial,
failed latest при двух старых, future/age26ч, malformed/duplicate/extra
manifest fields, неверные artifact/key/count/bool/hash/timing/binding,
parent link, изменение attempt и selected companion, same-size dump/object
corruption и дополнительный физический файл. Исторический допустимый
binding companion не принимается за current gate. Удаление selected
companion до возврата обязано привести к HOLD.

При реализации отдельно проверить, что tuple/list канонизация производится
строго в одном месте, bytes manifest действительно привязаны к физическому
manifest hash, а пропуск недействительного старого candidate не поглощает
общую ошибку времени или parent. Это следствия принятого алгоритма,
не новые предварительные блокеры. Прежние175 проверок и будущие source/test
hashes требуют отдельного code review; проектный PASS их не заменяет.

## Scoped analyze и 117 вопросов

Повторно прочитаны все117 действующих reviewer-owned вопросов:
requirements **16/0**, privacy-measurement **45/0**, security **27/0**,
infra **29/0**. Итого **117 checked / 0 unchecked**. Их хеши совпадают
с прежними; отметки не менялись. Это качество требований, не завершение
реализации или приёмка рабочих показателей.

Spec/plan/quickstart/contracts/constitution сверены по прежним SHA256
в рамках разрешённого владельцем F273 повторного использования неизменных
документов. Последнее status-добавление tasks прочитано:172+7PASS относятся
к внутреннему coherent producer; initial/верхний оператор, два комплекта,
actual restore/resume/ежедневные проверки, shell и T112 открыты.

Новая конкретизация согласуется с FR-025/034–036/051–053 и разделом ordinary
verify общего проекта: complete latest attempt, физические hashes/ownership,
две разные полные копии, отрицательная/26ч/future freshness запрещена,
latest и rehearsed references различны. Локальный набор не объявляется
защитой от полной потери узла/диска. Основания, точные удаления, сроки и
внешние получатели не меняются; новой отдельной задачи не требуется.

## Контрольные суммы

| Файл | SHA256 |
|---|---|
| spec.md | `45bcc14f170951e99813d6aeb0eddbbb413dd64f89cf410da256b6d5e30986b2` |
| plan.md | `02f4b52274c61fdf69f01415448a28d9509a1c12274a09d5a7382d3fc3db1b19` |
| tasks.md | `cd6a36e6151589b6fabb9cbd1a66e96981baf0249c60a8667c861400725dfd72` |
| quickstart.md | `5bde6a5f388a03b6df1440fca32429f49bd458fdf9203fdc8df880352d249fea` |
| contracts/activation-milestones.md | `9898007a0e87400246f8c95b899dd807fab0424472143e15338429873982f3f9` |
| contracts/operations.md | `7d68aa7dc06b170508cd8b2858ede6e3e929b2e7155cd03b0895e715cb2b3abb` |
| constitution.md | `7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8` |
| checklists/requirements.md | `6755318d0b7a76a9f6439446ad42362272d43859cc6f4b3c045b5c36ad1ed9a2` |
| checklists/privacy-measurement.md | `8c390000a2da12cf719348d56c08dcb21d886aac98ba1a90ad3d5c41e141cb4f` |
| checklists/security.md | `57f082b0b90faf7a3302db0aa1b9aacd29948641e824578ca4f86eee4dee9cb8` |
| checklists/infra.md | `998175e297553cedac7f4d7b2829459fcb3f1b650b3b3b6d072e9065437bfa94` |

Ревьюер создал только этот отчёт. Код, spec/plan/tasks/checklists/governance,
Git/GitHub/runtime не менял; тесты, SQL, сборки, серверные команды и выпуск
не запускал. Чужие изменения сохранены. Рабочие T0/ready/сбор/IP не включены;
T113/T112 и AC01–AC06 остаются открытыми.
