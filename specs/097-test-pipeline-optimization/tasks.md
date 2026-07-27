# Tasks: быстрый и достоверный test pipeline

## Phase 1 — contract first

- [X] T001 [P] Добавить `requires_postgres`, `governance`, `strict_rls` и `spike` markers в `apps/server/pyproject.toml`.
- [X] T002 [P] Добавить contract tests для PostgreSQL-only URL, lane flags, cleanup, metadata-only output и phase accounting в `apps/server/tests/contract/test_local_test_pipeline_contract.py`.
- [X] T003 [P] Добавить dependency `pytest-xdist` в `apps/server/pyproject.toml` и обновить `apps/server/uv.lock`.

## Phase 2 — PostgreSQL boundary

- [X] T004 Реализовать безопасное создание/удаление worker и clean database в `apps/server/tests/fixtures/postgres_test_database.py`.
- [X] T005 Перевести `apps/server/tests/conftest.py` на Alembic head, bounded reset и deterministic seed.
- [X] T006 Перевести `apps/server/tests/fixtures/postgres_rls.py` на общий disposable URL и строгую ошибку при отсутствии full-run boundary.
- [X] T007 Перевести ручные локальные database fixtures в `apps/server/tests/unit/test_app_lifecycle.py`, `apps/server/tests/integration/test_public_landing.py`, `apps/server/tests/integration/test_health_readiness.py`, `apps/server/tests/integration/test_production_docs_exposure.py` и `apps/server/tests/contract/test_public_analytics_contract.py`.
- [X] T008 Перевести migration tests в `apps/server/tests/integration/test_postgres_migrations.py` и `apps/server/tests/integration/test_meeting_detection_migrations.py` на clean PostgreSQL database.
- [X] T009 Удалить устаревшую test-only dependency and URLs; не удалять runtime PostgreSQL model/migration semantics.

## Phase 3 — lanes

- [X] T010 Создать `apps/server/scripts/run_local_postgres_tests.sh` с loopback-only disposable container, retry и cleanup.
- [X] T011 Добавить worker-count, baseline collection и phase-union guard в runner.
- [X] T012 Изменить `infra/scripts/ci-local.sh` на `--fast`, `--full`, `--governance` с сохранением full default.
- [X] T013 Отметить strict RLS, governance и optional spike tests; не добавлять skip/deselect ради скорости.

## Phase 4 — validation

- [X] T014 Запустить focused audio/download tests и fast lane.
- [X] T015 Запустить PostgreSQL focused, migration и RLS lanes.
- [X] T016 Запустить полный runner, lint, compile, lock, Compose config и RLS boundary.
- [X] T017 Сохранить aggregate timings/counts в `specs/097-test-pipeline-optimization/validation/` без sensitive content.
- [X] T018 Выполнить Ponytail review diff и обновить CHANGELOG/closeout evidence.

## Phase 5 — audit remediation

- [X] T019 [US1] Добавить owner-default и shared-denied regression coverage в apps/server/tests/integration/test_artifact_egress_policy.py и apps/server/tests/integration/test_cabinet_meeting_detail.py.
- [X] T020 [US1] Изменить transient default в apps/server/src/twobrain_rec_server/cabinet/egress.py на owner-only audio download без расширения доступа другим viewers.
- [X] T021 [P] [US2] Удалить test-only legacy apps/server/src/twobrain_rec_server/ingest/access_policy.py и apps/server/tests/integration/test_access_placeholders.py.
- [X] T022 [P] [US2] Переместить HTTP/API tests в apps/server/tests/integration/, pure worker payload checks в apps/server/tests/unit/ и historical evidence в apps/server/tests/governance/.
- [X] T023 [US3] Разделить full runner на ordinary, governance и strict RLS phases в apps/server/scripts/run_local_postgres_tests.sh, infra/scripts/ci-local.sh и apps/server/tests/contract/test_local_test_pipeline_contract.py.
- [X] T024 [US3] Выполнить focused owner-audio, fast, governance и full validation; обновить CHANGELOG.md и specs/097-test-pipeline-optimization/validation/summary.md.
