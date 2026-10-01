# Учебный протокол: проверка дополнения F281

Lane: tiny-low-risk content. Один фиксированный публичный маршрут `/guides/protokol-vstrechi-iz-zapisi`, существующий renderer/canonical, отдельный шаблон и дополнительный CSS только новой страницы. Нет data API, новых аналитических событий, auth, AI pipeline, migrations или внешних providers.

Baseline: `14fa81f4f`, после опубликованного `v2026.10.01.1` только release closeout docs. F282/PR7400 open/unmerged и относится к другим маршрутам; его главная/ссылки в пакет не входят. Защищенные landing/download/policy templates/assets и первый guide без diff.

Текст получен от редактора. Вымышленный диалог и вручную составленный протокол маркированы до примера и в его заголовке. 13 ноября 2026 15:00 по Москве — срок Алексея; срок Ирины не согласован и начинается после получения макета; Safari owner не назначен; 16 ноября остается предложением. Нет оценки точности, клиентского кейса, результата фактического ГРАФ или выдуманной Article schema/date.

Focused disposable PostgreSQL: `test_public_protocol_guide.py`, `test_public_mac_meeting_guide.py`, `test_copy_convention_contract.py`, `test_public_landing.py`, `test_public_landing_contract.py` — **96 passed**, 8.67 s; контейнер удален. Ruff changed Python, development-process и `git diff --check` — PASS.

Chromium с реальными CSS/Onest: 360/390/768 — width=scrollWidth, один H1, три адаптивных task blocks, pre без переполнения, копируемый текст сохраняет переносы; synthetic/manual notice присутствует. Снимок 390 просмотрен. Metadata/canonical/og:url/query removal, sitemap uniqueness, links/anchors и no scripts/noindex проверены контрактом. Сам материал без JS.

Exact-SHA PR gates и штатный Full CI остаются обязательными. Перед merge/release повторно проверить master и competing runs; не включать несогласованные billing/runtime/F282 изменения. Production readback и фактическая индексация пока не подтверждены.
