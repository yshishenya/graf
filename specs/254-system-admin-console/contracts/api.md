# Контракт интерфейсов Feature 254

Нормативный контракт до реализации. Основа URL на отдельном console origin: `/api/system-admin/v1`; HTML: `/system-admin`. Product origin не обслуживает admin API. JSON UTF-8, UUID как строки, времена RFC3339 UTC, деньги целыми копейками с `currency=RUB`, интервалы `[starts_at, ends_at)`, даты отображения в выбранной зоне. Enum неизвестной версии не интерпретируется как разрешение.

## Общие правила

Все вызовы, кроме явных auth endpoints, требуют отдельной admin cookie. Изменения — CSRF-token и same-origin; GET не меняет доменное состояние. Поиск с email/идентификаторами передаётся POST body, исключённым из access logs. Списки используют allowlist sort/filter, limit=25/50/100, стабильный cursor с привязкой к фильтрам, scope и сортировке. Ответ списка: `items, next_cursor, observed_at, coverage, warnings`; total необязателен и не задерживает страницу. Права фильтруют поля на сервере, не CSS.

Ошибки: `{error:{code,message,request_id,field_errors,retryable}, current_version?}`. 401 — сессия, 403 — недостаточно разрешений, 404 — несуществующий/недоступный объект для непривилегированного контекста, 409 — конфликт/несовместимая операция/повтор ключа с другим телом, 410 — истёкший preview/artifact, 422 — поля, 429 — предел (`Retry-After`), 503 — необходимый audit/DB/dependency недоступен. Стек, SQL, секреты и тело встречи в ошибке запрещены. `error.code`: `step_up_required`, `role_revoked`, `version_conflict`, `payment_reconciliation_required`, `deletion_in_progress`, `artifact_unavailable`, `quota_conflict`, `promotion_exhausted`, `audit_unavailable`, `capability_unsupported`.

Изменяемые ресурсы возвращают `version` (целое, увеличивается только при изменении). PUT/PATCH/command требуют `expected_version`. Для multi-object команды version каждого объекта. Все чувствительные команды требуют `Idempotency-Key` (UUID), `reason` 10–500 символов или действующий `case_context_id`; ключ уникален `(admin_id,command,key)`. Сохраняются hash входа и прежний result; другой payload на том же ключе — 409. Для денежных действий дедупликация дополнительно закреплена постоянным уникальным source_operation_id в доменной записи, не только TTL кешем.

Preview: POST `/previews` с `{command,targets:[{type,id,expected_version}],parameters,reason}`. Ответ `{preview_id,expires_at,source_versions,effects,warnings,blocked_reasons,requires_step_up}`. TTL 5 min; хранится безопасный снимок/hash без контента. Для денежных изменений `effects` включает payer, старый/новый plan_version, период, amount, квоту, следующую дату/цену списания и согласие. До commit пересчитывается под блокировкой. Не создаёт invoice/reservation/grant.

Commit: POST `/operations` с `{preview_id,expected_preview_hash}` и idempotency key. 202 `{operation_id,state,status_url}`; повтор — та же операция. Простые неопасные edits (черновик, ответственный обращения) допускают PATCH с version без preview. GET `/operations/{id}` → actor, kind, targets, created_at, updated_at, state, per_target_results, blocked_reason, domain_refs. Состояния `queued,running,awaiting_reconciliation,succeeded,partially_succeeded,failed,cancelled`; `awaiting_reconciliation` не является failure для повторного эффекта. Отмена возможна до отправки внешнего эффекта; UI не обещает отменить уже отправленное.

## Маршруты и полномочия

| Метод / путь | Полномочие | Вход / результат |
|---|---|---|
| POST `/auth/login` | Публичный ограниченный | email/password → opaque preauth challenge; одинаковая ошибка неизвестного email |
| POST `/auth/mfa` | preauth challenge | challenge + TOTP → session; recovery → только mfa_enrolment_required challenge |
| POST `/auth/enrolment/begin`, `/auth/enrolment/confirm` | ограниченный текущий enrolment challenge | настройка нового TOTP, confirm → полная session + одноразовый recovery набор |
| POST `/auth/activate` | одноразовое приглашение | token + password + подтверждённый TOTP; только после полной активации права |
| POST `/auth/password-reset/request`, `/auth/password-reset/complete` | Ограниченный reset | одноразовый reset, новый пароль; MFA сохраняется, старые сессии отзываются |
| POST `/auth/step-up`, `/auth/logout`, `/auth/activity` | Административная сессия | TOTP; отзыв; heartbeat только явной активности страницы |
| GET `/me`, `/sessions` | Self | собственные роли, сроки, capability flags, masked sessions |
| POST `/sessions/{id}/revoke` | Self / sessions.manage | собственная или разрешённая административная сессия |
| GET/POST `/admins`; PATCH `/admins/{id}` | admins.manage | приглашение/роль/status/expiry, version; superadmin only |
| POST `/admins/{id}/resend-invitation`; POST/DELETE `/grants/{id?}` | admins.manage | отзыв предыдущей ссылки; limited object/permission/expiry grant |
| POST `/search`; GET `/users`; GET `/users/{id}` | users.read | точный email/id/case/meeting/workflow; карточка с redacted sections |
| GET `/users/{id}/{access,payments,devices,meetings,incidents,history}` | соответствующее read | access explanations; money only billing.read |
| GET `/workspaces`; GET `/workspaces/{id}` | users.read | тип, memberships, policy, хранение; без чужих финансов по членству |
| GET `/meetings`; GET `/meetings/{id}` | meetings.metadata | metadata, revisions, availability, allowed_actions, evidence source/time |
| POST `/case-contexts` | любое относящееся к объекту content/audio/diagnostics право | объекты+reason/case; привязка к admin session, без wildcard из клиента |
| POST `/meetings/{id}/content` | content.read | context_id + revision + cursor; transcript/outcomes; аудит каждого обращения |
| POST `/meetings/{id}/exports` | content.export | context+format+revision → export operation; existing renderer, server download with session/revision recheck |
| POST `/meetings/{id}/media-ticket` | audio.listen / audio.download | purpose+context → короткий одноразовый серверный ticket; не MinIO URL |
| GET `/media/{ticket}` | то же право и session | Range stream/attachment; не bearer-only; content revision закреплена |
| POST `/meetings/{id}/retained-diagnostics` | diagnostics.content | context + конкретный generation id; separate view, без восстановления встречи |
| GET `/processing`; GET `/processing/{id}` | processing.read | попытки, очередь, провайдер, версии; action availability |
| GET `/incidents`; GET/PATCH `/incidents/{id}` | support.read/manage | статус, priority, assignee, snapshots, внутренние связи |
| GET `/devices`; GET `/devices/{id}` | devices.read | свежесть client state, версии/permissions/queue; без произвольных файлов |
| GET `/billing/{subscriptions,invoices,payments,refunds}` | billing.read | payer-filter, денежные строки и authoritative state |
| GET/POST `/plans`; GET/PATCH `/plans/{id}/versions/{version}` | catalog.read/draft | создание поддерживаемого plan code, capabilities, offers; только draft изменяем |
| GET/POST `/campaigns`; GET/PATCH `/campaigns/{id}` | promotions.read/draft | immutable published version + mutable draft; не сырой код в GET |
| POST `/campaigns/{id}/codes` | promotions.manage | common/batch<=1000; plaintext один раз, no-store, аудит без значения |
| POST `/campaigns/{id}/eligibility` | promotions.read | user+offer+now → применимость/причина, без резерва |
| GET `/metrics`, `/metrics/{id}/series` | analytics.read | definition_version, interval, timezone, count/sample/coverage, observed_at |
| GET `/alerts`; PATCH `/alerts/{id}` | operations.manage | ack/assignee/status; источник/влияние |
| GET `/integrations`; GET `/integrations/{id}` | integrations.read | consent/status/last success; masked settings |
| GET `/settings`; PATCH `/settings/{key}` | settings.read/manage | только разрешённый каталог ключей с version и validation |
| GET `/storage`, `/deletions/{id}`, `/dependencies` | operations.read | известные состояния с provenance/time |
| GET `/audit` | audit.read | actor/action/target/result/time; no edit/delete endpoints |
| POST `/table-exports`; GET `/table-exports/{id}/download` | exports.table + dataset permission | фильтры, <=10000 строк, 24h, access recheck, CSV formula escaping |

Отсутствие `{id}` в grant creation означает POST `/grants`; отзыв — DELETE `/grants/{id}`, с CSRF/version. Routes таблицы раскрываются в OpenAPI при реализации; `system_admin/schemas.py` — единственный runtime источник, golden контракт проверяет соответствие этому документу.

## Закрытый перечень команд operations

`meeting.export`, `meeting.reprocess`, `meeting.delete`, `account.close`, `account.block`, `user_sessions.revoke`, `sharing.revoke`, `calendar.sync`, `integration.disconnect`, `subscription.grant`, `subscription.compensate`, `subscription.schedule_transition`, `subscription.cancel_renewal`, `entitlement.override`, `entitlement.revoke_override`, `billing.reconcile`, `fair_use.resolve`, `queue.pause`, `queue.resume`, `notifications.retry`, `plan.publish`, `plan.close_sales`, `plan.archive`, `campaign.publish`, `campaign.pause`, `campaign.finish`, `campaign.archive`, `promotion.restore_usage`.

Каждая команда имеет отдельную allowlist-модель параметров, capability и handler. Произвольный kind, путь, SQL, URL callback, код Python и generic model patch запрещены. Массовый режим только для временных продуктовых grants, отзыва пользовательских сессий и будущих тарифных переходов, <=100 явно выбранных объектов; для остальных команд ровно 1 target. Исключение запуска/публикации целого тарифа не означает массового изменения подписчиков.

Refund: консоль только показывает результат существующего провайдерского процесса; endpoint прямого редактирования paid/refunded отсутствует. Published plan/campaign редактируются новой версией. Ошибки отдельной карточки не обнуляют остальные данные.

## Клиентский интерфейс событий

POST `/api/diagnostics/v1/events` использует существующий device/user auth, **не admin cookie**. `{schema_version:1,batch_id,events:[...]}`; поля и пределы в [telemetry-and-metrics.md](../telemetry-and-metrics.md). Ответ по event_id: `accepted|duplicate|rejected` + safe reason, `server_received_at`. Только rejected invalid items удаляются; сетевой сбой повторяет тот же ID. Нет произвольных строк атрибутов; unknown event/version отклоняется 422 без сохранения тела. При лимите 429 Retry-After. Сервер устанавливает владельца и проверяет связи. Prelogin сбор остаётся локальным до verified claim при входе; anonymous endpoint в первом выпуске не нужен.

POST `/api/diagnostics/v1/operation-links` связывает local_operation_id с upload/meeting, проверяет владельца и зарегистрированное устройство; внешний fingerprint не используется как авторизация. Старые support v2 клиенты продолжают работать; missing поля помечаются отсутствующими. Новый API добавляет внутреннюю историю, не расширяет внешний GitHub safe report.

`fair_use.resolve`: superadmin-only, `{case_id,decision:cleared|confirmed,expected_version,reason}`, отдельное non-grantable `fair_use.manage`; сохраняет usage/referral history, меняет только решение существующего fair-use lifecycle. Не подменяется entitlement override. Повтор/конкурентный ответ требует idempotency/version.

Case context — только основание аудита и scope, не grant: audio-only не получает transcript, diagnostics-only не получает live content, content.read не получает export. Transcript/outcome export требует content.export; combined package с аудио требует также audio.download и доступную согласованную revision. GET export artifact повторно проверяет эти права и session.

`queue.pause`: `{stage:normalization|asr|outcomes,duration_minutes:1..60,expected_version,reason}`, только superadmin queue.manage, preview affected queue/users; resume снимает конкретную pause version. Auto-expiry — внутренний lifecycle, не новая команда от браузера.

`notifications.retry`: system admin/superadmin; `{notification_id,expected_version,reason}`, только существующее разрешённое служебное сообщение с прежним recipient/template. Не маркетинг, не переотправка уже подтверждённо доставленного; отсутствие доказательства доставки не доказывает отсутствие отправки. Sent/unknown сначала существующая delivery reconciliation, expired/revoked invitation не возрождается. Предел 1/min и 5/day на notification/recipient, audit+idempotency.

Plan/campaign publish и subscription.schedule_transition поддерживают `execute_at`; future commit создаёт точное scheduled_approval из security contract. UI показывает scheduled/needs_review/expired/cancelled; естественное истечение browser session не отменяет запланированный запуск, отзыв полномочий отменяет неисполненное approval. PATCH настроек с retention/export/recipient последствиями требует preview_id/step-up/expected_version по key-level allowlist.

Одноразовая выдача новых promo codes: повтор idempotency key не генерирует новую партию. Сохраняется metadata результата; plaintext после первого показа недоступен. При утрате ответа UI показывает «коды созданы, значения недоступны» и предлагает отозвать только неиспользованные коды и создать новую партию отдельной операцией; redeemed/reserved obligations сохраняются. Это явное исключение для секретной части повторного ответа.

### Пользовательский профиль и коммерческие возможности

`GET /api/v1/auth/me` сохраняет существующие поля `billing` и добавляет `plan_label`, `access_source`, `access_until`, `commercial_capabilities`, `processing_used_seconds`, `processing_reserved_seconds`, `processing_available_seconds`, `processing_window_start/end`, `usage_freshness`. Название и возможности берутся из закреплённой версии либо legacy-контракта, затем применяются индивидуальные назначения. Источник различает free/trial/paid/gift; подарок не создаёт значение оплаченного срока. Название не выбирается по последней цене магазина.

`commercial_capabilities` содержит только поддерживаемые boolean-флаги и `export_formats`; количественные лимиты туда не дублируются. Это коммерческий слой: обязательные политики продукта и проверка конкретного действия на сервере сохраняются. Member получает возможности, но его объёмы, окна, оплаченный срок и доступ до даты — `null`; прежние границы финансовых полей owner/admin сохраняются. Для доступного количественного расчёта `processing_unlimited=true` и `processing_available_seconds=null` означают безлимит, `false` и `0` — исчерпание. `usage_freshness=null` означает, что количественная проекция не раскрыта. Права и usage читаются под shared lock пространства до конца транзакции. Ошибочные/отсутствующие закреплённые условия управляемого тарифа дают 503 `billing_entitlements_unavailable`, без подстановки Free или personal и без внутренних деталей ошибки.

`POST /billing/subscription/resume` принимает вместе с существующим согласием и `expected_authority_version` обязательные для выполнения `expected_plan_version_id`, `expected_price_id`, `expected_schedule_version`, `expected_paid_through` (timezone-aware ISO8601). Они приходят из серверной формы по закреплённой подписке. Под общей блокировкой сервер сверяет все поля, текущую подтверждённую цену, срок, плательщика и платёжный метод. Несовпадение/отсутствие поля → redirect `result=conflict`, неизвестные условия → `result=terms_unavailable`; новый платёж не создаётся. Старые формы после обновления сервера требуют перезагрузки. Изменение только consent version не заменяет проверку расписания и цены.


### Покупка публичного управляемого тарифа — реализованный участок T018

`GET /billing/plans` использует `read_public_catalog`, показывает произвольные публичные коды, название из display_terms, обе цены одной выбранной версии и фактическую квоту/ёмкость. Закрытые, административные и приглашённые предложения не продаются на этой странице. Текущий доступ определяется общим resolver; действующая платная подписка не заменяется новой покупкой.

`GET /billing/checkout?plan_code=…&cycle=month|year` и `POST /billing/checkout/preview` сохраняют выбранный код; отсутствие plan_code сохраняет совместимый personal. Промокод передаётся только телом формы и коротким HttpOnly cookie, не URL. POST start требует plan_code, cycle, idempotency_key, expected_quote и два явных согласия. expected_quote — SHA-256 канонических показанных условий, итоговой суммы и выбранной скидки/версии; это проверка согласованности, не отдельное полномочие. Цена берётся только из БД. Изменившийся расчёт возвращает terms_changed без счёта и резерва; после отображения новой суммы нужны новые согласия.

Внутри транзакции после workspace/subscription locks вызывается узкая `billing_lock_checkout_catalog(text)`: настоящая app role и request context, shared locks плана и выбранной версии, без выдачи app права UPDATE каталога. Отсутствующий контекст отклоняется через IS DISTINCT FROM, включая SQL NULL. После блокировки заново читается публичная доступность с актуальным временем. Изменения указателя продаж и закрытие версии ждут сохранения счёта; блокировки освобождаются до сети. Редактор/публикация каталога должны брать plan перед version. Уже сохранённый счёт сохраняет условия после закрытия продаж.

Повтор ключа сначала сверяет request_fingerprint: actor, plan, cycle, expected_quote и hash введённого нормализованного кода. Изменение тела даёт conflict; точный повтор возвращает прежний URL/счёт без повторной проверки меняющейся акции и без нового списания. Старые операции без fingerprint продолжаются через существующую страницу статуса; новая форма с их ключом не присваивает себе старую операцию. Перед отправкой управляемого платежа используется тот же validate_paid_catalog, что при подтверждении: оба финансовых снимка и точная историческая версия должны совпадать. Legacy personal recovery сохраняется.


`GET /billing/storage` использует разрешённую owner-проекцию общего resolver под shared workspace lock; показывается итоговая ёмкость с назначениями, а не только базовый тариф. Потерянные managed pins дают 503. Публичные `/` и `/offer` читают тот же selected-pointer каталог через существующий request context с нулевыми tenant IDs; public landing сохраняет проверку точных условий единственной существующей маркетинговой карточки, не возвращаясь к закрытым legacy-продажам. Отсутствие этой карточки не является глобальным запретом иных управляемых предложений в кабинете.

### Коммерческие ограничения выдачи — T017

Пользовательские capabilities и реальные выдачи в `cabinet/egress.py` используют общий resolver для пространства встречи и действительного пользователя. `audio_download` ограничивает скачивание аудио, не прослушивание; `content_export` и точный `export_formats` ограничивают содержательный экспорт. Старые текстовые выгрузки требуют `txt`, JSON-манифест пакета — `json`. Создание и повторное получение готового пакета повторно проверяют текущие разрешения его компонентов. Обязательные ACL, ограничения встречи, удаление и проверка версии сохраняются.

Shared content API и HTML получают отдельную зависимость `AuthenticatedShareDbDependency`: область данных остаётся областью владельца, `user_id` берётся из проверенного principal получателя. Анонимный public-share context остаётся отдельным. Идентификатор в контексте не заменяет recipient proof, активную подтверждённую почту принятого внешнего приглашения и ACL. Скрытое/отсутствующее пространство либо непроверенные условия дают безопасный `billing_access_unavailable`/503 без вложения.

Окончательная выдача использует порядок Workspace FOR SHARE → Meeting. Назначения/отзывы и billing writers должны брать Workspace до Meeting. Длительная подготовка содержательного экспорта выполняется после commit `content_export_requested`: иначе внешние ключи аудита удерживают KEY SHARE и блокируют отзыв. Перед выдачей повторяются актуальные условия и формат; подготовленные байты при отказе не возвращаются. Скачивание аудио повторно проверяет текущий момент после сборки ограниченного тела: начало запрета/конец разрешённого периода не требует записи в БД, поэтому одна блокировка строк недостаточна. Системная выдача суперадминистратора использует собственное полномочие и аудит и не зависит от пользовательского тарифа.

Интерфейс экспорта получает разрешённые форматы с сервера; копирование, выполняющее TXT-экспорт, отключено при отсутствии `txt`. Новая проверка допуска не меняет уже подтверждённые деньги, сохранённые расшифровки или результаты генерации.

`meeting_sharing` управляет допуском новых прямых доступов, приглашений и ротации токенов. Отказ `commercial_sharing_denied`/403 фиксируется до создания разрешения/приглашения и запуска доставки. Workspace lock сериализует допуск с изменением коммерческих условий. Ранее допущенные приглашения и grants не отменяются автоматически; их явный отзыв остаётся доступен владельцу при запрете новых приглашений. `access.can_share` сохраняет доменное право управления, а `share.capability_state=policy_blocked` и `capability_reason` описывают недоступность нового допуска. Интерфейс сохраняет список старых прав и отзыв, отключает поиск/создание и ротацию.

### Проверка адресата и архивирования при приёме

`rec_share_recipient_is_member(meeting_id, user_id)` — ограниченная проверка активного членства в текущем пространстве/организации с контекстом request и допустимым контекстом встречи. Она не выдаёт строки memberships, адреса, роль или право читать встречу. Поиск и создание по-прежнему выполняют полный ACL, включая подтверждение адреса внешнего приглашения; новая функция не заменяет его. Direct self-only RLS memberships сохраняется. EXECUTE доступен application role и владельцу функции; повторный runtime bootstrap выдаёт точное право. Membership proof используется для обнаружения уже имеющегося общего доступа и не повышает роль получателя.

`audio_archive` проверяется общим resolver при новом finalize, до подготовки и после Workspace FOR SHARE перед Meeting/MediaRevision/UploadSession. При отказе — 403 `commercial_audio_archive_denied`, без принятия ревизии и без молчаливой смены выбора. Исходные загруженные части остаются под существующим учётом хранения; составленные объекты очищаются существующим cleanup. Ручная загрузка проверяет право до первого сохранения объекта; её временный поток закрывается также при раннем отказе. Явное `archive_audio=false` сохраняет существующую временную обработку.

После успешного приёма persisted UploadSession.archive_audio — источник истины для обработки/нормализации и поздних повторов: позднее назначение не меняет способ хранения уже принятой записи. Реальная доступная ёмкость по-прежнему проверяется при резервировании; эта политика не означает обход количественной квоты. Веб-форма объясняет отказ и возвращает выбранный файл в диалог для явного изменения условий. macOS относит этот код к storageQuota, не отзывает вход из-за коммерческого 403.
