# Quickstart: Feature 200 Windows desktop-приложение GRAF

Этот runbook предназначен для будущей реализации и validation gate Feature 200.
Он не является доказательством готового приложения: сейчас в репозитории ещё
нет Windows solution. Все команды ниже должны выполняться на Windows host после
появления указанных путей.

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
msbuild apps/windows/GrafWindows.sln /m /p:Configuration=Release /p:Platform=x64
ctest --test-dir apps/windows/out/build/x64/Release --output-on-failure
pwsh -File apps/windows/scripts/validate-audio-contract.ps1
pwsh -File apps/windows/scripts/validate-webview-boundary.ps1
```

Ожидается: solution собирается без preview SDK, unit/contract tests проходят,
не создаются секретные или content-bearing diagnostics, а bridge policy
останавливает неразрешённые origin/route/command.

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
- только проверенный trusted prefix может быть degraded artifact.

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
recording, missing runtime и repair failure. Record/local custody должны
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
