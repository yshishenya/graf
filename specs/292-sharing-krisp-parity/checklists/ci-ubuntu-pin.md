# T040 — поддерживаемая Ubuntu для APT

Reviewer-owned: независимая проверка требований до кода.

- [x] CHK001 FR-027 и наблюдаемый26.04 failure однозначно задают ubuntu-24.04 ровно для3прямых callers helper; guard24.04 остаётся неизменным, прочие jobs вне изменения.
- [x] CHK002 План учитывает оба workflow, существующий release validator/self-test fixture и contract consumer; точный SHA/base, permissions/timeouts, состав тестов/full8частей и create-once сохраняются.
- [x] CHK003 Определены RED→GREEN/негативный latest/self-test/actual/focused, независимый обзор и PR gates; выпуск/merge/deploy не делегированы и не объявлены пройденными.

Независимая проверка требований: PASS, 3 checked / 0 unchecked, C0/H0. Доказательства и пределы: `../review-t040-requirements.md`. Реализация и CI этим результатом не подтверждаются.
