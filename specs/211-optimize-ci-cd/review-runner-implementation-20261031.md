# F211/A14: независимое ревью реализации T105

Дата: 2026-10-31. **Итог: SCOPED PASS.** Замечаний, требующих исправления
реализации, не обнаружено. Критических/высоких замечаний и P1/P2: 0.

## Назначение и область

Ревью выполнено отдельным проверяющим после реализации, в рабочей копии
`/Users/yshishenya/.codex/worktrees/f265-final-closeout/crisp`, ветка
`codex/211-macos-runner-migration`, исходный HEAD
`686e4bb59aae093c03839c80438e93076f9f824d` плюс текущие незакоммиченные файлы.

Применён навык `code-reviewer`. Объём: фактический diff трёх workflow,
Full validator и двух изменённых модулей проверок. Основание — FR038/059/060,
SC026, A14 плана, T105/T106 и конституция V/VI. Полоса — существующий
срез Spec Kit, инфраструктура CI. Обязательные документы полностью прочитаны
при независимом ревью требований в этом же диалоге; перед повторным
использованием их хеши сверены и совпали. Новых предметных зависимостей от
продуктовой приёмки в этом diff нет.

Разрешённая запись этого назначения — только данный отчёт. Checklist
требований не менялся: его текущий SHA-256 сохранён ниже. Код, spec/plan/tasks,
Git/GitHub, приложение, выпуск и production проверяющий не менял.

## Выводы по коду и требованиям

| Требование | Проверка фактического diff | Вывод |
| --- | --- | --- |
| FR038 | Меняется только среда native job. Сохраняются точный checkout/requested SHA, scope native_required/text_only, required result macos-pr, обработка required+skipped и text source proof. Build, run-swift-tests.sh и ContractValidation вызываются прежними командами. | Соответствует |
| FR059: образ и выбор Xcode | Все три существующих macOS задания переходят на macos-15 и имеют job-level DEVELOPER_DIR Xcode16.2. Переменная действует и на следующие build/test шаги. Нет системного switch, sudo, загрузки compiler, нового helper или latest fallback. | Соответствует |
| FR059: реальные условия среды | До изменения PATH проверяются заданный DEVELOPER_DIR, успешный uname/arm64, actual developer, непустой SDK внутри выбранного Xcode, SDK15.2 и оба исполняемых swift/swiftc с точной версией 6.0.3. Ошибки команд останавливают shell через set-euo pipefail. После изменения PATH проверяются разрешившиеся пути compiler и неизменность developer/SDK/path/version. GITHUB_PATH дописывается последним. | Соответствует |
| FR060 | В обоих caches одинаковый основной ключ с macos15, runner.os/arch, Swift6.0.3, Xcode16.2 и хешами lock/source. Одинаковый restore prefix содержит ту же совместимую среду, без хешей. Старый префикс удалён. Условия build/test не зависят от cache hit; только прежний refresh timestamps условен. | Соответствует |
| SC026: причинные проверки | Actual-YAML shell проверяется на трёх workflow. Все прежние 11 сценариев сохранены, добавлены 12 на каждый workflow: всего 69. Отдельный параметризованный тест проверяет job image/env. Full self-test дополнен отказом на macos14. Cache/diagnostic контракты согласованы с новой средой без удаления остальных assertions. | Локальная часть соответствует |
| SC026: внешняя приёмка | Реального native job macos15 и нового набора трёх exact-SHA/base checks ещё нет; T106 остаётся отдельным обязательным состоянием. | Ожидается |

### Проверка отрицательных сценариев

Сохранены valid, missing/wrong/error swift/swiftc, версия 6.0.31 вместо 6.0.3,
ошибка SDK, смена SDK и developer. Добавлены wrong-arch/arch-error,
missing-env/wrong-env, wrong-developer/developer-error/empty-developer,
empty-sdk/sdk-outside, sdk-version/sdk-version-error/sdk-version-drift.
Каждый отрицательный сценарий требует ненулевой exit и неизменного GITHUB_PATH.

Fixtures заменяют только платформенные пути и ответы команд; исполняется
настоящий run-блок YAML. Отдельная проверка job-level env не позволяет принять
наличие переменной только в тестовой обвязке за корректность самого workflow.
Версия SDK моделируется отдельной ветвью xcrun, поэтому path drift и version
случаи не подменяют друг друга. Прежние отрицательные expectations сохранены.

### Защита доказательств и минимальность

Прочитан весь diff шести файлов и актуальные изменённые блоки. Permissions,
concurrency, required names, checkout/source identity, scope/result,
text-only proof, reservation/aggregate и формат receipts не меняются.
Diagnostic остаётся неавторитетным и не получает release evidence.
Будущий release candidate сохраняет единственный authoritative Full.
Продуктовые файлы и run-swift-tests.sh не изменены; скрытый skip не добавлен.

Решение использует три прежних коротких selector, текущий cache и существующие
тестовые модули. Новые зависимости, настройка доверия, служба, схема доказательств
или дополнительная архитектура не появились.

## Проверенные результаты

Тесты и статические команды запущены основным исполнителем. Reviewer их
не повторял; самостоятельно прочитал завершённые журналы и сверил текущее
содержимое файлов. Точная команда GREEN передана исполнителем:

```sh
/Users/yshishenya/Documents/crisp/apps/server/.venv/bin/python -m pytest -q tests/governance/test_governance_workflow.py apps/server/tests/contract/test_ci_cd_contract.py
```

- RED actual-shell: 27 FAILED/42 PASSED/165 deselected,86.23s. Итоговая строка
  и перечень 27 отказов прочитаны в исходном журнале. Отдельные RED для двух
  cache/diagnostic contracts и трёх job pins сообщены исполнителем; отдельных
  журналов этих двух проверок reviewer не получал и не выдаёт их за собственное
  исполнение.
- GREEN: 365 PASSED/0 failed/0 skipped,129.76s; журнал достиг 100% и содержит
  терминальный итог. Один PytestAssertRewriteWarning относится к заранее
  импортированному fixture-модулю; он не скрывает skip или отказ.
- Статический журнал: Full validator/self-test OK, Ruff All checks passed,
  development-process OK, pinned Spec Kit governance OK, changelog-fragments OK.
  Actionlint и git diff --check не выводят текст при успехе; их PASS и точные
  команды подтверждены исполнителем. Reviewer отдельно выполнил только
  read-only git diff --check: exit 0.

Команды статического этапа исполнителя:

```sh
python3 scripts/validate-full-ci-workflow.py --self-test
python3 scripts/validate-full-ci-workflow.py
/opt/homebrew/bin/actionlint .github/workflows/macos-pr.yml .github/workflows/release-full.yml .github/workflows/macos-diagnostic.yml
/Users/yshishenya/Documents/crisp/apps/server/.venv/bin/ruff check tests/governance/test_governance_workflow.py apps/server/tests/contract/test_ci_cd_contract.py scripts/validate-full-ci-workflow.py
python3 scripts/check-development-process.py
python3 scripts/check_spec_kit_governance.py
python3 scripts/validate-changelog-fragments.py
git diff --check
```

## Пределы PASS и следующий шаг

Этот PASS относится к проверенным локальным байтам T105 и прочитанным
результатам. Он не является разрешением обойти T106: основной агент должен
получить реальное исполнение build/XCTest/ContractValidation на macos15,
три обязательных проверки точных SHA/основы, общий validator до/после
защищённого merge и содержательный live closeout #7834. Изменение кода после
этих хешей требует повторной оценки затронутой части и соответствующих проверок.

Новый release-full, выпуск, GRAF Dev, установленная совместимость macOS14,
публичная подпись/нотаризация, production и Windows не выполнялись и не
принимались этим ревью. Непроверенные критерии других задач F211/F269/T031
не закрываются. Новых обязательных задач из diff reviewer не выявил.

## SHA-256 проверенных файлов

```text
5252524953d383e205cf83ead3cd29e9074a1779fcea60eda1dc8bfd30094bcc .github/workflows/macos-pr.yml
e3342f96e9afd335892f5d850a7e03c2cee2264a4c20a9738ac5e5977472bb5a .github/workflows/release-full.yml
431a349664b63991c7723dff203bd2082b383e8dde526fc832ec7fb1482347ef .github/workflows/macos-diagnostic.yml
a0b68a8d991769f3b0edcfffb76854933c46e850b588daf09f02d1d18b712463 scripts/validate-full-ci-workflow.py
a329528d13653925ff924a3fdcca9ed453d1d15dc77dab799fe17dba92b3d214 tests/governance/test_governance_workflow.py
450447928f0baf4f7485263e6046c26189bcaab04bff420935c3b522011086cb apps/server/tests/contract/test_ci_cd_contract.py
55042d93b9683327ad2ce94d61ed3149ea13c483787d5ebfa669d90b613a833c specs/211-optimize-ci-cd/spec.md
93e9a242498136516ed188a9e9c6ee3eeadbaf7e5da7cc1c3390624f2359d668 specs/211-optimize-ci-cd/plan.md
2043a9baa932bd70925afc265d56c77939077607ca3c5f2a67649eda11481527 specs/211-optimize-ci-cd/tasks.md
1af82b01675429c5c6e9ffbdd5f58443ece70ea97a6ce66ff73fe13ac15b5690 specs/211-optimize-ci-cd/quickstart.md
3e716d94003b09488bc33861c99038e2415bf10e3da71aec92490f5bd7cda2a3 specs/211-optimize-ci-cd/checklists/runner-image.md
87afac265341f52c2914b6cbf62fc4b97d8676aed2d252b24ed583069da89f56 specs/211-optimize-ci-cd/review-runner-image-20261031.md
068353774999fa87818b1dfac7b5ff844f9b162c24afe6712a02798e1264ee36 specs/211-optimize-ci-cd/validation-runner-image-20261031.md
```

## SHA-256 завершённых журналов

```text
b0f5fafe7eaaa52c2bf59aadb3773e5b1408fcb846a50af9c74c3ba9b1dcc312 /tmp/f211-runner-red-20261031.log
8a8867f08d5bcc4aae91be63cfb231711bfa2a0a7d614f6d0f389ffcc0ea918f /tmp/f211-runner-green-20261031.log
859747f9c0b5280d52e3960849bbd4661f6bb189e8c64b08dfe2ba3d92766d0f /tmp/f211-runner-static-20261031.log
```
