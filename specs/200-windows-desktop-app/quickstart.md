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

Для T097/T109 отдельно выполнить в точном установленном MSIX настоящий путь
настроек уведомлений, без подставного `webkit` и ответов из browser fixture:

1. В согласованном тестовом аккаунте открыть `/desktop/settings/notifications`,
   дождаться native read и записать исходный выбор «Тихий режим». Не считать
   снимок страницы или поиск обработчика в исходниках выполнением сценария.
2. Изменить «Тихий режим», дождаться подтверждения сохранения, перейти в список
   встреч и вернуться. Повторный native read обязан показать сохранённый выбор.
   После обычного перезапуска приложения проверить его ещё раз в том же scope.
3. Вне записи, при разблокированном экране и без занятой важным сообщением
   карточки нажать «Проверить уведомление»: одна native-карточка, явный результат
   на странице, без начала записи/серверной отправки. Отдельно занятая карточка
   не заменяется проверочной; страница объясняет отказ. Проверить также
   управление с клавиатуры. Вернуть и повторно прочитать исходный выбор.
4. Отдельная синтетическая native-проверка должна удержать старое settings
   сообщение, заменить документ и доставить его с прежним nonce: нет мутации
   или ответа в новый документ; свежий документ может прочитать настройки.
   Не выполнять внедрение сообщений в рабочий аккаунт через консоль браузера.

PASS требует всей цепочки page → WebView2 → AppMain → сохранение → новый read;
mock browser tests и отдельные parser/presenter tests её не заменяют. Для
вывода о паритете тот же пользовательский сценарий проверяется на Mac.

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
   Со скрытым главным окном «Настройки» должны открыть то же окно на
   `/desktop/settings/account`. Затем «Встречи» возвращают к списку того же
   кабинета, без открытия внешнего браузера. «Начать запись» работает только
   при готовности; повтор не создаёт вторую запись.
   [Проверка настоящего меню Windows и маршрутов T111](validation-2026-11-06-t111-tray-cabinet.md)
   покрывает компонент меню и выбор адреса, но не установленное окно.
   [Проверка нативной карточки T110](validation-2026-11-06-t110-notice-foreground.md)
   подтверждает поведение компонента; эти шаги повторяются в установленном MSIX.
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
   Из трея открыть окно «Обновления GRAF» со светлой и тёмной темой кабинета.
   Не закрывая окно, сменить тему, затем включить и выключить высокую
   контрастность Windows. Проверить фон, текст, рамку и системные кнопки
   заголовка, в том числе при неактивном окне и масштабе 200%. При отсутствии
   источника нет кнопки установки. Возврат главного окна из трея подтверждать
   видимостью того же окна, а не временной диагностической строкой.
   [Проверка регистрации установленного пакета и нативного контроллера T112](validation-2026-11-06-t112-update-source.md)
   не заменяет ручную проверку окна и испытание подписанного канала обновлений.
   [Проверка заголовка нативного окна T097/T112](validation-2026-11-06-t097-update-chrome.md)
   подтверждает вызовы Windows; внешний вид проверяется на установленном MSIX.
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
| Completed migration discovery | После BOTH protected/null bootstrap — genuine cold Native/StoreOwner startup, без caller transaction: independent native-authenticated birth задаёт expected transaction current slots, strict current задаёт expected birth; conflicting copies/refs/roots блокируют effects. Whole positive generated legacy fixture сохраняет IDs/exact bytes/originals, затем обычная queue mutation и ещё один cold open; historical copy generation не фиксирует текущую очередь. |
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
| Native Resume handshake T120 | exact S_OK same-client clock, immutable early T0/L и checked B/prefix; только q<L остаётся pending в исходном1s, errors/S_FALSE/future/backward/identity/overflow отклоняют; retry той же odd epoch получает новые seq/T0/L и не принимает late seq; Stop/исключения освобождают READY; committed accepted не отменяется поздним deadline; floor-ms сохраняет порядок быстрых OPEN/CLOSE |
| Fixed-fence RED T120 | в реальном mailbox/controller T0=105ms и L>105ms; q104ms pending, затем q106.5ms/p5112 при новом before110ms даёт B5113@48k; unread frames4800..5279: prefix0, suffix только после B; нет pre-T0 сигнала, CLOSE105ms, не110ms/ACK; system/PTS/count/AEC сохранены |
| Fence integer/pending edges | отдельно проверены ceil-tick/100ns/строгий порядок и overflow L, q=L−1/L/after/after+1, F change; stale до timeout и continuous paused producer не двигают seq/L/T0/deadline, не удерживают buffer; отдельные Stop до/после commit, retry/late result и failed CLOSE |
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

### T116: Start-owner и аварийное восстановление — 2026-10-16

Existing generated-data NativeCaptureStorageIntegrationTests, без устройств,
рабочих файлов, installed app/внешней сети; serial Debug/Release, exact source
manifest/PE. Сначала квалифицированный RED старой реализации, затем GREEN.

1. Account A: удержать настоящий metadata publication/readback до первого ACK.
   Пока cut удержан: audio admitted=0, package/writer factory не вызвана.
   После full commit/adoption actual protected row содержит captured A/IDs.
   Cancel/lost poll/exit/update и A→B на каждом cut не дают stale start/Saved.
2. Crash до/после queue publication, readback/adoption, package birth/первого
   checkpoint, Stop, seal и row update. Новый genuine owner читает исходные
   IDs/owner; отсутствующий/partial пакет не достраивается автоматически.
   Synthetic success ticket не является доказательством durable ACK.
3. Sealed-normal Start row восстанавливается без нового UUID/второго enqueue;
   A не превращается в B. Full hashes/session/AAC и deletion/server-truth fences
   предшествуют update/readback/adoption. Capturing/finalizing принимают только
   complete480 prefix; zero/partial/key/quota/IO/ambiguous не дают normal и не
   удаляют артефакты. Return-to-baseline pins/jobs/memory проверяется отдельно.
4. Proven signed-out: marker остаётся, scheduled/auth/wake дают HTTP0; после
   full sealed-normal proof прежнее manual подтверждение назначает одну row
   текущему verified account одним commit/ACK. Cancel/stale/другая row/degraded
   не назначают owner. Unresolved /auth/me, default пустой token до bootstrap,
   failed cookie read → unknown marker, local Record разрешён, claim/HTTP0.
   На настоящем host callback отдельно проверить valid empty cookie read,
   reconciled=false, stale document/nonce/Source, expired session, workspace
   reselection и calendar authRequired: только valid current empty cookie read
   доказывает signed-out. Актуальные unreconciled/expired/reselection/calendar
   authRequired отзывают прежнюю authority и дают unknown, не разрешая claim.
   Stale document/nonce/Source callback игнорируется без изменения более нового
   auth/ownership state; оба исхода проверяются раздельно.
   Legacy missing fields/row/старый capture_interrupted не становятся no-login.
5. Short после EOS/drain: actual positive intent и exact Start row; другой
   alias/owner/remote range/deletion intent блокируют retirement. До queue
   retirement ACK OS effect=0; после него unchanged no-alias discard требует
   actual absence/adoption. Crash между шагами, плохой readback, readonly retry
   и lost poll не дают blind recycle/раннюю notice. Прежние Round430 no-row
   cases повторяются без ослабления guards/исчезновения deletion operations.
6. Native active/pending row закрыта от send/delete/playback на worker и не
   показана как готовая/испорченная. После restart — честное interrupted/unbound/
   unknown состояние через current auth/UI gate без раскрытия чужих owned данных.
   Повторить existing read-model/manual/local-delete/server-purge regressions
   и disk snapshots без plaintext temporary content.

Это existing T116/#7444, не новый task и не закрытие T117/T118, SC-003/005,
installed UI, physical x64 или release gates.

## T116: cold complete480 prefix, construction A — 2026-10-16

Только generated audio в отдельном временном root, без microphone/HTTP/MSIX.
Сначала executable RED на отсутствии нового reader в существующем Windows
package test; затем actual rebuild/тот же GREEN. Не ослаблять normal inspector.

1. Genuine package birth/canonical write/checkpoint, освобождение всех исходных
   writers/store/package owners, fresh StoreOwner и его cold BOTH pair. Проверить capturing и
   finalizing отдельно; sealed normal/degraded/discard не принимаются этим API.
2. Committed canonical содержит целые480 frames и неполный хвост: вернуть
   floor(logicalBytes/1920), tail не дополнять/перезаписывать. Отдельно
   недолговечный dirty tail не должен попасть в prefix. Проверить finite samples
   целого prefix; NaN в нём — отказ. Нулевой/меньше1920 bytes — отказ.
3. Плохой/отсутствующий peer package metadata или packed head, отказ allocation/
   native job/pin, cancel/null owner — без результата и записи.
   API не принимает caller-supplied root/Pair; root только из actual StoreOwner.
   Полный BOTH-reader не заменять одной здоровой веткой.
4. До/после каждого cold вызова сравнить regular-file paths и SHA всего test
   root; отсутствие factory/checkpoint/manifest/output/queue changes. После
   actual last release проверить native jobs/pins/owned memory against baseline.
   Proof не должен быть доступен normal upload/playback bridge по типу.

Точный результат — проверенный retained complete prefix, не восстановленный
проигрываемый пакет и не native startup acceptance. Construction B и общая
приёмка T116/T117/T118 остаются открыты.

## 2026-10-16 / T116 construction B acceptance

На generated Windows fixtures создать настоящие capturing/finalizing пакеты,
checkpoint cleaned canonical с полным prefix и неполным хвостом, bound manifest
с OPEN/CLOSE privacy, освободить всех исходных owners. Fresh owner → terminal
V5 recovery должен дать sealedDegraded, exact prefix duration, сохранённую
session/history/known times и декодируемый AAC/WAV. Canonical file SHA/size и
queue/owner unchanged; fresh cold full inspection подтверждает тот же результат.
Ни append после recover, ни normal/upload promotion не допускаются.

Отдельно проверить unused identity-only roles против partial/missing identity,
started content, singleton/bad peer/orphan metadata, ref только в peer package
slot, selected metadata newer than bound manifest, malformed history/session,
zero/nonfinite prefix и cancel/job/pin/memory refusal. Отказ до эффектов не
меняет files; после возможного publication сохраняет artifacts и требует fresh
reconciliation, не повтор factory. Каждый publish/rollover/final ACK crash cut
записывается отдельно; непроверенный cut не считается пройденным. Повторить
V5 writer и шесть существующих native/codec/revalidation regressions. Это не
installed-app, hardware, account E2E или release acceptance.

## 2026-10-16 / T116 — native startup B, раунд448

В NativeCaptureStorageIntegrationTests создать generated capturing/finalizing
пакет с checkpoint canonical и настоящей durable Start reservation владельца A.
Освободить все birth owners; запустить actual storage validation/ACK при current
account B. Дождаться recoveryDone, не одного callback. Fresh cold inspect должен
доказать sealedDegraded, exact prefix duration/AAC; canonical и вся служебная
очередь неизменны, original owner A, mutation ticket/HTTP отсутствуют.
Проверить отказ started outputs и deletion/changed reservation без перезаписи;
остановку и actual native retirement. Задержать canonical read существующим
test cut: Start/Stop новой записи должны завершиться до освобождения старого
recovery cut. Повторить прежние normal recovery/degraded restart/live playback,
revalidation, consumer и V5 тесты. Метаданные/звуки только искусственные.
Quarantine UI playback, настоящие устройства, installed package и release
не считаются принятыми результатами этой узкой проверки.

## T116 / owned-degraded local playback (раунд451)

На genuine cold B fixture проверить сохранение original A при current B:
невидимость/отказ open, затем actual account resolution A, display canOpen
только после verified playable degraded, Send=false. Через прежний native player
muted play должен продвигать позицию; проверить pause/seek и неизменные queue,
package, owner, ноль app HTTP. Повторить отказы без display proof, при active
reservation, deletion/auth/document invalidation, unfinished/started/corrupt и
неplayable degraded; actual retirement до purge. Использовать existing
NativeCaptureStorageIntegrationTests и CalendarJoinHostTests, generated media,
отдельные RED/GREEN source manifests и реальные process exit codes.
Это не закрывает T116 целиком, T117/T118, installed или аппаратную приёмку.

## T116 / явное назначение настоящего no-login Start (аудит453)

Положительный fixture должен пройти настоящий accepted signed-out observation,
Start reservation ACK до writer, generated capture/EOS и normal finish ACK.
Проверить сохранённые empty owner pair + quarantined/capture_prepared, HTTP0 и
cold restart до входа. Ordinary unowned pending row через enqueue не заменяет
этот fixture. После actual account resolution общая страница показывает строку
«Не назначена» только с актуальной normal inspection. «Отправить» открывает
native confirmation; отмена сохраняет прежние bytes/owner/queue и HTTP0.
Подтверждение назначает одну exact row текущему user/workspace одним commit/ACK;
проверить pending/lost poll и HTTP0 до adoption, затем настоящий upload consumer
с подменой только сети и повторный cold read принадлежности.

### T116 / P2: полностью записанный recovery до final seal (раунд457)

На generated canonical воспроизвести actual returned failure перед последним
package-state rename (тот же named boundary раунда456), освободить failed writer
и все старые proofs. Fresh StoreOwner/recovery должен проверить BOTH, завершённые
WAV/AAC/manifest/recovery и original privacy/time, опубликовать только package
generation+1 sealedDegraded и пройти настоящий cold full inspector/AAC. Сравнить
хеши всех пяти role members и native IDs до/после, queue неизменна; проверить
повторный cold recovery sealed без эффекта. RED сначала, затем GREEN на точном
source/PE с actual test log. Partial birth, invalid peer и неизвестные orphan
по-прежнему сохранённый отказ; narrow GREEN не закрывает весь P2/T116 и не
заменяет public Record, installed UI, hardware или release acceptance.

Отдельно проверить unknown/legacy, degraded/unfinished, alias/deletion/server
identity, active reservation и stale document/account до и после ожиданий.
Подмена display scalar не должна разрешать native claim. Cancel/IO/quota до
публикации оставляют запись неназначенной; ambiguous publication принимается
только через physical reconciliation, без повторного claim/чужого HTTP.
Длительная inspection не задерживает другой accepted Start/Stop/finalize;
actual readers/native jobs drain предшествует terminal. Owned manual-send,
playback/deletion регрессии и memory limits сохраняются. Source/PE, generated,
installed UI и аппаратные доказательства фиксируются отдельно.

### Public protected Record — T116 / P3 (раунд458)

В существующем NativeCaptureStorageIntegrationTests выполнить public record
после genuine startup/adoption. Ожидать accepted starting, reservation commit/
adoption до private factory и первого generated блока, затем прежние Stop/EOS/
finish/cold WAV/AAC/bytes проверки. Не обходить вход через private continuation
и не устанавливать storageWritable. Real native probes читают только метаданные
устройств/permission/AAC; acquisition workers заменить generated функциями после
accepted starting до pollHealth. Ни Start/read настоящего аудио, ни real HTTP.
Сохранить signed-out/unknown ownership и повторный Start rejection. Pending/
ambiguous/unadopted/error storage не допускает Start; clean update drain
сохраняет queue completeness, но не новый capture. Фиксировать точный RED,
финальные source/PE и затронутые регрессии отдельно от installed/hardware gates.

### T116 / P2: готовый WAV до AAC (раунд461)

После независимого checklist/analyze выполнить новый CLI existing
V5LocalRecordingWriterTests `--cold-recovery-wav`: настоящий child cut
role1/op6 с exit88, затем fresh recovery на старом source должен дать RED
на positive assertion. Это не тест возврата checkpoint ACK. После реализации
повторить тот же CLI на frozen source/PE: actual full cold sealedDegraded/AAC,
1000ms, semanticVerified/trustedPrefixRetained, normal/keepable=false;
canonical, готовый WAV, native IDs и queue hashes неизменны. Получить BOTH
manifest/history и actual inspection после освобождения recovery writer.

На отдельных таких же generated fixtures проверить сохранённый refusal и
полное равенство disk snapshot: неизвестный media physical tail; корректно
защищённый WAV с изменённым PCM при прежнем header; повреждённый/partial HEAD
peer; начатые playback/recovery; cancellation. Никакого truncate/перезаписи
существующего WAV или retry после возможной публикации. Затем прежняя полная
crash matrix (только доказанные WAV точки меняют ожидание), returned-fault,
terminal completion и затронутые native tests на одном source с actual logs.
Сохранить RED/GREEN, manifest/PE/exit/no-skip/source guards. Ни device audio,
ни real HTTP, ни установленное приложение этот срез не проверяет.

После сохранённого WAV29 RED дополнительно выполнить role1/op5 — crash после
полного native HEAD WriteFile до flush. Wrapper обязан assert полный transfer.
Для этой контролируемой fixture обязательны те же positive checks, что op6:
полный fresh proof, degraded/AAC/history, неизменные WAV/canonical/IDs/queue,
ресурсы и отсутствие normal/keepable. Полная matrix24 cuts, continued4 (два
WAV и два terminal); filtered op6 CLI всё ещё executed1/continued1 плюс7
refusals. Нельзя заменить это на «любой результат подходит» или вывести
исторический flush ACK из готового содержимого. Остальные started cuts и
refusal guards неизменны; no retry same owner, no repair, power_loss=0.

## Раунд462 / T116: начатый AAC — будущая приёмка

До кода: plan462/research/data-model/packed contract, независимая оценка
cold-prefix CHK035–041, scoped analyze C0/H0; прежняя T116/#7444 остаётся открытой.
Existing V5 executable/child crash harness: сначала actual RED после полного
playback HEAD flush на прежнем source, exit88/actual wait; затем тот же GREEN.
Build failure/timeout/skip не RED. Positive: canonical/WAV/IDs/queue прежние,
prefix и bytes [appendOffset, oldActualEOF) playback побайтово прежние, EOF не
уменьшился; full fresh cold degraded/AAC/privacy/optional times inspection,
normal=false/keepable=false/original owner/HTTP0; readonly reinspect не пишет.

Нужны valid empty birth, orphan DATA, HEAD WriteFile до flush, готовый unsealed
AAC до metadata; повторный crash reset/append/HEAD/metadata/final seal с exact
предзаданными outcomes, не «успех либо отказ». Старый24-cut regression сохранять.
Авторитетная конечная таблица — plan462, раздел462-U1 (R/C/D/S). Empty→0
сохраняет generation/bytes, reset-HEAD cut для него отсутствует; nonempty→0
требует+1. Для каждой новой fixture до запуска выбрать строку таблицы; после
actual failure не заменять её на несколько допустимых исходов. Newer-unbound
manifest/metadata orphan → D; terminal-bound при exact unused recovery → U
по plan468-U2 (до его реализации D); full terminal
recovery → C; sealed package → отказ recover и отдельный readonly S.
Отдельно actual MF partial AAC с committed logical size>256KiB, не short flush
или synthetic substitute. Incomplete birth/torn HEAD/metadata остаются отказом
и открытой работой P2. Прежние guards/timeout без новой конструкции не повышать.

Preflight negatives plan462 → whole-tree hash equality. Returned native/short
IO/flush/readback/DPAPI/hash/quota/cancel faults → sticky failure, original bytes
сохранены, no retry/normal/cleanup. Повторить V5/WAV/completion/returned-fault/
tree/files и затронутые native suites на одном source/PE; полные logs/JUnit/
receipt/no-skip/post216/owned0. Generated VM не принимает device audio,
installed UI, физический x64, accessibility или выпуск.

Уточнение464 (bounded WAV32): для первого сравнения кандидата использовать
`ctest --test-dir <build> -C Debug -R '^ProtectedRecoveryPlaybackPartial$' --output-on-failure`.
Тот же6000-frame generated fixture, serial180s/child60s, source216/PE/postflight,
полные JUnit/log/receipt и owned0. Проверять фазовые elapsed_ms, но успешность
определять прежними assert: реальный partial>256KiB/<complete, codec failure,
полный60000ms degraded recovery, old extent/IDs/queue/history/privacy неизменны.
Короткий100-frame пример проверяет последнюю неполную32-frame порцию,
6000 кадров — также неполную последнюю порцию; неверный WAV PCM/EOF и отмена
обязаны по-прежнему отказывать. Ни один допуск/таймер не повышать.

Уточнение465: тот же `ProtectedRecoveryPlaybackPartial` и срок180/child60
для canonical read-ahead32 в writePlayback. Нужен финальный маркер
`COLD_PARTIAL_RECOVERED`, а не только intermediate `partial_recovered`:
все последующие сохранность/fresh cold/privacy/history/readonly/resource
assert должны дойти до конца. Short100-frame проверяет последний refill4,
long6000 — последний refill16. Сохранить отдельные10ms MF samples, exact-count
каждого refill и отмену/output-fault checks на каждом sample. Прежние FAIL/
TIMEOUT не удалять и не заменять новой успешной записью. Затем full affected
regressions на одном source; hardware/installed/UI/release остаются отдельно.

## 468-U2 / T116: terminal manifest, recovery exact unused

До test edits независимые cold-prefix checklist/scoped analyze C0/H0, затем
actual test-diff gate. В existing V5 repeated-crash harness filtered cut13:
сначала фактический child exit88 после bound terminal publication с exact
recovery id.bin, затем свежий recover обязан дать U по plan468-U2. Старый
source — meaningful RED только по этому positive assert. Timeout/build failure
не RED. GREEN требует full cold degraded/AAC/privacy/times proof; четыре готовых
member, IDs/queue/owner неизменны, readonly sealed reinspect не пишет.

Зарегистрировать отдельные anchored CTest filters в том же executable для
terminal-unused positive, шести repeated physical cuts и returned-fault cases;
не менять limits/форматы/encoder и не использовать текущую запись пользователя.
Шесть cuts — до/после recovery index0, index1 и final package publication —
имеют фиксированные D/D/D/C/C/S. Repeated19: R9/D6/U1/C2/S1; прочие18 исходов
сохранены. Exact physical shape/role/op/child wait/exit обязательны, не один
номер. Negative preflight и sticky post-effect faults — plan468-U2.
В старой24-cut fixture U применяется только к тому же доказанному shape cut18
{package-state,op3}; прочие23 исхода не меняются.

На final source/PE последовательно повторить затронутые V5/completion/WAV/
playback/49 faults/old24/repeated19/long и native regressions: полные actual logs,
JUnit/receipt, no skip, source216 до/после, PE hash и owned0. Новая запись
recovery имеет genuine g1 BOTH readback до final seal; preflight JSON только
value, не fabricated proof. Старые AAC47/56 TIMEOUT сохраняются нерешёнными.
Ни один PASS не закрывает T116, installed/hardware/accessibility/release gates.

Для dispatch469 проверить не только successful U: normal empty/partial/full и
orphan playback tail должны сохранить прежний путь R; terminal с invalid
binding/peer/session/privacy/times должен дать неизменный D без приобретения
writable audio. Source tracing обязан показать bounded metadata classification
ДО первого openUnfinished, отсутствие fallback terminal→R, освобождение всех
временных metadata leases и повторную полную проверку на recovery executor.
Прежние AAC60 RED и AAC47/56 TIMEOUT не заменять новыми утверждениями.

## T104: временная недоступность календаря — 2026-10-21

На синтетическом календаре показать A, оставив B непоказанным. HTTP408/429/5xx
без ошибки транспорта и WinHTTP12002/12007/12029 сохраняют только видимую A с исходными identity,
generation, wall/steady expiry и единственным звуком; меню недоступно. Закрыть A
или дождаться любого исходного срока: B не появляется до нового успешного
снимка. Повтор ошибки не продлевает срок. Исчезновение/перенос A в новом снимке
закрывает A; поздний ответ другого контекста ничего не меняет.

Отдельно проверить definitive отказ/неверный JSON/context, status0 без известной
причины, TLS/12030/отмену, приоритет401/403; quiet/reminders-off, запись, lock/вытеснение
и смена owner/workspace/origin немедленно снимают A. Проверка Record после сбоя
не остаётся навсегда pending и не запускает запись по старому ответу. Проверить
передачу nativeError обеих HTTP стадий без настоящей сети/аккаунта/аудио. На
точном установленном пакете повторить показ, срок, клавиатуру и восстановление;
portable/native unit PASS не равен этой приёмке.

Для successful JoinAndRecord после временного сбоя проверить три синхронные
handoff-проверки, затем очистку при успехе/раннем возврате/исключении. Старый
target после cleanup больше не current; новый context/snapshot при повторном
входе не удаляется. Close/Join без Record/expiry не получают этого удержания.

## T103: same-URL permit-race, исследование 2026-10-22

В существующем isolated native runner добавить `history-race-native-first` и
`history-race-script-first`, не менять прежние23. Оба проходят подготовку
GET-S/POST-S/GET-C/новый GET-S/GET-C с distinct entry IDs. Native выбирает новый
GET-S, script из C делает go(-3) на POST-S; одновременно ожидаются обе команды
и два BackOrForward события. Наблюдать ContentLoading/Completed, финальный ID
и marker. Один URL не доказывает выбранный entry; POST count=1 не исключает
cached POST restore. Итог REFUTED/INCONCLUSIVE остаётся ненулевым результатом.

PASS только если оба конкурента действительно достигнуты, safe entry разрешён,
unsafe отменён и финальный GET identity подтверждён; он относится лишь к
наблюдаемому порядку. Исследование не даёт production GO и не закрывает T103.
Текущий опыт negative-only: target отменённого события независимо не установлен,
поэтому пути PASS нет. Найденный POST-entry сразу означает REFUTED даже при
ошибке DOM; safe GET без полного proof означает INCONCLUSIVE, а не успех.
Не использовать настоящий кабинет, учётные данные, устройства или установленный
GRAF. Сборка fresh /W4 /WX, GUID profile, source216 pre/post, точный PE SHA,
server drain/POST count и owned0 обязательны; limits прежнего runner неизменны.

### T103: выбранная безопасная история — tests-first, 2026-10-22

После независимого requirements/checklist/analyze gate сначала RED→GREEN
SafeHistory в существующем WebViewRoutePolicyTests. Проверить actual ordered
nearest-distinct GET BF; meeting Back filter; карантин при POST/unknown в ЛЮБОМ
месте (включая другой URL/forwardList); новый GET не реабилитирует old POST ID;
rename/replace/new ID не наследуют proof; stale snapshot/revision/session clear;
duplicate/negative ID/index/bounds/malformed snapshot не оставляют старый выбор;
reset не даёт proof другой оставшейся записи. Policy PASS не принимает host.

Перед native integration — source review. В synthetic loopback проверить
accepted GET → reset → exactly same singleton ID/URL и unchanged generation,
невозможность BF/new-document во время reset, ошибки API/metadata сохраняют
карантин; потом полезную actual all-GET историю. Подготовить POST другой страницы,
replaceState в URL safe GET/pushState/back: никаких POST replay/restore/authority.
Fallback из встречи делает fresh list + не более одного fresh forward; ошибка/
посторонний переход/session boundary отзывает его. Все испытания работают через
реальные production handlers/latch, не ручной nonce/fake document finish.
Default23/control/race evidence сохраняются раздельно. Не заявлять installed
parity по policy-only или запуску процесса; T103/T088/T097 остаются открытыми.

### T103: default23 после ALL-entries integration

Применять явную migration matrix из последнего раздела plan.md. Все23 IDs
исполняются, без skip/xfail/исключений в host. history-get и opt-in
history-host-get сохраняют positive actual all-GET selected-ID/DOM/GET/bridge.
history-post/history-host-same-url принимают только fresh-list/reset/fresh
singleForward, не старые IDs. history-entry/entry-same-url проверяют production
отмену unsolicited CDP через историю с POST до begin/replacement, без fixture
Cancel; текущий документ/ID/generation/bridge остаются. cancel-history-host
использует all-GET preparation и fixture-owned раннюю BF cancellation, не
отмену fallback вместо BF. cancel-history-script остаётся отдельным fixture
lifecycle control; same-document authority не доказывает GET proof mutation.
Остальные14 auth/transport/TLS и cancel-before-start сохраняют смысл.
Подсчитать counts для каждой новой последовательности; прежние default23
PASS, новые mechanism API PASS и production regression PASS не смешивать.
Initial opt-in history-host-quarantine проверяет настоящий host fallback/reset/
singleForward без fixture fence. Дополнительно нужны все семь групп plan,
включая pending/races/session/terminal-ID BEFORE latch/nonce, не только эти
два положительных initial cases. SOURCE review и meaningful old-host RED
предшествуют изменению host.

### T103: controlled native continuation slice

После independent requirements/analyze gate из нового раздела plan выполнить
pending-read-fence и terminal-held через один SDK-only friend fixture в прежнем
native test. Задерживается только настоящий production snapshot continuation,
результат не изменяется; stage/proof/session/nonce не выставляются вручную.
Pending case требует доставленных BF/GET/POST competitors с отменой до begin,
без замены current ID/generation/authority, затем полезного выбранного BF.
Terminal case удерживает snapshot после настоящих response/completion:
до delivery нет нового latch consumption/nonce/auth/bootstrap; после delivery
настоящий GET принимается и bridge действует. Никакого fixture Cancel/fake finish.
Default23/initial2 неизменны; группа2 после допуска, оба response delivery
порядка, reset intervals/errors, prepared session/mutation и прочие группы
остаются отдельными проверками. SOURCE/PE/GUID/owned0/deadlines прежние;
прохождение этого среза не означает полную T103/T088/T097 или release приёмку.

### T103: own fresh-list redirect к форме входа

После независимого bounded requirements/analyze gate выполнить один opt-in
native scenario из нового раздела plan: actual GET detail/рабочий bridge →
actual host Back/fresh GET list → реальный HTTP302 internal login next=list.
Проверить принадлежность redirect тому же NavigationId, final GET response/
completion, видимую редактируемую форму входа, authRequired без native authority
и сохранение synthetic input. Counts строго `2 1 0 1 0 0`, без POST/replay;
четвёртое поле сохраняет прежний смысл safe login next, не число HTTP-запросов.
Нельзя выдать разрешение по URL, fabricated response или fixture Cancel/finish.
До исправления нужен meaningful native RED, после — тот же unchanged GREEN;
source/PE/runtime/owned0/deadline receipts обязательны. Все прежние27 сценариев
и остальные acceptance группы сохраняются отдельно; это не UI/release PASS.

### T103: устаревший readback после reset и изменения истории

После bounded requirements/checklist/analyze и SOURCE review exact bytes
запустить opt-in `history-reset-stale-readback` по разделу plan: AGET/POST-B/
CGET → actual Back/fresh-list → настоящий reset ACK и удержанный singleton
readback → actual pushState/независимо подтверждённый новый current entry →
доставка неизменённого старого ответа один раз. Требуются unavailable/
history-mutation без новой activation/bridge/cookie reconciliation и без
восстановления stale proof. Затем новый native navigate(list)/GET с новым ID
должен восстановить обычный кабинет/bridge без старого singleForward.
Strict counts `4 0 0 0 0 1`, no replay. Нельзя подделывать snapshot/ACK/state,
блокировать original activation wrapper или считать BF без Starting проверкой.
Сохранить28 прежних сценариев и все сроки/изоляцию/контрольные суммы. Безопасный
PASS на прежнем host допустим: это отрицательная регрессия, не обещание нового
дефекта. Это не полная reset/session матрица и не установленная UI/релизная приёмка.

### T103: контекст меняется во время reset — без вечной загрузки

После bounded requirements/checklist/analyze и SOURCE review test3 выполнить
history-reset-account-boundary по plan: реальные AGET/POST-B/CGET, непустой
синтетический browser cookie, workspace A→B через публичный bind при удержанном
настоящем resetting readback после ACK. До recovery требуется unavailable
не позднее5с, отозванные proofs/authority и отсутствие дополнительного HTTP.
Доставить исходный ответ один раз: старый контекст/authority не воскресают.
Затем штатный host.reload() должен дать настоящий GET-list, новый nav/generation,
ordinary ready/reset/singleton и bridge3→4; cookie3→4, signed-out/invalidation0,
activation0→1, strict counts4 0 0 0 0 1. Новый числовой entry ID не обязателен.
Бесконечный initializing обязан провалить RED до reload; после минимальной
корневой правки нужны unchanged GREEN и прежние29, включая initial200 с1GET.
Это не приёмка реального account-me, окна AppMain или полного Windows-приложения.

### T103: смена workspace до HTTP-ответа, позднее перенаправление

После bounded requirements/checklist/analyze и SOURCE gate test3 выполнить
history-account-boundary-redirect-held из plan. AGET/POST-B/CGET/bridge3 → public
navigate(list)/actual unmarked GET, loopback hold до заголовков → настоящий
Starting/navigating/no response/completion → public workspace-only bind B →
unavailable≤5с ДО release, без новой HTTP/authority. Освободить actual302 и
дождаться реального same-ID redirect Starting и OperationCanceled без fixture
Cancel/GET-login/возврата loading; один marker или ранняя отмена не PASS этого
класса. Потом public reload/actual GET/new nav/generation/ordinary ready/bridge4
с B; counts4 0 0 0 0 1, cookie3→4, signed-out/invalidation0, activation0→1.
Hold≤8с/stop.request, release при любом выходе и drain/join обязательны;
сроки runner не расширять. Сначала meaningful RED, затем минимальная корневая
правка/SOURCE и unchanged GREEN + прежние30; actual Mac/Windows UI и прочие
группы/реальный сервер/звук/установленный пакет этим срезом не принимаются.

После stage26 в том же T103 opt-in уточнить метод измерения по plan:
WebResourceRequested до production не равен отправленному HTTP. После release
наблюдать только строгую synthetic same-origin GET-login Document попытку,
не закрывая host и не меняя Cancel/Response до рабочего подписчика; до release
никаких попыток. Actual server marker дополнительного запроса даёт FAIL ещё
до принятия terminal/recovery, strict counts4 0 0 0 0 1 не ослабляются.
Сначала bounded requirements/checklist/analyze и SOURCE, diagnostic RED на9308
с безопасными категориями пути/метода/origin/context, затем доказанный корневой
Document request veto, SOURCE и unchanged GREEN + старые30. Не вводить новые
tasks/framework/таймеры, не ослаблять B/no authority/same-ID redirect/terminal14/
public reload/ordinary ready/bridge4. Полное приложение этим не принимается.

### T116: проверка двух активных readers — 2026-11-03

До реализации прочитать последний раздел plan и независимое requirements/
checklist/analyze решение. На нынешнем reader сохранить причинный RED для
additionalReads0 в восьми парах с actual bytes77/42; baseline diagnostic32
не считать RED нового условия. Сборки/фикстуры изолированы; реальный звук,
сеть, установленный пакет и рабочее хранилище не участвуют.

После SOURCE GO проверить Debug ProtectedCustodyFilesTests, прежний
--cold-cache-close и новые bounded pressure/packed-hit/LRU сценарии, затем
ProtectedRecoveryPlaybackPartial с прежними CTest180/child60/fixture6000.
Успех partial требует конечного COLD_PARTIAL_RECOVERED и всех прежних
cold/privacy/readonly/idle assertions. Отдельный PASS счётчика его не заменяет.
Не менять предел времени при отказе; сохранить exact source/PE, JUnit,
журналы, postflight own0 и installed EXE unchanged. Далее полный затронутый
набор на одном final source; задача T116 и внешняя приёмка остаются открытыми.


### T116: диагностика native scheduler resume — 2026-11-03

После scoped requirements/analyze и SOURCE review: только Debug Native
Integration build; existing --protected-storage-profile должен подтвердить
adapter selfcheck включая log/profile on/off и exception, затем
CTest ^NativeProtectedSchedulerResume$ с прежним240s и общим внутренним180s.
Фикстура14000frames и все прежние assertions сохранены; вывод phase entry,
returned/unwound и wall time не содержит звука/содержимого/пути пользователя.
225 source/6PE/installed before-after/own0 и отсутствие forced cleanup
обязательны даже при отказе. Нельзя складывать вложенные spans или считать
thread-local API counters активными для native worker без profile.
Сопоставить активную фазу с прошлым timeout; это диагностика, не fix/PASS.


### T116: проверка Write admission dedup кандидата

После независимых gates: сначала test-only расширение existing
packedWriterAdmission с прежним production writer, затем тот же набор
с единственным writer candidate. Normal bytes/invalid bounds, grow/shrink/
no-op, first shared fault/revocation и multi-block cancellation/MF active
close должны сохранить исходы. Test-only первый baseline не считается
performance RED: RED уже записан native resume180deadline. После candidate
existing profile1000 показывает actual native-call counts, затем original
NativeProtectedSchedulerResume14000/shared180/CTest240. Нужны terminal
source225/PE/installed/own0, никакой аудио/network/install. Улучшение не
объявлять стабильным по одному PASS; всю affected matrix закрывать отдельно.


Квалификация первого test-only запуска: требовать новый assert
warm_write_needs_only_entry_and_ack_metadata_checks, обе actual metrics
overwrite/grow и exact pending/committed bytes до него. Wrapper может
квалифицировать ожидаемый RED, но не объявлять весь Owner suite PASS: после
assert остальные cases не исполняются. Следующий production GREEN обязан
пройти full Owner suite, включая injected post-admission failure и расширенные
grow/shrink/invalid SetSize first-fault cases; deadline RED остаётся отдельным.


### T116: повтор составного large-parts correctness case

После независимого review уточнения plan и one-case CMake diff выполнить
`ctest --test-dir <build> -C Debug -R '^NativeProtectedLargeUploadParts$' --output-on-failure`.
До запуска сверить generated CTest property TIMEOUT900/RUN_SERIAL и доказать,
что остальные commands/properties не изменились. Нужен actual JUnit PASS,
полные52500frames/525000ms/media16800044 и оба exact-wire oracle4/16MiB,
cleanup/idle, source/PE/installed/own0 postguards. CLI646632ms не заменяет
этот CTest. Новое runtime свидетельство не доказывает стабильность VM времени,
SC-003, аппаратную/установочную приёмку и весь T116; прежний240s FAIL сохранён.

## T088: persistent access / offline scope — проект проверки 2026-11-04

Связь: FR-006/013/022; data-model §7.1, native contract §7, local-custody §7.1.
До кода Main согласует эту delta; дальнейшие RED/compile/Windows результаты
пишутся отдельно. Прежние bridge/receipt PASS не доказывают offline parity.
Использовать generated nonempty queue и настоящий защищённый пакет, muted
native playback, подставной transport; real devices/network=0. Не вводить новый
CLI/CMake/timer, не увеличивать прежние deadlines и resource limits.

После реализации расширений собрать существующим §2, затем на Windows:

```powershell
ctest --test-dir apps/windows/out/build/x64/Release -C Release -R "^(DesktopUploadQueueV2Tests|DesktopUploadRecoveryTests)$" --output-on-failure
ctest --test-dir apps/windows/out/build/x64/Release -C Release -R "^(NativeProtectedPlaybackConsumer|NativeProtectedDeletionApplication)$" --output-on-failure
```

Portable первый ряд проверяет codec/domain, не Media Foundation/runtime.
Новые assertions добавить в эти existing tests и существующий host lifecycle
fixture; штатные `--protected-playback-consumer`/`--protected-deletion-application`
остаются. Положительный v4 decode на старом decoder должен дать конкретный RED
invalidContent; это только первый dependency RED, не весь offline сценарий.

| Сценарий | Обязательный наблюдаемый результат |
| --- | --- |
| V4 roundtrip / old inputs | exact canonical bytes; v2/v3 дают nil access/context; pure protected reads сохраняют BOTH bytes; malformed/duplicate/overlong access/context не дают owner/empty success |
| Raw server values | owner, unknown, access_revoked, stale_device_identity/null; все nonowner блокируют; missing/null sync-state не стирает cached refusal; late upload не снимает новый конфликт |
| Same-session cold offline | полный native commit/readback/adopt owner/context → освобождение всех owners → обычный cold startup с тем же cookie и unavailable network → реальный playback/seek exact generated bytes; nil допустим при прочих gates; nonowner закрыт после restart |
| Revocation during content | полностью scope/target-valid unavailable/nonowner/receipt при удержанном upload response → cancel ДО submit; busy сохраняется до actual done+leaseReleased, нового part/recovery upload нет; late result ACK без apply; после drain lifecycle commit/readback/adopt, cold read nonowner; invalid/foreign/partial answer consumer не отменяет; already-started commit проходит reconciliation; bytes/ranges/IDs сохранены |
| Domain stale row | тот же sameUploadIdentity кроме нового access: ожидаемый owner против actual unknown/access_revoked → applyUploadResult false; запоздавший uploaded/owner не снимает refusal/receipt; нового счётчика нет |
| Fingerprint exact bytes | synthetic token generated-session-1 и заданный canonical JSON → golden SHA256; quote/backslash/control escaping, no BOM/LF, origin/token change меняет digest; workspace/clientVersion/retry/nonce не меняют; empty/unread cookie не восстанавливает scope |
| Same cookie A→B | same-URL new document запускает existing validated cookie callback даже с прежним token; same-document SPA без события обнаруживается existing scheduled recovery; несколько activation/wake/hints дают один account flight; spaces/auth-me/context подтверждают B и отзывают epoch/flight/UI; scope_changed запускает тот же путь без WebView; DOM не назначает B; transient offline не стирает local cache |
| Offline document B / cached A | source/nonce/cookie/account/route mismatch не публикует строки A и не доставляет действие open/send; cache не подтверждает network B; положительный same-document A остаётся offline доступен |
| Both / rollback / failure | new mixed v3/v4 cold read; old reader отказывает при v4 в любом slot без peer fallback; notCommitted/ambiguous не публикует права, originals/history/quarantine и T117 barriers сохранены |

После фактического освобождения memory/jobs/pins/leases возвращаются к baseline.
Receipt остаётся monotonic, без receipt нет deletion/purge/ACK; счётчики DELETE/
purge ACK=0, no auto cleanup. Это покрытие существующего T088, не отметка о
полной T088/T117/T118, hardware, installed или release приёмке.

## T121: scoped acceptance shared-meeting — 2026-11-04

Prerequisites: принятые spec/bridge§11/plan, independent review/checklist gate,
current analyze и issue sync. До этого runtime allowlist не меняется.
Все IDs/token/media и записи искусственные. Полный URI/token/credentials и
приватный ответ не попадают в diagnostics; evidence — checks/коды/счётчики.

| Срез | Необходимые наблюдаемые проверки |
| --- | --- |
| Strict intent | два положительных варианта meeting/token; outcomes/recording; position 0/86400000; exact version; unknown/duplicate/encoded-duplicate/empty/both/neither, malformed UTF-8/percent, userinfo/port/path/fragment, overflow/overbound, token/version bounds, wrong registered scheme, URI cap отклонены без изменения pending |
| UUID syntax vs authority | uppercase/lowercase UUID и nil проходят только синтаксический intent/route parse; оба emitted UUID canonical lowercase. Account/owner/доступ без независимого session/server proof не подтверждаются; nil/unknown resource не даёт local effects; прежние accountId checks неизменны |
| Route/media | точные §11 paths/query/fragment; foreign origin/port, encoded separators, arbitrary next, extra keys, misplaced position запрещены; public audio Range/seek через existing server; summary-only не содержит full media; media не открывает native Save/export/blob |
| Cold/repeat | actual cold activation до cabinet ready и single-instance redirect; один pending, latest valid wins, invalid не стирает; каждый accepted intent потреблён один раз; новый valid из recovery начинает загрузку, 403/404 не оживляет старый; update/closing gate сохранён |
| Public capability | valid HTML+actual response/completion показывается без bridge; вошедший и гость не получают local rows/nonce/effects; forged old nonce/known local ID/visible/delete/settings/calendar requests не dispatch; replacement cancels stale actions/publication; возврат к own cabinet требует свежих прежних gates |
| Auth continuation | public sign-in/sign-up идут через sealed server continue без token в login next; addressed next сохраняет workspace/media_version/tab/position; app/browser cookies не копируются; 401/reselect/offline/timeout дают текущий безопасный retry, revoked/foreign grant не раскрывает local data |
| Public login cookie reconciliation | собственная cookie после login читается native cookie manager и обновляет app-session/account recovery без public bridge; stale document/account callback и unknown read не подменяют сессию. Не только успешная web-навигация: проверить actual native callback/current account proof, отсутствие nonce/local rows/effects и сохранение own-cabinet gates |
| Stale/context | A→B intent, account/workspace switch/logout/navigation во время load/login/media: старые callbacks не меняют актуальную страницу/owner; новая публичная ссылка после logout остаётся допустима; native capture/Stop независимы |
| Shared player | tab/seek/speed и exact generated Range bytes; stale media_version не применяет старую позицию, явный existing refresh начинает с начала; закрытая/summary-only ссылка не расширяет доступ; Mac и Windows используют общий UI |
| Regressions | attribution T106 parse/store/expiry/activation/recovery, auth provider/payment, local playback/delete/visibility, notification refreshPending, history GET/POST fences и прежние own-cabinet capabilities сохранены |

Parser/route/state tests дополняют существующие ProductAttributionHandoffTests,
WebViewRoutePolicyTests и WebView2HostLifecycleTests; actual shared browser
fixtures переиспользуются. Portable CMake не доказывает AppMain WinRT/MSIX
activation: нужен обычный full Release build и отдельный actual WebView2
response/cookie/redirect/message test. Точный installed MSIX cold/warm activation
и тот же Mac journey принадлежат T097/T063; фиксировать source/PE/package hashes
раздельно. Ни doc/source/build PASS, ни browser PASS не закрывает T121/F200,
установленную/аппаратную приёмку или release gates.
