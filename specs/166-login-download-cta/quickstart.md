# Quickstart: Контекстная ссылка на приложение на экране входа

## Prerequisites

- Repository root: `/Users/yshishenya/.codex/worktrees/899d/crisp`.
- Python environment available through the repository's `uv` setup.
- For visual checks, the local server or the configured local cabinet must be
  running; use synthetic/auth-free login page navigation only.

## Focused checks

```sh
cd apps/server
PYTHONPATH=src uv run --extra dev pytest -q \
  tests/unit/test_cabinet_web_shell.py \
  tests/integration/test_web_owner_session_context.py \
  tests/contract/test_account_routes.py
```

```sh
node --check apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js
git diff --check
```

## Browser visual matrix

Use the in-app browser and inspect `/login?next=/meetings` at 1440 px and
768 px. Confirm:

1. one CTA is visible in the lower-left area;
2. the auth card remains primary;
3. the link is keyboard reachable and its focus ring is visible;
4. an auth error does not hide or overlap the CTA, alert or legal copy;
5. at a narrow viewport the CTA wraps without horizontal overflow.

## Embedded visual matrix

Use the installed/local macOS app with `/login?next=/desktop/meetings` at a
wide and a narrow window. Confirm:

1. no download link or download copy is visible;
2. email/provider controls, error copy, terms and privacy remain visible;
3. no empty gap or broken placeholder suggests a missing action.

## Closeout gate

After the focused checks and visual review, run:

```sh
infra/scripts/ci-local.sh --fast
```

Record only command results and UI metadata here; never add email addresses,
auth codes, cookies, meeting content or private screenshots.
