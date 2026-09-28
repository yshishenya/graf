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
