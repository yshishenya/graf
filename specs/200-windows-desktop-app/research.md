# Research: Windows desktop-приложение GRAF

Дата исследования: 2026-08-23

Актуальное дополнение2026-10-03: владелец принял live incremental ACK
больших media objects с обязательным full verification после ownership gap
и более поздним обнаружением скрытой old-DATA corruption. Выбор per-record
DPAPI+SHA/packed radix64/depth3 обоснован исследованием
`checklists/research-2026-10-03-scalable-custody-proof.md` §11, без собственного
AES/DEK/nonce lifecycle. Точный нормативный кандидат —
`contracts/windows-protected-packed-custody.md`; v1 metadata остаются с full
resolver/no rollback. Это проект, не measured sustained/installed proof.

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

### Уточнение T083: первоначальное подтверждение аккаунта

Предыдущий вывод, что для неизвестного пространства нужно менять `/auth/me`,
был неполным. Действующий `cabinet/web_routes/spaces.py::list_accessible_spaces`
отдаёт JSON на `/desktop/settings/spaces`. Его `WebTenantDependency` определяет
текущее пространство сессии, а `auth/workspace_onboarding.py` помечает `active`
только для него. Контрактный тест `test_auth_contracts.py` проверяет запрос
без workspace header, единственное активное пространство и исключение
внутреннего пространства авторизации.

Решение: использовать этот read-only маршрут и затем существующий `/auth/me`
по правилам `windows-desktop-contract.md` §Local custody and upload. Ни список
устройств, ни содержимое DOM, ни первый UUID не заменяют подтверждение сессии.
Привязка отдельной установки для серверной очистки остаётся нерешённым
контрактом и в это исправление не входит.

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
side does not rebuild the cabinet. The active bridge sends `native_ready`, typed
settings/deletion replies and bounded `local_recordings` display rows with
operations/recoveryRequired; it accepts only typed `request_app_quit`,
`local_recording`, `app_appearance`, `native_settings`, `delete_selection`
and the bounded `request_app_update` intent added by the 2026-09-27 refinement
requests with command-specific route/schema/capability checks.
Capture/runtime/custody authority remains native.
The initial settings/diagnostics/repair/acknowledgement aliases and proposed
generic state messages have no active consumers and are not retained as a
compatibility surface. See `contracts/windows-native-web-bridge.md` §§3–5.

The initial handshake is bound to:

1. exact normalized origin and approved route kind;
2. random per-WebView session nonce held only in memory;
3. protocol version and maximum JSON payload size;
4. monotonically increasing web-to-native message id; no acknowledgement
   command or timeout is used as authority.

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

Use the WASAPI timestamp in fixed 100-ns units, not the raw QPC frequency.
`IAudioCaptureClient::GetBuffer` already performs that conversion. Keep device position and QPC observations for
sanity/diagnostic counters; keep the stream's clock domain on every batch. A
different endpoint may have a different clock domain, so the first release does
not invent a sample-rate correction from wall-clock arrival time. Drift is
handled by the bounded PTS timeline and the existing canonical conversion rules;
route/clock discontinuity ends the trusted segment when it exceeds the accepted
gap bound.

Проверка 2026-09-07: на текущей ARM64 VM `QueryPerformanceFrequency` равна
24 MHz; прежний Windows-код повторно делил уже преобразованную метку на эту
частоту вместо 10 MHz. [Официальный контракт GetBuffer](https://learn.microsoft.com/en-us/windows/win32/api/audioclient/nf-audioclient-iaudiocaptureclient-getbuffer)
прямо задаёт 100-нс единицы и отдельный флаг недостоверной метки.
Неверный параметр частоты удалён, `TIMESTAMP_ERROR` отвергается.
Это не исправляет автоматически общий origin, кратковременное колебание меток
и фактические `DATA_DISCONTINUITY` устройства. Их приёмка остаётся T071/T084;
ослабление порогов ради зелёного теста не допускается.

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
  of operating-system permission.
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

Уточнение 2026-09-06: действуют [Constitution 7, принцип II](../../.specify/memory/constitution.md)
и актуальная база в [spec.md](spec.md). Прежняя двоичная настройка заменена
локальным выбором для каждого подтверждённого приложения:

- `Всегда` — начать без вопроса, только после проверки всех условий записи.
- `Спрашивать` — значение новой установки и нового приложения; показать вопрос
  с восьмисекундным таймером. `Записать сейчас` начинает запись немедленно,
  `Не записывать` подавляет текущую запись, истечение таймера начинает её при
  сохранении всех условий записи.
- `Никогда` — не начинать автоматическую запись и не показывать вопрос.

`Запомнить выбор` сохраняет `Всегда` только после явного `Записать сейчас`,
а `Никогда` — только после явного `Не записывать`. Без галочки настройка не
меняется; истечение таймера не меняет её даже с галочкой. Все три значения
доступны и обратимы в настройках. `Для всех приложений` применяет выбранное
значение только к известным приложениям; `Разные` — отображение смешанных
значений, а не четвёртое сохраняемое состояние или разрешение любого звука.

Настройкой владеет только клиент. Сервер не хранит и не подтверждает эти
значения; сеть и устаревшая server-assisted policy/acknowledgement не являются
условием локально разрешённого старта. Юридическая политика пространства и
подтверждения уведомления/согласия также не являются условиями старта.
Подтверждённая текущая встреча, разрешения микрофона и
системного звука, локальное хранилище, подавление повторного старта, видимый
индикатор и Stop остаются обязательными. Удаление старого серверного контракта
не входит в этот срез и допускается только после выпуска совместимого клиента.

Решение T081/T082 после Constitution 7: удалить неиспользуемые поля legal-policy
readiness и постоянный запрет автозапуска. Новый источник «согласия», API,
диалог, настройка или фиктивная запись о согласии не нужны. Альтернатива
проставить true отклонена: она оставляет мёртвый контракт и ложную семантику.

Windows detector подтверждает точную исполняемую программу через проверенную
подпись либо утверждённую идентичность установки; одного имени процесса
недостаточно. Неизвестное приложение, музыка или обычное воспроизведение не
разрешают автозапуск. Детектор выбирает момент старта, но не изолирует звук:
WASAPI loopback сохраняет общий микс выбранного устройства вывода. Изоляция
звука процесса остаётся отдельной будущей фичей.

Совместимость уточнена в spec.md 2026-09-06: старый `alwaysRecordTarget_`
существовал только в памяти, а прежнее поле `user_auto_record_enabled` в модели
не доказывает существование сохранённой настройки для точного приложения.
Глобальные HKCU `assisted_auto_start`/`prompt_before_recording` не переносятся
в `Всегда`/`Никогда`. Отсутствующее или повреждённое локальное значение даёт
`Спрашивать` (`Ask`). Перед сохранением принимаются только точные три значения
enum; ошибка сохранения показывается явно и не считается успешной сменой
правила. Требование определено; его реализация и проверка остаются в T082.

### Фоновый запуск и срок автоматической записи (2026-09-06)

Mac `TwoBrainRecApp.swift` отслеживает активное приложение по bundle ID, а не
по одному PID; `stopStaleMeetingDetectionRecordingIfNeeded` завершает запись
после 600 секунд без подтверждения встречи. Windows сохраняет своё точное
сопоставление подписанного EXE/сертификата/версии реестра, но разрешает смену
PID в пределах той же проверенной идентичности. Имя процесса не заменяет
проверку. Порог 15 секунд подтверждённого отсутствия и свежесть 2 секунды
сохраняются; 600 секунд ограничивают потерю наблюдения, которая раньше могла
оставлять запись активной неограниченно. Всё время — монотонное.

Существующий `AutomaticRecordingPolicy` владеет этим состоянием с принятого
native `starting`, а не с поздней публикации `recording`. Новая служба,
контроллер, таймер и сохраняемая схема не нужны. Ручная запись не отслеживается.
Существующий CompactOverlay создаётся скрытым при старте GRAF, его Stop
подготовлен; видимость главного окна не является условием готовности. Перед
захватом отдельно проверяется фактический показ индикатора и доступность Stop.

Независимое исследование каталога: bundled macOS JSON и миграция сервера
0030 совпадают, версия `2026.07.21.1`, всего 85 ID; записей Windows и заполненных
`windowsProcessNames` нет. API реестра уже существует, но не содержит пар
SHA-256 EXE/DER сертификата для Windows. Установленный пакет MSTeams сам по
себе такой парой не является. Проверенные Windows-записи, стабильный ключ
продукта для сохранения Never при обновлении и положительная приёмка встреч
остаются в T082; синтетические тестовые хеши не попадают в рабочий каталог.

### Постоянные настройки и первый Windows-каталог (2026-09-06)

Mac хранит выбор по постоянному `targetID`. Windows V1 связывал его с хешами
EXE/сертификата/ревизией: одобренное обновление теряло даже `Никогда`.
Разделены постоянный `targetKey` для настроек и точный `identityKey` для
обнаружения, вопроса и срока записи. Членство в каталоге проверяет также
targetKey; совпадение только имени/ключа не подтверждает программу.

Новый отдельный HKCU `ApplicationRulesV2` с заголовком
`graf.automatic-recording.v2` хранит три режима по стабильному ключу.
V1 и глобальные флаги не читаются и не удаляются: до этого AppMain создавал
пустой verifiedTargets_, а setPreference/setAllPreferences отвергали цели вне
каталога. Поэтому реальные правила через UI сохранить было нельзя. Проверка
пользовательской Windows также вернула `V1RulesPresent=False`. Миграционный
reader не нужен; V2 сохраняет правила временно отсутствующих продуктов.

Первая запись использует общий ключ `microsoft_teams_new` из
`apps/macos/RecApp/Resources/meeting-target-registry-baseline.json`.
Проверено установленное приложение, без входа/встречи/захвата:

| Метаданные | Проверенное значение |
|---|---|
| Package / version | MSTeams / 26213.1006.5014.9784 |
| Architecture / family | ARM64 / MSTeams_8wekyb3d8bbwe |
| Manifest Application Id / EXE | MSTeams / ms-teams.exe |
| Product / signer | Microsoft Teams / Microsoft Corporation |
| Get-AuthenticodeSignature | Valid |
| EXE SHA-256 | `d2538d0290c463a896e2710534b5e078066d4c9519e3111754186f7f38fe2dd4` |
| Signer DER SHA-256 | `c4514cb03fff0842be711ecfec8560be9cc5fc7dbd1f7db95c68257ff77aae2f` |

### Вторая запись каталога: Yandex Telemost (2026-09-18)

Владелец попросил поставить в машину Microsoft Teams и Яндекс Телемост, чтобы
живая проверка автозаписи стала возможной. Teams в машине уже стоял — ровно та
сборка, что записана выше. Телемост поставили: установщик `TelemostSetup.exe`
(подпись `CN=YANDEX LLC`, `Valid`) скачивает полезную нагрузку
`YTelemostSetup.msi` и проверяет её по собственной опубликованной сумме; на Mac
файл скачан целиком (233 881 600 байт) и сумма совпала с той, что назвал
установщик. MSI поставлен молча, приложение работает.

Вторая запись берёт постоянный ключ из общего продуктового каталога
(`apps/macos/RecApp/Resources/meeting-target-registry-baseline.json`, запись
`yandex_telemost`, `prompt_enabled`, рынок `russia`). Точные хеши подтверждены
метаданными установки и проверкой Windows:

| Метаданные | Проверенное значение |
|---|---|
| Продукт / версия | Yandex Telemost / 2.42.4.9707 |
| Путь / размер | `C:\Program Files\Yandex\YandexTelemost\YandexTelemost.exe` / 144 480 792 |
| Издатель / подпись | YANDEX LLC / `Get-AuthenticodeSignature` = Valid |
| EXE SHA-256 | `fa3c6ff3a0f0d8f4d1e39ea79988f0926747d75c6351da0a0727aca0fb0f4249` |
| Signer DER SHA-256 | `8d24d59ad5240de240bb7d6b474c717d78a7155edd4cf347a047d5a2e8f0bf49` |

Запись, как и первая, привязана к точной сборке: другая версия или другая
архитектура требуют собственной проверенной записи и сами в каталог не попадают.

После обычного запуска уже установленного Teams существующий native
`AutomaticRecordingSmokeTests --inspect-process` подтвердил те же два хеша
через WindowsTargetDetector/WinVerifyTrust (проверка подписи и цепочки из кеша).
Manifest выбирался по Id MSTeams: второй entry использует тот же EXE.
Каталог не включает ms-teamsupdate.exe/autostarter или неподтверждённые версии.
Это точная идентичность одного ARM64-пакета, не доказательство встречи,
поддержки всех Teams, GRAF ARM64 либо физического x64-компьютера.

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

Any future process-isolated capture feature must separately specify how the user
selects and verifies the target process identity, whether child processes are in
scope, applicable Windows privacy/permission controls, protected-audio behavior,
data minimization and fallback. Here “privacy” means technical user/system
control and data scope; it does not mean participant legal notice or consent and
does not reinstate either as an app-enforced recording prerequisite. This future
gate neither authorizes process loopback work nor changes Feature 200's shared-
loopback-only baseline.

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

## T085: единицы WASAPI и особенности начала потока (2026-09-07)

[Актуальный GetBuffer](https://learn.microsoft.com/en-us/windows/win32/api/audioclient/nf-audioclient-iaudiocaptureclient-getbuffer)
определяет QPC100ns для первого кадра пакета, а device position — как число
аудиокадров от начала потока. Он не даёт отдельного правила пересчёта этой
позиции при внутреннем преобразовании частоты endpoint/engine.
[GetFrequency](https://learn.microsoft.com/en-us/windows/win32/api/audioclient/nf-audioclient-iaudioclock-getfrequency)
относится к IAudioClock.GetPosition, не к GetBuffer: измеренные 384000
нельзя считать частотой семплов пакетного счётчика.
[DeviceFormat](https://learn.microsoft.com/en-us/windows/win32/coreaudio/pkey-audioengine-deviceformat)
описывает поток engine ↔ endpoint. Для
[IAudioClock2.GetDevicePosition](https://learn.microsoft.com/en-us/windows/win32/api/audioclient/nf-audioclient-iaudioclock2-getdeviceposition)
различие аппаратной/mix частоты оговорено прямо, но это другой API и
текущая позиция, не timestamp первого семпла полученного пакета.

В ВМ подтверждены mic DeviceFormat44100 / GetMixFormat48000 и сочетание
device delta448 с пакетами487/488. Это согласуется с преобразованием
448 × 48000/44100 ≈ 487.62, но не разрешает автоматически переписать
единицы счётчика. Открытие shared DeviceFormat44100 даёт S_FALSE у
IsFormatSupported: запасной путь без изменения Windows-настроек не принят.
Render также имеет выходящие за текущий допуск колебания QPC после старта.
Точные метаданные и границы опыта — validation-2026-09-06.md.

В [официальной исторической документации Microsoft](https://github.com/MicrosoftDocs/sdk-api/blob/51e75730951a2cf9dea1fd96e7e062d57161fa6b/sdk-api-src/content/audioclient/nf-audioclient-iaudiocaptureclient-getbuffer.md#L81)
первый DATA_DISCONTINUITY после Start назван неопределённым;
[оговорка удалена 13.06.2019](https://github.com/MicrosoftDocs/sdk-api/commit/60b1f9ec4dfce32f30dfe9a74c33c642dd137aae),
причина не указана. [Chromium](https://github.com/chromium/chromium/blob/5b50c26e08d6f46f0f47ec548ef0fa0815e2a719/media/audio/win/audio_low_latency_input_win.cc#L1424-L1485)
и [cubeb](https://github.com/mozilla/cubeb/blob/dc56ea41279c1089eb9064d15fcebdefc5d9feca/src/cubeb_wasapi.cpp#L1197-L1213)
сохраняют особое отношение к первому флагу. Chromium считает ожидаемую
позицию через devicePosition + frameCount для учёта сбоев; это не доказательство
обязательного строгого равенства с остановкой на каждом устройстве.

Решение продолжения T085: **ограниченная подготовка, не гарантия Windows**.
Контракт §5 уточнён: отбросить только первый
непустой пакет с ровно флагом0x1, без чтения данных/продвижения аудиосостояния,
с проверенным ReleaseBuffer(count), отдельным учётом и прежним таймаутом.
Первый чистый пакет расходует это исключение, второй разрыв/смешанные флаги
и дальнейшие ошибки часов остаются отказом; переинициализация внутри записи
его не открывает заново. Основание — историческая документация и существующая
практика Chromium/cubeb, при сохранении наблюдаемого учёта и всех следующих
проверок. Альтернативы: прежний безусловный отказ блокирует подготовку;
пропуск произвольных флагов/неограниченный прогрев скрывает потери и отклонён.
До кода обязательны независимый review уточнения и регрессии. Даже это
решение не устраняет несовпадение счётчиков
микрофона и последующие отклонения render в нынешней ВМ.

Результат реализации: новая безопасная сводка самого GRAF подтвердила
стартовое отбрасывание и последующие render `clock_drift` / microphone
`sample_count_mismatch`. Тихий сценарий тоже отказал на микрофоне до deadline.
Это локализует проверки, но не доказывает единственную первопричину драйвера.

Дополнительный read-only запрос по
[IsFormatSupported](https://learn.microsoft.com/en-us/windows/win32/api/audioclient/nf-audioclient-iaudioclient-isformatsupported)
уточнил S_FALSE: для DeviceFormat44100 предложен closest 48000/stereo/32-bit
IEEE float, повторная проверка полного неизменённого дескриптора дала S_OK
без нового closest. Первоначальный дескриптор44100 от этого не становится
поддерживаемым. Предложенный формат номинально совпадает с текущим потоком;
он не является доказанным исправлением. Изменять ОС или автоматически
пересчитывать devicePosition по этому результату нельзя. См. также
[WAVEFORMATEXTENSIBLE](https://learn.microsoft.com/en-us/windows/win32/api/mmreg/ns-mmreg-waveformatextensible):
четыре сводных поля не заменяют полного описания формата. Подробное evidence
и границы настоящего испытания — последний раздел validation-2026-09-06.md.

Новое read-only измерение вызвало `IAudioClock::GetPosition` на каждом
полученном пакете. Для render с `frames=480` clock delta был `3840` при
frequency `384000`; для microphone с `frames=487/488` clock delta был
`3896/3904` при той же frequency. Это даёт ровно engine sample rate
`clockDelta * 48000 / 384000` и объясняет `devicePosition` delta `448`.
Поэтому минимальная правка использует уже существующий WASAPI audio clock
для packet continuity, сохраняя исходный device position для монотонности.
Перебирать форматы, менять настройки Windows или ослаблять count gates не
требуется.

### Пересмотр гипотезы часов и границы будущего routing (2026-09-26)

Предыдущее наблюдение VM не доказывает, что текущее показание IAudioClock —
позиция начала конкретного GetBuffer-пакета. Действующее правило в контракте §5
требует packet QPC и отдельную проверку непрерывности; гипотеза выше не даёт
разрешения синтезировать метки по frameCount или отключать drift gates.
Несовместимость устройства требует диагностики и открытого T094, не выдачи normal.

Process loopback остаётся вне F200. До отдельной спецификации должны быть явно
решены: техническое разрешение пользователя и видимый Stop; точная identity
целевого приложения; включение/исключение дочерних процессов и смена PID;
поведение защищённого/DRM звука без обхода; fallback при недоступности API,
отказе target и потере разрешения. F200 не разрешает молчаливый переход между
process-only и global capture; fallback и disclosure требуют отдельной приёмки.
Это перечень будущих вопросов, не юридические prerequisites и не реализация
process loopback, драйвера или скрытой записи в текущей фиче.

## Адресные платформенные подписи — 2026-09-27

Decision: один `GRAFDesktopPlatform` в доверенном Windows bootstrap, конечный
набор служебных ключей в общем cabinet.js и адресные атрибуты только на
элементах служебного текста. Поздний bootstrap вызывает идемпотентное обновление;
ранний читается при обычной инициализации. HTMX использует существующий цикл.
Текст динамического удаления выбирается до соединения с названием записи.
`canOpenSystemSettings` — отдельная возможность ответа уведомлений, false в
Windows; отсутствие поля у старого Mac сохраняет прежнее поведение после
успешного подключения. Признак платформы не является проверкой безопасности.

Rationale: независимое чтение `NativeSettingsBridge.cpp`, bootstrap host,
cabinet.js и шаблонов подтвердило отсутствие общего маркера ОС и опасный обход
всего body. `data-surface-mode` различает web/embedded, `window.webkit` используется
обоими клиентами. Ни один из них не доказывает macOS. Решение поддерживает старый
Mac без нового бинарного клиента и не затрагивает данные встречи.

Alternatives rejected: расширять string replacements/TreeWalker; определять ОС
по User-Agent или наличию webkit; отдельные страницы Windows; глобальный
MutationObserver; менять подпись устройства другого компьютера по текущей ОС.
Старый Windows с TreeWalker требует обновления приложения: сервер не способен
отменить уже исполняемый сторонний сценарий замены гарантированно.

## Системные напоминания и обновления (2026-09-27)

Часть о системных напоминаниях отменена решением пользователя 28 сентября:
фактический GRAF Dev F277 `51bcff6b…` удалил оба прежних канала в пользу одной
собственной карточки. Ниже сохранено основание предыдущего исследования,
НЕ указание реализовывать Scheduler. Решение T112 об обновлениях сохраняется.

T104 использует `Windows.UI.Notifications` ScheduledToastNotification и
ToastNotifier.AddToSchedule; локальная ранняя карточка остаётся отдельной.
ОС хранит расписание независимо от процесса. Её пятиминутное окно доставки
не гарантирует показ после длительного выключения; передача запроса не
является подтверждением показа. [Microsoft: scheduled notifications](https://learn.microsoft.com/en-us/windows/apps/develop/notifications/app-notifications/app-notifications-scheduled).
Нужны ExpirationTime, системная отмена, устойчивый журнал, безопасная активация
с повторной проверкой и нативная проверка подавления на границе записи.
Собственный второй таймер не удовлетворяет работе после выхода из приложения.

T112 использует системный PackageManager и зарегистрированный App Installer.
Из-за документированной ошибки не вызывается CheckUpdateAvailabilityAsync
непосредственно у Package.Current; пакет получают FindPackageForUser.
Unknown не равен NoUpdates. [Microsoft: проверка обновления пакета](https://learn.microsoft.com/en-us/uwp/api/windows.applicationmodel.package.checkupdateavailabilityasync?view=winrt-26100).
Наличие API не доказывает работу XML на минимальной ОС, доверие содержимому
канала, успешную подпись или сохранность при принудительном завершении.
Эти условия остаются отдельными тестами T112/T063/T071; публичный канал
не утверждён и не публикуется в рамках этой реализации.

## Фактический эталон F277 (2026-09-28)

Вместо догадки по master проверен GRAFSourceSHA работающего GRAF Dev:
`51bcff6b1abfdf2a01d59a7d3f00c831674c365c`. Пользователь явно выбрал его.
Прочитаны spec, два notification contracts, data-model и код этого git object.
F277 меняет канал, сроки, геометрию, quiet, историю и notification protocolv2.
Контракт переноса вынесен в `contracts/f277-notifications-parity.md`.
Системный планировщик и журнал отвергнуты как уже устаревшие относительно цели,
а не из-за недостатка Windows API. Одна карточка переиспользует текущих владельцев
Shell/модели; нет нового UI runtime, сервера календаря и фоновой службы.
Синхронизация с незавершённой чужой веткой выполняется по точному эталону и
проверкам, а не автоматическим merge. Production deploy по-прежнему отдельно.

## Windows-захват: повторная сверка открытого кода — 2026-09-30

Read-only исследование T094. Ранее изученные Chromium/cubeb найдены в T085;
поиск OpenViking вернул timeout и не использован как доказательство. Прочитаны
реальные публичные исходники, без переноса стороннего кода в приложение:

- [Chromium](https://github.com/chromium/chromium/blob/5b50c26e08d6f46f0f47ec548ef0fa0815e2a719/media/audio/win/audio_low_latency_input_win.cc#L1370-L1530)
  отдельно учитывает потерянные кадры через ожидаемую device position и ошибки
  времени, имеет timestamp fallback. В этом участке нет нашего немедленного
  отказа по формуле 100 ppm + 1 ms + frame.
- [cubeb](https://github.com/mozilla/cubeb/blob/dc56ea41279c1089eb9064d15fcebdefc5d9feca/src/cubeb_wasapi.cpp#L1136-L1268)
  накапливает frames, QPC использует для input latency и явно игнорирует
  DATA_DISCONTINUITY. Последнее не переносится в GRAF.
- [OBS](https://github.com/obsproject/obs-studio/blob/2c4e446a2201d5ef66b8909190f7f15afe092ace/plugins/win-wasapi/win-wasapi.cpp#L995-L1087)
  для обычного capture выбирает device timestamp либо время обработки минус
  длительность пакета. ProcessOutput — другой путь, вне F200.
- [Meetily stream.rs](https://github.com/Zackriya-Solutions/meetily/blob/a2cb62e827da7ef59f65064c97233efb2313878e/frontend/src-tauri/src/audio/stream.rs#L244-L309)
  принимает данные CPAL, но не использует InputCallbackInfo. Cargo.lock этого
  снимка закрепляет CPAL 0.15.3; его
  [WASAPI backend](https://github.com/RustAudio/cpal/blob/v0.15.3/src/host/wasapi/stream.rs#L379-L438)
  запрашивает QPC, но не device position. Это не доказательство нашего alignment.

[Microsoft QPC virtualization](https://learn.microsoft.com/en-us/windows/win32/sysinfo/acquiring-high-resolution-time-stamps#virtualization)
ожидает надёжность счётчика в корректном hypervisor. Сам факт VM не доказывает
поломку QPC. По
[GetBuffer](https://learn.microsoft.com/en-us/windows/win32/api/audioclient/nf-audioclient-iaudiocaptureclient-getbuffer)
метка относится к первому кадру пакета, а
[GetPosition](https://learn.microsoft.com/en-us/windows/win32/api/audioclient/nf-audioclient-iaudioclock-getposition)
— к текущей позиции. Заменять одно другим нельзя.

Schema6 пользователя: после startup кадры непрерывны, на packet60 (stats59)
packet QPC error = 12707 × 100 ns = 1.2707 ms; текущая граница = 1.0789604 ms.
Это превышение timestamp budget, не доказанный dropout: probe не читает звук.
VM/виртуальный endpoint остаётся гипотезой причины колебаний. AudioNormalizer
переносит QPC residual в ptsFrames, RecordingAudioTimeline ограничивает поправку
48 кадрами. Поэтому увеличение только mapper budget не исправляет весь путь.
Кандидат решения — раздельная оценка packet custody, кратковременной
неопределённости меток и устойчивого drift с bounded alignment двух источников.
Модель ещё не принята: нужны уточнение контракта §5, plan/checklist/analyze,
регрессии потерь/повторов/скачков/drift и живая приёмка. Это НЕ разрешение на
fake timestamps, wall-clock padding, сброс epoch или raw-mic fallback.

## Пробел локального хранения RQ30-H1 — 2026-09-30

Независимый review выявил: PRD требует encrypted local buffers, F057 FR-043 —
encrypted custody artifacts, а F200 FR-012 описывает ACL/atomic write; запись
T083 говорит, что буферы не шифруются. Это не одобренное исключение. Поиск
Windows-кода не нашёл шифрования custody: AtomicFileStore пишет bytes в
ofstream и применяет ACL; V5LocalRecordingWriter пишет временный canonical
float и использует Media Foundation URL writer. Шифрование тома в этом раунде
не проверялось. Нужны явные требования к сохраняемым media/temporary/key paths,
план защиты без admin/сети/новых пользовательских препятствий, сохранность
существующих записей и проверки restart/upload/playback/purge. Механизм не
выбран; считать ACL шифрованием или отменять baseline нельзя. Общий gate открыт.

### RQ30-H1: исследование нативной защиты — 2026-09-30

**Решение на этапе исследования:** FR-012 явно наследует шифрование F057
FR-043 и PRD; исключение для Windows не вводится. Предварительно осуществимый
путь — пользовательская защита ключа DPAPI и ограниченные независимо
аутентифицированные блоки CNG. Это кандидат, не завершённый формат или
разрешение реализации: Phase 0 остаётся открытой.

**Обоснование:** независимый исследователь проверил все активные пути:
`V5LocalRecordingWriter` создаёт открытый canonical float, WAV и M4A;
`AtomicFileStore` пишет открытые bytes и устанавливает ACL после записи;
`LocalRecordingPackage`, queue и WinHTTP читают файлы напрямую, а локальный
playback передаёт путь внешнему проигрывателю. Защита одного AtomicFileStore
не закрывает этот поток. Требуются защищённые временные/окончательные media,
manifest, recovery, queue registry, quarantine и их atomic temporary версии.
Конкретные объекты и регрессии должны попасть в data model/contract/tasks
после выбора и независимой проверки механизма, не только в FR.

**Альтернативы:** EFS прозрачен файловым readers, но не доступен на Windows
Home; включение BitLocker/FileVault/полного шифрования диска не является
условием обычного запуска. DPAPI целого media-файла требует целого DATA_BLOB
и не закрывает часовой захват с ограниченной памятью. DPAPI-NG streaming
не предоставляет автоматически произвольные seek/rewrite v5/MP4. Для
пользовательского DPAPI используются null prompt и UI_FORBIDDEN, не
LOCAL_MACHINE; ключ не передаётся в WebView/сеть/диагностику.

**Не разрешённые технические вопросы:** writable/seekable IMFByteStream для
AAC/MP4; безопасное изменение блока без повторного nonce с тем же ключом;
восстановление после частичной перезаписи/сбоя и ограниченность индекса;
playback без открытого временного файла/внешнего ShellExecute; миграция старых
plaintext packages/registry без перекодирования или потери UUID, исходных
v5 bytes, hashes, accepted ranges и delete intent. Распознанная повреждённая
зашифрованная оболочка не должна переходить в legacy plaintext reader.
Recovery зависит от сохранённого профиля/ключей Windows: переустановка ОС
или потеря ключей не получает обещания восстановления. Корзина сохраняет
восстановимость владельцу; шифрование не доказывает cryptographic erasure
старых копий, backup или остатков носителя.

Дополнительный подтверждённый риск SC-003: `Sha256.cpp::sha256File` загружает
целый файл в строку, а digest создаёт дополнительный полный vector. Часовой
mono float 48 kHz — 691200000 bytes (~659 MiB), ещё без этих копий. Нужен
инкрементальный хеш логических расшифрованных bytes с ограниченным буфером;
проверки маленьких fixtures не подтверждают предел роста памяти 128 MiB.

Первичные источники:
[CryptProtectData](https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptprotectdata),
[EncryptFileW](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-encryptfilew),
[CNG streaming](https://learn.microsoft.com/en-us/windows/win32/api/ncryptprotect/nf-ncryptprotect-ncryptstreamopentoprotect),
[BCrypt authenticated cipher info](https://learn.microsoft.com/en-us/windows/win32/api/bcrypt/ns-bcrypt-bcrypt_authenticated_cipher_mode_info),
[MP4 seekable byte stream](https://learn.microsoft.com/en-us/windows/win32/api/mfidl/nf-mfidl-mfcreatempeg4mediasink).
RQ30-H1 не закрыт: доступность API и дополнение FR не доказывают реализацию.

### T094: одиночная ошибка метки и downstream — 2026-09-30

Синтетическая проверка связывает настоящий `ClockMapper`, `AudioNormalizer`
и `RecordingAudioTimeline` из dirty worktree, без VM/микрофона/чтения звука.
На 58 идеальных интервалах по 480 frames при 48 kHz и одиночной ошибке
пакетного QPC +1.2707 ms текущий mapper закономерно даёт sticky clockDrift:
ошибка превышает бюджет 1.0789604 ms. Если только в изолированном стенде
обойти этот отказ, normalizer переносит ошибку в PTS и timeline отклоняет
скачок 61 frame при пределе коррекции 48. Идеальные интервалы проходят;
пропуск одного frame отдельно отвергается. Это не воспроизведение полного
аппаратного trace: пользовательская schema6 содержит лишь пять checkpoints.

**Решение:** увеличивать только порог mapper нельзя — это оставляет отказ
ниже по потоку. Нужны совместимые оценки packet timestamp uncertainty,
устойчивого дрейфа и двух исходных шкал, с сохранением независимой проверки
device/count/flags. Действующий численный контракт §5 пока не меняется;
новая модель не выбрана и приёмка записи не заявляется. Для проверки влияния
эмуляции подготовлены x64 и native ARM64 diagnostics из одного исходника;
это сравнение probe, не объявление ARM64-продукта поддерживаемым.

### RQ30-H1: проверка нативного stream adapter — 2026-09-30

**Выбрана API-граница, не формат хранения:** для Media Foundation использовать
штатный `MFCreateMFByteStreamOnStream` поверх seekable `IStream`, вместо своей
полной реализации IMFByteStream или открытого temporary media URL. Writer
принимает null URL + stream + явный MPEG4 container attribute; reader принимает
byte stream без URL. Это уменьшает будущий адаптер, но IStream всё равно должен
реализовать ограниченные logical read/write/seek/size и безопасное хранение.

Самостоятельный Windows x64 research fixture вне git
`f200-storage-stream-proof.b5wKeF/StreamProof.cpp` прошёл с exit0. Нативный
кодировщик получил 100 искусственных блоков 480 mono PCM16 при 48 kHz,
сохранил M4A в SHCreateMemStream (12929 bytes). Случайный 32-byte ключ защищён
пользовательским DPAPI с null prompt/UI_FORBIDDEN и восстановлен в том же
процессе/профиле. CNG AES-GCM восстановил исходные bytes; подмена ciphertext,
tag и block-identity AAD отдельно отклонена. Повторно восстановленные bytes
через новый IStream/byte stream декодированы до EOS: 96256 PCM bytes.
128 лишних PCM samples — наблюдаемое ограничение этого секундного fixture,
не основание менять duration/hash/delivery продуктового v5-контракта.

**Границы доказательства:** ни устройство, ни звук пользователя, ни сеть, ни
media-файл не использовались. Весь маленький искусственный fixture находился
в памяти; целый memory stream НЕ является проектом часового хранения. Нативный
кодек не воспроизводил звук. Не проверены защита ciphertext на диске, partial
write/rewrite/crash, уникальность nonce всего жизненного цикла, произвольные
логические диапазоны, другой пользователь/профиль, restart, Home/Windows10 и
реальный playback. CLI runner имеет Administrator role=True: этот запуск
не доказывает работу приложения без повышения прав. Раздельные DPAPI/CNG/MF
вызовы не означают, что будущий file-backed IStream уже защищает MP4 при записи.

**Следующие нерешённые вопросы:** формат и атомарный commit защищённых блоков,
key/nonce lifecycle при seek/rewrite, целостность logical length/index и предел
его памяти, безопасное восстановление/совместимый переход старых пакетов,
встроенное воспроизведение. Общий Phase0/review gate остаётся NOT READY.

Первичные источники:
[IStream adapter](https://learn.microsoft.com/en-us/windows/win32/api/mfidl/nf-mfidl-mfcreatemfbytestreamonstream),
[Sink Writer byte stream/container](https://learn.microsoft.com/en-us/windows/win32/api/mfreadwrite/nf-mfreadwrite-mfcreatesinkwriterfromurl),
[Source Reader from stream](https://learn.microsoft.com/en-us/windows/win32/api/mfreadwrite/nf-mfreadwrite-mfcreatesourcereaderfrombytestream),
[native memory stream](https://learn.microsoft.com/en-us/windows/win32/api/shlwapi/nf-shlwapi-shcreatememstream),
[native symmetric key lifetime](https://learn.microsoft.com/en-us/windows/win32/api/bcrypt/nf-bcrypt-bcryptgeneratesymmetrickey).

### RQ30-H1: bounded DPAPI blocks и переключение версии — 2026-09-30

**Более простой криптографический кандидат:** защищать каждый ограниченный
блок пользовательским DPAPI, вместо DPAPI только для ключа + собственного
управления AES-GCM ключом/nonce для перезаписи. Это не DPAPI целого часового
media: logical reader читает нужные блоки и выдаёт исходный диапазон. DPAPI
создаёт собственные session keys; приложение не сохраняет свой открытый ключ
или счётчик nonce. Формат/размер блока окончательно не выбран, код продукта
не изменён. CNG остаётся нативным инкрементальным SHA256, не самописным crypto.

**Важное уточнение целостности:** Microsoft CryptUnprotectData прямо допускает
при повреждении разные ошибки и в отдельных случаях успешный возврат с
повреждённым результатом; рекомендует дополнительную проверку приложения.
Поэтому TRUE недостаточен. Research envelope проверяет ожидаемые context
(schema/file identity/block index/generation), точную bounded length и SHA256
контекста/полезных bytes до их выдачи. Контекст также передан как optional
entropy. Выдача повреждённого результата как plaintext/fallback запрещена.
Это fixture-проверка, не security review будущего постоянного формата.

Нативный x64 BlockProof прошёл exit0: на каждом размере 12 encrypt/decrypt
round trips, отдельно шесть отказов (подмена ciphertext, усечение, другой
block index, другое generation, неверная ожидаемая длина, искусственно
повреждённый decoded envelope при успешном пути API). Все bytes искусственные,
media/устройства/сеть не использовались. Измерение после одного warmup:

| Payload | Cipher bytes | Protect mean/max, µs | Unprotect mean/max, µs |
| --- | --- | --- | --- |
| 65536 | 65830 | 5492 / 6430 | 5059 / 5592 |
| 262144 | 262438 | 20295 / 30808 | 21143 / 53442 |
| 1048576 | 1048870 | 76957 / 92806 | 73950 / 97597 |

Это wall-time в Parallels x64 emulation, не CPU-time SC003, не file IO и не
standard-user/Home/Windows10 proof. В том же runner ранее подтверждён admin
role=True. Замеры не разрешают новый размер очереди или ослабление Stop:
нужно измерить combined crypto/index/flush и существующий 256-item dispatcher
с двумя EOS/5s drain. Native writer finalization уже вынесен в существующую
packaged_task/future (`AppMain.cpp:995–1027`); новый сервис/очередь не нужны.

**Кандидат persistence layout из независимого исследования:** каталог каждого
logical artifact, immutable block versions и два alternating protected
index slots, без БД, журнала или head file. Seek/rewrite создаёт новую версию
затронутых блоков. Старый активный индекс не заменяется; новая версия
публикуется только в неактивный слот после проверенных записей/сбросов блоков
и временного индекса. Оба слота и их block references защищаются от очистки.
После публикации с неудачным barrier результат indeterminate: остановить
изменения/cleanup, перечитать оба слота; не объявлять normal saved.

Recovery проверяет только два bounded slots, layout/integrity/все обязательные
blocks и выбирает наибольшее пригодное generation. Temp index не считается
commit. Возврат к старой версии означает явное ограниченное recovery, а не
полное normal output. Missing block не превращается в нули; явное расширение
seekable файла требует определённых защищённых zero ranges. Восстановление
не защищает от намеренного rollback всего хранилища к старой корректной копии.

Append-only single container уменьшает число файлов, но оставляет мусор от
rewrite и требует безопасной compaction/двойного дискового резерва; in-place
encrypted rewrite отвергнут из-за уничтожения прежнего блока при partial write.
Directory layout пока предпочтителен только как следующий проверяемый протокол,
не как доказанный итоговый формат/производительность. Index ограничивает
logical bytes/block count/entry size до allocation. Disk budget учитывает оба
слота, pinned readers, dirty group и остатки сбоев; cleanup bounded и не гоняется
с writer/recovery. После финализации logical artifact неизменяем.

**Новые конкретные пробелы текущих helpers:** AtomicFileStore использует
ofstream/trunc, ACL после записи, нет CREATE_NEW и FlushFileBuffers, а
canonical path check не закрепляет открытые объекты от подмены/reparse/hardlink.
MOVEFILE_WRITE_THROUGH не доказывает весь требуемый порядок durability.
Результат storageWritable сейчас означает непустой путь. Нужны DACL при
создании, native handle/volume/identity guards, удержание trusted directories,
write/close/flush/replace/barrier errors и различение process crash/power loss.
Нельзя требовать admin/volume flush. Существующий AppInstance единственного
приложения и scheduler lease сначала используются и проверяются, не создаётся
новый lock service. `discardShortRecording` сейчас разрешает только regular
files непосредственно в пакете: вложенные блоки требуют согласованного purge
контракта. Общий recycle-bin путь уже проверяет вложенное дерево, но это не
доказательство новых ownership/hardlink/race guards.

Первичные источники:
[CryptUnprotectData integrity caveat](https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptunprotectdata),
[FlushFileBuffers](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-flushfilebuffers),
[MoveFileExW](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-movefileexw).
Следующий шаг Phase0 — Windows file-backed immutable-version/commit/recovery
fixture с искусственными bytes и отказами каждого этапа. Последний сохранённый
commit при отключении питания, безопасность путей, полный resource budget и
встроенный playback остаются непроверенными; RQ30-H1 не закрывается замерами.

### RQ30-H1: file-backed commit/recovery fixture — 2026-09-30

**Результат исследования:** отдельный x64 CommitProof проверил предложенный
порядок immutable block → temporary protected index → inactive slot на
Windows-local fixed NTFS. Исходник вне git: `f200-dpapi-commit-proof.9xdyLi`,
CPP SHA-256 `ced3982c08668428390f32983b1e7a374f9aec1fedbdfa928290af1de1d9b387`;
он повторно использует crypto/envelope функции BlockProof из раунда118, а не
создаёт ещё одну реализацию. EXE SHA-256
`3cc539dd67d84f0f283c78576a55fb2229f66577e3c3420c7c6aac0df61858fc`.
Строгая сборка /W4 /WX exit0. Два исполнения exit0/stderr0; второе после
проверки точного EXE hash, с 30s parent watchdog и 10s на каждого своего child.

Только искусственный 64KiB payload. Диск выбран через GetTempPath и проверен
как fixed NTFS, не общая папка `C:\Mac`. Новый случайный каталог; существующие
GRAF custody/записи не открывались. CREATE_NEW и защищённая DACL текущему
пользователю/SYSTEM перед записью, checked WriteFile/FlushFileBuffers/CloseHandle,
MoveFileEx в другой index slot, повторный checked flush опубликованного файла.
Открытые файлы проверяются по handle: regular file, no reparse, один hardlink;
directory handle удерживается без FILE_SHARE_DELETE. Это проверка своего
пустого каталога, не доказательство всей adversarial-path модели. DACL проверка
fixture ограничена protected-bit и двумя ACE, не полным сопоставлением SID/mask.

| Точка принудительного ExitProcess(77) дочернего writer | Выбранное generation |
| --- | --- |
| Половина нового encrypted block после flush | 1 |
| Полный новый block после flush | 1 |
| Половина temporary encrypted index после flush | 1 |
| Полный temporary index после flush | 1 |
| Inactive slot опубликован | 2 |
| Опубликованный slot повторно flush/close | 2 |
| Без сбоя | 2 |

На каждом случае исходный generation1 предварительно восстановлен. Temp index
не принимается за commit; незавершённый block не нужен прежнему индексу.
Дополнительно generation3 заменяет неактивный slot, не generation2. Подмена
block3 приводит к generation2 с одним invalid slot, то есть только к явному
ограниченному восстановлению. Усечение оставшегося index приводит к generation0
с двумя invalid slots, не пустому успешному ledger. CREATE_NEW collision
отклоняется во всех семи случаях; исходный block1 не перезаписывается.

**Границы:** child ExitProcess не равен отключению питания; незакрытые handles
закрывает ОС, disk cache не пропадает. Не проверены реальное failed/partial IO,
indeterminate post-publish barrier, low disk, несколько blocks и seek/rewrite,
GC/readers/migration, путь всех metadata/media, реальная очередь/Stop/60min,
размер index на час, memory/CPU, стандартный пользователь/другие профили/Home,
adversarial parent/namespace/races и встроенное воспроизведение. Файлы fixture
сохранены в его собственных временных каталогах; открытый звук не записывался.
Это поддерживает выбранный порядок для следующего проектирования, но не
завершает Phase0 и не разрешает внедрять формат в рабочие записи.

Нативные источники:
[CreateFileW: CREATE_NEW, security attributes и sharing](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew),
[ReplaceFileW: WRITE_THROUGH flag не поддерживается](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-replacefilew).

### T094: same-source native ARM64 результат — 2026-09-30

Присланный пользователем schema6 сверён с stdout живого PID2956:
`f200-arch-comparison.gJ8bq3/arm64/PacketProbe.exe`, PE ARM64 и SHA-256
`3b4128c5cc633cf460eaf9f8bea457b80c43332d4f107193ae4510c447d9e6b1`.
GRAF отсутствовал. Это один завершённый metadata-only запуск по явному Start,
не проверка звука/SC003. 65 packets/31200 frames/released65, startup480,
единственный startup discontinuity, release/timestamp errors0. Stats64,
gaps min/max/residual0; clockDrift на native packet12 (stats11), valid10.

| Stats checkpoint | Packet QPC error, ms | Current clock error, ms | Paired span shift, ms |
| --- | --- | --- | --- |
| 2 | -0.0601 | -10.0000 | -9.9399 |
| 8 | -0.0788 | -8.2058 | -8.1270 |
| 11 (первая ошибка) | +1.1438 | +3.8313 | +2.6875 |
| 32 | +1.8970 | -8.0315 | -9.9285 |
| 64 | +2.2090 | -7.4771 | -9.6861 |

На пяти точках `clockError - packetError - pairShift = 0` в единицах100ns:
относительные position spans совпадают после деления на свои частоты. Это
результат только экспортированных точек, не гарантия поведения между ними.
Текущие часы не являются более устойчивым готовым timestamp первого кадра.
На stats11 device span4800frames=100ms, ошибка packet1.1438ms превышает
действующий budget1.0309477ms. End-to-end источник отклонения по одному такому
короткому наблюдению не установлен: cadence/QPC/virtual endpoint/host scheduling
ещё не разделены. Max service17.148ms и hold34µs — агрегаты до первого fault,
не временная трасса его причины; отсутствие timestamp flag не доказывает
точность1ms. Native GetPosition/GetBuffer возвращают разные позиции/корреляции.

**Изменение следующего действия:** сбой существует в native ARM64, поэтому
нельзя считать x64 emulation его единственной необходимой причиной. Влияние
Parallels/виртуальных устройств остаётся гипотезой. После окончания/checked
release/Stop ARM64 process закрыт, затем открыт один x64 GUI из тех же исходников
и с предварительно проверенным EXE hash; Start ожидается отдельно, результат
пока не получен. Контролируемое сравнение двух архитектур ещё не завершено.
Никакая архитектура продукта не добавлялась.

Синтетическая изоляция actual mapper/normalizer/timeline дополнена именно
fault checkpoint stats11: идеальные предыдущие пакеты, ошибка1.1438ms,
sticky clock rejection PASS, потеря одного кадра отвергается. Counterfactual
mapper-only bypass даёт55frames и штатный timeline rejection (>48). Это не
полный replay аппаратной трассы: предыдущие64 timestamps не экспортированы.
На новом CPP `c6b918256b47e3debba80b5c100596e326eaa1e7d2f42cf3c8b9f9903002d799`
оба исторический и новый isolation cases PASS; продукт/§5 не изменены.
План остаётся: coherent clock model через всю цепочку, не увеличение одного
threshold и не замена PTS callback/wall-clock/current-clock timestamp.

### RQ30-H1: выбранные решения Phase0 для ProtectedLogicalFile — 2026-09-30

**Decision:** native user-scope DPAPI на ограниченные объекты, каталог каждого
logical artifact с immutable block versions и двумя alternating protected
indices; 256KiB payload block. CNG SHA256 проверяет decoded envelope.
**Rationale:** штатные offline/profile keys без своего AES key/nonce lifecycle;
256KiB уменьшает число файлов/индекс вчетверо против64KiB при измеренном
protect/unprotect≈20/21ms, не задержке1MiB объекта. Это выбор для дизайна,
не доказательство общей disk/index/queue скорости. **Alternatives:** EFS не
покрывает Home; AES-GCM+DPAPI key добавляет nonce lifecycle; append-only container
требует compaction; in-place rewrite разрушает прежний checkpoint.

Выбранные исходные bounds (не результаты runtime memory proof):

| Ресурс | Предел |
| --- | --- |
| Logical artifact | 64GiB; 262144block positions, exact ceil без overflow addition |
| Index entry | 16B: block version u64, cipher length u32, flags u32; index implicit |
| Plain index | Header/envelope≤4096 + count×16; максимум4198400B |
| Cipher block / index | Payload+4096 / plain-index-bound+64KiB; checked до чтения и после API |
| Plain block caches | До2MiB суммарно на процесс, не на каждый IStream Clone |
| Dirty rewrite group | До4blocks/1MiB, одна группа без очереди следующих групп |
| Layer-owned buffers | Cap64MiB, резервирование до allocation; внутренние DPAPI/MF не объявлены измеренными |
| GC pass | До64objects, без списка всего каталога в памяти |

64GiB — предел представления, не серверная квота/длительность и не разрешение
выделять его на диске. Он выше canonical boundary25769803554B из текущего RIFF
u32 limit и отношения192000/32000. Поэтому предложение исследователя16GiB
не принято как новый предел writer. Час canonical691200000B требует2637blocks/
index46288B; 4h2764800000B —10547/172848; 24h16588800000B —63282/1016608.
Коррекция вывода исследователя: DesktopHttpTransport.cpp:175 допускает24h
только в локальном parser, сервер config.py:238/ingest policy ограничивает4h.
Это найденное расхождение, не право заявлять server acceptance24h; эти лимиты
не менялись. Проверка общих product limits нужна до закрытия паритета.

Block version и index generation различаются: незатронутые blocks переиспользуются.
Protected envelope связывает schema/type/file identity/index/version/exact length
и digest; wire fields явно little-endian, не ABI memcpy. Explicit ZERO допустим
только для заданного расширения файла; missing/corrupt object никогда не ZERO.
Sequential writer публикует каждый полный256KiB block, Flush/Pause/Stop также
короткий хвост. 4blocks — максимум seek/rewrite группы, не ожидание5.46s для
обычной записи. При продвижении canonical cadence≈1.365s; это не wall-time
гарантия при зависшем IO. Recovery принимает только complete480-frame groups
в durable checkpoint; Write-accepted bytes не равны durable prefix. Любой
storage отказ завершает normal acceptance, не увеличивает256batches/2EOS/5s drain.

Commit сохраняет порядок round119; indeterminate post-publish error блокирует
writes/GC. Оба slots/readers/current group удерживают свои objects; unreadable
slot запрещает GC его неизвестных ссылок. Disk reserve считается по фактическим
cipher sizes+candidate index+orphan/pinned/legacy copies и PRD quota/reserve,
не считается гарантированным по одному GetDiskFreeSpace. Finalized snapshot
immutable; manifest последний после WAV/M4A. Streaming logical hash/ranges
сохраняют v5 bytes, не используют whole-file allocation. Existing LocalMetadataScan
и open-validation background path уже существуют — новый scanner service не нужен.

**Playback API выбран для дизайна:** IStream→IMFByteStream→native Media Engine
IMFMediaEngineEx::SetSourceFromByteStream; MF_MEDIA_ENGINE_AUDIOONLY — flag
CreateInstance (не attribute), IMFMediaEngineNotify callback обязателен.
Нейтральный resource label не раскрывает private path/token, не разрешает
external resource resolve. Нет ShellExecute через plaintext temp. Native
Pause/Resume/Seek/Stop и close/account/delete/shutdown fences используют один
pinned snapshot. Это API-интеграция по документации, ещё не runtime playback proof.

Legacy migration копирует один файл streaming, проверяет exact hash/length и
validated commit до переключения; original и durable intent сохраняются.
Без re-encode/new UUID/сброса accepted ranges. Два slots не являются transaction
всего package/ledger: точный intent/authority/order требует Phase1. Legacy/
oversized/key-loss copies не обрезаются/не удаляются автоматически; до безопасной
очистки originals весь old inventory не называется encrypted. DPAPI profile
loss не выдаётся за восстановление; plaintext fallback запрещён.

Bounds fixture `/tmp/graf-f200-storage-bounds.dMZocV/check.cpp`, SHA-256
`278566e785580d3c37b1200f14cd9e89007fafb9bc7671d1285995a43fe93aea`,
ASan/UBSan/Wall/Wextra/Wpedantic/Werror build0/run0: empty/partial/full/max
dimensions, UINT64/offset/count overflow, truncated/extra index, flags/ZERO,
cipher length. Только design arithmetic, не parser/crypto/storage acceptance.
Coherent clock model пока неизвестна; exact wire/envelope и package migration
contract требуют Phase1 после Phase0. Combined IO/resources, power-loss,
standard-user/Home и playback — обязательные будущие проверки реализации.
Общий Phase0/review NOT READY; production code не менялся.

Первичные источники:
[SetSourceFromByteStream](https://learn.microsoft.com/en-us/windows/win32/api/mfmediaengine/nf-mfmediaengine-imfmediaengineex-setsourcefrombytestream),
[CreateInstance audio-only and callback](https://learn.microsoft.com/en-us/windows/win32/api/mfmediaengine/nf-mfmediaengine-imfmediaengineclassfactory-createinstance),
[native create flags](https://learn.microsoft.com/en-us/windows/win32/api/mfmediaengine/ne-mfmediaengine-mf_media_engine_createflags).

### T094: проверка различимости дрейфа и ошибки меток — 2026-09-30

**Решение:** дальнейшая модель должна отдельно проверять custody кадров и
согласованность временной шкалы; один residual от первого пакета не является
измерением устойчивого изменения частоты. Для исследования выбран проверяемый
интервальный критерий совместимости меток с частотой/фазой, а не clamp результата
или перезапуск origin. Производственная модель PTS пока не выбрана: совместимость
одной частоты не означает, что она установлена, или что двухисточниковый AEC
получит достаточно точное выравнивание. Phase0 остаётся открытой.

**Обоснование:** синтетический стенд использует модель
`q(t)=phase+t*(1+e)+noise`, `abs(noise)<=J`. Для заданного постоянного `e` каждая
метка ограничивает phase интервалом `[q-t*(1+e)-J, q-t*(1+e)+J]`; пустое
пересечение отвергает гипотезу. Все точки учитываются без сброса окна/накопленной
границы. Это модель исследования, не гарантия постоянной частоты реального
устройства на протяжении всей записи и не алгоритм допуска аудио.

Оценка частоты по концам интервала имеет неопределённость `2J/T`. Две гипотезы
с разными неизвестными phase и собственным ограниченным noise гарантированно
различимы только при `abs(e1-e2)*T>4J`. При равенстве множества ещё соприкасаются.
Независимо известный точный phase даёт другую границу `>2J`, но первая измеренная
метка WASAPI не является таким точным внешним эталоном. Независимый исследователь
подтвердил различие этих трёх случаев. Это вывод из модели, не утверждение Microsoft.

В стенде **гипотетический** J=3ms: один и тот же полный искусственный ряд
совместим с 100 и 200ppm до120s включительно; после120s эти две гипотезы
различимы. Без шума несовместимость 200ppm с 100ppm появляется раньше — после60s.
Это не обоснование нового лимита3ms и не обещание, что120s любой настоящей
диагностики установят частоту. Пять экспортированных ARM64 checkpoints совместимы
с номинальной частотой при этом предположении; допустимая phase ширина3.7122ms
сама по себе не доказывает нынешнюю точность1ms/48frames. Неэкспортированные
пакеты, предел noise, последующая частота и относительная шкала render/mic
из этого не восстанавливаются.

**Проверено:** standalone C++17/ASan/UBSan/Wall/Wextra/Wpedantic/Werror, без VM,
устройств/PCM/сети: идеальный час, одиночная ошибка1.1438ms, alternating±3ms,
границы±100ppm; неоднозначность120s и исключение сразу за границей; phase step7ms,
sticky rejection и границы арифметики. Настоящий ClockMapper отдельно сохраняет
отказ при потере/повторе одного кадра и ошибочных flags. Файл вне git:
`/tmp/graf-f200-clock-feasibility.yvkwK5/check.cpp`, SHA-256
`3b54380d082bfb858446424f14a4be3de000a2304442726f91f6cd28dc3d6f32`.

**Отвергнутые альтернативы:** выдавать единственную подогнанную частоту за
подтверждённую; принять clamp/smoothing как исправление потерь; расширить только
порог mapper; заменить время первого кадра текущим clock/временем callback;
назвать ARM64 или VM единственной доказанной причиной. Следующий аппаратный
вопрос — долговременные диапазоны ошибки меток и совместимость обеих исходных
шкал. Численные правила §5/SC003, product mapper/normalizer/timeline не менялись.

Повторно сверенные первичные источники: Microsoft
[GetBuffer: время первого кадра](https://learn.microsoft.com/en-us/windows/win32/api/audioclient/nf-audioclient-iaudiocaptureclient-getbuffer),
[GetPosition: текущая позиция и S_FALSE](https://learn.microsoft.com/en-us/windows/win32/api/audioclient/nf-audioclient-iaudioclock-getposition),
[GetFrequency: номинальная частота не учитывает drift/jitter](https://learn.microsoft.com/en-us/windows/win32/api/audioclient/nf-audioclient-iaudioclock-getfrequency).

### T094: phase-only smoothing не является исправлением — 2026-09-30

**Решение:** отвергнут путь «сгладить пакетный QPC и оставить коррекцию семплов
существующей timeline». Следующая модель должна согласовывать оценку частоты с
непрерывной фазой resampler, а не лечить шум меток многократным trim/interpolate.
Это выбор направления, не готовый численный контракт или допуск нового mapper.

**Доказательство:** изолированный одноэкспоненциальный phase filter с временем
0.32s и гипотетической погрешностью±3ms на метку связан с настоящими
`AudioNormalizer`/`RecordingAudioTimeline`. Счётчик кадров проверяется независимо,
origin не сбрасывается. Четыре искусственных60s случая — 0/0 и+100/−100ppm,
постоянные/переменные пакеты, разные sinusoidal ошибки меток — проходят без
timeline fault:6000/5999 blocks. Это ещё не качество записи.

Контрпример10s: два одинаковых1kHz тона, идеальные реальные часы, различается
только искусственная ошибка меток. Timeline остаётся healthy, изменение RMS
render всего−0.000899928dB, но максимальная ошибка относительно исходной волны
и рассогласование двух одинаковых источников достигают0.5 при амплитуде0.25;
trimmed render frames1415. Так проверка уровня≤1dB и отсутствие fault могут
пропустить полную ошибку фазы. Это counterfactual prototype, не утверждение
о таких ошибках текущего GRAF или настоящем AEC. Рабочий GRAF ещё раньше
прекратил бы этот поток по неизменённому mapper budget.

Проверены sticky отказ при+200ppm (packet6021/60.21s в конкретном noiseless
стенде), loss/repeat одного кадра и скачок метки. Диагностический J3ms, предел
разности6ms и alpha не принимаются за production bounds. PCM — только
сгенерированные constant/tone samples; процессор passthrough, не pinned AEC.
Standalone C++17/O2/ASan/UBSan/Wall/Wextra/Wpedantic/Werror build0/run0:
`/tmp/graf-f200-clock-filter.vAEmXa/check.cpp`, SHA-256
`9ef5c4cd01d4c2fc6092c72af973b764cb31ea9eda23b425d4fb32f1d7890683`.

**Первичные образцы:** Chromium
[SnooperNode](https://github.com/chromium/chromium/blob/ab6b23fbaa30f59c1f7b7c984e4f4247aea6d2a8/services/audio/snooper_node.cc#L237-L318)
корректирует ratio resampler, не только output timestamp. Его zero-fill/drop/
seek/prime-silence пути не подходят для GRAF и не копируются. Это playback
node, не готовое доказательство capture integrity WASAPI.
[GStreamer slave methods](https://gstreamer.freedesktop.org/documentation/audio/gstaudiobasesrc.html#GstAudioBaseSrcSlaveMethod)
также разделяют resample, retimestamp и изменение capture pointer; библиотека
не добавляется. WebRTC
[CoreAudioInput](https://webrtc.googlesource.com/src/+/d2c106be9c34f71b756e45b2b7fd9e97f553a549/modules/audio_device/win/core_audio_input_win.cc#318)
использует packetQPC для latency estimate, а flags ошибок пишет как warning;
этот relaxed integrity путь не переносится в GRAF. Никакой сторонний код
или новая dependency в продукт не внесены. Phase0/§5/SC003 остаются открытыми.

### T094: последовательные metadata-only опыты x64 и ARM64 — 2026-09-30

**Решение:** исключить зависимость исследовательского опыта от ненадёжного
ручного ввода Parallels. В собственной утилите вне git добавлен строгий
`--metadata-once-48000`: тот же worker, видимый индикатор и Stop, один опыт,
5s deadline/750ms отмена, без чтения PCM. Без аргументов сохраняется ручной
Start; неизвестные аргументы отклоняются до COM/микрофона. Это CLI собственного
кода, не имитация GUI input и не доказательство приёмки интерфейса GRAF.

Две сборки одного источника, x64 и native ARM64, выполнены последовательно.
Обе дали exit0, Stop S_OK, освобождение каждого полученного пакета и отсутствие
остаточного процесса. x64:31 packets/14880frames/352ms,21 valid; clock_drift
на packet23, затем DATA_DISCONTINUITY на packet31. ARM64:7 packets/3360frames/
91ms,5 valid; DATA_DISCONTINUITY на packet7. До flag обе серии имеют нулевые
frame gaps; x64 checkpoint22 показывает packet-time residual1.2869ms.
Нулевой счётчик разрывов кадров не позволяет игнорировать аппаратный flag.

**Вывод и ограничения:** проблема не требует x64 эмуляции для возникновения.
Эти короткие неравные серии не сравнивают производительность архитектур,
не устанавливают Parallels/driver как единственную причину, не доказывают
качество/непрерывность звука. Автоматический сбор metadata теперь доступен
без пользовательского клика; основная запись и установленный MSIX не менялись.
Не копируется relaxed обработка flags из других продуктов; mapper threshold
не расширяется. Дальнейший кандидат должен согласовывать непрерывную фазу
преобразователя частоты и временную шкалу, а отдельно сохранять строгие
frame/flag/ReleaseBuffer/EOS проверки. См. round124 validation для точных
источников, хешей и отказа первой версии оболочки запуска.

### T094/T096: reuse преобразователя и исключение до ReleaseBuffer — 2026-09-30

Независимый исследователь проверил exact pinned WebRTC
`846fe90a289f58b7c9303a635142aa2c7caa93e5`: direct
[SincResampler API](https://github.com/okarlsen/webrtc-audio-processing/blob/846fe90a289f58b7c9303a635142aa2c7caa93e5/webrtc/common_audio/resampler/sinc_resampler.h)
поддерживает SetRatio без сброса fractional source phase; вызовы serial с
Resample. Он входит в уже linked libcommon_audio.a, новая dependency не нужна.
PushSincResampler фиксирует ratio/request sizes; старый discrete Resampler
не подходит. Vendor в этом worktree не доступен; local symbols/compiled reuse
не проверены. Это API-level reuse choice, не выбранная production clock модель.

Минимальный кандидат использует одну оценку `q=a+b*n+noise` и для source phase,
и для input/output ratio. PTS/normalizedFrameOffset продвигаются по выданным
семплам, реальная source phase не сбрасывается; phase correction действует
через непрерывный ratio, не независимый timeline trim. Correction horizon,
slew/phase uncertainty не определены и не заменяются прежними toy constants.
Совместимость clock/count/flags остаётся отдельным проверяемым gate. Вывод:
нужны true-time waveform для двух источников, partition-invariant output,
startup/partial-request/EOS accounting. Pinned sinc имеет zero startup history
и не имеет partial EOS drain; его callback padding нельзя молча принять за
полученный звук. Границы должны быть согласованы с §5 до внедрения.

Отдельно main-agent воспроизвёл T096 exception custody gap настоящего
`WasapiCaptureWorker::consumePacket`: искусственный отказ только1920B
выделения `batch.samples.resize(480)` выбрасывает bad_alloc до release callback.
Однопоточный portable стенд с generated zero array, actual worker/mapper/
normalizer/enumerator, ASan/UBSan/strict C++17 сообщает
`ALLOCATION_FAULT_REPRODUCED=1 RELEASE_CALLS=0 CUSTODY_ACCEPTED=0`.
Память системы не исчерпывалась, устройств/PCM/network не использовано.
Это реальная uncovered failure branch, а не объяснение аппаратного clock_drift.
Минимальное исправление должно гарантировать ровно один ReleaseBuffer после
успешного acquisition при исключении до copy/release, сохранить release error
как приоритетную причину и не вызвать normalizer/callback/writer. Сам product
пока не менялся; regression и review относятся к существующей T096, не дублирующей
фиче. Источник/хеши стенда в round124 validation.

### T094/T096: результат узкого исправления и MMCSS — 2026-10-01

Round125 восстановил existing release гарантию: catch только samples allocation,
checked release с приоритетом releaseFailed и false до normalize/callback.
Native std::function заранее построена до Start/GetBuffer; новая модель/API не
добавлена. RED→GREEN actual worker, macOS/Windows32/32 и ASan/UBSan1/1;
independent post-implementation review привязан к двум source hashes. Полная
T096 и clock/storage Phase0 остаются открытыми.

Отдельный disposable metadata-only x64 опыт зарегистрировал Audio thread через
[AvSetMmThreadCharacteristicsW](https://learn.microsoft.com/en-us/windows/win32/api/avrt/nf-avrt-avsetmmthreadcharacteristicsw)
и выполнил
[AvRevertMmThreadCharacteristics](https://learn.microsoft.com/en-us/windows/win32/api/avrt/nf-avrt-avrevertmmthreadcharacteristics)
на том же worker после Stop/COM cleanup. Registration/revert успешны, но
получен sample_count_mismatch packet9: frame gap−11 при65/65release, без
timestamp-error flags. Наблюдение отвергает достаточность одной регистрации,
не доказывает отсутствие её пользы или VM/driver sole cause. В приложение не
переносились MMCSS/buffer/новые thresholds. Подробности и hashes —
validation-2026-10-01.md; ни этот опыт, ни custody fix не принимают живой звук.

### T094/T095: compiled continuous-ratio waveform и граница EOS — 2026-10-01

**Decision:** сохранить direct pinned SincResampler как подтверждённый
исследовательский путь непрерывного ratio без новой зависимости. Не переносить
его в production до количественного clock estimator/uncertainty contract и
полного start/partial-EOS решения. Phase0 остаётся открытой.

**Rationale:** round126 впервые использует настоящий verified x64 artifact,
не копию алгоритма. Семь generated60s вариантов с реальным RecordingAudioTimeline
проверяют waveform, два источника44.1/48k, известные±100ppm, start offset,
разные input request sizes и output partitions, изменения ratio20/40s.
На одном опубликованном интервале fixed/variable output побитно одинаковы;
ошибка волны<0.000021, межисточниковая разница<0.000023. Negative с nominal
ratio здоров по timeline и RMS, но waveform mismatch≈0.39: длительности и
уровня недостаточно. Это oracle эксперимент, не clock estimator из метаданных.
Числа допустимой ошибки в собственном стенде не задают новых рабочих порогов.

**Startup/EOS:** из actual layout следует support
`[floor(x)-16,floor(x)+15]` для центра x. Zero-history начала нельзя выдавать
как полученный звук. Callback требует полный request R, R>48; после полной
загрузки C=R*floor(N/R) безопасный префикс API имеет16≤x<C−16.
Неполный хвост никогда не дополняется нулями. Два runnable edge cases R64/N100
и N128 подтвердили недоступность соответственно37 и1 математически пригодных
центров без ещё одного полного callback. Зеркало bounded local cursor нужно
проверять с тем же порядком floating-point операций; глобальная сумма ratio
не является точным публичным getter. Это дальнейшая интеграционная задача,
не объявленное отсутствие потерь полного EOS.

**Alternatives considered:** nominal ratio при независимом timestamp shift
отвергнут waveform negative; phase-only фильтр уже отвергнут round123;
callback zero-padding/Flush на смене ratio/игнорирование flags не допустимы.
Собственная новая resampler library не нужна. Частота/phase по oracle не
выдаётся за выбранный causal estimator, проверка generated prefix — за AEC,
AAC, WASAPI, device recovery или полноценный аппаратный тест.

Primary source pin:
[SincResampler API](https://github.com/okarlsen/webrtc-audio-processing/blob/846fe90a289f58b7c9303a635142aa2c7caa93e5/webrtc/common_audio/resampler/sinc_resampler.h),
[layout/SetRatio/Resample](https://github.com/okarlsen/webrtc-audio-processing/blob/846fe90a289f58b7c9303a635142aa2c7caa93e5/webrtc/common_audio/resampler/sinc_resampler.cc).
Exact source/artifact hashes, commands, counters and limitations находятся в
validation-2026-10-01.md, round126; production artifacts/tasks не изменились.

### T114 / RQ30-H1: совместный DPAPI/file-backed/MF опыт — 2026-10-01

**Decision:** сохранить выбранный native DPAPI + immutable256KiB blocks +
два protected indexes как исследовательский кандидат. Совместимость seekable
IStream → IMFByteStream с AAC encoder и SourceReader теперь проверена на
Windows, но Phase0 ещё не завершена; production формат не принят.

**Rationale:** один disposable стенд переиспользует прежние native DPAPI,
decoded-envelope CNG hash, DACL-before-write и checked file barriers. Он пишет
только ciphertext на Windows-local NTFS, а Media Foundation получает null URL
и logical byte stream. Искусственные3840123 canonical bytes после закрытия
совпадают в64 диапазонах и после исправления стенда проверены целиком, включая
короткий хвост;30s generated silent PCM кодируются в366529 logical
M4A bytes, декодируются до EOS, затем SourceReader переходит к10s и обратно1s.
Повторное открытие/декодирование/оба seek в отдельном процессе завершаются0.
Это не native MediaEngine playback и не испытание звуковых устройств.

17 собственных canonical и6 media files проверены по DPAPI и ожидаемой
context/digest envelope до намеренного повреждения. Corrupted tail заставляет
восстановить явно ограниченное предыдущее поколение3670016B с invalid-slot1
и полным совпадением его искусственных bytes;
повреждение второго index отвергает открытие. Это исследовательский fallback,
не разрешение выдавать усечённую запись/пустой ledger за обычный успех.
Проверка охватывает только собственный каталог стенда, не все возможные
внутренние файлы Windows/MF, pagefile, crash dumps или весь диск.

Фактический restricted same-user medium запуск не принят: дочерний процесс
создаётся, но завершает инициализацию с0xc0000142 без результата теста.
Причина не установлена; это не доказательство несовместимости DPAPI с обычным
пользователем. UAC, системные desktop DACL, профили и службы не менялись.
Отдельная standard-user account/Home/установленная сборка остаются непроверенными.

**Alternatives considered:** plaintext media URL/temporary decode copy не
используются. Новый crypto key lifecycle/библиотека не нужны для этого опыта.
Изолированный DPAPI benchmark и memory-only MF stream сами по себе не
доказывали совместный путь; теперь этот узкий пробел закрыт проверкой, не
вся T114. Fixture имеет64MiB cap, один256KiB cache и index≤256entries;
SetSize допускает только неизменную длину, Clone/CopyTo не реализованы,
GC отсутствует. Измеренный private-memory delta не является peak/bound.
Нет power-loss, большого index, failure injection всех publish barriers,
ключа другого профиля, pinned-reader lifecycle, dispatcher5s fence,
MediaEngine playback или полной аппаратной приёмки. T114 остаётся открытой.
Exact sources/artifacts/commands и числа — validation round133.

Первичные источники:
[IStream adapter](https://learn.microsoft.com/en-us/windows/win32/api/mfidl/nf-mfidl-mfcreatemfbytestreamonstream),
[sink writer existing stream](https://learn.microsoft.com/en-us/windows/win32/api/mfreadwrite/nf-mfreadwrite-mfcreatesinkwriterfromurl),
[restricted token](https://learn.microsoft.com/en-us/windows/win32/api/securitybaseapi/nf-securitybaseapi-createrestrictedtoken),
[same-user restricted process](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-createprocessasuserw).

### T114 / RQ30-H1: исправление medium launcher и совместный опыт — 2026-10-01

**Decision:** ошибка0xc0000142 предыдущего restricted launcher не принимается
за требование administrator/несовместимость DPAPI. Исправлена только модель
проверочного запуска: native SetEntriesInAclW добавляет право текущего TokenUser
в DefaultDacl нового временного restricted token перед CreateProcessAsUser.
Существующие ACE сохраняются; исходный token, учётная запись, UAC, системные
desktop/file DACL и приложение не меняются. Новый crypto/storage механизм не нужен.

**Rationale:** read-only native context показывает medium8192/noadmin,
доступ к проверенным минимальным операциям WinSta0/desktop, valid pipe stdin,
но DefaultDacl без user allow ACE и с admin allow ACE. На одном exact x64
EXE контроль без user grant завершает child с0xc0000142; добавление только
user grant даёт child0 с внутренней проверкой medium/noadmin. Ранний одинаковый
minimal source в x64 и native ARM64 падает одинаково, без MF/storage операций.
Это контролируемая причина отказа этого launcher, не объяснение аудиочасов
и не доказательство любых прав на desktop по одному минимальному mask.

Затем неизменённые ProtectedMfProof source141b…/EXE60cc… проходят весь
round133 generated-data опыт через исправленный launcher в actual medium
nonadmin процессе: полные canonical/fallback bytes, DPAPI envelopes, AAC,
reopen/decode/SourceReader seek и отдельный child reopen. Новый собственный
native Job Object удерживает только дерево этого опыта; не меняет глобальные
правила и не даёт продуктовой гарантии dispatcher drain. Подробные hashes,
контроли, counts и ограничения — validation round134.

**Alternatives considered:** не менялись UAC, системные desktop ACL, профиль,
частоты, audio flags или clock thresholds; native ARM64 не выбрана как новая
архитектура приложения. Standard-user account/Home/installed app, native
MediaEngine playback, big-index/peak/resource и power-loss/migration/fences
остаются непроверенными. Закрыт узкий пробел restricted-process proof,
не T114/Phase0 и не полная FR-012. Optional after_plan hook пока не исполняется.

### T114 / RQ30-H1: native MediaEngine playback и повреждение — 2026-10-01

**Decision:** продолжить исследование существующего protected IStream через
штатный MFCreateMFByteStreamOnStream → IMFMediaEngineEx::SetSourceFromByteStream.
Audio-only MediaEngine не требует отдельного проигрывателя, открытого media URL
или plaintext temporary copy. Это выбранный исследовательский путь, ещё не
принятый продуктовый контракт и не замена действующего ShellExecute в GRAF.

**Rationale:** disposable стенд на generated silence прошёл внутри actual
same-user restricted medium/noadmin процесса: загрузка 30s AAC, движение времени,
пауза со стабильной позицией, переходы на10s/1s/конец, два продолжения, событие
ENDED после перехода к хвосту, Shutdown16ms и MF_E_SHUTDOWN при новом Play.
Все шесть собственных файлов проверены как DPAPI envelopes до и после positive
опыта. На тех же exact bytes отдельный fresh fixture с повреждённым первым
блоком после validated reopen вызвал native ERROR0x8003001e; контроль IStream
подтвердил sticky read fault без выдачи байтов. Shutdown и запрет нового Play
прошли также при повреждении. Exact hashes/receipts/ограничения — round135.

**Alternatives considered:** не добавлялись codec/crypto библиотека, shell
player, новый пароль или открытая дисковая копия. Callback содержит только
атомарные счётчики и ошибки; существующие DPAPI/storage helpers переиспользованы.
Ввод устройств и рабочие записи не использованы; заглушённый audio-only engine
может открыть выход Windows, поэтому это не `devices=false`. Это не полные30s
непрерывного прослушивания, не доказательство удаления всех системных кэшей,
предела памяти/IO, finalizer/dispatcher5s, pinned readers/GC, fault publication,
key loss, power loss, миграции или installed standard-user/Home/hardware.
T114 и Phase0 остаются открытыми; after_plan hook пока не выполняется.

Первичные источники:
[MediaEngine audio-only/callback](https://learn.microsoft.com/en-us/windows/win32/api/mfmediaengine/nf-mfmediaengine-imfmediaengineclassfactory-createinstance),
[источник из byte stream](https://learn.microsoft.com/en-us/windows/win32/api/mfmediaengine/nf-mfmediaengine-imfmediaengineex-setsourcefrombytestream),
[события playback/seek/error](https://learn.microsoft.com/en-us/windows/win32/api/mfmediaengine/ne-mfmediaengine-mf_media_engine_event),
[закрытие MediaEngine](https://learn.microsoft.com/en-us/windows/win32/api/mfmediaengine/nf-mfmediaengine-imfmediaengine-shutdown).

### T114 / RQ30-H1: сбои публикации и повтор после оставшихся блоков — 2026-10-01

**Decision:** в disposable protected-stream стенде сохранять immutable версии
после сбоя и выбирать следующий номер выше всех найденных block names, а не
только записей выбранного индекса. Имена временного индекса содержат generation
и block version. Это минимальное исправление доказанной коллизии CREATE_NEW,
без удаления прежних объектов, overwrite или новой библиотеки. Обход ограничен
1024 объектами/256 block positions/64MiB; это границы стенда, не окончательный
large-layout recovery/GC contract T115.

**Rationale:** baseline actual restricted medium/noadmin опыт прошёл 28 случаев
сохранения контрольных bytes, но отдельно выявил отказ продолжения: оставшийся
неопубликованный блок занимал номер, который writer повторно выбирал из
последнего индекса. CREATE_NEW отвергал повтор; старый checkpoint оставался
целым. После учёта оставшихся версий тот же класс generated append/rewrite
опытов прошёл 28 случаев и 16 повторов после допубликационных сбоев. Новые
полные bytes совпадают с oracle, reader, открытый после сбоя до повтора,
по-прежнему читает прежние полные bytes, снятые после сбоя block/temp hashes
не меняются во время повтора. Это не reader, открытый до исходного сбоя.

Шесть точек — half/full block write, half/full candidate-index write, после
MoveFileEx и после published-index Flush/Close. Проверены введённое исключение
и ExitProcess(77); для исключения отдельно требуется точное достижение hook,
не только общий STG_E_WRITEFAULT. При 1–4 выбирается прежний checkpoint,
при 5–6 наблюдается новая целая версия. Это process-cut proof на текущем NTFS,
не гарантия при отключении питания. 12 failed writers отвергают новые Read,
Write и Commit; got/wrote остаются нулевыми. Hashes/receipts — round136.

**Alternatives considered:** удаление оставшихся блоков и повторная запись
с тем же именем отвергнуты: они не нужны для устранения коллизии и затронули бы
preservation/reader boundaries. Metadata inventory не заменяет production
identity/path/overflow/GC design. Не проверены большие объёмы, multi-block
atomic operation, серия повторных сбоев, полная потеря ключа, resource peak,
Stop/dispatcher fence, миграция, установленный GRAF и аппаратная матрица.
T114/Phase0 остаются открытыми; T115–T118 не начаты, product storage не менялся.

### T114 / RQ30-H1: combined resources и максимальный index envelope — 2026-10-01

**Decision:** сохранить native block/index кандидат, но full-block validation
делать вне foreground/UI/readiness и не принимать общий1MiB helper cap как
окончательный типизированный protocol. Existing LocalMetadataScan и
open-validation/UploadRecoveryScheduler workers уже существуют; новая scanner
служба не нужна. Потребуются их lifetime/account/delete fences и ресурсный
контракт T115, не простое добавление синхронного reopen в constructor.

**Rationale:** actual restricted medium/noadmin x64 процесс прошёл generated
stream cases1MiB+123/16MiB+123/64MiB-123, полный byte oracle и все собственные
DPAPI envelopes, без MF playback/выхода устройств. Lifetime peak commit
после трёх stream cases13.57MB, peak working set21.17MB; это весь отдельный
процесс, не только layer-owned buffers, и не установленный GRAF. Полный
validated reopen самого крупного случая9.44s, короткий final-tail commit24ms,
самая долгая Write430ms и index publication388ms: факт VM, не гарантированные
пороги. Background путь обязателен, чтобы не нарушить быстрый локальный старт.

Затем тот же процесс завершил native MF protected AAC30s, decode/seek и
envelope validation: Finalize/reset/Commit226ms. После separate maximum-index
native envelope4198400B protect/unprotect+compare280/262ms lifetime peak
commit37.26MB и working set59.31MB. Peak — с начала процесса; private samples
не объявлены мгновенным peak, IO counters охватывают все операции процесса,
file_bytes — сумма размеров файлов, не filesystem allocated sectors.
Exact bytes/IO/CPU/timing/receipts — round137.

**Alternatives considered:** whole-file plaintext copy, новый codec/crypto
механизм и GC не добавлялись. Native max-index envelope проверен только в
памяти, не как принятый semantic index/durable disk snapshot; общий helper
его ожидаемо отвергает по1MiB guard. Поднимать этот cap для всех объектов
нельзя: block/index limits должны различаться. Current64MiB fixture не
представляет2637block-hour или64GiB layout; peak/resource sampling и accelerated
CPU не принимают60min±100ppm/reference-x64 SC-003. Полный Stop/dispatcher5s,
key-loss, migration, large recovery/GC/readers и installed acceptance остаются
открытыми. T114/Phase0 не закрыты; after_plan hook не выполняется.

Первичные определения измерений:
[PROCESS_MEMORY_COUNTERS_EX](https://learn.microsoft.com/en-us/windows/win32/api/psapi/ns-psapi-process_memory_counters_ex),
[GetProcessIoCounters](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-getprocessiocounters),
[IO_COUNTERS](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-io_counters).

### T114 / RQ30-H1: максимальный ZERO-only индекс — 2026-10-01, round138

**Decision:** выбранный предел индекса допускается к дальнейшему Phase0
исследованию; полный T114 не принят. Отдельный парсер проверил 262144 явных
ZERO-записей: размерность 64GiB без создания или чтения медиа этого объёма.
Предел общего helper по умолчанию остаётся1MiB; только эта исследовательская
единица компиляции использует index bound4198400B. Product code не менялся.

**Rationale:** actual restricted medium/noadmin процесс опубликовал два
DPAPI-защищённых индекса с payload4194336B каждый; прочитал оба, проверил
envelope/семантику и выбрал generation2. После порчи нового ciphertext выбран
generation1; после порчи обоих индексов authority отсутствует. Две введённые
ошибки на границе чтения до native unprotect также отвергают выбор версии,
сохраняя ciphertext. Это не фактическая потеря DPAPI profile/master keys.
Десять отрицательных случаев парсера прошли. Публикация двух индексов609ms,
повторное чтение обоих551ms; lifetime peak commit27.15MB/working set39.80MB
относится к отдельному процессу, не к приложению и не к SC-003.

**Alternatives considered:** увеличение всех block limits или создание64GiB
файла не нужны для этого опыта и не выполнялись. ZERO-only metadata не
заменяет большой mixed/nonzero layout, проверку каждого реального блока,
повтор после прерванной большой публикации, power loss, Stop/fence или
реальную недоступность ключа. Дисковый reader стенда принимает только точный
max payload; это не готовый универсальный reader. Независимый review —
APPROVED NARROW, полный T114 NOT READY. Exact receipts/hashes и ограничения
покрытия записаны в validation round138; T115–T118 остаются открытыми.

### T114 / RQ30-H1: настоящий dispatcher и protected Stop — 2026-10-01, round139

**Decision:** для будущего protected writer использовать существующие FIFO,
typed EOS, callback fence и polling Finalizer контроллера. Новый dispatcher
или второй lifecycle не нужны. Это кандидат архитектуры, не изменение кода
приложения и не полная приёмка T114.

**Rationale:** отдельный x64 medium/nonadmin процесс связал настоящий
WindowsCaptureSessionController с исследовательским ProtectedStream. Пять
generated cases прошли: normal, overflow, sink rejection, sink exception,
реальная задержка первого sink5100ms. При одном in-flight batch очередь
принимает254data и два EOS; поздний batch не меняет её и не приходит в sink.
FIFO и точные raw float bytes подтверждены после protected Commit/reopen.
Отказы не дают normal savedLocal. UI Stop вернулся за11–680us; pending
асинхронный finalizer запущен один раз, удерживает lease до terminal.

Native MF в этом worker независимо кодирует generated zero PCM той же
принятой длительности, завершает защищённый AAC и проверяет его декодирование.
Это проверка coexistence/завершения, не преобразование сохранённых float bytes
в v5 и не доказательство нормализации/AEC/timeline. Самый долгий worker560ms
включает ожидание своей gate, tail commit, encode и полное decode; не равен
чистому AAC Finalize или времени полного пользовательского Stop.

**Alternatives considered:** отдельная тестовая копия dispatcher отвергнута;
переиспользован существующий friend CaptureSessionTestPeer. Только acquisition
обойдён, native workers не созданы и их cleanup не принят. Порог5s и объём
256items не менялись, неправильные ошибки не переименовывались в успех.
Изолированный опыт не принимает product package/manifest/queue, short-recording
discard, installed UI, key loss, большой nonzero layout или SC-003. Exact
source/EXE/receipts и независимый review — validation round139. T114 открыт.

Дополнение round139: независимый review нашёл P2 в проверочном условии sink
exception, не controller. После минимального exact-throw marker вне callback
свежие сборка и все пять runtime cases снова прошли; UI Stop4–357us,
protected job27.8–122.5ms. Первые timings выше остаются историческими.
Повтор не принимает timeline/v5/workers или весь T114; финальные hashes и
границы повторной независимой проверки записаны append-only в validation.

Финальный независимый результат round139 — APPROVED NARROW, P2 CLOSED;
полный T114/Phase0 NOT READY. Дальше нужен native read-failure опыт и большой
индекс с nonzero references; нынешний marker не симулирует потерю ключей.

Первичные источники для следующего read-boundary опыта:
[CryptUnprotectData](https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptunprotectdata)
привязывает user-scope decrypt к Windows identity и требует проверки результата
и содержимого, а не одного GetLastError. Возможный nondestructive эксперимент
с временной anonymous identity ограничен собственным test thread; это не
удаление профиля и не доказательство настоящей потери ключей.
[ImpersonateAnonymousToken](https://learn.microsoft.com/en-us/windows/win32/api/securitybaseapi/nf-securitybaseapi-impersonateanonymoustoken)
может отказать для restricted процесса: нельзя ослаблять ограничения ради
PASS. Отказ перехода identity не равен достигнутому отказу DPAPI.
[RevertToSelf](https://learn.microsoft.com/en-us/windows/win32/api/securitybaseapi/nf-securitybaseapi-reverttoself)
должен завершить временную identity; при отказе завершать собственный
исследовательский процесс. Этот опыт ещё не реализован и не запускался;
профиль/UAC/ключи/глобальные ACL не меняются.

### T114 / RQ30-H1: mixed large index и native отказ — 2026-10-01, round140

**Decision:** раздельные size guards для block/index и выбор последнего полностью
validated snapshot пригодны для дальнейшего проектирования; T114 ещё не принят.
Максимальная размерность индекса проверена с3 настоящими references в начале,
середине и конце, включая короткий tail, без выделения64GiB медиа.

**Rationale:** medium/nonadmin процесс выбрал2, при повреждении last-v2 выбрал1,
при authenticated-but-invalid generation3 сохранил2, при двух непригодных
snapshot отказал без изменения ciphertext. Exact bytes проверены для8 boundary
ranges и3 полных referenced blocks. Два реальных DPAPI refusal с неверным
optional entropy сохранили6 файлов; это key-context mismatch, не потеря профиля.
Шесть parser negatives прошли. Совокупный опыт5.44s, lifetime peak commit32.69MB,
resident45.04MB; these are isolated process measurements, not app limits.

**Alternatives considered:** общий расширенный block cap, полное64GiB медиа,
новые crypto/stream классы и изменение профиля не нужны для этого опыта.
Переиспользованы research helpers с guard до allocation; отдельный max-dimension
reader ограничен3 refs и не заменяет generic IStream/T116. Wrong entropy нельзя
называть потерей ключа или проверкой другого пользователя. Полная file/failure
matrix и установленный клиент остаются отдельными доказательствами. Exact hashes,
receipts и пределы опыта — validation round140; независимый review ещё ожидается.

По source-only review round140 усилен oracle для encrypted invalid generation3:
перед fallback требуется успешно открыть DPAPI/envelope, подтвердитьg3/точное
invalid поле и получить semantic parser rejection/reset. Пересборка и полный
повтор прошли; ранний crypto отказ больше не удовлетворяет этому сценарию.
Первый run сохраняет историческое значение до исправления. Fresh elapsed8.09s
включает дополнительные scans, не считается временем одного reopen/Stop;
commit peak32.65MB/resident44.77MB. Independent rereview pending.

Финальный independent rereview: APPROVED NARROW, P2 CLOSED. Согласованность
fresh source/build/runtime hashes проверена; дополнительный negative run
reviewer не выполнял. T114 не закрыт: отдельный exit audit должен сопоставить
его буквальные Phase0 критерии с результатами всех combined опытов, не
подменять их будущей installed/migration/100cycles приёмкой T118.

### T114 / RQ30-H1: combined MF IO — 2026-10-02, round141

**Decision:** завершено недостающее количественное измерение совместного MF-пути;
aggregate T114 exit ожидает независимого review, задачи пока не переотмечены.
Новый механизм не добавлен: используется прежний generated30s case и native
process IO counters, window исключает последующий verifyCipherFiles.

**Rationale:** encode/Finalize/reset/Commit → validated reopen → full decode/EOS
и seek10s/1s → reader release дали2086190B read/729376B write при366529B logical
AAC и4 checkpoints/2 rewrites. Whole window561718us, Finalize+reset+Commit246767us,
6 ciphertext files728676B; lifetime commit31.99MB/resident43.47MB, не app quota.
Raw/tail/index cases повторно прошли;64MiB validated reopen9.58s требует прежнего
background пути. IO counters — process transfer accounting, не physical disk.

**Alternatives considered:** новый stream/codec, больший media benchmark,
дополнительный профиль или полная installed матрица не нужны для literal Phase0
measurement gap и не добавлены. Полные product key-loss/power-loss/migration/
100cycles/SC-003 gates остаются T118; задача T115 определит окончательный format
и ownership. Exact source/build/runtime hashes, scope и limitations записаны
в `validation-2026-10-02.md`, round141. Product code не менялся.

**Окончательный Decision:** независимый aggregate review
`checklists/review-2026-10-02-phase0-exit.md` принял буквальный T114 (APPROVED).
Недостающее combined IO измерение достаточно; T114 отмечен выполненным.
RQ30-H1 в исследовательском объёме завершён, выбранный DPAPI/block/two-index
механизм передаётся в T115 для окончательного protocol/ownership design.
Исследовательские границы не объявлены реализованными квотами. Реальная потеря
ключей профиля, power-loss, full product pipeline и установленная матрица
остаются T115–T118; clock T094–T096 остаётся независимым открытым исследованием.

### T094/T095: наблюдённая поддержка фильтра и остаток EOS — 2026-10-02

**Decision:** результат round148 рассматривается как новый механический
кандидат для обсуждения EOS, не как принятая политика дополнения звука.
Прежний запрет выдавать ненаблюдённые отсчёты сохраняется. Product code,
контракт §5 и настройки захвата не изменены; независимый review запрошен.

**Rationale:** actual pinned SincResampler использует 32 входных отсчёта
`[floor(x)-16, floor(x)+15]` для каждого выходного центра x. На sealed EOS
частичный последний fixed request можно исследовать отдельно от выдачи:
два конечных заполнителя вне реального N (17 и −73) и comparator с настоящим
искусственным продолжением дают побитно одинаковые значения только на
полностью наблюдённой поддержке. В disposable Windows x64 опыте176 вариантов
прошли; отрицательный контроль за границей поддержки меняет результат.
При N100/request64/ratio1 доступны69 наблюдённых центров вместо прежних32;
при N128 —97 вместо96. Это уточнение механической причины потери API-хвоста,
не принятие всех исходных/канонических frames и не waveform/SC-003 acceptance.

Курсор повторяет сложения и wrap actual pinned implementation, не `j*ratio`;
проверены request64/512, малые N17–1024, дробные ratios и SetRatio между
output samples. Zero-history старта и последние неподдержанные центры не
выдаются. Связь будущего adapter с sealed EOS, retained real count, строгим
pre-output fence и запретом обработки filler как input coverage должна быть
отдельно согласована до реализации. Pin/исходники/стенд/хеши — round148.

**Alternatives considered:** принимать весь последний callback как настоящий
звук, выдать все вычисленные значения, разрешить padding до EOS или скрыть
невыданные края как complete recording — запрещено. Новая библиотека и
редактирование vendor не нужны. Исследование использует имеющийся native pin.

### T094: отрицательный результат постоянного causal affine fit — 2026-10-02

**Decision:** не выбирать единственную постоянную affine frequency estimate
для всей записи. На round149 найден generated counterexample; этот кандидат
исключён из дальнейшего проектирования. Causal time-varying estimator,
uncertainty/slew и связь с continuous source phase всё ещё открыты.

**Rationale:** bounded fit использует только прошлые anchor-relative метки,
пересекает допустимые slopes ±100ppm и прежний остаток1ms+1source frame,
не получает true rate из генератора. При постоянных −100/0/+100ppm и
ограниченном jitter он проходит искусственный час; устойчивые250ppm отвергает.
Но допустимая смена +100→−100→+100ppm с непрерывной фазой на input steps2000/4000
(номинальные20/40s, не точные физические моменты) делает пересечение пустым
на step2755/номинальные27.55s при44.1 и48k. Настоящий текущий
ClockMapper принимает этот generated поток по действующему bounded residual
правилу. Поэтому простое накопление constraints для постоянной частоты
не годится для её изменения, даже без packet loss и неизвестного будущего.

**Alternatives considered:** сбросить fit/phase на каждой метке, получать
истинную частоту от fixture/oracle либо расширить пороги после отказа — не
доказанное исправление. Нужна одна согласованная меняющаяся clock/phase модель;
оценка номинальной длительности сама по себе не доказывает совпадения волн.
Actual-source/ASan/UBSan proof и limitations — round149. Числа этого стенда
не устанавливают новых продуктовых допусков.

**Независимый итог EOS:** отдельный read-only code review завершился
APPROVED NARROW для frozen source round148. Подтверждены support и inclusive
right boundary,69/97 centers, cursor при Resample(1) и честный negative control.
Finite filler фактически существует внутри callback, но не влияет на выбранный
output; это не claim «padding отсутствует». Scalar/SSE/AVX2 support проверены
чтением, runtime выбирает одну CPU ветку; vendor NDEBUG не принимает DCHECK.
Крупные output partitions, NaN/Inf, reset, AEC/writer/clock policy и полный
EOS не приняты. Подробный результат добавлен к round148 ниже в validation.

### T094/T095: блочная выдача и граница приёма Stop — 2026-10-02

**Decision:** сохранить выбранный support-contained EOS путь как механически
подтверждённый кандидат, теперь и для больших output chunks. Это не разрешение
production padding или завершение clock/normalizer интеграции.

**Rationale:** round150 на том же actual pinned SincResampler прошёл384cases.
Каждый центр проверяется до Resample(chunk), chunk обрезается до первой
неподдержанной позиции и до ближайшей смены ratio. Fixed480 и variable
1/479/31/997/480/7/1024/211 побитно совпали с отдельным Resample(1), с двумя
finite filler и observed generated continuation на выбранном интервале.
Добавлено N65536 для большого числа region wraps. Independent static review
APPROVED NARROW принял механику и honest boundary claim; exact hashes ниже
в validation. Startup/unobserved EOS остаются невыданными,128N даёт97
поддержанных центров,100N —69. Число384=12N×2requests×4ratios×2ratio modes×2chunks.

**Интеграционная граница:** actual WasapiCaptureWorker нормализует до callback;
controller.enqueueBatch возвращает true также при намеренном игнорировании
закрытого admission; Stop закрывает acceptingBatches перед EOS. Следовательно,
bool callback success не доказывает приём исходных отсчётов. Нельзя добавить
worker-tail через обычный callback после Stop или считать всё normalizer
состояние автоматически admitted. Future EOS должен закрыть именно accepted
input prefix за существующим FIFO fence, не открывать capture заново.
Это ограничение будущего adapter, не новый доказанный дефект текущего Stop.
Выбор owner/admission representation для такого хвоста ещё не принят.

**Alternatives considered:** снять Stop fence, принять callback=true как
постоянный receipt, дописать текущий worker buffer после finalizer или считать
весь fixed callback реальным source coverage — запрещено. Новый service/queue
или второй capture pipeline не вводится исследованием.

### T094: предел имеющегося clock evidence — 2026-10-02

Actual worker GetPosition передаёт nullptr для QPC output и использует stream
position только как supplementary monotonicity check. Отдельный PacketProbe
читает current position/QPC pair; schema6 PacketStats показывает накопленные
span errors и pairShift относительно первой принятой точки, не текущую
packet/current-clock latency. Единицы уже пересчитаны правильно: packet
position — frames, current clock — position/GetFrequency, QPC обеих API100ns.
Вывод о VM/driver cause либо выбор current-clock replacement из пяти span
checkpoints не доказан. Следующее исследование должно различить current pair
correlation, packet-origin latency и first-anchor effect на bounded metadata;
это не разрешение проигнорировать count/flags или переопределить packet PTS.

Primary contracts перечитаны: Microsoft
[GetPosition](https://learn.microsoft.com/en-us/windows/win32/api/audioclient/nf-audioclient-iaudioclock-getposition)
и [GetBuffer](https://learn.microsoft.com/en-us/windows/win32/api/audioclient/nf-audioclient-iaudiocaptureclient-getbuffer).
Диагностика и метод сопоставления должны быть определены до следующего device
теста; в round150 устройств/нового metadata capture не было.

### T094: instantaneous pair diagnostic, schema7 — 2026-10-02

**Decision:** исследовать текущую связь двух WASAPI pairs отдельно от ошибок
span относительно первого anchor. Это disposable диагностика, не выбранный
PTS estimator и не изменение численного clock contract.

**Rationale:** schema7 сохраняет exact mapper, guard, ReleaseBuffer/Stop,
visible indicator/Stop, whole-case5s и parent12s из frozen schema6; меняются
только bounded arithmetic/checkpoints и JSON. На samples1/8/32/64 и первом
mapper fault экспортируются [count, position delta, QPC delta, residual]
в100ns, максимум5points. Position delta = currentPosition/GetFrequency −
packetFrames/sampleRate; QPC delta = currentClockQpc − packetQpc; residual =
QPC delta − position delta. Position comparison предполагает общий stream
origin; residual сам по себе не доказывает корректность ни одного clock.
Абсолютные позиции/QPC/device ID и PCM не экспортируются. Delta вне±0.5s
становится null, не нулём и не разрешением принять аудио. Квотиент/остаток
считаются до вычитания больших origins; округление position difference<100ns.

Подготовка: strict MSVCx64 build PASS;2000 generated arithmetic cases PASS;
те же portable cases под ASan/UBSan PASS. Отрицательный generated контроль
показывает: ошибочный первый current QPC влияет на последующий span error,
хотя последующие instantaneous residual равны0. Это пример неоднозначности,
не установленная причина VM fault. Bounded summary check929bytes PASS.
Source и runner frozen вне Git в f200-clock-pair.LXFJPO; live test разрешается
только после независимого narrow review, свежего process/hash check и одним
явно выбранным default48000case. Нет новых аудионастроек/44100/MMCSS в этом
эксперименте. Подготовка не считается T094/SC003 acceptance.

**Alternatives considered:** переиспользовать span errors как текущую latency,
переписать GetPosition position в packet frames без frequency, повышать drift
threshold, очищать sticky fault либо читать PCM для этого вопроса — отвергнуто.

**Единственный live результат:** после независимого APPROVED NARROW review и
fresh process/hash checks один default48000case завершился за441ms;
41/41packets released, Stop0, process0после.39metadata observations имеют
gaps0; packet41получил post-startup DATA_DISCONTINUITY, guard остановил опыт.
На samples1/8/32 position delta10ms, QPC delta14.6458/3.7205/0.042ms,
residual+4.6458/−6.2795/−9.958ms. Это дополнительные различия текущих pairs,
не proof причин VM/driver/scheduler и не воспроизведение clock_drift в этом
run. Replacement packet timestamp через current-clock pair не принят;
порог/flags/count guards не меняются. Истинная phase/frequency модель всё ещё
должна пройти generated changing-rate/waveform и аппаратную проверку. Полный
согласованный estimator нельзя заменить повторением одинаковых коротких probes.
Safe JSON/frozen hashes/cleanup и ограничения — validation round151.

### T094: диапазон достижимого времени при переменной частоте — 2026-10-02

**Decision:** сохранить локальное распространение диапазона времени как
исследовательский кандидат. Постоянный наклон на всю запись, отвергнутый в
round149, здесь не нужен. Середину каждого диапазона нельзя автоматически
публиковать как PTS или использовать как оценку частоты для resampler.

**Rationale:** если частота в каждый момент находится внутри±100ppm, прирост
времени для dn кадров находится между dn·10⁷/(rate·1.0001) и
dn·10⁷/(rate·0.9999). К прежнему диапазону добавляется этот прирост; результат
пересекается с текущей относительной меткой±(1ms+1source frame). Состояние O(1).
Это явно заданная гипотеза: первая метка считается точной, последующие ошибки
ограничены относительно неё, а предел частоты — мгновенный. Действующий
продуктовый guard проверяет накопленный интервал; эти правила не тождественны.
Кандидат НЕ заменяет guard, не доказывает свойства реальных временных меток.

Стенд48instantiations прошёл в Windows MSVC и на Mac Clang ASan/UBSan:
44.1/48k, fixed10ms/variable partitions, постоянные−100/0/+100ppm, смена
+100→−100→+100 на номинальных source20/40s и плавно меняющаяся частота.
Плавный случай задаёт dt/dframe с коэффициентом99ppm, что даёт частоты
примерно−98.9902…+99.0098ppm, не симметричную frequency sine. Генератор использует
jitter400µs; observer получает только номинальную rate и текущие n/q. Известная
истинная шкала используется только для проверок. Отдельный+250ppm случай
вызывает неизменный отказ, как и текущий mapper; другие проверки отвергают
обратный ход, повтор метки, слишком большой диапазон/шаг и выброс. Флаги/native
API/count custody здесь не реализованы и не считаются проверенными.

18,494,460 — число вызовов за всю матрицу, включая повторные отказы после
отрицательного случая, не число принятых пакетов. Позиции проверены до source
nominal3600s; последний объявленный packet count может выходить за этот
горизонт, EOS/точная длительность не приняты. double/long double в обеих
средах имеют53bits mantissa, поэтому это не две разные точности. Origin
вычитается в unsigned до float; nextafter расширяет границы наружу.
Сравнение с генератором допускает0.001tick, не новый продуктовый допуск.

**Найденное ограничение:** на допустимых generated случаях implied frequency
между соседними midpoint достигает4970.21ppm при отсутствии обратного хода.
Таким образом, containment каждого диапазона не обеспечивает согласованную
скорость публикации. Это не доказательство невозможности другой траектории.
Для production нужны выбранная единая шкала, управление фазой/ratio, waveform,
допуски/границы начала и конца, actual admission/EOS integration и review.
Применимость гипотезы к WASAPI/Parallels, неизвестный first-anchor error и
обработка observed clock_drift/discontinuity остаются открытыми.

**Alternatives considered:** хранить все прошлые constraints для постоянной
частоты, получать true rate/будущие метки от генератора, публиковать midpoint
без rate/slew proof или расширять пороги после отрицательного результата —
отвергнуто. Независимый read-only review APPROVED NARROW принял математику и
границы результата, не готовый estimator. Source/hashes/reproduce — round152.

### T094: причинное управление SincResampler на искусственном звуке — 2026-10-02

**Decision:** оставить фазовую обратную связь исследовательским кандидатом,
не переносить её в приложение по одному успешному стенду. Общий exact epoch,
1s correction horizon и command±500ppm — параметры опыта, не утверждённые
правила захвата. ReachablePhase здесь только дополнительная проверка принятых
меток; его interval не выбирает ratio. Действующий ClockMapper неизменён.

**Rationale:** actual pinned SincResampler получает ratio только из уже
полученных n/q, nominal rate, собственного cursor и output count. Истинная
шкала доступна генератору и измерениям, но не controller. Неизменённый mapper
проверяет metadata до допуска samples. Полный callback prefetch обязан быть
наблюдаемым до EOS; support каждого опубликованного sample целиком внутри
принятого prefix. Внутренний EOS filler17/−73 не меняет trusted output
побитово. Fault запечатывает оба prefix; тело отказного пакета не допускается.
Actual RecordingAudioTimeline принимает общий grid48k/480frames с epoch100s,
без переноса первого trusted sample на ноль и без drift trim. AEC — identity,
writer/worker admission не используются.

Свежие9коротких случаев PASS: baseline, opposite±100ppm fixed/variable,
reverse rates44.1/48k, changing/smooth rates, request512, nominal-only negative,
clockDrift и injected discontinuity. На nominal-only phase error5.99997ms;
на controlled healthy≤0.120253ms. Отдельный generated3600s run PASS:
172799520canonical frames, phase_max0.111918ms, duration_error9.625ms,
system RMS−0.000076223dB, nofault/no trim. Это симуляция часа, не часовой
захват микрофона и не измерение времени исполнения. Независимый source review
APPROVED NARROW относится к свежему guarded source, не собственным запускам
reviewer. Exact source/EXE/library hashes и результаты — validation round153.

**Ограничения:** системный RMS ограничен1dB; waveform_max_error и
joint_max_error только выводятся, не имеют acceptance bounds. На часовом
run они0.16402036/0.27000016, поэтому waveform fidelity и межканальная
точность НЕ приняты. Действующий mapper по-прежнему отвергнет реальные
clock_drift/discontinuity, наблюдавшиеся в VM. Не доказаны неизвестный
first-anchor error, разные реальные origins, native query timing, иной
jitter, реальные flags/ReleaseBuffer, Stop/dispatcher races, AEC, writer,
аппаратная матрица и SC003. Нет основания повышать пороги guard.

**Alternatives considered:** oracle true frequency/будущие метки, midpoint
из round152 как ratio, reset epoch, midstream filler или признание identity
AEC реальным подавлением эха — отвергнуто. Следующая полезная граница —
реальный native AEC на generated echo/near-voice и согласованный production
контракт admission/start/EOS, а не повтор тех же коротких live probes.

### T094/T096: native AEC на generated echo/near-end — 2026-10-02

**Decision:** не принимать качество AEC по construction/self-check или
успешному native вызову. Новые generated проверки не прошли предлагаемые
исследовательские границы echo reduction≥10dB и near-band change≤1dB;
эти границы не ослаблялись и не внесены как новый продуктовый контракт.
Готовность Windows/SC003 не подтверждена.

**Rationale:** actual GrafAEC3WebRtcAdapter вызывается через actual timeline,
reverse-before-near-end, microphone/output in-place; raw input копируется
только внутри measuring wrapper до обработки. Renderer сначала tone/chirp,
потом отдельно deterministic continuous interpolated noise+997Hz; microphone
0.65·render(t−4ms)+independent2111/1777Hz tones. After4s warm-up измеряются
1s quadrature band energies до/после AEC. При baseline44.1→48k/48k tone/chirp
echo band−0.112213dB/near band−0.124398dB; broadband−2.328237/−2.270941dB.
Оба executable exit1 на первом случае. Остальные заявленные в main случаи,
включая identity negative, НЕ выполнены и не считаются проверенными.

Для разделения native алгоритма и resampler выполнен отдельный direct48k
diagnostic, три6000-block generated случая. Metrics reset после24s не меняет
native state;36полных1s окон. Echo-only: echo−0.195884dB, near-band−0.129654dB
(голоса в этом случае нет). Near from start: echo−35.656151dB, near-band
−18.277412dB. Near after20s training: echo−3.589465dB, near-band−3.438458dB.
Diagnostic exit0 означает только завершённые вызовы/finite metrics, НЕ
suppression acceptance. Ни один результат не подтверждает одновременно
необходимую очистку эха и сохранение near-end компонента.

Pinned первичный render_signal_analyzer.cc содержит narrow-band adaptation
masking. Это объясняет необходимость отдельной broadband проверки, но НЕ
доказывает причину результатов. Не доказаны неисправность installed app,
ошибка resampler, проблема VM или достаточность другого training режима.
Двухтональный near-end не равен речи; broadband шум также имеет энергию в
2111Hz, поэтому near-band metric — не изолированный voice gain и не MOS/
широкополосное ERLE измерение. System/cleaned joint error не alignment oracle.

**Alternatives considered:** считать weak reduction готовым AEC, перенести
threshold, включить raw-mic fallback, скрыть failed baseline или приписать
проблему VM по одному результату — отвергнуто. Следующий причинный шаг —
сопоставить native reference fixture/configuration и API units/delay с этим
адаптером; сначала независимая проверка измерений. Production source unchanged.
Exact sources/hashes, builds/runtime и review scope — validation round154.

### T094/T096: alias и задержка, найденный Mac reference — 2026-10-02

**Decision:** не менять Windows output alias или подставлять40ms задержку
как исправление. Fresh paired native experiment исключил alias как причину
разницы в этих fixtures:6000blocks×6cases, два независимых actual adapter,
identical input, separate/in-place outputs полностью побитово равны.
Синтетические acoustic4/40ms не являются measured stream buffer delay.

**Rationale:** на40ms echo-only997Hz reduction37.904452dB лучше, чем0.195884dB
на4ms; near-from-start и trained40ms997Hz reduction35.519303/39.482100dB,
но2111Hz band−21.120643/−15.059707dB. Совместная исследовательская граница
не пройдена. Это эффект изменения искусственного пути эха в этих данных,
не установленная причина плохого качества в installed app. Внешняя задержка
buffer API имеет другое определение; нельзя передавать acoustic delay oracle.
Все прежние failed результаты сохранены, пороги не изменялись.

Primary pinned audio_processing.h подтверждает deinterleaved float[-1,1],
10ms frames и допустимый input/output alias. Native source при отсутствии
external buffer delay использует default buffer reset; встроенная оценка
задержки по config enabled. set_stream_delay_ms отсутствие пока только
наблюдённое отличие вызовов, не подтверждённая причина качества.

Найден существующий approved-reference test
`apps/macos/Shared/Tests/RecordingAEC3QualityTests.swift` и полностью прочитаны
Mac native bridge/Swift wrapper. Pin одинаковый Windows/Mac. Mac bridge
перед capture вызывает set_stream_delay_ms, Swift передаёт0; Windows adapter
этот вызов пропускает. Mac fixtures — smoothed LCG noise с envelope и voiced
harmonics, а не stationary997/2111tones: room delay20/80/150/300ms, RT60
0.2/0.5/0.8s; far-only≥20dB после5s; near-only level±1dB/correlation≥.98/
lag≤480; double-talk echo≥10dB/near projection±3dB/no silent run>960;
также acoustic delay80→85ms и canonical mix. Их наличие в исходниках НЕ
доказывает свежий Mac/Windows runtime PASS.

**Alternatives considered:** менять buffer по результату alias experiment,
объяснить оба failures VM, продолжать искать новый acceptance signal вместо
существующего Mac fixture или молча заменить прежние failed tone gates —
отвергнуто. Следующий шаг — воспроизвести существующий Mac quality fixture
на Windows native adapter и Mac bridge, с одними generated входами/метриками.
Порт ещё не создан/не запущен; исходники Mac и installed app не менялись.
Exact alias experiment evidence — validation round155.

### T094/T096: существующий Mac quality reference и изолированный mix candidate — 2026-10-02

**Decision:** переиспользовать существующие проверки
`apps/macos/Shared/Tests/RecordingAEC3QualityTests.swift` вместо объявления
общей неисправности AEC по прежним двухтональным fixtures. Для проектирования
Windows закрепить найденную формулу Mac `0.5 * (system + cleanedMicrophone)`;
однострочный кандидат проверен только вне продуктового дерева. Production,
численные clock guards, установленное приложение и задачи не изменены.

**Rationale:** actual Windows adapter и точная копия actual Mac C ABI bridge
собраны с одним pinned WebRTC под Windows. Оба получают одни generated входы:
12 room cases, near-only, double-talk и acoustic delay drift. Все30 core gates
прошли, хотя результаты движков не полностью равны. Это Windows runtime двух
обвязок, не запуск Mac/Swift и не byte identity генераторов разных языков.

Дополнительный actual Windows timeline gate не прошёл: смесь384000samples
на6.02059991328dB выше формулы Mac, max difference0.324655056. Source trace
подтвердил `clamp(system + cleanedMicrophone)` в Windows timeline; Mac timeline
умножает сумму на0.5. AppMain передаёт эти frames writer без коррекции; writer
сохраняет mixed float и кодирует без компенсации gain. Отрицательный остаток
−5.72882613074dB содержит лишнюю половину system reference и не измеряет
изолированное качество AEC.

Отдельная копия timeline меняет ровно этот коэффициент, сохраняя clamp,
count/PTS/admission/guards/EOS/AEC. Те же неизменные31 gates прошли: delta0dB,
max difference0, clipped0, residual reduction22.9561882573dB. Это причинное
устранение mix mismatch на данной generated matrix. Для arbitrary over-range
или nonfinite output эквивалентность с Mac без clamp не объявляется. Старые
суммарные ожидания Windows tests должны быть рассмотрены при разрешённой
реализации; нельзя просто объявить установленную запись исправленной.

**Alternatives considered:** ослабить20dB gate, компенсировать громкость во
writer или UI, поменять native alias/buffer delay, признать native self-check
полной AEC приёмкой — отвергнуто. Исправление относится к общей формуле смеси,
не к каждому consumer отдельно. Независимый source review APPROVED NARROW;
числа запуска получены Main. Evidence/hashes/ограничения — validation round156.
Clock estimator/resampler/start/EOS и protected-custody gates остаются открыты.

### T094/T096: native AEC вместе с causal resampler и контроль окна — 2026-10-02

**Decision:** не считать совместную цепочку полностью принятой и не объявлять
resampler причиной снижения RMS suppression на длинном fixture. Порог20dB
существующего Mac reference относится к окну5–12s. Дополнительный опыт5–60s
является новым исследовательским условием, а не скрытым изменением FR/SC.
Исходные проверки не ослаблены; все отрицательные результаты сохранены.

**Rationale:** frozen causal Source/actual ClockMapper/native SincResampler
из прежнего стенда получает физически sampled linear-interpolated speech/room/
voice, не stationary tones. Actual Windows native AEC вызывается in-place
в timeline с изолированным0.5mix candidate. Четыре60s конфигурации проверяют
48/44.1k, opposite±100ppm, reverse rates и changing rates, fixed/variable
partitions. Только observed packet metadata управляет ratio; true physical
time используется генератором/метриками, не controller. First anchors exact
и один общий epoch остаются исследовательскими предположениями.

Во всех13 cases exact canonical prefix2879520frames, no drift trim,
poison-independent trusted output и mix difference0. Phase max≤.111907ms,
duration error≤9.625ms. Near-only level≈−.50405dB/corr≈.99975969/lag434;
double-talk echo projection27.79898–58.19463dB, near−1.66786…−1.51482dB,
no long silence. Identity far negative correctly rejected at0dB. Но четыре
far-only aggregate5–60s дают16.44563–16.52975dB, а не20dB: original run
exit1,13checks/4failures. Это не общий PASS.

Причинный control без resampler на тех же60s generated arrays также FAIL
по aggregate5–60s: Windows16.63493dB, Mac bridge on Windows16.63462dB.
Их prefix5–12s22.47718/22.47953dB проходит существующий reference. В отдельном
derivative combined stand только добавлены четыре соответствующих prefix gates;
прежние13 не заменены. Combined5–12s22.25206–22.29796dB PASS; итог derivative
17checks/4failures. Смена длины/окна достаточна для наблюдения снижения и без
resampler; причиной этого native long-result либо полной Mac quality parity
эти измерения не являются. Два native engines не объявлены тождественными.

**Alternatives considered:** выдавать17checks за17PASS, уменьшить20dB,
выбросить long failures, исправлять controller по некорректно приписанной
причине, считать borrowed Mac bridge запуском MacOS — отвергнуто. Нужны
согласованный quantitative clock/start/EOS contract, waveform/joint bounds и
живой installed capture; no-fault generated model не исправляет VM clock_drift.
Exact frozen source/build/EXE и transport-recovery ограничения — round157.

### T094/T096: независимые начала источников и дробная сетка — 2026-10-02, round158

**Decision:** сохранить исследовательскую модель с независимым началом каждого
источника из его первой полученной QPC-метки. Это проверенный кандидат механики,
не принятая производственная модель часов. Полный Phase 0 остаётся открытым.

**Rationale:** новый OriginAlignment не передаёт физическое начало генератора
контроллеру: последний использует полученные q−anchorQ, счётчик принятых входов
и курсор. Целочисленное округление на сетку48k сохраняет дробный остаток;
первый уже непубликуемый шаг закреплённого Sinc задаёт фазу без сброса курсора.
Проверены четыре пары частот/дрейфа с разнесёнными стартами0.1375/3.7123/17.0153ms,
независимыми device origins, включая device counter около UINT64_MAX.
Admission, опора ядра, равенство двух заполнителей, общий интервал и EOS сохранены.
Ошибка фазы≤0.111902ms, длительности≤6.075ms; system RMS−0.172…−0.126dB,
ошибка формулы Mac mix0. Начальный непересекающийся префикс исключает timeline;
отсутствие drift trim не означает отсутствия этого стартового исключения.

Из16 quality gates12 PASS/4 FAIL: короткие far окна22.25417–22.31108dB,
near gain≈−0.50405dB/correlation≈0.99975969/lag434, DT echo22.909–55.423dB,
near projection−1.537…−1.438dB/no dropout. Все четыре дополнительные длинные
far окна16.454–16.550dB FAIL при неизменном20dB. Exit1 сохранён. Отдельный
reset-origin negative ожидаемо отклонён общим phase-or-mix утверждением;
это не17-й quality gate и не замена прежнего Identity AEC negative.

Независимый reviewer APPROVED NARROW по исходникам/механике и честному16/4:
runtime/EXE получены Main, reviewer не запускал. Первые метки в генераторе всё
ещё физически точны; near-UINT64_MAX относится только к device counter.
Короткое окно отсчитано от collected prefix, не буквально от прежней физической
Mac шкалы. DT использует ideal PTS references, включая эффект нормализации;
near-only system metric0 означает неприменимость. Производственные ресурсы,
SIMD matrix, macOS runtime и live capture этим не подтверждены.

**Alternatives considered:** общий искусственный q0, потеря дробной фазы,
обнуление обоих origins, снятие длинных quality gates или перенос кандидата
в продукт до coherent contract/review/analyze — отвергнуты.

### T094/T096: точность первой временной метки — 2026-10-02, round159

**Decision:** отделить наблюдаемую относительную непрерывность от абсолютной
точности первого отсчёта и межисточникового выравнивания. До Phase 1 требуется
обоснованная корреляция sample↔QPC либо явно измеренные границы этой точности.
Новая численная гарантия не придумана, текущий ClockMapper не ослаблен.

**Rationale:** независимая проверка вывела действующий guard
|Δn−FΔq|≤10^-4 FΔq+0.001F+1. При q=t+e он ограничивает разность e_i−e_0,
а не e_0: постоянное смещение первой метки не обнаруживается. Portable
AnchorModel проверил actual mapper на12000 observations: стабильные две
шкалы с разностью0.8ms принимаются одинаково при реальном разнесении стартов
и при постоянном timestamp bias; из этих данных различить случаи нельзя.
Первый абсолютный error+1ms и следующий−1ms дают observed8ms вместо10ms:
96frames residual превышает49.0384frames budget, actual sticky clockDrift.
Таким образом guard не эквивалентен независимому допуску±1ms для каждой метки.
Это математические контрпримеры, не доказательство дефекта WASAPI/Parallels.

По официальным контрактам GetBuffer возвращает position/QPC первого frame
пакета, GetPosition — текущую позицию с собственной QPC, в единицах GetFrequency.
GetFrequency номинальна и не измеряет drift/jitter. Подмена текущей позиции
первой позицией пакета без преобразования недопустима; заявленной численной
гарантии абсолютного anchor в этих API нет. Источники:
[GetBuffer](https://learn.microsoft.com/en-us/windows/win32/api/audioclient/nf-audioclient-iaudiocaptureclient-getbuffer),
[GetPosition](https://learn.microsoft.com/en-us/windows/win32/api/audioclient/nf-audioclient-iaudioclock-getposition),
[GetFrequency](https://learn.microsoft.com/en-us/windows/win32/api/audioclient/nf-audioclient-iaudioclock-getfrequency).

**Alternatives considered:** считать shared QPC epoch доказательством точного
начала, удвоить error budget, приписать контрпример VM или молча принять
generator truth за device evidence — отвергнуто. Следующий узкий вопрос:
может ли paired native clock/QPC подтвердить packet anchor при явно проверенных
единицах, stream origin, свежести и границах погрешности. Пока это гипотеза,
не новая authority для захвата. Новых микрофонных тестов в round158–159 нет.

### T094/T096: область paired clock диагностики — 2026-10-02, round160

**Decision:** schema6 checkpoints не использовать как доказательство абсолютной
корреляции первого frame. Прежние JSON сохраняют смысл измерения относительных
изменений; их pairShift не является текущим абсолютным смещением часов.

**Rationale:** PacketStats независимо вычитает первые device/QPC и clock/QPC.
pairShift=ΔclockQpc−ΔpacketQpc. Portable PairModel на actual PacketStats и
actual ClockMapper показал192 generated observations: constant packet bias
0.8ms и common packet/current bias0.8ms оставляют все checkpoints и mapper
verdicts идентичными reference. При явно заданном одном stream origin,
корректной конверсии clockFrequency/sampleRate проекция current QPC назад к
packet first frame обнаруживает только packet bias; common bias остаётся
ненаблюдаемым. В fixture residual0/−8000/0ticks соответственно. Это bounded
synthetic assertion, не готовый native projection/estimator и не аппаратная
граница ошибки. В actual worker GetPosition получает nullptr для paired QPC;
добавление этого выхода само по себе не исправило бы clock mapping.

**Alternatives considered:** трактовать прежние≈−10ms clock_points как
доказанную постоянную задержку, заменить packet timestamp текущим clock QPC
либо объявить native clock независимым физическим oracle — отвергнуто.
Следующий проект должен явно разделить доверенный контракт API, проверяемую
непрерывность/корреляцию и неподтверждённую аппаратную точность. Параметры
общего estimator/start/EOS не выбираются по этой короткой модели.

## Round161 — один конкретный clock candidate, 2026-10-02

**Decision:** проверить `contracts/windows-clock-candidate.md`, а не требовать
измерить абсолютную аппаратную точность первой метки до описания архитектуры.
API anchor, raw continuity checks и отдельная hardware acceptance явно разделены.
§5 и численные пределы отказа не изменены; это ещё не принятый план реализации.

**Rationale:** независимый requirements review подтвердил отсутствие такого
предварительного hardware требования. Модели rounds159–160 показывают предел
наблюдаемости, но не запрещают доверять семантике GetBuffer. Кандидат фиксирует
параметры реально исследованного Source вместо неопределённого «estimator».

**Alternatives considered:** новые бесконечные контрпримеры того же constant bias,
GetPosition как независимый аппаратный oracle и исключение из raw guard ради VM
отвергнуты. Следующий шаг — независимый review выбранной формулы, памяти,
first-phase/full-support EOS и проверки всего admitted envelope. Отказ mapper
на фактических VM метках остаётся самостоятельной нерешённой проблемой.

## Round162 — отрицательная проверка полного admission против ровной output PTS

**Decision:** не принимать candidate только по прежнему Sinc fixture. Отдельный
generated counter model с actual ClockMapper/AudioNormalizer/Timeline показал
48-frame failure, который кандидат с ровной PTS может скрыть. Исследовать
сохранение existing adjacent timestamp-gap guard перед публикацией.

**Rationale:**48000 наблюдений/8rates прошли actual cumulative guard, но step
−4ms→+4ms на50s дал old gap384frames/actual Timeline clockDiscontinuity и
candidate ideal-cursor phase8000us. Cumulative allowance не равен ограничению
скачка между соседними пакетами. Полная семантика §5 включает оба ограничения.
R_i=round(ΔQPC×48000−inputStart×48000/rate) даёт actual old gap через разность
с предыдущим R во всех проверенных случаях; это ограниченная sampled equivalence,
не общая доказанная замена старого механизма и не oracle physical phase.

**Alternatives considered:** объявить mapper PASS достаточным для новой ровной
сетки или добавить ReachablePhase oracle из физически точного генератора —
отвергнуто. Сохранение прежнего численного guard проверяется независимо.
Этот контрпример не объясняет фактический VM clock_drift, который возникает
раньше нормализации; согласованный план этого отказа всё ещё нужен.

## Round163 — простой соседний residual не эквивалентен timeline end

**Decision:** не внедрять R_i−R_prev как готовую замену existing48-frame guard.
Independent review: P1 ровная PTS скрывает отказ; P2 пустые выходы и полный trim
меняют опору сравнения. Два дополнительных actual-core generated теста это
подтвердили; независимый reviewer их source/runtime повторно не принимал.

**Rationale:** при192kHz после3s два1-frame входа дают raw residual30/60.
Actual mapper принимает оба; первый не выдаёт samples. Следующий emitted gap60
обязан отказать, хотя соседние raw deltas30/30 проходят. При48kHz размеры1000/1/1
и residual0/−48/+1 дают полностью trimmed1-frame выход, end остаётся прежним;
последний actual gap2 допускается, хотя raw difference49 отверг бы его.
Для точной старой семантики нужны виртуальные непустые output boundaries и
end=max(previousEnd,newEnd), не просто предыдущий пакет/QPC.

**Alternatives considered:** второй полный legacy normalizer ради проверки,
сброс опоры на каждом принятом raw packet или автоматическое tightening49→fail
отвергнуты как невыбранные решения. Нужно определить численное gap правило для
новой нормализации и согласовать изменения §5 явно; старый output count не
подменять новым молча. Производственная реализация пока не разрешена.

## Round164 — без legacy shadow; native staging и relative witness rounding

**Decision:** одно преобразование Sinc и существующий RecordingAudioTimeline
как единственный alignment owner. Реальная QPC-привязка выходного sample center
передаётся в timeline до canonical publication; actual interpolation/trim/failure
не заменяются виртуальным end. Candidate revision164, всё ещё pending.

**Rationale:** independent requirements review подтвердил, что условный пример
441/441 не закрепляет linear algorithm. Exact legacy decision-set equivalence
не является новым требованием; safety semantics и exact-signal partitionization
сохраняются. Предлагаемая relative witness formula учитывает integer origin
residue и packet anchor для соответствующего центра, а не callback read end.
Упаковка sink не может скрыть смену опоры.

Native disposable staging probe повторяет реальный pinned Sinc callback/cursor,
input sizes1/479/31/4800/480/7/1024/211, origins независимые, two EOS poisons.
11rates8000/8001/16000/44100/44101/47999/48000/48001/96000/191999/192000:
peak unread4863frames<=4864,2189 full blocks zero, no trims. Counter bound
не доказывает allocation layout/quota; fixture Source физически генерирует
samples по запросу, не реализует product-owned fixed FIFO. ReachablePhase
oracle остаётся research-only дополнительным предположением, не raw admission.

Portable relative-witness rounding:625 q0 residues и epochs0/nearUINT64MAX,
11rates, positions128…1023, anchors0/31-grid/center floor, double/long double.
73920000 assertions PASS; naive absolute-floating control35620594 несовпадений.
На этом Mac оба типа53bit: это два host types, не независимый extended precision.
Проверяется формула nominal точного source center, не native accumulated phase,
значения Sinc waveform, изменяющаяся ratio, tag resource bound или VM clocks.

**Alternatives considered:** второй legacy normalizer, отдельный виртуальный
timeline end без реального trim, q0+outputIndex до clock corrections и округление
большого absolute floating time отвергнуты. Raw thresholds и §5 не ослаблены;
candidate не заменяет нормативный контракт без оставшихся проверок и review.

## Rounds165–166 — полный witness путь: safety PASS не равен качеству

**Decision:** не переносить concrete round164 packet-center witnessPTS
реконструкцию в продукт. Actual native AEC quality выявила регрессию на входе,
который actual raw mapper допускает. Пороги и нормативный контракт не меняются.

**Rationale:** paired zero sources на11rates и двух one-frame stress проходят,
six8ms jumps после50s отвергаются actual timeline при healthy mapper.
Кольцо160 tags достигает measured peaks3/81/84, не универсального bound proof.
Независимый reviewer обнаружил повторное использование разошедшегося курсора
после flush failure; terminal guard исправлен в disposable Source и повторён
native. Приёмка reviewer ограничена этой правкой, не clock plan.

Ненулевые generated far/near/DT fixtures используют actual Windows AEC3,
существующие Mac metric helpers и unchanged thresholds. При48000 render /
44100 mic, own fractional origins и variable input до4800,12s:
metadata jitter0.4ms far0.945745dB FAIL20, near-.504dB/corr.999706/lag434 PASS,
DT9.82036dB FAIL10. 1199 canonical blocks, trimmed1876/1731.
Контроль без jitter: те же блоки, trim0/0, far22.4148dB PASS иDT28.4251dB PASS.
Третья проверка отключила только ratio control: с jitter far0.946011dB FAIL,
DT9.74786dB FAIL, trim1802/1675; без jitter все3PASS. Значит SetRatio controller
не необходим для регрессии; direct packet-QPC / real timeline corrector path
уже достаточен в этой fixture. Trim отдельно от interpolation и packetwise
phase этим опытом не изолирован, аппаратная причинность не доказана.

**Alternatives considered:** ослабить20/10dB thresholds, убрать jitter fixture,
считать safety PASS приёмкой качества или просто выключить controller —
отвергнуты. Нужно отделить timestamp uncertainty от actual drift и сохранить
обнаружение разрывов; новый конкретный estimator/contract пока не выбран.
Исследование не исправило живой VM raw clock_drift, не закрывает длинные far
FAIL предыдущих раундов, SC-003, protected custody или installed/UI acceptance.

## Round167 — continuous Sinc, innovation guard и исполнимый input bound

**Decision:** продолжить исследование phase-driven conversion вместо direct
packet witness reconstruction. Concrete successor ещё не принят, нормативный
§5 и thresholds не меняются. Plain uniform PTS без проверки часов не возвращён:
actual raw mapper и отдельный terminal phase guard проверяют input metadata
до дальнейшего resampling/publication.

**Rationale:** native generated tests подтверждают12/12 прежних quality
criteria при nominal/opposite±100ppm/sinusoidal99ppm, jitter0.4ms, paired48k/44.1k,
variable1…4800, own origins,12s. Far21.82…21.86dB/DT27.90…40.42dB, no trim;
near PASS относится только к pre/post-AEC обработанному входу, DT к общей
projection metric, не отдельно очищенной echo component. Waveform/hardware
exhaustiveness, partition invariance,60min/CPU/writer ещё не доказаны.

Controller прежний candidate1s/±500ppm; innovation сравнивает received
input-relative QPC с accumulated actual Sinc cursor offset в48k frames.
Separate rejection>48 не заменяет raw100ppm+1ms+frame.13healthy zero cases
8–192k/two one-frame stress и6cumulative-admitted8ms jumps прошли native;
fault prevents further Source advancement, но global second-source fence
и владение сессией не проверены.

Independent review нашёл P1:94admit без drain могло дать83161 input и
применить последнюю команду−386.8ppm ко всей очереди, computed−4.02165ms.
Bounded derivative требует callback unread<64 до packet admission; native
regression отвергает третий вызов при480 input и неизменном callback0,
late drain не возобновляет выход. Это не real-owned allocation quota proof.
Неиспользуемый old witness negative driver, не распознающий phaseRejected,
и другие frozen drivers удалены из derivative;242 строки меньше.

**Alternatives considered:** запретить jitter fixture, ослабить AEC metrics,
перенести playback arrival timestamps OBS либо relaxed integrity handling
WebRTC — не выбраны. WebRTC
[CoreAudioInput](https://webrtc.googlesource.com/src/+/d2c106be9c34f71b756e45b2b7fd9e97f553a549/modules/audio_device/win/core_audio_input_win.cc#318)
использует captured QPC для periodic latency estimate, а payload передаёт
в FineAudioBuffer; warning-only flags/restart не являются готовым GRAF gate.
OBS
[ProcessCaptureData](https://github.com/obsproject/obs-studio/blob/2c4e446a2201d5ef66b8909190f7f15afe092ace/plugins/win-wasapi/win-wasapi.cpp#L930-L1017)
допускает callback-time timestamp в обычном capture, но этот путь запрещён
нашим контрактом. Чужой код/новая dependency не внесены.

Открытый counterexample: две innovation величины около±47.52 могут пройти
abs48, хотя adjacent change≈95frames. Это существенно и не равно прежнему
timeline jump rule. Следующее исследование — именно его native replay и
согласование guard, не новое объявление проекта принятым по12 коротким PASS.
VM raw clock_drift всё ещё требует отдельного решения до работающего capture.

## Round168 — adjacent counterexample воспроизведён и guard проверен native

**Decision:** конкретный successor дополняется отдельной проверкой соседнего
raw phase residual. Не считать abs innovation48 сохранением jump rule без неё.
Normative §5 пока не заменён; исследование остаётся Phase0.

**Rationale:** same bounded Source/actual mapper/Sinc/timeline, generated
metadata ±40canonicalframes после2s,48000Hz/fixed480/no actual physical drift:
native modelwithoutstepguard принял79.9968frames между соседними опорами,
maxinnovation41.5589<48,299pairedblocks. Дополнительная проверка
step=(observedOffset−previousObservedOffset)*48000/rate не использует consumed
offset и не может компенсировать raw jump прошлой resampler коррекцией.
В новой версии step79.9968 прекращает Source приinnovation40.2224<48;
raw mapperhealthy,200blocks trusted, late calls не возобновляют выдачу.

Новая native source025eccaf… повторила12quality PASS без изменения чисел,
13healthy zero/6eight-ms faults/94queued-admit negative PASS. Independent
read-only reviewer узко Approved формулу и порядок; не запускал tests и не
принимает весь contract. Отказ доcommand/ratio/accepted/packet mutation;
actual mapper/tag текущего пакета уже обновлены, что названо явно.

**Alternatives considered:** надеяться, что отдельная величина innovation
всегда обнаружит переход, или удалить counterexample — отвергнуты. Новый guard
не обещает exact старые output decisions для empty output/full trim. Нужно
согласовать эту явную консервативную semantics и доказать остальные границы
до внедрения. Current raw VM clock_drift/SC003/hardware/full UI всё ещё открыты.

## Round169 — nominal waveform partition и точность команды

**Decision:** сохранить полученный FAIL предыдущего prototype и исследовать
минимальную command-only зону нечувствительности в один100ns тик. Не повышать
существующий sample tolerance0.00001 и не ослаблять raw clock/refusal guards.

**Rationale:** тот же абсолютный generated сигнал700+1900Hz,0.5s, nominal
physical rate и rounded QPC,11rates8–192k. Fixed10ms baseline сравнивается
с variable1…4800 и one-frame packets; drain480/479/1 также меняется.
Без controller22/22 exact, с controller7/22FAIL при сохранённых counts/PTS;
наибольшая ошибка0.0000411868. Это обнаруженная зависимость команды/выхода от
комбинации разбиения и обработки, не доказанный аппаратный dropout.

После command-only floor `abs(observedOffset-consumedOffset)<=rate/1e7`
команда нулевая:44/44comparisons exact. Pinned SetRatio реагирует на изменения
больше double epsilon и пересчитывает ядро; порога1e-6 в нём нет.
One-tick rationale относится к двум идеальным меткам, округлённым до ближайшего
тика, не к реальной точности WASAPI. В feedback входят и остаток Sinc, и
численные погрешности; универсальный long-duration double bound ещё не доказан.
Independent reviewer принял этот эксперимент условно, не нормативный §5.

Первое independent review предупредило: сравнительный PASS сам по себе может
скрыть одинаковую потерю во всех вариантах. Следующий driver проверил независимо
полные nominal границы kernel support, непустоту, PTS/count обоих источников
и число480-frame блоков.66прогонов/44сравнения PASS, max_error0; reviewer
проверил формулы для11rates точной рациональной арифметикой. Dynamic ratio и
другие origins этим не охвачены.12/12actual-native-AEC metrics и13healthy,
6eight-ms faults, отдельные adjacent/backlog negatives также PASS.

**Alternatives considered:** увеличить sample tolerance, исключить нечётные
частоты, отключить controller для всех входов, публиковать только удобный
480-frame prefix — не выбраны. Команда меняется минимально, existing mapper/
phase/step/staging проверки неизменны; доказательства ограничены generated
native chain. Продуктовая запись/VM clock_drift/SC003/полный дизайн не приняты.

## Round170 — first origin и фактические native kernel boundaries

**Decision:** сохранять strict ideal FAIL отдельно, а полноту реально выдаваемого
native диапазона проверять непосредственно по actual convolution read window,
не только по зеркальному double cursor или ideal rational формуле. Не менять
допуски часов, sample tolerance либо библиотеку ради совпадения двух моделей.

**Rationale:** firstorigin0/8k/count400 дал SourcefirstPTS97/generated2311,
тогда как ideal oracle ожидал96/2310; длина2214 одинаковая. Независимое чтение
фактического input_ptr с прежним native convolution вызовом показало j96 window
[-1,30],j97[0,31],j2310[368,399],j2311[369,400]. Поэтому Source правильно
исключает unobserved startup и сохраняет полный настоящий хвост.
Это numeric distinction, не доказательство hardware dropout/Sourceloss.

Матрица11rates×6QPCorigins×6start offsets×3partition/drain variants:
1188complete Source runs/native references PASS по границам/длине/значениям
с existing1e-5,792partition comparisons exact0. Full native reference equality
не объявлена bitwise0 по всей matrix; вывелись только subsetreferror0.
Source raw admission/control/guards unchanged; controllable generatedq0,
checked fixture integer sum и relative-only phase measurement добавлены отдельно.
Исследовательский seam использует существующий FRIEND_TEST без patch/newlib;
он последовательный, не гарантирует exception reuse/nonfinite/concurrent tests.
Reviewer по source узко Approved; native runs выполнял основной агент.

First-origin conversion имеет отдельный integer proof: q×3/625,period625,
maxG88544371553805848,maxremainderproduct479999952000,absresidue<=4992000,
firstRatio>=nominal×0.5008. BigInt cross-check3491q/6epochs совпал с current
quotient/remainder формулой. Largeabsolute metadata проверены отдельно от
large elapsed/input counts; последние и dynamic saturation ещё открыты.

**Alternatives considered:** epsilon-расширение support bounds, округление
курсора перед публикацией, принудительная выдача unobserved startup, patch Sinc,
переписывание retained FAIL в PASS — не выбраны. Проверяем фактическое закреплённое
ядро, сохраняем оба результата и не меняем normative§5 без полного review.

## Round171 — малый остаток и локальный центр вместо больших double

**Decision:** в research successor считать масштабированные целые значения
через quotient/remainder, объединять целочисленные residuals до double;
соседний step считать из packet delta и сохранять integer local native center.
Предел input2^52 взят из существующего AudioNormalizer, не выбран заново.

**Rationale:** на16896 введённых matched numeric states старые формулы дали
2003 ложные команды/949 несовпадений центра. Первый найденный old feedback
−0.09375 при rate8000/accepted281474976710657 вместо0; base281474976710640 и
index16.98 также округлялись на соседний центр. Это крайне большие counters,
не наблюдавшаяся ошибка короткой записи. До1h maxoldfeedback1.1920928955e−7;
для всей матрицы stablemax7.1054273576e−15. Native reachable state/длительная
запись не доказаны. На этой матрице naive split residuals тоже не дали false
command, их дефект без отдельного counterexample не утверждается.

Общий helper проверяет domain/overflow/nonfinite до преобразований.10 guard
checks, actual native support792comparisons/1188runs,quality12 и прежние
healthy/jump/adjacent/backlog scenarios PASS. Подробности/fingerprints находятся
в validation Round171; нельзя переносить эти результаты на старый installed EXE.

**Alternatives considered:** увеличение one-tick зоны/clock budget, перевод
native cursor в ideal rational модель и переписывание старого FAIL не выбраны.
Нет необходимости менять pinned native library или добавлять зависимость.
Полный clock design/§5 и причина raw VM clock_drift пока не приняты/не решены.

## T119: один нативный Join вместо запуска snapshot URL — 2026-10-02

**Decision:** повторить F279 resolver/one-operation/fresh browser recovery через
существующий Windows transport/bridge/dispatcher, без второй web страницы.
**Rationale:** на master721b5125d799ea798a4af0b3625e18d3c1109039 Mac
EmbeddedCabinetCalendarJoinBridge принимает exact action/eventId/requestId с
двумя UUID, требует main meetingList document и ревалидирует session/document.
CalendarMeetingOpener использует один eventOpening, fresh GET и явное browser
recovery. Windows AppMain пока открывает snapshot meetingUrl через ShellExecute;
WebViewBridge принимает лишь шесть intents, join-target в DesktopApiClient нет.
Это подтверждённое отсутствие общего сценария, не проблема Windows web дизайна.

Для Windows используется штатный
[Launcher.LaunchUriAsync](https://learn.microsoft.com/en-us/uwp/api/windows.system.launcher.launchuriasync):
bool подтверждает передачу приложению, не подключение к встрече; API доступен
desktop caller. Для явного browser-only пути
[IgnoreAppUriHandlers](https://raw.githubusercontent.com/MicrosoftDocs/winrt-api/docs/windows.system/launcheroptions_ignoreappurihandlers.md)
исключает HTTPS app handler и выбирает default browser. Native installed
associations всех трёх продуктов ещё НЕ проверены. Новый URI scheme/path по имени
продукта не выдумывается; успешная compilation не считается native parity.

**Alternatives considered:** snapshot URL/старый 303, общий ShellExecute browser
retry, generic run_process/web URL, отдельный HTTP client и Windows HTML copy
отвергнуты: stale access, повторный app handler, лишние полномочия или дублирование.
Спецификация/bridge/data-model/plan/quickstart уточнены; reviewer/analyze/code/live
остаются дальнейшими проверками, clock/storage/billing не приняты этим решением.

[QueryUriSupportAsync](https://learn.microsoft.com/en-us/uwp/api/windows.system.launcher.queryurisupportasync)
проверяет поддержку URI и для desktop applications. До custom-scheme launch
отсутствие handler отличается от unknown/error; нельзя отправлять пользователя
в Store вместо браузерного сценария Mac. Resolver ограничен общим15s deadline.
В Windows11 VM без запуска URL проверены создание WinRT LauncherOptions и
IgnoreAppUriHandlers=true (exit0, BROWSER_ONLY_OPTION=True). Первая PowerShell
попытка без WinRT type metadata и encoded argv завершилась exit1; исправлен только
способ диагностического вызова. Это доступность свойства, не compilation C++
продукта, не проверка native client/browser launch и не приёмка T119.

## Round174 — явная association key: проверка механизма, не Телемоста

**Decision:** оставить `SEE_MASK_CLASSKEY` исследовательским кандидатом для
передачи неизменной HTTPS ссылки известной регистрации Windows-клиента.
Продуктовый Launcher contract не заменён; U1 и T119 остаются открытыми.

**Rationale:** текущий VM `AssocQueryStringW` с IS_PROTOCOL и отдельно
FIXED_PROGID для telemost вернул существующий объект Parallels `.ico`, не native
EXE. Это lookup, не доказательство фактического запуска ОС. ByKey query от явно
открытой read-only HKCU Classes key вернул YandexTelemost.exe, product Yandex
Telemost, Authenticode Valid. Native App Paths для EXE в HKCU/HKLM не найдены.
Полные command templates, локальные пути и частные ссылки не записаны.

[SHELLEXECUTEINFOW](https://learn.microsoft.com/en-us/windows/win32/api/shellapi/ns-shellapi-shellexecuteinfow)
поддерживает явную association key с KEY_READ, отдельно от default handler.
Собственный одноразовый класс/консольный sink без App Paths/UseUrl получил4/4
синтетических HTTPS ссылки: root, percent-encoded quote/query/fragment,
percent-encoded UTF-8 и double-encoded value. Args=2, UTF-8 length/SHA-256 точно
совпали; процессы завершились, exit0. `unicode` содержит percent-encoded UTF-8,
не буквальные Unicode символы. Это доказывает механизм лишь для собственного
обработчика, не принятие HTTPS настоящим Телемостом или подключение к встрече.

Cleanup запрещён до dispatch и разрешён только при известном process_complete.
Exception/unknown сохраняют собственные keys и прекращают следующие cases.
Receipt атомарный; ожидание Stopwatch вместо wall clock. Process/receipt waits
не ограничивают ShellExecuteEx, whole-call deadline не заявлен. Reviewer принял
две правки исходников, не runtime/native/product результат. Последующая отдельная
read-only проверка точного fixture ID подтвердила отсутствие keys и sink процессов.

**Alternatives considered:** угадывание custom URI/EXE, ручная process command,
смена defaults и признание HTTPS Available доказательством native parity не
выбраны. Открытая key не фиксирует её значения/EXE; выбор актуального получателя
и фактическую поддержку HTTPS нужно проверить отдельно. Existing
WindowsTargetDetector/VerifiedTargetRegistry не заменяются второй системой
определения приложений; просмотр их кода не означает готовый launcher.
Mac locked, реальные приложения/URL/встречи/микрофон не запускались. Defaults,
UAC и постоянная PowerShell policy не менялись. Детали/hash — validation
2026-10-02, Раунд174; полный план и нормативный bridge не изменены.

## Round175 — насыщение команды нативного Sinc

**Decision:** отдельно проверить ранее не достигавшийся предел controller
±500ppm, не повторять12 прежних quality cases и не менять raw clock allowance.
Текущий NumericPhaseSource сохранён; исследовательский derivative меняет только
подключение прежнего helper и amplitude metadata noise4000→8000ticks.

**Rationale:** actual native Sinc, split residual arithmetic, прежние raw mapper/
innovation/step guards и Source drain прошли22 cases:11rates8–192k, два firstQPC
origin, physical−100/+100ppm, jitter0.8ms. Обе команды каждого Source достигли
−500/+500ppm; каждый case дал399 непрерывных480-frame blocks без trim и max
generated phase error<=0.210121ms. Завершение проверяет full-support по прежнему
Source cursor и bitwise equality двух EOS fillers. Независимого наблюдения
реального convolution input_ptr в этом новом saturation запуске нет.

**Alternatives considered:** увеличение timestamp/phase guards, сброс cursor
при saturation, повтор старой shortquality матрицы вместо насыщения и объявление
проверки SC003 не выбраны. В driver используется IdentityStage/zero generated
signal, не actual AEC execution: quality preservation им не доказывается.
Fixed около10ms packets/4s duration не покрывают variable/long/ownedFIFO/Stop.
Build/run exit0; wrapper фиксирует2 sources+helper, не все transitive sources/
linked libraries. Это не hermetic build attestation. Narrow source review
направлен тому же живому reviewer, пока не завершён; нормативный §5 не изменён.

## Round176 — фактический native запуск и причина фазового отказа

**Decision:** сохранить launcher как исследовательский кандидат до проверки
сценария подключения; проверить увеличение силы коррекции, а не допуска ошибки
часов. Это продолжение high-risk speckit-plan Phase0, не готовая реализация.

**Rationale:** Mac разблокирован. Fixed public root через read-only явную
association key открыл домашнее окно настоящего Windows Yandex Telemost
2.42.4.9707. Отдельно подтверждены один процесс/одно окно, соответствие пути
проверенной регистрации и Valid signature. Встреча/микрофон/Record не запускались.
Обработчик Parallels по умолчанию не менялся. Это не доказательство Join
произвольной допустимой ссылки, URL fidelity клиента или отсутствия гонки
проверки регистрации с запуском; U1/T119 остаются открытыми.

Generated quality test при jitter0.8ms,12s,48000/44100 Hz выявил отказ старой
команды±500ppm: innovation48.1112550067frames на packet471 микрофона, raw mapper
здоров, adjacent step14.1744 и staging отказа нет. Три номинальных quality cases
PASS, следующая пара−100/+100ppm остановлена до оценки качества. Скалярная
рекуррентная модель с проверкой innovation ДО обновления correction воспроизвела
первое пересечение на packet471; она не наблюдает native cursor/rounding.

Derivative с единственным runtime изменением clamp±1000ppm прошёл actual
native Sinc/AEC3 quality12/12 без изменения thresholds и с дополнительным
generated phase<=1ms assert. Все1199blocks/case непрерывны, trim0/0;
maxinnovation43.424079frames, maxphase0.122486ms. Положительный результат
обосновывает дальнейшую проверку управления, не принятие §5/SC003/rawVM.
Source review round175 узко Approved; он не закрывает четыре design gap:
смысл выходного PTS/отказов, dynamic partition independence, owned FIFO,
полный пригодный хвост принятого входа перед Stop/EOS.

**Alternatives considered:** увеличение допустимой ошибки, пропуск guard,
обвинение VM/AEC без причинного доказательства и признание короткого zero test
доказательством качества не выбраны. Исходный Source и failure log сохранены;
новые источники находятся вне Git. Нет новой зависимости, смены установленного
приложения, серверной/macOS логики или политики безопасности.

Последующее узкое source review derivative Approved, mandatory P1/P2 нет.
Сохранённый отказный corpus повторно прошёл13 healthy/6jump/1adjacent/1backlog,
включая terminal повторные вызовы; amplitude4000ticks для variable fixtures
сохранена явно. Это не variable0.8ms/productionStop/hardware proof и не закрытие
четырёх design gap. Точные hashes и ограничения — validation round176.

## Раунд 177 — длительный потоковый generated стенд

**Decision:** продолжить проверку Command1000 без переноса в продукт. Один час
искусственного сигнала прошёл actual native Sinc → RecordingAudioTimeline →
native AEC3 без хранения массива записи или звуковых файлов. Пара 48000/44100 Hz,
physical−100/+100ppm, metadata jitter0.8ms, фиксированные пакеты около10ms;
timeline ограничен4800frames на источник. Это одна пара, не полная матрица.

**Rationale:**359999 непрерывных блоков/3599.99s; разница длительности10ms,
trim0/0, maxphase0.122556ms, maxinnovation43.435980frames. Пиковый unread512/504,
anchors2/2. RMS render сравнивается с аналитическим уровнем генератора, не с
независимым Mac recording. Память измерена только отдельными snapshots; CPU
всего приложения, real-time scheduling и бюджет памяти продукта не доказаны.

**Alternatives considered:** накопление часового массива и объявление такого
прогона реальной SC-003 приёмкой не выбраны. Нет WASAPI, writer/WAV/M4A,
пользовательского звука, installed update, Stop5s/fence или аппаратной проверки.
Source не изменён; wrapper не закрепляет все transitive inputs/toolchain.
Четыре design gap и исходный VM clock_drift остаются открытыми. Fingerprints,
первый compile failure и границы доказательства — validation round177.

## Раунд 178 — воспроизведена зависимость dynamic команды от входных пакетов

**Decision:** Command1000 не принимать для продукта по long/quality PASS.
Новый counterexample закрывает неизвестность существования dynamic partition
регрессии, но не устраняет её. Один неизменный сигнал/first QPC/count при
constant physical−100/+100ppm, без metadata jitter и со всеми raw guards,
в вариантах fixed/variable/one-frame даёт разные значения при controller=true.

**Rationale:** на44100/48000Hz за0.5s8 из24 сравнений FAIL при прежнем допуске
0.00001; maxerror0.00257591158152. Начало и длина совпали. Все12 comparisons
controller=false и4 nominal controller=true PASS с error0. Отдельный derivative
оставил drain480 для всех input partitions: те же8 failures/численные ошибки.
Следовательно, varying caller drain limit не необходим для воспроизведения.
Здесь source signal и rounded continuous QPC одинаковой physical модели;
меняется sampling/admission cadence metadata, не waveform generator.

**Alternatives considered:** расширить error tolerance, отключить контроллер
в продукте либо ограничить норму §5 только nominal case не выбрано. Нужен
согласованный способ вычисления команды, не зависящий от произвольной границы
пакета. Изменение команды на fixed processing grid — лишь направление для
исследования: пока не выбраны lookup/lookahead/rounding/EOS правила и bounds.
IdentityStage вместо AEC используется намеренно, независимые dynamic full-
support bounds не доказаны. Fingerprints/exit codes — validation round178.

Независимый reviewer предложил сохранить FIFO/Sinc у существующего worker
и изменить admission/producer-complete/EOS порядок вместо переноса raw queue
в dispatcher. Это минимальное размещение без нового worker/service, но не
готовый проект: queue/tail capacities, output после Stop, прежний healthy tail
после новой fault метки и preparation/recorded граница требуют доказательства.
Предложение и ограничения сохранены в candidate contract; оно не принимается
как разрешение runtime или как решение нового partition failure.

## Раунды 179–180 — фиксированная сетка и точные неноминальные метки

**Decision:** исследовать перенос команды на каждые480 generated output frames,
не снимать partition gate. Numeric interpolation на11rates/3linear patterns/
2origins прошла66cases/2676grid points; maxtruth error0.5tick, разность между
partitions0.954143tick. Однако offline native grid с повторным rounding дал
1/24FAIL, сохранение fractional QPC —4/24FAIL. Следовательно, простой перенос
на сетку/удаление rounding не считается исправлением rounded cases.

**Rationale:** независимое чтение §5 не нашло nominal-only исключения, но
различило точные метки и их округление. Дополнительная fixture убирает эту
неопределённость: declared48001Hz/physical48000Hz (−20.833ppm), QPC=n*625/3,
все packet starts кратны3; asserts подтверждают целые точные метки без jitter.
Прежний packet-cadenced controller FAIL2/4 с maxerror0.000456225127;
fixed-grid fractional controller PASS4/4/maxerror0 при прежнем допуске0.00001.
Одинаковые start/count/generated. Это локализует самостоятельную cadence
ошибку: QPC quantization не необходима для её воспроизведения.

**Alternatives considered:** расширение допуска, nominal-only трактовка,
признание заранее известной будущей метки живой опорой или исключение хвоста
не выбраны. Grid опыт намеренно preload-ит metadata и заранее знает конец:
команда заморожена на последних4800input frames, Source выдаёт свой хвост
полностью. Это не bounded live FIFO/Stop/EOS либо quality/SC-003. Нужны
causal availability/latency/bounds/unknown-end правила и работа с неопределённостью
меток. Mac использует исходный CMSampleBuffer PTS, не callback time; готового
такого fixed-grid helper в прочитанных capture clock paths не найдено.
Frozen Source round176 не изменён; ExactGridSource меняет лишь fixture-profile
и разрешённые кратные3 partitions. Fingerprints/границы — validation179–180.

## Раунды 181–183 — причинный bounded grid без предзагрузки

**Decision:** заменить только внешний prototype: Sinc получает реально
скопированный owned ring, команда на480-output cell использует уже принятые
packet-start anchors с lookahead4800. EOS hold-tail появляется после фактического
EOS, не из заранее известного конца. Source/grid fixed buffers16384 находятся
на heap; initial stackoverflow сохранён как отрицательный запуск. Product
worker/normalizer/dispatcher ещё не меняются. Exactprofile PASS4/4 на0.5s и3s;
на3s190 fractional projection cells, error0. Фиксированная непрерывная
неноминальная шкала больше не требует заранее загруженных будущих опор.

**Rationale:** read-only review допускает техническое разделение precise/noisy
observations без исключения неноминальной шкалы либо округления из требований.
Rounded matrix11rates/3linear patterns/three partitions проходит guards, но
11/132 waveform comparisons FAIL при прежнем0.00001. Этот FAIL и historical179
не заменены новой интерпретацией PASS. Nominal44100 regression/rounded±100ppm/
jitter/AEC quality/SC-003 сохраняются. Uncertainty model и measurable quality
behaviour остаются техническим проектом, не выбором пользователя ослабить звук.

**Alternatives considered:** увеличивать tolerance, считать raw envelope quality
proof, использовать future generator metadata либо fixed4864 input bound не
выбрано. Новый cap16384/peak10045 — только research limit/measurement, не
принятый app allocation/latency guarantee. Нужны worst-case capacities, настоящая
admission/Stop/producer completion цепь и independent full-support completeness.
IdentityStage не доказывает AEC; sources/receipts — validation181–183.

## Раунды 184–185 — получатель ссылки и качество причинной звуковой сетки

**Decision:** предварительный lookup + удерживаемый class handle нельзя считать
закреплением прежнего получателя. Собственная ассоциация A→B при открытом ключе
запустила B с точным синтетическим URI; пользовательские defaults не менялись,
ключ/процессы опыта отсутствуют после завершения. Узкий source review Approved,
но T119/U1 остаются открытыми. Нельзя заменить доказательство конкретного
клиента фактом successful ShellExecuteExW или домашним окном Telemost174/176.

**Rationale:** causal grid теперь проверен с actual AEC3, не IdentityStage.
Повторно использованы quality fixtures/thresholds:12/12PASS на rounded0.8ms
noise,48000/44100Hz и четырёх прежних physical patterns. Mirrored-cursor phase<=.142306ms,
echo reduction>=21.980963dB, near correlation>=.9997597, double-talk>=27.014941dB,
trims0/0 наблюдаются, но не asserted; owned peak5324/cap16384. Это measurable
AEC quality только fixed packets, не независимая проверка timing до Sinc;
historical rounded partition FAIL остаются, uncertainty model ещё не принят.

**Alternatives considered:** ослаблять waveform/quality/clock tolerances,
объявлять registry handle неизменяемым снимком либо считать synthetic quality
живой записью не выбрано. Следующий шаг — те же quality gates на переменных
пакетах и interval/physical-truth proof; product FIFO/Stop/custody и installed
UI остаются отдельными gates. Fingerprints/exit codes — validation184–185.

Переменные пакеты с той же0.8ms noise остановились до quality verdict:
adjacent step53.109frames>48; raw/staging не причина. Отказ не переименован в
PASS. При metadataNoise=false, но rounded100ns,12/12 прежних quality gates
проходят, mirrored phase<=.100103ms/owned peak10086. Это отделяет adjacent noise
refusal от clean variable quality, не решает uncertainty/partition invariant
и не исключает jitter из покрытия. Fingerprints — validation186.

Round187 дополнил9run/18gate actual AEC независимым наблюдением fractional
позиции настоящего Sinc через existing test seam, без изменения pinned library
или feeding truth в controller. Система48000/−100ppm,mic44101/+100ppm,q0/q±0.8ms,
12s/fixed packets. Actual phase<=.121870ms, physical near corr>=.998522,
gain≈−.5047dB, render gain≈−.1271dB; прежние echo/near/doubletalk thresholds PASS.
Received slope intervals содержат independent constant physical truth; E
только fixture premise, exact known origin не uncertain anchor subtraction.
Это не замена waveform invariant/variable jitter/Stop/FIFO/SC-003; historical
FAIL остаются. Fingerprints и границы — validation187.

Round188 исправил два P2 truth driver (повторный detach при counter failure и
неполный passed), сохранив old bytes. Follow-up review Approved,9/9runs/18gates
PASS воспроизведены. Общий+2ms PTS shift отказан точной actual-time причиной;
counter mismatch после detach отказан корректно, без crash. Это проверяет
детектор и error path, не новый audio tolerance. Current accepted research
driver — CausalQualityTruthReviewed, не первоначальный truth source. Product
adoption/unknown-end/full-support/FIFO/Stop/custody/live gates остаются открыты.

## Раунды 189–190 — фактическая поддержка и пределы причинного буфера

**Decision:** сохранить received-only grid как исследование, не подключать к
продукту. Independent actual native kernel proof прошёл47/47 и source review:
проверены поддержанные значения/PTS/common full blocks и фактический следующий
образец после раннего EOS. Умышленно отброшенный хвост обнаружен точной причиной.
EOS наступает после целого accepted packet, не точного порога; zero-packet EOS/
31–32 границы не покрыты. Это completeness фактической последовательности,
не correctness команд/AEC/production Stop. float== не отдельный bit identity.

**Rationale:** source capacity audit выявил зависимость границы памяти от
обслуживания и накопленного100ppm отставания; innovation48 не ограничивает n−C
постоянной. Frozen grid q<1e9ticks ограничен<100s; условный high-rate bound16710
не доказывает ни достаточность16384, ни достижимое переполнение. Actual native
опыт неизменных Source/Grid достиг10075 unread на8000Hz до первого вывода без
EOS, опровергая4864. Delayed consumer отказал35-й480packet при16320 unread без
перезаписи input/metadata/позднего продвижения. Это fail-closed, не обещание
здоровой записи при произвольной задержке потребителя. Conditional lookahead
latency600ms на8000Hz/25ms на192000Hz не пользовательский SLA.

**Alternatives considered:** увеличить буфер по измеренному peak, ослабить guards,
переименовать healthy-prefix capacity refusal в PASS записи или объявить
короткий low-rate EOS тест открытым controller proof не выбрано. Следующий
минимальный вопрос — достижимая high-rate граница и численная/lifetime область
контроллера; waveform11/132FAIL/variable-noise/rawVM refusals сохраняются.
Production twoEOS/Stop/writer/custody/SC-003/installed UI остаются отдельными.
Полные hashes/premises/exits и границы source review — validation189–190.

## Раунды 191–193 — достигнутый рост FIFO и обратная QPC-проекция

**Decision:** nominal-input readiness не годится как bounded длинный тракт:
actual native192000Hz/−100ppm/variable healthy input достиг staging refusal
примерно332.64s при unread15927+next480>16384 даже с полным drain после каждого
приёма. Сначала frozen grid отказал своим<100s fixture domain; отдельная
одно-строчная расширенная research область<3601s позволила отделить эти причины.
Целочисленный residual безопасен в рассмотренной часовой области по условному
source review,но native accumulation/quality/hardware этим не доказаны.

**Rationale:** nominal n−consumed C накапливает drift внутри owned input.
Readiness по полученному QPC/output grid времени и обратная соседняя q→input
проекция устраняют эту причину в Ready600s generatedZero:peak10043,два finished/
timeline close/59999blocks. Первый Qpc вариант ошибся на ещё пустом втором
источнике: FAIL сохранён,Ready допускает wait только до первого accepted packet,
не ослабляет origin/lost metadata. Pruned дополнительно делает cleanup общим
для controlled/uncontrolled/holdTail; Ready600s не переносится на него.
Pruned прошёл unchanged47actual-support и negative-tail checks. Однако waveform
matrix132 дала20FAIL при прежнем.00001,хуже прежних11FAIL. Номинальные44 и
uncontrolled66 сравнений PASS/error0,но это не снимает nonnominal rounded gate.

**Alternatives considered:** увеличить cap,ослабить timestamp/phase/waveform
пороги,считать zero PCM качеством AEC или заменить старые FAIL новой успешной
длительностью не выбрано. QPC inverse prototype пока не принимается в runtime.
Дальнейший вопрос — отделить measurement quantization/uncertainty от cadence
waveform invariance с прежними требованиями,после этого quality/длительный
actual Pruned/полный FIFO bound/production Stop/custody/live. Старые artifacts
и отрицательные результаты сохранены; details/hashes/source review — validation191–193.

## Раунды194–196 — временной fit и native kernel boundary

**Decision:** принятие inverse-QPC runtime по-прежнему отложено. Weighted
local fit n(q) по полученным metadata уменьшил прежние20/132FAIL до13,но
.00001 не пройден. Actual convolution trace локализовал максимальный spike
по разные стороны integercell; отдельное одноratio endpoint сравнение
воспроизвело4.3008476e−5 gap безcallback/WASAPI/частного звука.

**Rationale:** это независимый отVM timestamp источник waveform error в одном
случае,не универсальная причина всехrefusals. Minimal external window trial
делитель31/zeroedges уменьшил matrix до5FAIL,но изменил windowcenter15.5vs
sinc16 и частотную характеристику. Остаточный actualtrace worstnearEOS
в однойintegercell,positiondelta.00044581189frames,поэтому нужны rounding/
uncertainty/heldcommand объяснение и корректная симметрия фильтра.
Математика exactaffinefit/sourcecausality одобрена только read-onlyresearch;
roundedpartition/cap16384/quality/Stop sufficiency этим не доказаны.

**Alternatives considered:** менять .00001,rawclock guard,считать native0
диагностики waveformPASS,внедрить окно безqualityreview или объявить
Parallels единственной причиной не выбрано. Следующий опыт должен опираться
на обнаруженный временной остаток,не произвольный перебор настроек. Source/
hashes/native exits/границы независимогоreview — validation194–196; noadoption.

## Раунды197–199 — до-EOS bias и constant-period interval probe

**Decision:** runtime не принимать. Actual received-fit/native-position trace
показал расхождение ещёнаopen stream;holdTail только сохраняет/увеличивает его.
Простейшее пересечениеperiod bounds отпринятыхquantized anchors сократило
132matrix до1FAIL при прежнем .00001,ноconstantperiod/exactfirst/.5tick
premises относятсякгенератору,неWASAPI. Это не новыйузкийцелевойпродукт.

**Rationale:** point interpolation treats разныеrounded anchor sets какточную
геометрию,давая небольшойbias даже без потерикадров. Interval model сохраняет
полученные ограничения вдвухчислах инеиспользуетfixturetruth;разныеfeasible
intervals всёравноимеют разныеmidpoints. Outward quotient/firstn0/domain guards
и3checks улучшили численнуюзащиту,неубралипоследнийwaveformFAIL. Исходный
синтаксическийcompilefail сохранён;fixedsourceconditionalreview неhardwareproof.

**Alternatives considered:** увеличитьtolerance/gainhorizon,обвинитьтолькоEOS,
подменить noisy/changingWASAPI clock идеальнымconstantperiod илисчитать131PASS
полнойматрицейневыбрано. Next:доказатьclockuncertainty/неизвестное начало и
совместимость exactcontinuousmapping,затемquality/kernel/lifetime/Stop/custody.
Details/sourcepremises/exits/fingerprints — validation197–199.

## Раунды200–202 — симметрия фильтра и границы идеальных часов

**Decision:** симметричный native window prototype остаётся исследовательским;
constant-period/exact-first вариант не выбирать общим решением для устройств.

**Rationale:** окно с центром16+fraction и поддержкой[1,31] прошло5445 native
coefficient/endpoint checks, но прежняя Fit matrix сохраняет5/132 FAIL.
Девять generated quality/physical случаев именно нового EXE дали18/18 PASS
с actual AEC,0/±.8ms noise; полного спектра и переменных packet boundaries
это не доказывает. Четыре metadata-only примера, все принятые actual mapper,
обнуляют пересечение ideal affine bounds при неизвестной первой дроби,
first-only measurement error, changing rate и шуме. Одного численного
расширения outward quotient для реальных часов недостаточно.

**Alternatives considered:** сохранять смещённое окно31, увеличить .00001,
поменять raw guard или объявить частный quality PASS общей приёмкой не выбрано.
Следующий проект — общий causal clock расчёт с неизвестной первой опорой и
изменением частоты; реальные требования, bounded memory и Stop сохраняются.
Source/VM verdicts/failure history/fingerprints — validation200–202.
