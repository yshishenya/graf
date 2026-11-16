# T119: независимая проверка требований календарного подключения

Дата: 2026-10-02. **Request Changes — gate FAIL только в области T119.**
Режим: read-only анализ высокорискового среза, затем разрешённая запись отчёта
и трёх reviewer-owned отметок. Не повторная проверка T115 и не разрешение кода.
Основа: `HEAD 99b00a579c24b50e320465b69d9a296038bc544d`,
`origin/master 721b5125d799ea798a4af0b3625e18d3c1109039`.
Проверены окончательные байты после дополнений deadline/preflight; T119 не менялся.

## Замечания

**C1 — HIGH, неоднозначное обязательное поведение native/browser.**
Bridge §10:439–443 одновременно выбирает Zoom/Teams по HTTPS host/path, «не из
provider_family», и направляет «unknown provider» только в браузер. Серверный
`api/calendar.py:495–499` возвращает provider_family из extras календарного события
с default `"calendar"`; `api/schemas.py:293–296` определяет обычную строку, не enum
приложения встречи. Mac `CalendarMeetingOpener.swift:80–101,113–121` выбирает
Zoom/Teams/Телемост по URL, а `DesktopUploadClient.swift:1405–1412` вообще не читает
provider_family. Поэтому разрешённый ответ `provider_family="calendar"` со
ссылкой `https://zoom.us/j/12345678901` допускает два несовместимых прочтения:
Zoom по адресу или browser-only по неизвестному семейству. Это контрпример
требованиям, не утверждение об исполнении Windows-кода.
Нужно явно определить unknown как отсутствие допустимого host/path приложения,
а не неизвестный источник календаря; provider_family не должен подменять выбор
по URL. Добавить такой случай в planned fake-resolver matrix. CHK006 requirements
снят до уточнения; новые API или серверные изменения для решения не требуются.

**C2 — MEDIUM, устаревшая reviewer-owned поверхность протокола.**
`security.md:25–26` требует закрытые шесть запросов и полный старый перечень
ответов, тогда как `spec.md:425–435`, bridge:119,378–403 и data-model:274–291
добавляют седьмой запрос/ответ. Прежние `[X]` не подтверждают новый состав.
CHK008/009 сняты, формулировки и история не переписаны. Обновить критерии для
`calendar_join`/`calendar_join_reply`, сохранив exact payload/envelope, main route,
UUID/nonce/replay/current checks, отсутствие URL/record authority, остальные
шесть команд и прежние ограничения. Затем повторить независимую проверку.
Это не требование вернуть старые aliases или завершить runtime tests до review.

**L1 — открытая проверка native association, не новый аппаратный gate дизайна.**
Bridge:440–453, plan:1186–1191, research:2438–2439 правильно оставляют фактическое
открытие Windows-клиентов неподтверждённым. Для Телемоста кандидат — HTTPS:
двухаргументный QueryUriSupportAsync сообщает доступность какого-либо обработчика,
не личность Телемоста; браузер тоже может обработать HTTPS. Available/true нельзя
использовать как доказательство installed-native parity. В будущей проверке
quickstart:439–449 различать передачу URI и выбор нужного клиента, в том
числе установленный, но не назначенный обработчиком Телемост. Неизвестность
не разрешает выдумать scheme/EXE и не заменяется PASS browser-only.

## Что достаточно определено в требованиях

- Запрос: envelope v1, calendar_join, ровно action/eventId/requestId, оба UUID,
  approved attached main RouteKind::meetings, точный list/inbox набор; остальные
  маршруты/frame запрещены. Trusted capture-phase click подавляет standalone
  handler через preventDefault; до handshake pending отсутствует (bridge:378–395;
  Windows route policy:300–304; master calendar-series.js:23–30).
- Корректный trusted not-ready/busy запрос получает terminal cancelled; malformed
  не отвечает. Reply связывает nonce/request/pending; terminal возвращает действие,
  URL/private content не передаётся. Invalidation не отвечает новому документу.
- Один busy owner для cabinet/card/menu через resolver/launcher/dialog; 15s whole
  resolver deadline, worker lease до фактического окончания; старый callback не
  освобождает новую операцию. HTMX same UUID сохраняет действие, removal/replacement
  отменяет; origin/owner/workspace/token/document/operation перепроверяются.
- Resolver остаётся существующим authenticated GET, HTTP200 без redirects, matching
  event UUID, bounded strict JSON; 401/404/503/network/malformed различаются.
  Backend, calendar credentials и standalone browser business logic не копируются.
- URL policy ссылается на неизменный master corpus (141 случай: 66 allow/75 deny),
  percent/IDNA/numeric IPv4/mapped IPv6; query/fragment/valid port сохраняются.
  Corpus отсутствует в старом HEAD рабочей копии: прочитан через git show master,
  это reference, не уже запущенная Windows regression и не новая same-origin policy.
- Native failure требует отдельного явного выбора браузера и свежего resolver; browser
  IgnoreAppUriHandlers=true не повторяет native association. Уже OS-dispatched URI
  не отзывается задним числом, но stale completion не меняет новое UI/не делает Record.
  Join-and-record только native → handed_off → current → capture readiness.
- Напоминание закрывается только после handoff; explicit failure retention ≤5min
  не продлевается фоновым отказом; auth/404/context/expiry снимают действие.
  Доступность/состояния и обязательная последующая installed matrix определены.

## Все 112 критериев: перечитаны и проверены на воздействие T119

| Чек-лист | Прочитанные IDs | Checked / unchecked | Влияние и основание |
|---|---|---:|---|
| requirements | CHK001–022 | 21 / 1 | CHK006: C1; 001–005,007,009,013,016,019–022 сверены с US2/FR002–006/SC002,006,009, T119 и §10; прочие без регрессии |
| audio-capture | CHK001–024 | 24 / 0 | Все сохранены: §10 не меняет clocks/AEC/writer; 002,023,024 сверены с запретом web Record и позднего native Record |
| advanced-routing | CHK001–014 | 14 / 0 | Все без воздействия: URI opener не audio routing, process capture/driver/service не добавляются |
| security | CHK001–027 | 25 / 2 | CHK008/009: C2; 001–007,010–011,014,017–018,021–025 сверены с envelope/route/egress/cancel; storage/supply-chain/target prefs не меняются |
| ux | CHK001–025 (включая отдельно расположенные 023–025) | 25 / 0 | 001–002,004,014–020,022 сверены с parity, loading/retry/accessibility и native controls; 003,005–013,021,023–025 без регрессии |
| **Всего** | **112 уникальных пунктов по пяти файлам** | **109 / 3** | **Не унаследованный PASS; фактические отметки после записи перечитаны** |

Отметки сохранённых пунктов означают отсутствие регрессии качества требований
от T119; не новую полную приёмку часов, storage/billing, оборудования или приложения.
FR002/005/006/015 и SC002/006/009 имеют явного владельца T119 с test-first порядком
в plan:1166–1174; новые unmapped tasks/constitution violations в этом срезе не найдены.
Проверка по code-reviewer + speckit-analyze; analyze hooks disabled, YAML прочитан.
Prerequisite выполнен с поддерживаемыми --require-tasks --include-tasks;
--require-spec из шаблона отсутствует в установленном script, spec прочитан отдельно.

## Точный снимок доказательств (SHA-256)

| Артефакт | SHA-256 |
|---|---|
| spec.md | 1eca85ec760ea8bfe7990e0f4e9c909d0b7a8b74b11012fb2e12c5dcbd011e23 |
| plan.md | ec6972fd594460fc2a7a6775e6f871a442a906d6211dd741bcd0cebf562fa167 |
| tasks.md (включая неизменный T119) | 45641d615923b4c049482397e90e6ce765255b8ba7467f2d867cd4c8c7e27d50 |
| data-model.md | 9883413023579202561dc214e0ce96b817c21a29a2e8af02717042dcb7a5429a |
| research.md | 81d5eb5d1dc62fdcfe8293e3ef406f9df754417908ff07dfc37afde7730eab42 |
| quickstart.md | 3b540825232d17d41ea66977d4a77c4e5236245a16526fbac41570bf3a13df90 |
| parity-matrix.md | 72c9b6556a4d18a3b6549322b44f02ff15959d8c2eb90f00d4a982ed280a24ab |
| contracts/windows-native-web-bridge.md | 246528c3ea175bacaa500d68851331eecb92aabff6076ff721177f3b000cf1b0 |
| constitution.md | d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859 |
| master F279 contracts/calendar.md | c635e11a0e757249743f4e8291929e710e410bbd988f412d1f59766dddbf7f3e |
| master EmbeddedCabinetCalendarJoinBridge.swift | 3932bf4f37d6fab48537c91c35d03161534154638612184d16bd9b850a6a8cd5 |
| master CalendarMeetingOpener.swift | 05eef2ba53c10913747b314d3eca0aff8a29303c055189c58d2083c677e08652 |
| master api/calendar.py | e84227a31233c4868a6baee87303dce2170ffa8ed442d330fe0c57281c09bd2d |
| master api/schemas.py | a2391756584859207cc60da70424354a8a6fcef660351b886fc09331cd05476a |
| master host corpus | 7c6731fe293226eb1033acb2c5acc930897134395e8d67ebc29cca7ba17757d1 |
| checklists/requirements.md после review | a2b0b45b6fee2f9d4f508942fbf4eea04b74476bd48e384385d9097d51c20150 |
| checklists/audio-capture.md (не менялся) | 4471fb8dc0fa82851c57c3c5e0bf49f4a5f94d838c082998488ecbdc15280cfd |
| checklists/advanced-routing.md (не менялся) | bd88f0588e806b16e93f7031645ed56384245343d20c7c41ab610a532620da12 |
| checklists/security.md после review | 8cd7b35baeb9a76cb949c32002ee2887c0572e7bf1fcd8dbd73a71c91db8a62b |
| checklists/ux.md (не менялся) | 1a5a28f7226d7fc25bafdb8239b3d4bea2aeae0d4aad969eb89b45ec5b855801 |

Microsoft primary references: [QueryUriSupportAsync](https://learn.microsoft.com/en-us/uwp/api/windows.system.launcher.queryurisupportasync?view=winrt-26100),
[LaunchUriAsync](https://learn.microsoft.com/en-us/uwp/api/windows.system.launcher.launchuriasync),
[IgnoreAppUriHandlers](https://raw.githubusercontent.com/MicrosoftDocs/winrt-api/docs/windows.system/launcheroptions_ignoreappurihandlers.md).
API documentation checked, not executed. Required guidance/constitution and all
112 criteria read personally; earlier T115 report not used as substitute.

Следующий шаг: уточнение C1 основным агентом, актуализация reviewer-owned C2 и
новая узкая проверка exact bytes. Затем отдельные analyze/issue-sync gates.
T119, T097/T063 и общий clock/F279/billing/storage gate не закрыты.
Build/VM/audio/GitHub/Git mutation не выполнялись; чужие изменения сохранены.

## Повторная независимая проверка — 2026-10-02, окончательные C1/C2/L1

**Approved — gate PASS только для качества требований C1/C2/L1 в срезе T119.**
Первоначальный Request Changes выше сохранён как история. Это не утверждение
готовности общего T119 design/реализации: технический способ гарантированного
native-запуска Телемоста остаётся неизвестным и НЕ получает PASS.
Новые блокирующие замечания к проверенным формулировкам не обнаружены.

- **C1 CLOSED:** bridge §10:439–448 и plan:1192–1198 выбирают кандидата только
  по validated host/path. provider_family — источник календаря, не app choice.
  calendar/unknown + Zoom URL и zoom + example.org явно назначены fake resolver
  регрессиям (quickstart:438–441). Фраза об unknown provider:411 читается с этим
  точным правилом: неизвестное семейство само не разрешает custom scheme, но
  не запрещает кандидат, независимо подтверждённый допустимым host/path.
- **C2 CLOSED:** security CHK008/009:25–26 теперь описывают ровно семь запросов
  и отдельный calendar_join_reply. Все шесть прежних запросов и native_ready/
  local_recordings/native_reply/deletion outcomes сохранены, как и envelope,
  текущий source/route/nonce, schema/size/depth/replay, native finalization,
  локальные полномочия/удаление, запреты aliases/произвольных путей/процессов/
  секретов/capture authority. Добавлены exact UUID/action/main route, busy и
  terminal not-ready, текущие operation fences, безопасные состояния/reasons
  reply, снятие pending и handed_off != вход. Новых CHK IDs нет.
- **L1 REQUIREMENT CLARIFIED / NATIVE TECHNICAL PROOF OPEN:** quickstart:459–462
  требует наблюдать именно Телемост при selected/nonselected HTTPS handler;
  Available/true не identity evidence, браузер не засчитывается как клиент.
  Сообщённые основным агентом registry/signature сведения в этой проверке не
  воспроизводились и не входят в frozen bytes: они не подтверждают URI format
  или native launch. Не добавлены новые критерии, scheme/EXE discovery или
  разрешение заменить установленный клиент браузером.

### Все 112 критериев и фактические отметки после повторной проверки

Лично перечитаны все пункты пяти файлов; оценено только воздействие нового
среза, не повторная полная приёмка Feature 200.

| Чек-лист | Прочитанные IDs | Checked / unchecked | Результат воздействия T119 |
|---|---|---:|---|
| requirements | CHK001–022 | 22 / 0 | CHK006 восстановлен по C1; 001–005,007,009,013,016,019–022 сверены с US2/FR002–006/SC002,006,009, §10 и T119; остальные без регрессии |
| audio-capture | CHK001–024 | 24 / 0 | 002,023,024 сохраняют readiness/Stop и отсутствие web/late Record; clocks/AEC/writer не меняются |
| advanced-routing | CHK001–014 | 14 / 0 | URI opener не audio routing; ни process capture, ни driver/service/privileged source не добавлены |
| security | CHK001–027 | 27 / 0 | 008/009 актуализированы; 001–007,010–011,014,017–018,021–025 сохраняют route/envelope/egress/cancel/технические условия; остальные без регрессии |
| ux | CHK001–025 | 25 / 0 | Включая 023–025: 001–002,004,014–020,022 сверены с parity/loading/retry/accessibility/controls; остальные без регрессии |
| **Всего** | **112, IDs уникальны внутри каждого файла** | **112 / 0** | **Проверены фактические отметки, не унаследованный PASS реализации** |

Изменены только requirements CHK006, security CHK008/009 и append-only записи
этих двух чек-листов/отчёта. Формулировки остальных 109 пунктов не менялись.
Прежние исторические результаты сохранены. Шаблон CHK006 security по-прежнему
не требует общий envelope у всех native-to-web display messages; новый reply
имеет отдельную форму §10, не новое полномочие или acknowledgement truth.

### Окончательный снимок SHA-256

| Артефакт | SHA-256 |
|---|---|
| spec.md | 1eca85ec760ea8bfe7990e0f4e9c909d0b7a8b74b11012fb2e12c5dcbd011e23 |
| plan.md | 018e70f802329463184f6c78f7032fc9b40b635a91d59c65cf7616c3c3c4233e |
| tasks.md | 45641d615923b4c049482397e90e6ce765255b8ba7467f2d867cd4c8c7e27d50 |
| data-model.md | 9883413023579202561dc214e0ce96b817c21a29a2e8af02717042dcb7a5429a |
| research.md | 81d5eb5d1dc62fdcfe8293e3ef406f9df754417908ff07dfc37afde7730eab42 |
| quickstart.md | 82aaf274bafc68e5d336bfbb35b6bd5f542dc035c0048303923dd22b14bf6aab |
| parity-matrix.md | 72c9b6556a4d18a3b6549322b44f02ff15959d8c2eb90f00d4a982ed280a24ab |
| contracts/windows-native-web-bridge.md | 59ae620f00e7c060ed362b20988db4b39edc6258d5d6064516d676679bd1db6e |
| checklists/requirements.md | 91fecd3ca4c79eba15faa3543fce18f8d5db1eb7a6664701c683c460d0d5bc55 |
| checklists/audio-capture.md | 4471fb8dc0fa82851c57c3c5e0bf49f4a5f94d838c082998488ecbdc15280cfd |
| checklists/advanced-routing.md | bd88f0588e806b16e93f7031645ed56384245343d20c7c41ab610a532620da12 |
| checklists/security.md | 50a47dd3ff25223665a77dae3ba163c8732fe52a9e7705a019544be563d817f9 |
| checklists/ux.md | 1a5a28f7226d7fc25bafdb8239b3d4bea2aeae0d4aad969eb89b45ec5b855801 |
| constitution | d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859 |

Source anchor из .specify/feature.json:
99b00a579c24b50e320465b69d9a296038bc544d; master comparison
721b5125d799ea798a4af0b3625e18d3c1109039 — ранее проверенные источники из
первого отчёта, не новая проверка HEAD/remote этим раундом. Окончательные bytes
spec/plan/tasks/model/research/quickstart/parity/bridge и constitution проверены
по файловым hashes; task SHA и смысл T119 не изменены. Предыдущий полный отчёт
до этого дополнения имел SHA-256
5fadba64ea675acbb888ec75a38f221e5deea7698f619bf06d944e0c8d84436b;
его байтовый префикс сохранён.

Применены code-reviewer и speckit-analyze. Required guidance/constitution уже
прочитаны в этой независимой проверке; все 112 критериев перечитаны заново.
Analyze hooks disabled. По прямому запрету Git в этом раунде prerequisite
script (использует Git) не запускался: активная feature, наличие и содержимое
spec/plan/tasks проверены чтением .specify/feature.json и файлов. Это явная
граница проверки, не доказательство свежего общего analyze/issue sync.

**Дальше:** отдельные актуальный scoped analyze/issue sync и решение технической
native association Телемоста, затем код/испытания по разрешённым gates. Это
дополнение закрывает stale reviewer C1/C2, не T119/T097/T063 и не общий
clock/storage/billing gate. Продукт, spec/plan/tasks/contracts не редактировались;
build/VM/audio/Git/GitHub не выполнялись. Внешние клиенты/релиз не одобрены.

### Заключительная сверка байтов C1 — 2026-10-02

После записи результата основной агент уточнил bridge:411–412:
«provider_family сам по себе не разрешает и не запрещает custom scheme:
кандидат определяется только validated HTTPS host/path ниже».
Перечитаны эта строка с resolver:407–418 и правила выбора:440–449. Формулировка
однозначна и согласована с C1; новых полномочий/кандидатов/требований нет.
Approved / gate PASS качества требований C1/C2/L1 сохранён; остальные 112
оценок не переигрывались без регрессии, все пять checklist hashes неизменны.

Окончательный contracts/windows-native-web-bridge.md SHA-256:
127356a14df140364ce619554bcc42cab03286262065afa40c1fcdb73ac51ff4.
Этот hash заменяет 59ae620f00e7c060ed362b20988db4b39edc6258d5d6064516d676679bd1db6e
из предыдущего снимка только для окончательных байтов bridge. Старое прочтение
строки:411 в дополнении выше — историческое; актуальны прямое правило:411–412
и сдвинутые на одну строку правила:440–449. Spec/plan/tasks/model/research/
quickstart/parity и все пять чек-листов повторно сверены по hashes и не изменились;
registry observation в research не появилась. Префикс исходного отчёта сохранён.
Техническая неизвестность native URI/запуска Телемоста остаётся OPEN, не PASS;
общие clock/storage/billing и реализация/выпуск не одобрены. Без Git/VM/audio/GitHub.
