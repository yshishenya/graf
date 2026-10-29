# T113: восстановление, повтор удалений и чтение объектов до очистки

30.10.2026. F273/T113/#7804, `high-risk-product`, Legacy Impact: `untouched`.
Основа `29d1c67f9d5447228295406054eb4b4ce2583bbe` и локальные изменения.
Это внутренняя стадия [принятого полного оператора](t113-full-operator-design-20261030.md),
не самостоятельный выпуск и не завершение T113.

## Реализация

- [x] `_rehearsal_resources` использует настоящий `rec-db-verify.py`, полный
  custom-format dump, отдельную UUID БД разбора схемы и прежний native inventory.
  Обе цели имеют CONNECTION LIMIT0; обычные роли не подключаются. Права/роли
  источника не ремонтируются. Owner-соединение и Docker проверяют один cluster.
- [x] Native `mc mb/mirror` восстанавливает объекты из закрытой копии с read-only
  mount в UUID bucket. Файлы без ссылок/спецобъектов/hardlinks имеют0700/0600
  и текущего владельца; точные UTF8/NFC ключи не допускают неоднозначного пути.
- [x] Manifest содержит размер и потоковый SHA256 каждого файла/объекта.
  SDK читает все байты, закрывает/releases response, повторяет list/stat/config.
  Versioning/lifecycle/object-lock запрещены. Точность Last-Modified у list и
  HEAD различается: она сверяется до/после внутри каждого метода; key/size/etag
  дополнительно совпадают между методами. Пустой объект и bucket допустимы.
- [x] До yield проверены native schema/roles/RLS/count/states и полный byte
  readback, повторный manifest исходной копии. Внутри контекста caller может
  выполнить пониженные replay/карантин/удаления, COMMIT и новое физическое чтение.
  Согласованность самой копии с текущим live source остаётся отдельным proof
  верхнего controlled export; sandbox её не подменяет.
- [x] Prepare и cleanup имеют одного удерживаемого владельца через повторную
  отмену. Успешное создание фиксирует OID до передачи отмены; неизвестный create
  не даёт DROP по UUID-имени. DROP без FORCE сверяет name/OID и отсутствие цели.
- [x] Для каждого native pg_restore/psql есть отдельный completion marker в
  принадлежащем процедуре container staging. Detached wrapper ждёт child,
  публикует exitcode и digest команды атомарным rename файла0600. Проверка
  отклоняет чужой digest/тип/ссылку/owner/mode/link-count/размер/exitcode.
  Завершение Docker CLI само по себе не доказывает завершения native child.
  Пока marker неизвестен либо не завершена загрузка `docker cp`, PG DB/staging
  сохраняются и готовность запрещена. Общее ожидание ограничено deadline.
- [x] Cleanup ограничивает также SQL identity. Сначала удаляет и проверяет
  отсутствие подтверждённо своих mc containers, затем чистит принадлежащий
  bucket. Неизвестный writer запрещает удаление bucket и оставляет HOLD.
  Cleanup может пережить общий срок ради владения, но не разрешает успех
  после исходного deadline. Нет ready/T0/resume/старта рабочих служб.

## Причинные проверки

Первые25 проверок manifest дали25FAIL из-за отсутствующих функций; затем25PASS.
В тесте SDK исправлена сигнатура S3Error согласно установленной версии, код
не принимает произвольный error как доказательство отсутствия object-lock.
Первая попытка native теста остановилась на настройке собственной Docker-сети,
а не доказала дефект оператора. После исправления стенда выполнено отдельное
сравнение с точными исходниками основы29d1c67f9: native тест падает на отсутствии
`_rehearsal_resources`; текущая реализация проходит тот же сценарий.

Native успех: полный migrated PG17 dump с9 состояниями доставки, известный
account-closure case и2 объекта (Unicode/пустой). Пониженный replay помещает8
намерений в карантин, удаляет1 строку, COMMIT и новый физический readback
подтверждают8 оставшихся строк до удаления целей. Основной source не меняется.

Причинные отказы: ошибка тела, двойная отмена create/cleanup, потерянный ответ
CREATE без удаления неизвестной цели, DROP failure, native schema mismatch после
создания обеих БД, same-size byte corruption, отмена во время живого native child,
потерянный ответ spawn с ожиданием marker, неизвестное завершение с сохранением
PG ресурсов, живой mc после потери attach и ограничение SQL identity в cleanup.
Ресурсы, намеренно сохранённые при unknown/failure, убирает именно владеющий
учебным стендом тест; рабочие данные и чужие Docker-ресурсы не затронуты.

- [x] Итоговый общий профиль fence/operator/drain/replay: **131PASS,
  2 существующих предупреждения,293,26с**, exit0. Три зафиксированных source/test
  SHA256 после окончания совпадают; собственные PG/MinIO/Compose контейнеры
  и сети удалены. Текущая unit matrix manifest содержит30 случаев;
  исторические25RED/25PASS выше относятся к первоначальному выборочному прогону.
- [x] [Независимое ревью зафиксированных source/test hashes](t113-rehearsal-stages-code-review-20261030.md):
  SCOPED PASS. Найденные три границы cleanup/SQL/daemon outcomes устранены
  до итогового профиля; новых установленных блокеров этой внутренней стадии нет.
- [x] Ruff, governance, development-process, changelog-fragments, локальные
  ссылки отчёта и `git diff --check`: PASS.

## Зафиксированные исходники

| Файл | SHA256 |
| --- | --- |
| activation_operator.py | `7230ff0159ed92509cffdaae5408c5a8a4af15a2f5079dfbf1da67f5e46a1f8e` |
| test_activation_operator.py | `487d2d1c19206014ae828a4ae81214c3ba1a552921d8e75889a94934746a07b4` |
| test_activation_restore_replay.py | `013e5e20a8f49eabff8c0bccf52f963545c674f780149a9e1e84609b0df97c0c` |
| Итоговый общий журнал | `134f004e99d37c41797e967b7124a4d8361ae92ac76a5e44f8be3ce34e3de2de` |

Журналы находятся в ignored `.dev/growth/t113-rehearsal-*.log`; исходные учебные
копии/пароли/полные зависимости в материалы доказательств не сохраняются.
Native checks сделаны на локальных изменённых байтах; exact-SHA GitHub CI этим
не подтверждается. [Независимое ревью проекта](t113-rehearsal-stages-design-review-20261030.md)
предшествовало реализации; его117/0 — качество требований, не рабочая приёмка.

## Остаток того же кандидата

Общий trusted initial/backup/verify/actual-restore/resume, durable attempts/
полные immutable комплекты, actual cutover/полное product-state сравнение,
ежедневные retention/access/resource проверки, CD/rollback и принятие паузы
сохраняются в T113. Затем T112 и видимый результат. Shell пока не переключён:
конечный trusted entrypoint должен делегировать эту же процедуру в общем
законченном кандидате. Отдельного keep-target/pass-file/callback/SQL интерфейса,
нового сервиса или зависимости нет. Новых задач и закрытий нет.

Рабочая T0 не установлена; `activation_recovery_unverified` сохранён. Аналитика,
IP, внешние получатели и расписание не включены. Production и GRAF Dev в этой
проверке не менялись; Full/CD/нового PR нет. Техническая учебная проверка не
засчитывается как посещения, новые внешние клиенты либо продажи; AC01–AC06 открыты.
