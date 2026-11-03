# F232 T024–T026: текущая независимая проверка

Дата: 2026-10-19. Reviewer: отдельный агент f263_performance_review.
Ветка: `codex/232-dev-launch-validation`.
HEAD основы: `c6c5441c930b8c1ecffed6de9b80773aa0e757e5`.
Путь проверки: **Active Spec Kit slice**, высокий риск управления установленным
macOS приложением. Проверяются незакоммиченные изменения T024/T025;
исходный исторический выпуск не переаттестуется.

**Решение: APPROVE текущей локальной реализации. Новых блокирующих замечаний:0.**
Три reviewer-owned списка: **16 + 21 + 8 = 45 checked / 0 unchecked**.
Это подтверждённое качество требований, отдельно от готовности установленного
Dev, текущего PR/CI и закрытия #7209. T024 локально выполнена; T025/T026
не отмечались этим reviewer и остаются в текущем tasks открытыми.

## Источники и способ проверки

Прочитаны текущие spec, plan, tasks, quickstart, packaged-startup contract,
все три checklist, прежние design/requirements/implementation отчёты и
validation/dev-launch-20261016.md. Применены AGENTS, guidance index,
spec-kit-flow, local-development, product-gates, constitution7.1.0 и текущие
правила PR/release validation. Навык code-reviewer использован для чтения diff.

Прочитан весь diff harness, lifecycle helper, packaged validator, README,
новый test_dev_launch_validation.py, changelog. Прослежены все общие
launch/terminate callers, state_lock и семь остальных изменяющих CLI входов,
startup markers, signing caller и фактический upload boundary release-artifacts.
Новый тест и часть specs пока не отслеживаются Git; они прочитаны по фактическим
файлам, а не только через git diff.

До моих разрешённых примечаний checklist **18/18 файлов** самостоятельно
совпали с F232-validated-files.json от16.10.2026. Текущий
baseline-manifest-recheck.json даёт тот же результат. Read-only сравнение
основы с локальным origin/master не показывает изменений затронутых runtime,
test и README путей. Сеть/GitHub не использовались: свежесть удалённой основы
этим reviewer отдельно не подтверждалась.

Reviewer не запускал тесты, Swift/helper, shell fixtures, приложение, Docker,
сборку, GitHub или release. Прочитанные результаты исполнителя и прежнего
reviewer ниже прямо отделены от самостоятельно выполненного разбора XML.

## Проверка текущего потока

| Граница | Вывод по коду и проверкам |
|---|---|
| Явный вход | validate-app-launch требует --live и принятый live root; операция целиком находится под общим state_lock. Работающий Dev без --restart-idle-app отклоняется до lifecycle. При неизвестной занятости actual не выполняется. |
| До первого изменения | Проверяются schema/rollback/recovery, active status/live pointer, clean tooling HEAD и committed bytes четырёх управляющих файлов. Bytes сравниваются через hash-object --no-filters с объектом exact SHA, поэтому clean status под индексными флагами недостаточен для обхода. |
| Установленный bundle | _validate_launch_bundle требует единственный штатный путь без symlink, bundle ID, channel и installed source SHA из manifest, полный tree digest, codesign --verify --deep --strict, signer/requirement/entitlements. SHA инструмента и приложения намеренно различаются. |
| Обычный запуск | Переиспользуется _launch_dev_app через open -n; добавлен только log_directory через open --env. HOME/Application Support/defaults/cookies/TCC не подменяются. Fresh-log запуск отказывает, если процесс уже работает. |
| Native identity | Helper отбирает точные bundle ID/path и требует ровно один живой процесс с launchDate. Identity имеет PID:launchDate. При identity-bound terminate native helper заново сравнивает токен до graceful terminate. Несовпадение не разрешает завершить заменивший процесс. |
| Наблюдатель | --observe-installed-dev проверяет identity до/после, 50 циклов kill -0/ps/sleep0.1 без zombie, оба полных имени событий в новом журнале. В этой ветви нет launch, terminate или cleanup установленного процесса. |
| Readiness | app_launch_finished расположен до вызова показа окна и сам по себе недостаточен. app_main_window_presented записывается после AppKit ordering/activation и проверки isVisible; неудача пишет другое событие. Regex в общем проверочном коде отвергает суффикс _fake. |
| Квитанция | До первого quit/start выполняется долговечная _write_json recovery receipt; после запуска добавляется owned identity. Необработанное завершение контроллера оставляет квитанцию. Она не означает успешного восстановления. |
| Восстановление | После успеха и обработанной ошибки останавливается только подтверждённый owned процесс. Его журнал удаляется после остановки; прежний running открывается обычным helper без временного log override. Ошибка восстановления даёт FAIL с сохранением квитанции/используемого каталога, forced termination отсутствует. |
| Общий отказ | Проверка recovery receipt находится под flock до yield state_lock; все build/promote/rollback/recover-schema/rehydrate/prune/reset-data используют этот guard. Семь отрицательных случаев запрещают достижение adapter и сохраняют квитанцию. Status остаётся чтением и показывает blocked. |
| Финальная сверка | После восстановления повторяются clean tooling/bytes/bundle/signature и active manifest. Ошибка проверки не превращается в PASS даже при успешно восстановленном running/stopped. |
| Релизный путь | Обычный release CLI по-прежнему принимает абсолютный GRAF.app, запускает точный binary как direct child, использует прежние временные окружения, ≥5s и оба маркера, очищает только своего ребёнка. Dev-ветвь не участвует в signing upload. |

Фактический signing путь не ограничивается наличием STARTUP_VALIDATOR:
release-artifacts.py перед upload_missing после public verify-only/check_stage
вызывает прежний CLI для arm64 и x86_64, затем повторяет stage identity и
clean source. Текущий diff не меняет signing/release-artifacts callers.

Прежние findings остаются устранёнными:

- **P1 recovery guard:** отказ вынесен в общий state_lock; остальные изменяющие
  команды не обходят оставшуюся app-launch-validation-recovery.json.
- **P2 idempotent promote:** README честно говорит, что живой backend и installed
  bundle могут дать idempotent success без запуска остановленного приложения.
  После внезапного завершения контроллера при прежнем running восстановление
  остаётся незавершённым, квитанция сохраняется. Поддержанной отдельной команды
  аварийного восстановления в этом срезе нет; инструкция не предлагает обход.

Эта ограниченная отказная семантика не является полной автоматической
crash-recovery приёмкой. Новый код для расширения области без подтверждённого
недостатка не требуется. Старые независимые воспроизведения сохранены в прежнем
implementation report; в текущем ревью повторные runtime пробы не выполнялись.

## Текущий журнал: независимый пересчёт

Прочитаны current-governance.xml/log и selected-tests.json из внешнего реестра
f232-current-preflight. Самостоятельный разбор XML даёт **201 testcase,
201 различных (classname,name), 201 PASS,0 failure,0 error,0 skipped**.
XML suite36.637s, общий вывод pytest36.85s. Это один текущий набор15 файлов,
а не сумма исторических перекрывающихся прогонов.

| Файл | PASS |
|---|---:|
| test_dev_compose_contract.py | 9 |
| test_dev_harness.py | 23 |
| test_dev_launch_validation.py | 41 |
| test_dev_live_smoke.py | 2 |
| test_dev_migration_preflight.py | 8 |
| test_dev_promotion_transaction.py | 3 |
| test_dev_rollback.py | 1 |
| test_dev_runtime.py | 6 |
| test_dev_runtime_contract.py | 3 |
| test_dev_runtime_identity.py | 5 |
| test_dev_runtime_isolation.py | 3 |
| test_dev_safety_guards.py | 2 |
| test_dev_schema_transition.py | 51 |
| test_dev_state_retention.py | 9 |
| test_release_artifacts.py | 35 |
| Всего | 201 |

test_dev_schema_restore_docker.py намеренно не выбран. Отсутствие Docker suite
не называется его PASS. Новый файл проверяет настоящую оркестрацию с подменённым
lifecycle/signature/tooling и настоящий shell observer над искусственными
процессами. Native NSWorkspace/codesign/LaunchServices installed acceptance
этими тестами не исполняется.

Исторические журналы16.10 прочитаны отдельно: negative-first2FAIL показывают
отсутствие новой операции/parser; observer-red даёт ложный PASS события _fake,
который обнаруживает отрицательный тест. Текущий regex и случай prefix это
закрывают. Прежний packaged launch fixtures журнал — PASS; signing custody —
PASS на disposable-public fixture, staging simulations явно SKIP без disposable
app. Это исторические журналы неизменных bytes, не новые собственные прогоны
и не новая публичная или установленная приёмка.

До завершения ревью поступили и прочитаны дополнительные текущие журналы19.10:
packaged-launch — PASS; signing-custody — PASS с тем же явным SKIP staging без
disposable app; Ruff — All checks passed; development-process — OK вместе с
agent-context/changelog-fragments/legacy-impact. Исполнитель отдельно сообщил
exit0 swiftc typecheck и sh syntax. native-typecheck.log пуст, поэтому сам по
себе этот файл не доказывает exit code. Reviewer эти команды не повторял.

## Основания каждого пункта checklist

Q01–Q16 — порядок исходных строк requirements.md; R001–R021 — CHK в
release-safety.md; D001–D008 — CHK в dev-launch.md. Отметки означают качество
требований; исходный release scope и текущий Dev scope различаются явно.

| Пункт | Текущее достаточное основание |
|---|---|
| Q01 | Spec описывает результат безопасного запуска; алгоритм и инструменты вынесены в plan/contract. |
| Q02 | US1/US2 описывают восстановление доступности продукта после сломанного обновления. |
| Q03 | Пользовательские сценарии объясняют обычный запуск/обновление; необходимые технические обозначения задают точную границу. |
| Q04 | В spec присутствуют истории, приёмка, edge cases, FR, SC, assumptions и исключения. |
| Q05 | NEEDS CLARIFICATION нет; новая граница обычного Dev и операторское предусловие явно уточнены. |
| Q06 | FR-001–020/SC-001–008 задают проверяемые результаты и отказы, неизвестная занятость не PASS. |
| Q07 | Минимум5s, число запусков, exact SHA/bytes, unique PID/date и restoration измеримы. |
| Q08 | SC задают наблюдаемый результат; детали observer/lifecycle находятся в плане и контракте. |
| Q09 | US1–US3 и installed дополнение охватывают обычные и отказные сценарии. |
| Q10 | Ресурсы/архитектуры/чужой процесс дополнены replacement/refusal/recovery/dirty/source mismatch. |
| Q11 | Out of Scope/FR-003/015–020 сохраняют узкую область без capture/data/backend policy изменений. |
| Q12 | Assumptions/quickstart называют healthy predecessor, hardware, signing и текущую доступность/idle Dev как предусловия. |
| Q13 | Исходные FR связаны с US/SC; FR-015–020/SC-008 с T024–T026. |
| Q14 | Запуск/ручной repair/Sparkle и текущая установленная проверка имеют отдельные пути. |
| Q15 | SC определяют целевые измеримые результаты; строка checklist не трактуется как уже выполненная installed acceptance. |
| Q16 | Выбор конкретного observer/locks/helper остаётся в plan/contract, а не расширяет продуктовую спецификацию. |
| R001 | US1/US2/FR-011 сохраняют manual repair и Sparkle с healthy predecessor. |
| R002 | FR-001/002/004/contract различают packaged, SwiftPM и missing resource. |
| R003 | FR-008/011 и quickstart сохраняют Developer ID/notarization/stapling/Gatekeeper/Sparkle. |
| R004 | FR-010/012/013/SC-005/006 требуют exact SHA и согласованные final bytes всех опубликованных артефактов. |
| R005 | Resource resolution1–4 отделяет packaged lookup от Bundle.module и Swift trap. |
| R006 | FR-002/003/Out of Scope не добавляют registry default или новую capture policy. |
| R007 | FR-005/006/release contract требуют owned direct child; Dev observer отдельно не присваивает владение. |
| R008 | FR-009/010/publication ordering сохраняют final stapled bytes и appcast-last. |
| R009 | SC-001 и release CLI задают10 запусков и минимум5s; Dev имеет отдельную SC-008. |
| R010 | SC-004/quickstart требуют отдельную оценку arm64/x86_64, недоступный slice не считается PASS. |
| R011 | SC-005/006 и quickstart требуют повторное скачивание/100% bytes/version/Sparkle/exact SHA. |
| R012 | FR-006/contract перечисляют immediate exit/malformed/missing/ambiguous identity как отказы. |
| R013 | FR-003 сохраняет Record/Stop, видимость и три состояния автозаписи; ordinary Dev не обещает подавить фоновые действия. |
| R014 | US1 AC3/SC-003 задают безопасное degraded поведение при отсутствующем baseline. |
| R015 | FR-010/SC-005 не допускают несовпадения public checksum/artifact. |
| R016 | FR-013 запрещает перезаписывать старый сломанный tag/assets. |
| R017 | Plan/quickstart оставляют Apple/hardware preconditions и недоступные проверки открытыми. |
| R018 | FR-012/contract/README ограничивают публичные доказательства метаданными; raw journal/local recovery paths не публикуются. |
| R019 | Исторические CalVer допускают повышение без переписывания .1; five-second/appcast-last согласованы; Dev не создаёт новый продуктовый релиз. |
| R020 | Исходный Out of Scope и текущий FR-020 исключают backend deploy и product policy изменение. |
| R021 | FR-014/SC-007/T020–T022 сохраняют независимость fixtures от feature pointer и занятых tags. |
| D001 | FR-015/plan/contract/quickstart требуют один установленный Dev через harness без копий/ссылок/обхода. |
| D002 | FR-016 требует clean tooling, live manifest/recovery, bytes/signature и раздельные source SHA. |
| D003 | FR-017 честно называет постоянные данные/настройки/фоновые действия; изоляции через HOME нет. |
| D004 | FR-018/quickstart определяют непосредственный idle, explicit restart, неатомарность и graceful refusal. |
| D005 | FR-019/contract требуют PID/date, fresh log, минимум5s, два новых события и отказ при замене процесса. |
| D006 | FR-018/019 задают running/stopped restoration; ошибка блокирует PASS, используемый журнал сохраняется. |
| D007 | FR-020/contract сохраняют release direct-child/signing и запрещают подменять ими installed proof другой фичи. |
| D008 | SC-008/T024–T026 задают test-first/review/analyze/sync, разрешённый commit, actual clean-checkout и exact-SHA/base CI. |

После разрешённых reviewer примечаний все три файла вновь перечитаны:
requirements16/0, release-safety21/0, dev-launch8/0. Ни одна отметка не добавлена
или снята; добавлены только ссылки на текущий отчёт.

## Граница интеграции с F224

**Высокий приоритет до слияния объединённого результата:** F224 PR#7676 тоже
меняет scripts/dev-harness.py и именно state_lock/принадлежность общего root.
Текущее APPROVE относится к прочитанному F232 snapshot и не переносится на
будущий объединённый код. Если F224 принимается раньше F232, обновление F232
на принятую основу должно сохранить origin/binding, прежний lock inode,
ownership recheck/порядок записи marker из F224 **и** отказ по launch recovery
receipt под полученной общей блокировкой из F232. Ни одну защиту нельзя потерять
при разрешении конфликта. Для объединённого diff нужны совместные относящиеся
к ним проверки и новые exact-SHA/base PR checks.

Это прогнозируемая область совместимости, а не найденный или воспроизведённый
runtime RED текущего F232. Реальный объединённый код в этом ревью не создавался
и не исполнялся; новая issue или реализация для гипотетического дефекта не нужна.

## Оставшиеся действия и предел решения

Историческое ожидание отдельного разрешения на commit в документах16.10
устарело: по текущему поручению действует общее разрешение на проверенный
commit/PR. Reviewer нового согласия не запрашивает и сам commit не делает.
T025 завершает владелец после текущих process/checks и оформления. T026 и
#7209 остаются открытыми до actual validator из чистого разрешённого commit,
свежей проверки idle, восстановления исходного состояния, status/smoke,
актуальных governance-fast/macos-pr/pr-metadata точного PR SHA/base, принятия
изменения и подробного комментария по исходным критериям.

Установленная занятость Dev неизвестна; это ревью не даёт оснований его
запускать/останавливать сейчас. Обычные capture/данные/TCC/подпись не менялись.
Слияния удерживаются до конца согласованного выпуска F280. Этот вывод не
подтверждает его текущий run, frozen release-full, public artifacts или deploy.

## Контрольные суммы

SHA256 текущих18 файлов после разрешённых примечаний reviewer. Новый report
не хеширует сам себя. Новый commit требует собственных CI доказательств.

```text
74fe2bd3da8bfd3c068740642b40e0aaf625bdc9b28ad659163bc94b1fb62520  apps/macos/Scripts/dev-app-lifecycle.swift
81a5af77b9b711ff9012c4176892193411ceddc6469473e833c6ab28c2d74b67  apps/macos/Scripts/validate-packaged-app-launch.sh
4ad855347416edcc75db5646c4b4502722512da360a405c0524019a8a8bf1cb3  changes/unreleased/F232.yaml
fbf30282ece10c48ae48d18efa5df8917228243813fd1f87d17df06a90396c0b  infra/dev/README.md
9d0d8da839baec9e25dd84788df4621ae6d98ae3e207ca87fb2d74299836c24a  scripts/dev-harness.py
06d06b491654b2d351e41cf2bd14650239fe68d288e813e851c0cc2dddca452c  specs/232-macos-resource-bundle-hotfix/checklists/dev-launch.md
1f02d361bc2dc9bc6e34f5c65b67b3e8d71872d3afbd5728313d96f29df14d64  specs/232-macos-resource-bundle-hotfix/checklists/release-safety.md
cff90f90c62392c73bb889561f5ea8e6ee3f837443c1f7e8715da4ef25cb1f41  specs/232-macos-resource-bundle-hotfix/checklists/requirements.md
a3f82b9039a7e04f3506c1f6752736207c480cbafca7ad7e4457897504c412f7  specs/232-macos-resource-bundle-hotfix/contracts/packaged-startup.md
9349dca1d9924f4fab4f3391855770e61348b05113b91b954c2a6b5d6a8d2935  specs/232-macos-resource-bundle-hotfix/plan.md
f91053956cf79be8d2b981b2566b0b69ec02fe254cbde3d9a2ae962fd5614f80  specs/232-macos-resource-bundle-hotfix/quickstart.md
14a0474f291a55a77c090642acdeb89f533d6cacfa236b7a7d965ff274d0dbed  specs/232-macos-resource-bundle-hotfix/spec.md
424d9c40889eeb9bf4ab547791de84e72e4e5e96a197524dde6cc6091cd85d96  specs/232-macos-resource-bundle-hotfix/tasks.md
7e52c5dabe4e8c2d81efa63acba1d3250fc6a6f161b297be70d2c7280da9406e  specs/232-macos-resource-bundle-hotfix/validation/dev-launch-20261016.md
404754cc31b628902769dfa3666db5e783dec05e776929ec8a09f42bbb48200b  specs/232-macos-resource-bundle-hotfix/validation/review-dev-launch-design-20261016.md
95217b2dae4e8c6b171630d60a6a1c6548b720916f6b1161d3600f58e256910c  specs/232-macos-resource-bundle-hotfix/validation/review-dev-launch-implementation-20261016.md
8e8a7706d8f43157450f26f94fb84e998d8ceac08e5e162679c481a264eb3b29  specs/232-macos-resource-bundle-hotfix/validation/review-dev-launch-requirements-20261016.md
e76ba1082ba83384a37469cf09815fa2a94206149db99b1e7dcf7c20034f1c3d  tests/governance/test_dev_launch_validation.py
```

Контрольные суммы текущего внешнего реестра:

```text
77f5002a6178e85724cbdae54d40dcc24ce6f7ff1ea2d1640bf9682913b49d19  baseline-manifest-recheck.json
903da9fce6fa42c514efadbae40f30d53d7bc5e31e06afe76e88e93ff8506dd7  selected-tests.json
359c75ef68d1dc56e76b2cb46135b0b337a6dd628eaf9aa1627999e5001567cc  current-governance.log
5c07954c4da78769f4fbc4215efdc39b20ed67a8372004d41e39674c2509f912  current-governance.xml
f539f592bb03aeff6419a6e1acb0b20272581c35ec17d48916343dad06879a9c  packaged-launch.log
9abbb0b055c438a7e749b38e5f80215c76714bc9f202bda2bc377384f72ec026  signing-custody.log
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855  native-typecheck.log
82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18  ruff.log
628cf4ac4ded785bb84301e2d3186036ec5a4c8c4b7aace6b5d8e7d943d694fb  development-process.log
```
