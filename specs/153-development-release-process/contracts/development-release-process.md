# Contract: Development-To-Release Process

| Stage | Required evidence | Release authority |
| --- | --- | --- |
| Local edit | focused check | none |
| Ready slice / PR | feature quickstart + `ci-local.sh --fast` | PR/merge review |
| Release preparation | CalVer metadata and changelog reviewed and committed | release approval |
| Release candidate | `ci-local.sh --full` for exact SHA | release approval |
| Production execute | dry-run, explicit approval, repeated full gate, smoke/rollback | production gate |

Rules:

1. A fast or focused run is never full-CI evidence.
2. Any change after full CI invalidates that candidate result.
3. Production deploy is tied to a pinned SHA, not a moving branch reference.
4. `--skip-local-ci` is incident-only and requires explicit risk acceptance.
