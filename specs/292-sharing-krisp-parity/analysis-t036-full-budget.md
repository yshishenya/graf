# T036 — согласованность выпускного бюджета

Lane: active Spec Kit slice / high-risk infrastructure. Источник намерения — FR-027 и T016/T017: полный release-full обязателен и должен завершиться. Scope: только `.github/workflows/release-full.yml`, `scripts/validate-full-ci-workflow.py`, задача, checklist/review и evidence/фрагмент. Нового продуктового требования нет.

Run43226719865 на da64bdd2 завершился canceled после 30 минут server-phases; aggregate failed. В артефакте timings329 setup/call/teardown, все passed: setup1445.59с, call198.53с, teardown47.96с, медиана setup3.89с. До прерывания журнал показал42% на288тестах, после —329 законченных. Прогноз strict около60мин; конечный бюджет90мин покрывает оставшиеся serial_performance, RLS verification и подготовку. Изоляция базы дорога, но её изменение — самостоятельный риск и вне минимального исправления.

Clarify: повышается только конечный предел server-phases; нет параллелизации strict, skip, retry, изменения тестов/RLS или performance threshold. Старые canceled evidence не разрешают выпуск, незавершённая нотарифицированная сборка da64 не выдаётся за новый source. Новые PR и один полный запуск нового кандидата обязательны. Точечная проверка: `python3 scripts/validate-full-ci-workflow.py --self-test` и обычный validator, diff/check/governance. Нужен независимый checklist PASS до кода, затем независимый обзор фактического diff.

Converge: один partial HIGH в FR-027, задачаT036, покрытие1/1. C0/H0 по противоречиям/неясности; реализация/CI/выпуск ещё не выполнены. Runtime, callers, fixtures, config вне job timeout, exports и пользовательские данные не меняются. Дополнительный риск — больший конечный расход времени runner при зависании; ограничение90мин сохраняется.

Независимое чтение обнаружило текущий предел validator1..60. План: только server-phases допускает1..90, прочие jobs1..60. Self-test принимает90 и отклоняет91 для server-phases, отклоняет61 для другого job. Это сохранение конечного ограничения, без изменения других инвариантов.

GitHub check-run131212115584 annotations подтверждает дословно: `The job has exceeded the maximum execution time of 30m0s`. Итог conclusion=cancelled, aggregate=failure; это прерывание по времени, а не успешная полная проверка.
