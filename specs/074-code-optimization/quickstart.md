# Quickstart: Code Optimization

Run from the repository root.

## Baseline

```sh
python3 - <<'PY'
from pathlib import Path
roots=[Path('apps/server/src'),Path('apps/macos'),Path('infra'),Path('scripts')]
exts={'.py':'python','.swift':'swift','.sh':'shell'}
counts={k:0 for k in exts.values()}
for root in roots:
    if not root.exists():
        continue
    for p in root.rglob('*'):
        if p.is_file() and p.suffix in exts and '.venv' not in p.parts:
            counts[exts[p.suffix]] += len(p.read_text(errors='ignore').splitlines())
print(counts)
PY
```

## Candidate Evidence

For each candidate, record exact searches. Example:

```sh
rg -n "candidate_symbol" apps/server/src apps/server/tests apps/macos infra scripts
```

If a candidate is a route, script entrypoint, template helper, Docker command,
SwiftPM target, or package-level import, inspect that registration path before
classification.

## Focused Validation

Choose the smallest relevant focused command for touched paths, for example:

```sh
uv --project apps/server run --extra dev pytest -q apps/server/tests/unit
uv --project apps/server run --extra dev pytest -q apps/server/tests/integration
swift test --package-path apps/macos/Shared
```

## Closeout Validation

```sh
git diff --check
infra/scripts/ci-local.sh
```

## Required PR Evidence

- Runtime LOC before/after and net delta
- Dependency delta
- Removed or shrunk candidates
- Kept intentionally candidates
- Deferred risky candidates
- Focused checks and repository gate results
