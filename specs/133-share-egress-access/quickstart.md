# Quickstart: полный пакет внешнего приглашения

Risk lane: `high-risk-feature`.

## Focused checks

Run from the repository root with the server test environment:

```sh
pytest -q apps/server/tests/integration/test_recording_share_public_link.py \
  -k 'external_full_invitation or summary_only'
pytest -q apps/server/tests/integration/test_cabinet_playback_route.py \
  apps/server/tests/integration/test_transcript_export_egress.py
python -m compileall -q apps/server/src apps/server/tests
git diff --check
```

The focused invitation test must cover metadata-only assertions for:

- successful shared page;
- playback and audio download;
- transcript download;
- advertised transcript/summary/combined formats;
- at least one transcript, summary and combined export;
- revoke denial for page and egress;
- no workspace membership.

## Closeout checks

```sh
ruff check apps/server/src/twobrain_rec_server/cabinet/egress.py \
  apps/server/src/twobrain_rec_server/api/cabinet.py \
  apps/server/tests/integration/test_recording_share_public_link.py
infra/scripts/ci-local.sh
```

Record only pass/fail, test names, counts, commit/PR/issue references and
deployment status. Do not record meeting titles, transcript fragments, emails,
tokens, audio bytes, storage keys or signed URLs.

Production release remains a separate approval gate: after validation use the
release procedure, Developer ID macOS checks, `cd-remote.sh --dry-run`, then
execute/deploy only with explicit approval.

## Focused evidence (2026-07-27)

- `run_local_postgres_tests.sh` focused run: **56 passed**, 2 existing warnings;
  covered invitation, playback and transcript-export integration files.
- Targeted Ruff: **pass** for changed server and integration files.
- Python compileall: **pass**.
- `git diff --check`: **pass**.

## Full CI evidence (2026-07-27)

- `GRAF_TEST_WORKERS=4 bash infra/scripts/ci-local.sh`: **pass**;
  `ci_local_result=pass`.
- macOS: **642 passed**, ContractValidation **pass**.
- Server parallel phase: **2456 passed**, 1 skipped, 11 existing warnings.
- Server strict RLS phase: **42 passed**, 1 skipped, 2 existing warnings.
- Server lint and Python compile: **pass**.
- RLS hardening boundary: expected local-only `blocked` result because no
  production database was supplied; no live production probe was attempted.
- Production compose config and deployment evidence scan: **pass**.

An earlier single-worker retry ended with environment SIGKILL (code 137) at
29%; it is not used as release evidence. The repository-standard four-worker
run above completed successfully.
