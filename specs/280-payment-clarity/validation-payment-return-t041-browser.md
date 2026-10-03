# F280 — проверка браузера T041/#7490

Дата: 2026-10-03. Режим: `high-risk-product / active Spec Kit slice`.
Исполнитель владеет только двумя тестами и этим отчётом. Исходники контроллера
и шаблона принадлежат root. Прочитаны действующие задачи, план, требования,
quickstart, checklist `payment-return.md` и `graf-f280-t041-task.md`;
текущий независимый допуск требований17/0. Отметки checklist не менялись.

## Сценарий и сохранённые проверки

В существующей ветке `idle-five` добавлен узкий вариант `six-final-cooldown`.
Настоящие защищённые POST→303→GET проходят через HTTP→ASGI→изолированную
PostgreSQL; синтетический поставщик отвечает pending. Только доставка уже
полученного настоящего HTML задерживается до заданной фазы. Начала относительно
первого запроса:0/12/22/32/42/52с; ответы:12/22/32/42/52/53с.

После шестого ответа на53с проверяется немедленное точное сообщение окончания
«Подтверждение пока не получено. Проверьте оплату позже. Повторно платить не
нужно.», отдельное пояснение оставшейся паузы и запрет ручного Enter. На60с
сообщение должно сохраняться, пауза должна оставаться отдельной, ранний Enter
не должен запускать POST. На62с кнопка становится доступной без повторной
инициализации и отправляет настоящий ручной POST с интервалом≥10с. Повторная
инициализация не возобновляет автоматические запросы.

Сохранены существующие проверки документа/маркера, отсутствия внешних запросов
и навигации при refresh, единственного создания платежа, одной операции/счёта,
ожидаемого количества прав доступа, связи права с покупкой, повторяемости и
согласий. Для нового pending сценария права доступа не создаются; количество
POST сверяется с чтениями поставщика. Существующие ошибки, timeout, все границы
контекста, JS-off, доступность, темы и увеличение200% остаются в общей матрице.

## Фактически выполнено

- `node --check apps/server/tests/browser/billing-payment-return.test.cjs`: PASS.
- Сбор через канонический PostgreSQL runner с `--collect-only`: **56 тестов**,
  28 групп×320/1280. Журнал `graf-f280-t041-collection56.log`.
- SHA256 перечня тестов: `f61d5bb9ed1bb294054f821962c07ce747e94abbc7814825dcc25616e09f4d12`.
- Адресный сбор `-k six-final-cooldown`:2 теста на движок. Для четырёх
  причинных отказов на движок приготовлены два одинаковых запуска этих двух
  ширин. Повторы не увеличивают число уникальных сценариев.

**Окончательный результат: Chromium56 PASS + WebKit56 PASS =112 PASS; отказов и пропусков нет.**
Worker-сессия не имеет доступа к Docker socket. Запрос `require_escalated`
отклонён политикой `Never`. Root выполнил подготовленные команды вне этого
ограничения через тот же канонический runner; исполнитель проверяет настоящие
журналы, их SHA и результат. Это разделение исполнения сохранено явно.

На исходном `cabinet.js` SHA `486cf08240cb9f483325d3b9f8fb33040c9ac41cabbdd1dfeed93480a1ee7bc6`
каждый из двух повторов дал2 FAIL/54 deselected: по одному отказу на ширину, суммарно
четыре отказа на движок. Причина во всех восьми случаях одна: на53с фактический
текст — «Следующая проверка станет доступна через несколько секунд.», вместо
точного сообщения окончания. Нет ошибок сборки/подготовки. Четыре SHA
совпадают до и после всех RED запусков. Доказательство:
`graf-f280-t041-red-ready.json`, `valid:true`.

Root изменил исходник только после валидного RED. Файл
`graf-f280-t041-source-ready.json` содержит фактический новый SHA
`1444c3ac7cda96d8f5468236f172fc89a0e961b752104afc3faf4e1f34e13a05`.
Адресный GREEN дал Chromium2 PASS/12,78с, WebKit2 PASS/13,59с; оба56-case
набора начали полную проверку после фиксации всех четырёх SHA.

| Этап | Движок | Результат | Время pytest | Журнал |
|---|---|---|---|---|
| RED, повтор1 | Chromium |2 FAIL,54 deselected |12,19с | `graf-f280-t041-red-chromium-1-v3.log` |
| RED, повтор2 | Chromium |2 FAIL,54 deselected |11,91с | `graf-f280-t041-red-chromium-2-v3.log` |
| RED, повтор1 | WebKit |2 FAIL,54 deselected |12,87с | `graf-f280-t041-red-webkit-1-v3.log` |
| RED, повтор2 | WebKit |2 FAIL,54 deselected |12,60с | `graf-f280-t041-red-webkit-2-v3.log` |
| GREEN | Chromium |2 PASS,54 deselected |12,78с | `graf-f280-t041-green-chromium.log` |
| GREEN | WebKit |2 PASS,54 deselected |13,59с | `graf-f280-t041-green-webkit.log` |

Каждый из шести фактических запусков завершил каноническую очистку:
`postgres_test_cleanup=isolated_container_removed`.

## Неуспешные подготовительные попытки

| Журналы | Результат | Значение |
|---|---|---|
| `graf-f280-t041-red-{chromium,webkit}-{1,2}.log` | shell сообщил ошибку `collection_args[@]: unbound variable`, exit0 из cleanup | system Bash3; браузер и БД не запускались |
| те же имена с `-v2.log` | exit2, запрет записи в стандартный uv cache | сбор не выполнен |
| первичная попытка `-v3`, затем путь повторно использован root | exit1, адресный сбор2 выполнен, Docker недоступен | первоначальный текст сохранён в выводе worker; текущие `-v3.log` относятся к настоящему RED root |

Применён существующий Homebrew Bash5 и временный `UV_CACHE_DIR` с
`UV_OFFLINE=1`; канонический runner не менялся. В заблокированных подготовительных
попытках указан `postgres_test_cleanup=container_not_started`.

## Замороженные файлы перед причинной проверкой

| Файл | SHA256 |
|---|---|
| `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js` | `486cf08240cb9f483325d3b9f8fb33040c9ac41cabbdd1dfeed93480a1ee7bc6` |
| `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_operation_status_content.html` | `d3248713af17aa17cc9bd27a95bf51dcebf500a458e2161b9e88ebc226c27dba` |
| `apps/server/tests/browser/billing-payment-return.test.cjs` | `81573e6983bf4f4cc3fad19304db229166e7b087eaf1a0b22ff583ab7ba6e258` |
| `apps/server/tests/contract/test_billing_payment_return_browser.py` | `6718e667e9a831e98471b5186f31a54c036603fa306352f69406a08f66d62716` |

Первая полная матрица завершилась: Chromium54 PASS/2 FAIL,232,64с;
WebKit54 PASS/2 FAIL,251,63с. Во всех случаях единственная причина — старое
ожидание `/через|секунд/` в основном сообщении `manual-cooldown` после шестого
ответа. T041 теперь требует окончания и отдельного пояснения паузы. Ошибок
подготовки нет; обе базы удалены. Журналы `matrix56-{chromium,webkit}.log` и
машинный результат `initial-green-matrix-result.json` сохранены в локальный временный каталог.

Только после завершения обоих запусков уточнено ожидание шестого ответа:
точный текст окончания, отдельное видимое пояснение паузы и его связь с
кнопкой через `aria-describedby`. Существующие проверки недоступности,
раннего POST, ≥10с и окончательного настоящего ручного POST сохранены.
Первые пять ответов по-прежнему требуют прежнего пояснения. Новый тест T041
не менялся. SHA браузерного теста после уточнения:
`129b83a264f1c35b4f7a0fc1a9602eb4bc4231e1d7f8baa8717946ef8b01bf64`.
Повторно заморожены четыре файла в `final-tests-refreeze.json`; root получил
`rerun-ready.json` для адресных6 и полных56 проверок обоих движков.
Тесты и исходники в ходе полных запусков не менялись.
Коммитов, GitHub, deploy, production PostgreSQL и настоящих финансовых операций
исполнитель не выполнял. Legacy Impact: `untouched`.

## Повторная проверка после уточнения ожидания

Адресные `six-final-cooldown`, `manual-cooldown`, `idle-five` ×320/1280:
Chromium6 PASS/27,47с, WebKit6 PASS/29,39с; отказов и пропусков нет.
Журналы `graf-f280-t041-green-{chromium,webkit}-v2.log`; фазы31/33с,
в обеих случаях `postgres_test_cleanup=isolated_container_removed`.
Повторная полная матрица выполнена на зафиксированном SHA браузерного
теста `129b83a264f1c35b4f7a0fc1a9602eb4bc4231e1d7f8baa8717946ef8b01bf64`;
остальные три SHA соответствуют повторному запуску после source fix.
Окончательный результат приведён ниже; адресный GREEN отдельно от полной матрицы.

## Окончательная полная матрица и контроль неизменности

**112 PASS: Chromium56 / WebKit56, ошибок и пропусков нет.** Фактический
сбор каждого движка —56,28 групп×320/1280; SHA256 перечня:
`f61d5bb9ed1bb294054f821962c07ce747e94abbc7814825dcc25616e09f4d12`.
Все четыре SHA совпали до и после каждого окончательного запуска;
исполнитель независимо сверил текущие байты и SHA журналов с машинной записью.
Во время полных запусков тесты и исходники не менялись. Каждый канонический
runner подтвердил удаление своей изолированной PostgreSQL базы/контейнера.

| Этап | Движок | Результат | Время pytest | Журнал | SHA256 журнала |
|---|---|---|---|---|---|
| green | chromium | 6 PASS | 27.47с | `graf-f280-t041-green-chromium-v2.log` | `280fe5f8839f4ba219ae2135a89cbbeb399d77d95c8fe3ee20bba38909ee56a6` |
| green | webkit | 6 PASS | 29.39с | `graf-f280-t041-green-webkit-v2.log` | `b6323970427c8e0eae987f0a6f9d168f3e19dd5b74a51dc5c568942dcc127f56` |
| matrix56 | chromium | 56 PASS | 235.20с | `graf-f280-t041-matrix56-chromium-v2.log` | `4bbc27674116baf3c0b9aa289d4826780a51fc099c76c33e15e968ec68c63984` |
| matrix56 | webkit | 56 PASS | 254.85с | `graf-f280-t041-matrix56-webkit-v2.log` | `7783cefb2710aac351c618e0280df0f0c8c13d7f973ee84bf079993b3020d005` |

| Файл окончательной проверки | SHA256 до = после = текущий |
|---|---|
| `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js` | `1444c3ac7cda96d8f5468236f172fc89a0e961b752104afc3faf4e1f34e13a05` |
| `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_operation_status_content.html` | `d3248713af17aa17cc9bd27a95bf51dcebf500a458e2161b9e88ebc226c27dba` |
| `apps/server/tests/browser/billing-payment-return.test.cjs` | `129b83a264f1c35b4f7a0fc1a9602eb4bc4231e1d7f8baa8717946ef8b01bf64` |
| `apps/server/tests/contract/test_billing_payment_return_browser.py` | `6718e667e9a831e98471b5186f31a54c036603fa306352f69406a08f66d62716` |

Машинные доказательства: `graf-f280-t041-red-ready.json`,
`graf-f280-t041-source-ready.json`,
`graf-f280-t041-final-tests-refreeze.json`,
`graf-f280-t041-green-matrix-result.json`. Первая матрица с двумя
неуспешными ожиданиями на движок сохранена отдельно в
`graf-f280-t041-initial-green-matrix-result.json`; она не считается PASS.

Для воспроизведения использовать `GRAF_PAYMENT_RETURN_BROWSER=1`,
`GRAF_BROWSER=chromium` либо `webkit`, существующий `GRAF_NODE_MODULES`,
Homebrew Bash5 и `apps/server/scripts/run_local_postgres_tests.sh --focused
 tests/contract/test_billing_payment_return_browser.py -q --tb=short
 --show-capture=no`. Адресный выбор — `-k six-final-cooldown`; повторная
проверка общей ветки — `-k 'six-final-cooldown or manual-cooldown or idle-five'`.
В ограниченной worker-сессии запускал root вне её sandbox через этот же
runner. Worker проверил реальные результаты. Проверка локальная и синтетическая;
точные GitHub SHA/release gates, независимое ревью, настоящие платёжные/банковские
и человеческие доказательства остаются отдельной ответственностью root.
