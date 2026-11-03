# T108: нативное закрытие, возврат и завершение окна индикатора

Дата: 2026-11-03. F200, существующий `high-risk-product`, T108 / #7342.
Рабочая копия `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`,
ветка `codex/200-windows-followup`, HEAD
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`. Проверяется незакоммиченный снимок.

## Найденный дефект и исправление

Нативная проверка обнаружила реальное аварийное завершение после явного Quit
при существующем окне индикатора. Все промежуточные проверки окна и drain
завершались, но процесс возвращал `0xc0000005`, а не ожидаемый код 73.
Одного успешного сообщения terminal в журнале недостаточно: runner правильно
отклонил такой результат. Исходный неудачный stage сохранён:
`/Users/yshishenya/Documents/graf-f200-public458.po8CtB/shell-close-eptwa43d`.

В production Closed главного окна теперь удерживается локальная сильная
ссылка на indicatorWindow_ до возврата из indicator.Close(). Собственный
Closed окна индикатора синхронно очищает indicatorWindow_. Это минимальное
изменение времени жизни; второй путь Stop/finalizer не добавлен.
Обратная замена только этой правки восстанавливает исходный SHA-256 AppMain
`a85f5024813dbe4fdabbf879485bf12b4343b65b4a1709af1dbe8fdb012436c0`.

После правки тот же сценарий штатно завершился. Контроль с отменой только
этой правки повторил `0xc0000005`. Снятая собственным Win32 debugger трасса
подтверждает second-chance exception в ntdll, но DbgHelp в ARM-виртуализации
не раскрыл внутренний стек WinUI; более точная внутренняя причина по стеку
не заявляется. Дамп памяти не создавался.

## Сценарий и границы доказательства

Существующий генератор получил сценарий shell-close. Он сохраняет production
Closing/Closed, stateTimer и его положение, openMainWindow,
refreshTrayAvailability, indicator и общий exit/drain путь. Проверяется
побайтовое совпадение close/timer блока и 17 именованных секций.

В производной копии удалён ранний attribution/activation preamble, добавлен
наблюдатель, NativeCapture создан с отдельным несуществующим GUID-путём и
тестовым неготовым AEC, вместо storage validation вызвана управляемая ошибка
до reminders/readiness. Сохранён настоящий startup-error интерфейс и реальная
кнопка «Закрыть GRAF». AutomaticRecordingPolicy/notification store работают
в памяти. HWND берётся от собственного WinUI окна после загрузки кнопки;
не используется поиск общего окна по заголовку. Остальные подстановки
OnLaunched/entrypoint явно перечислены в appmain-test-bindings.json.

Последовательность использует настоящий WindowsTray с регистрацией Explorer
и настоящий WM_CLOSE своего главного окна:

1. Idle: hide, возврат тем же openMainWindow, затем Close без собственного трея
   сохраняет окно.
2. Friend peer вызывает существующий prepareRecording без launch: настоящая
   starting-резервация и эксклюзивная WindowsDesktopSession lease, без устройств.
3. С доступными треем и реальным CompactOverlay/Stop окно скрывается;
   повторное WM_CLOSE не меняет резервацию.
4. Возврат показывает то же HWND/controller, непустой session ID и starting;
   другой WindowsDesktopSession по-прежнему получает activeSessionExists.
5. При скрытом отдельном индикаторе крестик сохраняет главное окно. После
   возврата индикатора удаляется только собственный трей; главное окно снова
   остаётся доступным, indicator/Stop остаётся видимым.
6. Существующий SDK ButtonAutomationPeer вызывает реальную кнопку Quit один
   раз. Нужны общий drain, освобождённая lease, Closed и штатный код процесса.

Девять фаз содержат шесть WM_CLOSE и два возврата. Тайм-аут/спасательный Quit
навсегда оставляет failed; принудительное завершение runner не даёт PASS.
В проверках same подтверждаются отсутствие обоих WASAPI workers, dispatcher
и приёма batches. Синтетический custody-root не создаётся.

Это ограниченная проверка partial-startup shell, idle/starting и политики
закрытия. Она не принимает реальный звук, recording/paused/finalizing,
нажатие Stop во время захвата, настоящий выбор меню трея, нормальный fallback
banner, внешний auth/upload, установленный MSIX или всю задачу T108.

## Результаты Windows и локальных проверок

Основной stage:
`/Users/yshishenya/Documents/graf-f200-public458.po8CtB/shell-close-pin-juyt4_9v`.
Windows base: `C:\Temp\graf-settings-chain-li1qcg1c`.

| Проверка | Результат |
| --- | --- |
| MSBuild Release x64, исправленный вариант | exit 0; 223 input hashes до/после |
| Нативный исправленный вариант | exit 73; 9 фаз, 6 Close, 2 возврата, 1 Quit; drain/lease/no_files PASS |
| Контроль: отменена только локальная сильная ссылка | build 0; 222 прочих inputs прежние; процесс `0xc0000005`, native_pass=false, red_rejected=true |
| Восстановление исправленного варианта | 223 inputs и EXE hash совпали; RED AppMain.obj удалён, резервная EXE-копия удалена |
| RecordingIndicatorTests на macOS | 1/1 PASS; временный CMake build удалён |
| Пинованный Spec Kit doctor + governance | PASS; отдельная временная среда удалена, глобальные версии не менялись |
| git diff --check | PASS |

Исправленный PE:
`cef34154c06b165a6b5c78d00a9271c41aedb2b3f7f6cff442b8977823027da8`.
Контрольный PE:
`40106f0ed834d432723e2060fea7bee8b47f6d18c0ba586ac43a312c81e01e04`.
При смене производной копии принудительно удалялся только её AppMain.obj:
код MSBuild 0 дополнительно проверяется свежим временем объекта и хешами.

Установленный GRAF остался 0.1.0.14 / Ok, его EXE не изменён.
Эта проверка не устанавливает приложение, не включает микрофон и не меняет
доверие к сертификатам. T108 и issue #7342 остаются открыты: нужны остальные
состояния и приёмка точного установленного пакета. Требования и tasks не изменены.

## Точные исходники этого прохода

| Файл | SHA-256 |
| --- | --- |
| `apps/windows/RecApp/AppMain.cpp` | `b7a2ab3ec2128636c0b953a1c79e8a29f74f3b408734853b8bb25ec2ed34927e` |
| `apps/windows/scripts/prepare-appmain-problem-ui.mjs` | `b192b8ffce4d0626026a1ed75275f5abbd86e6d2acf1b139c4617523f6eb2bc2` |
| `apps/windows/Tests/GrafWindowsContractTests/AppMainProblemUiFixture.h` | `d4bd42ec58be9857fca4b264be58ddb795a00e3873b782258d1999eb2ebae904` |
| `apps/windows/Tests/GrafWindowsContractTests/AppMainShellCloseUiLaunch.inc` | `f27231449d0dcf4d048ce7ebe9827d45ab2d29638a5ded1dc8c1f3898a12ac45` |

## Повтор после восстановления и очистка

После обратного контроля восстановлены точные исходники и сохранённый GREEN
EXE; повторный native run снова завершился 73 с теми же 9 фазами / 6 Close /
2 возвратами / 1 Quit, native_pass=true, без принудительного завершения.
Проверены 223 input hashes до и после. Рабочая копия и установленный пакет
не заменялись тестовой производной.

Postflight: app/debugger процессов 0; прежний временный localhost-сертификат
E124DC23EF7CCEEEA348867E51692D9706798C32 отсутствует в CurrentUser Root/CA/My;
новых операций доверия в этом проходе не было. Только собственные временные
TraceExit.exe/obj удалены с записью контрольных сумм. Установленный GRAF:
0.1.0.14 / Ok, EXE SHA-256
`6e1626953fc7e409837d65bbdebd642d509e69569ae43545039826a433b72a48`.
Проверка YAML fragment и синтаксиса генератора прошла.

Терминальные артефакты stage (до удаления только source-снимков):

| Артефакт | SHA-256 |
| --- | --- |
| `source.json` | `d96f0d091b65969dafd2416e53044c59697631d03c1566028424f13dbc62e75c` |
| `test-source.json` | `d1cb5f35ab22ddf50638ca4e7bcd27337b2598677153865f0a8641f5d6655c0f` |
| `appmain-test-bindings.json` | `87b6e2fe5a295637e5ddffbb9aacf92715f8df580c4193e943e51d34fa5fc0bc` |
| `build-result.json` | `c626233191f2316f230b1c3b9b2d427fd5dfcbc334fc37de1948ca59001266d9` |
| `green-first-result.json` | `2d4954a03d47c2df4e18237b76151ffa13e29600e8aedd7cd4ea75933fcc5feb` |
| `red-control.json` | `9cfd60409aefebc05e5aa9903df09546debc13fd68d118536ebcd714949f133e` |
| `red-test-source.json` | `bf84685050f3aa6adf544d093a08308de64924ca0fe520b80a1bb3cb99750345` |
| `red-build-result.json` | `cc922859dd8f76cbde3022da032acdd8684c373fa2ae180ab7c4e7280e8edeff` |
| `red-result.json` | `715ab88c1f8fbcd677000ed4631d06014ead8bf5c1d5920c44e78127624a7651` |
| `restore-green.json` | `bdf9a5c99c32e601cc41185b757c1d869a20a36b986a89577e458df665fac4c3` |
| `green-result.json` | `2d4954a03d47c2df4e18237b76151ffa13e29600e8aedd7cd4ea75933fcc5feb` |
| `postflight.json` | `4d892bf9450bf0b03a8f796ec79ec69cb05c79c5b6ecc1a7c872d3acc7f3a064` |
| `governance.log` | `7111217999a9a47bdc8a16d0bc72045c5fe301d30f94e6427a2aa996c6255fb4` |
| `portable-close.log` | `f0dd6c3451419fbccd5e5f8a93d41c155bd8f5f830898e4178706ed650103680` |

## Независимое ревью и финальная гигиена

Финальное независимое ревью в review-2026-11-03-shell-close-native.md:
PASS, C0/H0 по текущим четырём исходным файлам, документам и точной
последовательности исправленный → отмена правки → восстановление → исправленный.
Прежний H1 аварийного выхода закрыт только в проверенном сценарии.

После ревью удалены только собственные host source/red-source снимки двух
stage: в каждом 226 проверенных regular source files и 1 контрольный AppMain.
Все хеши сверены перед удалением; host-source-cleanup.json сохранён отдельно
в каждом stage. Manifests/logs/receipts и диагностический исходник сохранены;
активная Windows base и рабочая копия не удалялись.

Свежий fetch master подтвердил прежний origin/master
`eab30ac17aa676e25fd367735cbdb39a48eaf40c`; HEAD не менялся.
Это наблюдение удалённой ветки, не утверждение о выполненном merge или
полном соответствии всем её изменениям. Нужна отдельная интеграционная
приёмка общего кабинета и текущего macOS. В этом раунде commit/push/PR/merge,
установка и release не выполнялись. Tasks.md побайтово сохранён:
`80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f`.
