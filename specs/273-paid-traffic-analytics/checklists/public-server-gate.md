# T106 — серверная граница public событий

- [x] CHK001 Определены прежний public scope, точные flag/env/revision/surface и независимость от product provider flags.
- [x] CHK002 Действующее основание, валидный пустой register, unknown/missing/error и отзыв только provider_analytics определены без нового хранения или кэша.
- [x] CHK003 Context, самостоятельный relay и повтор delivery перед side effect используют свежее решение; существующий PostHog final gate и consent/catalog guards сохраняются.
- [x] CHK004 RED/GREEN проверяет настоящие context/route/delivery и реальный меняющийся временный register; охватывает отказ, независимость уровней и гонку.
- [x] CHK005 Границы принятия честны: внешний SDK/старые вкладки/индивидуальный серверный отзыв/T0/полный T106 открыты; рабочие флаги закрыты; review/converge/exact PR gates обязательны.


## Независимое before-code ревью — 01.11.2026

Проверяющий: `/root/public_counter_readiness_review`.
Основа: `e8a67a7e21046a641b2bdd0f1caf75aca7895e6f`.
**PASS узких требований и плана: 5 отмечены / 0 открыты; P1/P2/HIGH0.**
Матрица каждого пункта и пределы — [отчёт](../validation/public-server-gate-review-20261101.md).
Допуск относится только к server context/relay/delivery. Код, actual SDK,
старые вкладки, индивидуальный серверный отзыв, измерение/T0 и весь T106
этим не приняты. Внешнее включение сохраняет прежний HOLD.


## Независимое implementation review / converge — 01.11.2026

**PASS узкого server кода, P1/P2/HIGH0.** Прочитаны actual diff и журналы,
настоящая route→worker гонка с реальным register, unknown/error отказ,
opt-in fixture и сохранение consent/scope/final PostHog gate.
RED2failed→GREEN2passed; broad112pass/1fail/1skip исправлен точной fixture
предпосылкой и повтором30pass/0skip, actual modal/NodePASS. Проверяющий
тесты не запускал. Checklist перечитан: **5 отмечены /0 открыты**.
Матрица/границы/хеши — в [отчёте](../validation/public-server-gate-review-20261101.md).
Exact PR gates, T106 целиком, SDK/старые вкладки/индивидуальный серверный
отзыв/runtime/T0 остаются открытыми; внешнее включение сохраняет HOLD.
