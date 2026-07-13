# UX Requirements Quality Checklist: Essential Interface Polish

**Purpose**: Validate that feature 104 requirements are complete, clear, measurable, and consistent for information hierarchy, capture trust, accessibility, localization, responsive layout, debug removal, and clean-room brand distance.
**Created**: 2026-07-13
**Feature**: [spec.md](../spec.md)

**Depth**: Formal high-risk pre-implementation gate
**Audience / timing**: Product, design, accessibility, native, and server reviewers before task generation and again before PR closeout

## Requirement Completeness

- [x] CHK001 Are requirements present for every visible main-window cluster: navigation, header/tools, calendar, meeting rows, selection, native rail, expanded capture panel, and active titlebar HUD? [Completeness, Spec §FR-001–FR-004, Research §Element-by-element Inventory]
- [x] CHK002 Are every current element and its keep/simplify/merge/move/remove disposition documented with a user or product-gate reason? [Completeness, Spec §FR-002, Research §Element-by-element Inventory]
- [x] CHK003 Are requirements defined for the ordinary, selected, searched, filtered, sorted, calendar-empty, first-run, active-recording, local-custody, cabinet-unavailable, and actionable-failure states? [Coverage, Spec §FR-023, Contract `main-window-ui.md` §Screen States]
- [x] CHK004 Are working and non-working navigation destinations distinguished so future placeholders cannot remain visible by accident? [Completeness, Spec §FR-025, Research §Decision 2]
- [x] CHK005 Are the single-search, filter, sort, active-state, and one-action reset requirements all specified? [Completeness, Spec §FR-026, Contract `meeting-list-presentation.md` §Query Controls]
- [x] CHK006 Are contextual row selection, bulk selection, destructive confirmation, and unavailable-action removal requirements all defined? [Completeness, Spec §FR-028, Contract `meeting-list-presentation.md` §Row Composition/Destruction]
- [x] CHK007 Are human title fallback, filename cleanup, duration localization, terminal status, active progress, and local-custody wording all specified? [Completeness, Spec §FR-029–FR-030, Contract `meeting-list-presentation.md` §Title/Duration/Status]
- [x] CHK008 Are native rail, titlebar HUD, inspector disclosure, permission recovery, recording parameters, custody recovery, meters, and support-entry requirements all defined? [Completeness, Spec §FR-008–FR-011/FR-031, Contract `capture-surface-ui.md`]

## Requirement Clarity

- [x] CHK009 Is “главное действие” made concrete for idle, recording, paused, stopping, permission-blocked, local-only, and failed capture states? [Clarity, Spec §FR-004/FR-006, Data Model §CaptureSurfacePresentation]
- [x] CHK010 Is “без debug-информации” bounded by an explicit list of forbidden ordinary-screen content and an explicit keep-boundary for metadata-only diagnostics/redaction? [Clarity, Spec §FR-005/FR-007/FR-020, Contract `capture-surface-ui.md` §Hidden From Ordinary UI]
- [x] CHK011 Is “компактный” quantified through sidebar, rail, inspector, control, row, typography, radius, and spacing ranges rather than subjective language alone? [Clarity, Plan §Performance Goals, Contract `main-window-ui.md` §Layout/Typography]
- [x] CHK012 Is the difference between an actionable problem and a technical/internal warning explicitly defined for inspector expansion and support visibility? [Clarity, Data Model §CaptureSurfacePresentation, Contract `capture-surface-ui.md` §Expanded Panel]
- [x] CHK013 Are the recognized generated-title categories and presentation-only mutation boundary explicit enough to avoid rewriting meaningful user titles? [Clarity, Data Model §MeetingListItemPresentation, Contract `meeting-list-presentation.md` §Title Presentation]
- [x] CHK014 Is active progress distinguished from terminal completion with an objective `is_active` and meaningful-total condition? [Clarity, Spec §FR-030, Data Model §MeetingListItemPresentation]
- [x] CHK015 Is the responsive boundary stated relative to the supported native minimum window and embedded viewport rather than an unexplained breakpoint? [Clarity, Contract `main-window-ui.md` §Layout]

## Requirement Consistency

- [x] CHK016 Are direct rail Start/Stop, stable workspace width, manual/actionable inspector expansion, and persistent titlebar Stop mutually consistent across spec, plan, data model, and contracts? [Consistency, Spec Clarifications/FR-008/FR-031, Data Model §CaptureSurfacePresentation, Contract `capture-surface-ui.md`]
- [x] CHK017 Are server-owned meeting content and native-owned capture controls consistently separated without duplicate authority? [Consistency, Spec §FR-010–FR-011, Data Model §Relationship And Ownership]
- [x] CHK018 Are debug-removal requirements consistent with the prohibition on deleting diagnostic, redaction, audit, or support-safety infrastructure? [Consistency, Spec §FR-005/FR-020, Research §Decision 7]
- [x] CHK019 Are deletion simplification requirements consistent with existing bounded confirmation and truthful erasure limits? [Consistency, Spec §FR-017–FR-021, Contract `meeting-list-presentation.md` §Destruction]
- [x] CHK020 Are clean-room constraints consistent with the requirement to learn only general hierarchy/progressive-disclosure principles from Krisp? [Consistency, Spec §FR-003/FR-013, Research §Decision 1]
- [x] CHK021 Is the supported dark-theme scope consistent across scenarios, responsive/accessibility requirements, and the explicit light-theme exclusion? [Consistency, Spec US4/FR-016/Scope Boundaries]

## Acceptance Criteria Quality

- [x] CHK022 Can absence of debug identifiers, disabled placeholders, duplicate search, premature bulk actions, generated titles, and terminal 100% meters be counted objectively? [Measurability, Spec §SC-002/SC-010–SC-012]
- [x] CHK023 Can five-second comprehension and one-action Stop be evaluated consistently across the defined state matrix? [Measurability, Spec §SC-003, Data Model §CaptureSurfacePresentation]
- [x] CHK024 Are responsive acceptance criteria tied to named window sizes and observable overlap/scroll/critical-action failures? [Measurability, Spec §SC-006, Plan §Validation Plan, Quickstart §Live Main-window Matrix]
- [x] CHK025 Are keyboard, VoiceOver, accessible-name, focus-order, and focus-visibility outcomes defined for all critical interactions? [Measurability, Spec §SC-007/FR-015, Contract `main-window-ui.md` §Accessibility]
- [x] CHK026 Is brand-distance success measurable through zero copied strings, assets, icon treatments, proprietary flows, and recognizable branded composition? [Measurability, Spec §SC-008, Quickstart §Visual Comparison And Brand Distance]

## Scenario And Edge-case Coverage

- [x] CHK027 Are exception and recovery requirements defined for permission denial, cabinet offline/auth failure, local-only custody, failed upload, and support-report failure without losing local recording control? [Coverage, Spec Edge Cases/FR-006–FR-011, Contract `capture-surface-ui.md`]
- [x] CHK028 Are empty-list and no-results requirements distinguished so first-run guidance is not incorrectly shown for a filtered empty result? [Coverage, Contract `meeting-list-presentation.md` §Empty States]
- [x] CHK029 Are long Russian text, increased text size/zoom, minimum window, increased contrast, and missing-wordmark fallback requirements documented? [Coverage, Spec Edge Cases/FR-016, Contract `main-window-ui.md` §Typography/Visual Tokens]
- [x] CHK030 Are Reduce Motion requirements specified so meaning, focus, and availability do not depend on inspector/list animation? [Coverage, Spec §FR-034, Contract `main-window-ui.md` §Interaction Contract]
- [x] CHK031 Are hover-only selection/delete affordances paired with keyboard-focus and active-selection requirements? [Coverage, Spec §FR-015/FR-028, Contract `main-window-ui.md` §Accessibility]
- [x] CHK032 Are concurrent active-recording plus permission/custody/connectivity problem priorities defined so Stop is never displaced? [Coverage, Spec Edge Cases/FR-008–FR-011, Contract `capture-surface-ui.md` §Accessibility And Failure Rules]

## Dependencies, Boundaries, And Evidence

- [x] CHK033 Are the no-schema/no-API/no-new-dependency assumptions and presentation-only boundaries explicit? [Assumption, Plan §Technical Context, Data Model §Migration]
- [x] CHK034 Are official macOS/WCAG control-size, contrast, focus, and semantic-control references tied to requirements rather than treated as decorative research? [Dependency, Research §Decision 8, Plan §Validation Plan]
- [x] CHK035 Are private-content exclusions defined for screenshots, specs, diagnostics, and validation evidence? [Completeness, Spec §FR-024/SC-009, Contract `main-window-ui.md` §Privacy And Evidence]
- [x] CHK036 Are implementation, release, deployment, full light-theme, new feature, and broad-refactor exclusions explicit enough to prevent scope drift? [Boundary, Spec §Scope Boundaries, Plan §Release Gate/Scale]

## Notes

- All 36 requirement-quality checks passed on 2026-07-13 after the supplied Krisp/GRAF states and current code paths were incorporated.
- The checklist validates written requirements, not implementation behavior. Implementation proof is defined separately in `quickstart.md`.
- Optional before/after checklist commit hooks were not executed because no commit approval was given.

## Remediation Recheck — 2026-07-13

- [x] CHK037 Is account-plan/trial presentation explicitly prohibited when the main-window projection has no authoritative billing source? [Truthfulness, Spec Clarifications/FR-025, Research §Decision 2]
- [x] CHK038 Is the calendar boundary unambiguous: no main-window upcoming region without an authoritative event projection, settings remain reachable, and future event presentation requires a separate feature? [Clarity, Spec §FR-032/Scope Boundaries, Contract `main-window-ui.md` §Visible Elements By Default]
- [x] CHK039 Are generated-title rules complete and consistent for capture/upload records both with and without trustworthy local date/time? [Consistency, Spec §FR-029, Data Model §MeetingListItemPresentation, Contract `meeting-list-presentation.md` §Title Presentation]
- [x] CHK040 Are all 16 required state classes named consistently across requirements, visual evidence, validation, and acceptance criteria? [Coverage, Spec §FR-023/SC-009, Visual Target §State Evidence Matrix, Quickstart §Live Main-window Matrix]
- [x] CHK041 Is the pre-build visual source identified by a stable project/screen ID and bounded to hierarchy, geometry, responsive behavior, and semantics rather than copied prototype code? [Traceability, Spec §FR-035, Plan §Validation Plan, Visual Target §Source Of Truth]
- [x] CHK042 Are minimum-window requirements explicit about sidebar/toolbar collapse, preserved date/upload/capture controls, zero horizontal overflow, and exact accessible names? [Clarity, Spec §FR-015–FR-016/SC-006–SC-007, Contract `main-window-ui.md` §Layout]
- [x] CHK043 Is scope limited to the main-window session/permission/recovery presentation and working settings destination while separate settings, onboarding, and menu/status windows are excluded? [Boundary, Spec §Scope Boundaries, Plan §Scale/Scope]
- [x] CHK044 Are performance expectations expressed as observable non-regression constraints on existing debounce, list replacement/limit, polling, network, capture-thread, and background work rather than subjective smoothness? [Measurability, Plan §Performance / Non-regression Goals]
- [x] CHK045 Does the element inventory classify system-owned traffic-light controls and the `GRAF` window title in addition to server/native product elements? [Completeness, Spec §SC-001, Research §Element-by-element Inventory]
- [x] CHK046 Are ordinary native-rail requirements consistent about retaining only readiness/attention, direct Start/Stop, contextual custody, and intentional disclosure while moving settings detail out of the idle rail? [Consistency, Research §Decision 6/Inventory, Contract `capture-surface-ui.md` §Compact Rail]
- [x] CHK047 Is screenshot/evidence coverage measurable for every state class and both target sizes where layout changes, while still excluding private content? [Acceptance Criteria, Spec §FR-024/SC-009, Visual Target §State Evidence Matrix]
- [x] CHK048 Are clean-room and dependency boundaries explicit enough to prevent Stitch CDN/code, Krisp expression, new routes, billing copy, or invented calendar data from entering production? [Boundary, Spec §FR-013/FR-032/FR-035, Visual Target §Implementation Boundary]

## Remediation Notes

- CHK001 and CHK003 preserve the initial draft's calendar terminology because this checklist is append-only. CHK038 is the current requirement-quality gate and confirms the approved removal of the unsupported main-window calendar region.
- All 12 remediation checks passed after cross-reading the specification, plan, research, data model, contracts, visual target, quickstart, and tasks.
- The optional before/after checklist commit hooks remain unexecuted because the user has not approved a commit.

## Final Visual-contract Recheck — 2026-07-13

- [x] CHK049 Does the selected ordinary-state target omit selection and delete controls both visually and from the accessibility tree until hover, keyboard focus, or explicit selection intent? [Accessibility, Visual Target §Accessibility Target, Contract `meeting-list-presentation.md` §Row Composition]
- [x] CHK050 Do final search, sort, duration, status, upload, readiness, recording, and disclosure names match the written contracts at both target widths? [Consistency, Quickstart §Approved Pre-build Visual Target, Contracts]
- [x] CHK051 Does the embedded no-meetings requirement avoid asking a user inside the installed macOS app to download/install it again or complete unrelated calendar onboarding? [Relevance, Spec Clarifications/FR-027, Contract `main-window-ui.md` §Screen States]
- [x] CHK052 Does the selected shell fill `1280×760` and `1040×680` without an outer frame, clipping, horizontal overflow, or loss of the native capture rail? [Responsive Geometry, Visual Target §Geometry And Responsive Target]
- [x] CHK053 Is the current Stitch screen ID consistent across research, visual target, quickstart, tasks, and validation evidence? [Traceability, Research §Decision 10, Visual Target §Source Of Truth]

## Final Visual-contract Notes

- All five checks passed against the then-current Stitch screen and fresh Playwright snapshots at both target sizes; the final source is recorded below after density and semantic remediation.
- The ordinary `1040×680` accessibility tree contained zero checkbox/delete nodes; hover and keyboard focus exposed the row-specific names.
- Commit approval was granted after the earlier remediation note; only feature-owned artifacts may be included in the checkpoint commit.

## Analyze Finding Recheck — 2026-07-13

- [x] CHK054 Is the updated delivery boundary consistent with explicit user approval for scoped validated feature commits while still prohibiting deploy/release/installer replacement without a separate decision? [Consistency, Plan §Release Gate, Tasks §Notes, Quickstart §Release Boundary]
- [x] CHK055 Does the selected target render the contracted 20 px page heading, 36 px toolbar controls, and 48 px meeting rows at both target viewports? [Geometry, Contract `main-window-ui.md` §Typography And Density, Quickstart §Approved Pre-build Visual Target]
- [x] CHK056 Does processing/date wording use the approved one-line `Обрабатывается` and lowercase Russian month abbreviations without exposing a fake or terminal percentage? [Localization, Contract `meeting-list-presentation.md` §Duration And Date/Status And Progress]
- [x] CHK057 Is readiness communicated through a conventional check symbol and exact accessible name rather than color alone? [Accessibility, Contract `main-window-ui.md` §Accessibility, Visual Target §Accessibility Target]
- [x] CHK058 Is the primary `Открыть встречу …` link semantically distinct from contextual selection/delete, with source icon replacement and no permanently empty selection column? [Interaction, Contract `meeting-list-presentation.md` §Row Composition]

## Analyze Finding Notes

- All five first-pass findings are resolved; the final source ID is recorded in the last recheck below.
- Fresh ordinary, hover, row-focus, checkbox-focus, and result-link-focus accessibility snapshots confirm the intended disclosure and keyboard order at `1040×680`.

## Target-size And Motion Recheck — 2026-07-13

- [x] CHK059 Does the selected target disable the processing pulse and reduce nonessential transition durations when `prefers-reduced-motion: reduce` matches? [Accessibility, Spec §FR-034, Contract `main-window-ui.md` §Interaction Contract]
- [x] CHK060 Do the meeting result link, contextual checkbox label, and delete button provide at least 32×32 CSS px hit areas without changing the compact 48 px row? [Target Size, Contract `main-window-ui.md` §Typography And Density]
- [x] CHK061 Does `Открыть управление записью` provide a measured 40×40 CSS px hit area inside the 48–52 pt rail? [Target Size, Visual Target §Geometry And Responsive Target]

## Target-size And Motion Notes

- All three checks passed in final Stitch screen `e3c3421bd78e4320845d072c6a7193cc`.
- Playwright measured checkbox label `32×32`, delete `32×32`, result link height `32`, and rail disclosure `40×40`; the reduced-motion probe returned `pulseAnimation: none` and `rowTransitionDuration: 1e-05s`.

## Final Implementation Recheck — 2026-07-13

- [x] CHK062 Does the implemented ordinary screen contain only working navigation, one search, contextual list tools, upload, meeting results, and native capture control? [Relevance, T005–T009/T030–T031]
- [x] CHK063 Do real browser measurements at both embedded target widths show zero horizontal overflow, contracted sidebar/toolbar/row geometry, and preserved dates/actions? [Responsive QA, Quickstart §12]
- [x] CHK064 Does the focused accessibility snapshot expose contextual checkbox/link/delete semantics only with row intent and restore filter focus after Escape? [Accessibility QA, Quickstart §12]
- [x] CHK065 Do ordinary native copy/contracts exclude raw IDs, paths, telemetry, internal processing names, diagnostics/report tooling, and placeholder support identifiers? [Debug-free UI, T018/T021–T023]
- [x] CHK066 Do automated checks preserve native one-action Stop, separate Pause/Resume controls, stable width, permission recovery, local custody, and metadata-only support boundaries? [Safety, T010–T016/T022]
- [x] CHK067 Did the implementation avoid new dependencies, schemas, routes, services, polling frequency, and capture-thread work while deleting only proven presentation noise? [Ponytail/Performance, Research §Implementation Deletion And Boundary Proof]
- [x] CHK068 Are final visual artifacts synthetic, outside git, recognizably GRAF, and clean-room distant from the supplied Krisp reference? [Privacy/Brand Distance, Quickstart §12]
- [ ] CHK069 Has the final native window been exercised unlocked through all required runtime/VoiceOver states at both app sizes? [Manual Runtime QA, T016/T028/T036]

## Final Implementation Notes

- CHK062–CHK068 pass against the final source, real browser runtime, automated
  native contracts, full repository gate, and rebuilt local release artifact.
- CHK069 is not waived: macOS remained locked and exposed no GRAF window to the
  accessibility client. T016, T028, and T036 stay open for that exact pass.
- No production deployment, public release, installer replacement, or private
  screenshot commit occurred.
