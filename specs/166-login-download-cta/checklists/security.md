# Security Requirements Checklist: Контекстная ссылка на приложение на экране входа

**Purpose**: Проверить, что auth boundary не расширяется изменением CTA
**Created**: 2026-08-18
**Feature**: [spec.md](../spec.md)

## Auth Boundary

- [x] Спецификация сохраняет существующую нормализацию same-origin `next` [Security, FR-004]
- [x] Embedded decision не зависит от доверенного client header, cookie или user-agent [Security, Assumption]
- [x] Новая ссылка ведёт только на существующий same-origin `/download` [Security, FR-001]
- [x] Auth/session/provider/invitation semantics явно исключены из изменения [Security, FR-004, FR-007]

## Failure And Privacy Coverage

- [x] Auth errors сохраняют доступность формы и legal copy без утечки meeting content [Failure, FR-006]
- [x] Нет новых токенов, credentials, analytics payloads или persistent state [Privacy, Key Entities]
- [x] Небезопасный внешний `next` не превращается в новый redirect [Edge Case, FR-004]

## Traceability

- [x] Каждое security-ожидание связано с FR, assumption или edge case [Traceability]
