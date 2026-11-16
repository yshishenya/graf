# T112/T113 — повторная независимая оценка проекта D1/D2

16.11.2026. Проверяющий `/root/public_counter_readiness_review`.
Копия `/private/tmp/graf-f273-result-visibility-20261116`.
Заявленная основа `8a7b43955e6abc1dcdac8d47f8cbfb16ff359ae7`;
Git/remote не опрашивались по границам задания. Файлы сверены по SHA-256.
Существующие F273/T112/#7698, T113/#7804; `high-risk-product`, проект до кода.

## Решение

**Scoped DESIGN PASS: P1=0, P2=0. D1 и D2 закрыты.**
Принята редакция integration design1723f68c с полным финальным уточнением
«Уточнение после независимого HOLD: D1/D2». Старый собственный HOLD2e7d172e
сохранён неизменным. Это разрешает следующий изолированный шаг реализации
по данному проекту с последующим причинным RED/GREEN и независимым ревью.
Реализация, runtime verifier T113, рабочее измерение и выпуск не приняты.

Полностью прочитаны запрос85770b5f и весь актуальный integration design,
а не только добавленные абзацы. Проверены фактические hashes исходников,
на которых основан предыдущий самостоятельный разбор D1/D2: они не менялись.
Чтение применимых оригиналов и зависимостей из собственного предыдущего
отчёта того же диалога сохранено;18 входов заново сверены, все SAME.

## D1 — exact INSERT: PASS

Теперь выбрано конкретное исполнение, устраняющее ORM pre-session copy:

1. Единственный прежний primitive `admit_account_milestone` строит values,
   ON CONFLICT и фиксированный RETURNING id. Внутренняя необязательная
   `_execute_insert(statement)` не является публичным trust-флагом.
   Default caller сохраняет db.execute; копии SQL и разбора Insert._values нет.
2. Только фиксированная операция admission owner передаёт своё короткое
   замыкание. Оно использует **await owned_async_connection.execute(statement)**
   на том же statement, а не Session.execute/invoke_statement. Соединение
   public AsyncConnection получено один раз собственной свежей Session при
   start и соответствует Connection, на которой стоят detectors.
3. `_permit(statement)` и before_execute могут сохранить прежнее тождество
   объекта и закреплённого соединения: нет аннотирования ORM pre-session.
   Before_cursor должен подтвердить одно фактическое исполнение. Лимит
   statement, свежий gate/checkpoint и предварительный расход применяются
   до него; finally снимает разрешение, ошибка/отмена сохраняет failed.
4. Verifier получает только db, не callback. Общего разрешения DML/flush/
   rawConnection не появляется. Нет нового checkout или транзакции.
   Стадии owner привязаны к двум прежним именам, account/source и порядку;
   completed означает весь primitive с SELECT, а не лишь попытку INSERT.

Статический путь согласован с ранее прочитанными установленными SQLAlchemy
ORM/Core исходниками: Connection.execute передаёт исходный ClauseElement
в before_execute, затем компилирует его; scalar UUID не требует ORM
result-map. Проверяемый продуктовый путь использует public API и не читает
частные annotations/Insert values. Старый дефект «обычный db.execute под
_permit(original)» выбранным проектом больше не предлагается.

Фиксированный UUID RETURNING даёт не более1row/32bytes, резервируется до SQL
и не возвращается при конфликтном0. JSON/остальные поля читаются отдельным
общим SELECT с прежним numeric raw-byte/raw-shape preflight. Row/created
контракт примитива сохраняется; default caller получает один дополнительный
SELECT на успешном INSERT, что остаётся явной обязанностью регрессионной
проверки. Не вводится исключение из бюджетов для полного ORM RETURNING.

## D2 — абсолютные сроки: PASS

Уточнение теперь задаёт отдельные обязательные keyword-only
`work_deadline`/`cleanup_deadline` общему внутреннему context. Он не создаёт
новые2s и не вычитает0.5 повторно. Владелец использует work от start до
единственной попытки commit, очистка — исходный cleanup.

Read-only public wrapper сохраняет прежний deadline=end и переводит его
в work=end-0.5/end ровно один раз. Изменение его прежнего временного
контракта не требуется. Отдельный внутренний admit_result_view создаёт
исходную пару до входа в период; при внешней паре передаёт её без сдвига.
Один отсутствующий срок, невалидная/истёкшая пара и срок за start+2
закрывают путь до подключения/verifier. Проверка некорректной пары при
реализации должна исключать нечисловые/нефинитные значения, инверсию и
обход исходного0.5s резерва; никакой альтернативный увеличенный бюджет
настоящим PASS не вводится.

Поток явно задан: middleware → admit_result_view → _account_transaction →
_result_period_context → owner. Middleware сохраняет work в прежнем
result_view_deadline и исходный end в result_view_cleanup_deadline.
Handler передаёт оба, а не превращает work в новый end. В require_period
новые timeout2/timeout1.5 удаляются; используется timeout_at тех же значений.
Обычный server-auth путь сохраняется. Body/auth/dependencies/commit/response/
cleanup не получают отдельные новые2s.

## Сохраняемые требования к последующей реализации

Свежие filesystem/DB SH fences, identity/session/membership/device/Meeting/
source/result проверки и общий gate перед каждым INSERT/commit сохраняются.
Commit отдельно расходует единицу исходного128; последовательность после
двух completed операций допускает одну попытку и становится terminal.
После неизвестного исхода нет refund/retry, счётчики и failed не сбрасываются.
Повтор на следующем настоящем показе использует authoritative account keys,
не переписывая прежнее решение. Настоящий _result_period_context остаётся
yield None; положительный fixture не создаёт runtime readiness.

После кода обязательны причинные проверки exact public Connection исполнения,
другого/лишнего statement и direct DML, обоих primitive callers, UUID charge
и последующего guarded SELECT, фаз/порядка/перехваченной ошибки, свежего gate,
второго INSERT/unknown commit, задержки до периода/checkout без нового срока,
однократного резерва, отмены в SQL/commit/close и pool handoff. Assertions
состояния должны находиться снаружи sanitizing контекста. Fixture полной
обычной60мин встречи с600+600 сегментами должен проходить всю новую цепочку
в исходном envelope с равенством ответа; отказ не разрешает повысить caps
или уменьшить fixture. Writer/phantom races используют реальные fences.
Все это ещё план проверки, а не новые результаты тестов.

## Checklist и пределы

Независимый повторный подсчёт четырёх reviewer-owned checklist:
requirements16/0,security27/0,privacy-measurement52/0,infra29/0 —
**124 checked / 0 unchecked**. Файлы и отметки не менялись.
Все18 прежних requirement inputs SAME; analyze0252da92 неизменен.

Этот PASS закрывает ровно два замечания проекта до кода. Admission/два
INSERT/commit ещё не реализованы по данному проекту. Полные T112/T113,
runtime readiness/receipts/backup/restore/ресурсы/filesystem guards,
HTTP issuance/renewal/все cleanup исходы, maximum envelope, рабочие T0/
измерение, трафик/продажи, GitHub gates и выпуск остаются открытыми.
Никакие прежние частные PASS не переносятся на эти границы.

Создан только настоящий новый собственный отчёт. Старый HOLD, чужие code/
spec/plan/tasks/checklists/проект, Git/GitHub и runtime/данные/службы
сохранены. Тесты/БД/пробы/сборки, новые агенты и межчатовые сообщения
не запускались. Дополнительных продуктовых решений владельца не требуется.

## Точные SHA-256

| Артефакт | SHA-256 |
| --- | --- |
| Актуальный integration design | `1723f68cc452487f7db8c7869b8718d47a68db4712e994edbc1b731ff9e0ccb8` |
| Запрос повторного разбора | `85770b5fb5e60a2d9333206ce6c67ca72c89d3e8cb980360749d6f5c4af509f9` |
| Неизменный прежний HOLD | `2e7d172ee05216a7f2cc4737e84bd196789cd00f9b72f40cbe184061089d36a5` |
| ingest.py | `b718fd0c23c08c1b51cfe2062254c1433b026f4bc68c1f37a2b79b2c5f31095a` |
| milestones.py | `f6fa054826632f5f6f40c16fd8449f05ea82c35f64750f3e5fea26480ee31f02` |
| Session owner | `95108da96f1df0c479ad402cc80a563382049f395d276c5976499a8a67874dc8` |
| HTTP guard | `0ee850ee5310ff1c83d3c6e32d209ce8cee97951393863e937ac33f8e51421bc` |
