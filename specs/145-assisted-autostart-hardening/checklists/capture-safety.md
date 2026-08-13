# Requirement Quality Checklist: Capture Safety And Authorization

**Purpose**: Проверить полноту и однозначность требований к чувствительному assisted capture до реализации
**Created**: 2026-08-12
**Feature**: [spec.md](../spec.md)

## Authorization Boundary

- [x] Указано, какая policy считается действующей и что missing/expired state означает deny
- [x] Workspace scope и запрет внешнего rollout сформулированы явно
- [x] Acknowledgement привязан к точной версии и имеет безопасную миграцию
- [x] Per-target preference не подменяет workspace policy или acknowledgement
- [x] Offline поведение ограничено явным expiry

## Capture Authority

- [x] Требования различают button confirmation, timeout и saved-target authorization
- [x] Countdown, Skip, indicator и one-action Stop сохранены как обязательный контракт
- [x] Определён полный список gates для повторной проверки непосредственно перед стартом
- [x] Manual recording отделена от assisted-auto-start acknowledgement
- [x] Target end, competing recording и cancellation races покрыты acceptance scenarios

## Evidence And Privacy

- [x] Для каждого detector-assisted старта определена ровно одна стабильная причина
- [x] Требования запрещают ложный `.user` attribution для автоматического действия
- [x] Перечислены обязательные metadata-only поля policy/readiness evidence
- [x] Явно запрещены raw audio, transcript, meeting content, credentials и secret paths
- [x] Blocked path требует blocker и recovery evidence

## Readiness And Accessibility

- [x] Storage requirement требует фактического состояния, а не константы
- [x] Countdown boundary измерим на 7.999/8.000 s
- [x] Single-resolution и late-start prevention сформулированы однозначно
- [x] Оставшееся время требуется и визуально, и через accessibility semantics
- [x] Неизменность unknown/browser/manual-only suppression включена в acceptance

## Notes

- Requirement gaps, требующие ответа пользователя, не обнаружены.
- Production enablement намеренно не является acceptance condition этой feature.
