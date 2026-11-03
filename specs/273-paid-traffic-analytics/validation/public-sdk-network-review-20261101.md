# Независимое before-code ревью изолированного SDK профиля F273/T106

Дата01.11.2026. Проверяющий:`/root/public_counter_readiness_review`.
Копия:`/Users/yshishenya/.codex/worktrees/growth-protocol-result/crisp`.
Ветка:`codex/f273-public-sdk-proof-20261101`.
В поручении HEAD3aa38ce2568e5bb89c8a5a763c19ae51d5f82d29; при непосредственном
чтении git rev-parse и active pointer уже согласованно показывают
`94c40e0b78da2e222c0318ded5d89f0c8174f012`. Review привязан к фактически
прочитанным hashes ниже; причиной изменения HEAD проверяющий не спекулирует.
Lane:active Spec Kit slice/test-only privacy proof.

## Решение

**PASS требований и минимального плана выбранного тестового профиля:
5 `[x]`/0 `[ ]`, blockers/P1/P2/HIGH0.** Код ещё не реализован/не принят.
Допускается только новый focused CLI и минимальный reuse modal helpers.
Продуктовый контроллер/flags/revision/scope не меняются.

## Матрица checklist

| Пункт | Итог | Прямое основание |
| --- | --- | --- |
| CHK001 | PASS | Spec/plan/quickstart называют настоящий официальный tag.js как явный local file+SHA, настоящий GRAF controller и CookieConsent. Обе поверхности / и /download, analytics-only, same/cross-tab. До отзыва обязательны настоящий instance и watch attempt>0; замена SDK либо нулевая активность не дают PASS. |
| CHK002 | PASS | Новый непостоянный context; перехват HTTP/WS до SDK, только fulfill/abort/close, без continue/fetch/forwarding. Учебный counter99999999, никакого live account/counter/goal. Неизвестный SDK input — error без fallback/download/SKIP. Отчёт ограничен count/types/phase, без query/cookies/body/pseudonyms. |
| CHK003 | PASS | Реальный library choice и сохранение/события контроллера; второй page имеет тот же origin/storage и настоящую библиотеку/контроллер. Граница отзыва фиксируется до/при выборе, затем отсутствие instance и0 новых optional HTTP/WS/relay attempts20s при кликах/scroll/focus/visibility. Любая попытка или unknown — FAIL. |
| CHK004 | PASS | Control в собственной временной копии подавляет только destruct после положительного контроля и должен FAIL на сохранившемся instance. Не утверждает доказанную autonomous send. Копия удаляется finally; JS/исходный тест не мутируются. Прежний modal/Node/server guard suite, независимое review/converge/exactPR сохраняются. |
| CHK005 | PASS | Полностью отделены finite20s/analytics-only/local backend от реального backend/settings/replay/global serverpermission/individual revoke/runtime/T0/всегоT106. Внешний HOLD сохранён; нет рабочего включения, нового provider/config/service, неявной CI сети. |

## Невакуозность и достаточность ограниченного доказательства

Тест обязан сначала подтвердить, что настоящий SDK действительно выполнял
разрешённую работу с настоящим контроллером: instance существует и watch
попытка перехвачена. Затем тот же сценарий сравнивает реальные browser
сетевые попытки до/после реального CookieConsent выбора. Успешный intercept
или abort не означает отсутствия попытки: учитывать нужно сам request/WS,
включая first-party relay, даже если отправка не покинула браузерную среду.
Проверка не сводится к GRAF flags или наличию вызова destruct.

Отзыв одной вкладки должен прекращать instance и optional attempts всех
участвующих страниц сценария. В cross-tab path второй контроллер действительно
читает общий origin и library storage, а не вручную вызывается callback в
первой. План задаёт реальные страницы и настоящие события, что достаточно
для исполнения этого критерия без нового runtime механизма.

Negative control — проверка способности теста заметить оставшийся instance.
Он не обещает автономного HTTP при подавленном destruct: disable-флаг может
уже прекратить такую сеть. Поэтому ожидаемая ошибка control и её причина
должны быть именно instance-still-present, а не произвольный exception,
недостающий SDK или неподтверждённый positive контроль.

Двадцать секунд — конечный наблюдаемый интервал, а не разрешённая задержка
отзыва и не универсальное доказательство любого будущего момента. Локальный
watch JSON делает проверку воспроизводимой и изолированной, но не охватывает
поведение настоящих server settings/replies. Replay не выбирается и остаётся
неисследованным. Этот срез улучшает доказательство конкретного runtime path,
сохраняя прежний HOLD внешнего включения.

## Reuse и отсутствие продуктовых изменений

Modal harness прочитан полностью: readConfig использует существующий
synthetic Python fixture; loadController загружает vendored CookieConsent
и настоящий analytics.js, меняя только hideFromBots в library run.
Экспорт именно этих helpers и require.main guard — минимальная модификация;
самостоятельный прежний main и assertions должны сохраниться. Новый CLI
может задать только учебную конфигурацию/страницу и сеть, без изменения
содержимого SDK или исходного контроллера. Официальный file не коммитится.

Текущие JS canUseAnalytics/owned queue/disableOptionalProviders/destruct
и startup boundaries перечитаны; hash контроллера совпадает с собственным
принятым local-browser review. Проверка проектирует фактическую библиотеку,
не добавляет новый источник идентичности, broker или provider route.

## Исследовательская проба и пределы чтения

Research report прочитан целиком. Он сообщает SHA
72dadb1a319174bf611e44d0a70ed9569fb3c72fdd685223ac6091fc3ef0db9e,
3prewatch/0post за20s с local replies, без ГРАФ/CookieConsent/второй вкладки.
Эта проба не заменяет новый четырёхсценарный профиль и не является его GREEN.
Источник/time/status/hash обозначены metadata-only. Проверяющий файл SDK,
исследовательский script/result и удалённый источник не исполнял/не скачивал;
приведённые результаты остаются evidence предоставленного research report.
Ошибка первого driver вывода и принятая повторная сводка не скрыты.

Все новые sections spec/plan/tasks/quickstart и5checklist пунктов прочитаны
целиком. Scoped исключение F273 применено к неизменным constitution/PRD/
status/product-gates:4/4 SHA совпали с собственным прежним чтением.
Никаких новых тестов/сети/CI/Git/GitHub/runtime/внешних отправок проверяющий
не выполнял. Только чтение code/context/status/хешей; изменения ограничены
этим отчётом и новым checklist, чужие изменения сохранены.
После отметок checklist перечитан:5checked/0unchecked. Scoped analyze/sync
existing T106/#7696 следуют перед кодом, actual implementation review — после.

## Хеши фактически прочитанного состояния

- Controller:`c04612cb03eee01b893c4b8cc2b680e6d8e052854c2cfba10bffa004c51eee14`.
- Modal harness:`d670744d3b163a277ecf647f7a0aedb5cdd8ceaadd019b78407a8cc2abc10f3c`.
- Spec:`1587c87eb6945bda0aa19b85d23ba2faa80d32459872587eb3483d778f3b8005`.
- Plan:`99a7ca5a4266079079ce14e0b2dbf4d92ad5e231c3af2bf8161ae5f77d73ddf0`.
- Tasks:`57ed20af833160417493f9b8cbbebf4f97e5ad2bde3d6b1d2febe55cfc9776e0`.
- Quickstart:`5cb797f79271d9c8ff6f8a13c9b85a3b0a84632254b7afff961afc1a68b54c39`.
- Research report:`39f9ba71b4bd016b20f5e9b7be916de9a63481fd9d19f5829ff5a9a6877b4574`.
- Constitution:`7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8`.
- PRD:`0f3ccfcfa60062bb0aae6802eeb0012056a635a30cb9f46f54d1992d0b4f57c2`.
- Status:`25b7f383be47c7160da8e852006ff82019f30a5f9c371fc30baa79238649cd16`.
- Product gates:`9f7072c879490d250053cb7397ad6b9b68fdcde17bdf9367ed874a41e450b5f5`.


## Повторное requirements review учебного provider_smoke — 01.11.2026

**PASS узкого уточнения plan/quickstart; P1/P2/HIGH0.** Checklist целиком
перечитан: **5 `[x]`/0 `[ ]`**. Это не code review/приёмка чернового CLI.

Непосредственно прочитаны обновлённые полные SDK sections plan/quickstart
и весь черновой public-analytics-sdk-network.test.cjs. Существующий fixture
возвращает render_only, а текущий контроллер intentionally не вставляет tag.js
в этом режиме. Поэтому первый отказ положительного instance контроля
объясним указанным prerequisite и сохраняется как честный FAIL, не результат
прекращения после отзыва и не деградация SDK. Actual run проверяющим не
повторялся, его failed итог сообщён владельцем.

Уточнение меняет только переданный локальной странице synthetic config:
validation_mode=provider_smoke вместе с прежним counter99999999. Это уже
существующий режим контроллера, который позволяет фактическую загрузку
SDK и тем самым делает positive instance/watch контроль исполнимым.
Не меняются продуктовые Settings/flags/редакция/scope или содержание SDK.
Все interception handlers по требованиям ставятся до страницы/контроллера/
SDK; mode сам по себе не разрешает forwarding и не снимает network guards.

В прочитанном черновике provider_smoke ещё не добавлен, как прямо указано
в поручении. Его implementation и ограничения перехвата/логирования/negative
control остаются предметом будущего независимого code review. Наличие
draft source не выдано за PASS. Предыдущее требование «только counter override»
замещается этим явно принятым уточнением для учебной конфигурации.

Finite20s/analytics-only/local replies и все external/backend/replay/global/
individual/runtime/T0/fullT106 HOLD сохранены. Тесты/сеть/Git/GitHub/runtime
проверяющим не запускались. Изменены только собственный review и checklist.

Хеши прочитанного уточнения:

- Plan:`0e7626260ddd15e98bf1543cb16578c18d41abbff32350d20bc79dfa7fac3692`.
- Quickstart:`821f0942af96a1bc49fb229e54a1cca5bafe12d3d452539470244a43046cecd3`.
- Draft CLI (НЕ принят):`bfc4f5b881362f04350ae2bb8d243b8309ff786f0f3ae93e1904c45a084e09c7`.


## Повторный before-code gate: идентичность SDK очереди — 01.11.2026

**PASS требований минимального исправления общей cleanup; P1/P2/HIGH0.**
Checklist целиком перечитан: **5 `[x]`/0 `[ ]`**. Прежний test-only объём
явно расширен ровно на disableYandexCounter и причинную Node регрессию,
как теперь определено spec/plan/tasks/quickstart. Это не скрытое разрешение
других product/runtime изменений и не PASS ещё не изменённого кода.

### Непосредственная проверка root cause

Прочитан локальный настоящий SDK с SHA256
72dadb1a319174bf611e44d0a70ed9569fb3c72fdd685223ac6091fc3ef0db9e.
В Bi(a,b,...) прежний b.push сохраняется в f, затем тому же b присваивается
новая push function; она использует f.apply(b,arguments) и вызывает e.trigger.
Unsubscribe восстанавливает b.push=f. В конце SDK берётся c=J(b,"a") у
window.ym и вызывается Bi(a,c,...,!0), подписывая Ht(a) именно на этот массив.
Таким образом подписчик связан с идентичностью исходного ym.a, а не со
свойством .a у функции, перечитываемым при каждой последующей замене.

Текущий prepareYandexQueue GRAF при собственном stub пишет очередные
arguments в текущий window.ym.a через .push. Текущий disableYandexCounter
создаёт новый Array через filter и присваивает его ownedYandexQueue.a;
новый массив не получает SDK custom push. Последующий ym(id,destruct)
поэтому может попасть в новую необрабатываемую очередь. Этот механизм
подтверждён чтением обоих исходников, без тестового исполнения проверяющим.
Интегрированный FAIL и отдельное успешное прямое instance.destruct сообщены
владельцем; здесь они не выдаются за самостоятельно воспроизведённые пробы.
Product JS hash всё ещё c04612cb… — до данного before-code PASS не изменён.

### Достаточность минимального исправления

Обратный проход по исходному ownedYandexQueue.a с splice сохраняет Array
identity и тот же custom push; удаление с конца не пропускает соседние
команды своего ID и сохраняет порядок/байты чужих commands. Такое исправление
не меняет SDK/ym, не требует прямого instance.destruct в продукте, нового
API/таймера/реестра. Прежний disable flag, guards/idempotence/destruct try/catch
сохраняются. Обе точки вызова функции в disableOptionalProviders — public
и product ID — найдены и прочитаны; общая cleanup должна работать для обоих.

Node RED/GREEN должен проверить реальные ссылки array/push до/после cleanup,
обработку destruct через custom push и сохранение чужих команд. Только count
вызова внешней ym недостаточен: новый FAIL как раз показал вызванный, но
необработанный destruct. Настоящий SDK профиль затем выполняется без обёртки
ym и без прямого instance.destruct. Negative control сохраняет прежнюю
узкую интерпретацию оставшегося instance, не автономной отправки.

Spec/plan/tasks/quickstart новые уточнения прочитаны целиком. Начальный
большой вывод был усечён; tasks/quickstart и SDK final subscription отдельно
перечитаны без усечения. Прежние finite20s/analytics-only/local backend/
replay/globalpermission/individualrevoke/runtime/T0/fullT106 ограничения и
external HOLD сохранены. Прежние code PASS не выдаются за доказательство
успешного настоящего SDK — найденный интеграцией дефект отражён прямо.

Тесты/сеть/Git/GitHub/runtime/release проверяющим не запускались.
Изменены только собственные review/checklist, чужие изменения сохранены.
После отметок checklist перечитан:5checked/0open. После scoped analyze/sync
возможна только описанная правка; code review следует после причинного GREEN.

Хеши нового требования и неизменного кода:

- Spec:`855478a14da7ef4c958488bfa0d0ee3f14d9e991302cbf882c40bcec6229bbfe`.
- Plan:`fadc0a06fe6a4eec94fcc9a08a0ac3c3bbe5acd774cdbb765f7556a4216438c6`.
- Tasks:`ed142646e3fb6f93ca3270813c8dd4649f572eac7a18dd286c9d6a44c3d2e7b7`.
- Quickstart:`c5066bd67d02ed108d843550702ceb2ee622d40d9a76d3ceb4758e34b253548f`.
- Controller unchanged:`c04612cb03eee01b893c4b8cc2b680e6d8e052854c2cfba10bffa004c51eee14`.
- Local SDK:`72dadb1a319174bf611e44d0a70ed9569fb3c72fdd685223ac6091fc3ef0db9e`.


## Первое implementation review SDK профиля/cleanup — 01.11.2026

**HOLD общего implementation PASS:1 открытое P2; P1/HIGH0.**
Требования checklist остаются качественно принятыми: после полного
перечитывания **5 `[x]`/0 `[ ]`**. Отметки не подменяют текущий code HOLD.

### Обязательное исправление: точность negative control

В public-analytics-sdk-network.test.cjs:90–91 catch преобразует *любое*
исключение waitForFunction в instance-still-present. Закрытая/упавшая страница
либо иная ошибка ожидания тоже дают ровно ожидаемый отрицательным control
маркер. Поэтому reported exact marker сам по себе не доказывает сохранившийся
instance — это прямо относится к ранее принятой границе CHK004: не принимать
произвольную ошибку за причинный контроль.

Минимальная правка: только TimeoutError кандидата перепроверить отдельным
page.evaluate(Boolean(window.yaCounter99999999)); выдавать instance-still-present
только при true. Другие ошибки, невозможность чтения или false instance
должны оставаться собственным/неизвестным FAIL, который control не принимает.
Новый runtime механизм и изменение SDK не нужны. После изменения отдельно
повторить отрицательный control и relevant профиль; остальные принятые
положительные результаты ниже не переписываются. Код проверяющим не менялся.

### Остальная проверенная реализация

Реальный product diff ограничен reverse splice в ownedYandexQueue.a.
Исходный массив/custom push сохраняются, удаление собственного ID выполняется
с конца, чужие команды и порядок не меняются; guards/disable flag/destruct
try/catch и callers сохранены. Node test добавляет array/push identity,
обработку destruct через custom push и preservation other counter. RED
падает на array identity, GREEN18 именованных сценариев. Минимальная root
cleanup соответствует отдельно принятому уточнению.

Modal harness изменён только exports readConfig/loadController и
require.main guard; прежний самостоятельный main/assertions сохранены.
Новый CLI прочитан целиком: explicit absolute local SDK file+64hex/hash
проверяется до browser import/launch; downloads/fallback/SKIP нет.
Новый context на сценарий с serviceWorkers:block, context.routeHTTP/WS
установлены до page/SDK; HTTP только local fulfill либо abort, WS close
без connect/forward. Unknown requests тоже учитываются и abort.
В config только учебные counter/provider_smoke; настоящий SDK/controller/
CookieConsent, analytics-only. Продуктовые Settings/flags/revision/scope
не расширены. SDK bytes не изменяются, в accepted CLI нет прямого
instance.destruct или подмены ym.

Четыре цикла pagePath×same/cross-tab используют настоящий shared origin;
обе страницы cross-tab должны иметь instance до отказа. Positive watch>0
обязателен. Phase revoked ставится до real library choice, все optional
HTTP/WS/relay после этой границы учитываются на уровне context, включая
abort. Fixture navigation обслуживается отдельно. После исчезновения
instance проверяются saved categories, click/wheel и synthetic focus/resize/
visibility events, затем finite20s. Это не утверждение настоящего background/
BFCache lifecycle или любого будущего момента.

### Прочитанные результаты и границы

Integrated-result:4/4PASS, watch3/6/3/6,0after20s. Это положительные конечные
наблюдения с local replies. Negative-result содержит лишь итоговую строку
expected_failure=instance-still-present; separate temporary driver/source
не сохранён среди предъявленных файлов, описание injection/finally принято
как отчёт владельца, не самостоятельно просмотренный diff временной копии.
Даже если reported run действительно оставил instance, текущая catch ветка
пока позволяет принять и другой сбой, что требует правки выше.

Regression журнал:67passed/0skips11.21s, настоящий modal присутствует,
PostgreSQL runner cleanup isolated_container_removed. Node RED/GREEN,
integrated/negative сводки и validation report прочитаны. Process/governance/
fragment/diff PASS сообщены владельцем; самостоятельно проверки не запускались.
Исходные scopes и новые spec/plan/tasks/quickstart/fragment прочитаны в
затронутых sections. Quickstart заменил wildcard browser CLI двумя прежними
explicit harness запусками; ручной SDK CLI требует явный input и не
подключается к CI network. Это соответствует принятой ручной полосе.

Тесты/сеть/Git/GitHub/runtime/release проверяющим не выполнялись, изменены
только собственный report/checklist. Все чужие изменения сохранены.
Scoped converge пока HOLD по одному P2. FullT106/replay/realbackend/global/
individual/runtime/T0/external включение по-прежнему не принимаются.

Хеши проверенного первого состояния реализации:

- Controller:`2d05b53cd6087cfb80258687bc798e99d910bfde6249cadc4045ac444c08c0c1`.
- SDK CLI:`9ae9930fba16221a4b81be29fe19fa583394c18f06d64bc9d857db2aef0a9efc`.
- Node harness:`4af9a930f13b72b822dc4f4e56599c23455d719eacb04666ac8afe7b91801ac4`.
- Modal harness:`dcd4e5b58fa4eca160b63d57be3fce9f12cfe2a01ed610771fb081c3ffe46b3f`.
- Integrated result:`9f84a5bb3cd72a3051e0c44b39a6c30dca57c0946b1a3d05cf2074cc7f92f1ae`.
- Negative result:`f88b5791bd797d23da9e7f594df9b771df6f85d0fd5ee4e389c365ce05976261`.
- Node RED:`1a7177a89ab5dc73f5a99deebcbb02d55bdb33d327c29c614078970cce522e9e`.
- Node GREEN:`50fe365f62e15c4c7f5cb8636098c9dbd3ab5ccf23d419aeb6f219181c869ef3`.
- Regression:`e91394a43d4236f0a05862d56faecb7faea988377e563bd39d593e9dea7d3c13`.

## Повторное implementation review и scoped converge — 01.11.2026

**PASS ограниченного SDK профиля и общей cleanup: открытых P1/P2/HIGH — 0/0/0.**
Замечание P2 первого ревью устранено; его исторический HOLD выше сохранён.
Checklist требований повторно прочитан: **5 `[x]` / 0 `[ ]`**. Это отдельные
итоги проверки требований и текущей реализации, а не принятие всей T106.

Исправленный CLI прочитан целиком. В catch теперь проверяется именно
`error.name === 'TimeoutError'`, затем отдельное успешное чтение
`Boolean(window.yaCounter99999999)`. Только true приводит к
`instance-still-present`. Иная ошибка ожидания, false instance либо ошибка
самого чтения не получают этот ожидаемый маркер. Узкая правка устраняет
причину P2 и не меняет обработку сетевых попыток, положительный контроль,
границу отказа или длительность наблюдения.

Свежие integrated-result.txt и negative-result.txt прочитаны. Четыре
обычных сценария снова PASS: `/` и `/download`, отказ в той же и другой
вкладке; watch до отказа 3/6/3/6, после отказа 0 попыток за 20 секунд.
Negative summary подтверждает точную ожидаемую ошибку оставшегося instance;
дополнительный closed-page summary подтверждает отсутствие ложного маркера
при закрытии страницы. Дополнительно полностью прочитан предоставленный
`/tmp/graf-sdk-negative-run.cjs`: он читает текущий CLI, проверяет единственность
точки вставки, создаёт собственную копию с `flag: 'wx'` и подавляет только
destruct в этой копии после положительного контроля. Для ожидаемой ошибки
требует exit1, точное stderr `instance-still-present` и пустой stdout.
Затем другая копия закрывает страницу после отказа; driver требует exit1,
ошибку с `closed` и отсутствие точного instance marker. Временный файл
удаляется в finally; исходник и SDK не записываются. Это независимое чтение
механизма двух controls, а не самостоятельное повторение их исполнения;
связь предъявленной сводки с запуском сообщил владелец. Исправление guard
также независимо проверено по исходнику. При чтении файлов обнаружено
0 `.sdk-negative-*.cjs` рядом с harness; SHA256 прочитанного driver:
`d9eebb2e57de81ae656d0e5ce28ae58b74122bd30ea94a5cbee7285a332a6c6d`.

Повторно прочитан diff product JS и Node/modal harness. Их хеши совпадают
с первым implementation review: reverse splice сохраняет исходные массив
и SDK push, прежние callers/guards/destruct остаются; Node проверяет
identity, обработку destruct и чужую команду; modal exports/guard сохраняют
самостоятельный запуск. Регрессионный журнал имеет прежний хеш, поэтому
результат 67 passed/0 skips относится к неизменным затронутым product/Node/
modal исходникам; это не объявляется новым исполнением регрессии.

В пределах согласованного изменения дополнительных непокрытых требований
и замечаний P1/P2/HIGH не найдено. Scoped converge PASS не принимает
настоящий backend/settings/readback, replay, global server permission,
индивидуальный server revoke, любое будущее поведение SDK, runtime,
измерение/T0, всю T106/#7696 или цель трафика/продаж. Внешнее включение
по-прежнему **HOLD**. Exact PR/base checks и выпуск проверяются отдельно.

Проверяющий не запускал тесты, сеть, Git/GitHub mutations, runtime или
release. Изменены только собственные checklist и этот review report;
чужие изменения сохранены.

Хеши текущего принятого состояния:

- SDK CLI:`8e42c8d02b09e1e20485f6e119c2f01c030f5ee6a50f2b498e09d9417691571b`.
- Controller:`2d05b53cd6087cfb80258687bc798e99d910bfde6249cadc4045ac444c08c0c1`.
- Node harness:`4af9a930f13b72b822dc4f4e56599c23455d719eacb04666ac8afe7b91801ac4`.
- Modal harness:`dcd4e5b58fa4eca160b63d57be3fce9f12cfe2a01ed610771fb081c3ffe46b3f`.
- SDK bytes:`72dadb1a319174bf611e44d0a70ed9569fb3c72fdd685223ac6091fc3ef0db9e`.
- Integrated result:`9f84a5bb3cd72a3051e0c44b39a6c30dca57c0946b1a3d05cf2074cc7f92f1ae`.
- Negative/closed-page summary:`3cb98b337d367c9190335405c5bd5189fbff28c636d1bda15e17b3cc89761fa4`.
- Regression:`e91394a43d4236f0a05862d56faecb7faea988377e563bd39d593e9dea7d3c13`.
