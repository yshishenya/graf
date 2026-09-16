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
- Автоматические доказательства: focused-набор из этого файла — `47 passed`,
  соседний набор публичных юридических, конфигурационных и compose-проверок —
  `52 passed`; `node --check` и `git diff --check` — успешно.
- Фрагмент `changes/unreleased/F266.yaml` прошёл
  `scripts/validate-changelog-fragments.py`.
- Браузерный smoke и кабинетный smoke имеют статус `pending`: общий GRAF Dev
  на момент проверки работал на другом exact SHA, а штатный live-переход
  незакоммиченного кандидата запрещён harness. Проверка старого runtime не
  засчитывается доказательством этой ветки.
- Итог фичи: `implementation ready`; `tracker pending`, `legal pending`,
  `provider dashboard pending`, `release pending`. Production не менялся,
  настоящий счётчик не публиковался.
