# Независимый обзор исходников, безопасности и понятности хранения

Дата: 2026-10-16. Область: F280 FR-056–058, две существующие billing страницы, общий selector JS, scoped CSS и три связанных проверочных файла. Reviewer изменил только этот отчёт; code/spec/tasks/checklist/Git/GitHub/production не менялись. Применение operator recovery и его послеоперационная сверка вне этого UI обзора.

**SOURCE/UX REVIEW PASS: применимых незакрытых critical0/high0/medium0.** Допуск касается прочитанных исходников и перечисленной независимой проверки; окончательный текущий browser GREEN, PR/release/runtime и человеческая приёмка остаются отдельными воротами.

## Найдено и исправлено до допуска

1. MEDIUM: безусловное «5ГБ включены в тариф» на free/trial давало ложное впечатление о действующем объёме. Исполнитель заменил на «В тариф „Личный“ включено5ГБ», сохранив настоящую capacity бесплатного пользователя. Добавлен отдельный регрессионный сценарий. Reviewer перечитал actual bytes и получил GREEN.
2. Уточнение понятности80/95%: после удаления normal status строка предупреждения объясняла лишь возможные действия. Теперь явно «Место заканчивается». Сохранены full действия и exhausted запрет обработки без аудио. `over_capacity` в label helper существует исторически, но текущий producer возвращает full приratio>=1; первоначальное предположение о новом runtime blocker от over_capacity отозвано после чтения producer. Исполнитель также сохранил совместимый текст превышения в общей полной ветке без изменения модели. Регрессионные проверки80/95/over_capacity проходят.

## Проверенная причинная цепочка и границы

- `billing_storage_page` формирует существующие approved catalog `addon_label`, `total_label`, `cycle_label`; новые шаблоны используют их раздельно. Select показывает общий объём плюс каталожную цену только места за месяц/год. Полная будущая сумма подписана «Вместе с тарифом» в одном раскрытии. Перед продолжением явно сказано, что точная доплата за оставшийся срок появится на следующем шаге без списания. Form/method/action/package_count/promo/CSRF остаются существующими; сумма не вычисляется в JS. Серверное purchase preview, все интервалы/proration и финансовое подтверждение не переписаны.
- История prepaid/bonus закрыта native details, но ближайший будущий объём и его отмена видны вне раскрытия. Cancel-selection форма теперь доступна при disabled checkout, что соответствует FR-058. Проверен существующий route: WebCSRF, principal/tenant, workspace lock, owner subscription, pending blocker и selection_version не зависят от checkout flag; изменяется отложенный выбор, не сумма/оплаченный срок. Из view передаётся настоящее subscription.next_capacity_version.
- Usage показывает owner used/capacity и native progress с доступным именем/aria-valuetext. Private used/reserved/processing totals и progress отсутствуют для member. Unavailable не выдаёт количественные данные/шкалу; stale явно помечен. Reserves остаются на виду при ненуле; свободное место с учётом резервов доступно в подробностях. Free processing ограничения и full/exhausted recovery сохранены.
- JS меняет только текстовое представление и индекс existing select, раскрывает плюс/минус после инициализации; используется textContent, каталог не становится денежным authority. Native select/details/form работают без JS; hidden JS-only controls не мешают. Ограничения края0/99 и пропуск недоступного каталожного варианта сохранены существующим индексным выбором.
- Все новые строки шаблона по-прежнему autoescaped; новые URL константны. No new third-party assets, packages, tracking, migrations, API или денежные обработчики. CSS ограничен классом страницы; native progress/details/select и прежние дизайн-токены соответствуют независимой реализации GRAF.

## Самостоятельная проверка

Команда из apps/server: `.venv/bin/python -m pytest tests/contract/test_billing_clarity.py -k 'storage' -q` → **17passed,15deselected**. Проверены addon/full distinction, receipt-missing choice, disabled cancellation visibility, timeline disclosure/future selection, owner/member×fresh/stale/unavailable, явные warning states и точное название платного плана. Два предупреждения библиотек существующие; продуктовые проверки прошли. Это локальная проверка представления, не PostgreSQL или настоящий провайдер.

Визуально прочитаны8 WebKit synthetic изображений: usage-fresh и packages-timeline-year ×1280/320 ×light/dark из `/tmp/graf-storage-simplicity-webkit/`. Главное действие различимо; used/capacity выше справки/расхода; на320 selector и шаги расположены последовательно, длинные даты переносятся, перекрытия/горизонтальной прокрутки на снимках нет. Видимый фокус summary читается в обеих темах, price/proration не смешаны. На storage снимках раскрытие открыто для проверки timeline/bonus; исходник закрывает его по умолчанию. Снимки предшествуют последним малым copy/disabled-cancel изменениям: финальный browser повтор на новых bytes требуется отдельно, старые пиксели не выданы за окончательную проверку. Полный keyboard/no-JS/contrast/200% проверяет существующий browser runner с добавленными assertions; его сообщение44PASS и PostgreSQL21PASS переданы основным агентом, reviewer не выдаёт их за собственный повтор на окончательных байтах.

## Отпечатки прочитанных файлов

| Файл | SHA-256 |
| --- | --- |
| `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_usage_content.html` | `61cb3de90a5d2f21f62d73e7c3dadbb644ad0753f6cf3de04a74fe4b401f3639` |
| `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_storage_content.html` | `ce8a651bcbd36180e05a37d07aa495238c7b8b48efbec2ee0f1a25bccfaefce7` |
| `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css` | `43f7db52ac1418adeba6ffc1760df34d57cc5ea238be1d3cdb90bb0e1f8d88df` |
| `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js` | `904e12c4aa8f9777eaff9724ed70f31919e56b4801a0ba366910ee13fb6e6407` |
| `apps/server/tests/contract/test_billing_clarity.py` | `539ac76d0088d2db5a14cba30668385f275cb2a6bf4ab9992994a2c44d2b1291` |
| `apps/server/tests/contract/test_billing_accessibility.py` | `ebda8b41261e04856470be2881e32f8ab1c9a724cb8a6f017af52b44d6a4fb59` |
| `apps/server/tests/browser/billing-accessibility.test.cjs` | `fc03093b8c66290fcdc91c9283087a7c11cad4ad6d22e146d94cd18dea08e951` |

Требования/источники: актуальные spec/plan/quickstart/analyze и reference-subscription-krisp прочитаны в рамках независимого requirements обзора, затем сопоставлены с current UI diff. Никаких гарантий роста конверсии, доставки нового письма, банковской выплаты, будущего автопродления или выпущенного интерфейса этот source PASS не даёт.

## Окончательный refresh текущей проверки, 2026-10-16

**CURRENT SOURCE/VISUAL/VALIDATION REVIEW PASS — critical0/high0/medium0.** Все семь исходных file hashes из предыдущего раздела повторно вычислены: соответствуют ровно прежним проверенным байтам, UI после source обзора не менялся. Дополнительно прочитан diff `test_billing_ui.py`: два старых теста адаптированы к новым буквальным подписям и отсутствию normalstatus, при этом добавлены прямые проверки href `/meetings` и `/meetings?archive_audio=false#manual-upload`; остальные финансовые/роль/данные assertions не удалены.

Теперь непосредственно прочитаны конечные логи Chromium48passed/WebKit48passed, PostgreSQL storage21passed, wider109passed и focused contract32passed. Browser: Chromium68.27с/WebKit78.50с; PostgreSQL storage16.29с, изолированный контейнер штатно удалён. Wider109 имеет PostgreSQL harness result PASS/cleanup. Исторические RED5failed/3passed и промежуточный неуспех1failed/27passed сохранены в своих журналах; они не выданы за текущий GREEN. Reviewer не повторял эти полные команды сам, а прочитал их actual output и сопоставил неизменность исходников. Собственный17PASS из предыдущего раздела остаётся отдельным прямым повтором.

Финальные synthetic снимки `.dev/storage-simplicity/{usage,storage}-{1280,320}.png` просмотрены непосредственно. Закрытые default details подтверждены: period history, промокод и справка не занимают основной экран; будущий объём/отмена видны сразу, основной шаг заметен, значение общего объёма и цена дополнения читаются на320. Исправленный subtitle точно называет тариф «Личный». На четырёх снимках нет перекрытия или общей горизонтальной прокрутки; storage footer на320 корректно переносится. Это окончательные synthetic изображения текущего UI, не authenticated production. Предыдущая оговорка об отсутствии browser повторения после minorfix заменена текущим прочитанным GREEN; старые изображения сохраняют историческую границу.

Прочитан `validation-storage-simplicity.md`: готовность рабочей копии, выполненное восстановление доступа и текущие тесты отделены от ещё не выполненных implementation commit/PR/exact-SHA CI/frozen Full/CD/runtime UI. Новая доставка письма и метрики удержания/конверсии остаются не подтверждены. Выпускные ворота и T011/T012/umbrella этим обзором не закрываются.

| Прочитанный дополнительный артефакт | SHA-256 |
| --- | --- |
| `.dev/storage-browser-chromium.log` | `b59e4650c90869ff18c4b753969a8b95a71794ecf9f8c6c88c77445bd2c770d4` |
| `.dev/storage-browser-webkit.log` | `2c276f185059d94ab7f37b217908d2e141e09bd64a7e4982d583070e40ab1160` |
| `.dev/storage-postgres.log` | `d3603dd03b03e6746096c0ed45ca2dcd26058192f7fa2e8d905c1c102e1a3aff` |
| `.dev/storage-ui-regression.log` | `58497d6bd5b5b00db67e9c60ed1934d5b8ee0e11a69ed0b252408937a1d3bb26` |
| `.dev/storage-contract.log` | `931d05c770d57f99fce343215b2c279456d95886642b91530db375b8780f2fee` |
| `apps/server/tests/contract/test_billing_ui.py` | `877b311fa799b79a1ccfeb9a229be29443ce2e8021c1e8ab9481ec6d6dc19543` |
| `specs/280-payment-clarity/validation-storage-simplicity.md` | `471405b6caf2a6bd75758345a7bef18b1758479c37283ac7e26a790510f17185` |

| Финальный synthetic снимок | SHA-256 |
| --- | --- |
| `usage-1280.png` | `ba43f20deaab5b6fb6c3474da11ee8ec5db80af789d8754bacbbcbb41ad8c4e0` |
| `usage-320.png` | `087491e3427eb672676d0966e9162e59132462126c0e60e675a0b8ba518b7c69` |
| `storage-1280.png` | `c88f18fe316274f98e7d47f3acea648da84a8aa57bb836393a6e29e69f42ef7a` |
| `storage-320.png` | `02635c33752f0ff2c79d89ff2094e58db1c9504a6c82f2dc257b0a6b1e6866a2` |

Reviewer изменил только этот отчёт и свой requirements отчёт. Implementation/canonical/checklist/GitHub/БД не менялись reviewer.


## FR-059 / T067: текущий адрес нового чека автопродления, 2026-10-16

**FINAL BACKEND SOURCE REVIEW PASS — critical 0 / high 0 / medium 0.** Рассмотрены окончательные байты после сортировки импортов. Это отдельный допуск изменения выбора контакта нового чека; прежний UI review сохраняется на прежних байтах. Применён локальный процесс `code-reviewer`; никаких изменений реализации reviewer не делал.

Причина подтверждена непосредственно diff и исходником: до исправления planner выбирал только snapshot последнего успешного счёта, поэтому смена проверенного контакта владельца не влияла на будущую новую операцию продления. Теперь `plan_due_renewals` сначала вызывает `verified_receipt_contact(db, subscription.billing_owner_id)` и только при отсутствии результата выполняет прежний запрос исторического успешного счёта этого workspace. Прежняя проверка типа/непустой строки и resolution `receipt_contact_required` сохранена; trim выполняется при создании нового snapshot.

Независимое сравнение синтаксических деревьев старого `_verified_receipt_contact` из HEAD и нового helper (нормализовано только имя функции) дало exact match. Сохранены db=None, user_id, active, verified, email non-null, created_at ascending и limit1. Alias в `web_routes/billing.py` сохраняет все шесть существующих ручных callers; они по-прежнему передают principal.user_id. Отдельно прочитаны зависимости db models: обратной зависимости на receipts нет; запуск tests подтверждает импорт. Новый PostgreSQL тест через прежний alias реально исключает другой user, inactive и unverified; после выключения единственного подходящего identity возвращается None. Это проверка настоящего SQL, не эмуляция predicates.

Денежные границы сохранены: diff planner меняет только источник `receipt_contact`. Существующие owner/workspace/active membership, recurring_allowed, accepted catalog/storage price, verified default method, locks, окна попыток, authority version, ключи повторяемости и лимит приёмки не изменены. Новое значение записывается только в вновь создаваемый BillingInvoice. Существующая операция переиспользуется без переписывания контакта её счёта; старые успешные/начатые счета не обновляются. Отправка по-прежнему строит provider receipt из `invoice.receipt_contact_snapshot`, а не из повторно прочитанного текущего identity. Цена, платёжный метод, согласие, amount/currency, provider POST и dispatch marker не изменены.

Проверены causal RED и финальный GREEN: новый параметризованный planner scenario различает новый verified contact и прежний fallback при None; старый сценарий сохраняет catalog assertions. Непосредственно прочитаны журналы renewal **108 passed**, receipt lifecycle **8 passed**, изолированная PostgreSQL выборка/manual/renewal regression **192 passed** (52.84с), штатное удаление контейнера подтверждено. После последней сортировки импортов reviewer самостоятельно повторил `.venv/bin/python -m pytest tests/unit/test_renewal_charge.py -q` из apps/server: **108 passed** (0.81с), только два существующих предупреждения библиотек. Полный PostgreSQL запуск reviewer повторно не выполнял: прочитал завершённый журнал и его cleanup.

Новых списаний или включения автопродления этот обзор не выполняет и не подтверждает. Доставка будущего письма, production runtime новой версии, exact-SHA CI/PR/Full/CD и retention/conversion остаются отдельными воротами. Нет требований менять исторические счета или запускать финансовую проверку для этого исправления. Reviewer обновил только этот source report; checklist, canonical документы, код, Git/GitHub и production не менялись.

| Окончательный файл / журнал | SHA-256 |
| --- | --- |
| `apps/server/src/twobrain_rec_server/billing/receipts.py` | `71196cf85a24e0bb9d16181a75089fe8969d5acc51b2f4186173039a8f743d9c` |
| `apps/server/src/twobrain_rec_server/billing/renewal_charge.py` | `1e11a885bea77456d97deded3afeb4a9d3138c47801f38620967d2fed1c4de16` |
| `apps/server/src/twobrain_rec_server/cabinet/web_routes/billing.py` | `8cc136766d931b1ecccc1dcf5392696f0e37b320825c9be3538cef40886fe2cb` |
| `apps/server/tests/unit/test_renewal_charge.py` | `2c2233b09115e1f52adf565505532621acdb1d715f7e13f3e7f9fe2ff6d0cdfe` |
| `apps/server/tests/integration/test_billing_clarity.py` | `910a7d47961b1b4a06a425ea4444d5f13a2d0e954c24dd17497f949b2259a968` |
| `.dev/storage-receipt-contact-red.log` | `19fe23aa1101d4c8b02c3b2dfd8f47897942211e196cc54dfbdee9fcb401d263` |
| `.dev/storage-renewal-unit.log` | `05abe385e03ef400c3ed9fc609d8cba390ecd2849ca51a3109d1b6565fef4abb` |
| `.dev/storage-receipt-unit.log` | `b75d6dfd4b59424970df6215224cd584ac1d8db787833d04a27f56508d8c59bd` |
| `.dev/storage-contact-postgres.log` | `8e9c2e418ab3e067e332f9e95d6df7861bf94c46149d596484c46412e605160a` |

Дополнительная проверка контекста настоящего фонового обработчика: `workflows/worker.py::run_billing_renewal_reconciler` применяет `MaintenanceTenantContext(operation_name="billing_reconciliation")` перед planner. Эта операция входит в разрешённый список tenant context; существующая migration0076 включает `MAINTENANCE_SCOPE` с `rec_maintenance_allowed()` в SELECT policy external_identities. Поэтому новая выборка не требует расширения RLS (прав доступа на уровне строк); diff миграций отсутствует. Прочитан конечный `.dev/storage-lint.log`: `All checks passed!`. Девять значений `.dev/storage-simplicity/final-source-hashes.json` совпадают с независимо вычисленными выше backend/test hashes и ранее проверенными четырьмя UI файлами. Итоговый PASS не изменён.
