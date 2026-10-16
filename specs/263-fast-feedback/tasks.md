# Tasks: F263 — восстановление и независимая карта поведения

Исходные задачи реконструированы из канонических полей семи issues. Исходного
файла не найдено; все старые состояния оставлены открытыми. Здесь не зафиксированы
придуманные node IDs или измерения. Фаза US4 исполнима независимо от US1–US3.

## Setup и исходные измерения

- [ ] T001 Перепроверить полные требования F263 в specs/263-fast-feedback/spec.md, checklists и analyze. Issue: #6904.
- [ ] T002 Сохранить три исходных запуска четырёх оригинальных node IDs, условия и медианы в specs/263-fast-feedback/validation.md. Issue: #6904.

## US1 — чтение

- [ ] T003 [US1] Согласовать правила целых разделов и четыре сценария в docs/agent-guidance/ и specs/263-fast-feedback/validation.md. Issue: #6905.

## US2 — данные

- [ ] T004 [US2] Упростить только четыре исходных теста apps/server/tests/ без потери ready/audio/assertions/negative cases. Issue: #6906.
- [ ] T005 [US2] Записать три после-замера приworkers1 в specs/263-fast-feedback/validation.md. Issue: #6906.

## US3 — выполнение

- [ ] T006 [US3] Проверить subprocess collection и разбиение apps/server/scripts/run_local_postgres_tests.sh без повторов. Issue: #6907.
- [ ] T007 [US3] Подтвердить strictpriority/workercap/errors/empty/cleanup и реальныеPG/RLS в specs/263-fast-feedback/validation.md. Issue: #6907.
- [ ] T008 [US3] Выполнить два независимых запуска и отдельные замерыworkers1/2 в specs/263-fast-feedback/validation.md. Issue: #6907.

## US4 — активная независимая часть

- [X] T009 [US4] Добавить картуmatching/API/model→существующиеcalendarcontract/integration в scripts/ci-behavior-tests.py и убрать дубли этапов в infra/scripts/ci-local.sh; регрессии в apps/server/tests/contract/test_ci_cd_contract.py. Issue: #6908.

T009: сначала текущие specify/clarify/plan/checklist review/analyze/issue sync,
затем red→green; оба календарных файла с настоящимPG и requiredperformance.
Покрыть mixed/covered, missing/empty/syntax/symlink, skip/deselect/failure,
unknown/shared/rename/base и неизменную изоляциюcabinet. Не зависит отT002/T005:
fixtures, правила чтения и разбиение не изменяются.

## Общая приёмка

- [ ] T010 Сверить все истории, review/converge/validation и changes/unreleased/F263.yaml. Issue: #6909.
- [ ] T011 После разрешений пройтиcommit/PR/exact-SHAchecks и общую приёмку, записать specs/263-fast-feedback/validation.md. Issue: #6909.

## Зависимости и порядок

Исходныйbenchmark:T001→T002→T004→T005; US1:T001→T003; US3:T001→T006→T007→T008.
Текущая независимаяUS4:новое ревью/analyze/sync→T009. T010 требует всеUS;
T011 послеT010. Параллельных изменений общих скриптов сейчас нет.
Общая issue#6901 не владеетT000: это исторический резерв; согласовать её с
реальной итоговой задачей до закрытия, не заводить фиктивную задачу.
