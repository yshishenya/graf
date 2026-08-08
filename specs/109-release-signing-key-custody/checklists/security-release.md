# Security & Release Requirements Checklist: Надёжное хранение ключа обновлений

> This checklist is for Sparkle Ed25519 custody. It does not authorize the
> former owner-only/self-signed Apple signing lane; current public macOS release
> gates are maintained by Feature 130.

**Purpose**: Проверить, что требования к custody ключа, trust migration и
выпуску сформулированы полно, однозначно и измеримо до реализации.
**Created**: 2026-07-17
**Feature**: [spec.md](../spec.md)
**Audience / timing**: автор и security/release reviewer перед реализацией и
физическим выпуском.

## Requirement Completeness

- [x] CHK001 Are the two protected channels named by required trust properties (independent administrator/control plane, access policy, recovery behavior), not only by count? [Completeness, Spec §FR-001]
- [x] CHK002 Are requirements defined for the active public-key manifest's schema, ownership, allowed status values, and fail-closed handling of an unknown version? [Gap]
- [x] CHK003 Are requirements defined for how a candidate app, manifest, local signer, and cloud signer prove equality using only safe public identifiers? [Completeness, Spec §FR-002, FR-004]
- [x] CHK004 Are requirements defined for initial enrollment of a new signer generation without exposing private material through shell history, logs, artifacts, or persistent temporary files? [Gap]
- [x] CHK005 Are requirements defined for a periodic two-channel readiness drill, its responsible role, and its evidence-retention boundary? [Gap]
- [x] CHK006 Are requirements defined for the protected workflow's trigger classes, trusted ref rule, least privilege, environment approval, and prohibition on untrusted pull-request execution? [Completeness, Spec §FR-008]
- [x] CHK007 Are requirements defined for the immutable provenance inputs and hash/identity checks for a draft archive and release notes before cloud signing? [Completeness, Spec §FR-002, FR-007]
- [x] CHK008 Are requirements defined for the explicit fallback decision when one protected channel is unavailable, including who may approve it and what must still be proven? [Completeness, Spec §FR-001, User Story 2]
- [x] CHK009 Are requirements defined for exact separation between signed draft artifacts, GitHub release assets, and the live public download host? [Completeness, Spec §FR-003, FR-007]
- [x] CHK010 Are requirements defined for cryptographic checksum algorithm, archive retention, and re-fetch proof before the live appcast changes? [Clarity, Spec §FR-007]

## Requirement Clarity

- [x] CHK011 Is “independent protected channels” clarified so two copies accessible through the same account, device, or administrator cannot qualify? [Ambiguity, Spec §FR-001]
- [x] CHK012 Is “always available” translated into measurable readiness/degraded/unavailable states and an operational recovery expectation rather than an unbounded availability promise? [Ambiguity, User input, Spec §SC-003]
- [x] CHK013 Is the safe `keyId` derivation (input, algorithm, encoding and comparison rules) specified precisely enough to prevent two tools from producing incompatible identifiers? [Clarity, Spec §FR-004]
- [x] CHK014 Is “approved release context” precise about tag ancestry, required branch/ref, required reviewer, and whether the workflow may write a draft release? [Clarity, Spec §FR-008]
- [x] CHK015 Is “one approved manual bootstrap” bounded by an explicit trust-generation transition, package label, and prohibition on appcast creation? [Clarity, Spec §FR-005, FR-006]
- [x] CHK016 Is the time/freshness rule for a cloud attestation specified, including what makes an attestation stale or bound to the wrong candidate? [Gap]
- [x] CHK017 Is “public catalog remains active” clarified for each failure point: before staging, after draft upload, after archive copy, and after appcast replacement? [Clarity, User Story 3]
- [x] CHK018 Are “previous version” and “strictly higher” specified consistently for CalVer, bootstrap, normal updates, and forward rollback? [Consistency, Spec §FR-007, User Story 3]

## Requirement Consistency

- [x] CHK019 Do the fallback-release requirements in User Story 2 remain consistent with SC-003, which treats a missing channel as blocking or emergency rather than routine success? [Consistency, Spec §User Story 2, §SC-003]
- [x] CHK020 Do the manual-bootstrap requirements preserve the ordinary-update key/feed immutability requirement without an implicit exception in shared staging tooling? [Consistency, Spec §FR-005, FR-006]
- [x] CHK021 Do the channel custody requirements align with the product rule that desktop clients, diagnostics, public hosts, and repository artifacts never carry secrets? [Consistency, Spec §FR-001, §SC-004]
- [x] CHK022 Do all release requirements preserve the stated bundle identifier, name, signing identity, capture deferral, and TCC boundary without introducing a conflicting recovery shortcut? [Consistency, Spec §FR-010]
- [x] CHK023 Do the plan's two post-bootstrap update proofs and the spec's single functional story describe the same number and purpose of sequential updates? [Consistency, Spec §SC-001, plan §Summary]

## Acceptance Criteria Quality

- [x] CHK024 Can “100% of checked failed signing attempts” be objectively scoped to a defined test matrix of absent, malformed, mismatched, stale, and inaccessible channel conditions? [Measurability, Spec §SC-002]
- [x] CHK025 Can “two independent protected channels” be objectively accepted without inspecting any secret value? [Measurability, Spec §SC-003]
- [x] CHK026 Is the definition of “no secret exposure” measurable across tracked files, app bundle, build artifacts, action output, caches, release assets, and diagnostics? [Measurability, Spec §SC-004]
- [x] CHK027 Are success criteria defined for a concurrent-release collision, including the expected state of both draft and public appcasts? [Gap, Spec §Edge Cases]
- [x] CHK028 Are success criteria defined for a cloud-signing workflow that succeeds but whose draft artifacts cannot be verified or copied to the public host? [Gap]

## Scenario & Recovery Coverage

- [x] CHK029 Are requirements specified for both normal two-channel readiness and explicitly approved one-channel degraded release paths? [Coverage, Primary and Alternate flows]
- [x] CHK030 Are requirements specified for no available channel, malformed key, wrong key, absent secret, expired/stale attestation, and an unavailable GitHub environment? [Coverage, Exception flows]
- [x] CHK031 Are requirements specified for revoking a compromised active key, retaining/replacing old public feed assets, and communicating the required new manual bootstrap? [Gap, Recovery flow]
- [x] CHK032 Are requirements specified for failed manual bootstrap installation, partial package delivery, and a client that has not yet moved off the historic trust line? [Coverage, Recovery flow]
- [x] CHK033 Are requirements specified for first normal update after bootstrap and the second continuity update, including what evidence proves each is not a manual installation? [Coverage, Spec §SC-001]
- [x] CHK034 Are requirements specified for restoring a known-good live appcast versus issuing a higher forward-fix after clients have installed a bad release? [Coverage, Spec §User Story 3]

## Dependencies & Assumptions

- [x] CHK035 Is the GitHub environment/reviewer capability validated as a required operational dependency before the new trust generation is activated? [Assumption, Spec §FR-008]
- [x] CHK036 Are Sparkle tool/version compatibility and the supported macOS Keychain account behavior recorded as dependencies with an upgrade/recheck trigger? [Dependency, plan §Technical Context]
- [x] CHK037 Is the historical app-signing assumption explicitly separated from
  Sparkle custody and excluded from the current public release path? [Assumption,
  Spec §Assumptions]
- [x] CHK038 Is the public-host operator boundary documented so it has artifact-copy authority but never signer-secret authority? [Dependency, Spec §FR-001, FR-007]

## Notes

- This is a requirements-quality checklist, not implementation test evidence.
- Any unchecked `[Gap]`, `[Ambiguity]`, `[Conflict]`, or `[Assumption]` item
  that changes the security/release decision must be resolved in the spec or
  plan before implementation.
