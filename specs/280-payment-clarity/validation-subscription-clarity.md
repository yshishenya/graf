# F280 T046 — проверка простого управления подпиской

Дата: 2026-10-04. Lane: high-risk-product. Требования: FR-039–045, SC-014; независимый checklist PASS14/0, analyze и issue sync до тестовых изменений. Задачи: T046#7500, T047#7502, T048#7503.

## Причинный исходный отказ

Исходный production source: `a7553db61b2625e767b3afa147c7b61c097fe918`. Перед RED не изменены template, CSS или route; добавлены только проверки в четырех существующих тестовых файлах. Это синтетические состояния, без пользовательской сессии, реального провайдера или настоящих финансовых действий.

Одинаковый baseline active/personal/month/auto-off/no-card: оплачено до `03.11.2026, 12:19 (UTC+03:00)`, следующий период `1 000 ₽`, продление выключено, карта отсутствует. Синтетические снимки baseline сохранены вне git: `off-no-card-chromium-1280-dark.png` и `off-no-card-webkit-1280-dark.png`. Обе реализации браузера воспроизводят ложное предупреждение «Возобновление пока недоступно» и отсутствие очевидного основного действия «Продлить подписку».

Выполнены команды из корня репозитория:

```sh
apps/server/.venv/bin/python -m pytest -q apps/server/tests/contract/test_billing_ui.py --tb=short --show-capture=no
apps/server/.venv/bin/python -m pytest -q apps/server/tests/contract/test_billing_ui.py -k 'subscription_' --tb=short --show-capture=no
apps/server/.venv/bin/python -m pytest -q apps/server/tests/contract/test_billing_accessibility.py --tb=short --show-capture=no
GRAF_BROWSER=webkit apps/server/.venv/bin/python -m pytest -q apps/server/tests/contract/test_billing_accessibility.py --tb=short --show-capture=no
apps/server/scripts/run_local_postgres_tests.sh --focused tests/integration/test_billing_review_regressions.py -k subscription_existing_payment_of_every_kind -q --tb=short --show-capture=no
```

- До новых проверок прежние контракты: **53 passed**.
- Новый subscription contract slice: **19 failed / 7 passed / 51 deselected**. Отказы воспроизводят ложную ошибку отсутствия карты, отсутствие компактного GET-продления/раскрытий, конкурирующее восстановление при неопределенной оплате, неверное представление trial/free при случайно будущем paid_through и отсутствие короткой локальной даты.
- Chromium: **1 failed / 15 passed**, 31.57с; WebKit: **1 failed / 15 passed**, 48.18с. Обе проверки останавливаются на ложном предупреждении no-card; дальнейшую матрицу/NoJS этот RED не подтверждает.
- Настоящий route→изолированная PostgreSQL: **16 failed / 125 deselected**, 66.96с исполнения; контейнер удален штатным runner. Initial/storage pending не видны; renewal/early pending оставляют форму resume; provider_key_expired и отсутствие subscription теряют путь к ожидающему invoice. Ошибок fixture/setup нет.

В тестах матрица реальных invoice содержит initial_checkout/storage_upgrade/renewal/early_renewal × provider_pending/provider_key_expired × subscription present/absent. GREEN дополнительно сравнивает operation/invoice states и числа operation/invoice/grant/quote до и после GET, запрещает provider create_payment. Shared денежный набор состояний не меняется; observation_expired намеренно не включается в новый view-only запрет.

## Дополнительный причинный отказ при первой реализации

Первый полный contract GREEN:77 passed. Первый браузерный GREEN: Chromium16 passed71.12с с синтетическими снимками; WebKit16 passed84.83с. После раскрытия всех invoice видов и подавления конкурирующих форм PostgreSQL еще показала **8 failed / 10 passed / 125 deselected**: активная подписка с картой создавала один неиспользуемый resume_renewal quote при pending/keyexpired invoice (0→1). Финансовые operation/invoice/grant числа и states сохранялись. Новое узкое условие подготовки quote в самом GET запрещает ее при pending invoice или pending/unknown/unknown_pending/provider_key_expired resolution; денежные POST handlers не изменены.

Матрица затем расширена до22case:16invoice случаев, два положительных legacy observation_expired initial_checkout (checkout остается допустимым), четыре resolution-only без ожидающего invoice/amount. Для разрешенного legacy GET допустим максимум один существующий non-financial resume quote; новые operation/invoice/grant или вызов provider запрещены.

## Итоговая проверка текущих файлов

После quote fence и окончательной короткой фразы:

- Полный `test_billing_ui.py`: **77 passed**, прежние assertions сохранены.
- Полный `test_billing_accessibility.py`: **Chromium16 passed71.77с; WebKit16 passed93.23с**. Ноль failures/skips. Собственный bounded subprocess limit вырос90→120с вместе с расширенной матрицей; это предел тестового runner, не изменение таймеров продукта.
- Каждая синтетическая страница проходит320/360/768/1280px × light/dark ×100/200%; доступность основного действия, отсутствие горизонтальной прокрутки, минимальный размер целей, контраст при1280/100%, первоначальный/видимый фокус и сохранение фокуса после reinit. Native details доступны клавиатурой; значения основного dl не имеют стандартного отступа dd. Отдельный настоящий browser с JavaScript disabled отправляет existing resume/cancel формы, проверяет обязательное непринятое resume consent и сериализацию CSRF/version/quote. Provider не вызывается.
- Полный existing isolated PostgreSQL `test_billing_review_regressions.py`: **147 passed /0failed/0skipped**, 390.07с pytest,410с runner; одноразовый контейнер удален. Включены все125прежних financial regressions и22новыхcase. Для pending invoice/resolution operation/invoice/grant/quote counts и operation/invoice states неизменны, provider create_payment0; legacy expiry сохраняет безопасное оформление.

Этот документ не доказывает production выпуск, живое списание, банковское зачисление, возврат, человеческую приемку или рост конверсии; итоговые независимые обзоры и release фиксируются отдельно.

## Методика SC-014

Сравнить описанный baseline и новый active/auto-off/no-card при одной ширине1280, темной теме100%, закрытых native details. Считать видимые поясняющие слова русского текста; исключить названия полей, числа/даты/валюту, навигацию и названия действий. Не учитывать скрытые дополнительные сведения; существенные условия сохраняются перед existing денежным POST. Требование: уменьшение≥50%. Итоговое измерение на том же fixture приведено ниже. Метрика не является обещанием конверсии и не применяется к состоянию неопределенного платежа, где необходимы предупреждения.


## Измерение SC-014

Одинаковый synthetic active/auto-off/no-card, Chromium1280px, dark100%, раскрытия закрыты. Baseline и новая страница действительно отображены с CSS; видимость проверена через браузер. Из p удалены навигационные ссылки, исключена полная дата/время/зона; из dd взято лишь поясняющее предложение про отключенные списания. Отдельный оставшийся союз «и», соединявший исключенные ссылки, консервативно тоже исключен как navigation.

| Пояснение baseline (даты и ссылки исключены) | Слова |
|---|---:|
| «Новые автоматические списания отключены.» |4|
| «Без новой оплаты после [дата] включится бесплатный тариф.» |7|
| «Возобновление пока недоступно.» |3|
| Всего |14|

Новое единственное пояснение: «После этого срока без оплаты — бесплатный тариф.» — **7слов**. Сокращение `(14−7)/14 =50.00%`, требование≥50% выполнено. Первый буквальный DOM count сохранял лишний союз:15→7/53.33%; финальный консервативный результат50% не завышает пользу. Full precise date/time/zone и справочная цена остались в доступных native сведениях; сведения суммы/срока/карты/согласия перед resume POST видны внутри его единственного раскрытия.

Синтетические comparison снимки `compare-old-1280-dark.png`, `compare-new-1280-dark.png` и `prose-count.json` сохранены вне git; новая карточка визуально просмотрена. SC-014 ограничена именно этим обычным no-card состоянием, не отменяет необходимые пояснения при pending/blocker и не является метрикой конверсии.

## Привязка итогового прогона к содержимому

База `a7553db61b2625e767b3afa147c7b61c097fe918`; итоговые source/test bytes заморожены на старте прогона до реализации release. SHA-256 ниже позволяют проверить отсутствие дрейфа до коммита. Commit/PR/candidate SHA и независимый review будут добавлены основным агентом отдельно.

| Файл | SHA-256 |
|---|---|
| `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_subscription_content.html` | `3fa4aa82bbe3362e3f3688a44c19fda0467656cf72eed11b3f1f868dd33c2d13` |
| `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css` | `77ee7e8297b2c9c4696e115f1d7729b70380079eb26bf0a23df897718f5f2247` |
| `apps/server/src/twobrain_rec_server/cabinet/web_routes/billing.py` | `b199d977373883be3a94c5d395387c219beed1eebbdd3931921188bfdcced666` |
| `apps/server/tests/contract/test_billing_ui.py` | `14b17920fbae54d05f14d4ce1b8d9a76b9e608941f65c29ee9e701978845b723` |
| `apps/server/tests/contract/test_billing_accessibility.py` | `559a0c7590593015ac3e75e2b4784e0b66601d6df9e29aa2fdd248b408e9dfef` |
| `apps/server/tests/browser/billing-accessibility.test.cjs` | `4a76c35e0d838a4255778c01ac322f104cf3688cd3037bca8620cb81e0220a85` |
| `apps/server/tests/integration/test_billing_review_regressions.py` | `1e0833ca58e0a6cc4597601f751bc469861d62657e5c222e5bead8f4cb875b2f` |


Дополнительное текущее чтение Chromium/WebKit при320px/dark/200%, JavaScript disabled: native «Способ оплаты и условия» раскрывается Space, полная дата/время/зона видимы; фокус фактически на summary, вычисленный outline solid2px. CSS встроен в synthetic документ заранее; попытка addStyleTag при JavaScript disabled была остановлена из-за ограничения тестового API и не является дефектом продукта. Снимки `focus-chromium-320-dark-200.png` и `focus-webkit-320-dark-200.png` вне git. После всех итоговых прогонов SHA-256 семи source/test файлов перечитаны и совпали с замороженными значениями таблицы.

После rebase актуальной общей CSS F285 выполнена независимая повторная проверка: Chromium16 PASS61.93с, WebKit16 PASS90.65с,44 focus checks PASS. Шаблон и маршрут совпадают с таблицей; актуальная CSS SHA-25624074ca3bc01545a1ab794c8df222e36622fa1cbe171a6a327dfe840fe200a64. Отчет: review-subscription-clarity-browser.md; предыдущие хеши описывают исходный прогон до интеграции. Архив fragment v2026.10.04.1 сохранен побайтово, текущее изменение находится в changes/unreleased/F280.yaml только с T046–T048.


## T049 — прежнее ожидание полной даты в основной сводке

Причинный GitHub CI RED: `governance-fast` run `37159387757` на SHA `4eda104af2522b435fb7d38f6e45c490cb28e221`, выбранный денежный набор180case:179passed/1failed. Единственный отказ — `test_subscription_page_names_the_real_charge_day`: прежний assertion ожидал полную дату/время/зону внутри основного «Оплачено до», тогда как утвержденные FR-039/041 требуют короткую локальную дату и полные условия в native details. Новый T049/#7507 оформлен и синхронизирован до изменения; требования не расширены.

Изменен только существующий `apps/server/tests/unit/test_billing_money_path_e2e.py`: добавлен импорт уже существующего `local_datetime`; последнее markup ожидание заменено проверкой точного значения короткой viewer-local даты в основном `billing-subscription-facts`, отсутствия полного срока в том же поле, закрытого native раскрытия «Способ оплаты и условия» без вложенных details и точного полного срока в поле «Точный срок доступа». Все прежние checkout/webhook/reconcile/paid-through/recurring assertions и проверка реальной первой попытки за72ч сохранены. Эта правка не меняет код продукта или денежные переходы.

```sh
apps/server/scripts/run_local_postgres_tests.sh --focused tests/unit/test_billing_money_path_e2e.py -k test_subscription_page_names_the_real_charge_day -q --tb=short --show-capture=no
apps/server/scripts/run_local_postgres_tests.sh --focused tests/unit/test_billing_money_path_e2e.py -q --tb=short --show-capture=no
apps/server/.venv/bin/ruff check apps/server/tests/unit/test_billing_money_path_e2e.py
git diff --check
```

Целевой PostgreSQL GREEN: **1passed/70deselected**,5.71с pytest/10с runner. Полный существующий файл: **71passed/0failed/0skipped**,63.50с pytest/68с runner; collection digest `730f03bf1a6c92701a74b5cfb5e5d06beb3a869edf81ec91a992e5541ea5d026`. Оба одноразовых контейнера удалены штатным runner; `ruff` и whitespace checks PASS. Этот полный файл содержит71case, исходные180case относятся к объединенной выбранной CI-группе; результаты не смешаны. Два прежних предупреждения fixture plugin/Starlette не являются skip.

Исходники template/CSS/route не менялись в этом срезе; независимый test review и новые exact-SHA CI доказательства оформляет основной агент. Реальных новых платежей, списаний, возвратов или grants нет. Тестовый файл SHA-256 после обоих GREEN: `93ae6b4eed0ca2dd5de3c7ed9fc0539dc4dca75531bf1e851e1f2b7f7d34681d`.
