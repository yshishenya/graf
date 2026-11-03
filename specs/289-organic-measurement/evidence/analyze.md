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

## Повторный анализ перед T006

Прочитаны актуальные spec/plan/tasks, контракт, data-model и конституция.
FR-001/003 и SC-002 прямо запрещают новый L2. T006 исправляет ошибочную
реализацию этих требований без нового продукта и привязана к открытым
#7603/#7605. План теперь сохраняет PUBLIC_PAGE_SURFACES и
surface_for_public_path для прежней атрибуции, ANONYMOUS_PAGE_SURFACES и
surface_for_anonymous_page обслуживают только бакет уровня 1. Каталог
необязательных провайдеров не расширяется. T001–T005 сохраняют покрытие
FR-001–008; T006 добавляет отрицательную cookie/acquisition регрессию.
Порядок: requirements review → причинный RED → runtime → соседние проверки
→ независимое code review → новые SHA-bound gates. Требующих решения
владельца неопределённостей нет. CRITICAL 0 / HIGH 0 / MEDIUM 0, coverage
8/8 FR; T006 не меняет основание, хранение или включение уровня 2.
