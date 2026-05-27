# Implementation Plan: [FEATURE]

**Branch**: `[###-feature-name]` | **Date**: [DATE] | **Spec**: [link]

**Input**: Feature specification from `/specs/[###-feature-name]/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

[Extract from feature spec: primary requirement + technical approach from research]

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: [e.g., Python 3.11, Swift 5.9, Rust 1.75 or NEEDS CLARIFICATION]

**Primary Dependencies**: [e.g., FastAPI, UIKit, LLVM or NEEDS CLARIFICATION]

**Storage**: [if applicable, e.g., PostgreSQL, CoreData, files or N/A]

**Testing**: [e.g., pytest, XCTest, cargo test or NEEDS CLARIFICATION]

**Target Platform**: [e.g., Linux server, iOS 15+, WASM or NEEDS CLARIFICATION]

**Project Type**: [e.g., library/cli/web-service/mobile-app/compiler/desktop-app or NEEDS CLARIFICATION]

**Performance Goals**: [domain-specific, e.g., 1000 req/s, 10k lines/sec, 60 fps or NEEDS CLARIFICATION]

**Constraints**: [domain-specific, e.g., <200ms p95, <100MB memory, offline-capable or NEEDS CLARIFICATION]

**Scale/Scope**: [domain-specific, e.g., 10k users, 1M LOC, 50 screens or NEEDS CLARIFICATION]

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Answer every gate below with PASS, FAIL, or N/A. Any FAIL requires correction
before implementation planning continues, unless explicitly justified in
Complexity Tracking and approved by the user.

### 2brain Rec Constitutional Gates

- **Driver-first capture integrity**: If the feature touches capture, routing,
  recording, buffering, installer, permissions, or driver UX, does it preserve
  the macOS driver-first MVP, separate mic/speaker tracks, no loopback, local
  passthrough, degraded states, and Phase 0 driver decision gates?
- **Visible consent and control**: If the feature touches recording or
  transcription start/stop, does it preserve visible active-capture indication,
  one-action stop, manual start/stop, policy-gated assisted auto-start, and no
  invisible/silent recording path?
- **Data boundary and secrets**: If the feature touches upload, processing,
  STT, LLM, observability, integrations, auth, or deployment, does it keep
  credentials server-side, document egress, prevent secret/log leakage, and keep
  Langfuse metadata-only by default?
- **Deletion truth and lifecycle accounting**: If the feature creates,
  transforms, exports, observes, or caches meeting content, does it register
  artifacts for retention/deletion and avoid promises beyond 2brain Rec control?
- **Spec-driven delivery**: Is the feature specified, clarified where needed,
  planned, checklist-gated for high risk, taskable by independent user story,
  and analyzable before implementation?
- **Brand-distance and accessibility**: If the feature changes UI, does it
  require original 2brain Rec design, accessibility states, localization safety,
  and brand-distance review?
- **Operational readiness**: If the feature touches Docker/deployment/storage,
  does it cover secrets, health checks, backups, restore, rollback, log
  redaction, timeout/failure behavior, and disk-full behavior?

**Initial Gate Result**: [PASS/FAIL with notes]
**Post-Design Gate Result**: [PASS/FAIL with notes]

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```text
# [REMOVE IF UNUSED] Option 1: Single project (DEFAULT)
src/
├── models/
├── services/
├── cli/
└── lib/

tests/
├── contract/
├── integration/
└── unit/

# [REMOVE IF UNUSED] Option 2: Web application (when "frontend" + "backend" detected)
backend/
├── src/
│   ├── models/
│   ├── services/
│   └── api/
└── tests/

frontend/
├── src/
│   ├── components/
│   ├── pages/
│   └── services/
└── tests/

# [REMOVE IF UNUSED] Option 3: Mobile + API (when "iOS/Android" detected)
api/
└── [same as backend above]

ios/ or android/
└── [platform-specific structure: feature modules, UI flows, platform tests]
```

**Structure Decision**: [Document the selected structure and reference the real
directories captured above]

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
