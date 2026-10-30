# T113: физические соединения предварительной проверки БД

Основа 5501d2ba65ae7d383c511b46bba8ce0a002b0cbb, тот же F273/T113/#7804,
полоса high-risk-product. Это часть принятого полного оператора; рабочий
сервер, GRAF Dev, T0/ready, выключатели и получатели не менялись.

## Реализовано

В runtime preflight теперь удерживаются actual Settings работающих writers,
owner password из exact proc-root bind PostgreSQL и две физические DB-сессии.
Адрес выбирается из двух фактических network views rec-postgres, без DNS/CLI/
host env. Перед connect проверяются закрытые canonical URL и роли служб.
PostgreSQL PID проверяется с UID/GID70, остальные процессы — прежние100/101.

Существующее mapped-file чтение вынесено для двух настоящих потребителей.
Для GRAF сохранены group-read/placeholder/ACL/ancestry/inode/bytes/FD проверки.
Owner leaf проверяется тем же способом, но читается доверенным root operator:
daemon70 не обязан читать mode640 installation group. Права не расширялись.

Source в twobrain_rec сначала проходит существующий readonly verifier grants
и packaged Alembic head в readonly transaction с owner видимостью. Затем
понижается до maintenance, row_security=on и проходит _database_identity.
Owner остаётся в postgres. Каждый actual Settings role URL подключается реально;
проверяются DB/OID/cluster/schema, фактические session/current роли, атрибуты и
отсутствие memberships. Проверенные соединения принадлежат одному контексту,
закрываются до результата, в том числе при повторной отмене и гонке connect.
Внешний результат сохраняет прежние4 поля; DB/secret proofs входят в общий digest.

## Доказательства и пределы

- До реализации: [независимый проект и scoped analyze](t113-database-design-review-20261030.md),
  117 отмеченных вопросов, 0 открытых. Исходный precode SHA-256:
  2ce581a1ecb66110f6750cf58231c7e12bfeb8a4cd28c2bb248c5a1f20cd52a6.
- RED до функций:21 причинный AttributeError по отсутствующему механизму адреса
  и URL. Первая cancellation-проба ожидала event без срока и была прервана;
  это ошибка теста, а не доказательство4 обходов. Тест исправлен конечным ожиданием.
- Профиль operator/bootstrap/fence/provider/config:472 passed,6 skipped,
  два прежних предупреждения. На Mac ACL/memfd skips не повышаются до PASS.
- Native PG17:6/6 на полностью мигрированной собственной БД со штатным bootstrap
  только при подготовке собственного стенда. Operator выполняет настоящий readonly
  _verify_runtime_roles без подмены. Успех; неверный head; лишний media DELETE;
  реальные credentials, приведшие к owner вместо app; лишнее membership;
  повторная отмена во время настоящего pg_sleep. После каждого случая0 backend
  с application_name оператора. Секреты случайные, только временный стенд.
- На Mac native тест перенаправляет только host/port транспорта на собственный
  loopback port. Это не доказательство production bridge маршрута. Выбор IP,
  NetworkID и согласованность двух фактических views проверяет отдельная матрица.
- Собственная механическая PG17-проба подтвердила UID/GID70 и доступность
  pg_control_system() для непривилегированных app/maintenance без новых GRANT.
  Первое противоположное предположение было опровергнуто; продуктовые права
  по нему не менялись. Кластер удалён.
- Гонка failed connect с отменой: отдельный причинный RED на прежнем варианте
  показал OSError вместо исходной CancelledError, затем6/6 GREEN матрицы
  connect/connect failure/одновременный отказ/body/close/close timeout.
  Соединения удерживаются до close; неуспешный close вызывает terminate и отказ.
- Независимый первый [code review](t113-database-code-review-20261030.md) нашёл
  P2: результат verified строился до закрытия DB/secret контекстов, поэтому
  просроченный cleanup мог дать успех. Результат теперь возвращается только
  после обоих выходов и свежей проверки исходного deadline. Два причинных RED
  (DB close и secret close) дали DID NOT RAISE, после правки оба отклоняются;
  cleanup завершается без преждевременного освобождения. Исторический HOLD сохранён.
- Ruff с прежним E721 исключением и whitespace:PASS.

- Linux extraction:38 passed на собственном Linux-томе с настоящими ACL/memfd/
  ancestry/FD проверками. Временные зависимости и том удалены. Этот профиль
  доказывает сохранение shared GRAF extraction.
- Отдельная native owner bind проба: настоящий свой PG17, Linux volume и точный
  file bind; root проверяющий контейнер присоединён только к собственному PG PID
  namespace с SYS_PTRACE для proc-root. PID1 — тот же настоящий postgres UID/GID70.
  Все функции owner/file/process/traversal исполняются без подмен. Leaf mode640
  root:1001 принимается при daemon group70; замена inode Source с сохранением
  прежнего PG bind отклоняется; mode700 настоящего собственного /run/secrets
  отклоняется проверкой traversal UID70. Три результата подтверждены, свой
  PG/runner/volume удалены. Первая probe без --interactive потеряла stdin и дала
  exit1/пустой stdout; она очищена и не считается причинным продуктовым RED.

Общий native product drain/controlled export/Compose stop/full DB preflight:
23 passed на редакции до узкого исправления connect/cancel race.
После исправления повторены6 native preflight сценариев на окончательном коде:
6 passed,17 deselected. Прежние17 drain/export/stop сценариев не затронуты.
В общем профиле два прежних предупреждения. Каждый стенд имеет собственное имя и
очистку; рабочие контейнеры не использовались.

Независимое [окончательное повторное ревью](t113-database-code-rereview-20261030.md)
подтвердило SCOPED PASS этих байтов: P1/P2=0, контрольные суммы трёх исходных
файлов совпали. Все117 вопросов требований перечитаны, отметки117/0 сохранены.
Исторический HOLD первого code review сохранён. Это приёмка данного участка,
а не завершение T113 или разрешение рабочего измерения.

## Открытый остаток

Проверка head и runtime grants не является полной проверкой schema/constraints/
RLS/ledger и lifecycle. Существующий native inventory после coherent backup
остаётся обязательным. Ещё открыты legal/register/local retention/access/
guard/capacity, верхние initial/backup/verify/actual restore/resume, shell/CD/
rollback/daily и T112. Общий bootstrap остаётся HOLD/full_preflight_not_implemented,
activation_recovery_unverified сохранён. T113/#7804 и AC01–AC06 не закрываются.
Подтверждение UID1003, production root запуск и изменения прав сюда не входят.

## Проверенные исходники

```text
activation_operator.py
6c2144a01a4b20a4fa3d89e13ecb54b34fec457cee5f1d2e0d64b27e4c380cef
test_activation_operator.py
80faf87396e21bf1b7640dd3a9633dc7b6e28791ca31a1f6c78f10e82a47bb4c
test_activation_product_drain.py
71265a9098abdeb64e31e21b6f8a998cffb7e53c9b9d1682c8b4a85b09c07f84
```
