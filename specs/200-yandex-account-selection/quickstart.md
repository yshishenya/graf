# Quickstart: Yandex ID account selection

## Focused automated validation

```sh
cd apps/server
uv run --extra dev pytest -q tests/integration/test_web_owner_session_context.py -k 'yandex_login_start or yandex_callback'
```

Expected: Yandex authorization URLs contain `force_confirm=1`; VK URLs do not
gain the parameter; existing callback state tests pass.

Automated result (2026-08-25): PASS. The focused PostgreSQL harness ran
`test_browser_yandex_login_start_redirects_to_provider` and
`test_browser_yandex_callback_rejects_missing_browser_state_cookie`; both
passed. The paired VK redirect isolation test also passed. Repository fast
lane passed with 1240 unit tests, lint, and Python compile. The API provider
start contract also passed with the same Yandex parameter assertion.

## Manual provider validation

1. Use a clean browser context or the installed app's browser login surface.
2. Make two Yandex ID accounts available to the same provider session.
3. Open `/login/yandex/start?next=/meetings`.
4. Verify Yandex shows an interactive account/login step instead of silently
   using the previously active account.
5. Select account A and verify GRAF opens account A's profile.
6. Repeat with account B and verify GRAF opens account B's profile.
7. Cancel the provider flow and verify no new GRAF session is issued.

Do not record account identifiers, email addresses, phone numbers, OAuth codes,
tokens, cookies, or raw provider profile data in evidence.

## Repository validation

Before a PR for this auth slice, run:

```sh
infra/scripts/ci-local.sh --fast
```

This task does not authorize a commit, PR, release, or production deploy.
