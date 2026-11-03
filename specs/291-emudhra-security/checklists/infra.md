# Infrastructure requirements checklist F291

Purpose: reviewer-owned requirements quality. Created: 2026-10-23.
Feature: [spec.md](../spec.md). `[x]` means reviewed requirements, not implementation. Main implementation must not mark items.

- [x] CHK001 Are existing owners, dirty checkouts and draft/public release boundaries addressed? [Coverage, FR-006/008]
- [x] CHK002 Are backup authority, restore gates and fail-closed execute behavior unambiguous? [Clarity, FR-005/007]
- [x] CHK003 Are safe rollback, health/smoke, repeated worker readiness and no data loss specified? [Recovery, FR-005, Edge Cases]
- [x] CHK004 Are server-only release and preserved macOS trust/assets boundaries defined? [Scope, FR-008]

## Reviewer notes — 2026-10-23

FR-005/007 preserve every backup/restore/release gate and explicitly stop execute without applicable backup authority. This approval does not grant that authority. FR-006/008 and quickstart preserve foreign work, distinguish draft/published releases and exclude new macOS publication. Required tasks.md reread remains pending after generation, before implementation.

## Независимое ревью применимости — 2026-10-28

Повторно прочитаны spec/plan/tasks/quickstart и release guidance. Все четыре
пункта остаются подтверждённой проверкой качества требований. Inventory
четырёх служб и связанный с точным source Full не заменяют исходные
backup authority/restore и все обязательные release evidence. У maintenance
нет healthcheck. Дополнительно прочитанные первичные журналы подтверждают
ранний `branch_mismatch` до удалённого CD, запись abandoned, затем отдельные
штатные dry-run/deploy с тем же source/evidence, smoke и повторной readiness.
Итог сверки и добавление quickstart сохраняют ранний отказ, поздний успех и
неподтверждённые authority/restore отдельно; `backup_result=pass` не принят
за восстановление. Требования rollback/no-data-loss не отменены.
Общая приёмка T007/T008 и закрытие #7734 этим ревью не разрешаются.
Подробности и контрольные суммы:
[независимый отчёт](../review-runtime-applicability-20261028.md).
После записи файл полностью перечитан: **4 checked / 0 unchecked**.
