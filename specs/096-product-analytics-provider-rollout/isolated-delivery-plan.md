# Изолированная доставка PostHog: план и граница доказательств

03.10.2026. Это предложение, стенд не установлен и ingestion не подтверждён.

## Фактический preflight

- Docker Desktop 29.6.1, aarch64, 10 CPU, 8 216 862 720 bytes RAM. Общий Docker уже обслуживает GRAF Dev и другие задачи; их контейнеры/тома/настройки не менялись.
- Локальных образов PostHog, ClickHouse, Kafka/Redpanda, Redis, ZooKeeper и SeaweedFS нет. Имеющихся PostgreSQL и браузерных зависимостей достаточно для consent/API теста, но не для ingestion.
- `infra/posthog/docker-compose.posthog.yml` прямо объявлен metadata-only handoff; он не содержит полный ingestion pipeline. Его запуск не докажет доставку.
- Исследованы официальные [base](https://github.com/PostHog/posthog/blob/36259e3a58f40d0d09cbc98f179066a4addbb3db/docker-compose.base.yml), [hobby](https://github.com/PostHog/posthog/blob/36259e3a58f40d0d09cbc98f179066a4addbb3db/docker-compose.hobby.yml) и [dev](https://github.com/PostHog/posthog/blob/36259e3a58f40d0d09cbc98f179066a4addbb3db/docker-compose.dev.yml) Compose. Upstream master SHA прочитан через GitHub API: `36259e3a58f40d0d09cbc98f179066a4addbb3db`. Ранее скачанные `/tmp` копии не являются проверенным runtime и не считаются закреплёнными на этом SHA.
- Hobby/dev используют дополнительные source mounts, registry variables, floating image references и optional build services. Нельзя обрезать pipeline до HTTP stub/ClickHouse-only и назвать результат PostHog delivery. Совместимость закреплённых upstream app/node/capture образов с aarch64 ещё не проверена; эмуляция не разрешена по умолчанию.

## Ограниченная следующая операция, требующая разрешения

Установить официальный synthetic test runtime только в отдельный Docker project `graf-pr7477-synthetic`, из закреплённого source SHA выше. Нужен checkout официального PostHog и загрузка его отсутствующих образов/зависимостей. Это установка вне уже существующего набора зависимостей; здесь она не выполнялась.

Предлагаемый лимит одной попытки: не более 10 GiB сетевых загрузок, 20 GiB дополнительных файлов/томов, 4 CPU и 4 GiB совокупной памяти контейнеров, 45 минут runtime. До старта проверить image digests/architecture, полный capture → Kafka → ingestion → ClickHouse pipeline и ресурсный бюджет. Если official runtime не помещается или требует иных компонентов, остановиться с точной новой оценкой; не повышать Docker Desktop ресурсы, не отключать другие задачи, не переключать архитектуру и не скачивать floating latest по предположению.

Отдельная internal Docker network и только loopback ingress `127.0.0.1:18977`. Никаких production/shared volumes, runtime env files, пользовательских cookies, SSH к production, новых операторов, keys/PAT/grants и реальных данных. Runtime bootstrap допускает только upstream synthetic test fixtures с явно тестовыми несекретными значениями; создание настоящих учётных данных не входит в запрос. Если upstream требует аккаунт/ключ/внешний доступ сверх этого, остановиться. Не применять TTL DDL или purge даже на основании production retention approval. После попытки удалить только принадлежащие этому проекту контейнеры/сеть/тома; глобальный prune запрещён.

## Приёмочный сценарий после разрешённой установки

1. Через существующие GRAF consent/context/events и синтетическую auth fixture принять текущий test notice. Production readiness флаги не трогать; fixture approval явно test-only.
2. Записать пять разрешённых вех для двух synthetic users. Проверить серверный псевдоним, отсутствие content/IP/raw identifiers и запреты до согласия, после отзыва и при смене аккаунта.
3. Отправить capture через настоящий GRAF PostHog wrapper, без подмены provider transport. Сохранить status receipt, UUID и безопасные счётчики. `HTTP 200`/`status=1` остаются только capture acceptance.
4. Ограниченным опросом прочитать только fixture rows через ClickHouse в этом отдельном project. Сверить UUID/event/distinct_id и ожидаемые счётчики. Прямая вставка событий SQL не допускается.
5. Потерять ответ после настоящего capture, повторить тот же UUID и проверить readback/deduplication отдельно для raw rows и supported final query. Не объявлять exactly-once по одному ответу или client ledger.
6. Проверить отсутствие непустого `$ip`, IP/provider ingress-derived fields, GeoIP country/city/coordinates и PII в сохранённых fixture events. `$ip:null` и `$geoip_disable:true` в отправленном JSON сами по себе не дают runtime proof. Отдельно учитывать service ingress IP и свойства, добавленные ingestion.
7. Отчёт содержит pinned upstream/image identities, bounded resources, counts/dedup/readback verdict и cleanup receipt; не содержит payload/private data/credentials.

## Оставшиеся production шаги

Реальное сопоставление неизменённого notice с approved режимом; актуальные backup + isolated restore + offsite proofs; существующие operators и подтверждение MFA; отдельная secure secret-file wiring; exact 365-day retention assessment, dry-run/status, затем отдельное разрешение на DDL/purge. По переданному ops report production `78f9a12`: GRAF flags/host/key unset, project1 содержит 46 July events, retention84 months, TTL отсутствует, IP anonymization=false, 2 admins без подтверждённого TOTP. Эти факты не перепроверены и не исправлены этим срезом. D7/payment/refund остаются отдельной задачей.
