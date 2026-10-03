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
