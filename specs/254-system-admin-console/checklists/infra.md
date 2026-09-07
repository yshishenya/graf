# Ревью требований: infra

Дата: 2026-09-06. Глубина: строгая, перед реализацией. Владелец: ревьюер. `[x]` означает оценку качества требований, не выполненную реализацию. Генератор и исполнитель не отмечают пункты за ревьюера.

- [x] CHK001 Определены ли isolation, migrations, mixed-writer barrier и safe rollback? [Полнота/согласованность; contracts/migration.md; T004/T037]
- [x] CHK002 Полны ли provenance/freshness зависимостей, backup и отдельный restore? [Полнота/согласованность; FR-075–079; AC-035]
- [x] CHK003 Измеримы ли server/client performance, outage, refresh и resource limits? [Полнота/согласованность; SC-006–009; plan.md; research.md; T038]
- [x] CHK004 Сохранены ли existing capture, LiteLLM/Langfuse и retained deletion boundaries? [Полнота/согласованность; plan.md Constitution Check; FR-073/078]
- [x] CHK005 Определены ли release и macOS gates отдельно от результатов подготовки? [Полнота/согласованность; quickstart.md; T039]

## Независимое ревью требований — 2026-09-06

Ревьюер: `admin_access`; проверка документов после авторской подготовки, база кода `a389657e607ef8389fcf947b26b158cee6928884`.

- CHK001: `contracts/migration.md` — additive schema, повторный bootstrap, writer barrier + final catch-up до lag=0, несовместимый binary rollback запрещён; `contracts/security.md` — отдельные origin/process/DB role и продолжение принятых обязательств.
- CHK002: UI §13–14, FR-075/079 и AC-035 разделяют время наблюдения, неизвестное состояние, backup и подтверждённый restore; без обещания универсального удаления.
- CHK003: `plan.md` Technical Context, `research.md` «Принятые технические пределы», `telemetry-and-metrics.md` §5, `quickstart.md`, AC-042 и T038 задают объём/профиль стенда, p95, лимиты pool/report, 60-min outage, M1/8GiB CPU/memory сравнение.
- CHK004: Constitution Check в plan, `contracts/security.md`, UI §5/13–14 сохраняют native capture/Stop, существующее управление LiteLLM/Langfuse и retained границы.
- CHK005: `quickstart.md` и T039 явно отделяют будущие проверки, exact-SHA/release/deploy и Developer ID/notarization/Sparkle от готовности документов.

Отметки подтверждают измеримость и согласованность требований. Docker, DNS/TLS, runtime роли, миграции, нагрузка, backup/restore и macOS проверки не выполнялись; production не исследован. Их фактический результат остаётся открытой реализацией T004/T007/T029/T036–T039.
