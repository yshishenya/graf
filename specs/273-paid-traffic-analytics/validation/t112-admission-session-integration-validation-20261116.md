# T112 — ограниченная общая транзакция пары вех

16.11.2026. F273/T112/#7698, T113/#7804, `high-risk-product`.
Основа `8a7b43955e6abc1dcdac8d47f8cbfb16ff359ae7` плюс собственный diff.
Проект D1/D2 принят независимо: [повторный разбор](t112-admission-session-d1-d2-rereview-20261116.md),
SHA-256 `8af7b866817aba3dfc2fd83872583d6728a3433563f0c71b33cbd0359a703217`.
Текущая реализация и исправление C1 приняты независимым повторным ревью:
[scoped implementation PASS, P1=0/P2=0](t112-admission-session-precommit-rereview-20261116.md),
SHA-256 `ff6249cb0dd7160b94d20664d303a06be03776106569f0da0d766f2708c1eafb`.
Полный T112/T113 этим документом не закрывается.

## Что подключено

- Отдельный ResultAdmissionSession использует общую ограниченную RR Session,
  одно соединение и прежние числовые/SQL/временные ограничения. Компонент
  только для чтения не получает права записи.
- После будущего внешнего filesystem SH собственный start берёт DB SH advisory
  (273,3), затем сервис проверяет identity/session/membership/device и передаёт
  ту же Session настоящему source/projection verifier. Неподходящий, чужой,
  read-only или незапущенный owner отказывает до verifier.
- Только две прежние account-вехи, в фиксированном порядке и для закреплённых
  account/source. Один существующий primitive строит INSERT; его exact object
  исполняется через public AsyncConnection того же owner. Прямые DML, flush,
  commit и raw Connection не получают этого допуска.
- RETURNING содержит только UUID id. До исполнения консервативно расходуются
  1 строка/32 байта даже при конфликтном0, без возврата; полная строка читается
  прежним SELECT с общим numeric raw-byte/raw-shape preflight. Контракт
  `(row,created)` сохраняется; default caller получает дополнительный SELECT.
- Свежие gates проверяются перед каждой записью и commit. Список получателей
  перечитывается после ограничения statement и сравнивается с намерением
  построенного INSERT: изменение закрывает всю новую пару, не сохраняет
  устаревшее намерение. Внутри этого запроса нет отправки провайдерам.
- Единственная commit attempt отдельно расходует исходный SQL128. Ошибка,
  отмена и неизвестный исход не возвращают бюджет и не дают немедленного retry.
  Следующий отдельный показ разрешает прежние authoritative account keys.
- Единая пара work/cleanup передаётся без нового2s и повторного резерва0.5.
  Middleware сохраняет оба срока; read-only wrapper сохраняет прежний end.

Настоящий `_result_period_context` остаётся `yield None`. Положительные тесты
подставляют только внутреннюю границу периода, а не production trusted-флаг.
Filesystem guards/readiness/receipts/restore T113 здесь не изобретаются.
Рабочие настройки, данные, службы, почта, контент и вёрстка не менялись.

## Независимое замечание precommit

Reviewer обнаружил, что `commit_pair.recheck()` находился до try/finally.
Перехваченный внутри owner PermissionError оставлял разрешение на чтение и
повтор commit. Текущий сервис эту ошибку не перехватывал и откатывался;
замечание относится к самостоятельному persistent-refusal контракту owner.

Причинный тест сначала дал RED на прежнем owner477d2164:
1FAIL/55deselected,3.93s/runner7s,EXIT1,container_removed. Затем recheck,
checkpoint, резерв и разрешение commit перенесены внутрь прежнего
try/except/finally: отказ сохраняет failed и terminal до передачи ошибки.
Новая проверка перехватывает его внутри context, затем пытается читать и
повторять commit; все assertions результата расположены снаружи sanitizing
сервиса. Повторный независимый разбор подтвердил исправление C1 и всю
согласованную область подключения admission owner. Первоначальный HOLD
сохранён отдельно, без изменения исторического вывода.

## Проверки и пределы доказательств

| Проверка | Наблюдённый результат |
| --- | --- |
| Исходный обычный period Session, до реализации | 1FAIL/22deselected,3.35s,runner7s,EXIT1,container_removed: verifier вызывался без owner |
| Восемь файлов общего профиля до precommit исправления | 486PASS/0skips,185.86s,runner191s,EXIT0,container_removed; этот PASS не опровергает найденный затем дефект |
| Новый precommit причинный случай на старом owner | 1FAIL/55deselected,3.93s,runner7s,EXIT1,container_removed |
| Текущий admission/access после исправления | 87PASS/0skips,67.10s,runner71s,EXIT0,container_removed |

Полный профиль включает admission/access, Session44, numeric34, прежние
ledger/ingress/delivery и unit HTTP guard. После узкого precommit исправления
неизменные пути общего профиля повторно не запускаются без нового основания;
нового общего487PASS нет. Итог текущего профильного запуска фиксируется отдельно. После только линтерной
замены try/except/pass на suppress(PermissionError) новый precommit случай
повторно прошёл:1PASS/55deselected,4.14s,runner8s,EXIT0,container_removed.

Обычный полный60мин fixture:600 transcript+600 diarization,JSON,4 участника,
предыдущая встреча, default pinned outcomev2 при transcriptv3. Вся цепочка
source/projection/2INSERT/SELECT/commit проходит прежний envelope; полная
карта bindings совпала с исходной:94 SQL,1228rows,1224672bytes,1909nodes.
Число SET при сужении statement timeout зависит от остатка срока; пределы
не увеличивались. Общий reader fixture вынесен без изменения данных, прежнее
сравнение полного review сохранено и прошло общий профиль.

Реальные writer conflicts, phantom binding, RR40001 без retry, busy DB SH,
свежие gate/expiry, second INSERT/unknown commit, actual INSERT/deferred COMMIT
cancellation, delayed period/checkout, cleanup timeout и same-pool handoff
проверены. Нет утверждения о всех исходах TLS/reset/recycle/HTTP cleanup.

Первая новая provider-проба переключала gate по общему счётчику вызовов и
не задавала момент изменения относительно конкретного INSERT. Её FAIL не
считается причинным RED. Она заменена переключением непосредственно внутри
обёртки `_execute_insert`; исправленный случай вошёл в86PASS и затем486PASS.
Первый ошибочный запуск с путём apps/server/tests не собрал тесты (EXIT4,
container_not_started); он также не считается RED.

18 requirement inputs сверены SAME; четыре reviewer-owned checklist124/0
не изменялись. Analyze0252da92 и существующие T112/T113 mapping сохранены.
Перед сохранением: Ruff0.15.20 всех девяти исходников, agent-context,
changelog-fragments, prerequisite и `git diff --check` PASS. Первый вызов
системного Ruff0.2.1 дал несовместимые замечания; код по ним не менялся,
проверка повторена уже установленной закреплённой версией0.15.20.
Девять source hashes и два отчёта reviewer совпали с принятой картой.

## Сопоставление с оставшейся работой

Принятое подключение исполняет внутреннюю часть T112/T113 по проекту
1723f68c: одна ограниченная RR-сессия, exact INSERT прежнего примитива,
единые сроки и терминальный отказ. Источник периода, filesystem/readiness,
HTTP выдача/обновление/приём и полный максимальный объём данных остаются
частичными или отсутствуют. Они уже входят в открытые T112/T113;
новых дублирующих task ID и отметок завершения нет. Это сопоставление
текущего среза, а не полная сходимость всей F273. `tasks.md` и требования
сохранены побайтово. После implement нет включённых hooks;
выпускные и рабочие проверки этим сохранением не выполняются.

## Точные исходники и журналы

SHA-256 исходников ниже сверены с независимым повторным разбором. Сам отчёт
не является exact-SHA CI, слиянием, выпуском или рабочей готовностью.

| Путь | SHA-256 |
| --- | --- |
| `apps/server/src/twobrain_rec_server/api/product_analytics_guard.py` | `de069df2ecf27abc99f185d4591bf44b06df22149a165bec6b629cdf6e35f3b9` |
| `apps/server/src/twobrain_rec_server/cabinet/result_projection_budget.py` | `2dd1047bd35c69f40532389ec1c37a3957f20a7f6c6044f896b2403cc866d934` |
| `apps/server/src/twobrain_rec_server/cabinet/result_projection_session.py` | `60311e805510146be860f844e53931fe9570ae56d47eaf5fa1c9d6764ba37e01` |
| `apps/server/src/twobrain_rec_server/product_analytics/ingest.py` | `64d2a716584b9164744cfb1d9a575a03d1b27d39b2e3088157ebd9532e0b8e7f` |
| `apps/server/src/twobrain_rec_server/product_analytics/milestones.py` | `b00d925dc803c198f53de3ed098d968288efa8f7c606390c1a7c23855a82472a` |
| `apps/server/tests/contract/test_result_projection_session.py` | `c4f8880960f241d9b1b8d00587b35fff9446dfcd15c9c2ecdec0e5addf167458` |
| `apps/server/tests/contract/test_result_view_access.py` | `e647d5235091d22e8515f8081abf86ea7fe3a3335be18b7141dcae359e670d4f` |
| `apps/server/tests/contract/test_result_view_admission.py` | `44e51f37cad630576af337c07012d011d219f109f0d589ed9eef587015306269` |
| `apps/server/tests/unit/test_result_view_http_guard.py` | `3bb30a6a0aca16a2cb38d993e04034a0b12b26297e67b4479989bd21225607a6` |

| Журнал вне Git | SHA-256 |
| --- | --- |
| `/private/tmp/graf-t112-admission-owner-red-20261116.log` | `4ce336a518848d6aa1d305b72c562f17f53d4f6ab247dec8a543ada9a910a4f2` |
| `/private/tmp/graf-t112-admission-owner-accepted-green-20261116.log` | `d4ac1e1bb04a506bdbf77d87278bde914129c8819124dd2328febab1cc74b950` |
| `/private/tmp/graf-t112-admission-precommit-red-20261116.log` | `3c1a71f090e2d9ed64832c7c124745d9fd24f2c137137fc519b60fc75b0f3997` |
| `/private/tmp/graf-t112-admission-precommit-green-20261116.log` | `64958af4aed8f9794d18c2328645c52fafb45eb44754b6b30208809caa33f022` |
| `/private/tmp/graf-t112-admission-precommit-lint-green-20261116.log` | `dcc5f9c90ea32ce898f8ad59128e9d522d25599c042a6e69e06874d6216d95ae` |

## Открытые обязательства

Runtime verifier T113, filesystem ownership/fences и настоящие
readiness/backup/restore/ресурсы,
HTTP issuance/renewal и защищённый обработчик, максимальный envelope и
непокрытые cleanup исходы остаются обязательными. T112/T113/измерение/T0 и
коммерческая цель открыты. PR/merge/CI/Full/CD/рабочего включения нет.
Истёкший T098 не продлевается, направления не удаляются ради PASS.
