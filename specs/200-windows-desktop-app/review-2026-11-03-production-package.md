# F200: ограниченное requirements/gate review production MSIX 0.1.0.15

Дата: 2026-11-03.
Рабочий корень: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`.
HEAD по контексту исполнителя: `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`;
Git рецензентом не вызывался. Исходники привязаны SHA-256 ниже.

**FINAL: C0/H0, ограниченный installed PASS для обновления 0.1.0.14 → 0.1.0.15,
совпадения установленного payload с подписанным MSIX, сохранности наблюдаемых
метаданных пяти областей данных и инвентаризации доверия, а также самопроверки
backend установленного пакета. Основание — точные terminal receipts и документы
ниже; новых запусков рецензент не выполнял. Это не полная приёмка F200,
интерфейса, микрофона, реальной записи или публичного выпуска.**

Это существующий F200, high-risk-product, ограниченная проверка сборки и обновления пакета,
не публичный выпуск. Новые product edits и перепланирование не требуются.
Прежний shell-close GREEN/RED/restore/GREEN принят только в своих границах;
его derivative PE не является production payload для MSIX.

## Основание и inspected scope

Прочитаны относящиеся положения release-and-validation, product gates,
F200 plan, quickstart §8, FR-020, SC-008 и security CHK016/020:
подпись/архитектура/runtime dependencies должны быть проверены, обновление
сохраняет пользовательские записи/очередь и профиль, а package evidence
не заменяет clean-image lifecycle, hardware или release readiness.
Общий requirements marker 477/0 не пересчитывался и не переодобрялся.

Manifest уже содержит Name=com.graf.desktop, Publisher=CN=GRAF,
Version=0.1.0.15, Application Id=GRAF, Executable=GrafWindowsApp.exe.
Установленная 0.1.0.14 / Ok подтверждена terminal preflight/inspection ниже;
рецензент не делал собственной VM-инспекции.

Рассмотрены только packaging project/native project, manifest, существующий
dev-sign helper, static smoke и связанные инструкции. Код приложения
не переаудировался: текущий AppMain совпал с принятым shell-close исправлением.

## Конкретные ограничения существующих helpers

1. **build-dev-signed-package.ps1 несовместим с noexport/noimport/no-new-trust.**
   Он выбирает ключ только по Subject/HasPrivateKey и максимальному NotAfter;
   при отсутствии создаёт New-SelfSignedCertificate (строки 50–62), затем
   безусловно выполняет Export-Certificate и Export-PfxCertificate (65–67).
   SkipTrust пропускает лишь Import-Certificate (69–73), но не создание и
   экспорт. Поэтому запуск этого helper, включая -SkipTrust, не соответствует
   данному плану. Исправлять helper ради этого прохода не требуется: допустим
   прямой SignTool с точным существующим сертификатом из store и private key
   внутри store, без /f PFX, создания/экспорта/импорта и timestamp service.
   Это ограничение применимости helper, а не finding о выбранной пользователем
   прямой подписи из хранилища.

2. **Static smoke необходим, но не проверяет все pins нового пакета.**
   validate-package-smoke.ps1 с реальным -Package проверяет имя приложения,
   executable, capabilities, русский язык, отсутствие запрещённых payload
   entries/managed projection и Valid Authenticode. Он отдельно не закрепляет
   Version=0.1.0.15, Publisher, signer thumbprint, architecture, зависимости
   или payload EXE hash. Эти сравнения должны быть в package receipt.
   Запуск без -Package печатает pending и возвращает 0; это не package PASS.

3. **Standalone EXE и packaged EXE имеют разные build properties.**
   GrafWindowsApp.vcxproj по умолчанию WindowsPackageType=None; .wapproj
   передаёт GrafWindowsPackageType=MSIX и отключает встроенную подпись для
   последующей явной подписи. Для MSIX нужен именно packaging build graph.
   Простой повторный линк unpackaged shell-close/production EXE не доказывает
   правильный runtime mode пакета. AppInstaller.xml остаётся отдельным
   сетевым каналом с Version=0.1.0.0; он не является входом локального
   обновления выбранным MSIX и в этом проходе не публикуется/не изменяется.

Эти ограничения устранимы выбором и проверкой уже заявленной процедуры;
подтверждённого продуктового C/H-дефекта этот requirements review не устанавливает.

## Условия до установки

**Точные оригинальные входы.** Новый snapshot из 223 текущих production inputs
должен совпасть с manifest до/после build. В нём оригинальный vcxproj с обычным
ClCompile AppMain.cpp, production entrypoint и полный AppMain SHA-256
`b7a2ab3ec2128636c0b953a1c79e8a29f74f3b408734853b8bb25ec2ed34927e`.
Наличие тестовых файлов среди 223 inputs допустимо; их forced inclusion и
исполнение в production запрещены. Нужно подтвердить отсутствие fixture /FI
в фактической компиляции, а не только отсутствие XML-подстановки в проекте.
Удаляется только точный собственный AppMain.obj перед свежей компиляцией;
build receipt связывает source/project/toolchain/runtime/AEC provenance,
факт AppMain compile, новый object и PE. Нельзя копировать производный PE
из предыдущего сценария или принимать один MSBuild exit 0.

**Packaging и payload.** Release/x64 .wapproj должен собрать production graph
с GrafWindowsPackageType=MSIX. Упакованный EXE должен совпасть с PE именно
этого packaged build, а runtime DLL/dependency metadata — с его входами.
Зафиксировать реальный AppxManifest.xml внутри MSIX: Name/Publisher/version,
processor architecture, Application Id, executable, capabilities и зависимости
Windows App SDK/VCLibs. Проверить необходимые framework packages уже на хосте
и соответствие целевой архитектуре. Quickstart prose не заменяет фактический
package manifest: исходный manifest сейчас объявляет VCLibs dependency.
Отсутствующая обязательная зависимость останавливает установку в этом срезе;
её установка/ремонт не следуют автоматически из данного review.

**Точный существующий signer.** До подписи закрепить store location и thumbprint
уже существующего CN=GRAF: HasPrivateKey, действующий срок, code-signing EKU,
совпадение с Publisher и уже работающая цепочка доверия. Один CN недостаточен
для выбора ключа. Если ключ отсутствует/непригоден или Valid не получается
на имеющемся доверии, остановиться без создания ключа, экспорта, импорта и
добавления доверия. После подписи требуются MSIX SHA-256, Valid signature,
тот же signer thumbprint и успешный smoke для именно этого файла. Инвентаризация
соответствующего signer/trust до/после — только чтение; новый TLS trust test
или подтверждение нового сертификата не нужны.

**Identity и данные.** Перед изменением установленного состояния сопоставить
реальный installed package 0.1.0.14 с кандидатом 0.1.0.15: Name, Publisher,
PublisherId/PackageFamilyName, architecture и Application Id. Не подменять
обновление соседней identity или uninstall/reinstall. Предварительно закрепить
только безопасные metadata/digests нужных user-data scopes (local custody,
очередь, существующий профиль/настройки), без чтения/публикации их содержимого,
cookies, ключей или private filenames. Предусмотреть сохранение прежних данных
при отказе update; отсутствие данных не объявлять, если baseline не проверен.
Фактический rollback остаётся отдельной приёмкой, не выполняется автоматически.

**Чистая остановка.** Непосредственно перед update нет capture, starting,
finalizing, незавершённых изменений/очередного cleanup и живых GRAF/owned child
процессов. Основание — штатное завершение и свежий preflight, а не убийство
процесса ради снятия блокировки или один старый shell-close receipt.
Установка — обновление точной existing identity из проверенного локального
MSIX, без Remove/Reset-AppxPackage, force shutdown, удаления профиля,
пользовательских записей и загрузки AppInstaller URL. Package activation,
автозапись, web/account и UI-проверка не входят в этот шаг установки.

## Условия после update и пределы вывода

Точная terminal update receipt без ошибки; installed Version=0.1.0.15,
Status=Ok, прежний PackageFamilyName/identity, installed EXE и runtime payload
соответствуют проверенному signed MSIX. Данные/профиль/очередь по исходному
baseline сохранены, signer/trust inventory неизменен, процессов GRAF нет.
Не ослаблять ошибку установки до PASS по факту наличия пакета. Если операция
не завершилась, installed state нужно установить чтением; uninstall/reset
не является автоматической процедурой восстановления.

Такое свидетельство принимает локальную сборку/подпись/обновление версии,
но не first launch, пользовательские сценарии, physical x64, реальный звук,
hardware, UI/accessibility, missing-runtime repair, clean-image lifecycle,
rollback или публичный выпуск. T108/T109 и остальные задачи не закрываются.
Проверки общего release CI/публикации не добавляются к этому эксперименту;
их отсутствие продолжает запрещать утверждение о готовом публичном выпуске.

## Привязка прочитанных файлов

| Файл | SHA-256 |
| --- | --- |
| RecApp/AppMain.cpp | `b7a2ab3ec2128636c0b953a1c79e8a29f74f3b408734853b8bb25ec2ed34927e` |
| RecApp/GrafWindowsApp.vcxproj | `84656a004e791c2727184615e767c0ba14846f14314edfcbd2dee825ac91ff5a` |
| Installer/Package.appxmanifest | `15190c49a46f0245e8a48ef234582c778e3ec38517094f3996b408bb03950572` |
| Installer/GrafWindows.Package.wapproj | `9ad98a78e026e546b7e21b2c9f9d083f7e6ee8f988181a4b091bf7eed813f486` |
| scripts/build-dev-signed-package.ps1 | `9d644ef02a46d97d112b59a4fdf06fdceb3d99abdc46c70e868aa3fcfde032ee` |
| scripts/validate-package-smoke.ps1 | `c2df99be7d65d279c967c8b0ee8c5b2d35dd63497389e99783ec62521543d130` |
| Installer/AppInstaller.xml | `a6749bc3a01ed4d297b9a06d87277932f5e7787738cfcac873e6a4b930522e07` |

Все пути таблицы относительны apps/windows в указанном checkout.

## Повторное независимое PREINSTALL review: production-package-9rjper_d

Stage:
`/Users/yshishenya/Documents/graf-f200-public458.po8CtB/production-package-9rjper_d`.
Рассмотрены Preflight.ps1, Build-Production.ps1, Inspect-Candidate.ps1,
Data-Inventory.inc.ps1, Install.ps1 и точные terminal receipts/logs. Новые
запуски не выполнялись. install-result.json на момент сверки отсутствует.

Первые две wrapper attempts остаются FAIL и не выдаются за MSBuild runs:
build-result.json остановился в helper selftest из-за пустого Path при
потерянном PSScriptRoot; retry-build-result.json — на file ExecutionPolicy.
Обе квитанции terminal, без build_exit. Третий Build-Production использует
реальный packaging Rebuild и не заявляет свежий selftest. В рассмотренных
скриптах нет изменения ExecutionPolicy; выполнение static smoke через
ScriptBlock не изменяет сам helper, а его реальные проверки/исключения
сохраняются. Предыдущие неудачи не подменены успешной квитанцией.

unchanged-helper-proof.json связан с t097-current-package.gryT9X.
Хеш прежнего source.sha256 совпал с 0fc0d3c… из proof; текущие два helper
совпали с закреплёнными хешами. Хеш прежнего validator-tests.log совпал с
654ebe9f…; UTF-16 журнал содержит 6/6 signature, 2/2 native payload и 6/6
language PASS. Это повторное использование исторических проверок неизменённых
helpers, не их новое исполнение. Свежий package-smoke.log отдельно подтверждает
проверку именно текущего подписанного MSIX, signatureStatus=Valid.

### Принятые build/package/signature свидетельства

Все 223 исходника source.json повторно сопоставлены с текущим checkout —
совпали. Source manifest SHA-256:
`d96f0d091b65969dafd2416e53044c59697631d03c1566028424f13dbc62e75c`.
source-identity закрепляет полный AppMain b7a2… и оригинальный project.
Build-Production проверяет manifest pin, все входы до/после, пустые CL/_CL_,
отсутствие ForcedIncludeFiles/fixture project и вызывает .wapproj /t:Rebuild
Release/x64. Изолированный package output и свежие AppMain.obj/EXE проверяются
по времени. В build.log есть AppMain.cpp и Generating code.

production-build-result.json: terminal=true, production_build=true,
build_exit=0, pre_source=post_source=223, failure отсутствует;
installed_exe_unchanged=true. Production PE и payload EXE:
`e6094e4de8b919ba94db652eae4f11ef9762c89d4d0b16f23e19f9342bfa02c5`.
Подписанный MSIX:
`7e737dcf969846bde70a36c3be2108696a6ea2b69fe935433271e79fe2d44a08`.
Файл MSIX независимо хеширован рецензентом; хеш совпал. Независимо прочитаны
его manifest, все 15 EXE/DLL, PE machine=0x8664 и отсутствие четырёх fixture
markers в UTF-8/UTF-16 представлениях. Все 15 payload hashes совпали с inspection.
Это не запуск packaged EXE и не first-launch acceptance.

Подпись выполнена SignTool /fd SHA256 /sha1 с CurrentUser My, без PFX,
New-SelfSignedCertificate, import/export или timestamp authority. Точный signer:
`816CC8B4EB216A0755BFB118992BB594AF51BF6C`.
Preflight проверяет CN=GRAF, HasPrivateKey, NotBefore/NotAfter, code-signing EKU
и наличие этого же сертификата в LocalMachine TrustedPeople. Signature Valid
и signer pin подтверждены build и повторной inspection; sign.log подтверждает
успешное подписание. Нативная Authenticode-проверка самим рецензентом на Mac
не повторялась; приняты Windows receipts и проверенный путь их получения.

Trust inventory до/после build и inspection совпадает:
`fa77c88ed61577b5f53b2fb56d58af476ad6602722aab8fd2ea9aa04418cf541`.
Это digest пяти перечисленных в процедуре stores: CurrentUser Root/CA/
TrustedPeople/My и LocalMachine TrustedPeople. Не заявляется новый тест TLS
или полный аудит всех machine stores. Изменений доверия в прочитанных скриптах нет.

### Terminal inspection и сохранность данных

inspection-result.json завершён без failure, inspection_only=true,
observed_version=0.1.0.14, observed_status=Ok. Процедура перед этим проверила
PFN com.graf.desktop_jqvfym1syd7bp, x64, Publisher CN=GRAF, Application Id=GRAF,
прежний installed EXE 6e162695… и отсутствие GRAF/probe/build/owned browser.
Candidate manifest независимо подтверждает те же Name/Publisher/Application,
Version=0.1.0.15 и ProcessorArchitecture=x64.

Фактические зависимости и уже доступные подходящие frameworks:

| Dependency | Minimum | Installed suitable |
| --- | --- | --- |
| Microsoft.VCLibs.140.00.UWPDesktop | 14.0.30035.0 | 14.0.33728.0 X64 |
| Microsoft.WindowsAppRuntime.2 | 2.4.0.0 | 2.5.1.0 X64 |

Совпадение Publisher/min-version/architecture проверяется снова перед установкой.
Наличие Bootstrap.dll среди payload само по себе не означает unpackaged build:
проверенный вход — .wapproj с packaged properties; его использование в runtime
этим статическим проходом не принимается.

Inspection сохранил hash compiler command tlog
`3cc20edd4d24e897becb376cd03d7e7297c2f0ed7c8393731a992ce81b7eceeb`.
Прочитанная проверка требует APPMAIN.CPP и отклоняет известные fixture includes/
test macro; оригинальный project и compiler env проверены build-процедурой.
Сам raw гостевой tlog рецензенту отдельным файлом не предоставлен и напрямую
не прочитан: утверждение об отсутствии fixture в command опирается на эту
inspection и inspected script, дополнительно на production inputs/PE markers.

Metadata helper открывает файлы через CreateFileW с FILE_READ_ATTRIBUTES=0x80,
OPEN_EXISTING, BACKUP_SEMANTICS|OPEN_REPARSE_POINT; reparse points отклоняются.
Он не читает contents, ключи или cookies. Относительные имена участвуют только
во внутреннем digest; наружу записываются scope labels, exists/counts/bytes и
metadata_sha256 по file IDs/stamps/attributes. Проверяются global GRAF,
package cached GRAF, LocalState, Settings и RoamingState. Preview terminal
содержит существующие непустые данные; это не случай пустого профиля.

Ограничение: равенство metadata digest не доказывает побайтовую идентичность
содержимого или семантику cookies/очереди. Для данного update без запуска
приложения это допустимая проверка сохранности наблюдаемых metadata. Нельзя
после неё писать «все данные побайтово проверены». В случае изменения metadata
Install остаётся FAIL, даже если это окажется штатное изменение Windows.

### Вывод по точному Install.ps1

GO относится к SHA-256
`170fb99390c220492a7fceec0ece58637af8821992a5ae74ce941e38e5f937a7`.
Сценарий повторяет build/source/package/signature/trust/identity/framework/
compiler checks, снимает свежий metadata baseline и непосредственно перед
операцией повторяет No-Owned-Processes. Единственная deployment операция —
Add-AppxPackage -Path точного локального MSIX. Нет force shutdown, uninstall,
reset, загрузки dependencies/AppInstaller, запуска продукта или trust/key writes.

После операции нужны правильные version/status/PFN/Publisher, hashes всех
15 установленных EXE/DLL, равенство metadata before/after, неизменный trust
digest и отсутствие процессов. При любой ошибке сохраняется failure и
наблюдаемая версия; одно installed=true не означает успешный postflight.
До такой terminal квитанции installed update не принят.

Сценарий запускается одним владельцем. Прежний P2 риска перезаписи квитанции
при повторе исправлен до первой установки: единственный INSTALL_STAGE_USED
перенесён перед function Trust-Inventory и вне внешнего try/finally. Повтор
при существующей квитанции теперь бросает исключение до входа в finally и
не выполняет Set-Content install-result.json. Это guard последовательного
повтора, не механизм блокировки параллельных запусков; single-owner сохраняется.

### Узкое delta-review P2 до первой установки

Прежний принятый Install.ps1 имел SHA-256
`a0290836a372497c5ba996475ab3a3f1403723809977b90b0423aa4bbeb126ab`.
Новый SHA-256:
`170fb99390c220492a7fceec0ece58637af8821992a5ae74ce941e38e5f937a7`.
Обратный перенос guard в памяти воспроизвёл точный прежний хеш. Иных
изменений Install нет. 223 inputs, build/signature/helper proofs и package
повторно не аудировались; ранее принятый вывод сохраняется. P2 закрыт,
PREINSTALL GO остаётся в силе для нового pin. install-result.json на момент
этой сверки отсутствовал; installation и postflight ещё не выполнены.

В подготовленном Verify-Installed-Backend.ps1 guard BACKEND_STAGE_USED также
расположен до functions/try, поэтому последовательный повтор не перезаписывает
backend-result.json через finally. SHA-256 сценария:
`dc292b1fcfa8a9dfaa8f4b0240e2109c72054f3ec416680b386884c53b6f42bb`.
backend-result.json отсутствовал. Это проверка подготовленного исходника,
не принятие результата backend execution.

Для уточнения границы прочитан существующий ранний --verify-audio-backend
в production wWinMain и verifyAudioBackendForInstalledPackage: при точном
аргументе возвращается до Application::Start/обычного startup. Он требует
package identity и создаёт реальный GrafAEC3WebRtcAdapter; initialize использует
нулевые 480-frame массивы, ProcessReverseStream/ProcessStream, без открытия
устройств, пользовательского профиля или WebView. Это вычислительная проверка
backend, не аудиозахват/UI/hardware acceptance. Ветка packaged launch arguments
также возвращает до обычной активации приложения.

Подготовленный backend runner допускает старт только после успешной update
receipt, сверяет version/PFN/exact installed EXE и trust digest, передаёт один
--verify-audio-backend, требует OS exit=73, повторно проверяет EXE/trust;
timeout/forced cleanup остаются FAIL. Сам runner рецензентом не исполнялся;
его source рассмотрен лишь для guard и заявленной границы без UI/device.

### Точные артефакты PREINSTALL review

| Артефакт stage | SHA-256 |
| --- | --- |
| preflight.json | `7e53ffa2704abfe4084d84b5c6b769bed7fd671ed157c160d8e4a17974bfaa76` |
| build-result.json (отклонён) | `915e0fe58f471221d1bebd9039af04f4c0169c1cb25925e22b693d2625c4e587` |
| retry-build-result.json (отклонён) | `d4d9b5ecf51a6dfebe0161633a439b91f0dbd19df26dc75c463d612f8efb1b00` |
| production-build-result.json | `f1a0e239dda0ad22ff95b1f49f75015c7fbccb97648ef79227e596955c8738c2` |
| inspection-result.json | `672127b8ceab384b5b8c9b30cc20b87ecdcdea5b80a43728890719563eaafeb9` |
| unchanged-helper-proof.json | `16e1159c0139f24c74633554bda175ed46c857ba6eafac861be098f9dad73895` |
| package-smoke.log | `b15d516eb7ab6a93d55583a4e724db46156cb8b284343134d68d8d4cd818942c` |
| sign.log | `a989c5b4299ff37b28799e5513cfbf8f7fa1d8d3ecd930c0a8d0bcc58f3b642d` |
| Install.ps1 (после исправления P2) | `170fb99390c220492a7fceec0ece58637af8821992a5ae74ce941e38e5f937a7` |
| Verify-Installed-Backend.ps1 (подготовлен, не исполнен) | `dc292b1fcfa8a9dfaa8f4b0240e2109c72054f3ec416680b386884c53b6f42bb` |
| Inspect-Candidate.ps1 | `81682bc422c9480e238e61196e97b61d79587feab71df4c6f21ff055a5ae2ee3` |
| Build-Production.ps1 | `9ab4ab24044f3ffa4e11438b8c49ea51548d4b5850c1d9e2de15429b03b09ace` |
| Data-Inventory.inc.ps1 | `820ff8077e0c796a805cda592cc278382d9620ebae919e54fd9650a58cdd7e6d` |

Исторический итог до установки: PREINSTALL GO, C0/H0 для точного локального пакета и первого запуска
проверенного Install.ps1 с новым SHA-256; P2 перезаписи квитанции закрыт
узкой проверкой переноса guard. Это не installed PASS, не backend runtime PASS,
не first launch или полная приёмка F200.
Написан только этот отчёт. Код, spec/tasks/checklists, Git, VM, сертификаты,
пакеты и userdata рецензентом не изменялись; тесты/сборки не запускались.

## Финальное ограниченное ревью установки, backend и postflight

Сверены новые install-result.json, backend-result.json, postflight.json,
оба user-data JSON, portable-suite.log и обновлённый
validation-2026-11-03-production-package.md. Прочитаны Postflight.ps1 и
Cleanup-Package-Output.ps1; повторно проверены pins Install.ps1 и
Verify-Installed-Backend.ps1. Исполненные production-build-result.json,
inspection-result.json и source.json сохранили ранее принятые хеши.
Повторный аудит 223 исходников, Git, VM и новые тесты не выполнялись.
Предыдущие разделы PREINSTALL и отсутствие receipts описывают момент
предыдущих сверок; ожидания установки и backend этим разделом сняты.

### Установка и сохранность наблюдаемого состояния

install-result.json: terminal=true, failure отсутствует, installed=true,
deployment_returned=true, installed_version=observed_version=0.1.0.15,
installed_status=observed_status=Ok. PackageFamilyName остался
com.graf.desktop_jqvfym1syd7bp. Проверены 15 установленных EXE/DLL;
payload_files_verified=15, package_sha256 и installed_exe_sha256 совпадают
с ранее независимо проверенными MSIX и production PE:

- MSIX: `7e737dcf969846bde70a36c3be2108696a6ea2b69fe935433271e79fe2d44a08`.
- Установленный EXE: `e6094e4de8b919ba94db652eae4f11ef9762c89d4d0b16f23e19f9342bfa02c5`.

Квитанция связывает source_count=223, прежний compiler command digest и
test_forced_include_absent=true. Отсутствие force/reset/uninstall, нового
доверия и экспорта ключа согласуется с ранее прочитанным точным Install.ps1;
это не вывод только из декларативных false-полей результата.

Независимое сравнение JSON подтвердило полное равенство пяти metadata scopes
в install before/after, отдельных user-data-before.json/user-data-after.json
и postflight после backend. Baseline непустой: global GRAF — 786 файлов,
195 каталогов, 79 775 375 байт; LocalState — 2 файла / 4 269 байт;
Settings — 4 файла / 16 384 байта. Package cached GRAF не существовал и
остался отсутствующим; RoamingState сохранил существующий пустой каталог.
Принимается сохранность наблюдаемых метаданных, а не побайтовое сравнение
содержимого, работоспособность очереди или повторный вход в аккаунт.

Trust digest до/после установки, после backend и в postflight один:
`fa77c88ed61577b5f53b2fb56d58af476ad6602722aab8fd2ea9aa04418cf541`.
Вывод ограничен пятью перечисленными ранее хранилищами сертификатов.

### Самопроверка установленного backend и итоговая остановка

backend-result.json: terminal=true, failure/forced_cleanup отсутствуют,
exit_code=73, backend_selfcheck_pass=true, installed_backend_verified=true,
app_stopped=true. EXE hash совпал с installation и postflight. Прочитанный
runner получает путь через Get-AppxPackage.InstallLocation, проверяет его
identity/hash и запускает именно этот EXE с --verify-audio-backend; отдельный
тестовый или unpackaged EXE не подменяет результат. Ранее проверенная ранняя
production-ветка создаёт настоящий AEC backend на синтетических массивах
до обычного UI/startup, без открытия аудиоустройства. Это installed backend
PASS, не микрофонная или аппаратная приёмка качества AEC.

postflight.json: terminal=true, failure отсутствует, 0.1.0.15 / Ok,
тот же installed EXE, user_metadata_unchanged=true, прежний trust digest,
app_processes=0, owned_browser_processes=0. Читаемый Postflight.ps1 требует
успешных install/backend receipts и выполняет реальные сравнения; их ошибка
не превращается в PASS через finally. Старый конкретный localhost certificate
отсутствует в CurrentUser Root/CA/My (old_localhost_certificate_present=0).
source_count=223 получен после проверки гостевых входов по source.json.
ОС — build 26300 / Arm64: x64-пакет исполнялся через эмуляцию, не на
физическом Windows x64. Никакой новый trust test для этого вывода не требуется.

### Переносимые тесты и согласованность документов

portable-suite.log содержит успешные configure/build и CTest EXIT 0:
100% tests passed, 0 tests failed out of 48. Это свежие 48/48 переносимых
проверок на macOS / AppleClang 21, не Windows-only/hardware ветви.
Указанный журналом временный CMake-каталог при чтении уже отсутствовал.
Равенство всех 223 inputs до/после этого переносимого прогона заявлено
исполнителем и validation; отдельного portable before/after manifest в stage
нет, поэтому оно не представляется как повторная независимая сверка
рецензентом каждого файла в оба момента. Гостевая проверка 223 inputs
отдельно подтверждена terminal build/install/postflight в своих границах.

Все 12 хешей терминальной таблицы validation независимо вычислены по файлам
stage и совпали. Текст о фактической установке, backend, metadata/trust и
пределах приёмки согласуется с receipts. Прежняя формулировка «пока не
принимается по одному build receipt» находится в разделе подготовки и
не отменяет последующий terminal раздел. Последняя существующая запись
release_notes_windows_indicator_exit_20261103 в changes/unreleased/F200.yaml
согласуется с установленным MSIX и сохраняет границу «не публичный выпуск».
Общий marker 477/0, задачи и перечни качества не пересчитывались и не
переодобрялись.

### Точные новые свидетельства

| Артефакт | SHA-256 |
| --- | --- |
| install-result.json | `cbffc4a32b1333b987ca416cee29d7371c9017a373802bd5ee75651acae8286d` |
| user-data-before.json | `a5eee8143474dedea4e7095dd02aecf3b62aaa2b3d7613b13bc0da5059783381` |
| user-data-after.json | `a5eee8143474dedea4e7095dd02aecf3b62aaa2b3d7613b13bc0da5059783381` |
| backend-result.json | `5c60ae193fd4c469e6edef4fc59ad17bbd0ccc629c1de0aa0a068e3d0432990e` |
| postflight.json | `4182ed8fd94d0c31eb1140d17d2dddaf0543aaed427e85f61bbd87272ea34b90` |
| portable-suite.log | `db8fedff9621cca39f57fb828333c25b983db11004efe0ec096d5b517b1e83df` |
| Postflight.ps1 | `856c86ed92bd899793bee00c9499937cbda6f4537c6c72e1bca3896b90ef5560` |
| Cleanup-Package-Output.ps1 | `a2160405646e1cd24fb164535caa932f980a6af6cc2e3ae5c8d0afae03276e2e` |
| validation-2026-11-03-production-package.md (checkout) | `0286fb04bce40c0ed82c07fb306f71cf8f340bb4240b6f7545f305b53599562c` |

### Финальный вывод и граница очистки

**C0/H0. Ограниченный installed PASS принят по точным receipts:** обычный
подписанный production MSIX обновил существующую identity до 0.1.0.15 / Ok;
установленный payload совпал, наблюдаемые metadata/trust сохранились,
установленный backend прошёл раннюю самопроверку, процессы завершены.
Прежний P2 guard остаётся закрытым на неизменном Install pin
170fb99390c220492a7fceec0ece58637af8821992a5ae74ce941e38e5f937a7.
Конкретных C/H-блокеров или оснований для нового тестового запуска в этом
срезе не найдено. Это не закрытие T097/T108/T109, всей F200, first UI launch,
микрофона, реального захвата, физического x64, rollback или выпуска.

Сохранённый финальный MSIX, manifests/logs/receipts и этот отчёт достаточны
для сохранения привязки после заявленной очистки собственного host source
snapshot и точного уникального Windows package output. Прочитанный cleanup
ограничивает output родителем TEMP и уникальным именем из build receipt,
отклоняет reparse points, сверяет единственный собственный MSIX и сохранённый
артефакт, не удаляет active Windows base/installed package. Очистка ещё не
считается выполненной: рецензент её не запускал и terminal cleanup receipt
не принимал. Исходники других проверок и активная Windows base вне этой
границы. Изменён только настоящий отчёт; код, документы исполнителя,
tasks/checklists, Git, VM и установленное состояние не изменялись.
