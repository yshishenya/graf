# T077: внутреннее наблюдение биллинга

01.11.2026. Требования к первому шагу, не приёмка реализации.
Исходная FR-089/T077/#4932 целиком сохраняется. Владелец — repository-audit.
Связанные границы: [operations](operations-reconciliation.md),
[импорт B1–B3](registry-operator-import.md),
[security](security-privacy-compliance.md). Никакой новой службы/зависимости.

Статус O16 от03.11.2026 — первый шаг J1–J4/агрегаты принят через PR7914;
текущий следующий шаг J5/J6 уточняется. Ответы владельца, включая явное
решение в этом чате для конкретного accepted_risk, приняты в spec.
Новый план и независимый допуск к реакции/тревогам ещё впереди. O1–O15 и
исходная T077 сохраняются; назначение канала не доказывает фактическую доставку.

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


## O14. Следующий срез: сохраняемые запросы удаления

Исходная T077/#4932 после PR7896; это ограниченный обзор, не выполнение T070.
Уточнение `$speckit-clarify`: источник/границы ниже выведены из действующих
FR077/078/089, O6 и конституции IV; новых ответов владельца не приписывают.

- **D1 — источник и граница.** Внутри deletion_and_fair_use подключить
  MeetingDeletionRequest/meeting_deletion_requests. Root source точно
  fair_use_reviews,meeting_deletion_requests; values.deletion — отдельный
  source meeting_deletion_requests. Оба database_inventory/current_state,
  без report_date/created_at/accepted_at/completed_at/failed_at фильтров.
  Все видимые запросы, включая исторические и не доказанные текущему shop;
  count — строки запросов, не уникальные встречи/люди и не число удалений.
- **D2 — закрытые группы.** Ровно requested (default модели/миграции),
  deleting, active_purge_complete, retryable_failed (текущие writers).
  Любое другое значение, включая NULL/complete/terminal_failed/none,
  относится к одной unrecognized без исходной строки. Groups sorted по state;
  count равен сумме групп. Перечисление DeletionState шире реальных writers
  запросов и не является основанием назвать все его значения завершением.
- **D3 — отсутствие ложной приёмки.** active_purge_complete — только
  сохранённое состояние запроса, не проверка объектов или полного удаления.
  Оно не доказывает backup/local/MediaScribe/post-egress исход и не означает
  удаления Generation Call/Langfuse/Temporal, сохраняемых по политике оператора.
  completed_at не заменяет эти доказательства и вообще не читается.
  В values.deletion.values оставить artifact_completion, deadline_status,
  job_attempts, job_errors, job_retries=null. Нет SLA/возраста/дат/доли успеха.
- **D4 — неполнота и приоритет.** Nested coverage всегда partial;
  reason unrecognized при такой группе, иначе artifact_and_deadline_uninstrumented.
  Root всегда partial: unrecognized любого источника → invalid_schedule
  fair-use → deletion_details_and_reaction_uninstrumented. Fair-use count/groups/
  pending_review сохраняются отдельно, с deletion count не складываются.
  reaction=null. Пустые запросы дают count0/groups[] и всё равно partial.
  Недоступная таблица/схема — безопасный отказ всего CLI, а не пустой успех.
- **D5 — безопасность и минимальность.** Один helper/одна SQL-агрегация
  state/count в прежнем billing/monitoring.py, вызываемая прежним fair-use
  collector. В Python не выбирать ID/связи/request_source/reason/failure_reason/
  confirmation_boundary/policy/metadata/времена и объекты встреч. Не вызывать
  deletion/retention/purge/repair writers или внешние зависимости; схема,
  права/политики RLS, guard/READ ONLY RR/as_of/пределы O2/cleanup не меняются.
- **D6 — проверяемый порядок.** До кода семь согласованных документов,
  независимый reviewer-owned checklists/deletion-inventory.md и scoped analyze;
  исходная #4932 без дубля. RED, реальные PostgreSQL/CLI/FORCE RLS/NOT NULL,
  четыре state/unknown/NULL defensive SQL, private sentinels/два снимка/
  новый процесс/no-write/схема/роли; минимальные затронутые fair-use регрессии.
  Затем independent code/converge и exact SHA/base gates. T077[ ],87полных
  task lines,58старых gaps, весь O6/исходные сроки и отдельная T070 сохраняются.
  Наших Full/CD/релиза/Dev/данных нет. Исторический O8 пропуск не исправлен.

## O15. Следующий срез: проекция storage

02.11.2026, исходная T077/#4932 после принятого PR7897. Это подключение
уже объявленного O4, не приёмка всего storage/reconciliation/O6.

**S1 — область и предел.** Семейство storage: source=
`workspaces,workspace_subscriptions,effective_paid_storage,storage_reservations,track_artifacts,upload_sessions`,
scope=database_inventory, kind=current_state. Все видимые Workspace, без
фильтра report_date/shop/environment и без inner join, теряющего workspace
без подписки. Отдельные reservation counts также охватывают все видимые
строки. Inventory workspaces ограничен 500: SELECT не более501 узких строк;
501-я означает ReportLimitError/прежний report_limit_exceeded, без частичного
JSON или продолжения со случайной выборкой. Никакой maintenance batch100.
Прежние 15с/5с/2с и500gaps/64KiB независимы; превышение любого предела
отказывает целому отчёту. Это диагностика, не новое условие работы продукта.

**S2 — байты.** Для каждой workspace с доказанной capacity переиспользовать
effective_paid_storage(subscription,now=as_of), затем _active_reserved_bytes
(workspace_id,now=as_of) и project_active_playback_storage с явно переданными
workspace_id/capacity_bytes/reserved_bytes. Default reserved=0 запрещён.
Единый as_of и READ ONLY RR по O2. Used — существующая сумма canonical
stored/playback/profile/точного suffix `/meeting-review.m4a`, с исключением
finalized UploadSession/archive_audio=False. Reserved — max(0,sum(declared−
committed)) только active и (expiry NULL либо >as_of), не число резервов.
Capacity следует ровно существующему helper: trial/free/paid cutoff, applied
bonus, действующие storage grants, base invoice и historical cache fallback.
Существующие helpers/финансовые writers/схема не меняются ради мониторинга.
Это проекция строк, не проверка фактических объектов/MinIO или оплаты.

**S3 — неизвестность и итоги.** values содержит workspace_count,
capacity_unavailable_workspace_count, unrecognized_plan_count,
invalid_capacity_time_count, used_bytes/reserved_bytes/capacity_bytes,
reservations по S4 и reconciliation_gaps=null. Только plan free/trial/personal
распознаются; любой иной/NULL считается unrecognized_plan_count и capacity
unavailable, без исходной строки. Узкий SQL-признак наличия подписки различает
отсутствие строки и NULL plan у существующей строки: отсутствие увеличивает
только capacity_unavailable_workspace_count, без unrecognized_plan_count;
NULL/unknown plan существующей подписки увеличивает оба счётчика. Подписка
отсутствует — unavailable, не Free; её причина capacity_unavailable, тогда
как NULL/unknown plan даёт unrecognized по S6.
Для trial релевантно trial_ends_at, для personal paid_through: NULL сохраняет
семантику helper (Free), nonfinite значение даёт invalid_capacity_time_count
и unavailable до передачи datetime в helper. Free эти даты не использует.
Неположительная capacity helper также unavailable; не подставлять default/1.
При хотя бы одной unavailable workspace, unrecognized reservation state или
invalid reservation values **все три** byte totals=null. Иначе — точные целые
суммы всех workspace projections без float; известный subtotal не выводится.
Полностью пустой inventory даёт workspace_count0 и три byte totals0; пустые
резервы count0/groups[]. Это всё равно partial.

**S4 — резервы.** reservations содержит count (строки, не jobs/objects),
groups [{state,count}] в сортировке state, expired_active_count и
invalid_value_count. Распознаются active/committed/released; любая другая
строка/NULL — единая unrecognized. Expired-active — stateactive с конечной
ненулевой expires_at<=as_of; expiry==as_of уже истекла, NULLexpiry действует.
Invalid — declared NULL/<=0, committed NULL/<0/>declared либо ненулевая
nonfinite expiry; строка считается один раз. Это отдельные признаки, могут
пересекаться с expired-active. SQL проверяет isfinite до передачи дат в
Python, raw expiry не выбирается. Clamp helper не скрывает malformed строки.
Не вызывать release_expired, repair, locks, flush, purge или финансовые paths.

**S5 — приватность и отказ.** В Python передаются только внутренний workspace
ref и нужные helper поля subscription: plan_code/paid_through/trial_ends_at/
capacity_bytes, плюс безопасные SQL-признаки наличия подписки и nonfinite дат. Целый ORM объект,
billing owner/method/контакты не нужны. Существующий effective_paid_storage
внутренне выбирает финансовый plan_snapshot: утверждение «JSON не выбирается»
к O15 неприменимо. Snapshot, invoice/grant/ledger refs, object keys, IDs,
денежные суммы/контакты/raw значения не выводятся/не логируются; допустимы
только закрытые коды, counts и целые байты. Семантика `plan_snapshot or {}` и
`catalog_snapshot or {}` существующего helper сохраняется: JSON null, [], 0,
false и пустая строка сами по себе не означают отказ. Неподдерживаемая форма —
та, которую helper действительно не может обработать, например truthy
nonobject без `.get`; отдельный более строгий JSON-валидатор не добавляется.
Исключение helper или schema failure — прежний безопасный отказ целого CLI
`report_unavailable`/exit1 (O3), без
traceback/SQL/сырых исключений и ложного нуля. Нового egress/сохранения нет.

**S6 — неполнота и приёмка.** coverage всегда partial; приоритет reason_code:
unrecognized (plan/reservation) → invalid_storage_values (резервы) →
capacity_unavailable → reconciliation_uninstrumented. Группы и все counts
сохраняются независимо от причины; reconciliation_gaps всегда null.
Used не MinIO inventory, capacity с historical fallback не финансовая сверка,
expired-active не доказательство своевременной очистки/jobs/heartbeat.
Настоящие PG/CLI/FORCE RLS/снимки/newprocess/no-write/privacy/предел501,
схема/malformed/helper failures и source semantics обязательны по quickstart.
До кода независимый reviewer-owned storage-projection/analyze; после —
независимые code/converge и exact PR gates. T077/T070/O6/58 прежних gaps,
все87 полных task lines и все исходные сроки сохраняются. Новых служб,
таблиц, зависимостей, прав, тревог, записи или выпуска этот срез не вводит.

## O16. Проект следующего среза: журнал попыток reconciliation

03.11.2026. Требования исходной T077/#4932 после PR7898, с принятыми
ответами владельца по J5/J6. Первый шаг J1–J4/агрегаты принят через PR7914.
Для следующего шага J5/J6 подготовлен план A1–A7 ниже; независимые
checklist/analyze ещё не приняты, код/установка/записи реакции не допущены. O1–O15
остаются действующими для принятого отчёта. Запись узкого источника не меняет
read-only поведение CLI. Общего принятия финансового или приватностного риска нет.

**J1 — потребность и единица.** Оператору нужны сохраняемые наблюдения
фактических попыток существующего billing reconciliation, чтобы перезапуск
не стирал сведения о подтверждённом отказе или неизвестном исходе. Источник
identity — настоящие Temporal namespace/workflow ID/execution run ID/activity ID/
attempt. Payload run_id обозначает интервал планирования и не заменяет
execution run ID: ALLOW_DUPLICATE допускает несколько исполнений того же ID.
Одинаковый полный ключ означает одну логическую наблюдаемую попытку; повторная
доставка не увеличивает этот count. Более поздний противоречащий исход должен
сохранять прежнее подтверждение и признак противоречия, а не переписывать его.
Никаких вымышленных workspace/user/device, generic incident/outbox или новой
службы/зависимости. Предметные operation/grant/credit/audit counts не attempts.

**J2 — исход и финансовая граница.** Различаются наблюдаемый старт,
подтверждённые success/failure/cancellation и противоречащие подтверждения.
Незавершённый старт означает неизвестный исход; возраст сам по себе не failure.
Запись начала и исхода требует отдельных коротких транзакций, независимых от
финансовых rollback/commit. Existing maintenance→COMMIT→webhook/initial checkout→
COMMIT и порядок освобождения locks сохраняются. Сбой записи до работы не
создаёт новый финансовый запрет; сбой после финансового commit не превращает
успешную работу в retry. Исходные результат, исключение и cancellation
финансовой activity сохраняются. Ошибка наблюдения даёт только закрытый
metadata-only сигнал неполноты, без SQL/URL/текста исключения. Авария между
финансовым commit и записью исхода остаётся unknown; повтор финансовой работы
ради восстановления журнала запрещён. Для будущего плана предложен общий
предел2с на каждую запись, включая setup/guard/cleanup, без фоновых хвостов.

**J3 — предел показателей.** Число попыток — уникальные успешно сохранённые
полные ключи; наблюдаемые повторы — только сохранённые ключи с attempt>1,
без восстановления отсутствующих предыдущих попыток по номеру. Отказ —
подтверждённое наблюдение исключения, не число SQL/provider ошибок и не число
денежных операций. Неизвестные, отменённые и противоречащие исходы различаются.
Пустой успешно прочитанный журнал подтверждает ноль его строк, а не отсутствие
исторических заданий. До начала инструмента, во время недоступности БД и при
потере записи полнота не доказана: coverage всегда partial. Этот workflow
совмещает несколько видов maintenance; отдельные add-on/time-credit jobs и
их failures из общего прохода не выводятся. Не заполнять прежние неподключённые
addon_jobs/job_errors/heartbeat псевдозначениями. Точная форма агрегированного
чтения требует последующего плана, без нового Temporal RPC в O1–O15 CLI.

**J4 — полномочия, данные и сохранность.** Предлагаемый источник глобальный
служебный, вне tenant RBAC: точные session_user=current_user=
twobrain_rec_maintenance, row_security=on, существующий allowlisted
billing_reconciliation/billing context, ENABLE/FORCE RLS. Request/worker/app,
SET ROLE и подмена URL не дают доступа; образец защиты0107 не разрешает
помещать job data в registry receipts/gaps. Только необходимые технические
связи, закрытые признаки исхода и время наблюдения; не сохранять task_token,
payload/snapshot, provider IDs, деньги, контакты, meeting data или raw failure.
Вне защищённого журнала допускаются только агрегаты и закрытые коды.
Исторические наблюдения не удаляются при повторе, изменении outcome или
meeting deletion. Автоматической очистки, сокращения retention Temporal/
Langfuse или нового срока хранения финансовых данных нет. Миграция, downgrade,
backup/restore и декларация нового источника в RLS inventory требуют отдельной
проверки в последующем плане до кода; существующие ворота не снимаются.

**J5 — принятые период, пороги и реакция.** Владелец принял порядок03.11.
Producer остаётся существующим пятиминутным scheduler; его цикл не подтверждает
фактический heartbeat. Проверка наблюдения каждые5мин; сохранённый
failure/противоречащий outcome — detected при следующей проверке; отсутствие
подтверждения наблюдения15мин — detected observability gap, без утверждения
о финансовом отказе. Незавершённая попытка после5мин остаётся unknown, а не
подтверждённой ошибкой. Эти технические пороги не заменяют transient15мин/24ч,
fair-use≤24ч, receipt canceled немедленно/pending3дня, registry/F278FR041≤24ч
или primary eligible purge≤24ч.
Успешная проверка источника, последнее событие reconciliation и живой
наблюдатель — разные свидетельства. Цикл в rec-maintenance вне Temporal
может пережить обычный отказ Temporal, но не доказывает контроль собственной
остановки. При общей недоступности БД нельзя обещать сохранённую попытку до
POST или своевременную доставку тем же процессом. После восстановления
прошлый gap сохраняет исходное время; он не становится уведомлением,
доставленным во время отказа. Для полного O6 нужны отдельно доказанные
независимый контроль наблюдателя и поведение при общей недоступности БД.
Работающий API, Docker restart и проверка при выпуске сами этого не доказывают.
Сохраняемая реакция следует O6: detected→contained→owner_assigned→notified→
investigating→resolved|accepted_risk, с severity, реальным owner, evidence class/
reference, сроком, containment, основанием разрешения и временем закрытия.
Канал — почта назначенного владельца GRAF. Адрес — только закрытая серверная
конфигурация, не данные tenant, требования или журналы. Неуспешную или
неподтверждённую отправку повторять не чаще раза в5мин; одинаковую принятую
почтовым сервером тревогу не отправлять повторно. Каждая попытка и failed/
unknown/accepted сохраняются раздельно. Принятие почтовым сервером не доказывает
получение/прочтение человеком; неизвестность не становится delivered. Повтор
после unknown не даёт exactly-once гарантии внешнего транспорта. Эти правила
не изменяют отправку чеков и существующих финансовых уведомлений.
Containment означает
явно отметить неполноту и восстановить наблюдение/зависимость; emergency stop,
runtime launch-gates и отказ в оплаченном сроке не возвращаются. Это требования
к будущей реакции, а не утверждение о существующей реализации или доставке.

**J6 — принятое назначение и оставшиеся ворота.** Владелец GRAF назначил
себя ответственным за инциденты биллинга и приватности, выбрал почту и принял
порядок J5 в ответах03.11 (§Session 2026-11-03 в spec). Принятие конкретного
риска подтверждается отдельным явным решением владельца в этом чате,
с сохранением ссылки на основание, связи с конкретной тревогой и времени.
Служебный исполнитель только переносит принятое решение в журнал;
произвольные --owner/--operator/actor_id или maintenance SQL не доказывают
личность и не создают accepted_risk. Письмо, молчание и общая политика
также не являются решением. Доверенная граница переноса и сохранения
основания должна быть определена в плане; вымышленная проверка автора
или автоматическое принятие риска запрещены. Ответов об owner/channel/
порядке/способе решения больше не требуется. Repository-audit отвечает за
подключение; это не новая роль, разрешение финансовых действий или tenant bypass.
Analytics/F273 Telegram, customer notification outbox/Postal и tenant
SupportIncident не становятся внутренним журналом автоматически; фиктивный
workspace запрещён. Переиспользование существующего почтового транспорта
требует исследования и плана с сохранением его финансовых ограничений.
До согласованного плана и независимого checklist/analyze не выполнять
миграцию, запись наблюдений/реакции или отправку тревог. Изолированные проверки
не заменяют фактическую приёмку доставки и не разрешают выпуск. Все87 task
lines/T077[ ]/T070[ ]/58 старых gaps, исходные сроки и полный FR-089/O6
сохраняются; новых issue/task нет.

### O16: первый шаг плана и граница полного O6

Первый шаг реализует только постоянные наблюдения J1–J4 и их агрегированное
чтение: `billing_reconciliation_observations` по [модели](../data-model.md)
и последовательности [плана](../plan.md). J5/J6 уже приняты как обязательные
условия дальнейших тревог/реакции этой же T077, а не исключены из работы.
До реализации первого шага — независимый checklist/analyze; фактическая
приёмка доставки нужна для работающих тревог и полного закрытия O6, а не
утверждается до появления почтового механизма. Первым шагом писем нет.

Новое семейство отчёта `reconciliation_attempts`: source=
billing_reconciliation_observations, database_inventory/current_state,
coverage=partial. attempt_count — уникальные полные ключи; groups outcome/count
только succeeded/failed/canceled/unknown/conflict, sorted и сумма=count.
observed_retry_attempt_count считает ключи с attempt>1;
missing_start_count — ключи с terminal, но без started. Нет выдуманных
предыдущих попыток/начала. Пустота0/[]/0/0, reason=history_incomplete;
при конфликте reason=conflicting_observations. Неизвестность не financial
failure, а failure activity не банковский отказ. Нет времени/возраста/SLA/
heartbeat или принятия всех maintenance jobs. No-write/DB-only O1–O15 CLI
сохраняются; новое сохранение производится только activity в отдельной
транзакции под прежним guard. Сбой схемы/доступа/лимита отказывает целому CLI.

Сохранять каждое различное закрытое подтверждение отдельной неизменяемой
строкой с DB UTC clock_timestamp; повтор того же события не меняет время.
2с на запись — выбранный предел плана, включая cleanup, не финансовый gate.
Нет payload/task_token/сырых ошибок и новых источников частного содержимого.
Непустой журнал защищён от UPDATE/DELETE/destructive downgrade; сроки
retention финансов/Temporal/Langfuse не меняются. Реальные права/RLS,
restart/rollback/restore/cancel/timeout/privacy проверяются до принятия кода.

### O16/J5/J6: контракт независимого наблюдения A1–A7

03.11.2026, продолжение после PR7914. Ниже нормативный дизайн, ещё не
проверенная реализация. Источник ограничен billing reconciliation0109;
остальные семьи и полный FR089/O6 этим не принимаются.

**A1 — чтение и три разных свидетельства.** Fixed source probe возвращает
schema_version=1, source_profile/generation, UTC as_of, coverage=partial,
event_count, failed_event_count, conflicting_attempt_count и nullable
last_event_at. Только целые неотрицательные counters≤9223372036854775807;
conflict — ключ попытки с несколькими terminal kinds, failed — сохранённый
event_kind=failed, не отказ банка. Никаких identity строк0109 или частных
полей наружу. Exact maintenance/FORCE RLS/READ ONLY RR до первого SQL/hooks;
15с весь DB probe, statement5с/lock2с, output≤16KiB, whole unavailable при
ошибке схемы/доступа/предела/непредставимом времени. O1–O15 CLI прежний.
Источник успешно прочитан, producer имеет последнее событие, observer
зафиксировал завершение цикла — независимые поля; source/status чтение само
не обновляет ни producer, ни durable observer tick. last_event_at — сигнал
свежести, не cursor для новых failure/conflict. Поздний commit старой даты
должен обнаруживаться приростом накопленных counters.

**A2 — расписание и incident basis.** Два systemd timer/oneshot на существующих
узлах, интервалы300с, без случайной дополнительной задержки, без параллельных
writer. Основной внешний observer читает source и tick встречного witness;
witness читает только durable tick основного observer. Оба живут вне
rec-maintenance/Temporal/PostgreSQL и публикуют собственный завершённый tick.
Невозможность прочитать source не мешает durable tick с outcome=unavailable.
Kinds: reconciliation_failure, reconciliation_conflict, source_gap,
producer_gap, observer_gap, witness_gap, source_discontinuity. Gap не financial
failure. На первой активации failed_event_count>0 создаёт историческую
reconciliation_failure, conflicting_attempt_count>0 — reconciliation_conflict,
обе unresolved. Один event_count>0 при двух нулевых предметных счётчиках
не создаёт этих тревог. Последний успех чтения/события/tick или
durable activation при их отсутствии — начало своего15мин интервала;
при возрасте≥900с gap detected, включая точное равенство. Будущее время,
clock rollback, уменьшение counters, новая source generation или нарушенная
схема создают discontinuity/unknown, не зелёное состояние или сброс истории.
Незавершённая activity после300с остаётся unknown. Её старт не доказывает
успешное завершение финансовой работы. Любой restore требует recovery hold
и сверки поколения; counts не обнаруживают все возможные восстановления.
Проверка —300с, это не обещание доставки за900с: следующий tick и бюджет
добавляют задержку. На здоровом расписании обнаружение порога≤300с после
его достижения; полный tick≤60с, remote source wrapper≤25с с cleanup,
SSH/status budgets входят в60с. При неисправном scheduler своевременность
не заявляется; witness фиксирует фактический gap.

Основание не равно всему source_sample. Для каждого kind канонический basis
содержит source_profile, проверенную source_generation, kind и только поля
следующей таблицы; очередные as_of/received_at/возраст в hash не входят.

| Kind | Стабильная предметная часть basis / новое основание |
| --- | --- |
| reconciliation_failure | Текущее failed_event_count; новое основание только при его строгом приросте в том же поколении. event_count, последний success и времена чтения его не меняют. |
| reconciliation_conflict | Текущее conflicting_attempt_count; новое основание только при его строгом приросте. Рост одного failed_event_count или event_count его не меняет. |
| source_gap | Последний сохранённый успешный source-check, либо activation при его отсутствии; при продолжающейся недоступности anchor неизменен. |
| producer_gap | Последний допустимый last_event_at, либо activation, если события не было. Изменение возраста/общего count без нового last_event_at не меняет anchor. |
| observer_gap / witness_gap | Последний допустимый durable peer tick и его head ref, либо activation при отсутствии tick. Status read не меняет anchor. |
| source_discontinuity | Сохранённый sequence первой записи текущего эпизода discontinuity и закрытый reason code; последующие invalid samples/времена не меняют этот эпизод. |

Gap anchor фиксируется, когда впервые достигнут порог900с. Успешное новое
свидетельство прекращает текущий эпизод gap, но не закрывает его incident.
Последующая потеря с новым anchor создаёт новое основание. Эпизод
discontinuity прекращается только явным recovery custodian с проверкой
lineage/времени; автоматическое улучшение sample его не завершает.
При нескольких причинах discontinuity первая запись выбирает один code
в порядке schema_invalid, source_generation_changed, counters_decreased,
source_time_invalid, local_clock_rollback; сырые неверные значения не сохранять.
До проверки lineage предметные counters не принимаются как новый baseline.
Сам отказ source не запрещает письмо о discontinuity из исправного внешнего
журнала; recovery hold после restore или отказа FS/часов запрещает POST по A3/A4.
После сверенного нового source_generation его
ненулевые failed/conflict counts снова требуют исторических тревог.
В каждом принятом поколении последние предметные counts сохраняются и после
закрытия incident: неизменный ненулевой count не создаёт его заново.

**A3 — durable журнал вне общей БД.** Каждый узел хранит свой узкий журнал
на защищённой локальной FS; основной авторитетен для source incidents,
witness — только для observer_gap. Нет concurrent writers/двух авторитетных
копий одного incident. Один lock≤2с объединяет tick/relay/backup; отсутствующий
после activation/повреждённый журнал не создаётся как пустой заново.
Create-once activation и append-only checksum/hash-chain records с fsync
файла, при создании также каталога; одна запись — одна атомарно принимаемая
версия перехода. Частичный tail, неверная цепочка, fsync/диск/лимит дают
recovery hold и запрещают POST; хвост не обрезается и история не удаляется.
Полные границы/схема — в модели. Отдельного изменяемого authoritative snapshot
или нескольких файлов, объявленных одной транзакцией, нет. До POST durable
record содержит incident/message identity, attempt=unknown и next_allowed_at.
При восстановлении незавершённая попытка остаётся unknown. Backup под lock
включает всю цепочку/consumed refs/accepted outcomes/activation/сроки; restore
проверяется отдельно, сохраняет старые времена и начинает с hold без рассылки.
Откат всех доступных копий и свидетелей не объявляется обнаружимым автоматически.

Уточнение A3 после проверки отказа fsync: перед каждой записью под тем же
lock создаётся фиксированный соседний `journal.jsonl.hold` через защищённый
O_EXCL/NOFOLLOW,0600,owner/nlink/identity checks. Он содержит только постоянный
признак формата, никогда не копию head/accepted/consumed/сроков. Сначала fsync
этого файла и каталога, затем append+fsync журнала, затем unlink только своего
проверенного файла запрета и fsync каталога. До завершения всей цепочки нет
POST или успешного ответа. Это запретительный предохранитель, не второй
источник состояния и не обещание общей атомарной транзакции двух файлов.
Уже существующий/неверный/недоступный запрет обычный запуск не присваивает
и не снимает; status не выдаёт такой хвост за подтверждённый tick. Activation
ставит запрет до создания журнала; restore не очищает его копированием.
Авария внутри записи требует явной сверки custodian и восстановления;
авария после снятого запрета вокруг POST оставляет unknown и прежний retry≥300с.
Storage-only recovery при целой проверенной цепочке может сохранить source
generation и все accepted/consumed/паузы; source discontinuity/restore требуют
сверенного нового поколения. Неполный хвост автоматически не исправляется.
Если fsync каталога после unlink отказал, журнал уже синхронизирован, но
видимый запрет может отсутствовать: вернуть ошибку и попытаться восстановить
его. Полный отказ FS/откат всех копий не позволяет гарантировать сохранение
нового признака. Все барьеры входят в60с; синхронный fsync не объявляется
прерываемым Python timeout, внешний ограниченный runner обязан ограничить процесс.

**A4 — письмо.** Только существующий Postal dataclass с минимальной закрытой
конфигурацией, без общего Settings, customer outbox или fake workspace.
Текст содержит закрытый kind, severity, технический incident reference,
detected/deadline UTC и безопасную evidence class; ни адрес, ни exception,
SQL/URL/деньги/Temporal identity/meeting data в журнал/вывод не входят.
Получатель — назначенный владелец, opaque binding version из закрытого
профиля, без email в данных incident. Deadline доставки одного POST≤10с
в общем60с budget; outcome только failed/unknown/accepted, accepted требует
сохранённого подтверждения транспорта. Acceptance ref хранить лишь digest.
Одинаковый message key с durable accepted не посылать повторно. Retry failed/
unknown≥300с по сохранённому next_allowed_at; rollback часов не ускоряет его.
При сомнении в clock/state POST запрещён до восстановления. Crash после
приёма до durable outcome — unknown, разрешённый повтор может дублировать
физическое письмо. Mailbox/read/exactly-once не обещаются. Не более одного
POST за tick на узел. Каждое новое message identity получает queue_seq —
sequence записи его создания. Сначала зафиксировать все новые основания tick,
потом выбрать среди eligible минимальную пару (queue_seq, incident key).
Eligibility требует открытого incident, совпадения message identity с его
текущей basis_revision и текущей binding_version закрытого почтового профиля,
отсутствия durable accepted этого key и now≥next_allowed_at incident.
Прежние key/attempts/reservations/accepted/queue_seq остаются неизменной
историей вне очереди; failed/unknown старой identity не разрешает её POST.
Срок последней reservation данного incident сохраняется также при смене
revision/binding, поэтому такая смена не ускоряет повтор раньше300с.
Поздний outcome прежнего key относится только к его истории и не подтверждает
notified текущей identity; даже accepted текущего key не возвращает старый
failed/unknown key в очередь. Новая сущность для прежних версий не нужна.
В durable reservation до POST queue_seq выбранного сообщения меняется на
sequence этой reservation; оно встаёт за уже ожидающими eligible сообщениями
даже при failed/unknown/crash. Исход отправки не возвращает старый queue_seq.
Не выбирать по detected_at. При конечном числе сохраняющихся eligible
сообщений каждое получит слот не позднее их числа последующих здоровых ticks;
restart восстанавливает тот же порядок. При одинаковом queue_seq tie по
incident key детерминирован. Accepted удаляется только из допуска к отправке,
вся его история сохраняется. Финансовые/customer retry и classifier не меняются.

**A5 — реакция и принятое решение.** Каждый incident сохраняет detected,
contained (только честная отметка неполноты/действие восстановления наблюдения),
owner_assigned=владелец GRAF, notified лишь после durable accepted текущей
message identity по A4, investigating
и resolved|accepted_risk. Source failure/conflict — severity=high технической
сверки, gap/discontinuity — high потери наблюдения, не оценка суммы/утечки.
Первый follow-up deadline=detected+300с на проверку/повтор доставки; исходный
detected/deadline не сдвигать повтором. Пропущенный deadline сохранять с
breached=true, это не доказательство ответа человека за300с. Investigating
требует сохранённого действия custodian; notified не означает прочтение.
Готовность источника после gap сама не закрывает incident и historical failure.
Только новое предметное основание по A2 меняет basis_hash/basis_revision;
обычный success, sample/tick, попытка почты и переход реакции их не меняют.
Source_generation — эксплуатационно сверенное поколение источника.
Incident_generation начинается с1 для пары source_profile/role/kind и
увеличивается лишь после закрытого incident при новом основании; incident_id
новый в каждом таком поколении. У открытого incident новое основание
увеличивает basis_revision с1, сохраняя историю прежней revision и исходные
detected/deadline; для новой revision текущие подтверждения notified/closure
не наследуются. Смена binding_version также не переносит notified прежнего
key на текущий; basis и конкретное решение владельца сама по себе не меняет.
Новый message key не покрыт прежним accepted; новое основание не покрыто
прежним решением риска. Прежние identity не отправляются по A4.
После закрытия неизменное основание ничего не создаёт; новое свидетельство
по A2 создаёт следующее incident_generation с basis_revision=1. Journal sequence
версирует каждую запись, но не является версией основания или решения.
Конкретный accepted_risk
требует явного решения владельца в этом чате; manifest связывает
source_profile/source_generation,
incident_id/incident_generation/expected_basis_revision/basis_hash,
message ref/time и digest
точного решения. Root custodian переносит реальное решение через отдельный
локальный защищённый create-once файл. Это доверенный перенос, не проверка
подписи/автора чата. Произвольный actor/owner/DB role/почтовый ответ не дают
полномочия; старое основание, replay/consumed ref, другой incident/source,
hash/schema/permission mismatch отклоняются без изменения. Перенос/consumed
ref и переход — одна durable запись до успешного ответа. Resolved требует
актуальной evidence class/ref устранения; факт отправки письма недостаточен.
Expected_basis_revision сравнивается с текущей basis_revision под lock;
отдельной ожидаемой версии lifecycle/tick нет. Допустимость перехода также
проверяется по текущему состоянию. Поэтому неизменное основание после новых
samples/mail attempts не делает конкретный manifest устаревшим, а прирост
относящегося к kind счётчика или новый gap anchor делает. Принятие одного
риска не покрывает другое основание/поколение; replay не разрешает повторный
переход даже при совпадающем basis.

**A6 — исполнение и секреты.** Root-owned fixed launchers/SSH config/host keys,
отдельные source/status ключи, forced command без shell/PTY/forwarding/stdin/
client env и без выполнения SSH_ORIGINAL_COMMAND. Caller не выбирает SQL,
image, module или путь и не получает Docker socket. Заранее закреплённый
image ID/platform/source label+env; pull/build/Compose start при аварии нет.
Контейнеры non-root/read-only/cap-drop/no-new-privileges с узкими mounts,
лимитами CPU/memory/pids и ограниченным cleanup даже после SSH disconnect.
Основной mail-only runner не получает DB/YooKassa/MinIO/meeting secrets;
DB secret остаётся на цели. Root и выделенный UID журнала — доверенная
эксплуатационная граница, не защита от compromised root/controller.
Не читать/менять F273 channel/права/конфигурацию. Нет runtime financial gate.

**A7 — приёмка и пределы.** До кода: отдельный reviewer-owned checklist,
scoped analyze и прежняя #4932. Изолированно доказать stopped maintenance,
DB outage до/во время probe, Temporal/producer outage, старый late commit,
bootstrap без success, counters restore/rollback, stop каждого observer,
SSH/Docker hang/disconnect/invalid image, bounded cleanup/privacy/no-write,
concurrency/crash/fsync/disk-full/partial tail/limits/backup restore и owner
relay negative/positive. Письма в этих проверках только synthetic transport.
Отдельно доказать успешный bootstrap без failure/conflict; неизменные
basis/message/owner manifest при success-only росте event_count и новых
as_of; late failed/conflict increment меняет только свой kind; продолжающийся
gap и новый gap после recovery различаются. Две eligible тревоги при постоянно
unknown старой получают по попытке, включая restart и равные queue_seq/tie.
Отдельно M1 unknown/failed → смена basis_revision, в другом сценарии смена
binding_version → M2 accepted → restart: M1 больше не POST, M2 dedup,
прежняя история и исходный next_allowed_at incident≥last reservation+300с
сохранены. Поздний accepted M1 не делает M2 notified и не возвращает M1
в очередь, в том числе до accepted M2.
Отдельная разрешённая установка требует независимого Postal route с обоих
узлов при DB/maintenance outage, pinned images/keys/FS custody, регулярных
ticks и учебного письма с подтверждением владельца; production отказ для
учения не создавать. Серверное accepted отдельно от mailbox/read. Общая потеря
двух узлов/сети/почты — недоступность без гарантии тревоги, не accepted_risk.
Без фактической приёмки полный O6 остаётся открыт; остальные семьи,58 gaps,
T070/T077[ ],87 task lines и все исходные сроки сохраняются.

## O16: отдельные фискальные основания T077

**ROC1–ROC4.** Probe v2: прежний набор v1, `schema_version: 2` и ровно три
дополнительных обязательных неотрицательных целых ≤2^63−1:
`receipt_canceled_count`, `receipt_overdue_confirmed_count`,
`receipt_overdue_unknown_count`. Это суммы анонимных приростов
одного snapshot; ни один не выводится из `event_count`. Ноль действителен
только в успешном v2; недоступная/неперенесённая таблица или неверные числа
не заменяются нулями. Лимит envelope 16 KiB и существующие таймауты сохранены.
v1 читается для replay и до первого принятого v2; после v2 понижение
формата — source discontinuity, включая после replay и смены поколения.
Смена source_generation не превращает ранее принятый v2 в v1. Старый
контроллер не обязан читать новые записи; совместимый контрольный образ
должен быть закреплён до изменения формата. Установочный rollback не
удаляет историю и не скрывает регрессию.

Соответствие counts: `receipt_canceled`, `receipt_overdue_confirmed`,
`receipt_overdue_unknown`. У каждого basis={source_profile,source_generation,
kind,count}; prior basis/revision, повтор, accepted и решения — A2–A5.
Receipt count не продлевает producer heartbeat попыток 0109 и не меняет
предметные счётчики reconciliation failure/conflict. При первом v2
с положительным count появляется основание, а не «успешный bootstrap».
После недоступности накопительный прирост приходит в первом здоровом
снимке. История и accepted существующих kinds сохраняются при обновлении.

Новое письмо использует O16 технический incident reference и только
закрытый смысл категории: отмена регистрации чека, подтверждённое ожидание
или «последнее подтверждённое состояние — ожидание, актуальность
неизвестна». Без ссылки на клиента/счёт и без содержимого чека.
Действующие максимумы, дедупликация и ротация A4 обязательны.


**Формат журнала и восстановление.** Сохраняется существующая внешняя
форма записи `sample` с полями `at,source,peer`; вложенный source строго
проверяется по закрытой схеме своей версии. Протокольный минимум v2
закрепляет первая успешно сохранённая и проверенная по A3 запись
`sample` с ненулевым (не null) валидным v2 source. Invalid/failed/не
дописанный sample порог не меняет; повреждённый хвост остаётся в hold.
При replay/restore минимум выводится из всей цепочки, включая записи
до последней `recovery`. Резервная копия до v2 допустима только после
доказательства, что более поздней принятой цепочки нет; иначе нужен
целый более поздний журнал. Нельзя сбрасывать минимум активацией нового
пустого журнала или новой generation. Проверяется известный head и
история pinned-образов; откат всех доказательств не объявляется обнаружимым.

Для receipt kinds после source recovery сохраняются два разных предела
для каждого count: последний принятый v2 sample (проверка полноты
суммы) и число в последнем durable receipt basis (дедупликация реакции).
Оба выводятся replay из всей цепочки одного source_profile и не
обнуляются сменой поколения. Если sample зафиксирован, а соответствующий
incident нет, повтор того же count завершает недостающий шаг. Перед
снятием recovery hold custodian сверяет старый head и непрерывность
восстановленного анонимного источника по совместимой копии. Простого
равенства чисел для доказательства lineage недостаточно. Если полноту
подтвердить нельзя или хотя бы одно число меньше последнего принятого
v2, нельзя делать rebase на меньшее число; receipt-реакция остаётся
приостановленной до восстановления источника. Первый совпадающий или
больший v2 в проверенной линии возвращает допуск. Неизменный обработанный
count сохраняет существующий incident, его message, принятые доставки и
срок повтора, даже если incident начат в прежнем source_generation.
Открытая непринятая попытка возобновляется по старой паузе и исходному
binding, пока версия привязки не менялась. Строгий прирост даёт новый
basis в текущем поколении по A5; старые failed/conflict сохраняют
собственные прежние правила, включая историческую тревогу после recovery.
Эти исключения для старого receipt basis не меняют доступ relay: решение
по-прежнему связывается с generation самого basis, его ревизией и hash.

**Три новых вида реакции.** Severity `high` означает фискальную сверку,
без оценки денег, доступа, утечки или текущего состояния провайдера.
Для `resolved` нужны прежнее durable investigating и защищённая
ссылка класса `receipt_reconciliation_verified` на актуальную операторскую
сверку именно этого basis: все новые основания рассмотрены и по каждому
есть подтверждение исхода/исправления. Для unknown требуется свежая
авторитетная сверка, снимающая неизвестность. При невозможности получить
доказательство инцидент остаётся открытым или допускает только конкретное
`accepted_risk` по A5. Probe health, нулевой прирост, Postal accepted и
факт отправки не являются доказательством устранения. В манифест и письмо
не переносятся данные счёта; используется закрытая техническая ссылка.
