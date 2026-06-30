# Cabinet Candidates

**Date**: 2026-06-30
**Scope**: `apps/server/src/twobrain_rec_server/cabinet/`, cabinet-facing routes, templates, static assets, and cabinet tests.

## Size Signals

Largest cabinet-related files from inventory:

```text
2125 apps/server/src/twobrain_rec_server/cabinet/web.py
1928 apps/server/src/twobrain_rec_server/cabinet/view_models.py
1192 apps/server/src/twobrain_rec_server/cabinet/rendering.py
1158 apps/server/tests/unit/test_cabinet_web_shell.py
1070 apps/server/src/twobrain_rec_server/cabinet/egress.py
722 apps/server/src/twobrain_rec_server/api/cabinet.py
```

## Candidate Decisions

### CAB-001: `cabinet/web.py` presentation split

Decision: retained for now; needs dedicated cabinet presentation batch.

Reason:

- The file is large, but it owns browser routes, HTMX fragments, email-code flows, calendar settings forms, CSRF/session behavior, and rendering orchestration.
- A safe split should be presentation-only and must not mix with API/service/auth behavior.
- Batch A already removed only unused local rendering parameters; no additional deletion is proven.

Validation requirement for future batch:

- `tests/unit/test_cabinet_web_shell.py`
- `tests/integration/test_web_owner_session_context.py`
- cabinet CSRF/access/fragment integration tests
- server lint and `infra/scripts/ci-local.sh`

### CAB-002: `cabinet/view_models.py` model split

Decision: retained for now; needs caller-by-caller view model audit.

Reason:

- The file is large but feeds server-rendered pages and tests.
- View model functions can be template-only and not obvious through Python caller search.

### CAB-003: `cabinet/rendering.py` template shell helpers

Decision: retained for now.

Reason:

- Rendering helpers are entrypoints for template composition and embedded/desktop cabinet behavior.
- Batch A already removed unused parameters proven by caller/template behavior.

### CAB-004: `htmx-2.0.10.min.js`

Decision: retained.

Reason:

- This is a vendored browser runtime asset, not hand-authored dead code.
- Removing it requires replacement asset proof and browser-cabinet validation.

## Approved Cabinet Removals

None beyond Batch A.
