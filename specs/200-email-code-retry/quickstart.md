# Quickstart: Повторный ввод email-кода

## Focused tests

From the repository root:

```sh
PYTHONPATH=apps/server/src pytest -q \
  apps/server/tests/integration/test_web_owner_session_context.py \
  -k 'email_login_wrong_code or email_signup_flow or email_login_rejects_relayed_code'

PYTHONPATH=apps/server/src pytest -q \
  apps/server/tests/contract/test_account_routes.py \
  apps/server/tests/contract/test_cabinet_static_assets_contract.py \
  -k 'email_code or code_slots'
```

Expected outcomes:

1. First wrong login code returns 400 with the code form still present.
2. Correct code after one or two wrong attempts returns the normal 303 and
   creates one session.
3. The third wrong attempt immediately shows the blocked recovery state; the
   next verification request is rate-limited, cannot create a session, and
   offers resend.
4. A new code can complete login within the existing resend limits.
5. Expiry, replay, browser binding, signup and account-linking protections stay
   covered by existing focused tests.

## Repository gate

```sh
infra/scripts/ci-local.sh --fast
```

No deploy, release preparation, or installed-app production smoke is included.

## Validation evidence (2026-08-25)

- Auth web integration (`-k 'email_login or email_signup'`): 23 passed.
- Forced-RLS email auth integration (`-k 'email_auth'`): 4 passed.
- Account-route/static contract checks (`-k 'email_code or code_slots'`): 3 passed.
- `infra/scripts/ci-local.sh --fast`: 1240 unit tests passed; lint and compile passed.
