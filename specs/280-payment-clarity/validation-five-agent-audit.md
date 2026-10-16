# F280 — пять независимых агентных ролей и исправление доступности

Дата: 2026-10-16. Пользователь поручил пять независимых агентов; каждый первоначально получил отдельную роль без истории/заключений остальных. Запуск в две очереди из-за ограничения одновременных агентов. Это независимые технические заключения, не пять людей и не измерение SC-005/006.

## Проверенный источник

Начальный HEAD `95002a18f47194686642a2dfde99ee843f14808a`, затем документальный `6de02bc59d20bbab1cfa0487e942963509aa9d15`. Серверные исходники/тесты обоих совпадают с выпущенным `79804a512a50e94e618ff3380b472d7f027963d6`; агент платёжной проверки сверил14 контрольных сумм до/после. Ниже результаты исходной версии, а не ещё не выпущенного исправления.

| Роль | Собственная проверка | Результат и границы |
|---|---|---|
|1. Первая покупка и цены|132 существующих contract cases;16 собственных browser cases Chromium/WebKit, месяц/год и скидка|PASS: полная сумма сегодня, обычная сумма следующего периода, срок/правило даты, отдельная оферта и необязательное предвыбранное продление. Данные вымышленные; live каталог не проверялся.|
|2. Оплаченная подписка и объём|161 существующая проверка;11 собственных синтетических сценариев расчёта/реального HTML|PASS increase/decrease, суммы сегодня/следующий период и нулевое отложенное уменьшение; LOW: подпись «Проверить доплату» также при уменьшении.|
|3. Промокод и подтверждение почты|77 проверок без БД; отдельная синтетическая граница signed draft t299/t300|PASS: исправление кода, safe return, сохранение периода в пределах TTL/session, скрытые unbound copy controls. HTTP/PG цепочка отдельно в роли4.|
|4. Неизвестный результат/повтор платежа|505 полных основных +90 дополнительных HTTP/PostgreSQL/unit cases|595 PASS/0 FAIL/0 SKIP. Оба disposable containers штатно удалены. Проверены latest pending/terminal pair, actor/workspace/URL, paid truth, replay/idempotency, email recovery, storage/subscription/purchase и legacy dispatch. Провайдер контролируемый; настоящий банк не проверялся.|
|5. Отключение и доступность|20 existing cases Chromium+20 WebKit;48 собственных keyboard combinations;18 domain/lifecycle|MEDIUM:8 NoJS×320/360×200%×темы/движки обрезают кнопку отмены и условия. Остальные40 геометрических случаев PASS, native синтетическая отправка работает во всех48. Общий scrollWidth скрывает проблему.|

Наборы ролей частично пересекаются: числа не суммируются в число уникальных тестов. Первые попытки роли3 без DSN/импорта и диагностический addStyleTag NoJS роли5 не выданы за PASS; успешные ограниченные повторы и исходные журналы сохранены локально. Новых реальных оплат/отмен/возвратов/писем нет, зависимости не устанавливались.

## Допуск исправления T069/T070

Активный high-risk-product срез F280. Требования FR-010/012/045 и SC-017 уже требуют доступного NoJS пути/масштаба/тем. Append-only уточнения spec/plan/quickstart и Phase29 tasks сохраняют денежные правила, цены, API/БД и решения пользователя: оферта required/unchecked, продление optional/checked везде, явный выбор сохраняется. T066–T068 другого владельца не перенумерованы.

Scoped analyze: critical0/high0/medium0 в намерении задачи, уточнений0. Реализационный MEDIUM остается открыт до своего RED→GREEN. Дедупликация по all-state title/body не нашла владельцев новых задач; T069#7613/T070#7614 созданы по canon, ensure/validate PASS. Независимый reviewer-owned refresh — `review-five-agent-requirements.md`:129checked/0unchecked, включая121reviewer-owned и8built-in. Отчёт перечитан; scoped analyze и canon sync подтверждены до допуска product edits.

## Исправление и повторная проверка

Предварительный расчёт: исполнитель расширил прежний no-contact contract на decrease10→5/increase10→15, сохранив запрет купона без контакта, POST/CSRF, выбранный объём и отсутствие денежных согласий. До шаблона2ожидаемых RED только на подписи; после единственной замены «Проверить изменение» полные clarity/purchase_ui/billing_ui133PASS/0SKIP, Ruff/whitespacePASS. Маршруты и обработчики не менялись.

Доступность: независимый injected-CSS опыт48GREEN установил две совместные причины. Только скрытие sidebar сохраняло растянутый min-content track; только minmax оставляло implicit column от sidebar. Кандидат ограничивает именно NoJS/nonembedded/mobile grid и сохраняет скрытие sidebar с достаточной специфичностью. Уточнённый baseline с измерением каждой строки пояснения выявил24геометрических assertion в16комбинациях:8кнопки при200% и16пояснения при100/200%; исходная оценка8касалась только кнопки. Кандидат устраняет обе причины. Нового overflow/clipping не добавлено. В существующий browser harness добавлены24keyboard/native-submit сочетания на движок; полный RED→GREEN и независимый final review завершены, как показано ниже. T069 выполнена; T070 остается открытой до своих exact-SHA/merge/release ворот.


### Фактический RED→GREEN исправленного кода

Один и тот же новый assertion полной оболочки выполнен до CSS-правки и после нее. До исправления полный accessibility-файл в каждом движке дал **1 failed,19 passed**, строго `focused cancellation fits viewport` для320/light/200%/NoJS: Chromium left−39.625/right359.359375; WebKit left−29.625/right350.484375. Журналы исполнителя: `.dev/agent-acceptance-20261016/05-accessibility/05-t069-red.log` и `05-t069-red-webkit.log`. После двух CSS-правил:

| Проверка исправленных байтов | Результат | Локальный журнал |
|---|---|---|
| Accessibility полный Chromium |20PASS,0FAIL/0SKIP,66.29s|`05-accessibility/05-t069-green-chromium.log`|
| Accessibility полный WebKit |20PASS,0FAIL/0SKIP,79.88s|`05-accessibility/05-t069-green-webkit.log`|
| Новая встроенная full-shell keyboard/native-submit матрица |24сочетания на движок,48всего, всеPASS; входит в20+20 выше|оба browser-журнала|
| Дополнительный48-combo скрипт на настоящем CSS без injection |48 выполнено,failures:[],exit0; пересекается с новой встроенной матрицей|`05-accessibility/05-t069-product-48.log`|
| Соседние shell/static/settings contracts |110PASS,0FAIL/0SKIP,3.80s|`05-accessibility/05-t069-shell-contracts.log`|
| Clarity/purchase_ui/billing_ui полностью |133PASS,0FAIL/0SKIP,0.44s|`05-accessibility/05-t069-adjacent-contracts.log`|

Для этих относительных журналов префикс `.dev/agent-acceptance-20261016/`. Числа наборов и повторов **не суммируются** в количество уникальных тестов. Исправление — только ограничение NoJS mobile grid через `minmax(0,1fr)` и специфичное скрытие sidebar; новые overflow hiding, JS, dependencies и изменения платежных обработчиков отсутствуют. Пять текущих файлов совпали с независимыми контрольными суммами final reviewer; `review-five-agent-final.md` содержит полную таблицу.

Независимый final reviewer самостоятельно повторил **133contractPASS**, **20ChromiumPASS**, **20WebKitPASS**, отдельный checker **24+24сочетанийPASS**. Он воспроизвел старый CSS через `git show HEAD:<CSS>` в изолированной synthetic route: оба движка дали ожидаемый RED на геометрии кнопки. Отдельно старый literal подписи дал2ожидаемых RED, текущий —2GREEN. Его SOURCE REVIEW PASS: critical0/high0/исправимых medium0. Это обзор проверенных незакоммиченных байтов на базе `6de02bc59d20bbab1cfa0487e942963509aa9d15`, не новый CI/production PASS. Предреализационный reviewer-owned checklist сохранен как результат независимого рецензента, автор сопровождения его не менял.

Точные команды исполнителя из корня (тот же установленный `.venv`, без установки/БД):

```sh
apps/server/.venv/bin/python -m pytest apps/server/tests/contract/test_billing_accessibility.py -q --tb=short --show-capture=no
GRAF_BROWSER=webkit apps/server/.venv/bin/python -m pytest apps/server/tests/contract/test_billing_accessibility.py -q --tb=short --show-capture=no
apps/server/.venv/bin/python -m pytest apps/server/tests/contract/test_billing_clarity.py apps/server/tests/contract/test_billing_purchase_ui.py apps/server/tests/contract/test_billing_ui.py -q --tb=short --show-capture=no
apps/server/.venv/bin/python -m pytest apps/server/tests/contract/test_cabinet_frontend_foundation_contract.py apps/server/tests/contract/test_graf_ux_ui_contract.py apps/server/tests/contract/test_settings_ui_contract.py apps/server/tests/contract/test_cabinet_static_assets_contract.py -q --tb=short --show-capture=no
node .dev/agent-acceptance-20261016/05-accessibility/05-reflow-investigation.cjs
```

Convergence этого узкого исправления: FR-008/010/012/045/SC-017 и нейтральная подпись FR-006/007/US2 подтверждены текущими source/browser/contract evidence; новых применимых обязательных product gaps не выявлено. T069 отмечена выполненной после независимого final review; T070 остается открытой. CSS zoom2 не заменяет все варианты системного увеличения/весь WCAG, перехваченный browser POST не доказывает сохранение в БД. Прежние595 DB checks относятся к первоначальному неизменному денежному исходнику и не выдаются за повтор после CSS/copy исправления.

## Выпуск и отдельная приёмка

Исправление ещё не выпущено. Для него требуются новый PR/exactSHA/base gates, ordinary merge, новый frozen authoritative Full и согласованный одним оператором CD dry-run/execute, tag/Release/русские notes и current source/runtime/live evidence. Предыдущий v2026.10.16.1 не доказывает новые байты. T011/T012/SC005/006/F278 сохраняют собственные открытые критерии. Агентная проверка не подменяет понимание людей, установленный GRAF Dev, настоящую доставку писем, банк/возвраты/будущее продление или рост конверсии.


## Объединение с PR #7612 — новая база, 2026-10-16

До создания коммита получен текущий `origin/master` `2340d6d2ff4ca2a7f8fb9bde7ae77f20b22ed57b` (соседний storage/mail срез T066–T068). Прежний dirty diff безопасно сохранен в Git stash, ветка передвинута на эту базу, затем обе реализации объединены без удаления соседних изменений. Конфликты storage template разрешены сохранением `data-billing-primary` из #7612 и новой нейтральной подписи; clarity test сохраняет параметризацию increase/decrease и добавленный соседним срезом `addon_label`. CSS/browser изменения вошли автоматически. В spec/plan/quickstart/tasks сохранены оба дополнения; combined F280 fragment сохраняет storage/mail результаты и добавляет reflow. Соседний release-prep PR #7615 не менялся.

Все предыдущие контрольные суммы/20+20/133 и independent final review выше относятся к версии до этой интеграции и остаются историей. На объединенных байтах заново выполнены три полных billing contract-файла: **144PASS/0FAIL/0SKIP,0.52s**, `.dev/combined-contracts-20261016.log`, существующий `.venv`, `PYTHONDONTWRITEBYTECODE=1`, `-p no:cacheprovider`; команда и остальные аргументы те же, что выше. Число изменилось из-за новых storage cases, это не пересуммирование старых результатов. Combined requirements refresh завершен:136checked/0unchecked по11файлам (128reviewer-owned+8built-in), ux23/0; storage-simplicity checklist совпадает с HEAD2340d6d. Дублировавшийся после объединения заголовок исправлен только у нашего раздела на Phase30, без измененияtaskID. Combined final review завершен: критических/высоких/исправимых средних замечаний0/0/0; contracts+renewal252PASS/0FAIL/0SKIP, Chromium20PASS62.22s, WebKit20PASS79.72s; встроенные24сочетания на движок входят в эти browser-наборы. Девять текущих source/test hashes повторно совпали9/9. Отдельные144 billing contracts входят в пересекающийся252набор и не складываются с ним. Текущие process/governance/fragment/Node/Ruff/whitespace проверки PASS; новые exact-SHA GitHub PR checks еще требуются. Это достаточное локальное основание для ранее разрешенного коммита/PR, не выпуска. Реальных денежных операций/писем/production изменений нет.


Сценарий отдельной проверки с пятью людьми подготовлен в `usability-session-script.md`; это инструкция и пустая форма наблюдения, не результат прохождения. T069 остается[X], T070[ ]. Полные команды252/browser и hashes текущей объединенной версии приведены в `review-five-agent-final.md`; исходные свидетельства RED остаются историческими causal evidence, а GREEN выше привязан к текущим объединенным байтам.


### Обновление базы после release-prep #7615

Перед проверкой PR #7616 в master вошел release-prep `278911f31c6ac0edcb478bcc03ad7808b6a15d2c`. Своя ветка rebased на эту базу. Git автоматически перенес изменение прежнего unreleased в архив; это исправлено до отправки: `changes/releases/v2026.10.16.2/F280.yaml` сохранен побайтово как в новом master, отдельный `changes/unreleased/F280.yaml` содержит только T069/T070. Архив/CHANGELOG/версия выпуска не изменяются этим PR. Ранее описанный combined fragment остается историей до этого архивирования.

`git diff --quiet df72fbc03cfcae4520c570282d3dbd73dd3b1c7b HEAD -- apps/server` вернул0: продукт и тесты после обновления базы побайтово прежние;9/9combined hashes совпали. Нового широкого прогона из-за исключительно release metadata базы не выполнялось. Результаты252/20/20 и136/0 применимы к тем же проверенным байтам. Прежние SHA/PR gates не переиспользуются: metadata/body и GitHub checks привязываются к новому коммиту.


### Совместимость порядка CSS со старой shell-проверкой

GitHub governance run38841058770 на `ff78cea11b4ffc4af96e6b9c8b91ee9cd2be1309` дал2295PASS/1FAIL: `test_web_shell_keeps_sidebar_pinned_without_scrollbar` ожидает буквальное начало NoJS rule со свойством grid-template-rows. В этом же rule переставлены только две независимые декларации: rows вновь идет первой, columns второй. Их значения/selector/порядок остальных правил не изменены; сравнение всего CSS до/после этой единственной перестановки PASS. При получении задачи перестановка уже была в рабочем дереве; сохранена без дополнительных продуктовых изменений. Существующий тест не изменялся и не ослаблялся.

Полный текущий `apps/server/tests/unit/test_cabinet_web_shell.py` повторен существующим `.venv`:96PASS/0FAIL/0SKIP,0.43s, журнал `.dev/shell-order-correction-20261016.log`; `PYTHONDONTWRITEBYTECODE=1`, `-p no:cacheprovider -q --tb=short --show-capture=no`. Повтор широких браузерных наборов не выполнялся из-за тождественного поведения CSS. Прежний fingerprint CSS относится к прежнему порядку деклараций, новый SHA/CI нужен после этой поправки; source review всех остальных файлов и причинный browser RED→GREEN сохраняют применимость.
