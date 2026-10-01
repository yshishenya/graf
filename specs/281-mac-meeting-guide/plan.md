# План F281: раздел руководств

Lane: active Spec Kit slice, narrow low-risk public content navigation. Существующий F281 расширяется без новой фичи. Нет публичного data API, schema/migrations, auth, capture, AI или privacy contracts.

## Архитектура

FastAPI/Jinja существующего public renderer. Frozen dataclass и enum guides/help/news в `public/content.py` содержат только опубликованные entries и их closed analytics surface. Не вводятся loader, CMS, база контента, dependencies или пустые placeholders. `/guides` — фиксированный маршрут с прежним PublicWebDbDependency; оба guides используют тот же best-effort L1/campaign helper. Sitemap и measurement inventories читают опубликованные paths реестра. Контент не включает analytics JS.

Дизайн hub соответствует существующему landing: Onest, #090b12, фиолетовые акценты, светлая область карточек, радиус26px, без декоративных изображений или новых обещаний. Крупный H1 и спокойный lead, две карточки в порядке запись→протокол. На360/390px одна колонка, на768px проверяется удобство чтения и касаний; клавиатура/контраст/reduced-motion обязательны. Новый компактный CSS для hub/cards/breadcrumb/related block; base guide CSS, landing/download/policy assets не меняются. Главная отличается ровно одной footer anchor. В статьях добавляются только breadcrumb и related block; существующие URLs/metadata и основной текст сохранены.

## Constitution / scope check

Публичные editorial материалы без записей людей, private content, необоснованных claims или provider data. Не создаются credentials/grants и новые analytics modes. Capture/auth/storage contracts не затрагиваются. Owner clarification FR007 явно разрешает footer link; другие защищенные пути без diff. Custom reviewer checklists в F281 отсутствуют.

## Проверка

T006: реальные HTML links/canonical/indexability/sitemap; registry empty help/news negative checks; сохранение основной landing source при удалении единственной новой строки; aggregate inventory contract и real isolated L1/campaign persistence; a11y/keyboard/contrast/mobile360390768.
T007: required exact-SHA GitHub checks + общий validator; fresh production/master and competing release; frozen scoped Full; dry-run, backup, execute and publication attestation; production URLs and protected HTML comparison. Foreign unpublished billing не выкатывать: дождаться отдельного verified baseline.

## Analyze

FR006–FR010 имеют задачи и проверки; scope/clarification явные, пустые разделы исключены. Перед implementation выполнить read-only cross-artifact analysis; critical/high findings блокируют работу.
