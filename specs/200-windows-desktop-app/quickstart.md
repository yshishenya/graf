# Quickstart: Feature 200 Windows desktop-приложение GRAF

Этот runbook предназначен для реализации и validation gate Feature 200.
В репозитории уже есть portable CMake contract surface и заготовка MSBuild/
MSIX; этот runbook не превращает их в доказательство готового Windows продукта.
Windows host обязателен для claims о WinUI/WebView2, WASAPI, Media Foundation,
MSIX и hardware.

## 1. Host prerequisites

- Windows 10 22H2 (19045) или поддерживаемый Windows 11; первый claim — x64.
- Visual Studio с C++/WinRT, Windows App SDK stable и Windows SDK без preview API.
- WebView2 Evergreen Runtime; отдельно проверяется сценарий отсутствующего или
  повреждённого runtime.
- PowerShell 7, `msbuild`, `ctest` и стандартные Media Foundation components.
- Для hardware evidence: встроенный/USB/Bluetooth microphone, HDMI/DisplayPort
  или dock render endpoint. RDP проверяется отдельно как ограниченный сценарий.

Не сохранять в evidence реальные meeting audio, transcript, cookies, tokens,
signed URLs, raw device paths или private meeting ids.

## 2. Build and platform-independent checks

```powershell
Push-Location apps/windows
cmake --preset x64-release
cmake --build --preset x64-release
ctest --preset x64-release --output-on-failure
Pop-Location
msbuild apps/windows/GrafWindows.sln /m /p:Configuration=Release /p:Platform=x64
ctest --test-dir apps/windows/out/build/x64/Release --output-on-failure
pwsh -File apps/windows/scripts/validate-audio-contract.ps1
pwsh -File apps/windows/scripts/validate-webview-boundary.ps1
```

Ожидается: solution собирается без preview SDK, unit/contract tests проходят,
не создаются секретные или content-bearing diagnostics, а bridge policy
останавливает неразрешённые origin/route/command.

Portable CMake/CTest на macOS подтверждает только platform-independent contracts.
Он не заменяет MSBuild/WinUI 3, реальный WebView2 lifecycle, WASAPI capture,
Media Foundation AAC или signed MSIX evidence.

## 3. Synthetic audio gate

Источник synthetic fixture должен генерировать только детерминированные тоны и
шум с известными параметрами: system render reference, microphone near-end,
controlled echo, ±100 ppm clock drift, jitter, packet partition и injected gap.

```powershell
ctest --test-dir apps/windows/out/build/x64/Release -R "Timeline|AEC3|Writer" --output-on-failure
pwsh -File apps/windows/scripts/validate-audio-contract.ps1 -Synthetic
```

Pass criteria:

- два source batch могут иметь разные размеры, но timeline выдаёт только
  contiguous 480-sample frames;
- reference передаётся в AEC3 до microphone frame;
- no dropped/duplicated output frames в 60-minute reference run при ±100 ppm;
- WAV/M4A/timeline duration difference не больше 100 ms;
- integrated RMS dBFS of the canonical 48 kHz mono system-render component,
  measured before final mix over the active synthetic interval, differs from
  the reference by no more than 1 dB;
- processor/timestamp/gap/overflow error не включает raw-microphone fallback;
- только проверенный trusted prefix может быть degraded artifact;
- after warm-up, native process CPU time is no more than 25% of wall time on the
  reference four-core x64 machine, resident memory growth is no more than 128
  MiB, and neither bounded source queue grows without limit.

## 4. Hardware capture matrix

На каждой комбинации Windows 10 22H2/Windows 11 и x64 выполнить manual Record,
Pause, Resume, Stop, endpoint unplug/replug, default-device change, sleep/wake и
Audio Service restart. Отдельно проверить microphone privacy denial, exclusive
consumer, protected/DRM render и disk-full fixture.

Записывать только metadata-safe evidence: OS/build, app build, architecture,
source class, format class, state, safe reason code, counters, durations и
redacted endpoint fingerprint. Raw audio остаётся локальным QA input и не
попадает в git/evidence.

```powershell
pwsh -File apps/windows/scripts/validate-audio-contract.ps1 -HardwareMatrix `
  -Os "Windows10-22H2,Windows11" `
  -Inputs "BuiltIn,USB,Bluetooth" `
  -Outputs "BuiltIn,HDMI,DisplayPort,Dock"
```

Pass criteria: active indicator и one-action Stop остаются видимыми при каждом
fault injection; permission/endpoint/clock/protected/overflow failures не дают
normal-status claim; silent cross-device continuation отсутствует.

## 5. WebView2 security and parity gate

```powershell
pwsh -File apps/windows/scripts/validate-webview-boundary.ps1 -Contract
ctest --test-dir apps/windows/out/build/x64/Release -R "WebView|Bridge|Route" --output-on-failure
```

Матрица обязана включать trusted origin/routes, auth expiry, redirect,
cross-frame message, stale nonce, replayed id, malformed JSON, unknown version,
oversized/deep payload, token/file/process command, WebView close/recreate during
recording, missing runtime и repair failure. Для embedded profile menu отдельно
проверяется, что «Закрыть GRAF» отправляет только `request_app_quit` с payload
`{"action":"quit"}`; любой другой action, origin или route не закрывает shell.
Record/local custody должны
оставаться независимыми от результата WebView.

Сравнить с macOS parity matrix: `/desktop/meetings`, detail, settings, auth
recovery, review и deletion-report. Не добавлять Windows-only business UI.

## 6. Local custody and recovery gate

```powershell
ctest --test-dir apps/windows/out/build/x64/Release -R "Custody|Queue|Upload" --output-on-failure
pwsh -File apps/windows/scripts/validate-audio-contract.ps1 -CustodyFaults
```

Сценарии: offline finalization, process relaunch, network recovery, auth expiry,
partial accepted range, malformed ledger, duplicate Stop, wake recovery и local
purge/deletion truth. Требование — 100 циклов recovery без duplicate meeting или
upload session, когда server truth доступна.

## 7. Automatic recording and accessibility gate

```powershell
ctest --test-dir apps/windows/out/build/x64/Release -R "Automatic|Accessibility" --output-on-failure
pwsh -File apps/windows/scripts/validate-package-smoke.ps1 -UiMatrix
```

Проверить verified target, unknown target, ordinary media playback, eight-second
countdown, «Записать сейчас», «Пропустить», timeout, reversible «Всегда писать
это приложение», missing prerequisites, keyboard-only, screen reader, High
Contrast, 200% DPI, narrow window и reduced motion.

## 8. MSIX package smoke

```powershell
msbuild apps/windows/Installer/GrafWindows.Package.wapproj /p:Configuration=Release /p:Platform=x64
pwsh -File apps/windows/scripts/validate-package-smoke.ps1 -Package <signed-msix>
```

На чистом x64 image проверить install, first launch, WebView2 missing/repair,
update, interrupted update, rollback, uninstall и сохранность user-scoped
recordings/queue. До signed-package evidence нельзя заявлять distribution
readiness; до отдельного approval нельзя публиковать release или deploy.

## 9. Repository gate and evidence handoff

Из корня репозитория выполнить:

```sh
infra/scripts/ci-local.sh --fast
```

Этот gate не заменяет Windows build/hardware/package evidence. Перед PR должен
быть приложен список exact commit, host OS/build, architecture, focused commands,
pass/fail result, exact supported Windows 11 build set, skipped ARM64 lane (если не заявлен), known limitations и
отсутствие release/deploy claim. Для Windows behavior/architecture обязательно
обновить `CHANGELOG.md` на русском.

### Текущий implementation evidence

- Рабочая база: `59803fc1b95e7b76e84d31ee82b7b2cbd24b2a27`; текущий worktree
  содержит незакоммиченный implementation diff и не является release SHA.
- Windows VM: Windows 11 build `10.0.26200.9168`, MSBuild `17.14.51`, x64.
  `GrafWindowsApp.vcxproj` и `GrafWindows.sln` собраны в Release; native
  `GrafWindowsApp.exe` запущен с `MainWindowTitle=GRAF`, `Responding=True`.
  После явного `/utf-8` русские native-строки отображаются корректно. Кнопка
  Record не переводит сессию в запись при закрытых AEC3/permission gates —
  fail-closed поведение подтверждено вручную. Это host evidence для dirty
  worktree, не release SHA.
- Windows CMake/Ninja после свежего configure через x64 toolchain:
  `100% tests passed, 20/20`; quickstart scripts: synthetic audio `2/2`,
  custody `3/3`, WebView boundary `4/4`. Pinned WebRTC AEC3 checkout
  `846fe90a289f58b7c9303a635142aa2c7caa93e5` собран Meson в `440/440`, а
  native app перелинкован с adapter/library. Package smoke без signed MSIX
  проверяет только контракт.
- После штатного MSBuild restore `GrafWindows.sln`, native
  `GrafWindowsApp.exe` и `.wapproj` собраны в Release x64. Package stage
  сформировал unsigned test MSIX; после локальной self-signed проверки static
  package smoke подтвердил manifest, entry point, capabilities и embedded
  certificate. Это не заменяет доверенную release-подпись, clean-image
  install/update/rollback, WebView2 repair и hardware capture. Запрос Windows к
  `/desktop/meetings` получает `401
  application/problem+json`, поэтому authenticated cabinet parity ещё не
  доказана.
- macOS Swift build, `swift test --disable-swift-testing` (`764/764`),
  `ContractValidation`, legacy-audio guard, desktop upload queue и local
  recording persistence — PASS; локальный `GRAF Local.app` собран и прошёл
  `codesign --verify --deep --strict`.
- `infra/scripts/ci-local.sh --fast`: `1240 passed`, server lint и Python
  compile — PASS; macOS portable CMake/CTest — `20/20` PASS.
- T069: WinHTTP transport использует server-authoritative `sync-state`,
  повторно использует meeting/session, грузит только missing ranges, проверяет
  `byte_offset`/`byte_length`, обрабатывает auth/network/server rejection и
  создаёт новую idempotent session после `upload_session_expired`.
- T067/T072/T073/T074/T075 implementation: startup WASAPI подтверждается до перехода в
  `recording`, QPC mapping использует runtime frequency, неподдерживаемый или
  невалидный PCM не превращается в нулевые samples, worker fault блокирует
  normal finalization, а v5 writer очищает partial WAV/M4A artifacts.
- T070 package metadata: manifest объявляет `internetClient`, `microphone` и
  необходимый для full-trust desktop shell `runFullTrust`; native app и
  `.wapproj` собираются в unsigned x64 MSIX. Static package smoke проходит;
  доверенная release-подпись и clean-image smoke ещё не доказаны.
- Не заявлено: hardware WASAPI run, authenticated cabinet parity, clean-image
  package evidence и signed MSIX; это остаётся в T070/T071/T063.

## 10. Latest local implementation re-check (2026-08-30)

- Windows shell no longer hides WebView2 merely because the process is
  unpackaged. WebView2 gets a user-scoped `%LOCALAPPDATA%\\GRAF\\WebView2`
  profile in both dev and packaged modes; runtime/network failure alone shows
  the bounded fallback.
- Native shell now has a persistent recording strip, notification-area menu
  with one-action Stop, a WinUI settings window, microphone onboarding dialog,
  dynamic local-custody summary and allowlisted native bridge handlers.
- Browser-owned auth is read from the WebView2 session cookie after each
  successful document boundary and held in memory only for native upload; it is
  never placed in the bridge, ledger or diagnostics.
- Portable checks after this slice: CMake/CTest `20/20`, route regressions and
  `infra/scripts/ci-local.sh --fast` `1240 passed`; Windows MSBuild/UI,
  hardware, authenticated cabinet and signed MSIX still require the VM gates
  above and are not claimed here.
