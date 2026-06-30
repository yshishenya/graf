# Baseline Validation

**Date**: 2026-06-30
**Scope**: 071 kickoff baseline for Batch A and future Ponytail audit batches.

## Commands

```text
rg -n "structlog" apps/server apps/macos infra scripts .specify AGENTS.md
```

Result: pass. No active code, script, infra, or guidance references remain after removing `structlog` from server dependency metadata.

```text
cd apps/server && PYTHONPATH=src uv run --extra dev ruff check src tests
```

Result: pass. Output: `All checks passed!`

```text
cd apps/server && PYTHONPATH=src uv run --with vulture --extra dev vulture src tests --min-confidence 80
```

Result: pass. No findings printed at the configured threshold.

```text
find apps/server/src apps/server/tests apps/macos infra scripts -type f -name '*.js' -print0 | xargs -0 -n1 node --check
```

Result: pass. No syntax errors printed.

```text
find apps/macos infra scripts .specify/scripts -type f -name '*.sh' -print0 | xargs -0 -n1 bash -n
```

Result: pass. No syntax errors printed.

```text
git diff --check
```

Result: pass. No whitespace errors printed.

## Baseline Notes

- Historical specs still mention `structlog`; those are not active runtime dependency declarations and are read-only under this feature unless a later documentation cleanup task scopes them.
- The static checks are candidate inputs only. Future deletion still requires caller/runtime evidence plus focused validation.
