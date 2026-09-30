# Минимальная полезная аналитика PostHog: пакет для согласования

30 сентября 2026. Destination: существующий self-hosted `https://analytics.2brain.pro`,
проект `GRAF Product Activation`, ID 1. Никаких новых credentials, grants,
ресурсов, provider ingestion или изменений production этим пакетом не сделано.
Главная и download сохранены. Настройки найденного проекта проверены через
существующий read-only Docker/DB доступ без вывода секретов.

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

До входа — короткоживущий непрозрачный view/bridge identifier только по допустимому
согласию. После входа — существующий pseudonymous account identity, никакого email,
display name, названий встреч или участников. `identity.py` делает SHA256 от
внутреннего identifier с постоянным публичным salt; это pseudonymization,
не криптографическая анонимность. Нельзя хешировать email и назвать его anonymous.
HMAC/секретный salt и смена identity потребуют отдельного совместимого контракта.
Bridge/unknown coverage всегда показывать; неподтверждённый источник не direct/AI.

Дедупликация: UUID-проверка достаточна только для транспортных дублей. Проверить
first milestone per account после рестарта и со второго устройства; app durable
ledger и process server guard не заменяют доказательства для всего аккаунта.
Не запускать эксперимент на production users.

## Retention/IP и готовый безопасный путь

Предложение для существующего проекта: explicit pseudonymous events 365 дней,
без replay/autocapture и без клиентского IP/GeoIP. Текущий repo policy ожидает
365 дней, минимум baseline 90; изменение срока без owner/legal решения запрещено.
Уже существует `infra/scripts/apply-posthog-event-ttl.sh --dry-run/--status/--execute`
и `infra/posthog/clickhouse-retention.sql`. Script apply TTL к MergeTree таблице,
а не distributed events. Проверенная текущая реализация enforcement отсутствует:
TTL_defined=0. После отдельного инфраструктурного approval требуется dry-run,
проверка совместимости текущего PostHog schema, применение и `--status`, а затем
контролируемый expiry-test в отдельной restore среде. Не менять production TTL
в рамках «найти реквизиты»; retention может удалять данные.

IP: `anonymize_ips=true` менять через поддерживаемый Projects API/UI после входа,
а не SQL update. Для server-mediated events отдельно проверить `$geoip_disable`,
чтобы адрес сервера не становился местоположением клиента. Это предложение,
не проверенный deployed patch. Документация:
[Projects API](https://posthog.com/docs/api/projects),
[GeoIP implementation](https://github.com/PostHog/posthog-plugin-geoip).
На стенде доказать отсутствие `$ip` и производных GeoIP properties после ingress.
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

## Одно согласование после готовности

Текст решения для владельца, а не применённое разрешение:

«Разрешаю подготовить и проверить на отдельном стенде минимальную explicit
воронку в существующем self-hosted PostHog project GRAF Product Activation.
Данные: короткоживущая анонимная связка по согласию, псевдонимный account ID,
название milestone, время, platform/version bucket, обезличенные campaign labels,
bridge/source reliability; без email, IP/GeoIP, текстов/названий встреч, участников,
аудио, replay/autocapture. Предлагаемый retention — 365 дней. Сначала подтвердить
основание сбора/consent, semantic dedupe, доставку в ClickHouse, attribution,
retention/backup/deletion и dashboards. После review точного конфигурационного
diff отдельно разрешить rollout; это решение само по себе production deploy
не разрешает. Payments остаются в GRAF ledger до отдельной финансовой сверки».

Главный blocker: отсутствует management session и проверенные readiness evidence.
Проект и endpoint уже найдены, пользователю не нужно искать реквизиты вручную.
Нужен только безопасный финальный вход владельца в существующий PostHog; найденные
секреты не будут передаваться в browser tool args, сообщения или другой сервис.
