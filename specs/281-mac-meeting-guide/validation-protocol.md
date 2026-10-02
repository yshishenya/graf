# Учебный протокол: проверка дополнения F281

Lane: tiny-low-risk content. Один фиксированный публичный маршрут `/guides/protokol-vstrechi-iz-zapisi`, существующий renderer/canonical, отдельный шаблон и дополнительный CSS только новой страницы. Нет data API, новых аналитических событий, auth, AI pipeline, migrations или внешних providers.

Baseline: `e9d34cf349a6bc2248a9d4e206138fd77dee9c56`, опубликованный `v2026.10.01.2`; чужая выкладка не входит в этот diff. F282/PR7400 open/unmerged и относится к другим маршрутам; его главная/ссылки в пакет не входят. Защищенные landing/download/policy templates/assets и первый guide без diff.

Текст получен от редактора. Вымышленный диалог и вручную составленный протокол маркированы до примера и в его заголовке. 13 ноября 2026 15:00 по Москве — срок Алексея; срок Ирины не согласован и начинается после получения макета; Safari owner не назначен; 16 ноября остается предложением. Нет оценки точности, клиентского кейса, результата фактического ГРАФ или выдуманной Article schema/date.

Focused disposable PostgreSQL: `test_public_protocol_guide.py`, `test_public_mac_meeting_guide.py`, `test_copy_convention_contract.py`, `test_public_landing.py`, `test_public_landing_contract.py` — **96 passed**, 8.67 s; контейнер удален. Ruff changed Python, development-process и `git diff --check` — PASS.

Chromium с реальными CSS/Onest: 360/390/768 — width=scrollWidth, один H1, три адаптивных task blocks, pre без переполнения, копируемый текст сохраняет переносы; synthetic/manual notice присутствует. Снимок 390 просмотрен. Metadata/canonical/og:url/query removal, sitemap uniqueness, links/anchors и no scripts/noindex проверены контрактом. Сам материал без JS.

Exact-SHA PR gates и штатный Full CI остаются обязательными. Перед merge/release повторно проверить master и competing runs; не включать несогласованные billing/runtime/F282 изменения. Production readback и фактическая индексация пока не подтверждены.

Исправление review: только новый route зарегистрирован в существующих inventories и передает PublicWebDbDependency. Шаблон без analytics JS; providers/replay/ingestion/consent/env не изменены. Disposable PostgreSQL test проверяет L1 bucket, идемпотентный campaign reference, перенос source/landing в download, отсутствие secret query и L1-off brake. Campaign bookkeeping использует прежний local legal-basis gate, не optional provider consent.

Focused measurement suite: 27 passed, 10.35 s; disposable container removed. Ruff, development-process и diff whitespace — PASS.

Первый frozen Full 36922903347 выявил устаревший exact surface inventory contract: добавлен public_protocol_guide в ожидаемый закрытый список. Отдельная ошибка browser focus существующего consent modal исследуется без изменения интерфейса/политик. Production еще не менялся.

Consent focus failure reproduced as a harness readiness race: vendored library schedules initial focus after 100 ms, while test waited only for DOM. Harness now waits for initial focus inside modal before keyboard assertions, preserving the assertion and real refusal behavior. Product JS/CSS/copy unchanged. Focused repair suite initially 28 passed including real modal; rerun validates the readiness fix.

Repair validation: 28 focused tests passed, 13.64 s; real modal harness separately PASS after final bounded-wait options. Ruff/development-process/whitespace PASS.

## Третье руководство: проверка расшифровки

Baseline11196fe593e9a0320d70a140d1237ecd5d497409 — документальный closeout опубликованного540f. Active slice/T008T009/issue7429. Default-off provider contracts и readiness не изменены. Новые страницы добавлены только в existing closed L1/campaign registry.

Учебные примеры явно вымышлены и не являются результатами ГРАФ. Источники Google Cloud diarization и Microsoft WER прочитаны 2026-10-02; используются для определения методов, не для доказательства провайдера/точности продукта. Ни редактор текста, ни поиск, ни автоматический пересчет не обещаны. Цены/checkout не дублируются.

Focused local PostgreSQL/HTML/copy/aggregate contracts: 96 PASS,14.90s, disposable container removed. Первые два запуска остановились на неполном тестовом env (TWOBRAIN_DATABASE_URL и admin postgres database); исправлен только локальный harness, без продукта/production. Последний запуск покрывает source/landing/campaign перенос в download, повторные visits без повторной attribution row, секретный query не сохраняется, L1-off brake.

Actual SSR/CSS/Onest mobile360/390/768/1440 для новой статьи и трехкарточного хаба: no overflow (проверены также границы элементов), один H1, skiplink first focus; screenshot390 visual review PASS. Ruff, development-process и whitespace PASS. Zero protected diff landing/download/all policies/landing assets; existing article body/metadata сохранены, связанный partial добавляет третью статью.

Exact-SHA PR gates, frozen Full/backup/CD и production readback еще pending; локальные результаты не заменяют эти gates. Индексация, рост и organic activation не проверены.
