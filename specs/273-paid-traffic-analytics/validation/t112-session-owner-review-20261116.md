# T112 — независимое ревью отдельного владельца Session только для чтения

16.11.2026. Проверяющий `/root/public_counter_readiness_review`.
Копия `/private/tmp/graf-f273-result-visibility-20261116`.
Основа `3fd1de03b342d85537784db98b213dfc1553edbd` плюс новые owned files.
Полоса: implementation review существующего high-risk-product F273/T112.
Прочитано полное задание `graf-t112-session-owner-review-request-20261116.txt`;
повторные прямые сообщения имеют ту же область и не разрешают новые запуски.

## Решение

**HOLD отдельного read-only Session owner: P1=0, P2=3.**
Нужны исправления R1–R3 ниже. Это дефекты уже заявленной standalone области
перехвата/отказа неизвестных форм, а не отсутствие будущих HTTP/admission/
T113 или требование превратить Python-код в общую песочницу.

Текущие24 PASS подтверждают перечисленные проверенные пути и не покрывают
три найденных случая. Новых тестов/проб reviewer не запускал. Контрпримеры
ниже — статический разбор нынешнего кода и установленного SQLAlchemy2.0.51,
не новые наблюдения runtime. Достижимость этих трёх форм в нынешнем штатном
reader не заявляется; однако компонент сейчас принимает их через обычные
публичные SQLAlchemy API вместо требуемого безопасного отказа.

## R1 — P2: другая привязка Session обходит единственное защищённое соединение

Места: `result_projection_session.py:118–137,158–172,187–192`.
Фабрика проверяется только по class_ и общему bind AsyncEngine. При этом
принимается обычный `async_sessionmaker(bind=engine_a, binds={Probe:engine_b})`.
Ещё один вариант — публичный
`db.execute(select(Probe), bind_arguments={"bind": engine_b.sync_engine})`.
Также `db.connection(bind_arguments=...)` может получить второе соединение
той же Session и затем вызвать его Core execute без do_orm_execute.

`start()` настраивает RR, timeout и detectors лишь на default connection A.
При ORM чтении `_read` всегда проводит numeric preflight на A, но
`state.invoke_statement()` сохраняет bind_arguments и mapper/table routing.
SQLAlchemy может выбрать B для исходного Q. Detectors на B отсутствуют,
а `_permit` при выходе просто очищает `_expected/_cursor_pending`, не
проверяя, что исходное выполнение действительно прошло через защищённый A.
Получается проверка данных/снимка A перед загрузкой данных B, без счёта
исходного SQL B и без установленных для него RR/statement/lock timeout.
Это нарушает основное соответствие preflight→reader ещё до HTTP или записи.

Источник подтверждения: AsyncSession.__init__ в установленном
`ext/asyncio/session.py:250–270` переводит и основной bind, и binds в sync
варианты. `orm/session.py:2259–2280` выбирает get_bind и соответствующее
соединение после обработки событий; get_bind:2780–2845 явно предпочитает
переданный bind и поддерживает mapper/table binds. Это штатная маршрутизация,
не произвольный доступ к asyncpg и не изменение частных полей владельца.

Нужно до выдачи результата закрыть любое отличающееся соединение/привязку
Session, включая factory binds, явный bind_arguments и прямое получение
Connection. Поддерживать несколько БД не требуется: допустим отказ.
Одного запрета binds у фабрики мало без защиты последующих bind_arguments/
получений Connection. Добавить причинные проверки этих публичных путей:
второе соединение не исполняет tenant/private/control SQL, не выдаёт объект,
а владелец остаётся failed. Положительное чтение на единственном A сохранить.

## R2 — P2: внешний SELECT с изменяющим CTE проходит как read-only

Места: Session `_read:124–130`; `result_projection_budget.py:72–93`.
Проверяется `state.is_select`, а обход `_bounded_projection` отвергает
несколько конкретных классов/функций, но не Insert/Update/Delete внутри CTE.
Например, публичная конструкция
`select(literal(1)).add_cte(delete(Probe).where(Probe.id == 1).cte("d"))`
остаётся Select с допустимым Integer output и без запрещённых функций.
Её числовой preflight тоже содержит data-modifying CTE.

SQLAlchemy документирует именно такое назначение `add_cte`: независимый
INSERT/UPDATE/DELETE CTE выполняется даже без ссылки из SELECT, а по умолчанию
переносится к верхнему итоговому WITH при вложении SELECT в подзапрос.
Прочитаны `sql/selectable.py:2531–2604`; `sql/dml.py:421` задаёт узлам
`is_dml=True`. Эти узлы доступны общему visitor, но нынешний код их пропускает.

Владелец до исходного reader может выполнить изменение таблицы внутри
своего numeric запроса. Session.before_flush/before_commit это не остановят:
нет ORM flush/commit, внешняя операция — Select, а Connection detectors
проверяют только разрешённый внешний объект. Последующий rollback не делает
выполненное изменение допустимым чтением, не отменяет уже взятые write locks
и не доказывает отсутствия эффектов sequence/trigger. Сохранение изменения
после закрытия контекста здесь не заявляется.

Требуется отказ до первого такого SQL для всех DML внутри дерева выбранного
Q, включая referenced и независимые CTE. Запрет outer insert/delete из
нынешнего теста недостаточен. Добавить причинный случай с внешним SELECT и
изменяющим CTE: отказ происходит до эффекта на таблицу, без модели и без
возможности продолжить тем же владельцем. Это можно закрыть узким отказом,
не создавая отдельный SQL rewriting framework.

## R3 — P2: SKIP LOCKED допускает другой набор между фазами одного RR

Места: Session `_read:124–130` и numeric `_bounded_projection:78–93`.
Принятый проект295ce2c прямо требует отказа для SKIP LOCKED до полного row.
Нынешний обход не проверяет `ForUpdateArg.skip_locked`, и Session тоже не
отвергает эту форму. Select с `.with_for_update(skip_locked=True)` проходит.
В установленном SQLAlchemy это обычный ForUpdateArg со skip_locked boolean
(`sql/selectable.py:3256–3315`); он включён в traversal Select:5346.

Конкретный опасный порядок: другой writer держит row lock видимой RR строкы
с body сверх256KiB. Numeric byte/shape Q с SKIP LOCKED видят пустой набор;
writer освобождает lock после preflight, до исходного Q; исходный Q читает
ту же строку и отдаёт её большое поле driver/ORM. Данные строки не менялись,
поэтому не требуется40001 или новый snapshot. Даже полный ORDER BY id не
стабилизирует динамическую доступность row locks. Числовое разрешение пустого
набора не ограничивает фактический последующий результат.

Нужно закрыть SKIP LOCKED в полном дереве Q, сохранив принятые обычные
FOR UPDATE/SHARE и NOWAIT/ограниченный timeout. Причинная проверка должна
показать отказ формы до материализации, включая вложенный locking selector;
для демонстрации основания можно синхронизировать освобождение чужого lock
между preflight и исходным Q. RR сам по себе этого случая не исправляет.

## Проверенное положительное поведение

Полностью прочитаны новый модуль214 строк, тест417 строк, main validation148
строк и текущий F273 fragment. Прочитаны зависимости tenant settings и
apply_tenant_context, необходимые части SQLAlchemy Session routing, traversal,
asyncpg close/invalidate, прежний принятый проект и применимые контракты.

На единственном штатном bind владелец выбирает RR до tenant SQL, выключает
autoflush и не принимает заимствованную Session/начатую Connection. Session
hook покрывает execute/scalar/scalars/get; кэш ранее проверенного get не
повторяет SQL. Для двух поддержанных tenant contexts ожидаемый set_config
SELECT сравнивается с общим apply_tenant_context; произвольный raw/control
вызов разрешения не получает. Исходная ORM форма не заменяется.

Подсчитываются actual SQLAlchemy cursor executions защищённого соединения,
включая SET/tenant/numeric/original, с отказом перед129-м. Это не подсчёт
каждого низкоуровневого PostgreSQL protocol message. Полезная работа имеет
общий срок1.5s, ещё0.5s оставлено close; остаток и failed state проверяются
до/после исполнения и явным checkpoint после синхронной работы. Тайм-аут
statement уменьшается от500ms, lock250ms. Проверенные обычные исключения
превращаются в общий отказ; CancelledError сохраняет отмену caller.

Listeners снимаются перед прямым await close. При проверенном stuck close
fallback сверяет живую Connection и точный driver, прежде чем terminate;
уже отданный и повторно выданный driver не завершается по старой ссылке.
Это доказательство двух конкретных исходов close, не всех checkout/TLS/
pool reset/driver cancellation/cleanup неисправностей. Вызов invalidate после
terminate не выдаётся за универсальную доказанную границу всех внешних hooks.

## Прочитанные тестовые доказательства

Финальный журнал прочитан по всем немиграционным строкам, включая collection,
summary, stdout ordinary fixture и завершение. Большой metadata-only список
миграций не выдаётся за новое ревью их исходников. Результат **24 PASS,
0 skips,1 прежний PytestAssertRewriteWarning,17.52s**, runner22s,
`postgres_test_result=pass`, `isolated_container_removed`.
Основной исполнитель сообщил terminal session77922 EXIT0; reviewer эту
terminal session не опрашивал. Журнал не имеет собственного source-hash
manifest: привязка к точному коду — подтверждение исполнителя и нынешняя
сверка, а не новый exact-SHA CI или самостоятельный запуск reviewer.

| Обычный полный путь | SQL | Rows | Raw bytes | JSON nodes |
| --- | ---: | ---: | ---: | ---: |
| Общий review | 56 | 1212 | 1214494 | 1263 |
| Fresh bindings с source/Meeting fence | 71 | 1216 | 1221872 | 1870 |

Fixture действительно содержит3600s,600 transcript/600 diarization rows,
JSON provenance,4 календарных участника, предыдущую1800s встречу с результатом,
текущую transcript v3 и итоговую v2 через настоящий default MeetingSummarySlot.
Полные ответы сравниваются с исходным reader без защиты; в bindings проверены
конкретные result/outcome IDs. Отключения calendar/previous/roster или
упрощённого аналитического reader нет. Время всего pytest case включает
создание fixture и исходное контрольное чтение; его2.21s нельзя напрямую
объявить временем защищённой Session либо POST. Общий контекст с timeout
проходит, но maximum допустимый envelope этим не измерен.

Читались оба причинных regression журнала: удаление budget.failed checkpoint
дало5 DID NOT RAISE,18 deselected,4.91s; удаление проверки текущего владения
перед terminate дало1 failure underlying connection is closed,23 deselected,
4.74s. Хеши совпали. Это контрпримеры двух конкретных исправленных дефектов,
не RED всего исторического пути без владельца. Текущий GREEN24 заново включает
эти случаи, lock timeout до model load, ровно один40001 без retry, отказ
сырого SQL/записи/stream, SQL128, sync checkpoint, отмену, отсутствие surviving
tasks в проверенных сценариях и тот же физический pool connection.
R1–R3 в тестовом файле отсутствуют, поэтому его PASS им не противоречит.

## Требования и оставшиеся границы

Все18 прежних requirement/review inputs независимо сверены: SAME. Собственное
чтение того же диалога сохранено; вновь прочитаны относящиеся к замечаниям
целые положения проекта295ce2c об interception/unknown/SKIP LOCKED/locks и
result-visibility о deadline/закрытой записи. Изменения требований не нужны
для устранения R1–R3: они уже требуют отказа неизвестных обходов и форм.
Analyze0252da92 остаётся прежним, новым PASS реализации не объявляется.

Reviewer-owned totals неизменны: requirements16/0,security27/0,
privacy-measurement52/0,infra29/0 — **124 checked/0 unchecked**. Отметки
не менялись. Неизменность требований не закрывает найденные дефекты кода.

Будущий full admission с filesystem/DB readiness fences, fresh legal/session/
source/deletion/writer fences, общей парой INSERT/commit, HTTP/auth/proof/
renewal, максимальным envelope, T113/restore и рабочим измерением остаётся
отдельным. Недостающие будущие возможности не включены в число дефектов этого
standalone review. Компонент не подключён к продукту, _result_period_context
остаётся yield None. Прямой произвольный asyncpg/DBAPI доступ не является
поддержанной песочницей; R1 относится к обычному публичному Session routing.
GRAF использует Postal; соседний Stalwart не является воротами этого этапа.

Создан только настоящий отчёт. Code/tests/fragment/main report, spec/plan/tasks,
checklists, Git/GitHub, runtime/данные/БД, сайт, почта, соседние службы,
сбор/T0/публикации/выпуск не менялись. Тесты, сборки, пробы, новые агенты
и межчатовые сообщения не запускались. Чужие изменения сохранены.

## Точные контрольные суммы

| Проверенный файл | SHA-256 |
| --- | --- |
| `cabinet/result_projection_session.py` | `0a7cd26ea864df12b498bf044015f34b328bf96c7c46ade1ee79b0c44b9b3c3e` |
| `tests/contract/test_result_projection_session.py` | `c071b26d044c377dd960e7ad706f66eb3d3864b4b3788877c954f384ecaa3bcd` |
| `cabinet/result_projection_budget.py` | `3017498c3ae23d897671ae7cc67432b36ffcfbedc9b96a0ab442610b4ef2d18b` |
| `changes/unreleased/F273.yaml` | `b027bcbf7ee98a5fb889eb4e69cc28535eaf2f6c994c2eb1e6479a215842667c` |
| Основной session-owner validation report | `6cfc576cf5e7ca108dc8b55b01a1c84756586cb9af31b225932112f940f51561` |
| Pinned-final GREEN24 log | `f2f34fc9521b03825ef5e4eed57ba83f9bb2efdecb436d2f73253cf71dbf0fcc` |
| Closed-state RED5 log | `55980bf6b67096a607b50c9db12fd72b40a629408deb8bee0f4f6bee40e07b2f` |
| Released-close RED1 log | `b34ae851486bebcf52aa0b2d90bbb6d4f84657322518e6bc09a375ff03a21244` |

Следующий шаг — узко закрыть R1–R3, показать причинные проверки на настоящем
PostgreSQL и новый exact code/test/log для повторного независимого ревью.
Старые24 PASS на изменившийся код автоматически не переносятся.

При окончательной сверке основной исполнитель уже сохранил срез в commit
`f59c1f70ff97d7ac94fd32c330599aa4eed8b889`. Source/test/fragment/main-report
хеши остались указанными выше; code/test blobs HEAD отдельно сверены с ними.
Первоначальная основа3fd1de остаётся происхождением изменения. Reviewer
коммитов не создавал; это заключение применимо к тем же exact code/test в
новом HEAD, а не является приёмкой последующих изменений или remote/CI.
