# T077: внутреннее наблюдение биллинга

01.11.2026. Требования к первому шагу, не приёмка реализации.
Исходная FR-089/T077/#4932 целиком сохраняется. Владелец — repository-audit.
Связанные границы: [operations](operations-reconciliation.md),
[импорт B1–B3](registry-operator-import.md),
[security](security-privacy-compliance.md). Никакой новой службы/зависимости.

## O1. Вход и полномочия

Одна внутренняя команда `python -m twobrain_rec_server.cli.billing_monitoring
--date YYYY-MM-DD` в существующем серверном окружении. День реестра выбран
явно в Europe/Moscow, магазин/окружение — серверные Settings. Это чтение,
поэтому флага execute и записи результата в продуктовую БД нет.
До первого чтения предметных таблиц — `require_billing_maintenance_database`:
реальные session_user/current_user `twobrain_rec_maintenance`, RLS on,
без superuser/BYPASSRLS, контекст billing_reconciliation/billing.
Подмена URL/SET ROLE/имени оператора не даёт доступа.
Корпоративный Admin, личный Owner, Member, app/worker не получают этот вход.
`admin/metrics.py`, `readiness/checks.py` и F254 не меняются.

## O2. Снимок, время и пределы

Одна PostgreSQL READ ONLY REPEATABLE READ транзакция; режим задаётся
на connection до первого SELECT, включая tenant after_begin hook/guard.
В начале фиксируется один timezone-aware `as_of` UTC для всех возрастов,
expiry/capacity; отдельно — `finished_at`. Это снимок транзакции, не гарантия
последнего импорта после ожидания shared advisory lock registry_status.
Импорт, завершившийся во время ожидания, может остаться вне снимка;
новый запуск получает новый снимок. Не добавлять ради свежести новый lock.

Общий предел 15 секунд включает подключение, guard, hooks, запросы и lock;
statement_timeout 5 секунд, lock_timeout 2 секунды внутри транзакции.
После timeout/cancel/error выполняется rollback/закрытие connection.
Предметные запросы агрегируют данные в БД, без загрузки всех операций.
Перед registry_status проверить число detected gaps того же scope:
более 500 — `report_limit_exceeded`, без загрузки и усечения истории.
Результат stdout не более 64 KiB UTF-8. Превышение — отказ целого отчёта,
без частичного зелёного результата. Числовые пределы — границы диагностики,
не коммерческие ограничения или новые параметры запуска биллинга.

## O3. Форма и смысл

JSON schema_version=1; `coverage=partial` даже при успешном чтении первого
шага, `as_of`, `finished_at`, выбранный report_date и список семейств ниже.
Каждое семейство имеет source, scope, kind (`current_state` либо
`event_window`), coverage (`complete_declared_source|partial|unavailable`),
reason_code и values. Нет общего `healthy/ready/financial_pass`.
Exit 0 означает только завершённое чтение объявленных источников;
exit 1 — runtime/identity/timeout/schema/limit error, exit 2 — неверный ввод
или отсутствующий/некорректный серверный shop scope. При отказе — только
schema_version/result_code, без сырых исключений, SQL и connection URL.

Ноль — успешное полное чтение **объявленного** источника. Нет источника —
values=null/reason_code=not_connected либо uninstrumented; пустой набор
имеет count=0 и oldest_age_seconds=null с reason empty. Будущее время
не превращается в нулевой возраст: возраст null, invalid_time_count>0 и
coverage=partial. Возраст старейшего — max(as_of−timestamp), не сумма.
Новые неизвестные состояния группируются только в `unrecognized`,
дают неполноту и никогда не выводятся исходной строкой.

`database_inventory` — все строки, доступные защищённому maintenance
снимку БД, включая исторические/непривязанные; это не текущий магазин.
`proven_current_shop` допустим только при доказанной immutable привязке
shop/environment и согласованной workspace/invoice/operation связи.
В первом шаге только registry использует серверную shop-область.
Refund имеет environment без shop_id, webhook не имеет отдельных
shop/environment колонок. Текущие Settings не восстанавливают старую связь;
неподключённое разделение unbound/conflict явно остаётся неподтверждённым.

## O4. Объявленные источники первого шага

| Семейство | Подключение первого шага | Предел утверждения |
| --- | --- | --- |
| payment_state | BillingOperation/BillingInvoice; database_inventory/current_state, count по закрытым группам | Это состояния строк, не успехи/отказы за сутки. Bank cancellation reasons=null/uninstrumented; local cancel_reason не банковский отказ. |
| operation_uncertainty | Те же операции; count и oldest operation age по состояниям | unknown/manual_resolution/reconciliation_gap — три отдельные группы, не весь unresolved. Отдельно scheduled/provider_pending/sent/processing/pending_reconciliation/method_required/observation_expired/provider_key_expired; unknown_since отсутствует, длительность неизвестности=null. |
| webhook_queue | BillingWebhookEvent; database_inventory/current_state, count по состоянию и oldest received_at общей очереди accepted/pending_reconciliation | Это возраст очереди, не задержка транспорта. reconciliation_gap считается отдельно для реакции. occurred_at=object.created_at с fallback1970 не время отправки; transport lag/errors/dedup counters=null/uninstrumented. |
| ingress_and_duplicates | values=null, uninstrumented | Число уникальных строк не число предотвращённых повторов; 401/409/503 не накопленный счётчик. |
| free_projection | В принятом первом шаге values=null, not_connected; следующий срез определён O9 | Только видимые audit-события renewal.cutoff_projected_free, не все Free paths и не своевременность. |
| storage | values=null, not_connected | Последующее подключение требует effective_paid_storage и действующих _active_reserved_bytes с общим as_of, явных аргументов project_active_playback_storage; без default zero. Expired-active отдельно, workspace без subscription не пропускается, capacity без источника unavailable. WAV/object total не customer quota; repair/purge не вызываются. |
| addon_and_time_credit | values=null, not_connected | Следующий источник — сохраняемые operation/grant/credit state/expiry, не число maintenance-действий и не heartbeat. |
| refunds_and_receipts | values=null, not_connected | Только authoritative observed outcome с доказанной областью; observed_at не дата возврата, отсутствие observation не успех чека или банковский срок. |
| registry | registry_status выбранного дня/магазина, proven_current_shop/current_state | Только последний attempt/accepted, files_complete, financial_status=not_checked и detected gaps. Отсутствие отчёта — unverified. История resolution не читается и не принимается. |
| notifications | BillingNotificationDelivery (billing_notification_deliveries); database_inventory/current_state, count по state, сумма сохранённых attempts и oldest created_at очереди pending/retry | failed имеет отдельные count/oldest age для реакции: postal_outcome_unknown сохраняется до POST и не доказывает отказ доставки. suppressed — подавленное необязательное письмо, не ожидающая обязательная очередь. created_at не последний отказ; attempts не число HTTP или принятых писем; delivered не приёмка всех producers T068 и реальной почты #7524. |
| deletion_and_fair_use | values=null, not_connected | Нужны отдельно проверенные lifecycle/deadline источники, не ноль нарушений. T070 и privacy-приёмка сохраняются. |

Закрытые группы сверены с сохраняющими путями исходников на
`c6f42e8c7dec50ba769216feab4a80b70b50959a`:

- operation kind: initial_checkout/renewal/storage_upgrade/early_renewal/
  storage_schedule/resume_renewal. Последние два — служебные операции без
  списания и счёта; succeeded не означает успешную оплату. Считать kind и
  state совместно, без сводного показателя «успешные оплаты» из операций.
- operation state с текущими writers: scheduled/provider_pending/sent/
  processing/unknown/reconciliation_gap/manual_resolution/observation_expired/
  provider_key_expired/succeeded/succeeded_projected/succeeded_refused/canceled.
  provider_key_expired сохраняется для старой схемы покупки; наличие
  succeeded_refused не разрешает вернуть отменённый отказ F278 FR-041.
  pending_reconciliation/method_required/failed — отдельные распознаваемые
  группы совместимости чтения, без подтверждённого текущего writer и без
  утверждения о наличии таких строк в рабочей БД. Их count>0 требует
  coverage=partial/reason_code=read_compatibility_state; нулевые группы
  не доказывают отсутствие исторического пути.
- invoice status: pending/unknown/succeeded/canceled/manual_resolution;
  failed — та же группа совместимости чтения с отдельной неполнотой.
  paid не подменяет succeeded.
- webhook state: accepted/pending_reconciliation/reconciled/reconciliation_gap.
  processed/failed — счётчики обработки, не сохраняемые состояния inbox.
- delivery state: pending/retry/failed/delivered/suppressed. BillingNotification
  задаёт виды сообщений, а не таблицу; sending — переменная, не state.

Иные реальные значения дают только unrecognized с неполнотой, без исходной
строки. Названные группы — статический контракт источников, не live inventory
и не доказательство всех динамических writers. Отдельные возраста по state,
общая очередь и failed не складываются в возраст или число уникальных оплат.

## O5. Приватность

Выход содержит только имена закрытых групп, количества, секунды, даты и
ограниченные metadata реестра. Не включать shop_id, provider/payment/refund/
invoice/operation/workspace/user/device/meeting IDs, суммы, method mask,
контакты, исходные пути, payload/snapshot/JSON, raw причины и секреты.
Результат registry_status не печатать целиком: спроецировать counts,
files_complete, дату последнего принятия и исходные detected/deadline;
owner выводить только как owner_unverified: CLI проверяет формат и сохраняет
переданную строку, но не подтверждает назначение/полномочия владельца.
Даже billing-operations не является проверенным назначением; исходная
запись сохраняется без потери/изменения. Новая система ролей не требуется.
Причины и severity — закрытые коды; неизвестное неполно и безопасно.
Финансовый оператор уточняет исходного owner штатным registry status,
который сохраняет собственную maintenance-границу. Нет HTTP/почты/analytics,
provider GET/POST, доступа к объектам встреч или финансовых записей результата.

## O6. Реакция и полный остаток

Первый отчёт не ставит resolved/accepted_risk и не сохраняет incident.
Registry detected owner/deadline неизменны при повторе; отсутствие detected
gap не доказывает проверку разрешений. Для неподключённых семейств ответственный
за подключение — repository-audit, до приёмки T077; это **не перенос** сроков
уже существующих финансовых/приватностных нарушений.

Полный FR-089 остаётся в T077: подключить все семейства, постоянные показатели
попыток/ошибок/повторов, регулярный запуск и heartbeat наблюдения, внутреннюю
доставку тревог/повтор, сохраняемую реакцию detected→contained→owner_assigned→
notified→investigating→resolved|accepted_risk с severity/owner/evidence/сроком
и доказанным закрытием. Сначала проверить существующие эксплуатационные
механизмы; не строить универсальную систему и не использовать tenant
SupportIncident с фиктивными workspace/user/device или transactional outbox
для общего магазина. Канал/период/пороги закрепить до подключения тревог.

Исходные сроки сохраняются: transient 15 минут/24 часа, fair-use review≤24 ч,
receipt canceled — немедленно, pending — эскалация через3дня, registry gap
и F278 FR-041 — реакция≤24 ч. Неизвестный/неизмеренный исход не безопасный.
F272/F199 emergency stop и runtime-launch-gates не возвращаются. Оплаченный
срок после отзыва сохраняется по F278 FR-041. Изменение checkout/выпуск/
финансовая или обязательная ручная приёмка не входят в первый отчёт.

## O7. Содержательная приёмка первого шага

Настоящий CLI→guard→отдельная PostgreSQL с forced RLS→JSON; успешный ноль
против unavailable; app/worker/superuser/SET ROLE/неверный контекст denied;
повтор из нового процесса не пишет. Один снимок при конкурентном изменении
и ожидании registry lock, новый запуск видит новое; единый as_of на временной
границе. Future timestamps/unrecognized/неполная схема безопасны.
Timeout подключения/lock/query и пределы дают ненулевой исход без traceback
и частичного отчёта. Сравнить данные до/после; provider POST/GET/почта=0.
В синтетическом входе разместить запрещённые поля и проверить отсутствие
их значений в stdout/stderr. Schema mismatch не выдавать за пустой результат.

## O8. Порядок и критерий завершения

До кода: полное чтение обязательных документов, закреплённые source/task/
ownership, уточнение spec/plan/tasks/quickstart, reviewer-owned checklist
и независимый PASS всех применимых пунктов, scoped analyze без CRITICAL/HIGH,
существующая #4932 без дубля. После: профильная проверка, independent code
review/converge, обязательные governance-fast/macos-pr/pr-metadata exact SHA
и основы. До выполнения всего O6 и исходной FR-089 T077 остаётся `[ ]`,
issue OPEN; PR первого шага только Refs #4932. Выпуск не имитировать новым Full.

## O9. Следующий срез: события free_projection

Требования к доработке исходной T077/#4932 после PR7884; не приёмка кода.
O1–O8 сохраняются, кроме явно уточнённой ниже семантики времени этого
нового семейства. Другие семейства и их возрастные правила не меняются.

- **P1 — источник и смысл.** source=billing_audit_events,
  scope=database_inventory, kind=event_window; точный action
  renewal.cutoff_projected_free. count — число видимых audit-строк,
  не уникальных workspace/платежей и не всех переходов на Free.
  created_at не cutoff/commit/фактическое время проекции. blocked не означает
  отсутствие проекции, renewal_not_confirmed не доказывает банковский отказ.
- **P2 — окно.** report_date — календарный день Europe/Moscow. Обе локальные
  полуночи отдельно переводятся в UTC: start включён, end исключён.
  Наблюдаемый интервал [start,min(end,as_of)); точный as_of исключён.
  Семейство содержит window с timezone, start, end, observed_until и
  calendar_day_elapsed=(end<=as_of). Этот признак календарный, не watermark:
  PostgreSQL now() может относиться к началу поздно закоммиченной транзакции;
  новый снимок вправе изменить итог прошлого дня.
- **P3 — группы.** Внутри наблюдаемого интервала известны ровно пары
  blocked/workspace_scope_invalid, projected/unknown_pending и
  projected/renewal_not_confirmed, только при target_kind=workspace_subscription.
  Группы содержат outcome/reason_code/count; отсутствующие группы не выводятся,
  count равен сумме групп. Неизвестная/невозможная пара, NULL reason или иной
  target_kind попадают в одну группу unrecognized/unrecognized. Исходные
  строки не выводятся; неполнота выражена coverage=partial/reason=unrecognized.
- **P4 — неполнота и приоритет.** values содержит count, groups,
  undated_count, undated_count_scope=database_inventory и
  at_or_after_as_of_count. undated_count считает все строки этого action
  с NULL created_at в доступном снимке БД, без приписывания выбранному дню.
  at_or_after_as_of_count считает строки этого action только в выбранном
  [start,end) с created_at>=as_of; это может быть нормальная конкурентная
  запись во время подключения, не доказательство ошибки часов. Эти строки
  не входят в count/groups. Для начавшегося представимого дня reason_code
  выбирается строго: unrecognized → undated_time → at_or_after_as_of →
  window_open → empty → observed. Первые четыре означают partial; empty
  и observed — complete_declared_source только объявленного audit-источника.
  undated_time требует undated_count>0, at_or_after_as_of — соответствующий
  count>0, window_open — start<=as_of<end. Все признаки и количества
  сохраняются независимо от единственного выбранного reason_code.
- **P5 — недоступное окно.** Для представимого дня с start>as_of:
  unavailable/window_not_started, values=null, observed_until=null,
  calendar_day_elapsed=false; не выдавать будущий день за ноль, запросы
  подсчёта этого семейства не выполнять. Если локальная полуночь, следующий
  день или её UTC-проекция не представимы stdlib datetime/date:
  unavailable/calendar_boundary_unrepresentable, values=null,
  start/end/observed_until/calendar_day_elapsed=null, timezone сохранён.
  Этот исход имеет приоритет перед window_not_started. Произвольного
  коммерческого ограничения дат нет; CLI-проверка YYYY-MM-DD сохраняется.
  Недоступность семейства не отменяет чтение других источников: успешный
  отчёт с общей coverage=partial имеет exit 0. Ошибка БД/схемы/предела
  сохраняет отказ всего отчёта по O2/O3, без частичного результата.
- **P6 — безопасность и допуск.** SQL агрегирует только объявленный action,
  выбирает закрытые группы и времена/счётчики. Не читать metadata_json,
  target_ref, workspace/actor/id; не менять источники, RLS, деньги или guard.
  Единый as_of и существующая READ ONLY RR/timeout/cleanup граница обязательны.
  До кода — предметный reviewer-owned checklist free-projection.md,
  независимый PASS и scoped analyze; после — реальные PostgreSQL/CLI
  сценарии quickstart, независимое review/converge и точные PR gates.
  Только Refs #4932; T077 остаётся [ ], весь O6/FR089 не закрывается.

## O10. Следующий срез: сохраняемый реестр бонусных дней

После PR7887 подключается только один источник внутри исходной T077/#4932.
O1–O9 сохраняются. Это требования к чтению, не приёмка заданий начисления.

- **C1 — источник и граница.** Семейство addon_and_time_credit получает
  source=time_credit_ledger_entries, scope=database_inventory,
  kind=current_state. Это все доступные строки реестра в том же снимке,
  независимо от report_date; не текущий магазин, не события за сутки,
  не число пользователей, начисленных дней или выполненных заданий.
  coverage всегда partial. В values поля addon_jobs, job_attempts,
  job_errors и job_retries остаются null: эти измерители не подключены.
- **C2 — закрытые состояния.** values.count — число строк; values.groups —
  отсортированные по state непустые группы state/count. Известны ровно
  pending/available/applied/expired/rejected/reversed; иное, включая NULL,
  попадает в одну unrecognized без исходной строки. count равен сумме групп.
  Состояние matured вспомогательного расчёта не объявляется состоянием БД.
  Отрицательные reversal-строки тоже считаются строками; days не читается
  и не суммируется, баланс/долг/число наград из count не выводятся.
- **C3 — временные признаки.** values.pending_or_available содержит count
  строк только pending/available и четыре непересекающихся количества:
  invalid_schedule_count (NULL maturity_at/expires_at или expires_at<=maturity_at),
  expiry_reached_count (валидные даты, expires_at<=as_of),
  maturity_reached_unexpired_count (валидные даты, maturity_at<=as_of<expires_at),
  waiting_count (валидные даты, as_of<maturity_at). Сумма четырёх равна этому
  count; недействительное расписание классифицируется первым. Будущие
  maturity/expiry допустимы и не являются ошибкой часов. Терминальные и
  неизвестные состояния в эту классификацию не входят. Поле
  oldest_maturity_reached_age_seconds — целая неотрицательная часть
  max(as_of−maturity_at) только maturity_reached_unexpired, либо null при
  отсутствии таких строк; возраста групп не складываются. Это возраст
  после сохранённой границы созревания, не длительность ошибки или SLA:
  security review и отсутствие оплаченной подписки могут законно удерживать
  credit. Ни один признак не доказывает готовность к применению или сбой.
- **C4 — ноль и неполнота.** reason_code выбирается строго:
  unrecognized → invalid_schedule → jobs_uninstrumented. Первый требует
  неизвестной группы, второй — invalid_schedule_count>0; иначе третий,
  даже при пустом источнике. После успешного чтения пустой реестр даёт
  count=0/groups=[], все четыре количества=0, возраст=null и прежние null
  измерители; не unavailable и не финансовый PASS. Ошибка доступа/БД/схемы
  сохраняет безопасный отказ всего отчёта O2/O3, без подстановки нулей.
- **C5 — безопасность и минимум.** Агрегировать в БД только state,
  maturity_at/expires_at, количества и минимальную допустимую maturity.
  Не выбирать days, source_ref, идентификаторы/связи, capacity_snapshot_bytes
  или applied interval; не вызывать начисление, expiry, reversal, repair,
  provider, почту или analytics. Не менять CLI/guard/RLS/снимок/cleanup,
  модель/миграции/полномочия, остальные семейства или финансовые writers.
  Один UTC as_of, ограничения O2, приватность O5 и отсутствие записи
  обязательны; новых служб/зависимостей/параметров нет.
- **C6 — допуск и доказательство.** До кода — собственный обязательный
  контекст, независимый reviewer-owned checklist credit-ledger.md и
  scoped analyze. Затем RED и реальные PostgreSQL/CLI/forced RLS сценарии
  quickstart: пустое/полное/неизвестное, точные границы/недействительный
  порядок дат/будущая maturity, отрицательная reversal, два снимка/новый
  процесс, no-write/privacy и безопасная ошибка схемы. Не ослаблять
  NOT NULL реальной миграции ради положительного сценария; SQL NULL-ветвь
  отдельно проверяется как защитная формулировка. После — независимые
  кодовое review/converge и три exact-SHA/base PR gates. Только Refs #4932;
  исходная T077 [ ], полный O6/FR089, сроки и внешняя приёмка сохраняются.

## O11. Следующий срез: сохранённые наблюдения возвратов

После PR7890 подключается один источник исходной T077/#4932. O1–O10
сохраняются; это чтение inventory, не выполнение возврата или финансовая сверка.

- **R1 — источник и смысл.** Семейство refunds_and_receipts получает
  source=observed_provider_refunds, scope=database_inventory, kind=current_state.
  Считаются все доступные строки того же защищённого снимка независимо от
  report_date, environment и observed_at. В таблице нет shop_id: текущие
  Settings не превращают inventory в текущий магазин. count не число
  уникальных платежей/заявок и не сумма возвратов; несколько частичных
  возвратов одного платежа могут давать несколько строк.
- **R2 — закрытые группы.** values.count — число строк; values.groups —
  непустые группы status/count, отсортированные по status. Распознаётся
  только совместная пара status=succeeded и source=provider_observation.
  Любая другая пара, включая NULL любого поля, даёт одну status=unrecognized
  без исходных строк; count равен сумме групп. Это сверка с объявленным
  сохраняющим путём, не доказательство всех динамических writers, актуальной
  достоверности провайдера или завершённой сверки. webhook/poll/registry —
  транспортные источники observation, не значения сохраняемого source.
- **R3 — ноль и неполнота.** coverage всегда partial. values.receipts и
  values.reconciliation_gaps остаются null: чеки и сравнение CSV/API/ledger
  не подключены. reason_code=unrecognized при неизвестной группе, иначе
  receipts_and_reconciliation_uninstrumented, в том числе при пустой таблице.
  Успешный пустой inventory имеет count=0/groups=[] и прежние null; ошибка
  доступа/БД/схемы сохраняет отказ целого отчёта O2/O3 без подстановки нулей.
- **R4 — время.** observed_at — локальное время наблюдения с default now()
  начала транзакции, не время возврата/банковского зачисления/последней
  проверки. Для этого inventory оно не читается, не фильтрует строки и не
  образует возраст или invalid_time_count; NULL, будущая дата и выбранный
  день не меняют количества. Отсутствие observation не доказывает отсутствие
  возврата, корректность чека или соблюдение срока. Receipt canceled требует
  немедленной реакции, pending — эскалации через3дня по исходному O6;
  этот срез их не измеряет и не переносит.
- **R5 — безопасность и минимум.** Одна SQL-агрегация только status/source
  и количества. Не выбирать IDs/связи, суммы/валюту, environment, observed_at,
  invoice.plan_snapshot/JSON, контакты или provider payload. Не вызывать
  record_observed_refund, reversal, provider GET/POST, почту или analytics.
  Не менять модель/миграции/полномочия, финансовых writers, CLI/guard/RLS,
  READ ONLY RR, cleanup, пределы O2 и остальные семейства. Новых служб,
  зависимостей и параметров нет; общий отчёт остаётся coverage=partial.
- **R6 — допуск и доказательство.** До кода — собственный обязательный
  контекст, reviewer-owned checklists/refund-inventory.md, независимый PASS,
  scoped analyze и существующая #4932. Затем RED, реальные PostgreSQL/CLI
  с FORCE RLS: пустое, известная/неизвестная совместная пара, несколько
  частичных строк, разные environments/дни/NULL и будущие observed_at,
  два снимка/новый процесс, no-write/privacy, безопасная ошибка схемы и
  прежняя граница ролей. NOT NULL реальной схемы сохраняется; защитная
  SQL NULL-ветвь проверяется отдельно без ослабления положительной БД.
  После — независимые review/converge и три exact-SHA/base PR gates.
  Только Refs #4932; все исходные task lines, T077 [ ], полный O6/FR089,
  сроки и внешняя финансовая/приватностная приёмка остаются открытыми.

## O12. Следующий срез: сроки сохраняемых fair-use проверок

После PR7892 подключается только fair-use источник исходной T077/#4932.
O1–O11 сохраняются. Это обзор строк, не новые ограничения или реакция.

- **F1 — источник и смысл.** Семейство deletion_and_fair_use получает
  source=fair_use_reviews, scope=database_inventory, kind=current_state.
  Считаются все видимые строки того же снимка независимо от report_date;
  это не текущий магазин, число людей/нарушений или завершённых рассмотрений.
  values.deletion и values.reaction остаются null; coverage всегда partial.
- **F2 — закрытые состояния.** values.count равен сумме непустых values.groups,
  отсортированных по state: notice/restricted/appealed/cleared/confirmed.
  Другой state, включая NULL, попадает в одну unrecognized без исходной строки.
  confirmed означает сохранённое подтверждение ограничения и может продолжать
  ограничивать capability; это не снятое ограничение. Наличие cleared/confirmed
  не доказывает сохраняемого решения с владельцем/evidence или закрытия incident.
- **F3 — сохранённое расписание.** values.pending_review содержит count только
  notice/restricted/appealed и четыре непересекающихся количества. Сначала
  invalid_schedule_count: NULL либо не конечные starts_at/review_by, review_by
  раньше starts_at либо больше чем через24 истекших часа. Затем для корректных
  дат not_started_count при starts_at>as_of; deadline_reached_count при
  starts_at<=as_of и review_by<=as_of; waiting_count при starts_at<=as_of<review_by.
  Сумма четырёх равна pending_review.count. Равенство начала уже началось,
  равенство срока уже достигнуто; review_by=starts_at допустимо. Будущая дата
  нормальна. cleared/confirmed/неизвестные состояния в эти количества не входят.
  24 часа — прошедшие86400секунд, независимо от session timezone/DST.
- **F4 — предел и неполнота.** Ни даты, ни возраст не выводятся. Достигнутый
  сохранённый срок — сигнал строки, не доказанный глобальный SLA breach,
  длительность сбоя, подтверждённая доставка письма или автоматическое решение.
  reason_code выбирается строго unrecognized → invalid_schedule →
  deletion_and_reaction_uninstrumented. Пустая таблица: count=0/groups=[],
  pending_review.count и четыре количества=0, оба прежних null; всегда partial.
  Ошибка доступа/БД/схемы даёт отказ целого отчёта O2/O3, без подстановки нулей.
  Срок review≤24ч и полная реакция O6 сохраняются независимо от этого счётчика.
- **F5 — безопасность и минимум.** Одна SQL-агрегация только state/starts_at/
  review_by и количеств; даты не загружаются в Python. Не выбирать ID/связи,
  capability/reason/evidence_ref/appeal_ref/decision metadata/контакты/JSON.
  Не вызывать persist/appeal/resolve/restrict, provider/почту/analytics/purge.
  Не менять модель/миграции/RLS/права, CLI/guard/READ ONLY RR/cleanup,
  пределы O2 и другие семейства. Новых служб/зависимостей/параметров нет.
- **F6 — допуск и доказательство.** До кода — собственный контекст, независимый
  reviewer-owned checklists/fair-use-inventory.md, PASS и scoped analyze,
  существующая #4932. Затем RED и реальные PostgreSQL/CLI/forced RLS:
  пустое/все5states, точные ±1мкс границы/будущее/нулевой срок/24ч,
  не конечные даты без ошибки арифметики, приоритеты, два снимка/новый процесс,
  no-write/privacy/ошибка схемы и прежняя граница ролей. Сохранить реальные
  NOT NULL/state/deadline CHECK: неверные значения должны отвергаться;
  защитные NULL/неизвестные/неверный порядок/срок>24ч ветви проверять отдельно
  на синтетическом SQL-входе без ослабления положительной схемы.
  После — независимые code review/converge и три exact-SHA/base PR gates.
  Только Refs #4932, T077 [ ], все87 исходных task lines, полный FR089/O6,
  58 старых gaps и внешние приёмки сохраняются; исторический пропуск до
  первоначального PR7884 кода не исправлен, весь O8 не объявляется PASS.

## O13. Следующий срез: сохраняемые наблюдения чеков

После PR7894 подключается map наблюдений чеков внутри той же T077/#4932.
O1–O12 сохраняются; для receipts/null и source/reason семейства O11 действуют
явные уточнения ниже. Это чтение inventory, не финансовая сверка или реакция.

- **Q1 — источник и форма.** refunds_and_receipts сохраняет count/groups
  наблюдаемых возвратов O11, но source становится составным:
  observed_provider_refunds,billing_invoices.plan_snapshot.receipt_observations.
  values.receipts вместо null получает самостоятельный source-объект:
  source=billing_invoices.plan_snapshot.receipt_observations,
  scope=database_inventory, kind=current_state, coverage всегда partial,
  reason_code и values ниже. Корневые scope/kind/partial сохраняются.
  Это все видимые invoice/map entries того же снимка независимо от report_date,
  invoice status, environment/shop и времён, не текущий магазин или число
  уникальных чеков/платежей. Корневой count не складывается с вложенным.
- **Q2 — контейнеры.** receipts.values содержит invoice_count (все invoice),
  missing_map_count (только object plan_snapshot с отсутствующим ключом
  receipt_observations либо JSON null), invalid_container_count (plan_snapshot
  не object, включая SQL/JSON null, либо его ненулевая map не object).
  Пустая object map допустима, даёт0entries и не missing. Invalid не missing;
  контейнеры считаются по invoice один раз. Они не дают фиктивную запись
  observation. Раскрывать в SQL только object map через защищённый CASE;
  malformed array/scalar не должны вызывать ошибку json_each или исчезать
  под видом успешного полного нуля. NOT NULL реальной схемы не ослаблять.
- **Q3 — закрытые группы.** receipts.values.count — число видимых JSON entries
  object map; groups — непустые группы parent_kind/status/source/count,
  лексикографически отсортированные в этом порядке. Известны только совместно
  parent_kind=payment|refund, status=pending|succeeded|canceled,
  source=webhook|poll|registry (18 сочетаний). Иной/отсутствующий/NULL/нестроковый
  компонент или не-object entry даёт одну тройку unrecognized/unrecognized/
  unrecognized; исходные строки не выводятся. Count равен сумме groups.
  Ключ map/идентичность/immutable связи не перепроверяются; SQL JSON может
  содержать повторяющиеся ключи, entries не объявляются уникальными чеками.
  Top-level receipt_registration — отдельная payment UI projection; её
  наличие без map не считается observation и не восстанавливается догадкой.
- **Q4 — время и неполнота.** registered_at/observed_at/created_at не читаются
  и не образуют возраст: ни одна не является доказанным pending_since.
  receipts.values.pending_age_seconds и escalation_due остаются null;
  values.reconciliation_gaps корневого семейства остаётся null. Succeeded
  означает сохранённый статус, не доставку письма/актуальную проверку API,
  финансовое разрешение или работу всех producers. Вложенная причина строго
  unrecognized → invalid_container → missing_observations →
  timing_and_reconciliation_uninstrumented. Первые три требуют соответственно
  unknown group/invalid count>0/missing count>0. Корневая причина имеет тот же
  приоритет с учётом unknown возвратов O11, последний код —
  reconciliation_uninstrumented. Пустая БД даёт нулевые counts/groups[]/null,
  оба source partial. Ошибка доступа/БД/схемы сохраняет отказ целого отчёта
  O2/O3. Canceled требует немедленной реакции, pending эскалации через3дня;
  этот срез сроков не измеряет и их не переносит, O6 остаётся открытым.
- **Q5 — безопасность и минимум.** Две SQL-агрегации invoice containers и
  закрытых map groups в существующем billing/monitoring.py; прежняя refund
  агрегация сохраняется. JSON читается только внутри SQL по разрешённому пути
  и полям parent_kind/status/source; в Python/вывод не выбирать целый JSON,
  map key, ID/связи/shop/environment/контакты/суммы/времена/receipt URL.
  Не вызывать record/merge receipt, provider/почту/analytics или writer.
  Не менять модель/миграции/права/RLS/CLI/guard/READ ONLY RR/as_of/cleanup,
  пределы15с/5с/2с/500gaps/64KiB или остальные семейства. Новых служб,
  зависимостей/параметров нет; группы ограничены19 закрытыми комбинациями.
- **Q6 — допуск и доказательство.** До кода собственный контекст, reviewer-owned
  checklists/receipt-inventory.md, независимый PASS, scoped analyze и та же
  #4932. Затем RED и реальные PostgreSQL/CLI/FORCE RLS: пустота, payment/refund
  и все18сочетаний, malformed root/map/entries/NULL/missing/{} и приоритеты,
  два снимка/новый процесс/разные дни, private sentinels/no-write/схема/роли.
  Сохранить NOT NULL; SQL NULL защиту проверять отдельно от положительной БД.
  После независимые review/converge и три exact-SHA/base PR gates. Только
  Refs #4932; T077[ ],87 исходных task lines,58 старых gaps/весьFR089/O6,
  исторический O8 пропуск и отдельные приёмки остаются открытыми.
