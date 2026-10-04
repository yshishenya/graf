# Изолированная доставка PostHog: план и граница доказательств

Обновлено после разрешённой попытки 03.10.2026 UTC. Runtime delivery не подтверждён; [отчёт](isolated-delivery-attempt.md) и [metadata receipt](validation/isolated-posthog-attempt.json) сохраняют фактический результат.

## Закреплённый официальный путь

Upstream source `36259e3a58f40d0d09cbc98f179066a4addbb3db`: официальные [base](https://github.com/PostHog/posthog/blob/36259e3a58f40d0d09cbc98f179066a4addbb3db/docker-compose.base.yml), [hobby](https://github.com/PostHog/posthog/blob/36259e3a58f40d0d09cbc98f179066a4addbb3db/docker-compose.hobby.yml) и [dev](https://github.com/PostHog/posthog/blob/36259e3a58f40d0d09cbc98f179066a4addbb3db/docker-compose.dev.yml). Все 11 aarch64 images были загружены по конкретным ARM64 digests; upstream tag/revision/digest записаны раздельно. App image совпадает с source SHA, node/capture/personhog имеют свои официальные revisions. Их runtime-совместимость не доказана: bootstrap не завершён.

Выбран реальный event pipeline: GRAF default transport → официальный capture → Redpanda/Kafka → официальный ingestion-general/personhog → ClickHouse. PostgreSQL, Redis, ZooKeeper и SeaweedFS — его disposable зависимости. Не использованы HTTP stub, прямая SQL-вставка событий, worker/replay/browserless/AI/Temporal services или широкий hobby installer. Repository `infra/posthog/docker-compose.posthog.yml` остаётся metadata-only handoff, не готовым runtime.

Сеть `graf-pr7477-synthetic` internal, отдельный непересекающийся subnet; единственный ingress — loopback `127.0.0.1:18977`. Readback предполагался через Docker exec только fixture rows, без публикации ClickHouse. Официальные source mounts readonly; users-dev.xml и штатная restrictive autoresearch policy применены как upstream dev fixtures, без ручных grants или auth bypass. Runtime migrations использовали штатные postgres/clickhouse/persons scopes; до последних двух выполнение не дошло.

## Разрешение и результат

User разрешил одну попытку: 90 минут, ≤6 GiB загрузок, ≤20 GiB дополнительного диска, ≤4 CPU/10 GiB container RAM; допускаемый Desktop RAM 16 GiB с restart. Фиксированное окно: 21:27–22:57 UTC. Bootstrap остановлен в 22:37:29, финальный cleanup receipt — 22:42:46 UTC. Продления и второй попытки не было.

Desktop остался 8092 MiB: исходный detached контейнер `AutoRemove=true` мог быть удалён при выходе daemon, поэтому restart/RAM change не выполнены. Runtime caps ограничены 4 CPU/7040 MiB; консервативно downloads≤4,10 GiB, disk≤11,17 GiB. Официальный PostgreSQL bootstrap достиг 3029 применённых migrations, но два retry исчерпаны после убийства процесса. OOMKilled и малые MemAvailable/swap подтверждены; cgroup limit и global OOM не разделены. Core services/Kafka initialization успели запуститься, capture/ingestion/team fixture — нет. HTTP200, delivery, no-IP и provider dedupe не заявлены.

Удалены только own 9 containers, 9 volumes, network, 11 новых pinned image references и скачанный source cache. Shared initial/used images защищены, global prune не применялся. Действия этой попытки не останавливали и не пересоздавали shared контейнеры. Все 15 исходных IDs не сохранились: семь GRAF Dev заменены, AIRIS candidate exited0/OOM=false; actor по snapshots не установлен. Текущие GRAF Dev: шесть healthy, maintenance running; исходный AutoRemove контейнер имеет прежний StartedAt/OOM=false.

## Условие следующего окна

Требуется безопасное согласованное окно с достаточной свободной RAM. Владелец AutoRemove workload должен сначала завершить его штатно либо отдельно согласовать проверенный способ сохранения; чужую работу нельзя пересоздавать ради стенда. После этого возможна одна новая ограниченная попытка: Desktop16 GiB, ≤4 CPU/10 GiB container RAM, ≤6 GiB downloads/20 GiB disk, ≤90 минут, только тот же pinned disposable project с own cleanup. Нынешнее разрешение не продлевается и новая попытка не начата. Установка host packages, новая архитектура, внешняя VM/access, новые реальные credentials/operators/grants требуют отдельного bounded approval.

## Приёмочный сценарий после успешного bootstrap

1. Existing GRAF consent/context/events, настоящие synthetic auth/session/device fixtures; test-only readiness явно не operational proof. Upstream public inert test token, без новых реальных ключей/операторов. Production не участвует.
2. Пять вех для двух synthetic users; server account milestone, псевдонимы и запреты до согласия, после отзыва, stale copy и forged identity.
3. Настоящий default PostHog transport; реальный capture receipt отдельно от delivery. Потеря ответа после actual acceptance — явно fault injection, затем повтор того же UUID.
4. ClickHouse raw и supported FINAL query: точные UUID/event/distinct_id, counts до/после retry; не count(DISTINCT) и не claim exactly-once по client ledger.
5. Persisted event/person properties: непустые IP и ingress-derived поля, GeoIP и PII/content отсутствуют. `$ip:null/$geoip_disable:true` недостаточны. Synthetic `anonymize_ips=true` — условие теста, не изменение production. Необязательную negative canary исключать из основной выборки точным UUID/identity.
6. Metadata-only receipt с source/digests/resources/counts/verdict/cleanup; никакого purge для подготовки proof.

## Оставшиеся production шаги

Legal mapping неизменённого notice; актуальные backup + isolated restore + offsite proofs; существующие operator access и MFA; отдельные secure capture-key wiring и IP anonymization config/readback; exact365-day retention assessment/dry-run/status, затем отдельное approval на необратимые TTL/purge действия. По переданному report production78f9a12: GRAF flags/host/key unset, project1 содержит46 July events, retention84 months/noTTL/anonymize_ips=false,2admins без подтверждённого TOTP. Это не перепроверялось и не исправлялось. D7/payment/refund — отдельный scope.
