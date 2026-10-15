# F280: проверка двух замечаний к PR7465

Дата: 2026-10-03, UTC+3. Режим: продолжение существующего high-risk-product / full Spec Kit F280, задачи T026–T028; коммиты, выпуск и закрытие задач выполняет основной агент. База проверки: `b2ce252ce91db79a58a06687e355cf2b6f40bf51`, изменения ниже находятся в рабочем дереве. Рецензентские чеклисты не изменялись.

## Исправления

1. При `checkout_result=account_unavailable` общий `checkout_available` становится false. Шаблон сохраняет понятное сообщение о недоступной оплате аккаунта и обращении в поддержку, но убирает цену к оплате, форму запуска, платежные идентификаторы и согласия. Ошибка аккаунта не преобразуется в `pending` и не сообщает ложно, что платеж уже создан. Проверены как отсутствующий `checkout_blocked`, так и явный false.
2. Ручная ссылка восстановления содержит только подтвержденный период текущего расчета: `/billing/checkout?cycle=month` либо `/billing/checkout?cycle=year`. Любое другое значение шаблона дает month. Промокод, платежные идентификаторы и согласия в ссылку не попадают. После успешной подмены HTML при проверке промокода новая ссылка получается из нового серверного шаблона; после ошибки показывается ссылка последнего подтвержденного расчета. Изменение `cabinet.js` не требуется.

Производственный файл изменен один: `billing_checkout_content.html`. Новый SHA256: `9c68661848504e02b02f067f7e2a3f759fa0c04fd7f808354e4388c1d06d54b2`. JavaScript не изменен: SHA256 `95f5d619f7cab0d70e1b604f0c6fccaba5ce47b91c756ae4fc9073ac75baeb34`.

## Воспроизведение до исправления

- Пять новых проверок шаблона: 5 FAIL,16 deselected,0.16с. Две выявили оставшуюся форму оплаты при ошибке аккаунта; три — отсутствие периода в ссылке восстановления. Артефакт `graf-f280-inline-followups-contract-red.log`.
- Chromium320: 1 FAIL,27 deselected,11.96с; runner17с. Отказ непосредственно на проверке href: прежний `/billing/checkout` вместо `/billing/checkout?cycle=year` после годового расчета без сохраненного промокода и ошибки500. Строка386 браузерного сценария; диагностическое имя стадии оставалось от предыдущего шага `inline-unexpected-html`. Bridge errors пусты, контейнер изолированной базы удален. Артефакт `graf-f280-inline-followups-chromium-red.log`.

## Результаты после исправления

| Проверка | Результат | Время pytest / runner | Артефакт |
| --- | --- | --- | --- |
| Полные contract UI + clarity | 74 PASS | 0.24с | `graf-f280-inline-followups-ui-green.log` |
| Ограничение аккаунта: disabled/expired/exhausted × ordinary/promo-removed | 6 PASS,101 deselected | 12.26с /16с | `graf-f280-inline-followups-account-green.log` |
| Chromium inline-errors,320/1280 | 2 PASS,26 deselected | 19.58с /24с | `graf-f280-inline-followups-chromium-green.log` |
| WebKit inline-errors,320/1280 | 2 PASS,26 deselected | 21.89с /27с | `graf-f280-inline-followups-webkit-green.log` |

Браузерные сценарии сохраняют прежние HTTP500/429/401/403, сетевую ошибку и неожиданный HTML. Добавлен седьмой шаг: убрать промокод, подтвердить годовой расчет через существующий запрос, выключить автопродление, принять оферту, получить ошибку500 и явно перейти по ручной ссылке восстановления. До перехода сохраняются окно, документ, длина истории и выбранный год; старая кнопка оплаты заблокирована. При явном переходе происходит ровно одна загрузка документа; год и полная годовая цена сохраняются без помощи сохраненного промокода, автопродление остается false, новая оферта непринята и свежая форма оплаты доступна. Во время проверок промокода документ не перезагружается.

ASGI bridge проверяет отсутствие финансовых строк после каждого inline запроса; provider payloads пусты и внешние запросы отсутствуют. Account regression содержит явный запрет вызова `_create_initial_checkout_payment`, проверяет rollback всех финансовых строк и неизменность бюджета. Все изолированные контейнеры PostgreSQL удалены штатно. Новые проверки не вводят реальные коды и не создают настоящую оплату.

Ruff по трем измененным Python tests, `node --check` для браузерного сценария и `git diff --check`: PASS. Чеклисты, продуктовые задачи, GitHub и production этим агентом не менялись; commit/push не выполнялись. Основные финансовые и браузерные матрицы предыдущей проверки остаются отдельным доказательством; этот отчет покрывает только два исправления замечаний к PR7465.

## Команды

Из корня репозитория:

```sh
apps/server/.venv/bin/python -m pytest apps/server/tests/contract/test_billing_clarity.py -k 'unavailable_account or manual_preview_recovery' -q --tb=short --show-capture=no
apps/server/.venv/bin/python -m pytest apps/server/tests/contract/test_billing_clarity.py apps/server/tests/contract/test_billing_ui.py -q --tb=short --show-capture=no
apps/server/scripts/run_local_postgres_tests.sh --focused tests/integration/test_billing_promo_refresh.py -k account_restriction -q --tb=short --show-capture=no
GRAF_PROMO_BROWSER=1 GRAF_BROWSER=chromium apps/server/scripts/run_local_postgres_tests.sh --focused tests/contract/test_billing_promo_refresh_browser.py -k 'inline-errors' -q --tb=short --show-capture=no
GRAF_PROMO_BROWSER=1 GRAF_BROWSER=webkit apps/server/scripts/run_local_postgres_tests.sh --focused tests/contract/test_billing_promo_refresh_browser.py -k 'inline-errors' -q --tb=short --show-capture=no
```

## Границы

Синтетические проверки не подтверждают реальные деньги, привязку карты, последующее списание, чек, зачисление, возврат, человеческую приемку либо конверсию. T011/T012, F278/#7285 и umbrella#7366 сохраняют прежние открытые границы. Для текущего изменения обязательны новый exact-SHA PR gate и выпуск основным агентом.
