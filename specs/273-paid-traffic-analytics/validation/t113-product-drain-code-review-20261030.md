# T113: независимое ревью кода двух шагов product drain

30.10.2026. Проверяющий `/root/f273_release_boundary`, исполнитель `/root`.
Основа `40a8be0161fa3cbd12373381506dca2bb6cca62a`, high-risk-product.

## Текущий вывод

**SCOPED PASS кода и локальных причинных проверок двух шагов product drain.**
Оставшихся блокирующих дефектов прочитанной реализации не найдено.
Три файла заморожены исполнителем на контрольных суммах ниже; после полного
чтения повторная проверка хешей подтвердила этот же снимок. Прочитан финальный
журнал исполнителя: **62 passed,2 warnings /27.57s**. Ревьюер тесты/сборки/
подключения не запускал. Ранние21PASS не выданы за результат последнего снимка.

Это узкая проверка соответствия двух шагов принятому проекту; незавершённый
верхний initial/full restore operator ей не подменяется.

Полностью прочитаны `activation_operator.py`, оба профильных файла тестов,
повторно соответствующие части существующего activation_fence, Compose и
настоящего CD. При чтении код/тесты менялись исполнителем; оценка ниже
относится к контрольным суммам в конце, а не ко всем промежуточным версиям.
Новый модуль не имеет CLI, ready/initial writer, actual restore/swap/resume,
не создаёт T0, не снимает unconditional recovery blocker и не запускается
самопроизвольно из API/CD.

## Проверенные границы

| Область | Вывод по коду |
| --- | --- |
| EX/revoked | `_revoked` требует exclusive, проверяет реальные directory/lock inode через существующий fence, закрытый файл и точные поля/status/reason/mode/dev/ino. Оба публичных шага проверяют его до subprocess/SQL; stop повторяет перед stop и после metadata, DB перед ALTER и перед возвратом. |
| Docker inventory | Проверяются полные ID, уникальность service/container, expected project, oneoff=False, точные status/flags/PID/exit, две собственные сети с project labels/internal flags/ID, точная membership. Чужой активный endpoint не принимается по известному имени роли. Env/Cmd не считываются, stderr CLI не публикуется. |
| Матрица | Обязательны три runtime writers, migrate/minio-init и postgres/minio/temporal. Два operations writers могут отсутствовать/быть created с PID0. Bootstrap отдельно optional, но присутствующий допускается только exited0 и не oneoff. Ни отсутствующая служба, ни failure не приводят к созданию/старту. |
| Остановка | Одна команда compose stop только присутствующих writers фиксированного списка. После проверяются тот же service→ID, ID сетей и набор network keys; созданные/исчезнувшие/заменённые containers приводят к отказу. Один deadline120с перед первым subprocess используется во всех командах. |
| CLI lifetime | Отдельный владелец охватывает spawn/communicate/finally. Shielded spawn извлекается и при отмене до получения child. Собственный CLI terminate→при необходимости kill→communicate/reap. Повторная отмена внешнего ожидателя не отменяет cleanup owner. Контейнерные kill/start/restart не добавлены. |
| DB вход | Строгое имя/не template/postgres, целый положительный OID/cluster format. Проверяются отсутствие активной transaction, source name/OID/cluster/session/current/row_security и все пять role flags, owner postgres/session=current/superuser/cluster. |
| Source gate | ALTER выполняется owner-соединением вне transaction, подтверждается OID/false. Неопределённая ошибка/timeout не продолжают процедуру. Нет ALLOW_CONNECTIONS=true, terminate-backend или автоматического rollback/start. |
| DB drain | Session EX273,3 через try-lock, затем metadata autocommit со сбросом статистического snapshot. Считаются все другие PID данного OID и все prepared текущей DB, без фильтра по роли/типу и без query text. Перед metadata PASS повторены identity/closed/revoked. |
| Deadline/lifetime | Один DB timeout_at охватывает первый identity SQL, ALTER/ACK, advisory loop, metadata и финальные проверки. Код не закрывает source и не отпускает EX lock; caller продолжает владеть ними до экспорта/закрытия, включая error/cancel. Это локальный договор helper, не доказанный полный верхний оператор. |
| Вывод/ошибки | Возвращаются только метаданные DB drain/service IDs. Ошибки драйвера/неизвестного SQL превращаются в конечный HOLD-код без connection/SQL/private text. CancelledError передаётся отдельно. |

## Исправления, проверенные в ходе ревью

1. **Bootstrap.** Ранняя версия делала rec-db-runtime-bootstrap обязательным.
   Проверенный CD:1270 использует `run --rm --no-deps`; исправленная матрица
   проекта принята отдельным design review. Код теперь вычитает
   OPTIONAL_INITIALIZERS из обязательного множества. Прямой bootstrap_absent
   testcase добавлен. Отсутствие не выдаётся за проверку истории ролей/схемы.
2. **Фактическое имя Postal network.** Ранняя версия сравнивала логический ключ
   `postal-network` с ключами Docker inspect, где действующее имя по Compose
   `postal_postal-network` либо настроенное TWOBRAIN_POSTAL_DOCKER_NETWORK.
   Это блокировало бы штатный inventory. Код теперь получает проверенное
   фактическое имя отдельным обязательным аргументом и преобразует только этот
   логический ключ. Прямые тесты используют default/custom имена при неизменном
   SERVICE_NETWORKS; старый логический аргумент на таких metadata отвергается.
   Поэтому регрессия не скрыта только учебным monkeypatch таблицы.
3. **Имена и владение учебных сетей.** Native Docker fixture использует
   собственный UUID-project/сети и labels, не присоединяется к локальным
   рабочим fixed network names. Конкретные имена заменяются только внутри
   теста; это не новый рабочий параметр для обхода private network проверки.

## Причинность прочитанных тестов

Unit-профиль проверяет матрицу good/optional absent/created/bootstrap absent,
required absent/created, dead/removing, failed initializer, duplicate,
foreign/wrong network и oneoff. Настоящая stop-функция вызывается через узкую
fake-command границу с проверкой argv, service set, неизменности ID и отказа
без subprocess при shared fence. Fake-данные не объявлены настоящим Docker.

Отдельные реальные Python child cases: timeout, cancel twice, timeout во время
spawn и cancel во время spawn. Задержка TERM даёт время повторной отмене;
после завершения ожидателя os.kill(pid,0) должен получить ProcessLookupError.
Отдельный тест оставляет150мс от исходного DB budget и тормозит первый identity
SELECT: ALTER после исчерпания периода недопустим. Подмена времени относится
только к модулю оператора, clock asyncio не меняется.

Native PostgreSQL17 fixture использует отдельный tmpfs-кластер и UUID DB,
проверяет late PID, настоящий SH advisory xact, prepared transaction при
0 других PID, отмену, неверный cluster и активную transaction. Timeout
сокращает только исходный deadline до500мс; unknown ALTER выполняет реальный
ALTER, затем намеренно теряет подтверждение. Prepared fixture разрешает
подготовленную transaction только после наблюдения реального0PID/1prepared;
привилегированный RESET используется исключительно управляющим кодом теста.
Он не добавлен в production replay/drain.

В учебном кластере отдельно выдаётся EXECUTE pg_control_system maintenance:
это подготовка собственной роли fixture, не новая рабочая grant-операция
модуля. Тест не доказывает наличие прав рабочей роли; ранее переданная
read-only host probe и будущий полный verifier остаются отдельными основаниями.

Native Compose fixture вызывает настоящую stop-функцию и настоящий Docker
stop на своих процессах sleep. После должны остановиться writers и остаться
работающими три инфраструктурных контейнера; это проверка механики остановки,
не запуска настоящего GRAF. Cleanup проверяет ownership labels, выполняет
compose down и отсутствие своих контейнеров/сетей. Рабочие names не используются.

Финальный ignored журнал `.dev/growth/t113-product-drain-final.log`
прочитан целиком:62PASS/2warnings/27.57s, SHA-256
`519d80b8c60fd758fbcf58f6bd5c2fdd2ab686e7b78252527faedeb179e2b03e`.
Журнал содержит итог pytest; соответствие полного выбранного профиля и
замороженных трёх файлов подтверждено исполнителем в сообщении передачи.
Два предупреждения касаются уже импортированного pytest fixture и deprecated
Starlette/httpx; падений в журнале нет. Ruff трёх файлов PASS и отсутствие
собственных контейнеров/сетей после запуска сообщены исполнителем отдельно;
ревьюер не выполнял свой Docker inventory и не выдаёт это за самостоятельную
повторную проверку. Cleanup assertions находятся внутри прочитанных native
fixtures; успешный профиль не обходит их.

Четыре checklist SHA-256 повторно совпали с принятым снимком:16/45/27/29,
всего117 `[x]`/0 `[ ]`; отметки ревьюер не менял.

## Ограничения

117/0 checklist — качество требований, не приёмка этого кода. Финальный
initial verifier, полный actual restore/rollback и их независимый precode gate,
правовой/операторский запуск, T112/T113 целиком, T0, CI/PR/release, органический
трафик и продажи не объявлены выполненными. Нет вывода о полном отсутствии
гонок во всём будущем операторе на основании тестов этих двух шагов.

## Контрольные суммы

| Файл | SHA-256 |
| --- | --- |
| activation_operator.py | `9927e66cc96731b723c8a9689cbb65ec2f2a72af1fd157de2ef2b055504931a2` |
| unit/test_activation_operator.py | `4f59426ba2d4bd018b61fdd47d229603b8826e9254cd8941741ae79c764497c3` |
| integration/test_activation_product_drain.py | `4d0223b522cc8ec69ef14e005109e25a0e1eadc948f0b335548a0ce10abb2f1d` |
| product-drain design | `301a53f7e1fb7fce6251c8401c45487793d0013468c8dfca68c7d38b41e48cfa` |
| final pytest log | `519d80b8c60fd758fbcf58f6bd5c2fdd2ab686e7b78252527faedeb179e2b03e` |
| Compose | `9098cb15c8c4a675beae529664e128d46a2dc50671dee8171d05b659b482bcc6` |
| CD runtime | `86c88314db12f9f10423b5e38c44c4682092c358f521ac590b4e12e9539b0d35` |

Последующие правки исходника/тестов потребуют перечитать затронутые участки
и проверить новые журналы. Ревьюер изменил только разрешённые design/code
отчёты, не менял code/spec/plan/tasks/checklists/Git/GitHub/runtime и
сохранил чужие правки.
