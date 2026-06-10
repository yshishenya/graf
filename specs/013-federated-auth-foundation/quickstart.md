# Quickstart: Provider-Neutral Federated Auth Foundation (013)

## 1) Local Development Preconditions

Run the existing server stack and ensure `012` baseline is healthy before starting `013`:

```sh
cd /Users/yshishenya/.codex/worktrees/b395/019-live-route-stability
docker compose -f infra/docker-compose.dev.yml up --build
```

Expected:

- API reachable at `http://localhost:8080`.
- Postgres + MinIO healthy.
- Existing ingest endpoints still respond with their current auth checks.

## 2) Seed RU-local workspace policy fixture

Use the local seed path used by existing tests to create workspace/user/device rows.
Then add policy fixture directly in a small manual step:

- set `require_ru_local=true`
- enable at least one of `Yandex`, `VK`, `Telegram Login`
- keep `T-ID/SberID/MTSID/ESIA` disabled for now

Expected:

- `/api/v1/auth/providers?workspace_id=<workspace>` returns only enabled providers.
- provider and policy responses include active RU consent copy and version.

## 3) Start auth flow

For each provider in scope:

- call `POST /api/v1/auth/providers/{provider}/start`
- open returned `authorization_url` (real integration environment in staging/dev)
- complete provider consent

Expected:

- provider callback resolves to active user context.
- callback state/nonce is consumed exactly once.
- response/error codes are deterministic and safe.

## 4) Validate one-click and workspace policy behavior

For a workspace where only Yandex is enabled:

- verify `GET /api/v1/auth/providers` returns Yandex only.
- verify direct provider options for disabled adapters are not returned.

Expected:

- no disabled provider appears.
- session establishment still uses workspace policy.

## 5) Link second identity

As an authenticated session:

- attempt linking VK/Telegram from current `session` context.
- simulate confirmed match path (verified email/phone) and conflict path.

Expected:

- confirmed path creates one user with additional external identity.
- conflict path returns explicit non-destructive error and no account merge.

## 6) Register and revoke device

- call `/api/v1/auth/devices/register` from authenticated context
- call `/api/v1/auth/devices/<id>/revoke`
- retry protected endpoints with revoked device id.

Expected:

- revoked device cannot create or access sessions.
- active sessions bound to revoked device are denied within request.
- session-token ingest from an active but unbound device fails with `device_untrusted`.

## 7) Failure-state validation

Validate the following and record deterministic outcomes:

- callback with tampered state
- callback reuse attempt
- provider unavailable simulation
- revoked link attempt

Expected:

- each failure returns an explicit code from spec.
- each failure generates an auth audit record with safe metadata.

## 8) Log and audit validation

Run local API logs and grep checks for forbidden evidence markers:

```sh
docker compose -f infra/docker-compose.dev.yml logs api > /tmp/2brain-rec-api.log
```

Expected:

- no raw provider tokens,
- no bearer strings,
- no raw emails/phones beyond safe normalized fields if required by policy,
- no claim blobs in logs.

## 9) API contract validation

- Validate auth endpoint contracts against this feature contract list.
- Confirm 012 tenant-scoped endpoints still fail closed for missing auth context.

Expected:

- auth routes expose and enforce failure taxonomy.
- existing ingest routes still rely on valid tenant context until migration.

## 10) RU-local policy sanity check

- switch policy to non-RU mode and back (test workspace-level effect).
- verify provider list and consent text updates accordingly.

Expected:

- behavior changes are immediate and explicit in `GET /auth/providers` and `/auth/me` output.
- no cross-boundary write behavior is introduced when RU mode is enabled.

## 11) Validation Evidence Captured

### 2026-06-10

```sh
PYTHONPATH=apps/server/src pytest -q apps/server/tests/contract
PYTHONPATH=apps/server/src pytest -q apps/server/tests/integration
PYTHONPATH=apps/server/src pytest -q apps/server/tests
```

Observed:

- Contract suite: `29 passed in 1.28s`
- Integration suite: `85 passed in 5.86s`
- Full server tests: `184 passed in 7.22s`

Revalidated on 2026-06-10 after callback/audit fixes:

- Contract suite: `29 passed in 1.20s` (after callback parameter and TTL hardening)
- Integration suite: `85 passed in 5.23s` (same command set)
- Full server tests: `184 passed in 6.81s`

```sh
bash .specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks
```

Observed:

- `FEATURE_DIR=/Users/yshishenya/.codex/worktrees/b395/019-live-route-stability/specs/013-federated-auth-foundation`
- `AVAILABLE_DOCS=[research.md,data-model.md,contracts/,quickstart.md,tasks.md]`

```sh
python3 - <<'PY'
import json, re, subprocess

issues = json.loads(
    subprocess.check_output(
        ["gh", "issue", "list", "--label", "feature:013", "--state", "all", "--limit", "500", "--json", "title,state,number"],
        text=True,
    )
)
task_ids = {re.search(r"T\d{3}", i["title"]).group(0) for i in issues if re.search(r"T\d{3}", i["title"])}
open_tasks = {
    t for t in task_ids
    if any(
        i["state"] == "OPEN" and re.search(r"T\d{3}", i["title"]).group(0) == t
        for i in issues
        if re.search(r"T\d{3}", i["title"])
    )
}
print(f"mapped_task_ids={len(task_ids)}")
print(f"open_task_count={len(open_tasks)}")
PY
```

Observed:

- `mapped_task_ids=75`
- `open_task_count=0` (current state)

### 2026-06-10 (dedupe cleanup)

```sh
python3 - <<'PY'
import json
import re
import subprocess

issues = json.loads(
    subprocess.check_output(
        ["gh", "issue", "list", "--label", "feature:013", "--state", "all", "--limit", "400", "--json", "title,state,number"],
        text=True,
    )
)
task_ids = {}
for issue in issues:
    match = re.search(r"T\d{3}", issue["title"] or "")
    if match:
        task_ids.setdefault(match.group(0), []).append(issue)

open_task_count = sum(1 for items in task_ids.values() if any(i["state"] == "OPEN" for i in items))
mapped_task_ids = len(task_ids)
print(f"mapped_task_ids={mapped_task_ids}")
print(f"open_task_count={open_task_count}")
PY
```

Observed:

- Duplicated legacy open issues `#361..404` were closed as superseded by the latest sync artifacts.
- `mapped_task_ids=75`
- `open_task_count=0`

### 2026-06-11 (completion-audit hardening)

Fresh audit pass fixed these non-blocking but real requirement mismatches:

- public `GET /api/v1/auth/providers` now hides disabled providers; admin `/api/v1/auth/policy` keeps the full provider matrix.
- device registration returns `status=active` with `registration_state=approved`, matching the 013 data model and OpenAPI contract.
- revoked and quarantined devices now return deterministic `device_revoked` / `device_quarantined` denial codes before ingest actions.
- workspace auth policy updates now emit `workspace_auth_policy_updated` audit events with safe metadata.
- provider discovery and policy responses now include persisted RU consent copy, and provider start persists active consent copy before callback/link completion.
- session-bound ingest now requires a trusted device binding; otherwise it fails closed with `device_untrusted`.

```sh
specify --version
specify self check
bash .specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks
ruff check apps/server/src/twobrain_rec_server/api/auth.py apps/server/src/twobrain_rec_server/auth/dependencies.py apps/server/src/twobrain_rec_server/auth/policy.py apps/server/tests/contract/test_auth_contracts.py apps/server/tests/integration/test_tenant_authorization.py
PYTHONPATH=apps/server/src pytest -q apps/server/tests/contract/test_auth_contracts.py apps/server/tests/integration/test_tenant_authorization.py
PYTHONPATH=apps/server/src pytest -q apps/server/tests/contract/test_openapi_contract_drift.py::test_runtime_openapi_matches_committed_contract
PYTHONPATH=apps/server/src pytest -q apps/server/tests/contract apps/server/tests/integration
PYTHONPATH=apps/server/src pytest -q apps/server/tests
```

Observed:

- Spec Kit CLI: `specify 0.10.1`
- Spec Kit self-check: `Up to date: 0.10.1`
- Prerequisites: `AVAILABLE_DOCS=[research.md,data-model.md,contracts/,quickstart.md,tasks.md]`
- Ruff: clean after import ordering fix.
- Focused auth/tenant suite: `19 passed in 1.81s`
- OpenAPI drift test: `1 passed in 0.23s`
- Contract + integration suite: `116 passed in 8.91s`
- Full server tests: `186 passed in 7.87s`
- Task-to-issue sync: `tasks_total=75`, `mapped_task_ids=75`, `missing_count=0`, `open_task_ids=0`

### 2026-06-11 (review-remediation task and issue backfill)

Review findings were appended as Phase 11 remediation tasks in
`specs/013-federated-auth-foundation/tasks.md`.

GitHub issues created:

- `T076` -> `#498` forged provider callback tests (open)
- `T077` -> `#499` real provider verification boundary (open)
- `T078` -> `#500` workspace enrollment abuse tests (closed with evidence)
- `T079` -> `#501` workspace enrollment gate implementation (closed with evidence)
- `T080` -> `#502` RU-local write-boundary tests (open)
- `T081` -> `#503` RU-local auth write guard (open)
- `T082` -> `#504` audit metadata redaction tests (closed with evidence)
- `T083` -> `#505` audit metadata minimization (closed with evidence)
- `T084` -> `#506` no-write policy read tests (closed with evidence)
- `T085` -> `#507` side-effect-safe policy reads (closed with evidence)
- `T086` -> `#508` admin device revoke tests (closed with evidence)
- `T087` -> `#509` admin device revoke implementation/contract (closed with evidence)
- `T088` -> `#510` remediation mapping evidence (closed after Linear sync evidence)
- `T089` -> `#511` Spec Kit tooling split decision (open)

Validation commands run during this remediation pass:

```sh
python3 .specify/extensions/github-issue-canon/scripts/validate_issue_canon.py
PYTHONPATH=apps/server/src pytest apps/server/tests/contract/test_auth_contracts.py apps/server/tests/contract/test_openapi_contract_drift.py -q
PYTHONPATH=apps/server/src pytest apps/server/tests/integration/test_postgres_migrations.py -q
ruff check apps/server/src/twobrain_rec_server/api/auth.py apps/server/src/twobrain_rec_server/auth/callbacks.py apps/server/src/twobrain_rec_server/auth/policy.py apps/server/src/twobrain_rec_server/auth/audit.py apps/server/tests/contract/test_auth_contracts.py
python3 .specify/extensions/linear-sync/scripts/linear_sync.py sync --feature 013
```

Observed:

- GitHub issue canon: `OK`.
- Current task inventory before Linear evidence closure: `tasks_total=89`, `open_tasks=6`,
  `open_task_ids=T076,T080,T088,T077,T081,T089`.
- Remediation GitHub inventory before Linear evidence closure: 14 issues, open `#498,#499,#502,#503,#510,#511`.
- Focused auth/OpenAPI suite after remediation: `17 passed`.
- Postgres migration suite after `allow_provider_self_enrollment`: `3 passed`.
- Final focused auth/OpenAPI/tenant/migration suite: `32 passed`.
- Final full server test suite: `192 passed`.
- `git diff --check`: clean.
- Linear sync status: not applied. Dry-run reports `Без Linear issue: 89`; applying
  safely requires `.specify/linear.yml`/`LINEAR_API_KEY` and a filtered/imported
  mapping so the script does not create duplicate Linear issues for already
  completed historical tasks.

### 2026-06-11 (Linear remediation issue sync)

Linear API was applied only to remediation tasks `T076`-`T089`, not to the full
historical `T001`-`T075` task set. Team inferred from Linear workspace: `YSH`.

Created Linear issues:

| Task | GitHub | Linear | State |
|------|--------|--------|-------|
| T076 | #498 | YSH-96 | Done after provider verification regression tests |
| T077 | #499 | YSH-97 | Done after verified provider boundary implementation |
| T078 | #500 | YSH-98 | Done |
| T079 | #501 | YSH-99 | Done |
| T080 | #502 | YSH-100 | Done |
| T081 | #503 | YSH-101 | Done |
| T082 | #504 | YSH-102 | Done |
| T083 | #505 | YSH-103 | Done |
| T084 | #506 | YSH-104 | Done |
| T085 | #507 | YSH-105 | Done |
| T086 | #508 | YSH-106 | Done |
| T087 | #509 | YSH-107 | Done |
| T088 | #510 | YSH-108 | Todo at creation; moved to Done after this evidence was recorded |
| T089 | #511 | YSH-109 | Todo |

Current open remediation work after provider verification fixes:

- none

### 2026-06-11 (RU-local auth storage attestation)

Implemented deployment attestation guard for RU-local auth/session/device/audit
storage:

- production `Settings` now require `auth_storage_region_tag=ru`
- production `Settings` now require `auth_ru_local_storage_attested=true`
- `infra/env/rec.production.env.example` documents the operator attestation
- `apps/server/.env.example` documents the local/default fields without secrets

Validation:

```sh
PYTHONPATH=apps/server/src pytest apps/server/tests/unit/test_config_validation.py apps/server/tests/contract/test_secrets_env_contract.py -q
ruff check apps/server/src/twobrain_rec_server/config.py apps/server/tests/unit/test_config_validation.py apps/server/tests/contract/test_secrets_env_contract.py
```

Observed:

- Config/env validation: `19 passed`
- Affected production-docs/config/env subset after test fixture update: `21 passed`
- Final full server suite after RU-local attestation guard: `194 passed`
- Ruff: clean
- GitHub closed: `#502`, `#503`
- Linear moved to Done: `YSH-100`, `YSH-101`

### 2026-06-11 (provider callback verification remediation)

Implemented verified provider callback boundaries:

- Yandex callback now exchanges authorization code for an access token and reads
  profile from Yandex ID before creating the internal subject.
- VK callback now exchanges authorization code for access token and reads
  profile from VK API before creating the internal subject.
- Telegram callback now validates signed login payload with HMAC-SHA-256 and
  rejects expired `auth_date` payloads.
- Built-in provider adapters remain fail-closed when provider secret files are
  absent; deterministic direct-claim parsing is restricted to test adapters.

Validation:

```sh
PYTHONPATH=apps/server/src pytest apps/server/tests/contract/test_auth_contracts.py -q
ruff check apps/server/src/twobrain_rec_server/auth/providers/base.py apps/server/src/twobrain_rec_server/auth/callbacks.py apps/server/src/twobrain_rec_server/api/auth.py apps/server/tests/contract/test_auth_contracts.py apps/server/tests/fakes/auth_providers.py
```

Observed:

- Auth contract suite: `17 passed`
- Ruff: clean
- GitHub closed: `#498`, `#499`
- Linear moved to Done: `YSH-96`, `YSH-97`

### 2026-06-11 (Spec Kit tooling separation)

Separated Spec Kit local/tooling state from auth runtime review:

- `.gitignore` now treats `.specify/*` as local/runtime/tooling state.
- Existing tracked `.specify` files were removed from the git index with
  `git rm -r --cached .specify`; files remain present locally for Spec Kit use.
- Ignored untracked Linear-sync extension and workflow-run files no longer
  appear in normal `git status`.
- Feature 013 remediation tasks are now all mapped and completed; the remaining
  `.specify` changes are not part of the auth runtime diff.

Validation:

```sh
git check-ignore -v .specify/feature.json .specify/extensions/linear-sync/README.md
git status --short -- .specify
```

Observed:

- `.specify/*` ignore rule applies to local Spec Kit files.
- `.specify` is represented as staged index removals only, not auth runtime
  implementation changes.
- GitHub closed: `#511`
- Linear moved to Done: `YSH-109`

### 2026-06-11 (final pre-deploy local CI)

Regenerated the committed OpenAPI contract from the current FastAPI runtime and
ran the canonical local CI gate:

```sh
cd apps/server && PYTHONPATH=src uv run --extra dev python - <<'PY'
from pathlib import Path
import yaml
from twobrain_rec_server.config import Settings
from twobrain_rec_server.main import create_app
Path('../../specs/012-server-ingest-foundation/contracts/openapi.yaml').write_text(
    yaml.safe_dump(create_app(Settings()).openapi(), allow_unicode=True, sort_keys=False),
    encoding='utf-8',
)
PY
infra/scripts/ci-local.sh
```

Observed:

- Server tests: `196 passed`
- Server lint: `All checks passed!`
- Python compile: pass
- Production compose config: rendered successfully
- Deployment evidence scan: `deployment_evidence_scan=pass`
- `ci_local_result=pass`
