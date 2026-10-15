# Data Model: Windows desktop-приложение GRAF

Документ описывает продуктовые и межслойные сущности. Он не создаёт новую
серверную таблицу: локальная модель должна проецироваться на существующий v5
manifest и локальный ledger: запись `desktop-upload-queue.v3`, чтение v2/v3,
историческое имя файла `desktop-upload-queue.v2`. Неизвестная схема изолируется,
не заменяется пустой очередью; откат приложения не должен перезаписывать v3
старым писателем. Старые упоминания v2 ниже описывают совместимость/имя файла,
а не разрешение потери операций удаления новой схемы.

## 1. WindowsDesktopSession

One active native recording session per user process.

| Field | Type | Persisted | Invariant |
|---|---|---:|---|
| `session_id` | opaque string/UUID | yes | immutable and unique per local package |
| `state` | `SessionState` | yes | every transition is explicit and monotonic except `paused`/`recording` |
| `started_at` / `stopped_at` | ISO-8601 | yes | server-independent local timestamps |
| `target_evidence` | bounded object | yes | absent for manual start; never guessed from process name |
| `permission_snapshot` | `PermissionSnapshot` | yes | records observed OS/device readiness, not a guarantee of future availability |
| `system_route_generation` | non-negative integer | yes | changes on endpoint/clock discontinuity |
| `microphone_route_generation` | non-negative integer | yes | changes on endpoint/clock discontinuity |
| `capture_health` | `CaptureHealth` | yes | counts/reasons only, no samples |
| `finalization` | `FinalizationState` | yes | normal package only after all required artifacts pass |

### SessionState

```text
idle
checking_readiness
ready
starting
recording
paused
degraded
stopping
finalizing
saved_local
queued
uploaded
blocked
failed
```

`recording` and `paused` are the only active capture states. `degraded` can be
active only while the user can still invoke Stop; it cannot be advertised as a
normal session. There is no state in which capture is active but the indicator is
hidden.

### Приватные сегменты сессии — T120, 2026-10-04

`privacySegments` принадлежит логическому v5 manifest той же сессии/пакета,
не серверному разрешению или отдельному журналу. Модель и Codable names —
Mac `ProductPrivacySegment`/`LocalRecordingManifest` на c8d67c…:

| Поле | Представление | Правило |
| --- | --- | --- |
| segmentId/sessionId | строка | неизменная привязка к текущей сессии; ID сегмента уникален |
| control | pause/resume/stop | новый Pause создаёт pause, финализация не выдумывает новый control |
| startedAt/endedAt | ISO8601 UTC | дата начала обязательна; endedAt отсутствует для OPEN |
| startMonotonicMs/endMonotonicMs | неотрицательное целое | отсчёт от начала записи; end отсутствует для OPEN, не раньше start |
| durationMs | неотрицательное целое | OPEN0, закрытый max(0,end−start), без overflow |
| localMicTreatment | silenced/redacted/ended | пользовательская Pause — silenced |
| initiator | RecordingEvidenceInitiator | пользовательская Pause — user |
| diagnosticSafe | bool | новый продуктовый сегмент true; не содержит samples/paths |

Mac Codable опускает nil endedAt/endMonotonicMs; Windows fixtures должны
сохранять этот смысл и known legacy отсутствие privacySegments. ISO8601
кодирование определено LocalRecordingManifestService, а не угадывается по
wall-clock числу. JSON whitespace/key order не являются новой authority.
Полный manifest≤64KiB по local custody §3; не вводится отдельный cap числа
сегментов или потеря старой истории. Несовместимая/повреждённая форма blocked.

Принятый OPEN предшествует подавлению. Принятый Resume требует точной FIFO
границы; failed CLOSE сохраняет прежний durable OPEN. Storage completion
привязан к session/generation; Stop остаётся доступным и late result не
возобновляет запись. T116 внедряет защищённую запись, T120 — этот control flow;
наличие модели не означает выполненную интеграцию.

## 2. PermissionSnapshot

```json
{
  "microphone": "granted|denied|restricted|unknown",
  "microphone_endpoint": "ready|missing|unsupported|unknown",
  "render_endpoint": "ready|missing|unsupported|unknown",
  "storage": "ready|low|full|unavailable",
  "webview_runtime": "ready|missing|repair_required|unknown",
  "observed_at": "2026-08-23T00:00:00Z"
}
```

The snapshot is a readiness explanation. It does not contain a Windows token,
cookie or raw device path. Device display names may be shown in UI only after
bounded normalization; diagnostics use stable hash/fingerprint or safe class.

## 3. WasapiEndpointSnapshot

The in-memory endpoint descriptor is richer than persisted metadata:

```text
endpoint_id             # in memory; never put in committed evidence
endpoint_fingerprint    # bounded hash for diagnostics
data_flow               # render | capture
role                    # console | communications | multimedia
is_default              # bool
sample_rate             # observed device rate
channel_count           # observed channel count
sample_format           # PCM/float and bit depth
route_generation        # monotonically increasing local generation
clock_domain            # opaque local identity
state                   # active | disabled | unplugged | invalidated
```

The source may use its device mix format. A worker normalizer produces the
canonical `48_000 Hz`, mono, float representation while retaining the source
PTS and route generation.

## 4. RecordingAudioBatch

До публикации batch ClockMapper получает полные битовые flags WASAPI. Только
первый непустой пакет новой сессии с flags=0x1 может быть отброшен по контракту
§5; он не задаёт origin/фазу/offset. Worker отдельно хранит счётчик успешно
освобождённых стартовых кадров (0..4800) и типизированный clock fault.
В MetadataSnapshot это две пары `render_*`/`microphone_*` полей, не часть
сохраняемого v5/v2. Чтение итоговой сводки происходит после завершения workers.

Each source producer publishes a bounded value to its queue:

```text
source                  # system_render | microphone
samples                 # in-memory float samples; never persisted as metadata
source_frame_count
source_sample_rate
source_channel_count
presentation_timestamp  # full WASAPI QPC before normalization; canonical frames after it
clock_domain
device_position_frames  # optional WASAPI position
qpc_100ns               # optional packet QPC; fixed 100-ns units from GetBuffer
audio_clock_position    # IAudioClock position for packet continuity
audio_clock_frequency   # IAudioClock frequency; fixed for the worker route
route_generation
discontinuity            # none | device_changed | clock_changed | overflow |
                         # invalid_timestamp | service_interrupted
```

Invariants:

- callback code drains packets and enqueues or records an overflow; it does not
  write files, call WebView, allocate unbounded memory or run AEC3;
- a timestamp must be finite/monotonic inside its source route generation;
- samples from different clock domains are never aligned directly;
- queue capacity and maximum reorder window are finite and covered by tests;
- the timeline emits only canonical 480-sample pairs to AEC3.

Для Windows worker `audio_clock_position` и `audio_clock_frequency` берутся
из `IAudioClock::GetPosition/GetFrequency` как дополнительная проверка часов,
не как timestamp начала пакета. PTS каждого пакета — его `GetBuffer.qpcPosition`
в 100 ns; device position проверяет непрерывность отдельно. Повтор текущего
IAudioClock при чтении нескольких накопившихся пакетов допустим только при
самостоятельно корректных packet QPC/device/flags. Нельзя безусловно принимать
пакет из-за наличия IAudioClock или синтезировать PTS суммированием frameCount.
Действующие пределы/отказы — контракт §5 от 2026-09-26; код T094–T096 должен
быть приведён к нему до приёмки.

T085: device position is a per-stream integrity observation, never the common
presentation origin. Source-normalization phase follows submitted samples;
presentation timestamps retain QPC offset separately. The bounded drift
envelope and ±48-frame interpolation/overlap rules are defined in contract §5.

## 5. RecordingAudioTimeline

The timeline is the only alignment owner.

| Field | Meaning |
|---|---|
| `canonical_sample_rate` | 48,000 Hz |
| `canonical_channels` | 1 |
| `aec_frame_samples` | 480 |
| `system_queue` / `microphone_queue` | bounded normalized batches |
| `active_route_generations` | current system/microphone generation pair |
| `last_emitted_frame` | canonical frame index |
| `max_buffered_frames_per_source` | `960_000` canonical frames (20 s at 48 kHz) |
| `max_clock_recovery_frames_per_batch` | `48` canonical frames (1 ms at 48 kHz) |
| `dropped_frame_count` | diagnostic counter |
| `overflow_count` | diagnostic counter |
| `clock_discontinuity_count` | diagnostic counter |
| `aec_processed_frames` | diagnostic counter |
| `aec_error_count` | diagnostic counter |
| `trusted_prefix_only` | true after a terminal integrity error |

The timeline calls AEC3 in the fixed order `system/reference` then
`microphone/near-end`, combines the cleaned microphone with the unchanged system
component and sends canonical chunks to the writer. It never returns raw
microphone samples as a normal artifact.

The buffer and correction bounds follow macOS defaults. T085 removes unused
reorder/15-second gap fields from Windows: workers deliver packets in source
order, and a gap above 48 fails the normal segment. Independent source arrival
order is retained. Synthetic evidence must cover latency, memory, overflow,
duration and common-start prefix disposal; queues cannot grow without bound.

## 6. LocalRecordingPackage

The directory is user-scoped and contains only the established v5 package shape:

```text
LocalRecordingPackage {
  directory_id: String,
  schema_version: "local-recording-manifest.v5",
  canonical_mix_profile: "canonical-mix.v1",
  source_kind: "initial_mixed_recording",
  manifest: LocalRecordingManifest,
  artifacts: [ArtifactDescriptor],
  integrity: PackageIntegrity,
  local_deletion_registered: Bool
}
```

`ArtifactDescriptor` fields:

| Field | Normal value |
|---|---|
| `role` | `mixed_meeting_audio` / `review_playback` |
| `file_name` | `meeting-transcription.wav` / `meeting-review.m4a` |
| `format` | PCM S16LE 16 kHz mono / AAC-LC 48 kHz mono |
| `byte_count` | positive bounded integer |
| `sha256` | 64-char digest |
| `duration_ms` | duration measured from decoded/known frames |
| `status` | `writing` / `verified` / `degraded` / `failed` |

The local role names are an app-facing projection. At upload time they MUST map
to the server roles `media` and `playback`; the manifest track descriptors and
upload-session request also include `manifest`. The v5 session therefore uses
`media_scribe_source_mode=single_wav_v1` and the exact role set
`{manifest, media, playback}`. It must never be sent as the historical dual
shape `{manifest, microphone, system}`.

The manifest may carry optional Windows capture health and endpoint class fields
compatible with existing optional v5 decoding. It must not introduce a second
server-required package schema or store raw endpoint ids, local absolute paths,
cookies, tokens, audio samples or transcript content in evidence.

## 7. UploadCustodyItem

Windows uses the existing queue ledger and maps it to the same custody projection
as macOS:

```text
local_recording_id
local_media_revision_id
platform = windows
state = queued | uploading | retrying | uploaded | degraded | blocked | failed |
        terminal_deleted
server_truth
accepted_bytes_by_track
retry_class = automatic | manual_only | terminal
failure_category
sync_conflict_state
retention_deadline
```

The ledger is written atomically. A malformed document is quarantined with a
bounded reason code and a recoverable backup; it is never replaced by an empty
document. Server reconciliation wins over local guesses for server meeting,
media revision, upload session and accepted ranges.

## 8. WebViewBridgeEnvelope

Уточнение 2026-09-27: `request_app_update` использует тот же проверяемый envelope
и строго пустой payload. Это просьба открыть нативную проверку, не передача
пакета/адреса/команды установки. `GRAFDesktopPlatform` — конечное значение
`windows` или `macos` для представления общей страницы; отсутствие сохраняет
совместимость отображения старого Mac. Значение не даёт полномочий и не
сохраняется в данных встречи. UI обновления хранит только эфемерные состояния
checking/current/available/unavailable/error и generation; неизвестный источник
не приравнивается к current. Сохранённые схемы записей/очереди не меняются.

Web-to-native requests use this JSON shape; native display messages are
specified separately in `contracts/windows-native-web-bridge.md` §4:

```json
{
  "protocol": "graf.desktop.bridge",
  "version": 1,
  "direction": "web_to_native",
  "message_id": 1,
  "nonce": "ephemeral-nonce",
  "origin": "https://rec.2brain.pro",
  "command": "request_app_quit",
  "payload": {"action": "quit"},
  "sent_at_monotonic_ms": 12345
}
```

Rules:

- `nonce` changes whenever the WebView document/origin/session boundary
  changes;
- native validates `Source`, exact origin, route kind, version, direction,
  message id, payload size and command-specific payload before action;
- only `request_app_quit`, `local_recording`, `app_appearance`,
  `native_settings`, `delete_selection`, `request_app_update`, `calendar_join`
  and cancellation-only `calendar_join_cancel` are accepted as requests;
  their exact payloads and current-state checks are defined in the bridge
  contract; obsolete settings/diagnostics/repair/acknowledgement aliases fail;
- web receives `native_ready`, typed settings replies, deletion outcomes and
  bounded `local_recordings` display rows/operations/recoveryRequired, never
  file paths, tokens, device handles or raw samples;
- unknown commands, stale nonce, duplicate id, oversized payload and invalid JSON
  are rejected with a bounded error and no side effect;
- no web acknowledgement is accepted or treated as proof that audio was saved,
  uploaded or removed; only local custody/server truth can establish that.

T119 добавляет эфемерный CalendarJoinOperation по bridge contract §10:
event/request UUID, operation ID, origin/owner/workspace/auth generation,
document/nonce либо native action identity/epoch/deadline, state и safe reason.
Session token/https_url нужны только в памяти текущей операции, не сохраняются
и не проецируются в web reply/history. Один busy owner для всех Join entrypoints;
terminal/stale callback не изменяет новую операцию. Record не является payload
моста; native joinAndRecord проходит отдельную проверку после handoff.

Document Join correlation: canonical event/request UUID, pinned generation/nonce,
до1024 consumed request UUID без вытеснения. Join consumes UUID даже при busy/
not-ready; replay не создаёт flight. Cap-отказ — исключение: UUID не admitted/
consumed, его повтор даёт только cancelled/not_ready без work/history growth;
replay saved UUID проверяется первым. Cancel содержит только те же два UUID,
не создаёт request и относится лишь к matching document pending. Новый document
сбрасывает consumed set, но не завершает actual SDK/worker child прежней операции.

Recovery сохраняет operation/request identity и внешний opening до результата.
Новый deadline относится только к свежему resolver после явного подтверждения;
исходный action expiry не продлевается. Terminal UI и actual pending-work drain
раздельны; новое действие не принимается до drain. State/fence owner не хранит
ссылку и не считает вызов cancellation доказательством завершения работы.

CalendarNativeLauncher — один ephemeral owned query/launch SDK handle без
HTTP/dialog/auth/capture authority. State owner сохраняет operation/work ticket.
Discard-only cancellation удерживает handle; natural Completed/Error означает
owned API child completion, indeterminate Status/Canceled — busy без разрешения
drain. StartFailed завершает только синхронный dispatch scope без полученного
handle, не доказывает отсутствие OS effect. Current/receiver/handoff/Record
остаются отдельными доказательствами; неопределённая работа не пересоздаётся.

T119 native upcoming projection: CalendarReminderSnapshot дополнен server
showUpcomingTime/showUpcomingTitle (default true для missing/null), event.allDay
(default false для missing/null). Present non-bool отвергает весь ответ. Это
эфемерные поля существующего snapshot, не новые local preferences. Privacy
titleState и прежняя owner/UUID/instant/link validation остаются обязательными.
Menu rows — startsAt/eventId sorted prefix12, независимо от card canSurface,
dismissal/quiet/capture; source current берётся только из доступного принятого
snapshot. Ошибка refresh очищает menu, даже если card сохраняет failed Retry.

Native menu selection хранит frozen event target (eventId/startsAt/endsAt/link
availability/URL identity), owner epoch и native action UUID; не свежий row index
и не card pendingAction. Original endsAt один раз преобразуется из remaining
wall duration в checked steady_clock expiry на принятии выбора; invalid/expired/
overflow отвергаются. Current требует неизменного target/owner, доступной текущей
проекции и исходного expiry. Presentation-only flags/title refresh прекращает
popup tracking, но не меняет target уже принятого flight. Normal popup close
после selection — не отмена flight. Ни один из этих фактов не actual drain.

Menu failure Retry — dialog work общего operation owner до terminal, отдельный
purpose от browser recovery. После matching dialog drain + explicit current
Primary прежний attempt становится failed, новый request/operation получает тот
же source/expiry и новый resolver budget click+15s. Не возобновлять terminal,
не переиспользовать URL, не освобождать busy между попытками для другого Join.
Cancelled/stale/unknown exit не начинает новую попытку. Menu never Record;
card/document sources и их lifetime остаются прежними.

T119 display-time context (Round243): ephemeral origin/native owner/workspace/
auth generation/token identity/document generation/nonce/context revision плюс
metadata session UUID и optional preferred IANA zone. Metadata не auth authority
и не persisted preference; принятие только по plan «T119: пользовательское время»
и bridge§10. Invalid current data сбрасывают preference в system fallback;
stale completion не стирает более новый context. Account/session/origin switch
сбрасывает его до нового accepted document. Display revision влияет на popup
tracking, но не заменяет event/Join identity и immutable action expiry.

## 9. VerifiedTargetIdentity

```text
target_key                 # stable product registry key
display_name               # user-facing name
executable_identity_hash   # stable identity proof, not a raw path in evidence
publisher_or_signature     # approved bounded proof
installation_scope         # per_user | machine | unknown
registry_version           # reviewed registry version
prompt_capable             # bool
auto_record_preference     # always | ask | never; local, target-scoped, reversible
```

A friendly process name without the identity proof cannot enable automatic
recording. Registry identity and the client-owned preference are distinct:
the server must not store, authorize or acknowledge `auto_record_preference`.
This is a local model, not a new server or manifest field.

### Актуальный выбор автозаписи (2026-09-06)

| Значение | Название | Поведение при подтверждённой встрече |
|---|---|---|
| `always` | `Всегда` | Начать без вопроса, если выполнены все условия записи |
| `ask` | `Спрашивать` | Показать вопрос с восьмисекундным таймером; истечение запускает текущую запись при выполнении всех условий |
| `never` | `Никогда` | Не запускать автозапись и не показывать вопрос |

- Новая установка и новое подтверждённое приложение получают `ask`.
- `Записать сейчас` начинает запись немедленно; `Не записывать` подавляет
  текущую запись. С `Запомнить выбор` явные действия сохраняют соответственно
  `always` и `never`. Без галочки, а также при истечении таймера с любым
  состоянием галочки сохранённое значение не меняется.
- Галочка и оставшееся время относятся к текущему вопросу, а не к четвёртому
  значению настройки. `Для всех приложений` меняет только известные приложения;
  `Разные` вычисляется для отображения и не сохраняется как значение.
- Локальные настройки относятся к текущему пользователю Windows на устройстве,
  как локальные правила macOS; серверное пространство ими не управляет.
  Изменение видно и обратимо в настройках; оно не даёт разрешения
  записывать любое системное аудио и не блокирует разрешённый ручной Record.
- Сеть и серверное подтверждение настройки не нужны. При старте всё равно
  проверяются идентичность приложения, текущая встреча, разрешения, устройства,
  AEC3/AAC, хранилище, подавление, индикатор и Stop. Поля общей правовой политики
  и подтверждения согласия исключены из readiness по Constitution 7; отсутствие
  этих данных не блокирует старт, фиктивное согласие не создаётся.
- Старый `alwaysRecordTarget_` существовал только в памяти; прежнее модельное
  поле `user_auto_record_enabled` не означает наличие сохранённого выбора
  точного приложения. Глобальные HKCU `assisted_auto_start` и
  `prompt_before_recording` не мигрируют в `always`/`never`.
- Отсутствующее или повреждённое сохранённое значение читается как `ask`
  (`Ask`). Перед сохранением проверяется точное значение enum; неизвестные
  значения отклоняются. Ошибка сохранения явно видна пользователю и не
  подтверждает успешное изменение настройки. Проверки реализации — T082.

Основание: [spec.md, уточнение 2026-09-06](spec.md),
[research.md, решение 8](research.md#решение-8-automatic-recording-and-capture-scope),
[Constitution 7, принцип II](../../.specify/memory/constitution.md).

Жизненный цикл автоматической записи хранится только в памяти существующей
AutomaticRecordingPolicy: точная identity цели принятого старта, время последнего
положительного подтверждения, время последнего принятого снимка и начало
непрерывного подтверждённого отсутствия. PID не является ключом продолжения;
каждый учитываемый процесс отдельно проходит прежнюю проверку идентичности и
потоков. Пороги — 2 секунды свежести, 15 секунд отсутствия, 600 секунд без
положительного подтверждения. Ручной Stop/Record и завершение capture очищают
это слежение, но не меняют сохранённый выбор пользователя.

`target_key` — постоянный ID общего продуктового каталога, ASCII
`[a-z][a-z0-9_]{0,63}`. Это ключ настройки, не доказательство доверия. Точная
identity включает хеш EXE, сертификата и ревизию; membership дополнительно
сверяет её target_key. Несколько identity могут принадлежать одному продукту,
один EXE не может принадлежать разным продуктам. Название одного продукта
однозначно; настройки группируются по target_key.

Формат правил `graf.automatic-recording.v2`/HKCU `ApplicationRulesV2` сохраняет
значения по target_key без изменения при обновлении подтверждённых identity.
Неизвестные текущему каталогу ключи сохраняются для будущего восстановления,
но не разрешают неподтверждённый EXE. Дорелизный V1 не читается и не удаляется:
пустой production registry не мог сохранить реальные per-app правила; это
подтверждено кодом и отсутствием значения V1 на проверяемой Windows.

## 10. CaptureHealth and reason codes

Persist only bounded codes/counters, for example:

```text
ready
permission_denied
endpoint_missing
endpoint_invalidated
audio_service_unavailable
protected_audio_limited
unsupported_format
clock_untrusted
timestamp_discontinuity
timeline_gap_exceeded
source_overflow
aec_processor_failed
writer_failed
disk_full
playback_encoder_unavailable
webview_runtime_unavailable
```

Reason code text is product-owned and localized at the UI layer. Diagnostics may
include counts and durations, but never the content that was spoken or recorded.

## 11. Отменённый проект системных попыток (T104, 2026-09-27)

Историческое исследование, НЕ модель для реализации: пользователь 28 сентября
выбрал F277 с единственным собственным каналом. Журнал ниже не создаётся;
действующее состояние определено в contracts/f277-notifications-parity.md.

Отдельно от настроек и аудиозаписей хранится минимальный журнал схемы v1:
хешированный ключ owner/workspace/event occurrence, plannedDue, validUntil,
состояние reservation. StartsAt не входит в идентичность попытки. Сначала
устойчиво записывается запрет повторной попытки, затем будущая reservation;
сбой между записями остаётся безопасным молчанием, не повторной доставкой.
Будущая reservation допускает сверку/замену до due; после due факт попытки
не снимается по отсутствию уведомления в очереди. Идентификаторы очереди ОС
связываются с хешированным ключом; названия, ссылки, аудио и токены не хранятся
в этом журнале. Контекст ограничивает доступ и очистку системных заявок.
Повреждение/неизвестная схема не разрешают повтор; диагностика только кодом.
Журнал не является доказательством фактического показа или звука.

## 12. Защищённый custody v1 — проектирование T115, 2026-10-02

Этот раздел определяет v1 metadata и исходные flat-index objects. Поправка
больших media objects описана ниже отдельно; ошибка packed decoder не
разрешает вернуться к v1 по одному совпадению logical role.

Статус: проектирование принято, runtime ещё не принят. Нормативный wire/authority:
`contracts/windows-protected-local-custody.md`. T114/T115 завершены в своих
исследовательском/проектном объёмах; independent review112/112, storage analyze
CRITICAL=0/HIGH=0 и issue-sync PASS. T116–T118 остаются открыты.
Схемы logical v5/v3/v2 выше остаются; их physical representation меняется,
серверная таблица/role set не создаётся. Указание «directory содержит v5 файлы»
в §6 означает логический пакет; открытые physical content files не допустимы
после проверенного перехода. Historical notification §11 не внедряется.

| Сущность | Поля / отношения | Правило |
| --- | --- | --- |
| ProtectedObject | store_id,object_id,role,logical_length,index_generation | IDs opaque16B; native user-scope; decoder/role/length bounds до allocation |
| BlockVersion | position,version,exact payload bytes,digest,cipher size | immutable; index implicit position; DATA либо explicit ZERO, missing не ZERO |
| ProtectedIndex | generation,length,entries,checksum | metadata birth g1 в обоих slots до ACK; singleton после restart blocked, включая g1; refs/exact tail verified; no generation wrap |
| PinnedSnapshot | object/index identity,cursor,context epoch,lease | Clone sharing cache; owner сохраняется до callback/MF Shutdown/worker exit |
| ProtectedPackageState | strict UTF-8 schema `graf.custody.package.v1`, own IDs/generation/directory,phase,reason,short predicate,refs≤5 | live refs только capture/recovery; sealed после manifest; GC сохраняет refs обоих state slots |
| ProtectedBootstrap | strict UTF-8 schema `graf.custody.bootstrap.v1`, own IDs/generation,mode,queue ID,transaction/subject/directory или null | prepared intent до closing fence; reserved queue ID без indices допустим только initial migrating/prepared, не regular authority; protected после reconciliation; fixed location, no JSON redirects |
| ProtectedMigrationIntent | strict UTF-8 schema `graf.custody.migration.v1`, IDs/generation,subject,stage,ledger anchor,sources≤6,historical barrier ref,cleanup authorization | exact fields/enums/null/identity по contract §8.1; direct birth-block validator не требует старого mutable index; persistent roots обоих slots восстанавливаются до GC; old .quarantine durable до rename; original до authorized cleanup |
| PendingLedgerMutation | immutable candidate,ticket ID,base/target generation,context epoch,typed outcome | pending/committed/not_committed/ambiguous; network/reply/handled только ACK; physical committed adoption даже при stale UI, lease/result до actual completion |

Media checkpoint fallback даёт degraded prefix, не normal package. Любая
unreadable slot/reference authority metadata блокирует mutations/upload/unsafe
GC, чтобы прежний ledger не отменил delete intent. Сохранность неизвестных
objects не означает возможность их расшифровать при потере DPAPI profile.

New authority payloads имеют единственный строгий codec contract §8.1, не
неопределённые schema1 field lists. Unknown/duplicate/missing keys, numeric
overflow, inconsistent refs/stages/contexts отвергаются. Existing logical v5/
v3/v2 не меняются. Первое store.id допускается для verified legacy inventory
без protected traces, но никогда для восстановления потерянного encrypted ID.
Migration делает ledger source/range stamp по whole logical hash/length;
Initial prepared/fence/destination birth и cuts определены contract §8: closing
fence не является уже открытой queue. Mutable queue после switch может иметь
новые generations/ranges; migration copy receipt не отменяет current authority.
Package-state v1/v2 использует единственный JSON key версии `schema` и ровно
девять top-level fields базового §8.1. `schema_version` не является alias;
это уточнение не переименовывает поле версии существующего logical v5 manifest.
cleanup receipt не заменяет свежую проверку owner/delete rights. Все temp/
quarantine роли замкнуты §8.2; plaintext leftovers исключают encrypted claim.

Protected logical bytes/hash/ranges являются единственным представлением для
инспектора/кодера/проигрывателя/HTTP. Canonical recovery обрезает **выбранный
logical prefix в памяти**, floor(length/1920)×1920, не original artifact.
Старый plaintext reader ограничен миграцией и owner/expiry/removal gate §8
контракта; обычная отправка/прослушивание им не пользуются. Все stages/pins/
budgets требуют тестов T116–T118; принятие требований T115 не доказывает runtime.

## 13. Packed media v2 — поправка T115, 2026-10-03

Точный wire/proof: `contracts/windows-protected-packed-custody.md`.
Metadata v1/его rollback barrier остаются §12; logical v5/v3/v2 неизменны.

| Сущность | Поля / отношения | Правило |
| --- | --- | --- |
| PackedContainer | store/object/container opaque IDs, role, verified native identity, two head cells, append records | Один confined default stream и непрерывный GuardOwner; heads не atomic, DATA/nodes immutable |
| PackedRoot | generation, logical length≤64GiB, committed extent, root ref, block/radix/depth parameters | Exact protected descriptor128B; highest valid paired generation, EOF не authority |
| PackedRef | kind, envelope length, offset, version, payload length, reserved0, ciphertext SHA | Exact64B; expected path/kind/selector/context, child before parent; inline ZERO только explicit extension |
| PackedProof | full либо inherited_live, owner epoch/native identity, exact root stamp | RAM-only; меняется только проверенным base→candidate transition; любой ownership gap уничтожает proof |
| PackedSnapshot | proof/root stamp≤4KiB, independent cursor, owner pin | Clone/read/job совместно сохраняют owner до actual completion; pin≤32/process |

Новый DATA и обе heads независимо проверяются перед live ACK. Старые unchanged
bytes не reread при каждом ACK: скрытая порча обнаруживается при read либо
полном cold verify. Это явно принятое свойство, не гарантия свежей full scan.
Всё выданное DATA проходит exact context/envelope/payload checks. Read/cache
при наблюдаемой ошибке sticky failed; невозможен plaintext/default ZERO fallback.
Protected package.v2 refs и migration.v2 sources требуют explicit representation/
stamp и strict codec по packed contract §6.1 до подключения к приложению.
Служебный physical codec остаётся v1; старый payload schema1 не разрешает
packed decode. Persistent root stamps обоих metadata slots восстанавливаются
и full-verified до GC даже вне current media heads. Migration gates T117
остаются отдельными, новый field list не принимается как runtime implementation.

## T116: runtime ownership полного V5-пути — 2026-10-07

Новых persistent schemas/полей нет: package.v2/queue v3-read-v2 и typed ticket
определены существующими contracts. Private package owner удерживает настоящую
root-часть, package-state lease/accepted generation и generated member identities;
не account/effect authority. Capturing → finalizing → sealed normal/degraded
или discard pending проверяется существующим codec, с BOTH slots и exact refs.
Charged recording work удерживается native worker через capture/finalizer/queue
ACK; UI получает только values. Mutable writer имеет одного serial mutator:
dispatcher до EOS, finalizer после fence, MF calls через закрытый serial adapter
без прямого параллельного доступа. Worker очищает native refs до terminal values.
Short intent не означает removed; codec result не означает saved; stale epoch
принимает physical generation, но не account/network capability. Это design,
не утверждение о текущей реализации; допуск следующего кода проверяется отдельно.

## T116: HTTP-flight и результат очереди — 2026-10-10

Persistent schema не меняется. Construction source: `plan.md`, раздел
«T116: защищённая HTTP-отправка и принятие результата».

- Flight: charged выбранные строки/результаты≤32, captured row identity,
  store/queue context/base generation, auth epoch/cancel и busy/lease.
  Retained package inspection принадлежит network worker, не UI completion.
- Prepare: current protected value → private candidate → committed/adoption →
  current-context dispatch. Непустой flight сохраняет full candidate и при
  неизменном payload; пустой выбор не создаёт flight/commit/network.
  Display snapshot и false от domain helper не дают dispatch authority.
- Result: network terminal → проверка свежей row/epoch → private full candidate
  (server truth + status) → committed/adoption → retired. Pending и lost poll
  сохраняют result/busy; ambiguous закрывает продолжение до reconciliation.
- Protected HTTP-body: shared immutable CustodyBytes и charged control block;
  обычный string body пуст. Копирование request удерживает тот же owner, не bytes.
  Logical chunks≤256KiB не меняют wire part4MiB/clamp64KiB–16MiB.

Это конструкция перед независимым review, не наличие реализации или новое
разрешение на upload/playback/delete/публичный выпуск.
