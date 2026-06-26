# Quickstart: Web Cabinet HTMX Shell Validation

Run these checks after implementation tasks for feature 058. Use synthetic fixtures only; do not capture or commit private meeting content.

## 1. Server Unit And Contract Checks

```sh
cd apps/server
PYTHONPATH=src uv run --extra dev pytest -q \
  tests/unit/test_cabinet_web_shell.py \
  tests/integration/test_cabinet_meeting_list.py \
  tests/integration/test_cabinet_meeting_detail.py \
  tests/integration/test_cabinet_web_access_states.py \
  tests/contract/test_cabinet_contract.py \
  tests/contract/test_cabinet_no_secret_content_egress.py \
  tests/contract/test_deletion_no_secret_leakage.py \
  tests/contract/test_openapi_contract_drift.py
```

Expected outcome:

- Existing JSON API contracts remain stable.
- Browser and desktop cabinet routes render through templates.
- Private paths, object keys, signed URLs, transcript text, raw audio, and generated outcome text are absent from evidence-oriented tests.
- Unsafe cookie-authenticated actions fail closed without CSRF proof.

## 2. Desktop Route Policy And Native Shell Invariants

```sh
swift test --package-path apps/macos --filter DesktopCabinet
```

Expected outcome:

- Desktop route policy uses exact route-kind classification.
- `/desktop/meetings/{meeting_id}/deletion-report` is not blocked by broad substring matching.
- Native Stop, active recording state, local upload truth, and diagnostics remain outside WebView ownership.
- Login/auth pages do not mark the cabinet ready.

## 3. Runtime HTML Checks

```sh
PYTHONPATH=apps/server/src python specs/058-web-cabinet-htmx-shell/evidence/cabinet_runtime_check.py
```

Expected outcome:

- Standalone desktop, mobile-width browser, and desktop embedded WebView layouts have no horizontal overflow or incoherent overlap.
- HTMX fragment responses differ from full pages and set `Vary: HX-Request`.
- Local static assets load without CDN, external fonts, Tailwind-generated CSS, UI-kit runtime code, or frontend build outputs.
- Component target size, focus state, disabled state, destructive state, and long Russian labels pass runtime checks.

## 4. Static Source Guard

```sh
if find apps/server/src/twobrain_rec_server/cabinet apps/server \
  \( -name package.json -o -name package-lock.json -o -name pnpm-lock.yaml -o -name yarn.lock \
     -o -name vite.config.js -o -name vite.config.ts -o -name webpack.config.js \
     -o -name tailwind.config.js -o -name tailwind.config.ts -o -name postcss.config.js \
     -o -name storybook.config.js \) | rg .; then
  echo "Forbidden frontend toolchain file found"
  exit 1
fi

if rg -ni "tailwindcss|@tailwind|daisyui|flowbite|shadcn|@vitejs|react-dom|nextjs|storybook|webpack|https?://[^[:space:]\"']*(cdn|jsdelivr|googleapis|gstatic)" \
  apps/server/src/twobrain_rec_server/cabinet \
  apps/server/pyproject.toml \
  --glob '!static/cabinet/htmx-2.0.10.min.js' \
  --glob '!static/cabinet/htmx-2.0.10.source.txt'; then
  echo "Forbidden frontend dependency marker found"
  exit 1
fi
```

Expected outcome:

- No Tailwind, UI-kit, SPA framework, CDN font, component preview app, or frontend build pipeline is introduced for feature 058.
- Mentions are allowed only in comments/tests that explicitly assert exclusion.

## 5. Safe Stop And Rollback

Safe-stop the feature branch before merge if any of these checks fail:

- a current browser or desktop embedded cabinet URL loses its full-page fallback;
- an unsafe cookie-authenticated action mutates without CSRF proof;
- the desktop shell hides or moves native Record/Stop, active capture, upload truth, permission recovery, or local diagnostics into the WebView;
- rendered templates or committed evidence expose raw audio, transcript text, generated outcome text, signed URLs, object keys, credentials, private paths, or real account identifiers;
- Tailwind, a ready UI kit, a SPA framework, CDN UI assets, a component preview app, or a frontend build pipeline appears in the feature diff.

Rollback policy:

- This slice has no database migration and no machine-readable JSON contract change, so rollback should deploy the previous server/macOS release or revert the 058 feature branch as a whole.
- Do not leave a partial rollback where templates are reverted but route policy, CSRF wiring, static assets, or task/evidence files remain half-updated.
- If HTMX enhancement causes runtime trouble after merge, temporarily rely on the existing full-page fallback by removing the bounded `hx-*` attributes in the next hotfix while preserving CSRF and access/lifecycle checks.
- Keep GitHub issues open and `tasks.md` unchecked for any task whose evidence command has not passed after the rollback/hotfix.

## 6. Canonical Local CI

```sh
infra/scripts/ci-local.sh
```

Expected outcome:

- `ci_local_result=pass`
- No committed evidence contains private content or secrets.
