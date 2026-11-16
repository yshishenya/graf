# T112 — независимый проект ограничения материализации проекции

16.11.2026. Проверяющий: `/root/public_counter_readiness_review`.
Рабочая копия: `/private/tmp/graf-f273-result-visibility-20261116`.
HEAD: `eea992190c92e57b2cceaa199c2bcbd94ff71614`.
Полоса: TEST/RUNTIME DESIGN существующих F273/T112/T113, high-risk-product.
Разрешённое изменение проверяющего — только этот отчёт.

## Решение и точный предел

**HOLD проекта session-scoped проверки точного SELECT: P1=0/P2=1.**
Ранний REPEATABLE READ допустим для согласованного множества строк, но двух
исполнений одного LIMIT запроса недостаточно для доказательства одной и той же
строки. Найденное условие H1 ниже необходимо закрыть до кода этого варианта.
Ниже сохранён конкретный проект и причинный профиль; последний раздел H1
задаёт безопасный способ исправления. Это не runtime дефект: новый HTTP путь
ещё не подключён, preflight отсутствует и настоящий T113 закрыт.

**HTTP hookup, настоящий T113, измерение/T0 и выпуск остаются HOLD.**
Устойчивый снимок решает соответствие объёма двух чтений; он сам по себе
не доказывает свежесть legal/readiness/session/source до commit. Обязательства
по действующим writer fences перечислены отдельно ниже. Настоящий закрытый
`_result_period_context` сохраняется. Настоящий отчёт не разрешает его заменить
датой, флагом или готовым True, ни включить рабочий сбор в этом срезе.

Прежние idle Pool.close и 294 теста не проверялись повторно. PostgreSQL,
HTTP, браузер, приложение, production isolation и рабочие данные не читались.
Все результаты ниже — проект и самостоятельное чтение исходников.

## Проверенные входы и применимость

Прочитаны main-owned `t112-projection-budget-map-20261116.md`, актуальные
применимые разделы собственных `t112-http-preflight`, `t112-server-preflight`
и `t112-view-selectors-review`, исходники общего reader/source/binding,
календаря, доступа, итогов, аудио и двух историй действий. Карта основного
исполнителя не изменена. Статический инвентарь 193 функций/31 модели использован
как дополнительный указатель; в нём есть annotations, batch/коррекция и
storage-ветви, недостижимые из текущего вызова. Он не является полным
доказательством динамического множества чтений.

Неизменные 18 входов требований/ревью сверены побайтно по SHA-256, полный
перечень в конце. Использовано собственное прежнее чтение того же диалога,
восстановленное по оригиналам применимых разделов. Чужая карта чтения не
выдаётся за новое полное чтение PRD/всей истории. Для этого среза применимы:
result-visibility §§2/3/5/7; activation-milestones и существующий T113;
spec Session16.11/FR-021/025/SC-006; plan/tasks/quickstart T112/T113;
research/data-model account decision и transient proof; constitution privacy,
deletion и delivery gates; PRD backend/detail/privacy/observability;
product-gates metadata-only evidence, data/AI/deletion boundaries.

| Reviewer-owned список | Отмечено | Открыто |
| --- | ---: | ---: |
| requirements |16|0|
| security |27|0|
| privacy-measurement |52|0|
| infra |29|0|
| Всего |**124**|**0**|

Отметки не менялись. Это качество требований; 124/0 не является приёмкой кода.

## Фактическая область общего чтения

`load_fresh_result_view_bindings()` сначала вызывает `lock_meeting_fence()`:
тот уже возвращает полный ORM Meeting. Самостоятельно прочитана текущая
`db/models/meeting.py`: там String(N), UUID, числа и даты, нет Text/JSON.
Это ранняя материализация, но не пример неограниченной нынешней строки.
Её можно покрыть доказанным фиксированным schema byte envelope либо общим
числовым guard; нельзя объявить, что до getter вообще не было ORM load.
Последующая Workspace и другие большие модели всё равно требуют проверки.

| Ветвь | Что фактически материализуется и должно проходить проверку |
| --- | --- |
| queries.py:1464, prefetch | Workspace; revision/workflow; current и effective result; default/selected slot, outcome, собственный result и SummaryTemplate; accepted revision, artifact policy, normalization job/canonical TrackArtifact, finalized UploadSession, calendar link, dependency, personal default template, latest generation attempt. Каждый lateral LIMIT1 всё равно загружает все выбранные scalar/JSON поля |
| queries.py:1653 | Полный Meeting; explicit source_result той же ревизии; все TranscriptSegment и DiarizationSegment выбранного result; все MeetingSpeakerName встречи, с последующим Python-фильтром; default/selected итог и template; summary_progress с возможным fallback на полный attempt/pinned outcome/result |
| access.py:477/635/896 | Даже owner читает активную WorkspaceMembership. Предыдущая встреча может принадлежать другому человеку: user/workspace grants, полный UserIdentity viewer и все verified ExternalIdentity.email при соответствующей ветви metadata; отсутствие owner-проверки для предыдущей встречи нельзя предполагать |
| access.py:948/969 | Все активные grants; все подходящие invitations, включая ciphertext/delivery поля при отсутствии ключа; полный UserIdentity каждого grantee через db.get, а не только безопасное имя |
| calendar/service.py:964/1165/1212 | Текущий Meeting/link; исходный candidate_event_ids_json до Python-разбора; до10 уникальных допустимых UUID. Для каждого сначала полный CalendarEventSnapshot, затем CalendarSource, ExternalCalendar, только затем часть workspace/owner/visibility отказов. Нельзя проверять размер лишь строк current workspace: реально загружаемые ошибочные foreign candidate/source/calendar тоже покрываются. Numeric participant count плюс до100 полных CalendarParticipant |
| queries.py:2145 | Полная пара RecordingCalendarContextLink + Meeting другого meeting_id: тот же series hash, более раннее время, matched_auto/user, order start DESC/link.id DESC, LIMIT1. Затем access, latest revision/result и current default outcome/его source result. Общий getter рекурсивно не вызывается, но вторичные таблицы этой встречи читаются |
| queries.py:2233 | В legacy_linked ветви все CalendarParticipant snapshot, без LIMIT. В snapshot ветви matched_roster_json уже загружен полностью до среза первых100 |
| egress.py:1440/1527/1597 | Общие effective result/policy/current outcome; принятая revision, upload archive, normalization job, canonical TrackArtifact. storage=None убирает обращение к объектному хранилищу, но оставляет эти DB-чтения |
| processing/store.py:1763 | MediaRevision с manifest/track_sha256_by_role и все соответствующие stored TrackArtifact до проверки дубликатов/ролей. Ограниченное число ролей не доказывает ограниченное число фактически загружаемых строк |
| egress.py:2651; calendar/audit.py:182 | До50 полных строк каждого журнала. Последующее безопасное представление и общий срез50 не ограничивают bytes ORM-записей |
| result_visibility.py:203/292/362 | Полные Meeting/MediaRevision/ProcessingResult/ProcessingWorkflow для каждого действительно показанного transcript/outcome source, включая другой pinned result. UploadSession и IngestAuditEvent в lineage EXISTS участвуют в SQL, но не материализуются как полные модели этой выборкой. Numeric/two-ID outcome read тоже проходит общий контроль, без выдуманного чтения его остальных полей |

`include_calendar_correction_candidates` в рассматриваемом fresh вызове не
передан и по существующему default равен False. Это наблюдение текущего вызова,
не предложение выключить работающую ветвь. Обычные owner candidates, roster и
previous recurring остаются. Если существующий caller включает коррекцию,
универсальный контроль фактических SELECT обязан охватить и её дополнительные
источники/события; неизвестная форма закрывает только аналитику.

## Выбранный способ: одна сессия, один снимок, контроль каждого SELECT

1. Общий service owner T113 создаёт новую отдельную AsyncSession. До tenant
   SET/любого readiness/auth/query вызывает публичный
   `await db.connection(execution_options={"isolation_level": "REPEATABLE READ"})`.
   Такой порядок уже показан в `notification_snapshot_db`, notifications.py:35–44;
   это образец выбора isolation, а не доказательство готовности T113.
   Нельзя передать уже начавшую SELECT сессию или скопировать её identity map.
   Позднего SET TRANSACTION, смены глобальной engine factory и второй commit
   boundary нет. Tenant context далее единственный и не меняется во время чтения.
2. Владелец устанавливает на **свою** сессию узкий guard материализации.
   Действующий порядок filesystem SH → DB SH xact advisory(273,3) → identity
   → session/membership/device → meeting/source/result сохраняется. Управляющие
   SQL с побочным эффектом, в том числе advisory-lock функции, **не повторяются**
   числовым preflight. Они остаются отдельными фиксированными bounded control
   statements владельца; модельные SELECT охватываются до первого полного row.
3. Guard получает **тот же Select, фактические bind parameters и projection**,
   который сейчас собирается исполнить Session. Не восстанавливает их по
   meeting_id и не угадывает ветку. Возможный механизм — публичный локальный
   SessionEvents.do_orm_execute на sync_session данной AsyncSession, а числовой
   SQL через то же adapted connection. Это проект; фактический охват scalar,
   scalars, execute и get проверяется обязательным RED, а не предполагается.
   Одной обёртки AsyncSession.execute недостаточно: scalar/get/identity map
   могут обойти такой override. Глобальный event listener не устанавливается.
4. Для обычного детерминированного SELECT строится SQL subquery Q из **всей
   исходной выборки**. Сохраняются WHERE/JOIN/LATERAL/DISTINCT/ORDER BY/LIMIT,
   параметры и все реально выбираемые колонки. Над Q ставится дополнительный
   внутренний предел `remaining_rows + 1` для числового контроля; он не меняет
   фактический продуктовый запрос. Даже db.scalar(select(Model)) без LIMIT
   проверяется как потенциально весь набор: scalar не является DB LIMIT1.
   В Python возвращается одна фиксированная строка чисел/признаков переполнения,
   а не IDs всех строк, JSON, текст или ORM model.
5. COUNT, SUM/MAX UTF-8 octet lengths и JSON shape считаются в PostgreSQL.
   `octet_length(to_jsonb(q)::text)` допустим как консервативный верхний размер
   целой реально выбранной строки: включает выбранные большие scalar/JSON,
   в том числе поля, которые view затем не использует. Для field maximum
   нужны все выбранные variable-length поля, а не только text transcript.
   JSON/array/binary приведения учитываются явно; неизвестный тип/форма SELECT
   дают unavailable. Один pg_column_size недостаточен: TOAST/compression не
   ограничивает разжатый текст/JSON и последующее Python-представление.
6. Row locking исходного SELECT **не удаляется частным API SQLAlchemy**.
   Для текущих точечных FOR UPDATE/FOR SHARE числовой SQL может сохранить
   locking SELECT внутри Q: rows блокируются на сервере до передачи полного
   объекта. Поэтому даже первый lock_meeting_fence сначала получает числовой
   ответ о bounded Meeting. Блокировка принадлежит той же транзакции и остаётся
   до решения owner. Нужен отдельный PG тест SQL-формы и lock mode. Запросы
   SKIP LOCKED, volatile/side-effect SELECT/CTE или недоказанная трансформация
   не допускаются в повторяемый preflight. Неизвестную форму нельзя исполнить
   без проверки или молча переписать в похожий запрос.
7. После положительного числового контроля исполняется **исходный** SELECT,
   затем неизменный общий getter/binding. Guard остаётся включённым до конца
   getter, source и binding reads, включая поздние fallback/get. Внутри этой
   фазы нет DML/flush/изменения tenant context: autoflush выключен, сессия новая,
   нет внешних prefetched/ORM объектов и неограниченного уже заполненного cache.
   Любой объект в её identity map должен происходить из проверенной загрузки.
   Предварительные SQL не запускают рекурсивно сами себя и не учитываются как
   продуктовая материализация. Обход через raw connection/text SQL не становится
   разрешённой ветвью: неподдержанный read закрывает аналитику.
8. Счётчики расхода общие для всей проверки, включая повторные SELECT,
   root fence и source bindings. Не обнуляются на helper/модель/второй блок.
   Read count также ограничен. Этот guard — свойство конкретной сессии/фазы,
   не новое клиентское право, конфигурационный флаг T113 или общий SQL framework.
   Если его фактическое безопасное подключение нельзя доказать публичными API,
   этот вариант останавливается до нового независимого проекта; нельзя выдать
   частичный execute wrapper за полный guard.
9. Затем общий owner выполняет существующие свежие guards, пару admission
   и единственный commit. Proof/accepted/renewed выдаются после успешного выхода
   владельца. Фаза чтения сама не создаёт durable запись. Guard/event hook
   обязательно снимается в finally; другая сессия и обычный просмотр не меняются.

Условие соответствия (пока не доказано для всех Q): каждое последующее
материализуемое поле должно входить в проверенный SQL envelope. Один MVCC
snapshot исключает внешнее увеличение read set, но не выбор другого члена
неоднозначного LIMIT множества. Поэтому равенство SQL/параметров недостаточно
без доказанной детерминированности всех вложенных selectors либо числового
superset всех допустимых вариантов. Новые calendar/grant/previous записи после
snapshot не видны A; неоднозначные существующие строки внутри snapshot при
этом остаются возможной причиной H1. Новые блокировки календарных writers
для размера не предлагаются. Свежесть прав/source отдельно обязательна.

Преимущество для проверки полноты: новый динамически достижимый SELECT не
теряется из-за пропущенной зависимости в ручной таблице. Таблица выше остаётся
списком обязательных причинных случаев для доказательства самого guard.

## Явные числовые границы и синхронная работа

Следующие значения — конкретная консервативная исходная настройка **проекта**,
не измеренный безопасный предел текущей машины. До принятия кода нужны
описанные ниже граничные проверки. Изменение констант требует того же профиля.

| Измерение | Кандидат верхней границы включительно |
| --- | ---: |
| Материализованные строки одной фактической выборки |4096|
| Строки всех выборок одной проверки, с повторными чтениями |16384|
| Суммарные логические UTF-8 bytes выбранных строк |8 MiB|
| Bytes одной выбранной строки |512 KiB|
| Bytes одного variable-length выбранного поля |256 KiB|
| Число фактических SELECT проекции/source/binding |128|
| Глубина любого выбранного JSON/array |32|
| JSON узлы одной проверки, включая повторные чтения |65536|

Отказ при cap+1, неизвестности, SQL timeout/serialization conflict. Коллекции
и JSON не сначала загружаются в Python для проверки. JSON depth/node count
вычисляются числовым bounded traversal на стороне БД после byte envelope;
при достижении depth/node cap+1 достаточно переполнения, обход прекращается.
Объект с одной огромной строкой, глубоким JSON, множеством пустых элементов,
Unicode и сжимаемыми повторяющимися полями проверяется отдельно. Отсутствие
значения/NULL имеет определённый нулевой расход; bytes считаются UTF-8, а не
числом Python символов. Пределы не режут продуктовый transcript/roster/outcome.
Большой результат остаётся доступным пользователю; у аналитики нет proof.

Один абсолютный POST срок2s включает всё окружение. Для каждого SQL timeout
не более min(500ms, оставшийся бюджет), для lock min(250ms, остаток).
Нельзя дать каждому из128 SELECT собственные независимые2s. Пул/подключение,
tenant setup, commit и cleanup уже входят в принятую внешнюю границу;
старые idle-close проверки этим проектом не пересоздаются.

Один asyncio timeout не прерывает синхронные model/JSON/digest операции.
Нужна проверка остатка **до** такой фазы и после неё/перед каждым INSERT,
renewal и commit. Профиль максимальных допустимых rows/bytes/JSON и худшего
пересечения transcript/diarization обязан показать приемлемое полное время.
Если он не помещается в общий срок, уменьшить внутренние аналитические caps
либо отдельно пересмотреть bounded алгоритм; не увеличивать2s и не обрезать
показанный текст. Пока этого доказательства нет, runtime budget не принят.

Для GET отдельно: уже построенный продуктовый render review не прошёл новый
DB guard и мог отличаться от fresh snapshot. До digest его старого содержимого
нужен bounded in-memory shape/length precheck; можно консервативно ограничить
число элементов и4*len(str) без выделения неограниченного UTF-8 буфера.
Неизвестная/слишком большая старая projection → отсутствие enrichment, прежний
HTML сохраняется. Fresh guarded review не подменяет текст старого render;
proof выдаётся только при полном совпадении текущих общих bindings.

## Свежесть и реальные writers: что снимок не заменяет

Самостоятельно прочитан `processing/fences.py:38`: lock_meeting_fence —
FOR UPDATE Meeting с populate_existing. В исходниках подтверждено применение
того же fence в сохранении speaker name, baseline outcome/source-проверке и
processing recovery. Это конкретные примеры координации, не доказательство,
что все календарные, grant, auth или legal writers берут этот Meeting lock.
Поэтому проект **не выбирает** его как единственную защиту объёма вложенных
зависимостей: для объёма выбран RR snapshot.

Для авторизации и admission действуют отдельные прежние обязанности T113:

- Shared identity/status lock должен конфликтовать с account close/purge;
  session/membership/device блокируются режимом, конфликтующим с non-key
  status/binding UPDATE. FOR KEY SHARE один этого не даёт.
- Текущий source/revision/result, selected/pinned outcome и deletion должны
  оставаться допустимыми до commit за действующими product writer fences.
  Проверка bounded previous meeting/calendar snapshot не доказывает current
  source и не добавляет эти данные в аналитический payload.
- В RR locking read строки, изменённой после snapshot, может дать40001.
  Это unavailable без retry, а не повод вернуться к READ COMMITTED или принять
  старый ORM объект. Нельзя ловить конфликт и продолжать ту же транзакцию.
- Особенно важно: snapshot мог появиться при первом SELECT setup/advisory
  lock **раньше** последующего lock. Новый отзыв/закрывающая запись может
  оказаться phantom, а неизменившаяся parent-строка не выдаст40001. Поэтому
  RR и одна SH блокировка не являются доказательством свежести предиката.
  Для настоящего T113 нужно собственное доказательство каждого такого writer:
  действующая конфликтующая coordination/locked version-row, которую writer
  действительно меняет, и тест mutation-first/analytics-first. Новую фиктивную
  version-row/глобальный advisory lock без участвующих writers здесь не вводить.
- Legal/disclosure/withdrawal, readiness/mode/resource guard проверяются перед
  каждым INSERT и перед выдачей/commit по прежнему контракту. Нельзя заменить
  их повтором SELECT, который в RR просто снова видит старое отсутствие отзыва.
  Непокрытый writer/predicate означает закрытый T113, даже если размер совпал.

Это явное ограничение проекта: отдельное исправление H1 не доказывает,
что будущая механическая смена isolation готового T113 безопасна.
До рабочего подключения конкретный владелец должен
принять и доказать оба свойства: bounded snapshot и авторитетную свежесть.

## Причинный RED/GREEN профиль следующего исполнения

Все данные синтетические в изолированной PostgreSQL; нет повторного приёма
реального аудио, рабочего T0 или provider запросов. Сначала один RED на
большую вторичную строку и одна реальная PG гонка, затем оставшийся профиль.

1. **Guard interception RED.** Spy до ORM instance/load и driver получения
   исходного row. По отдельности execute/scalar/scalars/db.get, including
   first Meeting fence, prefetch LATERAL, fallback summary attempt, source
   binding. До исправления огромная строка достигает materialization; после
   отказ возникает раньше. Не считать spy только на входе getter достаточным:
   getter мог законно начаться, пока поздняя выборка ещё не была проверена.
   Проверяются также cached object из предыдущей/непроверенной сессии,
   recursive preflight, listener cleanup и независимость другой Session.
2. **Большая побочная строка.** По одному cap+1 полю, где schema это допускает: Workspace,
   result/workflow, slot/outcome/template, revision manifest/digest mapping,
   normalization/artifact/upload/attempt, grant/invitation/grantee,
   calendar candidate/snapshot/source/calendar/participant, обоих журналах.
   В частности: LIMIT1/50/100 не спасает; foreign candidate/grantee и legacy
   roster обязательны. Проверять и потенциально unused ORM поле, а не только
   отображаемое имя. Для полностью String(N)-ограниченных Meeting/dependency/
   workflow не обходить ограничения schema ради невозможного гигантского поля:
   проверить достаточный фиксированный envelope или реальную cumulative границу.
   Отказ до model load именно плохой строки,0 ledger/provider.
3. **Rows/bytes/shape boundaries.** cap-1/cap/cap+1 для query и cumulative
   расхода; один text/JSON row, много маленьких rows, повторные reads, UTF-8
   кириллица/emoji, сжимаемый TOAST, глубина32/33, node cap, NULL, пустые массивы.
   Для bytes границы учитывать тот же SQL serializer, не Python len текста.
   Не ограничиваться monkeypatch малых caps: нужен реальный выбранный envelope.
4. **Обычный GREEN.** Полный getter и общие source/binding без trim: обычная
   новая загрузка старого разговора; browser/default/выбранный summary;
   explicit старый source_result той же revision; pinned outcome другого
   result; desktop summary-only selection; отсутствие аудио/прав экспорта.
   Естественная30–60-минутная синтетическая встреча должна проходить с разумным
   запасом. Отсутствие participant/archive/calendar не становится обязательным
   условием этого GREEN. Сохранены exact digest и правила empty/whitespace.
5. **Точная PG гонка размера.** В независимых соединениях остановить A после
   числового preflight Q до исходного Q. B реально UPDATE/INSERT и COMMIT
   transcript/outcome/unused scalar JSON. A либо читает тот же bounded snapshot,
   либо закрывается известным конфликтом; новая большая строка не попадает в
   Python. Подставной sleep/mock isolation не является этим доказательством.
6. **Вложенные PG гонки.** Тот же barrier для candidate ID/link replacement,
   snapshot/source/calendar/participant update и insertion, legacy roster,
   previous recurring insertion с более новым start, grant/invitation/grantee
   update. В одном случае B не затрагивает текущий Meeting: это RED против
   ошибочного допущения о достаточности его fence. A подтверждает старый
   bounded read set, никакого дополнительного глобального lock writers нет.
7. **Snapshot creation/order.** Реально SHOW transaction_isolation в fixture;
   guard проходит setup с RR до первого tenant/readiness SQL. Сессия с уже
   начатой транзакцией отвергается. Test, где B меняет строку между первым
   snapshot и locking numeric preflight, даёт40001/unavailable без retry.
   Не выводить production isolation из отсутствия engine option.
8. **Lock semantics.** Числовой FOR UPDATE внутри Q действительно удерживает
   исходную row-блокировку до owner exit, включая outer aggregate/limit.
   Writer при analytics-first ждёт в точном общем порядке; mutation-first
   обнаруживается. SKIP LOCKED/volatile/unrecognized SELECT отвергаются до
   повторного исполнения. Advisory-lock control SQL не вызывается дважды.
9. **Свежесть T113 отдельно.** Действующие revoke/account-close/session/
   membership/device/source/result/outcome/deletion writers проверяются
   настоящими SQL-мутациями mutation-first/analytics-first; дополнительно
   insertion отзыва между snapshot и identity/gate lock. Неизменная parent
   row не скрывает новый запрет. Если этого нет, оставить настоящий verifier
   закрытым; scoped numeric GREEN не выдавать за admission GREEN.
10. **Deadline/atomicity.** На максимальном допустимом envelope измерить полные
    SQL+materialization+canonical speaker/model+JSON/digest и остаток до
    INSERT/commit. Отдельно общий cap SELECT, aggregate timeout, удержанный
    lock и cancellation нового guard. Прежние2s/250ms/500ms,0 retry, отсутствие
    surviving task/session и одного частичного нового события сохраняются.
    Idle Pool.close/294 без новых относящихся изменений повторять не нужно.
11. **GET/renewal/admission.** Guarded fresh совпал со старым ограниченным
    render → proof; старый огромный/сменившийся render → обычный HTML без
    proof. Matching expired →renewed и0 INSERT/provider; changed/invalid →
    unavailable. Одна допустимая пара через прежний SQL primitive и один
    commit; ошибка второго INSERT/последнего guard/unknown commit не даёт
    ложного accepted или автоматического повтора. Подставляется закрытая
    внутренняя context boundary, а не HMAC/source verifier=True.
12. **Privacy/output.** Inspect синтетических ledger/log/fake transport:
    нет text/JSON/ciphertext/proof/body/частных refs в новых журналах или
    аналитическом payload. Guard выдаёт только разрешённый generic отказ;
    bytes/query counts не становятся новым внешним событием или reason echo.

Не требуется запускать все прежние suite ради этого документа. После кода —
назначенные причинные проверки, независимое implementation review/converge
на точном срезе и существующие release gates; они остаются отдельными шагами.

## H1 — точный SELECT повторён, но допустим другой ограниченный row

**P2 / design blocker.** В описанном варианте preflight сначала исполняет
Q внутри aggregate, затем исходный Q. Это два самостоятельных исполнения.
REPEATABLE READ задаёт одинаковый видимый набор committed rows, но не одинаковый
порядок строк без полного ORDER BY. LIMIT1 без порядка или с равными sort keys
может выбрать другую строку. Иной план aggregate против исходного reader
достаточен; конкурентный writer для этой причины вообще не обязателен.

Конкретный достижимый пример: `egress.py:2651` выбирает50 полных
MeetingEgressAuditEvent с ORDER BY created_at DESC без id. В модели
`db/models/meeting_access.py:224` created_at не уникален, а metadata_json —
неограниченный JSON. При51 событиях одного времени маленький и большой JSON
могут оказаться по разные стороны LIMIT50. Без всякого writer одна проверка
только выбранных50 не доказывает размер иных допустимых50. Текущий
calendar audit, напротив, добавляет id DESC и этим свойством не обладает.

Дополнительно проверены mapped constraints: текущий calendar link уникален
по workspace/meeting; artifact policy тоже; slot уникален по типу и имеет
partial unique default; MediaRevision revision_number уникален в workspace/
meeting. Их нельзя называть доказанными примерами неоднозначности. В workflow
attempt_ordinal/created_at не являются общей unique pair; у dependency есть
unique по revision/dependency, но не meeting/updated_at. Нужна полная сверка
ограничений и всех вложенных selectors; один известный уникальный root её
не заменяет. Модельные ограничения здесь — source evidence, не runtime inspection.
Поэтому текущая схема ещё не получает SCOPED DESIGN PASS.

Обязательный RED H1: изолированный допускающий это schema/selector с двумя
строками одинаковых WHERE/sort keys, маленькой и превышающей bytes cap;
заставить preflight и actual query выбрать разные существующие rows при одном
RR snapshot. Не ограничиваться mock возвращённого ORM объекта. Неполный
ORDER BY журнала и вложенный LATERAL должны быть отдельными случаями.
Если schema не допускает две строки,
привести действующий unique constraint, его predicate и конкретный selector;
не имитировать невозможное нарушение ограничения в production schema.

**Полный безопасный способ исправления без изменения common reader:**
числовой guard обязан проверять супермножество всех потенциально выбранных
rows/полей, а не один произвольно выбранный LIMIT row. Для этого допустима
явная консервативная DB-карта зависимостей вместо повторения 31 latest selectors:

1. После numeric byte/shape preflight текущего Meeting и всех подходящих
   current calendar links той же bounded RR транзакцией получить ограниченные
   scalar ID/candidate JSON inputs. Даже discovery JSON сначала проверяется
   на bytes/depth/nodes на сервере; это не загрузка неограниченного JSON для
   последующего выяснения размера. Он учитывается в общей стоимости.
2. Для каждого допустимого current link включить точную предыдущую встречу
   по существующему полному order start/link.id. Если текущие links могут
   быть неоднозначны, включить все варианты в ограниченное множество roots;
   превышение root cap закрывает аналитику. Календарные candidates разобрать
   ровно как common parser (UUID(str(raw)), первые10 уникальных допустимых
   IDs), по каждому допустимому link, с уже bounded исходным JSON.
3. По root meeting IDs агрегировать все потенциально загружаемые MediaRevision,
   ProcessingWorkflow/Result, slots/outcomes/items, speaker names, dependency,
   attempts, artifacts/policy/normalization/upload и оба журнала. Это намеренно
   включает историю и все варианты ties; LIMIT reader не используется как
   оправдание меньшего envelope. Transcript/diarization можно ограничить
   всеми result IDs root meetings, также консервативно. Не читать содержимое
   audit metadata, которое source path использует только в EXISTS.
4. Дочитать числовые envelopes templates всех outcome/default pointers;
   grants/invitations и identities всех реально достигаемых получателей;
   viewer membership/identity/external-email доступа предыдущей встречи;
   snapshots/source/calendar по всем candidate IDs, включая foreign IDs,
   все их participants и legacy matched snapshot participants. Точное имя
   безопасного view не ограничивает полноту ORM row. Unknown relation закрывает
   аналитику. Ограничивать это всем workspace или всей базой не требуется.
5. Учитывать стоимость повторного чтения строки, а не только unique rows.
   Допустим фиксированный консервативный коэффициент по каждой доказанной
   группе плюс session-scoped count всех фактических SELECT: например,
   transcript/diarization/outcome-items читаются один раз этим getter;
   metadata при hard query-count cap128 можно зарезервировать до128 раз.
   Более точные меньшие коэффициенты требуют отдельного полного source proof.
   При переполнении row/byte/shape cost proof отсутствует. Если такое
   консервативное правило отсекает обычную встречу, его нельзя просто ослабить:
   уточнить покрытие или вернуться к корректному guard фактических выборок.
6. В неизменном RR snapshot это закрытое супермножество покрывает любую
   выбранную reader строку, включая недетерминированный tie. Затем остаются
   тот же Meeting/source fences и полный общий getter без trim/обхода ветвей.
   Дополнительные DB aggregates подчинены500ms и одному2s сроку; огромная
   историческая встреча может честно остаться без измерения при доступном
   полном продуктовом просмотре.

Этот способ конкретен и сохраняет все требуемые ветви, но до его исполнения
нужны явный набор roots/числовых selectors/коэффициентов и независимая сверка
на фактическом source. Настоящий отчёт не подменяет эту сверку выдуманным
полным proof 31 selectors. Второй допустимый путь — проверка и материализация
строго одного server-materialized Q с числовым отказом до передачи private
rows Python; он требует отдельного проекта сохранения ORM mapping, порядка,
NULL/empty и cumulative envelope и здесь не объявляется готовым решением.

Не исправлять H1 добавлением ORDER BY только в preflight, новым альтернативным
latest reader, строковыми проверками после ORM load, поздним isolation,
SKIP LOCKED, глобальным lock без writers или обрезанием результата. HTTP/T113
остаются закрытыми. Для продолжения пользователю действий не требуется:
это технический выбор числового покрытия, не новое продуктовое разрешение.

## Отсутствие побочных действий

Создан только этот отчёт. Main map, код, tests, spec/plan/tasks/checklists,
управление Git/GitHub, runtime/данные, почта, страницы/контент/вёрстка, DNS/nginx,
Compose, сбор/T0 и публичные сообщения не менялись. Новых агентов не запускал.
Рабочая почта ГРАФ — Postal; чужой Stalwart отчёт не условие этого проекта.
Нет утверждения о полученном трафике, продажах или принятой production аналитике.

## Точные контрольные суммы

18 неизменных входов, сверены16.11.2026; все SAME относительно принятого
перечня того же диалога.

| Путь | SHA-256 |
| --- | --- |
| `specs/273-paid-traffic-analytics/spec.md` | `a7f23904625df9b06aed1e09c05f2ffa75ec3e5ec9ac0eda0531cd88c949c645` |
| `specs/273-paid-traffic-analytics/plan.md` | `5207a988f666c47f65203718a1212cf352312009f1c3804163abd093318a8b3c` |
| `specs/273-paid-traffic-analytics/tasks.md` | `3870e4d091557e0c40dd5500aa8fb5932b933cfe877e684c930d7f7e4f93a7d5` |
| `specs/273-paid-traffic-analytics/quickstart.md` | `4f2488aa98a3fba478eed042304279f408dc2530bd3f2b0449cedabaf39dd074` |
| `specs/273-paid-traffic-analytics/research.md` | `64caef3d9a78f0021c2b37ca86e0f388724bf117e899bd044f4ca557a1ba094f` |
| `specs/273-paid-traffic-analytics/data-model.md` | `478c18546d1240c4a1c15c5b07e76f7aeb551082273b75bc1fbf4cdd8d1ae8ab` |
| `specs/273-paid-traffic-analytics/contracts/activation-milestones.md` | `4835c0c6672a464366c9657d9285b28429ec2ed4d4e234c0c4897a65ed5027c4` |
| `specs/273-paid-traffic-analytics/contracts/result-visibility.md` | `ee1005b6a59ad1b42f0b7d0af25dd7099c8337a4d11930a3aba9ee6479d270d8` |
| `specs/273-paid-traffic-analytics/checklists/requirements.md` | `d771fe1f54e69b297346bfde3ea52f82d484fc241f13576efc34e09feffe80f4` |
| `specs/273-paid-traffic-analytics/checklists/security.md` | `dbd65a5afb7829789d8b4aa48f8c0b32243cc039681d15a5b851b381ca3b8b92` |
| `specs/273-paid-traffic-analytics/checklists/privacy-measurement.md` | `5b4164d0ce3e11ea6bca8419f4f0d6f6d33de163e3745cbb4cbfccd90ce07840` |
| `specs/273-paid-traffic-analytics/checklists/infra.md` | `a3319849bcd8be93803415495b42b4e50476cf1e08eb57ef898d34293f2be0cf` |
| `specs/273-paid-traffic-analytics/validation/t112-requirements-review-20261116.md` | `bb7c8592b302d6cb9ef21e0ecfc1045778afd39f07efed29787091ae3aaf91a5` |
| `specs/273-paid-traffic-analytics/validation/t112-analyze-20261116.md` | `0252da92dd9c3ff435a13bf55c0234afbb010abd9a3a1c49f8e42461427c18dc` |
| `.specify/memory/constitution.md` | `7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8` |
| `docs/prd-voice-layer-final.md` | `0f3ccfcfa60062bb0aae6802eeb0012056a635a30cb9f46f54d1992d0b4f57c2` |
| `docs/current-product-status.md` | `66ba7daa70519c8848a6daea51cd593220fccf75d4b5ea3a4a154e5ae139c3ca` |
| `docs/agent-guidance/product-gates.md` | `9f7072c879490d250053cb7397ad6b9b68fdcde17bdf9367ed874a41e450b5f5` |

Исходники и отчёты текущего независимого чтения:

| Путь | SHA-256 |
| --- | --- |
| `docs/agent-guidance/document-reading.md` | `5c3ab1f885dbf324edab70c0f4b7a5451208b3d7307c1ca7a5afdd7af0c8eb22` |
| `specs/273-paid-traffic-analytics/validation/t112-projection-budget-map-20261116.md` | `8f3e811d35f441ba29ec534956d94e6c04103471fad3905fc49f950df61cd7d6` |
| `specs/273-paid-traffic-analytics/validation/t112-http-preflight-20261116.md` | `9d25134784ec51a1eab528e609ed4f5d38df10af7e44870fbcdecaa29d8304d2` |
| `specs/273-paid-traffic-analytics/validation/t112-server-preflight-20261116.md` | `326782d610867430e26a7e97c71803bb1e44e2c57472790c16a8f158f5eabf59` |
| `specs/273-paid-traffic-analytics/validation/t112-view-selectors-review-20261116.md` | `d4d91ec375a2c9875d102ba8776edede1d00b89a38489d3b9fd40015567690bc` |
| `apps/server/src/twobrain_rec_server/cabinet/queries.py` | `cf0e7b622c60e53513df78140ddf2d2ab74937a55a15ce7c719de56fa14f50da` |
| `apps/server/src/twobrain_rec_server/cabinet/result_visibility.py` | `b59aa36240282748ed88696e1cfee04710302364ce9df9f2b5fc3315fdedb5e7` |
| `apps/server/src/twobrain_rec_server/cabinet/access.py` | `b4c055f84f8e8f51500e96468d20b01c72125aa19e910b43297a93b7677100bc` |
| `apps/server/src/twobrain_rec_server/cabinet/egress.py` | `4f31ab02b410938596a0fde2c4085ec31e0b4e6b1944db23607036f0fe380e40` |
| `apps/server/src/twobrain_rec_server/calendar/service.py` | `5c81afc11964c63314c1dcdafd381c594ed6f8081141117afb63ffd033c8fb84` |
| `apps/server/src/twobrain_rec_server/calendar/audit.py` | `cb5f8a219c147065c006e917ec8809f3f508e9b14a32fd2c25e2492f1ad61657` |
| `apps/server/src/twobrain_rec_server/outcomes/service.py` | `b10b0708564a809ec102f83d90f8030a3587dae28cbeae0781d9c5b1a3432377` |
| `apps/server/src/twobrain_rec_server/outcomes/progress.py` | `e84d89e8ee8e949a25339a1b8275daa6d5de174e892fa2f640209a8484977773` |
| `apps/server/src/twobrain_rec_server/processing/store.py` | `de616c64a03c3a036ab09d532d84bdb9443089a6c8f85f53a332af0295ba4b42` |
| `apps/server/src/twobrain_rec_server/processing/fences.py` | `1b4b8398d49212f5703a29e18460130d13d2c2bb39bcbc0b1d968804c63c4834` |
| `apps/server/src/twobrain_rec_server/processing/results.py` | `9a5044639b3902a4c4cd577dfc73a1d4b0a282f960b76a24f20ec39e41c8b009` |
| `apps/server/src/twobrain_rec_server/ingest/media_revisions.py` | `72e5e4a0d4ab6631762c84799b626f594dec7b8f3264b5b9f6f909c19f9e0391` |
| `apps/server/src/twobrain_rec_server/cabinet/speakers.py` | `e2978b9f04e6af5fe6c35cd98b4ee9960df69d28a7722265241311a8eb62f763` |
| `apps/server/src/twobrain_rec_server/cabinet/web_routes/notifications.py` | `b67fb88191839aba9ad6ac25aa6fd8f3ca3d34fae9c68f1f906cdf4778983505` |


Дополнительно прочитанные mapped constraints:

| Путь | SHA-256 |
| --- | --- |
| `apps/server/src/twobrain_rec_server/db/models/processing.py` | `fceefdfc9f1f0c8669a0bdedc744bf24877ef412af8f118f255d6bb0bec7296b` |
| `apps/server/src/twobrain_rec_server/db/models/ingest.py` | `46c814be586c78a69fa31f7bef1e6756dbec2a070f5c1bd9df5ce0714298809c` |
| `apps/server/src/twobrain_rec_server/db/models/calendar.py` | `0a2d82743331cfdade53fc4f781a5ed1cb31aaeee176d74463e01d278e1a419a` |
| `apps/server/src/twobrain_rec_server/db/models/outcomes.py` | `456b0c1cae8d6da7b6a4efe3cb90fe3c0e867ca93e83b15df61d8d6b008fbbaf` |
| `apps/server/src/twobrain_rec_server/db/models/meeting_access.py` | `37bc890cbafbe8f4b35f479ad42444790aa164707f69e3aa329794e3edfb3cad` |

Дополнительный статический указатель (не runtime proof):
`/private/tmp/graf-t112-projection-static-read-inventory-20261116.json`,
SHA-256 `ddf57567065f11c3a6946c29af14bea17566d1237ccaacc032093a0bfc5c1d4b`.

Самостоятельно прочитано появившееся уточнение основного исполнителя
`t112-projection-read-stability-20261116.md`, SHA-256
`aafc600100bdae59d73fd27dab20a5ead5557a3f22bbf02da20d37de0ff2feea`.
Его предупреждение о bounded Meeting подтверждено оригиналом; уточнение
сохранено без изменений и не снимает H1 неполного ORDER BY.

Дополнительно: `apps/server/src/twobrain_rec_server/db/models/meeting.py`,
SHA-256 `df51678d89abf694afe05e4fe5ade2ecb7e76ebe91e08d560ad08641967033c7`.
