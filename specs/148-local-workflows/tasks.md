# Tasks: Локальные CI и release workflows

**Input**: Design documents from `specs/148-local-workflows/`

**Tests**: Security-sensitive signing migration requires focused negative tests
plus fast/full repository gates.

## Phase 1: Foundational contracts

- [X] T001 Update the local-only signing channel schema and validators in `apps/macos/Installer/UpdateSigningKey.json` and `apps/macos/Installer/Scripts/release-signing-common.sh`
- [X] T002 Update local-only signer initialization and recovery in `apps/macos/Installer/Scripts/provision-release-signing-custody.sh`
- [X] T003 [P] Update local custody verification output contract in `apps/macos/Installer/Scripts/verify-release-signing-custody.sh`

## Phase 2: User Story 1 - Локальная проверка изменений (P1)

**Goal**: Existing local fast/full CI remains the sole validation entrypoint.

**Independent Test**: Run both local lanes and obtain explicit pass/fail without
creating a GitHub Actions run.

- [X] T004 [US1] Assert the existing fast/full CI contract remains canonical in `infra/scripts/ci-local.sh`

## Phase 3: User Story 2 - Локальная проверка ключа подписи (P1)

**Goal**: Exact-tag Keychain custody produces metadata-only evidence.

**Independent Test**: Disposable matching signer succeeds; missing/mismatched
signer, tag and commit fixtures fail before mutation.

- [X] T005 [US2] Add local-only manifest and attestation fixtures before implementation in `apps/macos/Installer/Scripts/test-release-signing-custody.sh`
- [X] T006 [US2] Complete local custody verifier behavior in `apps/macos/Installer/Scripts/verify-release-signing-custody.sh`

## Phase 4: User Story 3 - Локальная подпись draft release (P1)

**Goal**: One local command safely signs approved draft assets with Keychain.

**Independent Test**: Disposable draft fixtures stage bounded outputs; unsafe
archive/provenance/signer scenarios make zero upload calls.

- [X] T007 [US3] Add local draft-signing orchestration fixtures before implementation in `apps/macos/Installer/Scripts/test-release-signing-custody.sh`
- [X] T008 [US3] Implement the fail-closed local signing entrypoint in `apps/macos/Installer/Scripts/sign-graf-app-update-local.sh`

## Phase 5: User Story 4 - GitHub без исполняемых workflows (P2)

**Goal**: GitHub stores collaboration/release data but executes no workflows.

**Independent Test**: No tracked workflow YAML remains, active guidance names
only local commands, and repository Actions API returns disabled.

- [X] T009 [P] [US4] Remove `.github/workflows/validate.yml`, `.github/workflows/verify-release-signing-custody.yml`, and `.github/workflows/sign-graf-app-update.yml`
- [X] T010 [US4] Replace remote execution guidance in `docs/agent-guidance/release-and-validation.md`, `docs/agent-guidance/macos-notarization.md`, and `infra/scripts/README.md`
- [X] T011 [US4] Update release-signing lifecycle tests and active-source scans in `apps/macos/Installer/Scripts/test-release-signing-custody.sh` and `apps/macos/Shared/Tests/InstallerLifecycleEvidenceTests.swift`

## Phase 6: Closeout

- [X] T012 Update `[Unreleased]` operations notes in `CHANGELOG.md`
- [X] T013 Record feature 148 in `docs/current-product-status.md` and `docs/spec-kit-feature-index.md`
- [X] T014 Run `specs/148-local-workflows/quickstart.md` focused checks and mark completed tasks
- [X] T015 Run `infra/scripts/ci-local.sh --fast`, `infra/scripts/ci-local.sh --full`, and verify repository Actions `enabled=false`

## Dependencies & Execution Order

1. T001–T003 establish the local trust contract.
2. T005–T006 prove custody before draft orchestration.
3. T007–T008 implement signing before deleting workflows.
4. T009–T013 remove the remote surface and update active truth.
5. T014–T015 validate the complete migration.

T004 can be inspected independently. T009 can be prepared in parallel with T010
but must not be considered complete until T008 passes focused tests.

## Implementation Strategy

Reuse existing CI/CD and release-signing helpers. Add one orchestration script,
delete three YAML workflows, add no dependencies, preserve the current signer
and trust generation.
