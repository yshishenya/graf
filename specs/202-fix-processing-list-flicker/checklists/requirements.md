# Specification Quality Checklist: Стабильные статусы обработки

**Purpose**: Проверить полноту спецификации до планирования
**Created**: 2026-08-25
**Feature**: [spec.md](../spec.md)

- [x] Симптом отделён от подтверждённой причины [Clarity]
- [x] Один владелец structural/terminal состояния указан явно [Consistency]
- [x] Failed, active, processed и stale-response состояния покрыты [Coverage]
- [x] Стабильность DOM, текста, геометрии, focus и selection измерима [Measurability]
- [x] Browser и embedded cabinet входят в общий scope [Parity]
- [x] Upload/playback, provider retry и deploy явно ограничены [Scope]
- [x] Нет `[NEEDS CLARIFICATION]` и блокирующих продуктовых решений [Readiness]

## Clarification Result

Пользователь просит исправить дефект на общей поверхности. Безопасный default:
web и embedded cabinet исправляются одинаково; сервер владеет terminal truth,
клиент — только временным текстом active processing. Вопросов, меняющих scope
или продуктовый результат, не осталось.
