# T112 — границы объёма повторного чтения перед HTTP-подключением

16.11.2026. Основной исполнитель /root, существующие F273/T112/T113.
Основа eea992190c92e57b2cceaa199c2bcbd94ff71614; код не изменён.
Полоса этого документа: read-only investigation / docs-only. Дальнейший
код остаётся high-risk-product с независимым ревью. Это карта подтверждённых
зависимостей и проекта проверки, не новое разрешение, тест или приёмка.

## Вывод из текущих исходников

Клиентский перенос выбора уже реализован и независимо принят: observer
передаёт последнее значение summary_format, а browser также source_result_id;
JSON содержит только proof. Новый формат proof или перенос этих значений
в JSON для подключения сервера не нужны. Сервер обязан заново проверить
недоверенный выбор, штатный доступ и HMAC по свежей общей проекции.

Следующий обязательный участок — ограничение объёма всей аналитической
проекции до её материализации, а не только числа сегментов. Общий getter
читает также связанные календарные записи и предыдущую встречу серии.
Предварительная проверка только текущего meeting_id неполна.
Счётчик строк сам по себе не ограничивает один большой текст/JSON.
Срез исходного idle Pool.close уже принят; новые испытания этого исправления
без новых изменений не нужны.

## Проверенные места чтения

Пути относительно apps/server/src/twobrain_rec_server.

| Чтение | Источник | Что требуется покрыть |
| --- | --- | --- |
| Основные scalar/JSON | cabinet/queries.py:1464, _prefetch_meeting_review_reads | Workspace, current/selected/historical result, revision, workflow, slot/outcome/template, artifact policy, normalization/artifact, upload archive, calendar link, dependency, summary attempt. limit(1) ограничивает строки отдельного выбора, но не размер полей |
| Текстовые коллекции | cabinet/queries.py:1719 | Полные TranscriptSegment и DiarizationSegment выбранного результата до .all(); MeetingSpeakerName всей встречи |
| Итоги | outcomes/service.py:795, load_outcome_items | Все MeetingOutcomeItem выбранного outcome-set, без ограничения числа строк |
| Доступ и панель публикации | cabinet/access.py:948/969 | Полные grants/invitations текущей встречи и UserIdentity получателей; строки приглашения загружаются и при отсутствии ключа расшифрования |
| Календарный roster | cabinet/queries.py:2233 | Legacy CalendarParticipant связанного snapshot без LIMIT; roster snapshot JSON уже загруженного link также требует byte bound |
| Кандидаты календарного контекста | calendar/service.py:1165/1225 | До10 допустимых уникальных candidate UUID; полные CalendarEventSnapshot, CalendarSource, ExternalCalendar и до100 участников каждого. Числовой participant_count не ограничивает размер строк |
| Предыдущая встреча серии | cabinet/queries.py:2145 | Выбранные RecordingCalendarContextLink и Meeting другого meeting_id, затем его latest revision/result/current outcome и проверки доступа. current Meeting fence не является сам по себе доказательством размера этих зависимостей |
| История действий | cabinet/egress.py:2651 и calendar/audit.py:182 | По50 ORM-строк двух журналов; существующий LIMIT не ограничивает текстовые/JSON поля загружаемой записи |
| Проверка источника/артефактов | processing/store.py:1763, cabinet/egress.py:1527 | MediaRevision manifest/digest mapping и TrackArtifact; matching source/ID не ограничивает их scalar/JSON размер |
| Аналитическая привязка | cabinet/result_visibility.py:286/362 | Общие result_view_text_blocks, digest/JSON и load_fresh_result_view_bindings; HMAC остаётся обязанностью нового доверенного HTTP/service пути |

Это проверенная карта названных ветвей, а не утверждение полного транзитивного
покрытия всех возможных ветвей reader. Перед реализацией нужно закончить
точный перечень агрегатов/связей и сверить его независимо.

## Согласованность проверки размера и последующего чтения

Нужен не только размер в момент первого SELECT, но и основание, что reader
не загрузит затем другую либо увеличенную зависимость. Текущий helper берёт
fence текущей Meeting; связанные calendar/global/previous-meeting данные
требуют отдельного разбора. Один main fence не объявляется достаточным
доказательством всех вложенных объектов.

db/session.py:25/29 создаёт engine с pool_pre_ping=True и sessionmaker без
явного isolation_level. Это отсутствие гарантии устойчивого снимка в коде,
не наблюдение фактической настройки рабочего PostgreSQL. Уровень изоляции
сервера в этом проходе не читался. Утверждать рабочий TOCTOU-дефект нельзя:
аналитический HTTP-путь ещё не подключён и preflight ещё отсутствует.

До кода независимо выбрать один полный способ обеспечить соответствие
DB-агрегатов последующему общему чтению: устойчивый снимок, полученный
владельцем транзакции до его первого чтения, либо доказанные ограничения/
блокировки всех конкретных вложенных выборок. Нельзя менять изоляцию уже
начатой транзакции после readiness/auth чтений, считать FOR SHARE защитой
от всех новых дочерних INSERT или добавлять глобальный advisory lock,
который продуктовые writers не используют. Retry после конфликта не вводится.
Нельзя просто исключить календарь/предыдущую встречу из общей проекции либо
обрезать текст ради совпавшего digest.

## Критерии следующего исполнения

1. Размеры/количества считаются на стороне PostgreSQL до передачи больших
   полей/коллекций Python; возвращаются ограниченные числовые результаты.
   Консервативные константы явные и имеют граничные проверки; они ограничивают
   только аналитику, не показ продукта, не становятся новым флагом T113.
2. Проверяются и многие строки, и одна большая scalar/JSON строка, включая
   вторичные таблицы. Spy на общий reader подтверждает ранний отказ до
   материализации. Положительный обычный/pinned/selector путь сохранён.
3. Детерминированная конкурентная замена вложенной зависимости между
   preflight и reader не может обойти ограничение. Новый контекст и его
   snapshot/locks проверяются по реальным writers; неизвестность закрывает
   аналитику, не продукт.
4. Общий исходный двухсекундный POST срок, body2048/proof1536, штатные
   Principal/WebTenant/WebCSRF, fresh owner/session/source/gate и один общий
   commit остаются. Timeout SQL сам по себе не ограничивает synchronous
   JSON/digest после получения данных. После них проверяется остаток времени.
5. Только затем подключаются общий result_views router, GET/HTMX enrichment,
   valid/expired renewal и атомарная пара в общем service owner. Matching
   expired даёт0 INSERT/0 provider; proof/accepted — только после успешного
   выхода owner. Настоящий _result_period_context остаётся закрытым до T113.

Это конкретизация существующего t112-http-preflight §«Ограничение большой
проекции», не изменение требований или новая задача. T112/T113 и issue7698
остаются открытыми; дополнительные дубли в tasks не нужны.

## Версия и отсутствие побочных действий

| Источник | SHA-256 |
| --- | --- |
| cabinet/queries.py | cf0e7b622c60e53513df78140ddf2d2ab74937a55a15ce7c719de56fa14f50da |
| cabinet/result_visibility.py | b59aa36240282748ed88696e1cfee04710302364ce9df9f2b5fc3315fdedb5e7 |
| calendar/service.py | 5c81afc11964c63314c1dcdafd381c594ed6f8081141117afb63ffd033c8fb84 |
| cabinet/egress.py | 4f31ab02b410938596a0fde2c4085ec31e0b4e6b1944db23607036f0fe380e40 |
| cabinet/access.py | b4c055f84f8e8f51500e96468d20b01c72125aa19e910b43297a93b7677100bc |
| validation/t112-http-preflight-20261116.md | 9d25134784ec51a1eab528e609ed4f5d38df10af7e44870fbcdecaa29d8304d2 |
| validation/t112-view-selectors-review-20261116.md | d4d91ec375a2c9875d102ba8776edede1d00b89a38489d3b9fd40015567690bc |

Это чтение исходников. Новые tests/DB/HTTP/browser/native не запускались;
старые257/2/294 не повторялись. Runtime, сайт, контент/вёрстка, почта,
nginx/DNS/Compose, данные, рабочий сбор/T0 не менялись. Новый код, PR,
merge/выпуск и внешние публикации не создавались.
