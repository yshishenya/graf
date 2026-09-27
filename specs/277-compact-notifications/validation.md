# F277 — Доказательства проверки

## Исходная база, до изменения приложения

- Ветка: `277-compact-notifications`.
- Исходный commit: `f5cca687a06dc57ad6ccbef840a0be897eaa6336`.
- Команда: `swift test --package-path apps/macos --filter 'DesktopNotification|DesktopLocalNotification|EmbeddedCabinetNotification|MeetingDetectionPrompt|ShortRecording'`.
- Завершение: 2026-09-26 21:04:14 по часам тестового процесса; код выхода 0.
- XCTest: 86 тестов, 1 пропущен, 0 ошибок; 30.836 секунды выполнения тестов. Отдельная строка Swift Testing о 0 тестах не используется как доказательство.
- Это исходный результат старой реализации. Он не подтверждает новый дизайн, удаление системного канала, полноту доступности или ручную приёмку.
- Сборка сообщала существующие предупреждения `@preconcurrency` на WebKit conformances. Пропущенный тест необходимо отдельно классифицировать при окончательной проверке.
- GRAF Dev не устанавливался и не перезапускался в рамках этого исходного теста.

## Текущая приёмка

## Допуск к реализации — 2026-09-26

- Независимый reviewer перечитал задачи и контракты после исправления B3/B4: UX10/10, Security6/6, Capture5/5; 21/21, ноль открытых. Заключение и подтверждения принадлежат reviewer в `review-report.md`.
- Spec Kit analyze выполнен на текущих 22 задачах: покрыты FR-001–025 и SC-001–007, незакрытых CRITICAL/HIGH, противоречий Конституции, требований без задач и задач без назначения нет. B3/B4 (пути и фильтр regression suites) исправлены до итогового анализа. Shared-file зависимости заданы явно.
- Установленный prerequisite script не поддерживает `--require-spec`: после проверенного `--help` выполнен поддерживаемый `--json --require-tasks --include-tasks`, feature directory совпадает с277; наличие и содержимое spec проверены чтением отдельно.
- Все22 задачи имеют открытые GitHub issues в `yshishenya/graf`, точная карта — tasks.md. Existing reservation #7276 стала итоговой T022; дубли не создавались. Обязательные ensure/validate выполнены: `github-issue-canon: OK (300 Spec Kit issue(s) checked)`.
- Существующий `.gitignore` покрывает `.build`, `node_modules`, `.venv`, `.env`; новых зависимостей нет. Hook не изменил управляемые файлы. Основной checkout и его чужие изменения не менялись.
- Добавление issue links и отметок T001/T002 не меняет требований, зависимостей или объёма задач; analyze остаётся применимым. Это допуск к изменениям, не приёмка приложения.

## Незавершённая проверка приложения

### Наблюдаемый RED до нового рабочего кода

- Выполнен `swift test --package-path apps/macos --filter 'DesktopNotificationAppIntegrationTests|DesktopCabinetRoutePolicyTests.testRetiredNotificationSettingsRouteIsRejectedWithoutAlias|DesktopNotificationControlTests/testF277|DesktopLocalNotificationDeliveryTests/testF277|DesktopNotificationCompactTests|DesktopNotificationPromptLifecycleTests|DesktopNotificationAccessibilityTests|EmbeddedCabinetNotificationSettingsBridgeTests'`.
- Сборка успешна; тестовый процесс завершился с кодом1: 41 тест, 125 assertion failures, из них2 unexpected в WebKit-проверках старого контракта. Повтор `--skip-build` подтвердил тот же итог. Это ожидаемый исход старого поведения, не результат новой реализации.
- Подтверждены отказы геометрии, единственного текста, близкого крестика, сохранения window/control identity, callback после dismiss, reentrant terminal action, приоритетов, сроков0/1/5, quiet и версии2 bridge. Отдельные уже корректные сценарии прошли; их проверки сохранены.
- Node: `node apps/server/tests/browser/settings-consistency.test.cjs --notification-contract`: 6 тестов, 2 PASS/4 FAIL до изменения рабочего JavaScript. READY RED и отсутствие Swift-команд подтверждены рабочим агентом.
- Только после этих результатов рабочим агентам разрешены изменения карточки, координатора и bridge. Главный агент единолично выполняет Swift-сборки.
- Начальная проверка удаления после интеграции приложения обнаружила16 старых символов в ещё не заменённых notification sources; ожидаемый FAIL. Это защита удаления, не замена функциональных тестов.

Новая реализация и её проверки ещё не завершены. Результаты будут добавляться после фактического выполнения. Проверка требований в `review-report.md` не заменяет испытания кода.

### Проверки реализации — промежуточный результат

- Первый общий XCTest-прогон новой реализации: 231 тест, 1 пропуск, 34 assertion failures. Группы coordinator, preferences, history, prompt lifecycle, protected region, tray, WebKit bridge прошли; отказы относятся к геометрии/доступности/клавиатуре карточки и прежнему списку пунктов меню. Это не приёмка. Исправления переданы на повторный прогон.
- Пропуск — экспорт снимков при отсутствующей `GRAF_CARD_SNAPSHOT_DIR`. Повторный прогон задаёт отдельный временный каталог для 20 синтетических PNG; это отрисовка AppKit в тесте, не ручная проверка GRAF Dev.
- `node apps/server/tests/browser/settings-consistency.test.cjs --notification-contract`: 13 PASS, 0 FAIL/skip. Две новые проверки сначала воспроизвели гонку поздних `read`/`test` с новым черновиком (11 PASS/2 FAIL), после исправления все13 проходят. Проверены сохранение видимого выбора, ошибки/повтор и nonce.
- `apps/server/.venv/bin/python -m pytest -q -o addopts= apps/server/tests/contract/test_desktop_notification_retirement.py`: 2 PASS. Проверка удаления охватывает Swift consumers, bridge/template и выделенный раздел JavaScript; статический тест запускается также из macOS XCTest, чтобы попасть в macos-pr.
- Из каталога `apps/server`: `.venv/bin/python -m pytest -q -o addopts= tests/contract/test_desktop_notification_retirement.py tests/contract/test_settings_ui_contract.py tests/unit/test_settings_view_models.py tests/contract/test_cabinet_static_assets_contract.py`: 114 PASS, 2 предупреждения существующей среды, 3.10s.
- `infra/scripts/ci-local.sh --focused`: PASS, 112 тестов, покрытие `partial`, рабочая копия, 7.00s. Этот выбор не включает macOS и не заменяет дополнительные прямые проверки.
- `bash apps/server/scripts/run_local_postgres_tests.sh --focused -q tests/integration/test_settings_ia_flow.py`: 7 PASS, 2 предупреждения, 9.12s; штатный временный PostgreSQL-контейнер завершён и удалён runner. Первый вызов без URL и отдельная попытка при недоступном Docker были ошибками предусловий; в PASS не включены. Данные установленного Dev не использовались.
- `python3 scripts/check_notification_retirement.py`: PASS, 0 нарушений. Ruff новых Python-файлов, `git diff --check` и проверка changelog fragment также проходили; требуется повтор на итоговом состоянии.

### Открытые замечания независимого просмотра кода

- P1: отменённый запуск после `await writer.startAsync` завершает фрагмент с `.permissionDenied` и не вызывает enqueue. Но ошибка записи итогового manifest может оставить `.active`, которое штатное восстановление позднее разрешит к отправке. Проверка повторного сканирования подтверждает только успешный stop; путь ошибки финализации пока не закрыт. Нужен долговечный запрет до асинхронного старта. Изменение writer выходит за согласованные границы уведомлений: у пользователя запрошено отдельное согласие. Код writer/recovery не изменён, замечание блокирует завершение и установку этой версии.
- P2 позднего ответа настроек исправлено с двумя регрессионными Node-проверками.
- P2 двойной отмены неудачного показа исправлено проверкой token перед повторной обработкой отказа.
- P2 старой истории в уже открытом меню исправлено синхронной очисткой при смене authEpoch; runtime-проверка меню прошла.
- P2 отложенного сброса CalendarTray исправляется синхронной инвалидизацией поколения перед новым сетевым запросом; добавлена проверка задержанного старого ответа, результат ожидается в повторном XCTest-прогоне.

Пока нет итогового build/ContractValidation, проверки GRAF Dev, независимого заключения о готовности, PR или exact-SHA CI evidence. Ничего не опубликовано.

### Повторный прогон и визуальный просмотр

- Расширенный фильтр из quickstart с `GRAF_CARD_SNAPSHOT_DIR` завершён 2026-09-26 22:19:02: **240 XCTest, 0 ошибок, 0 пропусков**, 23.987s. Включены дополнительная проверка календарного сброса, проверки таймеров и клавиатуры, а также экспорт 20 снимков.
- `swift build --package-path apps/macos --product TwoBrainRecApp`: PASS, 2.97s. `swift build --package-path apps/macos --product ContractValidation`: PASS, 0.91s; запуск `apps/macos/.build/debug/ContractValidation`: PASS. Это промежуточное состояние до последующей визуальной правки и удаления дополнительных неиспользуемых функций; требуется итоговый повтор.
- Снимки представляют реальный AppKit-компонент тестового процесса, а не сгенерированный макет. Основной агент просмотрел все пять обычных сценариев и пять вариантов с увеличенным текстом, включая светлую и тёмную темы. На `prompt-dark-large` обнаружен обрезанный хвост «7 секунд»: измерения прямоугольников были недостаточны для проверки полного текста. На тёмной теме пустой флажок визуально сливался с фоном. Оба замечания переданы автору компонента; визуальная приёмка **не пройдена**, несмотря на зелёные XCTest.
- Дополнительный просмотр обнаружил неприменяемые `onOpenCalendar`, `.openCalendar`, `cardDismissalKey`, `dismissCard(eventID:)`, старые функции измерения без потребителей и тестовый путь имитации клика без рабочего потребителя. Они удаляются вместо сохранения ради старых тестов; реальное закрытие проверяется через AppKit control.
- Полный `settings-combobox.test.cjs` выполнен рабочим агентом в Chromium на синтетических страницах: PASS. Повторный просмотр выявил отдельный случай `test → изменённые native prefs → обратный выбор` без pending: интерфейс обновлялся, а очередь сохраняла старое значение. Исправление и новый регрессионный тест ещё выполняются.

### Следующий проверочный цикл

- Ошибка полноты large-текста и контраста пустого флажка исправлена. Основной агент повторно просмотрел оба `prompt-*-large` и обычный short: «7 секунд» полностью видны, флажок различим, короткая строка не изменилась. Рабочий агент дополнительно просмотрел все20 PNG. Это подтверждение отрисовки в тестах, не приёмка установленного приложения.
- Самостоятельный прогон45 карточных проверок выявил17 ошибок только в реальном получении клавиатурного фокуса; общий прогон240 ранее не выявлял зависимость от состояния GUI-процесса. Повтор после первой правки: 50 тестов, 19 ошибок, из которых18 относятся к фокусу, одна — неверное `titleState` новой синтетической проверки. Fixture titleState исправлен; фокус ещё диагностируется. Результат240 PASS не используется как подтверждение исправности последнего состояния.
- Для диагностики фокуса временное исключительное владение Swift `.build` передано автору карточки; основной агент и остальные рабочие агенты параллельных сборок не выполняют. Никаких альтернативных приложений не запускается.
- Прямой расширенный Node-прогон теперь **37/37 PASS** после исправления состояния очереди у `test`, 53.309ms. Матрица включает read/test, pending, canEdit, новый nonce и новое поколение того же nonce; старые ответы и незапрошенные сохранения отклоняются.
- Основной агент повторил полный Chromium-тест командой `NODE_PATH=/Users/yshishenya/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules node apps/server/tests/browser/settings-combobox.test.cjs`: PASS, exit0. Прямой вызов без NODE_PATH ранее завершился MODULE_NOT_FOUND и в результат не включён. Установленные зависимости не менялись.
- Дополнительные XCTest с `--skip-build --filter 'DesktopCabinetSessionBridgeTests|EmbeddedCabinetReloadRegressionTests|CabinetSidebarRuntimeTests|EmbeddedCabinetJavaScriptConfirmTests|DesktopCabinetWorkspaceTests|DesktopCabinetPaymentPopupTests|DesktopUploadQueueV5Tests|LocalRecordingWriterSystemAudioTests|CanonicalRecordingManifestTests|CaptureRecoveryTests'`: **106 PASS**, 0 ошибок/пропусков, 31.147s. Это регрессии ранее собранного состояния, не проверка ещё не внесённой защиты ошибки final manifest.
- Независимый reviewer подтвердил P2/SC-003: календарная отметка показа существовала только в памяти. Добавлены9 тестов `--filter testF277MeetingClaim`; наблюдаемый RED —9 тестов,25 assertion failures,1.082s. Только после этого разрешена постоянная контекстная отметка показа и односторонняя миграция старых доставленных/отменённых будущих reservations. Реализация выполняется, результат ещё не объявлен.
- `python3 scripts/check_spec_kit_governance.py`: PASS, bootstrap integrity + GRAF invariants. Проверка changelog fragment и удаления старого канала проходят. Итоговые runtime/CI gates остаются открытыми.

### F277 — промежуточный полный прогон, 2026-09-26 22:54

- После диагностического прогона карточек (52 теста, 4 ошибки в двух отрицательных сценариях фокуса) основной агент разделил реальные проверки AppKit и моделирование задержанного/отклонённого системного запроса. `NotificationCardEnvironment` теперь передаёт запросы активации и выбора key window через проверяемую границу; значения по умолчанию вызывают те же публичные AppKit API. Настоящий переход из неактивного приложения и реальные клавиатурные действия не заменены имитацией. Две отрицательные проверки используют явно моделируемый поздний системный сигнал и не выдают его за работу ОС.
- `swift test --package-path apps/macos --filter 'DesktopNotificationAccessibilityTests'`: **17 PASS, 0 ошибок/пропусков**, 3.269s; журнал `/tmp/graf-f277-focus-boundary.log`.
- Новые проверки `--filter 'testF277MeetingReceiptTTL|testMeetingReceiptsHaveFiniteUnextendedExpiryAndPruneExpiredOccurrences'` сначала дали **3 теста, 5 assertion failures**, 0.383s (`/tmp/graf-f277-meeting-ttl-red.log`). Доказан повтор карточки/звука после продления `endsAt`, в том числе после пересоздания presenter/store. После исправления TTL отметки на `startsAt + 120` независимо от изменяемого `endsAt`: **3 PASS**, 0.216s (`/tmp/graf-f277-meeting-ttl-green.log`). Видимый срок остаётся `min(due + 120, endsAt)`; завершённое событие не получает новую отметку.
- Полная команда XCTest из текущего quickstart выполнена с `GRAF_CARD_SNAPSHOT_DIR=/tmp/graf-f277-card-renders-current.56Flis`: **263 PASS, 0 ошибок, 0 пропусков**, 25.168s. Журнал `/tmp/graf-f277-current-full.log`. Это актуальное состояние после исправлений фокуса, миграции календарных отметок, их TTL и JavaScript-очереди, а не повторное использование прежних 240 PASS.
- `swift build --package-path apps/macos --product TwoBrainRecApp`: **PASS**, 0.79s. `swift build --package-path apps/macos --product ContractValidation`: **PASS**, 0.75s; `apps/macos/.build/debug/ContractValidation`: **PASS**. Журналы `/tmp/graf-f277-current-app-build.log`, `/tmp/graf-f277-current-contract-build.log`, `/tmp/graf-f277-current-contract-validation.log`.
- `node apps/server/tests/browser/settings-consistency.test.cjs --notification-contract`: **37 PASS**, 61.789ms; `/tmp/graf-f277-node-current.log`. `apps/server/.venv/bin/python -m pytest -q -o addopts= apps/server/tests/contract/test_desktop_notification_retirement.py`: **2 PASS**, 0.15s, два ранее известных предупреждения среды; `/tmp/graf-f277-retirement-current.log`. `python3 scripts/check_notification_retirement.py`: **PASS, 0 нарушений**; `git diff --check`: PASS.
- Отрисованы 20 свежих синтетических AppKit PNG в указанном временном каталоге. Основной агент просмотрел все 20: пять сценариев × две темы × стандартный/увеличенный текст. Крестик не занимает колонку, текст/действия не обрезаны, полный отсчёт виден, пустой флажок различим. Это измерение и просмотр компонента в XCTest, **не** установленный GRAF Dev и не ручная проверка VoiceOver.
- Текущая сборка повторно прошла дополнительный regression-фильтр кабинета/записи/восстановления из предыдущего цикла: **106 PASS**, 0 ошибок/пропусков, 31.062s; `/tmp/graf-f277-current-regressions.log`. Он не покрывает новый сценарий отказа финального manifest и не закрывает P1.
- Независимый reviewer подтвердил корректность границы AppKit и сохранение настоящей интеграционной проверки фокуса; не обнаружил нового активного старого канала. Выявленная лишняя обёртка `screensChanged() → reposition()` удалена; тест теперь подаёт событие изменения экранов в тот же NotificationCenter, который слушает рабочий компонент. Изменение требует повторного focused-прогона.
- P1 ошибки финализации отменённой записи остаётся открытым и блокирует установку и завершение. Для изменения writer/recovery всё ещё требуется отдельное согласие на расширение scope. Никакого релиза, установки, PR или exact-SHA CI этим прогоном не заявляется.

### F277 — повторная проверка среды и открытый сбой, 2026-09-26 23:08

- После удаления `screensChanged()` повторный запуск 21 карточной проверки обнаружил 19 ошибок получения настоящего фокуса (`/tmp/graf-f277-final-cleanup-tests.log`). Отдельный временный контроль обычного `NSWindow`, без notification-компонента, тоже не получил фокус: `active=false`, `key=false`, запуск AppKit завершён (`/tmp/graf-f277-native-focus-baseline.log`). Этот диагностический тест после проверки удалён; причина недоступности фокуса не приписывается доказанному отказу ОС.
- Пять зависимых от фокуса тестов теперь сначала проверяют обычное AppKit-окно **до** создания карточки. Только отсутствие этой предпосылки даёт SKIP; незавершённый запуск/невозможность установить или восстановить исходное состояние дают FAIL. После успешного контроля ошибки самой карточки остаются FAIL. Независимый reviewer проверил эти границы. Его замечание о совпадении двухсекундных таймеров устранено: ожидание результата явного запроса в обоих местах составляет 3 секунды, рабочая отмена остаётся 2 секунды.
- Общий прогон текущего состояния `/tmp/graf-f277-final-focused.log`: **263 теста, 5 пропусков, 6 ошибок (3 unexpected), FAIL**, 54.784s. Три WebKit-теста не дождались начальной загрузки JavaScript. Дополнительные `NSCocoaError256` были искусственно созданы самим `wait()` после тайм-аута, а не ошибкой чтения файлов. Результат 263 PASS из 22:54 не подтверждает это более позднее состояние.
- Изолированный `swift test --package-path apps/macos --skip-build --filter 'EmbeddedCabinetNotificationSettingsBridgeTests'`: **8 PASS**, 0 ошибок/пропусков, 0.771s (`/tmp/graf-f277-webkit-isolated.log`).
- Проверка пары `--filter 'DesktopNotificationAccessibilityTests/testExplicitFocusFromInactiveAppDoesNotDependOnAnotherSuiteActivation|EmbeddedCabinetNotificationSettingsBridgeTests/testAccountChangeWhileActivationWaitsCannotReconnectOldDocument'`: **2 теста, 1 пропуск, 0 ошибок**, 2.358s (`/tmp/graf-f277-focus-webkit-pair.log`).
- Совместный `--filter 'DesktopNotificationAccessibilityTests|DesktopNotificationPromptLifecycleTests|EmbeddedCabinetNotificationSettingsBridgeTests'`: **40 тестов, 5 пропусков, 0 ошибок**, 14.005s (`/tmp/graf-f277-focus-webkit-suites.log`). Все 8 WebKit-тестов проходят и после проверок фокуса; прямая причинная связь с `NSApp.run()/stop()` не доказана. Эти два узких запуска использовали прежнюю тестовую сборку до правки одного трёхсекундного ожидания.
- Итог: общий сбой пока не исправлен и не закрыт успешным узким повтором. Пять SKIP — отсутствующее подтверждение клавиатурного управления, а не его приёмка. Обязательны повтор после улучшения диагностики и ручная проверка только установленного GRAF Dev после снятия P1. T006/T015/T019/T020 остаются открыты; T012 снова открыт до устойчивой совместной проверки.
- Повтор `python3 scripts/check_notification_retirement.py`: **PASS, 0 нарушений**; `git diff --check`: PASS. Уточнено, что односторонняя миграция не обещает точную дедупликацию после запуска старой версии и создания ею новых записей; старый канал ради rollback не возвращается.
- Writer/recovery, установленный GRAF Dev, GitHub и релизы в этом цикле не изменялись. P1 по-прежнему требует решения пользователя о расширении границ работы.

### F277 — уточнённая диагностика, 2026-09-26 23:10

- `wait()` в WebKit-тестах больше не скрывает последнюю ошибку JavaScript и не выдаёт её за ошибку файла: сохраняются только domain/code, последнее булево значение и isLoading, без `userInfo`/содержимого страницы. Тайм-аут регистрирует один бросающий `XCTUnwrap`, прекращающий тест. Число попыток 100, пауза 50мс и условие успеха не изменены; это улучшение диагностики, не исправление установленной причины.
- Свежая пересборка и команда `swift test --package-path apps/macos --filter 'DesktopNotificationAccessibilityTests|DesktopNotificationPromptLifecycleTests|EmbeddedCabinetNotificationSettingsBridgeTests'`: **40 тестов, 5 пропусков, 0 ошибок**, 13.974s (`/tmp/graf-f277-diagnostics-focused.log`). Включена правка трёхсекундного ожидания; все8 WebKit проходят.
- `swift build --package-path apps/macos --product TwoBrainRecApp`: **PASS**, 2.30s (`/tmp/graf-f277-final-app-build.log`); `swift build --package-path apps/macos --product ContractValidation`: **PASS**, 0.66s (`/tmp/graf-f277-final-contract-build.log`); `apps/macos/.build/debug/ContractValidation`: **PASS** (`/tmp/graf-f277-final-contract-validation.log`).
- Проверка удаления снова **0 нарушений**, `git diff --check` PASS. Общий сбой, пять недоступных фокусных проверок, ручная приёмка и P1 этим узким результатом не закрываются.
- Повтор всего фильтра quickstart с новой диагностикой и экспортом изображений: **263 теста, 5 пропусков, 3 ошибки (0 unexpected), FAIL**, 54.918s (`/tmp/graf-f277-diagnostics-full.log`). Те же три WebKit-сценария воспроизводятся; количество ошибок уменьшилось только из-за удаления двойной регистрации, не из-за исправления сценариев. Минимальная страница сообщает `lastJSError=none`, `lastBooleanResult=false`, `isLoading=true`; предположение об ошибке чтения файла исключено. Причина незавершённой загрузки ещё не установлена.
- Сочетание только раскладки и WebKit (`--filter 'DesktopNotificationCardTests|DesktopNotificationCompactTests|EmbeddedCabinetNotificationSettingsBridgeTests'`) без экспорта: **25 тестов, 1 пропуск экспорта, 0 ошибок**, 1.018s (`/tmp/graf-f277-layout-webkit.log`); с `GRAF_CARD_SNAPSHOT_DIR=/tmp/graf-f277-card-renders-current.56Flis`: **25 PASS, 0 пропусков**, 1.262s (`/tmp/graf-f277-render-webkit.log`). Ни экспорт изображений отдельно, ни проверки фокуса отдельно пока не воспроизвели общий сбой.
- Независимый reviewer одобрил диагностическую правку: успех только при настоящем `Bool == true`, тайм-аут остаётся FAIL, дополнительных повторных запусков/SKIP нет. Это не заключение о готовности фичи.

### F277 — очистка недостижимых связей T018, 2026-09-26 23:29

- Независимый просмотр нашёл три команды `DesktopControlAction.settings/localRecordings/permissions` без рабочих отправителей, цепочку `grafOpenLocalRecordingControls` и свойства snapshot `calendarContextEventID/permissionBlocker/completedRecording/recoveryAction/localIssues`. Основной агент подтвердил поиск потребителей; карта удаления дополнена в пределах FR-021/T018. Прямые методы открытия настроек/разрешений, адресная навигация и действующий календарный контекст приложения не удаляются.
- До удаления расширен `check_notification_retirement.py`: различает конкретные типы, не запрещает одноимённые поля диагностики и живые методы. RED: **11 нарушений**; pytest **1 FAIL / 23 PASS**, 0.32s (`/tmp/graf-f277-dead-control-red.log`), падает только проверка текущего дерева. Добавлены отрицательные проверки каждой команды, каждого поля и старого сообщения.
- Новая проверка `testOwnedFreshServerAcceptedItemsStaySilentAndLocalBlockedActionOnlyOpensRecording` сначала выявила ошибочную фикстуру: `.blocked/package_not_uploadable` была задана без рабочей категории `.localResource` и с отправляемым профилем. Исправлены только тестовые данные — отдельные sessionID, подтверждённый владелец, свежие времена, срок хранения +7дней, неотправляемый профиль и явные проверки `.cannotSend/requiresUserAttention`. **До удаления старого кода: 1 PASS**, 0.104s (`/tmp/graf-f277-live-custody-before-cleanup.log`). Проверяется реальный presenter, настоящая кнопка, единственная команда `.localRecording(id)` и неизменность снимка, а не старое вычисляемое свойство.
- Удалены объявления, три недостижимые ветки приложения, Notification.Name и подписчик оболочки, лишние поля snapshot и тесты только старой логики. Вычисление разрешений стало локальным `let` с прежним условием/текстом; start/stop/pause/resume, `showRecording`, `recordingNavigationRequest` и прямые пути настроек/разрешений сохранены. Независимый reviewer подтвердил границы и отсутствие потери рабочих вызовов. Удалён ненужный импорт AppKit из модели управления, вместо него используется Foundation.
- После удаления Python: **24 PASS**, 0.28s, два известных предупреждения (`/tmp/graf-f277-dead-control-green.log`); guard **0 нарушений**. Swift-фильтр `DesktopNotificationControlTests|DesktopLocalNotificationDeliveryTests|DesktopUploadQueueV5Tests|DesktopNotificationAppIntegrationTests|CabinetSidebarRuntimeTests|DesktopCabinetWorkspaceTests`: **117 PASS, 0 пропусков**, 5.812s (`/tmp/graf-f277-dead-control-swift.log`). App build **PASS 0.79s**, ContractValidation build **PASS 0.74s**, запуск **PASS** (`/tmp/graf-f277-cleanup-{app-build,contract-build,contract}.log`). Последняя замена импорта требует свежей пересборки; она не меняет модель и будет проверена отдельно.
- T018 отмечен выполненным по карте удаления, независимому просмотру и scoped-проверкам. Это не закрытие T019/T020/T021/T022 или GitHub issue: общий WebKit-сбой, ручная приёмка и P1 остаются открытыми. Никаких commits/PR/установки/release в этом цикле.

### F277 — сужение WebKit-сбоя

- 57 тестов (accessibility + card + compact + prompt + WebKit), со снимками: **5 SKIP, 3 FAIL**, 30.462s (`/tmp/graf-f277-combined57.log`). 26 тестов (card + prompt + minimal WebKit), со снимками: **2 SKIP, 1 FAIL**, 10.688s (`/tmp/graf-f277-card-prompt26.log`); без экспорта: **3 SKIP, 0 FAIL**, 5.144s (`/tmp/graf-f277-card-prompt-noexport.log`). Пропуск экспорта в последнем запуске не считается его приёмкой.
- Только экспорт + весь prompt-набор + minimal WebKit: **17 тестов, 2 SKIP, 0 FAIL**, 5.129s (`/tmp/graf-f277-render-prompt17.log`). Только проверка геометрии всех тем/шрифтов + тот же остаток: **17 тестов, 2 SKIP, 0 FAIL**, 5.053s (`/tmp/graf-f277-fit-prompt17.log`). Обе эти card-проверки вместе + тот же остаток: **18 тестов, 2 SKIP, 1 FAIL**, 15.409s (`/tmp/graf-f277-fit-render-prompt18.log`).
- Обе card-проверки + только две независимые focus-пробы + minimal WebKit: **5 тестов, 2 SKIP, 0 FAIL**, 4.747s (`/tmp/graf-f277-fit-render-focus-five.log`). Следовательно, простой порядок export→focus или одни вызовы run/stop не доказаны как достаточная причина.
- Эксперимент с видимым неактивирующим NSPanel для minimal WebKit также воспроизвёл сбой со снимками: **33 теста, 2 SKIP, 3 FAIL**, 21.539s (`/tmp/graf-f277-window-fixture-samecase.log`). Эксперимент полностью откатан; полезная диагностика wait сохранена. Содержимое страницы не логируется. Причина взаимодействия наборов пока не установлена; никакие тайм-ауты, условия WebKit или пропуски для него не ослаблялись.
- Отдельный согласованный reviewer-ом эксперимент изолировал только `announce` в девяти обычных инициализациях prompt lifecycle тестов; настоящие часы, автоматический таймер, окна и все утверждения оставались прежними. Тот же набор18 всё равно дал **2 SKIP, 1 FAIL**, 14.924s (`/tmp/graf-f277-noannouncements-B18.log`). Помощник и все девять подмен полностью удалены; рабочий `NSAccessibility.post` и специализированная проверка единственного объявления не менялись. Гипотеза объявлений как достаточной причины этим экспериментом не подтверждена.

### F277 — итог проверенного состояния очистки, 2026-09-26 23:33

- После отката обоих диагностических экспериментов и замены ненужного AppKit-импорта в модели на Foundation заново пересобран и выполнен тот же scoped-фильтр: **117 PASS, 0 ошибок/пропусков**, 5.666s (`/tmp/graf-f277-cleanup-final117.log`).
- App build **PASS 0.54s** (`/tmp/graf-f277-cleanup-final-app.log`), ContractValidation build **PASS 0.75s** (`/tmp/graf-f277-cleanup-final-contract-build.log`), запуск **PASS** (`/tmp/graf-f277-cleanup-final-contract.log`). Ruff двух Python-файлов PASS; `check_spec_kit_governance.py` PASS (bootstrap integrity + GRAF invariants); `git diff --check` PASS.
- Это актуальное подтверждение очистки T018, не общая приёмка. Последний полный набор остаётся FAIL; его минимизированный сбой сохраняется. Пять проверок настоящего фокуса и ручная матрица GRAF Dev требуют отдельного подтверждения. P1 долговечного запрета отменённой записи остаётся за согласованными границами и требует решения пользователя; writer/recovery не изменены.

### F277 — завершение жизненного цикла нативного окна, 2026-09-27

- Проверка предыдущего состояния подтвердила завершение диагностических процессов; новая реализация продолжена в `277-compact-notifications`, основной checkout не менялся. Требования и границы capture engine не пересмотрены. Повторно прочитан применимый договор; reviewer-owned требования остаются 21/21 PASS, не runtime-приёмкой.
- Новые проверки выявили: простое `orderOut` не посылает `NSWindow.willCloseNotification`; переход на `close()` исправляет нативное завершение, но сам по себе не освобождает окно. Явное отсоединение `contentView` освобождает содержимое, но не окно. Раннее обнуление состояния/обработчиков сохранено, восстановление прежнего фокуса защищено поколением от повторного входа при закрытии.
- Сравнение с обычной `NSPanel` изолировало удержание без содержимого и подкласса GRAF: `.canJoinAllSpaces` отдельно и `.transient` отдельно освобождались; `.fullScreenAuxiliary` отдельно удерживалась. Сброс `collectionBehavior` после `close()` не помог. Сброс перед `close()` освобождал контроль, но предварительный `orderOut()` снова приводил к удержанию. Журналы: `/tmp/graf-f277-native-{collection-only,clear-collection,allspaces-only,transient-only,fullscreen-only,clear-before-close,hide-clear-close}.log`. Эти сравнения устанавливают наблюдаемую последовательность, не внутренний механизм AppKit.
- Рабочая очистка теперь адресует только сохранённое старое окно: снять флаги → `close()` → отсоединить содержимое. Новое видимое окно сохраняет все три исходных флага. Регрессии проверяют однократное нативное закрытие, отсутствие пользовательского действия при замене/истечении, повторный вход наблюдателя с новой карточкой и освобождение presenter/window/rootView для всех пяти сценариев.
- Изолированный эксперимент с начальной загрузкой WK внутри `NSApplication.run()` не помог: **18 тестов, 2 SKIP, 1 FAIL**, 20.209s (`/tmp/graf-f277-wk-continuous-loop18.log`). Эксперимент полностью удалён. После исправления порядка закрытия совместный набор **23 теста, 2 SKIP, 0 ошибок**, 5.371s (`/tmp/graf-f277-retirement-webkit23.log`); минимальная страница выполнила start→commit→finish. До загрузки оставалось 3 окна вместо 75; одно скрытое окно связано с тестом принудительного внешнего `orderOut` и не покрывается доказательством обычного пути завершения.
- Первый полный прогон после исправления: **266 тестов, 5 SKIP, 7 ошибок**, 38.380s (`/tmp/graf-f277-retirement-full265.log`; имя файла не отражает фактический счётчик). Все 8 WebKit-тестов прошли. Две ошибки — устаревшие source-assertions старых связей настроек/разрешений после T018; пять — требование немедленного освобождения окна после autoreleasepool в уже активировавшем AppKit процессе.
- Последний случай сужен до accessibility-prefix + release-test: **18 тестов, 3 SKIP, 5 ошибок**, 8.767s (`/tmp/graf-f277-release-after-focus18.log`). Ограниченное ожидание 20×10мс без операций над закрытым окном и без нового run/stop позволило освободиться всем пяти рабочим окнам: **18 тестов, 3 SKIP, 0 ошибок**, 10.029s (`/tmp/graf-f277-release-postfocus-control.log`). Немедленное освобождение обычного контрольного окна также не было доказано. Временный контроль и вся печать удалены; постоянный тест проверяет фактическое освобождение с ограниченной обработкой событий.
- Выполнена отрицательная проверка именно окончательного асинхронного теста: временно удалена только строка сброса флагов рабочего окна. **18 тестов, 3 SKIP, 5 ошибок**, 10.177s (`/tmp/graf-f277-native-async-retirement-red.log`), все пять окон остались. Строка восстановлена перед следующим прогоном. Следовательно, ожидание не скрывает исходное удержание. Условия и сроки WebKit-тестов не ослаблены; весь временный WKNavigationDelegate и диагностические сообщения удалены.
- Независимый просмотр одобрил порядок очистки и поведенческие регрессии; немедленное освобождение не объявляется общим контрактом AppKit. Настоящий фокус, визуальное завершение в fullscreen и ручная приёмка остаются отдельными воротами.
- Тест интеграции настроек/разрешений переведён с удалённых веток `syncControlPanel` на действующие связи `CaptureControlView`, защищённый `presentPermissionSetup`, раздел recording и адресное открытие принадлежащей текущему контексту записи. Старые обработчики не возвращены ради теста. Проверка исходников: **0 нарушений**; Node-контракт уведомлений: **37 PASS**, 54.757ms; Python retirement: **24 PASS**, 0.29s, два прежних предупреждения; `git diff --check` PASS.
- P1 writer/recovery остаётся нерешённым, отдельно запрошено разрешение на расширение границ. Не выполнялись установка GRAF Dev, изменения writer/recovery, GitHub, релиз или публикация. Этот раздел фиксирует прогресс, не завершение F277.

### Подтверждённые результаты после исправления закрытия окна — 2026-09-27

Повторно проверены текущее рабочее дерево `277-compact-notifications` на базе
`f5cca687a06dc57ad6ccbef840a0be897eaa6336`, исходники и завершённые журналы.
Активных Swift/build/XCTest процессов из предыдущего запуска нет; команды
не перезапускались из-за потери прежнего идентификатора процесса.

- Общий фильтр `swift test` из quickstart, с
  `GRAF_CARD_SNAPSHOT_DIR=/tmp/graf-f277-card-renders-current.56Flis`:
  **266 тестов, 5 SKIP, 0 ошибок**, 39.305s. Завершён 2026-09-27 00:12:14
  по часам XCTest; журнал `/tmp/graf-f277-retirement-full266-green.log`.
  Все 8 проверок `EmbeddedCabinetNotificationSettingsBridgeTests` прошли
  внутри этого общего набора. Это заменяет прежний результат совместного
  прогона FAIL; проверки WebKit не ослаблены.
- `swift build --package-path apps/macos --product TwoBrainRecApp`: PASS,
  1.41s, `/tmp/graf-f277-retirement-app-build.log`.
  `swift build --package-path apps/macos --product ContractValidation`: PASS,
  0.20s, `/tmp/graf-f277-retirement-contract-build.log`.
  `apps/macos/.build/debug/ContractValidation`: PASS,
  `/tmp/graf-f277-retirement-contract.log`.
  Предупреждения WebKit о `@preconcurrency` сохраняются; сборка не объявляется
  выполненной без предупреждений.
- Дополнительный фильтр
  `DesktopNotificationControlTests|DesktopLocalNotificationDeliveryTests|DesktopUploadQueueV5Tests|DesktopNotificationAppIntegrationTests|CabinetSidebarRuntimeTests|DesktopCabinetWorkspaceTests`:
  **117 тестов, 0 ошибок и пропусков**, 10.810s,
  `/tmp/graf-f277-retirement-regression117.log`. Он частично пересекается с
  общим набором, поэтому результаты не складываются в число уникальных тестов.
- Свежий `node apps/server/tests/browser/settings-consistency.test.cjs --notification-contract`:
  **37 PASS**, 52.279ms, `/tmp/graf-f277-final-notification-node.log`.
- Свежий `apps/server/.venv/bin/python -m pytest -q -o addopts= apps/server/tests/contract/test_desktop_notification_retirement.py`:
  **24 PASS**, 0.24s, два прежних предупреждения среды,
  `/tmp/graf-f277-final-retirement-pytest.log`.
  `python3 scripts/check_notification_retirement.py`: **0 нарушений**.
- Свежий `bash apps/server/scripts/run_local_postgres_tests.sh --focused -q tests/integration/test_settings_ia_flow.py`:
  **7 PASS**, 7.70s тестов, два предупреждения,
  `/tmp/graf-f277-final-settings-ia.log`. Runner подтвердил удаление своего
  изолированного тестового контейнера; установленный Dev не использовался.
- Существующий `apps/server/tests/browser/settings-combobox.test.cjs`:
  **PASS в Chromium и WebKit**, код выхода0. Использована уже установленная
  библиотека: `NODE_PATH=/Users/yshishenya/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules`;
  для второго запуска дополнительно `BROWSER=webkit`. Журналы:
  `/tmp/graf-f277-final-combobox-chromium-configured.log` и
  `/tmp/graf-f277-final-combobox-webkit-configured.log`.
  Обычный запуск без NODE_PATH остановился до тестов с MODULE_NOT_FOUND;
  он не считается PASS. Зависимости не устанавливались. Browser skill
  в текущем окружении отсутствует; выполнен существующий автоматический
  тест на синтетических страницах, не ручная проверка встроенного кабинета.
- `infra/scripts/ci-local.sh --plan`, затем `--focused`: PASS,
  **112 тестов**, 5.13s общего выполнения, покрытие `partial`,
  `/tmp/graf-f277-final-ci-plan.log` и `/tmp/graf-f277-final-ci-focused.log`.
  Это диагностика рабочей копии, не exact-SHA GitHub gate.
- Просмотрены экспортированные настоящим AppKit тестового процесса изображения
  `prompt-dark-large`, `short-dark-standard`, `meeting-light-standard`,
  `problem-light-large`, `preview-dark-standard`: видимое содержимое не
  обрезано, крупный отсчёт переносится полностью, пустой флажок различим,
  закрытие вынесено в верхний левый край. Это ограниченная проверка снимков,
  не ручная матрица GRAF Dev, не доказательство клавиатуры или VoiceOver.
- Независимый reviewer повторно сверил окончательный `clear()`, защиту
  повторного входа, действующие связи настроек и разрешений, отрицательный
  тест освобождения пяти окон и итоговый общий журнал. Изменения этого участка
  одобрены; новых блокирующих замечаний к нему не обнаружено.

T012 возвращён в выполненное состояние: проверки нового договора настроек
прошли в общем native/WebKit наборе, Node, обоих браузерах и pytest с базой.
Это выполнение тестовой задачи, не закрытие T019/T020/T021/T022 или её issue.
Пять SKIP означают отсутствие подтверждения настоящего фокуса обычного
AppKit-окна в тестовом host: три accessibility-проверки и две проверки
фокусного удержания/сроков. Они не превращены в PASS. P1 writer/recovery,
ручная приёмка единственного GRAF Dev и exact-SHA PR-проверки остаются
обязательными незавершёнными условиями. Writer/recovery, установленное
приложение и внешний трекер не изменялись; релиз не выполнялся.

### Повторный визуальный просмотр и расширение очистки

- Основной агент досмотрел все 20 изображений последнего экспорта: пять
  сценариев × aqua/darkAqua × стандартный/увеличенный в 1.6 раза текст.
  Проверены полные подписи, положение закрытия, отдельная строка флажка и
  перенос календарных действий. В этой матрице обрезания и перекрытия не
  обнаружены. Изображения относятся к AppKit-компоненту тестового процесса;
  установленное приложение, переключение системного размера текста,
  VoiceOver и полноэкранный режим ими не проверены.
- T004 отмечен выполненным как задача построения геометрии: сверены рабочие
  measure/update/controls, непрозрачные цвета без анимаций, 7 compact-тестов
  общего успешного набора, проверки контраста текста/основного действия и
  видимой границы флажка. Фон всегда непрозрачен, а переходы не анимируются,
  поэтому отдельное включение Reduce Transparency/Reduce Motion не требуется
  для отключения этих эффектов. Настоящий фокус и ручная приёмка остаются
  открытыми в T015/T017/T020; T004 не закрывает их.
- Независимый аудит удаления нашёл один реальный остаток: неиспользуемый
  CSS-селектор `[data-local-notification-permission]`. Также обнаружено,
  что source guard не проверял Shared/Sources, Shared/Tests и CSS, а его
  проверка подключения cleanup принимала простое текстовое упоминание.
  T018 открыт снова; ограниченная правка удаления и отрицательные тесты
  выполняются в его прежних границах. Это не изменение writer/recovery.

### Завершение расширенной очистки — 2026-09-27

- Рабочий агент изменил только CSS, source guard и его тесты. Добавлено 27
  случаев с сохранением 24 прежних. Агент зафиксировал RED: 23 failed,
  28 passed; после исправления GREEN: 51 passed. Основной агент прочитал
  полные исходники обеих проверок и diff единственной удалённой CSS-строки.
- Независимый повтор основным агентом:
  `apps/server/.venv/bin/python -B -m pytest --noconftest -p no:cacheprovider -q apps/server/tests/contract/test_desktop_notification_retirement.py --tb=short`
  — **51 PASS**, 1.53s, exit0.
- `python3 -B scripts/check_notification_retirement.py` — **0 нарушений**;
  `apps/server/.venv/bin/python -B -m ruff check scripts/check_notification_retirement.py apps/server/tests/contract/test_desktop_notification_retirement.py`
  — PASS; `git diff --check` — PASS.
- После удаления CSS повторён `settings-combobox.test.cjs` с ранее указанным
  NODE_PATH и BROWSER=webkit: **PASS**, exit0. Повторён
  `infra/scripts/ci-local.sh --focused`: **112 PASS**, два прежних
  предупреждения, 2.38s тестов / 5.63s всего, покрытие partial.
- T018 снова выполнен. Проверка лексическая: исключает комментарии/литералы,
  сохраняет исполняемые интерполяции и требует прямой формы cleanup-вызова,
  но не доказывает достижимость функций, не разрешает макросы/псевдонимы или
  условную компиляцию и не разбирает Swift regex literals. Поэтому отсутствие
  любого мёртвого кода не объявляется математически доказанным.
- Swift-код последней правкой не менялся; результаты 266 тестов с пятью
  SKIP и отдельного набора 117 PASS остаются применимыми, но не суммируются
  как непересекающиеся проверки. Полная приёмка всё ещё не завершена.

Дальнейшая приёмка требует решения по ранее повторно зафиксированному P1:
разрешить ли узкое изменение writer/recovery для долговечного запрета
отменённой записи. Пока такого согласия нет, этот участок и установленный
GRAF Dev не изменены. Ручная проверка фокуса/VoiceOver/экранов, итоговая
сверка реализации и PR-проверки остаются открытыми. Успешная очистка не
заменяет их и не разрешает выпуск.

### Разрешение P1 и обновление предварительных условий — 2026-09-27

Пользователь ответил «разрешаю» на последнее явное предложение расширить
задачу на узкую защиту writer/recovery/допуска отправки. Прежнее отсутствие
разрешения больше не является блокером. Это не разрешение выпуска.

Clarify: принят один ранее заданный вопрос, новых вопросов0; в spec обновлены
Context, Session2026-09-27, US2, Edge Cases, FR-026–028, SC-008 и Assumptions.
Все категории (scope, данные, взаимодействие, надёжность/приватность,
зависимости, отказы, ограничения, термины, критерии завершения, placeholders)
ясны для узкого расширения; неразрешённых продуктовых вопросов0.
Built-in requirements checklist: 5/5 → 5/5, отметки не изменялись.

Plan/data-model/research/quickstart дополнены; необязательный agent-context
hook пропущен, корневой AGENTS не менялся. Reviewer повторно проверил все26
custom пунктов (ux10/security8/audio8): предварительный PASS26/26,
`scope-review.md`. Добавлены T023–T026, переданы для окончательной сверки.

Основной read-only analyze после добавления задач: 28FR + 8SC, 26tasks,
покрытие36/36; новых несвязанных задач0, CRITICAL0/HIGH0, неоднозначностей0,
дублирующих требований0. FR-026→T023/T024/T026;
FR-027→T023–T026; FR-028/SC-008→T023–T026; прежняя матрица сохраняется.
T023 RED предшествует T024/T025, T026 предшествует общей приёмке.
Установленный prerequisite script не поддерживает --require-spec: проверены
существование spec отдельно и поддерживаемые --json --require-tasks --include-tasks.

Live dedupe нашёл прежние22открытых владельца T001–T022, новых IDs не было.
Создана одна issue #7336 с явным владением T023/T024/T025/T026; прежние связи
сохранены. Обязательный ensure hook прошёл без изменения guidance/AGENTS.
Это допуск к последующей реализации после финального reviewer/issue gate,
не runtime-проверка исправления.

Окончательный reviewer gate с Phase8: 26/26 PASS,0блокеров; обязательный
issue canon validate: PASS,300SpecKit issues. Синхронизация #7336 завершена,
прочие22issue остаются открытыми. Перед кодом дополнительных подтверждений
пользователя не требовалось.

### P1 — RED и первые проверки реализации

- До изменения модели/writer/recovery добавлен исполняемый тест
  `RecordingStartAcceptanceTests.testPendingRecoveryNeverRepairsOrRemovesAudio`.
  `swift test --package-path apps/macos --filter RecordingStartAcceptanceTests`
  дал **1тест/7ошибок**,0.209s: прежний recovery создавал saved/ready с
  разрешением и убирал partial. Журнал `/tmp/graf-f277-acceptance-recovery-red.log`.
- Добавлены optional pending/accepted, начальный запрет без scopeApproval,
  синхронное принятие текущей сессии и сохранение признака при stop/recovery.
  Manifest пишет защищённый staging, синхронизирует/закрывает его до rename,
  после успешной замены не выполняет fallible шагов. Общий helper защиты
  других файлов не менялся. App сохраняет порядок recheck→markCapturing→accept
  без новой точки await.
- Первый набор8тестов прошёл0ошибок,0.085s,
  `/tmp/graf-f277-acceptance-core.log`, измерение commit0.000867958s.
- После добавления реального отказа rename через права собственного тестового
  каталога и отмены decision на MainActor во время настоящего startAsync:
  `swift test --package-path apps/macos --filter 'RecordingStartAcceptanceTests|DesktopNotificationAppIntegrationTests'`
  — **15PASS**,0пропусков,1.879s (10runtimeacceptance +5appintegration),
  `/tmp/graf-f277-acceptance-core10.log`, commit0.001320625s.
  Source-проверка порядка в executable app дополняет, не заменяет runtime
  отмены/диска/writer/recovery. Ни реальная встреча, ни сеть не использовались.
- Это промежуточный результат T024, не закрытие P1: отдельные отрицательные
  тесты queue/directclient и их исправление, общие регрессии и code review
  ещё выполняются. Установленный Dev не менялся.

- Queue/directclient RED: 8 новых исполняемых тестов успешно собраны;
  201 assertion failures (70 client, 131 queue), 0.707s.
  Команда `swift test --package-path apps/macos --filter 'DesktopUploadQueueTests/testStartAcceptance|DesktopUploadClientTests/testStartAcceptance'`,
  журнал `/tmp/graf-f277-acceptance-upload-red.log`. До этого запуска
  production queue/client не менялись. Имя класса очереди —
  `DesktopUploadQueueTests`, не имя файла `DesktopUploadQueueV5Tests.swift`;
  quickstart исправлен, чтобы исключить пустой запуск.
- Независимый code review T024 выявил C1: отложенная отмена встречи могла
  потеряться при повторной активности того же приложения. Проверка решения
  теперь использует общий `MeetingDetectionAppModule.allowsPendingStart`
  с реальным `pendingMeetingDetectionStopBundleID`; повторная активность
  не отменяет уже зарегистрированную остановку. Добавлен runtime сценарий
  stop→reactivation во время startAsync с ошибкой stop и новым recovery,
  плюс source wiring-проверка приложения. Результат повторного запуска
  и reviewer recheck будет записан отдельно; на этом этапе это не PASS.

### P1 — первый полный отрицательный/положительный набор после исправления

- `swift test --package-path apps/macos --filter 'RecordingStartAcceptanceTests|DesktopNotificationAppIntegrationTests|DesktopUploadQueueTests/testStartAcceptance|DesktopUploadClientTests/testStartAcceptance'`
  — **25PASS**,0ошибок/пропусков,2.330s. Журнал
  `/tmp/graf-f277-acceptance-green-first.log`: 12runtime core,5appintegration,
  8queue/client. Измерение commit0.000653375s. Ранее падавшие201assertions
  queue/client теперь проходят; это не пустой Swift Testing итог0tests.
- C1 повторно независимо проверен по коду: Approved,T024,0открытых дефектов,
  `scope-review.md`. Его новая последовательность stop→reactivation теперь
  также прошла runtime-проверку в указанном наборе.
- Различены строгий предзагрузочный reconcile и прежнее чтение серверного
  состояния уже известной записи после удаления локальных файлов. Внутренний
  `reconcileServerTruth` только GET; прямой upload по-прежнему самостоятельно
  проверяет локальный manifest, наличие server ID не снимает барьер.
  Независимая оценка подтвердила необходимость сохранить служебные пути;
  окончательное T025 review и регрессии ещё выполняются.
- Повторно на этом состоянии: retirement guard PASS0violations,
 51pytest PASS,37Node PASS. GRAF Dev только проверен через harness status:
  установлен, active manifest `dev-ee9533b28166`; build/promote ещё не выполнялись.

### P1 — заключительная проверка и сходимость реализации

- Первый расширенный прогон writer/recovery/capture/queue/client/deletion:
  193tests,1failure,22.612s (`/tmp/graf-f277-acceptance-domain.log`).
  Старый PurgeAcceptanceFixture записывал обычный текст вместо manifest;
  новый допуск верно отклонял его до ожидаемой приостановки mock upload.
  Только queued-ветка этого тестового пакета заменена реальным JSON с
  accepted, корректными метаданными дорожек, scope и permissions.
  Повреждённые пакеты отрицательных проверок очистки сохранены.
- Первая сборка обновлённого fixture отказала из-за пропущенных обязательных
  echoProcessor/echoProcessingHealth; параметры добавлены. Затем пара тестов
  удаления/серверного GET прошла. Дополнительное утверждение isComplete
  выявило незавершённый echoHealth в fixture: общий510 дал5SKIP/1FAIL,
  `/tmp/graf-f277-acceptance-full.log`. Исправлено на completed, не ослаблены
  утверждения или production gate. Focused purge+server GET:6PASS,
  `/tmp/graf-f277-acceptance-purge-green.log`.
- Окончательный общий запуск:
  `GRAF_CARD_SNAPSHOT_DIR=/tmp/graf-f277-acceptance-renders.VR6N1T swift test --package-path apps/macos --filter 'RecordingStartAcceptanceTests|DesktopUploadQueueTests|DesktopUploadClientTests|LocalRecordingWriter|CaptureRecovery|CaptureControlV5Tests|RecordingDeletion|DesktopNotification|DesktopLocalNotification|EmbeddedCabinetNotification|MeetingDetectionCountdownTests|MeetingDetectionPolicyTests|MeetingDetectionRecordingLifecycleTests|ShortRecording|AppControlAccessibility|DesktopCabinetRoutePolicy|DesktopCalendarReminderTests|CabinetSidebarRuntimeTests|DesktopCabinetWorkspaceTests'`
  — **510tests:505PASS,5SKIP,0FAIL**,37.991s,
  `/tmp/graf-f277-acceptance-full-green.log`. Очередь78, клиент49,
  принятие12, purge5, WebKit8. Пять пропусков прежнего настоящего AppKit focus
  не считаются приёмкой. Измерение commit0.000587417s.
- Свежие `swift build --package-path apps/macos --product TwoBrainRecApp`
  PASS1.63s; `--product ContractValidation` PASS0.21s и
  `apps/macos/.build/debug/ContractValidation` PASS.
  Журналы `/tmp/graf-f277-acceptance-app-build.log`,
  `/tmp/graf-f277-acceptance-contract-build.log`,
  `/tmp/graf-f277-acceptance-contract.log`. Прежние предупреждения WebKit
  остаются. Governance и whitespace checks PASS.
- Независимое ревью T025 одобрило scoped-перенос проверки/учёта попытки,
  строгий upload с известным meetingId, служебный GET без выдачи разрешения
  и отказ без фиктивных сетевых попыток; P1/P2 замечаний0. Последний новый
  runtime-тест отдельно проверяет GET без manifest с ownerScope, ожидаемые
  owner-заголовки и последующий отказ upload без второго запроса.
- Speckit-converge: checked28FR,8SC,15USacceptance,7architecture+8P1plan
  решений; принципы Конституции I–VII учтены в границах реализации.
  Missing/partial/contradicts/unrequested buildable findings0;
  CRITICAL/HIGH/MEDIUM/LOW0. Новых задач0; во время convergence tasks.md
  не менялся. Hooks before/after_converge отсутствуют. Ограничение
  установленного prerequisite `--require-spec` уже проверено; использованы
  поддерживаемые `--json --require-tasks --include-tasks` и прочитанный spec.
- T023–T026 завершены как локальная реализация/проверка P1. Это не закрытие
  #7336: PR и внешние проверки пока отсутствуют. T019–T022 и настоящая
  ручная матрица остаются отдельными условиями завершения F277.

### Установка единственного GRAF Dev и ограниченная ручная проверка

- Сохранён коммит `8e77ea82894c7f3aada9b9ebc694c14bb55a9901`, рабочее
  дерево чистое. Штатные harness build(feature277), promote dry-run,
  promote live, status и отдельный smoke live выполнены успешно.
  Активный manifest `dev-8e77ea82894c`; прежний — `dev-ee9533b28166`.
  Schema head не менялся. Все13проверок smoke PASS, включая подпись/идентичность,
  представление Dev, точный SHA, backend/frontend и worker readiness.
  Журналы `/tmp/graf-f277-dev-{build,promote-dry-run,promote,smoke}.log`.
  Production не использовался, отдельные приложения не создавались.
- Перед обновлением установленное приложение показывало «Готово к записи».
  После обновления через интерфейс открыты Настройки→Уведомления: видны
  пять локальных предпочтений и реальная кнопка проверки, системного запроса
  разрешения нет. Сохранённые настройки не менялись.
- Кнопка проверки показала настоящую карточку. Основное окно сохранило
  фокус на кнопке проверки. Команда приложения «Перейти к уведомлению»
  стала доступна только при наличии карточки; её выполнение перевело фокус
  на «Закрыть уведомление». AX определяет `graf-notification-card`, заголовок,
  пояснение и доступную кнопку закрытия. В снимке карточки тёмной темы нет
  обрезания; закрытие слева сверху вынесено из текстовой колонки.
- Escape закрыл карточку и вернул фокус на кнопку проверки в настройках.
  Это ручное подтверждение preview/focus/Escape в установленном приложении,
  не замена пяти пропущенных тестов или полной матрицы T020. VoiceOver,
  интерактивный вопрос записи, ввод в другом приложении, fullscreen и
  несколько физических экранов пока не объявляются проверенными.
- Повторный preview после явного перехода удержал фокус на закрытии не
  менее13секунд (наблюдения11:00:36→11:00:49UTC), то есть дольше обычных6секунд.
  Space активировал закрытие и вернул фокус к кнопке проверки. Это проверка
  реального удержания preview, не интерактивного8секундного вопроса.

### Телемост и ограниченная проверка с VoiceOver — 2026-09-27

- Пользователь подтвердил одиночную тестовую встречу без речи в Яндекс
  Телемосте. В установленном GRAF Dev наблюдались «Идет запись», источник
  Yandex Telemost и кнопка остановки. После явной остановки показана настоящая
  карточка «Запись не сохранена — короче 30 секунд»: одна строка, без обрезания,
  отдельной колонки закрытия нет. Команда «Перейти к уведомлению» перевела
  фокус на доступную кнопку закрытия слева сверху.
- В этот же момент свёрнутая панель показывала «Сохранено на Mac», что
  противоречит карточке короткой записи. Это наблюдаемая несогласованность,
  не подтверждение фактического сохранения. Файлы записи не исследовались.
- После выхода пользователя была создана новая одиночная тестовая встреча,
  без приглашений. VoiceOver через Системные настройки временно переключён
  off→on. У настоящего вопроса записи AX показал заголовок, обратный отсчёт
  (наблюдались оставшиеся4секунды), checkbox off с названием приложения,
  «Не записывать», «Записать» и доступную кнопку закрытия. Снимок карточки
  подтвердил отсутствие обрезания и положение крестика слева сверху.
- После Escape карточка исчезла, однако затем интерфейс показал
  `render_reference_missing`, «Уже очищенная часть сохранена локально» и
  одновременно «Локальная запись не сохранена». Порядок истечения8секунд,
  начала/ошибки записи и Escape не установлен; отмена до запуска не объявлена
  PASS. Исходник RecordingAudioTimeline.emitAvailableFrames связывает этот
  код с отсутствием покрытия системным звуком нужного интервала для
  подавления эха; причина отсутствия покрытия на данном Mac не установлена.
  Нельзя считать молчание пользователя доказанной причиной ошибки.
- Озвучивание не прослушано инструментом; наличие AX-элементов при включённом
  VoiceOver не доказывает однократное объявление/отсутствие повторов отсчёта.
  Checkbox Space, обе кнопки, first-click и сохранение выбора остаются
  непроверенными вручную. Снимки камеры, ссылки, звук и содержимое встреч
  в evidence не сохранены.
- Тестовая встреча завершена через Телемост. В GRAF видна кнопка начала,
  не остановки; правило Yandex Telemost осталось «Спрашивать». VoiceOver
  восстановлен on→off с проверкой переключателя. Код/установка/постоянные
  правила записи не менялись. T020 остаётся незавершённой; это частичная
  ручная проверка, не полная приёмка или release gate.

## Phase 9 — правдивый результат записи, 2026-09-27

Режим: high-risk-product F277, продолжение полного Spec Kit, задачи
T027/T028, владелец [#7337](https://github.com/yshishenya/graf/issues/7337).
После дополнения задач выполнен analyze в сессии: 28 FR / 8 SC / 28 задач,
нет неразрешённых CRITICAL/HIGH противоречий требований; issue sync завершён,
обязательная проверка canon прошла для выбранных 300 issues.
Независимый допуск требований: 26/26, см. scope-review.md. Это не приёмка кода.

- T027: `.stopped/.finalized` показывают «Запись остановлена», нейтральные
  цвет/значок, а не обещание сохранения. Подтверждённый локальный статус
  сохранения остаётся отдельным видимым результатом. Уведомление короткой
  записи и его история не удалены. Контроллер/manifest не менялись.
- T028: `.failed` отображается как «Запись завершилась с ошибкой» с признаком
  предупреждения. Форматирование вынесено в существующий SystemAudioStatusLabels.
  Утверждение о фрагменте по-прежнему требует совпадения sessionId и успешного
  localPlaybackURL. Два синтетических примера очереди проверяют наличие
  доступного фрагмента и отсутствие аудио; правила playback/upload не менялись.
- Начальный RED T027: 61 тест, 10 отказавших утверждений
  (`/tmp/graf-f277-outcome-red.log`). В числе отказов также обнаружена старая
  проверка `elapsed < 8`: теперь проверяются обновление remainingSeconds и
  onExpire, поведение срока проверяют runtime-тесты. Новое ожидание AX
  уточнено до нейтрального текста без добавления несуществующего суффикса.
- RED T028: 68 тестов, 3 отказавших утверждения — непризнанное предупреждение
  и старый mapping приложения (`/tmp/graf-f277-failure-red.log`).
  Проверки новых чистых функций/стиля и двух файловых примеров добавлены затем;
  для них отдельный RED не заявляется.
- Профильный GREEN: `swift test --package-path apps/macos --filter
  'CaptureIndicatorTests|CaptureControlTests|ShortRecordingNoticeTests|DesktopNotificationAppIntegrationTests|DesktopUploadQueueTests/testV5CaptureFailure'`
  — 72 PASS, 0 SKIP/FAIL, 1.922s (`/tmp/graf-f277-outcome-focused.log`).
  CaptureControlTests 49, CaptureIndicatorTests 14, app wiring 6,
  queue 2, short notice 1. Source-wiring не заменяет установленное приложение.
- Исправлена команда quickstart: класс в CaptureControlV5Tests.swift называется
  CaptureControlTests. Прежний фильтр по имени файла не выбирал этот класс;
  исторический результат 510 не является доказательством его прохождения.
- Новый общий запуск: прежний объединённый фильтр плюс правильный
  CaptureControlTests и CaptureIndicatorTests — 574 теста, 1 SKIP, 11 отказов
  утверждений в 6 тестах, 38.347s (`/tmp/graf-f277-outcome-full.log`). Одна
  source-проверка AppControlAccessibilityTests ещё требовала checkmark;
  обновлена на stop.circle и запрет галочки. Пять других тестов не смогли
  установить/восстановить inactive состояние независимого AppKit test host
  до проверки карточки. Это не PASS и не доказанная ошибка продукта.
  Экспорт картинок не запрашивался — один явный SKIP снимков.
- Изолированная повторная проверка AppControlAccessibilityTests,
  DesktopNotificationAccessibilityTests и DesktopNotificationPromptLifecycleTests:
  56 тестов, 10 отказов утверждений в тех же 5 тестах фокуса, 13.607s
  (`/tmp/graf-f277-outcome-focus-recheck.log`). Все24 AppControlAccessibilityTests
  прошли. Проверки фокуса не ослаблены; полная приёмка T019/T020 открыта.
- Сборки TwoBrainRecApp и ContractValidation, запуск ContractValidation,
  notification-retirement (0 нарушений), governance и git diff --check — PASS.
  Журналы `/tmp/graf-f277-outcome-app-build.log`,
  `/tmp/graf-f277-outcome-contract-build.log`, `/tmp/graf-f277-outcome-contract.log`.
- Независимый просмотр кода T027/T028 не выявил замечаний в проверенной
  области; отдельно проверены реальные места использования, терминальные
  цвет/значок и неизменность проверки фрагмента. Проверяющий не запускал тесты.
  Причина render_reference_missing не исправлялась: аудиодвижок вне Phase 9.

Установленный GRAF Dev на момент этих проверок остаётся dev-8e77ea82894c.
Новые исходники ещё не проверены в установленном приложении. Никакие issues,
ручные/PR gates, выпуск или общая цель этими результатами не закрываются.

Финальный профильный запуск после исправления source-проверки: предыдущий
72-тестовый фильтр плюс `AppControlAccessibilityTests` — **96 PASS, 0 SKIP/FAIL**,
2.017s (`/tmp/graf-f277-outcome-final-focused.log`). Общий574 от этого не
становится успешным. Независимая диагностика пяти отказов: первый не может
вернуть неактивное состояние после обычного пробного окна, четыре следующих
не могут установить его до пробы; все останавливаются до presenter.
Двойной учёт вызван `XCTFail` и последующим собственным `CocoaError(1570)`
helper, а не дополнительной доказанной ошибкой данных продукта.

Повторная независимая сверка текущего кода по speckit-converge:
28/28 FR, 8/8 SC, 15/15 сценариев US, 7 архитектурных + 8 решений P1,
ограничения Конституции I–VII. Новых buildable findings 0 во всех категориях
и уровнях; CV1/CV2 устранены. Новых задач не добавлено. T027/T028 отмечены
по реализованному и проверенному исправлению; незавершённые T019–T022 и
прежние ручные условия не закрыты. Проверяющий не запускал тесты/приложение.

## Возобновление ручной проверки после разрешения переключать окна — 2026-09-27

- Пользователь разрешил переключать окна. До обновления проверено через UI:
  в GRAF Dev доступна команда начала записи, активного Stop нет. Рабочая
  копия чистая, HEAD `49766da1f17c4bd157a44320dfc3996b52697194`.
- Штатный `dev-harness.sh promote --manifest …/manifests/dev-49766da1f17c.json
  --live` завершился успешно. `status --json` подтвердил active exact SHA,
  `/Applications/GRAF Dev.app`, установленное приложение. Отдельный
  `dev-harness.sh smoke --json --live`: все13 проверок PASS. Журналы
  `/tmp/graf-f277-resume-promote.log`, `/tmp/graf-f277-resume-smoke.json`.
  Bundle ID, подпись, разрешения и production не менялись.
- В установленном приложении через настройки показана настоящая проверочная
  карточка. Снимок подтвердил небольшой крестик слева сверху вне текстовой
  колонки, читаемые две строки без обрезания. Явная команда меню «Перейти к
  уведомлению» передала фокус кнопке «Закрыть уведомление». Tab оставил фокус
  на единственной кнопке; Escape закрыл карточку и вернул основное окно.
  Это проверка preview, не матрица интерактивного вопроса/VoiceOver/first-click.
- По test-triage сначала выполнен один тест в свежем процессе:
  `swift test --package-path apps/macos --skip-build --filter
  'DesktopNotificationAccessibilityTests/testExplicitFocusAndKeyLoopReachCloseCheckboxAndActions'`.
  Результат 1 SKIP, 0 FAIL, 2.139s: независимое обычное окно не получило
  настоящий focus. Причина внешнего отказа активации не доказана; это не PASS
  карточки. Журнал `/tmp/graf-f277-resume-focus-single.log`.
- Затем общий объединённый фильтр Phase9 (с правильными CaptureControlTests
  и CaptureIndicatorTests) с
  `GRAF_CARD_SNAPSHOT_DIR=/tmp/graf-f277-resume-renders.1hRKs2`:
  **574 теста, 569 PASS, 5 SKIP, 0 FAIL**,40.315s.
  `/tmp/graf-f277-resume-full.log`. Пять SKIP — три Accessibility и два
  PromptLifecycle с отказом независимой пробы focus. Проверки не ослаблялись.
  Созданы20 синтетических снимков: 5 сценариев × 2 темы × 2 размера текста.
  Просмотрены short/light/standard и prompt/dark/large, без обрезания текста,
  флажка и кнопок. Не заявляется просмотр всех20 или установленная матрица.
- Пользователь отдельно разрешил создать пустую встречу в Телемосте без
  приглашений. Приложение открылось, но осталось на «Загрузка / Подключиться»
  с повторными попытками. Явная попытка подключения не помогла. Встреча не
  создана, запись не запускалась, сетевые/VPN-настройки не менялись.
- Дополнительное наблюдение, пока без установленной причины: AX описывает
  reminders/showTitles/sound как on, а снимок страницы показывает серые
  переключатели слева; quiet off совпадает. После обновления страницы
  расхождение осталось. Настройки не переключались. Это требует отдельной
  проверки отображения/AX-инструмента, а не заявления о подтверждённом
  дефекте сохранения. Меню GRAF позже дважды вернуло timeout инструмента;
  первоначальный успешный переход к карточке этим не отменяется.

Ручная приёмка и PR gates остаются открытыми. Полного VoiceOver-озвучивания,
матрицы start/skip/close/timeout и проверки двух физических экранов этот
прогон не подтверждает. Новых аудио, ссылок встреч или частного содержимого
в репозиторий не записано.

Независимый read-only разбор расхождения переключателей: JS присваивает
булево `.checked`, CSS использует `:checked`, а не исходный HTML-атрибут;
прямая причина в исходнике не установлена. Выявлена граница тестов:
EmbeddedCabinetNotificationSettingsBridgeTests проверяют упрощённые checkbox
без настоящего switch-макроса/дорожки/CSS; Chromium проверяет размеры, но
не соответствие цвета/сдвига состоянию. Поэтому прежний WebKit/Chromium PASS
не доказывает согласованность именно этого отображения. Следующая проверка:
в одном живом документе сопоставить `.checked`, `matches(':checked')`,
вычисленный стиль дорожки/ползунка, свежий AX и снимок, не меняя настройки.
Поздняя попытка щелчка по заголовку GRAF вернула `noWindowsAvailable`,
хотя инвентарь приложения и AX оставались доступны; достоверность этих
поздних снимков как живой отрисовки отдельно не подтверждена.
