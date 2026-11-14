# Независимое ревью F200/T108: первый Quit при удержанном startup worker

Дата: 2026-11-03. Ветка `codex/200-windows-followup`.
HEAD: `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`.
Текущий stage: `/Users/yshishenya/Documents/graf-f200-public458.po8CtB/startup-exit-final-2ywiz46z`.
Исторический stage: `/Users/yshishenya/Documents/graf-f200-public458.po8CtB/startup-exit-sahz6bkv`.

**Финальное ограниченное ревью: PASS, C0/H0 по трём текущим тестовым файлам,
их native evidence и соответствию финальному приложению validation.
GREEN, RED attempt 2 и restore final-2ywiz46z приняты в указанных границах.
Первая попытка RED build отклонена: STALE_APPMAIN_COMPILE, без запуска теста.
Ожидающих проверок внутри этого среза не осталось.**

Границы текущего заключения: prepare-appmain-problem-ui.mjs,
AppMainProblemUiFixture.h и AppMainStartupExitUiLaunch.inc, требования T108
и native evidence названных stage. Расширение обзора остановлено;
исторический storage, другие продуктовые срезы и новая матрица испытаний
не входят в вывод. Рецензент не выполняет новые запуски.

Конкретных C/H-блокеров трёх текущих исходников не обнаружено. Проверены
изоляция, сохранность production exit/polling и запрет PASS после rescue.
Свидетельства первого stage сохранены как исторические; они не заменяют
проверку исполнения после изменения release guard.

Это регрессия существующего T108 после уже принятого source-исправления,
а не новая продуктовая возможность или перепланирование F200. Полоса —
ограниченное независимое ревью активного `high-risk-product` среза.
Рецензент записывает только этот отчёт; код, задачи, контрольные списки,
Git и Windows/VM не изменяет. Старый неисполненный prototype u724 не используется.

## Допустимость и сохранённый requirements/checklist gate

Проверка соответствует T108 в tasks.md:485, FR-002/004/015, SC-002/004,
требованиям безопасного degraded startup и независимого нативного выхода.
Связанные критерии: requirements CHK016, security CHK008 о drain перед выходом,
ux CHK006/021/022 о повторном завершении, Close/Quit и независимости от WebView.
Прочитаны конституция, product gates, относящиеся требования/plan/quickstart
и контекст уже принятого исправления в validation. Перепланирование,
новые задачи и большой analyze для этой тестовой регрессии не нужны.

| Существующий список качества требований | Checked | Unchecked |
| --- | ---: | ---: |
| requirements.md | 22 | 0 |
| security.md | 27 | 0 |
| ux.md | 25 | 0 |
| Всего | 74 | 0 |

Таблица показывает только три ранее проверенных списка, а не общий gate.
Общий маркер **477 checked / 0 unchecked** получен из контекста исполнителя
предыдущего ревью, а не из самостоятельного подсчёта рецензента и не как
утверждение пользователя о качестве требований. Позднее исполнитель сообщил
механический подсчёт 477/0 в 31 файле; рецензент его не повторяет и не
переодобряет смысл всех этих пунктов.
Все отметки сохранены, не переотмечались. Они не означают приёмку нового
кода, выполнения теста, установленного приложения или всего T108.
Предварительно названные пробелы изоляции сняты уточнённым устройством
fixture и проверенным исходником: in-memory autoPolicy до OnLaunched,
отдельный entrypoint без product activation/single-instance redirect,
несуществующий synthetic root, пустой auth и отсутствие readiness/web attach.

## Source review и изоляция

Проверены prepare-appmain-problem-ui.mjs, AppMainProblemUiFixture.h с
holdStartup и новый AppMainStartupExitUiLaunch.inc. Production AppMain
сохранил SHA-256 `a85f5024813dbe4fdabbf879485bf12b4343b65b4a1709af1dbe8fdb012436c0`.

- Генератор допускает `startup-exit` отдельно от прежних problem/settings.
  Он по-прежнему требует пустой отдельный realpath вне checkout; точные
  замены требуют единственного вхождения. Удаление attribution/pending
  activation, observer, synthetic capture/worker/fault и отдельный title
  ограничены производным OnLaunched и объявлены в replacements.
- Обычный wWinMain заменён тестовым входом без регистрации/перенаправления
  установленного GRAF. Сохраняется прежняя подстановка пустого preference
  store в initializer AutomaticRecordingPolicy: его обычный конструктор
  действительно вызывает store.read до OnLaunched. Присваивание пустого
  problemStore выполняется до использования; native() создаёт только callbacks.
- Root — временный путь с новым session GUID; он не создаётся. NativeCapture
  получает именно этот путь и dummy AEC с ready=false. Проверенный constructor
  создаёт pipeline, но не запускает устройства/metadata probes; constructor
  очереди только сохраняет пути. Нет setAuthSessionToken, refreshReadiness,
  старта capture, web attach, production storage validation или сети.
  Точный worker заменяет startStorageValidation, затем exception возникает
  до reminders. shellReady остаётся false: обычная refresh/readiness/activation
  ветвь не вызывается; после Quit исполняется существующий exit branch.
- AppMainProblemUiFixture.h:22–45 создаёт настоящий event и `_beginthreadex`
  handle, установленные в существующие поля NativeCapture через friend peer.
  StorageStartupWork начинается с ready=false/terminal=false; поток ждёт
  event не более 10 секунд без I/O. mutex не удерживается во время ожидания,
  поэтому настоящий requestShutdown не блокируется на тестовом worker.
  terminal устанавливается под штатным mutex перед завершением потока.
- Настоящие Closing/Closed, создание/положение stateTimer, условие
  shellReady || exitRequested_, ранний !shellReady return и методы выхода
  сохранены. Полный OnLaunched закономерно имеет другой хеш из-за явно
  перечисленных подстановок; утверждение побайтовой сохранности относится
  к проверяемым участкам и 14 секциям, а не ко всему изменённому методу.

node --check прошёл. Сам генератор дополнительно исполнен с файловыми
операциями записи, перенаправленными исключительно в память: 222 входа,
14 bindings, отличаются только производные AppMain.cpp и GrafWindowsApp.vcxproj.
Полученный AppMain SHA-256:
`09e3bec9569c66711281b45e11e30d06edd21dbfca086ed9f4621d925b211450`.
Он совпал с первоначальным stage sahz6bkv; все 222 входа source.json совпали с рабочей копией,
все 222 файла source/ — с test-source.json. Каждая из 14 секций независимо
сопоставлена побайтово с production и хешами bindings; отдельно целиком
сверена область Closing/Closed/timer/раннего return. Forced include остаётся
только у compile item AppMain.cpp. installed_acceptance=false.

## Почему rescue не может дать PASS

AppMainStartupExitUiLaunch.inc:21–38 ищет реальную загруженную кнопку
«Закрыть GRAF», вызывает существующий WinUI Invoke helper и после первого
действия требует exitRequested && !exitWorkDrained() && !shuttingDown.
До release повторно требуется недренированное состояние. После минимум
500 мс event освобождается; watchdog не вызывает refreshNativeState и не
закрывает окно на успешной ветви. Закрытие должен выполнить production timer.

При любом catch сначала выставляется необратимый failed=true и увеличивается
invocations, только потом выполняется rescue requestExit. Closed принимает
73 лишь при !failed, invocations==1, heldTicks>=2, обычном release,
worker.released=true, exitWorkDrained() и отсутствии synthetic root.
Тайм-аут 10-секундного ожидания даёт released=false и не может пройти PASS.
Штатный shutdownWorkDrained проверяет и terminal, и сигнальное состояние
настоящего native thread handle: одного выставленного флага недостаточно.

Предел rescue — 3000 мс от firstQuit, не от release; после штатного release
остаётся примерно 2,5 секунды на закрытие. Это может дать FAIL на медленном
стенде, но не ложный PASS. Deadline и rescue работают тем же UI dispatcher;
независимый внешний Run.ps1 ограничивает процесс 20 секундами и reaps его
после принудительного завершения. Forced cleanup не принимается за успех.

Run.ps1 дополнительно требует exit=73, строгий terminal с invocations=1,
worker_released/drained/no_files=1 и отсутствие failure=1 для GREEN.
RED имеет отдельный red_rejected, ожидает exit=3 и rescue; это успешное
обнаружение регрессии, а не native_pass. Оценивать надо целую квитанцию,
включая отсутствие failure/forced_cleanup и app_stopped, не один bool.
Исключение внутри observer журналируется обобщённо: точная стадия RED
восстанавливается по source control и последовательности журнала, а не
по одному полю red_rejected.

## Исторические build/GREEN свидетельства: sahz6bkv

Прочитаны Build.ps1, build.log/result, Run.ps1 и green-result/ui.err.
Build задаёт Release/x64; terminal=true, build_exit=0, до/после 222 входа,
нет failure. PE:
`fb9763242b8446bcf67f4c2b8384b7db8ec8bf89eb04a1b0b153b149195da9ba`.
Сохранённый stage green.exe независимо хеширован рецензентом и совпал.

GREEN: terminal=true, app_exit=73, native_pass=true, app_stopped=true,
source_files=post_source_files=222, installed_exe_unchanged=true;
failure/forced_cleanup отсутствуют. Настоящий журнал:
`first_quit=1 held=1`, затем terminal invocations=1, held_ticks=4,
worker_released=drained=no_files=1, exit=73. Установленная версия 0.1.0.14.
Принято как сохранённое Windows SDK/WinUI свидетельство этого derivative;
рецензент не исполнял процесс на VM.

certificate_changed=false и audio_started=false в runner — декларации
среза; отсутствие таких действий обосновано также прочитанным достижимым
путём. Новая инспекция системного trust/mic не выполнялась и не требуется.
Нет чтения аккаунта, пользовательских записей, нового доверия или обновления.

## Исторические RED/restore: sahz6bkv

red-control.json, red-source/AppMain и red-test-source.json проверены.
Меняется ровно один файл относительно GREEN. В памяти независимо
воспроизведено единственное перемещение того же блока production timer
ниже !shellReady/Activate/return; результат побайтово совпал с red-source.
Все 14 остальных секций сохранены. RED AppMain:
`625da2d7fa5cce3d07870cf6c4a920f975b5044934dd13b8fc9cacc187555641`.
Build-Red.ps1 проверяет GREEN перед заменой, сохраняет pinned green.exe,
проверяет RED inputs до/после сборки и компилирует AppMain заново.

Во время ревью завершились RED и восстановление; прочитаны их terminal
квитанции и журналы. red-build-result.json: build_exit=0, source_files=
post_source_files=222, failure отсутствует. RED PE:
`380f4beb0680e67e52bda240a983ab541766d29f1824e61a984579d21937d61a`.
red-result.json: app_exit=3, native_pass=false, red_rejected=true,
app_stopped=true, до/после 222 source, installed_exe_unchanged=true;
failure/forced_cleanup отсутствуют. Журнал содержит first_quit=1 held=1,
затем failure=1 rescue_quit=1 и terminal invocations=2, held_ticks=5,
worker_released=drained=no_files=1, exit=3. Нормальный GREEN завершился
одним Invoke; перестановка только production timer потребовала rescue и
осталась FAIL. Так доказана различающая регрессия, а не успех за rescue.

Restore-Green.ps1 перед изменениями сверяет весь RED manifest и допускает
ровно один source diff — AppMain.cpp. Он проверяет сохранённый GREEN PE,
возвращает этот исходник и EXE, затем сверяет все GREEN inputs и PE.
Удаляется точный гостевой RED AppMain.obj, чтобы последующая сборка не
использовала его с восстановленным GREEN source, и временный stage green.exe.
Проверенный restore-green.json: terminal=true, source_files=222,
exe_sha256 совпадает с GREEN `fb976324…195da9ba`, red_object_absent=true,
temporary_exe_copy_absent=true, app_processes=owned_browser_processes=0,
installed_version=0.1.0.14, installed_status=Ok; failure отсутствует.
Отсутствие временного stage green.exe дополнительно проверено локально.
Финальный restore сообщает версию/статус установленного пакета; побайтовая
неизменность установленного EXE отдельно подтверждена обоими run receipts.
Рецензент не запускал тесты и не восстанавливал чужой гостевой checkout.

Этот опыт принимает только startup-error/первый Quit/worker drain/Closed.
Не принимаются весь T108, закрытие во время реальной записи, hide/reopen из
трея, вся матрица repeated Close/no-tray, installed MSIX, hardware или release.
T108/T109 и отметки качества остаются без изменений. Старые HTTPS-квитанции
этим независимым срезом не пересчитываются.

## Финальное повторное SOURCE review: поправка release guard

В прежней fixture найден P2: если первый тик после Invoke задерживался более
500 мс, worker освобождался при heldTicks=1. Исправленный продукт мог штатно
закрыться, но тест требовал минимум два тика и ошибочно давал FAIL.
Этот путь рецензент первоначально пропустил; замечание учтено и проверено.

Единственная текущая дельта относительно замороженного sahz6bkv:
release требует одновременно `elapsed >= 500` и `heldTicks >= 2`.
Генератор и peer побайтово прежние. Новый guard гарантирует нужные два
наблюдения до release, не вызывает production polling и не закрывает окно.
При прежнем расположении production timer его по-прежнему нет на error
ветви: освобождение worker не создаёт нового пути Close. Остаётся только
rescue после deadline, который заранее ставит failed=true и увеличивает
invocations. Поэтому guard не скрывает исходный RED timer defect.
Сроки не расширены: worker 10 секунд, внешний процесс 20 секунд;
rescue по-прежнему через 3 секунды от первого Quit.

В финальном stage независимо сверены все 222 source.json входа с текущими
файлами и 222 файла source/ с test-source.json. Финальный GREEN AppMain
побайтово равен старому derivative с одной указанной заменой:
`8b47bf425c1d338d34e4669e26d0216398e10231b14e50edbc83642f2f092fa1`.
Финальный RED повторно получен в памяти только перемещением того же timer
после раннего return; совпал с red-source и отличается ровно одним файлом:
`dbde3d75d45db79edced2283675cae73a60a3121a50184f772ebfcb5e37ffe6e`.

После текущей поправки повторно извлечены и сопоставлены все 14 секций
текущего production AppMain, финального GREEN и финального RED. Каждая
побайтово совпала и дала именно хеш из нового appmain-test-bindings.json:

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

Отдельно побайтово сохранён GREEN блок Closing/Closed/timer/early return,
SHA-256 `5fd01b9e44a0902fd823fe040e83fc119187faaf97f8f228a8472f32cceec5ee`.
Это текущая проверка после patch, а не перенос прежнего native policy PASS.
Тесты, сборки и VM рецензентом повторно не запускались.

Ограниченный ponytail-review применён по доступному SKILL.md версии 5.3.3
(путь каталога 4.9.0 из перечня навыков устарел). Нагрузка — один изолированный
тестовый процесс и один управляемый worker. Нет новых зависимостей,
произвольного ввода каталогов/команд, нового executor финализации или unsafe
PASS; используются существующие peer, Invoke helper и production polling.
Дополнительного переусложнения, требующего удаления, не обнаружено.
P2 release guard исправлен; новых must-fix/should-fix в трёх файлах нет.

## Текущие build/native свидетельства: final-2ywiz46z

Новый GREEN независимо прочитан: build_exit=0, source_files=
post_source_files=222, PE
`5e1561ff9a9e1d8b2aa15d2e99af6f9f7f5dc5278594783486adbb0453327f28`.
green-result: terminal=true, app_exit=73, native_pass=true,
installed_exe_unchanged=true, app_stopped=true, до/после 222 source,
failure/forced_cleanup отсутствуют. Журнал: first_quit=held=1, terminal
invocations=1, held_ticks=5, worker_released=drained=no_files=1, exit=73.

Первая RED build квитанция с build_exit=0 и тем же GREEN PE отклонена:
failure=STALE_APPMAIN_COMPILE. Исполнитель подтвердил, что заранее созданный
RED source сохранил старое mtime при копировании, поэтому MSBuild не
скомпилировал AppMain повторно; native RED этой попытки не запускался.
Сбой не является ни успешным RED, ни продуктовым изменением. Исполнитель
сохранил отдельные immutable red-stale-build-result/log/err. Эта попытка
остаётся отклонённой независимо от последующего успешного повтора.

Build-Red-Retry.ps1 перед повтором сверяет RED manifest и сохранённый GREEN
PE pin, удаляет только точный собственный AppMain.obj. В red-build.log есть
новая компиляция AppMain.cpp и последующая генерация кода. Прочитанная
red-build-result.json: terminal=true, attempt=2, build_exit=0, 222 входа
до/после, без failure. PE:
`9825523509ee9b38823736a72ffdf3b2687a5d79233d411967ca85b1c2aef0e0`.
Новый AppMain.obj:
`d7cf211c983946fc161284a4df0bb02d228c27e6e8cd5f7cdc2ed2e9bafc0844`;
он отличается от GREEN, тогда как WebView2Host.obj и runtime DLL pins совпали.

Финальный red-result.json: terminal=true, app_exit=3, native_pass=false,
red_rejected=true, app_stopped=true, installed_exe_unchanged=true,
source_files=post_source_files=222; failure/forced_cleanup отсутствуют.
red-ui.err: first_quit=1 held=1, затем failure=1 rescue_quit=1;
terminal invocations=2, held_ticks=4, worker_released=drained=no_files=1,
exit=3. Это ожидаемое отклонение прежнего положения timer. Изменённый guard
не скрыл регрессию, а rescue не превратил её в native PASS.

Restore-Green.ps1 проверен для этого stage: он допускает только один diff
AppMain.cpp между GREEN/RED, сверяет сохранённый GREEN EXE и после возврата
сверяет все GREEN inputs. restore-green.json: terminal=true, source_files=222,
exe_sha256=`5e1561ff9a9e1d8b2aa15d2e99af6f9f7f5dc5278594783486adbb0453327f28`,
red_object_absent=true, temporary_exe_copy_absent=true,
app_processes=owned_browser_processes=0, installed_version=0.1.0.14,
installed_status=Ok; failure отсутствует. Отсутствие временного host green.exe
подтверждено чтением файловой системы. Остальные гостевые результаты приняты
по точным сохранённым квитанциям и проверенной процедуре, без новой VM-инспекции.
Неизменность установленного EXE подтверждают оба run receipts; это не приёмка
установленного приложения (installed_acceptance=false).

При финальной сверке повторно совпали 222 текущих входа с source.json и 222
замороженных GREEN-файла с test-source.json; три текущих тестовых SHA-256
сохранились. Production AppMain по-прежнему
`a85f5024813dbe4fdabbf879485bf12b4343b65b4a1709af1dbe8fdb012436c0`.
Уже выполненная после однострочного patch побайтовая сверка 14 секций выше
относится к этим же неизменным production/GREEN/RED исходникам и bindings.
Старый native policy PASS повторно не использован вместо этой проверки.

Финальное приложение validation-2026-11-03-startup-exit.md прочитано;
все 14 перечисленных в нём SHA-256 совпали с файлами final-2ywiz46z.
Текущий SHA-256 документа:
`20b84b7fae3ca9d86cdd65d800ac1ae0c47a31cb6a95158809d03c28857002db`.
GREEN/RED/restore и честное отклонение stale attempt 1 согласованы с квитанциями.
Хеш pinned-governance.log сверён как один из артефактов приложения;
повторная независимая проверка governance, общего числа checklist markers,
live issue и числа всех задач не входит в это C0/H0 заключение.

Итог: конкретных новых C/H-блокеров или иных подтверждённых замечаний в
согласованном срезе нет; P2 release guard устранён. Требования T108 не меняются,
продуктовые handlers/trust не изменены. Принят только сценарий startup-error /
первый Quit / удержанный native worker / штатный drain и Closed. Весь T108,
T109, installed MSIX, реальный storage I/O, hardware и выпуск этим не закрыты.
Финальная сверка завершена до планируемого исполнителем удаления двух host
каталогов source/red-source. Рецензент их не удалял; manifests/logs/receipts
сохраняются, активная Windows base для T109 не входит в очистку этого ревью.

| Текущий артефакт final-2ywiz46z | SHA-256 |
| --- | --- |
| prepare-appmain-problem-ui.mjs | `6ee6bd23ff22e4976e79a3ac3ffc4d825893d4000ab9e6baf1cbc4370c1bb1a4` |
| AppMainProblemUiFixture.h | `f4a30df52345581877f4dd5c533028f30e704c554dc9798bc9ea9e5e9e9d3b67` |
| AppMainStartupExitUiLaunch.inc | `9d33be56a9eb0771ef13a71c4b0ba914c74991738ea09627a5d015a36d17d873` |
| source.json | `367d4c1bca8205dd32a19a99ef9b1f55f0d8bfa71109303263656de9885e4f5b` |
| test-source.json | `1436258ede9646fb4130e320db0d013181ccd9db672e09dcdcb8f230ace897f4` |
| appmain-test-bindings.json | `e7eedcfa5aa8bb828d188e44fc0f9b28439fbe697c36cf57a185f5f36313b067` |
| red-control.json | `4aabdb15972182fcbfedab879ddcac3fe3e6f45124f283a45aed53f3b0562f64` |
| red-test-source.json | `2be447171660b184246102df2f09a852dd4b2beab5c1d7ddad8cedace3ff67bf` |
| Run.ps1 | `ad638063534f99c9531d501ffaf9fa2c336b5b1a5d94d2b76c4ba89ec958e795` |
| build-result.json | `923f5d58dcacbf1d4f3e624d431a63916503200364b1fadafe5d14baa29e9caa` |
| green-result.json | `5ab30fbd64ccdaa391d6f26c2dd5628df327c42e619d1d22ee2d877941d21900` |
| green-ui.err | `f2d3c30f4cc660e2b17f7f81e6e5469f3bef7b287bff685692ca4ea41cd03404` |
| red-stale-build-result.json (отклонён) | `09e4760f727e15e6377428cf146c664599eb3807cfa9eaead04e9c4ef1f758d9` |
| Build-Red-Retry.ps1 | `7377ee9b3facb32700071f9a8fb26b3d52b08bedd69e998ffc4846b6fe6d642d` |
| red-build-result.json (attempt 2) | `b8d6becf32903d54685ad1cb8c069281506da9ad5dc80daf84a626be9a0e9a95` |
| red-result.json | `5bd8ee5a2ed3006dfe0e5810235e6930361fb9a283cec0777adacb3c47a87c8e` |
| red-ui.err | `74574a936dee257f22669320af8af71750597f4c930c4059d04318ec3d6d8d2f` |
| Restore-Green.ps1 | `bf1ee7e6ed5e67087cba3bc10b17ebe6f20d63b9125623d9d95445de485ca486` |
| restore-green.json | `08ed6fc7a9df67411c8293ed98c997b369622c52204ba820f0556c3f20b0ce2f` |

## SHA-256 исторического состояния: sahz6bkv

| Артефакт | SHA-256 |
| --- | --- |
| prepare-appmain-problem-ui.mjs | `6ee6bd23ff22e4976e79a3ac3ffc4d825893d4000ab9e6baf1cbc4370c1bb1a4` |
| AppMainProblemUiFixture.h | `f4a30df52345581877f4dd5c533028f30e704c554dc9798bc9ea9e5e9e9d3b67` |
| AppMainStartupExitUiLaunch.inc | `daff596e7c3e4b7d6125c8ef929ad614d96e5b184bfe73b21ae967420d19e77f` |
| appmain-test-bindings.json | `9afc51665e35758a1e243317309909b4cd00acdf97288f8133c5aa866e8ee759` |
| source.json | `f872955666384058c2683ee4ddb722abebf41b378e05164ab1a2ac428210ffb1` |
| test-source.json | `a0539dfae584c74b873ff721c23437583d976a6d3c9a6cd82707ee2ca7bd9054` |
| build-result.json | `7722fffd48fde74b6eaee236f0ff4b94e42bf388cd6041a6866a2dcf0450157f` |
| Run.ps1 | `cbcc14d11486c9a7f3942da8451bd7132f671c7379b36e1495635c437b5956d4` |
| green-result.json | `bf383e698ba6b59f2e97e8bb8de2f9574507429600f94cf85a0bb0d194c8dc86` |
| green-ui.err | `786f61d366c6e401272721adf590bdaba43c01f4c25a7691b7b33d71a734f4fb` |
| red-control.json | `35f4130929c8b603a8412ebdcaabce1a10bb1afcf25350628d0b49bce87e706e` |
| red-test-source.json | `988cb30be591cbe153d09a0db1519651d84b3d426d380645520b99b75a776ba2` |
| red-build-result.json | `ff249d237230d8bfc81954443a51c165a995117ff3b4726b85c985c158e5821a` |
| red-result.json | `6b4f09c88dbda73d5fcee8c7d3763c9dab9859bb31e855659a373854911998a0` |
| red-ui.err | `50a029283ecd916b85ba91426b1342985a1a5556e488f9d5c989b33c1d18a2de` |
| Restore-Green.ps1 | `74fd7117709eacb08eefb92767221e7562b8c8f5d176c90ffc297e3b4e9d6aef` |
| restore-green.json | `893a9b522c17d5a54ca773ebeefaba1947122f91d78b84a7ef70abfc2de892e0` |
| requirements.md | `91fecd3ca4c79eba15faa3543fce18f8d5db1eb7a6664701c683c460d0d5bc55` |
| security.md | `0a321d6d52a4f56d8c2888bd3fa639c85a7c9dc82b5a6acdc2bc3f1bb7a40273` |
| ux.md | `1a5a28f7226d7fc25bafdb8239b3d4bea2aeae0d4aad969eb89b45ec5b855801` |

Изменён только этот отдельный отчёт. Новые тесты на диске не создавались,
VM/trust/микрофон/сеть и установка рецензентом не использовались.
