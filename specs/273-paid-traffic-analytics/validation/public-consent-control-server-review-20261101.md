# T106 — промежуточное независимое ревью серверного контроля согласия

Дата: 01.11.2026. Reviewer: `/root/public_counter_readiness_review`.
Worktree: `/Users/yshishenya/.codex/worktrees/growth-protocol-result/crisp`.
Ветка по поручению: `codex/f273-public-permission-20261101`, baseline
`c6f42e8c7dec50ba769216feab4a80b70b50959a`.

**Первый промежуточный проход — HOLD: P1 1, P2 1.** Текущий результат
повторной проверки записан в завершающем разделе. Это незавершённая реализация;
браузер, lifecycle/restore, реальные роли и полный causal профиль ещё впереди.
Пройденный requirements checklist6/0 не изменяется и не означает code PASS.

Прочитаны новые public/consent.py, control/relay routes в public/web.py,
normalize/deliver в public/analytics.py, db/models/public_consent.py,
tenant_context.py и migration0108; существующие PostHog wrapper,
router async transport, provider secret reader; текущий договор,
tasks/analysis и растущий test_public_consent_control.py. Файлы основной
реализации меняются параллельно: финальные хеши ниже привязывают именно
прочитанный снимок. Тесты reviewer не запускал; сообщение4PASS не
переобъявляется собственным или окончательным доказательством.

## S1 — P1: после начала передачи неизвестный/успешный исход превращается в choice_blocked

Места: `public/consent.py::send_consented_event`, заключительный
`except Exception: return blocked` (около строк174–175);
`public/analytics.py::deliver_public_analytics_event` (около1247–1263).

Общий exception handler не различает ошибку до сети и после неё. В частности:

1. Guarded transport вошёл в HTTP; получатель мог принять событие.
2. Общий timeout/отмена с последующим исключением, ошибка read/close/commit
   после завершения transport или иной поздний сбой выходит из locked_choice.
3. Возвращается `status=choice_blocked, delivered=false, retryable=false`,
   хотя отказ до отправки не доказан. Если sender уже вернул delivered=true,
   последующий commit error тоже теряет подтверждённый HTTP результат.

Другой путь: PostHog wrapper превращает TimeoutError/OSError в network_error;
httpx exceptions проходят в catch deliver и превращаются в unavailable.
Отдельного ambiguous результата после вступления в transport в публичном
пути нет. Само retryable=false правильно запрещает повтор, но не делает
неизвестную доставку доказанным блокированием или отсутствием передачи.
Это противоречит принятому договору «неопределённая внешняя доставка остаётся
ambiguous» и правдивому trace FR-049.

Нужны независимое состояние вступления в transport и сохранение его
подтверждённого/неизвестного исхода через DB cleanup/commit. До вступления
можно вернуть доказанный blocked; после вступления без доказательства
получателя — ambiguous, без автоповтора. Полученный HTTP acceptance не
называть provider readback или удалением прежних данных.
Причинная приёмка: transport вошёл, затем timeout/ошибка; отдельно transport
вернул200, затем синтетический before_commit/cleanup failure. Оба пути
обязаны отличаться от доказанного pre-send refusal.

## S2 — P2: общий6с бюджет можно превратить в бесконечный drain потока

Место: `public/consent.py::send_consented_event`, create_task(to_thread(sender))
и cancel handler с `while not task.done(): await shield(task)`
(около158–169). У цикла нет конечного срока и он поглощает повторную отмену.
Будущий guarded_transport действительно ограничен deadline, но это не
ограничивает синхронную подготовку sender **до вызова transport**.

В фактическом sender PostHogClientWrapper.from_settings вызывает
secret_file_status → Path.read_text; wrapper и global/provider gates также
синхронно читают файлы. При блокировке такой подготовки timeout6с отменяет
внешнюю корутину, после чего она навсегда ждёт thread task с удержанным
PostgreSQL advisory lock/соединением. Например, закрытый временный учебный
FIFO в роли key-file без writer причинно воспроизводит неограниченный read;
вообще не нужно начинать HTTP. Это ошибка границы6с, а не требование
дополнительного сервиса или общей переделки хранилищ секретов.

Нужно ограничить всю подготовку/дренирование и гарантировать, что оставшаяся
после отмены синхронная работа не сможет поздно войти в transport после
освобождения защиты. Простое прекращение ожидания shield без запрета
позднего transport небезопасно. Приёмка: подготовка sender удерживается до
истечения общего бюджета, одновременно ждёт revoke; запрос завершается
в принятом конечном сроке, lock освобождён безопасно, позднее отпускание
подготовки не начинает сеть. Отдельно проверить повторную отмену во время
настоящего bounded async transport.

## Что уже выглядит корректно по исходнику

- Сырой UUID канонизируется, digest вычисляется только первой стороной;
  id/epoch не входят в properties или distinct_id провайдера.
- Control route требует точный configured Origin, ограничивает streaming
  body1024байта, даёт no-store и stable reason без exception text/ID.
- Read не создаёт строку; revoke не зависит от flags/basis/revision;
  grant повторяет basis guard после lock, использует CAS и новый epoch.
- Успешный control response строится заранее, но возвращается только после
  успешного выхода db.begin/commit. Ошибочный commit не отдаёт accepted/epoch.
- Общий digest advisory lock используется и для отсутствующей строки;
  новые строки берут admission после digest, pg_total_relation_size проверяется
  под ним. Существующий revoke не зависит от cap новых строк.
- Migration включает ENABLE/FORCE RLS и exact digest predicate; maintenance
  ограничен session_user/current_user/named operation/feature/actor/reason.
  App не получает DELETE, maintenance не получает INSERT. Context
  transaction-local, существующий after_begin сохраняет его между транзакциями.
- Wrapper сохраняет global/provider gate и payload guards; delivery без
  переданного transport закрыта. Автоматической очереди/retry здесь нет.

Это source observations, не принятие actual roles/DB/cap или runtime.
Нельзя закрыть RLS по тестам с суперпользовательским seeded connection;
проверки реальных app/maintenance/no-context/cross-digest прав остаются нужны.

## Пределы и текущие зависимости

Прочитанный contract test уже содержит4 основных сценария и новые
multiprocess/cap/timeout/commit cases. Их runtime исход reviewer не получал.
Browser grant/revoke/retry/onConsent, lifecycle/retention/restore quarantine,
публикуемые тексты и внешний readback ещё не приняты. Текущие общие
privacy/security/infra HOLD, внешний SDK, fullT106/T113/T0 остаются открытыми.
Некорректный action с JSON-массивом первоначально мог давать503, но в ходе
параллельной работы добавлена проверка isinstance(action,str); в текущем
снимке это не считается открытой ошибкой.

## Хеши прочитанного серверного снимка

- consent.py: `ee6aadb749a6cd34fbd2e63528a12539d82bc162edd23624cd3be9c047be6903`
- web.py: `e8a80c667a8a6e378ecdaa896f476dcbae2a809c85cb6ee997c53df67e5a09a9`
- analytics.py: `6ef00ee65ecffd7431db71acf1cbd08fbf2044512e05e847763bae25d752d7f5`
- model: `35ad147276b65907315181f6535ba0329f420dba519151b1464e1815d72b5194`
- tenant_context.py: `a42161e70629b4c2ffd916110fece8f764e2e2569ea258d2ce7fda335eee3bd7`
- migration0108: `b63793d10829de1a50fc0c38453bc9c0ae5320a4d87a209bfc1ed92bc0a576e6`
- test_public_consent_control.py: `3ed9f6f07f612681bcff26f0f82eea3e4ccfd6ff861ffc65833c4fa6c33a22cd`

Изменён только данный новый reviewer report. Код, spec/plan/tasks,
checklist, Git/GitHub, сеть, БД и runtime не менялись; чужая работа сохранена.


## Повторная проверка решения S1/S2, 01.11.2026

Текущий снимок consent.py:
`572815e48b097c2a8039d7be85a690b6ae5f1e2505c09769ba9076281cfe54b2`.
Test module:
`136e8950c6252136505d6793fb608cfc52074ab8d50e9ebbceb35fe806577d32`.
analytics.py и web.py сохранили указанные выше хеши. Прочитаны весь новый
send_consented_event и причинный late_sender_failure test. Основной агент
сообщил RED1failed/7passed → GREEN8passed/0skips; reviewer эти запуски не
повторял и не видел исходного журнала, поэтому это переданное evidence.

**S1 закрыт по исходнику:** entered/response_status хранятся независимо от
sender и DB exit. Наблюдённый2xx остаётся live_safe_sent/delivered=true при
позднем OSError/commit error; вступление в transport без ответа возвращает
transport_ambiguous/delivered=null/retryable=false. Pre-send denial остаётся
отдельным. Прочитанный тест непосредственно проверяет200→late OSError.
Профили transport-timeout и200→commit error ещё следует реально выполнить;
их отсутствие не переименовывается в обнаруженную ошибку кода.

**S2 закрыт в части DB/сети:** sync sender не владеет DB, native async
transport получает собственный lock через bounded IO/commit. Отмена
родительского запроса не освобождает чужую DB-сессию: closed.set() запрещает
позднюю отправку и проверяется и в sync transport, и в queued async callback
до DB, и после получения digest lock. Уже вошедший native transport имеет
собственный deadline и завершает lock scope. Цикла бесконечного ожидания
sender под DB lock больше нет. Прочитанный тест удерживает preparation,
показывает возврат запроса и успешный revoke, затем отпускает поток и
проверяет отсутствие новой сети. Такое оставление потока без DB допустимо
для границы согласия; простое отсутствие await потока не является обходом
отзыва при этих трёх проверках closed/deadline.

### S3 — P2: оставляемые подготовки не имеют ограничения количества

Оставшийся ресурсный пробел относится именно к выбранному способу отделения
потока, а не к освобождению DB lock. consent.py:185 каждый раз делает
create_task(asyncio.to_thread(sender,...)); после6с task остаётся живой из-за
shield, и новый запрос создаёт следующую независимо от количества таких
предыдущих подготовок. Ни semaphore/admission, ни отдельный принятый предел
на outstanding preparation в этом пути не найден.

Причинный сценарий: несколько sender блокируются в подготовке, как в уже
принятом учебном stalled_preparation, но release не наступает. Запросы
завершаются по6с, а их worker threads остаются заняты. Следующие запросы
создают новые futures в неограниченной очереди общего executor, даже если их
closed уже установлен до начала выполнения. Старые queued sender всё равно
начнут полную синхронную подготовку, поскольку closed проверяется только при
последующем transport. В результате исчерпываются общий пул потоков и память
очереди; shutdown_default_executor также ждёт незавершённую работу. Конечный
срок HTTP-запроса не является ограничением этих ресурсов.

Нужен маленький конечный admission подготовки в существующем процессе:
число действительно незавершённых sender должно иметь предел, и слот
освобождается после фактического завершения потока, а не после таймаута
родителя. Ожидание admission входит в прежний deadline; при исчерпании
аналитика закрывается, продукт не ждёт. Рано закрытая queued попытка не
должна начинать подготовку. Новый сервис/брокер/общая фабрика очередей не нужны.

Приёмка: удержать все принятые preparation slots, отправить больше запросов
чем предел, дождаться их bounded закрытия и доказать, что started/outstanding
preparation не растёт; revoke не ждёт и новая сеть не возникает. Отпустить
учебные потоки и доказать возвращение ёмкости без фоновой отправки. Предел
может быть простым и локальным для worker, без нового идентификатора данных.

**Текущий вывод:** S1/S2 закрыты по исходнику; S3 P2 остаётся открытым.
Общий срез WIP/HOLD. Requirements checklist6/0 и все прежние общие
privacy/security/infra/runtime/T0 HOLD не менялись. Новых тестов reviewer
не запускал; изменён только этот отчёт, код и чужие изменения сохранены.


## Повторная проверка ограничения подготовки S3, 01.11.2026

**Текущий узкий source-вердикт: S1/S2/S3 закрыты; новых P1/P2 в повторно
проверенной серверной границе не найдено.** Общая реализация остаётся WIP/HOLD:
это не convergence, не приёмка браузера/lifecycle/restore или рабочего запуска.

Прочитаны полный текущий consent.py, новый causal stalled_preparations test,
actual-role migration test и real-wrapper→fake-transport test. Хеши:

- consent.py: `8f9c7e7b1f1d57befb21cf80bfb82982ec2695b1d869404e43a0f8256322097f`
- test_public_consent_control.py: `0a97e7c82cc457c65696be03ff160b7511ab86a6d7e33c671b9f921caec358ef`
- analytics.py: `6ef00ee65ecffd7431db71acf1cbd08fbf2044512e05e847763bae25d752d7f5`
- web.py: `e8a80c667a8a6e378ecdaa896f476dcbae2a809c85cb6ee997c53df67e5a09a9`
- model: `35ad147276b65907315181f6535ba0329f420dba519151b1464e1815d72b5194`
- tenant_context.py: `a42161e70629b4c2ffd916110fece8f764e2e2569ea258d2ce7fda335eee3bd7`
- migration0108: `b63793d10829de1a50fc0c38453bc9c0ae5320a4d87a209bfc1ed92bc0a576e6`

### S3 закрыт

Процессный threading.BoundedSemaphore(4) приобретается неблокирующим вызовом
до создания to_thread/task. При исчерпании немедленный pre-send closed result:
нет новой future, очереди ожидания admission или DB-сессии.
Слот захватывается в local slots и освобождается из finally фактически
выполненной prepare, поэтому родительский timeout не возвращает ёмкость,
пока реальная подготовка ещё занята. На старте prepare проверяется closed;
ранее закрытая queued попытка не начинает sender. Сохранены обе проверки
перед guarded transport и после lock, самостоятельное владение DB native
корутиной и независимая правда HTTP/ambiguous исхода S1/S2.

Таким образом, этот путь может оставить максимум4 подготовки на процесс,
а не неограниченную цепь abandoned futures в общем executor. Если подготовка
не завершится, её слот остаётся занят и дальнейшая аналитика закрывается —
это выбранная деградация. Удерживаемый слот не подменяет успех и не даёт
позднюю сеть. Принудительно убивать thread или добавлять executor/service
ради данного исправления не требуется.

Прочитанный test_stalled_preparations ограничивает учебный semaphore двумя
слотами, подаёт10 запросов и требует ровно2 started preparation, bounded
отказы, успешный revoke, отсутствие позднего transport и возврат ёмкости
после фактического release. Это причинно покрывает S3; простая проверка
конечного времени одного запроса его бы не покрыла.

### Дополнительный серверный профиль — прочитанный тест, не runtime-проверка reviewer

Actual-role test создаёт LOGIN NOSUPERUSER/NOBYPASSRLS/NOINHERIT роли,
применяет реальную migration0108 после их создания и подключается ими:
app без контекста видит0, под digest ровно1/другой0, DELETE запрещён;
maintenance с иной operation0, с public_consent_control2; RLS/FORCE флаги true.
Это содержательное доказательство в сценарии, не имитация через SET ROLE
на суперпользовательском соединении. Полную эксплуатационную матрицу этим
тестом не объявляем пройденной.

Real-wrapper test использует действующий PostHogClientWrapper с локальным
учебным ключом, нормализацию публичного события и fake async transport.
Проверяет прежний view_id, отсутствие consentId/digest/epoch в receiver
body, отказ final provider gate и отказ старому epoch после revoke. Gate
параметризован, внешний получатель не вызывается. Тест не доказывает
реальный provider readback или рабочую конфигурацию.

Основной агент сообщил причинный RED S3 (10started вместо2), затем50passed/
1deselected в четырёх модулях и11passed/0skips отдельного нового модуля.
Reviewer видел код этих сценариев, но не запускал их и исходные журналы в
этом проходе не перечитывал; числа остаются переданным evidence.
Тест200→commit error, транспортный unknown и активная cancellation/drain
остаются обязательными частями итоговой объявленной failure приёмки —
закрытые source замечания не подменяют выполнение полного quickstart.

Изменён только данный reviewer report. Checklist6/0 не менялся; исходники,
проектные документы, Git/GitHub и runtime не менялись. Сеть/БД/тесты reviewer
не запускал. Внешний SDK, общие privacy/security/infra HOLD, полный T106,
T113/T0 и цель трафика/продаж остаются открытыми в прежних границах.
