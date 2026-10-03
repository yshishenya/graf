# F280 — независимые проверки перед выпуском

Дата:2026-10-03. T031/source PASS, открытых применимых существенных замечаний0.

- return_requirements: независимые требования и UI/payment/worker/CD coverage; `review-payment-return-ui.md`, checklist17/0, FR-031 wording подтвержден.
- return_live_check: автор worker, независимо проверил UI/controller/routes/CD; `review-payment-return-ui-worker.md`, UI-R1–R6 закрыты по source и actual tests. Собственный worker review здесь не заявляется независимым.
- return_design: автор browser bridge/tests, независимо проверил production UI/controller/routes/worker/database/CD; `validation-payment-browser.md`, current source hashes и coverage PASS, pending regression закрыта.

Матрица:full Chromium27PASS/1initial GET timeout; full WebKit28PASS; pending320/1280 после correction2PASS каждого engine; a11y2PASS каждого engine. Root389regressionPASS,129staticPASS,53pendingcontractPASS; worker25+19PASS; CD56PASS; recovery91PASS общего набора плюс исправленный targeted1PASS. Исходные RED и неудачные попытки в evidence сохранены.

Сведение:$speckit-converge, `converge-payment-return.md`, новых обязательных unbuilt gaps0. Выполненные T029/T030/T031/T033 можно отметить по этим доказательствам. T032 остается до current-base/exact-SHA PR/Full/CD/live closeout. Live payment/receipt/bank/refund/recurring/human acceptance этим source PASS не подтверждены.
