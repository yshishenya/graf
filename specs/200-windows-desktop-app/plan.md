# Implementation Plan: Windows desktop-приложение GRAF

**Branch**: `200-windows-desktop-app` | **Date**: 2026-08-23 | **Spec**:
[spec.md](spec.md)

**Input**: Feature specification from
`/specs/200-windows-desktop-app/spec.md`

## Summary

Порядок завершения F200 и подготовки внешнего выпуска:
[цель и критерии приёмки, 2026-11-09](release-execution-plan.md).
Технические решения и действующие ворота отдельных срезов остаются ниже.

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

Для T063/T097 статическая проверка MSIX и проверка установленного экземпляра
раздельны. При проверке установленного экземпляра существующий
`validate-package-smoke.ps1` принимает заранее зафиксированный SHA-256 MSIX,
связывает проверенную подпись и исполняемый файл внутри этого пакета с
регистрацией для текущего пользователя (имя, издатель, версия, архитектура
и состояние) и сверяет SHA-256 установленного EXE. Отдельный режим наблюдает
уже запущенный экземпляр с тем же путём в текущем сеансе. Системный диалог
ошибки запуска не считается его окном, даже если отвечает Windows.
Окно и ответ процесса не означают приёмку интерфейса. Скрипт не устанавливает, не запускает и
не закрывает приложение, не меняет доверие к сертификатам. Контроли: точный
установленный пакет, другой подписанный пакет, неверный хеш, прежние проверки
архива. Требования чистой установки и внешней подписи остаются прежними.

Для T097 доступные имена «Вид», «Решение проблем», «Документация» и
вариантов темы в точности совпадают с видимыми подписями. Стрелки
раскрытия и отметка выбранной темы видны, но не входят в имена.
Состояния открытого и закрытого пункта передаёт `details/summary`,
состояние ровно одного выбранного варианта — радиокнопка. Исправление принадлежит
общему кабинету; размеры, сторона открытия, управление фокусом, выбор
и сохранение темы остаются прежними. Сначала подтвердить регрессию и
исправление в WebView2 и WebKit на одинаковой странице, затем проверить
дикторы обеих ОС в установленных приложениях по Quickstart §5.

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
   source/build cache допустим. Опись и проверка хешей включают скрытые
   библиотеки и заголовки, доступные инструментам сборки. Скрипт проверяет
   exit code каждого native tool.
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
  Для T110 использовать один нативный маршрут F6 для WinUI и WebView2. На
  стенде проверена очередь только своего UI-потока (`WH_GETMESSAGE`, удалённые
  сообщения); принимать начальный F6 без модификаторов только у активного
  корня главного окна. Не добавлять глобальный перехват или команду веб-моста.
  Сохранять существующий порядок выбора: предложение записи, доступный Stop,
  другая карточка. Откладывать перевод вне обработчика очереди и перед ним
  проверять то же окно, отсутствие деактивации после нажатия, поколение
  карточки либо тот же сеанс и доступный Stop, а также состояние выхода.
  Отозванная команда не переназначается. При недоступном маршруте остаются
  нативный Stop, обычная навигация и команда трея. Снимать обработчик при
  выходе; не менять hide/restore/Quit T108 и обработчики записи.
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
- **T124 — решение владельца 2026-11-12.** Для первого публичного x64-выпуска
  выбран прямой MSIX с сайта GRAF через системный App Installer. Официальное
  легальное имя издателя — «ИП Шишеня Ян Александрович». Это имя не является
  ещё не полученным CA-verified Subject сертификата; тестовый `CN=GRAF`
  публичной идентичностью не становится. Владелец GRAF / оператор выпуска
  утверждает до публичной производственной сборки постоянные Package Name,
  точный Publisher по проверенному Subject, ожидаемое семейство, x64,
  поддерживаемые ОС, версию MSIX, точный SHA исходников, HTTPS-адреса
  `.appinstaller`, пакета и зависимостей и способ публичной подписи по
  [порядку T124](release-execution-plan.md#как-принимаем-публичную-поставку-t124).
  Регистрация, оплата, доступ к ключам и выпуск не входят в принятое решение;
  получение сертификата не становится новым предварительным условием разработки.
  Независимое ревью CHK001/CHK006 и существующие проверки публичного доверия
  сохраняются. Для выбранного канала T112 разрешает только ручное обновление
  после явного действия: установка не начинается при записи или незавершённом
  сохранении, новые записи блокируются перед передачей установки Windows,
  неуспешное ожидание отменяет установку; `drain` не подменяется `cancel`.
  Автоматическое и случайное понижение исключены; публичный `.appinstaller`
  не включает `OnLaunch`, `AutomaticBackgroundTask` и `ForceUpdateFromAnyVersion`.
  Смена тестового семейства требует отдельной проверки переноса на искусственных
  данных без автоматического удаления прежнего пакета и данных. T124/T112/T117
  остаются открытыми до своих проверок; ARM64 — до отдельной приёмки SC-010.
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
  overflow вычисления B и обычный capture fault отклоняют запрос, не чинятся
  ожиданием. Для старой пары q<L вычисленный B не применяется и может быть
  позади releasedEnd: продолжается прежняя пауза с тем же seq/T0/L/deadline.
  Для свежей пары q≥L сохраняется обязательный отказ при B<releasedEnd,
  без подгонки B или выдачи READY. Неубывание позиции, точный S_OK и все
  остальные проверки действуют также для старой пары.
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

**Уточнение T120 — 2026-11-06.** Опыт из validation-2026-10-02.md
с `first_clock_checks` подтвердил старую пару q<L и B<releasedEnd при
продолжающемся микрофонном потоке. Сравнение B с releasedEnd является условием
принятия свежей границы, а не условием ожидания уже непригодного B. Проверить
RED → GREEN через существующий controller/mailbox с первым B<releasedEnd,
последующим свежим B и подавлением unread prefix. Сохранить отрицательный
контроль свежей пары B<releasedEnd: одно чтение, нет ACK/CLOSE, Pause и Stop
работают, повтор с новым seq возможен. Отдельно остаётся проверка на устройстве.

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
Прежний AAC encoder использовал PCM/MF цикл: output IStream → MFByteStream →
SinkWriter с URL=null и explicit MPEG4 container attribute. Решение T116 от
2026-11-16 и контракт §5.1 заменяют только этот AAC encoding/muxing блок на
штатный FFmpeg; MF reader/playback и защищённый logical IO сохраняются. Штатный readonly Reader не становится
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
binding для §8.1 bridge contract. Новых task IDs и серверного API нет;
сама подсказка/квитанция не требует новой ledger-схемы. Дополнение persistent
access ниже выбирает только local queue v4. T088 остаётся открытой до приёмки.

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
   `DesktopHttpTransport::recordingLifecycleProtected` и
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

### T088: persistent access и восстановление локальной области — 2026-11-04

Продолжение FR-006/013/022, high-risk-product; порядок Main → requirements review
→ отдельно назначенные tests/code. Базовый bridge/receipt срез и его результаты
не принимают offline access. Формат — data-model §7.1 и local-custody §7.1.

1. Расширить existing `BasicUploadCustodyItem`/`ProtectedUploadQueueValue` и
   shared `decodeQueueLedger`/`serializeQueueLedger`: v4 writer, v2/v3/v4 reader,
   nullable raw access и один authenticated context. Проверить strict codec,
   canonical bytes, прежние adapters/copy/persist и BOTH mixed-version отказ
   old reader сначала в existing `DesktopUploadQueueV2Tests`; новых файлов
   состояния/фреймворка/task IDs и схем server/crypto/package-state нет.
2. В `NativeCapture` вычислять fingerprint существующим SHA256 из эффективного
   native identity-request origin/auth headers; не из полного HTTP config,
   document claims или cached scope. После настоящего account/notification
   proof сохранять context существующим recovery/lifecycle worker commit даже
   без origins. На cold startup восстанавливать отдельный local content scope
   после native cookie observation и принятой queue; network `currentAccount_`
   и `confirmedIdentity` из cache не заполнять. Смена runtime сессии отзывает
   restoration и потребителей; процессный epoch на диск не писать.
3. `pollAccount` останавливается при `currentAccount_`, а setAuthSessionToken
   возвращает рано при прежнем cookie. Один private coalesced revalidation intent
   ставят existing recover(activation/wake/scheduled/authRecovered), validated
   WebView reconcileAuthSessionForDocument → AppMain authSessionHandler даже
   при прежнем token, и проверенный transport scope_changed. Вызовы объединяются
   в один accountFuture; pending intent не теряется, retry использует прежний
   accountRetryAt_, без нового timer. Same-URL SPA без события достигается
   existing scheduled recovery 30s. Fresh config без confirmedIdentity/workspace
   выполняет spaces → auth/me, затем existing notification-context gate.
   Сохранить existing IdentityResult.status до NativeCapture: нынешний nullable
   no-arg getter теряет его; переиспользовать accountIdentity(IdentityGet) и
   native requestIdentity adapter внутри transport, не новый parser/API/schema.
   Transient failure оставляет local cache, но не подтверждает online workspace;
   authRequired не становится offline success. Native B вызывает общую existing
   auth-epoch/cancel invalidation даже с тем же token (не повторный вызов раннего
   setAuthSessionToken). AppMain инвалидирует прежние привязки по authGeneration
   также при asynchronous native смене. DOM mismatch закрывает действие, не
   присваивает B и не открывает доступ; cache fingerprint не workspace proof.
4. Подключить local scope к `localObservation`/созданию `DisplayWork`, open и
   playback predicates, а в `AppMain` отделить local document binding от
   network/reminder identity. Host сохраняет cookie/HTML/route/nonce fences.
   Общий content predicate используется в canOpen, native open/authorize/seek,
   fresh-owner PlaybackExchange, manual/automatic upload selection и его IO/
   continuation, а также прежнем local-removal gate. Nonowner отменяет active
   consumer только после проверки полного scope/target-valid restrictive answer.
   До submitProtectedDeletion выполнить scheduler.cancel и closeLocalPlayback;
   пока busy/work.upload, удерживать answer и не пускать pendingRecovery upload.
   resultReady cancelled flight получает ACK без applyUploadResult/commit;
   actual done+leaseReleased → retireProtected, затем lifecycle submit с новым
   snapshot, commit/readback/adopt. Already-started publication проходит прежний
   reconciliation до применения отказа. Nullable access включить в existing
   sameUploadIdentity; нового access revision counter нет. Actual drain/leases/
   pins продолжают прежний жизненный цикл, positive access только после adoption.
5. В `applyLifecycleEntries` менять private access field; existing
   `decodeSyncStateUsing` → `BasicUploadServerTruth` → apply сохраняет bounded
   raw access, включая access_revoked/stale_device_identity. Missing/null
   sync-state — no new value, не erase cached nonowner. Старый response не
   перебазируется поверх нового отказа без fresh owner/scope/generation/subject
   проверки. Квитанции монотонны, cleanup/ACK полномочия не расширяются.

Targets: `Contracts/WindowsDesktopContracts.h`, `Upload/DesktopUploadQueueService.*`,
`Upload/DesktopHttpTransport.cpp`, `Recording/NativeCapture.h`, `AppMain.cpp`,
`Web/WebView2Host.*`; существующий `Storage/Sha256.h` переиспользуется.
Изменения `ProtectedCustodyMetadata.cpp`, CMake, Mac/server и generic auth
refactor не являются необходимой частью этого выбора. T117 migration сначала
копирует exact исходный ledger; v4 upgrade — последующая обычная queue mutation.
Проверки/RED→GREEN — quickstart T088 persistent access, без новых CLI/deadlines;
generated metadata/audio, devices/network 0, прежние budgets и fair cursor.

## T121: shared-meeting handoff после master5485b92 — 2026-11-04

Existing F200 high-risk auth/privacy/navigation slice, no deploy. Clarify уже
определён пользовательским Mac parity и actual F292 source; новых продуктовых
вопросов нет. Owner T121, нормативные поля/маршруты — bridge §11, поведение —
spec Session2026-11-04. T106/T119 и storage T116–T118 не переопределяются.

Для недоказуемого возврата по legacy 303 выделен отдельный проект CHK022:
[§11.4](contracts/windows-native-web-bridge.md#114-проект-windows-возврата-после-входа-t121--chk022)
и [чеклист](checklists/t121-windows-auth-continuation.md). Сначала независимый
review/analyze, затем изолированные HTTP-регрессии с существующим шифрованием,
потом native lifecycle и installed acceptance. Оба явных перехода привязываются
к одной попытке; прежние маршруты Mac/браузера остаются совместимыми.
Работа ведётся в T121 / #7933 без отдельной задачи-дубля.

Основной путь уже в истории ветки: `f5d61539fc0fbcdd4a05f7416054fa1ac8e2ea57`
добавил активацию ссылки, строгий разбор маршрута и публичный просмотр без
моста. Ниже план оставшихся исправлений и приёмки существующего пути,
а не повторное внедрение. На текущем дереве отрицательная проба подтвердила
допуск моста для адресного reader и перенос позиции без версии в обеих
формах. См. [проверку текущей политики](validation-2026-11-06-t121-current-document.md#проверка-текущей-политики-windows).

1. В existing Windows contract tests сначала RED для shared intent/route и
   capability isolation публичной и адресной страницы. Переиспользовать syntax-only UUID validator
   WebViewRoutePolicy (upper/lowercase и nil), URL policy, single-instance activation, cabinet.open и actual document response
   latch. Один небольшой typed value для intent допустим; отдельный router,
   store, generic capability framework или новый JSON/server parser не нужен.
2. В AppMain receiveActivation/applyPendingActivation отделить host shared-meeting
   от attribution, сохранив его parser/store/sign-in поведение. Один latest-valid
   pending shared intent; existing admission/lifetime/UI dispatch. Скрытие
   в трей сохраняет ожидание, новая ссылка выводит окно без изменения записи;
   явный выход прекращает ожидание. Сначала
   canonical route, затем обычная navigation: external URI не назначает account.
3. WebViewRoutePolicy: единые strict validators §11 для создания и повторной
   проверки routes. Ни публичный, ни адресный reader не используют общий
   `meetingDetail` с bridge, в том числе для владельца. Отдельно проверить
   серверные разрешения для адресного экспорта и прежние права своего кабинета.
   `isAllowedDownload` не принимает public media/continuation или public blob.
   Не приравнивать адресный reader к публичному при выборе способа входа:
   адресный сохраняет локальный `next`, публичный использует серверное
   продолжение. Переиспользовать ветку показа подтверждённого HTML без моста,
   отдельно сохранив разрешённое сервером адресное вложение; простая подмена
   `RouteKind::meetingDetail` на `RouteKind::publicReader` ломает оба пути.
4. WebView2Host: успешный current correlated HTML response общего reader
   должен показываться без bridge. Сейчас completeDocumentNavigation допускает
   cabinet только при allowsNativeBridge, а nativeActivateDocument требует bridge;
   простое расширение route allowlist либо оставит fail, либо выдаст лишние права.
   Использовать существующий unprivileged display lifecycle с точным current
   response/completion proof, без ослабления T103 history GET fences и без
   влияния на auth/payment states. После replacement старые native actions,
   nonce, local publication/visibility/user-time callbacks не актуальны.
5. Recovery: нынешний safeRecoveryUrl требует bridge и теряет query/fragment;
   изменить только bounded shared-reader GET handling, не общий произвольный
   next. Public login идёт через серверный continue; addressed login сохраняет
   canonical query/fragment. Согласовать signInUrlBuilder, requested/safe URL,
   redirect response и fresh intent из recovery, сохранив attribution T106.
   Проверять продолжение и итоговый переход до смены документа; устаревшая
   цепочка A не открывает A после перехода на B или logout, даже если сервер
   принял свой cookie. Сравнения URL без подтверждения текущей цепочки мало.
   Содержимое sealed cookie не читать; если цепочку нельзя подтвердить,
   показывать штатный повтор. Без версии не переносить позицию, включая 0.
   Native cookie read сейчас запущен внутри bridge activation, а
   reconcileAuthSessionForDocument требует ready/nonce/allowsNativeBridge.
   Отделить existing own-cookie/session reconciliation для доказанно текущего
   unprivileged shared document от выдачи bridge; не включать bridge ради
   refresh сессии. Сохранить native cookie read, generation/source/response
   proof, stale cancellation и существующее account/context confirmation.
   Прежние privileged-document checks не ослаблять; intent/DOM не назначают
   account, а публичному reader не публикуются local rows/nonce/effects.
6. Connected callers review перед SOURCE GO: navigate/begin/complete/activate,
   source/history changes, native script installation/message validation,
   userTimeDocumentCurrent/localContentDocumentCurrent, inventory publication,
   visible/local recording/deletion/calendar handlers, downloads/new-window,
   response/header correlation и cabinet/native lifetime. Header X-GRAF-Client
   может выбирать embedded presentation, но не выдаёт bridge/account authority.
   Shared-page media использует WebView network, без нового native fetch/cache.

Технический риск, требующий реализации/доказательства, конкретен: текущий host
связывает successful cabinet display с bridge authority. Это не неясный
продуктовый выбор; ветка read-only должна пройти и portable, и actual SDK path.
Windows manifest сейчас регистрирует только `grafrec`, Mac Dev — `grafrec-dev`.
Проверить путь от штатной кнопки отдельно от parser тестов: два адреса
одинаковой изолированной сборки кабинета с одним набором искусственных
данных, для Windows — не-loopback HTTPS с `grafrec`, для Mac Dev — loopback
с `grafrec-dev`. Это настройка стенда, без подмены ссылки и изменения
регистрации пакетов. Пока доверенный адрес Windows зашит в пакет,
изолированный прогон требует отдельной QA-сборки с зафиксированным адресом
и своим хешем; отдельно нужен прогон точного кандидата на его разрешённом
сервере. Подмена DNS или обход проверки HTTPS не используются.
Закрыть отдельно обнаруженный разрыв позиции без версии
на Mac до зачёта паритета; изменения общих контрактов вести по CHK022.

До кода обязательны independent requirements/design review, применимый текущий
reviewer-checklist gate, analyze без unresolved C/H и issue sync по T121; данный
проект не объявляет их пройденными и не создаёт issue. Затем focused source,
synthetic/actual WebView2 и installed T097/T063 evidence отдельно. Никакой новой
серверной схемы, бизнес-логики, public DTO или durable local storage.

Первый самостоятельный срез T121 — разбор входящего `grafrec://shared-meeting`
в `WebViewRoutePolicy::sharedMeetingRoute` и его тесты. После действующей
проверки формы ссылки позиция без версии записи отбрасывается, вкладка
сохраняется; позиция с версией, включая 0, передаётся для дальнейшей сверки
проигрывателем. Срез не меняет допустимые маршруты, полномочия, WebView,
вход и восстановление после входа. Для него действует отдельный
[чеклист требований](checklists/t121-windows-inbound-position.md);
перед переносом в рабочие исходники нужен полный PASS этого чеклиста,
анализ среза без C/H и существующая связь T121 с #7933. Общий чеклист
T121, цепочка восстановления и сравнение двух установленных приложений
остаются отдельными воротами; результат среза их не закрывает.

Второй самостоятельный срез T121 — нормализация допустимого GET-адреса
просмотра в `WebViewRoutePolicy` и использование результата в
`WebView2Host`. Адрес повторного просмотра, публичный `/continue` и
адресный `/login?next=…` должны сохранять вкладку, а позицию передавать
только с синтаксически допустимой версией. Оба пути входа сохраняют свой
прежний механизм возврата. Программный переход и ранний повтор до
`NavigationStarting` используют ту же нормализацию, чтобы запасной
адрес не возвращал удалённую позицию. Срез не меняет правила допуска
входящего HTTPS или ответа сервера, выдачу нативного моста, OAuth
или логику кабинета.
Перед переносом кода — независимый полный PASS
[чеклиста этого среза](checklists/t121-windows-recovery-position.md),
анализ без C/H и существующая связь с #7933. Установленная проверка
входа и полный чеклист T121 остаются открытыми.

Отдельный общий серверный срез T121 (CHK022) — только нормализация
позиции при выдаче и поглощении публичного продолжения. Применяется к
Mac, Windows и браузеру. При входе или регистрации ссылка без версии
сохраняет вкладку, включая `recording`, и теряет позицию. Действующий
подписанный cookie старого формата подчиняется тому же правилу после
проверки прежних границ; позиция с допустимой версией, включая 0,
передаётся проигрывателю для проверки совпадения версии. Некорректный
контекст и повреждённый или истёкший cookie отклоняются как прежде.
Токен ссылки остаётся вне `login?next`; формат cookie, срок, серверные
права, OAuth, база и миграции не меняются. При откате прежний код
может прочитать cookie, выпущенный новым кодом. Проверить реальные
HTTP-обработчики и грант на отдельном PostgreSQL с искусственной записью.
Перед переносом — полный независимый PASS
[чеклиста](checklists/t121-shared-cookie-position.md) и анализ без C/H;
привязка к #7933. Привязку OAuth-возврата к текущему поколению Windows
и позицию в напрямую открытом reader проверять отдельно.

Отдельный общий срез T121 (CHK022) — адресная страница общей встречи
и адрес её возврата после входа. При переходе внутри страницы позиция
применяется только к версии, показанной текущим документом. Более
свежая ручная перемотка, выбор вкладки или смена адреса отменяют
ожидание метаданных предыдущей ссылки. «Назад» и «Вперёд» восстанавливают
вкладку и допустимую позицию; адрес без фрагмента возвращает исходную
вкладку, заданную серверной страницей. Переход по ссылке не переносит
клавиатурный фокус на расшифровку и не запускает проигрывание.
Устаревшая версия показывает одно уведомление с доступным действием
«Открыть новую запись с начала».

На адресном входе и регистрации явный фрагмент `next` имеет приоритет
над унаследованным фрагментом. Неподтверждённая позиция исключается из
формы и существующих ссылок на вход, включая провайдеров; вкладка и
канонический ресурс сохраняются. Проверить фактически отрисованные
формы и прежние границы возврата. Этот срез не меняет серверные права,
настройки провайдеров, публичный cookie, нативный мост, маршруты или
политику загрузки. Перед изменением общих исходников нужны независимый
PASS [чеклиста](checklists/t121-addressed-position.md), analyze без
нерешённых C/H в этом срезе и связь с #7933. Публичный проигрыватель,
сквозной вход и установленная приёмка остаются отдельными сценариями.

### T121: позиция публичной встречи — отдельный общий срез CHK022

Изменение ограничено публичным проигрывателем `public-sharing.js` и
его браузерной проверкой. При применении ожидания и построении перехода
использовать текущий допустимый фрагмент. История и переходы по вкладкам
сохраняют уже достигнутую позицию без повторной перемотки; явно заданный
таймкод создаёт новую команду. Проверить оба порядка событий и все три
действия ссылки на штатном HTML с искусственным WAV.

До продуктового кода: независимый PASS
[чеклиста](checklists/t121-public-pending-seek.md), analyze без C/H
для среза и существующая задача [#7933](https://github.com/yshishenya/graf/issues/7933).
Адресная страница, серверные обработчики, cookie, мост, маршруты и
установленная приёмка вне этого среза. Откат — возврат скрипта и теста;
постоянные данные и форматы не меняются.

### T083: обращения по отказам очереди — 2026-11-06

Область: US3, FR-006/013 и SC-005/006; high-risk-product из-за сессии
и диагностических метаданных. Эталон — текущий
`DesktopSupportIncidentActionStrip`, `DesktopUploadQueueService` и
`EmbeddedCabinetSupportIncidentBridge`. F061 описывает первоначальный
сценарий, действующие POST и поля ответа сверяются с F114 и серверным кодом.
Это уточнение T083; не меняет политику обработки записей.

Предварительная проверка exact source
`d1340645da9cb9f401861cc42406b514e8e16fad`: настоящий
`build_server_redacted_report` сохраняет `com.graf.desktop`, отбрасывает
`platform` и `windows_version`; `build_github_issue_draft` присваивает
`area:macos`. Контрольный Mac сохраняет версию ОС; запрещённое поле аудио
отклонено. Тест только строил локальный черновик в памяти, запросов и
обращений не было. Нельзя принять этот результат за действующую Windows
интеграцию или подменить версию Windows в поле `macos_version`.

Контроль старого фильтра подтвердил `support_incident.unsupported_schema`
для пробной v3; 24 текущих модульных теста F114 прошли. Это проверка функций
на искусственных данных, не запуск рабочего сервиса.

Порядок разработки:

1. Согласовать отдельное [дополнение общего F114-контракта](../114-support-incident-diagnostics/contracts/support-incident-v2.md#дополнение-для-t083-windows-проект-ещё-не-действует) до подключения
   Windows. Предпочтительная форма — новая версия отчёта на тех же
   endpoints, чтобы старый сервер отклонял её, не создавая обращение с
   меткой Mac. Совместимость v1/v2 Mac, серверная фильтрация, tenant scope,
   ограничение размера, вычисление дедупликации и private target сохраняются.
   Платформа из разрешённого перечня влияет только на диагностику и метку,
   не на авторизацию. Проект метки: `area:windows` вместо `area:macos`;
   Windows остаётся в F114 и не падает в ветку F061. Отсутствие нужной метки
   не разрешает создать обращение с другой платформой и не блокирует Mac.
   Точная форма, проверка меток и переход включаются в отдельную задачу
   общего контракта, не в клиентскую T083.
2. Windows повторяет нативные действия Mac для записи и группы. Отправитель
   использует только действующий документ собственного кабинета и точные
   same-origin маршруты создания/синхронизации, с существующей web-сессией,
   CSRF и проверкой actor/workspace/session до POST. Отдельная capability
   у публичной страницы не появляется. Запрос после logout, смены страницы,
   аккаунта или workspace не получает разрешение; поздний ответ не
   принимается. Закрытый кабинет и недоступная сеть оставляют копирование.
3. Защищённая очередь фиксирует намерение до POST и принятый номер до показа
   результата. Применяются подтверждённая запись, повторное чтение и adoption;
   при неопределённой записи сначала сверить состояние хранилища. Группа
   следует Mac (`copyKey` и ответственный). Привязать попытку к исходному
   составу, аккаунту/пространству и поколению; исключить пересекающиеся действия
   и повторно проверять право на каждую строку, в том числе при копировании.
4. Различать отказ, неизвестный исход без номера и принятый `pending_sync`.
   Ручной повтор без номера допускается только с тем же ключом и доказуемо
   тем же отчётом и группой. Отпечатка недостаточно: отчёт включает меняемые
   поля, а старый ключ с новым содержимым получает 409. До кода согласовать
   ограниченный защищённый снимок разрешённых метаданных и срок его хранения
   либо эквивалентное точное восстановление. При невозможности доказать
   совпадение доступно копирование; нет автоматического повтора. С номером —
   только ручной sync, номер остаётся при отказе. Данные входа и ответ
   целиком не сохраняются. Отзыв доступа закрывает отображение и действие.
5. В общем F114 закрыть подтверждённый разрыв синхронизации. На том же
   source SHA, в одноразовой PostgreSQL с настоящими функциями создания,
   повтора и синхронизации и транспортом GitHub без сети: первое создание
   принято подменой GitHub, но клиент получил тайм-аут. Точный повтор
   вернул тот же `pending_sync` без вызова GitHub. Ручной sync затем сделал
   второй POST: в подмене два Issue с одним CUST, в базе одно обращение.
   Другой автор с собственным устройством в том же пространстве получил
   409 на тот же ключ и 404 на sync, без чужого номера или вызова GitHub.
   Сценарий не доказал раскрытие CUST, но показал общий конфликт ключей в
   пространстве. Отчёт `t083-support-replay-5NoCCwgr/result.json`,
   SHA-256 `1a3c65b54500e507ab1a70d68745491adf231390ea50774aabbb0e2f917f496a`.
   Запросов в рабочий сервис или GitHub не было.
6. Отдельно подтверждён дубль без тайм-аута на
   `3dfeaff5a6774ab12be781547e4a300f9ce2a46c`. Два вызова ручного sync
   одного CUST шли в разных транзакциях; PostgreSQL подтвердил, что
   вторая ждала блокировку первой. После подтверждения первой операции
   обе вернули «синхронизировано» с разными номерами Issue. В подмене
   GitHub было два POST и два Issue, в базе один CUST со второй ссылкой.
   Следующий одиночный sync внешнего запроса не сделал. Здесь нет потери
   ответа: вторая транзакция прочитала запись до ожидания и не перечитала
   её перед внешним действием. Серверный критерий должен покрыть и эту
   гонку, и отдельно потерю подтверждения после создания.
   Проверены 9 точных входов до и после. Использованы реальные функции
   сервиса, одноразовая PostgreSQL через локальный сокет и имитация
   транспорта GitHub. База удалена; HTTP-авторизация и рабочий сервер
   в проверке не участвовали.
   Отчёт `t083-concurrent-sync.pbx4DHTO/race-reviewed.json`,
   SHA-256 `1ed15148b2531e43f7ad7657045d9d81b5b031500a66f363c4f19b692b949a41`.

До изменения кода: независимое review контракта и требований, analyze
T083/F114 и синхронизация соответствующих задач. Изменение общего
контракта проходит свой server gate; работа над клиентом не меняет
серверную бизнес-логику, а локальные проверки не меняют рабочий сервер.

### T088: имя Windows-приложения в списке сеансов — 2026-11-07

Существующая задача T088; требования FR-006/SC-002 и серверный эталон
[F6794](../6794-active-account-sessions/spec.md) / [F6795](../6795-persistent-app-session/spec.md).
[Воспроизведение](validation-2026-11-07-t088-session-platform.md)
подтвердило неверную подпись без изменения прав или данных.

По независимой проверке рабочий вариант — отдельная ограниченная
подсказка на конечном запросе входа к настроенному GRAF. Переиспользовать
общий список сеансов. Поля обычной регистрации устройства
`platform`, `client_version` и `device_public_id` не определяют
подпись приложения: их задаёт клиент. Не менять
глобальный User-Agent WebView2 и значение `X-GRAF-Client: desktop`.
Версию брать только из проверенных сведений сборки; при их отсутствии
показать «Версия приложения неизвестна». Существующие строки не переносить.

- Возможные точки: POST подтверждения email при входе или регистрации
  и GET обратного вызова уже разрешённого провайдера. Точные маршруты
  сверить с действующим кодом. Допуск привязан к схеме, адресу, порту,
  маршруту и методу. [Нативная проба](validation-2026-11-07-t088-session-platform.md#проверка-заголовков-в-реальном-webview2)
  показала, что WebView2 добавляет `Sec-Fetch-Dest` после перехватчика:
  проверять `document` в самом перехватчике нельзя. Предлагаемая граница
  для отображения — принять признак только при единственном
  `Sec-Fetch-Dest: document` на сервере; `iframe`, пропуск или
  неоднозначность оставляют прежнюю подпись. Проверить реальные
  заголовки во всей цепочке HTTPS, включая внешний запрос, вложенный
  документ и соседний маршрут. Это условие показа, вход от него не зависит.
- Сервер использует подсказку только для подписи после обычной проверки
  входа. Неверное, отсутствующее или неоднозначное значение оставляет
  прежнюю классификацию. Браузерный переход оплаты (`browser_only`)
  игнорирует обе метки даже при явно переданных метаданных; вне оплаты
  при конфликте сохраняется действующая подпись Mac.
  Привязка провайдера не переименовывает существующий
  вход. Признак не включать в URL, OAuth state, cookie, логи или решения
  о правах. Поддельная подсказка не меняет отказ, продление или отзыв.
- Предлагаемый отдельный серверный срез по CHK022: поле
  `RegisteredDevice.windows_desktop_version` с допустимым `NULL`, длиной
  до 23 знаков хранит только проверенную ASCII-версию из §12 либо `unknown`.
  Миграция добавляет поле без заполнения старых записей.
  Запись — только при успешном новом входе; перенос при замене устройства
  рабочего пространства — только из серверного поля проверенного
  устройства исходного сеанса, без чтения заголовка и публичных полей
  для подписи. Если устройства или значения нет, оставить `NULL`.
  Обычная регистрация не меняет поле. Проверить запуск прежнего кода после добавления
  поля и возврат к прежней подписи без изменения данных входа.
- До кода: согласовать отдельный серверный срез и общий контракт,
  проверить чеклист и analyze, синхронизировать зависимости T088.
  Затем проверить реальные email/OAuth/billing запросы на отдельном
  сервере и тот же путь на установленных Windows и Mac.

### T117 — устойчивость нового карантина очереди к откату

FR-012/013/022, SC-005/008, [§8 контракта](contracts/windows-protected-local-custody.md).
[Точный исторический читатель](validation-2026-11-06-t117-historical-queue.md)
отказывает после switch, но способен заменить изменяемую цель и убрать
sentinel. [Нативные проверки](validation-2026-11-06-t117-gate-publication.md)
подтвердили no-replace публикацию, восстановление после остановки процесса,
сброс привязки имени и конфликт прав при передаче усиленного root владельцу.
Исправление не добавляет старому клиенту доступ, не меняет формат очереди
и не продлевает исключение старого читателя.

1. Использовать текущие `ProtectedCustodyQueueMigration::openImpl` и
   `ProtectedCustodyFiles::installQueueMigrationBarriers`. Единственный
   кандидат на `FILE_ADD_FILE` — закрытый fallback восстановления очереди
   из `ProtectedCustodyMigration::open` после `openProtected` с
   `recoveryRequired`. Он получает право при первом захвате конечного
   корня с прежним `FILE_SHARE_READ`, **для классификации**, пока состояние
   ещё неизвестно. Это не право на мутацию. Отказ усиленного открытия,
   конфликт или отмена завершают проход, без повторения в менее строгом
   режиме. Обычный `prepare` без переключения, discovery, `openProtected`,
   чтение и обычный владелец используют прежний режим.
   - Исходник под старым именем, нет gate/stage и strict исходный inventory
     допускает новый либо уже признанный pre-fence профиль: разрешены
     существующие prepared/Birth, bootstrap и `copiedVerified` шаги.
     Если закрывающий bootstrap и обе записи intent уже подтверждены
     в `prepared` либо `copiedVerified`, продолжить тот же перенос и
     тот же transaction с прежними IDs и Birth. Отсутствие stage после
     автоматического удаления не означает новую инициализацию или
     право чинить неполную историю. Публикация допустима только после
     прежних проверок и подтверждения `copiedVerified`.
   - Исходник ещё под старым именем, есть stage или readonly gate: сначала
     без записей сверить уже существующие обе записи intent, актуальный
     `copiedVerified`, закрывающий bootstrap, исходник и committed Birth.
     Если что-то не подтверждено, не создавать недостающую историю для
     оправдания находки. После проверки действуют точные правила stage
     и повторного сброса имени из §8.
   - Оригинал уже перенесён и подлинный карантин удержан. Новая
     публикация не нужна. При отметке о переносе пакета `openImpl`
     останавливается: её проверяет отдельный путь `openProtected`.
     Подтвердить защиту по следующему разделу **до** снятия временного
     права по шагам 3–4. Только после повторной сверки можно продолжить
     доказанную ветку. Отсутствие sentinel допустимо только в
     незавершённой стадии между rename оригинала и созданием sentinel.
   - Неизвестный stage/gate, неаутентифицированные пары, отсутствующий
     обязательный маркер или противоречие истории: отказ без новой
     мутации. Изменяемый gate не допускается в протоколе новой публикации;
     отдельное подтверждение защиты уже существующей подлинной цели
     определено в следующем разделе.
2. Разделить существующую публикацию: точный зашифрованный stage и flush
   → no-replace rename → подтверждённый flush каталога → прежний перенос
   исходника → проверенный sentinel → прежний switch. Точное состояние
   восстановления и допустимое имя stage заданы §8. Уже перемещённый
   оригинал, missing marker, чужой stage, singleton, повреждённые пары,
   package fence и authorized cleanup не переводить в fresh birth.
   Только известный остаток можно убрать под удерживаемым дескриптором.
   Обычные inventory validators не принимают stage; только закрытая
   ветка восстановления может распознать точное имя и проверить его
   после аутентификации intent, до любой новой мутации.
3. Для fresh-ветки после подтверждения двух `switched` intent и двух
   protected bootstrap, перед сбором package inventory, заменить только
   конечный root handle. Для распознанного уже перенесённого оригинала
   или package fence сделать ту же смену после проверки состояния и
   подтверждения защиты карантина, до продолжения прежнего сценария.
   Взять промежуточный `FILE_LIST_DIRECTORY` с
   `FILE_SHARE_READ | FILE_SHARE_WRITE` без `FILE_SHARE_DELETE`, сравнить
   FileId/том, закрыть усиленный, открыть обычный и повторно сверить, затем
   снять промежуточный. Не использовать `DuplicateHandle` или handle
   только для атрибутов как доказательство защиты от удаления.
   Несовместимый доступ на запись завершает текущий проход без допуска.
4. Сохранить исходный `State`, роли, удерживаемые маркеры и оригинал,
   точный набор проверок отсутствия и sticky conflict. После смены
   дескриптора перечитать пары и Birth/маркеры/оригинал на уже
   удерживаемых объектах; обычные повторные открытия тех же файлов
   могут конфликтовать с этими дескрипторами. Выполнить строгую проверку
   всего корня и отсутствий до любого следующего package write;
   `migrationPackages` один недостаточен. Не пытаться продолжить
   через новый worker в том же проходе после обнаруженного конфликта.

#### T117 — ранее созданный карантин: проект решения

Исторический reader способен убрать sentinel, даже когда сообщает отказ.
[Изолированная проверка NTFS](validation-2026-11-07-t117-ntfs-replay.md)
различает видимый и переживший повторное подключение атрибут. Она
обосновывает выбор кандидата на повторное подтверждение, но сама не
проверяет работу GRAF и потерю питания.

1. **Незавершённый перенос.** В `ProtectedCustodyQueueMigration::openImpl`
   использовать существующее закрытое открытие корня. Сначала проверить
   обе записи intent и bootstrap, Birth, пару очереди, исходник в точном
   ожидаемом месте и полный состав файлов. Уже опубликованный карантин
   должен совпасть с ожидаемым Birth под удерживаемым дескриптором.
   Подтвердить его защиту и перед переносом оригинала, и при возобновлении
   между переносом и созданием sentinel. Во втором случае подтверждение
   предшествует `retirePublication(false)` и любой дальнейшей мутации.
   Отсутствие sentinel допустимо только в уже признанной стадии переноса.
2. **Завершённый профиль.** Узкая точка — холодный
   `ProtectedCustodyStoreOwner::open`, включая его прямых вызывающих.
   Сначала обычная проверка целого профиля, включая обе записи истории,
   package closure, оригиналы или подтверждённую очистку, и обязательные
   gate/sentinel. Удерживать те же два файла до конца подтверждения.
   Временный доступ на корень допустим только в этом закрытом шаге.
   Обычный режим с `FILE_SHARE_READ` конфликтует с одновременным
   усиленным открытием. Для повышения и снятия доступа использовать
   промежуточный `FILE_LIST_DIRECTORY` с `FILE_SHARE_READ | FILE_SHARE_WRITE`
   без разрешения удаления, с проверкой того же тома/FileId при каждой
   смене. До сброса и после возврата в обычный режим заново сверить
   полный снимок. Общий `validate`, диагностическое
   чтение, очистка под уже выданным владельцем и профиль без прежней
   очереди этот шаг не используют.
3. **Уже перенесённая очередь, но ещё не все пакеты.** Закрытый
   `openProtected` тоже должен подтвердить защиту очереди до выдачи
   worker, который может вызвать `migratePackage`. Действующий package
   fence проверяется только здесь: `openImpl` продолжает перенос
   очереди и отклоняет любую отметку о переносе пакета без изменений,
   в том числе смешанную пару в любом порядке слотов.
   При каждой публикации заново сверить оба проверенных индекса под
   блокировкой записи хранилища до создания новых блоков.
   Этим уточнением заменён прежний вариант маршрута из ревью CHK005;
   требование подтверждения защиты до первой записи не меняется.
   Сначала проверить обе записи очереди и bootstrap, полную историю
   перехода, оба обязательных маркера, применимый состав, отсутствия
   и уже начатый package fence. Повторно проверить их после снятия
   временных прав. Успех обычной проверки после переноса пакета не
   заменяет проверку **до первой записи пакета**. Профиль без истории
   прежней очереди не получает временное право по этому правилу.
4. **Подтверждение в текущей попытке.** Для подлинной изменяемой цели
   добавить только `READONLY` и сбросить тот же дескриптор, через который
   поставлен атрибут. Для карантина последовательность такая:
   `GENERIC_READ` с `FILE_SHARE_READ` → промежуточный `GENERIC_READ`
   с `FILE_SHARE_READ | FILE_SHARE_WRITE` без совместного удаления →
   закрыть исходный дескриптор → `GENERIC_READ | GENERIC_WRITE`
   с `FILE_SHARE_READ`. Сверить тот же том/FileId и аутентифицированные
   байты на записывающем дескрипторе, поставить атрибут, сбросить этот
   же дескриптор и вернуться к обычному чтению через промежуточный.
   Sentinel, если он обязателен для стадии, остаётся удержанным всё время.
   Промежуточный дескриптор блокирует удаление, но допускает
   конкурирующую запись; без повторной сверки менять атрибут нельзя.
   Если защита уже появилась в момент смены режима или обнаружен
   конфликт, не снимать атрибут и не продолжать этот проход.
   Для уже видимого `READONLY` повторно сбросить
   удерживаемый родительский каталог с существующей маской
   `READ_CONTROL | FILE_READ_ATTRIBUTES | FILE_LIST_DIRECTORY | FILE_ADD_FILE`
   и `FILE_SHARE_READ`; без снятия `READONLY`, изменения `ARCHIVE` или
   записи заново. Атрибут, видимый после неоднозначного отказа, сам по
   себе недостаточен. Повторно сверить атрибуты, содержимое и FileId,
   идентичность корня, точные маркеры/оригиналы, обе пары, состав и
   наблюдавшиеся отсутствия после снятия временного доступа. Не вводить
   новую запись о завершении: следующий холодный запуск подтверждает
   защиту заново, пока профиль использует прежнюю пару маркеров.
5. **Отказ.** Неподлинный или пропавший обязательный маркер, неизвестный
   файл, несовместимый дескриптор, подмена, отмена и любой неоднозначный
   сброс прекращают попытку с точным отказом. Ошибка начатого
   подтверждения должна отличаться от структурного результата «нужно
   восстановить незавершённый перенос» в координаторе: прежние
   `StoreOwner::open → openProtected → openImpl` переходы после неё
   запрещены независимо от нативного кода ошибки. Не выдавать ни
   владельца, ни worker, не начинать запись пакета, не делать следующий
   шаг переноса. После уже поставленного `READONLY` не снимать его при
   ошибке. Сброс каталога как подтверждение для старого карантина пока
   проверяется только на NTFS. Для другой ФС без эквивалентного
   доказательства этот шаг не может подтверждать допуск; общие правила
   для профилей без миграции не меняются.

[Сценарии приёмки](quickstart.md#t117--публикация-защитного-файла-и-откат)
проверяют прерванную очередь, перенос пакетов и завершённый профиль раздельно. Отказ старого reader сам по себе не
принимается: обязательны неизменность обоих имён и обычный запуск GRAF
после него. Переход и выпуск остаются открытыми.

### T119: стабильный HTTPS перед передачей Windows — 2026-11-06

Уточнение существующего §10 и T119, high-risk-product. После проверки
authority кодировать только буквальные кавычку, обратную косую черту и
пробел в пути, параметрах и фрагменте. Уже закодированные значения,
разделители, host-policy и выбор получателя не меняются. Ссылку
длиннее 8192 байт после нормализации отклонять как invalid_target до
передачи: повторная проверка валидного результата должна быть идемпотентна.
Узкое независимое ревью требований не выявило C/H после учёта границы
длины; [T119 / #7540](https://github.com/yshishenya/graf/issues/7540)
остаётся владельцем, нового формата или задачи нет.

Контроль: общая таблица адресов 141/141, точные байты пути, параметров
и фрагмента при двух проверках, граничная длина, пустой путь Телемоста
с параметрами и WinRT Uri в нативном и браузерном режимах на подмене
только системного запуска. Не вводить явный запуск через класс реестра
по результату этой проверки. Получатель, установленный MSIX, сквозной
сценарий и допуск к записи проверяются отдельно.

### Опытный запуск автоматических проверок Windows в PR

Отдельный инфраструктурный срез F200 для одинакового процесса развития
macOS и Windows. [План пилота](windows-pr-verification.md) задаёт область
изменений, пять синтетических тестов, привязку отчёта к PR и пределы
доверия. [Чеклист требований](checklists/windows-pr-verification.md)
проверяется независимо до правки задания GitHub. Локальный прогон
поддерживает T063/T071, но не закрывает их. Опытное задание не меняет
настройки защиты ветки, обязательные проверки и условия выпуска.

### T097: отмена экспорта при смене исходной страницы

Уточнение существующего сценария, [T097 / #7240](https://github.com/yshishenya/graf/issues/7240).
Загрузка и выбор пути принадлежат одному готовому документу WebView2
и его окну. Подтверждённый переход или потеря готовности закрывает
уже открытый диалог и отменяет выдачу пути; смена поколения не является
обязательным условием отзыва. Изменение фактического URL источника,
включая `replaceState` и фрагмент в том же документе, отзывает
конкретный экспорт при несовпадении с исходным URL. Отклонённая
навигация, оставившая тот же URL и готовый документ, экспорт не отзывает.
Отзыв необратим для этого запроса: возвращение на исходный URL,
восстановление готовности и ошибка закрытия не разрешают выдать путь.
После отзыва старый ответ не очищает слот нового диалога и не возвращает
фокус в старое окно. Обычный выбор пути и отмена сохраняются.

Рабочий кандидат реализации — T123, отдельная задача повышенного риска
(нативный интерфейс, данные пользователя, приватность). T097 остаётся
приёмкой точного пакета; серверные маршруты, разрешённые выгрузки и
macOS-код не меняются. Прежнее решение с `IFileSaveDialog` и
`IFileDialog::Close` отклонено для этого исправления: реальный диалог
с владельцем кратко возвращал фокус GRAF после переключения пользователя,
а без владельца терялась обычная клавиатура. См. [исследование](research.md#t123-нативный-экспорт)
и [проверки](validation-2026-11-06-t097-export-focus.md).

Сделать дочернюю нативную панель в том же окне и на его UI-потоке,
с системным `IExplorerBrowser`. Связать подписку, окно и состояние с
фактическим временем жизни дочернего HWND, включая уничтожение
родителем, повторный вызов и ошибку закрытия. Пока переход по папкам
не завершён, путь не выдаётся. В обработчиках Enter, двойного щелчка
и меню проводника разделить навигацию папки и выбор имени, не запускать
файлы. В обычном Save/Cancel восстанавливать прежний элемент только
в активном и актуальном окне; на отзыве не активировать окно и не
трогать фокус. Не оставлять старый диалог как запасной маршрут.

WebView2 скачивает только в свежую закрытую папку конкретного запроса.
Запись, копирование, проверка идентичности и восстановление выполняются
за пределами UI-потока. Windows связывает операцию с выбранной папкой,
а при замене удерживает точный исходник от показа подтверждения
до переноса с защитой от изменения и подмены.
На томе назначения создать новый временный файл с ограниченными правами,
перенести полные байты и выполнить операцию по открытому дескриптору,
запрещающую замещение нового имени. Этот же путь покрывает другой том.
Условную замену квалифицировать отдельно: зафиксировать защищённое
намерение до переноса исходника в уникальное резервное имя. При сбое
проверить точные объекты и применить таблицу восстановления из
контракта; вернуть исходник только в свободное место без замещения.
Нельзя стирать данные при неоднозначном состоянии. Если место сохранения
не даёт нужных гарантий, показать ошибку с выбором другого пути.

Сначала покрыть отдельными нативными тестами отказ при конфликте и
сбой с восстановлением, затем подключить панель и реальный WebView2.
В коде переиспользовать текущие проверки источника и результата;
не добавлять новый маршрут, веб-команду, сервис, постоянный реестр
пользовательских путей или новый фоновой агент. Подробности о границе
фиксации, собственных временных данных и приватности:
[контракт T123](contracts/windows-export-save.md).

Критерии прогона: обычные Save и Cancel с клавиатурой; реальная
принятая навигация и искусственный отказ на том же поколении, оба
пока открыт диалог; отсутствие файла и подтверждённая отмена; после
навигации новый диалог из готовой страницы открывается и работает.
Отдельный управляемый прогон: задержать завершение A после отзыва,
дать B занять слот и доставить старое завершение A. Оно отменяет
только свой запрос и не очищает, не закрывает и не меняет B. Проверить
также изменение URL внутри документа, отклонённый переход и ошибку
закрытия с последующим поздним выбором.
После смены активного окна подтверждать отсутствие перехвата фокуса
отдельно. Сравнение и приёмка установленных оболочек по T097/SC-009
остаются обязательными. [Чеклист требований](checklists/t097-export-dialog-revocation.md).


### T097: контрастная палитра открытых нативных окон

Причина и воспроизведение:
[диагностика текущего кандидата](validation-2026-11-08-t097-native-contrast.md).
Уточнение FR-002/SC-009 остаётся в T097, задача GitHub #7240.

- Сначала проверить независимым ревью требования, [чеклист](checklists/t097-native-contrast.md)
  и границы: холодный вход с активным контрастом, смена палитры A → B без
  смены режима, выключение контраста, повтор одного и того же состояния.
- В действующем обновлении кистей WinUI назначить подписи акцентной
  кнопки цвет текста выделения, а фону оставить цвет выделения. Без
  контраста используются прежние цвета GRAF. Полный проход
  `refreshNativeState` уже обновляет кисти при смене системных цветов;
  сохранить этот путь. Изменение не требует пересоздавать окна, менять
  их фокус, захват или оформление кабинета, уведомлений и экспорта.
- Сначала регрессия на двух искусственных системных палитрах и на выходе
  из контраста; затем MSVC и настоящий WinUI; финальная проверка на
  установленном MSIX с двумя реальными темами Windows, клавиатурой,
  Narrator и масштабом 200%. Локальное изменение режима оформления
  системного профиля выполняется только в изолированной среде проверки.

### T104: подсказка панели записи — 2026-11-08

High-risk-product, действующая T104/#7281; T109 сохраняет общий шаблон,
T119 владеет открытием встречи. Эталон
`bd088c8fdea6007a12df3eee13da62b20e3c5828`:
`TwoBrainRecApp.refreshCalendarReminder` → `DesktopCalendarReminderService`
→ `CaptureControlViewCore` → `DesktopCalendarPromptActions`. Это не
`DesktopNotificationPresenter`: правила F277 остаются отдельными.
[Воспроизведение](validation-2026-11-08-t109-calendar-record-prompt.md).

A. В существующем ответе `GET /api/v1/desktop/calendar/upcoming` различать
состояние подключения и состояние записи. Допустимые значения для показа:
`not_due` и `shown`. Отсутствующее состояние, `null` или неизвестное
значение не дают подсказку. При разрешающем состоянии отсутствующий/null
`record_prompt_due_at` означает начало встречи; невалидное время не даёт
подсказку. Ошибка этих необязательных полей не портит карточку, меню или
остальной корректный снимок. Чистый выбор возвращает только активные
события в текущем полном снимке: `max(startsAt, dueAt) <= now < endsAt`,
без требования к ссылке, с устойчивой сортировкой по началу и UUID.
Полный снимок — исходный принятый ответ текущего владельца/пространства,
до клиентского сокращения для повтора или меню. Это ограниченный ответ
API (до 50 событий), без обещания исчерпывающего списка. Он даёт подсказку,
только если Windows знает монотонное время запуска того запроса и возраст
запроса в момент выбора находится в `[0, 60 с)` (два обычных интервала
опроса по 30 с). Поздний ответ не омолаживается временем доставки;
зависание отзывает подсказку на границе 60 с. Время встречи по-прежнему
сверяется по часам UTC. Ошибка обновления, явное сокращение, сброс scope
или блокировка немедленно отзывают право подсказки; новый принятый
исходный ответ из текущего scope может её восстановить. В A модель
получает метку от вызывающего кода и покрывается искусственными часами;
B подключает метку запуска из существующего нативного полёта. Старые
потребители могут не передавать её: это не делает их источником подсказок.
Невалидное время или текущая запись не дают кандидатов. Отдельного
запроса из WebView нет. Этот срез не меняет сроки или удержание F277 и
не включает кнопку записи.

B. В нативной панели повторить отдельный блок Mac; одна встреча → автоматический
контекст, пересечение → выбор события или отказ от контекста. Идентичность
действия включает поколение сеанса, полный набор актуальных вариантов,
время и выбранный UUID; после свежего ответа и после каждой точки, в которой
возможно повторное открытие UI, сверять прежнее действие. После потери
права старый callback не возрождается. Существующий `recordCapture` и
`NativeCapture::record` с StartGuard — единственные пути начала; контекст не
открывает ссылку и не ослабляет допуск звука, индикатор, Stop или хранилище.

Серверный путь Mac: после фактического начала, по локальному ID и исходному
времени записи, `POST /api/v1/desktop/recordings/{local_recording_id}/calendar-context/resolve`
с `Idempotency-Key: desktop-calendar-context-resolve:{local_recording_id}`.
Контракт `calendar_auto_context_v1` различает `automatic` (без UUID),
`user_selected` (один текущий UUID) и `user_declined` (без UUID).
В `POST /api/v1/meetings` существующее поле `calendar_match_attempt_id`
передаёт подтверждённый ID попытки для той же записи. Смена аккаунта не
передаёт попытку другой записи/владельцу; отказ выбора не превращается в
`automatic`. Перед кодом B отдельно проверить, где сохранить решение и
результат в защищённом состоянии, включая Stop до ответа, перезапуск и
повтор отправки с тем же ключом. Сбой календаря не теряет звук, не меняет
выбор и не допускает повторную запись; без подмены решения старой попыткой.
API, WebView, сервер и Mac в A и B менять не требуется.

Независимый контроль требований/анализа до A; отдельная проверка решений
панели, StartGuard и защищённого сохранения до B. После A — RED→GREEN
портативного контракта и модели. После B — сравнение экранов и проверка
синтетического сквозного сценария в точном MSIX, включая фактическое
сопоставление встречи, отказ от него и доступность. См. quickstart.

**Точки подключения B, сверка с установленным GRAF Dev 73fdf67f.**
`AppMain.cpp::refreshMeetingReminders` уже связывает запрос с поколением
входа, владельцем и пространством, но передаёт в `MeetingReminderModel::update`
только снимок и epoch. `recordCandidates` пока вызывают только тесты.
Для B запоминать монотонную метку на старте именно этого нативного запроса,
передавать её вместе с подтверждённым снимком; не подменять её временем
доставки ответа или меткой следующего запроса. Переиспользовать текущий
опрос и закрывать возможность действия при отзыве его контекста. Прежде
чем показывать действие в панели, принять защищённое сохранение решения
и совместимую отправку по B2c. Простое подключение кнопки к
`recordCapture()` начнёт обычную запись, но не докажет выбранный
календарный контекст; это не реализация B.

Нативная панель Mac даёт подсказке записи приоритет перед подсказкой
подключения к предстоящей встрече. Сравнить конфликт двух событий
отдельно от карточки F277: после начала подходящей встречи при выключенном
подключении должна остаться подсказка записи; при нескольких активных
встречах должны быть выбор встречи и запись без привязки. Если допустимой
подсказки записи нет, перед началом другой встречи с проверенной ссылкой
Mac может предложить подключение в панели. Это отдельная поверхность,
действие подключения переиспользует T119. Зафиксировать результат
сравнения и отличие от фоновой карточки, не выводить одно из другого.

#### T104/B1: контракт календарного решения и создания встречи

До подключения кнопки и хранения: в `DesktopApiClient` использовать
действующий контракт сервера и обычный/защищённый тип строки. Собрать
один неизменный запрос из UUID локальной записи, фактического UTC
начала (секунды, как ISO-8601 у Mac) и решения. Локальный UUID и UUID
выбранного события должны быть ненулевыми и каноническими; событие
присутствует только для `user_selected`. Не передавать имя, ссылку,
учётные данные или новый ключ на повторе. Полученный ответ ограничен
до 8192 байт перед JSON-разбором. Извлекать только ненулевой UUID
попытки и положительный срок UTC в формате существующего
`calendarInstant` (зона обязательна, дробные секунды допустимы).
`matched_user` соответствует выбору, `declined_by_user` — отказу.
Для `automatic` допустимы `matched_auto`, `provisional_prestart`,
`ambiguous`, `no_context`, `skipped_private`, `skipped_all_day`,
`skipped_stale_calendar`, `calendar_unavailable`. Ошибка, дубль поля
или неподходящее состояние не возвращают попытку. Не привязывать данные из ответа к
другому HTTP-запросу, владельцу или записи: это обязанность
следующего среза на границе защищённой очереди и отправки.
`createMeetingRequest` принимает необязательный, строго проверенный
UUID попытки. Без него байты прежнего запроса не меняются. Подключение
HTTP, сравнение срока до первого запроса создания, закрепление тела
для повтора и жизненный цикл sidecar требуют отдельного допуска.

#### T104/B2: где закрепить решение — кандидат к ревью

Аудит прежнего формата исключает добавление ключа в v4 queue row:
`decodeQueueLedger` проверяет точный набор ключей, поэтому пакет до
B2 перестанет открывать такую очередь. Новый файл в каталоге самой
записи тоже требует изменения ожидаемого состава защищённого пакета.
Оба формата сохраняются. Кандидат — отдельный журнал метаданных в
локальном каталоге GRAF вне дерева записей, зашифрованный DPAPI текущего
пользователя, без названий и ссылок. Это проектное решение, до записи
в журнал нужны отдельная проверка конструкции и тесты.

- В существующем потоке подготовки резервирование владельца и запись
  решения в журнал относятся к одному UUID. При явном выборе событие
  должно быть сохранено до допуска звука; при ошибке допуска нет, обычная
  кнопка ручной записи остаётся доступна. Подготовка без допуска не даёт
  сетевой записи. StartGuard привязывается к своему session ID и допускает
  только его собственное состояние `starting`; повторная проверка учитывает
  взаимодействие с ОС, контекст, снимок календаря и готовность Stop.
- Время запроса привязки закрепляется один раз по доказанному началу,
  а не по времени нажатия, подготовки, Stop или повтора. Проверить
  текущий `V5LocalRecordingWriter::append` (метка первой записанной
  рамки) и восстановление по защищённому манифесту; одного индикатора
  `starting` для сетевого POST недостаточно.
- Перед созданием встречи закрепить неизменяемый выбор тела с тем же
  ID попытки или явным отсутствием ID. Если ответ создания потерян,
  сначала штатная сверка sync-state; неизменившийся ID записи не
  позволяет заново выбирать тело. После истечения серверной попытки
  нельзя заменить уже отправленный ID новым. Неподходящие
  owner/workspace/origin, потерянный ответ, повреждённое или чужое
  содержимое журнала не дают связать другую запись. Штатный сбой
  календаря не уничтожает аудио и не заменяет отказ на автоматический выбор.
- Очистка проверяется вместе с окончанием, короткой записью, локальным
  удалением и восстановлением. До подтверждения старым пакетом
  проверять отдельно чтение очереди/воспроизведение и судьбу ожидающего
  календарного решения: старый клиент может прочитать неизменённый
  формат очереди, но не знает про журнал и может начать создание встречи
  без поля попытки. Не заявлять безопасный откат с ожидающими решениями
  без явной проверенной процедуры (или совместимой базовой сборки).

##### T104/B2a: неизменяемый локальный выбор

Первое значение закрепляется только для канонического ненулевого UUID
записи, выделенного владельцем очереди. Корень берётся из того же
локального каталога GRAF, что и `localCustodyRoot()`, но файл находится
в соседнем частном каталоге `calendar-match` вне дерева `recordings`.
Внешний ввод не определяет путь. Открытие каталога и файла должно
удерживать проверенные дескрипторы и не следовать через ссылки Windows;
одно вычисление канонического пути не защищает от подмены между
проверкой и открытием.

Конверт DPAPI текущего пользователя (не более 4 КиБ) использует
версию 1 и отдельную область шифрования; аутентифицированные данные
однозначно связываются с точными origin, actor, workspace и UUID записи.
Данные решения содержат только код одного из трёх вариантов и UUID
события только для явного выбора. Внутри DPAPI также находятся версия
формата и SHA-256 данных: отдельная проверка отклоняет повреждённый
результат, даже если операция Windows вернула успех. Буферы открытых
данных очищаются.
При открытии владельца сначала подготавливается частный каталог
журнала. Создание корня GRAF и каталога подтверждается сбросом их
буферов и буферов родителя GRAF. Неподтверждённая подготовка блокирует
использование журнала. Публикация первой версии: частный временный файл,
запись и сброс буферов, затем атомарное перемещение без замены и сброс
буферов удерживаемого каталога журнала. Ошибка сброса после перемещения
означает неподтверждённую публикацию; файл не удаляется и не заменяется.
Идемпотентный повтор сверяет файл и повторяет сброс каталога. Чтение
решения перед использованием также сбрасывает этот каталог.

Отсутствие записи определяется только точным результатом открытия файла
относительно подготовленного частного каталога. Неудачная подготовка
каталога и иная ошибка открытия не означают пустой журнал. Код, версия, форма или размер вне
контракта — недопустимое содержимое. Ошибка аутентификации DPAPI
единая для повреждённого шифротекста и чужого контекста/пользователя:
по такому результату нельзя судить, что именно произошло. Непохожее
проверенное решение — конфликт; подмена пути, запрет доступа или
иной сбой ввода-вывода блокируют использование. Ни один из этих
отказов не превращается в отсутствие или автоматический выбор.

Проверки: чтение новым процессом в том же тестовом профиле, повтор
и конфликт, копирование конверта между UUID и несовпадение каждого
из компонентов контекста, обрезанный конверт, подмена файла или
каталога ссылкой, неизменность первого выбора после отказа. Подключение
к началу записи, журналирование попытки серверного сопоставления,
очистка и откат — следующие срезы того же T104, ни один из них не
принимается проверкой B2a.

##### T104/B2b: передача выбора через допуск записи

Явное решение панели передаётся как владеющее значением в существующий
`RecordingWork`. Не использовать предикат `recordCapture(current)` как
длительный допуск: сейчас он действует только до `capture_->record()`.
Не переиспользовать объект передачи из «Войти и записать»: он снимается
при возврате из обработчика. Привязать отдельное одноразовое действие
панели через `StartGuardFactory` после возможной замены конвейера и
до передачи задания рабочему потоку.

Точка записи журнала — существующее продолжение рабочего потока
`StorageCommand::prepareRecording` после долговечного резервирования и
подтверждения приёма результата основным потоком, непосредственно перед
`V5LocalRecordingWriter::open`. Сопоставить UUID, владельца и рабочее
пространство с проверенной строкой `capture_prepared`; одного статуса
строки недостаточно для вошедшего владельца. Origin брать из настройки
захвата, проверять равенство origin привязанного действия. Ввод-вывод
выполнять без удержания мьютексов хранилища и записи. Только
`committed` допускает открытие writer; после вызова повторить проверку
отмены. Ошибка не запускает обычную запись автоматически. Stop во
время сохранения может оставить решение только у старого UUID, но
не даёт стартовать; жизненный цикл таких решений принимается отдельно.

Финальный допуск остаётся в `pollHealth` до `acceptingBatches`: та же
попытка в собственном состоянии `starting`, действующие аккаунт и
рабочее пространство (в том числе после возможного сброса аккаунта
без смены поколения), свежий и подходящий снимок событий, актуальная
проверка взаимодействия с ОС и доступный Stop. Отзыв одноразовый,
старый обработчик не может восстановить своё право. Путь записи
без календарной подсказки сохраняет прежнее поведение. В срезе B2b новое
действие панели недоступно пользователю. Открывать его в пользовательской
сборке только после сквозной проверки, что отправка читает и соблюдает
сохранённое решение для той же записи.

Проверки удерживают рабочий поток непосредственно перед подтверждением
журнала и отдельно последнее подтверждение готовности звукового
устройства. В первой точке UI и Stop остаются доступны; ошибка
журнала не открывает writer и не запускает WASAPI. Во второй точке
отмена, смена или потеря контекста и устаревание события не допускают
ни одного пакета. Положительный сценарий допускает ровно один старт
своей попытки. Кнопку панели и дальнейшую отправку проверять сквозным
сценарием после подключения обоих путей.

Интеграционный результат: активный владелец защищённой очереди удерживает
предков `recordings` с `FILE_SHARE_READ`. Повторное открытие родителя
GRAF для сброса даёт ошибку Windows 32; сброс дескриптора без права
записи даёт 5. Сохранить ограничения владельца. До его открытия рабочий
поток подготавливает отдельный частный каталог журнала, подтверждает
сброс дочернего каталога, GRAF и его родителя, затем освобождает дескрипторы с правами записи для
предков. Сам каталог журнала удерживается без разрешения на удаление,
а его предки — с доступом чтения и без разрешения на удаление. При
сохранении и чтении решения сбрасывается этот уже подтверждённый
каталог, без повторного открытия предка с правом записи. Без
подтверждённого каталога выбор встречи недоступен, обычная запись
продолжает работать по прежним условиям.

##### T104/B2c: подтверждение выбора при отправке — границы следующего среза

Проверка действующего потока выявила две границы перед подключением панели:

1. Обычное завершение и восстановление защищённой записи могут перевести
   резервирование в обычную ожидающую отправку. Требование явного решения
   должно пережить этот переход независимо от файла журнала. Иначе
   потерянный файл неотличим от обычной записи. Старый декодер требует
   точный набор ключей очереди v4. До изменения формата проверить, можно
   ли сохранить признак через существующее закрытое состояние, которое
   текущий и предыдущий MSIX не могут отправить ни автоматически, ни
   вручную. Подтвердить это на завершении, восстановлении после сбоя,
   ручном повторе, удалении и откате. При отсутствии такого состояния
   нужен отдельно согласованный переход формата; действие панели остаётся
   закрытым. Проверенная обычная запись сохраняет прежний путь.
2. Создание встречи сейчас может вернуть успех даже при просроченной
   попытке сопоставления: сервер оставляет календарь без подтверждённого
   выбора, а ответ проверки состояния записи не сообщает, была ли
   применена эта попытка. Наличие встречи или успешная загрузка звука
   не доказывают применение выбора. Действующий
   `GET /api/v1/meetings/{meeting_id}/calendar-context` даёт событие,
   состояние и источник решения, но показывает текущий изменяемый
   контекст, без UUID использованной попытки. Он годится для проверки
   итогового пользовательского результата, а не для доказательства
   принятия исходного запроса после потери ответа. Для подтверждения
   сначала проверить существующую запись попытки: сервер уже связывает
   принятую попытку с UUID встречи и временем применения, сохраняет
   эту связь после очистки снимка и удаляет вместе с данными встречи.
   Кандидат — отдавать только факт принятия UUID попытки в существующем
   ответе проверки состояния для исходного владельца, устройства и
   записи, без раскрытия снимка календаря и без нового журнала на сервере.
   Отдельно уточнить обработку истечения срока при принятии запроса,
   сохранив совместимость уже установленных клиентов.

Для явного выбора и отказа клиент сначала проверяет состояние записи.
Если встречи ещё нет, он разрешает ровно одно решение из журнала для
текущего владельца и закрепляет UUID попытки, ключ идемпотентности и
точное тело создания (или версию данных, воспроизводящую те же байты)
до отправки запроса. При неопределённом результате сначала сверяет
состояние на сервере. Допустимый повтор использует те же тело и ключ.
Истёкшая попытка не разрешает убрать UUID, заменить его или выбрать
событие автоматически. Неподтверждённый исход сохраняет локальный звук
и требует отдельной обработки. Критерии следующего среза: потеря или
повреждение журнала, перезапуск после закрепления запроса, потеря ответа
до и после создания, истечение срока на клиенте и сервере, откат на
предыдущий пакет и подтверждение итогового календарного результата.

###### T104/B2c.1: подтверждение принятой попытки в сверке записи

Срез с повышенным риском (сверка загрузки и доступ к данным аккаунта).
В существующий `GET /api/v1/desktop/recordings/{local_recording_id}/sync-state`
добавить необязательный параметр `include_calendar_match_receipt=true`.
Без него прежний JSON и запросы к хранилищу сохраняются. При запросе
ответ может содержать `calendar_match_receipt: {attempt_id, state}`,
где `state` — только `matched_user` или `declined_by_user`. Отсутствующее
подтверждение означает «не доказано». Оно не даёт права заменить выбор
или повторить создание с изменёнными данными.

Единственный источник — уже принятая строка
`RecordingCalendarMatchAttempt`: точные workspace, пользователь,
устройство, локальный UUID, UUID встречи, положительный момент принятия
и согласованная пара intent/state. Встреча должна принадлежать тому же
устройству; при несовпадении ревизии, отзыве доступа, удалении или
отсутствии БД поле не возвращается. Состояние upload-session, в том числе
её истечение, не меняет уже доказанное принятие. При отсутствии строки,
истечении **до** принятия, другом устройстве или несовпадении области
значение не возвращается; текущее состояние карточки не подменяет
доказательство. Не читать и не возвращать снимок календаря. Запрос
с включённым подтверждением получает `Cache-Control: no-store`.

Подтверждение проверяется после потери ответа на создание, в том числе
после истечения срока **уже принятой** попытки; TTL ограничивает
принятие, а не возможность проверить ранее принятое решение. Отдельно
сверить старый запрос, непринятую попытку, подмену устройства, ревизии и
удаление. Эта поставка меняет локальные исходники API и тесты, не
меняет поведение создания, Mac, серверную схему или рабочий сервер.
Строгое создание, защита локального признака и подключение интерфейса
остаются условиями полного B2c/T104.

###### T104/B2c.2: ограничение совместимости для строгого создания

Существующий `POST /api/v1/meetings` сохраняет запасной исход для
старых клиентов. Текущая схема отклоняет неизвестные поля, но защита
от отката не должна зависеть от правил разбора тела в прежней версии.
Использовать отдельный `POST /api/v1/desktop/meetings/with-calendar-context`
с прежней схемой создания и обязательным UUID календарной попытки.
Отсутствие маршрута (404/405) или отказ не разрешают Windows повторить
отправку через обычное создание. До подключения клиента этот запрет
проверяется как требование, а не как работающий механизм Windows.

Общий путь ingest проверяет авторизацию и блокирует источник записи.
Строгое создание сверяет владельца, пространство, устройство, запись
и время начала (тот же UTC-момент, который Windows отправил при
сопоставлении). Применимы только явный выбор с тем же сохранённым
событием либо явный отказ без события. Отсутствующая, чужая, уже
потреблённая или просроченная попытка и автоматический исход не дают
запасного результата. Срок проверяется после блокировки строки
попытки. После ожидания блокировок обе ветки заново проверяют доступ
пользователя, членство, устройство и привязку действующей сессии. Создание встречи, начальной ревизии, записи обработки,
применение попытки и аудит фиксируются вместе; при отказе не остаётся
следов ни в базе, ни в памяти процесса.

При повторе требуются исходный отпечаток тела, та же актуальная
ревизия и точная попытка, принятая до истечения срока именно этой
встречей. Текущий контекст карточки не является доказательством.
Повтор не применяет решение вновь и может подтвердить его после TTL.
Удаление блокирует обе ветки. Встреча без точного подтверждения
не меняется. Старый маршрут, macOS и схема базы не меняются.


###### T104/B2c.3: признак явного решения в защищённой очереди

Использовать прежнюю схему v4: `quarantined` с безопасными причинами
`capture_calendar_prepared` до завершения и `calendar_match_required`
после подтверждённого обычного завершения или восстановления.
Первая метка записывается в резервирование до открытия записи звука;
смысл обеих — отправку нельзя начать без явного решения. Поля календаря
остаются в отдельном защищённом журнале. Причины принимаются только
с владельцем, одним UUID записи/каталога/сессии и без попыток, диапазонов
или статуса серверной отправки. UUID встречи, добавленный старым
читателем при принятом удалении, не даёт права на отправку. Только
совпадающие задание и принятая квитанция того же сервера, владельца
и рабочего пространства позволяют записать намерение
`calendar_server_purge_pending` без выхода из карантина. Оно не
возобновляется как обычное локальное удаление: после прерывания нужно
продолжить то же серверное задание и подтвердить отсутствие пакета
и запись результата в очереди. Неизвестный или отсутствующий журнал
не открывает отправку; правила короткой записи остаются прежними. Обе метки обязательны для `user_selected` и
`user_declined`. Для этих двух решений допуск журнала B2b ожидает
`capture_calendar_prepared` вместо `capture_prepared`, с прежними
проверками UUID, владельца, рабочего пространства и origin. Обычная
запись и автоматическое сопоставление не получают новые метки.

Штатное восстановление переводит запись с первой меткой во вторую
только для проверенного `sealedNormal`, вместо обычного pending.
Отсутствующий каталог, незапечатанный и восстановленный
`sealedDegraded` не меняют первую метку и не открывают отправку. Подтверждённое воспроизведение
и удаление владельцем остаются доступны по действующим проверкам
пакета и доступа. Старый читатель принимает форму v4 и не отправляет
такие quarantined строки. Это не означает, что профиль можно откатить:
0.1.0.18 не знает `calendar_server_purge_pending`. Перед удалением
он может убрать запись как обычную локальную копию без подтверждения
серверу; после удаления и до фиксации результата он может отказать
в открытии всей очереди. Для включения панели нужна подтверждённая
базовая версия отката, которая сохраняет эти ограничения и завершает
то же задание по обе стороны удаления. Проверить точные установленные
пакеты с искусственными профилями; 0.1.0.18 не считать безопасным
откатом для такого профиля. Пока не пройдены эта проверка и строгая
отправка через B2c.1/B2c.2, пользовательский вход закрыт.

###### T104/B2c.4: проверка подтверждения на стороне Windows

После потери ответа Windows должен различить три исхода: точное
подтверждение выбора или отказа; точный ответ сервера, что записи нет
в запрошенной области; отсутствие доказательства. В этом срезе
проверяется разбор ответа; следующий срез привязывает его к запросу
B2c.1 в подтверждённой сессии того же сервера, аккаунта, пространства и
устройства. Сам разбор не даёт разрешения создать встречу, повторить
POST, открыть очередь или удалить запись.

Подтверждение — только полностью полученный HTTP 200 и ограниченный
корректный JSON без повторов ключей, включая их экранированные варианты.
Сверить локальный UUID записи, обе проекции точного локального ID
ревизии, UUID встречи (включая ранее известный, если он есть), явные
`access_state=owner` и `deletion_state=none`. Исключить состояние
удалённой ревизии и конфликт идентичности, доступа, удаления или
ревизии. При точной квитанции допустимы только `none`,
`upload_session_expired`, `processing_failed`, `processing_blocked`,
а также `dependency_unavailable` с причиной
`sync_state_dependency_unavailable` или `upload_session_unavailable`.
Вариант `meeting_unavailable`, отсутствующая или другая причина при
`dependency_unavailable`, отсутствующее или неизвестное состояние
означают «не доказано». Обязательны UUID попытки и точная пара:
`user_selected → matched_user` или `user_declined → declined_by_user`.
Результат отдаёт только проверенный UUID встречи. Полный HTTP 404
с корневым `code=recording_not_found` отличим от ответа старого
маршрутизатора, но сам по себе не разрешает создание. Остальные ответы,
сбой транспорта, отмена, отсутствие или `null` в квитанции означают
«не доказано». Тело не сохраняется и не журналируется; поведение
обычной загрузки и пользовательского интерфейса не меняется.

###### T104/B2c.5: запрос подтверждения в исходной области

Высокий риск: авторизованный запрос из защищённого фонового потока.
Принимать только исходную область уже выделенной попытки: HTTPS origin,
UUID владельца, рабочего пространства, устройства, записи и попытки,
точный локальный ID ревизии и ожидаемый явный исход. Если UUID встречи
уже известен, передать его в B2c.4. До сети сверить origin, владельца и
пространство с конфигурацией и подтверждённым снимком текущего токена,
а устройство — с явно передаваемым UUID устройства. Нужен токен, связанный
с этим снимком, и маркер отмены его поколения. Не восстанавливать область
из ответа, из других аккаунтов или только из наличия токена.

Отправить только один защищённый GET на
`/api/v1/desktop/recordings/{uuid}/sync-state?local_media_revision_id={id}&include_calendar_match_receipt=true`
с ожидаемыми заголовками актёра и пространства, явным `X-Device-Id`
и штатной проверкой сессии и устройства сервером. Не использовать
перенаправления, cookies, кэширование запроса, запасной адрес или
POST. Использовать исходный срок фоновой операции, ограниченный
сверху 15 с от входа, и общий предел JSON 2 МиБ с проверкой конца тела.
Отмена, истечение срока, исключение или неполный ответ не подтверждают
ни решение, ни отсутствие записи. Проверить срок и отмену после
возврата сети и после разбора. Запрос и ответ остаются в защищённых
буферах; результат B2c.4 не даёт прав очереди или удаления.

Первый потребитель — следующий срез строгого повтора с сохранённой
попыткой, исходным телом/ключом и подтверждённым устройством. До него
не запускать этот путь из обычной очереди, не менять вход в приложение,
календарную панель или сервер.

###### T104/B2c.6: подтверждённое устройство текущего токена

Высокий риск, общий контракт входа. Добавить необязательный
`active_session_device_id` в существующий `GET /api/v1/auth/me`.
Он возвращается без кэширования только для активной сессии того же
владельца и пространства, когда проверенный сервером principal
содержит однозначное доверенное устройство этой сессии. Не брать ID
из заголовка, списка зарегистрированных устройств, выбора платформы
или просто из непроверенной строки устройства. У сессии без устройства,
legacy-запроса или неподтверждённой привязки поля нет; действующие
отказы для отозванного и заблокированного устройства сохраняются.
Поля старого ответа, схема БД и код Mac не меняются.

Windows принимает только канонический ненулевой UUID из точного
поля при уже валидных аккаунте, пространстве и сессии. Отсутствие,
`null` или непригодное значение отключает календарную сверку; обычный
вход и загрузка остаются доступны. Сохранить UUID только в снимке
того же токена/поколения, который уже использует Windows. Сброс
снимка и отмена при смене токена остаются существующими. Перед
календарным GET сверить подтверждённое устройство с исходной попыткой
и явным заголовком; не включать новый заголовок для обычной загрузки.
Не сохранять этот сетевой снимок в журнале и не включать панель;
сохранение исходной области конкретной попытки и строгий POST —
следующий срез.

###### T104/B2c.7: неизменяемый запрос создания после перезапуска

Перед первым строгим POST закрепить в закрытом локальном журнале
один пакет запроса: UUID попытки, срок UTC в миллисекундах (округлять
вниз), точные байты тела и ключ идемпотентности. Строить их штатным
формирователем создания из границ запечатанной записи, явной попытки
и исходной ревизии; без корректной шкалы времени запрос не готовить.
Использовать отдельный ключ для строгого маршрута. Токен и ответы
сервера целиком не сохранять.

Оставить файл и двоичный формат решения v1 побайтно неизменными.
Второй файл `<uuid>.create` имеет собственные версию и домен DPAPI,
границы длины тела, ключа и конверта и независимую проверку дайджеста.
Открывать файл относительно того же удерживаемого каталога с теми же
проверками частного объекта и ACL, атомарным созданием без замены
и подтверждением записи на диск. Привязать шифрование DPAPI
к origin, владельцу, пространству, записи, подтверждённому устройству,
ревизии и точному сохранённому решению (включая выбранное событие).
И чтение, и запись требуют подтверждённого исходного файла решения.
После публикации совпадающий запрос принимается без перезаписи;
иной запрос, повреждение, чужая область и неопределённая публикация
не дают пригодного запроса. Чтение возвращает исходные байты без
повторной генерации. Истёкшая попытка остаётся доступной для сверки
квитанции; разрешение первого POST/повтора по времени — обязанность
будущего потребителя, не журнала. Не подключать сетевой вызов или
панель до проверки обработки отсутствующего журнала, срока, удаления
обоих файлов и сценариев восстановления/отката.
Перед первым POST потребитель должен устойчиво отметить в защищённой
очереди, что пакет попытки уже обязателен. Если после этой границы
файл отсутствует, не разрешать новую попытку: это может быть потеря
файла после успешного POST. И чтение, и публикацию обоих файлов
согласовать с удалением и снимком авторизации на одном владельце очереди.

###### T104/B2c.8: очередь помнит закреплённую попытку

В защищённой очереди v4 добавить закрытую причину
`calendar_replay_required` без изменения схемы. Переход только из
`calendar_match_required` по свежей строке того же владельца,
пространства и записи, без подтверждённой встречи, запрета доступа или
удаления. Проверка ожидаемого поколения и отмены выполняется тем же
владельцем защищённой очереди. Сначала подтвердить пакет в журнале,
потом подготовить закрытую копию очереди; до отдельного подтверждения
записи и перечитывания очередь не отдаёт пакет на отправку. После
сбоя между журналом и очередью можно закрепить только тот же пакет
или принять уже подтверждённый пакет без нового разрешения выбора.
У закреплённой строки отсутствующий/испорченный журнал не заменять
даже при наличии нового ответа разрешения. Никакого обычного POST,
автоматической или ручной отправки и применения старого результата.
После обращения к журналу повторно проверить отмену и сохранённое
поколение с правом исходной строки, прежде чем вернуть частную копию
или тело и ключ. При неопределённой записи очереди этот владелец
не выдаёт пакет. Новый владелец признаёт только перечитанное поколение:
старое не даёт запроса, новое открывает только исходный пакет.

Оба состояния сохраняют существующие проверенные локальный просмотр и
удаление. Переход в ожидающее подтверждённое серверное удаление
сохраняет запрет отправки. Проверить точный откат отдельно: прежний
сборщик может открыть неизвестную причину как карантин, но это не
доказывает прежний просмотр/удаление и не разрешает выпуск. В этом
срезе провести тесты границы подготовки/чтения в существующем
владельце, без вызова сети или показа панели. До подключения строгого
POST остаются отмена по живому поколению и согласованное удаление
файлов журнала в полном потоке.


###### T104/B2c.9: строгий POST и подтверждение потерянного ответа

Сетевой исполнитель получает только исходный пакет, прочитанный владельцем
подтверждённого поколения B2c.8, и ту же область попытки. Подключение
владельца очереди, доказательство запечатанного аудио и удаление журнала
остаются обязательными до запуска из продукта. Не менять обычную
отправку, сервер, очередь, панель и Mac в этом сетевом срезе.

Сначала выполнить B2c.5 в исходной области, со сроком всей операции не
более 15 секунд. Точная квитанция завершает сверку даже после истечения
попытки. Только точный `recording_not_found` без известного UUID встречи
позволяет один POST на `/api/v1/desktop/meetings/with-calendar-context`.
Непосредственно перед `WinHttpSendRequest`, после настройки
соединения, заголовков и таймаутов, повторно проверить отмену,
монотонный срок операции и сохранённый UTC-срок попытки. При
`nowUtc >= expiresAt` POST не вызывается. Просроченный пакет можно
сверять; сервер отдельно проверяет срок применения попытки.
Использовать только исходное тело и исходный ключ, сверенный с областью
записи и UUID попытки; учётные данные и заголовки области совпадают с GET.
Никаких перенаправлений, cookies, повторного разрешения или запасного POST.

После попытки POST, включая потерю ответа или исключение транспорта,
выполнить не более одного GET в той же области в остатке исходного срока.
Ответ POST, в том числе 2xx, не подтверждает решение. Отдать только
точную квитанцию B2c.5; иной ответ, отмена или истечение срока оставляют
запись без разрешения продолжать отправку. Повтор операции после
перезапуска начинается с той же сверки и того же сохранённого пакета.


###### T104/B2c.10: подтверждённая встреча в закрытой очереди

Не переводить подтверждённую календарную запись в обычное `pending`:
при 404 обычная отправка может создать встречу без исходного решения.
В существующей схеме v4 хранить UUID встречи из точной квитанции в
`meetingId` и новую закрытую причину `calendar_receipt_confirmed`.
Запись остаётся в карантине; UUID обязателен и сам по себе не разрешает
передачу аудио или очистку. Сохранить текущие условия просмотра и
удаления, в том числе согласованное серверное удаление. Точное
совместимое поведение при установленном откате остаётся открытым.

Владелец готовит частную копию только из перечитанной
`calendar_replay_required` текущего поколения. Требуются та же
проверенная сессия, исходная область с явным устройством, точный
подтверждённый UUID, исходное решение и точное совпадение пакета
(попытка, тело, ключ, срок) при новом чтении журнала. Подтверждение несёт область запроса,
закреплённую самим защищённым GET; результат голого разбора
JSON или ответ от другой сессии не подходит. Заново проверить
защищённые метаданные именно пакета этой строки и допустить только
`sealedNormal`. Отсутствие, повреждение, чужая идентичность или
`sealedDegraded` не разрешают кандидат. Проверить доступ и удаление,
включая удаление, нацеленное на UUID встречи из квитанции, пока его нет
в строке. Проверить отмену и поколение после чтения журнала, пакета и
подготовки копии. Не выдавать новую строку за сохранённую до штатного
коммита очереди; старое поколение не содержит UUID, новое содержит
ровно подтверждённый. Не повторять POST из новой закрытой строки.
До подключения из продукта нужны отдельный путь загрузки для той же
встречи, сверка и очистка журнала в удалении; сетевых и UI-вызовов
из владельца этот срез не подключает.

###### T104/B2c.11: сеанс загрузки только для подтверждённой ревизии

Клиент сверяет закрытую строку и журнал с точной серверной квитанцией
и извлекает UUID серверной ревизии из того же ответа. Проверка UUID
после создания сеанса не предотвращает создание сеанса для другой
ревизии. Поэтому отдельный POST `/api/v1/desktop/meetings/{meeting_id}/upload-sessions`
переиспользует создание сеанса, но требует `expected_media_revision_id`
и `calendar_match_attempt_id`. Сервер под блокировкой встречи повторяет
проверку квитанции: ожидает то же устройство, активный доступ и принятое
явное решение исходной попытки для актуальной начальной ревизии
(номер 1, источник `initial_mixed_recording`). Без действующей авторизованной
сессии с привязкой к устройству строгий маршрут закрыт. Сеанс и аудит
не публикуются в памяти до подтверждения записи в БД.
Новая строка ревизии блокирует продолжение, когда становится актуальной.
Без базы строгий режим недоступен.
До создания нужен полный список уникальных ролей с одним
положительным размером на дорожку. Повтор с тем же ключом допускает
только действующий сеанс той же ревизии и устройства. Для чужой ревизии или устройства, истёкшего
или завершённого сеанса с тем же ключом сервер отказывает без возврата
или замены сеанса, изменения встречи и события создания. Отозванный
при ожидании блокировки доступ не допускает ни создания, ни повтора.
Прежний маршрут сохраняет контракт. Сервер без нового маршрута
возвращает 404, поэтому старый сервер не может
молча проигнорировать закрепление ревизии и создать сеанс.

Перед любым диапазоном, частью или завершением Windows проверяет
устройство через строгую серверную сверку сеанса и сверяет UUID сеанса,
встречи и ревизии, допустимое состояние, роли и размеры дорожек.
До запроса частная квитанция должна совпасть с независимо выбранной
строкой и её журналом, включая запись, локальную ревизию, исходную
попытку, решение и сохранённый UUID встречи. Пара квитанция–сеанс от
другой записи не проходит даже при тех же размерах дорожек.
Строгий GET `/api/v1/desktop/meetings/{meeting_id}/upload-sessions/{session_id}`
требует `expected_media_revision_id`. Одно чтение БД подтверждает, что
сеанс и исходная актуальная ревизия принадлежат той же встрече,
пространству, владельцу и устройству, доступ ещё действует, встреча
не удаляется, а сеанс допускает запись и не истёк. Успешный ответ
`Cache-Control: no-store` содержит только UUID, состояние, срок и
форму дорожек. Синтетическая ревизия старого сеанса или ответ из памяти
не подходит. Ответ не заменяет проверки на границе записи байтов.
После потери
ответа повтор начинается со свежей сверки. Нет запасного создания
встречи или перехода на обычную отправку. Параметр сам по себе не
разрешает аудио: проверка журнала, пакета, отмены, поколения и права
владельца остаётся обязательной. Изменения рабочего сервера проходят
отдельные ворота выпуска.

###### T104/B2c.12: допуск сеанса со стороны Windows

Из проверенной пары «закрытая строка + журнал» и свежей квитанции
клиент получает точную серверную ревизию. Строгий POST отправляет
исходную попытку, этот UUID и размеры трёх защищённых потоков.
Ключ `calendar-upload-session` выводится из UUID записи и попытки;
при потере ответа следующая отправка повторяет тот же запрос с тем
же ключом. UUID ответа POST — только кандидат: возвращать его
допускается после строгого GET с теми же ролями и размерами.
До POST действуют те же проверки области и токена, что и до GET.
Оба запроса используют один срок операции. Старый сервер, сбой
запроса, истёкший сеанс или неподтверждённый UUID не дают допуск.
Обычные пути создания встречи и сеанса не используются.

Этот шаг не активирует очередь и не отправляет байты. Замена
истёкшего сеанса, подтверждение завершения при потере ответа и
привязка к рабочему планировщику требуют отдельной проверки T104.

###### T104/B2c.13: календарный сеанс сохраняет ограничение при приёме частей

Сервер сохраняет UUID календарной попытки в отдельном nullable поле
строки upload session только при строгом создании. UUID нужен для
точного повторного POST и для различения строгого и обычного сеансов.
Старые строки остаются NULL и не подходят для строгой сверки; ключ
идемпотентности, параметры обычного POST и догадки по ревизии не
могут повысить такой сеанс до строгого. Календарная очистка не
удаляет ограничение, поэтому поле не ссылается на удаляемую попытку.

Для помеченного сеанса сервер до обращения к объектному хранилищу
и после него под существующими блокировками встречи и сеанса
перепроверяет строгий допуск: фактическую связь с начальной
ревизией, устройство, действующий доступ, срок и отсутствие
удаления. Это относится и к ответу о повторной части. Для нового объекта строгой части применяется журнал
и протокол B2c.14 ниже. При позднем отказе не принимать часть;
сохранить обязательство очистки точной попытки. Обычные загрузки
сохраняют прежний маршрут. Завершение загрузки и планировщик
в этом срезе не включаются; серверный выпуск требует отдельной
проверки миграции и совместимости отката.

Строгий повтор POST требует точного равенства сохранённой метки и
UUID принятой попытки запроса. NULL и другой UUID не допускают ни
возврата, ни подмены, ни создания сеанса. В режиме с БД для приёма
частей вид сеанса определяется только сохранённой строкой:
при отсутствии строки кэш не разрешает загрузку. Без доступной БД
помеченный сеанс закрыт. Обычный сеанс с подтверждённой строкой
не получает дополнительных календарных условий.

Быстрый идемпотентный повтор части и повтор после конкурентной записи
требуют свежего допуска под блокировками Meeting → UploadSession.
При отказе ранее принятую часть не менять, пробный объект очищать
только если он был создан текущим запросом.

###### T104/B2c.14: допуск при завершении календарной загрузки

Использовать сохранённую метку и ту же проверку, что при приёме
частей. Для помеченного сеанса требуется допуск до чтения объектов,
а затем свежий допуск под действующими блокировками: Meeting →
MediaRevision → UploadSession перед успешным завершением и
Meeting → UploadSession перед записью DEGRADED. Сверять исходную
метку и ревизию с текущей строкой, без подстановки из кэша.
При отказе не менять встречу, сеанс, ревизию, производные задания
или аудит завершения/ошибки; ранее принятые части остаются на месте.

Для нового объекта строгого сеанса (входящая часть B2c.13 и
составная дорожка B2c.14b) использовать существующий `PurgeJournal` с
отдельным классом записи и уникальным ключом каждой попытки.
Под существующим префиксом встречи защищены ровно два семейства:
`artifacts/media-revisions/<revision>/attempts/<epoch>/<attempt>/tracks/<role>`
и `sessions/<session>/tracks/<role>/parts/<part>/calendar-attempts/<epoch>/<attempt>`.
У составной дорожки после роли суффикса нет. Оба семейства одинаково
ограничивают роли записи, очистки и старых клиентов. Обычная загрузка и путь B2c.14a, где каждая
дорожка уже представлена одной принятой частью, сохраняют свои ключи и I/O.

Ключ каждой новой попытки должен быть гарантированно свежим даже после
восстановления. На закреплённом MinIO условие Complete защищает читаемый
занятый ключ, но не доказывает, что ключ действительно свободен: прежние
метаданные могут не читаться, а операция продолжится. HEAD 404, ошибка
кворума и пустой список не дают права повторно использовать ключ.
До подтверждения этой границы строгий писатель выключен.

Если выпуск оборвался после активации, путь восстановления определён в
[плане исполнения](release-execution-plan.md#следующий-срез-t104-восстановление-выпуском-с-исправлением).
Выпуск с исправлением наследует обычный допуск по `go`, точному SHA и
авторитетному Full CI. Журнал запуска и подтверждение остановки связаны
с активной попыткой и общим замком. Копия перед переходом обязательна
для каждого кандидата. Приёмка требует полной готовности служб и
публичного установщика, а не только запуска контейнеров.

- До выдачи прав записи однократно и необратимо выделить номер поколения
  `epoch` из долговечного журнала эксплуатации вне восстанавливаемых
  PostgreSQL, MinIO и комплекта развёртывания. Выдача атомарна и привязана
  к истории БД, месту хранения и активации писателя. Выданный или
  неоднозначно выделенный номер не переиспользовать. Если непрерывность
  журнала не подтверждена, новое поколение не открывать и не
  восстанавливать номер по S3 или старой БД.
- В активной истории БД номера попыток выдаёт одна последовательность
  `NO CYCLE` без права сброса у приложения. Подтвердить выделение номера
  и точный ключ в `PurgeJournal` до любого запроса в хранилище. Допуск
  к Complete требует совпадения с активным поколением, точным ключом
  и этой единственной попыткой; сомнение закрывает запись. Подписанное
  условие Complete остаётся дополнительной защитой.
- Право записи ограничено обоими семействами ключей конкретного активного
  поколения; обычные роли и старые экземпляры не могут писать туда.
  Эксплуатационные операции, которые могут писать в эту область или
  менять правила доступа, включая восстановление, запрещены одновременно
  с активным писателем. При смене истории БД, восстановлении, откате или
  неизвестном состоянии отозвать права старого поколения, остановить либо
  изолировать уже допущенные запросы и запретить старым сеансам I/O.
  Только после этого выдавать новое поколение. Старые ключи доступны для
  чтения и совместимой очистки, но их право записи не возвращается.
  Старый установщик правил не должен снимать ограничения.

1. Под блокировкой Meeting сверить актуальный допуск и `deletion_epoch`;
   зарегистрировать намерение и подтвердить COMMIT. До подтверждения и
   после его неопределённого исхода запрос не начинает I/O. Освободить
   Meeting до I/O. Под блокировкой своей записи `pending` проверить
   принадлежность попытке. До Create устойчиво зафиксировать, что он
   мог быть отправлен; повторно взять журнал и убедиться, что очиститель
   его не захватил. Не повторять Create для того же ключа.
2. Передавать данные только через один явно созданный multipart `uploadId`,
   даже для небольшой части. Подтверждение Create и устойчивый COMMIT
   записи именно этого ID обязательны до UploadPart и Complete.
   Перед отправкой вновь взять только свою строку журнала и непрерывно
   удерживать её через UploadPart, Complete и COMMIT `settled`. Потерянную
   транзакцию нельзя заменить новым захватом даже после позднего успеха.
   Отключить скрытые повторы SDK, повторы посредников и редиректы.
   Complete отправляет подписанное условие `If-None-Match: *`.
   Успех требует корневого XML-элемента `CompleteMultipartUploadResult`,
   ожидаемых бакета и ключа и непустого ETag; `HTTP 200` с `<Error>` не считается успехом. Передавать
   данные потоково ограниченными S3-частями; не увеличивать объём памяти
   до размера дорожки. Установить конечные таймауты соединения и чтения,
   общий монотонный срок всей попытки и конечный срок транзакции PostgreSQL
   с блокировкой. После превышения срока не посылать следующие запросы,
   прекратить ожидание и освободить транзакцию. Уже отправленный запрос
   всё ещё мог завершиться в MinIO: неизвестный Complete или COMMIT
   `settled` оставляет обязательство и останавливает исходный запрос.
3. Отпустить блокировку журнала до позднего допуска; повторно взять
   её после продуктовых блокировок в установленном порядке. Принимать
   только свои строки `pending + settled` с точным ключом и без
   захвата очистителем. Один владелец транзакции
   публикует часть или дорожку и закрывает все соответствующие точные
   строки журнала одним COMMIT. Общие операции и обработчики ошибок
   не закрывают и не создают эти строки заново. При неизвестном результате
   COMMIT запрос не удаляет, не переотмечает и не пересоздаёт объект:
   либо COMMIT закрепил принятого владельца, либо остался журнал.
   Известный отказ оставляет непринятый ключ на согласованную очистку.
   При конфликте условного Complete не считать занятый ключ своим;
   принятый или иной чужой объект защищён, неясное владение остаётся
   отдельным обязательством для сверки.
4. Фоновая очистка и полное удаление встречи используют исходную строку,
   сверяют отсутствие принятого владельца и подтверждают COMMIT необратимого
   захвата до I/O. Обе ветки используют один протокол. Полное удаление
   сначала обрабатывает защищённые обязательства отдельной фазой после
   устойчивой метки удаления, затем заново сверяет их под Meeting перед
   продолжением. Сетевые операции этого протокола не держат Meeting;
   завершение очистки сверяет тот же номер попытки захвата. Нельзя заменять её второй общей строкой. При известном
   ID подтвердить Abort и ListParts с `NoSuchUpload`. Одиночный DELETE
   допустим только при доказанном владении и гарантии, что чужой объект
   не может занять ключ до DELETE, даже если HEAD ещё возвращает 404.
   После DELETE проверить HEAD 404 на здоровом MinIO без текущих или
   исторических версий. Это подтверждение на уровне API.
   На закреплённом MinIO подписанный `If-Match` у DELETE не защищает
   от замены: неверный ETag не остановил удаление. Пока не проверена
   изоляция ключа либо другая атомарная защита чужого объекта, не удалять
   неоднозначный ключ и не включать писателя.
   Кандидат для отдельной проверки: выделенная область строгих попыток,
   в которую обычные роли и старые писатели не могут писать. Строгому
   писателю дать только `PutObject` на эту область; MinIO применяет его
   и к обычному PUT, поэтому выделенный клиент не предоставляет обычный
   PUT или выдачу полномочий наружу. Очиститель получает точные
   `GetObject`, `DeleteObject`, `AbortMultipartUpload` и
   `ListMultipartUploadParts` на ту же область, без `PutObject`.
   Метка объекта совпадает с устойчивым идентификатором попытки. При наличии объекта сверять метку; чужая,
   отсутствующая или неверная метка запрещает DELETE. При HEAD 404
   требуется та же защита от чужой записи до окончания DELETE.
   Права, маршруты и состояние бакета не меняются, пока этот протокол
   активен; перед изменениями остановить писателей и очистителей,
   сохранить обязательства, заново подтвердить конфигурацию. Это
   кандидат, пока не проверен полный состав ролей и оба очистителя.
   При неопределённости обязательство остаётся в журнале; после
   ограниченных повторов оно становится `terminal_unknown`. Последний
   просроченный `deleting` также должен быть виден оператору. Ответ
   очистки не разрешает выставить `settled` или принять объект.
5. При потерянном Create до подтверждённой фиксации ID медиа не отправляется;
   отсутствие объекта и пустой список не закрывают журнал. Оператор
   отдельно и с узкими полномочиями сверяет место хранения и точный ключ,
   может принять найденный единственный ID только для очистки, затем
   выполняет тот же протокол. Основная роль API не получает `s3:ListBucketMultipartUploads`.
   Действующий `s3:ListBucket` для объектов — другое разрешение. На этой
   версии MinIO поиск multipart нельзя ограничить IAM-условием `s3:prefix`.
   Только доверенная операторская команда использует отдельную роль
   с `ListBucketMultipartUploads` на целевой бакет, без чтения, записи,
   Abort или DELETE. Она извлекает ключ из авторизованной строки журнала,
   не принимает ключ от вызывающего и передаёт совместимому очистителю
   только ровно один точный результат. Пустой список, неточное или
   неоднозначное совпадение не закрывают запись журнала.
   Полное удаление встречи не сообщает `active_purge_complete`, пока
   любое такое обязательство остаётся нерешённым, включая коллизию
   и последний просроченный захват. Операторский повтор исполняет или
   устойчиво ставит в очередь именно это обязательство и не заявляет
   завершение на основании пустого фильтра.

**Порядок реализации и откат.** B2c.14a сохраняет существующий безопасный
отказ до I/O для нескольких частей одной дорожки строгого сеанса. Убирать
его и подключать календарный путь можно только после реализации и приёмки
B2c.13/B2c.14b. Сначала развёртываются миграция и поддержка обоих путей
очистки; писатель включается отдельно после проверки всех экземпляров.
При откате остановить или оградить писателей; выданные строгие сеансы
обслуживаются совместимым кодом либо получают отказ до I/O, включая
приём частей. Сохранить совместимых очистителей и операторский повтор до
разбора всех незавершённых журналов. Сверить также обязательства и сеансы,
которые могли потеряться при восстановлении более старой копии: смена
поколения предотвращает перезапись, но не подтверждает очистку этих данных.
Если сверка неполна, сохранять долговечное `recovery_unknown` для затронутых
встреч или всей области восстановленного хранилища, если встречи неизвестны.
Оба пути сверяют этот признак: он блокирует `active_purge_complete` и
операторское `converged`, даже если восстановленный журнал пуст. Снять его
можно после подтверждённой сверки и учёта всех обязательств. Для принятых объектов подтвердить
чтение, обработку и удаление по сохранённым ссылкам. Запрет удаления для
обычной роли требует направить точные операции над принятыми строгими
ключами через совместимый очиститель также при очистке временных данных
и по сроку хранения; наличие ссылки не превращает старый клиент в
совместимый. Старый очиститель
полного удаления несовместим с незавершённым новым журналом. Неизвестное
состояние или история конфигурации хранилища закрывают допуск; одной
проверки конфигурации при старте недостаточно.

Проект опирается на [проверки MinIO и отката GRAF](validation-2026-11-08-t109-calendar-record-prompt.md#независимое-ревью-и-проверка-отката-через-настоящий-graf).
Модель состояний — в [data-model](data-model.md#t104b2c13b2c14b--журнал-объекта-строгой-загрузки),
критерии — в [Quickstart](quickstart.md#t104b2c14-завершение-после-отзыва-допуска).
До независимого допуска CHK005 и CHK008 это проект, а не снятие ограничения.

## T071: исправление канонического микса Windows

Область — повышенный риск, тракт записи; это исправление выявленного дефекта
в T071, владелец [#5783](https://github.com/yshishenya/graf/issues/5783).
Уточнение FR-010 и FR-011 опирается на ранее утверждённый эталон GRAF Dev
`1c581d4555c5c0976e6b24746240181fc7befc4b` и формулу F177. Нового
пользовательского выбора нет. Применять формулу на существующей границе
`RecordingAudioTimeline` после AEC и до передачи writer. Проверка конечности
очищенного отсчёта использует существующий отказ AEC; частичный кадр не
публиковать, ранее принятые кадры оставить действующему правилу.

Сохранить разметку времени, размер блока и очереди, авторизацию, приватную
паузу и готовность AEC. Не трогать порядок и настройку AEC, разрешения,
кодирование, схему, отправку и хранение. Уже готовые пакеты не переписывать;
уже переданный на хранение префикс незавершённой записи не пересчитывать.
Проверить конкретные выходные отсчёты, отсутствие обрезания нормированных
пиков, отсутствие публикации при неконечном выходе и прежнее поведение
паузы и EOS. Полные замеры длительности, CPU, памяти и аппаратная приёмка
остаются в T063/T071; локальное исправление их не закрывает.

Чеклист [требований](checklists/t071-canonical-mix.md) относится только
к срезу микса; изменение старта AEC требует отдельного решения и прогона.

### T071: причина сбоя AEC при завершении записи

Диагностика тракта записи, повышенный риск. Уточнение FR-010/017:
наличие `aecProcessFailed` не означает ошибку часов. Переиспользовать
`aec_unavailable`; новый код, схема и телеметрия не нужны. Приёмник
кадров возвращает существующий `ReasonCode` (`none` при успехе).
Контроллер сохраняет первую причину при ошибке в обычном приёме
или при остановке. При отказе закрытия шкалы без ранее сохранённой
причины финализатор использует то же преобразование. Синхронизация,
приватная пауза, Stop, EOS, правила префикса и допуск записи прежние.

Повторить тест на синтетическом сигнале через диспетчер до финализации.
Проверить ошибку AEC и неконечный отсчёт, истинную причину, один
пригодный блок, отсутствие обычного успеха и понятный текст при наличии
и отсутствии сохранённого префикса. Установленная и аппаратная
приёмка остаются в T071. Изменение запуска AEC вне этого среза.

## T125: восстановление размещения главного окна

Полоса `high-risk-product`: изменение нативной оболочки не должно создавать
путь, на котором окно и Stop недоступны. Источник — [уточнение T125](spec.md#session-2026-11-10--t125-расположение-главного-окна-windows),
FR-002/015, SC-009 и F293 FR-008. Граница: `AppMain.cpp`, маленький
проверяемый расчёт размещения рядом с `Shell/`, существующие Windows
тесты и регистрация теста в `apps/windows/CMakeLists.txt`. Не вводить
второе окно, веб-настройку, библиотеку, службу или собственную схему хранения.

- `AppMain` остаётся владельцем главного окна. Вызвать восстановление один
  раз в существующем пути первой активации с уже известным HWND и DPI.
  Возврат из трея не восстанавливает размещение с диска. При отсутствии
  подходящей записи использовать существующую начальную геометрию.
- Windows остаётся Per-Monitor V2. Выбрать прежний активный монитор по
  однозначному интерфейсному имени монитора из `EnumDisplayDevicesW`
  (`EDD_GET_DEVICE_INTERFACE_NAME`); неизвестный или неоднозначный
  идентификатор считать отсутствующим. Не сохранять `HMONITOR` или `DISPLAY2`.
  Использовать Win32 `GetMonitorInfoW` с
  `rcWork` в общих экранных координатах, включая отрицательные. Проверить
  DPI после переноса HWND на выбранный экран, затем применять окончательную
  геометрию через `AppWindow.MoveAndResize` в экранных координатах. Для
  начального размещения главного окна использовать ту же `rcWork`: у
  `DisplayArea.WorkArea` начало отсчитывается от самого экрана. При неизменном
  DPI исходный физический размер и отступы не пересчитывать. При новом DPI
  пересчитать их отношением нового DPI к сохранённому; ограничить размер
  и положение рабочей областью. Если экран исчез, центрировать ограниченный
  размер на основном. При сбое API сохранить доступное системное или
  начальное положение, не отменяя запуск.
- После инициализации отслеживать обычную геометрию через
  `AppWindow.Changed`; учитывать только изменение размера/позиции главного
  окна, которое видно и в состоянии `OverlappedPresenterState::Restored`
  (дополнительно исключить `IsIconic` и `IsZoomed`). Не сохранять
  программные промежуточные изменения восстановления. Объединять события
  серии перемещения/размера; штатное скрытие и выход могут записать уже
  принятую обычную геометрию, но не считывают геометрию скрытого или
  развёрнутого окна. Снять подписку и остановить отложенную запись при
  разрушении окна.
- Хранить один необязательный составной параметр в
  `Windows.Storage.ApplicationData.Current.LocalSettings`, в профиле
  приложения. Принимать только целую валидную запись; ошибка доступа
  не мешает окну или записи. Без удалённых данных и без вывода
  идентификатора монитора в журналы. См. [данные T125](data-model.md#t125-размещение-главного-окна).

Проверить расчёт прежней геометрии, отрицательное начало координат,
разные DPI, малую рабочую область, исчезнувший монитор и неверные числа
на переносимых тестах; Windows проверяет события окна и состояние
хранилища. Приёмка точного MSIX и Dev — в [Quickstart](quickstart.md#t125-восстановление-главного-окна-между-запусками).
Границы Constitution II: управление захватом и Stop не меняются; проверка
новой геометрии не закрывает T108 или T097. До реализации нужны независимый
[чеклист T125](checklists/t125-main-window-placement.md), текущий analyze
и связь задачи с GitHub.

## T126: системный звук при потере выбранного микрофона

Полоса `high-risk-product`. [Уточнение T126](spec.md#session-2026-11-10--t126-потеря-выбранного-микрофона)
устанавливает общий результат. Windows-реализация принадлежит F200;
исправление macOS необходимо согласовать с владельцем F293 и провести
в отдельном срезе macOS, чтобы не смешивать исходники и приёмку.
Зафиксированный эталон остаётся базой воспроизведения; исправленную пару
назначают эталоном после совместной приёмки.

1. В Windows различить доказанное отключение **фактически активного**
   микрофона и общий отказ. Явное решение 2026-11-12 расширяет T126:
   тот же путь применяется к явно выбранному и разрешённому по умолчанию
   при старте входу. Привязать существующий наблюдатель к уже разрешённому
   endpoint текущего worker; не искать новый default при уведомлении.
   Смена default и ошибка перечисления не доказывают потерю, reconnect
   не открывает микрофон в той же сессии. Существующие generation, FIFO,
   fault-before-proof и T120 guards остаются обязательными. Источник доказательства — подтверждённое
   состояние того же endpoint и идентичность текущей сессии по
   [§3 контракта](contracts/windows-desktop-contract.md#потеря-выбранного-микрофона--t126). Ошибка WASAPI
   или завершение потока сами по себе этого не доказывают. Сравнивать
   идентичность только в памяти. Нативное уведомление не выполняет запись
   и не ждёт UI; переход производится существующим владельцем захвата.
2. Использовать последовательность существующего диспетчера и тип
   `SourceEndOfStream`: завершить приём микрофона до публикации его
   границы, обработать достоверные пакеты до границы, исключить опоздавшие
   и повторные события. Нельзя повторно завершить тот же вход при Stop
   или закрыть паузу до окончательного Stop. Сбой или гонка, не позволяющие
   доказать границу, остаются прерыванием с сохранением достоверной части.
3. В `RecordingAudioTimeline` отдельно завершить микрофон, оставив
   монотонность, проверку пропусков и ограничение очереди системного
   источника. Нулевой вклад микрофона после границы привязан к проверенным
   кадрам вывода; не создавать пакеты захвата или разрешение для нового
   источника. Сохранить правило микса и AEC3 с нулевым микрофоном
   до и после обработки для отсчётов начиная с границы, в том числе
   в пересекающем кадре. Общий отказ AEC и ошибки часов по-прежнему
   не открывают обходную ветку. На Mac отдельно исследовать уже имеющийся
   буфер переупорядочивания и подтверждённую запись его данных до границы:
   не сбрасывать исправные данные как при общем терминальном отказе.
4. Сохранить тот же видимый индикатор, доступность Stop и явную причину
   ограничения в `NativeCapture` и нативном тексте. Один финализатор
   сохраняет защищённую локальную запись как `sealed_degraded`,
   с причиной недоступности микрофона и проверенным результатом.
   Автоматическая и ручная отправка запрещены, включая перезапуск. Пауза,
   если была открыта, завершается по уже действующему правилу T120.
   Если после потери микрофона отказывает системный источник, часы или
   защищённое хранилище, окончательный результат честно отражает этот сбой.
   Контракт сервера, права отправки и схема пакета остаются прежними.

Сначала воспроизвести отказ на старых исходниках, затем закрыть его
проверками контроллера, звуковой шкалы и записанных файлов: один переход,
нет потерь и дублей проверенных системных кадров, нет утечки микрофона
на границе, очереди и Stop сохраняют действующие пределы. Для итоговой
приёмки — [T126 в Quickstart](quickstart.md#t126-потеря-выбранного-микрофона)
на проверенной паре установленных приложений и физическом Windows x64.
До изменения кода — независимый чеклист, analyze и привязка в GitHub.
Для расширения от 2026-11-12 повторить все положительные сценарии и гонки
в двух режимах выбора: explicit и resolved-default. Сначала доказать RED
исходного default-сценария без изменения проверок кадров/границ/deadlines.
Текущее ревью 7/0 от 2026-11-10 относится только к selected-only и не
является допуском этого расширения. Историю ревью не переписывать.
Согласование эталона F294 ведётся отдельно по точному upstream
`e6195edc787b6c2a8b66b697d1e453e27fdf614c`; Mac25 и docs6 не являются
разрешением менять Windows исходники или объявлять установленную приёмку.

### T088/T118/T121: account DOM — подготовка требований 2026-11-12

T088 владеет результатом bridge §6: немедленный отзыв прежних account/document
capabilities; подтверждённая очистка обоих storage actual profile/origin до
принятой reload/new-account publication; error/unknown/stale не успех.
Не выбирать API/helper из предположения. Сначала установить фактический охват
и completion доступного WebView2 operation, затем после отдельного допуска
доказать порядок на generated localStorage/sessionStorage sentinel и A→B→C,
logout/close/recreate/navigation. T118 проверяет сохранность native protected
media/queue/keys/settings; T121 — прежнюю cookie-политику входа/выхода/CSRF и origin/nonce/operation fences и
public reader без native authority. Прежние queue truth/epochs/leases неизменны.

### T108/T110/T097: Stop — подготовка требований 2026-11-12

T108/T110 применяют матрицу desktop contract §8 ко всем нативным поверхностям:
starting/recording/paused/degraded имеют доступный Stop, stopping/finalizing
остаются видимыми без доступного повтора. Не подменять indicator readiness
enabled Stop. Сначала доказать исходное несоответствие и затем, после допуска,
проверить cancellation/late READY/повтор Stop/Quit/actual drain и keyboard/AX;
T110 сохраняет F6/nonactivation, T097 — точный installed MSIX. Не менять
isCaptureState или иной код этим текстом; API/helper/архитектура не выбираются.
T125 и шесть прежних invariant sections остаются неизменными.


## T127: предупреждение о локальном месте

Режим `high-risk-product`: узкое продолжение существующего F200 через
specify → clarify → plan → checklist → tasks; независимые review/analyze/issues
и допуск к исходникам остаются за Main. Основание — T127-R01–R06 в spec,
[desktop contract §10](contracts/windows-desktop-contract.md#10-storage-warning--t127)
и [чеклист требований](checklists/t127-storage-warning.md). Авторский этап
не реализует код и не принимает работающий продукт.

### Три существующих файла и существующий worker

1. `apps/windows/RecApp/Storage/ProtectedCustodyMetadata.h`: объявить один
   worker-only `ProtectedCustodyStoreOwner::queryStoragePressure()` с существующим
   результатом `CustodyFileResult<unsigned>`, без новой модели счётчиков.
2. `apps/windows/RecApp/Storage/ProtectedCustodyMetadata.cpp`: проверить
   действительного владельца и удерживаемую queue lease и прежнее состояние
   отказа; вызвать `queue_->checkWriteReserve(0, 0)`, на успехе вернуть
   `queue_->storagePressurePercent()`, на отказе сохранить error/nativeError.
   Нужен queue с rootLease: запрос через голый root пропускает проверку cap.
   Нельзя использовать sticky `Guard::reserve` для показа состояния. Нулевой
   peak — наблюдение, без файлов, commit, блокировки дальнейших записей и
   разрешения аудио. Ошибка запроса не отравляет исправного владельца.
3. `apps/windows/RecApp/Recording/NativeCapture.h`: в существующем
   `StorageStartupWork` хранить один объединяемый `spaceQueryRequested` и
   последний результат (необязательный процент, error/nativeError). Существующий
   worker исполняет запрос после startup validation и по существующим событиям
   activation/wake/scheduled, вне mutex значений и без пересечения с
   commit/adoption, записью или finalizer; Start/Stop/drain приоритетнее.
   Намерение запроса устанавливается до account/network веток recovery;
   существующий poll будит worker и переносит безопасные значения. HTTP и
   Retry-After не владеют запросом. Отложенный сетевой scheduled recovery не
   даёт обещания периодичности и не является условием Start.

После успешной factory и каждого существующего `writer->append(frame)` копировать
уже вычисленный `writer->package()->storagePressurePercent()` в значение текущего
`RecordingWork`, без I/O и передачи writer в UI. После команды с подтверждённой
записью можно использовать её уже обновлённое давление; read-only/no-change
команда не доказывает нового измерения. UI получает значения и
`storageWarningText()` без доступа к файлам. Показ различает pending, warning,
последний недостаток места и ошибку наблюдения по T127-R01/R04; успешное новое
значение ниже порога снимает предупреждение. Ошибки записи выше по приоритету.

Не менять `readiness().storageWritable`, protectedQueueComplete, reservation /
adoption ACK, V5 factory, startPreparedRecording и capture controller.
Предупреждение не создаёт дополнительных отказов ручного или автоматического
старта. Не добавлять probe, TTL, таймер, поток, StorageCommand, ticket, схему,
миграцию или новый сервис. ProtectedCustodyFiles/packed/writer сохраняют
существующую арифметику и фактические проверки каждой группы записи.

### Последующее подключение AppMain и порядок приёмки

Boole подключает безопасные summary/`storageWarningText()` в существующем
`apps/windows/RecApp/AppMain.cpp::refreshNativeState()` рядом с `readinessText_`:
видимый доступный текст для idle/recording/paused, без нового диалога/контрола
и без замещения более важных причин, индикатора и Stop. WebView2Host не нужен.
Этот исполнитель AppMain/WebView2Host и T088 не меняет. Внутренний getter
не закрывает T127 до видимого подключения и его проверки владельцем.

Порядок одной T127: независимые gates Main → содержательные регрессии из
[Quickstart T127](quickstart.md#t127-предупреждение-о-локальном-месте) → три файла
→ подключение Boole → проверка видимого результата. Тесты используют существующие
genuine-owner fixtures и точки наблюдения; не подставляют фиктивные owner/writer
или ready-флаги. Нет зависимости от новой реализации T088/B31 и правок их
секций; текущая validation и активный native127 snapshot остаются у Main.

## T116 — штатный FFmpeg после решения владельца 2026-11-16

Полоса остаётся high-risk-product, существующие T116/T118. Решение и границы
задаёт [контракт §5.1](contracts/windows-protected-local-custody.md). Конституция
I/II/IV/VI сохраняется: WASAPI/AEC/clock и local recording truth принадлежат
GRAF; FFmpeg заменяет только подтверждённо дефектный AAC encoding/muxing путь.

После независимого [ревью требований](checklists/t116-stock-ffmpeg.md), analyze
и синхронизации существующих GitHub задач:

1. Закрепить поддерживаемую стабильную версию, официальный source hash,
   воспроизводимую LGPL-сборку обычного FFmpeg и архитектуру; проверить
   уведомления/исходники/условия распространения. Не использовать GPL-сборку
   Homebrew и не продолжать собственный allocator/private715 fork. Прежние
   исследовательские файлы и квитанции сохраняются как история, не поставляются.
2. В `apps/windows/RecApp/Recording/V5LocalRecordingWriter.cpp::writePlayback`
   заменить только MF AAC encoding/muxing блок, переиспользуя существующие
   canonical reader и protected seek/rewrite IO. Жизненный цикл writer,
   checkpoint/prefix/finalize и вызовы `writePlayback` сохраняются. Encoder
   работает вне audio/UI callbacks и не меняет PCM, AEC, cutoff, v5 bytes/ranges/UUID,
   durable authority или правила ошибок. Удалить только заменённый MF AAC-блок
   и действительно неиспользуемые зависимости; `LocalRecordingPackage.cpp`
   остаётся reader/inspection consumer, Media Foundation reader/playback сохраняются.
3. Включить DLL/лицензию через существующие `apps/windows/RecApp/GrafWindowsApp.vcxproj`,
   `apps/windows/CMakeLists.txt` и упаковочный путь; загрузка только app-local,
   ошибка зависимости не подменяется старым encoder или внешним executable.
4. Переиспользовать `apps/windows/Tests/GrafWindowsContractTests/` и
   `GrafWindowsPackageTests/` для аудио, защищённого IO, отказов и сохранности;
   выполнить [приёмку](quickstart.md#t116--штатный-ffmpeg-и-измерение-памяти).
   Собственные буферы GRAF учитываются до allocation и затираются; внутренние
   объекты FFmpeg освобождаются штатно, полное затирание не заявляется.

Не вводятся вторая запись, служба, процесс encoder, открытые временные файлы,
новый формат хранения или копирование всей встречи в RAM. Длинная запись,
установленный MSIX, x64 hardware/AEC и публичная подпись остаются отдельными
непройденными воротами, пока нет соответствующих фактических результатов.


### T116/T118: фазовый замер завершения — 2026-11-17

High-risk-product; уточнение существующей диагностики FR-012/013 и SC-003/005/006,
без нового формата или изменения продуктовых критериев. Часовой искусственный
тест R11 показал finalize 1041244 ms; причина ещё не установлена. Сначала
измеряется существующий путь, затем по результату выбирается исправление.

Единственный изменяемый исходник —
`apps/windows/Tests/GrafWindowsContractTests/NativeCaptureStorageIntegrationTests.cpp`:
существующая `protectedStorageProfile` и её единственный CLI caller.
Прежний selector без длительности сохраняет 1000 блоков / 10 секунд и
`written.calls <= 16`. Дополнительные значения только 30/120/300 секунд
соответствуют 3000/12000/30000 блокам по 10 ms; неверные аргументы дают exit 2
до создания fixture. Используются прежний искусственный сигнал, один worker
и один настоящий finalize, без микрофона, сети и дополнительного cold pass.

Новый общий таймер охватывает только вызов writer finalize; сохраняет входной
и выходной GetLastError. Четыре прежних непересекающихся этапа остаются
canonical_seal/wav/aac/inspection. Их сумма проверяется до вычитания из общего
времени; отрицательный остаток запрещён. AAC включает protected IO, sealing,
hash и decode, а metadata counters — вложенные измерения. Их нельзя складывать
с wall time или выдавать за чистое время кодека, DPAPI либо физического диска.
Production hooks, guards, protected IO, owned64MiB/wipe и semantic decode не меняются.

До применения: независимый checklist/analyze и актуальная связь T116/T118 с
issues; затем отдельная проверка точного source diff и сборки. До выполнения —
независимое ревью существующего runner с точными EXE/DLL/source/argv pins,
180 s на case и 15 min на весь последовательный проход 30→120→300 с cleanup.
FAILED/TIMEOUT/UNKNOWN останавливает проход до reconciliation; timeout не
доказывает завершение worker и не разрешает удалять его активные файлы.
Принимаются только реальные terminal/owned-idle/cleanup результаты. Сроки,
длительность и критерии не расширяются ради PASS. Такой замер не закрывает
T116/T118, installed Stop, SC-003, x64 hardware/AEC либо выпуск.

## F296 parity — защищённый локальный кэш (T128–T133)

Дата:2026-11-16. `high-risk-product`, существующий F200 US2/US3.
Статус: авторский план для review, не implementation GO. Требования
[F296-R01–R08](spec.md#session-2026-11-16--f296-локальный-кэш),
[контракт](contracts/windows-local-cache-cleanup.md),
[reviewer checklist](checklists/f296-local-cache-cleanup.md). Сначала независимо
проверить strict missing finalized local ID → keep решение (contract §2);
точный partial wire/rollback обязателен до T129 codec/readers/writers.
После общих gates T128 разрешает только неразрушающий GET/parser/eligibility.
Не отмечать reviewer boxes автором.

### Основание и constitution check

Точный parity audit: `.dev/t116-master-f296-windows-parity-audit-20261116.md`;
после синхронизации server proof/storage уже сохранены, independent review
`.dev/f200-master-sync-independent-review-20261116.md`. Actual Mac source:
`apps/macos/Shared/Sources/Models/LocalCacheEligibility.swift`,
`LocalCacheEvictionPolicy.swift`, `apps/macos/RecApp/Sources/Upload/LocalCacheCleanupService.swift`
и `LocalCacheEvictionScheduler.swift`. Их source не означает installed F296 PASS.
Применены Constitution storage/owner/deletion truth, protected exact bytes,
metadata-only diagnostics, visible Stop и independent-review gates.
Новых исключений конституции, quota gate или server/Mac feature не требуется.

### Минимальные данные и путь

Новый временный native proof содержит existing sync-state playback,
finalized_upload, meeting.retention и scope/fetch time, bounded на существующем
JSON/WinHTTP path `Upload/DesktopHttpTransport.*`. Read-only fetch не вызывает
loadTracks, upload admission или новый session. `DesktopUploadQueueService.*`
даёт held текущий snapshot/generation; cached history не permission.

Durable partial state живёт в существующем protected package-state, не в queue
флаге, JSON sidecar или второй базе. Нужна явная versioned codec extension
`Storage/ProtectedCustodyMetadata.*` с intent/refs/bindings contract §3. До кода T129
уточняет wire/version/size/оба slot roots/rollback и регрессии; v1/v2 field sets,
DPAPI/packed representations не расширяются молча. `ProtectedCustodyFiles.*`
удаляет только exact owned media inventory, не чужие containers/unknown names.

`Recording/LocalRecordingPackage.*` различает full и verified partial evidence:
полный upload validator прежний; local player получает purpose-bound retained
manifest/M4A proof с exact receipt. `ProtectedLocalRecordingPlayback.*` сохраняет
byte-stream/Clone/engine lifecycle, full EOF/time/flags/bounds и close/drain.
Startup/scan в existing worker распознаёт authorized missing WAV до generic
corruption/repair; свежий sync refresh и full purge остаются совместимыми.

Один worker command cleanup, existing typed persistence ACK и package/root leases;
никакого нового scanner/process framework. Сначала regression и primitive,
затем `Recording/NativeCapture.h`, `AppMain.cpp`, `Web/WebView2Host.*`: native
capability, confirmation/results/cache surface, user toggle и existing auth fence.
UI не выполняет filesystem/network I/O и не получает reusable proof.

Auto подключается к тем же worker commands после manual primitive: объединённые
launch/Stop/upload-finalized/pressure triggers, actual Mac bounded settings из
contract §6, priority capture/Stop/finalizer. Operator toggle перечитывается;
неизвестное давление/невозможность durable intent сохраняют WAV. Порог95% и reserve
не ослабляются ради записи receipt; cleanup не обещается при disk-full.

### Последовательность и пределы параллельной работы

T128 read-only proof/regressions → T129 exact wire review, затем codec/consumers → T130 actual cleanup/
recovery → T131 manual UI и T132 auto → T133 native/installed acceptance.
T131/T132 не помечены [P]: используют shared NativeCapture/AppMain, сначала
развести ownership Main. Checklists/analyze/Main issue sync до production edits;
самостоятельных issues/commit/VM эта подготовка не выполняет. Точная wire review
T129 — обязательный дополнительный gate перед его codec/reader/writer исходниками,
не prerequisite неразрушающего T128 и не permission на missing WAV.
Validation: [Quickstart F296](quickstart.md#f296--защищённая-очистка-локального-wav).
Main native validation2026-11-16-stock-ffmpeg файл и активные R11/R12 bytes не менять.
