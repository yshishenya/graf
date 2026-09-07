# Data Model: Windows desktop-приложение GRAF

Документ описывает продуктовые и межслойные сущности. Он не создаёт новую
серверную таблицу: локальная модель должна проецироваться на существующий v5
manifest и `desktop-upload-queue.v2`.

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
из `IAudioClock::GetPosition/GetFrequency` и являются проверяемой шкалой
непрерывности пакетов. `device_position_frames` сохраняется только как
монотонная наблюдаемая метка: при endpoint/engine resampling её delta может
отличаться от `source_frame_count`. `qpc_100ns` нужен для общей начальной
привязки двух источников; производная PTS не зависит от задержки callback.

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
- only `request_app_quit` and `local_recording` are accepted as requests;
  their exact payloads and current-state checks are defined in the bridge
  contract; obsolete settings/diagnostics/repair/acknowledgement aliases fail;
- web receives `native_ready` and bounded `local_recordings` display rows, never
  file paths, tokens, device handles or raw samples;
- unknown commands, stale nonce, duplicate id, oversized payload and invalid JSON
  are rejected with a bounded error and no side effect;
- no web acknowledgement is accepted or treated as proof that audio was saved,
  uploaded or removed; only local custody/server truth can establish that.

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
