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
