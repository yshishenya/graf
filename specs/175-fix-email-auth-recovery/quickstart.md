# Quickstart: email auth recovery hotfix

## Preconditions

- Use only the disposable PostgreSQL container created by the repository test script.
- Do not run merge/repair commands against production accounts.
- Keep Docker Desktop available for forced-RLS checks.

## Focused scenarios

1. Existing email user: start → valid code → `303`, cookie, usable session and
   callback `completed` under the app role.
2. Wrong/expired/replayed code and injected completion/response failure: no
   second or orphan session; callback and audit finish in allowed contexts and
   the transaction is all-or-nothing.
3. Early and late ambiguous email: localized explanation plus active Яндекс
   ID/VK actions in web and embedded-safe next path; no session and no account selection.
4. Authenticated email link: 0/1/>1 other users produce link/preview/ambiguity;
   an empty other account still requires preview and explicit confirm.
5. Merge terminal paths: preview, blocked, completed and error restore exact
   callback access after merge context.
6. OAuth provider-link conflict: terminal link-state update succeeds after
   merge context without broad RLS access.
7. Existing Яндекс ID and VK login contract remains green.
8. Embedded email verify/resend/back and merge preview/confirm/cancel remain on
   `/desktop/...`; preview clearly explains survivor and preserved consequences.

## Commands

```sh
cd /Users/yshishenya/.codex/worktrees/auth-hotfix-175
apps/server/scripts/run_local_postgres_tests.sh --focused \
  tests/integration/test_web_owner_session_context.py \
  tests/integration/test_account_merge.py \
  tests/integration/test_rls_postgres_policies.py -k 'email_auth or email_link or provider_link'

cd apps/server
uv run --extra dev ruff check \
  src/twobrain_rec_server/cabinet/web_routes/auth.py \
  src/twobrain_rec_server/cabinet/web_routes/auth_email_flow.py \
  src/twobrain_rec_server/auth/provider_links.py \
  tests/integration/test_web_owner_session_context.py \
  tests/integration/test_account_merge.py \
  tests/integration/test_rls_postgres_policies.py

cd ../..
infra/scripts/ci-local.sh --fast
```

Before production, prepare the hotfix CalVer candidate, run
`infra/scripts/cd-remote.sh --dry-run --branch <release-branch>`, review the
exact SHA and rollback plan, and obtain explicit approval before `--execute`.
