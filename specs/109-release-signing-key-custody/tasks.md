# Tasks: Надёжная custody подписи обновлений

**Input**: Design documents from `/specs/109-release-signing-key-custody/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [release-signing-custody.md](contracts/release-signing-custody.md), and [quickstart.md](quickstart.md)

**Risk / validation lane**: High-risk feature: release secrets, update trust, manual installer migration and public delivery. Tests and security gates are required before any physical release.

**Tests**: Add focused XCTest source/evidence coverage plus runnable shell and workflow checks before behavior changes. Use only disposable test keys and metadata-only fixtures.

**Organization**: Tasks are grouped by user story so each increment has a separate proof. `tasks.md` is the implementation source of truth.

## Phase 1: Setup and test boundary

**Purpose**: Establish the safe public trust representation and regression coverage without creating a real production key.

- [X] T001 [P] Add active/unprovisioned/malformed public manifest and secret-free output expectations to `apps/macos/Shared/Tests/InstallerLifecycleEvidenceTests.swift`.
- [X] T002 [P] Create a disposable fixture harness in `apps/macos/Installer/Scripts/test-release-signing-custody.sh` and an ignore rule in `.gitignore`; it must reject a production-key fixture.
- [X] T003 Create `apps/macos/Installer/UpdateSigningKey.json` with an unprovisioned public-only schema and `apps/macos/Installer/Scripts/release-signing-common.sh` for strict manifest, `keyId`, permission and safe-output helpers.
- [X] T004 Run the new focused fixture/test command in `apps/macos/Installer/Scripts/test-release-signing-custody.sh` and confirm desired guards fail before their implementation is complete.

**Checkpoint**: No secret source exists; the canonical public trust schema and test harness are ready.

---

## Phase 2: Foundational signing and build invariants

**Purpose**: Create the shared fail-closed boundary that every bootstrap, local recovery and cloud signing path must use.

**⚠️ CRITICAL**: Complete this phase before any user-story release flow.

- [X] T005 Update `apps/macos/Installer/Scripts/build-local-installer.sh` to load configured updater public trust from `apps/macos/Installer/UpdateSigningKey.json`, reject inactive/malformed/mismatched overrides, and retain updater-disabled local builds.
- [X] T006 Update `apps/macos/Installer/Scripts/prepare-app-update.sh` to require manifest/app/signer equality before staging, remove general local `GRAF_SPARKLE_PRIVATE_KEY_FILE` use, and permit a restrictive ephemeral CI file only through `release-signing-common.sh`.
- [X] T007 Create `apps/macos/Installer/Scripts/validate-manual-update-bootstrap.sh` that retains GRAF identity/signing/permission validation while allowing only an explicitly manual trust-generation change; it must not stage an appcast.
- [X] T008 Extend `apps/macos/Shared/Tests/InstallerLifecycleEvidenceTests.swift` and `apps/macos/Installer/Scripts/test-release-signing-custody.sh` for malformed manifest, key mismatch, forbidden legacy file, wrong temporary-file permissions, and ordinary key/feed rotation.
- [X] T009 Run shell syntax and focused macOS tests for `release-signing-common.sh`, `prepare-app-update.sh`, `validate-manual-update-bootstrap.sh`, and `test-release-signing-custody.sh`; fix all foundation failures.

**Checkpoint**: All signer paths share one public key/fingerprint rule and ordinary Sparkle trust remains immutable.

---

## Phase 3: User Story 1 — Один честный bootstrap и штатные обновления (Priority: P1) 🎯 MVP

**Goal**: Move a controlled installed client through one manual package, then allow the next ordinary Sparkle update without a trust bypass.

**Independent Test**: Disposable keys and controlled app bundles show that only the explicitly marked bootstrap may change trust; normal staging rejects the same rotation; the post-bootstrap candidate stages as a normal same-key update.

### Tests for User Story 1

- [X] T010 [P] [US1] Add bootstrap-versus-ordinary-update acceptance coverage to `apps/macos/Shared/Tests/InstallerLifecycleEvidenceTests.swift` and `apps/macos/Installer/Scripts/test-release-signing-custody.sh` before completing bootstrap packaging.

### Implementation for User Story 1

- [X] T011 [US1] Create `apps/macos/Installer/Scripts/build-trust-bootstrap.sh` that calls `validate-manual-update-bootstrap.sh`, labels a one-time migration, preserves GRAF identity and never stages an appcast.
- [X] T012 [US1] Update `apps/macos/Installer/README.md` with migration, failed-install recovery, old-client limitation and two sequential in-app proof steps without a secret or local secret path.
- [X] T013 [US1] Update `qa/macos/release-candidate-checklist.md` with bootstrap identity/TCC continuity, manual-install boundary and the first/second normal update gates.
- [X] T014 [US1] Run `apps/macos/Installer/Scripts/test-release-signing-custody.sh` and `apps/macos/Scripts/validate-macos-permission-retention.sh` identity checks on disposable artifacts; preserve only metadata-safe evidence in `quickstart.md`.

**Checkpoint**: A bootstrap cannot masquerade as an ordinary update and normal validation cannot be weakened by migration.

---

## Phase 4: User Story 2 — Выпуск без единой точки потери (Priority: P1)

**Goal**: Let an approved release operator use either a protected cloud signer or named Keychain recovery signer while proving both use the same public trust generation.

**Independent Test**: Disposable local/GitHub checks emit the same safe `keyId`; absent/mismatched channels fail before signed draft artifacts; an explicitly approved degraded fallback retains all equality checks.

### Tests for User Story 2

- [X] T015 [P] [US2] Add no-secret-output, safe-attestation, protected-manual-trigger, least-permission, no-untrusted-PR, immutable external-action SHA and temporary-key-cleanup expectations to `apps/macos/Shared/Tests/InstallerLifecycleEvidenceTests.swift`.
- [X] T016 [P] [US2] Add workflow syntax/static-policy checks for immutable external-action SHAs, `.github/workflows/verify-release-signing-custody.yml` and `.github/workflows/sign-graf-app-update.yml` to `apps/macos/Installer/Scripts/test-release-signing-custody.sh`.

### Implementation for User Story 2

- [X] T017 [US2] Create `apps/macos/Installer/Scripts/provision-release-signing-custody.sh` to initialize/verify a named Keychain generation, transfer only through a restrictive transient channel to the protected GitHub environment secret, and refuse accidental overwrite or secret output.
- [X] T018 [US2] Create `apps/macos/Installer/Scripts/verify-release-signing-custody.sh` to compare candidate app, active manifest, Keychain public key and cloud attestation; output only `keyId` and ready/degraded/unavailable state.
- [X] T019 [US2] Create `.github/workflows/verify-release-signing-custody.yml` with `workflow_dispatch`, `graf-release-signing` gate, exact-tag checks and metadata-only attestation; it must have no public-host write path.
- [X] T020 [US2] Create `.github/workflows/sign-graf-app-update.yml` to validate exact tagged draft inputs, materialize the protected secret only in a restrictive runner-temporary file, invoke the shared staging contract, upload only signed draft assets/checksums, and serialize release runs.
- [X] T021 [US2] Update `apps/macos/Installer/README.md` and `specs/109-release-signing-key-custody/quickstart.md` with environment approval, readiness drill, degraded fallback and safe attestation retrieval instructions.
- [ ] T022 [US2] Run local disposable-key tests in `apps/macos/Installer/Scripts/test-release-signing-custody.sh` and dispatch `.github/workflows/verify-release-signing-custody.yml` against an approved non-production tag using a dedicated disposable test secret/environment; prove matching, missing and mismatched states without exposing or activating the future production generation.

**Checkpoint**: The normal and recovery signers are independently usable and known equal before a release can proceed.

---

## Phase 5: User Story 3 — Безопасная готовность, сериализация и rollback (Priority: P2)

**Goal**: Make readiness, concurrent-release behavior and forward rollback safe and observable without revealing signer material or leaving a broken feed.

**Independent Test**: A stale/wrong attestation, missing artifact, cancelled request or concurrent request leaves the live appcast unchanged and produces a safe blocked/degraded result.

### Tests for User Story 3

- [X] T023 [P] [US3] Add stale/wrong-release attestation, draft-asset failure, concurrent-run and forward-rollback coverage to `apps/macos/Installer/Scripts/test-release-signing-custody.sh` and `apps/macos/Shared/Tests/InstallerLifecycleEvidenceTests.swift`; receipt recorded in `quickstart.md`.

### Implementation for User Story 3

- [X] T024 [US3] Add release-attempt serialization, attestation binding and atomic draft/staging failure handling to `apps/macos/Installer/Scripts/prepare-app-update.sh` and `.github/workflows/sign-graf-app-update.yml`.
- [X] T025 [US3] Add compromised-key, appcast-restore and forward-fix procedure to `apps/macos/Installer/README.md` and `qa/macos/release-candidate-checklist.md`, including the required new manual bootstrap after compromise.
- [X] T026 [US3] Add a tracked-source/artifact secret-pattern guard to `apps/macos/Installer/Scripts/test-release-signing-custody.sh` and document intentional false-positive handling in `apps/macos/Installer/README.md` without a real-secret exception.
- [X] T027 [US3] Run all US3 failure simulations with `apps/macos/Installer/Scripts/test-release-signing-custody.sh` and `apps/macos/Installer/Scripts/prepare-app-update.sh`; verify the previous staged/public appcast digest is unchanged for every blocked path; receipt recorded in `quickstart.md`.

**Checkpoint**: Release errors are fail-closed, serialized, safely diagnosable and recover only through a known-good feed or higher signed forward fix.

---

## Phase 6: Polish, integration and physical-release proof

**Purpose**: Finish cross-feature validation and the controlled trust migration only after code and repository gates are green.

- [X] T028 [P] Update `CHANGELOG.md` under `[Unreleased]` with feature 109 custody, manual-bootstrap compatibility and no-secret release-note wording.
- [X] T029 [P] Run `git diff --check`, shell syntax, workflow static checks, `swift test --package-path apps/macos --filter InstallerLifecycleEvidenceTests`, and `apps/macos/Installer/Scripts/test-release-signing-custody.sh`.
- [X] T030 Run `infra/scripts/ci-local.sh`, triage every new failure, and preserve high-risk validation evidence without raw keys/audio/transcripts.
- [X] T031 Re-run Spec Kit analyze for `specs/109-release-signing-key-custody/`, reconcile feature-109 GitHub task issues, and obtain required code/release review before a production secret enrollment or tag.
- [X] T032 After `v2026.07.17.12` is merged, fetch and semantically merge the exact current `origin/master` into the feature/release branch; preserve the completed `.12` behavior, re-run focused tests, and do not create a tag or package during this sync.
- [X] T033 After feature merge and release approval, create a clean release worktree at exact refreshed `origin/master`, enumerate remote CalVer tags, choose the next free version strictly greater than `.12`, and verify the branch/tag provenance before any active-key enrollment.
- [X] T034 Record the changed private-repository operating decision in `specs/109-release-signing-key-custody/spec.md`, `plan.md`, `research.md`, `quickstart.md`, `apps/macos/Installer/README.md`, and `qa/macos/release-candidate-checklist.md`: the unavailable protected reviewer path is superseded by the explicitly degraded owner-only Keychain lane, with the offline password-manager copy used only for recovery.
- [X] T035 Build/install the selected next-free CalVer manual bootstrap with `apps/macos/Installer/Scripts/build-trust-bootstrap.sh`; prove app identity and retained permissions without resetting/regranting TCC. Закрыто историческим системным receipt bootstrap `2026.07.18.3` и последующим штатным Sparkle-переходом; см. `quickstart.md`.
- [X] T036 Produce and verify two strictly greater normal updates through `.github/workflows/sign-graf-app-update.yml`, publish versioned assets before `graf-appcast.xml`, and capture metadata-only proof of the two in-app installations. Закрыто receipt переходов `2026.07.18.3 → 2026.07.20.1` и `2026.07.20.2 → 2026.07.21.1`; см. `quickstart.md`.
- [X] T037 [US2] Prove the current owner-only release lane in `apps/macos/Installer/README.md`, `specs/109-release-signing-key-custody/quickstart.md`, and `qa/macos/release-candidate-checklist.md`: exact tag/provenance, fresh Keychain attestation, explicit degraded approval, archive-before-appcast ordering, and no automated password-manager or public-host signer access. Закрыто receipt релиза `v2026.07.21.3`; публичные archive/pkg/checksum проверены до замены appcast, затем весь public result перепроверен.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1**: no dependency and no real production secret.
- **Phase 2**: depends on T001–T004 and blocks every story.
- **US1**: depends on Phase 2 and delivers the manual migration boundary.
- **US2**: depends on Phase 2; disposable proof can run beside US1 documentation after shared scripts stabilize.
- **US3**: depends on core US1/US2 controls because it hardens their state transitions.
- **Phase 6**: depends on all code/tests. T032–T037 require explicit release approval and a green repository gate; T035/T036/T037 are physical or release-lane proof, not documentation-only completion.

### User Story Dependencies

```text
Foundation
  ├── US1: explicit bootstrap boundary
  └── US2: protected dual signer custody
          \
           └── US3: safe release/rollback state
                 └── physical bootstrap + two in-app proofs
```

### Parallel Opportunities

- T001/T002 touch different test/harness surfaces.
- T015/T016 can be prepared in parallel after foundational contracts exist.
- T028 and focused validation preparation can run in parallel after user stories complete.
- No real-key, live-feed, tag or production-package operation is parallelizable.

## Parallel Example: User Story 2

```text
Task: "Add custody evidence tests in apps/macos/Shared/Tests/InstallerLifecycleEvidenceTests.swift"
Task: "Add workflow policy checks in apps/macos/Installer/Scripts/test-release-signing-custody.sh"
```

## Implementation Strategy

### MVP First

1. Complete Phase 1 and Phase 2.
2. Complete US1 so a trust transition remains manual-only and safe.
3. Complete US2 so the new signer is genuinely recoverable through two protected channels.
4. Stop for focused validation before any physical release state change.

### Incremental Delivery

1. Shared manifest/guard → no new secret and no relaxed update trust.
2. Bootstrap boundary → one honest migration path.
3. Protected signer workflows remain the future two-channel path; the current private-repository lane is the explicitly degraded owner-only Keychain path.
4. State/rollback checks → release safety under failure.
5. Green repository gate + refreshed master after `.12` + approved migration → bootstrap, owner-only release proof, and two in-app proofs.

## Notes

- `[P]` never permits parallel operations on a real signing key or live feed.
- A task becomes `[X]` only after its listed validation evidence exists.
- No task authorizes a secret, raw recording, transcript, credential-bearing URL or live local secret path in issues, commits or release evidence.
