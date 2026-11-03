# F290/T006 — независимая проверка инвентаризации, 01.11.2026

**SCOPED DOCUMENTARY ACCEPTANCE PASS** по предоставленным датированным
доказательствам. Открытые замечания в границах T006: CRITICAL 0, HIGH 0,
P1 0, P2 0. Это приёмка учёта и сохранности, без приёмки политики или
реализации ротации. Исходная F290 — active Spec Kit / high-risk infrastructure;
этот срез меняет только документацию и не выполняет production-действий.

Ветка `codex/290-retention-disposition`, исходная основа
`3aa38ce2568e5bb89c8a5a763c19ae51d5f82d29`. Активная F290 подтверждена
feature.json, веткой и tasks.md. На этапе первичного ревью локальный указатель включал T006/T007;
поручение этого ревью и допуск ограничены T006. Разрешена запись только
двух reviewer-owned списков и этого отчёта; чужие изменения не менялись.

## Источники и способ проверки

Перечитаны все20 исходных пунктов, spec/plan/tasks/quickstart/research/
data-model, stash-disposition.md и release-v2026.10.16.6.md. Применимые
AGENTS/guidance и конституция7.1.0 сверены по SHA-256 с полным чтением
в этом диалоге; их содержание не изменилось. Условия FR005/006/009,
различие inventory/design/implementation и запрет потери чужой работы
сохранены. Отметки требований не превращены в доказательство исполнения.

Прочитаны три JSON-доказательства, безопасная receipt.json и исходник
оператора inventory-readonly.py. Reviewer извлёк только безопасные
OID/parents, количества, размеры, digests и метаданные сохранности.
Приватные пути и содержимое посторонних записей не раскрывались и не
читались; файлы содержат только их path_sha256/size/sha256.

| Доказательство | SHA-256 |
| --- | --- |
| `inventory-readonly.py` | `fd070736eb3017569a3b10d3dc905286ed7f1e7a2cc5ec80b06dd4f400253bfb` |
| `receipt.json` | `1736aa48c63987e15ca99bfef0a322dcc11978b12189a7667dd4a014865aeab9` |
| `current-inventory.json` | `6480c32107b570769a3d299a4bf419dde11783dcd35b0078d1135c954f7edc2f` |
| `stash-preservation-live-20261031.json` | `0d623b7dcba42fc11518ad101f8f6ff6ef27aa4a1599cb33faa7efcae2a9716f` |
| `F290-stash-preservation-postcheck-20261017.json` | `1eea5137cedd4b18a91f7de892d0678bec64f4ff4ca7281262826c31f88eac57` |

Текущее чтение выполнено31.10.2026 в22:18:42UTC, то есть01.11.2026 по
локальному времени UTC+3. В evidence read_only=true, основная серверная
рабочая копия на `976f310f9fff09b96a1e6fcec99cb43f4bb706ae` чиста,
dirty_entries=0. Это источник наблюдения, не SHA принятия нового PR
и не утверждение о текущем выпущенном/runtime коде.

Reviewer сам к серверу не подключался: вывод о сохранности основан на
сопоставлении предоставленных выгрузок и принятого документа. Метка
read_only сама по себе не является доказательством отсутствия любой
возможной записи; неизменность предметных OID/parents/digests проверена
отдельно по нескольким наблюдениям. Дополнительно прочитан сам оператор:
он вызывает Git rev-parse/status/stash-list/rev-list/diff/show/ls-tree/
worktree-list, читает файлы пяти известных публичных путей для digests и
печатает JSON. Нет apply/pop/drop/reset, запуска backup/restore или записи
пользовательского кода. Абсолютная папка сервера не вынесена в вывод ревью.
Квитанция связывает exit0/PASS с точными SHA-256 исходника и inventory и
явно ограничивает результат T006. Оператор reviewer не исполнял.
Health/backup/restore не проверялись.

## Полнота и сохранность T006

Два stash из текущего evidence совпадают по OID с историческим postcheck;
весь массив метаданных stash, включая parents, записи и digests, полностью
совпал с предыдущей выгрузкой31.10. Для обоих index staged_count=0.

| Stash | Base | Index parent | Untracked parent |
| --- | --- | --- | --- |
| `7ca895259b05433799eeceae00877408730ad9ea` | `455990a33f51fe232a8fc3270c8d0a0d27db298b` | `4fb242738ddbe96e11fd524b913e53b40f40c0dd` | нет |
| `b0cce297217685fac91d9df58b022ee7d51752ec` | `7ff2c5c77ec007aac09cd86cded0579cd1a0443c` | `4a5a6c735cd7668e80c6560d4bff7fb9ea2b3340` | `c156ccec172c3a0348e9698ecee6e486b7365716` |

Ровно три записи: файл ротации2945bytes, посторонняя tracked запись15341bytes,
посторонняя untracked запись15296bytes. Их размеры и SHA-256 совпадают
со stash-disposition.md. Нет оснований считать посторонние записи ненужными
или переносить/отклонять их вместо владельца; сохраняются сами stash и parents.

Найдена одна сохранённая рабочая копия на основе
`42f0b95105c6545235ba219a55cbcc62bf577f39` с пятью dirty entries.
Все пять хешей равны историческому postcheck и таблице stash-disposition.md.
Это **основа незакоммиченной работы**, а не коммит, содержащий её пять
изменений. Наличие/хеши сохранённых файлов подтверждают сохранность;
оно не делает код принятым в master или частью выпуска.

release-v2026.10.16.6.md прямо устанавливает владельца пяти изменений —
другая задача «Проверь статус OV» — и описывает сохранение3tracked+2new,
сверку snapshot/рабочей копии и подтверждение продолжения владельцем.
Историческое12PASS в stash-disposition относится к изолированным старым
пробам; оно не используется как новое доказательство полноценной ротации,
backup, restore или текущей совместимости.

## Контрольные списки — основания по каждому пункту

| infra | Основание сохранённой отметки |
| --- | --- |
| CHK001 | FR001/SC004 и задачи сохраняют все три исходных результата и F238/F290. T006 не закрывает целую #6501. |
| CHK002 | FR002/research сохраняют точные pins/runtime/major compatibility. Новая проверка Actions не проводится. |
| CHK003 | FR003/010 и план сохраняют trust, SHA/base/run/attempt и обязательные PR gates; JSON inventory не подменяет CI-квитанцию. |
| CHK004 | FR004/план/research сохраняют различие Swift version/compiler/SDK/cache. T006 их не меняет. |
| CHK005 | План/quickstart сохраняют отказ при неверном toolchain до GITHUB_PATH. Нового исполнения этого пути не заявлено. |
| CHK006 | SC001/FR010 сохраняют границы локального/hosted/merge/release evidence; чтение inventory не является новым выпуском. |
| CHK007 | Исторические план/research сохраняют retirement macos14 и отдельную миграцию. Текущий runner не принимается в этом ревью. |
| CHK008 | FR005, T006 и fresh inventory покрывают оба stash, base/index/untracked, три записи и сопоставление пяти чужих файлов с историческим владельцем. |
| CHK009 | FR006, T007/T008 и quickstart сохраняют failure/concurrency/restore и отдельную границу удаления. Выполнение этих проверок ещё не принято. |
| CHK010 | FR007/data-model/T009–T011 сохраняют четыре отдельных результата и mapping cleanup. Их исполнения нет. |
| CHK011 | FR008/plan/quickstart сохраняют синтетику и запрет считать пишущий inventory чтением. Это Git inventory, не запуск предметного backfill. |
| CHK012 | FR009 и проверенные JSON используют только разрешённые OID/digests/counts. Приватные пути и содержимое посторонних записей не вынесены в отчёт. |
| CHK013 | FR010/011 и task dependencies сохраняют review/analyze/sync, валидацию и закрытие после приёмки; новых служб/обходов нет. |
| CHK014 | FR012/план/T016 сохраняют ранний CI-отказ без SSH-параметров. Это прежний отдельный CI-срез, без новой restore-приёмки. |

| requirements | Основание сохранённой отметки |
| --- | --- |
| 1. Полный объём/F238 | FR001/SC004, три истории и T006–T013 не переписаны. |
| 2. Независимые истории | T006 — только законченный учёт; T007/T008 и US3 имеют свои зависимости/приёмку. |
| 3. Измеримость | Полнота учёта подтверждается OID/parents,3записями и5digests; неизвестный результат политики не объявлен PASS. |
| 4. Полномочия | Git/PR follows validation; production, выпуск и удаление сохранённой работы сохраняют отдельные границы. |
| 5. Неизвестные факты | Текущее состояние сохранности выяснено; политика/перенос остаются T007/T008. Не придуманы неизвестные сроки или согласия. |
| 6. Пределы готовности | SC002/SC004 и T012/T013 не удовлетворяются одной инвентаризацией; все остальные задачи остаются отдельными. |

Все20 исходных строк и история списков сохранены. После записи оба списка
перечитаны целиком: infra **14 checked / 0 unchecked**, requirements
**6 checked / 0 unchecked**, вместе **20 checked / 0 unchecked**.

## Что этот PASS не принимает

По сообщению основного агента, текущий оператор выпуска не берёт ротацию,
а ни last30 из stash, ни14daily+weekly из чужой копии не приняты. Независимого
нового назначения владельца/согласованной политики в прочитанных документах
нет. Поэтому эти вопросы остаются T007; сохранность не равна согласию
на перенос, ни текущий оператор, ни reviewer не объявлены владельцами кода.

T007 требует отдельного design/owned paths и независимого review, T008 —
изолированной failure/concurrency/protected-copy/restore матрицы. Незавершённые
backup/restore изменения F273, о которых сообщил основной агент, не входят
в эту приёмку и не могут быть перезаписаны при будущей работе F290.
Код и сервер ради T006 не меняются; ничего не применяется и не удаляется.

Допустимо документально зафиксировать завершение только T006 и текущую
сохранность. T007/T008, T009–T013, полный FR005/006, SC002 и #6501/#7646
этим ревью не принимаются и не закрываются. Новый документальный PR должен
содержать собственную проверенную редакцию, review/converge и обязательные
governance-fast, macos-pr, pr-metadata точного SHA/основы. Если после этого
ревью изменится содержание решения, нужен повторный просмотр изменённых
документов; первичный PASS не принимал ещё не написанный итоговый diff.

Reviewer не изменял код/spec/plan/tasks, Git/GitHub, runtime или владельцев,
не запускал тесты, CI, SSH, приложение, backup/restore или production.

## Контрольные суммы источников и списков на этапе первичного ревью

| Файл | SHA-256 |
| --- | --- |
| `AGENTS.md` | `24c0767f2223bb21e969079ec1ec09e0dec7c3fd3d85d02e78832f17e0775958` |
| `.specify/memory/constitution.md` | `7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8` |
| `docs/agent-guidance/README.md` | `2f3e0339a89d3ccdf0878026920955a189584d6a985116b069584cd78b3c75bb` |
| `docs/agent-guidance/document-reading.md` | `5263860b1974df022826ac81c2482e6ee92100bc0bb718ab5a29b32e2422e411` |
| `docs/agent-guidance/spec-kit-flow.md` | `afb816ce48624eb79fcd7fd44d09f0986296e87ef1cfecd790228ac70a5b9b9e` |
| `docs/agent-guidance/release-and-validation.md` | `ff0d996c95101d5f782259661131db1b7528b3bf58991603f5652092e1e5256f` |
| `docs/agent-guidance/product-gates.md` | `9f7072c879490d250053cb7397ad6b9b68fdcde17bdf9367ed874a41e450b5f5` |
| `docs/agent-guidance/tracker-policy.md` | `9793de5e158283c2d37bdd2b47f0daf4d312a44fd6ffa37cc22ac47f7a0c3472` |
| `specs/290-post-release-hardening/spec.md` | `7ad5555a100954b0d8c3c6ab8f2faa00334a1873a2241d6ac7812cbe7bc5ba31` |
| `specs/290-post-release-hardening/plan.md` | `b9938439ba8b8cd02f198ac95190a53d6399466f8070fa0604eaf488d0a591f3` |
| `specs/290-post-release-hardening/tasks.md` | `eedaaa4b4c29d7566acf939a634876644598f08b7d26dfddfb40fa03a072bed1` |
| `specs/290-post-release-hardening/quickstart.md` | `f16eddebb44e5a50b4dd2d896ad005bfb623c1cb63425c0db221796adf956906` |
| `specs/290-post-release-hardening/research.md` | `a6bec8f55ff23b876fe93e74a9b6ce8ee5f33b2d4bcf9669e70add8fab7179ed` |
| `specs/290-post-release-hardening/data-model.md` | `ea2ad0764fef4e57c9324459a5e2bf1726d3ddd3e678dddcac08580f797e8468` |
| `specs/290-post-release-hardening/stash-disposition.md` | `74a9af755151b17b4a045bcfbbf6d48908fa2b8a506ca362df3ef08c4cd576c7` |
| `specs/290-post-release-hardening/checklists/infra.md` | `5484f592a870f4e0819c3b93cf334857dcf410dc4a5b6aa19fd52b872ab0e910` |
| `specs/290-post-release-hardening/checklists/requirements.md` | `80eedafa368d5e656ab5c9982445d9ef6f0a35b3a970d7a06f7243e7c41aca69` |
| `docs/deployments/2brain-rec/release-v2026.10.16.6.md` | `ebef90966e431d45e0893135f4a91141c7957d564e2f079a177565efb64f5d10` |


## Итоговое ревью документального diff T006 — 01.11.2026

**SCOPED FINAL DOCUMENTARY PASS**, CRITICAL 0 / HIGH 0 / P1 0 / P2 0.
Это дополнение принимает уже написанный итоговый diff и заменяет прежнее
ограничение о ещё не подготовленной документальной редакции. Полоса —
существующий active Spec Kit; в этом срезе только документальная приёмка
учёта T006, без изменения кода, политики хранения или серверных данных.
Локальный feature.json теперь ограничен только T006, основа та же
`3aa38ce2568e5bb89c8a5a763c19ae51d5f82d29`.

Целиком перечитаны окончательные tasks.md, stash-disposition.md,
validation.md, оба списка и новый changes/unreleased/F290.yaml; просмотрен
весь diff. Прямое сравнение с HEAD подтвердило сохранность всех16исходных
описаний задач и остальных отметок: изменена только T006 с [ ] на [X].
T007–T013 по-прежнему [ ]. spec/plan/quickstart/research/data-model
побайтово неизменны. Все20исходных строк списков неизменны, добавлены
только примечания ревью; история предыдущих этапов сохранена.

Новая запись учёта согласована с проверенной выше инвентаризацией:
два stash, три записи, их parents и пять хешей сохранённой работы.
Основа42f0b951 не выдана за коммит этих изменений; исторический владелец,
запрет перезаписи пересекающихся изменений F273/T113 и сохранение работы
до T007/T008 указаны. Ни last30, ни14daily+weekly/partial48h не приняты.
Отметка T006 и фрагмент изменений не обещают реализации ротации,
восстановления, выполнения старых12проб заново или закрытия общих issues.
Датированное дополнение объясняет прежние исторические отметки T006–T013.

После дополнения оба списка перечитаны целиком: infra **14 checked /
0 unchecked**, requirements **6 checked / 0 unchecked**, всего **20 checked /
0 unchecked**. Замечаний в этой области нет. `git diff --check` — PASS.
Общие FR005/006, SC002, T007–T013 и #6501/#7646 остаются незавершёнными.
Приёмка нового коммита/PR требует собственных governance-fast, macos-pr,
pr-metadata точного SHA и основы через общий валидатор; их прохождение,
слияние, выпуск или изменение сервера этим отчётом не утверждаются.
Reviewer изменил только два списка и этот отчёт; тесты/CI/SSH/приложение/
backup/restore не запускал, Git/GitHub-состояние не менял.

Контрольные суммы итоговых входов (таблица предыдущего этапа выше сохранена):

| Файл | SHA-256 |
| --- | --- |
| `specs/290-post-release-hardening/tasks.md` | `148a89a4710d5aa8d6f31c74fe03df84cb17a5ce490dc7658a2544931256620f` |
| `specs/290-post-release-hardening/stash-disposition.md` | `52b7f990b332a2fb0c70b08120841221b5df767423e8e4db6b41019bae01ac3a` |
| `specs/290-post-release-hardening/validation.md` | `800dcb785a7c4ac2fcd7abc2d0adc04fc525b327afe6b1c0294556a10ab2b522` |
| `changes/unreleased/F290.yaml` | `2f93f7e4a6389ce6d205a532a5586b2fdc2edc5d8a121998639d3e5be60fb8f4` |
| `specs/290-post-release-hardening/checklists/infra.md` | `4ea2cb9d98ed1a71632a220b6abb797a904cd9e5fa98939bfbccadb03a344f98` |
| `specs/290-post-release-hardening/checklists/requirements.md` | `ef098ea294c6bd561ba888f4d90c766b565f02cdb425947bf9638214faeba3e2` |
