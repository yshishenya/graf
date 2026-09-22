# Проверочный список: Паритет уведомлений GRAF с Krisp

**Назначение**: этот список принадлежит ревьюеру. Пункты отмечает ревьюер, а не
исполнитель. Реализация читает список как шлюз и не отмечает пункты сама.

## Сверка с эталоном

- [ ] CHK001 Наблюдаемые параметры окна карточки подтверждены повторным
      измерением эталона: ширина окна, ширина карточки, отступ сверху, поля.
- [ ] CHK002 Внешний вид карточки GRAF сверен с эталонным снимком, отклонения
      перечислены явно (SC-005).
- [X] CHK003 Тексты кнопок и сообщений совпадают с наблюдаемыми по смыслу и
      выполняемому действию, без чужих продуктовых утверждений.
- [X] CHK004 Подтверждено, что не перенесены исходный код, ресурсы, значки или
      торговые марки эталона (конституция, раздел VII).

## Логика показа

- [X] CHK005 Карточка появляется за наблюдаемый срок до встречи и исчезает по
      истечении окна показа.
- [X] CHK006 Закрытая пользователем карточка не появляется снова для того же
      события, включая перезапуск пересчёта календаря.
- [X] CHK007 Показывается одна карточка на актуальную встречу, даже если подряд
      идут несколько событий.
- [X] CHK008 Карточка не предлагает начать вторую запись, когда запись уже идёт.
- [X] CHK009 Перенесённое или отменённое событие не выполняет действие по
      устаревшей ссылке.
- [X] CHK010 Выключение напоминаний убирает и запланированные системные
      напоминания, и уже показанную карточку.
- [X] CHK011 Выход из аккаунта скрывает карточку и индикатор и отменяет
      запланированные напоминания.

## Системная независимость

- [ ] CHK012 При отозванном разрешении на уведомления macOS карточка
      показывается и работает.
- [ ] CHK013 При включённом режиме «Не беспокоить» карточка показывается, звук не
      проигрывается.
- [X] CHK014 Системный баннер не дублирует карточку для того же события.
- [ ] CHK015 Разрешение macOS по-прежнему отображается правдиво в настройках и
      обновляется без перезапуска.

## Запись и индикатор

- [ ] CHK016 Индикатор появляется при подтверждённом старте записи и исчезает
      после завершения обработки.
- [ ] CHK017 Индикатор показывает верное состояние и идущую длительность.
- [ ] CHK018 Кнопка останова в индикаторе завершает запись и не создаёт второй
      контроллер записи.
- [ ] CHK019 Индикатор и карточка не перехватывают клавиатурный фокус.

## Оформление и доступность

- [ ] CHK020 Карточка и индикатор корректны в светлом и тёмном оформлении.
- [ ] CHK021 VoiceOver читает осмысленную сводку карточки и индикатора.
- [ ] CHK022 При увеличенном системном шрифте текст не обрезается и не
      перекрывает действия.
- [ ] CHK023 Карточка и индикатор не перекрывают строку меню и остаются в
      рабочей области экрана, в том числе в полноэкранном режиме.

## Проверки и доказательства

- [X] CHK024 Новые тесты карточки проходят; перечислены проверяемые правила.
- [X] CHK025 Существующие тесты уведомлений остались зелёными.
- [X] CHK026 Полный набор macOS-тестов проходит.
- [ ] CHK027 Ручная проверка выполнена в единственном приложении
      `/Applications/GRAF Dev.app` через штатный `dev-harness`, без создания
      второй копии приложения.
- [ ] CHK028 Записаны доказательства: команды, результаты, снимки, отклонения.
- [X] CHK029 Обновлены спецификация, план, задачи и фрагмент журнала изменений.
- [X] CHK030 Отсутствуют секреты, токены, содержимое встреч и персональные данные
      в артефактах и доказательствах.

## Заметки ревьюера

Заполняется ревьюером по ходу проверки.

### Актуальный итог независимого финального ревью, 2026-09-22

Объект: рабочее дерево
/Users/yshishenya/.dsh/clutch-dsh-worktree/worktree/wt_6b80dad08d61,
ветка 274-notification-parity, HEAD
7c39dc2e2ad5a4c0aaf911bfba6ce1ae9674f503. Сверены текущие spec.md,
plan.md, tasks.md, quickstart.md, research.md,
changes/unreleased/F274.yaml, исходники согласователя/карточки и тесты.
Изменён только этот файл; commit, push, merge и release не выполнялись.

[X] означает достаточное доказательство кодом и/или переданным точным
результатом XCTest. [ ] означает отсутствие обязательного живого,
системного, снимочного или exact-SHA доказательства; зелёный unit-тест не
выдаётся за живую проверку.

| Пункт | Статус | Доказательство и точный остаток |
|---|---|---|
| CHK001 | BLOCKED | Геометрия окна 448/карточки 420, поля и адаптивная высота есть в коде и тестах; повторного измерения эталона в этом проходе нет. |
| CHK002 | BLOCKED | Текущий код и `DesktopNotificationCardTests` подтверждают левый верхний крестик и отсутствие пересечения с содержимым, но новый снимок живой карточки для сверки с эталоном не получен; snapshot-тест без `GRAF_CARD_SNAPSHOT_DIR` пропущен. |
| CHK003 | PASS | В реализации перечислены пять типов карточек; действия и русские строки проверены. Для короткой записи используются «Запись слишком короткая» и «Записи короче 30 секунд не сохраняются.» без дублирования. `DesktopNotificationCardTests`: 34 теста, 1 ожидаемый пропуск, 0 ошибок. |
| CHK004 | PASS | Реализация написана кодом GRAF и системными SF Symbols; чужих исходников, ресурсов и торговых марок в проверенных изменениях нет. |
| CHK005 | PASS | Код задаёт показ за 15 минут, предел 120 секунд и завершение до начала встречи; тесты текущего SHA покрывают сроки встречи, вопроса, короткой записи и предпросмотра. Это кодовое доказательство, не живая проверка. |
| CHK006 | PASS | `dismissedCards` фильтруется при пересчёте, ключ сохраняется при закрытии; тест обновления календаря после закрытия прошёл в текущем наборе. |
| CHK007 | PASS | `reconcileCard` сортирует кандидатов и берёт только `candidates.first`; единая поверхность не создаёт второго окна. Арбитраж также учитывает `meeting`, `problem`, `preview`, `shortRecording` и `recordingPrompt`; отдельная живая проверка нескольких одновременных событий отсутствует. |
| CHK008 | PASS | `shouldRemind` подавляет `snapshot.active` и `snapshot.stopping` для любого календарного события; соответствующие проверки текущей и другой встречи прошли. |
| CHK009 | PASS | Обработчик действия повторно проверяет актуальность события и безопасную HTTPS-ссылку; перенос, отмена, истечение и небезопасная ссылка покрыты тестами. |
| CHK010 | PASS | `save` сразу вызывает `reconcileCard`, планировщик удаляет устаревшие системные запросы; тест выключения напоминаний подтверждает скрытие карточки. |
| CHK011 | PASS | `invalidate` отменяет запросы/контекст и вызывает `dismissAllCards`; тесты выхода из аккаунта и очистки инцидента прошли. |
| CHK012 | BLOCKED | Кодовая ветка не требует разрешения для собственной карточки, а тест с `.denied` подтверждает локальный инцидент; календарная карточка при реально отозванном разрешении macOS живьём не проверена. |
| CHK013 | BLOCKED | Собственная карточка не создаёт системный звук, но режим «Не беспокоить» и фактическая тишина живьём не проверены. |
| CHK014 | PASS | При видимой карточке `presentationOptions` возвращает пустой набор; тесты встречи, инцидента и предпросмотра подтверждают отсутствие дублирующего системного баннера. |
| CHK015 | BLOCKED | `refreshPermission` обновляет текст без перезапуска по коду, но фактическое переключение разрешения macOS туда/обратно не выполнено. |
| CHK016 | BLOCKED | По текущему контракту отдельного плавающего индикатора нет: состояние должно быть в приложении, строке меню и панели управления. Полный живой цикл записи и исчезновение состояния после обработки не проверены. |
| CHK017 | BLOCKED | Состояния `recording`/`transcribing`/`finished` сохранены для контроля, а `elapsed` намеренно не рисуется карточкой; правильная длительность в штатной поверхности не проверена живьём. |
| CHK018 | BLOCKED | Команда остановки и доступность покрыты кодом и тестами, но этот пункт требует поведения штатной поверхности и живого клика; установленное приложение текущего SHA не запускалось. |
| CHK019 | BLOCKED | Карточка не становится key/main и использует `nonactivatingPanel`; отсутствие перехвата фокуса во всех штатных поверхностях живьём не проверено. |
| CHK020 | BLOCKED | Цвета зависят от `effectiveAppearance`, но светлая и тёмная темы карточки и индикатора живьём или снимками не подтверждены. |
| CHK021 | BLOCKED | Есть `accessibilitySummary`, подписи элементов и announcement; фактическое чтение карточки и состояния VoiceOver не выполнено. |
| CHK022 | BLOCKED | Длинный русский текст, перенос, адаптивная высота и границы всех пяти типов проверены на обычном тестовом окружении; отдельной проверки крупного системного шрифта нет. |
| CHK023 | BLOCKED | Код учитывает `visibleFrame`, `canJoinAllSpaces` и `fullScreenAuxiliary`; многоэкранный и полноэкранный сценарии живьём не проверены. |
| CHK024 | PASS | `swift test --package-path apps/macos --filter DesktopNotificationCardTests`: 34 теста, 1 ожидаемый пропуск, 0 ошибок. Тесты проверяют геометрию крестика, пять типов, границы, длинный текст, флажок, приоритет и сроки. |
| CHK025 | PASS | На текущем SHA прошли `DesktopNotificationControlTests` (21/0), `DesktopLocalNotificationDeliveryTests` (12/0), `ShortRecordingNoticeTests` (1/0), `AppControlAccessibilityTests` (24/0); фильтр `DesktopNotification` дал 55 тестов, 1 пропуск, 0 ошибок. |
| CHK026 | PASS | `bash apps/macos/Scripts/run-swift-tests.sh`: 1050 тестов, 2 пропуска, 0 ошибок; код возврата 0. |
| CHK027 | BLOCKED | `infra/scripts/dev-harness.sh status --json` подтверждает active manifest `dev-7c39dc2e2ad5`, exact `source_sha=7c39dc2e2ad5a4c0aaf911bfba6ce1ae9674f503` и health `pass`, но `/Applications/GRAF Dev.app` отсутствует (`installed=false`); ручная CUA/live-проверка заблокирована. |
| CHK028 | BLOCKED | `infra/scripts/ci-local.sh --fast` на грязном reviewer checkout завершился с exit 2; `ci_evidence_status=ambiguous`, `reason=dirty_worktree`. Это не PASS; свежих снимков и полной живой матрицы нет, поэтому доказательства живой приёмки неполны. |
| CHK029 | PASS | `spec.md`, `plan.md`, `tasks.md`, `quickstart.md`, `research.md` и `changes/unreleased/F274.yaml` согласованы с текущей реализацией: левый крестик, адаптивная высота, пять типов, флажок, сроки и тексты. T044/T045 остаются BLOCKED и открытыми как отдельные живые/exact-SHA гейты. |
| CHK030 | PASS | В проверенных артефактах нет секретов, токенов, содержимого встреч или персональных данных; используются синтетические значения. |

Отдельная сверка запроса владельца: левый верхний крестик проверен для всех
пяти типов общей поверхностью; пересечение с текстом и кнопками покрыто
геометрическими тестами. Длинный русский текст переносится, высота растёт.
Вопрос о записи содержит две кнопки и настоящий флажок «Запомнить выбор».
Приоритеты согласователя: problem выше recordingPrompt/shortRecording,
затем meeting, затем preview; тесты подтверждают защиту проблемы, общую
поверхность короткой записи и непоглощение инцидента. Активная или переходящая
запись подавляет вторую запись. Закрытие, истечение, выход и завершение
очищают поверхность по коду и тестам; актуальная живая сборка не доказана.

Точный остаток: F274 нельзя объявить полностью готовой к выпуску. Проверяемый
HEAD/PR — `7c39dc2e2ad5a4c0aaf911bfba6ce1ae9674f503`. Active manifest
`dev-7c39dc2e2ad5` указывает на тот же exact `source_sha` и имеет health
`pass`, но `/Applications/GRAF Dev.app` отсутствует (`installed=false`), а CUA
сообщает `Mac locked`. Не доказаны разрешения macOS, «Не беспокоить»,
светлая/тёмная тема, VoiceOver, крупный шрифт, полноэкранный/многоэкранный
режим и полный цикл записи/завершения процесса. `ci-local --fast` завершился с
exit 2; `ci_evidence_status=ambiguous`, `reason=dirty_worktree`, поэтому это
не PASS. Commit, PR, GitHub gates, merge, deploy и release не выполнялись.
T044 и T045 обоснованно остаются BLOCKED и [ ].

### Findings текущего SHA

1. **P1 — доказательства живой приёмки заблокированы.**
   Проверяемый HEAD/PR — `7c39dc2e2ad5a4c0aaf911bfba6ce1ae9674f503`. Active manifest
   `dev-7c39dc2e2ad5` указывает на exact `source_sha`
   `7c39dc2e2ad5a4c0aaf911bfba6ce1ae9674f503` и имеет `health.result=pass`, но
   `/Applications/GRAF Dev.app` отсутствует (`installed=false`), а CUA сообщает
   `Mac locked`. Поэтому нельзя считать доказанными системное разрешение, «Не
   беспокоить», полный цикл записи, закрытие главного окна, тему, VoiceOver,
   крупный шрифт, полноэкранный режим и несколько мониторов.

2. **P1 — локальный шлюз не даёт PASS и не закрывает T044.**
   Полный macOS-набор текущего SHA — 1050 тестов, 2 пропуска, 0 ошибок;
   `ci-local --fast` завершился с exit 2 на грязном reviewer checkout,
   `ci_evidence_status=ambiguous`, `reason=dirty_worktree`. Snapshot-тест
   пропущен без `GRAF_CARD_SNAPSHOT_DIR`, а ручная матрица T044 и последующее
   обновление доказательств T045 остаются BLOCKED и открытыми. Это блокер
   готовности, а не подтверждённый дефект исходников.

3. **P2 — ограничение покрытия доступности и адаптивности.**
   Код использует `preferredFont`, перенос по словам, неограниченное число строк,
   accessibility labels и summary; тесты проверяют обычный шрифт и геометрию.
   Нет фактического прогона VoiceOver и крупного системного шрифта, поэтому
   утверждение о полном отсутствии обрезания и корректном чтении пока нельзя
   считать доказанным.

Подтверждённых обязательных `FAIL` в реализации на этом SHA не найдено. Архивные
находки про правый верхний крестик, отсутствие арбитража пяти карточек,
дублирование текста короткой записи и фиксированную высоту относятся к SHA
`9a63d5da…` и не переносятся на текущий результат.

### Архив предыдущего промежуточного ревью

Ниже сохранён текст предыдущего прохода как история. Его статусы и находки
устарели после исправлений крестика, текста, адаптивной высоты и согласователя;
актуальным является раздел выше.

### Итог независимого ревью, 2026-09-20

**Объект**: текущий рабочий каталог ветки `274-notification-parity`, `HEAD`
`9a63d5daecdc2d8eb4003c50956dbce0c9327c75`, включая рабочий `git diff`.
Ревью выполнено в отдельном дереве
`/Users/yshishenya/.dsh/clutch-dsh-worktree/worktree/wt_6b80dad08d61`.
Изменён только этот `checklist.md`; исходники, тесты, спецификация, задачи,
журнал изменений, `AGENTS.md` и файлы руководств не изменялись. `git diff
--check` чистый. XCTest, `dev-harness`, DSH и `/Applications/GRAF Dev.app` в
этом проходе не запускались.

**Как читать результат**: `PASS` ниже означает достаточное статическое
доказательство в текущем коде и/или наличие точной проверки в исходном тесте;
это не утверждение, что тест уже был запущен. `BLOCKED` означает, что нужен
запуск теста, живое приложение, фактическое разрешение macOS/«Не беспокоить»,
VoiceOver, снимок или другое внешнее доказательство. Отмечены `[X]` только
пункты с достаточным текущим кодовым доказательством.

| Пункт | Результат | Доказательство и ограничение |
|---|---|---|
| CHK001 | BLOCKED | Размеры заданы и проверяются на окне в `/Users/yshishenya/.dsh/clutch-dsh-worktree/worktree/wt_6b80dad08d61/apps/macos/Shared/Tests/DesktopNotificationCardTests.swift:232-247,333-343`, но повторного измерения эталона и сохранённого снимка нет. |
| CHK002 | FAIL | Кнопка закрытия всё ещё закреплена сверху справа в `/Users/yshishenya/.dsh/clutch-dsh-worktree/worktree/wt_6b80dad08d61/apps/macos/RecApp/Sources/Notifications/DesktopNotificationCardPresenter.swift:557-560`; тест закрепляет это же положение в `/Users/yshishenya/.dsh/clutch-dsh-worktree/worktree/wt_6b80dad08d61/apps/macos/Shared/Tests/DesktopNotificationCardTests.swift:268-274`. Это прямо расходится с запросом владельца о левом верхнем углу. |
| CHK003 | FAIL | Для короткой записи заголовок и пояснение повторяют одну мысль: `«Запись не сохранена»` и `«Запись короче 30 секунд не сохранена»` в `/Users/yshishenya/.dsh/clutch-dsh-worktree/worktree/wt_6b80dad08d61/apps/macos/RecApp/Sources/Notifications/DesktopRecordingNoticePresenter.swift:8-9`; в карточку они передаются раздельно в `/Users/yshishenya/.dsh/clutch-dsh-worktree/worktree/wt_6b80dad08d61/apps/macos/RecApp/Sources/Notifications/DesktopNotificationCardPresenter.swift:601-617`. Требование владельца «без дублирования, коротко и однозначно» не выполнено. |
| CHK004 | PASS | В текущем diff нет новых ресурсов или бинарников эталона; поверхность собирается кодом и системными SF Symbols в `/Users/yshishenya/.dsh/clutch-dsh-worktree/worktree/wt_6b80dad08d61/apps/macos/RecApp/Sources/Notifications/DesktopNotificationCardPresenter.swift:489-492`, а спецификация фиксирует независимую реализацию в `/Users/yshishenya/.dsh/clutch-dsh-worktree/worktree/wt_6b80dad08d61/specs/274-notification-parity/spec.md:32-35`. |
| CHK005 | BLOCKED | Правила `15 минут`, `120 секунд`, начала/конца встречи есть в `/Users/yshishenya/.dsh/clutch-dsh-worktree/worktree/wt_6b80dad08d61/apps/macos/RecApp/Sources/Notifications/DesktopNotificationPresenter.swift:452-477`, таймер — в `/Users/yshishenya/.dsh/clutch-dsh-worktree/worktree/wt_6b80dad08d61/apps/macos/RecApp/Sources/Notifications/DesktopNotificationCardPresenter.swift:320-331`; фактический отсчёт и исчезновение в установленном приложении не проверены. |
| CHK006 | PASS | `reconcileCard` отбрасывает ключи из `dismissedCards` в `/Users/yshishenya/.dsh/clutch-dsh-worktree/worktree/wt_6b80dad08d61/apps/macos/RecApp/Sources/Notifications/DesktopNotificationPresenter.swift:504-507`, а `dismissCard` сохраняет ключ владельца/события в `/Users/yshishenya/.dsh/clutch-dsh-worktree/worktree/wt_6b80dad08d61/apps/macos/RecApp/Sources/Notifications/DesktopNotificationPresenter.swift:612-618`; сценарий повторного обновления есть в `/Users/yshishenya/.dsh/clutch-dsh-worktree/worktree/wt_6b80dad08d61/apps/macos/Shared/Tests/DesktopNotificationCardTests.swift:394-407`. Запуск теста не заявляется отдельно, см. CHK024. |
| CHK007 | PASS | Согласователь сортирует кандидатов и берёт только `candidates.first` в `/Users/yshishenya/.dsh/clutch-dsh-worktree/worktree/wt_6b80dad08d61/apps/macos/RecApp/Sources/Notifications/DesktopNotificationPresenter.swift:504-513`; `DesktopNotificationCardPresenter` создаёт одно текущее окно в `/Users/yshishenya/.dsh/clutch-dsh-worktree/worktree/wt_6b80dad08d61/apps/macos/RecApp/Sources/Notifications/DesktopNotificationCardPresenter.swift:196-220`. Отдельного теста с несколькими кандидатами в текущем наборе не найдено. |
| CHK008 | FAIL | `shouldRemind` подавляет только событие, равное `calendarContextEventID`, в `/Users/yshishenya/.dsh/clutch-dsh-worktree/worktree/wt_6b80dad08d61/apps/macos/RecApp/Sources/Notifications/DesktopNotificationPresenter.swift:452-455`. При уже активной записи другой встречи карточка всё ещё допускается и получает кнопку запуска в `meeting`-ветке `/Users/yshishenya/.dsh/clutch-dsh-worktree/worktree/wt_6b80dad08d61/apps/macos/RecApp/Sources/Notifications/DesktopNotificationCardPresenter.swift:621-632`; существующий тест прямо сохраняет напоминание для другой встречи в `/Users/yshishenya/.dsh/clutch-dsh-worktree/worktree/wt_6b80dad08d61/apps/macos/Shared/Tests/DesktopNotificationControlTests.swift:251-263`. Для формулировки пункта «вторая запись» это недопустимо или требует явного уточнения контракта. |
| CHK009 | PASS | Действие повторно сверяет актуальность в `/Users/yshishenya/.dsh/clutch-dsh-worktree/worktree/wt_6b80dad08d61/apps/macos/RecApp/Sources/Notifications/DesktopNotificationPresenter.swift:582-609`; ссылка дополнительно требует совпадения `eventId` и `startsAt` в `790-801`. Это покрыто проверками переноса/отмены/небезопасной ссылки в `/Users/yshishenya/.dsh/clutch-dsh-worktree/worktree/wt_6b80dad08d61/apps/macos/Shared/Tests/DesktopNotificationControlTests.swift:169-212`. |
| CHK010 | PASS | `save` сразу вызывает `reconcileCard`, а планировщик удаляет устаревшие запросы в `/Users/yshishenya/.dsh/clutch-dsh-worktree/worktree/wt_6b80dad08d61/apps/macos/RecApp/Sources/Notifications/DesktopNotificationPresenter.swift:362-369,424-431`; проверка скрытия карточки есть в `/Users/yshishenya/.dsh/clutch-dsh-worktree/worktree/wt_6b80dad08d61/apps/macos/Shared/Tests/DesktopNotificationCardTests.swift:409-417`. |
| CHK011 | PASS | `invalidate` удаляет запросы, очищает календарь и вызывает `dismissAllCards` в `/Users/yshishenya/.dsh/clutch-dsh-worktree/worktree/wt_6b80dad08d61/apps/macos/RecApp/Sources/Notifications/DesktopNotificationPresenter.swift:265-273`; `dismissAllCards` очищает состояние индикатора в `/Users/yshishenya/.dsh/clutch-dsh-worktree/worktree/wt_6b80dad08d61/apps/macos/RecApp/Sources/Notifications/DesktopNotificationPresenter.swift:659-664`. Проверки выхода есть в `/Users/yshishenya/.dsh/clutch-dsh-worktree/worktree/wt_6b80dad08d61/apps/macos/Shared/Tests/DesktopNotificationCardTests.swift:419-426` и `/Users/yshishenya/.dsh/clutch-dsh-worktree/worktree/wt_6b80dad08d61/apps/macos/Shared/Tests/DesktopLocalNotificationDeliveryTests.swift:132-146`. |
| CHK012 | BLOCKED | Код карточки не вызывает `allowed()` в `reconcileCard`/`refreshLocal`, а тест инцидента с `.denied` показывает карточку в `/Users/yshishenya/.dsh/clutch-dsh-worktree/worktree/wt_6b80dad08d61/apps/macos/Shared/Tests/DesktopLocalNotificationDeliveryTests.swift:100-115`; однако сценарий календарной карточки с реально отозванным разрешением macOS не выполнен в `/Applications/GRAF Dev.app`. |
| CHK013 | BLOCKED | В коде нет канала системного звука для собственной карточки, но включение «Не беспокоить» и отсутствие звука требуют живой проверки системного режима; теста такого сценария нет. |
| CHK014 | PASS | При видимой карточке `presentationOptions` возвращает пустой набор в `/Users/yshishenya/.dsh/clutch-dsh-worktree/worktree/wt_6b80dad08d61/apps/macos/RecApp/Sources/Notifications/DesktopNotificationPresenter.swift:770-785`; сценарии подавления баннера есть в `/Users/yshishenya/.dsh/clutch-dsh-worktree/worktree/wt_6b80dad08d61/apps/macos/Shared/Tests/DesktopNotificationCardTests.swift:380-392` и `/Users/yshishenya/.dsh/clutch-dsh-worktree/worktree/wt_6b80dad08d61/apps/macos/Shared/Tests/DesktopLocalNotificationDeliveryTests.swift:42-50`. |
| CHK015 | BLOCKED | `refreshPermission` и обновление формы настроек предусмотрены в `/Users/yshishenya/.dsh/clutch-dsh-worktree/wt_6b80dad08d61/apps/macos/RecApp/Sources/Notifications/DesktopNotificationPresenter.swift:318-335,889-894`, но смена разрешения без перезапуска не проверялась фактически; отдельного теста нет. |
| CHK016 | BLOCKED | Текущий контракт намеренно не создаёт отдельное плавающее окно состояния записи: `/Users/yshishenya/.dsh/clutch-dsh-worktree/worktree/wt_6b80dad08d61/apps/macos/RecApp/Sources/Notifications/DesktopNotificationPresenter.swift:621-629`. Состояние/индикатор в приложении и строке меню нужно проверить живьём; пункт чеклиста формулировался для прежней поверхности. |
| CHK017 | BLOCKED | `elapsed` в `updateRecordingIndicator` оставлен только для сигнатуры и не рисуется этой поверхностью (`/Users/yshishenya/.dsh/clutch-dsh-worktree/worktree/wt_6b80dad08d61/apps/macos/RecApp/Sources/Notifications/DesktopNotificationPresenter.swift:624-629`); правильность длительности в приложении/строке меню не подтверждена живой проверкой. |
| CHK018 | PASS | Существующий контроллер сохраняет доступный Stop во время `active/stopping` и убирает его после `stopped` в `/Users/yshishenya/.dsh/clutch-dsh-worktree/worktree/wt_6b80dad08d61/apps/macos/Shared/Tests/CaptureControlV5Tests.swift:64-85`; доступная кнопка и отдельный путь Stop проверяются также в `/Users/yshishenya/.dsh/clutch-dsh-worktree/worktree/wt_6b80dad08d61/apps/macos/Shared/Tests/AppControlAccessibilityTests.swift:128-163`. Запуск тестов и живой клик не выполнялись. |
| CHK019 | BLOCKED | Для карточки есть `canBecomeKey/Main == false` и проверки `/Users/yshishenya/.dsh/clutch-dsh-worktree/worktree/wt_6b80dad08d61/apps/macos/Shared/Tests/DesktopNotificationCardTests.swift:171-184,585-605`; отсутствие перехвата фокуса индикатором требует проверки живого приложения. |
| CHK020 | BLOCKED | Цвета карточки зависят от `effectiveAppearance` в `/Users/yshishenya/.dsh/clutch-dsh-worktree/worktree/wt_6b80dad08d61/apps/macos/RecApp/Sources/Notifications/DesktopNotificationCardPresenter.swift:430-456,674-685`, но светлая/тёмная тема карточки и индикатора не снята и не сверена. |
| CHK021 | BLOCKED | Для карточки есть `accessibilitySummary`, подписи и объявление в `/Users/yshishenya/.dsh/clutch-dsh-worktree/worktree/wt_6b80dad08d61/apps/macos/RecApp/Sources/Notifications/DesktopNotificationCardPresenter.swift:34-49,366-371,470-475`; фактическое чтение VoiceOver карточки и индикатора не выполнено. |
| CHK022 | FAIL | Используются фиксированные шрифты 14/13 и фиксированная высота однострочной карточки 82 в `/Users/yshishenya/.dsh/clutch-dsh-worktree/worktree/wt_6b80dad08d61/apps/macos/RecApp/Sources/Notifications/DesktopNotificationCardPresenter.swift:501-505,549-566,647-653`; максимальное число строк не ограничено, но расчёта высоты под увеличенный системный шрифт нет. Поэтому отсутствие обрезания/перекрытия не гарантировано и тестом не проверено. |
| CHK023 | BLOCKED | Карточка ограничивается `visibleFrame` и имеет `fullScreenAuxiliary` в `/Users/yshishenya/.dsh/clutch-dsh-worktree/worktree/wt_6b80dad08d61/apps/macos/RecApp/Sources/Notifications/DesktopNotificationCardPresenter.swift:336-363`; многоэкранный/полноэкранный сценарий и положение индикатора живьём не проверены. |
| CHK024 | BLOCKED | Новые проверки присутствуют, включая геометрию, закрытие и сроки в `/Users/yshishenya/.dsh/clutch-dsh-worktree/worktree/wt_6b80dad08d61/apps/macos/Shared/Tests/DesktopNotificationCardTests.swift:230-650`, но `swift test` в этом ревью не запускался. |
| CHK025 | BLOCKED | Файлы регрессии изменены и содержат проверки карточки/доставки, но зелёный результат текущего рабочего каталога не получен; запуск `DesktopNotification*` не выполнялся. |
| CHK026 | BLOCKED | Полный набор macOS-тестов не запускался; это прямо оставлено открытым задачей T045 в `/Users/yshishenya/.dsh/clutch-dsh-worktree/worktree/wt_6b80dad08d61/specs/274-notification-parity/tasks.md:186-189`. |
| CHK027 | BLOCKED | В `quickstart.md` описаны команды, но нет результата `dev-harness` и нет доказательства проверки именно `/Applications/GRAF Dev.app`; T044 остаётся `[ ]` в `/Users/yshishenya/.dsh/clutch-dsh-worktree/worktree/wt_6b80dad08d61/specs/274-notification-parity/tasks.md:180-185`. |
| CHK028 | BLOCKED | `research.md` содержит декларативные измерения и ограничения, но текущих команд, результатов, снимков и отклонений для этого грязного каталога нет; T044/T045 не закрыты. |
| CHK029 | BLOCKED | Файлы действительно присутствуют в текущем diff, но актуальное доказательство ещё не обновлено: T045 требует после T044 повторить `spec.md`, `plan.md`, `quickstart.md`, `research.md` и `F274.yaml` в `/Users/yshishenya/.dsh/clutch-dsh-worktree/worktree/wt_6b80dad08d61/specs/274-notification-parity/tasks.md:186-189`. |
| CHK030 | PASS | В просмотренных изменениях нет токенов, ключей, содержимого встреч или персональных данных; используются только синтетические значения (`Встреча команды`, `example.test`). Дополнительная санитарная проверка текстов есть в `/Users/yshishenya/.dsh/clutch-dsh-worktree/worktree/wt_6b80dad08d61/apps/macos/Shared/Tests/AppControlAccessibilityTests.swift:293-300`. |

### Ключевые находки для владельца

1. **FAIL, P1 — кнопка закрытия не перенесена в левый верхний угол.** Сейчас
   одновременно код, тест и `research.md` требуют верхний правый угол
   (`/Users/yshishenya/.dsh/clutch-dsh-worktree/worktree/wt_6b80dad08d61/apps/macos/RecApp/Sources/Notifications/DesktopNotificationCardPresenter.swift:557-560`,
   `/Users/yshishenya/.dsh/clutch-dsh-worktree/worktree/wt_6b80dad08d61/apps/macos/Shared/Tests/DesktopNotificationCardTests.swift:268-274`,
   `/Users/yshishenya/.dsh/clutch-dsh-worktree/worktree/wt_6b80dad08d61/specs/274-notification-parity/research.md:218-224`).
2. **FAIL, P1 — разные карточки не имеют общего арбитра.**
   `DesktopNotificationPresenter` назначает `activeCardOwner` только для
   `.meeting` и `.problem` (`/Users/yshishenya/.dsh/clutch-dsh-worktree/worktree/wt_6b80dad08d61/apps/macos/RecApp/Sources/Notifications/DesktopNotificationPresenter.swift:517,648`),
   хотя перечисляет `.preview`, `.shortRecording` и `.recordingPrompt`
   (`/Users/yshishenya/.dsh/clutch-dsh-worktree/worktree/wt_6b80dad08d61/apps/macos/RecApp/Sources/Notifications/DesktopNotificationPresenter.swift:185-190`). Предпросмотр и вопрос о записи напрямую заменяют общую
   карточку (`/Users/yshishenya/.dsh/clutch-dsh-worktree/worktree/wt_6b80dad08d61/apps/macos/RecApp/Sources/Notifications/DesktopNotificationPresenter.swift:408-410`,
   `/Users/yshishenya/.dsh/clutch-dsh-worktree/worktree/wt_6b80dad08d61/apps/macos/RecApp/App/TwoBrainRecApp.swift:1538-1584`). При календарном обновлении
   `reconcileCard` может заменить их карточкой встречи (`/Users/yshishenya/.dsh/clutch-dsh-worktree/worktree/wt_6b80dad08d61/apps/macos/RecApp/Sources/Notifications/DesktopNotificationPresenter.swift:499-531`),
   а `refreshLocal` может принять/поглотить инцидент во время другой карточки
   (`/Users/yshishenya/.dsh/clutch-dsh-worktree/worktree/wt_6b80dad08d61/apps/macos/RecApp/Sources/Notifications/DesktopNotificationPresenter.swift:744-760`) без показа нового сообщения.
3. **FAIL, P1 — короткая запись повторяет заголовок в пояснении.** Минимум
   нужен новый короткий текст без дублирования и отдельная проверка пяти
   вариантов карточки.
4. **BLOCKED/риск, P1 — «все пять текстов помещаются» не доказано.** Тесты
   проверяют счётчик кнопок и геометрию, но не реальные строки всех пяти
   типов, их переносы, крупный шрифт и отсутствие перекрытия. Однострочный
   режим имеет фиксированные 82 точки и фиксированный шрифт.
5. **BLOCKED — живые и автоматические доказательства не получены.** T044 и
   T045 открыты; поэтому нельзя закрывать фичу, даже несмотря на большое число
   отмеченных `[X]` в `tasks.md`.

### Минимальные изменения перед продолжением

- Перенести кнопку закрытия в левый верхний угол, затем синхронно обновить
  геометрию, тест и описание измерений.
- Ввести один владеющий слой показа для встречи, проблемы, предпросмотра,
  короткой записи и вопроса о записи: не заменять активную карточку молча и не
  поглощать инцидент до фактического показа.
- Переписать дублирующий текст короткой записи и добавить проверки текста,
  переноса и границ для всех пяти видов, включая крупный системный шрифт.
- После этого выполнить T044 в `/Applications/GRAF Dev.app`, затем T045:
  новые точные XCTest/полный набор/локальный шлюз и обязательные проверки на
  новом SHA. До этого основной агент может продолжать исправления, но не может
  считать F274 готовой к закрытию или выпуску.
