# Foundation Green Phase

**Feature**: `099-review-m4a-normalization`

**Date**: 2026-07-14

**Tasks**: T005-T020

## Outcome

The shared normalization foundation is green before user-story work begins:

- durable job, attempt and backfill states use typed transitions, bounded
  in-cycle retry and automatic daily recovery after the initial long-term
  schedule;
- migration `0022` is additive, portable to SQLite, reversible and preserves
  existing unvalidated playback rows without trusting them;
- PostgreSQL proves one canonical playback artifact under concurrent publish,
  meeting-row serialization and force-RLS tenant isolation;
- the two normalization maintenance operations are exact, read-only boundaries
  for jobs/backfill inventory and cannot enumerate attempt rows;
- media execution is no-shell, file-protocol-only, output-bounded,
  cancellation-safe and process-group-terminated;
- canonical output requires AAC-LC, 48 kHz mono, fast-start non-fragmented BMFF,
  metadata removal, strict full decode and derivation-specific duration
  tolerance (50 ms copy/remux, 250 ms transcode/mix);
- immutable object keys, disk-backed verified transfers and exclusive safe copy
  preserve existing destinations on failure;
- the media runtime is non-root, read-only, capability-dropped, limited to one
  CPU, 1 GiB, 128 PIDs and worker concurrency one.

## Focused suite

Run against a disposable PostgreSQL 17 container from `apps/server`:

```text
RLS_TEST_DATABASE_URL=<disposable local database> uv run --extra dev pytest -q \
  <normalization unit, contract, migration, PostgreSQL/RLS, config and compose filters>
```

Result:

- `178 passed`;
- one pre-existing Starlette/httpx deprecation warning;
- exit code `0`;
- disposable PostgreSQL container removed after the run.

The PostgreSQL subset independently reported `11 passed` and exercised the
real probe role, concurrent partial uniqueness, row locks, force-RLS flags,
cross-workspace denial and narrow maintenance policies. It also exposed and
fixed a test-harness bug where SQLAlchemy's safe URL rendering had replaced the
one-time probe password with `***`.

## Static and runtime gates

```text
uv run --extra dev ruff check src tests
docker compose -f infra/docker-compose.yml config --quiet
docker compose -f infra/docker-compose.yml -f infra/docker-compose.dev.yml config --quiet
git diff --check
```

All returned exit code `0`.

The media-only Docker target was built from `infra/server/Dockerfile`, then run
with an explicit probe that proved:

- the runtime UID is non-root;
- `ffmpeg` and `ffprobe` are executable;
- the private work directory is writable by the runtime user.

The proof image was removed. A final Docker inventory showed no remaining
`crisp-099-*` validation containers or proof image.

## Scope truth

- This receipt proves only the reusable T005-T020 foundation. It does not claim
  end-to-end playback, backfill, deletion, browser or production readiness.
- Feature 097 and its standalone Codex Security scan were not touched.
- No implementation commit, PR, release, deploy or production mutation was
  performed.
