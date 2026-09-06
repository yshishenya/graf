# Implementation Plan: Windows desktop-приложение GRAF

**Branch**: `200-windows-desktop-app` | **Date**: 2026-08-23 | **Spec**:
[spec.md](spec.md)

**Input**: Feature specification from
`/specs/200-windows-desktop-app/spec.md`

## Summary

### Продолжение 2026-09-06

Активный `high-risk-feature` срез продолжается после merge `bb4fc1fac` из
`origin/master` `6ff8db3ee`. Приоритет имеет уточнение в spec.md от 2026-09-06
и Constitution 7: локальная трёхрежимная автозапись, а не прежние checkbox и
server-assisted policy. Требование отличаться от эталона визуально отменено;
проверяются сходство с текущим GRAF macOS, доступность и происхождение ресурсов.

Constitution 7.0.0 и прямое решение владельца продукта снимают прежнее
противоречие внешнего использования: правовая политика и подтверждение
уведомления/согласия не являются условиями записи. В T081/T082 удалить
`ReadinessInputs.recordingPolicyAllowed`, `AutomaticRecordingPrerequisites.consentSatisfied`,
их проверки и неиспользуемые коды/подписи отказа, а не присваивать true.
Обновить все именованные и позиционные инициализации ReadinessInputs,
чтобы удаление bool не сдвинуло смысл оставшихся полей. Проверить Start,
countdown и каждый оставшийся технический отказ; отсутствие WebView/сети
не блокирует захват. Внешние серверные API, данные и Mac-код не меняются.
CHK010 теперь однозначен; перед кодом требуется повторная проверка затронутых
custom checklists и analyze. Это разрешение на реализацию, не готовность выпуска.

Порядок: T080 восстанавливает WebView lifecycle и его повторный запуск;
параллельно T081 нативный shell и T082 трёхрежимная политика с подтверждённым
детектором; T083 сверяет действующие серверные контракты без изменения сервера;
T084 проводит проверку собранного приложения и фиксирует каждый незакрытый путь.
Асинхронные WebView операции возвращаются на UI-поток, отменённое/старое окно
не получает callbacks; ошибка bootstrap отделяется от HTTP/auth/network.
Повторное открытие не стирает WebView профиль, локальные записи или очередь.
Использовать существующие WinUI/native компоненты без нового UI runtime.

Уточнение T083: первоначальное пространство можно получить без изменения
сервера через JSON `GET /desktop/settings/spaces`, затем подтвердить владельца
через `GET /api/v1/auth/me`. Общий Windows WinHTTP transport сохраняет запрет
редиректов и один снимок сессии. Использовать существующий ограниченный JSON
reader для массива и объектов, без новой зависимости или второго HTTP-клиента.
Тестировать именно двухшаговый алгоритм с подменяемым read-only GET: один
активный UUID, строгие типы/дубликаты/лимиты, отказ/отмена до второго запроса,
несовпадение пространства и недействительную сессию. Владелец записи, очередь,
права доступа к серверным данным и полномочия удаления не меняются.

Предыдущие отметки implementation complete не закрывают новые найденные
расхождения и не заменяют T070/T071/T063. Нужны свежая Release-сборка,
portable checks, настоящие окна в Parallels, recovery и контрактные сценарии.
Публичная подпись, physical x64 и отсутствующие устройства остаются отдельными
гейтами. Без разрешения не выполнять production deploy, публикацию или commit
новой реализации. Изменения описывать в `changes/unreleased/F200.yaml`.

Добавить Windows desktop shell, который повторяет product semantics macOS,
загружает существующий серверный кабинет через WebView2 и держит capture/local
custody в native code. Для аудио используется WASAPI shared-mode render loopback
для общего системного микса и отдельный shared-mode microphone endpoint. Оба
потока получают WASAPI/QPC timestamps, проходят одну bounded PTS timeline,
пинованный WebRTC AEC3 и существующий v5 artifact contract.

Feature 200 baseline intentionally does not attempt to isolate Zoom/Teams or
browser audio: process loopback требует более узкой Windows build matrix и
является отдельной будущей
фичей. Веб-кабинет и backend остаются общими; Windows не создаёт вторую web UI
или прямую egress-интеграцию к MediaScribe.

## Technical Context

**Language/Version**: C++17/20-compatible C++/WinRT, WinUI 3, Windows App SDK
stable, Windows SDK; exact stable versions and supported Windows 11 build set
are locked before implementation evidence; PowerShell is used for build/package
validation

**Primary Dependencies**: WinUI 3, Windows App SDK, WebView2 SDK/Evergreen
Runtime, WASAPI/MMDevice, Media Foundation (resampler, AAC encoder, Sink
Writer), pinned static GrafAEC3 C ABI, existing GRAF desktop HTTP contracts

**Storage**: user-scoped `%LOCALAPPDATA%\\GRAF` recording packages and the
existing `desktop-upload-queue.v2` JSON ledger; no new server database or
MediaScribe credential store

**Testing**: native C++ unit/self-checks, WebView2 route/bridge contract tests,
Windows integration/hardware matrix, MSIX install/update/rollback smoke,
repository `infra/scripts/ci-local.sh --fast` before PR

**Risk / Validation Lane**: `high-risk-feature` — new native system-audio and
microphone capture, local buffering/custody, permissions, upload recovery,
WebView trust boundary, tray/indicator and automatic-recording UX

**Release Gate**: `no deploy` — planning and implementation preparation only;
production Windows distribution requires a later signed-package release gate,
hardware evidence and explicit user approval

**Target Platform**: Windows 10 22H2 (19045) and supported Windows 11 releases;
x64 is the first claimable architecture, ARM64 is conditional on its own build
and hardware evidence

**Project Type**: native desktop app with server-owned embedded web cabinet

**Performance Goals**:

- Native shell and local Record readiness within 2 seconds after launch when
  permissions/storage are ready; WebView load has a separate 15-second bounded
  healthy-network target.
- Audio callback paths only drain bounded WASAPI packets and enqueue; no file I/O,
  allocation-heavy UI work, WebView calls or AEC processing from callbacks.
- One bounded queue per source and one timeline owner; overflow is observable and
  fails the normal capture gate instead of growing without limit.
- Initial timeline bounds reuse the active macOS defaults: 48,000-frame reorder
  window, 15-second known-gap limit, 960,000 buffered frames per source and
  48-frame clock recovery budget per batch; Windows may change them only with
  synthetic memory/latency evidence.
- 60-minute ±100 ppm reference run has no dropped/duplicated output and at most
  100 ms WAV/M4A/timeline duration difference.
- The same reference run has no sustained CPU runaway: after warm-up, native
  process CPU time is at most 25% of wall time on the reference four-core x64
  machine, resident memory growth is at most 128 MiB, and bounded source queues
  do not grow without limit.

**Constraints**:

- system-audio-first product boundary; no virtual driver, `Stereo Mix`, kernel
  route, exclusive capture or elevated process;
- persistent native indicator and one-action Stop even if WebView is offline,
  minimized or reloading;
- no raw microphone fallback after AEC/timeline integrity failure;
- exact-origin, allowlisted, JSON-only WebView bridge with no generic host objects;
- same v5 manifest/artifact/queue semantics as macOS;
- metadata-only diagnostics/evidence and server-owned credentials;
- implementation commits are allowed only after focused validation and explicit
  user approval; this slice still has no deploy, public release or Store claim.

**Scale/Scope**: one Windows app process, one active recording session per user,
two source streams, multiple pending local packages, current GRAF owner/workspace
server path, x64 first with an explicit ARM64 gate

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Status | Plan response |
|---|---|---|
| Capture-first Feature 200 integrity | PASS WITH EVIDENCE GATE | Separate Windows native stack uses WASAPI shared loopback + explicit mic; retired/virtual routing is not revived. Implementation is blocked until clock, dropout, endpoint and hardware evidence exists. |
| Visible capture and user control | PASS | Constitution 7 excludes legal/notice prerequisites; native permissions, indicator/Stop, countdown, local three-state choice and verified targets remain required. |
| Data boundary and secret discipline | PASS | Desktop uses GRAF APIs only; WebView receives bounded state, not files/tokens/handles; MediaScribe credentials remain server-side. |
| Deletion truth and lifecycle accounting | PASS | Windows local package/queue/purge use existing custody and deletion semantics; no universal-erasure promise is added. |
| Spec-driven delivery with testable gates | PASS | New feature has spec, clarification, research, data model, contracts, checklists, quickstart, tasks and analyze gate before implementation. |
| Clean-room UX/accessibility | PASS WITH DESIGN GATE | Web cabinet is reused; native Windows strip/tray mirrors semantics and requires keyboard, screen-reader, DPI/high-contrast and brand-distance review. |
| Platform/deployment safety | PASS WITH RELEASE GATE | Packaged Windows App SDK + signed MSIX + WebView2 Evergreen are planned; installer/rollback/signature evidence is required before distribution. |
| Ponytail ceiling | PASS | Native platform APIs, existing v5/queue contracts and pinned AEC C ABI are reused; no second UI framework, driver or transport is introduced. |

**Post-design re-check**: PASS WITH EVIDENCE GATES. Phase 1 artifacts preserve
the native/web boundary, but no code claim is made until Windows hardware,
package and fault-injection evidence is produced.

**Second analysis re-check (2026-08-24)**: PASS WITH EVIDENCE GATES. The parity
matrix points to the actual macOS `Upload`/`Cabinet` source paths, the v5
contract pins `local-recording-manifest.v5`, `canonical-mix.v1`,
`initial_mixed_recording`, `single_wav_v1` and `manifest/media/playback`, and
the native bridge contract now matches the implemented numeric message-id,
nonce and command envelope. The 22 functional requirements and 10 buildable
success criteria remain covered by 76 ordered tasks; T065–T069 and T072–T076
have an implementation slice, while T070/T071 and the Windows hardware,
package and release evidence remain open. This is a consistency result, not
Windows hardware, package or release evidence.

**Local implementation re-check (2026-08-25)**: PASS. The portable slice now
propagates privacy Pause into the timeline, treats WASAPI data discontinuity and
timeline/egress integrity failures as fail-closed, uses the macOS-compatible
`directoryId--initial` revision and Russian native status copy. The upload
transport now reconciles `sync-state`, resumes server ranges, verifies accepted
offsets and handles expired sessions with a fresh idempotency scope. CMake/CTest
passes 20/20 and `infra/scripts/ci-local.sh --fast` passes 1240 tests plus lint;
Windows Release MSBuild, pinned AEC3 build (440/440), WebView2 runtime launch
and native app smoke passed in the VM. Hardware and signed-package evidence
remain intentionally unclaimed under T070/T071.

**Native capture hardening re-check (2026-08-25)**: PASS for the portable
contract surface. `WasapiCaptureWorker` now waits for successful WASAPI startup,
uses the runtime `QueryPerformanceFrequency` for `ClockMapper`, rejects
unsupported/non-finite samples instead of synthesizing silence, and reports
worker faults to the session finalizer. The v5 writer removes partial artifacts
when either WAV or playback encoding fails and publishes both artifacts only
after their temporary files are complete. CMake/CTest remains 20/20 PASS;
Windows MSBuild, pinned AEC3 binding and resampling implementation are now
host-built; hardware and signed-package evidence remain open.

**Host validation re-check (2026-08-30)**: PASS WITH EVIDENCE GATES. After
MSBuild restore, the current dirty worktree builds `GrafWindows.sln` and the
native `GrafWindowsApp.exe` in Release x64 with the pinned AEC3 adapter; a
fresh Windows CMake/Ninja configure/build passes 20/20 CTest, synthetic audio
passes 2/2, custody passes 3/3 and WebView boundary passes 4/4. The pinned
AEC3 checkout builds 440/440, and the app launches as `GRAF` and loads the
server-owned auth cabinet. The `.wapproj` now forms an unsigned x64 test MSIX;
static package smoke checks its manifest, entry point, capabilities and
embedded signing certificate. The cabinet is unauthenticated, and trusted
release signing, hardware capture and clean-image package evidence remain open.
This is host evidence for the dirty worktree, not a release claim.

## Architecture

```text
apps/windows/RecApp (WinUI 3 / C++/WinRT, standard user)
├── Shell/              native shell, status strip, tray, keyboard focus
├── Web/                WebView2 host, route policy, JSON bridge
├── Permissions/       microphone/privacy/storage/WebView readiness
├── Capture/            session state, start/stop/pause/resume, power recovery
├── Audio/              WASAPI endpoints, timestamps, normalizers, timeline
├── Recording/          v5 manifest, WAV/M4A writers, integrity checks
├── Upload/             v2 queue projection and existing GRAF HTTP client
├── MeetingDetection/   verified target registry and auto-record policy
└── Diagnostics/        bounded metadata and safe reason codes

apps/windows/Native/GrafAEC3/  pinned static C ABI build and license notices
apps/windows/Tests/            core/contract/integration test targets
apps/windows/Installer/        MSIX/MSIXBundle/App Installer metadata
apps/windows/scripts/          reproducible build, validation and smoke scripts
```

### Source ownership

The Windows app owns Windows-native code and platform packaging. Existing server
cabinet routes/templates and macOS capture code are not copied into the native
client; a separately approved shared cabinet parity fix may update the common
server template/static contract, as in the profile-menu/quit marker slice here.
The server remains the owner of authentication, meetings, review, deletion,
MediaScribe and server-side processing.

### Audio pipeline

```text
WASAPI render loopback ─┐
                        ├─ timestamped bounded batches
WASAPI microphone ──────┘
          ↓ endpoint normalizers (actual device format → 48 kHz mono float)
          ↓ one PTS/route-generation RecordingAudioTimeline
          ↓ 480-sample frames: AEC3 reference → AEC3 microphone
          ↓ canonical mix
          ├─ PCM S16LE 16 kHz mono WAV (ASR)
          └─ AAC-LC 48 kHz mono M4A (review)
          ↓ v5 manifest + desktop-upload-queue.v2
          ↓ existing GRAF desktop upload/reconcile API
```

### WebView ownership

WebView2 loads the existing `/desktop/...` cabinet. Native code supplies only
bounded status and receives only allowlisted intents. Route policy rejects unknown
origins, file/local routes, capture/local-file/permission mutation attempts and
stale nonce messages. WebView cannot be the only place where active capture state
or Stop is visible.

## Implementation phases

### Phase 0 — Research and platform proof

1. Lock current stable Windows App SDK/WebView2 SDK/compiler versions and the
   supported Windows 11 build set in `apps/windows/Directory.Packages.props` and
   `specs/200-windows-desktop-app/parity-matrix.md` before implementation claims.
2. Build a throwaway/isolated WASAPI proof for render loopback, microphone,
   packet timestamps, endpoint invalidation and Media Foundation AAC/M4A.
3. Build the pinned GrafAEC3 C ABI for x64 and verify license/source identity;
   test ARM64 before advertising it.
4. Capture the hardware matrix and decide the Windows N/Media Feature Pack
   support line.

### Phase 1 — Native foundation and shared contracts

1. Create the Windows App SDK packaged solution, runtime dependency and standard
   user app lifecycle.
2. Port only shared value contracts needed for v5 manifest, upload custody,
   safe errors and session states; do not port macOS Swift UI or server business
   logic.
3. Add metadata-safe diagnostics, file protection, atomic JSON ledger and one
   active-session invariant.
4. Add the parity matrix and exact source/route ownership map against macOS
   Features 057/058/177/193/194/197.

### Phase 2 — Capture engine and integrity gates

1. Implement endpoint enumeration/selection and WASAPI event-driven workers.
2. Implement timestamp mapping, route generations, normalizers, bounded queues
   and one timeline with exact 10 ms AEC3 framing.
3. Implement canonical writers, AAC Sink Writer, v5 manifest and fault states.
4. Validate synthetic partition/clock/gap/overflow cases before any polished UI.

### Phase 3 — Native shell, indicator and permissions

1. Implement Record/Pause/Resume/Stop state machine and readiness surface.
2. Implement native recording strip, tray indicator, keyboard focus and one-action
   Stop outside WebView.
3. Implement microphone privacy/device recovery, sleep/wake and endpoint-change
   states.
4. Match macOS state/copy/accessibility semantics and run clean-room review.

### Phase 4 — WebView2 cabinet and custody bridge

1. Implement exact-origin navigation policy and WebView2 Evergreen readiness.
2. Implement versioned JSON bridge handshake, nonce, payload limits and bounded
   state events; test malformed/stale/untrusted messages.
3. Reuse existing GRAF upload/reconcile semantics and run custody independently
   of the WebView route.
4. Verify auth expiry, offline, reload, login and review/deletion-report routes.

### Phase 5 — Target-scoped automatic recording

1. Port the verified target registry contract to Windows exact identities.
2. Implement settings, prompt countdown, immediate start, skip and persistent
   opt-in with the same Russian product semantics.
3. Validate that unknown processes, media playback and missing prerequisites do
   not start capture.

Уточнение T081/T082 от 2026-09-06: использовать существующий CompactOverlay,
подготовив его скрытым вместе с нативной кнопкой Stop. Готовность автоматического
старта не зависит от IsIconic/IsWindowVisible главного окна; непосредственно
перед capture отдельное окно должно действительно стать видимым. Не создавать
ещё один индикатор, фоновую службу или UI runtime.

Перенести слежение за жизненным циклом авто-записи из AppMain в существующую
AutomaticRecordingPolicy, без нового контроллера. Включать слежение сразу после
принятого `starting`, не только после `recording`; ручные Record/Stop/Exit
отменяют его. Продолжение связано с той же проверенной идентичностью приложения,
не с одним PID. Сохраняется 15 секунд подтверждённого отсутствия; как в текущем
macOS `stopStaleMeetingDetectionRecordingIfNeeded`, 600 секунд без положительного
подтверждения завершают авто-запись. Freshness 2 секунды, монотонный порядок и
повторные снимки проверяются отдельно. Удалить заменённые pending/active/absence
поля AppMain и дублирующую логику. Сначала детерминированные тесты в существующем
AutomaticRecordingSmokeTests, затем Windows Release и нативная проверка окна.
Каталог и миграция предпочтений остаются отдельными незакрытыми частями T082;
синтетические идентичности не добавлять в рабочий реестр.

### Phase 6 — Packaging and release readiness

1. Build signed x64 MSIX/MSIXBundle, WebView2 runtime repair path and update
   migration; preserve queue/recording data across versions.
2. Run install/update/interrupted-update/rollback/uninstall and Windows security
   checks on clean images.
3. Run feature quickstart, Windows hardware matrix and repository fast lane;
   stop before release/deploy until separately approved.

## Validation Plan

1. Run `quickstart.md` on Windows x64 for core unit/contract checks, synthetic
   audio, WebView security and package smoke.
2. Run hardware matrix on Windows 10 22H2 and supported Windows 11 with built-in,
   USB, Bluetooth, HDMI/DisplayPort, dock and RDP conditions where supported.
3. Run focused C++/WinUI tests for timeline/AEC, writer/integrity, queue
   idempotency, endpoint recovery, bridge origin/nonce and auto-record policy.
4. Run MSIX install/update/rollback and WebView2 missing/repair checks on clean
   x64 images; run ARM64 only if that architecture is in the release claim.
5. Run `infra/scripts/ci-local.sh --fast` from the repository before PR. This
   repository gate does not replace the Windows host build or hardware evidence.
6. Do not run `cd-remote.sh`, production deployment, public release preparation
   or Microsoft Store publication in Feature 200 planning/implementation without
   explicit approval and a separate release candidate.

## Project Structure

### Documentation (this feature)

```text
specs/200-windows-desktop-app/
├── spec.md
├── clarify.md
├── plan.md
├── research.md
├── data-model.md
├── parity-matrix.md
├── quickstart.md
├── contracts/
│   ├── windows-desktop-contract.md
│   └── windows-native-web-bridge.md
├── checklists/
│   ├── requirements.md
│   ├── audio-capture.md
│   ├── advanced-routing.md
│   ├── security.md
│   └── ux.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/windows/
├── Directory.Build.props
├── Directory.Packages.props
├── GrafWindows.sln
├── RecApp/
│   ├── App/
│   ├── Shell/
│   ├── Web/
│   ├── Permissions/
│   ├── Capture/
│   ├── Audio/
│   ├── Recording/
│   ├── Upload/
│   ├── MeetingDetection/
│   ├── Diagnostics/
│   └── Resources/
├── Native/GrafAEC3/
│   ├── include/GrafAEC3.h
│   ├── src/GrafAEC3.cpp
│   ├── upstream.lock
│   └── notices/
├── Tests/
│   ├── GrafWindowsCoreTests/
│   ├── GrafWindowsContractTests/
│   └── GrafWindowsPackageTests/
├── Installer/
│   ├── Package.appxmanifest
│   ├── GrafWindows.Package.wapproj
│   └── AppInstaller/
└── scripts/
    ├── build-graf-aec3.ps1
    ├── validate-audio-contract.ps1
    ├── validate-webview-boundary.ps1
    └── validate-package-smoke.ps1
```

**Structure Decision**: keep one Windows native solution with feature folders,
one native C ABI for AEC3 and one test surface for platform-independent core
logic. Do not create a second web application, a driver project or a server
database migration. Shared server contracts are consumed through the existing
desktop APIs; any required server change must be a separately reviewed contract
slice.

## Latest implementation re-check (2026-08-30)

The Windows convergence slice now loads the existing cabinet through WebView2 in
both packaged and non-packaged development runs, using a user-scoped runtime
profile and a native download save dialog. The native shell owns a persistent
recording strip, notification-area Stop action, WinUI settings and permission
onboarding, while custody status remains visible outside the web document.
WebView2 session cookies are copied to an in-memory upload callback only after a
successful document boundary; no cookie is persisted or exposed through the
bridge. Route parsing is exact for meeting share/deletion-report actions and
does not treat query/fragment slashes as path separators.

Portable evidence: CMake/CTest `20/20`, `infra/scripts/ci-local.sh --fast`
`1240 passed`, and focused route/bridge regressions pass. T070/T071/T063 stay
open until Windows x64 MSBuild/UI, hardware, authenticated-cabinet, signed
MSIX and clean-image evidence is captured in Parallels.

## Complexity Tracking

No constitution violation is requested. The additional Windows native project,
static AEC3 artifact and package validation are required because capture,
WebView trust and signed desktop distribution are platform boundaries, not
generic abstractions. Process-loopback, virtual routing, a second UI runtime and
new server persistence are deliberately omitted.
