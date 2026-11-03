## Анализ среза содержания T048 — 01.11.2026

Сопоставлены текущие дополнения spec/plan/tasks/contracts/quickstart с
конституцией и действующими F278 FR-014/041. Восемь групп требований
(три producer, сумма, отдельные фактические периоды, принятое resume,
исторический текст, безопасные поля/старые строки, транзакция/повторы,
остаток приёмки) покрыты существующей T048 и пятью сценариями quickstart.
87 исходных task ID сохранены; новых несопоставленных задач нет.
**CRITICAL 0 / HIGH 0; scoped coverage 8/8.** Это анализ требований,
не приёмка кода, денег или доставки.

| ID | Уровень | Факт и решение |
| --- | --- | --- |
| M1 | MEDIUM, остаток T048 | FR-105 плановый интервал не подтверждён во всех invoice snapshots; не восстанавливать его из текущего состояния, не считать требование выполненным. |
| M2 | MEDIUM, исторический контракт | Строка charged-after-refusal содержит отменённое правило; применимость F278 уже задана в начале spec. Этот срез не меняет права/согласие и не принимает старые специальные шаблоны. |

До кода нужен PASS независимого notification-content checklist, затем
настоящие producer/commit/new-session/rollback/dedup и профильные проверки,
review/converge и обычные три GitHub gates точного SHA/основы. Новая таблица,
служба, зависимость, платёж или grant не требуются. Вся T048/T068/#7524
остаётся открытой; исторические итоги ниже сохранены с этой границей.

# Применимость анализа — 01.11.2026

Исторические результаты ниже сохранены; сводка 80/7 и утверждение о
завершении T048/T075–T077 не описывают текущую приёмку. Истина текущих
отметок — tasks.md. Для среза содержания T048 нужны актуальные независимое
ревью checklists/notification-content.md и scoped analyze после уточнений;
до их PASS реализация запрещена. Общие T048/T068/T083 и #7524 не приняты.

# Cross-artifact analysis — 2026-08-11 (исторический отчёт)

## Результат

Повторно сопоставлены `spec.md`, `plan.md`, `tasks.md`, `contracts/`,
`quickstart.md` и `.specify/memory/constitution.md`. Критических
противоречий между артефактами не найдено. Выбранная lane — **high-risk
product area / active Spec Kit slice** (auth, billing, storage, deletion,
Temporal и UX); до публичного запуска обязательны DB-backed, live-provider и
manual UX gates.

## Покрытие

| Область | Статус | Evidence |
|---|---|---|
| Account/trial lifecycle | закрыто для выбранных сценариев | `tests/integration/test_account_lifecycle.py`, disposable PostgreSQL: 4 passed |
| Temporal billing maintenance | закрыто | `tests/contract/test_billing_reconciliation_workflow.py`, `tests/unit/test_billing_maintenance.py` |
| Storage admission | закрыто для выбранных сценариев | fail-closed artifact/expiry checks; DB/object-stat/supersede lifecycle проходит focused disposable-PostgreSQL evidence |
| Source WAV retention/COGS | реализовано с внешним gate | production gate-поля, exact-byte evidence и opt-in/fail-closed worker wiring есть; policy approval остаётся launch gate |
| Desktop billing handoff | частично закрыто | browser-owned route policy и regression matrix покрывают 12 billing routes; полноценный embedded summary, short-lived one-time authenticated handoff, URL query sanitization и live browser/network matrix остаются отдельным implementation/release gate |
| Security/accessibility/usability | interim | automated suites pass; live/manual review ещё обязателен |
| Product-market/pricing | hypothesis | интервью, WTP, 30-day usage, COGS и margin approval отсутствуют |

После последней проверки: **87 задач, 80 закрыты, 7 открыты**. Открытые
задачи: T078–T080, T083–T085 и T087. T036, T047, T053 и T075–T077 имеют
implementation evidence и закрыты в `tasks.md`. Desktop route tests не
подменяют поведение FR-012: native summary и одноразовый browser handoff
намеренно не объявлены реализованными без отдельного архитектурного среза.

## Findings

- В embedded settings финансовая навигация больше не ведёт на несуществующий
  `/desktop/settings/billing`: она передаёт пользователя в browser-owned
  `/billing`; macOS policy открывает денежные маршруты внешним браузером.
- Trial/account-close integration fixture теперь создаёт trusted
  `AuthSessionDeviceBinding`; полный disposable PostgreSQL сценарий проходит.
- Storage commit fail-closed проверяет expiry, workspace, verified canonical
  `meeting-review.m4a`, artifact bytes и запрещает `None` artifact.
- `source_lifecycle.py` содержит чистые правила и DB-backed gate/purge wiring;
  normal retention остаётся opt-in/fail-closed до утверждения политики, а
  accepted deletion/account-close имеет обязательный override path.

## Launch blockers

Публичный запуск запрещён до controlled canary T078, ручного T079,
live-security T080, подтверждения T084/T085 и повторного T083/T087. Checkout и реальные
платёжные мутации остаются default-off до merchant/legal/finance approvals.
