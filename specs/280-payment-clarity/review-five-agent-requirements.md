# F280: независимый допуск качества требований перед T069/T070

Дата: 2026-10-16. Reviewer: `/root/independent_2_volume`. HEAD: `6de02bc59d20bbab1cfa0487e942963509aa9d15`; canonical spec/plan/tasks/quickstart имеют текущие незакоммиченные дополнения Phase29. Это отдельная роль после первоначальной независимой проверки объёма; автором новых требований reviewer не является.

**REQUIREMENTS PASS.** Применимых critical/high/исправимых medium пробелов требований не обнаружено. Это допуск формулировок и покрытия до реализации, не результат исправления, браузерных тестов, analyze/canon sync, CI или выпуска. T069/T070 остаются открытыми до собственных доказательств.

Прочитаны AGENTS.md, guidance index/spec-kit-flow/product-gates/release-and-validation, конституция7.1.0, продуктовый baseline/current status для ограничений, актуальные spec/plan/tasks/quickstart, договор payment-journey, data-model, исследовательские разделы и все10 checklists/*.md. Чужие отдельные review/validation отчёты не использованы; исторические PASS в notes чеклистов не являются основанием. Исследовательские источники оценены как требования к обоснованию и границам, без нового утверждения о live доступности внешних URL.

## Что проверено в Phase29

- Пользовательская цель конкретна: кнопка отключения и пояснения остаются видимыми/достижимыми без JavaScript, а увеличение/уменьшение имеют нейтральный предварительный шаг. CSS решение не закреплено заранее; обход через clipping запрещён.
- Матрица согласована:8 исходных проблемных сочетаний =2 движка×2 ширины×2 темы при JS off/200%; расширение48 =2×3ширины×2темы×2масштаба×2режимаJS. Для широкого экрана и соседних страниц предусмотрена регрессия. Геометрия после фокуса/текст/native submit дополняют scrollWidth.
- CSS zoom2 прямо ограничен способом воспроизведения,не объявлен полной WCAG/системной приемкой. Synthetic native POST не выдаётся за DB сохранение.
- Новая подпись сохраняет route/method/цену/срок/receipt-contact и отдельное согласие покупки. required unchecked оферта и optional default checked recurring остаются во всех новых/ручных оформлениях;explicit choice по FR019/020 сохранён.
- T069 имеет causal RED→минимальная правка→GREEN и полный прежний browser matrix;T070 имеет независимый final source/browser,converge,changelog,exactSHA/base,normal merge,один новый frozen release/full/CD/live. Общий оператор,SC005/006,F278 и GRAF Dev отделены.

Новые CHK022/023 добавлены независимым reviewer в ux-payment и отмечены по перечисленным текущим требованиям. Прежние127 пунктов перепроверены по требованиям,не по историческим отметкам.

## Основание каждого пункта

Все пути ниже относительно `specs/280-payment-clarity/`; `FR`, `SC`, `Session` относятся к текущему `spec.md`, `Plan`, `Tasks`, `Quickstart`, `Contract`, `Data model` — к одноимённым canonical файлам. PASS в таблицах означает только достаточность требований.

### checklists/invoice-consistency.md

| Пункт и строка | Оценка | Конкретное основание |
|---|---|---|
| CHK001, строка11 | PASS | FR046: определены назначение, сумма, результат, срок, чек, вторичная история и один главный шаг. |
| CHK002, строка12 | PASS | FR046/052 и Plan «Платеж и чек»: общая геометрия согласуется с подпиской; чужие цены/активы и денежные изменения исключены. |
| CHK003, строка13 | PASS | FR047 прямо различает дату создания, исторические/будущие сроки покупки и текущий доступ. |
| CHK004, строка14 | PASS | FR047 и сценарий2 требуют viewer-local краткие/точные границы, nullable недостоверный срок и сохранение отдельных storage intervals. |
| CHK005, строка15 | PASS | FR048 допускает только действительную ненулевую скидку и сохраняет ограничения прежнего плательщика при доступности номера. |
| CHK006, строка16 | PASS | FR049 разделяет question/refund; письмо открывается без отправки и возврата, безопасный адрес/номер обязательны, недопустимый контакт имеет fallback. |
| CHK007, строка17 | PASS | FR050 плюс уточнение T059 задают AVAILABLE без URL, can_refresh_receipt/CSRF/receipt_only, отсутствие формы без разрешения и запрет денежных действий. |
| CHK008, строка18 | PASS | FR048/051 и FR031–038 сохраняют service_gap/ожидание/recovery вне раскрытий; оформление не определяет финансовую истину. |
| CHK009, строка19 | PASS | Уточнение2026-10-04 отвергает автоматический off нового checkout и сохраняет FR019/020, что повторено Session2026-10-16. |
| CHK010, строка20 | PASS | FR012/052 и acceptance6 задают темы,320/390/768/1280,200%,фокус и JS-off; Session2026-10-16 усиливает фактическую геометрию полной оболочки. |
| CHK011, строка21 | PASS | FR014/052, research S01–S12 и раздел invoice отделяют рекомендации от доказательства GRAF, запрещают чужие активы и приватные источники. |
| CHK012, строка22 | PASS | SC016 перечисляет7 сценариев/zero-money read; SC017 задаёт матрицу и независимые замечания, Tasks T052–T056 связывают выполнение. |
| CHK013, строка23 | PASS | SC017 и границы invoice разделяют synthetic/server/live/installed/F278/SC005/006; T070 сохраняет нового общего оператора выпуска. |
| CHK014, строка24 | PASS | Границы invoice и уточнения T059/T060 явно сужают совместимость до copy/support, не меняют новую историю, деньги, полномочия или флаги. |
| CHK015, строка28 | PASS | T060 явно задаёт общий безопасный parser/URI, все sibling callers, CRLF и выключенный checkout; отдельное уточнение сохраняет строгий account_merge display-name запрет. |
| CHK016, строка29 | PASS | T060 задаёт только внешний subprocess300с для77×5×2×2 с неизменными assertions,HTTP15с/окном60с/числом попыток и отдельным новым SHA proof. |

### checklists/optional-renewal.md

| Пункт и строка | Оценка | Конкретное основание |
|---|---|---|
| CHK001, строка5 | PASS | FR019 и Session2026-10-16 явно задают offer required/unchecked и recurring optional/checked во всех новых и ручных checkout. |
| CHK002, строка6 | PASS | FR019/SC008 допускают False для month/year/скидок, один оплаченный период и запрет сохранения новой карты/будущего списания. |
| CHK003, строка7 | PASS | FR020, Data model «Выбор продления» и Contract определяют вкладку/user/workspace/session, sessionStorage и best effort fallback без принятой оферты. |
| CHK004, строка8 | PASS | FR003/012/019 и Contract «Необязательное продление» сохраняют сумму/срок, условную базовую NoJS подпись и обратимый режим без обещания списания при False. |
| CHK005, строка9 | PASS | Data model «Выбор продления и финансовые снимки» задаёт строгий bool request/invoice, provider save_payment_method и отказ malformed snapshot. |
| CHK006, строка10 | PASS | SC008 и тот же Data model явно запрещают сохранение неожиданной карты при False, выдача периода остаётся независимой от recurring. |
| CHK007, строка11 | PASS | FR020 требует неизменный снимок операции, независимую новую вкладку и невосстановление отмены поздним/повторным результатом или сменой владельца. |
| CHK008, строка12 | PASS | FR011/019/020 и Contract сохраняют цену/оферту/CSRF/owner/tenant/receipt/paid remainder; preview не создаёт деньги. |
| CHK009, строка13 | PASS | T020–T022/Quickstart задают RED/GREEN и три обзора, exact-SHA PR/Full/CD/runtime отдельны; T070 вновь требует новый кандидат. |
| CHK010, строка14 | PASS | SC008/Assumptions и Quickstart «Закрытие» отделяют F278/людей/T011/T012 и не используют прошлый релиз как новое доказательство. |

### checklists/payment-return.md

| Пункт и строка | Оценка | Конкретное основание |
|---|---|---|
| CHK001, строка11 | PASS | FR031/035 разрешают «Оплачено» только при trusted success и применённом доступе, return/query не является доказательством. |
| CHK002, строка12 | PASS | FR031/032 и acceptance1–4 различают деньги без доступа, pending/canceled и сетевую ошибку без ложного результата. |
| CHK003, строка13 | PASS | FR032 задаёт «К встречам» для success, проверку для pending и вторичный guarded continue текущего платежа. |
| CHK004, строка14 | PASS | Уточнение return и FR035 не выводят новую оплату/recurring из возвращения; отдельное действие пользователя обязательно. |
| CHK005, строка18 | PASS | FR033/034 задают6 запросов,60с,интервал≥10с,timeout15с,один in-flight и запрет сброса лимита при reinit. |
| CHK006, строка19 | PASS | FR033 определяет terminal/error/auth/context/navigation/hidden остановки; повторная видимость не перезапускает sequence. |
| CHK007, строка20 | PASS | FR034 и Plan T035–T037 различают browser abort и серверный запрос, разрешают локальное чтение и исключают пересекающийся manual POST. |
| CHK008, строка21 | PASS | FR036 сохраняет защищённую ручную проверку без JS и восстановление при исчерпании/ошибках по server limits. |
| CHK009, строка22 | PASS | FR034 задаёт четыре границы meta/user/workspace/payment/session и отказ foreign/late/detached; контакт/код/цена не хранятся. |
| CHK010, строка26 | PASS | FR035 сохраняет read-only GET и owner/tenant/session/CSRF/rate30за15мин POST; provider API только на сервере. |
| CHK011, строка27 | PASS | FR035 и FR053/уточнение2026-10-15 требуют повторную проверку связанной pending invoice/operation во всех continue/start callers с отдельным legacy путём. |
| CHK012, строка28 | PASS | FR035 сохраняет финансовые переходы,idempotency,согласия,worker300с и zero-new-payment; Plan не вводит новый эквайринг. |
| CHK013, строка29 | PASS | FR037/SC013 и Quickstart return требуют browser→ASGI→PG,Chromium/WebKit320/1280,JS-off и отрицательные денежные сценарии. |
| CHK014, строка30 | PASS | FR036/012 требуют status без повторного объявления,фокус,темы200% и клавиатуру; Phase29 не ослабляет эти требования. |
| CHK015, строка31 | PASS | research-payment-return.md отделяет ЮKassa succeeded/return от выбранных инженерных6/60/10/15 и не переносит конверсию на GRAF. |
| CHK016, строка32 | PASS | FR037/SC013 и Plan разделяют три обзора,новый SHA/release и F278/T011/T012/банк/реальные оплаты. |
| CHK017, строка34 | PASS | FR038 диагностирует role/queue причину, требует maintenance runtime role guard и применение existing transaction; одного текста недостаточно. |

### checklists/promo-inline.md

| Пункт и строка | Оценка | Конкретное основание |
|---|---|---|
| CHK001, строка10 | PASS | FR025/029,US1 additional AC1–5 и Contract «Транспорт» различают Apply/Enter/clear/cycle без навигации при JS и native303 без JS. |
| CHK002, строка11 | PASS | FR024 и Contract «Отказ» разделяют public promo error и account_unavailable без обхода acceptance budget. |
| CHK003, строка12 | PASS | Plan «Архитектура» пункт5 требует общий public error для5 loader callers и прямого reserve caller,сохраняя условия. |
| CHK004, строка13 | PASS | FR029/Contract разделяют draft300с/quote10мин/MAX48/binding; cycle/GET/start error не продлевают draft. |
| CHK005, строка17 | PASS | FR026 и Contract «Локальные состояния» сохраняют True/False в документе при denied storage через ошибки/cycle без межконтекстного переноса. |
| CHK006, строка18 | PASS | FR026/027 снимают оферту после нового/сомнительного итога; NoJS full navigation перенос best effort согласован с FR019/020. |
| CHK007, строка19 | PASS | FR028 и Contract «Финансовые границы» перечисляют owner/tenant/session/CSRF/rate/catalog/receipt/pending/quote/authority/idempotency и zero-money preview. |
| CHK008, строка20 | PASS | FR011/029 и Contract ограничивают временную память только bool/scope,без кода/цены/оферты/контакта/денежного права. |
| CHK009, строка24 | PASS | FR027/SC011 задают один запрос,busy блокировку input/Apply/cycle/start,timeout15с и запрет automatic money retry. |
| CHK010, строка25 | PASS | FR027/028 и Plan архитектура3 перечисляют stale/detached/mismatch/unexpected/auth/owner/scope с отказом вставки и явным recovery. |
| CHK011, строка26 | PASS | FR027/SC011 и recovery-required state требуют честную ошибку network/timeout/500/429/swapError,нет старого start до свежего расчёта. |
| CHK012, строка27 | PASS | FR025 и Plan архитектура4 задают replace cycle URL без history entry/кода и с сохранением server query priority. |
| CHK013, строка31 | PASS | FR030/SC010 задают focus/status/alert/aria-invalid,мышь/Enter/клавиатуру,320/200%,темы и оба движка. |
| CHK014, строка32 | PASS | SC010–012/Quickstart matrix требуют browser→ASGI→PG traces,отдельный NoJS native и causal RED/GREEN; fixture не заменяет backend. |
| CHK015, строка33 | PASS | Plan архитектура ограничена existing form/HTMX/templates/lifecycle/public errors без новых API/migrations/money transitions. |
| CHK016, строка34 | PASS | Plan порядок допуска/FR015/SC012 разделяют requirements,analyze,canon,три post-code обзора,converge,exact-SHA/release и F278/людей. |

### checklists/promo-presentation.md

| Пункт и строка | Оценка | Конкретное основание |
|---|---|---|
| CHK001, строка5 | PASS | Уточнение2026-09-30 и T014 требуют исторический цикл из совершённой покупки,не текущей кампании. |
| CHK002, строка6 | PASS | T014 и plan supplement запрещают выдуманный месяц при unknown/missing period. |
| CHK003, строка7 | PASS | T015/FR003/004/011 убирают непроверенный общий список,сохраняют известный код и актуальный итог. |
| CHK004, строка8 | PASS | Plan T014/T015 фиксирует неизменность денег/eligibility/cookie/receipt/idempotency; FR019/020 отдельно расширили только согласия. |
| CHK005, строка9 | PASS | Quickstart T014/T015 перечисляет annual purchase/campaign mutation/unknown/limited offer/apply→cycle→remove. |
| CHK006, строка10 | PASS | FR011/015/016 и Quickstart задают tenant/role/privacy,synthetic provider,новый exact-SHA и отдельные F278/людей. |

### checklists/promo-refresh.md

| Пункт и строка | Оценка | Конкретное основание |
|---|---|---|
| CHK001, строка11 | PASS | FR017/US1 AC5–6/SC007 требуют код+месяц/год после Apply,двух reload и return в той же сессии без нового экрана. |
| CHK002, строка12 | PASS | FR017/018 и Data model задают expiry300с от apply/replace без продления GET/cycle/start error,отказ на now≥expiry. |
| CHK003, строка13 | PASS | FR017 и Quickstart случаи3–4 задают bounded MAX48 включая invalid format,ошибку,запрет оплаты и encoded signed payload без raw headers. |
| CHK004, строка17 | PASS | FR018/ Data model задают exact user/workspace/session,binding/signature,purpose,отказ missing key/session/foreign/tamper/legacy. |
| CHK005, строка18 | PASS | FR003/007/011/018 требуют fresh server quote/eligibility и новую оферту,визуальный recurring по019/020,preview без денежных эффектов. |
| CHK006, строка19 | PASS | FR018/Data model задают отдельные remove/empty/replace/expiry/session/authoritative operation lifecycle transitions. |
| CHK007, строка20 | PASS | FR011/018 и Plan сохраняют узкий path,HttpOnly/SameSite/Secure,нет URL/JS/log/real-code evidence,новых migrations/dependencies нет. |
| CHK008, строка24 | PASS | SC007/FR015 и Quickstart задают positive/error/recovery/boundary matrix,три независимых обзора и новый frozen release. |
| CHK009, строка25 | PASS | Уточнения2026-09-30/10-01 явно отделяют прежний lifetime T014/015 от новых FR017/018,не закрывают T011/T012/F278 и конверсию. |

### checklists/provider-rejection.md

| Пункт и строка | Оценка | Конкретное основание |
|---|---|---|
| CHK001, строка5 | PASS | FR021/023 различают definitive creation rejection без provider_id,настоящий canceled и unknown outcome. |
| CHK002, строка6 | PASS | FR021/023 определяют заголовок по trusted stored state,query не источник финансовой причины. |
| CHK003, строка7 | PASS | FR021/022 задают только общий отказ для historical403 без exact reason,без предположения recurring. |
| CHK004, строка8 | PASS | FR022/023 разрешают specific recurring отказ только при exact причине и фактическом True; malformed/False не получают его. |
| CHK005, строка9 | PASS | FR023 запрещает raw response/description/request IDs/контакты/секреты и разрешает только fixed safe reason. |
| CHK006, строка10 | PASS | FR022/SC009 требуют ручные retry/cycle/False/новую оферту,не automatic POST/снятие recurring/перезапись snapshot. |
| CHK007, строка11 | PASS | FR022/023/Plan сохраняют defaultTrue/явный выбор,promo/quote/CSRF/owner/tenant/idempotency/резервы;expiry не возрождает скидку. |
| CHK008, строка12 | PASS | FR021/023/SC009 запрещают новую оплату при unknown/known provider_id,настоящий canceled сохраняет только existing retry. |
| CHK009, строка13 | PASS | Quickstart provider cases1–4 задают adapter/state/HTTP/Chromium/WebKit320/1280,keyboard и три обзора. |
| CHK010, строка14 | PASS | Clarifications и Plan provider отделяют подключение recurring/settlement/F278/T011/T012 от кода и требуют новый exact-SHA/Full/CD/runtime. |

### checklists/requirements.md

| Пункт и строка | Оценка | Конкретное основание |
|---|---|---|
| пункт01, строка5 | PASS | US1–US4 и FR задают пользовательские результаты; технические ограничения существующих путей в clarification не требуют нового алгоритма; CSS решение оставлено Plan/исполнителю. |
| пункт02, строка6 | PASS | US1–US4,FR001–016 и Assumptions называют пользователей,ценность,финансовые ограничения и исключения. |
| пункт03, строка7 | PASS | Spec содержит scenarios,edge cases,requirements,entities,SC,assumptions,clarifications; US2 independently проверяет объём/период. |
| пункт04, строка8 | PASS | Clarifications2026-09-29…Session2026-10-16 определяют Clear категории;Phase29 не требует нового денежного решения. |
| пункт05, строка9 | PASS | SC001–018 задают измеримые результаты;Session2026-10-16 и Quickstart48 combos измеримы;SC005/006 не подменяются кодом. |
| пункт06, строка10 | PASS | Edge Cases/FR009–012/053–055 и Session2026-10-16 охватывают ошибку,recovery,security,NoJS/геометрию/фокус. |
| пункт07, строка11 | PASS | Assumptions и SC017/018 сохраняют F278 и раздельные synthetic/server/live/installed/financial/human доказательства. |
| пункт08, строка12 | PASS | FR014/016 и SC005/006 требуют реальные наблюдения,а не обещание конверсии каждого посетителя;агентные роли не люди. |

### checklists/subscription-clarity.md

| Пункт и строка | Оценка | Конкретное основание |
|---|---|---|
| CHK001, строка7 | PASS | FR039/SC014 задают effective тариф/короткий срок/auto mode и ровно один основной шаг active off/no-card. |
| CHK002, строка8 | PASS | FR039/042 отделяют нормальное отсутствие карты от реальных method/price/receipt blockers без общего ложного warning. |
| CHK003, строка9 | PASS | FR039/044 и Contract требуют GET checkout текущего month/year без списания и без изменения authority. |
| CHK004, строка10 | PASS | FR040 требует сумму/дату auto on без details,прямую отмену и сохранение доступа без возврата/опроса. |
| CHK005, строка11 | PASS | FR041/044 задают resume amount/date/card/непринятое consent,CSRF/version/quote остаются. |
| CHK006, строка12 | PASS | FR041 различает справку одного уровня и обязательные финансовые условия,точная local date/time/zone доступна. |
| CHK007, строка13 | PASS | FR042/уточненияT051 требуют все blocking kinds/manual_resolution даже без subscription/суммы,без нового запрета от одного keyexpired. |
| CHK008, строка14 | PASS | FR042/уточненияT057/058 задают одновременные причины/pending,safe GET,receipt помощь без нового checkout,нейтральность и prepared exception. |
| CHK009, строка15 | PASS | FR043/T058 требуют effective free/trial/paid/expired,неизвестную дату без выдумки и cycle только active month/year во всех трёх подписях. |
| CHK010, строка16 | PASS | FR044 ограничивает presentation/минимальный context,сохраняет money/API/DB/JS/provider/quotes/session/tenant/idempotency;Phase29 отдельна. |
| CHK011, строка17 | PASS | FR012/045 и Session2026-10-16/Quickstart T069 уточняют NoJS/full-shell геометрию,keyboard,темы,движки200% без clipping. |
| CHK012, строка18 | PASS | research «Управление подпиской» приводит official Krisp billing/cancel/method,исторический2025 предел,свой код/активы и причины отклонений. |
| CHK013, строка19 | PASS | SC014 фиксирует≥50% видимых пояснений того же baseline fixture,исключает labels/numbers/dates/navigation и не гарантирует конверсию. |
| CHK014, строка20 | PASS | SC014,Plan/Quickstart и T070 требуют независимые обзоры/converge/новыйexactSHA/release,отделяют SC005/006/T011/T012/F278. |

### checklists/ux-payment.md

| Пункт и строка | Оценка | Конкретное основание |
|---|---|---|
| CHK001, строка8 | PASS | FR001 перечисляет billing страницы,referrals,ограничения и macOS;Contract «Экраны» и «Смежные входы» задаёт роли. |
| CHK002, строка9 | PASS | FR002 и Contract таблица экранов задают один главный шаг и вторичную информацию для каждого решения. |
| CHK003, строка10 | PASS | FR003/007/019 и Contract «Постоянно видимые сведения» сохраняют полный итог/срок/условный next/согласия вне details. |
| CHK004, строка11 | PASS | US1/FR003 и Contract различают one-time discount,промокод,trial500МБ и paid5ГБ без равнозначной рекламы. |
| CHK005, строка12 | PASS | FR006/US2 AC1–3 требуют общий объём и видимые сложные prepaid переходы без потери больших прав. |
| CHK006, строка13 | PASS | FR007/US2 AC2/4 различают save-without-charge,разовую карту и включение recurring;Phase29 подпись нейтральна. |
| CHK007, строка17 | PASS | Edge Cases/FR009/011 задают pending/unknown/repeat/two-tabs без нового платежа и ложного success. |
| CHK008, строка18 | PASS | Contract «Состояния» различает succeeded_refused/owner_changed/workspace_scope_invalid/elapsed storage и частичную услугу. |
| CHK009, строка19 | PASS | Contract receipt-contact recovery и FR009/039 сохраняют annual cycle,validated next к account/storage/subscription и карту. |
| CHK010, строка20 | PASS | FR010/011/040/041 и Contract требуют доступную cancel/resume,сохранение оплаченного доступа,согласий/сверки. |
| CHK011, строка21 | PASS | FR011 и Contract сохраняют CSRF,роль/workspace,idempotency,provider,каталог,оферту,quote и денежный source of truth. |
| CHK012, строка22 | PASS | FR008 и Contract native policy перечисляют ровно4POST/trusted origin/method и unknown/external rejection. |
| CHK013, строка26 | PASS | FR012/030/036/045/052 задают размеры/темы/масштаб/keyboard/status;Phase29 усиливает NoJS clipping criterion. |
| CHK014, строка27 | PASS | SC002/Contract «Визуальная приемка» сравнивают один fixture/viewport/closed promo,не оправдывают скрытие денег. |
| CHK015, строка28 | PASS | FR014 и research D01–D08/S01–S12 приводят источники,альтернативы/пределы,не выдают внешние conversion за GRAF. |
| CHK016, строка29 | PASS | FR015/016/SC004–006 требуют три независимых обзора и исправления,отдельные реальные люди и метрики. |
| CHK017, строка30 | PASS | FR011/Plan Constitution/FR052 запрещают стороннюю аналитику/private evidence/чужие активы,используют synthetic. |
| CHK018, строка31 | PASS | Assumptions/Quickstart «Закрытие» и T070 разделяют F278/local/commit/CI/Dev/release/внешнюю приемку. |
| CHK019, строка35 | PASS | FR053 и уточнение2026-10-15 задают current linked pending invoice/operation/payer/provider_id во всех hosted callers,legacy отдельно. |
| CHK020, строка36 | PASS | FR054 задаёт invoice.succeeded для receipt notice,query сам не подтверждает деньги;paid service_gap и guards сохранены. |
| CHK021, строка37 | PASS | FR055/уточнениеfallback требуют hidden copy до bind,selectable NoJS source,idempotent init,честный success/error и фокус. |
| CHK022, строка41 | PASS | Session2026-10-16,Plan311+,Tasks Phase29 и Quickstart350+ задают полную NoJS оболочку,320/360,zoom2,геометрию/фокус/условия,8 RED и48 regressions;CSS zoom предел назван. |
| CHK023, строка42 | PASS | Те же новые sections явно задают «Проверить изменение» для increase/decrease,прежний preview POST,отдельный money confirm/receipt guards,неизменные FR019/020 и отдельные F278/людей/Dev. |

## Повторное чтение и итог

| Файл | Checked | Unchecked |
|---|---:|---:|
| invoice-consistency.md | 16 | 0 |
| optional-renewal.md | 10 | 0 |
| payment-return.md | 17 | 0 |
| promo-inline.md | 16 | 0 |
| promo-presentation.md | 6 | 0 |
| promo-refresh.md | 9 | 0 |
| provider-rejection.md | 10 | 0 |
| requirements.md | 8 | 0 |
| subscription-clarity.md | 14 | 0 |
| ux-payment.md | 23 | 0 |
| **Все10 файлов** | **129** | **0** |

Reviewer-owned:121/0; built-in requirements:8/0; ux-payment:23/0. Все checkbox строки после добавления перечитаны и пересчитаны автоматически; ни один неподтверждённый пункт не отмечен.

## Снимок прочитанных требований SHA-256

Значения фиксируют конкретные dirty bytes, а не будущий commit. При содержательном изменении Phase29 до реализации повторно проверить затронутые пункты.

| Документ | SHA-256 |
|---|---|
| `specs/280-payment-clarity/spec.md` | `f3c1406f6387ab1330e49a6a875dc828fc6599af56e88188a616279c9708a404` |
| `specs/280-payment-clarity/plan.md` | `2bf793b2aa874f403040eff0999e7926d3935fc44895b8bdd7735c69e214c4d3` |
| `specs/280-payment-clarity/tasks.md` | `85fbfb232b17ad8a3454dda611d32d018aef1a7bb5cd383d9fde1efba6cbae11` |
| `specs/280-payment-clarity/quickstart.md` | `ab3fec36f53aec5eb60f6c200792bc5d0b7477f18dd671a1d17f50985a79ab84` |
| `specs/280-payment-clarity/data-model.md` | `ee98852e601068856101743d54c5c150f35529a5f3fe4fcc06002a061c6c7edd` |
| `specs/280-payment-clarity/contracts/payment-journey.md` | `c13fef0e0809459e34fae0aba829a657250c5839a4bb4de26347e970945bc9f2` |
| `.specify/memory/constitution.md` | `7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8` |
| `specs/280-payment-clarity/checklists/invoice-consistency.md` | `622d1670076143310393d65a396fe22bf56fad4dcf08284adea22a49b563bcdf` |
| `specs/280-payment-clarity/checklists/optional-renewal.md` | `aa32181fcc2884dc544a3b68fce297c45ffc0aff5217396052b547cd874de917` |
| `specs/280-payment-clarity/checklists/payment-return.md` | `e80800c04a4aa537d613a8fa5ecc3f6e0013da41446bdd74ccffb4d5eca691c3` |
| `specs/280-payment-clarity/checklists/promo-inline.md` | `43f1654fe7e57dbefd00ea9fe228d0d0f796a89b233c53585220eaa01ade197c` |
| `specs/280-payment-clarity/checklists/promo-presentation.md` | `c9105226b2482ab4b310919f639d077dd2dbb224b02f85e71bc3ccea04423057` |
| `specs/280-payment-clarity/checklists/promo-refresh.md` | `59cb858db47dbad8019136b11b92162470ab334640cb14364b9e45676417810a` |
| `specs/280-payment-clarity/checklists/provider-rejection.md` | `1e4d2a77669939130088628ba93a01c08edb1368bfcd5e983363bf0b05d59530` |
| `specs/280-payment-clarity/checklists/requirements.md` | `47e12866d6582d28a1bb76f2d9e3f09636f6c8f03fb9057c0470fc0d37ceaab6` |
| `specs/280-payment-clarity/checklists/subscription-clarity.md` | `1647bc49cef645c2094b71b9ad8d4993c295486bf1fd0e5246e19d8c482829ce` |
| `specs/280-payment-clarity/checklists/ux-payment.md` | `e16b29a028799e04d5ae5928a70cddb955b6ea559cfb32e146f1465b2b02629d` |

## Ограничения и изменения reviewer

Изменены только `checklists/ux-payment.md` и этот отчёт. Код,spec,plan,tasks,quickstart,конституция,GitHub,commits,PR,release/deploy и рабочие изменения других участников не менялись. Исполнение тестов в этой дополнительной роли не проводилось. Для вступления в реализацию root отдельно завершает scoped analyze и canon sync; после реализации необходимы новые фактические доказательства T069/T070. Ошибки текущей реализации не делают требования недостаточными, если ожидаемое поведение и проверка уже заданы. Предыдущий выпуск/старый агентный PASS не допускает новые байты автоматически.


## Независимый узкий refresh после объединения с PR #7612 — 2026-10-16

**REQUIREMENTS PASS — 136 checked / 0 unchecked.** База текущей рабочей копии: `2340d6d2ff4ca2a7f8fb9bde7ae77f20b22ed57b`; новые дополнения/реализация находятся в dirty diff. Старые SHA-256 выше сохранены как история и не характеризуют объединённые документы.

Прочитаны фактические объединённые дополнения spec/plan/tasks/quickstart, все11 текущих checklist файлов и исходные FR-056–059/T066–068 из HEAD. Проверка требований независима от сообщения исполнителя и прежних review PASS. Отдельные чужие review/validation отчёты не использованы.

| Объект | Основание и итог |
|---|---|
| Наши reflow требования, CHK022 | Session2026-10-16 сохранена: shell/NoJS320/360/200%,движки/темы/фокус/видимые условия/нет clipping;Quickstart сохраняет8 causal+48 regression и ограничения CSS zoom/синтетического POST. PASS. |
| Нейтральный preview, CHK023 | Spec/Plan/Tasks/Quickstart сохраняют точную подпись «Проверить изменение»,increase/decrease,прежний preview POST,receipt-contact/суммы/отдельное денежное подтверждение и FR019/020. PASS. |
| Полнота upstream требований | В spec/plan/quickstart весь текст HEAD2340d6d сохранён побайтовым префиксом,наше продолжение добавлено после. В tasks все строки upstream сохранены; дополнение имеет отдельный Phase30. Соседние taskID/issues не менялись. PASS. |
| storage-simplicity CHK001 | FR056/058 сохраняют usage main «занято из общего»,главное увеличение/вторичные записи,native details,reference со своим кодом. PASS. |
| storage-simplicity CHK002 | FR057 сохраняет включённые5ГБ/шаг5ГБ,addon/month/year отдельно от full total,не выдаёт catalog prices за today,точный server preview до подтверждения. Нейтральная подпись не подменяет расчёт. PASS. |
| storage-simplicity CHK003 | FR057/058 и Quickstart «Приёмка простого хранения» сохраняют5/10/15/500ГБ,month/year,zero/max,prepaid/bonus/future decrease и disabled billing. PASS. |
| storage-simplicity CHK004 | FR056/058 сохраняют unavailable/stale/thresholds80/95/full/reserves/exhausted и owner/member privacy/нет ложного действия. PASS. |
| storage-simplicity CHK005 | FR012/058 и Quickstart сохраняют keyboard320/themes/contrast/NoJS,existing contract/browser/storage PG и causal RED/GREEN;наш full-shell regression дополняет,не заменяет их. PASS. |
| storage-simplicity CHK006 | FR059 базовый proof и явное уточнение owner/operator scope сохранены вместе с locks/backup/restore/dry-run/collision/ACL/content/финансовой неизменностью. Отдельный future receipt contact требует current active verified billing owner первым,исторический fallback вторым,прежний отказ при отсутствии,old invoices/начатые оплаты неизменны. PASS качества требований;фактическое operator apply/доставка не перепроверялись. |
| storage-simplicity CHK007 | T068/Plan/Quickstart сохраняют новый exactSHA/base/frozenFull/CD/runtime и раздельные human/денежные/доставка gates;T070 не объявляет их автоматически закрытыми. PASS. |

`checklists/storage-simplicity.md` побайтово совпадает с HEAD. Маркеры и чужие заметки не редактировались. Прочие127 ранее проверенных пунктов не изменены объединением; повторное чтение всех строк чеклистов подтверждает сохранённые требования. Обнаруженный LOW дубль `Phase29` устранён исполнителем заголовком `Phase30` только нашего блока; T066–T070/issue mapping сохранены. **Открытых содержательных gaps нет.**

### Повторный подсчёт после записи

| Checklist | Checked | Unchecked |
|---|---:|---:|
| invoice-consistency.md | 16 | 0 |
| optional-renewal.md | 10 | 0 |
| payment-return.md | 17 | 0 |
| promo-inline.md | 16 | 0 |
| promo-presentation.md | 6 | 0 |
| promo-refresh.md | 9 | 0 |
| provider-rejection.md | 10 | 0 |
| requirements.md | 8 | 0 |
| storage-simplicity.md | 7 | 0 |
| subscription-clarity.md | 14 | 0 |
| ux-payment.md | 23 | 0 |
| **Все11 файлов** | **136** | **0** |

Reviewer-owned128/0, built-in requirements8/0, ux-payment23/0. Все checkbox строки перечитаны и пересчитаны;неподтверждённых отметок нет.

### Текущие SHA-256 объединённых документов

| Документ | SHA-256 |
|---|---|
| `specs/280-payment-clarity/spec.md` | `0252f04aff494d6d7cd339ccf1e56b238b3eb69a9709646bd3ff54e826c7f22f` |
| `specs/280-payment-clarity/plan.md` | `53027e61b9cee5f84561443ce26433289fbd41fb15d72cf17d21733caf326d4a` |
| `specs/280-payment-clarity/tasks.md` | `1582e76f6f7187601090c1507a35569cda5feadab124ae82aed833cfd42d4aeb` |
| `specs/280-payment-clarity/quickstart.md` | `d456b1bea1f7b4112f78e8c5ecbe75f90df47336876e1e3822fd403867c62c49` |
| `specs/280-payment-clarity/checklists/ux-payment.md` | `3fc3f019206408c4b9ef3be04aec2ccea99280c81d97c733ce11101d7b0d456c` |
| `specs/280-payment-clarity/checklists/storage-simplicity.md` | `a7b3a45d27933916db2d3d25843a72e18757e0e1b16f378f245263e6cf1f8ca0` |

Изменения reviewer в этом refresh: только добавления к ux-payment.md и этому отчёту. Код/canonical SDD/GitHub/index/commit/release/deploy reviewer не менял;чужие изменения сохранены. Это narrow requirements refresh перед commit,не новая реализационная/браузерная/операторская/финансовая приёмка. Текущие объединённые code checks/CI/выпуск должны иметь собственное evidence.
