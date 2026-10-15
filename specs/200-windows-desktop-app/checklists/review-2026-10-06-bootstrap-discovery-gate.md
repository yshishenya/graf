# Round264 — REQUIREMENTS: fixed bootstrap/queue identity discovery

Дата: 2026-10-06. Независимая проверка требований и scoped `speckit-analyze`,
до RED/реализации. Lane: **high-risk-product**, существующий T116 / #7444.
Canonical: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`,
branch `codex/200-windows-followup`, HEAD
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`; dirty preserved.

## Решение

**SCOPED REQUIREMENTS GO к RED и реализации overload
`ProtectedCustodyBootstrapPair::read(root, cancellation)` в предложенной
границе. C0/H0/M0/L0 новых неустранённых замечаний этой области.**
Порог: нет unresolved CRITICAL/HIGH или blocking clarification. Новое
продуктовое решение/schema не нужны. Обязательные условия ниже — действующий
контракт, не новые задачи или дополнительные форматы.

Это получение независимых fixed identities и проверка собственного BOTH
bootstrap под удержанными native leases. **Не queue authority**, не admission,
не SOURCE approval будущего кода, не завершение T116/приложения/выпуска.
Новый overload и его регрессии ещё не исполнены и не приняты как PASS.

## Прочитанный контекст и нормативные основания

Лично прочитаны инструкции `speckit-checklist` и `speckit-analyze`, root
AGENTS/README, constitution7.1.0, worktrees/spec-kit-flow/product-gates/tracker
guidance; относящиеся к области разделы release guidance, PRD/current status,
активных spec/plan/tasks/quickstart/data-model и обоих storage contracts.
Лично перечитаны все154 действующих критерия десяти нормативных checklist
наборов. История112 отдельных reports/context не переаудируется целиком;
относящиеся принятия bootstrap260/263 и history262 используются в своих
границах, не как автоматическое одобрение discovery.

- Base contract §§2–5, §8/8.1: fixed locations, exact16 opaque identities,
  confined handles, BOTH/no rollback, strict bootstrap semantics, retained
  leases, worker-only/native/owned budgets и first-transition reservation.
- Packed contract §1: bootstrap/queue остаются v1; discovery не создаёт
  downgrade/representation choice и не открывает packed media.
- FR-012/013/022, SC-006; plan:1501–1534/1565–1597, T116:568,
  model§12 ProtectedBootstrap/PinnedSnapshot, quickstart§12. FR-022 применён
  только к отсутствию выдуманного purge/delete authority, не к закрытию purge.
- Constitution III/IV/VI: защищённое локальное хранение, правдивое удаление,
  обязательные независимые gates. Другая capture/privacy/calendar работа
  остаётся самостоятельной; новая пользовательская политика не вводится.

## Качество требований и прослеживаемость

Таблица проверяет ясность/полноту требований, **не runtime PASS** будущего
кода. Traceability14/14; новых checkbox markers не добавлено.

| ID | Вопрос к требованиям | Решение / источник |
| --- | --- | --- |
| R01 | Однозначны ли источники identities? | PASS — base§2/8.1: actual fixed store.id, bootstrap/id.bin, queue/id.bin; ни own ID, ни ожидаемый queue ID не берутся из JSON. |
| R02 | Исключены ли создание/поиск/исправление? | PASS — base§2/8: OPEN_EXISTING fixed locations only; no scan, create, repair, UUID regeneration, legacy fallback или восстановление missing IDs. |
| R03 | Полна ли проверка действительных handles? | PASS — base§2: exact16, private ACL, actual confined path, local disk/reparse/ADS/UNC/hardlink checks и удержанные ancestors; строковый canonical path не заменяет handle proof. |
| R04 | Определена ли стабильность обоих store observations? | PASS — base§2/4 и proposal: store handles FILE_SHARE_READ, без share-write/delete; оба observed store IDs равны. Queue и bootstrap contexts принадлежат этому retained store. |
| R05 | Полна ли object exclusion/lifetime граница? | PASS — base§4/5: bootstrap и reserved queue id.bin под private writeExisting exclusion, без writes, blockWrites до публикации; обе leases/IDs/ancestors остаются до последнего owning result. |
| R06 | Отделён ли reservation от очереди? | PASS — base§8: queue ID обязателен, queue indices могут отсутствовать при migrating prepared. Это не empty/validated ledger и не разрешение effects; logical queue validation здесь не выполняется. |
| R07 | Сохранены ли physical BOTH правила? | PASS — base§4: существующий validator обеих indices/DATA, decoded equal g1 only, последующий exact slot/highest selection. Bad/missing/unreadable peer — whole failure, no repair/rollback. |
| R08 | Проверяются ли оба semantic payload с независимым queue ID? | PASS — base§3/8.1: strict bootstrap codec для каждого own index generation, exact own store/object, один actual reserved queue ID, payload positive≤65536. Не только current slot. |
| R09 | Сохранены ли известные формы и compatibility? | PASS — base§8.1: только девять полей bootstrap.v1, protected/null3 и migrating tuple; known-context overload source-compatible. Нет aliases, запрета zero/equal opaque IDs или требования равного mode между разными generations. |
| R10 | Полны ли failure/cancel условия? | PASS — base§5/FR-012: null/pre-cancel до IO, checkpoints вокруг bounded discovery/IO/decrypt и перед result; exact typed causes/native errors, whole cleanup/wipe, no partial result. |
| R11 | Измеримы ли ресурсы и actual completion? | PASS — base§3/5: общий native job≤4, pin≤32, owned≤64MiB, metadata≤64KiB; один compound job до IO и до actual native cleanup, не timeout release и не вложенная дополнительная квота. |
| R12 | Полна ли readonly/private result граница? | PASS — base§4/5/6: charged object/control block, private retained owners, const semantic values, wipes/exception cleanup; наружу нет writable Files/HANDLE или queue capabilities. |
| R13 | Разделены ли readiness и IO? | PASS — base§5/plan: вызов и final owner release на worker; UI/startup constructor не читает IDs/indices и не decrypt/hash. Readiness не становится ready только от discovery success. |
| R14 | Явно ли отложены права на действия? | PASS — base§8/8.1/T116–118: actual queue pair, matching intent/history/tombstone conflicts, account/epoch/currentness/root inventory и adoption отдельно; result не даёт migration/GC/capture/upload/playback/delete permission. |

## Пригодность реального reuse и обязательные условия SOURCE review

Files.cpp:90–218/230–286 уже содержит confined State/openFile/inspect,
private ACL, ancestor leases и exact16 identity read. Discovery должна
переиспользовать эти проверки, а не вводить второй path/security backend,
публичный generic role selector или второй scanner. Fixed bootstrap/queue
paths выбираются нативным кодом; package directory из JSON отсутствует.

**Существующий `identity(..., writer=false)` на Files.cpp:166–178 открывает
store с FILE_SHARE_WRITE. Это не доказательство требуемой стабильности нового
discovery.** Новый private discovery должен удержать оба store handles с
FILE_SHARE_READ only и сравнить их значения. Для object IDs допустимо прежнее
writeExisting exclusion без фактической записи; обе native leases переводятся
в blocked-write состояние до retained результата. Равенство store IDs не
заменяет confined path/ACL/actual handles. Missing/invalid fixed ID — отказ,
не virgin initialization внутри этого overload.

Metadata.cpp:534–590 уже имеет один bootstrap semantic consumer на прежнем
Files BOTH validator, typed cleanup/cancellation и charged result. После
discovery **не вызывать повторно public known-context read(root, own, queue,
cancel)**, заново открывающий уже удержанный exclusive bootstrap: это конфликт
lease. Использовать тот же внутренний validator на уже открытом bootstrap
owner, с передачей reserved queue owner в private result. Не дублировать
алгоритм выбора/DPAPI/strict codec и не собирать proof из naked caller JSON.

Один native job/pin должен обслуживать compound factory; discovery не
приобретает второй job через вложенный public factory. Два Files owners и
store/object handles удержаны на всём validation пути. Cleanup при second
open, codec, cancellation или allocation failure освобождает оба владельца
до возврата admission; pin результата освобождается после leases. Exceptions
при построении result/control block не оставляют утекшую lease reserved queue
ID. Сам существующий id.bin не удаляется и не изменяется при cleanup.

Прежние typed errors/native codes не маскируются: confinement/identity,
IO/sharing, codec/protection/hash, quota/allocation и cancellation остаются
различимы. Отсутствие queue indices не ошибка **reservation discovery**;
unreadable/invalid queue ledger этим не признан годным — он пока не проверен.
Даже mode=protected без проверки actual queue pair не даёт admission.
Mode=migrating без matching durable intent также не даёт migration permission.

## Что main обязан доказать до SOURCE approval

Это ожидаемые регрессии, не результаты уже выполненных проверок Round264.
Использовать существующие Files/Package/native fault targets и настоящую
private DACL/DPAPI fixture, без новых targets/frameworks и без профиля клиента.

- Genuine bootstrap BOTH positive: protected и migrating forms; fixed queue
  reservation без indices как initial migration cut, без empty-ledger claim.
  Own contexts/generation и expected queue берутся из fixed native IDs.
- Exact16 size/short IO, missing store/bootstrap/queue ID, actual store mismatch,
  JSON queue mismatch, bad lower/higher peer/schema/DATA: whole typed failure.
  No create/repair/scan/write/rename/flush; inventory/counters остаются прежними.
- ACL/reparse/hardlink/path violations на fixed locations fail closed; actual
  attempts store write/delete и bootstrap/queue identity writer при живой
  owning копии result отклоняются; после последнего release leases снимаются.
- Null/pre-cancel без IO, mid-discovery/validation cancel, actual native IO/
  protection/hash faults, job4/pin32/owned budget refusal и повтор после
  cleanup; никакого partial result или второго вложенного admission.
- Known-context overload сохраняет прежние accepted semantics/tests; один
  common BOTH validator, current fields/wipe/owner construction и cleanup
  source-reviewed. Release/Debug/native/portable/SDK проверяются на точных
  frozen inputs; native handles/lifetime не доказываются portable PASS.

## Текущий checklist/task/analyze inventory и отсутствие изменений

До нового отчёта122 Markdown files: **10 действующих нормативных наборов,
154 checked/0 open**, отдельно112 historical/context,256 checked/10 historical
open. Последние не превращаются в новые требования и не закрываются здесь.
Нормативные counts: requirements22, security27, ux25, audio-capture24,
advanced-routing14, calendar-launcher5, calendar-operation8, calendar-wire5,
packed-writer12, privacy-pause12; во всех open0.

Tasks:120 total/93 checked/27 open. Scoped coverage FR-012/013/022 и SC-006
4/4, unmapped0; ambiguity0, новых задач0. Владение реализации — существующий
T116/#7444; OPEN tracker state supplied main, отдельный live GitHub запрос
reviewer не выполнял. Это не whole-feature анализ покрытия120 tasks/всех SC.
T116/T117/T118/T119/T120, H250, legacy AAC RED257/B1 и application adoption
остаются открытыми. Последний supplied full native49/50 — не GREEN; его
known legacy failure не является новым PASS/новым отказом Round264.

Лично parsed extensions.yml: **каждая из шести** before/after implement,
analyze, checklist содержит один зарегистрированный git.commit hook,
enabled:false. В каждой enabled0, всего dispatch0. Историческое утверждение
об отсутствии before registrations неверно; старые immutable reports здесь
не исправлялись. Hooks/GitHub/VM/tests/EXE/app самим reviewer не запускались.

## SHA-256 текущих оснований

| Artifact | SHA-256 |
| --- | --- |
| constitution7.1.0 | `d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859` |
| spec | `b411bfb620e9d571422f9c423b0ae193ed70e87303d08e84a4b9844e32f81658` |
| plan | `527e660d9e1682e7a0f0a79118ea4bab38d4c174542b49c0113f571528a5b89c` |
| tasks | `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f` |
| quickstart | `fc225d2ec40cc26a7fad0bc6d7adcb22d7f4d676fcdf70b2e645dbbdb06ddb8e` |
| data-model | `8dd54012c3bfe4003cd18db98ebc67e0b7730cbbdfb6523b881cce4cdc15ec19` |
| base contract | `ec93d11c474cb970d57c2324518d541cd9fb3e7bb7f2f807d63d612ad878624a` |
| packed contract | `a1dedd9d5b7ce02e4a6c200a300b0423bcada82192217e2a79f9773428c4a7b5` |
| extensions.yml | `ad728fdff37fe1783903777fbdf792fc44752f2818d1765c76a7e1bea9dabb6c` |
| Metadata.h | `7c5cd425b94bba971bad960cd8ee16d87627706ce5a58214e58e2fa71e75f237` |
| Metadata.cpp | `4153506b4fd768869a3f1d2323c232d59bf0ddad786dc9c3733b187afceb8397` |
| Files.h | `d3d792efba7b0c4016169fb4aac1ab330bc7b4c349b9d87f3501d873857a7a17` |
| Files.cpp | `c23acf733011e9bcf4d80589d6a00e96a94a516866b822f95f436c49b9a70bd8` |

До записи captured exact sorted basename+space+SHA+LF inventory122:
`52dc3f60527c68b4f1bbdfb708c952794ec2bbaebcff5be70e6eed32abebc745`.
После записи лично сверены все прежние122 SHA: mismatches0, добавлен только
этот новый reviewer-owned report (теперь123 files). Tasks SHA неизменён;
`git diff --check` PASS. Прежние reports/markers и implementation не менялись.
