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

Техническое уточнение T117 (2026-11-04): после перехода bootstrap становится
protected, transaction/subject/directory равны null; после замены обоих slots
старый migrating peer не является постоянным источником transaction. Завершённая
история обнаруживается внутри существующего metadata owner из fixed native
intent role, BOTH indices и отдельного immutable birth envelope. Предварительный
разбор current payloads существующим PackageJson не даёт authority: barrier ref
используется только для bounded lookup fixed role/position0/version/size/hash.
Birth отдельно аутентифицируется native-derived context через
openMigrationBirthBlock. Его transaction передаётся строгому readCustodyMigration
для current slots; затем transaction уже проверенного current передаётся
readCustodyMigrationBirth для полного повторного relationship check. Ожидание
не берётся из того же JSON, который проверяется. Subject/directory заданы fixed
scope, context/generation — удерживаемыми native identity/index. Только после
BOTH progression, всех совпадающих barrier copies и retained packed roots
можно принять историю; preliminary values не разрешают admission/effect/GC.
Новая schema, persistent anchor, публичный UI API и второй parser не требуются.

Реализация остаётся после технической приёмки T116. Один storage worker удерживает
тот же root lease от legacy source snapshot через intent/fence/copy/barriers
до verified handoff обычному StoreOwner. Не использовать изменяющий
DesktopUploadQueueService::load как migration parser. Без cleanup authorization
оставлять stage switched и originals; обычная защищённая работа после полного
reconciliation не требует автоматического удаления прежних файлов.

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

**Техническое уточнение T120 — 2026-10-22, same-stream Resume:**

- Один private mailbox существующего microphone worker: seq, expected odd epoch,
  исходный absolute deadline, pending/ready/accepted/rejected. Dispatcher ждёт
  READY без captureMutex/dispatchMutex. Worker обслуживает запрос между пакетами,
  после возврата consumePacket и успешного ReleaseBuffer; не ждёт пустой FIFO.
- Для одного seq worker один раз фиксирует wall/steady receipt T0 после
  mailbox request и ДО первого QPC-before/измерения. Обе составляющие T0
  предшествуют неизменной нижней QPC границе L. При F=QPF>0 и Q=QPC-before≥0
  L=floor(Q*10^7/F)+ceil(10^7/F)+2 в единицах100ns: один консервативный
  межпоточный tick, одна единица квантования и ещё одна для строгого порядка.
  Quotient/remainder и все сложения проверяются; overflow/отказ QPC/QPF
  отклоняет запрос. Вычитание допуска из L запрещено. F/L/T0 не обновляются
  при следующем чтении в том же seq; смена F отклоняется.
- Clock/capture берутся у одного живого IAudioClient, без Reset/reopen.
  Нужен exact S_OK и достоверная same-stream пара p/q с L≤q≤QPC-after
  текущего вызова (QPC-after переведён floor). Это причинный witness после T0,
  не признание любой старой S_OK пары корректной по документации Microsoft.
  q может предшествовать before последующего вызова; фиксированная L не
  превращается в движущийся call bracket. Частота/формат прежние; p не
  уменьшается; checked B не раньше проверенного released end.
- Только недостаточная свежесть q<L оставляет исходный запрос pending, и лишь
  после остальных проверок достоверности/identity/арифметики. S_FALSE/ошибка,
  future q, before>after, смена F/потока/формата, неверный receipt, backward p,
  B<releasedEnd и обычный capture fault отклоняют запрос, не чинятся ожиданием.
  Между попытками worker продолжает обычную обработку/ReleaseBuffer paused
  пакетов без held COM buffer и busy-loop; применяется тот же исходный
  deadline1s, включая непрерывную FIFO и WAIT_TIMEOUT.
- Логическая граница B=floor(p*sampleRate/frequency)+1 исключает текущий frame.
  Quotient/remainder, умножение/сложение/+1 и packet exclusive end проверяются
  на overflow. Это семантика позиции API, не гарантия физической точности
  устройства меньше одного frame. Нет max-подгонки, clock repair или Bupper.
- Worker устанавливает B/expected even epoch ДО READY и ждёт ACK без COM buffer.
  Callback apply выполняется только dispatcher под resumeMutex→captureMutex→
  dispatchMutex; внутри admission fence проверяются точный expected epoch,
  deadline, Stop и fault. После epoch commit accepted необратим даже при более
  позднем истечении срока. Исключение не оставляет READY: notify и fatal Stop.
- Timeout/rejection отменяет только тот же seq и деактивирует candidate B;
  retry получает новый seq даже при той же odd epoch. Late COM result не может
  применить старый запрос. Все CV waits ограничены одним исходным deadline;
  Stop только закрывает admission/running и notify, не ждёт resumeMutex.
- Receipt содержит первоначальный T0, не время последнего measurement/UI ACK.
  CLOSE использует его только после принятой границы. OPEN/CLOSE используют
  existing floor-to-ms; не ceil, не скрытый max. Это квантованные metadata,
  не физическая QPC–wall калибровка. Аудио PTS этим не меняются.
- Следующие пакеты используют prefix=clamp(B-deviceFrames,0,frameCount) до
  normalizer; старые acquired-epoch/dispatcher/timeline guards сохраняются.
  Native loop обслуживает запрос также при WAIT_TIMEOUT и непрерывной очереди.
  Deadline1s — предел допуска Resume, не обещание прервать COM или mutex.

Предыдущий review call-bracket/позднего receipt — исторический, не принимает
это уточнение. Нужны текущий независимый requirements/checklist/analyze до
кода и SOURCE/runtime gate после patch. RED: stale q<L → witness≥L, но раньше
нового call-before, тот же seq/L/T0/deadline; unread packet пересекает B,
pre-T0 сигнал не возвращается, CLOSE получает T0. Дополнительные tests:
точные integer edges/overflow L, pending с paused producer/timeout,
unread→fresh/partial boundary, same-epoch retry/late result, S_FALSE/stale QPC,
native position/overflow refusal, Stop до/после epoch commit, handler exception,
accepted после deadline и быстрые повторные OPEN/CLOSE. До их прохождения
прежний unread RED не закрыт. Конституция I/II/III/VI/VII до/после уточнения:
native owner, visible control/Stop, прежние clocks/storage/egress gates сохранены.
Основание — clarify2026-10-22 и research/review того же дня; T120/T116 и
установленный/аппаратный допуск остаются открытыми. Возможный дополнительный
silence prefix не является обещанием latency или точного совпадения PCM/CLOSE.

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
исходная Start-owner строка подтверждена до первого блока, sealed package-state
подтверждён до exact-row queue update. EOS → timeline close →
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
NativeCapture/controller → Start-owner commit/adoption → V5 → sealed package →
exact-row queue update/adoption (уточнение порядка от 2026-10-16).
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
Start-owner admission и finalizer update (уточнение 2026-10-16 ниже заменяет
прежний insertion только после seal). Pure enqueue факторизуется из существующего domain helper
на charged private QueueValue, не создаётся второй ledger. Recording work,
package/writers/native result остаются worker-owned до full insertion commit
и polling adoption ACK. Actual NativeCapture finalizer всё это время pending;
future с lease на UI и bool queue_.enqueue fallback удаляются из этого пути.
Normal sealed → обновление исходной owned строки в pending → saved только при ACK/current epoch; degraded
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

## T116: исходный владелец до audio admission — 2026-10-16

Existing high-risk-product, T116/#7444; решение человека — spec Session
2026-10-16. Constitution II/III/IV/VI до исследования и после проекта:
нет нового согласия/сети для Record; auth/workspace, encrypted custody,
truthful deletion и независимые gates сохранены. Сервер/Mac не меняются.
Это construction для review, не наличие реализации, закрытие T116 или READY.

### Носитель и начало

1. Носитель — existing protected v3-read-v2 queue row. Нового поля, статуса,
   файла, сервиса или изменения logical v5/девяти package-state keys нет.
   Единственный StoreOwner готовит на charged private QueueValue исходные
   local/directory/session UUID, confined package path и captured owner pair.
   Path строится от удерживаемого trusted root, не берётся из web/caller JSON.
   UUID не переиспользуется; строка/alias/существующий каталог — conflict, не
   merge или reuse. Все server identities/ranges/attempts изначально пусты.
2. Existing `quarantined` + reserved safe_reason `capture_prepared` означает
   новый Start с confirmed owner либо доказанным signed-out (принятое текущее
   native auth observation с пустым token, оба owner поля пусты). Default пустая
   строка до auth bootstrap, failed cookie/account read и непустой token без
   текущей confirmed identity — не signed-out: сохранить
   `quarantined/capture_owner_unknown` с пустой owner pair.
   Это существующие bounded strings, не новый codec/enum. Ошибка /auth/me не
   блокирует local offline capture и не даёт claim. Старое отсутствие row/fields
   или `capture_interrupted` не создаёт ни один Start marker. В markers не
   включаются credentials, token/hash, cookies или новый auth proof.
   В существующем callback WebView2Host → AppMain → NativeCapture различаются
   успешное текущее чтение cookies без session cookie и простая invalidation.
   `reconciled=false`, expired session, workspace reselection и calendar
   authRequired очищают прежнюю authority, но не доказывают signed-out.
   Нельзя выводить signed-out из одного вызова прежнего string setter:
   положительное наблюдение и invalidation должны быть различимы до Start.
   Оно связано с текущим document generation/nonce/native Source; stale
   completion не подтверждает отсутствие аккаунта. При отсутствии такого
   наблюдения применяется unknown без сетевого условия для Record.
3. Порядок: accepted Start snapshot → full candidate → настоящий BOTH metadata
   commit/readback → value-only polling adoption → package/writer preparation
   → prepared → audio admission. До ACK ни один audio block не принимается.
   Отказ/отмена/unknown outcome не вызывают factory или ложный prepared/Saved.
   После публикации physical truth принимается и при stale epoch, но не даёт
   аудио/сеть нового аккаунта. Existing worker удерживает работу/lease до actual
   terminal/adoption; lost poll/тайм-аут не повторяют birth/публикацию.
4. Preparing/active/finalizing строка закрыта от конфликтующих send/delete/
   playback на настоящем worker до actual drain, не только скрыта в UI.
   Эфемерная native проекция не показывает её как готовую/испорченную; Stop и
   видимый indicator остаются. Окна подтверждения для начала не добавляются.
   После restart factory не достраивает отсутствующий/partial пакет по row.

### Finalizer и restart

5. Finalizer обновляет ровно исходную reservation после fresh context/generation,
   exact IDs/path/owner/marker comparison и отсутствия aliases. Это pure domain
   update на charged copy с прежним commit/adoption, не новый enqueue/UUID или
   owner на Stop. Deletion intent запрещает повышение в pending. Любые server
   identity/ranges/attempts либо несовпадающая row — conflict без перезаписи.
   Sealed normal known-owner → pending; degraded/fault/zero frames остаются
   quarantined без normal/Saved. No-login/unknown markers сохраняются до
   разрешённого claim, независимо от результата finalizer/auth/retry.
6. Restart читает BOTH queue/bootstrap под genuine StoreOwner. Только настоящий
   Start marker участвует в этой новой admission transition. Full sealed
   inspection/manifest-session/hash/codec и fresh metadata ACK предшествуют
   продвижению. Capturing/finalizing принимают только complete480 prefix по
   прежнему recovery contract, без padding/re-AEC. Partial birth, отсутствие,
   брак/IO/key/quota/ambiguous не становятся empty queue или normal.
   Carrier связывает logical UUID/session/directory/path, но не исходный Windows
   FileId/package object UUID. Их durable equivalence после ownership gap не
   заявляется: genuine current package/BOTH/session проверяются независимо.
7. Доказанный no-login (`capture_prepared`, оба owner пусты) сохраняет marker до
   явного назначения. Scheduled/auth/wake не выбирают его в HTTP. После full
   genuine sealed-normal inspection существующее native подтверждение «Отправить»
   может одним candidate/commit/adoption присвоить текущий verified account и
   перевести именно эту row в retry. Узкое исключение только для этого marker,
   без server/deletion conflict и при fresh account/generation; не для всей
   quarantine. Display через текущий auth/UI gate может показать его как
   «не назначена», без владельца текущего аккаунта. Чужие owned данные не видны.
8. `capture_owner_unknown`, исторический пакет без row/binding и legacy отсутствие
   owner fields не являются no-login. Они сохраняются без назначения/отправки;
   claim не разрешается даже после успешного нового входа. Нельзя добавлять
   ordinary sendable row или Start marker старому inventory. Existing unknown
   inventory остаётся recovery-required по прежним правилам; T117 не обходится.
   Недоступность аккаунта блокирует send, не Record; storage ACK failure до
   первого блока блокирует admission. Эти причины не смешиваются в UI.

### Short и deletion

9. Ранняя row не ослабляет no-queue-alias guard Round430. После EOS/actual drain
   genuine owner проверяет BOTH discard_pending/positive intent, exact package
   context/generation, full semantic short predicate и исходную quarantined
   Start row с exact IDs/path/owner/marker. Все прочие aliases, server identities/
   ranges/attempts или deletion intent блокируют retirement. Только эта private
   candidate row может быть убрана; обычный commit/readback/adoption обязателен
   ДО physical discard. Отдельные deletion operations/ack не стираются.
10. Далее действует прежний discardShortRecording с отсутствием ВСЕХ queue
    references и readonly reconciliation при возможном OS effect. Crash после
    retirement оставляет positive package intent, не возвращает пакет в upload.
    Restart не выводит remove authority/ACK из одной отсутствующей row/path;
    перед новым attempt нужны current BOTH intent/root/no-alias проверки.
    Ambiguous retirement удерживает full candidate/native ownership и fence.
    Short notice только после actual absence/adoption и current epoch.

### Реализация и доказательства

Existing Recording/NativeCapture.h, Upload/DesktopUploadQueueService.*,
Storage/ProtectedCustodyMetadata.* и native read-model/presenter; tests —
Tests/GrafWindowsContractTests/NativeCaptureStorageIntegrationTests.cpp.
Сначала reviewer-owned requirements checklist, scoped analyze и existing issue
owner; затем generated-data RED до production edits. Порядок: Start ACK/cancel,
update/restart, no-login/unknown/manual, short retirement. Промежуточный обход
guard запрещён. Нет нового dispatcher/pool/publisher/authority record.
Quickstart той же даты задаёт crash cuts/acceptance. Helper PASS не доказывает
native admission; synthetic не закрывает installed/hardware/release gates.

## T116: cold complete480 prefix — construction A, 2026-10-16

После Round444 настоящий restart ещё отвергает capturing/finalizing. Первая
реализуемая граница — read-only проверка сохранённого cleaned prefix, не
возобновление capture и не завершение всего recovery. Risk lane остаётся
high-risk-product; действуют Session2026-10-16, FR-012/013/014 и custody §4.

1. `LocalRecordingPackage::inspectUnfinished` принимает genuine StoreOwner,
   directory ID и cancellation token; получает `readPackage` под этим owner,
   root берёт только из owner. Caller-supplied path/Pair не принимаются:
   старый standalone Pair::read не содержит такой же retained-root binding.
   Только selected capturing/finalizing, canonical packed ref и настоящая
   BOTH package authority. `openProtectedCustodyReaders` сохраняет полную
   проверку обеих heads/всех reachable edges обеих package slots; singleton,
   bad peer, allocation/key/IO/cancel не становятся успешным prefix.
2. Используется logical length выбранного canonical stream, не EOF, accepted
   frame count, orphan bytes или checkpoint после restart. Exact complete
   bytes = floor(logicalBytes/1920)*1920; нулевой prefix отклоняется. Потоково
   проверяются finite float samples только этого complete prefix; остаток
   не аудио и не дополняется. Buffer не более64KiB, кратен sizeof(float).
   Stat/Read/Seek и cancellation проверяются; все retained streams возвращены
   в cursor0 с наблюдением общего sticky fault до выдачи результата.
3. Отдельный private-constructed `UnfinishedInspection` удерживает same pair,
   whole-group readers и cancellation; выдаёт только число complete480 frames.
   Он не является `ProtectedInspection`, sealed/degraded package, manifest
   validation, доказательством session/time/privacy/account или разрешением
   playback/upload/delete/GC. Нет path-only constructor, writable accessor,
   новых persistent fields, schema, pools и пределов. Последнее освобождение
   — на вызвавшем worker, без destructor I/O.
4. A не изменяет Native startup guard, queue, package-state, canonical,
   manifest/history и не создаёт output. Полная принадлежность по Start-row
   остаётся отдельным обязательным условием будущей интеграции. Чистое чтение
   не выдаёт mutation ticket, Saved, HTTP или готовность recovery. Примитив
   проверяется на genuine cold capturing/finalizing после освобождения всех
   исходных owners; это необходимая часть T116, не её закрытие.
5. Следующий construction B до своих production edits должен определить
   existing-only writable metadata acquisition под retained root, состояния
   unused/partial role без автодостройки birth, сохранение уже защищённой
   manifest/privacy history, sealedDegraded ACK/ambiguous reconciliation и
   WAV/AAC из exact prefix. Нынешние createPackage/createWriter — CREATE_NEW;
   ими нельзя ремонтировать старый пакет. A не даёт им новое разрешение.

Constitution check после design: visible Stop/offline capture, исходный owner,
encrypted custody, closed schema, resource limits и release gates сохранены.
Сначала независимый requirements/scoped analyze gate по этому append, затем
реальный generated-data RED до product edits и GREEN с unchanged-disk/drain.
Task owner прежний T116/#7444; ни новая задача, ни изменение пользовательского
решения, ни готовность установленного приложения не заявляются.

## T116: cold prefix → playable degraded — construction B, 2026-10-16

Продолжение A в high-risk-product lane, без новой схемы и без normal promotion.
Первый положительный путь B завершает cold capturing/finalizing, у которого
canonical существует, а media/playback/recovery ещё не начинались. Уже начатые
outputs, orphan metadata и ambiguous publication сохраняются без перезаписи;
их continuation и native startup integration остаются незакрытой частью T116.

1. Узкий private `StoreOwner::openUnfinished` получает existing-only package
   root/state/все пять role identities под непрерывным root lease. CREATE_NEW
   package/role identity не вызывается. Missing directory/id, collision,
   singleton/bad peer и cancellation отказывают до эффектов. Writable ownership
   приобретается с начала операции, не из readonly A и не через release/reopen.
2. Inventory сопоставляется с union refs BOTH package slots. Разрешены только
   live canonical и необязательный sealed manifest; selected phase — capturing
   или finalizing. Отсутствующая в BOTH role считается ещё не начатой только
   при точном inventory `id.bin` без других children. Иначе сохранённый отказ.
   Это не восстановление metadata birth: физическая роль уже существует и
   проверена, а первое content/metadata publication ещё не происходило.
3. Canonical открывается readonly с container ID из BOTH refs, без checkpoint,
   truncate, Writer::open или нового content birth. Все refs/heads/edges BOTH
   проверяются существующим group reader и общим алгоритмом A. Для manifest
   нужны BOTH metadata и selected generation, совпадающая с текущим bound ref;
   newer unbound metadata/peer-only history не переименовываются в принятую
   историю. Они требуют отдельного reconciliation, не `base=0`.
4. Приватный phase-aware вариант существующего closed RecordingJson принимает
   live normal/no-artifacts manifest, но не ослабляет sealed normal validator.
   Он проверяет session/privacy всех связанных manifest snapshots и сохраняет
   точный privacy array выбранного snapshot, включая OPEN, IDs и неизвестные
   границы. Сохранённые временные поля копируются без wall-clock recovery.
   При отсутствии bound manifest история отсутствует доказанно; пустой array
   не создаёт выдуманных пауз. Отсутствующие временные поля не синтезируются.
5. `V5LocalRecordingWriter::recover` — terminal worker-only операция, не новый
   live writer. Она использует exact complete480 frame limit A и genuine
   readonly canonical Tree. Существующие WAV/AAC loops создают первые content
   только у проверенных unused outputs, без padding/re-AEC/plaintext file.
   Canonical sealed ref/hash охватывает всю существующую logical length,
   включая неполный хвост; trusted_prefix_frames — только полные 1920-byte frames.
6. После проверки prefix/history и до эффектов освобождаются временные group
   readers, но root/package/role native leases непрерывно удерживаются.
   finalizing ACK, WAV/AAC checkpoints/decode, существующий recovery record,
   manifest через прежний ref rollover и sealedDegraded ACK выполняются по
   существующим протоколам. Неудача/ambiguous удерживает artifacts, без factory
   retry или degraded/playable claim. Последняя полная inspectProtected должна
   подтвердить degraded, session, exact duration и ненулевой decoded AAC.
7. В результате ни queue, ни original owner не меняются; нет HTTP, normal,
   deletion, install/release authority. Finalizer после recover не принимает
   append/privacy/finalize повторно. Runtime tests — только generated data.

До production edits — независимый checklist/scoped analyze GO; затем реальный
runtime RED и GREEN для cold capturing/finalizing с manifest OPEN/CLOSE, exact
canonical unchanged hash, incomplete tail, cold full inspection/playback and
same owner queue. Refusals: partial role/content birth, BOTH-union references,
unbound/singleton/bad metadata, malformed session/history, cancellation, memory/
jobs/pins, invalid canonical. Existing native/codec tests остаются обязательны.
Сбой после нового content birth сохраняется, но автоматический повтор B не
заявляется: следующий fresh read видит started output и отказывает без ремонта.
Constitution check: encryption, visible controls, private history, bounded
resources, normal-upload fence и внешние release gates сохранены.

## 2026-10-16 / T116 — native startup construction B (раунд 448)

Продолжение принятого восстановления, не новая задача/схема. После успешных
холодных проверок B и process-crash cuts подключить B к существующему
`NativeCapture::inspectRecovery`. High-risk-product; T116/#7444 остаётся открыт.

- Существующий storage worker остаётся единственным владельцем StoreOwner.
  Перед acquisition читает свежую очередь и проверяет исходную reservation:
  local/directory/session/path, owner user/workspace, quarantined/capture_prepared,
  исходное время изменения, отсутствие server identity и deletion intent.
  Переход другого аккаунта не назначает ему старую запись. Unrelated queue
  generation не отменяет запись, но изменение её строки отменяет восстановление.
- Минимально разделить существующий terminal V5 recovery на private acquisition
  и private выполнение; доступ только самому V5 и NativeCapture. Acquisition
  existing-only package выполняется storage worker, без content publication.
  Полный prefix/history/hash/WAV/AAC/decode выполняется существующим recovery
  executor. StoreOwner не передаётся другому потоку; нового executor/pool нет.
- Перед acquisition временный readonly pair освобождается на storage worker.
  Prepared writer передаётся один раз под существующим mutex; native package,
  writer и inspection освобождаются recovery executor до recoveryDone. UI
  получает только значения; повторный вызов исполнения не разрешён.
- sealedNormal продолжает прежний strict recovery/queue ACK. capturing/finalizing
  может стать только проверенным sealedDegraded. B не создаёт normal proof,
  queue mutation ticket, HTTP или автоматическую отправку. Уже sealedDegraded,
  started/orphan/ambiguous outputs остаются сохранёнными отказами без записи.
- Новая запись и её Stop/EOS не ждут encoding старого prefix. Изменение исходной
  reservation, deletion или shutdown отменяет B. Purge ждёт фактического
  retirement recovery executor; отмена не является свидетельством drain.
  На отказе частичные outputs сохраняются, автоматического factory retry нет.

Сначала независимые requirements/checklist/analyze gates; затем native runtime
RED/GREEN на generated данных: cold capturing/finalizing → verified degraded,
owner A при current B, неизменные canonical/queue, ноль HTTP, полное retirement;
started-output/deletion/changed-row refusal и Stop/drain. Прежние normal-owner,
degraded-restart, concurrent recording/playback, revalidation и V5 regressions
обязательны. Это ещё не доступ к quarantined записи через UI: разрешение
локального воспроизведения требует собственного существующего owner/deletion
пути, не ослабления playbackRowCurrent. Installed/hardware/release не приняты.
Constitution check: unchanged encryption/privacy/account/deletion/upload fences;
сервер, Mac, package-state schema и normal validator не меняются.

## 2026-10-16 / T116 — воспроизведение owned degraded после B (раунд451)

High-risk-product, T116/#7444; продолжение принятого восстановления, не новая
задача или постоянная схема. Предыдущий B scope не принимал quarantine UI.
Технологические неизвестные отсутствуют: повторно используются display inspection,
fresh queue/package validation, ProtectedInspection и protected IStream player.
Новое решение о принадлежности, upload или поддерживаемых ОС не требуется.

- Исключение только для quarantined/capture_prepared с доказанными исходными
  user/workspace, localId=directoryId=sessionId, без server identities/ranges/
  attempts, aliases и deletion intent. Чистую проверку формы строки переиспользовать
  из recovery admission; она не является authority. File/path alias checks остаются
  на storage worker вне mutex. Не разрешать всю quarantine, owner_unknown/unowned,
  неподтверждённый вход или текущую active reservation.
- Existing display inspection публикует один display-only bool playableDegraded
  вместе с timing, только после полного sealedDegraded content/AAC proof и
  повторной проверки exact package context/generation. Значение привязано к
  существующим snapshot/epoch, не передаёт proof в UI и не даёт native authority.
  Duration сама по себе не означает playable. WebView canOpen и native admission
  требуют этот свежий display result для нового исключения; normal branch прежний.
- Actual open/read и последующие resume/seek используют прежний exchange:
  original owner, current auth/document/row, fresh queue, exact reservation
  including updatedAt/status/reason и shared alias/deletion policy. Для нового
  исключения fresh package обязан быть sealedDegraded; retained full inspection,
  decoded AAC и существующая revalidation обязательны до эффекта. Ни disk/crypto
  под UI/mutex, ни нового executor/player/cache/capability не добавлять.
- Start/Stop, account/document change, deletion, cancellation и actual retirement
  сохраняют прежние fences. UI может только запросить native open; поддельный
  display bool не заменяет full proof. Quarantine/status/reason/owner/generation
  остаются прежними; Send=false, HTTP0, без normal/Saved/uploadComplete claim.
- Сначала текущий независимый checklist/analyze gate. Затем RED existing native
  cold-B fixture: current B отказывает A; actual account A получает genuine
  display, muted playback position/pause/seek, неизменные package/queue и HTTP0.
  Existing WebView host tests проверяют canOpen/command admission, no scalar,
  foreign/no-login/stale document/active/deletion/unknown/неplayable refusal.
  Fresh native tests проверяют actual auth/deletion invalidation и отказ
  capturing/started/corrupt/nonplayable; не подменять native proof тестовым scalar.
  Прежние native playback/revalidation/deletion и V5 регрессии обязательны.

Constitution check: encryption, original ownership, deletion, visible controls,
native-only file handling и normal upload gates сохранены. Persistent format,
server/Mac и T117 migration не меняются; installed/hardware/release ещё открыты.

### T116: завершение явного назначения no-login Start (аудит453)

Следующий участок реализации — существующий пункт7 Start-owner, не новая задача.
Аудит `review-2026-10-16-round453-t116-completion-audit.md` подтвердил разрыв:
finalizer сохраняет правильный marker, но ordinary retry predicate, скрытие empty
owner в WebView и постоянный `confirmUnowned=false` в AppMain не дают пользователю
выполнить предусмотренное действие. Прежний тест ordinary pending/unowned row
не является положительным доказательством этого сценария.

- Единственное новое исключение: exact quarantined/capture_prepared, оба owner
  явно пусты, local/directory/session совпадают, нет server identity/ranges/
  attempts, aliases, deletion intent или preparing/active/finalizing reservation.
  Unknown, legacy missing ownership и вся остальная quarantine не включаются.
- Общая страница получает через прежний native projection строку «Не назначена»
  и Send только после полного genuine sealed-normal inspection с актуальной
  package generation. Display-only scalar привязан к snapshot/auth epoch; это
  не native proof, не playback/delete permission и не сохранённый owner.
- Existing AppMain `confirmLocalAction` явно объясняет назначение текущему
  аккаунту и отправку в его рабочее пространство. «Отмена» — действие по умолчанию.
  После подтверждения заново проверяются тот же document/nonce, epoch/account,
  exact row и admission; повторный клик не создаёт вторую операцию.
- Existing manual-send ticket/worker и read-only inspection exchange получают
  полный свежий sealed-normal proof до candidate owner update. Полный hash/AAC
  выполняется вне UI, capture callback и storage mutex, не блокируя обслуживание
  Start/Stop/finalize. После ожиданий — fresh root/queue/exact row/package
  revalidation. Не использовать display scalar вместо этого proof.
- Один candidate/commit/readback/adoption назначает exact row и переводит её в
  retry; HTTP только после настоящего ACK. До публикации cancel/stale/refusal не
  назначают owner. Если публикация уже произошла, принять physical truth без
  повторного claim и без HTTP с устаревшими account/document полномочиями;
  unknown outcome сохраняет ticket/ownership до физического reconciliation.
  Последний native reader/proof освобождается на executor до terminal/drain.
- Сначала независимый текущий requirements/analyze gate existing CHK006/009,
  затем RED на настоящую no-login Start-row, а не ordinary enqueue. GREEN должен
  включать native claim → exact durable owner → cold restart и общий WebView/
  AppMain route; unknown/legacy/degraded/unfinished/foreign/deletion/cancel/stale
  отказы, unchanged source bytes и запрет сети до ACK. Существующие owned manual
  send, playback, deletion, concurrent recording и resource limits сохраняются.

Constitution/clarify: Session2026-10-16 уже разрешает именно это действие;
FR-012/013/014/022, schema, quotas, encryption и T116 → T117 → T118 прежние.
Технических неизвестных, требующих нового продукта/зависимости/сервиса, нет:
используются существующие owners/exchanges/dialog. Risk lane high-risk-product.
Это construction для текущего review, не source/runtime GO или public READY.

## T116 / P2 — завершение полностью записанного interrupted recovery (раунд457)

Risk lane: high-risk-product. Это продолжение construction B и Session2026-10-16,
FR-012/013/022, SC-005/006; T116/#7444 остаётся открытой. Новый формат, журнал,
поток, зависимость или продуктовая политика не нужны. P2 целиком не закрывается
этим подшагом: произвольные частичные outputs пока остаются сохранённым отказом.

Принимаемый layout ровно один: actual BOTH package-state valid, selected
finalizing с live canonical и действующим bound degraded/artifact manifest;
полностью записанные media/playback packed BOTH и recovery birth BOTH согласованы
с этим manifest/canonical/session. Это состояние настоящей ошибки непосредственно
перед final seal из раунда456, а не произвольный orphan, найденный по имени.

1. Existing private StoreOwner recovery acquisition получает отдельную internal
   completed-layout ветку: package-state writeExisting, все content/metadata роли
   readExisting, тот же continuously held root/package/role lease. Общую проверку
   identities/BOTH refs переиспользовать; unused-output ветку не ослаблять.
   Если unused acquisition отказал без эффекта, новая completed acquisition
   заново проверяет всё; старые proof/permission через разрыв не переносятся.
2. В existing packed owner — узкое private readonly discovery на уже открытом
   content handle. Независимый store/object/role берётся из genuine native role;
   container ID из prefix только candidate. Полный prefix и обе authenticated
   tree closures обязательны до формирования любых refs. Никакого write upgrade,
   random replacement ID, release/reopen между prefix/closure или partial repair.
3. В LocalRecordingPackage выделить общую value-only проверку содержимого из
   sealed inspector: closed manifest/recovery parsing, complete finite canonical
   prefix, exact lengths/SHA, WAV header и actual full AAC decode. Public sealed
   phase guards и конструктор ProtectedInspection неизменны; preflight не создаёт
   поддельную sealed Pair/ProtectedInspection. Private terminal validator берёт
   genuine package/readonly trees и actual metadata pairs, проверяет BOTH refs,
   selected bound manifest, original session/privacy/time и exact recovery tuple.
   Recovery пока только однозначный birth pair generation1; неизвестные newer
   unbound records, partial birth/invalid peer/unknown children сохраняются.
4. Из actual descriptors/hashes/metadata indices privately собрать пять refs.
   До первого эффекта полностью проверить terminal content и снова current
   package generation/BOTH refs под retained leases. Единственный эффект —
   existing package commit generation+1 → sealedDegraded. Canonical, WAV, AAC,
   manifest/recovery bytes/indices и IDs не меняются; нового encoding нет.
   После actual commit/readback освободить временные readers и вызвать настоящий
   sealed inspectProtected. Только он допускает semanticVerified/prefix result.
   Ошибка/cancel/ambiguous не разрешают повтор на failed lease, normal claim,
   cleanup или изменение queue/original owner.
5. Existing prepareRecovery/finishRecovery и Native executor передают этот
   internal mode, не caller proof/boolean. Acquisition остаётся storage-worker,
   hashes/AAC/final seal — recovery executor. Existing cancellation/drain,
   Start/Stop, quotas4jobs/32pins и independent finalizer не задерживаются.

Перед source edits: independent requirements/checklist/analyze review по current
plan/tasks/constitution. Сначала RED настоящего before-final-seal fault: release
failed owner → fresh cold recovery должен завершиться, а пока получает отказ.
GREEN: package generation+1, неизменные пять members/IDs/queue, actual cold AAC/
history, повтор sealed recovery без записи; сохранить существующие отказные
матрицы, меняя ожидание только доказанного completed layout. Это generated-data
проверка Windows VM, не public Record, установленная сборка или внешний релиз.

### T116 / P3 — единый публичный допуск новой защищённой записи (раунд458)

High-risk-product; прежние FR-002/012/013/014/022, SC-002/005/006 и T116/#7444.
Уточнение Start-owner от2026-10-16 актуально. Новый формат/authority/account
выбор не нужен; data-model и contracts сохраняются. Полный P2/T116, T117/T118,
T120 и installed/hardware/release acceptance остаются открытыми.

Причина: public Record/readiness до factory читают постоянно false поле и
legacy queue. Production consumers нового root уже подключены к protected
writer/inspection/playback/upload/deletion/privacy; старый guard не является
их proof. Не включать поле после boot и не открывать plaintext fallback.

1. Переиспользовать одну private value-проверку принятого storage state под
   existing StorageStartupWork::mutex для observation, queue completeness и
   повторного admission requestProtectedRecording. Нужны ready/adopted/current
   projection, valid context/generation, no queue/error/reconciliation/short
   discard, no command/inFlight/unadopted result. Legacy queue не участвует.
   Проверка — снимок готовности попытаться подготовить запись, не native proof.
2. Новый Start дополнительно закрыт при stop/terminal/cancellation, exit/update,
   deletion continuation. Readiness() возвращает актуальный ReadinessInputs
   snapshot; recordingReady/readinessSummary/manual/automatic callers используют
   его, не кэшированный storage boolean. После hardware probes/COM повторно
   проверить актуальное состояние в requestProtectedRecording под mutex.
3. Не включать recordingPending/любое active read/upload/display в общий queue
   predicate: свой подготовленный automatic Start проверяет readiness повторно,
   независимые readers могут работать параллельно. Duplicate Start, current
   auth epoch/session/guard и deletion/alias gates остаются на прежних границах.
4. Различать queue completeness и разрешение новой записи. Existing update
   caller сначала закрывает admission, затем дожидается native owner teardown.
   Принятое полное value после чистого stop/terminal остаётся достаточным для
   оценки update вместе с existing updateWorkDrained; для Record — недостаточно.
   Ошибка/unresolved publication не превращается в completeness после teardown.
5. Durable reservation generation/context/readback/adoption и private actual
   factory ACK по-прежнему обязательны до первого audio block. Ни observation,
   ни hardware input, ни caller boolean не обходят их. Signed-out/offline/unknown
   auth не блокируют local Start и сохраняют различную original ownership;
   stale auth result не назначает владельца и не даёт HTTP.
6. Tests-first: существующий Native integration scenario через public record,
   без beginPending/requestRecording/startPrepared/READY setter. Допустимы
   настоящие metadata-only endpoint/permission/AAC probes Windows, но сами
   capture workers после accepted starting и до pollHealth заменяются прежними
   generated producers. Ни одного настоящего audio Start/read. Проверить exact
   reservation adoption перед factory/blocks, Stop/EOS/finish, cold bytes/AAC,
   signed-out/unknown, повторный Start и update closure/drain. Сначала выполнить
   настоящий RED storageUnavailable, затем GREEN на том же сценарии.

Перед кодом — independent requirements/checklist/analyze gate текущего снимка.
Старые asserts global-false меняются только там, где accepted protected state
теперь действительно complete; failure/pending guards не ослабляются. Повторить
затронутые native tests на одной финальной source/PE версии. VM metadata probes
не заменяют device capture, AppMain installed UI или физическую x64 приёмку.

Уточнение по actual default regression458: hardware-denied private continuation
даёт rejected/blocked вместо принятого перехода blocked. Причина в общем
`WindowsCaptureSessionController::record`: accepted результата block ошибочно
достаточно для `launchPreparedRecording`, хотя controller не starting и не
awaiting preparation. Сохранить исходный blocked result; запускать continuation
только при accepted starting. Это прежний readiness contract, не разрешение
записи без оборудования и не изменение storage/native authority. Существующий
blockedRecordingDrains — actual RED; сохранить accepted/blocked assertion,
добавить отсутствие audio frames/visible capture и actual shutdown drain.
Перед production поправкой нужен независимый scoped requirements/analyze GO;
после неё проверить все callers record/prepare и исходные refusal tests.

### T116 / P2 — готовый WAV перед началом AAC (раунд461)

High-risk-product, прежние FR-012/013/022 и SC-005/006, T116/#7444.
Clarify: Session2026-10-16 остаётся актуальным; все продуктовые категории
определены, новых вопросов0. Меняется техническая конструкция продолжения,
а не владелец, формат, политика или критерий завершения. Срез не закрывает
произвольные interrupted outputs, весь P2/T116, T117/T118 или приёмку приложения.
Исторические запреты started outputs construction B/CHK001/003/020 относятся
к unused ветке; исключение ниже применяется только после нового полного proof.

Допустима ровно следующая структура: BOTH package slots valid, selected
finalizing (предыдущий capturing допустим), только live canonical и bound
manifest refs; canonical и media имеют только id.bin/content.packed-v2;
playback/recovery имеют только id.bin. Selected bound manifest и BOTH history
проходят прежние session/privacy/time/generation проверки. WAV не считается
готовым по факту FlushFileBuffers: новый cold reader заново проверяет всё.

1. Переиспользовать private openUnfinished с явным внутренним layout вместо
   completed bool: unused, completed, wavReady. Каждая попытка — fresh acquisition
   после освобождения отказавшей; никакой перенос proof/upgrade. В wavReady
   сразу получить readonly canonical/media, writable unused playback/recovery,
   writable existing manifest и package-state, сохранив root/package/role leases.
   Существующие unused/completed ветки и их правила не ослаблять. BOTH union,
   native IDs, запрет newer-unbound manifest, точный inventory обязательны;
   проверка inventory bound metadata допустима и на заранее writable lease,
   но не превращает readonly lease в writable.
2. Media container discover только из того же открытого content HANDLE;
   store/object/role — из native role. Полные authenticated BOTH HEAD closures,
   поколения и prefix обязательны. В existing Tree::verifyImpl добавить private
   strict-extent вариант для этого media preflight: под тем же Guard actual EOF
   должен равняться selected committedExtent. Не менять обычную verify/retained
   семантику, не обрезать неизвестный физический хвост. Canonical logical tail
   после полных480 frames сохраняется, включая его прежний partial content.
3. На recovery executor переиспользовать inspectUnfinished/unfinishedHistory и
   finite complete canonical prefix. Existing writeWav conversion используется
   и для проверки сохранённого WAV: exact44+frames*320 logical bytes, каждый
   header/PCM byte сравнивается с результатом той же конверсии canonical,
   без второй реализации преобразования. Перед допуском AAC обязательны EOF,
   cancellation и sticky-fault проверки обоих streams. Charged/wiped bounded
   staging прежний; несовпадение/повреждение/unknown tail → отказ без записи.
4. Только после всего preflight existing retainPrefix пропускает запись WAV,
   формирует его actual hash/ref через sealAudio(media,false), а AAC создаёт
   прежним writePlayback в доказанно unused role. Canonical/WAV/IDs неизменны;
   новый container ID ещё не созданного AAC не выдаётся за прежний durable ID.
   Manifest/recovery rollover и final sealedDegraded ACK/full AAC inspection
   прежние. Ни normal/upload/claim proof, ни изменение queue/owner не возникают.
   Failure/cancel/ambiguous после первого эффекта не разрешает retry, cleanup
   или принятие partial output; отдельные дальнейшие shapes пока отказные.
5. Native prepare/finish split, actual drain, job4/pin32/memory limits и
   public Record/Stop не меняются. Никаких новых потоков/менеджеров/зависимостей,
   публичных параметров recovery или расширения writable packed reopen.

До кода — reviewer-owned cold-prefix checklist и scoped analyze. Tests-first:
отдельный CLI existing physical child crash matrix, выбранный role=1/op=6
(после HEAD flush, до readback), child exit88. RED на старом source, затем
тот же positive GREEN, полный cold degraded/AAC, неизменные canonical/WAV/IDs/
queue, no normal/keepable и повторный readonly sealed inspection. Перед source
GREEN добавить refusal для unknown physical tail, valid но неравного PCM WAV,
неполного/повреждённого peer, начатых playback/recovery и cancellation; snapshot
всего дерева до/после refusal должен совпасть. Сохранить полную прежнюю crash
matrix, изменив ожидание только доказанных WAV-ready точек, returned-fault,
completed continuation и затронутые native regressions. Любой RED сохраняется
в evidence, сроки/guards не увеличиваются. Проверки generated VM не заменяют
device audio, installed UI, hardware, accessibility и release gates.

Уточнение после actual WAV29 RED: tests-first positive role1/op6 остаётся
отдельным обязательным сценарием. Дополнительная process-crash точка role1/op5
находится после успешной полной записи HEAD, но до flush/readback; ОС может
сохранить целиком читаемые bytes без прежнего checkpoint ACK. Если тот же
fresh BOTH/EOF/full PCM proof пройден, этот exact shape также восстанавливается.
Историю вызова flush нельзя выводить из готовых bytes; ни событие WriteFile,
ни номер cut не являются продуктовым допуском. Контролируемый test wrapper
должен подтвердить полный native HEAD transfer, а обе WAV точки — пройти все
неизменные positive assertions. Полная матрица требует24 executed cuts и4
продолжения (два WAV, два terminal), узкий op6 CLI — одно. Никакого «успех или
отказ оба допустимы», расширения прочих started shapes, flush/repair WAV,
retry того же failed owner или утверждения power-loss durability. Все прежние
refusal, cancellation, native-error, ресурсы и сроки сохраняются. Это уточнение
измеримого acceptance существующего shape predicate, не новый persistence flag.

### T116 / P2 — повторное построение начатого AAC (раунд462)

High-risk-product; FR-012/013/014/022, SC-005/006, T116/#7444. Clarify:
Session2026-10-16 актуальна, продуктовых вопросов0. Восстановить пригодный
исходник, не объявлять partial AAC готовым. Original owner и пользовательские
правила назначения/отправки/удаления прежние. Это следующий этап P2, не закрытие
T116/T117/T118, иных interrupted shapes или installed/hardware/release gates.

Admission: BOTH package slots valid, selected finalizing; refs обоих slots —
только прежние live canonical и bound manifest. Selected manifest обязателен,
его selected generation совпадает с binding; обе retained history валидны.
Canonical/media/playback inventory — ровно id.bin/content.packed-v2; recovery —
только id.bin; manifest — точный BOTH-referenced inventory. Неполный birth,
invalid HEAD/identity, unbound/newer manifest, started recovery и уже sealed
package сохраняются как отказ без записи. Это отдельное исключение к прежним
started-output запретам, не ослабление unused/completed/wavReady branches.

1. Private layout playbackStarted в существующем openUnfinished. Fresh
   acquisition сразу получает readonly canonical/media, writable existing
   playback/manifest/package-state и writable unused recovery. Непрерывные
   root/package/role leases, без readonly upgrade/переноса отказавшего proof/
   обхода через public path-open. Prepared writeExisting и writable packed
   inventory разрешить только для playback; access/writable/nonfailed state,
   trusted root/package/context обязаны совпадать. Не расширять другие роли.
2. Media/playback container ID обнаруживать из того же content HANDLE; новых
   IDs нет. Full BOTH closures всех packed объектов/union retained refs до
   первого эффекта. WAV — прежний strict actual EOF и bytewise canonical→WAV
   proof с EOF/cancel/sticky guards. Playback — обычный packed proof: orphan
   physical tail не authority, сохраняется целиком; corrupt reachable DATA или
   один valid HEAD из двух не допускают повторного кодирования.
3. После preflight existing Writer на fresh writable playback proof, явный
   setSize(0), прежний writePlayback из exact complete canonical prefix. Это
   logical root следующего поколения только для nonempty→0; empty→0 остаётся
   проверенным committed no-op того же proof/generation без HEAD write.
   Это не physical truncate/birth/generation reset. Prefix и bytes
   [appendOffset, oldActualEOF) неизменны; менять можно
   только HEAD cells и append после actual EOF. Утраченный MF state не
   продолжается, нет padding/AEC. Даже готовый, но unsealed AAC проходит тот
   же re-encode; decode не доказывает прежний Finalize ACK. Sealed data immutable.
4. Прежний Guard reserve/physicalBytes/95% от5GB cap учитывает старые records
   и orphan tail перед каждым reset/append. Нехватка места — отказ, не cleanup.
   Job4/pin32/owned64MiB/dirty staging/worker/drain и сроки не увеличиваются.
   После failure/cancel/ambiguous нет same-owner retry. Следующий fresh launch
   заново проверяет BOTH: valid empty-reset/partial/append-tail допускаются по
   тем же правилам, torn HEAD/birth — отказ. Старый physical extent сохраняется.
5. Прежние checkpoint/hash/full AAC decode → bound manifest/recovery →
   sealedDegraded ACK/full inspection. Canonical/WAV/все IDs/queue/owner прежние;
   normalPackage/keepablePackage/HTTP=false. Нет нового encoder/backend/schema/
   public API. Constitution check: encryption/visible capture/Stop/deletion/
   lifecycle/testable gates сохранены; server/macOS/v5 wire не меняются.

До test-only edits — reviewer-owned CHK035–041 и scoped analyze C0/H0. Actual
tests-first RED: child process crash после полного playback HEAD flush на
прежнем source, exit88/actual wait; не compile failure/timeout/skip. Затем тот
же positive GREEN. Покрыть valid empty birth, orphan DATA, полный HEAD до
flush, готовый AAC до metadata и повторный crash reset/append/HEAD/metadata/
final seal. Для actual trace заранее задать точные outcomes, не «успех либо
отказ». Старый24-cut regression сохранить, менять лишь доказанные new shapes.
Отдельно нужен actual MF partial AAC с committed logical size>256KiB, не только
односекундный flush или подставленные bytes. Если runtime budget недостаточен,
нужна отдельная конструкция испытания, не скрытое увеличение guards/timeout.

Preflight negatives: wrong PCM/unknown WAV tail, invalid/singleton playback
HEAD, corrupt reachable DATA, extra file, started recovery, wrong IDs/history,
pre-cancel → whole-tree hashes unchanged. После эффекта native/short IO/flush/
readback/DPAPI/hash/quota/cancel → sticky failure, no normal/retry/cleanup,
canonical/WAV/старый playback extent/queue сохранены. Success требует full fresh
cold degraded/AAC/privacy/optional times proof и unchanged IDs/owner; readonly
reinspect не пишет. Требования, source и runtime GO раздельны. Production пока
отказывает для начатого AAC; неполный birth/torn metadata остаются открытым P2.

Конечная таблица повторного запуска (462-U1, technical amendment468-U2). Обозначения: R — успешный новый
encode через playbackStarted с полным degraded proof; C — existing completed
continuation без encode; U — recovery birth затем completed seal по468-U2 без
encode; D — recover отказывает и всё дерево после fresh
attempt побайтово прежнее; S — recover не меняет sealed package и отказывает,
а отдельный прежний readonly sealed inspection успешен. Для R/C исходные
canonical/WAV/IDs/queue и старый physical playback extent неизменны. Таблица
предполагает остальные admission predicates, отсутствие cancel/pressure и
одинаковые данные fixture; повреждённая identity/retained ref/closure всегда D.
Номер cut или история flush не заменяют фактически прочитанный shape.

| Состояние после повторного прерывания | Единственный исход |
|---|---|
| До reset либо empty→0 no-op; старая unfinished history и valid BOTH playback | R; для empty нет reset-HEAD cut, первый эффект позже в encode |
| Nonempty→0 reset с полностью читаемой новой HEAD и прежней peer HEAD | R; поколение reset ровно+1 |
| Новый DATA/NODE append без смены HEAD; старые BOTH closures исправны | R; orphan bytes сохраняются и новые records идут после actual EOF |
| Полная новая HEAD WriteFile до flush либо после flush, обе closures valid | R; не доказательство прежнего ACK или power-loss durability |
| Torn/invalid playback HEAD либо incomplete birth | D; не достраивать и не откатывать |
| Manifest retire ещё не начат либо полностью опубликован; оба package slots связаны с прежней текущей unfinished history, exact inventory без orphan | R |
| Retire package-state torn/invalid либо его referenced metadata unreadable | D |
| Новые manifest DATA/temp/orphan уже созданы, но index ещё старый | D; exact inventory не допускает orphan metadata |
| Manifest index уже выбрал новую generation, package binding ещё старый | D; не выбирать прежний index ради продолжения |
| Terminal manifest bound, recovery ещё только id.bin | U по уточнению468-U2 ниже; до его реализации — сохранённый D. Не unfinishedHistory/encode и не partial recovery |
| Recovery DATA/temp/index singleton/partial/invalid | D; не достраивать birth |
| Recovery g1 BOTH полностью готовы, terminal manifest bound, package ещё finalizing | C; все прежние five-member/history/content checks обязательны |
| Final package-state publication оставила valid BOTH с selected finalizing и готовыми terminal members | C |
| Final package-state publication оставила valid BOTH с selected sealedDegraded | S; никакого reset/перекодирования |
| Final package-state torn/invalid либо повреждён retained referenced member | D |

Tests-first short playback-HEAD fixture и последующие repeated-crash fixtures
обязаны заранее выбрать конкретную строку/shape и assert именно её outcome.
Реальный trace уточняет ordinal/role/operation, но не разрешает после отказа
переписать ожидание на «D или R/C». Новый shape требует отдельного проекта,
а не более разрешающего history parser. Неподдержанные D остаются видимыми
открытыми сценариями P2, не основанием закрыть восстановление целиком.

### Уточнение 464 — ограниченная пакетная сборка и сверка WAV

AAC44 подтвердил child WAIT_TIMEOUT60s при настоящем MF60s fixture; полное
baseline recovery заняло около91s. Это не доказательство вклада отдельного
метода. Первый минимальный кандидат меняет только writeWav: до32 полных
10ms кадров за одно обращение (canonical<=61440bytes, PCM<=10240bytes),
оба буфера через прежний charged/wiped CustodyBytes. Последняя порция имеет
фактическое число кадров, incomplete canonical tail не включается.
Прежнее усреднение каждого triple/toPcm16 и порядок отсчётов сохраняются.
Input можно переиспользовать для WAV comparison только после преобразования
всей порции. Отмена проверяется на каждой10ms границе преобразования и до
эффекта; каждый фактический Read/writeAt проходит прежние native Guard,
sticky/short IO/полные длины. RIFF header/strict WAV EOF/canonical zero-read/
sealAudio и readonly comparison остаются. Общий cache256KiB, quotas и таймеры
не меняются; writePlayback/MF10ms samples этим шагом не меняются.

Формат, модель данных, authority/history/R/C/D/S и task ownership прежние,
нового продуктового решения нет. Проверка гипотезы — прежний serial180
ProtectedRecoveryPlaybackPartial с child60s и тем же6000-frame fixture;
прежний отказ остаётся RED evidence. Если кандидат не укладывается, нельзя
объявить partial proof или расширить пределы. Затем short/WAV negatives,
полная24-cut матрица и все затронутые suites на одном final source.

### Уточнение 465 — canonical read-ahead без смены MF samples

AAC45 дошёл до partial524288<complete732186 и recovery60000ms, но полный
тест закончился CTest180 timeout до завершающего fresh audit. Следующий
минимальный кандидат расширяет464 только чтением canonical в writePlayback:
один прежний charged/wiped буфер до61440bytes, refill до32 полных кадров,
последний refill по min(32,remaining). Индекс n выбирает только заполненный
кадр; incomplete canonical tail и неиспользованный buffer tail не читаются.

На каждый n остаётся отдельный PCM960/MF sample480 отсчётов, прежние
toPcm16/time=n*100000/duration100000/WriteSample и call wrapper. Каждый
реальный refill проходит прежние Read/Guard/exact got/observedFailure/cancel;
attempted/read/got относятся только к этому refill. На каждой MF frame
сохраняются проверки cancellation/output failure даже без refill. Ранее
обнаруженный output failure нельзя назвать canonical corruption. Read-ahead
может раньше обнаружить ошибку будущего canonical кадра; sticky остаётся
первый фактически обнаруженный отказ, а не прежнее чередование независимых
ещё не наблюдённых ошибок. Закрытие/drain/worker release/MFShutdown и полные
checkpoint/decode/seal остаются прежними. Нового authority/cache/формата нет.

Пределы job4/pin32/64MiB/cache256KiB/child60/CTest180 сохраняются. Сначала
тот же long partial test, затем short/WAV/returned/completion/full24 и
затронутые native/files/tree на final source, с отдельной проверкой отмены
и происхождения ошибок. Никакого изменения исходов R/C/D/S или выпуска.
Новые product answers/tasks/entities/contracts не требуются: это T116 и
прежние FR-012/013/014/022. До production — scoped requirements/source gates.

### T116 / P2 — terminal manifest с не начатой recovery role (468-U2)

High-risk-product; прежние FR-012/013/014/022, SC-005/006, T116/#7444 и
Session2026-10-16. Это техническое продолжение457/462, не изменение владельца,
формата, политики или полноты общей цели. U означает единственный успешный
исход нового layout: создать недостающую recovery g1 BOTH, затем прежний
completed final seal без encode. Строка462-U1 изменена только для этого shape;
исторические D/cut13 и старые отчёты сохраняются как evidence старого source.

1. Fresh private existing-only acquisition: selected package finalizing, BOTH
   slots/все retained refs valid; canonical live unsealed и все bound manifest
   references проверены целиком. Selected metadata generation
   обязана совпадать с текущим bound object/generation/length/SHA; newer-unbound,
   metadata orphan/temp/лишние children и повреждённый peer — D. Media/playback
   имеют valid BOTH packed closures и exact inventory/physical extent: нет нового
   неизвестного хвоста после committed extent; прежние невыбранные records внутри
   него не удаляются и не объявляются повреждением. Package peer может сохранять
   старую manifest reference, manifest peer — unfinished history; оба проверяются,
   не требуется две terminal-копии или дополнительная публикация. Recovery
   не имеет refs в union BOTH package slots и содержит ровно исходный id.bin:
   нет DATA/index/temp/начатого birth. Root/package/role leases непрерывны;
   package-state и recovery — writeExisting, canonical/media/playback/manifest —
   readExisting. Никакого readonly upgrade, нового ID или переноса proof между
   отказавшими acquisition; прочие unused/completed/WAV/playback guards прежние.
2. До первого эффекта: полные descriptors/SHA/finite canonical complete480,
   strict bytewise WAV equality существующей canonical-конверсии с exact EOF,
   full AAC decode, selected terminal degraded/artifacts manifest, session и
   BOTH manifest histories. Старый unfinished peer разрешён только по прежнему
   closed parser, privacy JSON/optional wall times/timezone строго совпадают;
   degraded peer побайтово равен selected. Не ослаблять unfinishedHistory и не
   выбирать старую history. Длительность terminal manifest = floor(canonical
   logical bytes/1920)*10; AAC непустой. Canonical tail сохраняется без padding.
3. Переиспользовать existing writeWav comparison (готовый snapshot, без writer)
   и completeUnfinished/value-only validateProtectedContent. Recovery JSON —
   только предложение из проверенных terminal reason, complete frames и полного
   canonical length/SHA в прежнем пятиключевом формате. Предполагаемые поля ref
   допустимы лишь внутри value proposal, не current_/retained pair или proof.
   Полная semantic проверка этого значения предшествует записи. Новых encoder,
   pool, persistent flags, schema или публичного effect API не требуется.
4. После preflight освободить временные readers, сохранив те же native owners.
   Existing commitMetadata recovery выполняет настоящий g1 birth BOTH с прежними
   crypto/flush/readback guards. Снова прочитать и сравнить BOTH actual recovery
   bytes/indices и получить действительный sealed ref; только затем existing
   completed five-ref commit generation+1 → sealedDegraded и fresh sealed
   inspectProtected. Никакой RAM layout/boolean не заменяет durable ACK. До full
   final inspection semanticVerified/trustedPrefixRetained не выдаются.
5. Pre-effect отказ/cancel — всё дерево побайтово прежнее. После возможного
   эффекта любой short/native/crypto/readback/flush/quota/cancel — sticky failure,
   без same-owner retry/cleanup/normal/upload/claim. Canonical/WAV/AAC/manifest
   bytes/indices/IDs и queue/original owner не меняются даже при успехе. Recovery
   partial/orphan/singleton по-прежнему D; complete g1 BOTH после нового crash —
   прежний C, selected sealed — S. Worker/executor, cancellation/drain,
   Start/Stop, job4/pin32/memory и child60/CTest180 limits не изменяются. Граница
   возможного эффекта — до вызова commitMetadata, не publicationStarted: DATA
   пишется раньше index. Ошибка/исключение после успешного recovery commit также
   блокирует package owner; recoveryPending=false само по себе недостаточно.
   После начавшейся публикации нельзя обрывать обязательный BOTH/readback ACK.

Tests-first: добавить filtered actual repeated cut13 (полностью bound terminal,
recovery exact unused), physical callback/child exit88; ожидание U задано до
запуска. Старый source должен отказать именно в новом positive assert, не build
failure/timeout. Затем GREEN с fresh cold full degraded/AAC/privacy proof,
unchanged four members/IDs/queue/owner и readonly sealed reinspect без записи.
Новая матрица interruption имеет шесть exact cuts: до/после recovery index0,
до/после recovery index1, до/после final package publication. Исходы заранее
D/D/D/C/C/S (при остальных predicates); D сохраняет дерево после fresh attempt,
C не кодирует/не переписывает members, S не пишет. В старой repeated19 только
cut13 меняется D→U: R9/D6/U1/C2/S1; прочие18 исходов неизменны.
В прежней24-cut матрице тот же physical shape — cut18 {package-state,op3};
он также D→U, прочие23 исхода сохраняются. Это проверка shape, не исключение
по номеру: обе fixture обязаны подтвердить exact unused recovery и bound history.

Негативные preflight: valid wrong WAV PCM/unknown extent, corrupt AAC/canonical,
wrong history/privacy/session/optional times/binding, newer-unbound/orphan,
started recovery/ref in peer и pre-cancel. Returned-fault/short IO/flush/readback/
crypto/quota/cancel после birth требуют sticky/no retry и preserved old members.
Повторить затронутые completed/WAV/playback/49 faults/old24/repeated19/long и
native regressions на точном final source/PE с no-skip/post216/owned0 evidence.
AAC47/AAC56 прежние TIMEOUT остаются нерешёнными, новый PASS не устанавливает
их причину. Independent requirements/checklist/analyze C0/H0 нужны до test edits,
actual test-diff/source gates — до соответствующих запусков/production edits.

Constitution check до и после проекта: I/II capture/control не меняются;
III encryption/egress/secrets сохранены; IV identity/deletion/actual retirement
сохранены; VI tests-first/reviewer/exact-source обязательны. Продуктовых вопросов0;
T116 и installed/hardware/accessibility/release gates остаются открытыми.

### Уточнение 469 — выбор normal/terminal до writable audio acquisition

Review468 выявил H1: structural playbackStarted может перехватить terminal U,
а перестановка U вперёд — прежний normal R. До ЛЮБОГО openUnfinished выполнить
private bounded metadata classification на storage worker: existing readPackage
с retained readonly package-state и только manifest member, без audio owners,
packed scan, encode или записи. BOTH package slots должны оставаться unfinished;
каждый manifest ref сверяется с actual BOTH metadata по object/generation/length/
SHA, selected bound ref — именно с selected metadata generation. Отсутствие
manifest допустимо как normal только если его нет в обоих package slots.

Shared private closed-parser helper возвращает только ReasonCode, не proof:
none только после явного unfinished parse всех bound histories; non-none только
для selected degraded/artifacts с прежней строгой BOTH history/privacy/times
проверкой. Неразобранный terminal, invalid binding/history, IO/crypto/quota/cancel
не становятся normal fallback. Для normal сохраняется прежний unfinishedHistory:
не вводить равенство privacy/times разных поколений и не требовать manifest у
package peer, где его раньше не было. Непривязанный metadata peer не добавляет
нового normal-ограничения; terminal по-прежнему проверяет оба metadata slots.

Все временные metadata leases уничтожаются ДО fresh content acquisition.
Normal идёт по прежней цепочке unused/completed/wavReady/playbackStarted;
terminal — только completed либо terminalRecoveryUnused. Структурный отказ U
никогда не разрешает R, partial/orphan/singleton recovery остаётся D. У terminal
никогда не приобретается writable canonical/media/playback/manifest. Полная
history/content проверка повторяется на recovery executor после fresh admission;
классификация worker не заменяет её и StoreOwner не передаётся executor.

Обязательные регрессии: прежний normal empty/partial/full/orphan AAC tail остаётся
на прежнем R; terminal bad peer/binding — D без writable audio acquisition.
Positive AAC60 meaningful RED сохраняется; исходы/лимиты468-U2 не меняются.
Это technical clarification существующей T116, не новый продуктовый выбор,
формат, задача или ослабление конституции. До production — независимый scoped
requirements/analyze/construction gate; actual diff — отдельный source gate.

### T104: сохранение видимого напоминания при временном сбое — 2026-10-21

High-risk-product, прежняя T104/#7281; новая задача/формат/зависимость не нужны.
Применяется уточнение contracts/f277-notifications-parity.md от 2026-10-21.
Сохранять точный WinHTTP nativeError сразу после отказавшего вызова в существующих
response types, передавать через notification-context и calendar reads. Не
выводить transient из status0 или исключения. Классифицировать до очистки UI;
auth/context/interaction invalidation остаются окончательными. Не менять
upload/delete retry, сервер, общий кабинет или account authority.

Существующая модель удаляет все события кроме точной видимой identity при
transient; menu availability выключается. Presenter не меняет её claim/deadlines
и не повторяет звук. Terminal удаляет удержанный снимок. Failed Record refresh
снимает pending без принятия старого completion. Успешный fresh snapshot вновь
разрешает обычный выбор/меню и инвалидирует изменённое событие.

Сначала meaningful RED обычной видимой карточки на прежнем коде; затем проверка
классификации HTTP/native errors и фактического переноса ошибки, visible-only
retention, no-stale-next, original wall/steady expiry, close/context/quiet/
recording/preemption и failed action retry. Независимый requirements/checklist/
analyze gate до кода; source gate и portable/native tests после. T104 не закрывается
без установленного пакета и доступности; T120 WASAPI boundary остаётся отдельно.

Уточнение T104 handoff: ordinary terminal очищает сокращённый снимок сразу;
успешный JoinAndRecord держит одну цель только в синхронном участке
recordCapture(predicate), после launched/finish/completeAction. Один локальный
признак отличает сокращённый снимок от свежего; scope cleanup действует на
возврат/исключение, не стирает новую epoch или новый успешный snapshot. Это
сохраняет существующие три проверки перед Record, не создаёт новый grant/cache.

### T103: безопасная история — исследовательский допуск, 2026-10-22

High-risk-product, существующие T103/#7280 и T088/#7231. Clarify — Session
2026-10-22 в spec.md; продуктовых вопросов нет. Полный production-план истории
пока НЕ завершён: NEEDS CLARIFICATION (техническое исследование) — как отличить
выбранный native GET-entry от конкурирующего script traversal на POST-entry
того же URL до допуска перехода. URL/kind сами по себе не являются entry ID.
Mac использует controllerTargetURL в policy и WKNavigation на завершении;
это не доказательство отсутствия такой гонки в Mac или Windows.

До выбора production-механизма разрешён только ограниченный тест в существующих
WebView2AuthNativeTests.cpp, WebView2AuthLoopback.py и их PowerShell runner:
две последовательности одного same-URL permit-race эксперимента. Подготовить
GET-S → POST-S → GET-C → новый GET-S → GET-C. Сохранить реальные разные ID;
native target — именно новый GET-S, script target — старый POST-S через go(-3).
Это соответствует Mac-случаю восстановления URL новым GET, не выдаёт старому
POST права безопасного перехода и не требует fallback на старые browser IDs.

Только fixture моделирует одноразовый permit по URL/BackOrForward и отменяет
следующие traversal events до product handler. Из одного UI callback отправить
native Page.navigateToHistoryEntry и script go(-3) в обоих порядках без ожидания
первой команды. Скрипт обязан подтвердить исполнение из C; обе команды и оба
фактических BackOrForward события должны быть наблюдаемы. Starting/Completed,
ContentLoading, текущий entry ID и GET/POST DOM marker — наблюдения, не способ
вручную завершить product latch или выдать nonce/authority.

Oracle: разрешённый/текущий POST-entry опровергает гипотезу даже без нового POST.
Два достигнутых перехода, разрешённый native safe GET и отменённый unsafe
script дают PASS только достигнутого порядка. Недостигнутый конкурент, ошибка
команды/наблюдения, оба отменены либо неизвестная идентичность — INCONCLUSIVE,
не production GO. Ненулевой итог не скрывать из runner.
Текущая конструкция не умеет независимо установить target отменённого события:
поэтому это negative-only опыт, без пути PASS. Финальный safe GET и два события
остаются INCONCLUSIVE; найденный unsafe ID немедленно даёт sticky REFUTED,
не ожидая успешного DOM-read. Это ограничение опыта, не ослабление oracle.
До эксперимента —
независимый requirements/checklist/analyze gate; actual diff — source review.
Старые 23 сценария не заменять новыми; source/PE hashes, GUID profile, synthetic
loopback, deadline20s/close10s/case35s и owned-child cleanup сохраняются.

Constitution check: I/II audio/control не меняются; III только синтетические
данные и закрытый loopback, без аккаунта/микрофона; IV прежняя session authority
не ослабляется; VI независимое review/tests-first; VII полезная Mac-навигация
остаётся целью. Новый history owner, fallback, новые persistent fields и API
не разрешены этим исследовательским допуском. Phase1/data model/contracts для
production оформляются после результата. T103/T088/T097 и release gates открыты.

### T103: выбранный план безопасной истории, 2026-10-22 (после stage9)

Этот раздел заменяет ограничение «только исследование» предыдущего раздела
для следующего среза. Lane `high-risk-product`, T103/#7280 и T088/#7231,
FR-002/005/006, SC-002; общий кабинет, сервер, Mac и persisted formats неизменны.
Clarify — дополнение Session 2026-10-22. Новых продуктовых вопросов нет.

**Phase0 / решение.** All-same-URL veto недостаточен: unsafe запись может сменить
URL через replaceState/pushState после snapshot. Native BF допустим только если
ВСЕ реальные записи полного свежего снимка individually confirmed GET текущей
сессии. Unknown/unsafe ANYWHERE включает карантин BF, независимо URL. Это
закрывает переименование старого POST без предположения о доставке событий.
Обычная all-GET история использует actual browser IDs и порядок; CDP-команда
не считается заранее связанной с NavigationId. Terminal selected-ID check до
nonce остаётся дополнительным барьером, не защитой от восстановления POST.

**Phase1 / модель и чистая политика.** В существующих WebViewRoutePolicy.* —
конкретный SafeHistory, без нового framework/зависимости/стека адресов. Полный
ограниченный snapshot `{id,url}`/currentIndex и индивидуальные GET proofs.
Revision отзывает async результаты. Повтор ID, отрицательный ID, неверный index,
более 128 entries, пустой URL, URL более 8192 байт или запрещённый символ — отказ
снимка с недоступным старым выбором. Snapshot не является proof. Proof сохраняется
только для неизменного ID+точного URL той же сессии; исчезнувшая/изменённая запись
его теряет. Current entry подтверждается actual final response GET, успешным
cabinet latch и свежим снимком того же документа. POST/unknown не наследуют GET.
Actual document replacement отзывает proof замещаемого entry, отмена до замены
его сохраняет. Ошибка metadata/snapshot не объявляется GET.

Back/Forward выбирают ближайший отличный URL в actual browser order. Из встречи/
review/share/meeting deletion report Back идёт только в meeting-history route.
Все entries должны быть подтверждены, включая текущую и forwardList. Новый
same-document ID остаётся unknown; смена URL не переносит proof. Session logout/
expiry/account/workspace/recreate очищают snapshot/proofs и singleForward.
Loading/pending/reset запрещают повторное действие. Phase1 сначала реализует
только policy; это не исправление установленного приложения и не закрытие T103.

**Phase2 / native integration.** Pending intent ставится ДО async snapshot,
при отсутствии незавершённой навигации. Пока snapshot не принят, все BF и новые
document navigation отменяются до beginDocumentNavigation. После полного all-GET
снимка разрешён один BF к URL выбранного ID, конкуренты отменяются. До nonce/
bridge authority terminal native snapshot подтверждает selected current ID,
session/generation; response-completion latch не обходится. HistoryChanged/
SourceChanged/revision/session отзывают устаревшие результаты, но не являются
доказательством актуальности браузера. Ошибка/несовпадение не даёт authority.

**Восстановление после карантина.** Из просмотра встречи без допустимой цели
Back делает свежий GET `/desktop/meetings`. Только из individually confirmed GET
сохраняется одна fresh-GET цель Forward той же сессии (не старый entry ID).
После обычного принятого GET списка/home, при карантине или новой сессии,
`Page.resetNavigationHistory` очищает только историю. Весь участок accepted GET →
reset ACK → проверочный snapshot запрещает ВСЕ BF и новые document navigation.
Проверка требует ровно одну ту же current entry, тот же URL/document generation/
session; ACK сам по себе не успех. Same-document mutation/new ID/иной документ
прерывает reset. Нельзя объявить неизвестную запись GET лишь потому, что reset
её оставил. Ошибка сохраняет карантин; raw GoBack/GoForward, перебор POST и
очистка cookies запрещены. SingleForward доступен после успешного reset,
отзывается при постороннем переходе/ошибке/session boundary. Reset не выполнять
на каждом обычном GET. Далее all-GET история снова даёт actual BF.

**Tests-first / допуск.** Requirements/checklists + analyze C0/H0 до code.
RED→GREEN в существующем WebViewRoutePolicyTests: useful BF/nearest distinct/
meeting filter, unknown ANY URL, fresh GET не реабилитирует POST ID, mutation,
stale revision/session clear/bad snapshot/reset не переносит proof. Независимый
source review policy перед native integration. Затем actual native tests reset
API установленного runtime, response binding, actual BF, fallback/singleForward,
cancel preserves-current/session boundary/POST rename race/no dead ends.
Default23 не удалять; ID-only/race диагностика не заменяет продуктовую приёмку.
Сохраняются source/PE hashes, GUID profiles, bounded runner/owned cleanup.
MSIX/UI/keyboard/accessibility — после native PASS, hardware/E2E — отдельно.

Constitution I/II audio/control неизменны; III synthetic loopback без микрофона
и аккаунта; IV authority не ослаблена; VI tests-first/review; VII полезная
навигация с явно описанным Windows security deviation. Новых задач нет: это
последовательный срез существующих T103/T088; T097 и release gates открыты.

#### T103 Phase2: миграция прежних native oracles, 2026-10-22

Сохраняются все23 default case IDs и исполнение каждого: сохраняем покрытие,
не небезопасный прежний traversal. Никаких skips/xfail либо production
exceptions ради старого теста. Stage11 mechanism PASS относится к прежнему
frozen host; direct-CDP опыт не обходит будущую admission policy.

| Existing case | Oracle после подключения host |
|---|---|
| history-get | Actual host all-GET Back/Forward с selected ID/DOM/native method/latch/bridge; always-deny/reset не проходят. |
| history-post | A→POST-B→C→fresh GET-list→fresh GET-C; list/reset/singleForward подтверждаются, old IDs не требуются, POST не повторяется. |
| history-host-same-url | Тот же fallback; fresh list ID отличается от прежних GET/POST того же URL, Forward создаёт новый GET-C, не старый ID. |
| history-entry и history-entry-same-url | Negative production unsolicited CDP traversal при POST anywhere: actual command отправлен, product отменяет ДО begin/replacement; текущие ID/DOM/generation/bridge сохранены. Fixture не вызывает Cancel. Positive selected-entry coverage остаётся в history-get/history-host-get. |
| cancel-history-host | Подготовка all-GET A→B→C вместо POST; fixture отменяет допустимый native BF к B до product. C/authority сохраняются, следующий документ работает. Одна отмена fresh-list fallback не заменяет этот BF lifecycle control. |
| cancel-history-script | Fixture-owned ранняя отмена script BF через POST сохраняется как lifecycle control, не доказательство production fence. |
| history-same-document | replaceState/hash сохраняют документ/bridge, затем работает новый документ; это не сохранение GET proof изменённого URL/new ID. |
| 14 auth/transport/TLS cases и cancel-before-start | Прежний смысл без изменения; результаты требуется проверить на новом host, а не выводить из прежнего PASS. |

Initial opt-in history-host-get/history-host-quarantine добавляют actual host
selected-ID/GET/bridge и fresh-list/reset/singleForward proofs без fixture
navigation fence; не заменяют default23 или остальные семь integration групп.
Counts каждого мигрированного case выводятся из его конкретной последовательности,
не расширяются ради GREEN. Новые native tests проходят SOURCE review до запуска;
сначала meaningful old-host RED. Это уточнение проверки ALL-entries политики,
не изменение продукта/контрактов/SC/scope T103/T088. До host edit требуется
повторный bounded requirements/analyze gate этой матрицы; migration H1 снимает
независимый reviewer, implementation не меняет checklist markers.

#### T103 Phase2: детерминированные native continuation проверки

Для обязательных integration групп2/3/5/7 разрешён один закрытый native-only
`friend struct WebView2HistoryNativeFixture` по существующему образцу payment
fixture. Определение живёт только в существующем native test, декларация — в
SDK-only части WebView2Host.h; публичного API, persistent state, framework либо
нового runtime switch не добавлять. Декоратор сохраняет original callable и
задерживает доставку настоящего production adapter результата/ACK; отдаёт
неизменённый результат ровно один раз на том же UI dispatcher. Выбор точки —
реальный этап selecting/accepting/resetting, не ordinal CDP-вызова.

Fixture не выставляет stage/revision/session/GET proofs/nonce, не вызывает
fake finish, не фабрикует snapshot/ACK/headers и не заменяет production Cancel.
Наблюдающий activation wrapper немедленно вызывает original, не предотвращает
ошибочную активацию вместо продукта. Удержанные closures освобождаются до
owned teardown, старый host не уничтожается до delivery его callback.

Первый ограниченный test slice добавляет opt-in pending-read-fence и
terminal-held в прежние три fixture-файла; default23 и initial2 сохраняются.
Pending: actual host Back → удержан настоящий selecting ответ → реальные
BF/GET/form POST и повторный native action. Для каждого browser конкурента
нужны Starting/OperationCanceled с его ID, отсутствие ContentLoading, прежние
current ID/generation/auth и retained bridge; после delivery original snapshot
selected BF работает. Отсутствие доставленного конкурента не PASS.
Terminal: actual selected BF → response/completion получены → настоящий
accepting snapshot удержан. До delivery latch не потреблён, нет нового nonce/
auth/cookie/bootstrap/activation; реальный bridge button не действует. После
неизменённого delivery ordinary finalizer сам принимает выбранный GET и
настоящий bridge работает. Fixture не выдаёт authority.

Следующие reset-ACK/readback и stale-account варианты используют тот же
декоратор и прежние семь групп; наличие первого среза их не закрывает. Wrong-ID
и перестановка delivery metadata — отдельные fault scenarios с настоящими
browser results, не поддельными успешными ответами. Deadline20s/close10s/
case35s, synthetic loopback/GUID/source/PE/owned0 safeguards неизменны.
Перед test edits — bounded independent requirements/analyze C0/H0; перед
запуском — отдельный SOURCE review точных test/host bytes. Продуктовые требования,
bridge и задачи не меняются: T103/T088/T097 и release gates остаются открыты.

#### T103 Phase2: fresh-list redirect к входу — прямой native контроль

Следующий ограниченный tests-first срез проверяет совместимость уже принятого
fresh-list выхода с обычным own-navigation redirect к входу. Это техническая
проверка действующих FR-002/005/006 и T103/#7280, не новое продуктовое поведение,
не изменение auth contracts и не разрешение внешнего next. Lane остаётся
high-risk-product; существующие clarify/checklist/analyze gates сохраняются.
Перед test edits требуется независимый bounded requirements/analyze review.

В прежних native CPP/loopback PY/PS добавить один opt-in scenario: настоящий
initial GET meeting detail C → принятие ordinary latch/GET/bridge → actual host
Back без прежнего list target → native fresh GET `/desktop/meetings` → настоящий
synthetic HTTP302 с внутренним Location `/login?next=%2Fdesktop%2Fmeetings`.
Fixture только инициирует пользовательское Back и наблюдает реальные события;
не выставляет permit/proof/session/nonce/stage, не отменяет переход и не
подменяет response/continuation/finish. Redirect должен принадлежать тому же
реальному NavigationId, а не считаться новым пользовательским разрешением.

Положительный oracle: принятый C с реальным bridge до действия; фактические
GET-list и redirect Starting/GET-login/response/completion; current login с
видимой редактируемой формой и безопасным next, authRequired без native bridge/
новой authority. Требуются доставленные redirect и final document, отсутствие
нового POST и повторной отправки формы. Прежняя шестипольная сводка строго
`2 1 0 1 0 0`: cabinet GET2/login GET1/email GET0/safe login next1/
unexpected path0/non-GET0. Четвёртое поле — подтверждение безопасного next,
а не ещё один запрос; его нельзя обнулять особой веткой нового case.
Один actual detail, один fresh list и один login, не расширять ради GREEN.
Попытка редактировать synthetic input
должна сохранять значение; новая отправка формы не нужна (default login-post400
продолжает отдельно проверять её интерактивность).

На исходном host выполнить meaningful RED до исправления; ошибка запуска/
компиляции не доказывает дефект redirect. Затем минимальная shared-root правка,
если отказ подтверждён, и unchanged GREEN. Перед каждым запуском exact SOURCE
review; прежние default23, initial2 и controlled2, их oracles/counts/deadlines
не меняются. Synthetic loopback/GUID,20s/10s/35s и source/PE/runtime/owned cleanup
сохраняются. Это не принятие всех metadata-order/session/reset групп, T103,
T088/T097 либо установленного приложения и не повод заранее разрешать redirect
без проверки actual native ownership/route/method/latch.

### T103: stale reset readback после настоящего изменения current entry

Следующий узкий срез уже запланированной группы7, без новых задач/продуктовых
требований: один opt-in `history-reset-stale-readback`. Использовать существующие
native fixture/loopback/runner и реальные AGET → POST-B → CGET с ordinary latch
и harmless bridge на принятых документах. После C вооружить наблюдатель, вызвать
actual host Back/fresh listGET. В существующем friend удержать только настоящий
результат nativeReadHistory на стадии resetting, после настоящего reset ACK.
Проверить actual singleton committed ID/URL списка; не подделывать snapshot/ACK,
не менять state/proof/nonce и не подменять reset adapter.

В настоящем list DOM выполнить history.pushState с `#synthetic-reset`, затем
независимым browser snapshot подтвердить новый current ID/URL при том же
документе/DOM и без нового document Starting. Продолжение старого singleton
доставить неизменённым ровно один раз на UI dispatcher. Ожидается fail-closed
unavailable/history-mutation, не ready; quarantine остаётся, singleForward
отозван. До изменения и после stale delivery нет новой activation, auth/cookie
reconciliation, bootstrap/native_ready или native dispatch. Наблюдающий wrapper
activation обязан вызвать original: он не скрывает ошибочную активацию.
Stale delivery не меняет реальный mutated current entry и не начинает traversal.

Проверка не заканчивается тупиком: actual host.navigate(list) выполняет новый
GET с новым document/entry ID; production сам выполняет нужные reset/readback,
ordinary latch/ready/реальный bridge снова работают. Старый singleForward к C
не воскресает. Strict counts `4 0 0 0 0 1`: AGET/CGET/fresh-list/recovery-list,
один прежний POST-B, без повторной отправки. Counts не заменяют actual browser
entry/DOM/native callback evidence. Это не доказательство BF fence через
history.go(-1) на singleton, где вообще может не возникнуть Starting.

До авторства нужен bounded независимый requirements/checklist/analyze C0/H0;
до запуска — SOURCE review exact test3. Если текущий host безопасно отказывает
и восстанавливается, PASS закрывает только этот отрицательный класс; не нужен
искусственный RED. Реальный дефект требует отдельного meaningful RED, минимальной
корневой правки/SOURCE и unchanged GREEN. Сохранить предыдущие28 case/counts,
default23,20s/10s/35s, GUID/profile/source/PE/runtime/owned0 и cleanup guards.
Host, серверный продукт, OS permissions и устройства этим срезом не меняются.
Другие reset интервалы/ошибки/timeout/session и полная T103/T088/T097/релизная
приёмка остаются открытыми. Реализация не отмечает reviewer-owned checklist.

### T103: смена контекста при незавершённом reset — завершение и штатный повтор

Следующий tests-first срез существующей группы5 — opt-in
`history-reset-account-boundary`. Переиспользовать AGET/POST-B/CGET и настоящий
reset-held readback после ACK. Непустой синтетический token получить из реального
browser cookie через штатный AuthSession callback; не печатать его. Публичный
bindUserTimeAccount меняет workspace A→B при неизменных user/token и явно
выбранной authGeneration. Fixture не меняет product state/proofs/nonce/ACK.

До любого восстановления отменённая операция обязана завершиться в пределах
существующего history budget 5с в unavailable: без authority, дополнительного
HTTP и бесконечного initializing. Старые proofs/singleForward отозваны;
session/operation/revision изменены. Затем однократная UI-доставка исходного
readback не меняет B, состояние, document/entry, callbacks либо authority.
Само по себе not-ready/idle без завершения loading не является PASS.

Восстановление — публичный host.reload(), тот же путь, что штатная кнопка,
не искусственный navigate(list). Требуются настоящий GET-list, новый nonzero
NavigationId/document generation, обычные response/completion/reset/readback,
ready и четвёртый реальный bridge callback. Числовой entry ID при повторном URL
может сохраниться: обязательны actual singleton/current URL и GET proof,
а не неподтверждённое правило нового ID. Auth callback сохраняет выбранный B.
Strict server counts4 0 0 0 0 1; cookie/auth3→4, signed-out/invalidation0,
наблюдаемая reset activation0→1, bridge3→4. До reload новых запросов нет.

Сначала независимый requirements/checklist/analyze gate и SOURCE review test3,
затем meaningful native RED на незавершённом loading до recovery. После
подтверждения — минимальная shared-root правка, SOURCE review и unchanged GREEN,
затем прежние29 без ослабления oracles/counts/20s/10s/35s/GUID/source/PE guards.
Первый bind уже ready initial200 не должен запускать eager GET: один GET
сохраняется. Это host integration, не реальный AppMain account-me/workspace UI
и не доказательство доступности кнопки мышью/клавиатурой. T103/T088/T097,
семь групп целиком, установочные, аппаратные и релизные gates остаются открытыми.

### T103: workspace boundary до ответа и доставленный поздний redirect

Следующий узкий tests-first срез существующей группы5 — один opt-in
`history-account-boundary-redirect-held`. Переиспользовать реальные AGET/
POST-B/CGET, cookie/account A/authGeneration1 и bridge3. Затем публичный
host.navigate(list), не Back: на actual HTTP GET подтвердить отсутствие
X-GRAF-History-Intent, чтобы прежний marker guard не скрывал отсутствие owner.
Synthetic loopback удерживает только этот запрос до HTTP-заголовков, без
блокировки counts lock. Из собственного GUID-case публикует metadata-only
response-held; fixture требует и marker, и настоящий Starting/navID, и
read-only navigating/nav!=0/no response/no completion до public bind A→B.
Меняется только workspace, token берётся из настоящего AuthSession callback.

До release/recovery требуются unavailable≤5с от bind, B, отозванная authority,
без новой navigation/HTTP/auth/bridge. Затем response-release освобождает
настоящий HTTP302 `/login?next=%2Fdesktop%2Fmeetings`. Обязательны реально
доставленный IsRedirected Starting того же navID и terminal OperationCanceled
без fixture Cancel; GET-login/новая authority/возврат в loading недопустимы.
Marker отправки302 не заменяет browser event. Отмена ещё до redirect не
принимает именно этот поздний-event класс. Не требовать неизменного DOM/entry
после позднего ответа; требовать неизменный B и безопасный terminal host.

Только после terminal старого navID — штатный host.reload(): actual GET-list,
новые nav/generation, ordinary latch/reset/singleton/ready/bridge4 с B. Новый
числовой entryID не обязателен. Strict counts4 0 0 0 0 1; auth/cookie3→4,
signed-out/invalidation0, наблюдаемая новая activation0→1. Наблюдатель activation
всегда вызывает original; fixture не присваивает state/proof/nonce и не фабрикует
HTTP/events/ACK/finish. Ни один original history result не задерживается здесь.

Server hold ограничен монотонно8с, немедленно прерывается stop.request;
fixture освобождает hold при любом завершении до owned teardown. Узко
ожидаемый client disconnect отмечается отдельно, остальные ошибки не скрывать;
drain/join предшествует чтению counts. Прежние readiness1.5s/native20s/close10s/
case35s/outer600s и profile/source/PE/runtime/owned guards не увеличивать.
Перед авторством — bounded requirements/checklist/analyze, затем SOURCE review,
meaningful native RED до production edits и unchanged GREEN/прежние30, включая
initial2001GET и положительный own fresh302. Возможный root candidate — завершить
прерванный initializing history при bind и не принимать redirect без актуального
owner; конкретный diff требует отдельного SOURCE review. Другие late200/session/
перестановки событий, T103/T088/T097, AppMain UI и релиз остаются открытыми.

#### Уточнение измерения HTTP после stage26

Это поправка метода испытания T103/group5, не разрешение дополнительного
сетевого обращения. WebResourceRequested уведомляет о попытке ДО отправки;
fixture подписан раньше production. Нельзя вызывать finish/close на одном
таком уведомлении после release: это выключает alive и не даёт production
обработчику исполниться. До release по-прежнему нет даже новой попытки.

Следующий diagnostic tests-first срез сохраняет тот же opt-in и все30 прежних
проверок. Ранний fixture observer выводит только same_origin, категорию
известного synthetic пути (list/detail/login/other), GET/POST/other и числовой
ResourceContext, без URL/query/cookie/header values. После release он может
наблюдать ровно одну same-origin GET-login Document попытку, но не выставляет
Cancel/Response/host state и не завершает host до рабочего подписчика.
Любой иной путь/метод/origin/context или ранняя попытка остаётся ошибкой.
Если реальное наблюдение не соответствует этой категории, не менять условие
на произвольную разрешающую ветку: сначала квалифицировать метаданные.

Synthetic server отмечает настоящий дополнительный HTTP metadata-only marker
в собственном GUID-case: категория пути/метода, без чувствительных значений;
counts lock не удерживается во время file I/O или response hold. Native fixture
проверяет marker до принятия terminal/recovery/успеха; все final counts читаются
после drain/join и остаются строго4 0 0 0 0 1. Уведомление попытки не успех и не
доказательство сетевой передачи; лишний actual server request — явный FAIL.
Обязательны прежние same-ID redirect Starting, terminal OperationCanceled14,
B/no authority/no loading resurrection, public reload/GET/new nav+generation/
ordinary ready/bridge4. Нет второго observer framework, fabricated response,
core.Stop или задержки original history callback; все deadlines прежние.

На host9308 сначала нужен diagnostic RED с доказательством категории попытки
и actual server marker, без вмешательства fixture в рабочий подписчик. Только
потом рассматривать минимальное дополнение существующего Document request
veto для unavailable/nav0, если наблюдаемый origin/context это подтверждает.
Не блокировать первый разрешённый GET/reload, ready downloads или ресурсы.
Перед test edit — bounded requirements/checklist/analyze; перед run — SOURCE;
после root fix — SOURCE и unchanged GREEN + старые30. Новый task не создаётся.

### T116: два источника в ограниченном кэше чтения — 2026-11-03

Это техническое уточнение существующих464/465, не новая функция или формат.
Risk lane остаётся high-risk-product, владелец T116/#7444. Диагностика
`validation-2026-11-03-partial-performance.md` локализовала затраты в finish;
отдельный actual flat-v1 тест подтвердил32 DATA-read на8 пар прогретых readers.
Это подтверждение вытеснения, не доказательство его доли в packed recovery.
Гипотеза принимается только после независимых requirements/checklist/analyze
и actual SOURCE gates; перед ними production reader не меняется.

Уточняется только прежний implementation cache256KiB: процесс удерживает
не более двух активных ReaderState и ровно одного блока≤256KiB на каждый,
итого plaintext≤512KiB, в прежнем contract decoded-cache≤2MiB. Все actual
allocations/capacity, включая Debug proxies, остаются в owned64MiB; временные
decrypt/cipher/NODE buffers по-прежнему проходят native job2MiB admission.
Нельзя подменять размером payload фактическую capacity или сумму временных
allocations. Pins32/jobs4/dirty4, buffers32frames/61440, fixture6000,
child60/CTest180 не меняются. Source/format/authority/history/queue неизменны.

Две фиксированные записи и прежний mutex; новых locks, pools, конфигурации
или второго reader API нет. Ключ — exact ReaderState и block, привязанные
к прежнему owner/root/generation. Другой block того же state всегда заменяет
его собственную запись. Новый state занимает свободное место, иначе LRU
из двух; успешные hit/fill обновляют один LRU-бит. Сам mutex и проверка
квот/отмены/общего первого отказа сохраняются. Каждый packed hit проходит
прежние native pre/post checks, каждый miss — прежний полный read/decrypt.
Это не обещание свежего DATA-read на hit: новая политика меняет порядок
повторного физического чтения между разными states; уже обнаруженный отказ
никогда не скрывается кэшем. Cold ownership gap требует прежних full proofs.

Payload записи — optional CustodyBytes: empty не создаёт vector/Debug proxy;
clear под mutex делает reset и стирает/освобождает actual capacity через
существующий wiping allocator, не создавая нового vector внутри noexcept.
После успешного actual read/decrypt использовать emplace с перемещением
существующего CustodyBytes и лишь после полного успеха опубликовать ключ.
Это уже не std::vector alias: CustodyVector/CustodyBytes в
ProtectedCustodyCodec.h имеют throwing default/move constructors через
count-constructor(size_t{0}) и прежний equal-allocator move-assignment.
Повторную обёртку или отдельный способ создания vector вводить не нужно.
Default/move самого std::vector в MSVC Debug могут быть noexcept и выделять
proxy; существующий helper уже сохраняет перехватываемый bad_alloc. Нужны
прежние compile-time traits throwing CustodyBytes move/nothrow assignment
и actual Debug pressure test нового места использования, без bypass/лимитов.
На отказе entry не опубликован; independent
entry сохраняется, а затронутый state/package получает прежний sticky fault.
Деструктор state очищает все его записи до освобождения адреса; cache не
удерживает shared_ptr на state. Factory preinit сохраняется без proxy allocation.

Tests-first: превратить диагностические8 пар в причинный RED additionalReads0
на прежнем reader при сохранении всех actual byte/seek assertions. Затем
LRU третьего state, свободное место после close, ровно один block на state,
short-tail/ZERO/EOF и clone cursors. Отдельно filled-cache close при полном
memory pressure без IO/allocation/terminate, возврат actual charge и wiping;
stronger coldCacheClose expected idle==before вместо остаточного пустого proxy.
Проверить отказ существующего CustodyBytes move без опубликованного key
и очистку при давлении памяти. Actual packed hit обязан обнаруживать
native pre/post fault без DATA-read; shared-package fault виден прогретой
соседней роли. Cache-hit prefix + последующий miss/fault сохраняют wipe/got0/
cursor/first-error; прежние cancellation/drain/owner/clone regressions остаются.

GREEN принимается только с новым exact-source Debug build и исходным полным
ProtectedRecoveryPlaybackPartial до180s, включая cold/privacy/readonly/idle
и terminal marker. Если времени всё ещё не хватает, не расширять deadline
или fixture и не объявлять причину устранённой. Далее полный затронутый набор
на одном source; остальные45 matrix cases, T116/T117/T118 и installed/hardware/
accessibility/release gates этим ограниченным исправлением не закрываются.


### T116: метки native finalize после matrix failure — 2026-11-03

Remaining57 дал44 PASS/один internal180deadline Failed/12 unrun:
NativeProtectedSchedulerResume остановился до network-resume проверок,
после14000 кадров на94151ms. Следующий срез только диагностический,
high-risk-product/T116/#7444, без нового продукта/формата/tasks.
Переиспользовать существующие begin/endFinalizePhase в test executable;
atomic test-only arm до Stop существующего resumedUpload и reset только
после resultReady. Worker сохраняет phase entry/return-or-unwind/wall time,
GetLastError и прежние вызовы/значения. Без профиля native-call counters
не интерпретируются как измеренные нули. Существующая самопроверка adapter
покрывает log on/off × profile on/off × returned/unwind. Сначала scoped
requirements/checklist/analyze и SOURCE review кандидата+runner, затем
Debug Native build, existing profile CLI/selfcheck и тот же CTest case.
14000frames/inner180/CTest240/семантические проверки и data/IO fences
не изменять; failure квалифицируется как failure, без объявления причины
по одной активной фазе. Это не T116 closeout или migration acceptance.


### T116: устранение повторного admission внутри Write — кандидат

High-risk-product/T116/#7444; исходный RED — native scheduler resume
с14000frames/общим180s, включая finalize. Ищется минимальное сокращение
повторного native metadata IO без ослабления guards. Предложение не применено:
State::resize имеет ровно двух callers — setSizeImpl и writeAtImpl. Перенести
его entry ready() в setSizeImpl; writeAtImpl уже проверяет entry перед
проверкой указателя/лимита и checked integer arithmetic, следующими chunks
и итоговым ACK. Первый loop chunk использует тот же entry вместо повторного
ready; последующие обязаны заново проверить. Между entry/first chunk/grow
resize только арифметика и sizeImpl (чтение RAM), нет внешнего вызова/IO.
Все проверки у фактических flush/load/packed transitions и post-write ACK
сохранены; readAt/Read/cache/pre-post guarded IO, sticky first fault и budgets
не меняются. Private resize не получает bool bypass/нового API/второго writer.

До production edit независимые scoped requirements/checklist/analyze и
SOURCE review конкретного candidate+runner. В существующем packedWriterAdmission
проверить blockWrites/revokeWrites/first I/O fault также для grow/shrink/invalid
SetSize — до аргументов и любых effects, сохранять точный первый отказ.
Затем actual Debug profile counters/wall, тот же14000-frame RED, writer/multi-
chunk cancellation/revocation/zero/sparse/ACK/MF-close regressions на одном
source. Выигрыш и семантика принимаются лишь по результату, не по размеру diff.
Нельзя повышать deadlines/уменьшать fixture или засчитывать прежние PE как новые.
MF throttling/cadence/async очереди не менять; это иной риск bounds/памяти.


Уточнение test-first того же кандидата: existing FindFirstStreamW counter
калибрует один native admission через no-op SetSize. На прогретом dirty-блоке
overwrite и grow обязаны сохранять exact bytes/length без ReadFile/WriteFile
и укладываться в entry+ACK (два прохода). До assert проверяются pending bytes,
настоящий checkpoint и чтение immutable snapshot. Старый writer ожидаемо
даёт3/4 прохода: это отдельный квалифицируемый RED, не полный baseline PASS.
После production candidate фактический last query второго прохода получает
existing throwingMetadata fault: нет byte ACK/IO, writer sticky, checkpoint
не committed. Existing actual-MF multi-block cancellation/write failure и
first-shared-fault tests дополняют, не заменяют эту post границу. Никакой новой
интерфейсной точки, счётчика или product fail switch не нужно.


### T116: отдельный бюджет составного large-parts correctness test

NativeProtectedLargeUploadParts проверяет полную525s generated запись,
finalize, cold verification и две multipart раскладки; его общий CTest cap
не является SC-003 или сроком Stop/финализации продукта. Квалифицированный
actual Debug diagnostic646632ms описан в validation-2026-11-03-partial-performance.md.
Для этого одного correctness case выбрать конечный900s cap (около39% выше
наблюдённого полного пути); сохранить RUN_SERIAL, fixture52500, все byte/SHA/
range/owner/idle assertions и все остальные deadlines, включая Resume180/240
и Partial180/child60. Сначала независимый scoped requirements/analyze/SOURCE
review, затем новый actual CTest с проверкой generated TIMEOUT900. Прежний
CTest240 FAIL и CLI diagnostic сохраняются отдельно, не переименовываются
в PASS. Это поправка проверки, не production performance fix/SC-003 acceptance.


### T116: UTF-8 пути прежней очереди под Unicode TEMP

Cohesive62-r2 и отдельный existing --logical-queue дают один actual RED:
valid owner-presence v3 row проходит protected decoder, но legacy load
отказывает на3249. Код переводит decoded UTF8 в filesystem::path через narrow
constructor, legacy serializer использует .string, quarantine suffix также
строится через narrow string. Минимальное исправление: в общей функции только
для filesystem::path использовать u8path; при сериализации этого типа u8string;
quarantine дописывать к native path без narrow roundtrip. CustodyString bytes,
строгий JSON/owner parser, confinement, ошибки/сохранность и wire schemas не
меняются. Переиспользовать existing logical-queue/legacy roundtrip и malformed
quarantine checks под тем же Unicode TEMP; исправить narrow path construction
в этих тестах, не переносить проверки в ASCII каталог и не повышать deadlines.
После SOURCE gate — targeted GREEN, затем текущий общий набор. Это исправление
наблюдаемой регрессии T116, не начало T117 и не разрешение трогать real quarantine.

### Ресурсы браузерных проверок календаря в CI — 2026-11-04

На SHA39572 governance-fast41742725170 выявил два отказа уже принятого
rendered calendar→Windows shim test: Chromium PASS, WebKit binary отсутствует.
Сам shim намеренно проверяет оба движка; локальная проверка обоих уже прошла.
Техническое исправление существующей F200/T119 validation, high-risk-product:
в трёх текущих Playwright install commands governance-fast/release-full
установить chromium и webkit той же закреплённой версии. Тесты, состав движков,
таймауты, package lock и scopes jobs не менять. Новых требований/задач/зависимостей
нет. До изменения — независимый bounded requirements/SOURCE разбор; после —
YAML и точная проверка трёх команд, затем GitHub code proof нового SHA.
Это исправляет подготовку CI, не принимает Windows/WebKit/installed parity
и не разрешает переименовать исходный отсутствующий-browser FAIL в PASS.

### T088: verified lifecycle по Mac publisher — 2026-11-04

Узкая конкретизация существующих T088/FR-006/013/022, high-risk-product lane.
Пользовательский результат и образец Mac уже приняты; здесь выбран технический
binding для §8.1 bridge contract. Новых task IDs, серверных/ledger схем
и серверного API нет; T088 остаётся открытой до проверенной реализации.

Порядок реализации после текущих квалификаций:

1. В `Web/RecordingDeletionBridge.cpp` расширить нынешний `kDocumentScript`
   (`RecordingDeletionBridge::documentScript`): перед имеющейся веткой
   `deleteSelection` принять точный Mac `visibleRecordings` и передать событие
   `graf:visible-recordings` без фильтрации/усечения IDs. В `Web/WebView2Host.cpp`
   существующий `kDesktopBridgeScript` получает отдельный listener этого события
   и передаёт payload через приватный `send('visible_recordings', ...)`.
   Сохранить publisher `cabinet.js`, его coalescing/visibility reset, нынешние
   `GRAFRecordingDeletionBridgeVersion = 1` и установку `grafLocalRecording`;
   не оборачивать/переустанавливать handler и не менять ветку удаления.
   В `Web/WebViewBridge.cpp`
   `isAllowedWebCommand` добавить ровно эту строку: тип команды сейчас строковый,
   нового enum не требуется. Существующие команды семантически не подходят.
   В `parseEnvelope`/приёме сообщения проверить точные исходные поля новой
   команды до WinRT Stringify, переиспользуя `DesktopApiClient::jsonObjectFields`
   по образцу calendar, затем обычную проверку конверта. Не расширять payload
   `local_recording`. В host переиспользовать проверки текущего защищённого
   документа (`localPlaybackDocumentCurrent`), аккаунта/cookie и последней
   проекции; проверить маршрут списка/встречи и detail UUID по нынешней policy.
   Пустой список отзывает видимость, навигация отзывает её нативно. Пробросить
   только проверенные local IDs и нативный контекст в владельца очереди.
2. В `Recording/NativeCapture.h`, нынешних `pollUploads`/`pollAccount` и
   startup/wake/network recovery подключить один объединяемый lifecycle flight
   для подтверждённых origin/user/workspace/authGeneration. Запрос строится из
   неизменяемого снимка принятой защищённой очереди; local IDs отображаются в
   принадлежащие аккаунту directory/origin IDs нативно. Использовать существующие
   `DesktopHttpTransport::recordingLifecycle` и
   `DesktopApiClient::decodeLifecycleEntries` с существующим verified scope и
   account headers. Сеть выполнять вне mutex значения/очереди; сохранить бюджеты
   памяти/IO, отмену и ограничения admission/Stop существующего владельца.
   Как в Mac `runRecordingLifecycleSync`: уникальные отсортированные origins,
   приоритет видимых/открытых и имеющих deletion operation, максимум 100 целей
   на запрос; каждый origin не более раза за цикл (`checked`). После приоритетов
   — одна фоновая страница от курсора, с переходом к началу. Повторные открытия
   не сбрасывают `checked`/курсор; курсор двигается после успешного принятия
   страницы. Использовать нынешние периодические/recovery триггеры, без нового
   таймера. Отсутствие WebView/пустая видимость не останавливает фон. Смена
   области аккаунта отменяет старый flight и сбрасывает его приоритет/курсор;
   навигация в том же аккаунте отзывает только приоритет документа, не отдельные
   нативные полномочия фоновой проверки.
3. В `Upload/DesktopUploadQueueService.*` дополнить существующее преобразование
   `ProtectedUploadQueueValue` обработкой проверенного lifecycle ответа без
   локальной операции: нынешний `applyDeletionAnswer` требует существующую
   операцию, поэтому сам по себе этого случая не покрывает. Проверить точное
   покрытие batch, отсутствие дублей/чужих целей, известное состояние и соответствие
   receipt типу/ID цели и проверенной области аккаунта. `receipt.requestId`
   обязан быть валидным UUID; первая внешняя квитанция не требует отсутствующего
   локального request ID, а повтор сверяется с сохранённым receiptRequestId.
   Без прежнего intent создать сразу принятое состояние в существующей модели операций;
   не вызывать `planDeletionSelection`, не создавать queued/sending намерение.
   Совпадающий повтор идемпотентен, конфликт квитанций отклоняется. `allowed` и
   `unavailable` следуют Mac server-truth semantics, не снимают принятую квитанцию
   и не разрешают purge; неизвестный/частичный ответ не принимается частично.
   Нынешний storage worker `NativeCapture` создаёт частный candidate, проверяет
   snapshot/queue generation/область, делает существующий полный защищённый
   commit и независимый readback, затем adoption. Только после adoption меняются
   опубликованная проекция и блокировки содержимого. При конфликте поколений —
   повторная сверка, не перезапись более новой очереди; при ambiguous commit —
   существующая reconciliation с сохранением артефактов. Смена аккаунта не
   публикует старый результат и не отменяет уже сохранённую истину под видом
   пустой очереди. Доработка не требует менять занятый `ProtectedCustodyMetadata.cpp`.

Минимальное связанное покрытие до реализации: добавить rendered
publisher→Windows shim случай по существующему образцу `CalendarJoinShimTests.cjs`,
с реальным `cabinet.js` и обоими нативными scripts; расширить существующие
`RecordingDeletionBridgeTests`, `WebViewBridgeEnvelopeTests` и
`WebView2HostLifecycleTests`. Проверить положительный путь из текущей проекции
и отказ для старых nonce,
message_id, документа/маршрута/detail UUID, cookie/аккаунта/authGeneration,
неверных типов/версии, extra/duplicate fields, ID вне проекции, дублей и >100 IDs.
Отдельно — `ids:[]`, навигационный отзыв и неизменность прежнего local_recording.
В существующем `NativeCaptureStorageIntegrationTests` расширить настоящий
startup/pollUploads путь на синтетической непустой защищённой очереди: >200 origins,
повторяемый видимый приоритет, фоновый прогресс/обход без WebView, scoped ответ,
первая внешняя квитанция при пустом списке deletion operations → commit/adoption
→ освобождение всех владельцев → первый новый обычный владелец читает ровно одну
принятую операцию; повтор не дублирует её. Это ожидаемый RED нынешнего кода,
а не fixture, вставляющая delete intent напрямую. Отказы полного batch, чужой
области/цели/receipt, stale auth generation, конфликта queue generation и
not-committed/ambiguous commit не публикуют успех до adoption. Использовать
сгенерированные метаданные и подставной transport: реальные устройства/сеть 0;
считать вызовы DELETE/purge ACK (оба 0), проверять отсутствие локальной очистки,
неизменность исходных пакетов и возврат leases/jobs/pins/памяти к исходному уровню.
Это покрытие доказывает получение/сохранение истины, не право удаления, очистку
оригиналов/карантина или завершение T088/FR-022.
