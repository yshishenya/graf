# T113: фактический охват кластера PostgreSQL — 31 октября

Основа `521670ddc1db2b9db25bcf987d622034a54a4248`, T113/#7804,
`high-risk-product`. Это чтение установки и конкретизация проекта J2 из
[независимого разбора](t113-installed-jobs-design-review-20261031.md).
Код, задания, настройки, права и данные сервера не менялись. Запросы к
каталогам выполнялись в `BEGIN READ ONLY`; продуктовые строки не читались.
Это не законченный runtime verifier и не разрешение T0.

## Наблюдение

В 12:04–12:07 UTC получены метаданные PostgreSQL 17.8 (`170008`):

| База | Подключения | Шаблон | Расширения |
| --- | --- | --- | --- |
| `postgres` | разрешены | нет | `plpgsql` 1.0 |
| `template0` | запрещены | да | содержимое не читалось |
| `template1` | разрешены | да | `plpgsql` 1.0 |
| `temporal` | разрешены | нет | `plpgsql` 1.0 |
| `temporal_visibility` | разрешены | нет | `btree_gin` 1.3, `plpgsql` 1.0 |
| `twobrain_rec` | разрешены | нет | `plpgsql` 1.0 |

Все шесть имеют владельца `twobrain_rec`, connection limit −1. Во всех пяти
доступных базах `shared_preload_libraries`, `session_preload_libraries` и
`local_preload_libraries` пусты; `dynamic_library_path=$libdir`; для этих
параметров `pending_restart=false`. Переопределений этих четырёх параметров
в `pg_db_role_setting` нет. Пять доступных баз не имеют проверенных схем
`cron`, `pgagent`, `timescaledb_information`, `_timescaledb_config` и
`_timescaledb_catalog`. Это ограниченная проба имён, не доказательство всех
косвенных исполнителей.

В `postgres`, `template1` и `temporal` нет пользовательских routines. В
`temporal_visibility` их 88: 87 принадлежат расширению `btree_gin` через
`pg_depend`; их C-library — `$libdir/btree_gin`. Ещё одна — штатная
`public.convert_ts(varchar)`, 55 байт тела, MD5
`3385398bbbc83e4d82f672d29a6cfa60`. Она преобразует временную строку в UTC;
декларация прочитана в схеме из действующего `temporalio/auto-setup:1.27.2`.
SHA-256 всего прочитанного packaged schema:
`efaee50f1feb7ba84bf9b97fcd8badc788f039a265284aebd0298e3b1a7eb369`.
Совпадение одного MD5/числа 87 не является runtime проверкой определения.

В четырёх непродуктовых доступных базах проверены четыре обычных языка
`c/internal/plpgsql/sql`, отсутствие event triggers, foreign wrappers и
foreign servers. Полный ожидаемый каталог GRAF продолжает проверять уже
существующий reader; новым наблюдением его приёмка не заменяется.

Закрытую `template0` не открывали. Отсутствие её подключений, prepared
transactions и фонового исполнителя в этой пробе ещё не проверено.
Доказательства сохранены локально как закрытые метаданные
`.dev/growth/t113-cluster-{metadata,catalogs,routines}-20261031.json`.

## Конкретный проект J2 для следующей реализации

Поддерживается именно этот конечный набор шести баз PG17, а не произвольный
кластер. Проверка входит в существующий `_runtime_databases` полного оператора,
до понижения source-роли и перед конечным допуском. Это не отдельный CLI,
сканер SQL или supplied PASS-файл.

1. Уже привязанный owner в `postgres` читает `pg_database`, cluster ID,
   `SHOW data_directory`, preload/settings и все `pg_db_role_setting`.
   Набор имён, owner, template flags, locale/encoding и supported connection
   state проверяются полностью. OID входят в текущий digest, но не зашиваются
   как вечные значения. Неизвестная/лишняя/недоступная база — HOLD.
2. Для пяти доступных баз используются отдельные физические read-only
   подключения к тому же фактическому endpoint с конечным общим deadline.
   Проверяются current DB/OID/cluster/PG major и эффективные четыре параметра,
   включая отсутствие pending restart и role/DB overrides. Каталожные запросы
   квалифицируются `pg_catalog`, пользовательские функции не исполняются.
3. Непродуктовый эталон мал и явен: `plpgsql` 1.0 в `pg_catalog`; только в
   `temporal_visibility` допускается дополнительно `btree_gin` 1.3 в `public`.
   Полная metadata/definition/dependency closure расширения сравнивается с
   независимо снятым чистым экземпляром того же закреплённого PG image с
   единственной штатной `CREATE EXTENSION btree_gin`. Closure охватывает все
   extension objects/dependencies, не только routines: сравниваются полные
   нормализованные object identities и определения, не случайные OID чистого
   экземпляра. Одного имени, self-hash,
   количества 87 или значения `probin` недостаточно. Единственная остальная
   routine `convert_ts` сравнивается целиком с конкретной декларацией из
   закреплённой Temporal schema, включая owner/ACL/language/config/attributes.
   Иных user routines, triggers, rules, event triggers, FDW/server/languages
   и scheduler namespaces у непродуктовых баз не допускается. Каталог GRAF
   проверяет существующий exact reader, а не новый сокращённый эталон.
4. Для `template0` не меняются `datallowconn` или права: требуется известный
   closed-template state, ноль подключений/prepared transactions, пустые
   cluster preload/overrides и отсутствие неизвестных background workers.
   Это доказательство невозможности исполнения в поддержанной конфигурации,
   не заявление об отсутствии каталогов внутри закрытой базы. Неизвестный
   backend, preload или состояние даёт HOLD. Доверенные ручные root/SQL
   действия остаются прежней границей, а периодические jobs проверяются J1.
5. Базовый набор — эти шесть баз. Во время своего rehearsal полный оператор
   дополнительно допускает ровно собственные уже доказанные UUID/OID targets
   текущего run под тем же deployment lock. Цели проверяются штатным exact
   native restore/replay путём; после cleanup их нет. Отдельно учитываются
   сохранённые closed prior DB после принятого actual restore из
   [полного алгоритма](t113-full-operator-design-20261030.md#actual-restore--schema-runtime-rollback).
   Их конечный набор выводится только из фактически прочитанного trusted
   fsynced actual-run state с доказанным switch/complete, cluster/OID/old-source
   binding и неизменной T0. Каждая prior DB обязана иметь именно прежний OID,
   owner, non-template, ALLOW_CONNECTIONS=false, limit0, ноль PID/prepared;
   её исходный native/catalog digest связан с принятым run. Незавершённый или
   неизвестный switch запрещает ready, а не расширяет разрешённый набор.
   Ни current target, ни retained prior не разрешаются одним prefix. Полное
   перечисление current-run targets и retained prior добавляется к базовым
   шести и проверяется до/после; лишний/потерянный/подменённый объект — HOLD.
   До первого actual restore retained-набор пуст. Prior не удаляются cleanup
   репетиции: их удаление отдельно после приёмки восстановления; lifecycle и
   обязательные решения об удалении охватывают их как сохранённые копии.
   Неизвестный охват такого решения закрывает допуск, срок не сбрасывается.
6. При controlled drain закрытая `twobrain_rec` читается только через уже
   удержанную reduced source без reconnect. До её понижения уже снята
   cluster-проверка; перед ready её текущий source catalog и остальные
   доступные DB проверяются снова, с ожидаемой закрытой фазой только своей
   DB. Любая иная смена inventory/settings/catalogs/cluster между стадиями
   закрывает успех. Digest включает фактические cluster/DB OID, image/source,
   settings и полные принятые каталоги; наружу не выходят определения/строки.
   Обычные PID/ticks/число активных Temporal clients не включаются в стабильный
   digest. Перед/после заново проверяются допустимые backend types, closed
   DB activity/prepared=0 и отсутствие неизвестного фонового исполнителя;
   разрешённая смена клиентских сессий не становится ложной подменой каталога.

## Что не принято

Эталон чистого `btree_gin`, полная сверка `convert_ts`, locale/encoding,
background/prepared coverage и собственно реализация ещё не выполнены.
Независимый reviewer должен повторно разобрать этот проект J2 до кода.
J1 — весь host scheduler/indirect closure — остаётся отдельным открытым
проектным пробелом. Срез не снимает `full_preflight_not_implemented`,
`activation_recovery_unverified`, ресурсный HOLD или открытые T112/T113.
Рабочие T0, трафик и продажи не заявляются.
