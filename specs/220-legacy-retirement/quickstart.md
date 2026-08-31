# Feature 220 Quickstart

This quickstart is metadata-only. It does not touch production, the existing Dev volume or user content.

## Preconditions

```sh
git status --short --branch
git rev-parse HEAD
python3 scripts/validate-agent-context.py
```

The active pointer must identify Feature 220 and the exact current SHA.

## Specification and inventory checks

```sh
python3 scripts/check-development-process.py --self-test
```

When the inventory adapter/fixture exists, verify repeated runs on one SHA have the same digest, every contour has owner/risk/classification/evidence, output contains no user rows/audio/transcripts/credentials, and a changed SHA is reported stale.

## Slice safety checks

For migration, Temporal or Sparkle contours, run only the isolated fixture/rehearsal documented by the child feature. Do not use the existing drifted volume and do not run `alembic stamp`, manual pointer edits or destructive reset.

## Repository gate

```sh
PYTHONDONTWRITEBYTECODE=1 pytest -q tests/governance
infra/scripts/ci-local.sh --fast
```

Expected result: governance tests pass, evidence is bound to the exact SHA, and the lane remains `fast` with `next_gate=full_before_release`.
