# F279 — security requirements review

Reviewer-owned. Автор реализации не меняет checkbox; это качество требований, не доказательство runtime.

- [x] CHK001: Определены ли owner/workspace/source/calendar selection проверки перед выдачей ссылки/серии/записей? [Spec FR-005–008,014; contracts]
- [x] CHK002: Ограничен ли мост UUID события и доверенным main frame с повторной проверкой сессии после await? [contracts; data-model]
- [x] CHK003: Определён ли запрет внешней передачи GRAF auth и сохранение параметров URL без журналирования содержимого? [Spec FR-005; contracts]
- [x] CHK004: Описаны ли отказ при отменённом событии, disconnect, logout, устаревшем ответе и двойном нажатии? [Spec FR-004–007; quickstart J04–J07]
- [x] CHK005: Имеет ли серия устойчивую изолированную идентичность и явно описанную совместимость legacy без объединения по названию? [Spec FR-008,015,018; data-model]
- [x] CHK006: Исключены ли утечки скрытых записей через группировку/счётчики и расширение прав через серию? [Spec FR-014,016; contracts]
- [x] CHK007: Описаны ли bounds пагинации/синхронизации и действующее удаление/хранение без нового бесконтрольного кеша? [Spec FR-013,017; data-model]
- [x] CHK008: Сохранены ли независимые правила записи, ручные Start/Stop и native-only app validation path? [Spec FR-020; plan; quickstart]

## Reviewer notes

Независимое ревью качества требований, 2026-09-28. `[x]` не означает runtime-приёмку. Результат: **8 checked / 0 unchecked**.

- CHK001 PASS: FR-005–008,014,017; contracts resolver/series/compatibility и data-model «Хранение и запросы» требуют owner/workspace/source/selection до выдачи, группировки и счётчиков, плюс независимые права каждой записи.
- CHK002 PASS: contract «Мост встроенного кабинета» задаёт UUID, точный action, bounded requestId, отказ лишним полям/недоверенному frame, trusted main document/route/session/WebView и повторную проверку после await. Непрозрачный ID не считается авторизацией.
- CHK003 PASS: FR-005, contract resolver/compatibility и design steps 2/5 запрещают вынос GRAF auth/cookies и логирование URL, сохраняют query и запрещают внешний redirect авторизованного resolver.
- CHK004 PASS: FR-004,006–007, state model и quickstart J04–J07 задают отмену, disconnect/selection, logout, stale-response и повторное нажатие; одна попытка открывает не более одного адресата.
- CHK005 PASS: FR-008,015,018 и data-model «Серия и её идентичность» задают составной ключ с external_calendar_id, версию v2, сохранение v1 и только доказанную однозначную связь старых контекстов.
- CHK006 PASS: FR-014,016, SC-005, data-model query constraints и contracts compatibility требуют фильтровать до группировки/счётчиков; серия не расширяет права и не раскрывает скрытые записи.
- CHK007 PASS (повторное ревью): `contracts/calendar.md` «Ограничения истории и курсора» задаёт timezone-aware ISO8601, положительный диапазон максимум 366 суток, default -180/+30 суток, limit 1..50/default 20. Cursor ограничен 2048 ASCII-символами, подписан HMAC, имеет версию, owner/workspace/series/range привязки, устойчивую пару сортировки и TTL 1 час; проверки предшествуют выборке, ошибки дают безопасный 422. `quickstart.md` S10 покрывает превышение диапазона/страницы/курсора, подпись, истечение и чужой контекст. Прежний sync horizon, lifecycle и запрет нового кеша сохраняются.
- CHK008 PASS: FR-020, Plan Constitution Check, design validation и quickstart C02 сохраняют ручные Start/Stop и прежнюю трёхсостоянийную автозапись; native-проверка явно ограничена GRAF Dev через dev-harness.

Повторная проверка перед реализацией: `tasks.md` T001–T008 прочитан и сопоставлен с пунктами; PASS сохраняется. T001 задаёт тесты до кода, T002–T007 — реализацию и проверки по пользовательским сценариям, T008 — полную приёмку и независимое ревью. Analyze записан в `validation.md`; завершение синхронизации GitHub остаётся отдельным процессным условием. Сводный отчёт: `../review-report.md`.


Завершающая проверка локальных доказательств T010: S07 (реальная API/ACL проверка grant/revoke/delete), C02 (production dispatcher/resolver/controller/writer с синтетическими данными) и SC-007 (30 измерений production browser harness) подтверждены PASS. Swift 113/0, серверный contract файл 9 PASS, browser PASS. Границы доказательств и оставшиеся SHA/CI/Dev условия записаны в разделе «Завершающее ревью локальных доказательств T010» `../review-report.md`. Качество требований сохраняется **8 checked / 0 unchecked**.


Независимое повторное ревью четырёх PR-замечаний: day30/history, явное browser recovery, async reminder retry с ограниченным сохранением при offline, допустимые HTTPS-порты — исправлены по исходникам/локальным тестам. Swift 117/0; server focused 13 PASS. Итог и границы app-build/runtime evidence записаны в последнем разделе `../review-report.md`; markers качества требований сохраняются **8 checked / 0 unchecked**.


Вторая группа PR-замечаний независимо проверена 2026-09-29: ранний readiness cancel, явный menu retry, стабильный signed overview anchor через UTC midnight, видимый reminder pending — RESOLVED в границах исходников/локальных тестов. Swift 120/0, server 14 PASS, дополнительный cursor unit 4 PASS (пересекающийся набор), browser PASS. Полные доказательства и границы в последнем разделе `../review-report.md`; требования **8 checked / 0 unchecked**.


Третья группа PR-замечаний проверена 2026-09-29: eligibility обычных дат при сохранении отменённых, prompt-specific guard через resolver/native/browser recovery, standalone local error с единственным безопасным popup — RESOLVED по исходникам и локальным проверкам. Swift 120/0, server 16 PASS, browser PASS с фактической проверкой отсутствия Referer/opener и двойного запуска. Подробности и границы в `../review-report.md`; требования **8 checked / 0 unchecked**.


Четвёртая группа PR-замечаний проверена 2026-09-29: новое действие того же UUID после обновления DOM, общий корпус политики hostname (141 пример), fresh POST с session-bound CSRF и несекретный marker против смены сессии во время позднего ответа — RESOLVED в границах исходников/локальных проверок. Swift 121/0, расширенный серверный набор 143 PASS, browser-epoch PASS. Подробности, покрытие двух issuer/трёх clear-путей cookie и границы доказательств — в последнем разделе `../review-report.md`. Качество требований сохраняется **8 checked / 0 unchecked**.


Пятая группа PR-замечаний проверена 2026-09-29: нормализация выбора native приложения, свежий resolver отдельной notification card с pending/error/cancellation, ограничение preview записей 200 кандидатами до ACL и нейтральный переход к общему списку — RESOLVED. Повторно проверены все production calendar entrypoints; notification host policy делегирована общей и проверена на 141 примере. Итоговый Swift: 269 tests / 8 skipped / 0 failures; server 144 PASS; browser PASS. Причины skips и границы runtime/SHA доказательств приведены в последнем разделе `../review-report.md`. Требования **8 checked / 0 unchecked**.


Шестая группа PR-замечаний проверена 2026-09-29: история восстанавливает подписанный диапазон из cursor через полночь с сохранением scope/TTL/explicit-bound проверок; кабинет использует общую native Join операцию с остальными поверхностями. Оба исправления RESOLVED, новые регрессии PASS. Swift 271 tests / 8 skipped / 0 failures; server 146 PASS. Причины прежних skips и границы SHA/runtime — в последнем разделе `../review-report.md`. Требования **8 checked / 0 unchecked**.
