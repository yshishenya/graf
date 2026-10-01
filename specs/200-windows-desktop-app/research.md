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
