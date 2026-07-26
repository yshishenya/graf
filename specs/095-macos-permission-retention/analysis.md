# Specification Analysis Report: macOS Permission Retention And Relaunch Reliability

> Historical analysis. Local/self-signed findings are fixture evidence only;
> Feature 130 owns the current Developer ID-only public release path.

Feature: `095-macos-permission-retention`
Date: 2026-07-09

## Scope Reviewed

- [spec.md](./spec.md)
- [plan.md](./plan.md)
- [research.md](./research.md)
- [data-model.md](./data-model.md)
- [quickstart.md](./quickstart.md)
- [contracts/macos-app-identity-contract.md](./contracts/macos-app-identity-contract.md)
- [contracts/local-signing-runbook.md](./contracts/local-signing-runbook.md)
- [contracts/termination-relaunch-contract.md](./contracts/termination-relaunch-contract.md)
- [checklists/requirements.md](./checklists/requirements.md)
- [checklists/audio-capture.md](./checklists/audio-capture.md)
- [checklists/ux.md](./checklists/ux.md)
- [checklists/installer-signing.md](./checklists/installer-signing.md)
- [tasks.md](./tasks.md)
- [.specify/memory/constitution.md](../../.specify/memory/constitution.md)

## Findings

| ID | Category | Severity | Status | Location(s) | Finding | Resolution |
|----|----------|----------|--------|-------------|---------|------------|
| A1 | Scope / tracker | LOW | Resolved | `tasks.md`, repo remote | The repository remote is GitHub and `tasks.md` has executable implementation tasks, so tracker sync is required before implementation. | GitHub issues #2979-#3018 were created for T001-T040 using the repository canon before implementation continued. |

No unresolved critical, high, medium, or low findings remain.

## Coverage Summary

| Requirement Key | Has Task? | Task IDs | Notes |
|-----------------|-----------|----------|-------|
| FR-001 stable bundle id | Yes | T007, T015, T019 | App identity validation and evidence cover `pro.2brain.graf`. |
| FR-002 non-ad-hoc signature | Yes | T006, T008, T009, T016, T019 | Signing policy tests and build script tasks cover this. |
| FR-003 free local self-signed path | Yes | T008, T010, T016, T027 | Explicit local flag and README runbook cover the no-paid path. |
| FR-004 distinguish signing modes | Yes | T006, T010, T025, T026, T028 | Tests/docs cover local, Apple Development, Developer ID, and public release boundaries. |
| FR-005 metadata-only identity evidence | Yes | T011, T015, T019, T039 | Evidence model and quickstart require bounded fields. |
| FR-006 preserve permissions after same-identity reinstall | Yes | T013-T019, T036 | US1 tasks and quickstart own reinstall validation. |
| FR-007 fail closed on drift/ad-hoc | Yes | T006, T009, T015, T033 | Signing drift and ad-hoc failure are explicit. |
| FR-008 suppress onboarding when granted | Yes | T014, T018, T033 | US1 and US4 cover ready-state quiet launch. |
| FR-009 no TCC bypass or reset | Yes | T017, T031, T033, T035 | Quickstart and tests preserve user-granted flow. |
| FR-010 dismiss modals on termination | Yes | T020-T024 | US2 covers permission and AppKit sheets. |
| FR-011 reply within 10 seconds | Yes | T024, T036, T039 | Contract and quickstart cover the bound. |
| FR-012 HAL driver excluded | Yes | T007, T035, T038 | Installer and audio checklists plus tests cover no-driver scope. |
| FR-013 preserve Record/Stop and fail-closed capture | Yes | T003, T030-T033, T038 | Permission UX work avoids capture behavior changes. |
| FR-014 metadata-only diagnostics | Yes | T005, T011, T019, T024, T033, T035, T039 | Evidence and forbidden-content scans cover this. |
| FR-015 changelog/release boundary | Yes | T029, T039 | Local-only signing boundary must be recorded. |
| SC-001 two reinstall cycles retain permissions | Yes | T016-T019, T036 | Quickstart scenario covers this. |
| SC-002 non-ad-hoc/stable DR evidence | Yes | T006, T008-T011, T015, T019 | Signing evidence covers this. |
| SC-003 quit under modal within 10 seconds | Yes | T020-T024, T036 | US2 covers this. |
| SC-004 focused macOS tests pass | Yes | T034 | Focused test command is in quickstart. |
| SC-005 quickstart and forbidden scan pass | Yes | T035-T036 | Static and manual scenarios are explicit. |
| SC-006 full local CI passes | Yes | T037 | Repository gate is explicit. |

## Constitution Alignment

| Principle | Result | Notes |
|-----------|--------|-------|
| Capture-first MVP integrity | PASS | The slice supports microphone/system-audio permission prerequisites without changing capture, upload, transcription, or HAL driver behavior. |
| Visible consent and user control | PASS | macOS permissions remain explicit user decisions; no hidden grants or TCC mutation are allowed. |
| Data boundary and secret discipline | PASS | Evidence is metadata-only and forbids keys, credentials, audio, transcripts, and private meeting content. |
| Deletion truth and lifecycle accounting | PASS | No meeting lifecycle/deletion boundary is introduced. |
| Spec-driven delivery with testable gates | PASS | Spec, clarify notes, plan, research, data model, contracts, checklists, tasks, quickstart, and this analysis are present. |
| UI and brand distance | PASS | Native permission UX is adjusted only for truth and relaunch reliability; no public brand surface changes. |
| Ponytail form | PASS | Plan reuses existing Swift/AppKit lifecycle, installer scripts, and tests. |

## Unmapped Tasks

No product implementation tasks are unmapped. Setup tasks T001-T005 and polish
tasks T034-T040 are cross-cutting by design.

## Validation Performed

```sh
.specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks
rg -n "NEEDS CLARIFICATION|\\[FEATURE NAME\\]|\\[DATE\\]|\\[###|TODO|TBD|\\$ARGUMENTS" specs/095-macos-permission-retention AGENTS.md
python3 - <<'PY'
from pathlib import Path
import re
text = Path('specs/095-macos-permission-retention/tasks.md').read_text()
ids = re.findall(r'- \\[ \\] (T\\d{3})', text)
assert len(ids) == 40
assert len(set(ids)) == 40
assert ids[0] == 'T001' and ids[-1] == 'T040'
assert not [line for line in text.splitlines() if line.startswith('- [ ] T') and '`' not in line]
PY
git diff --check
```

The only stale-marker matches are the literal scan command in
[quickstart.md](./quickstart.md) and checklist wording in
[checklists/requirements.md](./checklists/requirements.md); they are not
unresolved placeholders.

## Metrics

- Total functional requirements: 15
- Total measurable success criteria: 6
- Total tasks: 40
- Requirements with task coverage: 21/21
- Coverage: 100%
- Ambiguity count: 0 unresolved
- Duplication count: 0
- Critical issues count: 0

## Next Action

Proceed with `$speckit-implement`. Before marking any task complete, reconcile
the existing local termination hotfix with T020-T024 and collect quickstart
evidence.
