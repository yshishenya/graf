# Защищённое локальное хранение Windows — протокол T115

Дата: 2026-10-02. Область: FR-012/013/014/022, SC-003/005/006/008.
**Статус: проектирование T115 принято, продуктовая реализация T116–T118 не принята.**
Уточнение 2026-10-03: это принятие относится к исходному формату v1.
Поправка больших media objects определена в
`windows-protected-packed-custody.md`; её принятие проверяется отдельно.
v1 metadata, semantic authority, migration/deletion и logical v5 не заменяются.
Приведённые ниже flat-index/validated-reopen правила описывают именно v1,
не разрешают переносить live proof на другой file owner и не применяются
как альтернативный decoder при отказе явно выбранного packed формата.
Независимый обзор `checklists/review-2026-10-02-storage-independent.md`:112/112,
storage analyze CRITICAL=0/HIGH=0, issue-sync #7443–#7446 и canon PASS.
T114 завершён по aggregate review round141. Нормативные требования ниже
не менялись при принятии. Аудиочасы T094–T096
этим срезом не меняются. Измерения стенда не доказательство продуктовых квот.

## 1. Границы и повторное использование

Выбраны user-scope DPAPI, CNG SHA-256, immutable версии блоков по256KiB и два
защищённых индекса. Нет отдельного пароля, собственного AES/key/nonce lifecycle,
EFS, службы, драйвера, новой базы данных или сетевого сервиса ключей.
DPAPI вызывается с `CRYPTPROTECT_UI_FORBIDDEN`, без `LOCAL_MACHINE`, prompt,
описания с приватными данными или ключей в файлах приложения. Optional entropy
связывает контекст, но не является секретом/заменой авторизации аккаунта.
Это защита файлов профиля, не защита от самого вошедшего пользователя,
администратора, чтения памяти, отката всего диска или удаления master keys.
Не обещать per-recording cryptographic erasure, восстановление потерянных
ключей, отсутствие pagefile/crash dump/старых резервных копий Windows.

Логические bytes существующего v5 и схемы ledger v3/read v2 сохраняются.
`meeting-transcription.wav`, `meeting-review.m4a`, `manifest.json`,
`.canonical-mix.f32.tmp`, `capture-recovery.json` — **логические роли**, не
разрешение создать открытые физические файлы. UUID/session/revision, время,
byte ranges, SHA-256 и delete/purge receipts не заменяются при защите.

Переиспользовать `AtomicFileStore` confinement/ACL правила, но не его открытый
ofstream для content. `V5LocalRecordingWriter`, `LocalRecordingPackage`,
`Sha256`, `DesktopUploadQueueService`, `DesktopHttpTransport` и существующие
AppMain background open/scan/finalizer/recovery leases — точки внедрения T116.
Не создавать второй scanner/lifecycle. Whole-file sha256File, URL AAC writer,
SourceReaderFromURL и ShellExecute(mediaPath) выводятся из content пути.

## 2. Физические объекты и однозначная идентичность

Все файлы под проверенным user-scoped custodyRoot; запрет symlink/reparse,
alternate data stream, UNC/внешнего root и произвольного имени из JSON.
Проверяются открытые handles и их фактический confined путь; одной проверки
weakly_canonical до открытия недостаточно. User-only ACL устанавливается при
создании, **до** первого content write. Нельзя менять ACL всего профиля/VM.

В `.custody-v1/store.id` — ровно16 случайных opaque bytes, не account ID/ключ.
Создание exclusive только при новом пустом inventory либо проверенном legacy
inventory без единого protected object/sentinel, перед первым migration fence.
Отсутствующий/неверный ID при существующих protected объектах — blocked, не
генерация нового ID. Object ID
также16 opaque bytes, отдельный `id.bin` в confined object directory; известная
роль задаётся вызывающим custody record, а не угадывается по media extension.
Имена блоков — только внутренние block-position/version, индексы `index.0`
и `index.1`, ciphertext-only временные файлы с opaque suffix. Вне шифрования
допустимы лишь эти технические ID/номера/размеры, не user/workspace/name/URL,
recording timestamps, manifest JSON, hashes содержимого или private paths.

Фиксированные служебные роли: bootstrap, queue, migration-intent; пакет имеет
package-state и canonical/media/playback/manifest/recovery объекты в своём
`.custody-v1`. Его прежний directory_id остаётся неизменным. Неизвестные
папки/имена сохраняются, не принимаются автоматически за пустой пакет.
Bootstrap определяет единственный reader mode и protected queue object;
пакетный state содержит phase и ссылки на его объекты. Эти records защищены
тем же logical storage, без второй открытой базы указателей.

Начальные locations не берутся из неподтверждённого JSON: bootstrap и queue
открываются только в `custodyRoot/.custody-v1/bootstrap` и `/queue`, intent
ledger — `/migration-intent`. Пакетный state/intent/role objects только в
`custodyRoot/<directory_id>/.custody-v1/<role>`; directory_id проверяется
existing identity validator, role — enum фиксированных имён. Каждая directory
содержит свой exact16B id.bin, block envelopes и два index slots. Bootstrap
проверяет совпадение object ID queue, не перенаправляет чтение внешним path.
Inventory scan исключает служебный root `.custody-v1` из списка пакетов.

## 3. Кодирование v1 и проверка до выделения памяти

Wire codec явный little-endian; не memcpy C++ struct/padding/size_t/GUID ABI.
ID —16 bytes, не платформенное представление GUID. Числа unsigned, overflow
отвергается до сложения/умножения/кастов DWORD, size_t, streamoff и allocation.
Все reserved нули, неизвестные schema/role/flags и лишние/truncated bytes — отказ.

Outer envelope16B: magic8=`GRAFDP01`, schema u16=1, kind u16 (1 block/2 index),
cipher bytes u32; затем ровно указанное число DPAPI bytes, никакого plaintext
payload. Outer поля недоверенные; file size/kind bound проверяются **до** чтения.
После unprotect повторно проверяются decoded length, internal magic/schema,
identity и тип. Ни broken envelope, ни native FALSE не открываются как legacy.

Plain block header104B, порядок полей:
magic8=`GRAFBL01`, schema u16=1, role u16, header_bytes u32=104;
store_id16, object_id16, block_position u64, block_version u64;
payload_bytes u32, reserved u32=0, SHA256(payload)32; затем payload.
Position/version/role/IDs/exact payload length должны совпасть с pinned index.
Payload SHA проверяется после native integrity check; ошибка sticky, нет zero-fill.

Plain index header112B, порядок:
magic8=`GRAFIX01`, schema u16=1, role u16, header_bytes u32=112;
store_id16, object_id16, generation u64, logical_length u64;
block_size u32=262144, entry_count u32, reserved u64=0, checksum32;
затем ровно entry_count×16B. Checksum=CNG SHA-256 всего plain index с нулевым
checksum field. Entry: block_version u64, physical_envelope_bytes u32, flags u32.
Позиция implicit. flags=0 — DATA, version>0 и точный bounded cipher size;
flags=1 — ZERO, version=0/size=0. Иные сочетания запрещены.

Role enum v1: 1 canonical,2 media,3 playback,4 manifest,5 recovery,
6 queue,7 package-state,8 bootstrap,9 migration-intent. Role не authorizes
upload/deletion. Entropy bytes: ASCII `graf.custody.v1` без NUL, store_id16,
object_id16, role u16, kind u16, selector u64, version u64. Для block selector
равен position, version — entry version. Для index selector —slot0/1,
version=0 (generation неизвестна до unprotect); generation проверяется внутри.

Logical length≤64GiB, count=length/262144+(length%262144!=0), max262144;
length0 имеет count0, не является пустым восстановленным ledger. DATA length
равен full block либо точному tail. При расширении прежнего tail его версия
переписывается; старый short block не используется как full. ZERO только для
явного SetSize/seek extension, никогда вместо отсутствующих/битых DATA.
Plain index≤4096+count×16, max4198400B; physical index≤это+65536.
Physical block≤payload+4096; native выход сверх bound — отказ без публикации.
Метаданные: manifest≤64KiB, queue≤4MiB (существующий writer cap), служебные
bootstrap/package-state/intent/recovery≤64KiB каждый. Это пределы нового
кодека; oversized legacy сохраняется blocked, не обрезается/не «исправляется».

Поправка 2026-10-04 для T120: прежний manifest≤4096B не вмещал повторные
privacySegments Mac. Меняется только logical limit роли manifest; один
64KiB payload остаётся в существующем256KiB block, physical envelope/index
bounds, owned64MiB, job2MiB, cache/pins и аудиодопуски не увеличиваются.
Проверяется весь сериализованный manifest до OPEN, не приблизительный размер
или число сегментов. Decoder/reader/writer/legacy validator согласуют один
предел, exact/limit+1 и allocation/failure проверки обязательны. Новая форма
не принимается прежней exact regex через ослабление substring checks.
Эта проектная поправка требует свежего независимого gate перед изменением
кодека/потребителей; исторические приёмки4096B остаются историческими.

## 4. Commit, неопределённый результат и восстановление

Один writer на object под существующей process/lease защитой. Новая версия
блока создаётся CREATE_NEW; существующий orphan никогда не перезаписывается.
Version/generation не wrap/reset; inventory обходится порциями без накопления
списка. Достигнут предел — blocked. Незатронутые block versions переиспользуются.

Порядок: encrypt в памяти → create/полный write/FlushFileBuffers blocks →
encrypted temporary index → flush → atomic publish в alternating slot →
flush опубликованного handle и validated reopen → commit acknowledgment.
До последнего acknowledgment новые bytes accepted, но не durable. Инициировать
next generation/GC после ошибки post-publish запрещено: результат ambiguous,
writer sticky failed, retained artifacts, существующий last checkpoint не
удаляется. Reopen в фоне решает фактическую authority, а не возвращает bool
«не сохранилось» и тут же повторяет изменение. Rename/flush сами по себе не
доказательство любых power-loss свойств носителя; T118 проверяет границы.

Для canonical/media reader допустим validated прежний snapshot, но только
degraded/trusted prefix, не normal upload. Для queue/bootstrap/package-state/
migration/delete metadata **любая существующая unreadable/invalid index slot
или referenced block блокирует authority всего соответствующего контекста**.
Запрещён rollback к старому ledger, который мог не содержать delete intent.
Metadata birth публикует generation1 сначала в slot0, затем независимо
защищённую копию того же decoded index в slot1. Первый acknowledgment только
после flush/reopen/проверки **обоих** slots и равенства decoded bytes. Одинаковая
generation допустима только для этой пары g1; другие равные поколения либо
разные decoded bytes — конфликт. Последующие generations публикуются в slot
`(generation-1)%2`; выбирается наибольшая validated generation.
После restart **любой singleton metadata**, включая surviving g1/slot0,
блокирует authority: по одному файлу нельзя доказать, что g2 не потерян.
Interrupted birth сохраняется recovery-required без автодостройки/пустой
очереди. Для live birth до первого ACK также нет authority/effects.
Оба missing при известном inventory — не новая пустая очередь. Temporary/orphan
не является authority и не выбирается по mtime/самому большому filename.

package-state: capturing → finalizing → sealed_normal | sealed_degraded |
discard_pending. Первый state durable до canonical write. При capturing
canonical checkpoint выбирается отдельно; recovery принимает лишь
floor(validated_length/1920)×1920 bytes полных480-sample cleaned frames.
WAV/AAC finalization читает этот exact prefix, без padding/повторной AEC.
Finalized artifacts immutable; hashes/lengths/manifest verified, manifest
публикуется последним, затем package-state с exact object ID/generation/length/
SHA и normal/degraded reason. Незавершённые live refs разрешены только для
capturing/finalizing recovery, не inspect/upload. Лишь sealed state разрешает inspect/upload;
само наличие WAV/AAC или успешный encoder — не normal package. Fallback artifact,
отказ canonical/finalizer/clock никогда не normalizes capture failure.

## 5. Память, IO, квоты и потоки

Предельные owned buffers64MiB на процесс с резервированием **до** allocation;
включают indices/candidate copies, cipher/plain buffers, metadata serialization,
hash/upload/CopyTo buffers и cache. Plain read cache2MiB суммарно, общий для
Clone, одна dirty seek/rewrite группа≤4blocks/1MiB, без накопления следующих.
Крупный Write/CopyTo/hash выполняется частями≤256KiB; число Clones/pins≤32
на процесс; нехватка бюджета — явный отказ до принятия изменения, не swap spill.
MF/DPAPI internal allocations дополнительно измеряются, не объявляются частью
доказанной owned quota. Finalization освобождает writer copies перед reopen.

Sequential canonical публикует каждый full256KiB block, Flush/Pause/Stop также
tail. Это cadence по bytes, не wall-time гарантия1.365s при зависшем IO.
Dispatcher256items/254data+2EOS/5s drain, SC-001/003 неизменны. WASAPI callbacks
не делают IO/crypto; dispatcher не ждёт UI; по ошибке sink/queue/drain normal
capture прекращается. EOS → close timeline → async finalizer; lease и object
ownership живут до реального завершения, не до возврата Stop/тайм-аута.

UI/readiness не делает block scans/decrypt/hash/encode/migration/GC. Используются
existing AppMain background scan/open и workers. Startup constructor не читает
queue: readiness pending до background validation. Ledger mutation готовится
на value copy без изменения опубликованной projection. Существующие bool
domain helpers допускаются только внутри этой copy и означают validation,
не durable успех. Persistence-facing bool/void callers заменяются typed ticket:
`pending | committed | not_committed | ambiguous`, ticket ID, store/object ID,
base/target generation, captured context epoch. Нельзя вернуть true «поставлено
в очередь», false «ещё pending» или ждать IO внутри bool на UI.

Один candidate исполняется на ledger; максимум32 bounded commands/results,
с учётом retained completions и памяти до allocation. Worker владеет candidate,
pins/lease/result до terminal completion и adoption либо повторной validation.
Full metadata value публикуется **одним** commit: flush dirty groups не
публикует промежуточный неполный JSON. Следующая mutation только от фактически
принятой generation; старый snapshot не overwrites более новый commit.
До publish cancellation = not_committed, old projection retained. После начала
publish отмена не откатывает bytes: worker доводит reopen до committed либо
ambiguous; последнее запрещает effects/следующую запись/GC до reconciliation.
Физический committed result принимается storage projection даже при stale
account/UI epoch; stale callback не показывает данные и не запускает network.
Потерянный UI callback не освобождает lease/result: существующий polling/
background recovery принимает generation прежде следующей mutation. Store
ownership переживает UI/controller, без raw pointers в job.

| Существующий caller | Продолжение после typed result |
| --- | --- |
| RecoveryScheduler prepare | Retry/exhausted/status changes одним candidate; flight selection и network только после committed и current epoch |
| Completed-flight drain/apply | Flight/result/busy/lease удерживаются при pending. Reconcile server truth + terminal status одним candidate, не два игнорируемых bool. handled/новый flight только после committed/adoption; stale row identity запрещает применение |
| AppMain finalizer enqueue/discard | Finalizer result и capture lease удерживаются. pollFinalization возвращает pending до ACK queue insertion/removal; normal/saved/новая запись только после committed. not_committed/ambiguous сохраняет trusted artifacts, показывает recovery-required |
| DeletionPlan / network dispatch | saved=true только после committed intent. До ACK нет HTTP. Ответ сервера + receipts/status/identity одним candidate; reply accepted и снятие in-flight guard только после committed/current context |
| Local purge / short discard | Intent ACK → close admission/cancel/quiesce → actual OS absence proof → removed ACK. Pending/timeout сохраняет lease/intent, не removed; marker последний |
| Account/logout/close/quit/update | Отмена UI/network не уничтожает pending persistence ownership. Новая запись/установка запрещена до terminal job/adoption; stale completion меняет storage truth, не account capability |

При not_committed effect/reply не разрешается; old projection помечается
recovery-required до безопасного retry. При ambiguous не выдаётся ни success,
ни доказанное отсутствие commit. Существующие success labels не используются
для pending; отдельная Windows UI не вводится.

64GiB — representational bound, не quota/серверная длительность. Унаследованные
PRD retention7days, device cap5GB, предупреждение80%, критическое95%/OS disk risk
сохраняются. Минимум свободного места — **10GB или10% disk capacity, меньшее
из двух** (PRD local buffer policy). Admission capture/mutation отказывает,
если предсказанный physical peak группы уменьшит free bytes ниже reserve;
reserve учитывает **physical** cipher+две index slots+candidate+
orphans+pinned+legacy/temp+metadata, а не только logical audio. До native calls
проверяется запас для целой группы/indices; ошибка OS write всё равно terminal.
Retention не снимает owner/delete/lease fences и не удаляет undecodable либо
неподтверждённый original. Старые oversized записи не обрезаются. Найденное
расхождение parser24h/server4h не разрешает новую24h загрузку; проверка общих
лимитов остаётся открытой, без изменения сервера этим contract.

GC≤64 объектов за проход, streamed enumeration без vector inventory; сохраняет
refs обоих indices, всех pinned snapshots, dirty candidate и package-state.
До первого GC после restart восстановить transitive keep-roots из **обоих**
valid bootstrap/package-state/intent slots: destination/source snapshots,
direct historical barrier refs и ciphertext tombstones (§8.1). In-memory pin
прошлого процесса не считается persistent root. Пока roots не validated,
GC соответствующего scope запрещён. Обход streamed/bounded, не full inventory
allocation; один небольшой historical block на intent, не все старые indices.
Invalid/unknown slot/intent или ambiguous writer блокирует GC соответствующего
object. Не стирать index slot, чтобы искусственно сделать GC безопасным.

## 6. Logical IO, Media Foundation, hash и upload

Read возвращает только verified logical bytes pinned snapshot, в том числе
exact tail; EOF короткий=S_FALSE, got exact. Native/semantic error sticky,
got0; caller не использует частичный buffer после ошибки. Seek проверяет signed
offset/overflow; Read за EOF не добавляет bytes. Writer SetSize extension
задаёт ZERO, shrink/rewrite сохраняет прежние committed versions. Read-only
snapshot SetSize/Write отвергает. Clone — independent cursor/same pinned
generation/shared cache; CopyTo bounded, ошибки не маскируются. Commit flags
поддерживаются явно, неизвестные flags/locking/revert — отказ, не ложный S_OK.

IStream → IMFByteStream для SinkWriter/SourceReader/MediaEngine audio-only;
container задаётся MF attributes/нейтральным label `.m4a`, не private path.
Никаких plaintext temp/URL codecs/ShellExecute/audio exports для playback.
MediaEngine callbacks содержат безопасный event/error, не content, и проходят
проверку owner/context epoch на UI. Pause/resume/seek/Stop используют один pin;
Shutdown и release engine/byte stream завершаются до release pin. Отказ codec
объясняется штатной readiness/repair, не открытым запасным файлом.

CNG incremental SHA256 по logical stream chunks, не ciphertext/file_size.
Manifest/media/playback exact hashes, existing RIFF u32 bound и codec параметры
сохраняются. HTTP requests читают exact [start,end) verified bytes, прежний
partSize clamp/part digest и server accepted offsets; no re-encode или новый
UUID/session из-за encryption. Server truth/reconcile остаётся авторитетом
accepted ranges. Decrypt success не даёт owner права и не означает upload PASS.

## 7. Account, delete, callback и shutdown fences

Каждая работа владеет value snapshot, cancellation, store/account epoch,
package ID/state generation и pin; не raw UI/controller/queue reference.
До IO и каждого network part проверяется cancellation; до UI/queue commit
сверяется current owner/session/epoch/status. Account change/logout закрывает
старую capability и отменяет flight; запоздалый callback не отображает данные
другого аккаунта и не записывает новый ledger/назначение владельца.

Delete: durable existing user/server intent → запрет новых reads/upload/playback
→ cancellation/MediaEngine Shutdown → дождаться реального выхода владельцев
pins/flight/finalizer → confined recycle/purge → проверить отсутствие → durable
ack. Timeout сохраняет pending/lease, не removed и не принудительное закрытие
handle. No terminal purge ack на одном сообщении web или decrypt success.
User local delete остаётся Recycle Bin-only существующим IFileOperation sink;
server purge и short-discard не получают новых полномочий. Cipher в Корзине
не объявляется уничтоженным; копирование/удаление ключей профиля запрещено.

Short recording: прежнее exact frame count/normal stop/no-fault решение,
protected positive discard marker переживает удаление всех media; durable
queue removal прежде cleanup, marker/state удаляются последними. Незавершённое
удаление при restart не возвращает пакет в upload. Shutdown закрывает admission,
отменяет jobs, ждёт/сохраняет их ownership как existing lifecycle требует;
не делает encoding/network в destructor и не выдаёт expired lease за completion.

## 8. Restart-safe migration и старый reader

Legacy reader доступен **только** worker миграции, никогда regular inspect/hash/
upload/playback. Owner: F200 native storage, task T117. Expiry: принятие T117
до первого внешнего выпуска; hard stop2026-11-01 UTC. После срока отсутствие
успешного перехода блокирует публикацию, но не разрешает удалить/обрезать
original или автоматически продолжать открытый reader. Удаление executable
legacy path/fixtures разрешено лишь по доказанному retirement T117; истории
spec/validation не удаляются. Это deadline исключения, не обещание даты выпуска.

Сначала exclusive AppInstance/recovery lease, остановка writer/flight/pins,
закрытие admission в памяти и bounded source/stamp validation. Затем durable
protected prepared intent, **после него** protected bootstrap migration fence
по codec §8.1. Во время prepared/copy/switch глобальный migration fence
запрещает новые capture/queue/network/purge mutations; один transaction, не
вторая параллельная очередь. Existing queue bytes/hash фиксируют все owner/
deletion/range значения. Перед switch повторная source/stamp validation;
изменение старым клиентом — blocked, не применение устаревшей destination.

Первый queue transition резервирует fixed queue id.bin/object ID и destination
IDs в intent, **не создаёт пустой logical ledger**. Prepared intent born g1 в
двух slots, затем g2 prepared с historical barrier ref. Closing bootstrap
ссылается на этот intent/reserved queue ID: при prepared разрешено отсутствие
queue indices. Это валидный **запрещающий** fence, не reader authority очереди.
Лишь после его ACK worker пишет destination из exact legacy bytes. Для package
transition queue уже protected; prepared intent в fixed package intent role
предшествует root bootstrap fence с subject/package directory (§8.1).

| Наблюдение после interruption | Migration-only recovery / обычные effects |
| --- | --- |
| Только reserved opaque IDs, без protected envelopes | Повтор verified legacy initialization под lease; никаких effects/empty queue |
| Bootstrap отсутствует полностью; exact pair prepared root queue intent и reserved IDs valid | Продолжить birth закрывающего bootstrap с тем же transaction/IDs; не новый UUID/legacy downgrade. Package pre-fence intent при existing protected bootstrap аналогично продолжает тот же fence под lease |
| Любой singleton/invalid intent либо bootstrap | Retained recovery-required, без автодостройки slots/GC/effects |
| Valid migrating bootstrap + matching prepared intent | Queue destination отсутствует либо provisional: только copy/validation. Partial destination metadata birth с одной slot = retained recovery-required, не empty/normal queue |
| Matching copied_verified intent | Все destination pairs/length/hash и свежий source stamp обязательны; продолжить old-reader barriers/switch, не effects |
| Actual queue bootstrap protected либо package-state sealed, intent ещё copied_verified | Это разрешённое cut между authority switch и его receipt. Проверить exact destination, source/original, old-reader barrier; записать switched ACK. До reconciliation никаких effects, не возврат к legacy |
| Switched intent + migrating fence | Revalidate destination/state/barriers, затем снять fence protected commit; никаких effects до этого ACK |
| Protected bootstrap + verified sealed authority; intent switched/cleanup_pending/complete | Regular protected flows допустимы; originals/authorization/cleanup отдельно, без нового legacy reader |

Недопустимое сочетание, missing required intent или чужой transaction — blocked,
не выбор mtime/первого файла. При provisional destination prepared worker может
использовать только validated checkpoints **своего** transaction; semantic queue
authority ещё нет. Повтор не перезаписывает orphan/version и не исправляет
partial metadata birth. Перед каждой copy/switch опять проверяются source/owner/
stamp и lease. Начальный закрывающий fence не требует готовую queue раньше copy.

Stages: prepared → copied_verified → switched → cleanup_pending → complete.
prepared читает confined original streaming≤256KiB, **только копирует**, не
re-encode; destination не authority. copied_verified требует whole logical
hash/length равенства и durable validated destination; source остаётся.
Одно authoritative переключение — protected bootstrap для ledger и protected
package-state для пакета: readers выбирают только это значение, не первый
существующий файл. После ambiguous switch дальнейшая работа останавливается;
restart проверяет оба records и intent, не начинает новую copy/UUID.

Для ledger **до любого rename старого имени** создать CREATE_NEW и flush
`<old-ledger>.quarantine`: ciphertext envelope первого committed блока intent
сохраняется как opaque barrier. Existing old queue load при отсутствии ledger
и наличии этого имени отказывает вместо создания пустой очереди. Затем rename
original в fixed `legacy.originals`, flush/verify exact bytes; только после
этого ciphertext sentinel по old name, flush/verify, затем authority switch.
Между rename и sentinel old name отсутствует, но durable old-reader quarantine
gate уже существует. До rename original остаётся authority; если старый клиент
изменил его после copy, новый recovery это обнаруживает по stamp и отказывает.
Любой существующий .quarantine не перезаписывается: неизвестный либо legacy
барьер сохраняется blocked. Новый recovery сверяет barrier с pinned committed
intent block/context/transaction, не читает как v3. Pins intent/barrier держат
точную версию блока до terminal migration. Не удалять одновременно gate и
sentinel; после transition оба остаются fail-closed tombstones для old reader.

Manifest original также переносится в fixed legacy.originals, затем ciphertext
sentinel по прежнему имени до package switch. Его отсутствие/invalid JSON не
разрешает old inspector upload. Все old-name cuts отдельно проверяются T117.
Сам protected bootstrap неизвестен старому reader и **не считается** его
барьером. Если rename/sentinel/switch прерван, новый bootstrap migration fence
запрещает обычные effects до reconciliation; original не теряется и не удаляется.
No-intent legacy допустим лишь до первого protected fence и после строгой
проверки отсутствия всех protected/sentinel/quarantine следов; corruption
никогда не downgrades mode. Новая пустая очередь только в доказанном virgin root.

cleanup_pending удаляет original только по отдельному явному подтверждению
владельца на очистку прежней копии либо уже действующему подтверждённому
delete/purge intent; сама миграция не даёт права автоматического удаления
(FR-012). До этого original сохраняется, переход не называется полной защитой.
Нужны проверенный switch и повторная identity/hash/length/path проверка,
без active pins/delete conflict. Interrupted
cleanup повторяется по тому же intent, не отменяет accepted ranges/deletion
operations/purge acknowledgements. complete durable лишь после отсутствия
original/temp и совпадения projected ledger. Malformed/oversized/key-loss/
unknown-schema original сохраняется blocked; inventory не называется полностью
зашифрованным, пока plaintext originals/backup/quarantine остаются.

Rollback старого приложения: только сохранность/явный unsupported-format отказ,
не возвращение к открытому storage. Sentinel/quarantine вариант обязан быть
понятен новому recovery; updater не разрешает старому writer downgrade v3.
Серверную схему/историю записей rollback не меняет.

### 8.1. Строгий codec трёх новых authority records

Logical payload — UTF-8 JSON object, не LE storage header и не C++ ABI.
Без BOM, invalid UTF-8, duplicate decoded keys, unknown/missing fields, comments,
trailing bytes. Все поля таблиц обязательны; null допустим только явно ниже.
Object key order/JSON whitespace не значимы; writer пишет deterministic order.
Числа — decimal unsigned integer literal, без minus/fraction/exponent/overflow,
exact u64 через from_chars, не floating point. `bool` только true/false.
`id` —32 lowercase hex chars (16B), `sha` —64 lowercase hex chars (32B);
`identity` —1–300 ASCII `[A-Za-z0-9_-]`, без locale-dependent расширений.
`reason` —0–64 ASCII `[a-z0-9_-]`, только известный safe ReasonCode, пустой = none.
Все payloads≤64KiB; parser depth≤4, refs/sources≤6, object keys≤16. Unknown
enum/schema/bound или identity mismatch = recovery-required, не default/null.
`store_id/object_id/generation` mutable authority record совпадают с pinned own
index; direct historical barrier имеет отдельный validator ниже, не открывается
как current mutable record. Generation≥1, роль задаётся fixed location.
Запись payload для target generation готовится
до публикации. Это не изменение существующих logical v5 manifest/v3/v2 codecs.

Уточнение владельца 2026-10-04: package-state имеет **ровно девять** top-level
полей `schema`, `store_id`, `object_id`, `generation`, `directory_id`, `phase`,
`reason`, `short_recording_discarded`, `refs`. Единственный ключ версии —
`schema`, строка с точным schema string из таблицы. `schema_version`, aliases,
unknown/missing/duplicate decoded keys отвергаются; правила других records
и существующего logical v5 manifest этим уточнением не меняются.

| Record / точный schema string | Остальные точные поля и типы |
| --- | --- |
| bootstrap / `graf.custody.bootstrap.v1` | store_id:id, object_id:id, generation:u64, mode:`migrating\|protected`, queue_object_id:id, transaction_id:id/null, subject:`queue\|package`/null, directory_id:identity/null |
| package-state / `graf.custody.package.v1` | store_id:id, object_id:id, generation:u64, directory_id:identity, phase:`capturing\|finalizing\|sealed_normal\|sealed_degraded\|discard_pending`, reason:reason, short_recording_discarded:bool, refs:array |
| migration-intent / `graf.custody.migration.v1` | store_id:id, object_id:id, generation:u64, transaction_id:id, subject:`queue\|package`, directory_id:identity/null, stage:`prepared\|copied_verified\|switched\|cleanup_pending\|complete`, ledger_anchor:object, sources:array, barrier:object/null, cleanup_authorization:object/null |

Bootstrap migrating требует transaction_id/subject и matching durable intent;
queue subject имеет directory_id=null и fixed root intent, package — directory_id
и fixed package intent. Protected требует все три null. ID не задаёт path:
subject enum/directory validator выбирают только confined locations §2.
В migrating обычные эффекты запрещены. При switched reconciliation
публикует protected bootstrap и matching package-state прежде открытия admission.
cleanup_pending не держит глобальный fence: protected reader работает, original
сохраняется с явным unprotected-leftover status. Unmigrated/unknown пакеты не
допускаются в regular upload/playback; их наличие не превращается в empty state.
Queue reference всегда сверяется с fixed queue id.bin. Для initial migrating/
queue/prepared это reserved ID, indices отсутствуют либо provisional без reader
authority. При copied_verified обязательны два valid queue slots и exact copy
destination identity/length/hash. При protected обязательна current queue pair,
но её generation/hash не обязаны навсегда равняться migration copy: новые
owner/range/delete mutations легитимно меняют queue после switch. Для package migration protected queue
pair обязательна уже до prepared intent. JSON не определяет filesystem path
и не фиксирует вечную queue generation. Closing fence structural validation
не выдаёт regular admission; cross-record этапные правила заданы таблицей §8.

Package refs: массив0–5 уникальных ролей `canonical|media|playback|manifest|recovery`.
Каждый ref имеет **ровно** role:enum, object_id:id, binding:`live|sealed`,
generation:u64/null, length:u64/null, sha256:sha/null. live требует три null,
разрешён лишь в capturing/finalizing, не normal/inspect/upload; sealed требует
generation≥1, length≤role bound, SHA exact logical bytes и matching role/object
identity. directory_id соответствует реальной package directory. capturing/
finalizing требует canonical live ref; sealed_normal требует sealed media,
playback, manifest, reason empty и short_recording_discarded=false. degraded
имеет непустой reason и validated trusted prefix, upload запрещён. discard_pending
имеет positive short predicate, short_recording_discarded=true и protected
manifest marker; иных сочетаний нет. Каждый referenced sealed index/block
валидируется до authority. GC canonical/recovery только когда ни один из
двух state slots/pins больше не ссылается на них; при необходимости следующий
state commit с теми же sealed semantics снимает старую live ссылку, не стирает slot.

Intent queue требует directory_id=null, package — identity. `ledger_anchor`
имеет ровно object_id:id/null, generation:u64/null, length:u64, sha256:sha.
Legacy ledger = первые два null; protected = оба non-null. Hash/length entire
validated logical v3/read-v2 snapshot — stamp всех owner/range/deletion/purge
полей, не их выборочный пересказ. При virgin empty queue length0/hash empty
bytes допустимы только по доказанному virgin root. Снимок и matching pin
удерживаются до switch; changed stamp запрещает switch. После switch anchor
остаётся историческим доказательством copy, не полномочием удалить original.

`sources` —1–6 объектов, уникальный source enum
`ledger|manifest|canonical|media|playback|recovery`. Каждый содержит ровно
source:enum, source_length:u64, source_sha256:sha, destination_object_id:id,
destination_generation:u64/null, destination_length:u64/null,
destination_sha256:sha/null. queue только ledger; package не ledger.
Source enum задаёт fixed old filename из §1, original только
`<scope>/.custody-v1/legacy.originals/<source>`, никогда path из JSON.
Prepared destination triple весь null; copied_verified и далее весь non-null,
generation≥1, source/destination exact length/hash равны. При copied_verified/
switch обе index refs validated. После switch mutable queue destination triple
является authenticated историческим copy receipt, **не** reader snapshot:
regular reads берут current validated queue pair; старый g1 index не требуется
сохранять для каждой последующей mutation. Package sealed artifacts immutable,
их refs продолжают проверяться до authority; legacy source absence допустимо
только по complete/actual cleanup proof. Historical receipt не даёт права
rollback, upload старого ledger либо cleanup без fresh authorization.
Sources/role caps и package phase должны быть согласованы; неизвестный orphan
temp/quarantine не включается по произвольному имени и остаётся blocked legacy.

`barrier` — ровно object_id:id, generation:u64, block_version:u64, envelope_bytes:u64,
sha256:sha либо null. Для queue barrier non-null прежде rename: это pinned
block position0/role migration-intent/prepared snapshot текущего transaction,
не plaintext content hash; sha256 здесь **cipher envelope** hash. Версия>0,
размер в block bound, native context/header/payload schema/transaction проверены.
В prepared intent первый snapshot содержит null; затем отдельный committed
prepared snapshot записывает ref на первый immutable block, после чего создаётся
old .quarantine. Для package такой же direct ref задаёт old manifest sentinel;
switched intent любого subject без barrier invalid. Первый prepared snapshot
g1 имеет barrier=null, cleanup_authorization=null, destination triple null.

**Standalone historical validator**, до восстановления roots/разрешения GC:
current validated intent ref требует того же object ID, generation=1 и version>0
для immutable birth block position0/role migration-intent; envelope size/hash
exact, native entropy/context и block header проверяются как в §3. Payload
раскодируется строго по migration schema, но его own generation сверяется с
authenticated direct ref=1, **не** current g3/g4 index. Требуются prepared,
barrier=null, cleanup_authorization=null, destination triple null, совпадение
transaction/subject/directory/ledger anchor и всех source kind/size/hash/
destination IDs с current intent. Current mutable metadata по-прежнему требует
оба valid indices; этот historical путь не даёт queue/package authority.
Version сверяется exact с authenticated ref, не приравнивается к generation:
orphan collision не разрешает overwrite или выбор по большему имени.
First-block payload≤64KiB, поэтому birth record целиком в одном block.

Retained bytes берутся из exact immutable block либо из уже созданного
verified .quarantine/manifest sentinel envelope. При наличии обеих копий должны
совпасть envelope bytes/hash; malformed/conflicting copy блокирует recovery,
а не выбирается по mtime. Если old-name barrier ещё не создавался, immutable
block обязателен прежде rename. После создания verified tombstone может быть
standalone источником даже без historical index: третий индекс не сохраняется.
Transitive roots обоих current intent/metadata slots сохраняют direct block
ref и tombstone; после restart они заново validated **до** GC. Historical pin
удерживается до durable complete/фактического выхода jobs; затем memory pin
освобождается, persistent tombstone/ref остаются. Их удаляет только отдельно
разрешённое whole-scope deletion; root ledger gate/sentinel остаются для old
reader refusal. Старые index generations не накапливаются бесконечно.

`cleanup_authorization` — null либо ровно kind:`owner_confirmation|delete_purge`,
operation_id:identity, actor_user_id:identity, workspace_id:identity,
queue_object_id:id, queue_generation:u64. owner_confirmation создаётся только
continuation явного действия владельца для exact transaction/sources, operation_id
равен transaction_id (hex также valid identity). Receipt durable в этом intent,
не новая ledger schema. delete_purge ссылается на existing confirmed operation/
scope в queue. До любой очистки проверяется свежая queue authority/current owner/
receipt/cancellation; для ledger original проверяется право на **все** его rows,
не только один пакет. Unknown owner не подменяется текущим login. Старый anchor
и произвольный JSON не дают deletion right. cleanup_pending/complete требуют
non-null valid authorization;
stage complete только после actual absence proof. Смена authorization/пакета,
несогласованные bootstrap/intent/state/stage/refs — blocked, не auto-repair.

### 8.2. Закрытый реестр content-bearing temporary/quarantine путей

| Существующий logical path | Новый physical путь / исключение |
| --- | --- |
| `.canonical-mix.f32.tmp` | canonical protected blocks/index; checkpoint, без открытого float файла |
| `meeting-transcription.tmp.wav` → `.wav` | один media logical object; WAV bytes сразу защищены, seal после finalization |
| `meeting-review.tmp.m4a` → `.m4a` | один playback logical object/IStream; MF без physical URL/tmp |
| `manifest.json`, short-discard marker | protected manifest + package-state; marker удаляется последним |
| `capture-recovery.json` | protected recovery record; незавершённый capture state не normal |
| Ledger JSON, deletion/cleanup receipts | protected queue; полная candidate mutation одним ACK |
| AtomicFileStore `.tmp-*`, malformed new .quarantine | только opaque ciphertext envelopes; semantic failure сохраняет object, без plaintext dump |
| Migration old ledger/manifest sentinels и .quarantine | только encrypted intent block envelopes, old-reader отказ до switch |
| `legacy.originals`, pre-existing WAV/AAC temp/.quarantine/backup | уже существующий plaintext exception; не создавать новую открытую копию, не стирать автоматически и не объявлять encrypted inventory |

Только известные validated source roles переходят по §8.1. Остальные legacy
файлы сохраняются с blocking/cleanup-needed status; full encryption claim
запрещён, даже если новые записи protected. T116 ищет **всех** producers этих
путей; `.tmp-*` для content больше не проходит generic plaintext AtomicFileStore.

## 9. Обязательная приёмка, не результаты T114

T116: parser/integrity/overflow/EOF/Clone/CopyTo/SetSize/missing-vs-ZERO regressions,
bounded allocation/GC and ordered durability; protected canonical→WAV/AAC→
manifest→inspect/hash/upload/playback/delete со всеми temporary paths.
T116 дополнительно: g1→ACK g2/delete-intent→lost slot1→restart не выбирает g1;
двухслотовый birth/partial birth; strict payload codec; delayed/ambiguous ticket,
commit-before-stale-callback и retained flight/finalizer/delete result.
T117: cuts до/после каждой stage/old-name operation, actual old load при rename
до sentinel обязан видеть quarantine и отказать, orphan collision, bootstrap/queue/package
conflicts, original preservation/retirement и старый writer refusal.
T118: generated whole pipeline,100cycles, restarted accepted ranges/delete/purge,
disk snapshots без открытого content, actual profile/master-key refusal,
disk-full/power-loss, standard-user/noadmin/offline, Home/Pro/N (MF readiness),
Windows10 22H2/поддерживаемые11, exact installed MSIX/EXE/update/rollback,
UI/callback latency/SC003 и lifetime owned/MF memory peaks. App prerequisites
не заменяются наличием API; Home/N/codec и signed package доказать отдельно.
Ни Wrong entropy стенда, ни Parallels не закрывает physical x64/60min/AEC gates.

Первичные API: [DPAPI protect](https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptprotectdata),
[unprotect](https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptunprotectdata),
[IStream](https://learn.microsoft.com/en-us/windows/win32/api/objidl/nn-objidl-istream),
[MediaEngine byte stream](https://learn.microsoft.com/en-us/windows/win32/api/mfmediaengine/nf-mfmediaengine-imfmediaengineex-setsourcefrombytestream).
Wire/authority/bounds выше — проект GRAF, не стандарт Microsoft.

### Уточнение внутренней HTTP-интеграции T116 — 2026-10-10

Конструкция без изменения wire/schema/лимитов: `../plan.md`, раздел «T116:
защищённая HTTP-отправка и принятие результата». Применяются §5–7 выше.
Network не исполняется на единственном storage worker; UI не владеет native
inspection. Prepare changes и result truth/status публикуются каждый одним
full candidate с adoption ACK. Existing retry/account/server-truth правила
сохраняются. HTTP-body имеет одного charged immutable owner; request copies
не копируют logical content и не продлевают неучтённую plaintext allocation.
До независимого принятия конструкции и отказных RED production HTTP не меняется.
