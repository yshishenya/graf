# Минимальная полезная аналитика PostHog: пакет для согласования

30 сентября 2026. Destination: существующий self-hosted `https://analytics.2brain.pro`,
проект `GRAF Product Activation`, ID 1. Никаких новых credentials, grants,
ресурсов, provider ingestion или изменений production этим пакетом не сделано.
Главная и download сохранены. Настройки найденного проекта проверены через
существующий read-only Docker/DB доступ без вывода секретов.

## Решение владельца: последующая ревизия

30 сентября владелец явно выбрал IP и исходный внутренний account ID без
хеширования для своего self-hosted PostHog. Это заменяет прежнее предложение
no-IP/pseudonymous. Срок 365 дней не подтверждён. Решение о категориях данных
не разрешает rollout, новые credentials, обход readiness или сбор email/имени,
содержимого встреч, паролей, токенов, платёжных реквизитов, replay/autocapture.
Изменение этой документации не меняет текущий контракт приложения.

## Проверенные факты

- ClickHouse: 46 events, 46 уникальных UUID, все 9 июля 2026, последняя запись
  22:35:08 UTC. `graf_web_autocapture_pageview` 20, ready 17, click 6,
  `desktop_first_opened` 3. Нет сентябрьского ingestion.
- Наличие трёх first-open events не доказывает semantic dedupe: это три разных
  distinct/person identifiers. Anonymous → account merge реальными данными не доказан.
- У всех 46 events есть `$ip`; агрегированная проверка: все private network,
  не loopback/не пустые. IP значений не читали. `anonymize_ips=false` — будущие
  IP пользователей без дополнительной настройки не защищены этой политикой.
- Replay project opt-in=false, policy=90d. Event retention project=84 months.
  В фактических `events` и `sharded_events` нет TTL (проверка CREATE TABLE).
  Наличие файла 365-day TTL в репозитории не означает его применение.
- Один dashboard; его актуальность для сентябрьской воронки не подтверждается
  событиями. Существующих PersonalAPIKey records нет; capture project token
  не является management API credential.
- GRAF runtime PostHog disabled, host/key не заданы; подтверждённые readiness
  блокировки предыдущего отчёта сохраняются. Удобство входа не является причиной
  обходить provider gate или редактировать raw DB.
- PostHog browser открывает login; secure browserAuth инструментов в доступном
  каталоге нет. Scoped readable runtime env файлы не обнаружили операторских
  PostHog credentials. Пароль не сбрасывался, ключи не создавались.

## Оплата: последующее изменение владельца

API, processing worker и maintenance заново read-only проверены: checkout=true,
scope_all=true, observation=true, provider_environment=production. Это отдельная
чужая выкладка после первоначального аудита, а не наше изменение или разрешение
повторить выкладку. Источник release evidence: PR7386, head 5e0ebe113ae35095956245b9ad5d3a189180662b.

Billing ledger всё ещё 8 operations/8 unique idempotency keys, 4 webhooks/4 unique
provider event ids; последний webhook 29 сентября. Invoice states присутствуют,
но они не сверены с test/live provider, возвратами, чеками и settlement. Поэтому
выручка и payment acceptance не доказаны; платежей и webhook probes не делали.
Публичные сообщения о недоступности оплаты теперь требуют отдельного анализа
владельцем; по указанию пользователя тексты лендинга не менять.

## Сбор и идентичность

Существующий explicit allowlist из event_catalog.py:

`public_landing_viewed`, `public_landing_section_seen`, `public_landing_cta_clicked`,
`public_download_viewed`, `public_installer_download_clicked`, `public_login_intent_clicked`,
`desktop_first_opened`, `desktop_account_connected`, `desktop_autorecord_enabled`,
`first_recording_completed`, `first_result_viewed`, `first_value_session_completed`.

Для минимальной воронки autorecord не обязательно: пользователь может записывать
вручную. Не включать broad autocapture/replay/direct desktop egress только ради
этой воронки. Новые revenue/return events не входят в существующий allowlist;
их нельзя объявить уже готовыми. Первичная оплата/retention сверяется внутри
GRAF server ledger; отдельный контракт для передачи в PostHog подготовить позже.

До входа — непрозрачный consent-scoped browser/bridge identifier; не email и
не общая identity для всех посетителей. После входа proposed distinct_id — исходный
внутренний account ID, полученный сервером из authenticated principal, не из
произвольного поля клиента. Не передавать workspace/user IDs дополнительно, пока
не доказана необходимость. События остаются персональными и связуемыми с аккаунтом.
IP — адрес клиента из проверенной цепочки trusted proxy, не адрес API/worker;
не доверять произвольному X-Forwarded-For. Отсутствующий IP не выдумывать.
GeoIP enrichment пока отдельно не выбран; координаты/географию не добавлять.

Текущий код этого не реализует: identity.py/build_safe_identity хеширует исходные
IDs, is_safe_pseudonymous_id и posthog_client.py отвергают raw account IDs.
Нельзя просто включить флаги. Нужны versioned identity/payload contract для
PostHog, серверная binding/auth проверка, совместимый browser→account identify и
повторные dedupe tests. Псевдонимные ограничения других providers не ослаблять.
Исторические 46 событий не переписывать и не объединять задним числом без
проверенного mapping; смену схемы помечать identity_schema_version.
Bridge/unknown coverage всегда показывать; неподтверждённый источник не direct/AI.

Дедупликация: UUID-проверка достаточна только для транспортных дублей. Проверить
first milestone per account после рестарта и со второго устройства; app durable
ledger и process server guard не заменяют доказательства для всего аккаунта.
Не запускать эксперимент на production users.

## Retention/IP и готовый безопасный путь

Целевой режим после готовности: explicit events, исходный internal account ID и
IP, без содержимого, replay/autocapture. Срок хранения — нерешённый blocker;
365 дней остаётся предложением, не одобренной настройкой. Repo baseline и
project 84 months не заменяют решение владельца и проверку legal basis.
Уже существует `infra/scripts/apply-posthog-event-ttl.sh --dry-run/--status/--execute`
и `infra/posthog/clickhouse-retention.sql`. Script apply TTL к MergeTree таблице,
а не distributed events. Проверенная текущая реализация enforcement отсутствует:
TTL_defined=0. После отдельного инфраструктурного approval требуется dry-run,
проверка совместимости текущего PostHog schema, применение и `--status`, а затем
контролируемый expiry-test в отдельной restore среде. Не менять production TTL
в рамках «найти реквизиты»; retention может удалять данные.

IP: существующее anonymize_ips=false соответствует выбранной категории, но
доставка реального client IP не доказана: старые 46 адресов только private network.
Проектные настройки не менять через SQL. Supported UI/API после существующего
входа; не расширять постоянный доступ. На отдельном стенде проверить client IP
fixture против proxy spoofing, `$ip` на ingress и отсутствие ненужного GeoIP.
Документация: [Projects API](https://posthog.com/docs/api/projects).
Backup/export lifecycle и удаление по запросу должны иметь проверенные границы;
нельзя обещать исчезновение старых backup копий по одному TTL.

## Dashboards и запросы

Минимальные панели существующего project 1:

1. Freshness/delivery: approved events по дням, последний ingestion, dropped/retry
   отдельно от accepted. HTTP capture accepted не равняется записанному событию.
2. Acquisition coverage: organic/referral/direct/unknown, bridge presence,
   consented coverage и internal/automated исключения.
3. Activation: download intent/delivery/first launch/account/first processed/first
   value как отдельные stages. Уникальные first milestones по account, без
   person-level списков и без подмены funnel простыми totals.
4. D7: созревшие first-value cohorts и повторная полезная сессия; не pageview return.
5. Revenue reconciliation: live successful payment минус refunds из server ledger,
   не из CTA, invoice status или checkout flag. Несвязанные payments отдельно.

`docs/posthog-readonly-audit-2026-09-30.sql` содержит реально выполненные безопасные
ClickHouse queries freshness, schema, IP presence, duplicate и bridge coverage.
Сейчас fresh funnel/retention/payment panel должен честно показывать «не измерено».
Management API не доступен: PersonalAPIKey отсутствует, browser без сессии.
Сохранение панелей в production project не выполнено. Не создавать API key ради
обхода; требуется существующий поддерживаемый вход владельца (final secure ввод
самим владельцем), затем можно сохранить панели в доступном UI без новых grants.

## Consent/privacy: проверенный blocker и порядок реализации

Повторный live GET /privacy и /analytics-consent вернул HTTP 200. Тексты совпадают
с кодовым обещанием псевдонимных идентификаторов продуктовой аналитики и срока
«не менее 90 дней». Они не раскрывают выбранную связку raw account ID + client IP
для PostHog. Отсутствие адреса устройства в anonymous level 1 относится к агрегату;
его нельзя расширять новым персональным режимом. Одного решения владельца
недостаточно для обработки пользователей по несоответствующему notice.

Требуется согласованная отдельная ревизия privacy, analytics-consent и уведомления
зарегистрированного пользователя: destination, цели, исходный account ID и IP,
конкретный срок, отзыв/удаление, роли операторов. Версия решения должна явно
соответствовать новому scope; старое согласие нельзя автоматически считать
принятием расширенных категорий. Лендинг/CTA/title/description не менять.

Исходная specs/273-paid-traffic-analytics/spec.md требует ревизии FR-026/FR-046,
определения «Веха активации», identity и retention/deletion contracts;
FR-007/FR-010 anonymous level 1 остаются без изменений. Нужно обновить
product_analytics/consent_copy.py, identity.py, posthog_client.py, API contracts,
retention.py и связанные tests как отдельную согласованную реализацию, не
ослаблять forbidden_fields глобально. Этот аудиторский PR только фиксирует diff
требований; он не выдаёт false readiness и не разрешает production ingestion.

Стендовый acceptance: синтетический account и documentation IP fixture;
без/со старым/повреждённым/отозванным consent — ноль optional delivery; новый
scope — ровно allowlisted событие с server-bound raw account ID и client IP;
подмена account/proxy headers отклоняется; email/content/secrets/payment details
не проходят; anonymous→account merge не склеивает двух людей; повтор, restart и
второе устройство не умножают first milestones; accepted подтверждён ClickHouse;
удаление по raw account ID и expiry проверены после решения о сроке.

## Следующие необходимые решения и доступ

Категории account ID + IP уже выбраны; повторно их не согласовывать. Остались:
1. Срок хранения и проверка владельцем/ответственным за privacy актуального
   notice/legal basis, затем versioned consent implementation и стендовый тест.
2. Безопасный финальный вход владельца в существующий PostHog: management session
   отсутствует, project/endpoint найдены. Не создавать credentials/grants и не
   передавать найденные секреты в tool args, сообщения или другой сервис.
3. После тестов — отдельное согласование точного rollout diff. Readiness evidence
   backup/restore, retention/deletion и access governance не заменять флагами.

Dashboard/queries и серверная финансовая сверка сохраняются в описанном scope;
сбор реальных оплат не доказан наличием checkout=true. Production изменений нет.
