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
**до** runtime правки. После baseline получен отдельный runtime-design addendum (ниже). Ранний
test-design preflight сам по себе этого допуска не давал.

Весь T112/T113, pool reset, отдельный raw driver.close/TLS teardown,
остальные commit/cleanup исходы, реальные endpoint/proof/render/ledger,
browser/native, restore, PR/CI/merge/выпуск, runtime/T0 остаются открытыми.
Ни визиты, ни регистрации, ни оплаты этим тестом не подтверждаются.


## Исправление раннего владения и новый локальный профиль

Независимый runtime-design addendum полностью прочитан до изменения кода;
SHA-256 `4952a0e9fe19f4bb48e87cb7e4203d8c9e9a030577c37e13a985ac59ddba9bf8`.
Он принял один дополнительный initialization marker того же lease5 и прежнего
owner registry, без отдельной фабрики/реестра. Текущий guard использует public
Pool.connect(insert=True), проверяет exact entry/DBAPI/native driver/task/context
до initialization. На checkout/checkin marker проверяется до generic pop.
До join прекращается только exact невыданный driver только что отменённой DB
task; после успешного join удаляется только metadata того же closed/done lease.
Обычная invalidate ветвь сохраняет in_use, исходная ошибка не превращается в
accepted, нет повторных SQL/close/rollback/commit или retry.

Причинные native4 стали **4 PASS /21 deselected /1 прежний warning**,
7.33s/runner10s/EXIT0; isolated_container_removed. В transparent initialize
теперь проверяется уже установленный runtime lease/оба ключа. Оба fault
возвращают полный unavailable<2s; до gate.set проверены закрытый driver,
исчезнувшие backend/locks, пустые owner/root/task/pool/relay. Normal controls
подтверждают прежний initialize и committed renewal. Чужой direct backend
сохранён; последующий checkout с новым driver/PID успешен.

Весь изменённый профиль **197 PASS /0 skips /1 прежний warning**,
47.93s/runner51s/terminal96024 EXIT0, isolated_container_removed/result pass.
Состав:164 unit,25 contract,8 прежних integration. Collection197/digest
`b2314f82ef8554b7858533c7aa0552305e2d03125d79014f8350e01c9f44b30a`.
Новые73 unit проверяют exact owner/generation/keys/entry/task/context,
not-in-use/cancelling/cancelled-set, done/closed cleanup и transition/reuse.
Они сохраняют противоречивые mappings без частичной очистки. Full197 включает
все прежние120; это новое исполнение изменённого общего профиля, не повтор
неизменного старого результата.

| Новый вход | SHA-256 |
| --- | --- |
| `api/product_analytics_guard.py` | `87af502348a246bbf2073fe53bfa09710533cc4c7d8e852bc84d2d0db0ead40f` |
| `unit/test_result_view_http_guard.py` | `6e7136c5688661abc1a34548576af87254835c7ff0fbad84509134e265c8a17a` |
| `contract/test_result_view_http_budget.py` | `45f937184fd0f3569ee385659fc3529d5af1a3acb8d8a5b12fd72fce7dfad2ac` |
| `/private/tmp/graf-t112-init-full-20261116.log` | `11bbdad7a11cd0f4784a5dec757a2b94c9bf61ee230d94329da67e35979b1679` |
| Native4 log | `6360e5cb090de5ac4ddc14c51cf7e2a15478c705618ba1d61fd58ac03bc39b4d` |

Ruff/diff-check PASS. До запуска свободно150693760KiB (>80ГБ), архивы не
копировались, изолированный контейнер удалён штатным runner. Reading restore
`/private/tmp/graf-t112-init-reading-20261116.json` фиксирует собственные
применимые разделы и18 неизменных input hashes; это указатель текущего
same-thread targeted restore по разрешению владельца, не новая квитанция
первого полного чтения исторического корпуса.

Implementation review ещё открыто. Существующий reviewer получил поручение
`/private/tmp/graf-t112-init-implementation-review-request-20261116.txt`;
live agents snapshot подтвердил running. Отдельно требуется проверить,
достаточно ли отказа мутации противоречивого marker для закрытого admission,
если current owner не содержит чужой lease. Текущие unit negatives доказывают
сохранность metadata, но сами по себе не доказывают отказ accepted во всех
таких случаях. До заключения не выдавать197 за полную приёмку этой ветви.

Все прежние ограничения полного T112/T113/HTTP/restore/runtime/T0 сохраняются.


## I1 — сохранение отказа при противоречивом владении

Независимое implementation review первого исправления найдено и прочитано
полностью: [t112-init-review-20261116.md](t112-init-review-20261116.md),
SHA-256 `cbc8d545b3ed6b51f44872a431bdf42ce9d6804a3f0e4ffc707f491b80b55473`.
Результат P1=0/P2=1: rejected registration при отсутствующем current-owner
entry сохраняла foreign metadata, но могла пропустить accepted после обычной
Session. Реальное SQLite/Session воспроизведение reviewer подтверждает этот
исход; дополнительная собственная unit-like диагностика имеет тот же результат.
Это новый дефект I1, не ложный PASS197 и не доказательство сбоя рабочего сервера.

До исправления добавлены10 проверок. Законченный RED:7 FAIL/3 PASS,
164 deselected/1 прежний warning,0.40s/terminal66212 EXIT1. В четырёх отказах
настоящие SQLite Session/Pool, SELECT1/commit и оба HTTP aliases выпускали
accepted при ожидаемом unavailable. Три callback отказа не сохраняли failed;
три owner=None контроля прошли. Артефакт:
`/private/tmp/graf-t112-init-i1-red-20261116.log`, SHA-256
`4cb215341441402d829748fd9ac729559a866415b0e3a79a98ca9aeac48a235c`.

Следуя минимальному проекту reviewer, существующий owner получил failed bool.
Ранний connect/checkout/checkin при отказе точного сопоставления отмечают
только current owner; чужие mappings/driver не меняются. Конечный guard после
join проверяет failed даже при пустых registry. Поздний обычный checkout,
успешный commit и metadata cleanup не сбрасывают отказ. Owner=None сохраняет
обычный путь. Исключения callbacks, pool invalidation/reconnect/retry не вводились;
возможный commit не объявляется rollback и не повторяется автоматически.

Focused initialization units:83 PASS/91 deselected/1 warning,0.09s/EXIT0.
Новый полный изменённый профиль: **207 PASS/0 skips/1 прежний warning**,
49.10s/runner53s/terminal48899 EXIT0; isolated_container_removed/result pass.
Состав174 unit+25 contract+8 integration. Collection207/digest
`4eda745fd0666368aca28fd7091234fa7030208e373e2f2192eaeb0e61c53c67`.
Новое конечное HTTP поведение подтверждено для checkout/checkin с absent
current mapping на обоих aliases, sticky отказом после второй обычной Session,
неизменным foreign registry/driver и отсутствием новых tasks. Native init
faults остаются <2s (около1.64s), все прежние регрессии197 вошли в новый запуск.

| Окончательный вход I1 | SHA-256 |
| --- | --- |
| Guard | `b22a95714a2e6d94ec1645bad0475e1b99b518386caa7ebab785fb0d42dd0088` |
| Unit | `7ee3f98d9fdffec701b2bec5a38ddedd1b960f7345ef1b42ab508e9f86c92ee2` |
| Contract (без изменений после197) | `45f937184fd0f3569ee385659fc3529d5af1a3acb8d8a5b12fd72fce7dfad2ac` |
| Full207 log | `d59d798365d2d097c149ae42e1669300d0f8bdf995f11063ebb5b87db3a30ec9` |
| Focused83 log | `237c1592e8ba19617ff3f8de14aadc894d87e82527c11b6fd9273bfef2279285` |

Ruff/diff-check PASS. Повторная независимая приёмка checkpoint78cd1ea85
завершена: I1 устранена, P1=0/P2=0 в пределах initialization extension.
Основной агент прочитал весь addendum и сверил неизменные код/тесты/log207;
новый SHA-256 отчёта `646633c73276bfb6c91db6ebde5be4c7b049cc4722fbd0f05f6d50b0c88c01db`.
Тесты повторно не запускались. Основные checklist и T112/T113 остаются прежними.
Полные HTTP/issuance/ledger/browser/native/rawclose/TLS/poolreset/прочие commit,
restore/runtime/T0 и коммерческие результаты не приняты.
