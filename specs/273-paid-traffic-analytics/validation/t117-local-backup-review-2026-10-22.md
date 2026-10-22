# T117 — независимая проверка локальных резервных копий

Дата: 22.10.2026. Проверяющий: `/root/growth_infra_gate`.

## Этап 1 — достаточность требований до реализации

**PASS качества требований T117; существующие отметки 111/111 сохраняются.**
Пробелов, препятствующих минимальной корректной реализации, не обнаружено.
Это не приёмка текущих скриптов или будущих байтов: реализация должна быть
предъявлена отдельным замороженным снимком с завершёнными проверками.

Применено разрешение ограниченного чтения
`.dev/growth/f273-scoped-reading-authorization-2026-10-22.json`:
«Перечитать затронутые требования и все зависимости хранения; SHA остальных
ранее прочитанных документов. Не отменяет ревью, тесты, согласие, защиту данных
и выпускные проверки». Все 7 опорных SHA совпали. Полное новое чтение
конституции/PRD/status не заявляется.

Перечитаны operations §Резервное копирование, research §6, FR-033/034/035,
FR-051/052/053 и US1, T117/T118, quickstart scenarios 6 и 7, затронутые
вопросы четырёх reviewer-owned чек-листов, backup inventory и описанные границы
восстановления. Scenario 6 сохраняет защиту диска; непосредственно проверка
свежести копий находится в scenario 7. Исходные spec, plan, operations,
quickstart, data-model и три чек-листа совпали с принятым v3. Security
изменён только добавленным отчётом другого reviewer по T109/T111; вопросы
и отметки не изменились. Дополнения tasks рассмотрены: T116 и исторические
результаты не изменяют критерии T117/T118.

### Достаточность конкретных правил

| Область | Существующее основание | Результат |
| --- | --- | --- |
| Размещение и доступ | FR-052, operations, research §6: существующий `2brain.dev`, `/var/backups/graf-posthog`, root 0700, файлы 0600 | Назначение конкретно; новые получатели не нужны. |
| Расписание | FR-033, US1; existing runbook и timer: ежедневно в 02:30 | Частота определена, а не только слово «автоматически». |
| Отмена offsite | FR-034/052 и решение владельца в research §6 | Writer, readiness, alerts и examples должны принять отсутствие обязательной внешней выгрузки вместе; локальный `.offsite` не увеличивает счёт. |
| Полный успешный набор | T117, FR-034/052, backup-volumes inventory | Полный inventory/manifest, проверка нового набора и атомарное завершение; незавершённое не даёт успеха или готовности. |
| Возраст | FR-034, research §6, quickstart 7 | От окончания успешной копии: `0 ≤ age < 26 часов`; неизвестное, будущее и ровно 26 часов закрывают готовность. |
| Последняя ошибка | FR-034/051, operations | Failed последнего запуска закрывает готовность даже после прежнего pass; ошибка требует оповещения. |
| Ротация | FR-052, T117, research §6 | Последние 7 успешных полных наборов, минимум 2 для готовности; сначала проверка нового и сохранения минимума, затем ротация; неполные не вытесняют пригодные. |
| Смысл истории | FR-036/052 и research §6 | 7 — число точек восстановления; каждая сохраняет всю допустимую историю until_decision. Возрастное удаление событий из этого не следует. |
| Предел защиты | FR-053, operations, research §6 | Потеря узла/диска может уничтожить все локальные копии; восстановление истории не обещается. |
| Граница T118 | FR-035/053 и T118 | Согласованное чтение восстановленного полного PostHog обязательно, tar/hash сами по себе недостаточны. Приёмка этого отдельно от T117. |

### Уточнение существующей границы inventory

Явного принятого требования, запрещающего предложенную минимальную границу,
не найдено: T117 может проверять все required/optional классы существующего
`backup-volumes.txt` и полный набор фактических project named volumes,
отвергая неучтённый том; формировать manifest и атомарный completion marker.
`storage-mounts.txt` описывает более широкий учёт физического расхода T116,
включая восстановимые конфигурационные bind mounts. Этот учёт не задаёт
сам по себе обязательного копирования каждого конфигурационного bind в T117.

Реконструкция runtime/configuration и доказательство согласованного чтения
остаются T118. При такой границе T117 не должна утверждать, что одна её
проверка archives/manifest уже доказала восстановление всего рабочего
PostHog. Если в фактическом runtime обнаружится неучтённый том с данными,
он не может быть пропущен как «конфигурация»; это уже следует из полного
inventory. Новых классов данных, услуг, требований или задач этим выводом
не добавлено. Runtime данной проверкой не исследовался.

### Чек-листы после проверки

Перечитаны затронутые infra CHK001–010/018/021/024, privacy CHK031/033–037,
security CHK005/006/010–015/022/023 и общие вопросы измеримости, полноты,
границ/зависимостей. Остальные прежние выводы сохранены в установленной
границе чтения; новый полный security/privacy аудит не заявляется.
Отметки качества требований не являются готовностью установленного кода.

| Чек-лист | Отмечены `[x]` | Открыты `[ ]` |
| --- | --- | --- |
| infra | 25 | 0 |
| privacy-measurement | 45 | 0 |
| security | 25 | 0 |
| requirements | 16 | 0 |
| **Всего** | **111** | **0** |

Оснований менять вопросы или отметки нет. Старые исторические задачи и
отчёты с offsite не становятся действующей политикой и не доказывают
миграцию; T117/T118 остаются открытыми до соответствующих доказательств.

### Граница результата и снимок

Полоса: reviewer-only этап существующей high-risk F273, без изменения продукта.
Изменён только этот отчёт. Код, требования, чек-листы, Git/GitHub, timers,
рабочие данные и архивы не менялись. SSH/Docker/сеть/отправки/ротация и
восстановление не выполнялись. Проверки реализации ещё не предъявлены.
Самостоятельные T118, T097, выпуск, установка и рабочая приёмка сохраняются;
этот PASS не включает IP writer, необязательную доставку событий или запуск
трафика.

HEAD при фиксации: `7e34de9a1e4528ce60a8035d3b3b3a597d6a7062`.

| Входной файл | SHA-256 |
| --- | --- |
| `specs/273-paid-traffic-analytics/spec.md` | `c6b318125e90cd19018f43cecc8fced90bb22ee3e5340849d81189e520e081da` |
| `specs/273-paid-traffic-analytics/plan.md` | `0e0e5c3ee5d081c43d5b14f68f8a66d190d9b031cde6ae73c36f30844558a5e3` |
| `specs/273-paid-traffic-analytics/tasks.md` | `a394c10ab1b7342c4a670125cd7b9a475fdf6d362f6ebdae399819a876b6679f` |
| `specs/273-paid-traffic-analytics/contracts/operations.md` | `aef6aa9c7a494e3c99d57fa550e5c3eb164faa58404e35c9d6add53b104f7861` |
| `specs/273-paid-traffic-analytics/research.md` | `3551a1e91d3ce81eaa24d885916e1faa3b9be659c601eae0072b11224a2c6319` |
| `specs/273-paid-traffic-analytics/quickstart.md` | `6166abbcb98a6d626b48532f6632a20df9a36a1c22603a9e254c438883f35e8f` |
| `specs/273-paid-traffic-analytics/data-model.md` | `4a8f615425e5448c391551bebe8128b729e4b60692ca40bfa3b62647a678151f` |
| `specs/273-paid-traffic-analytics/checklists/requirements.md` | `2c4a91701de2dcdb377f758064216125098bdc752e616115deb2bdb6a2607f9d` |
| `specs/273-paid-traffic-analytics/checklists/privacy-measurement.md` | `00a31550d0ab58f06f2712434bf915119095f3c77ca7dc099cb3c79f83513f4f` |
| `specs/273-paid-traffic-analytics/checklists/infra.md` | `cb56fbd6280fea163c93ea5dd6b34bf18a0bbf2fe514344c2ca01c05b1027bee` |
| `specs/273-paid-traffic-analytics/checklists/security.md` | `700b1cad2aa658ed80631d25ed84083a799984e06fd362eebd6fc1055d1fd677` |
| `infra/posthog/backup-volumes.txt` | `d93524ea3fcb69915a96ec569e237c8991df2cbf0a2ad95614e77c35ced92aad` |
| `infra/posthog/storage-mounts.txt` | `0c356dbdbae2af7ba233b017bd2964805972b606c237686c378c3626a738b7d9` |
| `infra/posthog/backup-restore.md` | `b8c5716553701a15c73153e40fb4ceb04ebb3da957cb69e1c64c391a15afb255` |
| `infra/posthog/graf-posthog-backup.timer` | `e03d2ff99560adbed34a83d193932ac428f8e46a9647b1fb5ac0ff58d181614e` |


## Этап 2 v1 — независимое ревью реализации

**FAIL локальной реализации: B1/B2 высокой важности и B3 средней важности.**
PASS требований этапа 1 сохраняется; новые требования не предлагаются.
Исходный снимок `.dev/growth/t117-implementation-snapshot-2026-10-22.json`
содержит 18 файлов реализации и 4 требования на HEAD
`7e34de9a1e4528ce60a8035d3b3b3a597d6a7062`. Все 22 хеша совпали перед
независимыми пробами. Во время ревью основной агент сообщил о правках трёх
найденных его полным прогоном failures; будущие изменённые байты этим v1
не принимаются. Writer во время описанных ниже проб сохранял хеш снимка.

### B1 — ранние отказы execute сохраняют предыдущую готовность

`infra/scripts/backup-posthog.sh`: preflight проверки до объявления
`fail_backup`/установки ERR trap завершаются непосредственным exit. Это
включает чтение inventory/настроек, ошибку общего списка Docker и отдельного
списка project labels. Успешный старый backup-state не заменяется failed,
оповещение не вызывается. Нулевой код выхода не заявляется, но потребители
продолжают видеть прежний pass и допускают готовность, вопреки FR-034/051.

**Независимая проба:** создать во временном каталоге пригодный старый набор,
выполнить writer через Docker/logger/alert stubs: новый успешный набор даёт
2 копии и отсутствие backup blockers. Затем stub возвращает exit7 только
на `docker volume ls ... --filter label=com.docker.compose.project=...`.
Writer возвращает exit1 с `project_volume_list_unavailable`, байты состояния
не изменились, alert-файл отсутствует; API по-прежнему возвращает
`backup blockers=[]`. Рабочий Docker не использовался.

**Минимальное исправление:** все отказы после начала execute должны проходить
один существующий failure path; необходимо закрытое состояние попытки до
проб, затем терминальный pass/failed. Dry-run/status остаются отдельными.
Нужны регрессии с уже существующим свежим pass для ошибок listing/preflight,
с проверкой реальных reader/alert, а не только кода выхода.

### B2 — отказ записи состояния оставляет pass и обрывает alert

`write_state` при отказе атомарной записи завершает вызов ошибкой.
`fail_backup` вызывает его до `raise_alert`; ERR trap там уже отключён.
Поэтому ошибка persistence обрывает обработку отказа, alert не запускается,
старый pass сохраняется. В конце успешного пути отказ записи pass также
может перейти в тот же незавершающийся failure path. Это не durable closed
attempt и не достаточное оповещение об ошибке копирования.

**Независимая проба:** после успешного pass с 2 наборами подставной python3
отказывает только атомарной публикации `backup-state` (exit9); остальной
Python, lock и writer выполняются нормально с заглушками. Следующая
неуспешная попытка завершается exit9, старые байты pass неизменны,
alert не вызван, `backup blockers=[]`.

**Минимальное исправление:** failed state persistence не должно отменять
независимый вызов оповещения/журналирование. До действий нужен устойчивый
закрытый attempt-state или эквивалентная минимальная инвалидизация старого
pass: не оставлять готовность от предыдущей попытки при невозможности
подтвердить терминальный результат. Не подменять это безусловным удалением
архивов или глотанием ошибки. Регрессия должна начинаться со свежего pass,
инъецировать отказ state write и проверять закрытие readiness и alert path.

### B3 — неуспешная ротация молча даёт pass с более чем 7 наборами

В цикле ротации `if rm -rf ...; then ...; fi` неуспех удаления не фиксируется.
Новый набор при этом может быть корректен, но обязательная глубина последних
7 точек не соблюдена; writer выдаёт pass и не оповещает о накоплении копий.
На том же диске это скрывает незавершённую операцию хранения.

**Независимая проба:** 8 полных проверенных старых наборов, успешный новый,
заглушка rm возвращает exit7. Результат: `exit0`, `backup_result=pass`,
`copies_local=9`, alert отсутствует. Все временные наборы после пробы удалены
штатной очисткой временного каталога, а не скриптом продукта.

**Минимальное исправление:** ошибка удаления в запланированной ротации должна
дать failed attempt/alert; не продолжать заявлять соблюдение keep7.
Сохранить хорошие наборы и не удалять дополнительные данные ради теста.
Добавить регрессию конкретного отказа rm.

### Что подтверждено независимо

Прямо выполнены существующие локальные проверки: полный набор/manifest/
completion marker и права; ротация только пригодных наборов; отказ
отсутствующего required класса с failed/alert; неизвестный project volume;
ошибка архива без публикации complete и без вытеснения хороших. Все пять
завершились PASS.

Отдельно прямо выполнены все 10 API/alert boundary случаев: future, ровно
26 часов, неизвестное время, failed, неизвестный результат, старая schema,
неполный набор, неизвестное число, одна копия и валидное состояние.
Потребители согласованно закрываются; ослабляющие env100h/min1 не обходят
нормативные 26h/min2. Offsite не требуется. Пробы alert были dry-run с curl
stub, без внешних сообщений. Это независимое выполнение локальных функций,
а не повтор полного набора pytest с реальной БД.

По коду подтверждены: один parent lock на execute; скрытый staging;
fsync архивов/manifest/inventory/marker и каталогов, атомарный rename;
архивные bytes/hash проверяются перед счётом/ротацией; неизвестные
project labels закрываются, дубликаты томов/неполные/повреждённые наборы
не считаются; неудавшийся новый набор не ротирует хорошие.
API получает только read-only bind состояния и использует существующую
группу чтения. Фактическая установка и права на узле не проверялись.
Проверка архива по manifest не выдаётся за согласованное восстановление T118.

### Предоставленный полный прогон и отдельный остаток

Полный профиль 11 модулей завершён: **196passed,3failed,1skipped,2warnings**,
runner сообщает fail, изолированный контейнер удалён. Failures: неполная
новая alert rule, прежняя широкая проверка подстроки secret, fixture
Yandex offline без runtime guard. Основной агент сообщил об их исправлении;
нового окончательного результата в v1 нет. Browser skip остаётся пропуском.

При поиске потребителей обнаружена старая fixture выпускного smoke:
`infra/scripts/run-product-analytics-provider-smoke.sh` создаёт
`backup_state_version=1`/`copies_offsite`. Она не соответствует новому
reader v2 и должна быть согласована перед использованием этого smoke как
выпускного доказательства. Сам smoke не запускался; эта запись не заявляет
новую приёмку его остальных зависимостей или реальной доставки.

Все пробы использовали временные каталоги и подставные команды, без реальных
SSH/Docker/сети, рабочих архивов/данных и внешних отправок; каталоги очищены.
Reviewer изменил только этот отчёт. Чек-листы сохраняются 111checked/0open;
они проверяют требования, а не эту непрошедшую реализацию. T117 нельзя
принимать по v1; T118, установка, выпуск и рабочие receipts отдельны.

### Снимок v1

| Группа | Файл | SHA-256 |
| --- | --- | --- |
| hashes | `apps/server/src/twobrain_rec_server/product_analytics/provider_readiness.py` | `ed21b9447adbda469ae3561672e414f73823889e62f4d792d00d5b9ce67e57a6` |
| hashes | `apps/server/tests/contract/test_analytics_degradation_alerting.py` | `65670235346cca0dd0b5c95e0e6310b615e0353dd1df1733d0287f90a2aaddcb` |
| hashes | `apps/server/tests/contract/test_analytics_retention_enforcement.py` | `861cbe15896a9f65e7c977795acc9c2a139108672118abb4f326fc64fbb57897` |
| hashes | `apps/server/tests/integration/test_product_analytics_provider_readiness_blockers.py` | `43bd76861d4dc9557368f6895f06cdd534725023cdcf237e10ee140dacfed2e5` |
| hashes | `apps/server/tests/integration/test_product_analytics_yandex_page_scope.py` | `70478d7d855f0bbbb238e1456ff1fba5dcdb19a27bc130628a5a3e1e2b732370` |
| hashes | `apps/server/tests/unit/test_product_analytics_launch_approvals.py` | `4027a725da3b1d80181e4a10c2827604f0bfa50be867160dd4d1a68d39179aac` |
| hashes | `apps/server/tests/unit/test_product_analytics_posthog_provider.py` | `f34b3bd9f83b54ef54c14609aa083cc9e34f229ec0c33ef704f4e9795f89b0e4` |
| hashes | `apps/server/tests/unit/test_product_analytics_provider_delivery_gate.py` | `82ccfe08e4ecbbab628781e0c0f03de18e93ee3320ab8052d3b76e721e3cd8ab` |
| hashes | `apps/server/tests/unit/test_product_analytics_yandex_offline_provider.py` | `484192f73aedae95482d79499343a537a6f29cd72ec810e42ac7f90c7e1398a6` |
| hashes | `changes/unreleased/F273.yaml` | `258fd4660db605e5a65abef8c1a9a811fc4a68cb8afaee72b4f73e05044c14c8` |
| hashes | `docs/analytics/product-analytics-posthog-runbook.md` | `ace769759e61aeef8b040ee227a0e3092a790e19d65fda7900f77731d9cf5a75` |
| hashes | `infra/docker-compose.yml` | `a10cd177d6da9a8c50690975a48ca6a04b6968a08ee4c6fb6f8bf6f39ec4051b` |
| hashes | `infra/posthog/alert-rules.txt` | `32eaddf6fbf4b2aafedc37472a2ebf3558e4c27ff4a63750d014adb950863f28` |
| hashes | `infra/posthog/backup-restore.md` | `d914590359c84b653c2f13342fe7c8d52c584b52a13732eecbf924492c6069d7` |
| hashes | `infra/posthog/backup.env.example` | `9bbcace7572daef8c91406d6ef1d923efe7b01ea5228073439ea0a53ec629ffd` |
| hashes | `infra/posthog/graf-posthog-backup.service` | `8c10724404ce0b0b5594884fa923ee86e2ba125e379f88e2489ef3c5f36b7dcf` |
| hashes | `infra/scripts/alert-analytics-degradation.sh` | `1289eda6dc6852ae58ca5879b3c73fde3f5a71ebfadab24bb6db4e76a0de117b` |
| hashes | `infra/scripts/backup-posthog.sh` | `9d297129400daad4eff7403f571f61250b5705321a65894136d6709b47367626` |
| requirements | `specs/273-paid-traffic-analytics/contracts/operations.md` | `aef6aa9c7a494e3c99d57fa550e5c3eb164faa58404e35c9d6add53b104f7861` |
| requirements | `specs/273-paid-traffic-analytics/research.md` | `3551a1e91d3ce81eaa24d885916e1faa3b9be659c601eae0072b11224a2c6319` |
| requirements | `specs/273-paid-traffic-analytics/quickstart.md` | `6166abbcb98a6d626b48532f6632a20df9a36a1c22603a9e254c438883f35e8f` |
| requirements | `specs/273-paid-traffic-analytics/tasks.md` | `a394c10ab1b7342c4a670125cd7b9a475fdf6d362f6ebdae399819a876b6679f` |

## Этап 2 v3 — независимый повтор исправлений B1/B2/B3

**PASS локальной реализации T117 на предъявленном снимке v3.** Исторический
FAIL v1 выше сохраняется. Пробелов требований не добавлено, чек-листы
не изменены. Это не операторская приёмка, T118 или подтверждение рабочего
копирования/доставки оповещения.

Снимок `.dev/growth/t117-implementation-snapshot-v3-2026-10-22.json`:
19 файлов реализации/документов и 4 требования, исходный HEAD
`7e34de9a1e4528ce60a8035d3b3b3a597d6a7062`. Все 23 SHA и HEAD совпали до
и после проверки; 7 опорных SHA разрешения ограниченного чтения также
совпали. SHA-256 самого снимка:
`0bb2d6330724a7180aab2bab7aa7b9d05a5b2ca7fb48109e27ad1709198fd598`.
Исходные требования этапа 1 не менялись; повтор полного общего аудита
или конституции/PRD/status не заявляется.

### Устранение причин B1/B2/B3

- **B1 закрыт:** EXIT trap установлен до fallible preflight execute.
  Под общим lock прежний pass удаляется с fsync каталога; до проб пишется
  состояние `running`, не допускающее готовность. Прямые ошибки list,
  inventory/настроек теперь достигают общего failure path. Dry-run/status
  не инвалидируют рабочую готовность.
- **B2 закрыт:** `fail_backup` не обрывается при ошибке записи failed state:
  ошибка отдельно журналируется, затем вызывается alert. Предварительная
  инвалидизация устраняет источник прежнего ложного pass. Ошибка persistence
  не выдаётся за подтверждённый terminal result.
- **B3 закрыт:** отказ rm при ротации вызывает
  `fail_backup retention_delete_failed`; новые/старые пригодные наборы
  сохраняются, ошибка не становится успешным соблюдением keep7.

**Независимые повторные пробы** выполнены с настоящим shell writer и локальными
Docker/logger/alert stubs. Каждая B1/B2 проба начиналась с фактически
выполненного успешного writer и двух пригодных наборов, а не только
подставленной строки pass. Затем:

| Инъекция | Результат независимой пробы |
| --- | --- |
| Отказ списка project labels | Неуспех, вызван alert, старый pass заменён; API: backup_failed + backup_set_unverified. |
| Отказ общего списка volumes | Неуспех, вызван alert, старый pass заменён; API закрыт. |
| Исчезнувший inventory | Неуспех, вызван alert, старый pass заменён; API закрыт. |
| Отказ Python атомарной записи backup-state | Неуспех, вызван alert; старого pass нет, API: backup_state_unavailable. |
| Отказ только `rm -rf` при ротации | `retention_delete_failed`, exit1, alert; 9 пригодных наборов сохранены, API: backup_failed. |

Для последней пробы заглушка rm разрешает удаление старого state через `-f`
и отказывает именно операции удаления архивного набора через `-rf`;
тем самым проверена ветка ротации, а не ранний отказ инвалидизации.
Никакие рабочие архивы не использовались.

### Согласованность потребителей и сохранённых доказательств

Повторно независимо исполнены все 10 общих boundary случаев API/alert:
future, ровно26h, неизвестное время, failed/unknown result, schema1,
incomplete, неизвестное число, одна копия и valid. Оба потребителя
сохранили закрытые границы 26h/min2; ослабляющие env не обходят их.
Offsite больше не является условием готовности.

Дополнение provider-smoke просмотрено: fixture теперь schema2,
`backup_set_complete=true`, без offsite; общий fixture guard добавлен.
Независимо исполнено **только Python-тело этого smoke** с системным
Python audit hook, запрещающим `socket.connect` и `socket.getaddrinfo`.
Получен `provider_smoke_result=pass`; передача выполнялась подставными
transport-функциями на временных синтетических данных. Внешняя shell-обвязка
с Docker/deploy не запускалась. Этот результат не является проверкой
работающего provider или выпускного smoke целиком.

Изменения тестов/правила относительно v1 просмотрены: новое правило
backup_set_unverified имеет owner, deadline и requirement; проверка
секретов допускает имя existing runtime-reader group и сохраняет запрет
реальных встроенных секретов; offline fixture получает общий guard.
Writer/runtime-причины трёх замечаний устранены отдельно от этих fixtures.

Атомарная публикация, проверка inventory/manifest/архивных hash перед
счётом, исключение неполных/повреждённых наборов, keep7/min2 и блокировка
ошибки нового набора сохраняют прочитанный путь v1. Прежние независимые
положительные пробы v1 остаются историческими доказательствами, новый
полный предоставленный прогон покрывает актуальные байты. Одни hash/tar
не объявляются доказательством согласованного восстановления T118.

### Завершённые прогоны v3 и остаток

Предоставленные журналы прочитаны до конечного результата:

| Журнал | Итог | SHA-256 |
| --- | --- | --- |
| `.dev/growth/t117-writer-v3b.log` | 13passed,53deselected,1warning | `32c62087bf06ea9b8d44ae0d7a939b6c93b71a5adfad79b451fa0dfa0732b007` |
| `.dev/growth/t117-all-focused-v3-2026-10-22.log` | 207passed,1skipped,2warnings; runner pass; isolated_container_removed | `c4ba100175b42b05000dd5c1f9d6f24ad7528183d6bac24822e78d189812403b` |

Полный профиль собрал208 проверок с digest
`53d6b9271a6df97b8621a691c4f3216ea681303fb64af0f0c826866d141ebe10`.
Reviewer не повторял полный pytest-профиль с БД; независимые прямые пробы
перечислены отдельно. Browser skip не считается выполненной браузерной
проверкой. Промежуточные v1/v2 логи не переименованы в новый PASS.

Чек-листы повторно сверены: infra25/0, privacy-measurement45/0,
security25/0, requirements16/0; **111checked/0open**. Они отражают качество
требований. Открытых конкретных дефектов предъявленного локального среза
T117 после исправлений не найдено. T117 сохраняет собственные PR/release/
операторские ворота; T118, фактические rights/mounts, реальная доставка,
резервные копии БД GRAF/IP и включение записи этим результатом не принимаются.

Reviewer изменил только этот отчёт; исходники, требования, чек-листы,
Git/GitHub, production, timers и данные не менял. Все временные каталоги
проб удалены, реальных Docker/SSH/сети/внешних сообщений не было.
`git diff --check` выполнен. Этот PASS не подтверждает трафик или продажи.

### Точный снимок v3

| Группа | Файл | SHA-256 |
| --- | --- | --- |
| hashes | `apps/server/src/twobrain_rec_server/product_analytics/provider_readiness.py` | `ed21b9447adbda469ae3561672e414f73823889e62f4d792d00d5b9ce67e57a6` |
| hashes | `apps/server/tests/contract/test_analytics_degradation_alerting.py` | `65670235346cca0dd0b5c95e0e6310b615e0353dd1df1733d0287f90a2aaddcb` |
| hashes | `apps/server/tests/contract/test_analytics_retention_enforcement.py` | `e2e1fc09334f4b6fd9ba23f60d384c5c30542f8ce481cde479ace559477bac9c` |
| hashes | `apps/server/tests/integration/test_product_analytics_provider_readiness_blockers.py` | `43bd76861d4dc9557368f6895f06cdd534725023cdcf237e10ee140dacfed2e5` |
| hashes | `apps/server/tests/integration/test_product_analytics_yandex_page_scope.py` | `70478d7d855f0bbbb238e1456ff1fba5dcdb19a27bc130628a5a3e1e2b732370` |
| hashes | `apps/server/tests/unit/test_product_analytics_launch_approvals.py` | `4027a725da3b1d80181e4a10c2827604f0bfa50be867160dd4d1a68d39179aac` |
| hashes | `apps/server/tests/unit/test_product_analytics_posthog_provider.py` | `f34b3bd9f83b54ef54c14609aa083cc9e34f229ec0c33ef704f4e9795f89b0e4` |
| hashes | `apps/server/tests/unit/test_product_analytics_provider_delivery_gate.py` | `82ccfe08e4ecbbab628781e0c0f03de18e93ee3320ab8052d3b76e721e3cd8ab` |
| hashes | `apps/server/tests/unit/test_product_analytics_yandex_offline_provider.py` | `484192f73aedae95482d79499343a537a6f29cd72ec810e42ac7f90c7e1398a6` |
| hashes | `changes/unreleased/F273.yaml` | `258fd4660db605e5a65abef8c1a9a811fc4a68cb8afaee72b4f73e05044c14c8` |
| hashes | `docs/analytics/product-analytics-posthog-runbook.md` | `ace769759e61aeef8b040ee227a0e3092a790e19d65fda7900f77731d9cf5a75` |
| hashes | `infra/docker-compose.yml` | `a10cd177d6da9a8c50690975a48ca6a04b6968a08ee4c6fb6f8bf6f39ec4051b` |
| hashes | `infra/posthog/alert-rules.txt` | `32eaddf6fbf4b2aafedc37472a2ebf3558e4c27ff4a63750d014adb950863f28` |
| hashes | `infra/posthog/backup-restore.md` | `d914590359c84b653c2f13342fe7c8d52c584b52a13732eecbf924492c6069d7` |
| hashes | `infra/posthog/backup.env.example` | `9bbcace7572daef8c91406d6ef1d923efe7b01ea5228073439ea0a53ec629ffd` |
| hashes | `infra/posthog/graf-posthog-backup.service` | `8c10724404ce0b0b5594884fa923ee86e2ba125e379f88e2489ef3c5f36b7dcf` |
| hashes | `infra/scripts/alert-analytics-degradation.sh` | `1289eda6dc6852ae58ca5879b3c73fde3f5a71ebfadab24bb6db4e76a0de117b` |
| hashes | `infra/scripts/backup-posthog.sh` | `26f027711e28f19eb5f777c3aadf127ab9ef970a60c012a34cef949eb11e43ca` |
| hashes | `infra/scripts/run-product-analytics-provider-smoke.sh` | `e595d9ef55dc7a3781d4e3d25861bc7016dbfa866c2480c1549423e395156a30` |
| requirements | `specs/273-paid-traffic-analytics/contracts/operations.md` | `aef6aa9c7a494e3c99d57fa550e5c3eb164faa58404e35c9d6add53b104f7861` |
| requirements | `specs/273-paid-traffic-analytics/research.md` | `3551a1e91d3ce81eaa24d885916e1faa3b9be659c601eae0072b11224a2c6319` |
| requirements | `specs/273-paid-traffic-analytics/quickstart.md` | `6166abbcb98a6d626b48532f6632a20df9a36a1c22603a9e254c438883f35e8f` |
| requirements | `specs/273-paid-traffic-analytics/tasks.md` | `a394c10ab1b7342c4a670125cd7b9a475fdf6d362f6ebdae399819a876b6679f` |

## Финальная косметическая досверка после v3

**PASS локальной реализации сохраняется для final snapshot.** Проверен
`.dev/growth/t117-implementation-snapshot-final-2026-10-22.json`, SHA-256
`164cfc955b70700216a7aac202786eb132d439a472f66c3add3ab8a06ef763d9`,
на том же HEAD `7e34de9a1e4528ce60a8035d3b3b3a597d6a7062`.
Совпали все19 текущих файлов и4 требования; относительно v3 **18/19 файлов
не изменены**. Единственное изменение — удаление одной пустой строки
между tests fixture и twobrain imports в
`apps/server/tests/unit/test_product_analytics_yandex_offline_provider.py`.

Для точного доказательства reviewer локально в памяти вставил эту строку
обратно: восстановленные байты дали прежний SHA v3
`484192f73aedae95482d79499343a537a6f29cd72ec810e42ac7f90c7e1398a6`.
Новый SHA файла:
`ff7c53e98bba0217a9b6fe310d603d0b07cf3f6521f0798eb5034116e9749daf`.
Runtime и логика тестов не менялись; повтор функциональных проверок для
изменения пустой строки не требовался. Прежний завершённый результат
207passed/1skipped сохраняет свою указанную выше границу.

Reviewer независимо выполнил Ruff0.15.20 `check --no-cache` по всем9
изменённым Python-файлам final snapshot: **All checks passed**, exit0.
`git diff --check` также прошёл. Код, Git/GitHub и production не менялись;
дополнен только данный отчёт. Все прежние ограничения PASS, отдельные
PR/release/операторские ворота и T118 сохраняются.
| log | `.dev/growth/t117-all-focused-2026-10-22.log` | `6432aa05303a17b52153d67d6cecec38e950870177686aed9c5f9e602b4d37fb` |
