# Implementation Plan: Личный кабинет, тарифы и биллинг

**Branch**: `codex/140-user-account-billing` | **Date**: 2026-08-06 | **Spec**: [spec.md](spec.md)

## Summary

Текущий проект11.11.2026 — T070/T068, операторский источник fair-use;
канонический scoped проект и условия допуска в заключительном разделе
«T070/T068: операторский источник fair-use». Ниже — прежние датированные срезы.

Активный срез03.11.2026 — T077/O16 J5/J6 после принятого PR7914/J1–J4.
Ответы владельца приняты. Ниже подготовлен дизайн регулярной проверки,
почтовых тревог и сохраняемой реакции для независимых checklist/analyze;
это ещё не допуск к коду или установке. Порядок5мин/15мин/retry≥5мин,
исходные сроки и полный остаток той же T077/O6 сохраняются.

Активная доработка 01.11.2026 — T077/#4932: внутренний read-only отчёт
по [контракту O1–O8](contracts/operator-observation.md). Полоса:
active Spec Kit slice, high-risk (диагностика/финансы/PostgreSQL).
Предыдущие срезы T048 ниже сохраняют собственные результаты и остаток.

Первый шаг T077: заменить непотребляемую модель снимка в billing/monitoring.py
конкретным read-only сбором и добавить cli/billing_monitoring.py по образцу
cli/billing_registry.py; argparse, SQLAlchemy и существующий maintenance guard.
Пути имеют префикс apps/server/src/twobrain_rec_server/. Новых таблиц,
миграций, зависимостей, scheduler и публичного API нет. Admin/readiness/F254
не менять. PostgreSQL isolation/read-only установить на connection до hooks;
общий timeout включает setup/lock. registry_status использовать после bounded
preflight и проецировать только разрешённые поля, без raw ответа.

Порядок внутри исходной T077: O1–O8 и reviewer-owned
checklists/operator-observation.md → независимый допуск → scoped analyze →
подтверждение #4932 → RED → минимальный collector/CLI → unit плюс настоящая
изолированная PostgreSQL CLI/guard/snapshot/timeout/privacy/no-write проверка
в tests/unit/test_billing_monitoring.py и
tests/integration/test_billing_monitoring_postgres.py → независимое кодовое
ревью/converge → три обязательных exact-SHA/base PR gates.

Предварительный Constitution Check: проект сохраняет maintenance/RLS,
metadata-only вывод, source/deletion truth, capture/Stop, деньги, согласие
и права; нет egress/production/Dev. После независимого review повторить.
Полный остаток FR-089/O6 — та же T077, не новая задача/отмена; частичный
JSON не закрывает issue и не является доказательством работающих тревог.

Предыдущая доработка 30.10.2026 — F140/T075/#4930, операторский импорт
по [контракту B1–B3](contracts/registry-operator-import.md). Полоса:
`active Spec Kit slice`, high-risk gates для PostgreSQL, полномочий и денег.
Прежний план ниже сохраняет историю; заменённые каталог/renewal/emergency-stop/
launch-table/brand-distance требования не восстанавливаются (см. §Scope Summary
`spec.md`). Новая служба, интерфейс, SDK и финансовая mutation не нужны.

Порядок: уточнение → независимое ревью B1–B3 → анализ → существующая #4930 →
parser/CLI/storage → изолированная PostgreSQL/права/restart → converge →
проверенный commit/PR → `governance-fast`, `macos-pr`, `pr-metadata` и общий
валидатор точного SHA/основы. До scoped PASS код не меняется. Частичный импорт
с `financial_status=not_checked` оставляет T075 открытой.

Пути реализации: существующий `billing/registry.py`, один внутренний
`cli/billing_registry.py`, два определения metadata-таблиц рядом с billing
models, одна миграция от фактического Alembic head, `db/rls_validation.py` и
профильные parser/CLI/DB tests. До миграции проверить head, grants и существующий
advisory-lock pattern. Новых зависимостей нет. Финансовую сверку продолжать в
том же T075 после полного импорта, используя authenticated API time; локальные
`created_at/observed_at` не подходят для дня подтверждения.

Предварительная конституционная проверка: PASS для дизайна — доступ только
maintenance, не меняются charge/entitlement, client secrets, capture/deletion
или production. После независимого ревью повторить оценку; runtime/RLS/release
gates этим не принимаются.

Расширить существующий Jinja/HTMX-кабинет GRAF личным account-and-billing
контуром. GRAF остаётся источником истины для каталога, согласий, invoice,
subscription schedule, entitlement, точных Free-секунд, playback-storage,
промокодов и 7/30-дневных реферальных начислений. YooKassa выполняет hosted
payment/binding, хранит opaque payment method и остаётся источником истины о
платеже, чеке и уже выполненном merchant refund.

Возврат не становится функцией продукта: кабинет показывает отдельный email,
safe invoice reference и `Написать письмо`; переписка, решение, расчёт и ручной
возврат происходят вне GRAF. GRAF не содержит refund case/form/status/operator
UI/API/CLI и не вызывает refund API. Он только идемпотентно сверяет
authoritative provider refund/receipt truth, чтобы финансовый ledger,
entitlement и referral credit не расходились.

Переиспользуются текущие `Organization`/`Workspace`/`UserIdentity`/
`WorkspaceMembership`, personal-workspace bootstrap, session rotation, CSRF,
tenant context/RLS, cabinet shell, MinIO lifecycle, Temporal, Postal и `httpx`.
Не добавляются SPA, YooKassa SDK, generic payment-provider abstraction, wallet,
dunning engine или второй платный тариф только ради хранения.

## Technical Context

### T077/O16 J5/J6: независимое наблюдение и реакция (03.11.2026)

Полоса active Spec Kit slice/high-risk-product; Legacy Impact untouched.
Решения владельца — Session2026-11-03. Первый шаг J1–J4 принят PR7914;
его financial body/recorder/0109 и O1–O15 CLI не меняются. Новых служб,
образов, зависимостей, БД, generic incident/outbox или публичного API нет.
Переиспользовать существующий application runtime image, PostgreSQL guard,
PostalEmailLoginClient и systemd для ограниченных разовых контейнеров.

**Constitution Check до Phase0:** III/IV/VI и Docker baseline сохранены;
только технические метаданные, секреты отдельно, без финансовых mutation,
изменения согласия, tenant bypass, capture/Stop или retention. Независимое
исследование подтвердило source-возможность варианта A; установленный маршрут
почты, образы и доступы ещё не приняты. Не выдавать их за предположенный успех.

1. Основной systemd timer на существующем astraglobal вызывает fixed launcher
   каждые300с. Встречный timer на ОС2brain.dev проверяет его durable tick,
   независимо от rec-maintenance/Temporal/PostgreSQL. Основной запуск читает
   также статус встречной проверки. Оба запускают тот же закреплённый image
   через `docker run --rm --pull never`, без Compose dependencies/start/restart.
   Это два разовых задания, не новые постоянно работающие службы. Host wrapper
   только проверяет закрепление/запускает/ограничивает процесс; прикладная
   логика исполняется в Docker. Общий отказ обоих узлов/Postal/сети остаётся
   честной недоступностью, не принятой владельцем безопасностью.
2. `infra/scripts/billing-observation-probe.sh` — root-owned fixed wrapper
   цели и фиксированных status-команд. SSH forced-command разрешает только
   заранее заданный read-only режим, без shell/PTY/forwarding/agent/env/stdin,
   SQL, image или аргументов клиента. Host keys закреплены. Wrapper не отдаёт
   Docker socket; command из SSH_ORIGINAL_COMMAND не исполняется. Отдельные
   ключи для source/status; никакой relay через них. Разовый source-контейнер
   non-root/read-only/cap-drop/no-new-privileges получает только DB secret и
   точный maintenance context. Публичного порта/HTTP endpoint нет.
3. Узкие `billing/observation_probe.py` и `cli/billing_observation_probe.py`
   читают только0109: один RR/READ ONLY снимок до hooks, exact maintenance,
   cumulative event/failed-event/conflicting-attempt counts, last_event_at.
   Не использовать MAX(time) как cursor: поздний commit виден приростом count.
   Source profile/generation задаётся защищённой установкой, не tenant input;
   понижение любого счётчика/смена generation/плохое время создаёт gap.
   Restore той же/большей мощности нельзя всегда обнаружить counts: процедура
   любого restore обязана перевести наблюдение в recovery hold и сменить
   generation после сверки, а не обещать автоматическое распознавание.
   Пустота не heartbeat. Сведения об API/container running его не подменяют.
   Предметный basis задаётся таблицей A2: failure только failed_event_count,
   conflict только conflicting_attempt_count; при bootstrap общий event_count
   не тревога. Success-only прирост/новый as_of не меняют их basis/message.
   Gap использует зафиксированный anchor эпизода; recovery не закрывает incident.
4. `billing/observation_alerts.py` и `cli/billing_observation_alerts.py` —
   один controller для tick/witness/status/local relay. Только стандартная
   библиотека и уже установленный Postal dataclass; общий Settings не читать.
   Launcher `infra/scripts/check-billing-observation.sh` запускает fixed module
   в заранее доставленном image с ID/platform/source label+env проверками.
   Ограниченный writable state принадлежит выделенному non-root UID; root
   владеет конфигурацией/родительским каталогом/launchers и relay inbox.
   Bind mounts не дают контейнеру host shell/socket/общие env или секреты
   YooKassa/MinIO/встреч. SSH выполняет launcher до запуска контроллера,
   передавая ему лишь bounded source/status envelopes через закрытый input
   mount; контроллер не вызывает host commands. Ответ — закрытый JSON.
5. Авторитетный FS journal и его fail-closed/recovery описаны в модели/A3.
   Одна блокировка на writer/tick/relay/backup, durable reservation до POST,
   accepted dedup и сохранённые next_allowed_at независимо от PostgreSQL.
   Mail-only Postal-клиент получает закрытые endpoint/key/sender/recipient;
   один POST с прежним classifier, новые повторы только здесь. Адрес и секреты
   не входят в argv/state/stdout/evidence. Настоящая доступность Postal с обоих
   узлов без основной БД/maintenance — отдельная обязательная приёмка A7.
   Очередность A4: записать новые основания, выбрать eligible по сохраняемому
   queue_seq/incident key, durable reservation переставляет сообщение в конец
   до POST, даже при unknown. Старый повтор не занимает все слоты; срок300с
   сохраняется при смене basis/binding, restart сохраняет порядок.
   Eligible только текущие basis_revision/binding_version открытого incident;
   прежние key/attempts остаются историей вне очереди. Поздний outcome старого
   key не подтверждает notified текущего; исходный retry deadline сохраняется.
6. Owner relay — только эксплуатационно доверенный локальный перенос root
   фактического конкретного решения в этом чате. Root-owned create-once
   manifest, exact source_profile/source_generation/incident_id/
   incident_generation/expected_basis_revision/basis_hash, message ref/time
   и decision digest; сравнение под lock. Accepted decision/consumed ref —
   одна durable запись до ответа. Root-доступ не выдаётся за проверку автора
   чата; компрометация custodian остаётся пределом. Ни SQL role, ни имя actor,
   ни письмо/тишина не меняют состояние. Resolved требует доказательства.
   Basis_revision меняет только новое основание A2, а не journal sequence,
   tick, попытка письма или lifecycle. Под lock проверить текущий basis и
   допустимость перехода; при старом основании после closure не создавать
   новое поколение. Все номера/переходы определены A5/моделью.
7. Порядок: семь согласованных документов → новый reviewer-owned
   `checklists/observation-alerts.md`/независимый допуск → tasks-stage пояснение
   под той же T077 → scoped analyze A1–A7/J5/J6 → sync существующей #4932 →
   RED → source/controller/launchers/units/config templates/run guide/tests/
   F140 fragment → независимые code review и converge → exact source/base
   governance-fast/macos-pr/pr-metadata/common before/after/tree-parent.
   Старые68 проверок/PR7914 не повторять без затронутой зависимости.

Пути новых units: `infra/systemd/graf-billing-observation{,-witness}.{service,timer}`;
пример без секретов `infra/env/billing-observation.example.json`; установка/
restore/rollback — `infra/docs/billing-observation.md`. Проверки:
`apps/server/tests/unit/test_billing_observation_alerts.py`,
`apps/server/tests/integration/test_billing_observation_alerts.py`,
`apps/server/tests/integration/test_billing_monitoring_postgres.py`,
`apps/server/tests/contract/test_billing_observation_infra.py`.
Существующие source/table/writers/customer mail/F273 не расширяются.

**После Phase1:** дизайн сохраняет конституционные границы; новых исключений
нет. Это root design assessment, не независимый PASS или работающая почта.
Сценарии A7 обязательны; при неподтверждённом внешнем маршруте доставка остаётся
unavailable. До независимых checklist/analyze кода нет; установка и реальная
почта ожидают отдельного эксплуатационного разрешения. Весь FR089/O6,
прочие источники,58 gaps, T070/T077[ ] остаются открытыми.

### T077/O16: постоянный журнал попыток (03.11.2026)

Полоса: active Spec Kit slice/high-risk-product (PostgreSQL, Temporal,
диагностика, финансовая граница). Legacy Impact untouched. Без новых служб,
библиотек, scheduler, Temporal RPC, продуктового API, флага запуска денег
или нового tenant. O1–O15 CLI сохраняет READ ONLY RR и прежние пределы.

**Constitution Check до исследования:** дизайн сохраняет III/IV/VI,
metadata-only технический источник, изоляцию и неизменные финансовые
результаты/согласия/locks. Нет изменения retention Temporal/Langfuse,
capture/Stop/удаления или выпуска. Принятые ответы находятся в spec,
Session2026-11-03; адрес получателя не входит в git/evidence.

1. Одна новая append-only таблица `billing_reconciliation_observations`
   в существующем PostgreSQL; модель рядом с billing models, одна миграция
   от фактического Alembic head и строка в `db/rls_validation.py`.
   По модели данных ключ попытки — namespace/workflow_id/workflow_run_id/
   activity_id/attempt, ключ наблюдения дополняется event_kind. События
   started/succeeded/failed/canceled неизменяемы; INSERT ON CONFLICT DO NOTHING
   подавляет повтор того же свидетельства. Другой terminal event сохраняется
   второй строкой и образует conflict. UPDATE/DELETE запрещены grants и
   history-trigger; записи не удаляются по возрасту или meeting deletion.
2. Новый узкий `billing/reconciliation_observation.py` получает identity
   из `temporalio.activity.info()` текущей workflow activity (SDK1.30.0),
   проверяет namespace, существующий workflow ID pattern/type, настоящий UUID
   workflow_run_id, activity_id/type и положительный attempt. Ни payload run_id,
   ни номер schedule bucket не используются вместо execution run ID.
   Нет activity context/валидной identity — закрытый сигнал неполноты,
   без вымышленной записи и без нового отказа финансовой работе.
3. В `workflows/worker.py::run_billing_reconciliation_activity` добавить
   наблюдение входа и исхода вокруг существующего тела. Наблюдение started
   включает и последующий отказ валидации payload; failed — исключение
   activity, а не банковский отказ. succeeded только после возврата всего
   существующего тела, включая его cleanup. CancelledError сохраняется как
   отмена, а не failure. Два COMMIT, maintenance→освобождение locks→webhook→
   initial checkout, counters/result и исходные исключения остаются прежними.
4. Каждая запись использует отдельные engine/connection/session и короткую
   транзакцию; финансовая session не передаётся. Общий предел2с на запись
   включает settings/connect/context/guard/INSERT/COMMIT/cleanup. До первого
   SQL задать statement_timeout≤1с/lock_timeout≤0.5с на соединении; точный
   existing maintenance context и `require_billing_maintenance_database`
   обязательны. Использовать проверенный способ bounded cleanup из CLI:
   публичный AsyncConnection, синхронный driver.terminate по deadline,
   Connection.invalidate перед Session.invalidate, без shield/__aexit__
   и оставшихся фоновых задач. Это локальный ресурсный образец, CLI не менять.
5. Timeout/отказ записи не заменяет исходный result/exception и не повторяет
   финансовую работу. Пробел остаётся unknown/partial. Внешнюю отмену
   не поглощать: она прекращает работу; запись canceled — ограниченная
   попытка, а не обещание сохранения при повторной отмене/аварии. При уже
   возникшем финансовом исключении ошибка записи не подменяет его.
   Обычный logger выдаёт только фиксированный `billing_observation_unavailable`,
   без exc_info, identity, payload или исходного текста исключения.
6. В прежнем `billing/monitoring.py` одна SQL-агрегация по полному ключу
   попытки и закрытым event_kind; новое семейство `reconciliation_attempts`
   описано в model/contract. Никакого Temporal RPC, предметных объектов или
   запуска writer из отчёта. Наблюдаемый attempt>1 считается один раз;
   отсутствующие меньшие attempt не восстанавливаются. Остальные семейства,
   особенно addon job_* и heartbeat, сохраняют прежние null.
7. До кода: согласованные семь документов → reviewer-owned
   `checklists/reconciliation-observations.md` → независимый PASS → scoped
   analyze J1–J6 и тот же T077/#4932. Затем RED → модель/миграция/recorder/
   activity/collector → настоящие PG/ActivityEnvironment/CLI сценарии
   quickstart → независимые code review/converge → точные source/base gates.
   Новых task ID/issue нет;87 исходных task lines и58 gaps сохраняются.

**После дизайна:** исключений конституции не выявлено; это оценка проекта,
не независимый PASS, не фактическая RLS/backup/доставка/финансовая приёмка.
Непустой журнал запрещает destructive downgrade: миграция должна отказать
до удаления строк; проверяются пустой downgrade/upgrade и восстановление
синтетического журнала штатным PG dump/restore без долговечного дампа.
При disk-full/обрыве/несовместимой схеме запись не даёт ложного успеха,
а диагностический CLI безопасно отказывает целиком по O3.

**Обязательное продолжение O6 (уточнено J5/J6 выше):** Postal
`_post_message` пригоден без новой службы; соседний rec-maintenance loop
не обеспечивает независимость от общей остановки/БД. Нужны отдельные внутренние
recipient binding, сохраняемые reaction/delivery attempts, проверка каждые5мин,
gap15мин, retry failed/unknown≥5мин и dedup сохранённого accepted.
Не использовать tenant customer outbox с fake workspace; не менять общий
EmailLoginDeliveryError или финансовый sender. До POST нужно сохранять попытку
и next_allowed_at с защитой конкуренции; crash после Postal acceptance до journal
остаётся unknown и допускает физический дубль при разрешённом повторе.
Фактическое подключение и приёмка доставки — отдельные ворота этой же T077,
не свойство журнала. Прежние финансовые/приватностные сроки действуют сейчас.

### T077: проекция storage (02.11.2026)

High-risk-product/active Spec Kit slice, O15/S1–S6 после PR7897. Один
_storage_inventory в существующем billing/monitoring.py; _source/_closed и
ReportLimitError переиспользуются. Узкий outer join от Workspace к
WorkspaceSubscription, limit501 с отказом >500; пять полей helper и SQL
признаки наличия подписки/nonfinite релевантной даты, без целого ORM/private полей. Никакой
новой абстракции, wrapper/factory, схемы или изменения трёх существующих
storage/capacity helpers. SQL row содержит нужные читаемые атрибуты подписки.

Сначала одна SQL aggregation reservations по закрытым state/count с filtered
expired_active/invalid counters. Затем для workspace с доказанной capacity
existing effective_paid_storage → _active_reserved_bytes →
project_active_playback_storage с явными аргументами и общим as_of. Несколько
SELECT на workspace остаются под общим15с; нет скрытого batch/sampling.
Неизвестные/некорректные данные дают counts и null итогов ровно по контракту;
Отсутствие подписки увеличивает только unavailable; NULL/unknown plan
существующей строки — также unrecognized_plan_count. Falsy значения обоих
snapshot сохраняют существующее `or {}`; отдельного JSON-валидатора нет.
Форма, которую helper не может обработать, или его exception безопасно
отказывает CLI с прежним report_unavailable/exit1.
Успех всегда partial, reconciliation_gaps=null; прочие семейства прежние.

Constitution Check до исследования/после дизайна: PASS для этого дизайна —
только чтение под maintenance/FORCE RLS/READ ONLY RR, metadata-only вывод
(counts/целые байты), нет egress/финансовых/retention мутаций. Внутреннее чтение
snapshot существующим helper признано; поля не экспортируются/не логируются.
Действующий data-model storage pending — историческое описание; текущий
writer/model и O15 явно используют active/committed/released без миграции.
Ни O6, ни privacy/финансовые/ручные/выпускные ворота этим не принимаются.

Порядок: уточнение/research/model/quickstart → независимый reviewer-owned
checklists/storage-projection.md → scoped analyze/существующая #4932 → RED →
один collector и профильные сценарии в прежних unit/integration файлах →
независимые code/converge → governance-fast/macos-pr/pr-metadata на точном
source/base. До допуска кода нет. Новые реальные PG cases проходят штатный
одноразовый runner, полные Alembic схемы/NOTNULL/FORCERLS, узкие SELECT fixture
соответствуют существующей maintenance роли, не ослабляют production RLS.
Legacy Impact untouched; все87 task lines/T077[ ]/58gaps/O6/сроки прежние.
Full/CD/Dev/рабочая БД и новые dependencies не требуются.

### T077: сохраняемые запросы удаления (01.11.2026)

High-risk-product/active Spec Kit slice, D1–D6/O14 после PR7896. Один helper
SQLAlchemy select/case/count в billing/monitoring.py плюс включение в прежний
fair-use collector. _closed/_source переиспользуются; generic _groups не нужен,
так как возраста/времена не читаются. MeetingDeletionRequest/state — источник;
четыре объявленные state не брать из всего DeletionState. Root/nested sources
и приоритеты точно по контракту, без суммирования двух сущностей.

Constitution Check до исследования/после дизайна: сохранены deletion truth,
metadata-only/RLS/maintenance guard/единый READ ONLY RR/пределы/финансы/egress;
нет новых схем/прав/служб/зависимостей. Существующая migration0007 включает
FORCE RLS и rec_maintenance_allowed, не менять политику ради тестов.
В TABLES/fingerprint существующего integration fixture добавить request model;
дополнительные FK tables уже создаёт штатный runner. Для настоящих строк
использовать синтетическую Meeting/Workspace; NULLstate проверить отдельно
через SQL VALUES, не ослабляя NOT NULL положительной схемы.

Порядок: уточнение/research/model/quickstart → reviewer-owned deletion-inventory
и независимый PASS → scoped analyze/существующая #4932 → RED → минимальный
collector и проверки в прежних apps/server/tests/unit/test_billing_monitoring.py,
apps/server/tests/integration/test_billing_monitoring_postgres.py → independent
code/converge/exact PR gates. Затронутые fair-use и identity/SETROLE случаи
повторить по изменению зависимости; остальные успешные наборы не повторять.
Legacy Impact untouched; все87полных task lines/T077[ ]/58gaps/O6/T070/сроки
сохраняются. Full/CD/выпуска/Dev здесь нет.

### T077: сохраняемые наблюдения чеков (01.11.2026)

High-risk-product/active Spec Kit slice исходной T077 после PR7894.
Q1–Q6 O13: использовать существующую BillingInvoice.plan_snapshot map
receipt_observations. Две SQL-агрегации в том же monitoring.py: counts всех
invoice/missing/invalid containers и closed map groups через json_each с
CASE, допускающим только object map. SQL JSON, без JSONB миграции; SQLAlchemy
func/case/select и существующие JSON/table-valued primitives достаточны.
Тип проверять до раскрытия; scalar/array entry закрывать общей unknown.
Выбирать только counts/закрытые parent_kind/status/source, не JSON/key/ID.
Root refund count/groups прежние, receipts получает отдельный source;
приоритеты/root composite source заданы контрактом, без сложения разных count.
Top-level UI projection и даты не переиспользовать как доказательство map/срока.

Порядок: specify/clarify Q1–Q6 → узкие research/model/quickstart → reviewer-owned
checklists/receipt-inventory.md/независимый PASS → analyze/та же #4932 → RED →
один helper и включение в существующий refund collector, случаи в прежних
apps/server/tests/unit/test_billing_monitoring.py и
apps/server/tests/integration/test_billing_monitoring_postgres.py → независимые
code review/converge → exact-SHA/base PR gates. Invoice уже входит в TABLES/
fingerprint/FORCE RLS; существующие affected refund/CLI/role проверки повторить
по изменению поведения, остальные успешные наборы не повторять.

Constitution Check до исследования и после дизайна: metadata-only/RLS/guard/
снимок/лимиты/деньги/приватность/удаление/egress сохранены. Нет новой схемы/
полномочий/службы/зависимости. Это проектная оценка, не приёмка кода/всегоO6.
Legacy Impact untouched; все87 task lines/T077[ ]/58gaps/сроки сохраняются.

### T077: сроки fair-use проверок (01.11.2026)

High-risk-product/active Spec Kit slice исходной T077 после PR7892.
F1–F6 [O12](contracts/operator-observation.md#o12-следующий-срез-сроки-сохраняемых-fair-use-проверок):
одна SQL-агрегация FairUseReviewRecord в существующем
apps/server/src/twobrain_rec_server/billing/monitoring.py по образцу _credit_ledger.
CASE закрывает state; фильтры дают четыре непересекающихся pending buckets.
Вложенный CASE сначала проверяет NULL/isfinite дат, затем numeric разность
EXTRACT(EPOCH) для24истекших часов, без infinity subtraction/float/DST.
Python получает только закрытые группы/количества, не timestamps или ORM rows.
Generic _groups не подходит: будущий срок нормален, возраста не нужны.

Конституционная проверка до исследования и после проектирования: сохраняются
metadata-only, RLS/maintenance guard, один READ ONLY RR снимок, пределы O2,
деньги/приватность/удаление и отсутствие egress. Нет новых writers/модели/
миграций/службы/прав/зависимостей. Это проектная оценка, не приёмка реализации.

Порядок: specify/clarify F1–F6 → research/model/quickstart → reviewer-owned
checklists/fair-use-inventory.md и независимый PASS → scoped analyze/прежняя
#4932 → RED → один collector и случаи в существующих
apps/server/tests/unit/test_billing_monitoring.py и
apps/server/tests/integration/test_billing_monitoring_postgres.py → независимое
кодовое review/converge → три exact-SHA/base PR gates. Реальные constraints
и FORCE RLS включить в fixture/fingerprint; защитные ветви отдельно проверить
синтетическим SQL-входом, не ослабляя положительную схему. Все87 task lines,
T077 [ ], полный O6/FR089 и58 старых gaps сохраняются. Legacy Impact untouched;
CLI/guard/cleanup/другие семейства прежние; Full/CD/Dev/выпуска здесь нет.

### T077: сохранённые наблюдения возвратов (01.11.2026)

High-risk-product/active Spec Kit slice исходной T077 после PR7890.
R1–R6 [O11](contracts/operator-observation.md#o11-следующий-срез-сохранённые-наблюдения-возвратов):
одна агрегация существующей ObservedProviderRefund в том же monitoring.py,
CASE по совместной паре status/source, count/group/order в SQL. Generic
_groups не подходит: здесь не нужен возраст, временной столбец не читается.
Форма семейства и maintenance/read-only граница переиспользуются. Чеки
из invoice JSON и CSV/API/ledger сверка не подключаются, их значения null;
coverage всегда partial. Новых схемы/служб/зависимостей/прав/egress нет.

Проверка конституции до исследования и после проектирования: сохранены
metadata-only, RLS/guard/единый снимок, ограниченные запросы/вывод,
финансовые и приватностные границы; новых writers/пользовательского входа
нет. Это вывод проектирования, ещё не независимый допуск или приёмка кода.

Порядок: уточнение R1–R6 → research/model/quickstart → reviewer-owned
checklists/refund-inventory.md и независимый PASS → scoped analyze/прежняя
#4932 → RED → минимальный collector и новые случаи в существующих
apps/server/tests/unit/test_billing_monitoring.py и
apps/server/tests/integration/test_billing_monitoring_postgres.py →
независимое code review/converge → три точных SHA/base GitHub gates.
Все87 исходных полных task lines, T077 [ ], полный O6/FR089 и58старых gaps
сохраняются. Legacy Impact untouched; Full/CD/Dev/выпуска здесь нет.

### T077: реестр бонусных дней (01.11.2026)

High-risk-product/active Spec Kit slice в исходной T077, после PR7887.
Реализовать C1–C6 [O10](contracts/operator-observation.md#o10-следующий-срез-сохраняемый-реестр-бонусных-дней)
одной ограниченной агрегацией существующего TimeCreditLedgerEntry в
apps/server/src/twobrain_rec_server/billing/monitoring.py. Переиспользовать
закрытую SQL-группировку и форму семейства; generic _groups не подходит:
у реестра нет created_at, будущая maturity нормальна. Группировать state,
считать четыре фильтра и MIN maturity только допустимого достигнутого окна.
Не загружать ORM-строки, не суммировать days и не вызывать финансовые helpers.
Семейство addon_and_time_credit всегда partial; add-on/job метрики null.

Проверка конституции до исследования и после проектирования: границы
сохранены — read-only metadata, прежний maintenance/RLS и единый снимок,
ограниченные запросы/вывод, без финансовых/пользовательских изменений,
новых зависимостей/служб/схемы/полномочий. Это решение проектирования,
независимый допуск и приёмка реализации ещё не получены.

Порядок: уточнение C1–C6 → research/model/quickstart → reviewer-owned
checklists/credit-ledger.md и независимый PASS → scoped analyze/существующая
#4932 → RED → минимальный collector и новые случаи в существующих
apps/server/tests/unit/test_billing_monitoring.py и
apps/server/tests/integration/test_billing_monitoring_postgres.py →
независимое кодовое review/converge → три точных SHA/base GitHub gates.
Все87 исходных полных task lines, T077 [ ], полный O6/FR089 и58старых gaps
сохраняются. Legacy Impact untouched; нет Full/CD/Dev/выпуска.

### T077: следующий срез free_projection (01.11.2026)

Требования P1–P6 [O9](contracts/operator-observation.md#o9-следующий-срез-события-free_projection)
выполняются в той же T077; первый read-only CLI принят PR7884.
High-risk-product/active Spec Kit slice. Реализация только в существующем
billing/monitoring.py: отдельная ограниченная SQL-агрегация BillingAuditEvent,
построение двух полуночей через stdlib date/datetime/ZoneInfo и
event_window вместо заглушки free_projection. usage.moscow_window_for
возвращает месяц и здесь не переиспользуется. CLI/guard/снимок/cleanup,
остальные семейства и их current_state остаются действующими.
Новых служб/таблиц/миграций/зависимостей/флагов/egress нет.

Порядок: уточнение P1–P6 → research/model/quickstart → reviewer-owned
checklists/free-projection.md и независимый PASS → scoped analyze и
подтверждение прежней #4932 → RED для нового семейства → минимальный
collector → содержательные unit и реальные PostgreSQL/CLI проверки в
существующих tests/unit/test_billing_monitoring.py и
tests/integration/test_billing_monitoring_postgres.py → независимое
кодовое review/converge → три exact-SHA/base GitHub gates. Полные пути
исходников/тестов имеют существующий префикс apps/server/.

Constitution Check до исследования и после проектирования: PASS по
границам проекта — metadata-only, действующий maintenance/RLS, read-only
снимок, ограниченные запросы/вывод, без изменения финансовых/пользовательских
данных. Независимое принятие требований ещё обязательно. Legacy Impact
следующего среза untouched: новых путей совместимости нет; удаление
непотребляемого снимка относится к уже принятому PR7884 и остаётся историей.
O6/FR089 и исходная T077 [ ] сохраняются. Своих Full/CD/Dev/выпуска нет.

**Language/Version**: Python 3.13; HTML/Jinja, CSS, HTMX 2.0.10 и минимальный
JavaScript; Swift 6 только для существующей macOS route/handoff policy

**Primary Dependencies**: FastAPI, SQLAlchemy/Alembic, Jinja2/HTMX, `httpx`,
Temporal Python SDK, Postal, existing cryptography/Fernet convention; только
уже установленные runtime dependencies

**Storage**: PostgreSQL как коммерческий ledger; существующий MinIO/object
lifecycle как источник exact `meeting-review.m4a` bytes; текущие и legacy
transcription sources учитываются в lifecycle, но не в customer quota;
provider payment-method reference хранится только в versioned encrypted envelope

**Testing**: pytest unit/contract/integration/E2E, disposable PostgreSQL RLS,
YooKassa test shop и синтетические doubles/CSV; Playwright/Chromium через уже
имеющийся dev stack; SwiftPM focused route-policy tests

**Risk / Validation Lane**: `high-risk-feature` — деньги, auth/session,
tenant isolation, secrets, Postgres/MinIO/Temporal, retention/deletion,
external provider, accessibility и reference-fidelity UX

**Release Gate**: `no deploy` для planning slice. Реализация требует feature
quickstart и `infra/scripts/ci-local.sh --fast` перед PR; production требует
full exact-SHA deploy gate, письменные product/unit-economics/finance/
accounting/legal/security/QA approvals и отдельное разрешение пользователя

**Target Platform**: Linux Docker server и современный browser; macOS Apple
Silicon desktop показывает read-only summary и открывает денежные действия во
внешнем browser, не передавая finance data в URL

**Project Type**: существующий FastAPI server-rendered cabinet + native macOS
handoff; YooKassa — единственный launch provider

**Performance Goals**: webhook edge acknowledgement ≤2 s в focused test;
provider GET/reconciliation выполняются вне request path; entitlement/quota
decision использует локальную server projection и не зависит синхронно от
YooKassa

**Constraints**: RUB; `bank_card`; hosted redirect; no PAN/CVC; no entitlement
from return URL/webhook body; одна automatic renewal operation и no grace/no
automatic retry; checkout default-off; local Record/Stop и существующие
read/export/delete не зависят от billing state

**Scale/Scope**: `Free` — 18 000 exact accepted seconds per Moscow calendar
month + 250 MB playback; explicit 7-day cardless Trial — unlimited core + 500
MB; `Личный` — 790 ₽/month or 7 900 ₽/year, unlimited core + 2 GB; ровно один
co-termed total-capacity add-on 5/20/100/500 GB. Add-on prices и checkout
остаются выключены до утверждения COGS/value и обязательных launch gates

**Unresolved Clarifications**: архитектурных нет. Product-market gates
остаются открытыми: primary Russia-first segment/JTBD, проверяемая
value hierarchy, WTP/comprehension для base/storage packaging, full usage-cohort
COGS/gross-margin floor, campaign guardrails и business launch thresholds.
Неутверждённые цены add-on, retention deadline, fiscal/legal wording и
real-shop capabilities также являются fail-closed launch gates.

## Constitution Check

### Pre-research gate

**Status**: PASS.

- Capture-first/visible control: billing не меняет native capture, persistent
  indicator и one-action Stop; storage/payment никогда не блокируют локальную
  запись.
- Data/secret boundary: YooKassa credentials и opaque method остаются на
  server; desktop не получает provider secret/reference; financial routes не
  отправляют content в Langfuse и исключены из Yandex/session replay.
- Deletion truth: logical meeting deletion сразу закрывает доступ и освобождает
  playback quota, а current/legacy primary audio проходит существующий purge;
  finance retention, backups, YooKassa, Langfuse и Temporal описываются
  отдельно без обещания universal erasure.
- Spec-driven delivery: выбран полный high-risk lane; clarify завершён, этот
  planning pass создаёт research, model, contracts и runnable quickstart;
  checklist/tasks/analyze остаются обязательными до implementation.
- UX/reference fidelity: используется текущий GRAF shell/tokens; наблюдаемые
  Krisp UX/UI/IA и функциональные подписи допускают точное воспроизведение
  по FR-081 и конституции §VII. Проверяются независимый код, права на материалы,
  WCAG 2.2 AA, Russian-first localization и явные degraded states.
- Deployment: planning не выполняет deploy и не повышает текущий
  `pilot_blocked` status.

## Architecture And Delivery Sequence

1. **Tenant/account foundation**: расширить существующий personal-workspace
   bootstrap и account routes; profile/preferences/session/device actions
   используют текущие auth, CSRF, membership switch и RLS boundaries.
2. **Commercial ledger**: добавить versioned catalog/gates, trial activation,
   checkout intent, immutable invoice, consent/recurring-authority evidence,
   provider operation/payment/method/receipt observation, workspace
   subscription и append-only entitlement grants.
3. **Quota truth**: проецировать plan в existing quota decision; добавить
   exact source-range ledger для Free, exact normalized-playback
   reservation/projection для storage на основе `TrackArtifact.byte_length`,
   co-termed add-on и transient no-archive lifecycle. Не использовать
   display-only daily aggregates или отдельный object inventory как
   enforcement.
4. **YooKassa boundary**: один прямой `httpx` adapter для payment, zero-amount
   binding, authoritative GET/list и bounded webhook inbox. Refund mutation
   отсутствует; `refund.succeeded`/refund registry — read/reconcile inputs only.
5. **Customer P1**: account/security/preferences, overview/usage/plans,
   checkout/return, method, cancel/resume/cycle/storage, history/receipt и
   static email refund instruction. Desktop получает только summary/handoff.
6. **Growth P2**: promo reservation/redemption, opaque first-touch referral и
   append-only 7/30-day time-credit ledger with maturity/cap/reversal.
7. **Durable operations**: Temporal-backed one-attempt renewal resolution,
   trial/time-credit/notice/account-close timers, transient purge and
   reconciliation. Existing deletion services own primary purge; external
   backoffice owns refund decisions/execution.
8. **Launch gates**: emergency stop for GRAF-originated checkout/binding/charge,
   official payment/refund CSV reconciliation, backup/restore, accessibility,
   clean-room review, test-shop and controlled real-shop canary.

The database is authoritative for GRAF commercial state. A return URL changes
only presentation. A webhook stores a bounded reference; worker performs
authoritative YooKassa read, validates environment/shop/amount/currency/
metadata and applies one monotonic transaction. Unknown operation keeps its
same persisted request/key and blocks pay-again until resolved.

## Validation Plan

- **Static planning checks**: `git diff --check`; no unresolved research marker;
  no product refund-case/form/execution language; no legacy 1/10 GB catalog;
  cross-links and managed AGENTS plan pointer valid.
- **Account/security contracts**: personal workspace idempotency, verified
  trial uniqueness, Owner/Admin/Member matrices, current-role recheck, CSRF,
  session rotation/revocation and same/cross-tenant RLS.
- **Money contracts**: server amount/receipt equality, double click/two tabs,
  permanent internal uniqueness, provider 24-hour key expiry, duplicate/
  out-of-order webhook, authoritative GET, saved=true/false, cancellation
  authority race, one renewal attempt, exact cutoff→Free and late outcome.
- **Storage/usage contracts**: one Moscow Free window bound at reservation,
  unique accepted source ranges, distinct 80%/100% Free thresholds,
  overrun rejection, 250 MB/500 MB/2 GB/5–500 GB exact decimal capacity,
  object-stat mismatch/supersede handling, only active `meeting-review.m4a`
  bytes charged, delete precedence, source-retention gate reopening,
  add-on serialization and no-archive 15-minute/24-hour purge.
- **External refund boundary**: route/schema/source scan proves zero refund
  form/case/status/operator mutation/CLI and zero refund API calls; static
  `mailto:` contains only configured address + safe reference; manual
  merchant-cabinet full/partial refund is observed once through provider/
  registry reconciliation and never rendered as product status.
- **Growth/CX**: promo atomicity/no stacking, referral first touch/maturity/
  7-or-30-day/cap/reversal, notification dedupe, keyboard/screen-reader/200%
  zoom/reduced-motion/JS-off states, Russian copy, reference fidelity,
  independent implementation and third-party asset rights under FR-081.
- **Operations**: stop-all-charges, test/prod isolation, secret rotation,
  webhook/poller/CSV gaps, billing backup/restore, migration rollback,
  disk-full fail-closed and metadata-only evidence scan.
- **Closeout**: [quickstart.md](quickstart.md) then
  `infra/scripts/ci-local.sh --fast`; full lane and `cd-remote.sh --dry-run`
  belong to the separately approved release boundary.

## Project Structure

### Documentation

```text
specs/140-user-account-billing/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
├── checklists/
└── tasks.md
```

### Source Code

```text
apps/server/src/twobrain_rec_server/
├── billing/                       # catalog/lifecycle/entitlement/usage/storage/reconciliation
│   └── yookassa.py                # direct read/pay/bind adapter; no refund mutation
├── cabinet/
│   ├── web_routes/account.py      # account pages over existing auth/session/device services
│   ├── web_routes/billing.py      # server-rendered billing pages and POST actions
│   └── templates/cabinet/         # existing shell/components/fragments
├── api/billing.py                 # bounded YooKassa webhook ingress only
├── db/models/billing.py           # new workspace/identity-scoped entities
├── db/migrations/versions/        # next Alembic migration + RLS policies
├── deletion/                      # reuse: primary purge and truthful lifecycle
└── workflows/                     # durable renewal/reconciliation/timers

apps/macos/RecApp/Sources/Cabinet/ # existing external-browser handoff policy
apps/macos/Shared/Tests/            # focused route-policy regression
apps/server/tests/{unit,contract,integration,e2e}/
infra/{env,docker-compose.yml,scripts/}
docs/runbooks/
```

**Structure Decision**: один cohesive `billing/` package и один account layer
поверх существующего cabinet/auth. Прямой YooKassa adapter достаточен для
единственного provider. Exact storage bytes переиспользуют active normalized
playback/object lifecycle; отдельный storage engine не создаётся. Refund
backoffice намеренно не моделируется в source tree.

## Phase 0 Research Output

Все решения и отклонённые альтернативы зафиксированы в
[research.md](research.md). Неразрешённых исследовательских маркеров нет;
неизвестные
commercial/legal/provider параметры превращены в default-off launch gates.

## Phase 1 Design Output

- [data-model.md](data-model.md)
- [account-ia-ux-ui-cx.md](contracts/account-ia-ux-ui-cx.md)
- [billing-lifecycle.md](contracts/billing-lifecycle.md)
- [entitlement-degradation.md](contracts/entitlement-degradation.md)
- [http-interface.md](contracts/http-interface.md)
- [operations-reconciliation.md](contracts/operations-reconciliation.md)
- [security-privacy-compliance.md](contracts/security-privacy-compliance.md)
- [yookassa-integration.md](contracts/yookassa-integration.md)
- [quickstart.md](quickstart.md)

## Post-Design Constitution Check

**Status**: PASS.

- Customer/account/payment interfaces preserve Owner authority, CSRF,
  workspace/session recheck and deny-by-default RLS.
- Append-only invoice/operation/authority/grant/usage/referral records plus
  uniqueness/locks make money and access recoverable without provider-owned
  subscription state.
- Finite playback quota is adjacent to every unlimited claim; transcription
  WAV remains lifecycle-accounted at zero customer quota; accepted deletion
  overrides recovery retention and enters mandatory purge.
- Refund design has the smallest truthful boundary: a static external-email
  instruction plus read-only provider reconciliation. No product case,
  execution endpoint, operator surface, status/SLA or duplicate authority was
  introduced.
- Capture, deletion/export, analytics/observability, external dependency,
  accessibility, clean-room, deployment and evidence gates are preserved.
- Production remains fail-closed until catalog, storage COGS/retention,
  YooKassa real-shop, fiscal/legal, security/QA and global rollout gates pass.

## Complexity Tracking

Конституционных исключений нет. Намеренно не создаются generic provider layer,
SPA, dunning/grace engine, wallet, stacked add-ons, seats/team billing,
usage-overage и GRAF refund backoffice. Добавлять их можно только отдельной
проверенной feature slice, когда появится подтверждённая потребность.


## T074: сохраняемый отказ продления — 2026-10-31

Полоса: active Spec Kit slice, test-only. Владелец — repository-audit; #4928.
Только существующий `apps/server/tests/integration/test_billing_renewal_planner_postgres.py`:
переиспользовать paid_workspace, maintenance context, настоящий planner/charge
и проверенный offline MockTransport pattern. Новые зависимости, фабрики
платежей, службы, миграции и продуктовые изменения не нужны.

До тестового кода — независимый `checklists/renewal-decline.md` и scoped analyze.
Далее существующий baseline → один последовательный PostgreSQL сценарий
трёх отказов → профильные unit/contract/integration/E2E → independent review
и converge → точные PR checks. При найденном дефекте продукта остановить
его зависимую приёмку и оформить требования отдельно, не ослаблять assertion.
Constitution Check: сохраняются полномочия, scope, согласие, оплаченный доступ,
сохранность истории и запрет реальных запросов; release/Dev/production не входят.

## Историческая T023 — сверка 31.10.2026

Полоса этой сверки: docs-only / mechanical; Legacy Impact: untouched.
Принятые требования F210 FR017/F278 FR006 заменили browser-only billing
часть F140 FR012. Старую совокупную T023 не реализуем повторно: сохраняем
исходный текст и владельца, снимаем неподтверждённую отметку выполнения и
отдельно фиксируем отмену. #4877 можно закрыть только NOT_PLANNED после
принятия этой сверки обычным PR и индивидуального повторного чтения issue.

Действующие account UI/доступность/ошибки остаются в T079/#4936, F210
T017/#5961, F278 T017/#7323/T025/#7332. Account-close, внешний refund,
изоляция и серверная власть над оплатой сохраняются; код, платёжные настройки,
приложение и выпуск не меняются. Возврат к старой отдельной native сводке
и внешнему handoff возможен только после нового решения владельца о пути
оплаты; отмена не доказывает текущий installed-app или финансовый результат.


## T068 / #4922 и T070 / #4926: уведомления о пробном сроке

Режим: действующий срез Spec Kit, повышенный риск (фоновые письма и проверка
владельца). Сначала уточнение и независимое ревью, затем анализ,
сверка #4922 (проверка) и #4926 (рабочие источники), реализация и
проверки. Обе исходные задачи остаются открытыми. Реальные письма, выпуск и развёртывание не входят.

- Источник дат — сохранённая `TrialActivation`. В существующем POST
  `/billing/trial/activate` добавить событие старта в транзакцию активации;
  не создавать письмо для отклонённого POST, повтора или отката.
- Пять минут между запусками уже задаёт штатный процесс обслуживания.
  Добавить ограниченную выборку наступивших событий в его существующую
  операцию с ролью `billing_reconciliation`, не в GET кабинета и не в цикл
  списаний. Собственная транзакция в activity после commit общих работ
  не смешивает блокировки писем с блокировками платежей и хранилища.
  Связать активацию, личное пространство, текущую подписку и активного
  владельца; плательщик либо тот же пользователь, либо не назначен,
  как у части действующих пробных подписок. Срок подписки совпадает с активацией, план всё ещё
  относится к этому пробному сроку; действующая оплата исключает уведомление.
  По окончании использовать штатную проекцию Free, не менять подписку.
- Ключ очереди: ID активации и фаза `started / t72 / t24 / expired`.
  Использовать существующий уникальный ключ очереди; до ограничения выборки
  исключать записи, уже поставленные в очередь, включая подавленные и
  завершённые. Обрабатывать до 100 кандидатов за запуск. Порядок по границе окна и ID. Повторная проверка под штатной
  блокировкой пространства защищает от конкурирующей оплаты и повторов.
  При обработке нескольких пространств блокировки брать по стабильному
  порядку идентификаторов, независимо от приоритета выдачи кандидатов.
- Перед сохранённым захватом отправки проверить то же основание, границу окна,
  подтверждённого получателя и действующую настройку в той же транзакции.
  Использовать штатный выбор текущего подтверждённого адреса только для
  пользователя активации. Потерявшее основание
  письмо подавляется без вызова транспорта. Повторить проверку при каждой
  новой попытке. Сохранить действующие границы захвата;
  неизвестный исход не повторяется; известный временный отказ допускает
  новую попытку в штатном минутном цикле, до пяти попыток всего.
  Состояние проверяется до сохранения захвата: после commit внешняя
  отправка не атомарна с последующими изменениями пользователя.
  Не держать блокировку на время внешней отправки и не менять обработку
  остальных шаблонов.
- Передавать только две проверенные даты события и фиксированный путь
  кабинета. Время показывать в МСК; состояние после момента события
  пользователь проверяет в кабинете. Идентификаторы для внутренней
  уникальности не включаются в письмо. Старую или неполную запись trial
  без проверяемого ID фазы, обеих дат и ожидаемого пути подавить.
- Проверка: сценарий явной активации и повторного POST в
  `test_account_lifecycle.py`; изолированная PostgreSQL с действующим RLS,
  штатным обслуживанием и отправителем в `test_billing_notification_flow.py`;
  проверка текста и полей в `test_billing_notifications.py`. Остальные
  уведомления, ограниченный повтор и защитный захват остаются прежними.

Конституционные ворота: минимум данных, существующая роль и очередь,
нет новой таблицы, внешнего сервиса, полномочий, обработки денег, нового
срока доступа или удаления. Проверки точного SHA и базы обязательны.

## T048: уведомление unknown при cutoff — 01.11.2026

Полоса: active Spec Kit slice, серверная финансовая область; Legacy Impact: untouched.
До кода — независимая проверка `checklists/renewal-unknown.md` и scoped analyze.
В `billing/renewal_charge.py::project_renewal_cutoffs` сохранить существующую
проекцию доступа, блокировку пространства и транзакцию. Перед `_project_free`
использовать сохранённую `paid_through`; после `unknown_pending` проверить снимки
операции и счёта (workspace, operation, payer, paid_through), затем вызвать
существующий `enqueue_billing_notification` с `RENEWAL_UNKNOWN`, стабильным
`renewal:<invoice UUID>:unknown`, безопасным номером и относительным путём.
Не проверять равенство текущего согласия историческому: отменённая отправленная
операция всё ещё требует выяснения исхода, а письмо не разрешает новую отправку.
Сохраняются существующие paid-through, grant, provider state и consent semantics.

Проверки в существующем PostgreSQL planner test: первоначальный RED, сохранение
после commit/новой session; повтор/rollback; sent/processing/unknown; отменённое
согласие; старый период, другой плательщик, отсутствие/несовпадение счёта,
неподходящее пространство и оконченная/неотправленная операция. HTTP запрещён
fixture. Затем профильные billing unit/contract/integration, review/converge,
обязательные три PR проверки точного SHA/основы. Новые зависимости, очереди,
миграции и финансовые изменения не требуются. T048/#4903 остаётся открытой
до остальных producers и полной проверки исходного объёма; #7524 отдельно.
Constitution Check: изоляция, полномочия, сохранность финансовой истории,
отсутствие повторной оплаты и атомарность сохранены; секреты и реальные
письма/платежи/Dev/production в проверку не входят.

Уточнение текста до merge: сохранённое событие может доставляться после позднего
успеха. Заголовок и тело описывают состояние на границе периода в прошлом,
ссылаются на текущий статус в кабинете и не предлагают повторное списание.
Достаточно исправления существующего шаблона и его предметной проверки;
нового фильтра доставки, состояния или службы не требуется.

## T048: итоговый подтверждённый отказ — 01.11.2026

Active Spec Kit slice; Legacy Impact untouched. До кода: уточнение выше,
reviewer-owned checklists/renewal-final-failure.md, scoped analyze и исходная
#4903. Переиспользовать PAYMENT_FAILED, существующую очередь и безопасное
форматирование даты, без новой службы/таблицы/миграции/платежа.

Сначала подтвердить отсутствие notice после трёх реальных синтетических
отказов и cutoff. Общую проверку связей UNKNOWN/итогового отказа держать
в одном узком helper в renewal_charge.py, вызываемом из cutoff и общей
record_renewal_decline для позднего исхода. Сам финансовый guard отзыва
согласия и проекцию доступа не менять; письмо о сохранённом исходе
не является разрешением на новое списание. До cutoff оставить попытку,
после Free — только итоговое письмо.

Проверки: сохраняемая PostgreSQL цепочка трёх отказов→cutoff; неизвестность→
Free→подтверждённый отказ; поздний третий отказ с переходом; отозванное
согласие; сохранение после нового сеанса, повтор, rollback, конкуренция,
отрицательные payer/period/operation/invoice/owner/status связи. Новые
сценарии не обращаются к настоящим провайдерам/почте. Затем профильные
renewal/notification tests, независимые review/converge и три точных PR gate.
Конституционные деньги/изоляция/история/сохранность/секреты сохранены;
полная T048 не принимается. Выпуск/Dev/Full/CD отсутствуют.

Общий helper сохраняет UNKNOWN без восстановленного provider_id; этот guard
применяется только к canceled/canceled. Отдельная регрессия сохранит границу.


## T048: напоминание в первом окне продления — 01.11.2026

Active Spec Kit slice, Legacy Impact untouched. До кода — независимый
checklists/renewal-reminder.md и ограниченный analyze. Использовать
plan_due_renewals после всех действующих проверок и создания первой
operation/invoice. Существующая транзакционная очередь, новый конкретный
вид сообщения в notifications.py; не создавать таблицу, службу или scheduler.
Stable event на workspace/payer/paid_through, без номера попытки/операции.
Тариф/цикл и сумма берутся из принятого снимка, даты — из текущего периода
и первого окна. В payload только minor units, RUB, month/year, даты МСК,
последние4цифры безопасной маски и путь кабинета. Случай отсутствующей маски
показывает «сохранённый способ оплаты», а не provider ID.

RED на настоящем PostgreSQL planner, затем одна минимальная запись в том же
commit. Проверки: first-window commit/rollback/new session/repeat/concurrent;
local retry и следующие окна без дубликата; no consent/method/current scope,
unknown/newer payment; точная историческая копия и allowlist. Финансовое
планирование/отправка не меняются. Предыдущий итоговый отказ хранится в
отдельном коммите; исходная T048/#4903 остаётся владельцем остатка без дублей.


## T048: содержание подтверждений — 01.11.2026

Active Spec Kit slice, financial notification content; Legacy Impact untouched.
До кода — независимый checklists/notification-content.md и scoped analyze.
Меняются только payload существующих производителей: два в entitlements.py,
успешное предоставление storage segments в purchases.py и resume route
cabinet/web_routes/billing.py. notifications.py сохраняет allowlist и renderer;
существующие форматирование/очередь/Postal переиспользуются без новой таблицы,
миграции, зависимости или службы. Общая подготовка полей подтверждения оплаты
не дублирует форматирование в трёх местах. Сумма — invoice, фактический срок —
grant/segments, без объединения отдельных сегментов. Плановый интервал
FR-105 пока не подтверждён во всех снимках счетов и остаётся открытым. Resume использует
потреблённый quote, полную catalog amount без повторного сложения storage и
точный принятый next_attempt_label (дата с UTC offset или закрытая фраза окна).
Старые строки без данных не дополняются из текущей подписки при доставке.

RED → настоящие producer/commit/new-session проверки в существующих
integration тестах → минимальная правка → повтор/rollback/отрицательные
границы/профильные notification и billing tests → независимое ревью и
converge → обязательные три GitHub gates точного SHA/основы. Деньги, права,
согласие и event identity не меняются; Dev/production/почта не затрагиваются.
Constitution Check: изоляция, серверные секреты, история и атомарность
сохранены. T048/T068/#7524 этим срезом не завершаются.


## Срез T068/T070 — события реферального бонуса

Границы состояний и получателя: [контракт уведомлений](contracts/notifications-support.md#реферальный-бонус-постановка-и-доставка). Постановка в очередь выполняется в сохраняющей переход транзакции журнала рефералов. Рабочие входы: maturity/application в `billing/referral_rewards.py` через существующее обслуживание и bounded reversal через штатное подтверждённое событие. Повторное чтение кабинета не порождает письмо. Не добавлять фоновую рассылку по старым записям.

Роль `twobrain_rec_maintenance` с действующим RLS и billing reconciliation уже может создать и прочитать строку очереди: локальная проба показала rollback и ровно одну строку после commit и повтора. Новые права, роль, миграция, внешний вызов и смена транспорта не планируются. В `run_billing_notification_reconciler` повторно проверить право на реферальное письмо при взятии строки на отправку. Сохранить отдельно подтверждённый отказ, сбой до обращения к транспорту и неопределённый результат после обращения. Повтор использует существующий цикл и предел пяти попыток. Для остальных видов писем правила не меняются.

Перед допуском к коду подтвердить в одноразовой PostgreSQL видимость владельца, атрибуции, подтверждённого адреса и настройки именно под контекстом рабочего источника и отправщика. Отдельно проверить отмену между двумя пространствами. Повтор после сбоя проверки должен хранить срок следующей попытки вместе со счётчиком, чтобы перезапуск не сокращал 60 секунд; сам интервал опроса этого не гарантирует. Если действующих границ доступа или полей очереди недостаточно, сначала согласовать узкое изменение плана без обхода RLS.

До кода: независимый [проверочный список требований](checklists/referral-notices.md), сверка spec/plan/tasks/контракта/quickstart и существующих #4922/#4926. После реализации — штатные предметные проверки, независимый review и converge, три обязательные проверки PR на точном коммите и базе. T068/T070 остаются открытыми для остальных семейств уведомлений; #7524 и выпуск имеют отдельные условия.


## T068 / #4922: доставка платёжных уведомлений в изолированной PostgreSQL

Срез существующей задачи T068 (US9, FR-070–072). Фиксируем постоянной
проверкой пять событий: первичная оплата, готовый чек, первое напоминание
о продлении, неизвестный исход на границе оплаченного срока и поздний
подтверждённый отказ. Пробный срок, пороги хранилища, реферальные бонусы,
остальные состояния чека и поздний успех остаются в T068; не закрывать #4922
и не отмечать задачу выполненной. Приёмка реальной почты остаётся в #7524.

В `apps/server/tests/integration/test_billing_notification_flow.py` использовать
существующую фикстуру оплаченного пространства и общий сценарий планирования
продления, без вызова одного теста из другого. Первичная оплата и готовый чек
исходят из обработки синтетического подтверждения. Напоминание возникает
при первом планировании. До конца периода неизвестный исход не создаёт
итогового отказа; на границе без ссылки поставщика создаётся одно
уведомление о неопределённости. Поздний синтетический результат с
подтверждённой ссылкой на исходную операцию даёт одно итоговое уведомление
и не выдаётся за очередную попытку. Отзыв согласия не разрешает новое списание.
Для позднего успеха сохраняется F278 FR-041; этот сценарий здесь не принимается.

Каждое событие имеет собственный идентификатор; рабочий обработчик читает
сохранённую запись в новой сессии под PostgreSQL RLS. Получатель — подтверждённый
плательщик; эти сообщения обязательны при выключенной необязательной почте.
Тест фиксирует один вызов подставного транспорта на событие. До опроса
запись находится в `pending / 0`; при вызове отдельная сессия уже видит
защитный захват `failed / 1 / postal_outcome_unknown`. После ответа
транспорта сохраняется `delivered / 1` без ошибки, с `delivered_at`.
Идентичность и данные события не меняются; повторный запуск не вызывает
транспорт для этих записей. Подставной транспорт и остановка цикла после одного
опроса ограничены тестом; очередь и обработчик настоящие.

Порядок: независимая проверка требований, анализ и сверка #4922, профильный
PostgreSQL runner, проверка полноты, затем PR с `Refs #4922` и обязательными
проверками GitHub на точном SHA и базе. Режим: активный срез Spec Kit.
Конституционные ограничения сохранены: нет изменений runtime, схемы,
доступа, платёжной власти, хранения или удаления; нет внешних запросов,
реальных писем, денег и данных получателей. Выпуск и развёртывание вне среза.

### T068 / #4922: готовность чека после штатного опроса

Режим: активный срез Spec Kit, только проверки. Уточнение по US9, FR-051/055,
FR-070–072 и R1–R6: подтверждённая оплата уже существует, чек ожидает;
72 часа — граница операторской реакции, не отмена оплаты. Свежий проверенный
GET исходного платежа в том же магазине подтверждает готовность чека до
проверки просрочки. Клиент получает обязательное письмо только при готовности;
отмена регистрации, продолжающееся ожидание, недоступный и неполный ответы
не дают письма. Прежние операторские результаты сверки сохраняются.

Перенести один существующий параметризованный сценарий
`test_receipt_poll_checks_provider_before_overdue_and_keeps_payment` из
`apps/server/tests/integration/test_provider_refund_observation.py` в
`apps/server/tests/integration/test_billing_notification_flow.py` (путь T068),
сохранив прежние проверки. Переиспользовать подготовку исходной операции,
подставной GET и изолированную PostgreSQL с реальными миграциями и рабочей
ролью под FORCE RLS. Отправщик читает всю очередь; соседние тесты не должны
влиять на выборку. Очередь создаёт штатный опрос, прямой постановки нет.

После commit отдельная сессия видит одну запись готовности для текущего
подтверждённого плательщика. При отключённой необязательной почте штатный
отправщик сохраняет защитный захват до подставного транспорта. После его
успеха есть ровно один вызов на подтверждённый адрес с безопасной ссылкой на
историю платежей и сохранённый `delivered / 1`; повтор опроса и отправщика
ничего не дублирует. Во всех пяти вариантах оплата остаётся подтверждённой.

Новых контрактов, модели данных, прав, денежных действий, внешних запросов
или поведения продукта нет. Независимый [чеклист требований](checklists/late-receipt-delivery.md)
и анализ предшествуют коду. Проверяются изменённые наборы PostgreSQL и
три обязательных проверки GitHub на точном SHA и базе. #4922 остаётся открытой:
другие источники и состояния чеков, 80/95/100 и поздний успех оплаты отдельно.
Подставной транспорт не заменяет фактическое получение #7524. Выпуск отдельно.

## T075/T077: подтверждение и сроки регистрации чека — 10.11.2026

**Профиль:** high-risk-product, действующий F140/US10. База — существующие
PostgreSQL, Temporal reconciliation и авторитетные методы YooKassa. До
исходников: уточнение R1–R6 → требования, модель и сценарии → независимое
ревью `checklists/receipt-escalation.md` → scoped analyze → сверка T075/T077
с существующими issues. Новых задач в GitHub и финансовых зависимостей нет.

**Проверка конституции до и после проектирования.** VI: отдельный допуск и
проверки PostgreSQL/FORCE RLS. III/IV: только технические поля, текущий срок
хранения и права счёта, без содержимого чека/встречи и без нового места
хранения частных данных. Внешнее чтение использует действующий серверный
GET с прежними секретами и границами. Отказ не меняет доступ или деньги.

1. Свести четыре существующие точки записи (первичная оплата в
   `billing/entitlements.py`, остальные покупки и опрос в
   `billing/webhook_reconciliation.py`, отдельное чтение в
   `billing/reconciliation.py`) к общим правилам времени и основания.
   Сохранить текущий внешний статус и логический ключ клиентского письма.
   Для отдельного GET чека закрепить проверенный ID уникальным ключом
   PostgreSQL после проверки локального перехода и до записи карты.
   Только точная роль сверки может читать и добавлять связи при FORCE RLS;
   повторный bootstrap восстанавливает минимальные права. Миграция читает
   все счета под ролью миграции, блокирует запись счетов до окончания
   заполнения, переносит однозначные структурные связи и прекращается целиком
   при неоднозначной или повреждённой записи. Перенос не доказывает магазин
   исторического платежа и не разрешает GET. Обновлять только после остановки
   старых обработчиков: штатный CD останавливает API, processing и maintenance
   до миграции. При разрешённом CD `alembic downgrade` удаляет только
   таблицу связей; карты сохраняются и повторное обновление сверяет их заново.
   Если новая схема сохранена, совместимое исполнение использует новый
   обработчик. Старый обработчик, который пишет только в карту, с этой
   схемой несовместим; при отсутствии совместимого исполнения нужен
   исправляющий выпуск.
2. В существующем пятиминутном maintenance workflow обработать до 10
   чеков, общий бюджет прохода 60с, одна попытка GET до 5с без повтора внутри
   прохода. Старые и новые чеки оплаты/возврата в общей очереди: сначала без
   попыток, затем по возрастанию времени попытки, при равенстве — по
   неизменной паре «счёт, локальный ключ чека». Попытка резервируется под
   блокировкой и сохраняется до запроса; следующий захват не ранее чем
   через 300с, в том числе после сбоя GET или отката применения ответа.
   При конечной очереди каждый пригодный чек получает слот при исправных
   БД и планировщике; превышение бюджета показывает неполноту.
3. Не держать блокировки между транзакциями. Под второй блокировкой
   повторно сверить статус, workspace, родителя, магазин и reservation,
   выполнить ограниченный GET и применить ответ только к прежней привязке.
   Для известного ID использовать GET чека, иначе для чека оплаты GET
   платежа. При отказе состояние не меняется; сохраняется закрытый класс
   отказа. Просрочка допустима по последнему подтверждению с отметкой
   свежести. При откате часов показать неполноту, не обрабатывать запись.
   Опрос чека не использует ветви применения оплаты или её таймеры.
   Источники выборки — верхнее поле оплаты или проверяемая карта
   известного возврата; терминальные, неготовые по интервалу и заведомо
   непригодные записи не занимают лимит GET. Повторная потеря связи
   освобождает место без запроса. Перед сетевой попыткой на границе срока
   стараться получить свежий факт; терминальный ответ этого GET применяется
   раньше проверки порога. Если запрос недоступен или пропущен из-за
   предела, оценивать только сохранённый факт, когда очередь дошла до
   записи; фиксировать отдельно нормативный срок и время обнаружения.
   Некорректные контейнеры не приводить к object, не читать как пустые и
   не переписывать. Сохранять закрытый результат отказа без payload.
   Глобальный проход выполняется только под существующей точной
   maintenance-ролью billing reconciliation с FORCE RLS. Из уже
   авторизованного tenant/Owner refresh применим только его прежний счёт
   и его подтверждённый GET; глобальная выборка недоступна. Не менять grants,
   политики RLS, сериализаторы, публичные маршруты или прочий отчёт O13.

4. Первая версия ограничена сохранением фактов и оснований в существующем
   счёте, включая дедупликацию и переходы. После неё отдельно спроектировать
   надёжную передачу ограниченных оснований в существующий независимый
   журнал O16 с восстановлением и обработкой пропусков. Не добавлять почтовый
   POST в платёжную транзакцию и не менять независимость наблюдателя от БД.
5. После допуска: целевые PostgreSQL-тесты, независимое ревью реализации и
   converge; три обязательных проверки на точном SHA и основе PR. Test-shop,
   выпуск, приёмка Postal/получателя и закрытие исходных задач отдельно.

## T077: передача оснований чеков в O16 — high-risk-product

**Конституция III/IV/VI до и после проектирования:** новый источник хранит
только категориальные числа без связи с человеком или счётом. Удаление и
жизненный цикл исходных данных не меняются; наблюдатель, маршруты, секреты
и полномочия принятия риска сохраняются. Существующие R1–R6 и O16/J5/J6
разрешают направление; ROC1–ROC4 уточняют реализацию без смены канала.

1. Следующей свободной миграцией добавить append-only технический источник
   приростов; в одной транзакции защитить снимки invoice от параллельной
   записи на время начального переноса и подключить запись новых приростов.
   Обычная транзакция хранит снимок и прирост вместе; откат не оставляет
   строки. Сбой записи означает обычный повтор сверки, без новой платёжной
   мутации и без отъёма уже подтверждённого доступа. Никаких сетевых
   действий из PostgreSQL. Закрытый контракт — в модели; матрица F031 и
   bootstrap отражают только новые разрешения.

2. Расширить точечный probe и валидацию fixed launcher до v2 в прежнем
   RR/READ ONLY снимке. Статус peer и запись activation остаются v1. В
   контроллере принимать историю v1, добавлять v2 без переписывания журнала
   и обнаруживать downgrade после первого v2. Старый маршрут источника и
   параметры SSH не расширять; первая установка обоих закреплённых образов
   и миграции — отдельный выпуск. При откате сохранять анонимный журнал,
   доказательства и совместимый reader; старый reader после v2 не подходит.
3. Существующий первичный O16 принимает три отдельных вида в прежнюю
   очередь, соблюдая A3–A6. Свидетель не получает права создавать
   фискальные incidents. Bootstrap, смена поколения, паузы, accepted и
   owner relay используют уже принятый порядок. При пропуске чтения ждать
   следующего здорового снимка, а не снимать неполноту.
4. До кода: независимое ревью чеклиста, scoped analyze и сверка T077/#4932
   без дубля. После — целевые PostgreSQL/RLS, подставной Postal и replay,
   миграционная/роль/инфраструктурная проверка, независимое ревью и
   exact-SHA PR-проверки. Выпуск, test-shop и фактическая приёмка отдельно.


Порядок установки совместимых образов: сначала миграция с сохранением
старого source v1; затем новый primary launcher/controller, который
понимает v1 и v2, при старом witness/source. Сверить v1 чтение и прежний
peer status. Затем новый witness/source с совместимым launcher и v2
probe. Сверить первый durable v2 в primary; status peer остаётся v1.
Обратная пара (старый primary, новый witness/source v2) запрещена.
До первого durable v2 возможен откат witness/source раньше primary
после подтверждения v1 чтения и head. После принятого v2 держать
совместимый primary и v2 source, даже если бизнес-приложение требует
отката. При недоступности совместимой пары сохранять журнал и recovery
hold; не обещать приёмку по status v1. Наличие accepted v2 проверяется
по цепочке, а не по обычному полю source_check.

### T048/T068 — позднее начало оплаченного периода

Доработка двух существующих задач: производитель подтверждения находится в
`billing/entitlements.py:grant_confirmed_renewal`, вызывается штатным
согласованием и рабочим обработчиком подтверждения; точка вывода —
`billing/notifications.py`. Проверка границы выполняется до изменения
подписки под существующей блокировкой; признак добавляется только на
успешном пути с фактическим grant. Повтор использует прежний ключ события
и не создаёт новое письмо. Не менять финансовые правила, получателя,
доступ и восстановление полномочий; без миграции, нового сервиса, правки
рабочего отправщика или перезаписи старой очереди.

Постоянная сквозная проверка в
`apps/server/tests/integration/test_billing_notification_flow.py` использует
изолированную роль RLS и подставные платёжный и почтовый транспорты.
Узкий чеклист требований и analyze — до кода; после изменения — converge,
предметный PostgreSQL и обязательные проверки точного PR. Исходные T048 и
T068 остаются открытыми, без новых issues. Реальная доставка, выпуск и
развёртывание имеют отдельные ворота.


## T070/T068 — наблюдение порогов архива, 10.11.2026

**Полоса:** high-risk-product, существующий F140/US9, S1–S9 в Clarifications.
Constitution Check до исследования и после проекта: III — только технические
байты и служебные ключи в существующей PostgreSQL; IV — явная очистка при
финализации плюс FK cascade при физическом удалении; VI — независимый
checklist/analyze до кода. Нет изменения коммерческих прав, денег, согласия,
хранения встреч, capture, внешнего маршрута или принципов конституции.

### Источники и минимальный состав

`billing/storage.py:project_active_playback_storage` и общий
`billing/catalog.py:classify_storage_threshold` определяют занятое и уровень.
Вместимость: Free без подписки — FREE_STORAGE_BYTES; действующие Trial/Personal
по effective_plan_code/effective_paid_storage и тому же as_of, как /billing/usage
и _reserve_playback_storage. Перенести совпадающую проекцию capacity в общий
непубличный helper только если это необходимо для одного правила; все callers
и отрицательные состояния сохранить. Не выбирать capacity из одного cache.

`billing/storage_notifications.py` содержит наблюдение, eligibility и claim
проверку; новая миграция от фактического Alembic head, модели/exports, bootstrap
и RLS inventory. Две небольшие таблицы: состояние по workspace и один курсор
полного обхода (точная модель ниже). Не создавать инвентарь объектов, службу,
новый workflow, настройку либо транспорт. Места вызова: отдельный storage шаг
в _run_billing_reconciliation_activity после предыдущего commit; существующий
run_billing_notification_reconciler; существующий account_closure finalizer.

### Конечный обход и транзакции

Курсор хранит cycle_started_at, upper_workspace_id и after_workspace_id,
агрегаты attempted/observed/skipped/failed и ограниченный last_error_code.
При завершении last_finished_summary сохраняет начало/конец, эти четыре
счётчика и признак неполноты; новый цикл не стирает последний результат.
Attempted не означает успешное наблюдение, проход не является общим MVCC-снимком.
При начале цикла зафиксировать серверный UTC момент и наибольший UUID
личного пространства с created_at <= cycle_started_at. Дальше выбирать
личные пространства с этим ограничением времени и
`after < id <= upper`, по UUID. Новые пространства с датой позже начала
входят в следующий цикл; поздно закоммиченная более старая строка позади
курсора также входит в следующий цикл. После конца диапазона сбросить цикл
и закончить текущий вызов, без нового наблюдения в этом же вызове.

Один вызов: до 100 разных кандидатов и общий бюджет 60 секунд; запросу
не более 2 секунд, ожиданию блокировки не более 1 секунды, отмена сохраняется.
При неизменном конечном наборе N, исправной работе и полном исполнении
партий весь набор обходится за не более ceil(N/100)+1 вызовов; +1 учитывает
завершение диапазона. Это предел вызовов, не обещание календарного времени.
Превышение бюджета/ошибка означает неполноту; фактические завершённые партии
и время измеряются. Пять минут — существующее расписание запуска.
Поздние commit, вошедшие впереди курсора, учитываются отдельно как L:
предел относится к N+L; новые обычные вставки не оттесняют начальную когорту.
При бесконечной задержке БД/планировщика срок не обещается.

Каждый кандидат — отдельная транзакция: lock курсора → штатная advisory
блокировка workspace → Workspace row lock → subscription/state →
вычисление/очередь → cursor advance → commit. Свежий as_of брать после
ожидания блокировок, не из начала длинной партии. Нет обратного запроса курсора из publication/sender/finalizer.
Блокировка курсора сериализует конкурентные проходы; не держать её между
кандидатами или во время сети. После получения lock повторно сверять cursor.
Cursor lock брать до savepoint. Ошибку кандидата откатить savepoint:
прежние owner/band/generation/observed_at и очередь не меняются; записать
только агрегаты/закрытый error class и продвинуть cursor в той же внешней
транзакции. Не писать даже ошибку в workspace-state после rollback savepoint:
его Workspace lock мог быть снят и finalizer мог уже удалить state. Следующий цикл повторяет кандидата. Ошибка всей
БД/commit откатывает всю транзакцию и не объявляет продвижение; повтор
безопасен по состоянию и unique
outbox. Начальные неизвестные/несогласованные даты — incomplete, не normal.

### Получатель, отправщик и удаление

Один helper проверяет S4 при observation и claim. Активная исходная личность,
owner marker, membership и billing_owner должны согласоваться; нужен текущий
verified email и preference. При действительном отсутствии обновить band,
не ставить письмо; при ошибке не поглощать подъём. Если owner изменился,
первое наблюдение нового owner отдельно, sequence не сбрасывать.

Sender включает storage в выборку даже без verified email, чтобы terminal
suppressed не выпадал навсегда. Для storage сначала workspace advisory lock,
Workspace row lock, потом queue row lock, затем новая проверка
eligibility/preference/address
в этой транзакции и прежний durable unknown claim до транспорта. Изменение
права после сохранённого claim не превращает его в гарантию отзыва уже
отправленного письма. Старые payload без достаточного исторического снимка
подавляются закрытой причиной, не дополняются текущим состоянием.

Перечитанный begin_account_close_finalization уже закрывает identity до fanout;
finalize_account_close оставляет Workspace физически. Поэтому явное удаление
storage state по frozen content_workspace_ids сделать в существующем
begin_account_close_finalization, в одном commit с identity=closed до fanout; FK CASCADE — дополнительная защита фактического удаления, не замена.
Observer создаёт/меняет state только под Workspace row lock после повторной
проверки active/unmerged owner; для закрытого/объединённого владельца state
не создаётся. Не брать closure request после Workspace: begin-finalization
берёт request раньше Workspace; повтор с frozen scope уже видит identity=closed.
Подавление старой очереди сохраняет её существующую политику жизненного цикла.

Retry storage guard использует прежние правила referral: сохраняемые attempts
и deadline не менее 60 секунд, максимум пять попыток. Known retryable Postal
rejection повторяется в этих границах, unknown автоматически не повторяется.
Не менять остальные виды уведомлений или держать блокировки через HTTP.

### Права, совместимость и ворота

Новые таблицы ENABLE/FORCE RLS. Только точная session_user=current_user
maintenance без superuser/BYPASSRLS, row_security=on и allowlisted context.
State: billing_reconciliation/billing SELECT/INSERT/UPDATE; SELECT/DELETE для
существующей account-close billing_reconciliation/account, без чтения/записи
другими request/worker/media contexts. Курсор — system-owned, только billing
reconciliation SELECT/INSERT/UPDATE. PUBLIC/app/media отозвать; повторный
bootstrap не восстанавливает широкие grants. `rec_maintenance_allowed` не
расширять глобально; использовать require_billing_maintenance_database,
не normalization-specific require_database_context. F031 policy matrix,
RLS_BILLING_TABLES и RLS_COVERED_TABLES отразить явно.

Миграция не создаёт исторические письма или снимки: первое наблюдение после
установки следует S2. Непустые state/cursor блокируют downgrade, чтобы откат
не сбросил дедупликацию и не повторил первое высокое письмо. При откате нужен
совместимый reader с сохранением состояния; исправление вперёд вместо удаления
истории. Нового legacy path нет, Legacy Impact — untouched.

До исходников: независимый checklists/storage-notices.md, scoped analyze и
сверка существующих #4926/#4922; затем RED/миграция/RLS/рабочая publication
и sender, независимое code review/converge, предметный PostgreSQL и три
обязательных проверки точного SHA/актуальной основы. Полные T070/T068 и #7524
не завершаются. Выпуск, сервер, реальная почта и Dev отдельно.

## T070/T068: операторский источник fair-use — 11.11.2026

Проект FU1–FU8, high-risk-product. Применить существующий F140, не создавать
дубликат фичи или задачи. Scope — внутренний ввод уже проверенного человеком
основания, атомарные review/audit/outbox, апелляция и сохраняемое решение,
проверяемая единственная подставная отправка. Полный enforcement и реальная
операционная реакция≤24ч остаются в исходной T070. Рабочий договор:
[fair-use-operator](contracts/fair-use-operator.md).

### Constitution Check до и после проекта

I/II: нет изменения capture/Record/Stop; III: нет нового внешнего направления,
только непрозрачные ссылки и закрытые метаданные; IV: нет хранения материалов
основания, сроков удаления или обхода закрытия аккаунта; VI: до кода нужны
независимый checklist, tasks, Analyze и существующие issues, затем реальная
PostgreSQL/RLS, code review/Converge и три PR gate точного SHA/основы.
Новая операторская обработка не является выпуском/продакшеном и не вводит
новое платное ограничение. Legacy Impact: untouched; старые строки не получают
выдуманную историю или массовую повторную рассылку. Принципы не меняются.

### Phase 0 и неизвестные до реализации

Повторно использовать `cli/billing_registry.py` и identity gate
`billing/database.py`, существующие FairUseReviewRecord.resolved_at/
resolution_code, BillingAuditEvent и outbox. Поля решения уже есть, но
исследование текущих RLS/grants опровергло гипотезу отсутствия миграции:
0074 разрешает app DML своей/lineage строки,0044 и bootstrap не защищают
audit от переписывания. До допуска требуется узкая миграция, SQL guard
переходов/защищённого audit и сохранение прав при повторном bootstrap.
Операторский ввод — ручной классифицированный источник, не выдуманный
автоматический детектор объёма. Независимое исследование обязано проверить
достаточность существующих ролей, порядок блокировок, реальные потребители
state, права кабинета/lineage и источник истины получателя. Найденные
зависимости должны попасть в договор и Quickstart до допуска к коду.
Отчёт Phase0 от11.11 — `f140-t070-fair-use-operator-research-20261111.md`
во внешнем каталоге доказательств; это исследование, не reviewer PASS.
Дополнительный Phase0 `f140-t070-fair-use-db-design-20261111.md` выбирает
существующие таблицы, INVOKER guards перехода/namespace и автоматический
DEFINER audit writer минимальной NOLOGIN роли по принципу0111. Root проверяет
оригиналы и принимает технический выбор отдельно от checklist/реализации.
Контракт содержит полные ACL/role/trigger/legacy/cleanup границы. Phase1
подготовлен ниже; checklist/tasks/analyze/допуск ещё не завершены.

Существенный уже найденный эффект: account_merge передаёт
include_confirmed=False. restricted/appealed блокируют merge,
notice/cleared/confirmed — нет. Новое создание и решение делают эту
существующую ветку достижимой из реального источника; не называть весь срез
инертным и не исправлять merge policy без отдельного согласованного проекта.

### Phase 1: минимальные стыки

1. В новом `cli/billing_fair_use.py` защищённые create/resolve и READ ONLY
   dry-run по умолчанию; закрытые ошибки, без значений аргументов/секретов.
2. В `billing/fair_use.py` общий атомарный путь, неизменный первый срок,
   idempotent/конфликт решения и уведомление первой апелляции. Workspace
   lock → review lock → audit/outbox; повтор и откат покрыть до исправления.
3. В `billing/events.py` и `notifications.py` прежняя family плюс закрытая
   phase, стабильная identity по исходному review/переходу, безопасная copy.
   Никакого прямого enqueue в положительном причинном тесте.
4. В `workflows/worker.py` источник/первоначальный адресат проверяются при
   захвате по существующему шаблону; обязательная почта не зависит от marketing.
   Unknown после POST не повторяется. Ошибку чтения не смешивать с утратой права.
5. `cabinet/web_routes/fair_use.py` сохраняет текущие CSRF/lineage и commit;
   положительный тест проходит настоящий маршрут, а не вызывает helper вместо
   пользовательского действия. Изначальная строка возникает через CLI.
6. Следующая свободная миграция в `db/migrations/versions/` защищает
   create/resolve от прямого app SQL и историю новых audit, сохраняя
   допустимую апелляцию и lineage чтение. Стыки: `db/rls_validation.py`,
   `apps/server/scripts/bootstrap_runtime_database_roles.py`, профильные
   migration/role fixtures и tests. Существующих review/audit полей достаточно;
   новую таблицу/сервис/обход RLS не добавлять. Роль
   `twobrain_rec_fair_use_audit_writer` NOLOGIN/NOINHERIT/NOBYPASSRLS только
   вставляет audit через установленный AFTER DEFINER trigger. BEFORE INVOKER
   guard review проверяет реальные роли и разрешённые переходы; BEFORE
   INVOKER audit guard запрещает прямой reserved INSERT app/maintenance и
   UPDATE/DELETE по OLD ИЛИ NEW namespace. Canonical audit больше не вставляет
   Python. fixed search_path/qualified refs/row_security, REVOKE EXECUTE и
   ENABLE ALWAYS; никаких runtime role memberships/SET parameter обходов.
   Разделить SELECT/INSERT/UPDATE review policies, удалить старый FOR ALL.
   UPDATE USING обязан сохранить validated account_merge row-lock ветку:
   F178 SELECT FOR UPDATE применяет UPDATE policy. WITH CHECK/guard не дают
   этой ветке фактический UPDATE. Общий rec_maintenance_allowed недостаточен
   для operator authority. Проверить повтор bootstrap,
   старые строки и блокирующий destructive downgrade без backfill/рассылки.
7. `cabinet/templates/cabinet/pages/fair_use_content.html` и route projection
   должны различать review/appeal/result и исторический срок. Старое confirmed
   не объявляется снятым ограничением; новый confirmed не доказывает
   применение санкции. Сохранить keyboard/CSRF/status announcements, safe
   support action и прежнюю структуру страницы, без новых assets/редизайна.
8. В `cleanup_smoke_artifacts.py` проверить реальную maintenance identity и
   прежний cleanup context; после Workspace root lock, ДО любого DML/Minio,
   preflight exact synthetic scope на любые review/зарезервированный audit.
   Наличие/ошибка чтения → safe protected_fair_use_history,0 изменений.
   Удалить выполнение DELETE fair_use_reviews, даже при пустой таблице,
   поскольку право DELETE отозвано. Обычный smoke без истории чистится как
   прежде; с историей безопасно отказывает. Не давать исключения по cleanup
   GUC или depth. Проверить race preflight/source insert; account-close
   retained metadata остаются, физического DELETE/bypass не добавлять.
9. Дополнить профильные роли/миграционные fixtures, tests
   `test_fair_use.py`, `test_fair_use_ui.py`, billing notification flow,
   настоящий CLI/roleSQL и account-merge/cleanup tests. Существующие callers
   `persist_review` и direct FairUseReviewRecord fixtures переводятся на
   новую настоящую разрешённую роль либо trusted setup только для старой
   истории; нельзя вернуть широкие app grants ради прежнего теста.
   Доказать триггер при REVOKE EXECUTE, прямой audit spoof app/maintenance,
   UPDATE laundering, rollback при audit error и repeat bootstrap на PG17.

Workspace → review → audit/outbox остаётся локальным порядком. При пересечении
с UserIdentity/membership/account merge не добавлять обратное ожидание:
использовать NOWAIT и полный rollback/bounded retry, сохранять проверку
актуальности до commit/claim. Sender для fair-use должен выбирать и строки
без текущего адреса, различать terminal suppression и временную ошибку;
retry≤5/≥60сек учитывается в selector и под lock. Это не распространение
новой политики на остальные семейства.

Профильный RED от входа → минимальная реализация → PostgreSQL с настоящими
ограниченными LOGIN/FORCE RLS и отдельным соединением после commit → code
review/Converge/fragment → точный commit/push/PR и проверки. Tasks87 строк,
T068/T070 `[ ]`, #7524 и остальные gaps сохраняются. Допуск пока не выдан.
