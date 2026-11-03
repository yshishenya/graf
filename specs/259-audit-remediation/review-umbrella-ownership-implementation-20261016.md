# Независимое итоговое ревью F259/#7631 — 2026-10-16

Рецензент: отдельный агент `review_f259`; автор реализации — другой агент.
Объём: US3, новый ремонт учёта собственной задачи главной issue, T024–T026.
Рабочая копия: `/Users/yshishenya/.codex/worktrees/issue-closeout-owner/crisp`.
Основа: `e8ec10f812c375d1a538c43d2750260e29eaf2a5`.
Полоса: active Spec Kit / high-risk-product / significant governance.

## Вердикт

**PASS после независимой повторной проверки исправления.**
Нерешённых замечаний: CRITICAL 0, HIGH 0, MEDIUM 0. Общий ремонт минимален;
исключение теперь требует точного разрешённого состояния OPEN.
Первоначальное замечание о неизвестном состоянии устранено до принятия.

### Устранённое замечание: неизвестное состояние главной issue

Первоначальный guard разрешал любое состояние главной issue при
`allow_open_umbrella`. Независимое воспроизведение вернуло `[]` для
`UNKNOWN`, пустой строки и None на корректных синтетических задачах и
комментариях. Это не соответствовало условию допуска только OPEN.

Автор минимально дополнил исключение точной проверкой OPEN и добавил
три отрицательных значения в существующую направленную регрессию.
Рецензент перечитал изменённые код/тест и независимо повторил вызовы:
OPEN даёт `[]`, каждое из UNKNOWN/пусто/None даёт отказ
`issue #6415 for T017 is still open`. Замечание устранено; код и тесты
рецензент не менял.

## Что подтверждено

- Общий цикл теперь учитывает главную issue через тот же _owned_task_ids,
  _task_state/validate; отдельно child_issues её не содержит. Нет F265-
  исключения, новой функции, формата, зависимости или сетевого запроса.
- Двойной владелец, отсутствие задачи, unchecked и неправильная обратная
  ссылка проверяются общими прежними механизмами. Комментарий/PR/SHA/CI
  остаются обязательными для открытого главного владельца.
- Закрытая главная issue сохраняет T000, closedAt и строгий порядок после
  детей; раннее, равное и отсутствующее closedAt проверяются.
- Новый runnable test содержит OPEN/CLOSED положительные случаи, отдельный
  отказ без флага, 13 исходных отрицательных вариантов и три неверных
  состояния; ordinary dependency T999
  не становится владельцем.
- Исправлены только две прежние некорректные положительные T017 fixtures.
  Независимое сравнение AST всех 59 прежних функций тестового файла
  подтвердило сохранение всех прежних assert без изменений. В self-test
  изменены только разрешённые синтетические данные T017 и её комментарий.
- Diff не меняет validate (single-issue), live/PR/run/candidate/release
  fences, CLI или workflow. Сравнение AST подтверждает
  структурную эквивалентность остальных 13 функций валидатора.
  require_release_full передаётся в validate
  прежним способом; отсутствие GitHub writes сохранено.
- T024/T025 отмечены, T026 остаётся открытой до успешного независимого ревью;
  все три связаны с #7631. Документы не объявляют завершение F265, всего
  backlog F259 или наличие точных PR checks/merge.

## Выполненные и прочитанные проверки

Рецензент самостоятельно выполнил без bytecode/cacheprovider:

- `pytest tests/governance/test_validator_safety.py -q -p no:cacheprovider`: **54 passed, 0.61 s** (повтор после исправления состояния).
- `python3 scripts/validate-issue-closeout.py --self-test`: **OK**.
- Независимый in-memory сценарий состояния: описанный выше отказ защиты
  сначала воспроизведён, после исправления повторно подтверждён отказ для
  всех трёх неверных значений; реальные issues не затрагивались.
- AST прежних assertions: **59/59 функций сохранены**.

Перечитаны исходные журналы f259-umbrella-before.log и after.log: первый
показывает **1 failed, 53 deselected** именно с `T017 has no task-backed
issue in the feature inventory`, второй — **54 passed, 0.63 s**.
Ruff/governance/changelog/diff PASS записаны автором в validation; рецензент
не выдаёт их за собственный повторный запуск. Анализ до кода и канонический
владелец #7631 проверяются по сохранённому локальному артефакту/задачам,
не по новому live API; GitHub рецензент не менял.

## Повторное чтение контрольных списков

Качество требований остаётся **35 checked / 0 unchecked**:
requirements 13/0, numbering 6/0, three-digit-numbering 9/0, umbrella-ownership
7/0. Первоначальное замечание касалось реализации и устранено; качество уже
ясного требования не переотмечалось.
Три исторических списка совпадают с HEAD. Отметки не подтверждают приёмку
279 исходных issues, платформы macOS, реальный выпуск или закрытие F265.

## SHA256 рассмотренных источников

- `0626370928c0f45a71bb3168194191bb449fd1af633d810bf8a6bea52a087b77` — `scripts/validate-issue-closeout.py`
- `97811576ef3888c99da556e33cd6e1ab31844f8d2e187e6e6843564ffa7f8a5a` — `tests/governance/test_validator_safety.py`
- `0b102677b5676d517c1f02b277a000d106d33913ec0169bc34fa67a8062b5261` — `specs/259-audit-remediation/spec.md`
- `28a3d6ffc4dbfc8d5588814509d842c68d7c9b52caf89cf70c608b0fd4191134` — `specs/259-audit-remediation/plan.md`
- `27359dc53434da105f8e218ce890f6f1a041517890f553c81c690fd5a1addfe9` — `specs/259-audit-remediation/tasks.md`
- `9575866ccc7b297a8d2bcbe7281f39d0e81fe4567932ebe64a192b08f28ed422` — `specs/259-audit-remediation/quickstart.md`
- `258d8ed6514a7386035c0593cf558f78a01d853468fb40ea0de68f0c2f0b954b` — `specs/259-audit-remediation/validation-umbrella-ownership-20261016.md`
- `cfa3307d4b18ba35f3dca4dbda42604971a1a85d9543937e6afb6d5440e946fb` — `specs/259-audit-remediation/checklists/requirements.md`
- `0700cdac78bd3040e1d7e0e9d7beed279c3c908bd4c8481c61d7d1d5bd641245` — `specs/259-audit-remediation/checklists/numbering.md`
- `934f39d21ae3c97534ff9acc644f32802d0437667723c2e627ec06c0c7c0e52c` — `specs/259-audit-remediation/checklists/three-digit-numbering.md`
- `6d6d0800f487967a5cf96994773f40833b8b853933ec165c2c6f49c4fedbc09d` — `specs/259-audit-remediation/checklists/umbrella-ownership.md`
- `282bd7bb6cd6ed895e6d99ac9c83cec48716acd33ffc79fe4e9dd5cb6f1e9214` — `changes/unreleased/F259.yaml`
- `e1e850f20dbb4d2ffcd3a6ad5c409360ccc27ca6dc373819ddc0996f6ac29196` — внешнее доказательство `F259-umbrella-ownership-analysis.json`
- `156998598546fffdc690d11b71d5254e4416b3d850eb4f7ec33d640610e049b8` — внешнее доказательство `checks/f259-umbrella-before.log`
- `e2620e2b1e7472bd158acdec0e01ec64e8589a8bb2871a86176a0df306b975a1` — внешнее доказательство `checks/f259-umbrella-after.log`
