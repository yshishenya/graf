# F211/A14: поддерживаемый исполнитель macOS

Дата: 2026-10-31. Ветка: `codex/211-macos-runner-migration`.
Исходная основа: `686e4bb59aae093c03839c80438e93076f9f824d`.
Область: #7834, T105/T106, FR038/059/060, SC026.
Полоса: существующий срез Spec Kit, инфраструктура CI.

## Проверка требований и анализ до реализации

Независимый reviewer: `checklists/runner-image.md`, 5/0 PASS.
Уточнение FR060 отделило primary key с хешами от restore prefix без них.
Ограниченный analyze A14: CRITICAL 0, HIGH 0; нет блокирующей неоднозначности.
FR038/059/060 покрываются T105, SC026 — T105/T106. Все четыре требования
имеют задачи; T106 зависит от T105. Конституция V/VI: публичная подпись,
доверие и обязательные проверки сохраняются. Другие задачи F211 не принимаются.
Существующая issue #7834 сверена по содержимому, task links и feature:211;
добавлены type:hardening и gate:pr-blocker, дубликат не создан.

## Причинная проверка

Исполнен настоящий shell selector каждого из трёх YAML; подменены только
платформенные пути/ответы, приложение и системный Xcode не менялись.
До исправления: **27 FAILED / 42 PASSED** из 69 сценариев
(`/tmp/f211-runner-red-20261031.log`). Новые отказы обнаружили пропущенные
проверки архитектуры, job env, developer path, принадлежности/версии SDK и её
смены. Старые отрицательные сценарии сохранены.
Дополнительно до исправления: три проверки образа/среды и два контракта
cache/diagnostic завершились ожидаемым FAIL на macos14/старом namespace.

## Реализация

Три задания используют macos15 и job-level DEVELOPER_DIR Xcode16.2.
Selector сохраняет оба executable/version/error checks Swift6.0.3, проверяет
arm64, developer, SDK15.2 внутри выбранного Xcode и неизменность среды.
GITHUB_PATH дописывается только после полного успеха. Оба Swift cache keys
и restore prefix согласованы и содержат macos15. Новый helper/зависимость,
sudo или системное переключение Xcode не вводились.

## Локальные результаты

- `/Users/yshishenya/Documents/crisp/apps/server/.venv/bin/python -m pytest -q tests/governance/test_governance_workflow.py apps/server/tests/contract/test_ci_cd_contract.py`:
  **365 PASS**, 129.76s; один PytestAssertRewriteWarning о заранее загруженном
  модуле fixture, отказов/пропусков нет. Включены 69 actual-shell сценариев
  и 3 проверки job image/env.
- `python3 scripts/validate-full-ci-workflow.py --self-test`: PASS, включая
  отклонение прежнего macos14; валидатор текущего workflow: PASS.
- `actionlint` трёх изменённых workflows: PASS.
- Ruff трёх изменённых Python-файлов: PASS.
- `check-development-process.py`, `check_spec_kit_governance.py`,
  `validate-changelog-fragments.py`, `git diff --check`: PASS.

## Независимое ревью, сходимость и внешняя приёмка

Независимое ревью реализации: SCOPED PASS, P1/P2 и CRITICAL/HIGH0;
`review-runner-implementation-20261031.md`. Scoped convergence A14: текущие
source соответствуют FR038/059/060; новые обязательные задачи не обнаружены.
T105 принята локально, T106 остаётся открытой до настоящего native
GitHub job, всех трёх exact head/base checks, защищённого merge и live closeout.
Локальные подмены среды не доказывают настоящий compiler GitHub.

## Границы

Продукт, GRAF Dev, установленная совместимость macOS14, Windows/F200,
публичная подпись/нотаризация, production и выпуск не проверялись/не менялись.
Новый release-full не запускался: будущий замороженный кандидат требует его
обычным единственным authoritative прогоном. F269/T031 и остальные открытые
задачи F211 не закрываются этим переходом. Legacy Impact: remove — активный
macos14 runner и совместимый с ним cache namespace заменены; fallback нет.
