# Implementation Plan: Meeting List Presentation Contract

**Branch**: `122-meeting-list-presentation-contract` | **Date**: 2026-07-21 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/122-meeting-list-presentation-contract/spec.md`

## Summary

Replace the meeting list's accumulated pipeline labels with one deterministic, user-facing presentation state while preserving the existing server-owned cabinet, HTMX refresh, access policy, upload, playback, calendar, and bounded-deletion behavior. The implementation adds a small presentation-only projection in the current cabinet view-model/rendering boundary, makes the meeting row's primary action unambiguously open the result, keeps selection explicit, defaults sorting to trusted meeting start time, and aligns toolbar, empty, recovery, live-region, responsive, keyboard, and assistive-technology behavior with [visual-target.md](./visual-target.md). No Figma artifact, new API, database change, native capture change, dependency, or Krisp-like product capability is introduced.

## Technical Context

**Language/Version**: Python 3.13 for the server; HTML/Jinja, CSS, and the existing dependency-free cabinet JavaScript. The Swift 6 macOS shell is a non-regression boundary only and is not expected to change.

**Primary Dependencies**: FastAPI, Pydantic, SQLAlchemy, Jinja 3.1, the repository-owned HTMX asset, existing cabinet template/icon helpers, and vanilla JavaScript/CSS. No new runtime dependency.

**Storage**: Existing PostgreSQL meeting, upload, processing, calendar-context, playback, access, and deletion records remain authoritative. No table, migration, preference, local manifest, or persisted title change.

**Testing**: pytest unit, contract, and integration suites; existing HTML/CSS/JavaScript contract assertions; synthetic browser and accessibility inspection for browser and embedded surfaces; `infra/scripts/ci-local.sh` as the repository gate.

**Risk / Validation Lane**: High-risk feature. The slice changes a primary user workflow, accessible names/focus, selection versus navigation, status truth, and destructive-action feedback. It therefore requires full Spec Kit clarify, plan, UX checklist, tasks, clean analyze, GitHub issue sync, tests-first implementation, synthetic visual/accessibility evidence, and the repository gate.

**Release Gate**: No deploy. This lane ends with validated uncommitted implementation code and documentation checkpoint commits. A product-code commit, PR, release, installer replacement, deploy, and production rollout require separate user approval.

**Target Platform**: Authenticated browser cabinet and the same server-rendered surface embedded in the macOS 14+ app. Native capture controls remain independent and unchanged.

**Project Type**: Server-rendered web application embedded in a native macOS desktop shell.

**Performance Goals**: Preserve the 150 ms refinement debounce, current 50-row default page bound, one list request per refinement, one-second polling only for already-active states, and HTMX fragment replacement without a full page/app reload. Add no query, request, polling loop, or client framework.

**Constraints**: One compact status per row; ready-state silence; no invented progress; explicit open/select/delete semantics; no private metadata in unavailable/session states or evidence; 32×32 CSS-pixel contextual targets; visible focus; no horizontal scroll at `1040×680`; Reduce Motion support; existing auth, access, upload, playback, calendar, deletion, and native capture authority must remain intact.

**Scale/Scope**: One meeting-list route rendered for browser and embedded variants; one toolbar; one row pattern; one client-side selection mode; 11 canonical row states and 16 evidence classes. Meeting detail, transcript, notes, playback timeline, native capture rail, onboarding, settings, new organization features, and production deployment are outside scope.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Before Phase 0: PASS

- **Capture-first platform integrity**: PASS. Only the server-owned post-meeting list changes; native recording, permission, local-custody, and one-action Stop paths remain untouched.
- **Visible consent and control**: PASS. The embedded cabinet cannot start, stop, or obscure native capture authority.
- **Data and egress boundaries**: PASS. The projection consumes existing safe list fields and adds no storage, credential, raw-content, MediaScribe, Langfuse, or external egress behavior.
- **Access and privacy**: PASS. Existing access filtering remains upstream of rendering; session/access recovery copy is metadata-free; evidence is synthetic or redacted.
- **Deletion truth**: PASS. Existing CSRF, authorization, confirmation, bounded erasure copy, and request semantics are reused; only feedback placement and focus reconciliation change.
- **Spec-driven delivery**: PASS. The feature follows clarify → plan → checklist → tasks → analyze → taskstoissues → implement.
- **Accessibility and localization**: PASS with explicit Russian copy, native HTML controls, ordered content, keyboard/VoiceOver, focus, live-region, contrast, target-size, long-text, and responsive contracts.
- **Brand distance**: PASS. Krisp is used only as clean-room evidence for hierarchy and progressive disclosure; GRAF tokens, icons, wording, and supported behavior remain original.
- **Ponytail form**: PASS. Reuse current schema, query, template, HTMX, JavaScript selection/deletion flow, CSS tokens, and tests. Add one small presentation value object/helper rather than a new layer, API, dependency, or framework.

### After Phase 1: PASS

The Phase 1 artifacts keep all authority in existing owners. [data-model.md](./data-model.md) defines only an immutable presentation value object; [contracts/meeting-list-presentation.md](./contracts/meeting-list-presentation.md) makes precedence total and preserves detail truth; [quickstart.md](./quickstart.md) verifies browser/embedded parity, privacy, deletion, accessibility, and repository gates. No constitution exception or complexity waiver is required.

## Validation Plan

1. Capture a clean baseline with the focused server suites named in [quickstart.md](./quickstart.md).
2. Add failing view-model tests for the total status precedence, ready-state silence, exact row copy, generated-title neutrality, selected sort timestamp, and refinement vocabulary.
3. Add failing rendering/integration tests for one semantic open action, explicit checkbox selection, stable contextual controls, batch toolbar disclosure, feedback placement, result count, empty/recovery states, and browser/embedded parity.
4. Add or refine static JavaScript/CSS contracts for `Enter` to open, `Space` to select, post-refresh selection/focus reconciliation, non-hover access, 32×32 targets, visible focus, minimum-width layout, increased contrast, and Reduce Motion.
5. Run the focused pytest command from `apps/server`, then the privacy/deletion/cabinet contract suites called out in the quickstart.
6. Exercise all 16 synthetic evidence classes at `1280×760` and layout-sensitive classes at `1040×680`; inspect keyboard order and the accessibility tree without real meeting/account data.
7. Confirm zero copied Krisp strings, assets, icons, palette, composition, or unsupported features.
8. Run `infra/scripts/ci-local.sh`. Do not deploy or replace the installed app in this lane.

## Project Structure

### Documentation (this feature)

```text
specs/122-meeting-list-presentation-contract/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── visual-target.md
├── quickstart.md
├── contracts/
│   └── meeting-list-presentation.md
├── checklists/
│   ├── requirements.md
│   └── ux.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/server/
├── src/twobrain_rec_server/cabinet/
│   ├── queries.py
│   ├── rendering.py
│   ├── view_models.py
│   ├── web_routes/
│   │   ├── browser.py
│   │   ├── desktop.py
│   │   └── support.py
│   ├── static/cabinet/
│   │   ├── cabinet.css
│   │   └── cabinet.js
│   └── templates/cabinet/pages/
│       └── meeting_list_content.html
└── tests/
    ├── contract/
    ├── integration/
    └── unit/

CHANGELOG.md
AGENTS.md
```

**Structure Decision**: Keep query truth in `queries.py`, derive compact user presentation in `view_models.py`, render it in the existing Jinja/Python boundary, and adjust only the existing cabinet template, JavaScript, and CSS needed for hierarchy and interaction. Browser and desktop routes share the same projection. No native file, public API schema, database model, or new frontend component system is planned.

## Complexity Tracking

No constitution violations.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |

## Ponytail Plan

- Remove duplicate labels and ordinary-state tokens before adding markup.
- Reuse the existing `MeetingListItem`, safe title/date/duration helpers, HTMX form, selection set, delete dialog, icon macros, and cabinet tokens.
- Add one immutable presentation projection only because total precedence, copy, accessible description, and time semantics must be testable independently of HTML.
- Prefer native `<a>`, `<input type="checkbox">`, `<button>`, `<select>`, ordered-list semantics, and live regions over custom ARIA widgets.
- Keep detailed calendar/playback/failure truth on the detail/recovery surfaces; compact-list silence must not delete source data.
- Add no design framework, state store, endpoint, persistence, background job, organization feature, or compatibility adapter.
