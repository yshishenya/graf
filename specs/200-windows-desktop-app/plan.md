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

Продолжение T083: устранить три подтверждённых тупика в существующей очереди,
не создавать вторую службу отправки. Явное «Отправить» возобновляет только
выбранную запись после исчерпания автоматических повторов; проверка владельца
сохраняет различие сетевого отказа и HTTP 401/403. Промежуточный `uploading`
после загрузки проверенного реестра возобновляется через server truth.
Ключ замены истёкшей серверной сессии не должен зависеть от сбрасываемого
счётчика повторов. Регрессии и условия сохранности перечислены в контракте §7;
серверный API, v2/v5 и Mac-код не меняются.

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
- Active Windows bounds are 960,000 buffered frames per source and at most
  48-frame clock recovery per batch, following the macOS bounded correction.
  T085 removes unused reorder/known-gap configuration: WASAPI workers deliver
  each source in order; reversed/duplicate packets or gaps above 48 stop the
  normal segment rather than waiting for an unimplemented 15-second recovery.
  Interleaving of the two sources remains independent. Synthetic tests must
  cover the memory bound, common-start trimming and correction limits.
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
| Capture-first Feature 200 integrity | PASS WITH EVIDENCE GATE | Separate Windows native stack uses WASAPI shared loopback + explicit mic; retired/virtual routing is not revived. Claims of validated capture and external release are blocked until clock, dropout, endpoint and hardware evidence exists; implementation and isolated verification produce that evidence. |
| Visible capture and user control | PASS | Constitution 7 excludes legal/notice prerequisites; native permissions, indicator/Stop, countdown, local three-state choice and verified targets remain required. |
| Data boundary and secret discipline | PASS | Desktop uses GRAF APIs only; WebView receives bounded state, not files/tokens/handles; MediaScribe credentials remain server-side. |
| Deletion truth and lifecycle accounting | PASS | Windows local package/queue/purge use existing custody and deletion semantics; no universal-erasure promise is added. |
| Spec-driven delivery with testable gates | PASS | New feature has spec, clarification, research, data model, contracts, checklists, quickstart, tasks and analyze gate before implementation. |
| UX/accessibility and reference fidelity | PASS WITH DESIGN GATE | Web cabinet is reused; native Windows strip/tray mirrors macOS semantics and requires keyboard, screen-reader, DPI/high-contrast and reference-fidelity review against current GRAF macOS. Windows-only deviations must be documented and justified by OS behavior, accessibility or truthful platform limits; third-party asset provenance remains a release gate. |
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
used the runtime `QueryPerformanceFrequency` for `ClockMapper` (this historical
claim is corrected below: WASAPI already converts QPC to 100-ns units), rejects
unsupported/non-finite samples instead of synthesizing silence, and reports
worker faults to the session finalizer. The v5 writer removes partial artifacts
when either WAV or playback encoding fails and publishes both artifacts only
after their temporary files are complete. CMake/CTest remains 20/20 PASS;
Windows MSBuild, pinned AEC3 binding and resampling implementation are now
host-built; hardware and signed-package evidence remain open.

**Уточнение по реальному отказу 2026-09-07 (T081/T084)**: `GetBuffer` возвращает
QPC уже в 100-нс единицах, независимо от частоты `QueryPerformanceFrequency`.
Обнаруженная в VM частота 24 MHz не может быть делителем этого значения.
У `ClockMapper` удалить неиспользуемую после исправления настраиваемую частоту;
поле входа назвать `qpc100ns`. `AUDCLNT_BUFFERFLAGS_TIMESTAMP_ERROR` запрещает
считать метку достоверной. Это исправление единиц, не разрешение игнорировать
разрывы или ослаблять аудиоконтракт. Общая временная шкала двух источников,
дрейф и реальный полный Record/Pause/Resume/Stop остаются предметом T071/T084.

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

Продолжение T085 (#6781): техническое уточнение контракта §5 отделяет общие
QPC timestamps от независимых device counters и фазы преобразования семплов.
Переиспользовать алгоритм ограниченной интерполяции/обрезки из macOS
`RecordingAudioTimeline.swift`, независимо реализовав его в существующем
Windows timeline. Не добавлять новый runtime/библиотеку/параллельный конвейер.
До реализации — регрессии на всю цепочку и независимая проверка требований;
до новой попытки записи — portable/native тесты. Недостоверные метки VM
остаются отказом, а не поводом увеличивать пределы. T085 предшествует
повторной аудиопроверке T084; обе задачи открыты до фактических результатов.

Уточнение начала потока T085: использовать существующий ClockMapper как
общую проверяемую точку решения о первом пакете, передавая битовые флаги
WASAPI целиком вместо отдельного timestampError. Единственное отбрасывание
по контракту §5 не начинает шкалу; ReleaseBuffer и фактический счётчик остаются
у worker. Готовность устанавливается после первых нормализованных данных.
Типизированный отказ часов и стартовый счётчик передаются через существующие
worker/controller/MetadataSafeDiagnostics, без журнала содержимого пакетов.
Сначала регрессии первого/второго/смешанного флага, неизменности формата,
ошибки освобождения, общей шкалы, таймаута и безопасной сериализации.
Не менять формат устройства Windows, правила count/device или пределы дрейфа.

Историческая гипотеза read-only измерения 2026-09-07 (не действующее правило;
заменена уточнением §5 контракта от 2026-09-26): `GetBuffer`-
`devicePosition` может быть в endpoint-единицах и не обязан совпадать с
числом кадров engine-пакета при внутреннем преобразовании частоты. Worker
обязан получить существующий `IAudioClock`, проверять его частоту и брать
`GetPosition` для непрерывности пакетов; `GetBuffer.qpcPosition` остаётся
монотонной общей начальной привязкой. После первого пригодного пакета
presentation timestamp выводится из общей QPC-точки и `IAudioClock`
progression, чтобы виртуализированный хост не подменял audio clock шагом
callback. При отсутствии `IAudioClock` worker отказывает в инициализации;
автоматический пересчёт `devicePosition` по DeviceFormat не используется.

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

Следующий срез T082 (US5/AC7–9): добавить `targetKey` в существующую
VerifiedTargetIdentity. Старый составной ключ переименовать в `identityKey`
и сохранить для точного слежения/вопроса; только настройки получают постоянный
ключ продукта. Проверка членства в реестре сверяет также targetKey, поэтому
подмена ключа при настоящих хешах не читает/не меняет чужой режим. Разрешить
несколько проверенных версий одного продукта, но одну строку настроек; отвергать
назначение одного EXE разным продуктам и противоречивые названия. Лимит 64
проверенных записей пока прежний.

HKCU `ApplicationRulesV2`, заголовок `graf.automatic-recording.v2`: ключ
`[a-z][a-z0-9_]{0,63}`, три прежних значения и атомарная запись одного документа.
Не добавлять миграционный reader V1: рабочий каталог до этого был пуст, UI
не мог сохранить реальные per-app правила, на проверяемой Windows V1 отсутствует.
Не удалять старые значения. V2 сохраняет правила временно отсутствующих продуктов,
но они применяются только после возвращения подтверждённой записи того же ключа.
Не создавать нового сервиса/серверного API/хранилища, не менять правила вручную
в Windows ради проверки. Начать с synthetic regression в VerifiedTargetPolicyTests.

Первый реальный элемент bundled-реестра — `microsoft_teams_new` из общего
каталога, только проверенная установленная ARM64-версия Microsoft Teams.
Хеши и происхождение фиксируются в research.md; это не утверждение поддержки
всех Teams/x64 и не закрытие всего T082. Таблица находится в существующем
VerifiedTargetRegistry.cpp; AppMain получает её до создания policy/detector.
Нативная проверка подписи остаётся обязательной при каждом наблюдении.

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

## Уточнение полного паритета от 2026-09-26

Пользователь подтвердил цель: все функции и логика текущего macOS, а не только
первоначальный Windows MVP. Опорный master — `f5cca687a06dc57ad6ccbef840a0be897eaa6336`.
Дорожка остаётся `high-risk-product`; изменения не ослабляют capture/privacy,
не меняют серверную бизнес-логику и не означают разрешение публичного выпуска.
Уточнения ниже реализуют FR-002 и отражены в Phase 15 tasks.md.

1. **Поставка звука.** Обязателен настоящий backend из `Native/GrafAEC3/upstream.lock`.
   MSBuild приложения и пакета завершает сборку ошибкой при отсутствии header,
   статических библиотек или неверном pin/архитектуре. Portable tests сохраняют
   test doubles, но не служат приёмкой backend. Путь к внешнему проверенному
   source/build cache допустим. Скрипт проверяет exit code каждого native tool.
   Конфигурация как на Mac: только AEC3, без high-pass, NS, AGC1/2 и transient
   suppression. Минимальный локальный режим `--verify-audio-backend` выполняет
   реальное создание и 10 ms reverse/near-end обработку, возвращает exit code,
   не пишет звук, не включает устройства и не обращается в сеть.
2. **Оплата.** Чистая policy рядом с `WebViewRoutePolicy` хранит одну сессию на
   текущий host, с монотонным пределом 900 секунд. Вход только из доверенного
   billing-документа к точному HTTPS provider из Mac allowlist: `api.yookassa.ru`,
   `api.yookassa.test`, `yookassa.ru`, `yookassa.test`, `yoomoney.ru`.
   Редирект после POST допустим; последующие HTTPS bank hops и payment frames
   допустимы только внутри живой цепочки. Popup направляется в тот же контролируемый
   WebView, не получает новый привилегированный host. Возврат к origin, timeout,
   process/navigation failure, recreate и logout прекращают исключение.
   Внешний документ не получает nonce, bootstrap, cookie extraction или native
   команды. Общий route allowlist не расширяется на произвольный веб.
3. **Вход.** Response policy сохраняет ожидаемые HTML-ошибки интерактивных
   login/signup/email-форм, включая 400/429, до общей обработки ошибок HTTP.
   Auth-документ не привилегирован. Recovery хранит только разрешённый GET-путь
   кабинета (включая billing/detail), никогда внешний URL или повтор POST.
   Настоящие ошибки cabinet 5xx по-прежнему выводят native recovery.
4. **Напоминания.** `Shell` получает один нативный non-activating presenter и
   тестируемую модель сроков/дедупликации, `NativeSettingsBridge` — сохраняемые
   read/update/test. Источник событий — существующий account/calendar context,
   не новый calendar provider. Перед Join/Record событие и аккаунт проверяются
   заново. Карточка справа сверху живёт до более раннего из начала встречи и
   120 секунд; тест — 6 секунд, короткая запись — 20 секунд. Замена/закрытие
   не крадут фокус; кнопки доступны клавиатурой и screen reader. Logout очищает
   account-bound модель, offline не подтверждает устаревшее событие. Вторая
   запись запрещена. Системные toast permissions не блокируют локальную карточку.
   Исторический T097 проверяет скрытие неработающих кнопок; после T104 тестовая
   кнопка должна работать, а не оставаться скрытой ради старого снимка.
5. **Атрибуция.** Штатная активация MSIX `grafrec://attribution` передаёт только
   ограниченные поля текущего Mac `ProductAttributionHandoff`; один сохранённый
   handoff живёт 90 дней. Повторная активация работающего экземпляра передаётся
   ему, а не теряется за single-instance mutex. Bridge id: `graf_attr_` плюс
   8–64 ASCII alphanumeric/underscore/hyphen; пять `utm_*` меток до 96 символов,
   без секретоподобного содержимого, email/телефонов; landing path до 96 символов
   из `/A-Za-z0-9_-`. Ни исходная ссылка, ни метки не попадают в diagnostics.
   Единый sign-in builder для всех путей сохраняет validated next и добавляет
   bounded fallback/ref; отсутствие/ошибка аналитики не мешает входу.
6. **Очередь.** Постоянные allowlisted отказы сервера не превращаются в повторяемые
   сетевые ошибки. Историческое имя файла `desktop-upload-queue.v2` сохраняется;
   актуальная схема v3 с чтением v2. `not_retryable` не допускает Send/requeue,
   но не лишает пользователя проверенного playback/delete.

Проверки: сначала негативные/позитивные core tests, затем реальный x64 MSBuild,
установленный MSIX, живые окна/вход/запись и matrix с точными SHA. Платёжные
редиректы проверяются тестовыми ответами без реального списания денег.
Физический x64/60 минут/чистая установка остаются отдельными открытыми условиями;
Parallels ARM64 с x64 эмуляцией не выдаётся за их выполнение.

No constitution violation is requested. The additional Windows native project,
static AEC3 artifact and package validation are required because capture,
WebView trust and signed desktop distribution are platform boundaries, not
generic abstractions. Process-loopback, virtual routing, a second UI runtime and
new server persistence are deliberately omitted.

## Завершение паритета и совместное развитие — 2026-09-27

Действует цель из spec.md от 27 сентября. Полоса `high-risk-product`,
production deploy/public release не разрешены. Существующие 16 открытых задач
сохраняются; новые задачи описывают только неучтённые дефекты последней проверки.
Сначала сохранность записи и пользовательского текста, затем удобство оболочки,
напоминания/оплата/обновления, после них полная приёмка.

- **Закрытие и трей.** Разделить закрытие главного окна и явный выход. При
  работающем трее крестик скрывает окно; активная запись продолжает ту же сессию
  с отдельным видимым индикатором и Stop. Если управление в фоне недоступно,
  закрытие отменяется без остановки. Только явный Quit выполняет существующую
  bounded остановку/финализацию. Start и Settings в WindowsTray вызывают уже
  существующие действия AppMain; состояния готовности/занятости не дублируются.
  Минимальное тестируемое решение о закрытии располагается рядом с shell;
  AppMain остаётся владельцем окон и вызовов захвата.
  Общая команда Settings открывает `/desktop/settings/account`, как команда Mac,
  а не только нативную страницу автозаписи. При недоступном кабинете сохраняется
  существующее восстановление и независимое нативное управление записью.
  Скрытие окна не вызывает безусловный `automaticPolicy_.cancel()`: сопровождение
  уже начатой автозаписи и её остановка по окончании встречи сохраняются.
- **Платформенный текст.** Удалить whole-body `adaptPlatformWords`, а не
  расширять список замен. В общих шаблонах адресно обозначить только подписи
  приложения; динамические тексты формировать общей функцией выбора подписи.
  Windows публикует ограниченный признак платформы только в доверенном bootstrap.
  Этот признак влияет на отображение, не предоставляет полномочий. Без нового
  признака существующий Mac сохраняет свой интерфейс. Пользовательский текст
  не сканируется. Повторная инициализация через имеющийся HTMX lifecycle,
  без нового наблюдателя за всем DOM и без второго комплекта страниц.
- **Фокус.** Автоматическое предложение и индикатор показываются штатным
  API без активации. Ручные действия пользователя могут активировать окно;
  фоновое обнаружение и старт — нет. Проверяются сохранение foreground HWND,
  доступность Stop и клавиатурный путь к фоновому окну, не только видимость.
- **Напоминания T104/T105 — уточнение 28 сентября.** Эталон F277 на
  `51bcff6b1abfdf2a01d59a7d3f00c831674c365c`, подтверждённый пользователем,
  заменяет два прежних канала единственной собственной карточкой. Использовать
  существующие RecordingNoticePresenter/MeetingReminderModel/Presenter и
  automatic prompt owner, удалить раннее окно −15 минут. Due=startsAt−offset,
  deadline=min(due+120s,endsAt); срок не перезапускается при refresh. Системные
  уведомления/новая служба/постоянный журнал попыток не добавляются. Общая
  карточка получает варианты meeting/prompt/problem/short/preview, компактную
  раскладку и правила приоритета F277. Настройки уведомлений переходят на v2
  с quiet; история последних 50 нейтральных событий только в памяти контекста.
  Quit прекращает показ, скрытие окна — нет. Тихий режим не скрывает prompt,
  indicator/Stop и не меняет решения записи. Shared server templates/JS F277
  интегрируются адресно после освобождения файлов T109, не вторым Windows UI.
  Существующий recording-settings bridge сохраняет свою версию; notification
  v1 даёт понятный отказ обновить окно без изменения настроек.
- **Обновление.** Источник истины — штатные Package/App Installer API текущего
  подписанного пакета и зарегистрированный источник обновлений, не собственный
  загрузчик и не URL из страницы. Общий intent `request_app_update` с пустым
  payload открывает нативную поверхность проверки; ответы unknown/unavailable
  не выдаются за «последняя версия». Установка требует явного нативного действия,
  не прерывает запись и не снимает проверку подписи. Нет App Installer association
  или ещё не опубликован канал — честная диагностика и незакрытый delivery gate,
  а не выдуманный production endpoint. Проверяются статусы, отказ, повтор,
  закрытие окна/устаревший callback и отделение capability от факта обновления.
  Системный `PackageManager.FindPackageForUser` получает текущий пакет по
  identity; `GetAppInstallerInfo` и `CheckUpdateAvailabilityAsync` проверяют
  зарегистрированный источник без известного обходного пути через
  `Package::Current().CheckUpdateAvailabilityAsync`. NoUpdates/Available/
  Required/Unknown/Error отображаются раздельно. API не сообщает новую версию:
  она не выдумывается. Перед установкой повторно сверяются identity и URI;
  принимается только абсолютный HTTPS без userinfo/query/fragment.
  Зарегистрированный URI не доказывает доверие всему содержимому канала:
  утверждённый выпуском канал обязан соответствовать identity/publisher/версии/
  архитектуре пакета, без неожиданных дополнительных пакетов/redirects.
  Отсутствие такого канала оставляет установку недоступной. Тестовый канал
  не становится производственным. Автообновление в AppInstaller не должно
  обходить явное действие и сохранность записи. Перед передачей управления
  системному установщику блокируются новые записи и завершаются фоновые
  изменения файлов; ограниченное ожидание при неуспехе отменяет установку.
  `ForceTargetAppShutdown` допустим только после готовности, `drain` не
  подменяется `cancel`. Перезапуск регистрируется, но не обещается безусловно.
  Проверка подписи требует Status=Valid, не наличия сертификата. Совместимость
  AppInstaller XML проверяется на минимальной Windows 10 19045 отдельно от API.
- **Общее развитие.** `parity-matrix.md` остаётся единым списком пользовательских
  возможностей. У каждого нового общего поведения указываются реализации и
  проверки двух ОС, допустимое системное отличие и результат приёмки. Нового
  UI runtime, общей абстракции захвата, серверной схемы или глобального процесса
  выпуска не вводится. Рабочая инструкция находится в пределах F200.

Constitution check до и после уточнения: I/II — нативный захват/видимый Stop
сохранены; III/IV — данные не подменяются, секреты/удаление не расширены;
V — Mac distribution не меняется; VI — независимые checklist/analyze/issue
гейты перед реализацией; VII — общий эталон и доступность сохраняются.
Новые поля хранимых аудиозаписей не нужны; состояние обновления эфемерно.
Настройки уведомлений дополняются quiet с сохранением прежних значений;
по уточнению F277 постоянный журнал системных попыток не создаётся.
История уведомлений — только память текущего контекста (data-model.md).
Аудиоалгоритмы этого исправления не
меняются. Обязательная аппаратная/сквозная приёмка остаётся открытой.

### Уточнение F277: окончательное принятие автоматического старта

T113 сохраняет нынешний закрытый допуск пакетов во время starting. Контроллер
при готовности обоих workers вызывает единственную синхронную проверку решения
до startRecording/acceptingBatches: текущий сеанс, поколение отмены, подтверждённая
цель и процесс, свежесть обнаружения, действующее правило и prerequisites.
Собственное starting не считается другой записью. AppMain связывает эту проверку
с текущей политикой; starting больше не вызывает captureAccepted. Любой путь
pollHealth использует тот же допуск, а не только таймер. Отказ завершает workers
с закрытым допуском; writer не получает пакеты, recovery не получает нормальный
пакет. Нельзя вводить await/обработку событий между проверкой и открытием допуска.
Manual Start сохраняет штатную readiness-проверку, без автоматического решения.
Новые manifest-поля не нужны, пока сохраняется эта граница; предварительное
накопление аудио или асинхронное подтверждение потребует durable pending/accepted
с запретом pending/ошибок во всех upload/recovery путях и отдельной проверкой.
Регрессии T113 охватывают задержанный worker, отмену/правило/цель/свежесть,
чужой сеанс, повтор, прерывание до допуска и нормальный принятый старт.

### Открытая Phase 0 от 2026-09-30: T094 и RQ30-H1

Риск остаётся high-risk-product. Clarify в spec.md закрепляет унаследованное
шифрование и отделение потери кадров от ошибки метки; новых пользовательских
решений не выдумано. Исследование в research.md выявило два незавершённых
технических решения: согласованную модель packet timestamp/дрейфа для всего
аудиопотока и защищённый seekable local custody поток на всех поддерживаемых
редакциях Windows. Увеличение порога только ClockMapper не является планом
исправления; EFS/ACL либо шифрование только окончательного manifest не
являются планом защиты полного локального потока.

Перед реализацией необходимы выбранный устойчивый формат и нативные
интеграции, согласованные data-model/contract/quickstart/tasks и независимый
review/checklist/analyze. Пока это не сделано, Phase 1 и общий gate не
закрываются; численные правила §5 не ослаблены, код шифрования не внедряется,
существующие пользовательские записи не мигрируются. Разрешены ограниченные
синтетические/metadata-only исследования без приёмки аудио и без изменения
рабочих данных. Необязательное обновление agent context после plan не
выполняется: этап не завершён, корневой AGENTS.md должен остаться стабильным.

Уточнение исследования 2026-09-30: штатная граница IStream → IMFByteStream
проверена искусственным AAC round trip. Для дальнейшего протокола рассмотрены
bounded DPAPI blocks с дополнительной проверкой целостности и два alternating
protected indexes над immutable block versions; это проще собственной AES
key/nonce lifecycle. По round121 выбран исходный layout для проектирования:
256KiB immutable block versions, два protected index snapshots, native
user-scope DPAPI; block version отличается от index generation. Index entry16B,
logical representation64GiB/262144blocks, plain index≤4198400B; bounds проверены
арифметически ASan/UBSan, не приняты как runtime resource proof. Это не новая
продуктовая квота или длительность: local parser24h отличается от server4h,
расхождение не исправляется скрытым ограничением Windows writer. Sequential
checkpoint на полном block, Flush/Pause/Stop сохраняют короткий tail; 4block
group относится к seek/rewrite, не обычной задержке checkpoint. Финальный wire
format/intent/authority migration будет определён в Phase1; combined IO,
memory/Stop/power-loss/paths остаются отдельными обязательными проверками.
Существующие AppInstance, recovery lease, finalizer future и CNG hash reuse
предпочтительнее нового сервиса/БД/очереди. При directory layout обязательно
согласовать short-recording discard и миграцию прежних пакетов. Phase0 остаётся
открытой, новый protected-storage код в продукт пока не вводится.

Playback проектируется через native Media Engine audio-only и существующий
IStream→IMFByteStream adapter без plaintext tempfile/ShellExecute. Существующие
LocalMetadataScan/open-validation background paths сохраняются; новых scanner
services нет. Callback lifetime/account/delete/shutdown fences и управление
потоком закрепляются в contract до кода. Выбор API по документации — не
runtime proof проигрывания. Последние decisions/отвергнутые альтернативы и
границы Phase0 записаны в research.md: выбран storage путь, coherent clock
model ещё не выбрана. Общий gate не закрывается; after_plan context hook
по-прежнему не применяется к незавершённому этапу.

Уточнение round122: для исследования clock выбрана раздельная проверка
непрерывности кадров и интервальной совместимости phase/frequency с ошибкой
меток; не выбран готовый производственный PTS estimator. Детерминированный
стенд показал, что при гипотетическом noise±3ms полный120s ряд ещё может быть
совместим одновременно со100 и200ppm. Это не новый продуктовый порог3ms/120s:
bounded noise реального endpoint и достаточная точность двухисточникового
выравнивания ещё не установлены. Совместимость одной гипотезы не означает
SC003 PASS; clamp/reset origin/fallback/mapper-only bypass запрещены. Следующее
исследование должно дать наблюдаемые долгосрочные границы и согласованный
mapper→normalizer→timeline, а не только сгладить краткий metadata trace.

Round123 отверг phase-only smoothing после проверки всей настоящей downstream
цепочки: healthy timeline и почти неизменённый RMS не исключили рассогласование
двух одинаковых тестовых волн. Следующий кандидат — непрерывная коррекция
resampler ratio, связанная с оценкой частоты/неопределённости; не общий trim/
interpolate ответ на noise. До production кода нужны waveform/двухисточниковые
регрессии, количественный clock contract и независимый review. Ни гипотетические
J3ms/6ms, ни alpha0.32s не становятся рабочими порогами. Новая библиотека,
zero-fill/drop/epoch reset из сторонних playback реализаций не переносятся.

Round124 завершил доступный CLI путь последовательных metadata-only опытов
x64/native ARM64: оба получают DATA_DISCONTINUITY, x64 также clock_drift;
корректный Stop/release/exit не означает здоровый capture. Эмуляция x64 не
единственное необходимое условие. Product/§5 не меняются. Отдельная следующая
проверка — native MMCSS registration на capture thread с гарантированным
AvRevert на том же thread после Stop/COM cleanup; только disposable probe,
без registry/service/global priority. Сначала сравнить короткие явные CLI
варианты на одинаковом endpoint/buffer/mapper, сохранить flags/count/Stop
guards. Даже благополучный короткий опыт не закрывает SC003 и не выбирает
численный clock contract. Эта независимая scheduling гипотеза не заменяет
частотную модель и не является разрешением phase-only/threshold обхода.

Независимый API review round124 выбрал direct pinned WebRTC SincResampler как
reuse candidate для SetRatio с непрерывной source phase, не PushSincResampler
и не новую библиотеку. Это ещё не production model: численные estimator/slew
bounds, startup zero history/partial EOS и waveform evidence остаются открытыми.
Кроме того, T096 требует отдельной узкой regression/fix exception-before-release:
main-agent synthetic bad_alloc в actual consumePacket подтвердил ReleaseBuffer
calls0. Исправление текущей custody гарантии не требует расширения clock bounds,
но требует reviewer/implementation gates; ошибка выделения не выдаётся за
причину наблюдаемого WASAPI clock_drift.

Round126 подтвердил compiled reuse direct pinned SincResampler: oracle
двухисточниковая waveform проверка с настоящим timeline проходит fixed/variable
partitions и реальную смену ratio без сброса фазы. Nominal-ratio negative
отвергается при healthy timeline/нормальном RMS. API edge tests также подтвердили
ограничение полного partial-EOS без padding callback. Это выбор исследовательского
механизма, не законченный causal clock contract. До production интеграции нужны
estimator/phase uncertainty/slew bounds и явно согласованные начало/конец;
§5 и SC003 не меняются, Phase0/after_plan context hook остаются открытыми.

### Полный охват защиты локальных записей — 2026-10-01

Владелец явно одобрил промежуточный коммит и правки плана/задач по
шифрованию. Это не разрешение обойти незавершённую Phase0, мигрировать
пользовательские данные либо публиковать пакет. Сохранённый исходный срез:
`99b00a579c24b50e320465b69d9a296038bc544d`; последующие изменения этого
раздела и tasks — документация, не уже реализованная защита.

FR-012 — требование ко всей цепочке, а не к одному готовому manifest.
Исторические закрытые T009/T022/T037/T038 не доказывают его новую полную
редакцию. Добавляемые T114–T118 владеют только недостающим protected-storage
результатом; auth, server truth, удаление и аудиочасы остаются у существующих
T083/T087/T088/T094–T096. Прежние task IDs и отметки не переписываются.

| Поверхность | Существующий владелец и необходимая граница |
| --- | --- |
| Canonical float, WAV, AAC/M4A, временные версии и короткий хвост | `Recording/V5LocalRecordingWriter.*`: защищённый seekable logical stream до первой дисковой записи; Media Foundation через штатный IStream → IMFByteStream, не через открытый временный URL. |
| Manifest, recovery, queue/deletion metadata, quarantine и atomic temporary версии | `Storage/AtomicFileStore.*`, `Upload/DesktopUploadQueueService.*` (включая deletion ledger): единая защита content-bearing bytes, сохранение прежнего валидного поколения при ошибке; не пустой ledger и не plaintext fallback. |
| Inspect, hash, диапазоны upload и playback | `Recording/LocalRecordingPackage.*`, `Storage/Sha256.*`, `Upload/DesktopHttpTransport.*`, существующий playback-путь `AppMain.cpp`: bounded logical read исходных v5 bytes; не весь файл в памяти, не расшифрованная копия на диске, не ShellExecute локального media path. |
| Старые незашифрованные пакеты и реестры | Те же recovery/queue owners: restart-safe копирование с проверкой bytes/hash и durable intent перед сменой единственного authority; без re-encode, нового UUID, сброса accepted ranges или delete intent. |

Исходный кандидат остаётся выбранным в research.md: user-scope DPAPI,
immutable block versions по 256KiB и два protected index snapshots. Собственный
криптографический алгоритм, новая БД, служба, очередь или библиотека не нужны.
Существующие AppInstance/recovery lease/finalizer и CNG hash переиспользуются.
Арифметические bounds round121 — вход в исследование, не доказанные runtime
пределы; изменение их требует обоснования и повторной проверки, не тихого
ограничения длительности или нового права на заполнение диска.

Порядок дальнейшей работы:

1. **T114 / Phase0:** один ограниченный синтетический стенд проверяет combined
   DPAPI/index/IO/seek/Media Foundation/память/Stop и отказы публикации. Звук
   устройств и рабочие записи не используются. В research фиксируются факты,
   количественные границы и отвергнутые варианты; при неподтверждённом пути
   Phase0 остаётся открытой, новые значения не становятся рабочими порогами.
2. **T115 / Phase1, только после T114:** финальный contract
   `contracts/windows-protected-local-custody.md`, data-model и quickstart
   определяют format/version/identity/integrity, commit/recovery authority,
   concurrency/lifetime, миграцию и численные проверки. Независимый reviewer
   заново проверяет затронутые checklists; затем текущий read-only analyze и
   taskstoissues. Этот раздел не подменяет законченный contract.
3. **T116–T117 / implement, только после gates:** защищённый полный поток и
   переход старых пакетов реализуются последовательно по принятому contract.
   Старый format reader не становится постоянной альтернативой; у перехода
   должны быть owner, expiry/removal trigger и отдельная retirement-проверка.
4. **T118 / acceptance:** generated v5 bytes проходят restart, playback/seek,
   hash/range upload и deletion/recovery; проверяются ciphertext-only disk
   snapshots, key/integrity failures, память/диск/Stop и installed standard-user
   Windows. VM evidence не закрывает физическую x64 матрицу/SC-003/SC-008.

До подтверждённого переключения и безопасной очистки прежних копий старый
inventory не называется зашифрованным. Потеря профиля DPAPI, повреждённый
объект или неопределённый commit сохраняют артефакты и блокируют небезопасную
запись/GC. Отказ не превращается в нормальное сохранение, нулевые bytes,
повторный plaintext reader или пустую очередь. Ключи не уходят в WebView,
диагностику или сеть; новые пароли, диалоги, admin и whole-disk prerequisites
не вводятся. Локальная очистка по-прежнему не обещает forensic/cryptographic
erasure: DPAPI пользовательского профиля не доказывает уничтожение ключа
конкретной записи или всех старых копий.

Новый coherent clock estimator по T094–T096 остаётся независимым открытым
решением. Дополнение покрытия FR-012 не завершает ни его, ни storage Phase0,
ни общий допуск F200 к реализации/слиянию/выпуску. Необязательный after_plan
agent-context hook не выполняется на незавершённом этапе; AGENTS.md не меняется.

### Ограничения из измерений T114 — 2026-10-01, round137

Полный validated reopen стенда64MiB занял9.44s в Parallels. T115/T116 не могут
выполнять такой scan в foreground constructor/readiness, UI или callback:
переиспользуются существующие `AppMain.cpp::LocalMetadataScan`, asynchronous
open-validation и upload worker, с account/delete/shutdown fences и явным
состоянием проверки. SC-001 (2s), SC-003 и 5s dispatcher drain не расширяются.
Это требование к проектированию, не подтверждение уже выполненного переноса.
Существующий plaintext constructor `NativeCapture` синхронно читает ledger и
prune state; не следует молча добавлять туда проверку каждого media block.

Research helper имеет общий1MiB cap, тогда как выбранный максимальный индекс
требует4198400B. Native DPAPI roundtrip такого envelope измерен отдельно, но
не semantic-index/durable-recovery proof. T115 определяет отдельные проверяемые
границы block/index по типу объекта; нельзя просто расширить общий cap и
тем самым принять oversized media blocks. Ни полный64GiB layout, ни рост
памяти/CPU всего приложения/Stop не закрываются isolated envelope/64MiB стендом.

### Выход исследования T114 — 2026-10-02, round141

T114 завершён в ограниченном исследовательском объёме. Совокупность round134–140
и fresh combined MF IO round141 принята независимым рецензентом:
`checklists/review-2026-10-02-phase0-exit.md`, дополнение от2026-10-02.
Последний пробел измерения закрыт; дополнительных опытов механизма до T115
этот audit не требует. Исторические NOT READY выше сохранены как прежнее
состояние, актуальные результаты — `validation-2026-10-02.md`.

Следующий этап T115 — окончательный contract защищённого хранения и согласование
data-model/quickstart. Он ещё не принят. Исследовательские bounds не стали
продуктовыми квотами; синхронный reopen по-прежнему запрещён в UI/readiness.
T116–T118 не начинаются до независимых checklist/analyze/taskstoissues gates.
Аудиочасы T094–T096, установленный клиент, migration и общая приёмка F200
остаются открытыми; это не завершение всей Phase0 и не разрешение выпуска.

### T115: кандидат contract — 2026-10-02

Создан `contracts/windows-protected-local-custody.md`; согласованы кандидатные
entities в data-model §12 и будущая проверочная матрица quickstart §12.
Выбраны явный LE wire v1, раздельные DATA/ZERO, block/index bound, native
context binding и immutable snapshots. Для authority metadata запрещён
откат к старой очереди при unreadable slot: delete intent не должен исчезать.
Media fallback остаётся degraded. Bootstrap/package-state/intent описывают
один restart-safe reader authority; legacy reader только migration, не fallback.

T115 остаётся открытым: независимый design/checklist review и текущий analyze
ещё не завершены. Candidate не разрешает T116/T117 или рабочую migration.
Особенно проверить границы async ledger acknowledgment, published authority,
двух slots/pins/GC, migration/sentinel/rollback и прежних product limits.
После REQUEST CHANGES рецензента уточнены четыре решения: metadata birth с
двумя g1 slots и отказ любого singleton после restart; durable old-reader
.quarantine до rename; typed commit tickets/ACK continuations для всех existing
callers; strict UTF-8 authority records со schema/enums/refs и conflict checks.
Contract §8.2 замыкает temp/quarantine registry; §5 сохраняет PRD free reserve
min(10GB,10%capacity), включая physical peak/admission. Это revised candidate,
не независимое принятие исправлений; T115 остаётся открыта до повторной проверки.
Следующий review принял F1–F4 в design scope, но потребовал F5/F6: initial
migration prerequisites и historical barrier после ухода birth index из обоих
slots. Revised contract задаёт prepared intent до closing fence, stage-aware
reserved queue/destination rules и interruption table; direct immutable birth
block validator и persistent transitive roots до GC, без третьего индекса.
Mutable queue copy receipt после switch не заменяет current generations/ranges.
Эти уточнения также требуют повторного independent review; T115 не закрыта.
Общий plan не завершён из-за clock T094–T096; optional after_plan context hook
пока не выполняется, root AGENTS.md стабилен. Ни нового commit/push/PR/release,
ни обновления установленного клиента этой документацией не производится.

### Clock Phase 0 checkpoint — rounds158–160, 2026-10-02

Исследовательский Source теперь проверен при разных первых QPC, дробной сетке
и независимых device counters, а не только при общем точном старте генератора.
Это сужает неопределённость механики SetRatio/start/EOS, но не выбирает готовую
модель часов: первый QPC в generated fixture ещё физически точен. Приёмка
качества mixed:12/16 PASS, четыре дополнительные long far FAIL сохранены.
Согласование coefficient0.5 с Mac проверено только isolated candidate.

До Phase1 clock contract обязан явно различить: относительный packet guard,
абсолютный first-frame anchor, межисточниковое начало, packet first position
и current clock position с разными единицами. Schema6 pairShift вычитает две
первые QPC и не измеряет абсолютную связь:192 generated observations подтвердили
неразличимость постоянных смещений. Ни GetPosition как oracle, ни удвоение1ms
budget не выбраны. Для estimator требуются обоснованные входные assumptions,
наблюдаемые bounds и перенос ошибки через resampler/rounding/полный common EOS;
новые числа нельзя получить из одного короткого no-fault metadata run.
Детали/контрпримеры/границы — research и validation rounds158–160.
Новые tasks, reviewer checkbox edits, product patches и after_plan hook отсутствуют:
Phase0 открыта, storage design не устраняет самостоятельный clock gate.

### Граница clock design и аппаратной приёмки — round161, 2026-10-02

Независимый review требований уточнил: аппаратная калибровка абсолютной первой
метки до выбора design не предписана FR-009/018, SC-003 или §5. Можно опереться
на семантику WASAPI GetBuffer, явно сохранив неподтверждённую аппаратную точность
как ограничение будущей live/hardware приёмки. Контрпример постоянного bias
не создаёт бесконечного предварительного hardware gate.

Один конкретный проект изложен в `contracts/windows-clock-candidate.md`:
own QPC origin/fraction, pinned SincResampler, continuity-preserving SetRatio,
phase controller horizon1s/±500ppm, bounded staging и full-support EOS.
Это candidate algorithm, не новое admission правило. ReachablePhase из fixture
не переносится в runtime; действующий raw guard не ослабляется. Кандидат сам
по себе не исправляет текущий VM clock_drift. Нужны независимый review и
adversarial/resource проверки; plan/Phase1/checklists/analyze/issues не завершены.

Round162–163: candidate не принят. Контрпример8ms и independent P1 показали
обход прежнего48-frame downstream refusal. Два дополнительных actual-core
counterexamples подтвердили P2 empty output и full trim: соседний raw residual
не заменяет timeline end. Нельзя добавить второй legacy normalizer ради
кажущегося точного совпадения или назвать изменённую семантику прежней.
Следующая правка должна определить сохранение действующего gap rule на новых
output boundaries; затем повторить тесты и review. VM raw clock_drift отдельно
требует решения до готовности; resampler после него не устраняет root cause.

### Один Sinc и существующий timeline — round164, 2026-10-02

Independent requirements review отделил безопасность от exact legacy output
boundaries: §5 не обязывает воспроизводить linear Normalizer после перехода
на Sinc; пример441/441 условен. Выбрано направление без второй старой цепочки:
real full-support Sinc samples + packet-QPC-derived witnessPTS + непрерывный
pre-correction offset передаются существующему RecordingAudioTimeline.
Он реально интерполирует/обрезает до48 и отказывает при превышении; простая
виртуальная проверка с последующей публикацией всех samples на ровной сетке
отвергнута. Пустой output и full trim используют реальный timeline end.
Точное множество решений старой и новой цепочки не обещается; unchanged
packetization invariance для точного сигнала остаётся обязательной проверкой.

Candidate revision164 определяет выбор пакетной опоры по source sample center,
разделение выходных диапазонов при смене опоры, относительное округление с
origin residue и различие generated/pre-correction/canonical counters.
Эта конкретная формула и layout тегов пока не приняты. Независимый reviewer
принял только допустимость направления, не numerical proof/implementation.

Native staging probe на11rates8–192k с variable input до4800frames и callback64
дал peak4863<=4864,2189 canonical zero blocks, full-support/two-poison checks.
Это measured unread input count, не реальная production allocator quota.
Portable rounding probe покрывает625 origin residues/two epochs/11rates/three
anchor partitions: relative formula PASS, naive absolute-floating negative FAIL.
Оба host types имеют53-bit mantissa; source waveform/native Sinc packetization,
timestamps на новой полной цепочке, metadata tag bound и VM fault не приняты.
Полный план/after_plan hook/checklist/analyze/issue sync ещё не завершены.

### Проверка полной witness цепочки и отказ качества — rounds165–166

Native generated-data probe соединяет actual admission, packet-center tags,
Sinc/full-support EOS и существующий timeline. 13 healthy zero cases проходят;
6 cumulative-mapper-admitted8ms jumps отвергаются actual timeline. Найденный
независимым reviewer P2 повторного продолжения после отказа исправлен только
в disposable Source: после замеченного terminal state его курсор/счётчики
больше не изменяются. Source SHA5bee360d… повторно принят reviewer узко;
native rerun подтвердил late-call fencing, не production controller fence.

Однако concrete witness reconstruction round164 **не принимается**:
при generated physical nominal rate допустимый metadata jitter0.4ms обрушает
native far AEC с22.41dB до0.946dB. Двойная речь также ниже существующего10dB
порога. Отключение динамической обратной связи ratio не исправляет результат;
direct QPC
batch boundaries и actual timeline correction достаточны для воспроизведения.
Поэтому успешные13/6 проверки не разрешают внедрение, установка не обновлена.

Следующий clock design должен отделить uncertainty временных меток от
physical drift, сохранить наблюдаемый разрыв/terminal semantics и проверить
ненулевой waveform, а не только counts/zero/EOS. Числа guard/quality не
ослабляются; ровная PTS без сохранённой защиты также не возвращается молча.
Новый estimator/contract ещё не выбран. Raw VM clock_drift остаётся отдельным
открытым вопросом. Phase0/plan/checklist/analyze/issue sync не завершены;
после plan optional agent-context hook пока не выполняется.

### Фазовый successor с ограниченной очередью — round167, 2026-10-02

Исследован другой путь после quality FAIL предыдущего варианта: непрерывный
native Sinc и QPC-driven phase feedback с отдельным48-frame innovation guard;
publication gridOrigin+outputIndex не переносит packet jitter в waveform.
Это изменение downstream semantics, не тот же witness algorithm и не
согласованная замена §5. Raw admission/flags/device count остаются прежними.
Установленная ошибка VM ClockMapper всё ещё не исправлена.

12/12 native quality checks PASS: paired48k/44.1k, variable packets1…4800,
own fractional origins, nominal/opposite±100ppm/sinusoidal99ppm и metadata
jitter0.4ms. Каждый case1199blocks/12s/no trim; far21.82…21.86dB, DT27.90…40.42dB,
near gain−.504dB/corr.99976/lag434. Scope не расширен до60min/writer/CPU/hardware.

Independent Hubble review нашёл возможность применить последнюю команду к
94 накопленным пакетам: computed phase drift около4ms без нового наблюдения.
В bounded derivative admission теперь требует unread<64, next packet<=4800;
нарушение terminal до новой метки. Native backlog regression94calls отказывает
на третьем/accepted480/no output. Повторные13healthy/6eight-ms-fault cases PASS;
242 строки неиспользуемых legacy research drivers удалены из нового derivative.
Original frozen probes сохранены как исторические доказательства, product code
не меняется. Реальный Source-owned FIFO/controller fence ещё не реализованы.

Innovation magnitude48 не равно adjacent phase jump48: +47.52→−47.52 остаётся
обязательным отрицательным случаем и предметом согласования guard. Поэтому
Phase0/plan/checklist/analyze/issue sync пока открыты, after_plan не выполняется.
Следующий шаг — проверить и устранить именно этот разрыв семантики, затем
принять согласованный clock design; не повторять уже доказанные quality cases
вместо продвижения к реализации.

### Соседний переход: native counterexample и исправление — round168

Не оставлен только как предполагаемая проблема: generated QPC ±40frames
после2s при48000/fixed480 native дал adjacent79.9968/maxinnovation41.5589,
raw mapperhealthy, phase modelcontinued299blocks. В следующем prototype
добавлен отдельный raw-phase step guard48, независимый от accumulated Sinc
correction. Теперь тот же случай прекращён приstep79.9968 иinnovation40.2224,
prefix200blocks; late Source calls fenced. Existing12quality results
численно совпали,13healthy/6eight-ms-fault/backlog regression снова PASS.

Independent review Source025eccaf… узко принял formula/order; current raw mapper
и tag mutation before phase failure не скрываются. Это source-step safety
semantics, не exact legacy output decision-set equivalence и не принятый §5.
Конкретный gap round167 исправлен только в prototype. До product code остаются
численные края/точный waveform partition/full common prefix/resource layout,
согласованные design artifacts/checklist/analyze/issues и отдельное решение
живого raw VM clock_drift. Установленный пакет этой проверкой не изменён.

### Независимость от размеров пакетов и обработки — round169

Нативная проверка nominal ненулевого сигнала выявила 7 несовпадений из44:
при выключенном controller все22 сравнения совпали точно, при включённом
менялись значения, но не начало/длина. В исследовательском successor команда
не реагирует на feedback внутри одного100ns тика в source-frame единицах.
Это точность представления двух идеальных округлённых меток, не обещание
точности WASAPI; raw budget/flags/step48/innovation48 не изменяются.

Теперь44/44 сравнения имеют max_error0. Дополнительный driver независимо
вычисляет полный nominal support, включая неполный хвост до timeline и число
полных480-frame блоков:66 прогонов/44 сравнения PASS.12/12 quality и все
прежние healthy/negative/backlog cases PASS. Independent review узко принял
метод, условность команды и формулы границ, не весь clock design.
Подробности: contracts/windows-clock-candidate.md и validation Round169.

Номинальное разбиение данной fixture больше не открытый пробел, но это не
общая гарантия для dynamic ratio/любого origin/длинной записи. Следующий шаг:
численные границы origin/counter/cursor и насыщенного controller, согласование
guard/publication semantics с §5 и реальные memory/controller boundaries.
Raw VM clock_drift отдельно остаётся нерешённым. Phase0/Phase1/checklist/analyze/
issue sync не объявлены завершёнными; optional after_plan отложен до принятия
всего плана. Source/apps/windows и установленный пакет не изменены.

### Большие начальные метки и реальная опора ядра — round170

Nominal origin matrix сначала отказала на8k/origin0: ideal full-support range
`[96,2310)`, фактический Source`[97,2311)`,2214samples в обоих. Не добавлен
count tolerance и не сдвинут output насильно. Наблюдение actual native input_ptr
подтвердило полный диапазон чтения32samples: исключённый startup j96 содержит
unobserved−1, j97/j2310 полны, j2311 использует input400 вне[0,400).
Source отбирает весь фактически поддержанный диапазон. Ideal FAIL сохраняется
отдельно как различие rational и sequential-double моделей, не дефект Source.

792partition comparisons/1188Source runs прошли короткую nominal matrix11rates,
6QPC origins (до околоUINT64_MAX),6start offsets и3partition/drain variants.
Границы проверены по independently observed actual kernel, values — с прежним
1e-5; partition errors0. First-origin integer conversion обоснована дляuint64q
через quotient/remainder и period625: G/int64,residue/phase/positive first ratio
имеют конечные явные границы. Dynamic counters и feedback этими выводами
не закрыты. Code reviewer узко Approved isolated sequential finite observer.

Следующий обязательный вопрос — большие elapsed/input/output counters и
насыщенная динамическая команда без потери текущего phase/error accounting;
затем согласование guard/publication semantics и реального staging ownership.
Это продвижение Phase0, не принятый полный design/§5 и не изменение installed
клиента. Raw VM clock_drift и все сквозные release/паритет-гейты остаются открыты.

### Расчёт остатка при больших счётчиках — round171

Введённые numeric states выявили ложные команды и выбор соседнего центра в
старом исследовательском Source при больших счётчиках. До одного часа таких
ошибок в проверенной матрице не обнаружено; это не объяснение живого VM сбоя.
Successor вычисляет feedback через целочисленные whole/remainder части,
соседний phaseStep — через packet delta, сохраняет actual local native cell
для anchor lookup и прежний продуктовый input cap2^52. Новый допуск часов,
сброс Sinc, округление его cursor или публикация неподтверждённой опоры не нужны.

16896 numeric states/10 guards,792 actual-kernel partition comparisons,
12 quality и прежние healthy/negative/backlog scenarios PASS в native Windows.
Это исправление внешнего Phase0 prototype, не apps/windows или установленного
клиента. Следующий объём — динамическое насыщение/phase accounting и реальные
staging/session boundaries, принятие §5/checklist/analyze/issue sync. Не повторять
nominal origin matrix без изменения затрагивающего её кода. Raw VM clock_drift,
защищённое хранение и сквозная приёмка Windows остаются открытыми.

## T119: нативное календарное подключение — 2026-10-02

Lane: high-risk-feature, no deploy. Clarify в spec.md от2026-10-02: дополнительных
продуктовых решений нет; общий F279 сценарий включён в US2/FR-002/005/006.
Constitution pre/post design: PASS для этого среза — нет web capture authority,
URL из страницы, новой provider integration, credentials egress или второго UI;
visible controls, owner/session/deletion и release gates сохранены. Это не PASS
общего clock/Phase0 и не разрешение кода до reviewer/analyze/issue sync.

Порядок внутри T119: сначала portable strict payload/response/URL/state/fence
регрессии; затем existing DesktopApiClient + WinHTTP GET join-target и owner-
scoped async continuation вне UI; затем единый opener/state owner для WebView,
MeetingReminderPresenter/AppMain и нативного меню. Использовать существующие
JSON reader, UUID validators, dispatcher, alive token и auth generation, не
строить второй HTTP client/service или generic process launcher. В WebView2Host
добавляются только calendar_join/cancellation-only calendar_join_cancel/reply
по bridge §10 и trusted delegated click;
Browser standalone handler/общий HTML остаются серверными. Bootstrap handshake,
nonce/replay и frame policy не обходятся «совместимым» отдельным handler.

MeetingReminderModel больше не авторизует launch сохранённым meetingUrl:
event ID/context/current deadline передаются общему resolver. URL validation
остаётся общей для всех native entrypoints; нынешний safeMeetingUrl переносится
в единственную проверку и приводится к F279 fixture, не сохраняется параллельным
legacy fallback. Snapshot API остаётся совместимым, необязательные URL поля
не являются разрешением. Operation busy охватывает resolver/launch/dialog,
completion checks не освобождают новую операцию. Current проверяется до OS
dispatch и после async completion; уже переданный ОС переход нельзя отозвать,
но поздний результат не запускает Record/новый переход и не меняет другой UI.

Launcher: existing C++/WinRT Windows.System.Launcher, штатные URI associations;
browser-only/recovery применяет IgnoreAppUriHandlers=true, без UWP-only
TreatAsUntrusted/автоматического FallbackUri/смены default apps. Из-за возможных
различий registered Windows Zoom/Teams/Телемост handler installed acceptance
обязательна: API availability/portable PASS не доказывают запуск нужного клиента.
Нет нового EXE path discovery, shell command или macOS identifier в Windows.
Выбор приложения определяется только validated host/path, не provider_family
источника календаря; неизвестное семейство не переводит корректный Zoom/Teams
адрес в браузер. Browser-only означает отсутствие поддерживаемого сочетания
host/path либо допустимый нестандартный порт. Эти контрпримеры входят в первые
fake resolver/launcher регрессии quickstart §13.

Артефакты: bridge §10, data-model §8, quickstart §13; research фиксирует источники
и альтернативы. T119 не закрыт; общий analyze повторяется после независимой
проверки затронутых требований. Hardware/audio/storage/billing gates сохраняются.

Уточнение launcher: preflight QueryUriSupportAsync отличает отсутствующий
custom-scheme handler от неизвестности/отказа installed клиента; отсутствие
открывает HTTPS в browser-only режиме, ошибка допускает только явный recovery.
Resolver deadline15s проверяется как whole-resolver-call, не переигрывается каждой
частью ответа; expiry/cancel сохраняют worker lease до actual completion.

### T119: единая операция подключения — уточнение 2026-10-04

Lane остаётся existing high-risk slice, owner #7540/T119. Clarify:0 новых
пользовательских вопросов; это реализация уже выбранного сценария Mac.
Pinned EmbeddedCabinetCalendarJoinBridge.join ждёт CalendarMeetingOpener.open
до terminal reply, а open ждёт confirm → fresh resolve → browser completion.
Поэтому сохраняем один request `opening` во время recovery, не оживляем failed.
Начальный resolver deadline = принятие действия+15s; recovery resolver deadline
= явное подтверждение+15s. Время очереди входит в соответствующий budget,
chunks его не обновляют; lease/action identity остаются прежними. Отдельного
15s OS/dialog timeout нет ни в целевом Mac, ни в bridge §10; его не добавляем.

Один UI-thread CalendarJoinOperation в Shell/CalendarJoinOperation.* хранит
operation ID, exact ephemeral context snapshot (origin/owner/workspace/auth
generation/token и source=document generation/nonce либо native action
epoch/identity), event/request UUID, внешний state/safe reason, resolver deadline
и pending work. Нет URL, хранения на диске, I/O или нового factory/interface.
Это минимальный общий state/fence owner, не отдельный HTTP client/launcher.
Последовательные child work получают отдельный монотонный work ID: completion
исходного resolver не может завершить recovery resolver той же operation ID.
Owner не принимает второй child work, пока первый физически pending. Adapter
сообщает completion только точного ticket после actual worker/OS/dialog exit;
helper не способен установить этот факт из bool cancellation либо elapsed time.
Ticket несёт общий cancellation flag, kind и absolute resolver deadline; поля
не приходят из web payload. Context содержит исходный monotonic action expiry
(для web без отдельного срока — max), epoch/identity, не продлевается recovery.
Переход initial resolving → opening разрешён только после resolver drain;
query/launch/dialog и recovery сохраняют opening. Handed_off допускается только
из opening после matching work drain и fresh context; native Record делает
потребитель после отдельного повторного current/readiness check, не helper.
Helper требует matching operation/work IDs для completion, удерживает terminal
pending work и возвращает неприменимый stale результат без нового эффекта.
Первые test-first проверки в CalendarJoinOperationTests.cpp: one busy между
источниками; stale/token/owner/workspace/document/native action; ровно15s;
terminal UI при ещё pending work; completion старого ID; recovery после
подтверждения со свежим budget, без оживления terminal/продления action expiry.

Далее AppMain переиспользует timer/future/packaged_task/alive/DispatcherQueue и
WinRT handles. Worker/OS/dialog terminal completion подтверждает завершение
своего pending work; отмена/exception poll/отказ очереди сами его не доказывают.
После UI terminal busy снимается только при actual completion; завершения
забираются независимо от interactionPermit. Один callback не освобождает новый
ID. Helper tests не доказывают этот adapter lifetime: integration source review
и delayed actual worker/native/installed tests обязательны отдельно.
Прежние completeAction early close и cancelDialog early slot release не
переносятся в Join. Card закрывается только handoff; Record-after-current и все
capture/storage/audio/release gates сохранены. До текущих independent checklist
и analyze продуктовый owner код не меняется; T119 остаётся открытой.

### T119: строгий wire и отмена документа — 2026-10-05

Existing high-risk T119/#7540, no deploy. Техническое уточнение не меняет
продуктовый сценарий. Constitution pre/post design: PASS для этого среза;
нет URL/capture authority из WebView, нового сервера/интерфейса/factory.
Reuse private strict JsonReader/calendarString/calendarEventId из DesktopApiClient
для точных join/cancel payloads и owned raw payload исходного envelope до SDK
Parse/Stringify. Envelope root добавляет один уровень к payload depth8; не
терять duplicate decoded keys/Unicode и не возвращать dangling string_view.
Bridge сохраняет exact origin/nonce/direction/message-id/64KiB guards.

Host принимает Join только из attached main RouteKind::meetings. Одноразовые
canonical request UUID хранятся до1024 за document generation/nonce без eviction;
replay не отвечает/не действует, новый запрос при полном наборе cancelled/not_ready.
Replay saved UUID проверяется до cap; UUID, отвергнутый по cap, не consumed,
его повтор допускает только тот же terminal not_ready без work/history growth.
Cancellation-only intent не создаёт UUID и передаётся только для matching pending
document request/event; card/menu child остаётся untouched. Pending owner сам
различает applicability и actual drain. До nonce/runtime script invalidation
отменяется старый Join и отправляется старому current document terminal reply;
поздний reply не получает новый nonce. HTMX observer сверяет итоговое DOM-состояние:
same canonical UUID сохраняет pending, removal/replacement отправляет cancel.

Порядок реализации: strict decoder/envelope portable RED→GREEN; host доверие/
route/replay/reply/invalidation; shim trusted click/HTMX/a11y; затем AppMain единый
operation owner с resolver/launcher/dialog/current auth и Record handoff. Source
review и Windows full solution compile обязательны для SDK ветви, которая не
компилируется portable CMake. Fake/compile не заменяют installed auth/UI acceptance.
T119 остаётся открытой. Новых задач не требуется: работа уже перечислена в T119.

### T119: Windows launcher adapter — 2026-10-05

Existing high-risk T119, no deploy; clarify остаётся current: новый продуктовый
выбор не нужен. Native target выбирается только из validated HTTPS по pinned Mac
host/path/port, с теми же Zoom query items и Teams conversion; Телемост — HTTPS
association. Все параметры подключения/fragment сохраняют значение; никакого
provider_family authority, произвольного custom scheme, EXE discovery или новых
Mac identifiers. CalendarMeetingOpener получает nativeTarget; один concrete
CalendarNativeLauncher в Shell/CalendarNativeLauncher.* владеет только одним
SDK query/launch handle. AppMain сохраняет общий state/fence owner и отдельно
ContentDialog; нет нового HTTP/dialog/recording service/interface/factory.

Уточнение после Microsoft RemoteAsync research: explicit IAsyncInfo.Cancel
может завершить proxy до underlying work. Поэтому adapter cancel снимает лишь
applicability, не вызывает OS Cancel/Close и не освобождает handle. Natural
Completed/Error заканчивает owned API child; Started держит pending. Непрошенный
Canceled или Status exception — отдельный indeterminate outcome, не drain:
безопасный terminal UI без handoff/Record, handle/busy удерживаются, повтор
блокируется до доказанного natural completion либо явного выхода/перезапуска
приложения. Это не дополнительный15s OS timeout. GetResults exception после
достоверного natural terminal — failure результата с matching API completion.

Старт различает busy/rejected/started/startFailed. Rejected до OS-вызова означает
no work; busy не меняет старый child. StartFailed при throw/null OS API означает
окончание синхронного dispatch scope без полученного owned async handle, а не
доказательство отсутствия OS side effect/underlying exit. Этот scope completion
позволяет снять только его child ticket, без handoff/Record/автоматического
fallback; повторное разрешение/переход — отдельное явное действие/recovery по
bridge10. Если handle получен, он сохраняется даже после reentrant cancel.
Guard ставится до native подготовки/current predicate/dispatch/poll; native
current проверяется непосредственно перед OS dispatch. Status exception не
выдаётся за startFailed. Query возвращает отдельные Available/AppNotInstalled/
AppUnavailable/NotSupported/Unknown, ничего не запускает. Только owner решает
следующий child после matching drain и fresh current. Native-only/browser-only
launch revalidates HTTPS; browser options IgnoreAppUriHandlers=true, без cookies/
auth/Store/fallback URIs. API true — handoff, не вход/идентичность получателя.

Test-first: native target/Zoom query/Teams/Telemost и unsupported/port fixtures;
TU-local fake Launcher statics с настоящими WinRT IAsyncOperation interfaces
проверяют delayed Started, discard без OS Cancel, terminal/GetResults faults,
unsolicited Canceled/Status fault без drain, reentry и browser flags. Нет
реальных ссылок/микрофона/запуска приложения из этих tests. Installed launcher/
dialog/bridge/Record acceptance остаётся отдельной. Перед этим adapter кодом
требуется ограниченный независимый requirements gate и current analyze.

### Clock Phase0 checkpoint — rounds177–178

Command1000 прошёл3600s generated native Sinc/AEC3 одной пары, но отдельный
constant±100ppm/no-jitter test выявил8/24 packet-partition FAIL на44100/48000Hz.
Повтор с общим drain480 сохраняет те же ошибки; это не зависимость только от
размера output batch. Не принимать packet-cadenced controller либо сужать §5
до nominal clocks. Следующий кандидат должен определить cadence команд и
получение QPC опоры на ней, включая quantization/lookahead/переменный packet/
EOS, затем пройти прежний допуск независимости waveform и quality/negative
corpus. Owned FIFO/Stop дизайн и upstream rawVM clock_drift сохраняют отдельные
ворота. Phase0 не завершена; after_plan hook/implementation не запускаются.

### Clock checkpoint — rounds179–180

Fixed-output-grid направление отделено от live admission: offline metadata
interpolation/480-output commands проверены, но rounded drift matrix остаётся
непройденной (1/24FAIL с llround,4/24FAIL при сохранении fraction). Exactinteger
QPC fixture с physical48000/declared48001Hz показывает oldpacket2/4FAIL против
grid4/4PASS. Это допускает дальнейшее исследование сетки, не adoption §5:
причинная доступность правой метки, неизвестный live Stop, FIFO/latency bounds,
quantization/jitter/quality и upstream VM refusal ещё не решены. Нельзя назвать
preloaded future metadata существующим live наблюдением либо сузить инвариант
до nominal. Phase0/Phase1 и implementation gate остаются открытыми.

### Clock checkpoint — rounds181–183

Внешний causal grid больше не preload-ит metadata, input фактически копируется
в fixed owned ring. Exactprofile0.5s/3s PASS4/4+4/4; второй случай упражняет190
ненулевых fractional QPC projections, error0. Received-only lookahead4800,
cap16384/peak10045 пока не product guarantee и не UI Stop protocol. Rounded
11-rate matrix остаётся11/132 FAIL по прежнему0.00001; нет silent reclassification.
Следующий технический gate: uncertainty/quality model с сохранением nominal
rounded regression и полного±100ppm/jitter/AEC/SC-003 покрытия, independent
completeness и FIFO admission/Stop bounds. Literal §5/FR/SC не меняются;
продуктовых вопросов не обнаружено. Phase0 продолжается, after_plan hook и
runtime implementation не выполняются. Fingerprints/evidence — validation181–183.

### Phase0 checkpoint — rounds184–185

T119: собственный A→B опыт показал, что read-only class handle не замораживает
command recipient. Actual native Telemost Join/identity и bounded launch design
не приняты; T119 не закрывать по home/lookup/Shell success. Пользовательские
ассоциации не менялись, собственный ключ/процессы очищены после завершения.

Clock: received-only causal grid с actual AEC3 прошёл12/12 прежних quality gates
на fixed packets с0.8ms metadata noise; mirrored-cursor phase<=.142306ms, не
независимый physical oracle. Trims0/0 наблюдаются, но не asserted. Ни waveform
FAIL11/132, ни capacity/Stop/unknown-end/SC-003 gaps этим не закрыты. Следующий
минимальный опыт переиспользует quality driver с переменными packets; interval
uncertainty и независимый физический oracle остаются частью технического плана.
Runtime implementation/after_plan hooks пока не запускаются; validation184–185.
Переменные packets с0.8ms noise отказаны по adjacent53.109>48 до quality verdict;
тот же driver с noise выключенным, rounded100ns, прошёл12/12. Не менять guard
и не считать clean PASS jitter приёмкой. Next uncertainty/independent actual
Sinc timing proof должен отличать measurement ambiguity от continuity violation
без ослабления historical waveform/quality нормы. Evidence — validation186.

Round187 выполнил9run/18gate actual AEC + independent actual Sinc position /
constant physical reference proof: actual error<=.121870ms, near corr>=.998522,
render gain−.127109dB, received interval truth containment. Это отдельное
основание продолжать проект causal grid, не принятие runtime. Existing §5 /
rounded FAIL / adjacent refusal / unknown Stop / FIFO bounds остаются; interval
proof использует simulation constant-rate/known exact origin, не WASAPI premise.

Round188: Reviewed truth driver прошёл follow-up source review и повтор9/18;
shift+2ms и observer count mutation дают точные ожидаемые отказы. Первоначальный
truth driver имел два P2 error/reporting path и сохранён как historical artifact.
Следующая работа: независимые dynamic full-support/unknown Stop границы и
worst-case FIFO/latency, без переноса исследовательских cap16384/innovation48
в product contract до принятия. Живые VM clock/T097 и custody gates отдельны.

### Phase0 checkpoint — rounds189–190

Actual native kernel observer независимо от mirrored cursor проверил полную
поддержку и конец реально принятого префикса:47/47PASS,source review Approved
driver only; additional native sample обнаруживает premature tail mutation.
IdentityStage/recovery0 подтверждает PCM/PTS/common blocks численно, не±0 bit
identity. Early EOS только после целого пакета; zero-packet/31–32 boundary,
производственные admission/twoEOS/finalizer/writer этим не закрыты.

Capacity audit: приём→полный drain обязателен для условных bound; innovation48
относительно QPC не даёт постоянной границы nominal−native. Frozen grid команды
ограничены<100s. Условный high-rate bound16710>cap16384 не доказывает достижимый
overflow, но запрещает считать cap достаточным по прежним peaks. Реальные
admissions8000Hz достигли10075 unread до первого open drain, disproving4864;
delayed48000Hz отказал следующий480 при16320 без потери accepted input/metadata.
Два отдельных native опыта PASS,source review последнего запрошен. Следующий
минимальный research: численная/достижимая high-rate граница и lifetime, без
новой quality matrix вместо этого и без cap/guard adoption. Full Phase0 ещё
не завершена; after_plan/implementation/hooks/задачи не закрываются. Fingerprints
и условные latency bounds — validation189–190; historical waveform/jitter/rawVM,
custody/SC-003/installed UI gates остаются открытыми.

Bounds source review: Approved только startup-before-EOS/terminal refusal после
уточнения ошибочной Main формулировки про полный EOS. Historical Request Changes
сохранён; normal EOS/close этого driver не заявляются, Source/runtime неизменны.

### Clock Phase0 checkpoint — rounds191–193

Только расширение external q domain<3601s позволило воспроизвести реальное
staging переполнение healthy192000Hz/−100ppm/variable input примерно332.64s.
Nominal readiness n+4800 расходится с consumed input; это не произвольная
задержка потребителя и не raw clock fault. Условный numeric review требует
конечных/монотонных inputs и ограниченных счётчиков,не заменяет native hour QA.

Received-QPC readiness + обратная соседняя q→input projection проверена как
отдельный Ready600s прототип:peak10043/обаfinished/timeline close59999blocks.
Initial empty-second-source ошибка сохранена,поправка разрешает только startup
wait; lost metadata/origin guard сохраняются. Pruned делает очистку metadata
независимой от controlled/holdTail; её47actual-support/negative-tail PASS не
переносят Ready600s на новый source. Новая rounded132matrix20FAIL(ранее11),
хотя44nominal/66uncontrolled PASS/error0. Adoption ещё запрещена: решать
uncertainty/cadence waveform вопрос,не увеличивать cap/tolerance ради PASS.
Actual AEC quality,длительная Pruned,full FIFO/latency/Stop/custody/installed/live/
physical gates остаются отдельными. Phase0/after_plan/implementation не закрыты.
Source/verdict/pins/точные причины отказов — validation191–193.

### Clock Phase0 checkpoint — rounds194–196

Received-time weighted local fit уменьшил132waveform FAIL20→13,не PASS.
Actual native trace и отдельное endpoint сравнение при одномratio выявили
limiting kernel gap4.3008476e−5 на одном generated44101/+100ppm случае.
Исследовательская window correction32→31/exactzero дала5/132FAIL при прежнем
.00001;не внедрена. У неё window center15.5 противsinc16:симметрия/частотная
характеристика/aliasing/AEC требуют отдельного обоснования,не просто adoption.

Новый actual trace worst23737nearEOS теперь внутри однойcell,positiondelta
.00044581189 inputframes:оставшийся вопрос rounding/clock-fit/EOS-held-command,
не только integer boundary. Следующая работа — объяснить этот локализованный
временной остаток и выбрать минимальный корректный clock/kernel подход с
неизменными guards/tolerance,потом fullsupport/quality/lifetime/capacity/Stop.
Source review Approved только researchmath/causalflow/counterexample;runtime
не принят. Ниphysical/live/installed gates,ниtasks/normative§5 не закрываются.
Phase0/after_plan/implementation ещё открыты; pins/verdicts — validation194–196.

### Clock Phase0 checkpoint — rounds197–199

Actual CELL trace локализовал estimator/position divergence ДОEOS:наopen
out16800 delta−.0719tick,holdTail позже сохраняет разные команды иувеличивает
остаток. Нельзя лечить только Stop/horizon радиPASS. Constant/exact-origin
quantization interval research уменьшил132matrix до1FAIL,но егоузкиеpremises
не доказаны дляWASAPI/noisy/changingclock. Outward numeric derivative+3guard
cases сохраняет1FAIL1.1416152e−5,не passed .00001. Initialcompilefail сохранён;
source review толькоconditionalresearch,не runtime принятие.

Следующий gate — uncertainty/first-anchor/changingclock model,faithful exact
continuousmapping иобоснованное kernelwindow/quality;не переносить идеальные
clock premises впубличныйпродукт. Норматив§5/FR/SC/tasks/checklist state не
меняются,Phase0/after_plan/implementation остаются открытыми. Evidence197–199.

### Clock Phase0 checkpoint — rounds200–202

Симметричное окно native Sinc устраняет предельный cell-boundary jump на
33 базисных импульсах при пяти ratio; 5445 algebra checks прошли.
С unchanged Fit всё ещё5/132 waveform FAIL при .00001. Новые девять12s
actual AEC/physical cases с fixed packets и noise0/±.8ms дали18/18 PASS:
не отменяют waveform FAIL и не являются полным спектральным/hardware proof.

Exact-first/constant-period модель отдельно отвергает четыре входа,
принятых actual ClockMapper: неизвестная начальная дробь, ошибка первой
метки, изменение частоты и измерительный шум. Эти premises нельзя использовать
как целевое решение или расширить raw отказ без согласованного общего проекта.
Следующий расчёт должен учитывать неопределённость обеих опор и изменение
частоты; сохраняются точные непрерывные метки, исходные guards, .00001 evidence,
full-support/quality/bounded lifetime/Stop/custody. Phase0 не закрыта;
runtime не изменён, installed UI заблокирован свежим CUA lock наблюдением.
Подробности, отрицательные результаты и pins — validation200–202.

## Актуальный порядок: независимый срез хранения — 2026-10-02

Явное решение владельца в spec.md разрешает T115–T118 независимо от открытой
clock Phase0 T094–T096 и календарного T119. Этот раздел заменяет прежний общий
запрет начать storage implementation до завершения всех исследований; старые
checkpoint-разделы выше фиксируют состояние на момент соответствующих опытов.
Требования, численные допуски и условия выпуска не меняются.

- **Storage Phase0:** T114 принят в ограниченном объёме исследования механизма.
- **Storage Phase1:** protocol `contracts/windows-protected-local-custody.md`,
  data-model §12 и quickstart §12 приняты как проектирование T115:
  `checklists/review-2026-10-02-storage-independent.md` PASS112/112,
  scoped storage analyze CRITICAL=0/HIGH=0, issue-sync #7443–#7446/canon PASS.
- **Собственный допуск:** все reviewer-owned checklist items подтверждены;
  analyze storage-среза имеет CRITICAL=0/HIGH=0 и неразрешённых уточнений нет;
  T115–T118 имеют актуальных владельцев GitHub. Общий F200 PASS не объявляется.
- **Реализация:** T116 → T117 → T118, сначала регрессии на искусственных данных.
  Первые ограниченные шаги T116 — wire/identity/bounds/integrity primitives
  и bounded incremental hash в существующем `Storage/Sha256.*`,
  затем durable logical IO и нативные adapters, затем все существующие
  producer/reader/queue/finalizer/upload/playback/delete точки. Неподключённый
  codec не считается защищённым приложением и не закрывает T116.
- **Независимые работы:** clock и календарный запуск продолжаются в собственных
  контрактах. Их недостатки не маскируются storage PASS и не попадают в код
  под видом упрощения зависимости.
- **Общая приёмка:** T118 не заменяет T083/T087/T088/T063/T071/T094–T097,
  физический x64/60min/AEC, доступность, install/update/rollback и доверенную
  подпись. Реальная миграция inventory и установка сборки только после их
  применимых gates; это решение не разрешает production или публичный выпуск.

Constitution II/III/IV/VI сохранены: локальная защита не меняет серверную
наблюдаемость, права аккаунта, Stop/индикатор, удаление или обязательный review.
Risk/validation lane остаётся high-risk-product. Общий after_plan hook пока
не выполняется: clock/T119 планирование не завершено; корневой AGENTS.md стабилен.

## Поправка масштабирования хранения — 2026-10-03

Владелец явно принял detection-time tradeoff в spec.md. Для больших
canonical/media/playback objects используется отдельный packed v2 по
`contracts/windows-protected-packed-custody.md`; metadata v1 и его full
resolver/no-rollback не меняются. Предыдущие измерения O(N²) full DATA scans
не являются доказательством sustained capture. Продолжать оптимизировать
только hash provider при сохранении этих scans недостаточно.

Decision: per-record user-scope DPAPI+SHA, один постоянно удерживаемый container
HANDLE, bounded radix64/depth3, две фиксированные защищённые head cells.
Новые данные/изменённые paths и обе heads проверяются перед ACK; unchanged
subtrees наследуют proof только того же GuardOwner. Любой ownership gap и
ambiguous publication требуют полного streaming verify прежде normal use.
Старую порчу можно обнаружить позднее при read/full verify — это принятый
компромисс, не новая гарантия защиты от disk rollback или мгновенного отказа.

Alternatives rejected: собственный AES/DEK/nonce lifecycle без измеренной
необходимости, plaintext temporary files, unlimited handle/cache inventory,
lazy cold authority, per-checkpoint full recording scan. Исследование
`checklists/research-2026-10-03-scalable-custody-proof.md` §11 обосновывает
выбор primitive; normative wire/proof определяется контрактом, не исследованием.

Constitution check: visible capture/Stop, privacy, logical v5, session access,
delete intent и release gates сохранены. Новая область требует повторного
T115 independent checklist/analyze; прежний PASS не переносится автоматически.
Принципы constitution не изменяются. Все исходные memory/IO/audio tolerances
сохранены; no wall-time promise для зависшего storage/native operation.

Dependency order в существующей T116, без параллельных lifecycle owners:

1. После scoped design gate — RED exact v2 wire/entropy/context/DPAPI failure
   tests; затем bounded codec с reuse ProtectedCustodyCodec primitives.
2. Native continuous GuardOwner + positioned append/flush/readback + две heads;
   failure cuts, actual release/reacquire и forged proof tests до adoption.
3. Один persistent-tree update + pinned reader/Clone + shrink/ZERO/seek;
   budgets/cache/pins до allocation, path proof не serialized verified flag.
   Следующий bounded этап — worker-only Tree.setSize по packed §4: общий
   transition/publisher с append/replace, recursive range trim/explicit ZERO,
   максимум7 NODE+1 DATA, два независимых structural readback. Сначала RED
   shrink→grow/pinned prefix/EOF/64GiB/same-size stale, затем реализация и
   actual native failure cuts; arbitrary partial Write/stream adapter и
   подключение приложения не принимаются одним этим этапом.
   Затем существующий `ProtectedCustodyWriter` получает packed open и reuse
   одного State/dirty/API по packed §6.0: сначала RED partial/cross-block/
   sparse/pending-vs-pinned/shrink-regrow/отказов, затем реализация через
   проверенные appendBlock/replaceBlock/setSize. Нового Tree Write API и
   параллельного writer backend нет; без §6.1 это ещё не consumer adoption.
4. Generated sequential recording measurements: records-per-checkpoint не
   растёт с длиной; длительный cadence/Stop проверяются отдельно от big-O.
5. Strict package.v2 refs по packed contract §6.1 и интеграция существующих
   V5/MF/hash/upload/finalizer consumers без plaintext путей. До неё primitive
   не приложение; этот schema gate проверяется до consumer adoption.
6. T117 migration только после проверки exact migration.v2 contract §6.1
   и его собственного review; legacy/v1 inventory не автоматически переводится
   в v2. Физический v1 codec служебных metadata сохраняется.
7. T118 полная generated/installed/native матрица; physical x64, real audio,
   accessibility, external signing и release acceptance остаются отдельными.

До повторного design/checklist/analyze исходный T115 принят только для v1;
поправка не считается реализацией и не закрывает T116–T118. Частичный gate
wire/owner/tree не разрешает внедрить непринятый metadata/migration lifecycle.

## Приватная пауза T120 — проектирование 2026-10-04

Lane: high-risk-product. Clarify повторно сопоставил уже одобренный Mac
F284 c8d67c… с реальным Windows flow; новых продуктовых предпочтений нет.
Контракт — desktop §3 «Приватная Pause/Resume», хранение — local custody §3.
Исправление не разрешается старым packed Reader source acceptance.

**Decision:** переиспользовать существующие capture owner/dispatcher/timeline/
writer; подавление должно сохраняться в самих ещё не записанных данных,
а не зависеть только от bool во время drain. Точная граница Resume охватывает
producer FIFO, извлечённые/in-flight/prefetched batches и накопленный timeline.
Снимок остатка заменяется, не суммируется. Уже записанный участок не меняется.
Непрерывный producer не заставляет Resume ждать пустую очередь.

**Порядок внутри T120, без новых задач-дублей:**

1. RED в существующих Timeline/CaptureFaultState tests: delayed render,
   pre-Pause pending/paused queued/in-flight данные, частичный prefix,
   повторные Pause/Resume и продолжающийся producer. Ошибки исходных данных
   не скрываются обнулением; system/PTS/count/AEC/Stop сохраняются.
2. Минимальный timeline/dispatcher prerequisite с проверенной границей,
   без изменения manifest/UI принятия и без заявления готовой приватной Pause.
3. T116 внедряет защищённый writer/metadata путь. Перед durable integration
   fixture exact logical v5 privacySegments из Mac должен иметь подтверждённые
   поля/serialization, а existing validator — принимать только известные формы.
4. Writer подтверждает OPEN до опубликованной паузы. Resume с недоступной
   границей остаётся paused. CLOSE после успешной границы best-effort;
   при отказе старый durable OPEN остаётся, Resume не отменяется.
5. Асинхронный текущий pipeline AppMain сохраняет одного владельца и порядок
   writer. UI/Stop не ждут file I/O или освобождения очереди; late completion
   не меняет остановленную/новую сессию. Затем actual installed acceptance.

**Точечная поправка вместимости T116:** manifest logical cap64KiB вместо4096B,
как существующие служебные metadata. Не новый backend/журнал: один прежний
block/codec/owner. Общий owned64MiB, native job2MiB, blocks256KiB, root4096,
cache/pins/jobs/queue и audio limits сохранены. Cap проверяется до OPEN по
полному сериализованному payload; нельзя убирать старые сегменты или назначать
случайное число пауз. Неуспешный OPEN виден пользователю. Новый размер не даёт
authority/cold proof и не меняет entropy/wire/schema. Изменение требует
отдельного текущего review; source tests4096B остаются историческими.
Existing LocalRecordingPackage size4096+exact regex тоже надо согласовать,
не ослабляя проверку hash/format/ownership/version или вводя plaintext fallback.

Constitution before/after design: I/II — видимый capture/Stop и ошибки сохранены;
III — сервер/credentials/egress не меняются; IV — сегменты принадлежат пакету
и его существующему удалению; VI/VII — независимые требования/source/runtime
проверки обязательны. История сегментов не новый consent gate. Public signing,
physical x64/60min/AEC/accessibility/installed gates не закрыты этим проектом.

До independent requirements checklist, текущего analyze и owner T120 код
capture не меняется. Полный T120 также зависит от незавершённого T116;
принятый prerequisite не закрывает ни одну из этих задач.

### T119: ближайшие встречи в нативном меню — 2026-10-05

Existing high-risk-feature/no deploy, T119/#7540. Clarify: продуктовый выбор уже
сделан; отдельной Windows страницы, второго API client или второго owner нет.
Phase0 reference — собственные CalendarTray.swift, CalendarMeetingOpener.swift
и CalendarContextModels.swift на `721b5125d799ea798a4af0b3625e18d3c1109039`.
Constitution before design: I/II — меню не даёт Record; III — прежний native
auth/endpoint без новых секретов/egress; IV — эфемерная проекция, не новый
долговечный artifact; VI/VII — независимые требования/source/installed gates.

Phase1, точное сопоставление:

1. Уже принятый owner/workspace snapshot `/api/v1/desktop/calendar/upcoming`
   одновременно питает карточку и меню. Для меню: сортировка startsAt, затем
   eventId, первые12. Не фильтровать по canSurface/due/dismissed, capture или
   локальному quiet/reminders. Server show_upcoming_title/show_upcoming_time —
   authority; missing/null default true как Mac, present non-bool — весь snapshot
   invalid. all_day missing/null=false, non-bool invalid. Добавить только эти
   поля существующего decoder; старые обязательные поля и bounds не ослаблять.
2. «Ближайшие встречи»; название available и непустое после пробелов — название,
   пустое available — «Без названия», private/unavailable/скрыто — «Встреча».
   Время HH:mm в существующем пользовательском часовом поясе; all-day — «Весь
   день»; скрытое время не рисовать. Native font/DPI width fitting, полный safe
   текст в accessibility, никаких private title/URL в истории/diagnostics.
   Нет безопасной snapshot HTTPS-ссылки либо meeting_link_present=false — строка
   видна, но не активируется. Snapshot URL — только availability, launch всегда
   через fresh join-target. Существующие Record/Stop/settings/history сохраняются.
3. Проекция — отдельно от card eligibility и failed-card retry. Очищается при
   ошибке refresh, invalidation/auth switch; старый successful snapshot не
   продолжает authorizing menu. При изменении отображаемого списка/flags/auth
   EndMenu прекращает tracking; локальная копия rows/handlers живёт до выхода
   TrackPopupMenuEx. Выбор несёт frozen event identity, не индекс новой проекции.
   После loop проверяются alive/window/current projection до callback; после
   callback нельзя обращаться к потенциально уничтоженному Impl.
4. Selected native menu action хранит owner epoch, eventId/startsAt/endsAt,
   подтверждённую target identity и свой UUID. Срок не берётся из карточки:
   lifetime события endsAt из исходного snapshot один раз переводится в
   steady_clock expiry на принятии выбора (remaining=endsAt-wallNow; <=0 reject,
   checked conversion/overflow fail closed). Это техническое выражение окончания
   актуального события, не произвольный15s/120s timer. Refresh, Retry и смена
   часов не продлевают исходный expiry. Новое открытие меню даёт новый source
   UUID, но не оживляет старый flight.
5. Normal popup close после выбора не отменяет уже принятое действие. EndMenu
   из-за изменения только presentation прекращает старый selection, но не
   отменяет уже принятый flight, если его event/owner/target ещё актуальны.
   Удаление/замена выбранного event/target, unavailable projection, auth,
   interaction invalidation/exit или original expiry отменяют применимость.
   Не менять card pendingActionExpiry ради menu. Current перепроверяется до и
   после каждого resolver/OS/dialog ожидания; closing/Hide/Cancel не actual drain.
6. Общий CalendarJoinOperation/AppMain flight + существующие resolver/launcher/
   ContentDialog. Menu source не использует reminder pending action и никогда
   joinAndRecord. После resolver/launch failure, пока source current: «Не удалось
   открыть встречу», «Проверьте подключение и повторите попытку. Если событие
   изменилось, обновите календарь.», «Повторить подключение»/«Отмена» как Mac.
   Browser recovery остаётся отдельным существующим подтверждением.
7. Retry dialog — owned work того же общего owner, не второе independent modal
   состояние. До его показа все предыдущие actual work завершены; failure UI
   не завершает owner до dialog drain. Старый attempt не оживляется: после
   matching dialog terminal, явного current Primary и свежей проверки source
   старый attempt заканчивается failed, новый request/operation начинается с
   прежним source/expiry и acceptedAt=момент click. Вся замена — одна защищённая
   от reentrancy UI-thread transition; общий busy не имеет admission gap.
   Новый resolver budget=click+15s включает ожидание закрытия диалога. Отмена/
   stale/auth/expiry не показывают новый Retry, не повторяют launch. Неизвестный
   SDK/dialog exit удерживает handle/ticket/busy до доказанного natural terminal
   либо выхода процесса. Никакого автоматического повтора или cached URL.

Порядок: decoder tests/fields → отдельная menu projection в существующем model
и presenter → frozen native tray rows → common owner menu admission/Retry.
Файлы: Upload/DesktopApiClient.*, Shell/MeetingReminderModel.*,
MeetingReminderPresenter.*, WindowsTray.*, AppMain.cpp, существующие Contract/
Package tests. T119 уже содержит этот объём; новая задача/дубликат issue не нужны.
Quickstart §16 задаёт проверки; bridge §10 и data-model §8 остаются authority.

Constitution after design: PASS для проекта этого среза, без новых capture,
server/macOS/credentials/storage writes. Gate M1 закрывается только текущим
независимым requirements review + analyze; код до них не меняется. Optional
agent-context hook не запускается: root AGENTS.md уже маршрутизирует активную
фичу и остаётся стабильным. T119/installed/physical x64/public release не закрыты.

### T119: пользовательское время меню — уточнение Round243, 2026-10-05

Existing high-risk-feature/no deploy, тот же T119/#7540. Clarify завершён без
новых вопросов: ранее выбранный точный Mac требует account preference, не
always-system localtime. Constitution before research: II — только presentation,
не capture/Join authority; III/IV — без secret egress, persistence или нового
серверного artifact; VI/VII — independent requirements/source/native/installed.

Phase0: pinned DesktopUserTimeContext.swift на `721b5125d799ea798a4af0b3625e18d3c1109039`
читает graf-time-user/session/preferred после cookie reconciliation и сравнивает
revision/current-document/documentURL. CalendarTray использует этот контекст,
системная autoupdatingCurrent — fallback. Existing server base.html уже содержит
metadata и graf-workspace. Windows.Globalization.Calendar принимает IANA zone;
native DST/HH:mm возможны без своей базы зон или новой зависимости. Research
содержит первичные ссылки; наличие API проверяется отдельно на Windows.

Phase1 — один ephemeral display-time context в существующем native owner:

1. WebView2Host читает metadata только из текущего доверенного главного документа
   после существующей cookie reconciliation/подтверждения native account. Allowed
   route kinds: meetings/meetingDetail/share/deletionReport/settings/nativeSettings/
   billing, с прежней allow+same-origin проверкой. Auth/provider/payment/frame/
   external/recovery/failed document не устанавливают context. Использовать
   существующий ExecuteScript/current-document lifetime, не новый web command,
   message payload, HTTP client, session-cookie reader или скрытый fetch.
2. Native-owned script возвращает только userId/workspaceId/sessionId/timeZone/
   documentURL из graf-time-user/graf-workspace/graf-time-session/graf-time-preferred
   и document.URL. Сырой результат <=2048 UTF-8 bytes; точный object пяти string
   fields, без decoded duplicate/unknown keys; canonical UUID IDs, zone <=100 ASCII
   bytes, documentURL <=1024 bytes. Null/missing/non-string/invalid result не
   создаёт предпочтение. Никаких cookies/token/meeting URL или содержимого формы.
3. Dispatch фиксирует native auth generation/account/workspace, session-token
   identity только в памяти, host document generation/nonce/URL и display context
   revision. Completion повторно проверяет alive/current trusted document,
   совпадение owner/workspace с native account и все captured generations. Данные
   не подтверждают auth самостоятельно. Stale callback отбрасывается, не стирая
   новый контекст; текущий invalid result сбрасывает preference в system fallback.
4. Epoch/revision меняются при auth/session/account/workspace/origin switch,
   logout, host detach/failed document и подтверждённой замене preference. Context
   хранит metadata session UUID, но он не заменяет native token/generation. До
   следующего accepted context нет reuse зоны прежнего аккаунта. Отсутствующее
   или пустое предпочтение использует свежую системную зону Windows; неизвестная
   непустая зона отвергается, context сбрасывается, old preferred zone не остаётся.
   Persistence/logging/diagnostics этого context запрещены.
5. UTC либо именованная IANA zone с '/' проверяется Windows.Globalization.Calendar;
   fixed current offset, ручная таблица IANA→Windows и локальное время вместо
   выбранной зоны запрещены. Native Gregorian/24-hour calendar и UTC instant
   дают HH:mm с DST на дату события; allDay → «Весь день», server hide-time →
   без времени. Проверить finite/range/overflow до преобразования ticks; отказ
   formatter не возвращает выдуманное время. Portable именованная зона не
   имитирует native proof. Уже имеющиеся formatter/UTF helpers переиспользуются
   по возможности, без второго owner/service/cache.
6. Accepted preference/system-zone change обновляет safe menu labels и прекращает
   tracking старого popup. Это presentation-only: уже принятое unchanged Join
   не отменяется и original steady expiry не продлевается. Cookie/token/account
   invalidation остаётся отдельной причиной отмены Join. Перед новым открытием
   меню labels строятся заново; сохранённое с сервера предпочтение проверяется
   на свежем подтверждённом документе, не по несохранённому значению формы.

Порядок: strict metadata decoding/current-context tests → native Calendar
formatter tests → actual host/account binding → frozen tray rows/lifetime →
common menu admission/Retry. Existing DesktopApiClient.*, WebView2Host.*,
MeetingReminderPresenter.*, WindowsTray.*, AppMain.cpp и Contract/Package tests;
нового server endpoint или задачи нет. Same-page timezone save/следующий document
refresh проверяются явно: состояние формы само не даёт native preference.
Прежнее утверждение полноты Phase1 относится к prior norm snapshot; Round243 M1
требует нового independent review + analyze до formatter/transport code.
Constitution after design: PASS по указанным границам, root/guidance неизменны.
Optional agent-context hook не нужен: root router остаётся стабильным.

## T116: подключение действующего защищённого потока — 2026-10-07

Lane: high-risk-product, существующие T116/#7444 → T117/#7445 → T118/#7446.
Это конкретизация local custody §5/§8 и packed §6.1, не новый формат,
продуктовый выбор или разрешение открыть рабочий профиль. Принятый Round275
проверяет закрытый старт настоящего NativeCapture; он не реализует запись.
Clarify: прежнее разрешение владельца на полный защищённый поток сохраняется;
новых предпочтений пользователя нет. Constitution before design: II/III/IV —
без открытых временных копий, смены account authority или ложного saved/delete;
VI/VII — независимое requirements/source review и нативные проверки.

### Один владелец и непрерывное владение файлами

Startup worker существующего NativeCapture создаёт внутреннее состояние store
в существующих ProtectedCustodyFiles/ProtectedCustodyMetadata. Оно удерживает
проверенные root/ancestor handles, store.id, фиксированные bootstrap/queue IDs,
независимые contexts, leases и принятые поколения. UI получает только значения
состояния; path, metadata pair и bool готовности не заменяют это владение.

Для действительно нового inventory: удержать native root ownership → streamed
проверка inventory → private ACL до bytes → exclusive создание случайных IDs →
защищённый пустой ledger и bootstrap → независимая повторная проверка обоих
слотов и inventory. Нельзя принимать пустым неизвестный root или создавать ID
поверх partial birth, reserved/prepared objects либо неподтверждённых данных.
Отказ сохраняет созданные артефакты и закрывает повторный birth; restart не
чинит их автоматически. Legacy inventory требует перехода T117, не load()
открытого реестра из regular startup.

Existing protected inventory использует текущие BOTH-slot semantic decoders
и связанные intent проверки. Readonly proof не превращается во writable.
Worker factory переиспользует State/openImpl и удерживает writable queue lease
без закрытия и повторного открытия по path. Existing commit-body используется
и path API, и внутренним owner-путём; второго publisher нет. Перед mutation
сверяются независимый context, admissible stage и фактически принятое base
generation под тем же ownership. Любой разрыв требует повторной полной
проверки; публичного READY setter либо «разблокировать proof» нет.

### Очередь и подтверждение результата

DesktopUploadQueueService сохраняет существующие domain helpers/serialization,
но mutation выполняется на ограниченной копии, не опубликованной projection.
Worker последовательно сохраняет один full candidate и удерживает его,
native lease и commit result. В UI пересылается value-only ticket из §5;
poll принимает фактическую generation и возвращает adoption ACK. Только
после ACK worker освобождает completion и допускает следующую mutation.
Передача future<CustodyMetadataCommit> с уничтожением lease на UI запрещена.
Очередь/результаты ограничены уже принятыми32 и общим memory budget.

Отмена до publication сохраняет старое состояние; после publication worker
завершает readback. Ambiguous сохраняет ownership и запрещает effects до
reconciliation. Stale account epoch не откатывает committed bytes: storage
принимает generation, но UI/network capability остаётся закрытой. Shutdown,
update и потерянный callback учитывают pending jobs и adoption, не только
видимый capture. Нового dispatcher, базы или сервиса сохранения не требуется.

### Подключение реальных потребителей

NativeCapture сначала poll'ит storage completions, затем проверяет общий
consumer guard. Иначе закрытый guard не даст принять собственный startup.
Внутренний pipeline получает подлинное store/package ownership; общий
storageWritable остаётся false до подключения **всех** content consumers.
Доступ к этому pipeline не даёт обычному Record обойти закрытый admission.

Действующий V5LocalRecordingWriter использует защищённые logical streams:
capturing package-state подтверждён до audio bytes, canonical checkpoints
сохраняют принятую cadence, WAV/AAC проходят existing MF stream adapters,
sealed package-state подтверждён до queue insertion. EOS → timeline close →
existing async finalizer сохраняется. Finalizer удерживает результат и lease,
возвращает pending до queue commit/adoption, не сообщает saved заранее.
Затем подключаются existing logical HTTP range/hash, playback и deletion/purge
с продолжениями §5. Plaintext URL/temp/ShellExecute и bool durable fallback
удаляются из рабочего content пути, а не остаются альтернативой при отказе.

### Проверка единого пути

Сначала generated-data RED на настоящем NativeCapture/controller, не отдельном
commit helper: genuine startup/birth → V5 append ≥30s по числу frames → EOS →
pending finalizer → sealed state → queue commit/adoption → холодный restart.
Existing CaptureSessionTestPeer заменяет только device audio и наблюдает owner;
он не устанавливает READY, IDs, generation или authority. Далее тот же пакет
проходит logical playback/seek, partial HTTP/reconcile и deletion ACK/purge.
Проверяются birth cuts/races, отказ до publish, ambiguous, stale epoch,
lost callback/shutdown и отсутствие открытых content-bearing файлов.

До независимого requirements review и scoped analyze код этого подключения
не меняется. Current-store identity/authority, typed result adoption и весь
generated vertical path принимаются отдельно от installed UI/hardware/release.
Constitution after design: прежние разрешения/Stop, квоты, privacy, deletion
truth и release gates сохранены. Tasks и reviewer-owned markers не меняются.
Optional agent-context hook не нужен: корневой router остаётся стабильным.

### T116: конкретная конструкция полного V5-пути — 2026-10-07

Следующий участок после SOURCE277: не отдельный reader/helper, а действующий
NativeCapture/controller → V5 → sealed package → queue insertion/adoption.
Lane остаётся high-risk-product; clarify выше и в spec.md действует, новых
продуктовых решений/форматов/задач нет. Перед кодом требуется независимый
requirements/analyze допуск именно этой конструкции; SOURCE277 его не даёт.
Constitution before design: II/III/IV/VI сохраняют Stop, отсутствие открытых
копий, account/deletion truth и отдельную приёмку кода/установки/оборудования.

**Factory и владение.** Existing retained storage worker вызывает закрытую
package factory в Metadata от подлинного StoreOwner. В Files переиспользуются
State/security/openRole и проверенная root-часть, а не повторный path-based
open/store.id. Общая удерживаемая root-часть не содержит mutable queue state;
дочерний owner не получает права работать с queue с capture/MF потоков.
Package directory создаётся исключительно с private ACL; existing directory
или любой partial birth — conflict/recovery-required, не reuse/автодостройка.
Идентификаторы package-state/canonical/container генерируются CNG внутри
factory, не приходят от UI/JSON/test. Native session directory ID — только
ограниченное имя, не доказательство authority. Child leases удерживают root.

Factory резервирует настоящие role identities, затем publishes package.v2
capturing с canonical LIVE ref через существующий commitImpl на удерживаемом
package-state lease. BOTH g1 indices/payload/context independently read back
до первого ACK. Лишь затем prepared canonical Files передаётся внутреннему
входу прежнего PackedOwner: тот же prefix/content/HEAD код, без второй реализации
и повторного createNew role. Packed check проверяет настоящий borrowed store
handle и все ancestors, не пропускает их из-за отсутствия собственного handle.
Empty BOTH packed heads → Tree::verify → прежний ProtectedCustodyWriter.
Canonical bytes разрешены только после capturing ACK и настоящего writer open.
При частичном birth созданные artifacts и ownership сохраняются, package scope
sticky failed; новая попытка не regenerates IDs и не объявляет пустой пакет.

**Writer и Media Foundation.** V5 получает private package ownership, не
пути открытых файлов. Его работа удерживается storage worker; на UI только
значения и polling, не native последний reference. Единственный mutator —
capture dispatcher; после workers/EOS/dispatcher fence и close timeline writer
передаётся existing async finalizer. Canonical checkpoints сохраняют cadence;
восстановление использует только complete480-sample frames, без padding/AEC.
WAV сохраняет прежний 48→16 kHz PCM алгоритм/RIFF u32 bound через logical IO.
AAC сохраняет PCM/MF цикл; output IStream → MFByteStream → SinkWriter с URL=null
и explicit MPEG4 container attribute. Штатный readonly Reader не становится
writable через bool, plaintext URL/temp fallback не остаётся в рабочем V5.

Тонкий writable IStream над тем же Writer имеет один charged serial state;
одна mutex охватывает cursor и целиком Read/Write/Seek/SetSize/Commit, включая
sticky ошибки, checked offsets/flags, bounded buffers и ZERO только extension.
MF thread ID не предполагается фиксированным; владение одним сериализованным
mutator не заменяется mutex только физического packed owner. Прямой доступ к
writer исключён пока adapter открыт. Finalizer не держит adapter mutex вокруг
WriteSample/Finalize. После Finalize он закрывает adapter access под этой mutex,
ждёт уже активные обращения, releases sink/byteStream/COM, затем checkpoint и
readback/release на worker. Поздний COM вызов видит closed без native доступа.
Underlying writer/native lease удерживается worker независимо от COM refs;
новый dispatcher/БД/сервис не требуется. Фактические потоки и teardown проверяются.

**Sealing и очередь.** Из фактически committed Tree snapshot получают exact
stamps и logical hashes. Media/playback immutable и проверены; protected
manifest публикуется последним, после него package-state sealed. Existing
semantic decoder/member inspection body переиспользуется на retained leases,
без закрытия writable ownership ради path reopen или создания raw-proof API.
Результат/codecs сами по себе не дают saved/upload/account capability.

Один bounded command/result существующего queue worker расширяется kind для
finalizer insertion. Pure enqueue факторизуется из существующего domain helper
на charged private QueueValue, не создаётся второй ledger. Recording work,
package/writers/native result остаются worker-owned до full insertion commit
и polling adoption ACK. Actual NativeCapture finalizer всё это время pending;
future с lease на UI и bool queue_.enqueue fallback удаляются из этого пути.
Normal sealed → pending row → saved только при ACK/current epoch; degraded
validated prefix → quarantined row/no saved. Short → durable discard intent,
не removed: purge/OS absence/removed ACK отдельны, преждевременного сообщения нет.
Cancel до publish сохраняет old projection/artifacts; после publish readback
обязателен; ambiguous запрещает следующий mutation до reconciliation. Stale
epoch принимает только physical storage truth. Shutdown/update/lost poll
удерживают active recording/result до native terminal/adoption, не бросают их
при остановке startup loop. Native fields очищаются worker до terminal values.
Global admission остаётся false до подключения HTTP/playback/delete/T120.

Изменение V5 охватывает всех callers, не только NativeCapture. Удаляются
production path constructors/PlaybackEncoder и destructor plaintext recovery,
а не оставляются dormant за false guard. Существующие V5/short-threshold,
offline/controller fault, protected-files и upload/recovery tests адаптируются
без удаления проверяемых свойств. Legacy read/migration требует generated
plaintext inputs только в изолированных test fixtures, не production writer.
Не копировать прежний writer целиком в новый test backend ради зелёных checks;
reuse native stream encoder/существующие минимальные fixture primitives.
AAC corrupted-mdat/native-hash отказные регрессии остаются обязательными;
нельзя заменить их fake encoder или исключить из полного набора.

**Приёмка конструкции.** Actual NativeCapture/controller, ≥3000 generated
10-ms кадров, настоящий factory/queue owner, capturing-before-bytes, EOS,
WAV/AAC, sealed, pending insertion/adoption, холодный restart. Peer заменяет
только device audio; не используется helper begin с session_.markReady().
Hardware/AEC fixtures допустимы, но storage readiness private continuation
вычисляется только из genuine capturing ACK/held owner; peer не ставит READY,
IDs/generation/authority и не открывает public Record. Дополнительно native
birth cuts/races/ACL, budget refusal, cancel/ambiguous/stale/shutdown, MF late
calls и отсутствие plaintext. Source-only ordering не становится runtime PASS.
Constitution after design: прежние gates не ослаблены; T116 и полный goal OPEN.
Root agent-context не обновляется: router/stack/active feature не меняются.

## T116: защищённая HTTP-отправка и принятие результата — 2026-10-10

Lane остаётся high-risk-product, T116/#7444. Это уточнение FR-012/013/014 и
local custody §5–7 после чтения настоящих transport/scheduler/storage worker.
Clarify 2026-10-02/03 остаётся действующим: новых пользовательских решений,
endpoint, wire schema, auth policy, partSize или формата хранения нет.
Конституция II/III/IV/VI: без plaintext, без повышения proof до account
authority, без ложного committed, независимая приёмка конструкции до кода.
Прежний scoped GO для V5/cold discovery не принимает эту интеграцию.

### Очередь, работа в фоне и подтверждения

Переиспользуются существующие DesktopUploadRecoveryScheduler flight/executor,
NativeCapture storage worker и QueueMutationTicket. Второго scheduler, реестра,
потока записи либо общего persistence framework не вводится. Нативные package
owners остаются только в рабочих потоках; UI хранит значения, cancellation и
состояние flight. Последний release native proof на UI запрещён, в том числе
при отказе создания потока. Получение genuine package pair и запуск
существующего executor выполняет storage worker, не UI. Полный inspection и
HTTP исполняются в существующем network executor отдельно от storage worker:
проверка содержимого или сеть не занимают единственного исполнителя
prepareRecording/finalizeRecording.

1. Выбрать строки только из принятого защищённого поколения. Existing rules
   pending/retry/uploading, retry budget, auth recovery и Retry-After сохраняются;
   максимум32 строк/результатов, один flight. Изменения prepare выполняются на
   charged private QueueValue. Для непустого flight prepare всегда сохраняет
   один full candidate, даже если domain helper не изменил ни одной строки:
   тот же logical payload публикуется как следующее generation и получает
   обычные committed/adoption ACK. false от helper не означает durable failure
   и не заменяет ACK. Для пустого выбора flight/commit/network не создаётся.
   Дополнительный metadata commit на непустой flight принят явно: не вводится
   пятый ticket state или отдельный no-change протокол, SC-003 проверяется.
2. До dispatch дождаться commit и adoption ACK. Storage worker получает genuine
   package pair через readPackage(directoryId), сверяет точные directory/session
   и sealedNormal. Тот же retained pair передаётся существующему executor для
   полного inspectProtected перед HTTP. UI не передаёт IDs/generation как proof.
   Перед запуском worker повторно проверяет value-only grant текущего account/
   authGeneration, cancel, исходную identity/status/attempts строки и отсутствие
   delete/update/shutdown. Grant не даёт filesystem authority. При изменении
   grant подготовленные owners освобождаются здесь, без HTTP.
3. Существующий network executor владеет retained inspection до завершения
   transport. Storage worker остаётся свободен для записи и сериализованных
   queue mutations. Result содержит захваченную row identity, store/queue
   context, auth epoch и cancel; не raw UI/controller/queue. Конкурирующая
   mutation никогда не запускает второй flight этого ledger.
4. После сети storage worker сверяет current row identity/status/attempts и
   epoch. На свежей копии **текущего принятого** поколения применяет server truth
   и terminal/retry status одним domain helper, затем одним full commit. Нельзя
   делать reconcile() и markUploaded()/markRetry() отдельными bool-записями.
   Retry-After/session-expiry UI effects допускаются только после ACK/current
   context; пауза HTTP не расходует retry budget.
5. Flight/result/busy/lease сохраняются при pending и потерянном poll. После
   committed принимается физическая generation даже при поздней смене account;
   stale completion не показывает данные и не запускает новую сеть. До publish
   stale epoch/row отвергает candidate: worker повторно проверяет актуальное
   хранилище, не пишет старый result в новую identity и только после native
   completion/revalidation освобождает flight. Следующий разрешённый retry
   заново получает server truth по existing sync-state.

not_committed сохраняет старую projection и закрывает effects до безопасного
retry; ambiguous сохраняет ownership/result и закрывает продолжение до readback/
reconciliation. Cancel/account change отменяет сеть, не уже начатый publish.
Shutdown/update ждёт фактического network/native выхода и принятия результата
либо повторной проверки storage truth; потерянный UI poll не уничтожает owner.
Storage stop predicate учитывает flight, а не только recording. Закрытие thread
handle/тайм-аут не является завершением работы. UI не ждёт native IO.

### Проверенные байты и один HTTP-body

ProtectedInspection даёт transport минимальный внутренний доступ к трём
проверенным refs/потокам выбранного слота: manifest/media/playback, length и
SHA256. Evidence остаётся semantic proof, не owner/session/upload authority.
Переиспользуется inspectProtected и общий production upload decision flow,
включая injected UploadSend. Нет второго parser, plaintext reopen/fallback,
file_size(ciphertext), перекодирования или нового session/UUID.

Прежний HTTP-part остаётся default4MiB, clamp64KiB–16MiB. Exact [start,end)
заполняется проверенными logical reads≤256KiB, digest считается по полному
body; part index, tail, невыравненный missing range и accepted offsets прежние.
Отказ/short read/cancel до заполнения всей части запрещает PUT этой части.
Полный hash неизменного pinned stream проверяется existing bounded hash helper.

В UploadRequest добавляется внутренний owning protected body: один
shared<const CustodyBytes> с charged control block; обычный body пуст для этого
запроса. Синхронный WinHTTP читает view именно этого owner, не копирует в string.
Owner живёт до завершения WinHttpReceiveResponse либо закрытия request handle
при ошибке; одного возврата WinHttpSendRequest недостаточно. Cancel не стирает
body во время native вызова. Handle закрывается в том же worker до release body.
Копия UploadRequest удерживает тот же charged owner, а не висячий string_view
или вторую открытую копию. Оба body одновременно — invalid input. Внешняя
схема не меняется. Буфер выделяется через existing CustodyAllocator до reads,
стирается CustodyBytes при последнем release. Не накапливаются следующие parts.
Request/response/hash/serialization buffers и retained flight/results также
учитываются общей квотой до allocation, включая capacity/control/Debug proxy;
нельзя зарезервировать только read scratch и оставить body/копии вне учёта.
64MiB owned, cache2MiB, pins32, native jobs4 не увеличиваются. Отказ бюджета
сохраняет принятые диапазоны; не уменьшает partSize и не включает fallback.

### Граница приёмки

До реализации — независимый requirements/analyze review этой конструкции;
до утверждения H1/H2 production HTTP не меняется. Затем RED на actual
NativeCapture ≥3000 generated кадров → protected insertion/adoption → release
owners → cold discovery → actual transport с подменой только сети → protected
result commit/adoption. Дополнительные RED: диапазоны/part sizes, sticky read/
hash fault, wrong binding/degraded/discard, cancel/quota, pending/lost poll,
not_committed/ambiguous, stale epoch/row, shutdown и повторный ACK. В тестах
нет READY setters, подставленных context/generation, реальной сети/аудио.
Helper/direct transport PASS без scheduler/worker continuation не закрывает
срез. Global storageWritable/localQueueComplete остаются false до всех
HTTP/playback/delete/T120 consumers; T116/T117/T118 и installed/release OPEN.
Constitution after design: требования и gates не ослаблены. Дополнительного
agent-context update не требуется: active feature/stack/root router прежние.

### T116: обслуживание записи во время cold inspection — 2026-10-11

Узкое уточнение механики прежнего high-risk-product T116/#7444 после source
trace requestProof → readPackage → openProtectedCustodyReaders/hash → полный
AAC decode. Clarify 2026-10-02/03 остаётся действующим: новых продуктовых
решений, wire/schema, quota, endpoint или допуска записи нет. Constitution
before/after design II/III/IV/VI: видимый Stop, отсутствие plaintext fallback,
auth/deletion fences, ограничения ресурсов и отдельные release gates сохранены.
Текущий source365 ещё выполняет inspection на storage worker; его selected22
не доказывает и не принимает новую границу конкурентного исполнения.

Storage worker сохраняет единственное mutable StoreOwner и проверку текущей
строки/удаления/account grant. Полученный genuine readPackage pair передаётся
через существующий worker-only ProtectedNetworkWork slot, без второго reopen,
передачи StoreOwner или native references в UI. Existing network executor
забирает этот же pair под mutex, выполняет неизменный полный inspectProtected
и uploadProtected. Не больше одного pair/inspection одновременно;32 остаётся
пределом выбора flight, не числом одновременно открытых пакетов или inventory.
Нативные pair/proof освобождаются на worker до resultReady при успехе, отказе,
отмене и exception; остаток slot также очищается на worker. Повторная проверка
cancellation/current grant до wire и existing fresh-result commit/adoption
обязательны. Quota/key/IO/cancel не превращаются в доказанную порчу пакета.

Сначала квалифицируемый generated-data RED на существующем integrationRead:
one-shot пауза настоящего nonempty packed read именно выбранного старого
пакета, offset ≥ appendOffset; LastError сохраняется, private path не выводится.
Маркер различает packed inspection IO, но не приписывает его hash/AAC без
наблюдения caller. При удерживаемом cut новая запись должна действительно
достичь prepared, не только queued. Отдельно для активной записи наблюдается
обслуживание finalize-команды; cut затем освобождается до проверки полного
EOS/finalization/commit/adoption, чтобы тест сам не удерживал Reader cache/
Guard во время ожидания его полного drain. Cancel проверяет wire0 и настоящий
drain/release, не ложный invalidPackage. Потерянный poll/retry сохраняют flight.

Конструкция не устанавливает новый срок native ReadSample/IO либо AAC
finalization. Пятисекундный dispatcher drain не объявляется сроком всего
сохранения. До source fix нужны независимый requirements/checklist review,
обновлённый scoped analyze и подтверждение ownership существующего T116.
Global storageWritable/localQueueComplete остаются закрытыми до всех consumers;
SC-003/60min, T117/T118/T120, installed UI и аппаратная приёмка не закрыты.
