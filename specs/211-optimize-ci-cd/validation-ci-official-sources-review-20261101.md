# F211 T112 — независимое ревью требований до кода, 01.11.2026

Проверяющий: `/root/public_counter_readiness_review`.
Рабочая копия: growth-protocol-result/crisp.
Непосредственно проверены ветка `codex/f211-ci-official-sources-20261101`,
HEAD `ca02e2cf9bb4d761cc1d24bde230a8071c078361` и активный указатель
`.specify/feature.json`: F211/T112, active-spec-kit. Физическое имя рабочей
копии не использовалось как источник выбора фичи.

**PASS качества требований T112: 5 checked / 0 unchecked.**
Открытых замечаний P1/P2/HIGH: **0/0/0**. Это не review реализации и не
разрешение миновать tasks/analyze/issue sync или проверки выпуска.

## Основания по пунктам

| Пункт | Основание в текущих документах | Вывод |
| --- | --- | --- |
| CHK001 | Spec T112 прямо заменяет историческое правило сохранения ubuntu.sources только для GitHub-hosted Linux Ubuntu24.04/noble, native amd64 без foreign architectures. Исторические T099/T110/T111 и незнание AWS URI сохранены. В отличие от нового допуска cloud URI, задан фиксированный проверенный выход. | PASS |
| CHK002 | Весь вход ограничен размером, типом файла, владельцем/правами и защищённым parent; keyring также проверяется. Поля и значения перечислены исчерпывающе, flat ASCII deb822 не допускает продолжений/повторов/unknown fields. Только заменяемый URI может быть неизвестным; trust overrides запрещены. План называет native os-release/dpkg проверки. | PASS |
| CHK003 | Для каждой suite сохраняются Types/components/architecture/Signed-By/Enabled; отсутствующие suites/компоненты/deb-src не добавляются. Mixed stanza делится по suite; security получает security.ubuntu.com, остальные три suite — archive.ubuntu.com, только HTTPS. apt-mirrors.txt и сторонние sources не меняются. | PASS |
| CHK004 | Полная проверка до побочных действий; собственный temp в том же parent, uid/gid/mode, write/flush/fsync, atomic replace, readback и finally cleanup названы. Повтор совпавших bytes сохраняет mtime. Ошибка до replace оставляет исходник; после replace останавливает APT без ложного заявления отката. Подмена перед replace также даёт отказ. | PASS |
| CHK005 | Plan/quickstart расширяют существующий actual-shell профиль трёх YAML callers, явно моделируя root metadata только на непривилегированных fixtures. Названы RED/GREEN, package tuples, mixed/security-only/no-security/deb-src/optional architecture, platform/owner/mode/keyring/format и write/readback отказы. Сохранены independent review/converge, analyze/issue sync, exact PR gates и обычный Full нового кандидата без случайных диагностических наборов. | PASS |

## Применимые документы и согласованность

Полностью прочитаны новые разделы T112 spec/plan/quickstart и checklist;
затронутые T099/T110/T111, относящиеся к ним задачи и итоговый отчёт
`validation-aws-apt-20261031.md` прочитаны ранее в текущей проверке дизайна.
Проверены текущие tasks routing/статусы и активный указатель: T110 `[ ]`,
T111 `[X]`; исполняемой T112 пока нет по запрошенному порядку checklist gate.
Это не считается доказательством готовности задачи или выполненного analyze.

Конституция перечитана, в том числе III/VI и обязательный reviewer gate.
Прочитаны guidance index, document-reading, spec-kit-flow,
development-process, codex-worktrees и применимые CI/exact-SHA/release разделы
release-and-validation. Использовано разрешённое владельцем исключение F211
для повторного чтения затронутых разделов; хеши PRD, merged status и
product-gates совпали с ранее прочитанными и записанными значениями.
Новых продуктовых, пользовательских данных или зависимостей T112 не вводит.

Конституционных противоречий в проекте не найдено: подписи/ключи/доверие APT
и прежние required checks сохраняются; неизвестный URI заменяется как инертное
входное поле, не открывается/не исполняется/не разыменовывается/не печатается.
Root-owned одноразовый runner обозначен границей доверия, доказательство
защиты от root/kernel compromise не заявлено. Отдельная нормализация выхода
не выдаётся за установление фактического AWS формата.

После промежуточной обратной связи владелец явно уточнил в spec/plan
`GITHUB_ACTIONS=true`, `RUNNER_OS=Linux`,
`RUNNER_ENVIRONMENT=github-hosted` и отказ на C0 кроме TAB/LF и DEL во всём
файле, включая URIs. Изменённые разделы T112 перечитаны целиком; они сохраняют
принятую границу и снимают необходимость толковать hosted/ASCII при code review.
Неизвестный credential URI без управляющих символов допустим только для
замены, без обращения/печати. Остальные хеши требований не изменились.

Существующий helper/harness на момент ревью не изменены: `git diff` по ним
пуст. Их прошлые результаты относятся к прежней политике и не используются
как PASS T112. После checklist PASS обязательны добавление исполняемой T112
с точными путями, scoped analyze и issue sync, затем реализация и отдельное
независимое code review/converge. Если эти документы изменят принятую границу,
нужно повторное ревью затронутых требований.

## Ограничения и выполненные действия

Проверяющий не запускал тесты, CI, сетевые обращения, APT/sudo, серверы,
Git/GitHub mutations, release или deploy. Выполнены только чтение, локальные
hash/status/diff проверки и изменение двух собственных reviewer файлов.
Чужие изменения сохранены. После отметок checklist перечитан: **5/0**.

Не приняты: реализация T112, фактические native/root проверки hosted runner,
успешная подготовка пакетов/скорость, exact PR checks, Full кандидата,
release/CD/runtime/T0 и цель трафика/продаж. T110/#7849 не закрываются этим
решением; отсутствие необходимости выяснять AWS для нового способа подготовки
не равно выполнению исторического диагностического критерия.

## Хеши прочитанного состояния

- Spec: `bf303f86fcdb5c4ed5f6b5967ca12cbcf834bd2be1454c3d25eb015bfb7b450d`.
- Plan: `b92f7413f5ec6a20f522d2eba6f0be930609a93e4d9a6ff05de6f277114a9eb5`.
- Tasks до добавления T112: `ea02e3381215f6fdbb7a095e33bc21fc94ce0627978afc23b4815ed7e2d7edf0`.
- Quickstart: `0de76c9aa2c64d2c92a46c384a8e523b3ed55ee48e563b60ddb7d354f0ae0d51`.
- Неизменный helper: `c5e2e851d2b79ba9d1ab7bcdc5da2f9e52c6721bb9faefed6d6ded233fcf68c9`.
- Неизменный harness: `110f6cd771f0786112bbefca628017d3857cd4fe5bc56499ad85dec582a5de6d`.
- Конституция: `7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8`.
- PRD: `0f3ccfcfa60062bb0aae6802eeb0012056a635a30cb9f46f54d1992d0b4f57c2`.
- Merged status: `25b7f383be47c7160da8e852006ff82019f30a5f9c371fc30baa79238649cd16`.
- Product gates: `9f7072c879490d250053cb7397ad6b9b68fdcde17bdf9367ed874a41e450b5f5`.
- Guidance index: `2f3e0339a89d3ccdf0878026920955a189584d6a985116b069584cd78b3c75bb`.
- Document-reading: `5263860b1974df022826ac81c2482e6ee92100bc0bb718ab5a29b32e2422e411`.
- Spec Kit flow: `afb816ce48624eb79fcd7fd44d09f0986296e87ef1cfecd790228ac70a5b9b9e`.
- Development process: `41fa13de8addaec6cc7c13c8be9da53c2c5527a302247d85b738f20c3155e864`.
- Release guidance: `ff0d996c95101d5f782259661131db1b7528b3bf58991603f5652092e1e5256f`.
- Worktrees guidance: `d7d8c9cce8315c17efaa1da05ece80c2542ca01b966f81fb848580104b785e1d`.
