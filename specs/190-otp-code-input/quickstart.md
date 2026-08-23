# Quickstart: Единый ввод одноразового кода

## Focused checks

```sh
cd apps/server
PYTHONPATH=src uv run --extra dev pytest -q \
  tests/contract/test_account_merge_contract.py \
  tests/contract/test_account_routes.py \
  tests/contract/test_cabinet_static_assets_contract.py \
  tests/integration/test_web_owner_session_context.py
```

The checks must cover login, signup, invitation, browser link, and desktop
link rendering, six slots, hidden `code`, and the shared JS/CSS contract.

## Runtime smoke

1. Start the canonical local server with `sh infra/scripts/start-local.sh`.
2. Open the email-code page from web login and inspect a desktop viewport and
   a 390px viewport.
3. Repeat from the macOS embedded cabinet account-link route.
4. Type one digit per slot, paste mixed text, use Backspace/arrows, and submit
   a synthetic local code. Confirm the existing route receives one `code` value.
5. Do not store real email addresses, codes, tokens, or private content in
   screenshots or evidence.

## Repository gate

```sh
infra/scripts/ci-local.sh --fast
```

No production deploy or release validation is part of this slice.
