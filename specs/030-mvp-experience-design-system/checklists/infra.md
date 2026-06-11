# Infrastructure Requirements Checklist: MVP Product Experience And Design System

**Purpose**: Validate that requirements capture server, storage, processing, deletion, and external-dependency truth needed by the MVP experience design. This checklist tests the written requirements, not deployment or runtime behavior.
**Created**: 2026-06-11
**Feature**: 030-mvp-experience-design-system

## Requirement Completeness

- [x] CHK001 Are requirements complete for all infrastructure-owned user-visible states: signed out, connected, stale policy, server offline, upload queued, uploading, uploaded, audio extraction, transcription, transcript ready, notes ready, degraded, failed, deleted, and access denied? [Completeness, Spec §FR-014, Spec §FR-029, Contract cross-surface-status]
- [x] CHK002 Are requirements complete for representing Rec server, Postgres, MinIO, Temporal, MediaScribe, Langfuse, backups, diagnostics, and local buffers in lifecycle/deletion truth? [Completeness, Constitution §III-IV, Spec §FR-020]
- [x] CHK003 Are requirements complete for manual media upload infrastructure states, including accepted category, upload, audio extraction, processing, failure, ownership, retention, and deletion implications? [Completeness, Spec §FR-012, Spec §SC-004]
- [x] CHK004 Are requirements complete for keeping desktop clients away from MediaScribe credentials, object-storage credentials, signed URLs, and direct third-party upload paths? [Completeness, Constitution §III, Plan §Constraints]
- [x] CHK005 Are requirements complete for the full browser cabinet routes that expose account/security, admin, audit, retention, deletion, sharing, downloads, billing, team/workspace, help/legal, and browser-only launch surfaces? [Completeness, Spec §FR-008]
- [x] CHK006 Are requirements complete for the embedded desktop subset when server account/cabinet state is unavailable, slow, signed out, or blocked while local recording remains available by policy? [Completeness, Spec §Edge Cases, Data Model §Embedded Desktop Cabinet Subset]

## Requirement Clarity

- [x] CHK007 Is the distinction between upload accepted, server stored, audio extraction running, transcription running, transcript ready, and notes ready clear enough for user-facing labels in desktop and web? [Clarity, Contract cross-surface-status]
- [x] CHK008 Is deletion language specific enough to avoid promising universal erasure outside 2brain Rec controlled systems and dependencies? [Clarity, Constitution §IV, Spec §FR-020]
- [x] CHK009 Are infrastructure failure states clear about what exists, what failed, which dependency is involved, and what user action is available without exposing sensitive internals? [Clarity, Spec §US3, Contract cross-surface-status]
- [x] CHK010 Are browser-only route classifications clear enough for admin, audit, legal/help, billing, public sharing, exports/downloads, and full video UX to avoid accidental desktop embedding? [Clarity, Spec §FR-006, Contract route-visibility]
- [x] CHK011 Are MediaScribe, Langfuse, MinIO, Postgres, Temporal, and backup boundaries described in product language rather than implementation-only jargon? [Clarity, Constitution §III-IV, Spec §FR-020]
- [x] CHK012 Are sample-data and prototype-handoff requirements clear enough to avoid real meeting content, credentials, signed URLs, live local paths, or private infrastructure metadata? [Clarity, Contract prototype-handoff]

## Requirement Consistency

- [x] CHK013 Are server/storage/processing requirements consistent between the constitution, spec, plan, status contract, route contract, data model, and quickstart? [Consistency, Constitution §III-IV, Spec §FR-020, Plan §Constraints]
- [x] CHK014 Are desktop and web requirements consistent about server unavailability not changing local recording truth or local artifact existence? [Consistency, Spec §US2, Data Model §Desktop Trust Shell]
- [x] CHK015 Are processing-state requirements consistent with already implemented `015` processing context and future dashboard/review work rather than implying this slice implements processing? [Consistency, Plan §Technical Context, Research §Owner Value Loop]
- [x] CHK016 Are manual upload requirements consistent with already implemented `014` desktop upload context and future browser upload/review surfaces? [Consistency, Plan §Technical Context, Spec §FR-011-FR-012]
- [x] CHK017 Are deletion/access requirements consistent between meeting review, status labels, route visibility, deferred retention/deletion slices, and future admin/audit surfaces? [Consistency, Spec §SC-005, Spec §FR-030, Contract cross-surface-status]
- [x] CHK018 Are external dependency requirements consistent with owner-controlled infrastructure positioning while still acknowledging allowlisted MediaScribe and Langfuse egress? [Consistency, Constitution §III, Spec §FR-020]

## Acceptance Criteria Quality

- [x] CHK019 Can reviewers objectively determine whether 100% of manual upload states include user-visible truth for accepted media category, upload, extraction, processing, failure, ownership, retention, and deletion implications? [Measurability, Spec §SC-004]
- [x] CHK020 Can reviewers objectively determine whether 100% of meeting review states distinguish upload success from transcript readiness, notes readiness, sharing readiness, and deletion truth? [Measurability, Spec §SC-005]
- [x] CHK021 Can reviewers objectively determine whether 100% of launch-critical prototype paths show the same status in desktop app and web cabinet? [Measurability, Spec §SC-013]
- [x] CHK022 Are acceptance criteria defined for degraded infrastructure states without turning the checklist into a deployment smoke test? [Acceptance Criteria, Spec §SC-014, Quickstart §Purpose]
- [x] CHK023 Are success criteria defined for external artifact references without requiring secrets or private infrastructure access to review them? [Measurability, Spec §SC-012, Contract prototype-handoff]

## Scenario Coverage

- [x] CHK024 Are primary infrastructure-backed scenarios covered for server-connected account, manual upload, processing progress, completed review, and deletion/access entry points? [Coverage, Spec §US3, Data Model §Owner Value Loop]
- [x] CHK025 Are alternate scenarios covered for server slow/offline, stale policy, signed-out upload block, multiple workspaces, and embedded cabinet unavailable? [Coverage, Spec §Edge Cases]
- [x] CHK026 Are exception scenarios covered for unsupported, oversized, encrypted, corrupted, duplicate, no-audio, partial upload, MediaScribe unavailable, and notes failed? [Coverage, Spec §Edge Cases]
- [x] CHK027 Are recovery scenarios covered for retry, browser handoff, re-auth/session recovery, degraded meeting review, and later deletion/lifecycle follow-up? [Coverage, Contract route-visibility, Contract cross-surface-status]
- [x] CHK028 Are non-functional infrastructure UX scenarios covered for privacy, redaction, metadata-only traces, external design tools, localization, and no secret leakage? [Coverage, Constitution §III, Spec §FR-018-FR-020]

## Edge Case Coverage

- [x] CHK029 Are requirements defined for upload succeeds but MediaScribe processing is not configured or unavailable? [Coverage, Spec §Edge Cases]
- [x] CHK030 Are requirements defined for transcript ready but notes/action items fail or remain unavailable? [Coverage, Spec §Edge Cases, Spec §FR-014]
- [x] CHK031 Are requirements defined for deleted, access denied, and local/server disagreement states without leaking private meeting metadata? [Coverage, Contract cross-surface-status]
- [x] CHK032 Are requirements defined for backup expiry, Temporal/workflow payload limits, diagnostics, unreachable clients, and external dependency deletion limits as future lifecycle truth? [Coverage, Constitution §IV]

## Dependencies & Assumptions

- [x] CHK033 Are dependencies on `014`, `015`, `028`, `029`, PRD/status docs, ADR 001, MediaScribe, Langfuse, MinIO, Postgres, Temporal, and Docker traceable from the plan? [Dependency, Plan §Primary Dependencies, Constitution §Product And Platform Constraints]
- [x] CHK034 Are assumptions clear that this feature produces design and handoff artifacts, not production Docker, API, worker, storage, backup, migration, or deployment changes? [Scope, Spec §FR-031, Plan §Summary]
- [x] CHK035 Is there any ambiguity about which infrastructure workflows are first-launch required, browser-only handoff markers, deferred, or out of scope? [Ambiguity, Spec §FR-001, Spec §FR-030]
