# Infrastructure Requirements Checklist: GitHub Full CI

**Purpose**: Validate release-gate requirements before implementation

**Created**: 2026-09-02

**Feature**: [spec.md](../spec.md)

**Review Ownership**: reviewer-owned; implementation MUST NOT mark these items complete.

## Release boundary

- [x] CHK001 Is the frozen candidate identity required before any full test starts? [Completeness, FR-001/FR-002]
- [x] CHK002 Does the specification require exactly one authoritative run and a create-once reservation? [Clarity, FR-004/FR-005]
- [x] CHK003 Are signing, notarization, publication and production deploy explicitly outside the GitHub workflow? [Boundary, FR-007/FR-010]

## Failure and concurrency

- [x] CHK004 Are stale, cancelled, failed, ambiguous and skipped-gate states all release-blocking? [Coverage, FR-006]
- [x] CHK005 Is same-candidate concurrency serialized without cancelling the first run? [Clarity, Edge Cases]
- [x] CHK006 Does one component failure make the aggregate fail rather than produce partial evidence? [Acceptance, SC-004]

## Security and evidence

- [x] CHK007 Are permissions read-only and artifacts metadata-only with a no-secret boundary? [Security, FR-007/SC-005]
- [x] CHK008 Do all component SHAs and artifact digests bind to the requested SHA? [Traceability, FR-004/SC-001]
- [x] CHK009 Is the local full lane clearly documented as non-authoritative fallback? [Consistency, FR-008]

## macOS diagnostic boundary

- [x] CHK010 Does the macOS-only diagnostic require a 40-character SHA, verify the checked-out commit before repository code runs, and preserve the pinned macOS 14 / Swift 6.0.3 baseline? [Traceability, FR-013]
- [x] CHK011 Is the diagnostic workflow explicitly non-authoritative, read-only, and unable to publish candidate reservations, artifacts, release evidence, deployments or releases? [Boundary, FR-007/FR-013]
- [x] CHK012 Does a successful macOS diagnostic still require one complete `release-full` with Ubuntu, macOS and aggregate evidence before release approval? [Acceptance, SC-002/SC-004]

## Reviewer Evidence

- 2026-09-02: reviewer-owned requirements review выполнен по `spec.md`, `plan.md` и контракту Feature 236; после уточнения требований все 9 из 9 критериев подтверждены трассировкой к указанным FR/SC.
- Follow-up по CHK005 закрыт: требования однозначно требуют сериализации запусков одного candidate, `cancel-in-progress: false`, сохранения первого run и завершения второго после reservation с причиной `candidate_already_reserved`. Это устраняет прежнюю неоднозначность о timeout/конфликтном исходе.
- Связанные GitHub issues закрываются только после проверки evidence по соответствующему Spec Kit task и добавления closure comment с результатом, границами и ссылками на PR/task; сама отметка checklist не означает завершение реализации.
- 2026-09-04: reviewer-owned follow-up по CHK010–CHK012 выполнен по обновлённым `spec.md`, `plan.md`, `contracts/macos-diagnostic-workflow.md`, `.github/workflows/macos-diagnostic.yml`, contract-тесту и release guidance. Exact-SHA macOS-only граница, отсутствие release authority и обязательный последующий полный `release-full` подтверждены; runtime evidence нового workflow остаётся гейтом T023 и не подменяет reviewer checklist.
