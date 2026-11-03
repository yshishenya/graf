# F200: notification context refresh — ограниченный requirements/analyze gate

Дата: 2026-11-03. Рабочий корень:
`/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`.
Lane: high-risk-product, существующий T104, интеграционная граница T109.
Новые задачи, схемы, серверные API и продуктовые решения не требуются.

**SCOPED REQUIREMENTS / ANALYZE GO, C0/H0 для предложенных двух строк
AppMain и native derivative context-refresh.** Допуск относится к реализации
и проверке связи смены нативного контекста с refresh API. Это не source PASS
ещё не написанного патча и не полное закрытие P2 во всех порядках DOM/read.

## Основание и ограниченный analyze

Сопоставлены T104/T109 в tasks.md:448,474–478,486, spec FR-002/FR-006,
contracts/f277-notifications-parity.md §§«Мост и настройки»,
windows-native-web-bridge.md §§3–5 и settings supplement, quickstart:152–166,
checklists/security.md CHK006–009/011, ux.md CHK019/020,
review-2026-09-28.md и analyze-2026-09-28.md в части контекста/настроек.
Прочитаны фактические AppMain binding/answer, model epoch, host refresh и
script guards, общий JS load и существующая notification-contract fixture.
Это адресная проверка требований и согласованности; общий marker 477/0 не
пересчитывался, существующие checklist/task отметки не изменялись.

T104 владеет settings/context; T109 сохраняет общую страницу и адресную
адаптацию. Вызов существующего refresh API после изменения контекста не
меняет protocol v2, owner-scoped store, permission UI или маршруты. Нельзя
выдавать неподтверждённый аккаунт за подтверждённый. READY, cookie reconciliation,
доступность хранилища и возможность записи этим вызовом не устанавливаются.
Противоречий выбранной узкой реализации этим требованиям не найдено.

## Условия реализации двух строк

Внутри существующего условия изменения problemContextEpoch_ /
problemAuthGeneration_ после invalidate/update и refreshSelectedRecording:
`if (cabinet_) cabinet_->webView().refreshNativeSettings();`.
Сохранить обновление обоих markers ДО вызова: наблюдатель/ответ настроек может
повторно вызвать bindNotificationContext, но неизменный контекст не должен
повторно обновлять страницу. При account bind меняется model epoch; при logout
меняется auth generation и снимается owner. Не добавлять polling refresh на
каждом tick, новый setter аккаунта, чтение cookies или запись настроек.

refreshNativeSettings уже требует settings nonce и nativeRunScript callback;
production callback проверяет document generation, ready, actual Source,
current URL и разрешённый bridge origin. Эти проверки сохраняются. Сам nonce
не является доказательством подтверждённого account context.

## Самая маленькая содержательная native регрессия

Предложенный context-refresh scenario генератора допустим:

1. Byte binding реальных bindNotificationContext, answerNativeSettings и
   refreshSelectedRecording; без копии их логики в тесте.
2. NativeCapture с явным no-HW AEC, новым несуществующим GUID-root, без
   startStorageValidation/readiness/device probes. Строгий generated wire
   принимает только ожидаемый account GET с синтетическим token; прочие
   HTTP/effects отвергаются. Account подтверждается настоящим pollAccount /
   future, без fake account setter. Presenter/store — только в памяти.
3. Узкий WebView2SettingsContextFixture задаёт только синтетическое состояние
   settings-документа/nonce и наблюдатель nativeRunScript. Никакого attach,
   navigation, CoreWebView2, browser, TLS/cert trust, профиля или installed path.
   Это тест AppMain glue / account future / model / refresh API; принятие
   web authority, native navigation и DOM явно исключено.
4. Сначала settled read даёт canEdit=false. Освобождение account reply и его
   принятие настоящим pollAccount, затем actual bind дают ровно один refresh;
   read внутри наблюдателя/после вызова даёт canEdit=true. Повторный bind без
   изменений не даёт дополнительных refresh. Logout через существующий
   setAuthSessionToken({}, true), затем bind даёт ровно один refresh и false.
   Начальное уведомление о начальном поколении учитывать отдельно от этих
   переходов; не скрывать лишние вызовы сбросом счётчика во время перехода.
5. RED: убрать только новый вызов из derivative при неизменных остальных входах;
   тест обязан отказать из-за отсутствия refresh, даже если вручную вызванный
   answer уже возвращает true. GREEN обязан проверять именно вызов API и данные.
   Ожидания account worker/процесса ограничены; event освобождается и worker
   завершается при ошибке. Проверка no-files, отсутствие внешних эффектов и
   неизменность byte bindings входят в terminal result.

Такой native test — достаточная минимальная регрессия выбранного AppMain glue;
новый localhost TLS trust test для него не нужен. Весь HTTPS/settings fixture
ради этого запуска повторять не требуется. Установленный UI остаётся отдельным.

## Непокрытая граница: refresh при незавершённом read

В cabinet.js:6291 `if(loading)return loading`, а finally:6329 только сбрасывает
loading. Единственный refresh во время read не запоминается. Это ограничение
не устраняется предлагаемым native observer и не должно превращаться в
утверждение, что все варианты исходного P2 исправлены.

Выполнена только проверка в памяти Node: из существующего
settings-consistency.test.cjs взяты без изменения fixture и shipped notification
JS; добавлены три временных сценария в памяти, файлы не создавались:

| Порядок | Read requests | Итог controls.disabled |
| --- | --- | --- |
| false read завершён, затем refresh и true | 2 | false |
| false read удержан, refresh, затем старый false reply | 1 | true |
| старый true read удержан, logout refresh, затем старый true reply | 1 | false |

Последняя строка показывает устаревшее отображение, не доказанное право
сохранения: реальный owner проверяется отдельно. Native ordering/installed
выполнение этими сценариями не подтверждены.

Для закрытия P2 во всех порядках минимальное дополнительное покрытие уже есть
где разместить: notification-contract режим существующего
apps/server/tests/browser/settings-consistency.test.cjs. Удержать Promise первого
false read, вызвать refresh, отпустить ответ; требовать следующий актуальный read
и enabled без focus/reload. Сейчас этот порядок RED. Возможное исправление
должно помнить один refresh до завершения текущего read с прежними проверками
nonce/generation/disconnect, без таймерного цикла; его реализация в этот GO
не включена. Полный исходный P2 до такого решения остаётся частично открытым.

## Привязка и границы

| Прочитанный файл | SHA-256 |
| --- | --- |
| apps/windows/RecApp/AppMain.cpp | `b7a2ab3ec2128636c0b953a1c79e8a29f74f3b408734853b8bb25ec2ed34927e` |
| apps/windows/RecApp/Web/WebView2Host.cpp | `ab7f676828418e6a688e9b6cab7138b7f85502d51096bd9ae8bf6febeb72e04f` |
| apps/windows/RecApp/Shell/MeetingReminderModel.cpp | `8aab49cfcbe1a7cf4a688f6865fa8e97a975fa630c49e560392721faa4ee53d1` |
| apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js | `7862f2375188a1f3b9a1f5cb6a330028411cfb5ab5709c81b5f73cbab08ce948` |
| apps/server/tests/browser/settings-consistency.test.cjs | `310567b17ee185e86e28b69477ba72ff850a60202d848e069ef483e15376595a` |

Новый патч/native результат ещё не рассмотрены. Никакого общего source/native/
installed PASS, закрытия T104/T109 или миграции T117 этот gate не выдаёт.
Live signin/meetings/storage error — контекст исполнителя, не свидетельство
устранения данного P2. Неудачный process query не означает остановку процесса;
forced cleanup не выполнялся рецензентом. Изменён только этот отчёт. Код,
tasks/checklists, shared agent files, Git, сервер, VM и пользовательские данные
не изменялись.

## SOURCE / Ponytail review замороженного native среза

**SOURCE GO, C0/H0; новых подтверждённых P2 в native срезе и рассмотренных
Build.ps1/Run.ps1 нет.** Разрешены сборка и ограниченный GREEN/RED, не принятие
ещё отсутствующих результатов. Применён ponytail-review: фактический поток,
ошибки, тестовое различение и минимальность без новых зависимостей.

Stage: `/Users/yshishenya/Documents/graf-f200-public458.po8CtB/notification-context-4d1aq44j`.
Независимо сопоставлены 225 source.json entries с текущим checkout и все 225
test-source.json entries с frozen source: mismatches=0. Производный снимок
меняет только AppMain.cpp и GrafWindowsApp.vcxproj. Все 11 sections повторно
извлечены из production/derivative, сравнены побайтово и сверены с bindings;
расхождений нет, включая bindNotificationContext, answerNativeSettings и
refreshSelectedRecording. Генератор не запускался рецензентом.

Обратное удаление двух новых строк AppMain воспроизводит прежний принятый
b7a2ab3ec2128636c0b953a1c79e8a29f74f3b408734853b8bb25ec2ed34927e.
Удаление единственного friend из WebView2Host.h и accountPending getter из
AppMainProblemUiFixture.h также воспроизводит соответствующие pins прежнего
production-package/source.json. Нового production handler/trust/navigation
поведения или account setter нет. Два markers обновляются до refresh.

Новая фикстура использует NativeCapture с generated wire, явным no-HW AEC,
несуществующим root и настоящим account future/pollAccount. Допустимы только
синтетические account GET и workspace fallback; реальные HTTP/device/storage
startup вызовы отсутствуют. Presenter получает пустой NotificationPreferenceStore
без native callbacks. Default problemStore содержит лишь неиспользуемые callbacks:
refreshSelectedRecording возвращается по отсутствующему panel, store не читается.
Не создаются CoreWebView2, browser/profile, tray, TLS/cert objects. Synthetic
host URL/nonce/script observer не является доказательством web authority.

Read сохраняет reply в локальной строке до использования jsonObjectFields;
ссылки на поля не переживают строку. Observer входит повторно в настоящий answer
и bind: recursive refresh ограничен счётчиком и отсутствием новой смены markers.
Initial refresh учитывается отдельно; успешный bind добавляет один, повторные
bind не добавляют, logout добавляет один false read. Closing до terminal даёт
FAIL; finished устанавливается до Window::Close. На отказе event освобождается,
callback снимается, capture shutdown/cancellation и потребление account future
предшествуют destruction. Worker wait ограничен 5s, фаза — 10s; no-files
проверяется фактически. Значение worker_drained относится к account future этого
сценария, не проверяет общий storage/capture lifecycle.

Wrappers не устанавливают пакет и допускают открытый ordinary installed EXE:
отклоняется только точный own-base GrafWindowsApp.exe. Build требует исходный
production-package baseline, накладывает frozen delta, сверяет входы до/после,
удаляет только AppMain.obj и проверяет его свежесть. Run требует terminal build,
точный EXE и manifest; GREEN — OS exit73 плюс точный marker 3 refresh / initial1,
без failure; RED — OS exit3 плюс ровно один context_confirmed_refresh и точный
marker 0/initial0. Crash, пустой log и forced cleanup не принимаются. После run
сверяются EXE, inputs и installed EXE. Own app deadline 30s, reap 5s; только
свой PID/tree. Build deadline 600s с отказом/завершением собственного tree.
Наличие отдельного installed процесса не является installed acceptance.

| Файл | SHA-256 |
| --- | --- |
| AppMain.cpp | `71552b2ae132f5431ed2af8f45ba13d31225d9758fa3cf34df8f8b419721919f` |
| WebView2Host.h | `151cd23d9dc4109cfda7540391dde16d29d0821cf6f1baf2ef48be8dabccb4d7` |
| AppMainProblemUiFixture.h | `55b23d22d4d9a6e6c98de369a4c291471af5ee23e6ea3e7cf80165506fbc79ab` |
| prepare-appmain-problem-ui.mjs | `e6ae25a033a6d9cc274a98c08ef9f8f549896bd8d8b06310de290ab99ad7992a` |
| AppMainNotificationContextUiFixture.h | `5c0be4a47e03a804bb28ee13bc07e9923939b146be2c0991bb02cb72b9d50e59` |
| AppMainNotificationContextUiLaunch.inc | `e48cdf658e057d8d06b61aea948bac0fc1cb606855310ee25a03c72fcf27be1a` |
| stage/source.json | `ed4cb7489b98d38d28f7b89a8ff0547c906aee065721c88342fe2f4214e698d6` |
| stage/test-source.json | `aa05ffbf28daad38d1ef564711ce9aa40bb2d88b6d676ffa7999e67996ed1711` |
| stage/appmain-test-bindings.json | `2875f88174027fe6842cc5116cb27d29a71d0e807aca6d8fadeca71cdf2dbd06` |
| stage/Build.ps1 | `b424b00de1202ce8aa4d4b14f3337c988da2b44f975f949ab516d0b53b0cbddd` |
| stage/Run.ps1 | `6e74d612941fb0073eb9cb6c0981ddce20edd389cef66fb2686b10489be99398` |

Derivative AppMain: `a984861b090b3836086855b2d0eea4fd03eaed81999d2e3905252cac6e26b9df`.
Build/green/red receipts на момент этой сверки отсутствуют. RED builder/restore
ещё не рассмотрены: перед принятием RED нужен точный removal-only контроль,
свежий AppMain object и собственный PE pin. Никакого runtime PASS пока нет.

## Дополнительный scoped requirements/analyze GO: shared refreshPending

**GO, C0/H0 для предложенной ограниченной реализации в существующих T104/T109:**
локальный boolean refreshPending; при loading запомнить refresh; в current
finally снять loading и один раз повторить load; disconnect сбрасывает flag.
Это дополняет native notification и закрывает потерю его доставки при pending
read. Protocol, store/autosave, платформенные подписи и privacy не меняются.
Новых TLS/browser dependencies, polling, retry timer или server API не требуется.
Это requirements GO, не SOURCE GO ещё не изменённого shared JS.

Обязательные условия: повтор только для текущего nonce/generation/root;
старый finally после disconnect/reconnect не снимает loading нового контекста
и не запускает старый read. Несколько refresh во время одного read объединяются
в один follow-up. Сохранить existing autosave draft/failed-save/preview поведение;
ошибка чтения не выдаётся за successful save. Initial connect уже вызывает load
и refresh, поэтому начальные чтения надо дождаться до отдельной held-read фазы;
добавочный начальный read сам по себе не является бесконечным циклом.

Прочитан внешний notification-refresh-test.txt и shared-qualified-red.log.
settings-consistency-proposed.cjs отличается от текущего real test ровно вставкой
этого блока (проверено обратным удалением). Тест использует actual shipped JS и
realQueue, ждёт baseline false, удерживает следующий старый false reply,
посылает 3 refresh после смены синтетического контекста, требует ровно один
follow-up read, enabled controls и прежний nonce/read action. Это содержательный
RED: 37 PASS / 1 FAIL точно на expected before+2, actual 2 versus expected 3.
Первый shared-red.log содержит wrapper SyntaxError повторного module declaration;
это не результат тестового RED и он не принят вместо qualified run.

После реализации нужны GREEN этого теста и существующего contract набора,
плюс delayed refresh→disconnect и delayed refresh→new nonce: поздний old reply
не восстанавливает старый UI и не создаёт лишнего read старого контекста.
Existing stale-response cases остаются, но новый pending flag проверяется
именно с запрошенным повтором. Native GREEN/RED отдельно подтверждает AppMain
trigger: shared initial connect не может заменить его отсутствие.

Pins внешнего proposed test/RED: notification-refresh-test.txt
`062b7e490b8c57707033181c70182c8080ca4d0d735efef2b9958d3b5732dc9b`;
settings-consistency-proposed.cjs
`70c9067d1d0873feb5d3c57fc8c96280fa88d945a5732c2c20b74592f1ce6182`;
shared-qualified-red.log
`4703be8134c983c9582c66ac7cdca80ca55190302871586c31500da97af9a286`.
Код, wrappers, JS/test files и установленное приложение рецензентом не изменялись;
новых сборок/VM/тестовых запусков в этом SOURCE review не выполнялось.

## SOURCE / Ponytail review фактической shared дельты

**SCOPED SOURCE GO, C0/H0; новых подтверждённых P2 нет** для двух файлов:
cabinet.js и settings-consistency.test.cjs. Вместе с ранее рассмотренным
AppMain trigger они реализуют согласованный путь устранения P2; закрытие
дефекта по выполнению ещё требует соответствующих GREEN/RED результатов.
Нативную сборку и запущенный main contract рецензент не трогал.

Независимое обратное применение четырёх локальных изменений JS восстановило
точный прежний SHA-256
`7862f2375188a1f3b9a1f5cb6a330028411cfb5ab5709c81b5f73cbab08ce948`.
Удаление первого нового test и следующего цикла из трёх delayed cases
восстановило точный прежний SHA-256 тестового файла
`310567b17ee185e86e28b69477ba72ff850a60202d848e069ef483e15376595a`.
Иных изменений общего JS, прежней fixture, realQueue или старых cases нет.

Проверен полный связанный flow load/post/render/disconnect и четыре новые
проверки. При active loading запросы refresh устанавливают один boolean;
после завершения только current-document finally снимает loading, сбрасывает
flag до вызова и запускает один follow-up load. Сам load не создаёт refresh
event и не вооружает flag, поэтому без нового внешнего события повторный
цикл не возникает. Initial connect может дать дополнительный объединённый
read; baseline нового теста завершается до отдельной проверяемой фазы.

Disconnect сбрасывает pending flag, queue/snapshot/loading и меняет generation.
После new nonce либо same nonce с новым generation старый post отклоняется
через current(owner,epoch); его catch/finally не меняют новый UI/loading/flag.
Действующие root.isConnected, nonce и generation проверки сохранены.
Нет нового протокола, polling, timeout/retry цикла, native authority или
permission поведения. Existing autosave draft/flush и preview ветви сохранены;
read сам не порождает запись предпочтений. Flag находится в существующем
экземпляре страницы; глобального сервиса/нового состояния хранения нет.

Первый новый тест использует realQueue и snapshot до await: удержанный reply
действительно остаётся старым false, хотя native state уже true. После трёх
refresh проверяются ровно один дополнительный read, canEdit через доступность
controls и ожидаемый read/nonce. Три delayed cases сначала вооружают pending
refresh, затем делают disconnect/new nonce/same nonce reconnect; поздний
старый reply не должен добавлять запросы либо менять текущую доступность.
Захваченный reply не перечитывается из изменяемого state после await; cleanup
освобождает held Promise и disconnect. Это actual JS/realQueue regression,
не installed UI или WebView2 authority acceptance.

По Ponytail отдельного безопасного упрощения не найдено: один boolean
переиспользует существующие Promise/current/disconnect, без новых helper,
очереди, зависимостей или копии production алгоритма. Существенное исправление
не заменено тестом, который повторяет четыре строки: проверяется наблюдаемое
число запросов и состояние интерфейса; прежний qualified RED сохранён отдельно.

| Файл | Точный SHA-256 SOURCE GO |
| --- | --- |
| apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js | `6c4dca3b613e215b5c8dc1dbae2d039a195f562ae7836d13d02ab6b9b344ee8f` |
| apps/server/tests/browser/settings-consistency.test.cjs | `d4fccecccf96bd276497746c55aff431062c61954209b6dc6ef9d6caa1f52fdc` |

Предыдущий native SOURCE/wrapper GO сохраняется для своих pins. Новые
shared GREEN, native build/run и полный исходный P2 не объявлены принятыми
до сверки terminal evidence. Browser/macOS/installed runtime, отсутствие
storage error, capture/migration T117 и вся F200 этим SOURCE GO не принимаются.
Исправление остаётся существующим T104/T109; задачи/checklists не закрыты.
Изменён только этот отчёт, код/тесты/сервер/VM/Git рецензентом не менялись.

## SOURCE GO: native RED overlay и восстановление GREEN

**C0/H0, SOURCE GO для точных Build-Red.ps1 и Restore-Green.ps1 ниже.**
Сверены wrappers, red-control.json, red-test-source.json и фактический diff
overlay. RED ещё не выполнялся рецензентом; его результат не принят.

red-source содержит ровно один AppMain.cpp. Его diff относительно frozen
GREEN derivative удаляет только единственный вызов refreshNativeSettings
в bindNotificationContext; комментарий и все остальные bytes сохраняются.
Manifest RED содержит 225 entries, отличается от GREEN ровно этим файлом;
композиция GREEN source + однофайловый RED overlay совпала со всеми 225 pins.
GREEN derivative SHA a984861b090b3836086855b2d0eea4fd03eaed81999d2e3905252cac6e26b9df;
RED derivative SHA f041143dbdb04a6255518150f753277ccec2c9e2eac741294817ee348387f51a.

Build-Red проверяет полный GREEN base и отсутствие own-base EXE/build,
сверяет фактический GREEN EXE с build receipt, сохраняет его, заменяет только
AppMain и обязательно удаляет AppMain.obj перед MSBuild. RED inputs до/после,
свежесть AppMain.obj, object/PE/runtime hashes фиксируются; build_exit0 сам
по себе не является native RED. Сохранение mtime копируемого source не может
оставить старый AppMain.obj, поскольку его отсутствие принудительно обеспечено.

Restore проверяет полный RED base, разрешает ровно один changed input AppMain,
сверяет backup GREEN EXE с build receipt, возвращает GREEN AppMain и EXE,
проверяет все 225 GREEN inputs и PE. Затем удаляет только собственный RED
AppMain.obj и stage/green.exe; состояние их отсутствия записывается.
Скрипт не удаляет base/source directories, installed package или пользовательские
данные и не завершает открытое обычное installed приложение. Общий app_processes
в restore — наблюдение, не требование нуля при разрешённом installed процессе.
Installed EXE hash и фактическую остановку test process подтверждает отдельный
Run/postflight; restore receipt с одной version/status их не заменяет.

Порядок single-owner: дождаться завершения GREEN Run.ps1 целиком и успешной
terminal green-result.json, затем Build-Red → RED Run → Restore. Проверка
отсутствия child EXE сама по себе не доказывает, что parent GREEN Run закончил
post-source checks: параллельно менять base нельзя. Это условие исполнения,
не запрос нового подтверждения и не требование повторного GREEN до RED.

Прочитан текущий build-result.json: terminal, build_exit0, 225/225,
PE `62ce438210d69d8313cefb63f7ad349f43dc036adb644fa782a460892962086d`;
это build evidence, не принятие ещё не рассмотренного native run.

| Артефакт stage | SHA-256 |
| --- | --- |
| Build-Red.ps1 | `23b4e56efc5cf25db9788d5df15c994c2f6d8346c305e6b2b8ab63b83f54c072` |
| Restore-Green.ps1 | `cfb83451caa777708169e4f0aece1a67d832f183ea4ab9e073c9911a91af155a` |
| red-control.json | `73264d97ea17d6ba0ba6184fba379a993a9c79ec4eb98503dce35b92941cdc4f` |
| red-test-source.json | `1ed40695568a7695e101ed236167e93ca24ac895428e06e2e9ffd966dbce4b91` |
| build-result.json | `404594890023d8880841c2bfdcb9888656715061ec13a7e3f57b38cec6bdd04f` |

Shared 41/41, executor transcription receipt и Chromium/WebKit combobox
результаты сообщены исполнителем; этим SOURCE review их terminal evidence
не принималась. Browser combobox suite не выдаётся за delayed-DOM regression.
Новых исполнений/мутаций base рецензент не делал; изменён только этот отчёт.

### Подтверждение GO после завершения GREEN

После compaction повторно сверены SHA-256 обоих wrappers, red-control.json
и red-test-source.json: они точно совпадают с таблицей SOURCE GO выше.
**C0/H0, SOURCE GO сохраняется для этих wrappers и однофайлового inverse
control; препятствий к последовательному RED → Restore по рассмотренному
порядку нет.** Это разрешение по результатам проверки исходников, а не
утверждение об успешном выполнении RED или восстановления.

Непосредственно прочитана завершённая green-result.json, SHA-256
`5123879a0a811d9ad5da198adb64f4323e9aa07e0b06ca82fb6ce3df70ae8455`:
terminal=true, mode=green, app_exit=73, native_pass=true, app_stopped=true,
source_files=225/post_source_files=225, PE
`62ce438210d69d8313cefb63f7ad349f43dc036adb644fa782a460892962086d`,
installed_version=0.1.0.15, installed_exe_unchanged=true.
В green-ui.err независимо найден точный marker:
`CONTEXT_UI terminal=1 refreshes=3 initial=1 no_files=1 worker_drained=1 browser_started=0 exit=73`.
Для уже проверенного Run эти квитанции подтверждают scoped native GREEN;
worker_drained относится к account future этой fixture. Installed acceptance,
реальный DOM, audio и вся F200 из этого результата не следуют.

Условие одного владельца остаётся: менять base после полного завершения
родительского GREEN Run, а не только после выхода его child process.
Terminal review RED/Restore будет отдельным после появления их квитанций.
Рецензент не запускал wrappers/VM/тесты и не менял ничего кроме этого отчёта.

## Terminal RED/Restore и SOURCE GO повторного GREEN

**C0/H0 в рассмотренном source/evidence срезе. Native GREEN и причинный RED
квалифицированы; восстановление GREEN source/EXE подтверждено отдельной
квитанцией. Повторный native запуск восстановленного GREEN пока не принят.**

Повторная независимая сверка source.json с checkout и test-source.json с
frozen source дала 225/225 без несовпадений в каждом случае. Их pins и pin
appmain-test-bindings.json совпадают с ранее рассмотренными. Между GREEN/RED
manifests изменён только AppMain.cpp. Shared JS и test pins также совпали
с прежним SOURCE GO; актуальный combobox test совпал с provenance.

Прочитаны red-build-result.json, red-result.json и весь red-ui.err. Сборка
terminal/build_exit0/225→225; RED PE
`a91d1287827c3fe4d4df4f85009251219c429e00a7582b4a88e12306c9cb434d`.
AppMain object изменился, WebView2Host object и три runtime DLL совпадают
с GREEN build. Run завершён с app_exit3/native_pass=false/red_rejected=true,
app_stopped=true/225→225/installed_exe_unchanged=true. Журнал содержит ровно
две строки: единственную `PROBLEM_UI failure=context_confirmed_refresh` и
`CONTEXT_UI terminal=1 refreshes=0 initial=0 no_files=1 worker_drained=1 browser_started=0 exit=3`.
Это meaningful inverse control именно нового native trigger, не crash либо
успех только по build exit0. Предыдущий GREEN проверяет три refresh, initial1.

restore-green.json terminal, без failure: 225 GREEN inputs, PE
`62ce438210d69d8313cefb63f7ad349f43dc036adb644fa782a460892962086d`,
red_object_absent=true/temporary_exe_copy_absent=true, owned_browser_processes0,
installed0.1.0.15/Ok. app_processes1 допустим: обычное installed приложение
оставлено пользователю. Транзитный prl Invalidargument255 сообщён исполнителем;
не квалифицируется как crash приложения или отдельный успешный restore.
Наличие terminal receipt снимает ожидание восстановления, но не заменяет
последующий runtime восстановленного GREEN.

Фактический Run-Restored.ps1 рассмотрен целиком через diff с pin Run.ps1.
Ровно четыре места меняют имена receipt/stdout/stderr/readback на restored-
prefix; входные source/build pins, Mode=green по умолчанию, проверки результата,
deadline/owned cleanup и installed hash сохранены. **SOURCE GO** для SHA-256
`aca29abb008e589c6b0c819d699634764a816f13b234a2da8e196e5d3a42967b`.
Запуск допустим после terminal Restore и отсутствия иных владельцев base;
повторное использование нового receipt по-прежнему отвергается до try.

Shared 41/41 принимается как явно подписанное свидетельство исполнителя:
shared-contract-result.json ссылается на terminal tool5b94ad и честно сообщает,
что отдельный raw log не сохранён. Команда, exit0, tests41/pass41/fail0 и оба
source pins согласованы. Независимо восстановить полный вывод41 cases из этой
квитанции нельзя; новый запуск не выполнялся и не требуется этим review.
Сохранённый meaningful shared RED и ошибка первой wrapper попытки сохраняют
свои ранее описанные границы; ошибка module не выдаётся за regression RED.

Полностью прочитаны Chromium/WebKit combobox logs: оба содержат итоговый PASS
coverage/settings/filter/bulk/selection/keyboard/IME/reset/disabled/catalog,
600 options и narrow layout. Provenance описывает единственную Python/Jinja
подстановку во внешней копии. Это сохранённые браузерные результаты старого
набора, не delayed notification DOM или installed WebView2 acceptance;
саму временную копию и окружение рецензент заново не аттестовал.

validation-2026-11-03-notification-context-refresh.md прочитан и согласован
с этими результатами/ограничениями. Его ожидание Restore относится к снимку
до новой квитанции; этот reviewer append фиксирует уже подтверждённое
восстановление, не меняя чужой документ. T104/T109 целиком не закрываются.

| Новое свидетельство | SHA-256 |
| --- | --- |
| red-build-result.json | `9265931d25c344019f47e21fed4b4348ec78445cd289aaf97c720ae495d0285a` |
| red-result.json | `300111a656a3b4d6497b0c6c5aa09dda5fe3dbdc1778a1b1f9eb8e0bb80534a2` |
| red-ui.err | `21b8670eca67b98f80c5a90c81a288fb54dce3e82d2b39215cbfb468b5e9e1b3` |
| restore-green.json | `09ca64b7a30c16e6132041dc1bba04b2198b5e9611eb7f566124ab220d111e4b` |
| shared-contract-result.json | `7f3341a8c7ab3c503a6c20d8f9b7f06f242953e343aee55897b4f9d2466b1fa7` |
| chromium-combobox.log | `b2ae1ee753b987779dd903dd504098e03dd06ac54b49bbeabeb20a8d0e00dcbb` |
| webkit-combobox.log | `f3b42b06747de6417fc639cabb1a7a7ea551817efa29c7a714cbe93330a216da` |
| combobox-provenance.json | `984631bf93e2c095cce91fd14d297668b421b75a06f8fbd80fac9639fdb888ad` |

Проверка read-only кроме этого report; VM, wrappers, тесты, код, tasks,
checklists и Git не выполнялись/не менялись рецензентом.
