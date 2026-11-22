# F296 parity: защищённая очистка только локального WAV

Дата: 2026-11-16. Срез F200 T128–T133, `high-risk-product`.
Статус: требования приняты; ниже интегрирован независимо согласованный проект
exact wire T129. Итоговый contract diff ожидает независимого review;
codec/deletion implementation и native/installed приёмка остаются открытыми.
Основание: решение владельца о полном текущем Mac parity, F296 и
[уточнение F200](../spec.md#session-2026-11-16--f296-локальный-кэш).
Не является разрешением удалять реальные данные при подготовке требований.

## 1. Область и неизменные гарантии

«Освободить место» удаляет только защищённый объект роли `media`, логически
`meeting-transcription.wav`, у подходящей завершённой записи. Это отдельная
операция от удаления встречи и полного local purge. Сохраняются exact bytes/hash
manifest, playback M4A, canonical/recovery и остальных retained roles, queue item,
directory/session/local recording/local revision IDs и серверная встреча.
Нельзя переименовать весь каталог в recycle, удалить packed container другой роли,
восстановить WAV перекодированием, уменьшить canonical prefix или изменить manifest
для сокрытия отсутствующего WAV. Шифрование DPAPI/CNG, confinement/ACL, memory/IO
bounds и правила unknown/orphan/pinned roots действуют без послаблений.

Область — новые sealed-normal v5 protected packages, существующие uploaded queue
items и действующий владелец. Capturing/finalizing/degraded/legacy-unmigrated,
local-only/unbound, несохранённые/неотправленные/failed, undecodable и записи с
открытым upload/repair/delete/purge или несовпавшим context сохраняются.
Защищённые старые версии не мигрируются автоматически ради очистки.

## 2. Свежий proof и единый предикат

Переиспользовать tenant/device-scoped
`GET /api/v1/desktop/recordings/{local_recording_id}/sync-state?local_media_revision_id=<id>`
и [F296 wire contract](../../296-server-cache-proof/contracts/desktop-sync-proof.md).
GET не требует открытия WAV или запуска upload; refresh работает и после cleanup.
Сохраняются TLS/auth/no-redirect, bounded parsing/timeouts/cancellation и
`Cache-Control: no-store`. Дополнительные поля совместимы со старым sync consumer;
старый сервер/отсутствующие поля не разрешают cleanup. Proof — временное значение
одного действия, не persisted permission; receipt хранит историческое основание,
но не выдаёт разрешение на следующее удаление.

Все следующие условия обязательны в одном текущем снимке:

| Проверка | Точное условие |
| --- | --- |
| Владелец | active authenticated origin/user/workspace/device и queue owner совпадают; owner/access/lifecycle доступны; нет stale auth/account generation |
| Локальное состояние | uploaded/finalized, bound; нет sync conflict, confirmed deletion, open deletion/purge/repair/upload |
| Meeting/revision | proof meeting совпадает с item; playback и finalized local revision присутствуют и равны item local revision; finalized server UUID равен playback server UUID |
| Finalized | отдельный finalized_upload: status finalized, archive_audio=true, валидные session/revision/finalized_at; active upload_session не заменяет его |
| Playback | state=available, can_play=true, reason_code=canonical_ready, object_verified=true; deletion_state=none, access_state=owner |
| Свежесть | age fetched_at и age verified_at каждый в диапазоне **[-60s,120s]**, включительно; >120s, >60s в будущем или неизвестное время → keep |
| Grace | now−finalized_at **≥604800s (7 дней)** |
| Retention | policy_state=active, delete_after−now **≥2592000s (30 дней)**; null не означает forever |
| Локальная целостность | проверены реальные held objects, IDs/generations/lengths/hashes, manifest и полный пригодный playback; измерены удаляемые bytes; нет чужого live pin/lease на удаляемую роль |

Возраст считается на фактический момент допуска к destructive step, а не на
момент показа кнопки; ожидание/сеть не продлевают120s. UTC ISO8601 поддерживает
дробные секунды; native account/deletion epochs сверяются заново после await.
Допуск часов60s взят из Mac LocalCacheEligibility.maximumClockSkew, не является
разрешением хранить proof180s. Требовать bounded валидные UUID/типы/даты; unknown
enum, duplicate/malformed keys, missing required data, offline, timeout,
401/403/404/409/5xx, unsafe/blocked/expired retention → keep, ноль удалений.

**Обязательное решение Windows:** playback.local_media_revision_id и
finalized_upload.local_media_revision_id оба присутствуют, корректного типа
и равны item local revision; finalized server revision UUID отдельно равен
playback server UUID. Missing/null/malformed/mismatch/legacy unknown → keep,
0 удалений для manual и auto. Отсутствующее поле не выводится из playback
или active upload_session. F296 wire §43 требует сохранять файлы при unknown;
server finalized_upload_custody_for_revision() выбирает local ID по exact
workspace/meeting/server revision и FINALIZED session. Mac optional guard
допускает отсутствие finalized local ID: Windows сознательно сохраняет WAV
в этом узком legacy/unknown случае. Полный корректный proof сохраняет parity.
Регрессии T128 проверяют otherwise-valid missing/null/mismatched finalized
local ID → keep/0effects и положительный полный exact proof.
Не сравнивать UUID и local ID в одном пространстве. Не использовать
processed/reviewAvailable/uploaded/cached serverTruth,
quota, предупреждение T127 или сам UI как самостоятельную authority.

## 3. Защищённый receipt и частичное состояние

Новая schema — **`graf.custody.package.v3`**, только для cleanup. Обычные full
writers продолжают v2; byte encoding и закрытые field sets v1/v2 неизменны.
Существующие DPAPI/CNG context, package-state slot/index/block format и IDs
сохраняются. Нет plaintext sidecar, второй БД, очереди proof или нового scanner.

### 3.1. Закрытая форма и пределы

Top-level содержит ровно10 keys в canonical writer order:
`schema, store_id, object_id, generation, directory_id, phase, reason,
short_recording_discarded, refs, local_cache_cleanup`. Первые9 имеют прежние
типы/ограничения; v3 требует `phase="sealed_normal"`, `reason=""`,
`short_recording_discarded=false`, все refs sealed и receipt не null.
Refs сохраняют прежний v2 exact10-field encoding/order:
`role, object_id, binding, generation, length, sha256, representation,
container_id, committed_extent, root_ref`, прежние representation/null rules
и canonical role order. **Все refs, включая historical media stamp, неизменны**;
исчезнувший media object не выдаётся за readable stream.

Payload≤65536 plaintext bytes, JSON depth≤3, keys/object≤10, refs≤5,
fields/ref=10; fixed optional receipt/arrays без heap DOM/input views.
Обе slots учитываются в прежних charged/wiping owned64MiB/32pins/IO bounds.
Writer использует закрытые ASCII/UUID/hex/enums без escapes. Unknown/missing/
duplicate key, unknown schema/enum, signed/float/overflow integer, лишний ref,
identity alias, receipt в v1/v2 или v3/null → отказ до публикации.
Read/write имеют явный schema switch; неизвестный schema не кодируется как v2.
Диагностика — только безопасные причины/числа/fingerprints, без content/secrets/paths.

### 3.2. local_cache_cleanup: exact9 keys

| Key в canonical order | Точный тип и значение |
| --- | --- |
| `schema` | Только `graf.custody.local-cache-cleanup.v1`. |
| `operation_id` | Nonzero16-byte ID, lowercase hex32 из existing secure RNG один раз до pending. Повтор manual/auto/restart использует тот же ID; это не recording/revision UUID. |
| `action` | Только `manual_cleanup` или `automatic_eviction`, неизменен при повторе из другой точки входа. |
| `state` | Только `pending` или `completed`; единственное изменяемое receipt field. |
| `base_generation` | JSON uint64 g, 1≤g≤UINT64_MAX−3, generation прошедшего full admission selected v2. |
| `base_sha256` | Lowercase hex64 SHA256 canonical полного v2 payload на g: восстановить schema2/generation g из неизменных первых9 полей/refs/context/directory существующим `writeCustodyPackage` и сравнить. Не hash текущего v3 и не новый ref codec. |
| `binding` | Exact7-key object ниже. |
| `proof` | Exact8-key object ниже, историческое основание, не новый grant. |
| `physical` | Exact7-key object ниже, только фиксированный media inventory. |

`binding` canonical order/types:

1. `owner_user_id, owner_workspace_id, device_id` — каждый `[A-Za-z0-9_-]{1,300}`;
   не token/email.
2. `origin_sha256` — lowercase hex64 SHA256 точных UTF-8 bytes canonical origin
   уже проверенного native auth/config scope того же GET; не URL из receipt и
   не иная самодельная нормализация.
3. `queue_object_id` — existing queue context ID lowercase hex32; top store_id
   совпадает с реальным held root/queue.
4. `queue_generation` — uint64≥1 исторического snapshot до pending.
5. `queue_sha256` — hex64 SHA256 exact serialized snapshot bytes существующего
   `ProtectedUploadQueueValue::serialize`, включая server/access/status fields.

`localRecordingId == sessionId == directoryId == top.directory_id`;
`localMediaRevisionId = directory_id + "--initial"` для этого среза, без нового
UUID/иного derivation. Оба server proof local IDs обязаны совпасть с ним по §2.
Queue fingerprint не вечное permission: обычные authorized queue changes после
completed допустимы; каждый destructive шаг проверяет текущий row/scope/lifecycle.

`proof` canonical keys: `meeting_id, media_revision_id,
finalized_upload_session_id, fetched_at_ms, verified_at_ms, finalized_at_ms,
delete_after_ms, admitted_at_ms`. Первые3 — bounded canonical UUID strings36;
server revision UUID один, поскольку playback/finalized UUID обязаны совпасть.
Последние5 — UTC epoch milliseconds uint64>0, в проверяемой календарной области
existing date parser, с checked arithmetic. Scope/archive/verified/retention
предикаты доказываются до публикации, не заменяются optional bool defaults.
Timestamps неизменны при restart/refresh и не продлевают intent. Для каждого
нового delete нужен текущий proof §2, совпадающий с receipt по origin/device/
owner/meeting, обоим local IDs, server revision UUID и finalized session.

### 3.3. physical: exact7 keys и native identity

Canonical keys: `volume_serial, package_file_id, media_directory_file_id,
id_file_id, content_file_id, content_length, content_sha256`.
`volume_serial` — hex16 unsigned VolumeSerialNumber проверенного root и всех
четырёх file/directory identities. Каждое FileId — nonzero16 native bytes
`FILE_ID_INFO.FileId.Identifier`, lowercase hex32 в порядке массива,
без UUID/endian преобразования.

**package_file_id — сам каталог записи**
`<held trusted root>/<validated directory_id>`, не `.custody-v1`, role directory,
package-state/id.bin/index/block/slot. ID и volume снимаются одним успешным
`GetFileInformationByHandleEx(..., FileIdInfo, ...)` с того же удерживаемого
native directory handle при full admission до pending. Только existing каталог,
без create/repair; native directory/non-reparse attributes, ACL/confinement и
проверенная root/parent chain обязательны. Каталог записи/parents удерживаются
на протяжении эффекта; после любого reacquire/restart и перед каждым delete,
до/после открытия target заново сверяются chain/attributes/ACL/volume/FileId.
Held handle не отменяет проверки replacement по fixed path; одно имя/ID/receipt
не заменяет остальных guards. Каталог записи не удаляется и обязан оставаться
тем же при pending/completed. Missing/replaced/unknown identity, query/cancel/
неподтверждённый close/absence → stop/keep/reconcile, не следующий delete или
успешный completed ACK. Разрешённая absence media не означает absence package.

Остальные IDs относятся ровно к media directory и его `id.bin`/`content.packed-v2`.
`content_length` — actual cipher file length, uint64≥packed appendOffset и
≥ref.committed_extent, ≤INT64_MAX и прежних native IO/storage bounds.
`content_sha256` — hex64 streaming SHA256 всего cipher content, без PCM/files
с открытым аудио. `id.bin` — ровно16 bytes media ref.object_id; отдельный hash
не нужен. Ни пути, ни список имён из wire не принимаются.

### 3.4. Admission layout/migration

Только sealed-normal v5: full v2 с packed media и exact inventory
`<directory>/.custody-v1/media/{id.bin,content.packed-v2}`. Переиспользовать closed
`completedPackageRole` inventory pattern; root scanner не ослаблять.
Logical packed root/extent/generation/whole SHA проверяются прежним reader,
cipher hash — дополнительная привязка. Full admission проверяет обе прежние
slots/refs. Flat v1/v2, legacy-unmigrated/unknown layout → keep, без миграции
ради cleanup. Уже мигрированный пакет допустим только при independently verified
migration complete/завершённом original cleanup и прежних history/barrier guards.
Exact destination stamps всех refs неизменны; original WAV/intent эта операция
не удаляет. Incomplete migration → keep, без принудительного продвижения.

## 4. Публикация, удаление и восстановление

Один existing custody worker/rootLease, single-flight с package/queue mutations;
никаких I/O на UI/audio callback. До pending: full package/M4A/queue admission,
fresh §2 proof и physical snapshot, нет upload/repair/purge/deletion/recording/
foreign reader; admission новых media consumers закрыт, собственные readers/
Clones действительно drain. Readonly pair освобождается перед mutation;
readonly proof не повышается до writable.

Узкий owner-side метод открывает existing package-state write lease без create/
repair/openUnfinished, перечитывает обе slots и сверяет semantic pair/base.
Private cleanup-owner provenance не выдаётся за isolatedReadOnly/публичный bypass.
DELETE media handles открываются до первого destructive шага; retained leases
и parent identities удерживаются, после reacquire всё проверяется заново.
Переиспользовать `CustodyMetadataCommit::commitImpl` reserve/flush/index placement/
independent reopen. После **каждой** публикации — BOTH semantic payload readback,
exact receipt/base/ref comparison и typed **committed** ACK. Recording schema2
commit/validateRefs не ослабляются. Disk-full/notCommitted/ambiguous/cancel/IO/
allocation/epoch mismatch → stop/reconcile, не догадка по higher generation.

| Actual selected / peer slots | Допуск / восстановление |
| --- | --- |
| Full g / прежняя peer, receipt нет | Обычный full package; missing media без receipt = corruption/keep. |
| Pending g+1 / exact full g | Первый ACK, **delete запрещён**, media цел. Совпадают base/refs; после fresh guards возможен только второй pending. Уже частичная absence — нарушение, не законный cut. |
| Pending g+2 / pending g+1 | Второй ACK; тот же operation/base/refs/bindings, отличается generation. Только теперь допустим первый delete после fresh admission. |
| Эти два pending, все media files/dir целы | Заново current proof/scope, retained closure/native/cipher/logical identity; тот же intent, не новый ID. |
| Эти два pending, content отсутствует, id.bin/dir целы | Проверить оставшиеся IDs/id bytes/inventory/retained closure; следующий delete только после fresh guards. Не full proof. |
| Эти два pending, оба файла отсутствуют, exact dir цел/пуст | Проверить exact directory ID/parents/empty inventory и fresh guards; удалить только этот каталог. |
| Эти два pending, media directory отсутствует | Base/retained closure и confined actual absence → metadata-only completed; второго delete нет, expired proof не permission. Current account fences действуют. |
| Completed g+3 / pending g+2 | Actual media absence, обе retained closures и BOTH semantic ACK; receipt отличается только state. Лишь теперь UI success. Дополнительное completed mirror не нужно. |
| Completed / completed, successive generations≥g+3 | Immutable operation/base/refs и no-media состояние; idempotent noop,0 новых deletes/bytes. Metadata mutation сохраняет receipt; возврата schema2/full/нового ID на тех же bytes нет. |
| Bad slot/operation/base/generations, replaced/extra objects, content present при missing id, completed с media present | Refuse/UNKNOWN/reconcile; не выбрать удобную slot, не удалить replacement/очередь и не восстанавливать WAV/revision. |

Дополнительный pending checkpoint запрещён: он разрушает различимость первого
и второго ACK. После первого completed selected pending не возвращается.
Generation overflow/wrap запрещён; при исчерпании uint64 дальнейшая mutation
отказывает. Сбой требует fresh owner/reconciliation без schema rollback.
Снять fence при целом pending можно лишь сохранив partial classification,
не full upload proof. Старый full peer не даёт authority.

Physical порядок: **content → id.bin → пустой media directory**. Полный inventory
не допускает extra file/subdir/ADS/reparse/hardlink/неожиданные attrs/ACL.
Полный cipher hash/length и disposition — через тот же retained content handle,
как существующий same-handle migration-original pattern. Перед каждым эффектом
заново §2 proof ages, queue/scope/lifecycle/epochs, auto settings, pins и held
identities; ожидание commit не продлевает proof. Каждый handle действительно
закрыт, confined native absence подтверждена; unknown не absence. Directory ID
сохраняет locator до последнего эффекта, даже после удаления id.bin.
Sharing/IO/timeout/close/absence failure остаётся pending/error, не completed.
Нельзя remove_all/recycle whole package/force unload/менять ACL/readonly или
чужие refs. Общий GC не получает permission; whole purge имеет свой admission.
После completed actual storage query наблюдает physical used/free; logical WAV
length/cipher length не доказывают освобождение кластеров.

## 5. Совместимость потребителей

Private-constructed `LocalRecordingPackage::PartialPlaybackInspection` удерживает
genuine pair, retained readers/leases обеих slots, session/manifest buffers,
cancel, duration/start/stop/timezone и PlaybackEvidence. Не содержит
`ProtectedEvidence{integrity=valid}`, не конвертируется в full/upload permission.
`inspectPartialPlayback(root,pair,expectedSession,cancel)` принимает только
законную v3 pair state machine. Private sparse group проверяет structural identity
edges всех refs обеих slots, включая media stamp; все остальные closures/whole
hashes открывает и проверяет полностью. Ровно один media object допускает
неоткрытие лишь по exact receipt/base и отдельной проверке physical inventory.
Это не полный `CustodyPackageReaders`, не public skipWav/null-stream обход.

Переиспользовать manifest/session/artifact comparison: historical media artifact
совпадает с сохранённым ref, playback — с фактическим retained M4A. Whole M4A
hash, native decode **до полного EOS**, format/flags/timestamps/duration bounds,
rewind всех retained readers, canonical/recovery и peer roots обязательны.
Player получает typed partial overload с прежними readerInstances/Clone/account/
COM/MF/cancel/close/drain guards и общими startup/close helpers. Малый закрытый
lifetime variant допустим, новый framework/общий ignore-missing — нет.
Receipt не proof слышимости и не обход T116–T118/T088/T110/AAC gates.

| Существующий потребитель | Обязательное изменение до включения первого v3 writer |
| --- | --- |
| Metadata PackageJson/packageShape/write/read/revalidate | Closed schema3 и semantic BOTH pair validation; full reader/inspector явно отвергает любую cleanup pair до member open. |
| ProtectedCustodyReader full openers | Сохраняют full result/provenance; private retained helper и отдельный typed sparse result, без null media в full group. |
| LocalRecordingPackage / protected player | Общие manifest/playback primitives, отдельный partial proof/overload; display `authorizedPartial`, не `valid`. Codec-only playback не shortcut authority. |
| NativeCapture playback/display | Full/partial выбираются по доказанной pair classification; текущие session/account/command fences, timing/capabilities без WAV/send availability. |
| Startup/queue/recovery/repair/upload/calendar preflight/replay | Recognized partial до generic malformed/quarantine/retry; item/revision/serialized queue bytes сохраняются, WAV не reencode/repair. Нет нового upload/revision или подмены uploaded row; WAV-required path честно unavailable. |
| readPackage/validateMigrationPackageHistory, cold admission/recycle | Явная full/partial closure ветка, exact history/stamps/barriers/original absence. Partial proof не даёт purge/recycle permission; openUnfinished не достраивает media. |
| DesktopHttpTransport/network | Fresh sync GET до/без loadTracks и после cleanup; historical receipt не grant. UploadProtected по-прежнему full private proof и все3 tracks. |
| Account/delete/purge | Stale callbacks не действуют; смена аккаунта не выдаёт content/cleanup; настоящий deletion/purge сильнее cache noop. |

**Compatibility/rollback:** v1/v2 full read/write/inspection и golden bytes
неизменны; unsupported flat cleanup → keep. Текущий старый codec читает обе slots
и отвергает любой v3, даже с full peer. Source отказ не доказывает безопасность
всех historical/updater binaries. До native writer нужны frozen old-reader/new-
writer и new-reader/old-full fixtures; до installed activation — rollback gate:
старый reader не получает writable/effect admission, не чинит/мигрирует/удаляет
partial и сохраняет bytes/queue. Snapshot rollback всего диска receipt не защищает.

Минимальные регрессии в существующих suites, без нового framework:

1. `ProtectedCustodyPackageTests.cpp` / `ProtectedCustodyCodecTests.cpp`:
   v1/v2 golden, v3 roundtrip/max-bound/depth/keys, каждый
   missing/duplicate/unknown field/schema/state/enum, foreign context/queue/owner/
   refs/base hash, uint64 overflow и все допустимые/недопустимые пары §4.
2. `ProtectedCustodyFilesTests.cpp` / `ProtectedPackedCustodyOwnerTests.cpp`:
   native IDs roundtrip; ID `.custody-v1`/package-state
   вместо recording directory, same-path replacement/wrong volume/reacquire,
   query/close/cancel UNKNOWN →0 следующих effects/не completed; metadata slot
   update не меняет package_file_id. Same-handle hash/inventory, ADS/link/reparse/
   ACL/extra files, foreign reader/Clone и каждый delete/close/absence fault cut.
3. `NativeCaptureStorageIntegrationTests.cpp`:
   actual sealed v5 → full proof → BOTH pending ACKs → все
   physical cuts → completed → cold reopen/full M4A EOS/close/drain; точные
   до/после hashes retained content и serialized queue bytes. Crash после каждого
   commit/publish/readback/delete, disk-full/admission/allocation/ambiguous без
   forced cleanup. Missing media без receipt и completed/replacement → отказ.
4. Existing migration/playback suites и `DesktopUploadQueueV2Tests.cpp` /
   `DesktopUploadRecoveryTests.cpp`: complete migration + partial cold/recycle, incomplete
   originals →0 cleanup; no quarantine/revision/reupload, fresh GET без WAV;
   scope/device/origin/account/delete/settings changes на каждом await/cut →0
   следующих deletes, no stale playback; retained hash/peer/manifest/decode/time/
   rewind/clone/drain negatives. Frozen old/new binary и installed rollback
   отказ сохраняет exact bytes/queue. Описанные тесты ещё не выполнены этим текстом.

## 6. Ручное действие, UI и автоматическая очистка

Через существующие WebView/native capabilities, document nonce и auth epoch:
«Освободить место» → подтверждение роли и измеренных bytes → confirm/cancel.
Текст: «Будет удалена только локальная копия файла транскрипции этой записи.
Аудио для прослушивания и описание записи останутся на этом компьютере.
Встреча на сервере не удалится». Cancel ничего не меняет; stale capability
отвергается native. Reason/unknown/failed/noop отличаются от успеха. Native surface
и UIA/клавиатура доступны без зависимости только от цвета; предупреждение не
скрывает indicator/Stop/ошибку сохранения. WebView не передаёт paths/proof как право.

«Локальный кэш»: измеренные occupied/budget, объяснение, переключатель
«Автоматически освобождать место»; default user=true как Mac, effective=
user && !operatorDisabled. `GRAF_DISABLE_LOCAL_CACHE_AUTO_EVICTION` использует
Mac truthy1/true/yes без учёта регистра и внешних пробелов, перечитывается перед
каждым удалением. Выключение немедленно прекращает новые удаления; завершение
уже начатой metadata transaction не представляется отменённым rollback.

Auto использует **тот же primitive**, single-flight/off-UI, запускается после
launch/Stop/finalized upload/pressure, debounce60s; не больше20 candidates и50
удалений за проход (фактически не больше числа candidates), oldest finalized_at
first с детерминированным fingerprint tie-break. Candidate discovery: как Mac
max scan200/proof timeout5s/total budget120s; scope/settings/cancel проверяются
между candidates, capture commands/Stop/finalizer приоритетны. Пока идёт запись,
очистка не конкурирует с capture/finalization mutations; повторный trigger
объединяется и обслуживается после освобождения соответствующего worker/lease.
Начать при physical used≥80% от5GB либо free≤min(10GB,10%capacity); прекратить,
когда used<80% **и** free>reserve, при exhausted bounds или отказе scope/settings.
После completed заново наблюдать actual physical used/free через существующий
worker; не выводить free из logical WAV length и не продолжать при unknown query.
95% остаётся existing critical admission boundary, не разрешением удалить без proof.
Unknown pressure → keep. Учитывать весь store/retained/pinned/temp/metadata как T127;
reserve/capture factory,5GB,80/95% и memory bounds не меняются. Не обещать cleanup
при невозможности durable receipt: сохранить данные и честный отказ.

## 7. Источники и границы

F296 [proof](../../296-server-cache-proof/contracts/desktop-sync-proof.md),
[reasons](../../296-server-cache-proof/contracts/eligibility-reasons.md),
[receipt semantics](../../296-server-cache-proof/contracts/cleanup-receipt.schema.json),
[UX](../../296-server-cache-proof/contracts/ux-copy.md); Mac LocalCacheEligibility,
LocalCacheCleanupService, LocalCacheEvictionPolicy/Scheduler. Семантика переносится,
Mac plaintext receipt format не становится разрешением plaintext на Windows.
Server storage/status — supporting API; quota/billing panel не добавляется как
несуществующее Mac runtime требование. Исторический installed Dev до F296 не
доказывает новую функциональность. Изменений server/Mac этим срезом не требуется.

До исходников Phase29: независимый [checklist](../checklists/f296-local-cache-cleanup.md),
analyze и issue sync Main. После этих общих gates разрешён только неразрушающий
T128 GET/parser/eligibility и его регрессии: без partial writes, активации partial
consumers, удаления, upload/WAV side effects. Exact T129 version/layout/limits,
BOTH pairs/native IDs/typed consumers/old-reader/rollback заданы в §3–5.
Объединённый проект прошёл второе независимое review 16.11.2026; отдельный
wire/codec/consumer gate требует независимого review **итогового contract diff**
до codec/reader/writer изменений. T130 destructive path зависит от T129.
Frozen full+partial artifacts требуются для соответствующей native/installed
приёмки, не начала T128.
Текущий документ не закрывает эти gates и не меняет прежние acceptance receipts.
