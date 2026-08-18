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

## Validation evidence (2026-08-18)

- Unit render regression: `2 passed, 75 deselected` for the two login CTA tests.
- Integration render regression: `2 passed, 43 deselected` for browser login and
  embedded auth-error login, using the isolated PostgreSQL test runner; the
  container was removed after the run.
- Account-route contract suite: `18 passed`; the broader focused unit/contract
  selection also passed. The initial combined integration command without the
  disposable database was not counted as evidence because it produced setup
  errors.
- Static checks: `node --check .../cabinet.js` and `git diff --check` passed.
- Web visual metadata: at the available wide browser viewport (`1280×720`) one
  CTA rendered at the lower left without horizontal overflow; at `768×900` the
  panel-to-CTA gap was about 7 px and CTA-to-legal gap 8 px; at `320×900` the
  CTA wrapped to two lines with 12 px/8 px vertical gaps and no overflow.
- Web auth-error metadata: one CTA remained visible, the alert stayed above it,
  and legal copy remained below it without overlap.
- Embedded visual metadata: wide (`1018×818` available viewport) and narrow
  (`654×818`) auth-error views contained zero `/download` links or download
  copy while email, provider controls, error, terms and privacy remained
  visible; no horizontal overflow was observed.
- The global existing `a:focus-visible` rule and the semantic link name
  `Скачать приложение GRAF` were present in the rendered web surface.
- Closeout fast lane: `infra/scripts/ci-local.sh --fast` passed with 1103 unit
  tests, lint and Python compile; no full CI or production deploy was run for
  this release-train slice.
