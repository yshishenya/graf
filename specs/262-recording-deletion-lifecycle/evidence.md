# F262: реализация и проверенные границы

Дата: 2026-09-09. Ветка: `codex/262-recording-deletion-lifecycle`.
Risk/validation lane: **high-risk product area / full Spec Kit** (удаление, хранение, авторизация, интерфейс).

Основной код опубликован в PR #6911. Итоговая приёмка и исправления продолжаются; T019–T023 пока открыты. Production и выпуск не выполнялись.

База после rebase: `1768d78e5` (master). Первый опубликованный/установленный SHA F262: `2c9ffc01112d0584b53ff3cd5f1498ec1054f005`. Последующие исправления ниже пока относятся к рабочему снимку; [source-files.sha256.json](source-files.sha256.json) связывает проверенные исходники/тесты. Итоговый exact SHA будет записан в PR после проверки и коммита.

## Дополнительная приёмка 2026-09-09 UTC (журналы 2026-09-10 +05)

- GRAF Dev на `2c9ffc01112d0584b53ff3cd5f1498ec1054f005`: штатные build/promote PASS, smoke **13/13 PASS**, схема `0092_recording_origin_cancel`. Логи `/tmp/graf-262-pr-build.log`, `/tmp/graf-262-pr-promote.log`, `/tmp/graf-262-pr-smoke.log`.
- В установленном GRAF Dev создан и удалён только синтетический WAV. Space меняет выбор, Escape закрывает подтверждение и возвращает фокус на флажок, счётчик согласован. После подтверждения встреча исчезла, поиск показывает 0. Найден дефект: завершённая карточка загрузки сохранила ссылку. Исправление ожидает повторной установленной проверки.
- Дополнительная независимая проверка обнаружила поздний XHR после web-delete: сервер уже удалил встречу, но ответ загрузки возвращал карточку. Теперь страница запоминает отозванный meeting ID и не публикует позднюю ссылку. Chromium regression воспроизводит реальный порядок upload → delete → late response, а также remote deletion/unavailable. **3 PASS**, отрицательная проверка без исправления падает: `/tmp/graf-262-manual-upload-deletion.log`.
- Mixed-list Chromium, включая pending → rejected с однократным обновлением и удаление карточки завершённой загрузки: **PASS**, `/tmp/graf-262-upload-revocation-browser.log`.
- Swift: итоговый тематический набор **190 PASS**, `/tmp/graf-262-precommit-native.log`; прежний набор **186 PASS** после исправлений capability/target 404, `/tmp/graf-262-final-pr-native.log`. AVPlayer/AVPlayerView/NSWindow release/revoke/replacement: **1 PASS**, `/tmp/graf-262-player-release.log`; это компонентная проверка, а не установленный пользовательский путь.
- SC-006: **100 пакетов по 100 MiB**, фактическая очистка **0,370283 с**, 100 повторных чтений и restart очереди без возвращения строк: `/tmp/graf-262-hundred-max.log`. Это один контрольный запуск, не p95 и не смешанные серверные операции.
- PostgreSQL0091 →0092 с сохранением всех колонок существующих meeting/request/purge tasks; атомарный отказ при дублях; отказ downgrade с сохранением marker/history: **3 PASS**, `/tmp/graf-262-migration-acceptance.log`.
- Capability protocol version1 подтверждается до мутации, старый сервер не получает DELETE; недоступная отдельная цель не блокирует следующие операции и не разрешает purge. **15 PostgreSQL PASS**, `/tmp/graf-262-review-fixes-server.log`; native проверки включены в набор выше.
- Первый GitHub `governance-fast` на `2c9ffc0…` не прошёл: 4 ошибки устаревших unit fixtures (inventory marker, schema head, request URL). Исправления проверены: **52 PASS**, `/tmp/graf-262-ci-regressions.log`. Новый required run ещё ожидается.
- Общий Spec Kit checker с закреплённым CLI: **PASS**, `/tmp/graf-262-governance-local.log`. Первоначальный конфликт установленного CLI/lock не был дефектом F262; использован совместимый runtime, lock не изменялся.

- SC-004: отдельный тест 100 смешанных команд через настоящие queue/client. Первый проход 33 accepted/33 rejected/34 resolving; restart и повтор только pending дают67 accepted/33 rejected. Ни одна ошибка не считается успешной очисткой: `RecordingDeletionBulkAcceptanceTests` PASS.
- Заполненная legacy v2 очередь: **2 Swift PASS**. Неизвестный/чужой владелец сохраняет файлы и запрещает действия; подтверждённый owner+deleted сохраняет запрет после restart. `RecordingDeletionLegacyAcceptanceTests`.
- Восстановленные старые аудио/расшифровка с сохранённым tombstone: **1 PostgreSQL PASS**. API/web/desktop/download/playback не раскрывают возвращённое содержимое; другая встреча доступна. `test_recording_deletion_restore_fence.py`. Это не разрешение восстанавливать полную старую БД с потерей markers.
- Chromium acceptance: **6 PASS** — замороженный mixed selection, изменение фильтра во время подтверждения, последняя строка/фокус/поздний HTML, 200 видимых aliases порциями≤100, частичный сетевой сбой, настоящий30-секундный polling. Измерение SC-003: remote30006мс, reconnect7мс, один образец, `/tmp/graf-262-timing-selection-browser.log`.
- Проверка замороженного выбора выявила попадание новой невыбранной local строки через `undefined` identity. Исправлено: обновление DOM сохраняет исходный набор и использует общую identity. В больших списках lifecycle больше не пропускает серверные строки за карточками загрузки; успешная порция обновляет счётчик даже при последующей503.
- Chromium recovery: **2 PASS** — настоящий offline без запроса на сервер и без обещания сохранённой команды; явный повтор после подключения; повторный импорт того же WAV с другим origin и meeting ID. `/tmp/graf-262-deletion-recovery-browser.log`.
- Неизменённые защитные проверки harness/schema transition: **68 PASS**, `/tmp/graf-262-pr-check-harness.log`. Они подтверждают границу допуска новых writers и запрет отката к старой схеме, но не заменяют установленную проверку совместимого восстановления.
- Итоговый независимый просмотр `deletion_release_review`: открытых подтверждённых P1/P2 в исправлениях нет; Ponytail review не требует новой инфраструктуры/зависимостей.

## Подтверждённая причина

Старый `renderLocalRecordingRows` добавлял копию при отсутствии серверной строки (`!serverRow || uploadComplete !== true`). Отсутствие строки после удаления превращало retained local alias обратно в видимую запись. У локальной строки не было рабочего флажка. Native проверка открытия не учитывала весь lifecycle/access, а `NSWorkspace.open` передавал файл внешней программе, которую GRAF уже не мог остановить.

## Реализованные инварианты

- Серверная identity никогда не становится local-only из-за отсутствия в выдаче. Сервер определяет фильтры и страницы связанных встреч.
- В queue v3 одна коллекция deletionOperations, включая server-only; принадлежность, попытка создания и факт удаления различаются.
- Долговечный intent/tombstone сохраняется до сети/файлов. Нет загрузки и открытия после intent, принятого удаления или неподтверждённого доступа.
- Accepted/verified требуют подходящего receipt. Неизвестный исход и отсутствие локального пакета не считаются физической очисткой.
- Origin cancellation использует PostgreSQL transaction lock, общий с create; отменённый origin не создаёт фиктивную Meeting и не используется повторно.
- Повтор meeting-delete возвращает прежний receipt. Существующие deletion epoch, purge journal и downstream guards сохранены.
- Истёкшее задание может принять проверенный поздний ACK. Новая регистрация устройства получает отдельное задание и не подтверждает старое.
- Смена аккаунта закрывает локальный плеер и отключает чужие команды/метаданные. HTTP execution scope сверяется сервером до изменения данных.
- Флажки, замороженный набор, перенос alias/focus, частичный результат и повтор используют один native executor. В старом bridge локальное удаление требует обновления приложения.
- AVKit player заменяет внешнее открытие. Native intent и серверное согласование отзывают управляемый контент; результат каждой операции публикуется до окончания всего набора.
- Локальная очистка не зависит от сетевого успеха другого запроса. Ошибка одного пакета не мешает другому; unsafe path не удаляется.
- Состояние незавершённой очистки, ожидание сервера/входа/обновления и существующие deletion reports доступны пользователю.

## Первоначальные проверки до дополнительных исправлений

Все данные синтетические. PostgreSQL runner создавал отдельный disposable контейнер и удалял его после прогона. В graf-dev добавлялась и удалялась только собственная синтетическая встреча для приёмки.

| Проверка | Результат | Запись запуска |
|---|---|---|
| SwiftPM: RecordingDeletionLifecycleTests, DesktopUploadQueueTests, DesktopMeetingShellWebViewBoundaryTests, DesktopLocalPurgeTests, DesktopUploadCustodyProjectionTests, DesktopUploadClient* | **PASS, 183 теста**; продукт также скомпилирован | `/tmp/graf-262-validated-native.log` |
| PostgreSQL: origin cancellation, local purge, HX delete feedback, CSRF, deletion access, sync conflicts, workflow deletion races | **PASS, 42 теста** | `/tmp/graf-262-final-backend.log` |
| PostgreSQL: deletion feedback/index и изоляция чужого workspace | **PASS, 7 тестов**, 6 пересекаются с предыдущим набором | `/tmp/graf-262-access-reviewed-backend.log` |
| Реальный Chromium: mixed list, семь сортировок, фильтры, local→server selection/focus, retained deletion после HTMX, native bulk, несовместимый bridge, нейтральное account recovery | **PASS** | `/tmp/graf-262-handoff-browser.log` |
| Chromium: playback-refresh, playback-comments, protocol-source | **PASS**, сохранение audio/comment UI и точных ссылок на ревизию | `/tmp/graf-262-playback-refresh.log`, `/tmp/graf-262-playback-comments.log`, `/tmp/graf-262-protocol-source.log` |
| Ruff для всех изменённых Python-файлов | **PASS** | `/tmp/graf-262-final-lint.log` |
| `node --check cabinet.js`, `git diff --check` | **PASS** | локальный stdout |
| `validate-changelog-fragments.py` | **PASS** | `/tmp/graf-262-fragment.log` |
| Общий `check_spec_kit_governance.py` | **FAIL**, несовпадение installed tool/lock | `/tmp/graf-262-governance.log` |

43 различных серверных integration tests прошли двумя прогонами. Ранние неуспешные прогоны не считаются доказательством: исправлены default callback нового типа, fixture принадлежности аккаунту, передача уже встроенного шаблонного time helper и неверное смешение correlation request_id с deletion receipt ID.

Проверка гонки cancel/create содержит два управляемых порядка: первый запрос удерживает origin lock, второй доказанно приходит до его освобождения; после commit поздний create отклоняется. Проверка RLS исполняется не от PostgreSQL superuser. Тест нового устройства проверяет разные task_id и отсутствие ложного ACK старой регистрации.

## Покрытие S01–S51

`AUTO` ниже означает проверку конкретного автоматического инварианта, **не** полную приёмку сценария во всех клиентах. `PARTIAL` требует дополнительных runtime/интеграционных доказательств. Ни один такой статус не заменяет T019/T022/T023.

| Сценарии | Текущее доказательство | Остаток |
|---|---|---|
| S01–S06 | AUTO/PARTIAL: repeat receipt, durable restart, mixed-list/HTMX, действие после intent заблокировано | установленный клиент и полный цикл до очистки |
| S07–S08 | AUTO/PARTIAL: offline never-submitted tombstone, атомарная запись, файлы и retry | реальное отключение сети/перезапуск UI |
| S09 | NOT RUN: browser offline end-to-end | проверить ошибку и отсутствие обещания долговечной команды |
| S10–S12 | AUTO: cancel/create в обоих порядках, lost-create identity, repeat | проверить с установленным клиентом |
| S13–S14 | AUTO/PARTIAL: существующие sync/workflow deletion races; callback guards | задержанные реальные part/finalize и обработчики при runtime-приёмке |
| S15–S17 | PARTIAL: saving/action guards и существующие queue/artifact regressions | активный writer, остановка и повреждённый реальный пакет |
| S18–S23 | AUTO/PARTIAL: checkbox, alias/focus, bulk, фильтры/счётчики/HTMX | полная смешанная выборка, пустой список, 100 повторов |
| S24 | PARTIAL: bounded origin/meeting lookup, независимый цикл, reconnect triggers | два активных устройства и SC-003 |
| S25–S26 | AUTO: expired→verified ACK, separate new-device task | Mac после долгого offline |
| S27–S29 | AUTO/PARTIAL: scope, request headers, unknown access, deletion precedence | смена сессии во всех задержанных sibling callbacks |
| S30–S31 | PARTIAL: AVKit source release и bounded deletion copy реализованы | прослушивание/seek в GRAF Dev; внешние копии вне контроля |
| S32–S36 | AUTO/PARTIAL: ошибка одного пакета, unsafe path, missing package, atomic-save failure | crash между unlink/ACK, частичный реальный файловый отказ |
| S37–S38 | AUTO/PARTIAL: legacy/future schema, corrupt queue guard, owner reconciliation | существующие legacy ghosts и восстановление состояния |
| S39–S40 | PARTIAL: old bridge требует обновления, future queue не перезаписывается, migration downgrade запрещён | полная таблица binary/store/server совместимости и rollback |
| S41 | PARTIAL: браузерный focus/checkbox/dialog | VoiceOver, клавиши и реальное native окно |
| S42–S43 | PARTIAL/NOT RUN: прежние серверные fences сохранены | отказы зависимостей и backup restore |
| S44–S46 | AUTO/PARTIAL: per-operation monotonic state, bounded payload, server-only store | 100 объектов, несколько окон, задержанные общие ответы |
| S47 | AUTO/PARTIAL: explicit local-unbound/owner split, offline local deletion | полный путь новой записи до выбора аккаунта |
| S48–S49 | NOT RUN: явный повторный импорт и manager другого creator | отдельные acceptance сценарии |
| S50 | AUTO: cancellation без Meeting/FK; accepted без пакета не verified | пользовательский путь в installed app |
| S51 | PARTIAL: meeting lookup, access resolver и browser revocation | две сессии, открытая чужая встреча |

SC-003 измерен в Chromium, SC-006 на файловой системе; см. дополнительные результаты выше. Установленные части SC-002/007 ещё проверяются. p95 не заявляется. Актуальное сопоставление каждого сценария: [scenario-evidence.md](scenario-evidence.md).

## Обновление и откат

1. Сначала новый сервер и миграция 0092, затем клиент. Миграция сохраняет отрицательные origin markers и останавливается при старых дублированных purge tasks; автоматически удалять доказательства нельзя.
2. Queue v1/v2 читаются и переводятся в v3; неопределённая принадлежность не разрешает auto-upload, просмотр или удаление. В интерфейсе есть нейтральное сообщение о проверке исходного аккаунта, без чужих названий и времени.
3. Бинарник, выпущенный до v3, не знает deletionOperations. Откат такого бинарника поверх v3 — неподдерживаемая комбинация, которую нельзя считать безопасной.
4. Downgrade миграции блокируется, чтобы не стереть origin tombstones. Восстанавливать можно совместимый сервер/клиент с сохранением новых fences, а не старый queue поверх удаления.
5. Строка «удалено» не означает очистку всех резервных, внешних и выгруженных копий. Действующие retention/observability policies не менялись.

Issue canon: штатный post-hook PASS (300 возвращённых issues), отдельная проверка F262 23/23 PASS, все issues OPEN. Прежняя ошибка #6852 при отдельной текущей проверке отсутствует; чужая issue здесь не менялась.

## Незакрытые обязательные этапы

- T019/T022: точное сопоставление S01–S51, итоговый GRAF Dev, управляемый плеер, VoiceOver, SC-003/004/007. SC-006 уже измерен отдельно.
- T023: поддерживаемое восстановление v3/0092 без потери tombstones; старый бинарник поверх v3 не поддерживается. Миграционные проверки существующей БД выполнены.
- T020/T021: итоговая независимая проверка/конвергенция и `governance-fast` на точном SHA. Выпуск отдельно требует frozen candidate/release-full и обычные macOS gates.

Предыдущая установленная версия не подтверждает последующие изменения. Финальная приёмка не объявляется выполненной до повторного build/promote/smoke и проверки сценария.
