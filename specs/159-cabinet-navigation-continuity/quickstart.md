# Quickstart: проверка непрерывной навигации кабинета

Run commands from the repository root unless noted. Use only synthetic test
fixtures and metadata-only evidence; do not use production credentials,
meetings, audio, transcripts, tokens or private screenshots.

## Focused source and contract checks

```sh
cd apps/server
PYTHONPATH=src uv run --extra dev pytest -q \
  tests/unit/test_cabinet_web_shell.py \
  tests/contract/test_cabinet_static_assets_contract.py \
  tests/contract/test_account_routes.py \
  tests/integration/test_web_owner_session_context.py
cd ../..
node --check apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js
git diff --check
```

If integration tests require PostgreSQL, run them through the disposable local
runner and remove the container after the run:

```sh
bash apps/server/scripts/run_local_postgres_tests.sh \
  --focused tests/integration/test_settings_ia_flow.py
```

## Synthetic browser/embedded matrix

Render or inspect the existing credential-free harness for:

- `/meetings` and one meeting-detail route;
- `/settings`, every existing category, and calendar settings;
- browser and `/desktop` variants;
- 1280×720 and 390×844;
- light/dark, keyboard focus, reduced motion, empty/missing profile values,
  long Russian search and repeated partial initialization.

Expected evidence:

1. One shared toggle has truthful action label, `aria-expanded` and focus
   retention in both states.
2. Search icon is decorative, text has separate spacing, and the document has no
   horizontal overflow.
3. Browser shell has exactly one `/download` sidebar CTA; embedded shell has
   zero sidebar download CTAs.
4. Profile menu exposes only safe name/email, Настройки and Выйти; Escape,
   outside click and focus return work without duplicate handlers.
5. Every settings route has one accessible primary rail, one selected category
   and a canonical «К встречам» link.
6. Auth matrix preserves unknown-email rejection, explicit signup/invitation/
   provider/email-code paths, CSRF and safe same-origin return behavior.

## Closeout gate

```sh
infra/scripts/ci-local.sh --fast
```

Record the exact commit SHA, command, result and any concrete environment
limitation. This slice has no production deploy, public release or native
macOS-shell approval gate.

## Recorded run

- Implementation SHA: `34f234490f55fe7d5f0ffe3d7da4335cb558d4c9`.
- Focused contracts: 133 passed; `node --check`; `git diff --check`.
- Disposable PostgreSQL runner: 48 passed across settings IA and web owner
  session/auth parity; isolated container removed.
- Synthetic Playwright Chromium matrix: browser/embedded toggle, profile,
  download, settings rail and 390×844 overflow checks passed. The browser
  matrix used synthetic render functions and no credentials or private content.
- Fast lane: 1100 passed, lint PASS, Python compile PASS, legacy-audio guard
  PASS. Two existing pytest warnings were reported; no test failed.
- Limitation: active `prefers-reduced-motion` media emulation was unavailable
  in the installed CLI; the shared reduced-motion rule was verified in the
  loaded stylesheet and recorded in `analysis.md`.
