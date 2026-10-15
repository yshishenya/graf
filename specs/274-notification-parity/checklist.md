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

- [ ] CHK005 Карточка появляется за наблюдаемый срок до встречи и исчезает по
      истечении окна показа.
- [X] CHK006 Закрытая пользователем карточка не появляется снова для того же
      события, включая перезапуск пересчёта календаря.
- [ ] CHK007 Показывается одна карточка на актуальную встречу, даже если подряд
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
`/Users/yshishenya/.dsh/clutch-dsh-worktree/worktree/wt_6b80dad08d61`, ветка
`274-notification-parity`, точный `HEAD` и `source_sha`:
`3cae818cf57ad24ab4b58c5bafd2d0cb8b1df600`. Точная привязка подтверждена
`git rev-parse HEAD` и `.specify/feature.json`. До начала ревью дерево было
чистым. Сверены `spec.md`, `plan.md`, `tasks.md`, `quickstart.md`,
`research.md`, `changes/unreleased/F274.yaml`, код карточки и согласователя,
а также связанные тесты. Commit, push, merge и release в этом проходе не
выполнялись.

`[X]` означает достаточное доказательство кодом, статическим анализом или
точным результатом XCTest для пункта, который не требует живого сценария.
`[ ]` и статус `BLOCKED` означают, что для этого пункта требуется живое,
системное, снимочное или exact-SHA доказательство, которого нет. `PASS` не
используется как замена живой проверке.

| Пункт | Статус | Доказательство и точный остаток |
|---|---|---|
| CHK001 | BLOCKED | В коде и тестах зафиксированы окно 448, карточка 420, поля и вычисляемая высота; повторного измерения эталона в этом проходе нет. |
| CHK002 | BLOCKED | Тесты подтверждают геометрию карточки и левый верхний крестик, но свежий снимок exact-SHA для сравнения с эталоном не получен. Snapshot-тест штатно пропущен без `GRAF_CARD_SNAPSHOT_DIR`. |
| CHK003 | PASS | У общей поверхности есть пять вариантов и раздельные действия. Для короткой записи используются «Запись слишком короткая» и «Записи короче 30 секунд не сохраняются.»; повторения одной и той же фразы в заголовке и пояснении нет. Покрыто `DesktopNotificationCardTests`; 34 теста, 1 ожидаемый пропуск, 0 ошибок. |
| CHK004 | PASS | В проверенных изменениях нет чужого исходного кода, ресурсов или торговых марок; карточка собирается кодом GRAF и системными SF Symbols. |
| CHK005 | BLOCKED | Код и XCTest проверяют сроки встречи, вопроса, проблемы, предпросмотра и короткой записи, но формулировка требует наблюдаемого показа и исчезновения. Живого exact-SHA сценария нет. |
| CHK006 | PASS | `dismissedCards` и стабильный ключ события сохраняются и учитываются при пересчёте; тест обновления календаря после закрытия прошёл на exact SHA. Живая перезагрузка приложения отдельно не заявляется. |
| CHK007 | BLOCKED | Кодовая сверка и XCTest подтверждают единую поверхность и выбор одного кандидата, включая пять владельцев карточки; отдельного живого сценария с конкурирующими событиями в exact-SHA приложении нет. См. отдельную сверку старого замечания ниже. |
| CHK008 | PASS | `shouldRemind` подавляет `active` и `stopping` для любого календарного события; `testCardNeverOffersASecondRecordingDuringActiveMeeting` и `testRecordingSuppressesEveryCalendarOccurrence` прошли. |
| CHK009 | PASS | Действие повторно проверяет актуальность события и безопасную HTTPS-ссылку; перенос, отмена, истечение и небезопасная ссылка покрыты XCTest. |
| CHK010 | PASS | Сохранение настроек вызывает `reconcileCard`, а планировщик удаляет устаревшие системные запросы; отключение напоминаний скрывает карточку в XCTest. |
| CHK011 | PASS | `invalidate` очищает контекст, запросы и общую карточку; выход из аккаунта и очистка инцидента покрыты тестами. |
| CHK012 | BLOCKED | Кодовая ветка локальной карточки не зависит от разрешения, тест с `.denied` есть, но календарная карточка при реально отозванном разрешении macOS в `/Applications/GRAF Dev.app` не проверена. |
| CHK013 | BLOCKED | Собственная карточка не создаёт системный звуковой канал, но режим «Не беспокоить» и фактическая тишина живьём не проверены. |
| CHK014 | PASS | При видимой карточке системная `presentationOptions` возвращает пустой набор; тесты встречи, инцидента и предпросмотра подтверждают отсутствие системного дубликата. |
| CHK015 | BLOCKED | `refreshPermission` и обновление текста настроек предусмотрены кодом, но переключение разрешения macOS туда и обратно без перезапуска не выполнено живьём. |
| CHK016 | BLOCKED | По текущему контракту отдельной плавающей карточки-индикатора нет: состояние остаётся в приложении, строке меню и панели управления. Полный живой цикл записи и исчезновение состояния после обработки не проверены. |
| CHK017 | BLOCKED | Состояния `recording`/`transcribing`/`finished` сохраняются для штатных поверхностей, а `elapsed` не рисуется этой карточкой. Правильная длительность в штатной поверхности живьём не подтверждена. |
| CHK018 | BLOCKED | Команда останова и доступность покрыты кодом и XCTest, но этот пункт требует живой штатной поверхности и клика. Exact-SHA `NSPanel` не был получен через AX-дерево; живого клика нет. |
| CHK019 | BLOCKED | `nonactivatingPanel`, `canBecomeKey == false` и `canBecomeMain == false` подтверждены кодом и тестами; отсутствие перехвата фокуса во всех штатных поверхностях живьём не проверено. |
| CHK020 | BLOCKED | Цвета зависят от `effectiveAppearance`, но светлая и тёмная темы карточки и штатного индикатора не подтверждены живым снимком или ручным сценарием. |
| CHK021 | BLOCKED | Есть `accessibilitySummary`, подписи и announcement, но фактическое чтение карточки и состояния VoiceOver не выполнено. |
| CHK022 | BLOCKED | Длинный русский текст, перенос и вычисляемая высота покрыты обычным тестовым окружением; отдельной проверки крупного системного шрифта нет. Наличие `preferredFont` само по себе не является живым доказательством. |
| CHK023 | BLOCKED | Код использует `visibleFrame`, `.canJoinAllSpaces` и `.fullScreenAuxiliary`, но полноэкранный и многоэкранный сценарии живьём не проверены. |
| CHK024 | PASS | `swift test --package-path apps/macos --filter DesktopNotification`: 55 тестов, 1 ожидаемый пропуск snapshot-теста, 0 ошибок. Покрыты крестик, пять вариантов, границы, длинный текст, флажок, арбитраж и сроки. |
| CHK025 | PASS | На exact SHA прошли связанные регрессии: фильтр `DesktopLocalNotificationDeliveryTests|ShortRecordingNoticeTests|AppLifecycleWindowRegressionTests|AppControlAccessibilityTests|CaptureControlV5Tests` дал 40 тестов, 0 ошибок и 0 пропусков. В состав фильтра `DesktopNotification` входят также 21 тест `DesktopNotificationControlTests`. |
| CHK026 | PASS | `bash apps/macos/Scripts/run-swift-tests.sh`: 1050 тестов, 2 ожидаемых пропуска, 0 ошибок, код возврата 0. Это автоматическое доказательство exact SHA, не живая приёмка. |
| CHK027 | BLOCKED | `/Applications/GRAF Dev.app` установлено, но `infra/scripts/dev-harness.sh status --json` показывает активный manifest `dev-68e4afea0c81` с `source_sha=68e4afea0c8176ffc336617e09be3951086567ef`; это не проверяемый `3cae818…`. Health `pass` активного другого SHA не переносится на F274. |
| CHK028 | BLOCKED | Свежей exact-SHA матрицы живых сценариев, снимков и описания отклонений нет. Snapshot-тест пропущен без `GRAF_CARD_SNAPSHOT_DIR`; T044 и T045 остаются открытыми в `tasks.md`. |
| CHK029 | PASS | `spec.md`, `plan.md`, `tasks.md`, `quickstart.md`, `research.md` и `F274.yaml` сверены с кодом и тестами; при этом T044/T045 не выдаются за закрытые и остаются отдельным гейтом живых доказательств. |
| CHK030 | PASS | В проверенных артефактах нет секретов, токенов, содержимого встреч или персональных данных; используются синтетические значения. |

Итог текущего раздела чеклиста: `PASS` — 13, `BLOCKED` — 17,
`FAIL` — 0. Нулевой `FAIL` означает, что на exact SHA не подтверждён новый
обязательный дефект исходного кода; это не означает готовность F274 к слиянию
или выпуску.

### Отдельная сверка старых замечаний

| Старое замечание | Проверка на `3cae818…` | Статус текущего SHA |
|---|---|---|
| Крестик слева сверху | `DesktopNotificationCardPresenter.swift:658-662` привязывает знак к левому верхнему углу карточки (`14` слева, `12` сверху), а заголовок начинается с отступа `50`. `DesktopNotificationCardTests` проверяет геометрию и попадание мыши в кнопку. | `PASS` по коду/XCTest; `BLOCKED` по живому exact-SHA снимку и клику. Не переносится старый `FAIL` про правый угол. |
| Единый арбитр пяти вариантов | `CardOwner` перечисляет `meeting`, `problem`, `preview`, `shortRecording`, `recordingPrompt`; `cardPriority` и `canPresent` действуют для всех пяти, `reconcileCard` выбирает одного кандидата, используется одна `card`. `testCardBrokerKeepsHigherPriorityProblemAndDoesNotConsumeHiddenIncident` и `testShortRecordingNoticeUsesTheSameBrokerAsOtherCards` покрывают ключевые отрицательные случаи. | `PASS` по коду/XCTest; `BLOCKED` по живому сценарию конкуренции. Не переносится старый `FAIL` про отсутствие арбитра. |
| Отсутствие дублирования | Короткая запись использует одну общую карточку через `DesktopRecordingNoticePresenter`; заголовок «Запись слишком короткая» и сообщение «Записи короче 30 секунд не сохраняются.» различаются. Переходы состояния записи не создают вторую карточку или системный баннер. | `PASS` по коду/XCTest; живой exact-SHA цикл не доказан и покрывается CHK016–018/027. Не переносится старый `FAIL` о повторе текста. |
| Адаптивность | `preferredFont`, перенос по словам, вычисление высоты и отдельная строка действий при необходимости находятся в `DesktopNotificationCardPresenter.swift:428-518,617-690`; `testAllCardKindsKeepTextAndActionsInsideAdaptiveSurface` и `testLongRussianContentWrapsAndRaisesCardWithoutOverlap` прошли. | `PASS` по статическому/XCTest-слою для обычного окружения; `BLOCKED` по эталонному снимку и живому сценарию. |
| Крупный шрифт | Код запрашивает `preferredFont`, но нет отдельного прогона с увеличенным системным размером, снимка и VoiceOver-проверки. | `BLOCKED`; `PASS` не выставляется. Подтверждённого `FAIL` исходного кода нет, но отсутствие доказательства блокирует закрытие. |

### Точный остаток и вердикт

Активный `/Applications/GRAF Dev.app` имеет health `pass`, но весь его
manifest — backend, frontend и macOS app — привязан к
`68e4afea0c8176ffc336617e09be3951086567ef`, а не к проверяемому
`3cae818cf57ad24ab4b58c5bafd2d0cb8b1df600`. `parent_manifest_id=dev-3cae818cf57a`
и `rollback_target_id=dev-3cae818cf57a` не являются доказательством того, что
активный пакет собран с нужного SHA. Поэтому T044/T045 и все живые пункты
остаются `BLOCKED`. Финальный вердикт: **BLOCKED / NO-MERGE / NO-RELEASE**.

Ни один исходный файл, тест, Spec Kit-артефакт, guidance-файл или журнал
изменений в этом проходе не редактировался. Изменения ограничены этим
reviewer-owned чеклистом; отдельный полный отчёт сохранён в
`specs/274-notification-parity/final-review-report.md`.

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
