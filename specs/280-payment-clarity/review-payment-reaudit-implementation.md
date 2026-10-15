# F280 — независимая проверка реализации повторного среза

2026-10-16. Reviewer `/root/ux_research`; ветка `codex/280-payment-reaudit`, исходный HEAD `0a235f175bed306324064b68a7c1e38bffa322b0`. Проверен фактический незакоммиченный diff T062–T064 / FR053–055 относительно этого HEAD. Lane `high-risk-product`. Ownership reviewer ограничен этим отчетом; код, тесты, SDD, checklist, GitHub, commits и выпуск reviewer не менял. Прогоны не дублировал.

**SOURCE REVIEW PASS: новых применимых critical/high/medium замечаний к изменению нет. Завершенные Chromium/WebKit журналы подтверждают затронутый браузерный контракт. Полная платежная приемка и выпуск остаются отдельными воротами.**

## Основания и выводы

Прочитаны текущие FR053–055, SC018 и уточнения actor/provider_id/legacy/fallback в spec/tasks, независимый requirements report, полный product diff и окружающие guards затронутых маршрутов, изменения контрактов/HTTP-PG/браузерных проверок и существующий initializer. Применены `code-reviewer` и `web-design-guidelines`; актуальный источник рекомендаций проверен по `https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md`. Согласованная плотная композиция, 720px, исходно непринятая оферта и включенное необязательное автопродление этим срезом не меняются. Материалы Krisp и новые зависимости не добавляются.

| Требование | Независимая проверка фактической реализации | Результат |
|---|---|---|
| FR053 / T062 | `_hosted_checkout_url` требует обе записи текущего workspace, связь invoice.operation_id с operation.id, invoice.pending и operation.provider_pending, разрешенный kind/URL и actor. Initial требует provider_id; историческое отсутствие actor разрешено только initial, storage требует точного текущего пользователя. | PASS |
| Все hosted callers | GET checkout, status, явное continue и start recovery для same-key/unresolved/IntegrityError winner используют общий helper. `_recover_checkout_operation` читает invoice с фильтром workspace/operation; отказ ведет в локальный статус либо `/billing?result=pending`, ответ 303 и очистка draft сохранены. Helper только читает и выбирает адрес. | PASS |
| Существующие guards | Permission/flags/actor проверки внешних callers сохранены; initial legacy без provider_id остается отдельной ветвью с прежними `_initial_checkout_can_continue`, `_checkout_invoice_can_continue`, ключом и dispatch. Существующее присвоение исторического actor в explicit continue не выдавалось за новый read-only путь. Истечение provider key само по себе не блокирует уже действующий provider_pending URL. | PASS |
| FR054 / T063 | Флаг `receipt_refresh_failed` теперь дополнительно требует `invoice.status == succeeded`; произвольный result query не создает подтвержденную оплату. Разрешение receipt-only и сообщения service_gap не изменены. Оплаченная услуга, требующая сверки, сохраняет видимое предупреждение. | PASS |
| FR055 / T064 | Все четыре существующие copy buttons получают native `hidden` в HTML, общий initializer снимает его после addEventListener. Значения номера/адреса/ссылки остаются в обычном видимом содержимом, input readonly или раскрываемых сведениях; без JS нет обещания работающего действия и лишней остановки Tab. | PASS |
| Клавиатура и запасное копирование | Существующий native button остается доступен Enter/Space после инициализации, повторная инициализация защищена copyReady. Отказ Clipboard API допускает textarea/execCommand; успех и полный отказ различаются в role=status/aria-live=polite. finally удаляет временное поле и возвращает прежний подключенный фокус только при потере фокуса на body, с preventScroll. | PASS по исходникам; браузерный результат отдельно |

Новых дефектов, требующих изменения кода, при чтении не найдено. Содержимое публичного интерфейса не пополнилось техническими подробностями. CSS и согласованные карточки/режим согласий не менялись.

## Проверки и их границы

Проверены сами новые тесты: матрица start проходит настоящие HTTP/PG ветви replay/blocker/winner, подменяет только первый lookup для причинного попадания в IntegrityError recovery, затем читает сохраненного победителя. Ее fixture запрещает создание YooKassaClient; сравниваются все billing/workspace_subscriptions строки, timestamps и counts. Проверки actor, terminal/missing/foreign/mismatched invoice, URL, provider_id и expired key не заменены браузерными заглушками. Матрица receipt проверяет unpaid и succeeded/service_gap с подставленным query и неизменным снимком БД.

Браузерный diff проверяет все четыре caller без JS и с JS, ручное выделение исходного значения, отсутствие dead tab stop, два повторных htmx:afterSwap, Clipboard API success, denial с успешным fallback и полный отказ; один обработчик, локальные сообщения и сохранение фокуса. Существующая матрица ширин 320/360/390/768/1280, тем light/dark, масштаба 100/200%, контраста и достижимости действия сохранена. Fair-use добавлен в набор и корректно исключен из специфичного для billing начального h1 focus; сценарии его копирования остаются активными.

Непосредственно прочитаны завершенные журналы `f280-reaudit-presentation-green` (presentation: 21 passed), `f280-reaudit-safety-green` (initial checkout recovery и billing security: 28 passed) и `f280-reaudit-shell-green` (cabinet static assets и settings contract/view models: 112 passed). Журнал `f280-t064-copy-red` содержит причинные четыре падения на отсутствии hidden до product исправления. Отдельный sibling-набор `f280-reaudit-sibling-green` также завершен: 267 passed, 2 warnings, 396.85s; runner status=pass, duration_seconds=402, `postgres_test_result=pass` и `isolated_container_removed`. Ожидаемых локальных тестовых результатов для этого отчета больше нет. Сводная приемка и дальнейшее обновление статуса находятся в [validation-payment-reaudit.md](validation-payment-reaudit.md).

Прочитаны завершенные Chromium `f280-t064-chromium-final`: 59 passed, 2 warnings, 66.51s, и WebKit `f280-t064-webkit-final`: 20 passed, 2 warnings, 90.35s. Это подтверждает успешное завершение браузерного контракта и соседних тестов этих прогонов после исправления helper. Предупреждения относятся к pytest import rewriting и существующей Starlette/httpx deprecation. Визуальная независимая оценка снимков принадлежит отдельному проверяющему; здесь ее результат не подменен.

Независимо сверены сохраненные fixtures обоих окончательных прогонов Chromium/WebKit: по 78 страниц; оба набора `billing-pages.json` имеют SHA-256 `ad83b5552fe3dfcfad37f2d108e53f64d50b204f667debc1376b88c79730ca95`.

Промежуточные `f280-t064-chromium-green` и `f280-t064-webkit-green`, несмотря на имена, на момент чтения содержали TimeoutExpired 300s и соответственно 58/19 прочих passed; они не приняты как GREEN. Владелец браузерного прогона уведомлен и локализовал зависание нового helper на `page.addStyleTag` при отключенном JavaScript. Независимо перечитано его исправление: действующий CSS теперь передан в исходном HTML того же синтетического ответа; все проверки/таймеры сохранены, product файлы не изменены. Итоговый независимый браузерный вывод опирается на завершенные журналы с суффиксом `final`. Новых product-дефектов из timeout журналов не установлено.

Дополнительно непосредственно прочитан завершенный `payment-reaudit-full-green`: полные `test_billing_clarity.py` и `test_billing_ui.py`, 289 passed, 2 warnings, 142.30s; collection_count=289 и завершение isolated PostgreSQL runner с `postgres_test_result=pass`/`isolated_container_removed`. Отдельный sibling-набор подтвержден своим завершенным журналом выше.

Этот отчет не доказывает production, финансовую F278, установленное GRAF Dev, SC005/006 или человеческую приемку. Exact PR SHA/base, merge, frozen release-full, штатный deployment и текущая live проверка остаются отдельными воротами T065.

## SHA-256 проверенного product снимка

Пути в таблице относительно корня репозитория. При изменении любого из этих файлов вывод требует повторной сверки.

| Файл | SHA-256 |
|---|---|
| `apps/server/src/twobrain_rec_server/cabinet/web_routes/billing.py` | `30530765973b9f2073a2a08dcc005943d9b2ae21d613f297667ebc57902b5623` |
| `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js` | `ecfc375b7374b9a19f759d69b08b6df80885a56bf09556844fae7a2033d05fa6` |
| `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_invoice_content.html` | `388491ebcdce197493f47147a6f1677bdab92c6541b4a263d4b4a305604ab04f` |
| `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_history_content.html` | `2abee565e4b56edfb9976e51ec9feb77298d4a491c37936981a32e30c80b1c7a` |
| `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/referrals_content.html` | `9beade0c2c625a1629a6cb92dcc0ea39b7e4e9c14a5d82666b35e71cac521752` |
| `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/fair_use_content.html` | `f262b9e97251ff43f0a394c035973410220ca349895b08e8def6592983f7f535` |

Проверенный снимок измененных тестов и прочитанных журналов. Названия журналов логические, без привязки к временному каталогу конкретного компьютера; полные исходные журналы не включены в репозиторий. Контрольные суммы позволяют сопоставить сохраненное доказательство со сводным [validation report](validation-payment-reaudit.md).

| Файл | SHA-256 |
|---|---|
| `apps/server/tests/browser/billing-accessibility.test.cjs` | `590d5c7529c0efc1800d81621464d4aa547cccf71730039b04a8b536c011c0f1` |
| `apps/server/tests/contract/test_billing_accessibility.py` | `35fa2de41619c80db1b1fbb068fde9808d2204da5fe072647c4160c5b08a1c04` |
| `apps/server/tests/contract/test_billing_ui.py` | `b3eeea724d36c56657ef0d67892111c15e84a22c62158c02506a382684501358` |
| `apps/server/tests/integration/test_billing_clarity.py` | `de7729f3a775501e64b48baf5f1239a6f11b9d0b4c7fa7c807f7987c5a10aaa7` |
| `f280-reaudit-presentation-green` — PASS 21 | `50743e5faad08cdb9b2cb75e97df328ecdab06f0e6abc8f259ced3efdaf6b164` |
| `f280-reaudit-safety-green` — PASS 28 | `69282c077db9925c91bf527929e3308840590a6714d8f61a810cba39302dfc88` |
| `f280-reaudit-shell-green` — PASS 112 | `d023367d4d6eb8e2f8e55e34666f75834a7021cd4c0b307ba2a1b256fb3eac28` |
| `f280-t064-copy-red` — RED 4 | `e38b44ba52c17dd0dff3ad59e60b73e7d09559b792a7d80d0efe22d8d04b902f` |
| `f280-t064-chromium-green` — промежуточный timeout | `5845c6e4ce38980f810d0ca034cb856f0a73c22c169ae690ea5c8b7bad9e5978` |
| `f280-t064-webkit-green` — промежуточный timeout | `32adf936124b8595274b331e7e4acb59840f966425b359d2f0b06062d1d336d9` |
| `f280-t064-chromium-final` — PASS 59 | `6abfd03b084737d8c090931bd6c6fdf647189926babc86207bf35f938f0ff08d` |
| `f280-t064-webkit-final` — PASS 20 | `1406d51b0fc07c223480cc3bd0aa453a7db7fbe7daae4bbf7d1fe8af3c25a499` |
| `payment-reaudit-full-green` — PASS 289 | `fa862f1ccbd2c12faec9267e9c111b2bf3adcd041642703d2c1d22aae6f87f45` |
| `f280-reaudit-sibling-green` — PASS 267 | `11a4aac3a27bd66097463cfecb6f392ec43cfc4d420beb515f55bb83fb6672f2` |
