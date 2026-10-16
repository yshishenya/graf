# Quickstart

Свежая disposable копия origin/master; desktop и production test accounts не запускать. Перед окружением на Mac проверено 104 GiB свободно.

1. В apps/server: `UV_PROJECT_ENVIRONMENT=/tmp/graf-f289-venv uv sync --frozen --extra dev --extra evaluation`. Временную среду удалить после проверки, сохранить только журналы.
2. Из корня: `UV_PROJECT_ENVIRONMENT=/tmp/graf-f289-venv bash apps/server/scripts/run_local_postgres_tests.sh --focused -q tests/contract/test_public_organic_measurement.py tests/contract/test_public_zoom_recording_guide.py tests/contract/test_public_search_pages.py tests/contract/test_public_guides_hub.py tests/contract/test_public_landing_contract.py tests/unit/test_public_analytics.py tests/unit/test_public_visit_attribution.py tests/unit/test_product_analytics_anonymous_aggregate.py tests/contract/test_product_analytics_anonymous_aggregate_contract.py tests/contract/test_product_analytics_registration_handoff_contract.py`.
3. Ruff изменённых Python, `git diff --check`, `python3 scripts/check-development-process.py`, `python3 scripts/check_spec_kit_governance.py`, `python3 scripts/validate-changelog-fragments.py`.
4. Четыре пути: 2 GET → requests=2; organic/referral/direct; automated отдельно; unsafe UTM rejected; текущий путь против существующего cookie; нет L2/новых cookies/scripts. Kill switch, отключение уровня/отзыв основания, DB down → 200 без записи. Templates/static/sitemap/default optional inventory неизменны.
5. Независимый review/converge. Локальное PASS не заменяет commit approval, exact-SHA PR checks или frozen release-full/deploy. Рост не заявлять.

6. FR-008: unit8cases — зависшие execute/commit, подготовка/cleanup, handler
дольше250мс и внешняя отмена. Настоящая PostgreSQL: pg_sleep при подготовке
и записи всех4маршрутов → HTML200; следующая запись восстанавливается
(только ей в тесте дан запас2с). Регистрация с зависшим счётчиком сохраняет
аккаунт. Соседние шаги/доставка установщика проверяются полным handoff-файлом.
На текущем Mac reuse существующей среды без установки зависимостей:
`UV_NO_SYNC=1 UV_PROJECT_ENVIRONMENT=/Users/yshishenya/Documents/crisp/apps/server/.venv`.
Контейнер изолированный, runner удаляет его по завершении.
7. `python3 docs/growth/check-evidence-manifest.py` проверяет SHA-256 и полноту
снимка diff относительно записанной базы. Manifest пересоздаётся последним.

8. FR-001/003, T006: оба конструктора уровня 2 отвергают четыре пути;
корректно сформированный поддельный cookie с каждым таким landing_path на
GET /download не создаёт public_visit_attributions или acquisition и
не возвращает сохранённые метки. Все четыре бакета уровня 1 продолжают
записываться. Включить также tests/unit/test_product_analytics_acquisition.py
и tests/contract/test_public_traffic_measurement_contract.py.
