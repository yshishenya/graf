# F224: независимое ревью требований и проекта US1

Дата: 2026-10-16. Reviewer: отдельный агент review_f224_design.
Режим: проверка качества требований в high-risk product area; код не изменялся.
Основа проекта: f4b38141af2fad64bae219e8c012b0a54f237491.

Результат: **PASS требований текущего US1**, без блокирующих пробелов.
requirements.md: **16 checked / 0 unchecked**. infra.md: **20 checked / 0 unchecked**.
Отмеченные пункты означают полноту и согласованность требований. Они не означают
прохождение реализации, миграции состояния, фактического macOS smoke/rollback,
TCC, CI нового SHA или готовность общей #6180 к закрытию.

## Основания и границы

Прочитаны AGENTS.md, конституция7.1.0, guidance README/spec-kit-flow/product-gates,
local-development и применимые разделы release-and-validation. Проверены все
spec/plan/research/data-model/contracts/quickstart/tasks и оба чеклиста F224.
Сверены исходные #6180–#6188 по сохранённому индивидуальному снимку аудита.
Для проверки технических предпосылок прочитаны вызовы state_dir/global_state_dir,
build_manifest, операции harness, state_lock и _write_json/_atomic_write.
Последний уже выполняет fsync файла, replace и fsync каталога; проект не
приписывает имеющемуся JSON writer недоказанную атомарность всей promotion.

Исходные восемь задач честно восстановлены. После первого ревью сформирован
полный реестр13 задач; все остаются unchecked. Повторное независимое чтение
этого реестра выполнено ниже. Analyze и issue sync обязательны до кода.
Дополнительный дизайн ordinary-promote crash recovery относится к будущему US3;
текущий PASS не разрешает его реализацию. Существующий миграционный владелец
F249 T038/#6786 сохранён. Исторические свидетельства F229/F249 не считаются
приёмкой нынешнего F224 SHA. Внешние команды, GitHub, приложение и runtime не
изменялись. Новые тесты в рамках этого ревью не запускались.

## Проверка requirements.md

| Пункт | Подтверждение |
|---|---|
| Q001 | Spec описывает цели и наблюдаемые отказы; выбор binding, locks и parser вынесен в plan/contract. |
| Q002 | Три User Stories объясняют недостоверность проверки, риск состояния и пользу восстановления. |
| Q003 | Истории и FR изложены через действия/результаты; путь приложения и Dev/TCC/SHA оставлены для точности. |
| Q004 | Есть входное поручение, истории, независимые тесты, сценарии, edge cases, FR/entities, SC и допущения. |
| Q005 | Clarifications разрешают границы из исходных issues и действующего правила одного Dev; технические решения определены отдельно. |
| Q006 | FR-004/006/008/016 и contract запрещают второй путь/lock и shared effects fixture; старое состояние сохраняется на месте. |
| Q007 | SC-001–006 задают пары адресов, взаимоисключение процессов, сохранность, идентичность и разрешения. |
| Q008 | SC требуют результаты без назначения алгоритма хранения, парсера или нового слоя. |
| Q009 | У каждой из трёх историй независимый тест и положительные/отрицательные сценарии. |
| Q010 | Edge Cases покрывают origin, cwd, worktrees/clones, paths, locks, старую версию и существующие данные. |
| Q011 | FR-017/018, plan и исходный реестр сохраняют полный umbrella #6180, не подменяя его узкими T001–T008. |
| Q012 | Assumptions/plan/quickstart явно называют занятый Dev,27GiB, существующие зависимости и отложенную живую приёмку. |
| Q013 | FR-001–007→US1/SC-001–003; FR-008–011→US2/SC-004; FR-012–014→US3/SC-003–005; FR-015–018→границы/SC-006 и quickstart. |
| Q014 | US2 содержит штатный lifecycle, US3 — сбои, совместимость схемы и сохранение Dev grants. |
| Q015 | Spec имеет статус восстановленных требований, research различает текущие primitives и недоказанные обязательства. |
| Q016 | Input/Status/tasks прямо говорят, что оригиналы не найдены и выполнение не объявлено. |

## Проверка infra.md

| Пункт | Подтверждение |
|---|---|
| CHK001 | Contract Канонизация перечисляет HTTPS/SSH/SCP, .git/slash/case и запрещённые credentials/escapes/query/fragment/порты; raw/effective origin должны совпасть. |
| CHK002 | FR-001/002, US1.1–2 и quickstart.1 различают worktrees/clones/чужие origins без basename/cwd. |
| CHK003 | Research и data-model прямо запрещают вывод владельца из совпадения SHA; adopt требует операторского подтверждения. |
| CHK004 | FR-006 и data-model сохраняют manifests/runtime/journals/data/secrets/archives на месте, путь и inode promote.lock. |
| CHK005 | Contract Adoption.1/3 отказывает при неизвестном втором standard root; неизвестные overrides не заявлены как исчерпывающе обнаруженные. |
| CHK006 | Registration lock действует только при adoption; порядок registration→operational, обычные команды используют прежний promote.lock. |
| CHK007 | FR-005, Adoption.4 и table обычных операций требуют повторного чтения binding/active/parent после ожидания и expected SHA. |
| CHK008 | Data-model transitions и Adoption.2/5/6 определяют атомарную публикацию, безопасный повтор и отказ перепривязки. |
| CHK009 | Adoption.1 проверяет исходные компоненты до записи, lock требует owner/type/inode и отказ symlink/подмены; FR-003/004 обобщают границу. |
| CHK010 | Contract перечисляет все mutating CLI operations, status/smoke/startup guard, direct adapter paths, _live_state_owns_tags и build_manifest; prune без live охвачен отдельно. |
| CHK011 | Contract fixture root отделён от binding root и его предков/потомков; общие Docker tags и canonical pointer запрещены. |
| CHK012 | FR-009–011 и contract status/smoke различают снимок, фикстуру и реальную проверку с проверкой active identity по завершении. |
| CHK013 | Contract adapters сохраняет clean/fullSHA/tracked bytes/digest; resolver проверяется до stop/install/Docker без изменения frozen guard. |
| CHK014 | Research/contract прямо ограничивают гарантию произвольного старого контроллера, требуют исключения самостоятельных старых jobs. |
| CHK015 | FR-008–014/017/018, US2/US3 и quickstart сохраняют lifecycle/runtime/recovery/schema/TCC и отдельную реальную приёмку. |
| CHK016 | Research фиксирует отсутствие durable journal обычного promote до stop/install; plan откладывает отдельный US3 design и сохраняет F249 T038/#6786. |
| CHK017 | Quickstart задаёт Dev-only before/update/relaunch/after microphone/system audio, signer/requirement/entitlements без reset/второго app. |
| CHK018 | FR-017/018 и research отделяют historical evidence от нынешнего exact SHA и US1 от полного закрытия umbrella. |
| CHK019 | Quickstart US1.1–6 и contract Проверки отказа требуют реальные временные repos/processes, отсутствие writes/effects и сохранность/inode. |
| CHK020 | Plan/quickstart разделяют требования US1, будущий US3, post-commit exact-SHA fast, три PR checks и release-full frozen candidate. |

## Оставшиеся обязательные ворота

- Cross-artifact analyze полного реестра13 задач, затем issue sync.
- Воспроизводящие исходный отказ и итоговые изолированные проверки US1,
  независимое ревью кода и ограниченный converge.
- Отдельное разрешение на проверенный commit; три текущие PR-проверки на exact SHA/base.
- Реальный adoption только после освобождения стенда; отдельные US2/US3,
  compatible rollback, миграционный владелец и Dev TCC остаются открытыми.

Нерешённых замечаний к проверенным требованиям US1:0. Неподтверждённых пунктов
чеклистов:0. Это не снимает перечисленные ворота реализации и общей приёмки.

## Повторная проверка после генерации задач

Повторно полностью прочитаны семь документов spec.md, plan.md, research.md,
data-model.md, contracts/state-ownership.md, quickstart.md и итоговый tasks.md.
Хеши первых шести совпадают с первоначальным отчётом; изменён только tasks.md.
Перечитаны оба отмеченных чеклиста. Результат сохраняется: **PASS US1**,
requirements16 checked/0 unchecked, infra20 checked/0 unchecked.

Итоговый tasks.md содержит ровно13 уникальных T001–T013, все unchecked.
Исторические T001–T008 и связи #6181–#6188 сохранены; зависимость T002 перед
T008 указана явно, несмотря на сохранённую историческую нумерацию. Тесты
T003 предшествуют изменениям T004/T005, межпроцессная матрица T007 и guidance
T006 входят до итоговой T008. Shared callers, frozen adapters и неизменность
данных/lock не выпали. T009 сохраняет реальную US2; T010 требует отдельного
проекта/reviewer/analyze/sync до кода US3; T011/T012 сохраняют живой rollback
и Dev TCC; T013 не разрешает закрытие umbrella до всех обязательств.
Разрешение US1 по-прежнему не считается разрешением live adoption/merge/release.

Прочитан существующий specs/249-notification-control-design/tasks.md:225–227:
T038 остаётся unchecked и прямо связан с #6786. Его требования охватывают
доказанного предка, неизменные storage images, согласованный холодный снимок
PostgreSQL/MinIO, компенсацию до допуска writers и запрет автоматического
возврата старого снимка после запуска worker. Ссылка из F224 T011 корректна;
новая миграционная задача не создана. Приёмка T038 этим ревью не подтверждена.

Новых замечаний нет. Обновлён только SHA256 tasks.md и этот отчёт;
спецификации, план, задачи, код, GitHub и установленный стенд не менялись.

## Проверенные версии файлов

SHA256 ниже фиксируют документы, по которым принято решение; изменение их
содержания требует оценки затронутых пунктов reviewer, а не переноса PASS молча.

```text
10f19dfc5ad304073d35942357c7732d9ed79de441340266ca8528b7bc583a63  spec.md
bb52559d92153bbffd3d617e8ef35fa74292791e54687217455ae61e31705c2e  plan.md
bfffa6f74ba41e6fc51e1ef490b1e644c4d15eaf1fe56b45b5c546658425cc8d  research.md
0227601333fb82afe7e99cdfe95cab2ae1a7860efe1f42e058a121830a5fb9ab  data-model.md
ee4d3d6e618dd83f5ce414edc70f15c403688434180532e04f3fdcb35e38018d  contracts/state-ownership.md
baa4816bc760f2d9ac60a212f612b96e63421a7acfa956dbf8ebb94ce351c918  quickstart.md
ecdbe3f530815e896f9060c2fd0256919d47a7e79a6d65ec0885d77fd7683b0a  tasks.md
```
