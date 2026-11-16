# T112 — подключение ограниченной сессии к общей транзакции

16.11.2026. Точная основа `c78a3222c5f3f5a622f7d9c4eb56aea29967d77e`.
Существующие F273/T112/#7698 и T113/#7804, `high-risk-product`.
Это проект следующего изменения до кода; независимая оценка ещё требуется.
Контент, вёрстка, рабочий сбор и инфраструктура не меняются.

## Проблема и сохраняемые требования

Самостоятельный read-only owner принят после R1–R4; Session source95108da9,
testa39d6f25, независимый отчёт24cd545c. Он запрещает любой INSERT/commit.
Общая `_account_transaction(require_period=True)` уже умеет две account-вехи,
но получает другую, пока неограниченную Session из подставленного периода.
Механически разрешить DML в read-only owner или отключить listeners перед
commit нельзя: это снова откроет произвольные записи и обходы чтения.

Сохраняются договор result-visibility §§2/3/5/7, activation-milestones
«Первый локальный период» и проект295ce2c. Одна свежая RR Session, тот же
DB connection/снимок/счётчик/срок от начала до commit/rollback/close.
Пределы исходного envelope не повышаются. Порядок filesystem SH → DB SH
advisory(273,3) → identity/session/membership/device → Meeting/source/result.
Shared locks и свежие проверки остаются до единственного commit пары.
Чужие Session/Connection, raw SQL, DML CTE, SKIP LOCKED и ORM flush запрещены.
После любого неизвестного исхода нет refund/retry; failed сохраняется.

## Предлагаемый минимальный путь

1. Read-only `result_projection_session` остаётся с прежними полномочиями.
   Общий внутренний context manager переиспользует создание/срок/очистку
   сессии. Отдельный внутренний admission owner имеет фиксированную операцию
   записи двух прежних событий; нового публичного флага read_only/trusted нет.
   Его db передаётся verifier, права записи остаются у owner/ingest.
2. `_AccountAdmissionContext` для require_period содержит именно admission
   owner и его db. Несовпадающая/посторонняя/обычная Session закрывает путь.
   Настоящий `_result_period_context` по-прежнему `yield None`: он не создаёт
   доверенный started_at, receipt или фиктивную readiness. Положительный
   тест явно подставляет контекст периода и использует настоящий owner.
   Будущий T113 source обязан получить filesystem SH перед входом в owner
   и держать до разрешения DB исхода/очистки. Fixture не доказывает это.
3. Admission owner начинает RR до первого SQL. Через один фиксированный
   контрольный SELECT получает неблокирующий PostgreSQL shared transaction
   advisory(273,3); false означает отказ. SQL учтён, перепроверка namespace
   не делегируется произвольной функции из клиента. Два SET и tenant setup
   остаются фиксированными контрольными операциями, без numeric recursion.
4. `_account_transaction` и `_lock_result_session` для result-пути используют
   owner.tenant вместо неограниченного apply_tenant_context. Identity/session/
   membership/device/Meeting/source/readiness SQL проходит тот же numeric
   preflight и реальные before_cursor detectors. RR40001 после конкурентной
   смены закрывает вызов без повтора. Обычный server-auth путь без периода
   сохраняет прежнее поведение и не принимает result/value из client JSON.
5. После полного свежего verifier и построения двух безопасных payload owner
   допускает ровно два последовательных вызова существующего
   admit_account_milestone: first_result_viewed, first_value_session_completed,
   прежний account/source. В самом SQL-примитиве одна необязательная внутренняя
   точка выполнения конечного INSERT позволяет передать точный построенный
   statement owner. Существующие callers без неё используют db.execute.
   Это повторное использование прежнего SQL/ledger, не копия его реализации.
6. Точка выполнения разрешает только текущий exact statement из этого
   фиксированного вызова и ровно одно фактическое cursor execution. Прямой
   db.execute того же table, произвольный INSERT/UPDATE/DELETE/raw Connection
   и .flush не получают разрешение. Никакого общего allow-writes context нет.
   Для RETURNING выбран фиксированный scalar UUID `id`, а не полный ORM row.
   В общем SQL-примитиве меняется `.returning(ProductActivationMilestone)` на
   `.returning(ProductActivationMilestone.id)`; после результата обоих исходов
   выполняется прежний SELECT по account/event. `created` определяется наличием
   возвращённого ID, row/created контракт сохраняется. Это один общий код,
   без разбора частных Insert._values и без отдельного ledger или копии SQL.
   Новая строка возвращается обычным SELECT через numeric preflight; старый
   duplicate SELECT сохраняется. Default callers получают один дополнительный
   SELECT после успешного INSERT и тот же payload/ORM row.
   До INSERT owner консервативно резервирует одну возможную строку/32bytes
   фиксированного UUID, даже если позже ON CONFLICT вернёт0, без refund.
   RETURNING не может вернуть JSON/неограниченную колонку: exact statement
   строится только прежним внутренним SQL-примитивом с фиксированным id.
   Последующий SELECT расходует row/byte/JSON budget как любой другой read.
   Связь admission с конкретным построенным statement остаётся обязательной;
   прямой db.execute похожего INSERT не получает разрешение.
7. Свежий общий gate/recheck до каждого INSERT и перед commit остаётся.
   Время проверяется до и после синхронного catalog/JSON/digest/gate кода.
   Только owner завершает транзакцию после обоих вызовов; verifier не может
   выполнить db.commit/Connection.commit/rollback и затем продолжить.
   До разрешённого commit проверяется счётчик/срок/failed и пустые new/dirty/
   deleted. Connection commit event допускается только на коротком собственном
   commit-вызове, один раз; случайный before_flush остаётся отказом.
8. Commit не является before_cursor_execute. Его единственная попытка
   дополнительно резервируется в том же пределе128, отдельно от уже учтённых
   SET/numeric/original/INSERT cursor executions. При нехватке срока/лимита
   до commit — rollback; потеря подтверждения после отправки commit — unknown,
   False без повторения, следующая новая видимость разрешает старые ключи.
   После commit owner терминален, новое чтение/новая транзакция запрещены.
9. Один absolute work deadline и отдельный cleanup reserve идут от внешнего
   запроса; вложенные операции не создают новые2s. При отдельном внутреннем
   вызове срок начинается до входа в период. Нынешний HTTP guard уже хранит
   work deadline в request.state; будущий handler передаёт его прямо и не
   прибавляет новый резерв поверх. Read-only tests сохраняют свой прежний срок.
   Close не shielded, при отказе завершает только ещё принадлежащий owner
   driver, а не уже переданное replacement Session соединение. Listeners
   снимаются finally. Полные precheckout/HTTP cleanup гарантии этого шага
   отдельно доказываются, существующий частный PASS не переносится на них.

## Причинные проверки до приёмки

- RED: нынешняя require_period Session не имеет общего SQL/raw budget/RR;
  неверный context/чужая Session не должен вызывать verifier.
- Обычный полный60мин путь с600+600 сегментами и pinned/current источниками
  проходит всю identity/session/tenant/projection/обаINSERT/commit цепочку
  в исходном envelope, полный результат и старый payload не меняются.
  Если не проходит — HOLD проекта, а не уменьшение fixture/увеличение caps.
- Только две заданные операции. Direct DML/commit/flush/rawConnection в
  verifier, лишнее/переставленное событие, и ошибка после numeric дают
  persistent failed, отсутствие новой частичной пары и последующего SQL.
- Смена gate/expiry перед вторым INSERT и commit, второй INSERT failure,
  unknown commit и последующая новая видимость, listener/pool reuse,
  отмена внутри исполняемого SQL и commit/close; никаких surviving tasks.
- Реальная writer mutation до snapshot/после получения locks и phantom
  binding/source/result insert: свежий отказ либо writer ждёт/получает
  ограниченный отказ. Используются фактические продуктовые writer fences.
- Две RR сессии: победитель сохраняет пару. Конкурентный40001 может дать
  unavailable; немедленного retry ради двух accepted нет. Следующий отдельный
  настоящий показ разрешает authoritative keys. Это отдельно от replay
  на новом снимке и не разрешает потерю уже сохранённого payload.
- Настоящий закрытый период по-прежнему не вызывает verifier и не пишет.
  Existing non-result ingest/auth/ledger/delivery и read-only owner сохраняют
  регрессии. Новая точка SQL-примитива тестируется с обоими callers.

## Ограничения и следующий шаг

Runtime verifier T113 с readiness/backup/restore/ресурсами и настоящими
filesystem guards не выдумывается данным проектом. Источник закрыт и после
подключения owner, пока T113 не реализован и не принят. Это реальное
подключение недостающего ограничения общей транзакции, а не доказательство
готовности измерения. HTTP issuance/renewal и максимальный envelope остаются
обязательными частями полного результата. Новый issue не нужен.

До кода независимый reviewer должен подтвердить точку допуска INSERT,
учёт RETURNING/commit, полномочия Session и единый срок. Неясный узел
означает доработку проекта; код не начинается по общему одобрению направления.
