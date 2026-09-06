# Финальный анализ Feature 211

## Follow-up 2026-08-31

Production feedback showed that the conservative v1 classification made most
real server and infrastructure diffs run full despite an explicit `--fast`.
The follow-up contract supersedes only that classification rule: fast remains
bounded and reports `full_before_release`; the authoritative exact-SHA full and
all production gates remain unchanged. The original release analysis below is
retained as historical evidence for PR #6004.

**Дата**: 2026-08-30
**Lane**: high-risk infrastructure / validation governance / production deploy
**Статус**: PR #6004; production rollout explicitly approved by the user.

## Spec Kit consistency

- FR-001–FR-004: explicit lanes, conservative component union/escalation,
  timing and failure contracts.
- FR-005–FR-008: clean → remote sync → authoritative full → unchanged remote
  gates; no locally reusable attestation.
- FR-009: only the shared-host p95 threshold may be report-only; setup,
  database and functional failures remain hard.
- FR-010–FR-012: active docs/code consistency with historical evidence left
  unchanged.
- FR-013–FR-014: batching remains guidance; immutable-image delivery remains a
  separate slice.

Unresolved CRITICAL/HIGH requirements or constitution conflicts: `0`.

## Root-cause and minimality audit

The initial design attempted to reuse a local JSON full-CI receipt. Review showed
that a file and its stage journal have no independent provenance against another
process running as the same user. More validation fields did not fix that trust
boundary. The final design deletes the helper and its tests instead of claiming
attestation it cannot provide.

The normal production path is now:

```text
focused → component-aware fast → review/merge → dry-run → execute
execute: clean master → exact origin/master SHA → one full → remote gates
```

A direct full before execute is diagnostic only and intentionally repeats.
`--skip-local-ci` remains incident-only. Backup/restore, migrations/RLS,
secrets, readiness, smoke, cleanup, deploy lock, public health and guarded
rollback remain in the unchanged remote runtime script.

## Evidence already obtained

- pre-change full baseline: `1406.36s`;
- component-only server fast runs: `86s`, `71s`, `70s`; p50 `71s`;
- last complete implementation full before the final simplification: macOS
  `769/769`, server `3760 passed, 1 skipped`, performance `1 passed`, strict RLS
  `52 passed, 1 skipped`;
- follow-up focused contracts before deleting receipt: `52 passed`;
- automated review findings on performance semantics, high-risk path
  classification, diff failure propagation and deploy evidence escalation were
  incorporated.

The frozen post-review candidate still requires focused checks and the normal
authoritative full inside production execute. Those results belong in PR and
deployment evidence because adding them to this commit would change the exact
candidate after validation.

## Conclusion

The executable contract and active documentation describe the same process.
The optimization removes repeated full runs for small changes and makes the
single production full explicit without weakening any independent production
gate.
