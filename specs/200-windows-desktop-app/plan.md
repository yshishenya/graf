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
