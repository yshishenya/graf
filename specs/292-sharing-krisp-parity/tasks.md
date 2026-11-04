# Tasks: F292 — поделиться встречей по образцу Krisp

**Input**: spec.md, plan.md, research.md, data-model.md, contracts/sharing.md, quickstart.md.
**Lane**: high-risk-product; выпуск — release/production deploy, явно разрешён пользователем 2026-11-03. Источник реализации — этот список; все задачи обязательны. Тесты нужны для приватности/прав и переходов. Reviewer чеклисты не отмечаются реализацией.

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
- [ ] T013 Выполнить converge, final review и exact-SHA/base `governance-fast`/`macos-pr`/`pr-metadata`, сопоставить tasks/issues без ложного закрытия незавершённой приёмки в `specs/292-sharing-krisp-parity/{tasks,validation}.md`. После PASS перейти к T015–T017. [FR-015/027]

## Зависимости и выполнение

T001 → T002 → T003 → T004 → T005 → T006. T007 после T003 и T006. T008 после T006; T009 после contracts, T010 после T008/T009. T011 после T007/T008/T010, затем T012 → T013. Внутри каждой фазы тесты приватности до реализации. Без независимого PASS финальной сверки tasks, analyze и issue sync код не начинается.

Параллельные возможности: read-only сверка требований и подготовка локальной среды; сами implementation задачи выполняются последовательно из-за общих файлов. Новых worker agents этот план не требует. Приращения US2→US1→US3→US4 проверяются отдельно, но весь заявленный объём обязателен; промежуточная готовность одной истории не завершает задачу пользователя.

## Phase 8 — Уточнение единого просмотра

- [X] T014 [US2] Переиспользовать рендер и JS/CSS основного проигрывателя в `cabinet/rendering.py`, `templates/cabinet/pages/shared_meeting_reader.html`, `static/cabinet/{cabinet,public-sharing}.js`: дорожки/цвета/доля речи, таймлайн/переход/выбор спикеров/следующая реплика/скорость/сворачивание/клавиатура; безопасные локальные ключи из `cabinet/public_sharing.py`, без внутренних идентификаторов/комментариев. Проверить основной и публичный путь в существующих playback tests и `test_meeting_sharing_parity_ui.py`, а затем в T012. [FR-007/008/018/023/026]

T014 выполняется до завершения T011–T013; требует независимого повторного просмотра уточнённых требований и синхронизации задачи GitHub до кода.

## Phase 9 — Разрешённый выпуск

- [ ] T015 Подготовить новый CalVer серверный релиз по `docs/agent-guidance/release-and-validation.md`: завершить T012/T013, exact-SHA/base PR gates и линейный merge; `prepare-release.sh`, frozen train/candidate, один authoritative GitHub release-full, train-attest/decide, `cd-remote.sh --dry-run` и штатный execute/health/rollback evidence. [FR-027]
- [ ] T016 Выпустить macOS GRAF с того же frozen source по `docs/agent-guidance/macos-notarization.md`: Developer ID, hardened runtime/timestamp, Accepted notarization, staple/Gatekeeper, проверенный Sparkle archive/signature, tag/GitHub Release и публичный feed readback. Не публиковать ненотарифицированный пакет. [FR-027]
- [ ] T017 Проверить опубликованные сервер, страницу получателя и версию приложения на синтетических материалах; записать metadata-only evidence в `validation.md`, сверить tasks/issues и закрыть task issues перед umbrella через live closeout validator с release-full. Очистить только собственные завершённые временные сборки, сохранить журналы и контрольные суммы. [FR-015/023/027]

T015 после T012/T013; подготовка подписанного macOS-пакета T016 может идти параллельно authoritative full CI замороженного кандидата, публикация — после go/tag. T017 после обеих публикаций. Это расширение разрешения на выпуск, без изменения продуктового состава доступа.

## Phase 10: Convergence

- [X] T018 Исправить R1 в `static/cabinet/summary-sharing.js`: копирование при invite_only/workspace сохраняет аудиторию и копирует существующий защищённый маршрут без публикации; публичный доступ включается только отдельным подтверждённым выбором. Дополнить `tests/browser/sharing-owner.test.cjs` отрицательными сценариями обеих аудиторий, отменой подтверждения и стабильным повторным копированием; обновить живую проверку `sharing-live.test.cjs` и повторить приёмку до T012/T013. [FR-003/006/024; US1/AC3; contracts UX; partial, HIGH]

## Phase 11: Convergence

- [X] T019 Исправить R2: надпись копирования и статус в `static/cabinet/summary-sharing.js` должны соответствовать эффективной аудитории при invite_only с expired/replacement_required ссылкой. Дополнить `tests/browser/sharing-owner.test.cjs` проверкой защищённого копирования без продления/ротации и ложного обещания кнопки. [FR-006/019; contracts UX; partial, MEDIUM]

## Phase 12: Convergence

- [X] T020 Исправить размещение панели в `static/cabinet/summary-sharing.js`: учитывать доступную область кабинета над проигрывателем, чтобы нижние действия оставались достижимы прокруткой в установленном GRAF Dev. В `tests/browser/sharing-owner.test.cjs` воспроизвести настоящую структуру `.app-shell`/`main`/проигрывателя и проверить границы панели и достижимость кнопки копирования; повторить Chromium/WebKit и установленное приложение. [FR-013/017/023; US4/AC1–2; partial, HIGH]

## Phase 13: Convergence

- [X] T021 Исправить восстановление клавиатурного фокуса после системного сохранения экспорта в `apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetWebView.swift`: общий обработчик загрузок возвращает фокус в прежний активный встроенный кабинет после Save/Cancel, не перехватывает другое окно или отсоединённый WebView. В общем `static/cabinet/cabinet.js` после успешного экспорта учитывать фактический родительский dialog переиспользуемой формы: самостоятельное окно закрывается с прежним возвратом, форма внутри sharing сохраняет фокус на своей кнопке, без ухода на «Ещё». Добавить предметную Swift-проверку в `apps/macos/Shared/Tests/EmbeddedCabinetJavaScriptConfirmTests.swift` и browser-проверку реального обработчика для обеих поверхностей в `apps/server/tests/browser/sharing-export-focus.test.cjs`, затем повторить сохранение/отмену и Escape в единственном установленном GRAF Dev. [FR-013/017/023; US4/AC1–2; partial, MEDIUM]


## Phase 14: Convergence

- [X] T022 Сохранять запрошенную позицию до загрузки metadata аудио в `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/public-sharing.js`: общий сборщик контекста входа и приложения использует pendingSeek до фактического применения, затем актуальное время проигрывателя. В `apps/server/tests/browser/public-sharing.test.cjs` проверить pending15/0 и готовую запись без запуска внешнего протокола, затем повторить обе browser-группы и установленный переход. [FR-010/021/025; US3/AC2–3; partial, HIGH]


## Phase 15: Convergence

- [X] T023 Устранить R6 при проверке адресного sharing в другом своём пространстве: `apps/server/src/twobrain_rec_server/auth/workspace_onboarding.py` проверяет и переносит fingerprint почтовой сессии по нормализованному email подтверждённой identity, как существующий email login/provider linking, сохраняя прежний subject для OAuth. В `apps/server/tests/unit/test_workspace_onboarding.py` воспроизвести hashed provider_subject≠email, проверить переход туда/обратно с неизменным сроком и заменой старых sessions, отказ при чужом fingerprint, inactive identity, неподтверждённой почте и отсутствии действующего членства; OAuth roundtrip без изменения subject. Повторить настоящие Dev owner grant/role/revoke в отдельном учебном пространстве; не менять личное пространство и не ослаблять auth/RLS. [FR-005/010/021; US3/AC2, US4/AC3; partial, HIGH]


## Phase 16: Convergence

- [ ] T024 Исправить R7: после замены списка адресатов в общем `static/cabinet/summary-sharing.js` возвращать клавиатурный фокус на заголовок sharing, только если перед заменой он находился в удаляемой строке. Сохранить чужой/перемещённый фокус. В `tests/browser/sharing-owner.test.cjs` воспроизвести role/revoke→Escape без дополнительного клика; Chromium/WebKit, затем установленный GRAF Dev. [FR-013/017/023; US1/US4; partial, MEDIUM]

- [ ] T025 Исправить R8: принятый новый shared intent должен начать загрузку даже из прежнего состояния expiredSession/offline/denied. В существующем `SharedMeetingHandoffInbox.take` синхронно с успешным consume установить `.loading`, в `TwoBrainRecApp.swift` передать текущий state. В `SharedMeetingHandoffTests.swift` проверить recovery states, пустой/отвергнутый intent без сброса state и single consume; не ослаблять parser, origin, server auth или отказ при загрузке. Повторить Swift и установленный публичный переход без собственного сеанса с сохранением recording00:15. [FR-010/021/023; US4; partial, HIGH]
