# Server Checks Evidence: 058 Web Cabinet HTMX Shell

Date: 2026-06-26

## Result

`targeted_server_result=pass`

## Command

```sh
cd apps/server
PYTHONPATH=src uv run --extra dev pytest -q \
  tests/unit/test_cabinet_web_shell.py \
  tests/unit/test_cabinet_navigation_model.py \
  tests/unit/test_cabinet_template_components.py \
  tests/unit/test_cabinet_template_sections.py \
  tests/integration/test_cabinet_meeting_list.py \
  tests/integration/test_cabinet_meeting_detail.py \
  tests/integration/test_cabinet_web_access_states.py \
  tests/integration/test_cabinet_csrf.py \
  tests/integration/test_cabinet_hx_fragments.py \
  tests/integration/test_cabinet_hx_delete_feedback.py \
  tests/contract/test_cabinet_contract.py \
  tests/contract/test_cabinet_no_secret_content_egress.py \
  tests/contract/test_cabinet_csrf_contract.py \
  tests/contract/test_cabinet_frontend_foundation_contract.py \
  tests/contract/test_cabinet_shell_response_contract.py \
  tests/contract/test_cabinet_static_assets_contract.py \
  tests/contract/test_cabinet_runtime_evidence_contract.py \
  tests/contract/test_openapi_contract_drift.py
```

## Observed Output

- `93 passed, 5 warnings`
- Warnings were pytest-asyncio and Starlette TestClient deprecations.

## Convergence Check For T087-T090

```sh
cd apps/server
uv run pytest \
  tests/unit/test_cabinet_template_components.py \
  tests/unit/test_cabinet_web_shell.py \
  tests/integration/test_cabinet_meeting_list.py \
  tests/integration/test_cabinet_hx_fragments.py \
  tests/integration/test_cabinet_hx_delete_feedback.py
PYTHONPATH=src uv run --extra dev ruff check .
```

Observed result:

- `40 passed, 1 warning`
- `ruff`: `All checks passed`

Covered convergence checks:

- shared shell composition renders through Jinja templates;
- direct `Markup(...)` is absent from `cabinet/web.py`;
- Jinja `|safe` remains limited to the reviewed static icon path whitelist;
- list filter/sort controls use GET plus bounded HTMX region updates;
- selected-row deletion uses server-owned HTMX feedback instead of custom JSON `fetch()`.

## Runtime HTML Check

```sh
PYTHONPATH=apps/server/src python specs/058-web-cabinet-htmx-shell/evidence/cabinet_runtime_check.py
```

Observed result:

- `result=pass`
- `surface_count=8`
- `checks=12 passed`

Covered checks:

- standalone shell
- desktop embedded shell
- native controls absent from WebView
- bounded list fragment
- bounded detail fragment
- bounded deletion report fragment
- `Vary: HX-Request`
- responsive contract
- focus and target sizing contract
- ephemeral fragment JavaScript state
- excluded frontend stack markers absent
- rendered synthetic evidence metadata-safe

## Static Source Guard

The quickstart static source guard passed:

- no Tailwind/UI-kit/SPA/frontend-build toolchain file was found;
- no forbidden runtime dependency marker was found in cabinet static assets or server package metadata.

## Wheel Package Data Check

The server wheel was built locally with `uv build --wheel` and inspected for
required cabinet package data. Required Jinja templates and static assets were
present:

- `twobrain_rec_server/cabinet/templates/cabinet/base.html`
- `twobrain_rec_server/cabinet/templates/cabinet/fragments/deletion_report.html`
- `twobrain_rec_server/cabinet/static/cabinet/cabinet.css`
- `twobrain_rec_server/cabinet/static/cabinet/htmx-2.0.10.min.js`

Observed result: `missing=[]`.

## Evidence Hygiene

This evidence records command names, counts, and safe check names only. It does
not include raw audio, transcript text, generated outcome text, object keys,
signed URLs, credentials, private local paths, or real account identifiers.
