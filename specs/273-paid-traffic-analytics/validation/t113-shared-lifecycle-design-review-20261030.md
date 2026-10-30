# F273/T113: независимый проектный гейт общего lifecycle reader

Дата: 30.10.2026. Проверяющий `/root/f273_release_boundary`.
Рабочая копия `growth-guide-previews/crisp`, ветка
`codex/f273-local-period-20261029`, HEAD
`8350b688788861d8b35dd304bcf325f7eef305e8`. T113/#7804,
`high-risk-product`. Проверка до изменения исходников.

## Решение

**SCOPED DESIGN / ANALYZE PASS: CRITICAL0, HIGH0; открытых P1:0, P2:0.**
Четыре контрольных списка: **117 checked / 0 unchecked**; отметки не менялись.
Минимальный алгоритм определён, блокирующих пробелов проектирования не найдено.
Разрешён общий фактический reader внутри существующего оператора; полный
graf-local/installed-jobs proof, верхний оператор и рабочая готовность не приняты.

Полностью прочитан precode
`.dev/growth/t113-shared-lifecycle-precode-20261030.md`, SHA-256
`4eb782f7cfed302e77dd216ed05f28807bb1b93f74ebc1eafdbf1bac7bd64bfa`.
Точный полный алгоритм остаётся
[t113-full-operator-design-20261030.md](t113-full-operator-design-20261030.md),
SHA-256 `5d1e069f3fe18f31a21c72c9b0abc41614ff8bfc00c3269f27b1f3cb596738ec`.

## Проверенное состояние и путь вызовов

Полностью прочитаны текущие `_backup_lifecycle`, `_runtime_operations`,
`_runtime_databases`, `_runtime_preflight` и найденные production callers.
Единственный production caller backup wrapper находится в coherent copy
под controlled export; он использует прежнюю пару digest/raw и повторно
сравнивает private register перед завершением копии. `_runtime_operations`
вызывается только внутри удержанного ExitStack `_runtime_preflight` для всех
работающих writers. `_runtime_databases` там же владеет owner/source и
одноразовыми role connections. `_runtime_main` печатает только результат
preflight, а не private bytes.

Backup reader уже исполняет действительные запросы под maintenance context,
проверяет точные closure/ledger RLS и access, закреплённые local catalog/access,
полный closure snapshot без LIMIT, v2 cases, требуемые категории, сроки и
отсутствие фактических остатков. Runtime пока проверяет файлы/guard/access
и schema/catalog, но не вызывает этот полный lifecycle reader. Проект закрывает
именно этот реальный пробел повторным применением прежнего алгоритма.

Прочитаны зависимости `private_bytes`, parser v2, `source_replay_accounts`,
withdrawn category coverage, local catalog/access, `_bound_runtime_file`,
`_physical_connection` и `_settled_sql`. Новая схема, права, получатели,
обход RLS, файловая копия или дополнительное DB-подключение не нужны.

## Принятый алгоритм и обязательные условия реализации

1. `_local_lifecycle(source, raw, *, root)` принимает именно неизменяемые bytes,
   непустые и не более10МБ. Используется прежнее SQL/policy/parser/replay тело,
   прежняя read-only repeatable-read transaction и тот же digest. Ядро не читает
   произвольный путь, не создаёт файлы и не принимает supplied PASS.
2. `_backup_lifecycle` остаётся wrapper: прежний `private_bytes` до core и
   повторное чтение/равенство **после закрытия** транзакции core до возврата
   прежней пары digest/raw. Требования0700/0600, single-link, owner и10МБ
   сохраняются; memfd не используется как обход `private_bytes`.
3. `_runtime_operations` после evaluate отдаёт прежний digest и actual bytes
   legal register из уже удержанного `_bound_runtime_file`. Runtime bound-file
   предел остаётся65536байт. Это внутреннее владение в памяти; sealed snapshots
   прежних readers не превращаются в новый файловый lifecycle вход.
4. `_runtime_preflight` отдельно сравнивает actual raw всех writers, сохраняет
   прежнее равенство operations digests и передаёт `register_raw` обязательным
   keyword, без default/callback. В operations proofs остаются только digests;
   raw не попадает в public result/JSON/журнал.
5. `_runtime_databases` после понижения source и проверки ролей вызывает core
   на той же физической source с `root=snapshot`. Вызов расположен вне внешней
   DB transaction: core сам открывает RR, его нельзя поместить в savepoint
   внешней read-committed transaction. Ни reconnect, ни owner вместо reduced
   source не допускаются. Yield proof добавляет только `lifecycle_sha256`.
6. После yield core выполняется снова в новой собственной RR transaction,
   digest сравнивается с первоначальным; прежние identity/catalog/access
   проверки сохраняются. Наружный operations context после закрытия DB
   перепроверяет файл, proc/bind identity, bytes, guard/access и свежесть.
   Исключение или отмена не возвращают успешный runtime result.

Это конкретизация имеющихся требований precode и полного алгоритма, а не
новые полномочия или ослабление границ. Порядок контекстов позволяет проверить
текущую БД, затем текущие удержанные файлы до успешного возврата.

## Уточнение значения accepted

В precode слово «accepted case» в проверках прочитано совместно с прежним
parser/replay договором. Исполнитель прямо подтвердил это уточнение до кода:
новый runtime negative case относится к **category disposition**.
Accepted category даже при пустой таблице не доказывает исполнение и даёт HOLD.
Failed/unknown/unresolved состояние также не принимается.

**Accepted account_closure не запрещается автоматически:** прежний source
reader допускает новый replay intent, если исходное completed/purge реально
подтверждено в БД, хронология и точный охват согласованы и остатков нет.
Это прямо проверяют `test_source_finalizer_result_allows_a_new_replay_intent_and_idempotent_applied`
и native source-lifecycle. Менять этот смысл при выделении общего ядра нельзя.
Позднее applied время остаётся наблюдаемым `late`, а исторические сроки —
`unverified`; новый replay не подменяет доказательство исходного purge.

## Scoped analyze

Использован ранее прочитанный `speckit-analyze`. Current prerequisites с
поддержанными `--json --require-tasks --include-tasks` подтвердили F273.
Before/after_analyze auto-commit hooks остаются отключёнными; изменяющие
состояние hooks не выполнялись. Полный новый analyze всей фичи не заявляется.

| Требование | Задача | Покрытие этой реализации |
| --- | --- | --- |
| FR-025, SC-006 | T113 | Текущее lifecycle состояние добавляется в runtime binding; admission/ready/T0 не ослабляются. |
| FR-034/035 | T113, T117/T118 в прежних границах | Backup wrapper сохраняет private bytes и поведение; core не заменяет полный backup/restore. |
| FR-036/050 | T109, T113 | Те же four-category until_decision, реальные catalog/access и отказ на неизвестном состоянии. |
| FR-038 | T113 | Actual bound raw и доверенный snapshot вместо внешнего digest/PASS; повторная сверка после yield. |
| FR-048 | T109/T111/T113 | Полный current closure/category coverage, сроки, результаты и фактические остатки читаются из БД. |

Непосредственно затронутых FR/SC8, покрыто8/8 существующими задачами.
FR-031/032/037 сохраняют отдельные current resource/access checks: lifecycle
digest их не заменяет и не выдаёт ready. Противоречий, дублирования,
непокрытых задач или новых продуктовых решений в этом scoped алгоритме нет.
Конституция III/IV/VI соблюдается: private bytes остаются внутри доверенного
владения, lifecycle пределы правдивы, high-risk ворота и верификация сохраняются.

## Минимальная необходимая матрица до приёмки кода

Текущие unit/native tests прочитаны; они ещё используют старые интерфейсы,
поэтому их исторические PASS не принимаются за проверку новой связи.
Нужен causal RED отсутствующих core/register_raw/lifecycle proof до source
правки, затем существующий полный focused-профиль, указанный precode.

- В прежних unit tests: actual raw передаётся без изменения; несовпадение raw
  writers отвергается даже при одинаковом stub digest; отсутствующий keyword,
  не-bytes/пустой/oversize core вход запрещён. Public proofs/result содержат
  только digests. Runtime65536 и backup10МБ не смешиваются.
- Native PG17 runtime: valid empty v2; неверная версия/malformed; withdrawal
  без полного category coverage; accepted/failed category; unresolved closure;
  applied category с реальными остатками; изменение closure metadata/остатков
  во время yield. Изменение БД проверяется новой RR, не старым snapshot.
  Прежние role/RLS/catalog/access отказы сохраняются.
- Native source lifecycle: общий core и файловый wrapper дают одинаковый
  digest на одной reduced source, без reconnect при closedDB false/limit0;
  исходная DB metadata восстанавливается в finally. Прежние непустые
  closure/purge/four-category и coherent-copy/replay consumers сохраняются.
- Повторная отмена должна затронуть реальное ожидание query/close и завершить
  все owned connections; имеющиеся physical-connection cancellation tests
  сохраняются. Один прежний body `pg_sleep` сам по себе не доказывает отмену
  на новой lifecycle query.
- Actual bound-file unit cases выполняются отдельно на Linux через уже
  имеющийся Python3.13 образ, в изолированном root-контейнере без сети,
  Docker socket и приложения, с source RO. Mac skips не заменяют этот proof.
  Такой план дополнительно подтверждён исполнителем; reviewer контейнер не запускал.

Это конкретные критерии последующего code review, а не утверждение, что новые
проверки уже пройдены. Нового framework, сервиса, CLI callback или дублирующего
набора не требуется. Ruff/governance/fragments/links/whitespace остаются.

## Контрольные списки и повторное чтение

Все117 вопросов четырёх списков прочитаны заново. Privacy CHK013/026/034–037,
security CHK004/010–015/022 и infra CHK006/008/013/014/025 сохраняют конкретные
договоры текущего основания, фактического удаления, хранения, отказа и
отдельного runtime/backup/restore допуска. Остальные вопросы не получают
новых категорий/получателей/ролей/пользовательских сценариев.
Отметки относятся к качеству требований, не к завершению реализации.

| Список | Checked | Unchecked | SHA-256 |
| --- | ---: | ---: | --- |
| requirements | 16 | 0 | `6755318d0b7a76a9f6439446ad42362272d43859cc6f4b3c045b5c36ad1ed9a2` |
| privacy-measurement | 45 | 0 | `8c390000a2da12cf719348d56c08dcb21d886aac98ba1a90ad3d5c41e141cb4f` |
| security | 27 | 0 | `57f082b0b90faf7a3302db0aa1b9aacd29948641e824578ca4f86eee4dee9cb8` |
| infra | 29 | 0 | `998175e297553cedac7f4d7b2829459fcb3f1b650b3b3b6d072e9065437bfa94` |

Заново прочитаны полные разделы полного алгоритма «Команды и доверие»,
«Владение ресурсами», «Полная копия после drain», «Initial», «Durable attempts
и completed manifest», «Local retention/resource/access и реальный gate» и
«Обязательные проверки и границы следующего кода», полные операции lifecycle/
закрытых файлов и текущие T113 дополнения plan/tasks. Требования FR-048/050
и зависимости reader/parser/source tests прочитаны непосредственно.
Прежние неизменные constitution/PRD/status/product-gates/spec/operations/
data-model и принятые plan/tasks/quickstart сверены по SHA по исключению F273.
Полное повторное чтение прежних PRD/истории статуса не имитируется.

## Контрольные суммы исходного состояния

| Источник | SHA-256 |
| --- | --- |
| activation_operator.py | `01c5117741d94135978096575ad834902c93bb0e9324e2f28da7b3c472e448c9` |
| restore_replay.py | `5beb31ebac95b05928f95489f93eeb59e9631a0ac67a37d2f9f821fd592a1118` |
| legal_basis_lifecycle.py | `4ba719383e35887d6efb9502317a7daea29e2e6b96b5d2374a03253689ea629a` |
| unit/test_activation_operator.py | `dd8591334cb098aec30a73b77107bfb3dd9e55b3cf159feb9a780dbd4de5673c` |
| unit/test_activation_restore_replay.py | `1d600d2cd044636e49579332718fcd9e9da7abd60b1dd7e666af011efcfec4e8` |
| integration/test_activation_product_drain.py | `31fdae19c3681a38531b43891af72b99650d407deff9578c8b8a71a21a18c862` |
| integration/test_activation_restore_replay.py | `7fd4b6ac7483585f7be7a96f946ff950626eec46fa0383f53f8964deff2c70e9` |
| plan | `b7b5e34b9fc3129c2741ee66f46f9da02789e396a5d751be5e06ee798d02cb68` |
| tasks | `b720051debf1f555d18ae8d716d8840ab83574260f2e3670de80172a33f3ee6b` |
| quickstart | `3a4e842f68fa862e614985dfab0ea89e4712b2b67cceae296622c66319917f7b` |

## Ограничения

Полные installed jobs, shell graf-local, единый ready receipt, верхние
initial/backup/verify/actual-restore/resume, CD/rollback/daily и рабочая
приёмка остаются впереди. `full_preflight_not_implemented` и
`activation_recovery_unverified` не снимаются. T112/T113/#7804, рабочие
T0/ready/IP/получатели, выпуск и коммерческие AC01–AC06 остаются открытыми.
Source lifecycle digest не доказывает provider deletion или исторические сроки.

Проверяющий не запускал tests/SSH/БД/контейнеры/production/Dev и изменил
только этот отчёт. Source/spec/plan/tasks/Git/GitHub/checklist marks не менялись.
Отчёт после записи перечитан целиком, итог checked/unchecked пересчитан.
