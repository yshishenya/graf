# Packed media custody v2 — поправка T115, 2026-10-03

Статус: решение владельца о времени обнаружения старой порчи принято;
проект ниже подлежит независимому review/analyze перед реализацией T116.
Не является выполненной реализацией или приёмкой приложения.
Область FR-012/013/014/022, SC-003/005/006/008. Базовый контракт
`windows-protected-local-custody.md` сохраняет остальные требования.

## 1. Область и доказательство

Packed v2 применяется только к canonical/media/playback objects. Bootstrap,
queue, manifest, recovery, package-state, migration и delete intent остаются
в v1 с полной проверкой обеих metadata slots/referenced blocks и запретом
возврата к старому ledger. Явная защищённая authority выбирает representation;
ошибка v2 не разрешает decoder downgrade в v1 или plaintext.

DPAPI user scope, `CRYPTPROTECT_UI_FORBIDDEN`, CNG SHA-256 и существующая
защита памяти сохраняются. Нет собственного DEK/AES/nonce/key cache,
сетевого ключа, пароля или нового диалога. DPAPI success не заменяет exact
context/length/checksum checks. Весь content и digest находятся внутри
защищённых records; открыты лишь технические opaque IDs/framing/размеры.

Два вида RAM proof: `full` после streaming проверки достижимых данных
и `inherited_live` после проверенного перехода от доказанного root.
Оба допускают normal logical operation только в пределах того же непрерывного
GuardOwner. Это доказательство происхождения и проверенного перехода,
не свежее перечитывание всей старой записи при каждом ACK.
Скрытая порча старого DATA может обнаружиться при чтении/full verification.
Любая наблюдаемая ошибка делает owner sticky failed; нет normal effects,
нового commit или GC до полного reconciliation. Старые artifacts сохраняются.

## 2. Один непрерывный native owner

Один `content.packed-v2` в существующем confined object directory и default
file stream. GuardOwner держит проверенный native HANDLE без
`FILE_SHARE_WRITE`/`FILE_SHARE_DELETE`; разрешается только `FILE_SHARE_READ`.
Не наследовать HANDLE дочерним процессам. Проверить фактические file identity,
путь, ACL, ancestors, reparse/ADS/hard-link ограничения до content effects.
Существующий внешний writable handle/mapping либо неизвестный результат
проверки — отказ, не обещание исключительности по одному pathname.

Токен proof содержит owner epoch, native identity, container ID и exact root
descriptor. Он не сериализуется и не переносится в другой ownership epoch.
Reader/Clone имеет собственный cursor и pin; writer/finalizer/read/hash/upload
jobs, незавершённые native operations и retained results разделяют тот же
owner. Writer release лишь отзывает write capability. Last actual release
после I/O завершения закрывает HANDLE, уничтожает proof и затем отпускает pin.
Cancel/timeout не освобождают работающий DPAPI/I/O owner или его buffers.

ACK readback выполняется независимыми positioned reads того же HANDLE после
освобождения writer plaintext/cipher copies, не закрытием/reopen файла.
Native I/O сериализуется существующей ownership/admission дисциплиной;
у caller нет общего file pointer. Чужой процесс не наследует RAM authority.

## 3. Точный wire и пределы

Все числа little-endian без native struct padding. Unknown magic/schema/kind/
role/flags, nonzero reserved/padding, overflow, extra/truncated bytes — отказ.
IDs по16 opaque bytes; role берётся из уже авторизованного custody object.
Разрешены ровно CustodyRole canonical=1, media=2, playback=3; queue/служебные
роли и неизвестный integer не имеют packed decoder/live proof.
Размер блока262144B, radix64, depth3, logical length≤68719476736B.
Это предел представления, не новая квота или обещание вместимости диска.

Container prefix128B: magic8=`GRFPCV2\0`, schema u32=2, size u32=128,
store/object/container IDs16B каждый, block size u32=262144, radix u16=64,
depth u16=3, head cell size u32=16384, ref size u32=64, reserved48B=0.
Head0 offset128; head1 offset16512; append region начинается32896.
Контекст prefix сверяется с защищёнными records, сам prefix не authority.

Envelope framing16B: magic8=`GRFPEV2\0`, schema u16=2, kind u8,
role u8, DPAPI ciphertext length u32. Далее exact ciphertext, без открытых
digest/logical lengths. Обычный record заканчивается после ciphertext;
выравнивание следующего offset до16B заполняется нулями и не входит в digest.
HEAD cell содержит envelope и нулевое padding до16384B.

Typed plaintext header128B: magic8=`GRFPTV2\0`, schema u16=2, kind u8,
role u8, header size u32=128, store/object/container IDs16B каждый,
physical offset u64, logical selector u64, record version u64>0,
body length u32, flags u32=0, digest32B. Entropy domain — ASCII
`graf.custody.packed.v2` без NUL плюс LE schema u16/kind u8/role u8,
три IDs, offset u64/selector u64.
До unprotect этот контекст берётся из ожидаемого typed ref/slot, а не
из неподтверждённых plaintext bytes. Header затем проверяется целиком.

Kinds:1 DATA,2 NODE_L0,3 NODE_L1,4 NODE_L2,5 HEAD;0 EMPTY и6 ZERO
допускаются только как inline refs, не encrypted record. DATA selector —
logical block position; NODE selector — base block своего диапазона;
HEAD selector — slot0/1. Новые DATA/NODE имеют version=target generation;
старые refs сохраняют exact прежнюю version, не переписываются in-place.

| Вид | Exact plaintext/body | Полный envelope limit | Digest |
| --- | --- | --- | --- |
| DATA | header128 + payload P, 0<P≤262144 | P+4096, max266240B | SHA-256 exact payload |
| NODE | header128 +64 refs×64B=4224B |8192B | SHA-256 всего plaintext при zero digest field |
| HEAD | header128 + descriptor128=256B |16384B cell, включая framing/padding | То же whole-plaintext checksum |

Caps — пределы приложения, не гарантия DPAPI overhead. Protect output сверх
cap — отказ до append/head publication. Framing bounds проверяются до
unprotect/owned allocation; native output nonempty и exact plaintext length
проверяется до копирования. Native внутренние allocations измеряются отдельно.
Все reads/writes разбиваются на chunks≤262144B, включая ciphertext266240B.

Ref64B: kind u32, exact envelope length u32, physical offset u64,
record version u64, DATA payload length u32, reserved u32=0,
SHA-256 exact child envelope32B. EMPTY —64 нулевых bytes. ZERO —kind6,
остальные fields0; logical range следует из parent slot. ZERO допустим только
для явного zero-extension, не отсутствующего/битого DATA. NODE ref payload
length0, DATA ref exact full/tail length. Ref kind/selector/level/alignment/
offset+length проверяются по ожидаемому пути, committed extent и child header.
Child record предшествует parent в append region; циклы/forward refs запрещены.
Для каждого non-inline DATA/NODE_L0/L1/L2, включая root, сначала сверяются
exact envelope length и SHA с ожидаемым защищённым Ref, **до** DPAPI decode
или использования child refs; затем exact typed context и внутренний checksum.
Это действует для новых readbacks, base-path disk reads и cold closure всех
retained roots. DATA дополнительно сверяет exact payload SHA. EMPTY/ZERO
не имеют envelope. Cache допускается только после этих checks и по exact
owner/root/ref key, без обещания fresh disk на каждом cache hit.

Descriptor128B: generation u64>0, logical length u64, committed extent u64,
block size u32=262144, block count u32=ceil(length/262144), radix u32=64,
depth u32=3, flags u64=0, root ref64B, reserved16B=0. HEAD version= generation.
Root —NODE_L2/base0, EMPTY только при length0; диапазон вне EOF не выдаётся.
HEAD selector задаёт slot; оба birth heads могут иметь одинаковый descriptor,
но их typed headers/ciphertext/slot различаются. EOF не выбирает root.

## 4. Дерево и проверенный переход

NODE_L0 покрывает64 DATA blocks, L1 —4096, L2 —262144. Отдельный ZERO
может обозначать целый явно расширенный диапазон; EMPTY допустим только вне
logical length. Для tail DATA payload exact, прежний короткий tail нельзя
использовать как полный блок после роста. Shrink сохраняет old pinned root,
отрезает доступный диапазон нового root; повторный grow создаёт ZERO,
не раскрывает отброшенные bytes прежнего snapshot.
Целиком за EOF новые refs EMPTY; inline ZERO subtree может пересекать EOF,
но выдаются только bytes внутри logical length. Nonzero DATA за EOF не
сохраняется в новом root. При partial-block shrink текущий tail переписывается.

Неизменённые refs наследуются лишь через bounded structural diff с exact
доказанным base path. Caller не может подать произвольный root или перенести
`verified=true` из другой generation. Меняются только явно разрешённые
Write/SetSize позиции/диапазоны; все новые nodes и DATA проверяются с диска.
Усечение/расширение больших ZERO ranges обрабатывается по трём уровням,
не созданием per-block массива. До публикации проверяется длина, tail,
версии, refs и отсутствие неавторизованного изменения shared children.

Один полный sequential block: не более1 DATA+3 новых nodes; append≤290816B
(284KiB), два прохода readback новых records и два head reads. Нет полного
flat index, per-block HANDLE или N-sized bitmap. Dirty группа≤4blocks/1MiB;
одна операция commit может обработать её ограниченное объединение paths.
Read после proof establishment:≤3 nodes+1 DATA,≤284KiB envelope input.
Worker-only `setSize(length)` принимает0…64GiB и только текущий selected
proof. Тот же размер — committed no-op того же proof/generation, но лишь
после проверки write capability/identity/actual paired heads; stale proof
даёт conflict без append/head writes. Прочие изменения увеличивают generation
ровно на1, включая shrink→0; extent никогда не уменьшается и orphan tail
не переиспользуется. При shrink→0 root EMPTY, extent равен прежнему committed
extent; отсутствие новых records не отменяет обе проверки heads/guard.
Операция меняет только bytes после меньшей из двух длин: сохранённый prefix
точно прежний, grow suffix ZERO. DATA на частичной границе переписывается
с exact новым payload; ZERO не превращается в DATA. Удалённые DATA не читаются
для разрешения truncate, но все использованные base nodes/граничный DATA
сверяются с диска; наблюдаемый fault остаётся sticky. Все новые NODE refs
сверяются через structural diff с аутентифицированными base refs в двух
readback проходах, до HEAD и до ACK, по разрешённому диапазону SetSize.
Полная ZERO subtree не разворачивается в per-block массив: не более7 новых
NODE+1 DATA и327680B append с padding на один resize; owned/dirty/pin/native
лимиты не увеличиваются. Старый pinned proof/Reader/Clone видит прежнюю длину
и прежние bytes после shrink/grow, пока тот же owner не получил sticky fault.
Invalid size/generation exhaustion/stale/admission refusal до native append
не публикуют snapshot; physical/crypto/readback failure блокируют owner,
после первой HEAD попытки результат ambiguous с retained base lease.
Цена flush/DPAPI/OS scheduling не имеет обещанного wall-time предела.
Validated cache keyed exact owner/root/ref может обслужить read без повторного
disk I/O: проверена выдаваемая память, а не свежесть носителя. На ownership gap
такой cache/proof недействителен. Cache никогда не скрывает наблюдаемый fault.

## 5. Birth, commit и recovery

Новый CREATE_NEW контейнер: prefix и две independently protected empty g1
heads с length0/root EMPTY/extent32896. Полный write/flush/readback обоих
heads до proof establishment. Неполный birth не достраивается автоматически
при restart. Empty media object не является пустой queue или sealed package.

Commit под одним writer:

1. Выбрать highest доказанный base из корректной paired authority; у empty
   equal-g1 birth selected slot0. Зафиксировать operation/context и budgets.
   Candidate generation **ровно checked base.generation+1**; u64 exhaustion,
   stale/non-selected base и неверный target отказывают до append/head I/O.
2. Encrypt и append новые DATA/children/parents после actual EOF; aligned
   offsets не пересекают heads/старые records. Не truncate/reuse orphan tail.
3. Полный records write и первый FlushFileBuffers. Independent readback новых
   records, всех проверок и structural diff. До head I/O отказ not_committed.
4. Target slot=(generation−1)%2. Перед первой попыткой head write outcome
   становится ambiguous; выполнить полный cell write и второй flush.
5. Positioned readback обеих cells. Новый descriptor равен exact candidate;
   другая cell равна **selected base descriptor**, не его прежнему lower peer.
   Перед ACK проверить соседство candidate/base и правильные slots. Повторно проверить
   новые records/identity/path/ACL, не writer copies. Лишь затем committed
   ACK и новый proof. Actual публикация не исчезает при stale UI/cancel.

Fixed cell overwrite **не atomic**. Partial write/flush/readback failure после
начала head I/O — sticky ambiguous: нет нового commit/GC/normal effects,
owner/artifacts удерживаются до full reconciliation. Generation не wrap/reset.
Actual extent включает до candidate EOF, но orphan bytes не authority;
каждый ref ограничен descriptor extent и фактическим размером файла.

После last guard close/crash/new acquisition/ambiguous outcome proof утрачен.
Fresh guarded open, decode обеих cells, streaming DFS достижимых nodes/DATA
обоих snapshots с полной integrity/structure/tail проверкой до normal admission.
Нужен bounded stack depth3+DATA buffer; разрешено повторно читать общие refs,
не требуется unlimited dedup bitmap. Полная проверка O(reachable bytes),
не мгновенная. Выбор highest validated generation только при корректной паре:
equal generations разрешены лишь identical empty g1 birth; последующие
generations в двух slots соседние и соответствуют slot formula.
Один missing/invalid head не разрешает normal result. Media-only degraded
trusted prefix допускается исключительно по базовым recovery/package-state
правилам, никогда вместо metadata authority или normal upload.

## 6. Жизненный цикл, квоты и интеграция

Owned64MiB/process до allocation, pins≤32/process, общий decoded cache≤2MiB
(DATA+nodes вместе), dirty≤4blocks, ≤4 одновременно admitted native I/O jobs.
Writer/root stamp≤4KiB каждый, без flat index copies и app key cache.
Сохраняются исходные dispatcher254DATA+2EOS/5s drain, cadence256KiB,
audio tolerances, product disk quotas/reserve/80%/95% и logical v5 bytes.
Physical append/orphan/pinned/legacy/temp peaks учитываются до admission;
представление64GiB не отменяет меньший продуктовый или свободный disk budget.

Никакого per-record GC/compaction/hole-punch при живых roots. Весь container
сохраняет records/extents обоих heads, protected retained roots и active pins,
**пока объект жив**. Whole-object удаление имеет отдельное разрешение после
durable intent и снятия внешних live retainers по current authority. Собственные
heads и receipts, описывающие уже удаляемый object, не вечные keep-edges.
Это не отменяет проверки historical migration/delete barriers; неизвестные
или ambiguous external references по-прежнему блокируют purge. Удаление только после
durable delete intent → close admission/cancel/quiesce actual native owners →
actual absence proof → durable removed ACK. Сборщик не получает authority
из имени файла/mtime; unknown/ambiguous references блокируют unsafe GC.

Protected package ref должен явно задавать representation v2, store/object/
container IDs, role, generation, logical length, committed extent, exact root
ref и logical SHA finalized artifact. Проверить semantic authority и stamp
до открытия; это отдельная versioned strict schema, не угадывание по extension.
Дополнить базовый metadata codec явно; v1 payload не разрешает v2 сам собой.

### 6.0. Существующий seekable writer, packed v2

Следующий шаг T116 переиспользует `ProtectedCustodyWriter` и его единственный
State/dirty buffer/API `writeAt/readAt/setSize/checkpoint`. Отдельного writer,
backend interface, фабрики или нового dispatcher нет. Worker-only packed open
принимает уже доказанный selected Tree и общий cancellation token, проверяет
актуальность paired heads и write capability до admission. Role следует из
проверенного Tree context, а не из произвольного caller enum. Это media-object
API, не принятие package authority и не внедрение в приложение.

Write принимает байты, не обещает атомарность всего большого вызова или
долговечность его последнего неполного блока. Крупный вызов проходит частями
до262144B; один dirty block резервируется до plaintext. Canonical сохраняет
прежнюю automatic checkpoint cadence при полном блоке. Media/playback также
могут опубликовать предыдущий dirty block при переходе к другому; checkpoint
проверяет оставшиеся изменения. Не обещать единственный generation increment
на весь Write/checkpoint: каждый фактический Tree transition увеличивает
generation ровно на1; result показывает фактический base/target. Пустой Write
при valid offset не расширяет EOF. Invalid pointer/offset/overflow или отмена
делают writer sticky failed, без частичного byte ACK.

Pending logical length/dirty bytes принадлежат writer; Reader/Clone остаются
на прежнем immutable committed Tree. Нет flat entries, bitmap или массива
размером с запись в packed State. Частичная перезапись использует проверенный
старый блок плюс dirty merge, затем существующий replaceBlock; append —
существующий appendBlock. При sparse Write ZERO разрешён только для явно
заданного промежутка до записываемых bytes. Нельзя сначала публиковать ZERO
вместо ещё не сохранённого входного аудио. SetSize может задавать ZERO suffix;
shrink→grow не восстанавливает отрезанные bytes, включая ещё dirty suffix.
Writer Read выдаёт его pending view, EOF короткий; любая ошибка стирает уже
скопированный prefix и не выдаёт partial byte ACK. Cold reopen видит только
фактически committed Tree, не pending length и не RAM dirty buffer.

Checkpoint flush/append/replace/resize используют единственного прежнего
owner и publisher, два independent readback и unchanged physical budgets.
Fail до HEAD — notCommitted; после попытки HEAD — ambiguous; после actual
ACK сохраняется новый Tree даже при поздней отмене. Более ранние ACK большого
вызова не откатываются и не объявляются отсутствующими. Первый fault/native
error и actual base lease удерживаются до worker release/reconciliation;
повторный вызов не делает новые native writes. Destruction только очищает RAM,
отзывает writer capability и освобождает refs; не делает flush/checkpoint/I/O.
Reader/Clone может сохранить тот же owner после healthy writer release.

Приёмка: generated bytes, header rewrite, crossing blocks, EOF, sparse gap,
SetSize shrink/regrow, pinned Reader/Clone, cold reopen, cancellation и
invalid input, общие dirty/pin/owned limits, actual native failure cuts и
plaintext wipe. Реальные V5/MF consumers, schema gate §6.1, cadence/Stop,
migration, T120, установленный пакет и hardware остаются отдельными gates.

### 6.1. Точные versioned metadata payloads

Физическая защита служебных payloads остаётся v1. Старые schema strings/field
sets не расширяются молча. Все bounds/unknown/duplicate/null/depth≤4 и16keys
правила базового §8.1 сохраняются. ID/sha string encoding остаётся базовым;
`root_ref` — ровно128 lowercase hex chars кодировки Ref64B из §3, не path
или JSON subtree. Он декодируется строго с root NODE_L2/base0 правилами.

`graf.custody.package.v2` имеет ровно те же top-level поля, что package.v1,
то есть девять полей §8.1 с единственным ключом версии `schema` (не
`schema_version`); значение `schema` здесь строго `graf.custody.package.v2`,
но каждый `refs` item содержит ровно10 fields: role, object_id, binding,
generation, length, sha256, representation, container_id, committed_extent,
root_ref. Representation — `flat_v1|packed_v2`. `flat_v1` сохраняет все прежние
binding/triple semantics, последние три fields=null. `packed_v2` разрешён лишь
canonical/media/playback; container_id=id non-null уже для live. Store ID
берётся из own package context, object/role — из ref. При live последние
extent/root и generation/length/sha=null, только capturing/finalizing; при
sealed все non-null, exact root stamp/extent/generation/length и logical SHA
проверены. Empty sealed root может быть EMPTY только при length0; sealed normal
не обходится этим исключением. Phase/reason/short marker правила package.v1
не меняются. В capture recovery выбирается live paired root по §5, не null
length как разрешение пустой записи. Старый schema1 остаётся v1-only.

`graf.custody.migration.v2` имеет ровно те же top-level fields, enums,
ledger_anchor/barrier/cleanup_authorization и stages, что migration.v1.
Отличие: каждый sources item — прежние7 fields плюс ровно4 fields:
destination_representation (`flat_v1|packed_v2`), destination_container_id,
destination_committed_extent, destination_root_ref. `packed_v2` разрешён
только для source canonical/media/playback subject=package; container ID
non-null заранее reserved. Prepared destination triple и extent/root=null.
Copied_verified и далее — exact verified sealed triple/stamp, logical length/
SHA равны original source. `flat_v1` требует три новых stamp fields=null
и исходную проверку обоих v1 indices. Subject queue/ledger всегда flat_v1.
Package manifest/recovery также flat_v1. Barrier всё ещё direct immutable
v1 migration-intent birth block, unprotect schema2/transaction/context exact;
historical validator сравнивает также representation/reserved container ID.
Смена schema/version не разрешена внутри уже начатого transaction.

Все v2 persistent root stamps обоих metadata slots/barriers, даже уже не
находящиеся в двух текущих media heads, восстанавливаются как retained roots
до GC. После ownership gap каждый такой root проходит full closure под тем
же guard и strict protected stamp; RAM proof не выводится из ref string.
Обновление current heads не стирает retained root. Unknown representation/
schema у старого reader даёт blocked/recovery-required, не empty/default.
Новая migration сохраняет исходный intent→old-reader fence→verified copy→
authority switch→authorized cleanup порядок базового §8 без in-place erase.

Reuse существующих ProtectedCustodyFiles/Codec/Reader/Writer, memory budget,
AppMain worker/leases, MF adapters и v5 finalizer. Не создавать параллельный
lifecycle/dispatcher/upload queue/сервер. Интеграция/миграция остаётся T116→
T117→T118; реальный inventory и установленное приложение не затрагиваются
до собственных проверок. Физический x64/audio/install/release — отдельные gates.

## 7. Обязательные проверки

Exact wire/context/overflow/DPAPI FALSE и TRUE+corrupt/oversized output;
DATA/NODE/HEAD tamper/substitution/type/ID/position/version/tail;
constant record count at64GiB edge без giant fixture/allocation;
full→inherited-live transition с changed-path и unchanged-child forgery;
сначала родитель/child corruption, потом normal read/commit/cold reopen;
writer release при active Clone и loss/reacquire той же file identity;
cuts до/после каждой записи/flush/head readback и torn birth/heads;
stale/cancel при реально выполняемом native operation; ZERO/shrink/grow;
pins/cache/budget/32/4 exhaustion до acceptance, no per-block HANDLE growth;
оба v1 metadata deletion rollback tests без ослабления;
package/migration schema1-vs-schema2 strict fields/null/stamps и восстановление
retained root не в current heads; source equality/barrier/old-reader cuts;
generated v5→finalize→restart→hash/playback/upload/delete и100cycles;
повторяемые last-checkpoint/Stop/memory/IO measurements, cold cost отдельно.
Ни unit tests, ни постоянное число records не принимают sustained capture.

Первичные native API ограничения повторно сверены2026-10-03:
[CryptUnprotectData](https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptunprotectdata)
прямо предупреждает о возможном success с corrupted output и рекомендует
дополнительные integrity checks; поэтому FALSE-only validation недостаточна.
[CreateFileW](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew)
определяет sharing на lifetime HANDLE и исключение metadata access; один
pathname не доказывает identity/ACL/непрерывный owner. Эти документы не
доказывают корректность нашего wire/commit протокола или hardware latency.
