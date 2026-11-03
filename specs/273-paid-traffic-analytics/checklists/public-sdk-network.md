# T106 — изолированный профиль настоящего SDK

Reviewer-owned; до кода все пункты проверяет независимый reviewer.

- [x] CHK001 Явно определены настоящий официальный SDK/SHA, реальный контроллер и CookieConsent, две поверхности, analytics-only и положительный контроль instance+watch; заглушка SDK или нулевая активность не дают PASS.
- [x] CHK002 Все HTTP/WebSocket перехватываются без forwarding, только учебный counter/данные; неизвестный SDK input даёт ошибку без сетевого fallback, внешние цели и частные данные запрещены.
- [x] CHK003 Отзыв той же/другой вкладки проходит реальную библиотеку/storage/controller; граница и finite20с с0 optional attempts/удалённым instance измеримы, клики/scroll/focus/visibility названы.
- [x] CHK004 Причинный control точно ограничен проверкой оставшегося instance; собственная временная копия не меняет продукт, прежние modal/Node/server guards и обязательные review/exact PR gates сохранены.
- [x] CHK005 Честно сохранены ограничения локальных backend replies, replay/global/individual/runtime/T0 и всего T106; нет рабочего включения, неявной CI сети, новой инфраструктуры или изменения scope.


## Независимое before-code ревью — 01.11.2026

Проверяющий:`/root/public_counter_readiness_review`.
Непосредственно наблюдённый HEAD:`94c40e0b78da2e222c0318ded5d89f0c8174f012`,
ветка:`codex/f273-public-sdk-proof-20261101`.
**PASS требований test-only профиля:5 отмечены/0 открыты;
P1/P2/HIGH0.** Матрица/хеши/границы —
[отчёт](../validation/public-sdk-network-review-20261101.md).
Реализация и actual четыре сценария ещё не приняты. Конечный analytics-only
профиль с локальным backend не принимает весь SDK/replay/globalpermission/
individualrevoke/runtime/T0/T106 и не разрешает внешнее включение.


## Повторное requirements review provider_smoke — 01.11.2026

**PASS узкого уточнения учебной конфигурации**: существующий provider_smoke
вместо render_only позволяет positive SDK контроль только в изолированной
локальной странице. Interception устанавливается до SDK, продуктовые flags
и SDK bytes не меняются. Первый instance FAIL сохраняется, черновой CLI
ещё не принят. Checklist перечитан: **5 отмечены/0 открыты; P1/P2/HIGH0**.
Хеши/пределы — в том же [отчёте](../validation/public-sdk-network-review-20261101.md).


## Повторный gate общей cleanup после integrated RED — 01.11.2026

**PASS минимального нового требования: сохранить исходный ym.a/custom push
обратным in-place splice только своего counter.** SDK Bi и final subscription,
неизменный GRAF filter и оба caller прочитаны; причина потери subscriber
подтверждается исходниками. Scope расширен явно только на эту cleanup и
причинную Node регрессию, остальные product/runtime изменения не разрешены.
Checklist перечитан: **5 отмечены/0 открыты; P1/P2/HIGH0**.
Реализация/настоящий SDK GREEN ещё не приняты, прежние external/T106 HOLD
сохранены. Детали/hashes — в [отчёте](../validation/public-sdk-network-review-20261101.md).


## Первое implementation review — 01.11.2026

**HOLD code/converge:1P2, P1/HIGH0** — catch любого исключения SDK ожидания
выдаёт expected negative marker instance-still-present. Требуется выдавать
его только после TimeoutError и отдельного подтверждения существующего
instance; unknown/другие ошибки не должны приниматься negative control.
Остальная cleanup/isolation/positive4scenarios/регрессия проверена;
детали/hashes — [отчёт](../validation/public-sdk-network-review-20261101.md).
Checklist требований перечитан: **5 отмечены/0 открыты**. Эти отметки
не принимают текущий код и не снимают прежние external/T106 HOLD.

## Повторное implementation review и scoped converge — 01.11.2026

**PASS узкого SDK профиля и cleanup; открытых P1/P2/HIGH — 0/0/0.**
P2 устранено: expected instance marker возможен только после TimeoutError
и отдельного true чтения реального instance; прочие ошибки не маскируются.
Прочитаны исправленный CLI, неизменные product/Node/modal diff и свежие
сводки: 4/4 normal PASS с0после отказа за20s; negative expected-instance
и closed-page без ложного маркера PASS. Источники результатов и пределы
независимой проверки указаны в [отчёте](../validation/public-sdk-network-review-20261101.md).
Checklist перечитан: **5 отмечены/0 открыты**. Прежний HOLD выше исторический;
external включение, runtime/T0, весь T106 и цели трафика/продаж остаются
непринятыми; exact PR/base и release gates проверяются отдельно.
