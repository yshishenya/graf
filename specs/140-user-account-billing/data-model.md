## MRC: интерпретация существующих строк продления — 12.11.2026

Новых сущностей/полей/миграций нет. `WorkspaceSubscription.renewal_resolution`
остаётся существующей строкой: общий сбой проверки операции даёт `pending`,
а operation/invoice сохраняют `manual_resolution`. Исторические строки
`method_required` не переписываются массово: при чтении приоритет имеет
операция периода; planner обновляет только проекцию текущей подписки.

Область чтения: exact workspace, kind=renewal, JSON `paid_through_at`, равный
UTC ISO8601 текущего subscription.paid_through по существующему формату.
Другой срок/пространство/вид не влияет на это состояние. Без paid_through
нет такой выборки. RLS и разрешения чтения сохраняются.

| Сохранённое состояние operation | Незавершённый результат MRC |
|---|---|
| canceled или succeeded | нет; прежние правила разрешённых окон сохраняются |
| scheduled, provider_id отсутствует | нет; подготовленная, ещё не отправленная попытка |
| scheduled, provider_id сохранён | да; нельзя заявить отсутствие отправки |
| manual_resolution, sent, processing, unknown, unknown_pending, иное неразрешённое состояние | да, независимо от наличия provider_id |

Чтение UI не пишет ledger/authority. Planner читает под существующим
workspace lock и FOR UPDATE перед изменяемыми предпосылками следующей
попытки; ошибка SQL откатывает транзакцию и не означает пустой истории.
Сумма/валюта/снимок покупки, срок, grants, method, idempotence key,
authority/version и существующие audit rows неизменны. Допустимые изменения
ошибочной операции ограничены прежними state/status/audit и resolution;
нового аудита повторной отправки или второй операции быть не должно.
Retention/псевдонимизация/очистка остаются прежними; решения SSN сюда не входят.

## T077/O16 J5/J6: журнал реакции вне PostgreSQL — 03.11.2026

Дизайн для независимого ревью, не допуск к установке. Источник0109 принят
PR7914 и не меняется. Новых таблиц, миграций, БД или tenant entities нет.
Ниже один конкретный журнал для A1–A7 [контракта](contracts/operator-observation.md).

- `activation`: schema1, случайные installation_id/source_profile/generation,
  роль primary|witness, activated_at UTC, неприватная binding_version. Это
  create-once локальная эксплуатационная привязка; повторная активация поверх
  существующего состояния запрещена. Не хранит адрес, endpoints или secret.
- `source_sample`: UTC source_as_of/received_at, cumulative event_count/
  failed_event_count/conflicting_attempt_count, nullable last_event_at,
  partial=true, закрытый outcome available|unavailable|discontinuity. Event
  counts монотонны лишь в неизменном append-only источнике без restore.
  Source_generation задаётся custodian, не создаёт доказательство полноты.
- `tick`: role, local completed_at UTC, source_check outcome, peer_tick_at,
  peer journal head ref и собственные sequence/head hash. Read-only status
  возвращает только эти поля≤16KiB, без инцидентов/решений/почтовых receipts;
  чтение не пишет новый tick. Missing/invalid status — unavailable.
- `incident`: случайный incident_id, source_profile/source_generation/role/kind,
  incident_generation, basis_revision, basis_hash только стабильных полей A2
  (не всего sample), severity=high, owner=GRAF_owner, detected_at,
  initial_deadline=detected+300с, breached, containment code/evidence class/ref,
  состояния/времена detected→contained→owner_assigned→notified→investigating→
  resolved|accepted_risk, nullable closure ref/time. Времена — наблюдаемые,
  не вымышленные за прошлый outage. Contained отмечает неполноту и безопасное
  действие восстановления наблюдения, не исправление денег/данных. Новое
  основание по A2 меняет basis_revision/message key; новое поколение только
  после closure и нового основания. Обе нумерации с1; source_generation —
  отдельное сверенное поколение источника. Tick/почта/реакция basis не меняют;
  journal sequence не expected version решения. Последние принятые предметные
  counts и gap anchors сохраняются после closure, чтобы старое основание не
  возникало заново. Новая revision открытого incident сохраняет исходные
  detected/deadline и прежние подтверждения в истории, но не наследует их
  как notified/closure нового основания. Точная таблица всех7 kinds — A2.
- `mail_attempt`: incident_id/incident_generation/basis_revision/binding_version/message_key,
  последовательный attempt, reserved_at, next_allowed_at≥reserved_at+300с,
  unknown до POST; затем failed|unknown|accepted и nullable digest acceptance
  ref, queue_seq. Ключ сообщения — SHA256 канонических source_profile/
  source_generation/incident_id/incident_generation/basis_revision/kind/
  binding_version, не адреса. Повтор записи outcome не новый POST.
  Accepted той же identity сохраняется навсегда в истории. POST разрешён
  только для текущих basis_revision и binding_version открытого incident,
  без accepted этого key и после next_allowed_at incident. Unknown/failed
  прежнего key не eligible: все его attempts/reservations/accepted/queue_seq
  сохраняются как неизменная история вне очереди. Поздний outcome старого
  key меняет только его историю, не notified текущей identity. Смена binding
  не меняет basis/решение владельца, но notified старого key не наследуется.
  Новое основание не покрыто old accepted/risk.
  Queue_seq нового сообщения равен sequence создания; перед POST одной
  reservation записью меняется на её sequence, даже если исход unknown.
  Выбор eligible по (queue_seq, incident key), не detected_at; все новые
  основания tick записываются до выбора. Next_allowed_at последней reservation
  incident действует и после изменения basis/binding. Порядок восстанавливается
  replay; old identity/accepted/closure не eligible, история не удаляется (A4).
- `reaction_transfer`: source_profile/source_generation/incident_id/
  incident_generation/expected_basis_revision и basis_hash,
  action investigating|resolved|accepted_risk, evidence class/ref, message ref
  и message_at для решения владельца, decision_digest, transferred_at,
  manifest_digest/consumed_ref. Конкретный accepted_risk только из root-owned
  create-once manifest переноса фактического решения в чате. Не хранить полный
  текст сообщения; hash не удостоверяет автора. Resolved имеет evidence
  устранения; произвольный actor, DB role, общая политика и письмо не основание.
  Expected_basis_revision — только текущая basis_revision под lock, не sequence
  журнала или номер tick/lifecycle. Проверяется также допустимость перехода;
  новое предметное основание отклоняет старый manifest, новый sample — нет.

Единственный authoritative файл — append-only journal JSON Lines. Каждая
каноническая UTF-8 запись содержит sequence, prev_sha256, kind, bounded data,
record_sha256; hash считается без своего поля. Один record атомарно описывает
все изменения одной версии, включая transfer+consumed_ref или reservation+
next_allowed_at. Один nonblocking flock с общим ожиданием≤2с, append полного
record и fsync до внешнего действия/успешного ответа. Данные восстанавливаются
replay цепочки; изменяемый кэш/отдельный HEAD не авторитетны. Незавершённая
строка или противоречие — hold; не отбрасывать tail/не создавать новую историю.
Journal create O_EXCL/NOFOLLOW, file0600/state directory0700; тип/UID/mode/
nlink=1/identity lstat→fstat проверять до чтения, запрещать writable ancestors
кроме выделенного owner каталога. Root владеет launcher/config/relay inbox;
контейнер non-root с отдельным UID владеет только узким journal mount.

Запретительный `journal.jsonl.hold` содержит только постоянный признак формата,
не предметные состояния. Под journal flock перед каждой записью: защищённое
create-once/0600/owner/nlink/identity → fsync запрета и каталога → append+fsync
журнала → unlink своего проверенного запрета → fsync каталога → внешнее
действие/успешный ответ. Activation ставит запрет до создания журнала. Чужой
или прежний запрет обычный writer/status не снимает и не объявляет хвост
подтверждённым; авария внутри записи оставляет hold. После законченной записи
crash вокруг POST сохраняет unknown/прежний retry. Recovery под тем же lock
после полной проверки цепочки/expected_head, последней проверенной копии и
реальных решений синхронизирует журнал, сохраняет accepted/consumed/сроки,
записывает recovery и только затем снимает запрет. Для storage-only recovery
целой цепочки допустимо прежнее source_generation; discontinuity/restore
требуют нового сверенного поколения. Backup/restore не очищают hold копированием.
Ошибка fsync каталога после unlink возвращает отказ, хотя имя могло исчезнуть;
данные журнала к этому моменту уже синхронизированы. Попытаться вернуть запрет,
но при полностью отказавшей FS не обещать его сохранение. Это консервативный
предохранитель, не второй authoritative snapshot или двухфайловая транзакция.
Барьеры входят в60с, непрерываемый fsync ограничивается внешним runner процесса.

Пределы: record/manifest≤16KiB, journal≤64MiB и≤262144 records,≤500 incident
generations, строки refs≤255 UTF-8 bytes, UUID и SHA256 строго проверяются,
unknown keys/JSON duplicate keys/nonfinite/bool-as-int отклоняются. Full replay
и все операции входят в60с tick; рост не разрешает его молча продлевать.
При достижении любого лимита — hold/закрытая ошибка, без trimming, sampling,
удаления или автоматического archive/reset. Эти пределы должны пройти
проверку заполненного synthetic журнала до принятия реализации; новый формат
хранения при необходимости — отдельная согласованная доработка, не fallback.

Backup под тем же lock сохраняет всю цепочку/activation, checksum/count/head,
accepted/consumed/сроки. Закрытое штатное хранилище; временный synthetic backup
удаляется finally. Restore на отдельный путь проверяет полную цепочку и peer
head, остаётся в hold до сверки с последней проверенной копией и реальными
решениями. Нельзя возобновлять рассылку после stale/неполного восстановления,
забыв accepted/next_allowed_at. Откат всех копий не распознаётся по одному
локальному hash. Нет автоматического срока очистки; meeting deletion не
удаляет финансовую/операционную историю. Секреты и адреса не часть backup
журнала; custody конфигурации — отдельные закрытые эксплуатационные средства.

## T077/O16: наблюдения попыток reconciliation — 03.11.2026

Проект первого шага J1–J6, не приёмка миграции. Одна глобальная служебная
таблица `billing_reconciliation_observations`, без workspace/user/device:

| Поле | Ограничение и смысл |
| --- | --- |
| namespace | Непустая строка UTF-8, не более255байт, actual ActivityInfo.namespace |
| workflow_id | Существующий billing-reconciliation/<UUID>/v1 pattern, ≤128байт |
| workflow_run_id | UUID фактического исполнения из ActivityInfo; не payload run_id |
| activity_id | Непустая строка, ≤255байт, из ActivityInfo |
| attempt | Целое1..2147483647; положительный фактически наблюдаемый номер |
| event_kind | Только started/succeeded/failed/canceled |
| observed_at | Конечный timestamptz UTC, DB clock_timestamp(), NOT NULL |

Составной PK — все пять полей identity плюс event_kind. Валидация выполняется
до записи, CHECK/NOT NULL/unique в БД сохраняют те же границы. Поле observed_at
не обновляется при повторе. Append-only, запрет UPDATE/DELETE и destructive
downgrade непустой таблицы; автоматической очистки/исторического backfill нет.
Индекс по полному ключу покрывается PK; дополнительные индексы без измеренной
потребности не нужны. Нет failure text, task_token, counters JSON, payload,
shop, provider/payment ID, суммы, контактов или meeting content.

Изоляция: глобальный служебный источник ADR003, не tenant-данные и не bypass.
ENABLE/FORCE RLS, точные session_user=current_user=twobrain_rec_maintenance,
row_security=on, rec_context_kind=maintenance, rec_maintenance_allowed и
billing_reconciliation/billing; grants только SELECT/INSERT. App/worker/
request/SET ROLE/неверные operation/area denied; superuser/BYPASSRLS отвергает
guard. Добавить в фактический RLS inventory; защищённый backup/restore
сохраняет наблюдения/ограничения, не создаёт фиктивного tenant audit event.

Read projection: source=billing_reconciliation_observations,
scope=database_inventory, kind=current_state, coverage всегда partial.
values: attempt_count, groups[{outcome,count}], observed_retry_attempt_count,
missing_start_count; outcome — succeeded/failed/canceled/unknown/conflict,
только непустые группы, sorted. Для ключа несколько разных terminal kinds —
conflict; один terminal — его исход; ни одного — unknown. Start не требуется
для сохранения terminal: missing_start_count считает такие ключи отдельно,
не создаёт искусственный started. attempt_count равен сумме groups;
retry count — ключи с attempt>1, не сумма номеров и не число денег/HTTP retries.
Все строки независимо от report_date; future observed_at не становится
возрастом: возраста/длительности/heartbeat вообще не выводятся. Пустой
успешный inventory —0/[]/0/0, всё равно partial/reason=history_incomplete;
при conflict reason=conflicting_observations. Ошибка схемы/доступа — отказ
всего CLI по O3. Старые addon job_* и heartbeat не заполняются этим источником.

Почтовая reaction/delivery модель не вводится этим первым шагом. Принятые
owner/email/5мин/15мин/retry≥5мин/явный accepted_risk остаются обязательными
для следующего подключения по O6, включая сохраняемую попытку до POST.

## T077: storage projection — 02.11.2026

Read-only JSON projection O15/S1–S6, без таблиц/миграций/новых прав. Root
storage source/scope/kind/coverage/reason заданы контрактом. values:
workspace_count, capacity_unavailable_workspace_count, unrecognized_plan_count,
invalid_capacity_time_count; used_bytes/reserved_bytes/capacity_bytes
(целые суммы либо все null по S3); reservations {count,groups [{state,count}],
expired_active_count,invalid_value_count}; reconciliation_gaps=null.
Counts — целые количества строк/workspaces, не bytes/jobs/unique objects.
Byte totals суммируют только полные existing projections всех workspaces;
данные capacity/reservations с неизвестностью запрещают любые subtotal итоги.
Ни один ID/JSON/object key не входит в форму. Empty inventory имеет нули,
groups[], всегда partial. Отсутствие подписки увеличивает только unavailable;
NULL/unknown plan существующей подписки — также unrecognized_plan_count.
Узкий SQL-признак наличия строки не экспортируется. Snapshot, который helper
не может обработать, helper/schema/limit failure — безопасный отказ целого
отчёта, не JSON-ноль. Falsy plan_snapshot/catalog_snapshot сохраняют existing
`or {}` семантику. Область database_inventory не доказывает shop.
Текущие StorageReservation model/writers/O15 используют active/committed/
released; историческое pending в исходном design ниже не меняет runtime.

## T077: проекция запросов удаления — 01.11.2026

Существующая MeetingDeletionRequest/meeting_deletion_requests: новых моделей
и миграций нет. Migration0007 задаёт NOT NULLstate/defaultrequested и FORCE RLS;
поле state модели без явного nullable=False не заменяет реальную схему.
В SQL читается только state, наружу count и sorted closedgroups D1–D6/O14:
requested/deleting/active_purge_complete/retryable_failed, иначеunrecognized.
Nested source в values.deletion с database_inventory/current_state/partial.
Нет времени/возраста/ID/metadata/фактической проверки объектов. Counts запросов
и fair-use отдельно; artifact_completion/deadline_status/job_attempts/job_errors/
job_retries/reaction null. Сохранённый active_purge_complete не универсальное
удаление и не отменяет operator-retained Generation Call/Langfuse/Temporal.

## T077: проекция наблюдений чеков — 01.11.2026

Новой сущности/колонки/миграции нет. Существующий BillingInvoice.plan_snapshot
(JSON NOT NULL) хранит receipt_observations object map; текущий writer16entries,
parent_kind payment/refund, status pending/succeeded/canceled, source webhook/
poll/registry. Служебный inventory O13 читает только закрытые группы/counts.
Invoice/missing/invalid containers отдельно от числа map entries; JSON null
не SQL NULL, реальные constraints сохраняются. Ключи/связи/shop/environment/
времена/JSON не выбираются. Top-level receipt_registration — отдельная UI
projection; count не число уникальных чеков, pending_since здесь отсутствует.
Имеющийся READ ONLY RR/RLS/maintenance и все прежние сущности неизменны.

# Data Model: account, subscription and billing

## Modeling rules

- `workspace_id` is the billing/tenant boundary; actor/payer references the
  existing `UserIdentity`. Исключение по области, не обход tenant RLS:
  общий metadata отчёта магазина T075 хранится в отдельных maintenance-only
  таблицах по [контракту импорта](contracts/registry-operator-import.md).
- Money is integer minor units plus ISO currency (`RUB` at launch). Decimal
  bytes are integers; displayed hour equivalents never drive enforcement.
- All timestamps are UTC. Free window boundaries are derived once from
  `Europe/Moscow`; display uses the user locale/timezone with authority noted.
- Catalog, invoice, receipt lines, consent, discount and policy snapshots are
  immutable bounded schemas, not raw provider payloads.
- Provider references are opaque and environment/shop scoped. Saved payment
  method ids are encrypted and excluded from generic account/admin queries.
- Every commercial mutation has a stable logical operation, database
  uniqueness/lock and append-only audit source.
- GRAF has no refund request/case/execution entity. A refund is only a
  read-only provider observation created after merchant-backoffice action.

## Existing entities and truth reused

`Organization`, `Workspace`, `UserIdentity`, `WorkspaceMembership`,
`RegisteredDevice`, auth sessions/provider links, `WorkspaceQuotaPolicy`,
`WorkspaceUsageDaily`, `UserUsageDaily`, `AdminAuditEvent`, `TrackArtifact`,
`UploadSession`, `TemporaryUploadObject`, `DeletionFence`, `PurgeJournal` and
existing meeting deletion/lifecycle entities.

- `ensure_personal_workspace` remains the idempotent personal tenant bootstrap.
- User preferences add only bounded `locale`, IANA `timezone`, `theme` and
  optional-notification settings; verified login identity remains auth truth.
- `WorkspaceUsageDaily`/`UserUsageDaily` are display projections, never
  transactional quota admission.
- Active validated canonical playback `TrackArtifact.byte_length` and lifecycle
  status remain authoritative storage truth; no duplicate object inventory is
  introduced.

## Catalog and launch control

### `billing_plan_version`

Immutable version: stable `plan_code`, display name, cycle, `amount_minor`,
currency, typed entitlement snapshot (`quota|unlimited` per dimension), base
storage bytes, receipt/offer/fair-use policy versions, effective window and
`enabled_for_checkout`. Disabling affects new checkout only.

### `storage_capacity_sku_version`

Immutable co-termed add-on version: stable SKU, total capacity bytes
(`5_000_000_000|20_000_000_000|100_000_000_000|500_000_000_000`), cycle,
nullable approved amount, currency, COGS/value-study version, effective window
and `enabled_for_checkout=false` by default.

### `billing_launch_gate`

Versioned approval matrix for product, unit economics, finance, accounting,
legal, security, privacy, storage, QA, accessibility and provider canary.
Each gate stores a named owner, evidence class/reference, approved-at,
valid-until/revalidation timestamp, revocation state and binary blocking
outcome. Four-eyes thresholds and approver/executor role mappings are versioned
gate values. Checkout requires a complete current gate plus enabled catalog
versions; a client cannot override missing, stale or revoked approval or price.

## Account, subscription and authority

### `workspace_subscription`

One row per workspace: billing Owner, state
`free|trialing|active|cancel_at_period_end`, current plan/cycle/capacity,
trial/paid/bonus boundaries, billing anchor, default method, current recurring
authority allowed/version, renewal-resolution flag and monotonic application
version. There is no `past_due`, grace or paid suspension state.

```text
free → trialing → free
free|trialing → active
active → active                    confirmed renewal / contiguous time credit
active → cancel_at_period_end → free
cancel_at_period_end → active      resume before final cutoff
active → free                      confirmed failure or unconfirmed cutoff
```

Unknown renewal is operation truth, not paid access: at cutoff the projection
is Free and manual pay is blocked until resolution. No transition deletes
invoice/audit/data, and local Record/Stop/read/export/delete never depends on
subscription state.

### `trial_activation`

One immutable row per verified `UserIdentity` (unique): activation operation,
target personal workspace, policy version, exact `starts_at`, `ends_at =
starts_at + 7 calendar days`, verification/eligibility source and audit time.
The identity key is locked before subscription update. Signup, linked methods,
new workspaces, sessions and concurrent tabs cannot create a second row.

### `billing_consent`

Append-only evidence: workspace, actor, purpose `offer|recurring`, exact
version, accepted time and only retention-approved bounded fields. Offer and
recurring controls remain separate and unchecked by default.

### `billing_payment_authority_event`

Append-only `accepted|refused` evidence: workspace, payer/actor,
purpose/version, source
`checkout|renewal_cancel|payment_data_refusal|role_loss|account_close`,
`recorded_at`, `effective_at` and resulting monotonic authority version. The
subscription stores only current projection. An email about refund is not an
input and cannot change this ledger.

### `account_close_request`

User-scoped durable request: policy version, state
`scheduled_cooling|canceled|finalizing|completed|blocked`, exact `finalize_at`,
Temporal workflow id, re-auth class, membership/last-owner decision, future
charge veto, meeting deletion fanout, retained-finance pseudonymous subject and
session/device finalization. Launch cooling is seven days. Finalization uses
the existing deletion fence/purge journal; it does not create a second purge
system.

## Checkout, invoice and entitlement

### `billing_checkout_intent`

Mutable bounded quote before provider mutation: workspace/actor, plan/cycle,
optional capacity SKU, catalog/offer/consent versions, masked receipt contact,
base/add-on lines, candidate promo/referral discount, state
`draft|ready|locked|expired|converted|canceled`, revision and expiry. Mid-cycle
storage upgrade stores exact remaining/full billable seconds and calculated
positive pro-rata delta.

### `billing_invoice`

Immutable invoice created immediately before provider mutation: safe invoice
number, checkout revision, plan/price/tax/discount/offer/contact snapshots,
base/add-on receipt lines, amount/currency, kind
`initial|renewal|storage_upgrade`, purchased duration, planned service interval
and status. A unique logical source prevents two payable invoices for one
operation. UI timeout cannot void a pending/unknown invoice.

### `entitlement_grant`

Append-only actual access entry: workspace, source payment/time-credit/manual
correction reference, kind `paid|late_paid|time_credit|correction`, actual
`starts_at/ends_at`, plan/capacity snapshot, source authority version,
application version, optional `reversal_of_id` and bounded reason. Normal
success uses the planned interval. Late confirmation of the original renewal
creates one actual full term for the same authorized payer, even after recurring
refusal (F278 FR-041). The grant does not restore recurring authority. Independent
inability to provide service follows existing reconciliation. A later correction
remains a separate explicit audited decision outside the product.

### `storage_capacity_addon`

At most one per workspace: SKU/version, current/scheduled total capacity,
cycle/price snapshot, shared base renewal anchor, state
`payment_pending|active|change_scheduled|removal_scheduled|ended`, effective
date, source invoice and application version. It cannot exist independently of
`Личный`, stack, or own another renewal anchor.

## Payment provider observation

### `billing_operation`

Durable logical mutation: workspace, kind `initial_payment|renewal|binding`,
internal/provider idempotence keys, `provider_key_expires_at`, canonical request
hash/snapshot, actor/source, recurring-authority version snapshot, state and
timestamps. Refund mutation is not an allowed kind. Immediately before a
recurring provider call, subscription lock must still show the same allowed
authority version.

### `billing_payment_attempt`

One provider attempt for an invoice/operation: environment/shop class,
confirmed provider payment id, amount/currency, state
`checkout_pending|processing|succeeded|canceled|unknown|method_required`, safe
cancellation reason class, saved-method result and timestamps. Provider id is
unique within environment/shop; only one non-final attempt exists per invoice.

### `billing_payment_method`

Workspace + original billing Owner scoped: encrypted opaque provider reference,
encryption key id/version, safe kind/mask/expiry, state
`pending|active|revoked|expired|permission_revoked` and verified time. At most
one default active method. A successor Owner cannot inherit it.

### `billing_webhook_inbox`

Bounded signal: environment/shop, allowlisted event type, object id, dedupe
identity, received/processed timestamps and safe result/error class. Raw body
is not retained as audit. Worker must perform authoritative provider read
before state application.

### `observed_provider_refund`

Read-only reconciliation row: unique environment/shop/provider refund id,
original provider payment reference, confirmed `succeeded` status,
amount/currency, provider timestamps, observed/last-checked timestamps,
source set `webhook|poll|registry`, receipt-registration state and monotonic
applied-consistency version. It contains no request, claimant, reason,
calculation, decision, correspondence, SLA, operator action or user-visible
state. GRAF never creates this provider object.

Уточнение фактического T077/O11: модель ObservedProviderRefund и таблица
observed_provider_refunds имеют environment без shop_id, status/source
NOT NULL и nullable observed_at/default now(). Объявленный writer сохраняет
пару succeeded/provider_observation; transport webhook/poll/registry не
являются значениями row.source. Историческое описание выше не доказывает
наличие дополнительных столбцов или текущую shop-привязку. Collector
читает только status/source/count и безопасную неизвестную группу,
без сумм/связей/времени; inventory, всегда partial, не сверка и не SLA.

### `billing_receipt_state`

Payment or observed-refund linked: kind, approved configuration version,
bounded provider registration/reference class, `pending|succeeded|canceled`,
requested/confirmed timestamps, last poll and error class. Money state and
fiscal state are separate. Restricted contact snapshot remains on invoice and
is omitted from general/admin projections.

Для O11 это историческая проектная сущность: отдельной BillingReceiptState
модели/таблицы нет. Реальные observations находятся в ограниченной карте
BillingInvoice.plan_snapshot, отдельно от прежнего receipt_registration.
Они не читаются этим срезом; values.receipts/reconciliation_gaps=null,
pending/canceled и исходные сроки не выдаются за проверенные.

## Usage and storage

### `free_usage_window`

Unique `(workspace_id, capability, window_start)`: policy version,
`included_seconds=18_000`, UTC start/end derived from the Moscow calendar
month, committed/reserved projection and reconciliation freshness. No rollover.

### `usage_reservation` / `usage_ledger_entry`

Reservation stores authoritative admission/window, media/source identity,
declared whole seconds and unique operation. Ledger entry stores accepted
non-overlapping source range, committed seconds and release/reversal linkage.
Admission checks committed + active reservations + incoming. Only unique
successful ranges commit; failed/canceled/rejected/unaccepted ranges release.
Paid/trial actual usage may be observed but cannot deny from a commercial
counter.

### `storage_reservation`

Transactionally reserves declared normalized playback bytes for a unique
upload/job with `pending|committed|released`, expiry and final
`TrackArtifact` reference. Admission locks workspace capacity and checks:

```text
sum(active validated canonical playback TrackArtifact.byte_length)
+ active reservations + incoming <= effective capacity
```

Commit requires verified active `meeting-review.m4a`; failure/cancel releases.
A small reconciled projection may cache used/reserved/freshness, but it is
rebuildable and not source truth. `meeting-transcription.wav`, legacy
`mic.wav`/`incoming.wav`, transcripts/notes, derivatives, replicas/backups,
transient/local/provider objects and logically deleted artifacts contribute
zero customer bytes.

### Existing transcription-source lifecycle extension

Current and legacy source artifacts keep role, actual bytes, transcript-import
verification, playback verification, policy version, purge deadline/evidence
and bounded recovery state in existing artifact/lifecycle/purge journal records.
Normal purge requires approved recovery policy. Accepted meeting deletion or
account-close finalization overrides that delay: access/quota ends immediately
and all primary artifacts enter mandatory purge unless a formally approved hold
exists.

### Existing transient upload/object extension

Explicit `Обработать без сохранения аудио` stores admission/job reference,
actual bytes, state, `terminal_at`, `purge_due_at ≤ terminal + 15 min` and hard
`expires_at ≤ admission + 24 h`. It never becomes playback inventory. Missed
purge is a lifecycle/privacy gap, not chargeable storage.

## Promotions and referrals

### `promotion_campaign` / `promotion_redemption`

Versioned normalized-code hash, eligibility/window/scope/discount/caps and
immutable application snapshot. Redemption state
`reserved|redeemed|released|reversed` has bounded expiry and subject uniqueness.
Invoice creation revalidates and locks counters. Raw codes do not enter logs or
analytics.

### `referral_link` / `referral_attribution`

`referral_link` is one stable opaque share link per personal inviter workspace
(`workspace_id + inviter_user_id`), with a hashed token, campaign version,
active/expired state and bounded expiry. The public canonical path is
`/r/{opaque}`; `/referral/{opaque}` remains a non-indexed compatibility alias.

`referral_attribution` is one first-touch row per invitee and link, copied with
the inviter/workspace authority and lifecycle
`issued|bound|registered|paid|pending_maturity|available|applied|expired|rejected|reversed`.
The row stores only a coarse `risk_signal` such as `review`, never raw device,
IP, email or payment-profile evidence. Its first reward ledger row is linked by
`time_credit_ledger_entry.referral_attribution_id`.
The link is not consumed after the first signup: concurrent new invitees get
separate attribution rows, while the invitee/user uniqueness and first-payment
source uniqueness keep rewards idempotent. Email and new OAuth registration use
the same binder; existing accounts are never re-attributed. Referral lookup
contexts expose only the bearer-token link or the current invitee's own bound
row under RLS; inviter identity is not rendered to the invitee.

### `time_credit_ledger_entry`

Append-only target-workspace service credit: 7 or 30 days, first paid
source/cycle, `maturity_at = confirmed payment + 14 calendar days`, expiry,
state `pending|available|applied|expired|reversed`, applied interval and
`reversal_of_id`. Unique first-payment source; cap 180 granted days per rolling
12 months. Active renewal shifts charge anchor; cancel-scheduled extends only
final service/add-on cutoff; Free holds credit up to 12 months. No cash value,
receipt or mutable wallet.

Уточнение чтения T077/credit ledger (01.11.2026), C1–C6 O10: новых сущностей
нет. Фактический TimeCreditLedgerEntry дополнительно допускает сохраняемый
rejected; matured не является состоянием строки. Диагностика читает только
state/maturity_at/expires_at, без days/IDs/source_ref/applied interval.
Отрицательная reversal — отдельная строка и не денежный долг; изменение
state исходной строки не выдаётся за неизменность всех полей реестра.
Четыре временные группы применимы только pending/available; достигнутая
граница не доказывает eligibility, сбой задания или пропущенный SLA.
Миграция0044 задаёт обе даты NOT NULL; несогласованный порядок дат явно
неполон, NULL-ветвь — защитная семантика, не разрешение ослабить схему.

### `fair_use_review`

Narrow non-meter restriction: workspace, affected capability, reason class
`automated_bulk|resale|limit_circumvention|security_abuse`, bounded operator
reference, urgency/state, `starts_at`, `review_by ≤ starts_at + 24h`, appeal
and decision. The persisted row is workspace/user scoped and deduplicated by
the opaque evidence reference; the notification outbox receives only a hashed
subject and the `/account/fair-use` action path. Volume/IP/device alone cannot
decide it. Local Record/Stop and existing read/export/delete remain available.

Уточнение T077/fair-use inventory (01.11.2026): существующая таблица
fair_use_reviews с NOT NULL state/starts_at/review_by и CHECK state/deadline.
Новых сущностей/миграций нет. Читаются только state и две даты внутри SQL;
наружу — закрытые количества F1–F6 O12. confirmed не снятое ограничение.
Pending notice/restricted/appealed классифицируются по корректности расписания,
началу и сроку; остальные state не входят в buckets. Сохранённый срок не
подтверждает владельца/доставку/разрешение. Не конечные даты безопасно
неполны; положительная тестовая схема сохраняет реальные constraints.

## Notifications, audit and reconciliation

### `transactional_notice`

Idempotent outbox keyed by logical event/recipient/channel/template version,
with locale, safe destination class, delivery state/attempts/error and
timestamps. Marketing preference cannot disable mandatory security/financial/
receipt messages. Refund correspondence is outside this outbox.

### `billing_audit_event`

Append-only actor/workspace/action/target class/outcome/reason/source/time.
Broad admin projection omits provider ids, amounts, contacts, codes and private
payloads. Observed refund audit records only source/reference class/outcome and
projection before/after, never email/backoffice content.

Уточнение T077/free_projection (01.11.2026): новых сущностей или миграций нет.
Наблюдение читает только action/outcome/reason_code/target_kind/created_at
существующего billing_audit_event. Реальная миграция0044 допускает NULL
created_at; now() — начало транзакции. Event-window counts и inventory
undated_count не становятся источником финансового состояния, уникальными
workspace или окончательным дневным итогом. Формат — P1–P6 контракта O9.

### `reconciliation_gap`

Internal/provider/registry mismatch: object class, safe reference, severity,
source, detected/checked/resolved times, owner and bounded resolution class.
Gaps are internal operations truth, never a user refund status.

### `registry_import`

Реализация T075 использует `billing_registry_imports` (неизменяемый receipt
попытки, scope/digests/counts/completeness/previous receipt/DB identity/time)
и `billing_registry_gaps` (стабильный ключ, поколение, owner/severity/deadline,
detected/checked и resolution/actor/time/closing receipt).
Полный ключ повторов, атомарность, защита замены и RLS определены в
[контракте импорта](contracts/registry-operator-import.md). Raw CSV, provider
object IDs, суммы и контакты здесь не сохраняются; разбор и проверка identities
выполняются только в памяти. Исходный экспорт команда не копирует и не удаляет.
Состояния общего магазина не привязываются к произвольному workspace.

## Transaction boundaries and invariants

1. Checkout submit locks intent/workspace, revalidates catalog/gates/consents/
   discount/floor, creates one immutable invoice + operation, then calls
   provider. After mutation, pending/unknown invoice and discount remain locked.
2. Provider payment state applies only after authoritative read. Redirect and
   webhook body cannot grant access. Same operation/key resolves unknown; no
   silent new payment exists after provider-key expiry.
3. Renewal planner creates one `(subscription, paid period)` operation.
   Cutoff applies Free under the current F278 rules. A confirmed late renewal
   grants the same payer one paid term even after refusal; refusal stays in force
   for future sends. Independent service gaps remain subject to reconciliation.
4. Trial uniqueness is identity-scoped; plan/subscription/usage/storage are
   workspace-scoped. Every mutation rechecks current membership/role/session.
5. Free usage commits only deduplicated accepted ranges. Storage admission
   reserves bytes then converges on existing active playback `TrackArtifact`
   truth. Logical deletion releases quota and existing purge lifecycle wins.
6. Base/add-on/cancel/renewal/time credit serialize on one workspace
   subscription; add-on never owns a second anchor.
7. Provider-confirmed refund observation is read-only and idempotent. It may
   prevent/reverse referral reward by policy; any entitlement/add-on correction
   needs separate explicit audited authority and never restores recurring
   consent. No provider refund mutation path exists.
8. Account-close scheduling vetoes future charges; finalizer reuses existing
   meeting deletion/purge and then revokes sessions/devices.
9. Every workspace/user table joins the RLS inventory. Worker/maintenance paths
   use exact existing tenant or allowlisted maintenance context.

## Retention and deletion

Account/profile/session data follows account close. Required invoice, consent,
authority, payment, observed provider refund/receipt, entitlement, audit and
reconciliation records retain the approved financial period with identity
minimized where lawful. No refund email or merchant decision evidence enters
GRAF. Playback/source/transient artifacts follow existing lifecycle and the
specification’s deletion precedence; backup expiry and YooKassa-controlled
objects remain separately disclosed.

## T068/T070: пробный срок и очередь уведомлений

Существующая `TrialActivation` задаёт ID, пользователя, пространство и обе
даты. Существующая подписка подтверждает текущий пробный срок и владельца.
Идентификатор события очереди связывает ID активации и фазу. В полезных
данных только даты и фиксированный путь кабинета; адрес определяется из
действующей подтверждённой личности при отправке, отдельно от записи
очереди. Подавленная запись остаётся свидетельством обработанной фазы.
Новые таблицы, роли и поля не требуются.

## T075/T077: часы и основания реакции на чек — 10.11.2026

Использовать ограниченные метаданные уже существующего счёта: одна запись
на чек оплаты, привязанная к проверенному родителю, и одна запись на каждый
известный чек возврата в существующей ограниченной карте. Индивидуальная
связь проверяется внутри БД; внутренние ID, сумма, контакты и ответ провайдера
не выводятся наружу. Привязка: среда/магазин из проверенного снимка
операции, workspace, счёт и исходная операция; для возврата — ещё прежний
подтверждённый refund и неизменный ID чека. Отсутствующая или несовпадающая
привязка не допускает GET. Первый ID чека оплаты прикрепляется к прежнему
логическому чеку; другой ID, несколько записей одного чека оплаты,
несовместимость старой карты с верхним полем или перепривязка известного ID
считаются конфликтом. Прежнее подтверждение остаётся; сверка неполная.
Лимит карты прежний: нехватка ёмкости не вытесняет запись или основание.

`billing_receipt_identities` хранит только техническую связь для проверки
уникальности: ключ (среда, магазин, ID чека) закреплён за workspace, счётом,
видом и ID родителя. Карту счёта читают как прежде: таблица не хранит
состояние, даты и основания. Новый ключ и карта записываются в одной
транзакции. Повтор той же связи разрешён, другая связь даёт общий конфликт
без раскрытия чужой записи. Составная связь со счётом удаляет ключ вместе со
счётом; срок хранения и процедура удаления не меняются.

Новые покупки сверяют сохранённые shop/environment и существующую
авторитетную привязку операции. При старой операции без сохранённой привязки
узкий опрос её не ищет в текущем магазине по догадке. Иной уже существующий
авторитетный GET платежа может дать первое доказательство только если ответ
явно подтверждает магазин и среду, а ID, сумма, валюта и связь счёта проходят
прежнюю проверку. Такой GET сохраняет подтверждённые магазин и среду
в закрытых метаданных чека как неизменную привязку к той же операции, не
меняя исторический снимок операции. Узкий опрос и проверка 72ч принимают
это доказательство при полном совпадении с текущим магазином и средой.
Неполный legacy GET продолжает прежний платёжный путь, но не создаёт факта
или привязки. Для отдельного GET чека проверяется запрошенный ID и
неизменная связь: ответ под полномочиями исходного магазина, совпадающий
parent ID, исходная операция с проверенной привязкой магазина (в снимке
или подтверждённых метаданных чека оплаты), а для возврата — сохранённый
возврат в той же среде и с тем же счётом.
Отсутствие optional payment hint не ослабляет эту цепочку; присутствующий
hint обязан совпасть. Несколько подтверждённых receipt ID одного refund
различаются, уже известный ID не меняет parent.

До первого нового наблюдения верхний статус оплаты и известные записи
возврата используются только для обнаружения кандидатов и признака неполноты,
не для синтеза даты. Старый `pending` после нового подтверждённого GET
получает самостоятельную нижнюю границу 72ч; исторический пробел не стирается.
В каждом результате прохода maintenance публикуются только агрегаты
`legacy_pending_unknown`, `binding_unverified`, `receipt_state_conflict`,
`receipt_source_invalid`, `receipt_capacity_reached` и
`receipt_poll_incomplete`; это счётчики наблюдаемых случаев в ограниченном
проходе, не полная инвентаризация. Ни provider ID, ни ID счёта, ни содержимое
карты в результаты, письма, логи и клиентский API не добавляются.

Для логического чека оплаты часы и основания лежат в закрытом поле
`receipt_registration_timing` счёта. GET платежа и GET отдельного чека
используют это поле до и после появления ID. Для чека возврата те же
поля лежат в его записи карты. Поле времени не создаёт ID чека.

В записи: подтверждённое состояние, nullable UTC
`first_confirmed_pending_at`, признак исторически неизвестного возраста,
nullable время последней резервированной попытки GET, закрытый результат
чтения и неизменяемые отметки `canceled` / `pending_overdue` с временем
обнаружения, исходным сроком и классом свежести. Время — UTC PostgreSQL
`clock_timestamp()` после проверки GET и под блокировкой для срока/
резервирования. При более раннем времени, чем сохранённое, просрочка не
выводится. Снаружи только закрытые классы неполноты и агрегаты без ID.
O13 Q4 остаётся `null` в старой проекции.
Для `canceled` срок совпадает с подтверждением; для `pending_overdue` он
равен первому подтверждению +72ч. Старый статус без новых полей читается
прежним способом; отсутствие времени остаётся неизвестностью. Транзакция,
откат, повтор и восстановление сохраняют единственность основания; права
доступа, срок хранения счёта и режим удаления остаются прежними. Эти поля
не подтверждают приём письма и не являются журналом действий владельца.

## T077: анонимные приросты оснований для O16

Внутренняя append-only таблица `billing_receipt_observation_deltas`: технический
bigint PK и три неотрицательных целых приращения, хотя бы одно >0.
Запись не содержит ID счёта/операции/чека/workspace, магазина, timestamp,
контакта или связи с invoice. Хранится вместе с внутренним источником O16;
удаление счёта не удаляет обезличенную статистику. Нельзя очищать счётчики
с обычным обслуживанием или удалением счёта; несогласованный сброс — gap.
Возможное свёртывание истории только отдельной проверенной процедурой,
с сохраняемыми totals и совместимостью backup/restore.

На INSERT/UPDATE снимка выборка из верхнего времени логического чека
оплаты и отдельных валидных refund entries: только закрытые основания
`canceled` (confirmed, due=detected) и `pending_overdue` (confirmed/unknown,
due=first+72h, detected>=due) с UTC. Старое основание присутствует даже
после смены статуса на терминальный. Сравнивается наличие валидного
основания по локальной паре (логический чек, тип основания); изменение
freshness/времени уже существующего валидного основания — конфликт, а
не новый прирост. На UPDATE подмена или исчезновение валидного основания
в сохраняемом счёте не допускается. DELETE счёта разрешён по старым
правилам и прироста не даёт. В старых картах отсутствующие поля и неверные
контейнеры не конвертируются в факт; некорректная форма присутствующего
основания на начальном переносе останавливает миграцию без частичного
переноса. Валидные существующие основания переносятся одним итоговым
приростом под блокировкой записей. Snapshot из восстановления БД
обрабатывается штатным режимом смены поколения O16; прямой reinsert
сохранённого исторического счёта вне процедуры восстановления не является
поддерживаемым способом работы.

Начальное чтение выполняет только доверенная миграционная роль с правом
полной выборки под FORCE RLS. Под блокировкой записи счетов включается
`SET LOCAL row_security = off` как в 0110: если RLS могла бы скрыть строки,
сам SELECT обязан завершиться ошибкой, а не успешным пустым переносом.
RLS не выключается в схеме и право обхода не выдаётся runtime-ролям.
Создание/заполнение таблицы, ACL и подключение триггера фиксируются одной
транзакцией; проверка открывает другой tenant с ненулевой историей.

Постоянная DB authority — выделенная кластерная роль
`twobrain_rec_receipt_observation_writer`: NOLOGIN, NOINHERIT,
NOSUPERUSER, NOBYPASSRLS, NOCREATEDB, NOCREATEROLE, NOREPLICATION. Доверенный
владелец миграций создаёт её при отсутствии и проверяет эти свойства
и отсутствие членств в обе стороны; неправильную роль не присваивает.
Повторный bootstrap проверяет те же свойства, включая запрет SET ROLE
для runtime. Не удалять кластерную роль при downgrade другой базы.
После установки ей остаются только USAGE схемы, INSERT в новый источник,
USAGE его sequence и отдельная INSERT-политика под FORCE RLS. Временные
полномочия для установки/передачи ownership отсутствуют после commit.
Функция SECURITY DEFINER принадлежит только этой роли; предел кода —
OLD/NEW и INSERT чисел в именованную таблицу. Проверяются точная
таблица/схема, событие и уровень триггера. Фиксированный search_path,
полные имена, без dynamic SQL. Ни PUBLIC, ни runtime-роли не получают
EXECUTE или возможность назначить функцию триггером на иной таблице.
Проверяются эффективные права, включая наследование и default grants.
App/media не имеют доступа к таблице, sequence или функции; точная
maintenance-роль получает только SELECT по прежней политике. Bootstrap
снимает широкие табличные/sequence grants; инвентарь отражается в F031.
Перед destructive downgrade непустой источник блокирует удаление; рабочий
откат сохраняет миграцию и использует совместимые image/reader. Суммы
приростов считываются без cursor по ID или времени, с SQL timeout.


## T070/T068: состояние наблюдения архива

Нефинансовая рабочая проекция, не источник bytes/capacity и не реестр встреч.
`storage_notification_states`: workspace_id PK/FK workspaces ON DELETE CASCADE;
owner_user_id nullable UUID исходного наблюдаемого owner; band normal/80/95/100;
generation bigint >=0; observed_at finite UTC. State существует только после
достоверного снимка: error не создаёт строку и не стирает последний снимок.
При смене owner band считается первым наблюдением, generation монотонно
возрастает только при новом высоком событии и не сбрасывается (в том числе
A→B→A). Отсутствие права/согласия не ставит очередь, но сохраняет достоверный
band. State закрытого/объединённого владельца не воссоздаётся; существующий
begin-finalization явно удаляет его по frozen content_workspace_ids в одном
commit с identity=closed. Физическое удаление Workspace также даёт cascade.

`storage_notification_scan`: единственная system-owned строка с постоянным
ключом; cycle_started_at, upper_workspace_id, after_workspace_id nullable.
Все null означают границу цикла. Активный цикл имеет finite cycle_started_at
и upper UUID; after nullable до первого кандидата, далее <= upper.
UUID здесь — положение обхода, не FK: удаление workspace не уничтожает курсор.
Агрегаты attempted/observed/skipped/failed — неотрицательные bigint;
attempted=observed+skipped+failed, last_error_code nullable из закрытого набора.
last_finished_summary — nullable закрытый JSON-снимок последнего завершённого
прохода: started_at/finished_at, четыре счётчика и incomplete (failed>0).
Даты finite UTC, finished_at>=started_at, unknown keys не допускаются.
Он сохраняется при начале нового цикла; нет идентификаторов кандидата/owner
или текстов исключений. Новый сервис/история проходов не создаются.
До 100 отдельных committed кандидатов/вызов; бюджет и fairness в Plan.

Atomic successful observation под cursor/advisory/Workspace row locks: state
owner/band/observed_at и при подъёме новый generation + outbox + cursor advance.
Ошибка savepoint откатывает snapshot/state/outbox; во внешней транзакции
фиксируются только cursor aggregates/error/advance. После освобождения
Workspace lock не создавать даже error state. Общая ошибка DB/commit не
считается продвижением. Unique event_id использует workspace, монотонный
generation и уровень; recipient неизменен, channel=email.

Allowlist payload: storage_level, storage_used_bytes, storage_capacity_bytes,
storage_observed_at (безопасная дата/МСК), action_path=/billing/usage.
Целые used>=0, capacity>0; уровень обязан соответствовать целочисленной
классификации. Служебный retry deadline не показывается. Адрес берётся заново
у того же recipient; сумма, email, provider refs и материалы встреч не хранятся.

Обе таблицы относятся к точной maintenance identity с FORCE RLS; state имеет
workspace parent и cleanup по account finalizer, scan — системная позиция.
Права SELECT/INSERT/UPDATE только billing reconciliation/billing; state SELECT/DELETE
также в account-close context billing_reconciliation/account. Нет request,
worker или media доступа. Migration и повторный bootstrap сохраняют минимум.
Непустое состояние запрещает downgrade; сброс поколений не является rollback.

## T070/T068: сохранённое операторское рассмотрение fair-use

FU1–FU8 используют существующую fair_use_reviews: первоначальные
workspace/subject/capability/reason/evidence_ref/starts_at/review_by неизменны;
appealed_at/appeal_ref сохраняют первый переход; resolved_at/resolution_code
фиксируют единственное окончательное решение cleared или confirmed.
Совпавший повтор не меняет даты/аудит/очередь; противоположное решение
возвращает конфликт. Оператор не передаёт произвольную дату или urgent.

Существующий billing_audit_events должен связывать внутренний review
со временем, ограниченным operator-ref, переходом и закрытым result code.
Broad audit не содержит evidence_ref, переписку, контакты, материалы встреч
или финансовые поля. CLI выводит только закрытый result code/dry_run/status.
Строка от прежнего helper сама не доказывает правоту классификации или SLA.

В существующей очереди отдельная служебная связь review/phase нужна для
проверки происхождения; она не попадает в отображаемые поля. Фазы
notice/appealed/cleared/confirmed имеют разные логические event keys.
Recipient неизменен после постановки; текущие права и подтверждённый адрес
проверяются до claim. Прежний принцип unknown-before-POST сохраняется.
Полей достаточно, но существующий audit не доказан append-only:0044/0074
и bootstrap выдают более широкую DML-возможность. Проект требует узкую
миграцию защиты переходов/истории в этих таблицах; новую сущность заранее
не добавлять. Защищённые action created/appealed/resolved связываются с
workspace/review, уникальны для перехода, не допускают подмены source/actor,
UPDATE/DELETE или переноса в другое семейство. App сохраняет только
разрешённую апелляцию, maintenance — create/resolve с реальной identity;
права сохраняются после повторного bootstrap. Audit атомарно создаёт AFTER
DEFINER trigger фактического review перехода; минимальная NOLOGIN роль имеет
только INSERT нужных audit столбцов, без SELECT/UPDATE/DELETE или role memberships.
BEFORE INVOKER guard review разрешает create/resolve только реальному
maintenance, app — только прежнюю апелляцию; guard audit запрещает прямую
подделку reserved namespace также maintenance, а OLD ИЛИ NEW проверка не даёт
переименовать/стереть историю. UUID/server time/db_login/db_writer и закрытый
versioned envelope задаёт DB; declared_operator не аутентифицирует человека.
Единственный полный формат v1 — contracts/fair-use-operator.md, раздел
«Точный формат operator-ref и audit v1»: operator-ref ровно35ASCIIсимволов
`^op-[0-9a-f]{32}$`,10явных audit столбцов и ровно8обязательных JSON keys
с указанными типами/NULL/enum, без unknown keys/coercion. Новых столбцов
review/audit для этого не нужно; CLI и DB guard используют тот же договор.
Python не пишет reserved audit. Ошибка trigger откатывает source/outbox.
UPDATE USING сохраняет valid account_merge SELECT FOR UPDATE, но
WITH CHECK/guard не дают мутировать review этим context. Это новая узкая
миграция защиты, не новый журнал/table и не уже установленная гарантия.
Старые строки не получают source/operator/time задним числом. Существующие
метаданные закрытого аккаунта не стираются; destructive downgrade с новой
историей запрещён. Smoke cleanup под прежним корневым lock делает preflight
до любого изменения/удаления объектов; любая review/защищённый audit или
ошибка чтения останавливает очистку с safe code, без DELETE review/bypass.
Новое действие не создаёт commercial balance
или storage ledger entry и не изменяет существующую merge state semantics.


## T070/T068: account-close notification snapshot — 12.11.2026

Новых таблиц/полей/миграций нет. AccountClosureRequest остаётся источником
requested_by_user_id/workspace/policy/state/requested_at/finalize_at/canceled_at;
семантика его состояний не меняется. В существующем delivery event_id равен
`account.close:<request.id.hex>:scheduled|canceled`, исходный recipient неизменен.
Safe snapshot и запреты — §ACN contracts/notifications-support.md. Обновление
phase в исходной записи не переписывает прежний delivery. Retry использует
прежний внутренний not-before ключ; он не часть текста или источника времени.
