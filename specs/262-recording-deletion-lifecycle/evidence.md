# F262: реализация и проверенные границы

Дата: 2026-09-09. Ветка: `codex/262-recording-deletion-lifecycle`.
Risk/validation lane: **high-risk product area / full Spec Kit** (удаление, хранение, авторизация, интерфейс).

Основной код реализован, но фича **не завершена и не готова к выпуску**: открыты T019–T023. Коммита, PR, push, установки новой версии и production-изменений нет.

База: `bc41c10bf7a561c04c8a51d2a034dd6d75a36aad`. Это исходный HEAD, а не SHA реализованных изменений. Код пока незакоммичен. Файлы кода/тестов привязаны к [source-files.sha256.json](source-files.sha256.json); SHA256 этого снимка: `57b9d6ee089e5a089f92178e3b6a746b431c2c6dcc9e52ddeaa4ebc62a889c54`. Он не заменяет обязательный точный SHA коммита для CI и стенда.

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

## Выполненные проверки

Все данные синтетические. PostgreSQL runner создавал отдельный disposable контейнер и удалял его после прогона. Данные действующего graf-dev не изменялись.

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

SC-002/003/006/007 не измерены; p95 и выполненная полная матрица не заявляются.

## Обновление и откат

1. Сначала новый сервер и миграция 0092, затем клиент. Миграция сохраняет отрицательные origin markers и останавливается при старых дублированных purge tasks; автоматически удалять доказательства нельзя.
2. Queue v1/v2 читаются и переводятся в v3; неопределённая принадлежность не разрешает auto-upload, просмотр или удаление. В интерфейсе есть нейтральное сообщение о проверке исходного аккаунта, без чужих названий и времени.
3. Бинарник, выпущенный до v3, не знает deletionOperations. Откат такого бинарника поверх v3 — неподдерживаемая комбинация, которую нельзя считать безопасной.
4. Downgrade миграции блокируется, чтобы не стереть origin tombstones. Восстанавливать можно совместимый сервер/клиент с сохранением новых fences, а не старый queue поверх удаления.
5. Строка «удалено» не означает очистку всех резервных, внешних и выгруженных копий. Действующие retention/observability policies не менялись.

Issue canon: штатный post-hook PASS (300 возвращённых issues), отдельная проверка F262 23/23 PASS, все issues OPEN. Прежняя ошибка #6852 при отдельной текущей проверке отсутствует; чужая issue здесь не менялась.

## Незакрытые обязательные этапы

- T019/T022: полная матрица, GRAF Dev, managed player, VoiceOver, нагрузка и измерения.
- T023: upgrade/rollback и сочетания реальных версий.
- T020/T021: итоговая независимая проверка кода/конвергенция и `governance-fast` на точном PR SHA. Выпуск дополнительно требует frozen candidate/release-full и обычные macOS gates.
- Общий Spec Kit checker: installed specify v1.0.4/ref cb610277… против locked v1.0.1/ref 9118ed15…; state github-issue-canon отличается от lock. Эти файлы не исправлялись в рамках удаления.
- Единственный GRAF Dev сейчас имеет active manifest `dev-9cf93b92eb60`, source `9cf93b92eb608ccf952b477f7bd0beb6a45c560c`. Выполнен только read-only status. Это другая версия и не acceptance F262.
- Правило `docs/agent-guidance/local-development.md`: при dirty checkout закончить тесты и авторизованный коммит до build/promote; правило AGENTS.md: implementation commits требуют явного разрешения пользователя после проверки.

Full CI, PR, commit, push, deploy, выпуск и изменение пользовательских записей не выполнялись.
