# F280 — окончательная совместимость платежного документа T059

Полоса: high-risk-product, продолжение существующего Spec Kit. Проверены объединенные локальные файлы invoice/T059 поверх подписки PR7506 и восстановления чека F278. Историческая база invoice3cf и исходный коммитdb2baf сохранены; до текущего PR коммиты переносятся на фактическую основу с отдельной сверкой байтов.

Требования T059 независимо проверены: invoice checklist14checked/0unchecked, issue7530, review-invoice-t059-requirements.md. Три причинных отказа: старый blanket запрет форм, новая receipt copy с ё, одна такая же буква в подписи подписки. Полный support/copy RED:3failed/80passed0.20s. Минимальная правка сохраняет receipt form, CSRF, доступ владельца, точный receipt-only endpoint, денежные обработчики и API. Только тексты и содержательный контракт формы меняются.

Полные support/UI/copy contracts GREEN:186passed0.59s. Проверены rendered default/false/unavailable/true состояния: отсутствие формы либо ровно одна protected receipt форма с точным action/method и единственным CSRF input; блок помощи не содержит form/submit, formaction запрещен, provider refund API не появляется. При первом запуске нового render-test не хватило обязательного synthetic receipt_label; исправлен только тестовый контекст. Этот промежуточный отказ не был ошибкой продукта.

Целевая одноразовая PostgreSQL выборка invoice projections и F278 late receipt/paid-refused/nonrecoverable:74passed/83deselected54.09s, runner59s, collection digest ca5f807ccc7f29fc3a867b50de3f342d494e65bc201fdb5d719342cdbaf46dc7, isolated_container_removed. Проверка выполнена до последних copy-only/test-guard/glyph правок. После них money/DB/route файлы не менялись; результат не называется повторным полным post-fix прогоном.

Окончательный combined accessibility: Chromium16passed63.49s; WebKit16passed97.35s. Перед успешным WebKit повтором сохранен первоначальный15passed/1failed120.67s — внешний subprocess timeout120s, без завершенного assertion failure. Полный последовательный повтор сохранил assertions и предел120s. По узкому PASS причина исходного таймаута не объявляется доказанной. Проверены320–1280, обе темы,100/200%, keyboard/focus, native details/copy/receipt/support и работа без JavaScript. Обе NoJS группы подписки и invoice сохранены. Изображения только synthetic и не доказывают состояние production/provider.

Отдельный read-only capture закрытой карточки выполнен из тех же сохраненных pages.json и текущих CSS/JS. Он помогает независимому визуальному обзору; не считается дополнительным тестовым прогоном. Десять final source/test fingerprints сохранены внеgit и сверяются после commit/rebase; подписка меняет только «Проверить платёж»→«Проверить платеж», hash34523d26edfff86ccd9044c70013ccd392fbbd716b5221411e77f8ef15f38aa8.

Ruff измененных Python файлов, Node syntax, governance, changelog fragments и git diff --check PASS. Независимый source report и отдельный visual report имеют собственные terminal решения; их результаты добавляются как отдельное доказательство, автор не переписывает reviewer findings. Независимый T058 source impact F278 сохранен в review-subscription-t058-rebase-7520.md.

Команды из apps/server:

```sh
uv run --extra dev pytest tests/contract/test_payment_history_support.py tests/contract/test_billing_ui.py tests/contract/test_copy_convention_contract.py -q --tb=short --show-capture=no
BILLING_VISUAL_OUTPUT_DIR=/tmp/f280-invoice-combined-chromium uv run --extra dev pytest tests/contract/test_billing_accessibility.py -q --tb=short --show-capture=no
GRAF_BROWSER=webkit BILLING_VISUAL_OUTPUT_DIR=/tmp/f280-invoice-combined-webkit-repeat uv run --extra dev pytest tests/contract/test_billing_accessibility.py -q --tb=short --show-capture=no
```

Команда из root:

```sh
apps/server/scripts/run_local_postgres_tests.sh --focused tests/integration/test_billing_clarity.py tests/integration/test_billing_purchase_journey.py -k 'invoice_projection or completed_purchase_recovers_late_receipt or paid_refused_renewal_recovers_receipt or invoice_hides_receipt_refresh' -q --tb=short --show-capture=no
```

Current exact SHA/base PR checks, merged source, frozen release-full/GO, dry-run/execute и live production остаются обязательными следующими воротами T055/T056. GRAF Dev, реальные платежи/письма/возвраты, финансовая F278 и человеческие SC005/006 этим отчетом не подтверждаются. Пользовательское решение о предвыборе автосписаний везде сохранено.
