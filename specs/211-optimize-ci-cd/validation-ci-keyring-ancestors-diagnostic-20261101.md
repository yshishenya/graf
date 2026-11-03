# F211/T114 — независимое ревью конечной диагностики предков

Дата: 01.11.2026. Проверяющий: `/root/public_counter_readiness_review`.
Область: только уточнение сообщения существующего отказа unsafe keyring
ancestor, продолжение диагностики T113/T114 до изменения кода.

**Requirements PASS; P1/P2/HIGH — 0/0/0.**
Прочитаны полностью последние sections spec/plan «конечная диагностика
предков», применимые T114 guards и текущая точка отказа helper.

## Основания

- Native факт source `c8275c5d2f3db7e6f5a22327979b01db8cd82cc7`,
  run41258326161, отделён от неизвестных metadata предков и key pin.
  Отказ происходит до key/source write. Причина прав не угадывается.
- Только при существующем unsafe-ancestor условии допускаются lstat трёх
  фиксированных публичных каталогов `/usr/share`, `/usr`, `/` и вывод
  фиксированных labels share/usr/root плюс numeric type/uid/gid/mode/size.
  `/` служит только конечной точкой диагностического набора; он не становится
  новым разрешением ремонта. Новых пользовательских путей, обхода каталогов,
  чтения содержимого, env/listing или сетевых действий нет. Объём ограничен
  тремя stat-записями, значения size — metadata, не содержимое.
- Прежние condition/ненулевой отказ и порядок выполнения сохраняются.
  Диагностика не допускает unsafe ancestor, не исправляет его, не снимает
  pin и не добавляет пишущих операций. После отказа APT/npm/Playwright не
  запускаются. Безопасная ветвь и прежняя atomic directory/key логика не
  получают нового функционального допуска.
- Существующие отрицательные ancestor fixtures требуют exact numeric stderr
  для всех трёх категорий. Это проверяет и фиксированный формат, и отсутствие
  лишнего вывода; прежние side-effect assertions остаются. Нового тестового
  framework, workflow, службы или хранилища не требуется.
- Сохраняются independent before/after review и focused/static проверки,
  затем ровно один штатный native Prepare на том же draft. Full не служит
  диагностикой. Только после конечного набора фактов допускается отдельный
  проект/review функциональной адаптации. Промежуточный отказ не получает
  merge/PASS выпуска, F273/T0 либо коммерческих критериев.

Новое содержание не меняет constitution III/VI или доверие APT. По разрешению
повторного чтения F211 проверены совпадающие хеши ранее полностью прочитанных
constitution/product-gates/Spec Kit flow/release guidance. Текущие helper и
тест имеют прежние reviewed hashes: diagnostic code ещё не написан.
Существующий checklist `ci-keyring-directory.md` перечитан: **5 отмечены /
0 открыты**, без изменения отметок. Это исторический requirements gate
функционального directory среза; новую диагностику принимает данный отчёт,
а не задним числом расширенные отметки того checklist.

## Границы проверки

Создан только этот назначенный отчёт. Код, requirements/checklist, Git/GitHub,
сервер, release/deploy и чужие изменения не менялись. Тесты, native CI,
сеть/APT/root операции не запускались. Native факт прочитан из требований
исполнителя, независимо не воспроизводился. Implementation PASS ещё нет.
Текущий pin runner, безопасный hosted Prepare, exact PR gates/merge, Full,
выпуск/runtime, F273/T0 и трафик/продажи этим заключением не приняты.

## Хеши состояния до кода

- `specs/211-optimize-ci-cd/spec.md`: `4168782e630db1350f3a6ce308135aa4ab406f7b0a30c8280a27ed763840cd33`.
- `specs/211-optimize-ci-cd/plan.md`: `d7f500b30999a68223f2e0a7e2d9e1a9f925f1fd0eb5f46622b6ecb53b022264`.
- `specs/211-optimize-ci-cd/checklists/ci-keyring-directory.md`: `bc5fd935caaf17cecbd6f369d0bc4db3775de79168cf2f32f6a4c378a7766c8b`.
- `infra/scripts/prepare-ci-apt.sh`: `879306f087c4809fea3a3c26d004f78914e5541ac8490d9e3334058020e48023`.
- `tests/governance/test_governance_workflow.py`: `4ffb95eb130da7a60e46cd6af0cd005d6ad310f415ad7e3c9dc404e033a9fcbd`.
- `.specify/memory/constitution.md`: `7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8`.
- `docs/agent-guidance/product-gates.md`: `9f7072c879490d250053cb7397ad6b9b68fdcde17bdf9367ed874a41e450b5f5`.
- `docs/agent-guidance/spec-kit-flow.md`: `afb816ce48624eb79fcd7fd44d09f0986296e87ef1cfecd790228ac70a5b9b9e`.
- `docs/agent-guidance/release-and-validation.md`: `ff0d996c95101d5f782259661131db1b7528b3bf58991603f5652092e1e5256f`.

## Независимое ревью реализации диагностики

Повторно прочитаны требования и фактическая новая ветвь helper, точные stderr
assertions и сохранённые общие side-effect assertions существующей матрицы.
**Scoped source PASS; P1/P2/HIGH — 0/0/0.** Требующих исправления дефектов
в проверенном изменении не найдено.

В существующем unsafe-ancestor условии изменено только сообщение отказа.
При его срабатывании цикл имеет ровно три фиксированные пары label/path:
share→`keyring.parent.parent`, usr→`keyring.parent.parent.parent`, root→`/`.
При фиксированном production keyring это ровно `/usr/share`, `/usr`, `/`.
В цикл не поступают env, URI, пользовательские пути либо содержимое файлов;
используется только lstat без listing/read/open. Формат включает только
фиксированные слова и числовые stat type/uid/gid/mode/size. Строки не могут
включить имена, содержимое либо произвольные входные значения. Диагностика
не добавлена в успешную ветвь.

Исходный condition unsafe directory/uid/write bits не менялся. Сразу после
трёх summaries вызывается тот же fail/SystemExit. Нет допуска к key pin,
source normalization, chmod, replace или последующим APT/npm/Playwright.
Изменение не расширяет repair_parent либо доверие к небезопасным предкам.
Новых dependencies, конфигурации или workflow нет; простой локальный цикл
достаточен, абстракций и кода для удаления не обнаружено.

Четыре прежних отрицательных состояния owner/mode/symlink share и mode usr
× три настоящих caller проверяют exact stderr, включая все три metadata
записи и порядок labels. Fixture явно подставляет только root metadata и
опасное условие; ожидаемые числа сверяются с файловой моделью. Прежние
assertions сохраняют отсутствие следующих действий, key/source bytes,
inode/modes, directory mode, сторонних файлов и temp. Реальные hosted
metadata этим не доказываются.

Тесты проверяющий не запускал. Прочитаны законченные журналы исполнителя:

- `ancestors-red.log`: **12 failed /495 deselected /4.37s** на прежнем
  коротком сообщении.
- `ancestors-green.log`: **66 passed /441 deselected /23.15s** — текущая
  directory+ancestor матрица.
- `ancestors-static.log`: **8 команд EXIT0** — Bash syntax, Ruff helper/test,
  actionlint, development-process, workflow self-test, Spec Kit governance,
  changelog fragments и diff check.

Полный модуль после этого текстового изменения повторно не запускался.
Предыдущие whole504 и дополнительный focused3 сохраняют собственные старые
хеши и не выдаются здесь за whole на текущем helper/test. Это допустимый
предел данного узкого source/message review; native диагностический Prepare
на момент заключения ещё не выполнялся. Один такой запуск и следующие
exact-SHA gates остаются отдельными. Успех source review не означает
безопасные предки или фактическое совпадение key pin на runner.

Изменён только назначенный отчёт; код, тесты, требования, checklist,
Git/GitHub/серверы/выпуск не менялись, чужие изменения сохранены. Сеть,
тесты, APT/root/native проверки не запускались. Функциональная адаптация
предков требует нового проекта/review после фактов. Merge, Full, выпуск,
F273/T0 и коммерческие критерии не приняты.

### Хеши после реализации

- `infra/scripts/prepare-ci-apt.sh`: `9330c5a53fd1025db74aa014e5371607ec40a7fa681aa4156ed24ee06ec04b0d`.
- `tests/governance/test_governance_workflow.py`: `eab71f505076ada14ec0a9d8a9facac72b5e1e25b8dc7d247d635716c399d96f`.
- `.dev/ci-official-sources/ancestors-red.log`: `de7e687675f8614cb1501f78b68a6980b30e39a1c1b6e7071f111996a7cc5279`.
- `.dev/ci-official-sources/ancestors-green.log`: `12edfa0ee9498e62f57bb7f3d568b437db48408f28f858ec53cd9bbe6af3a9d0`.
- `.dev/ci-official-sources/ancestors-static.log`: `75b742563f8be7e5189a16cbd460f62d22201b518c0101f00dd9e165d89440b8`.
