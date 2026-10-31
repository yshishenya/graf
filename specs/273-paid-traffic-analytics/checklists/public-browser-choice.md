# T106 — требования актуального локального выбора

Reviewer-owned. До кода пункты проверяет независимый reviewer.

- [x] CHK001 Требование точно называет сохранённые категории/редакцию/state, fail-closed при ошибке и общую проверку всех управляемых side effects, без нового источника идентичности.
- [x] CHK002 Указаны cross-tab/clear/resume, stale-positive callback и свежий явный grant; lifecycle не переписывает чужой выбор и не создаёт скрытого повторного старта.
- [x] CHK003 Штатный destruct, собственная очередь и порядок отключения описаны, ошибки не открывают отправки; автономная остановка настоящего SDK отдельно не принята.
- [x] CHK004 RED/GREEN считаются по фактическим relay/ym вызовам; modal и старые согласие/replay/каталог регрессии сохраняются; независимое review/converge и exact PR обязательны.
- [x] CHK005 Объём остаётся T106/#7696 без рабочего включения/новой инфраструктуры; server permission, индивидуальный server revoke, полный SDK/T0 и критерии роста остаются открытыми.


## Независимое before-code ревью — 01.11.2026

Проверяющий:`/root/public_counter_readiness_review`.
Основа:`b18f1a485a4b500c4b6a2c92667b4464b205016d`.
**PASS требований узкого локального выбора:5 отмечены/0 открыты;
P1/P2/HIGH0.** Матрица/хеши/пределы —
[отчёт](../validation/public-browser-choice-review-20261101.md).
Это не приёмка кода/actualSDKstop/serverpermission/индивидуальногоserverrevoke/
T0/всегоT106. Внешний SDK остаётся HOLD; рабочих отправок не разрешает.


## Независимое implementation review / converge — 01.11.2026

**PASS узкой реализации; P1/P2/HIGH0.** Actual JS/test diff и журналы
проверены: свежая saved-choice граница, stale callback до записи,
lifecycle без автостарта, fresh grant, идемпотентный destruct и очистка
только own counter queue. RED воспроизводит отправку после revoke,
GREEN18scenarios/0skips,focused53pass/0skips с actual modal.
Проверяющий тесты не запускал. Checklist перечитан: **5 отмечены/0 открыты**.
Детали/hashes — [отчёт](../validation/public-browser-choice-review-20261101.md).
External SDK/global permission/individualserverrevoke/T0/весьT106 HOLD
сохранены; exact PR/runtime приёмка этим не заменяется.
