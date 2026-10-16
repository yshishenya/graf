# Независимая проверка требований F259: владелец главной issue

Дата: 2026-10-16. Рецензент: отдельный агент `review_f259`.
Рабочая копия: `/Users/yshishenya/.codex/worktrees/issue-closeout-owner/crisp`.
Ветка: `codex/259-umbrella-task-ownership`, HEAD `e8ec10f812c375d1a538c43d2750260e29eaf2a5`.
Полоса основного этапа: active Spec Kit / significant governance.
Рецензент изменяет только новый контрольный список и данный отчёт.

Вердикт после повторной проверки уточнённых plan/quickstart: **PASS, 7/7; CRITICAL 0, HIGH 0**.
Первоначальный FAIL CHK007 устранён документальным уточнением до реализации.
Продуктовый код и тесты ещё не изменены. Новые исполняемые задачи T024+
должны появиться после устранения противоречия, затем требуются analyze и
согласование внешнего трекера до реализации. Это не нарушение текущей
последовательности и не подтверждение будущих задач.

## Основания по пунктам

| Пункт | Результат и основание |
|---|---|
| CHK001 | PASS. Уточнение spec от 2026-10-16 задаёт ownership через канонический title/Spec tasks, checked task с `(Issue #N)`; обычные упоминания исключены. Это соответствует `_owned_task_ids`/`_task_state`, issue canon. |
| CHK002 | PASS. Spec явно отклоняет duplicate owner, неизвестную задачу, unchecked и неверную обратную ссылку; план сохраняет существующий validate. |
| CHK003 | PASS. allow-open разрешает состояние OPEN только для главной issue; задачи, комментарий, PR/SHA/CI остаются обязательными. Дочерние должны быть CLOSED. |
| CHK004 | PASS. Spec сохраняет T000, closedAt и строгий порядок после всех дочерних. План оставляет главную issue вне child_issues; существующие equal/early timestamp отказы остаются. |
| CHK005 | PASS. Single-issue/live/release сохранены, новых GitHub writes/закрытия нет; локальный снимок не выдаётся за live validation. |
| CHK006 | PASS. План переиспользует существующие парсеры и validate, без исключения для F265, новой схемы, зависимости или сетевого запроса. |
| CHK007 | PASS после уточнения. Матрица и воспроизведение определены; план и quickstart явно разрешают исправить две неверные положительные синтетические связки, сохранив все assertions/отрицательные ожидания и строгий отказ для неизвестных задач. |

## Первоначальное замечание и его устранение

В `tests/governance/test_validator_safety.py:629` положительный тест
`test_feature_closeout_requires_closed_unique_children_and_umbrella_last`
объявляет у #6415 задачу T017, отсутствующую в tasks. `--self-test`
`scripts/validate-issue-closeout.py:580` делает то же. Оба комментария
называют T001. Прежний skip umbrella скрывает некорректность данных.
Общий ремонт должен её выявлять. После замечания plan.md и quickstart.md
явно разрешили исправить обе положительные синтетические связки на checked
T017→#6415 с T017 в её комментарии, сохранив все прежние assertions и
отрицательные сценарии. Ослабление validate и исключение ради прохождения
старой некорректной fixture прямо запрещены. Противоречие устранено.

## Прежние контрольные списки

- requirements.md: 13 отмечено, 0 не отмечено. Сохраняется исторический
  ограниченный PASS качества US1–US3/FR001–011/SC001–005 и датированного
  реестра. Текущая добавка усиливает доказательное закрытие US3; не
  утверждает повторную проверку 279 исходных issues или завершение F259.
- numbering.md: 6 отмечено, 0 не отмечено. Это исторический ремонт
  FR023–026/SC006–007; последующее ограничение 999 явно заменило допущение
  F1000+ именно в GRAF. Формулировки и исторические отметки не изменены.
- three-digit-numbering.md: 9 отмечено, 0 не отмечено. Действующие FR027–029
  и SC008/009 сохраняют диапазон, занятость, отказ до записи, единый номер
  и исходный bootstrap; новый slice их не меняет. Формулировки не изменены.

Всего после повторного чтения: **35 отмечено, 0 не отмечено**
(13+6+9+7). Старые три файла совпадают с HEAD.
Их runtime/CI и старый снимок GitHub повторно не принимались.

## Ограничения и доказательства

Проверены фактический текущий цикл validate_feature, оба парсера, validate,
существующие положительные/отрицательные fixtures и локальная диагностика
`F265-precloseout-structural-errors.json`. Снимок содержит и 9 ошибок SHA
дочерних комментариев: ремонт ownership сам их не устраняет и не разрешает
закрытие #7002. Требуется отдельная проверка реальных комментариев и exact
PR/checks после принятия кода. Тесты не запускались; рецензент не менял код,
тесты, spec/plan/tasks, GitHub, PR, коммиты, выпуск или развёртывание.

Исторические research/data-model содержат прежние формулировки нумерации;
позднее уточнение spec и contracts явно заменяет предел, а текущая работа
не меняет allocator. Общий backlog остаётся открытым.

## SHA256 прочитанных источников

- `384c41c0b1674a3daf75d0e57646379198295c3f8452012c8101fc6332bec58b` — `AGENTS.md`
- `40e357e422c60915d2c4334c83b9ab74f5ef4c0df6ab8831e3ed16e281ba18a6` — `docs/agent-guidance/README.md`
- `7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8` — `.specify/memory/constitution.md`
- `5edf818b6ee27c7ee66d14edc003325ec7b16789eb1a195377cdeb901ae44887` — `docs/agent-guidance/spec-kit-flow.md`
- `06450200cabdef48000af51241564e9ee9e8d36b50c71e06a88f8c50b7365466` — `docs/agent-guidance/tracker-policy.md`
- `7cd5c1cde2bb51e3842cae9e3717b094fea9f6fbb33fb1a408e6d243f9d68bf3` — `docs/agent-guidance/github-issue-canon.md`
- `e3d24689a330634ec5ef87d829f8bcbf16bb7b81e0196b9d0baae4f49f27278d` — `docs/agent-guidance/release-and-validation.md`
- `0b102677b5676d517c1f02b277a000d106d33913ec0169bc34fa67a8062b5261` — `specs/259-audit-remediation/spec.md`
- `28a3d6ffc4dbfc8d5588814509d842c68d7c9b52caf89cf70c608b0fd4191134` — `specs/259-audit-remediation/plan.md`
- `6001c230ce62d3974664415f576d8fe051d391258631e10bebe0603b6ebf9d85` — `specs/259-audit-remediation/tasks.md`
- `9575866ccc7b297a8d2bcbe7281f39d0e81fe4567932ebe64a192b08f28ed422` — `specs/259-audit-remediation/quickstart.md`
- `ad09e4013356c3b24e880fc1cd9f4d0fc23805f3a2cb8ca36bf2cef1c86aef71` — `specs/259-audit-remediation/research.md`
- `b8f42ab32f72dac79b61fab7f83ff9dac6776022eb55a3d87769bfe40882b762` — `specs/259-audit-remediation/data-model.md`
- `d1c9e3e06cd97191c44e9dc8feabfde84090d66b27340f78763b94a2276959c8` — `specs/259-audit-remediation/contracts/allocator.md`
- `17e2b598f34eb0b188ba57dc6528d63f6d1d2506cd2ce84b5e5c1a6eb17fb151` — `specs/259-audit-remediation/backlog.md`
- `8f53e081bddf119a693db440fbd60f65be5814fe959fcad75c3ba128a01ddbbf` — `specs/259-audit-remediation/issue-inventory.md`
- `cfa3307d4b18ba35f3dca4dbda42604971a1a85d9543937e6afb6d5440e946fb` — `specs/259-audit-remediation/checklists/requirements.md`
- `0700cdac78bd3040e1d7e0e9d7beed279c3c908bd4c8481c61d7d1d5bd641245` — `specs/259-audit-remediation/checklists/numbering.md`
- `934f39d21ae3c97534ff9acc644f32802d0437667723c2e627ec06c0c7c0e52c` — `specs/259-audit-remediation/checklists/three-digit-numbering.md`
- `6d6d0800f487967a5cf96994773f40833b8b853933ec165c2c6f49c4fedbc09d` — `specs/259-audit-remediation/checklists/umbrella-ownership.md`
- `cd4792412c42acb5858fbbdbe7b1d0ad81228eaa14cfb998257c7f0b0422e8af` — `scripts/validate-issue-closeout.py`
- `6fac877d17009bddb0882cf2312f2f2634970f60326db394f98a628b0278a868` — `tests/governance/test_validator_safety.py`
- `028f72523db73ecc075939bdb6f8dc51d6492785b1ad0e761399a60937c3e170` — внешняя структурная диагностика F265.
