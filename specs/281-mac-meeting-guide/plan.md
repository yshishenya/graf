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

## Следующий узкий срез: качество расшифровки

Active Spec Kit slice, tiny-low-risk editorial content. Новый фиксированный маршрут/шаблон и запись в существующем реестре; shared related partial выводит все опубликованные соседние guides. Используются существующие landing/guide/content CSS, новые стили только для учебных примеров при необходимости; CMS/search/editor не добавляются. Исходная реализация ASR/AI не меняется. Current base11196fe59 содержит только документальный closeout поверх опубликованного540f. FR011–FR015 покрываются T008/T009. Google Cloud speaker diarization и Microsoft WER docs прочитаны 2026-10-02; оба источника определяют общие понятия, не являются доказательством использования этих провайдеров в ГРАФ.

## Шапка: narrow low-risk navigation
Baseline721b5125d, опубликованный v2026.10.02.3. Общий Jinja partial четырёх content routes и scoped CSS; mobile links видимы во второй строке без JS. Главная получает одну ссылку в двух представлениях, aria-controls и Escape/resize; скрытые ссылки не фокусируются. Проверка current/no-JS/focus/mobile36039076898010241440, protected HTML outside-header equality.
Analyze: FR016–18 покрыты T010/T011; critical/high нет. Keyboard defect opacity-menu исправляется в разрешённой шапке. Recovery retained baseline/verify previous/finish restored проверен предыдущим выпуском; перед CD привязать к точному candidate/baseline.

## Проверка завершённой анимации меню
Дополнительный браузерный тест после полного раскрытия выявил фокус в закрывающемся меню: visibility меняется после .2s transition. Controller явно устанавливает inert сразу при закрытии и снимает при открытии. Без JS markup inert не содержит, ссылки доступны. Regression проверяет закрытие после350ms раскрытия, Tab немедленно после Escape, resize и повторное открытие.
