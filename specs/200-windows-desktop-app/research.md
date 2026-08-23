# Research: Windows desktop-приложение GRAF

Дата исследования: 2026-08-23

Исследование опирается на текущую архитектуру GRAF/macOS и официальные
материалы Microsoft, доступные на дату выше. Выводы ниже — дизайн-решения для
планирования, а не утверждение о готовой Windows-реализации.

## Источники

| Источник | Проверенный факт | Решение GRAF |
|---|---|---|
| [Windows App SDK](https://learn.microsoft.com/en-us/windows/apps/windows-app-sdk/) | Microsoft называет Windows App SDK рекомендуемой платформой для новых desktop apps; stable channel предназначен для production, WinUI 3 поддерживает C++ и C# | WinUI 3 + Windows App SDK stable, C++/WinRT host |
| [Windows App SDK deployment architecture](https://learn.microsoft.com/en-us/windows/apps/windows-app-sdk/deployment-architecture) | Packaged apps зависят от Framework package; framework-dependent и unpackaged имеют разные bootstrap/deployment obligations | Выбрать packaged MSIX/MSIXBundle и не смешивать runtime bootstrap с обычным app code |
| [Packaged deployment guide](https://learn.microsoft.com/en-us/windows/apps/windows-app-sdk/deploy-packaged-apps) | Для non-Store packaged app нужно распространять framework/runtime и можно использовать Deployment API | Installer проверяет Windows App SDK dependency, signature и rollback до claim of readiness |
| [WASAPI loopback recording](https://learn.microsoft.com/en-us/windows/win32/coreaudio/loopback-recording) | Loopback читает render endpoint, работает только в shared mode; hardware Stereo Mix не обязателен; protected content может быть недоступен; event-driven loopback поддерживается с Windows 10 1703 | Default render mix через shared/event-driven WASAPI; никаких виртуальных устройств и DRM bypass |
| [IAudioClient::Initialize](https://learn.microsoft.com/en-us/windows/win32/api/audioclient/nf-audioclient-iaudioclient-initialize) | Loopback требует render endpoint + shared mode; event callback должен иметь event handle; buffers/periods должны быть согласованы; endpoint format надо проверить | Использовать `GetMixFormat`/`IsFormatSupported`, event-driven capture, bounded worker queue |
| [IAudioCaptureClient::GetBuffer](https://learn.microsoft.com/en-us/windows/win32/api/audioclient/nf-audioclient-iaudiocaptureclient-getbuffer) | Буфер может содержать 0, 1 или несколько packets; `AUDCLNT_E_DEVICE_INVALIDATED` и resource errors означают недоступность потока | Callback только вычитывает packet и публикует batch; invalidation — явный route failure |
| [IMMNotificationClient](https://learn.microsoft.com/en-us/windows/win32/api/mmdeviceapi/nn-mmdeviceapi-immnotificationclient) и [RegisterEndpointNotificationCallback](https://learn.microsoft.com/en-us/windows/win32/api/mmdeviceapi/nf-mmdeviceapi-immdeviceenumerator-registerendpointnotificationcallback) | ОС уведомляет о смене роли, состояния, свойств и существования endpoint | Endpoint changes, default-device changes и re-enumeration — first-class recovery events |
| [IAudioClock](https://learn.microsoft.com/en-us/windows/win32/api/audioclient/nn-audioclient-iaudioclock) | WASAPI exposes device position/clock for stream timing | Сохранять clock metadata и проверять монотонность; не выравнивать по callback arrival |
| [QueryPerformanceFrequency](https://learn.microsoft.com/en-us/windows/win32/api/profileapi/nf-profileapi-queryperformancefrequency) | QPC frequency fixed at boot and consistent across processors; frequency можно кэшировать | QPC — monotonic host clock для mapping и sanity checks |
| [Application loopback sample](https://learn.microsoft.com/en-us/samples/microsoft/windows-classic-samples/applicationloopbackaudio-sample/) | Process-tree loopback через `ActivateAudioInterfaceAsync` требует Windows 10 build 20348+ и возвращает тишину, если у target нет render stream | Не включать process isolation в Feature 200 baseline с Windows 10 22H2 build 19045 |
| [Secure WebView2 apps](https://learn.microsoft.com/en-us/microsoft-edge/webview2/concepts/security) | Нужно проверять origin, валидировать web messages, предпочитать JSON, избегать generic proxies/host objects, держать host non-elevated | Exact-origin route policy, versioned JSON bridge, no generic host object, standard user |
| [WebView2 distribution](https://learn.microsoft.com/en-us/microsoft-edge/webview2/concepts/distribution) и [Evergreen vs fixed](https://learn.microsoft.com/en-us/microsoft-edge/webview2/concepts/evergreen-vs-fixed-version) | Production использует WebView2 Runtime, не Edge Stable; Evergreen обновляется отдельно и runtime нужно проверить/установить | Evergreen Runtime с preflight/install/repair и bounded unavailable state |
| [Microsoft AAC encoder](https://learn.microsoft.com/en-us/windows/win32/medfound/aac-encoder) | Media Foundation encoder поддерживает AAC-LC; input PCM — 16-bit, 44.1/48 kHz, mono/stereo/5.1; output sample — compressed AAC frame | Sink Writer/Media Foundation для `meeting-review.m4a`, readiness gate для Windows N |

## Решение 1: стек

### Выбрано

- **UI/shell**: WinUI 3 на Windows App SDK stable, C++/WinRT.
- **Native host**: C++17/20-compatible C++/WinRT project, standard user
  process. UI thread не занимается capture callbacks или file I/O.
- **Web**: Microsoft WebView2 SDK + Evergreen Runtime. WebView navigates only
  to the configured GRAF HTTPS origin and existing `/desktop/...` routes.
- **Audio**: Windows Core Audio MMDevice + WASAPI shared mode, event-driven
  `IAudioClient`/`IAudioCaptureClient`, `IMMNotificationClient`, `IAudioClock`
  metadata and QPC.
- **DSP**: same pinned WebRTC AEC3 C ABI as macOS:
  `webrtc-audio-processing` v2.1, commit
  `846fe90a289f58b7c9303a635142aa2c7caa93e5`, WebRTC M131, with the same
  AEC-only configuration. Build static `.lib` per architecture; no runtime
  WebRTC/Abseil DLL.
- **Format conversion**: read each endpoint's actual mix format and normalize on
  a worker through a native Media Foundation audio resampler/channel converter,
  not on the WASAPI callback. If the converter cannot produce 48 kHz mono with
  trusted timestamps, fail the normal capture gate.
- **Artifacts**: own WAV header/writer for PCM ASR artifact; Media Foundation
  Sink Writer + Microsoft AAC-LC encoder for M4A playback artifact.
- **Local files**: `%LOCALAPPDATA%\\GRAF\\Recordings` (or the approved product
  app-data root) with user ACL, atomic temp-to-final rename, same v5 manifest and
  `desktop-upload-queue.v2` semantics as macOS.
- **Distribution**: signed MSIX/MSIXBundle, packaged Windows App SDK runtime
  dependency, Evergreen WebView2 preflight/install/repair. Release and rollback
  are separate from this planning slice.

### Почему не C# + native audio DLL

C# + WinUI 3 is viable for UI, but it adds a managed/native boundary around
capture lifetime, callbacks, pinned memory, cancellation and AEC error handling.
The first Windows implementation already needs C++ for WASAPI, Media Foundation,
tray interop and the AEC ABI. One C++/WinRT process keeps ownership and teardown
in one language and leaves a narrow JSON boundary only at WebView.

### Почему не Tauri/Electron

They would add a second desktop runtime and a second audio/permission integration
surface while the product specifically wants the server web cabinet embedded and
capture native. WebView2 already supplies the required web runtime; packaging a
second Chromium/runtime or Rust bridge adds size and lifecycle without a product
benefit.

### Почему не WPF

WPF is supported and could host WebView2, but it is an older UI foundation for a
new product shell. WinUI 3/Windows App SDK gives the supported modern desktop
surface while C++/WinRT still exposes the Win32/Core Audio APIs directly.

## Решение 2: граница native и web

```text
WinUI 3 / C++/WinRT native shell
├── Record / Pause / Resume / Stop
├── permissions and readiness
├── WASAPI render loopback + microphone
├── QPC / endpoint clock / PTS timeline
├── AEC3 / canonical mix / WAV + M4A
├── local package and upload custody
├── tray/indicator and metadata-only diagnostics
└── WebView2 host + exact-origin JSON bridge
    └── https://rec.2brain.pro/desktop/...
        cabinet navigation, settings, meetings, review, deletion report
```

The web page never receives a file path, audio buffer, bearer token, cookie,
device handle, process handle, native object or arbitrary command. The native
side does not rebuild the cabinet. A bridge event can publish bounded state such
as `capture_state`, `custody_summary` or `runtime_state`; a request can be an
allowlisted intent such as `open_native_settings`, never “run this native
method”.

The initial handshake is bound to:

1. exact normalized origin and approved route kind;
2. random per-WebView session nonce held only in memory;
3. protocol major/minor and maximum JSON payload size;
4. monotonically increasing message id and bounded acknowledgement timeout.

Navigation policy is evaluated before every main-frame and relevant frame
navigation. On auth expiry or WebView recreation, the session nonce changes and
old bridge messages become invalid.

## Решение 3: audio acquisition and format path

### Render/system source

1. Enumerate the current `eRender` endpoint for the approved role.
2. Activate `IAudioClient` on the render endpoint.
3. Open shared mode with loopback + event callback; set the event handle before
   starting; use `IAudioCaptureClient` to drain all available packets.
4. Read the endpoint's actual mix format and the packet's device/QPC positions.
5. Publish a `RecordingAudioBatch` to the bounded system-source queue and return
   immediately from the callback thread.

This captures the Windows audio engine's global mix. It does not require the
user to expose or enable `Stereo Mix`, and it does not promise app isolation. A
protected/DRM stream may be missing by platform design; the product reports that
limitation.

### Microphone source

1. Resolve the exact user-selected endpoint id or the approved default capture
   endpoint.
2. Check Windows microphone privacy and endpoint state before starting.
3. Activate an independent shared-mode event-driven capture client.
4. Publish input packets with the endpoint clock/timestamp metadata.
5. On endpoint loss, stop the trusted segment; do not transparently swap to a
   new device inside the same normal package.

### Normalization and timeline

Capture callbacks may return arbitrary packet sizes, channel layouts and device
sample rates. They do not own 10 ms framing. Each source has a worker-side
normalizer that produces 48 kHz mono float batches while carrying the source PTS
and route generation. `RecordingAudioTimeline` is the only component allowed to:

- compare timestamp domains;
- reorder within a bounded window;
- reject backward/untrusted PTS;
- account for bounded gaps and overflow;
- align system and microphone;
- emit exactly 480-sample pairs.

The timeline calls the pinned AEC3 wrapper as:

```text
ProcessReverseStream(system/reference[480])
ProcessStream(microphone/near-end[480])
cleaned microphone + unchanged system -> canonical mix
```

The existing macOS policy is retained: processor creation/configuration failure,
missing reference, untrusted route/timestamp, invalid sample or overflow cannot
be silently converted into a normal raw-microphone recording. A bounded cleaned
prefix may be finalized as degraded if the writer has enough verified output.

### Clock and drift

Use the QPC frequency captured once at process initialization and the timestamp
metadata from WASAPI packets. Keep device position and QPC observations for
sanity/diagnostic counters; keep the stream's clock domain on every batch. A
different endpoint may have a different clock domain, so the first release does
not invent a sample-rate correction from wall-clock arrival time. Drift is
handled by the bounded PTS timeline and the existing canonical conversion rules;
route/clock discontinuity ends the trusted segment when it exceeds the accepted
gap bound.

## Решение 4: artifact and local custody

The Windows writer must produce the same normal v5 package shape as macOS:

```text
recording-package/
├── manifest.json
├── meeting-transcription.wav   # PCM S16LE, 16 kHz, mono, ASR
└── meeting-review.m4a          # AAC-LC, 48 kHz, mono, playback
```

Write audio to a temporary file in the same directory, flush/close it, validate
header/byte count/hash/duration, then atomically rename. Write `manifest.json`
last through the existing atomic file-protection pattern. A package is eligible
for normal upload only after the manifest and all required artifacts pass the
same v5 integrity profile. Disk-full and finalization failures preserve what can
be proven and expose a bounded degraded state.

The queue is a Windows projection of the existing product-owned custody ledger,
not a second upload implementation. It uses the same idempotency, accepted-range,
reconciliation, retry and purge semantics. WebView auth can unblock the queue,
but the queue runner never needs the cabinet route open.

## Решение 5: permissions, power and endpoint recovery

- The packaged app declares the microphone capability appropriate for the
  Windows package, but runtime readiness still checks the user's Windows privacy
  setting and the actual endpoint. Manifest declaration is not treated as proof
  of consent.
- A visible preflight explains microphone, default output and local storage
  readiness. Record remains blocked until all required gates are true.
- Register `IMMNotificationClient` for device state, default role and property
  changes. Handle `AUDCLNT_E_DEVICE_INVALIDATED`, audio-service interruption,
  suspend/resume and output/input changes through one route-generation owner.
- On sleep/wake, re-enumerate and compare endpoint identity/format/clock before
  allowing a new capture. The first release does not splice a new endpoint into
  an existing normal timeline.
- The host is never elevated. If a future privileged operation appears, it must
  be isolated from WebView and receive a separate approved feature and security
  design; no such operation is in Feature 200.

## Решение 6: tray and persistent recording indicator

Windows has no exact macOS titlebar equivalent. Use a native, keyboard-reachable
recording strip in the shell plus a `Shell_NotifyIcon` tray item while the app is
backgrounded/minimized. The tray item has an explicit recording glyph/state,
accessible name and one-click Stop; it is not the only indication while the main
shell is visible. WebView content cannot cover or own this native surface.

The indicator must remain truthful during starting, recording, paused, degraded,
stopping and finalizing states. It must never disappear because the web page
failed, a window lost focus or a navigation changed. No setting may make active
capture invisible.

## Решение 7: WebView2 runtime and package distribution

Use the WebView2 Evergreen Runtime, not the installed Edge browser as a hidden
production dependency. The installer or first-run repair path checks the
WebView2 runtime version/architecture before creating the control. If the
runtime is missing, native capture/local custody remains usable and the shell
shows a bounded repair path.

Use a signed MSIX/MSIXBundle with Windows App SDK framework dependency and
per-user data migration. The package must preserve app identity and local data
paths across update. The release lane must test install, update, interrupted
update, rollback, uninstall retention and WebView2 repair on x64 before public
claim. ARM64 is a claim only after its own gates pass.

## Решение 8: automatic recording and capture scope

Use the existing target-scoped product policy: verified registry, one reversible
checkbox per target, `Выбрать все`/`Снять все`, eight-second prompt, immediate
start, skip and “always record this application”. Windows detector evidence must
contain exact executable identity (for example a verified signed identity or
approved stable installation identity), not only a friendly process name.

The detector is a start-policy input, not an audio routing engine. It does not
make arbitrary render-mix capture safe to start, and it never grants an unknown
process permission. Process-isolated capture is an independent future feature.

## Rejected alternatives

| Alternative | Rejection |
|---|---|
| `Stereo Mix`/hardware loopback device | Not available on all adapters, user must enable it, names vary; Microsoft recommends WASAPI loopback instead |
| Exclusive-mode capture | Conflicts with other audio apps and is explicitly incompatible with loopback |
| Virtual audio driver/kernel route | Violates current product boundary, increases install/elevation/routing risk and repeats retired macOS failure class |
| Process loopback as universal Feature 200 baseline | Build 20348+ requirement does not cover Windows 10 22H2; requires new identity/privacy semantics |
| Capture on WebView/JavaScript | Web UI cannot own local permissions, reliable system mix, local custody or one-action Stop |
| Electron/Tauri runtime | Adds a second browser/runtime or native bridge without reducing Windows Core Audio work |
| C# shell + P/Invoke audio core | Extra managed/native lifecycle boundary around real-time ownership; revisit if UI staffing outweighs safety benefit |
| FFmpeg bundled solely for AAC | Larger dependency/license/release surface when native Media Foundation AAC-LC/Sink Writer meets the required format |

## Open validation gates

1. Prove Media Foundation AAC/Sink Writer produces a playable mono 48 kHz M4A
   on every supported Windows edition, including the declared Windows N policy.
2. Build and validate the pinned AEC3 C ABI for x64 and ARM64 with reproducible
   MSVC/clang-cl toolchain metadata and all third-party notices.
3. Measure 60-minute drift, packet loss, CPU/memory and sleep/wake behavior on
   reference hardware (USB headset, Bluetooth headset, HDMI/DisplayPort audio,
   built-in mic, USB mic, dock and RDP where supported).
4. Verify packaged microphone privacy behavior in both clean install and update
   paths; no UI may claim permission merely from a manifest flag.
5. Run WebView2 origin/navigation/message fuzz cases and confirm no bridge action
   is possible after navigation/session nonce changes.
