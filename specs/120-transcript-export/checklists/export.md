# Export Requirements Quality Checklist

**Purpose**: Validate canonical export, security/lifecycle, format, and UX
requirements before task generation and implementation
**Created**: 2026-07-21
**Audience**: Feature author and PR reviewer
**Depth**: Formal high-risk feature gate
**Feature**: [spec.md](../spec.md) · [plan.md](../plan.md)

## Requirement Completeness

- [x] CHK001 Are durable raw-source truth, canonical turns, human display groups, and per-format consumers each defined without overlap? [Completeness, Spec §FR-001–FR-007, Plan §Architecture Decisions 1]
- [x] CHK002 Are transcript-only, summary-only, and combined scope/format combinations explicitly enumerated? [Completeness, Spec §FR-018/FR-024/FR-031, Contract §Format and scope compatibility]
- [x] CHK003 Are all requested formats TXT, MD, CSV, XLSX, JSON, and SRT defined, with PDF/DOCX and adjacent expansion excluded? [Completeness, Spec §FR-010–FR-018, Spec §Out of Scope]
- [x] CHK004 Are saved summary categories, item fields, revision provenance, evidence references, and unavailable states specified? [Completeness, Spec §FR-020–FR-025, Data Model §Summary Revision Projection]
- [x] CHK005 Are meeting-detail action, Files/governance state, dialog, preview, progress, success, failure, retry, and disabled states documented? [Completeness, Spec §FR-030–FR-040, Plan §Architecture Decisions 6]
- [x] CHK006 Are policy, readiness, audit, deletion, retention, idempotency, and post-egress truth requirements defined separately for each content scope? [Completeness, Spec §FR-050–FR-066]

## Requirement Clarity

- [x] CHK007 Is revision pinning defined as one immutable snapshot rather than a vague “current” read performed by each serializer? [Clarity, Spec §FR-001/FR-005/FR-006, Plan §Architecture Decisions 1]
- [x] CHK008 Are canonical merge and non-merge boundaries explicit for speaker key, attribution, role, result, gap, overlap, invalid timing, and unknown state? [Clarity, Spec §FR-003/FR-004, Data Model §Canonical Speaker Turn]
- [x] CHK009 Is the exact one-second inclusive canonical threshold distinguished from optional human display grouping? [Clarity, Spec §Edge Cases, Data Model §Canonical Speaker Turn]
- [x] CHK010 Is “unknown” distinguished from confirmed `SPEAKER_00`, and is its export representation testable? [Clarity, Spec §FR-004/FR-016, Data Model §Canonical Speaker Turn]
- [x] CHK011 Are on-demand generation, absence of persistence, and the measured trigger for a future short-lived artifact design explicit? [Clarity, Spec §FR-050–FR-054, Plan §Architecture Decisions 2]
- [x] CHK012 Are supported format MIME, extension, scope, and filename rules explicit enough to reject aliases without implementation guessing? [Clarity, Spec §FR-066, Contract §File endpoint]

## Requirement Consistency

- [x] CHK013 Do spec, data model, API contract, and format contract consistently keep raw rows as truth and machine formats on canonical turns? [Consistency, Spec §Product Decision Summary, Data Model, Contracts]
- [x] CHK014 Do human grouping requirements preserve every child timestamp and avoid contradicting one-turn-per-row/cue machine formats? [Consistency, Spec §FR-004/FR-010–FR-017, Contract §Shared invariants]
- [x] CHK015 Do summary-only/combined requirements consistently forbid generation and select the stored outcome tied to the transcript result? [Consistency, Spec §FR-020/FR-023–FR-025, Plan §Architecture Decisions 4]
- [x] CHK016 Do new canonical endpoints remain additive and consistent with the raw/plain download and manifest-only package truth? [Consistency, Spec §FR-056/FR-064/FR-065, Contract §Compatibility]
- [x] CHK017 Are speaker display names treated consistently as projections while stable keys/states remain in structured formats? [Consistency, Spec §FR-003/FR-035, Format Contract §Shared invariants]
- [x] CHK018 Do performance targets align with the synchronous on-demand lifecycle and the explicit upgrade trigger? [Consistency, Spec §SC-006, Plan §Architecture Decisions 2, Quickstart §Performance checks]

## Acceptance Criteria Quality

- [x] CHK019 Can source-row retention, turn order/text/timing/state, and zero pause markers be measured across all requested formats? [Measurability, Spec §SC-001–SC-003]
- [x] CHK020 Are deterministic rerun expectations separated into byte-stable text formats and semantically stable XLSX package content? [Measurability, Spec §SC-004, Format Contract §Determinism]
- [x] CHK021 Are ready-response and XLSX progress/completion targets quantified with a named supported test environment requirement? [Measurability, Spec §SC-006, Quickstart §Performance checks]
- [x] CHK022 Are actor/policy/lifecycle matrices and fail-closed audit expectations expressed as countable outcomes? [Measurability, Spec §SC-008/SC-009/SC-013]
- [x] CHK023 Are revision-race and provider-swap outcomes objectively comparable from pinned metadata and semantic projections? [Measurability, Spec §SC-010/SC-011]
- [x] CHK024 Are usability and accessibility outcomes bounded by representative review and critical-blocker criteria? [Measurability, Spec §SC-012]

## Scenario Coverage

- [x] CHK025 Are primary transcript, structured-data, captions, summary, selection, and lifecycle stories independently testable? [Coverage, Spec §User Stories 1–6]
- [x] CHK026 Are alternate speaker/timestamp/evidence options constrained to projections without changing canonical data? [Coverage, Spec §FR-034/FR-035]
- [x] CHK027 Are exception paths defined for processing, partial, missing, denied, deleted, expired, generation failure, stale revision, and audit failure? [Coverage, Spec §FR-037/FR-060–FR-066, API Contract §Safe problem responses]
- [x] CHK028 Are recovery requirements defined for retry without duplicate artifacts/audits, selection loss, or content mutation? [Recovery, Spec §User Story 5.4/FR-053, API Contract §Browser meeting-detail contract]
- [x] CHK029 Is the capability-read-to-file-request revocation window explicitly covered by a server re-check? [Coverage, API Contract §Authorization and revision algorithm, Quickstart §Policy lifecycle]

## Edge Case Coverage

- [x] CHK030 Are 0.9/1.0/1.1/3/51/138-second gaps, A→B→A, unknown, source/result boundary, overlap, invalid/empty rows, and >1-hour timing all specified? [Coverage, Spec §Edge Cases, Quickstart §Canonical fixture matrix]
- [x] CHK031 Are Russian commas/quotes/line breaks, Markdown/HTML punctuation, control text, and spreadsheet formula prefixes covered without content loss? [Coverage, Spec §Edge Cases, Quickstart §Format safety checks]
- [x] CHK032 Are missing summary sections, missing owner/due date, unresolved evidence, and template/regeneration revisions explicit rather than silently omitted or invented? [Coverage, Spec §Edge Cases/FR-020–FR-025]
- [x] CHK033 Are valid overlap preservation and invalid SRT cue omission distinguished and surfaced truthfully? [Coverage, Spec §FR-015, Format Contract §SRT]

## Non-Functional Requirements

- [x] CHK034 Are formula/markup injection, MIME sniffing, cache, filename, and no-secret requirements specified at the egress trust boundary? [Security, Spec §FR-055/FR-066, API/Format Contracts]
- [x] CHK035 Are keyboard, focus trap/return, visible focus, live status, screen-reader naming, reduced motion, zoom/responsive, localization, and non-color meaning specified? [Accessibility, Spec §FR-039, API Contract §Browser meeting-detail contract]
- [x] CHK036 Are linear assembly, bounded memory, response time, progress, and future-persistence trigger requirements measurable? [Performance, Plan §Technical Context/Architecture Decision 2, Quickstart §Performance checks]
- [x] CHK037 Are metadata-only logging, diagnostics, audit, screenshots, fixtures, and committed evidence boundaries consistent? [Privacy, Spec §FR-055/SC-009, Quickstart §Prerequisites]
- [x] CHK038 Are provider neutrality and absence of provider calls/credentials independently testable? [Dependency, Spec §FR-006/FR-007/SC-011]

## Dependencies And Assumptions

- [x] CHK039 Are feature 113 turns, feature 118 speaker names, feature 049 outcomes, and feature 017 egress responsibilities mapped to concrete reuse seams? [Dependency, Spec §Assumptions, Research §Local evidence]
- [x] CHK040 Is the single new XLSX dependency justified against custom OOXML and broader spreadsheet stacks, with a generated-file validation requirement? [Dependency, Research §Decision 8, Plan §Complexity Tracking]
- [x] CHK041 Are no-table/no-worker/no-storage assumptions bounded by an explicit performance/memory upgrade trigger? [Assumption, Research §Decision 6]
- [x] CHK042 Are release/deploy, public links, ZIP/batch/integrations/audio, translation, retranscription, PDF, and DOCX clearly outside this slice? [Boundary, Spec §Out of Scope, Quickstart §Repository gate]

## Ambiguities And Conflicts

- [x] CHK043 Is the current code conflict around dropped unconfirmed turns and `SPEAKER_00` fallback recorded and resolved at the shared helper rather than hidden in serializers? [Conflict, Research §Local evidence/Decision 5]
- [x] CHK044 Is the current summary seed download distinguished from the stored-outcome export contract so implementation cannot treat placeholder text as a revision? [Conflict, Research §Local evidence, API Contract §Compatibility]
- [x] CHK045 Is “deterministic XLSX” qualified so ZIP metadata does not create an impossible byte-for-byte criterion while semantic content remains stable? [Ambiguity, Format Contract §Determinism]
- [x] CHK046 Is partial/draft export explicitly deferred, avoiding contradictory partial status support in implementation tasks? [Ambiguity, Spec §Assumptions, Research §Decision 3]

## Gate Result

## Export Dialog And Native Save Follow-up

- [x] CHK047 Is the default-dialog hierarchy explicit about which choices and action remain visible, and which technical fields use progressive disclosure? [Clarity, Spec §US5.6/FR-033/FR-036]
- [x] CHK048 Are compact embedded-width, 200% zoom, keyboard disclosure, and no-horizontal-overflow outcomes measurable without prescribing a competitor layout? [Measurability, Spec §SC-012a/FR-040]
- [x] CHK049 Does the embedded-client requirement name the native Save dialog, suggested filename/extension, destination choice, overwrite behavior, and cancel outcome? [Completeness, Spec §US5.5/FR-039/SC-012b]
- [x] CHK050 Is browser-owned attachment behavior kept distinct from embedded macOS save ownership so the web client does not invent a filesystem picker? [Consistency, API Contract §Browser meeting-detail contract]
- [x] CHK051 Is Save-dialog cancellation defined as writing no file and preserving meeting/selection state without weakening server policy, audit, or revision truth? [Recovery, Spec §FR-039/SC-012b]
- [x] CHK052 Is the native implementation boundary constrained to existing WebKit/AppKit primitives with no new persistence, service, or dependency? [Assumption, Plan §Architecture Decisions 6, Research §Decision 11]
- [x] CHK053 Does the revised default dialog require only two plain-language choices and one primary action? [Clarity, Spec §US5.6/FR-031–FR-033]
- [x] CHK054 Are technical metadata, diagnostic preview, and visible format cards explicitly excluded without weakening server revision/policy/audit truth? [Boundary, Spec §FR-033/FR-036]
- [x] CHK055 Are optional presentation settings and copy preserved as collapsed secondary actions rather than removed or made primary? [Completeness, Spec §FR-035/FR-038]
- [x] CHK056 Is the simple-dialog outcome measurable without requiring a reviewer to understand internal export terminology? [Measurability, Spec §SC-012c]

56/56 requirement-quality checks pass. No unresolved requirement ambiguity or
constitution conflict remains before task generation.
