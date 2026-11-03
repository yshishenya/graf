# F211 T113 — независимое ревью требований до кода, 01.11.2026

Проверяющий: `/root/public_counter_readiness_review`.
Ветка и активный указатель проверены непосредственно:
`codex/f211-ci-native-metadata-20261101`, F211/T112–T113, active-spec-kit,
HEAD `208e0aee20629c0770ad6ce0457fc1ebfcb6a631`.

**PASS качества требований T113. Checklist перечитан: 5 checked / 0 unchecked.
Блокирующих замечаний нет; P1/P2/HIGH — 0/0/0.** Это gate проекта перед
кодом, не review реализации или её фактической работоспособности.

## Доказательства по пунктам

1. Исходный отказ в spec T113 привязан к PR7861, source
   `838aa9e93310d341885b1a7a1d0b4011f3ed45ec`, run41254530857 и точному
   сообщению `unsafe source or keyring metadata`. Там прямо сохранены
   неизвестность файла/условия и закрытый без merge PR7862. T112 в текущем
   tasks `[ ]`, T113 `[ ]`; #7859 не считается закрытой. Внешнее состояние
   PR/run проверяющий здесь повторно не запрашивал: конкретные факты переданы
   владельцем и записаны в spec. Этот пункт принимает полноту и честность
   основания проекта, не подтверждает неизвестные native metadata.
2. Spec/plan ограничивают новое сообщение fixed category source/keyring и
   числами type/uid/gid/mode/size. Plan задаёт stat.S_IFMT/stat.S_IMODE,
   исключает чтение содержимого при неудачной metadata-проверке и сохраняет
   весь прежний guard. Paths/URI/env/другие файлы не входят в новое сообщение.
   При отказе отсутствуют запись APT и последующие APT/npm/Playwright.
   Перечитанный helper подтверждает, что известное сообщение относится к
   проверке lstat type/uid/mode/size до открытия source/keyring; причина
   одного из условий не угадана. Нет разрешения менять тип/владельца/права
   или расширять принимаемые значения по предположению.
3. Единственное расширение selector — точное имя
   `infra/scripts/prepare-ci-apt.sh` рядом с прежним server условием.
   Проверен существующий YAML блок: цикл changed_files, server branch,
   прежний helper до media/npm/Playwright и break. Новое условие не требует
   нового workflow/прав/runner sampling или искусственного server файла;
   обычные docs и прочая infra не выбираются новой ветвью. Остальные два
   caller остаются прежними. Изменение относится к существующему настоящему
   шагу и поэтому устраняет прежний пробел наблюдения helper-only PR.
4. Spec/plan/T113 tasks и новый quickstart согласованно требуют сначала RED
   новых metadata/selector assertions в существующем
   `tests/governance/test_governance_workflow.py`, затем весь трёх-caller
   профиль и статические/процессные проверки. Названы helper-only/server/docs,
   точные category/numeric values, отсутствие содержимого/URI/действий после
   отказа, независимые review/converge до draft PR. Native metadata получает
   именно настоящий Prepare в draft PR; локальная root модель остаётся
   моделью. Дополнительной инфраструктуры нет.
5. Spec/plan/tasks/quickstart запрещают merge промежуточного native failure,
   выдачу failure за PASS, Full ради диагностики и функциональную адаптацию
   до фактов и отдельного уточнения/независимого ревью. Конечные exact PR
   checks, Full, release/CD/runtime/T0/измерение не закрываются по этой
   диагностике. Прежняя локальная приёмка T112 не объявляется native успехом.

## Контекст, зависимости и порядок

Полностью перечитаны новые разделы T113 spec/plan/tasks/quickstart, checklist,
текущий helper и существующий governance-fast Prepare. Применимые T112
требования и границы native/model из прежнего полного чтения сохранены.
Документальные дополнения plan (явный Constitution III/VI до/после PASS),
tasks (точный путь теста) и новый quickstart поступили во время ревью и
прочитаны целиком до итоговых отметок.

По разрешённому владельцем повторному чтению F211 сверены хеши constitution,
PRD, merged status, product-gates и использованных guidance; они совпали с
ранее прочитанными. Конституционных противоречий не найдено: новое сообщение
не включает секретов/контента, checks/trust/signatures/права/production не
ослабляются, обязательный reviewer gate и дальнейший анализ сохранены.

Код/helper/test/YAML пока не менялись: локальный diff по ним пуст, helper и
test имеют прежние принятые хеши T112. Это подтверждает before-code положение,
а не работоспособность будущей реализации. После этого PASS обязательны
актуальные analyze и sync существующей #7859, затем RED и только разрешённые
изменения. Последующий функциональный выход из настоящего отказа — отдельное
решение после диагностических фактов и нового review.

## Действия и ограничения reviewer

Выполнены только чтение и локальные status/hash/diff проверки. Тесты, CI,
сеть, APT/sudo, серверы, Git/GitHub mutations, release/deploy не запускались.
Изменены только назначенные checklist и данный отчёт; чужие файлы сохранены.
После отметок checklist перечитан: **5/0**.

Это не приёмка новых чисел runner, реализации T113, устранения отказа,
hosted/native PASS, T112/#7859, exact PR gates/merge, Full или маркетинговых
целей. Известность общего сообщения не доказывает конкретный файл или
условие; это остаётся предметом разрешённого следующего наблюдения.

## Хеши принятого проекта

- Spec: `ca756eeda2f0ff8945e79c5e61ef3b98d4a7dd9fc228bff91ba7a603e9746e7c`.
- Plan: `95922e211a5fc827576cc9270a932ede73f53d0edd17583511c7710a97ee022f`.
- Tasks: `8e7745c1911379ea460ac222f5c21d83f0e1a62b74671dcbc964401cde65fc79`.
- Quickstart: `099663e0d3e8ff5ccb88039bf1b678edf9104d47b3fa07aa0c051c5a903f61f1`.
- Неизменный helper: `2364d3e6d5d66ef4b9081ae7d411380cdab37d09ca0dcaa1ca2f2670a7b9123f`.
- Неизменный test: `64223c8b65a55c227b6789dd7d2db1355e000da0718b974536120477e11d5f99`.
- Неизменный governance-fast YAML: `191f01fc6837a7486f3ed6220b5cd6cc7e2d5966932678f5208686a87d54f0b5`.
- Конституция: `7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8`.
- PRD: `0f3ccfcfa60062bb0aae6802eeb0012056a635a30cb9f46f54d1992d0b4f57c2`.
- Merged status: `25b7f383be47c7160da8e852006ff82019f30a5f9c371fc30baa79238649cd16`.
- Product gates: `9f7072c879490d250053cb7397ad6b9b68fdcde17bdf9367ed874a41e450b5f5`.
- Guidance index: `2f3e0339a89d3ccdf0878026920955a189584d6a985116b069584cd78b3c75bb`.
- Document-reading: `5263860b1974df022826ac81c2482e6ee92100bc0bb718ab5a29b32e2422e411`.
- Spec Kit flow: `afb816ce48624eb79fcd7fd44d09f0986296e87ef1cfecd790228ac70a5b9b9e`.
- Release guidance: `ff0d996c95101d5f782259661131db1b7528b3bf58991603f5652092e1e5256f`.
- Development process: `41fa13de8addaec6cc7c13c8be9da53c2c5527a302247d85b738f20c3155e864`.
- Worktrees guidance: `d7d8c9cce8315c17efaa1da05ece80c2542ca01b966f81fb848580104b785e1d`.
