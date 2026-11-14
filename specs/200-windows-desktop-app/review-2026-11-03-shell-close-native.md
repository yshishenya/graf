# Независимое ревью F200/T108: native Close / hide / reopen / no-tray

Дата: 2026-11-03.
Рабочая копия: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`.
База по контексту исполнителя: HEAD `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`;
Git в этом проходе не вызывался. Ревью привязано к текущим SHA-256 ниже.

**Финальное ограниченное ревью: PASS, C0/H0 по четырём текущим исходным файлам,
связанным документам и точным native evidence среза T108. Последовательность
GREEN → RED → restore → GREEN stage shell-close-pin-juyt4_9v принята.
Прежний H1 аварийного завершения закрыт только в этом проверенном сценарии:
с локальной Window-ссылкой оба GREEN завершаются 73, без неё RED повторяет
0xc0000005 и остаётся native_pass=false. Ожиданий внутри этого ревью нет.
Первоначальный stage shell-close-eptwa43d сохраняется как FAIL.**

Это ограниченная регрессия существующего T108, а не изменение требований
или приёмка всего T108/T109. Полоса — независимое source review активного
high-risk-product среза. Применён подход code-reviewer; пользовательские
ограничения исключают Git, новые запуски и изменения реализации.

## Требования и границы

T108 в tasks.md:485 требует отделить крестик от Quit, скрывать главное окно
при доступном фоновом управлении, сохранять окно при его недоступности,
возвращать ту же сессию и использовать единственный bounded exit drain.
Связь: FR-002/004/015, SC-002/004; UX CHK006/021/022, security CHK008 в части
drain до выхода. Прежний requirements gate сохраняется; общий маркер 477/0
получен из контекста исполнителя, не пересчитан и не переодобрен этим ревью.
Живой статус issues #7342/#7343 не перепроверялся; задачи не закрываются.

Резервация starting без запуска устройств допустима для этой проверки
политики окна. Она не доказывает продолжение реального аудиозахвата,
полную матрицу idle/starting/recording/paused/finalizing, доступность Stop
при всех отказах SC-004, установленный MSIX или release acceptance.

Намеренно используется настоящий partial-startup/error root. Стандартный catch
и showStartupError сохраняются. Проверка не заявляет наличие штатного fallback
banner в error root, восстановление полного кабинета или нормальную готовность
приложения. Нажатие Stop отдельно, tray callback/menu и внешняя UIA-приёмка
также не входят в утверждения. SDK Invoke используется только для реальной
кнопки «Закрыть GRAF» в error root.

## Исходный неудачный снимок: проверенные исходники и изоляция

| Файл | SHA-256 |
| --- | --- |
| prepare-appmain-problem-ui.mjs | `b192b8ffce4d0626026a1ed75275f5abbd86e6d2acf1b139c4617523f6eb2bc2` |
| AppMainProblemUiFixture.h | `d4bd42ec58be9857fca4b264be58ddb795a00e3873b782258d1999eb2ebae904` |
| AppMainShellCloseUiLaunch.inc | `f27231449d0dcf4d048ce7ebe9827d45ab2d29638a5ded1dc8c1f3898a12ac45` |
| Production AppMain.cpp | `a85f5024813dbe4fdabbf879485bf12b4343b65b4a1709af1dbe8fdb012436c0` |

Генератор требует пустой отдельный realpath вне checkout, копирует только
обычные Windows source files, проверяет ожидаемый production SHA-256 и
единственность каждой замены. Для shell-close сохраняется основной OnLaunched,
а объявленные подстановки ограничены удалением attribution/activation preamble,
вставкой observer, synthetic capture/AEC, throw вместо startStorageValidation,
тестовым title, in-memory automaticPolicy initializer и тестовым entrypoint.
Forced include относится только к AppMain.cpp; macro-подмена production запрещена.
В replacements перечислены эти области, unchanged_methods расширен до 17.

NativeCapture получает новый GUID temp root и ProblemUiAec ready=false. Root
не создаётся; явных startStorageValidation, setAuth, readiness, web attach,
device start или writer нет. Конструктор NativeCapture создаёт модель pipeline
и callbacks, без probes/IO; queue constructor только сохраняет пути.
ProblemUiState, его seeding и прежние дисковые сценарии из общего header
здесь не создаются и не вызываются. problemStore заменяется пустым store до
использования; automaticPolicy получает пустой preference store до OnLaunched.
Тестовый entrypoint исключает production activation/single-instance redirect.

Production catch оставляет shellReady=false, поэтому обычный stateTimer
не выполняет refreshNativeState до exitRequested. openMainWindow на этой
ветви не подключает web/recovery Activated handler: он установлен ниже
раннего return. HWND берётся в phase 0 через nativeWindowHandle(window_)
после загрузки кнопки; поиска по общему заголовку GRAF нет.

Обратное удаление только новых CaptureSessionTestPeer и controller accessor
из header в памяти воспроизвело прежний SHA-256
`f4a30df52345581877f4dd5c533028f30e704c554dc9798bc9ea9e5e9e9d3b67`.
Таким образом прочая часть общего fixture побайтово прежняя.

prepareRecording(nullptr, {}) действительно выполняет beginReadinessCheck,
markReady, beginStart, устанавливает awaitingPreparation и публикует starting,
не вызывая launchPreparedRecording/startWorkers. deviceFreeReservation требует
отсутствия обоих workers, joinable dispatcher и приёма batches. Непустой session
ID, указатель controller, HWND и starting проверяются повторно. Отдельная
WindowsDesktopSession получает activeSessionExists, подтверждая исключительный
lease. Это тестовая резервация, а не обход продуктового допуска аудиозаписи.

## Сохранность производственных методов

Подстановки shell-close OnLaunched независимо воспроизведены только в памяти,
без запуска генератора, Git и записи производных исходников. Блок
Closing/Closed/timer/early return совпал побайтово с production; SHA-256:
`5fd01b9e44a0902fd823fe040e83fc119187faaf97f8f228a8472f32cceec5ee`.
Все 17 секций, заданных генератором, сопоставлены с production и совпали:

| Секция | SHA-256 |
| --- | --- |
| configureCabinet | `91de20cba579043b0bfc25c2f56cce55b1478dda186471983609923aee1c5d6c` |
| answerNativeSettings | `22f63449b3c03b0038a7a0c4d433013a4951d320f2a6a551cc4528110e24bd4d` |
| bindNotificationContext | `9148a5c3705daa2b10ef1164fbee7fd323d7042acace38a6d18120b7db63cd9f` |
| interactionPermit | `6b26f7070b5b3af22995af13b8ae29fade4ff82aeacdcb150bac06ec84955fd3` |
| problemContextCurrent | `4304bf2bd45d1cb217bf5434255f8deaabba7f5a43ab0074629ffd4c954a797c` |
| problemActionCurrent | `357692fdccc4ed32771cb512187c5cdc2b8902d15af8cca1c15f29f4d5e9229c` |
| openProblemRecording | `84e11280c672715243ae4e51bdadb730dde8cdfea08849e575d43f99377450f3` |
| confirmLocalAction | `845d0a7536ea08b115efdabf330887e0ced7a943f9332c71568bec5a51afeee8` |
| pollLocalRecordingRemoval | `21f7022ac1ac2b1c3854afd704cbc629e1219c0f432de8046d93eddb9204d6a6` |
| reconcileRecordingProblems | `8759f4bfbfec252915eb8374d11f2715615198d85eb03c38ac79f9287a3c0ab0` |
| refreshSelectedRecording | `58a93665e29fa6d39408bc990d0c32eb54167e6ccc37b2cbf8431617350c790e` |
| exitPolicy | `620dcba29c7959becf0453109561caa8f9547bd78f808af5c48217e55ff45a46` |
| refreshNativeState | `c78caed6a926737cb2c5f246dde132115eab1e830301d7284ba008ccc19612c9` |
| showStartupError | `57fea855fee9a8dce46810b4872c82ef05348fa124fd41d9a34ed45993b0ad90` |
| openMainWindow | `8731fe1d1d341e6065ab5731e9a5b151930ef549c8aa59be538168a068caf108` |
| refreshTrayAvailability | `bd243bde4d892ab62cd1b910b03aa09487a7a4110661974aafa6c7c78e368e24` |
| recordingIndicator | `9034c95a04716453aabe3f6128732950797416d4f32eb0809410108340278c74` |

Весь OnLaunched имеет объявленные изменения, поэтому побайтовая сохранность
заявляется для названных секций и close/timer block, не для целого метода.
Изменения production trust/handlers этим патчем не вносятся.

## Последовательность и защита результата

Девять фаз проверяют idle hide/reopen/no-tray; затем настоящую starting
резервацию, hide и повторный WM_CLOSE; reopen; сохранение главного окна при
скрытом индикаторе; сохранение главного окна после удаления собственного
трея с доступным видимым индикатором Stop; реальный Quit через SDK Invoke.
WM_CLOSE отправляется настоящему HWND через PostMessageW, а не вызовом
скопированного решения. Счётчик closes считает успешные отправки сообщений;
наблюдаемые эффекты проверяются следующими фазами. Это не счётчик входов
в native Closing и не отдельная приёмка низкоуровневого сообщения Windows.

WindowsTray действительно создаёт собственное окно и регистрирует icon;
available вызывает штатное обновление и возвращает registered. Удаление
затрагивает только tray_ тестового процесса. Tray state/menu здесь не
публикуются и не принимаются. recordingIndicatorAvailable проверяет AppWindow
и HWND visibility, отсутствие минимизации, видимость и enabled кнопки Stop.
Скрытый icon в области уведомлений не считается заменой отдельного индикатора.

После каждого изменения видимости при starting повторно проверяются session,
controller, отсутствие устройств и удержание lease. Успешный путь не вызывает
stopCapture или refreshNativeState отдельно. На phase 8 перед настоящим Invoke
phase увеличивается до 9: синхронный Closed не даёт ложного FAIL из-за счётчика.

Closed даёт 73 только при !failed, phase=9, closes=6, reopens=2, quit=1,
exitWorkDrained, освобождённом lease и отсутствии synthetic root. Иначе 3.
Преждевременный Closed не удовлетворяет полному набору фаз и счётчиков.
Catch выставляет failed=true до rescue requestExit: rescue не может дать PASS.
После Quit завершение выполняет production exit path. Финализатор модели без
recordingWork возвращает storageUnavailable и освобождает lease через terminal
session state; это нормальная очистка искусственной резервации, не утверждение
об успешном сохранении записи или выполненном storage I/O.

Observer имеет deadline 8 секунд от создания состояния, проверяемый на UI
dispatcher. Если dispatcher зависнет, он сам не является внешним ограничителем.
В прочитанном Run.ps1 stage parent ждёт 20 секунд; при необходимости завершает
дерево точного собственного PID и ждёт ещё 5 секунд. Forced cleanup оставляет
FAIL. В рассматриваемом запуске процесс уже завершился аварийно, поэтому
forced cleanup в квитанции отсутствует. Возникшая ошибка остаётся FAIL даже
при последующем rescue.

## Исторический H1 runtime и первоначальная проверка времени жизни

Stage: `/Users/yshishenya/Documents/graf-f200-public458.po8CtB/shell-close-eptwa43d`.
build-result.json: terminal=true, build_exit=0, source_files=
post_source_files=223. PE:
`b3d0a6fb766fb90de781c9d200e1b09b0e68f8c2b45a2c6a6441183d068c8d1b`.
223 входа source.json независимо совпали с текущим checkout, 223 файла
source/ — с test-source.json. Производный AppMain:
`22212861df8db2db13f03b8ddea90a3053bc8d6164f2a1b8c4455b8869383bed`.

green-ui.err содержит phase=0..7 pass=1, затем terminal=1 phases=9,
closes=6 reopens=2 quit=1 drained=1 lease_released=1 no_files=1 exit=73.
Но green-result.json фиксирует app_exit=-1073741819 (0xc0000005),
native_pass=false, failure=UNEXPECTED_NATIVE_RESULT, app_stopped=true.
Результат — FAIL. На этом первоначальном этапе само падение было подтверждено,
а точный виновный участок ещё не был установлен. Финальный A/B разобран ниже.

Причина, по которой журнал не является signoff: тестовый window_.Closed
подписан во вставке раньше production window_.Closed. Он вычисляет результат
и печатает terminal до выполнения следующего cleanup handler. Возврат
wWinMain с problemUiResult=73 ещё не произошёл. Run.ps1 правильно требует
и точный OS process exit, и журнал; условие не следует ослаблять.

**Конкретный SOURCE concern о lifetime:** AppMain.cpp:598 вызывает
indicatorWindow_.Close() непосредственно через член GrafApp. Вложенный
indicatorWindow_.Closed в AppMain.cpp:2576–2579 присваивает nullptr этому же
indicatorWindow_, затем indicatorText_ и indicatorStop_. При синхронной
доставке Closed это изменяет владельца ещё до возврата исходного Close.
Вызывающая сторона не удерживает отдельную сильную ссылку на закрываемое
Window. Если поле содержит последнюю такую ссылку, объект может потерять
владельца во время обработки закрытия. По доступным исходникам нельзя
доказать, какие дополнительные ссылки удерживает WinUI и в какой инструкции
произошло нарушение доступа: stack/dump не предоставлен.

Уже существующий локальный образец — dismissPlaybackWindow, AppMain.cpp:1350–1355:
он переносит владение в локальный closing, очищает поле/инвалидирует поколение
и вызывает Close через сохранённую ссылку. Минимальный кандидат для индикатора —
удержать локальную сильную Window-ссылку на всё время Close; проверить тот же
вызов в catch ensureRecordingIndicator, AppMain.cpp:2589. Это рекомендация
исполнителю, не правка рецензента и не доказанное устранение аварии. Не нужно
подменять Closed, обходить cleanup или переводить процессный FAIL в PASS.

Другие lifetime-детали: indicatorPanel_ сохраняет ссылку на дерево элементов,
но не является явно удержанной Window-ссылкой. Indicator Closed не очищает
это поле. Само по себе это не доказывает use-after-free или вторую причину
падения и отдельным подтверждённым дефектом не объявляется.

Runner выбрасывает UNEXPECTED_NATIVE_RESULT до installed/post-source проверок.
Поэтому в этой неудачной квитанции нет installed_exe_unchanged и
post_source_files; нельзя приписывать ей успешный postflight. Совпадение
223 host inputs и frozen outputs проверено отдельно чтением файлов. Нового
подтверждения гостевого postflight/неизменности установленного EXE этим
первоначальным ревью не было получено. Installed version=0.1.0.14 не заменяет
такую проверку. Новые успешные квитанции ниже дополняют, а не переписывают
эту неудачную квитанцию.

| Артефакт неудачного запуска | SHA-256 |
| --- | --- |
| source.json | `7177cd8d3f1e21d4c845591cebc26a5d7368eef5fe9110ccee792e71d41e2432` |
| test-source.json | `bf84685050f3aa6adf544d093a08308de64924ca0fe520b80a1bb3cb99750345` |
| appmain-test-bindings.json | `fb96a71fdb804722ccad5708aee024314bbf35c0f3fc6bdf6ceeaee53d4694ea` |
| build-result.json | `c0b81fc8017418759d947dbff15b822ffc11f9ff1395ffe8f7ce489424342c31` |
| green-result.json | `6604ff2f846471cc493849df24f6b33aa9c08b5c6c312e9a199151968a36a602` |
| green-ui.err | `dc5fcf7db3d1770f6219e840e49686a94da6f80daf63af76a45246d19c81d425` |
| Run.ps1 | `49ddc0a65602b665be4a523a14e4a4d5c3d976c61296accb9d3f98ecb2985fb4` |

## Повторное SOURCE review минимального production candidate

Новый stage:
`/Users/yshishenya/Documents/graf-f200-public458.po8CtB/shell-close-pin-juyt4_9v`.
Рассмотрена только дельта реального cleanup главного окна; другие production
области в обзор не добавлялись. Три тестовых файла сохранили приведённые выше
хеши. SHA-256 текущего production AppMain:
`b7a2ab3ec2128636c0b953a1c79e8a29f74f3b408734853b8bb25ec2ed34927e`.
SHA-256 текущего derivative:
`837d7f4986c70b5fa8180344673b2d2caab06d49fe99a633517f1acbe0d610f6`.

В main Closed теперь выполняется
`if (const auto indicator = indicatorWindow_) indicator.Close();`
вместо прямого вызова через indicatorWindow_. Локальная переменная копирует
владеющую Window-ссылку до вызова. Её время жизни продолжается до конца if,
включая весь вызов Close и синхронные вложенные handlers. Обнуление поля в
indicator Closed поэтому уже не освобождает именно эту локальную ссылку.
Не меняются порядок shutdown, обработчики события, polling, drain, Stop,
admission/trust или условие результата теста. Локальное владение не доказывает
корректность всей отложенной обработки WinUI после возврата из Close.

Независимое обратное применение этой строки и двух новых комментариев в памяти
дало точный прежний production SHA-256
`a85f5024813dbe4fdabbf879485bf12b4343b65b4a1709af1dbe8fdb012436c0`.
Сравнение двух frozen derivative подтвердило ровно ту же дельту.
Все 223 текущих входа совпали с новым source.json, все 223 frozen outputs —
с test-source.json. Повторно извлечены 17 секций: production/candidate derivative
побайтово совпали, хеши равны новому bindings. Таблица 17 секций выше остаётся
верной. Главный Closing/Closed/timer block изменён намеренно и отдельно:
production и derivative совпали, новый SHA-256
`4667b1cf0618b080356faec025c2d4dccddc71fb770e40b1a929426c4fa67b8e`.
Прежний хеш блока относится только к исходному неудачному снимку.

Сохранённый debug-trace.log прежнего stage независимо прочитан:
SECOND_CHANCE code=c0000005, два кадра ntdll+1a818c. Это подтверждение
нарушения доступа, не локализация по AppMain/WinUI и не доказательство
освобождения последней ссылки. Сообщение исполнителя об ограничении DbgHelp
под ARM emulation согласуется с отсутствием полезного стека, но причина
ограничения самим рецензентом не воспроизводилась.

**Промежуточный вывод до native A/B: SOURCE допустим, C0/H0 только для этой
минимальной дельты. Закрытие H1 требовало нормального OS process exit;
оно получено и рассмотрено в финальном разделе ниже.**
Прямой Close в catch ensureRecordingIndicator остаётся прежним; он не входит
в успешную ветвь данного A/B и не объявляется исправленным этим candidate.
Не следует расширять дельту на другие окна без свидетельств их участия.

| Артефакт candidate / диагностики | SHA-256 |
| --- | --- |
| candidate source.json | `d96f0d091b65969dafd2416e53044c59697631d03c1566028424f13dbc62e75c` |
| candidate test-source.json | `d1cb5f35ab22ddf50638ca4e7bcd27337b2598677153865f0a8641f5d6655c0f` |
| candidate appmain-test-bindings.json | `87b6e2fe5a295637e5ddffbb9aacf92715f8df580c4193e943e51d34fa5fc0bc` |
| previous debug-trace.log | `f46d40b012a452baed9a807e13e0e92e6135cdc66dee46b0fd896ec67f5d3420` |
| previous debug-trace.err (пустой) | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |

## Финальное повторное ревью: exact GREEN / RED / restore / GREEN

Текущие четыре SHA-256 сверены повторно: production AppMain
`b7a2ab3ec2128636c0b953a1c79e8a29f74f3b408734853b8bb25ec2ed34927e`,
три test-only файла по-прежнему имеют приведённые выше b192b8ff… / d4bd42ec… /
f2723144… . Все 223 source.json входа совпали с рабочей копией; все 223
замороженных GREEN-файла совпали с test-source.json. RED manifest отличается
ровно AppMain.cpp; 222 прочих входа прежние. Отмена только локальной ссылки
и двух комментариев побайтово дала сохранённый исходный derivative
`22212861df8db2db13f03b8ddea90a3053bc8d6164f2a1b8c4455b8869383bed`.
Повторно сопоставлены все 17 секций production/GREEN/RED и хеши bindings;
главный close/timer block GREEN совпал с текущим production и хешем 4667b1cf…
выше. Это привязка к текущей правке, не перенос старого policy PASS.

Build-Red.ps1 сверяет GREEN source и PE, сохраняет pinned GREEN EXE, копирует
только RED AppMain и удаляет только принадлежащий этой сборке AppMain.obj.
Проверка времени объекта запрещает STALE_APPMAIN_COMPILE. В build.log и
red-build.log есть AppMain.cpp и Generating code. Обе build receipts terminal,
build_exit=0, source_files=post_source_files=223, без failure. AppMain.obj
различается, WebView2Host.obj и три runtime DLL pins совпадают.

| Этап | OS process / квитанция | Итог |
| --- | --- | --- |
| GREEN-first | app_exit=73, native_pass=true, app_stopped=true | PASS |
| RED: удалена только локальная Window-ссылка | app_exit=-1073741819 (0xc0000005), native_pass=false, red_rejected=true, app_stopped=true | Регрессия воспроизведена; native FAIL |
| Restore-Green | terminal=true, 223 GREEN inputs, точный GREEN PE, RED object и backup EXE отсутствуют | PASS |
| Финальный GREEN после restore | app_exit=73, native_pass=true, app_stopped=true | PASS |

GREEN PE:
`cef34154c06b165a6b5c78d00a9271c41aedb2b3f7f6cff442b8977823027da8`.
RED PE:
`40106f0ed834d432723e2060fea7bee8b47f6d18c0ba586ac43a312c81e01e04`.
У всех трёх run receipts terminal=true, до/после 223 inputs,
installed_exe_unchanged=true; failure/forced_cleanup отсутствуют.
Все три журнальных файла содержат одинаковые phase 0..7 pass=1 и terminal
phases=9 closes=6 reopens=2 quit=1 drained=lease_released=no_files=1 exit=73.
Идентичность журналов не означает одинаковый исход процесса: решающий факт —
OS exit 73 против 0xc0000005. GREEN-first и повторная GREEN receipts также
побайтово одинаковы по своему детерминированному набору полей.

Текущий Run.ps1 для GREEN требует настоящий exit=73, полный terminal pattern
и отсутствие failure=1. RED квалифицируется только при точном 0xc0000005,
том же полном terminal и native_pass=false. Это целевой отрицательный контроль
cleanup lifetime, не обычный успех приложения. Rescue/тайм-аут/forced kill
не удовлетворяют принятому пути. Процессный gate не ослаблен; код RED здесь
намеренно отличается от предыдущего startup-exit timer-контроля.

Restore-Green.ps1 проверяет RED manifest, допускает только один source diff,
сверяет сохранённый GREEN EXE, возвращает AppMain/EXE и сверяет все 223 входа.
Квитанция: red_object_absent=true, temporary_exe_copy_absent=true,
app_processes=owned_browser_processes=0, installed_version=0.1.0.14,
installed_status=Ok. Отсутствие host green.exe также проверено чтением.
Последующий GREEN повторно подтвердил полное штатное завершение после restore.

Postflight.ps1/receipt: terminal=true, без failure; app/debugger processes=0,
прежний тестовый сертификат отсутствует в CurrentUser Root/CA/My. Скрипт лишь
проверяет этот сертификат и не изменяет trust. Точные TraceExit.exe/obj
хешированы, удалены, отсутствие проверено до записи успешной квитанции.
Установленный пакет 0.1.0.14 / Ok, EXE SHA-256
`6e1626953fc7e409837d65bbdebd642d509e69569ae43545039826a433b72a48`.
Гостевой postflight принят по сохранённой квитанции и прочитанной процедуре;
рецензент не выполнял новой VM-инспекции. installed_acceptance=false.

Совокупность exact A/B/A закрывает обнаруженный H1 для проверенного пути:
удержание ссылки устраняет наблюдавшуюся аварию, удаление только этой ссылки
возвращает её, восстановление возвращает нормальный process exit. Точный
внутренний механизм/инструкция WinUI по-прежнему не выведены из ntdll-only
стека; это ограничение диагностики не подменяется утверждением о полном
разборе WinUI. В catch ensureRecordingIndicator и других окнах изменения
не заявляются. Новых подтверждённых C/H или иных must-fix в текущем срезе нет.

## Документы, дополнительные проверки и итоговые хеши

Прочитан validation-2026-11-03-shell-close.md, SHA-256
`6d7030c807045f17da15152fe2de07c10c086fe3e96b600228d0fafa620687fa`.
Все 18 приведённых хешей (четыре source + 14 артефактов) совпали. Описание
дефекта, минимальной правки, отрицательного контроля, restore/повтора и
ограничений согласовано с exact receipts. F200.yaml прочитан только в части
новой записи release_notes_windows_indicator_exit_20261103; она отражает
проверенный результат и явно оставляет реальную запись/installed acceptance
открытыми. SHA-256 фрагмента:
`6fef83ae90ac6e760bf91cd48ddc8b61c0af0c8f6f002acd66c4c649f3cbe3af`.
Другие исторические записи фрагмента не переодобрялись.

portable-close.log подтверждает build RecordingIndicatorTests и CTest 1/1
PASS, exit 0. governance.log подтверждает временную установку точного
Spec Kit 1.0.7 ref fe1d00e3ccaf495880aaf90fb0e17679e82f065b, doctor --frozen
bootstrap 0.11.0 и governance script exit 0. Это прочитанные журналы
исполнителя, не новый запуск рецензента. YAML/node syntax и diff-check приняты
как заявленные исполнителем дополнительные проверки; отдельно рецензентом
не повторялись. Общие 477/0 markers не пересчитывались.

| Финальный артефакт shell-close-pin-juyt4_9v | SHA-256 |
| --- | --- |
| build-result.json | `c626233191f2316f230b1c3b9b2d427fd5dfcbc334fc37de1948ca59001266d9` |
| green-first-result.json | `2d4954a03d47c2df4e18237b76151ffa13e29600e8aedd7cd4ea75933fcc5feb` |
| red-control.json | `9cfd60409aefebc05e5aa9903df09546debc13fd68d118536ebcd714949f133e` |
| red-test-source.json | `bf84685050f3aa6adf544d093a08308de64924ca0fe520b80a1bb3cb99750345` |
| red-build-result.json | `cc922859dd8f76cbde3022da032acdd8684c373fa2ae180ab7c4e7280e8edeff` |
| red-result.json | `715ab88c1f8fbcd677000ed4631d06014ead8bf5c1d5920c44e78127624a7651` |
| restore-green.json | `bdf9a5c99c32e601cc41185b757c1d869a20a36b986a89577e458df665fac4c3` |
| green-result.json | `2d4954a03d47c2df4e18237b76151ffa13e29600e8aedd7cd4ea75933fcc5feb` |
| green-first-ui.err / red-ui.err / green-ui.err | `dc5fcf7db3d1770f6219e840e49686a94da6f80daf63af76a45246d19c81d425` |
| postflight.json | `4d892bf9450bf0b03a8f796ec79ec69cb05c79c5b6ecc1a7c872d3acc7f3a064` |
| Run.ps1 | `d355f4ad5e7601b2ef9f819555491cb5d422fe3cd97cff81d9d3b8bcefca0960` |
| Build-Red.ps1 | `b5f68529f796806459b463210879fd5a55855778f0e6e814d31c43ebcbfdfd20` |
| Restore-Green.ps1 | `ab8b1d039df640ba0138674adc58e22035b03bea9fad5e33499214e7d0048927` |
| Postflight.ps1 | `05dcee41fdc860d0e65fd1fef8e8e91cfced731cc04e7e34b8ce5bd296a85e9a` |
| governance.log | `7111217999a9a47bdc8a16d0bc72045c5fe301d30f94e6427a2aa996c6255fb4` |
| portable-close.log | `f0dd6c3451419fbccd5e5f8a93d41c155bd8f5f830898e4178706ed650103680` |

## Завершение и границы приёмки

Прочитаны четыре текущих файла, связанные производственные constructor/reservation/lease,
Closing/Closed/open/reopen/indicator/tray/exit пути и только относящиеся к ним
требования. Выполнены чтение, хеширование и сравнения в памяти, затем изучены
точные сохранённые build/run receipts и журнал неудачного stage. Рецензент
не выполнял сборку, генерацию на диске, native test или runner cleanup.
Первоначальный FAIL сохранён как историческое свидетельство. Текущие четыре
source files, exact GREEN/RED/restore/GREEN receipts и связанные документы
приняты в описанных границах: C0/H0, прежний H1 для этого пути закрыт.
Не принимаются весь T108/T109, реальный звук, recording/paused/finalizing,
нажатие Stop, tray menu/callback, нормальный fallback banner, installed MSIX,
hardware или готовность F200 к выпуску. Tasks/issues/checklist state сохраняются.
Финальная сверка выполнена до планируемой исполнителем очистки принадлежащих
этому stage host source/red-source snapshots. Рецензент их не удалял;
manifests/logs/receipts должны сохраниться. Активная Windows base и установленный
пакет не относятся к этой очистке. Новых запусков для этого заключения нет.
Только этот новый отчёт записан рецензентом; код, задачи,
checklists, прежние отчёты, Git и VM не изменялись.
