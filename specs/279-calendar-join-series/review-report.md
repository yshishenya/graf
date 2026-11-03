# F279 — независимое ревью требований

Дата: 2026-09-28. Область: reviewer-owned UX/security checklist, включая повторную проверку с готовым tasks.md перед реализацией. Проверено качество требований, не работа реализации. Процесс: high-risk product area, полный Spec Kit.

## Результат

**PASS: UX 8/8, security 8/8; всего 16 checked, 0 unchecked.**

Повторное независимое ревью подтвердило устранение обоих первоначальных пробелов:

1. UX CHK002: `spec.md` «Детерминированный выбор даты серии» и quickstart S09 определяют текущий интервал, приоритет и порядок текущих/будущих событий, разрешение совпадений UUID и доступ к другим датам. Выбранная дата явно видна; join использует именно её.
2. Security CHK007: `contracts/calendar.md` «Ограничения истории и курсора» и quickstart S10 определяют 366 суток, limit 1..50, cursor до 2048 ASCII, подпись/TTL/контекст и безопасный отказ 422.

Остальные 14 пунктов повторно сопоставлены с актуальными артефактами: основания PASS сохраняются. Встроенный `checklists/requirements.md` правильно проверяет наличие сценариев SC, а не ещё не выполненную runtime-приёмку; reviewer его не изменял.

Первый проход дал 14/16 и два открытых замечания; настоящий повторный проход заменяет этот предварительный результат. Подробные доказательства каждого пункта приведены в `checklists/ux.md` и `checklists/security.md`. Готовые tasks и analyze впоследствии прочитаны; результат повторной проверки ниже. Runtime-проверка здесь не проводилась.

## Повторная проверка с tasks перед реализацией

`tasks.md` T001–T008 и актуальные spec/plan/custom checklist прочитаны. Итог **PASS 16/16** сохраняется; блокирующих пробелов требований в данном reviewer gate нет.

| Область checklist | Задачи и требуемое доказательство |
|---|---|
| UX CHK001–002,005 | T002, T005–T007; identity, отдельные экземпляры/записи, детерминированный выбор, S01–S10 |
| UX CHK003–004 | T003–T004; локальные состояния, сохранение экрана, одна попытка, stale-session отказ |
| UX CHK006 | T006, T008; приватность HTML, клавиатура/VoiceOver, темы и узкое окно |
| UX CHK007–008 | T004, T008; самостоятельная реализация/происхождение, native-приложения, GRAF Dev, SC-001–007 |
| Security CHK001,005–007 | T002–T003, T005–T007; owner/identity/access до группировки, совместимость v1, ограниченная история/курсор |
| Security CHK002–004 | T003–T004; UUID bridge, повторная авторизация, no-store, параметры URL, отказ устаревшим/повторным действиям |
| Security CHK008 | T004 FR-020 и T008 quickstart C02; правила записи и штатная native-приёмка |

Порядок T001→T008 задаёт зависимости; unit/contract проверки каждой части предшествуют коду. Записанный в `validation.md` раздел «Analyze перед реализацией» содержит покрытие 20 FR/7 SC и отсутствие critical/high findings. В tasks записаны связи T001–T008 с issues #7359–7362; live GitHub этой узкой проверкой не инспектировался, завершение issue sync подтверждает основной агент.

Неблокирующие замечания перед выполнением проверок сообщены основному агенту: обновить устаревшие статусы в plan/начале validation; до первого запуска тестов внести точные команды и окружение в tasks, как требует quickstart. Это не отменяет PASS качества требований и не означает успешного исполнения T001–T008.

## Прочитанные доказательства

- `spec.md`: Clarifications, US1–US3, Edge Cases, FR-001–020, SC-001–007, Assumptions.
- `plan.md`: Constitution Check, архитектура и последовательность, проверка приложений, validation.
- `tasks.md`: T001–T008, зависимости, независимые проверки сценариев, tracker links.
- `validation.md`: текущий раздел Analyze перед реализацией.
- `research.md`: причины дефекта, имеющиеся признаки повторения, пределы исследования Krisp, идентичность серии.
- `data-model.md`: identity v1/v2, повтор, записи, попытка подключения, хранение/запросы.
- `design-proposal.md`: интерфейс, join flow, проекция, матрица случаев, предложенная проверка.
- `contracts/calendar.md`: resolver, native bridge, overview/occurrences, совместимость и приватность.
- `quickstart.md`: J01–J07, S01–S08, S09–S10, U01, C01–C02, ограничение native-приёмки.
- `checklists/ux.md`, `checklists/security.md` прочитаны до и после reviewer-правок.
- `.specify/memory/constitution.md`: применимые capture/privacy/lifecycle/independent implementation/Spec Kit границы.
- `docs/agent-guidance/README.md`, `spec-kit-flow.md`, `product-gates.md`; релевантные вводные разделы `docs/prd-voice-layer-final.md`, `docs/current-product-status.md`.
- `.agents/skills/speckit-checklist/SKILL.md`: смысл requirements-quality checklist и reviewer ownership.

## Пределы

Покрытие требованиями задач T001–T008 проверено. Исполнение задач, live GitHub issue sync и runtime validation этим ревью не заменяются. Неподтверждённые внутренние механизмы Krisp не приняты за факты. Карточка серии является явным рабочим допущением, а не приписанным пользователю ответом.

Изменены только два custom checklist и этот отчёт. Код, требования, планы, tasks, GitHub, commits и окружения не менялись.


## Независимая проверка реализации — первый проход

Дата: 2026-09-28. Проверка чтением текущих изменений и новых тестов. **Качество требований остаётся PASS 16/16; завершение реализации пока не подтверждено.** Native-приёмка GRAF Dev и реальный запуск приложений не выполнены; идущие локальные проверки основного агента не объявляются здесь завершёнными.

### Конкретные замечания

| ID | Приоритет | Состояние | Замечание и требуемая проверка |
|---|---|---|---|
| IMP-001 | P1 | OPEN, основной агент исправляет | `cabinet/static/cabinet/cabinet.js` в `refreshCalendarDisplay` сохраняет прежний открытый details по одному ключу серии и двум display preference флагам. `calendar-series.js:8` не перезапрашивает уже полностью загруженную историю. При отмене/переносе даты, удалении записи или отзыве её доступа старая информация остаётся в панели после успешного обновления страницы. Серверные проверки действия сохраняются, но видимый состав/статус/число записей устаревает, нарушая FR-012/014/016. Сохранить раскрытие/фокус, обновляя содержимое через повторно авторизованный запрос; проверить отмену, перенос и revoke/delete при открытой панели. |
| IMP-002 | P2 | OPEN | `EmbeddedCabinetCalendarJoinBridge.swift:52` выбирает первую кнопку страницы по eventId. Текущий экземпляр одновременно присутствует на карточке и в истории: при клике внутри истории loading/error/aria-disabled появляются у первой кнопки карточки, а строка-инициатор остаётся без результата. Хранить инициатор и/или обновлять все видимые копии; проверить две кнопки одного eventId и ошибку подключения из истории. |
| IMP-003 | P2 | OPEN | `calendar-series.js:52` после 422 не сбрасывает истёкший/некорректный cursor: «Повторить» отправляет тот же cursor, поэтому после TTL в один час догрузка не восстанавливается. Нужна явно обозначенная перезагрузка первой страницы при 422; проверить invalid/expired cursor после успешной первой страницы. |
| IMP-004 | P1 | OPEN | `EmbeddedCabinetWebView.swift:1589–1594,2090–2114` регистрирует handler в page world и принимает прямое сообщение доверенного main frame. `event.isTrusted` есть только в JS click listener. Прямой `window.webkit.messageHandlers.grafCalendarJoin.postMessage` из скрипта страницы с доступным UUID минует обязательное пользовательское действие и запускает opener. Права на событие не обходятся, но FR-001/J07 не соблюдены. Изолировать script/handler в WKContentWorld с проверкой доверенного события или обеспечить эквивалентный нативный контроль; отдельно проверить direct page-world message и программный click. |

Номера строк соответствуют чтению первого прохода и могут сместиться при исправлениях. Решение об устранении замечания принимается после повторного чтения изменения и проверки нового сценария; обещание исправления не считается evidence.

### Что подтверждено чтением

- `calendar/series.py` использует owner/workspace/source/calendar selection до группировки и LIMIT; v2 identity учитывает внешний календарь. SQL-ранжирование выбирает текущий/ближайший экземпляр; повторы не объединяются по заголовку.
- Курсор шифруется Fernet, дополнительно подписывается HMAC, ограничен длиной/ASCII, привязан к owner/session/workspace/series/range и сроку действия; скрытое время не читается из его payload на клиенте. Запрос истории ограничен 366 сутками и 50 экземплярами.
- Resolver повторно проверяет доступность события и отмену, отдаёт no-store JSON; клиент сверяет UUID ответа, валидирует HTTPS, блокирует redirects авторизованного join-target. После await проверяются сессия, документ и операция.
- История включает отменённые snapshots, выключает их Join и сохраняет независимо разрешённые записи. `_series_recordings` проверяет workspace, deletion/context state и `decide_meeting_access`; приватные названия записей не выдаются.
- UI рендерит данные через textContent; скрытые title/time не возвращаются в обычных полях истории. Кнопка соединения не запускает запись.
- Изменения содержат самостоятельно написанные Python/Swift/JavaScript и существующие проектные компоненты. Признаков переноса кода, бинарных/графических ресурсов или закрытых API Krisp в просмотренном diff не найдено. Это scoped source review, а не доказательство всех будущих ресурсов релиза.

### Покрытие новых тестов и его пределы

Прочитаны `test_calendar_series.py`, `test_calendar_join_series_contract.py`, `calendar_series.mjs` и `CalendarMeetingOpenerTests.swift` (включая bridge/client test classes). Они задают проверки identity, representative, cursor tampering/expiry/context, отмены, owner/selection/disconnect, 12 дат, нескольких записей, скрытых полей, UI retry/pagination, double click и stale-session. Тесты первого прохода не покрывают четыре перечисленных замечания. Наличие тестового кода не означает успешный результат запуска; результаты и exact-SHA/native evidence ведёт основной агент отдельно.


## Повторная проверка реализации — второй проход

Первоначальные IMP-002, IMP-003 и IMP-004 **исправлены по коду и добавленным проверочным сценариям**. `render` обновляет все кнопки одного события; 422 очищает страницы/курсор и предлагает новую загрузку; script, handler и reply находятся в именованном `WKContentWorld` `GRAFCalendarJoin`. `CalendarJoinIsolationTests` проверяет недоступность handler/reply из page world и отсутствие сообщения при программном click. Browser regression проверяет обратную связь в повторной кнопке и восстановление после 422. Результаты запусков этих тестов не присваиваются независимому чтению кода; native-приёмка GRAF Dev и реальных приложений остаётся отдельной.

Основная причина IMP-001 исправлена: refresh инициирует повторные запросы видимых страниц, старые строки становятся inert, ошибка убирает прежнее содержимое. Однако полный путь refresh пока имеет следующие конкретные дефекты; завершённая приёмка реализации не подтверждается:

| ID | Приоритет | Состояние | Сценарий и исправление |
|---|---|---|---|
| IMP-005 | P2 | OPEN | В `cabinet.js` панель сначала удаляется через replacement региона; после вставки dispatch запускает `load`, который запоминает `document.activeElement` до восстановления `seriesFocus`. `hadFocus` становится false; позднее `rows.replaceChildren` снова уничтожает восстановленный focused link без выбора замены. Передать сохранённый focus/href или восстановить фокус до dispatch; проверить настоящий `refreshCalendarDisplay`, а не только ручной dispatch события панели. |
| IMP-006 | P2 | OPEN | В `calendar-series.js` success проверяет принадлежность ответа текущему state, а catch — нет. A в полёте → закрыть/раскрыть панель → B успешно отрисован → поздний A 422 либо failed refresh: catch A очищает/меняет новую панель B. При B.started=true/cursor=null повтор может перестать запускаться. Перед обработкой catch проверять panel.isConnected/state identity; delayed failure regression должен сохранить результат B. |
| IMP-007 | P1 | OPEN | `series_occurrences` применяет `filtered_events(...include_cancelled=True)`, включая eligibility для будущих приглашений participants/link/location. `normalize.py` явно удаляет conference_links у STATUS:CANCELLED; минимальный отменённый VEVENT может не иметь участников/места, и `sync.py` заменяет эти метаданные. Тогда разрешённая отменённая дата со связанной сохранённой записью исчезает до `_series_recordings`. Текущий contract test лишь меняет статус полной строки. История должна сохранять разрешённые отменённые даты/записи независимо от prompt eligibility; нужен отменённый snapshot без link/location/participants и с записью, желательно через реальный normalize/sync. |

Качество требований продолжает **PASS 16/16**. Новые замечания относятся к реализации, а не к наличию сформулированных требований.


## Финальный повторный просмотр исправлений IMP-001–007

Дата: 2026-09-28. **Все семь замечаний независимого просмотра устранены в проверенном рабочем коде.** Предыдущие таблицы сохраняют историю находок; итоговые состояния приведены ниже. Качество требований: UX **8 checked / 0 unchecked**, security **8 checked / 0 unchecked**.

| ID | Итог | Проверенное исправление и evidence |
|---|---|---|
| IMP-001 | RESOLVED | `refreshCalendarDisplay` сохраняет панель, но отправляет `graf:calendar-series-refresh`; история заново получает видимые страницы с авторизацией, делает старые строки inert на время запроса и убирает их при неуспехе. Browser regression actual `online` refresh проверяет отмену и удаление ранее показанной ссылки записи. |
| IMP-002 | RESOLVED | Native document script использует querySelectorAll для всех кнопок eventId. Browser regression нажимает копию внутри истории и проверяет её resolving/error/disabled состояние. |
| IMP-003 | RESOLVED | Ответ 422 очищает строки и cursor, возвращает состояние первой загрузки и понятное действие «Загрузить заново». Browser regression проверяет новый успешный первый запрос после истёкшего курсора. |
| IMP-004 | RESOLVED в исходниках | Script/handler/reply используют один именованный `WKContentWorld` `GRAFCalendarJoin`; page-world не имеет прямого доступа к обработчику. Прочитан настоящий `CalendarJoinIsolationTests` с WKWebView: handler/reply undefined в page world, программные click/dispatch не отправляют сообщение. Результат Swift-запуска и native-приёмка учитываются отдельно основным агентом. |
| IMP-005 | RESOLVED | Фокус прежнего элемента возвращается до dispatch refresh; после авторизованной замены строк `rows.inert=false` выполняется до focus. Первая попытка regression поймала inert-препятствие (actual href null), оно затем исправлено. Итоговый browser regression вызывает настоящее online-обновление календаря и подтверждает сохранение href фокуса. |
| IMP-006 | RESOLVED | Catch проверяет panel.isConnected и state identity до любых изменений; закрытие сбрасывает inert. Browser regression удерживает A, закрывает/открывает панель, успешно получает B, затем отдаёт A=422 и проверяет сохранение новых строк/статуса. |
| IMP-007 | RESOLVED в исходниках | `series_occurrences` вызывает filtered_events(history=True): ограничения owner/source/selection/privacy/all-day сохраняются, фильтр приглашений participants/link/location не применяется. Contract regression очищает эти метаданные отменённого события и требует обе его доступные записи при недоступном Join. Итоговый запуск серверных тестов учитывается отдельно основным агентом. |

### Непосредственно прочитанный результат проверки

`/tmp/f279-browser.log` после последнего исправления содержит:

> PASS: production series UI, keyboard, pagination 12 dates, inline retry, real calendar refresh focus, stale failure isolation, narrow viewport, exact native script double-click/retry/no-navigation

Прочитан актуальный код исправлений и сценариев. Это подтверждает перечисленные браузерные проверки в синтетическом окружении. Лог не заменяет сборку/запуск GRAF Dev, настоящий запуск Телемост/Zoom/Teams, ручную VoiceOver-приёмку, exact-SHA CI и release evidence. Эти неподтверждённые ворота данным отчётом не закрываются.

В области семи найденных замечаний открытых дефектов после повторного просмотра не осталось. Изменён только этот reviewer-report; checker markers не смешаны с runtime-статусом, код/tasks/GitHub не изменялись reviewer-агентом.


## Узкое ревью T009 — меню macOS и напоминания

Дата: 2026-09-28. **PASS для проверенного изменения; новых блокирующих замечаний не найдено.** Прочитаны актуальные `CalendarMeetingOpener.swift`, места вызова в `CalendarTray.swift` и `TwoBrainRecApp.swift`, действующий `DesktopCalendarPromptActions.swift`, конфигурация клиента и `NativeCalendarJoinTests`.

- Оба native-входа передают UUID в `openEvent`; сохранённый в модели URL не передаётся opener и не используется при отказе сервера. Старая проверка наличия ссылки остаётся условием доступности действия, не полномочием на запуск.
- `openEvent` использует действующий `DesktopUploadClient.calendarJoinTarget`; серверная авторизация/проверка отмены сохраняются. После await проверяются поколение сессии, отсутствие navigation barrier, текущий token, текущий origin и допустимый HTTPS. Отмена Task исключает запуск.
- `resolveAndOpen` выполняется на MainActor, удерживает одну активную native-операцию до её завершения и освобождает состояние через defer. Повтор после отказа возможен. Ошибка resolver не запускает cached fallback.
- Ветка записи `startRecording` и передаваемые ей intent/eventId не изменены; доработка касается только Join.

Непосредственно прочитан итог `/tmp/f279-swift.log`: **98 tests, 0 failures**. Включены оба `NativeCalendarJoinTests`: смена сессии/параллельный повтор/новая попытка и отказ resolver без cached fallback. Также теперь непосредственно подтверждён PASS `CalendarJoinIsolationTests.testPageCannotMessageBridgeOrSynthesizeJoin` (настоящий WKWebView).

Это локальное evidence тестов Swift, не запуск установленного GRAF Dev и не подтверждение Telemost/Zoom/Teams через macOS. Ручные/native/exact-SHA/release ворота сохраняют прежний отдельный статус. Reviewer не менял T009, его GitHub issue или код. Custom checklist качества требований остаётся UX 8/8 и security 8/8.


## Узкое ревью выбора приложения Teams/Zoom

Дата: 2026-09-28. **PASS по исходникам исправления; новых блокирующих замечаний не найдено.** Просмотрены текущие изменения `CalendarMeetingOpener.swift` и `NativeCalendarJoinTests`.

Для Teams допускаются только bundle ID `com.microsoft.teams2` / `com.microsoft.teams`, для Zoom — `us.zoom.xos`; выбор URL приложения выполняется через `urlForApplication(withBundleIdentifier:)`. Custom scheme передаётся найденному приложению явно через `open(_:withApplicationAt:configuration:)`. Прежний поиск любого обработчика схемы `urlForApplication(toOpen:)` удалён из этого пути, поэтому регистрация `msteams` у Parallels proxy сама по себе больше не выбирает native-адресата. Если известное приложение не найдено, используется исходный проверенный HTTPS URL. Прямой путь Телемост по bundle ID сохранён. Ошибка запуска выбранного приложения возвращается как неуспех, без одновременного второго запуска браузера.

Проверки host/path в nativeCandidate сохранены. Новый тест проверяет соответствие Teams/Zoom известным bundle ID, отказ подменённому домену и отсутствие native-кандидата для Zoom personal URL. Этот unit-тест проверяет политику выбора, но не реальное состояние Launch Services и не открытие установленного приложения.

На момент чтения `/tmp/f279-swift.log` новый запуск ещё компилировал набор; прежние 98 PASS не приписываются текущему изменению. Итог новой проверки и повторное открытие Teams-ссылки из установленного GRAF Dev должен подтвердить основной агент. Сообщённая им проверка Телемост/Zoom/Meet не заменяет проверку изменённого Teams-пути. Reviewer не запускал приложения и не менял код/commit/runtime. Качество требований остаётся UX 8/8, security 8/8.


## Аудит готовности F279 после пользовательской приёмки VoiceOver

Проверен исходный HEAD `54c9c7cdb877a3e00a57da68610557f4a5eb5c59`, затем подтверждён локальный HEAD после rebase `e26aedf74253dc2a4e65be333a90ddb54e306e0b`. Прочитаны актуальные spec/plan/tasks/quickstart/validation и custom checklist, новые server/Swift/browser tests и относящиеся к календарю существующие проверки. **Качество требований: UX 8 checked / 0 unchecked; security 8 checked / 0 unchecked.** Новых подтверждённых дефектов реализации при данном проходе не найдено.

### Пользовательская приёмка и границы проверки подключения

Пользователь прямо сообщил: «Voice Over не будем проверять. Я его уже отдельно проверил, все работает». Это принято как **user evidence** выполнения VoiceOver, а не как тест reviewer-агента; повторная проверка не требуется. В сочетании с описанными в validation проверками клавиатуры/тем GRAF Dev и browser узкого окна это закрывает известную незавершённость U01/SC-006.

Spec Independent Test и quickstart прямо допускают передачу синтетической ссылки приложению без участия в звонке. Следовательно, доказательства внешней маршрутизации Телемост/Zoom/Meet и сохранения GRAF нельзя отклонять только потому, что ссылка не ведёт к настоящему разговору. Критерий оценивается вместе с тестами точного UUID/query/выбора повторения. Права на микрофон, реальное аудио или вступление в чужой звонок для этого не требуются.

Teams на проверенной машине отсутствует: J02 для исходного HTTPS после исключения Parallels handler подтверждён validation. Native Teams остаётся **unverified**, как требует plan п.4; не считать браузер доказательством native-запуска. Проверка native Teams обязательна перед заявлением проверенной direct-app поддержки этого варианта; доказанный путь при отсутствующем приложении не требует его установки.

### Матрица J/S: сопоставление доказательств

Здесь «покрыт» означает достаточное совокупное scoped evidence требований, исходников, существующих/новых тестов и записанной Dev-приёмки. Это не заявление о едином полном ручном прогоне всех вариантов; самостоятельные SHA/CI и условия завершения указаны ниже.

| ID | Оценка | Доказательства / предел |
|---|---|---|
| J01 | Покрыт для установленного Телемост/Zoom | Dev-передача нужным приложениям и сохранение экрана (validation); точный event UUID/query проверяет CalendarJoinClientTests/контракт resolver. Native Teams отдельно unverified. |
| J02 | Покрыт | Dev Google Meet и Teams HTTPS при отсутствии Mac Teams; known-bundle policy и исходный HTTPS fallback прочитаны. |
| J03 | Покрыт | Contract resolver и Swift client/opener сохраняют синтетический query; redirect blocker отделяет auth GRAF. Новые пути не журналируют URL. |
| J04 | Покрыт | Contract cancelled/unselected/disconnect/foreign-owner; общий resolver не выдаёт отсутствующую/удалённую безопасную цель, no cached fallback проверен NativeCalendarJoinTests; локальная ошибка browser/bridge. |
| J05 | Покрыт | Native/bridge duplicate+stale+retry tests, browser точный documentScript и inline retry. |
| J06 | Покрыт | Поколение сессии/token/origin/navigation barrier и поздний resolver; NativeCalendarJoinTests/bridge tests. |
| J07 | Покрыт | Настоящий WKContentWorld isolation test + malformed/extra URL payload tests; Coordinator main-frame/origin/allowed-route guards и forMainFrameOnly не расширяют политику навигации. |
| S01 | Покрыт совокупно | Contract/browser/Dev 12 повторов; отдельные keys/группы; unit `series_key=None` и сохранённый API одиночных событий. |
| S02 | Покрыт | SQL группирует до LIMIT, contract две серии не вытесняются частыми экземплярами. |
| S03 | Покрыт | Unit owner/calendar identity, реальный SQL collision внешних календарей, группировка не использует title/link. |
| S04 | Покрыт | SQL move/cancel сохраняет ID и группу; cancelled-history contract; ссылки resolver выбираются по ID даты. Нормализация переносов покрыта существующим набором. |
| S05 | Покрыт совокупно | Прогнанный normalization suite содержит DST/all-day/floating/moved identity; Dev подтвердил одну зону карточки/истории, UI использует общий форматтер. |
| S06 | Покрыт совокупно | Fixture содержит одноэкземплярную отдельную серию; recurrence presence независимо от количества, UI не выдумывает частоту и пишет ограниченный диапазон/неполную историю. |
| S07 | **Обязательное дополнение evidence** | Own 0/2 записи, отменённая дата и hidden title/time покрыты; foreign-series отказ тоже. Нужен API сценарий **внутри разрешённой серии** с недоступной записью другого владельца/отозванным grant, затем удалением одной записи: реальные `_series_recordings`/`decide_meeting_access`, без лишней ссылки/скрытого счётчика. Browser mock revoke это не заменяет. Реальная утечка по исходникам не обнаружена. |
| S08 | Покрыт lifecycle; часть delete проверяется дополнением S07 | Contract source disconnect/unselect и существующий disconnect lifecycle сохраняют записи и убирают будущую проекцию. |
| S09 | Покрыт | `representative` unit и реальное SQL current-selection/move/collision; tie-break/граница ends_at заданы и проверены. |
| S10 | Покрыт | HMAC/Fernet context+expiry/tampering unit, API чужая серия/слишком длинный cursor/range, schema limit 1..50, browser 422 restart; keyset пара starts_at/id. |

### Обязательные остаточные доказательства до объявления готовности

1. **S07 / SC-005**: описанный выше авторизационный API regression в доступной серии, включая отзыв/удаление. Основной агент принял дополнение; будущий результат пока не PASS.
2. **C02 / FR-020**: Join во время уже активной записи. Существующие tests доказывают «join не вызывает startRecording» и сохранение recordingState при calendar invalidation, но ещё нет контролируемого сценария именно production Join при active capture-state. Достаточен синтетический recorder/controller с настоящим bridge/action: активный recording ID/state/context до вызова, success/failed/stale resolver, счётчики start/stop=0 и сохранение active ID/context/видимого состояния после. Recorder должен быть связан с проверяемым production путём, а не быть посторонней неизменяемой переменной. Реальный захват микрофона/экрана не является обязательным условием этого локального контракта.
3. **SC-007**: воспроизводимые измерения <=200 мс для индикации и p95 <=500 мс для уже загруженных данных. Production browser harness с trusted click, подготовленными данными, измерением до кадра, 30 образцами и явно указанными версиями среды/viewport/SHA/правилом p95 достаточен по формулировке spec. Native-WK p95 не требуется; Dev UI подтверждается отдельно. Время CUA round trip с фиксированным ожиданием инструмента не является временем paint. Временные цифры основного агента не считаются сохранённым PASS до воспроизводимого сценария и его результата.
4. **Финальный SHA/base/CI и согласованные документы**: после rebase/новых тестов нужен новый exact-SHA current-check validator; старые CI на 54c9 не квалифицируют новый SHA. Read-only GitHub snapshot PR #7363 дал head 54c9, draft=true, mergeable_state=behind и base e39c5f4554174451f790c1240cb07270072b69d1; это снимок до обновления remote, не утверждение о текущем состоянии после работы основного агента. Перед readiness согласовать tasks/validation с user VoiceOver и новыми результатами, убрать устаревшее требование участия в звонке. Замороженный release-full остаётся воротами конкретного релизного кандидата, а не дополнительным требованием к каждому локальному проходу.

Reviewer не менял tasks, spec/plan/validation, код, GitHub, commits или приложение. Будущие проверки не отмечены как выполненные.


## Завершающее ревью локальных доказательств T010

Дата: 2026-09-28. Проверены текущие изменения тестов поверх `e26aedf74253dc2a4e65be333a90ddb54e306e0b` и непосредственно прочитаны журналы их завершения. **S07/SC-005, C02/FR-020 в описанной ниже границе и SC-007 — PASS. Открытых обязательных локальных пробелов, перечисленных предыдущим проходом, больше нет.** Этот раздел заменяет незавершённый статус пунктов 1–3 предыдущего раздела; пункт 4 о финальном SHA/CI/документах сохраняется.

### S07: независимые права записей внутри разрешённой серии

`test_series_recordings_recheck_grant_revocation_and_deletion` в `apps/server/tests/contract/test_calendar_join_series_contract.py` вызывает настоящий HTTP endpoint и использует БД/действующую политику доступа. У разрешённой пользователю даты созданы собственная запись, чужая запись с активным персональным grant и чужая запись без grant. Сначала возвращаются только первые две, после отзыва grant — только собственная, после её удаления — пустой список. Тест проверяет отсутствие запрещённых/отозванных ID во всём payload и отсутствие `recording_count`, а не только число элементов. Это закрывает прежний пробел проверки `_series_recordings` в доступной серии; browser mock не используется как замена авторизации.

Непосредственно прочитан `/tmp/f279-closeout-server.log`: **9 passed, 2 warnings**, `postgres_test_result=pass`, изолированный контейнер удалён. Предупреждения не представлены как ошибки; тестовый код и итог проверены reviewer.

### C02: подключение при активной синтетической записи

`NativeCalendarJoinTests.testProductionPromptJoinKeepsSyntheticRecordingContinuous` в `apps/macos/Shared/Tests/CalendarMeetingOpenerTests.swift` сначала выполняет `.record` через настоящий `DesktopCalendarPromptActions`: его callback запускает настоящие `CaptureSessionController` и `LocalRecordingWriter` и создаёт контекст записи. Затем тот же dispatcher выполняет `.join` через настоящий `CalendarMeetingOpener.resolveAndOpen` для успеха, отказа resolver и устаревшей сессии. Положительный `.record` контроль связывает проверяемый recorder с production action; это не отдельная неизменяемая переменная рядом с bridge.

После каждого Join проверяются единственный старт записи, единственный успешный внешний запуск, прежние session/state/context/directory, активность writer и доступность Stop по production policy. Оба источника writer — `BufferedLocalRecordingSampleSource`; микрофонный содержит только синтетические нули. Четыре последовательные порции после явного завершения дают 6400 кадров mixedMeetingAudio на выходе 16 kHz, `captureFailureCode == nil`, `manifest.isComplete == true`. Первоначальный провал из-за отсутствия обязательного второго источника устранён в fixture; production-код не менялся.

Непосредственно прочитан `/tmp/f279-closeout-swift.log`: **113 tests, 0 failures**, в том числе новый C02. Граница доказательства: production dispatcher/resolver/controller/writer с подставным внешним opener и синтетическими аудиоданными. Это достаточно для локального контракта разделения Join/Record и сохранения записи; не является тестом аппаратного захвата, полного приватного ContentView, cabinet → OS → устройство или вступления в звонок. Новые системные разрешения не выдавались reviewer.

### SC-007: воспроизводимое измерение интерфейса

`apps/server/tests/browser/calendar_series.mjs` измеряет trusted click в capture-фазе window до production обработчика, затем видимый статус Join либо фактически отображённые строки серии и два requestAnimationFrame. Проверяется число измерений, Join maximum <=200 ms и series p95 <=500 ms. После 3 прогревочных измерений выполнены 30 образцов; p95 определяется nearest rank ceil(n*0.95). Используются production HTML/assets/documentScript и локальный синтетический API. Это соответствует согласованному локальному стенду spec; время внешнего запуска и аппаратного WKWebView не приписывается измерению.

Непосредственно прочитан `/tmp/f279-closeout-browser.log`: **PASS**; darwin 25.6.0 arm64, Chromium 151.0.7922.34, viewport 1100×850. Join p95 15.4 ms / max 15.5 ms; series p95 32.5 ms / max 32.8 ms. Строка SHA указывает базовый HEAD e26aedf при проверяемых незакоммиченных изменениях тестов, а не новый финальный commit. Сохранённые ранее проверки GRAF Dev и пользовательская VoiceOver-приёмка остаются отдельными доказательствами.

### Итог и оставшиеся условия готовности

Повторно прочитаны оба custom checklist: **UX 8 checked / 0 unchecked; security 8 checked / 0 unchecked; всего 16/16**. Их markers оценивают качество требований и не были переопределены как runtime checklist. Новых подтверждённых дефектов в трёх дополнениях не найдено.

Обязательных открытых локальных пробелов в проверенной матрице больше нет. Основному агенту остаются согласование tasks/validation, окончательный commit, актуальная проверка установленного GRAF Dev после rebase и CI/checked base на окончательном SHA. Старые CI 54c9 не заменяют новый SHA; release-full/распространение относятся к отдельному замороженному релизному кандидату. Native Teams на машине без Mac Teams остаётся unverified для заявления о проверенном прямом запуске; доказанный HTTPS fallback не требует установки Teams или реального звонка. Пользовательская VoiceOver-приёмка принята без повторного теста.

Reviewer изменил только reviewer-owned отчёт и примечания двух custom checklist. Код, tasks, другие документы, GitHub, commits и приложение не менялись. После передачи этого отчёта reviewer не меняет файлы без нового запроса основного агента.


## Независимое ревью четырёх замечаний PR #7363

Проверены actual GitHub review comments, изменения поверх HEAD `c019acab7c913fe7217a5fe9daf1fc0859d5fef1` и журналы `/tmp/f279-review-swift.log` (**116 tests / 0 failures**) и `/tmp/f279-review-server.log` (**13 passed / 2 warnings**). Продуктовый код и тесты reviewer не менял. Качество требований остаётся **UX 8 checked / 0 unchecked; security 8 checked / 0 unchecked**.

| Замечание | Результат независимой проверки | Доказательство / предел |
|---|---|---|
| Day30 в обзоре отсутствует в истории | RESOLVED | Default history `to` теперь midnight day31 exclusive. Настоящий API regression фиксирует now, включает all-day в 00:00 day30 и обычную дату day30, исключает day31; explicit `to=day30` остаётся исключительной границей. Изменение описания диапазона ведёт основной агент. |
| Ошибка native launch оставляет только неработающий повтор | RESOLVED по коду и локальному контракту | После отказа известного native application отдельный NSAlert предлагает действие браузера. `recoverInBrowser` проверяет current/cancellation до и после согласия, заново вызывает resolver и перепроверяет состояние/HTTPS после await. Cabinet передаёт прежние session/document/boundary/token guards; native menu/reminder — текущую сессию/token/origin. Браузер выбирается через нейтральный HTTPS URL и получает свежую ссылку явно через `withApplicationAt`, поэтому recovery не выбирает native provider повторно. Тесты покрывают согласие→новый resolve→browser, отказ пользователя, смену состояния и ошибку resolver. Реальный NSAlert/Launch Services этим unit-тестом не проверяется. |
| Уведомление закрывается до результата Join | PARTIAL: основной дефект исправлен, один остаточный P2 | Dispatcher теперь await Bool, не вызывает dismiss при false; ContentView защищает повтор busy-флагом и поздние UI-изменения identity/session guard, показывает текст ошибки/повтор. Но `refreshCalendarReminder` catch всё ещё безусловно устанавливает `desktopCalendarPrompt=nil`. При offline Join следующий штатный poll (каждые 30 секунд) тоже завершается сетевой ошибкой и скрывает единственный retry. Требуется сохранить failure prompt при временном отказе той же сессии, не сохраняя его при auth change/подтверждённой недоступности/новой проекции. Unit dispatcher no-dismiss/retry не покрывает этот refresh catch. |
| Корректный HTTPS с портом не443 отклоняется | RESOLVED | `validatedHTTPS` допускает допустимые порты 0..65535; nativeCandidate и отдельная ветка Telemost ограничены отсутствующим портом/443, остальные идут HTTPS-путём. Тест сохраняет generic8443/Zoom444/Teams8443/Telemost8443 и отвергает65536. |

На этом проходе три замечания закрыты в описанных границах, одно остаётся частично открытым из-за воспроизводимого refresh-сценария. Это не меняет markers качества требований и не отменяет прошлые доказательства остальных частей фичи. Финальный SHA/CI/Dev должен учитывать новые изменения; прежний PASS реализации не приписывается незавершённому исправлению автоматически.


### Повторная проверка остаточного refresh-сценария — все четыре замечания закрыты

`DesktopCalendarReminderService.shouldRetainFailedJoin` и его вызов в `ContentView.refreshCalendarReminder` повторно прочитаны после исправления. Сохранение допускается только для текущего failed Join с тем же ID/поколением сессии, возрастом от 0 до 300 секунд и временной транспортной ошибкой либо HTTP 408/429/5xx. При закрытом/заменённом уведомлении, другой сессии, истечении срока, отмене запроса, 401/404 и других окончательных отказах карточка не сохраняется. Успешная проекция сервера остаётся авторитетной; устаревший успешный ответ проверяется по поколению сессии до применения.

Восстановление текста ошибки после успешного фонового refresh вызывает `showCalendarJoinFailure(..., renewRetryWindow: false)` и не обновляет failedAt. Новая явная неудачная попытка пользователя начинает новое ограниченное окно. Dismiss очищает ID/time/generation. Поэтому штатный 30-секундный poll больше не убирает недавний retry при offline и не продлевает сохранение бесконечно.

Новый `testReminderRefreshRetainsOnlyRecentSameSessionTransientFailure` проверяет offline/503, 401/404/cancelled, другую сессию, заменённый ID, 301 секунду и nil prompt. Непосредственно перечитан повторный `/tmp/f279-review-swift.log` после последней правки: `Compiling TwoBrainRecApp TwoBrainRecApp.swift`, `Linking TwoBrainRecApp`, `Build complete!`, затем **117 tests, 0 failures** (23:44:43). Таким образом, последняя правка `renewRetryWindow: false` также прошла компиляцию executable; тесты подтверждают core policy/dispatcher/opener, а полный ContentView runtime этим не заявляется. Серверный результат предыдущего прохода — **13 PASS**.

Итог повторного ревью: **все 4 замечания PR #7363 RESOLVED в границах source review и локальных тестов; открытых конкретных дефектов в проверенных исправлениях не осталось**. Эта запись заменяет PARTIAL для уведомления в предыдущей таблице. Custom requirements checklist перечитаны: **UX 8 checked / 0 unchecked; security 8 checked / 0 unchecked, всего 16/16**. Проверки реального NSAlert/Launch Services, окончательной установленной сборки и exact-SHA CI остаются отдельными доказательствами основного агента. Reviewer не запускал приложения и не менял код, tasks, spec/plan, GitHub или commits.


## Независимое ревью второй группы замечаний PR #7363

Дата: 2026-09-29. Прочитаны четыре новых actual GitHub comments, изменения поверх `8ee05b71bf655ae9ade10bd51ffc626f16dc6fb7` и результаты проверок. **Все четыре замечания RESOLVED по исходникам и локальным контрактам; новых конкретных дефектов в проверенной области не найдено.**

| Замечание / thread | Проверенное исправление и evidence |
|---|---|
| Ранний trusted Join оставляет JS pending; `PRRT_kwDOSpM8OM6m25A6` | Coordinator сначала проверяет main frame, attached WebView, текущий document URL, разрешённый meeting-list route и UUID payload. Только затем readiness policy при временной неготовности отправляет terminal `cancelled` в `GRAFCalendarJoin` content world. Недоверенные/malformed сообщения по-прежнему не отвечаются. Swift readiness test проверяет отказ без открытия и последующую успешную попытку; production documentScript в browser regression очищает pending после `cancelled` и допускает следующий click. Это совокупная проверка policy/JS/wiring; реальная гонка `didFinish` не выдаётся за отдельно воспроизведённый сквозной WKWebView-тест. |
| Меню игнорирует отказ resolver; `PRRT_kwDOSpM8OM6m25BD` | Tray вызывает `openEventFromMenu`; единый `menuOpening` удерживается до завершения попыток/диалога. `retryFailedJoin` показывает отдельный явный повтор после false, повторно вызывает `openEvent(UUID)`, проверяет current/cancellation перед каждой попыткой и перед диалогом; после согласия снова проходит проверку цикла. Native resolver повторно проверяет доступ и текущие auth/token/origin. Swift test проверяет failure→explicit retry→success, смену сессии после отказа и во время выбора, без лишней попытки. NSAlert/Launch Services runtime остаётся отдельной приёмкой. |
| Overview cursor ломается через UTC midnight; `PRRT_kwDOSpM8OM6m25BL` | В подписанном/зашифрованном context хранится полный `anchor` и исходные границы. Decoder проверяет точный состав полей, owner/session/workspace/series, согласованность диапазона с anchor, подпись и TTL. Исходный anchor передаётся в `overview_events(now=...)` для того же выбора представителя и SQL-окна. Авторизация/selection по-прежнему выполняется на каждой странице. Обычный `decode_cursor` истории сохраняет exact-context equality. API test переходит через полночь и границу текущего экземпляра, не возвращая повтор серии; unit проверяет каждую scope-привязку, expiry, несогласованный диапазон и exact decoder. |
| Busy-флаг уведомления невидим; `PRRT_kwDOSpM8OM6m25BV` | `pendingJoinPrompt` меняет видимый message, primary action и accessibility label на открытие; сохраняет ID/выбор дат и не меняет Record. При нескольких choices видимый общий message и accessibility сообщают состояние без потери подписей вариантов. ContentView привязывает pending к ID/generation, восстанавливает его после успешного refresh того же уведомления и временно сохраняет при transport error во время await. Task defer очищает pending metadata, а при устаревшей операции убирает оставшуюся карточку с progress. Успех закрывает только актуальное уведомление, failure переводит его в действие повтора. Swift presentation test и чтение wiring подтверждают этот локальный контракт. |

### Непосредственно прочитанные результаты

- `/tmp/f279-review2-swift.log`: **120 tests / 0 failures**, включая readiness/retry/pending presentation и предыдущие проверки. Компиляция изменённых core файлов завершена; это не подмена установленной Dev-приёмки.
- `/tmp/f279-review2-server.log`: **14 passed / 2 warnings**, PostgreSQL focused phase PASS и штатное удаление изолированного контейнера.
- `/tmp/f279-review2-cursor.log`: **4 passed / 2 warnings**, включая добавленный scope/expiry regression; этот набор пересекается с предыдущим и не суммируется как 18 уникальных тестов.
- `/tmp/f279-review2-browser.log`: **PASS** production JS/UI; terminal cancelled→retry, прежние regression и 30 замеров SC-007 после 3 warmup. Join max 16.4 ms, series p95 34.3 ms. Указанный SHA — исходный HEAD 8ee05 при незакоммиченных проверяемых изменениях, не будущий commit.

Повторно прочитаны reviewer-owned checklist: **UX 8 checked / 0 unchecked; security 8 checked / 0 unchecked; всего 16/16**. Их markers качества требований остаются прежними. Открытых локальных замечаний во второй группе не осталось; окончательный commit, exact-SHA CI/checked base и GRAF Dev после изменений подтверждает основной агент отдельно. Код, tasks, спецификации, GitHub, commits и окружение reviewer не менял; изменены только этот отчёт и примечания двух checklist.


## Независимое ревью третьей группы замечаний PR #7363

Дата: 2026-09-29. Прочитаны три actual GitHub review comments и diff поверх `a720af75e44e5465f7439f8b9c8f26ce0499ca80`. **Все три замечания RESOLVED в границах исходников и локальных проверок; новых конкретных дефектов в рассмотренных изменениях не найдено.**

1. **Eligibility обычных дат истории.** `filtered_events(history=True)` больше не возвращается до вычисления eligibility. Исключение метаданных применено только к `source_status=cancelled` либо `source_deleted_at != None`. Owner/workspace/source/selection/all-day/privacy остаются в прежних предикатах. Новый настоящий API regression скрывает активный экземпляр без участников/ссылки/места, сохраняет обе минимальные отменённые/удалённые даты, затем возвращает активный экземпляр после явного включения соответствующих настроек. Предыдущая проверка доступных записей отменённой даты сохранена.
2. **Актуальность уведомления после await.** `ContentView` передаёт свою prompt-specific closure в `openEvent(eventID, isCurrent:)`. Внутри она соединена логическим AND с проверками session generation/token/origin; именно эта общая closure передаётся в `resolveAndOpen`, native `open` и `recoverInBrowser`. Поэтому смена/закрытие уведомления проверяется после исходного resolver и после отдельного browser recovery. Прежние delayed-resolver и stale recovery тесты проверяют поведение общего guard, а две строки production-проводки просмотрены непосредственно. Новый искусственный product seam или тест, зеркалящий исходник, для этой узкой проводки не требуется; это не объявляется полным ContentView end-to-end тестом.
3. **Локальная ошибка в обычном браузере.** FR-003/007 и browser contract применимы к standalone cabinet. Новый page handler использует trusted click, свежий JSON join-target с same-origin credentials/no-store/redirect:error, проверяет event ID/HTTPS, отображает состояние у всех копий действия и держит одну операцию. Пустая вкладка резервируется во время клика, `opener` немедленно обнуляется; ошибка/timeout/pagehide закрывает принадлежащую операции вкладку и возвращает локальный повтор. Успех выполняет переход через ссылку внутри этой вкладки с `rel=noreferrer` и `referrerPolicy=no-referrer`. Это финальное исправление после обнаруженной тестом передачи Referer у `location.replace`; успешный результат не приписывается прежнему варианту.

### Разделение browser/native и доказательства

Native listener теперь выполняется в capture-фазе и вызывает preventDefault; page handler в bubble-фазе игнорирует уже обработанное событие. Это не зависит от порядка регистрации. До native injection признак `GRAFDesktop/` обеспечивает локальное сообщение о загрузке без web popup; он используется только как выбор маршрута, не как авторизация. Именованный WKContentWorld, trusted input и native проверки полномочий сохраняются.

Прочитан новый browser сценарий и завершившийся `/tmp/f279-review3-browser.log`: **PASS**. Проверены stale 404→закрытие пустой вкладки/локальный повтор; двойное нажатие; успешная синтетическая HTTPS-навигация с сохранением query/fragment; реальный `window.opener == null`; отсутствие Referer, X-Auth-Session и cookie в наблюдаемом внешнем запросе; сохранение страницы GRAF; отмена по pagehide; early desktop guard. Совместный native/page маршрут проверен с обычным UA и injected production native documentScript: **0 standalone resolver requests, 0 дополнительных popup**. Внешний адрес перехвачен локальным тестом, не является участием в звонке.

Непосредственно прочитанные остальные результаты:

- `/tmp/f279-review3-swift.log`: **120 tests / 0 failures**, после изменений native capture и caller guard.
- `/tmp/f279-review3-server.log`: **16 passed / 2 warnings**, PostgreSQL focused phase PASS.
- Browser SC-007: 30 измерений после 3 warmup, Join max **16.1 ms**, series p95 **33.5 ms**. SHA в выводе — исходный HEAD a720 при незакоммиченных проверяемых изменениях.
- Уточнение предыдущей группы: совместный `/tmp/f279-review2-server-final.log` непосредственно прочитан и содержит **15 passed / 2 warnings** (11 contract + 4 unit). Это единый итог вместо раздельных пересекающихся 14+4, а не дополнительный набор к 16 текущего прохода.

Reviewer-owned checklist перечитаны: **UX 8 checked / 0 unchecked; security 8 checked / 0 unchecked; всего 16/16**. Требования и факт runtime-проверок не смешаны. Открытых локальных дефектов этой третьей группы не осталось. Окончательный SHA/checked base/CI и штатная установленная Dev-приёмка остаются отдельными evidence. Reviewer менял только этот отчёт и примечания двух checklist; код, tasks, другие спецификации, GitHub, commits и приложения не менялись.


## Независимое ревью четвёртой группы замечаний PR #7363

Дата: 2026-09-29. Выполнено ограниченное независимое ревью изменений поверх `0262d37a4b48c53656c5a2be4cbfb01386939562`: актуальность действия после обновления DOM, совпадение политики hostname между сервером и macOS, смена браузерной сессии во время подключения. Прочитаны итоговые исходники, новые регрессии и завершившиеся журналы. **Все три замечания RESOLVED в границах исходников и локальных проверок; открытых конкретных дефектов в проверенных исправлениях не осталось.** Это не общий аудит всей архитектуры авторизации.

1. **Обновление календаря во время Join.** Проверка старого `button.isConnected` заменена поиском актуального действия того же UUID в текущем документе, вне `[inert]`/`[hidden]`. Идентичность операции, отмена и состояние принадлежащей ей вкладки по-прежнему проверяются. Browser regression запускает настоящий `window.online` refresh production cabinet, подтверждает замену исходной кнопки при ожидающем запросе и успешно завершает единственную передачу ссылки через новое действие. Удалённое либо временно недоступное действие не открывает ссылку.
2. **Единая политика hostname.** Native допускает соответствующие серверной политике DNS-имена и глобальные IP; localhost и неглобальные IP отклоняются. IPv4 использует `inet_aton` до любых decimal-only интерпретаций, IPv6 — `inet_pton` и диапазоны/исключения Python 3.13, включая IPv4-mapped адреса. Сервер нормализует percent-encoding/IDNA hostname, проверяет legacy abbreviated/integer/hex/octal IPv4 и отклоняет обратный слеш в authority. Тем самым закрыты проверенные обходы `%31%32%37.0.0.1`, `%6cocalhost`, обратный слеш перед псевдодоменом и octal-адреса. Swift и Python читают один `calendar_join_host_policy.json`: **141 пример, 66 разрешённых / 75 запрещённых**. Положительные примеры сохраняют допустимые публичные адреса; это проверка согласованной политики, не заявление о DNS-проверке назначения или полном аудите произвольных URL.
3. **Смена сессии после await в standalone браузере.** После GET выполняется новый read-only POST того же join-target с CSRF исходной страницы; используется только URL повторно разрешённого POST. Реальный API regression проверяет отсутствие CSRF, другую сессию того же владельца и отзыв новой сессии. Дополнительно случайный несекретный epoch cookie сравнивается между запросами и после последнего `await confirmed.json()` перед синхронным переходом. Browser regression задерживает уже разрешённый POST, меняет marker и подтверждает закрытие пустой вкладки без передачи поздней ссылки. Предыдущие проверки pagehide, единственной операции, локального повтора, отсутствия opener/Referer/GRAF auth и разделения native/page обработчиков сохранены.

### Проверка границ cookie marker

Непосредственный поиск всех записей/удалений owner-session cookie подтвердил покрытие обоих issuer (`api/auth.py`, `auth_email_flow.py`) и всех трёх путей удаления (logout, отзыв текущего способа входа в settings, account-merge relogin). Marker добавляется после auth cookie; сама auth cookie остаётся HttpOnly. Production marker имеет Secure, host-only, Path=/, SameSite=Lax, случайные 16 байт без session ID/bearer/данных пользователя и не участвует в серверной авторизации. Logout меняет marker на новый с TTL 60 секунд, в том числе для старой сессии без marker. Account-merge теперь использует существующие динамические имя/secure auth cookie. Обычное продление сохраняет marker, поэтому успешный запрос не отменяет собственный Join. Отзыв через `_revoke_account_session` отдельно запрещает текущую сессию при выполнении, а не только при показе подтверждения. Новая helper/issuer unit-проверка и реальная logout/API регрессия подтверждают указанный контракт; глобальная мгновенная синхронизация удалённого отзыва после уже завершённой серверной проверки этим не заявляется.

### Непосредственно прочитанные итоговые результаты

- `/tmp/f279-review4-swift-complete.log`: **121 tests / 0 failures**, включая весь общий корпус hostname.
- `/tmp/f279-review4-server-complete.log`: **143 passed / 2 warnings**, PostgreSQL focused phase PASS, штатное удаление изолированного контейнера. Расширенный набор включает calendar, CSRF, owner-session и renewal. Ранние неуспешные промежуточные прогоны этим итогом заменены, не суммируются с ним.
- `/tmp/f279-review4-browser-epoch.log`: **PASS** production browser/native scripts, обновление DOM во время Join, новая сессия между GET/POST и marker change во время уже разрешённого POST. SC-007: 30 измерений после 3 warmup; Join max **16.5 ms**, series p95 **34.1 ms**.
- Логи относятся к рабочим изменениям поверх указанного HEAD, а не к будущему commit. Окончательный SHA/checked base/CI и штатная установленная GRAF Dev проверка остаются отдельными доказательствами основного агента.

Оба reviewer-owned checklist повторно прочитаны: **UX 8 checked / 0 unchecked; security 8 checked / 0 unchecked; всего 16/16**. Отметки продолжают означать качество требований, а runtime-доказательства описаны отдельно. Reviewer изменил только этот отчёт и примечания двух checklist; код, tasks, другие документы, GitHub, commits и приложение не менялись. После передачи результата файлы освобождены для согласованного commit; дальнейших правок без нового запроса не выполняется.


## Независимое ревью пятой группы замечаний PR #7363

Дата: 2026-09-29. Прочитаны три actual PR threads `PRRT_kwDOSpM8OM6m4Jmc`, `PRRT_kwDOSpM8OM6m4Jmi`, `PRRT_kwDOSpM8OM6m4Jmq`, итоговый diff поверх `1a6cafed017c06f95d1a1c59cb41373bb30333a5`, обновлённые contracts/plan/data-model/quickstart/tasks и завершившиеся журналы. **Все три замечания RESOLVED в границах исходников и локальных регрессий; новых конкретных дефектов в проверенных исправлениях не осталось.**

1. **Нормализация при выборе приложения.** `nativeCandidate` и `nativeApplicationIdentifiers` используют общую нормализацию регистра/завершающей точки. Teams/Zoom получают нормализованный host в native URI, Telemost выбирается тем же общим списком известных bundle ID и получает исходный HTTPS. Тест проверяет верхний регистр/завершающую точку для Zoom, поддомена Zoom, Teams и Telemost, сохранение query/fragment, отказы lookalike-доменам и нестандартному порту. Это проверка выбора адресата и URL, не новый реальный запуск всех установленных приложений.
2. **Отдельная карточка уведомления.** Прямой cached URL → NSWorkspace удалён. Production dependency `openMeetingEvent` принимает eventID и closure актуальности, вызывает `CalendarMeetingOpener.openEvent`. Карточка и envelope сохраняются во время await; повторный Join не допускается, текст/accessibility показывают открытие. Проверяются active token, presentationEpoch, authEpoch, видимость, текущее событие и deadline; retire отменяет joinTask. После ответа проверяются cancellation/current, лишь успех закрывает карточку и разрешает `.start` для Join+Record. Ошибка сохраняет явный повтор, обычный Join не запускает запись. `reconcileCard` переносит pending/error из envelope без продления deadline. Регрессии проходят через настоящие кнопки карточки: failure→refresh→retry→success, двойное нажатие, отдельное поведение Join/Join+Record и отсутствие handoff/record после close/deadline/auth/link removal/cancel/lock/вытеснения. Поздний resolver в cancellation-тесте использует production `resolveAndOpen`.
3. **Ограничение записей в истории.** SQL выбирает максимум **200 кандидатов на страницу дат** с устойчивым порядком started_at DESC/id ASC до prefetch и индивидуальной ACL. В ответ попадают только доступные meeting ID; hidden total/count не добавлены. `recordings_partial=true` постоянно для каждой даты, независимо от скрытых кандидатов: это контракт ограниченного просмотра, а не сигнал о наличии скрытых данных. Пустая выборка не называется отсутствием записи. UI показывает нейтральное пояснение и общий список `/meetings` либо `/desktop/meetings`; не обещает отсутствующую фильтрацию этого списка по серии. Курсор дат не выдаётся за продолжение записей. Настоящий API regression создаёт более 200 связей, включая скрытые, фиксирует ровно 200 ACL-проверок, проверяет предел результата/отсутствие скрытых UUID/счётчика и одинаковый partial для пустых дат. Browser regression проверяет пояснение, переход и отсутствие неверного «Нет доступной записи».

### Повторная проверка всех точек календарного подключения

Поиск production macOS/HTML/JS/Python подтвердил следующие маршруты: overview/series `data-calendar-join` → общий browser handler; WK Coordinator → bridge/fresh resolver; tray → `openEventFromMenu`; основной ContentView prompt → `openEvent`; отдельная notification card → новый `openMeetingEvent`; резервный API `/events/{id}/open` → `_resolve_join_target`. Других прямых календарных handoff по cached URL в проверенных production-файлах не найдено. Legacy signature `DesktopCalendarPromptActions.openURL` сама не создаёт обход: единственная product injection игнорирует URL и разрешает eventID. Общая внешняя навигация WKWebView не является отдельным calendar action.

В ходе ревью обнаружен оставшийся дублированный фильтр `DesktopNotificationPresenter.safeMeetingURL`, который запрещал public IPv4-mapped IPv6, уже разрешённый общей политикой. Он заменён делегированием `CalendarMeetingOpener.validatedHTTPS` с прежним отдельным запретом fragment. Новый `testNotificationUsesSharedMeetingHostPolicy` проверяет notification путь на всех **141** общих примерах; PASS. Это исправление проверено до завершения данного отчёта.

### Непосредственно прочитанные результаты и границы

- `/tmp/f279-review5-swift-complete.log`: **269 tests, 8 skipped, 0 failures** (261 выполнен без ошибки). Все новые F279 notification async/cancellation, trailing-dot и shared-host tests — PASS. Семь прежних AppKit focus/keyboard сценариев пропущены, поскольку среда не подтвердила фокус обычного окна; ещё один skip — необязательный экспорт snapshot без `GRAF_CARD_SNAPSHOT_DIR`. Эти skips не объявляются runtime PASS или результатом нашей VoiceOver-проверки. Ранее переданное пользователем подтверждение VoiceOver сохраняет отдельное происхождение.
- `/tmp/f279-review5-server.log`: **144 passed / 2 warnings**, PostgreSQL focused PASS, изолированный контейнер штатно удалён.
- `/tmp/f279-review5-browser.log`: **PASS** production UI/scripts и ограниченного просмотра; SC-007 после 3 warmup/30 samples: Join max **16.5 ms**, series p95 **34.4 ms**.
- Предварительный Swift 85 tests / 1 skipped / 0 failures не суммируется с итоговым расширенным набором. Доказательства относятся к рабочим изменениям поверх 1a6, а не к будущему commit. Exact-SHA CI/checked base и штатная установленная GRAF Dev приёмка остаются отдельными доказательствами основного агента; reviewer их этим проходом не закрывал.

Custom checklist перечитаны после правок: **UX 8 checked / 0 unchecked; security 8 checked / 0 unchecked; всего 16/16**. Отметки качества требований отделены от результатов выполнения. Reviewer менял только этот отчёт и примечания двух custom checklist; код, спецификации/plan/tasks, GitHub, commits и приложения не изменял. Файлы освобождены для согласованного commit, дальнейшие правки — только по новому запросу.


## Независимое ревью шестой группы замечаний PR #7363

Дата: 2026-09-29. Проверены threads `PRRT_kwDOSpM8OM6m4lc4` и `PRRT_kwDOSpM8OM6m4lc8`, diff поверх `0c249111f782fac1d774c4121d68062073ca3e68`, обновлённый контракт и J21/S15. **Оба замечания RESOLVED в границах исходников и локальных регрессий; новых конкретных дефектов в этих изменениях не найдено.**

1. **Самостоятельный курсор истории через полночь.** На cursor-пути endpoint использует `decode_occurrence_cursor` и исходные подписанные from/to, не вычисляя новый дневной диапазон. Проверяются exact набор context keys, owner/session/workspace/series, HMAC/шифрование/TTL/размер прежнего формата, aware datetime и 0 < диапазон ≤ 366 дней. Каждая явно повторённая граница должна совпасть с подписанной, отсутствующая восстанавливается. Следующий курсор сохраняет исходный context; текущая авторизация календаря и ACL записей применяются вновь. API regression получает первую страницу в 23:59:59 и следующую после 00:00:02, проверяет cursor-only, обе совпадающие границы и каждую по отдельности, исходный coverage_range и 7 оставшихся дат без дублей. Другие explicit bounds дают 422. Unit покрывает смену каждой scope-привязки, expiry, tamper, oversize, extra context key, naive datetime, пустой и слишком длинный диапазон. Строгий decoder других контрактов не ослаблен.
2. **Общая операция native Join.** `EmbeddedCabinetCalendarJoinBridge.join` теперь вызывает общий `CalendarMeetingOpener.resolveAndOpen`, поэтому process-wide `eventOpening` удерживается на весь resolver и await open, включая существующее browser recovery. `activeID` остаётся проверкой запроса конкретного моста. Opening отправляется только из разрешённой open closure; занятая актуальная попытка завершается failed, а изменившийся current state — cancelled. Invalidate отменяет задачу и не отправляет поздний ответ старому документу. Общий helper освобождает операцию через defer после завершения, ошибки или отмены resolver. Двусторонняя regression удерживает resolver кабинета и проверяет отсутствие второго native resolve/open, затем наоборот; проверяет конечный ответ моста, единственный handoff и новую успешную явную попытку. Дополнительная regression проверяет ошибку resolver и invalidate с освобождением общей операции. Product WebView callsite и его session/document/token guards сохранены.

### Итоговые доказательства

- `/tmp/f279-review6-swift.log`: **271 tests / 8 skipped / 0 failures** (263 выполненных без ошибки). Обе новые regression общей операции — PASS. Причины восьми прежних skips прежние: 7 AppKit focus/keyboard из-за неподтверждённого фокуса тестового окна, 1 необязательный snapshot export. Это не доказательство ручной accessibility-приёмки.
- `/tmp/f279-review6-server.log`: **146 passed / 2 warnings**, PostgreSQL focused PASS, штатное удаление изолированного контейнера; новые unit/API cursor tests входят в итог.
- Browser UI/JS в этом исправлении не менялись; отдельный новый browser-прогон не заявляется. Предыдущие доказательства пятой группы сохраняют свою область.
- Логи относятся к рабочим изменениям поверх 0c249. Новый commit, его exact-SHA CI/checked base и штатный GRAF Dev остаются отдельными доказательствами основного агента.

После записи перечитаны оба checklist: **UX 8 checked / 0 unchecked; security 8 checked / 0 unchecked; всего 16/16**. Отметки качества требований не подменяют runtime. Изменены только reviewer-owned отчёт и примечания ux/security; код, остальные документы, GitHub, commits и приложение reviewer не менял. Файлы освобождены для согласованного commit; без нового запроса дальнейших правок не будет.
