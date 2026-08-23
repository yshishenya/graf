# Feature Specification: Windows desktop-приложение GRAF

**Feature Branch**: `200-windows-desktop-app`

**Created**: 2026-08-23

**Status**: Draft

**Input**: Пользователь просит разработать Windows-версию GRAF, максимально
идентичную macOS-приложению: серверный web-кабинет загружается внутри desktop
shell, а запись звука, управление, разрешения и локальная сохранность остаются
нативными.

## Контекст и цель

Windows-клиент должен дать пользователю тот же продуктовый сценарий, что и
macOS-клиент: открыть кабинет, начать/поставить на паузу/остановить запись,
видеть честное состояние, сохранить запись локально и автоматически передать её
в GRAF. Веб-кабинет не должен дублироваться отдельной Windows UI-реализацией, а
нативная часть не должна передавать удалённой странице контроль над аудио,
файлами, разрешениями или локальной очередью.

Рабочее решение для первого Windows-среза: Windows пишет общий микс звука устройства
вывода через системный WASAPI loopback и отдельный физический микрофон. Это не
изоляция звука конкретного приложения: во время активной сессии в запись может
попасть любой звук, который Windows выводит на выбранное устройство. Автозапись
по подтверждённому приложению только запускает видимую сессию; она не является
фильтром аудиопотока.

## User Scenarios & Testing

### User Story 1 - Записать встречу с нативным управлением (Priority: P1)

Как пользователь GRAF на Windows, я хочу открыть знакомое приложение, начать
запись, видеть её состояние и одним действием остановить, чтобы не зависеть от
доступности веб-кабинета во время встречи.

**Why this priority**: Запись и доверие к её состоянию — основной продуктовый
сценарий. Если web-страница зависла или сеть исчезла, пользователь всё равно
должен сохранить встречу и остановить захват.

**Independent Test**: Запустить Windows shell с недоступным кабинетом, дать
разрешения, выполнить Record/Pause/Resume/Stop и проверить локальный пакет,
индикатор и отсутствие обычной записи без готового захвата.

**Acceptance Scenarios**:

1. **Given** нативный shell запущен, а WebView не загрузился, **When** разрешения
   и локальное хранилище готовы, **Then** Record и локальный индикатор остаются
   доступны, а ошибка WebView не блокирует запись.
2. **Given** активна запись, **When** пользователь нажимает Stop в shell или
   tray-индикаторе, **Then** все источники останавливаются, trusted timeline
   закрывается, локальный пакет финализируется, а состояние меняется на честное
   сохранённое/ограниченное/ошибочное.
3. **Given** активна запись, **When** WebView перезагрузился, закрылся или
   перешёл на страницу входа, **Then** native indicator и Stop не исчезают и не
   передают управление странице.

### User Story 2 - Работать с тем же кабинетом, что и на macOS (Priority: P1)

Как пользователь, я хочу видеть тот же серверный кабинет, встречи, настройки,
review и deletion-report, чтобы Windows не стал отдельным продуктом с расходящейся
логикой и копией UI.

**Why this priority**: Единая web-версия сокращает расхождение поведения и
оставляет бизнес-правила на сервере.

**Independent Test**: Открыть `/desktop/meetings`, detail, settings и auth
recovery в Windows WebView2 и в обычном браузере; сравнить route/state matrix,
русский текст, focus/keyboard states и отсутствие native-only controls в HTML.

**Acceptance Scenarios**:

1. **Given** WebView2 runtime доступен и пользователь авторизован, **When** shell
   открывает кабинет, **Then** он загружает тот же origin `https://rec.2brain.pro`
   и desktop routes, что и macOS shell.
2. **Given** страница пытается перейти на неизвестный origin или native-only
   route, **When** route policy оценивает переход, **Then** переход блокируется или
   открывается в обычном браузере без изменения capture/local state.
3. **Given** пользователь перемещается по кабинету, **When** native shell
   получает route/load failure, **Then** он показывает bounded offline/auth/error
   state, а не подменяет серверный кабинет второй локальной встречной лентой.

### User Story 3 - Не потерять локальную запись и догрузить её после сбоя (Priority: P1)

Как пользователь, я хочу, чтобы запись сначала надёжно сохранялась на диске, а
потом автоматически отправлялась в GRAF, чтобы перезапуск, отсутствие сети,
ошибка авторизации или закрытый WebView не уничтожили результат встречи.

**Why this priority**: Локальная custody и повторяемая загрузка — часть доверия к
записи и уже принятый контракт macOS.

**Independent Test**: Завершить запись offline, перезапустить приложение,
восстановить сеть и авторизацию через WebView; проверить возобновление upload по
серверной truth без дублирования meeting/upload session.

**Acceptance Scenarios**:

1. **Given** запись остановлена при отсутствии сети, **When** приложение
   перезапускается и сеть появляется, **Then** локальный пакет остаётся в
   `desktop-upload-queue.v2` и автоматически продолжает передачу.
2. **Given** часть байтов уже принята сервером, **When** upload возобновляется,
   **Then** native client использует подтверждённые диапазоны и не создаёт второй
   server meeting из-за повторного запуска.
3. **Given** локальная запись не прошла integrity gate, **When** queue её
   проецирует в UI, **Then** она не выдаётся за нормальную готовую встречу и
   показывает только metadata-safe причину и доступное действие.

### User Story 4 - Получить честный результат при ограничении Windows-аудио (Priority: P1)

Как пользователь, я хочу понимать, что именно записалось, если микрофон,
устройство вывода, Windows privacy, sleep/wake, exclusive-mode приложение или
защищённый DRM-поток помешали захвату, чтобы GRAF не показывал ложную уверенность.

**Why this priority**: Неполная или рассинхронизированная запись хуже явной
ошибки. Capture integrity — high-risk boundary.

**Independent Test**: В тестовой матрице отключать разрешение микрофона,
вынимать endpoint, менять default device, уводить машину в sleep, отдавать
protected audio и инжектировать разрыв clock; проверять fail-closed state,
постоянный Stop и metadata-only diagnostics.

**Acceptance Scenarios**:

1. **Given** Windows microphone privacy или выбранное устройство не готово,
   **When** пользователь нажимает Record, **Then** запись не стартует как
   нормальная и предлагает восстановить разрешение/устройство.
2. **Given** WASAPI сообщает invalidated endpoint, разрыв timestamp или overflow,
   **When** trusted capture segment больше нельзя продолжать, **Then** текущий
   сегмент завершается как degraded/failed, без raw-microphone fallback и без
   тихого склеивания разных clock domains.
3. **Given** loopback не содержит protected audio, **When** пользователь
   завершает сессию, **Then** manifest отражает ограничение и не заявляет, что
   защищённый звук был записан.

### User Story 5 - Пользоваться автоматической записью так же, как на macOS (Priority: P2)

Как пользователь, я хочу включать автозапись только для подтверждённых Windows
meeting-приложений с обратимой настройкой и видимым countdown, чтобы запись не
запускалась от музыки, видео или произвольного системного звука.

**Why this priority**: Это защищённая продуктовая capability macOS; Windows не
должен снижать порог согласия ради простоты интеграции.

**Independent Test**: В тестовом registry зарегистрировать и удалить target,
проверить настройки, prompt, `Записать сейчас`, `Пропустить`, timeout и
`Всегда писать это приложение`, включая отказ в разрешении.

**Acceptance Scenarios**:

1. **Given** обнаружен verified Windows target без сохранённого разрешения,
   **When** пользователь видит prompt, **Then** появляется тот же восьмисекундный
   countdown с явными `Записать сейчас`, `Пропустить` и `Всегда писать это
   приложение`.
2. **Given** пользователь сохранил разрешение для точной identity target,
   **When** этот target обнаружен снова, **Then** автозапуск проходит через все
   capture prerequisites и оставляет persistent indicator/one-action Stop.
3. **Given** обнаружено неизвестное имя процесса или обычное media playback,
   **When** detector оценивает событие, **Then** запись не запускается и target не
   добавляется в allowlist догадкой.

## Edge Cases

- WebView2 отсутствует, повреждён или его runtime ниже минимальной проверенной
  версии: native capture/local custody не ломаются; кабинет получает bounded
  runtime-unavailable state и инструкцию восстановления.
- Кабинет недоступен, auth-сессия истекла, route malformed или сервер вернул
  401/403/409/429/503: native queue сохраняет локальную truth и retry policy.
- Нет default render endpoint, endpoint занят exclusive mode, устройство
  отключилось, default endpoint сменился или Windows Audio Service перезапустил
  поток: текущий trusted сегмент не продолжается молча.
- Микрофон запрещён глобальной privacy-настройкой, выбранный input исчез,
  формат не поддерживает целевую конфигурацию или пользователь отключил input:
  Record блокируется или session становится явно degraded.
- Система уходит в sleep/modern standby, возвращается с другим device/clock или
  приложение получает suspend/termination: writer делает bounded recovery и не
  подменяет отсутствующие frames wall-clock padding.
- Render loopback возвращает тишину из-за protected/DRM-контента: состояние и
  manifest говорят об ограничении, а не о полноценной записи.
- Callbacks приходят не блоками 10 ms, с разным размером или с jitter:
  callbacks только публикуют timestamped batches; единственная timeline делает
  canonical 480-sample framing.
- Диск заполнен, файл нельзя атомарно закрыть, manifest повреждён или очередь
  записана частично: сохранённые байты не перезаписываются пустым ledger,
  документ quarantine-ится metadata-safely.
- Windows N не имеет нужного Media Foundation AAC encoder: installer/runtime
  readiness сообщает несовместимость до нормальной записи или сохраняет только
  проверенный degraded artifact по явно согласованному контракту; нормальная
  запись с отсутствующим playback artifact не заявляется.
- Приложение закрывается дважды, Stop нажимается во время старта/финализации или
  user запускает два потока одновременно: действует один idempotent session и
  одна очередь writer.
- High Contrast, DPI 200%, narrow window, keyboard-only, screen reader и
  Reduce Motion не скрывают indicator, Stop, permission state или важное
  degraded сообщение.

## Out of Scope

- Process-isolated loopback, запись только Zoom/Teams/браузера, включение или
  создание `Stereo Mix`, виртуального аудиодрайвера, отдельной routing-системы,
  kernel component или driver installer.
- DRM bypass, обход Windows privacy, запись без видимого пользовательского
  контроля, запись в elevated/system process или service.
- Новая серверная meeting-list UI, отдельная Windows web frontend-копия,
  прямой доступ desktop клиента к MediaScribe/MinIO и хранение server secrets в
  клиенте.
- Изменение утверждённых macOS capture semantics, manifest v5 и server upload
  lifecycle без отдельной совместимой миграции.
- Browser extension, bot/participant joining, calendar provider integration,
  удалённое управление записью и скрытая запись от произвольного процесса.
- Автоматическая публикация в Microsoft Store, release/deploy и production
  rollout до отдельного release approval.

## Requirements

### Functional Requirements

- **FR-001**: Windows client MUST support Windows 10 22H2 (build 19045) and
  supported Windows 11 releases on x64; ARM64 MUST be built and tested before
  claiming ARM64 support. The app MUST NOT depend on a preview Windows SDK or
  preview Windows App SDK API. The exact Windows 11 build set and stable SDK/
  WebView2 versions MUST be recorded in the implementation lock/matrix before
  any Windows support or performance claim is made.
- **FR-002**: The product MUST preserve the macOS user-visible semantics for
  Record, Pause, Resume, Stop, recording states, permission recovery, local
  custody, upload status, auth recovery and deletion truth. OS-native window and
  tray conventions MAY differ only where Windows has no equivalent macOS surface.
- **FR-003**: The client MUST load the server-owned cabinet from the configured
  approved HTTPS origin, with production default
  `https://rec.2brain.pro/desktop/meetings`, and MUST NOT duplicate meeting list,
  detail, settings or review business logic in native Windows UI.
- **FR-004**: Native code MUST own audio capture, capture readiness, permission
  recovery, local recording files, local upload custody, diagnostics, persistent
  indicator and one-action Stop independently of WebView availability.
- **FR-005**: WebView navigation MUST be limited to exact approved route kinds on
  the configured origin. Unknown origins, arbitrary file URLs, local paths and
  native-only routes MUST be rejected or opened externally without mutating
  local state.
- **FR-006**: Native↔WebView communication MUST use a versioned JSON envelope,
  validate source origin, schema, session nonce, command and payload before
  acting, and MUST expose no generic host object or arbitrary script bridge.
- **FR-007**: The Feature 200 baseline system track MUST use WASAPI shared-mode loopback on the
  current/default render endpoint and MUST NOT require `Stereo Mix`, a hardware
  loopback device, a virtual driver or exclusive mode.
- **FR-008**: The Feature 200 baseline microphone track MUST use a user-selected or approved
  default physical capture endpoint through WASAPI shared mode. Windows
  microphone privacy and endpoint readiness MUST be explicit prerequisites.
- **FR-009**: Native capture MUST publish timestamped batches into one bounded
  timeline. The timeline MUST normalize to 48 kHz mono, process exact 10 ms /
  480-sample pairs through the pinned GRAF WebRTC AEC3 C ABI, and MUST own
  ordering, gaps, route generations and final framing.
- **FR-010**: AEC3 reference processing MUST receive the render/system frame
  before the microphone frame. Processor failure, missing reference, invalid
  samples, untrusted timestamps, route change or overflow MUST never fall back to
  an untreated raw microphone track or present the result as normal.
- **FR-011**: A normal finalized package MUST remain compatible with macOS v5
  custody: one canonical ASR WAV (PCM signed 16-bit little-endian, 16 kHz,
  mono), one playback M4A (AAC-LC, 48 kHz, mono), manifest metadata and the
  existing accepted track/queue roles. WAV/M4A/timeline duration difference MUST
  be no more than 100 ms for a normal package.
- **FR-012**: Local recordings MUST be written below the user-scoped Windows
  application-data directory with user-only ACLs, temp-file plus atomic-rename
  finalization, bounded flush/error handling and no credentials, cookies, raw
  transcript or raw audio in diagnostics.
- **FR-013**: The Windows queue MUST reuse `desktop-upload-queue.v2` semantics and
  preserve immutable local identity, server truth, accepted ranges, retry records,
  retention and conflict state. It MUST quarantine malformed ledgers rather than
  replacing them with an empty queue.
- **FR-014**: Upload MUST go only through existing GRAF desktop APIs; the client
  MUST never send audio directly to MediaScribe or store MediaScribe credentials.
  Upload MUST resume after launch, activation, auth recovery, network recovery,
  wake and scheduled retry without the WebView route being open.
- **FR-015**: Active capture MUST have a persistent native visible status and a
  one-action Stop reachable from the main shell and the Windows background/tray
  surface. WebView failure, minimization or focus changes MUST NOT hide Stop.
- **FR-016**: Target-scoped automatic recording MUST use verified Windows target
  identity, explicit reversible settings, the existing countdown/prompt actions,
  capture prerequisites, visible indicator and Stop. It MUST NOT infer a target
  from arbitrary process names or start for arbitrary system/media playback.
- **FR-017**: Endpoint change, sleep/wake, audio-service interruption and
  protected-audio limitation MUST transition through explicit states with
  metadata-safe reason codes and recovery action. Silent cross-device continuation
  is forbidden for the first release.
- **FR-018**: Audio timestamps MUST use a monotonic QPC/WASAPI clock mapping and
  validate monotonicity, clock domain and drift. Wall-clock arrival time MUST NOT
  be used to invent missing audio or align independent streams.
- **FR-019**: WebView2 and native host MUST run as a standard user process. No
  driver, service, system/elevated process or privileged audio component may be
  required for the Feature 200 baseline.
- **FR-020**: The distributable MUST validate WebView2 Evergreen availability,
  Windows App SDK dependencies, package signature, architecture and rollback
  behavior before installation can be claimed as ready. WebView2 must be restored
  or installed by the supported installer path, not by silently switching to an
  arbitrary Edge browser.
- **FR-021**: Native diagnostics and committed evidence MUST contain only bounded
  metadata: version, platform, state, safe reason code, counts, durations and
  redacted device identity. They MUST NOT contain raw audio, transcript text,
  credentials, cookies, signed URLs, private meeting content or live private
  paths.
- **FR-022**: Windows deletion and local purge behavior MUST use the existing
  GRAF lifecycle truth and MUST acknowledge local purge only after deletion,
  tombstone or cryptographic unrecoverability has been verified.

### Key Entities

- **WindowsDesktopSession**: one native capture session with id, state, start/stop
  times, target evidence, permission snapshot, route generations and finalization
  result.
- **WasapiEndpointSnapshot**: stable device id hash, data-flow role, format,
  channel/sample rate, default/selected status, availability and route generation.
- **RecordingAudioBatch**: bounded mono/float sample batch with source role,
  sample count, monotonic presentation timestamp, clock domain, format and
  discontinuity marker.
- **RecordingAudioTimeline**: one trusted ordering/alignment owner with bounded
  source buffers, AEC3 processing counters, drift/drop/gap state and canonical
  output framing.
- **LocalRecordingPackage**: user-scoped directory containing manifest, canonical
  ASR artifact, review playback artifact, hashes, byte counts and integrity state.
- **UploadCustodyItem**: queue projection over the existing v2 ledger with local
  identity, server truth, retry owner/action, accepted ranges and retention state.
- **WebViewBridgeEnvelope**: version, message id, session nonce, origin-bound
  direction, command/event name, bounded payload and acknowledgement/error.
- **VerifiedTargetIdentity**: exact Windows target evidence used by auto-record
  policy, including approved executable identity and registry version; process
  name alone is insufficient.

## Success Criteria

### Measurable Outcomes

- **SC-001**: On a reference Windows 10 22H2 and Windows 11 x64 machine, native
  shell and local Record readiness are available within 2 seconds after launch
  when permissions/storage are ready, independently of web/network state. A
  healthy cabinet loads its approved route within 15 seconds.
- **SC-002**: The parity matrix covers every macOS recording state, native action,
  permission state, upload custody state and cabinet route in scope; 100% of
  mandatory cases have matching user-visible meaning and no duplicate native/web
  ownership.
- **SC-003**: In a 60-minute synthetic/reference capture with source clocks at
  ±100 ppm, there are no dropped or duplicated output frames, WAV/M4A/timeline
  duration difference is at most 100 ms, and the system-audio component level
  differs by no more than 1 dB from the reference run. The level is the
  integrated RMS dBFS of the canonical 48 kHz mono system-render component over
  the same active synthetic interval, measured before the final mix.
- **SC-004**: 100% of active-capture fault injections keep a visible native
  indicator and one-action Stop, and 100% of permission, endpoint, clock,
  protected-audio and overflow failures avoid normal-status claims and raw-mic
  fallback.
- **SC-005**: Across 100 offline/relaunch/auth-recovery/wake upload cycles, local
  packages remain recoverable and no duplicate server meeting or upload session
  is created when server truth is available.
- **SC-006**: Security tests reject every message from an unapproved origin,
  invalid schema/nonce/command or oversized payload in the bridge matrix; no
  secret or content-bearing field appears in metadata-only diagnostics.
- **SC-007**: Automated-recording tests produce distinct outcomes for immediate
  start, skip, countdown timeout and saved target policy; unknown targets produce
  zero automatic starts.
- **SC-008**: Install, update, uninstall and rollback on supported x64 test
  images preserve authenticated web profile policy, local queue and recordings;
  a missing WebView2 runtime produces a recoverable bounded state.
- **SC-009**: Keyboard-only, screen-reader, high-contrast, 200% DPI, narrow
  window and reduced-motion checks retain visible focus, readable state, target
  size, indicator and Stop without horizontal overflow or color-only meaning.
- **SC-010**: Before ARM64 support is advertised, the same capture, writer, AEC3,
  WebView boundary, installer and rollback gates pass on an ARM64 Windows image;
  otherwise the release explicitly remains x64-only.

## Assumptions

- Existing server cabinet routes, authentication, desktop upload APIs, v5
  manifest and deletion contracts remain the source of truth; this feature does
  not fork server UI or invent a Windows-only API.
- The first Windows release targets a user-installed desktop app and standard
  user context. No enterprise driver, system service or admin elevation is
  required.
- Windows App SDK stable, WebView2 Evergreen Runtime, WASAPI, Media Foundation
  and the Windows SDK are available through a supported build/installer lane.
- Microsoft AAC encoder is available on supported Windows editions. Windows N
  is not part of the initial supported claim until its Media Feature Pack/AAC
  gate passes; otherwise the installer must exclude it and a normal
  playback-ready package must not be claimed there.
- The existing pinned WebRTC AEC3 dependency and its narrow C ABI remain the
  algorithmic contract; a Windows build must prove identical configuration and
  license provenance before implementation uses it.
- A healthy network is not required to begin or finish local recording; it is
  required only for server cabinet/authentication and upload progress.
- Product-owner approval is still required before implementation commits,
  release packaging or production distribution.

## Clarifications

### Session 2026-08-23

- Q: Which Windows render-capture scope is in the first slice? → A: Full default render mix
  through WASAPI shared loopback; process-isolated capture is deferred.
- Q: Which minimum Windows versions are in scope? → A: Windows 10 22H2 and
  supported Windows 11 releases; process-loopback-only builds are not a gate.
- Q: Which part remains native versus web? → A: WebView owns the online cabinet;
  native code owns capture, indicator, permissions, local custody, upload and
  diagnostics.
- Q: What does “identical to macOS” mean? → A: Same product semantics, routes,
  states, copy and safety gates; only unavoidable Windows window/tray conventions
  may differ.
- Q: What is the automatic-recording policy? → A: Preserve target-scoped verified
  identity, visible countdown, explicit opt-in and one-action Stop; never record
  arbitrary system audio by default.
