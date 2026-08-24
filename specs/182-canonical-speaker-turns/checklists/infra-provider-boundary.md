# Infrastructure and Provider Boundary Checklist: Canonical Provider Speaker Turns

**Purpose**: Keep the change GRAF-only and prove it does not alter or deploy MediaScribe.

**Created**: 2026-08-21

## Scope boundary

- [x] CHK001 Is external MediaScribe code, configuration, model, runtime, and deployment explicitly out of scope? [Boundary, Spec FR-021]
- [x] CHK002 Is the GRAF-owned adapter boundary distinguished from the external provider service? [Clarity, Plan]
- [x] CHK003 Does the design avoid new provider calls, re-diarization, or retries? [Scope, Spec Out of Scope]
- [x] CHK004 Does the canonical path begin only after receipt of a provider result? [Traceability, Constitution check]

## Storage and operations

- [x] CHK005 Is existing PostgreSQL storage sufficient without an unproven migration? [Simplicity, Data model]
- [x] CHK006 Are new diagnostics restricted to the existing allowlisted audit path? [Security, Diagnostics contract]
- [x] CHK007 Is production deployment forbidden in this stage? [Release gate, Plan]
- [x] CHK008 Is commit forbidden until separate user approval? [Release gate, AGENTS.md]
- [x] CHK009 Does validation include repository tests but exclude provider/runtime deployment checks? [Scope, Quickstart]
- [x] CHK010 Does closeout explicitly report zero MediaScribe changes/deployments? [Measurability, SC-012]

## Notes

- All requirements are complete; release/deploy approval is intentionally absent.
