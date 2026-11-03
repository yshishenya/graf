# Tasks: F292 — поделиться встречей по образцу Krisp

**Input**: spec.md, plan.md, research.md, data-model.md, contracts/sharing.md, quickstart.md.
**Lane**: high-risk-feature, no deploy. Источник реализации — этот список; все задачи обязательны. Тесты нужны для приватности/прав и переходов. Reviewer чеклисты не отмечаются реализацией.

## Phase 1 — Подготовка

- [X] T001 Зафиксировать исследование Krisp, clarify, план и независимую готовность требований в `specs/292-sharing-krisp-parity/{spec,research,plan,review-report}.md`; выполнить analyze и сопоставление задач GitHub до кода. [FR-001/014/015]

## Phase 2 — Основа доступа

- [X] T002 Добавить проверки совместимости F286, версий/стабильного copy, всех переходов invite_only/workspace/link и сохранения адресных прав в `apps/server/tests/integration/test_meeting_sharing_parity.py`; проверить stale409, tenant/CSRF и legacy writer. [FR-003–006/024]
- [X] T003 Согласовать scope-aware link/general-access в `apps/server/src/twobrain_rec_server/cabinet/summary_sharing.py`, `cabinet/access.py`, `api/summary_sharing.py`: scope строго summary_only/full_meeting, default summary_only, expiry строго7/30/90, одна active link; изменения требуют grant/version либо fingerprint64hex под fence. Современная encrypted ссылка не меняется legacy writer без версии. [FR-003–006/024]

## Phase 3 — US2: получатель читает встречу

**Independent test**: synthetic full/summary links, готовые/пустые материалы, анонимное чтение и отзыв.

- [X] T004 [US2] Добавить проверки публичной проекции/audio в `apps/server/tests/integration/test_meeting_sharing_parity.py`: summary-only без скрытого transcript/audio, чужие workspace/result, revoke/expiry/rotate/scope/deletion, замена media между страницей и playback, полный файл >4MiB без Range200, Range206/416, заголовки и audit без мнимого owner. [FR-007–009/012/020/025]
- [X] T005 [US2] Реализовать общий public resolver, узкую full DTO и потоковое audio в `apps/server/src/twobrain_rec_server/cabinet/public_sharing.py`, `cabinet/egress.py`, `api/cabinet.py`: повторная проверка grant под fence, effective accepted result и одинаковые workspace/meeting/result, media_version24hex, несовпадение409, буфер <=4MiB, без materialize всего файла; summary-only JSON совместим. [FR-007–009/012/020/025]
- [X] T006 [US2] Собрать reader с tabs/copy/search/говорящими/таймкодами/player±15/speed и пустыми состояниями в `apps/server/src/twobrain_rec_server/cabinet/rendering.py`, `templates/cabinet/pages/shared_meeting_reader.html`, `static/cabinet/public-sharing.js`, `static/cabinet/cabinet.css`; обеспечить 320/390/1440/light/dark/keyboard/no-JS и добавить проверки в `apps/server/tests/contract/test_recording_share_ui_contract.py`, `tests/browser/public-sharing.test.cjs`. [FR-007/008/013/018/019/022/023]

## Phase 4 — US1: владелец передаёт доступ

**Independent test**: панель владельца, роли/список/отзыв/экспорт, стабильное копирование и прежняя отправка итогов.

- [X] T007 [US1] Перестроить окно справа Share/Export, приглашение/owner/список/общую аудиторию/scope/copy в `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/fragments/meeting_share.html`, `cabinet/review_policy_rendering.py`, `static/cabinet/summary-sharing.js`, `static/cabinet/cabinet.js`; переиспользовать существующие адресные grants/invitations и export, сохранить F286 email/auto/idempotency/unknown. Обновить предметные UI/browser проверки в `apps/server/tests/{contract/test_recording_share_ui_contract.py,browser/summary-sharing-state.test.cjs,browser/share-recipient-privacy.test.cjs}`. [FR-002–006/013/017/019/022/024]

## Phase 5 — US3: получатель начинает пользоваться GRAF

**Independent test**: чистый гость → приглашение/просмотр → вход/регистрация/возврат; своя встреча в своём пространстве.

- [X] T008 [US3] Добавить первое добровольное приглашение, постоянную шапку/вход/начало своей встречи и browser/install fallback в `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/shared_meeting_reader.html`, `static/cabinet/public-sharing.js`; реализовать зашифрованный HttpOnly/SameSite cookie продолжения TTL600 без токена в login query в `api/cabinet.py`/`cabinet/public_sharing.py`; проверить безопасный возврат/expiry/tamper/нет membership в `apps/server/tests/integration/test_meeting_sharing_parity.py`. [FR-010/011/016/021]

## Phase 6 — US4: приложение и браузер

**Independent test**: parser/route/state и живой cold/warm GRAF Dev, собственная сессия и контекст.

- [X] T009 [US4] Добавить Swift-проверки строгого native intent, pending cold/warm и full route восстановления в `apps/macos/Shared/Tests/SharedMeetingHandoffTests.swift`, `DesktopCabinetRoutePolicyTests.swift`, `DesktopCabinetWorkspaceTests.swift`; token32..128 ASCII URL-safe, position integer0..86400000, unknown/duplicate/credentials/origin запрещены, media replacement не применяет старую позицию автоматически. [FR-010/021/025]
- [X] T010 [US4] Реализовать переход в `apps/macos/RecApp/Sources/Cabinet/SharedMeetingHandoff.swift`, `DesktopCabinetRoutePolicy.swift`, `DesktopCabinetState.swift`, `App/TwoBrainRecApp.swift`: один pending intent, configured origin, собственные права, полный canonical route при входе; согласовать Dev grafrec-dev / production grafrec в `apps/macos/Scripts/build-dev-app.sh`, `Sources/Upload/ProductAttributionHandoff.swift`, серверной атрибуции и существующих contract tests. В `static/cabinet/public-sharing.js` переносить tab/position/media_version; прежняя версия записи → явное обновление без автоматического seek. [FR-010/021/025]

## Phase 7 — Полнота и приёмка

- [X] T011 Выполнить focused pytest/node/Swift из `specs/292-sharing-krisp-parity/quickstart.md`, исправить сбои, добавить русский `changes/unreleased/F292.yaml` и metadata-only `specs/292-sharing-krisp-parity/validation.md`. [FR-015/023; SC-001–005]
- [ ] T012 Проверить браузер и единственный `/Applications/GRAF Dev.app` через dev-harness с чистого exact SHA по `specs/292-sharing-krisp-parity/quickstart.md`: owner/anonymous/external, scope/revoke/range/return/cold/warm, все размеры/темы/keyboard; сохранить обезличенные доказательства в `specs/292-sharing-krisp-parity/validation.md`. [FR-001/013/015/023; SC-001–005]
- [ ] T013 Выполнить converge, final review и exact-SHA/base `governance-fast`/`macos-pr`/`pr-metadata`, сопоставить tasks/issues без ложного закрытия незавершённой приёмки в `specs/292-sharing-krisp-parity/{tasks,validation}.md`. Production/release не выполнять. [FR-015]

## Зависимости и выполнение

T001 → T002 → T003 → T004 → T005 → T006. T007 после T003 и T006. T008 после T006; T009 после contracts, T010 после T008/T009. T011 после T007/T008/T010, затем T012 → T013. Внутри каждой фазы тесты приватности до реализации. Без независимого PASS финальной сверки tasks, analyze и issue sync код не начинается.

Параллельные возможности: read-only сверка требований и подготовка локальной среды; сами implementation задачи выполняются последовательно из-за общих файлов. Новых worker agents этот план не требует. Приращения US2→US1→US3→US4 проверяются отдельно, но весь заявленный объём обязателен; промежуточная готовность одной истории не завершает задачу пользователя.

## Phase 8 — Уточнение единого просмотра

- [X] T014 [US2] Переиспользовать рендер и JS/CSS основного проигрывателя в `cabinet/rendering.py`, `templates/cabinet/pages/shared_meeting_reader.html`, `static/cabinet/{cabinet,public-sharing}.js`: дорожки/цвета/доля речи, таймлайн/переход/выбор спикеров/следующая реплика/скорость/сворачивание/клавиатура; безопасные локальные ключи из `cabinet/public_sharing.py`, без внутренних идентификаторов/комментариев. Проверить основной и публичный путь в существующих playback tests и `test_meeting_sharing_parity_ui.py`, а затем в T012. [FR-007/008/018/023/026]

T014 выполняется до завершения T011–T013; требует независимого повторного просмотра уточнённых требований и синхронизации задачи GitHub до кода.
