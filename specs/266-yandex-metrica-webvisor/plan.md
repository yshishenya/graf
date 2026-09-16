# Implementation Plan: Безопасная аналитика и Webvisor для пути пользователя

**Branch**: `266-yandex-metrica-webvisor` | **Date**: 2026-09-15 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/266-yandex-metrica-webvisor/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Восстановить единый opt-in для публичной и продуктовой браузерной аналитики,
включить Webvisor, карту кликов и карту прокрутки только на `/` и `/download`
после явного разрешения категории `behavior_replay`, а внутренний путь измерять
только безопасными метаданными через существующие провайдеры и инвентарь страниц.
Синхронно раскрыть обработку данных в четырёх пользовательских документах и
добавить автоматические и ручные проверки, не включая production автоматически.

Основной подход — переиспользовать существующие `CookieConsent`, контроллер
`analytics.js`, `page_inventory.py`, `browser_context.py`, шлюз продуктовой
аналитики и текущие маскирующие атрибуты. Новая база записей сессий, новый
провайдер и новый поток хранения не нужны.

## Technical Context

**Language/Version**: Python 3.13+; браузерный JavaScript без сборочного шага

**Primary Dependencies**: FastAPI, Pydantic, Jinja2, pytest, существующий
CookieConsent 3.1.0, Яндекс Метрика и первый-party маршрут PostHog

**Storage**: Новое хранилище не добавляется. Выбор хранится локально средством
CookieConsent; записи Webvisor живут у Яндекса в пределах фактически настроенного
срока. Серверные события проходят существующий first-party маршрут.

**Testing**: pytest (unit, contract, integration), `node --check` для
`analytics.js`, `git diff --check`, опубликованный ручной smoke в кабинете
Яндекс Метрики и браузерная проверка сетевых запросов.

**Risk / Validation Lane**: `high-risk-feature`. Изменяются согласие, запись
поведения, внешняя передача и пользовательские документы; требуется полный
Spec Kit, reviewer-owned `security.md`, автоматические проверки, юридическое
согласование и ручное подтверждение кабинета.

**Release Gate**: `no deploy` для этой ветки; перед возможным выпуском нужен
отдельный операторский gate с `cd-remote.sh --dry-run`, exact-SHA проверками,
юридическим статусом и ручным подтверждением кабинета. `--execute` не выполняется.

**Target Platform**: Сервер GRAF и браузеры, отображающие публичные и кабинетные
HTML-шаблоны; внешняя запись ограничена публичными веб-поверхностями.

**Project Type**: Серверное веб-приложение с HTML-шаблонами и браузерными
провайдерами аналитики.

**Performance Goals**: Провайдеры загружаются отложенно и не блокируют основной
путь; отказ провайдера не ломает навигацию; повторная инициализация не создаёт
дубликаты событий.

**Constraints**: До opt-in нет необязательных запросов. `analytics` без
`behavior_replay` не включает Webvisor или карты. Webvisor разрешён только для
`public_landing` и `public_download`; финансовые, auth, admin, deletion,
meeting, OAuth и embedded-поверхности закрыты. Произвольный DOM-текст, URL,
query/hash, формы, идентификаторы, cookies, секреты, аудио и расшифровки не
передаются. Runtime-флаги остаются fail-closed.

**Scale/Scope**: `/`, `/download` и существующий инвентарь внутренних классов
страниц; каталог из девяти публичных событий и ограниченный allowlist
внутренних действий. Мобильные и новые классы наследуют запрет до отдельного
утверждения.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Проверка до исследования: **PASS с обязательными ограничениями**.

- **II. Visible Consent And User Control**: необязательная аналитика и запись
  поведения запускаются только после явного выбора; отказ не блокирует основной
  сайт; отзыв прекращает новые отправки.
- **III. Plaintext Observability For Internal MVP**: эта функция не передаёт
  содержимое встреч, аудио или расшифровки; внешняя передача ограничена
  allowlist-провайдерами, а конфигурация и срок хранения остаются операционным
  gate. Сырые секреты и личные значения не попадают в события или журналы.
- **VI. Spec-Driven Delivery With Testable Gates**: сохраняются полный Spec Kit,
  reviewer-owned privacy/security checklist, точные пути файлов, contract/
  integration проверки и раздельное доказательство кода, кабинета и права.
- **Release safety**: production-флаги не включаются этой реализацией, deploy и
  публикация выполняются только отдельным разрешённым выпускным процессом.

Нарушений, требующих Complexity Tracking, нет. Требование пользователя
«по умолчанию» трактуется как автоматический запуск Webvisor после согласия
категории `behavior_replay`; запуск до согласия исключён как небезопасный и
юридически неподтверждённый.

## Validation Plan

1. Запустить focused pytest-набор из `quickstart.md`: публичный opt-in,
   внутренний browser opt-in, каталог и allowlist, инвентарь страниц, запрет
   Webvisor на чувствительных поверхностях, маскирование и отсутствие секретов.
2. Выполнить `node --check apps/server/src/twobrain_rec_server/public/static/public/analytics.js`
   и `git diff --check`.
3. В чистом браузере проверить отсутствие запросов до выбора, режимы
   `necessary_only`, `analytics`, `analytics + behavior_replay`, повторный визит
   и отзыв через «Настройки cookies»; убедиться, что сайт продолжает работать.
4. В тестовом кабинете Яндекс Метрики проверить Webvisor, карту кликов, карту
   прокрутки, ссылки, точный отказ от быстрых визитов, фильтры, цели и срок
   хранения; evidence не должен содержать идентификаторы посетителей.
5. Сопоставить четыре документа с одной редакцией раскрытия и получить
   юридическое подтверждение. Без этого и без smoke кабинета выпускной gate
   остаётся закрытым.
6. Для PR получить обязательные `governance-fast`, `macos-pr` и `pr-metadata`
   на exact PR SHA. Production deploy в этой задаче не выполняется.

## Project Structure

### Documentation (this feature)

```text
specs/266-yandex-metrica-webvisor/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── consent-and-provider.md
│   ├── page-policy-and-events.md
│   └── dashboard-evidence.md
├── checklists/
│   ├── requirements.md
│   └── security.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/server/src/twobrain_rec_server/public/analytics.py
apps/server/src/twobrain_rec_server/public/static/public/analytics.js
apps/server/src/twobrain_rec_server/public/static/public/cookieconsent.umd.js
apps/server/src/twobrain_rec_server/public/static/public/cookieconsent.css
apps/server/src/twobrain_rec_server/public/templates/public/_analytics.html
apps/server/src/twobrain_rec_server/public/templates/public/_product_analytics_provider.html
apps/server/src/twobrain_rec_server/public/templates/public/analytics_consent.html
apps/server/src/twobrain_rec_server/public/templates/public/cookies.html
apps/server/src/twobrain_rec_server/public/templates/public/privacy.html
apps/server/src/twobrain_rec_server/public/templates/public/terms.html
apps/server/src/twobrain_rec_server/public/templates/public/landing.html
apps/server/src/twobrain_rec_server/public/templates/public/download.html
apps/server/src/twobrain_rec_server/product_analytics/browser_context.py
apps/server/src/twobrain_rec_server/product_analytics/page_inventory.py
apps/server/src/twobrain_rec_server/product_analytics/telemetry_gate.py
apps/server/src/twobrain_rec_server/product_analytics/ingest.py
apps/server/src/twobrain_rec_server/product_analytics/forbidden_fields.py
apps/server/src/twobrain_rec_server/product_analytics/identity.py
apps/server/src/twobrain_rec_server/config.py
infra/env/rec.production.env.example
infra/docker-compose.yml
apps/server/tests/unit/test_public_analytics.py
apps/server/tests/contract/test_public_analytics_contract.py
apps/server/tests/contract/test_product_analytics_replay_webvisor_boundaries.py
apps/server/tests/contract/test_product_analytics_yandex_provider_contract.py
apps/server/tests/contract/test_product_analytics_page_inventory_096.py
apps/server/tests/contract/test_product_analytics_posthog_autocapture_contract.py
apps/server/tests/integration/test_product_analytics_autocapture_pages.py
apps/server/tests/integration/test_product_analytics_yandex_page_scope.py
apps/server/tests/unit/test_product_analytics_provider_config.py
apps/server/tests/integration/test_compose_hardening.py
```

**Structure Decision**: Изменяется существующий серверный рендеринг и единый
браузерный контроллер. Политика страницы и контексты провайдеров остаются
серверными источниками истины; клиент получает только минимальную конфигурацию,
а серверный маршрут повторно проверяет безопасные действия. Публичные документы
используют общий текст версии раскрытия. Тесты расширяются в уже существующих
unit/contract/integration файлах.

## Complexity Tracking

Нарушений нет: новых подсистем, провайдеров, таблиц или фоновых процессов не
требуется.
