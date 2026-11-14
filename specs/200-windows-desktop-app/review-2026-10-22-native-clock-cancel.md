# Независимая проверка native3 и history5c — 2026-10-22

**Итог:** native3 SOURCE / saved build GO; единственный разрешённый metadata-only
запуск main уже выполнен: cleanup GO, clock measurement RED, без повтора.
history5c — достоверный
сохранённый RED: два PASS, два FAIL. Минимальная ранняя проверка `args.Cancel()`
обоснована для нового cancel-before-start дефекта; производственная правка
ещё не сделана и не проверена. Прежний POST-history RED остаётся открытым.

## Границы и привязка

Проверена только `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`,
ветка `codex/200-windows-followup`, HEAD
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`; `.specify/feature.json` и
prerequisite paths указывают на Feature 200. HEAD не подменяет фактические
незакоммиченные байты. Прочитаны AGENTS/router, относящиеся к области правила
Spec Kit, product gates, validation/worktrees и полный `code-reviewer` skill.
Режим: независимое исследование без исполнения; единственная запись — этот
отчёт, то есть docs-only. VM, build/test, приложения, звук, сеть и операции
изменения Git не выполнялись. Нормы, задачи и контрольные списки не правились;
общая приёмка Feature 200 вне области проверки.

Локальная база сохранённых свидетельств:
`/Users/yshishenya/Documents/graf-f200-public458.po8CtB/`.
Ниже пути стадий указаны относительно неё; report453 —
`review-2026-10-16-round453-t116-completion-audit.md` в этой папке спецификации.

## native3: квалификация сохранённой сборки и единственного запуска

Полностью прочитаны оба UTF-16LE журнала `t120-clock-native3`, receipt и
неизменённые `native-clock.r6Lltd/{ClockProbe.cpp,Build-Probe.ps1,build.cmd,Run-Probe.ps1}`.
Сверка с квалификацией native2 в report453:808 и фактическими файлами дала:

- `source.sha256` = `prior.sha256` =
  `e069fdc2a69aafc9827f8c9aff593c92bd92daf700873ad34f00633d8cd52319`;
  216 уникальных путей, все 216 совпали с текущими исходниками; `changed.json=[]`.
  От manifest native2 `0de1d3b969115c42c9dc30db1c1a10704b6850206a12fd9f5483fe09cc1445c2`
  отличаются ровно три файла тестов WebView2Auth: C++, Python и PowerShell.
  Производственные аудиофайлы не изменились. Это свежая привязка сборки к
  текущему набору исходников, а не перенос старого receipt на другую версию.
- Receipt: `terminal=true`, Debug, `native_build=0`, `probe_build=0`,
  `pure_checks=2`, `postflight=216`, `owned_processes=0`, без `failure`;
  `device_started=false`, `device_audio_read=false`.
- Native log: MSBuild 17.14.51, Checking File Globs, успешный common target;
  новых маркеров компиляции нет. Это инкрементальное использование common
  objects. Probe log: VS 2022 17.14.39, environment x64, `ClockProbe.cpp`.
  Успешная линковка и два чистых запуска подтверждаются receipt и проверенным
  потоком Build-Probe, отдельных stdout/receipts чистых child checks нет.
  `--self-check` требует exit0, `--unsupported` — exit64, каждый с пределом 5 с;
  оба пути заканчиваются до COM/UI/device activation.
- Все четыре object hashes в native3 receipt равны native2. PE receipt:
  `c3df5e405435d5c66dd4db70fdf3a6ba32a2aec618e242f9aa0e08896994aa9d`.
  Отсутствующий старый outer handle `61082` не позволяет утверждать outer exit0;
  заключение основано на сохранённом terminal receipt, полных журналах и исходниках.

| Проверенный вход / объект | SHA-256 |
| --- | --- |
| ClockProbe.cpp | `298cdcafff666a602d904c8563cd9ee4d9595c3878e645490ccdf66fb28f8374` |
| Build-Probe.ps1 | `755aa27dd46be26673070d655c099b0da7641b2585807d20805eaa332f5d7084` |
| build.cmd | `906985751ed73a46ac7b69e07fe43d028fbf30e65a3ed31a8366478573e2e3dc` |
| Run-Probe.ps1 | `dbfc729a50eb320b5dcc0710d86a7ac7a7a09cf211b17eef70b82e93056db3a1` |
| WasapiCaptureWorker.obj, receipt | `420263169d8b9fb9a0b67e0762c3154ec3fd87150ccdfd74ed91489210f0d8dd` |
| AudioNormalizer.obj, receipt | `3cd6574f4045f172a2d916c001569293d82052b1b747cc814d65ebd0e223573a` |
| ClockMapper.obj, receipt | `1c584c8b80ed00254186a59c697926a895332af8194bd4ab9619c9187f375694` |
| WasapiEndpointEnumerator.obj, receipt | `3f56183896897748d4e92cee4bd85919b7be4ee4a5a999d36520eadc4169e883` |

Local stage не содержит guest PE/objects: независимого чтения этих guest bytes
не было. Main отдельно сообщил свежий preflight `exec61911`, exit0: actual
ClockProbe PE MATCH указанному `c3df…`, history5c PE MATCH `b47e…`, owned0 с
учётом GUID profiles и свежий CUA screenshot разблокированного видимого Windows
desktop. Эти наблюдения main выполняют условия запуска; reviewer не выдаёт их
за собственную проверку VM. Сообщённое main совпадение нормативных хешей и
полного прежнего checklist review не является новым полным review в этом отчёте.

**GO ровно на один запуск** неизменённого `Run-Probe.ps1` с
`Stage=t120-clock-native3` и ExpectedHash, равным полному `c3df…` выше.
Main обеспечивает видимый доступный интерфейс Start/Stop/Esc и отсутствие
другого capture/build/test до запуска; runner повторно сверяет source216,
входы, четыре actual objects и PE до/после. Только `--metadata-once-48000`,
48 кГц, stereo float, shared/event 10 мс: cap65, минимум 16 valid packets и
16 clock reads, нулевые native/clock/mapper ошибки, end=`packet_limit`,
полное освобождение пакетов и успешный Stop; UI watchdog 5 с, owned parent 12 с.
Нативный mic stream реально активируется, но opaque PCM pointer нигде не
разыменовывается/не копируется, PCM не сохраняется/не передаётся, сети нет.
Helper тот же, что в worker: clock call учитывается после ReleaseBuffer и
проверки известных отказов; cancel/deadline имеют приоритет над packet_limit.
Refusal/cleanup failure сохраняются без автоматического повтора или ослабления
проверок. Итог clock measurement требует отдельной квалификации summary/result;
этот GO не принимает Resume, свежий звук, hardware, установленное приложение или T120.

### Отдельная квалификация выполненного main запуска

После приведённого выше разрешения main сообщил: ровно один запуск,
`exec1013` terminal exit1, без автоматического повтора. Reviewer прочитал только
сохранённые `clock-summary.json` и `run-result.json` файловым API, без shell,
VM или capture. Прежнее разрешение использовано и второго запуска не разрешает.

**Cleanup GO; clock measurement RED.** Run receipt terminal, manifest/PE/runner
совпали с квалифицированными выше, probe_exit0, postflight216, owned0,
capture_cleanup_verified=true, measurement_accepted=false,
failure=`MEASUREMENT_REFUSED`. Summary schema1, audio_read=false,
continuity_acceptance=false, started=true; packets1/released1/release_failures0,
Stop S_OK, elapsed_through_cleanup180ms. Первое чтение clock вернуло S_OK,
но отказано bracket-проверкой: reads1, outside1, invalid0/non_s_ok0,
early_100ns34615 (3,4615 мс до нижней границы), max_call_100ns270 (27 мкс),
valid_packets0, end=`clock_sample_refused`. До mapper принятие не дошло:
mapper_fault0 здесь не доказывает успешный mapper. Минимум16 не достигнут,
probe exit0 подтверждает штатную выдачу summary, не PASS измерения.

Runner сохранил отказ без ослабления guards; источник расхождения paired QPC
по этим агрегатам не установлен. Нет доказательства успешного живого bracket,
Resume или аудиоприёмки. Ни повтор, ни дополнительный shell/capture не выполнялись.

## history5c: meaningful RED и узкая рекомендация

Полностью прочитаны `t103-history5c/run.log`, `result.json`, пустой `run.err`,
wrapper/runner и соответствующие обработчики WebView2Host. Source216 имеет тот
же `e069…`, prior=current, changed=[]; три сохранённых тестовых файла побайтно
равны текущим. От `t103-history5` изменён только C++ capture list: во внутреннюю
queued lambda добавлен `queue` (:539). Прочие байты трёх тестовых файлов
совпадают; фикса производственного поведения здесь нет.

Receipt: terminal, preflight/staged/postflight216, run_exit1,
`NATIVE_RUN_FAILED`, elapsed358109ms, owned0. Журнал показывает ARM64-host
compiler с x64 target (`arm64_x64`, первым найден HostARM64/x64/cl.exe),
54 уникальных свежих TU в отдельном GUID directory, fixture build PASS и PE
`b47e278184d9f1e6776a91c686d079ffcc466fa219fed96cabbfea4bd8e3fcc7`.
Список 54 TU согласован с project-derived runner: исключены ровно AppMain и
production WebRTC adapter, fixture добавлен один раз, object names проверяются.
Это standalone fixture build, не установленное приложение и не native ARM64 target.

| Сценарий | Сохранённое наблюдение | Вывод |
| --- | --- | --- |
| login-post400 | status400, state3, DOM_FLAGS74, bridge0/handshake0; counts `0 1 0 0 0 1` | PASS интерактивной формы |
| history-get | A/B/C/B/A/B/C, семь success200, ready2, authority1, обе source identity совпали; counts `7 0 0 0 0 0` | PASS обычной GET-истории |
| history-post | A/POST-B/C прошли; возврат phase3/nav5: status0, success0, error0, state0, source mismatch; counts `2 0 0 0 0 1` | Исходный `history-host-unavailable` RED сохранился |
| cancel-before-start | A ready; ранний subscriber выставил Cancel(true), затем nav3 завершился status0/success0/error14 и state0; counts `2 0 0 0 0 0` | Новый `cancelled-navigation-revoked-current-document` RED |

Во всех четырёх случаях есть browser exit PASS, fixture exit0/0/1/1 и server
exit0; cleanup errors не отмечены. Runner продолжил после первого FAIL и
сохранил общий `2/4`, exit1. Это поведенческий RED после successful build,
не ошибка компиляции и не общий PASS. Сервер synthetic loopback; без реального
аккаунта, установки или устройства. Actual guest PE/GUID inventory подтверждены
main отдельно, как указано выше.

**[P2] WebView2Host.cpp:1792–1801 игнорирует уже выставленный Cancel.**
Fixture подписывается раньше `host->attach` и отменяет только точный переход B.
У product subscriber первой строкой внутри try сейчас читается Uri, затем
вызывается `beginDocumentNavigation`. Этот единственный производственный caller
(:1800) меняет generation/navigationId, очищает committed document и через
`setRuntimeState(initializing)` отзывает nonce/bridge. Затем completion error14
обрабатывается как завершение уже принятой навигации и приводит к unavailable.
`host->navigate` до события запрашивает переход, но generation/bridge не отзывает.

Рекомендация — **construction GO** на минимальную строку первой внутри
существующего try (:1794), после прежней alive-проверки:

```cpp
if (args.Cancel()) return;
```

Она не начинает отменённую навигацию и сохраняет исключения getter в прежнем
catch. При неизменённом navigationId (после подтверждённого A он равен0)
completion отменённого B отсекается существующим NavigationCompleted guard
(:2513–2514). Проверки origin/route/response/generation для неотменённых переходов
остаются прежними. Новая модель истории или восстановление nonce не нужны.
Current production SHA-256:
`0c843eae40b30e388a881b057ccdbce9fa89d4bb99620d5148e5a63bba0de883`;
предложенная строка в проверенных байтах отсутствует.

После правки нужен свежий build/run с теми же controls и точной новой привязкой.
Cancel-case должен доказать не только сохранённые A/generation/auth callbacks,
но и реальный update bridge dispatch со старым nonce, затем успешный переход C
с новым generation и вторым auth callback. В нынешнем RED эти последующие фазы
не достигнуты. Более поздняя отмена другим subscriber этой строкой не покрывается.
Причина прежнего POST-history failure из error0 не установлена; guard не
объявляется его исправлением. T103/сессии/installed/общая приёмка остаются открытыми.

## Контрольные суммы сохранённых свидетельств

| Файл | SHA-256 |
| --- | --- |
| native3/build-result.json | `088bf885f7f55a458e028e4eec5c542b2e44a5fd3a23e9315a6755c5d753b2b3` |
| native3/native-build.log | `1344c175e12a8bf02292c7af1a2abff0e6617ea4f84b16a0c3f00907ebb74807` |
| native3/probe-build.log | `31f6cad0ff8e051b15675da271bad79c06d8382713be8946a37f3c544afceaf2` |
| native3/clock-summary.json | `18e88c98522e9b38690694c4e6f039fe1a7694e27f10cda7379fb616ac7f545a` |
| native3/run-result.json | `dceec9d82165cd4f8e7d94b7cb93b7c1ef5395b1a632de8a93cf07868c4c4893` |
| history5c/result.json | `25b36eee71894275758148cce8e3d7feb54e4ebb23a4088c403bff5e95df33f8` |
| history5c/run.log | `063f2e4163237177577d807c788a04458b9d22d8ec270e23c415d4f9b7e832e8` |
| history5c/run.err, 0 bytes | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |

Только новый отчёт. Повторная сверка source216: 216 unique/current match,
0 mismatch; все 54 TU журнала совпали с перечнем runner/project, wrapper input
hashes совпали с receipt. Снимок 206 путей (198 checklist files, семь документов
спецификации и WebView2Host.cpp) остался побайтно неизменным. Производственные
исходники, нормы, tasks/checklists и Git не менялись; готовность всей функции
или выпуска не заявляется.

## Дополнение: фактические guard и stage6 wrappers — SOURCE GO

После предыдущей контрольной точки main внёс ровно комментарий и
`if (args.Cancel()) return;` первыми внутри существующего try (:1795–1796).
**Независимый bounded guard SOURCE GO, блокеров нет.** Текущий production hash
`a68f2ec8a2696204e25167a2d90261f41d3e839794453bed2a6e28b659d7b2e6`;
удаление ровно этих двух строк в памяти восстанавливает прежний
`0c843eae40b30e388a881b057ccdbce9fa89d4bb99620d5148e5a63bba0de883`.
Это сохраняет прежнее source-обоснование: отменённый до product handler переход
не начинает смену документа; уже существующие completion guards остаются.

**Stage6 wrapper SOURCE GO, блокеров нет.** Полностью прочитаны фактические
`t103-history6/Run-History.ps1`, `Invoke-Runner.ps1`, `run.cmd`; сравнение с
history5c выполнено в памяти, без shell, VM, Git или запуска. Manifest
`3c4e0610c8c3828b29a75d6d286c9c85310a9323514a87b8c65cd4a21d377130`:
216 unique/current match, 0 mismatch. Prior побайтно равен history5c source
`e069fdc2a69aafc9827f8c9aff593c92bd92daf700873ad34f00633d8cd52319`;
дельта и changed.json содержат только `apps/windows/RecApp/Web/WebView2Host.cpp`.
Staged production copy и три staged тестовых файла равны текущим байтам.

Точная дельта Run-History: две строки копирования одного production файла,
два current-manifest bindings (staged/postflight) и requested19. Preflight
по-прежнему требует prior e069. Invoke меняет только Scenarios19; этот список
побайтно равен canonical runner default19 и requested receipt. run.cmd и
synthetic cert/key побайтно прежние. Проверки свежей стадии, source216,
SDK/runtime/input hashes, owned processes, compiler/target, deadlines и
cleanup не изменились. Общий nonzero при провале любого сценария сохранён;
исходный history-post не исключён и не объявляется исправленным.

Проверенные wrapper SHA-256:

- Run-History.ps1: `0e44736c02e5e2b6de884fde6a5704f04b1d75288c79a57302e0c93b82ee7037`.
- Invoke-Runner.ps1: `6b9e5898bfe9300815e174581bfb3b930129c61ece10aac44ccfe8d6d290e7b5`.
- run.cmd: `0a75f74b7466383a1cafc79665c5daf61c48f6e5a831dce6bc958c09eae0d856`.

Прежние выводы сохранены: native3 saved build/cleanup GO, measurement RED;
history5c — meaningful cancel RED. SOURCE GO относится к guard и подготовке
19 существующих synthetic-сценариев. Main сообщил уже идущий exec58636;
reviewer его не опрашивал, stage6 live log/result не читал и runtime не принимал.
Ожидается отдельная квалификация terminal evidence. Никаких повторов или
аудиоправок; единственная запись reviewer — дополнение этого отчёта.

## Дополнение: stage6 terminal — guard runtime GO, общий T103 RED

После сообщения main о terminal полностью прочитаны сохранённые
`/Users/yshishenya/Documents/graf-f200-public458.po8CtB/t103-history6/{run.log,result.json,run.err}`.
Это отдельная квалификация завершённого запуска, не опрос live exec и не повтор.
Receipt: terminal=true, preflight/staged/postflight=216, manifest `3c4e…7130`,
run_exit=1, owned_processes=0, elapsed_ms=397924, failure=NATIVE_RUN_FAILED.
Manifest равен ранее проверенному source216; все пять input hashes receipt
повторно совпали с сохранёнными байтами. Журнал содержит 54 уникальных свежих TU,
ARM64 host compiler → x64 target (`arm64_x64`, первым выбран HostARM64/x64/cl.exe),
fixture build PASS и binary SHA-256
`895201dbdf80d37ea602f106e5dacb0899efbca222315c4b649d58be54bcfa9d`.
Вторая строка where с ARM64 target не подменяет выбранный x64 compiler.

Независимый подсчёт: ровно requested19, 18 PASS / 1 FAIL; у всех 19
browser exit PASS и synthetic server exit0. Единственный FAIL — исходный
history-post: A/POST-B/C готовы, затем phase3/nav5 success0/status0/error0,
state0/document0, counts `2 0 0 0 0 1`. Причина конкретного browser failure
этим не установлена; HRESULT/диалог повторной отправки не доказаны.

cancel-before-start PASS: nav3 действительно завершился OperationCanceled14;
между CANCEL_BEFORE_PRODUCT_START и этим completion нет HOST_STATE=1/0.
Фактические assertions fixture :517–580 и :749–753 требуют прежние ready,
generation, source и authCallbacks, затем реальный bridge dispatch с прежним
nonce (updateCallbacks=1), после него новый C со свежей generation.
Итог nav4 success200/state2, starts3/completions3, authCallbacks2,
counts `3 0 0 0 0 0`. Следовательно, **bounded guard runtime GO** именно для
отмены более ранним subscriber; поздняя отмена или все гонки этим не покрыты.

history-get PASS A/B/C/B/A/B/C, counts `7 0 0 0 0 0`.
Оба CDP diagnostic cases PASS: реальные entry IDs A=5/B=6/C=8,
восстановление A=5/C=8, включая одинаковые URL GET-A/POST-B;
у каждого counts `4 0 0 0 0 1`. Это не PASS production back()/forward().

SHA-256 сохранённых доказательств:

- result.json: `f2e2e63be69f8abc6b19579f778e8d51a6bf6f281f176b6f4fa5ebd816c4581f`.
- run.log: `13fed73bc46c327534997938a47ae7148cb5c7c97d925876d80fd0c40815963c`.
- run.err: 0 bytes, `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.

Отдельное свидетельство main, не собственный VM check reviewer:
exec78416 terminal exit0, actual guest PE равен указанному `895201…fa9d`,
OWNED_PROCESSES=0, включая exact GUID commandline. Оно согласуется с saved
build hash/cleanup receipt, но не превращает overall run_exit1 в PASS.
Полная готовность T103, установленное приложение и feature acceptance не заявлены.

## Дополнение: build-only preflight — SOURCE GO только для точных байтов

Полностью прочитан actual local `t103-app-build2/Build-App.ps1`, сравнен с
`t120-app-build1/Build-App.ps1`, полными build1 log/receipt и source manifests.
**SOURCE GO** для одного production Release x64 project Build, без install,
launch, audio и restore. Это не будущий build0 и не разрешение повтора.
Проверенная версия имеет 70 строк плюс завершающую пустую; SHA-256
`785a7b2d53b4d58ea0c8ec36ccddd357bc0ef5ebb1edc49c8b1d67adb15bdb5c`.
Сообщённые позднее main 83/85 строк reviewer в локальном файле не увидел;
если guest-версия другая, этот GO её не покрывает до привязки точного SHA.

Build1 receipt build0/post216/owned0 и полный UTF16 log согласованы:
manifest `0de1d3b969115c42c9dc30db1c1a10704b6850206a12fd9f5483fe09cc1445c2`,
AppMain.obj `47c39d081c6a6b018eb86b63c5522811a0530b546d8b41cfb9039ad29b4d45f6`.
Новый manifest `3c4e…7130`: 216 unique/current match, 0 mismatch;
дельта против build1 — только три тестовых файла и двухстрочный host guard.
AppMain.cpp, project и AEC verification script не изменились.

Core guards сохранены: source216 до/после, одноразовая stage, отсутствие активных
build/capture процессов, disk threshold, фиксированный AppMain.obj до/после,
свежие UTC host object/PE плюс compile/link log, MZ/PE x64,
project target ValidateGrafAEC3 → -VerifyBuildArtifacts (pin/source tree,
identity/artifact inventory/hashes), неизменные provenance и runner hash.
Новый parent ждёт 600s; taskkill ограничен PID созданного MSBuild и его tree,
не общей выборкой процессов. Nonzero build/deadline/остаточные owned processes
не дают exit0. Проверка происхождения AEC не запускает обработку звука.
Main сообщил один уже запущенный build; reviewer его не опрашивал.

## Дополнение: T103 history root — минимальный следующий test-first шаг

Область: фактические host/native вызовы и policy, существующий fixture,
plan :530–560, validation :29695–29727 и report453 :948–956; не весь dirty diff.
Подтверждённый пробел реализации, а не доказанная внутренняя причина browser error:
кнопки AppMain.cpp :844–847 → WebView2Host.back()/forward() :1021–1034 →
nativeBack_/nativeForward_ :1854–1857 → raw core.GoBack()/GoForward().
CanGoBack/Forward проверяет наличие browser history, но не подтверждённый GET
целевой записи. Выбора безопасного entry ID здесь нет. Cancel guard эту цепочку
не меняет. Не использовать safeRecoveryUrl как доказательство метода старой записи:
его allowlist проверяет переданный GET и строит отдельный recovery URL (:387–406).
Настоящий метод документа поступает сейчас из correlated request.Method()
в WebResourceResponseReceived (:1917–1935), не из NavigationStarting (:1802–1803).

Пути, которым нужен один владелец решения о traversal:

| Путь | Фактическое состояние / граница будущего решения |
| --- | --- |
| Native кнопки GRAF | Вызывают host; заменить только raw callbacks недостаточно для остальных путей. canGoBack/Forward должны отражать ту же допустимую цель. |
| Browser клавиши, меню, swipe | Отдельного host history adapter не найдено; root KeyDown :544 обрабатывает только F6. Browser settings для accelerator/context menu/swipe здесь не переопределены. Физическая доставка touch/trackpad/XButton в этой среде не проверялась. |
| Script history.back/forward/go(delta) | Не обязаны проходить через C++ back()/forward(). В просмотренном cabinet.js прямых вызовов нет, но путь DOM остаётся; go(-2) нельзя свести к raw back, go(0) — reload. Возможные navigation.back/forward/traverseTo также не считать закрытыми без проверки поддержки runtime. |
| Same-document push/replace/hash | Нельзя полагаться только на NavigationStarting. Реально cabinet.js :137 нейтрализует private location, :1881 меняет hash через replaceState; meeting_list_content.html :16 использует data-hx-replace-url. Host SourceChanged :1876–1897 уже сохраняет generation/nonce и не превращает POST в GET. |
| Payment popup и recovery | Сохранить особый Back → отмена popup/разрешённый billing GET и запрет Forward; explicit nativeReload — отдельный safe recovery, не обычный replay history. Формы POST не запрещать глобально. |

Основание API: browser accelerator keys, context menus и touch swipe имеют
включённые defaults; отключение всех accelerators затронет также find/print/reload,
поэтому это не нейтральная замена точечного history adapter.
[Microsoft Settings](https://learn.microsoft.com/en-us/microsoft-edge/webview2/reference/winrt/microsoft_web_webview2_core/corewebview2settings?view=webview2-winrt-1.0.4129.50).
BackOrForward объединяет разные источники, но event args не дают direction,
delta, target entry ID или HTTP method.
[NavigationKind](https://learn.microsoft.com/en-us/microsoft-edge/webview2/reference/winrt/microsoft_web_webview2_core/corewebview2navigationkind?view=webview2-winrt-1.0.4129.50),
[NavigationStartingEventArgs](https://learn.microsoft.com/en-us/microsoft-edge/webview2/reference/winrt/microsoft_web_webview2_core/corewebview2navigationstartingeventargs?view=webview2-winrt-1.0.4129.50).
Same-document переход может не вызвать Starting; HistoryChanged — уже уведомление
об изменении joint history, включая manual frame navigation, не permission gate.
[Navigation events](https://learn.microsoft.com/en-us/microsoft-edge/webview2/concepts/navigation-events),
[CoreWebView2](https://learn.microsoft.com/en-us/microsoft-edge/webview2/reference/winrt/microsoft_web_webview2_core/corewebview2?view=webview2-winrt-1.0.4129.50).

**Рекомендованный ближайший шаг — test-only расширение существующего fixture,
не production broker и не перенос diagnostic CDP steering в успешный host test.**

1. Сохранить original history-post RED и два entry diagnostic controls.
   Добавить host-driven same-URL вариант существующей A/POST-B/C/A/C проверки:
   действия только actual host.back()/forward(); GET-A и POST-B имеют один URL,
   но разные browser entry IDs. Проверять ожидаемые ID/документы/ready/bridge
   authority и точный POST count=1. Нынешний production путь должен оставаться
   RED, а не становиться зелёным от подмены driver на navigateToHistoryEntry.
2. На той же подготовке отдельно проверить отмену traversal ранним subscriber
   для host.back() и script history.back()/go(-2); записывать NavigationKind и
   реальные текущие entry IDs. Требовать OperationCanceled, неизменные C,
   generation/auth callbacks и реальный старый nonce dispatch, затем обычный
   новый документ. Это узкая проверка пригодности общей точки отмены; test
   subscriber не выдавать за установленного production owner. Same-document
   replace/hash включить как различающий контроль, не ожидать у него Starting.
3. До разрешения production реализации зафиксировать тестовый контракт stale
   snapshot/callback: после реальной смены документа, history mutation, auth
   session или close/recreate старый ответ не может вызвать traversal/выдать
   bridge. Проверять будущий настоящий owner, а не только phase guards fixture.
   Пока owner отсутствует, такой тест не объявлять пройденным доказательством.

Дальнейший минимальный owner логично оставить внутри существующего WebView2Host:
один pending intent, browser entry IDs + отдельно подтверждённый метод документа
в границе текущего host/auth session, без собственного упорядоченного URL stack.
Источник порядка — свежая browser history; неизвестный/неоднозначный метод или
устаревшая привязка означает отказ, не fallback Navigate(url). Все доступные
input adapters должны передать проверенное направление/цель этому owner либо
безопасно отклонить неподтверждённый traversal до смены документа; неизвестное
направление нельзя угадывать по URL. Как сохранить полноценное поведение всех
таких inputs, ещё не доказано — это конкретный blocker blanket broker SOURCE GO,
но не blocker описанного test-first шага. Общий запрет inputs не равен паритету.

CDP getNavigationHistory даёт browser order/IDs, но NavigationEntry не содержит
HTTP method; transitionType и URL не заменяют его. navigateToHistoryEntry выбирает
запись, а не сам по себе безопасный GET. Await serializes CDP calls, но не делает
snapshot+переход атомарными относительно page/user events; readiness и authority
по-прежнему подтверждает существующая document response/completion цепочка,
не успешный command result.
[Chromium Page schema](https://raw.githubusercontent.com/ChromeDevTools/devtools-protocol/master/pdl/domains/Page.pdl),
[Microsoft CDP method contract](https://learn.microsoft.com/en-us/microsoft-edge/webview2/reference/winrt/microsoft_web_webview2_core/corewebview2?view=webview2-winrt-1.0.4129.50#calldevtoolsprotocolmethodasync).
DOM go(0) означает reload; Navigation API intercept() не является универсальным
перехватом cross-document traversal, а formData=null при возврате не доказывает GET.
[HTML Standard](https://html.spec.whatwg.org/multipage/nav-history-apis.html).

Это продолжает уже записанный validation :29721 шаг «browser-entry proof +
подтверждённый метод + граница сеанса; cancellation/same-URL/stale test-first»,
не меняя plan/norm/tasks. code-reviewer применён к точному control flow,
полномочиям bridge и пределам доказательств. Только этот owned report дополнен;
никаких VM/Git/build/code/norm/checklist действий reviewer не выполнял.

## Дополнение: production AppBuild2 terminal — bounded build GO

После сообщения main об exec26325 exit0 полностью прочитаны завершённые
`/Users/yshishenya/Documents/graf-f200-public458.po8CtB/t103-app-build2/{build.log,build.err,result.json}`.
**Независимая квалификация сохранённых build evidence: GO для production Release
x64 project Build и его cleanup; не приёмка запуска приложения.** Main сообщил
один запуск без повторов; reviewer VM/build не запускал и не опрашивал.

Receipt согласован с полным журналом: terminal=true, build=0,
preflight/postflight=216, elapsed_ms=245481, owned_processes=0, failure отсутствует.
Manifest `3c4e0610c8c3828b29a75d6d286c9c85310a9323514a87b8c65cd4a21d377130`
и runner `785a7b2d53b4d58ea0c8ec36ccddd357bc0ef5ebb1edc49c8b1d67adb15bdb5c`
повторно совпали с фактическими локальными файлами; manifest содержит 216 unique
paths. Main отдельно подтвердил, что actual guest wrapper имеет именно этот SHA:
прежние «83/85 строк» были неточным описанием, не другой версией. Оговорка о
неподтверждённых иных байтах к данному завершённому запуску больше не относится.

Полный build.log (939 bytes) содержит компиляцию WebView2Host.cpp, AEC identity
verified для pin `846fe90a289f58b7c9303a635142aa2c7caa93e5`, code generation и
линковку нужного Release/GrafWindowsApp.exe. Это инкрементальная сборка:
57/29004 функций скомпилированы, остальные переиспользованы; не clean rebuild.
Единственное предупреждение — прежнее command-line D9025 (`/W1` → `/W4`),
уже присутствовавшее в build1; новых C++ source warnings/errors в журнале нет.
build.err пуст. Проверенный wrapper до exit0 требует свежие UTC host object/PE
и compile/link log; их квалификация здесь опирается на этот контроль и receipt,
не на дополнительное чтение guest artifacts reviewer.

Receipt фиксирует host object
`f5b548260746746c8258a48e71ecc169e88840e47cdcbf173ea8357d33ecdc0d`,
PE `89cc93a2e86dc181324f7018cd04faa500e023f325e3558a4c0d4643414f43a9`,
3319808 bytes, machine 0x8664, written_utc `2026-10-21T21:39:48.2480333Z`.
AppMain.obj reuse точно равен build1
`47c39d081c6a6b018eb86b63c5522811a0530b546d8b41cfb9039ad29b4d45f6`;
AEC provenance также равен build1
`ebe9b371f9ef9ab8e78f45c607ab7a661235ad9396d4001e2079395b08aae0fe`.
installed/launched/device_started/app_network/restore_performed все false.

SHA-256 сохранённых доказательств:

- result.json: `2d49a7e2a9eedbd3d65bcb49e13ff862c337a78c768ed81c0442de84bb05a006`.
- build.log: `fe8906ba8adfdb7219df76fac4a1e7c403ab3270b1380edf8d8f78cf1007edec`.
- build.err: 0 bytes, `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.

Узкий guard checkpoint имеет source + synthetic runtime + production build
evidence; исходный history-post остаётся RED, full T103/full feature не приняты.
Новый actual-host same-URL тест ещё не написан и не пройден. Другого исследования
или поручения этим дополнением не открывается. Единственная запись reviewer —
этот отчёт; code/norm/tasks/checklists/Git и VM не затронуты.

## Дополнение: same-URL actual-host test — requirements/analyze GO, C0/H0

**Scoped GO, CRITICAL 0 / HIGH 0 / blocking clarification 0** только для
написания одного следующего test-only сценария в прежних трёх файлах:
WebView2AuthNativeTests.cpp, WebView2AuthLoopback.py,
RunWebView2AuthNativeTests.ps1. Production broker, изменение history policy,
новый public seam и изменение production host этим не разрешены.
Это revalidation применимости gate8037/8113/8169 report460 к пункту 1
настоящего отчёта, не полный новый analyze Feature200 и не SOURCE GO ещё
не предъявленной тестовой дельты. Lane остаётся active high-risk auth slice;
то, что меняются только тесты, не переводит его в low-risk.

Прочитаны точно соответствующие разделы report460 :8037–8093,
:8103–8139 и :8169–8225, текущие FR-002/003/005/006, SC-002,
plan :547–561, tasks T103(:447)/T088(:390), bridge §§2/6/9 и применимые
requirements/security/UX критерии. Навык speckit-analyze прочитан целиком
и применён к ограниченной cross-artifact сверке. Full workflow и prerequisite
script не запускались: сохранённый prerequisite gate8169 переиспользован
в заданной пользователем границе no Git; feature.json заново прочитан и
подтверждает F200/high-risk-product/codex/200-windows-followup/source_sha
b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1. Фактические analyze/implement
commit hooks в extensions.yml disabled; hooks не выполнялись.

Повторно вычисленные пять нормативных SHA точно совпали с gate8169:
constitution d28f8312…, spec0065a781…, planf3009717…, tasks80fc15cd…,
quickstartbe5ad099…. Production host SHA остался
`a68f2ec8a2696204e25167a2d90261f41d3e839794453bed2a6e28b659d7b2e6`.
Независимо пересчитан sorted checklist inventory: 198 файлов, 31 с
checkbox-критериями, 477 total / 477 checked / 0 unchecked; SHA-256
`6aaf78544635814de7c4feacc8f153eee2876226b9702bf70b0e16bfb4f351b2`.
Это неизменность прежнего requirements-quality gate, не свежая runtime
приёмка всех 477 пунктов; checkbox markers не менялись.

Узкое сопоставление не выявило противоречий/новых unmapped requirements:
FR-002/SC-002 → T103, наблюдаемая правильная история/положительный GET control;
FR-003/005 → T103, reuse approved cabinet routes без собственного URL stack;
FR-006/bridge lifecycle → T103 и сохранённая связь с T088 для отдельного
session/stale среза. Same URL — различающий тест уже обязательного метода и
document authority, не новое требование и не выбор реализации исправления.
Constitution VI и требования к секретам/границе документа не ослабляются.

Обязательные границы конструкции и последующего SOURCE review:

- Обычная approved GET-A → настоящая form POST-B по тому же URL → distinct
  GET-C, затем actual host.back()/forward() с ожидаемыми A/C. A/B различаются
  browser entry IDs и synthetic document markers, не строкой URL; POST-метод
  доказывается настоящим submit/сервером, не URL или transitionType.
- CDP getNavigationHistory допустим как observation действительных entry IDs;
  CDP navigateToHistoryEntry, Navigate(GET), ручной callback или заранее
  нарисованная authority не могут подменить проверяемые host actions.
- Нужны document/source/ready/bridge authority и POST count=1 вместе.
  Только отсутствие второго сетевого POST недостаточно: POST document может
  восстановиться из cache. Отказ/confirm/error/неверный документ не PASS;
  genuine reached-action RED отделяется от build failure/fixture timeout.
- Прежние 19 сценариев, original history-post RED, GET-only positive control,
  оба CDP diagnostic controls, login/forms/cancel expectations и все
  isolation/TLS/loopback/deadline/owned cleanup/terminal count guards сохранить.
  Только synthetic case/наблюдения/exact counts/runner registration; никаких
  cookies/tokens/nonce/HTML/private content в evidence.

Прежние session-cookie crossing, stale callbacks, gestures/script/native
единый owner, pre-wire correlation и вся production broker correctness
остаются отдельными доказательствами. Их отсутствие не блокирует написание
именно данного различающего теста, но его будущий PASS их не принимает.
Т103/#7280 и T088/#7231 OPEN переданы main как свежий live факт; reviewer
новый GitHub запрос не делал. Mapping совпадает с gate8169/tasks, закрытие
issues или назначенного исполнителя не утверждается.

Новая задача/spec/plan/clarification не нужна. Следующий gate — предъявленная
точная frozen 3-file delta и source bindings для независимого code-reviewer
SOURCE review; runtime допускается только отдельно после него. Сейчас тест
ещё не написан и не пройден. После read-only анализа разрешённо дополнен
только этот отчёт; code/norm/tasks/checkbox markers/VM/build/tests/Git/GitHub
не изменялись. Full T103/full feature acceptance по-прежнему не заявляется.

## Дополнение: history7 actual-host same-URL — bounded SOURCE GO

**SOURCE GO, блокеров не найдено** для предъявленной замороженной test-only
дельты и трёх stage7 wrappers. Предыдущий requirements/analyze GO C0/H0
завершён выше; этот кандидат укладывается в его пункт 1, не production broker.
Навык code-reviewer применён к полной actual 3-file delta против сохранённого
source-qualified stage6 и связанным control-flow/response/cleanup участкам.
Полностью прочитаны actual Run-History.ps1, Invoke-Runner.ps1, run.cmd;
Python server и canonical test runner также прочитаны целиком.

Независимая привязка: source manifest
`2891adb4b792c01d38415a7765ea80cbabeaf30034f5edf6f9a5af2975380271`,
216 unique/current match, 0 mismatch, тот же набор путей. Prior побайтно равен
stage6 manifest `3c4e0610c8c3828b29a75d6d286c9c85310a9323514a87b8c65cd4a21d377130`.
Manifest delta и changed.json содержат ровно следующие три файла; их staged
копии равны текущим байтам:

- WebView2AuthNativeTests.cpp: `e2767b652995f06c70772123905fd5ab0d8612a6280fac8043a381d1dabc7f9b`.
- WebView2AuthLoopback.py: `4752e106ed771d4fa4774585dbc93938032cc85b044ce42b5b1d4954e31a8c09`.
- RunWebView2AuthNativeTests.ps1: `e4d10d4c62ae85127615010f2b97e3c2600df97a5dd2ece0255928c922ec82ab`.

Production host остаётся `a68f2ec8a2696204e25167a2d90261f41d3e839794453bed2a6e28b659d7b2e6`;
stage7 копирует те же host bytes, не вносит production delta. Новых норм,
tasks, bridge API, route/session policy или broker нет. Cert/key побайтно равны
stage6; содержимое ключа не выводилось.

Проверенный смысл нового history-host-same-url:

- C++ :52–54 различает historyEntryScenario (только прежние два diagnostic
  cases) и historySameUrlScenario (same-URL diagnostic плюс новый host case).
  Поэтому advanceHistory :373–389 никогда не исполняет CDP steering для
  нового случая: после настоящего form.requestSubmit (:390–401) и GET-C
  (:402–405) используются host.back()/forward() (:406–411).
- Python :21–23/45–55/119–141 выдаёт GET-A и валидированный POST-B по одному
  URL, но с разными document markers; метод и точное тело настоящего POST
  проверяются сервером. GET по общему URL возвращает A, а не маскирует B.
- C++ :468–514 до перехода проверяет completed/current navigation, generation,
  ready/observedSuccess, bootstrap/native_ready booleans, A/B/C marker,
  POST-accepted плюс сохранённый synthetic input и оба source identities.
  Новый case использует checkHistoryEntry только для наблюдения.
- Snapshot :415–465 проверяет текущий owner/generation/navigation, bounded
  integer IDs, distinct IDs A/B/C, существование A/C в нужном направлении;
  после traversal требуются именно прежние A/C IDs и документы. Совпадение
  URL A/B не может само дать PASS. CDP command result не заменяет readiness.
  Это не новая приёмка полноты nonce/session/stale callbacks: отдельный
  real bridge dispatch из cancellation test не приписывается history case.
- Canonical runner добавляет только новый case в ValidateSet/default (прежние
  19 сохранены) и в ту же строгую count-группу: cabinet GET [2–4], остальные
  четыре поля 0, actual non-GET ровно 1. Counts читаются только после terminal
  server drain; PASS также требует fixture exit0. Original history-post по-
  прежнему обязан реально пройти oracle, его RED не объявлен ожидаемым PASS.

Новый сценарий должен сам достигнуть host action: если distinct-entry/POST
precondition не достигнут, это не доказательство production history RED.
Build failure, snapshot error и deadline также остаются отдельными исходами.
При достигнутом Back неправильный документ/ID/authority или отказ — FAIL,
а не разрешённый альтернативный PASS. Никаких результатов запуска ещё нет.

Wrappers сравнивались со stage6 целиком: Run-History меняет только requested7
и три manifest bindings (preflight prior3c4e, staged/post current2891);
Invoke — только selected7; run.cmd идентичен. requested/selected побайтно
согласованы: login-post400, history-get, history-post, history-entry,
history-entry-same-url, cancel-before-start, history-host-same-url.
Это focused7, не повторная runtime-приёмка всех default20.

Проверки fresh stage, source216 до/после, SDK/runtime/input bytes, compiler
ARM64 host → x64 target, /W4 /WX, x64 link, isolated GUID profile, loopback TLS,
20s fixture / 10s browser release / 35s case / 600s parent bounds, server writer
drain, owned-process cleanup и nonzero на любой failed case не изменились.
Project Includes55 − AppMain/production AEC adapter + fixture дают 54 unique
fresh TU, не ручной урезанный список. Failure diagnostics сохраняются.

SHA-256 wrappers:

- Run-History.ps1: `66647e47a549b3ad9414f5efe859ebf7c18896a733d590a5764048b2937fee3e`.
- Invoke-Runner.ps1: `afd7edc412f9d8be01f9a0b5435a8c9d3eee42b0c526eb30736102e9579c2b39`.
- run.cmd: `0a75f74b7466383a1cafc79665c5daf61c48f6e5a831dce6bc958c09eae0d856`.

Итог — допуск исходников этого одного test-first добавления и bounded focused
runner, не исправление исходного Back, не broker SOURCE GO, не build/runtime
PASS и не full T103/full feature acceptance. Reviewer ничего не запускал
и VM/Git не трогал; единственная запись — этот owned report append.

## Дополнение: шаг 2, cancellation traversal — requirements/analyze GO C0/H0

**Scoped GO, CRITICAL 0 / HIGH 0 / blocking clarification 0** для написания
следующего test-first подмножества в тех же трёх test files: отмена actual
host.back() и script history.go(-2) ранним native subscriber при фактическом
NavigationKind=BackOrForward, плюс отдельный same-document контроль.
Это продолжение gate8037/8113/8169 и ранее рекомендованного шага 2; не новый
product requirement, не production broker/policy и не SOURCE GO будущего кода.
Новый spec/plan/task/issue или продуктовый clarification не нужен.

Использован полностью прочитанный speckit-analyze в scoped read-only режиме.
Повторно вычислены пять нормативных SHA: constitution d28f8312…, spec0065a781…,
planf3009717…, tasks80fc15cd…, quickstartbe5ad099… — все прежние. Feature.json
подтверждает F200/high-risk-product/codex/200-windows-followup/source_sha
b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1. Host всё ещё a68f…; C++ fixture
e2767b… из source-qualified stage7, никаких новых code bytes не оценивалось.
Analyze/implement commit hooks перечитаны: disabled, не выполнялись.
Сохранённый prerequisite и неизменный requirements-quality inventory 6aaf…
(198 files, 31 checkbox files, 477/0) переиспользованы; новый whole-checklist
review/пересчёт всех критериев или новый GitHub/live issue fetch не заявлены.

Покрытие: FR-002/SC-002 и T103 — сохранение действующего документа/обычного
последующего перехода; FR-003/005 — прежний approved cabinet и native/web
ownership; FR-006, bridge §§2/6/9 (:45,134–143,229–254) — nonce/document
boundary и неприменение событий отменённого перехода к новому документу.
Связь T088 остаётся для отдельной session/stale проверки. Constitution VI,
plan §Вход, применимые security/requirements/UX критерии предыдущего gate не
конфликтуют с такой конструкцией и не требуют нового требования.

Минимальный oracle — два независимо подготовленных driver cases и отдельный
различающий контроль, с заранее фиксированными ожиданиями:

1. Реальные A → form POST-B → GET-C в isolated fixture. До действия дождаться
   полного C completion/readiness и ожидаемого auth observation; снять реальные
   browser entry IDs/order, C marker, host/core source, generation и auth/bridge
   counters. Подготовка должна различать документы, а не считать URL методом.
2. Subscriber зарегистрирован до product NavigationStarting handler. Вооружать
   отмену только после принятого C для одного ожидаемого traversal; проверять
   фактический BackOrForward, записать его navigation ID, затем Cancel(true).
   Первый driver вызывает именно host.back(); второй исполняет настоящий
   history.go(-2), не history.back(), CDP steering или Navigate(GET). В A/B/C
   первый идёт к B, второй к A: одинаковый kind не доказывает равную цель/delta.
   Начальные A/POST-B/C и последующий новый GET нельзя случайно отменить.
3. Обязательно достигнуты реальный Starting/cancel и completion именно этого
   navigation ID с OperationCanceled, не только «script returned true».
   После completion и свежего observation snapshot всё ещё тот же C entry ID,
   C marker, host/core source, ready, прежняя generation и auth counters;
   host не проходил initializing/unavailable в интервале отмены. Затем реальный
   typed bridge dispatch из сохранившегося C должен дойти до existing native
   handler ровно один раз, без reinjection/nonce setter/ручного callback.
   DOM flags или один ready недостаточны; nonce/token не печатать.
4. После этого обычный host.navigate к известной разрешённой GET-странице,
   отличной от текущего C: реальный новый document success200/ready,
   generation увеличилась, ожидаемый auth callback произошёл один раз,
   актуальные marker/source/bridge соответствуют новому документу. Поздний
   callback старого cancelled ID не может отменить этот успех. Это наблюдение
   настоящей последовательности, не доказательство всей adversarial stale
   матрицы или session crossing и не повод вручную вызывать host completion.
5. Actual POST остаётся ровно один; final server counts — только после writer
   drain/server terminal. GET bounds задать до запуска с учётом возможного
   provisional GET при отмене, не требовать отсутствия любой сетевой активности.
   Не достигнутый Starting, wrong kind, snapshot/fixture timeout, compile failure
   не превращаются в cancellation PASS или meaningful product RED.

**Same-document контроль нельзя незаметно вставлять между подготовленным C
и проверяемым traversal.** Hash может добавить history entry, изменить цель
go(-2) и сделать ближайший Back same-document вместо отменяемого нового
документа. Минимально — отдельный isolated case (replaceState и hash как две
фазы) либо строго отдельная уже завершённая последовательность с новым baseline.
Оба изменения остаются на прежнем approved route с фиксированными synthetic
fragment/path. Требовать сохранение C document marker/generation/auth/nonce
dispatch и соответствие host/core source изменённому browser URL; это разрешённая
смена source, не ожидание прежней полной строки C URL. Нового document Starting
и нового document completion для продвижения такого контроля не ждать.
Для hash **не требовать прежний browser entry ID**: новый same-document item
не равен новому документу. Реальные snapshots отдельно фиксируют изменения
entry order/IDs, не подменяют их URL stack. Отсутствие Starting при hash не
доказывает работу cancellation subscriber и не считается ошибкой само по себе.

Основание различения: Microsoft объединяет разные history entrypoints в
BackOrForward; same-document fragment navigation не вызывает Starting и не
меняет navigation ID. DOM go(-2) задаёт delta, а go(0) имеет отдельную reload
семантику — не заменять один другим.
[NavigationKind](https://learn.microsoft.com/en-us/microsoft-edge/webview2/reference/winrt/microsoft_web_webview2_core/corewebview2navigationkind?view=webview2-winrt-1.0.4129.50),
[Navigation events](https://learn.microsoft.com/en-us/microsoft-edge/webview2/concepts/navigation-events),
[HTML History](https://html.spec.whatwg.org/multipage/nav-history-apis.html#dom-history-go).

Никакого production interception owner этим тестом не устанавливается:
ранний subscriber остаётся test-only construction. Не покрываются все gestures,
browser shortcuts/context menu, arbitrary script deltas/frames, late subscriber
cancellation, snapshot atomicity или logout/recreate/session fence. Прежние
GET/POST/CDP/cancel controls, strict errors/counts/cleanup остаются неизменными;
generic history disable и refusal-as-PASS недопустимы. После frozen delta нужен
отдельный code-reviewer SOURCE gate перед любым runtime.

Main сообщил ongoing stage7 session73863; reviewer не читал live/terminal stage7
logs/result и не квалифицировал его runtime. Текущую source216 freeze нельзя
нарушать подготовкой новых tests во время этой компиляции/запуска; этот gate
оценивает следующий шаг после отдельного source checkpoint. Единственная запись
reviewer — разрешённый report append после read-only анализа; code, VM, build,
Git, norms/tasks/checklist markers не трогались. Full T103/full feature остаются
непринятыми, исходный POST RED этим заключением не исправлен.

## Stage7 saved runtime: build/cleanup GO; focused7 overall RED

Независимо полностью прочитаны завершённые `t103-history7/run.log`,
`result.json`, `run.err` из `/Users/yshishenya/Documents/graf-f200-public458.po8CtB/`.
Это отдельная квалификация после terminal, не результат будущего шага 2.
Сам reviewer ничего не запускал и не обращался к VM.

Контрольные суммы пересчитаны по сохранённым байтам:

- `result.json`: 1754 B, SHA256 `00ee6634f67ab73293abd3aae3a669c2e87a3f03e356c9f2ec193d244cfbede3`.
- `run.log`: 15847 B, SHA256 `e86fba0a512739bd96fda4fcbee23a8660c1c9db3e0d5433af588595fad53032`.
- `run.err`: 0 B, SHA256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.

Receipt: `terminal=true`, preflight/staged/postflight=216,
manifest `2891adb4b792c01d38415a7765ea80cbabeaf30034f5edf6f9a5af2975380271`,
`run_exit=1`, `failure=NATIVE_RUN_FAILED`, elapsed=187151 ms,
`owned_processes=0`; installed/device_started/real_account=false,
server=loopback-synthetic. Manifest повторно прочитан: 216 уникальных путей,
все 216 текущих source hashes совпадают. Все пять сохранённых wrapper/cert/key
input hashes совпадают с receipt; содержимое private key не выводилось.
Полную guest staged/postflight сверку подтверждает receipt, не отдельное
самостоятельное чтение guest reviewer: на Mac сохранены не все 216 staged files.

Log подтверждает `arm64_x64`, первый compiler `HostARM64/x64/cl.exe`, 54 свежих
TU и `T103_NATIVE_FIXTURE_BUILD=PASS`; fixture PE SHA256
`961473347486b330f08861e6b72860a5cccda132cf2f18417607c224ceb8b00d`.
Main отдельно сообщил terminal Check-Terminal session99486 exit0: actual guest
PE имеет тот же SHA, owned/profile=0, включая exact GUID commandline. Это
дополнительное свидетельство main; reviewer не выполнял этот guest check.

Все семь выбранных cases завершены: PASS для `login-post400`, `history-get`,
`history-entry`, `history-entry-same-url`, `cancel-before-start`; FAIL для
`history-post` и `history-host-same-url`. Для каждого case browser exit PASS,
synthetic server exit0. Итог ровно `T103_CASES_PASSED=5 REQUESTED=7`.

Новый actual-host same-URL тест дал содержательный RED: до traversal реально
успешны A/B/C с IDs 5/6/8, phase1 имеет POST_DOCUMENT=1; после real host.back
phase3/nav5: success=0/status=0/error=0/state=0/document=0 при source_matches=1,1.
Следовательно, совпадение URL не подтверждает восстановление документа или entry.
До успешного восстановления A и последующего forward C тест не дошёл; их PASS
не заявляется. Финальные counts `2 0 0 0 0 1`: ровно один POST, без наблюдаемого
повторного POST, но это не успешный возврат. Ошибка не подменена timeout/build
failure. Почему navigation завершилась status0/error0, этими данными не доказано.

Original `history-post` остаётся RED на том же phase3/nav5 с unavailable document
и counts `2 0 0 0 0 1`; Cancel guard не исправил этот путь. CDP diagnostics
действительно восстановили entry IDs 5/8, но это другой управляющий путь и не
доказательство исправности native back/forward. `cancel-before-start` снова PASS:
cancelled nav3/error14, затем nav4 success200/state2; это прежний контроль,
не ещё не написанные BackOrForward cancellation tests шага 2.

Bounded вывод: saved build/terminal/cleanup evidence GO, focused7 runtime RED.
Прежние stage6 18/19 сюда не перенесены; default20 не запускались. Requirements/
analyze GO C0/H0 для следующего test-only шага 2 сохраняет ограничения выше;
его source/runtime review ещё впереди. Никаких code/VM/Git/norm/task/checklist
изменений или повторных запусков; только этот append. Full T103/full feature
не принимаются.

## Stage8 final freeze: diagnostic SOURCE GO C0/H0; correction of parity oracle

Область: полностью прочитана actual delta трёх tests vs frozen stage7,
связанные event/callback/helper paths и все три stage8 wrappers. Использован
code-reviewer; вместо Git/preflight — read-only byte comparison по manifests,
как прямо ограничено пользователем. Риск остаётся high-risk F200/T103; это
scoped test-only SOURCE review внутри прежнего плана, не новый low-risk product
lane, не build/runtime acceptance и не одобрение production broker.

Во время чтения main superseded два ещё не запущенных checkpoint:
`7bb6f2b32888375dd049c091220c8d124c96a917c3956c30f83d4c605683f616` /
C++ `92baf0a1f3affb605cdcdb99407feb4024b3444f24dae37a38f25f07b63482f5`, затем
`485d3fbbbdcb24b31172f5735cb72ce882a8598551512073d0683828b25fcdf5` /
C++ `18c41c6e7c8143919159a3dfe2f56dfa6f548cfdc66b78829a79271f8e9a0113`.
Они не получают SOURCE GO. Финальная повторная сверка:

- source216 `4f107b439792aac321f77dd254bfed94d3334d004e8d2dac670b0a92e9995619`:
  216 unique paths, current mismatch0; prior побайтно равен stage7
  `2891adb4b792c01d38415a7765ea80cbabeaf30034f5edf6f9a5af2975380271`.
- C++ `41290967b19f16cb0825b2bf35d7922bc351b4648400459e35fb32bd787f3e14`.
- Python `55e04722aec3927ea24cb19ce6608fd54a3c56e4c676d400e4535e4057eb85b4`.
- Runner `6d6406935e184bda71603ff93af27a4b9d85587d458857b5cf12ebad121f2ed3`.
- Changed paths ровно эти три; current/staged hashes совпадают. Product host
  current/staged неизменён: `a68f2ec8a2696204e25167a2d90261f41d3e839794453bed2a6e28b659d7b2e6`.
- `Run-History.ps1` SHA `c2220541db215596251af854e131197b2ecf7c73114dc5e4d1f5d1d2a9657ed2`;
  `Invoke-Runner.ps1` SHA `c94840e5d61bd800c92528a04d2b510c79f4db87529deca87726ce32ebbf35a7`;
  cmd неизменён `0a75f74b7466383a1cafc79665c5daf61c48f6e5a831dce6bc958c09eae0d856`.

Wrappers vs stage7: только prior/current manifest bindings и selected10 = прежние7
+ `cancel-history-host`, `cancel-history-script`, `history-same-document`.
Cert/key прежние; SDK includes, arm64_x64/compiler ordering, fresh project-derived
54 TU, /W4 /WX, per-case deadline35s/fixture20s+browser close10s, parent600s,
GUID/profile identity, source/runtime/input postchecks, terminal receipt,
owned-child-only termination и strict nonzero failure propagation не ослаблены.
Canonical default теперь23, но wrapper выбирает10, не default23. На момент
последнего чтения stage8 result/log/err ещё отсутствуют; запуска reviewer не делал.

### Проверка нового oracle и асинхронных путей

C++371–406,449–560: настоящая A/form-POST-B/C preparation остаётся product-driven;
проверяются POST marker/value, ready/source/gen/auth и разные actual entry IDs.
CDP navigation steering остаётся только historyEntryScenario; новые cases
используют CDP исключительно для наблюдения. Host вызывает real back(), script —
реальный history.go(-2). Subscriber959–987 зарегистрирован до product attach;
после phase2 он требует фактический target/kind, записывает cancelled nav ID и
Cancel(true), а не подделывает completion или authority.

Forwarded XAML NavigationStarting несёт CoreWebView2NavigationStartingEventArgs:
это не отдельный DTO без NavigationKind. Проверены [WinUI example](https://learn.microsoft.com/en-us/microsoft-edge/webview2/get-started/winui),
[pinned Core args API](https://learn.microsoft.com/en-us/microsoft-edge/webview2/reference/winrt/microsoft_web_webview2_core/corewebview2navigationstartingeventargs?view=webview2-winrt-1.0.4129.50)
и [Microsoft forwarding implementation](https://github.com/microsoft/microsoft-ui-xaml/blob/main/controls/dev/WebView2/WebView2.cpp):
FireNavigationStarting передаёт те же args. Последний upstream source не является
самостоятельным доказательством байтов установленного SDK/runtime. Истинный
kind/event ordering и доступность интерфейса всё равно подлежат actual runtime
проверке; SOURCE review не заменяет compile.

C++562–606 retained observer не может перепрыгнуть phase: callback проверяет
phase/probeExit, затем постоянный C generation/auth baseline, ready/source и
latched controlLostAuthority до записи controlEntryVerified. Для отмены нужны
прежние C ID/count/index; для replaceState старый C entry ID НЕ навязан, а
наблюдённый replaced ID затем обязан сохраниться перед новым hash entry.
Hash требует count/index+1, новый ID и URL обеих entries. Это bounded entry
observation, не полный аудит всех A/B IDs и не атомарный browser transaction.

C++609–665: replace/hash — отдельный isolated case, после собственной A/B/C
подготовки; original C nav ID, generation/auth, starts и реальный DOM C сохраняются.
Два update callbacks проходят через настоящий product bridge с прежней authority,
не через ручной вызов handler. После hash перед новым GET берётся свежий completion
baseline. Main убрал неоснованный запрет любых same-document completions; допускаются
completions с прежним C nav ID, новый GET требует иной согласованный start/completed
ID, ровно +1 completion/+1 start, success200/new generation/+1 auth.
Это соответствует ограниченной гарантии [Navigation events](https://learn.microsoft.com/en-us/microsoft-edge/webview2/concepts/navigation-events),
а не предположению, что fragment вообще не вызывает событий.

C++667–739 reused cancel checker требует именно отменённый nav completion/error14,
неизменённую C authority, retained entry snapshot, реальный old-nonce dispatch,
затем новый GET-A с новым generation/auth и точными event counts. Phase/gen/nav
fences отбрасывают устаревшие DOM/command callbacks; generation failure не может
стать PASS через молча отброшенный callback: следующий baseline check либо deadline
завершает FAIL. Enqueue/command failures и missing Starting могут дать ограниченный
test failure, но без достигнутых cancellation milestones не являются доказанным
product cancellation RED. C++697–698 mechanical rename documentIsC устраняет
затенение outer expectC; другой semantics delta против прочитанного18c нет.
Новых блокирующих compile/false-PASS/stale дефектов по SOURCE не найдено; compile
не запускался. Python сохраняет реальный POST и запрет GET-B; runner требует
ровно POST1, GET3–4, прочие counts0, fixture exit0, drained server exit0/empty err.

### Существенная коррекция: original-entry diagnostic НЕ равен Mac parity

Независимо прочитаны реальные файлы основного Mac checkout (не Windows frozen
Mac-копия, которая старее):
`/Users/yshishenya/Documents/crisp/apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetWebView.swift`
SHA `ba955ff6dab10d6c32fcf64db01ce80bedc019287c97be9c3824d32aa91c62d8`, и
`/Users/yshishenya/Documents/crisp/apps/macos/Shared/Tests/DesktopCabinetWorkspaceTests.swift`
SHA `43c638b988237c60c04432d7b27be1ac5836ea5313a623a5de7f9863da830110`.
Принадлежность merged F136 commit0648784... сообщена main; Git/commit identity
reviewer не проверял и Mac tests не запускал.

Mac goBack214–272/preferredBack818–838/isSafeHistoryDocument869–879 подтверждают:
unsafe items и unsafe URLs исключаются. Commit483–491 POST-B на URL A делает
этот URL unsafe; synthetic finish GET не снимает запрет. Только настоящий
подтверждённый safe GET finish505–511 может снова сделать URL safe, сохранив
запрет старого unsafe POST item. Для A/POST-same-A/C без такого fresh GET
из meetingDetail C backDecision49–76 выбирает meetingsList fallback, если нет
другого safe item и допустима сессия. GoBack243–267 грузит настоящий fallback GET
и сохраняет безопасный C как syntheticForwardRequest; forward275–305 может
загрузить его заново. Это допускает новые browser entry IDs для A и C.
Expired-session проверки и attach/detach/commitPendingSessionBoundary725–737
ограничивают восстановление: synthetic forward не является универсальным
URL-stack или разрешением вернуть protected документ через границу сессии.

Точный Mac test177–272 testNewGetAfterPostRestoresHistoryWithoutReplayingOldPost
готовит GET-same / POST-same / GET-next / NEW GET-same / GET-next (также reload),
потом native back/forward; старый POST item отдельно отвергается coordinator,
POST count остаётся1. Это НЕ Windows A/POST-same/C без fresh GET rehabilitation.

Поэтому прежнее требование original A ID5/C ID8 отзывается как обязательный
product-parity oracle. Оно остаётся честным отдельным original-entry diagnostic
для CDP/raw-host paths; будущий корректный fallback с новым A ID не должен
считаться product regression только за несовпадение старого ID. Аналогично
cancel-history-host target B/kindBackOrForward — конструкционное доказательство
нынешнего raw core.GoBack, не требование всегда выбирать B после нового owner.
Будущий безопасный skip/fallback потребует адаптации diagnostic target/kind и
отдельной проверки product outcome; нельзя требовать BackOrForward от fresh GET.

Product oracle должен различать safe selected history entry и разрешённый
fresh GET fallback по реальным request/document evidence: успешный approved GET
document с новой authority при загрузке, отсутствие POST replay/restore unsafe
item и корректный доступный forward с учётом session fence. Нельзя выводить
method из URL, делать произвольный GET для unsafe POST URL или заводить свой
общий URL stack. Конкретную production owner реализацию этот review не выбирает.

Stage7 history-host-same-url не переименовывается в PASS: там нет ни успешного
original entry, ни успешного fallback document (state0/document0). Но failure
строгого original-entry assertion в будущей иной реализации сам по себе уже
не докажет нарушение Mac parity; прежние saved результаты не переписываются.

Итог: bounded diagnostic SOURCE GO C0/H0 для final4f107/412909, с обязательной
коррекцией интерпретации выше. Не GO для цели «всегда original A ID» и не
обязательство будущего owner сохранять raw target B. Runtime stage8 отсутствует;
прежние7/19 counts сюда не переносятся. Только own report append; code, VM,
build, Git, нормы/tasks/checklist markers не менялись, full T103/F200 не приняты.

## Stage8 completed runtime: three new controls PASS; focused10 overall RED

Независимо полностью прочитаны завершённые BASE/t103-history8 run.log (472
непустых строк журнала до завершающего newline), result.json и пустой run.err.
BASE = `/Users/yshishenya/Documents/graf-f200-public458.po8CtB/`.
Reviewer не запускал VM/build/tests/guest checks; применён code-reviewer для
сопоставления результатов с ранее проверенными SOURCE assertions, не для нового
изменения реализации. Единственная запись — этот append.

Пересчитанные SHA256:

- run.log, 21999 B: `2173d7a61984b363afc9f2ffd440f9179d28eeda4e7990b79fdce535690017f7`.
- result.json, 1896 B: `a0f8023cfb414aebcd6129578331f4a6de2c82f25e86af1798be1ae1e63383d2`.
- run.err, 0 B: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.

Receipt terminal=true, preflight/staged/postflight216,
manifest `4f107b439792aac321f77dd254bfed94d3334d004e8d2dac670b0a92e9995619`,
run_exit1/NATIVE_RUN_FAILED, elapsed293306 ms, owned_processes0,
installed/device_started/real_account=false, server=loopback-synthetic.
Повторно прочитаны manifest216 уникальных путей/current mismatch0 и prior2891...;
все пять saved inputs совпадают с receipt и SOURCE checkpoint выше. Три tests
и product host current/staged совпадают с final412909/55e047/6d6406/a68f...;
нового production delta нет. Guest pre/staged/post216 подтверждает receipt,
не самостоятельное чтение VM reviewer.

Log1–64 подтверждает arm64_x64, первым HostARM64/x64/cl.exe, 54 TU и buildPASS;
/W4 /WX установлены hash-bound runner, а не выведены отдельной compiler command
в log. Fixture PE SHA `20971ee4cd9733232b46f90412197e5a265466bf39a08d153aa6901780fb87fe`.
Main сообщил отдельный Check-Terminal session43530 exit0 с этим actual guest PE
SHA MATCH/owned0; это свидетельство main, не выполненный reviewer guest check.
Один завершённый запуск session22824/exit1 — по main; сохранённые файлы содержат
один последовательный набор десяти cases, без свидетельства retry внутри него.

Фактический итог ровно8/10. PASS: login-post400, history-get, history-entry,
history-entry-same-url, cancel-before-start и три новых controls. FAIL:
history-post/history-host-same-url. Все10 завершились browser exitPASS/server
exit0; fixture exit0 для8 PASS, exit1 для2 FAIL. Это ожидаемая передача ошибок,
не ошибка сборки или зависание. Default23 и прежние full19 не запускались здесь.

Новые milestones:

- cancel-history-host, log344–386: реальные A5/POST-B6/C8 с ready/success200,
  затем HISTORY_CANCEL_BEFORE_PRODUCT kind1/driver host-back, nav5 error14.
  Retained phase1 C id8/count3; между отменой и nav6 нет host initializing/
  unavailable. Новый GET nav6 success200/state2, starts5/completions5,
  current_reads4/signed_out4/invalidations0; final counts `3 0 0 0 0 1`.
- cancel-history-script, log387–429: та же полноценная preparation; реальный
  script-go-minus-two дал kind1/nav5 error14, retained C8/count3, затем nav6
  success200/state2, starts5/completions5/auth4/invalidations0. Final counts
  `4 0 0 0 0 1`: дополнительный GET допускается как provisional GET-A, не
  свидетельствует о POST replay; точную причинность лишнего GET log не доказывает.
- history-same-document, log430–470: C id8/count3; replace snapshot id8/count3,
  затем hash id10/count4. Нового Starting между C/nav4 и следующим GET/nav7
  нет. Новый nav7 success200/state2, starts4/completions4/auth4/invalidations0,
  counts `3 0 0 0 0 1`. Разница nav IDs4→7 не означает три новых документа.

Сохранение source/gen/auth, старого C document и работоспособности прежнего nonce
подтверждается не отдельными числовыми log полями, а достигнутым PASS строгих
hash-bound assertions C++562–739/912–919: retained ID/index/count, generation
baseline, latched authority loss, реальный bridge callback1 для каждого cancel
и callback2 после replace/hash, затем новый generation/+1 auth на новом GET.
Nonce не выводился и вручную не задавался. Для hash также проверен сохранённый
replaced ID/URL; совпадение id8 после replace — наблюдение данного запуска,
не навязанная гарантия replaceState. Final drained counts всех трёх новых cases
дают ровно POST1, unexpected0, то есть нет наблюдаемого POST replay или GET-B.

Оба старых raw-host diagnostics остаются содержательным RED: после успешных
A/B/C phase3/nav5 status0/success0/error0/state0/document0; source_matches0,0
для history-post и1,1 для host-same-url. Оба counts `2 0 0 0 0 1`. Ошибка до
успешного документа/fallback, не только несовпадение original entry ID. Причина
status0/error0 не установлена; Cancel guard исходный POST path не исправляет.

Оценка достоверности ограниченного результата: C0/H0 — не выявлено критических
или высоких дефектов test/receipt/oracle, которые обесценивают эти три PASS.
Это НЕ C0/H0 всему production host и НЕ full T103 READY: итог focused10 RED.
Доказаны ранняя native cancellation двух конкретных drivers и отдельный
same-document control на нынешнем raw host, но не общий navigation owner,
Mac safe-fallback/synthetic-forward parity, все gestures/deltas/frames,
late cancellation/stale-callback permutations или logout/recreate/session matrix.
Предыдущая коррекция original IDs/raw target B остаётся обязательной: это
diagnostic construction, не вечная продуктовая цель. Ни existing RED, ни
будущий правильный fresh fallback не переименовываются ради этого oracle.
Никаких code/norm/tasks/checklist/Git изменений, повторных запусков или иных
действий в VM; full T103/full F200 не принимаются.

## 2026-10-22 — bounded quality gate: test-only Phase 0 same-URL permit-race

**GO для test edits, C0/H0 в требованиях этого исследовательского среза.**
Это не production SOURCE GO, не разрешение запуска и не закрытие технического
NEEDS CLARIFICATION. Проверяется именно неизвестная корреляция native CDP
команды и конкурирующего script traversal; требовать её решения до данного
эксперимента было бы подменой его цели. Новых продуктовых вопросов нет.

Прочитаны actual spec Clarifications Session 2026-10-22:661–684,
plan:3053–3093, quickstart:1277–1292, research:3289–3307, действующая
constitution 7.1.0, router/index и применимые правила worktree, Spec Kit,
product/evidence/validation. Применён speckit-analyze: только согласованность
ограниченного исследовательского допуска. before/after_analyze Git hooks
в actual extensions.yml disabled; никаких hooks/команд/Git не выполнял.
Prerequisites/governance и live OPEN #7280/#7231 подтверждены main, не выданы
за собственный повторный запуск или независимый live query.

### Checklist gate и трассировка

Независимо заново прочитаны байты всех 198 файлов checklist inventory и
пересчитаны SHA/markers: **31 файл с checkbox, 477 checked / 0 unchecked**.
Канонический inventory — sorted filename, строка `SHA256  filename\n`:
`6aaf78544635814de7c4feacc8f153eee2876226b9702bf70b0e16bfb4f351b2`.
Совпадение со всем прежним inventory точное: отсутствуют новые/изменённые/
удалённые файлы. Прежняя независимая проверка неизменных критериев повторно
использована по этим байтам; свежего полного перечитывания исторических
отчётов или повторной проверки старых runtime/source cohorts не заявляю.

К scope применимы requirements CHK004/006/007/013/019–022, security
CHK001–003/007–011/017–018/022 и UX CHK001–002/020: ownership, Mac parity,
точная граница полномочий/документа, отказы и правдивость evidence. Новый допуск
не меняет capture/storage/calendar/recovery/update предмет остальных checklist
критериев и не расширяет их исторические PASS. Нужды менять checkbox markers
или создавать новый checklist для этой Phase 0 пары не выявлено. Отметки
оценивают качество требований, не production/runtime готовность.

Связь сохраняется с FR-002/005/006 и существующими T103/#7280, T088/#7231;
задачи остаются открытыми, новых нет. Дополнительный production contract или
data model не является предварительным условием написания fixture: новый
production owner/API/persistent state не вводится. Их проектирование и полный
production-plan остаются после результата, как прямо ограничено plan END.

### Обязательные ограничения actual test/oracle для следующего source gate

1. Ровно два порядка: `history-race-native-first` и
   `history-race-script-first`; реальная подготовка GET-S → POST-S → C →
   fresh GET-S → C. Реальные distinct entry IDs и DOM markers подтверждают
   старый POST и новый GET; native выбирает ID именно fresh GET-S, script
   исполняет go(-3) именно из исходного C. Обе команды из одного UI callback,
   без ожидания первой, и обе фактические traversal попытки обязательны.
2. Наблюдения вести **отдельно по каждому NavigationId**, включая kind,
   разрешение/отмену и доступные Starting/ContentLoading/Completed факты.
   Global lastStarted/lastCompleted и финальный snapshot не заменяют журнал
   двух конкурентов: поздний safe GET не должен скрыть ранее разрешённый POST.
3. Идентичность разрешённого/восстановленного entry определять независимо от
   исследуемого URL/kind permit. Нельзя считать first-next event native-командой
   по порядку вызовов, URL, command completion или позднему правильному GET.
   Неподтверждённая идентичность означает INCONCLUSIVE, а не PASS. Доказанное
   разрешение/восстановление unsafe POST фиксируется sticky REFUTED даже при
   последующем safe GET и даже при server POST count=1 (cached restore).
4. PASS относится только к достигнутому порядку: оба конкурента наблюдаемы,
   safe GET разрешён, unsafe отменён, финальный GET identity подтверждён.
   Недостижение пары, unsupported API/наблюдения, ошибка команды, оба отменены
   или неизвестная identity — INCONCLUSIVE с ненулевым итогом runner.
   Эти два ограничения по navID/identity обязательны для SOURCE GO; обещание
   implementer включить их не является проверкой ещё не написанного кода.
5. Permit — только fixture и только гипотеза эксперимента. Нельзя вручную
   завершать product response latch, выдавать nonce/native authority или
   ослаблять текущие origin/session/document/response проверки. Только
   синтетический loopback/GUID profile, без реального кабинета, аккаунта,
   устройств, аудио или установленного GRAF. Сохраняются прежние source/PE
   bindings, fresh /W4 /WX, deadlines20/10/35s, server drain и owned cleanup.
   Прежние 23 сценария и существующие RED не удаляются и не переименовываются.

Два замечания Bohr — обязательные требования к доказательству actual теста,
а не два неустранённых HIGH в текущих нормах: plan уже запрещает PASS при
неизвестной identity и требует наблюдать оба перехода. Если actual diff не
сможет это обеспечить, source gate будет NO-GO либо эксперимент обязан честно
завершаться INCONCLUSIVE. Даже два PASS не доказывают отсутствие гонки во всех
расписаниях и не разрешают production broker. Mac fallback/single-forward и
session parity остаются целями, original IDs/raw target B — диагностикой.

### Точные bindings quality gate

| Артефакт | SHA-256 |
|---|---|
| constitution | `d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859` |
| spec.md | `e96fe93f1bb9b1a2965ad8b4e3871c1d1d98622acffa7694e932d9d1dc518435` |
| plan.md | `1cdccfcdab8f14718635277c883be838a6ac8f01f4191c2ed9d14002ed0f972e` |
| tasks.md | `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f` |
| quickstart.md | `630a9768fa1d0790bf434b29678d3f664fdf343810a993c86f09f33fae3fd6a7` |
| research.md | `5404f0af34ca763cb7103c2a74e9444db4d717a925ccf5b5e787636a15a5aea0` |
| requirements.md checklist | `91fecd3ca4c79eba15faa3543fce18f8d5db1eb7a6664701c683c460d0d5bc55` |
| security.md checklist | `0a321d6d52a4f56d8c2888bd3fa639c85a7c9dc82b5a6acdc2bc3f1bb7a40273` |
| ux.md checklist | `1a5a28f7226d7fc25bafdb8239b3d4bea2aeae0d4aad969eb89b45ec5b855801` |

Эти текущие нормы связывают только следующий test-only gate, не перепривязывают
старые frozen runtime receipts. Изменён только этот собственный report;
norms/code/tasks/checklists/Git/VM/build не менялись и не запускались.

## 2026-10-22 — stage9 SOURCE gate: negative-only permit-race

**Scoped SOURCE GO, C0/H0 для окончательных negative-only тестов и wrappers.**
Проверка выполнена code-reviewer по actual delta трёх existing test files
от frozen history8, не по большому diff от HEAD. Ничего не запускал.
Main отдельно сообщил о начале одного fresh build/focused5 после review Bohr;
это не собственное наблюдение runtime и не основание для повторного запуска.

### Старый кандидат и исправление oracle

Первоначальный cpp `858085cd34c467a908424ee0975b3fe815cc1c479d3bb7f4a19a50c676ab3981`
не заслуживал SOURCE GO: `RaceNavigation[2]` действительно разделяет два
NavigationId, но `raceScriptFromC` подтверждал только DOM marker C, не
независимую identity цели отменённого traversal. Safe final entry/GET DOM,
два starts, command acknowledgements и OperationCanceled второго события
не доказывали, что отменён именно старый POST. При неизвестной цели прежняя
ветка `race-observed-order-safe-only` могла дать неподдержанный PASS. Кроме
того, найденный unsafe ID проверялся на REFUTED лишь после удачного DOM read:
ошибка чтения могла понизить уже доказанный unsafe до INCONCLUSIVE.

Actual исправление cpp `ec3af695c1393afab7ce2f5ba835f6131f65b4c39e86b698fa861d81e15931b1`
перечитано целиком как delta к этому кандидату:

- `checkHistoryRace`:645–650 немедленно завершает REFUTED при actual old POST
  entry ID, до DOM read. Это доказательство больше не теряется при DOM error.
- DOM postAccepted также фиксирует `raceUnsafe` до дальнейшей классификации.
- Положительный путь удалён полностью: safe GET, два ID/starts и завершённые
  команды теперь только диагностические поля; итог без unsafe proof всегда
  `race-inconclusive-cancelled-target-identity` / nonzero. Другие observation
  errors и deadline также не дают PASS.
- Отдельные per-ID completed/loaded/success/error slots сохранены; глобальные
  lastStarted/lastCompleted используются для прежней preparation, но не
  заменяют записи двух race events. Первый matching URL/kind permit остаётся
  исследуемой fixture-гипотезой; второй traversal отменяется до product handler.

Ограничение важно: это поздний snapshot примерно через 1500 ms плюс DOM,
не полный независимый журнал промежуточных entry identities. Он может
обнаружить counterexample, но не гарантирует обнаружение каждого краткого
unsafe состояния и не доказывает target отменённого события. Теперь это не
скрыто веткой PASS: отсутствие unsafe observation остаётся INCONCLUSIVE.
Не требуется новый API framework или решение production unknown до опыта.
Runtime REFUTED необходимо квалифицировать по actual log/IDs и достигнутым
командам; INCONCLUSIVE нельзя переименовать в безопасный порядок или GREEN.

### Preparation, server, runner и frozen scope

Пять actual подготовительных документов и generation/auth/DOM проверки
сохранены: GET-S / POST-S / C / fresh GET-S / C; `checkHistoryEntry` требует
пять distinct IDs в правильном порядке, native target — fresh GET entry.
Команды выдаются из одного UI callback без ожидания первой, в двух порядках.
Script подтверждает marker C; это наблюдение issuer document, не доказательство
конкурентного target. Сервер действительно различает GET history-a и actual
form POST history-b по тому же пути с postAccepted; C имеет другой путь.

Внутренний runner добавляет два ValidateSet имени, но default23 не меняет.
Для race counts допустимы GET4..6 и ровно POST1, остальные четыре counters0;
это сетевой контроль, не доказательство отсутствия cached POST restore.
REFUTED/INCONCLUSIVE передаются через fixture nonzero → case FAIL → runner
nonzero → outer NATIVE_RUN_FAILED; ожидаемый отрицательный опыт не маскируется.

Полностью прочитаны actual Run-History.ps1, Invoke-Runner.ps1 и run.cmd.
От history8 изменены только selected cases/manifest bindings: selected5 —
history-entry-same-url, cancel-history-host, history-same-document и два новых
race. Старые history-post/host-same-url RED не удалены из default23 и не
превращены в PASS; focused5 не означает default23 или full T103.
Прежние compiler/SDK, ARM64-host/x64-target, fresh compile, /W4 /WX,
source216 pre/staged/post, runtime DLL/input hashes, GUID profile, deadlines
20s/close10s/case35s/outer600s, owned child-tree timeout и cleanup guards
не изменены. Actual compilation, terminal PE, owned0 и оба порядка пока
не квалифицированы; read-only AST PASS сообщён main, не выполнен reviewer.

Финальный local manifest216/current match независимо проверен: **0 mismatch**.
Его delta к history8 — ровно три test files; staged copies этих трёх и host
побайтово соответствуют manifest. Stage содержит лишь копируемые файлы поверх
prior guest baseline, не отдельную полную копию всех 216; это предусмотрено
wrapper preflight. Production host SHA остаётся
`a68f2ec8a2696204e25167a2d90261f41d3e839794453bed2a6e28b659d7b2e6`.

| Binding | SHA-256 |
|---|---|
| history8 / stage9 prior216 | `4f107b439792aac321f77dd254bfed94d3334d004e8d2dac670b0a92e9995619` |
| final stage9 source216 | `4b9391fee3b1fce378ac7facc28f9a685113b7a5fe50d2b17cf35c647a98da93` |
| C++ | `ec3af695c1393afab7ce2f5ba835f6131f65b4c39e86b698fa861d81e15931b1` |
| Python | `80d68c8b4401172d8c2907149569d844111f97fe0205d3aee5b0594ba8fc88c1` |
| internal runner | `aabfa7165e379f1f84c9b5826ced3f771aa863edf8a7172f24fe8f28a24e76ec` |
| Run-History.ps1 | `37b2c0cf85d054e7bc786b40cb7969bfc0840e85041cdcd13577bd591e11c54b` |
| Invoke-Runner.ps1 | `89282aee76fc7881ca671206e5c095085eda48a91d3eedbd469ba8141109f4eb` |
| run.cmd | `0a75f74b7466383a1cafc79665c5daf61c48f6e5a831dce6bc958c09eae0d856` |
| plan.md current | `05b1a2fb7e5f5a722d87c2f714a997ba7b2f4714d05d6a94ab914d1f59a29722` |
| quickstart.md current | `594141223b87e0ee7012d1099bb83d222789f3e32c0babfba74604cc443c1c70` |

Actual новые строки plan END/quickstart END прочитаны: negative-only,
cancelled target unknown, no PASS, unsafe ID decisive before DOM — явно
записанные ограничения actual experiment, не ослабление положительного oracle.
Предыдущий stage9 manifest `4a5adac2...` с cpp `858085...` superseded/unrun по
сообщению main; текущий SOURCE GO относится только к final4b9391/ec3af6.

Это допуск существующего bounded negative-only build/focused5 scope, не
production GO и не обещание GREEN. Результат требует отдельной сохранённой
runtime qualification; никаких автоматических повторов. Нынешний технический
NEEDS CLARIFICATION, полезная Mac safe history/fallback/single-forward/session
семантика, два прежних RED и T103/T088/full-feature gates остаются открытыми.
Reviewer изменил только этот report; код/нормы/checklists/Git/VM не менял.

## 2026-10-22 — stage9 saved-runtime qualification: 3 PASS / 2 INCONCLUSIVE

Полностью прочитаны сохранённые 319 строк run.log, result.json и пустой run.err
из `t103-history9`. **Один завершённый focused5: три прежних PASS, оба новых
race INCONCLUSIVE; ни safe-candidate, ни REFUTED не установлены.** Raw cases
остались FAIL/nonzero и не переименовываются в GREEN. Нового запуска нет.

### Binding, build и terminal

- run.log: 14752 B, SHA
  `03c24655be057fd1c219306b114a3256e70c2ae3e0fe115bd9611a98a08e36b4`.
- result.json: 1701 B, SHA
  `5cca973d9132b00c53b66aa136574e5a55d3b1b669cd257092ff097915585191`.
- run.err: 0 B, SHA
  `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
- Receipt terminal=true, preflight/staged/postflight=216, manifest
  `4b9391fee3b1fce378ac7facc28f9a685113b7a5fe50d2b17cf35c647a98da93`,
  run_exit=1, failure=NATIVE_RUN_FAILED, elapsed116834ms, owned_processes=0.
  device_started/real_account/installed=false; server=loopback-synthetic.
- Independently saved prior216 SHA matches history8 `4f107b43...`; all five
  frozen wrapper/certificate input hashes match receipt. Three staged tests
  and unchanged staged production host match final manifest. Bound wrapper
  checks post-source/runtime DLL/input invariance before NATIVE_RUN_FAILED;
  terminal receipt is consistent with those checks having completed.
- Log: ARM64-host/x64-target environment, 54 actual source-TU names and
  T103_NATIVE_FIXTURE_BUILD=PASS; fresh /W4 /WX belongs to the reviewed bound
  runner, not an independently repeated compiler invocation. Logged PE SHA
  `6a2b1bbf8fcf178212b2233b06ef59f462b050154ffa1b46a63e3a9af4f2af94`.
  Temp GUID `ca09876385184ec8b7b5ded18d6456dc`; each of five cases has its own
  case profile, exact environment/profile checks and starts-before-check=0.
- All five T103_BROWSER_EXITED=PASS and all five SYNTHETIC_SERVER_EXIT=0.
  Separate actual guest PE/process check90343 was still ongoing per main at
  qualification time: logged PE/source-bound cleanup is accepted here, but
  actual guest PE/commandline-profile owned0 confirmation is not yet claimed.

### What the two race cases actually reached

Both prepared real GET-S5 / POST-S6 / C8 / fresh GET-S10 / C12, with successful
document/generation/source/post-marker checks and five distinct entry IDs.
POST phase1 is actual form POST, not an address-derived method.

| Observation | native-first | script-first |
|---|---|---|
| Command callbacks / native ack | 2 / 1 | 2 / 1 |
| Script execution confirmed from C | **0** | **1** |
| Race Starting events | **1**, nav7 kind1 allowed | **2**, nav7 kind1 allowed; nav8 kind1 cancelled |
| nav7 completion | status200/success1/error0 | status0/success0/error9 |
| ContentLoading | nav7 observed | no race ContentLoading observed in saved log |
| nav8 completion | no second Starting/nav8 | status0/success0/error14 OperationCanceled |
| Final snapshot / DOM bits | entry10, SAFE_GET1, bits49 | entry12, SAFE_GET0, bits48 |
| UNSAFE_POST_SEEN | 0 | 0 |
| RACE_TWO_STARTS_OBSERVED | 0 | 0 |
| Final network counts | `5 0 0 0 0 1` | `5 0 0 0 0 1` |

Native-first (log238–248): safe fresh GET10 restored, but only one traversal
Starting exists and SCRIPT_FROM_C=0. Two command callbacks are not two actual
traversals; execution of go(-3) from the intended C is unconfirmed. Therefore
the required concurrent unsafe competitor was not demonstrated.

Script-first (log297–309): C execution is confirmed and two distinct Starting
IDs were observed. However nav7 failed with numeric error9 and did not produce
a successful commit/ContentLoading; nav8 was cancelled with error14. The
per-ID reached predicate remains false, not merely a global completion count.
Send order is not independent proof of which target belonged to nav7/nav8;
do not assign old POST to either ID from order or common URL. Final browser
entry is original C12, host state0, not ready; DOM bits48 contain bootstrap/
native-ready booleans, not proof of current production authority or a safe
committed GET. No root cause is inferred for numeric error9.

Both fixture results are explicitly `race-inconclusive-cancelled-target-identity`
and exit1. Counts prove exactly one server POST, not absence of cached POST
restore. Neither late snapshot showed entry6 nor DOM postAccepted, so this
run contains **no observed REFUTED proof**. This does not exclude a missed
intermediate unsafe state: the observer remains a late snapshot, not a full
commit/entry journal. Neither case establishes the required safe/unsafe pair.

### Controls and limits of acceptance

Three selected controls genuinely PASS: history-entry-same-url (CDP diagnostic
entry5↔entry8, starts/completions5/5, counts4/POST1), cancel-history-host
(early kind1 cancellation nav5/error14, retained C8, next GET nav6/200,
counts3/POST1), history-same-document (replace entry8, hash entry10, next GET
nav7/200, counts3/POST1). These are this focused5's results, not reused18/19
or8/10. They do not fix or retest production history-post/host-same-url RED.
Default23 and full T103/session/Mac fallback/installed/feature matrix were not
run. Receipt and log consistently preserve 3/5 plus two honest INCONCLUSIVE.

**C0/H0 for integrity of this bounded saved result and its non-PASS
classification**, not for a production history mechanism. The technical
correlation unknown remains unresolved; neither permit safety nor its
refutation follows. Qualification ends with this single experiment; no new
API research, rerun, VM action, source/norm/task/checklist/Git change.

### Stage9: отдельное actual guest подтверждение main

После сохранённой квалификации main сообщил terminal Check-Terminal90343
exit0: actual guest PE
`6a2b1bbf8fcf178212b2233b06ef59f462b050154ffa1b46a63e3a9af4f2af94`
MATCH и owned0. Это отдельное подтверждение main, не собственный VM вызов.
Оно закрывает отмеченное выше ожидание actual guest PE/process check,
не меняет 3 PASS / 2 INCONCLUSIVE и не доказывает безопасность permit.

### Предварительная оценка следующего кандидата, без production GO

Предложенный main вариант конструктивен: не переносить Mac URL-exception
для unsafe/unknown same-URL записей; разрешать history URL только если все
его actual entries по отдельности подтверждены GET в текущей сессии; иначе
отказывать BF по этому URL, даже после fresh GET rehabilitation. Browser
history остаётся источником порядка; другой ближайший safe GET и ограниченный
meeting-detail→fresh-list fallback/single-forward сохраняют полезный путь.
Это документируемое защитное отличие от Mac, не доказанный production fix.

Минимальные доказательства перед его принятием: (1) положительный actual
native Back/Forward по чистым confirmed-GET entries, а не только отказы;
(2) POST-S/fresh-GET-S ambiguity не разрешает старый POST, но оставляет
nearest other safe GET либо оговорённый fresh fallback и один forward;
(3) pending concurrent navigation/session/revision change не выдаёт authority
невыбранному или stale документу. Unknown/неполная классификация одного из
same-URL entries должна исключать URL из permit, а не считаться GET.

Безопасность множества допустимых entries не равна корреляции конкретной
CDP-команды: другой confirmed GET того же URL всё ещё может быть не selected
entry. Поэтому terminal selected-ID check до nonce обязателен, с отказом при
неподтверждённом/устаревшем результате; его корректность и commit/response→
entry classification не доказаны этим опытом. Запрет новых non-BF при pending
и generation/revision fences — требования будущего bounded review, не уже
проверенный код. Нового API-исследования или реализации здесь не выполнялось.

## 2026-10-22 — выбранный SafeHistory: portable Phase1 pre-code gate

**GO, CRITICAL0 / HIGH0 — только portable Phase1 tests-first**: snapshot,
proofs, all-GET guard, selection, revision/session в существующих
`apps/windows/RecApp/Web/WebViewRoutePolicy.h`, `.cpp` и
`apps/windows/Tests/GrafWindowsContractTests/WebViewRoutePolicyTests.cpp`.
Lane high-risk-product, existing F200. Это допуск начать RED→GREEN, не SOURCE
GO ещё не написанного API и не native integration/reset/host-authority GO.

### Нормативная проверка и checklist gate

Применён speckit-analyze: actual spec Session2026-10-22:661–694, выбранный
plan END:3100–3173, data-model END:709–722, bridge END:565–574, quickstart END:
1297–1316 и новый research decision:3347–3376 полностью прочитаны. Последний
append включён: прежний same-URL candidate отвергнут, ALL-entries guard закрывает
POST rename-пробел без доверия уведомлениям; actual runtime reset проверяется
позже. Исторический experiment-only gate не подменяет выбранный новый срез.

Active feature.json, constitution7.1.0, root router/index и применимые правила
worktree/Spec Kit/product/validation/tracker прочитаны самим reviewer. Для
ранее лично прочитанных неизменных guidance/constitution дополнительно сверены
свежие SHA; старые validation journals заново не аудировались. Analyze hooks
disabled в actual extensions.yml; hooks/CLI prerequisites/Git/remote reviewer
не запускал. Required artifacts существуют; actual pointer — F200,
codex/200-windows-followup, b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1.

Все **198 файлов** checklist inventory заново byte/hash проверены: **31 файл
с checkbox, 477 checked / 0 unchecked**, exact inventory неизменен:
`6aaf78544635814de7c4feacc8f153eee2876226b9702bf70b0e16bfb4f351b2`.
Канон — sorted filenames, строки `SHA256  filename\n`. Прежний независимый
обзор неизменных критериев повторно использован по точным байтам, не как новая
приёмка исторических source/runtime cohorts.

Свежий semantic review delta выполнен по requirements CHK001/002/004–007/
013/019–022, security CHK001–003/007–011/017–018/022 и UX CHK001/002/019/020:
ownership, измеримость отказов, session/document boundary, отсутствие нового
bridge authority, privacy/evidence и security deviation согласованы. Остальные
критерии не получают нового предмета: capture/custody/calendar/egress/installer/
release этим portable scope не меняются. Нужды менять checkbox markers нет;
477 checked не означают разрешение всей F200 или native Phase2.

### Scoped coverage и обязательные Phase1 oracles

| Группа | Нормативный oracle / existing ownership |
|---|---|
| Полезная история | Browser-owned порядок/IDs, ближайший отличный точный URL в обоих направлениях, meeting Back filter; positive all-GET cases обязательны. T103, FR-002/005, SC-002. |
| Глобальный quarantine | POST/unknown ЛЮБОГО URL, включая current/forwardList, запрещает BF; fresh GET не реабилитирует old POST ID. T103, FR-005/006. |
| Proof identity | Snapshot не proof; exact ID+URL+session; trusted final GET/cabinet acceptance — input будущего adapter. Исчезновение/смена URL/new ID не наследуют proof. T103/T088. |
| Bounds/failure | Duplicate/negative ID, invalid index, >128 entries, empty/oversize/invalid URL не оставляют старый выбор. T103. |
| Lifetime | Stale revision/session отказ; logout/expiry/account/workspace/recreate clear; pending/loading/reset исключают повторное действие. T103/T088. |
| Reset model boundary | Другой оставшийся ID не становится GET; сохранение proof требует того же accepted ID/URL/session/generation. Pure value/state checks допустимы; reset API не Phase1. T103. |

Шесть групп прослеживаются к существующим tasks; новых непокрытых задач или
дубликатов нет. tasks.md: **120 task строк, 0 duplicate IDs**, SHA неизменен;
T103 и T088 остаются `[ ]`. Ownership — T103/#7280 и T088/#7231 по existing
связям; нового live issue query reviewer не делал, issues не создавал/закрывал.
SC-002 целиком не принимается: это только policy-часть.

Для actual tests нельзя спутать уход с документа и replacement самой записи:
useful all-GET BF сохраняет proofs оставшихся неизменных ID/URL; действительно
замещённый entry теряет proof до нового подтверждения. Cancellation до замены
сохраняет current proof. Positive/negative controls следуют из plan3121–3134
и исключают always-quarantine/always-deny реализацию.

Constitution conflicts, blocking ambiguity или unresolved HIGH именно для
portable Phase1 не обнаружены. Spec явно описывает Windows security deviation,
сохранение полезной all-GET истории, safe recovery и неочистку cookies/account/
user data. Это документированное защитное отличие, не молчаливая отмена parity.

### Граница GO и exact hashes

Native response→entry binding, pending до snapshot, блок ALL navigation в
reset interval, actual reset ACK/runtime/same-ID singleton, terminal selected-ID
до nonce и fallback/singleForward host wiring остаются Phase2 после SOURCE
review policy. Их нельзя подменять fake callbacks, ручным nonce/latch или новым
bridge. Их native доказательства не являются условием написания pure policy.

| Артефакт | SHA-256 |
|---|---|
| constitution | `d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859` |
| spec.md | `04f708f040e23fcca0f1e8d386c181421c5da2c81a37033155ad9f3a0536ed92` |
| plan.md | `7b84e844149a1630b8564e43d832efd2595241d9822399a3b1c42c80c860a050` |
| data-model.md | `338653d8c905eb5db07e33394bbf441978df5b49899cb88a0203047017a885a7` |
| contracts/windows-native-web-bridge.md | `2d31f0f9bd1548ca592561062788aa87a521cf8f9661bf320a7c9177cb456dc5` |
| quickstart.md | `e94e94fdf40af09f71b1de9f0a7a47d0a6d86a010e2cf6da4a2c986c501f0cbb` |
| research.md incl chosen decision | `af208357cb36658a629e1daf1c0af9b82339fba45a9cafe57bec8c871e5f890e` |
| tasks.md | `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f` |

Pre-code policy h/cpp/tests SHA соответственно:
`484164af5f6bf4cd4082705288ac35ba646579b0c89b42200eac9d6c9162c258`,
`57c66b187311d606727d7d0b776b462ca20fbc1a717a6d219ed61e19e5c5c169`,
`df79e84897bf3828ea9e2b2f0359e8e460228c42192e8f2143416d4b213c6bd9`;
host unchanged `a68f2ec8a2696204e25167a2d90261f41d3e839794453bed2a6e28b659d7b2e6`.
Actual diff придёт отдельно для SOURCE review. Тестов/сборок/VM не запускал;
изменён только этот report. Norms/code/tasks/checklists/Git/GitHub не менялись.
T103/T088/T097/full F200, installed/native/release acceptance остаются открытыми.

## 2026-10-22 — SafeHistory portable Phase1: SOURCE review последних трёх файлов

**SOURCE GO, CRITICAL0 / HIGH0 — только чистая portable policy Phase1.**
Применён code-reviewer. Прочитаны весь новый SafeHistory API, методы cpp:435–517,
safeHistoryContract:10–136 и вызов из main:254; существующие URL/route helpers,
которые использует новая политика, проверены по фактическому коду. Блокирующих
ошибок корректности или переусложнения в этом срезе не обнаружено. Это не native
integration/reset/installed GO и не утверждение, что original history-post исправлен.

### Exact source bindings и отсутствие посторонней дельты

| Файл | SHA-256 |
|---|---|
| apps/windows/RecApp/Web/WebViewRoutePolicy.h | `fb5c46379a940b251084b9438f1b5ad2727fc06fd5d02d92db16703b5a3f10a3` |
| apps/windows/RecApp/Web/WebViewRoutePolicy.cpp | `2f2de7dc0f6d686d1ead5363d4a21c608953d9d0521c2ff2ab27a032543a9ced` |
| apps/windows/Tests/GrafWindowsContractTests/WebViewRoutePolicyTests.cpp | `4cb2d26bc6861ae0140387c42d6329f85ff29a2f301aced5ef801feb3a6b1305` |

Это последние байты после усиления положительных предусловий eviction/session,
stale POST callback, meeting review/share/report controls и явного `<utility>`.
Без записи файлов reviewer удалил из прочитанных строк только новый API/методы,
safeHistoryContract/main-call и добавленные include. Остатки дали ТОЧНЫЕ три
pre-code SHA из предыдущего раздела: `484164af…`, `57c66b18…`, `df79e848…`.
Значит прежние billing/routes/response bodies и прежние тесты не переписаны.
Actual WebView2Host.cpp SHA остаётся
`a68f2ec8a2696204e25167a2d90261f41d3e839794453bed2a6e28b659d7b2e6`.

Повторно прочитанный Phase1 plan:3116–3134 и свежие SHA всех семи нормативных
файлов точно совпали с таблицей pre-code gate выше. Его requirements/checklist
решение повторно используется без расширения scope: 198/31/477 checked/0 unchecked,
inventory `6aaf78544635814de7c4feacc8f153eee2876226b9702bf70b0e16bfb4f351b2`;
нового полного inventory-аудита в этом SOURCE review не заявляю.

### Проверенные свойства и границы ответственности

- Snapshot сам не даёт GET proof. Сохранение proof требует exact ID+URL;
  исчезнувший ID не остаётся в новом vector, изменённый URL не наследует proof.
  confirmCurrent требует свежую revision, точный response URL, literal GET и
  допустимый cabinet route. Актуальный mismatch/POST отзывает current proof;
  stale callback возвращает false до записи и не портит более новый snapshot.
- Каждый актуальный snapshot request сначала потребляет revision и снимает
  fresh, включая отказ валидации. Поздний запрос иной revision ничего не
  перезаписывает. Duplicate/negative ID, неверные index/source, >128 entries,
  empty/>8192-byte URL и запрещённые символы не оставляют старый доступный выбор.
- target проверяет ВСЕ entries, не только выбранный URL или направление:
  unknown/POST current/forward/другого URL запрещает оба BF. Свежий GET с другим
  ID не реабилитирует old POST; переименование unsafe ID не создаёт proof.
- Положительные all-GET cases действительно разрешают Back и Forward по
  browser-owned order. Выбирается ближайший отличный точный URL. Meeting Back
  пропускает settings/inbox; отдельные review/share/meeting deletion-report
  controls проверяют тот же фильтр. Обычная страница сохраняет обычную историю.
- invalidate временно закрывает выбор, сохраняя доказательства неизменных
  entries; forgetEntry отзывает заменённую запись; clear снимает все proofs и
  меняет revision. Тесты eviction и session clear теперь предварительно реально
  подтверждают соответствующий GET, поэтому отказ не проходит вхолостую.
- Session boundary в этой чистой модели представлен clear, а document replacement
  — forgetEntry. Обязательный вызов на logout/expiry/account/workspace/recreate,
  настоящая корреляция final response/cabinet latch со свежим entry, а также
  pending/loading/reset fences принадлежат будущему host adapter. Передача URL
  и строки GET из произвольного callback сама по себе НЕ удовлетворяет контракту.

Оценка формы реализации: один ограниченный vector реальных browser entries,
один bool proof на entry, revision/fresh и небольшой конкретный API; своего URL
stack, framework, зависимости или persistence нет. Линейный выбор и квадратичная
проверка duplicate/proof lookup при лимите 128 не требуют дополнительного индекса
или архитектуры. Оснований требовать такую сложность не найдено.

### Тестовые сведения — не смешивать с независимой SOURCE проверкой

Main сообщил: production clang++17 `/Wall /Wextra /Werror` GREEN exit0;
ASan/UBSan exit0; временный mutant без all-GET guard runtime RED exit134 на
assert line53 (unknown unrelated forward entry). Чтение фактического теста
подтверждает значимость этого oracle: до добавления unknown уже есть полезный
GET Back/Forward, а строка53 требует quarantine обоих направлений. Reviewer
эти процессы/журналы не запускал и независимо их runtime receipts не квалифицировал.
Ранний missing-type RED был только compilation RED, не доказательством старой
host POST ошибки. Native Windows compiler/runtime и исходный history-post RED
не переобъявлены GREEN этими portable результатами.

Изменён только этот собственный report. Code/norms/tasks/checklist markers/Git/
GitHub/VM не менялись; своих тестов или сборок не было. T103/#7280, T088/#7231
и full F200 остаются открытыми. Следующий native срез требует отдельного SOURCE
review фактического adapter, затем относящихся к нему bounded runtime evidence.
