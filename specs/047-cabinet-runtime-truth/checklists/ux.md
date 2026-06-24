# UX Requirements Checklist: Cabinet Runtime Truth

**Purpose**: Validate that cabinet status requirements are clear, user-safe, accessible, and consistent across desktop and web.
**Created**: 2026-06-24
**Feature**: [spec.md](../spec.md)

**Note**: This checklist validates requirement quality. It does not test implementation behavior.

## Requirement Completeness

- [X] Are configured, checking, ready, server-unavailable, auth-required, denied, not-found, and blocked states covered?
- [X] Does the spec forbid green/success state before runtime proof?
- [X] Does the spec preserve local recording controls during cabinet failures?
- [X] Does the spec require web and embedded desktop parity checks?

## Requirement Clarity

- [X] Is "server unavailable" separated from ordinary logged-out/auth-required copy?
- [X] Is successful login page load explicitly not a ready state?
- [X] Are visual tone expectations measurable without prescribing exact final design?
- [X] Is metadata-only evidence required for UI checks?

## Scenario Coverage

- [X] Server restart after a prior ready state is covered.
- [X] Timeout, 5xx, 401/login, and route-blocked cases are covered.
- [X] Mobile/desktop overflow and text overlap checks are included.

## Notes

- No blocking UX requirement gaps found before implementation.
