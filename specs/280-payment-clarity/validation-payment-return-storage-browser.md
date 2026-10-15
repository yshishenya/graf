# F280 — повторная браузерная проверка после T042/T043

Дата:2026-10-03. Lane:high-risk-product, действующая F280. Финальная матрица настоящего браузера→ASGI→PostgreSQL: **Chromium56 PASS / WebKit56 PASS, failed0/skipped0**. 28 сценариев на каждую ширину320/1280. Collection digest `f61d5bb9ed1bb294054f821962c07ce747e94abbc7814825dcc25616e09f4d12`. Каждый runner подтвердил удаление изолированного контейнера.

| Движок | Время pytest | Временный журнал | SHA256 журнала |
|---|---|---|---|
| chromium | 56 passed, 2 warnings in 233.93s (0:03:53) | `graf-f280-storage-final-matrix56-chromium.log` | `6bc3c9f5b6fcfc79c79ba8208b4b5e4ff7b097e34f277e83fdc6eb46f0ca04c0` |
| webkit | 56 passed, 2 warnings in 254.07s (0:04:14) | `graf-f280-storage-final-matrix56-webkit.log` | `7eafa0424f45bd9730f9a5b02ea45e20489565917f9ba87ae47ebf178b789ae4` |

Все шесть контрольных сумм совпали до/после обоих прогонов и с текущими файлами:

| Относительный файл | SHA256 |
|---|---|
| `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js` | `1444c3ac7cda96d8f5468236f172fc89a0e961b752104afc3faf4e1f34e13a05` |
| `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_operation_status_content.html` | `a33426dee1cb1ea7d12d94d1752a46ebac91dd073e37dd9754f773dbfc4b27c1` |
| `apps/server/tests/browser/billing-payment-return.test.cjs` | `129b83a264f1c35b4f7a0fc1a9602eb4bc4231e1d7f8baa8717946ef8b01bf64` |
| `apps/server/tests/contract/test_billing_payment_return_browser.py` | `6718e667e9a831e98471b5186f31a54c036603fa306352f69406a08f66d62716` |
| `apps/server/src/twobrain_rec_server/cabinet/web_routes/billing.py` | `0af48ddb2d628815dc0626d4cbd7e7a84328b3b2e37512ac2daaff09fdb787d5` |
| `apps/server/tests/integration/test_billing_clarity.py` | `0d34024119097888e56b81370d6c6acd8b93783d6aaffffb4c0e160501cf3a45` |

Контроллер и существующие browser tests не менялись. Повтор проверяет подписку, успех/ожидание/ошибки, лимиты, остановку при смене контекста, ручное восстановление, фокус, раскрытые сведения, темы и увеличение200%. **Это регрессия общего поведения страницы, а не самостоятельные браузерные доказательства покупки хранилища.** Для хранилища отдельно выполнены32 причинные проверки настоящего route→PostgreSQL и общий набор157 PASS: [отчёт](validation-payment-return-storage.md).

Имена журналов и машинной записи `graf-f280-storage-final-result.json` обозначают временные локальные артефакты. Они не опубликованы в Git и не представлены доступными читателю ссылками. Исторические результаты T041 относятся к прежним исходникам и сохранены без переобозначения. Независимые обзоры и выпуск требуются отдельно; реальная UI-сессия пользователя и production этой матрицей не проверены.


Дополнительные статические проверки актуального среза:74 PASS (`test_billing_clarity.py` и `test_billing_ui.py`), Ruff изменённых Python файлов, `node --check` контроллера/браузерного теста, governance и `git diff --check` PASS. Они не заменяют route/DB, браузер и выпуск.
