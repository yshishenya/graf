# Tasks: Повторная обработка no-speech

**Risk lane**: `high-risk-feature`.

- [X] T001 [P] [US1] Добавить regression coverage для imported no-speech result,
  допуска новой попытки и нового attempt ordinal в
  `apps/server/tests/integration/test_processing_failures.py`.
- [X] T002 [P] [US2] Добавить regression coverage, что старый no-speech result
  не перекрывает active workflow в
  `apps/server/tests/contract/test_processing_status_contract.py`.
- [X] T003 [US1] Разрешить terminal no-speech result в общем admission boundary
  `apps/server/src/twobrain_rec_server/processing/store.py`, сохранив все
  существующие fences.
- [X] T004 [US2] Ограничить no-speech status override текущим workflow в
  `apps/server/src/twobrain_rec_server/processing/status.py`.
- [X] T005 [US3] Прогнать focused matrix, quickstart, diff check и fast/full CI;
  записать evidence в `specs/204-terminal-no-speech-recovery/quickstart.md`.
- [X] T006 [US3] После approval проверить exact-SHA production deployment и
  metadata-only smoke на существующей записи.
- [X] T007 [US3] Исправить lazy Temporal dispatch в новых попытках и manual
  check и добавить API regression coverage без заранее заполненного
  `app.state.temporal_client` в
  `apps/server/src/twobrain_rec_server/api/processing.py` и
  `apps/server/tests/contract/test_processing_status_contract.py`.
- [X] T008 [US3] Разрешить переход свежей Temporal-попытки `starting → submitting`
  и добавить regression на реальный submit-путь, чтобы activity не завершалась
  ошибочно при ещё не сохранённой промежуточной проекции.
- [X] T009 [US3] После durable `WAITING_RETRY` возвращать существующий
  idempotent provider job через `submitted` и не зацикливать single-step poll;
  добавить integration regression на recovery готового job.
