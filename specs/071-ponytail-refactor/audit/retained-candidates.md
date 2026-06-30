# Retained Candidates

**Date**: 2026-06-30

These items looked removable or oversized during static audit, but are intentionally retained because evidence is insufficient or they are known entrypoints/contracts.

| Candidate | Decision | Reason |
| --- | --- | --- |
| Provider adapter `credentials`, `http_client`, `now` arguments | Retain | Shared auth-provider callback contract; security boundary. |
| `pytest-asyncio` | Retain | Pytest async plugin; no direct import expected and `asyncio_mode = "auto"` depends on async test support. |
| `python-multipart` | Retain | FastAPI form parser for admin/cabinet `Form(...)` routes. |
| `asyncpg` | Retain | SQLAlchemy driver selected by `postgresql+asyncpg` URLs. |
| `uvicorn[standard]` | Retain | Docker/runtime ASGI entrypoint. |
| `cabinet/web.py` | Retain | Large presentation/router file; needs dedicated presentation split. |
| `cabinet/view_models.py` | Retain | Template-fed view model surface; Python caller search is insufficient. |
| `htmx-2.0.10.min.js` | Retain | Vendored browser runtime asset. |
| macOS capture/upload/diagnostic large files | Retain | Protect capture truth, upload custody, metadata-only diagnostics, and deletion/purge semantics. |
| AudioDriver proof code | Retain | Parked future-routing evidence, not proven obsolete. |
| deployment/smoke/backup/restore scripts | Retain | Operational safety entrypoints. |
| generated caches | Excluded | Local generated output, not tracked code. |

## Removed After Candidate Review

- `httpx2` dev dependency: removed in Batch B after a minimal dependency-metadata patch and validation.
