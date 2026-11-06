# F200: обычная сборка и пакет Windows 0.1.0.15

Дата: 2026-11-03. Существующий high-risk-product F200, подготовка
установленного MSIX для T097/T108 и общей приёмки. Это локальная проверка
в Parallels на ARM Mac с Windows x64 emulation, не публичный выпуск.

Рабочая копия `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`,
ветка `codex/200-windows-followup`, HEAD
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`; проверяется незакоммиченный снимок.
Manifest уже содержал версию 0.1.0.15; в этом проходе его не меняли.

## Обычная сборка

Stage:
`/Users/yshishenya/Documents/graf-f200-public458.po8CtB/production-package-9rjper_d`.
Заморожены 223 текущих Windows input files. AppMain SHA-256
`b7a2ab3ec2128636c0b953a1c79e8a29f74f3b408734853b8bb25ec2ed34927e`
содержит исправление времени жизни индикатора из shell-close проверки.
Это оригинальный AppMain и оригинальный project, без test derivative.

Windows base `C:\Temp\graf-settings-chain-li1qcg1c` переведена с принятой
shell-close derivative на оригиналы только двух файлов: AppMain.cpp и
GrafWindowsApp.vcxproj. Остальные 221 input совпали. Принудительно удалён
только принадлежащий этой временной сборке AppMain.obj; .wapproj Rebuild
выполнил обычный packaged MSIX build graph с GrafWindowsPackageType=MSIX.
Все 223 source hashes проверены до/после; object/PE свежие.

Фактический CL.command.1.tlog проверен: AppMain компилировался без fixture
forced include и тестового finalize macro. Проверены исходный project и
отсутствие известных fixture-маркеров в PE. Статический разбор PE показал
x64/0x8664; Bootstrap DLL не импортируется ни обычной, ни delayed таблицей.
Наличие SDK DLL в архиве само по себе не означает её импорт.

## Подпись и состав

Использован только существующий CurrentUser/My code-signing сертификат
CN=GRAF, thumbprint `816CC8B4EB216A0755BFB118992BB594AF51BF6C`:
проверены HasPrivateKey, срок, EKU и существующий LocalMachine/TrustedPeople.
SignTool подписал пакет ключом из хранилища по точному thumbprint.
Новый ключ не создавался, экспорт PFX/ключа и import/trust не выполнялись,
внешний timestamp service не использовался. До/после build/sign совпал digest
инвентаризации CurrentUser Root/CA/TrustedPeople/My и LocalMachine TrustedPeople.
Не запускался helper build-dev-signed-package.ps1: он создаёт/экспортирует ключ.

Реальный подписанный MSIX прошёл validate-package-smoke.ps1 с -Package:
identity, entrypoint, русский язык, capabilities, отсутствие драйверов/служб/
elevation и managed WebView2 projection; Authenticode Valid, точный signer.
Отдельно закреплены версия 0.1.0.15, Publisher, x64, Application Id=GRAF,
EXE внутри MSIX и исходный PE. Не принимается запуск validator без -Package.

Из фактического AppxManifest.xml подтверждены зависимости и их наличие:
Microsoft.VCLibs.140.00.UWPDesktop >=14.0.30035.0, установлен x64 14.0.33728.0;
Microsoft.WindowsAppRuntime.2 >=2.4.0.0, установлен x64 2.5.1.0.
Framework install/repair в этом проходе не требуется и не выполнялся.

Пакет:
`GRAF-F200-0.1.0.15-development.msix`, 2 895 803 байта.
MSIX SHA-256:
`7e737dcf969846bde70a36c3be2108696a6ea2b69fe935433271e79fe2d44a08`.
Production/payload EXE SHA-256:
`e6094e4de8b919ba94db652eae4f11ef9762c89d4d0b16f23e19f9342bfa02c5`.

## Две неудачные попытки запускателя до MSBuild

Первый build-result.json — FAIL до MSBuild: вызванный как ScriptBlock helper
самопроверки потерял PSScriptRoot и не нашёл соседний validator.
Вторая retry-build-result.json — FAIL до MSBuild: прямой запуск файла .ps1
запрещён текущей Windows ExecutionPolicy. Политика не менялась, этот отказ
не объявлен успешной проверкой.

Оба package helper побайтово совпали с ранее проверенным stage
`t097-current-package.gryT9X`. unchanged-helper-proof.json связывает их SHA
с прежним source.sha256 и UTF-16 validator-tests.log: 6/6 simulated signature,
2/2 managed projection, 6/6 resource language. Это прежнее свидетельство
неизменённого helper, не заявление о новом прогоне selftests. Новый реальный
подписанный пакет отдельно прошёл действующий static smoke. Третья попытка
production-build-result.json успешно выполнила Rebuild/sign/smoke.

## Подготовка обновления и границы

До обновления installed 0.1.0.14 / Ok, EXE
`6e1626953fc7e409837d65bbdebd642d509e69569ae43545039826a433b72a48`.
Read-only inspection подтвердил исходную identity, новый package/dependencies,
compile command, payload и доступность безопасного metadata inventory.
Обновление пока не принимается по одному успешному build receipt.

Data inventory открывает файлы/каталоги только с FILE_READ_ATTRIBUTES,
фиксирует file identity, размер, creation/write stamps и attributes.
В отчёт идут лишь числа и общий digest по scopes GRAF, packaged GRAF cache,
LocalState, Settings, RoamingState. Содержимое записей, очередь/токены/cookies,
ключи и частные имена файлов не читаются и не публикуются. Это сравнение
метаданных, а не hash содержимого и не проверка входа/проигрывания записи.

Условия обновления: та же PackageFamilyName/Publisher/Application Id,
нет GRAF/capture/owned browser процессов; исходные metadata закреплены;
Add-AppxPackage без Remove/Reset/force shutdown. После нужен успешный terminal,
0.1.0.15 / Ok, соответствие всех EXE/DLL подписанному архиву, совпадение
userdata metadata и trust inventory. Rollback, repair и публикация не входят.

Полная приёмка T097/T108, реальные recording/paused/finalizing, UI/accessibility,
физический x64, 60 минут capture, auth/upload/delete, clean-image lifecycle,
внешняя доверенная подпись и выпуск остаются отдельными незавершёнными воротами.
AppInstaller.xml/feed не публиковался и не изменялся. Commit/push/PR/merge,
выпуск и рабочий сервер в этом проходе не менялись.

## Предварительное независимое ревью

Рецензент независимо хешировал подписанный MSIX и сверил все 15 EXE/DLL,
223 inputs, manifest/dependencies, source/project и inspection. Первичный
вывод PREINSTALL GO, C0/H0. Замечание P2 о возможной перезаписи install receipt
при ошибочном повторе устранено до первого запуска: guard перенесён из try
наружу, поэтому finally не может перезаписать существующий результат.
Текущий Install.ps1 SHA-256
`170fb99390c220492a7fceec0ece58637af8821992a5ae74ce941e38e5f937a7`.
Исполненные build scripts/receipts не переписывались.

## Фактическое обновление и проверка установленного EXE

После узкого повторного review guard получен PREINSTALL GO для точного
Install.ps1. Первый запуск завершился успешно: Add-AppxPackage вернулся
без ошибки, установлен 0.1.0.15 / Ok с прежней PackageFamilyName.
Все 15 EXE/DLL внутри установленного пакета совпали с подписанным MSIX;
исходные 223 inputs и actual compile tlog повторно проверены. Не использованы
force shutdown, Remove/Reset, uninstall/reinstall, новый сертификат или ключ.

Все пять user-data scopes совпали по существованию, file/directory counts,
размерам и digest метаданных до/после. Прежний GRAF scope содержал 786 файлов,
195 каталогов, 79 775 375 байт; LocalState 2 файла/4 269 байт, Settings
4 файла/16 384 байта. Не существовавший packaged GRAF cache остался
отсутствующим. Ни отсутствие исходных данных, ни побайтовая неизменность
их содержимого не предполагаются: это именно metadata comparison.
Trust inventory остался прежним.

Затем выполнен существующий --verify-audio-backend именно из установленного
WindowsApps EXE, сверенного с MSIX: process exit 73, backend_selfcheck_pass=true,
app_stopped=true, без forced cleanup. Ветка проверяет AEC на синтетических
массивах и возвращается до обычного UI/профиля/устройств. Она подтверждает
запуск нативного backend установленного пакета, а не hardware/AEC качество
на настоящем микрофоне или весь пользовательский сценарий.

Postflight повторно подтвердил: 0.1.0.15 / Ok, тот же EXE hash, userdata metadata
и trust совпали, GRAF/owned browser процессов 0. Прежний временный localhost
сертификат отсутствует в Root/CA/My. Реальная ОС VM: build 26300, Arm64;
PE x64 работает через эмуляцию. Это не физический Windows x64.

Полная переносимая CMake/CTest проверка текущих Windows inputs на macOS:
48/48 PASS. Хеши всех 223 inputs совпали до/после. Временный CMake build
удалён, журнал сохранён; native Windows-only/hardware ветви этим не принимаются.

| Терминальный артефакт stage | SHA-256 |
| --- | --- |
| `source.json` | `d96f0d091b65969dafd2416e53044c59697631d03c1566028424f13dbc62e75c` |
| `source-identity.json` | `00b0c852f835dd3704ff60286a551cafea5b14b7b431226d6127c8a8730c35e3` |
| `production-build-result.json` | `f1a0e239dda0ad22ff95b1f49f75015c7fbccb97648ef79227e596955c8738c2` |
| `inspection-result.json` | `672127b8ceab384b5b8c9b30cc20b87ecdcdea5b80a43728890719563eaafeb9` |
| `Install.ps1` | `170fb99390c220492a7fceec0ece58637af8821992a5ae74ce941e38e5f937a7` |
| `install-result.json` | `cbffc4a32b1333b987ca416cee29d7371c9017a373802bd5ee75651acae8286d` |
| `user-data-before.json` | `a5eee8143474dedea4e7095dd02aecf3b62aaa2b3d7613b13bc0da5059783381` |
| `user-data-after.json` | `a5eee8143474dedea4e7095dd02aecf3b62aaa2b3d7613b13bc0da5059783381` |
| `backend-result.json` | `5c60ae193fd4c469e6edef4fc59ad17bbd0ccc629c1de0aa0a068e3d0432990e` |
| `postflight.json` | `4182ed8fd94d0c31eb1140d17d2dddaf0543aaed427e85f61bbd87272ea34b90` |
| `pe-imports.json` | `64c1d2fc976c5010bc0d98fab8eba09fb979b9ad1f8761ff5b606fbac04d2f19` |
| `portable-suite.log` | `db8fedff9621cca39f57fb828333c25b983db11004efe0ec096d5b517b1e83df` |

## Финальное независимое заключение и очистка

В review-2026-11-03-production-package.md зафиксирован FINAL C0/H0,
ограниченный installed PASS: обычная сборка, signed MSIX, update прежней
identity, 15 EXE/DLL, metadata/trust preservation и установленный backend.
Это не UI/microphone/real-capture/release acceptance. Рецензент отдельно
различает зафиксированные в гостевых receipts 223 inputs и сообщение
исполнителя о host hashes до/после portable run: отдельной второй полной
host-инвентаризации для этих моментов нет.

После завершения review удалён только принадлежащий этому stage source
snapshot: 223 regular files, все хеши предварительно сверены с source.json.
Удалён только точный уникальный Windows package output из build receipt:
34 файла, 190 267 295 байт. Его Scope/отсутствие reparse points и hash
собственного MSIX проверены до удаления. Активная Windows build base,
установленный пакет и пользовательские данные не удалялись.
Финальный MSIX, source manifest, журналы и terminal receipts сохранены.
Cleanup повторно подтвердил 0.1.0.15 / Ok и ожидаемый установленный EXE.

| Квитанция очистки | SHA-256 |
| --- | --- |
| `host-source-cleanup.json` | `b2f588743894c426176666bad0a6bc59d26f319e2a0a94a20638221a0374a52c` |
| `package-output-cleanup.json` | `c19a7ddd6856ef64ea4214a71c67742b125f64e4cd034015e5fcfd74106674ac` |
