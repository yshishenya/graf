# Python Dependency Evidence

**Date**: 2026-06-30
**Scope**: `apps/server/pyproject.toml`, `apps/server/constraints.txt`, `apps/server/uv.lock`, server source, tests, and server scripts.

## Evidence Commands

```text
python AST import scan over apps/server/src, apps/server/tests, apps/server/scripts
=> python_files=411
=> alembic=22, asyncpg=0, cryptography=2, fastapi=44, httpx=8, jinja2=2, minio=4, pydantic=12, pydantic_settings=1, sqlalchemy=206, temporalio=6, uvicorn=0, pytest=41, aiosqlite=0, httpx2=0, ruff=0
```

```text
fixed-string runtime reference scan
=> postgresql+asyncpg=9
=> Form(=3
=> uvicorn=4
=> alembic=32
=> sqlite+aiosqlite=5
=> httpx2=2
=> ruff check=1
=> pytest=50
```

```text
cd apps/server && uv tree --all-groups --depth 2
=> resolved 56 packages
=> direct runtime deps include alembic, asyncpg, cryptography, fastapi, httpx, jinja2, minio, pydantic, pydantic-settings, python-multipart, sqlalchemy[asyncio], temporalio, uvicorn[standard]
=> direct dev deps include aiosqlite, httpx2, pytest, pytest-asyncio, ruff
```

## Runtime Dependencies

| Dependency | Evidence | Decision |
| --- | --- | --- |
| `alembic` | Imported by RLS verification script; `alembic.ini`; Docker compose migration command. | Keep. Migration/runtime CLI dependency. |
| `asyncpg` | No direct import, but 9 `postgresql+asyncpg` URLs across config, compose, tests, and scripts. | Keep. SQLAlchemy async driver. |
| `cryptography` | Imported for calendar credential encryption and documented production key generation. | Keep. Security boundary. |
| `fastapi` | 44 imports across app, routes, dependencies, tests. | Keep. Web framework. |
| `httpx` | 8 imports across MediaScribe, support incident, email delivery, and tests. | Keep. HTTP client and mock transport tests. |
| `jinja2` | Imported by admin/cabinet template environments. | Keep. Server-rendered UI. |
| `minio` | Imported by storage and smoke cleanup scripts/tests. | Keep. Object storage client. |
| `pydantic` | Imported across schemas/config/contracts. | Keep. Data validation. |
| `pydantic-settings` | Imported by server config. | Keep. Settings source of truth. |
| `python-multipart` | No direct import; FastAPI `Form(...)` is used in admin and cabinet form routes. | Keep. Runtime parser for form posts. |
| `sqlalchemy[asyncio]` | 206 imports across models, queries, migrations, tests, scripts. | Keep. Persistence layer. |
| `temporalio` | 6 imports in workflows/client/worker. | Keep. Processing workflow integration. |
| `uvicorn[standard]` | Dockerfile CMD and runtime launch references, no direct import expected. | Keep. ASGI server entrypoint. |

## Dev Dependencies

| Dependency | Evidence | Decision |
| --- | --- | --- |
| `aiosqlite` | 5 `sqlite+aiosqlite` test/config references. | Keep. Local test database driver. |
| `httpx2` | Declared only as dev extra and resolved by `uv tree`; no source/test import found. | Removed in Batch B. |
| `pytest` | 41 imports and 50 command/reference hits. | Keep. Test runner. |
| `pytest-asyncio` | No direct import expected; pytest plugin used by async tests and `asyncio_mode = "auto"`. | Keep unless a plugin-removal experiment proves async tests still run. |
| `ruff` | No import expected; `ruff check` used by local CI. | Keep. Lint gate. |

## Removed In Batch A

| Dependency | Evidence | Decision |
| --- | --- | --- |
| `structlog` | Previously declared in server dependency metadata; active server/macos/infra/scripts search now has no matches after removal from `pyproject`, `constraints.txt`, and `uv.lock`. | Removed. |

## Removed In Batch B

| Dependency | Evidence | Decision |
| --- | --- | --- |
| `httpx2` | Direct dev extra only; no imports; no active references after removal. Transitive `httpcore2` and `truststore` were lockfile-only through `httpx2`. | Removed. |

## Next Candidate

No additional direct Python dependency removal is approved from the current evidence.
