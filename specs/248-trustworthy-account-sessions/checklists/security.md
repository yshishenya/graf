# Security requirements review
Reviewer-owned; отдельный рецензент заполняет после проверки spec/plan/contracts.
- [x] CHK001 Ясно ли различены display hint и auth/trust доказательство? [FR-001–003]
- [x] CHK002 Полон ли контракт отзыва direct/binding-only, current/foreign/replay/CSRF? [FR-007–009]
- [x] CHK003 Определены ли expiry, недопущение оживления и атомарные RLS-переходы? [FR-005–009, plan]
- [x] CHK004 Ограничены ли данные/доказательства и область рабочего пространства? [FR-003,011–012]

## Reviewer evidence — 2026-09-06
Независимый рецензент: references. Проведён read-only speckit-analyze по spec, plan, data-model, contracts/sessions, tasks, quickstart, research и constitution v6.0.0; prerequisite подтвердил Feature 248. YAML hooks разобран: включённых before/after_analyze hooks нет.

- CHK001 PASS: FR-001–003, plan §Architecture 1–2 и contracts явно отделяют ограниченный display hint от доказательства доступа; аппаратные идентификаторы и raw UA не собираются.
- CHK004 PASS: FR-003/011/012 и quickstart ограничивают область рабочим пространством, требуют синтетические данные и запрещают секреты/частный контент в evidence.
- CHK002/CHK003 OPEN: A1 (HIGH). FR-005 и data-model требуют разрешённую связанную регистрацию для active, но plan §Architecture 3 и contracts допускают unbound API bootstrap. Не указан единый критерий legitimately unbound против потерянной/заблокированной связи, разрешённые границы доступа и его UI-состояние. До реализации согласовать этот случай в spec/data-model/contracts и добавить проверку отсутствующей, заблокированной и никогда не созданной связи в T005/T007. Остальной контракт owner/workspace/CSRF, replay, device/direct/binding revoke, expiry и server-side invalidation описан.

Все 12 FR и 4 SC имеют покрытие задачами T001–T009; это проверка полноты требований, не доказательство работы реализации. Gate пока не пройден из-за A1.

## Повторная проверка — 2026-09-06 — PASS
A1 устранён: во всех четырёх артефактах согласован и повторно прочитан раздел Unbound API bootstrap. Законный bootstrap требует NULL device_id и полного отсутствия bindings; missing/blocked/несогласованная существующая связь отклоняется. Principal-only доступ ограничен прежними маршрутами, tenant/cabinet запрещены до регистрации. UI явно показывает «Клиент не зарегистрирован» и позволяет отзыв из другого сеанса владельца. FR-005 называет исключение; T005/T007 содержат проверки обеих сторон границы.

Итог независимого speckit-analyze: CRITICAL 0, HIGH 0, блокирующих уточнений 0; A1 закрыт после исправления автором. Покрытие 12/12 FR и 4/4 SC задачами, 9 задач без потерянных связей. Все пункты этого checklist приняты как требования. Это разрешает следующий этап Spec Kit после issue sync, но не заменяет тесты, проверку реализации, converge и exact-SHA PR gate.
