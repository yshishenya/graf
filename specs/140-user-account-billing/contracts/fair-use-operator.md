# T070/T068: операторский вход fair-use

Проект от 11.11.2026. Источник требований: FR-107, FR-070–072,
FU1–FU8 `../spec.md`. Это рабочее рассмотрение основания вне GRAF,
а не автоматический классификатор или право вводить скрытую квоту.
До независимого checklist/Analyze реализация не допускается.

## Вход и полномочия

Использовать существующий внутренний CLI образец `cli/billing_registry.py`,
`require_billing_maintenance_database` и утверждённый контекст
`billing_reconciliation` / `billing`. Реальные session_user/current_user
должны быть `twobrain_rec_maintenance`, row_security=on, без superuser,
BYPASSRLS и подмены через SET ROLE. Пользовательские имена в аргументах
не заменяют этот контроль. Предполагается существующее закрытое хранение
учётных данных обслуживания; новый сервер, секрет или публичный API не нужен.
Личность человека устанавливает существующий операционный процесс доступа;
operator-ref должен ссылаться на его закрытый журнал. Shared login доказывает
роль службы, а строка operator-ref/флаг подтверждения — только её заявление.
Эта организационная предпосылка не принимается синтетическим тестом.

Команда `python -m twobrain_rec_server.cli.billing_fair_use`:

- `create`: workspace UUID, subject UUID, capability из
  `server_processing|storage`, один из четырёх существующих reason,
  непрозрачный evidence-ref, ограниченный operator-ref и явное
  подтверждение, что оператор изучил внешнее основание. Сам объём/IP/device
  или единичная аномалия не достаточны; эти данные команда не принимает.
- `resolve`: workspace UUID и тот же evidence-ref, decision `cleared|confirmed`,
  закрытый код решения, operator-ref и такое же подтверждение рассмотрения.
  Для cleared: `not_substantiated|no_longer_applicable`; для confirmed:
  `basis_confirmed`. Свободный текст и новое основание через resolve запрещены.
- По умолчанию — транзакция READ ONLY и проверка намерения. `--execute`
  сохраняет ровно одно действие. Время первого принятия и решения задаёт
  сервер; аргумента для заднего числа нет. Ошибка разбора/БД возвращает
  закрытый result_code, без echo аргументов, SQL, адреса БД или traceback.
- В выводе только результат, признак dry_run и обезличенный статус.
  Workspace/subject/evidence/operator, адреса и полные строки БД не выводятся.
  Существующие UUID передаются только внутреннему операторскому входу;
  они не попадают в письмо или долговечные открытые доказательства.

Это способ передать уже проверенное человеком основание. Флаг подтверждения
не доказывает правоту человека и не является автоматическим анализом
доказательств. Операционная приёмка должна отдельно подтвердить полномочия
и рассмотрение в пределах 24 часов; тестовый оператор этого не подтверждает.

## Сохранение и конкуренция

Блокировка workspace предшествует review, затем audit/outbox. Существующие
проверки связи активного субъекта с пространством выполняются до создания.
При проверке identity/membership после захвата workspace использовать
неблокирующие чтения с нужной row lock либо NOWAIT с откатом и безопасным
повтором: account merge блокирует UserIdentity → membership → Workspace,
а закрытие аккаунта уже использует Workspace раньше identity. Нового
обратного ожидания и изменения чужого порядка блокировок не вводить.
Завершённый/финализирующийся аккаунт и чужая область отклоняются. Новый
review использует существующие `create_review` и `persist_review`; атомарно
сохраняются notice, `starts_at`, `review_by=starts_at+24h`, audit и очередь.
Ключ workspace/evidence_ref уже уникален. Совпавший повтор сохраняет исходные
даты; изменение subject/capability/reason отклоняется. Повтор после решения
не возвращает notice и не создаёт прежнее письмо заново.

Resolve блокирует точную строку по уникальному workspace/evidence_ref.
Оператор использует собственную исходную ссылку, поэтому ему не требуется
чтение таблицы напрямую или вывод частных идентификаторов. Сохраняются state,
resolved_at, resolution_code и append-only `BillingAuditEvent` с закрытым
action, исходным/новым состоянием и ограниченным operator-ref; target_ref
не содержит исходное доказательство. Совпавший повтор — без новой записи,
даты и письма; иной результат/код после окончательного решения — конфликт.
Решение не меняет starts_at/review_by/appealed_at. Неконечные/противоречивые
исторические даты не исправляются угадыванием; операция отклоняется.

Существующий CSRF/lineage путь апелляции сохраняется. Только первый переход
сохраняет appealed_at/appeal_ref и отдельное событие; повтор после решения
ничего не меняет. Ошибка queue/audit откатывает переход, ошибка commit
не создаёт успешный результат. Отдельное соединение после commit должно
увидеть все части; после rollback — ни одной части нового действия.

## Письмо и исходный адресат

Использовать прежний обязательный вид `fair_use.review` и шаблон с закрытой
фазой `notice|appealed|cleared|confirmed`; разные фазы имеют разные стабильные
event keys, привязанные к review. В письмо допускаются только phase,
capability, reason, исторический срок в МСК и фиксированное действие
`/account/fair-use`. Непрозрачная ссылка на основание никогда не отображается.
Первое письмо говорит о принятой проверке, апелляция — о принятой апелляции,
решение — о сохранённом результате и необходимости смотреть действующее
состояние в кабинете. Нельзя обещать фактическое ограничение/разблокировку,
успех почты или исполнение решения оператором.

Очередь хранит отдельно служебную связь с review и фазой. Первоначальный
subject и отличный от него действующий owner получают отдельные строки;
повтор не добавляет нового адресата к прежнему событию. Перед claim под
установленным порядком блокировок повторно проверяются источник, исходный
получатель, активная личность, действующее право читать эту проверку и
подтверждённый действующий адрес. Не следовать объединению аккаунта и не
перенаправлять старую очередь новому owner. Отсутствие права/источника/адреса
даёт suppressed; ошибка чтения — прежний сохраняемый ограниченный retry.
Неподтверждённая старая очередь без связи с источником не получает
выдуманную связь и не отправляется как новое подтверждённое событие.

Marketing preference не отключает эти обязательные сообщения. Использовать
существующий долговечный claim до сетевой отправки. Неизвестный исход не
повторяется; известный повторяемый отказ сохраняет прежние пределы попыток
и задержку. Полный материал основания, контакты и тексты писем не попадают
в CLI/audit/диагностику. Реальный Postal не используется при разработке.

## Существующие эффекты и граница

Новый вход не принимает urgent, не добавляет capability enforcement и
не меняет коммерческую квоту/срок/record/read/export/delete. Но проверка
не полностью инертна: account_merge использует
`fair_use_restricted_for_lineage(include_confirmed=False)`, поэтому
restricted/appealed блокируют объединение, notice/cleared/confirmed — нет.
Нужна регрессия этой существующей зависимости, а не её удаление ради теста.

## Защита истории на уровне PostgreSQL

Исследование0074/0044/bootstrap опровергло исходную гипотезу «миграция не
нужна»: FOR ALL policy и общие DML grants не защищают операторское решение
или audit от прямой записи app-роли. Одного guard Python недостаточно для
FR-078/079. Использовать существующие таблицы review/audit/outbox, но добавить
узкую миграцию от фактического Alembic head, SQL-защиту переходов/истории и
сохранение минимальных прав при bootstrap. Новая таблица, роль с BYPASSRLS,
публичный API или новый сервис для этого не требуются.

Обязательные свойства миграции:

- SELECT сохраняет существующую изоляцию subject/Owner/lineage. INSERT нового
  notice и окончательное решение доступны только фактической maintenance
  identity с точными billing operation/feature, row_security=on и без
  superuser/BYPASSRLS; app/media/SET ROLE не становятся оператором.
- UPDATE для app ограничен первой апелляцией допустимого субъекта/lineage.
  Исходные поля, первый срок/апелляция и окончательное решение неизменны;
  actor нельзя подменить аргументом или GUC вместо проверки роли БД.
- Новое семейство audit `fair_use.review.created|appealed|resolved`
  связано с внутренним review и видом перехода, имеет уникальный ключ
  workspace/review/действие, закрытые metadata и серверное время. INSERT
  выполняет только установленный автоматический writer после фактического
  перехода; app и maintenance не вставляют такой audit напрямую. UPDATE/DELETE,
  включая смену action/target из защищённого семейства и обратную подмену
  обычного события на защищённое, запрещены. Защита остальных audit families
  этим не принимается.
- Bootstrap повторно снимает лишние table/column grants, не отключает
  триггеры/RLS и проверяет реальные роли. Runtime не владеет таблицей/функцией,
  не имеет TRIGGER/TRUNCATE, не может отключить защиту или повысить роль.
- Существующие строки сохраняются без изменения классификации/основания,
  поддельного create audit, первой даты или рассылки. Миграция не объявляет
  старые final строки рассмотренными новым входом. Противоречие защищённой
  истории останавливает миграцию/операцию атомарно, без угадывания.
- `cleanup_smoke_artifacts.py` после проверки настоящей maintenance identity,
  точного cleanup context и прежней блокировки корня synthetic workspace
  проверяет любые fair-use review и защищённый audit ДО любого DML/удаления
  объектов. Наличие истории или ошибка чтения — `protected_fair_use_history`,
  полный откат/0удалений, без частных полей. Обычный DELETE fair_use_reviews
  исключается из очистки, даже пустой: у runtime больше нет DELETE. При
  отсутствии истории остальная очистка сохраняется. Общая maintenance
  роль/operation не является исключением. Account close сохраняет retained
  metadata, не получает bypass. Downgrade с непустой новой историей запрещён.

### Выбранный SQL-механизм

Повторить принцип0111 receipt observation, без новой таблицы. Существующий
schema owner остаётся владельцем review/audit и INVOKER guard functions.
Отдельная `twobrain_rec_fair_use_audit_writer` — NOLOGIN NOINHERIT NOSUPERUSER
NOBYPASSRLS NOCREATEDB NOCREATEROLE NOREPLICATION, без memberships, владения
таблицами/чужими функциями, SELECT/UPDATE/DELETE/TRUNCATE/TRIGGER/REFERENCES
или schema CREATE. Нужны только schema USAGE и INSERT конкретных audit
столбцов; UUID создаёт функция, sequence права не нужны. Уже существующая
небезопасная одноимённая роль означает отказ миграции, не молчаливое исправление.

1. BEFORE ROW SECURITY INVOKER guard review проверяет настоящие session_user
   и current_user, role attributes/context, допустимый переход и неизменность
   остальных полей. DB time задаёт starts_at/review_by, первую appealed_at/ref
   и resolved_at; no-op сохраняет updated_at. App request допускает только
   прежнюю subject/lineage апелляцию notice/restricted→appealed. Maintenance
   создаёт notice и разрешает только review с каноническим created audit новой
   версии. Legacy appeal сохраняется, но не подтверждает старое основание;
   legacy resolve без такого источника отклоняется. Guard не заменяет CSRF.
2. AFTER ROW SECURITY DEFINER trigger, владелец — только writer, вычисляет
   created/первую appealed/первую resolved из OLD/NEW и сам INSERT audit в ту
   же транзакцию. Проверяет TG_RELID/ROW/AFTER/OP, не принимает произвольный
   action/payload и не использует dynamic SQL. No-op не пишет событие.
   DB login/session_user и DB writer/current_user сохраняются отдельно:
   внутри DEFINER current_user уже writer, а не исходный оператор. Для
   maintenance actor_user_id=NULL, declared_operator — ограниченное заявление;
   для appeal — прежний проверенный request user. Ни evidence_ref, ни контакты,
   содержание встреч/переписки, финансовые поля в audit не переносятся.
   Python больше не делает INSERT зарезервированного audit. Его ошибка
   откатывает source; обычный helper ставит outbox в этой же транзакции.
3. BEFORE ROW SECURITY INVOKER guard audit резервирует весь `fair_use.`
   namespace или target_kind=fair_use_review. Только настоящий current_user
   writer может INSERT закрытый canonical envelope; остальные INSERT,
   включая maintenance/COPY/UPSERT, отвергаются. Writer не вставляет обычные
   actions. OLD ИЛИ NEW в namespace запрещают UPDATE/DELETE/laundering.
   NULL/malformed поля не превращаются в разрешение. Unique partial index
   workspace/target_ref/action оставляет один created/appealed/resolved.
4. Functions имеют фиксированные search_path=pg_catalog,pg_temp, qualified
   public references и row_security=on. Создание/назначение владельца/attach/
   REVOKE PUBLIC и runtime EXECUTE выполняются одной транзакцией. RLS writer
   разрешает только canonical INSERT; широкий старый audit FOR ALL не считается
   защитой namespace — его обеспечивает INVOKER guard. Runtime не может
   вызвать/прикрепить writer, заменить/отключить trigger или SET
   session_replication_role. Guards/triggers ENABLE ALWAYS; TRUNCATE runtime
   запрещён правами и statement guard. Права прикреплённых триггеров после
   REVOKE EXECUTE доказать на PostgreSQL17, не возвращать PUBLIC EXECUTE.
5. Старую review FOR ALL policy заменить отдельными SELECT/INSERT/UPDATE,
   DELETE не разрешать. SELECT сохраняет subject/Owner/lineage/maintenance и
   валидированный account_merge scope. UPDATE USING дополнительно сохраняет
   узкую ветку valid account_merge для SELECT FOR UPDATE/FOR SHARE в F178;
   WITH CHECK и INVOKER guard запрещают этой ветке фактическую мутацию.
   Простое добавление узкой permissive policy не сужает старую OR-policy.
   rec_maintenance_allowed сам включает valid app account_merge, поэтому
   операторскому пути нужны также точные реальные maintenance identities.
6. Bootstrap применяет table И column REVOKE после общих grants до commit,
   возвращает только SELECT и перечисленные выше mutable-column права;
   проверяет effective ACL, FORCE RLS, definitions/owners/triggers, PUBLIC
   EXECUTE, memberships и parameter ACL. Несогласованная частичная миграция
   или failed bootstrap откатываются без окна расширенных прав. До установки
   миграции прежняя схема распознаётся, но новая защита не заявляется.

Это проект, не выполненная миграция или runtime PASS. Гарантия относится
к настоящим DB переходам и runtime-ролям: trusted schema/cluster owner может
изменить схему вне неё. Общая app DB роль и прежний authenticated request
context не являются новым независимым доказательством личности человека при
полном захвате app login/auth tables. Новый guard не даёт app операторских
прав, сохраняя прежнее доверие к пользовательскому контексту апелляции.
DB audit не доказывает полноту почты при произвольном ручном maintenance SQL:
положительный T068 путь проходит только рабочий CLI/кабинет → commit → outbox.
Полное чтение изменённых originals и независимый reviewer gate ещё впереди;
недостаток прав не разрешает подменить runtime-тест владельцем БД.

### Точный формат operator-ref и audit v1

Единственный нормативный формат `operator-ref`/`declared_operator` —
ASCII `^op-[0-9a-f]{32}$`, ровно35символов: непрозрачный ключ записи уже
существующего закрытого операционного журнала. Это не имя, email, credential
или доказательство личности; соответствие ключа журналу обеспечивает прежний
операционный процесс. CLI и BEFORE review guard проверяют один формат без
trim/casefold/coercion. Пустое, NULL, whitespace/control, Unicode, uppercase,
дополнительный суффикс или иная длина отвергаются закрытым кодом без echo.
Create/resolve передают заявление только через transaction-local
`app.fair_use_operator_ref` и точное `app.fair_use_evidence_reviewed=true`;
отсутствие/иное значение запрещает переход. Эти GUC не дают полномочий:
guard отдельно требует настоящую maintenance identity/context. Для app appeal
оба заявления игнорируются, в audit вместо них JSON null. Dry-run проверяет
те же входные ограничения без DML, execute не может ослабить DB guard.

Новый audit имеет ровно следующие физические столбцы существующей таблицы;
writer вставляет их явно, без произвольного JSON/SQL от вызывающего:

| Столбец | Точный тип, значение и происхождение |
| --- | --- |
| id | непустой UUID, новый `gen_random_uuid()` внутри DB writer |
| workspace_id | UUID фактического NEW.workspace_id |
| actor_user_id | SQL NULL для create/resolve; для appeal UUID прежнего проверенного request user с допустимой subject/lineage связью, не аргумент CLI |
| action | только `fair_use.review.created`, `fair_use.review.appealed`, `fair_use.review.resolved`, по фактическому переходу |
| target_kind | точная строка `fair_use_review` |
| target_ref | UUID NEW.id в стандартном lowercase формате36символов с дефисами, не evidence_ref |
| outcome | точная строка `applied`, фиксирует сохранённый переход, не enforcement/delivery |
| reason_code | SQL NULL для created/appealed; только NEW.resolution_code для resolved: `not_substantiated`/`no_longer_applicable` при cleared, `basis_confirmed` при confirmed |
| metadata_json | непустой JSON object ровно из8ключей ниже; без дополнительных ключей, массивов или свободного текста |
| created_at | конечный timestamptz из DB-защищённого NEW.starts_at/NEW.appealed_at/NEW.resolved_at соответственно, не дата вызывающего |

В metadata v1 все8ключей обязательны; отсутствие ключа отличается от
явно разрешённого JSON null. Дополнительные ключи отвергаются, неизвестная
версия отвергается; расширение требует отдельной миграции/контракта.

| Ключ | Точный JSON тип и допустимые значения |
| --- | --- |
| version | JSON number ровно `1`, без строкового/boolean/null преобразования |
| source | string `maintenance` для created/resolved, `request` для appealed |
| previous_state | JSON null для created; string `notice` или `restricted` для appealed; string `notice`, `restricted` или `appealed` для resolved |
| state | string `notice` для created; `appealed` для appealed; `cleared` или `confirmed` для resolved |
| db_login | string ровно `twobrain_rec_maintenance` для created/resolved либо `twobrain_rec_app` для appealed; фактический session_user, не GUC |
| db_writer | string ровно `twobrain_rec_fair_use_audit_writer`, фактический current_user внутри DEFINER |
| declared_operator | string точного формата operator-ref для created/resolved; JSON null для appealed |
| external_evidence_reviewed | JSON boolean true для created/resolved; JSON null для appealed; это заявление, не независимая проверка материала |

BEFORE audit guard проверяет точные набор столбцов/ключей, типы, NULL,
enum и межполевые соответствия action/source/state/result/actor/login/writer,
в том числе UUID/time. Автоматический AFTER writer получает workspace/review/
actor/time/переход из проверенного OLD/NEW и настоящего контекста, не из
переданного audit объекта. Его INSERT не требует права SELECT на review:
связь с реальным переходом обеспечивает фиксированный trigger, который
runtime не может вызвать/прикрепить. Прямой INSERT runtime запрещён даже
при безупречном envelope. Ошибка закрывается без SQL/значений в CLI.
Evidence-ref, appeal-ref, контакты, содержимое основания/встреч/переписки,
адреса БД и финансовые поля отсутствуют и в физическом target, и в JSON.
Это полный новый envelope v1; прежние nonreserved audit families не меняются.

Полный сигнал злоупотребления, применение ровно нужного ограничения,
notice-before-effect, срочное containment, реальное рассмотрение/реакция
≤24ч, остальные семейства событий, #7524, выпуск и развёртывание остаются
незавершёнными частями исходных задач. Принятый сигнал от тестового CLI
подтверждает только работоспособность операторского источника, не наличие
реального злоупотребления. T070/T068 остаются `[ ]`.
