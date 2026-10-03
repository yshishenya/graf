# T119: Windows-native передача HTTPS ссылки установленному Телемосту

Дата: 2026-10-03. Статус: исследование завершено; installed registration и подпись подтверждены, activation/native handoff остаётся OPEN. Не принятие реализации и не runtime acceptance.

Канонический worktree: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`. HEAD при начале чтения: `99b00a579c24b50e320465b69d9a296038bc544d`; это идентификатор начала исследования, не заявление о неизменности checkout при параллельной работе. Прочитаны только относящиеся к handoff нормы, первичные публичные документы и ограниченные native metadata в существующей VM. Единственное созданное содержимое — этот документ. Storage research/amendment, bridge/fresh resolver implementation, norms/tasks/reviewer marks, Git и внешние сообщения не изменялись.

## 1. Вывод для решения владельца

В Windows11 ARM64 VM реально установлена Win32 версия Yandex Telemost2.42.4.9707. В единственном обнаруженном загруженном пользовательском Classes hive зарегистрирован protocol/class **`telemost`**, с командой **`"C:\Program Files\Yandex\YandexTelemost\YandexTelemost.exe" --conf-url="%1"`**. У этого EXE native Authenticode status `Valid`, signer `YANDEX LLC`. Это наблюдаемые факты, а не угаданные имя/путь/CLI.

Однако HTTPS association того же загруженного пользователя имеет ProgID **`MSEdgeHTM`**. Поэтому unqualified `QueryUriSupportAsync(httpsUri, Uri) == Available` или `LaunchUriAsync(httpsUri) == true` нельзя превратить в доказательство запуска именно Телемоста. Package Family Name/AUMID для клиента не установлены этим исследованием; appx inventory с фильтром Telemost/YANDEX дал0 matches. `TargetApplicationPackageFamilyName` не является полем для EXE path/ProgID, а `ActivateForProtocol` не является универсальной активацией произвольного Win32 shortcut.

**Один конкретный кандидат для следующего разрешённого native gate:** `ShellExecuteExW` с `SEE_MASK_CLASSNAME`, `lpClass=L"telemost"`, `lpVerb=L"open"`, `lpFile=исходная validated HTTPS ссылка`, `lpParameters=nullptr`. Это явно выбирает найденную Windows association, не строит custom URI и не копирует registry command в собственный shell/CLI запуск. Microsoft документирует class selection; при этом передача HTTPS в именно этот Telemost class/клиент остаётся непроверенной. Кандидат нельзя объявить работающим либо уже принятым T119 до gate ниже.

Если явный class dispatch с HTTPS не работает, следующий безопасный шаг — получить документированный provider URI contract либо реальную packaged appUriHandler identity. Не подставлять guessed `telemost://...`, не запускать EXE напрямую с самостоятельно составленным `--conf-url`, не маскировать открытие Edge как native handoff.

## 2. Принятые границы, которые не менялись

[windows-native-web-bridge.md:430](/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup/specs/200-windows-desktop-app/contracts/windows-native-web-bridge.md:430), §10:

- Строки432–438: один existing HTTPS validator, запреты userinfo/control/backslash authority, действующий host-policy corpus, сохранение query/fragment. Исследование не меняет validator и не добавляет новый resolver.
- Строки440–449: выбор по validated host/path, не `provider_family`; Телемост получает validated HTTPS через штатную Windows association без выдуманного EXE/bundle ID/custom scheme; native conversion только без порта/на443.
- Строки450–459: browser-only/recovery через `IgnoreAppUriHandlers=true`; Available допускает API launch, unknown/error/installed-unavailable не становятся «приложения нет»; current check перед dispatch; False/exception — отказ; GRAF credentials не передаются; native association/result требуют installed проверки.

[calendar-join-design review:218](/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup/specs/200-windows-desktop-app/checklists/review-2026-10-02-calendar-join-design.md:218) и строка242 оставляют техническую native URI/activation неизвестность OPEN. Наличие подписанного клиента уточняет эту неизвестность, но не закрывает implementation/design/native gates и не меняет смысл `handed_off`/Join-and-record.

При предложенном явном class dispatch нужно отдельно согласовать с владельцем существующего opener gate, что identity-specific association check дополняет, а не заменяется общим HTTPS preflight. Этот отчёт не разрешает молча менять API/error taxonomy или нормы §10.

## 3. Первичные публичные источники: что они доказывают

### 3.1. Яндекс

Текущая [desktop инструкция «Подключиться к звонку»](https://yandex.ru/support/yandex-360/customers/telemost/desktop/ru/call/join) описывает переход по ссылке, предварительную проверку видео/звука и отдельное подключение; также ввод номера либо ссылки в desktop клиенте. Она не публикует PFN/AUMID, Windows CLI contract или точное преобразование HTTPS в `telemost` URI. Старый search snippet для `/join` описывал browser prompt, но live fetched URL перенаправил на `/call/join`; старый snippet не использован как актуальное доказательство API.

[Официальная MSI инструкция](https://yandex.ru/support/yandex-360/business/admin/en/telemost-msi) описывает Windows64-bit установку через MSI/EXE, включая per-user/all-users варианты. Это подтверждает наличие такого способа доставки, но не доказывает, что каждый EXE install имеет package identity или HTTPS AppUriHandler. Installer не скачивался и не запускался.

[Официальная Telemost API документация просмотра конференции](https://yandex.ru/dev/telemost/doc/ru/conferences/conference-read) описывает join URL и отдельно SIP-реквизиты. Чтение документации не сопровождалось API запросом к конференции, OAuth либо созданием встречи. SIP не является Windows desktop handoff substitute. В ограниченном поиске первичных Yandex страниц по `telemost://`, `yandextelemost:` и `conf-url` не найден публичный Windows URI grammar/CLI contract; это отсутствие найденного подтверждения, а не утверждение, что документа нигде нет.

### 3.2. Microsoft: границы трёх способов активации

| Способ | Что документировано | Вывод для этой установки |
| --- | --- | --- |
| `Launcher::QueryUriSupportAsync`/`LaunchUriAsync` без explicit package |Query проверяет доступность приложения для URI; Launch запускает связанную с scheme default app. Desktop apps тоже учитываются. [QueryUriSupportAsync](https://learn.microsoft.com/en-us/uwp/api/windows.system.launcher.queryurisupportasync?view=winrt-26100), [LaunchUriAsync](https://learn.microsoft.com/en-us/uwp/api/windows.system.launcher.launchuriasync?view=winrt-26100) |HTTPS availability не идентифицирует Телемост; в metadata HTTPS UserChoice указывает Edge. Browser-first flow не становится client-directed handoff от BOOL=true. |
| `LauncherOptions.TargetApplicationPackageFamilyName` и package-specific Query |Это PFN реального app package; есть Query overload с PFN. Свойство не обещает обработку произвольной ссылки любым EXE. [TargetApplicationPackageFamilyName](https://learn.microsoft.com/en-us/uwp/api/windows.system.launcheroptions.targetapplicationpackagefamilyname?view=winrt-26100) |Для найденного клиента PFN не установлен. Нельзя подставить `YandexTelemost`, certificate CN, MSI product GUID, ProgID `telemost` или EXE path. |
| `IApplicationActivationManager::ActivateForProtocol` |Активирует указанное Windows Store application для Windows.Protocol contract; appUserModelId — AUMID такого приложения, Shell item преобразуется в URI. [ActivateForProtocol](https://learn.microsoft.com/en-us/windows/win32/api/shobjidl_core/nf-shobjidl_core-iapplicationactivationmanager-activateforprotocol) |Подходящего packaged AUMID/contract не найдено. Win32 shortcut AUMID, даже если позднее обнаружится, сам по себе не докажет этот contract. |

Для native обработки **HTTPS** вместо браузера Microsoft описывает [Apps for Websites/AppUriHandlers](https://learn.microsoft.com/en-us/windows/apps/develop/launch/web-to-app-linking): нужна full/sparse package identity, manifest host registration, website association с PFN и actual activation handling. Наличие обычного `telemost` protocol key этого не доказывает. Ни GRAF, ни исследователь не могут за сторонний клиент создать package identity/manifest или provider website declaration. Это возможный путь только при обнаружении настоящей регистрации Телемоста, а не предложенная установка/обёртка.

## 4. Installed metadata: точное наблюдение в VM

Чтение выполнено `prlctl exec` в уже running VM `Windows 11`, только PowerShell `-NoProfile -NonInteractive`/registry/version/signature metadata. Экземпляр Telemost, ссылка и activation API не запускались. Не читались browser history, meeting MRU, command lines живых процессов, calendar content, cookies, credentials, user documents либо содержимое private profiles.

| Поле | Факт чтения |
| --- | --- |
| OS |Microsoft Windows11 Pro, `10.0.26200.9168`; WMI BuildNumber26200 |
| OS/process architecture |ARM64; PowerShell PrincipalIsSystem=true |
| Installed application |Uninstall DisplayName `Yandex Telemost`, DisplayVersion `2.42.4.9707`, Publisher `Yandex` |
| Uninstall source |`HKLM\Software\Microsoft\Windows\CurrentVersion\Uninstall\{587343C3-6DCC-5909-9018-E6430EB36FB7}` |
| InstallLocation |`C:\Program Files\Yandex\YandexTelemost\` |
| Loaded user Classes |Один загруженный `HKU\<user-SID>_Classes`; SID/имя пользователя не сохранены в отчёте |
| Protocol/class key |В этом hive `telemost`, default `Yandex Telemost`; **значение** `URL Protocol` существует и равно пустой строке, не отсутствует |
| Open command |`telemost\shell\open\command`: `"C:\Program Files\Yandex\YandexTelemost\YandexTelemost.exe" --conf-url="%1"` |
| Icon |`telemost\DefaultIcon`: тот же EXE, resource index−1 |
| Delegate/AUMID |`DelegateExecute` в прочитанных root/command отсутствует; `AppUserModelID` отсутствует в этих keys; `telemost\Application` не обнаружен этой адресной проверкой |
| HTTPS user association |В соответствующем loaded-user `UrlAssociations\https\UserChoice`, только поле ProgId: `MSEdgeHTM`. Hash/другие user values не читались |
| Appx/PFN discovery |`Get-AppxPackage -AllUsers`, фильтр Name содержит Telemost либо Publisher содержит YANDEX: `RelevantAppxCount=0`, `Packages=[]` |
| Executable version |FileVersion/ProductVersion `2.42.4.9707`, ProductName `Yandex Telemost`, CompanyName `Yandex`, OriginalFilename `YandexTelemost.exe` |
| Executable architecture |PE signature `0x00004550`, Machine `0x8664` — x64. Это x64 binary на ARM64 OS, не доказанный native ARM64 client |
| Signature |`Get-AuthenticodeSignature`: Status `Valid`, SignatureType `Authenticode`, signer CN/O `YANDEX LLC` |
| Signer certificate |Issuer `GlobalSign GCC R45 EV CodeSigning CA 2020`; thumbprint `52D76D99C3C46DCCD3810F7CCE9BC916003E639D`; NotBefore2025-02-20, NotAfter2028-02-21 |
| Timestamp signer |`Sectigo Public Time Stamping Signer R37` |

`Valid` — результат native signature check в этой VM, не независимая проверка online revocation policy, свежести версии или security всего приложения. Thumbprint — идентификатор наблюдаемого сертификата, **не предлагаемый вечный production pin**. Version/signature/registration могут измениться после обновления клиента.

SYSTEM HKCU относится не к интерактивному пользователю. Первичная проверка HKLM/SYSTEM HKCU не показала protocol key; последующее адресное чтение loaded-user Classes нашло его. `Get-StartApps` из SYSTEM не дал Telemost match, но это **не доказательство отсутствия AUMID у интерактивного пользователя**. Appx фильтр0 и отсутствие AppUserModelID в нескольких keys не исключают произвольно названный sparse package или shortcut property; они означают, что usable PFN/AUMID в данном ограниченном исследовании не установлен. Нельзя строить PFN/AUMID по имени EXE.

В registry metadata нет подтверждения, кто именно первоначально записал class или что он принимает HTTP/HTTPS кроме собственного scheme. Подписанный EXE и соответствующий install record подтверждают правдоподобность target identity, но command `%1` сам по себе не доказывает parser semantics `--conf-url` или успешное получение встречи клиентом.

При чтении возникали ошибки quoting/guest invocation; данные не выводились из failed calls. После перехода к короткому корректному UTF-16LE `-EncodedCommand` чтения завершились. VM/Parallels Tools не перезапускались, настройки не менялись; нет утверждения о недоступности handler по ошибке транспорта `prlctl`.

## 5. Точный кандидат: explicit Windows association, исходный HTTPS

Microsoft разрешает в `SHELLEXECUTEINFOW.lpClass` ProgID, protocol scheme либо class registry path; `SEE_MASK_CLASSNAME` выбирает этот class, вместо неявного выбора по расширению/scheme. Это документированный механизм Windows Shell, не `cmd.exe` и не собственное исполнение registry command: [SHELLEXECUTEINFOW, lpClass/fMask](https://learn.microsoft.com/en-us/windows/win32/api/shellapi/ns-shellapi-shellexecuteinfow).

Конфигурация кандидата для **будущей**, отдельно разрешённой проверки:

| Поле | Предложенное значение |
| --- | --- |
| API |`ShellExecuteExW`, корректный COM/apartment и lifetime owner |
| fMask |`SEE_MASK_CLASSNAME | SEE_MASK_FLAG_NO_UI`; не обходить security prompts/zone checks |
| lpClass |`L"telemost"`, взят из найденной registration, не из provider_family |
| lpVerb |`L"open"` |
| lpFile |Точная актуальная validated HTTPS target по разрешённому host/path; query/fragment сохранены, без переписывания на неизвестный scheme |
| lpParameters |`nullptr`: не составлять `--conf-url` самостоятельно |
| EXE path |Не hardcode; только разрешённая ОС association. Наблюдаемый путь служит evidence/preflight identity check, не launch instruction |

Предположение, требующее проверки: явный class сохранит HTTPS в `%1` наблюдаемой команды и клиент обработает его как meeting target, а не откроет браузер/домашнее окно/ошибку. Документация class selection и регистрация дают **обоснованного кандидата**, но не доказательство этого конкретного поведения Telemost.

Предлагаемый identity preflight — read-only Windows association query того же class/verb в **том же интерактивном user context**, затем проверка resolved executable/version/signature и bounded command-shape metadata. Microsoft документирует [AssocQueryStringW](https://learn.microsoft.com/en-us/windows/win32/api/shlwapi/nf-shlwapi-assocquerystringw) для association metadata. Такой query не запускался здесь как prototype; код/проверки основного агента не дублировались. Не разрешать unknown class/delegate, неожиданный publisher или неопределённый результат как отсутствие клиента. Нельзя вручную исполнить возвращённую команду.

Ни проверка class, ни подпись EXE не дают атомарного доказательства, что association не изменится между preflight и OS dispatch. Эту границу нужно явно определить в opener native gate; metadata snapshot не является anti-hijack capability или разрешением исполнять произвольную HKCU command. `QueryUriSupportAsync(HTTPS)` остаётся общей support проверкой, но не заменяет identity-specific evidence.

Microsoft возвращает у ShellExecuteEx BOOL и error, а process handle не гарантирован при existing-instance/delegated activation. Поэтому gate не должен считать отсутствие нового PID отказом или считать наличие PID доказательством принятия конкретной цели: [ShellExecuteExW](https://learn.microsoft.com/en-us/windows/win32/api/shellapi/nf-shellapi-shellexecuteexw), [SHELLEXECUTEINFOW, hProcess](https://learn.microsoft.com/en-us/windows/win32/api/shellapi/ns-shellapi-shellexecuteinfow). Для URI нельзя полагаться на SEE_MASK_NOASYNC как универсальное ожидание завершения; owner/COM lifetime и result semantics рассматриваются отдельно. Любой успешный OS dispatch остаётся только handoff, не доказательством присоединения, разрешений микрофона или начала capture.

## 6. Что именно ещё НЕ доказано

| Утверждение | Состояние |
| --- | --- |
| Телемост установлен, зарегистрированный class у loaded user и подписанный matching EXE есть |Подтверждено metadata reads, версия/сертификат указаны выше |
| HTTPS API Available направляет в Телемост |Не доказано; HTTPS UserChoice указывает Edge, API availability не сообщает client identity |
| Installed Телемост имеет usable PFN/AUMID/Windows.Protocol или appUriHandler |Не найдено; не угадывать и не объявлять универсальное отсутствие по SYSTEM StartApps |
| `telemost` scheme существует |Подтверждено registration; **grammar/path/query mapping scheme не установлен** |
| HTTPS→`telemost://...` преобразование официально поддерживается |Не доказано; ни команда `%1`, ни имя scheme не задают такого преобразования |
| Explicit class ShellExecuteEx передаёт исходный HTTPS в клиент, сохраняя значения |Конкретный candidate; activation не выполнялась, runtime результата нет |
| Клиент принимает HTTPS `--conf-url` и показывает именно эту цель |Не доказано; название argument не заменяет документацию/проверку parser |
| BOOL=true/PID гарантирует принятие встречи/неbrowser result |Не доказано; нельзя использовать для автоматического Record до принятого handoff gate |
| x64 client handoff проверен на физической x64 Windows / ARM64 native |Нет; только ARM64 VM metadata и x64 PE header, без запуска |
| Privacy, quote/query/fragment preservation, race/cancel semantics полностью приняты |Нет; требуется scoped native gate, existing validator/current checks сохраняются |

## 7. Минимальный необходимый native gate T119

Это предложение следующей проверки, **не выполненная проверка**. В данном раунде приложение, live meeting, audio/mic/camera и activation APIs запускать запрещено. Нельзя скрыто выполнить gate, прикрыв его словом «probe».

1. **Под тем же user/token/package context, что GRAF:** повторить effective class/verb/executable signature metadata; отдельно установить actual packaged identity/AppUriHandler, только если выбирается PFN путь. SYSTEM/HKU discovery не является runtime association selection интерактивной сессии. Различать missing, unknown/error и installed-but-unusable.
2. **Один class-directed dispatch, после отдельного разрешения запуска клиента:** проверять именно `ShellExecuteExW` + explicit `telemost` class + исходный HTTPS, без EXE invocation/custom URI. Нужна provider-confirmed не-живая тестовая цель либо специально контролируемый no-join fixture; случайный numeric meeting ID не гарантирует отсутствия живой встречи. Не сохранять реальную private target в research/logs. Без безопасной fixture/нового разрешения этот шаг остаётся blocked, не PASS.
3. **Подтвердить target identity и приём ссылки:** открывается установленный подписанный Telemost, не Edge/другой EXE/Store picker; цель принята клиентом, query/fragment/percent-encoded значения не потеряны и не стали arguments. Для уже работающего клиента проверить доставку в существующий instance, не требовать создания второго процесса. Не нажимать Join/Continue, не давать mic/camera доступ и не инициировать recording. При одной лишь домашней странице/client error/browser launch gate не пройден.
4. **Минимальные отрицательные случаи:** handler действительно отсутствует; class есть, EXE missing/неприемлемая подпись; package/class query error; dispatch False/cancel/exception; target неподдерживаемого host/path/port. Unknown не выдаёт «клиента нет», никакого автоматического второго browser launch/Store recommendation. Для recovery действуют явное согласие и новый existing resolver/current check.
5. **Сохранить existing lifecycle:** current fence непосредственно до OS dispatch; после dispatch ссылку не отозвать, stale completion не меняет новую сессию/не запускает Record. Runtime evidence хранит только обезличенные case IDs/identity/results, не private URL. Успешный OS handoff не означает joined/capture. Основной агент проверяет bridge/resolver implementation, здесь эта работа не переигрывается.

Если explicit-class HTTPS проваливается, остановить этот кандидат. Следующая развилка только по первичному подтверждению: официальный Telemost URI format для обнаруженного handler **либо** настоящая PFN+AUMID+manifest/provider association. Browser-first flow может оставаться честным browser-only/recovery по принятому contract, но не native-client substitute. Никакая новая custom conversion/CLI/package wrapper этим отчётом не разрешена.

## 8. Граница завершения

Применены `code-reviewer` для точных границ §10/review и `deep-research` для первичных Microsoft/Yandex источников, с отделением source facts, installed facts и engineering candidate. Lane: read-only technical investigation с единственным явно разрешённым ненормативным Markdown output. Не проводились builds/prototypes/runtime activation, не менялись installer/registry/defaults, не читались private URL/credentials, не изменялись markers/norms/source/Git/GitHub/API state и чужие документы.

**Исследование закрывает неизвестность наличия и имени installed Windows protocol handler. Оно не закрывает неизвестность exact HTTPS→client activation.** На сегодня достаточно точного candidate и перечисленного native gate; объявлять PFN решение, scheme conversion или Telemost handed_off уже доказанными нельзя.
