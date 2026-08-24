# Security Requirements Checklist: Email-code retry

**Purpose**: Validate auth security requirements before implementation closeout
**Created**: 2026-08-25
**Feature**: [spec.md](../spec.md)

## Rate limiting and replay

- [x] Three failed checks per state are explicitly specified and measurable [Spec §FR-001–FR-002]
- [x] The correct code cannot bypass a blocked state [Spec §FR-002]
- [x] Existing email, IP and resend limits are explicitly preserved [Spec §FR-006, Edge Cases]
- [x] Expiry, replay and browser binding remain fail-closed [Spec §FR-006, FR-007]

## Secret and audit boundaries

- [x] Code, token, email and state nonce logging restrictions are explicit [Spec §FR-008, Edge Cases]
- [x] Audit behavior is specified without sensitive values [Spec §FR-008]
- [x] No schema or migration change is assumed without a documented reason [Spec §Assumptions]
