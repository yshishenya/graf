# Итоговый независимый security обзор receipt-контракта F280

**Scoped PASS исправленной test-only коррекции.** Найденное при первом обзоре замечание о видимости свёрнутой Apply-кнопки устранено. Новых конкретных исправимых замечаний в прочитанной области нет. Категория active high-risk-product slice; применён code-reviewer. Только чтение: код, документы репозитория, Git/GitHub, БД, release/deploy не менял; тесты и агентов не запускал. Записан только этот собственный отчёт.

## Проверенные границы

В `test_checkout_missing_receipt_contact_provides_recovery_without_money_form` сохранены проверка сообщения «Подтвердите почту для чека», ссылка восстановления аккаунта и запрет action=/billing/checkout/start. Новые положительные assertions требуют форму с id=billing-promo-preview/action=/billing/checkout/preview, текстовый promo_code input и Apply-кнопку, связанные с ней через form attribute. Сохраняется видимый summary «Есть промокод?», а содержимое раскрывается по запросу. Действующий шаблон использует POST для preview и отдельный receipt guard для оплаты.

Отрицательные assertions запрещают inputs offer_consent/recurring_consent/quote_id/idempotency_key, кнопку с data-billing-primary и видимое «Оплатить». Поэтому успешный тест не может подтвердить скрытую денежную форму вместо предварительного редактора. Синтетический fixture намеренно имеет quote/idempotency в общем контексте, но receipt_ready=False запрещает их перенос в HTML оплаты. Ссылка «Подтвердить почту» допустима и не запрещается ошибочно как главный элемент.

Исходный test-only снимок a3f7b234a8cfde4046b6967a0a5debc712df8481d98cd8d8070d373fe982284a содержал неверное `assert "Применить" in page.visible`. При отсутствии кода/ошибки details закрыт, Page.handle_data исключает его содержимое вне summary, поэтому Apply ещё невидима. Замечание передано основному агенту сразу; удалён только этот assertion. Node assertion правильной Apply-кнопки и все денежные запреты сохранены. Шаблон/CSS/renderer ради теста не менялись. Предварительный Request changes относился к тому снимку, не к текущему 6b088.

`contracts/payment-journey.md:31` теперь соответствует ранее принятому spec/plan: редактор допускается для проверки/исправления/очистки до почты, а согласия и денежное действие недоступны. Account next не переносит code/quote/согласия, действующий signed draft ограничен той же сессией и исходным TTL. Семантика доказательства владения почтой/receipt/start не изменена.

## Актуальный прочитанный результат

Перезапущенный основным агентом `/tmp/graf-f280-refresh-receipt-contract-final.log` прочитан только после завершения для исправленного 6b088 теста: **329 passed, 2 warnings,179,06 с**, runner 183 с, status=pass, postgres_test_result=pass, isolated_container_removed. Collection 329 digest `3c8360b581fd7605bed25070d9d95075ed86843c2acd1f272cbf00bd6df75338`; SHA256 лога `4b059e2ce9398c25b0706edce35d03322d0c5ca7c39f7115384cf04139e91629`. Я не запускал набор самостоятельно. Первоначальный незавершённый журнал, исторические313/DOM/CI и отказавший frozen release-full не принимались за новый PASS.

Прочитан current diff: runtime/шаблон прежних fec78/8351694f не менялись, коррекция ограничена контрактным тестом и соответствующими документами. Existing HTTP unverified-receipt invalid→edit→clear сохраняет отсутствие start; синтетические money-path/security/lifecycle регрессии входят в прочитанный текущий набор. Никакой реальный провайдер, платёж, чек или банковская операция мной не проверялись.

## Требования и ворота

Независимый предварительный report `/tmp/graf-f280-receipt-contract-requirements-security.md` остаётся применимым после синхронизации редакционной фразы: custom UX 18/0, presentation 6/0, refresh 9/0, итого 33/0; встроенный 8/0 отдельно. Отметки не менял. Scoped analyze и issue sync не заменяют реализацию/CI/release; T018 переоткрыт для текущих результатов и независимых обзоров. T019 остаётся открытым до нового exact-SHA PR и frozen release-full/dry-run/deploy/runtime proof. Failed frozen candidate 36798151219 не становится пригодным к production от этого локального результата.

## SHA256 проверенного снимка

```text
test_billing_clarity.py
6b088ff18ffa4a391e72c14ba21969473a5935021aeecfd0795237e09a0c44c2
contracts/payment-journey.md
9e64a769cd01f97b94d062f09fa7edbb7283d5ddaa0b3d893e97394678fac1bd
billing.py
fec78d91a5ef03f667ddf34524afd6aaa787d1d6f1189bd3bfeb952d847a80c3
billing_checkout_content.html
8351694ffbd603639a6e05bd7bcd033ca3f33df4874128b67c220763b9a23556
```

## Пределы допуска

Scoped PASS относится к корректной test-only спецификации редактора и запрета денежных элементов, прочитанным источникам и текущему завершённому 329 набору. Он не подтверждает release/production/installed Dev, реальные деньги/чеки/банковское зачисление/возвраты, человеческую приёмку или конверсию. T011/T012/F278 остаются открытыми в прежнем объёме. Разрешение владельца на публичную оплату и технический production уже дано, повторного разрешения этот обзор не требует. Отсутствие конкретных замечаний не является гарантией отсутствия любых будущих ошибок.
