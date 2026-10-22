# Независимая итоговая проверка тестов F262/T012

Дата: 2026-10-22. Проверяющий: `f262_requirements_reviewer`.
Задача: [#6887](https://github.com/yshishenya/graf/issues/6887).
Ветка: `codex/262-lifecycle-lookup-audit`.
Исходный HEAD: `3758e61d723160d57a1702b58afd5e5c2bbed8c0`.
Область: окончательная незакоммиченная дельта
`apps/server/tests/integration/test_recording_origin_cancellation.py`.
Порядок: active Spec Kit slice существующей high-risk-feature F262; это
закрепление проверки доступа и удаления в существующем наборе, код продукта
не меняется. Применён навык `code-reviewer`.

## Решение

**PASS окончательного переноса и профильного локального доказательства.**
Блокирующих замечаний, ослабления прежних проверок, нового обхода авторизации
или возвращения удалённого legacy-механизма в проверенной дельте нет.

Проверен окончательный файл с SHA-256
`b798aea82c9512683a856c8864eff0e832020bb6b35568591dc5ba4d6db91252`.
Три сценария сохранены из внешней проверки, добавление границы запроса
соответствует действующей схеме. Требования ранее приняты отдельным обзором
[review-t012-lookup-checklists-20261022.md](review-t012-lookup-checklists-20261022.md),
20 подтверждённых / 0 неподтверждённых пунктов. Этот итоговый обзор не меняет
чеклисты и не объявляет весь F262 заново проверенным.

## Сопоставление с исходной проверкой

Полностью прочитаны текущий тестовый файл, его `git diff` и внешний
`test_f262_lookup_access_recheck.py`. Дополнительно выполнено сравнение AST
(структуры Python-кода без исполнения тестов):

- `_lifecycle_session_headers` идентичен прежнему `session_headers` после
  переименования; выдача через `issue_auth_session`, сохранение сессии и
  `AuthSessionDeviceBinding(device_state="trusted")` не ослаблены.
- `test_lookup_reauthorizes_share_revocation_and_lifecycle_manager` и
  `test_lookup_rejects_revoked_workspace_membership` идентичны исходным после
  переименования помощника и раскрытия константы URL.
- В `test_lookup_filters_other_workspace_meeting_and_cancellation` подготовка
  отмены заменена на существующий `cancel(client, origin)`: тот же endpoint,
  новый UUID операции, то же подтверждение `BOUNDED_DELETE_COPY`, тот же
  ожидаемый HTTP 202. Остальное тело структурно идентично.
- Не удалена ни одна прежняя функция. Все прежние функции структурно
  неизменны, кроме дополненного
  `test_lifecycle_batch_returns_metadata_receipts_and_bounds_selection`;
  его исходное тело целиком сохранено неизменным префиксом.

## Что проверено по исходникам

| Область | Основание | Итог |
| --- | --- | --- |
| Настоящая сессия | Помощник на строке 523 получает токен из `issue_auth_session`, записывает доверенную привязку к реальному синтетическому зарегистрированному устройству и commit; наружу передаёт `X-Auth-Session` и expected actor/workspace | PASS |
| Нет подмены читателя заголовками | Новые lookup-запросы не передают `X-User-Id`/`X-Workspace-Id`/`X-Device-Id`; `get_principal` сначала разрешает session token, `get_device_context` берёт контекст сессии; `_validate_tenant_scope` проверяет текущие membership/device/session/trusted binding | PASS |
| Отзыв grant в той же сессии | `reader_headers` создан один раз до первого lookup; grant, revoke, deletion и повышение текущей роли происходят между повторными запросами с теми же headers | PASS |
| Чужой origin и доступная встреча | До grant обе цели unavailable без receipt/meeting_id; grant открывает только meeting; после revoke полное равенство исходному denied; admin получает только meeting receipt, без чужого local_recording_id | PASS |
| Receipt удаления | Проверяются deletion_accepted, phase accepted и исходный request_id ответа удаления; обычный читатель после удаления остаётся denied | PASS |
| Отзыв membership в той же сессии | После allowed один раз выданные `reader_headers` повторно используются после commit status revoked; ожидаются HTTP 403, workspace_scope_denied и отсутствие receipt | PASS |
| Отсутствие содержимого | Общий lookup-помощник на каждом шаге проверяет no-store, отсутствие title/transcript; denied проверяет receipt/meeting_id None; после revoke/deletion сравнивается весь ответ с denied | PASS |
| Другая область workspace | Только синтетические Meeting и RecordingOriginCancellation перемещаются в уже существующий fixture workspace; запрос из исходного scope даёт ровно три unavailable без receipt/meeting_id | PASS |
| Суммарная граница и повторы | 50 одинаковых origins + 50 одинаковых meeting_ids проходят и дают две исходные metadata entries; 50+51 отвергаются до устранения повторов | PASS |
| Невалидные входы | Пустой набор, лишнее поле, неверный UUID, пустой и 241-символьный origin дают 422 без поля receipt | PASS |
| Изоляция и совместимость набора | Используются существующие client, create_ready_meeting, add_workspace_user и grant_meeting_to_user; прежние concurrency/RLS/audit тесты сохранены; новый framework/глобальный override не добавлен | PASS |

Чтение связывающих исходников: `auth/dependencies.py:391–541,650–819`,
`auth/sessions.py:164–197`, `api/ingest.py:590–604`,
`api/schemas.py:2505–2525`, `ingest/desktop_sync.py:950–1032`;
`tests/conftest.py` (подготовка БД, создание приложения и client),
`tests/fixtures/cabinet.py:77` и `tests/fixtures/cabinet_access.py:56–158`.
В прочитанном пути client создаётся настоящее приложение; новый перенос не
добавляет замен зависимостей авторизации. Fixture-изменения относятся только
к изолированной тестовой БД. Перенос связанных строк между пространствами
не является процедурой миграции или проверкой согласованности всех дочерних
таблиц; его цель здесь — отрицательная проверка трёх lookup-целей.

Исходные вспомогательные действия подготовки `cancel`/удаление владельцем
используют существующий `auth_headers()`, как и внешний исходник. Это не
новый путь исполнения продукта и не подмена session-проверок читателя.
Новый lookup использует реальную сессию, включая дополнение границы.

## Исполненное доказательство

Полностью прочитан окончательный журнал
`f262-t012-final-permanent-tests-20261022.log`:

- collection_count=23;
- collection_digest=`f2a1d1b3bc1261d743477f58f9e8b4ae61d08a338ffd4e5e7caf4b059e11479a`;
- **23 passed, 0 failed, 0 skipped**, 18.85 секунды pytest;
- runner: focused, 4 worker, partitioned=false, result=pass;
- cleanup: `isolated_container_removed`.

Состав: 17 тестовых функций текущего файла дают 21 случай с параметрами;
ещё два существующих случая проверяют unavailable deletion target и
origin-only receipt без фиктивных Meeting/purge FK. Журнал показывает также
исполнение трёх новых сценариев и дополненного bounded case.

Предыдущий `f262-t012-permanent-tests-20261022.log` тоже показывает 23 PASS,
но стартовал до дополнения границы; он историческое промежуточное
доказательство. Итог — **23 разных случая**, а не сумма повторных запусков.
Исторические внешние/схемные проверки к этому числу не прибавлены.

Два предупреждения относятся к уже импортированному pytest fixture plugin и
объявленному устаревании httpx transport в Starlette TestClient. Прогон
завершён успешно; перенос не меняет эти зависимости.

Проверяющий не запускал исполняемые проверки самостоятельно. Он прочитал
журналы штатного runner основного агента, проверил текущие исходники и их
хеши; сравнение AST не исполняет тесты или приложение. Текстовый журнал не
заменяет будущую проверку GitHub точного SHA и текущей основы.

## Ограничения следующего шага

Этот PASS относится к перечисленной дельте тестов и прочитанным профильным
доказательствам на исходном HEAD с указанным рабочим файлом. Он не заменяет
новый commit/PR, обязательные governance-fast/macos-pr/pr-metadata точного
SHA и основы, слияние и итоговую live-проверку закрытия #6887.

Проверка не доказывает исполнение всей S01–S51, установленную macOS-приёмку,
публичную поставку, production или сквозную очистку пользовательских файлов.
T010/T011 остаются исторически завершённой соседней работой.
Проверяющий не изменял код, tests, spec, plan, tasks, checklists, governance,
Git/GitHub, приложение или данные. Его единственная запись — этот отчёт.
`git diff --check` прошёл; это проверка форматирования, не CI продукта.

## Источники и контрольные суммы

Хеши сняты с фактических файлов окончательного просмотра. Для связывающих
исходников выше перечислены прочитанные разделы; весь feature/release scope
этот ограниченный обзор повторно не принимает.

| Путь относительно корня | SHA-256 |
| --- | --- |
| `apps/server/tests/integration/test_recording_origin_cancellation.py` | `b798aea82c9512683a856c8864eff0e832020bb6b35568591dc5ba4d6db91252` |
| `apps/server/tests/conftest.py` | `5cad4be139be77c18e6810387167da90c317732a7269c88949a8b87b41f46f8a` |
| `apps/server/tests/fixtures/cabinet.py` | `429e04f5f01bd5373d3b139f8d985cdb2f9542c663d95e082beccf06a8091d92` |
| `apps/server/tests/fixtures/cabinet_access.py` | `e34a4847406c614f41469ca93e1096d62cbbcacc8c910c62334c7550dd524610` |
| `apps/server/src/twobrain_rec_server/auth/dependencies.py` | `559bcc1c46cdf49cd283d8a199e089fc7047401b669c0ab17ae9b6d98c94d311` |
| `apps/server/src/twobrain_rec_server/auth/sessions.py` | `c94996ff2a4be814f43f502d7bc2f3fc925909311686d437aad32d7c9f528aab` |
| `apps/server/src/twobrain_rec_server/api/schemas.py` | `572e9df589572edc382005d512f65037e082d2a080b0ed9f4da4437f0a34f539` |
| `apps/server/src/twobrain_rec_server/api/ingest.py` | `7c02907ed64464f4baffe2f87b2a9d48f8a65b250140d48222b9f1ea33a14aaa` |
| `apps/server/src/twobrain_rec_server/ingest/desktop_sync.py` | `ba2b9ffab87f7b19a8a3cd47dc7ab15b693a3b8bcbae0a6f720eedc06f43863d` |
| `specs/262-recording-deletion-lifecycle/review-t012-lookup-checklists-20261022.md` | `b1c416ff6d7305d9ef8ada3ba3ef8e9f380a2ae10a4087eb43e9a9a596dd974b` |

Внешние файлы находятся в
локальном реестре доказательств `issues-334-audit/`; путь рабочей машины
в репозиторий не включается.

| Внешний источник | SHA-256 |
| --- | --- |
| `test_f262_lookup_access_recheck.py` | `07814d53703b06e4f09da42c2d1c737b6d77d342bba5e5d4604e17fe35f3bb24` |
| `f262-t012-final-permanent-tests-20261022.log` | `4fbcb1aaec900923b3d7165d5124cfd49cfaefd331fb03ae628e135acfae3273` |
| `f262-t012-permanent-tests-20261022.log` | `757ac61da1d3bb4f15073496e1c116d2a1dc58e54e0eb4c2dcedd077fad0da4e` |
