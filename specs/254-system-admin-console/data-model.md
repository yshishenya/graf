# Модель данных и атомарность

Все ниже — проектируемые изменения. Существующие ID, подтверждённые финансовые snapshots и времена не переписываются. Новые UUID генерируются сервером, foreign key принадлежность проверяется, деньги bigint minor units, интервалы UTC с отдельно закреплённой IANA timezone для календарных вычислений. У всех редактируемых aggregate roots есть integer version. Состояния фиксируются ограниченными enum/check, история append-only.

## 1. Системная область `system_control`

| Таблица | Основные поля | Ограничения и индекс |
|---|---|---|
| principals | id, normalized_email, password_hash, status invited/active/recovery_pending/blocked/revoked, auth_version, optional linked_user_id, created_at | UNIQUE email; связь с продуктом не даёт прав; удаление продукта не каскадирует principal |
| credentials | principal_id, credential_version, encrypted_totp_seed, key_id, nonce, last_totp_counter, recovery_code_hashes | Только служебные auth методы; никогда обычный API; одноразовый counter/recovery под row lock |
| role_assignments | id, principal_id, role, starts_at, expires_at, revoked_at, granted_by, reason | Один действующий role assignment на principal; expire>start; singleton governance lock для role mutation и bootstrap |
| permission_grants | id, principal_id, permission, target_type/id, start/end, revoked_at, granted_by, reason | Ограниченный список разрешений/объектов, <=24h; target creation через зарезервированный server id; уникальный source operation |
| sessions | id, token_hash, principal_id, auth_version, issued_at, last_interaction_at, absolute_expires_at, mfa_at, revoked_at | UNIQUE token_hash, index principal/revoked; session не имеет обязательного workspace/device |
| challenges | id, kind invitation/reset/preauth/enrolment, token_hash, principal_id, expires_at, consumed_at, attempts, issued_auth_version, credential_version | Одноразовое потребление, challenge не session; TTL cleanup |
| rate_limits | bucket_hash, kind, window_start, attempts | PK bucket+kind+window; login IP hash без сырого адреса в аналитике |
| case_contexts | id, principal/session, reason или incident_id, targets, expires_at | Не дольше session; exact object scope; DELETE/expiry не стирает аудит |
| previews | id, actor, command, safe_parameters, target_versions, effect_hash, expires_at | 5 min, no domain side effects, no content |
| operations | id, actor/session, command, idempotency_key, request_hash, expected_versions, safe_parameters, state, timestamps | UNIQUE actor+command+key; durable доменная source reference; state machine ниже |
| operation_targets | operation_id, target_type/id, expected_version, state, domain_ref, error_code, effect_started_at, authorized_permission/target, allowed_continuation_actions, attempt_fence | PK operation+target; <=100 только разрешённые batch команды |
| audit_events | id, actor/session/role, permission, action, target, reason/context, operation_id, result, occurred_at | INSERT-only для runtime; indexes time/id, actor/time, target/time, operation; нет transcript/secret |
| table_exports | id, actor, dataset/filter hash, scope, object_key, rows, state, expires_at | <=10000, 24h, file без контента встречи; access recheck; MinIO key не API URL |
| console_settings | key, typed_value, version, changed_by, effective_at | allowlist из security.md; нет произвольных JSON settings/секретов |

Связанные приглашения могут храниться в challenges без второго invitation service. TOTP secrets требуют encrypted-at-rest; правила transcript retention это не меняет. Удаление системной личности — отзыв с сохранением идентичности автора аудита, не hard-delete FK.

Защита последнего суперадминистратора: все изменения active role/status/expiry сериализуются на singleton row; после изменения должен существовать минимум один бессрочный superadmin с действующим назначением (active либо временный recovery_pending). Прикладной доступ recovery_pending закрыт до нового MFA; восстановление credentials не удаляет назначение. Invite не считается active. Bootstrap и emergency recovery используют тот же lock. Окончание временной роли не может сделать счётчик нулевым, поскольку invariant требует бессрочного назначения.

Operation: queued→running→succeeded/partially_succeeded/failed; running→awaiting_reconciliation→running/terminal. queued→cancelled допустимо до эффекта. Version и role проверяются при commit и отдельно при переходе к фактическому эффекту; после durable effect-start подтверждения/удаление доводятся до результата. Reconcile не повторяет неизвестную отправку. Worker читает фактическую операцию по ID, не доверяет сообщению транспорта как разрешению.

## 2. Тарифы и доступ

| Сущность | Изменение | Инвариант |
|---|---|---|
| billing_plans (новая) | id, unique immutable code, display_name, sales_state, current_version_id, version | free/trial зарезервированы; новые code regex `[a-z][a-z0-9_]{2,31}`, архив не удаление |
| billing_plan_versions (существующая) | plan_id, status, capability_schema_version, immutable capability JSON, display_terms, publication_revision | Сохранить UNIQUE(plan_code,version) и прежние id; draft→scheduled→published→retired, опубликованная immutable |
| billing_plan_prices (новая) | id, version_id, cycle month/year, RUB, amount_minor | UNIQUE(version_id,cycle,currency), amount>=provider minimum для paid; old version может иметь одну price |
| workspace_subscriptions | pinned_plan_version_id, pinned_price_id, timezone, next_charge_at, schedule_version, legacy_pinned_snapshot | Согласие recurring_authority_version отдельно от schedule/application version |
| billing_entitlement_grants | nullable plan_version_id, existing invoice/payment refs and snapshots | Только подтверждённые деньги; не использовать для gifts |
| billing_access_adjustments (новая) | id, user/workspace, kind plan_interval/allow/deny/extra_quota/exact_limit, feature_key, plan_version_id, value/unit, starts/ends, source_kind/ref, admin_operation_id, state/version | UNIQUE source_kind/source_ref, positive quota/days; no paid invoice; revoke отдельное событие |
| subscription_transitions (новая) | subscription, from/to version/price, effective_at, expected schedule, consent_state, notice refs, status | Одновременно один pending transition на subscription; нельзя применять новую цену без требуемого согласия |
| usage reservation allocations | reservation_id, source_kind/id, allocated_units, consumed_units | Сумма allocations соответствует резерву; source не расходуется дважды |

Capabilities — allowlist текущих функций и измеримых квот; unit и окно определяет schema, не arbitrary expression. `unlimited` — отдельное boolean, не -1; использование всё равно измеряется. Различать код тарифа и `Workspace.kind=personal`: корпоративный checkout не создаётся заменой строк.

Единый resolver возвращает `base_source, plan_version, grants, restrictions, effective_capabilities, access_until, paid_intervals, quota_window, used,reserved,remaining,explanation`. Порядок и примеры из ui-and-operations.md обязательны: hard product/workspace/security deny → индивидуальный deny → допустимый индивидуальный allow/exact limit → оплаченный/trial/gift base → Free; allow не снимает hard deny. Несколько exact limit для одной функции и перекрывающегося интервала запрещены; дополнительные квоты складываются по уникальному source. Совпавшие plan intervals разных тарифов требуют явного overlay/последовательности в preview, не выбора по алфавиту или цене.

Новые quota reservations распределяются: базовый остаток, затем extra sources по ближайшему expiry и ID. Уже принятый резерв сохраняет allocations после expiry/снижения лимита; новые могут блокироваться. Успешное потребление уникально по исходной ревизии/операции; смена плана/окна не обнуляет использованное. Если доступ заблокирован обязательной политикой, reserve не разрешает начать запрещённый capture, но учёт ранее начатой обработки остаётся согласованным.

Gift добавляется к концу непрерывного интервала выбранной версии или явно выбранной последовательности; календарные дни в pinned timezone. `paid_through` legacy не является источником суммы реально оплаченных дней: старые реферальные credits уже могли его расширить. UI paid interval берёт из paid grants, access_until из resolver. Storage addon — общий предел; отдельная extra bytes quota прибавляется только один раз. Существующая микросекундная пропорция доплаты сохраняется.

## 3. Акции

Сохранить identity promotion_campaigns, добавить immutable `promotion_campaign_versions` с benefit discount_percent/gift_days, audience definition, permitted offer IDs, start/end/timezone, max_uses, budget_value/budget_unit, publication_version. Бюджет discount — копейки скидки; gift — календарные дни; никогда смешанный денежный эквивалент.

`promotion_codes`: id, campaign_id, hash, batch_id, optional canonical_identity_id, max_uses, status, created_by. hash нормализованного кода по существующему helper, UNIQUE hash; legacy hashes переносятся без изменения. plaintext показывается только при создании/одноразовой выгрузке; повторное получение недоступно. Batch<=1000. Общий код имеет общий limit, индивидуальный default max_uses=1.

`promotion_redemptions` расширяется ссылками version_id/code_id/canonical_payer_id/operation_id, reserved_budget, used_budget, state, nullable invoice_id, gift_adjustment_id, timestamps. Каждая новая попытка — новая строка; не перепривязывать expired redemption к новому invoice. UNIQUE operation_id и ограничение одновременно активных/использованных применений по идентичности и условиям кампании. Исторические строки сохраняются; старый UNIQUE workspace/campaign снимается после установки нового ограничения и миграции.

Состояния reserved→redeemed/released/expired; released/expired не возвращаются в reserved. Gift reserve+adjustment+redeemed — одна транзакция. Refund не меняет redeemed и used_budget автоматически; restore_usage отдельный компенсирующий ledger event и явное решение superadmin. Не скрывать факт предыдущего использования.

## 4. Общий порядок блокировок денег

Одинаковый для checkout, gift, renewal, webhook, отмены и promo: canonical payer/merge guard → subscription → billing operations по ID → campaign по ID → code/eligibility identity → redemption → entitlement/usage rows. Подмножество допустимо, обратный порядок запрещён. Перед освобождением subscription lock атомарно записывается dispatch claim: operation_id, attempt_id, provider idempotency key, pinned request hash, schedule_version, consent_version и state=dispatching. Claim означает возможную отправку даже при падении процесса до сети: gift/cancel/release не считают его unsent. После commit исполнитель отправляет только этот snapshot с этим provider key; takeover после crash сначала сверяет провайдера, не создаёт новый key. Сетевой вызов вне транзакции; результат фиксируется новой транзакцией по attempt fence. Повтор отправки допускается только когда существующий provider protocol доказывает безопасное повторение того же ключа; иначе awaiting_reconciliation. Pause после claim не освобождает reservation. Crash-before-send не оправдывает автоматическое снятие claim без доказательства отсутствия эффекта. Lease/idempotency остаются существующими у provider adapter. Merge account берёт тот же identity guard и соблюдает текущие blockers.

Под campaign lock проверяется `used+reserved+requested<=max` для количества и бюджета, включая ambiguous. Reservation expiry освобождает только доказанно неотправленную scheduled операцию без provider ID. Provider sent/unknown/key_expired/manual_resolution → waiting_reconciliation. Простой timeout не разрешает повторную покупку/подарок с несовместимым расписанием.

Подарок/transition отменяет только доказанно неотправленное старое расписание под subscription lock; иначе команда ждёт reconciliation, затем заново preview/проверка версии. При изменившихся последствиях требуется новое подтверждение preview, не автоматическое принятие новой цены. Поздние деньги всегда отражаются, права выдаются по авторитетному paid snapshot либо отдельный reconciliation gap; не подделывается согласие.

## 5. Диагностика и хранение

`support.incidents` расширяется assignee/priority/status/version без удаления существующего safe report. Новые `support_incident_snapshots`: incident_id, sequence, schema_version, received_at, safe_json/hash; ограничение срока/числа из telemetry. `diagnostic_operation_links`: device+local_operation_id, verified user/workspace, upload/meeting/revision IDs, provenance, verified_at; UNIQUE device/local_op/relationship. Связь проверяется по реальной принадлежности сервера, совпадение fingerprint не доказательство.

`diagnostic_events`: event_id, schema_version, source, server user/device, source time + received_at, sequence/launch/local_operation_id, validated foreign links, safe typed payload, policy version, environment/internal flags. UNIQUE device+event_id, индексы target/received_at и retention partition. Данные до входа локальные; после входа только текущие разрешённые связи, previous-user local queue не присваивается новому аккаунту.

`metric_aggregates`: metric_id+definition_version+bucket+dimensions, numerator, denominator, coverage counters, computed_at/watermark. Исходный event time не финансовая истина, server state ledger источник денег. Пересчёт идемпотентен, late events обновляют незакрытый bucket, поздние исправления помечаются revised; нет скрытой подмены historic snapshots. Параметры окна и финализации — telemetry. `operational_alerts`: fingerprint, first/last_seen, affected_count, severity, state, assignee, resolved_at; дедупликация по rule/version/component/error window.

Сроки — [telemetry-and-metrics.md](telemetry-and-metrics.md), не новая единая политика: аудит 365 дней, события/снимки согласно своим классам; retained GenerationCall/Langfuse/Temporal остаются отдельными. Финансовые записи сохраняют существующий срок; новые display projections удаляемы/восстановимы из источника. Audit retention cleanup выполняется отдельной операторской maintenance ролью и фиксируется; console runtime DELETE не получает.

## Плановые и эксплуатационные записи

`system_control.scheduled_approvals`: actor/assignment_id+version, authorizing_permission, optional grant_id+version+expires_at, approved_command/target/parameters_hash, execute_at, approved_at/MFA_at, state scheduled/claimed/needs_review/expired/cancelled/completed, revoked_at; UNIQUE source_operation. Helper проверяет текущую роль/состояние личности и доменные условия по security contract, но не срок завершившейся browser session. На role/security reset и grant revoke/expiry/replacement pending approvals отзываются атомарно; execute_at строго внутри срока grant, фактический старт после expiry запрещён.

`queue_admission_pauses`: stage unique active slot, starts_at/expires_at, version, operation/actor, reason. До claim внешнего задания проверяется актуальный pause; active claim не отменяется. Auto-expiry применима даже после потери console, что исключает бессрочную остановку. Settings rows имеют typed key, policy version и effective_at; retention deadline записывается на новый объект и не пересчитывается молча задним числом.
