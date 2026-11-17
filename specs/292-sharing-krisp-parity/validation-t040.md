# T040 — исправление среды APT

Срез Active Spec Kit инфраструктурной предпосылки F292, FR-027/T016/T017.
База: e7723baf8a6890fff54956007baa0b29b3047892.

## RED → GREEN

Перед изменением workflow новый `test_apt_jobs_use_supported_ubuntu` упал на
`governance-fast: ubuntu-latest`, как ожидалось: 1 failed, 128 deselected.
Первый запуск из корня без PYTHONPATH остановился на импорте приложения до
исполнения тестов; рабочая команда исправлена в quickstart, этот отказ не
используется как RED.

После изменения трёх runs-on и потребителя release validator:

- `(cd apps/server && PYTHONPATH=src uv run --extra dev pytest tests/contract/test_ci_cd_contract.py -k 'apt_jobs or github_full_workflow or release_full_splits_postgres_work or release_full_artifacts_and_aggregate or release_full_python_heredocs_compile_after_yaml_stripping or release_full_worker_count' -q)` — PASS, 7 passed / 122 deselected.
- `python3 scripts/validate-full-ci-workflow.py --self-test` — PASS; отрицательные мутации по отдельности возвращают server-phases и server-parallel на latest и отклоняются по имени своего задания.
- `python3 scripts/validate-full-ci-workflow.py` — PASS на фактическом workflow.
- Ruff затронутых Python, `validate-changelog-fragments.py` и `git diff --check` — PASS.
- Дополнительный локальный `python3 scripts/check_spec_kit_governance.py` — не PASS: глобальный `specify` на Mac обновляется другим процессом и не совпадает с закреплённой версией v1.0.7/ref fe1d00e3ccaf495880aaf90fb0e17679e82f065b. Глобальное окружение не изменялось; обязательный GitHub governance-fast устанавливает закреплённую версию и проверяется отдельно.

## Сходимость

Новых обязательных задач реализации не обнаружено. Набор caller jobs ровно3;
исходный APT helper/guard, остальные runners, команды, permissions, timeouts,
exact-SHA, однократное резервирование и восемь частей полного прогона не меняются.
Reviewer-owned checklist требований: 3 checked / 0 unchecked; независимый обзор
реализации и GitHub checks точного SHA/base фиксируются отдельно.

T040 и issue #8119 остаются открытыми до подтверждения обязательных ворот.
Merge, release-full, релиз/выкатка, установленное приложение и стенд здесь не
изменяются и не объявляются проверенными. Финальную публикацию ведёт основной
оператор задачи.
