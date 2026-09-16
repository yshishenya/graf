# Быстрая проверка фичи

## Предварительные условия

- Рабочий каталог: `/Users/yshishenya/.codex/worktrees/06f1/crisp`.
- Python 3.13+ и зависимости `apps/server` установлены.
- Для локальных тестов используются синтетические настройки и тестовая база;
  реальные счётчики, cookies и идентификаторы посетителей в evidence не копируются.
- Кабинет Яндекс Метрики и юридическое подтверждение проверяются отдельно и не
  подменяются локальными тестами.

## Автоматические проверки

```sh
cd /Users/yshishenya/.codex/worktrees/06f1/crisp/apps/server
pytest -q \
  tests/unit/test_public_analytics.py \
  tests/contract/test_public_analytics_contract.py \
  tests/contract/test_product_analytics_replay_webvisor_boundaries.py \
  tests/contract/test_product_analytics_yandex_provider_contract.py \
  tests/contract/test_product_analytics_page_inventory_096.py \
  tests/contract/test_product_analytics_posthog_autocapture_contract.py \
  tests/integration/test_product_analytics_autocapture_pages.py \
  tests/integration/test_product_analytics_yandex_page_scope.py
node --check /Users/yshishenya/.codex/worktrees/06f1/crisp/apps/server/src/twobrain_rec_server/public/static/public/analytics.js
git -C /Users/yshishenya/.codex/worktrees/06f1/crisp diff --check
```

Проверки должны подтвердить отсутствие запуска до выбора, независимость
`behavior_replay`, fail-closed инвентарь, безопасные поля и отсутствие секретов.

## Браузерный сценарий

1. Открыть `/` в чистом профиле и включить журнал сети.
2. До выбора убедиться, что нет запросов к `mc.yandex.ru`, Webvisor,
   first-party capture endpoint или иным необязательным провайдерам.
3. Выбрать «Только необходимые»: перейти на `/download`, обновить страницы и
   убедиться, что необязательный сбор не появился.
4. В настройках выбрать только «Аналитика»: убедиться, что просмотры/цели
   разрешены, но Webvisor, карта кликов и карта прокрутки не запускаются.
5. Отозвать выбор через «Настройки cookies», обновить страницу и убедиться, что
   новые необязательные запросы отсутствуют.
6. В новом чистом профиле выбрать «Аналитика» и «Поведенческая запись». Проверить
   `/` и `/download`: контроллер передаёт `clickmap: true`, `trackLinks: true`,
   `accurateTrackBounce: true`, `defer: true` и `webvisor: true` только на этих
   поверхностях.
7. Открыть вкладку продукта, FAQ, CTA и прокрутить страницу. Убедиться, что
   события используют только каталог стабильных значений.
8. В тестовой авторизованной сессии проверить безопасные внутренние классы:
   продуктовые метаданные доступны только после существующего gate и browser
   opt-in, Webvisor не запускается.
9. Открыть meeting, playback, deletion, billing, auth, OAuth, admin и embedded
   поверхности. Убедиться, что Яндекс и запись заблокированы, а чувствительные
   значения не уходят ни в событие, ни в журнал.

## Кабинет и выпуск

Выполнить шаги из [dashboard-evidence.md](contracts/dashboard-evidence.md). В
итоге отдельно записать `implementation ready`, `tracker pending`,
`legal pending`, `provider dashboard pending` или подтверждённые статусы. Не
включать production и не публиковать счётчик только на основании этого файла.

## Фактически выполненный браузерный smoke

16 сентября 2026 года проверен установленный GRAF Dev на exact SHA
`2dea56f4240f10b6ecdb1df20e3f1a9e1d48e66a`, manifest
`dev-2dea56f4240f`, через `http://127.0.0.1:8081/` в чистой браузерной
сессии. В Dev используется синтетический счётчик `12345678` и режим
`render_only`: внешний тег и внешняя передача намеренно не выполняются.

- До выбора пользователя были только first-party статические запросы; запросов
  к `mc.yandex.ru`, Webvisor и capture endpoint не было. В localStorage и
  cookies не было состояния согласия.
- «Только необходимые» сохранило только `necessary`; необязательная Метрика,
  цели и запись не запустились.
- Только `analytics` создало обычный `hit` и безопасные публичные цели с
  `clickmap=false`, `webvisor=false`, `trackLinks=true`,
  `accurateTrackBounce=true`, `defer=true`, `trackHash=false` и
  `form_analytics=false`.
- Добавление `behavior_replay` после уже выданного `analytics` вызвало штатную
  перезагрузку. После неё на `/` queue Метрики содержала
  `clickmap=true` и `webvisor=true`; `trackLinks`, `accurateTrackBounce` и
  `defer` оставались включены, `form_analytics=false`.
- На `/download` при тех же категориях зафиксированы `surface=public_download`,
  событие `public_download_viewed` и такой же режим Webvisor/карт.
- Отзыв `behavior_replay` вызвал перезагрузку с `clickmap=false` и
  `webvisor=false`. Отзыв `analytics` перевёл контроллер в `revoked`, включил
  блокировку счётчика и не добавил новое событие после открытия FAQ.
- `/privacy`, `/login` и перенаправленный без авторизации `/meetings` не
  содержали контроллер публичной аналитики, `window.ym` или тег Метрики.
- В evidence не сохранялись идентификаторы посетителей, cookies, сырые записи,
  тексты форм, аудио, расшифровки или содержимое встреч. В консоли браузера —
  `0 errors`.

## Результат сверки и текущие статусы

Проверено 16 сентября 2026 года. Результат `$speckit-converge`: **converged** —
текущая реализация покрывает требования `spec.md`, решения `plan.md`, задачи
`tasks.md` и применимые принципы конституции; новых обязательных задач в раздел
Convergence не добавлено.

- Сверено: 25 функциональных требований, 10 критериев успеха, 16 сценариев
  приёмки и все 8 фаз текущего списка задач.
- Reviewer-owned чеклисты подтверждены ревьюером: requirements `16/16`,
  security `14/14`; отдельная security-проверка завершена с результатом
  `APPROVE`.
- Автоматические доказательства на exact SHA: focused-набор из этого файла —
  `47 passed`; соседний набор публичных юридических, конфигурационных,
  provider и compose-проверок — `117 passed`; `node --check` и
  `git diff --check` — успешно.
- Dev-harness: `build --live`, `promote --live`, `status --json` и
  `smoke --json --live` на manifest `dev-2dea56f4240f` — успешно; backend,
  frontend, workers, база, миграция, хранилище, Temporal и подписанный
  `/Applications/GRAF Dev.app` привязаны к тому же exact SHA.
- Фрагмент `changes/unreleased/F266.yaml` прошёл
  `scripts/validate-changelog-fragments.py`.
- Браузерный smoke на этом exact SHA — `passed`. Ручной smoke в кабинете
  Яндекс Метрики, фактический срок хранения и юридическое согласование —
  `pending`; локальный `render_only` не подменяет эти gates.
- Итог фичи: `implementation ready`, `browser smoke passed`; `tracker pending`,
  `legal pending`, `provider dashboard pending`, `release pending`.
  Production не менялся, настоящий счётчик не публиковался.
