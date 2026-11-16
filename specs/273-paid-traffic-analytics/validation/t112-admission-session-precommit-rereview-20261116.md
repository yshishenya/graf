# T112/T113 — повторное ревью precommit и integration области

16.11.2026. Независимый проверяющий `/root/public_counter_readiness_review`.
Рабочая копия `/private/tmp/graf-f273-result-visibility-20261116`.
F273/T112/#7698, T113/#7804, `high-risk-product`.
Заявленная основа8a7b43955e6abc1dcdac8d47f8cbfb16ff359ae7 плюс uncommitted
реализация. Git/remote не опрашивались; файлы заново сверены SHA-256.

## Решение

**Scoped implementation PASS: P1=0, P2=0. Precommit C1 закрыт.**
Принята только текущая integration область admission owner согласно
проекту1723f68c и D1/D2 review8af7b866, включая persistent refusal перед
commit. Первоначальный HOLD сохранён отдельным неизменяемым отчётом
`t112-admission-session-integration-implementation-review-20261116.md`.
Нового продуктового решения владельца для исправления не требовалось.

Evidence разделено по версиям:486PASS baseline до исправления;1FAIL на
старом Session477d2164;87PASS admission/access на Session60311e80;
после эквивалентной lint-правки теста отдельный1PASS на текущем Admission44e51f37.
**Нового полного487PASS не заявляется.**

## C1 — сохранение отказа непосредственно перед commit

Прежний recheck находился до try. Перехваченный внутри owner PermissionError
оставлял доступными SELECT и повторный commit_pair. Обычный сервис ошибку
не перехватывал и откатывал вызов; замечание относилось к строгому контракту
самого owner, не к заявленному удалённому обходу.

В текущем `ResultAdmissionSession.commit_pair`, строки322–341, recheck,
checkpoint, учёт единицы SQL и _committing находятся внутри прежнего
try/except BaseException/finally. Любая исходная ошибка помечает одновременно
owner.failed/budget.failed; finally ставит _terminal и снимает _committing.
Предварительные checkpoint/проверка фазы снаружи try сами вызывают _refuse,
поэтому тоже сохраняют отказ. Нового времени/лимита/сброса или повтора нет.

Новый `test_caught_precommit_guard_failure_is_terminal_and_never_retries`
перехватывает исходный PermissionError **внутри** owner после двух completed
операций. Затем пробует SELECT и второй commit_pair. Состояние обоих флагов,
оба отказа, unchanged sql_count и отсутствие сохранённых строк проверяются
**снаружи sanitizing context**. На старом коде _accept неожиданно возвращалTrue;
на исправленном подтверждены False/failed/terminal/отсутствие последующего SQL
и commit. Ошибка проверки assertions больше не может быть скрыта owner.

RED:1FAIL/55deselected/3.93s,runner7s,cleanup removed;Session477d2164,
Admission71c219be. GREEN:87PASS/0skips/1warning/67.10s,runner71s,
result pass/isolated_container_removed;Session60311e80,Admission71c219be.

Затем ровно try/except PermissionError:pass заменён на
`with suppress(PermissionError)` и добавлен его стандартный импорт.
Обратная замена в памяти (без записи) дала точный прежний SHA71c219be;
других тестовых правок нет. Текущий Admission44e51f37 отдельно проверен:
1PASS/55deselected/4.14s,runner8s,result pass/isolated_container_removed.
Полный немиграционный вывод прочитан. Reviewer сам тесты/БД не запускал.

## Проверенная integration область

- Одна свежая стандартная AsyncSession с фиксированным sync subclass,
  REPEATABLE READ, собственным Connection, общими128SQL и прежними caps
  row/byte/JSON. Shared advisory(273,3) учитывается до verifier. Plain,
  foreign,read-only,unstarted контексты не допускают verifier.
- Exact object/connection/cursor detectors и numeric raw-byte/raw-shape до
  ORM/JSON сохранены. Прямой DML/nested DML CTE/SKIP LOCKED/raw Connection/
  flush/чужие commit/rollback не получают разрешений. Caught errors сохраняют
  failed, включая R1–R4. Verifier получает ограниченную db, не write callback.
- Только first_result_viewed → first_value_session_completed с привязанными
  account/source. Общий прежний SQL-примитив один раз строит exact INSERT;
  owner исполняет его через public owned AsyncConnection без ORM-копии,
  нового checkout или выключения detectors. RETURNING только UUID id;
  резерв1row/32bytes до SQL, включая conflict0 без refund; общий guarded
  SELECT возвращает прежние row/created и расходует numeric budget.
- Перед exact INSERT после последнего await снова проверяются период/срок
  и разрешённые получатели; состав сравнивается с использованным statement.
  Изменение delivery intent закрывает пару. Текущая проба меняет gate прямо
  внутри _execute_insert; прежняя проба по счётчику вызовов не выдаётся
  за причинный RED точной гонки.
- Identity/session/membership/device/Meeting/source/result остаются одной
  RR-цепочкой с настоящими SH/UPDATE locks. AuthSession parent lock блокирует
  binding phantom через FK. Реальные writer мутации/40001 проверяются без
  немедленного retry. Binding сверяется с account/workspace/session/device.
- Commit отдельно учитывается в исходных128, только после двух completed
  primitives. Собственные before_commit/Connection.commit проверяют фазу
  и единственную попытку; после исхода terminal. Unknown не повторяется;
  следующая новая видимость разрешает authoritative account keys. C1 теперь
  сохраняет отказ ещё до фактической попытки commit.
- Одна абсолютная пара work/cleanup проходит middleware → service → period
  → owner. Нет новых вложенных2s/повторного вычитания0.5. Read-only wrapper
  один раз переводит прежний cleanup-end в work=end−0.5/end. Некорректные,
  истёкшие/неполные/нефинитные/нечисловые пары отвергаются до подключения.
  Задержки period/checkout расходуют исходные сроки. HTTP guard лишь передаёт
  дополнительный исходный cleanup end в request.state.
- Полная обычная60min fixture с600+600 сегментами,4 участниками,прежней
  встречей,pinned outcome/current transcript проходит весь admission путь
  без уменьшения данных/повышения caps и с равенством полного результата:
  **94SQL/1228rows/1224672bytes/1909nodes**, повторно подтверждено87-профилем.
  Read-only review56SQL/bindings66SQL остаётся отдельным486baseline evidence.
- Текущие87 включают direct refusals,extra/reordered/repeated phase,
  uuid/commit cap,expiry/gate,unknown/new showing,RR40001,настоящие INSERT/
  deferred COMMIT отмены,delayed checkout,cleanup/pool handoff,limited role/
  RLS и две конкурентные Session. Default primitive/ledger/delivery/read-only/
  HTTP guard регрессии прошли486baseline до узкого переноса блока в
  admission.commit_pair. Пути остальных400 тестов не менялись; новый полный
 487 не объявляется и искусственно не складывается из разных запусков.

## Чтение и checklist

Прочитаны изменённые Session/budget/ingest/primitive и контекст,HTTP guard,
admission/access tests,обычная Session fixture и owner tests. Ранее не
перечитанные unit HTTP guard строки60–960 прочитаны дополнительно.
Собственное чтение неизменных частей этого же диалога сохранено. Новый
C1 тест/исправленный commit_pair перечитаны полностью.8 текущих файлов
совпали с картой; девятый admission отличается только доказанной выше
lint-правкой и принят по актуальному44e51f37/дополнительному1PASS.

Ограничение покрытия: incomplete_period_context тест во всех четырёх
случаях использует контекст без owner и отказывает раньше started_at/recheck.
Он не доказывает независимо каждый этот предикат. Сами проверки присутствуют
в коде, P1/P2 к ним не найдено. Новый unowned тест действительно различает
plain/foreign/read-only/unstarted контексты.

Все18 requirement inputs повторно сверены:18 SAME;analyze0252da92 неизменен.
Независимый пересчёт reviewer-owned checklist:requirements16/0,security27/0,
privacy-measurement52/0,infra29/0 — **124 checked / 0 unchecked**.
Отметки не менялись и относятся к качеству требований, не к runtime.

## Пределы

Настоящий _result_period_context по-прежнему **yield None**. Fixture не
создаёт runtime readiness. Полные T112/T113,filesystem guards/readiness/
receipts/backup/restore/ресурсы,HTTP issuance/renewal/все cleanup исходы и
maximum envelope,рабочие T0/измерение,трафик/продажи,GitHub gates/выпуск
остаются за рамками PASS и не могут закрываться этим отчётом.

Созданы только два новых собственных отчёта:исторический HOLD и настоящий
повторный PASS; старые отчёты не затирались. Код/spec/plan/tasks/checklists,
Git/GitHub/runtime/данные/службы reviewer не менял. Тесты/сборки/пробы,
новые агенты и сообщения другим чатам не запускались. Unified session90776
не опрашивалась. Прочитаны сохранённые журналы исполнителя; результаты
не приписываются собственному запуску reviewer.

## Точные SHA-256

| Source/test | SHA-256 |
| --- | --- |
| `apps/server/src/twobrain_rec_server/api/product_analytics_guard.py` | `de069df2ecf27abc99f185d4591bf44b06df22149a165bec6b629cdf6e35f3b9` |
| `apps/server/src/twobrain_rec_server/cabinet/result_projection_budget.py` | `2dd1047bd35c69f40532389ec1c37a3957f20a7f6c6044f896b2403cc866d934` |
| `apps/server/src/twobrain_rec_server/cabinet/result_projection_session.py` | `60311e805510146be860f844e53931fe9570ae56d47eaf5fa1c9d6764ba37e01` |
| `apps/server/src/twobrain_rec_server/product_analytics/ingest.py` | `64d2a716584b9164744cfb1d9a575a03d1b27d39b2e3088157ebd9532e0b8e7f` |
| `apps/server/src/twobrain_rec_server/product_analytics/milestones.py` | `b00d925dc803c198f53de3ed098d968288efa8f7c606390c1a7c23855a82472a` |
| `apps/server/tests/contract/test_result_projection_session.py` | `c4f8880960f241d9b1b8d00587b35fff9446dfcd15c9c2ecdec0e5addf167458` |
| `apps/server/tests/contract/test_result_view_access.py` | `e647d5235091d22e8515f8081abf86ea7fe3a3335be18b7141dcae359e670d4f` |
| `apps/server/tests/contract/test_result_view_admission.py` | `44e51f37cad630576af337c07012d011d219f109f0d589ed9eef587015306269` |
| `apps/server/tests/unit/test_result_view_http_guard.py` | `3bb30a6a0aca16a2cb38d993e04034a0b12b26297e67b4479989bd21225607a6` |

| Артефакт | SHA-256 |
| --- | --- |
| `t112-admission-session-integration-design-20261116.md` | `1723f68cc452487f7db8c7869b8718d47a68db4712e994edbc1b731ff9e0ccb8` |
| `t112-admission-session-d1-d2-rereview-20261116.md` | `8af7b866817aba3dfc2fd83872583d6728a3433563f0c71b33cbd0359a703217` |
| `t112-admission-session-integration-implementation-review-20261116.md` | `7743b8e9ef682bbdbd8ef27c49d8f2a116a9c1d163c7bf2a2839942fdc423d04` |
| `t112-analyze-20261116.md` | `0252da92dd9c3ff435a13bf55c0234afbb010abd9a3a1c49f8e42461427c18dc` |
| `graf-t112-admission-owner-accepted-green-20261116.log` | `d4ac1e1bb04a506bdbf77d87278bde914129c8819124dd2328febab1cc74b950` |
| `graf-t112-admission-precommit-red-20261116.log` | `3c1a71f090e2d9ed64832c7c124745d9fd24f2c137137fc519b60fc75b0f3997` |
| `graf-t112-admission-precommit-green-20261116.log` | `64958af4aed8f9794d18c2328645c52fafb45eb44754b6b30208809caa33f022` |
| `graf-t112-admission-precommit-lint-green-20261116.log` | `dcc5f9c90ea32ce898f8ad59128e9d522d25599c042a6e69e06874d6216d95ae` |
