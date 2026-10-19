# Tasks: единый безопасный стенд GRAF Dev

**Input**: spec.md, plan.md, research.md, data-model.md,
contracts/state-ownership.md, quickstart.md.
**Status**: полный реестр после независимого ревью требований US1 36/36.
Исходные T001–T008 восстановлены из #6181–#6188 и сохраняют номера;
T009–T013 сохраняют широкие обязательства #6180. T001–T007 выполнены локально;
это не принятие issues. T008 и широкая приёмка остаются открытыми.
**Lane**: high-risk product area; analyze и issue sync обязательны до кода.
Текущий проект разрешает US1. US3 требует отдельного проекта и reviewer gate.

## Phase 1: подготовка

Новые зависимости, пакет и повторный lifecycle не нужны. Проверить source,
pointer, свободное место и сохранность чужой работы.

- [X] T001 Зафиксировать принадлежность репозитория в specs/224-dev-stand-completion/spec.md и specs/224-dev-stand-completion/contracts/state-ownership.md; принять независимые checklists/requirements.md и checklists/infra.md, analyze и issue sync перед кодом — #6181.

## Phase 2: общие обязательные ограничения

До кода требуется PASS T001. Не изменять занятый GRAF Dev, общие Docker tags,
производственные данные или существующий lock inode. Временные Git/HOME/state
ограничены каталогом проверки, после неё удаляются. Сначала отрицательные тесты.

## Phase 3: US1 — одна принадлежность стенда (P1)

**Цель**: рабочие копии одного origin используют прежний root/lock;
чужой/неизвестный origin останавливается до воздействия.
**Независимая проверка**: настоящие временные Git repos/worktrees/clones,
другой cwd, два процесса и старый удерживаемый lock; внешние эффекты подменены.

- [X] T003 [US1] Воспроизвести исходный отказ и добавить изолированную матрицу origin/binding/path/adoption/frozen-adapter в tests/governance/test_dev_state_ownership.py; сохранить отрицательные Git-failure/чужой repo/другой cwd в specs/259-audit-remediation/evidence/dev-identity-probe.py — #6183.
- [X] T004 [US1] Исправить принадлежность, одноразовый adopt-state и совместимость закреплённого adapter в scripts/dev-harness.py по contracts/state-ownership.md: schema_version «graf-dev-repository-state.v1», repository «canonical github.com/owner/repo без credentials», state_root «абсолютный реальный путь к единственному принятому harness», adopted_active_sha «полный активный SHA при принятии либо null для нового пустого стенда», adopted_at «время принятия UTC»; строгая проверка полей/путей, registration→прежний operational lock, fsync/атомарная публикация, неизменные данные/inode, безопасный повтор и отказ при неоднозначности — #6184.
- [X] T005 [US1] В scripts/dev-harness.py закрыть все shared callers до первой записи и после lock: binding/live-override, build_manifest, adapter, schema-start-guard, smoke и prune; fixture допускает только изолированные файловые операции и никогда не удаляет общие Docker tags; доказать отсутствие эффектов в tests/governance/test_dev_state_ownership.py — #6185.
- [X] T007 [US1] В tests/governance/test_dev_state_ownership.py доказать сериализацию двух реальных процессов/регистраций, ожидание прежнего lock без смены inode, отказ при смене active SHA во время ожидания, перепроверку parent кандидата и прерывания/ошибку публикации binding без изменения manifests/runtime/journals — #6187.
- [X] T006 [US1] Обновить infra/dev/README.md и docs/agent-guidance/local-development.md: один binding/root/lock, явное принятие владельцем, неоднозначное состояние, запрет самостоятельного старого controller, ограничения status/fixture prune; live adoption только после освобождения стенда — #6186.
- [ ] T008 [US1] В specs/224-dev-stand-completion/validation.md зафиксировать high-risk focused matrix, независимое ревью реализации, ограниченный converge US1, governance/context/process/changelog/diff; после отдельного разрешения commit/PR подтвердить exact-SHA fast на подходящей машине и governance-fast/macos-pr/pr-metadata на точном PR SHA/base, затем сверить критерии #6181–#6188 — #6188.

**Checkpoint**: принятие US1 не завершает US2/US3, live adoption или #6180.

## Phase 4: US2 — фактически работающая версия (P1)

**Независимая проверка**: один установленный Dev/PID и все заявленные компоненты
соответствуют полному SHA; остановка обязательной службы даёт отказ.

- [ ] T009 [US2] По scripts/dev-harness.py, infra/scripts/graf-local.sh и tests/governance/test_dev_runtime_identity.py подтвердить текущий lifecycle без повторного построения; после освобождения стенда записать в specs/224-dev-stand-completion/validation-runtime.md ровно один PID/path/bundle/signer/channel и фактический SHA app/backend/frontend/workers, включая отрицательную проверку остановленной обязательной службы; обнаруженные дефекты сначала уточнить и независимо проверить по Spec Kit.

## Phase 5: US3 — восстановление и разрешения (P1)

**Независимая проверка**: crash boundaries дают согласованный результат либо
recovery-required; совместимый живой rollback и Dev TCC подтверждены отдельно.

- [ ] T010 [US3] В tests/governance/test_dev_promotion_transaction.py сначала изолированно воспроизвести SIGKILL обычного promote на stop/install/pointer; зафиксировать минимальные фазы/recovery в specs/224-dev-stand-completion/contracts/promotion-recovery.md, уточнить plan.md и reviewer-owned infra checklist, повторить analyze/sync; только после отдельного PASS минимально исправить scripts/dev-harness.py и повторить crash matrix с журналом specs/224-dev-stand-completion/validation-recovery.md; не дублировать существующую schema-transition recovery.
- [ ] T011 [US3] После T009/T010 и освобождения стенда выполнить штатный живой build→promote→status→smoke→compensation→rollback на одном /Applications/GRAF Dev.app; в specs/224-dev-stand-completion/validation-live.md доказать согласованность app/runtime/pointer, exact SHA и сохранность данных; для schema-changing перехода использовать существующего владельца specs/249-notification-control-design/tasks.md T038/#6786, не дублировать миграционную задачу и не принимать F224 до её доказательства.
- [ ] T012 [US3] По docs/agent-guidance/local-development.md и specs/224-dev-stand-completion/quickstart.md провести Dev-only проверку разрешений до/update/relaunch/после с тем же подписантом; в specs/224-dev-stand-completion/validation-tcc.md сохранить только технические signer/requirement/entitlements и результаты microphone/system-audio по Dev bundle ID, без reset TCC/отдельного приложения/частных записей; неизвестное состояние не считать PASS.

## Phase 6: общая проверка и закрытие

- [X] T002 Добавить проверенный changes/unreleased/F224.yaml с результатом US1 без сборки root CHANGELOG.md; проверить штатным валидатором фрагментов перед T008 — #6182.
- [ ] T013 В specs/224-dev-stand-completion/validation.md свести полную приёмку FR-001–018/SC-001–006, T001–T012 и F249 T038/#6786; завершить общий converge, required PR checks exact SHA/base и один release-full замороженного кандидата; проверить live feature closeout и только затем закрыть общую #6180 с подробным русским комментарием; выпуск/развёртывание требуют отдельного разрешения.

## Dependencies and execution order

Исторические ID сохраняются, порядок задан фазами и зависимостями:
T001 → T003 → T004 → T005 → T007 → T006 → T002 → T008.
T009 зависит от принятой US1 и доступности единственного стенда.
T010 можно исследовать изолированно после T008, но код требует уточнённого
проекта/checklist/analyze/sync. T011 зависит от T009/T010, schema-changing
приёмка также от F249 T038/#6786. T012 следует за T011.
T013 зависит от всех задач и фактической широкой приёмки, не от числа тестов.
Неисполненные внешние/ручные ворота оставляются открытыми. Commit approval
не разрешает merge, live adoption, release или deploy.

## Requirement coverage

| Требования | Задачи | Проверка |
|---|---|---|
| FR-001–003, SC-001 | T001,T003,T004 | Git origins, cwd, aliases, отрицательные случаи |
| FR-004–007, SC-002–003 (US1) | T003–T007 | прежний lock, binding crash/ошибка, отсутствие shared effects |
| FR-008–011, SC-004 | T009,T011 | фактический Dev и службы/образы, negative stopped service |
| FR-012–013, SC-003–004 (promotion/schema) | T010,T011; F249 T038 | crash/recovery, живой совместимый откат |
| FR-014, SC-005 | T012 | Dev TCC до/update/relaunch/после |
| FR-015–016 | T003–T013 | metadata-only evidence, штатные paths/gates |
| FR-017–018, SC-006 | T008–T013 | source/PR/CI/runtime/release, live closeout |

## Parallel opportunities

Маркеров [P] нет: текущие кодовые задачи меняют общий harness и один suite.
US1: чтение документации независимо от изолированных тестов;
US2: разбор существующих доказательств можно вести во время US1 checks,
но живой стенд не занимать двумя проверками. US3: анализ старых журналов
независим от US2 чтения; проект/чеклист/код меняются последовательно.

## Implementation strategy

Сначала US1 и изолированная матрица; после validation/commit approval — PR checks.
Затем фактическая US2, отдельно уточнённая US3 и согласованные живые проверки.
Ни перенос root, ни повторный lifecycle, ни второй Dev не нужны.
