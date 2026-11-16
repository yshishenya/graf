# T112 — исходный отказ инициализации нового соединения

16.11.2026. Продолжение F273/T112, полоса `high-risk-product`.
Основа: `fb221efc9c0f54480cfc2b1cf50a2fd01fd1fdc4`.
Изменены только тесты и доказательства; runtime guard побайтно прежний.
Рабочий сбор выключен. Контент и вёрстка сайта не меняются.

## Допуск к тестам

Независимый [проектный разбор](t112-init-preflight-20261116.md) до тестового
кода согласовал четыре сценария: auth/renewal × обычная сеть/сетевая задержка.
P1=0/P2=0 в области проекта тестов, checklist124/0 без переотметок.
Основной агент прочитал весь отчёт, хеш совпал:
`453917ea63eae0329ead4c07fca0b4000895c25521e93df6f4c27cba0152b5c7`.
Это не допуск runtime исправления.

## Новый причинный результат

Seed/auth данные создаются прежним direct engine. Request engine холодный,
pool_pre_ping=True, без прогрева. В auth он используется сразу, в renewal
штатная авторизация заканчивается через direct engine, а синтетический
before_response переключает только тестовый sessionmaker для renewal.
Реальные auth/tenant/CSRF, native connect, codec setup, initialize,
rollback/close не подменены.

Ранний public connect(insert=True) подтверждает точные DBAPI/entry/driver,
PID, request owner/root task и отсутствие checkout. Он одноразово закрывает
только server→client response gate, без SQL/cancel/закрытия ресурса.
Прозрачный маркер public dialect.initialize вызывает сохранённый оригинал
ровно один раз, отдельно отмечает entry/normal return/finally. Независимый
observer с пустым Context подтверждает существующую initialization transaction
на том же PID, до завершения запроса. Случай до marker не выдаётся за init RED.

Законченный профиль: **2 normal PASS, 2 network fault FAIL, 21 deselected,
1 прежний fixture warning; pytest8.34s, runner12s, terminal18160 EXIT1,
isolated_container_removed.** Collection_count4/digest
`cc2462890c57737cbaadb1d2c95f0dbded4aef46344a6a4a787cc478d6d74359`.

Оба fault подтверждают завершённый native DBAPI connect, вход в настоящий
dialect.initialize и живую transaction через независимый observer. После
этого HTTPX обнаруживает отсутствие законченного ASGI-ответа около2.05s.
Это новый причинный дефект общего бюджета. Оба контроля проходят normal
initialize/completion/checkout, committed renewal и нулевой milestone ledger.
Foreign backend отдельного direct engine сохраняет PID/SELECT1; это не
испытание соседа того же ещё не инициализированного pool.

Поздние fault assertions закрытого driver, пустоты ресурсов/metadata,
исчезновения backend/locks и нового checkout после ответа ещё не достигнуты.
Они не объявляются PASS из успешной очистки стенда. Finally открывает gate
и завершает только синтетический target; runner удалил изолированный контейнер.
Watchdog3s не считается выполнением продуктового бюджета2s.

| Вход | SHA-256 |
| --- | --- |
| Неизменный `api/product_analytics_guard.py` | `4a20f7efbda819e774410b3907ac14c659d3e82b50dcf6b730ca506fd89c4509` |
| Новый `contract/test_result_view_http_budget.py` | `35250db3f0995ff13abad7f15912bb3a8318acbd898f575c92dd13f15861f0e0` |
| `/private/tmp/graf-t112-init-baseline-20261116.log` | `c5466a4e03a0be5deae7420cc325bebb197686558827dd356fa915f380c4b60b` |

Ruff и git diff --check прошли. Прежний успешный120 не повторялся и не
выдаётся за новое initialization evidence. Перед тестом свободно151772088KiB,
выше80ГБ; архивы/зависимости не копировались.

## Следующий инженерный шаг и ограничения

Установленный SQLAlchemy2.0.51 создаёт DBAPI до connect listeners; штатные
on_connect/initialize/finally rollback идут до checkout. Поэтому прежний
lease checkout не покрывает эту раннюю стадию. Простой отказ от проверки
entry.in_use в прежнем invalidate callback не является допустимым решением:
он убрал бы доказательство владения и не гарантировал бы вызов callback
при отказе конструктора entry.

Подготовлен отдельный минимальный public проект ранней connect-event связи
с прежним request owner и точным поколением DBAPI/driver, затем ограниченного
завершения только этого соединения. Требуется независимый проектный допуск
**до** runtime правки. После baseline его успешная отправка reviewer и новое
заключение ещё не подтверждены; подготовленный текст не является живым
ожиданием. Ранний test-design preflight не заменяет этот допуск.

Весь T112/T113, pool reset, отдельный raw driver.close/TLS teardown,
остальные commit/cleanup исходы, реальные endpoint/proof/render/ledger,
browser/native, restore, PR/CI/merge/выпуск, runtime/T0 остаются открытыми.
Ни визиты, ни регистрации, ни оплаты этим тестом не подтверждаются.
