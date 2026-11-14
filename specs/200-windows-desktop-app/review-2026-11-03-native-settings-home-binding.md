# Независимое ревью F200: домашний маршрут тестового CabinetWindow

Дата: 2026-11-03. Ветка `codex/200-windows-followup`.
HEAD: `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`.
Предмет — новые изменения рабочей копии поверх ранее проверенного снимка
`settings-return-20261103.qcbz2uck`, не весь накопленный diff относительно HEAD.

**SCOPED TEST-ONLY SOURCE PATCH APPROVED — C0/H0.** Новых критических или
высоких замечаний к указанной дельте нет. Изоляция генератора и все его
производные изменения объявлены и проверены. Прежнее замечание P2 об очистке
самостоятельного теста закрыто. **Положительная UI/full-chain приёмка — HOLD.**

Полоса: ограниченное независимое ревью существующего `high-risk-product`
среза F200; единственная запись рецензента — этот отдельный отчёт.
Прочитан контекст `review-2026-11-03-native-settings-fixture-routes.md` и
относящееся к новой правке дополнение validation. Новый цикл Spec Kit,
широкий аудит, изменение контрольных списков и обновление задач не выполнялись.

## Что проверено в новой дельте

1. `apps/windows/scripts/prepare-appmain-problem-ui.mjs:79–94`:
   новая замена находится только в ветви `scenario === 'settings'` и пишет
   только в отдельный выходной каталог. Реальные пути repo/output проверяются
   через realpath; выход обязан быть пустым и находиться вне рабочего дерева.
   Адрес ограничен HTTPS localhost и портом, проверяется до копирования.
   Замена требует ровно одно точное вхождение production home expression;
   при изменении исходника генерация остановится, а не расширит замену.
   `CabinetWindow.cpp` получает тот же origin, что производный конструктор.
   Новая замена явно указана в `replacements`; исходный и производный хеши
   файла отдельно входят в `source.json` и `test-source.json`.
2. Причина неработающей кнопки в прежней конфигурации подтверждается кодом:
   `AppMain.cpp:855` вызывает `cabinet_->openCabinet()`, а рабочий
   `Shell/CabinetWindow.cpp:5` содержит production home URL. При локальной
   политике старого derivative этот адрес не допускает внутренний переход.
   Исправлена конфигурация именно общего вызываемого метода в тестовой копии;
   обработчик кнопки и production CabinetWindow не изменены.
3. `AppMainSettingsUiLaunch.inc:59–66`: до присоединения WebView2 вызывается
   настоящий `openCabinet()` и требуется одновременно allow, meetings и
   точный нормализованный локальный адрес. Затем выбирается notifications,
   как прежде. Проверка не подставляет успешный route/result, document tag,
   native reply или HTML. До присоединения Core этот вызов не выполняет
   браузерную навигацию; прежняя проверка профиля до первой навигации сохранена.
4. `AppMainSettingsUiLaunch.inc:124–139`: новая диагностика добавляет только
   SHA-256 UTF-8 пути после удаления query. Действуют прежние точные
   origin/GET/Document условия; вывод не содержит URL, query, cookies,
   содержимое страницы или идентификатор владельца. Вычисление допуска и
   отказ 403 не изменены; metadata observer не получает полномочий допуска.
5. `test_appmain_settings_loopback.py:76–83`: при первом TimeoutExpired
   вызывается kill именно собственного объекта Popen, затем communicate с
   пределом 3 секунды и повторно выбрасывается исходный отказ. Поиск процессов
   по имени, массовое завершение и изменение системного trust отсутствуют.
   POST/plain-HTTP проверки уже описаны прежним отчётом и не считаются новой
   продуктовой дельтой.

## Независимая сверка снимка и границ

Снимок: `/Users/yshishenya/Documents/graf-f200-public458.po8CtB/settings-home-20261103.meye7krg`.

- Все 221 вход source.json совпали с текущей рабочей копией; все 221 файла
  `source/` совпали с test-source.json. Совпали также 23 ресурса и 112 входов
  shared-source.json. Список ресурсов и их хеши идентичны прежнему снимку.
- От предыдущего source.json отличаются ровно три входа: генератор,
  AppMainSettingsUiLaunch.inc и самостоятельный test_appmain_settings_loopback.py.
  Ни один вход `apps/windows/RecApp/` не изменён относительно прежнего снимка.
  В частности, AppMain, WebView2Host, WebViewRoutePolicy, bridge, TLS/history/
  response/nonce guards и обработчик настроек не менялись этой правкой.
  Это сравнение с предыдущим dirty-снимком, а не утверждение о чистоте HEAD.
- Между source.json и test-source.json отличаются ровно четыре производных
  файла: AppMain.cpp, GrafWindowsApp.vcxproj, CabinetWindow.h и CabinetWindow.cpp.
  Все четыре независимо реконструированы в памяти из текущих исходников
  согласно прочитанному генератору и совпали с сохранёнными файлами побайтово.
  Forced include ограничен compile item AppMain.cpp и объявлен отдельно.
- Все 11 секций unchanged_methods побайтово совпали с текущим production
  AppMain и с хешами bindings. Производный AppMain имеет SHA-256
  `ca15224e94be4aca8ef173b1d7d67c4166ee1ace74634b0752a65a6767a690fe`.
  `installed_acceptance=false` сохранено. Рабочий CabinetWindow.cpp по-прежнему
  содержит production home URL; расширения production trust нет.

## Выполненные проверки и сохранённая сборка

Рецензент выполнил node --check генератора и прямой запуск
`python3 -B apps/windows/Tests/GrafWindowsContractTests/test_appmain_settings_loopback.py`:
PASS для redirect, HTML/JSON MIME, allowlist, Host, POST, plain HTTP и content drift.
Временные TLS-материалы очищены самим тестом; системное доверие не менялось.

Тот же существующий тест дополнительно выполнен через runpy с подменой Popen
только в памяти: первый communicate собственного сервера принудительно
выбрасывает TimeoutExpired. Проверены kill точного дочернего процесса,
его завершение после ограниченного reap и распространение исходного
TimeoutExpired с timeout=8. PASS. Файлы тестов не редактировались и не добавлялись.
Таким образом прежнее P2 о потерянном subprocess закрыто.

Во время ревью завершилась уже запущенная другим исполнителем SDK-сборка.
Прочитаны Build.ps1, build.log и build-result.json: terminal=true,
build_exit=0, source_files=post_source_files=221,
installed=launched=audio_started=false. Скрипт проверяет хеши входов до/после
сборки и задаёт Release/x64. Журнал явно содержит компиляцию AppMain.cpp и
CabinetWindow.cpp, затем успешную линковку. PE SHA-256 по квитанции:
`4930911152d4caba3f0a5204169c062459a944dc515ced5fea7db4df35aaac43`.
Хеш WebView2Host.obj остался прежним:
`03a6e8adadb1624d7cbeb91fa7972b350f22e9bec68b8e9d7c381f5682011d05`.
Это принятое сохранённое свидетельство сборки; рецензент самостоятельно не
хешировал гостевой PE, не запускал Windows и не менял trust/установленный пакет.

## Конкретные ограничения допуска

- Старый положительный запуск остаётся FAIL: trusted-result.json содержит
  app_exit=3 и native_scenario_pass=https_slice_pass=full_chain_pass=false.
  В журнале quiet=1, restored=preview=0, settings_loads=1 и meetings_loads=1;
  последующий document=other allowed=0 закончился response-metadata-timeout.
  Пользовательское сообщение о неработающей кнопке не отменяется фактом
  загрузки meetings. Исправление домашнего адреса объясняет конкретный дефект
  кнопки стенда, но не устанавливает путь или причину следующего document=other.
- Новый path_sha256 поможет сопоставить локальный document с предполагаемым
  путём без публикации URL. Категоризация pageName и response observer
  по-прежнему не охватывают other/query так же полно, как транспортный допуск;
  хеш не заменяет доказательство успешной навигации или native read.
- Проверка openCabinet до attach принимает только привязку маршрута.
  Для UI-приёмки всё ещё нужен настоящий клик «Встречи» и возврат в настройки
  с повторным native read/отображением сохранённого выбора, восстановлением
  исходного выбора и preview. Новый успешный Windows-сценарий этим ревью
  не подтверждён. Старый PE/его TLS negative не принимают новую сборку.
- Старый trusted-postflight подтверждает сохранённое terminal-состояние:
  app/browser/profile=0, synthetic Registry value и точный сертификат
  отсутствуют; runner сообщает app_stopped/server_stopped/trust_restored и
  fresh_tls_refused. Это не самостоятельное наблюдение очистки VM рецензентом
  и не доказательство очистки будущего запуска.

Новых C/H-блокеров исходного патча нет. Условия runtime/UI, установленного
приложения и выпуска остаются отдельными воротами. T097/T104/T109 и отметки
контрольных списков не изменялись; закрытие задач этим отчётом не разрешается.

## Привязка проверенных байтов: SHA-256

| Артефакт | SHA-256 |
| --- | --- |
| prepare-appmain-problem-ui.mjs | `48d02f4504d436eb1e4f9edbacd232893ff00730ff29359a689b31f140d76ac3` |
| AppMainSettingsUiLaunch.inc | `df4b94510fdebe17edf4f2488872e63f8ea79cb31bfbdf07679a426f33158f46` |
| test_appmain_settings_loopback.py | `8ad62aaec7c27f188c6dda9082a29632864c56c79cfff98e91ef493a596f4cc9` |
| home/appmain-test-bindings.json | `32edbf3fc8fc2eab79763fe816822f10c32a77f9d90a90d148e8c2bb907166f5` |
| home/source.json | `b64f240da31fb63f43d9593b08131c2cb08b227762e93dd866ca7ae62eb8dc5f` |
| home/test-source.json | `8838b7f11739484dfad2a18d4bab55cf4815b4a346606a86714b6ad1d09d8c66` |
| home/resources.json | `aa839a28a717f46dd90ab8f2d08c6bb60feb240da544afd927ebbd4f109f98b4` |
| home/build-result.json | `cda482ae68856492c101af7e8181175cce6466ed64c22116bda34592e6b1163b` |
| home/build.log | `b2fef498e65c5a51c5d3b501f0bf3d86e686f289a44d0cf7d942d354b17f5120` |
| return/trusted-result.json | `dbf5d88000d6d8cf1d5723640c4703744d665b5f2a2b0ab2f3d4147a8703f6c7` |
| return/trusted-ui.err | `eed15f3afb46ecf82c0d747507f074d90a406fa73e79e0a517b8ea4c8d092653` |
| return/trusted-postflight.json | `88d8b553f1d403769d81d64c0329f872678d2beeed48d13f9fc149768fe39b78` |

В таблице home/return обозначают два явно названных выше сохранённых снимка.
Изменён только этот новый отчёт. Прежний reviewer report, код, spec/plan/tasks,
контрольные списки, Git index/refs и чужие изменения сохранены.
