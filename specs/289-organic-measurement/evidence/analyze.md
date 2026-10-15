# Analyze 2026-10-16

Проверены текущие spec/plan/tasks/research/data-model/contracts/quickstart и constitution 7.1.0. Threshold: CRITICAL 0, HIGH 0, нет блокирующих уточнений. Scope только четырёх путей; optional/provider/identity и выпуск не входят.

| Requirement | Tasks | Acceptance |
|---|---|---|
| FR-001/002 | T002/T003 | SC-001/002, закрытый каталог, текущий путь, safe UTM |
| FR-003/004 | T002/T003 | SC-002/003, cookie/L2/provider не добавляются, legal/kill/DB |
| FR-005 | T002/T003/T005 | HTML/static и прежние scope, соседние регрессии |
| FR-006 | T004 | SC-004, актуальные источники/периоды и 90-дневный план |
| FR-007 | T001/T005 | SC-005, independent checklist, issue sync, checks, commit/release approval |

Зависимости последовательны, пути определены. Существующий необязательный PUBLIC_CONTENT_SURFACES нельзя расширять; отдельный каталог устраняет конфликт. F282 меняется явно только на уровне 1. Кодовая проверка не заявляется до выполнения T002–T005. Reviewer-owned checklist остаётся отдельным pre-implementation gate. Неопределённости юридического запуска персональной аналитики не входят в этот срез.

Итог: CRITICAL 0 · HIGH 0 · MEDIUM 0; planning/analyze PASS. Перед реализацией ещё нужен independent checklist PASS и issue sync.

Совместимость tooling: установленный check-prerequisites.sh не поддерживает --require-spec из skill; после --help использован --json --require-tasks --include-tasks, наличие spec проверено напрямую. Защиты не обходились.

После чтения writer gate уточнена семантика отсутствующего withdrawal register: это прежнее разрешение уровня 1, а не новое основание для отключения. Spec/plan/quickstart согласованы с текущим legal gate, новые проверки сохраняют explicit withdrawal и kill switch. FR-004/SC-003 охвачены без изменения общей политики. Повторный analyze: CRITICAL/HIGH/MEDIUM 0.
