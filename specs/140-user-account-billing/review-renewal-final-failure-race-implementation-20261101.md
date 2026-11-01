# F140/T048: независимая проверка исправления гонки ответа провайдера

Дата: 01.11.2026. **SCOPED IMPLEMENTATION PASS: P1=0, P2=0, HIGH=0, CRITICAL=0.**
Ограниченная сходимость6/6 подтверждена для исправления конкретной гонки,
после проверки итогового профиля и текущих source hashes.

Основа `49f046d8ba2de6f460ab42afdfd77e00c62ea925`, ветка
`codex/140-final-renewal-failure`, `active Spec Kit slice`, T048/#4903,
PR #7861 `discussion_r4434006876`. Область требований уже принята в
`review-renewal-final-failure-race-requirements-20261101.md`; новых решений нет.

Изменены только этот отчёт и reviewer-owned checklist. Код, spec/plan/tasks, чужие
материалы, Git/GitHub, БД, CI, приложение, почта/провайдер/деньги не менялись;
тесты и сборки рецензент не запускал. Новых агентов не запускал.

## Прочитанный diff и вывод по реализации

В продукте изменён только аргумент времени в canceled-ветви sender:
`now=_utc(now or datetime.now(UTC))` вместо `now=current`, плюс пояснение.
При `now=None` время берётся после POST, повторного workspace lock и refresh
subscription/operation/invoice, непосредственно перед сохранением отказа.
Решение о допустимости самой отправки всё ещё использует прежний `current`;
цены/окна/ключ/согласие перед POST не ослаблены. Явный `now` сохранён
для прежних вызовов и детерминированных проверок. Нового clock-helper,
финансовой проекции, службы, схемы или зависимости не добавлено.

Прочитаны общие `_enqueue_renewal_cutoff_notice`, record_renewal_decline,
обработка ответа sender, места вызовов webhook/reconciliation/worker.
Рабочий renewal worker вызывает sender без now. Webhook передаёт время
после получения subscription под lock; reconciliation вычисляет время после
provider GET и повторного чтения под lock. Их семантика не меняется.
Guard терминального исхода и обе связи snapshot/плательщик/период, active
personal Owner, обязательный provider_id для canceled/canceled, допустимость
UNKNOWN без номера и финансовая версия согласия сохранены.

Обновлено существующее испытание трёх настоящих planner/charge попыток,
вместо четырёх независимых новых систем подготовки. Варианты explicit/early
проверяют прежнюю раннюю классификацию, late — ответ после cutoff без другого
worker, late-cutoff-worker — сохранённый Free/UNKNOWN во время ожидания POST.
Clock заменяет только получение времени в проверяемом модуле; текущий state
не подставляется, вызовы planner/charge/реального cutoff не заменены.

`entered.clear()` и `release.clear()` выполняются перед **каждой** попыткой.
Третий synthetic POST ставит entered и ждёт release; тест ждёт entered,
в другом AsyncSession читает сохранённый processing/no provider_id,
исполняет cutoff и commit, затем подтверждает Free и всё ещё processing/no id.
Только после этого сдвигает наблюдаемое время за cutoff и снимает ожидание.
Это исключает обнаруженный ранее ложный эксперимент с оставленным set-event.
Ожидания ограничены wait_for; finally освобождает event и отменяет/дожидается
незавершённой задачи. Один AsyncSession не используется параллельно двумя
задачами. Новых sleep или обращения к настоящему провайдеру нет.

После ответа проверяются canceled/canceled, исходный paid_through,
consent/authority, полные исходные снимки grants/methods, повтор без второго
POST, разные ключи трёх разрешённых попыток. До cutoff остаётся attempt;
в поздних случаях ровно две прежние attempt, без третьей новой, и один
PAYMENT_FAILED через существующий предметный helper. UNKNOWN допускается
только в варианте с cutoff-worker и сохраняет свой event_id/pending/attempts0.
Повтор/следующий cutoff не создаёт второе итоговое событие. Точный payload,
получатель, канал, историческая дата МСК и безопасный маршрут проверяются
прежним `_assert_final_failure_notice`.

Разрешённый async transport по-прежнему ограничен конкретным MockTransport
и synthetic host; sync HTTP запрещён fixture. Настоящие валидаторы Settings
и три отдельные synthetic secret files сохранены. Доставка не запускается.
Тест не доказывает новую физическую PostgreSQL-связь или настоящую доставку.

## Причинные результаты

Самостоятельно прочитаны XML и журналы `race-red-held` и `race-green-held`.
RED-held:2 FAIL (late и late-cutoff-worker),2 PASS (explicit/early),0 skip/error.
Без parallel cutoff прежний код оставлял personal вместо Free; с cutoff
создавал третью attempt вместо итогового результата. GREEN-held:4 PASS,
59 deselected,0 FAIL/SKIP/ERROR,4.42s. Оба журнала фиксируют штатную очистку
одноразового контейнера. Это один профильный эксперимент, не сумма с общим.

Первый диагностический race-red/green с несброшенным release не принимается
как доказательство удержания. Первый race-profile с collection error также
не является исполненным профилем. Окончательный `race-profile-v2` независимо проверен ниже; результаты
диагностических ошибок не подставлены вместо этого прогона.

## Границы

Контрольный список полностью перечитан после записи:6 отмечены/0 открыты.
Новая ограниченная implementation приёмка относится только к исправлению
гонки и перечисленным текущим байтам, а не всей T048. Остальные T048/T068/#7524,58 общих открытых пунктов F140,
реальная доставка/магазин/деньги, Dev, выпуск и production не принимаются.
После локальной проверки нужны converge и три обязательных exact-SHA/base
PR checks с общим валидатором. Это ревью не заменяет защищённое слияние.


## Окончательный профиль, ID и ограниченная сходимость

Самостоятельно разобраны XML старого profile-fixed и нового race-profile-v2.
Новый итог: **476 PASS / 0 FAIL / 0 ERROR / 0 SKIP**, время XML178.999s,
журнала179.01s. Журнал подтверждает collection_count=476, result=pass и
штатное удаление одноразового контейнера. Два прежних предупреждения pytest
rewrite/fastapi-httpx остаются предупреждениями, не скрытыми ошибками.

Точное сравнение ID:472 совпали побайтно; один прежний ID цепочки трёх
отказов заменён четырьмя вариантами [explicit], [early], [late],
[late-cutoff-worker]. Таким образом прибавилось3 случая, а не потеряна
исходная проверка: explicit сохраняет её прежний явный now, early проверяет
рабочий default-clock до cutoff, два late воспроизводят новую границу.
Непредусмотренных удалений, лишних ID и дубликатов0. Все4 GREEN-held ID
входят в476; их не надо суммировать отдельно. Независимый расчёт совпал с
race-profile-comparison.json.

Текущие два source файла самостоятельно пересчитаны и точно совпали с
race-code-hashes.json. После прогона иной source здесь не принят.
Фрагмент changelog прочитан: он точно описывает обработку позднего ответа
и сохраняет ограничения остальных событий/доставки. Обновлённое дополнение validation о гонке прочитано: оно фиксирует
held RED/GREEN, итоговые476 и прежние диагностические ошибки раздельно.
Прежние473/source hashes в нём относятся к истории. Этот отчёт фиксирует
проверенные новые byte hashes и журналы самостоятельно.

Сходимость для исправления существующих требований:

| Пункт | Основание |
| --- | --- |
| CHK001 | Время фактического ответа после POST/lock; GREEN-held late без worker и late с commit cutoff; ранний и explicit варианты сохранены. |
| CHK002 | Binding, personal/Owner, оба снимка/period, invoice и provider guard не изменены; профиль сохранил прежние отрицательные случаи. |
| CHK003 | Финансовый guard и отсутствие восстановления согласия не изменены; исходные paid_through/grants/methods и consent/authority проверяются расширенной цепочкой. |
| CHK004 | Реальное удержание ответа, другая транзакция cutoff, повтор без POST/дубликатов, две прежние attempt и один final; rollback/конкурентные регрессии вошли в476. |
| CHK005 | Текст/дата/безопасный payload/маршрут не изменены; предметный _assert_final_failure_notice проверяет их и в поздних sender-вариантах. |
| CHK006 | Настоящие planner/charge/cutoff и PostgreSQL, новый сеанс, точные held RED/GREEN и весь профиль, без реального провайдера/почты. |

Покрытие6/6; CRITICAL/HIGH0; неподкреплённого нового поведения0.
Незавершённая обязательная работа до merge — новые PR SHA/base gates.
Остаток всей T048 уже отслеживается исходной задачей, не объявлен выполненным.

## Контрольные суммы итоговой проверки

```text
8ea7bc414bb455ae2e02015b5e0eb37a9d6ec3f91a14711a8ac4562e923c1040  apps/server/src/twobrain_rec_server/billing/renewal_charge.py
95e71d6b9cdb5c50341e67da3f1995351328c3c3bbffa5d426af9efdffb97513  apps/server/tests/integration/test_billing_renewal_planner_postgres.py
a0fea3026e819c45f67e465571a98f9ddac200da3b2550396dc9a20ae3aabab3  specs/140-user-account-billing/checklists/renewal-final-failure.md
74f08996cbb2c65c628bf571bff708293b76d498ea354cb44618cb66ecdbf2b0  specs/140-user-account-billing/review-renewal-final-failure-race-requirements-20261101.md
a7e92ef9ef54654a1447fb440de04404a845a52c08f6462dd56d7c2662f915a4  specs/140-user-account-billing/spec.md
f757949fdc17a113bf542c397d4605d24f0d04201ff1d6b879f0815beb55599c  specs/140-user-account-billing/plan.md
a3f36e98acdf3c3cb0fd26fcef1343d2b297ee9c62402a9074ca59d0c1f5d701  specs/140-user-account-billing/tasks.md
c498c51c6a1024428d2e87f6845ca48a612f2101e82b02f624d63b264afa8e6d  specs/140-user-account-billing/quickstart.md
8419499b5407d3d5aaf52a08084087523f444fe6fb36edb8cb9f39ca31ec66fe  /Users/yshishenya/Documents/Codex/2026-11-01/graf-f140-final-failure/race-red-held.log
da79203b7b2c6b076237dfa81f95b20bc7f0010f54cfc82eb3868215ee38427c  /Users/yshishenya/Documents/Codex/2026-11-01/graf-f140-final-failure/race-red-held.xml
e2cada20fb4ad815803d83ae6114c1ca2b73d9bc28ada8b72600055d7f13b6d1  /Users/yshishenya/Documents/Codex/2026-11-01/graf-f140-final-failure/race-green-held.log
2bd81812eb2d8ff138b6ffd6e03e0ee2abc53bf8897166f87cbedc253f986172  /Users/yshishenya/Documents/Codex/2026-11-01/graf-f140-final-failure/race-green-held.xml
bd8cb4beb3fccb8b62cc3b691b54b70782909a1e2ec0d01723506e156956d641  /Users/yshishenya/Documents/Codex/2026-11-01/graf-f140-final-failure/race-profile-v2.log
8d3c8233c8e6e03761dd4570c863e5ca2e25dff6225dfade25cd440f7002aefc  /Users/yshishenya/Documents/Codex/2026-11-01/graf-f140-final-failure/race-profile-v2.xml
7bade1bcdae3c41daca26b01f398bf35ab83a7f0a7e8b9c2dcacdba7dcd01867  /Users/yshishenya/Documents/Codex/2026-11-01/graf-f140-final-failure/race-code-hashes.json
6b8920ab4a1d4ab4c88ad6955a45cff5118ee6171c23d5f6e0fbd092ec2b1713  /Users/yshishenya/Documents/Codex/2026-11-01/graf-f140-final-failure/race-profile-comparison.json
```

SHA-256 прочитанного документального дополнения: `8fbc8d3a2b31f0f74bef619506cea30b3294ae083be56ee24b7062616328a1d3` — `specs/140-user-account-billing/validation-renewal-final-failure-20261101.md`.

SHA-256 прочитанного документального дополнения: `4bd35c0eb34d8caa3df3f965369876bbc42ed7a9fda6da1dfddfdefc97f958d3` — `changes/unreleased/F140.yaml`.
