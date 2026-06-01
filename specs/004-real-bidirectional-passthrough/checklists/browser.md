# Browser Requirements Checklist: macOS Real Bidirectional Passthrough

**Purpose**: Validate browser meeting evidence requirement quality
**Created**: 2026-05-31
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [x] CHK001 Are Chrome, Opera, Yandex Browser, and Yandex Telemost-in-browser all listed as required evidence targets? [Completeness, Spec §FR-012]
- [x] CHK002 Are both selected meeting devices required in browser evidence? [Completeness, Contract browser-call]
- [x] CHK003 Are local speech usability and remote audio usability both required? [Completeness, Contract browser-call]
- [x] CHK004 Are pass, blocked, and not accepted states defined? [Completeness, Contract browser-call]

## Requirement Clarity

- [x] CHK005 Is blocked/not accepted evidence required to include a concrete reason? [Clarity, Contract browser-call]
- [x] CHK006 Is browser evidence explicitly metadata-only? [Clarity, Spec §FR-014]
- [x] CHK007 Is stale browser device ID behavior covered after app/driver/coreaudiod restart? [Coverage, Edge Cases]

## Acceptance Criteria Quality

- [x] CHK008 Can every browser target be objectively recorded as passed or not accepted? [Measurability, Spec §SC-007]
- [x] CHK009 Does browser validation avoid starting recording or transcript generation? [Consistency, Contract browser-call]
- [x] CHK010 Is remote-to-mic loopback checked as part of browser pass criteria? [Measurability, Contract browser-call]
