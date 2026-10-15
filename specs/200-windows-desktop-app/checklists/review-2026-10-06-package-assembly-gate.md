# Независимая проверка требований Round254: совместное чтение запечатанных refs

Дата: 2026-10-06. Владелец: независимый reviewer.
Feature200 / T116 / dependency5; полоса high-risk-product storage.
Единственная разрешённая запись — этот новый отчёт. Старые checklist markers,
spec/plan/tasks, код, GitHub и runtime reviewer не изменяет.

## Конечное решение

**REQUIREMENTS APPROVED / scoped GO — ALL-SEALED refs BOTH physical slots.**
Качество требований: **20/20; CRITICAL0/HIGH0/MEDIUM0/LOW0**, без нового
продуктового вопроса, schema, численного допуска или задачи.
Main может после личного прочтения начать RED и реализацию именно этого
совместного readonly prerequisite. Source ещё не написан и **NOT REVIEWED**;
build/VM/runtime/installed execution reviewer **NOT RUN**.

Разрешена одна worker-only перегрузка существующего Reader, принимающая
trusted root, собственную удерживаемую `ProtectedCustodyPackagePair` и owned
cancellation. Результат — фиксированная таблица 2×5 readonly streams:
каждый ref обеих slots проверен; ячейки вне соответствующего refCount пусты.
**Любая live-ссылка в любой slot отклоняет весь batch до member IO.**
Пропуск live edge, null→empty/sealed, частично успешная таблица запрещены.

Один внутренний bounded lifetime group удерживает Pair, до пяти физических
role owners и до десяти immutable proofs/snapshots. Каждый ReaderState и
Clone разделяет этот group; group не содержит Readers/streams. Один object
не открывается повторно для второго slot. Это необходимый держатель реальных
leases, не второй scanner, registry, backend, dispatcher или proof authority.

**НЕ ПРИНЯТЫ:** полная сборка/проверка normal package, live capture recovery,
фазы/manifest/v5 formats/duration/trusted prefix/short predicate, bootstrap/
intent/barriers, аккаунт/epoch/admission, V5/MF/transport/playback wiring,
upload/delete/GC, T116 целиком, T117/T118/T120, working profile, установленное
приложение, hardware и release. **H250-1/H250-2 остаются открыты.**
Это ограничение следующего шага разработки, не сужение конечной цели Windows.

## Почему live исключён из этого конечного GO

Base contract §4/§8.1 и packed §5/§6.1 разрешают live refs в capturing/
finalizing. Canonical recovery выбирает реальный checkpoint и доверенный
полный-frame prefix `floor(length/1920)×1920`; null triple не означает пустую
запись. Flat media recovery может иметь validated singleton/trustedPrefix,
тогда как sealed proof требует обеих проверенных actual indices и exact
generation/length/SHA. Packed cold normal proof требует actual paired heads.

Следовательно, ранний вариант «одинаковая строгая пара для любого live ref»
не доказывает полный recovery. Принят последний выбранный main срез:
ALL-SEALED, отказ целиком до открытия member при любом live. Это не запрет
нормативного recovery и не permission обойти его. Возможный случай, когда
selected sealed state соседствует с прежним capturing/finalizing live state,
здесь ещё не обслуживается и **не даёт normal admission**. Его реализация
остаётся в T116; deleting/replacing старого slot ради успеха запрещено.

## Минимальная форма и переиспользование одиночной перегрузки

Общая проверка должна использовать существующие Files/Tree/Reader/Hash:

1. До member IO проверить owned Pair/token, каждый refCount≤5, ALL-SEALED,
   fixed roles и совместимость identity обеих slots. Pair — существующий
   непридумываемый provenance object, не отдельно поданный parsed value.
2. Store/directory принадлежат собственной Pair; role/object/representation/
   container принадлежат её exact ref. Fixed confined role location задаёт
   путь. Same-role refs обеих slots обязаны согласовать object ID,
   representation и container; конфликт отвергается, а не получает другой
   file owner/path. Нельзя использовать один object ID для разных roles.
3. До IO/allocations получить прежние admission/budget reservations. Создать
   один фактический owner на role и разделить его между обеими snapshots.
   Не строить карту размером с запись, список блоков или global registry.
4. Flat: reuse actual `readValidatedSnapshotImpl` BOTH validator, selected и
   actual peer. Оба slots и DATA проверены; exact generation берётся только
   из реально доступного index. Singleton/trustedPrefix для sealed batch
   отклоняются с original first error. Older unavailable index —
   recoveryRequired, без реконструкции из names/version/SHA и третьего index.
5. Packed: reuse `verifyRetained` под общим owner, полная current BOTH-head
   closure и каждого защищённого retained stamp, включая root вне current
   heads. Identity/context/generation/extent/ref/tail проверки не заменяются
   cache или строкой root. Historical descriptor не подменяет current heads.
6. Каждый sealed ref имеет exact logical length и whole SHA; reuse charged,
   wiped `sha256ProtectedStream`, настоящий EOF и успешный rewind0. Одинаковые
   identity/generation не разрешают конфликтующие length/root/hash. Нельзя
   выдавать digest ciphertext/file_size или hash одного удобного slot.
7. Вернуть таблицу только после проверки всех refs, сохранения всех actual
   leases и последней cancellation/failure проверки. Ни один Reader не
   выходит из factory при отказе любого sibling.

**Delegation одиночной sealed перегрузки в новый batch допустима** как явно
выбранная main строгая надстройка той же проверки. Её прежний preflight
slot/ref/null/target-live rejection сохраняется до batch; затем она может
переместить requested stream из общей таблицы. Returned stream всё равно
удерживает весь group до last Clone. Гарантия одиночного API была проверкой
его sealed bytes, не обещанием успешного возврата при любом непроверенном
sibling. Дополнительный fail-closed отказ не вводит новые полномочия.

Это **осознанное ужесточение области успешных входов**: ранее допустимый
здоровый target с live/повреждённым sibling теперь отклоняется. Оно должно
быть явно отражено в новом API комментарии/документации и регрессии, а не
названо полностью неизменным поведением. Historical Round253 report не
переписывается: он описывает свои frozen bytes. Полный live recovery и
consumer availability таким отказом не принимаются. Если main предпочитает
сохранить одиночную success domain, допустим маленький общий private helper
с теми же validators, без копирования scanner; второй публичный backend
не нужен. Этот GO не требует конкретного private friend spelling.

## Lifetime, ошибки и неизменные ресурсы

Все returned streams/Clones сохраняют **весь** group, не только свой owner.
Сброс таблицы, Pair у caller и девяти streams не разрешает metadata/member
mutation, пока последний stream/Clone/native operation жив. Cursors отдельны;
generation/length/proof immutable; никто не получает Files/HANDLE/Writer.
Member handles/proofs и plaintext освобождаются прежде parent Pair/pins;
throwing move/allocation не передаёт lease до безопасной подготовки result.
Нет destructor IO, auto-commit, forced close по timeout или ownership gap
между проверкой и возвратом. Last release — существующий worker-only путь.

Общий sticky failure — одно first-fault состояние group, без цикла владения.
Observed member failure не обходится чтением другого sibling из того же
group. Shared status распространяется также на Clone; repeat/cancel/new
invalid input не затирают уже наблюдённую первичную причину. Factory error
сохраняет существующие typed/native distinctions, особенно M253-1 original
peer error, а не маскирует всё generic recoveryRequired. Cancellation до/
после IO/hash/return не уничтожает ещё выполняющийся call, buffer или owner.
При отказе — no value/partial stream и retained original artifacts, не empty
ledger, repair, representation downgrade или plaintext fallback.

**Owned64MiB/process, pins32/process, native jobs4/process, cache2MiB,
chunks≤256KiB неизменны.** Новый group/state/control-block, indices и их
capacity, staged result и hash buffers входят в прежний owned charge до
allocation. Native DPAPI/MF allocations не объявляются доказанной owned quota.

Fixed 5/10 bounds сами по себе не доказывают quota. Для текущих primitives
консервативный постоянный count: Pair1 + owners≤5 + proofs≤10 + Readers≤10
=≤26 pins; temporary ciphertext/plain read добавляет свои admission pins,
Clones конкурируют с тем же общим32, не получают отдельный лимит. Фактический
легальный packed role set только canonical/media/playback уменьшает peak;
source review обязан проследить actual temporary/nested lifetimes, а тесты —
давление бюджета. Нельзя удерживать ненужные промежуточные Tree proofs или
дублировать owners и затем увеличить32. Native operations выполняются
последовательно; outer job + helper/Guard/read jobs также делят общий4.
Это обоснование реализуемой bounded формы, **не измеренный runtime peak**.

## Requirements-quality / scoped analyze

PASS ниже означает достаточные существующие нормы для предложенного среза,
не выполненную реализацию. Новых checkbox markers нет.

| ID | Проверенный вопрос | Основание / результат |
| --- | --- | --- |
| R01 | Определена ли задача и bounded ALL-SEALED область? | PASS — T116, plan dependency5:1586–1588; выбранный main scope не принимает full consumer. |
| R02 | Обязательны ли refs обеих physical slots, не selected-only? | PASS — base §§5/8.1, packed §6.1, model §§12/13. |
| R03 | Однозначен ли whole-batch live rejection до member IO? | PASS — отдельные live/sealed semantics base §§4/8.1; исключение recovery из этого среза явно сохранено. |
| R04 | Доказано ли own Pair provenance, без caller-created authority? | PASS — существующая Pair API/private constructor, metadata-pair gate; own context/indices/values held. |
| R05 | Достаточны ли fixed identities/locations и запрет конфликтов? | PASS — base §2/§8.1, packed §§2/6.1; fixed role path не допускает двух разных identities одновременно. |
| R06 | Определён ли один actual owner при двух snapshots? | PASS — packed §2; base §§5–7; owner reuse сохраняет непрерывную lease и exclusive identity. |
| R07 | Полон ли flat BOTH/exact peer/no fabricated history путь? | PASS — base §§3/4/6, previous member gate R06/07; actual shared validator reuse. |
| R08 | Полон ли packed current + historical full closure? | PASS — packed §§3/5/6.1; accepted retained-root primitive не self-authorizes stamp. |
| R09 | Явны ли whole logical SHA/length/EOF/rewind? | PASS — base §6/§8.1, packed §6.1; member gate R13 и existing direct hash. |
| R10 | Отделены ли actual bytes от normal formats/manifest/phase? | PASS — FR-011/012; base §4/§8.1; этот batch не принимает normal/degraded/short semantics. |
| R11 | Удерживает ли каждый stream/Clone все physical owners? | PASS — base §§5–7, packed §2; fixed shared group необходим, временной таблицы недостаточно. |
| R12 | Независимы ли cursors и запрещены ли mutable capabilities/cycles? | PASS — base §6, packed §2/§6.0; existing ReaderState/Clone reused, group не содержит streams. |
| R13 | Есть ли shared first-fault без частичного успеха? | PASS — base §§3–7, packed §§1/2/5; M253-1 остаётся регрессией original cause. |
| R14 | Определены ли owned cancel/actual completion/throwing transfer? | PASS — base §§5/7, packed §2; отмена UI не уничтожает actual leases/jobs. |
| R15 | Сохраняются ли process memory/cache/pin/job limits? | PASS — base §5, packed §6; fixed group bounded, все ресурсы конкурируют в прежних caps. |
| R16 | Сохраняются ли wiped plaintext и worker-only IO? | PASS — FR-012/021, base §§1/5/6; no URL/tmp/export/content evidence. |
| R17 | Отделены ли account/effect/delete/GC/migration gates? | PASS — FR-013/014/022, base §§7/8, packed §6.1; batch только bytes/lifetime. |
| R18 | Допустима ли strict-superset delegation без второго scanner? | PASS — выбранное main ужесточение явно названо; preflight сохранён, новый scope не выдаёт старой success-domain гарантии. |
| R19 | Есть ли сопоставимые новые source/runtime проверки без old PASS? | PASS — quickstart §§12/14, T116→T117→T118; отдельный frozen review и exact source/EXE receipts. |
| R20 | Не создаются ли дубли tasks/schema/backend и ложный feature GO? | PASS — существующая T116/dependency5 владеет всем prerequisite; acceptance задачи остаются открыты. |

Scoped coverage: FR-011/012/013/014/022 и SC-006 → существующая T116:
**6/6 (100%), executable tasks1, unmapped0, ambiguity0, duplication0**.
Constitution II/III/IV/VI сохранены: Stop/visible capture, серверная
observability, deletion truth и независимые evidence gates не меняются.
Это не full-feature analyze22FR/10SC/120tasks.

### Сохраняемые границы, не дефекты требований выбранного ALL-SEALED шага

- B254-1: live recovery, включая flat singleton/trustedPrefix, **не принят**.
  Первоначальный более широкий вариант не доказал его семантику; narrowing
  implementation step устраняет ambiguity этого gate, не выполняет recovery.
- B254-2: full normal package/manifest/WAV/AAC/duration/phase/admission ещё
  **не принят**. Optional common format inspection из раннего сообщения
  main не включён: нужна точная отдельная consumer область и её review.
- B254-3: actual lifetime/budget/fault correctness будущего diff требует
  source и validation review. Ни fixed array, ни20/20 requirements не PASS
  реализации. H250/source-consumer debt/T117/T118 не сняты.

## Минимум следующего source/validation review — NOT RUN

- RED отсутствующего batch API; schema1/2, обе slots, all5roles, разные
  refCount/orders; любые null/bounds/live/identity/representation conflicts
  отказ до member IO. Непустые old/current bytes и разные SHA обязательны.
- Same physical role в обеих slots: один actual lease, разные readonly
  generations. Flat current/peer и packed historical root вне current heads
  дают именно свои bytes/lengths; будущий/conflicting stamp отказ.
- Повреждённый nonrequested sibling и lower-only ref отклоняют весь batch
  и delegating single; live sibling отклоняет их целиком, а не пропускается.
  Original peer DATA failure из M253-1 сохраняет exact typed/native reason.
- Release original Pair/таблицы/всех streams кроме одного Clone: ВСЕ member
  и parent mutations ещё excluded. Last Clone освобождает их только после
  actual IO completion. Independent cursors, no mutable access/cycle.
- Общий observed sticky fault инвалидирует siblings/Clones; first cause
  не заменяется поздним cancel/invalidInput. Частичный hash/EOF/rewind/cancel
  не возвращает result; charged/wiped buffers и lease release прослежены.
- Pressure pin32/job4/owned64MiB, throwing state/result/index transfers,
  retained temporary allocation и destructor/cache cleanup; no quota bump.
  Existing primitive/single-member regressions не удалять; изменённую
  success domain тестировать явно, не ослаблять original assertions молча.
- Frozen changed-file hashes/baseline, independent SOURCE verdict, terminal
  новые native/portable/SDK results по actual compiler input и EXE identity.
  Старые Round2538/8/3/3/46/46 не исполнение новых batch cases.

Reviewer builds/tests/VM/installed/hardware не запускает. Неполный execution
coverage должен быть явно назван main, не превращён в PASS этого отчёта.

## Источники, метод и существующие markers

Лично сверены canonical path
`/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`, branch
`codex/200-windows-followup`, HEAD
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1` и active feature pointer.
Dirty source определяется файловыми hashes, а не одним HEAD.
Прочитаны `speckit-analyze` и `code-reviewer`, root AGENTS/guidance index,
worktree/flow/product guides, constitution и применимые release-evidence,
PRD local-buffer/status sections. Extensions YAML parsed: enabled before/
after_analyze hooks0; state-changing hooks не выполнялись.

Действующие spec и оба custody contracts прочитаны; plan/tasks/model/quickstart
прочитаны по scoped storage dependencies и acceptance boundaries. Все десять
нормативных checklist criteria прочитаны; все101 checklist Markdown files
перечислены/hashed/count. Historical reports не объявляются полностью заново
аудированными: personally прочитаны relevant member gate/source/DOCS,
authority gate, package criteria/terminal boundaries, working-profile H250
и конечные tree/writer/cadence coverage sections. Source read ограничен
существующими Reader/Pair/Files/Tree/Owner/memory APIs, не новой реализацией.
Полная трассировка реальных consumers принадлежит main; его сообщения не
выдаются за независимый audit reviewer всех transport/AppMain/V5 callers.

Физический baseline count101files: **410 checked /10 unchecked** — это
исторические повторные markers, НЕ420 уникальных текущих требований.
Десять нормативных файлов: requirements22/0, audio24/0, routing14/0,
security27/0, ux25/0, launcher5/0, operation8/0, wire5/0, packed-writer12/0,
privacy-pause12/0; **154 checked /0 unchecked**.

Остальные отчёты суммарно256/10. Unchecked находятся в tree-source:61/62/586
(3), packed-writer-source:34/36/37/40 (4), cadence-source:34/35/40 (3).
Writer/cadence имеют последующие final9/0 в своих frozen scopes; tree final
17/1 сохраняет непроведённый exact engaged-snapshot worker error-return cut.
Это исторические evidence cohorts, не10 новых requirements blockers batch.
Ни одно из них не переотмечено. Current tasks: **120 =93checked +27open**;
T116/T117/T118/T120 остаются открыты. Новых checkbox markers в отчёте0.

Sorted baseline manifest (basename + space + SHA256 + LF):
`d419d8642d075777b4294a2e1557c5767ad010539ebc71112f77d3c40d12c662`.

## Идентичность норм и существующего Reader

| Артефакт | SHA-256 до нового implementation |
| --- | --- |
| spec.md | `b411bfb620e9d571422f9c423b0ae193ed70e87303d08e84a4b9844e32f81658` |
| plan.md | `527e660d9e1682e7a0f0a79118ea4bab38d4c174542b49c0113f571528a5b89c` |
| tasks.md | `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f` |
| data-model.md | `8dd54012c3bfe4003cd18db98ebc67e0b7730cbbdfb6523b881cce4cdc15ec19` |
| quickstart.md | `26d4595412c10968706dc3eaadd1fd242e146e1d1e954d0ebc452a6ac0ee2747` |
| constitution | `d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859` |
| base custody | `ec93d11c474cb970d57c2324518d541cd9fb3e7bb7f2f807d63d612ad878624a` |
| packed custody | `a1dedd9d5b7ce02e4a6c200a300b0423bcada82192217e2a79f9773428c4a7b5` |
| Reader.h | `a0a899339cac7f401791ed5355a1a53464a542b7e9cc034bf404aada724389aa` |
| Reader.cpp | `8c04a690f0511a4073717f0dbce837e7ab76a760a3eeb66fb925dc6af83f26de` |
| Files.h | `9c230612de5ab10a5cfb6463e1434b3efdd7267db4435826faee204655dc87f6` |
| Files.cpp | `ae784b46f417c503e592410edd7dc71ab8131592f5cfeb04c235e0a96a817b82` |
| Metadata.h | `3e1f12fda3e18463c6430921e16173afac5c549aaebfa222efcc9dd24b743478` |
| Metadata.cpp | `c917b43a94d09547be829694b6cf9c44efde0f91d03dce4c931d8534fa68a1f7` |
| Tree.h | `12221fc52c6955c3bd79efa11e37764dc93f7a80dfea25ef01704d8c742dfa6c` |
| Tree.cpp | `c308ac7159695a5a1e8edc1c65a1332481c576fff4f53b2ab270c99960d97391` |
| Memory.h | `a5a67fb3448f07d4232cf8dee893e60e65c3eea5687a0908f4469226be2000ad` |

## Терминальная граница

**Scoped requirements GO20/20 C0/H0/M0/L0 — ALL-SEALED BOTH-ref batch +
shared actual lifetime + разрешённая strict-superset delegation.**
Никакого ожидания future runtime для этого requirements решения нет.
Full package/live recovery/consumer/account/effects/migration/profile/installed/
release **не приняты**. Следующий отдельный SOURCE review — после frozen diff.
Единственная запись reviewer — этот файл. После сохранения отчёт лично
перечитан целиком: R-критериев20, новых checkbox markers0. SHA всех101
прежних checklist файлов совпали101/101; единственное добавление — этот
отчёт. Tasks SHA/count и branch/HEAD повторно совпали; git diff --check
без ошибок. Никаких продуктовых tests/runtime/VM jobs reviewer не запускал.
