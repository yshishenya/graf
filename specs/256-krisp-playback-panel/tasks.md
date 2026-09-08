# Tasks: F256 — первый этап панели

Источник: spec.md, plan.md, contracts, data-model.md, quickstart.md.
Режим high-risk-product. US4/ножницы отложены владельцем; US1–US3 обязательны.

## Подготовка

- [X] T001 Проверить текущие требования, независимые checklists и согласованность первого этапа в specs/256-krisp-playback-panel/checklists/ и specs/256-krisp-playback-panel/tasks.md; привязать все задачи к GitHub до кода. (Issue #6795)

## US1 — воспроизведение

- [X] T002 [US1] Обновить проверяемый контракт панели в apps/server/tests/unit/test_cabinet_web_shell.py и apps/server/tests/contract/test_cabinet_static_assets_contract.py: один audio, доступность, новые элементы и отсутствие ножниц; подтвердить ожидаемые падения до реализации. (Issue #6796)
- [X] T003 [US1] Воспроизвести геометрию и меню скорости, ±15, next/previous, события play/pause/error/end в apps/server/src/twobrain_rec_server/cabinet/rendering.py и apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js, cabinet.css по contracts/playback-panel.md. (Issue #6799)

## US2 — спикеры и навигация

- [X] T004 [US2] Реализовать Listen с объединением интервалов, сортировку с сохранением цвета, аватары, точный segment seek, collapse/resize и переименование без замены audio в apps/server/src/twobrain_rec_server/cabinet/rendering.py и apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js, cabinet.css; расширить тесты T002. (Issue #6802)

## US3 — обсуждения

- [X] T005 [P] [US3] Добавить проверки полного цикла, ACL (включая self-escalation), пагинации replies, RLS, stale/retry и lifecycle в apps/server/tests/integration/test_meeting_comments.py; подтверждать отрицательные сценарии до реализации соответствующих операций. (Issue #6805)
- [X] T006 [US3] Добавить модели/RLS и явные роли без повышения старых разрешений в apps/server/src/twobrain_rec_server/db/models/comments.py, db/models/meeting_access.py, db/migrations/versions/0090_playback_comments.py, cabinet/access.py, api/schemas.py, cabinet/queries.py и cabinet/templates/cabinet/fragments/meeting_share.html; все пути относительно apps/server/src/twobrain_rec_server. (Issue #6807)
- [X] T007 [US3] Реализовать comments/replies/edit/delete/resolve/reaction/mention candidates в apps/server/src/twobrain_rec_server/cabinet/comments.py и api/cabinet.py с общей owner/shared ACL, CSRF, meeting fence и version/idempotency проверкой. (Issue #6811)
- [X] T008 [US3] Включить упоминания, producer RLS, account merge и полную очистку в apps/server/src/twobrain_rec_server/notifications/inbox.py, cabinet/web_routes/notifications.py, auth/account_merge.py и deletion/service.py; пройти соответствующие регрессии. (Issue #6812)
- [X] T009 [P] [US3] Реализовать форму и боковую панель комментариев, Unicode emoji/mentions, ответы/реакции/фильтры/ссылки и ошибки в apps/server/src/twobrain_rec_server/cabinet/static/cabinet/playback-comments.js и playback-comments.css; подключить через apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/base.html; публичный hook window.GRAFPlaybackComments.init(shell) вызвать при повторной инициализации detail из cabinet.js. (Issue #6813)

## Проверки и завершение

- [X] T010 Проверить настоящее синтетическое audio, все переходы/темы/размеры/200% и комментарии в specs/256-krisp-playback-panel/evidence/playback-panel-runtime-check.cjs; выполнить scoped suites и existing F205 Chromium/WebKit geometry, сохранить только метаданные evidence. (Issue #6814)
- [X] T011 Выполнить независимый review, ponytail review и converge; устранить обязательные замечания, обновить changes/unreleased/F256.yaml и specs/256-krisp-playback-panel/evidence/validation.md, выполнить infra/scripts/ci-local.sh --fast. (Issue #6815)
- [X] T012 После разрешённого проверенного коммита пройти GRAF Dev build/promote/status/smoke и ручную приёмку по infra/dev/README.md, сохранить evidence в specs/256-krisp-playback-panel/evidence/validation.md; согласовать task/issue и exact-SHA PR gates. Выпуск и production вне задачи. (Issue #6816)

## Dependencies / параллельная работа

T001 → T002 → T003 → T004. Независимый backend: T001 → T005 → T006 → T007 → T008.
T009 использует утверждённый HTTP-контракт; интеграция требует T007–T008.
T003/T004 владеют rendering.py/cabinet.js/cabinet.css; T006–T008 не меняют эти файлы.
T009 владеет отдельными comment assets; подключение согласуется с владельцем rendering.
T010 после T004/T008/T009; T011 после T010; T012 после T011 и explicit commit approval.
Разные истории могут исполняться параллельно разными агентами после gate T001,
без записи в общие файлы. Reviewer checklists не принадлежат исполнителям.

## Coverage

FR-001–004: T002/T003/T010. FR-005–009: T004/T010.
FR-010/011: T005–T009. FR-015 (comments/full deletion): T008.
FR-016–018/020: T002–T012. SC-001–006: T010–T012.
FR-012–014/019, US4 и аудио-часть FR-015: следующий этап, не исполняются сейчас.
Завершение задачи отмечается после проверки; issue закрывается только с evidence
и соблюдением tracker-policy. Исторический reference JSON не является списком
обязательных действий первого этапа без учёта delivery_stages.
