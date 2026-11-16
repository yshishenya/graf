# T112 — проверка проекта observer/native перед кодом

Дата:16.11.2026. Проверяющий: `/root/public_counter_readiness_review`.
Основа: `13edb699c1cee3c9b40808b44d3d8d3b0ba01852`.
Полоса `high-risk-product`, тот же незавершённый T112.

## Решение

**PASS проекта следующего изолированного шага; P1=0, P2=0.**
Предложенные узкий native интерфейс и observer соответствуют принятому
назначению §§3–5 при перечисленных ниже точных границах реализации.
Новых продуктовых требований или новых разрешений на сбор не требуется.
Все14/14 текущих документов F273/checklists/review/analyze совпали с
принятым срезом; отметки16/0 +27/0 +52/0 +29/0 = **124/0** сохранены.
Это не ревью ещё не написанного кода и не автоматическое закрытие его
проверок. После уточнения договора нужно сверить его изменившийся срез
и соответствие spec/plan/tasks/analyze до зависящего кода.

## Прочитанные ограничения и существующие образцы

Перечитаны §§3–5 `contracts/result-visibility.md`. Прочитаны целиком
`EmbeddedCabinetRecordingSettingsBridge.swift`,
`EmbeddedCabinetNotificationSettingsBridge.swift`,
`DesktopCabinetRoutePolicy.swift`, применимые разделы
`DesktopCabinetSessionBridge.swift`, coordinator activation/cookie
reconciliation/navigation/detach/content termination и JS native queues,
CSRF/route freshness обработчики. Старые unrelated механизмы очередей и
visibleRecordings не становятся источником доказательства результата.

Session generation содержит navigation barriers; cookie reconciliation
может изменить generation и публикует auth-session notification. Поэтому
активация должна брать итоговое поколение после завершения reconciliation,
проверять `isCurrentSession`, attached/current document и nonce, а не
сохранять поколение до асинхронного чтения cookies. Существующий coordinator
уже содержит образец guarded synchronization после authNavigation.value
или syncAuthSessionCookies; detach/navigation/termination имеют явные места
инвалидации.

## Точные инженерные границы следующего шага

- `GRAFResultVisibility.connect(nonce)/disconnect()/refresh()` допустим.
  Новый WK handler принимает только два ключа `{version:1,nonce}` с точными
  типами и текущим nonce, возвращает только `{version:1,ready:Bool}`. Нет
  identity/proof/text/URL, capture commands, состояния deletion или отправки
  аналитики через native. Старый клиент/нет bridge/timeout/неизвестный ответ
  дают отсутствие измерения без влияния на просмотр и запись.
- Native проверяет тот же WKWebView, main frame, source/current origin,
  точный текущий detail document, loading=false, attached coordinator,
  session generation/no barrier и актуальный nonce. Проверка foreground
  выполняется на MainActor: активное приложение и видимое не minimised
  окно с visible occlusion state. Никакого сетевого или файлового чтения
  для foreground-запроса не требуется.
- **Нельзя ограничиться `route.kind == .meetingDetail`.** В существующем
  `DesktopCabinetRoutePolicy` этот kind охватывает shared/public handoff,
  deletion-requests и calendar actions. Для нового handler нужен точный
  canonical owned detail path `/desktop/meetings/{UUID}` с проверкой
  percent-encoded пути и соответствия source/current document; соседние
  shared/action/settings/download routes не становятся разрешёнными.
  Разрешённые собственные query состояния detail не используются для
  конструирования POST target. Это конкретизация уже принятой границы,
  а не расширение полномочий route policy.
- Инвалидация охватывает navigation start, detach, content termination и
  auth generation, включая уже ожидающие async ответы. Активация после
  восстановления прежнего finished document также должна пройти тот же
  reconcile/current-document guard. Native refresh при active/occlusion/
  window изменениях лишь запускает повторную проверку, не доказывает показ.
- Observer работает на текущих непустых текстовых элементах и перед каждым
  POST после double RAF/async native response снова проверяет root/node/
  proof/CSRF/route, connectedness/ancestors/viewport/document visible/focus/
  not-prerender. Закрытые details и скрытые ancestors не проходят проверку.
  HTMX cleanup отключает старые узлы и отменяет/обесценивает ожидающие шаги.
- Target строится только из canonical собственного meeting UUID и
  browser/desktop alias, не из произвольного data URL/query. Same-origin
  credentials, CSRF header, JSON `{proof}`≤2KiB, bounded abort/response и
  отсутствие redirect к чужому адресу сохраняют собственную границу.
- Ошибка/timeout/неизвестный commit не запускают очередь или timer retry.
  `refresh()`, repeated intersection callback или смена nonce сами по себе
  не сбрасывают запрет повтора после ошибки при непрерывной видимости.
  Новая попытка требует настоящего нового перехода видимости. Реальная
  native inactive/occluded→ready также может быть таким переходом после
  повторной browser/frame проверки. Нет beacon/storage/persistent queue.

## Предлагаемый ответ будущего POST

Допустимо закрепить закрытые формы без изменения смысла событий:

- HTTP200 `{"status":"accepted"}` — только после подтверждённого общего
  durable admission/commit либо подтверждённого идемпотентного прежнего
  решения. Не по факту построения payload, записи первой части пары или
  начала commit; неизвестный commit не становится accepted.
- HTTP200 `{"status":"renewed","proof":"..."}` — без admission, только
  при истёкшем прежнем proof и неизменных свежих проекции/версии/основаниях
  доступа. Новый proof соблюдает прежние формат/TTL/≤1536bytes. Observer
  допускает одно обновление за visibility transition, затем заново проверяет
  frame/native и лишь после этого может отправить новый proof.
- Для аналитической неготовности достаточно закрытого
  `{"status":"unavailable"}`, без content/exception/reason text. Действующие
  безопасные auth/CSRF HTTP отказы сохраняются. Клиент принимает только
  перечисленные status и точные наборы/типы полей, unknown/malformed/лишние
  поля/oversized response не объявляет успехом и не повторяет автоматически.

Ответы private/no-store; ни proof, ни response body не идут в diagnostics
или provider transport. Эти формы — конкретизация инженерного интерфейса;
сам endpoint и общая T113 в текущем изолированном шаге не включаются.

## Предел и срез

Код, договор/spec/plan/tasks/checklists, Git/GitHub, рабочий сервер и
публикации не менялись; создан только этот отчёт. Тесты/сборки/native запуск
не выполнялись. Production issuance/POST/T113/recovery/T0 и полный T112
остаются закрытыми. Для Swift/native реализации обязательны отдельные
тесты lifecycle/forgery/stale-session/foreground и будущая ручная приёмка
единственного GRAF Dev по правилам проекта.

| Прочитанный вход | SHA-256 |
| --- | --- |
| `contracts/result-visibility.md` относительно F273 | `80f7d5eb7cd43bb9e3cff34bf689f9ce01f98095e527cb7afdaf3bca7f864f0e` |
| `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js` | `ed427987adad3e0eb570d0bb4c10c2a7049121f481dc8b68c616d054e173e3ee` |
| `apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetWebView.swift` | `67b74b03be03339f94ff6fa29c2186d790d5e363e622995ab30f6c6dc422bad1` |
| `apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetNotificationSettingsBridge.swift` | `90e5478b81f4b230e56a47bcae9ba056c131dc7f0947da2ddc20adf2002eebca` |
| `apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetRecordingSettingsBridge.swift` | `14a62a3581d42b252cd6f8dd88b234e856632b7c2f1e0fc5caac350b08cdd870` |
| `apps/macos/RecApp/Sources/Cabinet/DesktopCabinetSessionBridge.swift` | `89150f3ab781e1ea2edda7dbbd85cd3696850a956ac9f7f13817d7b08af3564f` |

## Повторная проверка уточнённого договора до кода

В том же диалоге полностью перечитан изменённый `result-visibility.md`,
прочитан полный [scoped design/analyze](t112-observer-native-design-20261116.md)
и проверен полный diff: добавлены ровно22 строки, другие положения договора
сохранены. Новый SHA-256 договора:
`ee1005b6a59ad1b42f0b7d0af25dd7099c8337a4d11930a3aba9ee6479d270d8`.
Старый хеш в таблице выше относится только к первоначальному preflight.

**PASS уточнённого договора; P1=0, P2=0.** Точные native ключи/ответ,
canonical owned path, итоговые nonce/generation после reconciliation,
инвалидация и запрет retry от неизменного refresh соответствуют выбранному
проекту. Закрытые accepted/renewed/unavailable ответы сохраняют durable
семантику и разделение renewal/admission, не расширяют event catalogue,
полномочия, содержимое, получателей, рабочее включение или продуктовую цель.
Прежние guards §§2–6, auth/CSRF, ограничения proof/body/budget, recovery и
запрет автоматических повторов остаются применимыми в полном объёме.

Согласованность FR-021/025/SC-006, прежней T112/#7698 и открытой T113
подтверждена по исходным spec/plan/tasks/quickstart и новому scoped analyze:
critical/high/medium=0 для этой конкретизации. Новая задача/публичный
комментарий для того же инженерного среза не требуется. Самостоятельного
нового live GitHub readback здесь не было; соответствие использует ранее
принятую mapping и неизменные документы задач.

Все остальные13/13 входов совпали с принятым состоянием. Итог четырёх
reviewer-owned списков повторно пересчитан:requirements16/0,security27/0,
privacy52/0,infra29/0 — **124/0**. CHK047/048/050/051/052 остаются
подтверждены по уточнённому договору; изменения отметок не понадобились.
Можно продолжать зависящий изолированный observer/native код с последующим
независимым implementation review и причинными тестами. Первый browser RED
исполнителя не выдаётся за собственный запуск reviewer или рабочую приёмку.
Код/spec/plan/tasks/checklists/Git/GitHub/runtime не менялись этим проходом;
дополнен только настоящий отчёт. Полный T112/T113 и production закрыты.
