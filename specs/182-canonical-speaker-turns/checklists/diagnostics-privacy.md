# Diagnostics and Privacy Checklist: Canonical Provider Speaker Turns

**Purpose**: Validate metadata-only operability without exposing meeting content.

**Created**: 2026-08-21

## Required evidence

- [x] CHK001 Are job/result/build/model/alignment provenance fields required only when available? [Clarity, Spec FR-017]
- [x] CHK002 Are raw/accepted counts, conflict, unknown/tiny, duplicate, conservation, and source hash explicitly required? [Completeness, Spec FR-017]
- [x] CHK003 Can diagnostics distinguish provider defects from GRAF projection defects? [Traceability, Spec FR-019]
- [x] CHK004 Are all states and reasons bounded rather than accepting provider/user text? [Security, Diagnostics contract]

## Forbidden content

- [x] CHK005 Are audio, transcript text, turn text, provider JSON, URLs, signed URLs, credentials, meeting titles, and participant names prohibited? [Privacy, Spec FR-018]
- [x] CHK006 Do committed tests use synthetic content and identifiers only? [Privacy, SC-010]
- [x] CHK007 Does the plan reuse the existing audit redaction boundary rather than create a new content-bearing store? [Consistency, Plan]
- [x] CHK008 Is source-result hash retained without logging the hashed payload? [Clarity, Diagnostics contract]

## Lifecycle

- [x] CHK009 Does diagnostic storage remain inside existing GRAF meeting/audit lifecycle? [Governance, Constitution IV]
- [x] CHK010 Does closeout require a forbidden-content scan before reporting completion? [Measurability, Quickstart]

## Notes

- All requirements are complete; no privacy exception is accepted.
