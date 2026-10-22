# T116 — независимая проверка guard и его зависимостей

Дата:22.10.2026. Ветка `codex/273-storage-accounting`, исходный HEAD
`a4f670630e0001c1aae6f0dc399aac088834ed15`.

## Этап1 — действительность требований и чек-листов

**PASS требований сохраняется. Реализация guard/latch/readiness/alerts пока
не предъявлена замороженным снимком и не принята.** Данный этап не принимает
текущие изменяемые файлы или будущие байты реализации.

Применено существующее разрешение
`.dev/growth/f273-scoped-reading-authorization-2026-10-22.json`:
«Перечитать затронутые требования и все зависимости хранения; SHA остальных
ранее прочитанных документов. Не отменяет ревью, тесты, согласие, защиту данных
и выпускные проверки». Семь опорных SHA совпали до и после этапа. Полное новое
чтение конституции/PRD/status не заявляется.

Отчёт требований v3 сохранил SHA
`0495b65c7a1a32122a0eebe6fbffa6cb609084f0f75b81e9be22fc2e8c39901f`.
Из16 его входов13 совпадают; три изменённых зависимости проверены отдельно:

- `tasks.md`: добавлены записи о первой/второй частях T116. Сама T116 и T097
  остаются открытыми; данные runtime metadata не выдаются за размеры/рост.
  Реализационные отметки не подменяют качество требований. Старая запись
  «повторное независимое ревью ещё нужно» в историческом абзаце первой части
  не отменяет уже имеющийся collector v2 PASS; это устаревшая запись хода работ,
  не новое препятствие согласованности требований.
- `product-analytics-capacity-baseline.md`: уже проверенные collector-уточнения
  требуют измеренных двух полных samples≥24часа, unknown до этого, знаковые
  live/archive ряды и совместную установку wrapper/helper/inventories.
  Первая выборка не объявляется измеренным прогнозом. Уточнения согласованы
  с operations и прежним PASS требований.
- `runtime-guard.env.example`: текущий diff добавляет пути collector/inventory/
  budget и явную config version, делает20%/10% фиксированными байтовыми
  порогами. Safe observe defaults и conditional sufficient-headroom обещания
  сохранены. Эти комментарии/настройки не противоречат требованиям. **Это
  только проверка смысла зависимости; незамороженная реализация/применение
  новых настроек здесь не приняты.**

Spec/plan/operations/quickstart/data-model и оба reviewer-owned чек-листа
совпали с принятым v3. Все пункты infra/privacy перечитаны; изменения отметок
не требуются. Security и общий requirements сохраняют прежние отметки по
совпавшим SHA; новый полный security/общий requirements review не заявляется.

| Чек-лист | Подтверждены `[x]` | Открыты `[ ]` | Граница |
| --- | --- | --- | --- |
| infra | 25 | 0 | Качество требований; не работа защиты. |
| security | 25 | 0 | Сохранённый прежний PASS, хеш неизменен. |
| privacy-measurement | 45 | 0 | Качество требований; writer/провайдеры не включены. |
| requirements | 16 | 0 | Сохранённый прежний PASS, хеш неизменен. |
| **Всего** | **111** | **0** | Реализация и production остаются отдельными. |

Открытых фактических оснований отменять требования v3 или отметки не выявлено.
Чек-листы не менялись. Collector v2 и capacity evaluator имеют собственные
узкие отчёты; изменённые сейчас файлы capacity/guard/readiness не принимаются
по прежнему PASS старых байтов.

Следующий этап начнётся только после отдельного frozen snapshot реализации.
Он должен проверить постоянный инцидент, один успешный переход/повторы после
ошибки, dry-run/auto-off, применение и readback, ручное восстановление и
state-consumers/alerts по текущим требованиям. Фактические замеры/нагрузка и
операторское принятие T097/production не подменяются локальными тестами.

Reviewer на этом этапе только читал документы/хеши/diff и создал этот отчёт;
код/spec/plan/tasks, checklist, Git/GitHub, runtime/данные не менял. SSH/Docker,
сеть и внешние отправки не запускались. `git diff --check` выполнен после записи.

### Снимок требований этапа1

| Файл | SHA-256 |
| --- | --- |
| `specs/273-paid-traffic-analytics/spec.md` | `c6b318125e90cd19018f43cecc8fced90bb22ee3e5340849d81189e520e081da` |
| `specs/273-paid-traffic-analytics/plan.md` | `0e0e5c3ee5d081c43d5b14f68f8a66d190d9b031cde6ae73c36f30844558a5e3` |
| `specs/273-paid-traffic-analytics/tasks.md` | `ee8ef3dc281eebeaf2f9deaf50b328a44ba3889b7e1116cc34f0ed8ebc1fde64` |
| `specs/273-paid-traffic-analytics/quickstart.md` | `6166abbcb98a6d626b48532f6632a20df9a36a1c22603a9e254c438883f35e8f` |
| `specs/273-paid-traffic-analytics/contracts/operations.md` | `aef6aa9c7a494e3c99d57fa550e5c3eb164faa58404e35c9d6add53b104f7861` |
| `specs/273-paid-traffic-analytics/data-model.md` | `4a8f615425e5448c391551bebe8128b729e4b60692ca40bfa3b62647a678151f` |
| `specs/273-paid-traffic-analytics/checklists/infra.md` | `cb56fbd6280fea163c93ea5dd6b34bf18a0bbf2fe514344c2ca01c05b1027bee` |
| `specs/273-paid-traffic-analytics/checklists/privacy-measurement.md` | `00a31550d0ab58f06f2712434bf915119095f3c77ca7dc099cb3c79f83513f4f` |
| `specs/273-paid-traffic-analytics/checklists/security.md` | `9f1cbf1173102fac99a3acdff44ddad0bbca07a93ca8ff2130008063ce7a59fc` |
| `specs/273-paid-traffic-analytics/checklists/requirements.md` | `2c4a91701de2dcdb377f758064216125098bdc752e616115deb2bdb6a2607f9d` |
| `specs/273-paid-traffic-analytics/validation/t116-requirements-review-2026-10-22.md` | `0495b65c7a1a32122a0eebe6fbffa6cb609084f0f75b81e9be22fc2e8c39901f` |
| `docs/analytics/product-analytics-capacity-baseline.md` | `5518c40f3e1fb8c3b7848f0f7081254aa2481cb5de21944a3f36307d0fe93da8` |
| `docs/analytics/product-analytics-provider-rollback.md` | `e59c6e2987688ade44a2249b0978f9afe5d17409dd7c0be0e597475063aca2fb` |
| `docs/analytics/product-analytics-posthog-runbook.md` | `4bde983a10586a9a48035f5e4d6dff0add7c12b662ca0e90249a9f1c95e665cb` |
| `infra/posthog/runtime-guard.env.example` | `a317d1ade202e84a67d2ef7a1e7c8a630b91d3b77b452df236bc8f0178ce7f19` |
| `infra/posthog/backup-volumes.txt` | `d93524ea3fcb69915a96ec569e237c8991df2cbf0a2ad95614e77c35ced92aad` |
| `.dev/growth/f273-scoped-reading-authorization-2026-10-22.json` | `c3283ede037230a5f6b7cd7c0c11463c5e3e357d15e8627edbc945a7d642e0da` |


## Этап2, v1 — замороженная реализация guard/latch/readiness/alerts

**FAIL узкого реализационного среза: один блокирующий дефект G1 в API consumer.**
Requirements PASS этапа1 сохраняется; реализационное замечание не требует
новых требований, сервисов или возврата reviewer-owned отметок требований.
Исходный HEAD `a4f670630e0001c1aae6f0dc399aac088834ed15`, текущие изменённые
байты зафиксированы снимком ниже, не этим HEAD как готовым commit.

### G1 — API consumer принимает observed-state, который writer/guard отвергает (HIGH)

`provider_readiness.runtime_guard_blockers()` проверяет version/status JSON,
но не проверяет обязательный `reasons` и его code-only схему. При свежем
здоровом alert-state и protection-state
`{"protection_state_version":1,"status":"observed"}` функция возвращает
пустой набор blockers. При этом `posthog-capacity.transition(...,action=status)`
на том же файле отклоняет его с `protection_state_unverified`, поскольку reasons
отсутствует. Независимая локальная проба воспроизвела оба результата.

Таким образом, до следующего полного guard tick фактически известное
неподдержанное/повреждённое состояние может дать API ложную готовность и
провайдерный gate без блокировки. Наличие свежего старого alert-state не
исправляет повреждённое текущее состояние. Это противоречит уже принятому
требованию unknown без PASS и согласованным state-consumers.

Минимальная правка: API consumer должен отвергать отсутствие/неверный тип
reasons и неверные code-only элементы по той же минимальной схеме, что guard;
для observed состояние не должно скрывать незакрытые причины. Не требуется
новый сервис либо перенос shell helper в backend. Добавить регрессионную
проверку валидного observed и malformed observed (missing/list type/элемент),
сверив решение consumer с отказом guard. Не принимать будущие байты исправления
этим v1; после правки нужен новый снимок и профильная проверка.

### Что независимо подтверждено

- Latch записывается durable atomic_json до изменения switches; writer
  использует fsync файла/каталога. Отсутствие/невалидность исходного состояния
  не объявляются успешной защитой. Существующий helper/writer переиспользован.
- Один guard.lock сериализует обычные/операторские guard запуски; manual
  Restoration CLI берёт тот же lock. Успешный protected остаётся latched и
  не вызывает новый API restart при повторе либо исчезновении причины.
- apply/readback failure остаётся apply_failed; запрос переживает исчезновение
  первоначального симптома и повторяется. Действующий container Config.Env
  допускается только при State.Running и точном единственном значении каждого
  отключаемого ключа. Dry-run/auto-off имеют отдельные статусы и не заявляют
  выполненную остановку. State write error не является успехом.
- Shell вызывает соседний posthog-capacity.py; тот переиспользует соседний
  posthog-storage.py. Runbook устанавливает оба Python helper совместно с
  collector/inventory. Независимая проба с фактически скопированными малыми
  файлами под установленными именами graf-posthog-runtime-guard.sh,
  posthog-capacity.py и posthog-storage.py прошла: ошибка имени/относительного
  расположения не воспроизвелась.
- Независимые локальные guard-пробы с временными stub docker/curl/logger/
  collector подтвердили: low-space→protected, затем healthy symptoms при
  сохранённом latch и ровно одном restart; readback failure→apply_failed,
  затем healthy symptoms→retry→protected; два параллельных guard процесса
  выполнили один restart. API consumer блокирует валидный текущий latch.
- Прямо выполнена локальная существующая проверка transition/restore:
  запрос до protected, отказ неверного readback, неверных/expired/mismatched
  receipts, успешное ручное закрытие и отказ старого receipt для нового
  incident. Это проверка локальных metadata APIs, а не работающего контейнера
  или фактических T097 proofs.
- API consumer учитывает freshness самого guard и sample, expiry бюджета
  между ticks, бюджет/inventory SHA и текущий pre-switch latch; compose
  добавляет только read-only bind mount к API, существующая supplementary
  группа1001 переиспользована. Guard directory2750 и файлы0640 делают группу
  читателем; API не получает право записи. Эти permissions/mount описаны и
  проверены по коду, фактическая установка на узле не выполнена.
- Alert reader/rules понимают schema2, capacity failure и latched состояния,
  свежесть<120секунд/future; все новые коды имеют owner. Изменённая
  готовность операций отделена от provider configuration blockers, чтобы
  операционное закрытие не маскировалось статусом выключенного provider.

### Завершённые прогоны и границы доказательств

Первоначальный профильный прогон завершился **133passed,2warnings**, есть
конечные result=pass и isolated_container_removed; промежуточный вывод не
использован как результат. Дополнительный прогон actual delivery callers
после обновления двух старых fixtures завершился **36passed,1skipped,
2warnings**, result=pass и cleanup. Reviewer прочитал две добавки общего
write_runtime_guard и сверил их отдельные хеши. Browser skip не считается
выполненной браузерной проверкой.

Журналы предоставлены основным агентом, их конечные итоги/хеши сверены; reviewer
не повторял полные прогоны. Независимые пробы выше исполнялись локально с
временными подставными метаданными, без рабочего Docker/SSH, сети и внешних
отправок. Временные каталоги удалены. При первой сборке локального harness
был NameError из-за отсутствующего os в namespace; harness исправлен, после
чего все перечисленные guard-пробы завершились. Код продукта из-за этого
не менялся.

Все18 исходных/документационных хешей,4 requirements и2 дополнительных test
fixtures совпали до/после завершения проверки. Хеши обоих конечных журналов
совпали. Отметки требований сохраняются111checked/0open; они не являются
приёмкой runtime. Reviewer изменил только этот отчёт; код/spec/plan/tasks,
checklist, Git/GitHub, данные и рабочие настройки не менял.

Общая T116 требует исправления G1 и повторного узкого ревью текущих байтов.
T097 (реальные размеры, два замера≥24часа, рост/прогноз/нагрузка и операторское
принятие), выпуск/установка, рабочая проверка permissions, реальная доставка
оповещения и запуск трафика остаются самостоятельными открытыми воротами.
Ни nginx-t основного агента, ни локальные stubs не объявляются production
приёмкой. `git diff --check` выполнен после записи.

### Снимок этапа2 v1

| Группа | Файл | SHA-256 |
| --- | --- | --- |
| hashes | `apps/server/src/twobrain_rec_server/product_analytics/provider_readiness.py` | `eeaa5a80e68d93a922d16f999d84f95de50d1c4c878a46c68c8a0c85b7e736f1` |
| hashes | `apps/server/src/twobrain_rec_server/product_analytics/readiness.py` | `b8ac022bdc8588adcc98d93798866b2d78337ad714562d53ed2310e278d6b0e4` |
| hashes | `apps/server/tests/contract/test_analytics_degradation_alerting.py` | `db82f56625949b406f1af2dd9e15079fab45445c7d8c07ce8856f36165948577` |
| hashes | `apps/server/tests/contract/test_analytics_retention_enforcement.py` | `a3b896b8c49826885e02a5ae1876988159627d19f25f42a6e24d72cfb8dff0df` |
| hashes | `apps/server/tests/integration/test_product_analytics_provider_readiness_blockers.py` | `919b2162aa5a0c69fb77adb6444b7b5e5917293991b6f44a59369c807f417497` |
| hashes | `apps/server/tests/integration/test_product_analytics_yandex_page_scope.py` | `d2793d582aab75f411384e96e2d2f4a5af64f46c0f3532b94157895f2aa99f9e` |
| hashes | `apps/server/tests/unit/test_product_analytics_launch_approvals.py` | `2af594ee04097bdfbe381b7ea0a98c1638dbb3136e2a705dbe30f415a132607f` |
| hashes | `docs/analytics/product-analytics-capacity-baseline.md` | `2c4adb30a642aa9b0750e3932faaf45ec3b4537b5b0d694e7693e60218da8fb6` |
| hashes | `docs/analytics/product-analytics-posthog-runbook.md` | `db076bd564b5325aca34586515e6cc557fc97c51105656c9ef5f0630985ddd22` |
| hashes | `docs/analytics/product-analytics-provider-rollback.md` | `4048a73de064ae98987b675ff9c74ec5d35211ad887bfe3d074df88ba2d06e48` |
| hashes | `infra/docker-compose.yml` | `d5242bcde71f47ffdcef21cb9955903e28a7ea5df83150f34dd784b4079775e7` |
| hashes | `infra/posthog/alert-rules.txt` | `92fe7a8af1234f2adb9bd23449685305f4feef2eb70cb4c8464add0657160c7f` |
| hashes | `infra/posthog/graf-posthog-runtime-guard.service` | `2fe2ba898307f33aeff8ce1033c11be89f6299892c076ae0540ed3b40c4dc12e` |
| hashes | `infra/posthog/runtime-guard.env.example` | `ba2aa4d0c452e8fbbbec98a8fd3c6db6999141e4852e6dc24b59e755f269d1c3` |
| hashes | `infra/scripts/alert-analytics-degradation.sh` | `ac07001d9d74c2d32eb84651e2f68fb6d52bcf651aba5c47a437601db5b3657f` |
| hashes | `infra/scripts/posthog-capacity.py` | `ab552af4093a8a788e2b391d5e53106e56b77829f38e5e7f9537ff267242f07b` |
| hashes | `infra/scripts/posthog-runtime-guard.sh` | `7b2edddd233106220183eb73f03a9c034525a5f72e6a55c280457b9ae4f55455` |
| hashes | `apps/server/tests/fixtures/analytics_operations.py` | `5bcfcaf7fa6df0013e3daba665b540ad675874633c1fdd493bb994826ff9366f` |
| requirements | `specs/273-paid-traffic-analytics/contracts/operations.md` | `aef6aa9c7a494e3c99d57fa550e5c3eb164faa58404e35c9d6add53b104f7861` |
| requirements | `specs/273-paid-traffic-analytics/quickstart.md` | `6166abbcb98a6d626b48532f6632a20df9a36a1c22603a9e254c438883f35e8f` |
| requirements | `specs/273-paid-traffic-analytics/tasks.md` | `ee8ef3dc281eebeaf2f9deaf50b328a44ba3889b7e1116cc34f0ed8ebc1fde64` |
| requirements | `specs/273-paid-traffic-analytics/plan.md` | `0e0e5c3ee5d081c43d5b14f68f8a66d190d9b031cde6ae73c36f30844558a5e3` |
| additional_test_fixtures | `apps/server/tests/unit/test_product_analytics_provider_delivery_gate.py` | `d8cbacbcd490a5d2ecad5018197dee10e091660d28b0b7c656a6ba3abe29b069` |
| additional_test_fixtures | `apps/server/tests/unit/test_product_analytics_posthog_provider.py` | `7db8099e40bf5fcfff982798b3d9b53eb739662c5b802ca8028892d798f30042` |
| log | `.dev/growth/t116-guard-focused-2026-10-22.log` | `00748b0b77dc47d6c4588023e348d82a9ad54b87416e6b917493ebb7d00a82c5` |
| log | `.dev/growth/t116-delivery-focused-2026-10-22.log` | `9ba0105455f5fede9b81dce10bf454d7469f3ec6eb5c690e7680e6881772b2ac` |

## Этап2 v2 — повторное узкое ревью исправлений G1/G2

**PASS локальной реализации guard/latch/readiness/alerts на предъявленном
снимке v2.** Исторический FAIL v1 выше сохраняется; новые байты проверены
отдельно. Этот результат не принимает будущий перенос на другую базу,
фактическую установку, T097, выпуск или начало сбора рабочего трафика.

Проверен `.dev/growth/t116-guard-v2-snapshot-2026-10-22.json` на том же HEAD
`a4f670630e0001c1aae6f0dc399aac088834ed15`: совпали все20 файлов реализации,
4 требования и7 опорных SHA разрешённого ограниченного чтения. По сравнению
с полностью проверенным v1 изменены ровно4 файла ниже; остальные20 входов
сохранили уже приведённые хеши. Требования не менялись.

| Изменённый файл | SHA-256 v2 |
| --- | --- |
| `apps/server/src/twobrain_rec_server/product_analytics/provider_readiness.py` | `f49a4b60ea566540931639e6c28ac6170f02c72380543d7688ae1ea8ca10483f` |
| `apps/server/tests/contract/test_analytics_degradation_alerting.py` | `f21a9aaff11623b565a0b13f1156e67b45d43cb2f4b19dc30f81fcd2d19dd2f8` |
| `infra/scripts/posthog-capacity.py` | `764115bb4dee9056a5ee8f091256692d385c77e398da46749ec89bb272524948` |
| `infra/scripts/posthog-runtime-guard.sh` | `144884c16255ffe9b87d2c08cb2413f0d525fc33a6ace1650e46f72678d8bfaa` |

### G1 устранён

Consumer и transition теперь одинаково требуют `reasons` как список
строк-кодов `[a-z_]+`, а `observed` допускает только пустой список.
Независимое прямое выполнение локальной проверки подтвердило валидный
`observed`, а также отказ обеих сторон для отсутствующего поля, строки
вместо списка, `null` внутри списка, значения с пробелом и непустого списка
при `observed`. Валидная fixture текущего latch дополнена `reasons`.
Импорта shell helper в сервер и новых зависимостей не добавлено.

### G2 подтверждён и устранён

Предложенный основным агентом пограничный дефект независимо воспроизведён:
при пустом `breach` ошибка переноса `alert-state` выставляла
`rollback_failure=1`, но ранний `exit0` успевал вернуть успех и записать
`level=pass result=pass`. Для доказательства предыдущего поведения в
временной копии v2 удалена только новая проверка `rollback_failure` перед
веткой пустого `breach`; это восстановленный сценарий v1, а не неизменённый
архив всех его байтов.

Одинаковая независимая проба с именами установленного guard и соседних
helpers дала:

```text
reconstructed_v1 exit=0 write_failure=true pass_log=True
v2 exit=1 write_failure=true pass_log=False
```

В обеих пробах `breach_scope=none`, отсутствуют записанный `alert-state`
и перезапуск. Фальшивый `logger` подтвердил warning именно ошибки записи.
Дополнительная независимая проба ошибки `mktemp` для `alert-state.*`
на v2 также вернула `exit1`, warning и отсутствие pass-журнала при пустом
`breach`. Проверка поставлена перед ранним успешным выходом и покрывает
обе ветки ошибки записи без новой логики управления сервисом.

При первых двух попытках собрать дополнительную пробу reviewer ошибочно
искал сообщения `logger` в stdout: штатный helper отправляет их в logger,
а первоначальная заглушка их отбрасывала. Это ошибки локальной проверки;
после записи отдельного временного logger-журнала сравнение выше завершено.
Код продукта для проверки не менялся.

### Завершённая проверка v2 и сохраняемые границы

Предоставленный отрицательный контроль содержит **6failed,34deselected**
до исправлений; его SHA-256
`8bc0b73b81861f06fc1b0e09cec315b111023d50ccbedd99d3c338e819f0b1f0`.
Полный предоставленный повтор10 профильных модулей в
`.dev/growth/t116-guard-v2-focused-2026-10-22.log` завершён:
**175passed,1skipped,2warnings**, `postgres_test_result=pass`,
`postgres_test_cleanup=isolated_container_removed`. SHA-256 журнала:
`466d47fb2d5fdf08616af92598bbe3cbd5b0c70fbd4d8b73e8b2fc297921a56e`.
Reviewer проверил конечные результаты и хеши предоставленных журналов;
не заявляет независимый повтор всех10 модулей. Браузерный пропуск остаётся
пропуском.

Независимые G1/G2 пробы выполнены локально с временными метаданными и
заглушками Docker, curl, logger и collector. Реальные Docker/SSH/сеть,
рабочие данные, внешние отправки и production не затронуты; временные
каталоги удалены. В конце повторно сверены все24 входных SHA и HEAD.
Чек-листы перечитаны по отметкам: infra25/0, privacy-measurement45/0,
requirements16/0, security25/0; всего **111checked/0open**. Прежние
границы чтения требований сохраняются; отметки не менялись.

Открытых конкретных дефектов предъявленной локальной реализации guard
после G1/G2 не найдено. T097 с двумя реальными замерами≥24часа, измеренными
ростом/прогнозом/нагрузкой и принятием оператором, интеграция на новую базу,
выпуск/установка, проверка фактических permissions и реального оповещения
остаются самостоятельными воротами. Этот PASS не доказывает трафик или
продажи. Reviewer изменил только данный отчёт и проверил `git diff --check`.

## Этап3 — узкая проверка переноса T116 на принятую базу

**PASS переноса T116** на HEAD
`6cc9f0055e9b307ca8886c618b98844410efaf2e`, база
`25039ec43ee62e40a971e6a8d969bdfdaf0e840e`. Исходный принятый кандидат v2
сохранён в `aba5d5853dcc50017f21fcb22c61d53bb9d08564`.
Общий новый аудит не выполнялся; проверены различия переноса и сохранность
предыдущих доказательств.

Из20 входных файлов реализации T116 **19 совпали** с v2. Единственное
исключение — `infra/docker-compose.yml`, текущий SHA-256
`2ccd47187d07d00577adfc21cf0fe45222d37a5335665e4bf7a33b3c781e9a56`.
`git diff aba5d5853..HEAD -- infra/docker-compose.yml` содержит ровно
удаление `TWOBRAIN_PRODUCT_ANALYTICS_RETENTION_MIN_DAYS` и изменение
default `TWOBRAIN_PRODUCT_ANALYTICS_CONSENT_COPY_VERSION` на
`2026-10-22.1`. Оба изменения подтверждены непосредственно в принятой
базе master. Относительно базы compose содержит только уже проверенные
добавления пути guard в env и read-only bind mount; права записи и
настройки включения аналитики переносом не расширены.

Три из4 входов требований совпали с v2. Изменение `tasks.md` проверено
отдельно: после снимка добавлена историческая запись третьей части T116,
сохраняющая T116/T097 открытыми; при переносе из master пришло дополнение
о доказательствах T109. Критерии T116, operations, quickstart и plan не
изменены. Текущий SHA-256 tasks:
`a394c10ab1b7342c4a670125cd7b9a475fdf6d362f6ebdae399819a876b6679f`.
Дополнительно сверены **11/11 хешей реализации T115** с её снимком;
новая приёмка смысла T115 здесь не заявляется.

Предоставленный новый профильный журнал
`.dev/growth/t116-after-rebase-2026-10-22.log` завершился:
**175passed,1skipped,2warnings**, результат `pass`, cleanup
`isolated_container_removed`. Набор176 собранных проверок сохраняет digest
`8539d308c1ba29abd43524cd86d73659a3ff4d8b79feb68f561ee8d249c29550`.
SHA-256 завершённого журнала:
`63d0183475f0d04b5ee0b718c10ebcca912b3d2b854395ce0242e541b09bc5f4`.
Reviewer прочитал конечный итог;
самостоятельный повтор этого полного прогона и браузерная проверка не
заявляются.

Исторические FAIL/PASS остаются сохранены. PASS переноса не подтверждает
GitHub CI, выпуск, рабочую установку, T097, включение аналитики, трафик
или продажи. Reviewer изменил только этот отчёт; код, задачи, чек-листы,
Git/GitHub и рабочая среда не менялись. `git diff --check` пройден.
