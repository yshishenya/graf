# Batch A: Server Cleanup

**Status**: validated
**Scope**: `apps/server/pyproject.toml`, `apps/server/constraints.txt`, `apps/server/uv.lock`, selected server runtime files, and focused test stubs.
**Runtime diff size after completing dependency metadata**: 29 files, 44 insertions, 92 deletions.
**Risk lane**: significant/high-risk cleanup, because the touched surfaces include auth, admin, cabinet, deletion lifecycle, support redaction, RLS reporting, upload/session tests, and dependency metadata.

## Summary

Batch A removes one unused runtime dependency and shrinks small local redundancies that static analysis found in server code. It deliberately avoids architectural movement, cabinet splitting, endpoint behavior changes, database schema changes, capture behavior, deployment behavior, and new dependencies.

## Removed Dependency

### `structlog`

Changed files:

- `apps/server/pyproject.toml`
- `apps/server/constraints.txt`
- `apps/server/uv.lock`

Decision: remove.

Evidence:

- `structlog` was declared in the server runtime dependency list.
- The package entry and server package requirement were present only in dependency metadata.
- Current server code uses the standard `logging` module and project-local reporting helpers for the touched surfaces.
- Removing it required only dependency metadata deletion; no runtime code import had to be changed.
- Active server/infra search after the removal leaves only historical specs as `structlog` mentions.

Validation requirement:

- Static import/reference search for `structlog`.
- Server lint and focused tests.
- Full repository local CI gate.

## Removed Internal Parameters And Calls

Decision: remove only parameters whose values were not read inside private or project-local call chains.

Changed areas:

- `admin/permissions.py`, `admin/users.py`, `admin/web.py`: removed `target_user_id` from the internal membership mutation decision path because the decision uses target role/status and last-owner counts, not the id value.
- `api/auth.py`: removed unused `request` parameters from provider/policy/me routes; FastAPI does not require the parameter when request data is not read.
- `api/cabinet.py`, `deletion/service.py`: removed the unused `db` parameter from `lifecycle_for_meeting`; lifecycle state is derived from the already-loaded `Meeting`.
- `cabinet/egress.py`: removed unused `action` keyword from `_policy_blocked_state` and its local callers.
- `cabinet/rendering.py`, `cabinet/web.py`: removed unused `workspace_id` and `active` plumbing from email-code/settings rendering helpers where the rendered template does not consume those values.
- `ingest/lifecycle.py`: removed unused `reason` parameter from lifecycle-blocking helper while retaining the existing audit events for abort/expire paths.

Validation requirement:

- Admin permission tests.
- Browser email-code/login tests.
- Cabinet view model tests.
- Deletion lifecycle route tests through server focused suite.
- Full server test gate.

## Local Expression Shrinks

Decision: keep only mechanical, behavior-preserving simplifications where the value domain is unchanged.

Changed areas:

- Membership/session/status checks: single-element set membership became direct equality.
- Browser cabinet path checks: repeated path comparisons became set/tuple membership.
- Safe label fallback: temporary variable became direct `or fallback`.
- RLS/readiness/support helpers: list-building loops became equivalent comprehensions or `extend`.
- Redaction prefix checks: repeated `startswith` calls became tuple-prefix `startswith`.
- Calendar datetime parsing: Python 3.13 `datetime.fromisoformat` handles ISO timestamps directly; timezone fallback remains unchanged for naive strings.

Validation requirement:

- Focused tests for changed helpers.
- Full server test gate.

## Test Stub Shrinks

Decision: rename intentionally ignored callback arguments or remove implicit `return None` only where test behavior stays identical.

Changed areas:

- Upload/session/RLS monkeypatch callbacks now use `_args`/`_kwargs`.
- App lifecycle monkeypatch lambdas mark ignored values with `_` prefixes.
- Decimal test fixtures use exact integer construction for whole-second values.
- `RecordingAsyncSession.get` relies on the async function default `None` return.

Validation requirement:

- The focused tests that own these stubs.
- Full server test gate.

## Explicitly Not In This Batch

- No cabinet presentation split.
- No auth/session behavior change.
- No deletion or retention semantics change.
- No MediaScribe, audio capture, macOS, Docker, release, or production deployment changes.
- No cleanup of pre-existing `.specify/*` template changes or generated `.agents/skills/*` files.

## Validation Evidence

Current validation, 2026-06-30:

- `rg -n "structlog" apps/server apps/macos infra scripts .specify AGENTS.md`: pass, no active matches.
- `cd apps/server && PYTHONPATH=src uv run --extra dev ruff check src tests`: pass, `All checks passed!`
- `cd apps/server && PYTHONPATH=src uv run --with vulture --extra dev vulture src tests --min-confidence 80`: pass, no findings printed.
- `find apps/server/src apps/server/tests apps/macos infra scripts -type f -name '*.js' -print0 | xargs -0 -n1 node --check`: pass, no syntax errors printed.
- `find apps/macos infra scripts .specify/scripts -type f -name '*.sh' -print0 | xargs -0 -n1 bash -n`: pass, no syntax errors printed.
- Focused Batch A pytest:

```text
cd apps/server && PYTHONPATH=src uv run --extra dev pytest -q tests/unit/test_admin_permissions.py tests/unit/test_app_lifecycle.py tests/unit/test_media_revision_persistence_order.py tests/unit/test_cabinet_view_models.py tests/unit/test_cabinet_web_shell.py tests/integration/test_minio_upload_storage.py tests/integration/test_recording_sync_conflicts.py tests/integration/test_rls_auth_conflict_handling.py tests/integration/test_web_owner_session_context.py::test_browser_email_login_wrong_code_consumes_state
=> 63 passed in 3.08s
```

- `infra/scripts/ci-local.sh`: pass, `987 passed, 4 skipped`, `deployment_evidence_scan=pass`, `ci_local_result=pass`.
- `cd apps/macos && swift test`: pass, `706 tests, 0 failures`.
- `git diff --check`: pass, no whitespace errors printed.
