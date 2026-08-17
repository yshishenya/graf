# Implementation Plan: Meeting Review Continuity

**Branch**: `codex/158-meeting-review-continuity` | **Date**: 2026-08-17 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/158-meeting-review-continuity/spec.md`

## Summary

Keep the shared meeting-review surface continuous while adding only the
smallest UI state needed for speaker-lane discovery, bounded resizing, and
in-place speaker rename. Reuse the existing server-rendered speaker/timeline
markup, vanilla cabinet JavaScript, CSS, audio element, tab/hash model, and
authorization recovery helpers. Do not add persistence, a router, a second
audio element, analytics, or dependencies.

## Technical Context

**Language/Version**: Python 3.12 server templates plus browser JavaScript/CSS; macOS embedded shell consumes the same cabinet assets.

**Primary Dependencies**: Existing FastAPI/Jinja-style cabinet rendering, HTMX fragment lifecycle, vanilla DOM APIs, and existing test fixtures. No new dependency.

**Storage**: No new storage. Existing meeting/speaker data remains server-owned; timeline height is session-local DOM state.

**Testing**: `node --check`; focused `uv run` pytest through `apps/server/scripts/run_local_postgres_tests.sh`; `infra/scripts/ci-local.sh --fast`; manual browser/native visual checks.

**Risk / Validation Lane**: `high-risk-feature` for accessibility and user-facing review continuity. The slice changes shared web/embedded interaction, audio continuity, recovery behavior, and brand-distance UX, so it requires clarify, UX checklist, analyze, focused regression checks, and the fast repository gate.

**Release Gate**: `no deploy` for this isolated slice; production deployment and the combined release remain separate approval-gated work after all successor slices merge.

**Target Platform**: Desktop browser and embedded macOS GRAF review surface; supported narrow viewport, keyboard, reduced-motion, light/dark theme.

**Project Type**: Server-rendered web application with a native macOS embedded web shell.

**Performance Goals**: Resize uses one bounded pointer gesture and does not recreate playback or add polling; lane activation and tab switching retain existing immediate DOM behavior.

**Constraints**: Preserve the current `96px` minimum, never exceed natural complete rows or safe viewport, never replace the sole audio element on rename, preserve CSRF/access recovery, maintain existing hashes and avoid horizontal overflow.

**Scale/Scope**: Four related meeting-review behaviors in shared cabinet assets; synthetic speaker counts from one row through viewport-limited large sets.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Passes before design:

- Constitution VI: this is a high-risk UX/shared-surface change and follows the full Spec Kit sequence.
- Constitution II: no capture controls, consent, or recording source behavior is changed.
- Constitution III/IV: no AI, egress, retention, deletion, or persisted meeting data is changed; evidence remains metadata-only.
- Constitution V: no public macOS signing, updater, or package behavior is changed.
- Product UX gate: clean-room principles are recorded in `research.md`; no competitor layout/text/iconography is copied.

Passes after design:

- The design reuses existing native/browser primitives and shared paths, adds no dependencies or new router/state architecture, and defines focused accessibility and recovery checks in `quickstart.md`.

## Validation Plan

Follow `quickstart.md`: node syntax check, isolated focused server contracts/unit
tests for rendering and behavior harnesses, manual synthetic visual checks in
browser and native app, then `infra/scripts/ci-local.sh --fast`. The full CI,
production dry-run/execute, release candidate, and macOS notarization gates are
not part of this unmerged slice but remain mandatory for the final release
train.

## Project Structure

### Documentation (this feature)

```text
specs/158-meeting-review-continuity/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/meeting-review-continuity.md
├── checklists/requirements.md
├── checklists/ux.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/server/src/twobrain_rec_server/cabinet/
├── rendering.py
├── static/cabinet/
│   ├── cabinet.css
│   └── cabinet.js
└── templates/cabinet/pages/meeting_detail_content.html

apps/server/tests/
├── contract/test_cabinet_static_assets_contract.py
├── contract/test_recording_workflow_accessibility.py
└── unit/test_cabinet_web_shell.py
```

**Structure Decision**: Keep all behavior in the existing shared cabinet
rendering/static/template paths. Add contract assertions beside the existing
cabinet/playback/accessibility suites; no new application layer is justified.

## Research Outputs

- `research.md` records the bounded separator, in-place rename, sticky-tab, and clean-room UX decisions with dated public sources.
- `data-model.md` records only ephemeral view state and explicitly confirms no migration or persisted preference.
- `contracts/meeting-review-continuity.md` defines the shared web/embedded HTML/accessibility contract.
- `quickstart.md` defines focused, fast-lane, and manual visual validation.

## Implementation Phases

1. **Contract-first regression coverage**: extend synthetic rendering and static-asset harnesses for affordance visibility, resize bounds, rename states, and sticky tabs.
2. **Shared rendering**: add the timeline shell, resize separator, action hint, and stable speaker keys without changing playback data.
3. **Client continuity**: implement bounded resize and in-place rename label reconciliation with one-time initialization guards.
4. **Visual and accessibility polish**: add sticky tab styling, safe scroll margins, focus/pressed states, and reduced-motion-safe behavior.
5. **Review and validation**: run code/security/privacy/UX/brand-distance/Ponytail review, fix findings, run focused checks and `ci-local.sh --fast`, then perform manual synthetic browser/native checks.

## Complexity Tracking

No constitution violations. The simplest native DOM/CSS approach is sufficient;
no additional abstraction or dependency is justified.
