# Deployment dry-run

The metadata-only production dry-run passed on 2026-08-21 for branch `codex/179-production-landing-refresh`.

- target: `2brain.dev:/opt/projects/2brain-rec`;
- authoritative execution lane: full exact-SHA local CI;
- guarded sequence: clean/synchronized branch, pinned SHA, backup and restore rehearsal, secret and Compose checks, migration, runtime identity, worker readiness, production smoke, automatic dispatch gate and guarded rollback;
- execute state: not authorized and not run.

This preliminary dry-run validates the deployment path only. It must be repeated against the clean pushed release candidate after implementation commit approval and before the separate production execute approval.
