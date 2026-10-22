# Независимая проверка требований T012 перед закреплением тестов

Дата: 2026-10-22. Проверяющий: `f262_requirements_reviewer`.
Фича/задача: F262/T012, [#6887](https://github.com/yshishenya/graf/issues/6887).
Ветка: `codex/262-lifecycle-lookup-audit`.
Исходный HEAD: `3758e61d723160d57a1702b58afd5e5c2bbed8c0`.
Исходное рабочее дерево чистое; feature pointer соответствует ветке/T012.
Порядок: независимая проверка reviewer-owned требований активной области
high-risk-feature до изменения существующего набора тестов. Новая фича,
изменение принципа или отдельное согласие пользователя не нужны.

## Решение и границы

**PASS качества требований.** requirements: 10 отмечено/0 не отмечено;
security-ux: 10 отмечено/0 не отмечено; всего 20/0. Каждый пункт рассмотрен
отдельно, итоговые чеклисты перечитаны. Обязательной неоднозначности,
противоречия конституции или неподтверждённого пункта требований не найдено.

Можно перенести три содержательные проверки из внешнего probe в существующий
`apps/server/tests/integration/test_recording_origin_cancellation.py` с
сохранением реальной AuthSession и trusted device binding. Код продукта в
планируемом объёме не меняется. Ревью окончательного переноса и его исполнения
будет отдельным этапом; этот отчёт не объявляет будущие тесты уже принятыми.

T010/T011 не являются текущей задачей. История их прежних обзоров в чеклистах
сохранена; её исторические формулировки FAIL не являются новым выводом о
текущем T012 или основанием переоткрывать завершённую работу.

## Проверенные основания области T012

- FR-002/004/007–009 разделяют неизвестность, доступ, авторитетное принятие и
  разрешение физической очистки. FR-019 сохраняет scope исполнителя; target
  creator — отдельная идентичность. По data-model identity origin определяется
  workspace+creator+local_recording_id, а право управляющего действует через
  meeting_id. Совпадающий origin другого владельца не становится собственным.
- Contract/Состояние собственных origins требует bounded lookup 1–100 и
  отсутствие content для denied/unknown. Для server-only/доступной чужой
  встречи используется meeting lookup с существующим access/lifecycle
  resolver. Unavailable закрывает контент, но не доказывает удаление.
- `RecordingLifecycleLookup` (`api/schemas.py:2505`) запрещает лишние поля,
  ограничивает суммарный origins+meeting_ids 1–100; UUID и размер origin
  проверяются схемой. `lookup_recording_lifecycle` (`ingest/desktop_sync.py:950`)
  исключает повторы отдельно в каждом списке, не вводит неограниченный обход.
- Own-origin lookup сначала проверяет cancellation строго по workspace,
  creator и origin (`deletion/origin_cancellation.py:29`), затем Meeting по
  тем же трём полям. Meeting lookup выбирает только текущий workspace.
- Live meeting проходит `decide_meeting_access`. Deleted meeting дополнительно
  проходит `authorized_lifecycle_meeting` (`cabinet/access.py:2412`): receipt
  доступен владельцу или текущему owner/admin пространства. Прежний share или
  обычное чтение не заменяют право lifecycle. Для lookup по meeting_id чужой
  origin не включается в receipt.
- API route (`api/ingest.py:590–604`) использует PrincipalDependency,
  DeviceDependency, tenant scope и существующую CSRF границу; ответ no-store.
  `_validate_tenant_scope` (`auth/dependencies.py:650–819`) заново проверяет
  membership, device, AuthSession и trusted binding; отзыв членства не
  обходится тем, что сессия была выпущена раньше. Expected actor/workspace
  проверяются отдельно от переданных идентификаторов объектов.

Эти исходники прочитаны для подтверждения связи требований с планируемыми
проверками. Обзор не является финальной приёмкой всей реализации T012.

## Каждый пункт requirements

| Пункт | Основание для текущей области | Итог |
| --- | --- | --- |
| Пользовательское поведение | US5 и FR-002/007/009/019 задают доступный результат и запрет ложного удаления, а не тестовый механизм | PASS |
| Ценность, приоритеты, границы | US5/P1 защищает другое устройство и доступ; T012 ограничен существующим lookup и текущими правами | PASS |
| Обязательные секции | spec содержит US, FR, SC, Edge Cases, Assumptions, Clarifications; plan/data-model/contract/tasks определяют T012 | PASS |
| Нет обязательных уточнений | Для origin и meeting пути уже различены; receipt требует lifecycle manager, denied/unknown не являются удалением | PASS |
| Однозначная проверяемость | Из одного запроса однозначно проверяются state, receipt, отсутствие content и scope; grant/membership отзываются между повторными запросами той же сессии | PASS |
| Измеримый успех | SC-001/003/005 задают отсутствие восстановления и границу активного подключения; bounded 1–100 измеримо без обещания недоступному клиенту | PASS |
| Положительные/отрицательные/конкурентные сценарии | S24/S27–S29/S37–S40/S46/S49–S51 покрывают remote delete, смену контекста, denied, manager и origin cancellation; общий create/cancel остаётся в прежней матрице | PASS |
| Предположения и пределы | FR-018/022 и contract/Purge различают серверное подтверждение, Mac, offline, retained observability и rollback; тесты не расширяют полномочия очистки | PASS |
| Предложение/код/доказательство | Текущие 6 integration отдельно от исторических 11 schema cases и будущего переноса; полный UI/release не заявлен | PASS |
| Конституция/MVP | Constitution II/III/IV/VI и product-gates требуют явный Stop, доступ, metadata-only evidence и честное удаление; новый продуктовый механизм не вводится | PASS |

## Каждый пункт security-ux

| Пункт | Основание для текущей области | Итог |
| --- | --- | --- |
| CHK001 | data-model/Идентичность и FR-009/019: execution actor отдельно от creator; origin owner-only, manager через meeting_id; local_unbound не присваивается серверу | PASS |
| CHK002 | FR-002/004–008: allowed/unavailable не равны deletion_accepted; неподтверждённый исход не даёт receipt/очистку | PASS |
| CHK003 | FR-008/021, S10–S14 и contract/origin: cancellation подтверждает запрет позднего create; lookup не создаёт Meeting | PASS |
| CHK004 | FR-007/013/014 и contract/Purge: для cleanup требуется авторитетное основание; unknown/denied не дают его, late ACK остаётся отдельным | PASS |
| CHK005 | FR-010–012/017, US4 и S18–S23/S41 определяют frozen selection, результаты и фокус; перенос API-тестов эти требования не меняет | PASS |
| CHK006 | Contract/origins+meeting lookup, SC-003, S24/S28/S46/S51 прямо определяют remote delete, право доступа и offline/unavailable границы | PASS |
| CHK007 | FR-015/018 и contract/Плеер сохраняют управляемый preview, внешние копии и retained observability; lookup выдаёт только технические поля | PASS |
| CHK008 | FR-019/020/022, S27/S37–S40/S47 требуют scope fences, безопасное восстановление и совместимость; серверная/клиентская миграция тестами не вводится | PASS |
| CHK009 | SC-002/003/006 отделяют получение подтверждения, активное подключение и время очистки; 3 API-прогона не выдаются за измерение UI или p95 | PASS |
| CHK010 | FR-016, S15/S16 и Constitution II сохраняют ручной Stop и запрет скрытого delete active/saving; lookup не управляет capture | PASS |

## Прочитанные доказательства и обязательные условия переноса

Внешний `test_f262_lookup_access_recheck.py` содержит 3 разных теста:

1. В той же настоящей сессии: чужой origin недоступен; grant разрешает meeting
   projection; отзыв grant немедленно возвращает unavailable; после удаления
   обычный читатель не получает receipt; текущий admin получает accepted
   receipt исходного deletion request без чужого local_recording_id.
2. Синтетические Meeting и cancellation перенесены в другой workspace:
   запрос прежнего scope не раскрывает их — unavailable, receipt/meeting_id nil.
   Это изолированная подготовка fixture, не миграция пользовательских данных.
3. Отзыв membership после успешного чтения тем же AuthSession блокирует
   следующий запрос 403 workspace_scope_denied до выдачи receipt.

Прочитан журнал `f262-t012-session-access-current-20261022.log`: 3 PASS,
0 FAIL / 0 SKIP; штатный runner сообщает удаление изолированного PostgreSQL
контейнера. Настоящие AuthSession выдаются через `issue_auth_session`,
создаётся trusted AuthSessionDeviceBinding, а не подставляется произвольный
user header. Проверены no-store и отсутствие title/transcript в ответе.

В отдельном `f262-t012-existing-on-3758e61d7-20261022.log` ещё 3 существующих
integration PASS: bounded mixed lookup; unavailable без receipt с доступной
следующей целью; origin-only receipt без фиктивных Meeting/purge FK. Это
**6 разных текущих integration-тестов**, без добавления прежних 3 диагностических
header-based случаев, исторических 11 проверок схемы или повторного подсчёта
общих pytest итогов. Журналы не содержат доказательства всего S01–S51.

При переносе требуется сохранить:

- настоящую session/trusted binding и повторные запросы после отзыва прав;
- различие owner-origin и meeting manager без подмены creator identity;
- точные отрицательные assertions отсутствия receipt/content и положительные
  assertions исходного request_id/accepted, без ослабления до одного HTTP 200;
- синтетические fixture, штатную изоляцию БД/очистку и отсутствие пользовательских
  данных/сессионных токенов в отчётах;
- существующую суммарную границу 1–100, неизвестность без purge и no-store;
- исполнение окончательно перенесённых тестов и отдельное независимое ревью
  текущей дельты до дальнейшей приёмки.

Новых обязательных продуктовых решений или оснований изменить spec/plan/tasks
при этой проверке не найдено. До PR-проверок нового точного SHA/основы,
слияния и итоговой сверки issue остаётся открытой. Старый CI PR #6911 и
чужой завершённый T010/T011 не заменяют новое доказательство T012.

## Источники и SHA-256

Полное чтение требований уже выполнено в этом же диалоге; перед повторным
использованием все следующие документы сверены по SHA-256 с предыдущим
полным чтением, содержимое совпало. Изменённый документ таким образом не
пропускался. Ссылки и требования оригиналов остаются источником правды.

| Путь относительно корня репозитория | SHA-256 |
| --- | --- |
| `AGENTS.md` | `24c0767f2223bb21e969079ec1ec09e0dec7c3fd3d85d02e78832f17e0775958` |
| `.specify/memory/constitution.md` | `7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8` |
| `docs/agent-guidance/README.md` | `2f3e0339a89d3ccdf0878026920955a189584d6a985116b069584cd78b3c75bb` |
| `docs/agent-guidance/document-reading.md` | `5263860b1974df022826ac81c2482e6ee92100bc0bb718ab5a29b32e2422e411` |
| `docs/agent-guidance/spec-kit-flow.md` | `afb816ce48624eb79fcd7fd44d09f0986296e87ef1cfecd790228ac70a5b9b9e` |
| `docs/agent-guidance/product-gates.md` | `9f7072c879490d250053cb7397ad6b9b68fdcde17bdf9367ed874a41e450b5f5` |
| `docs/prd-voice-layer-final.md` | `0f3ccfcfa60062bb0aae6802eeb0012056a635a30cb9f46f54d1992d0b4f57c2` |
| `docs/current-product-status.md` | `25b7f383be47c7160da8e852006ff82019f30a5f9c371fc30baa79238649cd16` |
| `specs/262-recording-deletion-lifecycle/spec.md` | `f64766bd86981a52c7d18019cd418a8d227756de02e234af1e1d28cf762e063d` |
| `specs/262-recording-deletion-lifecycle/plan.md` | `25d14d4fd41cbc9a7364805722a92173f8e3b93debdd9f30efbfae21e3542cb3` |
| `specs/262-recording-deletion-lifecycle/tasks.md` | `f4ed5a207676dfa3fe7f2803c6fbcd447f2bc5faa49e812ba5617fa4c26175ce` |
| `specs/262-recording-deletion-lifecycle/data-model.md` | `0d3514d73303dd20c4e991b89ba6778de54a88cee5007a5b1684359f44a2367e` |
| `specs/262-recording-deletion-lifecycle/contracts/lifecycle.md` | `f0652db20a6369046802a78320c44f0fa7da1df506aed106d0790a724abc66ef` |
| `specs/262-recording-deletion-lifecycle/research.md` | `696aeff0f6dfe2da78cbd5a702eb5f57a32fd187011a114083b1cc2b9d7a636b` |
| `specs/262-recording-deletion-lifecycle/analysis.md` | `3c2ead5b0cfbf492d8c95c8a26b59b8dcd6d11accc872a9e997512d0077af4da` |
| `specs/262-recording-deletion-lifecycle/scenarios.md` | `29df91c40b00227e6f682394e4a1f5b0fdc8a426b7c734591a934fab72cb434b` |
| `specs/262-recording-deletion-lifecycle/quickstart.md` | `a728d664177055ad0544c3a2f1b72eee209805ce2612472ca4b2795bdedb2bb0` |
| `apps/server/src/twobrain_rec_server/ingest/desktop_sync.py` | `ba2b9ffab87f7b19a8a3cd47dc7ab15b693a3b8bcbae0a6f720eedc06f43863d` |
| `apps/server/src/twobrain_rec_server/api/ingest.py` | `7c02907ed64464f4baffe2f87b2a9d48f8a65b250140d48222b9f1ea33a14aaa` |
| `apps/server/src/twobrain_rec_server/api/schemas.py` | `572e9df589572edc382005d512f65037e082d2a080b0ed9f4da4437f0a34f539` |
| `apps/server/src/twobrain_rec_server/cabinet/access.py` | `12c96ecbbada2d3bb027f29b711a038fdf1e0f4cad050c7c2184b089d0f3afb4` |
| `apps/server/src/twobrain_rec_server/auth/dependencies.py` | `559bcc1c46cdf49cd283d8a199e089fc7047401b669c0ab17ae9b6d98c94d311` |
| `apps/server/src/twobrain_rec_server/deletion/origin_cancellation.py` | `397ae1f4ce4d86e21dba7acaa860644fb8949675648a2217e9211bef78e399f7` |
| `apps/server/tests/integration/test_recording_origin_cancellation.py` | `eef95fee0cb770598d1d3c24805cfaa643ccf952545f7918fd81492dedd07bed` |

| Внешний источник | SHA-256 |
| --- | --- |
| `test_f262_lookup_access_recheck.py` | `07814d53703b06e4f09da42c2d1c737b6d77d342bba5e5d4604e17fe35f3bb24` |
| `f262-t012-session-access-current-20261022.log` | `5d3d321f83569381a14315c61bb8e8eeae4e7bdb78b6577df14156596736df82` |
| `f262-t012-existing-on-3758e61d7-20261022.log` | `914b8b9a77775269d9e5b52afc7bb034de210b789111d24c8b860f22954fabe5` |
| `f262-t012-session-access-recheck-20261022.json` | `717fd85e8ae1509e2094fc9e6bcb16c5f3cf1055ae026455884b62537f3d0be9` |

Прочитана текущая issue #6887 с критериями и 3 комментариями, состояние OPEN.
GitHub не изменялся. Собственные исполняемые проверки не запускались.
Приложение, пользовательские данные, код продукта и тесты проверяющий не менял.
Разрешённые изменения: только оба чеклиста и этот отчёт. История сохранена.
Форматирование проверяется `git diff --check`; это не CI/приёмка продукта.
