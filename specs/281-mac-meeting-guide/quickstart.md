# Проверка F281

Lane: tiny-low-risk content, без нового data/API contract.

`PYTHONPATH="$PWD/apps/server/src" bash apps/server/scripts/run_local_postgres_tests.sh --focused tests/contract/test_public_mac_meeting_guide.py tests/unit/test_public_landing.py tests/contract/test_public_landing_contract.py -q`

Проверить нулевой diff protected templates/assets. Mobile widths 360/390/768: overflow 0, один H1, ссылка download. Production: только после exact-SHA CI и штатного full release candidate с backup/rollback.

Дополнение учебного протокола: включить `tests/contract/test_public_protocol_guide.py` и `tests/contract/test_copy_convention_contract.py` в focused disposable PostgreSQL набор. Проверить ручную/вымышленную маркировку, неизвестные сроки и Safari owner, порядок копируемого шаблона; Chromium 360/390/768 с реальными CSS/font. Выпуск только если текущий master не включает несогласованные изменения F282/runtime.

Hub: добавить `test_public_guides_hub.py`, `test_product_analytics_anonymous_aggregate_contract.py`, `test_public_traffic_measurement_contract.py` к focused suite. Проверить ровно одну новую footer строку, unchanged download/policies/assets, обе article URLs и breadcrumbs/related links. Mobile360390768 — hub/cards/guide links, keyboard focus и skip link. Не публиковать foreign billing при неподтвержденном baseline.

Проверка hub в изолированной среде: 23 PostgreSQL контракта PASS, контейнер удален; HTML guides regressions6 PASS. Chromium360/390/768/1440: overflow0, одинH1, две карточки, первый фокус skip-link. Источник лендинга при удалении новой footer-строки побайтово равен baseline; download/policies/landing assets zero diff. T007 завершена: baseline v2026.10.02.1 опубликован отдельно; hub опубликован в v2026.10.02.2 с Full36941465329, CD, backup и production readback PASS.

Production: https://rec.2brain.pro/guides — HTTP200, canonical self, две карточки, sitemap10 уникальных URL, mobile360/390/768/1440 PASS. Main допускает только одну footer-ссылку; download и политики сохранены. Боты отмечены automated и не считаются органическими активациями.

## Проверка качества расшифровки (следующий срез)

Проверить новую статью, query-free canonical, sitemap uniqueness, три карточки и взаимные ссылки, явную маркировку вымышленных примеров, внешние источники, отсутствие JS/noindex/неподтвержденных функций. Focused HTML + isolated DB campaign/consent/off tests; viewport360/390/768 и клавиатура. Проверить zero diff landing/download/policies/их assets. До выпуска обязательны exact-SHA PR checks, frozen Full, backup/CD; после — production GET/sitemap/protected readback без платежей и записей людей.

## Regression закрытия меню
С уже подготовленными browser dependencies: `node apps/server/tests/browser/public-navigation-focus.test.cjs`. Проверяет реальный controller, полностью раскрытую анимацию, Escape → Tab без скрытых ссылок, resize и no-JS fallback; вся сеть заблокирована. Геометрия проверяется отдельно на отрендеренных пяти страницах.

Этот harness вызывается обнаруживаемым pytest-тестом `tests/contract/test_public_guide_navigation.py::test_public_navigation_focus_and_article_reduced_motion_in_browser` (marker `browser`), поэтому входит в штатный CI. Требует уже установленные Node/Playwright; отсутствие ресурсов — failure, не skip. `GRAF_NODE_MODULES` может указывать существующую установку. Дополнительно проверяет фактический `scroll-behavior` корневого html всех трех шаблонов при reduce/no-preference; общий `landing.css` уже обеспечивает auto при reduced motion, менять CSS для замечания ревью не требуется.

## Дизайн статей

Сравнить DOM текст/metadata/section IDs/ссылки до и после; focused существующие guide contract tests. Chromium360/390/768/1440, text200%, keyboard skip/focus, noJS, длинный копируемый шаблон. Нулевой diff main/download/policies/assets. Новые изображения/schema/аналитика не добавляются.

## Помощь: одна сторона записи

Focused: `test_public_audio_help.py`, существующие public guide/hub/navigation/copy/landing contracts. Новые Help pages не добавляются в analytics inventories: test spies/cookie-free response доказывают отсутствие вызова recorder; прежние measured pages сохраняются. Sitemap содержит Help/hub по одному разу, News404. Mobile320/390/768/1440, text200%, keyboard skip/current, noJS, safe screenshots only. Protected templates/assets побайтово совпадают с master. Текущий текст сверить с SystemAudioStatusLabels, CaptureControlViewCore, DesktopPermissionOnboardingView, SystemAudioCaptureService, MicrophoneCaptureService и Apple mac-help14/15/26. Не запускать микрофон или экран ради проверки документации. Draft-only: точный PR SHA/CI отдельно от functional Mac compatibility и публикации.

## Отдельно разрешенная публикация Help

FR027–28/T016: сначала сверить свежие master, deployed image SHA, deploy lock и последний опубликованный stable Release. Открытый draft F286 не является опубликованным baseline. Пройти новый exact-SHA PR validator после обновления ветки; после завершения чужого выпуска подготовить собственный frozen candidate и одну authoritative Full. Затем штатные CD dry-run/execute с разрешенной свежей копией GRAF и health. Live readback: `/help` и статья200, self canonical, sitemap без дублей, контекстная ссылка руководства и current-навигация, mobile320/390, инварианты главной/download/политик/подписанных macOS артефактов. Личную запись и новые разрешения не использовать; installed-app audio compatibility остается непроверенной.
