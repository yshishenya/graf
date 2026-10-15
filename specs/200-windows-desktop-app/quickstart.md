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
pwsh -File apps/windows/scripts/validate-audio-contract.ps1 -Synthetic
pwsh -File apps/windows/scripts/validate-webview-boundary.ps1
```

Ожидается: solution собирается без preview SDK, unit/contract tests проходят,
не создаются секретные или content-bearing diagnostics, а bridge policy
останавливает неразрешённые origin/route/command.

Реальные contract/package tests запускаются через CMake/CTest. Пустые тестовые
проекты удалены из `GrafWindows.sln`; сборка solution не заменяет запуск тестов.

Portable CMake/CTest на macOS подтверждает только platform-independent contracts.
Он не заменяет MSBuild/WinUI 3, реальный WebView2 lifecycle, WASAPI capture,
Media Foundation AAC или signed MSIX evidence.

Проверка Constitution 7 (T081/T082): технически готовый manual Start и
автоматический countdown проходят без полей legal-policy/consent и без WebView.
Для каждого оставшегося условия отдельно проверить отказ: microphone privacy,
input, render, normalization, AEC3, storage, AAC, indicator, Stop, active session,
suppression; неизвестный target не запускает запись. После удаления bool-полей
пересобрать все тесты, включая позиционные ReadinessInputs. Реальная запись
частных разговоров для этой проверки не нужна: использовать synthetic fakes.

Фоновая автозапись T081/T082: проверить отдельный индикатор/Stop до старта при
свёрнутом главном окне; отказ создания/показа не запускает capture. В
AutomaticRecordingSmokeTests проверить слежение с `starting`, второй процесс
той же identity, отсутствие 14/15 секунд, разрыв свежести, повторные/старые/
будущие снимки, предел 599/600 секунд без подтверждения, ручной Stop и ручную
запись. Каталог синтетических целей не включать в рабочее приложение; отсутствие
настоящей встречи/каталога явно ограничивает нативную приёмку.

## 3. Synthetic audio gate

Продолжение T085: до реального Record проверить единственный стартовый 0x1,
запрет повторного/смешанного флага, ReleaseBuffer failure, неизменность
аудиосостояния при отбрасывании и таймаут без пригодного пакета. Итоговая
безопасная сводка должна различать причины часов каждого источника и
стартовые отбрасывания; её нулевые блоки не являются успешной записью.

Источник synthetic fixture должен генерировать только детерминированные тоны и
шум с известными параметрами: system render reference, microphone near-end,
controlled echo, ±100 ppm clock drift, jitter, packet partition и injected gap.

```powershell
ctest --test-dir apps/windows/out/build/x64/Release -R "Timeline|AudioNormalizer|CaptureFaultState|AEC3|Writer" --output-on-failure
pwsh -File apps/windows/scripts/validate-audio-contract.ps1 -Synthetic
```

Pass criteria:

T085: отдельно пройти `AudioNormalizerTests` с включёнными проверками Release:
общая QPC-шкала, несовпадающие device origins, ±100 ppm с округлением,
441 + 441 и малые переменные пакеты, mapper → normalizer → timeline.
Точные часы не требуют искусственной коррекции из-за разбиения пакетов.
`RecordingAudioTimelineTests` проверяет ±48/49 и разрывы; `CaptureFaultStateTests`
проверяет ошибки меток и native lifecycle. Прохождение моделируемого часа
одних метаданных не является 60-минутной звуковой/ресурсной приёмкой SC-003.

Для WASAPI действуют правила §5 `contracts/windows-desktop-contract.md`:
`GetBuffer.devicePosition` первого кадра точно продолжает размер предыдущего
пакета; расхождение не разрешено объяснять ресемплированием. `IAudioClock`
проверяется отдельно и не заменяет packet QPC/device/count. Отсутствие часов
является отказом инициализации. Прежняя гипотеза 2026-09-07 не является
действующим контрактом.

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

Эта матрица выполняется вручную на реальных устройствах. Скрипт
`validate-audio-contract.ps1` запускает только синтетические тесты и проверки
ошибок локального хранения; он не открывает устройства и не принимает список
операционных систем, микрофонов или выходов. Не засчитывать запуск скрипта как
аппаратную приёмку.

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

Дополнительные регрессии T083: исчерпать автоматические повторы и нажать
«Отправить» для одной записи; прервать проверку аккаунта сетевым отказом и
дождаться планового повтора без перезагрузки кабинета; отдельно проверить
401/403 и несовпадение владельца. Перезапуск между сохранением принятых
диапазонов и итогового статуса не оставляет вечное «Отправляется». Повтор
после нового истечения серверной сессии не использует прежний ключ.

## 7. Automatic recording and accessibility gate

```powershell
ctest --test-dir apps/windows/out/build/x64/Release -R "Automatic|RecordingIndicatorTests" --output-on-failure
pwsh -File apps/windows/scripts/validate-package-smoke.ps1 -UiMatrix
```

Проверить подтверждённое приложение, неизвестное приложение и обычное
воспроизведение медиа; режимы «Всегда», «Спрашивать» и «Никогда» с начальным
значением «Спрашивать». В prompt проверить восьмисекундный отсчёт, действия
«Записать сейчас» и «Не записывать», а также «Запомнить выбор»: настройка
сохраняется только при явном действии, не при истечении таймера. Проверить
автоматическое начало записи после отсчёта, изменение настройки для одного
приложения и для всех подтверждённых приложений, смешанное состояние и отказ
при невыполненных условиях начала записи.

`RecordingIndicatorTests` проверяет модель индикатора, а не доступность
настоящего окна. Отдельно на финальной Windows-сборке проверить управление
клавиатурой, экранный диктор, High Contrast, масштаб 200%, узкое окно и reduced
motion. До этой проверки доступность и поведение нативного prompt не подтверждены.

## 8. MSIX package smoke

```powershell
msbuild apps/windows/Installer/GrafWindows.Package.wapproj /p:Configuration=Release /p:Platform=x64
pwsh -File apps/windows/scripts/build-dev-signed-package.ps1 -Package <unsigned-msix>
pwsh -File apps/windows/scripts/validate-package-smoke.ps1 -Package <signed-msix>
```

Предварительных условий у пакета нет — это проверяемое свойство, а не обещание:

- распространяемый пакет Visual C++ лежит рядом с исполняемым файлом внутри
  пакета (`vcruntime140`, `msvcp140` и спутники), поэтому машинный
  redistributable не нужен;
- зависимость `Microsoft.WindowsAppRuntime.2` объявлена в манифесте, а сам
  framework-пакет лежит рядом с MSIX в `Dependencies\x64\`. Если в системе его
  нет, поставить его нужно **до** пакета:

```powershell
Get-ChildItem .\Dependencies\x64\*.msix | ForEach-Object { Add-AppxPackage -Path $_.FullName }
Add-AppxPackage -Path <signed-msix>
```

Проверить, что предварительных условий не осталось, можно так:

```powershell
$p = Get-AppxPackage com.graf.desktop
Get-ChildItem (Join-Path $p.InstallLocation '*.dll') | Select-Object -ExpandProperty Name
```

В списке должны быть `vcruntime140.dll` и `msvcp140.dll`: тогда приложение
берёт их из пакета, а не из системы.

На чистом x64 image проверить install, first launch, WebView2 missing/repair,
update, interrupted update, rollback, uninstall и сохранность user-scoped
recordings/queue. До signed-package evidence нельзя заявлять distribution
readiness; до отдельного approval нельзя публиковать release или deploy.

Ограничение проверки на 2026-09-18: буквальный прогон на образе без среды
разработки не выполнен — доступна одна виртуальная машина, и в ней есть и среда,
и runtime. Вместо этого зафиксированы три проверяемых факта: все импортируемые
библиотеки лежат внутри пакета, framework-пакет поставляется вместе с MSIX, а
установка, обновление и откат проходят на текущем образе (см.
`validation-2026-09-17.md`, раздел T070/T093).

## 9. Repository gate and evidence handoff

Основной PR gate — GitHub Actions `governance-fast` на точном SHA PR.
Для локальной диагностики из корня репозитория доступен:

```sh
infra/scripts/ci-local.sh --fast
```

Этот gate не заменяет Windows build/hardware/package evidence. Перед PR должен
быть приложен список exact commit, host OS/build, architecture, focused commands,
pass/fail result, exact supported Windows 11 build set, skipped ARM64 lane (если не заявлен), known limitations и
отсутствие release/deploy claim. Изменения Windows описываются на русском в
`changes/unreleased/F200.yaml`. Корневой `CHANGELOG.md` собирает оператор
выпуска для зафиксированного кандидата; эта задача его не редактирует.

Актуальные результаты и ограничения находятся в
`validation-2026-09-06.md`. Прогоны ниже — исторические и не заменяют проверку
окончательного состояния.

### Исторические результаты до синхронизации 2026-09-06

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

## Постоянные ключи приложений и первый Windows-каталог

- VerifiedTargetPolicyTests: все три режима сохраняются после обновления
  утверждённых EXE/сертификата/ревизии; неподтверждённая identity и подмена
  targetKey отклоняются. Несколько версий дают одну строку настроек.
- V2 переживает перезапуск/удаление и возвращение записи каталога; bulk не
  назначает режим новым приложениям; ошибка записи не меняет состояние.
  Неверный ключ/enum, дубли, неполный/слишком большой документ не дают Always.
- Старый V1/global документ не превращается в настройку V2 и не удаляется.
  Проверки используют внедряемое синтетическое хранилище, не HKCU пользователя.
- Bundled Teams сверяется с зафиксированными метаданными установки и native
  signature proof. Отрицательный snapshot выполняется без захвата; наличие
  строки Teams не выдаётся за подтверждение настоящей встречи или x64-приёмку.
- Повторить AutomaticRecordingSmokeTests: общий постоянный ключ не разрешает
  подменить точный EXE в countdown или продлить уже начавшуюся запись другой
  identity. Перед запуском сборки подтвердить отсутствие активной встречи;
  не изменять пользовательское Always/Ask/Never ради автоматической записи.

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

## 11. Итоговая приёмка двух платформ (2026-09-27)

Использовать одинаковые синтетические данные и актуальную `parity-matrix.md`.
Записывать точные Mac/source/server/package SHA, ОС, архитектуру, Runtime,
размер окна, масштаб и тему. Частные записи и снимки в evidence не включать.

1. На Mac и Windows пройти все общие маршруты/настройки, их загрузку, пустые
   состояния, ошибки и восстановление. Общие страницы проверить в Chromium и
   WebKit при 1080×620, 744×530, 744×400 и 560×530, в светлой/тёмной/системной
   теме. Нативные окна отдельно — с клавиатурой, диктором, High Contrast, 200%
   DPI и reduced motion. Любое отличие требует причины, не пометки «так в Win».
2. Закрыть главное окно во время безопасной записи >30 секунд, открыть из трея:
   та же запись продолжается, индикатор/Stop видимы. Затем явно остановить.
   Отдельно проверить Quit, повторное закрытие при finalizing и отсутствие трея.
3. Синтетическое название/текст с фразами «На этом Mac», «Настройки macOS»,
   «Windows» сохраняются дословно, в том числе после HTMX swap. При этом
   системные подписи/разрешения соответствуют ОС, сообщения удаления точны.
4. Проверить Start/Settings из трея; фоновые prompt/indicator не меняют
   foreground окно тестового приложения. Stop доступен мышью и клавиатурой.
5. По подтверждённому эталону F277 `51bcff6b…` проверить одну собственную
   компактную карточку: offsets0/1/5, sound/title/quiet, все пять вариантов,
   приоритеты и отсутствие старого −15min/system toast. Deadline=min(due+120s,endsAt),
   повтор/перенос/отмена/offline/restart/context/sleep/lock по новому контракту
   `contracts/f277-notifications-parity.md`. Quit прекращает показ; скрытие окна
   нет. Проверить v2 и отказv1 без mutation, миграциюquiet, ошибкуsave, историю≤50
   без содержания, hover/focus hold, первыйclick, keyboard/screen reader и Stop
   collision. Звук не повторяется поtick и не звучит приcapture/quiet. Preview
   не пишет историю, не начинаетзапись и не меняет сервер. После F277 новый
   системный канал не считается допустимым способом выполнить этот пункт.
6. T102: тестовая платёжная цепочка со всеми redirect/frame/popup и сохранением
   метода/тела без реального списания; истечение и hostile routes отвергаются.
7. Обновления: текущая/новая/неизвестная версия, отказ/повтор, отсутствие
   association, закрытие окна и поздний ответ. Проверка не устанавливает пакет;
   установка требует явного действия, доверенной подписи и отсутствия захвата.
8. Завершить существующие SC-003/005/008 аппаратными/сквозными измерениями,
   не заменяя их переносимыми тестами или VM ARM64 с x64-эмуляцией.

После каждой общей новой функции добавлять соответствующую строку матрицы и
оба набора проверок. PASS компонента не закрывает строку установленного приложения;
непроверенные и проваленные строки препятствуют итоговой приёмке.

## 12. Защищённое хранение: проект проверки T115–T118

Исходная таблица ниже сохраняется для metadata v1. Поправка больших media
objects от2026-10-03 дополнительно проверяется по §14; v1 metadata singleton/
delete rollback tests не заменяются live media proof.

Статус2026-10-02: T114 исследование PASS/independent APPROVED; **продуктового
protected storage ещё нет**. Проектирование T115 принято по независимому
review112/112, storage analyze CRITICAL=0/HIGH=0 и issue-sync PASS. Contract:
`contracts/windows-protected-local-custody.md`. Не запускать миграцию рабочих
записей для проверки проекта. Существующие CTest/`-CustodyFaults` и стенды T114
не подтверждают эту полную цепочку. Теперь разрешены regressions и
implementation T116/T117; T118 и общая приёмка остаются обязательными.

После реализации использовать disposable generated inventory и standard-user
Windows, отдельные собственные profile fixtures без удаления рабочих keys.
Сборка/CTest/native solution — существующий Windows путь из §2; MSIX —
§8. Новые проверочные условия включаются в существующие Core/Contract/Package
tests, а не отдельный постоянно работающий сервис. Команды ниже — только
проверка документации сегодня, не доказательство продукта:

```sh
python3 scripts/check_spec_kit_governance.py
speckit-bootstrap . --doctor --frozen
git diff --check
```

| Проверка после T116/T117 | Обязательный ожидаемый результат |
| --- | --- |
| Wire / тип / bounds | LE exact header/entry, overflow/truncated/extra/unknown role rejected до large allocation; broken encrypted не читается как legacy |
| Logical IO | full/tail/ZERO identity; Clone independent cursor/same generation; SetSize shrink/grow/seek/CopyTo/EOF; errors sticky/got0, no padding |
| Whole v5 path | generated canonical→protected WAV/AAC→manifest/state→restart→inspect/hash; exact v5 bytes/UUID/time/role/hash сохранены, native seek/EOS |
| Disk snapshots | до/после каждого checkpoint/finalize/metadata/atomic temporary/quarantine; no app-written plaintext media/JSON/private content; legacy leftovers явно исключают encrypted claim |
| Commit / GC / budget | cuts before/after every write/flush/publish/ack; last validated checkpoint retained; ambiguous blocks writer/GC; ≤64objects/pass, process shared cache/budget/pins bounded |
| Authority metadata | g1 birth в двух slots до ACK; g1→ACK g2/delete intent→lost slot1→restart blocked; partial birth/любая missing или invalid slot/reference даёт recovery-required, не old ledger/empty queue |
| New payload codec | strict UTF-8 exact schemas §8.1, duplicate/unknown/missing/null/enum/number/depth/ref bounds; own IDs/generation и stage/refs conflicts rejected; v5/v3 bytes unchanged |
| Async / fences | UI/callback no disk crypto; typed pending/committed/not_committed/ambiguous; prepare/drain/finalizer/delete continuation ждут ACK; stale UI не запускает effect, но committed storage generation принимается; flight/result/busy/lease retained |
| Upload / restart | server accepted exact logical ranges/part hashes; reconcile не теряет v3 deletion/purge ops; частичный upload после restart без нового UUID/перекодирования |
| Delete / discard | durable intent, close admission/cancel/shutdown/release pins, actual recycle/purge proof, durable ack; short marker last, повторный запуск не возвращает upload |
| Migration / downgrade | cut после каждого old-name действия, особенно rename до sentinel: actual old load отказывает по заранее durable .quarantine, не empty v3; source stamp changes blocked; original exact bytes preserved до authorized cleanup; strict intent recovery, retirement owner/expiry proven |
| First transition / inter-object cuts | verified legacy → reserved IDs → prepared intent pair → closing bootstrap pair → destination pair → switch/receipt; prepared fence не требует готовую queue; допустимые промежуточные состояния §8, singleton metadata retained blocked; никаких effects до reconciliation |
| Historical barrier / restart GC | g1 prepared block → g2 ref → g3/g4 replacement обоих index slots → restart/standalone validator → bounded GC → тот же transaction; tampered ref/context/generation rejected; transitive roots обоих metadata slots restored прежде GC, tombstone survives terminal pin release |
| Failure matrix | actual profile/key refusal, corruption/disk full/power-loss, no plaintext fallback/no normal claim; original preservation и retries без erase keys |
| Installed matrix | exact SHA/MSIX/EXE, standard-user/offline, Home/Pro/N prerequisites, Win10/11, install/update/rollback; privacy/readiness не выводятся из одной API-сборки |

Повторить100cycles SC-005, измерить owned/MF memory, CPU/IO/latency/Stop и
PRD quota/80%/95%, free disk reserve=min(10GB,10%capacity), включая peak groups/
indices/orphans/pins/legacy/temp. Admission не допускает пересечения reserve;
стендовые64GiB/64MiB не продуктовые доказательства.
Physical x64/60min/AEC и T083/T087/T088 остаются отдельными gates. Звуковой
device тест не нужен для generated storage regressions и не назначается
потому, что проверяется формат файлов. Недоступный hardware честно NOT RUN.

Порядок разработки уточнён 2026-10-02: storage §12 разрешено реализовать после
его собственных T115/checklist/analyze/taskstoissues gates, не ожидая clock
T094–T096 или T119. Искусственные storage-регрессии не требуют микрофона.
Общий clock/installed/physical acceptance этим не принимается; вся матрица §12
сохраняется, неподключённый storage primitive не закрывает T116/T118.

## 13. Календарное подключение T119

Контракт — `contracts/windows-native-web-bridge.md` §10. До реальной ссылки
использовать fake resolver/launcher и синтетические UUID; private URLs/auth
не выводить. В Windows portable/contract tests покрыть exact payload/response,
UUID/duplicate/extra/type/size/depth, frame/origin/route/nonce/replay, one busy,
401/404/503/network/redirect, stale callbacks/token/owner/document switch,
HTMX same UUID/replacement/removal, trusted/untrusted click, terminal not-ready,
join/cancel exact fields, duplicate escaped root/payload keys до SDK Stringify,
invalid Unicode, owned raw payload lifetime, request UUID replay при новом outer
message_id, bounded1024 UUID без eviction, delayed cancel против следующего flight,
cap-rejected UUID повтор даёт только cancelled/not_ready без history growth,
cancel card/menu denied, cancellation перед nonce/script invalidation,
launch false/exception и dialog cancel. Browser recovery получает новый resolver
result, сохраняет query/fragment/port и IgnoreAppUriHandlers=true; shared F279
host corpus проходит и в Mac, и в Windows без изменения expected cases.
Fake resolver: provider_family=calendar/unknown со ссылкой
https://zoom.us/j/12345678901 выбирает тот же Zoom candidate, что и любое другое
допустимое семейство; provider_family=zoom с https://example.org/meeting остаётся
browser-only. Источник календаря не подменяет проверку host/path приложения.

После реализации на точном установленном MSIX: кабинет/card/menu × Zoom/Teams/
Телемост/unsupported host/path HTTPS × installed/unavailable client; keyboard click, двойное
нажатие, network recovery, logout/navigation во время resolver/dialog/launch.
Каждый случай заканчивается handed_off/failed/cancelled без подвисшей кнопки;
нет второго launch/Record от stale result. Handoff не называется входом в звонок.
Join-and-record: только native current action после handoff и readiness; native
fault оставляет indicator/Stop. Card failure/retry сохраняет исходный срок и
bounded5min explicit failure retention, background failure не продлевает его.
Проверить одинаковый общий сценарий текущего Mac, accessible «Открываем…»/status,
browser recovery без повторного native handler. Fake parser tests не закрывают
T119/T097/SC-002; реально отсутствующий клиент отдельно от отказа installed.
Дополнительно: QueryUriSupport Available/absent/unknown/error, без Store popup
при отсутствующем клиенте; trickle response не продлевает resolver15s deadline,
timeout/cancel снимает pending, но повтор до фактического worker exit не создаёт
второго worker/launch. Подтверждённый OS dispatch нельзя считать отменённым
постфактум: отменяется лишь его влияние на новое UI и последующий Record.
Для Телемоста отдельно проверить installed client при выбранном и не выбранном
HTTPS app handler: QueryUriSupportAsync Available и LaunchUriAsync true не
доказывают личность получателя. Приёмка native parity требует наблюдаемого запуска
именно клиента; открытие браузера не засчитывается как запуск Телемоста.

Owner/state этап: CalendarJoinOperationTests использует synthetic identities
и управляемое время, без звука/сетевых ссылок. Покрыть terminal UI при delayed
actual completion и busy до drain; old completion не меняет новый ID. Recovery:
пользователь подтверждает после истечения начального resolver budget, fresh
resolver получает новый15s budget, внешний request остаётся opening; исходный
card/action expiry не продлевается, terminal request не оживает. OS query/launch
и dialog не получают искусственного общего15s timeout. Отдельно adapter tests
обязаны подтвердить actual worker/OS/dialog completion, не только helper boolean.

Launcher adapter: native target/Zoom query/Teams/Telemost и unsupported/non443;
delayed SDK Started, reentrant dispatch/cancel/poll, все пять query statuses,
browser IgnoreAppUriHandlers и launch false/exception. Явная отмена не вызывает
OS Cancel/Close и не снимает pending до natural Completed/Error. Непрошенный
Canceled/ошибка Status не считаются drain; safe terminal без handoff/Record,
retry blocked до доказанного completion или явного выхода/перезапуска GRAF.
API start throw/null без полученного handle завершает только синхронный dispatch,
не доказывает отсутствие OS side effect; нет автоматического browser fallback.
Проверки используют TU-local fake statics с реальными WinRT interfaces, без
запуска целевых приложений; полный installed сценарий остаётся отдельным.

## 14. Packed media v2 — проверка поправки T115, 2026-10-03

До product edits нужны текущие independent checklist/analyze и owner T116;
решение владельца в spec.md не runtime PASS. Нормативный wire/proof только
`contracts/windows-protected-packed-custody.md`, не ненормативный research.
В начале tests RED, затем реализация; live audio/private inventory не нужны.

| Группа | Проверяемый результат |
| --- | --- |
| Exact wire/context | prefix128/header128/ref64/descriptor128, LE/magic/schema/type/role/ID/offset/selector/version, overflow/truncation/reserved/padding/unknown rejected; child-before-parent и exact envelope SHA |
| Native DPAPI | FALSE, TRUE+corrupt/short/oversize, failed hash, allocation refusal → no accepted data/head; output очищен, no plaintext fallback, caps не обещанный native allocation bound |
| Live delta | proven base→candidate, ровно разрешённые changed paths, forged unchanged-child/root/owner stamp rejected; ≤1 DATA+3 nodes per sequential block при коротком и64GiB logical edge |
| Generation/peer | candidate=selected base+1; jump/stale-base/wrong-peer/u64 overflow отказ до append/head; после readback другая cell exact selected base, adjacent pair и slot rule; g1 tie выбирает slot0 |
| NODE/root Ref | самосогласованный plaintext checksum при несовпадающем expected envelope length/SHA всё равно rejected до decode/child-ref use; DATA и все три NODE levels, включая cold retained roots |
| Cold full | same owner release/reacquire, crash, ambiguous publication invalidates proof/cache; обе heads + reachable closure до normal use; no mtime/EOF/new empty recovery |
| Detection-time | после ACK испортить старый DATA; live next-checkpoint не обязан fresh-reread его, но read/cache semantics честны; fresh disk read/full reopen отказывают без normal upload; actual observed fault sticky |
| Birth/heads | обе empty g1 cells independently protected, incomplete/torn birth не достраивается; equal g>1/conflict/nonadjacent pair/invalid slot → no normal authority |
| Cuts/async | каждый records/head write/flush/readback cut; head I/O started → ambiguous до reconciliation; stale/cancel не отменяет committed disk fact, owner/buffers до actual completion |
| Read/Clone/seek | independent cursor/same pinned root, EOF/got0, partial tail, shrink→grow ZERO, больших ZERO ranges без flat arrays, no unsupported read-write shortcuts |
| Worker SetSize | actual `Tree.setSize`: empty/same-size/stale;1/block−1/block/block+1 и radix63/64/4095/4096/262143; truncate→grow не воскрешает прежние bytes, pinned Reader/Clone сохраняет prefix/length.64GiB ZERO создаёт≤7 NODE+1 DATA/327680B, не64GiB fixture. Guard/job/pin/dirty/owned refusal, generation overflow, revoked write; measured native read/write/flush/throw cuts до HEAD и после него сохраняют exact first fault/retained lease. Cold reopen обеих closures, no new snapshot при отказе. |
| Ownership/bounds | existing writable handle/mapping и confinement/ACL/ADS/reparse faults rejected; writer release при Clone сохраняет actual owner; owned64MiB/cache2MiB/dirty4/pins32/jobs4 с admission до allocation |
| Whole-object delete | durable intent и current-authority retirement внешних live retainers → actual jobs/guards completion → container absence → removed ACK; собственные heads/идентифицирующий receipt не удерживают вечно; unknown/ambiguous external refs блокируют purge |
| Regression | все v1 metadata g2/delete-intent→missing slot→restart no rollback; logical v5 bytes/hash/ranges unchanged; unknown explicit representation не decode fallback |
| Versioned metadata | package.v2 refs10 fields/migration.v2 sources11 fields строго по §6.1; unexpected/duplicate/null/stamp conflicts rejected; same original logical SHA/ranges; retained roots обоих metadata slots восстановлены и full-verified перед GC, включая roots вне current heads |

После wire/owner/tree gates, не вместо них: повторяемый synthetic source на
48kHz mono Float32, full block cadence262144/192000s=1.365333s. Измерить рост
last-checkpoint и actual record/read counts при1/2/4/8/16/32/64MiB, отдельно
cold verification, peak memory/native allocation/disk и Stop/tail/seek.
Нельзя принять sustained capture по одному лучшему замеру или одному big-O.
Generated v5/MF/playback/upload/delete/100cycles, точный installed MSIX,
physical x64/audio/accessibility/signature/install/rollback остаются §12/T118
и общей приёмкой. Неподключённый codec/дерево не закрывают T116.

## 15. Приватная пауза T120 — 2026-10-04

Сначала независимый requirements review/analyze, затем owner T120.
Используются существующие Timeline/CaptureFaultState/Codec tests, не реальные
устройства или записи. RED на старом source обязателен. Для codec prerequisite
owner остаётся T116/#7444; capture integration требует собственного T120.

| Проверка | Ожидаемый результат |
| --- | --- |
| Delayed render | установить общий480-frame prefix, Pause→mic480 без render→Resume→render: mic нулевой, system/PTS/count/AEC сохранены |
| Prefetched/timeline | ещё не записанный pre-Pause pending mic и накопления подавлены; уже записанный prefix не меняется |
| FIFO/in-flight | producer добавляет одновременно с Pause/Resume, batch уже извлечён до control; старая очередь подавлена, только новые после точной границы возвращают mic |
| Частичные данные | остаток паузы заканчивается внутри batch/480-frame output; старый prefix0, новый suffix нормальный, count/channels/route/PTS не меняются |
| Повторные controls | Pause/Resume/Pause/Resume заменяют снимок остатка, не удваивают его; постоянный producer не заставляет ждать пустую очередь |
| Неверные данные | NaN/Inf/невалидные timestamps/count/route/overflow отклоняются даже для подавляемого mic; fault sticky, raw fallback отсутствует |
| Mandatory OPEN | отказ write/flush/publication: Pause не принят и новый неподтверждённый сегмент откатан; отсутствие T116 не разрешает plaintext metadata |
| Boundary unavailable | Resume отклонён, прежний OPEN/paused/system/Stop сохранены |
| Best-effort CLOSE | после принятой границы сохранение CLOSE отказывает: Resume остаётся принят, старый durable OPEN не потерян |
| Размер metadata | полный manifest exact64KiB допустим для codec,65537B rejected до publication;1/4096/4097/65536 roundtrip, old4096 известный manifest остаётся читаемым |
| История пауз | actual serializer повторных сегментов проверяет общий размер, не только segment count; cap/full OPEN отказ не обрезает историю; no новые plaintext files |
| Stop/late completion | Stop/EOS и finalizer однократны; late OPEN/CLOSE после Stop/newsession не возвращает delivery/recording, UI не ждёт I/O |

Codec limit — не приёмка logical v5/LocalRecordingPackage validator. Bytes
fixtures Mac ISO8601/Codable, unknown/duplicate keys и package hash/format/
ownership проходят отдельную consumer приёмку T116/T120. Два новых bounds
не увеличиваются вместе: меняется только manifest logical cap, общие memory/
native/cache/queue/root/audio limits остаются прежними.

После synthetic/native acceptance — свежий exact-SHA установленный MSIX,
Record/Pause/Resume/Stop и воспроизведение результата. VM не physical x64;
hardware/AEC/60min/accessibility/install/update/signature остаются обязательны.

## 16. Ближайшие встречи в меню T119 — 2026-10-05

Prerequisites: current requirements review/analyze, exact source hash receipt,
тот же owner/workspace и подтверждённый SDK build. Эталон Mac pinned
`721b5125d799ea798a4af0b3625e18d3c1109039`, plan «T119: ближайшие встречи»,
data-model §8 и bridge §10. Синтетические event IDs/URLs, без private content.

1. Decoder: missing/null/true/false show_upcoming_* и all_day; true defaults
   только для presentation flags, false для all_day. Строка/число/object/array
   вместо bool отвергают весь snapshot, включая all_day второй строки. Прежние
   owner/instant/link/title privacy/bounds сохраняются.
2. Projection: unsorted13+ events и equal startsAt → sort/eventId/prefix12;
   dismissed/canSurface=false/quiet/active capture не скрывают menu rows;
   private/hidden/empty-title/all-day/timezone и unavailable-link labels.
   Failed refresh/auth switch немедленно убирают rows, даже при failed card.
3. Actual native popup: открыть меню, обновить projection/auth до selection;
   старый frozen row не вызывает новый target. Уничтожение owner во вложенном
   message loop безопасно. Обычное закрытие после выбора не отменяет flight;
   presentation-only change не отменяет принятый unchanged target. Keyboard,
   screen reader names, light/dark/high-contrast, DPI и длинный safe title.
4. Menu failure → explicit Retry/Cancel: одна общая busy операция с card/web;
   delayed resolver/SDK/dialog до natural terminal, no early drain/auto retry.
   Retry создаёт новый request/operation, использует fresh resolver после click,
   но сохраняет original action expiry. Delay dialog >15s после Primary не даёт
   свежие15s при poll; истёкший budget fails. Unknown exit остаётся busy.
5. Event removed/replaced/ended, owner/interaction switch во время всех ожиданий:
   нет позднего launch/новой попытки/Record. Одинаковые UUID и одинаковая позиция
   строки не возвращают старую authority. Original expiry не продлевается refresh
   либо переводом часов назад; overflow/invalid conversion fail closed.
6. Installed exact MSIX + authenticated calendar: future event из меню при
   закрытой card/quiet/recording; fresh native/browser launch, отказ/recovery/Retry,
   Cancel и многократный click без второй операции. Menu never Record. Сравнить
с тем же Mac и проверить card Join-and-record и cabinet без регрессии.

Focused portable check после сборки существующего target:
`ctest --test-dir <portable-build> -R '^NativeSettingsBridgeTests$' --output-on-failure`.
Полный portable + serial Windows CTest и SDK solution build обязательны после
integration. Decoder PASS не закрывает menu owner/installed T119; release,
hardware/audio/storage/a11y/update gates остаются отдельными.

### Пользовательское время T119 — Round243

До formatter/transport code требуется закрытие current requirements M1 и analyze;
подробный source/current contract — plan «T119: пользовательское время», bridge§10.
На синтетических metadata проверить exact5 keys/strings/2048 bytes, duplicate/
unknown/missing/null/invalid UUID/zone/URL, wrong owner/workspace и allowed route.
Нынешний document/account invalid result сбрасывает preference; delayed result
после auth/token/nonce/document/context switch не меняет новый context.

Actual Windows Calendar: UTC, Asia/Kathmandu (+05:45), America/New_York до/после
DST перехода и зимнее/летнее Europe/Berlin, all-day/hidden time, empty/system и
unknown zone, NaN/Inf/range overflow. Именованная zone проверяется на native API,
не portable fixed-offset stub. Не менять часовой пояс ОС ради теста.

Installed exact MSIX: аккаунт с zone, отличной от Windows system, правильный
HH:mm в menu; logout/другой user/workspace/session, отсутствие/смена preference
после сохранения на сервере и нового confirmed document. Отдельно same-page save
и dirty/failed save: несохранённая форма не меняет native preference. Preference
или system-zone refresh закрывает открытый popup, но unchanged admitted Join
сохраняет original expiry. Не закрывать T119 по decoder/formatter/probe PASS.

### Настоящее окно повторной попытки T119 — Round249

Отдельный SDK-only проект использует настоящий WinUI ContentDialog и тот же
CalendarJoinOperation, но только искусственные контексты и события. Нужны
интерактивный рабочий стол Windows, установленный Windows App Runtime и обычные
зависимости сборки приложения; запуск без них — отказ проверки, не пропуск.
Не запускать одновременно другие испытания меню/окон. Из PowerShell в корне
репозитория (MSBuild из Developer PowerShell Visual Studio 2022):

```powershell
$taskProject = 'apps\windows\Tests\GrafWindowsContractTests\NativeCalendarDialogTests.vcxproj'
MSBuild $taskProject /t:Restore /m:1 /p:Configuration=Release /p:Platform=x64 /v:minimal
if ($LASTEXITCODE -ne 0) { throw 'DIALOG_RESTORE_FAILED' }
MSBuild $taskProject /t:Build /m:1 /p:Configuration=Release /p:Platform=x64 /v:minimal
if ($LASTEXITCODE -ne 0) { throw 'DIALOG_BUILD_FAILED' }
$taskProcess = [System.Diagnostics.Process]::new()
$taskProcess.StartInfo.FileName = (Resolve-Path 'apps\windows\out\x64\Release\NativeCalendarDialogTests.exe').Path
$taskProcess.StartInfo.UseShellExecute = $false
$taskProcess.StartInfo.RedirectStandardOutput = $true
$taskProcess.StartInfo.RedirectStandardError = $true
if (!$taskProcess.Start()) { throw 'DIALOG_START_FAILED' }
if (!$taskProcess.WaitForExit(60000)) {
    Stop-Process -Id $taskProcess.Id
    $taskProcess.WaitForExit()
    throw 'DIALOG_WATCHDOG_FAILED_NOT_NATURAL_DRAIN'
}
$taskOutput = $taskProcess.StandardOutput.ReadToEnd()
$taskError = $taskProcess.StandardError.ReadToEnd()
$taskOutput
$taskError
$taskCases = @($taskOutput -split '\r?\n' | Where-Object { $_ -match '^native dialog case=[0-5] opened=1 ' })
if ($taskProcess.ExitCode -ne 73 -or $taskCases.Count -ne 6) { throw 'DIALOG_TEST_FAILED' }
$taskProcess.Dispose()
```

Успех — **код 73 и все 6 строк случаев**, не только надпись PASS. Наблюдаются
реальные Opened/Closing/Closed и завершение ShowAsync. Настоящая кнопка вызывается
через системный Automation Invoke. Future-ready при ещё живом native thread не
освобождает старую работу. Проверяются Primary, Close, отмена с Hide, устаревание
до Primary и во время закрытия, а также фактическая задержка закрытия 16 секунд:
после click+15s новая попытка не принимается. Только первый случай создаёт один
новый ticket с новым request и прежним сроком события; HTTP не выполняется.

Это не проверка частных методов AppMain, настоящей клавиатуры/экранного диктора,
SDK Error/неизвестного состояния/отказа ShowAsync/GetResults, авторизации,
обновлённой ссылки, запуска приложения встречи или установленного MSIX.
Эти границы остаются отдельной приёмкой T119/T097; настоящий audio/capture,
protected-storage, physical x64 и release gates этой проверкой не закрываются.

### Структурное описание защищённого пакета — package.v1/v2

`ProtectedCustodyPackageTests` проверяет production parser/serializer из
`Storage/ProtectedCustodyMetadata.*` только на generated JSON и typed values.
Это не запуск приложения, чтение профиля, recording/audio или миграция.
Один точный ключ `schema`, известные поля и nullable stamps; unknown/duplicate
decoded keys, неверный context/generation/directory, числа/представление/фаза,
root/extent и превышение whole payload65536B должны завершаться typed failure,
без принятого value/default/IO. Проверяются writer roundtrip, порядок ключей,
ASCII escapes, directory300/301, packed live/sealed/empty root и исчерпание
общего owned memory budget; квоты не расширяются.

Из Developer PowerShell Visual Studio2022 в корне репозитория:

```powershell
$taskBuild = 'out\windows-package-contracts'
cmake -S apps/windows -B $taskBuild -A x64
if ($LASTEXITCODE -ne 0) { throw 'PACKAGE_CONFIGURE_FAILED' }
cmake --build $taskBuild --config Release --target ProtectedCustodyPackageTests ProtectedCustodyFilesTests ProtectedCustodyCodecTests ProtectedPackedCustodyFormatTests NativeCustodyProtectionFailureTests -j 2 -- /nodeReuse:false
if ($LASTEXITCODE -ne 0) { throw 'PACKAGE_BUILD_FAILED' }
ctest --test-dir $taskBuild -C Release -j 1 -R '^(ProtectedCustodyPackageTests|ProtectedCustodyFilesTests|ProtectedCustodyCodecTests|ProtectedPackedCustodyFormatTests|NativeCustodyProtectionFailureTests)$' --output-on-failure --timeout 300
if ($LASTEXITCODE -ne 0) { throw 'PACKAGE_CONTRACT_FAILED' }
```

Не запускать параллельно с другим native storage test/build. Чужие процессы
не останавливать; дождаться своего actual completion. Результат должен быть
5/5 и exit0, с frozen source/EXE hash, не только строка PASS. Reader возвращает
фиксированное собственное structural value, не input views/proof/lease/pin.
Serializer резервирует прежний64KiB charged cap до plaintext, не растит vector
с освобождением unwiped старого буфера. Actual member hashes, retained roots
обоих metadata slots и closure под тем же owner, prefix/manifest/short predicate
и права effects остаются отдельным validator/consumer gate. Structural success
не разрешает normal upload/discard/GC и не закрывает T116/T117/T118/T120 или
working-profile install/update/rollback.

### Холодная проверка исторической версии packed media

`ProtectedPackedCustodyTreeTests` теперь проверяет `verifyRetained` на generated
истории g1→g2→g3→g4. После фактического освобождения старого owner проверяется
исторический g2, которого уже нет в текущих heads: полный обход текущей пары и
старого дерева, exact context/store/object/container/role и immutable bytes/EOF.
Отдельно проверяются порча исторических DATA/трёх уровней NODE и обеих heads,
недопустимые generation/count/root/extent, readonly mutation/Writer-open,
Reader/Clone lifetime после writer release, pin/job/owned-budget отказы,
EMPTY birth/shrink и 64GiB explicit ZERO без гигантского файла.

Из Developer PowerShell Visual Studio2022, последовательно, без другого
native storage test/build:

```powershell
$taskBuild = 'out\windows-package-contracts'
cmake -S apps/windows -B $taskBuild -A x64
if ($LASTEXITCODE -ne 0) { throw 'RETAINED_CONFIGURE_FAILED' }
cmake --build $taskBuild --config Release --target ProtectedPackedCustodyTreeTests ProtectedCustodyPackageTests ProtectedCustodyFilesTests ProtectedCustodyCodecTests ProtectedPackedCustodyFormatTests NativeCustodyProtectionFailureTests -j 2 -- /nodeReuse:false
if ($LASTEXITCODE -ne 0) { throw 'RETAINED_BUILD_FAILED' }
ctest --test-dir $taskBuild -C Release -j 1 -R '^(ProtectedPackedCustodyTreeTests|ProtectedCustodyPackageTests|ProtectedCustodyFilesTests|ProtectedCustodyCodecTests|ProtectedPackedCustodyFormatTests|NativeCustodyProtectionFailureTests)$' --output-on-failure --timeout 300
if ($LASTEXITCODE -ne 0) { throw 'RETAINED_CONTRACT_FAILED' }
```

Требуется 6/6, terminal exit0 и matching frozen source/EXE hashes; прежний
parser 5/5 или portable PASS не исполняют Windows-only cases. Timeout не
увеличивать, чужие процессы не останавливать. Retained proof всегда readonly,
даже если stamp совпадает с текущей head и физический owner writable. Обычный
отказ записи не повреждает общий owner; наблюдаемая первая ошибка целостности
или native operation остаётся blocking и не заменяется readonly отказом.

Это только проверенные logical bytes под тем же owner. Происхождение stamp из
защищённых metadata, восстановление всех refs обоих metadata slots/barriers,
actual finalized logical SHA, package/account admission и права upload/delete/
GC проверяются будущим caller отдельно. Нет запуска приложения, микрофона,
рабочего профиля, миграции или допуска к install/release. T116/T117/T118/T120
и аппаратные/доступность/установочные критерии остаются открытыми.

### Обе защищённые версии описания пакета

`ProtectedCustodyFilesTests` проверяет `ProtectedCustodyPackagePair::read`
на искусственных файлах: оба физических index slots и оба собственных
расшифрованных package payloads. При исправном higher slot повреждённый lower
не пропускается. Schema1/2, равный birth g1, разные refs g2/g3, 64KiB,
неверные JSON/generation/context, отсутствие DATA и ZERO metadata проверяются
без открытия пользовательского профиля. Обе версии остаются неизменными под
существующим native identity lease до освобождения последней shared reference;
протокольная запись в это время запрещена. Это не проверка связанных media
roots/hashes/manifest, прав аккаунта или перехода данных.

Применить последовательную Release-команду из предыдущего раздела:
те же шесть полных наборов, результат6/6 и exit0. Дополнительно проверить
отладочный вариант того же полного Files test; не запускать одновременно
с другими native тестами либо сборкой:

```powershell
$taskBuild = 'out\windows-package-contracts'
cmake --build $taskBuild --config Debug --target ProtectedCustodyFilesTests -j 2 -- /nodeReuse:false
if ($LASTEXITCODE -ne 0) { throw 'METADATA_PAIR_DEBUG_BUILD_FAILED' }
ctest --test-dir $taskBuild -C Debug -j 1 -R '^ProtectedCustodyFilesTests$' --output-on-failure --timeout 300
if ($LASTEXITCODE -ne 0) { throw 'METADATA_PAIR_DEBUG_TEST_FAILED' }
```

Нужны matching frozen source/EXE hashes и terminal1/1, а не только строка PASS.
Полный Files test также сохраняет прежние audio/trusted-prefix проверки.
Восемь внедрённых ReadFile отказов проверяют точный nativeError; отмена после
physical pair и каждого payload, pin32/job4/owned64MiB, отсутствие
write/rename/flush и освобождение lease входят в тот же тест. Native IO fault
в identity helper не маскируется identityMismatch; неверный ID/размер по-прежнему
отвергается. Debug запуск не объявляется исчерпывающей проверкой всех возможных
allocation cuts нового constructor/control block: эти выходы отдельно проверены
по исходникам. Пределы времени и матрицу не сокращать.

Generic physical pair сам по себе не блокирует запись: для него caller обязан
сохранять подходящий lease. Новый readonly package pair удерживает его сам,
но не даёт права на normal upload/discard/delete/GC. Будущий consumer перед
изменением metadata освобождает proof и заново проверяет полномочия;
не использовать const views после last owning reference release. T116/T117/
T118/T120 и приёмка установленного приложения этим prerequisite не закрыты.

### Защищённое описание → точный запечатанный файл

Overload `openProtectedCustodyReader(root, heldPair, slot, refIndex, cancel)`
принимает sealed ref только из собственной удерживаемой package pair. Проверка
обоих физических flat indices/DATA либо обоих packed heads и retained closure
предшествует сравнению полной logical length/SHA. Read-only stream возвращается
с cursor0 и удерживает parent/member leases через последнюю Reader/Clone ссылку.
Live ref отвергается; недоступный старый flat index не реконструируется. Отказ
другого physical slot сохраняет исходную причину, не возвращает partial stream.

Выполнить последовательно в отдельной копии исходников, без профиля приложения,
устройств и одновременных Windows сборок/тестов:

```powershell
$taskBuild = 'out\windows-package-contracts'
cmake --build $taskBuild --config Release --target NativeHashFailureTests Sha256Tests ProtectedPackedCustodyTreeTests ProtectedCustodyPackageTests ProtectedCustodyFilesTests ProtectedCustodyCodecTests ProtectedPackedCustodyCodecTests NativeCustodyProtectionFailureTests -j 2 -- /nodeReuse:false
if ($LASTEXITCODE -ne 0) { throw 'SEALED_MEMBER_RELEASE_BUILD_FAILED' }
ctest --test-dir $taskBuild -C Release -j 1 -R '^(NativeHashFailureTests|Sha256Tests|ProtectedPackedCustodyTreeTests|ProtectedCustodyPackageTests|ProtectedCustodyFilesTests|ProtectedCustodyCodecTests|ProtectedPackedCustodyCodecTests|NativeCustodyProtectionFailureTests)$' --output-on-failure --timeout 300
if ($LASTEXITCODE -ne 0) { throw 'SEALED_MEMBER_RELEASE_TEST_FAILED' }
cmake --build $taskBuild --config Debug --target ProtectedCustodyFilesTests ProtectedPackedCustodyTreeTests NativeHashFailureTests -j 2 -- /nodeReuse:false
if ($LASTEXITCODE -ne 0) { throw 'SEALED_MEMBER_DEBUG_BUILD_FAILED' }
ctest --test-dir $taskBuild -C Debug -j 1 -R '^(ProtectedCustodyFilesTests|ProtectedPackedCustodyTreeTests|NativeHashFailureTests)$' --output-on-failure --timeout 300
if ($LASTEXITCODE -ne 0) { throw 'SEALED_MEMBER_DEBUG_TEST_FAILED' }
```

Нужны terminal8/8 и3/3 на matching source/EXE hashes. Это проверки сгенерированных
файлов, не записи микрофона. Включены разные старые/новые flat bytes, старый packed
root вне current heads, SHA/length/context отказ, missing other-slot DATA/index,
Clone lifetime, точный EOF, invalid Read/count/HRESULT, CNG failures, owned memory/
job refusal и cancel. Debug не объявляется exhaustive allocation/rewind/wipe cut
matrix. Новый native hash использует один charged+wiped64KiB buffer; прежний
stack buffer `sha256Stream` очищается без изменения старой allocation семантики.

Один проверенный sealed member не принимает всех refs BOTH metadata slots,
live recovery, actual manifest/formats/duration/trusted prefix/positive short
predicate или normal package. Права аккаунта, upload/playback/delete/GC, wiring
V5/MF/queue consumers, T117 migration, H250 working-profile gate и полная T118
приёмка остаются отдельными открытыми обязательствами. Установка/подпись/запуск
на рабочем inventory этой командой не разрешены.

### Совместное чтение рабочих и запечатанных файлов обеих версий

`openProtectedCustodyReaders(root, heldPair, cancel)` возвращает фиксированные
2×5 readonly streams по actual ordinal каждой физической slot. Использовать
те же последовательные Release8/Debug3 команды выше. Проверяются разные
сохранённые bytes/версии, reversed wire order, mixed flat/packed и старые roots,
asymmetric refs, lower-only повреждение, конфликт representation до member IO,
LIVE current checkpoint рядом с SEALED historical ref, отказ quotas и общая первая ошибка. Любая оставшаяся Reader/Clone удерживает
описание и ВСЕ файлы записи; последняя ссылка освобождает их. Неиспользованные
ячейки пусты, каждый успешный stream начинается на cursor0. SEALED сохраняет
exact length/whole SHA/EOF; LIVE использует actual highest из BOTH verified
flat indices либо BOTH current packed closures, без придуманного null stamp.

Одиночная перегрузка использует общий batch: повреждённый sibling отклоняет
даже запрос здорового файла; здоровый LIVE sibling теперь поддерживается.
LIVE target одиночной перегрузки по-прежнему отклоняется. Новые регрессии
проверяют обе LIVE slots, переход finalizing → sealed_normal с lower-only
canonical, разные current/historical bytes, mixed flat/packed, пустой checkpoint,
отказ singleton/trustedPrefix и отсутствие write/repair/slot erase. Независимые
factory открывать последовательно: второй batch не переоткрывает уже удерживаемый
эксклюзивный role. Это расширяет прежнюю ALL-SEALED область успеха, не ослабляя
проверку старой SEALED ссылки. Читаемый checkpoint не доказывает complete-frame
prefix или normal package и не заменяет manifest/formats/phase/trusted prefix, права аккаунта,
интеграцию writer/upload/playback и переход данных. Не удалять старую slot и не
выдавать дополнительный sealed commit ради обхода отказа. T116/T117/T118/T120
и H250 остаются открытыми; working-profile install/launch не разрешён этим шагом.

### Общая проверка формата перед загрузкой

Для этого шага последовательно собрать и выполнить на Windows Release/Debug
`V5LocalRecordingWriterTests`, `NativeHashFailureTests`, `CaptureFaultStateTests`
и `DesktopUploadRecoveryTests`. Положительные случаи используют настоящий AAC
от существующего Windows V5 encoder, без устройств или внешнего сервера.
Текстовый M4A с правильной SHA и настоящий AAC другой длительности должны
давать `malformed` как с explicit root, так и без него; transport обязан вернуть
`invalidPackage` до первого send. Независимый проверенный WAV и доверенный
degraded фрагмент сохраняются, файлы не удаляются. Корень ограничивает playback,
но не освобождает metadata-only/upload callers от проверки формата.

Переносимая сборка не подтверждает AAC: положительная серверная матрица этих
двух upload tests выполняется на Windows, переносимые ветки проверяют отказ
без отправки и сохранность файлов. Штатный helper проверяет native AAC subtype,
48 кГц, mono и длительность контейнера; это не полный proof AAC-LC/payload/EOF.
Полная защищённая цепочка T116, переход T117, приёмка T118 и H250 всё ещё открыты;
данная проверка не разрешает установку или запуск на рабочем профиле.

## T116: проверка полного защищённого V5 vertical — план 2026-10-07

До независимого requirements/analyze допуска этот сценарий не запускается
и не считается реализованным. Использовать отдельный private fixture root,
искусственные samples и настоящий NativeCapture/controller; рабочие записи,
микрофон и аккаунт не нужны. Peer заменяет device audio, не storage authority.

1. Genuine store/package factory: private exclusive directory/IDs, capturing
   BOTH g1 ACK до canonical bytes; никаких plaintext float/media/manifest файлов.
2. Real controller.record/worker-ready/dispatcher: ≥3000 10-ms кадров; не
   использовать synthetic begin с прямым markReady. Проверить block cadence.
3. Stop → two EOS → dispatcher fence → close timeline → async finalizer:
   logical WAV/AAC, actual MF stream (не fake encoder), exact hashes/refs,
   manifest последним, sealed package-state. Пока queue commit/ACK нет — pending.
4. One full protected insertion commit/adoption → current-epoch saved;
   холодный restart подтверждает BOTH slots и immutable artifacts. Потерянный
   poll/stale epoch не дают effects и не освобождают native lease раньше terminal.
5. Birth cuts/ACL/races, budget refusals, cancel before/after publish, ambiguous,
   MF concurrent/late calls и shutdown: artifacts сохранены, нет false saved,
   открытой запасной копии, auto-repair partial birth или premature short purge.

Native Release/Debug и SDK caller build связываются с новым exact source map/EXE;
старые SOURCE277 receipts не подтверждают этот сценарий. Generated ≥30s — число
кадров, не 30s real audio, не 60min/hardware/AEC/installed/public release proof.

## T116: защищённая отправка — RED/приёмка 2026-10-10

Prerequisites: независимое принятие конструкции в `plan.md`, раздел «T116:
защищённая HTTP-отправка и принятие результата», generated private root,
actual NativeCapture vertical выше, без реальной сети/микрофона/аккаунта.
Подменяется только send; production transport и scheduler/worker продолжения
остаются настоящими. Старый plaintext upload должен дать RED на таком пакете.

1. ≥3000 generated кадров → insertion commit/adoption → освобождение прежних
   owners → cold discovery → real upload → один result commit/adoption → restart.
   Проверить прежнюю последовательность sync/create/session/missing/PUT/finalize,
   exact logical bytes/hash и отсутствие plaintext manifest/WAV/M4A на диске.
2. Parts64KiB/4MiB/16MiB, tail, невыравненный missing range, restart accepted
   ranges: exact offset/length/index/digest; invalid/out-of-bounds до PUT.
   Большие части проверяются на generated protected fixture, не реальном аудио.
3. Wrong session/directory/ref, degraded/discard, повреждение обязательного
   member, short read/EOF/hash failure: нет некорректного PUT/finalize/fallback.
4. Пока result commit pending, flight/result/busy/lease удержаны и projection
   прежняя. Проверить not_committed/ambiguous, lost poll, repeated ACK, stale
   epoch/row before и after publish, shutdown/native drain и cold server truth.
   Отдельно prepare без изменений строк, но с непустым выбором: zero HTTP до
   обычного full commit/adoption ACK; generation продвигается ровно один раз.
   Пустой выбор не выполняет commit/network. Это не новый fifth ticket state.
5. Cancel до inspection, между reads и перед/во время send; shared64MiB/pins/
   jobs/Debug allocation refusal: нет partial PUT, копии body вне квоты или
   раннего last native release. Длительный send не блокирует EOS/finalizer.

Проверки добавляются к existing NativeCaptureStorageIntegrationTests,
DesktopUploadRecoveryTests и DesktopUploadCustodySmokeTests; запуск через
`ctest --test-dir <build> -C <Release|Debug> --output-on-failure` по точному
source manifest. До реализации и фактического выполнения это сценарии, не PASS.
Direct reader/transport PASS без queue continuation не закрывает T116.
Global admission и остальные installed/hardware/release gates не открываются.

### T116: конкурентная запись при cold inspection

Дополнение 2026-10-11 к существующему generated-data integration fixture:
не заменяет полные integrity/hash/AAC проверки, прежние HTTP/result cases или
аппаратную60min матрицу. Ни устройства, ни рабочие записи не используются.

1. После настоящего prepare/adoption ACK удержать one-shot integrationRead
   внутри nonempty read content.packed-v2 выбранного старого пакета на offset
   ≥ ProtectedPackedCustodyFormat::appendOffset. Сохранить реальный результат
   и LastError. Маркер подтверждает packed inspection IO без private path,
   не заявляет hash/AAC caller без отдельного наблюдения.
2. При удерживаемом cut запросить новую запись через actual NativeCapture.
   Проверить reached-prepared, а не только accepted/queued. Для старого пути
   ожидать именованный RED именно этой проверки после подтверждения cut;
   factory/build/произвольный timeout не являются квалифицированным RED.
3. Для активной generated записи отдельно наблюдать обслуживание finalize
   после Stop. Не ждать полного финала под закрытым Reader cache/Guard cut:
   освободить cut, затем проверить EOS, sealed state, commit/adoption и restart.
4. Cancel/logout/shutdown внутри inspection: wire0 до нового допустимого
   retry, без invalidPackage/ложного успеха/раннего release. Проверить lost poll,
   busy/flight/native drain и возврат owned memory/pins к фактической базе.

Запускать существующий NativeCaptureStorageIntegrationTests последовательно
в Debug/Release с отдельным generated fixture и точным source manifest.
До реализации named case и фактического выполнения это план проверки, не PASS.
Кооперативная отмена не доказывает верхнюю границу одного native вызова;
общий storage admission и внешняя приёмка остаются закрытыми.
