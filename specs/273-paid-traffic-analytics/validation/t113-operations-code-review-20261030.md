# T113 — независимое ревью кода operational files, 30.10.2026

Вердикт: **SCOPED PASS указанным байтам; P1=0, P2=0**. Конкретных
воспроизводимых дефектов этих приоритетов в принятом участке F273/T113/#7804
не найдено. Полоса продукта — `high-risk-product`; способ этого ревью —
чтение кода, требований и существующих доказательств с единственной записью
настоящего отчёта. Полный допуск, T113/T112 и рабочее включение остаются открытыми.

База и HEAD: `0817654a05a84d9d8570ee774cdb7b4559900954`, ветка
`codex/f273-local-period-20261029`. Прочитан фактический diff рабочей копии
к этой базе: три файла кода/тестов и изменения `changes/unreleased/F273.yaml`,
`docs/growth/organic-growth-plan.md`, `tasks.md`. Прочитаны полные изменённые
функции, их места вызова и применимые функции чтения, Settings, проверки
процессов/путей/прав, удержания FD, policy и закрытия DB-соединений.
Неотслеживаемые design review и preflight исполнителя прочитаны отдельно.
Применён `code-reviewer` с ограничениями владельца этого задания.

## Проверенные байты

| Файл | SHA256 |
| --- | --- |
| `apps/server/src/twobrain_rec_server/product_analytics/activation_operator.py` | `33fb35d7975feef88e9ea8617afd4c386673239b340001d14f7f5d0a3f0a06b3` |
| `apps/server/src/twobrain_rec_server/product_analytics/provider_readiness.py` | `8fe369afc4d8720c372d94cbaaa84ddbc1d1e8649cfec987c387b80ea4939a77` |
| `apps/server/tests/unit/test_activation_operator.py` | `ab3cd09989499d21b16d0d975f197e8152f64c997a355ea1328db98a69dee317` |

Все три суммы совпали с окончательными суммами владельца и Linux final JSON.
Исходный проект `.dev/growth/t113-operations-precode-20261030.md` имеет SHA256
`3249d34bd1bd07c495dbf79f7bc59d5bf71f72ed8d637e28cdd9599803f29006`;
[проектное ревью](t113-operations-design-review-20261030.md) —
`0c33c662c4188f4b07a4c5680ea4a47ea06bba6e00ea01d2bc2db61979c13209`;
[отчёт исполнителя](t113-operations-preflight-20261030.md) —
`68e1b63a4e77ed3d0dbd32e8f894513e563c0829fa70d8c9c1bbfe5c5c0d5000`.
Прежний полный проект оператора подтверждён по SHA256
`5d1e069f3fe18f31a21c72c9b0abc41614ff8bfc00c3269f27b1f3cb596738ec`.

## Основания вердикта

1. **Actual Env, mounts и процесс.** `_runtime_operations` (operator:1817)
   получает среду исключительно через `_runtime_environment(row)`. Все четыре
   пути определяются из неё штатными helpers/defaults. Settings построены
   `_runtime_settings` из actual Env без host dotenv/settings fallback.
   `_runtime_preflight` (operator:2464) связывает running writers с actual
   inspect, image/source и `_process_identity`: UID/GID100:101 во всех четырёх
   полях, maps без remap, start time и supplementary groups. Identity повторяется
   при входе/выходе operations и в финальной runtime-проверке. Корень процесса
   открыт через `/proc/PID/root`, его dev/inode сверяются при выходе.

2. **Directory/file FD и замена пути.** Явный `directory_bind=True` в
   `_bound_runtime_file` (operator:1733) требует единственный RO bind предка
   logical file; exact-file и пересекающиеся mounts для этого режима отклоняются.
   Source вычисляется из actual Source и относительного пути. Source и proc-root
   directory FD, оба file FD и sealed memfd живут в `ExitStack` до выхода
   соответствующих контекстов. Directory identity включает dev/ino/uid/gid/mode;
   mtime/size каталога от соседней записи сами по себе не запрещают результат.
   Сверяются удержанные FD, текущий source path и заново открытый proc-root path.
   Поэтому удержанный старый directory bind не подтверждает новый host directory.
   File identity дополнительно включает link count, size, mtime/ctime; байты
   обоих файлов повторно сравниваются. Замена или изменение leaf даёт HOLD.

3. **No-follow, ACL и чтение процессом.** Source должен быть абсолютным и
   каноническим, без ссылок и `..`; protected ancestors проверяются штатной
   `_settings_source_ancestors`. После разрешённого proc-root перехода обход
   использует `dir_fd` и `O_NOFOLLOW`; промежуточные каталоги требуют права
   прохода actual UID/groups. ACL отвергаются у каталогов и файлов. Operational
   leaf — обычный single-link файл owner0/1001, mode0600/0640, с обязательным
   групповым чтением для actual процесса; следовательно, недоступный ему 0600
   не принимается. Ограничение64KiB, bounded `pread(65537)` и равенство размера
   прочитанным байтам сохранены. Мемориальные снимки запечатаны от записи,
   усечения и роста. Старые вызовы Settings и owner-secret не передают новый
   флаг: default по-прежнему требует exact-file bind; исключение пустого
   optional-provider placeholder также осталось прежним.

4. **Штатные legal/access/guard readers.** Они получают explicit environ
   с четырьмя проверенными снимками. Требуются валидный `local_only`, enabled,
   legal/disclosure, доступный реестр без file_errors и без withdrawal уровня2,
   успешный `parse_disposition_cases(..., now=aware UTC)` формата v2. Access
   проверяет актуальность, reviews, минимум двух операторов и MFA каждого.
   Guard сохраняет recorded/sample age `0 <= age <120s`, отказ будущего времени,
   budget deadline и latch. В `runtime_guard_blockers` (provider:69) новый
   keyword выбирает только protection path: `None` сохраняет прежний default,
   явные пустой/плохой пути дают blocker без переключения на default. Проверки
   содержимого и защёлки не ослаблены; прежний readiness caller параметр не задаёт.

5. **Installed guard и закреплённый источник.** Expected digest вычисляется
   из прочитанных installed bytes и обязательно подтверждается равенством
   скрипту `snapshot/infra/scripts/posthog-runtime-guard.sh`; произвольного
   expected из Env недостаточно, противоречащее значение отклоняется.
   Installed leaf требует root0755, regular/single-link, отсутствие ACL/ссылок,
   ненулевой размер до64KiB и root ancestors без group/world write. Его FD,
   identity и bytes удерживаются и перепроверяются, как и snapshot bytes.
   Все три digest access record должны совпасть с вычисленным expected.

6. **После await и cleanup.** `evaluate()` вызывается перед yield и повторно
   со свежим временем при выходе `_runtime_operations`. Контексты остаются
   открытыми через все финальные await inspect/process/network/release/head/
   policy и закрытие физических DB-соединений. При выходе дополнительно
   проверяются исходные files/directories/process identities и bytes; даже
   обычное обновление guard в этом окне требует нового полного запуска.
   Result вычисляется внутри контекстов, но возвращается только после их
   успешного выхода и проверки исходного monotonic deadline (operator:2639).
   Ошибка reader/cleanup/identity/time и отмена не превращаются в verified.

7. **Все running writers и отсутствие мутаций.** Каждая работающая служба
   из `WRITERS` получает собственные Settings и operations context. До DB
   требуется ровно одно значение среди всех operations proofs, содержащих
   identities/content digests четырёх файлов и guard digest. Разные корректные
   копии отклоняются. Actual mounts дополнительно входят в общий runtime proof.
   Наружу остаются четыре прежних поля; operational details входят только в
   `runtime_sha256`. В добавленном пути нет записи runtime/DB/state, изменения
   switches, запуска/остановки служб, ready/T0 или снятия общей блокировки.

## Прочитанные доказательства исполнителя

Собственных запусков тестов, Docker, SSH, приложений, production root operator
или выпуска в этом ревью не было; агенты не создавались. Ниже результаты
существующих артефактов исполнителя, прочитанных как доказательства с указанными
пределами; сценарии прочитаны, но не исполнялись.

| Артефакт в `.dev/growth/` | Результат и предел |
| --- | --- |
| `t113-operations-profile-20261030.log` | 524 passed / 38 skipped / 2 warnings; до форматирования imports/теста. |
| `t113-operations-unit-final-20261030.log` | 395 passed / 38 skipped / 2 warnings; окончательные затронутые unit. |
| `t113-operations-native-final-20261030.json` и `t113-operations-native-20261030.py` | 70 Linux passed: пять извлечённых tracked функций,32 новых случая и38 прежних. Сценарий сравнивает before/after hashes всех трёх файлов; final JSON соответствует окончательным суммам. FD/memfd/ACL настоящие, process metadata подменены. |
| `t113-operations-bind-native-20261030.py` и `.json` | Настоящий собственный worker100:101 с actual RO directory bind; root runner входит в его PID namespace с SYS_PTRACE. Process/bind/ACL/memfd функции без подмен, Settings учебные. Normal PASS → file replacement HOLD → stale directory bind HOLD → repeat PASS; число FD одинаково, собственные ресурсы удалены по отчёту. |
| `t113-operations-red-20261030.json`, `t113-operations-guard-red-20261030.log` | 32 AttributeError отсутствующей функции,38 прежних Linux passed; отдельно отсутствующий keyword. Это RED отсутствующего механизма, а не32 доказанных обхода. |

Прочитаны все32 новых сценария и изменённая полная функция runtime preflight
test: отказ operations, несовпадение proofs и поздний cleanup, включая сохранение
проверки охвата всех running writers и отсутствия mutating Docker-команд.
Прочитаны прежние Linux Settings/memfd/FD/ACL функции, извлекаемые native-сценарием.
Эти артефакты достаточны вместе с чтением кода для узкого вердикта; они не
подтверждают полный Compose/host/installed package или рабочую приёмку.

## Требования,117 вопросов и неизменность markers

Повторно прочитаны все117 действующих вопросов четырёх списков. Маркеры
не менялись; их суммы совпадают с проектным ревью. Это существующие отметки
качества требований, не117 принятых проверок реализации.

| Checklist | `[x]` | `[ ]` | SHA256 |
| --- | ---: | ---: | --- |
| requirements | 16 | 0 | `6755318d0b7a76a9f6439446ad42362272d43859cc6f4b3c045b5c36ad1ed9a2` |
| privacy-measurement | 45 | 0 | `8c390000a2da12cf719348d56c08dcb21d886aac98ba1a90ad3d5c41e141cb4f` |
| security | 27 | 0 | `57f082b0b90faf7a3302db0aa1b9aacd29948641e824578ca4f86eee4dee9cb8` |
| infra | 29 | 0 | `998175e297553cedac7f4d7b2829459fcb3f1b650b3b3b6d072e9065437bfa94` |
| Всего | **117** | **0** | Без изменения markers |

По прямо разрешённому владельцем F273 исключению прочитаны затронутые целые
разделы требований и зависимостей: spec Functional Requirements и дополнительные
FR; plan «первый локальный период» и «Полный оператор»; operations guard/resource,
retention/access/readiness, lifecycle/local period; activation-milestones local
period/settings/readiness/locks; quickstart degradation/local period; T112/T113
tasks и текущие связанные runtime/settings/policy/DB/operations примечания.
Остальные прежние baseline подтверждены по хешам; полное повторное чтение
неизменных PRD и истории статуса не заявляется.

| Документ | Текущий SHA256 |
| --- | --- |
| constitution | `7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8` |
| PRD | `0f3ccfcfa60062bb0aae6802eeb0012056a635a30cb9f46f54d1992d0b4f57c2` |
| current-product-status | `25b7f383be47c7160da8e852006ff82019f30a5f9c371fc30baa79238649cd16` |
| product-gates | `9f7072c879490d250053cb7397ad6b9b68fdcde17bdf9367ed874a41e450b5f5` |
| spec | `45bcc14f170951e99813d6aeb0eddbbb413dd64f89cf410da256b6d5e30986b2` |
| plan | `02f4b52274c61fdf69f01415448a28d9509a1c12274a09d5a7382d3fc3db1b19` |
| tasks | `16330cb7c12a3ae7152f476b8c8ab3ed25754a3e87632cb1898c4079a5997690` |
| quickstart | `5bde6a5f388a03b6df1440fca32429f49bd458fdf9203fdc8df880352d249fea` |
| operations contract | `7d68aa7dc06b170508cd8b2858ede6e3e929b2e7155cd03b0895e715cb2b3abb` |
| activation-milestones contract | `9898007a0e87400246f8c95b899dd807fab0424472143e15338429873982f3f9` |

Зависимости access/lifecycle и неизменные guard/bootstrap/Compose совпали
с хешами проектного ревью. Статусные изменения и fragment сохраняют открытыми
T113/T112/AC01–AC06; tasks не отмечает их выполненными.

## Сохранённая граница допуска

Compose legal/access/guard mounts/env всех writers ещё предстоит согласовать.
Отсутствие actual bind сейчас правильно даёт HOLD: host default не подставляется
вместо container proof. V2 parse подтверждает формат и применимые withdrawals;
он не исполняет lifecycle cases и не проверяет сроки исполнения или остатки.
Полные local-retention SQL/schema/trigger/jobs/config, четыре категории/таблицы,
retained-source lifecycle/remnant queries, верхние initial/backup/verify/restore/
resume/CD, T112 и рабочая приёмка остаются открытыми. Сверка одного installed
script не принимает все installed jobs/config и не доказывает live access.

UID1003 не подтверждён: bootstrap сохраняет доверенную группу `{1001}`.
`full_preflight_not_implemented` и unconditional `activation_recovery_unverified`
сохранены. SCOPED PASS не снимает общие HOLD, не разрешает production root
operator, новый T0/ready, аналитику/IP/получателей или выпуск.

Перед передачей отчёт полностью перечитан, исходные суммы и markers сверены
повторно. Единственная запись проверяющего — этот новый отчёт; его итоговый
SHA256 сообщается отдельно. EOF содержит один перевод строки без пустой строки.
