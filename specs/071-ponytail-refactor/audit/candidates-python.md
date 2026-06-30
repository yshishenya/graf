# Python Candidates

**Date**: 2026-06-30
**Scope**: server source, tests, scripts, and Python dependency metadata.

## Static Checks

- Default Ruff: pass.
- Vulture at `--min-confidence 80`: pass, no findings.
- Vulture at `--min-confidence 70`: pass, no findings.
- Extended Ruff `ARG`: 6 findings, all in provider adapter callback signatures.

## Approved Candidate

### PY-DEP-001: Remove `httpx2` dev dependency

Location:

- `apps/server/pyproject.toml`
- `apps/server/uv.lock`

Evidence:

- `httpx2` is a direct dev extra in `pyproject.toml`.
- `uv tree --all-groups --depth 2` resolves it only as `(extra: dev)`.
- AST import scan reports `httpx2=0`.
- Repository reference scan finds `httpx2` only in dependency metadata and 071 audit notes.
- Existing tests use `httpx`, not `httpx2`.

Decision: completed in Batch B.

Validation requirement:

- Removed from `pyproject.toml` and `uv.lock`.
- Removed lockfile-only transitive packages `httpcore2` and `truststore`.
- Validated by server Ruff, focused HTTP/auth/provider tests, and `infra/scripts/ci-local.sh`.

## Retained Candidates

### PY-ARG-001: Provider adapter callback signature parameters

Location:

- `apps/server/src/twobrain_rec_server/auth/providers/base.py`

Findings:

- `credentials`, `http_client`, and `now` are unused in some base/subclass implementations.
- Other subclasses use the same method signature to perform OAuth/token/profile verification.

Decision: retain.

Reason:

- The parameters are part of the shared provider adapter contract.
- Removing them from only the implementations where they are unused would either break polymorphism or require a broader auth-provider interface change.
- Auth provider callback verification is a security boundary and must not be shrunk opportunistically.

Upgrade path:

- A later auth-provider interface cleanup may split direct-claims providers from network-verified providers, with focused auth contract tests and callback flow validation.

## No Current Python Code Removal

No additional Python source/test deletion is approved from current static analysis. Large files and presentation modules are tracked in cabinet-specific candidate notes instead of being removed by generic unused-code rules.
