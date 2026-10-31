# Validation: F276

Lane: significant-feature, high-risk governance. Доказательства ниже относятся
к локальному состоянию до коммита; последующая сверка PR и Full приведена
в дополнении от 2026-10-31. Приёмка публикации не заявляется.

## До реализации

- Spec/clarify/plan/checklist/tasks/analyze/issue sync завершены по порядку.
- Независимое requirements review: 6/6, затем сверка tasks PASS.
- Analyze: CRITICAL 0, HIGH 0, MEDIUM 0; все 5 FR/4 SC покрыты T001–T004.
- Исходные metadata/checks/scope: 211 PASS / 33,04 с.
- Новые положительные регрессии: 2 FAIL; плохие истории: 12 PASS / 5,73 с.
- Read-only общий verifier #7257 воспроизвёл merge/source range must be linear.

## После исправления

- Новые сценарии: 14 PASS / 6,73 с. Настоящие Git histories, trusted metadata
  subprocess; refs, индекс, tracked files и checkout неизменны.
- Ruff, git diff --check, development-process, pinned Spec Kit governance PASS.
- Расширенный набор metadata/checks/scope/collect_release_train/release_train:
  235 PASS / 89,89 с.
- Live common verifier #7257 PASS: head c0e63780576968d97ede7d4eda29c156e36c3561,
  recovered base 46ecd45ba9d4edd5348c634a837fb688f7ffb723, merge
  a057e29f502dd09cb33118f329ece30d1ea2a40e. Source governance 35691279972,
  macOS 35691280021, trusted metadata 35691400419, attempt 1.
- Live common verifier #7256 PASS: head f02b92098355341163f24899e15a46dea825510f,
  recovered base 14bce7042d0315fa87f53b9deaecfa8f0978f15e.
- F275 #7267 independently passed all required checks/common verifier and was
  merged normally as 0580a8903a472c65541cbfa8a474b77658145c80. F276 advanced
  to this base without changes to its two validated code/test files.
- Независимое implementation review выполняется; результат отдельно.

## Замечание C1 и повторная проверка

Независимое ревью обнаружило обход пошаговой проверки через прежний допуск
несовпадающих деревьев. Точная новая регрессия retained-extra сначала дала
ложный PASS валидатора (тест FAIL); контроль обычного advanced-target squash
из синхронизированного head прошёл. Пара: 1 FAIL / 1 PASS / 0,98 с.

Перед старым допуском теперь отвергается несовпадающее конечное дерево при
точной границе terminal-sync replay. Неоднозначный squash с той же границей
также получает отказ; это явно уточнено в spec/plan. Однозначные прежние формы
сохраняются. Повторный analyze: CRITICAL/HIGH/MEDIUM 0, покрытие FR 5/5,
SC 4/4; существующие T002/T003 покрывают исправление, новых задач не требуется.

Окончательный пятифайловый набор: **237 PASS / 93,54 с**. Повторный live
common verifier #7257 PASS с той же правильной recovered base. F275 #7267
проверен после merge новым валидатором: PASS, head 545f2dd11feb640b712c45a439053eb3190133b9,
base a057e29f502dd09cb33118f329ece30d1ea2a40e, merge 0580a8903a472c65541cbfa8a474b77658145c80.
Ruff, development-process, governance и diff checks повторно PASS.
Независимый повторный review ещё обязателен; собственные тесты его не заменяют.

## Окончательное правило после повторного C1

Повторное независимое ревью выявило сочетания dropped/extra с retained-extra.
Длина диапазона не доказывает, что история является squash. План уточнён:
при source head с несколькими родителями и разных конечных деревьях aggregate
ветка недоступна независимо от count. Requirements checklist повторно PASS 6/6
до изменения кода. Ранее aggregate-only допускавшийся synced-head/advanced-target
squash намеренно отклоняется, обычный linear-source advanced-target сохранён.

Добавлены обе комбинации и явная регрессия консервативного отказа. Окончательный
набор: **239 PASS / 101,36 с**; все прежние тестовые ожидания сохранены.
Ruff, development-process, pinned governance, diff PASS. Новый общий verifier
повторно подтвердил #7257/#7256/#7267 с указанными выше head/base/merge.
Все три результата получены окончательным кодом, stderr пуст.

SHA-256: validator d91ff39356901b384b2f235ecea0087e27dfcdb53f28f78d7286d8c10d91e5ab;
tests b6cb5c363a2244ae5271005c7a32ecdb9b5cb8870117e44512b94cd849cdea02.
Окончательный независимый review: PASS, C1 закрыт, blockers 0; собственные
89 metadata tests проверяющего PASS / 25,35 с. Хеши сверены, отчёт
implementation-review.md. Required GitHub checks ещё ожидаются.

Converge: 5 FR, 4 SC, 4 acceptance scenarios, все edge-case группы,
8 проектных решений и применимые V/VI конституции проверены. Реализационных
missing/partial/contradicts/unrequested gaps 0; новых задач нет, tasks.md
в режиме converge не изменялся. T004 остаётся открытой для фактических PR/release
gates, перечисленных в её критериях; локальный PASS не закрывает tracker.

## Границы

Не изменены продукт, production, настройки защиты, форматы доказательств и
старые тестовые ожидания. Required GitHub checks exact SHA/base, один frozen
release-full, подпись/Apple/publication остаются отдельными обязательными gates.


## Сверка технического завершения T004 — 2026-10-31

Документальная полоса: исходные критерии не меняются, код и тесты не меняются.
Отметка T004 завершает технический объём #7272; общая #7268 остаётся открытой.
Независимая сверка исходных spec/plan/tasks/quickstart и issue подтвердила эту
границу: публикация, Apple/Gatekeeper и установленное обновление относятся
к отдельному процессу выпуска. Infra checklist перечитан: 6 отмечено / 0 открыто.

### PR и текущая проверка происхождения

Исходный PR [#7273](https://github.com/yshishenya/graf/pull/7273):
head `5609514f1f6eb375c449571c35d91c0b03ce16ea`, проверенная основа
`0580a8903a472c65541cbfa8a474b77658145c80`, merge
`d0d1a9000921dc930a92033b0a76ce4b91a4cdc0`.
Общий текущий `validate-pr-checks.py` повторно подтвердил точный набор:
[governance-fast 35936301628](https://github.com/yshishenya/graf/actions/runs/35936301628),
[macos-pr 35936301480](https://github.com/yshishenya/graf/actions/runs/35936301480),
[pr-metadata 38807959289](https://github.com/yshishenya/graf/actions/runs/38807959289).
Текущие read-only проверки исторических #7257/#7256/#7267 также завершились
с кодом 0; они подтверждают сохранённые доказательства, не новое исполнение тестов.
Исторические 239 профильных проверок, причинные отказы, независимое ревью
с закрытым C1 и converge выше сохранены без пересчёта или суммирования.

### Подлинный frozen release-full

[Run 35937798319](https://github.com/yshishenya/graf/actions/runs/35937798319):
`release-full`, `workflow_dispatch`, attempt 1, completed/success.
Candidate SHA: `f5cca687a06dc57ad6ccbef840a0be897eaa6336`.
Candidate ID: `rc-20260924T001804Z-775067689749`.
Merge F276 является предком этого кандидата. Artifact `10784375810`
получен через GitHub API, `expired=false`, хранится до 2026-12-23.

SHA-256 исходного ZIP совпал с digest GitHub:
`1830e22adf27a502f18478de9c2fa357c7ca60e03511fe6baaa554e1a2f6d04b`.
Полностью прочитаны оба исходных JSON:

- `authoritative-rc-20260924T001804Z-775067689749.json`:
  `7e4e859bd3ef30f6d5d2eac46f4a3b55acf8db3f93544bff118130764055021c`.
- `receipt-35937798319.json`:
  `48cdeb93d289226e49d0e65dc67b4b429b19ce4388b041e93e27cb21802563fa`.

Receipt ссылается на точные байты authoritative evidence через
`local_evidence_digest`. Receipt подтверждает успешный статус, чистое состояние,
отсутствие отмены/замены и совпадение requested/start/end SHA. Связанный
authoritative evidence подтверждает `authoritative_full=true`, `lane=full`,
`status=passed`, `skipped_gates=[]` и совпадение всех component SHA с кандидатом.
Хеши валидатора и тестов на PR и candidate совпали с окончательным
независимым ревью: `d91ff39356901b384b2f235ecea0087e27dfcdb53f28f78d7286d8c10d91e5ab`
и `b6cb5c363a2244ae5271005c7a32ecdb9b5cb8870117e44512b94cd849cdea02`.
Фрагмент F276 присутствует в исходном PR и в
`changes/releases/v2026.09.24.1/F276.yaml` кандидата.

Новый Full ради отчёта не запускался. Новых сборок, выпуска, развёртывания,
публикации или запуска приложения нет. Пробелы исторической приёмки #7275,
сопоставление опубликованного тега кандидату, Gatekeeper до публикации и
настоящее установленное обновление не приняты и сохраняются в #7268.

Перед закрытием #7272 обязательны принятие этого документального изменения,
три проверки его точного SHA/основы, подробный комментарий и текущий
`validate-issue-closeout.py --verify-live`. Старый merged PR #7273 не редактируется.
