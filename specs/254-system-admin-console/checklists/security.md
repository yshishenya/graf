# Ревью требований: security

Дата: 2026-09-06. Глубина: строгая, перед реализацией. Владелец: ревьюер. `[x]` означает оценку качества требований, не выполненную реализацию. Генератор и исполнитель не отмечают пункты за ревьюера.

- [x] CHK001 Определены ли независимые identity/session и запрет всех обычных credential путей? [Полнота/согласованность; FR-001–010; contracts/security.md]
- [x] CHK002 Достаточно ли определены bootstrap, потеря MFA, replay, отзыв и последний бессрочный superadmin? [Полнота/согласованность; AC-001–004; contracts/security.md]
- [x] CHK003 Разделены ли metadata, content, download, retained, admin assignment и scope? [Полнота/согласованность; spec.md роли; contracts/security.md]
- [x] CHK004 Определены ли реальные DB роли, secrets, schema grants, helpers, pool и worker boundary? [Полнота/согласованность; plan.md; contracts/security.md; T002–T007]
- [x] CHK005 Полны ли правила auditable intent/effect, отказа аудита, повторного доступа и поздних результатов? [Полнота/согласованность; FR-071–080; data-model.md; AC-033–036]
- [x] CHK006 Однозначны ли контент/CSV/cache/XSS и точное системное авторство? [Полнота/согласованность; FR-086–088; contracts/api.md; contracts/security.md]

## Независимое ревью требований — 2026-09-06

Ревьюер: `admin_access`, отдельный исследовательский проход после подготовки автором. Проверены текущие документы на базе кода `a389657e607ef8389fcf947b26b158cee6928884`; это ревью требований, не запуск реализации.

- CHK001–002: `contracts/security.md` — отдельный origin/principal/session, version-bound challenges, recovery только enrolment, recovery_pending, ротация TOTP-ключа; `data-model.md` §1 и AC-001–004 согласованы.
- CHK004: `contracts/security.md` — restrictive RLS поверх PUBLIC, отдельная схема/роль, credential isolation, ограниченный владелец worker helpers и per-target continuation; `contracts/migration.md` и T002–T007 предусматривают отрицательные проверки.
- CHK005–006: `data-model.md` §1, `contracts/api.md`, `contracts/security.md`, AC-033–039 — durable intent/effect, повторная авторизация выдачи, отказ аудита, distinct system actor, безопасный вывод/CSV/no-store, сохранение поздних обязательств.
- CHK003: после повторного чтения согласованы UI §14, key-level settings allowlist и API queue.pause/resume; настройки ограничены ролью, recipient ID и числовыми пределами. Case contexts и content.export не расширяют независимые audio/diagnostics права.

Проверены устранения предыдущих 1 CRITICAL/6 HIGH и трёх неточностей модели/порядка bootstrap. Runtime auth/RLS/конкурентность/скачивание, секреты и production не проверялись. Отметки не разрешают выпуск и не заменяют T007/T012/T015/T037.

Завершающее чтение 2026-09-06: отдельно проверен новый scheduled approval в security/API/data-model и AC-022. Он закрепляет точные command/target/parameters, актуальное authorizing permission и источник assignment/grant с версиями; browser expiry не равен отзыву, но revoke/security reset/expiry исходного grant закрывают неисполненное действие. execute_at и фактический запуск находятся внутри срока grant. Ранее выявленный пробел временного grant устранён автором и повторно проверен. Все шесть пунктов удовлетворены на уровне требований; оставшихся блокирующих замечаний в проверенной области нет.
