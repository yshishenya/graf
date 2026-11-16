# T040 — независимая проверка требований до кода

Дата: 2026-11-17. Проверяющий: отдельный агент `t040_requirements_reviewer`.
Рабочая копия: `/Users/yshishenya/.codex/worktrees/f292-ci-ubuntu-pin/crisp`.
Ветка: `codex/f292-ci-ubuntu-pin`.
Базовый HEAD: `e7723baf8a6890fff54956007baa0b29b3047892`.
Режим: активный срез Spec Kit, независимая проверка требований инфраструктурной предпосылки FR-027; код и внешнее состояние не изменяются.

## Результат

**PASS требований T040: 3 подтверждено / 0 неподтверждено; C0 / H0.**
Результат относится только к полноте, ясности и проверяемости требований. Он не подтверждает реализацию, успешный CI, слияние, выпуск или приёмку всего F292.

## Доказательства по пунктам

- CHK001. `spec.md`, раздел T040, явно требует поддерживаемую Ubuntu 24.04 noble и сохраняет проверки ОС/пакетов. `research.md` связывает причину с PR8118/run43965043808. Независимо прочитан `/private/tmp/graf-f292-t039-governance-all.log`: строки920–925 показывают Ubuntu26.04.1/ubuntu-26.04, строки1937–1938 — `CI APT preparation: expected Ubuntu 24.04 noble` и завершение с кодом1. Фактический `prepare-ci-apt.sh` проверяет ID ubuntu, VERSION_ID24.04 и VERSION_CODENAME noble, а также среду GitHub-hosted Linux, архитектуру и доверенные источники пакетов. Поиск по всем `.github/workflows` нашёл ровно3 прямых вызова: governance-fast:255, release-full server-phases:298, release-full server-parallel:448. Текущие3 runners — ubuntu-latest; план меняет только их на ubuntu-24.04. scope/reserve/static/aggregate/macOS явно исключены.
- CHK002. `plan.md`, раздел T040, охватывает оба workflow,2существующих runner requirements и2значения self-test fixture в `scripts/validate-full-ci-workflow.py`, а также предметный контракт `apps/server/tests/contract/test_ci_cd_contract.py`. Фактически у валидатора есть3отдельных server runner requirements, из которых меняются только phases/parallel, и синтетический пример тех же jobs. `job_block()` и YAML-чтение `release_full_jobs()` уже существуют. Требования сохраняют команды, permissions/timeouts, точный SHA/base, состав обязательных проверок,8частей parallel и однократное резервирование. Это согласовано с конституцией VI и `release-and-validation.md`: каждый новый код требует собственных exact-SHA PR gates, релиз — отдельной полной проверки замороженного кандидата.
- CHK003. `quickstart.md`, раздел T040, задаёт первоначальный отказ нового контракта, последующий GREEN, точный focused pytest selection, self-test и проверку настоящего workflow, ruff и diff check. План дополнительно требует отрицательный self-test возврата phases/parallel на latest. `tasks.md` оставляет T040 незавершённым и требует независимый обзор, анализ, issue sync до кода и текущие PR gates после него. release-full разрешён только отдельному оператору для нового замороженного кандидата; прежний failed run не годится. Полномочий на merge/release/deploy у проверяющего нет.

## Прочитанные основания и ограничения

Прочитаны AGENTS.md, guidance index, `spec-kit-flow.md`, применимые разделы конституции V/VI и Development Workflow And Quality Gates, правила точного SHA/base из `release-and-validation.md`; актуальные spec/plan/tasks/quickstart/research и `analysis-t040.md`. Prerequisite с явным `SPECIFY_FEATURE_DIRECTORY=specs/292-sharing-krisp-parity` подтвердил нужный активный каталог. Исходники workflow/helper/validator/contract и журнал отказа прочитаны напрямую. Тесты не запускались, продуктовый интерфейс и установленное приложение в этом узком обзоре не проверялись. Неподтверждённых пунктов требований нет.

## Снимок проверенных требований

SHA-256 на момент обзора; последующие содержательные правки требуют повторного обзора затронутых пунктов:

| Файл | SHA-256 |
| --- | --- |
| spec.md | aa2053ed1255af0a15368164fda09bdd92609ff6ff63fd2f752bb36dee03801c |
| plan.md | b2baa5e032779f1e9ba2ef13572795b96ab63a44e20f6fdfa797af21c8975004 |
| tasks.md | 210cca359a84ce1d4266e32356c758a4681ed3ef1dfceec4238cffcda80c663e |
| quickstart.md | 92add4714f1cc125985a1b864bb56884dd11ffc86ecd0747db6ff137b96d8204 |

Изменены только reviewer-owned checklist и этот отчёт. Чеклист после изменения перечитан: **3 checked / 0 unchecked**.
