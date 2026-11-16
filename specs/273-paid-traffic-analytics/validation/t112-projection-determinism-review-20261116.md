# T112 — независимое ревью реализации трёх общих tie-break

16.11.2026. Проверяющий `/root/public_counter_readiness_review`.
Копия `/private/tmp/graf-f273-result-visibility-20261116`.
Основа HEAD `eea992190c92e57b2cceaa199c2bcbd94ff71614` плюс проверенный локальный diff.
Полоса: implementation review существующего high-risk-product F273/T112.
Разрешённая запись проверяющего — только этот новый отчёт.

## Решение

**SCOPED IMPLEMENTATION PASS; P1=0/P2=0.** Реализованы ровно три принятых
общих tie-break. Обнаруженных препятствий к принятию этого среза нет.
PASS распространяется на определённый выбор workflow/dependency/activity
и прочитанные причинные испытания; это не приёмка будущего materialization
budget guard, HTTP, T113, рабочего измерения/T0, выпуска, трафика или продаж.

Собственный DESIGN PASS295ce2c… и прежний HOLDb3f534… не переписаны.
Прочитан новый полный request, весь diff, все127 строк нового теста, affected
callers и fixture setup/seed; восстановлены применимые оригиналы result-visibility
§3 и PRD§23. Сам проверяющий тесты не запускал. Ни294, ни257/native2 не повторял.

## Проверенный код и воздействие

- Workflow LATERAL в общем `_prefetch_meeting_review_reads`: после прежних
  attempt_ordinal DESC/created_at DESC добавлен только ProcessingWorkflow.id DESC.
- Dependency LATERAL того же helper: после updated_at DESC добавлен только
  ProcessingDependencyState.id DESC.
- Общий activity_response: после created_at DESC добавлен только
  MeetingEgressAuditEvent.id DESC, прежний LIMIT50 сохранён.

Ни фильтры, ни joins, ни выбранные поля/лимиты/параметры не менялись.
При разных старых sort keys приоритет прежний; при равных определяется PK.
Прошлый неопределённый tie может дать другую metadata-строку — changelog
это честно оговаривает. Авторизация и отсутствие содержимого в activity view
сохранены; большой unused metadata_json в тесте намеренно всё ещё читается,
поскольку byte guard этим изменением не вводится.

В исходниках подтверждено: общий get_cabinet_meeting_review вызывает
`_prefetch_meeting_review_reads`; самостоятельного аналитического latest reader нет.
activity_response используется API `/cabinet/meetings/{meeting_id}/activity`
после прежних `_authorized_meeting`/can_share checks и общим combined activity.
Последний уже сортирует по `(created_at,str(event_id)) DESC`; для PostgreSQL
UUID ascending/descending лексикографический canonical UUID string сохраняет
тот же порядок байтов. Новый SQL tie-break согласован с последующим общим
срезом50. Calendar activity order не менялся.

Соответствие result-visibility§3 сохранено: shared renderer/verifier используют
один getter; transcript/effective-result order, selected source и default/pinned
outcome pointers не менялись. Изменение касается определённости трёх metadata
выборок. Публичные страницы/контент/вёрстка и формат proof/admission не затронуты.
Новый пункт changes/unreleased/F273.yaml соответствует этому ограничению и
прямо сообщает об отсутствии JSON guard/HTTP подключения/рабочей аналитики.

## Проверка причинных тестов и происхождения результата

Новый файл вызывает настоящий prefetch и activity_response, без подставленного
готового решения. Fixture postgres_seeded_database_url поднимает миграции через
prepare_schema/Alembic head, сбрасывает mapped tables и заново создаёт тестовый
контекст. Используемый _seed_source создаёт synthetic source/result/workflow;
_run использует отдельный AsyncEngine с NullPool и dispose в finally.
Это настоящие SQL/model запросы, но не production/RLS/end-to-end admission.

5 workflow случаев проверяют равные ключи и обе прежние оси приоритета;
3 dependency случая — равное/раннее/позднее updated_at. Новые значения
размещены в допустимых разных rows, schema uniqueness не обходится.

Activity случай создаёт51 tied event, более новое событие с маленьким UUID
и более старое с максимальным UUID. Поэтому ошибочное перемещение id перед
created_at тоже обнаруживается. Один tied event содержит большой synthetic
JSON. В одной RR сессии создаётся только fixture index; rollback/close удаляет
его и SET LOCAL planner settings. Публичный listener do_orm_execute захватывает
реальный ORM SELECT, после вызова снимается finally. EXPLAIN построен именно
по захваченному statement; тест требует Seq Scan в одном проходе и Index Scan
в другом и в обоих сравнивает полный ожидаемый упорядоченный список50 IDs.
Это сильнее проверки одного текста ORDER BY или только длины списка.

`capture(state, statements=statements)` устраняет loop closure B023: каждый
listener пишет в список своего прохода. Прежний GREEN был до этой единственной
правки теста; конечный regression уже включает прочитанный исправленный файл.
Ruff PASS сообщён исполнителем; reviewer lint повторно не запускал.

| Прочитанный журнал | Завершённый результат | Предел доказательства |
| --- | --- | --- |
| determinism-red | 3 failed/6 passed,1 прежний warning,5.54s; runner9s, cleanup removed | Ровно workflow tie,dependency tie,activity order дают AssertionError до правок; остальные приоритеты уже проходят |
| determinism-green | 9 passed,1 прежний warning,5.82s; runner9s, result pass, cleanup removed | Три правки устраняют причинные отказы; запуск предшествовал единственной поздней правке default argument listener |
| determinism-regression | 61 passed,1 прежний warning,111.40s; runner116s, result pass, cleanup removed | Окончательный новый файл + result-view projection + cabinet detail/query-budget профиль |

У RED проверены начало, три конкретных AssertionError и итоговая сводка;
442 строки traceback не выдаются за новое полное чтение всех внутренних frame.
GREEN и33 строки окончательного regression прочитаны полностью. Основной
исполнитель отдельно подтвердил terminal session84612 EXIT0; reviewer читал
завершённый файл, не запускал/не опрашивал ту executor session самостоятельно.
Неопределённый running tail за PASS не принят. Warning прежний
PytestAssertRewriteWarning tests.fixtures.postgres_test_database.

Исходные source hashes из HEAD независимо совпали с baseline DESIGN report:
queries cf0e7b…; egress4f31ab…. Текущие code/test hashes совпадают с новым
request. Сам журнал не содержит source-hash manifest; привязка финального
regression к конечному файлу — подтверждение исполнителя плюс текущая сверка,
а не отдельный reviewer rerun/exact-SHA CI. Commit/CI этим не заявляются.

## Дополнительные PG witnesses и оставшийся объём

Прочитаны оба полных коротких probe журнала; hashes совпали с request.
Envelope probe подтверждает один RR backend/snapshot: legacy Seq/Index выбирают
разные tied sets с raw bytes350 и262495, а order date/id — один набор.
Whitespace JSON имеет raw262152 при normalized row15; duplicate keys raw264007
при15. Shape probe подтверждает overwritten early subtree: raw depth33 против
jsonb depth1; в другом случае raw6002 nodes против normalized2 при36007bytes.
Журналы явно сообщают application_guard_tested=false и production_used=false,
а также удаление собственных контейнеров.

Это причинное подтверждение оснований следующего guard, не его реализация.
Ограничения исходных JSON bytes до нормализации и raw depth/nodes остаются
обязательными. Они не закрываются тремя ORDER BY или большими JSON fixtures.
Обычная30–60мин встреча/общий2s/250ms lock/500ms statement, cumulative caps,
Session interception, реальный writer freshness, HTTP issuance/renewal и
атомарность пары сохраняются отдельными последующими проверками. Длительности
интеграционных fixture тестов не выдаются за измеренный2s аналитический POST.

Нынешний срез можно принять как завершённую правку shared ordering. Следующий
допустимый код — ранее принятый raw-byte/raw-shape числовой Session guard с
отдельными причинными RED/GREEN и независимым implementation review.
Настоящий T113/verifier и HTTP остаются закрытыми; этот отчёт их не открывает.

## Требования и сохранность

18 прежних requirements/review inputs сверены по SHA-256: все SAME относительно
собственного прежнего чтения. Checklist totals сохранены16/0+27/0+52/0+29/0=
**124/0**, reviewer-owned отметки не менялись и заново полным ревью не объявлялись.
Других необходимых продуктовых вопросов/изменений spec/plan/tasks не найдено.

Reviewer создал только этот отчёт. Не менял чужие tracked/untracked файлы,
код/tests/changelog, spec/plan/tasks/checklist, Git/GitHub, runtime/данные,
сайт, почту Postal, соседние службы, nginx/DNS/Compose, сбор/T0 и публикации.
Новых агентов не создавал. Новые тесты, сборки или PostgreSQL пробы не запускал.

## Точные контрольные суммы

| Проверенный файл/журнал | SHA-256 |
| --- | --- |
| `apps/server/src/twobrain_rec_server/cabinet/queries.py` | `a640ce364222d12e1a6ac71b5b569624ab21d8b954daa185526f50b51917fb9f` |
| `apps/server/src/twobrain_rec_server/cabinet/egress.py` | `8927113308b076e81a7e2c6343ae9c6634eb5e833aee54f5a9d348c96b932bf5` |
| `apps/server/tests/contract/test_result_projection_determinism.py` | `2c0b6809a0819b81d00c3fd644dabcc921394009ec019f6b1d8636dfeed20183` |
| `changes/unreleased/F273.yaml` | `dc0e677bffae5773997c72a6f0ff9f8470854823ede96007edfeb13b1a88faaf` |
| `apps/server/tests/contract/test_result_visibility.py` | `27bd0f0876bc2fbc43a50165abd354d57629309aebce350fb2d35e3643f321ff` |
| `apps/server/tests/contract/test_result_view_projection.py` | `9926f1c3e0941ee961c63663f80b245c06c3771a2c7a3df3a9c2392a4ff2b15c` |
| `apps/server/tests/integration/test_cabinet_meeting_detail_query_budget.py` | `730ab32ab05154542ce231d8f76c182f46ab8aec11ac981cd5dca1281aa0e9a3` |
| `apps/server/tests/conftest.py` | `0a8a2cb767b2f74e777fcb0c79616e68c65b0bf5a9ad5418838a4a0693389793` |
| `apps/server/tests/fixtures/postgres_test_database.py` | `9975596c2901035e2f58fe16481a19d1bc4d3924e8b3a00b1da69cfe80df505b` |
| `specs/273-paid-traffic-analytics/validation/t112-projection-determinism-preflight-20261116.md` | `295ce2c82c8638ddb9df1fbd5d478f0fefa53ea4b13ef34b6a3b760378a10326` |
| `specs/273-paid-traffic-analytics/validation/t112-projection-budget-preflight-20261116.md` | `b3f5344650831ed104af19a108bbc870de0813659723f3ca44f644b5302f2356` |
| `/private/tmp/graf-t112-projection-determinism-red-20261116.log` | `536d0165b9f830f7c7e2f0aeb5a19f22a642fa673d7feb5295c44593d41c51f3` |
| `/private/tmp/graf-t112-projection-determinism-green-20261116.log` | `1086a7ed1ad75672c3cf1282ddeb1fd0ba6676e29e1cf1abfa88fb99372598ff` |
| `/private/tmp/graf-t112-projection-determinism-regression-20261116.log` | `3debdf33cb353b79e18f6d34f9b77cf15f87ed008ab7dae43dcde9bf2184ec2e` |
| `/private/tmp/graf-t112-projection-envelope-probe-20261116.log` | `0ca6bde69f9039af466762ba67d25eb3720c9cf23d97eb757916f1c8176fc893` |
| `/private/tmp/graf-t112-json-shape-probe-20261116.log` | `5dd8bdc5e83b7d5dbeee04f9c4338e939b4a72858ad5889a0781698db76cd79f` |

Неизменные18 requirements/review inputs:

| Путь | SHA-256 |
| --- | --- |
| `specs/273-paid-traffic-analytics/spec.md` | `a7f23904625df9b06aed1e09c05f2ffa75ec3e5ec9ac0eda0531cd88c949c645` |
| `specs/273-paid-traffic-analytics/plan.md` | `5207a988f666c47f65203718a1212cf352312009f1c3804163abd093318a8b3c` |
| `specs/273-paid-traffic-analytics/tasks.md` | `3870e4d091557e0c40dd5500aa8fb5932b933cfe877e684c930d7f7e4f93a7d5` |
| `specs/273-paid-traffic-analytics/quickstart.md` | `4f2488aa98a3fba478eed042304279f408dc2530bd3f2b0449cedabaf39dd074` |
| `specs/273-paid-traffic-analytics/research.md` | `64caef3d9a78f0021c2b37ca86e0f388724bf117e899bd044f4ca557a1ba094f` |
| `specs/273-paid-traffic-analytics/data-model.md` | `478c18546d1240c4a1c15c5b07e76f7aeb551082273b75bc1fbf4cdd8d1ae8ab` |
| `specs/273-paid-traffic-analytics/contracts/activation-milestones.md` | `4835c0c6672a464366c9657d9285b28429ec2ed4d4e234c0c4897a65ed5027c4` |
| `specs/273-paid-traffic-analytics/contracts/result-visibility.md` | `ee1005b6a59ad1b42f0b7d0af25dd7099c8337a4d11930a3aba9ee6479d270d8` |
| `specs/273-paid-traffic-analytics/checklists/requirements.md` | `d771fe1f54e69b297346bfde3ea52f82d484fc241f13576efc34e09feffe80f4` |
| `specs/273-paid-traffic-analytics/checklists/security.md` | `dbd65a5afb7829789d8b4aa48f8c0b32243cc039681d15a5b851b381ca3b8b92` |
| `specs/273-paid-traffic-analytics/checklists/privacy-measurement.md` | `5b4164d0ce3e11ea6bca8419f4f0d6f6d33de163e3745cbb4cbfccd90ce07840` |
| `specs/273-paid-traffic-analytics/checklists/infra.md` | `a3319849bcd8be93803415495b42b4e50476cf1e08eb57ef898d34293f2be0cf` |
| `specs/273-paid-traffic-analytics/validation/t112-requirements-review-20261116.md` | `bb7c8592b302d6cb9ef21e0ecfc1045778afd39f07efed29787091ae3aaf91a5` |
| `specs/273-paid-traffic-analytics/validation/t112-analyze-20261116.md` | `0252da92dd9c3ff435a13bf55c0234afbb010abd9a3a1c49f8e42461427c18dc` |
| `.specify/memory/constitution.md` | `7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8` |
| `docs/prd-voice-layer-final.md` | `0f3ccfcfa60062bb0aae6802eeb0012056a635a30cb9f46f54d1992d0b4f57c2` |
| `docs/current-product-status.md` | `66ba7daa70519c8848a6daea51cd593220fccf75d4b5ea3a4a154e5ae139c3ca` |
| `docs/agent-guidance/product-gates.md` | `9f7072c879490d250053cb7397ad6b9b68fdcde17bdf9367ed874a41e450b5f5` |
