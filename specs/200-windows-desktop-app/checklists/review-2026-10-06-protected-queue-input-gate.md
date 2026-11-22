# Round266 — REQUIREMENTS: владеемая пара защищённых queue bytes

Дата:2026-10-06. Независимый requirements/checklist/scoped analyze до RED/code.
Canonical `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`,
branch `codex/200-windows-followup`, HEAD
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`; dirty preserved.
Lane **high-risk-product**, существующий T116/#7444.

## Решение

**SCOPED REQUIREMENTS GO к RED/реализации уточнённого Round266 proposal.**
C0/H0/M0/L0 новых неустранённых замечаний этой области; blocking clarification0.
Порог existing storage analyze: нет unresolved CRITICAL/HIGH и блокирующего
уточнения. Уточнения readonly-exclusive discovery и try-lock включены в это
решение; первоначальный вариант с `queueLease_->blockWrites()` не принимается.

Допуск относится только к настоящему retained input из обеих queue slots:
private-ctor `ProtectedCustodyQueueInput::read(shared_ptr<const BootstrapPair>,
nonnull cancellation)` в существующих Metadata.h/.cpp, минимальная поправка
private Files discovery и существующие native FilesTests. Нового parser,
schema, target, public unblock, controller или зависимости нет.
Это **не SOURCE approval**, не semantic queue authority, admission/mutation,
bootstrap recovery/migration или завершение T116/Windows. Реализация и новые
проверки Round266 ещё не выполнялись reviewer и не объявляются PASS.

## Прочитанные нормативные основания

Лично прочитаны `speckit-checklist` и `speckit-analyze`, canonical AGENTS,
guidance README/worktrees/spec-kit-flow/product-gates/tracker, constitution
7.1.0 и относящиеся release guidance/PRD/current-status разделы. Сверены
active feature pointer/prerequisites и относящиеся spec/plan/tasks/quickstart/
data-model, base custody contract §§1–5,7–8.1, packed contract§1/§6 budgets.
Повторно прочитаны все154 действующих критерия десяти normative checklists;
исторические reports инвентаризированы отдельно, не повторная общая приёмка.
Accepted bootstrap/discovery и correction265 decisions сохранены в их области.
Прочитаны actual Metadata/Files pair/discovery/open/read paths, Memory/Codec
ownership и существующие generated bootstrap fixture/metadata commit patterns.

Область соответствует FR-012/013/022, SC-006 и T116:568; plan:1501–1597,
data-model§12, quickstart§12. SC-003 memory/worker constraints применены как
неизменные ограничения, не как пройденная полная performance/audio приёмка.
Constitution III/IV/VI сохранены: нет egress, ложного purge, plaintext fallback
или обхода независимого gate. T117/T118 и текущая Mac parity цель не заменены.

Prerequisites checklist-template вернули active200 и шаблон. Skill analyze
указывает `--require-spec`, отсутствующий в установленном script: сначала
получен отказ unsupported option без изменений, затем прочитан --help и
выполнен поддерживаемый `--json --require-tasks --include-tasks`; spec/plan/
tasks существование и paths проверены отдельно. Это tooling discrepancy,
не пропуск проверки spec и не запуск hooks.

## Качество требований / scoped coverage

Таблица оценивает полноту/ясность proposal и действующих норм, не будущий код.
Новых checkbox markers не создаёт. Traceability15/15.

| ID | Вопрос к требованиям | Оценка и основание |
| --- | --- | --- |
| R01 | Определён ли независимый источник queue identity? | PASS — base§2/8.1: genuine discover-created BootstrapPair с retained fixed queue/id.bin, обе bootstrap semantics сверены с тем же ID. JSON не выбирает path. |
| R02 | Исключена ли подмена источника caller-массивом/старым overload? | PASS — private constructor; null parent/cancel и known-context bootstrap без queueLease invalidInput. Нет reopen/discovery fallback внутри QueueInput. |
| R03 | Полны ли role/store/object отношения? | PASS — base§2/3: bootstrap role, fixed queue role, общий observed store, object ID совпадает с независимо закреплённым queue ID обеих bootstrap slots; opaque zero/equal IDs не запрещаются произвольно. |
| R04 | Разделены ли reservation и готовая очередь? | PASS — base§8/8.1: отсутствие reserved queue indices может быть valid migration fence для BootstrapPair, но QueueInput отказывает без BOTH; не возвращает empty ledger. |
| R05 | Ясны ли правила BOTH/selection/no rollback? | PASS — base§4: существующий physical validator; оба indices и все DATA refs, g1 decoded equality, post-g1 placement/highest valid selection. Любой bad/missing peer блокирует весь result. |
| R06 | Полны ли byte-shape и bounds? | PASS — base§3 и proposal: каждый payload positive≤4MiB, exact entry count/tail, только DATA; ZERO/пустой payload не становятся queue JSON. Overflow/касты/размеры проверяются до allocation; chunk≤256KiB. |
| R07 | Определена ли владеемая immutable граница? | PASS — base§4/5/7: две charged byte copies и indices/context; const borrowed views действуют только при retained owner. Parent bootstrap/queue/store/ancestors удерживаются до последнего владельца, не naked array/path cache. |
| R08 | Разделены ли readonly и sticky failed? | PASS — уточнённый proposal: после successful discovery locks writable=false; handles/share/access неизменны. blockWrites/failed никогда не сбрасывается ради чтения. |
| R09 | Полна ли конкурентная граница общего lease? | PASS — base§4/5: private BootstrapPair mutex, try_lock после NativeJob, conflict/ERROR_BUSY без ожидания; удержание через pair/decode/publication. Нет второго registry или writer relaxation. |
| R10 | Определены ли отмена и реальные lifetime границы? | PASS — base§5/7: nonnull token, pre-cancel до IO, before/after compound pair, каждого readBlock/openBlock, после allocation/transfer до успеха. Нет принудительного освобождения active native call. |
| R11 | Измеримы ли общие quotas и cleanup? | PASS — base§5, packed§6: jobs≤4, pins≤32, owned≤64MiB; charged payloads/indices/result/control block, wipe и release. Retained queue results не cache, новые quotas не создаются. |
| R12 | Полны ли типизированные отказы/повторы? | PASS — existing errors/native codes сохраняются; busy/pre-IO quota/cancel не дают partial result. Sticky native validation fault требует fresh owner/reconciliation, не reset/empty queue. |
| R13 | Сохранены ли logical codecs и platform границы? | PASS — base§1/8.1: v3/read-v2 bytes без нового parser/schema; unsupported platform не даёт fabricated success. Bootstrap.v1/queue physical v1 не packed fallback. |
| R14 | Исключены ли effect/adoption полномочия? | PASS — base§5/7/8: raw payload не semantic candidate/current account/epoch/intent/mutation/network/delete proof. Future consumer обязан проверить их самостоятельно. |
| R15 | Есть ли проверяемый следующий этап к конечной цели? | PASS — T116/117/118, plan dependency order, quickstart§12: input pair перед bounded logical decoder/adoption, затем writer/recovery/upload/playback/delete hookup. Unwired prerequisite не закрывает приложение. |

Scoped coverage FR-012/013/022+SC-006:4/4 имеют T116; unmapped0,
ambiguity0/duplication0 новых этой области. Это не whole-feature coverage120
tasks и не снятие existing open tasks. Реализация владеется T116/#7444;
Fresh OPEN/canon labels state supplied main, local tasks также open. Live GitHub reviewer не
запрашивал и состояние не менял. Новое issue/task не требуется.

## Две причинные поправки и отмена

Actual Files.cpp:372 `blockWrites()` ставит `state_->failed=true`.
`readValidatedSnapshotImpl`:544 сразу отвергает этот state с writerFailed.
Metadata.cpp:574 применяет blockWrites к reserved queue. Значит исходное
повторное чтение этого lease неработоспособно; нельзя лечить публичным
unblock/reset, изменением stickyfailure или новым open поверх exclusive ID.

Принята минимальная поправка: private discover/openImpl сохраняет те же
GENERIC_READ|GENERIC_WRITE object-ID handles и FILE_SHARE_READ exclusion,
immutable store/ancestor locks. **Только после successful identity locking**
ставит writable=false до return. Queue discovery убирает redundant blockWrites;
bootstrap own lease всё ещё blockWrites после собственной полной проверки.
Это не ослабляет Failed state или доступ writer к другим open modes.
Все writeBlock/publishIndex/next-version/write-reserve entrypoints на такой
lease должны отказывать до write/flush/rename. Public writable Files наружу нет.

Shared queueLease имеет mutable failed state; even readonly validation нельзя
исполнять одновременно на одном parent. Private try-lock в BootstrapPair
сериализует именно эти вызовы, без ожидания UI и нового owner registry.
Busy получает typed conflict/ERROR_BUSY, не повреждает lease и допускает
retry после выхода первого call. Чужие будущие consumers того же lease обязаны
использовать ту же границу, не обходить её отдельным validator.

Existing readValidatedMetadataPair полностью ограничен queue cap: два indices,
не более16 DATA blocks в каждом, максимум32 referenced block visits. Внутри
readBlock уже выполняется native decode/integrity; после этого собираются
оба exact payloads, без повторного whole-file parser. До выделения любого
целого payload buffer проверяются **оба** positive lengths≤4MiB и DATA-only
closures, не сначала allocation выбранного slot и лишь затем проверка peer.
Для **данного чисто
readonly byte prerequisite** before/after существующего compound helper
достаточны: mid-helper cancellation наблюдается после actual return, результат
не публикуется, job/parent удержаны. Новый per-inner-read cancel API не является
условием этого gate. Нет обещания мгновенной отмены, hard timeout/latency
или остановки зависшего OS вызова. Далее каждый consumer readBlock/openBlock
получает собственные checkpoints; UI/network/effects здесь вообще отсутствуют.

NativeJob удерживается через весь synchronous flow, включая cleanup частично
созданных buffers/indices/result и last input-owner release. Важны ordering
member/local destruction и throwing moves Debug CustodyVector/control block:
сначала готовить throwing storage, потом переносить pin/parent; не терять
admission при allocation exception. Final success cancel после построения
owner/control block также обязателен. Две copies до8MiB учитываются в shared
64MiB как retained candidate/result, не объявляются бесплатным cache; scratch
остаётся bounded по block и прежние cache/native limits не увеличиваются.
MF/DPAPI private allocations не объявляются частью доказанного owned budget.

Native pair fault может sticky-poison parent. Повтор после job/pin/busy отказа
до Files допустим на прежнем owner; после sticky validation failure требуется
release прежнего parent/children и fresh verified discovery по existing rules.
Ни cancellation, ни quota test не должны сбрасывать failed для удобного retry.

## Обязательные доказательства следующего SOURCE этапа

Это требования к main validation, **не уже исполненный PASS** Round266.
Reuse existing FilesTests Fixture/bootstrap helpers и commitProtectedCustodyMetadata.

Начальный RED — настоящий build-success/native positive assert нового input
на существующем blocked queue discovery: writerFailed, а не compile-only
отсутствие API. Final имени результата `ProtectedCustodyQueueInput` не приписывает
semantic queue readiness/права; исходное слово QueuePair было заменено до gate.

- Native DPAPI genuine g1 BOTH equality и g2 с разными old/current payloads;
  exact slots/lengths/bytes/selection, multi-block/tail и exact4MiB/+1. Старый
  peer тоже decoded; current-only positive не заменяет BOTH proof.
- Missing reserved indices, singleton, bad lower/higher index/DATA/context/
  SHA/tail, empty/ZERO и ID conflict: typed whole failure, no empty/default
  ledger; source artifacts retained. Existing known bootstrap overload без
  discoveryqueuelease отвергается, не повторное открытие fixed directory.
- Discovery readonly transition: no accepted writable method/no actual
  write/rename/flush, immutable store и exclusive object locks unchanged.
  Child удерживает parent после release внешней bootstrap копии; обе bootstrap
  и queue identity writer/delete attempts blocked до последнего child release.
- Null/pre-cancel reads0; mid-compound/each-block/final-transfer cancel не даёт
  result; cleanup/retry без fake interrupt. Concurrent try-lock busy и retry
  после release; shared state не обращается параллельно и не reset failed.
- Native read/DPAPI/hash failure, actual job4/pin32/shared budget/refusal,
  allocation at partial payload/object/control construction, wipe/free before
  admission release и retry с правильным fresh-owner правилом. Debug allocator
  proxy тоже charged; нет full pipeline quota claim по одному input test.
- Fresh frozen source/native Release+Debug, portable applicability/SDK,
  personally readable immutable logs/receipts до SOURCE approval. Generated
  fixtures only; VM не physical audio/installed proof. Не требую новых targets,
  устройств, рабочего профиля или повторов исторического full suite сейчас.

## Inventory / hashes / сохранённые открытые границы

До записи127 Markdown files:10 current normative,154 checked/0 open;
отдельно117 historical/context,256 checked/10 historical open. Counts:
requirements22,security27,ux25,audio-capture24,advanced-routing14,
calendar-launcher5,calendar-operation8,calendar-wire5,packed-writer12,
privacy-pause12; во всех open0. Historical unchecked не recast new obligation.
Exact basename+space+SHA+LF inventory127 SHA
`dd1e72d6af3432eaa5d062dfa7ba852e3424f00061704e3e7cbeba918e79a845`.
После записи лично проверена сохранность всех127 и только один added report128.

Tasks120/93checked/27open, SHA
`80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f`.
Все before/after implement/analyze/checklist registry stages содержат1
registered git.commit enabled:false; всего enabled0/dispatch0.
Ни hook/VM/test/GitHub/app/commit reviewer не запускал. Metadata-only evidence.

| Artifact | Текущий SHA-256 |
| --- | --- |
| Constitution7.1.0 | `d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859` |
| Spec | `b411bfb620e9d571422f9c423b0ae193ed70e87303d08e84a4b9844e32f81658` |
| Plan | `527e660d9e1682e7a0f0a79118ea4bab38d4c174542b49c0113f571528a5b89c` |
| Quickstart | `fc225d2ec40cc26a7fad0bc6d7adcb22d7f4d676fcdf70b2e645dbbdb06ddb8e` |
| Data-model | `8dd54012c3bfe4003cd18db98ebc67e0b7730cbbdfb6523b881cce4cdc15ec19` |
| Base contract | `ec93d11c474cb970d57c2324518d541cd9fb3e7bb7f2f807d63d612ad878624a` |
| Packed contract | `a1dedd9d5b7ce02e4a6c200a300b0423bcada82192217e2a79f9773428c4a7b5` |
| Extensions registry | `ad728fdff37fe1783903777fbdf792fc44752f2818d1765c76a7e1bea9dabb6c` |
| Metadata.h | `fb15d53480d1281f5ffb1e6eea428c1b8ecca19d67a27d2d4b1b1cef8efc4480` |
| Metadata.cpp | `f7eb2cf8cfb1d9ad524461c5c3501e3984762ce050742a0ef0e8bf93c5d6c2ae` |
| Files.h | `9bbb8305400a31dd6a5765da31f37f26bff1bc3548f5df156081e638146dde5f` |
| Files.cpp | `95d40e76dc8404d1703594c3100a88eff22c65077e85f3aba148ad77abae7b36` |
| Memory.h | `a5a67fb3448f07d4232cf8dee893e60e65c3eea5687a0908f4469226be2000ad` |

Новому private immutable QueueInput есть конкретная необходимость: charged
bytes должны владеть proven parent/leases до использования. Помещение mutable
queue buffers в существующий bootstrap result смешало бы его own-record и
queue scopes; naked arrays не удерживают owner. Nested retained QueueBytes
с теми же private/lifetime guarantees допустим по сути, но не уменьшает
необходимую работу. Не вводить вторую selection/decrypt algorithm или public
Files access ради названия класса. Минимальная private friendship для доступа
к уже verified context не расширяет публичные mutation полномочия.

**Следующий этап после компонента:** exact bounded logical queue decode в
shared allocation domain + expected owner/context/currentness и matching
durable intent, затем typed worker adoption/mutation и actual callers. Они
обязательны T116, не могут быть подменены успехом двух byte buffers.
T116–T120/T117 migration/H250/B1/legacy AAC и вся application acceptance
остаются открытыми. Последний full native265k49/50 — НЕ GREEN; его известный
AAC counterexample не новый finding и не результат Round266.
