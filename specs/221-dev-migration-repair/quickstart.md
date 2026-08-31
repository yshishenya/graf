# Quickstart: migration repair rehearsal

Run from the Feature 221 worktree. These commands are intentionally bounded to
an isolated or temporary Dev target.

```sh
# 1. Confirm prerequisites and active feature
.specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks

# 2. Probe without mutation
python3 scripts/dev-migration-repair.py probe --target isolated-dev --output /tmp/f221-probe.json

# 3. Rehearse backup and restore on an isolated copy
python3 scripts/dev-migration-repair.py backup-restore --source isolated-dev --target isolated-restore --output /tmp/f221-restore.json

# 4. Prepare (do not self-approve) a decision
python3 scripts/dev-migration-repair.py decision --probe /tmp/f221-probe.json --restore /tmp/f221-restore.json --output /tmp/f221-decision.json

# 5. After reviewer approval only, execute Dev repair
python3 scripts/dev-migration-repair.py repair --decision /tmp/f221-decision.approved.json --output /tmp/f221-evidence.json

# 6. Validate governance and the active slice
python3 scripts/validate-agent-context.py
python3 scripts/validate-changelog-fragments.py
python3 scripts/validate-legacy-impact.py --feature specs/221-dev-migration-repair/spec.md
pytest -q tests/governance
infra/scripts/ci-local.sh --fast
```

If any command reports `blocked`, preserve the metadata record and stop. Do not
retry with `stamp`, manual pointer edits, `down -v`, or production credentials.
