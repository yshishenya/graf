# Round263 — REQUIREMENTS: retained bootstrap pair

Дата: 2026-10-06. Независимая проверка качества требований и scoped
`speckit-analyze`, до RED/реализации. Lane: **high-risk-product**, существующий
T116 / #7444. Canonical:
`/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`, branch
`codex/200-windows-followup`, HEAD
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`, dirty preserved.

## Решение и порог

**SCOPED REQUIREMENTS GO к RED и ограниченной реализации
`ProtectedCustodyBootstrapPair::read(root, own, expectedQueueId, cancellation)`.
C0/H0/M0/L0 новых неустранённых findings в этой области.** Порог текущего
storage-среза: нет unresolved CRITICAL/HIGH и blocking clarification.
Не требуется новое решение о schema или продуктовой политике.

Это provenance обоих собственных bootstrap payloads под удержанной exclusive
lease, **не полноценная bootstrap admission authority**, не SOURCE approval
будущего кода, не завершение T116/приложения/выпуска. Структурное `protected`
либо `migrating` не подтверждает готовность queue или matching intent.
Реализация и тесты этого нового consumer ещё не проверены как PASS.

## Нормативные основания и пригодность reuse

Лично перечитаны все154 действующих критериев десяти checklist наборов,
конституция7.1.0, root AGENTS/README, spec-kit-flow/product-gates/worktrees/
tracker guidance; активные spec/plan/tasks/quickstart/data-model прочитаны
в относящихся к области разделах. Использованы `speckit-checklist` и
`speckit-analyze`; вопросы о глубине/границе не задаются повторно: запрос точный.
Ранее принятый контекст сохраняется, история всех110 reports не переаудируется.
Прочитаны относящиеся условия bootstrap260, metadata-pair252 и history262;
их приёмка не переносится автоматически на новый bootstrap wrapper.

- Base contract §§2–5, §8/8.1: fixed root location/identity, metadata BOTH/no
  rollback, strict bootstrap JSON, пределы и worker-only владение.
- Spec FR-012/013/022, SC-006; plan:1501–1534/1565–1597, tasks:568 T116;
  model§12 ProtectedBootstrap/PinnedSnapshot, quickstart§12: physical/semantic
  failure и first-transition cuts. Storage dependency разрешена отдельно от
  clock/calendar, но не сокращает их или final application gates.
- Реальный `ProtectedCustodyFiles::open`:230–286 уже выбирает bootstrap только
  под root `.custody-v1/bootstrap`, с пустым package directory; проверяет
  handles/ACL/reparse/hardlink/store.id/id.bin. JSON не задаёт этот путь.
- Files:507–599: `readValidatedMetadataPair()` использует один прежний
  physical validator; проверяет BOTH indices и DATA, g1 equality и последующий
  highest selection. Новый сканер/алгоритм выбора не нужен.
- Metadata.h:128–152 / .cpp:520–594: существующий PackagePair даёт подходящий
  образец private retained lease/pin, charged object/control block и wipe.
  Переиспользовать pattern, не создавать generic controller или второй parser.
- Bootstrap codec .cpp:36–46/170–191/454–459 уже проверяет schema1, девять
  полей, own/generation и independent queue ID, точные mode/null сочетания.
  Внутреннее имя `protectedStore` не переименовывает JSON `protected`.

## Проверка полноты, ясности и согласованности требований

Таблица оценивает написанные требования, не исполнение будущих тестов и не
добавляет checkbox markers. Traceability12/12.

| ID | Вопрос к требованиям | Решение / основание |
| --- | --- | --- |
| R01 | Определены ли fixed location и независимые ожидания? | PASS — base§2/8.1: own bootstrap context и ожидаемый fixed queue ID получаются не из JSON; generation берётся из каждого authenticated own index. |
| R02 | Отделена ли проверка queue ID от доказательства queue owner? | PASS — base§8/8.1: caller независимо закрепляет id.bin/reservation. Этот API сверяет значение, не открывает/доказывает очередь; никаких JSON path redirects. |
| R03 | Полны ли BOTH/no-rollback правила? | PASS — base§4: missing/unreadable/invalid peer index/DATA блокирует весь результат, даже если higher/current годен. Нельзя singleton repair, default/empty bootstrap или legacy fallback. |
| R04 | Однозначны ли equality, placement и выбор поколения? | PASS — base§4: одинаковые decoded g1 допускаются; другие равные поколения/разный decoded g1 конфликтны. Последующие slots проверяются прежним codec, current=highest validated. |
| R05 | Определена ли семантика обоих payload, не только physical arrays? | PASS — base§3/8.1: каждый payload DATA positive≤65536, exact context/version/length; strict bootstrap codec с собственной index generation и одним independent expectedQueueId. |
| R06 | Ясны ли schema/mode/nullable поля без расширения? | PASS — base§8.1: только graf.custody.bootstrap.v1; protected→три null; migrating→tx/subject, queue→directory null, package→ASCII identity1..300. Unknown/missing/decoded duplicate/BOM/types/overflow fail closed. |
| R07 | Полон ли срок владения и readonly boundary? | PASS — base§4/5/6 и accepted252: exclusive id.bin lease до последней shared reference, private ctor/const values, нет Files/HANDLE/writable capability наружу. Mutation позже требует release и новой проверки. |
| R08 | Измеримы ли native/owned/pin пределы? | PASS — base§3/5: job≤4 до native IO, pins≤32, общий owned64MiB, metadata64KiB. Job живёт до actual synchronous completion; результат удерживает pin/lease, не вечный native job. |
| R09 | Определены ли cancel/exception/failure без partial success? | PASS — base§5/FR-012: null/pre-cancel до IO; checkpoint до/после compound bounded IO/decrypt, между slots и перед result; typed native ошибки, cleanup/wipe на всех выходах. Начатый native вызов не force-freed по timeout. |
| R10 | Отделены ли semantic wipe и lifetime от bool успеха? | PASS — base§5/6: charged owner/control block, local/retained owned values очищаются; leases закрываются до pin admission release. Result construction failure не теряет владение. Не обещается стирание всех register/parser stack копий. |
| R11 | Явны ли worker/UI/adoption границы? | PASS — base§5: нет crypto/scan/read в UI/startup ctor; result не stale account/epoch authority. Будущий caller не применяет projection/effects без актуальной отдельной проверки. |
| R12 | Полон ли перечень последующих зависимостей? | PASS — base§8/8.1/plan/T116–118: matching intent, current queue pair, account, inventory/root retention, GC/migration/effects и adoption отдельно. Initial migrating queue fence допускает reserved queue ID без indices, не empty queue authority. |

## Обязательная граница реализации для SOURCE review

Только existing Metadata/Files/codec/allocator и существующий native test target.
API не получает directory из JSON: для bootstrap всегда fixed location/пустой
package argument. Independently pinned own context/expectedQueueId неизменны
на весь вызов. Не вводить самостоятельный запрет zero/equal IDs, которого нет
в контракте. Для обоих slots нужен тот же ожидаемый queue ID, даже когда mode
и собственные generation различны; не навязывать постоянное равенство mode/tx
между разными generations, законный switch меняет эти значения.

ReadExisting не считается замороженным владельцем: existing writeExisting
открытие используется исключительно как private exclusion lease, без writes,
CREATE_NEW/IDs regeneration/ACL repair/flush/rename. Перед возвратом блокируются
права записи этого экземпляра; наружу только retained const result. Factory
не создаёт резервируемый queue ID и не читает произвольные служебные paths.

Physical pair проверяется до semantic результата. Оба bootstrap logical
payloads — ровно один DATA, length1..65536; ZERO/empty не допустимый JSON.
Повторное own DATA open/decrypt и strict parser не заменяются одним доверием к
array indices. Payload generation сверяется именно с generation своего slot.
Оба mode являются структурными значениями, не authorization predicates.

Cancellation проверяется вокруг реальных bounded composite операций
Files.open/physical-pair/read/decrypt и до публикации result. Нет обещания
остановить произвольный синхронный ReadFile/DPAPI посреди native wait; ресурсы
остаются до actual возврата. After-read cancellation не возвращает partial
pair и не освобождает чужой/следующий owner. Null token не принимается.
Typed native/hash/protection/allocation/identity ошибки сохраняются, не
подменяются удобным default/recovery success. Allocating Debug moves и shared
control-block refusal должны освобождать raw object/lease/pin без второго
throwing error-return snapshot. Shared_ptr copies удерживают одного владельца,
а не создают дополнительный protocol lease/native job на каждую копию.

## Scoped analyze и общий незакрытый объём

| Requirement | Existing owner | Покрытие данного шага |
| --- | --- | --- |
| FR-012 | T116 | Actual protected BOTH bootstrap payload provenance и bounded readonly владение. |
| FR-013 | T116; transition T117 | No missing-peer rollback/default queue; expected ID только independent match, queue content ещё не принят. |
| FR-022 | T116/T117/T118 | Retention до last release; нет delete/GC/cleanup полномочий. |
| SC-006 | T116 | Schema/context/bounds/failure и metadata-only evidence, не вся bridge/runtime matrix. |

Scoped coverage4/4=100%, executable owner task1=T116, unmapped0,
ambiguity0/duplication0/new product requirements0, C0/H0/M0/L0. Конституция
II/III/IV/VI не нарушена: indicator/Stop и account access не меняются, local
encryption не касается server plaintext observability, deletion truth и
independent review сохранены. Это **не full analyze22FR/10SC/120tasks**.
Незавершённый application T116 остаётся CRITICAL объёмом работы, а не новым
противоречием требований узкого prerequisites API. T116#7444 не закрывается;
связь/активность предоставлены main, remote GitHub здесь не запрашивался.

BootstrapPair самостоятельно НЕ доказывает current queue/ledger содержимое,
durable matching intent/history, migration stage/source stamp/old-name copy
conflicts/tombstone-only IO, восстановление всех roots перед GC, account/UI
epoch, virgin inventory либо switch/admission/network/delete/playback права.
Даже `protected` требует current queue pair до admission, а `migrating` требует
matching durable intent и этапные условия§8; package migration уже требует
protected queue до prepared. Эти обязанности не скрыты как выполненные.
Legacy RED257/B1, известный full49/50 и runtime adoption остаются открытыми.

## Минимальные будущие доказательства main — не результаты этой проверки

- Реальные DPAPI/bootstrap id.bin и BOTH slots: equal g1 и разные g3/g2,
  три разрешённые формы, собственные generations, законная смена mode;
  no queue object/indices для структурного initial migrating fence не считается
  queue-ready. Отдельный expectedQueueId mismatch в lower/higher payload.
- Singleton/missing/corrupt lower или higher index/DATA, unequal g1, conflict
  generations; authenticated malformed lower JSON с исправными checksum/hash,
  schema/own context/generation mismatch, empty/ZERO/oversize64KiB+1.
- Actual native identity writer exclusion до/после factory и после сброса
  первой ссылки при живой копии; last release разрешает повторное открытие.
  Public API не отдаёт write capability; artifacts/IO counters без mutations.
- Pre/mid IO/между-slot/final cancellation, точные native IO/hash/DPAPI ошибки;
  job4/pin32/owned pressure, retry и baseline memory, owned plaintext wipe.
  Объект/control block и Debug throwing transfers оцениваются отдельно.
- Genuine RED до кода, frozen canonical inputs, sequential focused native
  Release/Debug, existing portable/codec/pair regressions и SDK; фактические
  результаты/EXE identity в следующем SOURCE review. Portable не исполняет
  Windows ветку, сборка не принимает installed приложение или hardware.

## Инвентарь и неизменность

До этого файла120 `.md`: **10 текущих normative,154 checked/0 open**;
отдельно110 historical/context,256 historical checked/10 historical open.
Старые unresolved markers не превращены в новые требования этого gate.
Перечитаны все действующие criteria; прежние markers не менялись.

| Действующий checklist | Checked / open |
| --- | --- |
| requirements / security / ux | 22/0 · 27/0 · 25/0 |
| audio-capture / advanced-routing | 24/0 · 14/0 |
| calendar-launcher / calendar-operation / calendar-wire | 5/0 · 8/0 · 5/0 |
| packed-writer / privacy-pause | 12/0 · 12/0 |

SHA sorted basename + space + SHA + LF исходных120 файлов:
`3e1b319dc6c4c69739015c2c24aab565aa576afd43fce5b663d330138cfd1fbf`.
Tasks120/93/27, SHA
`80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f`.
Новый report0 checkbox markers; после его добавления121 файлов, не новый
нормативный список. Запись только в этот report, prior120 immutable.

Prerequisites analyze/checklist команды дали правильный FEATURE_DIR и template.
YAML лично разобран: before/after implement/analyze/checklist — в каждой из
шести стадий registered1 `git`/`speckit.git.commit`, enabledfalse; total6/0.
Disabled hooks не dispatch-ились, авто-коммит не запускался. Нет изменений
governance или расширения разрешений. Extensions SHA
`ad728fdff37fe1783903777fbdf792fc44752f2818d1765c76a7e1bea9dabb6c`.

## Свежие SHA до RED

| Артефакт | SHA-256 |
| --- | --- |
| constitution | `d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859` |
| spec.md | `b411bfb620e9d571422f9c423b0ae193ed70e87303d08e84a4b9844e32f81658` |
| plan.md | `527e660d9e1682e7a0f0a79118ea4bab38d4c174542b49c0113f571528a5b89c` |
| quickstart.md | `fc225d2ec40cc26a7fad0bc6d7adcb22d7f4d676fcdf70b2e645dbbdb06ddb8e` |
| data-model.md | `8dd54012c3bfe4003cd18db98ebc67e0b7730cbbdfb6523b881cce4cdc15ec19` |
| base contract | `ec93d11c474cb970d57c2324518d541cd9fb3e7bb7f2f807d63d612ad878624a` |
| packed contract | `a1dedd9d5b7ce02e4a6c200a300b0423bcada82192217e2a79f9773428c4a7b5` |
| Metadata.h | `24716202c2a508c7f8b3582d71d7f572059e254b870fc40b4160159b4652c4e5` |
| Metadata.cpp | `864eabe04dec416897aa7007e88870d4fc093c0406a35aba0b3502cdcad05f81` |
| Files.h | `d3d792efba7b0c4016169fb4aac1ab330bc7b4c349b9d87f3501d873857a7a17` |
| Files.cpp | `c23acf733011e9bcf4d80589d6a00e96a94a516866b822f95f436c49b9a70bd8` |
| Memory.h | `a5a67fb3448f07d4232cf8dee893e60e65c3eea5687a0908f4469226be2000ad` |

HEAD — только anchor; dirty bytes определяют приведённые SHA, не название
worktree или прошлый PASS. Reviewer не выполнял VM/tests/app/profile/Mic/server/
mac/install/commit/GitHub действия. SOURCE и actual acceptance нового consumer
потребуют отдельной независимой проверки после реализации.
