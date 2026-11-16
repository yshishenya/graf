# Specification Quality Checklist: F296 — Доказуемая серверная копия и безопасная очистка кэша

**Purpose**: Validate specification completeness and quality before planning
**Created**: 2026-11-16
**Feature**: [spec.md](../spec.md)

**Review Ownership**: reviewer-owned after the initial author self-check.

## Content Quality

- [x] No implementation details (languages, frameworks, APIs) leak into user-facing requirements
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders where the requirement is user-facing
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [ ] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic where they describe outcomes
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [ ] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [ ] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [ ] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Safety And Product Gates

- [x] Fail-closed behavior is explicit for every missing, unknown, stale or errored proof
- [ ] Deletion is limited to verified WAVs under explicit/automatic gates; no queue-schema change
- [x] F284 local playback, local-only mode and the local player are explicitly preserved
- [x] Server quota is explicitly not a capture or eviction gate
- [x] Retention and `archive_audio=false` are explicit keep-local conditions
- [ ] Dry-run evidence proves both eligibility logic and absence of file/queue mutation
- [x] Manual cleanup deletes only the transcription WAV and preserves review audio, manifest, queue row and local playback
- [ ] Automatic eviction is gated by a kill switch, deletes only verified WAVs, and stops on any missing/stale proof
- [ ] Cleanup and eviction are idempotent and leave a durable receipt without paths, titles or transcripts
- [x] The cache budget and thresholds follow the PRD baseline (5 GB / 80% / 95% / 10 GB-or-10% / 7 days)
- [ ] User-facing cleanup copy and accessibility labels are specified
- [x] Account/workspace, open deletion, pending purge and generation fences are explicit
- [x] Diagnostics and report content exclude paths, titles, transcripts and credentials

## Notes

- Items marked incomplete require spec updates before `$speckit-clarify` or `$speckit-plan`.
- The independent reviewer must re-check this file after clarify and before implementation; author self-check is not review evidence.
- **Review 2026-11-16**: 20/29 checked, 9 unchecked. See `review-2026-11-16.md`. The checklist now matches the Phase A/B/C scope. The 2026-11-16 review was run before the FR-011/revision/readability/roles/receipt fixes; a re-review is required.
