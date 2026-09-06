# Tasks: Полноценные итоги встреч

**Input**: Design documents from `/specs/239-full-meeting-minutes/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md,
contracts/meeting-protocol.md, quickstart.md

**Tests**: Обязательны до реализации для каждого изменяемого договора и
пользовательского пути; полнокорпусная содержательная проверка обязательна до PR.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: можно выполнять параллельно в разных файлах
- **[Story]**: пользовательская история из spec.md

## Phase 1: Setup

**Purpose**: Зафиксировать миграционный и релизный контекст.

- [ ] T001 Создать русскоязычный changelog fragment Feature 239 в changes/unreleased/F239.yaml
- [ ] T002 Зафиксировать безопасный corpus-review формат без частного содержания в specs/239-full-meeting-minutes/quickstart.md

---

## Phase 2: Foundational

**Purpose**: Ввести единый protocol contract и storage до пользовательских проекций.

- [ ] T003 [P] Написать failing nested-schema и validation tests в apps/server/tests/unit/test_outcome_prompts.py
- [ ] T004 [P] Написать failing persistence/migration tests в apps/server/tests/integration/test_meeting_outcomes_migrations.py
- [ ] T005 Добавить protocol fields и frozen header кандидата в apps/server/src/twobrain_rec_server/db/models/outcomes.py и новую Alembic migration в apps/server/src/twobrain_rec_server/db/migrations/versions/ после проверки реального Alembic head
- [ ] T006 Реализовать strict protocol schema, recursive refs validation и quote checks в apps/server/src/twobrain_rec_server/outcomes/prompts.py
- [ ] T007 Обновить protocol dataclasses/helpers в apps/server/src/twobrain_rec_server/outcomes/models.py
- [ ] T008 Обновить store/service whole-document persistence и truthful unavailable state в apps/server/src/twobrain_rec_server/outcomes/store.py и apps/server/src/twobrain_rec_server/outcomes/service.py

**Checkpoint**: Новый protocol document валидируется и сохраняется без пользовательского renderer.

---

## Phase 3: User Story 1 — Понять результат встречи (Priority: P1) 🎯 MVP

**Goal**: Получить связный тематический протокол по полной расшифровке.

**Independent Test**: Synthetic multi-topic transcript создаёт summary, цели и
темы с поздними уточнениями без пустых искусственных блоков.

- [ ] T009 [P] [US1] Написать failing prompt quality fixtures для multi-topic/revisited/correction сценариев в apps/server/tests/unit/test_outcome_prompts.py
- [ ] T010 [P] [US1] Написать failing protocol projection tests в apps/server/tests/unit/test_meeting_outcomes_view_models.py
- [ ] T011 [US1] Заменить плоский production prompt полным adaptive meeting-minutes prompt в apps/server/src/twobrain_rec_server/cli/langfuse_prompts.py
- [ ] T012 [US1] Сохранить canonical nested protocol в candidate Generation Call/outcome set в apps/server/src/twobrain_rec_server/outcomes/ai_service.py
- [ ] T013 [US1] Создать MeetingProtocol API/view models в apps/server/src/twobrain_rec_server/api/schemas.py и apps/server/src/twobrain_rec_server/cabinet/view_models.py
- [ ] T014 [US1] Отобразить key summary, цели и тематические блоки в apps/server/src/twobrain_rec_server/cabinet/rendering.py

**Checkpoint**: Владелец видит полный candidate/accepted протокол.

---

## Phase 4: User Story 2 — Проверить вывод по записи (Priority: P1)

**Goal**: Каждый существенный тезис имеет рабочие канонические таймкоды.

**Independent Test**: Все refs синтетического протокола разрешаются в pinned
segments; любой неправильный ref/quote отклоняет документ целиком; частично
подтверждённый составной тезис не публикуется.

- [ ] T015 [P] [US2] Написать failing single/multi-ref, invalid-ref, quote и stale-revision tests в apps/server/tests/unit/test_outcome_prompts.py
- [ ] T016 [P] [US2] Написать failing source-button seek/focus contract tests в apps/server/tests/contract/test_cabinet_playback_contract.py
- [ ] T017 [US2] Канонизировать все вложенные refs из pinned transcript в apps/server/src/twobrain_rec_server/outcomes/ai_service.py
- [ ] T018 [US2] Переиспользовать доступные source controls возле каждого statement в apps/server/src/twobrain_rec_server/cabinet/rendering.py
- [ ] T019 [US2] Сохранить keyboard/focus/live-region переход к transcript segment в apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js

**Checkpoint**: Любой показанный важный тезис проверяется по записи.

---

## Phase 5: User Story 3 — Точные решения и задачи (Priority: P1)

**Goal**: Отделить решения и обязательства, не угадывая owner/due.

**Independent Test**: Proposal не становится решением; отменённая задача
исчезает; переназначение и отдельно названный срок получают правильные refs.

- [ ] T020 [P] [US3] Написать failing decision/action/owner/due regression tests в apps/server/tests/unit/test_outcome_prompts.py
- [ ] T021 [P] [US3] Написать failing task table и empty-state tests в apps/server/tests/unit/test_meeting_outcomes_view_models.py
- [ ] T022 [US3] Усилить decision/action extraction и финальное self-check правило в apps/server/src/twobrain_rec_server/cli/langfuse_prompts.py
- [ ] T023 [US3] Валидировать независимые task/owner/due refs и generic owner запрет в apps/server/src/twobrain_rec_server/outcomes/prompts.py
- [ ] T024 [US3] Отобразить решения и таблицу задач с `Не назначен`/`Не указан` в apps/server/src/twobrain_rec_server/cabinet/rendering.py

**Checkpoint**: Решения и задачи фактически точны и исполнимы.

---

## Phase 6: User Story 4 — Интерфейс и выгрузка (Priority: P2)

**Goal**: HTML, summary-only, share, Markdown и JSON используют один протокол.

**Independent Test**: Смысл, refs и порядок разделов совпадают; Markdown не
экранирует обычную русскую пунктуацию и не показывает служебную шапку.

- [ ] T025 [P] [US4] Написать failing Markdown/JSON parity tests в apps/server/tests/unit/test_transcript_exports.py
- [ ] T026 [P] [US4] Написать failing accepted-only share/egress tests в apps/server/tests/integration/test_transcript_export_egress.py и apps/server/tests/integration/test_recording_share_public_link.py
- [ ] T027 [US4] Перевести export snapshot и renderers на protocol document в apps/server/src/twobrain_rec_server/cabinet/exports.py
- [ ] T028 [US4] Перевести summary-only/share projections на protocol document в apps/server/src/twobrain_rec_server/cabinet/egress.py и apps/server/src/twobrain_rec_server/cabinet/web_routes/browser.py
- [ ] T029 [US4] Добавить минимальные responsive/accessibility стили полного протокола в apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css

**Checkpoint**: Протокол пригоден как рабочий документ во всех разрешённых поверхностях.

---

## Phase 7: User Story 5 — Разные типы встреч (Priority: P2)

**Goal**: Адаптировать акценты без ослабления grounding.

**Independent Test**: Synthetic customer/brainstorm/incident/HR/interview
сценарии меняют фокус и сохраняют предложения, неопределённости и точные refs.

- [ ] T030 [P] [US5] Написать failing profile-specific prompt tests в apps/server/tests/unit/test_prompt_optimization.py
- [ ] T031 [US5] Обновить FORMAT_FOCUS всех встроенных профилей в apps/server/src/twobrain_rec_server/cli/langfuse_prompts.py
- [ ] T032 [US5] Обновить judge prompts для полноты тем, решений, задач и практической применимости в apps/server/src/twobrain_rec_server/cli/langfuse_prompts.py
- [ ] T033 [US5] Обновить built-in и personal template definitions на единый full protocol contract в apps/server/src/twobrain_rec_server/outcomes/templates.py и apps/server/src/twobrain_rec_server/api/cabinet.py

**Checkpoint**: Все доступные профили выдают полноценный протокол.

---

## Phase 8: User Story 6 — Переход без рабочего легаси (Priority: P2)

**Goal**: Ни один активный путь не создаёт и не показывает плоский v1.

**Independent Test**: Новая и старая встреча проходят generation/review/share/
export без импорта старого generator/renderer; старая ревизия честно недоступна.

- [ ] T034 [P] [US6] Написать failing no-flat-fallback contract test в apps/server/tests/contract/test_meeting_outcomes_contract.py
- [ ] T035 [US6] Удалить deterministic extractive generator и active item persistence из apps/server/src/twobrain_rec_server/outcomes/generator.py, apps/server/src/twobrain_rec_server/outcomes/service.py и apps/server/src/twobrain_rec_server/outcomes/store.py
- [ ] T036 [US6] Сохранить template keys/default/slot/share bindings, обновить текущие встроенные определения до version 2 без рабочего старого registry и применить mapping личных sections в apps/server/src/twobrain_rec_server/outcomes/templates.py, apps/server/src/twobrain_rec_server/api/cabinet.py и apps/server/src/twobrain_rec_server/cabinet/queries.py; покрыть сохранность в apps/server/tests/unit/test_summary_templates.py и apps/server/tests/integration/test_meeting_summary_slots.py
- [ ] T037 [US6] Удалить active flat category view/render/export code в apps/server/src/twobrain_rec_server/api/schemas.py, apps/server/src/twobrain_rec_server/cabinet/view_models.py, apps/server/src/twobrain_rec_server/cabinet/rendering.py и apps/server/src/twobrain_rec_server/cabinet/exports.py
- [ ] T038 [US6] Обновить deletion и RLS lifecycle tests для protocol artifact без потери исторической cleanup truth в apps/server/tests/integration/test_meeting_outcomes_deletion.py и apps/server/tests/contract/test_rls_access_outcomes.py

**Checkpoint**: Новый протокол — единственный рабочий outcome contract.

---

## Phase 9: Polish, полнокорпусная проверка и closeout

- [ ] T039 [P] Обновить релевантные docs/current-product-status.md и specs/239-full-meeting-minutes/contracts/meeting-protocol.md по фактической реализации
- [ ] T040 Запустить focused unit/contract/integration и PostgreSQL/RLS проверки из specs/239-full-meeting-minutes/quickstart.md
- Требование к T011/T014/T025/T040/T043: FR-035 — весь смысл создаёт LLM; проверки и форматирование не меняют слова, модальность, имена и сроки. Синтетические регрессии покрывают validation/enrichment/render/export; общая ошибка исправляется в модельной стадии, не серверным редактором текста.
- [ ] T041 Добавить закрытый corpus evaluator с безопасным aggregate-only отчётом в apps/server/src/twobrain_rec_server/cli/meeting_protocol_eval.py и покрыть его в apps/server/tests/unit/test_meeting_protocol_eval.py
- [ ] T042 Выполнить закрытую первичную генерацию через apps/server/src/twobrain_rec_server/cli/meeting_protocol_eval.py и полную содержательную проверку всех доступных пригодных встреч по FR-029 и specs/239-full-meeting-minutes/quickstart.md без записи частного содержания в репозиторий
- [ ] T043 Исправить каждый общий класс ошибки в apps/server/src/twobrain_rec_server/cli/langfuse_prompts.py, outcomes/prompts.py и cabinet/rendering.py; после T053–T057 сравнить модели через exact Langfuse configs и выбрать кандидат по реальным результатам; заново генерировать и полностью перечитывать весь корпус по specs/239-full-meeting-minutes/quickstart.md до SC-001..SC-013
- [ ] T044 Зафиксировать только безопасные агрегаты финального corpus-run в specs/239-full-meeting-minutes/validation/corpus-review.md
- [ ] T045 Выполнить speckit-converge и устранить все CRITICAL/HIGH findings в specs/239-full-meeting-minutes/ и затронутом коде
- [ ] T046 Запустить infra/scripts/ci-local.sh --fast и infra/scripts/ci-local.sh --full на точном кандидате PR
- [ ] T047 Выполнить Ponytail review, secret/private-content scan и проверить отсутствие active flat/v1 imports через rg по apps/server/src/
- [ ] T048 Зафиксировать implementation commit, exact source SHA, создать русский PR и дождаться governance-fast на том же SHA

## Review corrections 2026-09-06 — обязательны до UI и corpus

- [ ] T049 Написать failing tests двух стадий, отказа verifier, exact draft/transcript/root binding, frozen headers и replay/ambiguous границ в apps/server/tests/integration/test_outcome_generation_workflow.py, apps/server/tests/unit/test_prompt_bundle.py и apps/server/tests/unit/test_trusted_outcome_publication_boundary.py
- [ ] T050 Реализовать exact verifier child и две durable стадии с отдельными Generation Call без повтора inference и без публикации непроверенного документа в apps/server/src/twobrain_rec_server/cli/langfuse_prompts.py, outcomes/prompt_bundle.py, outcomes/prompts.py, outcomes/ai_service.py и workflows/outcome_generation_workflow.py
- [ ] T051 Добавить failing deletion tests, затем очистку нового protocol/header snapshot и учёт NOTES_SUMMARY при обычном/повторном удалении и гонке в apps/server/tests/integration/test_meeting_outcomes_deletion.py и apps/server/src/twobrain_rec_server/deletion/service.py; retained Generation Call не очищать
- [ ] T052 Покрыть затем реализовать source deep-link с повторной авторизацией и pinned source в apps/server/src/twobrain_rec_server/cabinet/web_routes/browser.py, cabinet/static/cabinet/cabinet.js и apps/server/tests/integration/test_cabinet_meeting_outcomes.py; проверить браузером на synthetic данных по specs/239-full-meeting-minutes/quickstart.md

---

## Уточнение FR-036/037 — настройки Langfuse без model lock

- [ ] T053 Написать failing tests config 5, exact Langfuse sync, отсутствия defaults/route descriptor/специальных headers, разных моделей и nullable provenance в apps/server/tests/unit/test_outcome_prompts.py, test_prompt_optimization.py, test_prompt_bundle.py и test_litellm_gateway.py
- [ ] T054 Реализовать единую проекцию настроек из Langfuse без defaults и обязательного high, sync из exact numeric source versions без потери параметров в apps/server/src/twobrain_rec_server/outcomes/prompts.py и cli/langfuse_prompts.py; обновить синтетические fixtures в apps/server/tests/fixtures/meeting_protocol.py
- [ ] T055 Удалить route descriptor/hash/allowlist/custom headers из apps/server/src/twobrain_rec_server/outcomes/prompt_bundle.py, outcomes/generator.py, outcomes/ai_service.py, outcomes/prompt_optimization.py и cli/prompt_optimization.py; удалить infra/litellm/graf_route_binding_callback.py и infra/litellm/graf-route-binding.json без runtime legacy
- [ ] T056 Покрыть exact settings/provenance tamper, разные модели стадий, root export/load, replay и retained delivery; обновить наблюдаемость без подмены actual из selected в apps/server/src/twobrain_rec_server/observability/langfuse.py и apps/server/tests/unit/test_langfuse_observability.py; выполнить unit/integration/PostgreSQL проверки по specs/239-full-meeting-minutes/quickstart.md
- [ ] T057 Согласовать действующие нормы и безопасный двухэтапный выпуск в docs/agent-guidance/product-gates.md, specs/183-trusted-outcome-lifecycle/prompt-pipeline.md, specs/183-trusted-outcome-lifecycle/temporal-langfuse.md, specs/239-full-meeting-minutes/quickstart.md и changes/unreleased/F239.yaml; независимый review полного удаления и отсутствие credential/routing изменений
- [ ] T058 Выпустить отдельно только снятие model lock и настройки Langfuse на действующем outcome contract: чистая ветка без незавершённого protocol pipeline, scoped PR, exact-SHA governance-fast/release-full, согласованное GRAF/root/LiteLLM переключение и synthetic smoke нескольких моделей по docs/agent-guidance/release-and-validation.md; сохранить безопасное evidence в docs/deployments/2brain-rec/
- [ ] T059 После T043–T048 выпустить новые протоколы и выбранный Langfuse root по docs/agent-guidance/release-and-validation.md: exact-SHA release-full/CD dry-run/deploy, post-deploy smoke, русский CalVer GitHub Release и закрытие issues с evidence в docs/deployments/2brain-rec/

T053 → T054 → T055 → T056/T057 → T058 → T043 → T048 → T059.
T056 и T057 могут проверяться параллельно. T058 исключает протоколы и имеет
отдельный технический PR; main feature/tasks не закрываются этим выпуском.

Issue sync 2026-09-06: T053 → #6630, T054 → #6631, T055 → #6632,
T056 → #6633, T057 → #6634, T058 → #6642, T059 → #6643; все OPEN. Владелец разрешил отдельный технический
релиз до corpus и основной релиз после приёмки. D239-I01 передан на узкую
повторную проверку; прежний отрицательный verdict — историческое evidence.

T056 включает синтетический исторический call с actual полями только из
старых headers: observation-only доставка сохраняет исходные hashes/metadata,
не требует текущего config/root и не разрешает новый inference/publication.

Технический срез T058, 2026-09-06: локальная реализация снятия ограничения
на действующем outcome contract прошла 129 unit/contract и 105 PostgreSQL
тестов, Ruff и project checks. Evidence:
[validation/model-settings-review.md](validation/model-settings-review.md).
Это частичный прогресс T053–T058, не закрытие задач новых протоколов.
Commit/push/PR, authoritative CI и production-переключение ещё не выполнены.

## Dependencies & Execution Order

- Phase 1 → Phase 2 блокирует все истории.
- T049 выполняется после T006/T007; T050 после T049 и T011/T012, до T013/T014 и всех полнокорпусных запусков.
- T051 выполняется после T005 до T038; T052 после T018/T019 до T027/T028.
- US1 требует Foundation; US2 и US3 требуют US1 protocol projection.
- US4 требует US1–US3; US5 может идти после Foundation параллельно UI.
- US6 завершается после перехода всех consumers на protocol document.
- Corpus review и closeout выполняются только после US1–US6.

## Parallel Opportunities

- Failing tests с `[P]` можно писать параллельно до соответствующего кода.
- Prompt profile tests US5 независимы от HTML/export работы US4.
- Документация T039 параллельна последним focused checks после стабилизации договора.

## Implementation Strategy

1. Сначала новый schema/storage и failing tests.
2. Затем один полный owner candidate с refs, решениями и задачами.
3. После него перевести accepted/share/export consumers.
4. Последним удалить active flat generator/renderer и обновить defaults.
5. Выполнить полный закрытый corpus loop, convergence и exact-SHA PR gates.

Не создавать рабочий v1/v2 switch, параллельный renderer, новый сервис или
зависимость. Production deployment описан в T058/T059, а не скрыт в T048.
