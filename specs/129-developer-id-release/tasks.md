# Tasks: Developer ID как единственный публичный macOS-релиз

**Input**: [spec.md](spec.md), [plan.md](plan.md), [research.md](research.md),
[contracts](contracts/), [quickstart.md](quickstart.md)

## Dependencies

```text
T001 ─┬─> T003 ─> T006 ─┐
T002 ─┘       └> T005 ─┤
T004 ────────────────> T011 ─> T012 ─> T013
T007 ────────────────> T011
T008 ─┬─> T009 ───────> T011
T010 ─┘
```

`[P]` tasks touch separate files and can run in parallel after their listed
prerequisites. T011–T013 are sequential release gates.

## Phase 1: Foundational trust guards

**Goal**: Make the public path fail closed before documentation is changed.

- [ ] T001 [P] Add a `GRAF_REQUIRE_PUBLIC_UPDATE_TRUST=1` identity guard to `apps/macos/Installer/Scripts/build-local-installer.sh`, requiring Developer ID Application and Developer ID Installer identities and rejecting local/ad-hoc opt-ins.
- [ ] T002 Add `GRAF_MANUAL_DEVELOPER_ID_BOOTSTRAP=1` to `apps/macos/Scripts/validate-app-updates.sh`, preserving ordinary Developer ID continuity while allowing only the explicitly named legacy-to-Developer-ID manual transition without archive/appcast.

## Phase 2: User Story 1 — доверенный публичный релиз (P1)

**Goal**: Public release validation exposes one Developer ID-only contract.

**Independent test**: Source guards, syntax checks and public validation rules
reject non-Developer-ID identities before a public mutation.

- [ ] T003 [P] [US1] Add focused source assertions for public identity guards and ordinary Developer ID continuity to `apps/macos/Shared/Tests/InstallerLifecycleEvidenceTests.swift`.
- [ ] T004 [US1] Update the active public build/sign/notarize/Gatekeeper workflow and remove executable self-signed release commands from `apps/macos/Installer/README.md`.
- [ ] T005 [P] [US1] Update the active release gate and candidate checklist to Developer ID-only wording in `docs/agent-guidance/release-and-validation.md`, `AGENTS.md`, and `qa/macos/release-candidate-checklist.md`.

## Phase 3: User Story 2 — безопасный переход со старого клиента (P1)

**Goal**: The already-published `.6` transition is manual-package-only and
future updates are Developer ID→Developer ID.

**Independent test**: The migration wrapper accepts a notarized Developer ID
app/package with the historical predecessor, rejects archive/appcast inputs,
and ordinary mode still rejects a changed signing kind.

- [ ] T006 Add `apps/macos/Installer/Scripts/validate-developer-id-bootstrap.sh` that reuses the shared validator and checks Developer ID Installer package signature, staple and install Gatekeeper acceptance.
- [ ] T007 [P] [US2] Clarify Sparkle trust-generation rotation versus Apple Developer ID migration in `apps/macos/Installer/Scripts/build-trust-bootstrap.sh`, `apps/macos/Installer/Scripts/validate-manual-update-bootstrap.sh`, and `apps/macos/Installer/Scripts/provision-release-signing-custody.sh` guidance/comments without changing Sparkle custody behavior.
- [ ] T008 [P] [US2] Update `specs/095-macos-permission-retention/contracts/local-signing-runbook.md`, `specs/095-macos-permission-retention/contracts/macos-app-identity-contract.md`, `specs/095-macos-permission-retention/quickstart.md`, `specs/105-macos-app-updates/contracts/update-publication-contract.md`, `specs/105-macos-app-updates/quickstart.md`, `specs/105-macos-app-updates/spec.md`, `specs/109-release-signing-key-custody/quickstart.md`, `specs/109-release-signing-key-custody/spec.md`, `specs/109-release-signing-key-custody/plan.md`, `specs/109-release-signing-key-custody/research.md`, `specs/109-release-signing-key-custody/checklists/security-release.md`, and `specs/109-release-signing-key-custody/hardening/context.md` to document the manual `.pkg` bootstrap and ordinary Developer ID lineage.

## Phase 4: User Story 3 — единые инструкции без legacy-пути (P1)

**Goal**: Repository-wide active instructions converge on one canonical scheme.

**Independent test**: An active-path audit finds no unmarked self-signed,
owner-only or local public-release instruction.

- [ ] T009 [P] [US3] Update current status, feature index, and `.6` release/deployment evidence in `docs/current-product-status.md`, `docs/spec-kit-feature-index.md`, `docs/releases/v2026.07.26.6.md`, and `docs/deployments/2brain-rec/release-v2026.07.26.6.md`.
- [ ] T010 [P] [US3] Mark legacy signing passages as historical receipts or isolated fixtures in `docs/releases/v2026.07.24.11.md`, `docs/releases/v2026.07.26.4.md`, `docs/releases/v2026.07.26.5.md`, `docs/deployments/2brain-rec/release-v2026.07.24.11.md`, `docs/deployments/2brain-rec/release-v2026.07.26.1.md`, `docs/deployments/2brain-rec/release-v2026.07.26.2.md`, `docs/deployments/2brain-rec/release-v2026.07.26.4.md`, `docs/deployments/2brain-rec/release-v2026.07.26.5.md`, `apps/macos/Installer/README.md`, and `qa/macos/release-candidate-checklist.md` without rewriting prior facts.
- [ ] T011 [P] [US3] Add the Developer ID-only operating rule and `.6` manual-bootstrap limitation to `CHANGELOG.md` without adding credentials or signed URLs.

## Phase 5: Polish and cross-cutting validation

**Goal**: Prove the docs, scripts, evidence and repository state agree.

- [ ] T012 Run `sh -n`, focused Swift lifecycle evidence tests, and a repository-wide active-path audit; record only secret-free results in `specs/129-developer-id-release/quickstart.md` or the relevant status artifact.
- [ ] T013 Run `infra/scripts/ci-local.sh` and resolve all failures without weakening the public signing gate or product/privacy gates.
- [ ] T014 Run `infra/scripts/cd-remote.sh --dry-run`, verify the current public host/appcast state remains unchanged by this docs/validator slice, and update `docs/deployments/2brain-rec/release-v2026.07.26.6.md` with metadata-only evidence.
- [ ] T015 Re-run the Spec Kit consistency checks, confirm all checklists are complete, mark completed tasks `[X]`, and perform the final forbidden-active-path scan across `AGENTS.md`, `docs/`, `qa/`, `apps/macos/Installer/`, and active `specs/` files.

## Implementation Strategy

1. Land the two trust-boundary guards first (T001–T002).
2. Add tests and the manual bootstrap wrapper (T003, T006), then update active
   operator surfaces (T004–T005, T007–T011).
3. Run focused checks before repository CI; finish with dry-run deployment and
   evidence closeout (T012–T015).
4. The MVP is T001–T006: public Developer ID gate plus safe `.6` bootstrap.
   Documentation convergence and closeout are required before the feature is
   considered complete.
