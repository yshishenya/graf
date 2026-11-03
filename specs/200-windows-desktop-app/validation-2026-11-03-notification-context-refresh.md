# F200: обновление настроек после подтверждения аккаунта

Дата: 2026-11-03. Существующий high-risk-product срез T104/T109.
Ветка `codex/200-windows-followup`, HEAD
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`, проверяются незакоммиченные исходники.
Рабочая копия: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`.
Независимое requirements/analyze/source review:
`review-2026-11-03-notification-context-refresh.md`.

## Причина и исправление

Первое чтение настроек может закончиться с `canEdit=false`, пока нативная
проверка аккаунта ещё не завершена. После её успешного окончания AppMain
обновлял модель напоминаний, но не уже открытую страницу настроек.
Теперь смена подтверждённого контекста вызывает существующий
`refreshNativeSettings`, после обновления маркеров контекста. Повторное чтение
из обработчика обновления не создаёт рекурсию; неизменный контекст не обновляет
страницу повторно. Выход из аккаунта также обновляет состояние страницы.

Общая страница раньше теряла refresh, пришедший во время незавершённого read.
Один локальный флаг теперь объединяет такие события в одно следующее чтение.
Disconnect сбрасывает флаг, а текущие проверки nonce/generation запрещают
повтор старого запроса после смены документа. Контракт сохранения, HTTP API,
права аккаунта и платформенные ограничения не изменены.

## Общая страница

`node apps/server/tests/browser/settings-consistency.test.cjs --notification-contract`:
41/41 PASS, exit 0. Четыре новые регрессии используют настоящий JS страницы
и существующую очередь: поздний контекст, disconnect, новый nonce и новая
generation с прежним nonce. Удерживаемый ответ снимался до смены контекста.
Контроль со старым JS: 37 PASS / 1 FAIL, точное несовпадение количества чтений
`2 !== 3`. Предшествующая ошибка запуска обёртки с повторным объявлением
`module` не считается RED; исправленный запуск записан отдельно.

Stage: `/Users/yshishenya/Documents/graf-f200-public458.po8CtB/notification-context-4d1aq44j`.
`shared-contract-result.json` — явно обозначенная запись исполнителя по
terminal tool result `5b94ad`, а не отдельно сохранённый сырой журнал.
Квалифицированный RED: `shared-qualified-red.log`.

| Исходник | SHA-256 |
| --- | --- |
| cabinet.js | `6c4dca3b613e215b5c8dc1dbae2d039a195f562ae7836d13d02ab6b9b344ee8f` |
| settings-consistency.test.cjs | `d4fccecccf96bd276497746c55aff431062c61954209b6dc6ef9d6caa1f52fdc` |

Существующий настоящий DOM-набор `settings-combobox.test.cjs` прошёл отдельно
в Chromium и WebKit. Сохранены `chromium-combobox.log`, `webkit-combobox.log`
и `combobox-provenance.json`. Единственная замена вне репозитория направляет
рендер Jinja на уже установленный Python основной рабочей копии; логика
тестов и проверяемые ресурсы сохранены. Это не отдельная DOM-регрессия позднего
notification read и не проверка установленного WebView2.

## Нативная проверка

Сценарий `notification-context` в существующем генераторе AppMain-проверок
сохраняет побайтно 11 настоящих методов. Используются настоящий NativeCapture
и pollAccount с удержанным generated auth-ответом, настоящий presenter и
память вместо сохранения предпочтений. Начальное чтение с `canEdit=false`
завершено до разрешения ответа аккаунта. Наблюдатель существующего вызова JS
проверяет обновление, повторное чтение, отсутствие рекурсии и выход.

Новый browser/profile/CoreWebView не создаётся. Нативный тест не доказывает
авторитет реального документа: URL и nonce заданы тестовой fixture. Устройства
и звук не читаются, HTTP подменён, storage root не создаётся. Окно закрывается,
account worker завершается штатно; сертификаты не меняются.

Release x64 сборка на ARM64 Windows в Parallels: build exit 0, 225 inputs
сверены до/после; AppMain.obj пересобран. GREEN: app exit 73,
`refreshes=3 initial=1 no_files=1 worker_drained=1 browser_started=0`.
Источник и EXE установленного GRAF не менялись.

RED удаляет только новый вызов `refreshNativeSettings` в bindNotificationContext
из производного AppMain; остальной source manifest идентичен. RED build exit 0,
225 inputs сверены до/после. RED run: exit 3, ровно одна ошибка
`context_confirmed_refresh`, `refreshes=0 initial=0`, no_files/worker_drained=1.
Это проверяет причину дефекта, а не только успешный запуск окна.

| Артефакт | SHA-256 |
| --- | --- |
| Обычный production AppMain.cpp | `71552b2ae132f5431ed2af8f45ba13d31225d9758fa3cf34df8f8b419721919f` |
| GREEN derivative AppMain.cpp | `a984861b090b3836086855b2d0eea4fd03eaed81999d2e3905252cac6e26b9df` |
| RED derivative AppMain.cpp | `f041143dbdb04a6255518150f753277ccec2c9e2eac741294817ee348387f51a` |
| GREEN EXE | `62ce438210d69d8313cefb63f7ad349f43dc036adb644fa782a460892962086d` |
| RED EXE | `a91d1287827c3fe4d4df4f85009251219c429e00a7582b4a88e12306c9cb434d` |

В stage сохранены source/test-source/red-test-source manifests, побайтные
bindings методов, build/run receipts и журналы. Восстановление GREEN и финальное
независимое terminal review фиксируются следующим append-only разделом после
получения результата; до этого они не считаются PASS.

## Границы

Установленный обычный GRAF по-прежнему 0.1.0.15: новый код этого среза в него
не установлен, общая страница не развёрнута на сервере. Его пользовательский
вход и отдельный блокер существующего storage root описаны в
`validation-2026-11-03-installed-ui.md`. T104/T109 целиком не закрыты;
T097/T116/T117/T118, настоящая запись и аппаратная приёмка остаются открытыми.
Commit/push/PR/merge, release и доверие к сертификатам не менялись.

## Завершение RED → Restore → повторный GREEN

После квалифицированного RED восстановлены все 225 GREEN inputs и прежний
GREEN EXE с проверкой его SHA-256. RED AppMain.obj и собственная временная
копия green.exe удалены. `restore-green.json` terminal=true, без failure.
Первый вызов Parallels вернул `PrlJob_GetResult: Invalid argument` без квитанции;
после проверки её отсутствия тот же защищённый от повторного выполнения
Restore завершился успешно. Ошибка наблюдения не считается ни падением
приложения, ни успешным выполнением Restore.

Повторный запуск использовал рассмотренный независимо Run-Restored.ps1:
от первоначального Run изменены только имена выходных receipt/stdout/stderr.
Первые GREEN/RED результаты не перезаписаны. `restored-green-result.json`:
terminal=true, app_exit=73, native_pass=true, 225 inputs до/после, app_stopped=true,
installed_exe_unchanged=true. Повторный marker: refreshes=3, initial=1,
no_files=1, worker_drained=1, browser_started=0. Это завершённый GREEN/RED/GREEN
на одном исправлении; ordinary installed GRAF в этих запусках не закрывался.

Native build/run выполнялись последовательно, владелец reusable build base
один. Base после восстановления содержит тестовый derivative, а не обычный
production AppMain; его нельзя упаковывать как готовое приложение.

## Проверки проекта и закреплённый Spec Kit

Проверки синтаксиса cabinet.js и генератора, `git diff --check` и разбор
F200.yaml прошли. Prerequisites подтверждает активную F200 в этой рабочей копии.
Сначала governance/frozen doctor отказали: общий specify на Mac уже 1.2.6,
а project lock требует 1.0.7/ref `fe1d00e3ccaf495880aaf90fb0e17679e82f065b`.
Project lock и общий инструмент не обновлялись и не понижались.

Закреплённый официальный CLI найден в локальном кэше и запущен offline.
Проверена настоящая direct_url.json с точным Git ref. Первая проверка через
его relocatable shell launcher не смогла определить ref: bootstrap читает
только абсолютный Python shebang. В stage/pinned-cli создан временный launcher
с абсолютным интерпретатором того же cached environment и побайтно тем же
Python body. Код CLI, provenance и проверка doctor не подменялись.

В таком локальном окружении `specify --version` дал 1.0.7, frozen doctor и
`python3 scripts/check_spec_kit_governance.py` завершились с exit 0. Квитанция
`pinned-python-governance-result.json` содержит суммы обоих launchers и
неизменного project lock; журналы — `pinned-python-*.log`. Первоначальные FAIL
через общий CLI и relocatable launcher сохранены отдельно. Это PASS для
явно закреплённого окружения, не утверждение, что общий PATH Mac исправлен.

## Последняя сверка установленного приложения и граница review

Metadata-only `postflight.json`: ordinary installed Version=0.1.0.15/Ok,
один отвечающий процесс с окном, test_processes=0, установленный EXE остался
`e6094e4de8b919ba94db652eae4f11ef9762c89d4d0b16f23e19f9342bfa02c5`.
Старые ledger/quarantine существуют, protected store отсутствует. Прежний
временный localhost leaf отсутствует в My/Root/TrustedPeople. Новая запись,
чтение содержимого старых файлов и изменения сертификатов не выполнялись.

Независимый reviewer сохранил source GO, первый GREEN, причинный RED и
Restore. Сверка повторного GREEN и локального pinned CLI исполнителем пройдена,
но заключительный независимый проход прерван API 403 у Gibbs; попытка
возобновления и новый reviewer Lorentz получили тот же отказ сервиса.
Новый terminal report не создан; его отсутствие не считается GO. Собственные
небольшие frozen source/RED overlay пока сохранены для завершения этой активной
проверки. Tasks/checklists не закрывались. Это ограничение работы reviewers,
не отказ GRAF и не автоматический запрет дальнейших безопасных проверок.
