# F211/A14: независимая проверка требований

Дата: 2026-10-31. Отдельный reviewer проверяет качество требований до реализации.

**Итог: PASS, 5 отмечено / 0 не отмечено.**
Предварительная промежуточная запись этого отчёта заменена завершённой
проверкой после полного чтения активных документов и уточнения FR060.
Этот результат не подтверждает реализацию, исполнение CI, merge или закрытие
#7834. Незавершённые критерии других срезов F211 остаются открытыми.

## Область и идентичность

- Ветка: `codex/211-macos-runner-migration`.
- Исходный HEAD: `686e4bb59aae093c03839c80438e93076f9f824d`.
- `.specify/feature.json`: F211, T105/T106, `active-spec-kit`.
- `check-prerequisites.sh --json --paths-only` подтверждает F211 и те же пути.
- Объём: FR038/059/060/SC026, A14 plan/tasks/quickstart и их ограничения CI.
- Разрешённые изменения reviewer: `checklists/runner-image.md` и этот отчёт.
  Прочие изменения принадлежат основному агенту и сохранены.
- Риск: существующий срез Spec Kit, инфраструктура CI. Продукт, GRAF Dev,
  выпуск, публичные пакеты, production и предметная установленная приёмка
  не входят. При чтении не обнаружена новая предметная зависимость,
  требующая проверки PRD или текущего продуктового статуса в этом срезе.

## Прочитанные документы

Полностью прочитаны собственным формальным проходом: root AGENTS, guidance
README, document-reading, codex-worktrees, development-process, spec-kit-flow,
release-and-validation, tracker-policy, github-issue-canon, конституция,
F211 spec/plan/tasks/quickstart/research/data-model и contracts/ci-cd-cli.
Длинные файлы прочитаны частями; усечённые участки spec и quickstart затем
прочитаны отдельно. Чтение не заменялось пересказом другого агента.

Частично, по применимым целым разделам, прочитаны: release-full trigger,
permissions, concurrency, reserve, macos-full и aggregate; существующий
actual-native-selector тест с параметрами; относящиеся к runner/cache
контракты и Full validator. Полностью прочитаны macos-pr, macos-diagnostic
и run-swift-tests.sh. Исторические доказательства не выдаются за новую приёмку.

## Независимо проверенные внешние источники

1. [GitHub runner-images #13518](https://github.com/actions/runner-images/issues/13518):
   API updated_at `2026-10-30T17:43:05Z`; macOS14/arm64 снимаются с поддержки
   02.11.2026. Окно отказов 31.10 14:00 UTC — 01.11 00:00 UTC подтверждено.
   macos15 указан допустимым переходом; latest не требуется.
2. [Закреплённый состав macos15 arm64](https://github.com/actions/runner-images/blob/4da2307112a0fad2fd2ecaca8ba7d08683b8c581/images/macos/macos-15-arm64-Readme.md):
   строки8/10 — macOS15.8.2, image20261028.0489.1;
   161 — default Xcode16.4; 163 — Xcode16.2 по ожидаемому пути;
   172 — SDK15.2 для Xcode16.2. Поэтому одного прежнего выбора compiler
   через PATH недостаточно: среда должна быть закреплена на уровне задания.
3. [Официальные GitHub runners](https://docs.github.com/en/actions/reference/runners/github-hosted-runners#supported-runners-and-hardware-resources):
   таблица связывает обычный label macos-15 с arm64/M1; Intel имеет отдельный
   macos-15-intel. Требование arm64 не основано на случайном имени образа.
4. `man xcode-select`, ENVIRONMENT: DEVELOPER_DIR переопределяет активную
   developer directory для процесса вместо системной. Системный switch
   меняет всех пользователей и не нужен для job-level выбора.
5. [Apple Xcode support](https://developer.apple.com/support/xcode/):
   Xcode16.2 поддерживает macOS15.x и SDK15.2. Таблица указывает Swift6.0
   без patch-версии; README также не доказывает patch-версию compiler.
   Точный Swift6.0.3 сохраняется существующим контрактом и должен быть
   проверен у обоих реальных исполняемых файлов по FR059/SC026, а не
   выведен из имени Xcode. Наличие официального
   [Swift6.0.3 release](https://github.com/swiftlang/swift/releases/tag/swift-6.0.3-RELEASE)
   не выдаётся за проверку установленного compiler.
6. Аннотация [native job124569540899](https://github.com/yshishenya/graf/actions/runs/41212247209/job/124569540899)
   повторно получена через GitHub API: отказ прямо связан с scheduled
   macOS14 brownout и retirement02.11. Это инфраструктурный отказ,
   а не доказательство дефекта приложения или успешных тестов.

## Проверка каждого пункта

| Пункт | Связь и конкретное основание | Итог качества требований |
| --- | --- | --- |
| CHK001 | FR059 и ввод A14 называют macos-15, Apple Silicon, Xcode16.2, SDK15.2 и сохраняемый Swift6.0.3; закреплённый README подтверждает наличие Xcode/SDK, официальная таблица — архитектуру. Требуется фактическая проверка compiler; latest и установка нового Xcode запрещены. | PASS |
| CHK002 | FR059 задаёт единый job-level DEVELOPER_DIR, arm64, actual developer path и принадлежность/версию SDK до изменения PATH, оба compiler, отказ при ошибке/отсутствии/смене. Plan A14.2 требует сохранить прежние отрицательные проверки и запрещает sudo, системный switch, загрузку или новый helper. SC026 требует исполнения actual YAML shell. | PASS |
| CHK003 | Уточнённый FR060 отдельно определяет primary key с хешами lock/source и restore prefix без них, но с macos15/архитектурой/Swift/Xcode; значения одинаковы между двумя workflow. Другая ОС исключена. FR038/SC026 сохраняют реальные build/tests/ContractValidation независимо от cache hit/miss. | PASS |
| CHK004 | FR038 сохраняет exact head/base, консервативный scope, required+skipped failure и запрет считать кэш исполнением. FR059 и plan A14.3 сохраняют required names/права/receipts/concurrency. Прежние FR039–041 и A6 ограничения source proof не переписаны; SC026 требует общий validator и все три checks. Будущий frozen candidate по-прежнему получает один authoritative release-full. | PASS |
| CHK005 | T105 перечисляет три workflow, validator, оба существующих test modules, причинный red/green и независимое review/converge. T106 зависит от T105 и требует реальный native на новом точном SHA, общий validator до/после защищённого merge и live closeout. Quickstart называет actual shell тест, профильные контракты, Full self-test/actionlint и отчёт; выпуск/Dev/продукт/Windows/чужие задачи явно вне области. | PASS |

## Устранённое замечание R1

Первое FR060 можно было прочитать как требование хешей исходников в restore
prefix, что противоречило сохранению прежней схемы восстановления.
Reviewer сообщил это основному агенту, не исправляя spec самостоятельно.
Автор уточнил FR060: primary key содержит оба хеша; restore prefix их не
содержит и ограничен совместимой средой. Текущее предложение прочитано,
проверено вместе с A14 плана и существующими двумя cache блоками. R1 закрыто.

## Границы и следующие обязательные условия

- Это проверка качества требований. T105/T106 ещё `[ ]`, код не принимался.
- Реализация обязана покрыть неправильный/отсутствующий job-level выбор,
  неверную архитектуру, developer/SDK вне Xcode или неправильной версии,
  ошибки и дрейф среды, missing/wrong/error swift и swiftc. Прежние
  6.0.31 prefix, SDK error/drift и developer drift проверки сохраняются.
- Полный новый native PR job должен вызвать build, XCTest и
  ContractValidation. Один scope/result или старый source proof недостаточен.
- Новый SHA требует новых обязательных exact-SHA/base проверок. Изменения
  описания и принятие merge проверяются общим validate-pr-checks.py.
- Будущий выпуск сохраняет единственный frozen-source Full. Новый Full,
  установленная совместимость macOS14, упаковка/нотарификация и production
  в T105/T106 не доказываются и не выполняются.
- #7834 остаётся OPEN; его окончательная синхронизация и закрытие принадлежат
  основному агенту после всех ворот. Общие F211 и F269/T031 не закрываются.

Тесты, сборки, CI, приложение, выпуск и развёртывание reviewer не запускал.
GitHub использовался только для чтения issue и исходной аннотации; Git — для
чтения идентичности/diff/status. Изменены только два разрешённых файла.

## SHA-256 прочитанных документов и применимых источников

Хеши фиксируют текущие байты. Они не доказывают реализацию или исполнение CI.

```text
24c0767f2223bb21e969079ec1ec09e0dec7c3fd3d85d02e78832f17e0775958 AGENTS.md
2f3e0339a89d3ccdf0878026920955a189584d6a985116b069584cd78b3c75bb docs/agent-guidance/README.md
5263860b1974df022826ac81c2482e6ee92100bc0bb718ab5a29b32e2422e411 docs/agent-guidance/document-reading.md
afb816ce48624eb79fcd7fd44d09f0986296e87ef1cfecd790228ac70a5b9b9e docs/agent-guidance/spec-kit-flow.md
ff0d996c95101d5f782259661131db1b7528b3bf58991603f5652092e1e5256f docs/agent-guidance/release-and-validation.md
41fa13de8addaec6cc7c13c8be9da53c2c5527a302247d85b738f20c3155e864 docs/agent-guidance/development-process.md
d7d8c9cce8315c17efaa1da05ece80c2542ca01b966f81fb848580104b785e1d docs/agent-guidance/codex-worktrees.md
9793de5e158283c2d37bdd2b47f0daf4d312a44fd6ffa37cc22ac47f7a0c3472 docs/agent-guidance/tracker-policy.md
7cd5c1cde2bb51e3842cae9e3717b094fea9f6fbb33fb1a408e6d243f9d68bf3 docs/agent-guidance/github-issue-canon.md
7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8 .specify/memory/constitution.md
55042d93b9683327ad2ce94d61ed3149ea13c483787d5ebfa669d90b613a833c specs/211-optimize-ci-cd/spec.md
93e9a242498136516ed188a9e9c6ee3eeadbaf7e5da7cc1c3390624f2359d668 specs/211-optimize-ci-cd/plan.md
2043a9baa932bd70925afc265d56c77939077607ca3c5f2a67649eda11481527 specs/211-optimize-ci-cd/tasks.md
1af82b01675429c5c6e9ffbdd5f58443ece70ea97a6ce66ff73fe13ac15b5690 specs/211-optimize-ci-cd/quickstart.md
612fceb783e6787598a0885e8acb6a70c258a67fba744fa059aebdfc41ce5e9b specs/211-optimize-ci-cd/research.md
0b3b520031473bf768d46fcfa6d9f4cec0023d90376cad3f138cfe14f660f6d2 specs/211-optimize-ci-cd/contracts/ci-cd-cli.md
e7a761c895dd524ca5c2d12d76a65f41abceb5b97dcb081d2a0113418f9809ed specs/211-optimize-ci-cd/data-model.md
5aa2a59ec9d8e5036305e271818ebd0dbb70a587d2c56900f3b6060af228d942 .github/workflows/macos-pr.yml
b009aa5c49f53dd5ee9b200cb88eec68f243b0a974b3e2e7aff50e71b568aac0 .github/workflows/release-full.yml
03e36534be234812750a4b7a5e72cc8becb664a50335d1e9d265cce791f0ac80 .github/workflows/macos-diagnostic.yml
d81cb9e6874bafa2214a8d47059fc1386df4b1a819c168c12527473f111ce6a4 tests/governance/test_governance_workflow.py
bbda28fe4d607b29c9a524f5add32407605de346917705deeb14eb9300be90f5 scripts/validate-full-ci-workflow.py
710dab10f8b6fdb713c99c01ba3e9bf50ef3ca58f8b9591d5616b51a3ecffa23 apps/server/tests/contract/test_ci_cd_contract.py
4cb13374b8f2318b534a48499cb64ca20bdd51f065ae30a80cb6cda34f31ccca apps/macos/Scripts/run-swift-tests.sh
```
