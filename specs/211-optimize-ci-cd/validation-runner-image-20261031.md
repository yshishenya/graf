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


## T107: фактический отказ и уточнение объёма

Первый настоящий native run [41215353665](https://github.com/yshishenya/graf/actions/runs/41215353665)
на source `45f783a5a6789db03e3530194be92453c0a86974` подтвердил macos15 arm64,
Xcode16.2, Swift6.0.3 и SDK15.2, но завершился FAILURE при сборке.
Три protocol conformances WebKit не принимали callback types без
`@MainActor @Sendable`. Следовательно, прежние локальные 365 PASS сами
по себе не доказывали native готовность; этот failed run сохранён.

До исправления добавлены FR061/T107 и точная граница двух файлов; issue
#7834 обновлена без создания дубля. Независимая повторная проверка требований:
6/0 SCOPED PASS, `review-webkit-types-20261031.md`. Scoped analyze A14 после
этого дополнения: FR038/059/060 → T105, FR061 → T107, SC026 → T105/T107/T106;
5/5 требований покрыты, несвязанных задач 0, CRITICAL/HIGH/clarification gaps0.
T106 зависит от T105 и T107; публичная совместимость/доверие не меняются.
Анализ выполнен до source edit, режим analyze не менял файлы.

Исправление удаляет 17 строк двух старых условных ветвей, без добавления кода.
Существующие шесть MainActor/Sendable aliases и все тела/consumers сохранены.
Compilation проверяет conformance; дополнительная обвязка не требуется.
Deployment target macOS14 сохранён; сборка старым SDK14 не поддерживается.
Ручная/установленная приёмка macOS14 этим изменением не заявляется.

Локальная `swift build --package-path apps/macos --scratch-path /tmp/graf-f211-t107-swift`:
PASS,31.05s, Swift6.3.3/Xcode26.6/SDK26.5, arm64. Это другая среда;
точный Swift6.0.3/SDK15.2 должен пройти новый настоящий native run.
Существующие XCTest/ContractValidation и независимое implementation review
ещё выполняются; T107/T106 пока открыты. GRAF Dev не запускался.


### T107: завершённые местные проверки

Существующие команды `swift test ... list` и `swift test ... --skip-build`
с тем же временным scratch успешно завершены, `_SWIFTPM_SKIP_TESTS_LIST` снят.
XCTest: **1296 total = 1287 PASS + 9 SKIP,0 failures**,130.105s.
Семь skip сохраняют честный отказ среды подтвердить AppKit focus; два —
не запрошенные экспорты synthetic previews. Они не относятся к типам WebKit
и не объявлены установленной приёмкой. Все тесты/ожидания сохранены.
`swift run ... --skip-build ContractValidation`: **PASS**,exit0.
Native приложение не запускалось; сборка executable не является запуском.

Журналы и SHA256:
- build: `af892cf6faf379fcc8d8deccb9fcfc0a4b3d0caeeef455fd0414ca1f0f98458b`;
- discovery: `20ec30e4c6e40db1ff74ca2412574cb250bc2245ce03648beb999ff3e8d1cfa4`;
- XCTest: `820e2540674757a4f43c0d2ceba0c869faa1d2578030bc23c4d59701742c7175`;
- ContractValidation: `17189bd7192c0e37e850670a49ed6602566a183b4d772c368024c2674e389c87`.

Process/governance/changelog/diff PASS. Scoped convergence после T107:
5 требований A14,6 типов/14 declaration consumers и3 решения плана сверены;
missing/partial/contradicts/unrequested0. Новых задач не добавлено:
настоящее pinned native и exact-SHA/base/merge уже принадлежат T106.
Общая программа F211 вне этой приёмки. Before/after hosted proof не смешивается.


Независимый reviewer перечитал завершённые XCTest/ContractValidation logs,
подтвердил итог, причины9 SKIP и неизменные source hashes; окончательный
`review-webkit-implementation-20261031.md`: SCOPED PASS, P1/P2/HIGH/CRITICAL0.
T107 отмечена после этой проверки; T106 до нового hosted proof/merge открыта.
