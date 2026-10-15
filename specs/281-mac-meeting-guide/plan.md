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

## Единый визуальный стиль статей

Active Spec Kit slice, узкий визуальный срез без data/API/runtime changes. Старые guide/protocol/quality CSS заменяются общим article.css; первые две статьи получают существующую структуру dark intro + light reading из третьей. Существующие landing.css/content.css переиспользуются без изменения. Тексты/SEO/headings/section IDs/link graph инвариантны. FR019–20 → T012/T013. Analyze: critical/high contradictions нет; старое ограничение guide body относится к предыдущей шапке, новое поручение пользователя явно разрешает оформление статей. Публикация только по точному CI/Full/CD; failed smoke требует штатного восстановления.

## Минимальная помощь: узкий редакционный срез

Lane: tiny-low-risk editorial content within F281; нет изменений поведения capture/permissions/diagnostic bundle/auth/storage или аналитики. Прямое поручение задает предмет статьи, безопасность проверки, protected paths и draft-only выход; уточнять заново не требуется. Новые custom reviewer checklists не создаются для этого низкорискового текста.

FR021–26 → T014/T015 (#7544). Fixed FastAPI routes `/help` + article, Jinja и текущие article/content/header CSS. Реестр PublicContentPage допускает отсутствие measurement surface; PUBLIC_HELP_PAGES отделены от прежних PUBLIC_CONTENT_PAGES, чтобы не менять closed analytics inventories. content_for_section и sitemap знают опубликованный Help, measurement map остается прежним. Help routes возвращают public_template_response без DB и record helpers. Это осознанная граница прямого запрета трогать analytics; не переносить Help в measured registry молча.

Constitution check: нет личных записей, secrets/egress, capture behavior, новых зависимостей или legacy fallback. Главная/download/policies/assets инвариантны. Чтение исходников и Apple docs доказывает текст/названия, а не installed-app acceptance. Narrow direct lane допускает focused проверки без новой фичи и полного capture Spec Kit.

Анализ согласованности этого дополнения: все FR021–26 имеют тесты/проверки и T014/T015; historical empty Help FR008 заменяется только после реального материала. Старые T011/T013 релизные хвосты остаются без изменения; новый draft их не закрывает. Critical/high contradictions в этом scope не найдены.

## Продвижение к отдельно разрешенной публикации

2026-10-06 владелец разрешил публикацию и обязательную свежую копию GRAF. FR027–28 → T016 (#7544); код статьи, аналитика и защищенные страницы не расширяются. Help переносится на актуальную базу master, проходит focused/regression и новый exact-SHA PR proof. Замороженный Full предыдущего F286 не является Full для будущего Help SHA.

Перед отдельным выпуском требуется опубликованный stable baseline F286: release tooling считает диапазон от последнего опубликованного Release, а не от runtime SHA. Первоначальный CD de255e0d завершился, но после него activation smoke отказал на cleanup FK; исправление и новый Full/CD выполнял другой оператор. Параллельный CD и автоматическое объединение исключены.

Граница подтверждена 2026-10-06: v2026.10.06.1 опубликован на29264c66520ee36b1a2f287fa7edd6e92139dd9f, Full37527256994 SUCCESS, durable CD result deployed, public live/ready200 ok/ready и deploy lock освобожден. Help переносится на этот опубликованный baseline и выпускается своим новым кандидатом; чужие миграции уже применены. Старые T011/T013 и переполнение прежнего guides остаются отдельно.
