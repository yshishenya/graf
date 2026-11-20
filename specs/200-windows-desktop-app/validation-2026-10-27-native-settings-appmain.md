# Настройки уведомлений через настоящий AppMain и WebView2

Дата: 2026-10-27. Активный F200, полоса `high-risk-product`, существующая
подзадача T104/#7281 и последующая приёмка T097/#7240, T109/#7343.
Рабочая копия: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`.
HEAD: `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`, проверяется грязный снимок.
Состояние: **full-chain PASS пока не получен; задачи остаются открытыми**.

## Конструкция проверки

Существующий `prepare-appmain-problem-ui.mjs` получил необязательный сценарий
`settings`; прежний `problem` остаётся значением по умолчанию. В отдельной
копии исходников заменяются только запуск приложения, безопасный тестовый
инициализатор automatic policy и входная точка. Forced include применяется
только к AppMain.cpp. Генератор побайтово проверяет сохранность 11 методов,
в том числе `configureCabinet`, `answerNativeSettings`, `bindNotificationContext`.
Продуктовые файлы при генерации не редактируются.

Загружаются настоящие текущие HTML, JS и стили общего кабинета. Данные
профиля, owner/workspace/session и HTTP-ответы определения аккаунта искусственные;
согласованный owner проходит настоящий decoder. `connect`, nonce, ответы
настройкам и обработчик AppMain не подменяются. Допускаются только локальные
ответы для точного списка ресурсов на стандартном доверенном origin;
прочие запросы получают 403. Certificate validation не отключается.

Создаётся эксклюзивный GUID-профиль WebView2, проверяются его фактический путь
и физическая идентичность до первого перехода. Permissions запрещены.
Сбой процесса не допускает Recreate в стандартном профиле: тест завершается
через штатное закрытие. В Registry заранее проверяется отсутствие точного
`sha256(synthetic owner)`; очистка удаляет только это значение, сохраняя key.
Кнопки записи выключены; готовность AEC тестовой capture-конструкции ложная.
Аудиозахват и рабочий сервер не используются. Установленный MSIX не заменяется.

## Source4: сборка прошла, пользовательский путь не прошёл

Windows 11 в Parallels ARM; Release PE x64, физический x64 этим не проверяется.
Проверены 218 исходных файлов до и после сборки, 113 входов общего кабинета,
22 ресурса; скопированные кабинетные assets совпали с текущей рабочей копией.

| Свидетельство | Результат |
| --- | --- |
| Полная сборка SDK, затем сборка исправленного AppMain | exit 0 |
| GUID-профиль до первого перехода | `profile_verified=1 starts_before_check=0` |
| Завершение навигации settings | наблюдалось |
| Начальное чтение native store | `present=0 quiet=0` |
| Допуск страницы к мосту | **отказ `response-metadata-timeout`** |
| Изменение quiet / возврат / preview | не выполнены |
| Завершение теста после закрытия пользователем | exit 3, ожидаемый отказ при неполном сценарии |
| Завершение браузера / очистка Registry | `browser_stopped=1 registry_cleaned=1` |

EXE source4 SHA-256:
`116510198823f51129b660270e02f28a3cd6a049a070ed9f32d44cef32064066`.
Продуктовый AppMain SHA-256:
`a7927bb8e84b05f0c747fdca7756edbd8b0509ce8f49a0083187ff9680f0ff38`.
Производный AppMain source4 SHA-256:
`6459d8889be5dfa47d6ef37be24d407aead43a010d45b6628c0e10f20ca2fcfd`.
Неизменённый WebView2Host.obj SHA-256:
`03a6e8adadb1624d7cbeb91fa7972b350f22e9bec68b8e9d7c381f5682011d05`.

Первые compile-only попытки отдельно сохранены: восстановление NuGet и Build
в одном процессе не подхватили созданные WinUI imports; отдельный Build решил
это. Следующая ошибка объявления `CommandLineToArgvW` устранена включением
`shellapi.h`. Source5 собран, но не запускался: ревью обнаружило слишком
раннюю проверку начального `unavailable`; она исправлена до исполнения.

## Следующая диагностика

Пассивный observer source6 читает только признаки двух document-ответов:
метод GET, статус, HTML MIME, наличие и ожидаемое значение Dest/Mode,
наличие и совпадение navigation tag, числовую generation и время.
Значения заголовков, cookies, URL, содержимое и пути профиля не печатаются.
Ни один метод принятия metadata не вызывается. При настоящем `unavailable`
после фактического `attach` проверка закрывается автоматически.

Исходное имя ошибки не устанавливает причину: оно возможно при отсутствии
коррелированных заголовков и при задержке последующего принятия истории.
Microsoft описывает ResponseReceived как наблюдение окончательного запроса;
добавочные заголовки могут появиться после Requested. Это основание для
наблюдателя, а не доказательство конкретного поведения локального ответа.
[Документация Microsoft](https://learn.microsoft.com/en-us/microsoft-edge/webview2/how-to/webresourcerequested).

Полные manifests, журналы, receipts и рецепты находятся в тестовом каталоге
`/Users/yshishenya/Documents/graf-f200-public458.po8CtB/settings-chain-li1qcg1c`.
Independent source gate записан отдельно в
`review-2026-10-27-t097-t109-native-settings-requirements.md`.
Cold-process restart, stale-document, установленный пакет, Mac, доступность,
аппаратная запись и выпуск этим запуском не принимаются.

## Source6: наблюдение фактических request metadata

Сборка exit 0, EXE SHA-256:
`f4e61d1f4846b2f293dca1b9829f7356551517f7f3d5d9ca18e9c5739be240ac`.
218 исходников проверены до/после. В фактическом событии наблюдалось:

```text
response=1 get=1 status=200 html=1
dest_present=0 dest=0 mode_present=0 mode=0 tag=0 tag_current=0
generation=2 elapsed_ms=1250 after_completion_ms=-1
```

Это устанавливает отсутствие трёх нужных request headers в наблюдаемом
локальном ответе. Оно не устанавливает, выполнялся ли штатный tagger,
и не доказывает неисправность обычного ответа рабочего сервера.
Допуск документа закономерно не получен; settings/set/read/preview не приняты.

Найден отдельный дефект тестового завершения: вызов `Window.Close()` из catch
завершил приложение с исходным exit 2 до timer cleanup. Отсутствующий terminal
receipt не объявлен успешной очисткой. Проверены отсутствие собственного
browser process, точное имя и время создания оставшегося GUID-каталога,
отсутствие reparse points и посторонних корневых элементов; удалён только
этот тестовый каталог. Точное synthetic Registry value отсутствует.
`source6-orphan-cleanup.json`: terminal=true, profile_cleaned=true,
registry_value_absent=true. Реальные профили и родительский Registry key
не удалялись.

В source7 все инициированные тестом закрытия переведены на одну closure:
closing/time → host.close/capture.shutdown → ожидание browser → очистка →
terminal → Window.Close/Exit. Дополнительно подготовлен ограниченный опыт
с перестановкой fulfillment после штатного tagger: до установки нового
обработчика работает deny-all, уже установленный production Response
сохраняется. Ранний запрос до перестановки ведёт в отказ. Новые заголовки
не создаются, методы принятия metadata не вызываются.

## Source7: порядок обработчиков исключён, очистка подтверждена

Сборка exit 0, EXE SHA-256:
`ddc844ddab0c30ec89e0bbb63c8671cfbcd38b16a29926b9bbc66e3494a4c133`.
Производный AppMain SHA-256:
`d6d5699a6fea8f581415f92ad795ec88531ba7aaf0fdda0df9e14814b1c4b520`.
Header SHA-256:
`2cff0f71ea71c5707692fc3d31652ec978fe8fd6442970595df363732a3173f8`.
Launch SHA-256:
`7948176946f786aa6be764f5cca4dd9d172b129b3ff1d0504755d7e651d92855`.

Наблюдалось **до** локального ответа:
`fulfillment_after_host=1 tag=1 tag_current=1`.
Затем фактический ResponseReceived снова дал GET/200/HTML,
`dest_present=0 mode_present=0 tag=0`, generation=2,
elapsed_ms=1047, до NavigationCompleted. Штатный tagger выполняется;
в наблюдаемом запросе локального ответа метка не сохраняется. Перестановка
не устраняет ограничение. Нет оснований повторять тот же опыт или менять
продуктовые проверки доверия, дописывая браузерные заголовки.

Полный сценарий снова **FAIL/HOLD**. После `settings_runtime_unavailable`
исправленный путь автоматически получил terminal:
`quiet=0 restored=0 preview=0 settings_loads=1 meetings_loads=0
browser_stopped=1 registry_cleaned=1 exit=3`.
Отказ не превращён в положительный UI-результат.

Независимая финальная проверка `postflight.json` завершилась exit 0:
218 source files, 22 resources и EXE совпадают с manifests;
owned_browser_processes=0, app_processes=0, owned_profile_folders=0,
registry_value_absent=true, full_chain_pass=false.
Установлен прежний GRAF 0.1.0.14, Status=Ok; его запуск и соответствие
текущим исходникам не подтверждаются. 113 shared source inputs также
сверены на Mac после исполнения; несовпадений нет.

Следующий срез — настоящий сетевой HTTPS-ответ с корректным доверием
сертификату и теми же обработчиками настроек. Локальная подстановка
не годится как положительное свидетельство текущего host. Новый транспорт,
доверенные сертификаты, policies и исключения защиты здесь не реализованы.
Такая конструкция требует отдельного узкого review до исполнения.
T104/T097/T109, cold restart, stale-document и общий Windows release открыты.


## Следующий срез: loopback HTTPS вместо подстановки ответа

В тестовом производном проекте конструктор CabinetWindow создаёт прежний
WebView2Host с policy `https://localhost:49317`. Рабочий CabinetWindow.h
и production AppMain.cpp не изменены. Генератор фиксирует эту замену отдельно;
11 обработчиков/связок AppMain по-прежнему совпадают побайтово.
Тестовый ресурсный обработчик разрешает только GET известных ресурсов
на этом origin, остальные запросы отклоняет. Разрешённый ответ приходит
через настоящий TLS-сокет; metadata, nonce и connect не подставляются.

Добавлен сервер на стандартной библиотеке Python: привязка 127.0.0.1,
проверка Host, manifest/hash ресурсов, запрет неизвестных путей, без журналов
URL/cookies/содержимого. Предварительный запуск на Mac подтвердил отказ
без доверия, HTML при явном cafile и 403 для постороннего файла; сервер
завершился с exit 0. Это проверка транспорта стенда, не Windows UI.

Runner предусматривает два последовательных запуска: без доверия сертификату
и с временным доверием только конкретному одноразовому публичному leaf
в CurrentUser Root. До импорта проверяются SHA-256, localhost SAN,
critical CA:false, serverAuth и срок до двух дней; наличие в store заранее —
отказ. LocalMachine и My не меняются. finally удаляет только свой thumbprint
и сравнивает перечень Root до/после. Certificate exceptions и browser
ignore-certificate flags не добавляются. Отрицательное свидетельство требует
фактического certificate WebErrorStatus, а не произвольной ошибки приложения.
До независимого review импорт и запуск UI не выполняются.

Source8: 219 входных файлов, Build exit 0, PE
`e494ba5caa5a47df05be889ef49593ba7becc6feef87c0c222aeed9d0c2ff061`;
не запускался. Source9 добавляет runner, passive TLS observer и close.request
для штатного завершения изолированного теста. Проверка PowerShell parse
в Windows прошла; leaf проверен как CA:false/serverAuth/localhost,
заранее не доверен. Результат source9 и runtime будут записаны отдельно.

Source9 сборка завершилась: BUILD_EXIT=0, source_files=220,
post_source_files=220, PE SHA-256 `1ca5a34213729acb480b0b3317b0c8d56a3601de4e2edcefde0f6466973d4511`.
Рабочие 220 входных файлов и 11 неизменённых методов сверены после подготовки.
Production WebView2Host.obj остался
`03a6e8adadb1624d7cbeb91fa7972b350f22e9bec68b8e9d7c381f5682011d05`.
Сборка не является runtime или full-chain PASS.


## Source10: исправления очистки и отрицательный Windows TLS-контроль

Независимый review сначала нашёл C0/H2: общий cleanup try мог пропускать
сервер при зависании app; промежуточный full_chain_pass мог оставаться true
при последующем отказе восстановления trust. Оба исправлены: отдельные
ограниченные попытки завершения собственных процессов, timeout TLS handler,
принудительное завершение означает FAIL, итог https_slice_pass вычисляется
только после очистки. full_chain_pass остаётся false всегда: CUA, холодный
перезапуск и отрицательный stale-document сценарий этим срезом не покрыты.
Повторный узкий review текущего runner: C0/H0, SHA-256
`15823166fee6e4fecabcee5e1ad7406aa579d7a393d29d74d6bf12300dcdc39d`.

Source10 изменяет относительно source9 только Python server и PowerShell
runner; C++ и производный AppMain побайтово прежние, используются PE/obj
source9. 220 файлов guest до/после копирования проверены по manifests;
PowerShell parse PASS. Mac smoke2: untrusted rejection, trusted HTML,
unknown resource/Host/non-GET/plain HTTP denied, stalled TLS cleanup ≤5 s.
Это transport evidence, не браузерная приёмка.

Windows negative без импорта сертификата завершён:
`tls_rejected=1 web_error=5`, settings_loads=0, meetings_loads=0,
нет native_read present=1, native exit=3,
`browser_stopped=1 registry_cleaned=1 profile_cleaned=1`.
Runner exit=0 означает ожидаемый TLS-отказ и очистку;
`untrusted_refused=true`, app_stopped/server_stopped/trust_restored=true,
full_chain_pass=false, https_slice_pass=false. Ошибка общего запуска
не выдана за положительный UI-результат.

Positive запущен тем же PE/leaf, но Import-Certificate показал штатное
Windows Security Warning. На момент этой записи импорт ожидает действия
пользователя; положительный результат отсутствует, native UI ещё не открыт.
Подтверждение системного доверия запрошено пользователю; автоматически
нажимать Yes или обходить предупреждение не стали. Скрипт остаётся активным
для штатного завершения и очистки после ответа. Установленный GRAF не обновлён.
T097/T104/T109 и общая приёмка Windows открыты.


## Независимый срез T108/T110/T111 во время ожидающего TLS-подтверждения

HTTPS runner подтверждён как живой через исходный session handle; терминальной
квитанции positive ещё нет, ожидающее Windows Security Warning не обходилось.
Параллельно прочитаны действующие Window.Closing, requestExit/beginExit,
refreshNativeState, ShellClosePolicy, восстановление при недоступном трее,
индикатор и WindowsTray. Исходники не менялись.

В отдельном временном каталоге на Mac выполнены CMake configure,
сборка RecordingIndicatorTests и `ctest -R '^RecordingIndicatorTests$'`:
все exit 0, **1/1 PASS**, 0.58 s. EXE/Mach-O SHA-256
`4f682e1a9ac0a10b581ce30681a99a9c5e0c9354a8e8dbddc562b5d73be5f7af`. Входной manifest Windows
`487cba19270355e9074285e882f9d32cd281b598b656b3bddf031272342d2131`: 220/220 текущих исходников совпадают.
Это переносимые проверки решения hide/keepVisible/wait, неизменности
сессии/автоматического отслеживания и source-order assertions. Win32-ветки
меню, реальное закрытие WinUI, foreground и установленный MSIX не запускались.
Данный PASS их не подтверждает и не закрывает T108/T110/T111.
Журнал и контрольная сумма сохранены; временная сборка удалена.
Первый guard очистки отказал из-за неверного предположения о /private/tmp;
после проверки реального tempfile.gettempdir удалён только точный каталог
этого запуска. Ошибочный guard не удалял файлов.


## Актуализация состояния master без слияния

`git fetch origin master` завершился exit 0. HEAD текущей feature:
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`, origin/master: `c4a742eb9fb3f9c9d62d8c4f6e5b9bd12c0a62c4`.
Разница истории HEAD...master: 70 feature-only / 251 master-only commits.
Это не число конфликтов и не факт синхронизации исходников.
После предыдущего проверенного master
`c5bbab2cd87c8ff6b9665ec4f54d4129c060c6e9` изменены публичные руководства,
документация/спецификация F125 и подготовка серверного релиза; новых изменений
apps/windows, apps/macos и cabinet в этой последней дельте нет.
Длинная разница между текущей веткой и master остаётся и должна быть
интегрирована с сохранением незакоммиченных изменений до окончательной приёмки.
Fetch не менял рабочие файлы, HEAD, установленный MSIX или рабочий сервер.


## T108: исправлен пропуск exit polling после startup error

Независимый разбор обнаружил M1/P2: исключение после создания capture/storage
оставляло shellReady=false; ранний return пропускал создание stateTimer.
Первый Quit мог получить недренированный worker, а после его завершения
повторной проверки exitWorkDrained не было. Это source-контрпример,
Windows held-worker UI-воспроизведение не заявлено.

Перенесён прежний timer/start перед ранним return; callback захватывает
shellReady по значению и вызывает прежний refreshNativeState только при
shellReady || exitRequested_. Частично созданная оболочка до Quit не
обновляется; после Quit работает существующий exit branch. Второй executor,
новая финализация и блокирующее ожидание не добавлены.
Узкий повторный review: C0/H0/M0, source-level M1 закрыт в существующей T108.
AppMain SHA-256 `a85f5024813dbe4fdabbf879485bf12b4343b65b4a1709af1dbe8fdb012436c0`;
RecordingIndicatorTests SHA-256
`d37c09c7c416924bc2bbf7ed3a9b362beadc218cbcb3d0a8c8ae4acf69ed73a4`.

Добавлена source-wiring регрессия: Start до !shellReady и защитный callback.
На старом тексте порядок не выполнен (RED); на новом configure/build/ctest
RecordingIndicatorTests exit 0, **1/1 PASS**. Mach-O SHA-256
`6e40b183cfee2c1f14bd0390d8c901a86b55b30f872a6c2733e7961350e82974`. 220 входных файлов сверены до/после;
временная сборка удалена, журналы сохранены. Source assertions не заменяют
native held-worker/первый Quit в настоящем WinUI; T108 остаётся открыт.

Ожидающий HTTPS PE source10 не заменён и не пересобран. Он не проверяет новое
поведение startup, его 11 production settings bindings не изменились.
Новый SDK compile-only исходного production AppMain без forced test fixture
запущен отдельно; это не link, MSIX, установка или native UI acceptance.


SDK compile-only production AppMain завершён: **compile_exit=0**,
input_files=220, исходный SHA-256 совпадает с текущим
`a85f5024813dbe4fdabbf879485bf12b4343b65b4a1709af1dbe8fdb012436c0`. На Mac после компиляции
220/220 snapshot и текущих файлов также сверены. В response file отсутствует
/FI тестовой fixture, вход — оригинальный AppMain.cpp с обычным OnLaunched;
использованы прежние x64 SDK include/define/optimization flags.
Object SHA-256 `05d0f4c595a2998454236075a5c1a28f79878d878709bc648b3c8fb06d717a98`.
Временные guest object/PDB удалены, журнал/рецепт/manifest/hash сохранены.
Установки, запуска, линковки и подмены ожидающего HTTPS PE не выполнялось.
Native startup-error first-Quit с удержанным worker ещё не принят.


## 2026-10-28: настоящий HTTPS загружен; полный ручной сценарий не завершён

После подтверждения человеком импорта того же временного localhost-сертификата
ожидавший runner продолжил работу. Старый host session 84586 уже отсутствовал;
повторного запуска не делалось. Независимый process inspection подтвердил
живой прежний PowerShell runner и его Python/GrafWindowsApp children.

В реальном WebView2 загружены settings и затем meetings: GET 200, HTML,
Sec-Fetch-Dest=document, Sec-Fetch-Mode=navigate и актуальный navigation tag
присутствуют; document generations 2/3. В изолированном native Registry
прочитано present=1, quiet=1 после ручного переключения. Таким образом,
прежний synthetic-response metadata timeout не воспроизвёлся при этих двух
настоящих HTTPS-переходах; это не общее доказательство всех history paths.

После meetings observer получил failed NavigationCompleted с web_error 0/14,
fixture завершилась settings_runtime_unavailable. Exact URL и действие возврата
журнал не содержит; утверждать причину и считать это production defect нельзя.
Уточнение пользователя о Back либо Settings запрошено. Нажатия/Tab через CUA
не дали подтверждённого переключения до ручных действий; ошибку продукта
по этому факту не заявляем.

Конечный результат — **https_slice_pass=false, app_exit=3**:
quiet=1, restored=0, preview=0, settings_loads=1, meetings_loads=1.
Сообщение пользователя «готово» не подменяет эти неполные evidence.
Положительная полная цепочка не принята, T097/T104/T109 не закрыты.

Штатная очистка подтверждена runner и отдельным read-only postflight:
browser_stopped, registry_cleaned, profile_cleaned, app_stopped, server_stopped,
trust_restored и fresh_tls_refused — true; owned processes/profiles 0,
изолированное Registry value и точный сертификат отсутствуют. Postflight
сверил 220 guest source files, 22 resource files и неизменный PE
`1ca5a34213729acb480b0b3317b0c8d56a3601de4e2edcefde0f6466973d4511`.
Installed GRAF остаётся 0.1.0.14, Status Ok; этот тест его не обновлял.
Исходный production snapshot current220 также совпадает 220/220; ожидавший
тестовый PE по-прежнему не включает последующий startup Quit fix.

Сохранённые SHA-256:
- `trusted-ui.err`: `6ba1d5c08389dd24eb5aa9b57a90125d0a012812b496a9d613db2ecf1c6b5165`.
- `trusted-result.json`: `624c9fa48809f2191f92fccabf3b5bb501f4d4cca2eaa77366bb321bd7025e03`.
- `https-postflight.json`: `b36fe25cb24608937343b437b3f9a004ac2202b771703385fec55201291d6f8e`.
- `server-counts.json`: `970829e196c02eae5de359f8e3d6dd34cd878ee33f3fabc74545192ceebe38f8`.

Независимый source review подтвердил отдельное ограничение fixture:
в экспортированном meetings HTML ссылки Settings ведут на
`/desktop/settings` и `/desktop/settings/account`, отсутствующие в 22-resource
allowlist. Fixture отвечает 403 до сервера, поэтому server denied=0
не исключает этот путь; passive response observer охватывает только два
известных документа. Это подтверждённая неполнота стенда, не установленная
причина конкретного отказа. Перед повтором нужно уточнить путь пользователя
либо включить настоящие промежуточные страницы/redirect и категоризированную
диагностику; production trust/response/history guards не ослаблять.


## 2026-11-03: восстановлен обычный путь возврата через общие настройки

Активный F200 / существующие T097/T104/T109, без изменения продукта или
контракта. Независимый допуск требований: 74 подтверждённых пункта, 0 открытых;
отдельный отчёт `review-2026-11-03-native-settings-fixture-routes.md`.
Исторический FAIL сохранён; причина конкретного прежнего web_error=0/14
по-прежнему не выводится только из отсутствия ресурсов.

Тестовый HTTPS-сервер теперь в точности отвечает на GET `/desktop/settings`
перенаправлением 303 на `/desktop/settings/account`, как production embedded
route. Адрес разрешён только при наличии account в замороженном manifest.
Страница account получает HTML MIME; остальные неизвестные пути и чужой Host
запрещены. Adapter требует все три общие страницы и разрешает корневой путь
только внутри прежнего same-origin/GET ограничения. Категории navigation,
redirect, document/allow и существующий constant-stage failureDetail помогают
различить отказ, не записывая URL, заголовки, идентификаторы или содержимое.
Production WebView2Host, доверие, correlation/nonce/history и обработчики
AppMain этим изменением не ослаблены.

Ресурсы заново экспортированы из текущих общих шаблонов через существующий
синтетический FastAPI harness: 23 ресурса, включая account, 112 server source
inputs. `/desktop/settings` остаётся перенаправлением, а не отдельной HTML-копией.
В тесте нет реального аккаунта, записи, отправки данных или установки пакета.

Проверки:

- `python3 apps/windows/Tests/GrafWindowsContractTests/test_appmain_settings_loopback.py`
  — PASS: настоящий TLS с локальным CA-файлом без изменения системного доверия,
  redirect/HTML/JSON, query, unknown/traversal, чужой Host, POST, plain HTTP,
  отказ запуска при изменённом содержимом manifest. Старый сервер на той же
  проверке — RED: обычный settings root возвращает 403.
- Генератор SDK derivative сохранил 11 production handler sections побайтно;
  source/test-source по 221 файлу. Release x64 MSBuild — BUILD_EXIT=0.
- Новый PE SHA-256: `f14dc3a77b4e7ef2556d0f7e3f667f6158172ddbdcac93c17fc3aae14a8afaed`.
- Настоящий WebView2 без доверия новому локальному leaf: PASS отрицательной
  проверки (`untrusted_refused=true`, `web_error=5`), ни одного принятого
  документа или native write. Browser/app/server остановлены, свой профиль и
  synthetic Registry value удалены; trust snapshot восстановлен.

Standalone Python check был дополнен POST/plain-HTTP отрицательными случаями
после заморозки компиляции. Это единственное расхождение текущего Windows source
со сборочным manifest: этот файл не является входом C++ compilation. Его
актуальная версия отдельно привязана в `transport-test-result.json`; product и
C++ fixture совпадают со сборочным снимком.

Артефакты: `/Users/yshishenya/Documents/graf-f200-public458.po8CtB/settings-return-20261103.qcbz2uck`.
Контрольные суммы квитанций:

- `build-result.json`: `0f470bbabc6fda8420cef1d8176c6e5c31987f2931e811677c1ce76815a07937`
- `resources.json`: `aa839a28a717f46dd90ab8f2d08c6bb60feb240da544afd927ebbd4f109f98b4`
- `source.json`: `dd0cf3c6f192f8ca3307599456418877dfbcb738cdce92d92aa5f246df62de51`
- `test-source.json`: `d74fec3d11b361319173a2b30c58acf9bf82d0a7a9084894c957f610bed120b3`
- `shared-source.json`: `742525dbe52a5d15dc18f02eb90b4bf9ca6949e1c45b089637b3a5f1864d968e`
- `untrusted-result.json`: `46c60e02f0eec02dac2f8b493480ee7f6dbf0ff27c5dae18d141dea3f148861c`
- `untrusted-ui.err`: `3a61098f2bfa01e9f6c0b4f240e8d8e002728c3f1fe8e81afb378864ee05416c`
- `transport-test-result.json`: `b1fb4a3c436ce1c0238d5b553ad35ecd554902cde24f072b8a1fac118a7f6222`

Положительный ручной HTTPS-сценарий ещё не принят. Предыдущий leaf истёк;
подготовлен новый одноразовый localhost leaf, запрос согласия перед временным
добавлением в CurrentUser Root отправлен пользователю. Сертификат пока не
добавлен. T097/T104/T109, установленный MSIX, холодный перезапуск, клавиатура,
Mac parity, аппаратная и полная релизная приёмка остаются открытыми.


### Текущий положительный запуск после согласия пользователя

Пользователь отдельно разрешил новый одноразовый localhost certificate test.
После подтверждения Windows загрузка notifications прошла через настоящий HTTPS:
GET/200/HTML, Dest/Mode/current tag=1, generation=2, 4656 ms; native read quiet=0.
После прерывания host exec handle 86891 исчез, но независимый guest inspection
в 12:54:32 UTC подтвердил живые runner PID12360, server PID3576, AppMain PID4040,
сертификат присутствует, terminal receipt отсутствует. Второй запуск не начат.
Средство управления экраном недоступно после изменения набора инструментов;
пользователю передан точный обычный путь Settings → Notifications. Исходный
runner сохраняет собственные deadlines и cleanup; завершение пока не принято.

Замечание независимого ревью P2 к standalone transport check устранено:
при communicate timeout завершается только собственный server и выполняется
повторный bounded communicate, затем исходный timeout возвращается вызывающему.
Обычная проверка PASS; принудительный timeout отдельным subprocess monkeypatch
подтвердил проброс TimeoutExpired и poll()!=None для собственного процесса.
Скомпилированные C++ adapters/production source от этого не менялись.
Повторная доставка рецензенту после прерывания недоступна (agent not found);
решение самого рецензента не переписывалось основным агентом.


### Общие настройки и актуальный master

`git ls-remote` и затем `git fetch origin master` подтвердили текущий
remote master `eab30ac17aa676e25fd367735cbdb39a48eaf40c`;
remote F200 остаётся `a9691d4d474d918f54493d55a3aba286c749b513`.
Рабочий HEAD не изменён; слияние, commit, push, PR и установка не выполнялись.
В свежем master есть Mac-only исправление F277
`5e5bb23f6fb68d6a9436f71e45c0c16e0f64969d`: синхронизация cookies и начало
чтения настроек после окончания auth navigation. Это повод сохранить проверки
порядка session/document/read на Windows, а не доказанная причина прежнего
Windows web_error и не автоматический перенос Swift-кода.

Первый запуск settings-consistency без подготовленного harness остановился на
ERR_CONNECTION_REFUSED (8874), до проверки страницы; продуктовый дефект из этого
не выводится. Повтор с собственным synthetic FastAPI harness на свободном
loopback-порту прошёл: **224 page/theme/width cases**, common controls, system
dark, reflow и dialogs PASS. Harness штатно завершён, установленное приложение
не изменено; журнал `shared-settings-browser.log`.
Отдельный `node apps/server/tests/browser/settings-consistency.test.cjs --notification-contract`
прошёл **37/37**, включая старые ответы/nonce, смену аккаунта и поздние
read/test ответы поверх нового черновика. Это shared JS/browser, не native
Windows или installed/Mac приёмка.

Актуальная standalone проверка после P2 привязана отдельно:
`transport-test-final-result.json` SHA-256
`a5229c06a557263ad238b9a9d57618d7721a59ba9d7157557b2dc567585b6ba2`.
Independent untrusted postflight: 221 исходник, 23 ресурса и PE совпали;
своих app/browser/profile нет, synthetic Registry value и certificate отсутствуют;
установленный GRAF остался 0.1.0.14 / Ok. Этот postflight предшествовал новому
положительному запуску и не доказывает его будущую очистку.


### Положительный запуск завершён FAIL; пользовательская обратная связь

Пользователь подтвердил: тихий режим включён, кнопка «Встречи» не работает,
затем приложение закрылось. Журнал принял native quiet=1 и документ meetings,
после чего получил navigation/document=other, allowed=0 и
host_failure=response-metadata-timeout. UI-приёмка противоречит полному PASS:
page=meetings подтверждает только загрузку, не работоспособность кнопки.
Fixture штатно завершилась exit=3, quiet=1/restored=0/preview=0,
settings_loads=1/meetings_loads=1. Причина закрытия — обработанный failure
тестового стенда, не доказанный crash установленного GRAF.

Cleanup принят отдельным trusted-postflight: 221 source/23 resources/PE совпали,
owned app/browser/profile=0, synthetic Registry value/certificate отсутствуют;
runner подтвердил trust_restored и отказ свежего TLS после удаления leaf.
Установленный GRAF остался 0.1.0.14 / Ok. Новый запуск с trust не начат.
- `trusted-result.json`: `dbf5d88000d6d8cf1d5723640c4703744d665b5f2a2b0ab2f3d4147a8703f6c7`
- `trusted-ui.err`: `eed15f3afb46ecf82c0d747507f074d90a406fa73e79e0a517b8ea4c8d092653`
- `trusted-postflight.json`: `88d8b553f1d403769d81d64c0329f872678d2beeed48d13f9fc149768fe39b78`

Дополнительно подтверждена конкретная ошибка конфигурации fixture:
генератор заменял trustedOrigin в CabinetWindow constructor, но оставлял
openCabinet() → https://rec.2brain.pro/desktop/meetings. При localhost policy
этот URL получает openExternal, и native кнопка, вызывающая openCabinet(),
не выполняет нужную внутреннюю навигацию. Это объясняет подтверждённый no-op
кнопки стенда; точный следующий document=other из старого журнала не восстановлен.

Минимальная правка генератора меняет этот home URL только в derivative,
объявляет замену в bindings/manifest. Product CabinetWindow.cpp не изменён.
Startup adapter теперь требует реальный openCabinet() результат allow/meetings
с точным локальным URL до attach и затем, как раньше, открывает notifications.
Следующий denied document получает только SHA-256 path без query/URL/content,
чтобы отличить оставшийся неизвестный маршрут без публикации личных данных.
Подготовлен новый отдельный source snapshot
`settings-home-20261103.meye7krg`: 221 source, 23 ресурса, 11 неизменных handlers;
новая SDK сборка начата. Старые FAIL/PE/manifests не переписывались.


### Сборка и отрицательная проверка home-binding исправления

Новая Release x64 сборка BUILD_EXIT=0, 221 source до/после;
PE SHA-256 `4930911152d4caba3f0a5204169c062459a944dc515ced5fea7db4df35aaac43`.
Текущие 221 Windows source совпадают с замороженным снимком, все 11 production
handler sections сохранены. В bindings дополнительно явно объявлена замена
CabinetWindow home URL в тестовой копии. Production-код этим не изменялся.

Новый настоящий WebView2 untrusted run: untrusted_refused=true, web_error=5,
нет успешного документа/native write, terminal cleanup browser/Registry/profile=1.
Поскольку SETTINGS_UI profile_verified и navigation=notifications находятся
после нового settings_home_origin_binding require, этот запуск также подтвердил
реальный результат openCabinet() allow/meetings с локальным URL до attach.
Это проверка destination dispatch, а не подтверждение клика/изображения списка.

Повторного импорта trust или ручного положительного сценария пока не было.
- `source.json`: `b64f240da31fb63f43d9593b08131c2cb08b227762e93dd866ca7ae62eb8dc5f`
- `test-source.json`: `8838b7f11739484dfad2a18d4bab55cf4815b4a346606a86714b6ad1d09d8c66`
- `appmain-test-bindings.json`: `32edbf3fc8fc2eab79763fe816822f10c32a77f9d90a90d148e8c2bb907166f5`
- `build-result.json`: `cda482ae68856492c101af7e8181175cce6466ed64c22116bda34592e6b1163b`
- `untrusted-result.json`: `46c60e02f0eec02dac2f8b493480ee7f6dbf0ff27c5dae18d141dea3f148861c`
- `untrusted-ui.err`: `5767e91b77002918cd440a0cdc4720f6aa1d5f44fc835ea4dcb1d085ae672af0`


Независимое source review home-binding исправления: C0/H0, PASS;
`review-2026-11-03-native-settings-home-binding.md`. Прежнее P2 к timeout
standalone проверки закрыто рецензентом после собственного normal/fault запуска.
Новый независимый untrusted postflight подтвердил 221 source/23 resources/PE,
нулевые owned app/browser/profile, отсутствие synthetic Registry value и
сертификата. Установленный GRAF остаётся 0.1.0.14 / Ok.
Ручной положительный повтор не запускался: предыдущий одноразовый test
consent израсходован, пользователю отправлен отдельный запрос на повтор.
T097/T104/T109 и остальные открытые задачи не закрывались.


Пользователь явно разрешил повторный одноразовый trust test после исправления
home-binding. Запущен готовый `settings-home-20261103.meye7krg/Https-trusted.ps1`,
точный PE `4930911152d4caba3f0a5204169c062459a944dc515ced5fea7db4df35aaac43`.
Новый host exec handle 21337; сначала отдельно проверяются quiet-on и native
«Встречи». Это начало проверки, не положительная приёмка или очистка.


Повторный положительный запуск действительно прошёл settings → meetings →
settings_root (303) → account (GET 200 HTML) → notifications (generation=6).
Новый native read подтвердил quiet=1 и returned_quiet=1. Пользователь подтвердил
видимую карточку после preview. Перед close.request поставлена проверка
фактического native quiet=0; она пока не прошла, поэтому close.request не создан
и тест остаётся живым. Пользователю задан точный вопрос о текущем положении
переключателя и ошибке сохранения. UI-подтверждение карточки не подменяет
обязательное восстановление выбора и terminal receipt.

### 2026-11-03: положительный нативный сценарий и отдельное восстановление trust

Пользователь подтвердил, что «Тихий режим» выключен и ошибки сохранения нет.
Журнал того же запуска содержит новый `native_read present=1 quiet=0`.
Только после этого создан `close.request`. Нативный процесс завершился с
`exit=73`, `quiet=1 restored=1 preview=1 settings_loads=2 meetings_loads=1`,
`browser_stopped=1 registry_cleaned=1 profile_cleaned=1`.
Таким образом на точном тестовом PE подтверждены: включение тихого режима,
реальная кнопка «Встречи», возврат через обычные настройки/account,
повторное чтение сохранённого выбора, восстановление выключенного состояния
и показ карточки, который дополнительно подтвердил пользователь.

Общий запускатель **не прошёл**: `trusted-result.json` содержит
`native_scenario_pass=true`, но `trust_failure="Cannot find object or property"`
и `https_slice_pass=false`. Во время задержки штатного удаления агент запустил
вторую попытку удаления того же точного сертификата. Пользователь затем
подтвердил, что видел системный запрос удаления и подтвердил его; сейчас
никаких запросов не видно. Конкурирующие попытки очистки — ошибка организации
проверки. По одной строке исключения нельзя установить, какая из попыток
обработала системное подтверждение или приписать ошибку продуктовой логике.

Отдельная проверка восстановления закончилась с exit 0:
`test_certificate_absent=true`, `other_roots_unchanged=true`.
Не импортировался новый сертификат и не менялись другие доверенные корни.
Штатный запускатель завершился с exit 1; его ошибочная квитанция сохранена.
Повторный положительный запуск для изменения результата не выполнялся.

Независимый postflight в Windows завершился с exit 0: 221 исходный файл,
23 ресурса и PE совпадают со снимком; app/browser/profile=0,
synthetic Registry value и точный сертификат отсутствуют.
Свежая инвентаризация в `2026-11-03T13:30:46.7930382Z` показала отсутствие
принадлежащих проверке app/server/runner процессов и сертификата.
Установленный пакет по-прежнему `0.1.0.14 / Ok`; он не заменялся тестовым PE.

Привязка текущего сценария:

- PE SHA-256: `4930911152d4caba3f0a5204169c062459a944dc515ced5fea7db4df35aaac43`.
- Все 221 текущих Windows-входа побайтово совпали с `source.json` после очистки.
- `trusted-ui.err`: `547daec76c5abc7e5f80857a3a5b8ef83be3c126e3bbbc49f31016c5ad35d79d`.
- `trusted-result.json`: `ba8f0ab089898e9b05979524970ec1b78270a1dc03e4009b92e23255e4b06f77`.
- `owned-leaf-recovery.json`: `0ed4c17fdbdc64ad1735c06836bee3ed6c57ba6a062091fabeaff5ec3d8c3700`.
- `trusted-postflight.json`: `7a17b9019372a3cd6a248ac294a0f8dff75ee726cca787246bbc60ce0f6a514b`.
- `server-counts.json`: `32bcdee7797cd513f663fd4c1aa35df24b0850e189efa06c2f82b58b1febe41a`;
  served=46, denied=0. Этот счётчик сам по себе не доказывает сценарий.

Для следующих проверок: один запускатель владеет удалением сертификата;
при задержке сначала проверяются его состояние и системное подтверждение,
вторая мутация хранилища доверия параллельно не запускается. Отдельное
восстановление допускается после завершения/остановки владельца с явным
учётом FAIL исходного запуска. Оно не превращает прежний FAIL в PASS.

Нативный settings-сценарий принят в указанном ограниченном объёме. Общий
HTTPS cleanup gate остаётся FAIL/recovered; T097/T104/T109 и полный Windows
паритет не закрыты. Холодный запуск, устаревший документ/nonce, установленный
MSIX, клавиатура и остальные продуктовые/аппаратные gates этим не проверены.

Независимое заключительное ревью —
`review-2026-11-03-native-settings-terminal.md`: C0/H0 в проверенных границах,
native PASS / original runner FAIL / отдельный recovery PASS. Сравнение
`other_roots_unchanged` относится к состоянию до и после recovery;
исходный snapshot первоначального runner и fresh-TLS refusal этим не доказаны.
После остановки сервера и подтверждённого postflight удалён только созданный
для данного опыта временный закрытый ключ; журналы и публичные материалы
сертификата сохранены. Повторный импорт/тест не выполнялись.

Заключительный governance сначала отказал: общая установленная на Mac CLI
стала Spec Kit 1.2.6 при закреплённой проектом 1.0.7. Общая установка и lock
проекта не менялись. Во временный отдельный UV_TOOL_DIR/UV_TOOL_BIN_DIR
установлен точный `git+https://github.com/github/spec-kit.git@fe1d00e3ccaf495880aaf90fb0e17679e82f065b`.
С этим настоящим CLI и его VCS metadata прошли
`speckit-bootstrap . --doctor --frozen` и
`python3 scripts/check_spec_kit_governance.py`, оба exit 0.
Временное окружение после проверки удалено. Простой `uv run --with` перед
этим подтвердил версию, но не прошёл проверку VCS metadata; тот результат
не засчитывается. Журнал успешной закреплённой проверки `pinned-governance.log`:
SHA-256 `5a34e1528d52708bdf9c76b259ba3a57266baab2f7a6d889f1ba9861dd89d7f4`.
Проверка без закреплённого окружения по-прежнему зависит от общей CLI;
обновление версии инструмента в проекте в этот срез не входит.
