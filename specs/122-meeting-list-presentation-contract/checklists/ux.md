# UX Requirement-Quality Checklist: Meeting List Presentation Contract

**Purpose**: Validate that the specification package is complete, unambiguous, consistent, measurable, accessible, privacy-safe, and implementation-ready. This checklist evaluates requirement quality, not production behavior.

**Created**: 2026-07-21

**Feature**: [spec.md](../spec.md) · [visual-target.md](../visual-target.md) · [plan.md](../plan.md) · [UI contract](../contracts/meeting-list-presentation.md)

## Scope And Ownership

- [x] CHK001 Does the package clearly limit change to the server-owned browser/embedded meeting list and exclude native capture authority? [Spec §Scope Boundaries, FR-001–FR-002]
- [x] CHK002 Are meeting detail, transcript, notes, playback timeline, export, settings, onboarding, release, deploy, and new organization features explicitly outside scope? [Spec §Scope Boundaries]
- [x] CHK003 Is browser/embedded parity required without creating duplicate implementations? [FR-001, FR-036; UI Contract §Surface Ownership]
- [x] CHK004 Are existing access, upload, calendar, playback, deletion, and lifecycle owners preserved rather than redefined? [FR-012, FR-020, FR-032; Plan §Structure Decision]
- [x] CHK005 Is the no-Figma decision explicit and is the repository target identified as the pre-build gate? [Clarifications; FR-033]
- [x] CHK006 Are unsupported Krisp-like features exhaustively excluded so reference review cannot silently expand scope? [FR-030–FR-031; Visual Target §Source And Approval Boundary]

## Information Hierarchy And Copy

- [x] CHK007 Is exactly one page heading, search surface, filter access, sort access, and upload action required? [FR-003]
- [x] CHK008 Are the duplicate sort subtitle and `Записи встреч` heading explicitly removed? [FR-004]
- [x] CHK009 Is result count visibility limited to active search/filter refinement with exact `Найдено: N` copy? [FR-004; Visual Target §Toolbar Copy]
- [x] CHK010 Are toolbar labels, filter vocabulary, sort vocabulary, reset, and upload copy exact and internally consistent? [FR-035–FR-036; Visual Target §Toolbar Copy]
- [x] CHK011 Is default sort unambiguously `Сначала новые` by trusted meeting start with undated rows last? [FR-005]
- [x] CHK012 Does the package distinguish meeting time from update time and define exact updated-label semantics? [FR-006; Visual Target §Sort Vocabulary]
- [x] CHK013 Are first-empty, refined-empty, loading, offline, service-unavailable, session-expired, access-revoked, deletion-success, and partial-failure messages all distinct and exact? [FR-021–FR-025, FR-036; Visual Target §Empty, Loading And Recovery Copy]
- [x] CHK014 Does every list-region state specify no more than one applicable next action and avoid duplicated persistent actions? [SC-007; FR-022–FR-024]

## Row Content And Titles

- [x] CHK015 Are stable row zones for intent, primary content, one status, context action, and time explicitly required across hover/focus/selection? [FR-007]
- [x] CHK016 Is preservation of meaningful user/calendar/upload titles distinguished from generated-title normalization? [FR-008]
- [x] CHK017 Is generated capture copy exactly `Запись` and generated manual upload copy exactly `Загруженная запись`? [FR-008; Visual Target §Row Content Contract]
- [x] CHK018 Is date/time explicitly separated from neutral titles with a truthful `Без даты` fallback? [FR-009]
- [x] CHK019 Are duration examples and Russian formatting requirements specific enough to test? [Visual Target §Row Content Contract; UI Contract §Duration]
- [x] CHK020 Is visual truncation separated from the requirement to preserve the full safe accessible title? [FR-027, FR-029; Visual Target §Geometry]
- [x] CHK021 Does the package forbid technical identifiers, paths, reason codes, and unsafe fallback metadata in row presentation? [FR-025, FR-027, FR-034; Data Model §Validation invariants]

## Status Truth And Precedence

- [x] CHK022 Is the compact status precedence total, ordered, and deterministic for every canonical class? [Spec §Canonical Presentation States]
- [x] CHK023 Does the specification require zero normality badges for fully ready rows? [FR-011, SC-001]
- [x] CHK024 Are normal playback availability and normal calendar provenance explicitly excluded from compact status? [FR-011–FR-014]
- [x] CHK025 Is ambiguous calendar context represented by static `Нужен выбор` plus a separate `Выбрать встречу` action? [FR-013]
- [x] CHK026 Are measured upload, unmeasured upload, processing, audio preparation, audio absence, partial result, failure, local-only, and deletion states distinguishable by exact copy? [FR-010, FR-014–FR-016]
- [x] CHK027 Is terminal `100%` forbidden and is the trustworthy-measurement boundary explicit? [FR-015]
- [x] CHK028 Does higher compact priority hide only lower list tokens while preserving underlying detail/recovery truth? [Spec §Canonical Presentation States; FR-012]
- [x] CHK029 Are specific impact labels preferred over generic `Нужна помощь` when the current user impact is known? [FR-016]
- [x] CHK030 Are one-status and five-second comprehension outcomes measurable for every state-matrix row? [SC-002–SC-003]

## Opening, Selection, And Deletion

- [x] CHK031 Is pointer/Enter opening explicitly separated from checkbox/Space selection? [FR-017; Visual Target §Interaction Contract]
- [x] CHK032 Does the package state that opening never changes selection and selection never opens? [SC-005]
- [x] CHK033 Are contextual control visibility triggers defined for hover, keyboard focus, selected state, and non-hover surfaces? [FR-018]
- [x] CHK034 Is content geometry required to stay stable when contextual controls appear? [FR-007, SC-009]
- [x] CHK035 Are all four batch elements and their exact copy defined, with batch mode absent before selection? [FR-019, SC-006; Visual Target §Batch Copy]
- [x] CHK036 Are existing authorization, CSRF, confirmation, bounded-erasure truth, and lack of unsupported Undo preserved? [FR-020]
- [x] CHK037 Is deletion feedback placement above the list and non-focus-stealing live-region behavior explicit? [FR-021]
- [x] CHK038 Is deterministic focus recovery after a removed row specified in next/previous/list-anchor order? [Visual Target §Empty, Loading And Recovery Copy; UI Contract §Deletion]
- [x] CHK039 Does partial batch failure define both truthful count copy and preserved retry scope? [Visual Target §Empty, Loading And Recovery Copy; UI Contract §Deletion]

## Accessibility And Responsive Behavior

- [x] CHK040 Are homogeneous ordered-list semantics and one primary action required for assistive technology? [FR-027]
- [x] CHK041 Must title, duration, compact status, and time be announced without repeats or replacement by a short alternative name? [FR-027]
- [x] CHK042 Are names, roles, checked/selected states, keyboard reachability, visible focus, and non-color-only meaning all required? [FR-026–FR-028, SC-008]
- [x] CHK043 Is the project target for contextual controls at least 32×32 CSS px and stronger than the applicable WCAG minimum? [Visual Target §Geometry; UI Contract §Accessibility]
- [x] CHK044 Are `1280×760`, `1040×680`, long titles, increased contrast, scaling, and Reduce Motion all explicit validation conditions? [FR-029; SC-009]
- [x] CHK045 Is horizontal-scroll/overlap/clipping tolerance unambiguously zero for critical content and actions? [SC-009]
- [x] CHK046 Are asynchronous results, progress, deletion, and errors required to be announced without unexpected focus movement? [FR-026]
- [x] CHK047 Are hidden contextual controls required to leave both the tab order and accessibility tree while retaining an equivalent reveal path? [FR-018; UI Contract §Contextual controls]
- [x] CHK048 Is native capture independence preserved in offline/list failure states? [US4 scenario 3; FR-002, FR-024]

## Privacy, Clean-room, And Evidence

- [x] CHK049 Is metadata suppression after session expiry/access revocation explicit and comprehensive? [FR-025]
- [x] CHK050 Are prohibited evidence contents enumerated, including meeting names, participants, content, credentials, tokens, signed URLs, and local paths? [FR-034]
- [x] CHK051 Does evidence cover every canonical row/list class rather than only a happy path? [SC-011; Visual Target §Evidence Matrix]
- [x] CHK052 Are layout-sensitive states required at both target window sizes with keyboard/accessibility/contrast/motion evidence? [FR-029, SC-008–SC-009; Visual Target §Evidence Matrix]
- [x] CHK053 Is clean-room review measurable as zero copied Krisp wording, assets, icons, branded composition, or proprietary flow? [FR-030, SC-010]
- [x] CHK054 Does the package prevent screenshots from becoming a new source of private test fixtures or repository data? [FR-034; Plan §Validation Plan]

## Consistency And Measurability

- [x] CHK055 Do the spec, visual target, data model, and UI contract use the same status order and exact labels? [Cross-artifact review]
- [x] CHK056 Do the toolbar, filter, sort, batch, empty, recovery, and deletion labels match across all artifacts? [FR-036; Cross-artifact review]
- [x] CHK057 Is every success criterion observable without requiring access to internal implementation details? [SC-001–SC-012]
- [x] CHK058 Are existing search, filters, sort, upload, open, selection, and confirmed deletion explicitly protected from regression? [SC-012]
- [x] CHK059 Is the no-new-data/no-new-integration/no-lifecycle-change boundary stated in both requirements and implementation plan? [FR-032; Plan §Technical Context]
- [x] CHK060 Are known edge cases for missing data, long titles, state collisions, partial materials, upload measurement loss, batch failure, focus removal, access loss, and live refresh included? [Spec §Edge Cases]

## Review Result

- Requirement-quality checks passed: `60/60`.
- Open critical ambiguities: `0`.
- Constitution conflicts: `0`.
- Missing canonical copy/state classes: `0`.
- Implementation behavior is not claimed by this checklist; it is validated later through `tasks.md`, tests, synthetic evidence, and `infra/scripts/ci-local.sh`.
