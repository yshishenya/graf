# Quickstart: Production Landing Refresh Validation

## Активный срез G026, 01.11.2026

Для R179-01–R179-05 сначала выполнить существующие unit/contract проверки лендинга:

```sh
bash apps/server/scripts/run_local_postgres_tests.sh --focused \
  tests/unit/test_public_landing.py tests/contract/test_public_landing_contract.py
git diff --check
```

Запускать из корня репозитория: штатный исполнитель создаёт отдельный PostgreSQL для проверок и удаляет его после завершения. Прямой pytest без тестовой БД не принимает восемь сценариев с общей фикстурой; его частичный результат не является PASS всего набора.

В изолированном браузере проверить ширины 280/320/390/768/1024/1440 CSS px в обычном виде и с удвоенными вычисленными `font-size` и численным `line-height`. Во всех случаях открыть FAQ, пройти три панели и проверить отсутствие горизонтальной прокрутки, перекрытия текста, недоступных кнопок и ссылок. Отдельно включить настоящий масштаб браузера 200%; изменение CSS или `deviceScaleFactor` им не считается. Проверить normal/hover/focus после завершения переходов: контраст кнопок и двух подписей подвала ≥4,5:1, видимый фокус и клавиатурные ArrowLeft/ArrowRight/Home/End. Повторить отсутствие JavaScript, отключённые изображения и уменьшенное движение; проверить `/download`, юридические и поисковые страницы, подключающие общий CSS. После проверки удалить временные стили и сбросить эмуляцию. Сохранить метод, размеры, числа и ограничения в `validation/readability-2026-11-01.md`.

Старые разделы аналитики и выпуска ниже — исторический полный объём F179. Этот срез не включает счётчики, оплату или изменение согласия; R179-04 имеет приоритет. T041 не отмечать выполненным без всей его матрицы.

## Focused validation

```bash
cd apps/server
uv run --extra dev pytest -q \
  tests/unit/test_public_landing.py \
  tests/unit/test_public_analytics.py \
  tests/contract/test_public_landing_contract.py \
  tests/contract/test_public_analytics_contract.py \
  tests/contract/test_checkout.py \
  tests/integration/test_product_analytics_yandex_page_scope.py
uv run --extra dev ruff check src tests
cd ../..
node --check apps/server/src/twobrain_rec_server/public/static/public/landing.js
node --check apps/server/src/twobrain_rec_server/public/static/public/analytics.js
git diff --check
```

Expected: tests, lint, syntax and diff checks pass; default-off settings load no external provider.

## Browser matrix

Check 1440x1000, 1024x768, 768x1024, 390x844, 320x800 and 280x653 across `/`, `/download`, legal routes and login handoff. Repeat the critical path at 200% text zoom, with reduced motion and with images disabled. Verify keyboard interactions, no overflow, same synthetic screenshot scenario, all links, non-clickable Windows/Linux and one working macOS package.

## Analytics interception

Stub `window.ym`, exercise every goal in [yandex-goals.md](contracts/yandex-goals.md), and assert exact events and safe payloads. Confirm `mc.yandex.ru` is absent from legal, login, cabinet, admin and meeting pages.

## Repository and deployment gates

```bash
infra/scripts/ci-local.sh --full
infra/scripts/cd-remote.sh --dry-run
```

Before execute: review the exact SHA; refresh backup/rollback evidence; obtain external legal approval for immediate Metrica; configure and test Yandex goals; satisfy the catalog, canary and billing launch gates in `docs/runbooks/billing-launch.md`; obtain explicit deploy authorization.

After execute, verify live/ready health, public routes, package download, goal delivery, containers, logs and exact SHA. Any mismatch triggers rollback and leaves checkout disabled.
