# Requirement Quality Checklist: Capture Reliability And Session Truth

**Purpose**: Проверить полноту и однозначность требований полного пути автозаписи до реализации
**Created**: 2026-08-23
**Feature**: [spec.md](../spec.md)

## Source And Candidate Lifecycle

- [x] Каждый поддерживаемый системный source назван и имеет независимое состояние
- [x] All-source end boundary и grace сформулированы однозначно
- [x] Порядок, повторы, задержки и пропущенный end покрыты edge cases
- [x] Startup, unexpected finish, deliberate stop и wake имеют разные требования
- [x] Snapshot не расширяет allowlist и проходит обычные debounce/policy gates

## Authorization And Trigger Handling

- [x] Countdown promise требует ту же current policy/ack pair, что и start
- [x] Immediate pre-start recheck перечисляет все изменяемые gates
- [x] Consumer acceptance отделена от detector emission
- [x] Retryable и terminal outcomes определены и измеримо ограничены
- [x] Skip/manual Stop/accepted handling запрещают duplicate restart до end
- [x] Manual Record/Stop явно не зависят от assisted acknowledgement

## Authentication

- [x] Web/native authority и same-origin scope определены
- [x] Replacement, logout, expiry, scheme, domain и path описаны
- [x] Deterministic cookie selection не зависит от storage order
- [x] Credential egress остаётся в существующем dedicated header boundary
- [x] Registry recovery и fail-closed cache behavior включены в требования

## Diagnostics And Evidence

- [x] Source, decision, consumer, observer и final capture outcomes трассируются
- [x] Reason codes и retryability стабильны и не требуют meeting content
- [x] Raw system lines, audio, transcript, cookies, tokens и secret paths запрещены
- [x] Observer recovery ≤5 s и trigger re-evaluation ≤2 s измеримы
- [x] Production config, installed app, deploy и release исключены без approval

## Notes

- Критических неоднозначностей, требующих ответа пользователя, нет.
- Server-side fail-closed policy contract остаётся без изменений.
