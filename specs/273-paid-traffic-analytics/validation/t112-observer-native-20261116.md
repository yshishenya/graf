# T112 — наблюдение видимого тела и текущего окна macOS

Дата:16.11.2026. Полоса:`high-risk-product`, существующая T112/#7698.
Рабочая копия:`/private/tmp/graf-f273-result-visibility-20261116`.
Ветка:`codex/f273-result-visibility-20261116`, входной
HEAD:`13edb699c1cee3c9b40808b44d3d8d3b0ba01852`.
Это частичный изолированный шаг, не закрытие T112 и не рабочее включение.

## Область

Общий observer в существующем `cabinet.js` принимает только bounded proof
на непустом `div.text` или `p.outcome-item-text` внутри собственного
canonical browser/desktop detail. Проверяются root UUID, connectedness,
IntersectionObserver, rect/viewport, ancestors/закрытые details,
visible/focus/not-prerender. После двух кадров и асинхронной native проверки
заново проверяются документ, root, узел, proof, CSRF, путь и query.

Собственный POST содержит только proof, same-origin credentials/CSRF,
`redirect:error`, no-store и отмену через2s. Ответ JSON ограничен2KiB;
только точная форма accepted прекращает попытки блока. Renewed не принимает
веху, допускается один раз за настоящий переход и требует новой проверки
кадров/native. Неизвестный исход не создаёт timer retry, beacon, storage или
очередь после ухода. Удалённые HTMX-узлы отключаются, ожидания отменяются.
Положительное native refresh/смена nonce, CSRF или query сами не разрешают
повтор при непрерывной видимости. Это клиентское наблюдение штатного показа,
не доказательство внимания человека или защита от подделки своего клиента.

Узкий `EmbeddedCabinetResultVisibilityBridge` принимает только main-frame
`{version:1,nonce}` своего WKWebView, origin и точного owned canonical path.
Ответ содержит только version/ready. AppKit проверяет активное приложение,
прикреплённый видимый view, видимое несвёрнутое окно и occlusion. Поколение
сессии и nonce фиксируются после reconciliation cookies; coordinator
инвалидирует bridge при navigation/detach/termination/auth. Нет native сети,
аналитики, proof, identity или содержимого встречи. Старый клиент без bridge
не даёт нового учёта и сохраняет просмотр.

Рабочие callers по-прежнему не выдают и не передают proof. Серверного
обработчика result-viewed, issuance/renewal и admission в этом шаге нет.
Настоящие `activation_recovery_unverified` и `trigger_unverified` сохранены.

## Предварительные ворота и проверки

[Уточнение договора](t112-observer-native-design-20261116.md) и
[независимый preflight](t112-observer-native-preflight-20261116.md) приняты
до зависящего кода: scoped analyze C/H/M0, blocking clarification0,
четыре reviewer-owned checklist124/0. Уточнённый договор имеет SHA-256
`ee1005b6a59ad1b42f0b7d0af25dd7099c8337a4d11930a3aba9ee6479d270d8`.
Spec/plan/tasks/quickstart, отметки списков и mapping T112→#7698 не менялись.

- Browser RED на отсутствовавшем observer: ожидаемый POST1, фактический0.
  Это отсутствие новой реализации, не отказ рабочего измерения.
- Итоговый серверный профиль:**158 passed,1 прежний fixture warning,0 skips**,
  25.65s,EXIT0. Включает прежние projection/render/protocol/detail проверки,
  Chromium summary picker и новые отдельные Chromium/WebKit observer runners.
  Сценарии: hidden/empty/heading/container/closed details/clipping,
  background/prerender/focus/legacy bridge, processing→ready/HTMX,
  renewal/no retry, pending native + detach/CSRF/root/nonce/focus/proof/pagehide.
- Swift/WK профиль:**69 tests,0 failures**,11.699s,EXIT0. Новых5 тестов:
  canonical маршруты/подделка формы и frame, каждое foreground условие,
  настоящий read-only WK reply/stale generation/current-document и coordinator
  activation после reconciliation с navigation/termination/detach invalidation.
  Соседние session/route/notification/recording/reload/JS-confirm регрессии
  включены в тот же профиль.
- Первоначальный browser fixture зависал, ожидая Promise до его ручного
  разрешения; вызов заменён на невозвращающий обработчик. Исправлен селектор
  CSRF meta. Первый Swift fixture не компилировался с await в XCTest
  autoclosure; расширенный coordinator fixture затем обратился к shared
  notification presenter и получил bundleProxy exception CLI host. Fixture
  переведён на существующий изолированный presenter/UserDefaults; production
  notifications не менялись. Все эти отказы отделены от конечного GREEN.
- Ruff нового Python wrapper, оба `node --check`, `git diff --check` PASS.
- `python3 scripts/validate-changelog-fragments.py` PASS.
- [Независимое чтение кода](t112-observer-native-review-20261116.md):
  PASS узкого observer/native шага, P1=0/P2=0, семь точных хешей совпали.
  Проверяющий не повторял тесты; окончательный Swift GREEN приведён выше
  отдельно по тому же неизменному коду и исправленному fixture.
- HTML:12/24 исходных хеша совпали буквально (все fragment). У12 page
  изменился только cache-version URL существующего cabinet.js с
  `ed427987adad` на `94189c0aba20`. После нормализации только этого URL
  **24/24** совпали с исходным манифестом. Контент и вёрстка не менялись.
- Перед Swift-run доступно166333096KiB, выше резерва80ГБ. Использован только
  свой scratch; приложение не устанавливалось, отдельная app-копия не запускалась.

Команды профилей из корня копии:

```sh
PYTHONPATH="$PWD/apps/server/src:$PWD/apps/server" \
GRAF_NODE_MODULES=/Users/yshishenya/Documents/crisp/apps/server/tests/browser/node_modules \
UV_PROJECT_ENVIRONMENT=/Users/yshishenya/Documents/crisp/apps/server/.venv \
UV_NO_SYNC=1 uv run --project apps/server pytest \
  apps/server/tests/unit/test_result_view_projection.py \
  apps/server/tests/unit/test_cabinet_web_shell.py \
  apps/server/tests/unit/test_meeting_protocol_rendering.py \
  apps/server/tests/contract/test_meeting_detail_reference_contract.py \
  apps/server/tests/contract/test_result_visibility_observer.py -q --tb=short

swift test --package-path apps/macos \
  --scratch-path /private/tmp/graf-t112-visibility-swift-20261116 \
  --filter 'EmbeddedCabinet(ResultVisibility|NotificationSettingsBridge|RecordingSettingsBridge|ReloadRegression|JavaScriptConfirm)|DesktopCabinet(SessionBridge|RoutePolicy)'
```

Журналы и SHA-256:

| Локальный путь | SHA-256 |
| --- | --- |
| `/private/tmp/graf-t112-visibility-server-20261116.log` | `0630bdab8d4d6acb4e284c8f9901eb30218b57aea63ea5f984ef9e8713366105` |
| `/private/tmp/graf-t112-visibility-swift-20261116.log` | `dbaf7ad25ce19d0b5cf553f6291fdb19c89b5ed664f7ac84d0da431bbda7bc00` |
| `/private/tmp/graf-t112-visibility-html-20261116.json` | `3a66d2371091665bf6dab659c011007e173229624d8ee7167812762ba3e86d60` |

Процессы14578 и8194 terminal EXIT0; повторно не опрашивать.
Точные кодовые хеши закрепляет отдельное финальное независимое ревью.

## Сверка оставшейся работы

FR-021/025/SC-006 в пределах client observer/native конкретизации покрыты
причинными тестами. Полная T112 остаётся partial, T113 остаётся открытой:
нужны рабочие issuance/renewal, оба защищённых POST, свежие principal/session/
membership/owner/source/result/digest/deletion проверки после общих fences,
bounded locks/statements и атомарная пара через `admit_account_milestone`.
Это уже область открытых T112/T113, дубль задач не добавлялся, `tasks.md`
побайтово сохранён. Общая convergence, DB/concurrency/failure матрица,
exact-SHA GitHub gates, выпуск и рабочая приёмка ещё не выполнены этим шагом.

Postal, соседние службы, nginx/DNS/Compose, очереди/письма и backup не менялись.
T0 не назначен, Product Radar не отправлялся. Визиты, регистрации, оплаты и
коммерческая цель этим кодом не подтверждаются. Ручная проверка GRAF Dev
и реальное активное окно ещё не приняты; automated WK policy не заменяет их.
