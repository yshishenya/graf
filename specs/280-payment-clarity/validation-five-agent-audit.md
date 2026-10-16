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


### PR #7616 — административная регрессия общего CSS, 2026-10-16

Независимое Codex review `discussion_r4290295731` / `PRRT_kwDOSpM8OM6tCmgN` выявило пропуск прежней приемки: новое общее sidebar-hide правило совпадает с `.app-shell.admin-app-shell` на ширине до980px. В admin/base.html нет cabinet.js/data-cabinet-js ready; admin.css mobile `.admin-sidebar { display:flex; }` проигрывает более специфичному новому selector. Прежние browser20/20 и source review подтверждали кабинет, но не административную навигацию; они не доказывают отсутствие этой регрессии. T069 вновь открыта до нового исправления и независимого обзора, T070 остается открытой.

Прослежены все производственные потребители cabinet.css: cabinet/base.html, admin/base.html и отдельная форма api/summary_autosend.py. Только cabinet/components/sections.html создает cabinet `.app-shell` с существующим `data-cabinet-shell`; admin/base.html создает `.app-shell.admin-app-shell[data-admin-shell]`. Форма summary_autosend не создает app-shell. JS обращается к положительному data-cabinet-shell; иных конструкторов app-shell в server source не найдено. Изменен только новый hide selector: добавлен `[data-cabinet-shell]` на самом `.app-shell`. Другие стили, admin CSS/templates/permissions, денежные обработчики и согласия не менялись.

До кода уточнения spec/plan/quickstart/tasks сопоставлены с FR008/012/SC017→T069/#7613. Scoped analyze: critical0/high0/medium0, новых вопросов/данных/полномочий нет. Project prerequisite не поддерживает `--require-spec`; использован штатный `--json --require-tasks --include-tasks`, наличие spec/plan/tasks проверено отдельно. Enabled clarify/analyze/implement/converge hooks отсутствуют. Независимый reviewer требований agent2 подтвердил137checked/0unchecked по11checklists, ux24/0; CHK024 и отчет `review-admin-navigation-requirements.md` принадлежат reviewer, исполнитель их не отмечал. Существующий T069 issue #7613 открыт и сохраняет feature/priority/area/gate/type canon; новая задача/issue не создавалась.

Причинный probe на реальном штатно отрендеренном admin/base.html, admin_navigation и cabinet.css/admin.css: до fix Chromium/WebKit на320/360/980 sidebar=false, доступных ссылок0; на1280 sidebar=true,7ссылок. Оба probe exit1. После одной правки selector те же probe на всех четырех ширинах sidebar=true,7ссылок, exit0. Журналы `.dev/admin-selector-{red,green}-{chromium,webkit}.log`.

В существующий `test_billing_accessibility.py` передан отдельный admin HTML, созданный штатными admin render/navigation helpers; billing pages и их assertions сохранены. Existing CJS suite добавляет16сочетаний на движок:4ширины×2темы×JSon/off. Проверяются загрузка обоих реальных CSS, отсутствие искусственных cabinet marker/ready/cabinet.js, sidebar и все7links, Tab/Option-Tab к каждой ссылке, outline/viewport/hit-test, Enter→/admin/users и сохранение shell. Маршрутизируются синтетические GET на тот же base; это доказательство browser-навигации/геометрии, не HTTP/auth/backend разрешений. Прежние24 cancellation-сочетания на движок и остальной browser suite сохранены.

Именно новый постоянный browser regression test ДО product fix завершился RED в обоих движках: `admin: 320px, light, JS=false: admin sidebar visible`, по1FAIL/19deselected (Chromium0.87s,WebKit1.10s), журналы `.dev/admin-regression-red-{chromium,webkit}.log`. Затем ограничен selector; тесты и матрица не упрощались ради GREEN.

Полные текущие shell/admin view-model unit + billing clarity/purchase_ui/ui + billing usability/copy-convention: **338PASS/0FAIL/0SKIP1.03s**, `.dev/admin-regression-contracts-unit.log`. Команда: `PYTHONDONTWRITEBYTECODE=1 apps/server/.venv/bin/python -m pytest -p no:cacheprovider apps/server/tests/unit/test_cabinet_web_shell.py apps/server/tests/unit/test_admin_overview_view_models.py apps/server/tests/unit/test_admin_audit_view_models.py apps/server/tests/contract/test_billing_clarity.py apps/server/tests/contract/test_billing_purchase_ui.py apps/server/tests/contract/test_billing_ui.py apps/server/tests/integration/test_billing_usability.py apps/server/tests/contract/test_copy_convention_contract.py -q --tb=short --show-capture=no`. Process/governance/fragment/Node/Ruff/whitespace PASS.

Текущие SHA-256: cabinet.css `c93c799c35ef57aac56bc032c9c00655d85ce0f59fc9521d68742195ff46094c`; browser CJS `1a4301f54a13aa45150ba910229d6c0c528fbc88a0910ac6f00963c0cbf08183`; accessibility Python `e027b49d7a6a81a8937baaad5edba54495fd20b2d1feb5761cb0a5cd5f491989`. Соседний #7617 сохранен. Технический выпуск v2026.10.16.2 наfb78 уже опубликован другим оператором и не содержит это исправление; его candidate/decision/CD/публикация не менялись. Для исправленного PR требуются новые exact-SHA/base GitHub gates; прежний c6dca PASS их не заменяет. Новый выпуск относится к T070; SC005/006/F278/GRAF Dev отдельно.

Полный текущий `test_billing_accessibility.py` после selector fix: **Chromium20PASS/0FAIL/0SKIP64.52s**, **WebKit20PASS/0FAIL/0SKIP84.28s**; `.dev/admin-regression-green-chromium.log` / `.dev/admin-regression-green-webkit.log`. Команда каждого: `GRAF_BROWSER=<chromium|webkit> PYTHONDONTWRITEBYTECODE=1 apps/server/.venv/bin/python -m pytest -p no:cacheprovider apps/server/tests/contract/test_billing_accessibility.py -q --tb=short --show-capture=no`. Новые16admin+прежние24cancellation сочетания на движок встроены в один browser pytest и не суммируются с20 как отдельные pytest cases.

Scoped convergence после GREEN сопоставил текущее исправление со spec/plan/quickstart и уточненным T069: обязательного нового buildable gap не найдено, дополнительные задачи не добавлены. T069 ожидает независимого итогового source/browser заключения; T070 сохраняет отдельные PR/merge/release/live ворота. Прежняя человеческая и финансовая приемка не закрывается этим результатом. Контрольные суммы пяти документов требований перед final review совпали со снимком `review-admin-navigation-requirements.md` (5/5).

Независимый итоговый `review-admin-navigation-final.md`: SOURCE/BROWSER REVIEW PASS, critical0/high0/исправимых medium0. Reviewer подтвердил единственную product selector replacement и побайтовую сохранность прежнего CJS после удаления только нового admin сценария/констант/вызова. Самостоятельные повторы:338PASS1.52s, Chromium20PASS64.87s, WebKit20PASS84.77s,0FAIL/0SKIP; hashes3/3 до/после совпали. Дополнительный независимый root source/browser обзор также PASS на тех же байтах,20/20; повторы не суммируются. T069 вновь[X] как реализация, T070[ ]; issues не закрыты, discussion пока не решено. Последующее изменение tasks — только статус и это подтверждение; пять hashes requirements report остаются историческим снимком перед final acceptance, product/test hashes выше актуальны. Новый коммит/PR description и точные GitHub gates следуют отдельно.
