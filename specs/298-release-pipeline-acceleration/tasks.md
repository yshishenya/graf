# Tasks: Ускорение релизного конвейера без ослабления гейтов

**Feature**: `298-release-pipeline-acceleration`

**Input**: `specs/298-release-pipeline-acceleration/spec.md`, `plan.md`

## Phase 1: Планирование фаз и подготовка кластера

- [X] T001 [US1] Разделить strict-доказательства по замыканию фикстур в
  `apps/server/tests/fixtures/test_resources.py`: самодостаточный кластер →
  parallel; общая строгая база, неизвестное замыкание и `serial_performance` →
  strict; изолированную фикстуру добавить в ресурсный маркер. (Issue #8161)
- [X] T002 [US3] Заменить пятисекундный таймаут docker на общий бюджет
  готовности 60 с и вызов не дольше остатка бюджета в
  `apps/server/tests/fixtures/postgres_test_database.py`; сохранить две попытки
  старта, отдельный лимит очистки и имя стадии при отказе. (Issue #8161)
- [X] T003 [US1] Пометить `serial_performance` четыре теста мониторинга с
  настенными границами в
  `apps/server/tests/integration/test_billing_monitoring_postgres.py`, чтобы они
  остались в последовательной фазе. (Issue #8161)

## Phase 2: Ранние контрактные доказательства

- [X] T004 [US2] Добавить группы `openapi-contract`, `copy-conventions` и
  `account-routes` в `scripts/ci-behavior-tests.py`, исполнять требующие
  приложение проверки через postgres-раннер и закрепить обязательные имена
  тестов. (Issue #8161)

## Phase 3: Полный прогон и параллельные наборы

- [X] T005 [US1] Сократить глубину checkout в `.github/workflows/release-full.yml`
  до 1 там, где история не нужна, и до 2 в static ради fallback `HEAD^`;
  валидатор workflow проходит. (Issue #8161)
- [X] T006 [US3] Перевести `tests/governance` и контракты раннера на `-n 4`,
  закрепить `pytest-xdist==3.8.0` в toolchain и сохранить последовательный
  fallback локально без xdist в `infra/scripts/ci-local.sh` и workflow. (Issue #8161)

## Phase 4: Проверка и приёмка

- [X] T007 [US1] Подтвердить инвентарь фаз на полном сборе: объединение равно
  baseline, strict содержит только общие и настенные доказательства; прогнать
  контракты, governance-предохранитель, lint и валидатор workflow. (Issue #8161)
- [ ] T008 [US1] Проверить обязательные GitHub-проверки PR на точном SHA и один
  полный `release-full` на замороженном кандидате; сравнить длительности и
  доказательство покрытия шардов; закрыть фичу только после приёмки. (Issue #8161)

Dependency: T001 → T002 → T003; T004; T005; T006 → T007 → T008.
