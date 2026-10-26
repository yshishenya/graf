# F211 T101–T102: доказательство исторического переноса

Дата:26.10.2026. Ветка `codex/211-release-rebase-proof`, исходный master
`2df314e5ca8549e636d386cdb68fecc861ddf015`. Lane: active Spec Kit slice,
high-risk CI/infrastructure. Текущий срез — T101/T102, issue
[#7742](https://github.com/yshishenya/graf/issues/7742); общая F211 остаётся открытой.

## Причина и предел исправления

Общий `checked_base` использует trusted metadata, `ci-pr-scope.resolve` и
`validate-pr-checks.code_snapshot/verify`. PR #7714 переносит четыре commits
на продвинутую цель. Старый aggregate на parent последнего переноса повторно
добавляет уже перенесённый файл и даёт
`merged tree cannot be reconstructed from checked base`.

Новая проверка доказывает каждое промежуточное дерево с явным source parent
через `git merge-tree --write-tree --merge-base=...` и возвращает исходную
проверенную базу. Равенство только конечного дерева недостаточно. Для squash
запасное aggregate-доказательство допускается лишь при полном независимом
линейном target prefix: учитываются пути каждого изменения source и target,
включая отменённые изменения, обе стороны rename/delete и файл/каталог.
NUL-разделители сохраняют имена с пробелами, переводами строк и табуляцией.

Настоящий squash с пересечением путей может блокироваться как неоднозначный:
доступные входы не всегда отличают его от испорченного replay. Whitelist,
patch-id, сообщения/авторы commits, новая proof-схема и обход gate не добавлены.
Прежние two-parent/terminal-sync формы и source/API/run/attempt/freshness
доказательства сохраняются. Проверка не меняет checkout, refs, index и source.

## До исправления

- Исходный focused-набор четырёх consumers:241 PASS,67.14s.
- Первая настоящая Git-регрессия:5 FAIL/13 PASS; корректный advanced replay
  и четыре full-consumer сценария блокировались старым helper до проверки receipts.
- Расширенная shape-регрессия:8 FAIL/24 PASS,21.44s. Старый код ошибочно
  принимал order/intermediate подмены при правильном final и пять вариантов
  пересекающегося squash. Корректный advanced replay ошибочно блокировался.
- Локальные журналы остаются в игнорируемом `.dev/release/`; SHA-256 журнала
  shape-регрессии `06e7efe9dbdc6b77b34a1a79d1092621d9d140d6d09a427f3d274138a01611db`.

## Матрица после исправления

| Область | Исполняемые проверки |
|---|---|
| Настоящий Git | 4 исходных commits с повторными изменениями добавленного файла; replay на прежнюю и продвинутую цель; исходная база сохраняется |
| Подмена истории | count, drop, extra, order, intermediate/final tree, nonlinear source/target, unrelated start, conflict, missing head/merge отклоняются |
| Squash | Независимый prefix принимается; same-path, transient target/source, rename/delete, ancestor file/directory и unusual-name overlap отклоняются |
| Ошибки Git | merge-tree error/unknown/multiple output, rev-list empty/invalid/noncontiguous/missing-first, ancestry error, diff error/non-NUL output отклоняются |
| Consumers | Настоящий scope и полный verifier сохраняют source base/diff; wrong receipt base, failed fixed gate и stale metadata отклоняются |
| Совместимость | Прежние two-parent, synced squash/rebase, double snapshot, repository/head/ref/state/merge/run/attempt/freshness проверки остаются в общем focused-наборе |
| Неизменность | HEAD, refs, bytes index и исходного validator сравниваются до/после trusted проверки |

Окончательный focused-набор четырёх файлов: **288 PASS/95.40s**,0 FAIL,
после последних изменений кода. Ruff, development-process, bootstrap/governance,
changelog fragments, `git diff --check` и относительные Markdown-ссылки:PASS.
Независимое [implementation review](validation-rebase-code-review-20261026.md):
первоначальный BLOCK снят; reviewer самостоятельно проверил11 отказов/допусков
на конечных байтах. Requirements checklist по-прежнему6 checked/0 unchecked.
Ранние36 PASS и282 PASS/92.47s не подменяют окончательный результат.
SHA-256 окончательного журнала:
`5b34b91216286bd58d0297a003d76b50ce89d3e283bc36260ca9e9e7f514f3a7`.

SHA-256 конечного кода:`52c57bc0c95a9a06afbb9e518a8370f58115f65416d09b11df44c1a61f6296e7`.
Тесты metadata:`f2f4f29faa2188729762fd7237685f7567567d9480ba3fc776751b6306b66b80`;
тесты checks:`48b142dfda67ea7550f9ee540f622d490422810092747cc6d0c9a771e2dfab45`.

Независимый reviewer обнаружил fail-open пустого/повреждённого `rev-list`
в запасном пути. Общий перехват ValueError удалён: валидность SHA/начала/
смежности/объёма проверяется до разрешённой неподходящей формы squash.
Дополнительно ошибки ancestry и неправильный NUL-вывод не считаются
доказательством независимости. Для этих отказов добавлена исполняемая регрессия.

## Настоящий historical PR

Общий live `validate-pr-checks.py --repository yshishenya/graf --pr 7714`
после первичного исправления:PASS,26.10.2026.

- Head:`50dd6724bed8f109c9de8b26339de20341c8c49f`.
- Source checked base:`79abe38fcce9d1a16ae8fc34f8f1f26b17b2ea4d`.
- Target start:`c60c2725d024e6ba0a9490364de7e57dc45820db`.
- Immutable merge:`25039ec43ee62e40a971e6a8d969bdfdaf0e840e`.
- `governance-fast`:run39709355733/attempt1.
- `macos-pr`:run39709355708/attempt1.
- `pr-metadata`:run39709354835/attempt1.
- SHA-256 JSON результата:
  `9595d0ba47cef000fb191e65143a81d636ee235d952d7357425156159738f088`.

Это настоящая проверка ранее слитого PR, отдельно от synthetic provider facts
в локальной Git-матрице. Она не означает успешную приёмку всего диапазона
следующего выпуска или самого нового PR.

## Процесс и оставшиеся ворота

Пользователь разрешил для F211 scoped повторное чтение: все затронутые
требования и зависимости перечитаны,7/7 хешей остальных базовых документов
совпали. Новое полное чтение всего PRD/status не заявляется. Requirements
checklist принят независимо6/0; отчёт
[`validation-rebase-requirements-20261026.md`](validation-rebase-requirements-20261026.md).
Scoped analyze:6 групп/2 задачи,100% покрытия,CRITICAL0/HIGH0/MEDIUM0;
issue canon300 PASS до кода. T098/CHK004 и другие исторические задачи не меняются.

Convergence ограничена новым T101-контрактом. Все шесть групп покрыты
реализацией/проверками или уже открытыми T101/T102; новые дубли задач не нужны.
T101 остаётся открытой до exact-SHA/base PR checks и merge. T102 требует
общего live verifier каждого PR диапазона, нового frozen candidate, одного
authoritative release-full, штатного dry-run/backup/CD и публичной приёмки.

Последний опубликованный stable при проверке26.10 — `v2026.10.22.1`, source
`8e37e0e3570372d7375151bf6624d5f0dcc3e627`; `v2026.10.22.2` остаётся draft.
Старый кандидат не используется как актуальное доказательство.
Product measurement на рабочем сервере ещё выключено. Трафик, атрибуция и
продажи не подтверждаются этим исправлением; коммерческие AC01–AC06 открыты.

Среда:Git2.44.0,Python3.13.3,Ruff0.15.20; новые зависимости не установлены.


## Дополнение P2: обычные commits после синхронизации

Review4378496721 PR #7745 выявило регрессию прежнего synced-squash proof:
однородительский head ошибочно считался доказательством линейности всего
source range. Требования T101.4/CHK004 сохраняют прежнюю поддержанную форму;
независимая проверка требований и воспроизведение —
[отчёт reviewer](validation-rebase-nonterminal-sync-review-20261026.md).

До исправления расширенная существующая Git-регрессия:2 FAIL/10 PASS.
Отказали только правильные истории с1/2 обычными commits после sync merge.
Исправление в общем checked_base проверяет наличие merge во всём точном
диапазоне parent..head перед выбором линейного доказательства. Наличие merge
маршрутизируется в прежнее отдельное доказательство точного tree/parent/count;
неизвестный вывод, несколько SHA или ошибка Git не становятся fallback.
Общий helper linear_rows и consumers не ослаблены.

После исправления пять профильных файлов, включая validator safety:
**475 PASS/88.10s**. Матрица существующего synced squash расширена0/1/2
последующими commits и неверными tree/count/parent, продвинутым API base,
неизменностью HEAD/refs/index. Проверены отказы нового Git-запроса.
`python3 -m ruff check` (Ruff0.15.20), process/governance/changelog/diff:PASS.
Устаревший внешний shim `ruff` показал прежние E721/F811; проверка выполнена
закреплённым модулем подготовленной среды, без новых зависимостей.
Игнорируемый feature context исправлен на допустимый lane active-spec-kit;
фактическая high-risk инфраструктурная область и обязательные проверки сохранены.

Конечные SHA-256 кодовых файлов:
- validator:1d45434a65a4bc0f88b3e0d615b468020531b7dd61ecd91cd0c06d9cbe7dd772;
- metadata tests:c57cabae1dd3177fac1b3d6d213d7b37213651243bd7ca60e48a93ad3e290436;
- checks tests:1002b386c118b01015e4caa037b2163b07d7c71468e3abef976db386820bcae0.

Журналы сохранены локально в .dev/release/t101-nonterminal-{before,focused,static}.log.
Независимое implementation review:PASS,22 самостоятельные настоящие Git
проверки, точные хеши и6/0 checklist в отдельном отчёте. Новые exact-SHA/base
GitHub checks и merge проверяются отдельно; старые успешные runs на a160 не принимают новый commit.
T101/T102 и коммерческие AC остаются открытыми.
