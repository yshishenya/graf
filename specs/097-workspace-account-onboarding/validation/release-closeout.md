# Release closeout: Workspace Account Onboarding

This is a metadata-only closeout receipt. It contains no credentials, tokens,
invitation values, private meeting content, raw recordings or production
identifiers.

## Release and ancestry

- Feature PR: [#3842](https://github.com/yshishenya/crisp/pull/3842).
- Merge commit in `master`: `d79f24a9b91a739e90826a5e51659614628b62d1`.
- Release: [`v2026.07.18.1`](https://github.com/yshishenya/crisp/releases/tag/v2026.07.18.1).
- Release-preparation and deployed SHA: `2e94cd76a716c46238a67a65ec9f83bd7381f8b6`.
- Deployed Alembic head: `0028_active_space_read`.

## Gates and production evidence

- `infra/scripts/cd-remote.sh --dry-run`: pass.
- `infra/scripts/cd-remote.sh --execute`: pass.
- Canonical local gate inside the deploy: `ci_local_result=pass`; 572 macOS
  tests passed; the PostgreSQL runner passed 1,830 tests plus one skip in the
  parallel phase and 34 tests plus one skip in the strict RLS phase; Ruff,
  compilation, Compose rendering and deployment-evidence scan passed.
- Backup and restore rehearsal: pass. No rollback was executed; the guarded
  rollback path remains available.
- Runtime database identity, migration, Temporal/processing readiness,
  dispatch controls, media-worker boundary and public live/ready probes: pass.
- Metadata-only production upload/auth smoke and cleanup: pass with no
  remaining smoke artifacts.
- Disposable PostgreSQL/RLS verification: pass. A live destructive production
  RLS probe was not run and is not claimed.

## User-path receipt

After deploy, a bounded metadata-only production smoke used a disposable
internal identity and a temporary corporate invitation. It verified, through
the deployed HTTP routes and session boundary:

- personal-space offer listing;
- explicit identity-matched invitation acceptance;
- listing of personal and corporate spaces;
- server-verified switch into the corporate space;
- corporate membership revocation;
- blocked access for the revoked corporate session; and
- a fresh personal session that listed only the personal space.

The smoke ended with cleanup `residue=0`. It did not use a real mailbox or
claim external email-delivery proof; it validates the deployed onboarding,
invitation, switch and revocation semantics without exposing private data.

## Legacy cleanup boundary

- Active server runtime, server tests, server scripts and deploy helpers contain
  no SQLite or `aiosqlite` runtime path, URL, dependency or dialect branch.
- Historical Alembic/ADR text mentioning SQLite is retained as an audit record;
  it is not executable runtime support.
- The macOS permission-retention helper's `sqlite3` invocation reads the
  operating system TCC database and is required for permission-retention
  validation; it is not an application database.
- The auth bootstrap context, read-only legacy classification command, old app
  alias cleanup and legacy environment-name fallbacks are bounded compatibility
  anchors. They are not dead code and were intentionally not deleted or used
  for new public enrollment.
- No legacy records, memberships or recordings were moved or deleted.

## Verdict

Release, merge, deploy, migration, infrastructure and bounded production
user-path closeout are complete. The standalone Codex Security scan was
skipped by explicit user instruction and is not represented as a security
result.
