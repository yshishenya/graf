# UX Requirements Checklist: Email-code retry

**Purpose**: Validate recoverable auth UX requirements before implementation closeout
**Created**: 2026-08-25
**Feature**: [spec.md](../spec.md)

## Recovery and clarity

- [x] First and second wrong attempts have a recoverable path [Spec §FR-003–FR-004]
- [x] The third failure has a clear blocked-state recovery path [Spec §FR-002, FR-005]
- [x] Email and safe return path are preserved across resend [Spec §FR-005]
- [x] Expired, replayed and invalid states are distinguished from a simple typo [Spec §FR-004, Edge Cases]

## Accessibility and surfaces

- [x] The six-slot input remains available on recoverable errors [Spec §FR-004]
- [x] The shared browser/WebView surface is explicitly in scope [Spec §Assumptions]
- [x] Account-linking is explicitly excluded to avoid changing merge-proof UX [Spec §Assumptions]
