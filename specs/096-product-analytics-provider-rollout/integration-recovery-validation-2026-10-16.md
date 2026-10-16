# Проверка совместимости F096 — 16.10.2026

Режим: действующий срез Spec Kit / high-risk-product. Основа d567a7dc51b0c4d99b22660d27950316ae609a66, перенос только diff draft a2bfee6b5ecb4e855cc96e9cc983195ff34adac8. Итоговое дерево пока не закоммичено. Старые результаты CI не относятся к этой интеграции.

## Причина и исправление

До исправления Alembic ScriptDirectory.get_current_head() завершился MultipleHeads: 0102_explicit_analytics_consent и 0104_summary_share_scope_cascade. Добавлена одна пустая объединяющая миграция 0105_merge_analytics_sharing с этими двумя родителями. Прежние ревизии сохранены. Два ожидания итоговой версии обновлены без удаления проверок master.

Один существующий интеграционный тест параметризован для0037,0104 sharing и0102 consent. На каждой исходной схеме создан синтетический пользователь; после обновления проверены его сохранность, NULL согласия, nullable JSON без default, таблицы sharing и прежние schema/security ожидания. Проверка единственной вершины после исправления — PASS.

## Исполненные проверки

- Основной набор: 96 PASS / 1 ERROR при подготовке browser test из-за отсутствующего GRAF_NODE_MODULES. Это ошибка окружения и не записывается как PASS. Включены весь test_postgres_migrations.py, worker schema guard, explicit consent/identity/retry/dedupe и provider gates.
- После указания существующих bundled Playwright/Chromium: весь test_explicit_consent_ui.py — 2 PASS, 0 SKIP. Настоящий headless Chromium, штатный notice, cookie-auth/CSRF FastAPI, временная PostgreSQL, два синтетических аккаунта, чтение сохранённого состояния. Провайдер событий подменён тестовым.
- Прежние PostHog/activation unit и contract tests, provider readiness blockers — 48 PASS, 0 SKIP.
- swift test --package-path apps/macos --scratch-path <temporary-build-directory> --filter ProductActivationAnalyticsContractTests — 30 PASS, 0 SKIP. Приложение не устанавливалось и не запускалось; GRAF Dev не менялся. Предупреждения в других существующих тестах не скрывают успешный результат выбранного набора.
- Ruff всего src/tests, JavaScript syntax, validate-agent-context, check-development-process, validate-changelog-fragments, git diff HEAD --check — PASS.
- Независимая проверка требований integration-recovery: 6 отмечено / 0 открыто; пять исторических списков прочитаны без переаттестации старых proofs. Проверка итогового кода записывается отдельно.

Команда основного набора: UV_PROJECT_ENVIRONMENT=<temporary-frozen-env> bash apps/server/scripts/run_local_postgres_tests.sh --focused -q tests/unit/test_explicit_product_funnel.py tests/integration/test_explicit_product_funnel.py tests/integration/test_explicit_consent_ui.py tests/unit/test_product_analytics_provider_delivery_gate.py tests/integration/test_product_analytics_provider_env.py tests/unit/test_playback_normalization_worker.py tests/integration/test_postgres_migrations.py. Для браузерного повтора указан GRAF_NODE_MODULES на существующие зависимости. Зависимости Python установлены uv sync --frozen --extra dev --extra evaluation.

PostgreSQL тестового runner удалён штатным cleanup. До подготовки свободно100 GiB; после проверки временные Python/Swift каталоги удалены, запас снова100 GiB. Журналы, контрольные суммы и отчёты сохранены.

## Граница результата

T109 и issue7472 открыты. HTTP receipt и тестовый провайдер не доказывают реальную запись PostHog/ClickHouse, отсутствие IP/GeoIP или срок365 дней. Поддерживаемый операторский доступ, legal mapping, точный новый SHA/base PR CI, проверка установленного native пути и выпуск остаются отдельными условиями. Production flags, ключи, MFA, TTL и история не менялись. Локальные результаты не означают готовность органической атрибуции, D7 или оплат.

## Разрешённый коммит и новая база16.10.2026

После локальной проверки и независимого ревью владелец прямо разрешил коммит и обновление существующего PR7477; включение рабочего провайдера и выпуск в разрешение не входят. На момент отправки master продвинулся до d75ba830c7a08621e9471ef62bf77b5bc66f80fb. Интеграционный коммит перенесён на эту базу без конфликтов; cmp полных binary diff до/после подтвердил побайтовую неизменность патча. Прочитанные independent-review source files не менялись.

Полный основной профиль повторён с уже подключённым Playwright/Chromium на новой базе:97 PASS,0 SKIP,2 прежних предупреждения,279.74s. Все migration tests, обе ветки и0037, настоящий browser consent, CSRF/identity/retry и provider gates пройдены. Collection digest e50258cd3ae3048c568e486557a9dc67a452c40bf0b380d05613bd6c7740af7a. Тестовый контейнер удалён штатным cleanup. Новых native source changes нет; обязательный native CI проверяет итоговый SHA/base заново. Старые CI исходного/промежуточного коммита не засчитываются.
