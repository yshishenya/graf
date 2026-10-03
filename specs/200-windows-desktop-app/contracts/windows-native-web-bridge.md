# Contract: Windows WebView2 navigation and native bridge

Дата: 2026-09-06

## 1. Trusted origin

The production origin is the normalized HTTPS origin configured by the same
cabinet configuration as macOS. The packaged default is:

```text
https://rec.2brain.pro
```

Allowed paths are the existing server-owned desktop route kinds, including:

- `/desktop/meetings`;
- `/desktop/meetings/{meeting_id}`;
- approved meeting share/deletion-report routes;
- approved `/desktop/settings/...` and auth recovery routes already accepted by
  the cabinet route policy.

The implementation must port the existing exact route-kind decision model. It
must not use a broad `contains("desktop")` or `contains("meeting")` check.

Unknown scheme/host/port, `file:`, `data:`, `javascript:`, local filesystem,
loopback not explicitly enabled for local development, downloads requiring native
file access and native-only capture routes are denied or opened externally by a
bounded policy.

Единственное embedded-исключение внешнему origin — непривилегированная платёжная
цепочка §9; оно имеет приоритет над общим отказом навигации, но не над запретом
native authority, неверной схемы или неподтверждённого первого provider.

## 2. WebView2 settings

For the remote cabinet:

- use WebView2 Evergreen Runtime and check runtime availability before creating
  the control;
- set `AreHostObjectsAllowed = false`;
- enable web messages only when the specific bridge is configured;
- do not expose COM host objects, arbitrary native methods or filesystem APIs;
- disable default script dialogs and unneeded capabilities;
- keep host process standard-user/non-elevated;
- remove or invalidate bridge state when the document/session boundary changes.

## 3. Envelope

Every web-to-native request uses:

```json
{
  "protocol": "graf.desktop.bridge",
  "version": 1,
  "direction": "web_to_native",
  "message_id": 1,
  "nonce": "ephemeral-nonce",
  "origin": "https://rec.2brain.pro",
  "command": "request_app_quit",
  "payload": {"action": "quit"},
  "sent_at_monotonic_ms": 12345
}
```

Limits for the first version:

- maximum serialized message: 64 KiB;
- maximum payload nesting: 8 levels;
- `message_id` is a positive monotonically increasing unsigned integer per
  WebView document; `nonce` is rotated at every successful document boundary;
- command strings and bounded payload strings have explicit allowlists/limits;
- no arrays of audio samples, file paths, cookies, tokens or transcript text;
- one in-memory nonce per WebView session, rotated on navigation/auth boundary.

Native rejects malformed JSON, unknown version/command, wrong direction, invalid
nonce, duplicate/expired message id, unapproved source or oversized payload
without a local side effect.

## 4. Native-to-web events

### `native_ready`

The native host sends the envelope from section 3 with direction
`native_to_web`, command `native_ready`, message id `1` and an empty payload.
It supplies the current document nonce after the typed bridge script is ready.
This is initialization, not authority to record, upload or delete. No
acknowledgement command is accepted from the web page.

### `local_recordings`

The native host sends `{"command":"local_recordings","nonce":"...","rows":[],"operations":[],"recoveryRequired":false}`
only to the current approved document. This bounded display message is distinct
from the web-to-native request envelope; it grants no native authority. The
page passes the rows to `window.GRAFLocalRecordings.update(rows)` as described
in section 8. Paths, credentials and recording contents are excluded.

Typed `native_reply` replies to settings requests bind the outer document nonce
and request_id to the pending request and bounded version-1 payload; no reply
creates native authority. Deletion completion binds the validated request ID to
saved/unknown/accepted/pending/rejected counts. `operations` describes only the
persisted native deletion lifecycle, not proof that a remote provider erased data.

Capture, readiness, runtime recovery and aggregate custody state are displayed
by native controls. The earlier proposed `capture_state`, `custody_summary`
and `runtime_state` messages are not part of the active protocol.

## 5. Web-to-native intents

The initial allowlist is intentionally small:

| Type | Effect | Allowed while capture active |
|---|---|---:|
| `request_app_quit` | validate exact `{"action":"quit"}`; stop active capture and wait for native finalization before closing | yes, close waits for finalization |
| `local_recording` | validate exact `{"action":"open\|send\|delete","id":"known-local-id"}` and the current row capability; see section 8 | only when current native state permits that action; deletion is blocked during capture/upload |
| `app_appearance` | bounded `theme` enum: system/light/dark, updates native appearance only | yes |
| `native_settings` | versioned request to exact recording/notification settings handler on its matching settings route; no arbitrary method invocation | yes; recording state still gates capture-related changes |
| `delete_selection` | typed version 1 `deleteSelection`, valid request ID, at most 100 unique known local IDs/server meeting UUIDs; current route and native capability rechecked | active capture/upload targets cannot be purged |
| `request_app_update` | exact empty payload; open native package-update UI, no URL/path/installer arguments | checking is allowed; installation is deferred until capture/finalization ends |
| `calendar_join` | exact action/event UUID/request UUID; freshly resolve authorized target, see §10 | Join does not alter capture; native Join-and-record is separately gated |

No compatibility aliases are accepted. `open_native_settings`,
`request_native_settings`, `open_native_diagnostics`, `request_diagnostics`,
`request_runtime_repair`, `ack` and `ack_display` are rejected. Settings,
diagnostics and runtime recovery remain available through native controls and
approved navigation, not dormant bridge handlers.

`start_recording`, `stop_recording`, `pause_recording`, `resume_recording`,
`read_file`, `write_file`, `run_process`, `set_audio_device`, `get_token`,
`get_cookie` and generic method names are rejected. User control remains native.

## 6. Navigation lifecycle

1. On `NavigationStarting`, normalize and evaluate origin/route before allow.
2. On accepted new document, create a fresh nonce and clear old bridge state.
3. On `ContentLoading`/document-created, do not inject a generic privileged
   script; only the reviewed typed commands from section 5 for the exact
   trusted origin may be installed.
4. On auth expiry, route block, WebView recreation or origin change, invalidate
   nonce and stop sending sensitive state.
5. On `WebMessageReceived`, compare the message source with the current WebView
   source/origin, then parse and validate the typed envelope.
6. On runtime or network error, leave native capture/custody state untouched and
   show bounded UI outside the document.

## 7. Security tests

The contract is not complete until tests cover:

- untrusted origin posting a valid-looking message;
- trusted origin with stale nonce;
- malformed JSON and unknown type/version;
- oversized/deep payload;
- replayed message id;
- attempted native control/file/token commands;
- non-quit app-close payloads and quit requests from a non-approved route;
- cross-frame/redirect navigation;
- WebView close/recreate during active recording;
- missing runtime and runtime repair failure.

## 8. Локальные записи: уточнение паритета от 2026-09-06 (T083/T084)

Windows использует существующий `window.GRAFLocalRecordings.update(rows)`
кабинета, как macOS. В веб передаются только строки для отображения: непрозрачный
локальный `id`, фиксированное название записи, время и длительность при наличии,
состояние, флаги `canOpen`, `canSend`, `canDelete`, `uploadComplete`. Пути,
учётные данные и содержимое записи в строки не входят. Нет достоверной даты —
показывается «На этом компьютере», дата не выдумывается.

Единственный новый запрос `local_recording` имеет ровно два строковых поля:
`{"action":"open|send|delete","id":"known-local-id"}`. Проверяются текущий
документ/nonce, типы, точные поля, ограничения длины, принадлежность id последнему
нативному списку и разрешение действия. Перед эффектом нативный владелец повторно
проверяет актуальное состояние записи и границы хранилища. Запрос не является
доступом к произвольным файлам и не может выбирать путь.

`open` открывает только проверенный готовый файл прослушивания; повреждённая или
ещё активная запись не объявляется доступной. `send` запускает существующую
очередь без повторной отправки завершённого пакета. При отсутствии входа
открывается вход с возвратом в список. `delete` требует отдельного нативного
подтверждения конкретной записи; запись/отправка в процессе блокирует удаление.
Это удаление локальной копии по явному решению пользователя, не серверная команда
удаления и не подтверждение серверной очистки. Команды очистки сервера остаются
закрытым условием до появления достоверной авторизации конкретной установки.

Уточнение 2026-09-26: существующий `delete_selection` связывает выбор кабинета
с нативным жизненным циклом удаления. Право конкретной установки/аккаунта
проверяется нативно по серверным возможностям перед эффектом; наличие команды
не является разрешением удаления. Успех сохранения запроса не означает очистку.

## 9. Актуальные границы паритета (2026-09-26)

`native_settings` принимает только `grafRecordingSettings` на
`/desktop/settings/recording` и `grafNotificationSettings` на
`/desktop/settings/notifications`, без query/fragment. Внутренний запрос имеет
version 1, session nonce, положительный целый requestId и ограниченное действие.
Recording actions — read/set/setAll с известным ID и правилом always/ask/never.
Notification actions и поля следуют серверному F264/F274 контракту; неподдерживаемое
действие получает явный отказ, а не зависшее обещание. T104 заменяет нынешний
read-only ответ на реальное локальное хранение/карточку; до реализации кнопки
не заявляются работающими.

Платёжное исключение T102 ограничено billing → точный HTTPS provider → bank
и 900 секундами (список и завершение см. plan.md). Это отдельное состояние
непривилегированной навигации, не расширение trusted-origin. Внешние страницы,
их frames и auth формы не получают native_ready/nonce, typed bootstrap, локальные
строки или cookie extraction. Возврат в кабинет заново устанавливает доверенную
границу; nonce внешней цепочки не существует. Expiry, WebView process failure,
recreate/logout сбрасывают платёжное исключение. Нативная запись не зависит от него.

T103 сохраняет HTML 400/429 доверенных интерактивных auth форм без выдачи моста.
Recovery next — только разрешённая внутренняя GET-страница кабинета, включая billing
и meeting detail, никогда payment POST или внешний URL. T106 добавляет только
проверенные bounded attribution поля в единый sign-in builder без журналирования.

Точные правила T102/T103:

- Только основной billing-документ начинает payment session; iframe не начинает,
  не продлевает и не завершает её. Same-origin frames допускаются как документы,
  без моста; внешний HTTPS frame — только внутри живой payment chain.
- Provider host сравнивается точно, без implicit subdomains; HTTPS URL с userinfo
  отвергается. Последующие bank hops также только HTTPS. Срок от первого перехода
  не продлевается и проверяется перед отложенным действием. Порты сохраняют
  политику Mac (не вводится новый запрет HTTPS-портов).
- Popup сохраняет browser method/body, а не заменяет POST вызовом Navigate(GET).
  При невозможности корректного adapter-пути это открытый тест/отказ, не PASS.
- Формы разрешённых login/sign-up маршрутов сохраняют HTTP-документ с ошибками;
  network/TLS failure не считается формой. Для account email-link start/verify
  исключение только HTML400/429/503;401 или `X-GRAF-Cabinet-Recovery: reselect-space`
  требуют восстановления. В cabinet401 означает истёкший вход,403 — отсутствие
  доступа без ложного logout. Bank401/403 не очищает сессию GRAF.
- Последний безопасный GET-document хранится отдельно от текущего URL;
  `next` содержит только URL-encoded разрешённый path без чужих query/fragment.
  Checkout start/subscription actions/discount actions не переигрываются.
  Запасной адрес оплаты — `/billing`, общий — `/desktop/meetings`.
- Старые navigation generation/cookie callbacks не меняют новый документ.
  OAuth остаётся отдельной ограниченной цепочкой 10 минут/32 перехода;
  payment не продлевает её. Границы download/upload transport не расширяются.

### Настройки уведомлений T104 — историческое решение до F277

Следующий раздел и «Системная доставка» заменены нормативным разделом F277
от 28 сентября в [f277-notifications-parity.md](f277-notifications-parity.md).
Они объясняют прежнее исследование, но не разрешают
новую реализацию version1, двух каналов или ScheduledToastNotification.

Нормативная база — `cabinet.js::nativeSettingsQueue/initNotificationSettings`
и `DesktopNotificationPresenter.swift` в master `f5cca687a`.
Outer payload ровно handler/requestId/request. Inner version1/nonce/action;
read/test без дополнительных полей, set содержит ровно field/value.
Поля: reminders/showTitles/sound строго boolean, offsetMinutes строго integer
0/1/5. Ответ version1/preferences{эти четыре поля}/canEdit:boolean/
canRequestPermission:boolean/permission:string, optional bounded message/error.
Optional `canOpenSystemSettings:boolean` describes only the system-settings
action: Windows returns false; an older Mac response without this field retains
the existing action only after a successful native settings connection.
This presentation capability never bypasses native request validation.
Неподдерживаемые requestPermission/openSystemSettings не объявляются доступными
и возвращают явный ответ, не меняют системные разрешения.
Nonce/requestId привязаны к текущему документу, stale ответы отвергаются.

Поведение карточки нормативно повторяет `cardDeadline`, `shouldPresentCard`,
`cardDismissalKey`, `reconcileCard`, `canPresent/cardPriority`, `handleCardAction`
и `currentMeetingURL` указанного Mac-среза: окно начинается в startsAt−15min,
заканчивается min(endsAt, startsAt, startsAt−15min+120s), не 120s после запуска
приложения. Поздний запуск не возвращает пропущенную карточку. Выбирается ближайшее
подходящее событие; контекст, event ID и время начала различают перенос/отказ.
Подавление закрытой карточки, приоритет настоящей/тестовой/короткой и очистка
при смене аккаунта соответствуют этим методам, без новой Windows-политики.
Join использует только текущий разрешённый URL после revalidation, не сохранённую
ссылку отменённого события. OS toast channel не требуется для местной карточки;
настройка offset0/1/5 сохраняется отдельно и не меняет фиксированное окно карточки.

Уточнение 2026-09-27: отдельное настраиваемое напоминание обязательно доставляется
в startsAt−offsetMinutes с выбранным sound. Фиксированная ранняя карточка его не
заменяет. Пропущенная ранняя карточка не поглощает напоминание; перенос/отмена,
смена аккаунта и дедупликация учитываются независимо. Неуспех системной доставки
не отражается как подтверждённый показ. Тесты времени/звука не меняют часы или
пользовательские настройки настоящей Windows.

#### Системная доставка и жизненный цикл T104

- Ранняя местная карточка существует только при работающем GRAF. Отдельное
  уведомление за 0/1/5 минут регистрируется в планировщике ОС и остаётся
  запланированным после обычного явного выхода из GRAF. Скрытие окна ничего
  не отменяет. Выход из аккаунта, смена владельца/рабочего пространства,
  выключение напоминаний и известная отмена события удаляют принадлежащие
  этому контексту запланированные и доставленные уведомления.
- ОС не получает прямые URL встречи, токены или текст расшифровки в аргументах
  активации. Используется непрозрачный ограниченный идентификатор; после
  активации GRAF заново проверяет владельца, событие и актуальную ссылку.
  Без входа/свежего подтверждения открывается кабинет/восстановление, запись
  и переход по устаревшему URL не начинаются. Сеть не требуется самой ОС для
  уже запланированного локального уведомления. Изменения календаря, сделанные
  когда GRAF не запущен или offline, невозможно знать до обновления данных;
  устаревшее уведомление не является разрешением его действия.
- Ключ попытки стабилен для владельца/контекста и экземпляра события, не для
  времени старта. До срока будущая заявка может быть заменена после переноса,
  изменения offset или перезапуска. После истечения срока повтор для того же
  экземпляра не создаётся, даже если факт показа неизвестен. Устойчивый журнал
  хранит только хешированные ключи, срок и состояние заявки, не содержимое.
  Ошибка чтения/записи журнала не разрешает повторную отправку; видна честная
  ограниченная ошибка. Ошибка передачи ОС не называется доставкой.
- При первом получении события после due, но до
  `min(endsAt, startsAt+300s)`, допускается одна немедленная заявка, если ранее
  попытки не было. После этого предела новая заявка запрещена. После сна/старта
  сверяются системные pending/history и журнал, отменяются устаревшие заявки,
  но неизвестный показ не приводит к дублированию. Срок действия системного
  уведомления ограничен тем же пределом; приёмка отдельно проверяет поведение
  ОС при sleep/wake, не обещает показ на выключенной машине.
  Уже существующую актуальную pending-заявку не удаляют только потому, что due
  прошёл: Windows может ещё обрабатывать её в своём пятиминутном окне.
  Первая поздняя постановка использует now+1s, строго раньше validUntil.
- При запуске записи, записи, паузе, остановке и финализации собственные
  напоминания отменяются/подавляются; они не предлагают вторую запись и не
  звучат поверх захвата. Звук настраивается штатным каналом согласно `sound`;
  собственное воспроизведение в обход системного отключения не используется.
  После завершения записи допускаются только ещё актуальные непоглощённые
  события. Тестовая карточка не меняет журнал настоящих уведомлений.
- Различаются состояния «передано ОС», «есть в системной истории», «пользователь
  нажал» и «фактический показ/звук проверен». Успех API — только первое.
  Отключённые уведомления, режим «Не беспокоить», лимит планировщика или отказ
  ОС не скрываются за PASS. Местная карточка сохраняется независимо от этого.
  Приёмка: due0/1/5 и sound on/off; процесс работает/завершён/перезапущен;
  ранний и поздний wake; перенос до/после due; смена владельца; отмена; запись
  на границе срока; denied/DND; ошибка журнала и API; повторная активация.

### Платформенные подписи и обновления — 2026-09-27

Общий кабинет получает только ограниченный признак Windows для выбора
адресных системных подписей. Признак не устанавливает trust/origin/nonce и не
является разрешением команды. Текстовые узлы встреч/расшифровок не обходятся и
не заменяются. Без признака старый Mac сохраняет прежние подписи; Windows-only
действия не появляются в Mac или обычном браузере. HTMX swaps повторяют только
адресную инициализацию общей страницы.

Совместимость старого Mac здесь относится к выбору подписей, не поддержанию
retired notification v1: уточнение F277 требует v2 и понятного отказа v1.

`request_app_update` — дополнительный web-to-native intent version1 с текущим
nonce и строго пустым payload. Доступен только в ready-документе разрешённого
кабинета, не auth/payment/external/frame; stale/oversized/extra fields отвергаются.
Открывает нативную проверку обновления текущего пакета, не принимает URL,
путь, аргументы запуска, пакет или сертификат. Никакое web-сообщение не
подтверждает доступность обновления и не начинает установку. Нативный результат
привязан к generation; неизвестный/отсутствующий канал показан как unavailable,
а не как up-to-date. Установка — отдельное явное нативное действие после
проверки штатного источника, не во время захвата/финализации. Подпись, rollback,
сохранность и public release gate остаются обязательными.

### Handoff T106

Нормативная форма и фильтрация — `ProductAttributionHandoff`/Store в
`apps/macos/RecApp/Sources/Upload/ProductAttributionHandoff.swift` на `f5cca687a`.
Input: bridge/fallback/landing_path и пять utm_source/medium/campaign/content/term;
output: graf_attribution_ref/graf_attribution_fallback=1 и разрешённые метки/path.
При повторе query берётся первое значение; неверные поля отбрасываются отдельно,
не обязательно весь handoff. UTM после trim: ASCII A-Za-z0-9_.:-, до96 символов,
с дополнительным secret/phone filter Mac. Пустая кампания означает unknown.
Одна последняя валидная по схеме ссылка заменяет предыдущую; истёкшая через90дней
забывается. При ошибке записи сохраняется прежнее состояние, вход продолжается
без обещания сохранённой attribution; в лог допускается только bounded error code.
Различие Windows — доставка через MSIX protocol activation, не формат данных.

Проверки: неизвестный id, подмена действия/лишние поля, смена документа,
повтор сообщения, устаревшие разрешения, активная запись/отправка, отмена
подтверждения, ошибка хранилища. Ни одна ошибка не выдаётся за успешное удаление.

## 10. Календарное подключение T119 — 2026-10-02

Общий источник: F279 `contracts/calendar.md`, Mac
`EmbeddedCabinetCalendarJoinBridge`/`CalendarMeetingOpener` на master
`721b5125d799ea798a4af0b3625e18d3c1109039`. Это целевой контракт, не нынешний
runtime allowlist. Он заменяет прямой запуск сохранённого `meetingUrl` для Join,
не меняя F277 настройки/сроки карточек и не создавая Windows web UI.

### Запрос, документ и результат

Envelope §3, command `calendar_join`, payload ровно три строковых поля:
`action="joinCalendarEvent"`, `eventId`, `requestId`. Оба IDs — UUID8-4-4-4-12 hex
без скобок/лишних символов; сравнение после нормализации регистра. Request UUID
отличается от outer message_id. Extra/duplicate fields, URL/path/record flag,
неверные типы/UUID/replay отвергаются до resolver. Только current attached main
document approved origin с разрешённым `RouteKind::meetings` и актуальным nonce;
используется существующий точный list/inbox набор, без wildcard/API navigation.
Auth/settings/billing/payment/detail/review/external/frame не получают Join.

Shim перехватывает только `event.isTrusted` click `[data-calendar-join]` в capture
phase до standalone обработчика, включая keyboard activation; synthetic click
не отправляет intent. Делегированный listener работает после HTMX. До handshake
pending не создаётся. Одна pending операция во всём native приложении включает
кабинет/меню/карточки, resolver/launcher/browser dialog. Busy не ставит второй
launch в очередь: корректный запрос получает terminal cancelled. Корректный
запрос временно неготового, но всё ещё trusted document также получает cancelled;
malformed/untrusted не получает ответа. Invalidation отменяет операцию и снимает
pending ещё текущего документа перед отзывом nonce, не отвечает новому документу.

Display reply: command `calendar_join_reply`, nonce, request_id(UUID), state
`resolving/opening/handed_off/failed/cancelled`, optional safe reason enum
`busy/not_ready/stale/auth_required/event_unavailable/dependency_unavailable/
invalid_target/launch_failed/cancelled`; без URL/title/token/raw exception.
Shim сверяет nonce/request UUID/pending event и допустимый переход; terminal
снимает aria-disabled. Status/live region сообщает «Открываем…», «Ссылка передана
приложению», ошибку/отмену с явным повтором. Handoff не подтверждает вход во встречу.

### Resolver и актуальность

Existing authenticated GET `/api/v1/calendar/events/{event_id}/join-target`,
без redirects и URL во входе. HTTP200 JSON: event_id совпадает с запросом,
provider_family — строка≤64bytes, https_url — строка≤8192 UTF-8 bytes; whole
response≤64KiB/depth8. Existing strict JSON reader отвергает duplicate/missing/
неверные типы. provider_family сам по себе не разрешает и не запрещает custom
scheme: кандидат определяется только validated HTTPS host/path ниже. URL не кэшируется,
не логируется, не передаётся странице. 401 снимает только актуальный auth context;
404 — единая недоступность;503/network — временный отказ; malformed/URL/launch —
failed. Redirect/ошибка никогда не означает handed_off.
Resolver имеет общий монотонный deadline15s, не бесконечно обновляемый receive
timeout. Expiry даёт terminal failed/dependency_unavailable и отмену worker;
busy/lease держатся до actual completion. Новый явный запрос при ещё занятом
worker получает cancelled/busy; старый результат не выполняет launch.

Dispatch фиксирует origin/owner/workspace/auth generation/session token,
operation ID, document generation/nonce либо native action identity/epoch/deadline.
Token только в памяти transport. До/после каждого await, после dialog и прямо
перед launch/Record сверяется весь снимок. Logout/navigation/recreate, смена
контекста, close/replacement/expiry отменяют действие. HTMX обновление узла того
же доступного UUID сохраняет pending; исчезновение/смена UUID отменяет его.
Смена token отменяет даже при прежнем owner. Stale callback не освобождает busy
новой операции. Cancelled операция не создаёт отложенную очередь переходов.

### URL и Windows launcher

Один общий validator/opener заменяет reminder safeMeetingUrl + прямой ShellExecute.
HTTPS без userinfo/control/backslash authority; percent/IDNA host normalization,
numeric IPv4 inet_aton forms и IPv4-mapped IPv6 проходят Python3.13 is_global policy
сервер/Mac с global exceptions. Expected corpus:
`apps/server/tests/fixtures/calendar_join_host_policy.json` на указанном SHA;
его не менять. DNS hostname не доказывает адрес после DNS: новый DNS-pinning не
обещается. Query/fragment подключения сохраняются, порт0..65535 допустим.

Zoom/Teams candidates — только из validated HTTPS по exact host/path Mac
(zoommtg/msteams), не из provider_family. Телемост получает validated HTTPS через
штатную Windows association без выдуманного EXE пути/bundle ID/custom scheme.
provider_family описывает источник календаря и не выбирает приложение встречи:
значения calendar/unknown/zoom или другое допустимое значение не меняют выбор
по validated host/path. Например, provider_family=calendar со ссылкой
https://zoom.us/j/12345678901 допускает Zoom candidate; provider_family=zoom
с https://example.org/meeting не создаёт Zoom candidate. Native conversion только
без порта/на443; другой допустимый порт или отсутствие поддерживаемого сочетания
host/path приложения — browser-only. Для browser-only/recovery:
`Launcher::LaunchUriAsync` + `LauncherOptions.IgnoreAppUriHandlers=true`; для
native candidate — штатная URI association с preflight
`QueryUriSupportAsync(candidate, LaunchQuerySupportType::Uri)`. Available допускает
launch; подтверждённое отсутствие handler даёт validated HTTPS/browser-only,
как отсутствие приложения на Mac, без Store recommendation. Unknown/query
error/installed-unavailable не объявляются отсутствием: failed с явным recovery.
Перед OS dispatch проверяется current; уже переданную ОС ссылку нельзя отозвать,
но stale completion не меняет новый UI и не запускает Record. False/exception — отказ. Не передавать
GRAF auth/cookies/headers, не менять browser defaults, не запускать shell command.
Windows native association/результат API требуют отдельной installed проверки.

Native отказ предлагает «Открыть в браузере»/«Отмена», без второго автоматического
launch. Подтверждение запускает свежий resolver того же UUID и current/URL checks;
старый URL не используется. Menu/card «Повторить подключение» также разрешает
цель заново. Card закрывается только при handed_off. Background refresh failure
сохраняет failed Join той же сессии максимум5min после явной попытки и не продлевает
срок; auth/404/context/replacement/close/expiry/успешная новая проекция снимают его.
Join-and-record существует только нативно: handed_off → current → existing capture
prerequisites → Record; active/starting/paused/stopping/finalizing не допускают
предложения второй записи. Индикатор/Stop и автозапись не меняются.
