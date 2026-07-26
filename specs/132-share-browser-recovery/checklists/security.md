# Security Requirements Checklist: browser invitation error responses

**Purpose**: Validate that the auth and secret-handling requirements are
complete before implementation.

**Created**: 2026-07-26

**Feature**: [spec.md](../spec.md)

## Authentication and authorization

- [X] Are successful first entry, replay, expiry, revoke and recipient mismatch
  requirements all defined? [Completeness, Spec FR-001, FR-006]
- [X] Is it explicit that presentation changes cannot create or broaden access?
  [Clarity, Spec FR-006]
- [X] Is the distinction between browser responses and explicit API responses
  defined without weakening auth checks? [Consistency, Spec FR-005, FR-006]
- [X] Are CSRF, session, grant and RLS protections named as preserved
  invariants? [Coverage, Spec FR-006]

## Secret and privacy boundaries

- [X] Does the specification prohibit tokens and continuation state in the
  error page? [Completeness, Spec FR-007]
- [X] Does it prohibit recipient email, meeting content, audio links and stack
  traces in browser errors and evidence? [Completeness, Spec FR-007]
- [X] Is metadata-only logging explicitly required for this flow? [Clarity,
  Spec FR-008]
- [X] Are link-preview and duplicated-tab scenarios covered without disclosing
  the meeting? [Edge Case Coverage]

## Failure and compatibility

- [X] Are API status, content type and Problem Details fields required to remain
  compatible? [Consistency, Spec FR-005]
- [X] Is the safe behavior for malformed or unknown invitation state defined?
  [Coverage, Spec FR-002, FR-003]
- [X] Are no-new-session and no-new-grant outcomes measurable? [Measurability,
  Spec SC-003]
