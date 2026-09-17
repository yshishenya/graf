# Research
- Decision: icalendar 7.3.0 + recurring-ical-events 3.8.2. Stdlib has no RFC recurrence engine; installed deps absent. Isolated test confirms RRULE/EXDATE/moved and cancelled RECURRENCE-ID with TZID. Use bounded between(), derive recurring UID from ORIGINAL components because library assigns recurrence ID to nonrecurring events too. Cancelled override without DTSTART uses its RECURRENCE-ID with original TZID; id-only series deletion separate.
- Decision: Google id-only cancellation is deletion ID list in CalendarEventPage. It never needs fabricated start/end; atomic apply with events/cursor.
- Decision: native one-minute scheduler for both providers, 30-second UI GET refresh; no Google watch/webhook infrastructure for present scale. Honor provider rate failures with bounded retry and last finish interval.
- Decision: existing last_sync_started_at is a claim token checked under row lock before publication; reclaim after five minutes. Selection/disconnect invalidates claim. Late old exception handler must also compare claim.
- Decision: owner data retains privacy classification but display is based on actual content availability. Existing private auto-context guard is independent of owner display. Full source text with URL passcodes remains encrypted in existing extras envelope and decryptable only on owner read. Do not broaden third-party sharing.
- Decision: current provider catalog always refreshed in sync, selection retained by stable calendar id; missing calendar de-selected, no auto-select of newly discovered calendars.

## Итоговые уточнения реализации
- Библиотечные `after()`/`paginate()` всё равно раскрывают набор повторений внутри `dateutil` до первого результата. Для старого `FREQ=SECONDLY` одного временного окна недостаточно. Разбор целого REPORT выполняется отдельным процессом с завершением по времени, ограничениями CPU/памяти в Linux и атомарным возвратом результата. Ресурс не усечён молча; неполный импорт не публикуется.
- Контейнер rec-maintenance ограничен 512 MiB; процесс разбора ограничен 256 MiB адресного пространства, чтобы оставить память родителю. Изолированный импорт календарного пакета на Linux занимал около 110 MiB адресного пространства до parser dependencies.
- `last_sync_started_at` остаётся идентификатором захвата. Проверка требует неизменённого захвата, active source и sealed credentials как для результата, так и для ошибки; disabled_by_policy тоже останавливает публикацию.
- Google сохраняет время последнего полного импорта в capabilities и раз в сутки продвигает окно. Хеши ссылок хранятся отдельно от порядка приоритетных ссылок открытия.
- Общее чтение encryption key переиспользовано в worker. Удалены повторное немедленное чтение каталога после успешного подключения и его синхронные обёртки.
- `all_day` добавлен в owner API и UI; в Swift поле опционально для ответов старого сервера. Дата целодневного события отображается без преобразования в другой часовой пояс.
