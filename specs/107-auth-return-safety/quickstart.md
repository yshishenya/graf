# Quickstart: Safe Browser Login Returns and Callback Diagnostics

## Scope boundary

Run all checks from this feature branch. They validate server behavior only.
Do not run a deployment, release preparation, production Docker command, tag,
or production log-retention action while the release gate remains closed.

## Focused development checks

From the repository root:

```sh
cd apps/server
PYTHONPATH=src uv run --extra dev pytest -q \
  tests/integration/test_web_owner_session_context.py \
  tests/integration/test_cabinet_web_access_states.py \
  tests/integration/test_runtime_request_logging.py \
  tests/integration/test_compose_hardening.py \
  tests/unit/test_cabinet_web_shell.py \
  tests/unit/test_structured_logging.py
```

Run the focused PostgreSQL RLS test when the local PostgreSQL integration
fixture is available:

```sh
cd apps/server
PYTHONPATH=src uv run --extra dev pytest -q tests/integration/test_rls_postgres_policies.py
```

## Required scenarios

1. Start from signed-out regular and embedded detail routes. Complete a
   supported external provider login as a user who cannot view the meeting;
   confirm a 303 to the matching list and no meeting content in the response.
2. Repeat for an authorized owner, active team-visible member, and named share
   recipient; confirm the original matching detail route remains.
3. Complete email login and email registration. Change the verification form's
   `next` value before submission; confirm the stored callback-state return
   candidate, not the changed form value, decides the result.
4. Re-run existing missing-browser-state, expiry, cancellation, and replay
   checks. They must remain unchanged.
5. Open missing, denied, and malformed regular and embedded detail URLs with
   an authenticated session. Confirm each full-page response is neutral HTML
   404 with a matching list link; confirm HTMX/API 404 behavior remains
   machine-readable.
6. Run the Uvicorn subprocess test with synthetic, non-secret markers in the
   query and headers. Confirm no marker appears in stdout/stderr while the safe
   structured completion event, templated path, status, and duration remain.

## Closeout gate

After focused checks are green and only when implementation is ready for
closeout, run from the repository root:

```sh
infra/scripts/ci-local.sh
```

Record the high-risk validation evidence. Do not run `infra/scripts/cd-remote.sh`
or create a release; the user must explicitly reopen that gate after parallel
work is complete.
