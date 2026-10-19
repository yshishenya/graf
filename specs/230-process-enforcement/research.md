# Research: восстановление F230

## Решение: использовать существующие механизмы

- Decision: F216/F227/F234/F235 остаются владельцами allocator/context/receipt/workflow.
- Rationale: требования отменённых F230 задач совпадают с проверенной принятой
  реализацией; текущий набор context/allocator дал 169 PASS/15 PowerShell SKIP.
- Alternatives considered: переписать механизмы в F230 — повторная работа и риск новых расхождений.

## Решение: одна процедура делегирования

- Decision: добавить секцию в `docs/agent-guidance/development-process.md`.
- Rationale: файл уже содержит роли, scoped context и ownership; в текущем тексте
  отсутствует явный результат read-only исследователя, требуемый #6330.
- Alternatives considered: отдельный агентный framework, новая глобальная skill,
  дублирование root/generic harness — не требуется текущим результатом.

## Решение: восстановить намерение, не изображать потерянные байты

- Decision: источники — текущие публичные тела исходных issues и фактический код.
- Rationale: прежние spec/plan/tasks не найдены после уже выполненной широкой
  проверки. Таблица восстановления сохраняет номера/смысл и отменённых преемников.
- Alternatives considered: считать отсутствие файла завершением или восстановить
  ложные [X] — нарушает tracker truth и исходные критерии.

## Решение: read-only наблюдение не меняет enforcement

- Decision: GET GitHub protections/rulesets/runs; результаты привязывать к source SHA.
- Rationale: уже действуют governance-fast, macos-pr, pr-metadata. Очередь слияния
  и merge_group — другой сценарий; отсутствие запусков не доказывает его приёмку.
- Alternatives considered: включить queue ради проверки или выдать PR за merge_group —
  меняет внешний процесс без rehearsal/отдельного разрешения и скрывает пробел.

Конкретные API-наблюдения независимого исследователя сохраняются отдельно в validation;
эта запись проектного решения не подменяет фактический rehearsal.
