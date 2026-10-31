# F273/T113: независимое ревью реализации staging

Проверяющий `/root/f273_release_boundary`, 31.10.2026. Ветка
`codex/f273-local-period-20261029`, основа
`28cf82c52fb962f62635e90c0d7a4d0f75051c06`, полоса `high-risk-product`.
Незакоммиченный срез определён контрольными суммами ниже.

## Решение

**SCOPED CODE / CONVERGENCE / ANALYZE PASS** только привязки staging к
защищённому ресурсу. Исходники и завершённые доказательства перечитаны;
окончательные16 frozen hashes совпали после последних тестов. Открытых ошибок
реализации P1: **0**, P2: **0**; CRITICAL: **0**, HIGH: **0**.
Чистые завершённые профили preservation1/replay-other12/failures12/coherent18
покрывают все43 случая replay. Это четыре отдельных прогона с cleanup/PASS,
а не один общий43; прежние неуспешные попытки остаются FAIL.

Все117 действующих вопросов повторно перечитаны и оценены: requirements16/0,
privacy45/0, security27/0, infra29/0; всего **117 checked / 0 unchecked**.
Отметки не менялись. Это качество требований, а не117 выполненных работ.
Предшествующий [проектный гейт](t113-staging-design-review-20261031.md) остаётся
основанием принятого объёма. Оба общих HOLD сохраняются.

Использованы `code-reviewer` и ранее `speckit-analyze`; прочитаны код, договоры,
runner и журналы. Тесты проверяющий лично не запускал; SSH/Docker/БД/Dev/Git/
GitHub не изменял. Разрешённое владельцем исключение F273 использовано только
для повторного чтения неизменных крупных baseline: четыре хеша и spec/data-model
вновь совпали; затронутые целые разделы и зависимости перечитаны.

## Сходимость реализации к принятому объёму

| Условие | Реализация и доказательство | Вывод |
| --- | --- | --- |
| Один новый PG prefix у четырёх создателей и SQL | Python coherent/rehearsal и оба shell caller создают `/var/lib/postgresql/data/twobrain-rec-backup.<alnum>`; SQL использует точный anchored guard до snapshot/dump/inventory; native проверяет отказ старого/неканонического пути | Соответствует |
| Metadata внутри фиксированного parent | Canonical parent, owner/mode, прямой canonical reference, удержанный FD; mkdir/rmtree относительно FD; pin dev/ino/uid/gid/mode, закрытие FD в finally | Соответствует |
| Удаляются только свои цели | Владение после успешного mkdir; коллизия/unknown create не дают права удаления. Native сохраняет reference, чужой host leaf и PGDATA sibling | Соответствует |
| PGDATA связан с фактическим ресурсом | env, единственный writable local volume без submount, host Source/proc-root, UID/GID70,0700/0750,noACL, PID start, стабильные identity и parent на том же st_dev | Соответствует |
| Запрет tmpfs/overlay независимо от st_dev | Stdlib ctypes fstatfs удержанных FD; только Linux64 amd64/arm64 и ext/XFS/Btrfs. Ошибка syscall/ABI/magic закрывает успех; actual FS проверены Linux | Соответствует |
| Проверка до/после DB context | SHOW data_directory сверяется до/после, staging context удерживается до завершения DB read, late failure не даёт вернуть успех; digest входит в runtime proof | Соответствует |
| Штатная запись PG не считается подменой | Первые5 стабильных полей identity без mtime/ctime/size/nlink; полная identity секретов не ослаблена | Соответствует |
| Частичный срез не выдаётся за включение | plan/tasks/quickstart/operations сохраняют общий preflight/recovery HOLD, T113/T112/T0 и коммерческие критерии | Соответствует |

Логические dump/restore не копируют PGDATA целиком; уникальный top-level
staging не relation и не цель DROP DATABASE. PGDATA/base/global/pg_wal и чужие
соседние каталоги не являются целями очистки.

Нижний rehearsal сохраняет `owner == geteuid()` по прежнему договору coherent
backup. Root0700 обеспечивается рабочим внешним входом и runtime staging
context. Linux-only ACL probe не вызывается нижним helper на Mac; noACL
обязателен в Linux runtime context. Это принятая граница, а не полный допуск
произвольного прямого вызова нижнего helper.

Изолированная PG fixture использует удаляемый anonymous volume вместо tmpfs:
реальный Docker cp не читает прежний tmpfs. Сохранены `--rm` и finally
`docker rm --force --volumes` своей цели. Это причинная адаптация испытания
к volume-backed продукту; новая рабочая конфигурация не вводилась.

## Закрытая P2: причинность wrong_device

Исходный `test_runtime_postgres_staging_binds_actual_protected_volume[wrong_device]`
подменял только os.fstat parent, оставляя Path.lstat настоящим. Он давал HOLD
на несогласованности identity даже без ключевого сравнения устройств.
Тест исправлен: fstat/lstat parent согласованно подменяют st_dev.

Прочитан runner: временная копия модуля теряет ровно
`and backup_identity[0] == identity[0]`; рабочий исходник не меняется. Целевой
тест тогда ожидаемо падает `DID NOT RAISE ActivationHold`,1failed,exit1.
JSON `execution_verified: true` здесь означает успешный отрицательный контроль.
Обычный Linux GREEN на тех же окончательных тестах проходит. **P2 закрыта**;
правка защитного кода ради этой пробы не требовалась.

## Прочитанные завершённые проверки

| Профиль | Фактический результат | Граница |
| --- | --- | --- |
| Linux staging actual FS/identity |25 passed,393 deselected,0 skipped,exit0| ext принят, tmpfs/overlay/неизвестное закрыты |
| Linux runtime lifetime/digest |118 passed,300 deselected,0 skipped,exit0| Пересекается с25; не суммировать |
| Полный unit operator |290 passed,128 Linux skipped,2warnings| Mac skips не заменяют Linux118 |
| Более ранний operator + оба shell modules |372 passed,116 skipped,2warnings| Иной состав; не суммировать с новым unit |
| Native snapshot/full migrated restore |8 passed,2warnings| Controller PASS и cleanup |
| Native DB/SHOW/lifecycle/access |24 passed,0 skipped,10warnings| Четыре worker; controller PASS и cleanup |
| Native replay-other |12 passed,31 deselected,2warnings| Controller PASS и cleanup |
| Native preservation |1 passed,42 deselected,2warnings| Reference/чужие цели сохранены; свои очищены |
| Native failures-clean |12 passed,31 deselected,2warnings| Последовательный запуск; controller PASS и cleanup |
| Native coherent-clean |18 passed,25 deselected,2warnings,262.61с| Последовательный запуск; controller PASS и cleanup |
| wrong_device mutation |1 ожидаемо failed,417 deselected,exit1| Отрицательный контроль, не обычный PASS |

Завершённые native журналы имеют `postgres_test_phase=focused status=pass`,
`postgres_test_result=pass`, `postgres_test_cleanup=isolated_container_removed`.
Значение worker_count=4 в заголовке runner само по себе не означает -n4:
failures-clean фактически последовательный.

Неуспешные попытки не зачтены общим PASS: tmpfs/Docker cp отказ, исправленная
ошибка нового assertion исходного числа DB, общий replay с21 PASS до
RequestTimeTooSkewed, затем остановленный clean -n4 с6PASS/6setup ERROR.
Последний выявил гонку существующей fixture выбора subnet до network create;
код среза не менялся, свои контейнеры очищены. Последовательные failures-clean
и coherent-clean завершены. Прочитан clock-current JSON: local start/end и
Docker epoch совпали, delta_seconds_from_end=0, clock_change_performed=false.
Проверяющий часов не менял; эта проба не подменяет результаты тестов.

## Остаток и запрет расширения PASS

`full_preflight_not_implemented` и `activation_recovery_unverified` остаются.
Не приняты installed jobs/cron/purge/retention/staging целиком, рабочая migration
protection v1 с историей, место для2полных копий+restore+staging, верхние
initial/backup/verify/actual restore/resume, shell/CD/rollback/daily, рабочие
ready/T0/IP/получатели, exact-SHA PR/CI/Full/выпуск. T112/T113/#7804 и
AC01–AC06 открыты. Производственный диск ниже20% по отдельному отчёту исполнителя;
это ревью ресурсный дефицит не снимает.

Привязка ресурса не доказывает ёмкость/квоты. Shell host TMPDIR ещё вне полного
local_only admission. Старый `_runtime_policy` использует полные metadata volume
roots; будущий верхний оператор не может считать прежний digest неизменным
после собственных mkdir/cleanup. Границы явно отражены договором.
Исходники/тесты не доказывают трафик, продажи или рабочую воронку.

## Контрольные суммы

Все16 frozen источников повторно совпали с
`.dev/growth/t113-staging-review-hashes-20261031.json`:

| Путь | SHA-256 |
| --- | --- |
| `apps/server/src/twobrain_rec_server/product_analytics/activation_operator.py` | `b086459d5f3a2a16571041cc96c7120543a6ebfed3dd1ae4887a0a7405ea4ced` |
| `apps/server/tests/fixtures/postgres_test_database.py` | `dc59630ba882005576c95b80964d03be650df62ffa7a6ddd9550e7c5641a7a94` |
| `apps/server/tests/integration/test_activation_product_drain.py` | `40a20ca85643e9615db82441cc5790b000da71797b09c51c02d70204131621c2` |
| `apps/server/tests/integration/test_activation_restore_replay.py` | `f31c1e74cc55972c9f118504d44a8ef9259b4490c40e37048681c83525b3bef8` |
| `apps/server/tests/integration/test_deployment_backup_restore_rehearsal.py` | `7b86192855667bb795ec42e39ce06030bbc1f0092c972c0c312c94b251e6441c` |
| `apps/server/tests/integration/test_deployment_backup_snapshot.py` | `6ed5bffcf14403b47aa5e210fe21b16891e0c7805a12ba38822988685476d357` |
| `apps/server/tests/integration/test_deployment_restore_safety.py` | `24834392b8d9712982e960f347113b333d4074cee0fc744433904eade2be5b3f` |
| `apps/server/tests/unit/test_activation_operator.py` | `82161f9349b415b4ff63dfc154570f5aff2d7d1e87b6ffc6769b04d1be313c40` |
| `changes/unreleased/F273.yaml` | `7e644838d1419fedbe7491813cf40753c6fdae060eb64e19a4416b8ee04ed79a` |
| `infra/scripts/backup-rec-stack.sh` | `3c8c9ddb8b7fa956a16a5f70f58e3756e06ba89c55340c376c58e35103e63f03` |
| `infra/scripts/rec-db-backup-inventory.sql` | `e324b585065912314476dc35f0f972469ff95214bb02591067879641cacec616` |
| `infra/scripts/rehearse-rec-restore.sh` | `8010cec7e7f23e28e40c259577dd6696b845fad29b877d172c2da232714a0511` |
| `specs/273-paid-traffic-analytics/contracts/operations.md` | `aa4536d6e082f9c830c342013c9ef4de5fc2f914a2e6cea6911521c613f6df95` |
| `specs/273-paid-traffic-analytics/plan.md` | `1dc9dc7019e81e4166de9ea636e64eacfad81da67d101566a75c134894bb370f` |
| `specs/273-paid-traffic-analytics/quickstart.md` | `a6d742666e14cea1a4940f0f00ed71438c7848d17da73b4fd8a25b32bdf665d9` |
| `specs/273-paid-traffic-analytics/tasks.md` | `adf455dfba084d14618bde48953cbd958b950971ba6b22a9fc83581daf2fc7f4` |

| Checklist | Проверено / не проверено | SHA-256 |
| --- | --- | --- |
| requirements |16/0| `6755318d0b7a76a9f6439446ad42362272d43859cc6f4b3c045b5c36ad1ed9a2` |
| privacy-measurement |45/0| `8c390000a2da12cf719348d56c08dcb21d886aac98ba1a90ad3d5c41e141cb4f` |
| security |27/0| `57f082b0b90faf7a3302db0aa1b9aacd29948641e824578ca4f86eee4dee9cb8` |
| infra |29/0| `998175e297553cedac7f4d7b2829459fcb3f1b650b3b3b6d072e9065437bfa94` |

| Завершённое доказательство в `.dev/growth/` | SHA-256 |
| --- | --- |
| `t113-staging-linux-green-20261031.json` | `e8df1cb2fef2527c6d6f926d257888c5531434e153b7dbcb157065553697ce51` |
| `t113-staging-runtime-linux-20261031.json` | `24b5c899064c3eff48045f8c566c7d413f2c844994029a7455bf5f9c723b1ad9` |
| `t113-staging-device-mutation-20261031.json` | `58ba581eef992096c144428ae9ec93f2ffc99b913868e097cd52ced1f1196c84` |
| `t113-staging-unit-final-20261031.log` | `612734d525809164a78b6eeb613480dcf54fc9348db23a39768ec53baa06577c` |
| `t113-staging-local-20261031.log` | `f2d5645e245f52d8513395f5d59e736e9f55faf9558fa87d22007aae2b241e98` |
| `t113-staging-native-snapshot-final-20261031.log` | `4de143ccbcf2040b9fa8e7dc9380281dcfa836e85feb67df677de12181c78cdc` |
| `t113-staging-native-database-final-20261031.log` | `41ee0bee811462563fe9f76217520bd069fd469ae852105d3e6f6afc5ad85a97` |
| `t113-staging-native-replay-other-20261031.log` | `c5ca5233d63d6383ea58c5cb00b3977c9973d57bc6c0bddb76e9dd53b95d5286` |
| `t113-staging-native-preservation-20261031.log` | `fae7e2c8269da40486ae8d2454a09e06598fc86eb2b1885e56ec01cf1ab69c61` |
| `t113-staging-native-failures-clean-20261031.log` | `d765c3924e4d8b82d7d2a8bd14d21fcedef67064cca99f14162dcc84c41fb827` |
| `t113-staging-native-coherent-clean-20261031.log` | `ba69975cca6fd50e47df0152e257f05844be412bdd85e86811d6eaf32586beba` |
| `t113-staging-clock-current-20261031.json` | `7566af9549d6708e1a213cee841cd7f18de182ca04b51cc97f634b5d3c1fed93` |

Журналы закрытые и ignored; перенесены только безопасные результаты/хеши.
