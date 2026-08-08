# Tasks: Надёжное принятие invitation magic-link

**Input**: Design documents from `/specs/129-share-magic-rls/`

**Prerequisites**: `spec.md`, `plan.md`, `research.md`, `data-model.md`,
`contracts/invitation-magic-link.md`, `quickstart.md`, security/infra checklists

**Risk lane**: high-risk-feature; tests precede implementation and full local
CI plus guarded production deploy are required.

## Phase 1: Regression-first foundation

**Purpose**: Capture the production failure and protect existing authorization
boundaries before changing runtime code.

- [X] T001 [P] [US1] Добавить contract assertions для personal/source workspace
  context boundary, audit flush ordering и сохранения RLS policy в
  `apps/server/tests/contract/test_recording_share_invitation_contract.py`
- [X] T002 [US1] Добавить integration/strict-RLS regression для first-entry
  external magic-link acceptance с новым recipient identity, pending auth audit
  row, context switch и rate-limit query в
  `apps/server/tests/integration/test_recording_share_public_link.py` и
  `apps/server/tests/integration/test_rls_postgres_policies.py`
- [X] T003 [P] [US2] Сохранить regression assertions для existing identity,
  replay/wrong-recipient, expiry/revoke и notification-failure isolation в
  `apps/server/tests/integration/test_recording_share_public_link.py` и
  `apps/server/tests/contract/test_recording_share_invitation_contract.py`

**Checkpoint**: Новый тест воспроизводит 500 до implementation; существующие
identity/replay/notification security cases остаются явно покрыты.

## Phase 2: Minimal runtime fix and cleanup

**Purpose**: Fix the transaction boundary without weakening RLS and remove only
proven dead/duplicate code.

- [X] T004 [US1] Исправить flush ordering после `_record_email_login_audit` в
  `apps/server/src/twobrain_rec_server/cabinet/web_routes/browser.py`, чтобы
  audit row записывался под personal workspace context до переключения на
  source invitation workspace; сохранить CSRF, exact-recipient и grant flow
- [X] T005 [US2] Проверить всех callers `enforce_share_rate_limit`,
  `apply_tenant_context`, `_record_email_login_audit` и
  `_dispatch_account_created_email`; удалить только доказанно недостижимый или
  дублирующий код в `apps/server/src/twobrain_rec_server/cabinet/` и
  `apps/server/src/twobrain_rec_server/auth/`, либо зафиксировать evidence,
  что cleanup не требуется
- [X] T006 [US2] Сохранить bounded post-commit notification handling и обновить
  source/contract checks в
  `apps/server/tests/contract/test_recording_share_invitation_contract.py`,
  чтобы secondary workflow failure не возвращал HTTP 500 после успешного commit

**Checkpoint**: Focused first-entry, existing-account, replay, revoke/expiry и
notification tests проходят; RLS policy и production security boundaries не
ослаблены.

## Phase 3: Evidence and release readiness

**Purpose**: Make the hotfix reviewable, releasable and operable.

- [X] T007 [P] [US3] Обновить metadata-only quickstart/evidence, Russian
  changelog и current product status в `specs/129-share-magic-rls/quickstart.md`,
  `CHANGELOG.md` и `docs/current-product-status.md` после validation
- [X] T008 [US3] Выполнить `git diff --check`, targeted Ruff/compile, focused
  isolated-Postgres matrix и полный `infra/scripts/ci-local.sh`; зафиксировать
  security/infra checklist status и Ponytail/code review evidence
- [X] T009 [US3] Подготовить CalVer release notes, macOS candidate/update
  continuity smoke, public artifact checks и guarded deploy evidence в
  `docs/releases/`, `docs/deployments/2brain-rec/` и release assets без raw
  meeting content

## Dependencies & Execution Order

### Phase Dependencies

- Phase 1 has no implementation dependency and must precede Phase 2.
- Phase 2 depends on T001–T003 and must pass its checkpoint before release work.
- Phase 3 depends on validated implementation and is required before PR closeout.

### User Story Dependencies

- US1 (T001, T002, T004) is the P1 hotfix and blocks release.
- US2 (T003, T005, T006) depends on the shared context fix but must remain
  independently testable.
- US3 (T007–T009) depends on the completed implementation and validation.

### Parallel Opportunities

- T001 and T003 can proceed in parallel because they start in different test
  sections, but T002 must own the integration fixture before implementation.
- T007 can be prepared in parallel with final review after T004–T006 pass.

## Implementation Strategy

1. Write and run T001–T003; confirm the new integration regression fails for the
   known RLS autoflush failure.
2. Implement T004 with the smallest existing-session flush boundary.
3. Complete T005 caller/cleanup review and T006 notification regression.
4. Run the focused checkpoint, then full local CI and security/infra review.
5. Complete release/build/update/deploy gates only after explicit approval.
