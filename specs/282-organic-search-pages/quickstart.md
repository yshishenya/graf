# Quickstart

## Preparation

Из корня фичи использовать `uv sync --frozen --extra dev` в apps/server при отсутствии готовой среды. Для тестов с БД использовать только существующий disposable PostgreSQL runner, не production. Браузерный preview — отрендеренные шаблоны TestClient без analytics и БД; desktop app не запускается.

## Checks

`python3 specs/282-organic-search-pages/scripts/check_landing_preserved.py` — одноразовая приёмка F282, не постоянная CI-заморозка будущего лендинга.

1. `cd apps/server && uv run --extra dev ruff check src/twobrain_rec_server/public/web.py tests/contract/test_public_search_pages.py`
2. `bash apps/server/scripts/run_local_postgres_tests.sh --focused -q tests/contract/test_public_search_pages.py tests/contract/test_public_landing_contract.py tests/contract/test_public_mac_meeting_guide.py tests/unit/test_public_landing.py tests/unit/test_public_analytics.py tests/unit/test_public_visit_attribution.py`
3. Браузер на 320, 390, 768, 1440: все три новые страницы, отсутствие горизонтального переполнения и скрытых CTA, фокус/skip-link и без JS. До/после first screen главной одинаков при одинаковом контексте; footer links доступны. Сохранить только синтетический preview.
4. `git diff --check` и `python3 scripts/check_spec_kit_governance.py`, `python3 scripts/validate-changelog-fragments.py` (актуальный интерфейс предварительно через --help).
5. Независимое ревью требований перед implement; analyze без critical/high; issue sync до implement. Converge после тестов.

## Expected results

Три страницы 200, метаданные/ссылки/sitemap/404 по контракту, canonical не меняется от query/Host; исходный лендинг сохранён за вычетом footer links. Аналитические проверки подтверждают существующий consent и запрет расширения поверхностей.

## Release and outcome

Локальное PASS не означает merge/release/трафик. Коммит требует явного разрешения, GitHub checks привязываются к полному SHA и checked base; выпуск проходит отдельный release-full и approved deploy. Измерение после публикации описано в evidence/measurement-plan.md; текущая база unknown.
