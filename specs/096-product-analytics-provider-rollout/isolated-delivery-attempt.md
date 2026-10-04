# Разрешённый PostHog стенд: bootstrap BLOCKED, доставка не доказана

Попытка 03.10.2026 UTC, draft PR7477 / issue7472 / T109. Подготовка GRAF основана на `b499eb196fdeabdb559fc76bc3688bfbd4b88d43`; продуктовый код этим отчётом не меняется. Risk lane — существующий high-risk096; эта дельта содержит только документы/metadata. [Машинный receipt](validation/isolated-posthog-attempt.json), [план](isolated-delivery-plan.md), [operator handoff](minimal-funnel-operator-handoff.md).

## Что действительно выполнено

После прямого разрешения загружены official source и 11 ARM64 images по digests. Отдельный internal Docker project, только loopback ingress, статические public upstream test fixtures, readonly source mounts и ограниченные RAM/CPU/logs. No production/shared volumes, production cookies/credentials, новых реальных keys/operators/grants, host packages или auth bypass. Широкий hobby installer не запускался.

PostgreSQL/Redis/ClickHouse/ZooKeeper/storage запущены; Kafka initialization завершилось. Canonical dev users file совместим со штатной restrictive autoresearch init policy; policy не удалялась и новые ручные grants не выдавались. Официальный migration command последовательно выполнял scopes, но PostgreSQL bootstrap не завершился: 3029 применённых migrations, два исчерпанных retry, killed process/OOMKilled. ClickHouse/persons scopes и marker успеха отсутствуют. Capture/ingestion/personhog/team fixture и GRAF end-to-end сценарий не запускались.

**Фактических capture requests — 0. Delivery, provider dedupe и persisted no-IP остаются NOT VERIFIED.** Не было HTTP200, прямой SQL-вставки аналитических событий или fake-provider readback. Уже существующие consent UI/API и 30 Swift checks остаются отдельным доказательством; они не подтверждают ingestion.

## Ресурсы и cleanup

Окно 21:27–22:57 UTC; остановка22:37:29, final cleanup22:42:46 — до 90-минутного предела. Download upper bound4,10GiB из6 (включает целый extra Node allowance после разрыва); disk upper bound11,17GiB из20 (повторно учитывает shared image layers). Caps≤4CPU/7040MiB из10GiB. Наблюдались MemAvailable425932KiB и SwapFree196KiB; OOM receipt не устанавливает исключительно глобальную причину.

Desktop8092MiB и daemon не менялись: restart опасен для исходного AutoRemove контейнера. Own 9 containers/9 volumes/1network/11 pinned references и source cache удалены; project-filter queries пусты. No force/global prune. Исходные и используемые shared images защищены.

Нельзя утверждать, что все15 исходных IDs сохранены. Семь GRAF Dev IDs исчезли и заменены новыми, AIRIS candidate exited0/OOM=false; эта попытка не выполняла их stop/recreate, snapshots не идентифицируют внешнего actor. На финальном независимом read-only snapshot шесть GRAF Dev healthy, maintenance running; исходный AutoRemove running с прежним StartedAt/OOM=false. Не пытались восстановить старые IDs поверх текущей чужой работы.

## No-IP и следующие gates

В [официальном event normalization](https://github.com/PostHog/posthog/blob/36259e3a58f40d0d09cbc98f179066a4addbb3db/nodejs/src/common/utils/event.ts) отсутствующий `$ip` может заполняться IP соединения; [ingestion prepare](https://github.com/PostHog/posthog/blob/36259e3a58f40d0d09cbc98f179066a4addbb3db/nodejs/src/ingestion/common/steps/event-processing/prepare-event-step.ts) удаляет его при `team.anonymize_ips=true`. Это source finding, а не runtime no-IP proof. Synthetic true fixture подготовлена, но не выполнена. Переданный production false — отдельный блокер, config не менялся.

T109 остаётся открытым. Для следующего стенда нужно отдельное безопасное окно RAM без потери AutoRemove workload; детали bounded proposal в плане. Production требует реальных ops proofs и отдельных secure actions; synthetic readiness файлы не заменяют backup/restore/offsite/MFA/retention evidence. Retention365, установленный native путь/release, D7/payments/refunds не переаттестованы.

Независимый read-only reviewer подтвердил корректность BLOCKED границы и own cleanup; reviewer-owned totals неизменны minimal8/0, provider52/0. Требуемые governance-fast/macos-pr/pr-metadata сверяются common validator на final pushed SHA; этот отчёт не подменяет CI.
