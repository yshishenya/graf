# Batch B: Remove Unused Python Dev Dependency

**Status**: validated
**Scope**: `apps/server/pyproject.toml`, `apps/server/uv.lock`
**Risk lane**: significant/high-risk cleanup, handled as dependency-only server batch.

## Summary

Batch B removes the unused `httpx2` dev dependency and its lockfile-only transitive packages:

- `httpx2`
- `httpcore2`
- `truststore`

No runtime code, tests, scripts, or production configuration were changed.

## Evidence

Pre-removal evidence:

- `httpx2` was declared only in `[project.optional-dependencies].dev`.
- AST import scan over server source, tests, and scripts reported `httpx2=0`.
- Repository reference scan found `httpx2` only in dependency metadata and 071 audit notes.
- `uv tree --all-groups --depth 2` showed `httpx2` only as `(extra: dev)`.

Post-removal evidence:

- `rg -n "httpx2|httpcore2|truststore" apps/server/pyproject.toml apps/server/uv.lock apps/server/constraints.txt apps/server/src apps/server/tests apps/server/scripts infra scripts .specify AGENTS.md docs/agent-guidance`: pass, no matches.
- `cd apps/server && uv lock --check`: pass, `Resolved 53 packages in 5ms`.
- `cd apps/server && uv tree --all-groups --depth 1`: pass, direct dev deps are now `aiosqlite`, `pytest`, `pytest-asyncio`, and `ruff`.

## Validation

- `cd apps/server && PYTHONPATH=src uv run --extra dev ruff check src tests`: pass, `All checks passed!`
- Focused HTTP/auth/provider tests:

```text
cd apps/server && PYTHONPATH=src uv run --extra dev pytest -q tests/unit/test_mediascribe_request_mapping.py tests/unit/test_support_incident_github_issue_body.py tests/unit/test_email_login_delivery.py tests/unit/test_auth_web_session_context.py tests/contract/test_auth_contracts.py
=> 38 passed in 2.82s
```

- `infra/scripts/ci-local.sh`: pass, `987 passed, 4 skipped`, `deployment_evidence_scan=pass`, `ci_local_result=pass`.
- `git diff --check`: pass.

## Explicitly Not In This Batch

- No runtime dependency removal.
- No auth/provider interface changes.
- No code path changes.
- No production deploy or smoke.
