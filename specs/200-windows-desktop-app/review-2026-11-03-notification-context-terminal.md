# F200 — независимая ограниченная SOURCE / terminal сверка

Дата: 2026-11-03. Проверка выполнена по фактическим локальным исходникам,
manifests, wrappers и журналам, без запуска приложения, VM, сборок или тестов.
Lane рецензента: read-only investigation с единственной разрешённой записью
этого отчёта; реализация остаётся существующим high-risk-product срезом F200.

Рабочая копия: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`.
Ветка `codex/200-windows-followup`, HEAD
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1` подтверждены чтением Git.
На входе наблюдались 349 dirty-путей, а не исторические 347. Чужие изменения
не исправлялись и не откатывались. Прочитаны AGENTS, guidance index,
spec-kit-flow/release guidance, feature pointer, оба notification-context
документа и validation-2026-11-03-master-preview.md. Старые API403 не являются
положительным review; эта проверка завершена с доступом к самим артефактам.

## Решение и область

**SCOPED SOURCE GO для временного master-integration-preview.** В шести
рассмотренных конфликтных файлах не найдено потери обязательных изменений
сторон или блокирующей ошибки совмещения. **Scoped terminal GO для повторного
notification GREEN73 и закреплённого CLI; четыре указанных native cases
квалифицированы как 4/4 PASS в своей generated-data области.**

Это не GO для применения merge, установленного приложения, всего T116,
миграции, аппаратной приёмки или выпуска. T104/T109 целиком, T097 и
T116/T117/T118 и завершающие gates остаются открытыми. Debug partial-recovery
timeout и активный 62-case job относятся к работе Main и здесь не исследовались.

## Совмещение shared UI с master

Stage: `/Users/yshishenya/Documents/graf-f200-public458.po8CtB/t116-custody-matrix-v4i88a4r`.
Preview проверен относительно доступного Git object master
`eab30ac17aa676e25fd367735cbdb39a48eaf40c`, base
`f5cca687a06dc57ad6ccbef840a0be897eaa6336`. Удалённый сервер заново не опрашивался;
GO привязан к этому SHA. Preview к checkout не применён.

Независимо сверены master_files с Git object, current/preview pins всех
overlays, семь дополнительных test overlays и три native-source файла для
браузерного извлечения. Для всех шести исходных diff3 previews совпали hashes
и числа конфликтов 1/5/1/1/2/1. Все неконфликтные участки сохранены в разрешениях
в прежнем порядке, маркеров конфликта в разрешённых файлах нет. Проверены
дельты разрешений относительно master и связанный текущий код.

| Конфликтный файл | Независимое заключение |
| --- | --- |
| cabinet/rendering.py | Сохранены master calendar join с target/rel, status, series и Windows data-platform-copy. Относительно master дельта этого файла — только платформенная подпись пустого календаря. |
| static/cabinet/cabinet.js | Сохранён master publishVisibleRecordings с ограничением 100 IDs, visibility/viewport checks и вызовами после обновлений; он требует Mac handler и bridge v1. Windows platformText, inventory state и notification refreshPending сохранены. Pending сбрасывается при disconnect, повторный read защищён nonce/generation/current; обновление не создаёт нового внешнего refresh. Остальные неконфликтные изменения master, включая календарь, не отброшены. |
| pages/settings_notifications_content.html | Сохранены пять предпочтений и test action протокола v2; Windows подписи добавлены без возврата старого permission API. |
| browser/local-recording-focus.test.cjs | Сохранены master сценарии обновления времени и F200 проверки UTC, фокуса, selection и 20 одинаковых публикаций после timezone change. |
| browser/playback-refresh.test.cjs | Сохранены master сценарии живого title editor, audio/draft/focus и F200 стабильность playback при отличии только native-кнопки. Mac platformText stub нужен извлечённому фрагменту. Есть повтор одного assertion о наличии local playback action; это безвредное дублирование проверки, не потеря поведения и не основание NO GO. |
| browser/settings-consistency.test.cjs | Сохранены master realQueue/response matrix и четыре новые F200 delayed-refresh регрессии. Извлечение platformText и чтение полного шаблона согласованы с новым embedded data attribute; контракт не возвращён к старой очереди. |

`master-preview-terminal-evidence.json` SHA-256
`eee23e4e00809f0d48f2f9f71318cb933d60645af406668f01b77829987cfcc5`:
совпали все 11 log pins, пять failed-attempt pins и четыре inputs. Прочитан
notification raw log: tests41/pass41/fail0/skipped0, включая четыре F200 cases.
Журналы подтверждают menu Chromium43/WebKit43, platform Chromium29/WebKit29,
106 Python PASS (один warning), playback в обоих сохранённых журналах,
combobox Chromium и actual WebKit, local-focus и исправленный autosave.
Exit codes в агрегате явно сообщены исполнителем по terminal tools; отдельные
журналы сами по себе не восстанавливают командную строку каждого запуска.

Проверено по исходникам: combobox выбирает `BROWSER`, playback — `GRAF_BROWSER`.
`master-preview-combobox-webkit.log` фактически содержит Chromium и исключён
из WebKit proof. Принят `master-preview-combobox-actual-webkit.log` с явным
`webkit:`. Два playback log имеют одинаковый hash и не называют engine внутри:
двухбраузерная атрибуция опирается также на сохранённую запись исполнителя.

Неудачные попытки не превращены в PASS: autosave locator timeout, старый CSS
unit без F200 overlay и отдельный Postgres setup error, неверный cwd/missing
test, 102 PASS + 4 browser setup errors без runtime, повтор Chromium вместо
WebKit. Окончательный 106 PASS не принимает DB-dependent notifications contract.
Исправление locator сверено с Git master: точная подпись production
«Загрузить сохраненное», hash теста
`a87b91ceb6b2a8d7a20e35421b413d0d130b55047c99f227163917eeb5b1c9f6`.
Synthetic браузерные результаты не принимают реальный API, Windows DPI,
WebView2 authority или установленный интерфейс.

## Restored notification GREEN73

Stage: `/Users/yshishenya/Documents/graf-f200-public458.po8CtB/notification-context-4d1aq44j`.
Сверены все 24 записи terminal-evidence.json: hashes и размеры совпали.
source.json совпал с checkout 225/225; test-source.json с frozen source 225/225.
RED manifest отличается только AppMain.cpp; единственный red-source файл
совпал с RED pin. Shared JS/test совпали с прежним SOURCE GO:
`6c4dca3b613e215b5c8dc1dbae2d039a195f562ae7836d13d02ab6b9b344ee8f` /
`d4fccecccf96bd276497746c55aff431062c61954209b6dc6ef9d6caa1f52fdc`.

Run-Restored.ps1 прочитан; SHA-256
`aca29abb008e589c6b0c819d699634764a816f13b234a2da8e196e5d3a42967b`
точно равен ранее одобренному pin. Проверки build/PE, полного manifest до/после,
deadline, одноразовой receipt, installed EXE и завершения own process сохранены.
Повторный native запуск квалифицирован: terminal=true, mode=green, exit73,
native_pass=true, 225→225, app_stopped=true, installed_exe_unchanged=true,
без failure/forced_cleanup. Raw stderr содержит единственную ожидаемую строку
`CONTEXT_UI terminal=1 refreshes=3 initial=1 no_files=1 worker_drained=1 browser_started=0 exit=73`.
Receipt hash `5123879a0a811d9ad5da198adb64f4323e9aa07e0b06ca82fb6ce3df70ae8455`,
stderr hash `933e0c0bb33a7aeb6491ded1c662183c9aea1d4c845ce243b4066ef1ba67f1cf`.
Они побайтно равны первому GREEN; отдельное имя wrapper/receipt согласовано,
но одинаковое содержимое само по себе не является независимой временной меткой.
GREEN PE в receipt: `62ce438210d69d8313cefb63f7ad349f43dc036adb644fa782a460892962086d`.
Существующие причинный RED и Restore из прежнего review сохраняют свои границы.

postflight.json подтверждает на момент записи installed0.1.0.15/Ok,
EXE `e6094e4de8b919ba94db652eae4f11ef9762c89d4d0b16f23e19f9342bfa02c5`,
ordinary_processes1/responding1, test_processes0, прежние legacy queue/quarantine,
protected_store_exists=false и previous_test_leaf_present0. Это сверенная
квитанция неизменности, не новая live-проверка VM или принятие старого storage.

## Закреплённый CLI и четыре native cases

pinned-python-governance-result.json, version/doctor/governance logs согласованы:
Spec Kit1.0.7/ref `fe1d00e3ccaf495880aaf90fb0e17679e82f065b`, exits0.
Фактически прочитаны cached launcher, METADATA и direct_url.json пакета;
233 хешированных файла пакета совпали с его RECORD. Cached launcher hash
`ad1e841e73de1d2009cd81b741a3843429a5d314dc2880f40019bb66ce1c4223`,
внешний Python launcher `6752b94c5e367f9632b7b398b3b5070c6ececdb3ef9434f05d6a0b320de0ef79`;
Python body побайтно одинаков, интерпретатор существует в том же cached env.
Это проверка локального происхождения, не новая загрузка upstream.
Фактический `.specify/speckit-bootstrap.lock.json` имеет hash
`b51653730eeec5f55066f92644dceb7257f9d8c37542924cb8de6b9e8da8f9f7`
и побайтно равен HEAD. Первые exit1 через relocatable launcher с пустым ref
и отказ глобального1.2.6 не принимаются за PASS. Общий PATH не квалифицирован;
правильный scoped runtime не требует изменения lock. Ничего не запускалось.

Stage `/Users/yshishenya/Documents/graf-f200-public458.po8CtB/t116-current-native-mt25cz_t`:
совпали все 12 terminal pins; source.json побайтно совпал с notification
test-source.json. Прочитаны Run.ps1, result.json, JUnit и actual-test.log.
Точный набор — NativeProtectedPendingStart, NativeProtectedShortDiscard,
NativeProtectedInspectionPreparation, NativeProtectedSchedulerSuccess:
4 PASS, failures/skipped0, Debug build/test exits0, 225→225,
installed_exe_unchanged=true, own_processes0. CMake mappings/исходный dispatch
согласованы с командами; assert не отключён NDEBUG. AppMain derivative не
является входом этого test target. Журналы содержат cold verification,
cancel/no-wire/drain и scheduler no-resend markers; это generated-data proof,
не реальные audio/network, весь protected-custody или новый installed build.

## Сохранность и последующая уборка

Рецензент ничего не удалял. В notification `source/` фактически 228 обычных
файлов без symlinks: 225 frozen-входов и три дубликата source.json,
test-source.json, appmain-test-bindings.json. Все три совпали с сохранёнными
в корне stage экземплярами. Единственный red-source AppMain также сверён.
Тем самым проверка hashes для указанной пользователем будущей уборки этих
локальных snapshots выполнена; решение о времени уборки остаётся у владельца
активной проверки. GO не распространяет удаление на root stage, preview,
журналы, manifests/receipts снаружи snapshots, VM base или installed app.

Не запускались VM/build/tests, CLI, cleanup или активный job; не менялись
source/tasks/checklists, Git index/refs, lock или чужие отчёты. Полный старый
аудит и обязательные завершающие проверки не повторялись и не закрывались.
