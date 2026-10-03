# F280 — проверки T036/T037 перед выпуском

Дата:2026-10-03. Lane:high-risk-product / active Spec Kit slice. Production и реальные денежные операции этими проверками не выполнялись.

## Причинные отказы

T037: независимый browser reviewer показал реальный потерянный сигнал до подготовки формы после14с pending ответа; 1FAIL/35deselected, bridge errors0, один POST303. Подробности в validation-payment-browser.md и graf-f280-slow-reply-process-diagnostic.log.

Первый root вариант htmx.process(form) прошёл последовательность пяти начал и дошёл до собственного RED T036 (graf-f280-t037-green-t036-red.log): assertion idle deadline message false, 1FAIL/35deselected,7.99с. Независимый reviewer предупредил о повторной обработке активной формы во время штатного settle; вариант заменён до окончательной проверки.

Окончательный T037 переносит только запуск дальнейшей автоматической проверки в afterSettle; afterSwap завершает запрос и фокус, общий initCabinet после afterSwap откладывает ту же инициализацию. Первоначальная инициализация сохраняется. При таком коде естественные пять начал0/14/28/42/52с прошли и RED T036 снова получен: assertion idle deadline reveals honest pending message without reinit false, 1FAIL/35deselected,7.91с. Лог graf-f280-t037-settle-green-t036-red.log.

T036 deadline callback прекращает новые старты, а без текущего запроса в том же активном видимом контексте вызывает существующий вывод исчерпания. Собственные15с активного запроса, one-flight, контекст и финансовые границы сохраняются.

## Адресная проверка

Команда: GRAF_PAYMENT_RETURN_BROWSER=1 GRAF_BROWSER=<engine> GRAF_NODE_MODULES=<existing dependencies> apps/server/scripts/run_local_postgres_tests.sh --focused tests/contract/test_billing_payment_return_browser.py -k 'idle-five or deadline' -q --tb=short --show-capture=no.

- Chromium:8PASS/28deselected,63.15сpytest/68сphase, graf-f280-t036-t037-chromium-green.log.
- WebKit:8PASS/28deselected,67.22сpytest/71сphase, graf-f280-t036-t037-webkit-green.log.

Каждый вариант использует настоящие browser HTTP→ASGI→PostgreSQL; source changes не подменяются reinit или fake server success. Сохраняются document/context/SQL/provider-create-negative assertions. Source JS SHA256:4516b74b639a7ba31807ecbbd758b961220785d278f96ec16b9c07dfe09da5dd.

Static contract:76PASS/2.23с; local governance PASS.

Полная новая36case матрица обоих браузеров выполняется отдельно и не считается завершенной заранее. Source review, GitHub exact-SHA gates, Full/CD/live observation — отдельные допуски.


## Полная матрица выявила регрессию контекста

Первая полная36case Chromium матрица:34PASS/2FAIL,174.73с; отказы guards320/1280, остальные34 прошли. WebKit:34PASS/2FAIL,190.86с; те же guards320/1280. Логи graf-f280-payment-return-final36-*.log. T037 defer всей status инициализации откладывал immediate guards в общем afterSwap при явном изменении контекста. Это product regression, не маскируется изменением tests. Исправление: initBillingStatusRefresh принимает deferScheduling; afterSwap по-прежнему немедленно проверяет/блокирует контекст и показывает бюджет/ошибки, до afterSettle откладывается только назначение следующего таймера. Полный повтор матрицы обязателен на новой source версии. Прежние reviewers на предыдущем hash не объявляются окончательным допуском.


## Окончательная полная браузерная матрица на исправленном контроллере

- Chromium:36PASS/184.79сpytest/190сphase, graf-f280-payment-return-final36-chromium-v2.log.
- WebKit:36PASS/201.58сpytest/205сphase, graf-f280-payment-return-final36-webkit-v2.log.
- Static assets contract:76PASS/2.31с; local Spec Kit governance PASS; diff --check PASS.

Все18групп на320/1280: success/historical/pending/canceled/cancel-on-check/refused/service-gap/errors/guards/lifecycle/timeout/native/a11y/provider-unavailable/deadline-success/deadline-pending/deadline-timeout/idle-five. Включены естественные slow replies, отсутствие шестого старта после idle60с, собственный15с timeout и безопасный local GET, реальные защищенные POST303/GET/SQL, document/context/financial-negative assertions. Прежние34PASS2FAIL записаны отдельно и исправлены без изменения тестовых требований. Контейнеры удалены.

Проверенные SHA256 после обоих прогонов: JS4ca35f0a1e8b9f96c96ff69933e2e8acb06b657bb7c863197a713ac5a70d9324; browser test d13ce7a2d2a0d211a30161cf47e844265901046b0b5621079d1075b2a8b53971; Python test3c38a7f651d52eb9f0807cb692f5550c2cbd63d3a6a4cafa16ebae858c6cc3f9. Source после этого не менялся. Это синтетический провайдер с настоящими браузером/сервером/БД, не доказательство настоящего банковского зачисления/возврата/renewal или пользовательской конверсии.
