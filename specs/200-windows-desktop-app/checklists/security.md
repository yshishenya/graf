# Security Checklist: Windows desktop-приложение GRAF

**Purpose**: Проверить требования к WebView2 trust boundary, локальной custody,
секретам, диагностике, удалению и стандартному пользовательскому контексту.
**Created**: 2026-08-23
**Feature**: [spec.md](../spec.md), [windows-native-web-bridge.md](../contracts/windows-native-web-bridge.md)

**Review Ownership**: Отметками управляет независимый рецензент требований.
`[X]` означает, что качество требований по критерию признано достаточным, а не
что реализация или испытания завершены. `$speckit-implement` читает эти отметки
как условие продолжения и не меняет их.

## WebView2 и навигация

- [X] CHK001 Trusted origin нормализуется по scheme/host/port и не разрешает broad substring-проверки вроде `contains("desktop")` или `contains("meeting")`. [Clarity, Bridge §Trusted origin]
- [X] CHK002 Approved route kinds перечислены для meetings, detail, settings, auth recovery, share и deletion report; native-only и неизвестные пути имеют отдельный результат. [Completeness, Bridge §Trusted origin]
- [X] CHK003 Redirect, cross-frame navigation, `file:`, `data:`, `javascript:`, local filesystem, loopback development и external browser handoff имеют явную policy. [Coverage, Bridge §Navigation lifecycle]
- [X] CHK004 WebView2 Evergreen availability, runtime repair и failure state не превращаются в permission error и не блокируют native capture/local custody. [Consistency, Spec §FR-020, §Edge Cases]
- [X] CHK005 AreHostObjectsAllowed, COM host object policy, script dialogs, capability scope и standard-user execution явно ограничены. [Completeness, Bridge §WebView2 settings]

## Bridge protocol

- [X] CHK006 Однозначно ли согласованы форматы направлений: каждый web-to-native запрос содержит protocol, version, direction, message id, ephemeral session nonce, origin, typed payload и monotonic send time; `native_ready` использует оболочку с `native_to_web`, а `local_recordings` — отдельное сообщение отображения `command/nonce/rows`, без требования общей оболочки для всех сообщений? [Consistency, Spec §FR-006, §Key Entities; Bridge §§3–4; Data Model §8]
- [X] CHK007 Origin/source, document/session boundary, direction, schema, payload size/depth, message replay и nonce rotation имеют измеримые правила отказа. [Measurability, Spec §FR-006]
- [X] CHK008 Согласован ли минимальный список запросов — только `request_app_quit` с точным `{"action":"quit"}` и `local_recording` с ровно двумя строковыми полями `action: open|send|delete` и известным локальным `id`? Определены ли ожидание нативной финализации перед выходом, проверка текущего документа/nonce и разрешения строки, повторная проверка состояния и границ хранилища перед действием, нативное подтверждение удаления и его запрет при записи/отправке; исключены ли произвольный путь и прежние settings/diagnostics/repair/ack-команды, управление захватом, файлами, процессами и секретами? [Least privilege, Bridge §§5, 8; Desktop Contract §§3, 7; Tasks §User Story 2]
- [X] CHK009 Определён ли состав только действующих native-to-web сообщений `native_ready` и `local_recordings`: инициализация и строки отображения с непрозрачным локальным id, фиксированным названием, временем/длительностью и флагами состояния/действий, без file paths, device/process handles, cookies, tokens, raw samples, transcript text, signed URLs и приватного содержимого встречи; исключены ли прежние `capture_state`/`custody_summary`/`runtime_state`? [Data boundary, Bridge §§4, 8; Research §Решение 2; Data Model §8]
- [X] CHK010 Однозначно ли запрещены `ack`/`ack_display` и использование `native_ready`, отображения строк или ответа веб-страницы как доказательства сохранения, отправки, server acceptance либо удаления? Указано ли, что факты устанавливают только нативные файлы/очередь и подтверждённое серверное состояние, а локальное удаление не доказывает серверную очистку? [Truthfulness, Bridge §§4–5, 8; Data Model §§7–8; Desktop Contract §7; Spec §Key Entities; Tasks §T031]
- [X] CHK011 Ошибка/закрытие/recreate WebView инвалидирует nonce и bridge state, но не изменяет native session state. [Recovery, Bridge §Navigation lifecycle]

## Локальная custody и egress

- [X] CHK012 Local recordings ограничены user-scoped app-data directory, имеют user-only ACL, temp-plus-atomic-rename и bounded flush/error semantics. [Completeness, Spec §FR-012]
- [X] CHK013 Queue ledger имеет atomic write, malformed-document quarantine и recoverable backup; пустая очередь не может молча заменить повреждённую. [Durability, Spec §FR-013]
- [X] CHK014 Upload egress ограничен существующими GRAF desktop APIs; MediaScribe/MinIO/provider credentials и direct traffic отсутствуют в Windows boundary. [Secret discipline, Spec §FR-014]
- [X] CHK015 Local purge признаётся только после deletion/tombstone/cryptographic unrecoverability proof, а server deletion truth не подменяется локальным флагом. [Deletion, Spec §FR-022]
- [X] CHK016 Update/uninstall/rollback сохраняют или явно обрабатывают local packages, queue, auth profile policy и не удаляют данные неявным clean-up. [Recovery, Spec §SC-008]

## Diagnostics и supply chain

- [X] CHK017 Metadata-only diagnostics перечисляют разрешённые поля и запретные поля на уровне contract, включая local absolute paths и process command lines. [Completeness, Spec §FR-021]
- [X] CHK018 Audio buffers, transcripts, private meeting ids, credentials, cookies, signed URLs и raw response bodies исключены из committed evidence, logs, screenshots и support bundles. [Privacy, Spec §Repository Hygiene]
- [X] CHK019 Pinned AEC3 source revision, license notices, hash/identity и reproducible build inputs имеют owner и evidence path. [Supply chain, Plan §Phase 0]
- [X] CHK020 Package signature, architecture, Windows App SDK dependency, WebView2 runtime channel и rollback proof входят в release-readiness criteria до распространения. [Packaging, Spec §FR-020]
- [X] CHK021 Native host, WebView2 and audio capture run without elevation, driver, system service or privileged audio component. [Privilege, Spec §FR-019]
- [X] CHK022 Threat scenarios include hostile origin, stale nonce, replay, malformed/deep/oversized payload, untrusted redirect, WebView close during capture and missing runtime. [Coverage, Bridge §Security tests]

## Первоначальное подтверждение владельца записи

- [X] CHK023 Достаточно ли точно определён безопасный двухшаговый запрос `GET /desktop/settings/spaces` → `GET /api/v1/auth/me`: один неизменный снимок сессии на разрешённом GRAF origin, без перенаправлений и только HTTP 200; первый запрос без `X-Workspace-Id`/`X-Device-Id`; строгая структура JSON и типы без преобразований, отказ при повторных ключах/UUID, ровно один `active: true` с корректным строковым UUID, предел 2 MiB на ответ и 1024 элемента с отказом целиком; совпадение `/me.workspace_id` с выбранным UUID, корректные строковые `user_id`/`active_session_id`; отмена до/после каждого запроса и запрет применения результата старого поколения входа; неизменность установленного владельца и отсутствие полномочий серверной очистки локальных копий? [Completeness, Measurability, Desktop Contract §7; Plan §Уточнение T083; Research §Уточнение T083; Gap]

## Независимая проверка требований — 2026-09-06

Область: CHK006/008/009/010 и новый CHK023 в текущей рабочей копии Feature 200.
Рецензент не менял реализацию. Остальные отметки сохранены без повторной оценки.
Режим проверки — ограниченная проверка документации внутри действующего
высокорискового среза Spec Kit; это не разрешение выпуска и не доказательство
работоспособности Windows. Навык `speckit-checklist` применён для оценки
полноты, однозначности и согласованности требований, не для закрытия реализации.

### Результат и необходимые уточнения

- **CHK006 — не выполнен.** Bridge §§3–4 и Data Model §8 правильно разделяют
  запросы и отображение. Но `spec.md` FR-006 всё ещё требует versioned JSON
  envelope для всего `Native↔WebView communication`, а Key Entities объединяет
  `command/event` в одной сущности. Нужно явно ограничить требование оболочки
  запросами и описать исключение `local_recordings`, сохранив его привязку к
  текущему документу/nonce. Добавлять оболочку в реализацию ради старого текста
  не требуется.
- **CHK008 — не выполнен из-за несогласованности документов.** Bridge §§5, 8
  задаёт ровно два запроса, ограниченные действия над известной записью и
  повторную нативную проверку; Desktop Contract §3 требует ожидать завершения
  worker/writer и сохранения очереди перед выходом. Однако цель User Story 2
  в `tasks.md` всё ещё обещает открытие native settings/diagnostics через мост.
  Её нужно согласовать с отказом от этих команд, не возвращая обработчики.
- **CHK009 — выполнен по качеству требований.** Bridge §§4, 8, Data Model §8
  и Research §Решение 2 явно ограничивают сообщения и поля, запрещают пути,
  секреты и содержимое записи. `local_recordings` — отображение, не доступ к
  файловой системе и не новое разрешение нативного действия.
- **CHK010 — не выполнен из-за несогласованности документов.** Bridge §§4–5
  и Data Model §8 запрещают подтверждения веб-страницы, но `spec.md` Key Entities
  сохраняет `acknowledgement/error`, а T031 в `tasks.md` — `bounded ack/error`.
  Нужно удалить обещание протокольного ack и отделить внутренний отказ проверки
  от ответа веб-странице; не вводить ack как доказательство сохранения/отправки.
- **CHK023 — пока не выполнен.** Desktop Contract §7 уже определяет одну сессию,
  HTTP 200, запрет перенаправлений, численные пределы, подтверждение через `/me`,
  отмену/поколение входа, сохранение владельца и отсутствие полномочий очистки.
  Не хватает явной схемы `{"spaces":[...]}` и правила отказа целиком при
  повторных JSON-ключах, повторных UUID и неверных типах элементов, включая
  неактивные. Например, строка `active: "false"`, элемент не-объект или
  повторный `id` не должны молча пропускаться ради другого допустимого элемента.
  Упоминание «строгие типы/дубликаты» в плане не определяет эти исходы.
  Нужно также явно назвать строковый UUID-тип всех трёх идентификаторов `/me`.
  Уточнения должны появиться в контракте до одобрения критерия; отсутствие
  ещё не написанной реализации само по себе не является причиной этой отметки.

### Прочитанные доказательства и границы проверки

- `WebViewBridge::isAllowedWebCommand` допускает только два действующих запроса;
  `WebView2Host::WebMessageReceived` проверяет источник, размер, оболочку и точные
  поля действия. `localRecordingActionAllowed` проверяет известный id и текущее
  разрешение строки. Отправка `native_ready` и `local_recordings` соответствует
  двум разным форматам Bridge §4; обработчика ack нет.
- `AppMain.cpp` связывает quit с `requestExit` и закрывает окно из
  `refreshNativeState` только после исчезновения нативного индикатора;
  `isCaptureState` включает `stopping/finalizing`, а `finishStop` ждёт worker
  и результат финализатора. Локальные действия повторно проверяют запись и
  корень хранилища; open выбирает фиксированный `meeting-review.m4a`, delete
  требует отдельного подтверждения и снова проверяет запись/отправку.
- Прочитаны `WebViewBridgeEnvelopeTests.cpp`, `NativeCaptureWebFailureTests.cpp`
  и относящиеся к завершению сценарии `CaptureFaultStateTests.cpp`: запрет
  прежних команд, nonce/replay/direction/size/depth, неизвестный id, разрешения
  строки, отзыв разрешения и ожидание финализатора. Это чтение исходников
  тестов, не отчёт об их успешном запуске и не сквозная проверка WinUI.
- Для CHK023 прочитаны серверные `cabinet/web_routes/spaces.py`,
  `auth/workspace_onboarding.py`, `api/auth.py` и соответствующий сценарий
  `test_auth_contracts.py`. Два пути spaces используют один обработчик JSON;
  `active` вычисляется сервером для текущего пространства. Тест обращается к
  `/settings/spaces`, а не напрямую к `/desktop/settings/spaces`, и подтверждает
  отсутствие внутреннего пространства авторизации и активность текущего.
  `/me` выдаёт `active_session_id` только для совпадающих пользователя,
  пространства и сессии. Текущий `DesktopHttpTransport::accountIdentity`
  ещё выполняет одиночный `/me`; новый алгоритм не считается реализованным.
- UI, виртуальная машина, захват звука, сетевые запросы, сборка и тесты не
  запускались. Изменён только этот файл; commit/push не выполнялись.

### Повторная независимая проверка — 2026-09-06

Перечитаны только исправленные FR-006/Key Entities в `spec.md`, цель US2/T031
в `tasks.md` и §7 `windows-desktop-contract.md`. Все четыре замечания выше
устранены; их первоначальное описание сохранено как история проверки.

- **CHK006 — выполнен:** запросы, `native_ready` и отдельный формат
  `local_recordings` согласованы; привязка к документу/nonce сохранена.
- **CHK008 — выполнен:** цель US2 допускает только quit и типизированные
  действия над известной записью с повторной нативной проверкой; прежние
  команды не возвращены. Требования ожидания финализации и локальных границ
  действий из предыдущей проверки остаются обязательными.
- **CHK010 — выполнен:** Key Entities и T031 отделяют внутренние коды отказа
  от веб-подтверждений; `ack`/`ack_display` не поддерживаются и не доказывают
  сохранение, отправку или удаление.
- **CHK023 — выполнен:** явно заданы схема spaces, типы всех элементов,
  включая неактивные, отказ всего ответа при дубликатах/повреждении и строковые
  UUID `/me`. Сохранены одна сессия через `X-Auth-Session`, пределы 2 MiB/1024,
  HTTP 200 без перенаправлений, совпадение пространства, отмена/поколение входа,
  неизменность установленного владельца и отсутствие полномочий очистки.

Итог: проверка требований по этим четырём пунктам пройдена; открытых замечаний
в области повторной проверки нет. Изменены только четыре отметки и добавлена
эта запись в `security.md`; остальные отметки и предыдущая проверка сохранены.
Режим — проверка документации; это не подтверждение реализации, испытаний или
готовности выпуска. UI, VM, аудио, сборка, тесты и commit/push не запускались.

## Уточнение Constitution 7 — требования к границе запуска

- [X] CHK024 Явно ли исключены юридическая политика пространства, уведомление участников и подтверждение согласия из условий ручной/автоматической записи для всех пользователей, без подмены фиктивным разрешением? [Consistency, Spec §Контекст и цель, §FR-004; Constitution §II]
- [X] CHK025 Полностью ли перечислены сохранённые технические условия старта и отделены ли от них неизменные права доступа к серверным данным, владение записью и подтверждение удаления? [Completeness, Spec §Контекст и цель; Desktop Contract §§2–3, 7]

### Независимая проверка снятия юридических условий — 2026-09-06

**PASS — CHK024/025.** Область ограничена изменением условий запуска по
Constitution 7.0.0; прежние пробелы всей Feature 200 не переоценивались.

- CHK024: Constitution §II, `spec.md:57–75,286–290`, `plan.md:19–27` и
  Desktop Contract §2 исключают юридическую политику, уведомление/согласие
  и серверное подтверждение для ручной записи, transcript-only и автозаписи,
  одинаково для внутренних/внешних пользователей. Замена проверок фиктивным
  разрешением запрещена; PRD §25 и Product Gates согласованы.
- CHK025: `spec.md:67–75`, Desktop Contract §§2–3,6–7 сохраняют разрешения ОС,
  input/render, форматы, AEC3/AAC, атомарное хранилище, единственную сессию,
  индикатор до захвата и Stop после отказа. Для автозаписи дополнительно
  обязательны подтверждённая текущая встреча, точное приложение, локальный
  трёхрежимный выбор и подавление повторов. Авторизация отправки, неизменность
  владельца, границы данных и доказательство удаления не отменены; отказ
  `/auth/me` блокирует отправку, не локальную запись.
- Связь с реализацией определена: `tasks.md:319–320` (T081/T082) и
  `plan.md:19–27` требуют удаления обоих устаревших полей и причин отказа,
  проверки позиционных инициализаций и последовательных правок AppMain.
  `quickstart.md:47–53` задаёт положительные сценарии и отдельные технические
  отказы; Data Model §9 и Research §8 не возвращают юридических условий.

Режим — ограниченная проверка требований действующего высокорискового среза
Spec Kit с `speckit-analyze`; это не подтверждение реализации или выпуска.
Изменены только две отметки и эта запись. Код, VM и частные данные не
просматривались; сборки, тесты, сетевые операции и commit/push не выполнялись.
