# Privacy Requirements Checklist: macOS Real Bidirectional Passthrough

**Purpose**: Validate privacy, diagnostics, secrets, and egress requirement quality
**Created**: 2026-05-31
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [x] CHK001 Are recording, upload, transcription, MediaScribe, Langfuse, and server workflows explicitly out of scope? [Completeness, Spec §FR-005]
- [x] CHK002 Is hidden recording and hidden capture prohibited during readiness and passthrough? [Completeness, Spec §FR-006]
- [x] CHK003 Are diagnostics required to be metadata-only with forbidden content listed? [Completeness, Spec §FR-014]
- [x] CHK004 Are temporary stimulus/debug audio artifacts constrained to local, explicit, release-disabled behavior? [Completeness, Spec §FR-015]

## Requirement Clarity

- [x] CHK005 Is "no new external network egress" stated in both spec and plan? [Clarity, Spec §FR-018, Plan §Constraints]
- [x] CHK006 Are forbidden diagnostic fields precise enough for redaction tests? [Clarity, Contract diagnostics]
- [x] CHK007 Is browser evidence constrained to metadata-only fields? [Clarity, Contract browser-call]

## Consistency

- [x] CHK008 Do the spec, plan, and diagnostics contract agree that raw audio and transcript text are forbidden? [Consistency]
- [x] CHK009 Does the feature avoid promising deletion of artifacts it does not create? [Consistency, Constitutional Requirements]
- [x] CHK010 Does the app remain local-only when backend/network services are unavailable? [Consistency, Spec §FR-013]

## Acceptance Criteria Quality

- [x] CHK011 Is diagnostic safety measurable with tests/scans rather than subjective review only? [Measurability, Quickstart]
- [x] CHK012 Is the absence of recording/transcription observable in success criteria or validation steps? [Measurability, Spec §SC-001, §SC-002]
