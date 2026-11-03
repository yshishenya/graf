# T101 — качество требований исторического replay

Создан26.10.2026. Reviewer-owned: `[x]` означает принятие качества требований,
не реализацию. Основной агент не меняет отметки. Активен только новый T101/T102.

- [x] CHK001 Различены ли source_checked_base и target_start, точные N/линейность/смежность, направление ancestry и возвращаемая база? [Clarity, Spec T101.1]
- [x] CHK002 Требуется ли доказать каждое промежуточное дерево, включая равный final, и определён ли отказ при конфликте/ошибке/неизвестном выводе? [Completeness, Spec T101.1–2]
- [x] CHK003 Явно ли ограничен squash независимым полным target prefix, включая изменения с возвратом, rename/delete и file-directory overlap; описан ли ambiguous отказ? [Coverage, Spec T101.3]
- [x] CHK004 Согласованы ли сохранённые sync/two-parent формы, source/proof/snapshot/run identity и границы исторической T098? [Consistency, Spec T101.4]
- [x] CHK005 Измеримы ли положительная/негативная настоящая Git матрица, consumers и сохранение checkout/refs/index? [Measurability, Spec T101.5]
- [x] CHK006 Разделены ли локальная реализация/exact-SHA PR и самостоятельные live verifier/Full/dry-run/CD/public gates без заявления продаж? [Traceability, Spec T101.6]

## Заметки проверяющего

Независимый reviewer `growth_infra_gate`,26.10.2026, HEAD
`2df314e5ca8549e636d386cdb68fecc861ddf015`: **PASS требований,6 checked/0 unchecked**.
Проверен текущий T101/T102 delta, прежние задачи/чек-листы не переотмечались.

- CHK001: spec:592–604 задаёт обе базы, равенство либо направление ancestry,
  N/линейность/смежность и исходную возвращаемую базу; plan шаг2 требует N пар.
- CHK002: spec:598–606 требует каждое полное дерево даже при равном final,
  перечисляет ошибки; plan шаг2 задаёт точный `merge-tree --merge-base`.
- CHK003: spec:607–616 и plan шаг3 требуют полный prefix и объединения путей
  каждого commit, включая возврат/rename/delete/файл-каталог; NUL/`--no-renames`
  сохраняют обе стороны. Overlapping настоящий squash явно может быть BLOCK.
- CHK004: spec:290 и:617–621, plan:225 и шаг4 сохраняют identity/receipts,
  отдельные sync/two-parent доказательства; историческая T098 не расширяется.
- CHK005: spec:622–629, plan шаг5 и quickstart:928–945 задают реальный Git,
  regression-before-fix, отрицательную матрицу и consumers; spec:621 требует
  неизменности checkout/refs/index/source. Это требования к будущим тестам.
- CHK006: spec:630–633 и quickstart:941–945 отделяют T101 PR от T102 выпуска;
  продажи/трафик/включение полной F273 не заявляются.

Полный отчёт и SHA-256 проверенных артефактов:
[`validation-rebase-requirements-20261026.md`](../validation-rebase-requirements-20261026.md).
Чек-лист перечитан после записи:6 `[x]`,0 `[ ]`. Tasks T101/T102, analyze,
issue sync, regression/fix, независимое review кода и все release gates ещё
предстоят; этот PASS не разрешает их пропускать и не является runtime PASS.
