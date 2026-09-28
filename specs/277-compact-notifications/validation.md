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

## Повторные попытки Телемоста и дополнительная проверка — 2026-09-27

Исходники: чистый HEAD `6d1d5ce7574ef4178ed31a57eb4bca96aa4ade1b`;
продуктовый код остаётся `49766da1f17c4bd157a44320dfc3996b52697194`.
В этом продолжении приложение не пересобиралось и не переустанавливалось.

- Главный экран Телемоста загрузился; пользователь ранее разрешил пустые
  тестовые встречи без приглашений. Сделаны три попытки нового вызова.
  На просмотренных снимках Телемост оставался на «Идёт подключение»;
  камера и микрофон в нём выключались. Ссылки никому не отправлялись.
- В двух последних попытках через UI замечено начало записи GRAF. Каждая
  остановлена штатной кнопкой; наблюдались «Запись остановлена» и доступный
  Start вместо Stop. Выход из вызовов подтверждён возвратом главного экрана
  Телемоста. Правило Yandex Telemost прочитано как «Спрашивать», не менялось.
  По этим наблюдениям нельзя заключить, что во время первой попытки запись
  не начиналась, или что тестовые данные не сохранялись.
- Узкая выборка технического журнала по событиям Telemost уточнила причину:
  `prompt_presented` в 18:59:15, 19:00:35 и 19:01:51 UTC; в каждом случае
  через 9 секунд по округлённым меткам — `prompt_accepted`,
  `autoRecordOptIn=false`, `reason=prompt_timeout`, затем `prompt_dismissed`.
  Это свидетельствует об истечении прежнего восьмисекундного предложения,
  а не о нажатии кнопки. Журнал читается только по разрешённому набору полей;
  его полный текст и содержимое встреч не копировались в evidence.
- Значение `result=accepted` у `consumer_outcome` при показе относится к
  обработке события детектором, не к явному согласию пользователя. Наличие
  `prompt_presented` не доказывает доступность карточки для физического щелчка,
  её положение на экране или VoiceOver. Матрица решений этим не закрыта.
- Независимое чтение подтверждает: отказ без флажка сохраняет Ask, но помечает
  текущую встречу обработанной; повторное предложение требует окончания всех
  источников и 15 секунд непрерывной неактивности. Добавлена воспроизводимая
  последовательность в quickstart. Пользователю предложено самому нажать
  «Не записывать» без флажка; до ответа агент не переключает окна. Результат
  этого отдельного испытания пока не получен и не считается PASS.

Дополнительные проверки, не вмешивающиеся в ручной тест:

- `python3 scripts/check_notification_retirement.py`: PASS, 0 нарушений.
- `apps/server/.venv/bin/python -m pytest -q -o addopts=
  apps/server/tests/contract/test_desktop_notification_retirement.py`:
  51 PASS, 1.73s; два прежних предупреждения pytest/Starlette.
- `node apps/server/tests/browser/settings-consistency.test.cjs
  --notification-contract`: 37 PASS, 0 SKIP/FAIL, 60.382ms. Это проверки
  контракта JavaScript, не живой отрисовки переключателей WebKit.
- Просмотрены все 20 ранее экспортированных синтетических снимков из
  `/tmp/graf-f277-resume-renders.1hRKs2`: meeting/prompt/problem/short/preview
  × light/dark × standard/large. Экспорт выполнен настоящими AppKit views
  через `testCardSurfacesCanBeCapturedForReferenceComparison` с масштабами
  шрифта 1 и 1.6.
  На этих снимках текст, флажок и действия не обрезаны и не пересекаются;
  короткое стандартное сообщение однострочное без пустых строк действий;
  при увеличении текста высота растёт и строки переносятся. Закрытие слева
  сверху не резервирует отдельную колонку. У календарной карточки длинные
  действия расположены вертикально. Проверка этих изображений не является
  установленной ручной матрицей, проверкой двух экранов или озвучивания.

T019–T022, ручные условия и PR-проверки остаются открытыми. Изменение только
документации проверки: `docs-only / mechanical` внутри активного среза
`high-risk-product`; продуктовый код и требования не менялись.

### Дополнительная очистка T029 — в работе

После указанной выше проверки независимое чтение цепочек Notifications
выявило недостижимый `.joinAndRecord` внутри обработчика `.recordingPrompt`.
Карточка вопроса не выдаёт такое действие; календарный обработчик использует
его отдельно и остаётся необходимым. Другой канал доставки в проверенных
цепочках не найден. Подтверждены рабочие вызовы retirement при создании shared
presenter, запасной экран настроек через тот же presenter, история и команда
фокуса; это не основание объявлять проверенным весь код приложения.

В Phase 10 добавлена T029 (FR-021/SC-006, partial/LOW), без изменения прежних
задач и требований. Анализ spec/plan/tasks: 29 задач, 28 FR, 8 SC, 15 AC;
непокрытых требований/сценариев и новых CRITICAL/HIGH — 0. Независимый допуск
требований 26/26 записан проверяющим в scope-review.md. Поиск существующих
issues по feature:277 и task ID не нашёл владельца T029; прежние 28 задач
сохраняют 24 открытых владельца. Создана #7338, связь добавлена в tasks.md.
Обязательные ensure/validate issue-canon выполнены; validate: 300 задач
проверено, PASS. Никто не закрыт.

После допуска в исходнике удалён только этот один case из ветки вопроса;
`.record`, `.skipRecordingPrompt` и календарный `.joinAndRecord` сохранены.
Проверка удаления: 0 нарушений; governance и git diff --check — PASS.
**Сборка и профильные AppKit-тесты после этой правки ещё не выполнены**:
пользователь приглашён выполнить ручной тест, агент не запускает конкурирующие
окна и не обновляет установленный GRAF Dev. T029 остаётся `[ ]`, исправление
ещё не считается проверенным или установленным. Прежние результаты 51/37
и снимки предшествуют правке и не выдаются за её runtime-проверку.
Независимое ревью точного однострочного diff не выявило замечаний: сохраняются
Start/Skip/remember/token/deadline и все календарные действия. Проверяющий
не выполнял тесты/сборку; ожидание проверки выполнением остаётся.

### Проверка сборки T029 без вмешательства в ручное испытание — 2026-09-27

На HEAD `9eb9d8ac7fcbbd5c4cddb329a06b07e2d4f3be3f` с указанной выше
однострочной правкой T029 повторно выполнена компиляция без запуска GUI:

- `swift build --package-path apps/macos --product TwoBrainRecApp` — PASS,
  1.98s. Компилятор сообщил предупреждения о неэффективном
  `@preconcurrency` у существующих соответствий протоколам WebKit.
- `swift build --package-path apps/macos --product ContractValidation` —
  PASS, 0.98s.
- `apps/macos/.build/debug/ContractValidation` — PASS. Это консольная
  проверка контрактов с подставными реализациями захвата, не запуск приложения
  и не доказательство поведения кнопок установленной карточки.
- `python3 scripts/check_notification_retirement.py` — PASS, 0 нарушений;
  `git diff --check` — PASS.

Предыдущая сессия сборки больше не была доступна для получения результата;
перед повторной проверкой работающих процессов компилятора не обнаружено.
Приведённые результаты относятся к новому завершённому запуску, не к
предположению о результате утраченной сессии.

Окна не переключались, AppKit-тесты не запускались, установленный GRAF Dev
не обновлялся. В узкой выборке журнала по Телемосту новых событий после
19:02:00 UTC не обнаружено; ручное нажатие «Не записывать» не подтверждено.
Профильные AppKit-тесты T029 и ручные условия остаются открытыми.

### Повторная проверка отказа в Телемосте и T029 — 2026-09-27

Пользователь вновь разрешил агенту управлять окнами. Harness status подтвердил
установленный `/Applications/GRAF Dev.app`, активный `dev-49766da1f17c`.
Приложение не обновлялось. Созданы два пустых тестовых звонка без приглашений.

- Первая попытка: `prompt_presented` 19:25:05 UTC → `prompt_accepted`
  19:25:11, `reason=prompt_button`, `autoRecordOptIn=false`. Пользователь
  отдельно подтвердил случайное нажатие «Записать». В UI затем показаны
  остановка с `render_reference_missing`, доступная кнопка начала записи и
  частично сохранённая локальная запись. Эта попытка не доказывает отказ.
- Повторная попытка: `prompt_presented` 19:26:33 UTC. После команды
  Cmd+Option+N дерево доступности показало отдельную карточку с оставшимися
  шестью секундами, «Не записывать», закрытием и выключенным флажком
  «Запомнить выбор для Yandex Telemost». Агент направил действие на найденную
  кнопку отказа. Инструмент также выдал предупреждение об изменении окна;
  один только ответ инструмента не считается доказательством щелчка.
- Независимая проверка журнала: в 19:26:36 — `consumer_outcome`,
  `result=rejected`, `reason=user_skipped`, `retryable=false`, затем
  `prompt_dismissed`. До выхода из вызова, существенно позже восьмисекундного
  срока, нового `prompt_accepted` не появилось; UI показывал «Начать запись»
  и «Встреча обнаружена». Правило Yandex Telemost в настройках прочитано как
  «Спрашивать»; настройки не менялись. Выход подтверждён главным экраном
  Телемоста с «Новый звонок».
- Это подтверждает установленный путь отказа без сохранения выбора и без
  позднего принятия по таймеру. Использовались явная команда фокуса и действие
  через дерево доступности: физический первый щелчок по неактивной карточке
  и фактическое озвучивание VoiceOver этим не доказаны.

После завершения звонков на текущем исходнике с правкой T029 выполнено:

`swift test --package-path apps/macos --filter
'DesktopNotificationCardTests|DesktopNotificationPromptLifecycleTests|DesktopLocalNotificationDeliveryTests'`

Результат: 61 тест, 58 PASS, 1 SKIP, 2 FAILED (4 сообщения об ошибках),
6.185s, exit 1. Delivery: 32 PASS; Card: 13 PASS и 1 SKIP; Lifecycle:
13 PASS и 2 FAILED. Экспорт снимков пропущен, поскольку
`GRAF_CARD_SNAPSHOT_DIR` не задан. Журнал: `/tmp/graf-f277-t029-focused.log`.

Оба сбоя возникли в `F277CardTestSupport.requireFocusHost` до проверки
карточки: не удалось восстановить неактивность после обычного окна-пробы,
затем не удалось установить исходное неактивное состояние. Упавшие тесты:
`testKeyFocusHoldAndHoverOverlapResumeOnlyAfterBothEnd` и
`testPromptAndMeetingDeadlinesIgnoreHoverAndKeyFocus`.
Их отдельный повтор в новом процессе через тот же `swift test --filter`
с двумя полными именами класса/метода воспроизвёл оба сбоя: 2 FAILED,
4 сообщения об ошибках, 4.212s, exit 1. Журнал:
`/tmp/graf-f277-t029-focus-recheck.log`.

Сбои подготовки среды не доказывают дефект карточки, но и не являются PASS.
Код проверки не ослаблялся. T029 и общая приёмка остаются открытыми до
разрешения проверки фокуса; ручной отказ не заменяет остальные условия.

### T019: проверка и исправление подготовки фокуса — 2026-09-27

Lane: существующий `high-risk-product` срез, тестовая регрессия T019
(открытая #7303), не новое поведение продукта. Независимый reviewer подтвердил
26/26 требований и актуальный analyze для 29 задач; дополнительные требования
или задачи не понадобились. Реализация затрагивает только подготовку AppKit
в `DesktopNotificationCompactTests.swift` и более строгие предусловия в
`DesktopNotificationAccessibilityTests.swift`. Установленное приложение,
продуктовые сроки, правила записи и обработчик фокуса не менялись.

Первый эксперимент перенёс три `deactivate()` в `perform` существующего
цикла AppKit. Три проверки дали 2 PASS / 1 FAILED (5.053s); одиночный
повтор оставшегося теста дал PASS (1.754s). Это не полное исправление:
сбой подготовки зависел от состояния процесса. Журналы:
`/tmp/graf-f277-focus-loop-probe.log`, `/tmp/graf-f277-focus-loop-single.log`.

Окончательный кандидат использует подготовку собственного тестового процесса
до показа карточки: `hide` → наблюдаемое `!isActive && isHidden` →
`unhideWithoutActivation` → наблюдаемое `!isActive && !isHidden`.
Обе операции выполняются в цикле событий; при ошибке скрытое состояние
снимается без активации, FAIL сохраняется. Не запускаются и не выбираются
чужие приложения; macOS сама может передать фокус при скрытии тестового
процесса. Обычное контрольное окно убирается до повторной подготовки.
Непосредственно перед `presenter.focus()` усилены проверки: приложение
неактивно и не скрыто, карточка видима и не key. Нет новых skips, увеличения
сроков, подставных уведомлений активации или принудительного успеха карточки.

Основание: Apple рекомендует заменять прямой `deactivate` и указывает, что
скрытие подразумевает деактивацию; `unhideWithoutActivation` восстанавливает
окна без активации владельца:
[cooperative activation](https://developer.apple.com/documentation/appkit/passing-control-from-one-app-to-another-with-cooperative-activation),
[unhideWithoutActivation](https://developer.apple.com/documentation/appkit/nsapplication/unhidewithoutactivation()).

- Пять зависимых от фокуса тестов вместе: 5 PASS, 0 SKIP/FAIL, 1.317s.
  `/tmp/graf-f277-focus-hide-probe.log`.
- Отрицательный контроль: только в тесте explicitInactive временно заменены
  `requestActivation` и `requestKeyWindow` на no-op. Первый отдельный запуск
  пропущен независимой пробой обычного окна (1 SKIP, 2.168s), поэтому не
  доказал чувствительность. Второй запуск включал обычный положительный
  тест фокуса: он прошёл, изменённый тест упал на пяти проверках реального
  результата (active/key/first responder), не на подготовке. 1 PASS,
  1 FAILED, 0 SKIP, 3.780s. Журналы:
  `/tmp/graf-f277-focus-negative-control.log` и
  `/tmp/graf-f277-focus-negative-calibrated.log`. Временная подмена удалена;
  восстановлен исходный `F277CardFixture().presenter()`.
- Card + Delivery с включённым экспортом синтетических снимков: 46 PASS,
  0 SKIP/FAIL, 1.545s; `/tmp/graf-f277-t029-card-delivery.log`. Это отдельный
  объём проверки, не замена не прошедшим ранее фокусным сценариям.

Итоговый общий запуск после удаления временной подмены:

```sh
notification_render_dir=$(mktemp -d /tmp/graf-f277-final-renders.XXXXXX)
GRAF_CARD_SNAPSHOT_DIR="$notification_render_dir" swift test --package-path apps/macos --filter 'RecordingStartAcceptanceTests|DesktopUploadQueueTests|DesktopUploadClientTests|LocalRecordingWriter|CaptureRecovery|CaptureControlTests|CaptureIndicatorTests|RecordingDeletion|DesktopNotification|DesktopLocalNotification|EmbeddedCabinetNotification|MeetingDetectionCountdownTests|MeetingDetectionPolicyTests|MeetingDetectionRecordingLifecycleTests|ShortRecording|AppControlAccessibility|DesktopCabinetRoutePolicy|DesktopCalendarReminderTests|CabinetSidebarRuntimeTests|DesktopCabinetWorkspaceTests'
```

**574 PASS, 0 SKIP, 0 FAIL**, 30.455s, exit 0. Число строк `Test Case ...
passed` дополнительно сверено: 574; строк skipped/error/failed нет.
Журнал `/tmp/graf-f277-final-regression.log`. Измерение подтверждения запуска:
0.000569708s, ниже целевых 100ms на этом синтетическом запуске.

Независимое ревью точного изменения двух тестовых файлов — без замечаний.
Проверяющий подтвердил наблюдение состояния, сохранённые проверки actual
active/key/first responder, отсутствие новых skips и удаление временной
подмены. Ограничение: аварийный defer снимает скрытие без ожидания завершения,
но исходная ошибка при этом остаётся FAIL. Сам общий запуск выполнил MAIN.
Retirement guard: PASS, 0 нарушений; governance: OK; git diff --check: PASS.

T029 отмечена выполненной локально: её исходник, сборки, профильные проверки
в общем наборе и независимое ревью подтверждены. #7338 остаётся открытой до
PR-подтверждения. T019/T020/T021/T022 целиком не закрыты: оставшиеся проверки
quickstart, ручные условия и exact-SHA/base PR gates не заменяются этим
нативным набором. Новая установка GRAF Dev и выпуск не выполнялись.

### T019/T020 — повтор настроек на 27bab9 и незакрытое визуальное расхождение

2026-09-27 основной агент повторил проверки на чистом
`27bab9dfd953cbbdce24f5f5dceb6d0f6eb25c20`. Это продолжение активной
high-risk-product F277; данный шаг меняет только документ с результатами,
не поведение продукта. Основная рабочая копия с подготовкой выпуска не затронута.

| Команда из корня F277 | Результат |
|---|---|
| `infra/scripts/ci-local.sh --plan` | Чистая рабочая копия; cabinet-shell/settings; частичный диагностический набор, не PR receipt |
| `node apps/server/tests/browser/settings-consistency.test.cjs --notification-contract` | 37 PASS, 0 FAIL/SKIP, 70.48225ms |
| `apps/server/.venv/bin/python -m pytest -q -o addopts= apps/server/tests/contract/test_desktop_notification_retirement.py` | 51 PASS, 1.80s |
| `infra/scripts/ci-local.sh --focused` | 112 PASS, 2.85s тестов, 6.65s всего; coverage partial |
| `bash apps/server/scripts/run_local_postgres_tests.sh --focused -q tests/integration/test_settings_ia_flow.py` | 7 PASS, 8.42s; отдельный тестовый контейнер PostgreSQL удалён штатным runner |

В трёх Python-наборах по два известных предупреждения о повторном импорте
pytest fixture и устаревающей интеграции Starlette/httpx; ошибок нет.
Журналы: `/tmp/graf-f277-27bab9-node.log`,
`/tmp/graf-f277-27bab9-retirement.log`,
`/tmp/graf-f277-27bab9-ci-focused.log`,
`/tmp/graf-f277-27bab9-settings-ia.log`.

Полный существующий `settings-combobox.test.cjs` повторён отдельно в Chromium
и WebKit: оба PASS, exit 0. Команды:

```sh
NODE_PATH=/Users/yshishenya/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules node apps/server/tests/browser/settings-combobox.test.cjs
NODE_PATH=/Users/yshishenya/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules BROWSER=webkit node apps/server/tests/browser/settings-combobox.test.cjs
```

Журналы `/tmp/graf-f277-27bab9-combobox-chromium.log` и
`/tmp/graf-f277-27bab9-combobox-webkit.log`. Browser plugin not available:
использованы существующие зависимости и браузерные проверки проекта, без
новых установок. Это синтетические страницы, не установленный WKWebView.

**T020 остаётся незакрытой.** В установленном `/Applications/GRAF Dev.app`
(активный manifest `dev-49766da1f17c`, не новый HEAD) страница
`/desktop/settings/notifications` показывает три локальных переключателя
серым цветом с ползунком слева, тогда как AX одновременно сообщает `on`
для «Напоминать о встречах», «Показывать названия встреч» и «Звук уведомлений».
«Тихий режим» передаёт `off` и выглядит выключенным. Серверные переключатели
писем/подсказок передают `on` и выглядят включёнными. Расхождение повторено
после сворачивания правой панели, штатного обновления страницы и прокрутки;
прокрутка действительно меняет снимок. Настройки пользователя не менялись.
Запись в интерфейсе остановлена. Этот результат не доказывает причину
несоответствия и не заменяет проверку DOM/computed styles в живом WKWebView.

Дополнительный временный пробник вне репозитория
`/tmp/graf-f277-switch-render.lbg8bj/probe.cjs` загрузил реальный Jinja-макрос
и локальный фрагмент страницы, полный `cabinet.css`, `settings-autosave.js`
и `cabinet.js`. Все сетевые запросы блокируются; bridge и аккаунт синтетические.
На 800×600 в Chromium и WebKit подтверждены:

- исходные три `checked=true`, `:checked=true`, включённые поля;
- фон включённого переключателя `rgb(112, 86, 233)`, сдвиг ползунка 16px;
- тихий режим исходно выключен; нажатие включает состояние и оформление;
- начальный `data-state="normal"` строки не мешает оформлению `:checked`;
- только ожидаемые bridge-действия `read` и `set`, ошибок страницы/консоли нет.

Основной агент просмотрел `webkit-initial.png`: три фиолетовых переключателя
с ползунком справа и один серый слева соответствуют вычисленным стилям.
Пробник не воспроизводит целый документ и установленный WebKit, поэтому не
опровергает живое наблюдение. Никакая правка CSS по предположению не внесена.

Read-only GET трёх общедоступных ресурсов локального сервера вернул HTTP 200;
содержимое каждого побайтно совпало с HEAD и установленным SHA49766da1f17c:
`cabinet.css` — `240833d27260`, `cabinet.js` — `cedf5121437a`,
`settings-autosave.js` — `6175466793e8` (первые12 знаков SHA256).
Это проверка ответов сервера, не содержимого кэша живого WKWebView.
GET страницы без сессии возвращает 303; сессия не извлекалась, обход авторизации
не выполнялся. Независимый read-only аудит не нашёл подтверждённой причины;
рекомендуется сопоставить `.checked`, `:checked`, вычисленные стили, AX и
изображение именно в одном живом документе. T013/T019/T020 и итоговая визуальная
приёмка не закрываются по зелёным синтетическим проверкам.

### T019 — системный WebKit: приостановленный переход в скрытом документе

2026-09-27, исходники `34c4650b4`. Предыдущий проход классифицирован как
progress: завершены дополнительные проверки и зафиксировано новое наблюдение.
Рабочая копия чистая; применимые контрольные списки повторно проверены:
requirements 5/5, UX 10/10, security 8/8, audio-capture 8/8. Независимый
reviewer подтвердил применимость существующей T019 и analyze29tasks; #7303
по read-only GitHub-запросу OPEN. До/после implement нет включённых hooks.

Вместо изменения продукта основной агент запустил временный автоматический
пробник `/tmp/graf-f277-system-webkit.4fpMwi/probe.swift`. Он компилируется
`swiftc -parse-as-library` вне репозитория, создаёт WKWebView без NSWindow,
с `.nonPersistent()` и политикой тестового процесса `.prohibited`; отдельный
пакет приложения не создаётся, пользовательский GRAF не заменяется. Jinja
рендерит текущий локальный фрагмент страницы и настоящий макрос; CSS/JS
читаются из текущего worktree. Ответы даёт искусственный
WKScriptMessageHandlerWithReply, не продуктовый bridge. Поэтому этот опыт
не проверяет его защитные границы и не заменяет существующие XCTest.
Данные синтетические, baseURL `https://graf.invalid`, внешние ресурсы в
загружаемом документе отсутствуют. Документ не использует реальную сессию.

Обычный запуск дождался настроек, но не дождался конечного положения
ползунков за 100×50ms. Первый вариант завершился exit133 из-за необработанной
ошибки **самого временного пробника**, не падения GRAF. После добавления
обработки ошибок и диагностического вывода повтор дал exit1 и следующие
одновременные значения (`result-2.log`):

- `document.visibilityState == "hidden"`;
- у трёх переключателей `checked == true` и `matches(':checked') == true`;
- фон всё ещё `rgb(48, 52, 60)`, сдвиг ползунка 0px;
- 21 CSS-переход имеет `playState == "running"`, `currentTime == 0`.

Причинный контроль только в том же искусственном документе:
`probe --finish-animations` завершил CSS-переходы через Web Animations API,
не меняя значения переключателей. Все три фона стали `rgb(112, 86, 233)`,
сдвиг —16px; синтетическое нажатие quiet и сохранение также дали верные
значение/оформление. Bridge вызван только с `read` и `set`.
`animation-control.log`, exit0. Его строка `SYSTEM_WEBKIT_PROBE_PASS`
означает успех **этого контрольного опыта**, не исправление продукта или
ручную приёмку: анимации были принудительно завершены только в пробнике.
Продуктовые CSS/JS и настройки не изменены.

Это подтверждает механизм расхождения в скрытом WKWebView, но пока не
устанавливает причину наблюдения в установленном GRAF. Независимый просмотр
нашёл допустимое обновление настроек до/вне видимости документа; постоянного
скрытия WebView в коде не обнаружил. Неактивность приложения не тождественна
`visibilityState=hidden`. Повторное открытие через Finder также не доказывает
активацию: `applicationShouldHandleReopen` при `hasVisibleWindows=true`
не вызывает `presentMainWindow`.

В живом GRAF повторены команды меню «Настройки…» → «Уведомления» без
изменения настроек; журнал подтверждает повторный показ существующего окна
20:00:49Z, `visible=true`, но это не доказывает видимость документа и ход
его анимаций. Снимок через инструмент всё ещё серый при AX-on. Пользователю
задан неблокирующий вопрос о виде переключателей в переднем окне; ответа
на момент записи нет. Нужны наблюдение переднего окна или значения
видимости/стилей/времени анимаций одного живого документа. Замечание T020
остаётся открытым; произвольное отключение переходов в продукт не внесено.

### Повторный аудит реализации и Phase 11 — T030–T032

На неизменном продуктовом коде `34c4650b4` три независимых агента проверили
незакрытые группы T005–T008, T010/T011/T013/T014 и T015–T017 по исходникам,
потребителям, тестам и существующему журналу 574 PASS. Они не запускали сборки,
GUI или новые тесты и не меняли файлы. MAIN перепроверил найденные объявления
и все Swift-потребители. Нового результата 574 PASS этим проходом не заявляется.

Локальный объём T005/T007/T010/T011/T016 подтверждён чтением и прежними
исполняемыми тестами. Общее закрытие задач/фичи не объявлено: T008/T013/T014/
T015/T017 имеют оставшиеся ограничения интеграционного или ручного evidence.
В частности, source-contract executable entry point не равен запуску его
реальных обработчиков; наличие fullscreen-флагов не доказывает работу на
двух физических экранах, а запись initial announcement — озвучивание VoiceOver.

Converge обнаружил три новые конкретные группы оставшейся работы:

| Finding | Тип / важность | Связь | Доказательство / дальнейшая работа |
|---|---|---|---|
| C11-01 | partial / MEDIUM | FR-009/010/020–022, SC-002/006 | `MeetingDetectionCountdown` и `PromptDecision.startReason` используются только тестами; недостижимый источник timeout в ветке persistedRule=always. T030 переносит проверки на действующий путь и удаляет остатки |
| C11-02 | partial / LOW | FR-012/021/022/025, SC-006 | duration short/preview нигде не переопределяется; callbacks этих методов не имеют рабочих потребителей. T031 убирает API и связанные поля, заменяя тестовые счётчики наблюдаемыми результатами |
| C11-03 | partial / MEDIUM | FR-019, SC-004 | Геометрия scroll view и получение key focus не доказывают клавиатурную прокрутку/возврат фокуса. T032 добавляет два поведенческих сценария |

Результат converge: `tasks_appended`, три задачи T030–T032, Phase 11.
Предыдущие задачи/spec/plan не переписаны. Проверены семь архитектурных пунктов
плана и ограничения применимых принципов Конституции I–VII; новых нарушений
конституции не найдено. Общая приёмка не пройдена, прежние открытые gates не
заменяются этими тремя задачами. До/после converge включённых hooks нет.

MAIN выполнил analyze после новых tasks: 32 уникальных задачи, 28 FR,
8 SC, 15 AC; покрытие задачами36/36 требований/критериев и15/15сценариев,
нет задач без назначения или конфликтующих зависимостей. A11-01 (MEDIUM)
уточнено append-only: старый disabled Start не возвращается; проверяется
действующий допуск записи на границе события, без изменения capture gates.
Итог неразрешённых CRITICAL/HIGH/MEDIUM/LOW:0/0/0/0. Независимый допуск31/31
и отдельный analyze32tasks PASS сохранены reviewer в `scope-review.md`.
Это качество требований, не выполнение новых задач.

Примечание совместимости инструментов: prerequisite не поддерживает
`--require-spec` (явный отказ); выполнен поддерживаемый
`--json --require-tasks --include-tasks` и отдельно проверено наличие spec.
Скрипт не менялся, отсутствующие документы не игнорировались.

Issue sync выполнен только после analyze: remote `yshishenya/graf` подтверждён;
поиск всех состояний по feature title и feature:277 нашёл25 прежних открытых
владельцев29задач, дублей T030–T032 не было. Созданы канонические русские issues
#7339/T030, #7340/T031, #7341/T032 с критериями, зависимостями и обязательными
метками. Прежние issues не закрывались и не редактировались. Pre-hook canon
ensure PASS без изменения файлов; post-hook canon validate PASS (300 issues).
Реализация Phase11 ещё не начата; код и установленный GRAF не менялись.

## Phase 11 — реализация T030–T032 (2026-09-27, после 8c57fd04b)

Lane: существующий `high-risk-product`; независимый повтор требований дал
26/26 custom + 5/5 built-in, 32 уникальных задачи, отсутствие нерешённых
CRITICAL/HIGH/MEDIUM. Три live issues #7339/#7340/#7341 проверены OPEN.
Изменения ограничены ранее согласованными задачами; installed Dev не менялся.

### Что удалено и чем заменены проверки

- T030: удалены `MeetingDetectionCountdown`, неиспользуемое вычисляемое свойство
  `MeetingDetectionPromptDecision.startReason` и недостижимый `prompt_timeout`
  внутри `persistedRule == .always`. Живые reason enum, persistedRule,
  обработчики записи и восемь секунд сохранены. До удаления пять перенесённых
  тестов прошли на настоящих presenter/card: 7.999/8, повторное нажатие,
  сохранённая старая кнопка, закрытие и отсутствие позднего старта.
- Изменение допуска в обе стороны после показа проверяется для кнопки и
  истечения с рабочим `RecordingPrerequisiteGate`. Обработчик связывания в этом
  тесте принадлежит тесту: это НЕ выполнение executable-handler TwoBrainRecApp
  и НЕ запуск аудио. Стандартный countdown presenter не заменяет проверку
  переданного приложением onTick; прежние Policy/RecordingLifecycle сохранены.
- Retirement guard получил 27 тестов. До изменения guard:24 FAILED/3 PASS;
  после:78 PASS включая текущее дерево. Обнаруживаются объявления старого
  типа и свойство в модели/расширениях; похожие живые имена, комментарии,
  строки, параметры и локальные переменные не запрещаются. Проверка
  лексическая, не полный анализатор Swift и не доказательство достижимости.
- T031: удалены duration/onExpire short/preview и поля ShortCandidate.
  Сохранены20 секунд ожидания от события,20 секунд показа от фактического
  появления и6 секунд preview. Общий Envelope.onExpire для prompt сохранён.
  Проверяются реальное исчезновение/закрытие, отсутствие повтора, новейший
  кандидат после истечения старого, исходный срок ожидания и нейтральная история.

### T032: обнаруженная ошибка и исправление

Исходный новый тест: Escape/возврат окна PASS; прокрутка RED,5 assertions.
После Tab firstResponder становился самой панелью; Down/PageDown оставляли y=0.
Принятие фокуса самой NotificationCardScrollView исправило прокрутку, но оставило
1 RED: следующий Tab попадал во внутренний NSClipView. Это наблюдалось в
firstResponder/nextKeyView, а не предполагалось по геометрии.

Исправление: scroll явно принимает фокус, computed keyboardControls задаёт
единственный порядок для links и явного Tab/Shift-Tab. Нет второго сохранённого
списка, новых активаций, сроков или изменений capture. Финальный тест проверяет
реальные Down/PageDown, новый заголовок в NSTextField после tick, прежние окно,
фокус и scroll position, действие и обратный обход. Отдельно настоящее
контрольное окно восстанавливается после Escape; новая карточка из onClose
получает и сохраняет key focus. Это не заменяет native-willClose и ручной VO.

Независимые code reviews T030/T031 без замечаний. В T032 reviewer нашёл пробел:
неизменный текст onTick не доказывал обновление. Он устранён изменяемым заголовком
и проверкой NSTextField; повторное review финального diff без P1/P2.

### Выполненные команды и результаты

Все команды из feature worktree, один владелец Swift build. Фильтры:

```sh
swift test --package-path apps/macos --filter MeetingDetectionCountdownTests
swift test --package-path apps/macos --filter 'MeetingDetectionCountdownTests|DesktopNotificationPromptLifecycleTests|MeetingDetectionPolicyTests|MeetingDetectionRecordingLifecycleTests|RecordingPrerequisiteGateTests'
swift test --package-path apps/macos --filter DesktopLocalNotificationDeliveryTests
swift test --package-path apps/macos --filter 'ShortRecording|DesktopLocalNotificationDeliveryTests|DesktopNotificationHistoryTests|DesktopNotificationPromptLifecycleTests|EmbeddedCabinetNotification'
swift test --package-path apps/macos --filter 'DesktopNotificationAccessibilityTests|DesktopNotificationCompactTests|DesktopNotificationPromptLifecycleTests'
```

Результаты по порядку:5 PASS до удаления;68 PASS после T030;35 PASS перед
удалением API T031;76 PASS после;41 PASS после исправления T032,0 skips/0 failures.

Общий фильтр, с GRAF_CARD_SNAPSHOT_DIR в отдельном временном каталоге:

```sh
swift test --package-path apps/macos --filter 'RecordingStartAcceptanceTests|DesktopUploadQueueTests|DesktopUploadClientTests|LocalRecordingWriter|CaptureRecovery|CaptureControlTests|CaptureIndicatorTests|RecordingDeletion|DesktopNotification|DesktopLocalNotification|EmbeddedCabinetNotification|MeetingDetectionCountdownTests|MeetingDetectionPolicyTests|MeetingDetectionRecordingLifecycleTests|ShortRecording|AppControlAccessibility|DesktopCabinetRoutePolicy|DesktopCalendarReminderTests|CabinetSidebarRuntimeTests|DesktopCabinetWorkspaceTests'
swift build --package-path apps/macos --product TwoBrainRecApp
swift build --package-path apps/macos --product ContractValidation
apps/macos/.build/debug/ContractValidation
python3 scripts/check_notification_retirement.py
apps/server/.venv/bin/python -m pytest -q -o addopts= apps/server/tests/contract/test_desktop_notification_retirement.py
```

После T030 общий574 PASS,0 skips/0 failures,31.078s. После всех изменений:
579 выбранных,572 PASS/7 SKIP/0 failures,44.443s. Повтор только профильных41:
34 PASS/7 SKIP/0 failures,17.975s. Оба поздних запуска получили отказ фокуса
обычного контрольного окна до создания карточки: пять Accessibility и два
PromptLifecycle. Это ограничение среды не убрано из тестов и не считается PASS;
ранний41/41 с тем же финальным кодом сохранён как отдельное доказательство.
Полный T019/T020 не закрыт этими результатами.

Обе сборки и ContractValidation PASS; retirement0violations; pytest78 PASS,
2.51s,0 skips. Существующие предупреждения preconcurrency/устаревших AX-методов
и два предупреждения pytest не подавлялись. T030–T032 отмечены как локально
реализованные и проверенные в их границах; GitHub остаётся OPEN до PR/приёмки.
T019–T022 и общий повтор converge ещё не завершены. Не выполнены новая установка
через harness, полная ручная матрица, exact-SHA PR checks, merge или release.

## Установка 51bcff6b1 и ограниченная ручная проверка — 2026-09-27

Контур: продолжение F277 `high-risk-product`, T020/T021; эта запись меняет
только доказательства, не поведение приложения и не статус незавершённых задач.

### Единственный GRAF Dev

- Из чистого feature worktree собран source SHA
  `51bcff6b1abfdf2a01d59a7d3f00c831674c365c` командой
  `infra/scripts/dev-harness.sh build --sha "$(git rev-parse HEAD)" --feature-id 277 --live`.
- `promote --live --dry-run`, затем настоящий `promote --live` с manifest
  `dev-51bcff6b1abf` завершились успешно. Установлен только
  `/Applications/GRAF Dev.app`, bundle ID `pro.2brain.graf.dev`; подпись,
  entitlements и данные сохранены, reset не выполнялся.
- Отдельный `infra/scripts/dev-harness.sh smoke --json --live` вернул
  `status=pass`, точный source SHA и 13 PASS: identity, presentation, auth,
  backend, database, source, frontend, media worker, migration, processing
  worker, representative API, storage, Temporal. Это подтверждает рабочую
  установку, но не всю ручную матрицу уведомлений.
- Production, PR, merge, release не затронуты. Нового полного запуска Swift
  tests в этом проходе не было; результаты и семь SKIP выше сохраняют силу
  только в своих границах.

### Фактический интерфейс и безопасное окончание теста

- Из настроек показан настоящий preview. Команда меню «Перейти к уведомлению»
  доступна при открытой карточке и переводит фокус на «Закрыть уведомление».
  На снимке компактная карточка с маленьким крестиком сверху слева, без
  отдельной пустой колонки; видна рамка клавиатурного фокуса.
- Настоящее нажатие Tab сохраняет фокус на единственном действии preview;
  Escape убирает карточку и возвращает основной интерфейс. Запись от preview
  не запускалась. Это не доказательство VoiceOver или первого физического
  нажатия по неактивной карточке.
- В двух разрешённых пустых встречах Телемоста вопрос фиксируется журналом,
  затем принят по `reason=prompt_timeout`, `autoRecordOptIn=false`.
  Времена UTC: 20:38:04 → 20:38:13 и 20:43:04 → 20:43:12. Секундные метки
  журнала не являются точным измерением восьмисекундного срока.
- Во втором проходе средство управления окнами вернуло
  `frontmostApplicationChanged` и `timeoutReached`; перейти к вопросу и
  выполнить отказ до срока не удалось. Это НЕ PASS кнопки отказа или флажка
  и само по себе не доказывает дефект приложения. Сроки/правила ради теста
  не изменялись, последующие повторные встречи не создавались.
- После входа камера и микрофон Телемоста выключены с подтверждением AX.
  Возникшая запись GRAF остановлена через его видимую кнопку; после последней
  попытки AX подтверждает «Запись остановлена» и «Начать запись». Из обеих
  тестовых встреч выполнен выход. Приглашения и содержимое встречи не
  отправлялись; ручное удаление данных не выполнялось.
- Несоответствие локальных переключателей сохраняется: AX сообщает первые
  три значения `on`, снимок показывает серые переключатели слева. Причина в
  установленном приложении не доказана; опыт скрытого WKWebView не заменяет
  это доказательство. Параметры пользователя не переключались ради проверки.

### Независимая ограниченная сверка кода

Два read-only reviewer на `51bcff6b1` не нашли новых конкретных дефектов в
проверенных очереди, сроках, календаре, приватной истории, настройках и
связях единого presenter. Отдельная проверка FR-021–023/SC-006 не обнаружила
новых мёртвых веток: единственный `UserNotifications` helper нужен только
для удаления прежних сообщений, а поля миграции — для переноса отметок и
защиты от повторов; это не второй способ показа.

Вывод ограничен прочитанным кодом: не общий `converged` и не закрытие T019–T022.
Открыты реальный отказ/флажок на текущей установке, VoiceOver/первое физическое
нажатие, полная матрица тем/шрифта, календарь/обновление старой установки,
сон/блокировка, два экрана/fullscreen, резервные настройки и соответствие
видимого положения переключателей значениям. Exact-SHA PR checks ещё не
выполнены. Новых задач-дублей для этих существующих пробелов не добавлено.

### Повтор фокуса без пропусков и уточнение WebKit — 2026-09-27

На чистом `f29675776` (product code совпадает с установленным `51bcff6b1`)
выполнен один ограниченный повтор после успешного переключения основного окна
командой меню `Window → GRAF Dev` (`makeKeyAndOrderFront:`):

```sh
swift test --package-path apps/macos --filter 'DesktopNotificationAccessibilityTests|DesktopNotificationCompactTests|DesktopNotificationPromptLifecycleTests'
```

Результат: **41 PASS, 0 SKIP, 0 FAIL**, exit0, 5.254s,
завершение тестового процесса 2026-09-27 23:47:30.506 по местному времени.
Временный журнал: `/tmp/graf-f277-focus-final-repeat.log`.
Пройдены в том числе реальные AppKit проверки Tab/ShiftTab/Space/Return,
Down/PageDown с сохранением прокрутки на tick, Escape с возвратом прежнего
окна и заменой карточки в callback, удержание информационного срока и
неизменность срока вопроса/встречи. Тесты и условия SKIP не менялись.
Это отдельное положительное доказательство семи ранее пропущенных проверок,
а не переписывание исторического общего результата 572 PASS/7 SKIP.
Полная ручная матрица T020 и общий T019 этим повтором не закрыты.

В установленном GRAF до запуска тестов получено новое визуальное наблюдение:
после `Window → GRAF Dev` системные кнопки окна стали цветными, первые три
переключателя сдвинулись из крайнего левого положения в промежуточное,
фон стал промежуточным фиолетово-серым. AX сохраняет `on/on/on/off`.
Следующий снимок и обычная прокрутка вниз/вверх показывают то же промежуточное
состояние. Значения предпочтений не менялись. Это совместимо с приостановкой
перехода/изображения, но не устанавливает её причину и не доказывает
`document.visibilityState` в живом документе.

Контекстное меню страницы содержит только Back/Reload; встроенный инспектор
WebKit через этот интерфейс недоступен. Обращение к Dock через средство
управления окон завершилось `timeoutReached`. Обход авторизации, установка
другого приложения, включение отладки в установленном пакете, изменения CSS
или принудительное завершение анимаций не выполнялись. Запрошен независимый
обычный снимок macOS от пользователя без переключения настроек/начала записи.
До него визуальное расхождение остаётся открытым, исправление по гипотезе
не внесено. Новых встреч и записей в этом проходе не создавали.

### Независимый снимок пользователя — 2026-09-28

Пользователь предоставил обычный снимок macOS в ответ на запрос выше.
На снимке видны GRAF Dev, раздел «Уведомления» и настоящая проверочная
карточка. Первые три локальных переключателя — «Напоминать о встречах»,
«Показывать названия встреч», «Звук уведомлений» — фиолетовые, ползунки
справа; «Тихий режим» — серый, ползунок слева. Значения соответствуют ранее
прочитанным AX `on/on/on/off`; выбран интервал «За минуту».

Конкретное препятствие проверки видимого положения переключателей снято:
неверное/промежуточное положение из снимков инструмента не воспроизводится
на независимом пользовательском снимке. Это не устанавливает точную причину
приостановки изображения в прежних наблюдениях и не является проверкой
сохранения всех комбинаций настроек. Оснований для предложенной по гипотезе
правки CSS нет; код, настройки и анимации не менялись.

Карточка в правом верхнем углу имеет две читаемые строки, значок колокольчика
и маленькое закрытие на верхнем левом углу без отдельной пустой колонки.
Текст не обрезан. Снимок подтверждает этот статический вид preview в тёмной
теме, но не нажатие крестика, его область нажатия, срок, VoiceOver,
интерактивный вопрос записи, другие виды карточек или темы/масштабы.
Версия исполняемого кода из самого снимка не определяется; ранее установленный
SHA не переаттестуется по изображению. Файл снимка с окружающими окнами не
копировался в репозиторий. Сохраняется только это описание результата.
Остальные условия T019–T022 остаются отдельными открытыми проверками.

### Настоящий отказ в Телемосте и границы следующих попыток — 2026-09-28

Рабочая копия перед проверкой чистая, HEAD `1110dc1cf`; `dev-harness status
--json` подтверждает установленный `/Applications/GRAF Dev.app`, активный
`dev-51bcff6b1abf`, source SHA `51bcff6b1abfdf2a01d59a7d3f00c831674c365c`.
Его сохранённый smoke PASS относится к предыдущей установке, не новому
запуску всех 13 проверок. В этом проходе сборок/установки/Swift tests не было.

**Отказ без запоминания — подтверждён в установленном приложении.**
Создана разрешённая пустая встреча без приглашений и разговора. Команда
`Command-Option-N` перевела фокус к настоящему `graf-notification-card`:
заголовок «Встреча в Yandex Telemost», текущий отсчёт, флажок `off`,
действия «Не записывать», «Записать», «Закрыть уведомление».
По свежему AX выбран «Не записывать»; карточка исчезла. После исходного
срока при ещё открытой встрече GRAF показывал «Запись остановлена» и
«Начать запись». Журнал UTC: 21:45:12 `prompt_presented`, 21:45:16
`consumer_outcome result=rejected reason=user_skipped`, затем
`prompt_dismissed`; принятия этого вопроса/начала записи не зафиксировано.
В настройках прочитано «Автозапись: Yandex Telemost — Спрашивать».
После проверки из встречи выполнен выход. Проверено действие через средство
управления интерфейсом после явного фокуса, не первый физический щелчок
по карточке неактивного приложения.

**Флажок плюс крестик — не подтверждены.** В следующей пустой встрече
21:46:12 UTC вопрос был показан и сразу снят при
`observer_lifecycle phase=unexpected_finish`, затем `retry_scheduled`,
`observer_reconcile`, `snapshot_started`, `snapshot_unavailable`,
`live_started`. Кнопки не нажимались; запись не началась, правило осталось
«Спрашивать». Это фактическое снятие вопроса при потере наблюдения, не
проверка крестика и не основание менять детектор в рамках оформления.

После восстановления выполнена одна дополнительная попытка: вопрос показан
21:48:03, принят 21:48:12 UTC с `reason=prompt_timeout`,
`autoRecordOptIn=false`. Инструмент не успел добраться до карточки;
флажок/крестик не нажимались. Запись остановлена видимой кнопкой, конечный
AX подтверждает «Запись остановлена»/«Начать запись», Телемост — главный
экран с «Новый звонок». Все три встречи завершены; микрофон и камера
Телемоста выключались после появления их элементов управления. Значения
правил и сроки не менялись ради теста. Ручного удаления данных не было.
Дальнейшие повторные встречи не создавались. Пользователю предложена одна
короткая физическая проверка флажка/крестика; её результат ещё не получен.

Отдельный read-only `system_profiler SPDisplaysDataType -json` (выведены
только имя/разрешение/признак основного экрана) показал один `Color LCD`,
1800×1169, 120 Hz. Реальная матрица двух экранов/отключения монитора не
может считаться проверенной на этом оборудовании. Попытка открыть View
для полноэкранного сценария получила `timeoutReached`; fullscreen не
подтверждён и не засчитан. Финальный AX снова подтверждает остановленную
запись. T020/T022 остаются открытыми; частичные результаты не общий PASS.

### Сверка локального выполнения задач — 2026-09-28

Независимый read-only reviewer сверил T005–T017 с текущими формулировками,
кодом `51bcff6b1` и evidence до `1110dc1cf`. Последующие изменения main
затрагивают только документы и не меняют проверенную реализацию.
По этому заключению и сохранённым результатам локально отмечены:

- T005: единственный short presenter, удаление старого файла,
  ShortRecordingNotice/AppIntegration и общий прогон.
- T006/T007: исходный RED PromptLifecycle, настоящий lifecycle карточки,
  исходные policy/countdown/capture группы и финальный 41/41 без SKIP.
- T008: интеграция актуального token/действий/отмены, срок после показа,
  gate/decision/presenter tests и настоящий timeout/Stop. Полная матрица
  обработчиков установленного приложения остаётся T020.
- T010/T011: Delivery/Control, приоритеты, сроки, миграция, owner,
  односторонняя очистка; retirement 0 нарушений и 78 PASS.
- T013/T014: действующие WebKit v2 и резервные настройки, удалённый маршрут,
  Swift/37 Node/7 integration, Chromium/WebKit и независимый снимок значений.
- T016/T017: ограниченная история и рабочее меню; AppKit клавиши/hold/фокус,
  модель экранов и недоступного размещения, исполняемая прокрутка и возврат
  окна. Реальные VoiceOver/первый физический щелчок/два экрана не подменены
  этими доказательствами и остаются T020.

Это десять отметок локального выполнения, не закрытие связанных GitHub
issues, приёмка, PR или выпуск. Формулировки и требования задач не менялись.
T015 оставлена открытой: функциональные History/Accessibility проходят,
но сохранённый первоначальный RED не включает HistoryTests, а git-история
вводит файл истории и реализацию одним commit. Доказательств требования
«сначала добавить проверки» для истории недостаточно; ретроспективный
прогон не может подтвердить неизвестную хронологию. Этот пробел в доказательствах
процесса не заявлен дефектом работающей истории. T019–T022 также открыты.

### Итоговый автоматический проход T019 — 2026-09-28

Исходники: чистый `8ed528260414a5d0dd8ddc4e1b301b372c6364d8`, код продукта
не менялся после `51bcff6b1`. Один владелец Swift-сборок; настоящие окна
GRAF/Телемоста не управлялись, новых встреч и установок не было.
Общий целевой набор (это не все тесты репозитория):

```sh
notification_render_dir=$(mktemp -d /tmp/graf-f277-complete-renders.XXXXXX)
GRAF_CARD_SNAPSHOT_DIR="$notification_render_dir" swift test --package-path apps/macos --filter 'RecordingStartAcceptanceTests|DesktopUploadQueueTests|DesktopUploadClientTests|LocalRecordingWriter|CaptureRecovery|CaptureControlTests|CaptureIndicatorTests|RecordingDeletion|DesktopNotification|DesktopLocalNotification|EmbeddedCabinetNotification|MeetingDetectionCountdownTests|MeetingDetectionPolicyTests|MeetingDetectionRecordingLifecycleTests|ShortRecording|AppControlAccessibility|DesktopCabinetRoutePolicy|DesktopCalendarReminderTests|CabinetSidebarRuntimeTests|DesktopCabinetWorkspaceTests'
```

579 выбрано: **577 PASS, 2 SKIP, 0 FAIL**, exit0, 43.809s;
окончание 2026-09-28 00:57:46.555 по местному времени. Пропущены только
`testEscapeRestoresPreviousWindowAndCallbackReplacementKeepsItsFocus` и
`testExplicitFocusAndKeyLoopReachCloseCheckboxAndActions`: независимое обычное
AppKit-окно не получило фокус до создания карточки. Это отказ подготовки
окружения, не успешное выполнение этих двух проверок в общем запуске.
Они ранее прошли в отдельном 41/41 на том же коде; оба результата сохранены
раздельно, условия SKIP и проверки не ослаблялись. Измеренное подтверждение
старта в целевом тесте: `start_acceptance_commit_duration=0.000900125 seconds`.

Остальные команды из quickstart выполнены в этом же проходе:

| Команда | Результат |
|---|---|
| `swift build --package-path apps/macos --product TwoBrainRecApp` | PASS, 3.80s |
| `swift build --package-path apps/macos --product ContractValidation` | PASS, 0.30s |
| `apps/macos/.build/debug/ContractValidation` | PASS |
| `python3 scripts/check_notification_retirement.py` | PASS, 0 нарушений |
| `node apps/server/tests/browser/settings-consistency.test.cjs --notification-contract` | 37 PASS, 0 FAIL/SKIP |
| `apps/server/.venv/bin/python -m pytest -q -o addopts= apps/server/tests/contract/test_desktop_notification_retirement.py` | 78 PASS, 2 предупреждения, 2.84s |
| `bash apps/server/scripts/run_local_postgres_tests.sh --focused -q tests/integration/test_settings_ia_flow.py` | 7 PASS, 2 предупреждения, 13.02s; временный контейнер удалён штатным runner |
| `infra/scripts/ci-local.sh --plan` | dirty=false, cabinet-shell/settings, coverage=partial |
| `infra/scripts/ci-local.sh --focused` | 112 PASS, 2 предупреждения, 3.07s; partial diagnostic, не PR receipt |

Дополнительно настоящий существующий `settings-combobox.test.cjs` запущен
в headless Chromium и WebKit с имеющейся зависимостью Playwright:

```sh
NODE_PATH=/Users/yshishenya/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules node apps/server/tests/browser/settings-combobox.test.cjs
NODE_PATH=/Users/yshishenya/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules BROWSER=webkit node apps/server/tests/browser/settings-combobox.test.cjs
```

Оба PASS, exit0: настройки, явный выбор, клавиши/IME, disabled/reset,
обновление каталога, 600 вариантов, узкая компоновка. Это синтетические
страницы, не дополнительная ручная проверка установленного GRAF.
Новых зависимостей не устанавливалось. Прежние предупреждения Swift
preconcurrency/AX и pytest fixture/Starlette не подавлялись.
Временные журналы имеют общий префикс `/tmp/graf-f277-complete-`:
`native.log`, `node.log`, `retirement.log`, `app-build.log`,
`contract-build.log`, `contract.log`, `settings-ia.log`, `ci-plan.log`,
`ci-focused.log`, `combobox-chromium.log`, `combobox-webkit.log`.

T019 отмечена как выполненный локальный проход: требуемые команды выполнены,
результаты/причины SKIP записаны, новых подтверждённых регрессий нет.
Это не утверждение 579 PASS и не замена открытых T020/T022, физической
проверки двух пропущенных сценариев или exact-SHA/base GitHub gates.

### Уточнение отклонения T015 по первичному журналу — 2026-09-28

Узкое чтение журнала текущей задачи и её субагента установило последовательность
2026-09-26 UTC: попытка patch в 18:52:17 отклонена; успешный patch в 18:57:01
добавил реализацию истории (`appendHistory`, insert newest-first, ограничение50,
очистка контекста); успешный Add File `DesktopNotificationHistoryTests.swift`
выполнен в 19:03:35. Проверены результаты самих вызовов, не только их намерения.
Таким образом, требование T015 «сначала добавить проверки» для истории
**не соблюдено**, а не просто не подтверждено итоговым отчётом.
Полные журналы/содержимое переписки в репозиторий не копировались.

Функциональные HistoryTests проходят, но это не исправляет исторический
порядок действий. T015 пока остаётся открытой; пользователю задан вопрос
о явном принятии документированного отклонения процесса без ослабления
функциональных требований и без закрытия отдельной ручной приёмки.
Без ответа принятие отклонения не предполагается. Производственный код,
спецификация поведения и критерии доступности не менялись.

### Пользовательская проверка запоминания отказа и крестика — 2026-09-28

Пользователь уточнил последовательность: сначала отметил запоминание и
отказался от записи с сохранением правила «Никогда», проверил это правило,
затем вручную вернул «Спрашивать», начал новую встречу, отметил флажок
запоминания и закрыл вопрос крестиком. После последнего крестика возврат
правила вручную не описывался: возврат на «Спрашивать» был до новой встречи.

Сопоставлены сообщение пользователя, свежий AX установленного GRAF и
ограниченный фрагмент технических событий (2026-09-27 UTC):

| Сценарий | Наблюдаемое доказательство | Результат |
|---|---|---|
| Отказ с запоминанием | 22:07:40 вопрос; 22:07:43 `user_skipped`; при следующей активности 22:08:39 `target_policy_never`, без нового вопроса/принятия в этом событии | Правило «Никогда» применилось; соответствует действиям пользователя |
| Ручной возврат «Спрашивать» | После сообщённого изменения снова `prompt_presented` в 22:09:27 | Следующая встреча снова предлагает выбор |
| Флажок запоминания + крестик | Пользователь подтверждает оба действия; 22:09:31 `user_skipped` и снятие вопроса, без `prompt_accepted`; событие закончилось 22:09:55; свежий AX показывает «Спрашивать» и «Запись остановлена» | Закрытие не сохранило новое правило и не запустило запись по сроку |

Журнал сам по себе не различает крестик и кнопку отказа и не содержит
значение флажка: эти сведения получены от пользователя, а не приписаны
техническим событиям. После уточнения промежуточное `target_policy_never`
не является свидетельством ошибочного сохранения по крестику. Оба ручных
сценария в указанной последовательности считаются подтверждёнными; повтор
от пользователя для них не требуется. Это не вся T020: не подтверждены
все сочетания действий, VoiceOver, первый щелчок именно по неактивному
приложению, сон/блокировка и несколько экранов. Принятие отклонения T015
из этого сообщения не следует. Код/настройки/встречи агент не изменял.

### Решения владельца и визуальная сверка — 2026-09-28

Владелец сообщил, что уже проверил VoiceOver и он работает. Это принято
как пользовательское подтверждение работоспособности VoiceOver в выполненной
им проверке; повтор не запрашивается. Подробная последовательность озвучивания
каждого из пяти сценариев не сообщалась и не приписывается этому подтверждению.

Владелец прямо перенёс физическую проверку второго монитора в технический
долг: оборудования сейчас нет. Перенос не является PASS, не отменяет
одноэкранную проверку fullscreen и не меняет код размещения. Долг остаётся
прослеживаемым в T020 / #7305, без новой дублирующей задачи:

- Владелец выполнения: исполнитель F277; доступ к оборудованию — владелец продукта.
- Условие возврата: доступен второй физический монитор.
- Проверить: первоначальный выбор по указателю, стабильность экрана при tick
  и перемещении указателя, отключение выбранного монитора, перенос на основной
  без сброса срока, разный масштаб, доступность крестика и отсутствие перекрытия Stop.
- До проверки нельзя заявлять полную физическую многомониторную приёмку.
  Существующие модельные тесты размещения сохраняются без ослабления.

MAIN просмотрел все 20 PNG, созданных завершённым автоматическим проходом
T019: пять семейств (prompt/short/meeting/problem/preview), aqua/darkAqua,
fontScale 1/1.6. Источник — настоящий AppKit-компонент в
`DesktopNotificationCardTests.testCardSurfacesCanBeCapturedForReferenceComparison`,
не рисунок и не отдельная установленная копия приложения. На просмотренных
снимках текст/действия не обрезаны и не перекрываются, закрытие находится
слева сверху без пустой колонки, у short нет лишнего заголовка/строки действий.
При большом шрифте short занимает две строки, длинные действия meeting
расположены вертикально. Контраст измеряется существующими тестами, а не
объявляется численно доказанным просмотром PNG. Это визуальная проверка
тестовых представлений; она не означает ручное прохождение всех сочетаний
в установленном GRAF Dev. Синтетические снимки остались вне git.

#### Ограниченная проверка полноэкранного сценария

Использовано только установленное GRAF Dev с неизменным кодом `51bcff6b1`.
Новых встреч, записи, изменений предпочтений, установок или сборок не было.
Телемост переведён в полноэкранный режим; меню подтвердило состояние командой
«Выйти из полноэкранного режима». У GRAF показан настоящий preview из настроек,
затем явная команда Command–Option–N: AX показывает `graf-notification-card`,
заголовок/сообщение и фокус на «Закрыть уведомление». Снимок отдельной карточки
читаем и без обрезания; Escape снимает её, GRAF показывает «Запись остановлена».

Снимок отдельного окна не доказывает видимость поверх другого приложения
без перехода фокуса, принадлежность текущему Space или отсутствие переключения
Space. Эти части fullscreen не объявлены PASS. Средства управления также
не подтвердили возвращение Телемоста в обычный режим: доступная команда выхода
и сочетание клавиш не изменили наблюдаемое состояние, снимок открытого меню
оказался недоступен. Меню закрыто; это ограничение управления тестовым окном,
не установленная регрессия GRAF. Частное содержимое чужих окон не сохранялось
в репозиторий.

#### Остаток приёмки после этого прохода

Независимый агент повторно сверил только изменения доказательств и исходные
критерии задач, без повторной реализации/сборок. VoiceOver подтверждён владельцем,
второй монитор отложен владельцем, 20 тестовых изображений просмотрены.
T020 остаётся частичной: первый физический щелчок по неактивному GRAF,
сон/блокировка/пробуждение, остальные сочетания настоящих действий с флажком
и полное одноэкранное fullscreen-поведение пока не подтверждены ручной проверкой.
Нужна также полная привязка живых проверок сроков/удержания, истории,
конкуренции и настроек к матрице quickstart; автоматические результаты
сохраняют свой уровень доказательности.

T015 остаётся открытой как установленное отклонение порядка tests-first:
общее поручение продолжать самостоятельно не записывается как конкретное
принятие отклонения. T021 не получает общей отметки завершения до остатка T020;
T022 (PR и exact-SHA/base проверки) не объявлена выполненной. В этой сверке
новых непокрытых задач не выявлено: остаток уже имеет владельцев T015/T020–T022,
поэтому дублирующая фаза Convergence не добавлена и полная сходимость не заявлена.
Изменения этого прохода — только доказательства/документация; общая полоса F277
остаётся `high-risk-product`, локальная проверка этих правок — docs-only.

### Пользовательская приёмка по пошаговой инструкции — 2026-09-28

Пользователь прислал результаты шести пунктов инструкции для единственного
GRAF Dev. Ниже — ручные свидетельства пользователя, не автоматические
измерения и не результат нового управления окнами агентом. Точное время
отдельных действий/версии приложения пользователь не указал; предыдущая
проверенная установка — `51bcff6b1`, агент после неё приложение не обновлял.

| Пункт | Подтверждение пользователя | Принятый результат |
|---|---|---|
| 1 — fullscreen / первый щелчок / close без флажка | Карточка появилась поверх полноэкранного приложения, рабочий стол не переключился, крестик сработал с первого раза, запись не началась | Подтверждены физический первый щелчок и одноэкранный полноэкранный сценарий; прежний пробел отдельного снимка окна закрыт пользовательским наблюдением |
| 2 — preview | Сам исчезает, наведение удерживает, фокус виден, Escape закрывает | Подтверждена ручная проверка по инструкции; точные длительности и отдельный перечень всех клавиш не заявлены инструментально измеренными |
| 3а — start без remember | Запустилась, остановлена, правило осталось «Спрашивать» | Подтверждено пользователем; он уточнил, что проверял это ранее, повтор не нужен |
| 3б — start с remember | Запустилась, остановлена, стало «Всегда», затем вручную возвращено «Спрашивать» | Подтверждено пользователем; не приписывать автоматический возврат правила приложению |
| 3в — timeout с remember | Запустилась по таймеру, остановлена, осталось «Спрашивать» | Подтверждено пользователем; флажок без явного действия не сохраняет правило |
| 4 — short и история | «ОК» в ответ на пункт о сообщении короткой записи и повторном доступе в меню | Принят успешный ручной результат заданного сценария; не доказательство всех 50 записей/смены контекста |
| 5 — блокировка | Заблокировал во время вопроса, после разблокировки запись остановлена; отдельным ответом уточнил «Не появился» | Запись не началась, новый вопрос после разблокировки не появился; ручной сценарий подтверждён |
| 6 — сон | «Сон ок» в ответ на сценарий сна до завершения отсчёта | Принят успешный ручной результат заданного сценария, без выдуманной трассы событий |

Прежние подтверждения VoiceOver, skip без remember, skip с remember → «Никогда»
и remember + close → без сохранения правила сохраняются. Повторять пункты
1–4/6 или матрицу старта от пользователя не требуется. Физические два экрана
остаются прямо согласованным техническим долгом T020 / #7305.

Владелец ответил на оба уточнения без повторного теста: новый вопрос
после разблокировки «Не появился»; на принятие документированного отклонения
T015 — «Да, принимаю это отклонение». T015 закрыта локально по реализации,
успешным проверкам и явно принятому отклонению процесса. Исторический порядок
не переписан и не объявлен tests-first; функциональные требования сохранены.
T020/T021/T022 пока не помечаются полностью завершёнными: требуется окончательная сверка
с исходной матрицей и независимым review, затем отдельные PR-проверки.
Этот отчёт снимает прежние перечисленные пробелы в пределах подтверждений,
а не заменяет пользовательскими словами автоматические/контекстные тесты.
Изменения — только документы (`docs-only` внутри F277 `high-risk-product`);
новых встреч/записей, изменений кода/настроек или установки агент не выполнял.

## Исправление подтверждённых сбоев PR #7351 — 2026-09-28

Lane: существующая F277 `high-risk-product`, T019 / #7303 и T022 / #7276.
Предыдущий проход дал новые проверенные причины отказа, а не только повтор
статуса. HEAD до исправления: `29141c332ab88f81395e40464083bb041d970836`.

- `governance-fast` run36359095808: отсутствовал `## Legacy Impact` в spec.
  Добавлен раздел `Classification: remove`, описывающий уже согласованные
  FR-014/021/023/027 и cleanup-map; новых исключений совместимости нет.
  Повторный локальный validate-legacy-impact — OK. Ошибки времени отчёта
  неуспешного CI не обходились; корректность отчёта подтвердит новый CI.
- `macos-pr` run36359095794 повторил ошибку Swift 6.0.3 на CalendarTray.swift:179:
  `sending 'self' risks causing data races`. В callback слабая ссылка
  раскрывается в неизменяемую ссылку до `MainActor.assumeIsolated`.
  Синхронная отмена прежнего контекста остаётся до Task refresh; событие,
  регистрация, очередь main и правила доступа не изменяются.
- Локальный компилятор: Apple Swift 6.3.3. Его успешный результат не заменяет
  компиляцию Swift 6.0.3 в GitHub. Code/Security review Codex для старого
  `29141c332` завершились без опубликованных замечаний; это не review нового SHA.
- Независимый reviewer: 26/26 custom + 5/5 built-in, analyze0/0/0,
  code-review ограниченного финального diff PASS, подробности в scope-review.

Проверки проводились автоматическими тестами worktree, без установки/запуска
нового приложения и без реальных встреч. Сначала добавлялся тест настоящего
NotificationCenter callback; два узких теста и профиль77 прошли. Reviewer
обнаружил, что новый тест запускал периодические ресурсы без очистки. Он
полностью удалён, файл тестов совпадает с HEAD; API только ради теста не добавлен.
Прежний тест синхронной отмены/отклонения pending ответа сохранён, но проверяет
прямой метод, а не регистрацию наблюдателя. Промежуточные77 не выдаются за
финальный набор.

Промежуточный неполный фильтр (488 тестов, с удалённым впоследствии тестом)
завершился exit1: один клавиатурный тест дал три assertions при отказе
получения key window (`active=false, running=false`), экспорт изображений
пропущен без GRAF_CARD_SNAPSHOT_DIR. Это не PASS; окончательный запуск ниже
использовал полный прежний фильтр и каталог экспорта, без изменения тестов
фокуса/условий пропуска и без снятия проверок. Прямой причинной связи сбоя
фокуса с удалённым тестом не утверждаем.

Окончательная команда:

```sh
notification_render_dir=$(mktemp -d /tmp/graf-f277-ci-fix-renders.XXXXXX)
GRAF_CARD_SNAPSHOT_DIR="$notification_render_dir" swift test --package-path apps/macos --filter 'RecordingStartAcceptanceTests|DesktopUploadQueueTests|DesktopUploadClientTests|LocalRecordingWriter|CaptureRecovery|CaptureControlTests|CaptureIndicatorTests|RecordingDeletion|DesktopNotification|DesktopLocalNotification|EmbeddedCabinetNotification|MeetingDetectionCountdownTests|MeetingDetectionPolicyTests|MeetingDetectionRecordingLifecycleTests|ShortRecording|AppControlAccessibility|DesktopCabinetRoutePolicy|DesktopCalendarReminderTests|CabinetSidebarRuntimeTests|DesktopCabinetWorkspaceTests'
```

Результат: **579 PASS, 0 SKIP, 0 FAIL**, exit0, 35.656s; окончание
2026-09-28 02:49:00.972 местного времени. Подтверждение запуска0.001379083s.
Журнал `/tmp/graf-f277-ci-fix-final.log`. Старые результаты не переписаны.

Также PASS: `swift build --package-path apps/macos --product TwoBrainRecApp`,
сборка и запуск ContractValidation, `scripts/check_notification_retirement.py`
(0 violations), `scripts/validate-legacy-impact.py --feature
specs/277-compact-notifications/spec.md`, `scripts/check-development-process.py`,
`scripts/check_spec_kit_governance.py`, `git diff --check`.
Локальный ignored feature pointer приведён к текущему HEAD после обнаружения
старого source_sha; ветка, область владения и риск сохранены, валидатор не менялся.
Hooks before/after implement отключены. Установленный GRAF Dev остаётся51bcff6b1;
ручную приёмку и долг второго монитора это исправление не переписывает.
Окончательная приёмка T021/T022 требует новых точных GitHub SHA/base результатов.

## Полный CI обнаружил оставшиеся старые тесты — 2026-09-28

На `b850b975f1902c511240133949e6080fb95a9b19` сборка Swift 6.0.3
успешно дошла до тестов: прежний отказ компиляции устранён. `macos-pr`
run36360051114 завершился FAILURE: 1139 тестов, 2 SKIP, 17 ошибок утверждений
в трёх тестах. Они не входили в прежний локальный фильтр579. Это новый
подтверждённый остаток T019, не повод объявить прошлые579 полной проверкой CI.

- AppLifecycleWindowRegressionTests.testPromptGeometryUsesSharedCardLayout
  всё ещё требовал старые420/448pt, topInset39 и удалённые методы. Пять
  проверок строк заменены настоящим компонентом из F277CardFixture:
  успешный показ,380pt видимой карточки, два нажатия крестика → один callback,
  ноль действий, скрытое окно, обязательный dismiss. Другие lifecycle-тесты
  не менялись; новая карточка не подстраивалась под старые размеры.
- Два положительных теста DesktopUploadRetirementTests не записывали исходный
  manifest v5. Действующий live gate закономерно запрещал попытку до вызова
  тестового транспорта. Теперь в изолированный каталог записывается
  декодируемый manifest с совпадающими sessionId/directoryId и accepted.
  В mixed-сценарии у v5 отдельные идентичности и каталог. Все прежние assertions
  retired/swap/reconcile/progress/late success/failure/повтор/удаление сохранены.
  Минимальный manifest с tracks=[] проверяет только переходы очереди через
  подставной транспорт; он не доказывает полноту медиа или отправку настоящим
  DesktopUploadClient. Рабочие admission/capture/upload paths не менялись.
- Обе группы включены в quickstart, чтобы не выпадать из целевых проверок.

Независимый допуск Russell и Laplace: custom26/26 + built-in5/5,
analyze0 CRITICAL/HIGH/MEDIUM, область прежней T019/#7303 без новой задачи.
Laplace отдельно прочитал окончательный diff и вернул code/test review PASS:
исходные утверждения сохранены, минимальный manifest допустим для этого
тестового транспорта. Reviewer файлы/отметки не менялись.

Воспроизведение и результат:

```sh
swift test --package-path apps/macos --filter 'AppLifecycleWindowRegressionTests|DesktopUploadRetirementTests'
```

До правки:8 тестов,3 неуспешных,17 ошибок assertions, exit1.
После:8 PASS/0 SKIP/0 FAIL, exit0,0.510s. Журналы:
`/tmp/graf-f277-ci-regressions-before.log`,
`/tmp/graf-f277-ci-regressions-after.log`.

Полный локальный фильтр предыдущего раздела расширен двумя группами
`AppLifecycleWindowRegressionTests|DesktopUploadRetirementTests`, с новым
GRAF_CARD_SNAPSHOT_DIR. Результат587: **580 PASS,7 SKIP,0 FAIL**, exit0,
53.672s, окончание03:04:09.124 местного времени. Журнал
`/tmp/graf-f277-regression-complete.log`. Подтверждение запуска0.00053725s.
Все семь пропусков — независимое контрольное окно не получило фокус:
пять DesktopNotificationAccessibilityTests (Escape/явный focus/inactive host/
keyboard actions/scroll), два DesktopNotificationPromptLifecycleTests
(hold/deadline). Условия SKIP и assertions не менялись. Отдельный профиль
Accessibility/Compact/PromptLifecycle:41 выбрано,34 PASS/7 SKIP/0 FAIL,
18.651s; `/tmp/graf-f277-regression-focus.log`. Это подтверждает ограничение
текущего тестового хоста, не успешность этих семи сценариев. Предыдущий579/579
и пользовательские проверки на неизменном рабочем коде сохраняются отдельно.

Retirement guard0violations, process/governance и diffcheck — PASS.
Этот проход меняет только тесты и документы. GRAF Dev не переустанавливался,
аудио/сеансы пользователя не использовались, PR не сливался. Требуется полный
GitHub CI следующего SHA; текущий неуспешный run не объявляется исправленным
по одним локальным результатам. Физический второй монитор остаётся долгом.

## Итог полного нативного CI — 2026-09-28

Проверен source SHA `e996d25b84557c08301c7563cefa16402631dec7`, база PR
`f5cca687a06dc57ad6ccbef840a0be897eaa6336`. Запуск
[macos-pr 36361150674](https://github.com/yshishenya/graf/actions/runs/36361150674)
завершён SUCCESS. Swift build, полный XCTest и ContractValidation — PASS.
XCTest: **1139 выбрано,1137 PASS,2 SKIP,0 FAIL**,124.560s;
окончание2026-09-28 00:17:07 UTC.

Пропущены только два экспорта изображений:

- DesktopNotificationCardTests.testCardSurfacesCanBeCapturedForReferenceComparison:
  GRAF_CARD_SNAPSHOT_DIR не задан; экспорт не запрошен.
- SystemAudioPermissionUXTests.testRenderSyntheticPermissionStates:
  GRAF_PERMISSION_PREVIEW_DIR не задан.

Семь клавиатурных сценариев, пропущенных локально из-за контрольного окна,
в полном CI не пропущены. Это подтверждает их на другом тестовом хосте,
но не превращает исторический локальный результат580/7 в587 PASS.
Ранее экспортированные20 AppKit-представлений и принятые пользовательские
VoiceOver/fullscreen/first-click/сон/блокировка сохраняются как отдельные
виды доказательств. Физический второй монитор T020/#7305 явно отложен
владельцем, не проверен и не закрывается этим запуском.

Этот раздел фиксирует результат проверенного исходного кода. Само добавление
отчёта не является разрешением слияния или выпуска: окончательная проверка
актуальных SHA/base трёх PR-гейтов выполняется отдельно через
scripts/validate-pr-checks.py. При последующих изменениях только документов
не приписывать прежнему запуску новый SHA.

Итоговый независимый аудит Russell сохранён append-only в `scope-review.md`:
28 FR +8 SC +15 сценариев приёмки +7 архитектурных обязательств, новых
обязательных доработок рабочего кода0. Исправления тестов e996 отдельно
проверены Laplace. T021 отмечена по этому результату и обновлённым документам,
с явно принятым исключением физических двух мониторов T020/#7305. Обязательные
условия T022 и состояния GitHub issues не объявлены завершёнными. Локальные
проверки только документации: spec-kit-governance, development-process и
git diff --check — PASS; новые сборки приложения ради текста не запускались.

### Проверка всей совокупности PR-гейтов исходного кода

После завершения общего CI выполнена штатная команда:

```sh
python3 scripts/validate-pr-checks.py --repository yshishenya/graf --pr 7351
```

Exit0; подтверждены target SHA `e996d25b84557c08301c7563cefa16402631dec7`
и checked base `f5cca687a06dc57ad6ccbef840a0be897eaa6336`:

- [governance-fast: PASS](https://github.com/yshishenya/graf/actions/runs/36361150695), attempt1.
- [macos-pr: PASS](https://github.com/yshishenya/graf/actions/runs/36361150674), attempt1.
- [pr-metadata: PASS](https://github.com/yshishenya/graf/actions/runs/36361163162), attempt1.

Валидатор проверил proof artifacts, точную идентичность SHA/base и актуальное
описание PR, не только зелёные значки. `merge_commit_sha:null`: PR не слит.
Следующий коммит сохраняет только итоговые документы и отметку T021. Его
обязательные проверки будут проверены отдельно; будущий результат хранится
в GitHub PR, чтобы не создавать бесконечную цепочку коммитов ради SHA отчёта.
Публичного выпуска и production-действий нет.

## T033 — единый срок видимого вопроса, 2026-09-28

После прежнего итогового аудита проверено замечание PR #7351
discussion_r4117588325. На a29feb9ee591532f695d6d6d2609197895de57aa
подтверждено расхождение трёх точек отсчёта. Прежние успешные проверки
не моделировали продвижение времени внутри первого размещения.
Задача добавлена через converge как T033 / #7352; до реализации выполнены
analyze и независимый requirements gate (31/31,0 unchecked,0 CRITICAL/HIGH,
1 MEDIUM A12-01 о доказательстве текста). Issue canon —300 issues, PASS.

### Воспроизведение до изменения рабочего кода

На прежнем коде, только с новыми тестами:

```sh
swift test --package-path apps/macos --filter 'MeetingDetectionCountdownTests/testDelayedPresentation|DesktopNotificationPromptLifecycleTests/testPromptGetsFullEight'
```

RED: **2 теста,37 ошибок assertions,exit1**, окончание01:39:02 UTC.
`/tmp/graf-f277-t033-red.log` — временный диагностический журнал, не
долговечное доказательство. Матрица проверяет Record/Skip/close/timeout
с флажком и без; часы однократно продвигаются на0.5s при размещении.
Отдельный тест воспроизводит потерю0.4s ещё до входа в card.

### Исправление и локальные проверки

Card фиксирует полный восьмисекундный срок при подтверждённой видимости;
coordinator сохраняет его до terminal clear и использует для текста,
действий и истечения. App передаёт только проверку актуальности token,
без `meetingDetectionPromptStartedAt`, своего remaining или duration.
Обновление флажка/текста не продлевает срок. Календарные абсолютные сроки,
информационное удержание, правила записи и обработка аудио не изменены.

- Первый GREEN:58 выбрано,56 PASS,2 SKIP,0 FAIL,5.772s,01:41:42 UTC.
- Общая регрессия:498 выбрано,490 PASS,8 SKIP,0 FAIL,38.537s,
  01:42:47 UTC. Уведомления, settings bridge, календарь, capture, writer,
  start acceptance, recovery, очередь/клиент отправки, lifecycle/route tests.
- После добавления проверки настоящего NSTextField и правильного имени
  integration suite (`CaptureControlTests`):24 выбрано,22 PASS,2 SKIP,
  0 FAIL,5.107s,01:43:33 UTC. Проверка App является source wiring, не
  исполнением executable-only обработчика. Остаток и текст выполняются
  настоящими presenter/card с callback актуальности, как у App.
- После замечаний независимого reviewer дополнены оба порядка событий ровно
  на deadline (Record/Skip/checkbox), скрытая панель именно на восьмой секунде
  и замена предложения внутри проверки актуальности на tick/action/expiry.
  Профильный итог:26 выбрано,24 PASS,2 focus SKIP,0 FAIL,5.209s,
  01:45:53 UTC. Сохранён строгий порядок: action-first на deadline отменяет
  просроченное предложение, tick-first даёт timeout; оба без сохранения правила.
- Полный локальный `swift test --package-path apps/macos` на итоговом коде
  и тестах:1144 выбрано,1135 PASS,9 SKIP,0 FAIL,89.325s,
  01:47:46 UTC. Из9 пропусков семь focus и два незапрошенных экспорта
  (`GRAF_CARD_SNAPSHOT_DIR`, `GRAF_PERMISSION_PREVIEW_DIR`). Это локальный
  тестовый запуск, не GitHub exact-SHA/base proof.
- `swift build --package-path apps/macos --product TwoBrainRecApp` —PASS.
- Сборка `ContractValidation` и выполнение —PASS.
- `python3 scripts/check_notification_retirement.py` —PASS,0 violations.
- Контрактные тесты retirement —78 PASS,2 существующих предупреждения.
- Spec Kit governance, development-process и `git diff --check` —PASS.

Из8 пропусков общей регрессии семь связаны с отказом тестовой среды
подтвердить фокус контрольного AppKit-окна; восьмой — незапрошенный экспорт
изображений (`GRAF_CARD_SNAPSHOT_DIR`). Два пропуска профильного набора —
те же focus/hold сценарии. Пропуски не считаются PASS. Предыдущие ручные
результаты и CI по другим SHA сохраняют собственные границы доказательств.

Рабочие изменения проверены в текущем diff после a29feb9ee; новый точный
commit SHA и обязательные PR-гейты фиксируются в GitHub после коммита.
Независимое code/test review T033 завершено Russell:0 production findings,
оба замечания к тестам закрыты, FR-009/020 и SC-002 покрыты3/3;
отчёт сохранён в `scope-review.md` (Phase12, post-implementation).
Это не означает слияния или общей готовности. Установленный GRAF Dev здесь
не обновлялся; ручные VoiceOver/полноэкранный режим/первый щелчок/сон/lock
заново не выполнялись. Второй физический монитор остаётся T020/#7305.

Сопутствующее замечание о claim до показа соответствует принятому договору
однократной попытки и отказа размещения; перенос claim после show не делается.
Для сохранения карточки при временной ошибке календаря требуется решение
владельца. Политика очистки проекции при ошибке в T033 не меняется.

## T034 — защита всех действующих indicator/Stop, 2026-09-28

Lane: active high-risk-product Spec Kit slice; Phase13, T017,
FR-019, SC-004, UI contract «Lifecycle/экран», plan I–II.
Requirements/checklist gate выполнен независимым reviewer до кода;
main analyze 2/2, без CRITICAL/HIGH. A13-01 закрыт настоящей проверкой
прокрутки в eventTracking, без ручного reposition и подставных событий.

### RED и исправление

На исходном единственном provider два настоящих hosting-view маркера дали
3 ошибки утверждений: потерю первой области и отсутствие оставшейся
после удаления последней. После введения registry, но до подключения
потребителей, отдельно подтверждён RED compact и titlebar HUD:
реальные AX-границы Stop получены, защищённые области отсутствуют.
Ошибки настройки тестового окружения, компиляции и AX-обхода не считаются
доказательством дефекта; они устранены до итогового прогона.

Единый UUID registry со слабыми ссылками заменяет прежний provider целиком.
Защищаются реальные indicator/Stop компактной панели, раскрытого блока
и titlebar accessory. Пустое пространство инспектора не резервируется.
Скрытие, clipping, смена владельца/окна, прокрутка, сворачивание окна,
создание и удаление HUD учитываются по событиям. Маркеры пропускают клики,
не удерживают view/presenter, не создают новых таймеров. При невозможном
размещении сохраняется явный отказ без скрытого или позднего старта записи.

### Итоговые проверки

- Профиль после последнего дополнения раскрытия/сворачивания:
  10 PASS,0 SKIP,0 FAIL,2.341s, завершён 05:56:35 по локальным часам.
  Три теста действующих потребителей и семь registry; девять новых тестов.
  Настоящие AX indicator/Stop измеряются независимо от маркеров;
  Stop вызывается через AX ровно один раз. Живое переключение панели
  даёт области 3→2→3, сохраняет окно и срок уведомления.
- Заключительный полный Swift-прогон после этого дополнения:
  1153 выбрано,1144 PASS,9 SKIP,0 FAIL,92.945s,
  завершён 05:58:45 по локальным часам.
  Команда: `swift test --package-path apps/macos`.
  Семь существующих пропусков связаны с фокусом тестового AppKit-окна,
  два — с незапрошенным экспортом изображений; это не PASS.
- `swift build --package-path apps/macos --product TwoBrainRecApp` —PASS.
- Сборка и выполнение ContractValidation —PASS.
- `python3 scripts/check_notification_retirement.py` —PASS,0 violations.
- Python retirement contracts —78 PASS,2 существующих предупреждения.
- Независимое code/test review Laplace —0 findings всех уровней;
  main scoped converge FR-019/SC-004 2/2, новых расхождений не выявлено.
  Полный перечень проверенных сценариев — scope-review.md Phase13.

Временные журналы /tmp не являются долговечными артефактами CI.
Точный новый SHA и обязательные GitHub proofs записываются в PR #7351;
успех предшествующего 14462f9f не доказывает новый код.
Ручная приёмка пользователя сохраняет прежние границы: здесь она не
повторялась. Общий /Applications/GRAF Dev.app принадлежит F278,
manifest dev-3e0a0b953c1a; приложение не заменялось и не перезапускалось.
Второй физический монитор — принятый долг T020/#7305; T022/#7276
открыта до завершения обязательных проверок и разрешённого слияния.
Календарная политика не менялась, решение владельца остаётся отдельным.

### T034 — исправление компиляции Swift 6.0.3

GitHub macos-pr run36372180300 для45b582944 завершился FAIL до запуска
тестов: CaptureStatusItem.swift:108 обращался из неизолированного частного
statusSurface(for:) к MainActor-инициализатору маркера. Локальный Swift6.3.3
принимал код; прежние локальные PASS не подтверждали сборку Swift6.0.3.
Последующий text-proof run36372187541 закономерно отклонил этот source proof.
Ошибка не скрывается повторным запуском или пропуском проверки.

Исправление в рамках T034: только явный @MainActor у частного helper
statusSurface(for:), вызываемого из View.body. Без изменения публичного API,
таймеров, callbacks, правил записи или ослабления изоляции через unsafe/Task.
Независимый повторный допуск Laplace:31/31 checklist criteria,0 unchecked;
FR-019/SC-004 2/2,0 findings; владелец #7353 OPEN. Новая задача не требуется.
Отчёт проверяющего получен в чате; исходники/чек-листы он не менял.

После исправления на локальном Swift6.3.3:
- swift test --package-path apps/macos --filter
  'DesktopNotificationProtected|CaptureControlTests|CaptureIndicatorTests':
  73 PASS,0 SKIP,0 FAIL,3.401s, завершено 06:10:13 по локальным часам.
- swift build --package-path apps/macos --product TwoBrainRecApp:PASS.

Полный локальный набор повторно не запускался для одной аннотации:
обязательный полный native CI на новом точном SHA и Swift6.0.3 остаётся
следующим доказательством. До его PASS сборка на поддерживаемом CI toolchain
и T022 не считаются завершёнными. Dev-приложение не изменялось.
