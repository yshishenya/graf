# T113: конкретный верхний оператор initial / verify / restore

Основа a241f34b8832b3b0ed83409f25d55853e7cb3e56, тот же F273/T113/#7804.
Это полный алгоритм следующей реализации, не разрешение рабочего запуска.
До кода нужен независимый precode review, включая117 требований и scoped analyze.
Не создавать новый framework, роль, гранты рабочего сервера, HBA, сервис или
контейнерный IPC. Использовать доверенный host uv/Python3.13/frozen lock и
существующие backup/inventory/restore/replay/retention/guard средства.

## Команды и доверие

Один модуль activation_operator.py получает операторский CLI initial/backup/verify/restore.
Он принимает проверенный root и режим; не принимает ready/pass JSON, SQL,
подменяемый callback, дамп с произвольным digest или новый cutoff. Конфигурация
постоянного activation path, UID, PostgreSQL и Compose берётся из одной текущей
установки. Интерактивный пароль/секрет в argv/лог не передаётся. Полный raw
operator register читается только на сервере из закрытого файла; в Git/выводе
только metadata/digest. Никакого source URL/password/owner engine в replay.

Доверенная граница — проверенный код оператора и уже существующий superuser
этой установки. RESET SESSION AUTHORIZATION технически обратим; sandbox не
обещается. Службы runtime доказанно не superuser/bypass/inherit и без memberships.
Ручные параллельные root/SQL/restore в обход оператора вне гарантии, как в договоре.

До мутаций: проверяется реальный running image ID/source SHA каждого writer,
immutable source/uv.lock/package head, точный Compose project/фактическая postal
network, закрытая конфигурация, место/бюджет, текущие роли/схема и все входы.
Нельзя устанавливать зависимости после остановки. Образ не выводится только из
строки environment: pinned image ID и встроенный source сверяются с release-images
и фактическим Docker inspect. Отсутствие/неизвестность любого входа — HOLD до stop.

## Владение ресурсами

Верхний процесс владеет существующим deployment lock, затем filesystem EX.
Durable revoke предшествует stop. Один owner task включает все DB/CLI children
и cleanup; ожидатель shield-ит его до окончания даже при повторной отмене.
Отмена не создаёт успешный результат. Никакой EX не отпускается до разрешения
отправленных DB-операций и закрытия принадлежащих соединений; после ошибки actual restore
source остаётся закрытым, writers остановлены. У planned backup отдельное
безопасное завершение ниже; обычная деградация аналитики не останавливает продукт. Неизвестный Docker daemon
outcome не превращается в разрешение следующей операции. Deployment lock не
обходится env-флагом от произвольного CLI caller.

Проверенные stop_product_writers/drain_product_database переиспользуются.
Фиксированные120с/30с остаются пределами соответствующих шагов. Полная операция
имеет конечный операторский предел600с, включающий export/rehearsal/replay;
каждый child получает остаток, никакой новый600с retry. После исчерпания срока
cleanup может занять больше времени ради владения ресурсами; успех запрещён.
Новая попытка не меняет уже выделенный T0 и не стирает anchor.

## Полная копия после drain: конкретное решение ограничения PostgreSQL

ALLOW_CONNECTIONS=false запрещает даже pg_dump владельца. Поэтому после
проверенного drain допускается **явная export-фаза того же оператора**:

1. Источник уже false/0 чужих PID/0 prepared, source maintenance держит session
   EX273,3. Все writers остановлены. Исходный datconnlimit читается до изменения.
2. Owner в postgres ставит CONNECTION LIMIT0, подтверждает его и лишь затем
   ALLOW_CONNECTIONS=true. Обычные app/maintenance/media подключения по-прежнему
   не допускаются; новые trusted owner connections нужны только штатному backup.
   Это временное разрешение владельцу, а не прежнее обещание запрета всех
   подключений в export-фазе. При любой ошибке owner закрывает false перед выходом.
3. Существующий backup-rec-stack.sh делает custom dump/schema/inventory из своего
   единого exported RR snapshot и полную копию MinIO. Product writers не запускаются.
   Host/source/session EX не освобождаются. Не менять в этот момент role grants.
4. Закрыть ALLOW_CONNECTIONS=false, проверить OID/limit0; дождаться всех прочих
   source PID/prepared без исключения backup/application_name. Только после
   подтверждённого завершения backup CLI и этого drain продолжать. Неизвестный
   child/SQL результат — HOLD, без использования частичного архива.
5. Источник остаётся false/limit0 до явно успешного resume. Исходный datconnlimit
   восстанавливается только при последнем успешном resume, непосредственно перед
   ALLOW_CONNECTIONS=true. Автоматического открытия при исключении нет.

Нативная собственная PG17 проба13/13 подтвердила: app/maintenance denied при
limit0; штатный pg_dump с exported snapshot reduced-сессии; native restore;
сохранность session EX после COMMIT; false/0PID после export и новый reduced
readback target. Кластер удалён. Это доказательство механизмов, не full operator.
Пока **не** проверены в этой пробе existing backup shell + lifecycle/recovery
cancellation и fallback false после неизвестного ALTER; они обязательны в коде.

## Initial: однократный T0 без восстановления старой маркетинговой истории

Постоянный inode activation.lock должен иметь доказанное первичное состояние
при provisioning этой фиксированной установки. CLI не создаёт новый каталог/
lock вместо потерянного. Для различения никогда не начатого периода и потерянного
initial используется небольшой marker **в том же inode**, без нового cutoff:
точный versioned never_started либо attempted + SHA256 единственного initial.
Непонятный/пустой/частичный marker запрещает initial. Provisioning создаёт его
только одновременно с первым постоянным lock через O_EXCL в новом защищённом
каталоге; не ремонтирует существующее неизвестное состояние по пустой DB.
Runtime остаётся read-only; запись marker разрешена только владельцу EX, открыв
тот же проверенный inode без замены. read_ready сверяет marker digest с initial.

1. Полный preflight → deployment EX → filesystem EX/revoke → stop/drain → export
   полного текущего backup по фазе выше. Проверяются backup artifact checksums,
   полные роли/RLS/constraints/columns/trigger/schema/ledger inventories, текущая
   packaged revision, grants и отсутствие скрытого RLS охвата.
2. Полная репетиция использует внутренние стадии штатного rehearsal, описанные
   ниже; обычный вызов shell до PASS не используется как подготавливающая стадия.
   UUID DB/schema DB/MinIO bucket, native schema canonicalization и metadata
   comparison выполняются до yield. До cleanup внутри того же владельца
   ledger/replay проверяется свежими reduced-сессиями: полный source
   closure snapshot и актуальный v2 disposition register; все accepted/completed/
   overdue cases имеют точный результат/срок и полный охват, failed/unknown — HOLD.
   Target quarantine + точные ledger удаления в одной transaction, после COMMIT
   новая физическая reduced-сессия сверяет полный ожидаемый ledger. Пустой рабочий
   ledger не заменяет отдельные непустые учебные случаи, уже проверенные T113.
3. Не делать synthetic-only CLI restore_replay.py доступным рабочим именам.
   Переиспользуются его внутренние database_context/closure_snapshot/replay_accounts/
   ledger/expected_ledger/verify_ledger и общие DELETE/quarantine через отдельные
   уже пониженные one-use connections. Owner factory replay не видит. Проверенный
   закрытый snapshot не принимается от внешнего caller как pass-file.
4. Полный GRAF backup включает DB и объекты. Существующий MinIO mirror сам по
   себе не доказывает обратное чтение байтов: на owned restore bucket нужны
   чтение восстановленных объектов и сравнение их полного закрытого manifest с
   backup, включая пустой/неполный/лишний/повреждённый объект. Ключи/контент только
   во временном закрытом staging на сервере. После проверяется очистка всех owned
   DB/bucket/staging, без удаления рабочего архива. Cleanup fail — HOLD.
5. После очистки повторные current binding/closed/0PID/prepared/EX/revoked,
   полный source RR snapshot текущего ledger/closure/category disposition и
   текущие основания/раскрытие/access/until_decision/resource checks. История
   маркетинга до T0 не проверяется; текущее состояние и обязанности проверяются.
6. Только теперь PostgreSQL clock_timestamp() задаёт T0; в том же закрытом
   source snapshot проверяются все user_identities.created_at: NULL/будущее >T0
   запрещает старт. Нет новых writers. history_proof_sha256 хеширует T0/binding/
   текущие schema/roles/ledger/lifecycle coverage digests и результат этого счёта,
   без списка клиентов. Все post-T0 события до initial отсутствуют по построению.
7. Начальный JSON формата INITIAL_FIELDS строится из этого результата. Перед
   созданием marker в том же lock inode необратимо меняется на attempted+digest,
   fsync. Затем initial.json создаётся только O_CREAT|O_EXCL|O_NOFOLLOW0600,
   fsync файла/каталога; bytes/digest/marker снова проверяются. Неопределённая
   запись/потеря initial после attempted — HOLD без нового T0. Начатый initial
   не перезаписывается; нет fallback на текущий clock или пустой ledger.
8. Ready формата READY_FIELDS создаётся atomic replace/fsync только после
   собственных выполненных проверок, затем читается штатным read_ready на
   фактическом expected binding. Никакие произвольные supplied hash/"pass" не
   считаются выполненными проверками. started_at всегда из одного initial.
9. Только успешный resume: проверить неизменные image/config/IDs и актуальные
   gates, закрыть все source/target sessions, восстановить исходный datconnlimit,
   открыть source, запустить только раньше running writers через compose start
   (не up). Проверить те же ID/images/config/healthy. Ready остаётся недоступным
   admission до отпускания filesystem EX. Ошибка start/health → revoke/stop/
   closed/HOLD, initial и T0 не меняются. Если первоначально служба была exited,
   оператор не маскирует это автоматическим её запуском.

## Один staged rehearsal без произвольного hook

Существующие native restore/schema/inventory/MinIO стадии shell переносятся
без изменения содержания в один внутренний async contextmanager
`_rehearsal_resources` в activation_operator.py (stdlib-only). Prepare выполняет
UUID create/ownership → pg_restore → schema parse в отдельной UUID DB → native
capture/compare → bucket create/mirror. После этого yield выдаёт только внутреннему
доверенному caller имена owned targets и private staging; full operator выполняет
reduced replay/fresh readback и полное чтение байтов **внутри** async with, до finally.
Общий finally проверяет удаление только подтверждённо owned DB/schema/bucket/staging.
Standalone shell сохраняет --remote/--execute/dry-run и конечный cleanup; execute
делегирует тот же stdlib Python entrypoint, который выходит только после finally.
Нового keep-target, pass-file, callback, supplied SQL/command или IPC нет.
Административные проверки pg_database/создание/удаление идут через postgres;
к закрытому twobrain_rec cleanup не подключается. Creation cancellation сохраняет
правило: сначала известный успешный create и ownership, затем обработка отмены;
неизвестное создание никогда не разрешает удаление объекта лишь по UUID-имени.
Все дочерние CLI удерживаются до reap; повторная отмена не обрывает cleanup.

Deployment lock удерживается одним in-process владельцем. Если standalone shell
передаёт lock после env-loading, передаётся реальный inherited FD, который Python
сверяет с canonical git lock по dev/ino/типу/владельцу/правам и flock(EX|NB) того же
open-file-description. GRAF_RESTORE_LOCK_HELD=1 не даёт обхода. CLI без доказанного
FD сам захватывает canonical lock; произвольный открытый FD на иной файл запрещён.
Неизвестный git-root/lock-path/подмена inode — HOLD до создания ресурсов.

Actual restore не использует ephemeral cleanup для своей будущей рабочей DB:
она принадлежит отдельному canonical run-token с OID/binding/digests и durable
состояниями prepared/restored/replayed/swapped/complete/unknown (fsync).
При неуспехе actual restore сохраняет принадлежащую запуску цель и экспорт для
проверки/продолжения того же запуска; временная rehearsal-схема/проверочный bucket
очищаются отдельно. Неизвестный rename COMMIT запрещает повтор имени/новый run.
Первичный export/old DB обязательны для проверки, не считаются учебным мусором.

## Последняя попытка, неизменяемый комплект и ежедневная проверка

Используются собственные закрытые каталоги GRAF, а не PostHog PASS. Host operator
является единственным писателем служебных файлов; runtime имеет read-only bind
постоянного outer parent. Файлы читаются O_NOFOLLOW, regular single-link, нужный
owner, 0600; каталоги0700, stat до/после, bounded parser с отказом duplicate keys.
Private manifest может содержать object keys, в ready/Git/stdout идут только
count/bytes/digest/time/binding. Никаких user/content/private key в evidence.

### Durable attempts и completed manifest

Один deployment lock сериализует operator backup, initial, verify, restore и CD.
Приём last attempt не опирается на stdout helper или mtime старого каталога.
До создания копии оператор atomic replace+fsync пишет свой `backup-attempt.json`
в постоянном activation-каталоге: version/run UUID/status=in_progress/start UTC/
source binding/целевой комплект. После любого известного отказа пишет failed;
при crash остаётся in_progress, что также запрещает ready. Новая попытка никогда
не перезаписывает завершённый комплект и initial/T0. Pending/failed в последней
попытке запрещает готовность даже при двух старых хороших копиях. Лишь полностью
проверенный результат переводит эту запись в completed с digest manifest и
finished_at, с fsync до допуска. Unknown/частичная последняя запись — HOLD.

Законченный `manifest.json` создаётся O_EXCL+fsync в новом каталоге копии только
после cleanup. Включает version/run UUID/source SHA/image/cluster/DB/schema,
проверенный период общего drain, единую DB snapshot identity и native inventory/
roles/columns/RLS/constraints/lifecycle invariant digests; bytes+SHA256 каждого
из postgres.dump/schema.sql/inventory.jsonl/checksums.sha256 и полного object
manifest; object count/bytes, started_at/finished_at по UTC и cleanup=confirmed.
Schema/roles/lifecycle digests считаются кодом с выполненных запросов, не
принимаются аргументами CLI. Object manifest — отсортированный список точных
UTF8 key/length/byte SHA256. Ключи с пустым именем, path traversal, ведущим или
конечным slash, dot components, NUL/неподдержанной нормализацией, файловые links/
спецобъекты/неоднозначные file-directory collisions дают HOLD. Не декодировать
имена повторно и не нормализовать два разных key в один filesystem path.
Versioning/object lock/неизвестная bucket config дают HOLD. Полный byte stream
SDK уже установлен, новых зависимостей нет; responses close/release в finally.
MinIO list/stat до и после чтения должны совпасть в закрытом drained interval.
Manifest backup сверяется с source bytes в том же интервале; pg_dump/schema/
inventory происходят из одного exported snapshot внутри него. Полная копия не
объявляется согласованной только по checksum уже скопированного дерева.

Первый запуск требует две полные локальные завершённые контролируемые копии;
старый каталог без manifest не повышается до нового доказательства. Две копии
можно получить в одном закрытом интервале initial до T0, с независимой проверкой
обоих комплектов; исходные рабочие архивы не удаляются. Далее остаются минимум2
успешных комплекта. Новая копия не инициирует удаление прежней перед завершением.
Бюджет/место учитывают весь product backup отдельно от аналитической доли.
На сервере metadata du всего GRAF backup tree показал406331924480 allocated bytes,
свободно396162203648 bytes. Это не размер одного комплекта и не128GiB аналитики.
До stop нужен размер выбранного завершённого комплекта, оценка новых2 копий+
restore target+staging и резерв физического диска; неизвестный размер — HOLD.

### Плановая coherent backup — отдельный безопасный исход отказа

Для этой фиксированной установки нет доказанного online DB+objects snapshot.
Поэтому `backup` использует ровно уже принятый controlled export с общим stop/
drain; новый online протокол не строится. Цель запуска задана кодом как
planned_coherent_graf_backup. Обычный verify продукт не останавливает.
Расписание — host cron, 03:10 UTC ежедневно, закрытый проверенный root+frozen uv
entrypoint; существующий host scheduler, нового daemon/долгоживущего сервиса нет.
Установка отдельной cron-строки входит в выпуск, не утверждается уже выполненной.
Deadline600с общий, без retry; до stop проверяются tooling/pinned runtime, source/
IDs/networks/space/legal/resource/ownership и отсутствие незавершённого actual run.
Resource/legal HOLD до stop закрывает только аналитику, продукт продолжает работу.
До stop по source RR проверяется отсутствие upload_sessions с expires_at>DB clock
и status вне закрытого terminal набора (finalized/expired/failed/cancelled);
неизвестный status — HOLD. Это не обещает исключить запрос, пришедший после
проверки. API останавливается SIGTERM со штатным graceful ожиданием, Compose
stop_grace_period задаётся120с внутри общего deadline; SIGKILL/137 либо неизвестный
результат graceful stop — отдельный maintenance incident/HOLD. После stop/drain
заново читаются незавершённые uploads. При гонке новой сессии копия отменяется
до export, продукт безопасно возобновляется, аналитика HOLD. В стенде запрос с
принятым chunk должен либо завершить DB/object commit+ответ до stop, либо
дать явный неуспех с повтором по прежнему idempotency_key; потеря уже принятого
chunk/двойной finalization запрещены. Новые запросы во время паузы могут получить
503/повтор, zero-downtime не обещается. До рабочего расписания измеряется весь
интервал и проверяется штатный retry клиента. Последняя попытка failed и штатное
существующее оповещение вызываются без содержания данных.

Healthy preflight → deployment EX → filesystem EX/revoke → stop/drain → export
true/limit0 → полный dump+objects+byte verification → false/drain → cleanup →
completed manifest/attempt → безопасный product resume → самостоятельный verify.
Фактическая пауза start-stop/start-health измеряется;600с — аварийный верхний
предел, а не утверждение приемлемого времени. Стенд проверяет предел и отсутствие
потери принятого upload/request. Рабочая длительность и нагрузка принимаются до
автоматического расписания; без этих доказательств scheduling/readiness HOLD.

**Обычная ошибка копии** (checksum/object/неполный archive/staging cleanup):
после reap всех CLI и разрешения всех SQL проверить неизменный исходныйOID/
cluster/schema/лимит, отсутствие actual switch/DDL/data write, прежние container
IDs/images/config и то, что active bucket в этой операции только читался. Отсутствие
реального cleanup временного export помечается failed и не скрывается. При
доказанном безопасном исходе закрыть все source-сессии, вернуть исходный лимит,
открыть исходную DB, запустить только прежние running IDs и подтвердить health.
Аналитика остаётся revoked/HOLD; failed последняя попытка, оповещение FR051,
не делать автоматический ready из предыдущего proof. Это не success копирования.
Если отменён родитель, дочерний owner завершает этот же безопасный возврат прежде
освобождения lock; отмена не выдаётся за успешную операцию.

**Неизвестное состояние продукта** (неразрешённый ALTER/stop/reap, смена identity,
новый writer, невозможный безопасный возврат) сохраняет closed/stop насколько
подтверждено, отдельный maintenance incident с durable known/unknown стадией,
без догадки о resume. Это авария обслуживания, не штатная реакция аналитики.
Actual restore сохраняет прежний более строгий HOLD и материалы своего run.

### Rehearsal receipt и ordinary verify

`rehearsal.json` — собственный атомарно завершённый receipt после fresh restore/
full native metadata+ledger replay+byte readback+cleanup; digest реально проверенного
backup manifest, время завершения и проверяющий source SHA/PG/schema/roles/
ledger/lifecycle/operator invariants. Версия алгоритма входит в code digest.
Пустой рабочий ledger не заменяет отдельные непустые synthetic tests этого же
кода и схемы; их native self-check исполняется trusted verifier на owned targets,
а не supplied JSON. Последняя failed/in_progress rehearsal запрещает ready.

`verify` не создаёт initial/T0 и не выполняет actual restore. Под deployment lock
+filesystem EX читает marker/initial, latest-attempt=completed и его manifest;
проверяет все artifact hashes, ownership, две локальные полные копии и
0≤now-finished_at<26ч; если последняя failed/incomplete/future — HOLD. Список
каталогов/их timestamps не определяет последнюю попытку. Для двух копий
требуется distinct run UUID и проверка каждого полного комплекта.

Latest backup и rehearsed backup остаются **разными** ссылками с собственными
digests и временами. Rehearsal≤30дней принимается только при равных текущих
PG major/source code/schema/roles/constraints/RLS/ledger/lifecycle policy/operator
code invariants и наличии проверенного rehearsed комплекта с совпадающим hash.
Новый backup не меняет rehearsal timestamp/digest. Любое изменение указанного
инварианта или исчезновение rehearsed комплекта требует новой изолированной
rehearsal нового latest комплекта до ready. Эта rehearsal продукт не заменяет
и его writers не останавливает; свежий source closure snapshot/register даёт
exact replay на изолированном target до cleanup. Исходный DB snapshot/MinIO
согласованы во время создания выбранного immutable backup; при работающем
источнике verify не утверждает равенство всей live DB уже прошлой копии.
Неизвестный post-T0 gap запрещает допуск без нового T0. Удаление старой копии
не стирает принятую T0, но требует переисполнения proof, если это её единственный
проверенный target. До first initial изолированные проверки делают current
source/disposition проверку; после T0 допускаются только покрытые intervals.

### Local retention/resource/access и реальный gate

Для собственных категорий shared enforce-product-analytics-retention.sh получает
явный scope graf-local ровно из LEVEL_RETENTION_CATEGORIES двух локальных
уровней: activation_milestone_decisions, anonymous_page_aggregate,
visit_attribution, client_acquisition_attribute. Таблицы соответственно
product_activation_milestones, anonymous_page_aggregate_buckets,
public_visit_attributions, client_acquisition_attributes. Другие категории этим
узким proof не принимаются и не становятся автоматически готовыми. ClickHouse/Yandex не запрашиваются этой ветвью, их прежний scope
сохраняется. Проверка не удаляет по возрасту: require until_decision/None и
соответствующие реальные таблицы/файлы; из owner schema catalog проверяет
ожидаемые trigger/functions и отсутствие pg_cron/timescaledb/чужих age jobs;
installed guard/purge/cron hashes сверяются с проверенным исходным кодом/политикой.
Проверку выполняет общая внутренняя функция со своими фактическими запросами
через удержанную reduced source-сессию, чтобы closed DB не требовала нового
подключения; shell scope graf-local делегирует её тому же доверенному host
entrypoint при ordinary online verify. Нельзя выдать отсутствие PostgreSQL
подключения за отсутствие TTL/таблиц. Реестр v2 перечитывается, все
accepted/completed/overdue/failed/unknown disposition
cases обрабатываются существующим lifecycle/replay путём с точным охватом/сроком;
неподтверждённое удаление/остатки — HOLD. Receipt только после фактических запросов
и политики; он содержит category coverage/policy/schema/register/installed-job
hashes и время, без content/IDs. Общий существующий retention PASS без activation
категории не принимается. Dry-run/ручной PASS не становится runtime proof.

Resource evidence — реально свежие файлы штатного runtime guard:
`runtime_guard_blockers()` должен вернуть пусто (включая120с sample и latch),
inventory/budget versions/дедлайн приняты; content digests обоих current файлов
и прошедшего capacity result записываются в ready. Не продлевать timestamps
старого sample. `<26ч` — предел ready retention/resource receipt,120с fresh guard
проверяется дополнительно при каждом admission. Access — штатные
read_access_governance_state/access_governance_blockers с текущим expected
installed digest, двумя допущенными операторами/MFA/сроком/ревью. Это отдельные
источники; resource guard не выдаёт access PASS. Неизвестная настройка — HOLD.

В activation_milestone_write_blockers(settings) сохранены enabled/mode/legal/
disclosure/current register/withdrawal. Только для корректного local_only
выбираются собственные current retention+resource+access gates, без вызова
PostHog build_analytics_operations_readiness. В остальных режимах прежний
PostHog gate и unconditional activation_recovery_unverified остаются до их
реальной приёмки. В local_only этот blocker снимается только в общем DB admission:
после SH fence и advisory transaction lock, фактического DB/schema/runtime binding
и успешного read_ready, проверяющего initial/marker/digests/freshness. Ранний
legal-gate precheck не является полной готовностью; его название/документация
должны говорить именно это. Ни один ingress не может вставить local-only row
до before_insert/read_ready; все callers проверены. Provider reconciliation
не получает разрешение на отправку в local_only: прежние provider settings false,
реальный provider gate проверяется перед transport. Режим не открывает T118/T119.
Unconditional blocker не удаляется в коде раньше полного trusted verifier.

После последнего await и непосредственно перед ready atomic write перечитываются
binding/lock identity/current legal/disclosure/register/retention/access/guard и
latest attempts. Несовпадение digest/current state — revoke/HOLD, без нового T0.
Сам read_ready никогда не создаёт файлы и не выводит проверки из одного JSON.

## Actual restore / schema-runtime rollback

Decision-only rollback-rec-stack не объявляется исполнителем. Все поддерживаемые
пути CD перед mutation/downgrade обязаны deployment→filesystem EX/revoke→stop/
source gate/session EX→all PID/prepared drain. Runtime rollback не берёт ready
из образа/архива и не возвращает старый initial. Старый CD без такого входа
нельзя считать поддерживаемым после включения local_only.

restore использует выбранный закрытый полный backup, сохраняет live source
снимок lifecycle/ledger/initial до изменения и проверяет coverage интервала
после копии. Нет живого authoritative source/anchor или известного покрытия
после T0 — аналитика HOLD, произвольная disaster-recovery история не выдумывается.
Новые post-T0 ledger decisions обязаны сохраниться без повторного принятия;
мismatch/missing account+event не маскируется карантином или нулём.

Target UUID DB имеет CONNECTION LIMIT0; pg_restore и metadata capture идут
только через доверенного owner. Native full schema/roles/count/states compare
с backup, затем свежий reduced replay из удержанного source snapshot, commit,
новый reduced readback полного expected ledger. Старое provider intention не
доставляется. Если ledger backup не покрывает current source, known gap даёт
HOLD до switch; импорт/додумывание утраченных решений не предусмотрены.

Перед switch target и old source false/0PID/0prepared, source session EX закрывается
только после завершения экспорта, filesystem EX/revoked остаются. Owner в postgres
в одной transaction переименовывает old→prior_UUID и target→canonical. Коллизия,
поздняя session, failure/неизвестный COMMIT — HOLD без догадки/retry/auto rollback.
После подтверждённого COMMIT owner в postgres заново сверяет canonical name,
новыйOID/cluster, false/limit0. Явно ставит ALLOW_CONNECTIONS=true, сохраняя
limit0; только тогда открывает новую физическую owner-сессию в canonical DB,
сразу выполняет SET SESSION AUTHORIZATION maintenance и row_security=on,
проверяет actual name/newOID/cluster/schema/roles и полный ожидаемый ledger.
После полного закрытия reduced-сессии owner снова ставит false и подтверждает
новыйOID/limit0/0PID/0prepared. Filesystem EX/revoked и остановка writers всё
это время сохраняются. Ошибка/неизвестный ALTER/отмена не разрешают resume;
owner пытается закрыть gate и подтверждает исход, неизвестный исход — HOLD.
Старые source receipts не переиспользуются. Initial.started_at не меняется.

Полное product состояние перед switch проверяется конкретно: все обычные public relations из native inventory, кроме activation ledger,
сравниваются как multiset SHA256 каждой row_to_json(row)::text, вычисленной в
PostgreSQL при фиксированных UTC/ISO/extra_float_digits/bytea_output settings.
Передаются только32-byte hashes отсортированным cursor stream, не private rows;
клиент считает итоговый SHA256 потока и точный count каждой relation. Схема/
column order/PG17 версия уже равны native verifier. Допускаются только public
ordinary heap relations без partitions/inheritance и views, не имеющие собственного
состояния, плюс принадлежащие им штатные sequences (их last_value/is_called
сравниваются отдельно owner metadata, не row hash). Partitioned/foreign/
materialized/non-public user relations, extension/custom/composite/range/unknown
column type дают HOLD. Имена/тип/число колонок сверяются с owner catalog, из
reduced pg_tables список не выводится. Поддержанные built-in типы фиксируются
закрытым списком pg_catalog type: bool/int2/int4/int8/numeric/float4/float8/
text/varchar/bpchar/bytea/uuid/json/jsonb/date/timestamp/timestamptz/time/timetz/
interval. Arrays/domains/enums/custom types и неизвестные collation/config
дают HOLD до отдельного native доказательства; молчаливого расширения нет.
SET LOCAL intervalstyle=postgres, timezone=UTC, datestyle='ISO, YMD',
extra_float_digits=3, bytea_output=hex, DateStyle/encoding version на обеих сторонах
фиксируются; строки хешируются UTF8 bytes и сортируются bytea, не locale text. Системные pg_catalog и
information_schema не являются product data. Native verifier должен подтвердить
владение/список sequences и отсутствие другого пользовательского состояния. Counts source fingerprint
сверяются с owner inventory; target counts — с native restore inventory. Одна
read-only RR snapshot на каждую сторону, источники остановлены. Неизвестный
тип/неполный список/timeout/hash/count mismatch запрещает switch. Ledger отдельно
сверяется полными полями expected_ledger(source current, exact cases), включая
карантин; отсутствующее decision нельзя восстановить выдуманным событием.
Таким образом старый backup с потерянной оплатой, account closure/session/device,
meeting deletion или другой product row не проходит, даже при тех же counts.
Это ограничивает поддерживаемое восстановление доказанным current state;
при реальной потере source/непокрытом gap аналитика остаётся HOLD, как требует
контракт. Disaster recovery с сознательной потерей продуктовых данных — отдельное
решение владельца, не автоматический режим этого оператора.

MinIO нельзя молча вернуть из старой копии поверх текущего bucket. В этой
поддерживаемой процедуре active bucket не перезаписывается: полный current
manifest key+byte SHA256+size должен совпасть с закрытым backup manifest и
прочитанным sandbox restore manifest. Неизвестный/удалённый/лишний/изменённый
объект — HOLD до switch. Пустой bucket проверяется отдельно. Versioning/object
lock/неизвестная storage config не принимаются как поддержанные без отдельной
проверки. Исходные bucket access/policies/config не меняются. Ключи/объекты не
пишутся в Git/публичные receipts; итоговые count/hash безопасны. Нет лишней
перезаписи активного bucket, поскольку его точное соответствие уже доказано.
Temporal DB/history не откатываются: все связанные application rows и active
objects доказанно равны current source, а workers остановлены. При их расхождении
нет product resume/analytics readiness. Активные runtime provider/secret настройки
после switch те же pinned значения и не копируются из старого архива. Сохранённый old DB закрыт как обязательный rollback reference,
его удаление отдельно после принятия полного восстановления; случайно не считать
его временным учебным мусором. Другие backup/data не удаляются.

## Обязательные проверки и границы следующего кода

Сначала RED, затем native causal tests: never-started/attempted/lost/partial marker;
T0 DB-time/NULL/future timestamps; no supplied-pass; parent cancel twice through
DB close/reap; controlled export app/media/maintenance denied; native full backup+
restore/schema/objects/replay/cleanup; partial copy/unknown commit/late PID/prepared;
actual two-name atomic cutover success/failure/collision; gap denies before switch;
new physical reduced readback; exact prior running IDs resume; runtime rollback
revokes before downgrade; daily verify does not reset T0 or accept stale proof.
Свой PG17/Compose/MinIO стенд, без рабочего GRAF Dev/production, без новых пакетов.

Если этот проект оставляет неопределённой обязательную операцию (например корректность полного
row fingerprint/MinIO manifest либо daily proof freshness), reviewer должен дать HOLD и назвать
конкретный минимальный недостающий алгоритм. Кода до устранения блокирующих
находок не писать; узкий helper не выдаётся за полную реализацию T113.
