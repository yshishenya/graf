# A10 focused partition requirements

- [x] CHK001 Is the changed-server-only opt-in explicit, with ordinary focused and user selection semantics preserved? [FR-055]
- [x] CHK002 Are nonempty baseline, disjoint complete execution, strict precedence, serial safety, fail-fast and cleanup specified? [FR-055]
- [x] CHK003 Do executable negative cases and a real equal-selection paired measurement distinguish local proof from final hosted evidence? [SC-023]

Reviewer-owned requirements gate; implementation does not mark this checklist.

## Независимая проверка требований — 2026-09-13

Рецензент: `requirements_review`, отдельно от исполнителя A10. Рассмотрены
FR-055 / SC-023, A10 implementation design, T078–T079, фактический
`run_changed_server_tests`, PostgreSQL runner и его collection/marker contract.

- **CHK001 PASS.** FR-055 и plan ограничивают изменение явным
  `--focused --partitioned` в changed-server caller; обычный focused сохраняется.
  Пользовательские селекторы, включая выражение `-m`, сохраняются без изменений.
  Точный селектор фазы `--graf-phase-file` в `test_resources.py` использует общий
  `phase_for` и проверяет совпадение полного набора node IDs фазы с исходной
  коллекцией; второе выражение `-m` и отбор по префиксу не используются.
  Несовместимые настройки xdist отклоняются
  до запуска Docker. Причина изменения подтверждена кодом: caller задаёт
  `GRAF_TEST_WORKERS`, но текущая focused ветка не передаёт `-n` в pytest.
- **CHK002 PASS.** FR-055 требует непустой исходный набор и выполнение каждого
  выбранного случая ровно один раз, ограничивает обычную фазу четырьмя процессами
  и оставляет performance/strict последовательными. При двух маркерах действует
  strict; ошибка останавливает последующие фазы. Plan сохраняет существующие
  отдельные worker databases и cleanup; SC-023 требует проверки этих свойств.
- **CHK003 PASS.** T078 ставит исполняемые проверки до изменения runner/caller.
  SC-023 включает состав без пересечений, селекторы, collection failure,
  collect-only, последовательные фазы и cleanup. T079 требует реальный парный
  замер при одинаковом выбранном наборе и Python/DB, с PASS без пропусков;
  окончательное hosted evidence записывается отдельно.

Итог: **PASS 3/3, открытых замечаний проверки требований A10 нет**.
Далее обязательны clean analyze и привязка задач к issue до реализации.
Это приёмка требований: код и другие документы не менялись, тесты, сборки,
Docker и GitHub не запускались. Реализация и её измерения остаются T078–T079.
