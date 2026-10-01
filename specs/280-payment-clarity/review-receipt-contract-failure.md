# Независимая причинная классификация отказа release-full36798151219

**Отказ вызван устаревшим договорным тестом, а не найденным дефектом runtime. Минимальная test-only поправка обоснована.** Проверка только чтением по code-reviewer: текущий HEAD694aa867, требования/plan, checkout/storagetemplates, contract/integration/DOMпроверки и shard2log. Репозиторий/Git/PR/GitHub/БД/deploy не менял, тесты/агентов не запускал; записан только этот собственный отчёт.

## Точная причина

Падает **apps/server/tests/contract/test_billing_clarity.py**, а не одноимённый integrationфайл. В shard2log единственныйFAILED `test_checkout_missing_receipt_contact_provides_recovery_without_money_form`, line113: запрет видимого `input[name=promo_code]`. Следующая строка114 запрещает «Есть промокод?» и также устарела; она не исполнилась после первого assert. Это заголовокsummary раскрываемого промокода, не новый запрет ordertotal. Тест не содержит отрицательного утверждения про billing-order-summary в этом сценарии.

Plan105 прямо требует редактор промокода до подтверждения почты при запрете start/денежного действия. Это согласовано с specedgeFR005/008/011/017/018 и независимыми requirements. Checkouttemplate условие промокода зависит от billing_enabled/catalog_ready/notblocked, receiptgate расположен после редактора и перед startform. Поэтому редактор присутствует намеренно; ветвь notreceipt отображает проверкупочты, а startform в elif не рендерится. Предварительная цена/проверка кода не является разрешением оплаты.

Согласованное положительное покрытие уже имеется:
- contract/test_billing_ui.py `test_checkout_allows_promo_correction_before_receipt_email_verification`: editableescapedinvalidcode, Apply, clearinstruction, previewform, accountrecovery, отсутствие start/offerconsent/recurringconsent;
- integration/test_billing_promo_refresh.py `test_unverified_receipt_allows_readonly_promo_correction_and_clear`: invalid→edit/clear при отсутствующемstart и видимой почте;
- integration/test_billing_clarity.py missingverifiedemail web/desktop: recoverylinknextyear, отсутствиеstart, прямойPOSTstart→receipt_contact_required и financialcounts0/0;
- stale_start_error_receipt regression проверяет прямой отказ, сохранение B/year/expiry без разрешения платежа; DOMpromo-refresh проверяет receiptverified/unverified согласно текущему harness.

Runtime `start_billing_checkout` проверяет verifiedreceipt после recoveryexistingoperation и до новых финансовых действий; отсутствующий контакт возвращает receipt_contact_required. Наличие editablepreview не обходит guards. Продолжение существующей операции без почты — намеренная идемпотентная recoveryсемантика, защищено отдельнымintegrationtest.

## Минимальный фикс и аналогичные ожидания

В одном failingcontract заменить **обе строки113/114** на положительные утверждения editableinput, привязки к previewform/Apply и видимого «Есть промокод?». Сохранить сообщение/ссылку подтвержденияпочты и запретstart. Для явного защитного договора добавить отсутствие offer_consent/recurring_consent/денежнойsubmitкнопки (либо сохранить имеющееся положительноепокрытие contractUI); в этом сценарии recovery является главным денежным следующим шагом. Testtitle уже корректен: recoverywithoutmoneyform, переименование не нужно. Не менятьruntime для возвращения скрытого редактора, не просто удалятьassertions, не менять receiptфинансовыеguards.

Поиск аналогичных отрицательных ожиданий во всём testsдереве и billingfiles выявил:
1. **Тот же failingcheckouttest line114** — исправить вместе с113, иначе следующийFullупадётнаследующемassert.
2. contract/test_billing_clarity.py storageбезreceipt line207/208: input/couponзапрет **действующий**, storagetemplate специально имеет receiptgate дляcoupon. Новый planоговорён checkouteditor, storageне менялся. Этот тест не устарел, его не менять.
3. contract/test_billing_ui.py pendingcheckoutorder-summaryline722: скрытие recomputedtotalприуже созданномплатеже **действующее**, unrelatedreceipt. Не ослаблять.
4. Остальные searchedbillingreceipt/promo assertions согласованы с текущимview. Второго отдельногоустаревшегоcheckoutконтракта не найдено.

Предлагаемое локальное выполнение после testfix: весь contract/test_billing_clarity.py + contract/test_billing_ui.py и integration/test_billing_clarity.py + соответствующаяunverifiedpromoрегрессия; общие guards сохраняются. Это рекомендации состава проверки, я запуск не выполнял.

## Выпуск

Замороженныйcandidate694aa867/release-full36798151219 имеетFAIL и не может получитьGO/deploy. Старый manifest/trainне переписывать, failedrunне объявлятьуспешным и не повторятьFullнатомжекандидате. Test-onlyкоммит требуетновыхexactSHAchecks/merge, новогofrozenactualsource и одногоauthoritativeFullдляновогокандидата. Frozenстарыйchangelog можносохранитьсодержательно, ноidentityдолжнавновьпройтиштатныйdriver. T019открыт, T011/T012/F278неподменяются этойпочинкой теста. Реальнаяфинансовая/человеческаяприёмкане подтверждена.
