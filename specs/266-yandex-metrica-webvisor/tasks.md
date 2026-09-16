---

description: "Исполнимый список задач для безопасной аналитики и Webvisor"
---

# Tasks: Безопасная аналитика и Webvisor для пути пользователя

**Input**: Design documents from `/specs/266-yandex-metrica-webvisor/`

**Prerequisites**: `spec.md`, `plan.md`, `research.md`, `data-model.md`,
`contracts/`, `checklists/`

**Risk lane**: `high-risk-feature`. Согласие, приватность, внешняя передача и
запись поведения требуют автоматических проверок, ручной проверки кабинета и
юридического gate. Production deploy в этой задаче не выполняется.

**Organization**: Задачи сгруппированы по пяти пользовательским историям и
идут в порядке зависимостей. Тесты стоят перед соответствующей реализацией.

## Phase 1: Setup

**Purpose**: Зафиксировать область работы и исходные ограничения без добавления
новой зависимости, хранилища или провайдера.

- [X] T001 Подтвердить активную фичу, high-risk validation lane и запрет production deploy в `specs/266-yandex-metrica-webvisor/plan.md` и `specs/266-yandex-metrica-webvisor/quickstart.md`

**Checkpoint**: Используются существующие `CookieConsent`, браузерный контроллер,
инвентарь страниц и first-party маршрут; новые провайдеры и хранилища не нужны.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Подготовить общий источник политики, согласия и маскирования для
публичных и внутренних браузерных маршрутов.

**CRITICAL**: Ни одна пользовательская история не считается готовой, пока общий
маршрут не остаётся fail-closed.

- [X] T002 [P] Проверить и синхронизировать версии согласия, категории и runtime defaults в `apps/server/src/twobrain_rec_server/public/analytics.py` и `apps/server/src/twobrain_rec_server/config.py`
- [X] T003 [P] Привязать общий браузерный gate согласия к единому контексту провайдеров в `apps/server/src/twobrain_rec_server/product_analytics/browser_context.py` и `apps/server/src/twobrain_rec_server/public/templates/public/_product_analytics_provider.html`
- [X] T004 [P] Сохранить fail-closed политику неизвестных классов, чувствительных полей и существующих маскирующих атрибутов в `apps/server/src/twobrain_rec_server/product_analytics/page_inventory.py` и `apps/server/src/twobrain_rec_server/product_analytics/forbidden_fields.py`

**Checkpoint**: Публичный и внутренний браузерные потоки получают один источник
разрешения и не отправляют необязательные данные при неизвестном состоянии.

---

## Phase 3: User Story 1 — Посетитель управляет согласием (Priority: P1) 🎯 MVP

**Goal**: До выбора пользователя нет необязательных запросов; выбор категорий,
повторный визит и отзыв управляют только соответствующими провайдерами.

**Independent Test**: В чистом браузере открыть `/`, выбрать «Только
необходимые», «Аналитика» и «Поведенческая запись», перезагрузить страницы,
отозвать выбор и убедиться, что сайт и скачивание остаются доступны.

### Tests for User Story 1

- [X] T005 [P] [US1] Добавить contract-проверки категорий, переходов, версии раскрытия, повреждённого выбора и отсутствия старого разрешения в `apps/server/tests/contract/test_public_analytics_contract.py`
- [X] T006 [P] [US1] Добавить unit-проверки нормализации состояния согласия и fail-closed поведения в `apps/server/tests/unit/test_public_analytics.py`

### Implementation for User Story 1

- [X] T007 [US1] Перенести запуск публичного и продуктового провайдеров за opt-in `CookieConsent`, сохранить выбор/версию/отзыв и остановить новые отправки в `apps/server/src/twobrain_rec_server/public/static/public/analytics.js`
- [X] T008 [US1] Подключить существующие `CookieConsent` assets и доступную кнопку «Настройки cookies» без обязательной загрузки необязательных провайдеров в `apps/server/src/twobrain_rec_server/public/templates/public/_analytics.html` и `apps/server/src/twobrain_rec_server/public/templates/public/_product_analytics_provider.html`

**Checkpoint**: US1 проходит чистый браузерный сценарий и не меняет доступность
публичных страниц при отказе или сбое JavaScript/провайдера.

---

## Phase 4: User Story 2 — Владелец продукта видит публичный путь (Priority: P1)

**Goal**: После соответствующего opt-in на `/` и `/download` измеряются просмотры,
цели, ссылки, клики, прокрутка, карта взаимодействий и Webvisor; событие
«установка завершена» не создаётся.

**Independent Test**: С включёнными `analytics + behavior_replay` пройти лендинг,
FAQ, вкладки, тариф, CTA и `/download`; проверить безопасные события и условную
конфигурацию Яндекс Метрики.

### Tests for User Story 2

- [X] T009 [P] [US2] Обновить contract-проверки флагов `clickmap`, `trackLinks`, `accurateTrackBounce`, `defer`, Webvisor и закрытого списка `/`/`/download` в `apps/server/tests/contract/test_public_analytics_contract.py`
- [X] T010 [P] [US2] Проверить полный публичный каталог, FAQ `google_calendar`, безопасные UTM и отсутствие события успешной установки в `apps/server/tests/unit/test_public_analytics.py` и `apps/server/tests/contract/test_public_analytics_contract.py`

### Implementation for User Story 2

- [X] T011 [US2] Включить `clickmap`, `trackLinks`, `accurateTrackBounce` и условный Webvisor только после `analytics + behavior_replay` в `apps/server/src/twobrain_rec_server/public/static/public/analytics.js` и `apps/server/src/twobrain_rec_server/public/analytics.py`
- [X] T012 [US2] Добавить отсутствующий безопасный FAQ `google_calendar` и сохранить allowlist событий, меток, UTM и категории реферера в `apps/server/src/twobrain_rec_server/public/analytics.py`
- [X] T013 [US2] Привязать просмотр секций, CTA, вкладок, периода тарифа и FAQ к существующему каталогу с дедупликацией в `apps/server/src/twobrain_rec_server/public/static/public/analytics.js`, `apps/server/src/twobrain_rec_server/public/templates/public/landing.html` и `apps/server/src/twobrain_rec_server/public/templates/public/download.html`

**Checkpoint**: Без `behavior_replay` просмотры и разрешённые цели работают без
Webvisor и карт; с ним запись включается автоматически только на двух публичных
поверхностях.

---

## Phase 5: User Story 3 — Аналитик видит безопасный внутренний путь (Priority: P1)

**Goal**: На разрешённых внутренних страницах передаются только стабильный класс,
тип действия и обезличенный идентификатор; Webvisor и карты внутренних страниц
всегда запрещены.

**Independent Test**: С тестовой учётной записью пройти кабинет, настройки,
список встреч, календарную интеграцию и загрузку, затем открыть встречу,
воспроизведение, удаление, оплату, вход, OAuth, админку и встроенный webview.

### Tests for User Story 3

- [X] T014 [P] [US3] Расширить contract-проверки всех классов инвентаря, статусов `page_view_allowed`/`safe_event_allowed` и запрета Webvisor/карт в `apps/server/tests/contract/test_product_analytics_page_inventory_096.py` и `apps/server/tests/contract/test_product_analytics_replay_webvisor_boundaries.py`
- [X] T015 [P] [US3] Проверить серверный allowlist `analytics_action`/`analytics_target`, маскирование и блокировку email, токенов, URL, текста и идентификаторов в `apps/server/tests/contract/test_product_analytics_posthog_autocapture_contract.py`
- [X] T016 [P] [US3] Добавить интеграционные сценарии общего opt-in, безопасных внутренних страниц и закрытых поверхностей в `apps/server/tests/integration/test_product_analytics_autocapture_pages.py` и `apps/server/tests/integration/test_product_analytics_yandex_page_scope.py`

### Implementation for User Story 3

- [X] T017 [US3] Передавать состояние браузерного согласия в общий `build_request_browser_provider_context` и включать провайдеры только после разрешения, сохранив анонимную/псевдонимизированную идентичность в `apps/server/src/twobrain_rec_server/product_analytics/browser_context.py`, `apps/server/src/twobrain_rec_server/cabinet/templates.py` и `apps/server/src/twobrain_rec_server/admin/templates.py`
- [X] T018 [US3] Добавить серверную проверку перечислимых внутренних `analytics_action` и `analytics_target` до маршрута доставки в `apps/server/src/twobrain_rec_server/api/product_analytics.py` и `apps/server/src/twobrain_rec_server/product_analytics/page_inventory.py`
- [X] T019 [US3] Оставить внутренние страницы, финансовые поверхности, auth/OAuth, deletion, meeting/playback, admin и embedded webview без Яндекс Метрики, Webvisor и карт, сохранив четыре маскирующих атрибута в `apps/server/src/twobrain_rec_server/public/templates/public/_product_analytics_provider.html`, `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/base.html` и `apps/server/src/twobrain_rec_server/admin/templates/admin/base.html`

**Checkpoint**: Неизвестная страница, неизвестное действие или чувствительное
значение блокируются до внешней отправки; отзыв оставляет доступными обязательные
юридические, экспортные и удаляющие действия.

---

## Phase 6: User Story 4 — Ответственный публикует прозрачные правила (Priority: P1)

**Goal**: Четыре документа используют одну редакцию раскрытия и прямо описывают
существенные категории обработки, границы Webvisor, получателя, срок хранения и
отзыв.

**Independent Test**: Сопоставить текст четырёх страниц с контрактом раскрытия и
фактическими режимами браузерного контроллера.

### Tests for User Story 4

- [X] T020 [P] [US4] Добавить contract-проверки единой версии, оператора, категорий, движения указателя, прокрутки, кликов, технического воспроизведения, получателя, срока хранения и отзыва в `apps/server/tests/contract/test_public_analytics_contract.py`

### Implementation for User Story 4

- [X] T021 [US4] Синхронизировать одну редакцию раскрытия аналитики, Webvisor, cookies/localStorage, внешнего получателя, хранения и отзыва в `apps/server/src/twobrain_rec_server/public/templates/public/analytics_consent.html`, `apps/server/src/twobrain_rec_server/public/templates/public/cookies.html`, `apps/server/src/twobrain_rec_server/public/templates/public/privacy.html` и `apps/server/src/twobrain_rec_server/public/templates/public/terms.html`
- [X] T022 [US4] Проверить доступность ссылки «Настройки cookies» и документов без необязательной загрузки на публичных страницах в `apps/server/src/twobrain_rec_server/public/templates/public/_analytics.html` и `apps/server/src/twobrain_rec_server/public/web.py`

**Checkpoint**: Юридический текст понятен пользователю, но выпуск всё ещё
заблокирован до отдельного статуса `legal_status=approved`.

---

## Phase 7: User Story 5 — Аналитик проверяет качество измерения (Priority: P2)

**Goal**: Есть воспроизводимое разделение между кодом, автоматическими тестами,
ручной настройкой кабинета и юридическим согласованием.

**Independent Test**: Выполнить redacted smoke в рабочем кабинете Яндекс Метрики
с тестовым визитом и зафиксировать только безопасный статус возможностей.

### Tests for User Story 5

- [X] T023 [P] [US5] Проверить redacted dashboard-чеклист, обязательные статусы и запрет идентификаторов посетителей в `specs/266-yandex-metrica-webvisor/contracts/dashboard-evidence.md` и `specs/266-yandex-metrica-webvisor/quickstart.md`
- [X] T024 [P] [US5] Проверить сохранение production defaults выключенными и отсутствие секретов/реального счётчика в `apps/server/tests/unit/test_product_analytics_provider_config.py`, `apps/server/tests/integration/test_compose_hardening.py` и `infra/env/rec.production.env.example`

### Implementation for User Story 5

- [X] T025 [US5] Сохранить в контракте ручного доказательства точные режимы `pending/blocked/passed`, фактический срок хранения и запрет анализа форм до отдельного утверждения в `specs/266-yandex-metrica-webvisor/contracts/dashboard-evidence.md` и `specs/266-yandex-metrica-webvisor/quickstart.md`
- [ ] T026 [US5] Выполнить ручной smoke в тестовом кабинете Яндекс Метрики после публикации кандидата и зафиксировать redacted evidence Webvisor, карты, ссылки, отказ от быстрых визитов, цели, фильтры и хранение в `specs/266-yandex-metrica-webvisor/contracts/dashboard-evidence.md`

**Checkpoint**: Если кабинета или юридического согласования нет, US5 остаётся
`pending` и не превращается в `pass` из-за зелёных локальных тестов.

---

## Phase 8: Polish & Cross-Cutting Validation

**Purpose**: Сверить спецификацию с реализацией и оставить воспроизводимые
локальные доказательства без изменения production.

- [X] T027 [P] Выполнить focused pytest-набор из `specs/266-yandex-metrica-webvisor/quickstart.md` для публичного consent, инвентаря, внутренних границ, маскирования и отсутствия секретов в `apps/server/tests/`
- [X] T028 [P] Проверить синтаксис контроллера и чистоту diff командами `node --check apps/server/src/twobrain_rec_server/public/static/public/analytics.js` и `git diff --check` в `apps/server/src/twobrain_rec_server/public/static/public/analytics.js`
- [X] T029 [P] Добавить русскоязычный фрагмент изменений и статусы `implementation ready`, `tracker pending`, `legal pending`, `provider dashboard pending`, `release pending` в канонический `changes/unreleased/F266.yaml`
- [X] T030 Выполнить `$speckit-converge` и записать результат сопоставления `spec.md`/`plan.md`/`tasks.md` с кодом и тестами в `specs/266-yandex-metrica-webvisor/quickstart.md`

**Final gate**: Для release нужны exact-SHA PR checks `governance-fast`,
`macos-pr`, `pr-metadata`, подтверждение кабинета и юридический статус. В этой
задаче `infra/scripts/cd-remote.sh --execute` не запускается.

## Dependencies & Execution Order

### Phase dependencies

- Phase 1 → Phase 2 → US1 → US2 → US3 → US4 → US5 → Polish.
- US2 depends on the consent controller from US1.
- US3 depends on the shared gate from Phase 2 and reuses US1's controller, but
  it must remain fail-closed for every internal page.
- US4 can be reviewed against the stable contract after US1–US3 define runtime
  behavior.
- US5 depends on the final runtime and disclosure text; T026 requires a test
  provider account and is intentionally a manual pending gate until performed.

### Parallel opportunities

- T002–T004 touch separate foundational concerns and may be prepared in parallel,
  but the shared gate is integrated sequentially before story work.
- T005–T006, T009–T010, T014–T016, T023–T024 and T027–T028 are independent test
  work on separate files.
- T020 is independent of the runtime implementation but must pass against the
  final wording.

## Implementation Strategy

1. MVP: complete Phase 1–3 and prove no-request-before-consent plus revoke.
2. Add the public funnel and Webvisor only on `/` and `/download`.
3. Add internal safe metadata with server-side allowlists and no replay.
4. Synchronize disclosure, then run automatic checks and convergence.
5. Keep legal approval, provider dashboard smoke and release as explicit gates;
   never infer them from source or unit tests.

## Notes

- `[P]` означает разные файлы без незавершённой зависимости, а не разрешение
  менять один и тот же файл одновременно.
- Чекбоксы `checklists/security.md` и `checklists/requirements.md` принадлежат
  ревьюеру; реализация их не меняет.
- Публичное событие скачивания означает намерение/начало загрузки, а не успешную
  установку приложения.
