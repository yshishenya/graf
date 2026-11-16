# Независимое ревью требований: T097/T109 и ближайшая native-store регрессия

Дата: 2026-10-27. Ветка `codex/200-windows-followup`, HEAD
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`.
Рабочая копия: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`.
Исходное состояние: 319 dirty paths; проверяется рабочий снимок, не один HEAD.
Полоса проверки: read-only investigation требований существующего
`high-risk-product` F200; единственная запись рецензента — этот отчёт.

## Решение по ближайшему шагу

**Scoped requirements/checklist/analyze PASS: C0 / H0.** Можно сейчас готовить
короткую Windows-only регрессию в существующем
`apps/windows/Tests/GrafWindowsContractTests/NativeSettingsBridgeTests.cpp`:
настоящий `NotificationPreferenceStore::native()` → save/read-back quiet →
новый `MeetingReminderPresenter` с новым native store → bind того же synthetic
owner → load/read подтверждает сохранённый quiet. Это допуск по требованиям
для указанного test-only изменения, не одобрение ещё не прочитанного diff
или результат Windows-исполнения. Рецензент код не менял и тесты не запускал.

Основание: F277 contract «Мост и настройки» задаёт owner-scoped сохраняемые
quiet/defaults и проверку записи; plan:632–646 и tasks Phase16 сохраняют
T104 владельцем модели/настроек, quickstart §11.5 включает restart/quiet/save
failure. T097/#7240 — установленная приёмка, T109/#7343 — адресные платформенные
подписи и общий кабинет. Ближайшая регрессия покрывает persistence-подзадачу
существующей **T104/#7281**, связанную с их последующей приёмкой. Новая задача,
issue, формат, серверный метод и изменение продуктовых требований не нужны.
Номера взяты из локального issue-map; live GitHub state/назначения не проверялись.

Условия допустимого теста:

1. `_WIN32` ограничивает Windows-код и его вызов из main; прежние portable
   проверки сохраняются. Existing CMake target уже подключает `ole32` и
   `advapi32`; менять build/project файлы для заявленного шага не требуется.
2. Свежий random GUID owner используется в одной точной строковой форме для
   hashing/save/bind/load. До первой записи WinAPI подтверждает отсутствие
   **именно** `sha256(owner)` в HKCU `Software\GRAF\Windows\Notifications`.
   Существующее значение, ошибка доступа или неизвестный результат — отказ
   без перезаписи/удаления. `load()==defaults` не доказывает отсутствие:
   production load также возвращает defaults при повреждённых данных.
3. Запись проходит через настоящий native store, без map/fake callbacks,
   прямого RegSetValue вместо save или нового registry namespace/формата.
   Проверяются успешный save, read-back существующих bytes и quiet после
   загрузки новым store/presenter; остальные четыре preferences сохраняются.
4. Для минимального шага писать через store.save, presenter использовать
   только для bind/load/read. Не вызывать preview, calendar update/reconcile,
   capture или сеть. Новый presenter — проверка пересоздания объекта;
   это **не** перезапуск процесса или установленного приложения.
5. До первой возможной записи устанавливается ответственность за очистку,
   включая случай «write произошёл, последующий read-back отказал». Все
   проверки после начала mutation обязаны пройти очистку до assert/abort;
   один destructor не помогает при аварийном завершении assert. Ошибка
   очистки — FAIL, а не PASS. После удаления подтвердить отсутствие exact value.
6. Удаляется только созданное synthetic value через RegDeleteValue,
   с закрытием собственных handles; родительский key и чужие значения
   сохраняются. Нет RegDeleteKey/RegDeleteTree, перечисления/копирования
   реальных профилей или восстановления снимка всего key. Очистка после
   принудительного завершения процесса не обещается как доказанная гарантия.
7. Только existing NativeSettingsBridgeTests.cpp принадлежит этому code diff.
   Нужны последующее независимое чтение фактического diff и Windows-запуск
   точных исходников; успешный portable запуск не исполняет `_WIN32` ветку.
   Общие файлы/изменения соседних исполнителей не присваиваются этому шагу.

## Требования полной цепочки остаются отдельными

Quickstart:152–174 уже требует общую настоящую страницу
`/desktop/settings/notifications` → WebView2 → actual AppMain
`answerNativeSettings` → native persistence → новый read после маршрута и
перезапуска приложения. Отдельный synthetic stale-document сценарий удерживает
старое сообщение, заменяет документ и доставляет старый nonce: ни mutation,
ни ответа в новый документ; свежий read работает. Preview/занятая карточка,
клавиатура и возврат исходного quiet также остаются обязательными.

Outer bridge v1, notification request/reply v2, recording-settings v1 неизменны;
retired notification v1 не меняет данные. Исторические canOpenSystemSettings,
два канала и ранняя карточка явно заменены F277 и не возвращаются из старого
текста T097/T109. Требования FR-002/003/005/006/015/021/022 и SC-002/006/009
имеют существующих владельцев, конфликтов требований этого среза не найдено.

`prepare-appmain-problem-ui.mjs` допускает изолированный производный тест;
его нынешний Launch.inc использует store в памяти, а список byte-identical
bindings не включает answerNativeSettings. Это основание отдельно подготовить
и проверить full-chain fixture, не дефект требований и не разрешение заменить
реальную страницу, shim/handler/store подставными ответами. Production shim
сам предоставляет window.webkit; запрет касается fake browser ответов.
Новый тест store не подтверждает страницу, AppMain, WebView2, stale document,
полный restart, MSIX или паритет Mac. T097/T109 не закрываются.

## Маркеры и gates

Все 198 Markdown-файлов checklists прочитаны при инвентаризации маркеров;
содержание, относящееся к этому срезу, сопоставлено с текущими нормативами,
историческими analyze27/28 и review-2026-10-01-ui-parity.
31 файл содержит checkbox markers: **477 checked / 0 unchecked**;
неверных однобуквенных маркеров нет. Остальные 167 — отчёты без checkbox.
Это текущая инвентаризация, не повторное принятие 477 требований/реализаций
storage/audio/calendar и не перенос исторических PASS на новый код.

| Основной checklist | Checked | Unchecked |
| --- | ---: | ---: |
| requirements.md | 22 | 0 |
| audio-capture.md | 24 | 0 |
| advanced-routing.md | 14 | 0 |
| security.md | 27 | 0 |
| ux.md | 25 | 0 |
| Итого основных | 112 | 0 |

Отметки сохранены; новых критериев/галочек нет. В затронутой области
требования persistence/read-back, scope/ошибок, shared/native ownership и
раздельной приёмки достаточны; незавершённая реализация не является новым
HIGH требования. Неприменимые здесь требования не переодобрялись.
Tasks: **120 уникальных, 93 checked / 27 unchecked**; T097/T109/T104 открыты.
Порог scoped analyze «нет unresolved C/H» выполнен только для описанной
native-store регрессии и требований последующей full-chain проверки.
Это не общий F200 analyze PASS или разрешение закрыть остальные gates.
Analyze hooks before/after отключены; никакие hooks с изменением состояния
не запускались. Read-only review и существующая test-only подзадача не
требуют нового taskstoissues; live ownership и closeout остаются отдельными.

## Контроль снимка

| Артефакт | SHA-256 |
| --- | --- |
| spec.md | `69e8b6cadae116cb8b59684738583e64d953c4243e9020653390dc9695befe9f` |
| plan.md | `1afadff31435700bcbb599ee9293c0b2a350d59a1e78869d827cd2067ae087b6` |
| tasks.md | `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f` |
| quickstart.md | `8b64709535ccc81a5d2d3fbd869ca02fbe206323ef1b66ba44e7c04ec11c5891` |
| constitution.md | `d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859` |
| NativeSettingsBridgeTests.cpp до нового теста | `d4c07768cfb3650b830c73fd741192d66d1931debd5668ef7b587e65e1bfdde7` |
| MeetingReminderModel.cpp | `8aab49cfcbe1a7cf4a688f6865fa8e97a975fa630c49e560392721faa4ee53d1` |
| MeetingReminderPresenter.cpp | `8dc420c5f19f3d80c029daa7d229c986bfeb34e4899f3c31b0369fee02faf1ff` |

Сборки, тесты, VM, capture, сеть, GitHub, commit и installed profile не
запускались/не менялись. 319 исходных dirty файлов сверяются по SHA-256;
единственный новый путь рецензента — этот отчёт. Проверка требований не
подменяет независимое source review будущего patch и его runtime evidence.


## Дополнение 2026-10-27: scoped requirements и source review test-only settings adapter (source4)

Это append-only запись завершённых независимых проверок из текущего диалога.
Предыдущие выводы и история выше сохранены без редактирования. HEAD:
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`. Рецензент не запускал адаптер,
Windows build/runtime, CUA, VM, сеть или capture. Сообщения главного агента о
сборке/исполнении ниже отделены от независимо прочитанных исходников.

### Область требований и владение

Scoped requirements/checklist/analyze gate: **C0 / H0**, только существующая
проверочная подзадача T104/#7281 с результатами для последующей T097/#7240.
T104 владеет моделью, сохраняемыми настройками и account context; T097 — приёмкой
установленного MSIX. T109/#7343 сохраняет область адресных платформенных подписей.
Новых задач, production API, форматов или серверных изменений этот допуск не
требует. Это active high-risk-product slice; независимый обзор был read-only.
Связи issues сверены по локальному issue-map, без live GitHub проверки.

Требования к адаптеру: реальные HTML/assets из settings_visual_ui_harness;
настоящие configureCabinet → answerNativeSettings → bindNotificationContext и
native NotificationPreferenceStore; отсутствие подмен connect/nonce/replies;
явная свежая GUID-среда WebView с проверкой фактического профиля до первой
навигации; локальные ответы разрешённым ресурсам на стандартном trusted origin,
правильные MIME и отказ остальным запросам без сетевого продолжения. Подставные
identity GET проходят настоящий decoder. Registry ограничен точным ранее
отсутствовавшим sha256 канонического synthetic owner; очищаются только созданные
values, не родительский key. startSeed, production OnLaunched, microphone,
recording и установленный профиль не запускаются.

При requirements gate инвентаризация оставалась: пять основных checklists —
112 checked / 0 unchecked; все 31 файл с маркерами — 477 checked / 0 unchecked
среди 198 Markdown-файлов. Tasks — 120 уникальных, 93 checked / 27 unchecked.
Маркеры не менялись. Это не повторное принятие посторонних audio/storage/calendar
проверок. Hashes spec/plan/tasks/quickstart/constitution совпали с таблицей выше.

### Завершённая узкая native-store регрессия

Независимо прочитан финальный NativeSettingsBridgeTests.cpp SHA-256
`b1f8da8f3a28def5c83c85300974ebe596411fd272fe2d5d4834743c6e441791`:
canonical lowercase GUID owner, точный WinAPI absent-check, actual native save/read,
пересозданный presenter/load, cleanup до итогового assertion. Ошибка fixture input
с uppercase GUID и warning при wchar→char были исправлены без production change.
Главный агент сообщил Windows x64 Release: 216 source files verified,
BUILD_EXIT=0, TEST_EXIT=0 и native printed pass; executable SHA-256
`2c575ef1e5268eb5f6c3b647422f189e644e848e79b34118312dd81311202a36`.
Это предоставленное runtime evidence, не независимый запуск рецензента и не
доказательство page/AppMain цепочки, cold restart или закрытия T097/T104/T109.

### История source review адаптера и исправлений

Первый обзор выявил **H1 — Recreate обходит изоляцию**. Настоящий configureCabinet
устанавливал production recreate-handler: после browser-process failure штатный
Reload мог создать новый WebView через cabinet_->attach(webView_) без supplied
GUID environment. Проверка профиля, offline interception и permission deny были
установлены только на первом control. Gate был **C0 / H1, NO-GO до UI-запуска**.

Также CommandLineToArgvW использовался в forced-include header без shellapi.h,
который подключался позднее в AppMain.cpp. Главный агент подтвердил C3861 и
добавил shellapi.h в новый header; наличие include независимо перепроверено.
Прежний MEDIUM касался независимых флагов/счётчиков: они не доказывали порядок
quiet → meetings → returned settings. Отсутствие tickNotice не является дефектом:
срок preview обслуживает собственный Win32-таймер RecordingNoticePresenter.

В исправленных байтах после configureCabinet/bindNotificationContext заменён
только recreate-handler: state.failed=true и window.Close(), без нового control.
Следующий timer tick проверяет !failed до дальнейшей работы; Closing сохраняет
контролируемую очистку, а итоговый passed требует !failed. Native settings handler
не переопределён. H1 снят.

meetingsAfterQuiet теперь связывает переход в meetings с ранее наблюдавшимся quiet
без восстановления; при возврате в settings native store повторно читается,
returnedWhileQuiet и соответствующий log входят в проверку, а returnedWhileQuiet
обязателен для passed. Прежнее MEDIUM снято в части порядка навигаций и native
Registry quiet. Явная среда, проверка профиля до навигации, offline interception,
permission deny и точечная очистка сохранены. Новых C/H, проблем C++/WinRT по
прочитанным правкам или существенного переусложнения не найдено.

**Итог узкого source gate для source4: C0 / H0; допуск к ограниченному UI-запуску.**
Генератор прошёл node --check; разделители всех 11 проверяемых production methods
найдены однозначно. Их неизменность в производной копии проверяет генератор.
Главный агент сообщил, что отдельные Restore/Build позволили пройти generated
WinUI headers и после исправления C3861 компиляция AppMain завершилась; это не
считалось подтверждением завершения всей сборки или исполнения финального source4.

### Зафиксированные байты source4 перед исполнением

| Файл | SHA-256 |
| --- | --- |
| apps/windows/Tests/GrafWindowsContractTests/AppMainSettingsUiFixture.h | `ccf3c98a2a3ddc66aee4b5f030068bd491d22adb4037dac042af541a4050f7d5` |
| apps/windows/Tests/GrafWindowsContractTests/AppMainSettingsUiLaunch.inc | `091fec151822e55c8bbb8f8a855bbfeaee07174bb473bc74fbb8ab0c3ca4bb2a` |
| apps/windows/scripts/prepare-appmain-problem-ui.mjs | `fb97ec4345f05f239926aa720b3b686cd1c4c59a2b83eed8dfb6c8c4c594be63` |
| apps/windows/RecApp/AppMain.cpp, исходный production input | `a7927bb8e84b05f0c747fdca7756edbd8b0509ce8f49a0083187ff9680f0ff38` |

Hashes независимо перечитаны перед добавлением этого раздела. Изменение этих
байтов требует соответствующего повторного source review; успешная компиляция
предыдущей копии не переносится автоматически на новый снимок.

### Что ещё требуется и чего этот допуск не подтверждает

CUA обязан отдельно наблюдать фактическую страницу после возврата: успешный
native read/reply и отображение сохранённого quiet. returnedWhileQuiet доказывает
порядок навигаций и значение native Registry, но не доставку ответа и отображение
значения общим HTML. Одного terminal PASS или снимка страницы для full-chain
acceptance недостаточно; runtime evidence связывается с точными reviewed bytes,
экспортированными HTML/assets, производной копией и executable.

**Cold-process restart не принят. Stale-document negative test не принят.**
Для stale нужен отдельный удержанный запрос старого документа: после замены нет
мутации store или ответа новому документу, свежий документ может читать настройки.
Пересоздание presenter не равно обычному перезапуску приложения. Installed MSIX,
Mac parity, hardware/accessibility, CI и release acceptance этим обзором не даны.
**T097, T104 и T109 остаются открытыми; задачи/issues и checklist markers не
закрывались и не менялись.**

В этом дополнении изменён только reviewer-owned отчёт; code, checklists, spec,
plan, tasks, constitution, GitHub и VM не менялись. Широкий аудит не повторялся.


## Дополнение 2026-10-27: source6/source7, metadata и завершение диагностики

Append-only история узких source gates и последующая проверка сохранённых
свидетельств. Предыдущие разделы не редактировались. Код, checklists, spec,
plan, tasks, constitution, GitHub, VM и процессы рецензент не менял/не запускал.

### Source6: пассивный observer и исправление преждевременного отказа

Первоначальная диагностическая дельта получила **C0 / H1**: новый timer assert
runtimeState != unavailable выполнялся в первом tick до асинхронного attach,
тогда как начальное состояние host равно unavailable. В исправленном source6
attached=false становится true только после возврата настоящего attach;
проверка unavailable действует только после attached. NavigationStarting
сбрасывает completedAt; dest_present/mode_present отделены от сравнения с
ожидаемыми document/navigate. Печать fprintf согласована с типами аргументов.
Observer пассивен: нет записи заголовков, metadata admission или private data.
Повторный узкий source gate исправленной дельты: **C0 / H0**.

| Source6 input | SHA-256 |
| --- | --- |
| AppMainSettingsUiFixture.h | `caf55971736cd282c3f07b2365e32366a18f8b8ecf4cf24f7f763a9bcbcb970a` |
| AppMainSettingsUiLaunch.inc | `c364ee002a67cf8f7d4a0d4a2a0a483267bc2173325df291d83eaf9286700e3a` |

Главный агент сообщил успешную Windows-сборку source6 и наблюдение response:
GET 200 HTML, dest_present=0, mode_present=0, tag=0, tag_current=0,
generation=2, elapsed_ms=1250, after_completion_ms=-1. Сохранённые
attempt6-ui.err и attempt6-ui-result.json позднее прочитаны рецензентом:
эти поля подтверждаются журналом, PE SHA-256
`f4e61d1f4846b2f293dca1b9829f7356551517f7f3d5d9ca18e9c5739be240ac`,
exit=2, failure=UI_NOT_PASSED. Нативной строки SETTINGS_UI terminal=1 в этом
журнале нет. terminal=true в wrapper receipt означает завершение wrapper,
не доказывает выполнение cleanup самим приложением.

Выявлен runtime-дефект fixture lifecycle: программный Window.Close из catch
обошёл ожидаемую отмену в AppWindow.Closing и завершил процесс до timer cleanup.
Это дефект тестового адаптера, а не успешная приёмка страницы или очистки.

### Source6: отдельная очистка собственного оставшегося профиля

Первоначально сведения о cleanup переданы главным агентом. Затем рецензент
прочитал сохранённые Cleanup-Owned-Orphan.ps1 и source6-orphan-cleanup.json.
Скрипт ограничен точным GUID leaf и source6 PE/exit; требует отсутствие
GrafWindowsApp и browser с этим user-data-dir, ровно один каталог, точное
CreationTime 2026-10-27 22:55:27, отсутствие root/child reparse points и
посторонних root children. Проверяет отсутствие только synthetic preference
value через readonly Registry access; родительский key не удаляет. После
Remove-Item проверяет отсутствие именно выбранного каталога.

Сохранённый receipt: source6_orphan=true, terminal=true,
profile_cleaned=true, registry_value_absent=true, поля failure нет.
Это независимая проверка содержимого сохранённого скрипта/receipt и их
согласованности с source6 result. Фактическое текущее состояние Windows,
CreationTime, отсутствие процессов и удаление рецензент через VM не перепроверял.

### Source7: исправление closeFixture и перестановка fulfillment

Сначала независимо проверена единая идемпотентная closeFixture:
closing/time → host.close/capture.shutdown → timer wait browser → exact Registry
cleanup и попытка удаления своего каталога → terminal → Window.Close/Exit.
Tick catch и recreate выставляют failed; OS Closing использует ту же closure.
Программный Window.Close остаётся только в финальной ветке адаптера.
При незавершённом browser каталог не удаляется, passed остаётся false.
Узкий source gate этой дельты: **C0 / H0**.

Затем независимо проверен reordered fulfillment. Первый CoreInitialized
устанавливает All/All filter и deny-all handler, сохраняет event token;
каждый ранний ресурс получает403 и earlyResource=true. Третий Initialized
регистрируется после настоящего host.attach/production registration, требует
!earlyResource, устанавливает новый обработчик и только после этого синхронно
снимает начальный deny token. Новый обработчик сохраняет уже установленный
args.Response, включая production403; обслуживает только allowlisted GET на
стандартном origin, остальное403. При closing ответы запрещены. Log перед
fulfillment только наблюдает tag/current; Sec-Fetch и сертификаты не меняются.
Если Initialized уже произошёл inline, начальный deny остаётся и получается
ограниченный FAIL, не разрешение сети. **Итог source7: C0 / H0** только для
этой диагностической конструкции; без приёмки сборки или UI по одному source gate.

| Финальный source7 input | SHA-256 |
| --- | --- |
| AppMainSettingsUiFixture.h | `2cff0f71ea71c5707692fc3d31652ec978fe8fd6442970595df363732a3173f8` |
| AppMainSettingsUiLaunch.inc | `7948176946f786aa6be764f5cca4dd9d172b129b3ff1d0504755d7e651d92855` |
| prepare-appmain-problem-ui.mjs | `fb97ec4345f05f239926aa720b3b686cd1c4c59a2b83eed8dfb6c8c4c594be63` |
| Original AppMain.cpp | `a7927bb8e84b05f0c747fdca7756edbd8b0509ce8f49a0083187ff9680f0ff38` |
| Derivative AppMain.cpp | `d6d5699a6fea8f581415f92ad795ec88531ba7aaf0fdda0df9e14814b1c4b520` |

### Source7: независимая проверка сохранённых runtime evidence

Прочитан stage:
`/Users/yshishenya/Documents/graf-f200-public458.po8CtB/settings-chain-li1qcg1c`.
Использованы ui.err, ui-result.json, build-result.json, source.json,
test-source.json, appmain-test-bindings.json, Run-Ui.ps1 и архив source7.
Рецензент независимо сверил все218 файлов архивной производной копии с
manifest: missing0/mismatch0. Все11 production method sections побайтово
совпали с текущим оригинальным AppMain и hashes bindings, в том числе
configureCabinet/answerNativeSettings/bindNotificationContext. Hash производного
AppMain также совпал. Текущие два fixture inputs совпали с reviewed source7.

Build receipt: terminal=true, build_exit=0, source_files=218,
post_source_files=218, installed=false, launched=false, audio_started=false.
Build и UI receipts согласованно указывают один PE SHA-256:
`ddc844ddab0c30ec89e0bbb63c8671cfbcd38b16a29926b9bbc66e3494a4c133`.
WebView2Host.obj SHA-256 сохранён прежним:
`03a6e8adadb1624d7cbeb91fa7972b350f22e9bec68b8e9d7c381f5682011d05`.
Это сверка сохранённых build records и исходников, не новая Windows-сборка и
не независимое чтение самого PE на Windows.

В ui.err фактически записано:

```text
fulfillment_after_host=1 tag=1 tag_current=1
response=1 get=1 status=200 html=1 dest_present=0 dest=0
mode_present=0 mode=0 tag=0 tag_current=0 generation=2
elapsed_ms=1047 after_completion_ms=-1
page=settings native_quiet=0 returned_quiet=0
failure=settings_runtime_unavailable
terminal=1 quiet=0 restored=0 preview=0 settings_loads=1 meetings_loads=0
browser_stopped=1 registry_cleaned=1 exit=3
```

UI receipt: terminal=true, launched=true, exit=3,
failure=UI_NOT_PASSED, installed=false, audio_started=false. Wrapper не выдаёт
диагностический отказ за PASS. Нативный terminal теперь присутствует; source6
проблема программного закрытия устранена в исполненном source7 пути.

Production tagger действительно создал актуальный tag до локального Response;
наблюдаемый ResponseReceived.Request затем не содержит ни его, ни Dest/Mode.
Это ограничивает вывод данным locally fulfilled сценарием/сборкой/runtime.
Повторная перестановка тех же обработчиков не обоснована. Причина прежнего
отказа не сводится к невыполнению production tagger; host корректно не допускает
документ без обязательной коррелированной metadata. Обычный HTTPS/server flow
этим не признан неисправным; обход guard и fake Sec-Fetch/metadata запрещены.

Cleanup scope source7: нативный журнал подтверждает browser_stopped=1 и
registry_cleaned=1. Отдельного profile_cleaned=true/успешного удаления каталога
в source7 receipt нет; remove_all error учитывается в passed, но его значение
не печатается, а этот запуск уже failed по иной причине. Поэтому удаление
каталога source7 отдельно не принято только по данному журналу. UI wrapper
останавливается на UI_NOT_PASSED до своих success-only post-source/exe checks;
post_source_files=218 относится к build receipt. Архивные218 файлов сверены
рецензентом независимо, но это не live post-run проверка Windows checkout.

### Допустимый следующий путь и оставшиеся gates

Готового Fetch.enable/Fetch.fulfillRequest helper в apps/windows не найдено;
существующие CDP вызовы обслуживают Page/history. Новая CDP interception не
является минимальным reuse и не имеет доказательства сохранности этих headers.
Существующий WebView2AuthNativeTests real HTTPS fixture создаёт самостоятельный
host с WebViewRoutePolicy(test origin); положительные сценарии используют
certificate exception. Такую настройку нельзя молча переносить при нынешнем
запрете ослабления TLS.

У host, созданного неизменённым configureCabinet(), нет setter trusted origin;
CabinetWindow создаёт default host. Для real HTTPS full-chain нужны отдельно
согласованное test-only связывание test-owned origin без копирования handlers и
действительно доверенный тестовый сертификат. Это новый construction gate;
нынешний C0/H0 не разрешает cert bypass, изменение системного trust, рабочий
сервер или production API. Иная существующая native проверка может дать только
своё частичное evidence и не заменяет actual AppMain chain.

**Full-chain PASS отсутствует.** CUA ещё должен подтвердить native read/reply и
отображение quiet общей страницей, изменение/возврат/preview. Cold-process
restart и stale-document negative acceptance не выполнены. Installed MSIX,
Mac parity, hardware/accessibility, CI/release остаются отдельными gates.
**T097/T104/T109 не закрыты, checklist markers не менялись.** Основной validation
документ прочитан как контекст; рецензент его не редактировал. Только этот
reviewer-owned отчёт дополнен, широкий аудит не повторялся.

### Контроль сохранённых свидетельств

- `attempt6-ui.err`: `81727880ad913ec4adc06da4a0a93a4a1655ce03ece0459e9d7e008f3a8c05ca`
- `attempt6-ui-result.json`: `804b5292ca4ff51e18da9a066626bea0a5961d15742fd5e0e7a124ef9f32112a`
- `source6-orphan-cleanup.json`: `e86ccc209745065e420f495b650acc6f5d46df44dba575eae0551663aab02cdf`
- `ui.err`: `4b83df37a7edc32a83fcf586b3be5fa7f648be69ef038fc9cf4904e3a82ad4bc`
- `ui-result.json`: `fefaf918de58069cec2f5512df986784c4a9df191d9f5f78aca2ef22f6f02453`
- `build-result.json`: `44cc8324f22bcc72b3700e2d0ff1ffeca93014ce0c4bf722f269dcbd738becf5`
- `source.json`: `c40106791813540514a444a951e3e4c2febc300de372b5986e519c3ee42a06fd`
- `test-source.json`: `2b046db5f88ee6f3f207e147b1435db75f2cdc043937b8fd74769259f40ea767`
- `appmain-test-bindings.json`: `e109ef0b439c629930ef2513aff88692b9884bd2252de101bbf7e6abe7c47ab3`
- `Run-Ui.ps1`: `3c15149998640cc2763b54a0e259868176d87a7d518d13bb149a529a67b1a560`
- `Cleanup-Owned-Orphan.ps1`: `998833d1e58b95c074af01348f5ad61af8c47c508f1feaabbc23839eac344aad`


## Дополнение 2026-10-27: postflight source7 и HTTPS source gate перед импортом trust

### Отдельное сохранённое свидетельство очистки source7

Прочитаны stage `settings-chain-li1qcg1c/postflight.json`, его сохранённая копия
`attempt7-postflight.json` и `Postflight.ps1`. Оба JSON побайтово совпадают:
SHA256 `b3127ebd4c7a7ce062dada5aa70f706cd01b0530d381b69e1451a285067ceea8`.
Скрипт SHA256 `3bd914c747f305892cc6303f7c7cf5f2f0b5dbb38941833ae472190c71d37421`.

Квитанция: terminal=true, full_chain_pass=false, source_files=218,
resource_files=22; exe_sha256
`ddc844ddab0c30ec89e0bbb63c8671cfbcd38b16a29926b9bbc66e3494a4c133`;
owned_browser_processes=0, app_processes=0, owned_profile_folders=0,
registry_value_absent=true. Скрипт сопоставляет хеши source/resources/exe,
проверяет процессы, каталоги graf-settings-ui-* в четырёх временных корнях и
отсутствие exact sha256(synthetic owner) value без записи в Registry.

Это дополнительное сохранённое свидетельство закрывает ранее отмеченную
нехватку явного profile-cleanup evidence source7 на уровне квитанции.
Рецензент прочитал файлы на Mac; самостоятельного наблюдения VM, запуска
скрипта, проверки установленного приложения или full-chain PASS не заявляет.
Source7 остаётся диагностическим FAIL с exit3; его история не переписана.

### Текущие HTTPS исходники и границы проверки

HEAD прежний `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`.
Сопоставлена дельта трёх adapter-файлов с сохранённым source7; прочитаны новый
Python server и PowerShell runner. Код не изменялся и не исполнялся.
`node --check` и разбор Python через ast.parse прошли; PowerShell/Windows
compile/runtime в этой проверке не выполнялись. Текущие 11 sections AppMain
сопоставлены побайтово с производной OnLaunched в памяти: без изменений.
Генератор требует localhost HTTPS origin, меняет единственный ctor anchor
только в выходном CabinetWindow.h и учитывает его hash в test-source manifest.
Рабочий CabinetWindow.h сохраняет default ctor; AppMain SHA256 остаётся
`a7927bb8e84b05f0c747fdca7756edbd8b0509ce8f49a0083187ff9680f0ff38`.

Успешные GET allowlist теперь идут по реальному HTTPS; synthetic success
responses удалены. Отказы остаются 403. Origin сравнивается с actual host
policy до attach; cookie synthetic localhost; профиль проверяется до навигации.
Наблюдатель TLS только печатает пять actual cert WebErrorStatus, не меняет
certificate action. close.request вызывает прежний closeFixture, не управляет
элементами общей страницы. Эти adapter-поправки: **C0/H0**.

Конструкция с временным публичным self-signed localhost leaf в
CurrentUser Root допустима как отдельная тестовая предпосылка, при обычной
проверке TLS и обязательной очистке. Это изменение trust текущего пользователя,
а не только изолированного WebView profile; ограничения SAN/CA:false/serverAuth
не делают trust привязанным к одному PID. Производственный origin, handlers,
TLS guard, LocalMachine/My не должны меняться. Известные SDK certificate-ignore
флаги, AlwaysAllow и metadata admission отсутствуют в прочитанной дельте.

### Блокирующие замечания к текущему runner: C0/H2, RUN HOLD

**H1 — независимость и ограниченность очистки процессов.**
RunAppMainSettingsHttps.ps1:59–68 содержит общий try для app и server:
APP_NOT_DRAINED пропускает запись stop.request и ожидание сервера. При
SERVER_NOT_DRAINED процесс также остаётся жив; Dispose() освобождает объект
Process, а не завершает процесс. У Python нет timeout принятого TLS socket;
handshake на обёрнутом listening socket может удержать accept до обработки
потоком, а daemon_threads=false заставляет server_close ждать незавершённые
обработчики. Поэтому одного stop.request/deadline недостаточно для гарантии
завершения. Минимальная правка: независимые попытки app/server cleanup,
ограниченное graceful ожидание и проверяемое завершение только собственных
PID при превышении срока; отсутствие их процессов должно быть подтверждено.
Нельзя получать terminal-success, оставив server/private key в живом процессе.

**H2 — преждевременный и завышенный full_chain_pass.**
RunAppMainSettingsHttps.ps1:53 устанавливает full_chain_pass по Trust+exit73,
до finally проверки trust snapshot. При TRUST_SNAPSHOT_CHANGED или drain_failure
поле сохраняется true в итоговом JSON. Кроме того, exit73 не доказывает CUA
отображение фактически прочитанного quiet, cold restart и stale negative.
Минимальная правка: общий full_chain_pass сохранять false; отдельный результат
этого HTTPS/UI среза выводить после успешных обязательных проверок и очистки,
без failure/drain_failure/trust_failure. Независимую CUA acceptance учитывать
отдельно. До устранения H1/H2 импорт сертификата и UI run не проходят gate.

### Обязательные проверки перед принятием следующего runtime evidence

- Заморозить полный актуальный derivative/source manifests вместе с server,
  runner, close.request и TLS observer; проверить inputs/resources/exe до и
  после запуска. Пользователь сообщил source8 compile PASS219 без запуска,
  source9 compile220 pending; рецензент не проверял эти build receipts.
- Привязать cert.cer SHA256 к фактически загруженному cert.pem и key.pem;
  проверить self-signature, SAN только localhost, CA:false, serverAuth, срок
  действия включая NotBefore, отсутствие private key в Windows stores.
- До импорта exact leaf отсутствует в CurrentUser Root; сохранить snapshot;
  реальный untrusted WebView запуск должен дать actual TLS rejection и ни
  одного accepted settings HTML200/native write. generic exit3 недостаточен.
  Positive запуск только после подтверждённого negative той же версии/leaf.
- При trust positive подтвердить реальный metadata GET/HTML200 с browser-owned
  dest/mode/current tag и unchanged native path; unknown resource, неверный
  Host/origin/port, HTTP и non-GET не должны получить доступ. Проверки чужих
  origin выполнять без обращения к production/external server.
- Ошибка запуска, TLS отказ, deadline и обычное закрытие должны всё равно
  завершить собственные процессы и убрать exact imported thumbprint;
  snapshot после очистки равен исходному. Чужие добавления/сертификаты не
  удалять для выравнивания snapshot. Проверить fresh TLS отказ после удаления
  trust без изменения certificate guards. Временный private key убрать после
  остановки сервера, сохранить публичные hashes/receipts.

Самостоятельных VM действий, trust mutation, UI действий, сборки и запуска
рецензент не выполнял. CUA actual read/display остаётся отдельным требованием;
ordinary cold restart и stale-document negative не приняты. T097/T104/T109
не закрыты, checklist markers не менялись. Полный analyze/task/issue inventory
повторно не выполнялся; normative spec/plan/tasks/quickstart hashes прежние.

### Зафиксированные текущие байты

- `apps/windows/scripts/prepare-appmain-problem-ui.mjs`: `4939aa1f66f9333217284d4052cf5d7214d8e3fa2d14f94ac5e556a3cea7e818`
- `apps/windows/Tests/GrafWindowsContractTests/AppMainSettingsUiFixture.h`: `ddc75340e3d40cf2e4a4478be6dbe0ab28fab143628ef72f8238a9a0ea340392`
- `apps/windows/Tests/GrafWindowsContractTests/AppMainSettingsUiLaunch.inc`: `918497b0497a7fd37427266372ed80c926c16c79f4770a8fd3bb8bb1f8c91763`
- `apps/windows/Tests/GrafWindowsContractTests/AppMainSettingsLoopback.py`: `ed24733f8600645cc40a5d5839717072331c979862240f326a1594fc26ade2cb`
- `apps/windows/Tests/GrafWindowsContractTests/RunAppMainSettingsHttps.ps1`: `6f6afd1f91f8af167fe55a6f55903a4626b3c2c6a2730a065b22c62343fa2c52`


## Дополнение 2026-10-27: source10, исправленные H1/H2 и Windows untrusted evidence

Проверка ограничена текущими сохранёнными stage-файлами
`/Users/yshishenya/Documents/graf-f200-public458.po8CtB/settings-chain-li1qcg1c`.
Никаких самостоятельных VM действий, сборки, UI запуска, импорта/удаления
сертификата рецензент не выполнял. Изменён только этот отчёт, добавлением в конец.

### Связь source10 с source9 и исполняемым срезом

Независимо пересчитаны SHA256 всех 220 сохранённых файлов source10:
220/220 соответствуют текущему test-source.json, отсутствующих/ошибочных 0.
Побайтовое сравнение сохранённых source9 и source10 выявило ровно два отличия:
AppMainSettingsLoopback.py и RunAppMainSettingsHttps.ps1; C++ inputs одинаковы.
AppMain derivative SHA256 в обеих копиях:
`827ceb5bd0ef3b2d17d4c1c7d5ce6f305d1723ae9de8bf6434d8ed19531f19d9`.

Текущая build-result.json содержит terminal=true, build_exit=0,
source_files=220, post_source_files=220, installed/launched/audio_started=false;
exe SHA256 `1ca5a34213729acb480b0b3317b0c8d56a3601de4e2edcefde0f6466973d4511`,
AppMain.obj `b215c7a4879ca9358c8f3b62b7f5819695c777536ddac6504918a5a085c8969f`,
WebView2Host.obj `03a6e8adadb1624d7cbeb91fa7972b350f22e9bec68b8e9d7c381f5682011d05`.
Прочитанный Https-untrusted.ps1 передаёт runner именно этот expected exe SHA,
cert.cer SHA и reviewed server SHA. Сохранённый cert.cer соответствует pinned
`75611f3556a33cbe76a49bb2ded7736d170b65a9b32c94c7a309527393d06b14`.
Это сверка исходников, скрипта вызова и квитанций; физический PE/obj на госте
рецензент самостоятельно не хешировал, build/runtime не повторял.

### Исправления прежних H и узкий source gate

Ранее найденные H1/H2 устранены в последующих прочитанных исходниках:
**C0/H0 для текущего bounded source gate**. Независимые app/server cleanup с
ограниченным ожиданием/forced-fail, отдельная очистка exact thumbprint и
сравнение snapshot; full_chain_pass всегда false, отдельный https_slice_pass
вычисляется после cleanup со всеми failure flags. Финальный порядок trusted
ветви: app stop → exact root remove/snapshot → свежий SslStream default TLS
refusal → независимый server stop. AuthenticationException доказывает отказ
TLS authentication, но сам по себе не классифицирует точную ошибку сертификата.
Наблюдение WebErrorStatus относится к отдельному Windows negative.

Проверенные source10 bytes:
- AppMainSettingsLoopback.py:
  `8d1c533f731ee97745ded0b7438c9b11812d36d98a29ea53ed9fbecada3686e7`.
- RunAppMainSettingsHttps.ps1:
  `15823166fee6e4fecabcee5e1ad7406aa579d7a393d29d74d6bf12300dcdc39d`.

### Сохранённый результат Windows negative без trust

untrusted-ui.err содержит:
- native_read present=0 quiet=0;
- profile_verified=1 starts_before_check=0;
- tls_rejected=1 web_error=5;
- settings_runtime_unavailable;
- terminal=1 quiet=0 restored=0 preview=0 settings_loads=0 meetings_loads=0,
  browser_stopped=1 registry_cleaned=1 profile_cleaned=1 exit=3.

Во всём прочитанном UI журнале нет accepted HTML200 или native_read present=1.
В untrusted-server.err обе TLS traceback завершаются
SSLV3_ALERT_CERTIFICATE_UNKNOWN; это согласуется с TLS отказом клиента, а не
положительным HTTP сценарием. Сырого контента/cookies в отчёт не копировали.

untrusted-result.json: terminal=true, mode=untrusted, app_exit=3,
untrusted_refused=true, cleanup_reported=true, app_stopped=true,
server_stopped=true, trust_restored=true; native_scenario_pass=false,
https_slice_pass=false, full_chain_pass=false, installed=false,
audio_started=false. Нет failure/app_drain_failure/server_drain_failure/
trust_failure. Runner exit0 для ожидаемого negative сообщён главным; отдельного
поля process exit0 в JSON нет, состояние JSON согласуется с ветвью exit0 runner.
Native exit3 здесь ожидаемый отказ, а не успешная full-chain работа.

**Принято как сохранённое свидетельство Windows untrusted TLS negative этого
среза.** Отсутствие native write подтверждено наблюдаемым журналом и cleanup
receipt; отдельного трассирования каждой Registry операции не выполнялось.
В этой ветви Root не импортируется: trust_restored=true означает совпадение
snapshot, а не успешное удаление сертификата после positive run.

### Positive остаётся ожидающим; границы приёмки сохранены

По сообщению главного positive импорт ожидает реального Windows Security
Warning и пользовательского Yes; обхода UI подтверждения нет. Положительные
квитанции в этом дополнении не рассматривались. **Positive PASS и full-chain
PASS не заявляются.** Actual CUA display/read, ordinary cold restart и stale
negative acceptance по-прежнему отдельно; T097/T104/T109 не закрываются.
Код, checklists/markers, spec/plan/tasks/constitution и GH не изменялись.
Повторный task/issue inventory и широкий аудит не выполнялись.

### SHA256 прочитанных сохранённых артефактов

- `untrusted-result.json`: `c555fe7325e441d5d003cd74df90e569d31202d0f38a5d4950aac5b2b8351cdf`
- `untrusted-ui.err`: `219152d86fb77eacfc7ef0fffbf4b0de9cb9394a5a5abbcc4bf6fb8ad69ab96a`
- `untrusted-server.err`: `b6375043f856d71e0f14e75dd8f88d180c6c2e640bd911e79cd349b0806ab6cb`
- `build-result.json`: `a89d84458d08080eead6b3582d443d873fa53d47c7cc110ed5440e54a52b3869`
- `source.json`: `487cba19270355e9074285e882f9d32cd281b598b656b3bddf031272342d2131`
- `test-source.json`: `51cba3ccdf884311f4fa70bf314c15f5a87ce26abd0ad0a2ae1a58fcf2e28593`
- `appmain-test-bindings.json`: `87a8eca9b149e63c4888718f9d167ea6ef43c56d2d01319cd08e72ac9cb87b4d`
- `Https-untrusted.ps1`: `a8370c1eb932bda913fc318968a61844686ebe1abb532b63440eaa90677b14fc`
- `cert.cer`: `75611f3556a33cbe76a49bb2ded7736d170b65a9b32c94c7a309527393d06b14`
