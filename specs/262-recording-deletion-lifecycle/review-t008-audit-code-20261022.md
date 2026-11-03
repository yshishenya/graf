# Независимое ревью кода и узкая сверка T008 / #6883

Дата: 2026-10-22. Проверяющий: `f262_requirements_reviewer`, отдельный агент,
не автор продуктового исправления. Исходная основа:
`9b286f6d9df01f4b948d7db1673aff99c78635ff`, ветка
`codex/262-origin-cancellation-audit`. Проверены незакоммиченные байты пяти
файлов; окончательный новый commit SHA ещё не присвоен этой проверкой.

**Итог: PASS в области исправления device audit T008. Блокирующих замечаний
к проверенным исходникам и тестам нет. Все 6 пунктов обязательного профиля
выполнены. CRITICAL 0 / HIGH 0. Узкая сверка: новых обязательных доработок
в этом исправлении не обнаружено.**

Это отдельное ревью готового кода после requirements gate. Предыдущий
внешний отчёт об отсутствии device audit на ee33/9b286 сохраняет историю
исходного дефекта. Новый PASS относится к перечисленным ниже изменённым
байтам и не приписывается старому коду, T007 или PR7722.

## Результат по шести условиям

| Условие профиля | Исходник и самостоятельная оценка |
|---|---|
| Первое событие и доверенная identity | PASS. `deletion/origin_cancellation.py` добавляет событие только внутри `if cancellation is None`, после flush серверного marker. Workspace/actor/device берутся из scope, время из marker.accepted_at, metadata связана с marker.id. Фиксированы event_type/safe_reason `recording_origin_canceled` и outcome `accepted`. Неуказанные meeting_id/deletion_request_id остаются NULL, что разрешает существующая модель/миграция0007 и подтверждает test_scope_acceptance. |
| Строгая безопасная metadata | PASS. `deletion/audit.py` добавляет только cancellation_id в список разрешённых ключей; его значение проверяется на UUID до общих правил bool/int/str/None и преобразуется через str(UUID). Строки, включая UUID-looking, None/bool/int/dict/list отвергаются отдельными unit cases. Остальные запреты ключей/значений сохранены. Origin, тело create, HTTP operation_id, содержимое или приватный путь не записываются. |
| Общая транзакция и отказ без подтверждения | PASS. Marker и audit используют один db, два flush и прежний endpoint commit после возврата helper; внутри helper нет commit/внешнего I/O. При ошибке audit flush ответ helper не возвращён, session не фиксируется. Integration test проверяет отсутствие обоих объектов в отдельной session после ошибки и последующий успешный create/новую отмену. |
| Идемпотентный повтор и первоначальное устройство | PASS. Для существующего marker добавления audit нет. Реально создан второй RegisteredDevice, две AuthSessionDeviceBinding и две сессии того же владельца; повтор с обеих сессий сохраняет receipt и полный snapshot исходного audit ID/workspace/actor/device/time/metadata. Late create обеих сессий отвергнут. Concurrent cancel test оставляет ровно один marker/audit. |
| Старые markers без вымышленной истории | PASS. В коде нет backfill/update/delete старого marker или аудита. Test предварительно сохраняет legacy marker без audit, повторяет cancel и проверяет исходные receipt/time/origin, отсутствие audit и сохранённый запрет позднего create. Старую неизвестную device identity исправление не фабрикует. |
| Прежние границы сохранены | PASS. Diff не меняет lock, lookup полного namespace, confirmation boundary, existing-Meeting ветку, общий create guard, HTTP auth/device/rate-limit, receipt schema, storage, processing, purge, retained observability или DDL. Расширенный restricted-role RLS test действительно записывает audit и не видит другой workspace; denied-device cases дают403 до marker/audit. |

Исходники общего create guard и двух callers, nullable FK, RLS0007/0092,
HTTP session/commit и зависимости были полностью исследованы в предыдущем
отдельном T008 обзоре; текущий diff и контрольные суммы подтверждают, что эти
неизменённые границы сохранены. Требования spec/plan/tasks/data-model/contracts
и конституция/guidance имеют те же хеши, что в непосредственно предшествовавшем
requirements review этого диалога; повторно проверены хеши и прочитан весь
checklist report с обязательным профилем. Исторические [X] в tasks не
использованы как замена приёмки.

## Самостоятельно проверенные доказательства

Все журналы прочитаны проверяющим; тесты запускал основной исполнитель.
Новые runtime-команды проверяющий не выполнял.

- `f262-t008-device-audit-red-20261022.log`: настоящий API/PostgreSQL case
  завершился FAIL именно на `assert len(events) == 1`, фактически0.
  Перед этим receipt202, повтор, lifecycle и late-create409 уже прошли.
  Ошибка исходного кода воспроизведена; это не отказ collection/setup/import.
- `f262-t008-device-audit-focused-20261022.log`: collected60,
  **60 PASS / 0 FAIL / 0 SKIP**, 56.55 s. В составе: origin15,
  scope4, migration3, metadata14, HX7, deletion-access1, local-purge8,
  sync-conflicts6, workflow-races2. Это один набор; вложенные группы не
  прибавляются к60 ещё раз. Журнал подтверждает удаление isolated container.
- `f262-t008-device-denied-20261022.log`: три дополнительно добавленных
  cases `revoked`, `pending`, `other_workspace` — **3 PASS**, 4.52 s,
  isolated container removed. Все три используют настоящую AuthSession и
  проверяют403/отсутствие подтверждения, marker и audit. Это отдельные cases,
  которые в прежние15 origin/60 общего набора ещё не входили.

Совокупность этих двух успешных запусков: **63 разных cases**, а не полный
прогон всего репозитория. Два предупреждения — pytest assert rewrite уже
загруженного fixture plugin и deprecation httpx/starlette; тестовых ошибок
или пропусков они не скрывают.

Для проверки отката инъекция ошибки установлена на SQLAlchemy
`before_insert` MeetingLifecycleAuditEvent. Она вызывает настоящий отказ
ORM flush в API request после flush marker, затем отдельная session видит
обе таблицы пустыми. Это достаточное доказательство требуемого атомарного
поведения при ошибке flush. Отдельный отказ SQL на стороне PostgreSQL,
потеря соединения или process crash здесь не моделировались и не называются
проверенными.

Restricted-role case сохраняет audit в текущем workspace после применения
TenantScope, проверяет actor/device/NULL FK, сохраняет запреты UPDATE/DELETE
marker и не видит audit другого workspace. В том же workspace журнал аудита
сохраняет прежнюю workspace-семантику RLS; новый owner-only RLS для всей
существующей audit таблицы этим изменением не заявляется и не вводится.

Существующий old-origin и controlled create/cancel interleavings code не
ослаблен; новые assertions scope test корректно заменяют прежнее ожидание
полного отсутствия audit на ровно одно настоящее cancellation event.
Отсутствие фиктивных Meeting/DeletionRequest/report/task/artifact/snapshot
по-прежнему проверяется отдельно. Это содержательное исправление тестового
инварианта, а не разрешение произвольных лишних объектов.

## Сверка с T008 и границы заключения

T008 отвечает за model/migration/common create guard. Исходный обзор подтвердил
полный namespace, UNIQUE/FORCE RLS, оба порядка cancel/create, запрет позднего
create до эффектов, сохранение прежнего deletion evidence при миграции,
preflight дублей и безопасный отказ downgrade. Единственным найденным
обязательным расхождением было отсутствие device audit из data-model.
Текущее минимальное исправление закрывает этот пробел без новой схемы;
миграционные3 вновь входят в успешный60-набор.

Тематические FR-008/009/014/019/021 и S10–S12/S27/S40/S50 в области этого
серверного среза согласованы. Дополнительная широкая переработка удаления,
универсальный журнал событий, второй storage/workflow или новая таблица
не требуются. Новых зависимостей и параллельного механизма нет; безопасных
обязательных сокращений в проверенном diff не найдено.

**Статус T008: реализация в проверенном локальном объёме принята независимым
ревью; окончательное закрытие #6883 пока не подтверждено.** Перед закрытием
нужны итоговые evidence/changelog основного исполнителя, новый commit SHA,
required governance-fast/macos-pr/pr-metadata на точных SHA и основе,
слияние и live validate-issue-closeout с подробным русским комментарием.
Старые проверки PR7722 не заменяют проверки нового продуктового commit.

Это не приёмка всей F262/всех51 GUI scenarios, установленного GRAF Dev,
сервисов production, нового выпуска, физического backup restore, старого
несовместимого клиента или полноты старого audit. Старые markers остаются
с прежним отсутствием исторической device identity, их защитный смысл
не меняется. Существующая admin проекция всех lifecycle events не получает
новый origin drill-down; отдельная такая UI-функция здесь не заявляется.

Проверяющий записал только этот файл. Checklist, код, тесты, spec, plan,
tasks, changelog, Git/GitHub, приложение и данные не менялись проверяющим.
Работа других участников сохранена.

## Контрольные суммы SHA-256

Контрольная сумма полного diff пяти проверенных файлов от9b286:
`64aebca224835e9a5d2285f163ead06fbc97e2a410876426471be305a4a8cee8`.

```text
b9717c97fc604033409060708c3558fef05ba5dc42b94ea9e2d609d7d6d53bf6  apps/server/src/twobrain_rec_server/deletion/audit.py
397ae1f4ce4d86e21dba7acaa860644fb8949675648a2217e9211bef78e399f7  apps/server/src/twobrain_rec_server/deletion/origin_cancellation.py
eef95fee0cb770598d1d3c24805cfaa643ccf952545f7918fd81492dedd07bed  apps/server/tests/integration/test_recording_origin_cancellation.py
75bd97cd928db216033cfe6de02dd97dacb4be21aa7ea6e83ce7fed91416e815  apps/server/tests/integration/test_recording_deletion_scope_acceptance.py
11db5c5cf6464536cd8a19bf5d0b9bb4991abb22e9249c92fa9baa210f97c2ed  apps/server/tests/unit/test_deletion_audit_metadata.py
fc535eaefb2eb265cae174508dcb06b548a3df3dc1f4bd54fb68a50d79ff4d27  apps/server/src/twobrain_rec_server/db/models/deletion.py
6ade5be83afcd81c29b944651c3a08ac1916e1f0a6b037277f4a744e23da886c  apps/server/src/twobrain_rec_server/db/migrations/versions/0007_retention_deletion_execution.py
52df617bd877cd5877aaab074633a2617d469fb06f5462106ca0416b2d4e9ceb  apps/server/src/twobrain_rec_server/db/migrations/versions/0092_recording_origin_cancellation.py
7c02907ed64464f4baffe2f87b2a9d48f8a65b250140d48222b9f1ea33a14aaa  apps/server/src/twobrain_rec_server/api/ingest.py
d0af070ed6316bb43f65b7bfce543dcff9873efd2549a73006a95a7dfaa93ffa  apps/server/src/twobrain_rec_server/ingest/meetings.py
c22d728d9d41a9346a8f17469946fa97cfbd888db6ad4f62452feab44538b976  apps/server/src/twobrain_rec_server/ingest/manual_media_upload.py
f64766bd86981a52c7d18019cd418a8d227756de02e234af1e1d28cf762e063d  specs/262-recording-deletion-lifecycle/spec.md
25d14d4fd41cbc9a7364805722a92173f8e3b93debdd9f30efbfae21e3542cb3  specs/262-recording-deletion-lifecycle/plan.md
f4ed5a207676dfa3fe7f2803c6fbcd447f2bc5faa49e812ba5617fa4c26175ce  specs/262-recording-deletion-lifecycle/tasks.md
0d3514d73303dd20c4e991b89ba6778de54a88cee5007a5b1684359f44a2367e  specs/262-recording-deletion-lifecycle/data-model.md
f0652db20a6369046802a78320c44f0fa7da1df506aed106d0790a724abc66ef  specs/262-recording-deletion-lifecycle/contracts/lifecycle.md
a1730b493e9ec27a63baa6c3b8f0e908a57b353fc975db4a056c790ac3e3a2b2  specs/262-recording-deletion-lifecycle/review-t008-audit-checklists-20261022.md
df6e1fe6ff9fa77802533413ef5ed00f4b738b1764fa3e1bcd9d68c06e84d50b  /Users/yshishenya/Documents/Codex/2026-10-21/issues-334-audit/f262-t008-device-audit-red-20261022.log
f1177436eab6d9a2c98fd880e8495492822e1ff6b1b71f5e96d8d1e0491ebed6  /Users/yshishenya/Documents/Codex/2026-10-21/issues-334-audit/f262-t008-device-audit-focused-20261022.log
176d60f81eaf83dc22cffbac93f8a8f700b1f9f91233a408be89effec9df9959  /Users/yshishenya/Documents/Codex/2026-10-21/issues-334-audit/f262-t008-device-denied-20261022.log
```
