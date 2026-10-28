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

## Повторная сверка платформы — 28.10.2026

Предлагаемое решение: отменить T013/#6327 и T021/#7662 как NOT_PLANNED,
сохранив исходный объём и условия будущего безопасного перехода. Причина —
совокупность применимости платформы и отсутствия нужного изменения защиты,
а не отсутствие evidence. Подробные границы — уточнение 28.10 в `spec.md`.

- GET `repos/yshishenya/graf`: public, `owner.type=User`.
- [GitHub Docs — Managing a merge queue](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-a-merge-queue),
  прочитано 28.10.2026, точная цитата:
  “Pull request merge queues are available in any public repository owned by an
  organization, or in private repositories owned by organizations using GitHub
  Enterprise Cloud.”
- SHA256 ответа документации:
  `e399632c3e8d33cfaa81e69a5534f964e62e6c9c392a52b442e036ab0fd53d78`.
- GET protection: strict=true; governance-fast/pr-metadata/macos-pr с app_id
  15368; linear history и conversation resolution=true; approvals=0;
  force_push=false, deletions=false. Состояние защиты не меняли.
- GET runs(event=merge_group): 0. Это дополнительное наблюдение, не
  доказательство невозможности и не выполненная проверка очереди.
- `.github/pr-check-policy.json` сохраняет foundation PR #6987, SHA
  `a3f5f72e994e7872ee175ebafd9f7699a2d4ffca`, activated_at
  `2026-09-13T13:18:40Z`; само наличие этой записи не доказывает старый откат.

Альтернативы: переносить репозиторий/покупать тариф/писать свою очередь только
ради старого плана — лишнее усложнение MVP; переключать уже действующие защиты
ради отчёта — ненужный риск. Ни одна альтернатива не выполняется. Текущие
последовательные защищённые PR и общий exact-SHA validator продолжают работать.
Решение вступает в силу после независимого ревью и принятого PR; задачи до
этого остаются открытыми. Для будущего конкретного изменения защиты снова
нужны план, реальные сценарии, полномочия, expected-state и проверка отката.
