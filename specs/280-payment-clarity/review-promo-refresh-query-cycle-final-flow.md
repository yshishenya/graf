# Независимая сверка F280: период из GET ссылки

**Ограниченный PASS по текущим исходникам/flow и сверке реализации; новых runtime findings0.** Риск `high-risk-product`. Проверка по code-reviewer; чтением сверены текущие spec/plan/tasks/analyze, FR017/018/SC007, новый GETresponse branch, связанный helper/callers, новые регрессии и состояние лога. Тесты, БД, других агентов не запускал, репозиторий/внешние системы не менял. Записан только этот собственный отчёт.

Новая ветвь действительно ограничена GET, действующим savedB, допустимым query month/year и отличием checkout_cycle от savedBcycle. Обычный/same/invalid query не переписывает draft; POSTrenderer старой формы новую ветвь не выполняет. Clear при blocking operation или непригодном draft стоит первым и имеет приоритет. Просроченный/подделанный/чужой draft не может войти в updateветвь.

Повторно использован существующий helper с replace=False и выбранным cycle. Helper повторно проверяет подпись/срок/связь, берёт только проверенный codeB и исходный expiry, SetCookie MaxAge равен оставшемуся сроку; новой300с пятиминутки нет. Если срок истечёт между первоначальным чтением и helper, он не возродит выбор. Из helper переносятся только все SetCookie headers, не Location, статус или тело. HTMLResponse остаётся200, цена соответствует выбранному периоду, не добавляются redirect/экран/финансовые calls. Старый legacycookie удаляется прежним helper. Защитные атрибуты и узкий путь сохранены.

Старые POST303ошибки сохраняют весьB; оба direct409 предпочитают savedBcycle и codeB, безB допускают только Formperiod. Explicit preview/Apply/clear и unavailable поправки сохранены. Новых значений суммы/quote/согласий в draft не появляется, денежная полномочность и guards прежние. Открытие страницы уже пересчитывало quote, новая ветвь не добавляет такой вызов. Старая фраза «только preview» согласована с явнымGET в spec/plan. Редакционная неточность остаётся в plan строке79: «GET не перевыпускает состояние» следует уточнить как «обычный GET не переписывает, явный допустимый GET меняет только cycle без продления срока»; новый scopedраздел однозначно задаёт действующую семантику, runtimeдефектом это не считается.

Матрица6 проверяет month→year/year→month × offer_changed/quote_changed/offer_required, новую цену/продление, remaining258, два reloadбезquery без SetCookie renewal, оба409 и303 со свежим сохранённым периодом, пустые согласия и отсутствие кодаt300. Обычный/same/invalidquery подтверждены условиями ветви; отдельного нового invalidquery+draft HTTPсценария эта матрица не содержит, поэтому не заявляется. Предыдущий HTTPнабор покрывает expiry/подпись/binding и ordinaryGET; nofinancial autouse и запрещающийprovider fixture сохранены. Условия требований9/0 прочитаны, отметки не менялись.

По sourceconvergence FR017/018/SC007 новых missing/partial/contradicts/unrequested задач реализации0. Текущий внешне выполненный набор завершён; остальные независимые обзоры сверяются основным агентом отдельно. T019/exactSHAchecks/releasefull/CD/runtime и внешниеT011/T012/F278 не дублируются и этим отчётом не закрываются. Реальные деньги, человеческая/macOSприёмка и конверсия не доказаны.

Baseline `/tmp/graf-f280-query-cycle-baseline.log`:6FAIL8,20с до поправки, контейнер удалён. Новый `/tmp/graf-f280-query-cycle-final.log` завершён и прочитан после завершения: **313 passed,2 warnings,179,05с**, phasefocusedpass184с, `postgres_test_result=pass`, изолированный контейнер удалён. Collection313 digest `720de8802a42176d192386a88c6b0ddc165fc3c61c40ad26670bf7686538aae2`. Самостоятельно тесты не запускал; лог не содержит proof неизменности файлов во время выполнения, текущие SHA проверены отдельно. Нового текущего DOM evidence в этом scopedобзоре нет. Прежние307/DOM относятся к истории, не считаются runtimefec78 выполнением и не прибавляются.

SHA256 текущих файлов:

```text
billing.py
fec78d91a5ef03f667ddf34524afd6aaa787d1d6f1189bd3bfeb952d847a80c3
test_billing_promo_refresh.py
7ad40a80c8d2a374b38cad1c73f6a26069265bcff112d2adc0874385714b5f96
```
