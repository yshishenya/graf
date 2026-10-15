# F280: независимый обзор браузера и доступности

2026-10-01. Продолжение T018, high-risk-product. **Промежуточное заключение: требуется исправление MEDIUM WebKit320; окончательный PASS пока не выдан.**

## Проверенные исходники

Прочитаны актуальные spec/plan/tasks/quickstart, requirements review и analyze, product gates, общий diff billing.py и весь checkout template. Применён `web-design-guidelines`, свежие правила получены с `https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md`. Правила URL state применяются с ограничением проекта: code не включается в URL; период передаётся отдельно, краткий выбор подписан и связан с проверенной сессией.

| Файл | SHA-256 |
| --- | --- |
| cabinet/web_routes/billing.py | `40e5e291dc925713a8bddb17076443eb67cf88c0c25038d4f2144a27739eca19` |
| billing_checkout_content.html | `10a7b0757eb16276f5c4206bab76ed506c8d177e0663ab2ff1d413d8b6d4d6ae` |
| cabinet.css, первая частичная правка | `7e79dec17b152ebd81609489eccf27fb05413927b846e3189608c6b1a1efbf5d` |

## Настоящий путь и исправленные замечания

HTTPServer на loopback пересылает реальные GET/POST в существующий ASGI TestClient; отдельный одноразовый PostgreSQL и реальная синтетическая auth-session/CSRF. Browser Cookie — единственный источник cookie: jar TestClient очищается перед/после каждого запроса, переходы 303 выполняет браузер. Нет подставленного HTML, подмены расчёта или провайдера. POST кроме preview запрещён, финансовые таблицы проверяются пустыми. Временная конфигурация с синтетической сессией имеет 0600 и удаляется в finally; HTTP/request payload не журналируются.

Браузерная цепочка на 320/1280: Apply → настоящий POST303GET → два reload → тарифы → back → checkout без query cycle; year/month, malformed AB → сохранённая ошибка/запрет формы оплаты → исправление при переключении периода; Enter на выбранном годе; очистка → два reload → первый ещё не применённый код при переключении периода. По 16 POST303 на каждый engine, пустые согласия, правильные текущие/обычные цены, отсутствие code/quote в URL и внешних запросов. Подписанный draft не считается ценой или согласием; права/quote/idempotency остаются в start.

Найденный дефект Enter воспроизведён на старом шаблоне: первый default submit был month, поэтому Enter на годе менял период. Source owner добавил скрытый default Apply, внешние controls остались native form-associated; реальный Enter прошёл в обеих engines. Reviewer source не изменял.

Три устаревшие строки contract заменены на нынешние `preview_action` + `form="billing-promo-preview"`, с дополнительной проверкой association самого input. Проверки цены, required согласий, role/error/focus, единственного основного действия, CSRF, тем, масштаба и ширин сохранены. Ruff и Node syntax PASS; opt-in отключён по умолчанию, запуск без `GRAF_PROMO_BROWSER=1` подтверждён как skip без DB/browser выполнения.

## Реальный блокирующий визуальный дефект

Лично просмотрены applied/error/consents снимки Chromium и WebKit на 320/1280. Внешний вид, цена, ошибка и сохранённый синтетический ввод согласованы; отсутствует общая горизонтальная прокрутка. На 320 px основной платёж расположен ниже первого экрана, поэтому отдельно снята сама форма согласий/оплаты.

`cabinet.css:5444` / `:5445`: **MEDIUM** — WebKit320 оставляет огромные пустые вертикальные промежутки в форме согласий. Это реальный DOM layout до screenshot, а не увеличение viewport снимком. На закрытом промокоде дефект тот же. Измерения до/после снимка:

- form height `769.03125`, первый label `136.5`, второй `546`, button top `710.5`;
- фактический текст span высотой только `19.5`/`58.5`, span width `237`, checkbox `16×16`;
- implicit grid rows сохраняют лишнюю высоту. Частичная замена только внутреннего label на flex не устраняет дефект, поскольку родительская `.billing-checkout-form` остаётся grid.

Артефакты диагностики: `/tmp/graf-promo-refresh-dom/promo-refresh-webkit-320-applied-layout.json` и `...-cleared-layout.json`; старые снимки `...-applied-consents.png` показывают тот же разрыв. Новая browser проверка сопоставляет высоту каждого label с реальной высотой текста/контрола, margins, padding, borders и доступным min-height, допускает 2px округления. Она ловит дефект без фиксированной эталонной высоты. Измерение ждёт `document.fonts.ready`.

`/tmp/graf-promo-refresh-dom-webkit-compact-baseline-detail.log`: fail-before на `320:initial-submit`, причина `consent rows fit their visible text and controls`. После частичного label-flex CSS: `/tmp/graf-promo-refresh-browser-webkit-final-compact.log` — **1 failed / 16 passed**, та же причина. Chromium на том же кандидате `/tmp/graf-promo-refresh-browser-chromium-final-compact.log` — **17 passed**.

Рекомендуемая минимальная коррекция владельцу source: обычная вертикальная flex-форма для трёх controls с существующим gap; сохранить labels, цель 24px, размеры checkbox, естественный перенос и одну видимую кнопку оплаты. Новый стек/JavaScript не требуется. Reviewer CSS не меняет. После коррекции нужны обе реальные engines, свежие снимки и затронутая accessibility матрица; исходные PASS навигации не заменяют эту проверку.

## Границы

Не изменялись source/CSS, specs/plan/tasks чужих агентов, reviewer-owned checklist, GitHub, commits или выпуск. Нет реального списания/чека/банковского зачисления/возврата, установленного GRAF Dev, человеческого понимания и измерения конверсии/удержания. T011/T012/F278 этими данными не закрываются. После устранения визуального MEDIUM этот отчёт должен быть обновлён свежим результатом; нынешняя запись не является допуском к выпуску.
