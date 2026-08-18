# Security Requirements Checklist: Непрерывная навигация кабинета

**Purpose**: Проверить, что shell/UI slice не ослабляет auth, tenant, CSRF и
safe-profile boundaries.
**Created**: 2026-08-17
**Feature**: [spec.md](../spec.md)

## Boundary Completeness

- [x] Unknown-email, explicit signup, invitation/provider, email-code, expired session и legacy `/sign-up` paths определены. [Spec §US3]
- [x] CSRF, OAuth state/nonce, exact-email, account-linking, session, rate-limit, tenant, role и billing boundaries перечислены как неизменяемые. [Spec §FR-012–FR-013]
- [x] Safe profile projection явно ограничена display name и verified email; sensitive fields перечислены. [Spec §FR-005, Key Entities]

## Failure and Recovery

- [x] Expired session, CSRF failure, blocked external continuation и unauthorized settings category имеют отдельные truthful outcomes. [Spec §Edge Cases]
- [x] Partial update/idempotence и отсутствие duplicate handlers заданы как проверяемые security/robustness invariants. [Spec §FR-015]
- [x] No new auth state, route, account model, persistence or User-Agent trust decision is introduced. [Spec §Out of Scope, plan]

## Evidence and Privacy

- [x] Synthetic-only and metadata-only evidence requirements запрещают credentials, tokens, real meetings, audio, transcript, signed URLs и private screenshots. [Spec §FR-016, contracts]
- [x] Public download CTA does not expose direct artifact URLs or alter updater ownership. [Spec §FR-004, Out of Scope]

## Traceability

- [x] Every security boundary maps to focused contract/integration tests in `tasks.md` and `quickstart.md`.
