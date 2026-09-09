# Итог независимой проверки объединённого кода

2026-09-08. Reviewer session: 01a081ce-fe72-7882-bda6-dcf0007cea18.
Метод: read-only codex exec; после прерывания продолжена та же session.
Ниже неизменённое заключение reviewer до исправления T023.

Итог независимого bounded review: найден один подтверждённый P2. Подтверждённых P0/P1 нет.

Runtime, установленный `/Applications/GRAF Dev.app`, сервер, PostgreSQL, браузер и Git-проверки мной не запускались. Поэтому это заключение относится только к статическому actual diff, затронутому коду и callers; runtime PASS я не заявляю. Переданные родителем результаты проверок рассматриваю только как внешнюю справку, а не как собственное evidence. Native Reload patch по указанию не перепроверял.

### P2 — `partial` рассогласован между серверной проекцией и пользовательским статусом

Затронутые места:

- [cabinet.js:1756](/Users/yshishenya/.codex/worktrees/0fc9/crisp/apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js:1756)
- [cabinet.js:2351](/Users/yshishenya/.codex/worktrees/0fc9/crisp/apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js:2351)
- [view_models.py:1886](/Users/yshishenya/.codex/worktrees/0fc9/crisp/apps/server/src/twobrain_rec_server/cabinet/view_models.py:1886)
- [processing/status.py:318](/Users/yshishenya/.codex/worktrees/0fc9/crisp/apps/server/src/twobrain_rec_server/processing/status.py:318)
- [processing/status.py:360](/Users/yshishenya/.codex/worktrees/0fc9/crisp/apps/server/src/twobrain_rec_server/processing/status.py:360)

Сценарий воспроизведения:

1. У встречи опубликован частичный итог: `summary_status == "partial"`. Сервер считает его доступным и явно выставляет `artifacts["summary"].visible = true`:

   ```python
   state=summary_state,
   visible=summary_state in {"available", "partial"}
   ```

2. Та же проекция передаётся в клиентский JavaScript. Текст предупреждения для `partial` уже корректный: «Итоги доступны частично…».

3. Но шкала этапов обрабатывает только `"available"` как готовое состояние:

   ```javascript
   summaryState === "available" ? "ready"
     : ["failed", "unavailable"].includes(summaryState) ? "unavailable"
     : ... ? "active" : "active"
   ```

   Для `"partial"` получается `active` и подпись «Готовятся». В результате уже доступный частичный результат выглядит как ещё не завершённый.

4. В списке встреч рассогласование обратное: `source_basis == "stored_output"` трактуется как полностью готовый результат, и возвращается:

   ```text
   Расшифровка и итоги готовы
   ```

   без указания ограничений. Это происходит потому, что `outcomes_ready` не различает `available` и `partial`.

Воздействие: содержимое не раскрывается чужому пользователю и не выбирается неверная ревизия, но пользователь получает неправильное состояние готовности — в одном месте видит незавершённый этап, в другом — сообщение о полностью готовых итогах. Это нарушает контракт, согласно которому `partial` должен быть доступным результатом с явно отражёнными ограничениями, а не ожиданием и не полной готовностью.

Ожидаемая коррекция — согласованно трактовать `partial` как доступное состояние с ограничениями: например, готовый этап с подписью «Доступно частично» и строка списка «Готово с ограничениями». Это не косметика текста: сейчас меняется смысл состояния результата.

### C1 — foreground claim

Подтверждённо исправлено статически:

- `refreshLocal` не подавляет локальную ошибку из-за `NSApp.isActive` или видимости окна;
- актуальные инциденты сначала фильтруются по сохранённому owner-bound session context;
- перед `await` и перед отправкой проверяется `authEpoch` и неизменность snapshot;
- `willPresent` дополнительно проверяет владельца запроса и существование текущего инцидента.

См. [DesktopNotificationPresenter.swift:455](/Users/yshishenya/.codex/worktrees/0fc9/crisp/apps/macos/RecApp/Sources/Notifications/DesktopNotificationPresenter.swift:455)–[469](/Users/yshishenya/.codex/worktrees/0fc9/crisp/apps/macos/RecApp/Sources/Notifications/DesktopNotificationPresenter.swift:469) и [483](/Users/yshishenya/.codex/worktrees/0fc9/crisp/apps/macos/RecApp/Sources/Notifications/DesktopNotificationPresenter.swift:483)–[492](/Users/yshishenya/.codex/worktrees/0fc9/crisp/apps/macos/RecApp/Sources/Notifications/DesktopNotificationPresenter.swift:492).

Нового подтверждённого дефекта по C1 нет.

### C2 — стабильный occurrence ID и дедупликация

Подтверждённо исправлено статически:

- основной reminder ID строится из `context + eventId`, без `startsAt`;
- старый ID с временем сохраняется как alias для миграции;
- reservation хранит `scheduledFor`;
- будущую reservation можно заменить до её due time;
- после наступления due time уже доставленное/зарезервированное событие не воспроизводится повторно;
- отмена и повторное планирование используют тот же стабильный идентификатор.

См. [DesktopNotificationPresenter.swift:443](/Users/yshishenya/.codex/worktrees/0fc9/crisp/apps/macos/RecApp/Sources/Notifications/DesktopNotificationPresenter.swift:443)–[453](/Users/yshishenya/.codex/worktrees/0fc9/crisp/apps/macos/RecApp/Sources/Notifications/DesktopNotificationPresenter.swift:453) и реализацию `claim` в начале того же файла.

Проверка клика также повторно требует совпадения актуальной occurrence по `eventId` и `startsAt`, затем проверяет разрешённость и срок действия встречи: [DesktopNotificationPresenter.swift:498](/Users/yshishenya/.codex/worktrees/0fc9/crisp/apps/macos/RecApp/Sources/Notifications/DesktopNotificationPresenter.swift:498)–[503](/Users/yshishenya/.codex/worktrees/0fc9/crisp/apps/macos/RecApp/Sources/Notifications/DesktopNotificationPresenter.swift:503). Подтверждённого P1/P2 по этому поведению нет.

### C3 — асинхронный fallback настроек

Подтверждённо исправлено статически:

- отказ/ошибка загрузки кабинета теперь ведёт в локальные настройки уведомлений, а не в раздел автозаписи;
- используется отдельный `openLocalNotificationSettings()`;
- уже открытое окно переиспользуется;
- выбирается вкладка с индексом `1`, то есть «Уведомления на этом Mac»;
- нативный маршрут разрешается только для доверенной встроенной поверхности и текущего готового кабинета.

См. [TwoBrainRecApp.swift:501](/Users/yshishenya/.codex/worktrees/0fc9/crisp/apps/macos/RecApp/App/TwoBrainRecApp.swift:501)–[516](/Users/yshishenya/.codex/worktrees/0fc9/crisp/apps/macos/RecApp/App/TwoBrainRecApp.swift:516), [TwoBrainRecApp.swift:3336](/Users/yshishenya/.codex/worktrees/0fc9/crisp/apps/macos/RecApp/App/TwoBrainRecApp.swift:3336)–[3337](/Users/yshishenya/.codex/worktrees/0fc9/crisp/apps/macos/RecApp/App/TwoBrainRecApp.swift:3337) и [TwoBrainRecApp.swift:3390](/Users/yshishenya/.codex/worktrees/0fc9/crisp/apps/macos/RecApp/App/TwoBrainRecApp.swift:3390)–[3427](/Users/yshishenya/.codex/worktrees/0fc9/crisp/apps/macos/RecApp/App/TwoBrainRecApp.swift:3427).

Подтверждённого дефекта trusted settings route не найдено.

### Остальные проверенные границы

Подтверждённых findings не обнаружено в следующих областях:

- четыре команды tray направлены через один `DesktopControlModel` dispatcher и существующие `start/stop/pause/resume` guards: [TwoBrainRecApp.swift:551](/Users/yshishenya/.codex/worktrees/0fc9/crisp/apps/macos/RecApp/App/TwoBrainRecApp.swift:551)–[578](/Users/yshishenya/.codex/worktrees/0fc9/crisp/apps/macos/RecApp/App/TwoBrainRecApp.swift:578);
- неуспешный Start не ставится в скрытую очередь до готовности обработчика;
- постоянный widget и старые четыре `NotificationCenter`-моста удалены, компактное меню F255 сохранено;
- локальные ошибки группируются по сессии, ограничение числа отображаемых групп не ограничивает вычисление actionable incidents;
- повторный клик по локальному уведомлению перепроверяет owner, текущий incident и наличие записи;
- успешная отправка не остаётся локальной ошибкой через `DesktopUploadCustodyProjection`;
- `summary_progress` проверяет current slot, результат, media revision, source hash и deletion fence;
- пустой summary slot не скрывает пригодный звук;
- replacement attempt не подменяет старую ревизию до публикации собственного результата;
- polling содержит generation, schedule-generation, timestamp и detached-document fences;
- обновление выбранного формата сохраняет player, вкладку, focus и draft в просмотренных ветках;
- серверный media worker выбирает workflow в пределах workspace/meeting/revision/purpose, читает только `workflow_id`, а fallback timer сохраняется;
- bootstrap ограничивает новый доступ к `public.processing_workflows` восемью column-level `SELECT` и не отзывает штатные права нормализации;
- native recap, UUID/time/dedup/UI не были повторно внесены, что соответствует решению владельца.

### Ponytail

Отдельного Ponytail finding нет.

В проверенном diff не обнаружен лишний новый движок уведомлений, новая зависимость или параллельная архитектура, влияющая на корректность. Использованы существующие dispatcher, `NSTabViewController`, route policy, generation fences, upload queue и native PostgreSQL role checks. Удалённый постоянный widget и старые мосты действительно относятся к superseded-поведению. Оставшийся P2 — функциональное рассогласование состояний `partial`, а не следствие чрезмерной архитектуры.

Review завершён в режиме `read-only investigation`. Файлы, стенд, приложения, данные и Git не изменялись; сообщения, PR и комментарии не отправлялись.
