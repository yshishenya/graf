# Driver Boundary Checklist: Server Ingest Foundation

**Purpose**: Validate that 012 requirements preserve macOS driver-first capture, visible capture, local recording truth, and clean separation from desktop implementation work.
**Created**: 2026-06-04
**Feature**: [spec.md](../spec.md)

**Note**: 012 is backend ingest only. This checklist tests whether requirements protect driver/capture boundaries; it is not a driver QA checklist.

## Requirement Completeness

- [ ] CHK001 Are requirements explicit that 012 starts only after a finalized local recording artifact exists and does not define capture start/stop behavior? [Completeness, Spec §Product Scope Boundary/FR-025]
- [ ] CHK002 Are out-of-scope declarations complete for production desktop uploader, local upload queue UI, automatic desktop retry loop, assisted auto-recording, and capture-critical UI? [Completeness, Spec §FR-018/FR-029]
- [ ] CHK003 Are requirements complete enough to preserve local artifact source-of-truth until later desktop uploader slice defines purge/retry behavior? [Completeness, Spec §FR-026/Assumptions]

## Requirement Clarity

- [ ] CHK004 Is the distinction between local capture truth and server ingest status clearly specified? [Clarity, Spec §FR-025]
- [ ] CHK005 Are local microphone and incoming speaker roles specified independently of file-name guessing and consistent with the accepted artifact contract? [Clarity, Spec §FR-007/FR-008]
- [ ] CHK006 Is "desktop-like client" clearly framed as a contract-test client for 012 rather than production macOS uploader implementation? [Clarity, Spec §FR-001/FR-029]

## Requirement Consistency

- [ ] CHK007 Are driver-first and visible-capture constitution gates consistently preserved by plan and spec without introducing a no-driver fallback or remote invisible capture path? [Consistency, Constitution §I/II, Plan §Constitution Check]
- [ ] CHK008 Are assisted detect-and-ask and auto-recording consistently deferred outside 012? [Consistency, Spec §FR-018/Assumptions]
- [ ] CHK009 Are desktop uploader responsibilities consistently assigned to 014 rather than leaking into 012 requirements or plan tasks? [Consistency, Spec §Downstream Slice Guardrail, Plan §Summary]

## Edge Case Coverage

- [ ] CHK010 Are degraded, failed, legacy, and non-ready local packages represented without requiring 012 to reinterpret how local capture happened? [Coverage, Spec §Edge Cases/FR-025]
- [ ] CHK011 Are wrong-role, empty, truncated, corrupt, and checksum-mismatch track cases covered as ingest validation requirements rather than driver repair behavior? [Coverage, Spec §Edge Cases/FR-016]
- [ ] CHK012 Are future local purge and deletion coordination responsibilities intentionally deferred while preserving enough lifecycle metadata for later truth reporting? [Coverage, Spec §FR-024/Assumptions]

## Acceptance Criteria Quality

- [ ] CHK013 Are acceptance criteria measurable enough to show no transcript, notes, dashboard, deletion execution, assisted auto-recording, or desktop uploader behavior is observable in 012? [Measurability, Spec §SC-012]
- [ ] CHK014 Are capture-boundary requirements traceable enough that task generation can avoid modifying `apps/macos` except where explicitly justified later? [Traceability, Plan §Project Structure]

## Notes

- This checklist should stay small because 012 does not implement macOS driver or uploader code.
