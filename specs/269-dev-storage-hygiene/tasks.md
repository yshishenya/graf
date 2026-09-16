---
description: "Task list for Feature 269 — гигиена дискового пространства Dev-стенда и ускорение CI"
---

# Tasks: Гигиена дискового пространства Dev-стенда и ускорение CI

**Input**: Design documents from `/specs/269-dev-storage-hygiene/`

**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Tests**: Включены — лейн high-risk требует тестов; тесты пишутся до реализации и должны падать.

**Organization**: Задачи сгруппированы по user stories: US1 — стабильный размер стенда (P1), US2 — быстрый CI (P2), US3 — отчёт об уборке (P3).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: можно выполнять параллельно (разные файлы, нет зависимостей)
- **[Story]**: US1, US2, US3
- Все пути указываются от корня репозитория

## Path Conventions

Монорепозиторий: `scripts/`, `infra/scripts/`, `.github/workflows/`, `tests/governance/`, `infra/dev/`, `docs/agent-guidance/`, `changes/unreleased/`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Подготовка новых файлов контрактов и тестового каркаса

- [x] T001 [P] Создать `tests/governance/test_dev_state_retention.py` со вспомогательными фикстурами (изолированный `GRAF_DEV_STATE_DIR` через `tmp_path`, синтетический манифест с `parent_manifest_id`, подмена `dev_harness._run_command`) по образцу `tests/governance/test_graf_local_adapter.py`
- [x] T002 [P] Создать `changes/unreleased/F269.yaml` с обязательными полями из `changes/unreleased/README.md`: `schema_version: 1`, `feature_id: 269`, `category`, `summary`, `issue: 7089`, `tasks`, `compatibility`, `known_limitations`, `release_notes` (финализируется в T028)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Общие помощники политики хранения, от которых зависят US1 и US3

**⚠️ CRITICAL**: US1 и US3 не начинаются до завершения этой фазы

- [x] T003 Добавить в `scripts/dev-harness.py` помощник `_remove_within_state(path, state_root, kind, receipt)`: удаляет файл/каталог только внутри `state_root`, считает байты, добавляет запись `{path, bytes, kind}` в квитанцию; при выходе за пределы state root — `HarnessError`
- [x] T004 [P] Добавить в `scripts/dev-harness.py` вычисление политики `_retention_plan(root, *, keep_extra=())`: `active_manifest_id` из `active-manifest.json`, `rollback_target_id = parent_manifest_id` активного, `keep = {active: [app_bundle], target: [archive, app_bundle]}` плюс `keep_extra` (свежесобранный кандидат), `remove` — остальные каталоги `artifacts/*` (Data Model §RetentionSet); отсутствие артефактов у целевого не является ошибкой
- [x] T005 [P] Добавить в `scripts/dev-harness.py` построитель квитанции `_prune_receipt(...)` с полями из `specs/269-dev-storage-hygiene/contracts/prune-receipt.schema.json`: `schema_version="dev-prune-receipt.v1"`, `dry_run`, `removed[]` c `kind ∈ {artifact_set, archive, app_bundle, build_dir, schema_snapshot, app_backup, image_tag}`, `kept[]`, `bytes_freed`, `status ∈ {ok, partial}`, `partial_reasons[]`

**Checkpoint**: Помощники готовы — US1 и US3 можно реализовывать параллельно с US2

---

## Phase 3: User Story 1 - Стабильный размер локального стенда (Priority: P1) 🎯 MVP

**Goal**: После сборки/продвижения/отката на диске остаётся только архив целевого отката и приложения активного и целевого манифестов; снапшоты завершённых переходов и остаточные копии приложения удаляются; откат сохраняется.

**Independent Test**: Выполнить цикл build → promote → prune-подобная проверка на изолированном state root с подменённым Docker и убедиться, что лишние каталоги и теги удалены, архив целевого создан, а `rehydrate` его читает.

### Tests for User Story 1 (write first, must FAIL) ⚠️

- [x] T006 [P] [US1] Тесты в `tests/governance/test_dev_state_retention.py`: `build` не создаёт `runtime-images.tar`, удаляет `artifacts/<id>/build` и сохраняет `GRAF Dev.app`
- [x] T007 [P] [US1] Тесты в `tests/governance/test_dev_state_retention.py`: `promote` создаёт архив только для нового целевого манифеста, удаляет прочие наборы и их теги `graf-dev-immutable:*`, не трогает активный и целевой; при отсутствии образов целевого — `HarnessError` до публикации active pointer
- [x] T008 [P] [US1] Тесты в `tests/governance/test_dev_state_retention.py`: каталог `schema-transactions/<op>` удаляется при `phase ∈ {complete, recovered}` и сохраняется при незавершённых фазах
- [x] T009 [P] [US1] Тесты в `tests/governance/test_dev_state_retention.py`: остаточный `transactions/previous-*.app` удаляется при успешной операции; при `rollback-required.json` удаление не выполняется

### Implementation for User Story 1

- [x] T010 [US1] Убрать `docker image save` из `GrafLocalAdapter.build` и удалять `artifact_root/build` после успешной сборки в `scripts/dev-harness.py` (R1, R2)
- [x] T011 [US1] Реализовать `_ensure_rollback_archive(manifest)`: `docker image save` всех digest целевого манифеста в `artifacts/<target>/runtime-images.tar`; вызывать в `promote` после успешного smoke и до `_publish_active`; при недоступности любого образа — `HarnessError` (fail-closed) в `scripts/dev-harness.py`
- [x] T012 [US1] Применять `_retention_plan` после успешных `build`/`promote`/`rollback`: в `build` передавать `keep_extra=(новый кандидат,)`, чтобы его приложение не удалялось до `promote`; в `promote`/`rollback` — без `keep_extra`; удалять наборы вне политики, не падать при отсутствии артефактов целевого и снимать теги `graf-dev-immutable:<manifest>-*` через `docker image rm` (без глобальных prune) в `scripts/dev-harness.py`
- [x] T013 [US1] Удалять `schema-transactions/<operation_id>` при переходе фазы в `complete`/`recovered` в `_schema_phase` в `scripts/dev-harness.py` (R4)
- [x] T014 [US1] Обновить сообщения `rehydrate`/`rollback` для манифеста вне политики: точный текст `immutable Dev image archive is unavailable; rebuild a new candidate` (contracts/dev-harness-cli.md) в `scripts/dev-harness.py`
- [x] T015 [US1] Удалять остаточные `transactions/previous-*.app` при успешном завершении операций под общим lock в `scripts/dev-harness.py` (R5)

**Checkpoint**: US1 даёт стабильный потолок диска и сохраняет откат

---

## Phase 4: User Story 2 - Быстрая повторная Swift-проверка (Priority: P2)

**Goal**: Повторный запуск macOS-проверки использует кэш Swift-сборки; доказательства привязаны к продуктам сборки, а не ко всему `.build`.

**Independent Test**: Статическая проверка контракта workflow и запуск `ci-local.sh --fast`; в evidence-записи присутствуют `macos-product-*`, отсутствует `macos-build`.

### Tests for User Story 2 (write first, must FAIL) ⚠️

- [x] T016 [P] [US2] Расширить `tests/governance/test_ci_cd_contract.py`: в `.github/workflows/macos-pr.yml` и `.github/workflows/release-full.yml` есть шаг `actions/cache` с путями `apps/macos/.build`, `~/.cache/org.swift.swiftpm`, `~/Library/Caches/org.swift.swiftpm`, ключом с `hashFiles('apps/macos/Package.resolved')` и `swift-version` 6.0.3; шаги сборки и тестов не обёрнуты условиями кэша
- [x] T017 [P] [US2] Расширить `tests/governance/test_ci_cd_contract.py`: `infra/scripts/ci-local.sh` передаёт `--artifact` с именами `macos-product-*` и `macos-tests` и не передаёт `macos-build=<.build>`

### Implementation for User Story 2

- [x] T018 [US2] Добавить шаг `actions/cache@v4` в job `native` файла `.github/workflows/macos-pr.yml` перед `swift build` (paths/key/restore-keys из contracts/ci-workflows.md §1)
- [x] T019 [US2] Добавить тот же шаг в job `macos-full` файла `.github/workflows/release-full.yml` (ключ обязан совпадать с macos-pr, чтобы кэш переиспользовался)
- [x] T020 [US2] Заменить в `infra/scripts/ci-local.sh` артефакт `macos-build=<.build>` на `${repo_root}/apps/macos/.build/debug/<Product>` для `TwoBrainRecApp`, `ContractValidation`, `MeetingMuteTruthRuntimeProof`, `WebRTCAEC3Validation`, `LeakageValidation`, `TwoBrainRecMacOSPackageTests.xctest`; добавлять только существующие пути (R7)

**Checkpoint**: US2 ускоряет повторные проверки, не ослабляя доказательства

---

## Phase 5: User Story 3 - Понятный отчёт об уборке (Priority: P3)

**Goal**: Явная команда `prune` с dry-run и JSON-квитанцией; `status` показывает политику хранения и объём артефактов.

**Independent Test**: `prune --dry-run --json` не изменяет FS и печатает квитанцию по схеме; `prune` при `rollback-required`/незавершённом переходе завершается с кодом 2.

### Tests for User Story 3 (write first, must FAIL) ⚠️

- [x] T021 [P] [US3] Тесты в `tests/governance/test_dev_state_retention.py`: `prune --dry-run` не изменяет FS, печатает квитанцию с `schema_version`, `removed[]`, `kept[]`, `bytes_freed`, `status` и не пишет `prune-history.jsonl`; `prune` дописывает квитанцию в `prune-history.jsonl`; `prune` при незавершённом переходе или `rollback-required.json` — exit 2 без изменений; путь вне state root отклоняется
- [x] T022 [P] [US3] Тест в `tests/governance/test_dev_state_retention.py`: недоступность Docker даёт `status: partial` с `partial_reasons`, файловые удаления при этом выполнены

### Implementation for User Story 3

- [x] T023 [US3] Добавить подкоманду `prune` (`--dry-run`, `--json`) в `parser()`/`dispatch()` и реализовать `operation_prune` в `scripts/dev-harness.py`: общий state lock, проверки T021-ограничений, применение `_retention_plan`, удаление «сиротских» каталогов завершённых переходов (не покрытых очисткой T013) и остаточных `previous-*.app`, снятие тегов, дописывание квитанции в `prune-history.jsonl` (кроме dry-run); Docker-ошибки → `partial` (R8)
- [x] T024 [US3] Дополнить `operation_status` в `scripts/dev-harness.py` блоком `retention`: `active_manifest_id`, `rollback_target_id`, `artifacts_bytes`, `archive_present` (без вызовов Docker) (FR-010, SC-006)
- [x] T025 [US3] Проверить структуру квитанции `prune` против `specs/269-dev-storage-hygiene/contracts/prune-receipt.schema.json` без новых зависимостей (ручная проверка полей в тесте)

**Checkpoint**: Все три истории функциональны независимо

---

## Phase 6: Polish & Cross-Cutting Concerns

- [x] T026 [P] Обновить `infra/dev/README.md`: политика хранения (один архив целевого отката), команда `prune`, порядок `rehydrate → rollback`, что удаляется автоматически
- [x] T027 [P] Обновить `docs/agent-guidance/local-development.md`: эксплуатация после фичи (где смотреть `retention`, когда запускать `prune`, что не удаляется)
- [x] T028 Финализировать `changes/unreleased/F269.yaml`: поля `tasks`, `compatibility`, `known_limitations`, `release_notes` по итогам реализации
- [x] T029 Запустить фокусную валидацию: `python3 -m pytest -q tests/governance/test_dev_state_retention.py tests/governance/test_graf_local_adapter.py tests/governance/test_ci_cd_contract.py`, portable harness self-test (`PYTHONPATH=harness/src`), `bash -n` для `infra/scripts/ci-local.sh` и `scripts/dev-harness.py`-обёртки, `python3 scripts/check_spec_kit_governance.py`, `infra/scripts/ci-local.sh --fast`
- [ ] T030 Live-проверка по `specs/269-dev-storage-hygiene/quickstart.md` на единственном стенде: `status` → `prune --dry-run` → `prune` → `status`/`smoke --live` → `rehydrate` целевого → `rollback --dry-run`; измерить длительность `promote` и подтвердить однократный `docker image save` (FR-015/SC-007); по отдельному согласованию — live `rollback` на предыдущий манифест и возврат (SC-003), иначе зафиксировать в evidence ограничение проверки dry-run и rehydrate

  > Частично выполнено: `status` с блоком `retention`, `prune --dry-run` (план 718 МБ) и `prune` (718 МБ освобождено, квитанция в `prune-history.jsonl`) проверены на живом стенде; `smoke` подтверждает backend/worker/database/storage, но `app_identity`, `app_presentation` и `exact_source_sha` недоступны, потому что `/Applications/GRAF Dev.app` удалён внешним процессом (параллельная сессия Feature 267 на том же SHA `751d52a93`); по решению владельца восстановление не выполняется. Live `rehydrate`/`rollback` с этой ветки невозможны из-за проверки exact-SHA checkout. Тайминг promote (FR-015/SC-007) не измерен по той же причине.

- [x] T031 Запушить ветку, дождаться GitHub `governance-fast`, `macos-pr`, `pr-metadata` на точном SHA; проверить cache miss на первом запуске и cache hit на повторном; подготовить описание PR с лейном, командами, результатами и evidence; `release-full` — на замороженном кандидате

  > Cache miss (сохранение 299 МБ) и cache hit подтверждены логами на SHA `16ccdb6`; выигрыш от обновления mtime восстановленных артефактов будет измерен на ближайшем PR с изменениями `apps/macos` (этот PR не запускает native-job, потому что не меняет Swift-код). Ветка перебазирована на `origin/master` по решению владельца.


---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: без зависимостей
- **Foundational (Phase 2)**: T003–T005, блокирует US1 и US3; US2 от них не зависит
- **US1 (Phase 3)**: после Foundational; T010–T015 зависят от T003–T005
- **US2 (Phase 4)**: может идти параллельно US1 (другие файлы)
- **US3 (Phase 5)**: после Foundational и T023 (зависит от T003–T005)
- **Polish (Phase 6)**: после завершения нужных историй; T029–T031 — в конце

### Within Each User Story

- Тесты пишутся до реализации и должны падать
- Помощники → реализация операций → интеграция
- US1 завершается до перехода к US3 (общая механика удаления)

### Parallel Opportunities

- T001/T002 (Setup), T004/T005 (Foundational)
- T006–T009 (тесты US1) и T016/T017 (тесты US2) — параллельно
- T018–T020 (US2) не зависят от US1
- T026/T027 (документация) — параллельно

---

## Parallel Example: User Story 1

```bash
# Тесты US1 (разные аспекты, один файл — писать последовательно во избежание конфликтов):
Task: "T006 build без архива и с удалением build/"
Task: "T007 promote создаёт архив целевого и чистит остальное"
Task: "T008 снапшоты схемы по фазе"
Task: "T009 остаточные копии приложения"
```

---

## Implementation Strategy

### MVP First (User Story 1)

1. Phase 1 → Phase 2 → Phase 3 (US1)
2. Остановиться и проверить: лишние наборы удалены, архив целевого создан, `rehydrate` работает
3. Прямо это решает основную жалобу (рост `artifacts/` и торможение машины)

### Incremental Delivery

1. US1 → стабильный размер стенда
2. US2 → быстрый CI (независимо, можно параллельно)
3. US3 → управляемая уборка и отчёт
4. Polish → документация, changelog, live-проверка, GitHub-гейты

---

## Notes

- [P] — разные файлы, нет зависимостей
- Никакие задачи не отмечают пункты reviewer-чеклистов (`checklists/retention-safety.md` — 35/35, ревью выполнено)
- `scripts/dev-harness.py` меняется многими задачами — правки последовательные
- Коммиты — только после явного одобрения пользователя
