# Независимый обзор исходников — платёж и чек F280

Дата: 2026-10-04. Base: `3cf989cd93f4d3d4b72f83068664f802a11a5eac`. Проверен полный рабочий product+tests diff относительно base, полные invoice/helper функции и все найденные production callers mailto. Reviewer изменяет только этот отчет, не код/canonical/checklist/GitHub/коммиты/выпуск. Полоса: source/security review active high-risk-product invoice среза.

## Решение после исправления S001

**SOURCE PASS: 0 CRITICAL, 0 HIGH, 0 исправимых MEDIUM.** Первый проход HOLD обнаружил S001 на переполнении viewer-local даты. Исполнитель узко обернул форматирование `_invoice_period_labels` в catch `ValueError/OverflowError` с nullable результатом. Reviewer повторно прочитал функцию и самостоятельно выполнил верхнюю границу Europe/Istanbul, нижнюю America/New_York и обычный cross-midnight; все три pure-source assertion прошли. Общие helpers/денежная модель не изменены.

В существующую parameterized route invalid-period regression добавлены upper9999Z и lower0001+14. Их наличие/содержательные assertions прочитаны; затем reviewer прочитал текущий isolated PostgreSQL лог25passed/71deselected45.65s и самостоятельно сверил SHA256 `1796057225bdd6f8c74ba37deb0bf8b1a62bd64f7be7f7b9a39920eed8fca946` файла `/tmp/f280-invoice-db-boundary-green.log`. Upper/lower JSON cases требуют настоящего GET200 и неизменности финансового snapshot. S001 закрыт source+verified regression evidence, лог принадлежит DB исполнителю и не объявляется повторным запуском reviewer. CI/release остаются отдельны. Последняя прочитанная дополнительная правка — единый changelogF280.yaml и дополнительные storage/support route cases; прежние product changes и guards сохраняются.

| ID | Приоритет | Место | Проверенный дефект | Исправление и регрессия |
| --- | --- | --- | --- | --- |
| S001 — исправлен, pure-source повторно PASS | P2 / MEDIUM исходного прохода | `apps/server/src/twobrain_rec_server/cabinet/web_routes/billing.py:4402–4403` | ISO-границы проходят parse/type/order, но перевод в viewer-local зону может переполнить datetime. При viewer `Europe/Istanbul` и строках `9999-12-31T20:00:00+00:00` / `9999-12-31T23:59:59+00:00` вызов `_invoice_period_labels` воспроизведенно бросает `OverflowError: date value out of range`. Invoice/segment projection не перехватывает его, поэтому вместо неизвестного периода защищенный GET завершается500. | Узко вернуть `(None,None)` при `ValueError/OverflowError` преобразования/форматирования этого периода; не менять глобальные helpers. Добавить эти JSON snapshot границы и нижний край с отрицательной viewer zone в существующий parameterized invalid-period/GET regression; сохранить read-only snapshot assertions и явно200/fallback/no raw malformed даты. |

Самостоятельный runnable repro из `apps/server`:

```sh
PYTHONPATH=src .venv/bin/python - <<'PY'
from twobrain_rec_server.cabinet.web_routes.billing import _invoice_period_labels
from twobrain_rec_server.cabinet.user_time import apply_user_time_preference
apply_user_time_preference(user_id='synthetic', session_id='synthetic', timezone='Europe/Istanbul')
assert _invoice_period_labels(
    '9999-12-31T20:00:00+00:00', '9999-12-31T23:59:59+00:00'
) == (None, None)
PY
```

Это synthetic read-only check; он не обращается к БД/провайдеру/почте. Первый проход воспроизвел OverflowError; после исправления этот repro PASS. Дополнительно проверена нижняя граница America/New_York с0001-01-01UTC и нормальный Istanbul cross-midnight. Negative mailto проверки предыдущего прохода PASS; helper с того прохода не менялся.

## Проверенные свойства diff

- `billing_invoice_detail_page` сохраняет настоящую personal owner membership/immutable owner проверку, workspace-scoped invoice query и текущий payer mandate. Previous-owner service-gap view допускает только прежние `owner_changed/workspace_scope_invalid`; receipt/card/contact закрыты при `not can_manage`. Новых разрешений или monetary API нет.
- GET использует чтение select/profile и чистую проекцию; новых commit/add/flush/provider/operation/refund calls нет. Checkout, subscription, consent JavaScript, provider money handlers и shared monetary helpers diff не меняет. FR019/020/checked выбор остаются вне invoice scope.
- Receipt AVAILABLE требует текущего payer permission и прежнего allowlisted HTTPS URL. AVAILABLE без URL показывает зарегистрированное состояние без действия/обещания отправки; неизвестная регистрация безопасно переводится в UNKNOWN. URL validator не меняется.
- Короткие/точные даты используют один snapshot и viewer-time контекст. На обычном случае `2026-10-03T21:30Z→2026-11-03T21:30Z`, Europe/Istanbul: коротко `04.10.2026 — 04.11.2026`, exact зона сохранена. Naive/malformed/reversed/неизвестный cycle не объявляют оплаченный месяц. S001 на пределах диапазона исправлен и pure-source проверен независимо; route regression проходит отдельно.
- Created_at подписан «Дата создания платежа», не settlement. Исторический/будущий период не объявляет текущий тариф активным. Positive integer capacity и discount1–100 фильтруют bool/нулевые/некорректные значения; valid storage intervals сохраняются. При недостоверном интервале показывается «Срок не указан» вместо выдуманной даты.
- Оба public mailto builder используют один внутренний helper. Production callers: история использует прежний refund wrapper; invoice — refund/question. Статические prefixes, safe invoice regex, decoded CRLF rejection и percent-encoded address устраняют query/header insertion. Самостоятельный check encoded/raw CRLF отклонён; адрес с `?cc=` создаёт только subject/body query. Новый question intent не берётся из непроверенного query.
- Jinja автоэкранирование сохранено, raw support mailto fallback удалён. Недопустимый адрес даёт ясное отсутствие контакта и прежнюю help-ссылку. Нейтральное обращение/возврат различаются, статический текст честно сообщает отсутствие отправки/финансового действия.
- Нативные ссылки/details/button, видимые globals focus styles, hierarchy/main/tabindex и существующий copy handler сохранены. Copy пишет только safe number и объявляет результат через status/aria-live; без JS номер остаётся текстом для ручного копирования. Service-gap/recovery/receipt на виду, история сверху, одна доминирующая status link.
- Первоначальный CSS добавил4 узкие invoice строки и переиспользовал order-summary/disclosure; width720 согласован с subscription. Status template меняет только dlclass; формы, финансовая copy, data attributes, live region, ordering и авто-проверка не изменяются.
- Нет сторонних assets/font/dependencies или скопированного конкурентного кода; новых abstractions/services/state нет. Helper extraction служит двум действующим intentions и сохранению прежнего refund API, не speculative layer.

## Проверка тестового diff и пределы

Полностью прочитаны новые изменения `test_billing_clarity.py`, `test_payment_history_support.py`, `test_billing_accessibility.py` и `billing-accessibility.test.cjs`. Existing tests не удаляются; содержательные invoice route→DB privacy/nullable/state/get-purity assertions добавлены, copy/native keyboard/две темы/320–1280/200%/JS-off — в существующую browser matrix. Browser fixture передаёт синтетическую готовую проекцию, поэтому browser PASS сам по себе не проверяет route localization/URL privacy; это покрывают отдельные integration проверки. Внешние mailto/receipt действия browser не выполняет.

Reviewer самостоятельно запустил только маленькие pure-source assertions для normal date/mailto и reproductionS001. Полные92contract PASS сообщены координатором, здесь не переобъявляются результатом reviewer; другие тесты еще выполняют отдельные участники. Не выполнены текущие CI/merge/frozen Full/CD/live/installed Dev/финансовая/человеческая приемка. Это source review рабочего diff, не готовность продакшена.

Независимые PNG/visual проверки выполнены в отдельном `review-invoice-consistency-visual.md`. Browser report сообщает Chromium16PASS/WebKit16PASS, reviewer не запускает их второй раз и не выдает чужой прогон за свой.

На момент окончания source review координатор отдельно сообщил отказы full status guards/lifecycle matrix. Reviewer эту диагностику не подменяет и не объявляет общий validation/release PASS. Invoice source замечаний после повторной проверки0; status matrix — самостоятельный открытый общий gate.


## Независимая повторная проверка плотности — 2026-10-04

**SOURCE PASS: 0 CRITICAL, 0 HIGH, 0 исправимых MEDIUM.** Координатор передал прямой ответ владельца «Сделать карточку плотнее». Проверенная узкая дополнительная правка — ровно два invoice CSS правила: `.billing-invoice-page .billing-checkout-card { gap:12px; padding:16px 20px; }` и `.billing-invoice-page .billing-order-summary > div { padding-block:8px; }`. Это авторизованное уточнение уже утверждённого компактного представления, не новая денежная/информационная модель. Canonical уточнение принадлежит основному писателю; reviewer не меняет canonical документы.

Селекторы ограничены `.billing-invoice-page`: width720, шрифты, цвета/контраст, min target sizes, focus-visible, native links/details/button, semantic template/handlers не изменены этой правкой. Общая карточка имела gap18/padding24, строки10; теперь сокращён только свободный интервал. Специфичность сохраняет invoice отступ16/20 и при мобильных media rules; на320 текст переносится, закрытый service-gap остаётся снаружи details. Семантические денежные guards, согласия/права/provider/DB остаются прежними. Invoice-required существенные факты не скрыты и не удалены.

Reviewer лично прочитал свежие accessibility логи: Chromium16passed52.71s и WebKit16passed59.51s. Прочитал исходные assertions: ширины320/360/390/768/1280 × обе темы ×100/200%, общий overflow, width720, минимум24px существующих контролов, contrast, native Space раскрытие/copy/mailto focus, JS-off и0POST. Новых browser/DB запусков reviewer не делал.

Историческое сообщение об отказах общей status матрицы выше относится к первому проходу. Текущие serial full логи лично прочитаны: Chromium56passed323.91s, WebKit56passed348.98s, isolated runner result=pass/cleanup. Эти прогоны выполнены до density2rules; оба правила исключительно invoice, поэтому dedicated status класс/контроллер не менялся. Это подтверждает устранение прежнего тестового блокера по данным исполнителя, не заменяет current exact-SHA CI/release proof.

HEAD рабочего дерева `3cf989cd93f4d3d4b72f83068664f802a11a5eac`; правки ещё рабочие, поэтому проверка привязана к fingerprints:

| Путь | SHA-256 |
|---|---|
| `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css` | `144b3649d73a02cf5b6634bc80c87b6e9162433aa561f2346a6739a9568e752d` |
| `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_invoice_content.html` | `01c99f0ab8887df3293086bd205a4d6d0ae0c1380c7a71cd18d125a86d2c5d87` |
| `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_operation_status_content.html` | `fedac5cd47b383c0ac7479b509ac6b7d3c5ac48064462cd9bba2e971c0c6f9a9` |
| `apps/server/src/twobrain_rec_server/cabinet/web_routes/billing.py` | `e4815d076732d0b07a9461208198c63f77c0edf6130bd4c3b477445e3daf7d4e` |
| `apps/server/src/twobrain_rec_server/billing/refund_email.py` | `abf37fbc463143c4b5f1d354713b55a22f757381500d1a008a6c802a4447282b` |
| `apps/server/tests/browser/billing-accessibility.test.cjs` | `9fa5055645b6a05eb34e260401edd594f9c7cf88f8bb8d8248d12a30040e53ce` |
| `apps/server/tests/contract/test_billing_accessibility.py` | `964d7b5503e3f26461d5fcca8bb845f82bf1d3c8df5c0bd70fdb67472441889c` |

| Артефакт вне git | SHA-256 |
|---|---|
| `/tmp/f280-invoice-density-chromium.log` | `4dceb661e012ea8ecb7e7813f63c35572ef0b24bf655234f78a57c687a15db30` |
| `/tmp/f280-invoice-density-webkit.log` | `2e2761d83f8851503746188da7ae0dabe8b8807af2e30e46f8881ead7aadf8f6` |
| `/tmp/f280-invoice-density-chromium/pages.json` | `ae0fa45b0e0caa537d212b1d7051ae82ea7b2305a3d4b66f4a79b580fce1b568` |
| `/tmp/f280-invoice-density-webkit/pages.json` | `ae0fa45b0e0caa537d212b1d7051ae82ea7b2305a3d4b66f4a79b580fce1b568` |
| `/tmp/f280-invoice-status-chromium-serial-full.log` | `4753546cef3dff9f967b011e362309c11616c1ed6dcde9dcb8f93a07aa34f3d8` |
| `/tmp/f280-invoice-status-webkit-serial-full.log` | `3c78aba26927d7e696174082c4dc0c37fcaf4756af590f56f7a32ddb2efe8664` |

Независимый визуальный повтор записан в отдельном visual report. Release/full/CD/live/установленный Dev/реальные деньги/человеческая приёмка остаются отдельными; SOURCE PASS не утверждает выпуск.
