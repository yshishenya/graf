# Доказательства прогона quickstart — фича 273 «paid-traffic-analytics»

Это собранные фактические доказательства проверки по
`specs/273-paid-traffic-analytics/quickstart.md` для задачи T074: что именно
запускалось, что получилось и что осталось непроверенным.

## Повторная проверка 2026-09-20

Этот раздел является актуальным срезом после продолжения работы над Feature
273. Более подробная таблица ниже сохраняет исторические результаты прогона от
2026-09-19; если результаты расходятся, приоритет у этого раздела.

- **Рабочее дерево:** `/Users/yshishenya/Documents/crisp/.dsh-worktrees/paid-traffic-analytics`.
- **Ветка:** `273-paid-traffic-analytics`.
- **База дерева:** `eb67ca5b47e0e60e63dcde626ffbc2e6c25d921d`; дерево остаётся грязным,
  поэтому SHA является базой, а не доказанным снимком реализации.
- **P1 admission guard:** `bash apps/server/scripts/run_local_postgres_tests.sh --focused tests/contract/test_product_analytics_anonymous_aggregate_contract.py -q` — **16 passed**. Восемь конкурентных новых ссылок при лимите 3 создали ровно 3 durable-строки; после исчерпания квоты `/download` вернул `200`, независимый обезличенный агрегат не заблокирован.
- **Расширенный focused-набор после P1:** `bash apps/server/scripts/run_local_postgres_tests.sh --focused ... -q` — **141 passed**; проверены acquisition, legal-basis, public analytics, config и registration/app handoff paths.
- **Миграции:** `test_production_share_head_upgrades_to_regeneration_merge` и `test_product_analytics_migrations_downgrade_cleanly` — **2 passed**; `0097_public_attribution_admission_index` применился и откатился вместе с цепочкой Feature 273.
- **Связанные проверки головы схемы и retention-контракта:** **39 passed**; `ruff`, `compileall` и `git diff --check` — **pass**.
- **Provider smoke:** `bash infra/scripts/run-product-analytics-provider-smoke.sh` — **pass**.
  В синтетическом metadata-only окружении подтверждены `live_safe`-отправка
  PostHog, `live_safe`-загрузка Yandex Offline Conversions, readiness
  `approved`, dry-run rollback без изменения состояния и отсутствие секретов в
  выводе. Реальные провайдеры и реальные секреты не использовались; вывод
  smoke по-прежнему фиксирует `product_rollout=blocked` и
  `campaign_launch=blocked`.
- **Контракты provider smoke:** 3 теста пройдено.
- **Модульные тесты провайдеров и общего gate:** 27 тестов пройдено.
- **PostgreSQL-набор Feature 273:** 84 теста пройдено через
  `apps/server/scripts/run_local_postgres_tests.sh --focused`; изолированный
  контейнер удалён.
- **Расширенный доменный набор Feature 273:** 643 теста пройдено той же
  штатной обёрткой по всем `tests/unit/test_product_analytics_*.py`,
  `tests/contract/test_product_analytics_*.py` и
  `tests/integration/test_product_analytics_*.py`; контейнер удалён.
- **Проверка охвата страниц:** `provider_page_validation=pass`, проверено 30
  классов страниц.
- **Swift-контракты приложения:** 24 теста, 0 ошибок.
- **Браузерные тесты согласия:** `public-analytics-consent-modal.test.cjs` и
  `public-analytics-consent.test.cjs` — пройдены.
- **Полный браузерный набор:** и `node --test ./*.cjs`, и повтор с
  `node --test --test-concurrency=1 ./*.cjs` дали 12 пройдено и 8 упало на
  существующих несвязанных проверках текста/стенда (`meeting-results`,
  `mixed-meeting-list`, `playback-comments`, `recording-deletion-*`,
  `settings-autosave`, `settings-consistency`, `summary-format-picker`). Это
  не считается зелёной проверкой полного браузерного набора; аналитические
  файлы `public-analytics-consent-modal.test.cjs` и
  `public-analytics-consent.test.cjs` проходят отдельно.
- **Стиль и синтаксис:** `ruff`, `py_compile`, `git diff --check` — пройдены.
- **`infra/scripts/ci-local.sh --fast`:** не выдал доказательство из-за
  намеренно грязного worktree: `ci_evidence_status=ambiguous`,
  `reason=dirty_worktree`, код возврата 2. Нужен новый запуск на чистом
  точном SHA после разрешённого коммита.
- **Общий GRAF Dev:** `infra/scripts/dev-harness.sh status --json` прошёл, но
  активный manifest принадлежит Feature 274 (`feature_id=274`,
  `manifest_id=dev-a0d1a4278708`, `source_sha=a0d1a427870817c407af661bd73b31ec2c7d1fdd`).
  Стенд не переключался и приложение Feature 273 не устанавливалось: ручная
  приёмка этой фичи на текущем установленном `/Applications/GRAF Dev.app` не
  доказана.

Остаются непроверенными или недопустимыми для закрытия локальными фикстурами:
живой capacity baseline, production internal/trusted-peer evidence, реальные
операторы и MFA, рабочие dashboard definitions, живой rollback, владельцы
alert-каналов, сверка опубликованного consent-copy, GitHub checks на exact SHA,
`release-full`, deploy, notarization/stapling/Gatekeeper/Sparkle и установленное
приложение.

## Условия прогона

- **Дата прогона:** 2026-09-19, часовой пояс +05.
- **Рабочее дерево:** `/Users/yshishenya/Documents/crisp/.dsh-worktrees/paid-traffic-analytics`.
- **Ветка:** `273-paid-traffic-analytics`.
- **Коммит-основание исторического прогона:** `7f39ea9552ea7d7ea1d56e568ecaf43a27d7a0be`
  (2026-09-18, «[F271] Подготовка релиза 2026.09.18.3»), получен командой
  `git rev-parse HEAD`.
- **Коммитов этой фичи в дереве на момент исторического прогона нет.** Все изменения фичи 273 лежат в рабочей
  копии поверх коммита-основания: `git status --porcelain` показывает 137
  измененных или новых путей. Среди них новые файлы реализации
  (`apps/server/src/twobrain_rec_server/product_analytics/acquisition.py`,
  `apps/server/src/twobrain_rec_server/public/downloads.py`,
  `apps/server/src/twobrain_rec_server/db/models/product_analytics.py`,
  миграции `0094_anonymous_page_aggregate.py`, `0095_public_attribution.py` и
  `0096_client_attribution_bridge.py`) и
  новые тесты (`apps/server/tests/unit/test_product_analytics_*.py`,
  `apps/server/tests/contract/test_analytics_*.py`,
  `apps/server/tests/browser/public-analytics-consent.test.cjs`). Поэтому SHA
  выше — это база, а не снимок проверенного кода: проверялся код рабочей копии.
- **Секреты не записывались.** В этом файле нет токенов, паролей, адресов
  живых узлов и персональных данных. Значения вида `redacted_status_only` ниже
  приведены так, как их печатают сами скрипты.

## Как запускались проверки

Строки команд в quickstart написаны через `python -m pytest`. Часть отобранных
тестов требует базы, и без обертки они падают. Это проверено фактически:

```text
$ cd apps/server && PYTHONPATH=src uv run --extra dev pytest -q \
    tests/contract/test_public_traffic_measurement_contract.py
...
TWOBRAIN_DATABASE_URL is required; run bash apps/server/scripts/run_local_postgres_tests.sh
2 warnings, 9 errors in 0.13s
[exit code: 1]
```

Поэтому все серверные прогоны ниже выполнены через штатную обертку
`apps/server/scripts/run_local_postgres_tests.sh --focused ...`, которая поднимает
изолированный контейнер Postgres и удаляет его после прогона
(`postgres_test_cleanup=isolated_container_removed`). Чисто модульные файлы
обертка распознает сама и выполняет без контейнера — в логах это видно как
`postgres_test_cleanup=container_not_started`. Все прогоны завершились с кодом
возврата 0, ни один тест не упал и не был пропущен.

Проверки обезличенного счета, меток кампании, воронки и хранения запускались на
реальном коде и на реальной схеме базы в одноразовом контейнере. Это разбор
сохраненных записей, а не чтение кода, как и требует сценарий 1.

## Сводная таблица

| Сценарий | Что проверялось | Команда (из корня дерева) | Результат |
|---|---|---|---|
| 1. Обезличенный счет видит всех | В каждый визит попадает в агрегат; в записях нет адреса устройства, идентификатора сессии, строки агента и отпечатка | `bash apps/server/scripts/run_local_postgres_tests.sh --focused tests/unit/test_product_analytics_anonymous_aggregate.py tests/contract/test_public_traffic_measurement_contract.py -q` | **63 passed**, код 0 |
| 1 (дополнительно) | Охват всех публичных классов страниц; контракт измерения и агрегата | `bash apps/server/scripts/run_local_postgres_tests.sh --focused tests/integration/test_product_analytics_autocapture_pages.py tests/contract/test_product_analytics_measurement_contract.py tests/contract/test_product_analytics_anonymous_aggregate_contract.py -q` | **23 passed**, код 0 |
| 1 (инфраструктура) | Политика измерения по каждому классу страниц | `bash infra/scripts/validate-product-analytics-provider-pages.sh` | **pass**, классов проверено 30 |
| 2. Метки кампании переживают переходы | Метки доезжают до следующей страницы, остаются нормализованными, постоянная cookie не появляется | `bash apps/server/scripts/run_local_postgres_tests.sh --focused tests/unit/test_product_analytics_campaign_labels.py tests/unit/test_public_visit_attribution.py -q` | **35 passed**, код 0 |
| 3. Регистрация переносит кампанию | У записи о клиенте есть атрибут привлечения с исходной кампанией, правилом последнего непрямого источника и уровнем `linked` | `bash apps/server/scripts/run_local_postgres_tests.sh --focused tests/contract/test_product_analytics_registration_handoff_contract.py tests/unit/test_product_analytics_acquisition.py -q` | **36 passed**, код 0 |
| 4. Воронка активации | Все шаги несут исходную кампанию; повтор шага не удваивает счет; несвязанный шаг помечен `unknown`, а не `direct` | `bash apps/server/scripts/run_local_postgres_tests.sh --focused tests/unit/test_product_analytics_activation_funnel.py tests/unit/test_product_analytics_attribution_bridge.py tests/unit/test_product_analytics_milestone_dedupe.py tests/unit/test_product_analytics_unknown_vs_direct.py -q` | **63 passed**, код 0 |
| 4 (контракты приложения) | Контракты шагов активации, меток и надежности в приложении | `cd apps/macos && swift test --filter ProductActivationAnalyticsContractTests` | **23 tests, 0 failures**, код 0 |
| 5. Отказ соблюдается | После отзыва не уходит ни одного необязательного события; отказ соблюдается в следующий визит; обезличенный счет продолжает работать | `bash apps/server/scripts/run_local_postgres_tests.sh --focused tests/contract/test_public_analytics_consent_enforcement.py tests/unit/test_product_analytics_consent_copy_consistency.py -q` | **Старое evidence: 19 passed**; отдельный текущий запуск consent-copy: **18 passed**, код 0. Контрактный набор в этой рабочей копии требует `TWOBRAIN_DATABASE_URL`, поэтому без локального PostgreSQL не повторён полностью. |
| 5 (браузерный контроллер) | Реальный `analytics.js` в синтетической странице: нет решения, отказ, поврежденная запись, отзыв, сбой провайдера | `cd apps/server/tests/browser && node --test ./public-analytics-consent.test.cjs` | **1 файл, 1 pass, 0 fail**, код 0 |
| 6. Деградация измерения | Измерение отключается управляемо, продукт работает, оповещение со сроком 15 минут и разделением областей | `bash apps/server/scripts/run_local_postgres_tests.sh --focused tests/unit/test_product_analytics_degradation_order.py tests/contract/test_analytics_degradation_alerting.py -q` | **24 passed**, код 0 |
| 7. Хранение и восстановление | Сроки по категориям, копии и проверка восстановления, блокировка готовности | `bash apps/server/scripts/run_local_postgres_tests.sh --focused tests/unit/test_product_analytics_retention_rules.py tests/contract/test_analytics_retention_enforcement.py tests/integration/test_product_analytics_legal_basis_erasure.py -q` | **41 passed**, код 0 |
| 7 (дополнительно) | Блокировка готовности при отсутствии и устаревании копии | `bash apps/server/scripts/run_local_postgres_tests.sh --focused tests/integration/test_product_analytics_provider_readiness_blockers.py tests/contract/test_product_analytics_provider_retention.py -q` | **11 passed**, код 0 |
| 7 (инфраструктура) | Сухой прогон применения сроков хранения по категориям | `bash infra/scripts/enforce-product-analytics-retention.sh --dry-run` | **retention_result=dry_run**, код 0 |
| Общие команды quickstart | Измерение, агрегат, атрибуция, сквозные серверные сценарии | `bash apps/server/scripts/run_local_postgres_tests.sh --focused tests/unit/test_public_analytics.py tests/contract/test_public_analytics_contract.py -q` | **25 passed**, код 0 |
| Общие команды quickstart | Агрегат, привлечение и хранение в модульных тестах | `bash apps/server/scripts/run_local_postgres_tests.sh --focused tests/unit -k "aggregate or acquisition or retention" -q` | **116 passed**, 1895 deselected, код 0 |
| Общие команды quickstart | Сквозные серверные сценарии аналитики | `bash apps/server/scripts/run_local_postgres_tests.sh --focused tests/integration -k "analytics" -q` | **43 passed**, 1613 deselected, код 0 |
| Инфраструктура | Стек провайдеров, готовность, откат, отсутствие секретов | `bash infra/scripts/run-product-analytics-provider-smoke.sh` | **pass**, код 0 |

Итого фактически прогнано в этом файле: **281 серверный тест по семи сценариям**
(63 + 35 + 36 + 63 + 19 + 24 + 41), плюс **34 вспомогательных серверных теста**
(23 + 11), плюс **184 теста по общим командам quickstart** (25 + 116 + 43), плюс
**23 контрактных теста приложения** на Swift, плюс **1 браузерный прогон** с
шестью именованными проверками, плюс **3 инфраструктурных скрипта**.

---

## Сценарий 1 — обезличенный счет видит всех

**Что запускалось:**

```sh
bash apps/server/scripts/run_local_postgres_tests.sh --focused \
  tests/unit/test_product_analytics_anonymous_aggregate.py \
  tests/contract/test_public_traffic_measurement_contract.py -q
```

**Что получилось:** 63 теста пройдено, 0 упало. Разбор по файлам (получен
отдельным сбором через `--collect-only`): 54 теста в
`test_product_analytics_anonymous_aggregate.py` и 9 в
`test_public_traffic_measurement_contract.py`, что точно сходится с итогом 63.
Обертка подняла изолированный контейнер Postgres и удалила его:

```text
postgres_test_mode=focused worker_count=4 collection_count=63 collection_digest=cb273f726a69cee56646ebd84bfbc1b5c1ed7a96ae1ddddebd3f2f85c2f21a8c
63 passed, 2 warnings in 7.37s
postgres_test_phase=focused status=pass duration_seconds=11
postgres_test_result=pass mode=focused partitioned=false shard=none
postgres_test_cleanup=isolated_container_removed
```

Ключевые проверки, которые при этом прошли: `test_stored_aggregate_records_hold_no_identifier`
(в сохраненных записях агрегата нет идентификаторов), `test_every_public_page_is_counted_without_consent`
(каждая публичная страница считается без согласия), `test_buckets_below_the_minimum_size_are_not_disclosed`,
`test_excluded_traffic_classes_never_reach_reports` (внутренний, служебный,
тестовый и автоматический трафик не попадает в отчеты),
`test_a_public_visit_never_reaches_a_provider` и
`test_an_unavailable_provider_leaves_the_page_and_the_count_intact`.

**Дополнительно:** тот же сценарий подтвержден прогоном охвата классов страниц:

```sh
bash apps/server/scripts/run_local_postgres_tests.sh --focused \
  tests/integration/test_product_analytics_autocapture_pages.py \
  tests/contract/test_product_analytics_measurement_contract.py \
  tests/contract/test_product_analytics_anonymous_aggregate_contract.py -q
```

Результат — 23 теста пройдено (3 + 5 + 15 по файлам), контейнер удален.

**Инфраструктурная проверка страниц:**

```sh
bash infra/scripts/validate-product-analytics-provider-pages.sh
```

```text
provider_page_validation=pass
page_classes_checked=30
posthog_autocapture=declared_classes_only count=17
public_page_measurement_classes=public_landing,public_download,legal,login_signup
```

То есть измерение объявлено для всех четырех публичных классов страниц
(лендинг, загрузка, правовые документы, вход и регистрация), а автозахват
включен только там, где это разрешено политикой класса.

## Сценарий 2 — метки кампании переживают переходы

**Что запускалось:**

```sh
bash apps/server/scripts/run_local_postgres_tests.sh --focused \
  tests/unit/test_product_analytics_campaign_labels.py \
  tests/unit/test_public_visit_attribution.py -q
```

**Что получилось:** 35 тестов пройдено, 0 упало. Разбор по файлам: 27 тестов в
`test_product_analytics_campaign_labels.py` и 8 в
`test_public_visit_attribution.py` — сходится с итогом 35. База этим тестам не
нужна, поэтому контейнер не поднимался:

```text
postgres_test_mode=focused worker_count=4 collection_count=35 collection_digest=74ef8700e9cc13785575bd2ef7a032ce2503143c72e7c3dd42abf7c1eea9a932
35 passed, 2 warnings in 0.04s
postgres_test_phase=focused status=pass duration_seconds=3
postgres_test_result=pass mode=focused partitioned=false shard=none
postgres_test_cleanup=container_not_started
```

Ключевые проверки: `test_campaign_labels_survive_public_page_transitions_in_a_session_cookie`
(метки переживают переход между страницами в сессионной cookie),
`test_visit_attribution_keeps_the_last_non_direct_source_of_the_visit`
(правило последнего непрямого источника),
`test_a_visit_without_campaign_material_gets_no_cookie_at_all`
(без меток cookie не появляется вовсе — постоянной cookie слежения нет),
`test_safe_labels_are_kept_without_rewriting` и
`test_source_and_medium_are_lowercased_before_the_safety_check`
(нормализация меток перед проверкой безопасности),
`test_public_page_aggregate_bucket_carries_the_visit_campaign_only`
(в агрегате лежит только нормализованная кампания визита).

## Сценарий 3 — регистрация переносит кампанию

**Что запускалось:**

```sh
bash apps/server/scripts/run_local_postgres_tests.sh --focused \
  tests/contract/test_product_analytics_registration_handoff_contract.py \
  tests/unit/test_product_analytics_acquisition.py -q
```

**Что получилось:** 36 тестов пройдено, 0 упало. Разбор по файлам: 9 тестов в
`test_product_analytics_registration_handoff_contract.py` и 27 в
`test_product_analytics_acquisition.py` — сходится с итогом 36.

```text
postgres_test_mode=focused worker_count=4 collection_count=36 collection_digest=093dde2f4a00c2e03f815be613ae9bae9ff4e3af5153ef199b0b8911c45f7a0d
36 passed, 2 warnings in 7.15s
postgres_test_phase=focused status=pass duration_seconds=11
postgres_test_result=pass mode=focused partitioned=false shard=none
postgres_test_cleanup=isolated_container_removed
```

Ключевые проверки: `test_the_campaign_of_the_visit_reaches_the_client_record`
(кампания визита доходит до записи о клиенте),
`test_the_same_account_keeps_its_first_attribute_in_storage` (первый атрибут
привлечения не переписывается), `test_a_second_registration_never_rewrites_the_campaign`,
`test_a_registration_without_a_campaign_is_unknown_and_never_direct` и
`test_a_damaged_cookie_is_unknown_and_never_direct` (регистрация без кампании и
поврежденная cookie дают `unknown`, а не `direct`),
`test_every_step_of_web_registration_is_counted_with_its_campaign`.

## Сценарий 4 — воронка активации

**Что запускалось:**

```sh
bash apps/server/scripts/run_local_postgres_tests.sh --focused \
  tests/unit/test_product_analytics_activation_funnel.py \
  tests/unit/test_product_analytics_attribution_bridge.py \
  tests/unit/test_product_analytics_milestone_dedupe.py \
  tests/unit/test_product_analytics_unknown_vs_direct.py -q
```

**Что получилось:** 63 теста пройдено, 0 упало. Разбор по файлам: 10 + 10 + 16 +
27 = 63, сходится.

```text
postgres_test_mode=focused worker_count=4 collection_count=63 collection_digest=3531d51be748147b65d0b0498409475c4e577d61cd63f93c6231e0ed2141de9f
63 passed, 3 warnings in 0.92s
postgres_test_phase=focused status=pass duration_seconds=4
postgres_test_result=pass mode=focused partitioned=false shard=none
postgres_test_cleanup=container_not_started
```

Ключевые проверки: `test_the_funnel_carries_the_campaign_of_the_visit`
(каждый шаг воронки несет кампанию визита),
`test_a_milestone_is_counted_once_per_pseudonymous_user` и
`test_the_ingest_service_delivers_a_repeated_milestone_only_once` (повтор шага не
удваивает счет), `test_a_milestone_without_identity_is_counted_unlinked`,
`test_every_milestone_carries_exactly_one_reliability_level` и
`test_the_reliability_level_follows_the_campaign_link`,
`test_the_app_handoff_link_round_trips_labels_and_landing_path`,
`test_an_expired_bridge_no_longer_resolves`, а также набор
`test_product_analytics_unknown_vs_direct.py` (27 тестов), который проверяет, что
несвязанный шаг помечается `unknown`, а не `direct`.

**Контракты приложения** (шаг из раздела «Команды проверки» quickstart):

```sh
cd apps/macos && swift test --filter ProductActivationAnalyticsContractTests
```

```text
Test Suite 'ProductActivationAnalyticsContractTests' passed at 2026-09-19 03:19:28.015.
	 Executed 23 tests, with 0 failures (0 unexpected) in 0.038 (0.039) seconds
```

Проверки включают `testUnknownCampaignIsMarkedUnknownAndNeverDirect`,
`testRepeatedMilestoneIsNotCountedTwiceInTheApp`,
`testProductActivationEventNamesAreStable`,
`testHandoffLinkRoundTripKeepsCampaignAndHidesClickIdentifier` и
`testTelemetryGateBlocksNormalUseUntilAccepted`.

## Сценарий 5 — отказ соблюдается

**Что запускалось:**

```sh
bash apps/server/scripts/run_local_postgres_tests.sh --focused \
  tests/contract/test_public_analytics_consent_enforcement.py \
  tests/unit/test_product_analytics_consent_copy_consistency.py -q
```

**Что получилось:** старое evidence фиксирует 19 тестов, 0 упало. После T093
текущий focused запуск `test_product_analytics_consent_copy_consistency.py`
прошел: 18 тестов, 0 упало. Контрактный запуск с PostgreSQL в этой рабочей
копии не повторен без `TWOBRAIN_DATABASE_URL`.

```text
Старое repository evidence (до T093):
postgres_test_mode=focused worker_count=4 collection_count=19 collection_digest=60e4309b5eecb8999a062449d52ef016992cd656cbd2a3f541a6197fb1335fb5
19 passed, 2 warnings in 4.25s
postgres_test_phase=focused status=pass duration_seconds=7
postgres_test_result=pass mode=focused partitioned=false shard=none
postgres_test_cleanup=isolated_container_removed

Текущий T093 focused unit:
18 passed, 2 warnings in 1.01s
```

Ключевые проверки: `test_browser_controller_never_sends_an_optional_event_without_consent`,
`test_relay_refuses_an_event_without_a_valid_consent_decision`,
`test_a_damaged_consent_record_is_read_as_a_denial`,
`test_refusal_does_not_stop_the_anonymous_count` (после отказа обезличенный счет
продолжает работать), `test_relay_is_closed_while_public_measurement_is_disabled`
и `test_relay_is_closed_for_a_cross_origin_post`. Отдельный файл
`test_product_analytics_consent_copy_consistency.py` (18 тестов) проверяет
согласованность текстов согласия между сайтом, кодом и опубликованными
документами. Для repository docs каждая копия отдельно называет точную редакцию
`2026-09-15.1`; тесты stale/missing подтверждают, что одна копия не маскирует
другую. Внешние копии документов и сроки в кабинете провайдера остаются
операторскими подтверждениями и не выдаются за проверенные этим тестом.

**Браузерный прогон** (шаг из раздела «Команды проверки» quickstart):

```sh
cd apps/server/tests/browser && node --test ./public-analytics-consent.test.cjs
```

```text
ok no_decision_sends_nothing
ok refusal_is_kept_on_a_repeat_visit
ok damaged_decision_is_a_refusal
ok consented_event_uses_the_first_party_relay
ok revocation_stops_optional_sends
ok provider_failure_does_not_break_the_page
public_analytics_consent_harness=pass
✔ public-analytics-consent.test.cjs (498.762083ms)
ℹ tests 1
ℹ pass 1
ℹ fail 0
ℹ duration_ms 503.290834
```

Этот прогон исполняет реальный файл
`apps/server/src/twobrain_rec_server/public/static/public/analytics.js` в
синтетической странице (`vm`) без сети и без скрипта провайдера. Проверка
`refusal_is_kept_on_a_repeat_visit` покрывает шаг сценария «закрыть и открыть
браузер, вернуться на сайт» на уровне повторного визита с сохраненным решением,
но не через настоящий браузер — см. раздел «Что не проверено и почему».

**Замечание про `node_modules`:** каталог `apps/server/tests/browser/node_modules`
в этом дереве есть, в нем лежат `playwright` и `playwright-core` версии 1.63.0.
При этом сам проверяемый файл согласия Playwright не использует (он работает
через `node:vm`), поэтому прогон не зависел от браузерных бинарников. Остальные
файлы `tests/browser/*.cjs` к фиче 273 не относятся и в этом прогоне не
запускались.

## Сценарий 6 — деградация измерения

**Что запускалось:**

```sh
bash apps/server/scripts/run_local_postgres_tests.sh --focused \
  tests/unit/test_product_analytics_degradation_order.py \
  tests/contract/test_analytics_degradation_alerting.py -q
```

**Что получилось:** 24 теста пройдено, 0 упало. Разбор по файлам: 5 тестов в
`test_product_analytics_degradation_order.py` и 19 в
`test_analytics_degradation_alerting.py` — сходится с итогом 24.

```text
postgres_test_mode=focused worker_count=4 collection_count=24 collection_digest=58321b278e0a247f6e51b86e1b8ca1620808b1b9ad0898ae55bb5b22e21ec4fd
24 passed, 2 warnings in 6.86s
postgres_test_phase=focused status=pass duration_seconds=10
postgres_test_result=pass mode=focused partitioned=false shard=none
postgres_test_cleanup=isolated_container_removed
```

Ключевые проверки: `test_the_product_answers_over_http_while_measurement_is_disabled`
(продукт продолжает работать при отключенном измерении),
`test_the_guard_switches_off_measurement_and_nothing_else` (отключается только
измерение), `test_only_analytics_scope_reasons_may_disable_measurement` и
`test_guard_splits_analytics_and_host_scopes` (всплеск нагрузки на сайт не
отключает измерение, потому что причина не в аналитике),
`test_alert_suppresses_repeats_and_keeps_the_deadline_visible`,
`test_documentation_keeps_the_scope_split_and_the_delivery_deadline` (срок
доставки оповещения 15 минут зафиксирован в документации),
`test_alert_labels_a_mixed_breach_list_with_both_scopes`,
`test_every_alert_code_has_an_owner_rule` (владелец у каждого правила),
`test_alert_channel_outage_is_detected_independently`,
`test_alert_uses_the_fallback_transport_when_the_primary_channel_is_unavailable` и
`test_alert_drill_verifies_the_channel_without_a_degradation`.

**Честная пометка:** эти тесты проверяют контракт скриптов оповещения и защиты,
расписание юнитов и наличие срока 15 минут в документации. Фактического
срабатывания внешнего канала при остановленном узле аналитики не наблюдалось, и
искусственная нагрузка на сервер не создавалась. См. раздел «Что не проверено и
почему».

## Сценарий 7 — хранение и восстановление

**Что запускалось:**

```sh
bash apps/server/scripts/run_local_postgres_tests.sh --focused \
  tests/unit/test_product_analytics_retention_rules.py \
  tests/contract/test_analytics_retention_enforcement.py \
  tests/integration/test_product_analytics_legal_basis_erasure.py -q
```

**Что получилось:** 41 тест пройдено, 0 упало. Разбор по файлам: 11 + 24 + 6 = 41,
сходится.

```text
postgres_test_mode=focused worker_count=4 collection_count=41 collection_digest=d578931fd61589de868e918bf0c212b0197e2eb2e5bafd1a8bc9a16b34e157db
41 passed, 2 warnings in 23.41s
postgres_test_phase=focused status=pass duration_seconds=27
postgres_test_result=pass mode=focused partitioned=false shard=none
postgres_test_cleanup=isolated_container_removed
```

Ключевые проверки: `test_retention_terms_match_the_approved_contract`,
`test_event_ttl_statement_targets_the_storage_table_for_365_days`,
`test_retention_execution_deletes_by_age_and_logs_every_deletion`,
`test_retention_fails_closed_when_a_category_has_no_storage`,
`test_backup_archives_every_required_class_and_ships_one_copy_offsite`,
`test_backup_requires_an_offsite_destination`,
`test_backup_keeps_two_copies_and_deletes_older_ones_with_a_log`,
`test_backup_fails_closed_and_alerts_when_a_required_class_is_absent`,
`test_restore_verification_replays_a_stored_copy_without_touching_the_live_stack`,
`test_restore_verification_detects_a_corrupted_archive`,
`test_restore_verification_fails_when_no_copy_exists`,
`test_backup_state_contract_is_readable_by_readiness_and_alerting`, а также
`test_level_two_data_is_deleted_and_anonymised_within_the_term` и
`test_erasure_leaves_no_personal_data_in_the_evidence`.

**Дополнительно — блокировка готовности:**

```sh
bash apps/server/scripts/run_local_postgres_tests.sh --focused \
  tests/integration/test_product_analytics_provider_readiness_blockers.py \
  tests/contract/test_product_analytics_provider_retention.py -q
```

Результат — 11 тестов пройдено (9 + 2 по файлам), контейнер удален. Это покрывает
ожидание «состояние готовности заблокировано, если копии нет или проверка
устарела».

**Инфраструктурная проверка сроков хранения (сухой прогон):**

```sh
bash infra/scripts/enforce-product-analytics-retention.sh --dry-run
```

```text
retention_result=dry_run
event_retention_days=365
category=measurement_events retention_days=365 storage=clickhouse enforcement=row_ttl table_candidates="measurement_events" timestamp_column=created_at
category=anonymous_aggregate retention_days=1095 storage=postgres enforcement=scheduled_task table_candidates="product_analytics_anonymous_aggregate product_analytics_aggregate_buckets anonymous_aggregate product_analytics_aggregate" timestamp_column=bucket_date
category=visit_attribution retention_days=90 storage=postgres enforcement=scheduled_task table_candidates="product_analytics_visit_attribution visit_attribution product_analytics_visit_attributions" timestamp_column=expires_at
category=acquisition_attribute retention_days=1095 storage=postgres enforcement=scheduled_task table_candidates="product_analytics_acquisition_attribute product_analytics_client_acquisition_attribute acquisition_attribute customer_acquisition_attribute" timestamp_column=captured_at
database_service=rec-postgres
next_step=run_with_--execute_on_the_product_host
```

Сроки совпадают с ожиданием сценария: события старше 12 месяцев удаляются
(365 дней), агрегаты доступны до 36 месяцев (1095 дней). Скрипт сам печатает
следующий шаг — `run_with_--execute_on_the_product_host`, то есть применение на
живом узле не выполнялось.

## Общие команды из раздела «Команды проверки» quickstart

Три команды из quickstart прогнаны дополнительно, чтобы подтвердить, что
проверки сценариев не расходятся с общим набором:

```sh
# 25 passed
bash apps/server/scripts/run_local_postgres_tests.sh --focused \
  tests/unit/test_public_analytics.py tests/contract/test_public_analytics_contract.py -q

# 116 passed, 1895 deselected
bash apps/server/scripts/run_local_postgres_tests.sh --focused \
  tests/unit -k "aggregate or acquisition or retention" -q

# 43 passed, 1613 deselected
bash apps/server/scripts/run_local_postgres_tests.sh --focused \
  tests/integration -k "analytics" -q
```

Разбор первого прогона по файлам: 13 + 12 = 25, сходится.

**Инфраструктурный smoke-прогон провайдеров:**

```sh
bash infra/scripts/run-product-analytics-provider-smoke.sh
```

Завершился с кодом 0. Существенные строки вывода:

```text
posthog_stack_contract=handoff_valid
posthog_secret=redacted_status_only
posthog_secret_payload_rejected=pass
posthog_deploy_dry_run=pass
posthog_delivery=dry_run
posthog_live_safe_delivery=transport_verified
posthog_autocapture=current_pages_enabled
yandex_blocked_pages=pass
yandex_live_safe_upload=transport_verified
yandex_duplicates=dedupe_key_stable
dashboard_readiness=metadata_only_live_safe_verified
provider_blockers=legal_privacy_security_qa_disclosure_campaign_product_rollout_separate
product_rollout=blocked
campaign_launch=blocked
no_secret_scan=metadata_only_pass
private_payload_status=none_committed
rollback_status=metadata_only_not_executed
rollback_execution=metadata_only_no_state_change
rollback_live_mutation=not_claimed
```

Обратите внимание на последние строки: запуск платного трафика остается
заблокированным (`campaign_launch=blocked`), а smoke выполнил только
`--metadata-only`: состояние провайдера не менялось
(`rollback_execution=metadata_only_no_state_change`), живой откат не заявляется.

## Полная проверка перед снятием блокировки

Раздел quickstart «Полная проверка перед снятием блокировки» содержит пять
пунктов. Состояние по каждому на момент прогона:

| Пункт | Состояние по факту прогона |
|---|---|
| 1. Все сценарии пройдены и результаты записаны | Выполнено в этом файле: семь сценариев подтверждены прогонами, все завершились с кодом 0. |
| 2. Обязательные проверки GitHub прошли на точном SHA pull request | **Не выполнено.** Pull request для этой фичи не создавался, коммитов фичи нет, проверить нечего. |
| 3. Записи об одобрении зафиксированы, включая правовое подтверждение | **Не выполнено.** Это действие владельца и юриста, вне периметра прогона тестов. |
| 4. Путь отката отработан на живом сценарии, а не только описан | **Не выполнено.** Smoke выполнил только метаданный режим: `rollback_status=metadata_only_not_executed`, `rollback_live_mutation=not_claimed`; операторский hook и живой откат не запускались. |
| 5. Тексты согласия на сайте, в коде и в документах совпадают | **Подтверждено для repository docs.** `tests/unit/test_product_analytics_consent_copy_consistency.py` проверяет 18 тестов: каждая копия опубликованного документа отдельно называет точную редакцию `2026-09-15.1`, а stale/missing документ не маскируется объединённым текстом. Внешние копии документов и срок хранения в кабинете провайдера по-прежнему требуют операторского подтверждения и не выдаются за проверенные этим тестом. |

Снятие блокировки платного запуска, как и сказано в quickstart, выполняется
отдельным выпускным решением и в эту фичу не входит.

## Что не проверено и почему

Ниже честно перечислено все, что осталось непроверенным. Ни одна из этих
проверок не выдана за пройденную.

1. **Нагрузочная проверка и абсолютный объем хранилища (T076).** Не выполнялась.
   В `specs/273-paid-traffic-analytics/tasks.md` (строка 80) задача T076 остается
   неотмеченной: `- [ ] T076 [US1] Провести нагрузочную проверку и зафиксировать
   абсолютный объем хранилища и ожидаемую скорость роста (FR-039, SC-012)`.
   Причина: нужен живой стенд и оператор, создающий реальный трафик; в этом
   прогоне трафик не создавался. Контракт измерения роста хранилища покрыт
   тестом `test_storage_growth_measurement_reports_the_documented_keys`, но это
   проверка формы отчета, а не измеренный объем.

2. **Прогон в настоящем браузере.** В сценариях 1, 2 и 5 шаги описаны как ручные
   действия в браузере: открыть страницу в чистом профиле, закрыть и открыть
   браузер, вернуться на сайт. В этом прогоне вместо настоящего браузера
   использован синтетический прогон реального `analytics.js` в `node:vm`
   (`apps/server/tests/browser/public-analytics-consent.test.cjs`). Он проверяет
   поведение контроллера согласия, включая повторный визит с сохраненным
   решением, но не воспроизводит работу настоящего браузера, профиля, cookie
   jar и сетевого стека. Playwright 1.63.0 в
   `apps/server/tests/browser/node_modules` установлен, однако тест согласия его
   не использует, а других браузерных тестов по фиче 273 в дереве нет. Каталог
   `node_modules` в этом дереве присутствует, так что ограничение здесь не в
   отсутствии зависимостей, а в том, что подходящего браузерного теста для фичи
   не существует.

3. **Ручной прогон в приложении `/Applications/GRAF Dev.app`.** Приложение в
   этой сессии не собиралось (`infra/scripts/dev-harness.sh` не запускался) и не
   открывалось. Шаги сценария 4 «открыть приложение, подключить аккаунт, сделать
   первую запись, посмотреть результат» на живом приложении не выполнялись.
   Контракты приложения проверены статически через
   `swift test --filter ProductActivationAnalyticsContractTests` — 23 теста
   прошли, но это проверка контрактов, а не ручной сценарий в приложении.

4. **Фактическое срабатывание внешнего оповещения не позднее 15 минут.** Не
   наблюдалось. Узел аналитики не останавливался, деградация не имитировалась,
   живой внешний канал не задействовался. Подтверждено только контрактно:
   скрипт оповещения, разделение областей, подавление повторов, наличие срока
   15 минут в документации и владелец у каждого правила оповещения. Отдельно
   отмечу: `test_alert_dry_run_never_contacts_the_external_channel` прямо
   проверяет, что сухой прогон не трогает внешний канал, поэтому факт доставки
   этим тестом не доказывается по построению.

5. **Искусственная нагрузка на сервер (вторая часть сценария 6).** Не
   создавалась. Ожидание «всплеск нагрузки на сайт не отключил измерение,
   потому что причина не в аналитике» подтверждено только логикой разделения
   областей в тестах `test_guard_splits_analytics_and_host_scopes` и
   `test_only_analytics_scope_reasons_may_disable_measurement`.

6. **Реальная резервная копия на живом узле и фактическая проверка
   восстановления не позднее 30 дней назад.** Не выполнялись. Контрактные тесты
   `test_analytics_retention_enforcement.py` запускают `infra/scripts/backup-posthog.sh`
   и `infra/scripts/verify-posthog-restore.sh` на поддельных хостах и каталогах в
   `tmp_path`, то есть проверяют логику скриптов, а не состояние живого узла.
   Свежесть копии и давность проверки восстановления на продуктивном стенде не
   измерялись.

7. **Фактическое применение сроков хранения на живом узле.** Выполнен только
   сухой прогон `enforce-product-analytics-retention.sh --dry-run`; скрипт сам
   печатает `next_step=run_with_--execute_on_the_product_host`. Режим `--execute`
   на продуктивном узле не запускался, поэтому фактического удаления событий
   старше 365 дней и агрегатов старше 1095 дней не наблюдалось.

8. **Путь отката на живом сценарии.** Не отрабатывался. Smoke-прогон сообщает
   `rollback_status=metadata_only_not_executed`. Это прямой пункт 4 раздела «Полная
   проверка перед снятием блокировки», и он остается открытым.

9. **Проверки GitHub на точном SHA pull request.** Не выполнялись, потому что
   pull request для фичи не создавался и коммитов фичи в дереве нет. В этом
   прогоне SHA `7f39ea9552ea7d7ea1d56e568ecaf43a27d7a0be` — это коммит-основание,
   а изменения фичи лежат в рабочей копии.

10. **Записи об одобрении и правовое подтверждение.** Не собирались: это
    действие владельца продукта и юриста, а не автоматическая проверка.

11. **Сценарий 7, часть «копия выгружена за пределы измеряемого узла».** В
    тестах подтверждено, что скрипт требует внешний получатель и падает закрыто
    без него (`test_backup_requires_an_offsite_destination`), но фактическая
    выгрузка копии за пределы узла не производилась.

12. **Остальные файлы `apps/server/tests/browser/*.cjs`.** Строка quickstart
    `node --test ./*.cjs` запускает все браузерные проверки дерева, включая
    воспроизведение записей, удаление, настройки и календарь. Они не относятся к
    фиче 273 и в этом прогоне не запускались; запускался только файл согласия.
