# Проверка F281

Lane: tiny-low-risk content, без нового data/API contract.

`PYTHONPATH="$PWD/apps/server/src" bash apps/server/scripts/run_local_postgres_tests.sh --focused tests/contract/test_public_mac_meeting_guide.py tests/unit/test_public_landing.py tests/contract/test_public_landing_contract.py -q`

Проверить нулевой diff protected templates/assets. Mobile widths 360/390/768: overflow 0, один H1, ссылка download. Production: только после exact-SHA CI и штатного full release candidate с backup/rollback.

Дополнение учебного протокола: включить `tests/contract/test_public_protocol_guide.py` и `tests/contract/test_copy_convention_contract.py` в focused disposable PostgreSQL набор. Проверить ручную/вымышленную маркировку, неизвестные сроки и Safari owner, порядок копируемого шаблона; Chromium 360/390/768 с реальными CSS/font. Выпуск только если текущий master не включает несогласованные изменения F282/runtime.

Hub: добавить `test_public_guides_hub.py`, `test_product_analytics_anonymous_aggregate_contract.py`, `test_public_traffic_measurement_contract.py` к focused suite. Проверить ровно одну новую footer строку, unchanged download/policies/assets, обе article URLs и breadcrumbs/related links. Mobile360390768 — hub/cards/guide links, keyboard focus и skip link. Не публиковать foreign billing при неподтвержденном baseline.

Проверка hub в изолированной среде: 23 PostgreSQL контракта PASS, контейнер удален; HTML guides regressions6 PASS. Chromium360/390/768/1440: overflow0, одинH1, две карточки, первый фокус skip-link. Источник лендинга при удалении новой footer-строки побайтово равен baseline; download/policies/landing assets zero diff. Выпуск T007 пока не подтвержден: чужой draft v2026.10.02.1 должен стать отдельным verified baseline.
