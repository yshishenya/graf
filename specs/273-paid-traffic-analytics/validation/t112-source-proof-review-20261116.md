# T112 — независимый обзор source/proof, 16.11.2026

Проверяющий: `/root/public_counter_readiness_review`.
Полоса: `high-risk-product`, неполный изолированный шаг T112.
Основа HEAD: `f8c560c0e8afc5c425b7767613519f33ab3e673c` плюс три рабочих
файла, точные хеши которых приведены ниже. Эти изменения ещё не часть HEAD.

## Решение

**PASS в пределах source-lineage loader и краткоживущего HMAC proof;
P1=0, P2=0.** Блокирующих дефектов в проверенных примитивах не найдено.
Это не приёмка полного T112/T113 и не разрешение включить рабочий сбор.
Четыре ранее принятых списка124/0 повторно не пересматривались.

## Проверка происхождения и SQL

Прочитан целиком `cabinet/result_visibility.py`, оба новых/расширенных
тестовых файла, принятый `contracts/result-visibility.md` и применимые
существующие source/processing helpers, модели и места создания audit.

- Loader требует timezone-aware известные начало периода и `now`, отвергает
  будущий старт. Даты, владелец, workspace, точный meeting/revision/result
  передаются доверенным вызывающим кодом; сама функция не выдаёт этим
  аргументам статус проверенной T113 readiness или действующего principal.
- SQL связывает владельца/workspace/meeting/revision/result/workflow/upload
  и повторно читает объекты через `populate_existing=True`. Нет fallback
  на одну свежую дату, название, revision number или ORM identity cache.
- Meeting должен быть создан после начала, без признаков удаления и с
  неотрицательным deletion epoch. Result/workflow обязаны совпасть с этим
  epoch и выбранной ревизией; проверяется совпадение вычисленного source
  fingerprint с workflow. `source_fingerprint_for_revision()` требует
  accepted/immutable revision, manifest и обязательные корректные digests,
  отвергая неизвестный source kind. Исторический `initial_recording`
  исключён отдельно.
- Применён общий `complete_processing_result_clause()`: штатный imported,
  available transcript/diarization и положительные counts. Неполный
  результат не становится пригодным только из его status или заданного ID.
  Это ещё не проверка непустого фактически показанного текстового блока.
- Сравнения nullable accepted/imported/finalized timestamps и deletion
  epochs в SQL дают отказ при NULL; timezone колонок соответствует aware
  времени. Проверяются нижние/верхние границы нового приёма, финализации и
  импорта. Существующая audit finalization создаётся до присвоения
  finalized_at, поэтому отсутствие ошибочного требования audit≥finalized_at
  сохраняет реальный путь.
- `_has_audit()` коррелирует workspace/meeting/owner/device. Для session
  дополнительно совпадают session ID, время после её создания и revision.
  NULL revision разрешён только для нормальных `session_created` и
  `finalized`: фактические writers именно так сохраняют эти два события.
  Revision-specific `media_revision_upload_session_created` требует точный
  revision ID. NULL actor/device/session не приравниваются к обязательным
  значениям. Схема `UploadSession.device_id` обязательная; встречная
  device-проверка не зависит от текущего устройства просмотра.
- Возвращаемая source-структура содержит только идентификаторы, fingerprint,
  версии/epoch и capture-свойство. Доказанный manual upload даёт `False`,
  остальные допустимые источники — `None`; физический desktop capture и
  внешний статус аккаунта не выдумываются.

## Проверка HMAC proof

- Используется HMAC-SHA256 с отдельным префиксом `f273-result-view-v1` и
  constant-time сравнением подписи. Secret отсутствует в payload.
- Канонический сериализатор включает полную frozen binding-структуру:
  owner/workspace/session/device/meeting/revision/source/result/version/
  deletion epoch/capture/block type/digest/outcome, версию формата и время.
  Изменение любого поля меняет ожидаемый proof.
- Выдача требует известное aware время, secret, допустимый тип блока и
  SHA-256 digest. Proof ограничен1536 ASCII-символами, следовательно байтами;
  неверные символы, подпись, кодировка или размер отвергаются до JSON.
  Проверенный формат одного поля помещается в2KiB body. Реальное ограничение
  тела/неизвестных полей HTTP ещё должен реализовать будущий POST handler.
- После проверки подписи JSON декодируется строго; issued_at должен быть
  именно int, а не bool. Сравнение исходной кодировки с повторно построенным
  каноническим payload отвергает лишние поля, неизвестную версию, иные
  binding, неканоническое JSON/base64 и дубли ключей даже с валидной подписью.
- Возраст<0 отвергается, возраст≥600 секунд возвращает `expired`, без
  принятия события или автоматического продления. Проверка не выполняет
  внешних вызовов, записи или admission.

## Проверка покрытия и пределы

Unit-файл содержит34 случая, включая исходные12 capture-случаев,
round-trip/TTL/будущее время/размер,13 замен binding-полей, malformed input,
разделение домена подписи, неизвестное поле и отсутствующий secret.
Contract-файл содержит38 PostgreSQL-сценариев:3 положительных,34 отдельных
повреждения цепочки и повторное чтение после чужого committed изменения.
Четыре добавленных readiness negatives проверяют transcript/diarization
availability и counts. Сценарии дополнительно удостоверяются, что ledger
не получил ProductActivationMilestone. Fixture использует синтетические
значения, в том числе старую дату самого разговора при новом поступлении.

В этом независимом проходе тесты не запускались, чужая session61404 не
опрашивалась. Заявленные исполнителем RED/GREEN и его текущий полный профиль
не считаются самостоятельным наблюдением reviewer. Заключение получено
чтением исходников и проверкой зависимостей; окончательные журналы запуска
должны быть приложены исполнителем отдельно к тем же хешам.

Loader намеренно не является полной границей полномочий: выбор текущей
разрешённой проекции/закреплённого outcome, проверка действующего аккаунта,
session/membership/access, locks, smoke/internal classification, неизменное
начало T113, свежие основание/отзыв/readiness/resource и request budget
остаются обязанностью будущего доверенного входа. Переданный старый result
ID сам по себе не становится доказательством текущего показанного блока.
Proof также не заменяет серверный расчёт digest из этой проекции.

Render/data-атрибуты/private-no-store, browser/native наблюдение видимости,
обновление истёкшего proof без счёта, защищённый POST, атомарная пара в общей
T113 admission, ограничения body/ресурсов и отказная/конкурентная матрица
пока не подключены. Отсутствие этих частей честно ограничивает шаг и не
трактуется как выполненный T112. Ни egress, ни новый рабочий admission в
проверенном модуле не появились. T113 recovery и действующие отказы не сняты.
GRAF использует Postal; Stalwart не является блокером изолированного шага.

Изменён только этот собственный отчёт. Код, требования, списки, Git/GitHub,
рабочая среда, внешние сообщения и настройки не изменялись проверяющим.

## SHA-256 проверенного среза

| Путь | SHA-256 |
| --- | --- |
| `apps/server/src/twobrain_rec_server/cabinet/result_visibility.py` | `aed1b4172995ce5619d9c9506a537db074679a51ac1e8a2135c3034f81b11d88` |
| `apps/server/tests/unit/test_result_visibility.py` | `eea528f87f2ed95dd92c5b3eba55cc71a02c518c7e6951467d323883df5d36bc` |
| `apps/server/tests/contract/test_result_visibility.py` | `27bd0f0876bc2fbc43a50165abd354d57629309aebce350fb2d35e3643f321ff` |
| `specs/273-paid-traffic-analytics/contracts/result-visibility.md` | `80f7d5eb7cd43bb9e3cff34bf689f9ce01f98095e527cb7afdaf3bca7f864f0e` |
| `apps/server/src/twobrain_rec_server/ingest/media_revisions.py` | `72e5e4a0d4ab6631762c84799b626f594dec7b8f3264b5b9f6f909c19f9e0391` |
| `apps/server/src/twobrain_rec_server/processing/results.py` | `9a5044639b3902a4c4cd577dfc73a1d4b0a282f960b76a24f20ec39e41c8b009` |
| `apps/server/src/twobrain_rec_server/db/models/ingest.py` | `46c814be586c78a69fa31f7bef1e6756dbec2a070f5c1bd9df5ce0714298809c` |
| `apps/server/src/twobrain_rec_server/db/models/processing.py` | `fceefdfc9f1f0c8669a0bdedc744bf24877ef412af8f118f255d6bb0bec7296b` |
