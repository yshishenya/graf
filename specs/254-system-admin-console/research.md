# Исследование технических решений

Дата 2026-09-06, база `a389657e607ef8389fcf947b26b158cee6928884`. Проверены текущие исходники, не production. Продуктовая карта источников — [research-and-readiness.md](research-and-readiness.md). Отдельные исследовательские проходы: admin_access — auth/RLS/egress/processing/deletion; diagnostics — billing/catalog/renewal/promo/usage. Оба только чтение, без выполненных runtime-тестов.

| Решение | Основание в коде | Почему / рассмотренная альтернатива |
|---|---|---|
| Отдельные principal/session | auth/context.py, auth/dependencies.py; db/models/federated_auth.py | AuthSession требует workspace/user; расширение обычной сессии создаёт ложного tenant. Переиспользуем только token/CSRF primitives |
| Отдельный ASGI-процесс и роль, system_control schema | db/session.py, db/tenant_context.py; scripts/bootstrap_runtime_database_roles.py; migration 0084_processing_recovery_maintenance.py | Public default privileges дают app/maintenance DML. Новый schema и ограниченные policies не смешивают секреты. Один public процесс с обоими DB secrets отвергнут |
| Явный system actor, не UUID в actor_user_id | db/models/admin.py, cabinet/egress.py, deletion/service.py | Existing FK на user identity; добавить operation reference и отдельный audit |
| Повторное использование egress с новой проверкой | cabinet/egress.py, `_refresh_egress_access`, `create_content_export`, `download_artifact` | Сохраняет revision/deletion gates; старый shortcut state=admin недостаточен |
| Общий dispatch reprocess | api/processing.py `_dispatch_created_processing_attempt`; processing/store.py `create_processing_attempt` | Сохраняет durable commit до Temporal и квоту. Новый прямой workflow start отвергнут |
| Точная saga удаления | deletion/service.py `request_meeting_deletion`; auth/account_closure.py | Существующий epoch/fence/purge, без самостоятельных DELETE по таблицам |
| Версия возможностей + таблица цен | billing/catalog.py; db/models/billing.py | UNIQUE(plan_code,version) и одна cycle в старой строке; новые month/year prices поддерживают одну версию, legacy IDs остаются |
| Закреплённое продление | billing/renewal_charge.py, entitlements.py, subscription.py, renewal_resolution.py | Current latest personal selection нарушает FR-045; pin из invoice snapshot, не current catalog |
| Отдельные административные adjustments | billing/referral_rewards.py; TimeCreditLedgerEntry | Paid grant требует payment/invoice; referral helper содержит специфические limits/aging. Подарок не должен наследовать эти условия |
| Schedule version отдельно от recurring consent | billing/renewal_charge.py, entitlements.py | Изменение consent version при gift способно отвергнуть позднюю оплату; отдельные версии сохраняют смысл |
| Reservation allocations по источникам квоты | billing/usage.py, storage.py | Сегодня 18000 seconds constant; новый resolver не обнуляет расход/резерв при смене тарифа |
| Новая promo попытка вместо повторного использования строки | migrations/versions/0081_secure_promotion_counter_function.py; cabinet/web_routes/billing.py | Trigger reserved→terminal не покрывает released/expired→reserved. Новые immutable attempts и пересчёт counters обязательны |
| Internal links, safe snapshots | support/redaction.py; DesktopUploadCustodyProjection.swift | Внешний отчёт использует fingerprints, не авторизацию; внутренний verified index не расширяет внешние поля |
| Каталог/агрегаты поверх Postgres | product_analytics/event_catalog.py, readiness.py; admin/metrics.py | 6 activation milestones и active memberships не DAU. Новый data warehouse/SaaS не нужен; false rollout flag не обходится |

## Обязательная карта billing consumers

Динамический plan code должен пройти `billing/catalog.py`, `entitlements.py`, `subscription.py`, `renewal_resolution.py`, `renewal_charge.py`, `maintenance.py`, `usage.py`, `storage.py`, `storage_addons.py`, `promotions.py`, `referral_rewards.py`, `public/offers.py`, `cabinet/web_routes/billing.py`, `api/auth.py` и все callers `entitlement_for_plan/effective_plan_code`. Поиск hard-coded personal/free/trial выполняется с семантической классификацией: `Workspace.kind=personal` сохраняется. Старые referral/grant semantics не переименовываются автоматически.

## Принятые технические пределы

Сроки сессий/кодов, очередей и хранения из нормативных приложений; дополнительные параметры security/API конкретизированы контрактами. Для клиентской нагрузки эталон: Apple Silicon M1, 8 GiB, поддерживаемая текущим release macOS, 60 min одинакового синтетического system-audio+mic сигнала, сравнение отключённой/включённой телеметрии в трёх прогонах, те же build/фоновые условия; CPU delta<=1 percentage point, память<=20 MiB. Intel/macOS variants из действующей QA-матрицы проходят функциональную совместимость отдельно.

Support snapshot cap: 100 на обращение за сутки и 1000 сохранённых снимков; duplicate hash не создаёт новый снимок. При достижении предела сохраняются первый, последний и переходы состояния, однотипные промежуточные coalesce; count потерь видим. Срок 180 дней после закрытия/365 для открытого остаётся верхней границей. Audit не coalesce.

Сервер принимает <=100 events/256 KiB batch, <=1000 events/device/hour (плюс приоритетный ручной support report по существующему route); явный 429/backoff. Клиент retry exponential 5s→5min с jitter, срок очереди 7 дней, пределы memory/disk из telemetry. При overflow сохраняет loss counters в отдельном bounded summary. Финансовые события рождаются из durable server ledger и не зависят от этого лимита.

Агрегаты пересчитываются раз в 5 min за последние 7 суток из авторитетных deduplicated sources; client events старше 7 суток rejected. Задержка event_time>5min относительно received_at помечается; order в launch — sequence/monotonic duration. Кроме последних 7 суток каждый проход обновляет все открытые когорты до конца их собственного окна +7 дней допустимой задержки; входящее событие обновляет затронутую когорту независимо от возраста начального bucket. Проверять W4 на 35/42-й день и late event в разрешённом окне. Финансовые late corrections пересчитывают затронутый период независимо от 7 дней. Product cohorts остаются provisional до конца окна +7 дней; corrections versioned. Малые продуктовые группы <5 пользователей не раскрывают значения/детализацию для analyst; административный технический поиск работает по отдельному праву.

## Что не является результатом исследования

Не подтверждены production включённость аналитики, ресурсы стенда, существование всех исторических копий, успешность будущих миграций/тестов. Их проверка включена в tasks/quickstart. Архитектурных неизвестных, требующих выбора нового провайдера/стека, не осталось; изменение этих решений требует обновления плана, не молчаливого расширения реализации.
