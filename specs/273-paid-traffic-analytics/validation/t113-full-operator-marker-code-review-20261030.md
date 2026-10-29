# T113: независимое ревью маркера единственного initial/T0

30.10.2026. Проверяющий `/root/f273_release_boundary`, исполнитель `/root`.
Полоса `high-risk-product`, F273/T113/#7804, HEAD
`a241f34b8832b3b0ed83409f25d55853e7cb3e56`. Код проверен по локальным
изменённым байтам; это не проверка CI конкретного коммита.

## Решение и область

**SCOPED PASS локальной marker-реализации. Блокирующих находок в проверенном
срезе нет.** Принятый полный проект остаётся достаточно определённым для
следующей реализации controlled export. Этот обзор не подтверждает весь верхний
оператор, рабочий initial/T0, actual restore, расписание или включение writer.
Не следует выпускать один marker helper как законченный T113.

Проверены полный `activation_fence.py`, новая `_create_initial` и её связь
с `_revoked`, полный `test_activation_fence.py`, изменения учебных receipts
в общем ingress и Linux mount-проверке, новая ссылка из plan на полный проект.
Поиск всех вызовов `_create_initial` подтвердил отсутствие рабочего caller/CLI:
сейчас её вызывают только unit-тесты. Прежний код оператора вне marker-среза
остаётся под прежним отдельным обзором product drain.

## Проверенные свойства кода

- `_create_initial` сначала проверяет EX/revoked того же fence и точный
  `never_started`; любой уже attempted отвергается до записи. Наличие любого
  существующего `initial.json`, включая ссылку, тоже запрещает создание.
- UTC timestamp и 64-hex proof digest проверяются как внутренние аргументы.
  Их доверенное DB-происхождение и полный stopped verifier обязан подтвердить
  будущий верхний caller; этот helper не объявляет себя такой проверкой и не
  принимает supplied pass-file через CLI.
- Lock открывается без следования ссылкам, dev/ino сверяются с уже удерживаемым
  постоянным inode. Он не заменяется: truncate/write attempted+initial digest
  и fsync выполняются **до** O_EXCL создания initial. Short write/ошибка
  fsync/частичное состояние завершаются ошибкой; код не возвращает never_started.
- Initial создаётся O_CREAT|O_EXCL|O_NOFOLLOW с 0600, проверяемым владельцем,
  полной записью и fsync файла/каталога. Затем проверяются identity и точное
  обратное чтение. Существующий initial не заменяется, новый cutoff при отказе
  не вычисляется.
- `initial_marker()` читает тот же удерживаемый descriptor через pread,
  ограничивает размер 1024 байт, сверяет size/mtime/ctime до/после и identity.
  Допустимы только два точных version1 состояния; duplicate keys и неверный
  attempted digest отвергаются. Пустое/частичное/неизвестное содержимое не
  превращается в новый период.
- `read_ready()` сохраняет прежние проверки binding/времени/initial, затем
  требует attempted marker с SHA256 именно прочитанного initial. Один valid-looking
  ready JSON или переписанный initial без совпадающего marker не дают допуска.
- Отдельный write descriptor не заменяет постоянный lock и не снимает flock
  с удерживаемого descriptor. Нового provisioning/авторемонта marker здесь нет.
  Потеря initial после attempted не даёт повторно вызвать первый старт.
- Изменения fixtures приводят учебный marker к реальному digest учебного
  initial. Проверки binding/T0/read-only mount не обходятся. Runtime
  `activation_recovery_unverified` остаётся в неизменённом legal gate.

## Проверки исполнителя и предел доказательств

Ревьюер не запускал тесты, сборки, контейнеры, подключения к серверу или GRAF Dev.
Прочитаны тестовый код, сохранённые итоги журналов и mount JSON:

- 10 новых сценариев на прежнем коде: **10 FAIL / 32 PASS**. Проверяются пять
  unknown/never_started/mismatched marker вариантов, потерянный initial,
  сохранение inode и запрет повтора, три отказа fsync marker/initial/каталога.
- После реализации с прежними unit-проверками оператора: **63 PASS, 2 warnings**.
- Профиль с настоящей PostgreSQL и ingress: **123 PASS, 2 warnings**, 19,40с;
  журнал сообщает `isolated_container_removed`. Прежний synthetic T0 fixture
  должен обновлять свой marker при смене initial; такое обновление проверено
  в diff и не является обходом runtime gate.
- Linux bind JSON: `result=pass`, atomic revoke виден через тот же lock,
  direct bind отвергнут, supported directory replacement даёт HOLD,
  negative-control direct replacement остаётся stale, owned volume удалён.
  `source_sha256` JSON совпадает с текущим `activation_fence.py`.

Это прочитанные результаты исполнителя, не новое независимое выполнение и не
полная проверка crash/power-loss, provisioning, DB-time, export/restore/rollback
или верхнего readiness verifier. Полные причинные тесты следующего объёма
остаются частью уже принятого проекта.

## Актуальность требований, scoped analyze и 117 пунктов

Повторно прочитаны все вопросы четырёх reviewer-owned checklist:
requirements **16/0**, privacy-measurement **45/0**, security **27/0**, infra
**29/0**; итого **117 checked / 0 unchecked**. Отметки и хеши checklist не
изменились. Они подтверждают качество требований, а не исполнение T113.

FR-025 и договор initial/readiness повторно сверены: одна T0 новых аккаунтов,
потеря/неоднозначность закрывает admission, initial не заменяется. Старую
маркетинговую историю до T0 этот обзор не требует. Полный проект в новом
`validation/t113-full-operator-design-20261030.md` побайтно совпадает с уже
прочитанным принятым проектом в `.dev/growth/`: SHA256
`5d1e069f3fe18f31a21c72c9b0abc41614ff8bfc00c3269f27b1f3cb596738ec`.
Прежний precode PASS R1–R3 актуален.

В plan добавлен только перечитанный раздел со ссылкой на эту точную редакцию,
границами ordinary verify/планового backup и запретом включения до приёмки.
Spec/tasks/quickstart/activation/operations/constitution имеют прежние SHA;
применено разрешённое владельцем F273 исключение повторного чтения неизменных
документов по хешам. Противоречий spec/plan/tasks в этом продолжении нет.
T113/#7804/T112, реальный verifier и коммерческие критерии остаются открытыми.
Фактическая пауза/retry/access/resource evidence являются условиями рабочей
приёмки, не новыми блокерами следующего кода. T118/T119 не закрываются.

## Контрольные суммы

| Файл | SHA256 |
|---|---|
| spec.md | `45bcc14f170951e99813d6aeb0eddbbb413dd64f89cf410da256b6d5e30986b2` |
| plan.md | `02f4b52274c61fdf69f01415448a28d9509a1c12274a09d5a7382d3fc3db1b19` |
| tasks.md | `0cc469289c07b939594591b7816429497d91df6c86a7104af16106f2653769ea` |
| quickstart.md | `5bde6a5f388a03b6df1440fca32429f49bd458fdf9203fdc8df880352d249fea` |
| contracts/activation-milestones.md | `9898007a0e87400246f8c95b899dd807fab0424472143e15338429873982f3f9` |
| contracts/operations.md | `7d68aa7dc06b170508cd8b2858ede6e3e929b2e7155cd03b0895e715cb2b3abb` |
| constitution.md | `7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8` |
| activation_fence.py | `142fcacf6f5a43c9fc2358b197245e7ef312ed57b0c3dd4dd2ad1f6da17e902b` |
| activation_operator.py | `6e51f1eea210e9cea5eda089404a752d0cae1980a3db334e141d1d54ba61608e` |
| legal_basis_gate.py | `578de74b6a8362de6c73de9e2bca79e7fd60774324966dae2086d2b6daf7644e` |
| unit/test_activation_fence.py | `024b8092a21dcf23be0add51a8308edc29c7bd1a49faaf852e1f8a55acb1ec2a` |
| unit/test_activation_operator.py | `4f59426ba2d4bd018b61fdd47d229603b8826e9254cd8941741ae79c764497c3` |
| contract/test_activation_milestone_ingress.py | `b063f33e406aec7f8090b5e9c8e5980e8953868072d1e41bbed1efa158f113c6` |
| validation/activation-fence-mount-check.py | `4ea20f117d1fb7fe07305296004748e95fd76bf595ce73377ec01037a95e1f32` |
| t113-full-operator-marker-red.log | `318cd9578b9e320618f3d0eb53bded1d9c4160e6c297cf7d7ae4964d4ea05e67` |
| t113-full-operator-marker-green.log | `6acfc48a2554c1e57047798ee009770d0e048402384d329ce4a477b713783ff5` |
| t113-full-operator-marker-postgres-final.log | `29a7d6e8b671f7727afb65b7292a349bc093968fccf916d30c90166ebe2f5d2b` |
| t113-full-operator-marker-mount.json | `4f5320d1aea5459da5ce69ad50ac4345d5202c38807adf1ed9b37dcfcb5a00e2` |
| checklists/requirements.md | `6755318d0b7a76a9f6439446ad42362272d43859cc6f4b3c045b5c36ad1ed9a2` |
| checklists/privacy-measurement.md | `8c390000a2da12cf719348d56c08dcb21d886aac98ba1a90ad3d5c41e141cb4f` |
| checklists/security.md | `57f082b0b90faf7a3302db0aa1b9aacd29948641e824578ca4f86eee4dee9cb8` |
| checklists/infra.md | `998175e297553cedac7f4d7b2829459fcb3f1b650b3b3b6d072e9065437bfa94` |

Ревьюер создал только этот отчёт. Код, требования, план, задачи, checklist,
тесты, Git/GitHub и runtime не изменял; чужие локальные изменения сохранены.
