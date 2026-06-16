# Contract: MVP Loop Readiness Report

Date: 2026-06-16

## Required Outputs

The feature produces the following committed outputs:

- `docs/evidence/034-mvp-loop-readiness/README.md`
- `docs/evidence/034-mvp-loop-readiness/readiness-report.json`
- `docs/evidence/034-mvp-loop-readiness/readiness-report.md`
- `docs/evidence/034-mvp-loop-readiness/launch-gap-register.md`
- `docs/evidence/034-mvp-loop-readiness/screenshots/` when screenshots are
  safe to commit

## Markdown Report Sections

`readiness-report.md` must include these sections in order:

1. `# MVP Loop Readiness`
2. `## Claim Summary`
3. `## MVP Loop Matrix`
4. `## Desktop App Evidence`
5. `## Web And Embedded Cabinet Evidence`
6. `## Access, Egress, Retention, And Deletion Truth`
7. `## Production Evidence`
8. `## Clean-Room Reference Comparison`
9. `## Forbidden Content Scan`
10. `## Launch Gap Register`
11. `## Next Slice Recommendation`

## Claim Summary Requirements

The claim summary must state:

- Current deployed commit when a production claim is made.
- Whether 034 proves `mvp_loop_ready`, proves only partial readiness, or blocks
  launch.
- Explicit exclusions, especially when evidence proves only
  `infra_smoke_ready`.
- P0/P1 blocker count.

## MVP Loop Matrix Requirements

The matrix must include at least these stages:

- local recording and visible stop;
- local artifact finalization and leakage gate;
- upload queue and server ingest;
- MediaScribe processing/import;
- meeting list;
- meeting detail transcript/playback/provenance;
- notes/action output availability;
- desktop embedded cabinet;
- access, sharing, download, export;
- retention/deletion/local purge truth;
- production deployment/smoke;
- product status and next-slice truth.

Each row must include:

- stage id;
- owner surface;
- status;
- evidence strength;
- evidence links;
- blocker/gap link or `none`;
- launch claim impact.

## Acceptance Summary

The acceptance summary can use only these final outcomes:

- `mvp_loop_ready`
- `internal_pilot_candidate`
- `partial_readiness`
- `pilot_blocked`
- `evidence_blocked`

The summary must not use a bare "ready" without the bounded outcome.
