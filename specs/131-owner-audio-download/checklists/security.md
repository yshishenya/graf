# Security Checklist: Owner-default audio egress

**Feature**: `131-owner-audio-download`

- [x] CHK001 Does the requirement distinguish an implicit workspace/default policy from an explicit per-meeting denial? [Completeness, Spec §FR-003, §FR-009]
- [x] CHK002 Does the requirement preserve the existing meeting access, workspace membership, share capability, session, and owner checks? [Consistency, Spec §FR-005]
- [x] CHK003 Does the requirement state that owner-default applies only to audio and cannot broaden transcript, summary, or package egress? [Scope, Spec §FR-002]
- [x] CHK004 Does the requirement define a fail-closed result for unknown policy sources or invalid policy values? [Measurability, Spec §FR-005]
- [x] CHK005 Does the requirement preserve deletion/lifecycle and validated-artifact gates before any bytes or headers are returned? [Coverage, Spec §FR-005, §FR-007]
- [x] CHK006 Does the requirement keep browser and embedded clients behind the same server-mediated route without storage URLs, signed URLs, credentials, or object keys? [Boundary, Spec §FR-006]
- [x] CHK007 Does the requirement constrain successful, denied, and retry audit evidence to metadata-only fields? [Privacy, Spec §FR-008]
- [x] CHK008 Are synthetic-only validation and evidence rules explicit enough to prevent raw audio, transcript, secrets, and private paths from being committed? [Operational safety, Spec §SC-004]
