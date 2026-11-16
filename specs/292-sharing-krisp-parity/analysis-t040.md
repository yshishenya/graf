# T040 — анализ требований до реализации

Срез FR-027 / T016–T017 prerequisite. Проверены spec/plan/tasks/quickstart и production-independent цепочка workflow→prepare-ci-apt→защищённая проверка Ubuntu24.04. Два release jobs и один PR job используют helper; server-static и прочие задания не используют его и остаются на прежнем runner. Существующий validator содержит2runner requirements и synthetic fixture, поэтому входит в минимальное изменение; для проверки каждого job допустимо переиспользовать job_block, не искать runner в соседнем job.

Clarify: неоднозначностей нет, helper не расширяется на26.04, tests/permissions/SHA/timeout остаются. Constitution check до и после плана PASS: действие только возвращает совместимую среду проверок; публикация и production не затрагиваются. Requirements C0/H0, покрытие текущего среза1/1; полнота всей F292 и приёмка продукта не заявляются. Checklist независимо проверяется до кода.
